"""Controller R2 adversarial closure probes; root runs on disposable PG.

App source remains unchanged. Gates only pause after real checks; they do
not inject a product error or replace any production decision.
"""
from __future__ import annotations

import json
import threading

import pytest
from django.conf import settings
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.network.models import DiscoveryObject, DiscoverySnapshot, Router
from domains.tenancy.models import Membership, Role, Tenant

pytest_plugins = ["tests.conftest"]
pytestmark = pytest.mark.django_db(
    transaction=True, available_apps=list(settings.INSTALLED_APPS)
)


def _setup(tag):
    actor = User.objects.create_user(
        email=f"r2-{tag}@test.local", full_name=f"R2 {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R2 {tag}", namespace=f"rtrw-r2-{tag}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id, display_name=tag, router_code=f"R2-{tag}"[:16],
            tunnel_ip="100.127.121.1", mode=Router.Mode.MANAGED,
            credential_ref="enc:r2-controlled",
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


def test_discovery_guard_and_domain_commit_are_atomic_against_reconcile(monkeypatch):
    """REV01: after real object-unit guard, independent reconcile must not
    complete before that guarded domain unit commits, or must roll it back.
    """
    from adapters.routeros import factory

    tenant, actor, router = _setup("guard-race")
    after_accounts = threading.Event()
    guard_checked = threading.Event()
    resume = threading.Event()
    outcomes = {}
    real_guard = engine.JobContext.assert_owned

    class Adapter:
        def list_accounts(self, ctx):
            after_accounts.set()
            return [{"username": "late-domain-account", "service": "pppoe"}]

        def read_health(self, ctx):
            return {"vpn_up": True, "api_up": True, "uptime_s": 1}

    def gated_guard(ctx):
        real_guard(ctx)
        if after_accounts.is_set() and not guard_checked.is_set():
            # The first real guard after list_accounts is the production
            # object/snapshot commit unit in services.run_discovery.
            guard_checked.set()
            if not resume.wait(20):
                raise RuntimeError("root did not release checked ownership guard")

    monkeypatch.setattr(factory, "active_routeros_adapter", lambda: Adapter())
    monkeypatch.setattr(factory, "active_adapter_name", lambda: "simulator")
    monkeypatch.setattr(engine.JobContext, "assert_owned", gated_guard)
    job = engine.create_job(
        tenant_id=tenant.id, kind="discover_router", actor=actor, router=router
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    worker = _thread(claimed, outcomes, "discovery")
    try:
        assert guard_checked.wait(15), "worker must pause after real domain guard"
        Job.objects.filter(id=job.id).update(
            lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert engine.reconcile_expired_leases() == 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
    finally:
        resume.set()
        worker.join(25)
    assert not worker.is_alive(), "bounded worker must exit"
    assert set(outcomes) == {"discovery"}, outcomes
    assert "exception" not in outcomes["discovery"], outcomes
    with tenant_scope(tenant.id):
        count = DiscoveryObject.objects.filter(router_id=router.id).count()
        snapshots = list(DiscoverySnapshot.objects.filter(router_id=router.id).values_list("status", flat=True))
    print(json.dumps({"case": "r2-guard-to-commit-race", "objects": count,
                      "snapshots": snapshots, "job": Job.objects.get(id=job.id).state,
                      "outcomes": outcomes}, default=str), flush=True)
    assert count == 0, "real discovery committed object after independent ownership loss"
    assert "succeeded" not in snapshots, "snapshot success committed after lease revocation"


def test_unknown_router_hold_is_rechecked_after_sender_acquisition(monkeypatch):
    """REV04: predecessor can become uncertain between successor's durable
    hold SELECT and its successful advisory acquisition. It still blocks send.
    """
    tenant, actor, router = _setup("hold-race")
    first_executing = threading.Event()
    finish_first = threading.Event()
    successor_checked_hold = threading.Event()
    acquire_second = threading.Event()
    sends = []
    outcomes = {}
    real_acquire = engine.acquire_router_sender

    class Handler(engine.JobHandler):
        kind = "_test_r2_unknown_race"

        def execute(self, ctx):
            sends.append(str(ctx.job.id))
            if threading.current_thread().name == "predecessor":
                first_executing.set()
                if not finish_first.wait(20):
                    raise RuntimeError("root did not release predecessor")
                raise engine.JobError(code="timeout_after_send", uncertain=True)
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    def gated_acquire(router_id):
        if threading.current_thread().name == "successor":
            # Called only after router_unknown SELECT returned false.
            successor_checked_hold.set()
            if not acquire_second.wait(20):
                raise RuntimeError("root did not release sender acquisition")
        return real_acquire(router_id)

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    monkeypatch.setattr(engine, "acquire_router_sender", gated_acquire)
    first = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    first_claim = engine.claim_next()
    assert first_claim is not None and first_claim.id == first.id
    predecessor = _thread(first_claim, outcomes, "predecessor")
    successor = None
    try:
        assert first_executing.wait(15), "predecessor must send before successor"
        second = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
        second_claim = engine.claim_next()
        assert second_claim is not None and second_claim.id == second.id
        successor = _thread(second_claim, outcomes, "successor")
        assert successor_checked_hold.wait(15), "successor must pass real durable hold check"
        finish_first.set()
        predecessor.join(20)
        assert not predecessor.is_alive()
        assert outcomes.get("predecessor") == {"state": JobState.UNCERTAIN}, outcomes
        acquire_second.set()
    finally:
        finish_first.set()
        acquire_second.set()
        predecessor.join(25)
        if successor is not None:
            successor.join(25)
    assert not predecessor.is_alive()
    assert successor is not None and not successor.is_alive()
    assert set(outcomes) == {"predecessor", "successor"}, outcomes
    assert all("exception" not in v for v in outcomes.values()), outcomes
    print(json.dumps({"case": "r2-hold-to-sender-race", "sends": len(sends),
                      "outcomes": outcomes, "first": Job.objects.get(id=first.id).state,
                      "second": Job.objects.get(id=second.id).state}, default=str), flush=True)
    assert len(sends) == 1, "successor sent after prior outcome became unknown before lock acquisition"
    assert Job.objects.get(id=second.id).state != JobState.SUCCEEDED


def test_database_session_loss_does_not_prove_adapter_writer_stopped(monkeypatch):
    """REV04/A03: DB advisory ownership ends on DB session loss even while
    the real worker remains in a blocked external adapter phase. A valid
    predecessor lease is not permission for a conflicting second send.
    """
    from django.db import connection

    tenant, actor, router = _setup("db-loss")
    writer_blocked = threading.Event()
    finish_writer = threading.Event()
    info = {}
    outcomes = {}
    sends = []

    class Handler(engine.JobHandler):
        kind = "_test_r2_db_loss"

        def execute(self, ctx):
            sends.append(str(ctx.job.id))
            if threading.current_thread().name == "live-adapter":
                with connection.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid()")
                    info["worker_pid"] = cur.fetchone()[0]
                writer_blocked.set()
                if not finish_writer.wait(20):
                    raise RuntimeError("root did not release live adapter phase")
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    first = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    first_claim = engine.claim_next()
    assert first_claim is not None and first_claim.id == first.id
    predecessor = _thread(first_claim, outcomes, "live-adapter")
    successor = None
    try:
        assert writer_blocked.wait(15), "first worker must be blocked after send"
        with connection.cursor() as cur:
            # Bound the wait for our own disposable runtime session to exit;
            # a delivered termination signal alone does not prove lock release.
            cur.execute("SELECT pg_backend_pid(), pg_terminate_backend(%s, 5000)", [info["worker_pid"]])
            observer_pid, terminated = cur.fetchone()
        assert observer_pid != info["worker_pid"] and terminated
        assert predecessor.is_alive() and "live-adapter" not in outcomes
        assert not finish_writer.is_set(), "adapter phase remains outstanding after DB death"
        first_after_loss = Job.objects.get(id=first.id)
        assert first_after_loss.state == JobState.EXECUTING
        assert first_after_loss.lease_expires_at > timezone.now()
        # Observe the actual session lock released, then give it back so the
        # next real engine run, not this observer, owns any successor lock.
        lock_released = engine.acquire_router_sender(router.id)
        info["lock_released"] = lock_released
        if lock_released:
            engine.release_router_sender(router.id)
        assert lock_released, "terminated DB session must release advisory ownership"
        second = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
        second_claim = engine.claim_next()
        assert second_claim is not None and second_claim.id == second.id
        successor = _thread(second_claim, outcomes, "successor-after-db-loss")
        successor.join(20)
        assert not successor.is_alive(), "successor must terminate bounded"
        # The predecessor is STILL blocked while any successor send happens.
        info["old_adapter_still_live_at_successor_end"] = predecessor.is_alive() and not finish_writer.is_set()
        assert info["old_adapter_still_live_at_successor_end"]
        assert "exception" not in outcomes.get("successor-after-db-loss", {}), outcomes
    finally:
        finish_writer.set()
        predecessor.join(25)
        if successor is not None:
            successor.join(25)
    assert not predecessor.is_alive()
    assert successor is not None and not successor.is_alive()
    assert set(outcomes) == {"live-adapter", "successor-after-db-loss"}, outcomes
    # The old worker's DB OperationalError after unblocking is an observed
    # process outcome, not an uncollected pytest/thread harness exception.
    assert "exception" in outcomes["live-adapter"], outcomes
    assert "OperationalError" in outcomes["live-adapter"]["exception"], outcomes
    print(json.dumps({"case": "r2-db-session-loss-live-adapter", "sends": len(sends),
                      "info": info, "outcomes": outcomes,
                      "first": Job.objects.get(id=first.id).state,
                      "second": Job.objects.get(id=second.id).state}, default=str), flush=True)
    assert len(sends) == 1, "DB session loss released lock while old adapter writer remained alive"
    assert Job.objects.get(id=second.id).state != JobState.SUCCEEDED
