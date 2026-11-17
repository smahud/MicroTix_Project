"""Integrasi enrollment router: token, replay, /32 unik, NAS otomatis (TK-301/302)."""
from __future__ import annotations

import pytest
from django.utils import timezone as dj_timezone

from domains.access.models import Nas
from domains.common.tenant_context import tenant_scope
from domains.network import enrollment as enrollment_service
from domains.network.models import ENROLL_TOKEN_TTL_S, Router, RouterEnrollment

pytestmark = pytest.mark.integration


@pytest.fixture
def wg_config(settings):
    settings.MT_WG_SERVER_PUBKEY = "testwgpubkey1234567890abcdef1234567890abcdef1234="
    settings.MT_ENROLL_VERIFY_SOURCE = False  # dev/test: verifikasi sumber via unit terpisah
    settings.MT_PUBLIC_BASE_URL = "https://microtix.test"
    settings.MT_WG_ENDPOINT = "wg.microtix.test:51820"
    return settings


class TestCreateEnrollment:
    def test_create_returns_token_once_and_reserves_ip(self, wg_config, tenant_a, owner):
        enrollment, token = enrollment_service.create_enrollment(
            tenant_id=tenant_a.id,
            actor=owner,
            display_name="RT Net Gateway",
            router_code="RT-GTW-01",
            location="Kantor Pusat",
        )
        assert enrollment.state == RouterEnrollment.State.ENROLLMENT_ISSUED
        assert enrollment.tunnel_ip  # /32 reserved
        # Token plaintext tidak pernah disimpan — hanya hash.
        assert enrollment.token_hash != token
        assert len(token) >= 40
        delta = enrollment.token_expires_at - dj_timezone.now()
        assert 0 < delta.total_seconds() <= ENROLL_TOKEN_TTL_S + 5
        # Audit tercatat tanpa token.
        from domains.audit.models import AuditEvent

        with tenant_scope(tenant_a.id):
            event = AuditEvent.objects.filter(
                action_code="network.enrollment.created", target_id=str(enrollment.id)
            ).first()
        assert event is not None
        assert "token" not in str(event.payload)

    def test_duplicate_active_code_rejected(self, wg_config, tenant_a, owner):
        enrollment_service.create_enrollment(
            tenant_id=tenant_a.id, actor=owner, display_name="Satu", router_code="RT-DUP"
        )
        with pytest.raises(enrollment_service.EnrollmentError) as exc:
            enrollment_service.create_enrollment(
                tenant_id=tenant_a.id, actor=owner, display_name="Dua", router_code="RT-DUP"
            )
        assert exc.value.code == "router_code_active"

    def test_tunnel_ip_unique_across_tenants(self, wg_config, tenant_a, tenant_b, owner):
        """Alokasi /32 lintas tenant tidak bentrok (UNIQUE global)."""
        _, _ = enrollment_service.create_enrollment(
            tenant_id=tenant_a.id, actor=owner, display_name="A", router_code="RT-A1"
        )
        e2, _ = enrollment_service.create_enrollment(
            tenant_id=tenant_b.id, actor=owner, display_name="B", router_code="RT-B1"
        )
        e1 = RouterEnrollment.objects.filter(tenant_id=tenant_a.id).first()
        assert e1.tunnel_ip != e2.tunnel_ip


