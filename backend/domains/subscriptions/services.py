"""Layanan subscription: seed paket, kuota atomik, quotation (TK-105).

Harga sesuai PRODUCT.md §3 (final, tanpa pajak tambahan; tarif pajak
per PlanVersion tersedia, default 0). Tahunan = 12 bulan harga 10× bulanan.
"""
from __future__ import annotations

import math
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from domains.common.envelope import ApiError
from domains.subscriptions.models import (
    PaymentSubmission,
    PlanVersion,
    QuotaReservation,
    SaaSInvoice,
    Subscription,
)

# Harga final PRODUCT.md §3 (Rp). Pajak default 0.
PLAN_CATALOG: list[dict] = [
    {"code": "free", "routers": 1, "services": 50, "monthly": "0", "yearly": "0"},
    {"code": "bronze", "routers": 2, "services": 150, "monthly": "500000", "yearly": "5000000"},
    {"code": "silver", "routers": 3, "services": 300, "monthly": "1000000", "yearly": "10000000"},
    {"code": "gold", "routers": 4, "services": 500, "monthly": "1500000", "yearly": "15000000"},
    {"code": "diamond", "routers": 5, "services": 750, "monthly": "2000000", "yearly": "20000000"},
    {"code": "platinum", "routers": None, "services": None, "monthly": "4000000", "yearly": "40000000",
     "routers_opcap": 25, "services_opcap": 5000},
]

RESERVATION_TTL_S = 3600
DRAFT_RATIO = 0.25
DRAFT_MIN = 10
DRAFT_MAX = 500


def seed_plans() -> int:
    """Idempoten: buat PlanVersion per kode bila belum ada."""
    created = 0
    for entry in PLAN_CATALOG:
        if not PlanVersion.objects.filter(code=entry["code"]).exists():
            PlanVersion.objects.create(
                code=entry["code"],
                version=1,
                routers_limit=entry["routers"],
                services_limit=entry["services"],
                routers_opcap=entry.get("routers_opcap"),
                services_opcap=entry.get("services_opcap"),
                monthly_price=Decimal(entry["monthly"]),
                yearly_price=Decimal(entry["yearly"]),
            )
            created += 1
    return created


def ensure_free_subscription(tenant) -> Subscription:
    free = PlanVersion.objects.filter(code=PlanVersion.Code.FREE, active=True).order_by("version").first()
    if free is None:
        free = PlanVersion.objects.create(code=PlanVersion.Code.FREE, monthly_price=0, yearly_price=0)
    sub, _ = Subscription.objects.get_or_create(tenant=tenant, defaults={"plan": free, "state": Subscription.State.FREE})
    return sub


def _limits(sub: Subscription) -> tuple[int | None, int | None]:
    """Batas efektif = lisensi paket; Platinum pakai plafon operasional."""
    plan = sub.plan
    routers = plan.routers_limit if plan.routers_limit is not None else plan.routers_opcap
    services = plan.services_limit if plan.services_limit is not None else plan.services_opcap
    return routers, services


def draft_cap(services_limit: int | None) -> int:
    """min(draft_max, max(draft_min, ceil(draft_ratio*limit))) — defaults.json."""
    if services_limit is None:
        return DRAFT_MAX
    return min(DRAFT_MAX, max(DRAFT_MIN, math.ceil(DRAFT_RATIO * services_limit)))


def _committed(resource: str, tenant_id) -> int:
    from domains.network.models import Router

    if resource == "routers":
        return Router.objects.filter(tenant_id=tenant_id, released_at=None).count()
    # services: committed_counted_accounts (M4) — M1: 0 tercatat jujur.
    return 0


def _reserved(resource: str, tenant_id) -> int:
    # Reservasi tanpa kemajuan kedaluwarsa setelah 60 menit (SUB-02):
    # tandai kedaluwarsa hanya yang MASA BERLAKUNYA TERLEWAT (bukan yang masih aktif).
    QuotaReservation.objects.filter(
        tenant_id=tenant_id,
        resource=resource,
        state=QuotaReservation.State.PENDING,
        expires_at__lte=timezone.now(),
    ).update(state=QuotaReservation.State.EXPIRED, expires_at=timezone.now())
    return QuotaReservation.objects.filter(
        tenant_id=tenant_id, resource=resource, state=QuotaReservation.State.PENDING
    ).count()


