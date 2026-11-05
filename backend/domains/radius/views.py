"""API RADIUS — status per router + cutover (U19; RADIUS.md §10.2)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.views import TenantApiView
from domains.jobs import engine
from domains.network.models import Router
from domains.radius import services


def _router_or_404(tenant_id: str, router_id: str) -> Router:
    router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
    if router is None:
        raise ApiError.not_found()
    return router


class RadiusStatusListView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Status RADIUS seluruh router tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        return Response(services.radius_status_for_tenant(tenant_id))


class RadiusStatusDetailView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Status RADIUS satu router")
    def get(self, request: Request, tenant_id: str, router_id: str) -> Response:
        data = services.radius_status_detail(tenant_id, router_id)
        if data is None:
            raise ApiError.not_found()
        return Response(data)


class RadiusCutoverView(TenantApiView):
    """Mulai/lanjutkan cutover B0–B6 (sensitif: radius.cutover + reauth)."""

    required_permission = "radius.cutover"

    @idempotent("radius_cutover", resource_from=lambda request, kwargs: str(kwargs.get("router_id", "")))
    @extend_schema(summary="Mulai/lanjutkan cutover RADIUS per router (B0–B6)")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = _router_or_404(tenant_id, router_id)
        job = engine.create_job(
            tenant_id=tenant_id,
            kind="radius_cutover_step",
            actor=request.user,
            router=router,
            payload={"router_id": str(router.id)},
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )
