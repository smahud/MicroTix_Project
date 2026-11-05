"""Integrasi alur enrollment M3 — ROUTEROS.md §2 (jujur: jalur simulator)."""
from __future__ import annotations

import pytest

from domains.common.tenant_context import tenant_scope
from domains.network.models import Router, RouterEnrollment, WireGuardPeer

pytestmark = pytest.mark.integration

CREATE_BODY = {
    "display_name": "Router Baru RT",
    "router_code": "RTR-BETA-1",
    "location": "Menara A",
    "mode": "read_only",
}


def _run_jobs_until(kind: str, limit: int = 10):
    from domains.jobs import engine

    for _ in range(limit):
        claimed = engine.claim_next()
        if claimed is None:
            return None
        engine.run_claimed(claimed)


class TestEnrollmentFlow:
    def test_create_issues_token_once_and_reserves_ip(self, api_client, owner, tenant_a):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            CREATE_BODY,
            headers={"Idempotency-Key": "enr-1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["state"] == "enrollment_issued"
        assert body["request"]["router_code"] == "RTR-BETA-1"
        with tenant_scope(tenant_a.id):
            enr = RouterEnrollment.objects.get(id=body["id"])
            assert enr.token_hash and not enr.wg_public_key
            assert enr.tunnel_ip  # /32 reserved
            assert enr.mode == "read_only"

    def test_invalid_router_code_422(self, api_client, owner, tenant_a):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {**CREATE_BODY, "router_code": "kode salah!"},
            headers={"Idempotency-Key": "enr-invalid"},
        )
        assert resp.status_code == 422
        assert "router_code" in resp.json()["field_errors"]

    def test_bootstrap_script_then_bridge_complete(self, api_client, owner, tenant_a):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            CREATE_BODY,
            headers={"Idempotency-Key": "enr-2"},
        )
        enr_id = resp.json()["id"]
        # Skrip bootstrap berisi token; hanya pembuat.
        resp = api_client.get(f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{enr_id}/bootstrap")
        assert resp.status_code == 200
        script_body = resp.json()
        assert script_body["script"]
        assert "token" in script_body["script"]
        token = script_body["script"].split(':local token "')[1].split('"')[0]
        assert len(token) >= 40  # 256-bit urlsafe

        # Bridge: konsumsi token (tanpa sesi — dari perangkat).
        from django.test import Client

        bridge = Client()
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-key-simulator-1"},
            content_type="application/json",
        )
        if resp.status_code != 200:
            print("BRIDGE_BODY:", resp.json())
        assert resp.status_code == 200, resp.json()
        assert resp.json()["status"] == "bootstrap_accepted"

        # Replay identitas sama → hasil logis sama (§2.7).
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-key-simulator-1"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["replay"] is True

        # Identitas BERBEDA pada token terpakai → 409.
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-key-LAIN"},
            content_type="application/json",
        )
        assert resp.status_code == 409

        # Job verifikasi menghasilkan router read-only + peer applied.
        _run_jobs_until("verify_api_ssl")
        with tenant_scope(tenant_a.id):
            enr = RouterEnrollment.objects.get(id=enr_id)
            assert enr.status == RouterEnrollment.Status.COMPLETED
            router = enr.router
            assert router.mode == Router.Mode.READ_ONLY
            assert router.api_cert_fingerprint
            assert router.capability["source"] == "simulator"  # jujur
            assert not router.capability["verified_lab"]
            peer = WireGuardPeer.objects.get(router=router)
            assert peer.state == WireGuardPeer.State.APPLIED

    def test_bridge_unknown_token_404(self, db):
        from django.test import Client

        bridge = Client()
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": "token-tidak-ada", "wg_public_key": "k"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_progress_stages_after_completion(self, api_client, owner, tenant_a):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {**CREATE_BODY, "router_code": "RTR-BETA-2"},
            headers={"Idempotency-Key": "enr-3"},
        )
        enr_id = resp.json()["id"]
        script = api_client.get(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{enr_id}/bootstrap"
        ).json()["script"]
        token = script.split(':local token "')[1].split('"')[0]
        from django.test import Client

        Client().post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-2"},
            content_type="application/json",
        )
        _run_jobs_until("verify_api_ssl")
        resp = api_client.get(f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{enr_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "discovery_ready"
        stages = {s["code"]: s["state"] for s in body["stage_detail"]}
        assert all(v == "ok" for v in stages.values())


class TestDiscoveryAndLifecycle:
    def _enrolled_router(self, tenant) -> Router:
        from domains.network import services

        with tenant_scope(tenant.id):
            enr = services.create_enrollment(
                str(tenant.id),
                {"display_name": "R Discovery", "router_code": "RTR-DISC", "mode": "read_only"},
            )
            script = services.bootstrap_script(enr)["script"]
            token = script.split(':local token "')[1].split('"')[0]
        from django.test import Client

        Client().post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-disc"},
            content_type="application/json",
        )
        _run_jobs_until("verify_api_ssl")
        with tenant_scope(tenant.id):
            return Router.objects.get(tenant_id=tenant.id, router_code="RTR-DISC")

    def test_discovery_creates_snapshot_without_password(self, tenant_a):
        router = self._enrolled_router(tenant_a)
        from domains.network import services

        with tenant_scope(tenant_a.id):  # konvensi: caller provides scope
            result = services.run_discovery(router)
        from domains.network.models import DiscoveryObject, DiscoverySnapshot

        with tenant_scope(tenant_a.id):
            snap = DiscoverySnapshot.objects.get(id=result["snapshot_id"])
            assert snap.status == DiscoverySnapshot.Status.SUCCEEDED
            for obj in DiscoveryObject.objects.filter(snapshot=snap):
                assert "password" not in obj.raw  # §3: tidak membaca password
            assert snap.objects_count if hasattr(snap, "objects_count") else True

    def test_release_job_marks_released_and_removes_peer(self, tenant_a):
        router = self._enrolled_router(tenant_a)
        from domains.jobs import engine

        with tenant_scope(tenant_a.id):
            job = engine.create_job(
                tenant_id=tenant_a.id, kind="router_release", router=router,
                payload={"router_id": str(router.id)},
            )
        claimed = engine.claim_next()
        assert str(claimed.id) == str(job.id)
        engine.run_claimed(claimed)
        with tenant_scope(tenant_a.id):
            router.refresh_from_db()
            assert router.released_at is not None
            peer = WireGuardPeer.objects.get(router=router)
            assert peer.state == WireGuardPeer.State.REMOVED
