"""Dokumen terbit immutable (TK-109) — invoice internet & kwitansi pembayaran.

Kontrak: docs/PRODUCT.md BIL-01 (dokumen memuat bahasa terbit) dan BIL-08
(kwitansi/invoice PDF, nomor kwitansi unik), docs/I18N.md §2 baris "Dokumen
yang dihasilkan" (I18N-01: snapshot bahasa, timezone, template version, nilai,
dan artifact/hash final saat issued; reprint tidak memakai template terbaru).

IssuedDocument adalah snapshot penerbitan: row TIDAK PERNAH diubah/dihapus
(trigger immutable 0002); reprint membaca artifact tersimpan, bukan template
terbaru. storage_path bersifat privat/opaque — tidak pernah diekspos via API.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


class IssuedDocument(models.Model):
    """Satu dokumen yang telah diterbitkan (PDF immutable + snapshot nilai)."""

    class Kind(models.TextChoices):
        INTERNET_INVOICE = "internet_invoice"
        RECEIPT = "receipt"          # kwitansi pembayaran internet
        SAAS_INVOICE = "saas_invoice"  # reserved — template belum wajib M6 ini
        REPORT = "report"              # reserved

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        related_name="issued_documents",
        db_column="tenant_id",
    )
    kind = models.CharField(max_length=48, choices=Kind.choices)
    # Ditetapkan pemanggil (domain billing), mis. INV-{ns}-{YYYYMM}-{seq} (BIL-01)
    # atau nomor kwitansi unik (BIL-08).
    doc_number = models.CharField(max_length=64)
    # Sumber dokumen (polimorfik, string id — BUKAN FK: tipe bervariasi lintas domain).
    ref_type = models.CharField(max_length=48, blank=True, default="")
    ref_id = models.CharField(max_length=64, blank=True, default="")
    # Bahasa terbit (BIL-01; I18N-04) — dibekukan saat issued.
    locale = models.CharField(max_length=5, default="id")
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    template_version = models.CharField(max_length=16, default="1")
    # Snapshot nilai yang dirender: uang sebagai string, tanggal ISO (I18N-03).
    values = models.JSONField(default=dict)
    # Path privat opaque di penyimpanan privat; TIDAK diekspos via API.
    storage_path = models.CharField(max_length=512, blank=True, default="")
    sha256 = models.CharField(max_length=64, blank=True, default="")
    size_bytes = models.IntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "documents_issued_document"
        constraints = [
            # Nomor dokumen unik per tenant dan jenis (BIL-01/BIL-08).
            models.UniqueConstraint(
                fields=["tenant", "kind", "doc_number"],
                name="uq_document_tenant_kind_number",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "kind", "issued_at"], name="ix_document_tenant_kind_time"),
            models.Index(fields=["tenant", "ref_type", "ref_id"], name="ix_document_tenant_ref"),
        ]
