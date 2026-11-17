"""Tes integrasi PA-002/PA-003 (task0020) — job lifecycle, fencing, authority.

Menutup acceptance J20-A01..A09 packet task/0020-job-lifecycle-authority.md
pada PostgreSQL nyata (peran runtime non-superuser, FORCE RLS aktif via
migrasi). Pola failing-before/passing-after: jalur unfenced write, false
cancel, uncertain retry buta, revoked authority, handler/verifier gagal
tertutup semuanya diuji dari efek/state durable — bukan mock-call.

Marker transaction=True wajib: setup dan tulisan worker thread/koneksi
independen harus ter-commit dan saling terlihat.
"""
from __future__ import annotations

import threading
import uuid as _uuid

from django.utils import timezone as tz


def _time_time() -> float:
    import time

    return time.time()

import pytest

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.engine import JobContext, JobError, JobHandler
from domains.jobs.models import Job, JobState
from domains.tenancy.models import Membership, Role, Tenant

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(
        transaction=True,
        available_apps=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "domains.tenancy",
            "domains.identity",
            "domains.network",
            "domains.customers",
            "domains.jobs",
            "domains.audit",
        ],
    ),
]

_TEST_PASSWORD = "test-password-1234567890"

# Penghitung efek "send" per job — pengamatan efek nyata, bukan status.
SENDS: dict[str, int] = {}
_SENDS_LOCK = threading.Lock()


def _send(job_id) -> int:
    with _SENDS_LOCK:
        return SENDS.get(str(job_id), 0)


def _do_send(job_id) -> int:
    with _SENDS_LOCK:
        SENDS[str(job_id)] = SENDS.get(str(job_id), 0) + 1
        return SENDS[str(job_id)]


class _RouterSendHandler(JobHandler):
    """Kirim terkontrol per router: hitung efek, blokir pada gate bila diminta."""

    kind = "_test_router_send"
    gate: threading.Event | None = None
    gate_job: str | None = None

    def execute(self, ctx: JobContext) -> dict:
        n = _do_send(ctx.job.id)
        gate = _RouterSendHandler.gate
        if gate is not None and _RouterSendHandler.gate_job == str(ctx.job.id):
            gate.wait(timeout=30)  # simulasi send/readback router terblokir
        return {"sent": n}

    def verify(self, ctx: JobContext) -> dict:
        return {"ok": True, "sends": _send(ctx.job.id)}


class _MarkerHandler(JobHandler):
    """Unit DB pendek lalu I/O terblokir — untuk observer koneksi kedua (A02)."""

    kind = "_test_marker"
    blocked: threading.Event | None = None
    release: threading.Event | None = None
    worker_pid: int | None = None

    def execute(self, ctx: JobContext) -> dict:
        with ctx.scope():  # unit DB pendek (commit segera)
            _ = ctx.payload
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            _MarkerHandler.worker_pid = cur.fetchone()[0]
        if _MarkerHandler.blocked is not None:
            _MarkerHandler.blocked.set()
        if _MarkerHandler.release is not None:
            _MarkerHandler.release.wait(timeout=30)
        return {"ok": True}

    def verify(self, ctx: JobContext) -> dict:
        return {"ok": True}


class _UncertainSendHandler(JobHandler):
    """Kirim lalu timeout setelah send PERTAMA → uncertain; percobaan
    berikutnya (setelah readback membuktikan belum terapkan) menyelesaikan."""

    kind = "_test_uncertain_send"

    def execute(self, ctx: JobContext) -> dict:
        if _do_send(ctx.job.id) == 1:
            raise JobError(code="timeout_after_send", uncertain=True)
        return {"sent": _send(ctx.job.id)}

    def verify(self, ctx: JobContext) -> dict:
        return {"ok": True, "sends": _send(ctx.job.id)}


class _NegativeVerifierHandler(JobHandler):
    """Verifier negatif {ok: False} — TIDAK boleh menjadi succeeded (A07)."""

    kind = "_test_negverify"

    def execute(self, ctx: JobContext) -> dict:
        return {"ok": True}

    def verify(self, ctx: JobContext) -> dict:
        return {"ok": False, "reason": "readback_gagal"}


@pytest.fixture(autouse=True)
def _register_handlers():
    for handler in (_RouterSendHandler(), _MarkerHandler(), _UncertainSendHandler(), _NegativeVerifierHandler()):
        try:
            engine.register(handler)
        except ValueError:
            pass
    _RouterSendHandler.gate = None
    _RouterSendHandler.gate_job = None
    _MarkerHandler.blocked = threading.Event()
    _MarkerHandler.release = threading.Event()
    _MarkerHandler.worker_pid = None
    SENDS.clear()
    yield
    if _RouterSendHandler.gate is not None:
        _RouterSendHandler.gate.set()
    _MarkerHandler.release.set()


def _make_tenant(namespace: str) -> tuple[Tenant, User]:
    from domains.subscriptions import services as sub_services

    owner = User.objects.create_user(
        email=f"pa002-{namespace}@test.local", full_name=f"PA002 {namespace}",
        password=_TEST_PASSWORD, is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"T {namespace}", namespace=namespace)
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        sub_services.ensure_free_subscription(tenant)
    return tenant, owner


def _make_router(tenant: Tenant, *, code: str, ip: str):
    from domains.network.models import Router

    with tenant_scope(tenant.id):
        return Router.objects.create(
            tenant_id=tenant.id, display_name=f"R {code}", router_code=code,
            tunnel_ip=ip, mode=Router.Mode.MANAGED, credential_ref="enc:test",
        )


def _run_in_thread(job, results: dict, tag: str = "final") -> threading.Thread:
    def _run():
        try:
            results[tag] = {"state": engine.run_claimed(job).state}
        except Exception as exc:  # noqa: BLE001 — exception worker ikut menggagalkan tes
            results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
        finally:
            # Tutup koneksi thread ini (thread-local) agar tidak mengganggu
            # teardown database uji / menahan advisory lock tertinggal.
            from django.db import connections

            connections.close_all()

    t = threading.Thread(target=_run)
    t.start()
    return t


def _wait_up_to(timeout_s: float, predicate) -> bool:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


