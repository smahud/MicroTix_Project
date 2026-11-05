"""Fixture pytest — environment test di-bootstrap oleh microtix/settings_test
(DJANGO_SETTINGS_MODULE di pytest.ini) yang dieksekusi paling awal oleh
pytest-django; setdefault env di conftest terbukti terlambat.

Test database dibuat pytest-django oleh peran mtx_app (CREATEDB khusus dev);
tabel dimiliki peran pembuat DB namun FORCE RLS tetap berlaku (§4).

CsrfAPIClient meniru perilaku SPA nyata: membaca cookie CSRF dari permintaan
awal dan mengirimkannya sebagai header x-csrf-token pada setiap mutasi.
"""
from __future__ import annotations

import os
import time

import django  # noqa: E402

django.setup()

import pytest  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from domains.common.tenant_context import tenant_scope  # noqa: E402
from domains.identity.models import User  # noqa: E402
from domains.subscriptions import services as sub_services  # noqa: E402
from domains.tenancy.models import Membership, Role, Tenant  # noqa: E402

TEST_PASSWORD = "test-password-1234567890"


@pytest.fixture(scope="session", autouse=True)
def _seed_plans(django_db_setup, django_db_blocker):
    """Seed PlanVersion katalog sekali per sesi (harga PRODUCT.md §3)."""
    with django_db_blocker.unblock():
        from domains.subscriptions import services as sub_seed

        sub_seed.seed_plans()


class CsrfAPIClient(APIClient):
    """APIClient yang mengirim x-csrf-token dari cookie (meniru SPA)."""

    def _csrf_headers(self, extra: dict) -> dict:
        headers = dict(extra.pop("headers", {}) or {})
        token = self.cookies.get("mtx_csrf")
        if token is not None:
            headers.setdefault("x-csrf-token", token.value)
        extra["headers"] = headers
        return extra

    def post(self, path, data=None, **extra):
        return super().post(path, data, **self._csrf_headers(extra))

    def put(self, path, data=None, **extra):
        return super().put(path, data, **self._csrf_headers(extra))

    def patch(self, path, data=None, **extra):
        return super().patch(path, data, **self._csrf_headers(extra))

    def delete(self, path, data=None, **extra):
        return super().delete(path, data, **self._csrf_headers(extra))


@pytest.fixture
def api_client():
    client = CsrfAPIClient(enforce_csrf_checks=False)
    # Seed cookie CSRF seperti SPA (SessionProvider memanggil getSession lebih dulu).
    client.get("/api/v1/auth/session")
    return client


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="owner@test.local", full_name="Owner Test", password=TEST_PASSWORD, is_active=True
    )


@pytest.fixture
def tenant_a(db, owner):
    tenant = Tenant.objects.create(display_name="Tenant A", namespace="rtrw-aaaa000001")
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        sub_services.ensure_free_subscription(tenant)
    return tenant


@pytest.fixture
def tenant_b(db):
    other = User.objects.create_user(
        email="owner-b@test.local", full_name="Owner B", password=TEST_PASSWORD, is_active=True
    )
    tenant = Tenant.objects.create(display_name="Tenant B", namespace="rtrw-bbbb000002")
    Membership.objects.create(user=other, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        sub_services.ensure_free_subscription(tenant)
    return tenant


@pytest.fixture
def auth_client(api_client, owner, tenant_a):
    """Klien terautentikasi dengan sesi aktif di tenant_a.

    Catatan: Client.session tidak di-cache (setiap akses = SessionStore baru);
    mutasi harus melalui satu referensi lalu save().
    """
    api_client.force_login(owner)
    session = api_client.session
    session["active_tenant_id"] = str(tenant_a.id)
    session["auth_at"] = time.time()
    session.save()
    return api_client
