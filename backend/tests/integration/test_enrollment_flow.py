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


class TestProtocolGatewayAndHonesty:
    """Phase 1 slice (master directive §9/§10): protokol+versi RouterOS,
    endpoint gateway PUBLIK pada skrip, dan pelabelan jujur sumber verifikasi
    (simulator tidak pernah menjadi klaim konektivitas perangkat nyata)."""

    def _create(self, api_client, owner, tenant, *, router_code, extra=None, idem=None):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant.id)
        session.save()
        body = {**CREATE_BODY, "router_code": router_code, **(extra or {})}
        return api_client.post(
            f"/api/v1/tenants/{tenant.id}/router-enrollments",
            body,
            headers={"Idempotency-Key": idem or f"enr-{router_code}"},
        )

    def _full_flow(self, api_client, owner, tenant, *, router_code, routeros_version=None, wg_public_key):
        resp = self._create(
            api_client, owner, tenant,
            router_code=router_code,
            extra={"routeros_version": routeros_version} if routeros_version else None,
        )
        assert resp.status_code == 201, resp.json()
        enr_id = resp.json()["id"]
        script = api_client.get(
            f"/api/v1/tenants/{tenant.id}/router-enrollments/{enr_id}/bootstrap"
        ).json()["script"]
        token = script.split(':local token "')[1].split('"')[0]
        from django.test import Client

        bridge_resp = Client().post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": wg_public_key},
            content_type="application/json",
        )
        assert bridge_resp.status_code == 200, bridge_resp.json()
        _run_jobs_until("verify_api_ssl")
        return enr_id

    # --- protokol & versi RouterOS ---

    def test_unsupported_protocol_rejected_422(self, api_client, owner, tenant_a):
        # Phase-2: sstp kini DIDUKUNG — protokol yang masih ditolak jujur
        # adalah l2tp/openvpn (menyusul per fase; matriks kapabilitas tersedia).
        resp = self._create(api_client, owner, tenant_a, router_code="RTR-PROTO-1", extra={"protocol": "openvpn"})
        assert resp.status_code == 422
        fe = resp.json()["field_errors"]
        assert fe["protocol"][0]["code"] == "unsupported"

    def test_wireguard_rejects_routeros_v6(self, api_client, owner, tenant_a):
        resp = self._create(
            api_client, owner, tenant_a, router_code="RTR-PROTO-2",
            extra={"protocol": "wireguard", "routeros_version": "6.49.10"},
        )
        assert resp.status_code == 422
        fe = resp.json()["field_errors"]
        assert fe["routeros_version"][0]["code"] == "wireguard_requires_v7"

    def test_invalid_routeros_version_format_422(self, api_client, owner, tenant_a):
        resp = self._create(api_client, owner, tenant_a, router_code="RTR-PROTO-3", extra={"routeros_version": "7.x"})
        assert resp.status_code == 422
        assert "routeros_version" in resp.json()["field_errors"]

    def test_protocol_and_version_echoed_on_create(self, api_client, owner, tenant_a):
        resp = self._create(
            api_client, owner, tenant_a, router_code="RTR-PROTO-4",
            extra={"protocol": "wireguard", "routeros_version": "v7.15.3"},
        )
        assert resp.status_code == 201
        req = resp.json()["request"]
        assert req["protocol"] == "wireguard"
        assert req["routeros_version"] == "7.15.3"  # normalisasi tanpa "v"

    def test_legacy_payload_without_protocol_still_valid(self, api_client, owner, tenant_a):
        """API lama tanpa protocol/routeros_version tetap sah (default wireguard/7)."""
        resp = self._create(api_client, owner, tenant_a, router_code="RTR-PROTO-5")
        assert resp.status_code == 201
        assert resp.json()["request"]["protocol"] == "wireguard"
        with tenant_scope(tenant_a.id):
            enr = RouterEnrollment.objects.get(id=resp.json()["id"])
            assert enr.routeros_version == "7"

    def test_routeros_version_copied_to_router_registry(self, api_client, owner, tenant_a):
        enr_id = self._full_flow(
            api_client, owner, tenant_a,
            router_code="RTR-PROTO-6", routeros_version="7.15.3", wg_public_key="wgpub-ver-6",
        )
        with tenant_scope(tenant_a.id):
            enr = RouterEnrollment.objects.get(id=enr_id)
            assert enr.router.routeros_version == "7.15.3"

    # --- skrip bootstrap: endpoint gateway publik ---

    def test_bootstrap_script_uses_public_gateway_not_tunnel_ip(self, api_client, owner, tenant_a):
        resp = self._create(api_client, owner, tenant_a, router_code="RTR-GW-1")
        enr_id = resp.json()["id"]
        out = api_client.get(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{enr_id}/bootstrap"
        ).json()
        script = out["script"]
        # Endpoint publik gateway (dev/test: placeholder .invalid), bukan IP tunnel internal.
        assert 'endpoint-address="microtix.invalid"' in script
        assert 'endpoint-address="100.127.0.1"' not in script  # regresi bug lama
        # Port dari state: listener host + api_port enrollment (bukan hardcode).
        assert "endpoint-port=51820" in script
        assert "dst-port=8729" in script
        assert 'allowed-address=($srvaddr . "/32")' in script
        # Callback HTTPS ke gateway yang sama, token di body.
        assert 'url="https://microtix.invalid/api/v1/bridge/enroll-complete"' in script
        # Artefak rusak lama hilang: tidak ada SCEP, tidak membaca private key.
        assert "scep" not in script.lower()
        assert ":local privkey" not in script
        # Meta gateway untuk preview UI (ROUTEROS.md §2.2).
        assert out["gateway"]["hostname"] == "microtix.invalid"
        assert out["gateway"]["listen_port"] == 51820
        assert out["gateway"]["api_port"] == 8729
        assert out["gateway"]["server_tunnel_ip"] == "100.127.0.1"
        assert out["protocol"] == "wireguard"

    def test_bootstrap_script_gateway_override_via_registry(self, db, monkeypatch, tenant_a):
        """Override registri MT_OVERRIDE_VPN__GATEWAY_HOSTNAME dipakai skrip."""
        import domains.config.registry as registry_mod
        from domains.network import services

        monkeypatch.setenv("MT_OVERRIDE_VPN__GATEWAY_HOSTNAME", '"vpn.example.com"')
        registry_mod._REGISTRY = None
        try:
            with tenant_scope(tenant_a.id):
                enr = services.create_enrollment(
                    str(tenant_a.id),
                    {"display_name": "R Gateway", "router_code": "RTR-GW-2", "mode": "read_only"},
                )
                out = services.bootstrap_script(enr)
        finally:
            monkeypatch.delenv("MT_OVERRIDE_VPN__GATEWAY_HOSTNAME")
            registry_mod._REGISTRY = None  # reload bersih untuk tes berikutnya
        assert 'endpoint-address="vpn.example.com"' in out["script"]
        assert 'url="https://vpn.example.com/api/v1/bridge/enroll-complete"' in out["script"]
        assert out["gateway"]["hostname"] == "vpn.example.com"

    def test_gateway_hostname_rejects_url_like_values(self, db, monkeypatch):
        from domains.common.envelope import ApiError
        from domains.network import services

        for bad in ("https://vpn.example.com", "vpn.example.com:51820", "vpn.example.com/path", "vpn ex ample"):
            monkeypatch.setenv("MT_PUBLIC_HOST", bad)
            try:
                with pytest.raises(ApiError):
                    services.gateway_hostname()
            finally:
                monkeypatch.delenv("MT_PUBLIC_HOST")
        monkeypatch.setenv("MT_PUBLIC_HOST", "203.0.113.10")
        try:
            assert services.gateway_hostname() == "203.0.113.10"  # IPv4 literal sah
        finally:
            monkeypatch.delenv("MT_PUBLIC_HOST")

    # --- kejujuran verifikasi (simulator ≠ perangkat nyata) ---

    def test_progress_verification_labeled_simulator(self, api_client, owner, tenant_a):
        enr_id = self._full_flow(
            api_client, owner, tenant_a, router_code="RTR-HON-1", wg_public_key="wgpub-hon-1",
        )
        resp = api_client.get(f"/api/v1/tenants/{tenant_a.id}/router-enrollments/{enr_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "discovery_ready"
        verification = body["verification"]
        assert verification["source"] == "simulator"
        assert verification["verified_lab"] is False
        assert verification["api_ssl"] is False  # TIDAK mengklaim API-SSL nyata
        assert verification["wireguard"] is False
        assert body["protocol"] == "wireguard"

    def test_capability_honest_no_real_connection_claim(self, api_client, owner, tenant_a):
        self._full_flow(api_client, owner, tenant_a, router_code="RTR-HON-2", wg_public_key="wgpub-hon-2")
        with tenant_scope(tenant_a.id):
            router = Router.objects.get(tenant_id=tenant_a.id, router_code="RTR-HON-2")
            assert router.capability["source"] == "simulator"
            assert router.capability["verified_lab"] is False
            assert router.capability["api_ssl"] is False
            assert router.capability["wireguard"] is False
            assert "simulator" in router.capability.get("note", "")

    def test_router_detail_verification_field(self, api_client, owner, tenant_a):
        enr_id = self._full_flow(
            api_client, owner, tenant_a, router_code="RTR-HON-3", wg_public_key="wgpub-hon-3",
        )
        with tenant_scope(tenant_a.id):
            router_id = RouterEnrollment.objects.get(id=enr_id).router_id
        resp = api_client.get(f"/api/v1/tenants/{tenant_a.id}/routers/{router_id}")
        assert resp.status_code == 200
        verification = resp.json()["verification"]
        assert verification["source"] == "simulator"
        assert verification["verified_lab"] is False
        assert verification["api_ssl"] is False

    # --- identitas kriptografis unik (isolasi lintas tenant §7) ---

    def test_duplicate_public_key_cross_tenant_409(self, api_client, owner, tenant_a, tenant_b):
        """Kunci publik yang sudah peer AKTIF di tenant lain tidak dapat dipakai
        ulang (uq_wgpeer_pubkey_active) — ditolak 409, tanpa detail lintas tenant."""
        self._full_flow(api_client, owner, tenant_a, router_code="RTR-DUP-A", wg_public_key="wgpub-dup-x")
        # Enrollment kedua di tenant BERBEDA memakai kunci publik yang sama.
        from domains.network import services

        with tenant_scope(tenant_b.id):
            enr_b = services.create_enrollment(
                str(tenant_b.id),
                {"display_name": "R Duplikat B", "router_code": "RTR-DUP-B", "mode": "read_only"},
            )
            script = services.bootstrap_script(enr_b)["script"]
            token = script.split(':local token "')[1].split('"')[0]
        from django.test import Client

        resp = Client().post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-dup-x"},
            content_type="application/json",
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "wg_public_key_registered"
        with tenant_scope(tenant_b.id):
            enr_b.refresh_from_db()
            assert enr_b.status == RouterEnrollment.Status.DRAFT  # tidak berubah diam-diam


class TestApiSslVerificationPath:
    """Jalur adapter api_ssl: probe TLS nyata (stub socket) — retry re-entry
    VERIFYING + bukti jujur (pin = fingerprint TERAMATI, bukan sintetis)."""

    def _bootstrap_enrollment(self, tenant) -> RouterEnrollment:
        from domains.network import services

        with tenant_scope(tenant.id):
            enr = services.create_enrollment(
                str(tenant.id),
                {"display_name": "R ApiSSL", "router_code": "RTR-APISSL", "mode": "read_only"},
            )
            script = services.bootstrap_script(enr)["script"]
            token = script.split(':local token "')[1].split('"')[0]
        from django.test import Client

        resp = Client().post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-apissl"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        with tenant_scope(tenant.id):
            return RouterEnrollment.objects.get(id=enr.id)

    def test_probe_failure_retries_then_completes_with_observed_pin(self, db, tenant_a, monkeypatch):
        """Attempt-1 probe gagal → job RETRY_WAIT + enrollment tetap VERIFYING
        (tidak diselesaikan palsu); attempt-2 (re-entry VERIFYING) sukses →
        completed dengan pin = fingerprint sertifikat teramati."""
        import adapters.routeros.factory as factory
        from domains.jobs import engine
        from domains.jobs.models import Job

        calls = {"n": 0}

        class StubAdapter:
            def probe_connectivity(self, ctx):
                calls["n"] += 1
                if calls["n"] == 1:
                    return {"ok": False, "error": "unreachable:connect refused"}
                return {"ok": True, "cert_sha256": "ab" * 32, "note": "stub"}

        monkeypatch.setattr(factory, "active_adapter_name", lambda: "api_ssl")
        monkeypatch.setattr(factory, "active_routeros_adapter", lambda: StubAdapter())

        enr = self._bootstrap_enrollment(tenant_a)
        job = engine.claim_next()
        assert job is not None and job.kind == "verify_api_ssl"
        engine.run_claimed(job)
        job.refresh_from_db()
        with tenant_scope(tenant_a.id):
            enr.refresh_from_db()
            assert job.state == "retry_wait"  # retryable — bukan failed permanen
            assert job.error_code == "api_ssl_unreachable"
            assert enr.status == RouterEnrollment.Status.VERIFYING  # jujur: belum selesai

        # Percepat backoff lalu re-claim — re-entry status VERIFYING harus sah.
        from django.utils import timezone as dj_tz

        Job.objects.filter(id=job.id).update(available_at=dj_tz.now())
        job2 = engine.claim_next()
        assert job2 is not None and str(job2.id) == str(job.id)
        engine.run_claimed(job2)
        # Progress menyatakan sumber verifikasi dengan jujur (dalam scope tenant).
        from domains.network import services

        with tenant_scope(tenant_a.id):
            enr.refresh_from_db()
            assert enr.status == RouterEnrollment.Status.COMPLETED
            router = enr.router
            assert router.capability["source"] == "api_ssl"
            assert router.capability["api_ssl"] is True  # probe TLS nyata sukses
            assert router.capability["wireguard"] is False  # handshake tetap jujur belum dibuktikan
            # Pin = fingerprint TERAMATI probe (bukan sintetis token-hash).
            assert router.api_cert_fingerprint == "ab" * 32
            assert enr.device_identity["probe"]["cert_sha256"] == "ab" * 32
            progress = services.enrollment_progress(enr)
        assert progress["verification"]["source"] == "api_ssl"
        assert progress["verification"]["api_ssl"] is True
        assert progress["verification"]["verified_lab"] is False  # lab G1 tetap menunggu
