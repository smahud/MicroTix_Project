"""API dokumen terbit (TK-109) — BIL-08: daftar + unduh PDF reprint.

GET  /tenants/{t}/documents?kind=&ref_type=&ref_id=&limit=&cursor=
     → {items: [document_info], next_cursor}   (customers.read)
GET  /tenants/{t}/documents/{document_id}
     → application/pdf (Content-Disposition inline)   (customers.read)

Dokumen tidak pernah di-render ulang dari template terbaru: artifact
tersimpan dibaca apa adanya (I18N-01/T23-I18-02). Non-milik → 404 generik
(ARCHITECTURE.md §5); storage_path tidak muncul di respons.
"""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.common.pagination import decode_cursor, encode_cursor, page_response, parse_limit
from domains.common.views import TenantApiView
from domains.documents import services
from domains.documents.models import IssuedDocument
from domains.documents.services import document_info

# Karakter aman untuk filename Content-Disposition (anti header-injection).
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _paginate(request: Request, qs):
    """Paginasi kursor standar (issued_at desc, id desc) — pola customers."""
    limit = parse_limit(request.query_params.get("limit"))
    cursor = request.query_params.get("cursor")
    if cursor:
        sort_key, last_id = decode_cursor(cursor)
        qs = qs.filter(issued_at__lt=sort_key) | qs.filter(issued_at=sort_key, id__lt=last_id)
    items = list(qs[: limit + 1])
    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        last = items[-1]
        next_cursor = encode_cursor(last.issued_at.isoformat(), str(last.id))
    return items, next_cursor


class DocumentListView(TenantApiView):
    """GET daftar dokumen terbit tenant (filter kind/ref_type/ref_id eksak).

    permission_classes kosong: IsAuthenticated DRF + SessionAuthentication
    tanpa WWW-Authenticate memaksa anonim jadi 403, sedangkan kontrak §5
    meminta 401 — TenantPermission.resolve_membership yang menuntun
    401 (anonim) / 404 (non-milik) / 403 (milik tanpa izin), seperti
    preseden PlatformApiView (subscriptions/views.py).
    """

    required_permission = "customers.read"
    permission_classes: list = []

    @extend_schema(summary="Daftar dokumen terbit tenant (invoice/kwitansi)")
    def get(self, request: Request, tenant_id: str) -> Response:
        params = request.query_params
        qs = IssuedDocument.objects.filter(tenant_id=tenant_id)
        kind = params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        ref_type = params.get("ref_type")
        if ref_type:
            qs = qs.filter(ref_type=ref_type)
        ref_id = params.get("ref_id")
        if ref_id:
            qs = qs.filter(ref_id=ref_id)
        items, next_cursor = _paginate(request, qs.order_by("-issued_at", "-id"))
        return Response(page_response([document_info(doc) for doc in items], next_cursor))


class DocumentArtifactView(TenantApiView):
    """GET artifact PDF dokumen (reprint identik; integritas sha256 dicek).

    401/404/403 mengikuti resolve_membership — lihat DocumentListView.
    """

    required_permission = "customers.read"
    permission_classes: list = []

    @extend_schema(summary="Unduh PDF dokumen terbit (application/pdf)")
    def get(self, request: Request, tenant_id: str, document_id: str) -> HttpResponse:
        # Tidak milik / id rusak → 404 generik (jangan bocorkan keberadaan).
        try:
            document = IssuedDocument.objects.filter(id=document_id, tenant_id=tenant_id).first()
        except (ValueError, ValidationError):
            raise ApiError.not_found() from None
        if document is None:
            raise ApiError.not_found()
        data = services.artifact_bytes(document)
        safe_name = _SAFE_FILENAME_RE.sub("_", document.doc_number).strip("._") or "document"
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{safe_name}.pdf"'
        return response