# ---------------------------------------------------------------------------
# J20-A01 — kepemilikan seluruh tulisan worker (fencing penuh)


class TestOwnershipFencing:
    def test_stale_snapshot_after_cancel_writes_nothing(self):
        """Cancel saat claimed menaikkan epoch; worker basi berhenti TANPA
        menimpa state/result dan TANPA efek baru (fail sebelum execute)."""
        tenant, owner = _make_tenant("rtrw-pa02-a01a")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner,
                                payload={"x": 1})
        claimed = engine.claim_next()
        assert claimed is not None and str(claimed.id) == str(job.id)
        epoch_before = claimed.lease_epoch

        cancelled = engine.cancel_job(claimed, "operator")
        assert cancelled.state == JobState.CANCELLED
        # epoch dinaikkan oleh cancel → pasangan token+epoch worker basi mati
        assert cancelled.lease_epoch == epoch_before + 1

        result = engine.run_claimed(claimed)  # snapshot basi milik worker lama
        assert result.state == JobState.CANCELLED  # tidak ditimpa
        assert _send(job.id) == 0  # nol efek baru
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.CANCELLED
        assert fresh.cancelled_reason == "operator"

    def test_stale_worker_after_lease_transfer_cannot_overwrite(self):
        """Lease dipindahkan (reconcile + klaim baru); snapshot worker lama
        tidak dapat menimpa state/hasil/progress pemilik baru."""
        tenant, owner = _make_tenant("rtrw-pa02-a01b")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        stale = engine.claim_next()
        from django.utils import timezone as tz

        # Paksa lease habis → reconcile → uncertain → klaim ulang (owner baru).
        Job.objects.filter(id=job.id).update(lease_expires_at=tz.now() - tz.timedelta(seconds=1))
        assert engine.reconcile_expired_leases() >= 1
        fresh_claim = engine.claim_next()
        assert fresh_claim is not None and fresh_claim.lease_epoch > stale.lease_epoch

        result = engine.run_claimed(stale)  # worker lama mencoba lanjut
        # Penulis basi menambah NOL efek (CAS gagal sebelum execute).
        assert _send(job.id) == 0, "worker basi tidak boleh mengeksekusi efek"
        # Pemilik baru menuntaskan pekerjaan dengan tepat satu efek.
        done = engine.run_claimed(fresh_claim)
        assert done.state == JobState.SUCCEEDED
        assert _send(job.id) == 1, "tepat satu efek dari pemilik yang sah"
        # Tidak ada penimpaan hasil oleh worker basi setelahnya.
        after = Job.objects.get(id=job.id)
        assert after.state == JobState.SUCCEEDED

    def test_heartbeat_progress_report_ownership_loss(self):
        """heartbeat/progress ter-fence: kehilangan lease dilaporkan (False),
        bukan diam-diam diabaikan; worker berhenti di batas berikutnya."""
        tenant, owner = _make_tenant("rtrw-pa02-a01c")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        ctx = engine.JobContext(job=claimed, payload={})
        assert ctx.heartbeat() is True
        assert ctx.progress(phase="bekerja", done=1, total=1) is True

        engine.cancel_job(claimed, "uji")  # epoch naik, token dibersihkan
        assert ctx.heartbeat() is False
        assert ctx.progress(phase="bekerja", done=2, total=2) is False
        assert ctx.lost is True
        with pytest.raises(engine.OwnershipLost):
            with ctx.scope():
                pass  # unit DB ditolak setelah kepemilikan hilang

    def test_terminal_state_immutable(self):
        """Terminal tidak dapat diubah oleh jalur engine manapun."""
        tenant, owner = _make_tenant("rtrw-pa02-a01d")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        done = engine.run_claimed(claimed)
        assert done.state == JobState.SUCCEEDED
        with pytest.raises(ValueError):
            engine.transition_claimed(done, JobState.FAILED)
        # _mark ter-fence: expected state bukan verifying → CAS gagal
        with pytest.raises(engine.OwnershipLost):
            engine._mark_fenced(done, [JobState.VERIFYING], JobState.FAILED, error_code="x")
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.SUCCEEDED


# ---------------------------------------------------------------------------
# J20-A02 — transaksi pendek + tanpa lock DB melintasi I/O


class TestTransactionBoundaries:
    def test_no_db_transaction_across_blocked_io(self):
        """Adapter diblokir terkendali: koneksi observer melihat state
        executing+maybe TERKOMIT, heartbeat terlihat, dan backend worker
        tidak menahan transaksi/lock DB (idle, bukan idle in transaction)."""
        tenant, owner = _make_tenant("rtrw-pa02-a02a")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_marker", actor=owner)
        claimed = engine.claim_next()
        lease_before = Job.objects.get(id=job.id).lease_expires_at

        results: dict = {}
        t = _run_in_thread(claimed, results)
        try:
            assert _MarkerHandler.blocked.wait(15), "handler tidak mencapai blok I/O"
            fresh = Job.objects.get(id=job.id)  # koneksi observer (utama)
            assert fresh.state == JobState.EXECUTING, "transisi executing harus terkomit"
            assert fresh.effect_state == "maybe", "effect_state=maybe harus terkomit atomik"
            assert fresh.lease_expires_at >= lease_before, "heartbeat harus terlihat observer"
            assert _MarkerHandler.worker_pid is not None
            from django.db import connection

            with connection.cursor() as cur:
                cur.execute(
                    "SELECT state FROM pg_stat_activity WHERE pid = %s",
                    [_MarkerHandler.worker_pid],
                )
                row = cur.fetchone()
                assert row is not None, "backend worker harus masih hidup (terblokir di I/O)"
                assert row[0] == "idle", (
                    f"worker tidak boleh menahan transaksi DB saat I/O (state={row[0]})"
                )
                cur.execute(
                    "SELECT count(*) FROM pg_locks WHERE pid = %s AND locktype = 'transactionid'",
                    [_MarkerHandler.worker_pid],
                )
                assert cur.fetchone()[0] == 0, "tidak boleh ada transaksi terbuka saat I/O"
        finally:
            _MarkerHandler.release.set()
        t.join(timeout=30)
        assert not t.is_alive(), "thread worker wajib selesai (bounded join)"
        assert "exception" not in results.get("final", {}), results
        assert results["final"]["state"] == JobState.SUCCEEDED

    def test_tenant_context_fail_closed_between_units(self):
        """Antar unit scope, GUC koneksi kembali fail-closed (tanpa konteks
        tenant) — koneksi pooled/reuse tidak membawa konteks lama."""
        from domains.common.tenant_context import current_tenant_id

        tenant, owner = _make_tenant("rtrw-pa02-a02b")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_marker", actor=owner)
        claimed = engine.claim_next()
        ctx = engine.JobContext(job=claimed, payload={})
        with ctx.scope():
            assert current_tenant_id() == str(tenant.id)
        assert current_tenant_id() is None, "GUC harus fail-closed setelah unit"
        # RLS fail-closed: payload tenant tidak terlihat tanpa konteks.
        from domains.jobs.models import JobDetail

        assert JobDetail.objects.count() == 0, "RLS harus menyembunyikan detail tanpa scope"


