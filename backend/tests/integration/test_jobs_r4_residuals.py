"""Tes integrasi task0020 R4 — residual lifecycle/authority/enrollment.

Regresi kompak di suite CI untuk koreksi temuan controller R4
(report/controller/20261118T025143Z-0020-r4-review.md):

- REV-1811-02: attempt final dengan bukti EKSPLISIT no-effect mencapai
  FAILED (tidak lagi tersangkut UNCERTAIN oleh CAS lease-valid yang mustahil
  dipenuhi setelah lease dilepas); attempt nonfinal tetap backoff RETRY_WAIT;
  worker basi tidak dapat menimpa state terminal/recovery lewat jalur baru.
- REV-1711-04: resolve_uncertain(applied=False) menolak membuka antrian ulang
  bila penulis attempt uncertain masih hidup DI PROSES LAIN (identitas
  writer dipersist + liveness /proc starttime), mengizinkan pemulihan
  positif hanya setelah penulis terverifikasi berhenti, dan menahan status
  yang tidak dapat diverifikasi (baris legacy tanpa identitas penulis).
- REV-1711-05: pencabutan membership yang ter-commit SELAMA worker menunggu
  lock baris kredensial membatalkan seluruh unit efek sebelum commit —
  Router tidak dibuat, kredensial tetap PENDING (guard batas commit).

Probe controller R4 (FROZEN, 4 assertion) tetap bukti acceptance; tes ini
pin invariant yang sama agar dijaga oleh CI `pytest tests`.
"""
from __future__ import annotations

import multiprocessing
import os
import signal
import uuid

import pytest
from django.conf import settings
from django.db import connection, connections
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.engine import JobError
from domains.jobs.models import Job, JobState
from domains.network.models import Router
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
            "domains.radius",
            "domains.backups",
            "domains.subscriptions",
        ],
    ),
]


def _tenant_actor_router(tag: str):
    from domains.network.models import Router as NetRouter

    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r4r-{tag}-{suffix}@test.local", full_name=f"R4R {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"R4R {tag}", namespace=f"rtrw-r4r-{tag}-{suffix}"[:32]
    )
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = NetRouter.objects.create(
            tenant_id=tenant.id, display_name=f"R4R {tag}",
            router_code=f"R4R-{tag}"[:16], tunnel_ip="100.127.125.1",
            mode=NetRouter.Mode.MANAGED, credential_ref="enc:r4r-controlled",
        )
    return tenant, actor, router


# ---------------------------------------------------------------------------
# REV-1811-02 — terminal no-effect koheren dengan lease yang dilepas


def test_final_no_effect_attempt_reaches_failed():
    """Attempt terakhir no-effect → FAILED tepat sekali (bukan UNCERTAIN)."""
    tenant, actor, _router = _tenant_actor_router("final-ne")
    executions = []

    class Handler(engine.JobHandler):
        kind = "_test_r4_final_noeffect"

        def execute(self, ctx):
            executions.append("definitive-no-effect")
            raise JobError(code="router_unreachable", retryable=True, no_effect=True)

        def verify(self, ctx):
            raise AssertionError("no-effect tidak boleh masuk verifier")

    engine._REGISTRY[Handler.kind] = Handler()
    try:
        job = engine.create_job(
            tenant_id=tenant.id, kind=Handler.kind, actor=actor
        )
        Job.objects.filter(id=job.id).update(max_attempts=1)
        claimed = engine.claim_next()
        assert claimed is not None and claimed.attempt == claimed.max_attempts == 1
        result = engine.run_claimed(claimed)
        fresh = Job.objects.get(id=job.id)
        assert result.state == JobState.FAILED
        assert fresh.state == JobState.FAILED
        assert fresh.error_code == "router_unreachable"
        assert fresh.retryable is True
        assert fresh.lease_token is None and fresh.lease_expires_at is None
        assert executions == ["definitive-no-effect"]
    finally:
        engine._REGISTRY.pop(Handler.kind, None)