def _in_scope(tenant_id) -> bool:
    from domains.common.tenant_context import current_tenant_id

    return current_tenant_id() == str(tenant_id)


@transaction.atomic
def reserve(tenant_id, resource: str, units: int = 1) -> QuotaReservation:
    """Reservasi atomik: gagal bila used+reserved+units > limit (SUB-02).

    Entitlement lock via SELECT FOR UPDATE pada baris subscription.
    """
    if units <= 0:
        raise ValueError("units harus > 0")
    from domains.common.tenant_context import tenant_scope

    if not _in_scope(tenant_id):
        with tenant_scope(tenant_id):
            return reserve(tenant_id, resource, units)
    sub = Subscription.objects.select_for_update().get(tenant=tenant_id)
    routers_limit, services_limit = _limits(sub)
    limit = routers_limit if resource == "routers" else services_limit
    used = _committed(resource, tenant_id) + _reserved(resource, tenant_id)
    if limit is not None and used + units > limit:
        raise ApiError.conflict("quota_exceeded", "error.quota_exceeded")
    return QuotaReservation.objects.create(
        tenant_id=tenant_id,
        resource=resource,
        units=units,
        expires_at=timezone.now() + timezone.timedelta(seconds=RESERVATION_TTL_S),
    )


@transaction.atomic
def commit_reservation(reservation: QuotaReservation) -> None:
    """Konsumsi reservasi dalam transaksi yang sama dengan pembuatan akun."""
    if not _in_scope(reservation.tenant_id):
        from domains.common.tenant_context import tenant_scope

        with tenant_scope(reservation.tenant_id):
            return commit_reservation(reservation)
    QuotaReservation.objects.filter(id=reservation.id, state=QuotaReservation.State.PENDING).update(
        state=QuotaReservation.State.COMMITTED
    )


@transaction.atomic
def release_reservation(reservation: QuotaReservation) -> None:
    if not _in_scope(reservation.tenant_id):
        from domains.common.tenant_context import tenant_scope

        with tenant_scope(reservation.tenant_id):
            return release_reservation(reservation)
    QuotaReservation.objects.filter(id=reservation.id, state=QuotaReservation.State.PENDING).update(
        state=QuotaReservation.State.RELEASED
    )


def usage(tenant_id) -> dict:
    from domains.common.tenant_context import tenant_scope

    if not _in_scope(tenant_id):
        with tenant_scope(tenant_id):
            return usage(tenant_id)
    sub = Subscription.objects.select_related("plan").get(tenant=tenant_id)
    routers_limit, services_limit = _limits(sub)
    return {
        "subscription": sub,
        "routers_used": _committed("routers", tenant_id),
        "services_used": _committed("services", tenant_id),
        "draft_used": 0,
        "draft_cap": draft_cap(services_limit),
    }


@transaction.atomic
def create_quotation(tenant_id, plan_code: str, term: str, locale: str = "id") -> tuple[SaaSInvoice, PlanVersion]:
    """Quotation → invoice SaaS terbit (snapshot nilai/periode/bahasa)."""
    from domains.tenancy.models import Tenant

    if term not in ("monthly", "yearly"):
        raise ApiError.validation({"term": [{"code": "choice", "message": "term harus monthly/yearly"}]})
    from domains.common.tenant_context import tenant_scope

    if not _in_scope(tenant_id):
        with tenant_scope(tenant_id):
            return create_quotation(tenant_id, plan_code, term, locale)
    sub = Subscription.objects.select_for_update().get(tenant=tenant_id)
    plan = PlanVersion.objects.filter(code=plan_code, active=True).order_by("version").first()
    if plan is None or plan.code == PlanVersion.Code.FREE:
        raise ApiError.validation({"plan_code": [{"code": "choice", "message": "Paket tidak tersedia"}]})
    term_months = 1 if term == "monthly" else 12
    amount = plan.monthly_price if term == "monthly" else plan.yearly_price
    tenant = Tenant.objects.get(id=tenant_id)
    now = timezone.now()
    # Periode mulai: akhir periode berjalan bila aktif, else hari ini.
    start = sub.period_end if sub.state == Subscription.State.ACTIVE and sub.period_end else now.date()
    if term == "monthly":
        from datetime import date

        if start.month == 12:
            end = date(start.year + 1, 1, 1)
        else:
            end = date(start.year, start.month + 1, 1)
    else:
        from datetime import date

        end = date(start.year + 1, start.month, start.day)
    invoice = SaaSInvoice.objects.create(
        tenant=tenant,
        plan=plan,
        term_months=term_months,
        amount=amount,
        period_start=start,
        period_end=end,
        locale=locale,
        timezone=tenant.timezone,
        due_at=now + timezone.timedelta(days=3),
    )
    return invoice, plan


