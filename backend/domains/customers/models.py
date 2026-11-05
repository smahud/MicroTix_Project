"""Pelanggan dan layanan — fondasi R1 (PRODUCT.md §7–§9 ringkas).

Customer = data pelanggan (nama/kontak). Service = satu layanan internet
milik pelanggan pada tenant; terhubung opsional ke AccessAccount (AAA).
Status pembayaran/isolir penuh adalah mesin R2 — di sini hanya state
provisioning yang jujur (draft/provisioned/.../terminated).

Invariant: service dimiliki tenant; pelanggan tidak berpindah tenant;
connection_state dari accounting RADIUS (bukan tebakan), default unknown.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="customers", db_column="tenant_id"
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True, default="")
    email = models.CharField(max_length=254, blank=True, default="")
    address = models.CharField(max_length=240, blank=True, default="")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customer"
        indexes = [models.Index(fields=["tenant", "full_name"], name="ix_customer_tenant_name")]


class Service(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft"
        PROVISIONING = "provisioning"
        PROVISIONED = "provisioned"
        CONFLICT = "conflict"
        FAILED = "failed"
        TERMINATED = "terminated"
        ARCHIVED = "archived"

    class Connection(models.TextChoices):
        ONLINE = "online"
        OFFLINE = "offline"
        UNKNOWN = "unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="services", db_column="tenant_id"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="services", db_column="customer_id"
    )
    display_name = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=16, choices=State.choices, default=State.DRAFT)
    # connection_state diisi dari accounting RADIUS (RAD-07); default unknown.
    connection_state = models.CharField(
        max_length=8, choices=Connection.choices, default=Connection.UNKNOWN
    )
    router = models.ForeignKey(
        "network.Router",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        db_column="router_id",
    )
    package_code = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "service"
        indexes = [models.Index(fields=["tenant", "state"], name="ix_service_tenant_state")]


class CsvImport(models.Model):
    """Impor CSV (S2 — RADIUS.md §10.1): username,password (+opsional).

    Batas 10 MiB / 10.000 baris (TK-404). Validasi streaming di service;
    commit berjalan sebagai job (idempoten per baris: username existing
    dilewati dan dilaporkan, bukan diduplikasi).
    """

    class Mode(models.TextChoices):
        CREATE = "create"
        UPDATE = "update"

    class State(models.TextChoices):
        UPLOADED = "uploaded"
        VALIDATED = "validated"
        COMMITTING = "committing"
        COMMITTED = "committed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="csv_imports", db_column="tenant_id"
    )
    created_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="csv_imports", db_column="created_by_id"
    )
    mode = models.CharField(max_length=8, choices=Mode.choices, default=Mode.CREATE)
    file_name = models.CharField(max_length=200)
    rows = models.JSONField(default=list)
    validation = models.JSONField(default=dict)
    state = models.CharField(max_length=12, choices=State.choices, default=State.UPLOADED)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "customer_csv_import"
        indexes = [models.Index(fields=["tenant", "created_at"], name="ix_csvimport_tenant_time")]
