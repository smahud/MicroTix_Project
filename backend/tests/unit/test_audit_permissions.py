"""Audit redaction + izin peran (TK-102)."""
from __future__ import annotations

from domains.audit.models import redact
from domains.tenancy.permissions import ROLE_PERMISSIONS, is_sensitive


def test_redact_strips_secrets():
    payload = {
        "username": "budi",
        "password": "rahasia",
        "nested": {"shared_secret": "abc", "note": "aman"},
        "totp_code": "123456",
        "list": [1, 2],
    }
    cleaned = redact(payload)
    assert cleaned["username"] == "budi"
    assert cleaned["password"] == "[redacted]"
    assert cleaned["nested"]["shared_secret"] == "[redacted]"
    assert cleaned["nested"]["note"] == "aman"
    assert cleaned["totp_code"] == "[redacted]"
    assert cleaned["list"] == [1, 2]


def test_role_permission_matrix():
    # Teknisi: baca operasional, TANPA payments.verify (§3)
    assert "customers.read" in ROLE_PERMISSIONS["technician"]
    assert "payments.verify" not in ROLE_PERMISSIONS["technician"]
    assert "routers.configure" not in ROLE_PERMISSIONS["technician"]
    # Admin pembayaran: verifikasi uang, TANPA konfigurasi WAN
    assert "payments.verify" in ROLE_PERMISSIONS["payments_admin"]
    assert "routers.configure" not in ROLE_PERMISSIONS["payments_admin"]
    # Akuntan: buku
    assert "ledger.post" in ROLE_PERMISSIONS["accountant"]
    # Kolektor: hanya assignment/penerimaannya
    assert set(ROLE_PERMISSIONS["collector"]) == {"collections.receive"}
    assert set(ROLE_PERMISSIONS["agent"]) == set()
    # Viewer: baca saja
    assert set(ROLE_PERMISSIONS["viewer"]) == {"customers.read", "routers.read"}
    # Owner: semua kecuali platform.*
    assert "subscription.manage" in ROLE_PERMISSIONS["owner"]
    assert "platform.payments.approve" not in ROLE_PERMISSIONS["owner"]


def test_sensitive_permissions_flag():
    assert is_sensitive("radius.cutover")
    assert is_sensitive("services.reveal_credentials")
    assert not is_sensitive("customers.read")
    assert not is_sensitive("routers.enroll")
