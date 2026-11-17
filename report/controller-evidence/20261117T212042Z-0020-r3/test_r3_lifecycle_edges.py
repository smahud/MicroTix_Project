"""Independent R3 safety assertions. Root executes on disposable PG only.

Controlled handlers gate real engine paths; production decisions and database
state changes are real. No device or production credentials are involved.
"""
from __future__ import annotations

import json
import threading
import time

import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.network.models import Router
from domains.tenancy.models import Membership, Role, Tenant

pytest_plugins = ["tests.conftest"]
pytestmark = pytest.mark.django_db(
    transaction=True, available_apps=list(settings.INSTALLED_APPS)
)


def _setup(tag):
    actor = User.objects.create_user(
        email=f"r3-{tag}@test.local", full_name=f"R3 {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R3 {tag}", namespace=f"rtrw-r3-{tag}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id, display_name=tag, router_code=f"R3-{tag}"[:16],
            tunnel_ip="100.127.123.1", mode=Router.Mode.MANAGED,
            credential_ref="enc:r3-controlled",
        )
    return tenant, actor, router


def _thread(claimed, outcomes, key):
    def run():
        from django.db import connections
        try:
            outcomes[key] = {"state": engine.run_claimed(claimed).state}
        except BaseException as exc:
            outcomes[key] = {"exception": f"{type(exc).__name__}: {exc}"}
        finally:
            connections.close_all()
    worker = threading.Thread(target=run, name=key)
    worker.start()
    return worker


def test_single_io_phase_survives_beyond_initial_lease_expiry(monkeypatch):
    """Positive REV09 evidence crosses actual original lease expiry with
    concurrent reconcile attempts and no cooperative progress inside I/O.
    """
    tenant, actor, router = _setup("cross-initial-expiry")
    entered = threading.Event()
    resume = threading.Event()
    outcomes = {}

    class Handler(engine.JobHandler):
        kind = "_test_r3_cross_initial_expiry"

        def execute(self, ctx):
            entered.set()
            if not resume.wait(20):
                raise RuntimeError("root did not release long single adapter phase")
            return {"ok": True}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setattr(engine, "LEASE_S", 2)
    monkeypatch.setattr(engine, "HEARTBEAT_S", 0.2)
    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    worker = _thread(claimed, outcomes, "cross-expiry")
    try:
        assert entered.wait(15)
        initial_expiry = Job.objects.get(id=job.id).lease_expires_at
        attempts = 0
        bounded_deadline = time.monotonic() + 8
        while timezone.now() <= initial_expiry + timezone.timedelta(seconds=0.6):
            assert time.monotonic() < bounded_deadline, "wall clock must advance within bounded window"
            assert engine.reconcile_expired_leases() == 0
            current = Job.objects.get(id=job.id)
            assert current.state == JobState.EXECUTING
            attempts += 1
            time.sleep(0.1)
        current = Job.objects.get(id=job.id)
        assert timezone.now() > initial_expiry
        assert current.lease_expires_at > timezone.now()
        assert current.lease_expires_at > initial_expiry
        assert attempts >= 3
        print(json.dumps({"case": "r3-cross-initial-expiry", "initial_expiry": initial_expiry,
                          "observed_at": timezone.now(), "lease": current.lease_expires_at,
                          "reconcile_attempts": attempts}, default=str), flush=True)
        resume.set()
    finally:
        resume.set()
        worker.join(25)
    assert not worker.is_alive()
    assert set(outcomes) == {"cross-expiry"}, outcomes
    assert outcomes["cross-expiry"] == {"state": JobState.SUCCEEDED}, outcomes