# ---------------------------------------------------------------------------
# J20-A03 — penulis eksternal & cancel


class TestExternalWriterAndCancel:
    def test_same_router_single_sender_other_router_independent(self):
        """Dua job router sama: pengirim kedua TIDAK mengirim bersamaan
        (advisory lock); router lain tetap maju mandiri."""
        tenant, owner = _make_tenant("rtrw-pa02-a03a")
        router1 = _make_router(tenant, code="PA02-R1", ip="100.127.8.1")
        router2 = _make_router(tenant, code="PA02-R2", ip="100.127.8.2")

        job1 = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner, router=router1)
        claimed1 = engine.claim_next()
        assert claimed1 is not None and str(claimed1.id) == str(job1.id)

        gate = threading.Event()
        _RouterSendHandler.gate = gate
        _RouterSendHandler.gate_job = str(job1.id)

        results1: dict = {}
        t1 = _run_in_thread(claimed1, results1)
        try:
            assert _wait_up_to(10, lambda: _send(job1.id) == 1), "job1 harus sudah 'mengirim'"

            # Job2 router sama → tidak boleh mengirim selama penulis lama hidup.
            job2 = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner, router=router1)
            claimed2 = engine.claim_next()
            assert claimed2 is not None and str(claimed2.id) == str(job2.id)
            attempt2_after_claim = Job.objects.get(id=job2.id).attempt
            r2 = engine.run_claimed(claimed2)
            assert r2.state == JobState.RETRY_WAIT
            assert r2.error_code == "router_sender_busy"
            assert _send(job2.id) == 0, "penulis kedua tidak boleh mengirim"
            fresh2 = Job.objects.get(id=job2.id)
            assert fresh2.attempt == attempt2_after_claim - 1, "attempt tidak dikonsumsi saat busy"

            # Router BERBEDA tetap mandiri (tidak diserialisasi).
            job3 = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner, router=router2)
            claimed3 = engine.claim_next()
            assert claimed3 is not None and str(claimed3.id) == str(job3.id)
            r3 = engine.run_claimed(claimed3)
            assert r3.state == JobState.SUCCEEDED
            assert _send(job3.id) == 1, "router lain harus tetap bisa maju"
        finally:
            gate.set()
        t1.join(timeout=30)
        assert not t1.is_alive()
        assert "exception" not in results1, results1
        assert results1["final"]["state"] == JobState.SUCCEEDED

        # Penulis lama selesai → job2 antrian ulang dan kini boleh mengirim.
        from django.utils import timezone as tz

        Job.objects.filter(id=job2.id).update(available_at=tz.now() - tz.timedelta(seconds=1))
        reclaimed = engine.claim_next()
        assert reclaimed is not None and str(reclaimed.id) == str(job2.id)
        r2b = engine.run_claimed(reclaimed)
        assert r2b.state == JobState.SUCCEEDED
        assert _send(job2.id) == 1, "job2 mengirim tepat sekali setelah penulis lama selesai"

    def test_cancel_rejected_while_send_outstanding(self):
        """Cancel saat executing (efek maybe, kirim outstanding) ditolak —
        tidak ada false cancelled menyembunyikan efek."""
        tenant, owner = _make_tenant("rtrw-pa02-a03b")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        gate = threading.Event()
        _RouterSendHandler.gate = gate
        _RouterSendHandler.gate_job = str(job.id)
        results: dict = {}
        t = _run_in_thread(claimed, results)
        try:
            assert _wait_up_to(10, lambda: _send(job.id) == 1)
            fresh = Job.objects.get(id=job.id)
            assert fresh.state == JobState.EXECUTING
            assert fresh.effect_state == "maybe", "effect_state=maybe harus terkomit SEBELUM handler"
            with pytest.raises(ValueError):
                engine.cancel_job(fresh, "dilarang")  # kirim outstanding
            still = Job.objects.get(id=job.id)
            assert still.state == JobState.EXECUTING, "tidak boleh false cancelled"
        finally:
            gate.set()
        t.join(timeout=30)
        assert not t.is_alive()
        assert results["final"]["state"] == JobState.SUCCEEDED

    def test_cancel_before_effect_is_atomic_and_fences_worker(self):
        """Race cancel vs execute: cancel menang CAS → worker berhenti sebelum
        efek (nol kirim); sudah executing → cancel jujur ditolak."""
        tenant, owner = _make_tenant("rtrw-pa02-a03c")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        # Cancel MENANG sebelum worker masuk executing.
        cancelled = engine.cancel_job(claimed, "cepat")
        assert cancelled.state == JobState.CANCELLED
        r = engine.run_claimed(claimed)
        assert r.state == JobState.CANCELLED
        assert _send(job.id) == 0, "cancel atomik mencegah kirim berikutnya"

    def test_cancel_queued_and_retry_wait_atomic(self):
        """queued/retry_wait (nol efek terbukti) dibatalkan atomik."""
        tenant, owner = _make_tenant("rtrw-pa02-a03d")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        c1 = engine.cancel_job(job, "antrean")
        assert c1.state == JobState.CANCELLED
        # retry_wait + effect none juga boleh.
        job2 = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        Job.objects.filter(id=job2.id).update(state=JobState.RETRY_WAIT)
        c2 = engine.cancel_job(job2, "undur")
        assert c2.state == JobState.CANCELLED


