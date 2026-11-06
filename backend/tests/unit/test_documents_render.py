"""Unit render dokumen (TK-109) — determinisme, escape, format I18N-03.

Tanpa DB (marker unit). Meliputi:
- render_pdf deterministik byte-identik (rl_config.invariant) + magic %PDF-.
- escape nilai pelanggan (anti HTML injection).
- assert_no_external_refs menolak src/href jaringan/file (ARCHITECTURE §1).
- format_idr/format_date/format_period id/en dari katalog doc.*.
- registry templat: versi terbaru; kind tanpa templat → 404 (anti API palsu).
- resolve_locale rantai fallback I18N-01.
"""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from domains.common.envelope import ApiError
from domains.documents import rendering
from domains.documents.rendering import (
    TEMPLATES,
    assert_no_external_refs,
    format_date,
    format_idr,
    format_period,
    latest_template_version,
    render_pdf,
)
from domains.documents.services import resolve_locale

pytestmark = pytest.mark.unit

INVOICE_VALUES = {
    "tenant_name": "RT RW Net Melati",
    "doc_number": "INV-rtrw-aaaa000001-202611-0001",
    "issued_date": "2026-11-01",
    "due_date": "2026-11-08",
    "customer_name": "Budi Santoso",
    "service_code": "SRV-0001",
    "lines": [{"description": "Paket 20M — periode November 2026", "amount": "150000.00"}],
    "total_amount": "150000.00",
}


def test_render_pdf_deterministic_bytes():
    """Byte PDF identik antar render (rl_config.invariant=1)."""
    html = TEMPLATES[("internet_invoice", "1")](INVOICE_VALUES, "id")
    first = render_pdf(html)
    second = render_pdf(html)
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_render_pdf_magic_and_size():
    """PDF valid: diawali %PDF- dan tidak kosong (<1000 byte)."""
    data = render_pdf(TEMPLATES[("receipt", "1")](
        {
            "tenant_name": "RT RW Net Melati",
            "doc_number": "KWI-rtrw-aaaa000001-202611-0001",
            "customer_name": "Budi Santoso",
            "received_at": "2026-11-06",
            "method": "cash",
            "applies_to": [{"invoice_number": "INV-rtrw-aaaa000001-202611-0001", "amount": "150000.00"}],
            "amount": "150000.00",
            "credit": "0",
        },
        "id",
    ))
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000


def test_values_are_html_escaped():
    """Nilai pelanggan di-escape — <script> tidak pernah lolos ke HTML."""
    evil = dict(INVOICE_VALUES, customer_name="<script>alert(1)</script>")
    html = TEMPLATES[("internet_invoice", "1")](evil, "id")
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    # PDF tetap valid dari HTML yang berisi payload ter-escape.
    assert render_pdf(html).startswith(b"%PDF-")


@pytest.mark.parametrize(
    "html_fragment",
    [
        '<html><body><img src="http://x/y.png"/></body></html>',
        '<html><body><a href="file:///etc/passwd">x</a></body></html>',
        '<html><body><img src="//cdn/x"/></body></html>',
        '<html><body><img SRC="HTTPS://attacker/x"/></body></html>',
    ],
)
def test_assert_no_external_refs_rejects_remote_and_file(html_fragment):
    """Renderer terbatas jaringan/file: rujukan eksternal → 422 ApiError."""
    with pytest.raises(ApiError) as exc:
        assert_no_external_refs(html_fragment)
    assert exc.value.status_code == 422
    assert exc.value.field_errors["resource"][0]["code"] == "external_forbidden"


def test_assert_no_external_refs_accepts_pure_builtin_html():
    """HTML bawaan templat lolos pemeriksaan."""
    assert_no_external_refs(TEMPLATES[("internet_invoice", "1")](INVOICE_VALUES, "en"))


def test_format_idr_regional_rules():
    """I18N-03: Rp1.500.000 (id) / IDR 1,500,000 (en); sen hanya bila ada."""
    assert format_idr("1500000.00", "id") == "Rp1.500.000"
    assert format_idr("1500000.50", "id") == "Rp1.500.000,50"
    assert format_idr("1500000.05", "id") == "Rp1.500.000,05"
    assert format_idr("1500000.00", "en") == "IDR 1,500,000"
    assert format_idr("1500000.50", "en") == "IDR 1,500,000.50"
    assert format_idr("0.00", "id") == "Rp0"
    assert format_idr("0.00", "en") == "IDR 0"
    # Uang sebagai Decimal (tidak pernah float) memberi hasil sama.
    assert format_idr(Decimal("1500000.00"), "id") == "Rp1.500.000"


