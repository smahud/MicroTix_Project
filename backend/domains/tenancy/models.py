"""Model tenant dan membership — TK-101, ARCHITECTURE.md §3/§4.

Tenant = perusahaan RT/RW Net, pemilik subscription dan data.
User global; membership menghubungkan user↔tenant dengan role+scope.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone as dj_timezone

ROLES = (
    "owner",
    "technician",
    "payments_admin",
    "accountant",
    "viewer",
    "collector",
    "agent",
)


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    TECHNICIAN = "technician", "Teknisi"
    PAYMENTS_ADMIN = "payments_admin", "Admin Pembayaran"
    ACCOUNTANT = "accountant", "Akuntan"
    VIEWER = "viewer", "Viewer"
    COLLECTOR = "collector", "Kolektor"
    AGENT = "agent", "Agen"


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=120)
    # Namespace internal stabil — tidak berubah saat nama display diganti (§9).
    namespace = models.CharField(max_length=32, unique=True, editable=False)
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    # Bahasa default tenant (I18N-06): rantai bahasa dokumen pelanggan =
    # preferensi pelanggan → bahasa default tenant → id (I18N-01 §2).
    locale = models.CharField(max_length=5, default="id")
    created_at = models.DateTimeField(default=dj_timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tenancy_tenant"
        indexes = [models.Index(fields=["id"], name="ix_tenant_id_first")]

    def __str__(self) -> str:  # pragma: no cover
        return self.display_name


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships", db_column="user_id"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships", db_column="tenant_id")
    role = models.CharField(max_length=20, choices=Role.choices)
    # Scope router opsional (teknis); null = seluruh router tenant.
    router_scope = models.JSONField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(default=dj_timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tenancy_membership"
        constraints = [
            models.UniqueConstraint(fields=["user", "tenant"], name="uq_membership_user_tenant"),
        ]
        indexes = [
            models.Index(fields=["tenant", "user"], name="ix_membership_tenant_user"),
        ]

    @property
    def active(self) -> bool:
        return self.revoked_at is None
