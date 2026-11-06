"""Render HTML→PDF deterministik untuk dokumen terbit (TK-109).

ARCHITECTURE.md §1 baris "Dokumen": HTML→PDF dengan renderer dibatasi
jaringan/file dan resource. Templat hanya HTML bawaan (tanpa import CSS,
gambar, atau URL eksternal); dua lapis pertahanan:
1. assert_no_external_refs menolak HTML dengan rujukan src/href eksternal.
2. ResourceAccessPolicy xhtml2pdf menolak semua fetch jaringan dan semua
   baca file lokal selama render (defense-in-depth — regex hanyalah lapis
   pertama; @font-face/url() jalur lain ditutup oleh kebijakan renderer).

rl_config.invariant = 1 (module import) membuat PDF byte-deterministik:
metadata tanggal fixed — reprint/cetak ulang dokumen yang sama menghasilkan
byte identik (sha256 stabil untuk audit integritas).

I18N: seluruh label manusia dari katalog (domains.i18n.catalogs.message)
— tidak ada teks manusia yang di-hardcode (I18N.md §1.2). Uang selalu
Decimal (I18N-03: tidak pernah float), format IDR: "Rp1.500.000" (id) /
"IDR 1,500,000" (en); suffix ",00"/".00" hanya bila ada sen.
"""
from __future__ import annotations

import html as _html
import io
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Callable

from reportlab import rl_config
from xhtml2pdf import pisa
from xhtml2pdf.config.resources import ResourceAccessPolicy

from domains.common.envelope import ApiError
from domains.i18n.catalogs import message

# Byte-deterministik (di-set saat import modul, sebelum render pertama):
# tanggal metadata PDF tetap — reprint dokumen yang sama menghasilkan byte
# identik (sha256 stabil untuk audit integritas).
rl_config.invariant = 1

# Renderer dibatasi jaringan/file (ARCHITECTURE §1 Dokumen):
# - allow_remote=False: tidak ada fetch http/https apa pun selama render.
# - base_dir=None: baca file lokal ditolak mutlak (bukan dibatasi cwd).
# data: URI bagian dari dokumen sendiri — tetap boleh (tidak menyentuh jaringan).
_RENDERER_POLICY = ResourceAccessPolicy(allow_remote=False, base_dir=None)

# Atribut sumber daya yang diperiksa assert_no_external_refs.
_EXTERNAL_REF_RE = re.compile(
    r"""(?:src|href)\s*=\s*(?:"[^"]*(?:https?://|//|file:)|'[^']*(?:https?://|//|file:)|(?:https?://|//|file:))""",
    re.IGNORECASE,
)

ZERO = Decimal("0")
_CENT = Decimal("0.01")


def escape(value) -> str:
    """Escape HTML untuk nilai dokumen (input tidak tepercaya)."""
    return _html.escape(str(value), quote=True)


def _dec(value) -> Decimal:
    """Konversi aman ke Decimal — uang tidak pernah float (I18N-03)."""
    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return ZERO
    return Decimal(str(value))


def format_idr(amount, locale: str) -> str:
    """Format IDR sesuai I18N-03: "Rp1.500.000" (id) / "IDR 1,500,000" (en).

    Pemisah ribuan "." (id) / "," (en); suffix ",00"/".00" hanya bila sen != 0.
    """
    value = _dec(amount).quantize(_CENT)
    sign = "-" if value.is_signed() else ""
    whole, cents_dec = divmod(abs(value), Decimal("1"))
    whole_str = f"{int(whole):,}"  # grup ribuan "," bawaan; id mengganti ke "."
    cents = int((cents_dec / _CENT).to_integral_value())
    if locale == "en":
        return f"{sign}IDR {whole_str}{f'.{cents:02d}' if cents else ''}"
    return f"{sign}Rp{whole_str.replace(',', '.')}{f',{cents:02d}' if cents else ''}"