def test_nonfinal_no_effect_backs_off_then_succeeds():
    """Attempt nonfinal no-effect → RETRY_WAIT + backoff; retry tuntas normal."""
    tenant, actor, _router = _tenant_actor_router("nonfinal-ne")
    attempts = []

    class Handler(engine.JobHandler):
        kind = "_test_r4_nonfinal_noeffect"

        def execute(self, ctx):
            attempts.append(ctx.job.attempt)
            if ctx.job.attempt < ctx.job.max_attempts:
                raise JobError(code="router_unreachable", retryable=True, no_effect=True)
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    engine._REGISTRY[Handler.kind] = Handler()
    try:
        job = engine.create_job(
            tenant_id=tenant.id, kind=Handler.kind, actor=actor
        )
        Job.objects.filter(id=job.id).update(max_attempts=2)
        first = engine.claim_next()
        assert first is not None
        result = engine.run_claimed(first)
        fresh = Job.objects.get(id=job.id)
        assert result.state == JobState.RETRY_WAIT
        assert fresh.state == JobState.RETRY_WAIT
        assert fresh.error_code == "router_unreachable"
        assert fresh.attempt == 1, "attempt nonfinal dikonsumsi (backoff, bukan reset)"
        assert fresh.available_at is not None, "backoff tersedia untuk claim ulang"
        # jatuhkan tempo backoff → claim ulang → sukses (jalur recovery sah).
        Job.objects.filter(id=job.id).update(available_at=timezone.now())
        second = engine.claim_next()
        assert second is not None and second.attempt == 2
        final = engine.run_claimed(second)
        assert final.state == JobState.SUCCEEDED
        assert attempts == [1, 2]
    finally:
        engine._REGISTRY.pop(Handler.kind, None)


def test_stale_worker_cannot_overwrite_via_no_effect_terminal():
    """Worker basi kalah CAS terminal: state yang dipindah pihak lain tidak
    tertimpa jalur terminal no-effect (expected-state + lease-NULL fence)."""
    tenant, actor, _router = _tenant_actor_router("stale")

    class Handler(engine.JobHandler):
        kind = "_test_r4_stale_terminal"

        def execute(self, ctx):
            raise JobError(code="router_unreachable", retryable=True, no_effect=True)

        def verify(self, ctx):
            raise AssertionError("tidak boleh masuk verifier")

    engine._REGISTRY[Handler.kind] = Handler()
    try:
        job = engine.create_job(
            tenant_id=tenant.id, kind=Handler.kind, actor=actor
        )
        Job.objects.filter(id=job.id).update(max_attempts=1)
        claimed = engine.claim_next()
        assert claimed is not None
        # Pihak lain (ops) memindahkan job keluar uncertain SEBELUM worker
        # menulis terminal (state berubah → CAS terminal kalah → OwnershipLost,
        # bukan menimpa). Simulasi: job sudah direkonsiliasi/diresolve.
        Job.objects.filter(id=job.id).update(state=JobState.RECOVERY_REQUIRED)
        with pytest.raises(engine.OwnershipLost):
            # _retry_no_effect final dipanggil langsung memakai snapshot basi
            # (attempt=max) — CAS gagal karena state bukan uncertain.
            engine._retry_no_effect(
                Job.objects.get(id=job.id),
                JobError(code="router_unreachable", retryable=True, no_effect=True),
            )
        assert Job.objects.get(id=job.id).state == JobState.RECOVERY_REQUIRED
    finally:
        engine._REGISTRY.pop(Handler.kind, None)


# ---------------------------------------------------------------------------
# REV-1711-04 — bukti penulis lintas proses


