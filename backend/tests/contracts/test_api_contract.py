"""Kontrak API — OpenAPI schema, envelope, health, enums, branding."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def test_openapi_schema_renders():
    from django.urls import reverse

    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.get("/api/schema/?format=json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["openapi"].startswith("3.")
    paths = spec["paths"]
    for expected in (
        "/api/v1/auth/login",
        "/api/v1/auth/login-totp",
        "/api/v1/auth/session",
        "/api/v1/auth/tenants/{tenant_id}/switch",
        "/api/v1/tenants/{tenant_id}/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/tenants/{tenant_id}/subscription",
        "/api/v1/tenants/{tenant_id}/quotations",
        "/api/v1/meta/enums",
        "/api/v1/health/ready",
    ):
        assert expected in paths, f"endpoint hilang: {expected}"


def test_error_envelope_shape_401(api_client):
    resp = api_client.get("/api/v1/auth/session")
    assert resp.status_code == 401
    body = resp.json()
    assert set(body.keys()) >= {"code", "message", "request_id", "locale"}
    assert body["code"] == "unauthorized"


def test_health_endpoints(api_client, db):
    resp = api_client.get("/api/v1/health/live")
    assert resp.status_code == 200 and resp.json() == {"status": "live"}
    resp = api_client.get("/api/v1/health/ready")
    assert resp.status_code == 200 and resp.json() == {"status": "ready"}


def test_enums_localized(auth_client):
    resp = auth_client.get("/api/v1/meta/enums?locale=id")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_state"]["queued"] == "Permintaan diterima dan menunggu giliran"
    assert data["lifecycle"]["provisioned"] == "Aktif"
    # Locale tidak dikenal → fallback id.
    resp = auth_client.get("/api/v1/meta/enums?locale=fr")
    assert resp.json()["job_state"]["queued"].startswith("Permintaan")


def test_branding_public(api_client):
    resp = api_client.get("/api/v1/meta/branding")
    assert resp.status_code == 200
    data = resp.json()
    assert {"project_name", "app_name", "brand_name", "publication_blocked"} <= set(data)


def test_accept_language_negotiation(auth_client):
    resp = auth_client.get("/api/v1/meta/enums", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9,id;q=0.1")
    assert resp.status_code == 200


def test_unknown_route_404_envelope(api_client):
    resp = api_client.get("/api/v1/tidak-ada")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] in ("not_found", "error")


def test_pagination_contract(auth_client, tenant_a, db):
    from domains.common.tenant_context import tenant_scope
    from domains.audit.models import record

    with tenant_scope(tenant_a.id):
        for i in range(7):
            record(tenant_id=tenant_a.id, action_code=f"evt.{i}")
    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/audit-timeline?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["next_cursor"]
    # limit tidak valid → 422.
    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/audit-timeline?limit=0")
    assert resp.status_code == 422
    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/audit-timeline?limit=999")
    assert resp.status_code == 422
    # kursor rusak → 422.
    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/audit-timeline?cursor=zzz")
    assert resp.status_code == 422
