"""Paket, subscription, reservasi kuota, invoice SaaS — TK-105, PRODUCT.md §3.

Harga numeric(20,2) string desimal — tidak float (ARCHITECTURE §4).
PlanVersion snapshot harga + periode + bahasa + timezone saat terbit (§4).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone as dj_timezone


class PlanVersion(models.Model):
    """Versi paket — harga immutable per versi (PRODUCT.md §3)."""

    class Code(models.TextChoices):
        FREE = "free"
        BRONZE = "bronze"
        SILVER = "silver"
        GOLD = "gold"
        DIAMOND = "diamond"
        PLATINUM = "platinum"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=12, choices=Code.choices, db_index=True)
    version = models.IntegerField(default=1)
    routers_limit = models.IntegerField(null=True, blank=True)  # null = unlimited lisensi
    services_limit = models.IntegerField(null=True, blank=True)
    # Plafon operasional Platinum (SUB-03) — bukan batas lisensi.
    routers_opcap = models.IntegerField(null=True, blank=True)
    services_opcap = models.IntegerField(null=True, blank=True)
    monthly_price = models.DecimalField(max_digits=20, decimal_places=2)
    yearly_price = models.DecimalField(max_digits=20, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    tax_inclusive = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "subs_plan_version"
        constraints = [
            models.UniqueConstraint(fields=["code", "version"], name="uq_plan_code_version"),
        ]


class Subscription(models.Model):
    """Langganan tenant — pemilik entitlement (PRODUCT.md §3)."""

    class State(models.TextChoices):
        FREE = "free"
        PENDING = "pending"
        ACTIVE = "active"
        GRACE = "grace"
        RESTRICTED = "restricted"
        ENDED = "ended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField("tenancy.Tenant", on_delete=models.CASCADE, related_name="subscription", db_column="tenant_id")
    state = models.CharField(max_length=12, choices=State.choices, default=State.FREE)
    plan = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, related_name="subscriptions", db_column="plan_version_id")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    anchor_day = models.IntegerField(null=True, blank=True)
    period_index = models.IntegerField(default=0)
    bonus_offset_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subs_subscription"


class QuotaReservation(models.Model):
    """Reservasi kuota atomik (SUB-02): pending → committed/released/expired."""

    class Resource(models.TextChoices):
        ROUTERS = "routers"
        SERVICES = "services"

    class State(models.TextChoices):
        PENDING = "pending"
        COMMITTED = "committed"
        RELEASED = "released"
        EXPIRED = "expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="quota_reservations", db_column="tenant_id")
    resource = models.CharField(max_length=12, choices=Resource.choices)
    units = models.IntegerField(default=1)
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    created_at = models.DateTimeField(default=dj_timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subs_quota_reservation"
        indexes = [models.Index(fields=["tenant", "resource", "state"], name="ix_quota_tenant_res_state")]


class SaaSInvoice(models.Model):
    """Invoice SaaS — snapshot harga/periode/bahasa/timezone saat terbit (§4)."""

    class State(models.TextChoices):
        DRAFT = "draft"
        OPEN = "open"
        PARTIAL = "partial"
        PAID = "paid"
        VOID = "void"
        EXPIRED = "expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="saas_invoices", db_column="tenant_id")
    plan = models.ForeignKey(PlanVersion, on_delete=models.PROTECT, db_column="plan_version_id")
    state = models.CharField(max_length=8, choices=State.choices, default=State.OPEN)
    term_months = models.IntegerField(default=1)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3, default="IDR")
    period_start = models.DateField()
    period_end = models.DateField()
    locale = models.CharField(max_length=5, default="id")
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    template_version = models.CharField(max_length=16, default="1")
    issued_at = models.DateTimeField(default=dj_timezone.now)
    due_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "subs_saas_invoice"
        indexes = [models.Index(fields=["tenant", "state", "due_at"], name="ix_saasinv_tenant_state_due")]


class PlatformPaymentSourceEvent(models.Model):
    """Event sumber pembayaran platform — immutable (TK-003, R1 untuk R2).

R2 membentuk buku platform dari event ini tanpa duplikasi; baris tidak
    pernah diubah setelah dibuat (trigger immutability di migrasi).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=48)
    submission = models.ForeignKey(
        "subscriptions.PaymentSubmission", null=True, on_delete=models.PROTECT, related_name="source_events", db_column="submission_id"
    )
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.PROTECT, db_column="tenant_id")
    payload = models.JSONField(default=dict)
    dedup_key = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "subs_platform_payment_source_event"


class PaymentSubmission(models.Model):
    """Pengajuan bukti bayar tenant → direview platform (PRODUCT §3)."""

    class State(models.TextChoices):
        SUBMITTED = "submitted"
        REVIEWING = "reviewing"
        APPROVED = "approved"
        REVISION_REQUESTED = "revision_requested"
        REJECTED = "rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="payment_submissions", db_column="tenant_id")
    invoice = models.ForeignKey(SaaSInvoice, on_delete=models.CASCADE, related_name="submissions", db_column="saas_invoice_id")
    state = models.CharField(max_length=20, choices=State.choices, default=State.SUBMITTED)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    # Path opaque penyimpanan privat (TK-106) — bukan URL publik.
    proof_path = models.CharField(max_length=128, blank=True, default="")
    proof_mime = models.CharField(max_length=64, blank=True, default="")
    proof_size = models.IntegerField(default=0)
    submitted_by = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL, db_column="submitted_by_id")
    submitted_at = models.DateTimeField(default=dj_timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # Reviewer platform (M2): pengambil keputusan — mengisi assignee kontrak
    # PlatformPaymentSubmission dan jejak koreksi (FINANCE.md §16 salah approval).
    reviewed_by = models.ForeignKey(
        "identity.User",
        null=True,
        on_delete=models.SET_NULL,
        db_column="reviewed_by_id",
        related_name="payment_submissions_reviewed",
    )
    review_note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "subs_payment_submission"
        indexes = [models.Index(fields=["state", "submitted_at"], name="ix_pay_sub_state_time")]
