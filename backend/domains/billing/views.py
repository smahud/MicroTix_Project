"""API billing internet M6 (TK-601) — BIL-01/02/03/07.

Endpoint (U09 U10 mengonsumsi fase UI TK-604; slice ini backend):
GET  /tenants/{t}/billing/packages                → daftar paket (services.provision)
POST /tenants/{t}/billing/packages                → buat paket (services.provision, Idempotency-Key)
PUT  /tenants/{t}/billing/packages/{id}            → ubah/nonaktifkan (services.provision, Idempotency-Key)
POST /tenants/{t}/services/{s}/billing-package     → pasang paket ke layanan (services.provision, Idempotency-Key)
GET  /tenants/{t}/services/{s}/charges            → add-on/diskon layanan (customers.read)
POST /tenants/{t}/services/{s}/charges            → tambah charge (services.provision, Idempotency-Key)
PUT  /tenants/{t}/charges/{id}                     → ubah/nonaktifkan charge (services.provision)
GET  /tenants/{t}/invoices                         → daftar invoice + filter (customers.read)
GET  /tenants/{t}/invoices/{id}                   → detail + lines + dokumen (customers.read)
GET  /tenants/{t}/invoices/aging                   → bucket aging (customers.read)
POST /tenants/{t}/payments                         → catat penerimaan submitted (payments.verify, Idempotency-Key)
POST /tenants/{t}/payments/{id}/verify             → verifikasi dana + alokasi (payments.verify, Idempotency-Key)
POST /tenants/{t}/payments/{id}/reject             → tolak dengan alasan (payments.verify, Idempotency-Key)
GET  /tenants/{t}/payments                         → daftar pembayaran (customers.read)
GET  /tenants/{t}/payments/{id}                    → detail + alokasi (customers.read)
"""
from __future__ import annotations

import uuid

from django.utils import timezone as dj_timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from domains.billing import services
from domains.billing.models import BillingPackage, InternetInvoice, InternetPayment, ServiceCharge
from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.pagination import encode_cursor, page_response, parse_limit
from domains.common.views import TenantApiView
from domains.customers.models import Service
from domains.documents.models import IssuedDocument


def _body(request: Request) -> dict:
    return request.data if isinstance(request.data, dict) else {}


def _parse_uuid(raw: str, field: str) -> str:
    try:
        return str(uuid.UUID(str(raw)))
    except (ValueError, TypeError, AttributeError):
        raise ApiError.validation({field: [{"code": "invalid", "message": "ID tidak valid"}]}) from None


def package_info(package) -> dict:
    return {
        "id": str(package.id),
        "name": package.name,
        "monthly_price": f"{package.monthly_price:.2f}",
        "billing_cycle": package.billing_cycle,
        "timing": package.timing,
        "due_day": package.due_day,
        "first_period_policy": package.first_period_policy,
        "active": package.active,
        "created_at": package.created_at.isoformat(),
    }


def charge_info(charge) -> dict:
    return {
        "id": str(charge.id),
        "service_id": str(charge.service_id),
        "kind": charge.kind,
        "name": charge.name,
        "amount": f"{charge.amount:.2f}",
        "valid_from": charge.valid_from.isoformat() if charge.valid_from else None,
        "valid_until": charge.valid_until.isoformat() if charge.valid_until else None,
        "active": charge.active,
    }


def invoice_info(invoice, *, lines=None) -> dict:
    document = (
        IssuedDocument.objects.filter(
            tenant_id=invoice.tenant_id,
            kind=IssuedDocument.Kind.INTERNET_INVOICE,
            ref_type="billing_invoice",
            ref_id=str(invoice.id),
        ).first()
    )
    data = {
        "id": str(invoice.id),
        "doc_number": invoice.doc_number,
        "service_id": str(invoice.service_id),
        "service_code": invoice.service.service_code,
        "customer_name": invoice.service.customer.display_name,
        "kind": invoice.kind,
        "state": invoice.state,
        "period_index": invoice.period_index,
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "issued_at": invoice.issued_at.isoformat(),
        "total_amount": f"{invoice.total_amount:.2f}",
        "paid_amount": f"{invoice.paid_amount:.2f}",
        "outstanding": f"{invoice.outstanding:.2f}",
        "first_period_policy": invoice.first_period_policy,
        "locale": invoice.locale,
        "timezone": invoice.timezone,
        "document_id": str(document.id) if document else None,
    }
    if lines is not None:
        data["lines"] = [
            {
                "line_kind": line.line_kind,
                "name": line.name,
                "amount": f"{line.amount:.2f}",
                "ordinal": line.ordinal,
            }
            for line in lines
        ]
    return data


