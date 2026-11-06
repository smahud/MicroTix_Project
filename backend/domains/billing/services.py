"""Layanan billing internet M6 — penerbitan invoice, penerimaan, alokasi.

Kontrak: docs/PRODUCT.md BIL-01/02/03/07/08, GOAL-02 ("sudah bayar" selalu
terkait invoice/periode, tanpa mencampur dimensi), docs/ARCHITECTURE.md §4/§5/§6.

Invarian yang dijaga di sini (diuji pada tests/integration/test_billing_*):
- Satu invoice per (tenant, service, jenis, periode) — UNIQUE DB + scheduler
  lanjutan indeks (AC-BIL: dua scheduler periode sama → satu invoice).
- Harga & kebijakan disnapshot pada invoice + lines: perubahan paket tidak
  mengubah invoice terbit (done_when TK-601).
- Bukti upload ≠ posted payment (BIL-03): submitted → verified (allocation
  dibuat) | rejected; alokasi ≤ nilai payment (sisa = kredit belum
  dialokasikan); alokasi ≤ sisa tagihan per invoice; partial tidak melunasi.
- Pembayaran TIDAK mengubah lifecycle/aktifasi service (PRODUCT §13:
  aktivasi manual terpisah — done_when TK-601 "payment cannot auto-activate").
- Nomor dokumen INV-/RCP- unik per tenant (BIL-01/BIL-08) via kunci baris
  tenant (penomoran terserialisasi per tenant).
- Audit + outbox per kejadian domain (ARCHITECTURE §6).

Semua fungsi pemanggil wajib berjalan dalam tenant_scope(tenant) (RLS aktif).
"""
from __future__ import annotations

import binascii
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone as dj_timezone

from domains.audit.models import record
from domains.billing import calendar
from domains.billing.models import (
    BillingPackage,
    InternetInvoice,
    InternetInvoiceLine,
    InternetPayment,
    PaymentAllocation,
    ServiceCharge,
)
from domains.common.envelope import ApiError
from domains.customers.models import Service
from domains.documents.models import IssuedDocument
from domains.documents.rendering import format_period
from domains.documents.services import issue_document
from domains.jobs.models import OutboxEvent
from domains.tenancy.models import Tenant

# Reuse pipeline bukti TK-106 (magic bytes, batas ukuran) — bukti pembayaran
# internet memakai aturan penyimpanan privat yang sama (BIL-03).
from domains.subscriptions.upload import ALLOWED_MIME, MAX_BYTES, sniff_mime

PAYABLE_STATES = (InternetInvoice.State.OPEN, InternetInvoice.State.PARTIAL)
ZERO = Decimal("0")
TWO = Decimal("0.01")


# ---------------------------------------------------------------------------
# Validasi kebijakan paket (BIL-02)
# ---------------------------------------------------------------------------

def _parse_amount(raw, *, allow_zero: bool = True, field: str = "amount") -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise ApiError.validation({field: [{"code": "invalid", "message": "Nilai tidak sah"}]}) from None
    if value.as_tuple().exponent < -2:
        raise ApiError.validation(
            {field: [{"code": "max_decimal_places", "message": "Maksimal 2 desimal"}]}
        )
    negative = value < ZERO or (not allow_zero and value == ZERO)
    if negative:
        raise ApiError.validation({field: [{"code": "positive", "message": "Nilai harus positif"}]})
    return value.quantize(TWO)


