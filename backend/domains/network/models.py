"""Registri router — fondasi R1 (TK-003; enrollment penuh di M3).

Router dimiliki satu tenant; credential disimpan sebagai referensi terenkripsi
(bukan plaintext). Enrollment/discovery/cutover adalah pekerjaan fase M3+;
model ini menyediakan registri dan status dasar yang dibutuhkuota, job, dan
audit. Invariant §4: satu tenant/router, tunnel IP unik global.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


class Router(models.Model):
    class Mode(models.TextChoices):
        READ_ONLY = "read_only"
        MANAGED = "managed"

    class Enforcement(models.TextChoices):
        LOCAL = "local"
        RADIUS_SHADOW = "radius_shadow"
        RADIUS_AUTHORITATIVE = "radius_authoritative"
        DEGRADED = "degraded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="routers", db_column="tenant_id")
    display_name = models.CharField(max_length=120)
    router_code = models.CharField(max_length=48)
    location = models.CharField(max_length=160, blank=True, default="")
    model = models.CharField(max_length=64, blank=True, default="")
    routeros_version = models.CharField(max_length=32, blank=True, default="")
    identity = models.CharField(max_length=64, blank=True, default="")
    serial = models.CharField(max_length=64, blank=True, default="")
    mode = models.CharField(max_length=12, choices=Mode.choices, default=Mode.READ_ONLY)
    enforcement_mode = models.CharField(max_length=24, choices=Enforcement.choices, default=Enforcement.LOCAL)
    # Tunnel IP unik global (WireGuard /32) — divalidasi di service layer M3.
    tunnel_ip = models.GenericIPAddressField(null=True, blank=True, unique=True)
    # Referensi credential terenkripsi (API-SSL user) — tidak plaintext.
    credential_ref = models.TextField(blank=True, default="")
    capability = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=dj_timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, db_column="replaced_by_id", related_name="replaces")

    class Meta:
        db_table = "network_router"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "router_code"], name="uq_router_tenant_code"),
        ]
        indexes = [models.Index(fields=["tenant", "released_at"], name="ix_router_tenant_active")]


class RouterHealthSample(models.Model):
    """Sampel kesehatan router — sumber/observed_at/quality (§11 monitoring).

Data unavailable tidak pernah ditulis sebagai nol; null = tidak tersedia.
    """

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="router_health_samples")
    router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name="health_samples", db_column="router_id")
    vpn_up = models.BooleanField(null=True)
    api_up = models.BooleanField(null=True)
    cpu_percent = models.IntegerField(null=True)
    memory_percent = models.IntegerField(null=True)
    uptime_s = models.BigIntegerField(null=True)
    observed_at = models.DateTimeField(default=dj_timezone.now)
    collected_at = models.DateTimeField(default=dj_timezone.now)
    source = models.CharField(max_length=32, default="poller")
    quality = models.CharField(max_length=16, default="ok")

    class Meta:
        db_table = "network_router_health"
        indexes = [models.Index(fields=["router", "observed_at"], name="ix_health_router_time")]
