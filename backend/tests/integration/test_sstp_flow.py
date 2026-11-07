"""Integrasi alur enrollment SSTP (Phase-2) — master directive konektivitas.

SSTP = transport KOMPLEMENTER WireGuard (v6.49.x/v7.x; matriks kapabilitas
report/researcher/20261106T183941Z §2). Kredensial per-router unik global,
MSCHAPv2 saja, verifikasi sertifikat server WAJIB nyala, listener
shared-port, isolasi tenant, kejujuran verifikasi (simulator ≠ nyata).
"""
from __future__ import annotations

import stat

import pytest

from domains.common.crypto import SecretBox
from domains.common.tenant_context import tenant_scope
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer

pytestmark = pytest.mark.integration

SSTP_BODY = {
    "display_name": "Router SSTP RT",
    "router_code": "RTR-SSTP-1",
    "location": "Menara B",
    "mode": "read_only",
    "protocol": "sstp",
    "routeros_version": "6.49.13",
}


def _run_jobs_until(kind: str, limit: int = 10):
    from domains.jobs import engine

    for _ in range(limit):
        claimed = engine.claim_next()
        if claimed is None:
            return None
        engine.run_claimed(claimed)


def _create_sstp(tenant, **overrides) -> RouterEnrollment:
    from domains.network import services

    body = {**SSTP_BODY, **overrides}
    with tenant_scope(tenant.id):
        return services.create_enrollment(str(tenant.id), body)


def _script_and_account(enrollment: RouterEnrollment) -> tuple[str, SstpAccount]:
    from domains.network import services

    with tenant_scope(enrollment.tenant_id):
        payload = services.bootstrap_script(enrollment)
        account = SstpAccount.objects.get(enrollment=enrollment)
    return payload["script"], account


class TestSstpDraft:
    def test_create_sstp_draft_v6_and_v7_issues_unique_credentials(self, api_client, owner, tenant_a):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            SSTP_BODY,
            headers={"Idempotency-Key": "sstp-1"},
        )
        assert resp.status_code == 201, resp.json()
        with tenant_scope(tenant_a.id):
            enr = RouterEnrollment.objects.get(id=resp.json()["id"])
            assert enr.protocol == "sstp"
            assert enr.routeros_version == "6.49.13"
            assert enr.tunnel_ip not in ("100.127.0.1", "100.127.0.2")  # alamat gateway dikecualikan
            account = SstpAccount.objects.get(enrollment=enr)
            assert account.username.startswith("mtx-rtr-sstp-1-")
            assert len(account.username) <= 48
            assert account.password_ref  # SecretBox, bukan plaintext
            assert SecretBox.decrypt_str(account.password_ref)  # terbaca oleh proses aplikasi
            assert account.tunnel_ip == enr.tunnel_ip
            assert account.state == SstpAccount.State.PENDING
            # Tidak ada peer WireGuard untuk enrollment SSTP.
            assert not WireGuardPeer.objects.filter(enrollment=enr).exists()
        # v7 juga sah (komplementer, bukan pengganti).
        resp7 = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {**SSTP_BODY, "router_code": "RTR-SSTP-7", "routeros_version": "7.15.3"},
            headers={"Idempotency-Key": "sstp-2"},
        )
        assert resp7.status_code == 201

    def test_sstp_rejects_v5_and_below(self, api_client, owner, tenant_a):
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {**SSTP_BODY, "router_code": "RTR-SSTP-V5", "routeros_version": "5.26"},
            headers={"Idempotency-Key": "sstp-v5"},
        )
        assert resp.status_code == 422
        assert resp.json()["field_errors"]["routeros_version"][0]["code"] == "sstp_requires_v6"

    def test_wireguard_v6_still_rejected_with_sstp_hint(self, api_client, owner, tenant_a):
        """v6 tidak memuat WireGuard — penolakan WireGuard mengarah ke SSTP."""
        api_client.force_login(owner)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/router-enrollments",
            {**SSTP_BODY, "router_code": "RTR-WG-V6", "protocol": "wireguard", "routeros_version": "6.49.13"},
            headers={"Idempotency-Key": "sstp-wgv6"},
        )
        assert resp.status_code == 422
        assert resp.json()["field_errors"]["routeros_version"][0]["code"] == "wireguard_requires_v7"

    def test_username_unique_cross_tenant(self, db, tenant_a, tenant_b):
        """Kode router sama pada dua tenant → kredensial BERBEDA (isolasi §7)."""
        enr_a = _create_sstp(tenant_a, router_code="RTR-SAMA")
        enr_b = _create_sstp(tenant_b, router_code="RTR-SAMA")
        with tenant_scope(tenant_a.id):
            user_a = SstpAccount.objects.get(enrollment=enr_a).username
        with tenant_scope(tenant_b.id):
            user_b = SstpAccount.objects.get(enrollment=enr_b).username
        assert user_a != user_b
        # RLS: akun tenant A tidak terlihat dalam scope tenant B.
        with tenant_scope(tenant_b.id):
            assert not SstpAccount.objects.filter(username=user_a).exists()


