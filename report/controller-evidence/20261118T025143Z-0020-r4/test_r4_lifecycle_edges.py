"""R4 real-engine assertions. Root executes on disposable PostgreSQL only.

Controlled adapters gate actual engine decisions. Cross-process proof uses a
real OS child with independently opened PG session; no physical-device claim.
"""
from __future__ import annotations

import json
import multiprocessing
import os

import pytest
from django.conf import settings
from django.db import connection, connections
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
        email=f"r4-{tag}@test.local", full_name=f"R4 {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R4 {tag}", namespace=f"rtrw-r4-{tag}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id, display_name=tag, router_code=f"R4-{tag}"[:16],
            tunnel_ip="100.127.124.1", mode=Router.Mode.MANAGED,
            credential_ref="enc:r4-controlled",
        )
    return tenant, actor, router


def test_cross_process_not_applied_resolution_cannot_resume_live_old_writer(monkeypatch):
    """A03/A04: separate-process registry cannot prove old writer stopped."""
    tenant, actor, router = _setup("crossproc-resolve")
    mp = multiprocessing.get_context("fork")
    finish_writer = mp.Event()
    observer, child_pipe = mp.Pipe(duplex=False)
    parent_pid = os.getpid()
    successor_sends = []

    class Handler(engine.JobHandler):
        kind = "_test_r4_crossproc_resolve"

        def execute(self, ctx):
            if os.getpid() != parent_pid:
                with connection.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid(), current_database()")
                    pg_pid, database = cur.fetchone()
                child_pipe.send({"event": "old-send-entered", "os_pid": os.getpid(),
                                 "pg_pid": pg_pid, "database": database,
                                 "registry": engine._attempt_inflight(ctx.job.id)})
                if not finish_writer.wait(30):
                    raise RuntimeError("parent failed to release controlled old adapter")
            else:
                successor_sends.append(str(ctx.job.id))
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    # No database socket survives fork: both processes reopen independently.
    # Django test DB settings (including actual test NAME) are inherited.
    actual_test_database = str(settings.DATABASES["default"]["NAME"])
    connections.close_all()

    def old_worker():
        try:
            result = engine.run_claimed(claimed)
            child_pipe.send({"event": "old-outcome", "state": result.state})
        except BaseException as exc:
            child_pipe.send({"event": "old-outcome", "exception": f"{type(exc).__name__}: {exc}"})
        finally:
            connections.close_all()
            child_pipe.close()

    old = mp.Process(target=old_worker, name="r4-old-live-adapter")
    old.start()
    child_pipe.close()
    resolve_rejected = None
    successor_outcome = None
    entered = None
    old_outcome = None
    try:
        assert observer.poll(15), "old process must enter its controlled adapter"
        entered = observer.recv()
        assert entered["event"] == "old-send-entered", entered
        assert entered["os_pid"] == old.pid != parent_pid
        assert entered["database"] == actual_test_database
        assert entered["registry"] is True
        assert engine._attempt_inflight(job.id) is False
        with connection.cursor() as cur:
            cur.execute("SELECT pg_backend_pid(), pg_terminate_backend(%s, 5000)", [entered["pg_pid"]])
            observer_pg_pid, terminated = cur.fetchone()
        assert terminated and observer_pg_pid != entered["pg_pid"]
        assert old.is_alive() and not finish_writer.is_set()
        assert engine.acquire_router_sender(router.id)
        engine.release_router_sender(router.id)
        Job.objects.filter(id=job.id).update(
            lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert engine.reconcile_expired_leases() == 1
        uncertain = Job.objects.get(id=job.id)
        assert uncertain.state == JobState.UNCERTAIN
        try:
            engine.resolve_uncertain(uncertain, applied=False)
        except ValueError as exc:
            resolve_rejected = str(exc)
        if resolve_rejected is None:
            successor = engine.claim_next()
            assert successor is not None and successor.id == job.id
            assert successor.lease_epoch > claimed.lease_epoch
            result = engine.run_claimed(successor)
            successor_outcome = {"state": result.state}
        live_at_resume = old.is_alive() and not finish_writer.is_set()
        assert live_at_resume
    finally:
        finish_writer.set()
        old.join(25)
        if old.is_alive():
            old.terminate()
            old.join(5)
    assert not old.is_alive() and old.exitcode == 0
    assert observer.poll(5), "old worker outcome must be collected"
    old_outcome = observer.recv()
    observer.close()
    assert old_outcome["event"] == "old-outcome", old_outcome
    assert "OperationalError" in old_outcome.get("exception", ""), old_outcome
    fresh = Job.objects.get(id=job.id)
    print(json.dumps({"case": "r4-cross-process-resolve", "old": entered,
                      "old_outcome": old_outcome, "resolve_rejected": resolve_rejected,
                      "successor_sends": successor_sends, "successor_outcome": successor_outcome,
                      "old_writer_live_at_resume": live_at_resume,
                      "total_send_entries": 1 + len(successor_sends), "state": fresh.state}, default=str), flush=True)
    assert successor_sends == [], "same-job recovery sent again while old process/adapter remained alive"
    assert resolve_rejected is not None, "free DB advisory lock does not prove cross-process writer stopped"


def test_proven_no_effect_at_max_attempts_reaches_terminal_failure(monkeypatch):
    """A05/A09: authorized recovery after releasing lease still terminates.

    Ordinary CAS now requires valid lease. _retry_no_effect clears its lease
    before max-attempt terminal step; that recovery step cannot match it.
    """
    tenant, actor, router = _setup("max-no-effect")
    executions = []

    class Handler(engine.JobHandler):
        kind = "_test_r4_max_no_effect"

        def execute(self, ctx):
            executions.append("definitive-no-effect")
            raise engine.JobError(code="router_unreachable", retryable=True, no_effect=True)

        def verify(self, ctx):
            raise AssertionError("no-effect failure must not enter verifier")

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    Job.objects.filter(id=job.id).update(max_attempts=1)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id and claimed.attempt == claimed.max_attempts == 1
    result = engine.run_claimed(claimed)
    fresh = Job.objects.get(id=job.id)
    print(json.dumps({"case": "r4-no-effect-max-attempts", "state": fresh.state,
                      "returned_state": result.state, "error": fresh.error_code,
                      "retryable": fresh.retryable, "lease_token": fresh.lease_token,
                      "lease_expires_at": fresh.lease_expires_at,
                      "attempt": fresh.attempt, "max_attempts": fresh.max_attempts,
                      "executions": executions}, default=str), flush=True)
    assert executions == ["definitive-no-effect"]
    assert fresh.state == JobState.FAILED, "last no-effect attempt stranded uncertain by impossible lease-valid CAS"
    assert fresh.error_code == "router_unreachable"
