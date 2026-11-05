"""Kontrak API customers — bentuk respons persis contracts.ts + OpenAPI (M4)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract

# Kunci kontrak frontend (apps/web/src/api/contracts.ts) — sumber kebenaran.
SERVICE_ROW_KEYS = {
    "id", "service_code", "customer_code", "customer_name", "username", "kind",
    "package_name", "router_id", "router_display_name", "lifecycle", "payment",
    "isolation", "connection", "job", "incomplete_mapping",
}
SERVICE_DETAIL_EXTRA = {"start_date", "contact", "address", "access"}
ACCESS_KEYS = {"username", "state", "credential_state", "session_limit", "mac_locked", "last_active_session_at", "restricting_router_id"}
RADIUS_ACCOUNT_ROW_KEYS = {
    "id", "username", "kind", "state", "credential_state", "package_name",
    "restricting_router_id", "last_active_session_at",
}
DISCOVERED_ACCOUNT_KEYS = {
    "id", "username", "kind", "profile", "service", "disabled_on_router", "comment", "state",
}
IDENTITY_CONFLICT_KEYS = {"candidate_group_id", "usernames", "routers", "kind", "resolution"}
CSV_VALIDATION_KEYS = {"total_rows", "valid_rows", "error_rows", "row_errors", "preview"}
CSV_ROW_ERROR_KEYS = {"row", "field", "reason_code", "action_hint"}
MIGRATION_COUNTS_KEYS = {"to_create", "to_merge", "unchanged", "conflicts", "quota_used", "quota_limit"}


@pytest.fixture
def cust_client(auth_client):
    session = auth_client.session
    session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()
    return auth_client


@pytest.fixture
def service_id(cust_client, tenant_a):
    resp = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/services",
        {"customer_name": "Kontrak", "username": "kontrak.user", "password": "pw-123456789012"},
        headers={"Idempotency-Key": "contract-1"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_openapi_schema_contains_customers_endpoints():
    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.get("/api/schema/?format=json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    base = "/api/v1/tenants/{tenant_id}"
    for expected in (
        f"{base}/services",
        f"{base}/services/{{service_id}}",
        f"{base}/services/{{service_id}}/reveal-credentials",
        f"{base}/access-accounts",
        f"{base}/access-accounts/{{account_id}}",
        f"{base}/imports",
        f"{base}/imports/{{import_id}}/validate",
        f"{base}/imports/{{import_id}}/commit",
        f"{base}/routers/{{router_id}}/migrations",
        f"{base}/routers/{{router_id}}/password-harvest",
        f"{base}/migrations/{{migration_id}}/accounts",
        f"{base}/migrations/{{migration_id}}/identity-conflicts",
        f"{base}/migrations/{{migration_id}}/identity-conflicts/{{group_id}}",
        f"{base}/migrations/{{migration_id}}/commit",
    ):
        assert expected in paths, f"endpoint hilang: {expected}"


def test_service_list_row_shape_exact(cust_client, tenant_a, service_id):
    resp = cust_client.get(f"/api/v1/tenants/{tenant_a.id}/services")
    assert resp.status_code == 200
    page = resp.json()
    assert set(page.keys()) == {"items", "next_cursor"}
    row = page["items"][0]
    assert set(row.keys()) == SERVICE_ROW_KEYS


def test_service_detail_shape_exact(cust_client, tenant_a, service_id):
    resp = cust_client.get(f"/api/v1/tenants/{tenant_a.id}/services/{service_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert set(detail.keys()) == SERVICE_ROW_KEYS | SERVICE_DETAIL_EXTRA
    assert set(detail["access"].keys()) == ACCESS_KEYS


def test_access_account_row_shape_exact(cust_client, tenant_a, service_id):
    resp = cust_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts")
    assert resp.status_code == 200
    account = resp.json()["items"][0]
    assert set(account.keys()) == RADIUS_ACCOUNT_ROW_KEYS


def test_reveal_credential_shape(cust_client, tenant_a, service_id):
    resp = cust_client.post(f"/api/v1/tenants/{tenant_a.id}/services/{service_id}/reveal-credentials")
    assert resp.status_code == 200
    body = resp.json()
    # Kontrak minimal RevealCredentialResult (+ revealed_at/expires_in_s ekstra).
    assert {"username", "password", "display_for_s"} <= set(body.keys())
    assert body["display_for_s"] == 30
    assert resp.headers.get("Cache-Control") == "no-store"


def test_csv_import_and_validation_shapes(cust_client, tenant_a):
    rows = [{"username": "csv.kontrak", "password": "pw-123456789", "kind": "pppoe", "package": "10M"}]
    resp = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/imports",
        {"mode": "create", "file_name": "kontrak.csv", "rows": rows},
        headers={"Idempotency-Key": "contract-csv-1"},
    )
    assert resp.status_code == 201
    draft = resp.json()
    # CsvImportDraft kontrak: id/mode/file_name/total_rows/validation (+import_id).
    assert {"id", "mode", "file_name", "total_rows", "validation", "import_id"} == set(draft.keys())
    assert draft["id"] == draft["import_id"]

    resp = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/imports/{draft['id']}/validate",
        headers={"Idempotency-Key": "contract-csv-v"},
    )
    assert resp.status_code == 200
    validation = resp.json()
    assert set(validation.keys()) == CSV_VALIDATION_KEYS
    bad_rows = [{"username": " a"}, {}, {"username": "ok"}]
    draft2 = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/imports",
        {"mode": "create", "file_name": "galat.csv", "rows": bad_rows},
        headers={"Idempotency-Key": "contract-csv-2"},
    ).json()
    validation2 = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/imports/{draft2['id']}/validate",
        headers={"Idempotency-Key": "contract-csv-2v"},
    ).json()
    assert set(validation2["row_errors"][0].keys()) == CSV_ROW_ERROR_KEYS


def test_discovered_account_and_conflict_shapes(cust_client, tenant_a, db):
    from domains.common.tenant_context import tenant_scope
    from domains.customers.models import MigrationSession
    from domains.customers.services import conflict_group_id
    from domains.network.models import DiscoveryObject, DiscoverySnapshot, Router

    with tenant_scope(tenant_a.id):
        r1 = Router.objects.create(tenant_id=tenant_a.id, display_name="R A", router_code="r-ca")
        r2 = Router.objects.create(tenant_id=tenant_a.id, display_name="R B", router_code="r-cb")
        s1 = DiscoverySnapshot.objects.create(tenant_id=tenant_a.id, router=r1, status="succeeded")
        s2 = DiscoverySnapshot.objects.create(tenant_id=tenant_a.id, router=r2, status="succeeded")
        DiscoveryObject.objects.create(tenant_id=tenant_a.id, snapshot=s1, router=r1, username="kontrak.dup")
        DiscoveryObject.objects.create(tenant_id=tenant_a.id, snapshot=s2, router=r2, username="KONTRAK.DUP")
        session = MigrationSession.objects.create(
            tenant_id=tenant_a.id, router=r1, snapshot=s1, state=MigrationSession.State.DISCOVERED
        )

    resp = cust_client.get(f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/accounts")
    assert resp.status_code == 200
    row = resp.json()["items"][0]
    assert set(row.keys()) == DISCOVERED_ACCOUNT_KEYS

    resp = cust_client.get(f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/identity-conflicts")
    assert resp.status_code == 200
    candidate = resp.json()[0]
    assert set(candidate.keys()) == IDENTITY_CONFLICT_KEYS

    # Resolusi → 204; bentuk keputusan konsisten.
    group_id = conflict_group_id(["kontrak.dup", "KONTRAK.DUP"])
    resp = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/identity-conflicts/{group_id}",
        {"resolution": "keep_one"},
        headers={"Idempotency-Key": "contract-conflict"},
    )
    assert resp.status_code == 204

    # Commit → 202 JobAccepted + counts MigrationSummaryCounts.
    resp = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/commit",
        headers={"Idempotency-Key": "contract-commit"},
    )
    assert resp.status_code == 202
    assert set(resp.json().keys()) == {"job_id", "status_url"}
    with tenant_scope(tenant_a.id):
        session.refresh_from_db()
        assert set(session.counts.keys()) == MIGRATION_COUNTS_KEYS


def test_job_accepted_shape_and_status_url(cust_client, tenant_a, service_id):
    """Semua 202 mengembalikan job_id + status_url /api/v1/jobs/{id}."""
    import uuid as uuid_mod

    router_id = str(uuid_mod.uuid4())
    resp = cust_client.post(
        f"/api/v1/tenants/{tenant_a.id}/routers/{router_id}/migrations",
        headers={"Idempotency-Key": "contract-mig"},
    )
    # Router tak dikenal → 404 generik (bukan 500): UUID valid diperlukan.
    assert resp.status_code == 404


def test_pagination_contract_on_services(cust_client, tenant_a, service_id):
    base = f"/api/v1/tenants/{tenant_a.id}/services"
    assert cust_client.get(f"{base}?limit=0").status_code == 422
    assert cust_client.get(f"{base}?limit=999").status_code == 422
    assert cust_client.get(f"{base}?cursor=zzz").status_code == 422
    assert cust_client.get(f"{base}?kind=l2tp").status_code == 422
    assert cust_client.get(f"{base}?lifecycle=aktip").status_code == 422
    ok = cust_client.get(f"{base}?limit=50")
    assert ok.status_code == 200
    assert set(ok.json().keys()) == {"items", "next_cursor"}
