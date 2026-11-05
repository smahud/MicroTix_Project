"""Kontrak API M5-ops — bentuk respons mengikuti contracts.ts (frontend).

Sumber kebenaran: apps/web/src/api/contracts.ts — BackupArtifact,
BackupSchedule, MonitorStatus, PlatformPaymentSubmission, JobAccepted.
Ekstra field diizinkan; field kontrak TIDAK BOLEH hilang.
"""
from __future__ import annotations

import time

import pytest

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.network.models import Router
from domains.subscriptions import services as sub_services
from domains.subscriptions.models import PaymentSubmission
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.contract

# Persis contracts.ts (union literal).
BACKUP_CATEGORIES = {"routine", "manual", "pre_change"}
TRANSFER_STATES = {"committed", "staging", "verifying", "failed"}
MONITOR_GROUPS = {"healthy", "disturbed", "unmonitored", "stale_data", "management_unreachable"}
SUBMISSION_STATES = {"submitted", "reviewing", "approved", "revision_requested", "rejected"}

BACKUP_ARTIFACT_KEYS = {"id", "router_id", "generation", "created_at", "category", "size_bytes", "transfer_state", "encrypted"}
BACKUP_SCHEDULE_KEYS = {"router_id", "timezone", "frequency", "time_local", "artifact_type", "notification_enabled"}
MONITOR_KEYS = {"router_id", "group", "observed_at", "source", "interfaces", "radius"}
PLATFORM_SUBMISSION_KEYS = {
    "id",
    "tenant_display_name",
    "saas_invoice_id",
    "plan_code",
    "period_months",
    "amount",
    "submitted_at",
    "state",
    "assignee",
}


@pytest.fixture
def platform_client(api_client):
    admin = User.objects.create_user(
        email="platform-contract@test.local",
        full_name="Admin Kontrak",
        password=TEST_PASSWORD,
        is_active=True,
    )
    admin.platform_admin = True
    admin.save(update_fields=["platform_admin"])
    api_client.force_login(admin)
    session = api_client.session
    session["auth_at"] = time.time()
    session.save()
    return api_client


def test_openapi_paths_m5_ops(api_client):
    resp = api_client.get("/api/schema/?format=json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    for expected in (
        "/api/v1/tenants/{tenant_id}/backups",
        "/api/v1/tenants/{tenant_id}/backup-schedules",
        "/api/v1/tenants/{tenant_id}/routers/{router_id}/backups",
        "/api/v1/tenants/{tenant_id}/monitor",
        "/api/v1/platform/payment-submissions",
        "/api/v1/platform/payment-submissions/{submission_id}/approve",
        "/api/v1/platform/payment-submissions/{submission_id}/reject",
        "/api/v1/platform/payment-submissions/{submission_id}/request-revision",
    ):
        assert expected in paths, f"endpoint hilang: {expected}"


def test_backup_artifact_shape(tenant_a, auth_client):
    from domains.backups.models import BackupArtifact
    from domains.jobs import engine

    with tenant_scope(tenant_a.id):
        router = Router.objects.create(
            tenant=tenant_a,
            display_name="Router Kontrak",
            router_code="RTR-K1",
            tunnel_ip="100.127.40.1",
            credential_ref="cred-k",
        )
    resp = auth_client.post(
        f"/api/v1/tenants/{tenant_a.id}/routers/{router.id}/backups",
        {},
        headers={"Idempotency-Key": "ct-bk-1"},
    )
    assert resp.status_code == 202
    accepted = resp.json()
    # JobAccepted: job_id + status_url (tanpa ETA palsu).
    assert set(accepted.keys()) >= {"job_id", "status_url"}
    job = engine.claim_next()
    assert engine.run_claimed(job).state == "succeeded"

    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backups")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert BACKUP_ARTIFACT_KEYS <= set(item.keys())
    assert item["category"] in BACKUP_CATEGORIES
    assert item["transfer_state"] in TRANSFER_STATES
    assert item["encrypted"] is True
    assert isinstance(item["size_bytes"], int)
    # id/generation konsisten dengan katalog.
    with tenant_scope(tenant_a.id):
        artifact = BackupArtifact.objects.get()
        assert item["id"] == str(artifact.id)
        assert item["generation"] == artifact.generation


def test_backup_schedule_shape(tenant_a, auth_client):
    with tenant_scope(tenant_a.id):
        Router.objects.create(tenant=tenant_a, display_name="Router Jadwal", router_code="RTR-K2")
    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backup-schedules")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert BACKUP_SCHEDULE_KEYS <= set(item.keys())
    assert item["frequency"] in {"daily", "weekly"}
    assert item["artifact_type"] in {"binary", "export"}
    assert isinstance(item["notification_enabled"], bool)
    assert ":" in item["time_local"]


def test_monitor_status_shape(tenant_a, auth_client):
    with tenant_scope(tenant_a.id):
        Router.objects.create(tenant=tenant_a, display_name="Router Monitor", router_code="RTR-K3")
    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert MONITOR_KEYS <= set(item.keys())
    assert item["group"] in MONITOR_GROUPS
    assert isinstance(item["source"], str)
    assert isinstance(item["interfaces"], list)
    # Beta: tanpa accounting RADIUS blok radius null — bukan rasio rekayasa.
    assert item["radius"] is None


def test_platform_submission_shape(tenant_a, owner, platform_client):
    with tenant_scope(tenant_a.id):
        invoice, _plan = sub_services.create_quotation(tenant_a.id, "gold", "monthly")
        PaymentSubmission.objects.create(
            tenant=tenant_a,
            invoice=invoice,
            amount=invoice.amount,
            proof_path="payment-proofs/ct",
            proof_mime="image/png",
            proof_size=512,
            submitted_by=owner,
        )
    resp = platform_client.get("/api/v1/platform/payment-submissions?queue=submitted")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert PLATFORM_SUBMISSION_KEYS <= set(item.keys())
    assert item["state"] in SUBMISSION_STATES
    assert item["plan_code"] == "gold"
    assert item["period_months"] == 1
    # Uang numeric(20,2) sebagai string JSON (§4).
    assert isinstance(item["amount"], str) and "." in item["amount"]
    assert item["tenant_display_name"] == "Tenant A"
    assert item["assignee"] is None
