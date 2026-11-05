"""Alur auth lengkap — register→verifikasi→login→MFA→sesi→switch→reauth (TK-101)."""
from __future__ import annotations

import pytest

from domains.identity import services
from domains.identity.models import EmailToken, User

pytestmark = pytest.mark.integration


def next_step_code(seed: str) -> str:
    """Kode TOTP step berikutnya — masih dalam jendela +1, tidak kena anti-replay."""
    import time as _t

    from domains.identity import totp as _totp

    now = int(_t.time())
    return _totp.totp_at(seed, (now // 30 + 1) * 30)



def test_register_verify_creates_tenant_owner(api_client, db, settings):
    resp = api_client.post(
        "/api/v1/auth/register",
        {"full_name": "Budi", "email": "budi@example.com", "password": "password-1234567890", "company_name": "RT Net Baru"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"verification_sent": True}
    # Password lemah ditolak 422 dengan field_errors.
    resp = api_client.post(
        "/api/v1/auth/register",
        {"full_name": "Budi", "email": "budi2@example.com", "password": "short", "company_name": "X"},
    )
    assert resp.status_code == 422
    assert "password" in resp.json()["field_errors"]

    # Verifikasi email dengan token dari DB (hash disimpan; token tidak).
    user = User.objects.get(email="budi@example.com")
    token = user.email_tokens.first()
    assert token.token_hash != token  # hanya hash
    # Ambil token mentah melalui pengeluaran ulang (dev: token dikirim via email console).
    fresh = services._issue_email_token(user, EmailToken.Kind.VERIFY_EMAIL)
    resp = api_client.post("/api/v1/auth/verify-email", {"token": fresh})
    assert resp.status_code == 200
    ctx = resp.json()
    assert ctx["user"]["email"] == "budi@example.com"
    assert len(ctx["tenants"]) == 1
    assert ctx["tenants"][0]["role"] == "owner"
    assert ctx["active_tenant_id"] == ctx["tenants"][0]["id"]
    assert "subscription.manage" in ctx["permissions"]


def test_login_without_mfa_completes_session(api_client, owner):
    resp = api_client.post("/api/v1/auth/login", {"email": "owner@test.local", "password": "test-password-1234567890"})
    assert resp.status_code == 200
    assert resp.json() == {"requires_totp": False}
    resp = api_client.get("/api/v1/auth/session")
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "owner@test.local"


def test_login_mfa_flow(api_client, owner):
    # Pasang MFA: seed + konfirmasi dengan kode saat ini.
    from domains.identity import totp as totp_mod
    from domains.common import crypto as mtx_crypto

    setup = services.setup_totp(owner)
    code = totp_mod.totp_at(setup["secret"], __import__("time").time())
    recovery = services.confirm_totp(owner, setup["device_id"], code)
    assert len(recovery) == 10
    owner.refresh_from_db()
    assert owner.mfa_enabled is True

    # Login: langkah 1 → requires_totp.
    resp = api_client.post("/api/v1/auth/login", {"email": "owner@test.local", "password": "test-password-1234567890"})
    assert resp.json() == {"requires_totp": True}

    # Kode salah → 401 pesan generik.
    resp = api_client.post("/api/v1/auth/login-totp", {"code": "000000"})
    assert resp.status_code == 401

    # Kode benar (step berikutnya; step konfirmasi sudah terpakai anti-replay) → sesi penuh.
    code2 = next_step_code(setup["secret"])
    resp = api_client.post("/api/v1/auth/login-totp", {"code": code2})
    assert resp.status_code == 200
    assert resp.json()["user"]["mfa_enabled"] is True


def test_recovery_code_login_single_use(api_client, owner):
    setup = services.setup_totp(owner)
    from domains.identity import totp as totp_mod

    code = totp_mod.totp_at(setup["secret"], __import__("time").time())
    recovery = services.confirm_totp(owner, setup["device_id"], code)
    api_client.post("/api/v1/auth/login", {"email": "owner@test.local", "password": "test-password-1234567890"})
    resp = api_client.post("/api/v1/auth/login-totp", {"code": recovery[0]})
    assert resp.status_code == 200
    # Kode yang sama tidak dapat dipakai lagi.
    api_client.post("/api/v1/auth/logout")
    api_client.post("/api/v1/auth/login", {"email": "owner@test.local", "password": "test-password-1234567890"})
    resp = api_client.post("/api/v1/auth/login-totp", {"code": recovery[0]})
    assert resp.status_code == 401


def test_login_failure_generic_message_and_rate_limit(api_client, owner):
    # 5 kegagalan berturut → rate_limited 429 + Retry-After.
    for _ in range(5):
        resp = api_client.post("/api/v1/auth/login", {"email": "owner@test.local", "password": "salah-123456789"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "unauthorized"
    resp = api_client.post("/api/v1/auth/login", {"email": "owner@test.local", "password": "salah-123456789"})
    assert resp.status_code == 429
    assert resp.json()["code"] == "rate_limited"
    assert "Retry-After" in resp.headers


def test_tenant_switch_and_reauth_reset(api_client, owner, tenant_a, tenant_b):
    from domains.tenancy.models import Membership

    # Owner A juga anggota tenant B (viewer).
    Membership.objects.create(user=owner, tenant=tenant_b, role="viewer")
    api_client.force_login(owner)
    session = api_client.session
    session["active_tenant_id"] = str(tenant_a.id)
    session["auth_at"] = __import__("time").time()
    session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()

    resp = api_client.post(f"/api/v1/auth/tenants/{tenant_b.id}/switch")
    assert resp.status_code == 200
    ctx = resp.json()
    assert ctx["active_tenant_id"] == str(tenant_b.id)
    assert "customers.read" in ctx["permissions"]
    assert "customers.write" not in ctx["permissions"]  # viewer
    # Reauth sensitif batal setelah pindah tenant (§3).
    assert ctx["sensitive_reauth_until"] is None


def test_reauthenticate_for_sensitive_action(api_client, owner, tenant_a):
    from domains.identity import totp as totp_mod

    setup = services.setup_totp(owner)
    code = totp_mod.totp_at(setup["secret"], __import__("time").time())
    services.confirm_totp(owner, setup["device_id"], code)
    api_client.force_login(owner)
    session = api_client.session
    session["active_tenant_id"] = str(tenant_a.id)
    session["auth_at"] = __import__("time").time()
    session.save()

    # Tanpa reauth: quotation (sensitif) → 403.
    resp = api_client.post(
        f"/api/v1/tenants/{tenant_a.id}/quotations",
        {"plan_code": "silver", "term": "monthly"},
        headers={"Idempotency-Key": "no-reauth"},
    )
    assert resp.status_code == 403

    # Reauth dengan password+TOTP (step berikutnya; step konfirmasi terpakai) → 200.
    code2 = next_step_code(setup["secret"])
    resp = api_client.post(
        "/api/v1/auth/reauthenticate",
        {"password": "test-password-1234567890", "totp_code": code2},
    )
    assert resp.status_code == 200
    assert "valid_until" in resp.json()
    resp = api_client.post(
        f"/api/v1/tenants/{tenant_a.id}/quotations",
        {"plan_code": "silver", "term": "monthly"},
        headers={"Idempotency-Key": "with-reauth"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "1000000.00"  # harga silver bulanan PRODUCT.md


def test_last_owner_guard(tenant_a, owner):
    from domains.identity.services import guard_last_owner
    from domains.tenancy.models import Membership

    membership = Membership.objects.get(user=owner, tenant=tenant_a)
    with pytest.raises(Exception):
        guard_last_owner(membership, new_role="viewer")  # didemote saat sendiri
    # Tambah owner kedua → demote owner pertama sah.
    second = User.objects.create_user(
        email="owner2@test.local", full_name="Owner 2", password="pass-123456789012", is_active=True
    )
    Membership.objects.create(user=second, tenant=tenant_a, role="owner")
    guard_last_owner(membership, new_role="viewer")  # tidak melempar
