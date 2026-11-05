"""Registri router + enrollment — ROUTEROS.md §2 (TK-301/TK-302).

Router dimiliki satu tenant; credential disimpan sebagai referensi terenkripsi
(bukan plaintext). Enrollment: draft → token hashed TTL 15 menit → reserve
/32 WireGuard unik → bootstrap script bernamespace → complete konsumsi token
(replay-safe) → Router read_only + NAS desired revision + audit, atomik.
Cutover/autoritatif tetap di-gate B0–B6 (belum aktif pada beta).
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


# Jaringan tunnel manajemen (RFC 6598 shared space — ROUTEROS.md §2:
# cek overlap termasuk shared address space 100.127/16).
WG_SERVER_IP = "100.127.0.1"
WG_NETWORK = "100.127.0.0/16"
WG_FIRST_CLIENT_IP = "100.127.0.10"

# TTL token enrollment (TK-301: hashed sekali pakai, TTL 15 menit).
ENROLL_TOKEN_TTL_S = 15 * 60
# Draft enrollment kedaluwarsa bila tidak dilanjutkan.
ENROLL_DRAFT_TTL_S = 24 * 3600


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
    # Kunci publik WireGuard peer (dibangkitkan router; private key tidak
    # pernah dikirim ke platform — ROUTEROS.md §2 langkah 3).
    wireguard_pubkey = models.CharField(max_length=64, blank=True, default="")
    # Fingerprint sertifikat API-SSL (dipin dari complete enrollment
    # terautentikasi — ROUTEROS.md §2 langkah 4).
    api_cert_fingerprint = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, db_column="replaced_by_id", related_name="replaces")

    class Meta:
        db_table = "network_router"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "router_code"], name="uq_router_tenant_code"),
        ]
        indexes = [models.Index(fields=["tenant", "released_at"], name="ix_router_tenant_active")]


class RouterEnrollment(models.Model):
    """Sesi enrollment satu router — ROUTEROS.md §2.

    Token sekali pakai: disimpan HANYA sebagai hash SHA-256; ditampilkan
    sekali saat issue; TTL 15 menit; replay dengan nonce/router-key sama
    mengembalikan logical enrollment (idempoten), identitas berbeda → 409.
    """

    class State(models.TextChoices):
        DRAFT = "draft"
        ENROLLMENT_ISSUED = "enrollment_issued"
        BOOTSTRAP_PENDING = "bootstrap_pending"
        TUNNEL_SEEN = "tunnel_seen"
        API_VERIFIED = "api_verified"
        DISCOVERY_READY = "discovery_ready"
        CONFLICT = "conflict"
        EXPIRED = "expired"
        CONSUMED = "consumed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="router_enrollments", db_column="tenant_id"
    )
    created_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="router_enrollments", db_column="created_by_id"
    )
    display_name = models.CharField(max_length=120)
    router_code = models.CharField(max_length=48)
    location = models.CharField(max_length=160, blank=True, default="")
    model = models.CharField(max_length=64, blank=True, default="")
    # /32 reserved dari WG_NETWORK — unik lintas tenant (cek overlap service).
    tunnel_ip = models.GenericIPAddressField(unique=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    # Token: hash SHA-256; plaintext hanya pada respons issue + bootstrap.
    token_hash = models.CharField(max_length=64, blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    token_used_at = models.DateTimeField(null=True, blank=True)
    # Replay protection: nonce dari pemanggil complete.
    complete_nonce = models.CharField(max_length=64, blank=True, default="", db_index=True)
    # Router dibuat saat complete; enrollment terhubung dua arah.
    router = models.OneToOneField(
        Router, null=True, blank=True, on_delete=models.SET_NULL, related_name="enrollment", db_column="router_id"
    )
    # Identitas perangkat diverifikasi saat complete.
    router_identity = models.CharField(max_length=64, blank=True, default="")
    routeros_version = models.CharField(max_length=32, blank=True, default="")
    architecture = models.CharField(max_length=32, blank=True, default="")
    wireguard_pubkey = models.CharField(max_length=64, blank=True, default="")
    api_cert_fingerprint = models.CharField(max_length=128, blank=True, default="")
    # Apakah complete diterima dari alamat tunnel reserved (bukti jalur WG).
    source_verified = models.BooleanField(default=False)
    # Password akun baca API-SSL (terenkripsi AEAD; disuntik ke skrip
    # bootstrap; dipindah ke router.credential_ref saat complete).
    api_password_ref = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "network_router_enrollment"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "router_code"], condition=models.Q(state__in=["draft", "enrollment_issued", "bootstrap_pending", "tunnel_seen", "api_verified"]), name="uq_enrollment_active_code"),
        ]
        indexes = [models.Index(fields=["tenant", "state"], name="ix_enroll_tenant_state")]


class RouterDiscoverySnapshot(models.Model):
    """Snapshot discovery read-only per router — ROUTEROS.md §3.

    Menyimpan akun PPP/Hotspot yang terbaca (tanpa password), fingerprint,
    revision, dan versi adapter. Discovery tidak pernah menulis router.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="discovery_snapshots", db_column="tenant_id")
    router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name="discovery_snapshots", db_column="router_id")
    adapter = models.CharField(max_length=24, default="simulator")
    routeros_version = models.CharField(max_length=32, blank=True, default="")
    fingerprint = models.CharField(max_length=64, blank=True, default="")
    revision = models.CharField(max_length=32, blank=True, default="")
    accounts = models.JSONField(default=list)
    summary = models.JSONField(default=dict)
    observed_at = models.DateTimeField(default=dj_timezone.now)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "network_discovery_snapshot"
        indexes = [models.Index(fields=["router", "observed_at"], name="ix_discovery_router_time")]


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