# ---------------------------------------------------------------------------
# J20-A04 — uncertain & retry


class TestUncertainAndRetry:
    def _uncertain_job(self, namespace: str):
        tenant, owner = _make_tenant(namespace)
        job = engine.create_job(tenant_id=tenant.id, kind="_test_uncertain_send", actor=owner)
        claimed = engine.claim_next()
        result = engine.run_claimed(claimed)
        assert result.state == JobState.UNCERTAIN
        assert _send(job.id) == 1
        return tenant, owner, Job.objects.get(id=job.id)  # instance segar

    def test_uncertain_not_retryable_until_readback(self):
        """Uncertain TIDAK boleh retry langsung (blind retry membuka efek baru
        dari hasil tak diketahui) — API 409, engine menolak."""
        from rest_framework.test import APIClient

        tenant, owner, job = self._uncertain_job("rtrw-pa02-a04a")
        with pytest.raises(ValueError):
            engine.retry_job(job)
        client = APIClient(enforce_csrf_checks=False)
        client.force_login(owner)
        session = client.session
        session["active_tenant_id"] = str(tenant.id)
        session["auth_at"] = _time_time()
        session.save()
        resp = client.post(f"/api/v1/jobs/{job.id}/retry")
        assert resp.status_code == 409
        assert _send(job.id) == 1, "tidak ada efek baru"

    def test_resolve_not_applied_requeues_with_old_writer_fence(self):
        """Readback terbukti belum diterapkan → antrian ulang dengan fence
        penulis lama (epoch naik); kirim ulang terjadi TEPAT sekali lagi."""
        tenant, owner, job = self._uncertain_job("rtrw-pa02-a04b")
        epoch_before = Job.objects.get(id=job.id).lease_epoch
        resolved = engine.resolve_uncertain(job, applied=False)
        assert resolved.state == JobState.RETRY_WAIT
        fresh = Job.objects.get(id=job.id)
        assert fresh.lease_epoch == epoch_before + 1, "penulis lama harus ter-fence"
        reclaimed = engine.claim_next()
        assert reclaimed is not None and str(reclaimed.id) == str(job.id)
        r = engine.run_claimed(reclaimed)
        assert r.state == JobState.SUCCEEDED
        assert _send(job.id) == 2, "kirim ulang sah tepat satu kali setelah bukti belum terapkan"

    def test_resolve_applied_verifies_without_resend(self):
        """Readback terbukti sudah diterapkan → verify TANPA resend: jumlah
        kirim tetap, job sukses lewat verifier readback."""
        tenant, owner, job = self._uncertain_job("rtrw-pa02-a04c")
        resolved = engine.resolve_uncertain(job, applied=True)
        assert resolved.state == JobState.SUCCEEDED
        assert _send(job.id) == 1, "verify tanpa resend — jumlah kirim tidak berubah"

    def test_resolve_unknown_stays_blocked(self):
        """Readback tak diketahui → tertahan (recovery_required), bukan
        dijadikan antrean eksekusi baru."""
        tenant, owner, job = self._uncertain_job("rtrw-pa02-a04d")
        resolved = engine.resolve_uncertain(job, applied=None)
        assert resolved.state == JobState.RECOVERY_REQUIRED
        assert engine.claim_next() is None, "job tertahan tidak boleh dieksekusi ulang"
        assert _send(job.id) == 1

    def test_concurrent_retry_single_active_candidate(self):
        """Retry serentak dari job failed: satu 202, lainnya 409 — tidak ada
        dua kandidat aktif untuk origin sama (efek logis tunggal)."""
        from rest_framework.test import APIClient

        tenant, owner = _make_tenant("rtrw-pa02-a04e")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        Job.objects.filter(id=job.id).update(state=JobState.FAILED, retryable=True, error_code="uji")

        def _client():
            client = APIClient(enforce_csrf_checks=False)
            client.force_login(owner)
            session = client.session
            session["active_tenant_id"] = str(tenant.id)
            session["auth_at"] = _time_time()
            session.save()
            return client

        outcomes: dict[str, dict] = {}
        barrier = threading.Barrier(2, timeout=30)

        def _retry(tag):
            try:
                client = _client()
                barrier.wait()
                resp = client.post(f"/api/v1/jobs/{job.id}/retry")
                outcomes[tag] = {"status": resp.status_code}
            except Exception as exc:  # noqa: BLE001
                outcomes[tag] = {"exception": f"{type(exc).__name__}: {exc}"}

        threads = [threading.Thread(target=_retry, args=(t,)) for t in ("A", "B")]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=45)
        assert not any(th.is_alive() for th in threads), "semua thread wajib selesai"
        assert set(outcomes) == {"A", "B"}, outcomes
        assert "exception" not in outcomes["A"] and "exception" not in outcomes["B"], outcomes
        codes = sorted([outcomes["A"]["status"], outcomes["B"]["status"]])
        assert codes == [202, 409], f"satu diterima, satu ditolak: {outcomes}"
        active = Job.objects.filter(origin_job_id=job.id).exclude(
            state__in=["succeeded", "failed", "cancelled"]
        )
        assert active.count() == 1, "tepat satu kandidat aktif"


# ---------------------------------------------------------------------------
# J20-A05 — crash / reconcile / deadline


