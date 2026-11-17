"""Kontrak API M3: enrollment, access-accounts, radius-status, probe (§5)."""
from __future__ import annotations

import pytest

from domains.common.tenant_context import tenant_scope
from domains.network.models import RouterEnrollment

pytestmark = pytest.mark.contract


@pytest.fixture
def wg_settings(settings):
    settings.MT_WG_SERVER_PUBKEY = "testwgpubkey1234567890abcdef1234567890abcdef1234="
    settings.MT_ENROLL_VERIFY_SOURCE = False
    settings.MT_PUBLIC_BASE_URL = "https://microtix.test"
    settings.MT_WG_ENDPOINT = "wg.microtix.test:51820"
    return settings


class TestEnrollmentContract:
    def test_create_enrollment_response_shape(self, auth_client, tenant_a, wg_settings):
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {"display_name": "GW Contract", "router_code": "RT-KONTRAK", "location": "POP Utama"},
            headers={"Idempotency-Key": "enr-1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        for field in ("id", "state", "tunnel_ip", "token", "token_expires_at", "bootstrap_url"):
            assert field in body, f"field {field} hilang"
        assert body["state"] == "enrollment_issued"
        assert body["tunnel_ip"].startswith("100.127.")

    def test_enrollment_requires_permission(self, api_client, owner, tenant_a, wg_settings):
        # Tanpa sesi → ditolak (401/403 sesuai jalur DRF) dengan envelope stabil.
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {"display_name": "X", "router_code": "RT-X"},
        )
        assert resp.status_code in (401, 403)
        assert resp.json()["code"] in ("unauthenticated", "unauthorized", "forbidden")

    def test_progress_endpoint(self, auth_client, tenant_a, wg_settings):
        created = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {"display_name": "GW Prog", "router_code": "RT-PROG"},
        )
        eid = created.json()["id"]
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{eid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enrollment_id"] == eid
        assert isinstance(body["stage_detail"], list) and body["stage_detail"]
        for stage in body["stage_detail"]:
            assert stage["state"] in ("pending", "ok", "failed")

    def test_bootstrap_endpoint_token_gated(self, auth_client, tenant_a, wg_settings):
        created = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {"display_name": "GW Boot", "router_code": "RT-BOOT"},
        )
        body = created.json()
        eid, token = body["id"], body["token"]
        # Tanpa token → 422.
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{eid}/bootstrap")
        assert resp.status_code == 422
        # Token salah → 401.
        resp = auth_client.get(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{eid}/bootstrap?token=salah"
        )
        assert resp.status_code == 401
        # Token benar → script + sensitive flag.
        resp = auth_client.get(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{eid}/bootstrap?token={token}"
        )
        assert resp.status_code == 200
        assert resp.json()["sensitive"] is True
        assert "rtrw-wg-RT-BOOT" in resp.json()["script"]

    def test_probe_public_endpoint_flow(self, api_client, tenant_a, wg_settings):
        created = api_client.post  # placeholder — pakai auth untuk create
        auth = api_client
        # Buat via service (tanpa sesi API) untuk isolasi probe:
        from domains.network import enrollment as enrollment_service
        from domains.identity.models import User

        owner = User.objects.filter(email="owner@test.local").first()
        enrollment, token = enrollment_service.create_enrollment(
            tenant_id=tenant_a.id, actor=owner, display_name="GW Probe", router_code="RT-PROBE"
        )
        # Probe TANPA sesi (dipanggil router melalui tunnel; token di body).
        resp = api_client.post(
            f"/api/v1/router-enrollments/{enrollment.id}/probe",
            {
                "token": token,
                "nonce": "RT-PROBE-enroll",
                "router_identity": "MikroTik-Probe",
                "routeros_version": "7.16.1",
                "architecture": "arm64",
                "wireguard_pubkey": "pubkey-x",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "consumed"
        assert resp.json()["mode"] == "read_only"
        # Replay: logical.
        resp2 = api_client.post(
            f"/api/v1/router-enrollments/{enrollment.id}/probe",
            {
                "token": token,
                "nonce": "RT-PROBE-enroll",
                "router_identity": "MikroTik-Probe",
                "routeros_version": "7.16.1",
                "architecture": "arm64",
                "wireguard_pubkey": "pubkey-x",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["state"] == "already_completed"


class TestAccessContract:
    def test_access_accounts_list_and_patch(self, auth_client, tenant_a):
        from domains.access import services as access_services
        from domains.customers.models import Customer, Service

        with tenant_scope(tenant_a.id):
            customer = Customer.objects.create(tenant=tenant_a, full_name="Kontrak A")
            service = Service.objects.create(tenant=tenant_a, customer=customer)
            account = access_services.create_access_account(
                tenant_id=tenant_a.id, username="kontrak-001", password="password-123", service=service
            )
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] and body["items"][0]["username"] == "kontrak-001"
        assert "next_cursor" in body and "has_more" in body

        # Suspend via PATCH.
        resp = auth_client.patch(
            f"/api/v1/tenants/{tenant_a.id}/access-accounts/{account.id}",
            {"state": "suspended"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "suspended"
        # Activate kembali.
        resp = auth_client.patch(
            f"/api/v1/tenants/{tenant_a.id}/access-accounts/{account.id}",
            {"state": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "active"

    def test_radius_status_shape(self, auth_client, tenant_a, wg_settings):
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/radius-status")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_discovery_starts_job(self, auth_client, tenant_a, wg_settings):
        from domains.network.models import Router

        with tenant_scope(tenant_a.id):
            router = Router.objects.create(
                tenant=tenant_a, display_name="RT Job", router_code="RT-JOB", tunnel_ip="100.127.99.1"
            )
        resp = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/routers/{router.id}/discoveries")
        assert resp.status_code == 202
        assert "job_id" in resp.json()