def test_cross_process_live_writer_blocks_resolve_not_applied():
    """Penulis attempt uncertain masih hidup di PROSES LAIN (sesi DB-nya
    dimatikan) → resolve not-applied DITOLAK; nol kirim ulang sampai penulis
    terbukti berhenti (identitas writer dipersist + liveness /proc)."""
    tenant, actor, router = _tenant_actor_router("xproc-live")
    mp = multiprocessing.get_context("fork")
    finish_writer = mp.Event()
    observer, child_pipe = mp.Pipe(duplex=False)
    parent_pid = os.getpid()
    successor_sends = []

    class Handler(engine.JobHandler):
        kind = "_test_r4_xproc_live"

        def execute(self, ctx):
            if os.getpid() != parent_pid:
                with connection.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid()")
                    pg_pid = cur.fetchone()[0]
                child_pipe.send({"event": "entered", "pg_pid": pg_pid,
                                 "registry": engine._attempt_inflight(ctx.job.id)})
                if not finish_writer.wait(30):
                    raise RuntimeError("parent tidak melepas adapter")
            else:
                successor_sends.append(str(ctx.job.id))
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    engine._REGISTRY[Handler.kind] = Handler()
    job = engine.create_job(
        tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    connections.close_all()

    def old_worker():
        try:
            result = engine.run_claimed(claimed)
            child_pipe.send({"event": "outcome", "state": result.state})
        except BaseException as exc:
            child_pipe.send({"event": "outcome", "exception": f"{type(exc).__name__}: {exc}"})
        finally:
            connections.close_all()
            child_pipe.close()

    old = mp.Process(target=old_worker, name="r4r-old-live-writer")
    old.start()
    child_pipe.close()
    rejected = None
    try:
        assert observer.poll(15), "child harus memasuki adapter terkontrol"
        entered = observer.recv()
        assert entered["event"] == "entered" and entered["registry"] is True
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(%s, 5000)", [entered["pg_pid"]]
            )
            cur.fetchone()
        assert old.is_alive() and not finish_writer.is_set()
        Job.objects.filter(id=job.id).update(
            lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert engine.reconcile_expired_leases() == 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        try:
            engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        except ValueError as exc:
            rejected = str(exc)
        assert rejected is not None, "penulis lintas proses hidup harus ditolak"
        assert "writer_active" in rejected
        assert successor_sends == []
        assert old.is_alive()
    finally:
        finish_writer.set()
        old.join(25)
        if old.is_alive():
            old.terminate()
            old.join(5)
    assert not old.is_alive() and old.exitcode == 0
    assert observer.poll(5)
    outcome = observer.recv()
    observer.close()
    assert "OperationalError" in outcome.get("exception", ""), outcome
    assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN


def test_cross_process_dead_writer_allows_positive_recovery():
    """Penulis attempt terverifikasi BERHENTI (proses mati, /proc hilang) →
    resolve not-applied diterima; pemulihan positif: claim ulang → sukses."""
    tenant, actor, router = _tenant_actor_router("xproc-dead")
    mp = multiprocessing.get_context("fork")
    observer, child_pipe = mp.Pipe(duplex=False)
    parent_pid = os.getpid()

    class Handler(engine.JobHandler):
        kind = "_test_r4_xproc_dead"

        def execute(self, ctx):
            if os.getpid() != parent_pid:
                child_pipe.send({"event": "entered"})
                import time as _t
                _t.sleep(30)  # dibunuh parent sebelum selesai
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    engine._REGISTRY[Handler.kind] = Handler()
    job = engine.create_job(
        tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router
    )
    claimed = engine.claim_next()
    assert claimed is not None
    connections.close_all()

    def old_worker():
        try:
            engine.run_claimed(claimed)
        except BaseException as exc:
            child_pipe.send({"event": "outcome", "exception": f"{type(exc).__name__}: {exc}"})
        finally:
            connections.close_all()
            child_pipe.close()

    old = mp.Process(target=old_worker, name="r4r-old-dead-writer")
    old.start()
    child_pipe.close()
    try:
        assert observer.poll(15), "child harus memasuki adapter"
        observer.recv()
        os.kill(old.pid, signal.SIGKILL)
        old.join(15)
        assert not old.is_alive() and old.exitcode == -signal.SIGKILL
        Job.objects.filter(id=job.id).update(
            lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert engine.reconcile_expired_leases() == 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        # Penulis terverifikasi berhenti (proses mati) → readback not-applied
        # diterima → pemulihan positif.
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        assert resolved.state == JobState.RETRY_WAIT
        reclaimed = engine.claim_next()
        assert reclaimed is not None and reclaimed.id == job.id
        finished = engine.run_claimed(reclaimed)
        assert finished.state == JobState.SUCCEEDED
    finally:
        old.join(10)
    observer.close()


def test_unverifiable_writer_holds_legacy_uncertain():
    """Baris uncertain tanpa identitas penulis (pra-migrasi/sintetis) →
    status TIDAK DIKETAHUI → resolve not-applied ditahan (fail-closed);
    jalur applied=None (recovery_required) tetap tersedia untuk ops."""
    tenant, actor, _router = _tenant_actor_router("legacy-hold")
    job = engine.create_job(
        tenant_id=tenant.id, kind="_test_r4_legacy_hold", actor=actor
    )
    engine.claim_next()
    # Simulasi baris legacy: uncertain tanpa pernah mencatat identitas
    # penulis attempt (pra-migrasi 0006) — writer_* NULL.
    Job.objects.filter(id=job.id).update(
        state=JobState.UNCERTAIN, lease_token=None, lease_expires_at=None,
        error_code="lease_expired",
        writer_pid=None, writer_host=None, writer_start_ticks=None,
        writer_ended_at=None,
    )
    with pytest.raises(ValueError, match="writer_unverifiable"):
        engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
    assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
    # Ops tetap punya jalur jujur untuk unknown: karantina recovery_required.
    resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=None)
    assert resolved.state == JobState.RECOVERY_REQUIRED


# ---------------------------------------------------------------------------
# REV-1711-05 — kewenangan pada batas commit setelah tunggu lock kredensial


@pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
def test_credential_lock_wait_does_not_outlive_authority(monkeypatch, protocol):
    """Revoke yang ter-commit SELAMA worker menunggu lock kredensial →
    nol Router, kredensial tetap PENDING, job gagal authority_denied.

    Versi CI dari probe controller R4 (adapter TLS terkontrol; PG nyata
    memblokir UPDATE kredensial via SELECT FOR UPDATE koneksi lain).
    """
    import threading
    import time as _time

    from django.db import close_old_connections, transaction
    from django.test import override_settings

    from domains.network.models import RouterEnrollment, SstpAccount, WireGuardPeer

    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r4cred-{suffix}@test.local", full_name="R4 credential",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name="R4 cred", namespace=f"rtrw-r4c-{suffix}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    ip = f"100.123.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}"
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="R4 cred enroll", router_code=f"R4C-{suffix}",
            protocol=protocol, tunnel_ip=ip, token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        if protocol == "sstp":
            credential = SstpAccount.objects.create(
                tenant=tenant, enrollment=enrollment, tunnel_ip=ip,
                username=f"r4c-{suffix}", password_ref="synthetic-not-decrypted",
                state=SstpAccount.State.PENDING,
            )
        else:
            credential = WireGuardPeer.objects.create(
                tenant=tenant, enrollment=enrollment, allowed_ip=ip,
                public_key=f"r4c-{suffix}", state=WireGuardPeer.State.PENDING,
            )
    credential_model = type(credential)

    job = engine.create_job(
        tenant_id=tenant.id, kind="verify_api_ssl", actor=actor,
        payload={"enrollment_id": str(enrollment.id)},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    probe_active, finish_probe = threading.Event(), threading.Event()
    locked, release_lock = threading.Event(), threading.Event()
    outcomes, errors, lock_outcomes, pids = {}, [], {}, {}

    class ConnectivityAdapter:
        def probe_connectivity(self, router_context):
            assert not connection.in_atomic_block
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["worker"] = cursor.fetchone()[0]
            probe_active.set()
            assert finish_probe.wait(15), "observasi TLS tidak dilepas"
            return {"ok": True, "cert_sha256": "a" * 64}

    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter",
        lambda: ConnectivityAdapter(),
    )

    def worker():
        close_old_connections()
        try:
            final = engine.run_claimed(Job.objects.get(id=claimed.id))
            outcomes.update(state=final.state, error=final.error_code)
        except BaseException as exc:
            errors.append(repr(exc))
        finally:
            connections.close_all()

    def locker():
        close_old_connections()
        try:
            with tenant_scope(tenant.id), transaction.atomic():
                credential_model.objects.select_for_update().get(id=credential.id)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids["locker"] = cursor.fetchone()[0]
                locked.set()
                assert release_lock.wait(20), "lock kredensial tidak dilepas"
            lock_outcomes["committed"] = True
        except BaseException as exc:
            lock_outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    worker_thread = threading.Thread(target=worker, name=f"r4r-cred-{protocol}")
    lock_thread = threading.Thread(target=locker, name=f"r4r-lock-{protocol}")
    blocked = False
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        worker_thread.start()
        try:
            assert probe_active.wait(15), "handler tidak sampai TLS"
            lock_thread.start()
            assert locked.wait(15), "baris kredensial tidak terkunci"
            finish_probe.set()
            deadline = _time.monotonic() + 10
            while _time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT %s = ANY(pg_blocking_pids(pid)) FROM pg_stat_activity WHERE pid=%s",
                        [pids["locker"], pids["worker"]],
                    )
                    row = cursor.fetchone()
                blocked = bool(row and row[0])
                if blocked:
                    break
            assert blocked, "PG harus mengamati kontensi lock kredensial nyata"
            # Revoke ter-commit pada koneksi terpisah SELAMA UPDATE sensitif
            # masih tertahan — setelah seluruh pembacaan authority entry.
            assert Membership.objects.filter(user=actor, tenant=tenant).update(
                revoked_at=timezone.now()
            ) == 1
        finally:
            finish_probe.set()
            release_lock.set()
            if lock_thread.ident is not None:
                lock_thread.join(20)
            worker_thread.join(20)
    assert not lock_thread.is_alive() and not worker_thread.is_alive()
    assert lock_outcomes == {"committed": True}, lock_outcomes
    assert not errors and "state" in outcomes, {"errors": errors, "outcomes": outcomes}
    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        routers = Router.objects.filter(tenant=tenant).count()
    assert routers == 0, "revoke saat tunggu lock kredensial tidak boleh mengaktifkan router"
    assert credential.state == "pending"
    assert outcomes["state"] == JobState.FAILED
    assert outcomes["error"] == "authority_denied"