class TestCrashReconcileDeadline:
    def test_crash_after_claim_requeues(self):
        """Proses mati setelah claim (belum ada efek): reconcile mengantrekan
        ulang — tidak menggantung, tidak false uncertain."""
        tenant, owner = _make_tenant("rtrw-pa02-a05a")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        from django.utils import timezone as tz

        Job.objects.filter(id=job.id).update(lease_expires_at=tz.now() - tz.timedelta(seconds=1))
        n = engine.reconcile_expired_leases()
        assert n >= 1
        fresh = Job.objects.get(id=job.id)
        # Jalur tabel §6: claimed/preflight → retry_wait (bukan queued langsung;
        # REV-2011-05) — claim berikutnya menaikkannya ke queued→claimed.
        assert fresh.state == JobState.RETRY_WAIT
        assert fresh.error_code == "lease_expired"
        reclaimed = engine.claim_next()
        assert reclaimed is not None and str(reclaimed.id) == str(job.id)
        r = engine.run_claimed(reclaimed)
        assert r.state == JobState.SUCCEEDED
        assert _send(job.id) == 1

    def test_crash_after_claim_max_attempts_fails(self):
        """Crash berulang hingga attempt habis → failed jujur."""
        from django.utils import timezone as tz

        tenant, owner = _make_tenant("rtrw-pa02-a05b")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        engine.claim_next()
        Job.objects.filter(id=job.id).update(
            lease_expires_at=tz.now() - tz.timedelta(seconds=1),
            attempt=5,
        )
        engine.reconcile_expired_leases()
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.FAILED
        assert fresh.error_code == "lease_expired"

    def test_reconcile_respects_renewed_lease_and_completion(self):
        """Reconcile tidak menimpa lease yang masih hidup ataupun hasil yang
        baru saja selesai (CAS memfilter state+token+masa lease teramati)."""
        from django.utils import timezone as tz

        tenant, owner = _make_tenant("rtrw-pa02-a05c")
        # (1) Lease masih hidup → tidak tersentuh.
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        engine.transition_claimed(claimed, JobState.PREFLIGHT)
        engine.transition_claimed(claimed, JobState.EXECUTING, effect_state="maybe")
        assert engine.reconcile_expired_leases() == 0
        assert Job.objects.get(id=job.id).state == JobState.EXECUTING
        # (2) Selesai (succeeded) dengan sisa lease basi → tidak ditimpa.
        Job.objects.filter(id=job.id).update(
            state=JobState.SUCCEEDED, lease_token=None,
            lease_expires_at=tz.now() - tz.timedelta(seconds=1),
        )
        assert engine.reconcile_expired_leases() == 0
        assert Job.objects.get(id=job.id).state == JobState.SUCCEEDED

    def test_reconcile_repeatable(self):
        """Reconcile diulang aman (idempotent) — tidak menimpa uncertain."""
        tenant, owner = _make_tenant("rtrw-pa02-a05d")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        engine.transition_claimed(claimed, JobState.PREFLIGHT)
        engine.transition_claimed(claimed, JobState.EXECUTING, effect_state="maybe")
        from django.utils import timezone as tz

        Job.objects.filter(id=job.id).update(lease_expires_at=tz.now() - tz.timedelta(seconds=1))
        assert engine.reconcile_expired_leases() >= 1
        assert engine.reconcile_expired_leases() == 0, "uncertain tidak di-recycle ulang"
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN

    def test_deadline_expired_in_queue_fails_without_send(self):
        """Deadline terlewat saat masih antrian → failed jujur, tanpa kirim."""
        tenant, owner = _make_tenant("rtrw-pa02-a05e")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        from django.utils import timezone as tz

        Job.objects.filter(id=job.id).update(deadline_at=tz.now() - tz.timedelta(seconds=1))
        assert engine.claim_next() is None
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.FAILED
        assert fresh.error_code == "deadline_exceeded"
        assert _send(job.id) == 0

    def test_deadline_before_execute_fails_honest(self):
        """Deadline habis setelah claim namun sebelum efek → failed tanpa
        mengirim terlambat; (expired SETELAH efek possible → uncertain,
        dibuktikan jalur uncertain di A04)."""
        tenant, owner = _make_tenant("rtrw-pa02-a05f")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        from django.utils import timezone as tz

        Job.objects.filter(id=job.id).update(deadline_at=tz.now() - tz.timedelta(seconds=1))
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED
        assert r.error_code == "deadline_exceeded"
        assert _send(job.id) == 0


# ---------------------------------------------------------------------------
# J20-A06 — kewenangan terkini sebelum efek (PA-003)


