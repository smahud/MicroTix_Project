"""API pekerjaan — U16 job center.

GET  /tenants/{t}/jobs        → CursorPage<JobRecord> (customers.read)
GET  /jobs/{id}               → JobRecord (izin resource dasar)
POST /jobs/{id}/retry         → 202 JobAccepted baru (job asal terminal retryable)
POST /jobs/{id}/cancel        → 204; menolak bila efek mungkin sudah terjadi
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.common.pagination import decode_cursor, encode_cursor, page_response, parse_limit
from domains.common.views import ActiveTenantApiView, TenantApiView
from domains.jobs import engine
from domains.jobs.models import Job


def job_record(job: Job) -> dict:
    """Bentuk JobRecord kontrak frontend (contracts.ts)."""
    return {
        "id": str(job.id),
        "kind": job.kind,
        "state": job.state,
        "actor_display": job.actor_display,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "router_id": str(job.router_id) if job.router_id else None,
        "phase_label_code": job.phase_label_code,
        "items_total": job.items_total,
        "items_done": job.items_done,
        "error_code": job.error_code,
        "request_id": job.request_id,
        "retryable": job.retryable,
    }


class JobListView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Daftar pekerjaan tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        limit = parse_limit(request.query_params.get("limit"))
        cursor = request.query_params.get("cursor")
        qs = Job.objects.filter(tenant_id=tenant_id).order_by("-created_at", "-id")
        if cursor:
            sort_key, last_id = decode_cursor(cursor)
            qs = qs.filter(created_at__lt=sort_key) | qs.filter(created_at=sort_key, id__lt=last_id)
        jobs = list(qs[: limit + 1])
        next_cursor = None
        if len(jobs) > limit:
            jobs = jobs[:limit]
            last = jobs[-1]
            next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))
        return Response(page_response([job_record(j) for j in jobs], next_cursor))


class JobDetailView(ActiveTenantApiView):
    @extend_schema(summary="Detail pekerjaan")
    def get(self, request: Request, job_id: str) -> Response:
        job = Job.objects.filter(id=job_id).first()
        if job is None or not self.in_scope(job.tenant_id):
            raise ApiError.not_found()
        return Response(job_record(job))


class JobRetryView(ActiveTenantApiView):
    def post(self, request: Request, job_id: str) -> Response:
        job = Job.objects.filter(id=job_id).first()
        if job is None or not self.in_scope(job.tenant_id):
            raise ApiError.not_found()
        if job.state not in ("failed", "cancelled", "uncertain") or not job.retryable:
            raise ApiError.conflict("conflict", "job.not_retryable")
        new_job = engine.retry_job(job, actor=request.user)
        return Response(
            {"job_id": str(new_job.id), "status_url": f"/api/v1/jobs/{new_job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


class JobCancelView(ActiveTenantApiView):
    def post(self, request: Request, job_id: str) -> Response:
        job = Job.objects.filter(id=job_id).first()
        if job is None or not self.in_scope(job.tenant_id):
            raise ApiError.not_found()
        reason = ""
        data = request.data
        if isinstance(data, dict):
            reason = str(data.get("reason", ""))[:500]
        try:
            engine.cancel_job(job, reason or "Dibatalkan operator")
        except ValueError:
            raise ApiError.conflict("conflict", "job.not_cancellable") from None
        return Response(status=status.HTTP_204_NO_CONTENT)