# ---------------------------------------------------------------------------
# Alur keputusan platform (M2) — PRODUCT.md PAY-01/PAY-04, FINANCE.md ACC-12
#
# Alur wajib: quotation → invoice → transfer → unggah bukti → verifikasi dana
# → approval → aktivasi (PAY-01). Approval = keputusan uang platform: satu
# transaksi DB (submission + invoice + subscription + audit + outbox) tanpa
# prorata; periode mengikuti snapshot invoice (PAY-04: "Approval ke
# subscription memakai transaksi database + outbox").

DECISION_STATES = (PaymentSubmission.State.SUBMITTED, PaymentSubmission.State.REVIEWING)


def _locate_tenant_of_submission(submission_id: str):
    """Temukan tenant pemilik submission dengan tetap menghormati RLS.

    subs_payment_submission FORCE RLS fail-closed; antrean platform belum
    punya principal RLS tersendiri (keputusan beta M2, lihat laporan slice),
    jadi lokasi dilakukan dengan mengiterasi scope tenant satu per satu.
    """
    from domains.common.tenant_context import tenant_scope
    from domains.tenancy.models import Tenant

    try:
        import uuid as _uuid

        key = _uuid.UUID(str(submission_id))
    except (ValueError, AttributeError, TypeError):
        return None
    for tenant in Tenant.objects.filter(archived_at=None).order_by("created_at").iterator():
        with tenant_scope(tenant.id):
            if PaymentSubmission.objects.filter(id=key).exists():
                return tenant.id
    return None


def list_platform_queue(state: str) -> list[PaymentSubmission]:
    """Antrean submission lintas tenant untuk platform admin (queue=state)."""
    from domains.common.tenant_context import tenant_scope
    from domains.tenancy.models import Tenant

    if state not in PaymentSubmission.State.values:
        raise ApiError.validation(
            {"queue": [{"code": "choice", "message": "queue harus salah satu state submission"}]}
        )
    found: list[PaymentSubmission] = []
    for tenant in Tenant.objects.filter(archived_at=None).order_by("created_at").iterator():
        with tenant_scope(tenant.id):
            found.extend(
                PaymentSubmission.objects.filter(state=state)
                .select_related("tenant", "invoice__plan", "reviewed_by")
                .order_by("-submitted_at")
            )
    found.sort(key=lambda s: s.submitted_at, reverse=True)
    return found


def _apply_decision(
    submission: PaymentSubmission,
    *,
    decision: str,
    actor,
    reason: str = "",
    request_id: str = "",
) -> PaymentSubmission:
    """Terapkan keputusan pada submission terkunci (dipanggil dalam scope)."""
    from domains.audit.models import record
    from domains.jobs.models import OutboxEvent

    if submission.state not in DECISION_STATES:
        # Sudah ada keputusan (approved/rejected/revision_requested) → 409
        # error.conflict — mesin state §7: submitted→reviewing→(terminal).
        raise ApiError.conflict()
    if decision in ("reject", "request_revision") and not reason.strip():
        raise ApiError.validation(
            {"reason": [{"code": "required", "message": "Alasan keputusan wajib diisi"}]}
        )
    now = timezone.now()
    submission.state = (
        PaymentSubmission.State.APPROVED
        if decision == "approve"
        else PaymentSubmission.State.REJECTED
        if decision == "reject"
        else PaymentSubmission.State.REVISION_REQUESTED
    )
    submission.reviewed_at = now
    submission.reviewed_by = actor
    submission.review_note = reason.strip()[:2000]
    submission.save(update_fields=["state", "reviewed_at", "reviewed_by", "review_note"])

    if decision == "approve":
        _activate_for_approval(submission, now=now)

    # Audit redacted + outbox dalam transaksi domain yang sama (§6).
    record(
        tenant_id=submission.tenant_id,
        action_code=f"payment_submission.{decision}",
        actor_display=getattr(actor, "full_name", "") or getattr(actor, "email", "") or "platform",
        actor_id=getattr(actor, "id", None),
        target_type="payment_submission",
        target_id=submission.id,
        target_display=f"Invoice SaaS {submission.invoice_id}",
        payload={"decision": decision, "invoice_id": str(submission.invoice_id), "reason_present": bool(reason)},
        request_id=request_id,
    )
    OutboxEvent.objects.create(
        tenant_id=submission.tenant_id,
        event_type=f"payment_submission.{decision}",
        aggregate_type="payment_submission",
        aggregate_id=submission.id,
        dedup_key=f"payment:{decision}:{submission.id}",
        payload={"invoice_id": str(submission.invoice_id)},
    )
    return submission


