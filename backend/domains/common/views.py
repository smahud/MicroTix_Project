"""Basis view API: sesi, izin, konteks tenant RLS.

- TenantApiView: route /tenants/{tenant_id}/... — membership diverifikasi,
  handler berjalan dalam tenant_scope (transaksi + GUC RLS).
- ActiveTenantApiView: route resource (mis. /jobs/{id}) — tenant diambil dari
  record pada konteks aktif (ARCHITECTURE.md §5).
- Permission non-milik → 404 generik; milik tapi tanpa izin → 403.
"""
from __future__ import annotations

import logging

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.common.envelope import ApiError
from domains.common.tenant_context import tenant_scope
from domains.tenancy.models import Membership
from domains.tenancy.permissions import ROLE_PERMISSIONS, is_sensitive

logger = logging.getLogger(__name__)


class SessionOrAnonymous:
    """Permintaan tanpa sesi → AnonymousUser; view menentukan 401/200."""

    pass


def resolve_membership(user, tenant_id: str) -> Membership:
    if getattr(user, "is_authenticated", False) is not True:
        raise ApiError.unauthorized()
    membership = (
        Membership.objects.filter(user=user, tenant_id=tenant_id, revoked_at=None)
        .select_related("tenant")
        .first()
    )
    if membership is None:
        # Non-milik/tdk terdaftar → 404 generik (jangan bocorkan keberadaan).
        raise ApiError.not_found()
    return membership


def role_permissions(membership: Membership) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(membership.role, frozenset())


def _require_reauth(request) -> None:
    from domains.identity.services import require_reauth as _rr

    _rr(request)


class TenantPermission:
    """Izin berbasis membership + peran pada tenant URL.

    required: nama izin; sensitive=True menambah syarat reauth aktif.
    """

    def __init__(self, required: str, *, sensitive: bool | None = None) -> None:
        self.required = required
        self.sensitive = is_sensitive(required) if sensitive is None else sensitive

    def __call__(self) -> "TenantPermission":
        return self

    # antarmuka DRF
    def has_permission(self, request, view) -> bool:
        tenant_id = view.kwargs.get("tenant_id")
        if not tenant_id:
            return False
        try:
            membership = resolve_membership(request.user, tenant_id)
        except ApiError:
            raise
        request.mt_membership = membership
        allowed = self.required in role_permissions(membership)
        if not allowed:
            # Milik tenant tapi tanpa izin → 403 (§5).
            raise ApiError.forbidden()
        if self.sensitive:
            _require_reauth(request)
        return True


class TenantApiView(APIView):
    """View ter-scoped tenant: dispatch membungkus handler dalam tenant_scope."""

    required_permission: str | None = None
    sensitive: bool | None = None

    def get_permissions(self):
        perms = super().get_permissions()
        if self.required_permission:
            perms.append(TenantPermission(self.required_permission, sensitive=self.sensitive))
        return perms

    def dispatch(self, request, *args, **kwargs):
        if not getattr(self, "swagger_fake_view", False) and kwargs.get("tenant_id") is not None:
            self.args, self.kwargs = args, kwargs
            drf_request = self.initialize_request(request, *args, **kwargs)
            self.request = drf_request
            self.headers = self.default_response_headers
            try:
                self.initial(drf_request, *args, **kwargs)
                membership = getattr(drf_request, "mt_membership", None)
                if membership is None:
                    membership = resolve_membership(drf_request.user, kwargs["tenant_id"])
                    drf_request.mt_membership = membership
                with tenant_scope(membership.tenant_id):
                    response = self._invoke(drf_request, *args, **kwargs)
            except Exception as exc:
                response = self.handle_exception(exc)
            self.response = self.finalize_response(drf_request, response, *args, **kwargs)
            return self.response
        return super().dispatch(request, *args, **kwargs)

    def _invoke(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)


class ActiveTenantApiView(APIView):
    """View resource: tenant diambil dari sesi aktif; record di luar scope → 404."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not getattr(request, "user", None) or isinstance(request.user, AnonymousUser):
            raise ApiError.unauthorized()
        active = request.session.get("active_tenant_id")
        if not active:
            raise ApiError.unauthorized()
        membership = resolve_membership(request.user, active)
        request.mt_membership = membership

    @property
    def active_tenant_id(self) -> str:
        return self.request.mt_membership.tenant_id

    def in_scope(self, record_tenant_id) -> bool:
        return str(record_tenant_id) == str(self.active_tenant_id)
