"""API registri router + enrollment + discovery + release/replace (M3)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.views import TenantApiView
from domains.jobs import engine
from domains.network import services
from domains.network.models import Router, RouterEnrollment


def _validate_uuid(field: str, value: str):
    import uuid as uuid_mod

    try:
        return str(uuid_mod.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ApiError.validation({field: [{"code": "invalid", "message": "ID tidak valid"}]}) from None


def router_summary(router: Router, *, services_count: int | None = None) -> dict:
    latest = router.health_samples.order_by("-observed_at").first()
    health = {
        "vpn": (None if latest is None or latest.vpn_up is None else ("up" if latest.vpn_up else "down")),
        "api": (None if latest is None or latest.api_up is None else ("up" if latest.api_up else "down")),
        "observed_at": latest.observed_at.isoformat() if latest else None,
    }
    if health["vpn"] is None:
        health["vpn"] = "unknown"
    if health["api"] is None:
        health["api"] = "unknown"
    if services_count is None:
        from domains.customers.models import Service

        services_count = Service.objects.filter(router=router, tenant_id=router.tenant_id).exclude(
            lifecycle__in=("terminated", "archived")
        ).count()
    return {
        "id": str(router.id),
        "display_name": router.display_name,
        "router_code": router.router_code,
        "location": router.location or None,
        "model": router.model or None,
        "routeros_version": router.routeros_version or None,
        "mode": router.mode,
        "health": health,
        "enforcement_mode": router.enforcement_mode,
        "services_count": services_count,
    }


class RouterListView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Daftar router tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        routers = Router.objects.filter(tenant_id=tenant_id, released_at=None).order_by("created_at")
        return Response([router_summary(r) for r in routers])


class RouterDetailView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Detail router")
    def get(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(
            id=_validate_uuid("router_id", router_id), tenant_id=tenant_id, released_at=None
        ).first()
        if router is None:
            raise ApiError.not_found()
        latest = router.health_samples.order_by("-observed_at").first()
        data = router_summary(router)
        data.update(
            {
                "identity": router.identity or None,
                "capability": router.capability or {},
                "uptime_s": latest.uptime_s if latest else None,
                "serial": router.serial or None,
            }
        )
        return Response(data)


class EnrollmentCreateView(TenantApiView):
    required_permission = "routers.enroll"

    @idempotent("router_enrollment_create")
    @extend_schema(summary="Buat draft enrollment router (token terbit sekali)")
    def post(self, request: Request, tenant_id: str) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        enrollment = services.create_enrollment(tenant_id, body, actor=request.user)
        return Response(
            {
                "id": str(enrollment.id),
                "request": {
                    "display_name": enrollment.display_name,
                    "router_code": enrollment.router_code,
                    "location": body.get("location"),
                    "mode": enrollment.mode,
                },
                "state": "enrollment_issued",
            },
            status=status.HTTP_201_CREATED,
        )


def _get_enrollment(tenant_id: str, enrollment_id: str) -> RouterEnrollment:
    enrollment = (
        RouterEnrollment.objects.filter(id=_validate_uuid("enrollment_id", enrollment_id), tenant_id=tenant_id)
        .order_by("-created_at")
        .first()
    )
    if enrollment is None:
        raise ApiError.not_found()
    return enrollment


class EnrollmentProgressView(TenantApiView):
    required_permission = "routers.enroll"

    @extend_schema(summary="Progres enrollment per tahap")
    def get(self, request: Request, tenant_id: str, enrollment_id: str) -> Response:
        return Response(services.enrollment_progress(_get_enrollment(tenant_id, enrollment_id)))


class EnrollmentBootstrapView(TenantApiView):
    required_permission = "routers.enroll"

    @extend_schema(summary="Skrip bootstrap RouterOS (sensitif; TTL 15 menit)")
    def get(self, request: Request, tenant_id: str, enrollment_id: str) -> Response:
        enrollment = _get_enrollment(tenant_id, enrollment_id)
        if enrollment.created_by_id and request.user and enrollment.created_by_id != request.user.id:
            # Skrip berisi token — hanya pembuat yang boleh mengambilnya.
            raise ApiError.not_found()
        return Response(services.bootstrap_script(enrollment))


class DiscoveryStartView(TenantApiView):
    required_permission = "routers.enroll"

    @idempotent("router_discovery", resource_from=lambda request, kwargs: str(kwargs.get("router_id", "")))
    @extend_schema(summary="Mulai discovery read-only router → job discover_router")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(
            id=_validate_uuid("router_id", router_id), tenant_id=tenant_id, released_at=None
        ).first()
        if router is None:
            raise ApiError.not_found()
        if router.mode != Router.Mode.MANAGED and not router.tunnel_ip:
            # read_only tetap boleh discovery via tunnel; tanpa tunnel = belum enroll.
            raise ApiError.conflict("router_not_enrolled", "error.conflict")
        job = engine.create_job(
            tenant_id=tenant_id, kind="discover_router", actor=request.user, router=router,
            payload={"router_id": str(router.id)},
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


class RouterReleaseView(TenantApiView):
    required_permission = "routers.release"

    @idempotent("router_release", resource_from=lambda request, kwargs: str(kwargs.get("router_id", "")))
    @extend_schema(summary="Lepas router (job; peer/NAS ditarik)")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(
            id=_validate_uuid("router_id", router_id), tenant_id=tenant_id, released_at=None
        ).first()
        if router is None:
            raise ApiError.not_found()
        job = engine.create_job(
            tenant_id=tenant_id, kind="router_release", actor=request.user, router=router,
            payload={"router_id": str(router.id)},
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


class RouterReplaceView(TenantApiView):
    required_permission = "routers.enroll"

    @idempotent("router_replace", resource_from=lambda request, kwargs: str(kwargs.get("router_id", "")))
    @extend_schema(summary="Ganti perangkat — lepas lama + draft enrollment baru")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(
            id=_validate_uuid("router_id", router_id), tenant_id=tenant_id, released_at=None
        ).first()
        if router is None:
            raise ApiError.not_found()
        body = request.data if isinstance(request.data, dict) else {}
        job = engine.create_job(
            tenant_id=tenant_id, kind="router_replace", actor=request.user, router=router,
            payload={"router_id": str(router.id), "display_name": str(body.get("display_name", ""))[:120]},
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


class BridgeEnrollCompleteView(APIView):
    """Callback dari ROUTER (skrip bootstrap) — token di body, tanpa sesi.

    Rate limiting brute-force tidak diperlukan pada 256-bit CSPRNG; token
    kedaluwarsa + konsumsi atomik + hash-only storage (§2.2/§2.7).
    """

    permission_classes: list = []

    @extend_schema(summary="Bridge enrollment: konsumsi token + kunci publik WG")
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        result = services.complete_enrollment(
            str(body.get("token", "")), str(body.get("wg_public_key", ""))
        )
        return Response(result)