def payment_info(payment, *, allocations=None) -> dict:
    data = {
        "id": str(payment.id),
        "method": payment.method,
        "state": payment.state,
        "amount": f"{payment.amount:.2f}",
        "allocated_amount": f"{payment.allocated_amount:.2f}",
        "credit": f"{payment.credit:.2f}",
        "external_ref": payment.external_ref,
        "has_proof": bool(payment.proof_path),
        "collector_display": payment.collector_display,
        "submitted_at": payment.submitted_at.isoformat(),
        "verified_at": payment.verified_at.isoformat() if payment.verified_at else None,
        "rejected_reason": payment.rejected_reason,
    }
    if allocations is not None:
        data["allocations"] = [
            {
                "invoice_id": str(alloc.invoice_id),
                "invoice_number": alloc.invoice.doc_number,
                "amount": f"{alloc.amount:.2f}",
                "allocated_at": alloc.allocated_at.isoformat(),
            }
            for alloc in allocations
        ]
    return data


def _paginate(request, qs):
    """Paginasi kursor untuk urutan (-issued_at, -id)."""
    limit = parse_limit(request.query_params.get("limit"))
    items = list(qs[: limit + 1])
    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        last = items[-1]
        next_cursor = encode_cursor(last.issued_at.isoformat(), str(last.id))
    return items, next_cursor


