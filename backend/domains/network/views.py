"""API registri router (R1 fondasi): GET list/detail.

Enrollment/discovery/cutover adalah endpoint M3+ — tidak dibuat di sini
(jangan membangun API untuk fitur fase yang belum aktif).
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.common.views import TenantApiView
from domains.network.models import Router, RouterHealthSample


def router_summary(router: Router, *, services_count: int = 0) -> dict:
    latest = router.health_samples.order_by("-observed_at").first()
    health = {
        "vpn": (None if latest is None or latest.vpn_up is None else ("up" if latest.vpn_up else "down")),
        "api": (None if latest is None or latest.api_up is None else ("up" if latest.api_up else "down")),
        "observed_at": latest.observed_at.isoformat() if latest else None,
    }
    # Tanpa sampel: unknown, bukan down (§11 — jangan membuat kesimpulan).
    if health["vpn"] is None:
        health["vpn"] = "unknown"
    if health["api"] is None:
        health["api"] = "unknown"
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
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
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
