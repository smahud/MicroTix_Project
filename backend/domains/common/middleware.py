"""Middleware request-id + locale.

request_id: UUID pendek per request, masuk envelope error dan audit.
locale: dari header Accept-Language dengan bobot q; fallback 'id' (I18N).
"""
from __future__ import annotations

import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

SUPPORTED_LOCALES = ("id", "en")
DEFAULT_LOCALE = "id"


def negotiate_locale(header: str | None) -> str:
    """Pilih locale terbaik dari Accept-Language; fallback id (I18N-05)."""
    if not header:
        return DEFAULT_LOCALE
    candidates: list[tuple[float, str]] = []
    for part in header.split(","):
        piece = part.strip()
        if not piece:
            continue
        if ";q=" in piece:
            lang, _, q = piece.partition(";q=")
            try:
                weight = float(q)
            except ValueError:
                weight = 0.0
        else:
            lang, weight = piece, 1.0
        lang = lang.strip().lower()
        base = lang.split("-")[0]
        if base in SUPPORTED_LOCALES:
            candidates.append((weight, base))
    if not candidates:
        return DEFAULT_LOCALE
    candidates.sort(key=lambda pair: -pair[0])
    return candidates[0][1]


class RequestIdLocaleMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.mt_request_id = uuid.uuid4().hex[:16]
        request.mt_locale = negotiate_locale(request.headers.get("Accept-Language"))
        response = self.get_response(request)
        response.headers["X-Request-Id"] = request.mt_request_id
        # Keamanan dasar untuk API JSON.
        response.headers.setdefault("Cache-Control", "no-store")
        return response
