"""Engine pekerjaan: claim, lease, fencing, transisi, rekonsiliasi (TK-103).

Aturan (ARCHITECTURE.md §6, task0020/PA-002+PA-003):
- Claim SKIP LOCKED, transaksi pendek, tanpa menahan lock/transaksi DB saat
  I/O jaringan (handler memakai ctx.scope() per unit DB pendek).
- Semua tulisan worker (transisi/terminal/hasil/heartbeat/progress/retry)
  adalah CAS lease token+epoch+expected state; kehilangan kepemilikan
  menghentikan efek berikutnya (OwnershipLost), bukan diabaikan.
- Actor/permission/policy terkini diperiksa ulang dari DB segar sebelum efek
  (PA-003); actor null tidak otomatis menjadi privilege sistem.
- Satu pemilik pengirim mutasi per router (advisory lock sesi PG); pemilik
  baru menunggu penulis lama benar-benar berhenti (koneksi/lease difence).
- Lease habis pada executing/verifying → uncertain; claimed/preflight tanpa
  efek → antrian ulang (recovery state/effect-aware, CAS, dapat diulang).
- Terminal state immutable; permintaan baru = job baru menautkan asal.
- B3/B4 jendela observasi tidak diberi deadline pendek (job cutover tanpa
  deadline_s; deadline hanya membatasi kirim efek baru).
"""
from __future__ import annotations

import hashlib
import logging
import os
import socket
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils import timezone as dj_timezone

from domains.common.tenant_context import tenant_scope
from domains.jobs.models import (
    CANCEL_OK_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    EffectState,
    Job,
    JobDetail,
    JobState,
    OutboxEvent,
)

logger = logging.getLogger(__name__)

LEASE_S = 30
HEARTBEAT_S = 10
BACKOFF_CAP_S = 300
MAX_ATTEMPTS = 5
OUTBOX_POLL_S = 2
ROUTER_BUSY_RETRY_S = 2
CLAIM_SCAN_LIMIT = 50

# Namespace advisory lock pengirim per-router (PG session-level): dua worker
# tidak mengirim mutasi ke router yang sama bersamaan; router lain mandiri.
_SENDER_LOCK_NS = 0x6D745253  # 'mtRS'

# Registry attempt in-flight per PROSES ini (REV-1711-04 R3).
# Kehilangan sesi DB (pg_terminate_backend / putus koneksi) melepas advisory
# lock pengirim dan lease bisa direkonsiliasi menjadi uncertain, TETAPI
# adapter/penulis lama bisa masih hidup di luar DB dan mendaratkan kirimnya
# SETELAH readback negatif diamati. Lock yang terlepas + epoch baru saja
# TIDAK membedakan "penulis lama masih berjalan" dari "penulis sudah
# selesai". Registry ini menutup kasus attempt yang masih berjalan DI PROSES
# INI. Bukti lintas proses (R4): kolom writer_* pada Job — identitas proses
# ditulis saat attempt memasuki EXECUTING, receipt writer_ended_at ditulis
# di finally run_claimed; resolve memakai receipt / liveness /proc.
_INFLIGHT_ATTEMPTS: set[str] = set()
_INFLIGHT_LOCK = threading.Lock()


def _attempt_inflight(job_id) -> bool:
    """Attempt run_claimed untuk job ini masih berjalan di proses ini."""
    with _INFLIGHT_LOCK:
        return str(job_id) in _INFLIGHT_ATTEMPTS


def _proc_start_ticks(pid: int) -> tuple[int | None, bool | None]:
    """(starttime /proc/<pid>/stat, alive) — identitas proses anti PID-reuse.

    - (ticks, True): proses ada dan starttime terbaca.
    - (None, False): /proc/<pid> TIDAK ADA → proses pasti sudah berhenti.
    - (None, None): proses mungkin ada tapi stat tidak terbaca/diparse
      (non-Linux, izin) → identitas tidak dapat ditentukan (unknown).
    Field 22 stat (starttime, clock ticks sejak boot) — comm bisa berisi
    spasi/kurung, jadi field diambil SETELAH karakter ')' terakhir.
    """
    try:
        with open(f"/proc/{int(pid)}/stat", "rb") as fh:
            data = fh.read()
    except FileNotFoundError:
        return None, False  # entri /proc hilang = proses mati (bukan unknown)
    except Exception:
        return None, None
    try:
        rest = data[data.rindex(b")") + 2:].split()
        return int(rest[19]), True  # field 22 keseluruhan = pid+comm+19 → index 19
    except Exception:
        return None, None


def _writer_identity() -> dict[str, Any]:
    """Identitas penulis attempt ini (proses OS saat ini)."""
    pid = os.getpid()
    start_ticks, _alive = _proc_start_ticks(pid)
    return {
        "writer_pid": pid,
        "writer_host": socket.gethostname(),
        "writer_start_ticks": start_ticks,
    }


def _write_attempt_receipt(job_id, attempt_epoch: int) -> None:
    """Receipt: attempt run_claimed selesai sepenuhnya (semua I/O handler
    sudah kembali) — bukti penulis attempt ini berhenti menulis (R4).

    CAS pada lease_epoch attempt: hanya receipt untuk attempt YANG SAMA;
    attempt baru (epoch naik) tidak tertimpa receipt basi. Kegagalan tulis
    (sesi DB mati) ditelan — bukti hilang berarti status penulis kembali
    unknown dan resolve tetap fail-closed lewat cek liveness.
    """
    try:
        with transaction.atomic():
            Job.objects.filter(
                id=job_id,
                lease_epoch=attempt_epoch,
                writer_ended_at=None,
            ).update(writer_ended_at=timezone.now())
    except Exception:
        logger.debug("writer receipt job %s gagal ditulis (sesi DB mati?)", job_id, exc_info=True)


def _writer_verifiably_stopped(job: Job) -> tuple[bool, str]:
    """Bukti penulis attempt yang menghasilkan uncertain telah berhenti.

    Urutan bukti (kuat → lemah):
    1. attempt masih in-flight DI PROSES INI → pasti belum selesai (False).
    2. receipt writer_ended_at untuk attempt terakhir → attempt selesai
       sepenuhnya dan tidak menulis lagi (True).
    3. penulis = proses INI (registry sudah tidak in-flight) → attempt
       selesai di proses ini (True) — cadangan bila receipt gagal ditulis.
    4. penulis proses LAIN pada host yang sama → liveness /proc + starttime:
       proses mati / PID direuse → penulis terverifikasi berhenti (True);
       proses masih hidup → (False, writer_active).
    5. penulis host lain / identitas tidak terbaca / baris lama tanpa
       identitas → status TIDAK DIKETAHUI → (False, writer_unverifiable)
       — fail-closed, tetap ditahan (A04: "unknown tetap tertahan").
    """
    if _attempt_inflight(job.id):
        return False, "writer_active"
    fresh = Job.objects.filter(id=job.id).values_list(
        "writer_pid", "writer_host", "writer_start_ticks", "writer_ended_at",
    ).first()
    if fresh is None:
        return False, "writer_unverifiable"
    writer_pid, writer_host, start_ticks, ended_at = fresh
    if ended_at is not None:
        return True, "attempt_completed"
    if writer_pid is None:
        # Tidak pernah ada identitas penulis attempt (baris pra-migrasi /
        # uncertain sintetis tanpa EXECUTING) → unknown, ditahan.
        return False, "writer_unverifiable"
    my_host = socket.gethostname()
    if writer_host != my_host:
        return False, "writer_unverifiable"
    if int(writer_pid) == os.getpid():
        return True, "same_process_completed"
    # Proses lain di host sama: bukti liveness nyata dari OS.
    observed, alive = _proc_start_ticks(int(writer_pid))
    if alive is False:
        # /proc/<pid> tidak ada → proses penulis pasti sudah berhenti.
        return True, "process_terminated"
    if observed is None or start_ticks is None:
        # Stat tidak terbaca/diparse atau identitas awal tidak terekam →
        # tidak bisa membedakan hidup/mati (termasuk kemungkinan PID reuse)
        # → unknown, ditahan (fail-closed).
        return False, "writer_unverifiable"
    if observed == start_ticks:
        # /proc/<pid> masih ada DAN starttime cocok → proses yang sama masih hidup.
        return False, "writer_active"
    # starttime berbeda (PID direuse proses lain) → proses penulis asli
    # sudah berhenti.
    return True, "process_terminated"


class JobError(Exception):
    """Galat handler: kategorisasi hasil untuk engine.

    - ``no_effect=True``: bukti EKSPLISIT handler bahwa kegagalan terjadi
      sebelum efek apa pun (probe baca-saja gagal / DB rollback bersih).
      Hanya bentuk ini yang boleh retry otomatis dari eksekusi (REV-1711-02:
      "retry hanya dari bukti no-effect/safe outcome yang eksplisit").
    - Tanpa bukti itu, kegagalan tahap executing default ditahan
      uncertain/recovery — tidak pernah blind retry_wait.
    """

    def __init__(self, *, code: str, retryable: bool = False, uncertain: bool = False,
                 recovery_required: bool = False, no_effect: bool = False,
                 message: str = "") -> None:
        self.code = code
        self.retryable = retryable
        self.uncertain = uncertain
        self.recovery_required = recovery_required
        self.no_effect = no_effect
        self.message = message or code
        super().__init__(self.message)


