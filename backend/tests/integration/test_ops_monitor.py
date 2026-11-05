"""Tes integrasi monitoring M5 — pengelompokan jujur dari sampel kesehatan.

ROUTEROS.md §6 + UI_UX.md §10: tanpa sampel = unmonitored (bukan down);
sampel usang >3×interval = stale_data; VPN/API gagal = management_unreachable
(kondisi manajemen, bukan internet pelanggan); interfaces/radius tanpa data
→ kosong/null, bukan angka rekayasa.
"""
from __future__ import annotations

from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.network.models import Router, RouterHealthSample

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def router_a(tenant_a):
    with tenant_scope(tenant_a.id):
        return Router.objects.create(
            tenant=tenant_a, display_name="Router Monitor", router_code="RTR-M1", tunnel_ip="100.127.30.1"
        )


def _sample(router, *, observed_at, vpn_up=True, api_up=True, quality="ok"):
    with tenant_scope(router.tenant_id):
        return RouterHealthSample.objects.create(
            tenant_id=router.tenant_id,
            router=router,
            vpn_up=vpn_up,
            api_up=api_up,
            cpu_percent=10,
            memory_percent=30,
            uptime_s=7200,
            observed_at=observed_at,
            collected_at=observed_at,
            source="poller",
            quality=quality,
        )


class TestMonitorGrouping:
    def test_no_sample_unmonitored(self, tenant_a, router_a, auth_client):
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        item = items[0]
        assert item["router_id"] == str(router_a.id)
        assert item["group"] == "unmonitored"
        assert item["observed_at"] is None
        assert item["interfaces"] == []
        # Tanpa accounting RADIUS → blok radius null (jujur, §6).
        assert item["radius"] is None

    def test_fresh_healthy_sample(self, tenant_a, router_a, auth_client):
        _sample(router_a, observed_at=timezone.now())
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor")
        item = resp.json()[0]
        assert item["group"] == "healthy"
        assert item["source"] == "poller"
        assert item["observed_at"] is not None

    def test_stale_sample_marks_stale_data(self, tenant_a, router_a, auth_client):
        # Usang: > 3 × poll.health_s (3 × 60s = 180s) — ROUTEROS §6.
        _sample(router_a, observed_at=timezone.now() - timezone.timedelta(minutes=10))
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor")
        assert resp.json()[0]["group"] == "stale_data"

    def test_vpn_down_is_management_condition(self, tenant_a, router_a, auth_client):
        # VPN/API gagal = kondisi manajemen — TIDAK menyimpulkan pelanggan offline.
        _sample(router_a, observed_at=timezone.now(), vpn_up=False, api_up=True)
        assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor").json()[0]["group"] == (
            "management_unreachable"
        )

    def test_api_down_is_management_condition(self, tenant_a, router_a, auth_client):
        _sample(router_a, observed_at=timezone.now(), vpn_up=True, api_up=False)
        assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor").json()[0]["group"] == (
            "management_unreachable"
        )

    def test_flagged_quality_is_disturbed(self, tenant_a, router_a, auth_client):
        _sample(router_a, observed_at=timezone.now(), quality="degraded")
        assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor").json()[0]["group"] == "disturbed"

    def test_released_router_not_monitored(self, tenant_a, router_a, auth_client):
        with tenant_scope(tenant_a.id):
            router_a.released_at = timezone.now()
            router_a.save(update_fields=["released_at"])
        assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/monitor").json() == []

    def test_cross_tenant_monitor_404(self, tenant_a, tenant_b, auth_client):
        # owner A bukan anggota tenant B → 404 generik.
        assert auth_client.get(f"/api/v1/tenants/{tenant_b.id}/monitor").status_code == 404
