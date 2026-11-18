"""Functional lease checks for a disposable PostgreSQL test database."""
from datetime import timedelta
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from uuid import uuid4
import importlib.util

import pytest
from django.db import connection, connections, transaction
from django.test import override_settings
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.network.models import Router, RouterEnrollment, WireGuardPeer
from domains.tenancy.models import Tenant

R5_TEST = Path.cwd() / "tests/integration/test_jobs_r5_residuals.py"
r5_spec = importlib.util.spec_from_file_location("existing_r5_checks", R5_TEST)
r5_checks = importlib.util.module_from_spec(r5_spec)
r5_spec.loader.exec_module(r5_checks)
pytestmark = r5_checks.pytestmark


def backend_pid():
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        return cursor.fetchone()[0]


def wait_for_blocked(worker_pid, blocker_pid, table=None):
    deadline = monotonic() + 2
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
        except BaseException as exc:
            result["exception"] = exc
        finally:
            connections.close_all()

    worker = Thread(target=run, daemon=True)
    worker.start()
    return worker, result


def finish_worker(worker, result):
    worker.join(8)
    assert not worker.is_alive()
    assert "exception" not in result, result
    assert "return" in result, result
    return result["return"]


@pytest.mark.parametrize("max_attempts", [1, 2], ids=["final", "nonfinal"])
@pytest.mark.parametrize("cross_expiry", [False, True], ids=["valid", "expired"])
def test_settlement_lease_is_checked_after_job_row_lock(monkeypatch, max_attempts, cross_expiry):
    tag = uuid4().hex[:10]
    tenant = Tenant.objects.create(display_name="Review settlement", namespace=f"rtrw-probe-{tag}")
    entered, finish = Event(), Event()
    observed = {}

    class ControlledNoEffect(engine.JobHandler):
        kind = "_test_review_settlement_wait"

        def execute(self, ctx):
            observed["pid"] = backend_pid()
            entered.set()
            assert finish.wait(8)
            raise engine.JobError(code="controlled_no_effect", retryable=True, no_effect=True)

        def verify(self, ctx):
            pytest.fail("No-effect job reached verification")

    handler = ControlledNoEffect()
    monkeypatch.setitem(engine._REGISTRY, handler.kind, handler)
    job = engine.create_job(tenant_id=tenant.id, kind=handler.kind)
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
    print(f"settlement max_attempts={max_attempts} expired_while_blocked={cross_expiry} "
          f"pg_wait={query.split()[0]} actual={fresh.state} error={fresh.error_code} "
          f"token_preserved={fresh.lease_token == initial_token} "
          f"epoch_preserved={fresh.lease_epoch == initial_epoch}")
    assert returned.state == fresh.state
    if cross_expiry:
        assert (fresh.state, fresh.error_code, fresh.lease_token, fresh.lease_epoch) == (
            JobState.EXECUTING, None, initial_token, initial_epoch,
        )
    else:
        assert fresh.state == (JobState.FAILED if max_attempts == 1 else JobState.RETRY_WAIT)
        assert fresh.error_code == "controlled_no_effect" and fresh.lease_token is None


def test_watchdog_cannot_extend_expired_lease_after_job_row_lock(monkeypatch):
    tag = uuid4().hex[:10]
    tenant = Tenant.objects.create(display_name="Review heartbeat", namespace=f"rtrw-probe-{tag}")
    job = engine.create_job(tenant_id=tenant.id, kind="_test_review_watchdog")
    claimed = engine.claim_next()
    assert claimed.id == job.id
    ready, stop, done = Event(), Event(), Event()
    observed = {}
    expiry = timezone.now() + timedelta(seconds=2.5)
    assert Job.objects.filter(id=job.id).update(state=JobState.EXECUTING, lease_expires_at=expiry) == 1
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
    print(f"watchdog pg_wait={query.split()[0]} expiry_preserved={fresh.lease_expires_at == expiry} "
          f"state={fresh.state} token_preserved={fresh.lease_token == claimed.lease_token} "
          f"lease_extended_after_wait={fresh.lease_expires_at > expiry}")
    assert fresh.lease_expires_at == expiry


def test_enrollment_lease_covers_deferred_foreign_key_wait(monkeypatch):
    tenant, _, enrollment, credential, job = r5_checks._credential_wait_setup("fk-wait", "wireguard")
    claimed = engine.claim_next()
    assert claimed.id == job.id
    active, finish = Event(), Event()
    worker = result = None
    observed = {}
    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter",
        lambda: r5_checks._ConnectivityAdapter(active, finish, observed),
    )
    # Observe the waiting transaction before the normal renewal can run.
    monkeypatch.setattr(engine, "HEARTBEAT_S", 20)

    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        worker, result = start_worker(lambda: engine.run_claimed(claimed))
        try:
            assert active.wait(5)
            expiry = timezone.now() + timedelta(seconds=2.5)
            assert Job.objects.filter(id=job.id).update(lease_expires_at=expiry) == 1
            with transaction.atomic():
                Tenant.objects.select_for_update().get(id=tenant.id)
                finish.set()
                query = wait_for_blocked(observed["worker"], backend_pid())
                assert timezone.now() < expiry
                wait_until_expired(expiry)
        finally:
            finish.set()
            returned = finish_worker(worker, result)

    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        router_count = Router.objects.filter(tenant=tenant).count()
    final = Job.objects.get(id=job.id)
    print(f"enrollment pg_wait={query.split()[0]} router_count={router_count} "
          f"credential={credential.state} enrollment={enrollment.status} job={final.state}")
    assert returned.state == final.state
    assert (router_count, credential.state, enrollment.status) == (
        0, WireGuardPeer.State.PENDING, RouterEnrollment.Status.VERIFYING,
    )
