"""API domain akses — akun AAA + status NAS/RADIUS per router (U19, TK-412).

Cutover B0–B6 TIDAK dibangun pada beta ini (gate G1 belum lulus — lihat
docs/ACCEPTANCE.md §3: 'Cutover RADIUS dan mode otoritatif' butuh T16–T18,
T21 pada lab). Endpoint yang ada benar-benar berfungsi terhadap data nyata.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from domains.access import services as access_services
from domains.access.models import AccessAccount, Nas
from domains.common.envelope import ApiError
from domains.common.pagination import decode_cursor, encode_cursor, parse_limit
from domains.common.views import TenantApiView
from domains.network.models import Router

# Enum state akun untuk klien (label i18n via /meta/enums).
_ACCOUNT_FIELDS = ("id", "username", "kind", "state", "credential_state", "simultaneous_use", "created_at")


def _account_row(account: AccessAccount) -> dict:
    return {
        "id": str(account.id),
        "username": account.username,
        "kind": account.kind,
        "state": account.state,
        "credential_state": account.credential_state,
        "simultaneous_use": account.simultaneous_use,
        "service_id": str(account.service_id) if account.service_id else None,
        "created_at": account.created_at.isoformat(),
    }


class AccessAccountListView(TenantApiView):
    """GET /tenants/{t}/access-accounts — kursor + filter query/state."""

    required_permission = "customers.read"

    @extend_schema(summary="Daftar akun akses (AAA) tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        limit = parse_limit(request.query_params.get("limit"))
        cursor = request.query_params.get("cursor")
        qs = AccessAccount.objects.all().order_by("created_at", "id")
        query = (request.query_params.get("query") or "").strip()
        if query:
            qs = qs.filter(username__icontains=query)
        state = (request.query_params.get("state") or "").strip()
        if state:
            if state not in AccessAccount.State.values:
                raise ApiError.validation(
                    field_errors={"state": [{"code": "invalid", "message": "State tidak dikenal"}]}
                )
            qs = qs.filter(state=state)
        if cursor:
            sort_key, last_id = decode_cursor(cursor)
            qs = qs.filter(created_at__gt=sort_key) | qs.filter(created_at=sort_key, id__gt=last_id)
        rows = list(qs[: limit + 1])
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = None
        if has_more and rows:
            last = rows[-1]
            next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))
        return Response(
            {
                "items": [_account_row(a) for a in rows],
                "next_cursor": next_cursor,
                "has_more": has_more,
            }
        )


class AccessAccountPatchView(TenantApiView):
    """PATCH /tenants/{t}/access-accounts/{id} — suspend/activate (RAD-06).

    Suspend: proyeksi Auth-Type Reject pada transaksi sama. Activate:
    manual (services.activate), memproyeksikan ulang atribut terkini.
    Disconnect sesi aktif = efek eksternal TERPISAH via job (belum aktif
    sampai dispatcher RADIUS terverifikasi lab).
    """

    required_permission = "services.activate"

    @extend_schema(summary="Ubah state akun akses (suspend/activate)")
    def patch(self, request: Request, tenant_id: str, account_id: str) -> Response:
        account = AccessAccount.objects.filter(id=account_id, tenant_id=tenant_id).first()
        if account is None:
            raise ApiError.not_found()
        body = request.data if isinstance(request.data, dict) else {}
        new_state = str(body.get("state", "")).strip()
        try:
            account = access_services.set_account_state(account, new_state=new_state, actor=request.user)
        except access_services.AccessError as exc:
            raise ApiError(exc.code, f"access.{exc.code}", status_code=400, http_message=exc.message) from None
        return Response(_account_row(account))


class AccessAccountRotateView(TenantApiView):
    """POST rotate password — aksi terpisah (RAD-05 §3)."""

    required_permission = "services.provision"

    @extend_schema(summary="Rotasi password akun akses")
    def post(self, request: Request, tenant_id: str, account_id: str) -> Response:
        account = AccessAccount.objects.filter(id=account_id, tenant_id=tenant_id).first()
        if account is None:
            raise ApiError.not_found()
        body = request.data if isinstance(request.data, dict) else {}
        new_password = str(body.get("password", ""))
        try:
            account = access_services.rotate_password(account, new_password=new_password, actor=request.user)
        except access_services.AccessError as exc:
            raise ApiError(exc.code, f"access.{exc.code}", status_code=400, http_message=exc.message) from None
        return Response({"id": str(account.id), "state": account.state, "credential_state": account.credential_state})


class RadiusStatusListView(TenantApiView):
    """GET /tenants/{t}/radius-status — status NAS per router (U19)."""

    required_permission = "routers.read"

    @extend_schema(summary="Status RADIUS per router (desired vs applied)")
    def get(self, request: Request, tenant_id: str) -> Response:
        routers = Router.objects.filter(tenant_id=tenant_id, released_at=None).order_by("created_at")
        result = []
        for router in routers:
            nas = getattr(router, "nas", None)
            result.append(
                {
                    "router_id": str(router.id),
                    "router_name": router.display_name,
                    "enforcement_mode": router.enforcement_mode,
                    "nas": {
                        "shortname": nas.shortname if nas else None,
                        "desired_revision": nas.desired_revision if nas else None,
                        "applied_revision": nas.applied_revision if nas else None,
                        "pending_reconciliation": bool(nas and (nas.applied_revision or 0) < nas.desired_revision),
                    }
                    if nas
                    else None,
                }
            )
        return Response(result)


class RadiusStatusDetailView(RadiusStatusListView):
    @extend_schema(summary="Status RADIUS satu router")
    def get(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
        if router is None:
            raise ApiError.not_found()
        nas = getattr(router, "nas", None)
        return Response(
            {
                "router_id": str(router.id),
                "router_name": router.display_name,
                "enforcement_mode": router.enforcement_mode,
                "nas": {
                    "shortname": nas.shortname if nas else None,
                    "desired_revision": nas.desired_revision if nas else None,
                    "applied_revision": nas.applied_revision if nas else None,
                    "pending_reconciliation": bool(nas and (nas.applied_revision or 0) < nas.desired_revision),
                }
                if nas
                else None,
            }
        )


class NasPendingView(TenantApiView):
    """GET /tenants/{t}/nas/pending — antrean reconciler (op internal)."""

    required_permission = "routers.configure"

    @extend_schema(summary="NAS menunggu rekonsiliasi")
    def get(self, request: Request, tenant_id: str) -> Response:
        return Response(access_services.nas_pending_reconciliation(tenant_id))
