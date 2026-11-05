"""Kontrak API RADIUS — bentuk respons persis contracts.ts (RadiusRouterStatus)."""
from __future__ import annotations

import pytest

from domains.common.tenant_context import tenant_scope
from domains.network.models import Router

pytestmark = pytest.mark.contract

RADIUS_STATUS_KEYS = {
    "router_id",
    "enforcement_mode",
    "migrated_accounts",
    "auth_success_ratio_24h",
    "inbound_sessions_24h",
    "last_accounting_at",
    "radius_primary",
    "radius_secondary",
    "client_status",
}


@pytest.fixture
def rad_client(api_client, owner, tenant_a):
    api_client.force_login(owner)
    session = api_client.session
    session["active_tenant_id"] = str(tenant_a.id)
    session.save()
    return api_client


def test_radius_status_list_shape(rad_client, tenant_a):
    with tenant_scope(tenant_a.id):
        Router.objects.create(
            tenant_id=tenant_a.id, display_name="R Kontrak", router_code="rtr-kon-1", tunnel_ip="100.127.6.9"
        )
    resp = rad_client.get(f"/api/v1/tenants/{tenant_a.id}/radius-status")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list) and len(items) == 1
    assert set(items[0].keys()) == RADIUS_STATUS_KEYS
    assert items[0]["radius_secondary"] is None  # beta: tanpa HA — jujur
    assert items[0]["migrated_accounts"] == 0  # belum ada proyeksi


def test_radius_status_detail_shape(rad_client, tenant_a):
    with tenant_scope(tenant_a.id):
        router = Router.objects.create(
            tenant_id=tenant_a.id, display_name="R Kontrak 2", router_code="rtr-kon-2", tunnel_ip="100.127.6.10"
        )
    resp = rad_client.get(f"/api/v1/tenants/{tenant_a.id}/radius-status/{router.id}")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == RADIUS_STATUS_KEYS


def test_radius_status_foreign_tenant_404(rad_client, tenant_a, tenant_b):
    with tenant_scope(tenant_b.id):
        router = Router.objects.create(
            tenant_id=tenant_b.id, display_name="RT B", router_code="rtr-kon-b", tunnel_ip="100.127.6.11"
        )
    resp = rad_client.get(f"/api/v1/tenants/{tenant_a.id}/radius-status/{router.id}")
    assert resp.status_code == 404


def test_radius_cutover_202_shape(rad_client, tenant_a):
    from domains.customers.services import provision_service_draft
    from domains.radius.projection import project_nas

    with tenant_scope(tenant_a.id):
        router = Router.objects.create(
            tenant_id=tenant_a.id,
            display_name="R Cut Kontrak",
            router_code="rtr-kon-3",
            tunnel_ip="100.127.6.12",
            mode=Router.Mode.MANAGED,
            credential_ref="enc:k",
        )
        provision_service_draft(
            tenant_a,
            {"customer_name": "P", "username": "kon.user", "password": "pw-1234567890ab", "kind": "pppoe"},
        )
        project_nas(router)
    # radius.cutover sensitif → reauth dulu.
    session = rad_client.session
    session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()
    resp = rad_client.post(
        f"/api/v1/tenants/{tenant_a.id}/routers/{router.id}/radius-cutover",
        headers={"Idempotency-Key": "kon-cutover-1"},
    )
    assert resp.status_code == 202
    assert set(resp.json().keys()) == {"job_id", "status_url"}
    assert resp.json()["status_url"].startswith("/api/v1/jobs/")
