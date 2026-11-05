"""Model identitas — User, TOTP, kode pemulihan, percobaan login, token email.

User global (bukan tenant-scoped); MFA wajib untuk aksi sensitif (§3).
Password Argon2id; seed TOTP terenkripsi AEAD (kunci di luar DB).
"""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone as dj_timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, *, email: str, full_name: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("email wajib")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, full_name=full_name, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, *, email: str, full_name: str, password: str, **extra):  # pragma: no cover
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(email=email, full_name=full_name, password=password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=False)  # aktif setelah verifikasi email
    is_staff = models.BooleanField(default=False)
    # Peran platform terpisah (Super Admin) — akses agregat saja (§3).
    platform_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        db_table = "identity_user"

    def __str__(self) -> str:  # pragma: no cover
        return self.email

    @property
    def mfa_enabled(self) -> bool:
        return self.totp_devices.filter(confirmed=True).exists()


class TOTPDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="totp_devices", db_column="user_id")
    name = models.CharField(max_length=64, default="default")
    # Seed base32 terenkripsi AEAD — kunci di luar DB (§7).
    encrypted_seed = models.TextField()
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=dj_timezone.now)
    # Jendela langkah yang pernah dipakai — cegah replay kode (RFC 6238).
    last_used_step = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "identity_totp_device"
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uq_totp_user_name"),
        ]


class RecoveryCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes", db_column="user_id")
    # HMAC pepper server — kode tidak disimpan plaintext (§7).
    code_hmac = models.CharField(max_length=64, unique=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "identity_recovery_code"
        indexes = [models.Index(fields=["user"], name="ix_recovery_user")]


class LoginAttempt(models.Model):
    """Pembatasan gagal login per akun dan per IP (auth.failed_max=5/900s)."""

    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    succeeded = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(default=dj_timezone.now, db_index=True)

    class Meta:
        db_table = "identity_login_attempt"
        indexes = [models.Index(fields=["email", "attempted_at"], name="ix_loginattempt_email_time"),
                   models.Index(fields=["ip_address", "attempted_at"], name="ix_loginattempt_ip_time")]


class EmailToken(models.Model):
    """Token sekali pakai untuk verifikasi email/reset — disimpan hash (§3)."""

    class Kind(models.TextChoices):
        VERIFY_EMAIL = "verify_email"
        PASSWORD_RESET = "password_reset"
        INVITATION = "invitation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_tokens", db_column="user_id")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    meta = models.JSONField(default=dict)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "identity_email_token"


class SupportGrant(models.Model):
    """Dukungan Super Admin ke tenant — persetujuan Owner, scope+expiry, banner (§3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="support_grants", db_column="tenant_id")
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_grants_given", db_column="granted_by_id")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_grants_received", db_column="actor_id")
    reason = models.TextField()
    scope = models.JSONField(default=dict)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "identity_support_grant"
        indexes = [models.Index(fields=["tenant"], name="ix_supportgrant_tenant")]
