"""Layanan identitas — register, login+MFA, reauth, tenant switch (TK-101).

Aturan (ARCHITECTURE.md §3):
- Password Argon2id min 12 karakter; gagal login max 5/900s per akun dan IP.
- Pesan gagal login tidak mengungkap eksistensi akun.
- Semua aktor wajib TOTP+reauth (600s) untuk aksi sensitif; reauth batal
  saat sesi/role berubah.
- Owner terakhir tidak boleh dihapus/didemote.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from domains.common import crypto
from domains.common.envelope import ApiError
from domains.i18n.catalogs import message
from domains.identity import totp as totp_mod
from domains.identity.models import EmailToken, LoginAttempt, RecoveryCode, TOTPDevice, User
from domains.tenancy.models import Membership, Role, Tenant
from domains.tenancy.permissions import ROLE_PERMISSIONS

FAILED_MAX = 5
WINDOW_S = 900
REAUTH_VALID_S = 600
PENDING_MFA_TTL_S = 300
EMAIL_TOKEN_TTL_S = 60 * 60 * 24


# ---------------------------------------------------------------------------
# Validasi


def validate_registration(email: str, password: str, full_name: str, company_name: str) -> None:
    errors: dict[str, list[dict[str, str]]] = {}
    if not (full_name or "").strip():
        errors["full_name"] = [{"code": "required", "message": "Nama wajib diisi"}]
    if not (email or "").strip() or "@" not in email:
        errors["email"] = [{"code": "email", "message": "Format email tidak valid"}]
    try:
        validate_password(password or "")
    except DjangoValidationError as exc:
        errors["password"] = [{"code": "password", "message": "; ".join(exc.messages)}]
    if not (company_name or "").strip():
        errors["company_name"] = [{"code": "required", "message": "Nama perusahaan wajib diisi"}]
    if errors:
        raise ApiError.validation(errors)


# ---------------------------------------------------------------------------
# Register + verifikasi email


@transaction.atomic
def register(email: str, password: str, full_name: str, company_name: str) -> str:
    validate_registration(email, password, full_name, company_name)
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        # Tidak bocorkan eksistensi akun: balas sukses generik.
        return "registered"
    user = User.objects.create_user(email=email, full_name=full_name.strip(), password=password)
    token = _issue_email_token(user, EmailToken.Kind.VERIFY_EMAIL, meta={"company_name": company_name.strip()})
    _send_email(
        user,
        subject_key="Verifikasi email MicroTix",
        body=(
            "Kode verifikasi email Anda:\n\n{token}\n\n"
            "Kode berlaku 24 jam dan hanya dapat dipakai sekali.\n"
        ).format(token=token),
    )
    return "registered"


def _issue_email_token(user: User, kind: str, meta: dict | None = None) -> str:
    token = crypto.generate_token(32)
    EmailToken.objects.create(
        user=user,
        kind=kind,
        meta=meta or {},
        token_hash=crypto.hash_token(token),
        expires_at=timezone.now() + timezone.timedelta(seconds=EMAIL_TOKEN_TTL_S),
    )
    return token


def _send_email(user: User, *, subject_key: str, body: str) -> None:
    # Dev: backend console (Mailpit saat tersedia). Gagal kirim tidak memblokir
    # alur; token tetap tersimpan dan dapat dikirim ulang.
    try:
        send_mail(subject_key, body, None, [user.email], fail_silently=True)
    except Exception:  # pragma: no cover - dev tanpa SMTP
        pass


@transaction.atomic
def verify_email(token: str) -> User:
    record = (
        EmailToken.objects.filter(token_hash=crypto.hash_token(token or ""), kind=EmailToken.Kind.VERIFY_EMAIL)
        .select_for_update()
        .first()
    )
    now = timezone.now()
    if record is None or record.consumed_at is not None or record.expires_at < now:
        raise ApiError("unauthorized", "auth.token_invalid", 401)
    record.consumed_at = now
    record.save(update_fields=["consumed_at"])
    user = record.user
    user.is_active = True
    user.save(update_fields=["is_active", "updated_at"])
    # Token verifikasi pertama → buat tenant + membership Owner + langganan free.
    if not user.memberships.filter(revoked_at=None).exists():
        company = (record.meta or {}).get("company_name") or user.full_name
        tenant = create_tenant(company)
        Membership.objects.create(user=user, tenant=tenant, role=Role.OWNER)
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.services import ensure_free_subscription

        with tenant_scope(tenant.id):
            ensure_free_subscription(tenant)
    return user


def create_tenant(display_name: str) -> Tenant:
    namespace = "rtrw-" + uuid.uuid4().hex[:10]
    return Tenant.objects.create(display_name=display_name.strip()[:120], namespace=namespace)


# ---------------------------------------------------------------------------
# Login + MFA


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _check_rate_limit(email: str, ip: str) -> None:
    since = timezone.now() - timezone.timedelta(seconds=WINDOW_S)
    recent_failures = LoginAttempt.objects.filter(
        Q(email=email) | Q(ip_address=ip), succeeded=False, attempted_at__gte=since
    ).count()
    if recent_failures >= FAILED_MAX:
        err = ApiError.rate_limited(WINDOW_S)
        err.http_message = message("auth.rate_limited")
        raise err


def _record_attempt(email: str, ip: str, succeeded: bool) -> None:
    LoginAttempt.objects.create(email=email, ip_address=ip, succeeded=succeeded)


def _generic_login_failure() -> ApiError:
    return ApiError("unauthorized", "auth.login_mismatch", 401)


def begin_login(request, email: str, password: str) -> dict:
    """Langkah 1: verifikasi password. Hasil menentukan lanjut MFA atau selesai.

    Sesi 'pending_mfa' berumur 300s dan tidak mengautentikasi apa pun.
    """
    email = (email or "").strip().lower()
    ip = _client_ip(request)
    _check_rate_limit(email, ip)

    user = User.objects.filter(email=email, is_active=True).first()
    ok = False
    if user is not None and user.has_usable_password():
        ok = django_authenticate(request=None, username=email, password=password or "") is not None
    if not ok:
        _record_attempt(email, ip, False)
        raise _generic_login_failure()
    _record_attempt(email, ip, True)

    if user.mfa_enabled:
        request.session["pending_mfa_user"] = str(user.id)
        request.session["pending_mfa_exp"] = timezone.now().timestamp() + PENDING_MFA_TTL_S
        return {"requires_totp": True}

    _establish_session(request, user)
    return {"requires_totp": False}


def complete_totp(request, code: str) -> User:
    """Langkah 2: verifikasi TOTP (atau kode pemulihan) → sesi penuh."""
    user_id = request.session.get("pending_mfa_user")
    exp = request.session.get("pending_mfa_exp", 0)
    if not user_id or timezone.now().timestamp() > float(exp or 0):
        request.session.pop("pending_mfa_user", None)
        request.session.pop("pending_mfa_exp", None)
        raise ApiError("unauthorized", "auth.totp_invalid", 401)
    user = User.objects.filter(id=user_id, is_active=True).first()
    if user is None:
        raise ApiError("unauthorized", "auth.totp_invalid", 401)

    if not _verify_totp_or_recovery(user, (code or "").strip()):
        raise ApiError("unauthorized", "auth.totp_invalid", 401)

    request.session.pop("pending_mfa_user", None)
    request.session.pop("pending_mfa_exp", None)
    _establish_session(request, user)
    return user


def _verify_totp_or_recovery(user: User, code: str) -> bool:
    # 1) kode pemulihan (format xxxx-xxxx-xxxx-xxxx)
    if "-" in code:
        candidate = crypto.hmac_code(code)
        rc = RecoveryCode.objects.filter(user=user, code_hmac=candidate, used_at=None).first()
        if rc is not None:
            rc.used_at = timezone.now()
            rc.save(update_fields=["used_at"])
            return True
        return False
    # 2) TOTP dengan anti-replay
    for device in user.totp_devices.filter(confirmed=True):
        seed = crypto.SecretBox.decrypt_str(device.encrypted_seed)
        step = totp_mod.verify(seed, code, last_used_step=device.last_used_step)
        if step is not None:
            device.last_used_step = step
            device.save(update_fields=["last_used_step"])
            return True
    return False


def _establish_session(request, user: User) -> None:
    django_login(request, user)
    # Sesi absolut + rotasi kunci sesi pada login (session fixation).
    request.session.cycle_key()
    request.session["auth_user"] = str(user.id)
    request.session["auth_at"] = timezone.now().timestamp()
    memberships = list(
        Membership.objects.filter(user=user, revoked_at=None).select_related("tenant").order_by("created_at")
    )
    if memberships:
        request.session["active_tenant_id"] = str(memberships[0].tenant_id)
    request.session.pop("reauth_until", None)


# ---------------------------------------------------------------------------
# MFA setup


@transaction.atomic
def setup_totp(user: User) -> dict:
    """Buat perangkat TOTP baru (belum confirmed). Seed ditampilkan sekali."""
    device = TOTPDevice.objects.create(
        user=user,
        name="default",
        encrypted_seed=crypto.SecretBox.encrypt(totp_mod.generate_seed()),
        confirmed=False,
    )
    seed = crypto.SecretBox.decrypt_str(device.encrypted_seed)
    return {
        "device_id": str(device.id),
        "secret": seed,
        "otpauth_uri": totp_mod.provisioning_uri(seed, user.email),
    }


@transaction.atomic
def confirm_totp(user: User, device_id: str, code: str) -> list[str]:
    """Konfirmasi perangkat + terbitkan 10 kode pemulihan (tampil sekali)."""
    device = user.totp_devices.filter(id=device_id, confirmed=False).first()
    if device is None:
        raise ApiError.not_found()
    seed = crypto.SecretBox.decrypt_str(device.encrypted_seed)
    step = totp_mod.verify(seed, code or "")
    if step is None:
        raise ApiError.validation({"code": [{"code": "invalid", "message": "Kode TOTP tidak sesuai"}]})
    device.confirmed = True
    device.last_used_step = step
    device.save(update_fields=["confirmed", "last_used_step"])
    codes = []
    RecoveryCode.objects.filter(user=user, used_at=None).delete()
    for _ in range(10):
        code_value = crypto.generate_recovery_code()
        RecoveryCode.objects.create(user=user, code_hmac=crypto.hmac_code(code_value))
        codes.append(code_value)
    return codes


# ---------------------------------------------------------------------------
# Sesi, tenant aktif, reauth


@dataclass
class AuthContext:
    user: User
    tenants: list[dict]
    active_tenant_id: str | None
    permissions: list[str]
    sensitive_reauth_until: str | None


def session_expired(request) -> bool:
    """Kebijakan sesi absolut: tenant 24 jam / platform 12 jam (defaults.json)."""
    auth_at = request.session.get("auth_at")
    if auth_at is None:
        return True
    age = timezone.now().timestamp() - float(auth_at)
    platform = request.user.platform_admin if hasattr(request, "user") else False
    limit = 12 * 3600 if platform else 24 * 3600
    return age > limit


def build_auth_context(request) -> AuthContext:
    user = request.user
    memberships = (
        Membership.objects.filter(user=user, revoked_at=None, tenant__archived_at=None)
        .select_related("tenant")
        .order_by("created_at")
    )
    tenants = [
        {"id": str(m.tenant_id), "display_name": m.tenant.display_name, "role": m.role}
        for m in memberships
    ]
    active_id = request.session.get("active_tenant_id")
    if active_id and active_id not in {t["id"] for t in tenants}:
        active_id = tenants[0]["id"] if tenants else None
        request.session["active_tenant_id"] = active_id
    role = next((t["role"] for t in tenants if t["id"] == active_id), None)
    perms = sorted(ROLE_PERMISSIONS.get(role or "", frozenset()))
    reauth_until = request.session.get("reauth_until")
    return AuthContext(
        user=user,
        tenants=tenants,
        active_tenant_id=active_id,
        permissions=perms,
        sensitive_reauth_until=str(reauth_until) if reauth_until else None,
    )


def switch_tenant(request, tenant_id: str) -> AuthContext:
    membership = (
        Membership.objects.filter(user=request.user, tenant_id=tenant_id, revoked_at=None).select_related("tenant").first()
    )
    if membership is None:
        raise ApiError.not_found()
    request.session["active_tenant_id"] = str(membership.tenant_id)
    # Tenant switch: reauth sensitif batal (scope berubah) — §3.
    request.session.pop("reauth_until", None)
    return build_auth_context(request)


def reauthenticate(request, password: str, totp_code: str) -> str:
    """Reauth aksi sensitif: password + TOTP valid → izin 600 detik."""
    user = request.user
    ok = user.check_password(password or "")
    if not ok or not _verify_totp_or_recovery(user, (totp_code or "").strip()):
        raise ApiError("unauthorized", "auth.reauth_failed", 401)
    until = timezone.now() + timezone.timedelta(seconds=REAUTH_VALID_S)
    request.session["reauth_until"] = until.isoformat()
    return until.isoformat()


def require_reauth(request) -> None:
    """Lempar 403 bila reauth sensitif tidak aktif."""
    from domains.tenancy.permissions import is_sensitive

    until = request.session.get("reauth_until")
    if until is None:
        raise ApiError.forbidden()
    try:
        valid = timezone.datetime.fromisoformat(until) > timezone.now()
    except ValueError:
        valid = False
    if not valid:
        raise ApiError.forbidden()


def logout(request) -> None:
    request.session.flush()


# ---------------------------------------------------------------------------
# Tim & proteksi owner terakhir


def active_owner_count(tenant_id) -> int:
    return Membership.objects.filter(tenant_id=tenant_id, role=Role.OWNER, revoked_at=None).count()


def guard_last_owner(membership: Membership, new_role: str | None = None) -> None:
    """Owner terakhir tidak boleh dihapus/didemote (§3)."""
    if membership.role != Role.OWNER:
        return
    changing = membership.revoked_at is not None or (new_role is not None and new_role != Role.OWNER)
    if changing and active_owner_count(membership.tenant_id) <= 1:
        raise ApiError.conflict("conflict", "team.last_owner")