class TestCompleteEnrollment:
    def _create(self, wg_config, tenant_a, owner, code="RT-C1"):
        return enrollment_service.create_enrollment(
            tenant_id=tenant_a.id, actor=owner, display_name="Gateway", router_code=code
        )

    def test_complete_creates_router_read_only_with_nas(self, wg_config, tenant_a, owner):
        enrollment, token = self._create(wg_config, tenant_a, owner)
        result, created = enrollment_service.complete_enrollment(
            enrollment_id=enrollment.id,
            token=token,
            nonce="RT-C1-enroll",
            router_identity="MikroTik-GTW",
            routeros_version="7.15.3",
            architecture="arm64",
            wireguard_pubkey="pubkey-router-abc",
        )
        assert created is True
        assert result.state == RouterEnrollment.State.CONSUMED
        router = result.router
        assert router.mode == Router.Mode.READ_ONLY
        assert router.tunnel_ip == enrollment.tunnel_ip
        assert router.wireguard_pubkey == "pubkey-router-abc"
        assert router.enforcement_mode == Router.Enforcement.LOCAL
        # NAS desired revision otomatis (TK-307: bersama enrollment).
        with tenant_scope(tenant_a.id):
            nas = Nas.objects.filter(router=router).first()
        assert nas is not None
        assert nas.desired_revision == 1
        assert nas.applied_revision is None

    def test_replay_same_nonce_is_logical(self, wg_config, tenant_a, owner):
        enrollment, token = self._create(wg_config, tenant_a, owner, code="RT-C2")
        first, created = enrollment_service.complete_enrollment(
            enrollment_id=enrollment.id, token=token, nonce="n-1", router_identity="R1",
            routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk1",
        )
        assert created is True
        second, created2 = enrollment_service.complete_enrollment(
            enrollment_id=enrollment.id, token=token, nonce="n-1", router_identity="R1",
            routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk1",
        )
        assert created2 is False
        assert second.id == first.id
        # Tidak ada router ganda.
        with tenant_scope(tenant_a.id):
            assert Router.objects.filter(tenant_id=tenant_a.id, router_code="RT-C2").count() == 1

    def test_different_identity_conflict(self, wg_config, tenant_a, owner):
        enrollment, token = self._create(wg_config, tenant_a, owner, code="RT-C3")
        enrollment_service.complete_enrollment(
            enrollment_id=enrollment.id, token=token, nonce="n-1", router_identity="R1",
            routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk1",
        )
        with pytest.raises(enrollment_service.EnrollmentError) as exc:
            enrollment_service.complete_enrollment(
                enrollment_id=enrollment.id, token=token, nonce="n-2", router_identity="R2",
                routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk2",
            )
        assert exc.value.status == 409

    def test_wrong_token_rejected(self, wg_config, tenant_a, owner):
        enrollment, _token = self._create(wg_config, tenant_a, owner, code="RT-C4")
        with pytest.raises(enrollment_service.EnrollmentError) as exc:
            enrollment_service.complete_enrollment(
                enrollment_id=enrollment.id, token="wrong-token", nonce="n", router_identity="R1",
                routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk",
            )
        assert exc.value.code == "token_invalid"
        # Enrollment tetap aktif (bukan dikonsumsi).
        with tenant_scope(tenant_a.id):
            enrollment.refresh_from_db()
        assert enrollment.state == RouterEnrollment.State.ENROLLMENT_ISSUED

    def test_expired_token_rejected(self, wg_config, tenant_a, owner):
        enrollment, token = self._create(wg_config, tenant_a, owner, code="RT-C5")
        with tenant_scope(tenant_a.id):
            RouterEnrollment.objects.filter(id=enrollment.id).update(
                token_expires_at=dj_timezone.now() - dj_timezone.timedelta(seconds=1)
            )
        with pytest.raises(enrollment_service.EnrollmentError) as exc:
            enrollment_service.complete_enrollment(
                enrollment_id=enrollment.id, token=token, nonce="n", router_identity="R1",
                routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk",
            )
        assert exc.value.code == "token_expired"

    def test_source_verification_enforced_when_enabled(self, wg_config, tenant_a, owner, settings):
        settings.MT_ENROLL_VERIFY_SOURCE = True
        enrollment, token = self._create(wg_config, tenant_a, owner, code="RT-C6")
        # Sumber BUKAN tunnel IP → ditolak.
        with pytest.raises(enrollment_service.EnrollmentError) as exc:
            enrollment_service.complete_enrollment(
                enrollment_id=enrollment.id, token=token, nonce="n", router_identity="R1",
                routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk",
                source_ip="203.0.113.9",
            )
        assert exc.value.code == "source_not_verified"
        # Sumber = tunnel IP reserved → diterima + source_verified.
        _, created = enrollment_service.complete_enrollment(
            enrollment_id=enrollment.id, token=token, nonce="n", router_identity="R1",
            routeros_version="7.15.3", architecture="arm64", wireguard_pubkey="pk",
            source_ip=str(enrollment.tunnel_ip),
        )
        assert created is True


class TestBootstrapScript:
    def test_script_contains_namespace_objects_and_token(self, wg_config, tenant_a, owner):
        enrollment, token = enrollment_service.create_enrollment(
            tenant_id=tenant_a.id, actor=owner, display_name="RT Skrip", router_code="RT-SCR"
        )
        script = enrollment_service.generate_bootstrap_script(
            enrollment, token=token, api_password="ApiPassword123456"
        )
        # Objek bernamespace rtrw- (idempoten; ROUTEROS.md §1).
        assert 'name="rtrw-wg-RT-SCR"' in script
        assert 'name="rtrw-read"' in script
        assert 'name="rtrw-ro-RT-SCR"' in script
        # Allowed-address hanya /32 server — bukan 0.0.0.0/0 pada konfigurasi.
        assert 'allowed-address="100.127.0.1/32"' in script
        assert 'allowed-address="0.0.0.0/0"' not in script
        # Token di body (kanal rahasia), TIDAK di URL.
        assert token in script
        assert f"probe?token={token}" not in script
        # Tidak menyentuh konfigurasi pelanggan.
        for forbidden in ("pppoe-server", "hotspot user", "default-route", "dhcp-server"):
            assert forbidden not in script.lower() or "find" in script.lower()

    def test_script_requires_wg_host_key(self, settings, tenant_a, owner):
        settings.MT_WG_SERVER_PUBKEY = ""
        enrollment, token = enrollment_service.create_enrollment(
            tenant_id=tenant_a.id, actor=owner, display_name="RT NoKey", router_code="RT-NOKEY"
        )
        with pytest.raises(enrollment_service.EnrollmentError) as exc:
            enrollment_service.generate_bootstrap_script(enrollment, token=token)
        assert exc.value.code == "wg_host_not_configured"
