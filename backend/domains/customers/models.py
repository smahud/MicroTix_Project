"""Pelanggan, layanan, akun akses, impor CSV, sesi migrasi (M4).

Kontrak: docs/ARCHITECTURE.md §4/§7, docs/RADIUS.md §3 (AccessAccount) dan
§10.1 (Tahap A discovery/adopsi DB-only), docs/ROUTEROS.md §3 (S1–S4).

- AccessAccount adalah sumber kebenaran AAA; tabel radius.* (proyeksi) datang
  pada fase RADIUS aktif — slice ini DB-only.
- secret_ref menyimpan password terenkripsi (SecretBox), TIDAK PERNAH plaintext.
- commit migrasi/CSV hanya menulis DB; router tidak pernah disentuh (Tahap A).
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


class Customer(models.Model):
    """Pelanggan tenant — customer_code unik per tenant (§4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="customers", db_column="tenant_id")
    display_name = models.CharField(max_length=120)
    customer_code = models.CharField(max_length=32)
    phone = models.CharField(max_length=32, blank=True, default="")
    email = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    # Bahasa komunikasi pelanggan (I18N-01 §2; kosong = belum diset → jatuh
    # ke bahasa default tenant). Menentukan bahasa dokumen terbit (BIL-01).
    locale = models.CharField(max_length=5, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "customers_customer"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "customer_code"], name="uq_customer_tenant_code"),
        ]
        indexes = [models.Index(fields=["tenant", "display_name"], name="ix_customer_tenant_name")]


class Service(models.Model):
    """Layanan internet pelanggan — satu customer banyak service (§4).

    lifecycle dan 4 dimensi tampilan (payment/isolation/connection/job)
    terpisah (UI_UX §5); dimensi connection/job diturunkan saat serialisasi.
    """

    class Kind(models.TextChoices):
        PPPOE = "pppoe"
        HOTSPOT = "hotspot"

    class Lifecycle(models.TextChoices):
        DRAFT = "draft"
        PENDING = "pending"
        PROVISIONING = "provisioning"
        PROVISIONED = "provisioned"
        CONFLICT = "conflict"
        FAILED = "failed"
        TERMINATED = "terminated"
        ARCHIVED = "archived"

    class PaymentStatus(models.TextChoices):
        """Dimensi pembayaran (beta): turunan field, bukan tagihan nyata."""

        UNBILLED = "unbilled"
        PARTIAL = "partial"
        PAID = "paid"
        NOT_BILLED = "not_billed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="services", db_column="tenant_id")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="services", db_column="customer_id")
    service_code = models.CharField(max_length=32)
    # Paket layanan free-text untuk beta; katalog paket tersedia fase berikutnya.
    package_name = models.CharField(max_length=120, blank=True, default="")
    # Paket penagihan M6 (TK-601, BIL-02): kebijakan siklus/waktu/due/jumlah
    # diambil dari sini saat menerbitkan invoice. PROTECT — paket yang dipakai
    # layanan tidak boleh dihapus (nonaktifkan via active=False).
    billing_package = models.ForeignKey(
        "billing.BillingPackage",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="services",
        db_column="billing_package_id",
    )
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.PPPOE)
    lifecycle = models.CharField(max_length=12, choices=Lifecycle.choices, default=Lifecycle.DRAFT)
    payment_status = models.CharField(max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.NOT_BILLED)
    # Router pilihan (preferred router) — pelanggan tidak terikat router (RADIUS §1).
    router = models.ForeignKey("network.Router", null=True, blank=True, on_delete=models.SET_NULL, related_name="services", db_column="router_id")
    start_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_service"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "service_code"], name="uq_service_tenant_code"),
        ]
        # Indeks query aktual (§4): Service(tenant, preferred_router, lifecycle, id).
        indexes = [models.Index(fields=["tenant", "router", "lifecycle", "id"], name="ix_service_tenant_rtr_life")]


class AccessAccount(models.Model):
    """Akun akses AAA — sumber kebenaran (RADIUS.md §3 persis).

    UNIQUE(tenant_id, username): satu namespace per tenant, case-sensitive.
    Username divalidasi di service layer: tanpa spasi tepi, ≤64 karakter dan
    ≤64 byte UTF-8, tanpa karakter kontrol. secret_ref = password terenkripsi
    SecretBox; credential_state terpisah dari state (bukan state kelima).
    """

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="access_accounts", db_column="tenant_id")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="access_accounts", db_column="service_id")
    username = models.CharField(max_length=64)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.PPPOE)
    state = models.CharField(max_length=10, choices=State.choices, default=State.ACTIVE)
    # Password terenkripsi (SecretBox) — plaintext tidak pernah disimpan.
    secret_ref = models.TextField(blank=True, default="")
    credential_state = models.CharField(max_length=16, choices=CredentialState.choices, default=CredentialState.UNKNOWN)
    simultaneous_use = models.IntegerField(default=1)
    mac_lock = models.CharField(max_length=64, null=True, blank=True)
    static_ip = models.GenericIPAddressField(null=True, blank=True)
    # null = semua router tenant; [] = tidak ada (null/kosong bukan sinonim, §4).
    allowed_router_ids = models.JSONField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    revision = models.IntegerField(default=1)
    last_active_session_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_access_account"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "username"], name="uq_access_tenant_username"),
        ]
        indexes = [
            models.Index(fields=["tenant", "state", "id"], name="ix_access_tenant_state"),
            models.Index(fields=["tenant", "service"], name="ix_access_tenant_service"),
        ]


