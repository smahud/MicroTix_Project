"""Kontrak API billing internet M6 (TK-601) — endpoint terdaftar di OpenAPI.

Anti-API-palsu (§5): endpoint yang diimplementasi wajib muncul di schema;
semantik inti (state invoice, metode, bucket aging) tervalidasi via tes
integrasi. Kontrak ini memastikan schema konsisten + envelope standar.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def _spec():
    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.get("/api/schema/?format=json")
    assert resp.status_code == 200
    return resp.json()


def test_billing_endpoints_in_openapi():
    paths = _spec()["paths"]
    expected = (
        "/api/v1/tenants/{tenant_id}/billing/packages",
        "/api/v1/tenants/{tenant_id}/billing/packages/{package_id}",
        "/api/v1/tenants/{tenant_id}/services/{service_id}/billing-package",
        "/api/v1/tenants/{tenant_id}/services/{service_id}/charges",
        "/api/v1/tenants/{tenant_id}/charges/{charge_id}",
        "/api/v1/tenants/{tenant_id}/invoices",
        "/api/v1/tenants/{tenant_id}/invoices/aging",
        "/api/v1/tenants/{tenant_id}/invoices/{invoice_id}",
        "/api/v1/tenants/{tenant_id}/payments",
        "/api/v1/tenants/{tenant_id}/payments/{payment_id}",
        "/api/v1/tenants/{tenant_id}/payments/{payment_id}/verify",
        "/api/v1/tenants/{tenant_id}/payments/{payment_id}/reject",
        # TK-109 documents
        "/api/v1/tenants/{tenant_id}/documents",
        "/api/v1/tenants/{tenant_id}/documents/{document_id}",
    )
    for path in expected:
        assert path in paths, f"endpoint billing/documents hilang: {path}"


def test_invoice_endpoints_methods():
    paths = _spec()["paths"]
    invoice = paths["/api/v1/tenants/{tenant_id}/invoices"]
    assert "get" in invoice
    payment = paths["/api/v1/tenants/{tenant_id}/payments"]
    assert {"get", "post"} <= set(payment.keys())
    verify = paths["/api/v1/tenants/{tenant_id}/payments/{payment_id}/verify"]
    assert "post" in verify


def test_unknown_billing_route_is_404_envelope(api_client, db):
    """Endpoint yang belum diimplementasi → 404 jujur (anti-API-palsu)."""
    resp = api_client.get("/api/v1/tenants/00000000-0000-0000-0000-000000000000/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "not_found"