class TestCurrentAuthority:
    def _release_job(self, tenant, owner, router):
        job = engine.create_job(
            tenant_id=tenant.id, kind="router_release", actor=owner, router=router,
            payload={"router_id": str(router.id)},
        )
        claimed = engine.claim_next()
        assert claimed is not None and str(claimed.id) == str(job.id)
        return job, claimed

    def test_revoked_membership_stops_job_with_zero_effects(self):
        """Membership dicabut SETELAH enqueue: nol efek (router tidak dilepas),
        job gagal jujur authority_denied."""
        tenant, owner = _make_tenant("rtrw-pa02-a06a")
        router = _make_router(tenant, code="PA02-AUTH1", ip="100.127.9.1")
        job, claimed = self._release_job(tenant, owner, router)
        Membership.objects.filter(user=owner, tenant=tenant).update(
            revoked_at=tz.now()
        )
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED
        assert r.error_code == "authority_denied"
        with tenant_scope(tenant.id):
            from domains.network.models import Router as R

            assert R.objects.get(id=router.id).released_at is None, "nol efek"

    def test_demoted_role_stops_job(self):
        """Owner diturunkan ke viewer (tanpa routers.release) setelah enqueue →
        nol efek; izin diperiksa dari DB mutakhir, bukan snapshot enqueue."""
        tenant, owner = _make_tenant("rtrw-pa02-a06b")
        router = _make_router(tenant, code="PA02-AUTH2", ip="100.127.9.2")
        job, claimed = self._release_job(tenant, owner, router)
        Membership.objects.filter(user=owner, tenant=tenant).update(role=Role.VIEWER)
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED
        assert r.error_code == "authority_denied"
        with tenant_scope(tenant.id):
            from domains.network.models import Router as R

            assert R.objects.get(id=router.id).released_at is None

    def test_actorless_legacy_job_quarantined_with_resume_path(self):
        """Job produksi lama tanpa aktor (payload legacy) TIDAK menjadi
        privilege sistem: dikarantina recovery_required dengan alasan; jalur
        resume = retry dengan provenance baru → tuntas."""
        tenant, owner = _make_tenant("rtrw-pa02-a06c")
        router = _make_router(tenant, code="PA02-AUTH3", ip="100.127.9.3")
        job = engine.create_job(  # tanpa actor — simulasi legacy
            tenant_id=tenant.id, kind="router_release", router=router,
            payload={"router_id": str(router.id)},
        )
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)
        # Karantina jujur sesuai tabel §6: FAILED authority_unresolved yang
        # retryable — nol efek, resume = retry dengan provenance (bukan
        # privilege sistem; REV-2011-05).
        assert r.state == JobState.FAILED
        assert r.error_code == "authority_unresolved"
        assert r.retryable is True
        with tenant_scope(tenant.id):
            from domains.network.models import Router as R

            assert R.objects.get(id=router.id).released_at is None, "karantina: nol efek"
        # Resume: ops retry dengan provenance aktor sah.
        resumed = engine.retry_job(Job.objects.get(id=job.id), actor=owner)
        reclaimed = engine.claim_next()
        assert str(reclaimed.id) == str(resumed.id)
        r2 = engine.run_claimed(reclaimed)
        assert r2.state == JobState.SUCCEEDED
        with tenant_scope(tenant.id):
            from domains.network.models import Router as R

            assert R.objects.get(id=router.id).released_at is not None

    def test_platform_only_and_foreign_actor_denied(self):
        """Aktor tanpa membership tenant (mis. user platform-only) → ditolak;
        aktor non-aktif → ditolak."""
        tenant, owner = _make_tenant("rtrw-pa02-a06d")
        router = _make_router(tenant, code="PA02-AUTH4", ip="100.127.9.4")
        outsider = User.objects.create_user(
            email="pa002-outsider@test.local", full_name="Outsider",
            password=_TEST_PASSWORD, is_active=True,
        )
        job = engine.create_job(
            tenant_id=tenant.id, kind="router_release", actor=outsider, router=router,
            payload={"router_id": str(router.id)},
        )
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED and r.error_code == "authority_denied"
        # Aktor dinonaktifkan setelah enqueue → ditolak.
        job2 = engine.create_job(
            tenant_id=tenant.id, kind="router_release", actor=owner, router=router,
            payload={"router_id": str(router.id)},
        )
        User.objects.filter(id=owner.id).update(is_active=False)
        claimed2 = engine.claim_next()
        r2 = engine.run_claimed(claimed2)
        assert r2.state == JobState.FAILED and r2.error_code == "authority_denied"
        User.objects.filter(id=owner.id).update(is_active=True)

    def test_router_scope_membership_enforced(self):
        """Membership dengan router_scope sempit: job router di luar scope
        ditolak sebelum efek."""
        tenant, owner = _make_tenant("rtrw-pa02-a06e")
        router_in = _make_router(tenant, code="PA02-AUTH5", ip="100.127.9.5")
        router_out = _make_router(tenant, code="PA02-AUTH6", ip="100.127.9.6")
        Membership.objects.filter(user=owner, tenant=tenant).update(
            router_scope=[str(router_in.id)]
        )
        job = engine.create_job(
            tenant_id=tenant.id, kind="router_release", actor=owner, router=router_out,
            payload={"router_id": str(router_out.id)},
        )
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED and r.error_code == "authority_denied"
        with tenant_scope(tenant.id):
            from domains.network.models import Router as R

            assert R.objects.get(id=router_out.id).released_at is None

    def test_verify_api_ssl_provenance_from_enrollment_creator(self):
        """verify_api_ssl actorless diturunkan dari enrollment.created_by
        (provenance ownership); creator sah → berjalan; creator dicabut →
        gagal jujur, bukan privilege sistem."""
        from domains.network.models import RouterEnrollment, WireGuardPeer

        tenant, owner = _make_tenant("rtrw-pa02-a06f")
        with tenant_scope(tenant.id):
            enrollment = RouterEnrollment.objects.create(
                tenant_id=tenant.id, display_name="R Prov", router_code="PA02-PROV",
                tunnel_ip="100.127.9.7", token_hash="th-" + _uuid.uuid4().hex,
                token_expires_at=tz.now()
                + tz.timedelta(minutes=10),
                status=RouterEnrollment.Status.BOOTSTRAPPED,
                created_by=owner,
            )
            # Peer desired dibuat oleh bootstrap nyata (services) — replika.
            WireGuardPeer.objects.create(
                tenant_id=tenant.id, router=None, enrollment=enrollment,
                allowed_ip=enrollment.tunnel_ip, public_key="wgpub-pa02-prov",
                desired_revision=1, state=WireGuardPeer.State.PENDING,
            )
        job = engine.create_job(  # tanpa actor — jalur bridge
            tenant_id=tenant.id, kind="verify_api_ssl",
            payload={"enrollment_id": str(enrollment.id)},
        )
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)  # simulator path — creator sah
        assert r.state == JobState.SUCCEEDED
        # Creator kehilangan membership → job berikutnya gagal jujur.
        enrollment2 = None
        with tenant_scope(tenant.id):
            enrollment2 = RouterEnrollment.objects.create(
                tenant_id=tenant.id, display_name="R Prov2", router_code="PA02-PRO2",
                tunnel_ip="100.127.9.8", token_hash="th-" + _uuid.uuid4().hex,
                token_expires_at=tz.now()
                + tz.timedelta(minutes=10),
                status=RouterEnrollment.Status.BOOTSTRAPPED,
                created_by=owner,
            )
            WireGuardPeer.objects.create(
                tenant_id=tenant.id, router=None, enrollment=enrollment2,
                allowed_ip=enrollment2.tunnel_ip, public_key="wgpub-pa02-pro2",
                desired_revision=1, state=WireGuardPeer.State.PENDING,
            )
        job2 = engine.create_job(
            tenant_id=tenant.id, kind="verify_api_ssl",
            payload={"enrollment_id": str(enrollment2.id)},
        )
        Membership.objects.filter(user=owner, tenant=tenant).update(
            revoked_at=tz.now()
        )
        claimed2 = engine.claim_next()
        r2 = engine.run_claimed(claimed2)
        assert r2.state == JobState.FAILED and r2.error_code == "authority_denied"


# ---------------------------------------------------------------------------
# J20-A07 — HTTP authority, handler/verifier fail-closed


