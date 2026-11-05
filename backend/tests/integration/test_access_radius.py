"""Integrasi domain akses: proyeksi radius.*, RLS, facade SQL (RAD-02/03/04/05/06)."""
from __future__ import annotations

import pytest

from domains.access import services as access_services
from domains.access.models import AccessAccount, Nas
from domains.common.tenant_context import tenant_scope
from domains.customers.models import Customer, Service
from domains.network.models import Router

pytestmark = pytest.mark.integration


def _router(tenant, *, code="RT-01", tunnel_ip="100.127.0.10"):
    with tenant_scope(tenant.id):
        return Router.objects.create(
            tenant=tenant, display_name=f"Router {code}", router_code=code, tunnel_ip=tunnel_ip
        )


def _service(tenant, name="Budi"):
    with tenant_scope(tenant.id):
        customer = Customer.objects.create(tenant=tenant, full_name=name)
        return Service.objects.create(tenant=tenant, customer=customer, state=Service.State.PROVISIONED)


class TestProjection:
    def test_create_projects_check_and_reply(self, tenant_a):
        service = _service(tenant_a)
        account = access_services.create_access_account(
            tenant_id=tenant_a.id,
            username="cust-001",
            password="password-123",
            service=service,
            rate_limit_rx_kbps=10_000,
            rate_limit_tx_kbps=20_000,
        )
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT attribute, op, value FROM radius.radcheck WHERE account_id = %s ORDER BY id",
                    [account.id],
                )
                checks = cur.fetchall()
                cur.execute(
                    "SELECT attribute, value FROM radius.radreply WHERE account_id = %s", [account.id]
                )
                replies = cur.fetchall()
        assert ("Cleartext-Password", ":=", "password-123") in checks
        assert ("Mikrotik-Rate-Limit", "10000000/20000000") in replies
        # Password disimpan terenkripsi di sumber kebenaran — bukan plaintext.
        assert account.secret_ref != "password-123"
        assert len(account.secret_ref) > 40

    def test_suspend_replaces_projection_with_reject(self, tenant_a):
        service = _service(tenant_a, "Siti")
        account = access_services.create_access_account(
            tenant_id=tenant_a.id, username="cust-002", password="password-456", service=service
        )
        access_services.set_account_state(account, new_state="suspended")
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("SELECT attribute, value FROM radius.radcheck WHERE account_id = %s", [account.id])
                checks = cur.fetchall()
        # Hanya Auth-Type Reject — kredensial tidak diproyeksikan saat tertolak.
        assert checks == [("Auth-Type", "Reject")]
        with tenant_scope(tenant_a.id):
            account.refresh_from_db()
        assert account.state == "suspended"
        assert account.revision == 2

    def test_activate_reprojects_normal_attributes(self, tenant_a):
        service = _service(tenant_a, "Tono")
        account = access_services.create_access_account(
            tenant_id=tenant_a.id, username="cust-003", password="password-789", service=service
        )
        access_services.set_account_state(account, new_state="suspended")
        access_services.set_account_state(account, new_state="active")
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("SELECT attribute, value FROM radius.radcheck WHERE account_id = %s", [account.id])
                checks = dict(cur.fetchall())
        assert checks.get("Cleartext-Password") == "password-789"
        assert "Auth-Type" not in checks

    def test_rotate_password_updates_projection_atomically(self, tenant_a):
        service = _service(tenant_a, "Rina")
        account = access_services.create_access_account(
            tenant_id=tenant_a.id, username="cust-004", password="old-password-1", service=service
        )
        access_services.rotate_password(account, new_password="new-password-2")
        assert access_services.reveal_password(account) == "new-password-2"
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT value FROM radius.radcheck WHERE account_id = %s AND attribute = 'Cleartext-Password'",
                    [account.id],
                )
                (value,) = cur.fetchone()
        assert value == "new-password-2"

    def test_username_unique_per_tenant(self, tenant_a):
        service = _service(tenant_a, "Dua")
        access_services.create_access_account(
            tenant_id=tenant_a.id, username="shared-name", password="password-123", service=service
        )
        with pytest.raises(access_services.AccessError) as exc:
            access_services.create_access_account(
                tenant_id=tenant_a.id, username="shared-name", password="password-456"
            )
        assert exc.value.code == "username_taken"

    def test_short_password_rejected(self, tenant_a):
        with pytest.raises(access_services.AccessError):
            access_services.create_access_account(
                tenant_id=tenant_a.id, username="cust-x", password="short"
            )


class TestRadiusTenantIsolation:
    def test_radius_rows_rls_isolated(self, tenant_a, tenant_b):
        """Tabel radius.* memakai RLS tenant — B tidak melihat baris A."""
        service_a = _service(tenant_a, "Isolasi A")
        access_services.create_access_account(
            tenant_id=tenant_a.id, username="iso-user", password="password-123", service=service_a
        )
        from django.db import connection

        # Konteks tenant B: nol baris proyeksi milik A.
        with tenant_scope(tenant_b.id):
            with connection.cursor() as cur:
                cur.execute("SELECT count(*) FROM radius.radcheck")
                (count_b_sees,) = cur.fetchone()
        assert count_b_sees == 0
        # Konteks tenant A: baris milik A terlihat.
        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("SELECT count(*) FROM radius.radcheck")
                (count_a_sees,) = cur.fetchone()
        assert count_a_sees >= 1

    def test_same_username_two_tenants_both_projected(self, tenant_a, tenant_b):
        """Username sama lintas tenant valid (namespace per tenant; RAD-02)."""
        service_a = _service(tenant_a, "Nama Sama A")
        service_b = _service(tenant_b, "Nama Sama B")
        access_services.create_access_account(
            tenant_id=tenant_a.id, username="duo-user", password="password-a1", service=service_a
        )
        access_services.create_access_account(
            tenant_id=tenant_b.id, username="duo-user", password="password-b2", service=service_b
        )
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("SELECT value FROM radius.radcheck WHERE username = 'duo-user' AND attribute = 'Cleartext-Password'")
                (value_a,) = cur.fetchone()
        with tenant_scope(tenant_b.id):
            with connection.cursor() as cur:
                cur.execute("SELECT value FROM radius.radcheck WHERE username = 'duo-user' AND attribute = 'Cleartext-Password'")
                (value_b,) = cur.fetchone()
        assert value_a == "password-a1"
        assert value_b == "password-b2"


