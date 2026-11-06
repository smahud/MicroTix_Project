"""Matematika periode & jatuh tempo penagihan (BIL-02) — murni, tanpa DB.

Aturan (docs/PRODUCT.md §BIL-02 + defaults.json):
- fixed_monthly: periode = bulan kalender; periode pertama dari tanggal
  aktivasi sampai awal bulan berikut (potongan parsial).
- anniversary: jangkar tanggal aktivasi; add_months non-drift (31 Jan →
  28 Feb → 31 Mar, dst. — index dihitung dari tanggal aktivasi asli).
- prepaid: issue = period_start - invoice.lead_prepaid_days (7, default
  approved-only), due = period_start, tidak sebelum tanggal issue.
- postpaid: issue = period_end (eksklusif, layanan selesai), due =
  issue + invoice.postpaid_due_days (7); due_day fixed_monthly memilih
  tanggal clamp pertama pada/selepas due default.
- first_period_policy: full | prorata_daily (ceil ke Rp100 terdekat,
  harga×hari_aktif/hari_kalender_bulan) | free_until_next_period (0).

Pengujian AC-BIL: 29/30/31 hari, tahun kabisat, batas zona waktu WIB/WITA/WIT
(konversi tanggal hari-ini di command; fungsi di sini murni kalender).
Semua hitungan uang memakai Decimal — tidak pernah float.
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

# defaults.json (approved_default_only): invoice.lead_prepaid_days=7,
# invoice.postpaid_due_days=7 — nilai kontrak; perubahan lewat registry
# memerlukan revisi bounds (bukan hardcode diam-diam di sini).
LEAD_PREPAID_DAYS = 7
POSTPAID_DUE_DAYS = 7

CYCLE_FIXED_MONTHLY = "fixed_monthly"
CYCLE_ANNIVERSARY = "anniversary"
TIMING_PREPAID = "prepaid"
TIMING_POSTPAID = "postpaid"
POLICY_FULL = "full"
POLICY_PRORATA_DAILY = "prorata_daily"
POLICY_FREE_UNTIL_NEXT_PERIOD = "free_until_next_period"

# Pengaman iterasi scheduler (50 tahun periode bulanan) — mencegah loop
# tak berbatas pada data tak masuk akal; bukan perilaku produk.
MAX_PERIODS_ITER = 600

CENT = Decimal("100")
TWO_PLACES = Decimal("0.01")


def ceil_to_rupiah_100(value: Decimal) -> Decimal:
    """Pembulatan ke atas ke Rp100 terdekat (BIL-02 prorata_daily)."""
    return (value / CENT).to_integral_value(rounding=ROUND_CEILING) * CENT


def add_months(anchor: date, months: int) -> date:
    """Tambah bulan kalender dengan clamp ke akhir bulan (non-drift: selalu
    dihitung dari anchor asli, mis. 31 Jan +1 = 28 Feb, +2 = 31 Mar)."""
    total = (anchor.year * 12 + anchor.month - 1) + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    last_day = _cal.monthrange(year, month)[1]
    return date(year, month, min(anchor.day, last_day))


def period_bounds(cycle: str, service_start: date, index: int) -> tuple[date, date]:
    """Batas periode ke-`index` (0 = periode pertama, [start, end) eksklusif).

    fixed_monthly: periode 0 parsial [start, awal bulan berikut); sesudahnya
    bulan kalender penuh. anniversary: [add_months(start,n), add_months(start,n+1)).
    """
    if cycle == CYCLE_FIXED_MONTHLY:
        first_next = add_months(date(service_start.year, service_start.month, 1), 1)
        if index == 0:
            return service_start, first_next
        return add_months(first_next, index - 1), add_months(first_next, index)
    if cycle == CYCLE_ANNIVERSARY:
        return add_months(service_start, index), add_months(service_start, index + 1)
    raise ValueError(f"billing_cycle tidak dikenal: {cycle!r}")


def first_period_amount(policy: str, monthly_price: Decimal, start: date, first_end: date) -> Decimal:
    """Jumlah line langganan pada periode pertama (kebijakan BIL-02).

    full: harga penuh. prorata_daily: harga × hari_aktif / hari_kalender_bulan
    (bulan aktivasi), dibulatkan ke atas ke Rp100. free_until_next_period: 0.
    """
    if policy == POLICY_FULL:
        return monthly_price
    if policy == POLICY_PRORATA_DAILY:
        days_active = (first_end - start).days
        days_in_month = _cal.monthrange(start.year, start.month)[1]
        if days_active <= 0:
            return Decimal("0")
        return ceil_to_rupiah_100(monthly_price * Decimal(days_active) / Decimal(days_in_month))
    if policy == POLICY_FREE_UNTIL_NEXT_PERIOD:
        return Decimal("0")
    raise ValueError(f"first_period_policy tidak dikenal: {policy!r}")


def clamp_due_day(due_default: date, due_day: int) -> date:
    """Tanggal clamp pertama pada/selepas due default dengan hari = due_day
    (clamp ke akhir bulan pendek). BIL-02: hanya berlaku fixed_monthly."""
    candidate = date(due_default.year, due_default.month, min(due_day, _cal.monthrange(due_default.year, due_default.month)[1]))
    if candidate >= due_default:
        return candidate
    nxt = add_months(date(due_default.year, due_default.month, 1), 1)
    return date(nxt.year, nxt.month, min(due_day, _cal.monthrange(nxt.year, nxt.month)[1]))


def issue_and_due_dates(
    *,
    cycle: str,
    timing: str,
    due_day: int | None,
    period_start: date,
    period_end: date,
    today: date,
) -> tuple[date, date]:
    """Tanggal issue & jatuh tempo sebuah periode (BIL-02).

    prepaid: issue = max(today, period_start - LEAD)? — TIDAK: issue adalah
    tanggal terbit aktual (hari scheduler berjalan), tetapi minimal tanggal
    trigger (start - lead); due = period_start, dan tidak sebelum issue.
    postpaid: issue = period_end (periode selesai); due = issue + 7 hari,
    lalu clamp due_day bila fixed_monthly.
    """
    if timing == TIMING_PREPAID:
        earliest_issue = period_start - timedelta(days=LEAD_PREPAID_DAYS)
        issue_date = max(today, earliest_issue)
        due = period_start if period_start >= issue_date else issue_date
        return issue_date, due
    if timing == TIMING_POSTPAID:
        issue_date = period_end
        due = issue_date + timedelta(days=POSTPAID_DUE_DAYS)
        if cycle == CYCLE_FIXED_MONTHLY and due_day:
            due = clamp_due_day(due, due_day)
        return issue_date, due
    raise ValueError(f"timing tidak dikenal: {timing!r}")


def due_period_indices(
    *,
    cycle: str,
    timing: str,
    service_start: date,
    last_index_issued: int,
    today: date,
) -> list[int]:
    """Indeks periode (lanjutan dari last_index_issued+1) yang wajib diterbitkan
    pada `today` (tanggal tenant-lokal). Scheduler idempoten: periode yang
    sudah diterbitkan tidak diulang (lanjutan murni dari indeks terakhir).

    prepaid: periode layak terbit bila today >= period_start - LEAD (BIL-02
    "terbit 7 hari sebelum periode mulai"). postpaid: layak bila today >=
    period_end (layanan selesai). Catch-up: scheduler yang lama tidak jalan
    menerbitkan semua periode terutang berjalan — perilaku benar, bukan
    duplikat (UNIQUE period tetap menjaga AC-BIL).
    """
    indices: list[int] = []
    index = last_index_issued + 1
    while len(indices) < MAX_PERIODS_ITER:
        start, end = period_bounds(cycle, service_start, index)
        if timing == TIMING_PREPAID:
            if today < start - timedelta(days=LEAD_PREPAID_DAYS):
                break
        elif timing == TIMING_POSTPAID:
            if today < end:
                break
        else:
            raise ValueError(f"timing tidak dikenal: {timing!r}")
        indices.append(index)
        index += 1
    return indices


def effective_locale(customer_locale: str, tenant_locale: str) -> str:
    """Rantai bahasa dokumen pelanggan (I18N-01 §2): pelanggan → tenant → id."""
    if customer_locale and customer_locale.strip():
        return customer_locale.strip()
    if tenant_locale and tenant_locale.strip():
        return tenant_locale.strip()
    return "id"


def round_money(value: Decimal) -> Decimal:
    """Pembulatan uang 2 desimal HALF_UP (diskon persen → nominal)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
