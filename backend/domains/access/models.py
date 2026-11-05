"""Model akses layanan — sumber kebenaran AAA (RADIUS.md §3).

- AccessAccount: satu namespace username per tenant (case-sensitive,
  UNIQUE(tenant_id, username)); password disimpan TERENKRIPSI pada
  secret_ref (SecretBox AEAD; kunci di luar DB). Proyeksi radcheck memuat
  Cleartext-Password karena CHAP memerlukannya (RAD-05 §1) — risiko
  dikendalikan lewat role radius terbatas + RLS.
- Nas: registry klien RADIUS per router (secret CSPRNG 32 karakter),
  siklus desired_revision → applied_revision (RAD-01 §2 reconciler).
- AccessAccountSource: jejak migrasi/adopsi (router, handle eksternal,
  fingerprint) — adopsi tidak pernah menulis router.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


def _urn() -> str:
    return uuid.uuid4()


class AccessAccount(models.Model):
    class Kind(models.TextChoices):
        PPPOE = "pppoe"
        HOTSPOT = "hotspot"

    class State(models.TextChoices):
        ACTIVE = "active"
        SUSPENDED = "suspended"
        DISABLED = "disabled"
        EXPIRED = "expired"

    class CredentialState(models.TextChoices):
        UNKNOWN = "unknown"
        READY = "ready"
        ROTATION_PENDING = "rotation_pending"

    id = models.UUIDField(primary_key=True, default=_urn, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="access_accounts", db_column="tenant_id"
    )
    service = models.ForeignKey(
        "customers.Service",
        on_delete=models.CASCADE,
        related_name="access_accounts",
        db_column="service_id",
        null=True,
        blank=True,
    )
    username = models.CharField(max_length=64)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.PPPOE)
    state = models.CharField(max_length=12, choices=State.choices, default=State.ACTIVE)
    # Password terenkripsi AEAD (SecretBox) — bukan plaintext.
    secret_ref = models.TextField(blank=True, default="")
    credential_state = models.CharField(
        max_length=16, choices=CredentialState.choices, default=CredentialState.UNKNOWN
    )
    simultaneous_use = models.PositiveIntegerField(default=1)
    mac_lock = models.CharField(max_length=32, blank=True, default="")
    static_ip = models.GenericIPAddressField(null=True, blank=True)
    static_ip_by_router = models.JSONField(default=dict, blank=True)
    allowed_router_ids = models.JSONField(default=list, blank=True)
    # Atribut layanan efektif (rate/pool) — override router > paket > tenant.
    rate_limit_rx_kbps = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_tx_kbps = models.PositiveIntegerField(null=True, blank=True)
    framed_pool = models.CharField(max_length=48, blank=True, default="")
    valid_from = models.DateField(default=dj_timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "access_account"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "username"], name="uq_access_tenant_username"),
            models.CheckConstraint(
                check=~models.Q(username__regex=r"^\s|\s$|\s{2,}") | models.Q(username__exact=""),
                name="ck_access_username_no_edge_space",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "state"], name="ix_access_tenant_state")]


class AccessAccountSource(models.Model):
    """Jejak asal akun (adopsi discovery / impor CSV / S4)."""

    id = models.UUIDField(primary_key=True, default=_urn, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="access_sources", db_column="tenant_id"
    )
    account = models.ForeignKey(
        AccessAccount, on_delete=models.CASCADE, related_name="sources", db_column="account_id"
    )
    router = models.ForeignKey(
        "network.Router", on_delete=models.CASCADE, related_name="adopted_sources", db_column="router_id"
    )
    namespace = models.CharField(max_length=24, default="routeros")
    external_handle = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64, blank=True, default="")
    imported_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "access_account_source"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "router", "namespace", "external_handle"],
                name="uq_access_source_router_handle",
            ),
        ]


class Nas(models.Model):
    """Klien RADIUS per router — desired revision sampai reconciler menerapkan.

    nasname = alamat tunnel /32 router (sumber terverifikasi); secret
    dibangkitkan platform (CSPRNG) dan disimpan terenkripsi; proyeksi
    radius.nas menyimpan bentuk yang dibutuhkan daemon FreeRADIUS.
    """

    id = models.UUIDField(primary_key=True, default=_urn, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="nas_clients", db_column="tenant_id")
    router = models.OneToOneField(
        "network.Router", on_delete=models.CASCADE, related_name="nas", db_column="router_id"
    )
    shortname = models.CharField(max_length=64)
    # Secret terenkripsi AEAD (dibaca hanya reconciler/worker).
    secret_ref = models.TextField()
    desired_revision = models.PositiveIntegerField(default=1)
    applied_revision = models.PositiveIntegerField(null=True, blank=True)
    # type 'other' sesuai skema FreeRADIUS.
    nas_type = models.CharField(max_length=16, default="other")
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "access_nas"
        indexes = [models.Index(fields=["tenant", "desired_revision"], name="ix_nas_tenant_desired")]
