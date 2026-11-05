"""RLS PostgreSQL nyata — fail-closed, konteks benar/salah, bypass runtime (TK-102)."""
from __future__ import annotations

import pytest
from django.db import connection

from domains.audit.models import AuditEvent, record
from domains.common.tenant_context import current_tenant_id, tenant_scope
from domains.tenancy.models import Tenant

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_write_outside_scope_blocked(tenant_a):
    """Konteks kosong gagal tertutup: INSERT tanpa konteks tenant ditolak RLS."""
    with pytest.raises(Exception, match="row-level security"):
        AuditEvent.objects.create(tenant=tenant_a, action_code="test.bypass")


def test_read_outside_scope_empty(tenant_a, db):
    with tenant_scope(tenant_a.id):
        record(tenant_id=tenant_a.id, action_code="tenant.a.event")
    # Tanpa konteks: 0 baris — bukan error, tapi gagal tertutup.
    assert AuditEvent.objects.count() == 0


def test_read_with_wrong_tenant_context_empty(tenant_a, tenant_b):
    with tenant_scope(tenant_a.id):
        record(tenant_id=tenant_a.id, action_code="a.event")
    with tenant_scope(tenant_b.id):
        assert list(AuditEvent.objects.values_list("action_code", flat=True)) == []


def test_read_with_right_context(tenant_a):
    with tenant_scope(tenant_a.id):
        record(tenant_id=tenant_a.id, action_code="ok.event")
        assert AuditEvent.objects.filter(action_code="ok.event").count() == 1


def test_context_is_transaction_local(tenant_a):
    """GUC tidak bocor keluar transaksi (pool reuse aman)."""
    with tenant_scope(tenant_a.id):
        assert current_tenant_id() == str(tenant_a.id)
    assert current_tenant_id() is None


def test_composite_fk_rejects_cross_tenant_reference(tenant_a, tenant_b, db):
    """FK komposit: JobDetail tidak boleh menunjuk job tenant lain."""
    from domains.jobs.models import Job, JobDetail, JobKind

    with tenant_scope(tenant_a.id):
        job = Job.objects.create(tenant=tenant_a, kind=JobKind.LIFECYCLE_SAAS)
    with pytest.raises(Exception):
        # job milik tenant_a tapi detail mengaku tenant_b → ditolak constraint.
        with tenant_scope(tenant_b.id):
            JobDetail.objects.create(job=job, tenant=tenant_b, payload={})


def test_runtime_role_is_not_privileged():
    """Peran runtime bukan superuser/BYPASSRLS (ARCHITECTURE §4)."""
    with connection.cursor() as cur:
        cur.execute("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        user, is_super, bypass = cur.fetchone()
    assert not is_super, "runtime tidak boleh superuser"
    assert not bypass, "runtime tidak boleh BYPASSRLS"