class TestHttpAuthorityAndVerifier:
    def _client(self, user, tenant_id: str, *, reauth: bool = True):
        from rest_framework.test import APIClient

        client = APIClient(enforce_csrf_checks=False)
        client.force_login(user)
        session = client.session
        session["active_tenant_id"] = str(tenant_id)
        session["auth_at"] = _time_time()
        if reauth:
            session["reauth_until"] = (
                tz.now()
                + tz.timedelta(minutes=10)
            ).isoformat()
        session.save()
        return client

    def test_detail_requires_underlying_permission(self):
        """Viewer (customers.read saja) tidak boleh detail job operasi
        backup; owner boleh; lintas tenant tetap 404 generik."""
        tenant, owner = _make_tenant("rtrw-pa02-a07a")
        job = engine.create_job(tenant_id=tenant.id, kind="backup_router", actor=owner)
        viewer = User.objects.create_user(
            email="pa002-viewer@test.local", full_name="Viewer",
            password=_TEST_PASSWORD, is_active=True,
        )
        Membership.objects.create(user=viewer, tenant=tenant, role=Role.VIEWER)
        resp_owner = self._client(owner, tenant.id).get(f"/api/v1/jobs/{job.id}")
        assert resp_owner.status_code == 200
        resp_viewer = self._client(viewer, tenant.id).get(f"/api/v1/jobs/{job.id}")
        assert resp_viewer.status_code == 403
        # Tenant lain → 404 generik.
        tenant_b, owner_b = _make_tenant("rtrw-pa02-a07b")
        resp_foreign = self._client(owner_b, tenant_b.id).get(f"/api/v1/jobs/{job.id}")
        assert resp_foreign.status_code == 404

    def test_retry_cancel_sensitive_kind_requires_permission_and_stepup(self):
        """Job cutover (radius.cutover, sensitif): retry/cancel butuh izin itu
        + step-up reauth; teknisi tanpa izin → 403; owner tanpa reauth → 403."""
        tenant, owner = _make_tenant("rtrw-pa02-a07c")
        technician = User.objects.create_user(
            email="pa002-tech@test.local", full_name="Tech",
            password=_TEST_PASSWORD, is_active=True,
        )
        Membership.objects.create(user=technician, tenant=tenant, role=Role.TECHNICIAN)
        job = engine.create_job(tenant_id=tenant.id, kind="radius_cutover_step", actor=owner)
        Job.objects.filter(id=job.id).update(state=JobState.FAILED, retryable=True, error_code="uji")

        # Teknisi punya banyak izin tapi TIDAK radius.cutover → 403.
        resp_tech = self._client(technician, tenant.id).post(f"/api/v1/jobs/{job.id}/retry")
        assert resp_tech.status_code == 403
        # Owner tanpa reauth (step-up sensitif) → 403.
        resp_no_reauth = self._client(owner, tenant.id, reauth=False).post(f"/api/v1/jobs/{job.id}/retry")
        assert resp_no_reauth.status_code == 403
        # Owner dengan reauth → 202 job baru.
        resp_ok = self._client(owner, tenant.id).post(f"/api/v1/jobs/{job.id}/retry")
        assert resp_ok.status_code == 202

        # Cancel sensitif juga step-up: tanpa reauth 403, dengan reauth 204.
        job2 = engine.create_job(tenant_id=tenant.id, kind="radius_cutover_step", actor=owner)
        resp_c1 = self._client(owner, tenant.id, reauth=False).post(f"/api/v1/jobs/{job2.id}/cancel")
        assert resp_c1.status_code == 403
        resp_c2 = self._client(owner, tenant.id).post(f"/api/v1/jobs/{job2.id}/cancel", {"reason": "uji"})
        assert resp_c2.status_code == 204

    def test_router_replace_requires_release_permission(self):
        """Penggantian melepas router lama → routers.release (ARCHITECTURE §5):
        teknisi (punya routers.enroll, TIDAK release) ditolak 403."""
        from domains.network.models import Router

        tenant, owner = _make_tenant("rtrw-pa02-a07d")
        technician = User.objects.create_user(
            email="pa02-tech2@test.local", full_name="Tech2",
            password=_TEST_PASSWORD, is_active=True,
        )
        Membership.objects.create(user=technician, tenant=tenant, role=Role.TECHNICIAN)
        with tenant_scope(tenant.id):
            router = Router.objects.create(
                tenant_id=tenant.id, display_name="R Replace", router_code="PA02-REPL",
                tunnel_ip="100.127.9.9", mode=Router.Mode.MANAGED, credential_ref="enc:t",
            )
        resp = self._client(technician, tenant.id).post(
            f"/api/v1/tenants/{tenant.id}/routers/{router.id}/replace",
            headers={"Idempotency-Key": "pa02-replace-1"},
        )
        assert resp.status_code == 403, "routers.enroll saja tidak boleh melepas router"
        # Owner (routers.release) diterima.
        resp_owner = self._client(owner, tenant.id).post(
            f"/api/v1/tenants/{tenant.id}/routers/{router.id}/replace",
            headers={"Idempotency-Key": "pa02-replace-2"},
        )
        assert resp_owner.status_code == 202

    def test_missing_handler_fails_closed(self):
        """Kind tanpa handler → gagal jujur handler_missing, TIDAK sukses
        kosong."""
        tenant, owner = _make_tenant("rtrw-pa02-a07e")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_nohandler", actor=owner)
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED
        assert r.error_code == "handler_missing"

    def test_negative_verifier_never_succeeds(self):
        """Verifier mengembalikan {ok: False} → job FAILED verification_failed,
        bukan succeeded."""
        tenant, owner = _make_tenant("rtrw-pa02-a07f")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_negverify", actor=owner)
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)
        assert r.state == JobState.FAILED
        assert r.error_code == "verification_failed"

    def test_cutover_pending_observation_still_succeeds_honestly(self):
        """Preservasi semantik pending_observation: job sukses dengan hasil
        menunggu jendela observasi — TANPA klaim mutasi perangkat selesai."""
        from domains.customers.services import provision_service_draft
        from domains.radius.models import CutoverRun

        tenant, owner = _make_tenant("rtrw-pa02-a07g")
        router = _make_router(tenant, code="PA02-CUT", ip="100.127.9.10")
        with tenant_scope(tenant.id):
            provision_service_draft(
                tenant,
                {"customer_name": "P Cut", "username": "pa02.cut", "password": "pw-cut-12345678",
                 "kind": "pppoe", "package_name": "10M/5M", "router_id": str(router.id)},
            )
            from domains.backups.models import BackupArtifact
            from domains.radius.projection import project_nas
            from domains.radius.reconciler import mark_applied

            project_nas(router)
            mark_applied(router)
            BackupArtifact.objects.create(
                tenant_id=tenant.id, router=router, category="prechange",
                generation=1, state="committed", file_name="b.backup",
            )
        job = engine.create_job(
            tenant_id=tenant.id, kind="radius_cutover_step", actor=owner, router=router,
            payload={"router_id": str(router.id)},
        )
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed)
        assert r.state == JobState.SUCCEEDED
        with tenant_scope(tenant.id):
            # Baca hasil via query segar (job.detail bisa instance ter-cache
            # basi — pola repo: refresh/GET eksplisit).
            from domains.jobs.models import JobDetail

            detail_result = JobDetail.objects.get(job_id=job.id).result
        assert detail_result.get("waiting") == "observation_window"
        assert detail_result.get("state") == CutoverRun.State.PENDING_OBSERVATION


