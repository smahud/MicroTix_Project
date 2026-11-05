"""GET /tenants/{t}/audit-timeline — U18 panel audit (customers.read)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.pagination import decode_cursor, encode_cursor, page_response, parse_limit
from domains.common.views import TenantApiView
from domains.audit.models import AuditEvent


class AuditTimelineView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Timeline audit tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        limit = parse_limit(request.query_params.get("limit"))
        cursor = request.query_params.get("cursor")
        target_id = request.query_params.get("target_id")
        qs = AuditEvent.objects.filter(tenant_id=tenant_id)
        if target_id:
            qs = qs.filter(target_id=target_id)
        qs = qs.order_by("-created_at", "-id")
        if cursor:
            sort_key, last_id = decode_cursor(cursor)
            qs = qs.filter(created_at__lt=sort_key) | qs.filter(created_at=sort_key, id__lt=last_id)
        events = list(qs[: limit + 1])
        next_cursor = None
        if len(events) > limit:
            events = events[:limit]
            last = events[-1]
            next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))
        items = [
            {
                "id": str(e.id),
                "at": e.created_at.isoformat(),
                "actor_display": e.actor_display,
                "action_code": e.action_code,
                "target_display": e.target_display or None,
            }
            for e in events
        ]
        return Response(page_response(items, next_cursor))
