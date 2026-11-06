"""Integrasi API customers — provisioning, kredensial, kuota, CSV (M4).

PostgreSQL nyata; RLS aktif. Fixture conftest: api_client/auth_client/owner/
tenant_a/tenant_b. Reauth aksi sensitif dipasang lewat sesi (pola test_auth).
"""
from __future__ import annotations

import uuid

import pytest

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.tenancy.models import Membership, Role

pytestmark = pytest.mark.integration

IDEM = {"Idempotency-Key": "customers-test-1"}


@pytest.fixture
def reauth_client(auth_client):
    """Klien dengan reauth aktif (aksi sensitif lolos, §3)."""
    session = auth_client.session
    session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()
    return auth_client


def _run_job(job_id) -> object:
    """Jalankan job secara inline lewat engine (pola test_jobs_engine)."""
    from domains.jobs import engine

    for _ in range(20):
        claimed = engine.claim_next()
        if claimed is None:
            break
        result = engine.run_claimed(claimed)
        if str(claimed.id) == str(job_id):
            return result
    raise AssertionError(f"job {job_id} tidak dapat diklaim/dijalankan")


def _create_router(tenant, code="rtr-1"):
    from domains.network.models import Router

    with tenant_scope(tenant.id):
        return Router.objects.create(tenant_id=tenant.id, display_name=f"Router {code}", router_code=code)


class TestServiceProvisioning:
    def test_create_draft_and_shapes(self, reauth_client, tenant_a):
        router = _create_router(tenant_a)
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {
                "customer_name": "Budi Santoso",
                "kind": "pppoe",
                "package_name": "Paket 20M",
                "router_id": str(router.id),
                "username": "budi.santoso",
                "password": "s3cret-password-123",
                "start_date": "2026-01-05",
            },
            headers=IDEM,
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert set(body.keys()) == {"id", "state"}
        assert body["state"] == "draft"

        # Daftar: bentuk baris persis kontrak ServiceRow.
        resp = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services")
        assert resp.status_code == 200
        page = resp.json()
        assert set(page.keys()) == {"items", "next_cursor"}
        row = page["items"][0]
        assert set(row.keys()) == {
            "id", "service_code", "customer_code", "customer_name", "username", "kind",
            "package_name", "router_id", "router_display_name", "lifecycle", "payment",
            "isolation", "connection", "job", "incomplete_mapping",
        }
        assert row["id"] == body["id"]
        assert row["username"] == "budi.santoso"
        assert row["lifecycle"] == "draft"
        assert row["payment"] == "not_billed"
        assert row["isolation"] == "normal"
        assert row["connection"] == "unknown"  # beta: belum accounting
        assert row["job"] == "none"
        assert row["incomplete_mapping"] is False

        # Detail: superset ServiceRow + start_date/contact/address/access.
        resp = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services/{body['id']}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["start_date"] == "2026-01-05"
        assert detail["access"]["username"] == "budi.santoso"
        assert detail["access"]["state"] == "active"
        assert detail["access"]["credential_state"] == "ready"
        assert detail["access"]["session_limit"] == 1

    def test_create_draft_without_username(self, reauth_client, tenant_a):
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Siti", "kind": "hotspot"},
            headers={"Idempotency-Key": "customers-draft-1"},
        )
        assert resp.status_code == 201
        assert resp.json()["state"] == "draft"
        # Baris tanpa akun: username null, isolation normal, access null.
        resp = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services")
        row = resp.json()["items"][0]
        assert row["username"] is None
        assert row["incomplete_mapping"] is True  # tanpa paket & router
        detail_resp = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services/{row['id']}")
        assert detail_resp.json()["access"] is None

    def test_create_account_choice_requires_username(self, reauth_client, tenant_a):
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Tanpa User", "final_choice": "create_account"},
            headers={"Idempotency-Key": "customers-choice-1"},
        )
        assert resp.status_code == 422
        assert resp.json()["field_errors"]["username"][0]["code"] == "required"

    def test_duplicate_username_conflict(self, reauth_client, tenant_a):
        payload = {"customer_name": "Budi", "username": "dup-user", "kind": "pppoe"}
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services", payload, headers={"Idempotency-Key": "customers-dup-1"}
        )
        assert resp.status_code == 201
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services", payload, headers={"Idempotency-Key": "customers-dup-2"}
        )
        assert resp.status_code == 409  # UNIQUE(tenant, username)

    def test_idempotent_replay_and_conflict(self, reauth_client, tenant_a):
        payload = {"customer_name": "Idem", "username": "idem-user"}
        headers = {"Idempotency-Key": "customers-idem-1"}
        first = reauth_client.post(f"/api/v1/tenants/{tenant_a.id}/services", payload, headers=headers)
        assert first.status_code == 201
        replay = reauth_client.post(f"/api/v1/tenants/{tenant_a.id}/services", payload, headers=headers)
        assert replay.status_code == 201
        assert replay.json()["id"] == first.json()["id"]  # aksi logis sama
        clash = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {**payload, "customer_name": "Bedanya"},
            headers=headers,
        )
        assert clash.status_code == 409
        assert clash.json()["code"] == "idempotency_conflict"
        missing = reauth_client.post(f"/api/v1/tenants/{tenant_a.id}/services", payload)
        assert missing.status_code == 422  # tanpa key