def _as_date(value) -> date | None:
    """Terima date/datetime/ISO string → date (snapshot JSON memakai ISO)."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        return datetime.fromisoformat(text).date()


def format_date(value, locale: str) -> str:
    """Tanggal penuh "11 Oktober 2026" (id) / "11 October 2026" (en) — I18N-03."""
    d = _as_date(value)
    if d is None:
        return ""
    return f"{d.day} {message(f'doc.month.{d.month}', locale)} {d.year}"


def format_period(start, end_exclusive, locale: str) -> str:
    """Periode layanan "{start} – {end inklusif}" (end eksklusif − 1 hari)."""
    d_start = _as_date(start)
    d_end = _as_date(end_exclusive)
    if d_start is None or d_end is None:
        return ""
    end_inclusive = d_end - timedelta(days=1)
    return f"{format_date(d_start, locale)} – {format_date(end_inclusive, locale)}"


# ---------------------------------------------------------------------------
# Templat dokumen — (kind, template_version) → builder(values, locale) → HTML.
# SAAS_INVOICE/REPORT belum terdaftar: tidak ada templat jujur untuknya —
# services menolak dengan error.not_found (anti API-palsu, ARCHITECTURE §5).
# ---------------------------------------------------------------------------

_CSS = """<style type="text/css">
body { font-family: Helvetica; font-size: 11pt; }
td, th { border: 0.5pt solid #888888; padding: 4px 8px; }
.meta td { border: none; padding: 2px 8px; }
</style>"""


def _meta_row(label: str, value: str) -> str:
    return f'<tr><td width="38%">{escape(label)}</td><td><b>{value}</b></td></tr>'


def _html_doc(lang: str, title: str, body: str) -> str:
    return (
        f'<html lang="{escape(lang)}"><head><meta charset="utf-8"/>{_CSS}'
        f"<title>{escape(title)}</title></head><body>{body}</body></html>"
    )


def _build_internet_invoice_v1(values: dict, locale: str) -> str:
    """Invoice internet v1 — BIL-01 (header, jatuh tempo, baris, total)."""
    values = values or {}

    def m(key: str) -> str:
        return message(key, locale)

    rows = [_meta_row(m("doc.invoice.number"), escape(values.get("doc_number", "")))]
    if _as_date(values.get("issued_date")):
        rows.append(_meta_row(m("doc.invoice.issued"), escape(format_date(values["issued_date"], locale))))
    if _as_date(values.get("due_date")):
        rows.append(_meta_row(m("doc.invoice.due"), escape(format_date(values["due_date"], locale))))
    if values.get("customer_name"):
        rows.append(_meta_row(m("doc.invoice.bill_to"), escape(values["customer_name"])))
    if values.get("service_code"):
        rows.append(_meta_row(m("doc.invoice.service"), escape(values["service_code"])))

    lines = values.get("lines") or []
    line_rows = "".join(
        f'<tr><td>{escape(line.get("description", ""))}</td>'
        f'<td align="right">{escape(format_idr(line.get("amount"), locale))}</td></tr>'
        for line in lines
    )
    total = format_idr(values.get("total_amount"), locale)
    body = (
        f'<h1>{escape(values.get("tenant_name", ""))}</h1>'
        f'<h2>{escape(m("doc.invoice.title"))}</h2>'
        f'<table class="meta">{"".join(rows)}</table>'
        f'<table><tr><th>{escape(m("doc.invoice.description"))}</th>'
        f'<th align="right">{escape(m("doc.invoice.amount"))}</th></tr>'
        f"{line_rows}"
        f'<tr><td><b>{escape(m("doc.invoice.total"))}</b></td>'
        f'<td align="right"><b>{escape(total)}</b></td></tr></table>'
        f'<p>{escape(m("doc.footer.generated"))}</p>'
    )
    return _html_doc(locale, m("doc.invoice.title"), body)


def _build_receipt_v1(values: dict, locale: str) -> str:
    """Kwitansi pembayaran v1 — BIL-08 (diterima dari, metode, diterapkan)."""
    values = values or {}

    def m(key: str) -> str:
        return message(key, locale)

    rows = [_meta_row(m("doc.receipt.number"), escape(values.get("doc_number", "")))]
    if values.get("customer_name"):
        rows.append(_meta_row(m("doc.receipt.received_from"), escape(values["customer_name"])))
    if _as_date(values.get("received_at")):
        rows.append(_meta_row(m("doc.receipt.received_at"), escape(format_date(values["received_at"], locale))))
    if values.get("method"):
        rows.append(_meta_row(m("doc.receipt.method"), escape(message(f"doc.payment.{values['method']}", locale))))

    applies_to = values.get("applies_to") or []
    apply_rows = "".join(
        f'<tr><td>{escape(entry.get("invoice_number", ""))}</td>'
        f'<td align="right">{escape(format_idr(entry.get("amount"), locale))}</td></tr>'
        for entry in applies_to
    )
    amount = format_idr(values.get("amount"), locale)
    body = (
        f'<h1>{escape(values.get("tenant_name", ""))}</h1>'
        f'<h2>{escape(m("doc.receipt.title"))}</h2>'
        f'<table class="meta">{"".join(rows)}</table>'
        f'<table><tr><th>{escape(m("doc.invoice.number"))}</th>'
        f'<th align="right">{escape(m("doc.invoice.amount"))}</th></tr>'
        f"{apply_rows}"
        f'<tr><td><b>{escape(m("doc.receipt.amount"))}</b></td>'
        f'<td align="right"><b>{escape(amount)}</b></td></tr></table>'
    )
    if _dec(values.get("credit")) != ZERO:
        body += (
            f'<p>{escape(m("doc.receipt.credit"))}: '
            f'{escape(format_idr(values.get("credit"), locale))}</p>'
        )
    body += f'<p>{escape(m("doc.receipt.thanks"))}</p><p>{escape(m("doc.footer.generated"))}</p>'
    return _html_doc(locale, m("doc.receipt.title"), body)


TEMPLATES: dict[tuple[str, str], Callable[[dict, str], str]] = {
    ("internet_invoice", "1"): _build_internet_invoice_v1,
    ("receipt", "1"): _build_receipt_v1,
}


def latest_template_version(kind: str) -> str:
    """Versi templat tertinggi yang terdaftar untuk kind (versi "1","2",...)."""
    versions = [version for (k, version) in TEMPLATES if k == kind]
    if not versions:
        # Kind tanpa templat jujur (saas_invoice/report pada M6 ini) → 404,
        # bukan API palsu (ARCHITECTURE §5).
        raise ApiError.not_found()
    return max(versions)


def assert_no_external_refs(html_text: str) -> None:
    """Tolak rujukan sumber daya eksternal pada HTML (renderer terbatas)."""
    if _EXTERNAL_REF_RE.search(html_text):
        raise ApiError.validation(
            {
                "resource": [
                    {
                        "code": "external_forbidden",
                        "message": "Dokumen tidak boleh memuat sumber daya eksternal",
                    }
                ]
            }
        )


def render_pdf(html_text: str) -> bytes:
    """Render HTML menjadi byte PDF deterministik (awalan b"%PDF-").

    Gagal render (exception/err pisa/PDF tidak terbentuk) → ApiError 500
    error.document_render — jangan pernah menyerahkan PDF setengah jadi.
    """
    assert_no_external_refs(html_text)
    dest = io.BytesIO()
    try:
        context = pisa.CreatePDF(
            io.BytesIO(html_text.encode("utf-8")),
            dest=dest,
            resource_policy=_RENDERER_POLICY,
        )
    except Exception:
        raise ApiError(
            code="document_render_failed",
            message_key="error.document_render",
            status_code=500,
        ) from None
    data = dest.getvalue()
    if getattr(context, "err", 0) or not data.startswith(b"%PDF-"):
        # Error parse pisa dihitung jujur — jangan serahkan PDF setengah jadi.
        raise ApiError(
            code="document_render_failed",
            message_key="error.document_render",
            status_code=500,
        )
    return data
