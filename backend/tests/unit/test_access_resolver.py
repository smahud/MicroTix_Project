"""Unit resolver atribut RADIUS (RAD-04) + validasi username (RAD-02)."""
from __future__ import annotations

import datetime

import pytest

from domains.access.models import AccessAccount
from domains.access.resolver import resolve_attributes
from domains.access.services import validate_username

pytestmark = pytest.mark.unit


def _account(**overrides) -> AccessAccount:
    defaults = dict(
        id="00000000-0000-0000-0000-000000000001",
        tenant_id="00000000-0000-0000-0000-000000000aaa",
        username="cust-001",
        kind="pppoe",
        state=AccessAccount.State.ACTIVE,
        credential_state=AccessAccount.CredentialState.READY,
        secret_ref="x",
        simultaneous_use=1,
        mac_lock="",
        static_ip=None,
        static_ip_by_router={},
        allowed_router_ids=None,
        rate_limit_rx_kbps=None,
        rate_limit_tx_kbps=None,
        framed_pool="",
        valid_from=datetime.date.today(),
        valid_until=None,
    )
    defaults.update(overrides)
    return AccessAccount(**defaults)


class TestResolver:
    def test_active_account_check_reply(self):
        account = _account(rate_limit_rx_kbps=10_000, rate_limit_tx_kbps=50_000, framed_pool="pool-rt")
        resolved = resolve_attributes(account)
        assert resolved.reject is False
        # rx = upload pelanggan, tx = download ke pelanggan (bit/s).
        assert resolved.reply["Mikrotik-Rate-Limit"] == "10000000/50000000"
        assert resolved.reply["Framed-Pool"] == "pool-rt"
        assert "Cleartext-Password" not in resolved.check
        assert "Auth-Type" not in resolved.check

    def test_simultaneous_use_only_when_not_one(self):
        assert "Simultaneous-Use" not in resolve_attributes(_account()).check
        resolved = resolve_attributes(_account(simultaneous_use=3))
        assert resolved.check["Simultaneous-Use"] == "3"

    def test_static_ip_precedence_over_pool(self):
        account = _account(static_ip="10.10.0.7", framed_pool="pool-rt")
        resolved = resolve_attributes(account)
        assert resolved.reply.get("Framed-IP-Address") == "10.10.0.7"
        assert "Framed-Pool" not in resolved.reply

    def test_router_override_static_ip(self):
        router_id = "11111111-1111-1111-1111-111111111111"
        account = _account(
            static_ip="10.10.0.7",
            static_ip_by_router={router_id: "10.99.0.9"},
            framed_pool="pool-rt",
        )
        resolved = resolve_attributes(account, router_id=router_id)
        assert resolved.reply["Framed-IP-Address"] == "10.99.0.9"

    def test_expiration_reply(self):
        account = _account(valid_until=datetime.date(2026, 12, 1))
        resolved = resolve_attributes(account)
        assert "01 Dec 2026" in resolved.reply["Expiration"]

    def test_suspended_rejects_without_password(self):
        account = _account(state=AccessAccount.State.SUSPENDED)
        resolved = resolve_attributes(account)
        assert resolved.reject is True
        assert resolved.check == {"Auth-Type": "Reject"}
        assert resolved.reject_reason_code == "policy_suspended"

    def test_disabled_and_expired_states(self):
        assert resolve_attributes(_account(state=AccessAccount.State.DISABLED)).reject_reason_code == "policy_disabled"
        assert resolve_attributes(_account(state=AccessAccount.State.EXPIRED)).reject_reason_code == "policy_expired"

    def test_credential_unknown_rejects(self):
        # password_unknown TIDAK menghasilkan Accept (RAD-10.1 §2).
        resolved = resolve_attributes(_account(credential_state=AccessAccount.CredentialState.UNKNOWN))
        assert resolved.reject is True
        assert resolved.reject_reason_code == "credential_not_ready"

    def test_validity_window(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        assert resolve_attributes(_account(valid_from=tomorrow)).reject_reason_code == "not_yet_valid"
        assert resolve_attributes(_account(valid_until=yesterday)).reject_reason_code == "expired_valid_until"

    def test_allowed_router_ids(self):
        allowed = "22222222-2222-2222-2222-222222222222"
        other = "33333333-3333-3333-3333-333333333333"
        assert resolve_attributes(_account(allowed_router_ids=[allowed]), router_id=allowed).reject is False
        resolved = resolve_attributes(_account(allowed_router_ids=[allowed]), router_id=other)
        assert resolved.reject_reason_code == "router_not_allowed"


class TestUsernameValidation:
    def test_valid(self):
        assert validate_username("cust-001") == "cust-001"

    def test_control_chars_rejected(self):
        with pytest.raises(ValueError):
            validate_username("bad\x01name")

    def test_edge_and_double_space_rejected(self):
        with pytest.raises(ValueError):
            validate_username(" leading")
        with pytest.raises(ValueError):
            validate_username("trailing ")
        with pytest.raises(ValueError):
            validate_username("double  space")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError):
            validate_username("a" * 65)

    def test_utf8_byte_limit(self):
        # 22 karakter emoji ≈ 88 byte UTF-8 → ditolak meski < 64 karakter.
        with pytest.raises(ValueError):
            validate_username("😀" * 22)

    def test_case_sensitive_not_normalized(self):
        assert validate_username("User") != validate_username("user")
