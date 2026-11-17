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


class JobError(Exception):
    """Galat handler: kategorisasi hasil untuk engine."""

    def __init__(self, *, code: str, retryable: bool = False, uncertain: bool = False,
                 recovery_required: bool = False, message: str = "") -> None:
        self.code = code
        self.retryable = retryable
        self.uncertain = uncertain
        self.recovery_required = recovery_required
        self.message = message
        super().__init__(message or code)


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

    - heartbeat/progress: CAS token+epoch; False = kepemilikan hilang
      (ctx.lost) dan efek berikutnya harus berhenti.
    - scope(): unit transaksi tenant pendek untuk kerja DB handler; I/O
      jaringan HARUS di luar unit ini (tidak ada lock DB melintasi send).
    """

    job: Job
    payload: dict[str, Any] = field(default_factory=dict)
    lost: bool = False

    def _fenced(self, **fields) -> bool:
        rows = Job.objects.filter(
            id=self.job.id,
            lease_token=self.job.lease_token,
            lease_epoch=self.job.lease_epoch,
        ).exclude(state__in=TERMINAL_STATES).update(**fields)
        owned = rows > 0
        if not owned:
            self.lost = True
        return owned

    def heartbeat(self) -> bool:
        """Perpanjang lease (transaksi pendek sendiri — terlihat observer)."""
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

    @contextmanager
    def scope(self):
        """Unit transaksi tenant pendek (RLS aktif) untuk kerja DB handler.

        Tidak menahan transaksi melintasi I/O jaringan: handler memanggil
        scope() per unit DB dan melakukan send/readback di antaranya.
        """
        if self.lost:
            raise OwnershipLost(f"job {self.job.id}: lease hilang sebelum unit DB")
        with tenant_scope(self.job.tenant_id):
            yield
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
    """CAS tulisan envelope: hanya bila lease+epoch milik worker dan state
    sesuai salah satu expected. Terminal tidak pernah tertimpa."""
    rows = Job.objects.filter(
        id=job.id,
        lease_token=job.lease_token,
        lease_epoch=job.lease_epoch,
        state__in=expected_states,
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


def check_current_authority(job: Job, payload: dict[str, Any] | None = None) -> None:
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

        membership = Membership.objects.filter(user=actor, tenant_id=job.tenant_id, revoked_at=None).first()
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

        # --- satu pemilik pengirim per router (A03) ---
        if job.router_id is not None:
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
            sender_router_id = job.router_id

        # --- execute: effect_state=maybe ATOMIK dengan entering executing ---
        # (mencegah false-cancel saat kirim outstanding; A03)
        if not _fenced_update(
            job, [JobState.PREFLIGHT], state=JobState.EXECUTING,
            effect_state=EffectState.MAYBE, phase_label_code="executing", updated_at=dj_timezone.now(),
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
            result = handler.execute(ctx) or {}
        except DrainRequested:
            return _hold_for_drain(job, mid_effect=True)
        except OwnershipLost:
            raise
        except JobError as exc:
            return _finish_execute_failure(job, exc)
        except Exception:
            logger.exception("job %s gagal tak terduga", job.id)
            return _finish_execute_failure(job, JobError(code="internal_error", retryable=True))

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
    if exc.uncertain:
        # Perintah mungkin sudah terkirim/terjalankan: status uncertain, bukan failed.
        return _mark_fenced(job, [JobState.EXECUTING], JobState.UNCERTAIN,
                            error_code=exc.code, retryable=exc.retryable,
                            lease_token=None, lease_expires_at=None)
    if exc.recovery_required:
        return _mark_fenced(job, [JobState.EXECUTING], JobState.RECOVERY_REQUIRED,
                            error_code=exc.code, retryable=False)
    return _retry_or_fail(job, exc, expected_states=[JobState.EXECUTING])


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
    """
    if job.state != JobState.UNCERTAIN:
        raise ValueError("Bukan uncertain")
    now = dj_timezone.now()
    if applied is False:
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


def retry_job(job: Job, actor=None) -> Job:
    """Job terminal retryable → job baru menautkan asal (key idempotensi semula).

    - uncertain TIDAK boleh retry langsung: unknown outcome harus lewat
      resolve_uncertain (readback) — retry tidak membuka efek baru dari hasil
      tak diketahui.
    - Retry serentak di-serialisasi (lock baris origin) dan ditolak bila
      sudah ada kandidat aktif untuk origin yang sama → tidak ada efek
      logis ganda.
    """
    if job.state not in (JobState.FAILED, JobState.CANCELLED):
        raise ValueError("not_retryable")
    detail = None
    with transaction.atomic():
        origin = Job.objects.select_for_update().filter(id=job.id).first()
        if origin is None or origin.state not in (JobState.FAILED, JobState.CANCELLED):
            raise ValueError("not_retryable")
        # Kandidat aktif = SEMUA state nonterminal, termasuk uncertain dan
        # recovery_required: uncertain berarti efek mungkin sudah terjadi —
        # kandidat kedua akan membuka efek baru dari outcome tak diketahui
        # (REV-2011-01, A04).
        active_states = {
            JobState.QUEUED, JobState.CLAIMED, JobState.PREFLIGHT,
            JobState.EXECUTING, JobState.VERIFYING, JobState.WAITING_DEPENDENCY,
            JobState.RETRY_WAIT, JobState.UNCERTAIN, JobState.RECOVERY_REQUIRED,
        }
        if Job.objects.filter(origin_job_id=origin.id, state__in=active_states).exists():
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
