"""API pekerjaan — U16 job center.

GET  /tenants/{t}/jobs        → CursorPage<JobRecord> (customers.read)
GET  /jobs/{id}               → JobRecord (izin resource yang mendasari)
POST /jobs/{id}/retry         → 202 JobAccepted baru (job asal terminal retryable)
POST /jobs/{id}/cancel        → 204; menolak bila efek mungkin sudah terjadi

PA-003 / A07: detail/retry/cancel memakai izin operasi yang mendasari job
(metadata enqueue atau fallback kind) — anggota tenant tanpa izin → 403;
resource di luar scope aktif → 404 generik. Mutasi job kind sensitif
(mis. radius.cutover) memerlukan step-up reauth yang berlaku.
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
from domains.tenancy.permissions import ROLE_PERMISSIONS, is_sensitive


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


def _require_job_authority(view: ActiveTenantApiView, request: Request, job: Job) -> None:
    """Izin operasi + membership router scope untuk aksi HTTP (A07).

    - Job di luar tenant sesi aktif → 404 generik (jangan bocorkan).
    - Router job di luar membership.router_scope → 404 generik (REV-1711-06:
      endpoint job menghormati scope membership; nol perubahan state/job).
    - Anggota tanpa izin operasi (in-scope) → 403.
    - Aksi mutasi pada kind sensitif → step-up reauth (ARCHITECTURE §3).
    """
    if not view.in_scope(job.tenant_id):
        raise ApiError.not_found()
    membership = request.mt_membership
    if job.router_id is not None and membership.router_scope is not None:
        scope = membership.router_scope
        allowed = {
            str(r) for r in (scope if isinstance(scope, (list, tuple)) else [scope])
        }
        if str(job.router_id) not in allowed:
            raise ApiError.not_found()
    requirement = engine.authority_requirement(job)
    if requirement is None:
        return
    perms = ROLE_PERMISSIONS.get(request.mt_membership.role, frozenset())
    needed = (requirement,) if isinstance(requirement, str) else tuple(requirement)
    if not any(p in perms for p in needed):
        raise ApiError.forbidden()
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and any(is_sensitive(p) for p in needed):
        from domains.identity.services import require_reauth as _require_reauth

        _require_reauth(request)


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
        if job is None:
            raise ApiError.not_found()
        _require_job_authority(self, request, job)
        return Response(job_record(job))


class JobRetryView(ActiveTenantApiView):
    @extend_schema(summary="Retry job terminal retryable → job baru")
    def post(self, request: Request, job_id: str) -> Response:
        job = Job.objects.filter(id=job_id).first()
        if job is None:
            raise ApiError.not_found()
        _require_job_authority(self, request, job)
        # uncertain TIDAK retry-able langsung: unknown outcome wajib lewat
        # resolve/readback (ops) — retry tidak boleh membuka efek baru (A04).
        if job.state not in ("failed", "cancelled") or not job.retryable:
            raise ApiError.conflict("conflict", "job.not_retryable")
        try:
            new_job = engine.retry_job(job, actor=request.user)
        except ValueError as exc:
            if "retry_active_exists" in str(exc):
                # Kandidat aktif untuk origin sama sudah ada → bukan efek ganda.
                raise ApiError.conflict("conflict", "job.retry_active_exists") from None
            raise ApiError.conflict("conflict", "job.not_retryable") from None
        return Response(
            {"job_id": str(new_job.id), "status_url": f"/api/v1/jobs/{new_job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


class JobCancelView(ActiveTenantApiView):
    @extend_schema(summary="Batalkan job (hanya nol efek terbukti)")
    def post(self, request: Request, job_id: str) -> Response:
        job = Job.objects.filter(id=job_id).first()
        if job is None:
            raise ApiError.not_found()
        _require_job_authority(self, request, job)
        reason = ""
        data = request.data
        if isinstance(data, dict):
            reason = str(data.get("reason", ""))[:500]
        try:
            engine.cancel_job(job, reason or "Dibatalkan operator")
        except ValueError:
            raise ApiError.conflict("conflict", "job.not_cancellable") from None
        return Response(status=status.HTTP_204_NO_CONTENT)