class OwnershipLost(Exception):
    """Worker kehilangan lease (transfer/reconcile/cancel) — efek dihentikan."""


class DrainRequested(Exception):
    """Worker diminta berhenti (drain) — handler berhenti di batas aman."""


# ---------------------------------------------------------------------------
# Kewenangan kind (PA-003) — sumber izin operasi yang mendasari job.


KIND_PERMISSION_FALLBACK: dict[str, str | tuple[str, ...]] = {
    "import_commit": "imports.run",
    "commit_migration": "migration.run",
    "harvest_passwords": "migration.run",
    "discover_router": ("routers.enroll", "migration.run"),
    "router_release": "routers.release",
    "router_replace": "routers.release",
    "verify_api_ssl": "routers.enroll",
    "backup_router": "backups.run",
    "radius_cutover_step": "radius.cutover",
}


def authority_requirement(job: Job) -> str | tuple[str, ...] | None:
    """Izin operasi yang mendasari job menurut kind (PA-003).

    Kebutuhan izin diturunkan dari kind karena setiap kind di-enqueue oleh
    view/layanan dengan izin tetap (inventaris task0020); discover_router
    punya DUA asal sah (discovery view routers.enroll; migrasi view
    migration.run) → any-of, identik dengan himpunan pengenqueue sahnya.
    Kind uji (_test*) sengaja tanpa syarat izin (bukan operasi produksi).
    Kind produksi yang LUPA dipetakan → None akan gagal tertutup di
    check_current_authority/create_job (fail-closed, REV-2011-08).
    """
    return KIND_PERMISSION_FALLBACK.get(job.kind)


def _unmapped_production_kind(kind: str) -> bool:
    return not kind.startswith("_test") and kind not in KIND_PERMISSION_FALLBACK


@dataclass
class JobContext:
    """Konteks eksekusi satu job milik worker ini.

    - heartbeat/progress/unit domain: CAS token+epoch; kehilangan kepemilikan
      langsung melempar OwnershipLost (efek berikutnya tidak bisa berjalan,
      termasuk kirim adapter setelah progress yang diabaikan — REV-1711-01).
    - scope(): unit transaksi tenant pendek dengan guard ownership DI DALAM
      transaksi yang sama (entry + sebelum commit) — kehilangan kepemilikan
      di tengah unit membatalkan commit domain (REV-1711-01).
    - assert_owned(): guard untuk unit DB milik service (run_discovery dll.) —
      wajib dipanggil DI DALAM transaksi unit agar cek+commit atomik.
    """

    job: Job
    payload: dict[str, Any] = field(default_factory=dict)
    lost: bool = False

    def _fenced(self, **fields) -> bool:
        # REV-1711-01 (R3): renewal worker hanya bila lease MASIH BERLAKU saat
        # pembaruan berjalan — token+epoch+state nonterminal saja tidak cukup;
        # lease kedaluwarsa berarti kepemilikan hilang (watchdog bersyarat R2
        # sudah menolaknya; jalur progress/heartbeat tidak boleh menghidupkan
        # kembali lease yang sudah mati tanpa menunggu reconciler).
        rows = Job.objects.filter(
            id=self.job.id,
            lease_token=self.job.lease_token,
            lease_epoch=self.job.lease_epoch,
            lease_expires_at__gt=timezone.now(),
        ).exclude(state__in=TERMINAL_STATES).update(**fields)
        owned = rows > 0
        if not owned:
            self.lost = True
            raise OwnershipLost(
                f"job {self.job.id}: kepemilikan hilang (lease/state berubah atau lease kedaluwarsa) — efek dihentikan"
            )
        return owned

    def heartbeat(self) -> bool:
        """Perpanjang lease (transaksi pendek sendiri — terlihat observer).

        Kehilangan kepemilikan melempar OwnershipLost (bukan sekadar False yang
        dapat diabaikan pemanggil — REV-1711-01 "helper return diabaikan").
        """
        return self._fenced(lease_expires_at=timezone.now() + timezone.timedelta(seconds=LEASE_S))

    def recheck_authority(self) -> None:
        """Periksa ulang kewenangan terkini (untuk chunk/fase kirim lanjutan).

        Handler multi-fase (mis. cutover B2→B5) memanggil ini sebelum setiap
        batas kirim sensitif berikutnya; pencabutan/demosi di tengah jalan
        menghentikan fase berikutnya tanpa efek baru (A06 per-chunk).
        """
        check_current_authority(self.job, self.payload)

    def progress(self, *, phase: str | None = None, done: int | None = None, total: int | None = None) -> bool:
        """Kemajuan + perpanjangan lease (renewal untuk pekerjaan panjang).

        Setiap laporan kemajuan sekaligus memperpanjang lease sehingga
        handler yang melapor per fase/chunk tidak dipaksa uncertain oleh
        reconcile worker lain saat masih bekerja (REV-2011-04).
        Kehilangan kepemilikan melempar OwnershipLost (REV-1711-01).
        """
        updates: dict[str, Any] = {
            "lease_expires_at": timezone.now() + timezone.timedelta(seconds=LEASE_S)
        }
        if phase is not None:
            updates["phase_label_code"] = phase
        if done is not None:
            updates["items_done"] = done
        if total is not None:
            updates["items_total"] = total
        return self._fenced(**updates)

    def assert_owned(self) -> None:
        """Guard ownership dari DB segar — untuk unit DB milik service.

        Baca lease_token/epoch/state terkini pada koneksi BERJALAN; pemanggil
        harus sudah berada DI DALAM transaksi unit (tenant_scope) sehingga
        cek ownership dan commit domain menjadi atomik: reconcile/cancel yang
        terjadi sebelum unit ini membuat guard gagal → unit dibatalkan sebelum
        commit (REV-1711-01). Guard gagal melempar OwnershipLost dan menandai
        ctx.lost sehingga efek berikutnya (termasuk send adapter) berhenti.
        """
        row = Job.objects.filter(id=self.job.id).values_list(
            "lease_token", "lease_epoch", "state"
        ).first()
        owned = (
            row is not None
            and row[0] == self.job.lease_token
            and row[1] == self.job.lease_epoch
            and row[2] not in TERMINAL_STATES
        )
        if not owned:
            self.lost = True
            raise OwnershipLost(
                f"job {self.job.id}: guard ownership gagal pada unit domain (REV-1711-01)"
            )

    def guard_commit(self) -> None:
        """Guard ownership TERKUNCI pada baris job — REV-1711-01 (R2).

        Dipanggil DI DALAM transaksi unit sesaat SEBELUM commit: SELECT ...
        FOR UPDATE pada baris job di koneksi/transaksi unit yang sama, lalu
        validasi segar token+epoch+state non-terminal+lease masih berlaku.
        Dengan lock baris ini, update ownership-changing (reconcile/cancel/
        transfer lease) milik pihak lain ter-serialisasi terhadap commit unit:
        transfer tidak bisa menyelinap di antara guard dan commit (window
        check-to-commit tertutup), atau unit kalah dan di-rollback. Ini bukan
        SELECT polos lain — lock dipegang sampai unit commit/rollback.
        """
        row = (
            Job.objects.select_for_update()
            .filter(id=self.job.id)
            .values_list("lease_token", "lease_epoch", "state", "lease_expires_at")
            .first()
        )
        owned = (
            row is not None
            and row[0] == self.job.lease_token
            and row[1] == self.job.lease_epoch
            and row[2] not in TERMINAL_STATES
            and row[3] is not None
            and row[3] > timezone.now()
        )
        if not owned:
            self.lost = True
            raise OwnershipLost(
                f"job {self.job.id}: guard commit terkunci gagal (lease/state berubah)"
            )

    @contextmanager
    def scope(self):
        """Unit transaksi tenant pendek (RLS aktif) + guard ownership.

        SATU transaksi nyata (transaction.atomic): (1) guard segar sebelum
        yield; (2) guard TERKUNCI (FOR UPDATE, guard_commit) sesaat sebelum
        commit — kehilangan kepemilikan yang terjadi selama unit membatalkan
        commit domain, dan update ownership-changing pihak lain ter-serialisasi
        terhadap commit unit ini (REV-1711-01 R2: window check-to-commit
        tertutup lock baris job; bukan SELECT polos lain). I/O jaringan TETAP
        di luar unit ini; handler memanggil scope() per unit DB.
        """
        if self.lost:
            raise OwnershipLost(f"job {self.job.id}: lease hilang sebelum unit DB")
        with tenant_scope(self.job.tenant_id), transaction.atomic():
            self.assert_owned()
            yield
            self.guard_commit()
        if self.lost:
            raise OwnershipLost(f"job {self.job.id}: lease hilang saat unit DB")


