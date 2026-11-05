"""Endpoint auth/sesi/tenant — kontrak client.ts (PENDING_BACKEND → didefinisikan).

POST /auth/register              → 200 {verification_sent: true}
POST /auth/verify-email          → 200 AuthContext
POST /auth/login                 → 200 {requires_totp}
POST /auth/login-totp            → 200 AuthContext
POST /auth/recover               → 204
GET  /auth/session               → 200 AuthContext
POST /auth/logout                → 204
POST /auth/reauthenticate        → 200 {valid_until}
GET  /auth/tenants               → 200 [TenantSummary]
POST /auth/tenants/{id}/switch   → 200 AuthContext
POST /auth/mfa/setup             → 200 {device_id, secret, otpauth_uri}
POST /auth/mfa/confirm           → 200 {recovery_codes}
"""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.common.envelope import ApiError
from domains.identity import services
from domains.identity.serializers import auth_context, session_user


def _body(request: Request) -> dict:
    data = request.data
    return data if isinstance(data, dict) else {}


class RegisterView(APIView):
    permission_classes: list = []

    @extend_schema(responses={200: OpenApiResponse(description="{verification_sent: true}")})
    def post(self, request: Request) -> Response:
        body = _body(request)
        services.register(
            email=str(body.get("email", "")),
            password=str(body.get("password", "")),
            full_name=str(body.get("full_name", "")),
            company_name=str(body.get("company_name", "")),
        )
        return Response({"verification_sent": True})


class VerifyEmailView(APIView):
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        token = str(_body(request).get("token", ""))
        user = services.verify_email(token)
        services._establish_session(request, user)
        return Response(auth_context(services.build_auth_context(request)))


class LoginView(APIView):
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        ensure_csrf(request)
        body = _body(request)
        result = services.begin_login(request, str(body.get("email", "")), str(body.get("password", "")))
        return Response(result)


class LoginTotpView(APIView):
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        code = str(_body(request).get("code", ""))
        is_totp = code.isdigit() and len(code) == 6
        is_recovery = (
            len(code) == 19
            and code.count("-") == 3
            and all(len(part) == 4 and part.isalnum() for part in code.split("-"))
        )
        if not (is_totp or is_recovery):
            raise ApiError.validation(
                {"code": [{"code": "pattern", "message": "Kode TOTP harus 6 digit atau kode pemulihan"}]}
            )
        user = services.complete_totp(request, code)
        return Response(auth_context(services.build_auth_context(request)))


class RecoverView(APIView):
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        # Respons selalu 204 — tidak membocorkan eksistensi akun.
        email = str(_body(request).get("email", "")).strip().lower()
        from domains.identity.models import User

        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            token = services._issue_email_token(user, "password_reset")
            services._send_email(
                user,
                subject_key="Reset password MicroTix",
                body=f"Tautan reset password (berlaku 24 jam):\n{token}",
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


def ensure_csrf(request: Request) -> None:
    """Pastikan cookie CSRF tersedia untuk SPA (dipanggil sebelum cek sesi).

    get_token() pada HttpRequest mentandai cookie; middleware CSRF
    menuliskannya pada respons (juga untuk respons 401 anonim).
    """
    from django.middleware.csrf import get_token

    get_token(request._request)


class SessionView(APIView):
    permission_classes: list = []

    def get(self, request: Request) -> Response:
        ensure_csrf(request)
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            raise ApiError.unauthorized()
        if services.session_expired(request):
            services.logout(request)
            raise ApiError.unauthorized()
        return Response(auth_context(services.build_auth_context(request)))


class LogoutView(APIView):
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        services.logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReauthenticateView(APIView):
    def post(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            raise ApiError.unauthorized()
        body = _body(request)
        valid_until = services.reauthenticate(
            request, str(body.get("password", "")), str(body.get("totp_code", ""))
        )
        return Response({"valid_until": valid_until})


class TenantsView(APIView):
    def get(self, request: Request) -> Response:
        ctx = services.build_auth_context(request)
        return Response(ctx.tenants)


class TenantSwitchView(APIView):
    def post(self, request: Request, tenant_id: str) -> Response:
        if not request.user.is_authenticated:
            raise ApiError.unauthorized()
        ctx = services.switch_tenant(request, tenant_id)
        return Response(auth_context(ctx))


class MfaSetupView(APIView):
    def post(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            raise ApiError.unauthorized()
        return Response(services.setup_totp(request.user))


class MfaConfirmView(APIView):
    def post(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            raise ApiError.unauthorized()
        body = _body(request)
        codes = services.confirm_totp(request.user, str(body.get("device_id", "")), str(body.get("code", "")))
        return Response({"recovery_codes": codes})
