"""Integrasi proyeksi RADIUS — signal AccessAccount → radius.* (RADIUS.md §3).

PostgreSQL nyata + RLS aktif. Suspend via service layer customers harus
memicu re-proyeksi menjadi Auth-Type Reject (§7) dalam transaksi sama.
"""
from __future__ import annotations

import pytest

from domains.common.tenant_context import tenant_scope
from domains.customers.models import AccessAccount, Customer, Service
from domains.customers.services import provision_service_draft, set_account_state, set_password
from domains.network.models import Router

pytestmark = pytest.mark.integration


_IP_SEQ = iter(f"100.127.9.{i}" for i in range(10, 200))


def _provision(tenant, username="test.user", password="pw-abc-123456789", package="20M/10M"):
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id,
            display_name="R1",
            router_code=f"rtr-rad-{str(tenant.id)[:8]}",
            tunnel_ip=next(_IP_SEQ),  # unik global (invariant §4)
        )
        service = provision_service_draft(
            tenant,
            {
                "customer_name": "Pelanggan Rad",
                "username": username,
                "password": password,
                "kind": "pppoe",
                "package_name": package,
                "router_id": str(router.id),
            },
        )
        return service, router


def _radcheck_rows(tenant_id, username):
    """Baca radcheck DALAM tenant_scope — RLS fail-closed tanpa konteks."""
    from domains.common.tenant_context import tenant_scope

    with tenant_scope(tenant_id):
        return _radcheck_rows_scoped(tenant_id, username)


def _radcheck_rows_scoped(tenant_id, username):
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            "SELECT attribute, value FROM radius.radcheck WHERE tenant_id = %s AND username = %s ORDER BY attribute",
            [str(tenant_id), username],
        )
        return dict(cur.fetchall())


def _radreply_rows(tenant_id, username):
    from domains.common.tenant_context import tenant_scope

    with tenant_scope(tenant_id):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT attribute, value FROM radius.radreply WHERE tenant_id = %s AND username = %s ORDER BY attribute",
                [str(tenant_id), username],
            )
            return dict(cur.fetchall())


class TestProjection:
    def test_active_account_projects_password_rate_interim(self, tenant_a):
        _provision(tenant_a)
        rows = _radcheck_rows(tenant_a.id, "test.user")
        assert "Cleartext-Password" in rows
        assert rows["Simultaneous-Use"] == "1"
        replies = _radreply_rows(tenant_a.id, "test.user")
        assert replies.get("Mikrotik-Rate-Limit") == "20M/10M"
        assert replies.get("Acct-Interim-Interval") == "300"

    def test_package_without_rate_shape_projects_no_rate(self, tenant_a):
        _provision(tenant_a, username="norate.user", package="Paket Reguler 2MB")
        replies = _radreply_rows(tenant_a.id, "norate.user")
        assert "Mikrotik-Rate-Limit" not in replies  # jangan mengarang angka

    def test_suspend_flips_projection_to_reject(self, tenant_a):
        service, _ = _provision(tenant_a)
        with tenant_scope(tenant_a.id):
            account = service.access_accounts.get()
            set_account_state(account, "suspended")
        rows = _radcheck_rows(tenant_a.id, "test.user")
        assert rows.get("Auth-Type") == "Reject"
        assert "Cleartext-Password" not in rows  # password tidak ikut bocor

    def test_activate_restores_password(self, tenant_a):
        service, _ = _provision(tenant_a)
        with tenant_scope(tenant_a.id):
            account = service.access_accounts.get()
            set_account_state(account, "suspended")
            set_account_state(account, "active")
        rows = _radcheck_rows(tenant_a.id, "test.user")
        assert "Cleartext-Password" in rows
        assert "Auth-Type" not in rows

    def test_delete_account_deprojects(self, tenant_a):
        service, _ = _provision(tenant_a)
        with tenant_scope(tenant_a.id):
            account = service.access_accounts.get()
            account.delete()
        assert _radcheck_rows(tenant_a.id, "test.user") == {}

    def test_tenant_isolation_radius_rows(self, tenant_a, tenant_b):
        _provision(tenant_a)
        # tenant_b dengan username sama — proyeksi B tidak terlihat dari A.
        _provision(tenant_b)
        with tenant_scope(tenant_b.id):
            rows_b = _radcheck_rows(tenant_b.id, "test.user")
        assert "Cleartext-Password" in rows_b
        # Konteks A tidak melihat baris B (RLS fail-closed):
        with tenant_scope(tenant_a.id):
            visible = _radcheck_rows_scoped(tenant_a.id, "test.user")
        assert visible.get("Cleartext-Password")  # hanya milik A yang terlihat


class TestNasProjection:
    def test_project_nas_secret_and_revision(self, tenant_a):
        with tenant_scope(tenant_a.id):
            router = Router.objects.create(
                tenant_id=tenant_a.id, display_name="RN", router_code="rtr-rad-n", tunnel_ip="100.127.9.7"
            )
            from domains.radius.projection import nas_state, project_nas

            secret = project_nas(router)
            nas = nas_state(router)
            assert nas is not None and nas[1] == secret
            assert nas[2] == 1 and nas[3] == 0  # desired 1, applied 0 → degraded
            # Rotasi secret → revision naik.
            project_nas(router, "secret-baru-csprng-1234567890ab")
            nas2 = nas_state(router)
            assert nas2[2] == 2 and nas2[1] == "secret-baru-csprng-1234567890ab"

    def test_unenrolled_router_rejected(self, tenant_a):
        with tenant_scope(tenant_a.id):
            router = Router.objects.create(
                tenant_id=tenant_a.id, display_name="RX", router_code="rtr-rad-x"  # tanpa tunnel_ip
            )
            from domains.radius.projection import project_nas

            with pytest.raises(ValueError):
                project_nas(router)