class JobHandler:
    """Antarmuka handler ter-tipe per kind (tidak ada DSL generik)."""

    kind: str = ""

    def preflight(self, ctx: JobContext) -> None:  # default: siap
        return None

    def execute(self, ctx: JobContext) -> dict[str, Any]:
        raise NotImplementedError

    def verify(self, ctx: JobContext) -> dict[str, Any]:
        raise NotImplementedError

    def on_retry(self, ctx: JobContext) -> None:  # default: tidak ada
        return None


_REGISTRY: dict[str, JobHandler] = {}


def register(handler: JobHandler) -> None:
    if handler.kind in _REGISTRY:
        raise ValueError(f"Handler duplikat: {handler.kind}")
    _REGISTRY[handler.kind] = handler


def handler_for(kind: str) -> JobHandler | None:
    return _REGISTRY.get(kind)


# ---------------------------------------------------------------------------
# Pembuatan job + outbox satu transaksi domain


def create_job(
    *,
    tenant_id,
    kind: str,
    actor=None,
    actor_display: str = "",
    router=None,
    payload: dict | None = None,
    request_id: str | None = None,
    deadline_s: int | None = None,
    priority: int = 100,
    origin_job=None,
) -> Job:
    """Buat job + detail + outbox satu transaksi; dikembalikan dalam state queued."""
    if kind not in _REGISTRY and not kind.startswith("_test"):
        # Kind fase aktif hanya yang punya handler terdaftar; mencegah job
        # palsu untuk fitur yang belum dibangun.
        raise ValueError(f"Kind tanpa handler terdaftar: {kind}")
    if _unmapped_production_kind(kind):
        # Fail-closed: kind produksi tanpa peta izin tidak boleh dibuat
        # (kelalaian future tidak membuka jalur tanpa pemeriksaan izin).
        raise ValueError(f"Kind produksi tanpa peta izin kewenangan: {kind}")
    with tenant_scope(tenant_id):
        with transaction.atomic():
            job = Job.objects.create(
                tenant_id=tenant_id,
                kind=kind,
                actor=actor,
                actor_display=actor_display or getattr(actor, "full_name", "") or getattr(actor, "email", ""),
                router=router,
                request_id=request_id,
                deadline_at=(timezone.now() + timezone.timedelta(seconds=deadline_s)) if deadline_s else None,
                priority=priority,
                origin_job=origin_job,
            )
            JobDetail.objects.create(job=job, tenant_id=tenant_id, payload=payload or {})
            OutboxEvent.objects.create(
                tenant_id=tenant_id,
                event_type="job.created",
                aggregate_type="job",
                aggregate_id=job.id,
                dedup_key=f"job:created:{job.id}",
                payload={"kind": kind},
            )
            return job


# ---------------------------------------------------------------------------
# Claim + eksekusi


def claim_next(worker_id: str | None = None) -> Job | None:
    """Klaim satu job queued (atau retry_wait yang telah jatuh tempo).

    SELECT ... FOR UPDATE SKIP LOCKED; transaksi pendek tanpa I/O jaringan.
    Job queued yang sudah melewati deadline gagal jujur (deadline_exceeded)
    tanpa pernah dikirim; pemindaian lanjut ke kandidat berikutnya.
    """
    now = timezone.now()
    for _ in range(CLAIM_SCAN_LIMIT):
        with transaction.atomic():
            job = (
                Job.objects.select_for_update(skip_locked=True)
                .filter(
                    Q(state=JobState.QUEUED, available_at__lte=now)
                    | Q(state=JobState.RETRY_WAIT, available_at__lte=now)
                )
                .order_by("priority", "id")
                .first()
            )
            if job is None:
                return None
            if job.deadline_at is not None and job.deadline_at < now:
                # Deadline terlewati sebelum efek apa pun: gagal jujur, bukan
                # dikirim terlambat (§6 "expired sebelum efek tidak mengirim").
                Job.objects.filter(id=job.id).update(
                    state=JobState.FAILED,
                    error_code="deadline_exceeded",
                    retryable=False,
                    lease_token=None,
                    updated_at=now,
                )
                continue
            previous = job.state
            job.state = JobState.CLAIMED
            job.attempt += 1
            job.lease_token = uuid.uuid4()
            job.lease_epoch += 1
            job.lease_expires_at = now + timezone.timedelta(seconds=LEASE_S)
            if previous == JobState.RETRY_WAIT:
                # retry_wait → queued → claimed sesuai mesin state.
                job.state = JobState.QUEUED
                job.save()
                job.state = JobState.CLAIMED
            job.save()
            return job
    return None


# ---------------------------------------------------------------------------
# Fencing/CAS — semua tulisan worker lewat sini (A01)


def _fenced_update(job: Job, expected_states, **fields) -> bool:
    """CAS tulisan envelope: hanya bila lease+epoch milik worker, state
    sesuai salah satu expected, dan lease MASIH BERLAKU (R3 REV-1711-01).

    Terminal tidak pernah tertimpa; lease kedaluwarsa = kepemilikan hilang
    untuk seluruh batas transisi/terminal worker — termasuk sukses terminal
    — tanpa menunggu reconciler dijadwalkan (watchdog bersyarat R2 hanya
    menutup jalur pembaruannya sendiri)."""
    rows = Job.objects.filter(
        id=job.id,
        lease_token=job.lease_token,
        lease_epoch=job.lease_epoch,
        state__in=expected_states,
        lease_expires_at__gt=dj_timezone.now(),
    ).exclude(state__in=TERMINAL_STATES).update(**fields)
    return rows > 0


def transition_claimed(job: Job, new_state: str, **fields) -> None:
    """Transisi state ter-fence (dipakai worker & API uji).

    Validasi mesin state dari snapshot; commit via CAS token+epoch+state.
    CAS gagal = kepemilikan hilang (cancel/transfer/reconcile) → OwnershipLost,
    efek berikutnya dihentikan — bukan ditimpa diam-diam.
    """
    if job.state in TERMINAL_STATES:
        raise ValueError("Job terminal tidak dapat berubah")
    if new_state not in VALID_TRANSITIONS.get(job.state, frozenset()):
        raise ValueError(f"Transisi tidak sah: {job.state} → {new_state}")
    updates = {"state": new_state, **fields, "updated_at": dj_timezone.now()}
    if not _fenced_update(job, [job.state], **updates):
        raise OwnershipLost(f"job {job.id}: transisi {job.state} → {new_state} gagal (lease/state berubah)")
    job.refresh_from_db()


# ---------------------------------------------------------------------------
# Pengirim per-router (A03): advisory lock sesi PostgreSQL