class TestSstpBootstrapScript:
    def test_script_content_security_invariants(self, db, tenant_a):
        enr = _create_sstp(tenant_a)
        script, account = _script_and_account(enr)
        password = SecretBox.decrypt_str(account.password_ref)
        # Endpoint = gateway publik + port shared-port dari registri (4443).
        assert "connect-to=microtix.invalid" in script
        assert "port=4443" in script
        assert ':local user "mtx-rtr-sstp-1-' in script  # kredensial per-router
        assert f'pass "{password}"' in script  # kredensial per-router
        # MSCHAPv2 SAJA — tidak ada PAP/CHAP/MSCHAPv1 (auth tak aman).
        assert "authentication=mschap2" in script
        assert "pap" not in script.replace("mschap2", "").lower()
        # Verifikasi sertifikat server WAJIB nyala + alamat dari sertifikat.
        assert "verify-server-certificate=yes" in script
        assert "verify-server-address-from-certificate=yes" in script
        assert "verify-server-certificate=no" not in script
        # TIDAK ada route default aktif / TIDAK ada IP tunnel di skrip (IP /32
        # dialokasikan server-side via chap-secrets, bukan diketik di router).
        assert "add-default-route=yes" not in script
        assert str(enr.tunnel_ip) not in script
        # CA platform diunduh dari endpoint publik + diimpor.
        assert "/api/v1/bridge/enroll-ca" in script
        assert '/certificate/import file-name=microtix-ca.crt' in script
        # API-SSL hanya dari alamat PPP server (.2) pada interface manajemen.
        assert "src-address=($gwaddr . \"/32\")" in script
        assert '"rtrw-mgmt-api"' in script
        # Callback: token + identitas kredensial di BODY (§2.2).
        assert "/api/v1/bridge/enroll-complete" in script
        assert '\\"protocol\\":\\"sstp\\"' in script
        assert account.username in script

    def test_script_response_gateway_block(self, db, tenant_a):
        from domains.network import services

        enr = _create_sstp(tenant_a)
        with tenant_scope(tenant_a.id):
            payload = services.bootstrap_script(enr)
        assert payload["protocol"] == "sstp"
        assert payload["gateway"]["listen_port"] == 4443
        assert payload["gateway"]["server_tunnel_ip"] == "100.127.0.2"
        assert payload["gateway"]["hostname"] == "microtix.invalid"
        assert any("sensitif" in p for p in payload["purpose_summary"])


