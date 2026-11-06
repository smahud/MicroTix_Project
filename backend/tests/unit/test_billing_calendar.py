"""Tes unit matematika kalender billing (BIL-02; AC-BIL) — murni tanpa DB.

Skenario wajib (AC-BIL): 29/30/31 hari, tahun kabisat, prorata deterministik,
batas zona waktu (konversi hari-ini; fungsi kalender murni — konversi zona
diuji di tests/integration/test_billing_flow.py), clamp due_day, jangkar
anniversary non-drift, kebijakan periode pertama.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from domains.billing import calendar

pytestmark = pytest.mark.unit

D = Decimal


class TestAddMonths:
    def test_clamp_end_of_month(self):
        assert calendar.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
        assert calendar.add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)  # kabisat
        assert calendar.add_months(date(2026, 1, 31), 2) == date(2026, 3, 31)  # non-drift
        assert calendar.add_months(date(2026, 3, 31), 1) == date(2026, 4, 30)

    def test_normal_month(self):
        assert calendar.add_months(date(2026, 11, 6), 1) == date(2026, 12, 6)
        assert calendar.add_months(date(2026, 12, 6), 1) == date(2027, 1, 6)
        assert calendar.add_months(date(2026, 11, 6), -1) == date(2026, 10, 6)


class TestPeriodBounds:
    def test_fixed_monthly_first_partial(self):
        # Aktivasi 15 Nov 2026 → periode pertama [15 Nov, 1 Des)
        assert calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, date(2026, 11, 15), 0) == (
            date(2026, 11, 15),
            date(2026, 12, 1),
        )

    def test_fixed_monthly_subsequent_calendar_months(self):
        start = date(2026, 11, 15)
        assert calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, start, 1) == (date(2026, 12, 1), date(2027, 1, 1))

    def test_fixed_monthly_february_lengths(self):
        # Feb 2026 (28 hari), Feb 2027 (28), Feb 2028 (29 kabisat) — AC-BIL 29/30/31
        ps, pe = calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, date(2026, 1, 1), 1)
        assert (pe - ps).days == 28
        ps, pe = calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, date(2027, 1, 1), 1)
        assert (pe - ps).days == 28
        ps, pe = calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, date(2028, 1, 1), 1)
        assert (pe - ps).days == 29
        ps, pe = calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, date(2026, 4, 1), 0)
        assert (pe - ps).days == 30
        ps, pe = calendar.period_bounds(calendar.CYCLE_FIXED_MONTHLY, date(2026, 5, 1), 0)
        assert (pe - ps).days == 31

    def test_anniversary_anchor(self):
        start = date(2026, 1, 31)
        assert calendar.period_bounds(calendar.CYCLE_ANNIVERSARY, start, 0) == (date(2026, 1, 31), date(2026, 2, 28))
        assert calendar.period_bounds(calendar.CYCLE_ANNIVERSARY, start, 1) == (date(2026, 2, 28), date(2026, 3, 31))
        assert calendar.period_bounds(calendar.CYCLE_ANNIVERSARY, start, 2) == (date(2026, 3, 31), date(2026, 4, 30))

    def test_unknown_cycle_rejected(self):
        with pytest.raises(ValueError):
            calendar.period_bounds("weekly", date(2026, 1, 1), 0)


class TestFirstPeriodAmount:
    def test_full_policy(self):
        assert calendar.first_period_amount(calendar.POLICY_FULL, D("300000"), date(2026, 11, 15), date(2026, 12, 1)) == D("300000")

    def test_prorata_daily_ceil_100(self):
        # Aktivasi 15 Nov (bulan 30 hari): hari aktif = 16 → 300000×16/30 = 160000 (tepat)
        assert calendar.first_period_amount(
            calendar.POLICY_PRORATA_DAILY, D("300000"), date(2026, 11, 15), date(2026, 12, 1)
        ) == D("160000")
        # 150000×17/30 = 85000 → tepat; nilai tak bulat dibulatkan ke atas ke Rp100:
        # 250000×16/30 = 133333,33 → ceil Rp100 = 133400
        assert calendar.first_period_amount(
            calendar.POLICY_PRORATA_DAILY, D("250000"), date(2026, 11, 15), date(2026, 12, 1)
        ) == D("133400")

    def test_prorata_feb_kabisat(self):
        # Aktivasi 20 Feb 2024 (kabisat, 29 hari): hari aktif = 10 → 290000×10/29 = 100000
        assert calendar.first_period_amount(
            calendar.POLICY_PRORATA_DAILY, D("290000"), date(2024, 2, 20), date(2024, 3, 1)
        ) == D("100000")

    def test_free_until_next_period(self):
        assert calendar.first_period_amount(
            calendar.POLICY_FREE_UNTIL_NEXT_PERIOD, D("300000"), date(2026, 11, 15), date(2026, 12, 1)
        ) == 0

    def test_first_day_of_month_full_charge_prorata(self):
        # Aktivasi tepat tanggal 1: seluruh bulan teraktivasi → prorata = harga penuh
        assert calendar.first_period_amount(
            calendar.POLICY_PRORATA_DAILY, D("310000"), date(2026, 1, 1), date(2026, 2, 1)
        ) == D("310000")

    def test_unknown_policy_rejected(self):
        with pytest.raises(ValueError):
            calendar.first_period_amount("weird", D("1"), date(2026, 1, 1), date(2026, 2, 1))


class TestClampDueDay:
    def test_after_default_same_month(self):
        # due default 3 Nov, due_day 10 → 10 Nov
        assert calendar.clamp_due_day(date(2026, 11, 3), 10) == date(2026, 11, 10)

    def test_before_default_next_month(self):
        # due default 15 Nov, due_day 10 → 10 Des
        assert calendar.clamp_due_day(date(2026, 11, 15), 10) == date(2026, 12, 10)

    def test_clamp_end_of_month(self):
        # due default 28 Feb 2026 (28 hari), due_day 31 → clamp 28 Feb ≥ default → 28 Feb
        assert calendar.clamp_due_day(date(2026, 2, 28), 31) == date(2026, 2, 28)
        # due default 27 Feb 2026, due_day 30 → clamp 28 Feb ≥ 27 → 28 Feb
        assert calendar.clamp_due_day(date(2026, 2, 27), 30) == date(2026, 2, 28)
        # due default 29 Feb 2024 (kabisat), due_day 30 → clamp 29 Feb = 29 Feb ≥ 29 → 29 Feb
        assert calendar.clamp_due_day(date(2024, 2, 29), 30) == date(2024, 2, 29)
        # due default 30 Nov, due_day 31 → clamp 30 Nov ≥ 30 → 30 Nov
        assert calendar.clamp_due_day(date(2026, 11, 30), 31) == date(2026, 11, 30)


class TestIssueAndDueDates:
    def test_prepaid_issue_lead_and_due(self):
        # Periode 1 Des; terbit pada hari trigger (start-7 = 24 Nov): due = start
        issue, due = calendar.issue_and_due_dates(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID, due_day=None,
            period_start=date(2026, 12, 1), period_end=date(2027, 1, 1), today=date(2026, 11, 24),
        )
        assert issue == date(2026, 11, 24)
        assert due == date(2026, 12, 1)
        # Terbit terlambat (setelah jendela): issue = hari scheduler berjalan
        issue, due = calendar.issue_and_due_dates(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID, due_day=None,
            period_start=date(2026, 12, 1), period_end=date(2027, 1, 1), today=date(2026, 11, 30),
        )
        assert issue == date(2026, 11, 30)
        assert due == date(2026, 12, 1)

    def test_prepaid_issue_late_due_not_before_issue(self):
        # Terbit terlambat (today > start): due = issue, tidak sebelum issue (BIL-02)
        issue, due = calendar.issue_and_due_dates(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID, due_day=None,
            period_start=date(2026, 11, 1), period_end=date(2026, 12, 1), today=date(2026, 11, 15),
        )
        assert due == date(2026, 11, 15) == issue

    def test_postpaid_issue_end_plus_due(self):
        issue, due = calendar.issue_and_due_dates(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_POSTPAID, due_day=None,
            period_start=date(2026, 11, 1), period_end=date(2026, 12, 1), today=date(2026, 12, 1),
        )
        assert issue == date(2026, 12, 1)
        assert due == date(2026, 12, 8)

    def test_postpaid_due_day_clamp(self):
        # postpaid issue 1 Des + 7 = 8 Des; due_day 10 → 10 Des
        _, due = calendar.issue_and_due_dates(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_POSTPAID, due_day=10,
            period_start=date(2026, 11, 1), period_end=date(2026, 12, 1), today=date(2026, 12, 1),
        )
        assert due == date(2026, 12, 10)
        # issue 28 Nov + 7 = 5 Des; due_day 3 → clamp pertama ≥ 5 → 3 Jan 2027
        _, due = calendar.issue_and_due_dates(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_POSTPAID, due_day=3,
            period_start=date(2026, 11, 1), period_end=date(2026, 11, 28), today=date(2026, 11, 28),
        )
        assert due == date(2027, 1, 3)

    def test_unknown_timing_rejected(self):
        with pytest.raises(ValueError):
            calendar.issue_and_due_dates(
                cycle=calendar.CYCLE_FIXED_MONTHLY, timing="later", due_day=None,
                period_start=date(2026, 11, 1), period_end=date(2026, 12, 1), today=date(2026, 11, 1),
            )


class TestDuePeriodIndices:
    def test_prepaid_lead_window(self):
        # Layanan mulai 1 Des → p0=[1 Des,1 Jan), trigger = 24 Nov
        assert calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID,
            service_start=date(2026, 12, 1), last_index_issued=-1, today=date(2026, 11, 20),
        ) == []
        # today 24 Nov (tepat trigger) → layak
        assert calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID,
            service_start=date(2026, 12, 1), last_index_issued=-1, today=date(2026, 11, 24),
        ) == [0]

    def test_prepaid_continues_from_last_index(self):
        # Periode 0 (Des) sudah diterbitkan → p1 trigger 25 Des; 24 Nov → kosong
        assert calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID,
            service_start=date(2026, 12, 1), last_index_issued=0, today=date(2026, 11, 24),
        ) == []
        # 25 Des → p1 layak
        assert calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID,
            service_start=date(2026, 12, 1), last_index_issued=0, today=date(2026, 12, 25),
        ) == [1]

    def test_prepaid_catchup_backlog(self):
        # Scheduler mati 3 bulan → semua periode lampau diterbitkan (catch-up);
        # today 23 Nov < trigger p4 (24 Nov) → p4 Des belum
        indices = calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_PREPAID,
            service_start=date(2026, 8, 1), last_index_issued=-1, today=date(2026, 11, 23),
        )
        assert indices == [0, 1, 2, 3]  # Agu, Sep, Okt, Nov

    def test_postpaid_only_finished_periods(self):
        assert calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_POSTPAID,
            service_start=date(2026, 11, 1), last_index_issued=-1, today=date(2026, 11, 30),
        ) == []
        assert calendar.due_period_indices(
            cycle=calendar.CYCLE_FIXED_MONTHLY, timing=calendar.TIMING_POSTPAID,
            service_start=date(2026, 11, 1), last_index_issued=-1, today=date(2026, 12, 1),
        ) == [0]

    def test_anniversary_monthly(self):
        # Jangkar 20 Sep: p0 [20 Sep,20 Okt), p1 [20 Okt,20 Nov), p2 [20 Nov,20 Des)
        # trigger prepaid p2 = 20 Nov - 7 = 13 Nov ≤ today 15 Nov → 3 periode layak
        indices = calendar.due_period_indices(
            cycle=calendar.CYCLE_ANNIVERSARY, timing=calendar.TIMING_PREPAID,
            service_start=date(2026, 9, 20), last_index_issued=-1, today=date(2026, 11, 15),
        )
        assert indices == [0, 1, 2]

    def test_unknown_timing_rejected(self):
        with pytest.raises(ValueError):
            calendar.due_period_indices(
                cycle=calendar.CYCLE_FIXED_MONTHLY, timing="later",
                service_start=date(2026, 1, 1), last_index_issued=-1, today=date(2026, 6, 1),
            )


class TestMoneyHelpers:
    def test_ceil_to_rupiah_100(self):
        assert calendar.ceil_to_rupiah_100(D("133333.33")) == D("133400")
        assert calendar.ceil_to_rupiah_100(D("160000")) == D("160000")
        assert calendar.ceil_to_rupiah_100(D("0.01")) == D("100")

    def test_round_money_half_up(self):
        assert calendar.round_money(D("1234.567")) == D("1234.57")
        assert calendar.round_money(D("1234.5")) == D("1234.50")


class TestLocaleChain:
    """Rantai bahasa dokumen (I18N-01 §2): pelanggan → tenant → id."""

    def test_customer_locale_wins(self):
        assert calendar.effective_locale("en", "id") == "en"

    def test_tenant_locale_fallback(self):
        assert calendar.effective_locale("", "en") == "en"

    def test_default_id(self):
        assert calendar.effective_locale("", "") == "id"
        assert calendar.effective_locale("  ", "  ") == "id"