class TestRevealCredentials:
    def _service_with_password(self, tenant_a) -> str:
        from domains.customers import services as cust_services
        from domains.customers.models import Service

        with tenant_scope(tenant_a.id):
            service = cust_services.provision_service_draft(
                tenant_a, {"customer_name": "Rahasia", "username": "rahasia.user", "password": "pw-123456789012"}
            )
        return str(service.id)

    def test_reveal_requires_reauth_then_ok(self, auth_client, tenant_a):
        # SATU klien: reauth_client turunan auth_client yang sama — memakai
        # keduanya membuat reauth sudah aktif sebelum assert 403.
        service_id = self._service_with_password(tenant_a)
        # Tanpa reauth → 403 (sensitif).
        resp = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/services/{service_id}/reveal-credentials")
        assert resp.status_code == 403
        assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/services/{service_id}").status_code == 200
        # Dengan reauth → 200 + no-store; password cocok.
        session = auth_client.session
        session["reauth_until"] = "2099-01-01T00:00:00+00:00"
        session.save()
        resp = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/services/{service_id}/reveal-credentials")
        assert resp.status_code == 200
        assert resp.headers["Cache-Control"] == "no-store"
        body = resp.json()
        assert body["username"] == "rahasia.user"
        assert body["password"] == "pw-123456789012"
        assert body["display_for_s"] == 30

    def test_reveal_unknown_credential_conflict(self, reauth_client, tenant_a):
        from domains.customers import services as cust_services

        with tenant_scope(tenant_a.id):
            service = cust_services.provision_service_draft(
                tenant_a, {"customer_name": "Belum Ada", "username": "unknown.cred"}
            )
        resp = reauth_client.post(f"/api/v1/tenants/{tenant_a.id}/services/{str(service.id)}/reveal-credentials")
        assert resp.status_code == 409  # credential_state unknown → jujur 409