def test_format_date_and_period_catalog_months():
    """Bulan dari kunci doc.month.*; periode memakai akhir inklusif."""
    assert format_date(date(2026, 10, 11), "id") == "11 Oktober 2026"
    assert format_date(date(2026, 10, 11), "en") == "11 October 2026"
    assert format_date("2026-12-31", "id") == "31 Desember 2026"
    assert format_date("2026-12-31", "en") == "31 December 2026"
    # end eksklusif 2026-12-01 → akhir inklusif 30 November 2026.
    assert format_period("2026-11-01", "2026-12-01", "id") == "1 November 2026 – 30 November 2026"
    assert format_period(date(2026, 1, 1), date(2026, 2, 1), "en") == "1 January 2026 – 31 January 2026"


def test_invoice_html_labels_catalog_driven():
    """Label dari katalog: id "Jatuh Tempo"/"Invoice Internet"; en padanan."""
    html_id = TEMPLATES[("internet_invoice", "1")](INVOICE_VALUES, "id")
    assert "Jatuh Tempo" in html_id
    assert "Invoice Internet" in html_id
    assert "Dokumen ini diterbitkan melalui MicroTix" in html_id
    html_en = TEMPLATES[("internet_invoice", "1")](INVOICE_VALUES, "en")
    assert "Due Date" in html_en
    assert "Internet Invoice" in html_en
    assert "This document was issued through MicroTix" in html_en


def test_receipt_html_labels_catalog_driven():
    """Kwitansi: label katalog + metode dilokalkan; kredit hanya bila ada."""
    values = {
        "tenant_name": "RT RW Net Melati",
        "doc_number": "KWI-rtrw-aaaa000001-202611-0001",
        "customer_name": "Budi Santoso",
        "received_at": "2026-11-06",
        "method": "cash",
        "applies_to": [{"invoice_number": "INV-rtrw-aaaa000001-202611-0001", "amount": "150000.00"}],
        "amount": "150000.00",
        "credit": "0",
    }
    html_id = TEMPLATES[("receipt", "1")](values, "id")
    assert "Kwitansi Pembayaran" in html_id
    assert "Diterima Dari" in html_id
    assert "Tunai" in html_id  # doc.payment.cash (id)
    assert "Terima kasih atas pembayaran Anda." in html_id
    # Kredit nol: baris kredit tidak dirender.
    assert "Kredit belum dialokasikan" not in html_id

    html_en = TEMPLATES[("receipt", "1")](dict(values, credit="2500.00", method="bank_transfer"), "en")
    assert "Payment Receipt" in html_en
    assert "Bank transfer" in html_en  # doc.payment.bank_transfer (en)
    assert "Unallocated credit" in html_en
    assert "IDR 2,500" in html_en


def test_latest_template_version_and_unregistered_kind():
    """Versi terbaru dari registry; kind tanpa templat → 404 ApiError."""
    assert latest_template_version("internet_invoice") == "1"
    assert latest_template_version("receipt") == "1"
    for kind in ("saas_invoice", "report", "tidak_ada"):
        with pytest.raises(ApiError) as exc:
            latest_template_version(kind)
        assert exc.value.status_code == 404


def test_resolve_locale_fallback_chain():
    """I18N-01: diminta → induk (en-GB → en) → id."""
    assert resolve_locale("id") == "id"
    assert resolve_locale("en") == "en"
    assert resolve_locale("en-GB") == "en"
    assert resolve_locale("id-ID") == "id"
    assert resolve_locale("fr") == "id"
    assert resolve_locale("") == "id"


def test_renderer_policy_denies_remote_and_local():
    """Defense-in-depth: kebijakan renderer menolak fetch jaringan + file."""
    policy = rendering._RENDERER_POLICY
    with pytest.raises(Exception, match="remote resources are not allowed"):
        policy.check_url("http://example.com/logo.png")
    with pytest.raises(Exception):
        policy.check_path("/etc/passwd")
