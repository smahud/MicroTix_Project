"""Idempotency-Key untuk mutasi (ARCHITECTURE.md §5).

Scope: principal + tenant/platform + operation + resource + key.
Body dibandingkan HMAC; sama+isi sama → replay respons logis; isi berbeda →
409 idempotency_conflict. Retensi 7 hari.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import json
from typing import Any, Callable

from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.jobs.models import IdempotencyKey

TTL_S = 7 * 24 * 3600


def _body_hash(body: Any) -> str:
    canonical = json.dumps(body or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(settings.SECRET_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def _principal(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return str(user.id)
    return "anonymous"


def idempotent(operation: str, resource_from: Callable[[Any, Any], str] | None = None):
    """Dekorator view DRF: simpan/replay respons per Idempotency-Key."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, request: Any, *args: Any, **kwargs: Any):
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                # Wajib untuk uang/provisioning/commit/cutover/backup/aktivasi.
                raise ApiError.validation(
                    {"idempotency_key": [{"code": "required", "message": "Idempotency-Key wajib"}]}
                )
            if len(key) > 128:
                raise ApiError.validation(
                    {"idempotency_key": [{"code": "max_length", "message": "Idempotency-Key terlalu panjang"}]}
                )
            tenant_part = str(kwargs.get("tenant_id") or request.session.get("active_tenant_id") or "platform")
            resource = resource_from(request, kwargs) if resource_from else kwargs.get("resource_id", "")
            scope = f"{operation}:{tenant_part}:{resource}"
            body_h = _body_hash(getattr(request, "data", None))

            cutoff = timezone.now() - timezone.timedelta(seconds=TTL_S)
            IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()

            existing = IdempotencyKey.objects.filter(scope=scope, idem_key=key).first()
            if existing is not None:
                if existing.body_hash != body_h:
                    raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")
                if existing.response_status is not None:
                    return Response(existing.response_body, status=existing.response_status)
                # Pencatatan tanpa respons (request sebelumnya gagal setelah simpan):
                # izinkan eksekusi ulang dengan key semula.
            else:
                IdempotencyKey.objects.create(
                    principal=_principal(request),
                    scope=scope,
                    idem_key=key,
                    body_hash=body_h,
                )

            response = func(self, request, *args, **kwargs)
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                IdempotencyKey.objects.filter(scope=scope, idem_key=key).update(
                    response_status=response.status_code,
                    response_body=response.data,
                )
            return response

        return wrapper

    return decorator
