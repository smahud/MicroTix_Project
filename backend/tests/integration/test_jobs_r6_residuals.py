"""Tes integrasi task0020 R6 — residual koreksi R5 (changes_requested).

Regresi kompak di suite CI untuk koreksi temuan controller atas koreksi R5
(report/controller/20261118T172344Z-0020-r5-correction-review.md):

- REV-1811-02 (P2 PARTIAL): settlement no-effect final/nonfinal yang lease
  kedaluwarsa SELAMA UPDATE menunggu lock baris job tetap ditolak — expiry
  dinilai SEGAR SETELAH kunci diperoleh (step-0 lock-first); row tetap
  EXECUTING dengan token/epoch awal tanpa error sampai reconciler. Kontrol
  lease valid tetap menyelesaikan FAILED/RETRY_WAIT sekali.
- REV-1711-01 (P1 PARTIAL): watchdog tidak menghidupkan kembali lease yang
  kedaluwarsa SELAMA UPDATE menunggu lock baris job (expiry lama
  dipertahankan untuk reconciler); enrollment WG yang lease kedaluwarsa
  SELAMA pemeriksaan referensial FK deferred menunggu kunci baris tenant
  commit NOL efek domain (Router 0, kredensial PENDING, enrollment
  VERIFYING) — akuisisi kunci referensial selesai SEBELUM fence akhir.
- REV-1711-04 (P1 PARTIAL): readback negatif terikat urutan bukti
  stop→observasi pada job/epoch sama — observasi pra-stop (attestasi
  waktu < receipt) DITOLAK; observasi pasca-stop sah membuka pemulihan
  tanpa kirim duplikat; attestasi tanpa receipt ditahan fail-closed.
- REV-1711-05 (P1 PARTIAL): perubahan authority (penonaktifan akun /
  pencabutan membership) yang ter-commit SELAMA unit efek router_release /
  router_replace menunggu lock domain membatalkan unit pada batas commit —
  router tetap aktif, kredensial/NAS tetap, NOL enrollment pengganti, job
  gagal authority_denied; kontrol berizin commit tepat sekali.

Probe controller R1–R4 (FROZEN), regresi R4/R5 dan probe lock-wait
controller tetap bukti acceptance; tes ini pin invariant koreksi R6 agar
dijaga oleh CI `pytest tests`.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import timedelta
from threading import Event
from time import monotonic

import pytest
from django.db import connection, connections, transaction
from django.test import override_settings
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.engine import JobError
from domains.jobs.models import Job, JobState
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer
from domains.tenancy.models import Membership, Role, Tenant

from tests.integration.test_jobs_r5_residuals import (
    _ConnectivityAdapter,
    _credential_wait_setup,
)

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
            "domains.radius",
            "domains.backups",
            "domains.subscriptions",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Helper pola probe controller lock-wait (dua koneksi + pg_blocking_pids)

def backend_pid():
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        return cursor.fetchone()[0]


def wait_for_blocked(worker_pid, blocker_pid, table=None):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_stat_clear_snapshot()")
            cursor.execute(
                "SELECT %s = ANY(pg_blocking_pids(pid)), wait_event_type, query "
                "FROM pg_stat_activity WHERE pid=%s", [blocker_pid, worker_pid]
            )
            row = cursor.fetchone()
        if row and row[0]:
            assert row[1] == "Lock", row[1]
            if table is not None:
                assert table in row[2], row[2]
            return row[2]
        Event().wait(0.01)
    pytest.fail("Expected a PostgreSQL lock wait on the test transaction")


def wait_until_expired(expiry):
    while (remaining := (expiry - timezone.now()).total_seconds()) > 0:
        Event().wait(min(remaining, 0.025))
    assert timezone.now() >= expiry


def start_worker(action):
    result = {}

    def run():
        try:
            result["return"] = action()
        except BaseException as exc:  # noqa: BLE001 — hasil thread direkam apa adanya
            result["exception"] = exc
        finally:
            connections.close_all()

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    return worker, result


def finish_worker(worker, result):
    worker.join(10)
    assert not worker.is_alive()
    assert "exception" not in result, result
    assert "return" in result, result
    return result["return"]


def _tenant_actor(tag: str):
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r6-{tag}-{suffix}@test.local", full_name=f"R6 {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"R6 {tag}", namespace=f"rtrw-r6-{tag}-{suffix}"[:32]
    )
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    return tenant, actor


def _make_router(tenant, code: str, ip: str) -> Router:
    with tenant_scope(tenant.id):
        return Router.objects.create(
            tenant_id=tenant.id, display_name=code, router_code=code[:16],
            tunnel_ip=ip, mode=Router.Mode.MANAGED, credential_ref="enc:r6-controlled",
        )


# ---------------------------------------------------------------------------
# REV-1811-02 — settlement menilai lease SETELAH lock baris job

class TestSettlementLeaseAfterJobRowLockWait:
    @pytest.mark.parametrize("max_attempts", [1, 2], ids=["final", "nonfinal"])
    @pytest.mark.parametrize("cross_expiry", [False, True], ids=["valid", "expired"])
    def test_settlement_lease_checked_after_job_row_lock(self, monkeypatch, max_attempts, cross_expiry):
        """Kasus probe controller: settlement UPDATE menunggu lock baris job
        yang dipegang transaksi lain; lease kedaluwarsa SELAMA tunggu →
        settlement DITOLAK (row tetap EXECUTING, token/epoch awal, tanpa
        error). Kontrol lease valid → FAILED(final)/RETRY_WAIT(nonfinal)
        dengan error dan token dilepas."""
        tag = "expired" if cross_expiry else "valid"
        tenant, actor = _tenant_actor(f"settle-{tag}-{max_attempts}")
        entered, finish = Event(), Event()
        observed = {}

        class ControlledNoEffect(engine.JobHandler):
            kind = "_test_r6_settlement_wait"

            def execute(self, ctx):
                observed["pid"] = backend_pid()
                entered.set()
                assert finish.wait(10)
                raise engine.JobError(code="controlled_no_effect", retryable=True, no_effect=True)

            def verify(self, ctx):
                pytest.fail("job no-effect tidak boleh masuk verifier")

        handler = ControlledNoEffect()
        monkeypatch.setitem(engine._REGISTRY, handler.kind, handler)
        monkeypatch.setattr(engine, "HEARTBEAT_S", 30)  # renewal tidak menyamarkan expiry
        job = engine.create_job(tenant_id=tenant.id, kind=handler.kind, actor=actor)
        Job.objects.filter(id=job.id).update(max_attempts=max_attempts)
        claimed = engine.claim_next()
        assert claimed.id == job.id
        initial_token, initial_epoch = claimed.lease_token, claimed.lease_epoch
        worker, result = start_worker(lambda: engine.run_claimed(claimed))

        try:
            assert entered.wait(5)
            expiry = timezone.now() + timedelta(seconds=2.5)
            assert Job.objects.filter(id=job.id).update(lease_expires_at=expiry) == 1
            with transaction.atomic():
                locked = Job.objects.select_for_update().get(id=job.id)
                assert (locked.state, locked.lease_token) == (JobState.EXECUTING, initial_token)
                finish.set()
                query = wait_for_blocked(observed["pid"], backend_pid(), "jobs_job")
                assert timezone.now() < expiry
                if cross_expiry:
                    wait_until_expired(expiry)
        finally:
            finish.set()
            returned = finish_worker(worker, result)

        fresh = Job.objects.get(id=job.id)
        assert returned.state == fresh.state
        if cross_expiry:
            assert (fresh.state, fresh.error_code, fresh.lease_token, fresh.lease_epoch) == (
                JobState.EXECUTING, None, initial_token, initial_epoch,
            ), "lease kedaluwarsa selama tunggu lock: settlement milik reconciler"
        else:
            assert fresh.state == (JobState.FAILED if max_attempts == 1 else JobState.RETRY_WAIT)
            assert fresh.error_code == "controlled_no_effect" and fresh.lease_token is None


# ---------------------------------------------------------------------------
# REV-1711-01 — watchdog tidak menghidupkan lease kedaluwarsa pasca tunggu

class TestWatchdogLeaseAfterJobRowLockWait:
    def test_watchdog_cannot_extend_expired_lease_after_job_row_lock(self, monkeypatch):
        """Kasus probe controller: pembaruan watchdog menunggu lock baris job;
        lease kedaluwarsa SELAMA tunggu → expiry LAMA dipertahankan (tidak
        dihidupkan kembali), state/token tidak berubah."""
        tenant, actor = _tenant_actor("watchdog")
        job = engine.create_job(tenant_id=tenant.id, kind="_test_r6_watchdog", actor=actor)
        claimed = engine.claim_next()
        assert claimed.id == job.id
        ready, stop, done = Event(), Event(), Event()
        observed = {}
        expiry = timezone.now() + timedelta(seconds=2.5)
        assert Job.objects.filter(id=job.id).update(
            state=JobState.EXECUTING, lease_expires_at=expiry
        ) == 1
        ctx = engine.JobContext(Job.objects.get(id=job.id))
        monkeypatch.setattr(engine, "HEARTBEAT_S", 0.05)

        def run_watchdog():
            observed["pid"] = backend_pid()
            ready.set()
            engine._heartbeat_watchdog(ctx, stop, done)

        worker = result = None
        try:
            with transaction.atomic():
                Job.objects.select_for_update().get(id=job.id)
                worker, result = start_worker(run_watchdog)
                assert ready.wait(5)
                query = wait_for_blocked(observed["pid"], backend_pid(), "jobs_job")
                assert timezone.now() < expiry
                wait_until_expired(expiry)
                stop.set()
        finally:
            stop.set()
            if worker is not None:
                finish_worker(worker, result)

        fresh = Job.objects.get(id=job.id)
        assert done.is_set()
        assert fresh.lease_expires_at == expiry, (
            "watchdog tidak boleh memperpanjang lease yang kedaluwarsa selama tunggu lock"
        )
        assert fresh.state == JobState.EXECUTING
        assert fresh.lease_token == claimed.lease_token


# ---------------------------------------------------------------------------
# REV-1711-01 — enrollment: kunci referensial tenant sebelum fence akhir

class TestEnrollmentLeaseCoversDeferredForeignKeyWait:
    def _run(self, monkeypatch, *, cross_expiry: bool):
        tenant, _actor, enrollment, credential, job = _credential_wait_setup(
            "fk-wait", "wireguard"
        )
        claimed = engine.claim_next()
        assert claimed.id == job.id
        active, finish = Event(), Event()
        worker = result = None
        observed = {}
        monkeypatch.setattr(
            "adapters.routeros.factory.active_routeros_adapter",
            lambda: _ConnectivityAdapter(active, finish, observed),
        )
        # Renewal watchdog tidak boleh menyamarkan expiry yang dilewati.
        monkeypatch.setattr(engine, "HEARTBEAT_S", 30)

        with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
            worker, result = start_worker(lambda: engine.run_claimed(claimed))
            try:
                assert active.wait(5)
                expiry = timezone.now() + timedelta(seconds=2.5)
                assert Job.objects.filter(id=job.id).update(lease_expires_at=expiry) == 1
                with transaction.atomic():
                    Tenant.objects.select_for_update().get(id=tenant.id)
                    finish.set()
                    # Dengan koreksi R6, worker menunggu kunci referensial
                    # tenant (FOR KEY SHARE) DI DALAM unit — SEBELUM fence
                    # akhir; bukan menunggu FK deferred di COMMIT.
                    query = wait_for_blocked(observed["worker"], backend_pid(), "tenancy_tenant")
                    assert timezone.now() < expiry
                    if cross_expiry:
                        wait_until_expired(expiry)
            finally:
                finish.set()
                returned = finish_worker(worker, result)

        with tenant_scope(tenant.id):
            enrollment.refresh_from_db()
            credential.refresh_from_db()
            router_count = Router.objects.filter(tenant=tenant).count()
        final = Job.objects.get(id=job.id)
        return returned, final, router_count, credential, enrollment

    def test_lease_expiry_during_tenant_referential_wait_cancels_unit(self, monkeypatch):
        """Kasus probe controller: lease kedaluwarsa SELAMA unit efek
        menunggu kunci baris tenant (titik pemeriksaan FK deferred) → NOL
        efek domain: Router 0, kredensial PENDING, enrollment VERIFYING,
        job tidak sukses (row menunggu reconciler)."""
        returned, final, router_count, credential, enrollment = self._run(
            monkeypatch, cross_expiry=True
        )
        assert returned.state == final.state
        assert (router_count, credential.state, enrollment.status) == (
            0, WireGuardPeer.State.PENDING, RouterEnrollment.Status.VERIFYING,
        ), "lease basi pada titik referensial tenant tidak boleh commit efek domain"
        assert final.state != JobState.SUCCEEDED
        assert final.state == JobState.EXECUTING and final.error_code is None

    def test_valid_lease_under_same_tenant_wait_commits_once(self, monkeypatch):
        """Kontrol: kontensi kunci tenant yang sama dengan lease tetap valid
        → unit menyelesaikan akuisisi referensial lalu commit tepat sekali
        (pengerasan tidak memblokir jalur sah)."""
        returned, final, router_count, credential, enrollment = self._run(
            monkeypatch, cross_expiry=False
        )
        assert returned.state == final.state == JobState.SUCCEEDED
        assert router_count == 1
        assert credential.state == WireGuardPeer.State.APPLIED
        assert enrollment.status == RouterEnrollment.Status.COMPLETED


# ---------------------------------------------------------------------------
# REV-1711-04 — readback negatif terikat urutan bukti stop→observasi

class TestNegativeReadbackStopProofOrdering:
    def _uncertain_with_receipt(self, monkeypatch, *, sends):
        tenant, actor = _tenant_actor("readback")
        router = _make_router(tenant, "R6-RB1", "100.126.10.1")
        parent_sends = sends

        class Handler(engine.JobHandler):
            kind = "_test_r6_readback_order"

            def execute(self, ctx):
                parent_sends.append(str(ctx.job.id))
                if len(parent_sends) == 1:
                    # Attempt pertama gagal tanpa no_effect → uncertain;
                    # receipt ditulis finally. Attempt penerus sukses.
                    raise JobError(code="link_flap", retryable=True)
                return {"sent": True}

            def verify(self, ctx):
                return {"ok": True}

        monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
        job = engine.create_job(
            tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router
        )
        claimed = engine.claim_next()
        assert claimed is not None and claimed.id == job.id
        assert engine.run_claimed(claimed).state == JobState.UNCERTAIN
        fresh = Job.objects.get(id=job.id)
        assert fresh.writer_ended_at is not None, "receipt attempt in-process wajib ada"
        return job, fresh, actor, router

    def test_prestop_observation_is_rejected_and_holds(self, monkeypatch):
        """Observasi readback negatif PRA-STOP (attestasi < receipt) tidak
        melepas hold: row tetap UNCERTAIN, tidak ada antrian ulang."""
        sends: list[str] = []
        job, uncertain, _actor, _router = self._uncertain_with_receipt(monkeypatch, sends=sends)
        prestop = uncertain.writer_ended_at - timedelta(seconds=5)
        with pytest.raises(ValueError, match="readback_before_stop"):
            engine.resolve_uncertain(
                Job.objects.get(id=job.id), applied=False, readback_observed_at=prestop
            )
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.UNCERTAIN, "hold dipertahankan untuk observasi pra-stop"
        assert sends == [str(job.id)], "nol kirim tambahan selama hold"

    def test_poststop_observation_opens_recovery_without_duplicate_send(self, monkeypatch):
        """Observasi PASCA-STOP (attestasi >= receipt, epoch sama) sah
        membuka pemulihan: retry_wait → claim ulang → kirim penerus TEPAT
        sekali (resolve sendiri nol kirim)."""
        sends: list[str] = []
        job, uncertain, _actor, _router = self._uncertain_with_receipt(monkeypatch, sends=sends)
        poststop = uncertain.writer_ended_at + timedelta(seconds=1)
        sends_before = len(sends)
        resolved = engine.resolve_uncertain(
            Job.objects.get(id=job.id), applied=False, readback_observed_at=poststop
        )
        assert resolved.state == JobState.RETRY_WAIT
        assert len(sends) == sends_before, "resolve sendiri tidak mengirim apa pun"
        Job.objects.filter(id=job.id).update(available_at=timezone.now())
        reclaimed = engine.claim_next()
        assert reclaimed is not None and reclaimed.id == job.id
        assert engine.run_claimed(reclaimed).state == JobState.SUCCEEDED
        assert sends.count(str(job.id)) == 2, "kirim penerus tepat satu kali (nol duplikat)"

    def test_naive_attestation_rejected(self, monkeypatch):
        """Attestasi waktu naive tidak dapat dinilai → ditolak (hold)."""
        sends: list[str] = []
        job, uncertain, _actor, _router = self._uncertain_with_receipt(monkeypatch, sends=sends)
        import datetime as _dt

        naive = _dt.datetime.utcnow()
        with pytest.raises(ValueError, match="readback_unordered"):
            engine.resolve_uncertain(
                Job.objects.get(id=job.id), applied=False, readback_observed_at=naive
            )
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN

    def test_explicit_attestation_without_receipt_fails_closed(self, monkeypatch):
        """Attestasi eksplisit TANPA receipt (bukti liveness saja) → urutan
        tidak terikat → ditahan; panggilan default (observasi = saat resolve,
        setelah bukti stop diperiksa) tetap sah membuka antrian ulang."""
        sends: list[str] = []
        job, uncertain, _actor, _router = self._uncertain_with_receipt(monkeypatch, sends=sends)
        # Simulasi receipt gagal tertulis (sesi DB mati saat finally) pada
        # epoch yang sama — baris uncertain dengan identitas penulis proses ini.
        assert Job.objects.filter(id=job.id, lease_epoch=uncertain.lease_epoch).update(
            writer_ended_at=None
        ) == 1
        with pytest.raises(ValueError, match="readback_unbound"):
            engine.resolve_uncertain(
                Job.objects.get(id=job.id), applied=False,
                readback_observed_at=timezone.now(),
            )
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        # Default tanpa attestasi: bukti stop diperiksa DI DALAM panggilan
        # sebelum observasi diattestasi terjadi (urutan terjalin) → diterima.
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        assert resolved.state == JobState.RETRY_WAIT


# ---------------------------------------------------------------------------
# REV-1711-05 — authority pada batas efek release/replace

def _release_replace_setup(tag: str, kind: str):
    tenant, actor = _tenant_actor(tag)
    router = _make_router(tenant, f"R6-{tag[:4].upper()}", f"100.127.{uuid.uuid4().int % 200 + 10}.1")
    with tenant_scope(tenant.id):
        WireGuardPeer.objects.create(
            tenant=tenant, router=router, allowed_ip=router.tunnel_ip,
            public_key=f"r6-{uuid.uuid4().hex[:10]}", state=WireGuardPeer.State.APPLIED,
        )
    job = engine.create_job(
        tenant_id=tenant.id, kind=kind, actor=actor, router=router,
        payload={"router_id": str(router.id)},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    return tenant, actor, router, job, claimed


def _run_release_replace_wait(monkeypatch, tag: str, kind: str, *, mutate_during_wait):
    """Worker memasuki unit efek release/replace; UPDATE router diblokir lock
    baris router koneksi lain; mutasi authority ter-commit SELAMA tunggu,
    lalu lock dilepas → klaim hasil akhir unit + efek domain."""
    tenant, actor, router, job, claimed = _release_replace_setup(tag, kind)
    locked, release_lock = Event(), Event()
    outcomes: dict = {}
    errors: list = []
    lock_outcomes: dict = {}
    pids: dict = {}

    def worker():
        from django.db import close_old_connections

        close_old_connections()
        try:
            final = engine.run_claimed(Job.objects.get(id=claimed.id))
            outcomes.update(state=final.state, error=final.error_code)
        except BaseException as exc:  # noqa: BLE001 — hasil thread direkam apa adanya
            errors.append(repr(exc))
        finally:
            connections.close_all()

    def locker():
        from django.db import close_old_connections

        close_old_connections()
        try:
            with tenant_scope(tenant.id), transaction.atomic():
                Router.objects.select_for_update().get(id=router.id)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids["locker"] = cursor.fetchone()[0]
                locked.set()
                assert release_lock.wait(25), "lock router tidak dilepas"
            lock_outcomes["committed"] = True
        except BaseException as exc:  # noqa: BLE001
            lock_outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    lock_thread = threading.Thread(target=locker, name=f"r6-lock-{tag}")
    lock_thread.start()
    assert locked.wait(15), "baris router tidak terkunci"
    worker_thread = threading.Thread(target=worker, name=f"r6-{tag}")
    worker_thread.start()
    blocked = False
    observed_query = ""
    try:
        deadline = monotonic() + 20
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pid, query FROM pg_stat_activity "
                    "WHERE %s = ANY(pg_blocking_pids(pid))",
                    [pids["locker"]],
                )
                rows = cursor.fetchall()
            if rows:
                blocked = True
                observed_query = rows[0][1]
                break
            time.sleep(0.01)
        assert blocked, "PG harus mengamati worker menunggu lock baris router"
        assert "network_router" in observed_query, observed_query
        # Mutasi authority ter-commit SELAMA UPDATE sensitif tertahan —
        # setelah seluruh pembacaan authority entry (preflight + batas efek).
        mutate_during_wait(tenant=tenant, actor=actor, job_id=claimed.id)
    finally:
        release_lock.set()
        lock_thread.join(20)
        worker_thread.join(25)
    assert not lock_thread.is_alive() and not worker_thread.is_alive(), "partisipan terbatas"
    assert lock_outcomes == {"committed": True}, lock_outcomes
    assert not errors and "state" in outcomes, {"errors": errors, "outcomes": outcomes}
    with tenant_scope(tenant.id):
        router.refresh_from_db()
        peers = list(WireGuardPeer.objects.filter(router=router))
        enrollments = RouterEnrollment.objects.filter(tenant=tenant).count()
    return {
        "outcomes": outcomes, "router": router, "peers": peers,
        "enrollments": enrollments, "job_id": claimed.id,
        "observed_query": observed_query,
    }


class TestReleaseReplaceAuthorityBoundary:
    def test_release_deactivation_during_router_wait_cancels_unit(self, monkeypatch):
        """REV-1711-05 (R6): akun dinonaktifkan SELAMA unit release menunggu
        lock baris router → guard authority terkunci pada batas commit
        membatalkan unit: router tetap aktif (released_at None), kredensial
        peer tetap APPLIED, job gagal authority_denied."""

        def deactivate(*, tenant, actor, job_id):
            assert User.objects.filter(id=actor.id).update(is_active=False) == 1

        result = _run_release_replace_wait(
            monkeypatch, "reldeact", "router_release", mutate_during_wait=deactivate
        )
        assert result["router"].released_at is None, "router tetap aktif"
        assert all(p.state == WireGuardPeer.State.APPLIED for p in result["peers"])
        assert result["outcomes"]["state"] == JobState.FAILED
        assert result["outcomes"]["error"] == "authority_denied"
        fresh_job = Job.objects.get(id=result["job_id"])
        assert fresh_job.state == JobState.FAILED and fresh_job.error_code == "authority_denied"

    def test_release_control_commits_once(self, monkeypatch):
        """Kontrol: authority sah (tanpa mutasi) → release commit tepat
        sekali: released_at terpasang, peer REMOVED, job SUCCEEDED."""

        def no_mutation(*, tenant, actor, job_id):
            return None

        result = _run_release_replace_wait(
            monkeypatch, "relok", "router_release", mutate_during_wait=no_mutation
        )
        assert result["router"].released_at is not None
        assert all(p.state == WireGuardPeer.State.REMOVED for p in result["peers"])
        assert result["outcomes"]["state"] == JobState.SUCCEEDED
        assert result["outcomes"]["error"] is None

    def test_replace_membership_revocation_during_router_wait_cancels_unit(self, monkeypatch):
        """REV-1711-05 (R6): membership dicabut SELAMA unit replace menunggu
        lock baris router → unit dibatalkan pada batas commit: router lama
        tetap aktif, kredensial tetap, NOL enrollment pengganti, job gagal
        authority_denied."""

        def revoke(*, tenant, actor, job_id):
            assert Membership.objects.filter(user=actor, tenant=tenant).update(
                revoked_at=timezone.now()
            ) == 1

        result = _run_release_replace_wait(
            monkeypatch, "reprevok", "router_replace", mutate_during_wait=revoke
        )
        assert result["router"].released_at is None, "router lama tetap aktif"
        assert all(p.state == WireGuardPeer.State.APPLIED for p in result["peers"])
        assert result["enrollments"] == 0, "nol enrollment pengganti baru"
        assert result["outcomes"]["state"] == JobState.FAILED
        assert result["outcomes"]["error"] == "authority_denied"

    def test_replace_control_commits_once(self, monkeypatch):
        """Kontrol: authority sah → replace commit tepat sekali: router lama
        terlepas, enrollment pengganti diterbitkan, job SUCCEEDED."""

        def no_mutation(*, tenant, actor, job_id):
            return None

        result = _run_release_replace_wait(
            monkeypatch, "repok", "router_replace", mutate_during_wait=no_mutation
        )
        assert result["router"].released_at is not None
        assert result["enrollments"] == 1, "enrollment pengganti diterbitkan"
        assert result["outcomes"]["state"] == JobState.SUCCEEDED
        assert result["outcomes"]["error"] is None
