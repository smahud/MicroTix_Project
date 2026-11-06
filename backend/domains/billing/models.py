"""Model billing internet M6 — TK-601 (BIL-01/02/03/07, GOAL-02).

Kontrak: docs/PRODUCT.md §BIL (BIL-01 invoice, BIL-02 kebijakan penagihan,
BIL-03 penerimaan pembayaran, BIL-07 promo/add-on, BIL-08 kwitansi),
docs/FINANCE.md §3 (siklus pendapatan — jurnal M7 TK-701 menyusul; slice ini
mencatat sumber dokumen keuangan tanpa posting ledger), docs/ARCHITECTURE.md
§4 (tenant-first, UNIQUE invariant, RLS via migrasi 0002).

Keputusan desain (dicatat untuk traceability):
- Invoice internet dipisah total dari invoice SaaS (namespace nomor dokumen
  berbeda; tabel berbeda karena kebijakan/relasi beda — BIL-03 eksplisit).
- UNIQUE(tenant, service, kind, period_start, period_end) mencegah scheduler
  ganda (AC-BIL: dua scheduler pada periode sama → satu invoice).
- period_index menyimpan urutan periode sejak aktivasi untuk kelanjutan
  scheduler; period_start/period_end tetap kunci tampilan/aging.
- Payment state: submitted (bukti/upload dicatat, BUKAN posted — BIL-03)
  → verified (dana diverifikasi → allocation dibuat) | rejected.
- Alokasi: satu payment → banyak invoice; jumlah dialokasikan ≤ nilai payment
  (sisa = kredit belum dialokasikan, BIL-03/TK-203 semantik).
- Pembayaran TIDAK PERNAH mengubah lifecycle service — aktivasi selalu
  terpisah manual (PRODUCT.md §13; done_when TK-601 "payment cannot
  auto-activate").
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone as dj_timezone


class BillingPackage(models.Model):
    """Kebijakan penagihan per paket (BIL-02) + harga yang disnapshot invoice.

    - billing_cycle: fixed_monthly (bulan kalender) | anniversary (jangkar
      tanggal aktivasi, aturan jangkar SUB-04).
    - timing: prepaid (bayar dulu; issue = start-7 hari default, due = start)
      | postpaid (issue = akhir periode, due = issue+7 hari default).
    - due_day: hanya berlaku pada fixed_monthly — tanggal clamp pertama
      pada/selepas due default (BIL-02).
    - first_period_policy: full | prorata_daily (ceil Rp100) |
      free_until_next_period — disnapshot pada invoice.
    """

    class Cycle(models.TextChoices):
        FIXED_MONTHLY = "fixed_monthly"
        ANNIVERSARY = "anniversary"

    class Timing(models.TextChoices):
        PREPAID = "prepaid"
        POSTPAID = "postpaid"

    class FirstPeriodPolicy(models.TextChoices):
        FULL = "full"
        PRORATA_DAILY = "prorata_daily"
        FREE_UNTIL_NEXT_PERIOD = "free_until_next_period"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="billing_packages", db_column="tenant_id"
    )
    name = models.CharField(max_length=120)
    monthly_price = models.DecimalField(max_digits=20, decimal_places=2)
    billing_cycle = models.CharField(max_length=14, choices=Cycle.choices, default=Cycle.FIXED_MONTHLY)
    timing = models.CharField(max_length=8, choices=Timing.choices, default=Timing.PREPAID)
    due_day = models.IntegerField(null=True, blank=True)
    first_period_policy = models.CharField(
        max_length=24, choices=FirstPeriodPolicy.choices, default=FirstPeriodPolicy.FULL
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "billing_package"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="uq_bilpkg_tenant_name"),
            models.CheckConstraint(check=models.Q(monthly_price__gte=0), name="ck_bilpkg_price_nonneg"),
            models.CheckConstraint(
                check=models.Q(due_day__isnull=True) | (models.Q(due_day__gte=1) & models.Q(due_day__lte=31)),
                name="ck_bilpkg_due_day_range",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "active"], name="ix_bilpkg_tenant_active")]


class ServiceCharge(models.Model):
    """Biaya berulang add-on / diskon per layanan (BIL-07) — snapshot ke line.

    kind add_on: harga positif ditambahkan tiap periode terbit.
    kind discount_nominal: potongan tetap (disimpan positif; line bernilai negatif).
    kind discount_pct: persen (0-100) dari line langganan; line bernilai negatif.
    Masa berlaku valid_from/valid_until (null = tanpa batas); dipakai bila
    aktif dan periode overlap dengan jendela berlaku pada tanggal terbit.
    """

    class Kind(models.TextChoices):
        ADD_ON = "add_on"
        DISCOUNT_NOMINAL = "discount_nominal"
        DISCOUNT_PCT = "discount_pct"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="service_charges", db_column="tenant_id"
    )
    service = models.ForeignKey(
        "customers.Service", on_delete=models.CASCADE, related_name="charges", db_column="service_id"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "billing_service_charge"
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gte=0), name="ck_charge_amount_nonneg"),
        ]
        indexes = [models.Index(fields=["tenant", "service", "active"], name="ix_charge_tenant_svc_active")]


class InternetInvoice(models.Model):
    """Invoice internet satu (service, periode, jenis) — BIL-01.

    state draft/open/partial/paid/void TERPISAH dari payment submission
    platform SaaS. Harga/kebijakan disnapshot pada invoice + lines —
    perubahan harga paket TIDAK mengubah invoice yang sudah terbit
    (done_when TK-601 "issued price unchanged").
    """

    class Kind(models.TextChoices):
        PREPAID = "prepaid"
        POSTPAID = "postpaid"

    class State(models.TextChoices):
        DRAFT = "draft"
        OPEN = "open"
        PARTIAL = "partial"
        PAID = "paid"
        VOID = "void"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="internet_invoices", db_column="tenant_id"
    )
    # PROTECT: catatan keuangan tidak ikut terhapus bila layanan dihapus;
    # layanan historis dibuat nonaktif, bukan dihapus (retensi FINANCE §16).
    service = models.ForeignKey(
        "customers.Service", on_delete=models.PROTECT, related_name="internet_invoices", db_column="service_id"
    )
    kind = models.CharField(max_length=8, choices=Kind.choices)
    state = models.CharField(max_length=8, choices=State.choices, default=State.OPEN)
    # Periode layanan [start, end) — end eksklusif (BIL-01; kontrak [start,end)
    # pada FINANCE.md §3 untuk pengakuan M7).
    period_index = models.IntegerField()
    period_start = models.DateField()
    period_end = models.DateField()
    # INV-{kode_tenant}-{YYYYMM}-{urut} — unik per tenant (BIL-01).
    doc_number = models.CharField(max_length=64)
    currency = models.CharField(max_length=3, default="IDR")
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    # Kebijakan periode pertama disnapshot (BIL-02; terlihat pada dokumen).
    first_period_policy = models.CharField(max_length=24, blank=True, default="")
    due_date = models.DateField()
    issued_at = models.DateTimeField(default=dj_timezone.now)
    issued_by = models.CharField(max_length=120, blank=True, default="")
    # Bahasa/zona terbit dokumen (BIL-01; rantai I18N-01 §2 saat terbit).
    locale = models.CharField(max_length=5, default="id")
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    void_reason = models.TextField(blank=True, default="")
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "billing_internet_invoice"
        constraints = [
            # AC-BIL: dua scheduler pada periode sama → satu invoice (BIL-01).
            models.UniqueConstraint(
                fields=["tenant", "service", "kind", "period_start", "period_end"],
                name="uq_bilinv_period",
            ),
            models.UniqueConstraint(fields=["tenant", "doc_number"], name="uq_bilinv_tenant_number"),
            models.CheckConstraint(check=models.Q(total_amount__gte=0), name="ck_bilinv_total_nonneg"),
            models.CheckConstraint(check=models.Q(paid_amount__gte=0), name="ck_bilinv_paid_nonneg"),
        ]
        indexes = [
            models.Index(fields=["tenant", "state", "due_date"], name="ix_bilinv_tenant_state_due"),
            models.Index(fields=["tenant", "service", "period_index"], name="ix_bilinv_tenant_svc_idx"),
        ]

    @property
    def outstanding(self) -> Decimal:
        return self.total_amount - self.paid_amount


class InternetInvoiceLine(models.Model):
    """Line item invoice — snapshot harga saat terbit (BIL-01/BIL-07).

    amount bertanda: langganan/installasi/add_on positif; diskon negatif.
    Immutable secara aplikasi: hanya dibuat saat penerbitan invoice.
    """

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="invoice_lines", db_column="tenant_id"
    )
    invoice = models.ForeignKey(
        InternetInvoice, on_delete=models.CASCADE, related_name="lines", db_column="invoice_id"
    )
    line_kind = models.CharField(max_length=20)
    name = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    ordinal = models.IntegerField(default=0)

    class Meta:
        db_table = "billing_internet_invoice_line"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "invoice", "ordinal"], name="uq_billine_ordinal"),
        ]
        indexes = [models.Index(fields=["tenant", "invoice"], name="ix_billine_tenant_invoice")]


class InternetPayment(models.Model):
    """Penerimaan pembayaran internet — dua tahap (BIL-03).

    submitted: dicatat (dengan/ tanpa bukti upload) — BUKAN posted payment.
    verified: dana diverifikasi → allocation ke invoice dibuat (BIL-03
    "Verifikasi dana membuat transaksi + allocation"); kwitansi terbit (BIL-08).
    rejected: verifikasi gagal dengan alasan.

    external_ref (nomor mutasi/referensi transfer) opsional-unik per tenant:
    event bank yang sama tidak bisa direkam dua kali (done_when TK-203 replay
    dedup; dua transfer nyata tetap dua Payment).
    """

    class Method(models.TextChoices):
        BANK_TRANSFER = "bank_transfer"
        EWALLET = "ewallet"
        CASH = "cash"
        COLLECTOR_CASH = "collector_cash"

    class State(models.TextChoices):
        SUBMITTED = "submitted"
        VERIFIED = "verified"
        REJECTED = "rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="internet_payments", db_column="tenant_id"
    )
    method = models.CharField(max_length=16, choices=Method.choices)
    state = models.CharField(max_length=10, choices=State.choices, default=State.SUBMITTED)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    external_ref = models.CharField(max_length=128, null=True, blank=True)
    # Bukti transfer/e-wallet (opsional untuk tunai) — path opaque privat.
    proof_path = models.CharField(max_length=128, blank=True, default="")
    proof_mime = models.CharField(max_length=64, blank=True, default="")
    proof_size = models.IntegerField(default=0)
    # Kolektor/agen yang menerima tunai (COL-01; saldonya TK-609).
    collector_display = models.CharField(max_length=120, blank=True, default="")
    submitted_by = models.ForeignKey(
        "identity.User", null=True, on_delete=models.SET_NULL, related_name="payments_recorded", db_column="submitted_by_id"
    )
    submitted_at = models.DateTimeField(default=dj_timezone.now)
    verified_by = models.ForeignKey(
        "identity.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="payments_verified",
        db_column="verified_by_id",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True, default="")
    rejected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "billing_internet_payment"
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="ck_bilpay_amount_pos"),
            models.CheckConstraint(check=models.Q(allocated_amount__gte=0), name="ck_bilpay_alloc_nonneg"),
            models.CheckConstraint(check=models.Q(allocated_amount__lte=models.F("amount")), name="ck_bilpay_alloc_lte"),
            models.UniqueConstraint(fields=["tenant", "external_ref"], name="uq_bilpay_tenant_extref"),
        ]
        indexes = [models.Index(fields=["tenant", "state", "submitted_at"], name="ix_bilpay_tenant_state_time")]

    @property
    def credit(self) -> Decimal:
        """Kredit belum dialokasikan (BIL-03: sisa → unallocated credit)."""
        return self.amount - self.allocated_amount


class PaymentAllocation(models.Model):
    """Alokasi payment → invoice (satu payment → banyak invoice, BIL-03).

    UNIQUE(tenant, payment, invoice): satu pasangan hanya satu baris;
    penambahan alokasi pada pasangan sama diperbarui nilainya, bukan baris baru.
    """

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="payment_allocations", db_column="tenant_id"
    )
    # PROTECT kedua sisi: bukti keuangan tidak boleh terhapus via hapus payment
    # maupun hapus invoice (retensi FINANCE.md §16).
    payment = models.ForeignKey(
        InternetPayment, on_delete=models.PROTECT, related_name="allocations", db_column="payment_id"
    )
    invoice = models.ForeignKey(
        InternetInvoice, on_delete=models.PROTECT, related_name="allocations", db_column="invoice_id"
    )
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    allocated_at = models.DateTimeField(default=dj_timezone.now)
    allocated_by = models.ForeignKey(
        "identity.User", null=True, on_delete=models.SET_NULL, related_name="allocations_made", db_column="allocated_by_id"
    )

    class Meta:
        db_table = "billing_payment_allocation"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "payment", "invoice"], name="uq_bilalloc_pair"),
            models.CheckConstraint(check=models.Q(amount__gt=0), name="ck_bilalloc_amount_pos"),
        ]
        indexes = [models.Index(fields=["tenant", "invoice"], name="ix_bilalloc_tenant_invoice")]
