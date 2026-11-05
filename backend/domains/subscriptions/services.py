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