def test_progress_cannot_revive_expired_worker_after_watchdog_stopped(monkeypatch):
    """A01/A05: every renewal path, not only watchdog, must honor expiry.

    Same expiry schedule as submitted non-resurrection test, without assuming
    an immediate reconciler. Watchdog sees the expiry and exits; a delayed
    handler then tries its next real progress/send boundary.
    """
    tenant, actor, router = _setup("expired-progress")
    entered = threading.Event()
    resume = threading.Event()
    watchdog_done = threading.Event()
    outcomes = {}
    effects = []
    real_watchdog = engine._heartbeat_watchdog

    def observed_watchdog(ctx, stop, done):
        real_watchdog(ctx, stop, done)
        watchdog_done.set()

    class Handler(engine.JobHandler):
        kind = "_test_r3_expired_progress"

        def execute(self, ctx):
            entered.set()
            if not resume.wait(20):
                raise RuntimeError("root did not resume expired worker")
            ctx.progress(phase="late-send")
            effects.append("new-send-after-expiry")
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setattr(engine, "HEARTBEAT_S", 0.1)
    monkeypatch.setattr(engine, "_heartbeat_watchdog", observed_watchdog)
    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    worker = _thread(claimed, outcomes, "expired-progress")
    try:
        assert entered.wait(15)
        expired_at = timezone.now() - timezone.timedelta(seconds=1)
        Job.objects.filter(id=job.id).update(lease_expires_at=expired_at)
        assert watchdog_done.wait(10), "real watchdog must observe expired lease and stop"
        assert Job.objects.get(id=job.id).lease_expires_at == expired_at
        # No reconciler has run: expired lease is itself no longer valid.
        resume.set()
    finally:
        resume.set()
        worker.join(25)
    assert not worker.is_alive(), "worker must exit bounded"
    assert set(outcomes) == {"expired-progress"}, outcomes
    assert "exception" not in outcomes["expired-progress"], outcomes
    fresh = Job.objects.get(id=job.id)
    print(json.dumps({"case": "r3-expired-progress-resurrection", "effects": effects,
                      "expired_at": expired_at, "final_lease": fresh.lease_expires_at,
                      "state": fresh.state, "outcomes": outcomes}, default=str), flush=True)
    assert effects == [], "progress resurrected an expired lease and allowed a new send"
    assert fresh.state != JobState.SUCCEEDED, "expired worker was falsely successful"


def test_returning_io_worker_cannot_revive_expired_lease_before_verify(monkeypatch):
    """A01/A05: engine's phase transition/heartbeat also require valid lease."""
    tenant, actor, router = _setup("expired-return")
    entered = threading.Event()
    resume = threading.Event()
    watchdog_done = threading.Event()
    outcomes = {}
    verified = []
    real_watchdog = engine._heartbeat_watchdog

    def observed_watchdog(ctx, stop, done):
        real_watchdog(ctx, stop, done)
        watchdog_done.set()

    class Handler(engine.JobHandler):
        kind = "_test_r3_expired_return"

        def execute(self, ctx):
            entered.set()
            if not resume.wait(20):
                raise RuntimeError("root did not release long adapter")
            return {"sent": True}

        def verify(self, ctx):
            verified.append("verify-after-expiry")
            return {"ok": True}

    monkeypatch.setattr(engine, "HEARTBEAT_S", 0.1)
    monkeypatch.setattr(engine, "_heartbeat_watchdog", observed_watchdog)
    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    worker = _thread(claimed, outcomes, "expired-return")
    try:
        assert entered.wait(15)
        expired_at = timezone.now() - timezone.timedelta(seconds=1)
        Job.objects.filter(id=job.id).update(lease_expires_at=expired_at)
        assert watchdog_done.wait(10)
        assert Job.objects.get(id=job.id).lease_expires_at == expired_at
        resume.set()
    finally:
        resume.set()
        worker.join(25)
    assert not worker.is_alive()
    assert set(outcomes) == {"expired-return"}, outcomes
    assert "exception" not in outcomes["expired-return"], outcomes
    fresh = Job.objects.get(id=job.id)
    print(json.dumps({"case": "r3-expired-return-resurrection", "verified": verified,
                      "expired_at": expired_at, "final_lease": fresh.lease_expires_at,
                      "state": fresh.state, "outcomes": outcomes}, default=str), flush=True)
    assert verified == [], "phase transition/heartbeat revived expired worker before verify"
    assert fresh.state != JobState.SUCCEEDED, "expired worker committed terminal success"


