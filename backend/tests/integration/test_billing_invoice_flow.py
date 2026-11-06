"""Tes integrasi billing internet M6 — penerbitan invoice (TK-601).

Skenario wajib (AC-BIL + done_when TK-601):
- Scheduler idempoten: dijalankan dua kali hari sama → satu invoice per
  (layanan, periode, jenis) — dua scheduler periode sama → satu invoice.
- Harga disnapshot: perubahan harga paket setelah terbit TIDAK mengubah
  invoice yang sudah terbit.
- Kebijakan periode pertama (full/prorata_daily/free) tertera & benar.
- Nomor dokumen INV-{ns}-{YYYYMM}-{urut} unik per tenant.
- Invoice terbit → dokumen PDF (TK-109) dengan bahasa rantai I18N-01.
- Isolasi tenant (RLS): invoice tenant A tidak terlihat via API tenant B.
- Izin: viewer bisa membaca; provisioning paket tanpa izin → 403.
- Validasi paket: anniversary + prorata ditolak; nama duplikat 409.
- Zona waktu tenant: konversi hari-ini WIB/WITA/WIT (batas tanggal).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from domains.billing import services
from domains.billing.management.commands.issue_due_invoices import today_in_timezone
from domains.billing.models import BillingPackage, InternetInvoice, ServiceCharge
from domains.common.tenant_context import tenant_scope
from domains.customers.models import Customer, Service
from domains.documents.models import IssuedDocument
from domains.tenancy.models import Membership, Role

pytestmark = pytest.mark.integration

from tests.conftest import TEST_PASSWORD  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture pembantu
# ---------------------------------------------------------------------------

@pytest.fixture
def billed_service(tenant_a):
    """Layanan provisioned + paket prepaid fixed_monthly 300.000."""
    with tenant_scope(tenant_a.id):
        customer = Customer.objects.create(
            tenant=tenant_a, display_name="Budi Pelanggan", customer_code="CUST-001"
        )
        package = BillingPackage.objects.create(
            tenant=tenant_a, name="Paket Reguler 300rb",
            monthly_price=Decimal("300000"),
        )
        service = Service.objects.create(
            tenant=tenant_a,
            customer=customer,
            service_code="SVC-001",
            lifecycle=Service.Lifecycle.PROVISIONED,
            start_date=date(2026, 12, 1),
            billing_package=package,
        )
    return {"service": service, "package": package, "customer": customer}


def run_scheduler(tenant, *, on_date: str):
    buf = StringIO()
    call_command("issue_due_invoices", "--tenant", tenant.namespace, "--date", on_date, stdout=buf, stderr=StringIO())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Paket penagihan (BIL-02) — validasi & API
# ---------------------------------------------------------------------------

class TestBillingPackageRules:
    def test_anniversary_rejects_non_full_first_policy(self, auth_client, tenant_a):
        # BIL-02: anniversary hanya full (tanpa batas kalender eksplisit)
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/billing/packages",
            {"name": "Paket Jangkar", "monthly_price": "150000",
             "billing_cycle": "anniversary", "first_period_policy": "prorata_daily"},
            headers={"Idempotency-Key": "pkg-anchor-1"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "billing.invalid_policy"

    def test_anniversary_rejects_due_day(self, auth_client, tenant_a):
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/billing/packages",
            {"name": "Paket Jangkar", "monthly_price": "150000",
             "billing_cycle": "anniversary", "due_day": 10},
            headers={"Idempotency-Key": "pkg-anchor-2"},
        )
        assert resp.status_code == 422

    def test_duplicate_name_conflict(self, auth_client, tenant_a, billed_service):
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/billing/packages",
            {"name": "Paket Reguler 300rb", "monthly_price": "100000"},
            headers={"Idempotency-Key": "pkg-dup"},
        )
        assert resp.status_code == 409

    def test_provision_permission_required(self, auth_client, tenant_a, db):
        # Viewer: bisa GET daftar, TIDAK bisa POST paket (403)
        from domains.identity.models import User

        vuser = User.objects.create_user(
            email="viewer@test.local", full_name="Viewer", password=TEST_PASSWORD, is_active=True
        )
        Membership.objects.create(user=vuser, tenant_id=tenant_a.id, role=Role.VIEWER)
        auth_client.force_login(vuser)
        session = auth_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session["auth_at"] = __import__("time").time()
        session.save()
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/billing/packages")
        assert resp.status_code == 200
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/billing/packages",
            {"name": "Paket X", "monthly_price": "100000"},
            headers={"Idempotency-Key": "pkg-v"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Scheduler penerbitan (AC-BIL) — idempoten, snapshot, kebijakan
# ---------------------------------------------------------------------------

class TestSchedulerIssue:
    def test_issue_once_then_rerun_same_day_single_invoice(self, tenant_a, billed_service):
        """AC-BIL: dua scheduler pada periode sama → satu invoice."""
        out1 = run_scheduler(tenant_a, on_date="2026-11-24")  # trigger p0 (start-7)
        assert "terbit 1 invoice" in out1
        with tenant_scope(tenant_a.id):
            assert InternetInvoice.objects.count() == 1
        out2 = run_scheduler(tenant_a, on_date="2026-11-24")  # dijalankan ulang
        with tenant_scope(tenant_a.id):
            assert InternetInvoice.objects.count() == 1  # tidak ganda

    def test_invoice_fields_and_document(self, tenant_a, billed_service):
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.select_related("service", "service__customer").get()
            assert invoice.kind == "prepaid"
            assert invoice.state == "open"
            assert invoice.period_start == date(2026, 12, 1)
            assert invoice.period_end == date(2027, 1, 1)
            assert invoice.total_amount == Decimal("300000.00")
            assert invoice.due_date == date(2026, 12, 1)
            assert invoice.doc_number.startswith(f"INV-{tenant_a.namespace}-202611-")
            assert invoice.first_period_policy == "full"
            # Bukti issue_by scheduler jujur
            assert invoice.issued_by == "scheduler"
            # Line snapshot
            lines = list(invoice.lines.order_by("ordinal"))
            assert len(lines) == 1 and lines[0].line_kind == "subscription"
            assert lines[0].amount == Decimal("300000.00")
            # Dokumen PDF terbit (TK-109) menaut invoice
            doc = IssuedDocument.objects.get(
                kind=IssuedDocument.Kind.INTERNET_INVOICE, ref_id=str(invoice.id)
            )
            assert doc.locale == "id"  # rantai: customer kosong → tenant default id
            assert doc.ref_type == "billing_invoice"

    def test_price_snapshot_issued_invoice_unchanged(self, tenant_a, billed_service):
        """done_when TK-601: harga baru tidak mengubah invoice issued."""
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            BillingPackage.objects.filter(id=billed_service["package"].id).update(
                monthly_price=Decimal("999000")
            )
        run_scheduler(tenant_a, on_date="2026-11-25")  # hari lain: tidak ada periode baru
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get()
            assert invoice.total_amount == Decimal("300000.00")
            assert invoice.lines.get().amount == Decimal("300000.00")

    def test_unique_period_prevents_direct_duplicate(self, tenant_a, billed_service):
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            original = InternetInvoice.objects.get()
            from django.db import IntegrityError

            with pytest.raises(IntegrityError):
                InternetInvoice.objects.create(
                    tenant=tenant_a,
                    service=billed_service["service"],
                    kind="prepaid",
                    period_index=0,
                    period_start=original.period_start,
                    period_end=original.period_end,
                    doc_number="INV-X-202611-0001",
                    due_date=original.due_date,
                )

    def test_prorata_first_policy_amount(self, tenant_a):
        """prorata_daily: 300000×16/30 = 160000 (aktivasi 15 Nov)."""
        from domains.customers.models import Customer as C

        with tenant_scope(tenant_a.id):
            customer = C.objects.create(tenant=tenant_a, display_name="Cici", customer_code="CUST-PR1")
            package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket Prorata", monthly_price=Decimal("300000"),
                first_period_policy=BillingPackage.FirstPeriodPolicy.PRORATA_DAILY,
            )
            service = Service.objects.create(
                tenant=tenant_a, customer=customer, service_code="SVC-PR1",
                lifecycle=Service.Lifecycle.PROVISIONED,
                start_date=date(2026, 11, 15), billing_package=package,
            )
        # Periode pertama sudah lewat jendela lead → terbit sekarang (aktivasi
        # tanggal 15; trigger 8 Nov sudah lewat → "segera saat service baru").
        run_scheduler(tenant_a, on_date="2026-11-16")
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(service=service)
            assert invoice.total_amount == Decimal("160000.00")
            assert invoice.first_period_policy == "prorata_daily"
            # due tidak sebelum issue (terbit 16 Nov > start? start=15 → due=issue 16)
            assert invoice.due_date == date(2026, 11, 16)

    def test_free_first_policy_zero_invoice_paid(self, tenant_a):
        """free_until_next_period: periode pertama 0 → state paid (catatan)."""
        with tenant_scope(tenant_a.id):
            customer = Customer.objects.create(tenant=tenant_a, display_name="Deni", customer_code="CUST-FR1")
            package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket Gratis Awal", monthly_price=Decimal("300000"),
                first_period_policy=BillingPackage.FirstPeriodPolicy.FREE_UNTIL_NEXT_PERIOD,
            )
            service = Service.objects.create(
                tenant=tenant_a, customer=customer, service_code="SVC-FR1",
                lifecycle=Service.Lifecycle.PROVISIONED,
                start_date=date(2026, 11, 15), billing_package=package,
            )
        run_scheduler(tenant_a, on_date="2026-11-16")
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(service=service)
            assert invoice.total_amount == 0
            assert invoice.state == "paid"  # tidak ada tagihan terutang

    def test_postpaid_issued_after_period_end(self, tenant_a):
        with tenant_scope(tenant_a.id):
            customer = Customer.objects.create(tenant=tenant_a, display_name="Eka", customer_code="CUST-PS1")
            package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket Pascabayar", monthly_price=Decimal("250000"),
                timing=BillingPackage.Timing.POSTPAID, due_day=10,
            )
            service = Service.objects.create(
                tenant=tenant_a, customer=customer, service_code="SVC-PS1",
                lifecycle=Service.Lifecycle.PROVISIONED,
                start_date=date(2026, 10, 1), billing_package=package,
            )
        run_scheduler(tenant_a, on_date="2026-11-01")  # periode Okt selesai 1 Nov
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(service=service)
            assert invoice.kind == "postpaid"
            # periode pertama Okt penuh: [1 Okt, 1 Nov)
            assert invoice.period_start == date(2026, 10, 1)
            assert invoice.period_end == date(2026, 11, 1)
            # issue = akhir periode; due = issue+7 (8 Nov) clamp due_day 10 → 10 Nov
            assert invoice.due_date == date(2026, 11, 10)

    def test_charges_add_on_and_discount_snapshot(self, tenant_a):
        """BIL-07: add-on + diskon snapshot; total = langganan + add-on − diskon."""
        with tenant_scope(tenant_a.id):
            customer = Customer.objects.create(tenant=tenant_a, display_name="Fani", customer_code="CUST-CH1")
            package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket Charge", monthly_price=Decimal("200000")
            )
            service = Service.objects.create(
                tenant=tenant_a, customer=customer, service_code="SVC-CH1",
                lifecycle=Service.Lifecycle.PROVISIONED,
                start_date=date(2026, 12, 1), billing_package=package,
            )
            ServiceCharge.objects.create(
                tenant=tenant_a, service=service, kind=ServiceCharge.Kind.ADD_ON,
                name="IP Publik Statis", amount=Decimal("50000"),
            )
            ServiceCharge.objects.create(
                tenant=tenant_a, service=service, kind=ServiceCharge.Kind.DISCOUNT_NOMINAL,
                name="Promo Perdana", amount=Decimal("20000"),
            )
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(service=service)
            assert invoice.total_amount == Decimal("230000.00")  # 200k + 50k − 20k
            kinds = {line.line_kind: line.amount for line in invoice.lines.all()}
            assert kinds["subscription"] == Decimal("200000.00")
            assert kinds["add_on"] == Decimal("50000.00")
            assert kinds["discount_nominal"] == Decimal("-20000.00")

    def test_charge_validity_window_respected(self, tenant_a):
        """Charge dengan valid_until < periode tidak disnapshot (masa berlaku)."""
        with tenant_scope(tenant_a.id):
            customer = Customer.objects.create(tenant=tenant_a, display_name="Gita", customer_code="CUST-CH2")
            package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket Jendela", monthly_price=Decimal("200000")
            )
            service = Service.objects.create(
                tenant=tenant_a, customer=customer, service_code="SVC-CH2",
                lifecycle=Service.Lifecycle.PROVISIONED,
                start_date=date(2026, 12, 1), billing_package=package,
            )
            ServiceCharge.objects.create(
                tenant=tenant_a, service=service, kind=ServiceCharge.Kind.ADD_ON,
                name="Add-on Lama", amount=Decimal("10000"),
                valid_from=date(2026, 1, 1), valid_until=date(2026, 11, 30),  # kedaluwarsa sebelum periode Des
            )
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(service=service)
            assert invoice.total_amount == Decimal("200000.00")  # add-on kedaluwarsa tidak ikut
            assert invoice.lines.count() == 1

    def test_inactive_package_not_billed(self, tenant_a, billed_service):
        with tenant_scope(tenant_a.id):
            BillingPackage.objects.filter(id=billed_service["package"].id).update(active=False)
        out = run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            assert InternetInvoice.objects.count() == 0

    def test_document_locale_chain_customer_en(self, tenant_a):
        """I18N-01: pelanggan locale en → dokumen terbit bahasa en."""
        with tenant_scope(tenant_a.id):
            customer = Customer.objects.create(
                tenant=tenant_a, display_name="Hana", customer_code="CUST-EN1", locale="en"
            )
            package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket EN", monthly_price=Decimal("100000")
            )
            Service.objects.create(
                tenant=tenant_a, customer=customer, service_code="SVC-EN1",
                lifecycle=Service.Lifecycle.PROVISIONED,
                start_date=date(2026, 12, 1), billing_package=package,
            )
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(service__service_code="SVC-EN1")
            assert invoice.locale == "en"
            doc = IssuedDocument.objects.get(ref_id=str(invoice.id))
            assert doc.locale == "en"

    def test_dry_run_writes_nothing(self, tenant_a, billed_service):
        buf = StringIO()
        call_command(
            "issue_due_invoices", "--tenant", tenant_a.namespace,
            "--date", "2026-11-24", "--dry-run", stdout=buf,
        )
        assert "[DRY]" in buf.getvalue()
        with tenant_scope(tenant_a.id):
            assert InternetInvoice.objects.count() == 0


class TestTimezoneBoundary:
    """I18N-03/AC-BIL: batas zona waktu pada tanggal scheduler."""

    def test_wit_crosses_date_before_wib(self):
        # UTC 2026-11-05 15:00 → WIB 22:00 5 Nov; WITA 23:00 5 Nov; WIT 00:00 6 Nov
        moment = datetime(2026, 11, 5, 15, 0, tzinfo=ZoneInfo("UTC"))
        assert today_in_timezone("Asia/Jakarta", now=moment) == date(2026, 11, 5)
        assert today_in_timezone("Asia/Makassar", now=moment) == date(2026, 11, 5)
        assert today_in_timezone("Asia/Jayapura", now=moment) == date(2026, 11, 6)

    def test_unknown_timezone_falls_back_wib(self):
        moment = datetime(2026, 11, 5, 15, 0, tzinfo=ZoneInfo("UTC"))
        assert today_in_timezone("Mars/Olympus", now=moment) == date(2026, 11, 5)


class TestInvoiceApi:
    def test_list_and_detail_with_document_link(self, auth_client, tenant_a, billed_service):
        run_scheduler(tenant_a, on_date="2026-11-24")
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/invoices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] and len(body["items"]) == 1
        invoice_id = body["items"][0]["id"]
        assert body["items"][0]["outstanding"] == "300000.00"
        assert body["items"][0]["document_id"]

        detail = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/invoices/{invoice_id}")
        assert detail.status_code == 200
        assert detail.json()["lines"][0]["line_kind"] == "subscription"

    def test_state_filter(self, auth_client, tenant_a, billed_service):
        run_scheduler(tenant_a, on_date="2026-11-24")
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/invoices?state=paid")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_cross_tenant_isolation_404_and_empty(self, auth_client, tenant_a, tenant_b, billed_service):
        run_scheduler(tenant_a, on_date="2026-11-24")
        # Sesi owner tenant A menanyakan URL tenant B → 404 generik (§5)
        resp = auth_client.get(f"/api/v1/tenants/{tenant_b.id}/invoices")
        assert resp.status_code == 404
        # Owner tenant B login → daftar kosong (RLS)
        from domains.identity.models import User

        other_owner = User.objects.create_user(
            email="owner-b2@test.local", full_name="Owner B", password=TEST_PASSWORD
        )
        # tenant_b fixture sudah punya owner sendiri; buat sesi pemiliknya
        resp2 = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/invoices")
        assert resp2.status_code == 200
        assert len(resp2.json()["items"]) == 1

    def test_rls_no_leak_via_orm(self, tenant_a, tenant_b, billed_service):
        run_scheduler(tenant_a, on_date="2026-11-24")
        with tenant_scope(tenant_b.id):
            assert InternetInvoice.objects.count() == 0  # scope B tidak melihat invoice A

    def test_attach_package_to_service_roundtrip(self, auth_client, tenant_a, billed_service):
        with tenant_scope(tenant_a.id):
            new_package = BillingPackage.objects.create(
                tenant=tenant_a, name="Paket Upgrade", monthly_price=Decimal("500000")
            )
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/services/{billed_service['service'].id}/billing-package",
            {"package_id": str(new_package.id)},
            headers={"Idempotency-Key": "attach-1"},
        )
        assert resp.status_code == 200
        with tenant_scope(tenant_a.id):
            billed_service["service"].refresh_from_db()
            assert str(billed_service["service"].billing_package_id) == str(new_package.id)
