"""Registri router + enrollment + discovery + operasi perangkat (M3).

Kontrak: docs/ROUTEROS.md §1–§4, ARCHITECTURE.md §4/§6.
- Enrollment: draft → token hashed TTL → bootstrap → WireGuard peer →
  API-SSL pin → completed. Tanpa reset/reboot; tanpa API publik.
- Discovery: snapshot bounded (properti minimum), tidak membaca password.
- DeviceOperation: jejak DISCOVER→PLAN→DIFF→AUTHORIZE→APPLY→READBACK→
  VERIFY→AUDIT per objek; timeout-after-send → uncertain.
Invariant §4: tenant-first; tunnel IP unik global; token hash only.
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
    # Tunnel IP unik global (WireGuard /32) — reserved saat draft enrollment.
    tunnel_ip = models.GenericIPAddressField(null=True, blank=True, unique=True)
    # Referensi credential terenkripsi (API-SSL user) — tidak plaintext.
    credential_ref = models.TextField(blank=True, default="")
    # Fingerprint sertifikat API-SSL yang dipin dari enrollment complete.
    api_cert_fingerprint = models.CharField(max_length=128, blank=True, default="")
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


class RouterEnrollment(models.Model):
    """Sesi enrollment per ROUTEROS.md §2 — dapat dipulihkan, sekali pakai per token.

    Token enrollment: 256-bit CSPRNG, disimpan HANYA sebagai hash SHA-256,
    TTL terbatas, proteksi replay via nonce/consume atomik.
    """

    class Status(models.TextChoices):
        DRAFT = "draft"                      # dibuat Owner; /32 dirender; token terbit
        AWAITING_BOOTSTRAP = "awaiting_bootstrap"
        BOOTSTRAPPED = "bootstrapped"        # router memanggil bridge dgn token
        VERIFYING = "verifying"              # API-SSL + capability diverifikasi
        COMPLETED = "completed"              # pin tersimpan; read-only aktif
        EXPIRED = "expired"
        FAILED = "failed"
        CANCELLED = "cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="enrollments", db_column="tenant_id")
    router = models.OneToOneField(Router, null=True, blank=True, on_delete=models.CASCADE, related_name="enrollment", db_column="router_id")
    display_name = models.CharField(max_length=120)
    router_code = models.CharField(max_length=48)
    mode = models.CharField(max_length=12, default=Router.Mode.READ_ONLY)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    # /32 unik dari pool host (100.64.0.0/10 carve; cek overlap shared space).
    tunnel_ip = models.GenericIPAddressField(unique=True)
    api_port = models.PositiveIntegerField(default=8729)
    # Token: hash SHA-256 untuk lookup; plaintext disimpan TERENKRIPSI
    # (SecretBox, kunci di luar DB) hanya selama TTL bootstrap, dikosongkan
    # saat konsumsi — skrip bootstrap perlu dirender ulang ≤15 menit.
    token_hash = models.CharField(max_length=64, unique=True)
    token_ref = models.TextField(blank=True, default="")
    token_nonce = models.CharField(max_length=32, blank=True, default="")
    token_expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    # Identitas perangkat terverifikasi saat complete.
    wg_public_key = models.CharField(max_length=64, blank=True, default="")
    api_cert_fingerprint = models.CharField(max_length=128, blank=True, default="")
    device_identity = models.JSONField(default=dict)
    failure_code = models.CharField(max_length=48, blank=True, default="")
    created_by = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL, db_column="created_by_id", related_name="enrollments_created")
    created_at = models.DateTimeField(default=dj_timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "network_router_enrollment"
        indexes = [
            models.Index(fields=["tenant", "status"], name="ix_enroll_tenant_status"),
            models.Index(fields=["token_expires_at"], name="ix_enroll_token_expiry"),
        ]


class WireGuardHost(models.Model):
    """State host WireGuard platform (satu baris) — provisioning via reconciler.

    Private key disimpan sebagai referensi terenkripsi (SecretBox), bukan
    plaintext; reconciler host menulis konfigurasi wg terkelola MicroTix.

    Adopsi keypair installer (instalasi.sh §9.13): publikasi kunci publik
    diambil dari env MT_WG_SERVER_PUBKEY (X25519 base64 dari `wg pubkey`).
    Kunci privat TIDAK pernah masuk proses aplikasi — pegangan host
    (root:600, /etc/microtix/wireguard/server_private.key); private_key_ref
    dikosongkan saat adopsi. Tanpa env (dev/test): fallback deterministik
    jujur (key_source=generated_dev, bukan klaim X25519).
    """

    class KeySource(models.TextChoices):
        INSTALLER_ENV = "installer_env"
        GENERATED_DEV = "generated_dev"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interface_name = models.CharField(max_length=16, default="mtx-wg0")
    listen_port = models.PositiveIntegerField(default=51820)
    subnet_cidr = models.CharField(max_length=24, default="100.127.0.0/16")
    public_key = models.CharField(max_length=64, blank=True, default="")
    private_key_ref = models.TextField(blank=True, default="")
    key_source = models.CharField(
        max_length=16, choices=KeySource.choices, default=KeySource.GENERATED_DEV
    )
    adopted_at = models.DateTimeField(null=True, blank=True)
    desired_revision = models.IntegerField(default=1)
    applied_revision = models.IntegerField(default=0)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "network_wireguard_host"


class WireGuardPeer(models.Model):
    """Peer per router — desired vs applied; /32 unik; reconciler host."""

    class State(models.TextChoices):
        PENDING = "pending"
        APPLIED = "applied"
        DRIFT = "drift"
        REMOVED = "removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="wg_peers", db_column="tenant_id")
    # Router nullable saat fase bridge (peer dibuat sebelum router final;
    # diisi oleh finalize_verification).
    router = models.OneToOneField(Router, null=True, blank=True, on_delete=models.CASCADE, related_name="wg_peer", db_column="router_id")
    enrollment = models.ForeignKey(RouterEnrollment, null=True, blank=True, on_delete=models.SET_NULL, db_column="enrollment_id", related_name="peers")
    allowed_ip = models.GenericIPAddressField(unique=True)
    public_key = models.CharField(max_length=64)
    desired_revision = models.IntegerField(default=1)
    applied_revision = models.IntegerField(default=0)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
    last_handshake_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "network_wireguard_peer"
        indexes = [models.Index(fields=["state", "desired_revision"], name="ix_wgpeer_state_rev")]


class DiscoverySnapshot(models.Model):
    """Satu sesi discovery per router — bounded, tanpa password (§3)."""

    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        STALE = "stale"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="discovery_snapshots", db_column="tenant_id")
    router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name="discovery_snapshots", db_column="router_id")
    adapter_version = models.CharField(max_length=32, default="simulator-1")
    config_fingerprint = models.CharField(max_length=128, blank=True, default="")
    revision = models.IntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(default=dj_timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    job_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "network_discovery_snapshot"
        indexes = [models.Index(fields=["router", "started_at"], name="ix_disc_router_time")]


class DiscoveryObject(models.Model):
    """Objek terdiscover (PPP secret/Hotspot user) — properti minimum §3.

    `raw` menyimpan properti bounded non-sensitif; password TIDAK pernah
    disimpan. state mengikuti wizard adopsi (discovered→selected→adopted…).
    """

    class ObjState(models.TextChoices):
        DISCOVERED = "discovered"
        SELECTED = "selected"
        ADOPTED = "adopted"
        IGNORED = "ignored"
        CONFLICT = "conflict"
        STALE = "stale"

    class Kind(models.TextChoices):
        PPPOE = "pppoe"
        HOTSPOT = "hotspot"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="discovery_objects", db_column="tenant_id")
    snapshot = models.ForeignKey(DiscoverySnapshot, on_delete=models.CASCADE, related_name="discovery_objects", db_column="snapshot_id")
    router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name="discovery_objects", db_column="router_id")
    username = models.CharField(max_length=64)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    # service RouterOS: pppoe | hotspot | any (any = direview per objek §3).
    router_service = models.CharField(max_length=8, default="pppoe")
    profile = models.CharField(max_length=64, blank=True, default="")
    disabled_on_router = models.BooleanField(default=False)
    comment = models.CharField(max_length=255, blank=True, default="")
    remote_address = models.GenericIPAddressField(null=True, blank=True)
    caller_id = models.CharField(max_length=64, blank=True, default="")
    raw = models.JSONField(default=dict)
    state = models.CharField(max_length=12, choices=ObjState.choices, default=ObjState.DISCOVERED)

    class Meta:
        db_table = "network_discovery_object"
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "kind", "username"], name="uq_discobj_snapshot_kind_user"),
        ]
        indexes = [models.Index(fields=["tenant", "username"], name="ix_discobj_tenant_user")]


class DeviceOperation(models.Model):
    """Jejak operasi ter-tipe per objek — PLAN→DIFF→AUTHORIZE→APPLY→
    READBACK→VERIFY→AUDIT (ROUTEROS.md §4).

    Tidak ada eksekusi command bebas; setiap baris adalah operasi ter-tipe
    dengan idempotency key + fencing token + evidence.
    """

    class Status(models.TextChoices):
        PLANNED = "planned"
        AUTHORIZED = "authorized"
        APPLYING = "applying"
        UNCERTAIN = "uncertain"          # timeout-after-send → readback
        APPLIED = "applied"
        VERIFIED = "verified"
        FAILED = "failed"
        ROLLED_BACK = "rolled_back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="device_operations", db_column="tenant_id")
    router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name="device_operations", db_column="router_id")
    op_type = models.CharField(max_length=48)         # mis. wg_peer_add, radius_client_install
    natural_key = models.CharField(max_length=128)
    desired = models.JSONField(default=dict)
    observed = models.JSONField(default=dict)
    plan = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)
    job_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    fencing_token = models.IntegerField(default=0)
    baseline_revision = models.IntegerField(default=1)
    evidence = models.JSONField(default=dict)          # readback/verify evidence
    recovery = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "network_device_operation"
        constraints = [
            models.UniqueConstraint(fields=["router", "op_type", "idempotency_key"], name="uq_devop_idem", condition=~models.Q(idempotency_key="")),
        ]
        indexes = [models.Index(fields=["tenant", "router", "status"], name="ix_devop_tenant_router_status")]