class TestSstpBridge:
    def _enroll_and_consume(self, tenant, username=None):
        from django.test import Client

        enr = _create_sstp(tenant)
        script, account = _script_and_account(enr)
        token = script.split(':local token "')[1].split('"')[0]
        body = {"token": token, "protocol": "sstp", "sstp_username": username or account.username}
        return enr, account, token, Client(), body

    def test_identity_mismatch_409(self, db, tenant_a):
        enr, account, token, bridge, _ = self._enroll_and_consume(tenant_a)
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "protocol": "sstp", "sstp_username": "mtx-penyusup-lain"},
            content_type="application/json",
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "sstp_identity_mismatch"
        with tenant_scope(tenant_a.id):
            enr.refresh_from_db()
            assert enr.status == RouterEnrollment.Status.DRAFT  # tidak berubah diam-diam

    def test_wg_key_rejected_for_sstp_422(self, db, tenant_a):
        enr, account, token, bridge, body = self._enroll_and_consume(tenant_a)
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-salah-protokol"},
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_consume_replay_and_different_identity(self, db, tenant_a):
        enr, account, token, bridge, body = self._enroll_and_consume(tenant_a)
        resp = bridge.post("/api/v1/bridge/enroll-complete", body, content_type="application/json")
        assert resp.status_code == 200, resp.json()
        assert resp.json()["status"] == "bootstrap_accepted"
        # Replay identitas sama → hasil logis sama (§2.7).
        resp = bridge.post("/api/v1/bridge/enroll-complete", body, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["replay"] is True
        # Identitas berbeda pada token terpakai → 409.
        resp = bridge.post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "protocol": "sstp", "sstp_username": "mtx-lain-1"},
            content_type="application/json",
        )
        assert resp.status_code == 409
        # Tidak ada peer WG yang dibuat oleh enrollment SSTP.
        with tenant_scope(tenant_a.id):
            assert not WireGuardPeer.objects.filter(enrollment=enr).exists()

    def test_sstp_username_rejected_for_wireguard_422(self, db, tenant_a):
        from domains.network import services
        from django.test import Client

        with tenant_scope(tenant_a.id):
            enr = services.create_enrollment(
                str(tenant_a.id),
                {"display_name": "R WG", "router_code": "RTR-WG-X", "mode": "read_only"},
            )
            script = services.bootstrap_script(enr)["script"]
        token = script.split(':local token "')[1].split('"')[0]
        resp = Client().post(
            "/api/v1/bridge/enroll-complete",
            {"token": token, "wg_public_key": "wgpub-ok", "sstp_username": "mtx-menyusup"},
            content_type="application/json",
        )
        assert resp.status_code == 422


class TestSstpVerificationHonesty:
    def test_simulator_path_labels_sstp_false(self, db, tenant_a):
        """Jalur simulator: enrollment selesai TANPA klaim tunnel SSTP nyata."""
        enr, account, token, bridge, body = TestSstpBridge()._enroll_and_consume(tenant_a)
        assert bridge.post("/api/v1/bridge/enroll-complete", body, content_type="application/json").status_code == 200
        _run_jobs_until("verify_api_ssl")
        with tenant_scope(tenant_a.id):
            enr.refresh_from_db()
            assert enr.status == RouterEnrollment.Status.COMPLETED
            router = enr.router
            assert router.mode == Router.Mode.READ_ONLY
            cap = router.capability
            assert cap["source"] == "simulator"
            assert cap["sstp"] is False  # jujur: tidak ada sesi PPP nyata
            assert cap["api_ssl"] is False
            assert cap["wireguard"] is False
            account.refresh_from_db()
            assert account.state == SstpAccount.State.APPLIED
            assert account.router_id == router.id
            assert enr.device_identity["sstp_username"] == account.username
            from domains.network import services

            progress = services.enrollment_progress(enr)
        assert progress["verification"]["sstp"] is False
        assert progress["verification"]["source"] == "simulator"

    def test_api_ssl_probe_path_labels_sstp_true(self, db, tenant_a, monkeypatch):
        """Jalur adapter api_ssl: probe TLS nyata melewati tunnel SSTP →
        sstp=True (sesi PPP nyata teramati), wireguard tetap False (jujur)."""
        import adapters.routeros.factory as factory
        from domains.jobs import engine

        class StubAdapter:
            def probe_connectivity(self, ctx):
                return {"ok": True, "cert_sha256": "cd" * 32, "note": "stub-sstp-probe"}

        monkeypatch.setattr(factory, "active_adapter_name", lambda: "api_ssl")
        monkeypatch.setattr(factory, "active_routeros_adapter", lambda: StubAdapter())

        enr, account, token, bridge, body = TestSstpBridge()._enroll_and_consume(tenant_a)
        assert bridge.post("/api/v1/bridge/enroll-complete", body, content_type="application/json").status_code == 200
        job = engine.claim_next()
        assert job is not None and job.kind == "verify_api_ssl"
        engine.run_claimed(job)
        with tenant_scope(tenant_a.id):
            enr.refresh_from_db()
            assert enr.status == RouterEnrollment.Status.COMPLETED
            cap = enr.router.capability
            assert cap["source"] == "api_ssl"
            assert cap["api_ssl"] is True
            assert cap["sstp"] is True  # probe nyata via tunnel SSTP
            assert cap["wireguard"] is False  # tidak ada klaim WG
            assert enr.router.api_cert_fingerprint == "cd" * 32  # pin teramati

    def test_release_revokes_sstp_account(self, db, tenant_a):
        from domains.jobs import engine
        from domains.network.models import Router

        enr, account, token, bridge, body = TestSstpBridge()._enroll_and_consume(tenant_a)
        assert bridge.post("/api/v1/bridge/enroll-complete", body, content_type="application/json").status_code == 200
        _run_jobs_until("verify_api_ssl")
        with tenant_scope(tenant_a.id):
            router = Router.objects.get(enrollment=enr)
            engine.create_job(
                tenant_id=str(tenant_a.id), kind="router_release", router=router,
                payload={"router_id": str(router.id)},
            )
        _run_jobs_until("router_release")
        with tenant_scope(tenant_a.id):
            account.refresh_from_db()
            assert account.state == SstpAccount.State.REMOVED  # revoke — tak dirender lagi