class TestAccessAccountLifecycle:
    def test_suspend_activate_and_isolation(self, reauth_client, tenant_a):
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Suspensi", "username": "suspend.me", "kind": "pppoe"},
            headers={"Idempotency-Key": "customers-susp-1"},
        )
        service_id = resp.json()["id"]
        resp = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts")
        assert resp.status_code == 200
        account = resp.json()["items"][0]
        assert set(account.keys()) == {
            "id", "username", "kind", "state", "credential_state",
            "service_id", "service_code", "customer_name",
            "package_name", "restricting_router_id", "last_active_session_at",
        }
        # Identitas layanan/pelanggan (TK-604 U10): akun dapat dipetakan ke
        # layanan + pelanggan tanpa permintaan detail per baris.
        assert account["service_id"] == service_id
        assert account["service_code"].startswith("SVC-")
        assert account["customer_name"] == "Suspensi"
        account_id = account["id"]

        # Suspend → 204; dimensi isolation jadi isolated.
        resp = reauth_client.patch(
            f"/api/v1/tenants/{tenant_a.id}/access-accounts/{account_id}",
            {"state": "suspended"},
            headers={"Idempotency-Key": "customers-susp-2"},
        )
        assert resp.status_code == 204
        row = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services").json()["items"][0]
        assert row["isolation"] == "isolated"
        # Filter isolation=isolated menemukan; normal tidak.
        isolated = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services?isolation=isolated").json()
        assert len(isolated["items"]) == 1
        normal = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services?isolation=normal").json()
        assert len(normal["items"]) == 0

        # Aktivasi kembali → normal.
        resp = reauth_client.patch(
            f"/api/v1/tenants/{tenant_a.id}/access-accounts/{account_id}",
            {"state": "active"},
            headers={"Idempotency-Key": "customers-susp-3"},
        )
        assert resp.status_code == 204
        row = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services").json()["items"][0]
        assert row["isolation"] == "normal"

    def test_state_filter_and_query(self, reauth_client, tenant_a):
        reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Cari Saya", "username": "cari.user"},
            headers={"Idempotency-Key": "customers-query-1"},
        )
        found = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts?query=cari").json()
        assert len(found["items"]) == 1
        state = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts?state=active").json()
        assert any(a["username"] == "cari.user" for a in state["items"])
        none = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts?state=suspended").json()
        assert none["items"] == []
        bad = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts?state=aktip")
        assert bad.status_code == 422


class TestCrossTenantIsolation:
    def test_tenant_b_invisible_to_a(self, reauth_client, tenant_a, tenant_b):
        from domains.customers import services as cust_services
        from domains.customers.models import AccessAccount

        with tenant_scope(tenant_b.id):
            service = cust_services.provision_service_draft(
                tenant_b, {"customer_name": "Milik B", "username": "b-only", "password": "pw-b-123456789"}
            )
            account = AccessAccount.objects.get(service=service)

        # Bukan anggota tenant B → 404 generik untuk route tenant B.
        resp = reauth_client.get(f"/api/v1/tenants/{tenant_b.id}/services")
        assert resp.status_code == 404
        # Resource B tidak terlihat dari konteks tenant A (RLS) → 404.
        assert reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services/{service.id}").status_code == 404
        # Daftar A tidak memuat layanan B; akun B tidak tampak.
        rows = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/services").json()["items"]
        assert all(r["customer_name"] != "Milik B" for r in rows)
        accounts = reauth_client.get(f"/api/v1/tenants/{tenant_a.id}/access-accounts").json()["items"]
        assert all(a["username"] != "b-only" for a in accounts)
        # Mutasi akun B dari A → 404.
        resp = reauth_client.patch(
            f"/api/v1/tenants/{tenant_a.id}/access-accounts/{account.id}",
            {"state": "suspended"},
            headers={"Idempotency-Key": "cross-1"},
        )
        assert resp.status_code == 404
        # Reveal layanan B dari A → 404 (bukan 403: tidak milik).
        resp = reauth_client.post(f"/api/v1/tenants/{tenant_a.id}/services/{service.id}/reveal-credentials")
        assert resp.status_code == 404


class TestQuotaEnforcement:
    def test_free_plan_limit_and_409(self, reauth_client, tenant_a):
        from domains.subscriptions.models import PlanVersion, Subscription

        # Paket uji limit kecil (kode unik version baru; tidak mengganggu seed).
        with tenant_scope(tenant_a.id):
            plan = PlanVersion.objects.create(
                code="bronze", version=99, routers_limit=1, services_limit=2,
                monthly_price=0, yearly_price=0,
            )
            Subscription.objects.filter(tenant=tenant_a).update(plan=plan)

        for i, name in enumerate(("Satu", "Dua")):
            resp = reauth_client.post(
                f"/api/v1/tenants/{tenant_a.id}/services",
                {"customer_name": name, "username": f"kuota-{i}"},
                headers={"Idempotency-Key": f"quota-{i}"},
            )
            assert resp.status_code == 201
        # Batas 2 tercapai → kuota terlampaui (409 quota_exceeded).
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Tiga", "username": "kuota-3"},
            headers={"Idempotency-Key": "quota-3"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "quota_exceeded"

        # CSV commit melebihi kuota → job gagal jujur quota_exceeded.
        imp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "lebih.csv", "rows": [{"username": f"csv-{i}"} for i in range(3)]},
            headers={"Idempotency-Key": "quota-csv"},
        ).json()
        reauth_client.post(f"/api/v1/tenants/{tenant_a.id}/imports/{imp['id']}/validate", headers={"Idempotency-Key": "quota-csv-v"})
        job = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{imp['id']}/commit", headers={"Idempotency-Key": "quota-csv-c"}
        ).json()
        result = _run_job(job["job_id"])
        assert result.state == "failed"
        assert result.error_code == "quota_exceeded"


