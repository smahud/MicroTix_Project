"""Endpoint meta/health — ARCHITECTURE.md §5.

- GET /meta/enums?locale=id — enum terautentikasi.
- GET /meta/branding — konfigurasi publik (tanpa autentikasi).
- GET /meta/config — konfigurasi resolved + release flag (autentikasi).
- GET /health/live, /health/ready — status minimal tanpa detail internal.
"""
from __future__ import annotations

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.common.middleware import DEFAULT_LOCALE
from domains.config.branding import resolve_branding
from domains.config.registry import RELEASE_FLAGS, registry
from domains.i18n.enums import enums_for


class EnumsView(APIView):
    @extend_schema(summary="Label enum terlokalkan", parameters=[])
    def get(self, request) -> Response:
        locale = request.query_params.get("locale") or getattr(request, "mt_locale", DEFAULT_LOCALE)
        if locale not in ("id", "en"):
            locale = "id"
        return Response(enums_for(locale))


class BrandingView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(summary="Branding publik (resolved backend)")
    def get(self, request) -> Response:
        return Response(resolve_branding())


class ConfigView(APIView):
    @extend_schema(summary="Konfigurasi resolved + release flag")
    def get(self, request) -> Response:
        reg = registry()
        return Response(
            {
                "revision": reg.revision,
                "release_flags": RELEASE_FLAGS,
                "pagination": {
                    "default": reg.get_int("api.pagination_default"),
                    "max": reg.get_int("api.pagination_max"),
                },
                "session": {
                    "tenant_idle_s": reg.get_int("session.tenant_idle_s"),
                    "tenant_absolute_s": reg.get_int("session.tenant_absolute_s"),
                },
                "job": {
                    "status_poll_initial_s": reg.get_int("job.status_poll_initial_s"),
                    "status_poll_later_s": reg.get_int("job.status_poll_later_s"),
                },
            }
        )


class HealthLiveView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(summary="Liveness probe")
    def get(self, request) -> Response:
        return Response({"status": "live"})


class HealthReadyView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(summary="Readiness probe — DB + migrasi")
    def get(self, request) -> Response:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            return Response({"status": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ready"})
