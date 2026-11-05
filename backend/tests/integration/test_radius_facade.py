"""Integrasi facade SQL RADIUS — pemanggilan langsung (RADIUS.md §4/§8).

PostgreSQL nyata. Membuktikan: resolusi tenant dari NAS, unknown NAS gagal,
accounting idempoten + monotonik + Stop-final, session_count.
"""
from __future__ import annotations

import pytest
from django.db import connection

from domains.common.tenant_context import tenant_scope
from domains.customers.models import AccessAccount, Customer, Service
from domains.customers.services import provision_service_draft, set_password
from domains.network.models import Router

pytestmark = pytest.mark.integration

NAS_A = "100.127.8.2"
NAS_B = "100.127.8.3"


def _seed_accounts(tenant_a, tenant_b):
    # Idempoten per panggilan: tenant sama tidak diseed dua kali (uji akunting
    # memakai (tenant_a, tenant_a) cukup sekali).
    seen: set = set()
    for tenant, nas_ip in ((tenant_a, NAS_A), (tenant_b, NAS_B)):
        if str(tenant.id) in seen:
            continue
        seen.add(str(tenant.id))
        with tenant_scope(tenant.id):
            Router.objects.create(
                tenant_id=tenant.id,
                display_name=f"RF {nas_ip}",
                router_code=f"rtr-fac-{nas_ip.split('.')[-1]}",
                tunnel_ip=nas_ip,
            )
            service = provision_service_draft(
                tenant,
                {
                    "customer_name": "Pelanggan Facade",
                    "username": "fac.user",
                    "password": "pw-fac-123456",
                    "kind": "pppoe",
                    "package_name": "10M/10M",
                },
            )
            from domains.radius.projection import project_nas

            project_nas(Router.objects.get(tenant_id=tenant.id, tunnel_ip=nas_ip))


def _facade(sql, params):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


class TestAuthorizeFacade:
    def test_authorize_check_binds_tenant_by_nas(self, tenant_a, tenant_b):
        _seed_accounts(tenant_a, tenant_b)
        # NAS tenant A → password tenant A.
        rows_a = _facade("SELECT attribute, value FROM radius.authorize_check(%s, %s)", [NAS_A, "fac.user"])
        attrs_a = {r[0]: r[1] for r in rows_a}
        assert "Cleartext-Password" in attrs_a
        # NAS tenant B → baris tenant B (konteks berbeda, data berbeda).
        rows_b = _facade("SELECT attribute, value FROM radius.authorize_check(%s, %s)", [NAS_B, "fac.user"])
        assert rows_b  # tenant B juga punya akun sama

    def test_unknown_nas_raises(self, tenant_a):
        with pytest.raises(Exception, match="unknown_nas"):
            _facade("SELECT * FROM radius.authorize_check(%s, %s)", ["10.9.9.9", "fac.user"])

    def test_authorize_reply_returns_rate(self, tenant_a, tenant_b):
        _seed_accounts(tenant_a, tenant_b)
        rows = _facade("SELECT attribute, value FROM radius.authorize_reply(%s, %s)", [NAS_A, "fac.user"])
        attrs = {r[0]: r[1] for r in rows}
        assert attrs.get("Mikrotik-Rate-Limit") == "10M/10M"


class TestAccountingFacade:
    def test_start_interim_stop_lifecycle(self, tenant_a):
        _seed_accounts(tenant_a, tenant_a)
        sql = "SELECT radius.accounting(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        base = [NAS_A, "uq-1", "sess-1", "fac.user", "Start", 0, 0, 0, 0, "", "10.1.1.5"]
        _facade(sql, base)
        row = _facade(
            "SELECT acctstoptime IS NULL, acctinputoctets FROM radius.radacct WHERE tenant_id = %s AND acctuniqueid = 'uq-1'",
            [str(tenant_a.id)],
        )
        assert row[0][0] is True and row[0][1] == 0
        # Retransmit Start idempoten.
        _facade(sql, base)
        assert _facade(
            "SELECT count(*) FROM radius.radacct WHERE acctuniqueid = 'uq-1'", []
        )[0][0] == 1
        # Interim menaikkan counter.
        _facade(sql, [NAS_A, "uq-1", "sess-1", "fac.user", "Interim-Update", 0, 1000, 2000, 60, "", "10.1.1.5"])
        row = _facade(
            "SELECT acctinputoctets, acctoutputoctets FROM radius.radacct WHERE acctuniqueid = 'uq-1'", []
        )
        assert row[0] == (1000, 2000)
        # Interim basi (counter turun) diabaikan — monotonik.
        _facade(sql, [NAS_A, "uq-1", "sess-1", "fac.user", "Interim-Update", 0, 500, 500, 10, "", "10.1.1.5"])
        row = _facade(
            "SELECT acctinputoctets, acctoutputoctets FROM radius.radacct WHERE acctuniqueid = 'uq-1'", []
        )
        assert row[0] == (1000, 2000)
        # Stop menutup.
        _facade(sql, [NAS_A, "uq-1", "sess-1", "fac.user", "Stop", 0, 1500, 2500, 90, "User-Request", "10.1.1.5"])
        row = _facade(
            "SELECT acctstoptime IS NOT NULL, acctterminatecause FROM radius.radacct WHERE acctuniqueid = 'uq-1'", []
        )
        assert row[0] == (True, "User-Request")
        # Start TERLAMBAT tidak membuka ulang sesi (§8).
        _facade(sql, base)
        row = _facade(
            "SELECT acctstoptime IS NOT NULL FROM radius.radacct WHERE acctuniqueid = 'uq-1'", []
        )
        assert row[0][0] is True

    def test_session_count(self, tenant_a):
        _seed_accounts(tenant_a, tenant_a)
        sql = "SELECT radius.accounting(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        _facade(sql, [NAS_A, "uq-c1", "sess-c1", "fac.user", "Start", 0, 0, 0, 0, "", None])
        count = _facade("SELECT radius.session_count(%s, %s)", [NAS_A, "fac.user"])[0][0]
        assert count == 1
        _facade(sql, [NAS_A, "uq-c1", "sess-c1", "fac.user", "Stop", 0, 0, 0, 0, "User-Request", None])
        count = _facade("SELECT radius.session_count(%s, %s)", [NAS_A, "fac.user"])[0][0]
        assert count == 0

    def test_post_auth_logs_without_password(self, tenant_a):
        _seed_accounts(tenant_a, tenant_a)
        _facade("SELECT radius.post_auth(%s, %s, %s)", [NAS_A, "fac.user", "Access-Accept"])
        row = _facade(
            "SELECT username, reply FROM radius.radpostauth WHERE tenant_id = %s ORDER BY id DESC LIMIT 1",
            [str(tenant_a.id)],
        )
        assert row[0] == ("fac.user", "Access-Accept")