def _activate_for_approval(submission: PaymentSubmission, *, now) -> None:
    """Approve → invoice paid + subscription aktif ke paket yang dikutip.

    PAY-01 (aktivasi setelah approval), PAY-04 (atomic), SUB-03 (periode baru
    mulai sesuai snapshot quotation; jangkar = hari mulai periode). Tanpa
    prorata uang. Partial (PAY-04) tidak mengaktifkan: submission M1 selalu
    sebesar nilai invoice penuh.
    """
    from domains.jobs.models import OutboxEvent
    from domains.subscriptions.models import PlatformPaymentSourceEvent

    invoice = submission.invoice
    if invoice.state != SaaSInvoice.State.OPEN:
        # Lunas/void/expired — keputusan ganda atau invoice tidak sah → 409.
        raise ApiError.conflict()
    invoice.state = SaaSInvoice.State.PAID
    invoice.paid_at = now
    invoice.save(update_fields=["state", "paid_at"])

    sub = Subscription.objects.select_for_update().get(tenant_id=submission.tenant_id)
    sub.plan = invoice.plan
    sub.state = Subscription.State.ACTIVE
    sub.period_start = invoice.period_start
    sub.period_end = invoice.period_end
    sub.anchor_day = invoice.period_start.day
    sub.period_index += 1
    sub.save()

    # Event sumber pembayaran platform immutable (TK-003/ACC-12): bahan buku
    # platform R2 tanpa duplikasi — dibuat tepat saat approval (satu Payment).
    PlatformPaymentSourceEvent.objects.create(
        event_type="platform_payment.approved",
        submission=submission,
        tenant_id=submission.tenant_id,
        dedup_key=f"platform_payment:{submission.id}",
        payload={
            "invoice_id": str(invoice.id),
            "amount": f"{invoice.amount:.2f}",
            "term_months": invoice.term_months,
            "plan_code": invoice.plan.code,
        },
    )
    OutboxEvent.objects.create(
        tenant_id=submission.tenant_id,
        event_type="subscription.activated",
        aggregate_type="subscription",
        aggregate_id=sub.id,
        dedup_key=f"subscription:activated:{invoice.id}",
        payload={"plan_code": invoice.plan.code, "period_end": invoice.period_end.isoformat()},
    )


def decide_platform_submission(
    submission_id: str,
    decision: str,
    *,
    actor,
    reason: str = "",
    request_id: str = "",
) -> PaymentSubmission:
    """Titik masuk keputusan platform: approve | reject | request_revision.

    Mengembalikan submission terbaru (dengan relasi invoice/plan) atau
    meningkatkan ApiError: 404 tak ditemukan, 409 keputusan sudah ada /
    invoice tidak lagi open, 422 alasan wajib.
    """
    from domains.common.tenant_context import tenant_scope

    if decision not in ("approve", "reject", "request_revision"):
        raise ValueError(f"Keputusan tidak dikenal: {decision}")
    tenant_id = _locate_tenant_of_submission(submission_id)
    if tenant_id is None:
        raise ApiError.not_found()
    with tenant_scope(tenant_id):
        # reviewed_by sengaja tidak di-select_related: FK nullable + FOR UPDATE
        # tidak boleh menyentuh sisi outer join (PostgreSQL).
        submission = (
            PaymentSubmission.objects.select_for_update()
            .select_related("invoice", "invoice__plan", "tenant")
            .filter(id=submission_id)
            .first()
        )
        if submission is None:
            # Hilang di antara lokasi dan kunci (race) → 404 generik.
            raise ApiError.not_found()
        return _apply_decision(submission, decision=decision, actor=actor, reason=reason, request_id=request_id)