def _sender_lock_key(router_id) -> int:
    digest = hashlib.sha256(f"{_SENDER_LOCK_NS}:{router_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def acquire_router_sender(router_id) -> bool:
    """Coba menjadi satu-satunya pengirim mutasi untuk router ini.

    Advisory lock sesi PG: dua worker/job router sama tidak mengirim
    bersamaan; router lain tetap mandiri. Lease/epoch DB TIDAK menarik
    kembali command RouterOS — lock ini membuktikan penulis lama (koneksi
    yang masih hidup) telah selesai; koneksi mati melepas lock otomatis.
    """
    from django.db import connection

    key = _sender_lock_key(router_id)
    with connection.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", [key])
        row = cur.fetchone()
    return bool(row and row[0])


def release_router_sender(router_id) -> None:
    from django.db import connection

    key = _sender_lock_key(router_id)
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", [key])
            cur.fetchone()
    except Exception:  # pragma: no cover - koneksi sudah berganti/matinya sesi
        logger.debug("advisory unlock router %s gagal (sesi sudah tertutup)", router_id)


# ---------------------------------------------------------------------------
# Kewenangan terkini sebelum efek (PA-003 / A06)


def _resolve_verify_actor(job: Job, payload: dict[str, Any]):
    """Provenance verify_api_ssl: aktor job atau pembuat enrollment (DB segar)."""
    from domains.identity.models import User
    from domains.network.models import RouterEnrollment

    if job.actor_id:
        return User.objects.filter(id=job.actor_id).first()
    enrollment_id = str(payload.get("enrollment_id") or "")
    if not enrollment_id:
        return None
    enrollment = RouterEnrollment.objects.filter(id=enrollment_id).first()
    if enrollment is None or enrollment.created_by_id is None:
        return None
    return User.objects.filter(id=enrollment.created_by_id).first()


def check_current_authority(
    job: Job, payload: dict[str, Any] | None = None, *, lock_membership: bool = False
) -> None:
    """Periksa kewenangan AKTUAL dari DB segar sebelum efek (PA-003).

    - Aktor aktif + membership tenant tidak dicabut + izin operasi (metadata
      enqueue atau fallback kind) masih dimiliki peran saat ini.
    - Resource router milik tenant (RLS) dan dalam scope membership bila
      membership punya router_scope.
    - actor=None tidak otomatis sistem: verify_api_ssl menurunkan provenance
      dari enrollment.created_by; selain itu → karantina recovery_required
      (authority_unresolved) dengan jalur resume, bukan privilege diam-diam.
    - Worker TIDAK memeriksa sesi/reauth HTTP: menutup browser tidak
      membatalkan pekerjaan async yang sah (§5).
    - ``lock_membership=True`` (REV-1711-05 R4): baca baris membership dengan
      SELECT ... FOR UPDATE — HANYA untuk guard batas commit DI DALAM transaksi
      unit efek: pencabutan yang berkompetisi ter-serialisasi terhadap commit
      unit (kewenangan terbukti sah MELALUI commit), atau pencabutan sudah
      ter-commit lebih dulu dan unit dibatalkan. Pemanggil di luar transaksi
      tidak boleh memakai mode ini (Django menolak FOR UPDATE autocommit).
    """
    requirement = authority_requirement(job)
    with tenant_scope(job.tenant_id):
        from domains.identity.models import User
        from domains.tenancy.models import Membership
        from domains.tenancy.permissions import ROLE_PERMISSIONS

        if _unmapped_production_kind(job.kind):
            # Fail-closed untuk kind produksi yang tak terpetakan (bukan
            # bypass diam-diam) — REV-2011-08.
            raise JobError(
                code="authority_denied",
                retryable=False,
                message="Kind produksi tanpa peta izin kewenangan",
            )

        actor = None
        if job.kind == "verify_api_ssl":
            actor = _resolve_verify_actor(job, payload or {})
        elif job.actor_id:
            actor = User.objects.filter(id=job.actor_id).first()

        if actor is None:
            if requirement is None:
                return  # kind uji tanpa operasi produksi di baliknya
            raise JobError(
                code="authority_unresolved",
                retryable=True,
                message="Job tanpa provenance aktor sah; karantina (retryable) hingga retry dengan provenance",
            )
        if not actor.is_active:
            # Aktor dinonaktifkan: penolakan definitif, bukan karantina.
            raise JobError(
                code="authority_denied",
                retryable=False,
                message="Aktor tidak lagi aktif",
            )

        membership_qs = Membership.objects.filter(
            user=actor, tenant_id=job.tenant_id, revoked_at=None
        )
        if lock_membership:
            membership_qs = membership_qs.select_for_update()
        membership = membership_qs.first()
        if membership is None:
            raise JobError(
                code="authority_denied",
                retryable=False,
                message="Aktor bukan anggota aktif tenant job",
            )
        if requirement is not None:
            perms = ROLE_PERMISSIONS.get(membership.role, frozenset())
            needed = (requirement,) if isinstance(requirement, str) else tuple(requirement)
            if not any(p in perms for p in needed):
                raise JobError(
                    code="authority_denied",
                    retryable=False,
                    message="Peran aktor tidak lagi memiliki izin operasi job",
                )
        if job.router_id is not None:
            from domains.network.models import Router

            router = Router.objects.filter(id=job.router_id).first()  # RLS tenant
            if router is None:
                raise JobError(
                    code="authority_denied",
                    retryable=False,
                    message="Router job di luar tenant/scope",
                )
            scope = membership.router_scope
            if scope is not None:
                allowed = {str(r) for r in (scope if isinstance(scope, (list, tuple)) else [scope])}
                if str(job.router_id) not in allowed:
                    raise JobError(
                        code="authority_denied",
                        retryable=False,
                        message="Router di luar scope membership aktor",
                    )


# ---------------------------------------------------------------------------
# Eksekusi (A01–A05/A07)


def _heartbeat_watchdog(ctx: JobContext, stop: threading.Event, done: threading.Event) -> None:
    """Perpanjang lease selama fase I/O handler yang panjang (REV-1711-09 R2).

    Satu pembaruan lease nyata memakai HEARTBEAT_S (sebelumnya dideklarasikan
    tetapi tidak dipakai): pembaruan BERSYARAT — hanya memperpanjang lease yang
    MASIH berlaku saat pembaruan berjalan, tidak pernah menghidupkan kembali
    lease kedaluwarsa, sehingga keputusan reconcile/pindah kepemilikan yang sah
    tidak tertimpa pembaruan lama (fence tetap CAS token+epoch di klausa
    WHERE). 0 baris (hilang kepemilikan/lease habis) atau kegagalan koneksi →
    berhenti jujur; thread tidak menahan transaksi/lock melintasi I/O.
    Koneksi thread-nya sendiri ditutup saat keluar (tidak ada sesi menggantung).
    """
    from django.db import connections

    try:
        while not stop.wait(HEARTBEAT_S):
            try:
                rows = (
                    Job.objects.filter(
                        id=ctx.job.id,
                        lease_token=ctx.job.lease_token,
                        lease_epoch=ctx.job.lease_epoch,
                        lease_expires_at__gt=timezone.now(),
                    )
                    .exclude(state__in=TERMINAL_STATES)
                    .update(
                        lease_expires_at=timezone.now()
                        + timezone.timedelta(seconds=LEASE_S)
                    )
                )
                if not rows:
                    break
            except Exception:
                break
    finally:
        try:
            connections.close_all()
        except Exception:  # pragma: no cover - koneksi sudah mati saat keluar
            pass
    done.set()


@contextmanager
def _heartbeat_during_io(ctx: JobContext):
    """Watchdog heartbeat untuk SATU fase I/O handler (execute/verify).

    Thread daemon dibatasi: stop + join di akhir fase — participant terkumpul
    dan terhenti, tidak ada thread menggantung melintasi I/O (A02/A08).
    Pembaruan berjalan di koneksi thread-nya sendiri (transaksi pendek per
    pembaruan), terlihat observer independen.
    """
    stop = threading.Event()
    done = threading.Event()
    worker = threading.Thread(
        target=_heartbeat_watchdog,
        args=(ctx, stop, done),
        name=f"heartbeat-{ctx.job.id}",
        daemon=True,
    )
    worker.start()
    try:
        yield
    finally:
        stop.set()
        worker.join(timeout=5)


def run_claimed(job: Job, *, stop_check: Callable[[], bool] | None = None) -> Job:
    """Jalankan satu job ter-claim: authority → preflight → execute → verify.

    Tidak ada transaksi/lock DB yang melintasi I/O handler: tiap fase
    berkomitmen pendek; handler memakai ctx.scope() untuk unit DB dan
    send/readback di luar unit. Semua tulisan engine CAS ter-fence.
    Handler hilang → gagal jujur tanpa efek; verifier negatif (ok=False)
    tidak pernah menjadi succeeded.
    """
    handler = handler_for(job.kind)
    sender_router_id = None
    # Identitas attempt ini untuk receipt penulis (REV-1711-04 R4): epoch
    # attempt dipakai sebagai kunci CAS receipt di finally.
    attempt_epoch = job.lease_epoch
    # REV-1711-04 (R3): attempt ini in-flight di proses ini dari awal sampai
    # finally — resolve_uncertain(applied=False) job yang sama ditolak
    # selama attempt masih berjalan (sesi DB mati ≠ penulis lama aman).
    with _INFLIGHT_LOCK:
        _INFLIGHT_ATTEMPTS.add(str(job.id))

    try:
        if handler is None:
            # Fail-closed: kind tanpa handler tidak "sukses kosong" (A07).
            if not _fenced_update(
                job, [JobState.CLAIMED], state=JobState.FAILED,
                error_code="handler_missing", retryable=False, updated_at=dj_timezone.now(),
            ):
                raise OwnershipLost(f"job {job.id}")
            job.refresh_from_db()
            return job

        with tenant_scope(job.tenant_id):
            detail = getattr(job, "detail", None) or JobDetail.objects.get(job_id=job.id)
        payload = detail.payload or {}
        ctx = JobContext(job=job, payload=payload)

        # --- kewenangan terkini (sebelum preflight/efek) ---
        try:
            check_current_authority(job, payload)
        except JobError as exc:
            return _finish_preflight_failure(job, exc)

        # --- preflight ---
        if not _fenced_update(
            job, [JobState.CLAIMED], state=JobState.PREFLIGHT,
            phase_label_code="preflight", updated_at=dj_timezone.now(),
        ):
            raise OwnershipLost(f"job {job.id}: preflight")
        job.refresh_from_db(fields=["state", "phase_label_code"])
        try:
            with tenant_scope(job.tenant_id):
                handler.preflight(ctx)
        except JobError as exc:
            return _finish_preflight_failure(job, exc)

        # --- kewenangan pada BATAS EFEK (setelah preflight — REV-1711-05/A06) ---
        # Revoke/demote/scope-narrowing yang terjadi selama preflight harus
        # menghentikan efek: lease yang valid bukan izin aktor. Resource/router/
        # policy dibaca segar dari DB, bukan snapshot enqueue.
        try:
            check_current_authority(job, payload)
        except JobError as exc:
            return _finish_preflight_failure(job, exc)

        # --- batas stop drain sebelum efek baru ---
        if stop_check is not None and stop_check():
            if not _fenced_update(
                job, [JobState.PREFLIGHT], state=JobState.RETRY_WAIT,
                error_code="drained_before_effect", retryable=True,
                available_at=dj_timezone.now(), lease_token=None, lease_expires_at=None,
                updated_at=dj_timezone.now(),
            ):
                raise OwnershipLost(f"job {job.id}: drain hold")
            job.refresh_from_db()
            return job

        # --- deadline sebelum efek: kirim terlambat tidak jujur ---
        # Dibaca segar dari DB (deadline dapat dipendekkan ops setelah claim).
        fresh_deadline = Job.objects.filter(id=job.id).values_list("deadline_at", flat=True).first()
        if fresh_deadline is not None and dj_timezone.now() > fresh_deadline:
            if not _fenced_update(
                job, [JobState.PREFLIGHT], state=JobState.FAILED,
                error_code="deadline_exceeded", retryable=False, updated_at=dj_timezone.now(),
            ):
                raise OwnershipLost(f"job {job.id}: deadline")
            job.refresh_from_db()
            return job

        # --- satu pemilik pengirim per router (A03) + hold durable (REV-1711-04) ---
        if job.router_id is not None:
            # DURABLE hold: job router lain dengan outcome UNKNOWN menahan
            # mutasi router berkonflik sampai old writer/readback membuktikan
            # kelanjutan aman — lock sesi advisory hanya hidup selama worker;
            # state DB bertahan melewati proses. Outcome unknown mencakup:
            # (a) state uncertain/recovery_required; (b) executing/verifying
            # dengan lease KEDALUWARSA (penulis hard-crash pasca-kirim SEBELUM
            # reconcile — jendela CORR-REV-02 ditutup; penulis hidup dengan
            # lease aktif tetap dibedakan advisory lock di bawah).
            router_unknown = (
                Job.objects.filter(router_id=job.router_id)
                .filter(
                    Q(state__in=[JobState.UNCERTAIN, JobState.RECOVERY_REQUIRED])
                    | Q(
                        state__in=[JobState.EXECUTING, JobState.VERIFYING],
                        lease_expires_at__lt=dj_timezone.now(),
                    )
                )
                .exclude(id=job.id)
                .exists()
            )
            if router_unknown:
                if not _fenced_update(
                    job, [JobState.PREFLIGHT], state=JobState.RETRY_WAIT,
                    error_code="router_outcome_unknown", retryable=True,
                    available_at=dj_timezone.now() + dj_timezone.timedelta(seconds=ROUTER_BUSY_RETRY_S),
                    attempt=F("attempt") - 1, lease_token=None, lease_expires_at=None,
                    updated_at=dj_timezone.now(),
                ):
                    raise OwnershipLost(f"job {job.id}: router outcome unknown")
                job.refresh_from_db()
                return job
            if not acquire_router_sender(job.router_id):
                # Penulis lama masih memegang router: job kembali antrian
                # (attempt tidak dikonsumsi) sampai penulis terbukti selesai.
                if not _fenced_update(
                    job, [JobState.PREFLIGHT], state=JobState.RETRY_WAIT,
                    error_code="router_sender_busy", retryable=True,
                    available_at=dj_timezone.now() + dj_timezone.timedelta(seconds=ROUTER_BUSY_RETRY_S),
                    attempt=F("attempt") - 1, lease_token=None, lease_expires_at=None,
                    updated_at=dj_timezone.now(),
                ):
                    raise OwnershipLost(f"job {job.id}: sender busy")
                job.refresh_from_db()
                return job
            # REV-1711-04 (R2): recheck DURABLE DI BAWAH kunci sender yang baru
            # dipegang. SELECT pertama di atas tidak menutup jendela sampai
            # acquisition (predecessor bisa menjadi uncertain di antara keduanya
            # → tetap menahan send); dan lock advisory mati bersama SESI DB,
            # bukan bersama worker: job lain pada router ini yang masih
            # EXECUTING/VERIFYING dengan lease berlaku = penulis yang mungkin
            # masih hidup (sesi PG terputus ≠ writer berhenti). State DB bertahan
            # melewati proses, jadi cek ini tahan kehilangan sesi. Keduanya
            # menahan send sampai terbukti aman; router lain tetap maju.
            held = (
                Job.objects.filter(router_id=job.router_id)
                .exclude(id=job.id)
                .filter(
                    Q(state__in=[JobState.UNCERTAIN, JobState.RECOVERY_REQUIRED])
                    | Q(state__in=[JobState.EXECUTING, JobState.VERIFYING])
                )
                .exists()
            )
            if held:
                release_router_sender(job.router_id)
                if not _fenced_update(
                    job, [JobState.PREFLIGHT], state=JobState.RETRY_WAIT,
                    error_code="router_outcome_unknown", retryable=True,
                    available_at=dj_timezone.now() + dj_timezone.timedelta(seconds=ROUTER_BUSY_RETRY_S),
                    attempt=F("attempt") - 1, lease_token=None, lease_expires_at=None,
                    updated_at=dj_timezone.now(),
                ):
                    raise OwnershipLost(f"job {job.id}: router held")
                job.refresh_from_db()
                return job
            sender_router_id = job.router_id

        # --- execute: effect_state=maybe ATOMIK dengan entering executing ---
        # (mencegah false-cancel saat kirim outstanding; A03)
        # REV-1711-04 (R4): identitas penulis attempt (OS pid/host/starttime)
        # dipersist ATOMIK dengan entering executing — bukti lintas proses
        # untuk resolve not-applied; receipt penyelesaian ditulis di finally.
        if not _fenced_update(
            job, [JobState.PREFLIGHT], state=JobState.EXECUTING,
            effect_state=EffectState.MAYBE, phase_label_code="executing", updated_at=dj_timezone.now(),
            writer_ended_at=None, **_writer_identity(),
        ):
            raise OwnershipLost(f"job {job.id}: executing")
        job.refresh_from_db(fields=["state", "effect_state", "phase_label_code"])
        result: dict = {}
        try:
            ctx.heartbeat()
            if ctx.lost:
                # Heartbeat gagal = lease sudah berpindah/dicabut: berhenti
                # sebelum efek apa pun (A01).
                raise OwnershipLost(f"job {job.id}: heartbeat sebelum execute")
            with _heartbeat_during_io(ctx):
                result = handler.execute(ctx) or {}
        except DrainRequested:
            return _hold_for_drain(job, mid_effect=True)
        except OwnershipLost:
            raise
        except JobError as exc:
            return _finish_execute_failure(job, exc)
        except Exception:
            # Kegagalan generic pada tahap executing: efek mungkin SUDAH
            # terjadi (state MAYBE) — default ditahan uncertain (readback ops
            # menentukan kelanjutan), TIDAK blind retry (REV-1711-02; tabel §6
            # executing tidak memuat retry_wait).
            logger.exception("job %s gagal tak terduga", job.id)
            return _finish_execute_failure(job, JobError(code="internal_error", uncertain=True))

        # --- verify: readback sebelum menyatakan berhasil ---
        if not _fenced_update(
            job, [JobState.EXECUTING], state=JobState.VERIFYING,
            phase_label_code="verifying", updated_at=dj_timezone.now(),
        ):
            raise OwnershipLost(f"job {job.id}: verifying")
        job.refresh_from_db(fields=["state", "phase_label_code"])
        try:
            ctx.heartbeat()
            if ctx.lost:
                raise OwnershipLost(f"job {job.id}: heartbeat sebelum verify")
            with _heartbeat_during_io(ctx):
                result = handler.verify(ctx) or result
            if isinstance(result, dict) and result.get("ok") is False:
                # Kontrak verifier eksplisit: hasil negatif ≠ sukses (A07).
                raise JobError(
                    code="verification_failed",
                    retryable=False,
                    message=str(result.get("reason") or "verifier negatif"),
                )
        except DrainRequested:
            return _hold_for_drain(job, mid_effect=True, phase="verify")
        except OwnershipLost:
            raise
        except JobError as exc:
            if exc.recovery_required:
                return _mark_fenced(job, [JobState.VERIFYING], JobState.RECOVERY_REQUIRED,
                                    error_code=exc.code, retryable=False)
            if exc.retryable or exc.uncertain:
                # Readback transient gagal: efek mungkin sudah terjadi dan
                # TIDAK boleh dibuka eksekusi ulang → uncertain (§6; tabel
                # verifying tidak memuat retry_wait — REV-2011-05).
                return _mark_fenced(job, [JobState.VERIFYING], JobState.UNCERTAIN,
                                    error_code=exc.code, retryable=True)
            # Verdict negatif definitif (mis. verifier ok:False): gagal jujur.
            return _mark_fenced(job, [JobState.VERIFYING], JobState.FAILED,
                                error_code=exc.code, retryable=False)
        except Exception:
            logger.exception("job %s verify gagal tak terduga", job.id)
            return _mark_fenced(job, [JobState.VERIFYING], JobState.UNCERTAIN,
                                error_code="verification_error", retryable=True)

        # --- hasil + terminal SATU transaksi tenant (result RLS + CAS state) ---
        # CAS sungguhan di klausa WHERE (token+epoch+state) — bukan
        # read-then-write — sehingga keputusan reconcile/resolve/pemilik baru
        # tidak dapat ditimpa window TOCTOU (REV-2011-02, A01).
        with tenant_scope(job.tenant_id):
            with transaction.atomic():
                updates: dict[str, Any] = {
                    "state": JobState.SUCCEEDED,
                    "effect_state": EffectState.CONFIRMED,
                    "phase_label_code": None,
                    "retryable": False,
                    "updated_at": dj_timezone.now(),
                }
                current_items = Job.objects.filter(id=job.id).values_list(
                    "items_total", "items_done"
                ).first()
                if current_items and current_items[0] is not None and current_items[1] is None:
                    updates["items_done"] = current_items[0]
                rows = Job.objects.filter(
                    id=job.id,
                    lease_token=job.lease_token,
                    lease_epoch=job.lease_epoch,
                    state=JobState.VERIFYING,
                    lease_expires_at__gt=dj_timezone.now(),  # R3 REV-1711-01: sukses terminal wajib lease berlaku
                ).update(**updates)
                if not rows:
                    raise OwnershipLost(f"job {job.id}: result commit")
                detail.result = result
                detail.save(update_fields=["result"])
        job.refresh_from_db()
        return job
    except OwnershipLost:
        # Kepemilikan hilang: worker ini tidak menulis apa pun lagi; hasil
        # akhir milik pemilik lease saat ini (cancel/reconcile/pemilik baru).
        job.refresh_from_db()
        return job
    finally:
        # REV-1711-04 (R4): receipt attempt selesai — attempt ini sudah tidak
        # akan menulis/mengirim apa pun lagi (semua I/O handler kembali).
        # Receipt gagal ditulis (sesi DB mati) = bukti hilang → resolve
        # not-applied kembali fail-closed lewat cek liveness proses.
        _write_attempt_receipt(job.id, attempt_epoch)
        # REV-1711-04 (R3): attempt ini selesai sepenuhnya (semua I/O handler
        # sudah kembali) — keluarkan dari registry in-flight proses INI.
        # Bukan bukti penulis aman lintas proses; registry hanya menahan
        # resolve not-applied selama attempt masih benar-benar berjalan.
        try:
            with _INFLIGHT_LOCK:
                _INFLIGHT_ATTEMPTS.discard(str(job.id))
        except Exception:  # pragma: no cover - pembersihan registry tidak boleh gagal
            pass
        if sender_router_id is not None:
            release_router_sender(sender_router_id)


def _hold_for_drain(job: Job, *, mid_effect: bool, phase: str = "execute") -> Job:
    """Drain di tengah job: ditahan jujur, bukan sukses/failed palsu."""
    if mid_effect:
        _mark_fenced(job, [JobState.EXECUTING, JobState.VERIFYING], JobState.UNCERTAIN,
                     error_code=f"drained_mid_{phase}", retryable=True)
    else:
        _mark_fenced(job, [JobState.PREFLIGHT], JobState.RETRY_WAIT,
                     error_code="drained_before_effect", retryable=True,
                     available_at=dj_timezone.now(), lease_token=None, lease_expires_at=None)
    job.refresh_from_db()
    raise DrainRequested(f"job {job.id} ditahan saat drain")


def _mark_fenced(job: Job, expected_states, state: str, **fields) -> Job:
    updates = {"state": state, **fields, "updated_at": dj_timezone.now()}
    if state == JobState.SUCCEEDED and job.items_total is not None:
        current = Job.objects.filter(id=job.id).values_list("items_done", flat=True).first()
        if current is None:
            updates["items_done"] = job.items_total
    if not _fenced_update(job, expected_states, **updates):
        raise OwnershipLost(f"job {job.id}: _mark {state} gagal (lease/state berubah)")
    job.refresh_from_db()
    return job


def _finish_preflight_failure(job: Job, exc: JobError) -> Job:
    """Kegagalan sebelum efek hanya ke retry_wait/failed (tabel §6 dari
    claimed/preflight tidak memuat recovery_required). Karantina authority
    jujur: FAILED authority_unresolved + retryable=True — TANPA auto-retry
    (provenance tidak muncul dengan sendirinya); jalur resume adalah retry
    eksplisit dengan aktor (A09), bukan privilege sistem."""
    if exc.code == "authority_unresolved":
        return _mark_fenced(job, [JobState.CLAIMED, JobState.PREFLIGHT], JobState.FAILED,
                            error_code=exc.code, retryable=True)
    return _retry_or_fail(job, exc, expected_states=[JobState.CLAIMED, JobState.PREFLIGHT])


def _finish_execute_failure(job: Job, exc: JobError) -> Job:
    """Kegagalan tahap executing — tabel state §6: executing tidak menuju
    retry_wait; outcome tak diketahui default ditahan (REV-1711-02).

    - ``uncertain`` → UNCERTAIN (readback ops; lease dibebaskan supaya
      reconcile/penulis berikutnya ter-fence epoch).
    - ``recovery_required`` → karantina RECOVERY_REQUIRED.
    - ``retryable + no_effect`` (bukti EKSPLISIT pra-efek dari handler,
      mis. probe baca-saja / DB rollback bersih) → dua langkah sah tabel §6:
      executing→uncertain (teramati jujur) lalu uncertain→retry_wait dengan
      bukti "belum diterapkan" dari deklarasi handler.
    - ``retryable`` tanpa bukti no-effect → default UNCERTAIN (hold).
    - definitif (``retryable=False``) → FAILED.
    """
    if exc.uncertain:
        # Perintah mungkin sudah terkirim/terjalankan: status uncertain, bukan failed.
        return _mark_fenced(job, [JobState.EXECUTING], JobState.UNCERTAIN,
                            error_code=exc.code, retryable=exc.retryable,
                            lease_token=None, lease_expires_at=None)
    if exc.recovery_required:
        return _mark_fenced(job, [JobState.EXECUTING], JobState.RECOVERY_REQUIRED,
                            error_code=exc.code, retryable=False)
    if exc.retryable and exc.no_effect:
        return _retry_no_effect(job, exc)
    if exc.retryable:
        # Tanpa bukti eksplisit no-effect: outcome tak diketahui → tahan.
        return _mark_fenced(job, [JobState.EXECUTING], JobState.UNCERTAIN,
                            error_code=exc.code, retryable=True,
                            lease_token=None, lease_expires_at=None)
    return _mark_fenced(job, [JobState.EXECUTING], JobState.FAILED,
                        error_code=exc.code, retryable=exc.retryable)


def _retry_no_effect(job: Job, exc: JobError) -> Job:
    """Retry pra-efek terbukti: komposisi transisi sah tabel §6 (REV-1711-02).

    executing→uncertain (klaim jujur sesaat: engine tidak tahu) lalu
    uncertain→retry_wait dengan "bukti belum diterapkan" = deklarasi
    no_effect handler. Backoff/attempt mengikuti kebijakan retry lama.
    """
    now = dj_timezone.now()
    rows = Job.objects.filter(
        id=job.id,
        lease_token=job.lease_token,
        lease_epoch=job.lease_epoch,
        state=JobState.EXECUTING,
    ).update(
        state=JobState.UNCERTAIN,
        error_code=exc.code,
        retryable=True,
        lease_token=None,
        lease_expires_at=None,
        updated_at=now,
    )
    if not rows:
        raise OwnershipLost(f"job {job.id}: no-effect step-1")
    if job.attempt < job.max_attempts:
        backoff = min(BACKOFF_CAP_S, 2 ** job.attempt * 5)
        rows = Job.objects.filter(
            id=job.id, state=JobState.UNCERTAIN, lease_token=None,
        ).update(
            state=JobState.RETRY_WAIT,
            available_at=now + dj_timezone.timedelta(seconds=backoff),
            error_code=exc.code,
            retryable=True,
            lease_token=None,
            lease_expires_at=None,
            updated_at=now,
        )
        if not rows:
            raise OwnershipLost(f"job {job.id}: no-effect step-2")
        job.refresh_from_db()
        handler = handler_for(job.kind)
        if handler is not None:
            ctx = _ctx_for(job)
            try:
                with tenant_scope(job.tenant_id):
                    handler.on_retry(ctx)
            except Exception:  # pragma: no cover - on_retry tidak boleh membalikkan state
                logger.exception("job %s on_retry gagal (diabaikan)", job.id)
        return job
    # Attempt final (attempt == max_attempts): transisi terminal UNCERTAIN →
    # FAILED. Step-1 (di atas) sudah membuktikan kepemilikan attempt ini via
    # CAS token+epoch SAAT MEMASUKI uncertain, lalu melepas lease sesuai
    # kontrak uncertain (penulis tidak lagi memperbarui lease; reconciler /
    # pemilik baru bergerak bebas). CAS terminal umum (_fenced_update) mensyaratkan
    # lease MASIH berlaku — syarat itu mustahil dipenuhi pada jalur ini dan
    # menyandarkan attempt no-effect terakhir di UNCERTAIN (REV-1811-02).
    # CAS koheren untuk jalur ini: expected state UNCERTAIN + lease TELEPAS
    # (lease_token NULL persis seperti yang ditulis step-1) — komponen fence:
    # state machine (hanya jalur sah yang menulis UNCERTAIN+lease NULL),
    # attempt sudah dikonsumsi (claim berikutnya menaikkan epoch), dan
    # resolve/cancel/reconcile yang memindahkan job keluar UNCERTAIN membuat
    # CAS ini kalah (0 baris) → OwnershipLost, bukan menimpa state pihak lain.
    rows = Job.objects.filter(
        id=job.id,
        state=JobState.UNCERTAIN,
        lease_token=None,
    ).update(
        state=JobState.FAILED,
        error_code=exc.code,
        retryable=True,
        updated_at=dj_timezone.now(),
    )
    if not rows:
        raise OwnershipLost(f"job {job.id}: no-effect terminal (state berubah) — attempt final tidak menimpa")
    job.refresh_from_db()
    return job


def _retry_or_fail(job: Job, exc: JobError, *, expected_states) -> Job:
    if exc.retryable and job.attempt < job.max_attempts:
        backoff = min(BACKOFF_CAP_S, 2 ** job.attempt * 5)
        if not _fenced_update(
            job, expected_states,
            state=JobState.RETRY_WAIT,
            available_at=dj_timezone.now() + dj_timezone.timedelta(seconds=backoff),
            error_code=exc.code,
            retryable=True,
            lease_token=None,
            lease_expires_at=None,
            updated_at=dj_timezone.now(),
        ):
            raise OwnershipLost(f"job {job.id}: retry")
        job.refresh_from_db()
        handler = handler_for(job.kind)
        if handler is not None:
            ctx = _ctx_for(job)
            try:
                with tenant_scope(job.tenant_id):
                    handler.on_retry(ctx)
            except Exception:  # pragma: no cover - on_retry tidak boleh membalikkan state
                logger.exception("job %s on_retry gagal (diabaikan)", job.id)
        return job
    return _mark_fenced(job, expected_states, JobState.FAILED,
                        error_code=exc.code, retryable=exc.retryable)


def _ctx_for(job: Job) -> JobContext:
    with tenant_scope(job.tenant_id):
        detail = getattr(job, "detail", None) or JobDetail.objects.filter(job_id=job.id).first()
    return JobContext(job=job, payload=(detail.payload if detail else {}) or {})


# ---------------------------------------------------------------------------
# Rekonsiliasi lease & pemulihan (A05)


def reconcile_expired_leases() -> int:
    """Pemulihan state/effect-aware untuk lease habis; CAS, dapat diulang.

    - claimed/preflight (belum ada efek — engine hanya menulis effect_state
      bersama entering executing): antrikan ulang, atau failed bila attempt
      habis. Crash sesudah claim/preflight tidak menggantung selamanya.
    - executing/verifying: uncertain (efek mungkin sudah terjadi; writer lama
      difence oleh peningkatan epoch saat claim berikutnya).
    CAS memfilter token+state+masa lease teramati: tidak menimpa lease yang
    diperbarui heartbeat, hasil yang baru selesai, ataupun cancel bersamaan.
    """
    now = timezone.now()
    count = 0

    early = list(
        Job.objects.filter(
            state__in=[JobState.CLAIMED, JobState.PREFLIGHT],
            lease_expires_at__lt=now,
        )
    )
    for job in early:
        if job.attempt >= job.max_attempts:
            rows = Job.objects.filter(
                id=job.id, state=job.state, lease_token=job.lease_token, lease_expires_at__lt=now,
            ).update(
                state=JobState.FAILED, error_code="lease_expired", retryable=False,
                lease_token=None, updated_at=now,
            )
        else:
            # claimed/preflight → retry_wait (jalur tabel §6); claim berikutnya
            # menaikkan retry_wait → queued → claimed.
            rows = Job.objects.filter(
                id=job.id, state=job.state, lease_token=job.lease_token, lease_expires_at__lt=now,
            ).update(
                state=JobState.RETRY_WAIT, error_code="lease_expired", retryable=True,
                available_at=now, lease_token=None, lease_expires_at=None, updated_at=now,
            )
        count += bool(rows)

    active = list(
        Job.objects.filter(
            state__in=[JobState.EXECUTING, JobState.VERIFYING],
            lease_expires_at__lt=now,
        )
    )
    for job in active:
        rows = Job.objects.filter(
            id=job.id, state=job.state, lease_token=job.lease_token, lease_expires_at__lt=now,
        ).update(
            state=JobState.UNCERTAIN, error_code="lease_expired", retryable=True,
            lease_token=None, updated_at=now,
        )
        count += bool(rows)
    return count


def resolve_uncertain(job: Job, *, applied: bool | None, error_code: str | None = None) -> Job:
    """Readback uncertain (ops): terbukti belum diterapkan → antrian ulang
    (dengan fence penulis lama); terbukti diterapkan → verify TANPA resend;
    tidak diketahui → recovery_required (tetap tertahan, bukan blind retry).

    applied=False (bukti "belum diterapkan" hanya membuka antrian ulang bila
    penulis lama terbukti aman — REV-1711-04 R4, lintas proses):
    (1) attempt run_claimed untuk job ID sama tidak masih berjalan di proses
    ini; (2) penulis attempt yang menghasilkan uncertain TERBUKTI selesai
    (receipt writer_ended_at) atau prosesnya TERBUKTI mati/berbeda-identitas
    via /proc starttime — sesi DB mati melepas advisory lock tetapi TIDAK
    membuktikan adapter lama berhenti; (3) advisory lock sesi pengirim
    router bebas (penulis hidup lintas sesi masih memegang router — jalur
    R1 tetap berlaku). Status yang tidak dapat diverifikasi → ditolak
    (unknown tetap tertahan).
    """
    if job.state != JobState.UNCERTAIN:
        raise ValueError("Bukan uncertain")
    now = dj_timezone.now()
    if applied is False:
        if _attempt_inflight(job.id):
            # REV-1711-04 (R3): attempt untuk job ini masih berjalan — sesi DB
            # mati/lock terlepas/epoch naik TIDAK membuktikan penulis lama
            # berhenti; readback negatif bisa dikejar kirim in-flight.
            raise ValueError(
                "writer_active: attempt job ini masih berjalan di proses "
                "(sesi DB mati ≠ penulis lama aman; readback not-applied ditolak)"
            )
        # REV-1711-04 (R4): bukti lintas proses — registry proses ini saja
        # dan advisory lock bebas TIDAK membedakan "penulis masih hidup di
        # proses lain" dari "penulis selesai". Identitas penulis attempt
        # dipersist saat EXECUTING + receipt penyelesaiannya; tanpa bukti
        # (receipt/liveness/proses ini) resolve not-applied ditolak.
        stopped, reason = _writer_verifiably_stopped(job)
        if not stopped:
            raise ValueError(
                f"{reason}: penulis attempt uncertain tidak terbukti berhenti "
                "(receipt/liveness lintas proses; readback not-applied ditolak)"
            )
        if job.router_id is not None and not acquire_router_sender(job.router_id):
            # Readback "belum diterapkan" tidak dapat dipercaya selama penulis
            # lama masih hidup (send in-flight bisa mendarat SETELAH readback):
            # tolak hingga penulis terbukti berhenti, ops mengulang readback
            # (REV-2011-03; §6 "retry hanya setelah old writer aman").
            raise ValueError("writer_active")
        try:
            rows = Job.objects.filter(id=job.id, state=JobState.UNCERTAIN).update(
                state=JobState.RETRY_WAIT,
                available_at=now,
                error_code=error_code or "readback_not_applied",
                retryable=True,
                lease_token=None,
                lease_epoch=F("lease_epoch") + 1,  # fence penulis lama
                updated_at=now,
            )
            if not rows:
                raise ValueError("Bukan uncertain")
        finally:
            if job.router_id is not None:
                release_router_sender(job.router_id)
        job.refresh_from_db()
        return job
    if applied is None:
        rows = Job.objects.filter(id=job.id, state=JobState.UNCERTAIN).update(
            state=JobState.RECOVERY_REQUIRED,
            error_code=error_code or "readback_unknown",
            retryable=False,
            updated_at=now,
        )
        if not rows:
            raise ValueError("Bukan uncertain")
        job.refresh_from_db()
        return job
    # applied=True: efek terbukti sudah terjadi — jalankan verifier readback
    # ulang tanpa resend, di lease baru milik pemanggil.
    rows = Job.objects.filter(id=job.id, state=JobState.UNCERTAIN).update(
        state=JobState.VERIFYING,
        lease_token=uuid.uuid4(),
        lease_epoch=F("lease_epoch") + 1,
        lease_expires_at=now + dj_timezone.timedelta(seconds=LEASE_S),
        phase_label_code="verifying",
        updated_at=now,
    )
    if not rows:
        raise ValueError("Bukan uncertain")
    job.refresh_from_db()
    return _verify_only(job)


def _verify_only(job: Job) -> Job:
    """Verify readback ulang tanpa execute/resend (hasil resolve applied)."""
    handler = handler_for(job.kind)
    if handler is None:
        return _mark_fenced(job, [JobState.VERIFYING], JobState.RECOVERY_REQUIRED,
                            error_code="handler_missing", retryable=False)
    try:
        with tenant_scope(job.tenant_id):
            detail = getattr(job, "detail", None) or JobDetail.objects.get(job_id=job.id)
        ctx = JobContext(job=job, payload=detail.payload or {})
        # Watchdog heartbeat yang sama dengan run_claimed (REV-R2C-04):
        # verify readback yang panjang tetap memperbarui lease; pembaruan
        # tetap bersyarat sehingga tidak menghidupkan lease kedaluwarsa.
        with _heartbeat_during_io(ctx):
            result = handler.verify(ctx) or {}
        if isinstance(result, dict) and result.get("ok") is False:
            raise JobError(code="verification_failed", retryable=False,
                           message=str(result.get("reason") or "verifier negatif"))
    except JobError as exc:
        if exc.uncertain:
            return _mark_fenced(job, [JobState.VERIFYING], JobState.UNCERTAIN,
                                error_code=exc.code, retryable=exc.retryable)
        return _mark_fenced(job, [JobState.VERIFYING], JobState.FAILED,
                            error_code=exc.code, retryable=exc.retryable)
    except Exception:
        logger.exception("job %s verify-only gagal", job.id)
        return _mark_fenced(job, [JobState.VERIFYING], JobState.UNCERTAIN,
                            error_code="verification_error", retryable=True)
    with tenant_scope(job.tenant_id):
        with transaction.atomic():
            rows = Job.objects.filter(
                id=job.id,
                lease_token=job.lease_token,
                lease_epoch=job.lease_epoch,
                state=JobState.VERIFYING,
                lease_expires_at__gt=dj_timezone.now(),  # R3 REV-1711-01: lease berlaku saat commit
            ).update(
                state=JobState.SUCCEEDED,
                effect_state=EffectState.CONFIRMED,
                phase_label_code=None,
                retryable=False,
                updated_at=dj_timezone.now(),
            )
            if not rows:
                raise OwnershipLost(f"job {job.id}: verify-only commit")
            detail.result = result
            detail.save(update_fields=["result"])
    job.refresh_from_db()
    return job


# ---------------------------------------------------------------------------
# Cancel & retry (A03/A04)


def cancel_job(job: Job, reason: str) -> Job:
    """Batal atomik HANYA bila nol efek terbukti (§6); selain itu 409.

    - queued/claimed/preflight/retry_wait/waiting_dependency + effect none:
      CAS cancel yang sekaligus menaikkan epoch → worker lama gagal CAS
      berikutnya dan berhenti sebelum efek (cancel race-proof).
    - executing/verifying: ditolak — kirim outstanding tidak bisa ditarik
      dari DB (RouterOS tidak mengenal epoch); jujur 409, bukan false
      cancelled (maybe/confirmed tidak disembunyikan).
    """
    now = dj_timezone.now()
    rows = Job.objects.filter(
        id=job.id,
        state__in=CANCEL_OK_STATES,
        effect_state=EffectState.NONE,
    ).update(
        state=JobState.CANCELLED,
        cancelled_reason=reason,
        lease_token=None,
        lease_epoch=F("lease_epoch") + 1,  # fence worker lama
        updated_at=now,
    )
    if rows:
        job.refresh_from_db()
        return job
    raise ValueError("not_cancellable")


# State yang menghalangi retry origin: seluruh nonterminal — uncertain dan
# recovery_required dianggap AKTIF karena outcome belum diketahui (A04).
_RETRY_BLOCKING_STATES = frozenset(
    {
        JobState.QUEUED, JobState.CLAIMED, JobState.PREFLIGHT,
        JobState.EXECUTING, JobState.VERIFYING, JobState.WAITING_DEPENDENCY,
        JobState.RETRY_WAIT, JobState.UNCERTAIN, JobState.RECOVERY_REQUIRED,
    }
)


def _lineage_root_id(job: Job):
    """Naik ke akar lineage (origin paling awal); lineage terbatas depth-nya."""
    current_id = job.id
    origin_id = job.origin_job_id
    visited = {current_id}
    for _ in range(64):  # pragma: no branch - lineage >64 tidak realistis; guard siklus
        if origin_id is None or origin_id in visited:
            return current_id
        visited.add(origin_id)
        row = Job.objects.filter(id=origin_id).values_list("id", "origin_job_id").first()
        if row is None:
            return current_id
        current_id, origin_id = row[0], row[1]
    return current_id


def _lineage_active_exists(root_id) -> bool:
    """True bila ada job nonterminal pada lineage manapun di bawah root.

    BFS turun lewat origin_job_id — menutup REV-1711-03: retry ancestor tidak
    boleh melewati descendant uncertain/recovery/aktif (bukan child langsung
    saja). Retry atas terminal dengan outcome final tetap sah (§6).
    """
    frontier: list = [root_id]
    visited: set = {root_id}
    while frontier:
        children = list(
            Job.objects.filter(origin_job_id__in=frontier).values_list("id", "state")
        )
        if any(state in _RETRY_BLOCKING_STATES for _job_id, state in children):
            return True
        frontier = [job_id for job_id, _state in children if job_id not in visited]
        visited.update(job_id for job_id, _state in children)
        if not frontier:
            break
    return False


def retry_job(job: Job, actor=None) -> Job:
    """Job terminal retryable → job baru menautkan asal (key idempotensi semula).

    - uncertain TIDAK boleh retry langsung: unknown outcome harus lewat
      resolve_uncertain (readback) — retry tidak membuka efek baru dari hasil
      tak diketahui.
    - Retry SERENTAK di-serialisasi pada baris AKAR lineage (lock row) dan
      ditolak bila sudah ada kandidat aktif pada LINEAGE yang sama (bukan
      child langsung saja — REV-1711-03) → tidak ada efek logis ganda dari
      jalur ancestor/grandchild manapun.
    """
    if job.state not in (JobState.FAILED, JobState.CANCELLED):
        raise ValueError("not_retryable")
    detail = None
    with transaction.atomic():
        origin = Job.objects.select_for_update().filter(id=job.id).first()
        if origin is None or origin.state not in (JobState.FAILED, JobState.CANCELLED):
            raise ValueError("not_retryable")
        # Serialisasi seluruh lineage: kunci akar lineage — dua retry serentak
        # (origin dan descendant) berbagi baris akar yang sama.
        root_id = _lineage_root_id(origin)
        if str(root_id) != str(origin.id):
            Job.objects.select_for_update().filter(id=root_id).first()
        # Kandidat aktif = SEMUA state nonterminal pada lineage, termasuk
        # uncertain dan recovery_required: uncertain berarti efek mungkin
        # sudah terjadi — kandidat kedua akan membuka efek baru dari outcome
        # tak diketahui (REV-2011-01, A04; lineage-wide REV-1711-03).
        if _lineage_active_exists(root_id):
            raise ValueError("retry_active_exists")
        with tenant_scope(job.tenant_id):
            detail = getattr(origin, "detail", None) or JobDetail.objects.filter(job_id=origin.id).first()
            # Muat router DALAM scope tenant (RLS) — lazy FK di luar scope
            # akan fail-closed tersembunyi.
            router = (
                origin.router
                if origin.router_id is None
                else Job.objects.select_related("router").filter(id=origin.id).first().router
            )
        return create_job(
            tenant_id=origin.tenant_id,
            kind=origin.kind,
            actor=actor or origin.actor,
            actor_display=origin.actor_display,
            router=router,
            payload=(detail.payload if detail else {}) or {},
            request_id=origin.request_id,
            deadline_s=None,
            priority=origin.priority,
            origin_job=origin,
        )


# ---------------------------------------------------------------------------
# Outbox


def dispatch_outbox(max_events: int = 100) -> int:
    """Kirim event outbox yang belum terkirim (polling, bukan on_commit blocking)."""
    events = OutboxEvent.objects.filter(dispatched_at=None).order_by("created_at")[:max_events]
    count = 0
    for event in events:
        # Endpoint distribusi nyata (webhook/monitor) datang bersama fiturnya;
        # M1: tandai terkirim agar outbox tidak menumpuk.
        event.dispatched_at = timezone.now()
        event.attempts += 1
        event.save(update_fields=["dispatched_at", "attempts"])
        count += 1
    return count