# ---------------------------------------------------------------------------
# Koreksi review independen (REV-2011-01/03/04/09) — failing-before/passing-after


class TestReviewerCorrections:
    def test_retry_origin_blocked_while_child_uncertain(self):
        """REV-2011-01: kandidat retry yang UNCERTAIN tetap dianggap aktif —
        retry kedua pada origin ditolak 409 sampai outcome terselesaikan
        (tidak ada efek logis ganda dari hasil tak diketahui)."""
        tenant, owner = _make_tenant("rtrw-pa02-rev01")
        origin = engine.create_job(tenant_id=tenant.id, kind="_test_uncertain_send", actor=owner)
        Job.objects.filter(id=origin.id).update(state=JobState.FAILED, retryable=True, error_code="uji")
        child = engine.retry_job(Job.objects.get(id=origin.id), actor=owner)
        claimed = engine.claim_next()
        assert str(claimed.id) == str(child.id)
        r = engine.run_claimed(claimed)
        assert r.state == JobState.UNCERTAIN  # kirim pertama, outcome tak diketahui

        # Retry origin LAGI saat kandidat masih uncertain → ditolak.
        with pytest.raises(ValueError):
            engine.retry_job(Job.objects.get(id=origin.id), actor=owner)
        assert _send(child.id) == 1, "tidak ada efek kedua"

        # Setelah resolve (readback membuktikan belum diterapkan) dan kandidat
        # tuntas, origin boleh dipakai lagi bila masih diperlukan.
        engine.resolve_uncertain(Job.objects.get(id=child.id), applied=False)
        reclaimed = engine.claim_next()
        finished = engine.run_claimed(reclaimed)
        assert finished.state == JobState.SUCCEEDED
        assert _send(child.id) == 2  # kirim ulang sah SETELAH bukti belum terapkan

    def test_resolve_not_applied_refused_while_old_writer_active(self):
        """REV-2011-03: readback 'belum diterapkan' tidak dipercaya selama
        penulis lama masih memegang router (send in-flight bisa mendarat
        setelah readback) — resolve menolak sampai penulis terbukti berhenti."""
        tenant, owner = _make_tenant("rtrw-pa02-rev03")
        router = _make_router(tenant, code="PA02-REV3", ip="100.127.10.1")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner, router=router)
        claimed = engine.claim_next()
        gate = threading.Event()
        _RouterSendHandler.gate = gate
        _RouterSendHandler.gate_job = str(job.id)
        results: dict = {}
        t = _run_in_thread(claimed, results)
        try:
            assert _wait_up_to(10, lambda: _send(job.id) == 1)
            # Paksa uncertain sementara penulis lama masih hidup (memegang lock).
            from django.utils import timezone as tz2

            Job.objects.filter(id=job.id).update(
                state=JobState.UNCERTAIN, lease_token=None, lease_expires_at=None,
                error_code="lease_expired",
            )
            with pytest.raises(ValueError, match="writer_active"):
                engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        finally:
            gate.set()
        t.join(timeout=30)
        assert not t.is_alive()
        # Penulis lama selesai → resolve kini diterima.
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        assert resolved.state == JobState.RETRY_WAIT

    def test_progress_renews_lease_for_long_work(self):
        """REV-2011-04: laporan kemajuan sekaligus memperpanjang lease —
        handler yang melapor per fase tidak dipaksa uncertain oleh reconcile
        worker lain (renewal pekerjaan panjang)."""
        tenant, owner = _make_tenant("rtrw-pa02-rev04")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        ctx = engine.JobContext(job=claimed, payload={})
        before = Job.objects.get(id=job.id).lease_expires_at
        assert ctx.progress(phase="fase", done=1, total=10) is True
        after = Job.objects.get(id=job.id).lease_expires_at
        assert after >= before, "progress harus memperpanjang lease"
        # Lease masih hidup → reconcile tidak menyentuh.
        assert engine.reconcile_expired_leases() == 0

    def test_drain_before_effect_holds_job_requeueable(self):
        """REV-2011-09: sinyal stop sebelum efek (preflight) → job ditahan di
        retry_wait drained_before_effect, nol efek, dapat diklaim ulang."""
        tenant, owner = _make_tenant("rtrw-pa02-rev09")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_router_send", actor=owner)
        claimed = engine.claim_next()
        r = engine.run_claimed(claimed, stop_check=lambda: True)
        assert r.state == JobState.RETRY_WAIT
        assert r.error_code == "drained_before_effect"
        assert _send(job.id) == 0, "nol efek saat ditahan sebelum execute"
        reclaimed = engine.claim_next()
        assert reclaimed is not None and str(reclaimed.id) == str(job.id)
        finished = engine.run_claimed(reclaimed)
        assert finished.state == JobState.SUCCEEDED
        assert _send(job.id) == 1
