"""Error envelope standar — ARCHITECTURE.md §5.

{code, message, request_id, locale, field_errors?, retryable?}
Kode mesin stabil; message dilokalkan. field_errors[field] = [{code,message}].
"""
from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from domains.i18n.catalogs import message as translate


class ApiError(exceptions.APIException):
    """Kesalahan domain dengan kode mesin stabil dan status HTTP eksplisit."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "conflict"

    def __init__(
        self,
        code: str,
        message_key: str,
        status_code: int | None = None,
        field_errors: dict[str, list[dict[str, str]]] | None = None,
        retryable: bool | None = None,
        http_message: str | None = None,
    ) -> None:
        self.code = code
        self.message_key = message_key
        self.field_errors = field_errors
        self.retryable = retryable
        self.http_message = http_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(translate(message_key))

    # --- pabrik kesalahan umum sesuai kontrak §5 ---

    @classmethod
    def validation(cls, field_errors: dict[str, list[dict[str, str]]] | None = None, key: str = "error.validation") -> "ApiError":
        return cls("validation_error", key, status.HTTP_422_UNPROCESSABLE_ENTITY, field_errors=field_errors)

    @classmethod
    def unauthorized(cls, key: str = "error.unauthorized") -> "ApiError":
        return cls("unauthorized", key, status.HTTP_401_UNAUTHORIZED)

    @classmethod
    def forbidden(cls, key: str = "error.forbidden") -> "ApiError":
        return cls("forbidden", key, status.HTTP_403_FORBIDDEN)

    @classmethod
    def not_found(cls, key: str = "error.not_found") -> "ApiError":
        return cls("not_found", key, status.HTTP_404_NOT_FOUND)

    @classmethod
    def conflict(cls, code: str = "conflict", key: str = "error.conflict") -> "ApiError":
        return cls(code, key, status.HTTP_409_CONFLICT)

    @classmethod
    def rate_limited(cls, retry_after_s: int) -> "ApiError":
        err = cls("rate_limited", "error.rate_limited", status.HTTP_429_TOO_MANY_REQUESTS, retryable=True)
        err.retry_after_s = retry_after_s
        return err

    @classmethod
    def unavailable(cls, code: str = "dependency_unavailable", key: str = "error.dependency_unavailable") -> "ApiError":
        return cls(code, key, status.HTTP_503_SERVICE_UNAVAILABLE, retryable=True)


def _envelope(request: Any, code: str, message: str, field_errors=None, retryable: bool | None = None) -> dict:
    request_id = getattr(request, "mt_request_id", None) or "unknown"
    locale = getattr(request, "mt_locale", "id")
    env: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
        "locale": locale,
    }
    if field_errors:
        env["field_errors"] = field_errors
    if retryable is not None:
        env["retryable"] = retryable
    return env


def exception_handler(exc: Exception, context: dict) -> Response | None:
    request = context.get("request")

    # 1) Kesalahan domain milik kita
    if isinstance(exc, ApiError):
        set_rollback()
        headers = {}
        retry_after = getattr(exc, "retry_after_s", None)
        if retry_after is not None:
            headers["Retry-After"] = str(int(retry_after))
        return Response(
            _envelope(request, exc.code, str(exc.detail), exc.field_errors, exc.retryable),
            status=exc.status_code,
            headers=headers or None,
        )

    # 2) DRF APIException (termasuk NotAuthenticated/PermissionDenied/NotFound/ValidationError)
    if isinstance(exc, exceptions.APIException):
        set_rollback()
        headers = {}
        code = exc.get_codes()
        if isinstance(code, list):
            code = code[0] if code else "error"
        status_map = {
            status.HTTP_401_UNAUTHORIZED: ("unauthorized", "error.unauthenticated"),
            status.HTTP_403_FORBIDDEN: ("forbidden", "error.forbidden"),
            status.HTTP_404_NOT_FOUND: ("not_found", "error.not_found"),
            status.HTTP_429_TOO_MANY_REQUESTS: ("rate_limited", "error.rate_limited"),
        }
        if exc.status_code in status_map:
            machine, key = status_map[exc.status_code]
            message = translate(key)
        elif exc.status_code == status.HTTP_400_BAD_REQUEST:
            machine, message = "validation_error", translate("error.validation")
        else:
            machine, message = str(code), str(exc.detail)
        field_errors = None
        if isinstance(exc.detail, dict):
            field_errors = {
                str(field): (
                    [{"code": str(c), "message": str(c)} for c in codes]
                    if isinstance(codes, list)
                    else [{"code": str(codes), "message": str(codes)}]
                )
                for field, codes in exc.detail.items()
            }
            message = translate("error.validation")
        retryable = exc.status_code >= 500 or exc.status_code == 429
        if exc.status_code == 429 and getattr(exc, "wait", None) is not None:
            headers["Retry-After"] = str(int(exc.wait))
        return Response(
            _envelope(request, machine, message, field_errors, retryable),
            status=exc.status_code,
            headers=headers or None,
        )

    # 3) Http404 / PermissionDenied Django (mis. tidak cocok URL)
    if isinstance(exc, Http404):
        return Response(_envelope(request, "not_found", translate("error.not_found")), status=404)
    if isinstance(exc, DjangoPermissionDenied):
        return Response(_envelope(request, "forbidden", translate("error.forbidden")), status=403)

    return None  # 500 ditangani oleh handler terakhir di middleware/views


def handler404(request, exception=None):
    """404 JSON untuk route tak dikenal (SPA menerima envelope, bukan HTML)."""
    from django.http import JsonResponse

    return JsonResponse(
        _envelope(request, "not_found", translate("error.not_found")), status=404
    )


def handler500(request):
    """500 JSON envelope — tanpa detail internal."""
    from django.http import JsonResponse

    return JsonResponse(
        _envelope(request, "internal_error", translate("error.dependency_unavailable"), retryable=True),
        status=500,
    )