def _validate_package_body(body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name or len(name) > 120:
        raise ApiError.validation({"name": [{"code": "invalid", "message": "Nama paket wajib 1-120 karakter"}]})
    cycle = str(body.get("billing_cycle", BillingPackage.Cycle.FIXED_MONTHLY))
    if cycle not in BillingPackage.Cycle.values:
        raise ApiError.validation({"billing_cycle": [{"code": "invalid", "message": "Siklus tidak dikenal"}]})
    timing = str(body.get("timing", BillingPackage.Timing.PREPAID))
    if timing not in BillingPackage.Timing.values:
        raise ApiError.validation({"timing": [{"code": "invalid", "message": "Waktu penagihan tidak dikenal"}]})
    policy = str(body.get("first_period_policy", BillingPackage.FirstPeriodPolicy.FULL))
    if policy not in BillingPackage.FirstPeriodPolicy.values:
        raise ApiError.validation(
            {"first_period_policy": [{"code": "invalid", "message": "Kebijakan periode pertama tidak dikenal"}]}
        )
    due_day = body.get("due_day")
    if due_day is not None and due_day != "":
        try:
            due_day = int(due_day)
        except (TypeError, ValueError):
            raise ApiError.validation({"due_day": [{"code": "integer", "message": "due_day harus bilangan bulat"}]}) from None
        if not 1 <= due_day <= 31:
            raise ApiError.validation({"due_day": [{"code": "out_of_range", "message": "due_day 1-31"}]})
    else:
        due_day = None
    # BIL-02: due_day hanya berlaku pada fixed_monthly; anniversary dengan
    # kebijakan periode pertama ≠ full ditolak kecuali batas kalender pertama
    # didefinisikan eksplisit pada paket (belum ada → tolak jujur).
    if cycle == BillingPackage.Cycle.ANNIVERSARY:
        if due_day is not None:
            raise ApiError.validation(
                {"due_day": [{"code": "invalid", "message": "due_day hanya berlaku pada fixed_monthly"}]}
            )
        if policy != BillingPackage.FirstPeriodPolicy.FULL:
            raise ApiError.conflict(code="billing.invalid_policy")
    return {
        "name": name,
        "monthly_price": _parse_amount(body.get("monthly_price", 0), field="monthly_price"),
        "billing_cycle": cycle,
        "timing": timing,
        "due_day": due_day,
        "first_period_policy": policy,
    }


def create_package(tenant_id, body: dict, *, actor) -> BillingPackage:
    data = _validate_package_body(body)
    try:
        package = BillingPackage.objects.create(tenant_id=tenant_id, **data)
    except IntegrityError:
        # UNIQUE(tenant, name) — BIL-02 nama paket unik per tenant.
        raise ApiError.conflict() from None
    record(
        tenant_id=tenant_id,
        action_code="billing.package_created",
        actor_display=getattr(actor, "full_name", "") or "",
        actor_id=getattr(actor, "id", None),
        target_type="billing_package",
        target_id=package.id,
        target_display=package.name,
    )
    return package


def update_package(tenant_id, package_id: str, body: dict, *, actor) -> BillingPackage:
    package = BillingPackage.objects.filter(id=package_id, tenant_id=tenant_id).first()
    if package is None:
        raise ApiError.not_found()
    merged = {
        "name": body.get("name", package.name),
        "monthly_price": body.get("monthly_price", package.monthly_price),
        "billing_cycle": body.get("billing_cycle", package.billing_cycle),
        "timing": body.get("timing", package.timing),
        "due_day": body.get("due_day", package.due_day),
        "first_period_policy": body.get("first_period_policy", package.first_period_policy),
    }
    data = _validate_package_body(merged)
    package.name = data["name"]
    package.monthly_price = data["monthly_price"]
    package.billing_cycle = data["billing_cycle"]
    package.timing = data["timing"]
    package.due_day = data["due_day"]
    package.first_period_policy = data["first_period_policy"]
    if "active" in body:
        package.active = bool(body.get("active"))
    try:
        package.save(update_fields=[
            "name", "monthly_price", "billing_cycle", "timing", "due_day",
            "first_period_policy", "active",
        ])
    except IntegrityError:
        raise ApiError.conflict() from None
    record(
        tenant_id=tenant_id,
        action_code="billing.package_updated",
        actor_display=getattr(actor, "full_name", "") or "",
        actor_id=getattr(actor, "id", None),
        target_type="billing_package",
        target_id=package.id,
        target_display=package.name,
    )
    return package


# ---------------------------------------------------------------------------
# Penomoran dokumen (BIL-01/BIL-08) — kunci baris tenant
# ---------------------------------------------------------------------------

def _lock_tenant(tenant_id) -> Tenant:
    """Kunci baris tenant → penomoran dokumen terserialisasi per tenant."""
    tenant = Tenant.objects.select_for_update().filter(id=tenant_id).first()
    if tenant is None:
        raise ApiError.not_found()
    return tenant


def _next_number(tenant: Tenant, prefix: str, today: date, *, kind_count) -> str:
    """{PREFIX}-{namespace}-{YYYYMM}-{urut 4 digit} — unik per tenant & bulan."""
    ym = today.strftime("%Y%m")
    base = f"{prefix}-{tenant.namespace}-{ym}-"
    used = kind_count(base)
    return f"{base}{used + 1:04d}"


def next_invoice_number(tenant_id, today: date) -> str:
    tenant = _lock_tenant(tenant_id)
    return _next_number(
        tenant, "INV", today,
        kind_count=lambda base: InternetInvoice.objects.filter(doc_number__startswith=base).count(),
    )


def next_receipt_number(tenant_id, today: date) -> str:
    tenant = _lock_tenant(tenant_id)
    return _next_number(
        tenant, "RCP", today,
        kind_count=lambda base: IssuedDocument.objects.filter(
            kind=IssuedDocument.Kind.RECEIPT, doc_number__startswith=base
        ).count(),
    )


# ---------------------------------------------------------------------------
# Penerbitan invoice (scheduler; BIL-01/BIL-02/BIL-07)
# ---------------------------------------------------------------------------

def _active_charges(service: Service, period_start: date):
    """Charge aktif pada periode: jendela berlaku dicek terhadap tanggal mulai
    periode (masa berlaku BIL-07)."""
    return ServiceCharge.objects.filter(
        service_id=service.id,
        active=True,
    ).filter(
        valid_from__isnull=True
    ) | ServiceCharge.objects.filter(
        service_id=service.id,
        active=True,
        valid_from__lte=period_start,
    )


def build_lines(
    package: BillingPackage,
    service: Service,
    *,
    period_index: int,
    period_start: date,
    period_end: date,
    locale: str,
) -> tuple[list[dict], Decimal]:
    """Snapshot line invoice (BIL-01/BIL-07) — harga dari paket SAAT INI.

    Line langganan periode pertama mengikuti first_period_policy (BIL-02);
    add_on positif; diskon negatif (pct dari nilai langganan). Total negatif
    = salah konfigurasi → ditolak jujur (bukan dipotong diam-diam).
    """
    if period_index == 0:
        subscription = calendar.first_period_amount(
            package.first_period_policy, package.monthly_price, period_start, period_end
        )
    else:
        subscription = package.monthly_price

    lines: list[dict] = [{
        "line_kind": "subscription",
        "name": f"{package.name} · {format_period(period_start, period_end, locale)}",
        "amount": subscription,
    }]
    charges = (
        ServiceCharge.objects.filter(service_id=service.id, active=True)
        .filter(valid_from__isnull=True)
        | ServiceCharge.objects.filter(service_id=service.id, active=True, valid_from__lte=period_start)
    )
    for charge in charges.distinct().order_by("created_at", "id"):
        if charge.valid_until is not None and charge.valid_until < period_start:
            continue
        if charge.kind == ServiceCharge.Kind.ADD_ON:
            lines.append({"line_kind": "add_on", "name": charge.name, "amount": charge.amount})
        elif charge.kind == ServiceCharge.Kind.DISCOUNT_NOMINAL:
            lines.append({"line_kind": "discount_nominal", "name": charge.name, "amount": -charge.amount})
        else:  # discount_pct — dari nilai langganan (BIL-07 persen diskon)
            lines.append({
                "line_kind": "discount_pct",
                "name": charge.name,
                "amount": -calendar.round_money(subscription * charge.amount / Decimal(100)),
            })
    total = sum((line["amount"] for line in lines), ZERO)
    if total < ZERO:
        raise ApiError.conflict(code="billing.invalid_total")
    return lines, total


def issue_invoice_for_service(
    *,
    tenant: Tenant,
    service: Service,
    today: date,
    actor_display: str = "scheduler",
    request_id: str = "",
) -> list[InternetInvoice]:
    """Terbitkan SEMUA periode terutang layanan ini (lanjutan indeks terakhir).

    Periode yang sudah terbit tidak diulang; UNIQUE(tenant, service, kind,
    period_start, period_end) menjaga AC-BIL bila dua scheduler berlomba
    (IntegrityError → skip periode itu, lanjut berikutnya).
    """
    package = service.billing_package
    if package is None or not package.active:
        return []
    if service.start_date is None:
        return []

    last = (
        InternetInvoice.objects.filter(service_id=service.id, kind=package.timing)
        .aggregate(m=Max("period_index"))
       ["m"]
    )
    last_index = -1 if last is None else last
    indices = calendar.due_period_indices(
        cycle=package.billing_cycle,
        timing=package.timing,
        service_start=service.start_date,
        last_index_issued=last_index,
        today=today,
    )
    issued: list[InternetInvoice] = []
    for index in indices:
        with transaction.atomic():
            try:
                issued.append(
                    _issue_one(
                        tenant=tenant, service=service, package=package,
                        period_index=index, today=today,
                        actor_display=actor_display, request_id=request_id,
                    )
                )
            except IntegrityError:
                # Scheduler ganda berlomba: periode sudah diterbitkan proses
                # lain (AC-BIL) — skip jujur, bukan galat.
                continue
    return issued


def _issue_one(
    *,
    tenant: Tenant,
    service: Service,
    package: BillingPackage,
    period_index: int,
    today: date,
    actor_display: str,
    request_id: str,
) -> InternetInvoice:
    period_start, period_end = calendar.period_bounds(package.billing_cycle, service.start_date, period_index)
    issue_date, due_date = calendar.issue_and_due_dates(
        cycle=package.billing_cycle,
        timing=package.timing,
        due_day=package.due_day,
        period_start=period_start,
        period_end=period_end,
        today=today,
    )
    locale = calendar.effective_locale(service.customer.locale, tenant.locale)
    lines, total = build_lines(
        package, service,
        period_index=period_index, period_start=period_start, period_end=period_end, locale=locale,
    )
    doc_number = next_invoice_number(tenant.id, issue_date)

    invoice = InternetInvoice.objects.create(
        tenant_id=tenant.id,
        service=service,
        kind=package.timing,
        # total 0 (free_until_next_period) → tidak ada tagihan terutang:
        # state paid — invoice tetap terbit sebagai catatan periode.
        state=InternetInvoice.State.PAID if total == ZERO else InternetInvoice.State.OPEN,
        period_index=period_index,
        period_start=period_start,
        period_end=period_end,
        doc_number=doc_number,
        total_amount=total,
        first_period_policy=package.first_period_policy,
        due_date=due_date,
        issued_by=actor_display[:120],
        locale=locale,
        timezone=tenant.timezone,
    )
    InternetInvoiceLine.objects.bulk_create([
        InternetInvoiceLine(
            tenant_id=tenant.id, invoice=invoice, line_kind=line["line_kind"],
            name=line["name"][:160], amount=line["amount"], ordinal=ordinal,
        )
        for ordinal, line in enumerate(lines)
    ])

    # Dokumen PDF invoice terbit + snapshot (TK-109; BIL-01 bahasa terbit).
    issue_document(
        tenant_id=tenant.id,
        kind=IssuedDocument.Kind.INTERNET_INVOICE,
        doc_number=doc_number,
        ref_type="billing_invoice",
        ref_id=str(invoice.id),
        locale=locale,
        timezone_name=tenant.timezone,
        values={
            "tenant_name": tenant.display_name,
            "doc_number": doc_number,
            "issued_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
            "customer_name": service.customer.display_name,
            "service_code": service.service_code,
            "lines": [{"description": line["name"], "amount": f"{line['amount']:.2f}"} for line in lines],
            "total_amount": f"{total:.2f}",
        },
    )

    record(
        tenant_id=tenant.id,
        action_code="internet_invoice.issued",
        actor_display=actor_display,
        target_type="internet_invoice",
        target_id=invoice.id,
        target_display=doc_number,
        payload={
            "period_index": period_index,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "kind": invoice.kind,
            "total": f"{total:.2f}",
        },
        request_id=request_id,
    )
    OutboxEvent.objects.create(
        tenant_id=tenant.id,
        event_type="internet_invoice.issued",
        aggregate_type="internet_invoice",
        aggregate_id=invoice.id,
        dedup_key=f"internet_invoice:{invoice.id}",
        payload={"doc_number": doc_number},
    )
    return invoice


# ---------------------------------------------------------------------------
# Penerimaan pembayaran (BIL-03) — dua tahap: record → verify/reject
# ---------------------------------------------------------------------------

def _store_proof(data: bytes) -> tuple[str, str, int]:
    """Simpan bukti di penyimpanan privat (path opaque 0600, TK-106 pattern)."""
    from django.conf import settings as dj_settings

    mime = sniff_mime(data)
    if mime is None:
        raise ApiError.validation(
            {"file_b64": [{"code": "mime", "message": "Jenis berkas tidak didukung (PNG/JPEG/WebP/PDF)"}]}
        )
    if len(data) > MAX_BYTES:
        raise ApiError.validation(
            {"file_b64": [{"code": "too_large", "message": f"Berkas melebihi {MAX_BYTES} byte"}]}
        )
    storage_path = f"billing-proofs/{uuid.uuid4().hex}"
    target = dj_settings.MT_STORAGE_ROOT / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return storage_path, mime, len(data)


def record_payment(tenant_id, body: dict, *, actor) -> InternetPayment:
    """Catat penerimaan (submitted) — BUKAN posted payment (BIL-03).

    transfer/e-wallet wajib membawa bukti upload; tunai boleh tanpa bukti.
    external_ref (nomor mutasi) unik per tenant bila diisi: event bank yang
    sama tidak bisa direkam dua kali; dua transfer nyata tetap dua Payment.
    """
    method = str(body.get("method", ""))
    if method not in InternetPayment.Method.values:
        raise ApiError.validation({"method": [{"code": "invalid", "message": "Metode tidak dikenal"}]})
    amount = _parse_amount(body.get("amount"), allow_zero=False)
    proof_path, proof_mime, proof_size = "", "", 0
    raw_file = body.get("file_b64")
    if method in (InternetPayment.Method.BANK_TRANSFER, InternetPayment.Method.EWALLET):
        if not raw_file:
            raise ApiError.validation(
                {"file_b64": [{"code": "required", "message": "Bukti transfer/e-wallet wajib diunggah"}]}
            )
    if raw_file:
        if not isinstance(raw_file, str):
            raise ApiError.validation({"file_b64": [{"code": "invalid", "message": "Base64 tidak valid"}]})
        try:
            data = binascii.a2b_base64(raw_file, strict_mode=False)
        except (binascii.Error, ValueError):
            raise ApiError.validation({"file_b64": [{"code": "invalid", "message": "Base64 tidak valid"}]}) from None
        claimed = str(body.get("mime", "")).split(";")[0].strip()
        proof_path, proof_mime, proof_size = _store_proof(data)
        if claimed and claimed not in ALLOWED_MIME:
            # Klaim MIME tidak dikenal — bukti tetap tersimpan per isi sniff,
            # klaim ditolak jujur.
            raise ApiError.validation({"mime": [{"code": "invalid", "message": "MIME klaim tidak didukung"}]})

    external_ref = str(body.get("external_ref", "")).strip()[:128] or None
    collector_display = str(body.get("collector_display", "")).strip()[:120]
    if method != InternetPayment.Method.COLLECTOR_CASH and collector_display:
        raise ApiError.validation(
            {"collector_display": [{"code": "invalid", "message": "Hanya untuk metode collector_cash"}]}
        )
    try:
        payment = InternetPayment.objects.create(
            tenant_id=tenant_id,
            method=method,
            amount=amount,
            external_ref=external_ref,
            proof_path=proof_path,
            proof_mime=proof_mime,
            proof_size=proof_size,
            collector_display=collector_display,
            submitted_by=actor,
        )
    except IntegrityError:
        # external_ref sama untuk tenant → event bank sama direkam ulang (409).
        raise ApiError.conflict() from None
    record(
        tenant_id=tenant_id,
        action_code="internet_payment.recorded",
        actor_display=getattr(actor, "full_name", "") or "",
        actor_id=getattr(actor, "id", None),
        target_type="internet_payment",
        target_id=payment.id,
        target_display=external_ref or method,
        payload={"method": method, "amount": f"{amount:.2f}", "has_proof": bool(proof_path)},
    )
    return payment


def _parse_allocations(raw_allocations, payment: InternetPayment) -> list[tuple[InternetInvoice, Decimal]]:
    """Validasi & gabung alokasi per invoice (duplikat id digabung nilainya).

    Alokasi tidak boleh melebihi nilai payment (kredit = sisa) maupun sisa
    tagihan tiap invoice (BIL-03/AC-BIL).
    """
    if not isinstance(raw_allocations, list):
        raise ApiError.validation({"allocations": [{"code": "required", "message": "Alokasi wajib berupa list"}]})
    merged: dict[str, Decimal] = {}
    for entry in raw_allocations:
        if not isinstance(entry, dict):
            raise ApiError.validation({"allocations": [{"code": "invalid", "message": "Alokasi tidak sah"}]})
        invoice_id = str(entry.get("invoice_id", ""))
        amount = _parse_amount(entry.get("amount"), allow_zero=False)
        merged[invoice_id] = merged.get(invoice_id, ZERO) + amount

    total_alloc = sum(merged.values(), ZERO)
    if total_alloc > payment.amount:
        raise ApiError.conflict(code="billing.allocation_exceeds_payment")

    resolved: list[tuple[InternetInvoice, Decimal]] = []
    for invoice_id, amount in merged.items():
        invoice = InternetInvoice.objects.filter(id=invoice_id, tenant_id=payment.tenant_id).first()
        if invoice is None:
            raise ApiError.not_found()
        if invoice.state not in PAYABLE_STATES:
            raise ApiError.conflict(code="billing.invoice_not_payable")
        outstanding = invoice.total_amount - invoice.paid_amount
        if amount > outstanding:
            raise ApiError.conflict(code="billing.allocation_exceeds_outstanding")
        resolved.append((invoice, amount))
    return resolved


def verify_payment(
    tenant_id,
    payment_id: str,
    body: dict,
    *,
    actor,
    request_id: str = "",
) -> InternetPayment:
    """Verifikasi dana → allocation dibuat + kwitansi terbit (BIL-03/BIL-08).

    Pembayaran TIDAK mengubah lifecycle service — aktivasi manual terpisah
    (PRODUCT §13). Kwitansi bernomor RCP unik; sisa payment = kredit belum
    dialokasikan (tidak dijurnal ulang; M7 TK-701 yang memposting).
    """
    from domains.customers.models import Customer

    payment = (
        InternetPayment.objects.select_for_update()
        .filter(id=payment_id, tenant_id=tenant_id)
        .first()
    )
    if payment is None:
        raise ApiError.not_found()
    if payment.state != InternetPayment.State.SUBMITTED:
        # Keputusan ganda (verified/rejected) → 409 jujur.
        raise ApiError.conflict(code="billing.payment_decided")

    allocations = _parse_allocations(body.get("allocations", []), payment)

    today = dj_timezone.now().date()
    for invoice, amount in allocations:
        invoice.paid_amount += amount
        invoice.state = (
            InternetInvoice.State.PAID
            if invoice.paid_amount == invoice.total_amount
            else InternetInvoice.State.PARTIAL
        )
        invoice.save(update_fields=["paid_amount", "state"])
        PaymentAllocation.objects.create(
            tenant_id=tenant_id, payment=payment, invoice=invoice,
            amount=amount, allocated_by=actor,
        )
    allocated_total = sum((amount for _, amount in allocations), ZERO)
    payment.allocated_amount += allocated_total
    payment.state = InternetPayment.State.VERIFIED
    payment.verified_by = actor
    payment.verified_at = dj_timezone.now()
    payment.save(update_fields=["allocated_amount", "state", "verified_by", "verified_at"])

    # Kwitansi (BIL-08): nomor unik RCP per tenant; bahasa pelanggan invoice
    # pertama (rantai I18N-01); tanpa alokasi → kwitansi kredit penuh.
    first_invoice = allocations[0][0] if allocations else None
    tenant = _lock_tenant(tenant_id)
    locale = "id"
    customer_name = ""
    if first_invoice is not None:
        customer = Customer.objects.filter(id=first_invoice.service.customer_id).first()
        if customer is not None:
            customer_name = customer.display_name
            locale = calendar.effective_locale(customer.locale, tenant.locale)
    receipt_number = next_receipt_number(tenant_id, today)
    issue_document(
        tenant_id=tenant_id,
        kind=IssuedDocument.Kind.RECEIPT,
        doc_number=receipt_number,
        ref_type="billing_payment",
        ref_id=str(payment.id),
        locale=locale,
        timezone_name=tenant.timezone,
        values={
            "tenant_name": tenant.display_name,
            "doc_number": receipt_number,
            "customer_name": customer_name,
            "received_at": today.isoformat(),
            "method": payment.method,
            "applies_to": [
                {"invoice_number": invoice.doc_number, "amount": f"{amount:.2f}"}
                for invoice, amount in allocations
            ],
            "amount": f"{payment.amount:.2f}",
            "credit": f"{payment.credit:.2f}",
        },
    )

    record(
        tenant_id=tenant_id,
        action_code="internet_payment.verified",
        actor_display=getattr(actor, "full_name", "") or "",
        actor_id=getattr(actor, "id", None),
        target_type="internet_payment",
        target_id=payment.id,
        target_display=receipt_number,
        payload={
            "allocated": f"{allocated_total:.2f}",
            "credit": f"{payment.credit:.2f}",
            "receipt_number": receipt_number,
        },
        request_id=request_id,
    )
    OutboxEvent.objects.create(
        tenant_id=tenant_id,
        event_type="internet_payment.verified",
        aggregate_type="internet_payment",
        aggregate_id=payment.id,
        dedup_key=f"internet_payment:verified:{payment.id}",
        payload={"receipt_number": receipt_number, "allocated": f"{allocated_total:.2f}"},
    )
    return payment


def reject_payment(tenant_id, payment_id: str, body: dict, *, actor, request_id: str = "") -> InternetPayment:
    payment = (
        InternetPayment.objects.select_for_update()
        .filter(id=payment_id, tenant_id=tenant_id)
        .first()
    )
    if payment is None:
        raise ApiError.not_found()
    if payment.state != InternetPayment.State.SUBMITTED:
        raise ApiError.conflict(code="billing.payment_decided")
    reason = str(body.get("reason", "")).strip()
    if not reason:
        raise ApiError.validation({"reason": [{"code": "required", "message": "Alasan penolakan wajib"}]})
    payment.state = InternetPayment.State.REJECTED
    payment.rejected_reason = reason[:2000]
    payment.rejected_at = dj_timezone.now()
    payment.save(update_fields=["state", "rejected_reason", "rejected_at"])
    record(
        tenant_id=tenant_id,
        action_code="internet_payment.rejected",
        actor_display=getattr(actor, "full_name", "") or "",
        actor_id=getattr(actor, "id", None),
        target_type="internet_payment",
        target_id=payment.id,
        target_display=payment.external_ref or payment.method,
        payload={"reason_present": True},
        request_id=request_id,
    )
    return payment


# ---------------------------------------------------------------------------
# Aging (BIL-05/ACC-04 bucket terhadap due) & laporan ringkas
# ---------------------------------------------------------------------------

AGING_BUCKETS = (("current", 0, 30), ("d31_60", 31, 60), ("d61_90", 61, 90), ("d90_plus", 91, None))


def aging_report(tenant_id, as_of: date) -> dict:
    """Aging invoice open/partial terhadap due_date (FINANCE.md §5 bucket).

    Invoice belum jatuh tempo masuk bucket "not_due" — dipisah dari piutang
    telat (prabayar memorandum vs piutang recognized dibedakan M7 TK-703
    saat tie-out; laporan ini level invoice).
    """
    rows = []
    totals: dict[str, dict] = {"not_due": {"count": 0, "outstanding": ZERO}}
    for key, _lo, _hi in AGING_BUCKETS:
        totals[key] = {"count": 0, "outstanding": ZERO}
    for invoice in (
        InternetInvoice.objects.filter(tenant_id=tenant_id, state__in=PAYABLE_STATES)
        .select_related("service", "service__customer")
        .order_by("due_date", "id")
    ):
        days_over = (as_of - invoice.due_date).days
        if days_over < 0:
            bucket = "not_due"
        elif days_over <= 30:
            bucket = "current"
        elif days_over <= 60:
            bucket = "d31_60"
        elif days_over <= 90:
            bucket = "d61_90"
        else:
            bucket = "d90_plus"
        outstanding = invoice.outstanding
        totals[bucket]["count"] += 1
        totals[bucket]["outstanding"] += outstanding
        rows.append({
            "invoice_id": str(invoice.id),
            "doc_number": invoice.doc_number,
            "service_code": invoice.service.service_code,
            "customer_name": invoice.service.customer.display_name,
            "due_date": invoice.due_date.isoformat(),
            "days_overdue": max(days_over, 0) if days_over >= 0 else 0,
            "overdue": days_over > 0,
            "bucket": bucket,
            "outstanding": f"{outstanding:.2f}",
        })
    return {
        "as_of": as_of.isoformat(),
        "totals": {k: {"count": v["count"], "outstanding": f"{v['outstanding']:.2f}"} for k, v in totals.items()},
        "items": rows,
    }
