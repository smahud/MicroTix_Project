"""Integrasi layanan pelanggan + CSV (U04/U08) melalui API + job engine."""
from __future__ import annotations

import pytest

from domains.common.tenant_context import tenant_scope
from domains.customers import csv_import as csv_service
from domains.customers.handlers import CsvImportCommitHandler
from domains.customers.models import CsvImport, Customer, Service
from domains.jobs import engine as jobs_engine
from domains.jobs.models import Job

pytestmark = pytest.mark.integration


class TestServiceApi:
    def test_create_service_full_flow(self, auth_client, tenant_a):
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {
                "customer_name": "Budi Santoso",
                "phone": "081200000001",
                "address": "Jl. Merdeka 1",
                "username": "budi-001",
                "password": "password-123",
                "kind": "pppoe",
                "simultaneous_use": 2,
                "rate_limit_rx_kbps": 10_000,
                "rate_limit_tx_kbps": 50_000,
            },
            headers={"Idempotency-Key": "svc-create-1"},
        )
        assert resp.status_code == 201, resp.content
        data = resp.json()
        assert data["state"] == "provisioned"
        with tenant_scope(tenant_a.id):
            service = Service.objects.get(id=data["id"])
            customer_name = service.customer.full_name
        assert customer_name == "Budi Santoso"
        # Proyeksi RADIUS tercipta (akun aktif → Cleartext-Password).
        from django.db import connection

        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT attribute, value FROM radius.radcheck rc "
                    "JOIN access_account a ON a.id = rc.account_id WHERE a.service_id = %s",
                    [service.id],
                )
                checks = dict(cur.fetchall())
        assert checks.get("Cleartext-Password") == "password-123"
        assert "Simultaneous-Use" in checks

    def test_idempotent_create(self, auth_client, tenant_a):
        body = {
            "customer_name": "Idem",
            "username": "idem-001",
            "password": "password-123",
        }
        r1 = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services", body, headers={"Idempotency-Key": "svc-idem"}
        )
        r2 = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services", body, headers={"Idempotency-Key": "svc-idem"}
        )
        assert r1.status_code == 201 and r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]
        with tenant_scope(tenant_a.id):
            assert Customer.objects.filter(full_name="Idem").count() == 1

    def test_list_services_with_query(self, auth_client, tenant_a):
        auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Cari Saya", "username": "cari-001", "password": "password-123"},
            headers={"Idempotency-Key": "svc-cari"},
        )
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/services", {"query": "cari"})
        assert resp.status_code == 200
        body = resp.json()
        usernames = [i.get("username") for i in body["items"]]
        assert "cari-001" in usernames
        # connection_state jujur: unknown tanpa accounting (RAD-07).
        for item in body["items"]:
            if item["username"] == "cari-001":
                assert item["connection_state"] == "unknown"

    def test_tenant_isolation_services(self, auth_client, tenant_a, tenant_b):
        auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Private A", "username": "priv-001", "password": "password-123"},
            headers={"Idempotency-Key": "svc-priv"},
        )
        resp = auth_client.get(f"/api/v1/tenants/{tenant_b.id}/services")
        assert resp.status_code == 404  # bukan anggota tenant B → 404 generik

    def test_reveal_requires_reauth(self, auth_client, tenant_a):
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Rahasia", "username": "rahasia-001", "password": "password-999"},
            headers={"Idempotency-Key": "svc-reveal"},
        )
        service_id = resp.json()["id"]
        # Tanpa reauth aktif → ditolak (permission sensitif; ARCHITECTURE §3).
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services/{service_id}/reveal-credentials",
            headers={"Idempotency-Key": "reveal-1"},
        )
        assert resp.status_code == 403


class TestCsvImport:
    def test_validate_and_commit_via_job(self, auth_client, tenant_a, owner):
        rows = [
            {"username": "csv-a", "password": "password-a1", "kind": "pppoe"},
            {"username": "csv-b", "password": "password-b2", "kind": "hotspot"},
            {"username": "bad", "password": "short"},  # invalid
        ]
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "pelanggan.csv", "rows": rows},
        )
        assert resp.status_code == 201, resp.content
        import_id = resp.json()["id"]

        resp = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/validate")
        assert resp.status_code == 200
        validation = resp.json()
        assert validation["total_rows"] == 3
        assert validation["invalid_rows"] == 1
        assert validation["issues"][0]["username"] == "bad"

        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/commit",
            headers={"Idempotency-Key": "csv-commit-1"},
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        claimed = jobs_engine.claim_next()
        assert claimed is not None and str(claimed.id) == job_id
        result = jobs_engine.run_claimed(claimed)
        assert result.state == "succeeded"
        with tenant_scope(tenant_a.id):
            detail = result.detail
        assert detail.result["created"] == 2
        assert detail.result["failed"] == 1

        # Commit ulang (idempoten per baris): username existing dilewati.
        with tenant_scope(tenant_a.id):
            csv = CsvImport.objects.get(id=import_id)
            csv.state = CsvImport.State.VALIDATED
            csv.save(update_fields=["state"])
            jobs_engine.create_job(
                tenant_id=tenant_a.id, kind="csv_import_commit", actor=owner, payload={"import_id": import_id}
            )
            claimed2 = jobs_engine.claim_next()
            result2 = jobs_engine.run_claimed(claimed2)
            detail2 = result2.detail
        assert detail2.result["created"] == 0
        assert detail2.result["skipped"] == 2

    def test_row_limit_enforced(self, auth_client, tenant_a):
        rows = [{"username": f"u{i}", "password": "password-x1"} for i in range(10_001)]
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "big.csv", "rows": rows},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "too_many_rows"
