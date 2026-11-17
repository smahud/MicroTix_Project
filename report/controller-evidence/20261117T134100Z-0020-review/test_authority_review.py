"""Controller acceptance probes against exact PR27 bd37c14.

The assertions express required acceptance. They intentionally fail on
confirmed defects, preserving observed HTTP/durable effects in stdout.
Run from backend with pytest-django and TEST_DATABASE_URL for disposable PG.
No application source is changed. Controlled B6 adapter is not real RouterOS.
"""
from __future__ import annotations

import json
import threading
import time
import uuid

import pytest
from django.db import close_old_connections, connection, connections
from django.utils import timezone
from rest_framework.test import APIClient

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.network.models import Router
from domains.radius.models import CutoverRun
from domains.tenancy.models import Membership, Role, Tenant

pytest_plugins = ["tests.conftest"]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(
        transaction=True,
        # Explicit available_apps enables Django's allow_cascade flush for
        # unmanaged RADIUS projection FKs, matching the project race suites.
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


def _identity(label):
    suffix = uuid.uuid4().hex[:10]
    owner = User.objects.create_user(
        email=f"controller-{label}-{suffix}@test.local", full_name="Controller probe",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"Review {label}", namespace=f"rtrw-rv-{suffix}")
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    return tenant, owner


def _router(tenant, code):
    with tenant_scope(tenant.id):
        return Router.objects.create(
            tenant=tenant, display_name=code, router_code=code,
            tunnel_ip=f"100.126.{uuid.uuid4().int % 240 + 1}.{uuid.uuid4().int % 240 + 1}",
            mode=Router.Mode.MANAGED, credential_ref="enc:controlled-review",
        )


def _client(user, tenant):
    client = APIClient(enforce_csrf_checks=False)
    client.force_login(user)
    session = client.session
    session["active_tenant_id"] = str(tenant.id)
    session["auth_at"] = time.time()
    session.save()
    return client


@pytest.mark.parametrize("action", ["detail", "cancel", "retry"])
def test_http_jobs_reject_router_outside_membership_scope(action):
    tenant, owner = _identity(f"scope-{action}")
    allowed, denied = _router(tenant, "allowed"), _router(tenant, "denied")
    Membership.objects.filter(user=owner, tenant=tenant).update(router_scope=[str(allowed.id)])
    job = engine.create_job(tenant_id=tenant.id, kind="backup_router", actor=owner, router=denied)
    if action == "retry":
        Job.objects.filter(id=job.id).update(state=JobState.FAILED, retryable=True)
    original_state = Job.objects.get(id=job.id).state
    before = Job.objects.filter(tenant_id=tenant.id).count()
    client = _client(owner, tenant)
    if action == "detail":
        response = client.get(f"/api/v1/jobs/{job.id}")
    else:
        response = client.post(f"/api/v1/jobs/{job.id}/{action}", {"reason": "scope probe"}, format="json")
    actual = Job.objects.get(id=job.id)
    after = Job.objects.filter(tenant_id=tenant.id).count()
    observed = {
        "probe": f"http_scope_{action}", "http_status": response.status_code,
        "job_state_before": original_state, "job_state_after": actual.state,
        "job_count_before": before, "job_count_after": after,
        "job_router_in_membership_scope": False,
    }
    print(json.dumps(observed, sort_keys=True))
    assert (response.status_code, actual.state, after) == (404, original_state, before), observed


@pytest.mark.parametrize("authority_change", ["revoke", "demote"])
def test_authority_change_after_real_preflight_prevents_router_release(monkeypatch, authority_change):
    tenant, owner = _identity(f"authority-{authority_change}")
    router = _router(tenant, "release-authority")
    job = engine.create_job(tenant_id=tenant.id, kind="router_release", actor=owner, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    real_handler = engine.handler_for("router_release")
    real_preflight = real_handler.preflight
    preflight_completed = threading.Event()
    allow_execute = threading.Event()
    results, errors, pids = {}, [], {}

    def gated_preflight(ctx):
        # Run the real production preflight first. The main connection then
        # commits revocation/demotion while this independent worker is held.
        real_preflight(ctx)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            pids["worker"] = cursor.fetchone()[0]
        preflight_completed.set()
        if not allow_execute.wait(timeout=15):
            raise AssertionError("controller gate timed out")

    monkeypatch.setattr(real_handler, "preflight", gated_preflight)

    def worker():
        close_old_connections()
        try:
            result = engine.run_claimed(Job.objects.get(id=claimed.id))
            results["job"] = {"state": result.state, "error_code": result.error_code}
        except BaseException as exc:
            errors.append(repr(exc))
        finally:
            connections.close_all()

    thread = threading.Thread(target=worker, name="controller-authority-probe")
    thread.start()
    try:
        assert preflight_completed.wait(timeout=15), "production preflight never completed"
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            pids["controller"] = cursor.fetchone()[0]
        assert pids["worker"] != pids["controller"]
        changes = {"revoked_at": timezone.now()} if authority_change == "revoke" else {"role": Role.VIEWER}
        assert Membership.objects.filter(user=owner, tenant=tenant).update(**changes) == 1
    finally:
        allow_execute.set()
        thread.join(timeout=20)
    assert not thread.is_alive(), "worker did not stop"
    assert not errors, errors
    assert "job" in results, "worker did not publish its result"
    with tenant_scope(tenant.id):
        released = Router.objects.get(id=router.id).released_at is not None
    observed = {"probe": f"after_preflight_{authority_change}", **results["job"], "router_released": released, "distinct_db_connections": True}
    print(json.dumps(observed, sort_keys=True))
    assert (released, results["job"]["error_code"]) == (False, "authority_denied"), observed


def _rollback_job(monkeypatch, *, verified):
    tenant, owner = _identity("b6")
    router = _router(tenant, "rollback")
    with tenant_scope(tenant.id):
        Router.objects.filter(id=router.id).update(enforcement_mode=Router.Enforcement.RADIUS_AUTHORITATIVE)
        cutover = CutoverRun.objects.create(
            tenant=tenant, router=router, created_by=owner,
            phase=CutoverRun.Phase.B5, state=CutoverRun.State.AUTHORITATIVE,
            evidence={"B2": {"review_baseline": True}},
        )
    calls = []

    def record(op):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            pid = cursor.fetchone()[0]
        calls.append({"op": op, "in_atomic_block": connection.in_atomic_block, "autocommit": connection.get_autocommit(), "pid": pid})

    class ControlledRollbackAdapter:
        def rollback_radius(self, ctx, baseline):
            return {"controlled_plan": True}

        def apply_action(self, ctx, plan):
            record("apply")
            return {"applied": True}

        def verify_action(self, ctx, plan):
            record("verify")
            return {"verified": verified}

    monkeypatch.setattr("adapters.routeros.simulator.RouterOsSimulator", ControlledRollbackAdapter)
    job = engine.create_job(
        tenant_id=tenant.id, kind="radius_cutover_step", actor=owner,
        router=router, payload={"router_id": str(router.id), "rollback": True},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    final = engine.run_claimed(claimed)
    with tenant_scope(tenant.id):
        cutover.refresh_from_db()
        router.refresh_from_db()
        final.detail.refresh_from_db()
        detail_result = dict(final.detail.result or {})
    return {
        "job_state": final.state, "job_error": final.error_code,
        "run_state": cutover.state, "router_enforcement": router.enforcement_mode,
        "readback_ok": cutover.evidence.get("B6", {}).get("rollback_readback_ok"),
        "result": detail_result, "calls": calls,
    }


def test_b6_negative_readback_never_reports_success(monkeypatch):
    observed = _rollback_job(monkeypatch, verified=False)
    print(json.dumps({"probe": "b6_negative_verifier", **observed}, sort_keys=True))
    assert (
        observed["job_state"] != JobState.SUCCEEDED
        and observed["run_state"] != CutoverRun.State.ROLLED_BACK
        and observed["router_enforcement"] != Router.Enforcement.LOCAL
    ), observed


def test_b6_adapter_calls_run_outside_real_database_transaction(monkeypatch):
    observed = _rollback_job(monkeypatch, verified=True)
    print(json.dumps({"probe": "b6_transaction_boundary", **observed}, sort_keys=True))
    assert [item["op"] for item in observed["calls"]] == ["apply", "verify"]
    assert all(not item["in_atomic_block"] and item["autocommit"] for item in observed["calls"]), observed