class BillingPackageListView(TenantApiView):
    """Daftar & buat paket penagihan (BIL-02). Izin per metode (§5)."""

    def get_permissions(self):
        self.required_permission = (
            "customers.read" if self.request.method in ("GET", "HEAD", "OPTIONS") else "services.provision"
        )
        return super().get_permissions()

    @extend_schema(summary="Daftar paket penagihan tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        packages = BillingPackage.objects.filter(tenant_id=tenant_id).order_by("created_at", "id")
        return Response([package_info(p) for p in packages])

    @idempotent("billing_package_create")
    @extend_schema(summary="Buat paket penagihan (BIL-02)")
    def post(self, request: Request, tenant_id: str) -> Response:
        package = services.create_package(tenant_id, _body(request), actor=request.user)
        return Response(package_info(package), status=status.HTTP_201_CREATED)


class BillingPackageDetailView(TenantApiView):
    required_permission = "services.provision"

    @idempotent("billing_package_update", resource_from=lambda request, kwargs: kwargs.get("package_id", ""))
    @extend_schema(summary="Ubah/nonaktifkan paket penagihan")
    def put(self, request: Request, tenant_id: str, package_id: str) -> Response:
        package = services.update_package(tenant_id, _parse_uuid(package_id, "package_id"), _body(request), actor=request.user)
        return Response(package_info(package))


class ServiceBillingPackageView(TenantApiView):
    """Pasang/lepas paket penagihan pada layanan (provisioning)."""

    required_permission = "services.provision"

    @idempotent("service_billing_package", resource_from=lambda request, kwargs: kwargs.get("service_id", ""))
    @extend_schema(summary="Pasang paket penagihan ke layanan")
    def post(self, request: Request, tenant_id: str, service_id: str) -> Response:
        from domains.billing.models import BillingPackage

        service = Service.objects.filter(id=_parse_uuid(service_id, "service_id"), tenant_id=tenant_id).first()
        if service is None:
            raise ApiError.not_found()
        body = _body(request)
        if "package_id" in body and body["package_id"]:
            package = BillingPackage.objects.filter(id=_parse_uuid(body["package_id"], "package_id"), tenant_id=tenant_id).first()
            if package is None:
                raise ApiError.not_found()
            service.billing_package = package
        else:
            service.billing_package = None
        service.save(update_fields=["billing_package"])
        return Response({"service_id": str(service.id), "billing_package_id": str(service.billing_package_id)})


class ServiceChargeListView(TenantApiView):
    """Add-on/diskon per layanan (BIL-07)."""

    def get_permissions(self):
        self.required_permission = (
            "customers.read" if self.request.method in ("GET", "HEAD", "OPTIONS") else "services.provision"
        )
        return super().get_permissions()

    @extend_schema(summary="Daftar add-on/diskon layanan")
    def get(self, request: Request, tenant_id: str, service_id: str) -> Response:
        service = Service.objects.filter(id=_parse_uuid(service_id, "service_id"), tenant_id=tenant_id).first()
        if service is None:
            raise ApiError.not_found()
        charges = ServiceCharge.objects.filter(service_id=service.id).order_by("created_at", "id")
        return Response([charge_info(c) for c in charges])

    @idempotent("service_charge_create", resource_from=lambda request, kwargs: kwargs.get("service_id", ""))
    @extend_schema(summary="Tambah add-on/diskon berulang ke layanan")
    def post(self, request: Request, tenant_id: str, service_id: str) -> Response:
        service = Service.objects.filter(id=_parse_uuid(service_id, "service_id"), tenant_id=tenant_id).first()
        if service is None:
            raise ApiError.not_found()
        body = _body(request)
        kind = str(body.get("kind", ""))
        if kind not in ServiceCharge.Kind.values:
            raise ApiError.validation({"kind": [{"code": "invalid", "message": "Jenis charge tidak dikenal"}]})
        amount = services._parse_amount(body.get("amount", 0), allow_zero=True)
        if kind == ServiceCharge.Kind.DISCOUNT_PCT and amount > 100:
            raise ApiError.validation({"amount": [{"code": "out_of_range", "message": "Persen diskon maksimal 100"}]})
        charge = ServiceCharge.objects.create(
            tenant_id=tenant_id,
            service=service,
            kind=kind,
            name=str(body.get("name", "")).strip()[:120] or "charge",
            amount=amount,
            valid_from=body.get("valid_from") or None,
            valid_until=body.get("valid_until") or None,
            active=True,
        )
        return Response(charge_info(charge), status=status.HTTP_201_CREATED)


class ServiceChargeDetailView(TenantApiView):
    required_permission = "services.provision"

    @idempotent("service_charge_update", resource_from=lambda request, kwargs: kwargs.get("charge_id", ""))
    @extend_schema(summary="Ubah/nonaktifkan add-on/diskon")
    def put(self, request: Request, tenant_id: str, charge_id: str) -> Response:
        charge = ServiceCharge.objects.filter(id=_parse_uuid(charge_id, "charge_id"), tenant_id=tenant_id).first()
        if charge is None:
            raise ApiError.not_found()
        body = _body(request)
        if "active" in body:
            charge.active = bool(body.get("active"))
        if "amount" in body:
            charge.amount = services._parse_amount(body.get("amount"), allow_zero=True)
        if "valid_until" in body:
            charge.valid_until = body.get("valid_until") or None
        charge.save(update_fields=["active", "amount", "valid_until"])
        return Response(charge_info(charge))


class InternetInvoiceListView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Daftar invoice internet (filter periode/state/service)")
    def get(self, request: Request, tenant_id: str) -> Response:
        params = request.query_params
        qs = (
            InternetInvoice.objects.filter(tenant_id=tenant_id)
            .select_related("service", "service__customer")
            .order_by("-issued_at", "-id")
        )
        state = params.get("state")
        if state:
            if state not in InternetInvoice.State.values:
                raise ApiError.validation({"state": [{"code": "invalid", "message": "State tidak dikenal"}]})
            qs = qs.filter(state=state)
        kind = params.get("kind")
        if kind:
            if kind not in InternetInvoice.Kind.values:
                raise ApiError.validation({"kind": [{"code": "invalid", "message": "Jenis tidak dikenal"}]})
            qs = qs.filter(kind=kind)
        service_id = params.get("service_id")
        if service_id:
            qs = qs.filter(service_id=_parse_uuid(service_id, "service_id"))
        period_from = params.get("period_from")
        if period_from:
            qs = qs.filter(period_start__gte=period_from)
        period_to = params.get("period_to")
        if period_to:
            qs = qs.filter(period_end__lte=period_to)
        invoices, next_cursor = _paginate(request, qs)
        return Response(page_response([invoice_info(inv) for inv in invoices], next_cursor))


class InternetInvoiceDetailView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Detail invoice + line item")
    def get(self, request: Request, tenant_id: str, invoice_id: str) -> Response:
        invoice = (
            InternetInvoice.objects.filter(id=_parse_uuid(invoice_id, "invoice_id"), tenant_id=tenant_id)
            .select_related("service", "service__customer")
            .first()
        )
        if invoice is None:
            raise ApiError.not_found()
        lines = invoice.lines.order_by("ordinal")
        return Response(invoice_info(invoice, lines=lines))


class InternetInvoiceAgingView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Aging piutang vs due (bucket 0-30/31-60/61-90/>90)")
    def get(self, request: Request, tenant_id: str) -> Response:
        raw = request.query_params.get("as_of")
        as_of = dj_timezone.now().date()
        if raw:
            try:
                from datetime import date as _date

                as_of = _date.fromisoformat(raw)
            except ValueError:
                raise ApiError.validation({"as_of": [{"code": "invalid", "message": "Format YYYY-MM-DD"}]}) from None
        return Response(services.aging_report(tenant_id, as_of))


class InternetPaymentCollectionView(TenantApiView):
    """GET /payments (customers.read) + POST /payments (payments.verify).

    BIL-03: catat penerimaan submitted — bukti upload ≠ posted payment;
    izin perekaman/verifikasi dana = payments.verify (Admin Pembayaran).
    """

    def get_permissions(self):
        self.required_permission = (
            "customers.read" if self.request.method in ("GET", "HEAD", "OPTIONS") else "payments.verify"
        )
        return super().get_permissions()

    @extend_schema(summary="Daftar penerimaan pembayaran internet")
    def get(self, request: Request, tenant_id: str) -> Response:
        params = request.query_params
        qs = InternetPayment.objects.filter(tenant_id=tenant_id).order_by("-submitted_at", "-id")
        state = params.get("state")
        if state:
            if state not in InternetPayment.State.values:
                raise ApiError.validation({"state": [{"code": "invalid", "message": "State tidak dikenal"}]})
            qs = qs.filter(state=state)
        method = params.get("method")
        if method:
            if method not in InternetPayment.Method.values:
                raise ApiError.validation({"method": [{"code": "invalid", "message": "Metode tidak dikenal"}]})
            qs = qs.filter(method=method)
        limit = parse_limit(params.get("limit"))
        items = list(qs[: limit + 1])
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            last = items[-1]
            next_cursor = encode_cursor(last.submitted_at.isoformat(), str(last.id))
        return Response(page_response([payment_info(p) for p in items], next_cursor))

    @idempotent("internet_payment_record")
    @extend_schema(summary="Catat penerimaan (submitted; transfer/e-wallet wajib bukti)")
    def post(self, request: Request, tenant_id: str) -> Response:
        payment = services.record_payment(tenant_id, _body(request), actor=request.user)
        return Response(payment_info(payment), status=status.HTTP_201_CREATED)


class InternetPaymentDetailView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Detail pembayaran + alokasinya")
    def get(self, request: Request, tenant_id: str, payment_id: str) -> Response:
        payment = InternetPayment.objects.filter(id=_parse_uuid(payment_id, "payment_id"), tenant_id=tenant_id).first()
        if payment is None:
            raise ApiError.not_found()
        allocations = payment.allocations.select_related("invoice").order_by("allocated_at", "id")
        return Response(payment_info(payment, allocations=allocations))


class InternetPaymentVerifyView(TenantApiView):
    """Verifikasi dana → alokasi + kwitansi (BIL-03/BIL-08)."""

    required_permission = "payments.verify"

    @idempotent(
        "internet_payment_verify",
        resource_from=lambda request, kwargs: str(kwargs.get("payment_id", "")),
    )
    @extend_schema(summary="Verifikasi dana: allocation ke invoice(s) + kwitansi")
    def post(self, request: Request, tenant_id: str, payment_id: str) -> Response:
        payment = services.verify_payment(
            tenant_id, _parse_uuid(payment_id, "payment_id"), _body(request),
            actor=request.user, request_id=getattr(request, "mt_request_id", ""),
        )
        allocations = payment.allocations.select_related("invoice").order_by("allocated_at", "id")
        return Response(payment_info(payment, allocations=allocations))


class InternetPaymentRejectView(TenantApiView):
    required_permission = "payments.verify"

    @idempotent(
        "internet_payment_reject",
        resource_from=lambda request, kwargs: str(kwargs.get("payment_id", "")),
    )
    @extend_schema(summary="Tolak penerimaan dengan alasan (dokumen koreksi disusul)")
    def post(self, request: Request, tenant_id: str, payment_id: str) -> Response:
        payment = services.reject_payment(
            tenant_id, _parse_uuid(payment_id, "payment_id"), _body(request),
            actor=request.user, request_id=getattr(request, "mt_request_id", ""),
        )
        return Response(payment_info(payment))