class TestCsvImportFlow:
    def test_create_validate_commit_happy_path(self, reauth_client, tenant_a):
        rows = [
            {"username": "csv.budi", "password": "pw-budi-123456789", "kind": "pppoe", "package": "20M", "customer_name": "CSV Budi"},
            {"username": "csv.siti", "password": "pw-siti-123456789", "kind": "hotspot", "package": "Voucher 3hr", "customer_name": "CSV Siti"},
        ]
        # 1) Unggah draf.
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "pelanggan.csv", "rows": rows},
            headers={"Idempotency-Key": "csv-1"},
        )
        assert resp.status_code == 201, resp.json()
        draft = resp.json()
        assert draft["id"] == draft["import_id"]
        assert draft["mode"] == "create"
        assert draft["total_rows"] == 2
        assert draft["validation"] is None

        # 2) Validasi sinkron.
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{draft['id']}/validate", headers={"Idempotency-Key": "csv-1-v"}
        )
        assert resp.status_code == 200
        validation = resp.json()
        assert set(validation.keys()) == {"total_rows", "valid_rows", "error_rows", "row_errors", "preview"}
        assert validation["total_rows"] == 2
        assert validation["valid_rows"] == 2
        assert validation["error_rows"] == 0
        assert validation["preview"] == rows

        # 3) Commit → 202 job; replay key sama → job sama.
        commit_resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{draft['id']}/commit", headers={"Idempotency-Key": "csv-1-c"}
        )
        assert commit_resp.status_code == 202
        job = commit_resp.json()
        assert set(job.keys()) == {"job_id", "status_url"}
        assert job["status_url"] == f"/api/v1/jobs/{job['job_id']}"
        replay = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{draft['id']}/commit", headers={"Idempotency-Key": "csv-1-c"}
        ).json()
        assert replay["job_id"] == job["job_id"]

        # 4) Jalankan job inline → sukses; akun dibuat terenkripsi.
        result = _run_job(job["job_id"])
        assert result.state == "succeeded"
        assert result.effect_state == "confirmed"

        from domains.customers.models import AccessAccount, CsvImport as CsvImportModel

        with tenant_scope(tenant_a.id):
            budi = AccessAccount.objects.get(username="csv.budi")
            assert budi.credential_state == "ready"
            assert "pw-budi-123456789" not in budi.secret_ref
            assert budi.service.package_name == "20M"
            assert budi.service.lifecycle == "draft"
            assert budi.service.customer.display_name == "CSV Budi"
            imp = CsvImportModel.objects.get(id=draft["id"])
            assert imp.state == "committed"
            assert imp.committed_at is not None

        # Commit ulang (key berbeda) → 409 (sudah committed).
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{draft['id']}/commit", headers={"Idempotency-Key": "csv-1-c2"}
        )
        assert resp.status_code == 409

    def test_validation_errors_preview_and_caps(self, reauth_client, tenant_a):
        rows = [{"username": "ok-1"}] + [
            {"username": "bad"} if i == 1 else {"username": f"ok-{i}"} for i in range(1, 13)
        ]
        rows[1] = {"username": " bad"}  # spasi tepi
        rows.append({"kind": "pppoe"})  # tanpa username
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "banyak.csv", "rows": rows},
            headers={"Idempotency-Key": "csv-2"},
        )
        assert resp.status_code == 201
        import_id = resp.json()["id"]
        validation = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/validate", headers={"Idempotency-Key": "csv-2-v"}
        ).json()
        assert validation["total_rows"] == 14
        assert validation["error_rows"] == 2
        assert validation["valid_rows"] == 12
        codes = {(e["row"], e["reason_code"]) for e in validation["row_errors"]}
        assert (3, "whitespace") in codes  # index 1 → baris 3 (baris 1 header)
        assert (15, "required") in codes
        assert len(validation["preview"]) == 10  # preview dibatasi 10 baris

        # Batas baris: 5001 → 422.
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "besar.csv", "rows": [{"username": f"x-{i}"} for i in range(5001)]},
            headers={"Idempotency-Key": "csv-3"},
        )
        assert resp.status_code == 422
        assert resp.json()["field_errors"]["rows"][0]["code"] == "max_rows"

        # Commit sebelum validasi → 422 (paritas mock).
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "belum.csv", "rows": [{"username": "belum"}]},
            headers={"Idempotency-Key": "csv-4"},
        )
        resp = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{resp.json()['id']}/commit",
            headers={"Idempotency-Key": "csv-4-c"},
        )
        assert resp.status_code == 422

    def test_unavailable_modes_honest_503(self, reauth_client, tenant_a):
        for mode in ("password_migration", "device_mapping"):
            resp = reauth_client.post(
                f"/api/v1/tenants/{tenant_a.id}/imports",
                {"mode": mode, "file_name": "mode.csv", "rows": [{"username": "x"}]},
                headers={"Idempotency-Key": f"csv-mode-{mode}"},
            )
            assert resp.status_code == 201
            import_id = resp.json()["id"]
            resp = reauth_client.post(
                f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/validate",
                headers={"Idempotency-Key": f"csv-mode-{mode}-v"},
            )
            assert resp.status_code == 503  # jujur: belum tersedia beta
            assert resp.json()["code"] == "dependency_unavailable"
            resp = reauth_client.post(
                f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/commit",
                headers={"Idempotency-Key": f"csv-mode-{mode}-c"},
            )
            assert resp.status_code == 503

    def test_link_mode_commit(self, reauth_client, tenant_a):
        from domains.customers import services as cust_services

        # Layanan tanpa akun + akun lepas (dibuat dulu lalu dilepas via link).
        with tenant_scope(tenant_a.id):
            with_account = cust_services.provision_service_draft(
                tenant_a, {"customer_name": "Punya Akun", "username": "link.me"}
            )
            bare = cust_services.provision_service_draft(tenant_a, {"customer_name": "Tanpa Akun"})
        rows = [{"username": "link.me", "service_code": bare.service_code}]
        import_id = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "link", "file_name": "link.csv", "rows": rows},
            headers={"Idempotency-Key": "csv-link"},
        ).json()["id"]
        validation = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/validate", headers={"Idempotency-Key": "csv-link-v"}
        ).json()
        assert validation["valid_rows"] == 1
        job = reauth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports/{import_id}/commit", headers={"Idempotency-Key": "csv-link-c"}
        ).json()
        result = _run_job(job["job_id"])
        assert result.state == "succeeded"

        from domains.customers.models import AccessAccount

        with tenant_scope(tenant_a.id):
            account = AccessAccount.objects.get(username="link.me")
            assert account.service_id == bare.id  # tertaut ke layanan target


class TestRolePermissions:
    def test_viewer_read_only(self, tenant_a):
        viewer = User.objects.create_user(
            email="viewer-cust@test.local", full_name="Viewer Cust", password="pass-123456789012", is_active=True
        )
        Membership.objects.create(user=viewer, tenant=tenant_a, role=Role.VIEWER)
        from rest_framework.test import APIClient

        client = APIClient(enforce_csrf_checks=False)
        client.force_login(viewer)
        session = client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session["auth_at"] = __import__("time").time()
        session["reauth_until"] = "2099-01-01T00:00:00+00:00"
        session.save()

        assert client.get(f"/api/v1/tenants/{tenant_a.id}/services").status_code == 200  # customers.read
        resp = client.post(
            f"/api/v1/tenants/{tenant_a.id}/services",
            {"customer_name": "Dilarang"},
            headers={"Idempotency-Key": "viewer-1"},
        )
        assert resp.status_code == 403  # tanpa services.provision
        resp = client.post(
            f"/api/v1/tenants/{tenant_a.id}/imports",
            {"mode": "create", "file_name": "x.csv", "rows": []},
            headers={"Idempotency-Key": "viewer-2"},
        )
        assert resp.status_code == 403  # tanpa imports.run
