"""Layanan dokumen terbit (TK-109) — penerbitan immutable + baca artifact.

Penerbitan (issue_document) menjalankan urutan yang aman terhadap rollback:
artifact PDF ditulis DULU ke penyimpanan privat (opaque, 0600), row DB sesudah
— kegagalan transaksi menyisakan paling banyak file yatim, tidak pernah row
menggantung tanpa artifact. Row immutable (trigger 0002): tidak ada jalur
update di modul ini; reprint membaca artifact tersimpan + cek sha256.

Keamanan data: values dapat memuat data pelanggan — tidak pernah di-log.
storage_path tidak pernah diekspos via API (serialisasi document_info tanpa
path).
"""
from __future__ import annotations

import hashlib
import os
import uuid

from django.conf import settings
from django.db import IntegrityError

from domains.common.envelope import ApiError
from domains.documents.models import IssuedDocument
from domains.documents.rendering import TEMPLATES, latest_template_version, render_pdf

# Bahasa dokumen yang didukung (I18N.md §1: id default, en wajib).
_SUPPORTED_LOCALES = ("id", "en")


def resolve_locale(locale: str) -> str:
    """Normalisasi bahasa dokumen dengan rantai fallback (I18N-01 §2).

    Bahasa diminta → bahasa induk (mis. "en-GB" → "en") → "id".
    """
    raw = (locale or "").strip().lower()
    if raw in _SUPPORTED_LOCALES:
        return raw
    parent = raw.split("-", 1)[0]
    if parent in _SUPPORTED_LOCALES:
        return parent
    return "id"


def _write_artifact(data: bytes) -> str:
    """Tulis artifact PDF ke penyimpanan privat: path opaque, mode 0600, fsync."""
    storage_path = f"documents/{uuid.uuid4().hex}"
    target = settings.MT_STORAGE_ROOT / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        # Gagal menulis parsial: hapus sisa best-effort, jangan bocor fd/file.
        try:
            os.unlink(target)
        except OSError:
            pass
        raise
    return storage_path


def _remove_artifact(storage_path: str) -> None:
    try:
        (settings.MT_STORAGE_ROOT / storage_path).unlink()
    except OSError:
        pass  # best-effort; janitor menyusul bersama penyimpanan privat


def issue_document(
    *,
    tenant_id,
    kind: str,
    doc_number: str,
    ref_type: str = "",
    ref_id: str = "",
    locale: str = "id",
    timezone_name: str = "Asia/Jakarta",
    values: dict,
    template_version: str | None = None,
) -> IssuedDocument:
    """Terbitkan dokumen: render → simpan artifact → row snapshot immutable.

    Pemanggil (domain billing) wajib berjalan dalam tenant_scope(tenant) agar
    RLS aktif. kind tanpa templat terdaftar (saas_invoice/report M6 ini) →
    404 error.not_found — jujur, bukan API palsu. Duplikat nomor
    (tenant, kind, doc_number) → 409 conflict (BIL-01/BIL-08).
    """
    loc = resolve_locale(locale)
    version = str(template_version) if template_version else latest_template_version(kind)
    builder = TEMPLATES.get((kind, version))
    if builder is None:
        raise ApiError.not_found()

    html = builder(values or {}, loc)
    data = render_pdf(html)

    # Artifact dulu, row kemudian: rollback DB menyisakan file yatim paling
    # buruknya — tidak pernah row tanpa artifact.
    storage_path = _write_artifact(data)

    try:
        document = IssuedDocument.objects.create(
            tenant_id=tenant_id,
            kind=kind,
            doc_number=doc_number,
            ref_type=ref_type,
            ref_id=ref_id,
            locale=loc,
            timezone=timezone_name,
            template_version=version,
            values=values or {},
            storage_path=storage_path,
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )
    except IntegrityError:
        # (tenant, kind, doc_number) sudah ada — artifact percuma dibuang.
        _remove_artifact(storage_path)
        raise ApiError.conflict() from None
    return document


def artifact_bytes(document: IssuedDocument) -> bytes:
    """Baca artifact tersimpan dengan verifikasi sha256 (reprint konsisten).

    File hilang / hash tidak cocok → 500 document_integrity: dokumen terbit
    harus selalu bisa dicetak ulang identik; kegagalan integritas tidak boleh
    disamarkan (T23-I18-02).
    """
    if not document.storage_path:
        raise ApiError(
            code="document_integrity",
            message_key="error.document_integrity",
            status_code=500,
        )
    try:
        data = (settings.MT_STORAGE_ROOT / document.storage_path).read_bytes()
    except OSError:
        raise ApiError(
            code="document_integrity",
            message_key="error.document_integrity",
            status_code=500,
        ) from None
    if hashlib.sha256(data).hexdigest() != document.sha256:
        raise ApiError(
            code="document_integrity",
            message_key="error.document_integrity",
            status_code=500,
        )
    return data


def document_info(document: IssuedDocument) -> dict:
    """Bentuk serialisasi API IssuedDocument — TANPA storage_path (privat)."""
    return {
        "id": str(document.id),
        "kind": document.kind,
        "doc_number": document.doc_number,
        "ref_type": document.ref_type,
        "ref_id": document.ref_id,
        "locale": document.locale,
        "timezone": document.timezone,
        "template_version": document.template_version,
        "sha256": document.sha256,
        "size_bytes": document.size_bytes,
        "issued_at": document.issued_at.isoformat(),
    }
