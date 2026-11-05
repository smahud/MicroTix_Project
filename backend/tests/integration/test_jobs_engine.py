"""Isolasi tenant pada API — 404 lintas tenant, izin per peran (TK-102)."""
from __future__ import annotations

import pytest

from domains.identity.models import User
from domains.tenancy.models import Membership, Role
from domains.jobs import engine
from domains.jobs.engine import JobContext, JobError, JobHandler

pytestmark = pytest.mark.integration


class _OkHandler(JobHandler):
    kind = "_test_ok"

    def execute(self, ctx: JobContext):
        ctx.progress(phase="bekerja", done=1, total=1)
        return {"ok": True}

    def verify(self, ctx: JobContext):
        return {"ok": True}


class _UncertainHandler(JobHandler):
    kind = "_test_uncertain"

    def execute(self, ctx: JobContext):
        raise JobError(code="timeout_after_send", uncertain=True)

    def verify(self, ctx: JobContext):
        return {}


class _RetryableHandler(JobHandler):
    kind = "_test_retry"

    def execute(self, ctx: JobContext):
        raise JobError(code="router_unreachable", retryable=True)

    def verify(self, ctx: JobContext):
        return {}


@pytest.fixture(autouse=True)
def _register_handlers():
    for handler in (_OkHandler(), _UncertainHandler(), _RetryableHandler()):
        try:
            engine.register(handler)
        except ValueError:
            pass
    yield


def test_job_end_to_end_success(tenant_a, owner):
    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_ok", actor=owner, payload={"x": 1})
    assert job.state == "queued"
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    assert claimed.state == "claimed"
    result = engine.run_claimed(claimed)
    assert result.state == "succeeded"
    assert result.effect_state == "confirmed"
    assert result.items_done == 1


def test_job_uncertain_on_timeout_after_send(tenant_a):
    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_uncertain")
    claimed = engine.claim_next()
    result = engine.run_claimed(claimed)
    # Kunci: hasil tak pasti ≠ failed (ARCHITECTURE §6).
    assert result.state == "uncertain"
    assert result.error_code == "timeout_after_send"


def test_job_retry_then_backoff(tenant_a):
    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_retry")
    claimed = engine.claim_next()
    result = engine.run_claimed(claimed)
    assert result.state == "retry_wait"
    assert result.attempt == 1
    assert result.available_at > result.updated_at  # backoff di masa depan
    # retry_wait belum jatuh tempo → tidak diklaim ulang
    assert engine.claim_next() is None


def test_job_cancel_rules(tenant_a):
    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_ok")
    cancelled = engine.cancel_job(job, "uji")
    assert cancelled.state == "cancelled"
    # Job executing dengan efek 'none' boleh dibatalkan; efek 'maybe' tidak.
    job2 = engine.create_job(tenant_id=tenant_a.id, kind="_test_ok")
    claimed = engine.claim_next()
    engine.transition_claimed(claimed, "preflight")
    engine.transition_claimed(claimed, "executing", effect_state="maybe")
    with pytest.raises(ValueError):
        engine.cancel_job(claimed, "dilarang")


def test_job_retry_creates_new_job_linking_origin(tenant_a):
    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_ok")
    engine.cancel_job(job, "uji")
    new_job = engine.retry_job(job)
    assert new_job.id != job.id
    assert new_job.origin_job_id == job.id
    assert new_job.state == "queued"


def test_lease_expiry_reconcile_to_uncertain(tenant_a):
    from django.utils import timezone

    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_ok")
    claimed = engine.claim_next()
    engine.transition_claimed(claimed, "preflight")
    engine.transition_claimed(claimed, "executing")
    # Paksa lease kedaluwarsa.
    from domains.jobs.models import Job

    Job.objects.filter(id=job.id).update(lease_expires_at=timezone.now() - timezone.timedelta(seconds=1))
    n = engine.reconcile_expired_leases()
    assert n >= 1
    job.refresh_from_db()
    assert job.state == "uncertain"
    assert job.error_code == "lease_expired"


def test_unknown_kind_rejected(tenant_a):
    with pytest.raises(ValueError):
        engine.create_job(tenant_id=tenant_a.id, kind="acs_task")  # fase R3: belum ada handler


def test_api_cross_tenant_job_404(tenant_a, tenant_b, auth_client, owner):
    # Buat job tenant B oleh owner B.
    from domains.tenancy.models import Membership

    job = engine.create_job(tenant_id=tenant_b.id, kind="_test_ok")
    # owner A (auth_client) meminta detail job tenant B → 404 generik.
    resp = auth_client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
    # Envelope error standar.
    body = resp.json()
    assert {"code", "message", "request_id", "locale"} <= set(body.keys())


def test_api_job_flow_visible_to_owner(tenant_a, auth_client):
    job = engine.create_job(tenant_id=tenant_a.id, kind="_test_ok")
    resp = auth_client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(job.id)
    assert data["state"] == "queued"
    assert "kind" in data and "retryable" in data


def test_api_tenant_routes_require_membership(auth_client, tenant_b):
    resp = auth_client.get(f"/api/v1/tenants/{tenant_b.id}/jobs")
    # owner A bukan anggota tenant B → 404 generik (bukan 403).
    assert resp.status_code == 404


def test_api_role_permission_403(tenant_a, auth_client):
    # Viewer tidak boleh quotations (subscription.manage sensitif).
    viewer = User.objects.create_user(
        email="viewer@test.local", full_name="Viewer", password="pass-123456789012", is_active=True
    )
    Membership.objects.create(user=viewer, tenant=tenant_a, role=Role.VIEWER)
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=False)
    client.force_login(viewer)
    session = client.session
    session["active_tenant_id"] = str(tenant_a.id)
    session["auth_at"] = __import__("time").time()
    session.save()
    resp = client.get(f"/api/v1/tenants/{tenant_a.id}/subscription")
    assert resp.status_code == 200  # customers.read boleh
    resp = client.post(
        f"/api/v1/tenants/{tenant_a.id}/quotations",
        {"plan_code": "silver", "term": "monthly"},
        headers={"Idempotency-Key": "test-key-1"},
    )
    assert resp.status_code == 403  # tanpa subscription.manage
