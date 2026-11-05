"""Autentikasi DRF berbasis sesi Django + CSRF ketat.

DRF membungkus view dengan csrf_exempt sehingga middleware CSRF Django TIDAK
berlaku untuk endpoint DRF; kelas ini menjadi penegak CSRF tunggal:
- Unsafe method (POST/PATCH/PUT/DELETE) wajib membawa token valid —
  termasuk permintaan anonim seperti login (mencegah login-CSRF).
- Pengguna diambil dari sesi Django (cookie HttpOnly), bukan token bearer.
"""
from __future__ import annotations

from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication as DRFSessionAuthentication
from rest_framework.request import Request

UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


class _CsrfCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class SessionAuthentication(DRFSessionAuthentication):
    def authenticate(self, request: Request):
        # CSRF wajib untuk semua unsafe method — anonim maupun terautentikasi.
        if request.method in UNSAFE_METHODS:
            check = _CsrfCheck(lambda req: None)
            check.process_request(request._request)
            reason = check.process_view(request._request, None, (), {})
            if reason:
                raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")
        user = getattr(request._request, "user", None)
        if user is None or not user.is_active:
            return None
        return (user, None)