def test_readback_not_applied_cannot_resume_after_db_loss_with_live_old_writer(monkeypatch):
    """REV04/A03/A04: resolve False must not equate lost DB session to stopped
    adapter. Readback can be negative while an old outstanding command can
    still land later. Reclaiming the SAME job must not bypass durable hold.
    """
    tenant, actor, router = _setup("resolve-db-loss")
    writer_blocked = threading.Event()
    finish_writer = threading.Event()
    info = {}
    outcomes = {}
    sends = []

    class Handler(engine.JobHandler):
        kind = "_test_r3_resolve_db_loss"

        def execute(self, ctx):
            sends.append(str(ctx.job.id))
            if threading.current_thread().name == "old-live-adapter":
                with connection.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid()")
                    info["worker_pid"] = cur.fetchone()[0]
                writer_blocked.set()
                if not finish_writer.wait(20):
                    raise RuntimeError("root did not release old adapter")
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    first = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == first.id
    predecessor = _thread(claimed, outcomes, "old-live-adapter")
    successor = None
    resolve_rejected = None
    try:
        assert writer_blocked.wait(15)
        with connection.cursor() as cur:
            # Only the probe's own disposable runtime session is terminated.
            cur.execute("SELECT pg_backend_pid(), pg_terminate_backend(%s, 5000)", [info["worker_pid"]])
            observer_pid, terminated = cur.fetchone()
        assert observer_pid != info["worker_pid"] and terminated
        assert predecessor.is_alive() and "old-live-adapter" not in outcomes
        assert not finish_writer.is_set()
        assert engine.acquire_router_sender(router.id), "own terminated DB session must release lock"
        engine.release_router_sender(router.id)
        Job.objects.filter(id=first.id).update(
            lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert engine.reconcile_expired_leases() == 1
        uncertain = Job.objects.get(id=first.id)
        assert uncertain.state == JobState.UNCERTAIN
        try:
            # This readback says not applied YET; an outstanding old adapter
            # remains capable of landing its first send after this observation.
            engine.resolve_uncertain(uncertain, applied=False)
        except ValueError as exc:
            resolve_rejected = str(exc)
        if resolve_rejected is None:
            reclaimed = engine.claim_next()
            assert reclaimed is not None and reclaimed.id == first.id
            assert reclaimed.lease_epoch > claimed.lease_epoch
            successor = _thread(reclaimed, outcomes, "new-same-job")
            successor.join(15)
            assert not successor.is_alive()
            assert "exception" not in outcomes.get("new-same-job", {}), outcomes
        info["old_writer_live_at_resume"] = predecessor.is_alive() and not finish_writer.is_set()
        assert info["old_writer_live_at_resume"]
    finally:
        finish_writer.set()
        predecessor.join(25)
        if successor is not None:
            successor.join(25)
    assert not predecessor.is_alive()
    assert successor is None or not successor.is_alive()
    expected_outcomes = {"old-live-adapter"} | ({"new-same-job"} if successor is not None else set())
    assert set(outcomes) == expected_outcomes, outcomes
    assert "exception" in outcomes["old-live-adapter"], outcomes
    assert "OperationalError" in outcomes["old-live-adapter"]["exception"], outcomes
    print(json.dumps({"case": "r3-resolve-db-session-loss", "sends": len(sends),
                      "resolve_rejected": resolve_rejected, "info": info,
                      "outcomes": outcomes, "final": Job.objects.get(id=first.id).state},
                     default=str), flush=True)
    assert len(sends) == 1, "not-applied resolution reopened send while old adapter remained live"
    assert resolve_rejected is not None, "DB-session lock release is not old-writer-safe proof"