class TestSstpHostRender:
    def test_render_sstp_config_files(self, db, tenant_a, tenant_b, tmp_path):
        from domains.network import services

        enr_a = _create_sstp(tenant_a)
        enr_b = _create_sstp(tenant_b, router_code="RTR-SSTP-B")
        for enr in (enr_a, enr_b):
            with tenant_scope(enr.tenant_id):
                enr.status = RouterEnrollment.Status.BOOTSTRAPPED
                enr.save(update_fields=["status"])
        # Akun REMOVED tidak dirender.
        with tenant_scope(tenant_b.id):
            SstpAccount.objects.filter(enrollment=enr_b).update(state=SstpAccount.State.REMOVED)

        result = services.render_sstp_config(str(tmp_path))
        assert result["status"] == "ok"
        assert result["listen_port"] == 4443
        assert result["gateway_ppp_address"] == "100.127.0.2"
        assert result["accounts"] == 1
        conf = (tmp_path / "accel-ppp.conf").read_text()
        assert "port=4443" in conf
        assert "ssl-protocol=tls1.2" in conf
        assert "ssl-ciphers=AES256-SHA:AES256-GCM-SHA384" in conf
        assert "gw-ip-address=100.127.0.2" in conf
        assert "ifname=mtx-sstp%d" in conf
        assert "auth_mschap_v2" in conf
        assert "auth_pap" not in conf  # tanpa modul auth tak aman
        secrets = (tmp_path / "chap-secrets").read_text()
        with tenant_scope(tenant_a.id):
            account = SstpAccount.objects.get(enrollment=enr_a)
        password = SecretBox.decrypt_str(account.password_ref)
        assert f"{account.username} {password} {account.tunnel_ip}" in secrets
        # Mode berkas 0600 (sensitif — password kredensial).
        for p in (tmp_path / "accel-ppp.conf", tmp_path / "chap-secrets"):
            assert stat.S_IMODE(p.stat().st_mode) & 0o777 == 0o600

    def test_allocate_tunnel_ip_skips_gateway_addresses(self, db, tenant_a):
        from domains.network import services

        enr = _create_sstp(tenant_a)
        assert str(enr.tunnel_ip) == "100.127.0.3"  # .1 (WG) + .2 (SSTP) dikecualikan


class TestEnrollCaEndpoint:
    def test_unconfigured_honest_409(self, db):
        from django.test import Client

        resp = Client().get("/api/v1/bridge/enroll-ca")
        assert resp.status_code == 409
        assert resp.json()["code"] == "enroll_ca_unconfigured"

    def test_serves_public_ca_bundle(self, db, tmp_path, monkeypatch):
        from django.test import Client

        pem = (
            "-----BEGIN CERTIFICATE-----\n"
            "MIIBkTCB+wIJAPx1\n"
            "-----END CERTIFICATE-----\n"
        )
        ca_file = tmp_path / "ca.crt"
        ca_file.write_text(pem)
        monkeypatch.setenv("MT_SSTP_CA_PATH", str(ca_file))
        resp = Client().get("/api/v1/bridge/enroll-ca")
        assert resp.status_code == 200
        assert "BEGIN CERTIFICATE" in resp.content.decode()
        assert "PRIVATE KEY" not in resp.content.decode()  # hanya materi publik

    def test_non_pem_rejected(self, db, tmp_path, monkeypatch):
        from django.test import Client

        bad = tmp_path / "ca.crt"
        bad.write_text("bukan sertifikat")
        monkeypatch.setenv("MT_SSTP_CA_PATH", str(bad))
        resp = Client().get("/api/v1/bridge/enroll-ca")
        assert resp.status_code == 409
        assert resp.json()["code"] == "enroll_ca_invalid"