class CsvImport(models.Model):
    """Draf impor CSV (U08) — baris bounded, validasi sinkron, commit via job."""

    class Mode(models.TextChoices):
        CREATE = "create"
        LINK = "link"
        UPDATE = "update"
        DEVICE_MAPPING = "device_mapping"
        PASSWORD_MIGRATION = "password_migration"

    class State(models.TextChoices):
        DRAFT = "draft"
        VALIDATED = "validated"
        COMMITTED = "committed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="csv_imports", db_column="tenant_id")
    mode = models.CharField(max_length=18, choices=Mode.choices, default=Mode.CREATE)
    file_name = models.CharField(max_length=255)
    # Baris hasil parse UI (list dict kolom→nilai); dibatasi ≤ MAX_ROWS.
    rows = models.JSONField(default=list)
    validation = models.JSONField(default=dict)
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        "identity.User", null=True, on_delete=models.SET_NULL, related_name="csv_imports_created", db_column="created_by_id"
    )
    created_at = models.DateTimeField(default=dj_timezone.now)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customers_csv_import"
        indexes = [models.Index(fields=["tenant", "state", "created_at"], name="ix_csvimp_tenant_state_time")]


class MigrationSession(models.Model):
    """Sesi migrasi Tahap A (RADIUS.md §10.1) — adopsi DB-only per router.

    state mengikuti alur wizard: pending_discovery → discovered → resolving →
    ready_to_commit → committing → committed; failed/cancelled terminal.
    """

    class State(models.TextChoices):
        PENDING_DISCOVERY = "pending_discovery"
        DISCOVERED = "discovered"
        RESOLVING = "resolving"
        READY_TO_COMMIT = "ready_to_commit"
        COMMITTING = "committing"
        COMMITTED = "committed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="migration_sessions", db_column="tenant_id")
    router = models.ForeignKey("network.Router", on_delete=models.CASCADE, related_name="migration_sessions", db_column="router_id")
    snapshot = models.ForeignKey(
        "network.DiscoverySnapshot", null=True, blank=True, on_delete=models.SET_NULL, related_name="migration_sessions", db_column="snapshot_id"
    )
    state = models.CharField(max_length=18, choices=State.choices, default=State.PENDING_DISCOVERY)
    # Ringkasan MigrationSummaryCounts (kontrak frontend): to_create/to_merge/
    # unchanged/conflicts/quota_used/quota_limit.
    counts = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "identity.User", null=True, on_delete=models.SET_NULL, related_name="migration_sessions_created", db_column="created_by_id"
    )
    created_at = models.DateTimeField(default=dj_timezone.now)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customers_migration_session"
        indexes = [models.Index(fields=["tenant", "router", "state"], name="ix_migsession_tenant_router")]


class MigrationAccountDecision(models.Model):
    """Keputusan adopsi per objek discovery (selected/ignored/merge/keep_one/rename).

    Default tanpa baris keputusan = selected (diadopsi), kecuali objek dalam
    grup konflik identitas yang belum diselesaikan. keep_one mengecualikan
    sumber lain tanpa menghapusnya; rename membuat identitas DB baru.
    """

    class Decision(models.TextChoices):
        SELECTED = "selected"
        IGNORED = "ignored"
        MERGE = "merge"
        KEEP_ONE = "keep_one"
        RENAME = "rename"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="migration_decisions", db_column="tenant_id")
    session = models.ForeignKey(MigrationSession, on_delete=models.CASCADE, related_name="decisions", db_column="session_id")
    discovery_object = models.ForeignKey(
        "network.DiscoveryObject", on_delete=models.CASCADE, related_name="decisions", db_column="discovery_object_id"
    )
    decision = models.CharField(max_length=10, choices=Decision.choices, default=Decision.SELECTED)
    # Username tujuan untuk rename; dipilih operator (identitas baru, bukan
    # rename lokal diam-diam — RADIUS.md §10.1).
    new_username = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "customers_migration_decision"
        constraints = [
            models.UniqueConstraint(fields=["session", "discovery_object"], name="uq_decision_session_object"),
        ]
        indexes = [models.Index(fields=["tenant", "decision"], name="ix_decision_tenant_decision")]