class TestFacade:
    def _setup_tenant_nas(self, tenant, *, tunnel_ip, username, password):
        router = _router(tenant, code=f"RT-{tunnel_ip.split('.')[-1]}", tunnel_ip=tunnel_ip)
        service = _service(tenant, f"Pelanggan {tunnel_ip}")
        access_services.create_access_account(
            tenant_id=tenant.id, username=username, password=password, service=service
        )
        nas = access_services.ensure_nas(tenant_id=tenant.id, router=router, shortname=f"nas-{tunnel_ip}")
        return router, nas

    def test_facade_binds_tenant_from_nas_ip(self, tenant_a, tenant_b):
        """RAD-03: NAS IP adalah satu-satunya pengikat tenant; payload tidak."""
        self._setup_tenant_nas(tenant_a, tunnel_ip="100.127.0.10", username="facade-user", password="password-a")
        self._setup_tenant_nas(tenant_b, tunnel_ip="100.127.0.20", username="facade-user", password="password-b")
        from django.db import connection

        # NAS tenant A hanya menghasilkan atribut tenant A.
        with connection.cursor() as cur:
            cur.execute("SELECT attribute, value FROM radius.facade_check('100.127.0.10', 'facade-user')")
            rows_a = cur.fetchall()
            cur.execute("SELECT attribute, value FROM radius.facade_check('100.127.0.20', 'facade-user')")
            rows_b = cur.fetchall()
        assert dict(rows_a).get("Cleartext-Password") == "password-a"
        assert dict(rows_b).get("Cleartext-Password") == "password-b"

    def test_unknown_nas_returns_nothing(self, tenant_a):
        """NAS tak dikenal: secure discard — tanpa baris, tanpa Accept."""
        self._setup_tenant_nas(tenant_a, tunnel_ip="100.127.0.11", username="anyone", password="password-c")
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT count(*) FROM radius.facade_check('100.127.9.9', 'anyone')")
            (count,) = cur.fetchone()
        assert count == 0

    def test_suspended_via_facade_rejects(self, tenant_a):
        router = _router(tenant_a, code="RT-SUS", tunnel_ip="100.127.0.12")
        service = _service(tenant_a, "Tertolak")
        account = access_services.create_access_account(
            tenant_id=tenant_a.id, username="suspended-user", password="password-d", service=service
        )
        access_services.ensure_nas(tenant_id=tenant_a.id, router=router, shortname="nas-sus")
        access_services.set_account_state(account, new_state="suspended")
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT attribute, value FROM radius.facade_check('100.127.0.12', 'suspended-user')")
            rows = dict(cur.fetchall())
        assert rows.get("Auth-Type") == "Reject"
        assert "Cleartext-Password" not in rows

    def test_nas_projection_contains_secret(self, tenant_a):
        router = _router(tenant_a, code="RT-NAS", tunnel_ip="100.127.0.13")
        nas = access_services.ensure_nas(tenant_id=tenant_a.id, router=router, shortname="nas-proj")
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("SELECT nasname, secret, type FROM radius.nas WHERE router_id = %s", [router.id])
                row = cur.fetchone()
        assert row[0] == "100.127.0.13"
        assert row[1] and len(row[1]) == 32  # secret CSPRNG 32 karakter
        assert row[2] == "other"
        assert nas.desired_revision == 1 and nas.applied_revision is None


class TestNasLifecycle:
    def test_rotate_nas_secret_bumps_desired_revision(self, tenant_a):
        router = _router(tenant_a, code="RT-ROT", tunnel_ip="100.127.0.14")
        nas = access_services.ensure_nas(tenant_id=tenant_a.id, router=router, shortname="nas-rot")
        old_secret = access_services.nas_secret(nas)
        access_services.rotate_nas_secret(nas)
        with tenant_scope(tenant_a.id):
            nas.refresh_from_db()
        assert nas.desired_revision == 2
        assert nas.applied_revision is None  # applied hanya setelah probe
        assert access_services.nas_secret(nas) != old_secret

    def test_pending_and_mark_applied(self, tenant_a):
        router = _router(tenant_a, code="RT-APL", tunnel_ip="100.127.0.15")
        nas = access_services.ensure_nas(tenant_id=tenant_a.id, router=router, shortname="nas-apl")
        pending = access_services.nas_pending_reconciliation(tenant_a.id)
        assert any(p["id"] == str(nas.id) for p in pending)
        access_services.mark_nas_applied(nas, revision=1)
        pending = access_services.nas_pending_reconciliation(tenant_a.id)
        assert not any(p["id"] == str(nas.id) for p in pending)
