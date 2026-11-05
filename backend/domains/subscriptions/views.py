"""API subscription — GET /subscription, /plans, POST quotations, submissions."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.views import TenantApiView
from domains.subscriptions import services
from domains.subscriptions.models import PaymentSubmission, PlanVersion, SaaSInvoice


def plan_info(plan: PlanVersion) -> dict:
    return {
        "code": plan.code,
        "routers_limit": plan.routers_limit if plan.routers_limit is not None else None,
        "services_limit": plan.services_limit if plan.services_limit is not None else None,
        "monthly_price": f"{plan.monthly_price:.2f}",
        "yearly_price": f"{plan.yearly_price:.2f}",
    }


def subscription_info(data: dict) -> dict:
    sub = data["subscription"]
    pending = (
        SaaSInvoice.objects.filter(tenant_id=sub.tenant_id, state=SaaSInvoice.State.OPEN)
        .order_by("-created_at")
        .first()
    )
    return {
        "plan": plan_info(sub.plan),
        "state": sub.state,
        "period_start": sub.period_start.isoformat() if sub.period_start else None,
        "period_end": sub.period_end.isoformat() if sub.period_end else None,
        "usage": {
            "routers_used": data["routers_used"],
            "services_used": data["services_used"],
            "draft_used": data["draft_used"],
            "draft_cap": data["draft_cap"],
        },
        "pending_invoice": (
            {"id": str(pending.id), "amount": f"{pending.amount:.2f}", "due_at": pending.due_at.isoformat()}
            if pending
            else None
        ),
    }


class SubscriptionView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Subscription dan kuota tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        return Response(subscription_info(services.usage(tenant_id)))


class PlansView(APIView):
    """Katalog paket global — autentikasi saja, tidak ter-scope tenant."""

    @extend_schema(summary="Daftar paket aktif")
    def get(self, request: Request) -> Response:
        plans = PlanVersion.objects.filter(active=True).order_by("created_at")
        return Response([plan_info(p) for p in plans])


class QuotationView(TenantApiView):
    required_permission = "subscription.manage"
    sensitive = True

    @idempotent("quotation")
    @extend_schema(summary="Ajukan quotation paket → invoice SaaS")
    def post(self, request: Request, tenant_id: str) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        invoice, plan = services.create_quotation(
            tenant_id,
            str(body.get("plan_code", "")),
            str(body.get("term", "")),
            locale=getattr(request, "mt_locale", "id"),
        )
        return Response(
            {
                "quotation_id": str(invoice.id),
                "invoice_id": str(invoice.id),
                "amount": f"{invoice.amount:.2f}",
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentSubmissionView(TenantApiView):
    required_permission = "subscription.manage"
    sensitive = True

    @idempotent("payment_submission")
    @extend_schema(summary="Ajukan bukti pembayaran invoice SaaS")
    def post(self, request: Request, tenant_id: str, invoice_id: str) -> Response:
        invoice = SaaSInvoice.objects.filter(id=invoice_id, tenant_id=tenant_id).first()
        if invoice is None:
            raise ApiError.not_found()
        body = request.data if isinstance(request.data, dict) else {}
        from domains.subscriptions.upload import store_payment_proof

        proof = store_payment_proof(request, tenant_id, invoice, body)
        submission = PaymentSubmission.objects.create(
            tenant_id=tenant_id,
            invoice=invoice,
            amount=invoice.amount,
            proof_path=proof["path"],
            proof_mime=proof["mime"],
            proof_size=proof["size"],
            submitted_by=request.user,
        )
        return Response(
            {"submission_id": str(submission.id), "state": submission.state},
            status=status.HTTP_201_CREATED,
        )
