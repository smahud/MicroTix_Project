"""Tes integrasi penerimaan pembayaran internet M6 (TK-601, BIL-03).

Skenario wajib (AC-BIL + done_when TK-601/TK-203):
- Bukti upload ≠ posted payment: record → submitted; verify → allocation.
- Partial tidak melunasi; overpayment → kredit belum dialokasikan.
- Alokasi tidak melebihi nilai payment maupun sisa tagihan invoice.
- Pembayaran TIDAK mengubah lifecycle service (payment cannot auto-activate).
- external_ref sama (event bank sama) → 409; replay Idempotency-Key → respons
  sama; isi berbeda → 409 idempotency_conflict.
- Keputusan ganda (verify dua kali) → 409 billing.payment_decided.
- Kwitansi RCP unik per tenant + dokumen PDF menaut payment (BIL-08).
- Aging bucket 0-30/31-60/61-90/>90 + not_due (FINANCE §5).
- Isolasi tenant: payment tenant A tidak terlihat dari tenant B.
- Izin: payments_admin dapat record/verify; viewer hanya membaca.
"""
from __future__ import annotations

import base64
import time
from datetime import date
from decimal import Decimal

import pytest

from domains.billing import services
from domains.billing.models import (
    BillingPackage,
    InternetInvoice,
    InternetPayment,
    PaymentAllocation,
    ServiceCharge,
)
from domains.common.tenant_context import tenant_scope
from domains.customers.models import Customer, Service
from domains.documents.models import IssuedDocument
from domains.identity.models import User
from domains.tenancy.models import Membership, Role
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.integration


def _png_proof() -> str:
    return base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()


@pytest.fixture
def provisioned_service(tenant_a):
    """Layanan provisioned + invoice prepaid 300.000 (sudah terbit, open)."""
    with tenant_scope(tenant_a.id):
        customer = Customer.objects.create(
            tenant=tenant_a, display_name="Ibu Wati", customer_code="CUST-PAY1"
        )
        package = BillingPackage.objects.create(
            tenant=tenant_a, name="Paket Bayar", monthly_price=Decimal("300000")
        )
        service = Service.objects.create(
            tenant=tenant_a,
            customer=customer,
            service_code="SVC-PAY1",
            lifecycle=Service.Lifecycle.PROVISIONED,
            start_date=date(2026, 12, 1),
            billing_package=package,
        )
        invoice = InternetInvoice.objects.create(
            tenant=tenant_a,
            service=service,
            kind="prepaid",
            state=InternetInvoice.State.OPEN,
            period_index=0,
            period_start=date(2026, 12, 1),
            period_end=date(2027, 1, 1),
            doc_number=f"INV-{tenant_a.namespace}-202611-0001",
            total_amount=Decimal("300000.00"),
            due_date=date(2026, 12, 1),
        )
    return {"service": service, "invoice": invoice, "customer": customer}


@pytest.fixture
def payments_admin_client(api_client, tenant_a):
    """Sesi payments_admin tenant_a (izin payments.verify)."""
    admin = User.objects.create_user(
        email="payadmin@test.local", full_name="Admin Bayar",
        password=TEST_PASSWORD, is_active=True,
    )
    Membership.objects.create(user=admin, tenant_id=tenant_a.id, role=Role.PAYMENTS_ADMIN)
    api_client.force_login(admin)
    session = api_client.session
    session["active_tenant_id"] = str(tenant_a.id)
    session["auth_at"] = time.time()
    session.save()
    return api_client


class TestRecordPayment:
    def test_bank_transfer_requires_proof(self, payments_admin_client, tenant_a):
        resp = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "bank_transfer", "amount": "300000"},
            headers={"Idempotency-Key": "pay-noproof"},
        )
        assert resp.status_code == 422
        assert "file_b64" in resp.json().get("field_errors", {})

    def test_cash_without_proof_ok(self, payments_admin_client, tenant_a, provisioned_service):
        resp = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "50000"},
            headers={"Idempotency-Key": "pay-cash-1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["state"] == "submitted"  # bukti/record ≠ posted (BIL-03)
        assert body["credit"] == "50000.00"

    def test_bad_mime_rejected(self, payments_admin_client, tenant_a):
        resp = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {
                "method": "bank_transfer",
                "amount": "1000",
                "file_b64": base64.b64encode(b"MZ\x90\x00garbage-not-an-image").decode(),
            },
            headers={"Idempotency-Key": "pay-badmime"},
        )
        assert resp.status_code == 422

    def test_external_ref_duplicate_conflict(self, payments_admin_client, tenant_a):
        payload = {
            "method": "bank_transfer", "amount": "300000", "external_ref": "MUT-2026-001",
            "file_b64": _png_proof(),
        }
        first = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments", payload,
            headers={"Idempotency-Key": "pay-ext-1"},
        )
        assert first.status_code == 201
        # Event bank sama direkam ulang → 409 (dedup event, BUKAN payment kedua)
        dup = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments", payload,
            headers={"Idempotency-Key": "pay-ext-2"},
        )
        assert dup.status_code == 409

    def test_idempotency_key_replay_same_response(self, payments_admin_client, tenant_a):
        payload = {"method": "cash", "amount": "10000"}
        r1 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments", payload,
            headers={"Idempotency-Key": "pay-idem-a"},
        )
        r2 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments", payload,
            headers={"Idempotency-Key": "pay-idem-a"},
        )
        assert r1.status_code == r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]  # replay = payment sama
        # Isi berbeda dengan key sama → 409 idempotency_conflict
        r3 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "99999"},
            headers={"Idempotency-Key": "pay-idem-a"},
        )
        assert r3.status_code == 409
        assert r3.json()["code"] == "idempotency_conflict"  # kode mesin stabil (§5)

    def test_viewer_cannot_record(self, api_client, tenant_a, provisioned_service):
        vuser = User.objects.create_user(
            email="viewer2@test.local", full_name="Viewer 2", password=TEST_PASSWORD, is_active=True
        )
        Membership.objects.create(user=vuser, tenant_id=tenant_a.id, role=Role.VIEWER)
        api_client.force_login(vuser)
        session = api_client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session["auth_at"] = time.time()
        session.save()
        resp = api_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "1000"},
            headers={"Idempotency-Key": "pay-viewer"},
        )
        assert resp.status_code == 403


class TestVerifyPayment:
    def test_partial_payment_keeps_invoice_partial(self, tenant_a, provisioned_service, payments_admin_client):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "100000"},
            headers={"Idempotency-Key": "ver-part-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "100000"}]},
            headers={"Idempotency-Key": "ver-part-2"},
        )
        assert verify.status_code == 200
        body = verify.json()
        assert body["state"] == "verified"
        assert body["credit"] == "0.00"
        with tenant_scope(tenant_a.id):
            invoice = InternetInvoice.objects.get(id=provisioned_service["invoice"].id)
            assert invoice.state == "partial"  # sebagian TIDAK melunasi (AC-BIL)
            assert invoice.paid_amount == Decimal("100000.00")

    def test_overpayment_leaves_credit(self, tenant_a, provisioned_service, payments_admin_client):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "350000"},
            headers={"Idempotency-Key": "ver-over-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "300000"}]},
            headers={"Idempotency-Key": "ver-over-2"},
        )
        body = verify.json()
        assert body["credit"] == "50000.00"  # selisih = kredit belum dialokasikan
        with tenant_scope(tenant_a.id):
            assert InternetInvoice.objects.get(id=provisioned_service["invoice"].id).state == "paid"

    def test_allocation_exceeds_payment_rejected(self, tenant_a, provisioned_service, payments_admin_client):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "100000"},
            headers={"Idempotency-Key": "ver-exceed-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "150000"}]},
            headers={"Idempotency-Key": "ver-exceed-2"},
        )
        assert verify.status_code == 409
        assert verify.json()["code"] == "billing.allocation_exceeds_payment"

    def test_allocation_exceeds_outstanding_rejected(self, tenant_a, provisioned_service, payments_admin_client):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "999999"},
            headers={"Idempotency-Key": "ver-out-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "300001"}]},
            headers={"Idempotency-Key": "ver-out-2"},
        )
        assert verify.status_code == 409
        assert verify.json()["code"] == "billing.allocation_exceeds_outstanding"

    def test_paid_invoice_not_payable(self, tenant_a, provisioned_service, payments_admin_client):
        with tenant_scope(tenant_a.id):
            InternetInvoice.objects.filter(id=provisioned_service["invoice"].id).update(
                state=InternetInvoice.State.PAID, paid_amount=Decimal("300000.00")
            )
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "50000"},
            headers={"Idempotency-Key": "ver-paid-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "50000"}]},
            headers={"Idempotency-Key": "ver-paid-2"},
        )
        assert verify.status_code == 409
        assert verify.json()["code"] == "billing.invoice_not_payable"

    def test_verify_twice_conflict(self, tenant_a, provisioned_service, payments_admin_client):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "300000"},
            headers={"Idempotency-Key": "ver-twice-1"},
        ).json()
        alloc = {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "300000"}]}
        v1 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify", alloc,
            headers={"Idempotency-Key": "ver-twice-2"},
        )
        assert v1.status_code == 200
        v2 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify", alloc,
            headers={"Idempotency-Key": "ver-twice-3"},
        )
        # Keputusan ganda → 409 payment_decided (bukan alokasi kedua)
        assert v2.status_code == 409
        assert v2.json()["code"] == "billing.payment_decided"
        with tenant_scope(tenant_a.id):
            assert PaymentAllocation.objects.count() == 1

    def test_idempotent_verify_replay(self, tenant_a, provisioned_service, payments_admin_client):
        """Idempotency-Key sama pada verify → replay respons logis, bukan dobel."""
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "300000"},
            headers={"Idempotency-Key": "ver-replay-1"},
        ).json()
        alloc = {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "300000"}]}
        v1 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify", alloc,
            headers={"Idempotency-Key": "ver-replay-key"},
        )
        v2 = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify", alloc,
            headers={"Idempotency-Key": "ver-replay-key"},
        )
        assert v1.status_code == v2.status_code == 200
        assert v1.json()["id"] == v2.json()["id"]
        with tenant_scope(tenant_a.id):
            assert PaymentAllocation.objects.count() == 1

    def test_payment_does_not_auto_activate(self, tenant_a, provisioned_service, payments_admin_client):
        """done_when TK-601: payment cannot auto-activate — lifecycle tak tersentuh."""
        with tenant_scope(tenant_a.id):
            service_before = Service.objects.get(id=provisioned_service["service"].id)
            lifecycle_before = service_before.lifecycle
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "300000"},
            headers={"Idempotency-Key": "ver-noact-1"},
        ).json()
        payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "300000"}]},
            headers={"Idempotency-Key": "ver-noact-2"},
        )
        with tenant_scope(tenant_a.id):
            service_after = Service.objects.get(id=provisioned_service["service"].id)
            assert service_after.lifecycle == lifecycle_before  # provisioning TIDAK otomatis
            assert service_after.lifecycle == Service.Lifecycle.PROVISIONED

    def test_receipt_document_issued(self, tenant_a, provisioned_service, payments_admin_client):
        """BIL-08: kwitansi bernomor RCP unik + dokumen PDF menaut payment."""
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "300000"},
            headers={"Idempotency-Key": "ver-rcp-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": provisioned_service["invoice"].id, "amount": "300000"}]},
            headers={"Idempotency-Key": "ver-rcp-2"},
        )
        assert verify.status_code == 200
        with tenant_scope(tenant_a.id):
            receipt = IssuedDocument.objects.get(
                kind=IssuedDocument.Kind.RECEIPT, ref_id=record["id"]
            )
            assert receipt.doc_number.startswith(f"RCP-{tenant_a.namespace}-")
            values = receipt.values
            assert values["customer_name"] == "Ibu Wati"
            assert values["applies_to"][0]["invoice_number"].startswith("INV-")

    def test_unallocated_payment_full_credit_receipt(self, tenant_a, payments_admin_client):
        """Verifikasi tanpa alokasi → seluruh nilai jadi kredit; kwitansi tetap terbit."""
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "75000"},
            headers={"Idempotency-Key": "ver-cred-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": []},
            headers={"Idempotency-Key": "ver-cred-2"},
        )
        assert verify.status_code == 200
        body = verify.json()
        assert body["credit"] == "75000.00"
        assert body["allocated_amount"] == "0.00"
        with tenant_scope(tenant_a.id):
            assert IssuedDocument.objects.filter(
                kind=IssuedDocument.Kind.RECEIPT, ref_id=record["id"]
            ).exists()

    def test_multi_invoice_allocation(self, tenant_a, provisioned_service, payments_admin_client):
        """Satu payment → banyak invoice (BIL-03); duplikat id digabung nilainya."""
        with tenant_scope(tenant_a.id):
            second = InternetInvoice.objects.create(
                tenant=tenant_a,
                service=provisioned_service["service"],
                kind="prepaid",
                state=InternetInvoice.State.OPEN,
                period_index=1,
                period_start=date(2027, 1, 1),
                period_end=date(2027, 2, 1),
                doc_number=f"INV-{tenant_a.namespace}-202611-0002",
                total_amount=Decimal("300000.00"),
                due_date=date(2027, 1, 1),
            )
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "400000"},
            headers={"Idempotency-Key": "ver-multi-1"},
        ).json()
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {
                "allocations": [
                    {"invoice_id": provisioned_service["invoice"].id, "amount": "250000"},
                    {"invoice_id": second.id, "amount": "150000"},
                ]
            },
            headers={"Idempotency-Key": "ver-multi-2"},
        )
        assert verify.status_code == 200
        with tenant_scope(tenant_a.id):
            first = InternetInvoice.objects.get(id=provisioned_service["invoice"].id)
            assert first.state == "partial" and first.paid_amount == Decimal("250000.00")
            assert InternetInvoice.objects.get(id=second.id).state == "partial"
            assert PaymentAllocation.objects.filter(payment_id=record["id"]).count() == 2

    def test_reject_with_reason(self, tenant_a, payments_admin_client):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "10000"},
            headers={"Idempotency-Key": "rej-1"},
        ).json()
        no_reason = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/reject",
            {"reason": ""},
            headers={"Idempotency-Key": "rej-2"},
        )
        assert no_reason.status_code == 422
        ok = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/reject",
            {"reason": "Bukti transfer tidak cocok dengan mutasi"},
            headers={"Idempotency-Key": "rej-3"},
        )
        assert ok.status_code == 200
        assert ok.json()["state"] == "rejected"
        # Setelah rejected, verify → 409 payment_decided
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": []},
            headers={"Idempotency-Key": "rej-4"},
        )
        assert verify.status_code == 409


class TestAging:
    def _make_invoice(self, tenant, number, due_date, total="300000.00", paid="0.00", state="open"):
        from domains.customers.models import Customer as C

        with tenant_scope(tenant.id):
            customer = C.objects.create(
                tenant=tenant, display_name=f"Customer {number}", customer_code=f"CUST-AG{number}"
            )
            service = Service.objects.create(
                tenant=tenant, customer=customer, service_code=f"SVC-AG{number}",
                lifecycle=Service.Lifecycle.PROVISIONED, start_date=date(2026, 1, 1),
            )
            return InternetInvoice.objects.create(
                tenant=tenant, service=service, kind="prepaid", state=state,
                period_index=0, period_start=date(2026, 1, 1), period_end=date(2026, 2, 1),
                doc_number=f"INV-{tenant.namespace}-202601-{number:04d}",
                total_amount=Decimal(total), paid_amount=Decimal(paid), due_date=due_date,
            )

    def test_aging_buckets_and_totals(self, auth_client, tenant_a):
        as_of = date(2026, 11, 6)
        self._make_invoice(tenant_a, 1, date(2026, 11, 1))                      # 5 hari → current (0-30)
        self._make_invoice(tenant_a, 2, date(2026, 10, 1))                       # 36 hari → 31-60
        self._make_invoice(tenant_a, 3, date(2026, 9, 1))                        # 66 hari → 61-90
        self._make_invoice(tenant_a, 4, date(2026, 7, 1))                        # >90 hari
        self._make_invoice(tenant_a, 5, date(2026, 12, 1))                       # belum jatuh tempo
        self._make_invoice(tenant_a, 6, date(2026, 8, 1), paid="300000.00", state="paid")  # paid tidak ikut

        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/invoices/aging?as_of=2026-11-06")
        assert resp.status_code == 200
        body = resp.json()
        assert body["as_of"] == "2026-11-06"
        totals = body["totals"]
        assert totals["not_due"]["count"] == 1
        assert totals["current"]["count"] == 1 and totals["current"]["outstanding"] == "300000.00"
        assert totals["d31_60"]["count"] == 1
        assert totals["d61_90"]["count"] == 1
        assert totals["d90_plus"]["count"] == 1
        # Invoice paid tidak masuk aging
        assert all(item["doc_number"].endswith("-0006") is False for item in body["items"])


class TestPaymentIsolation:
    def test_cross_tenant_payment_invisible(self, tenant_a, tenant_b, payments_admin_client, provisioned_service):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "10000"},
            headers={"Idempotency-Key": "iso-1"},
        ).json()
        # Owner tenant A menanyakan URL tenant B → 404 generik
        resp = payments_admin_client.get(f"/api/v1/tenants/{tenant_b.id}/payments")
        assert resp.status_code == 404
        # ORM scope tenant B tidak melihat payment tenant A
        with tenant_scope(tenant_b.id):
            assert InternetPayment.objects.count() == 0
        with tenant_scope(tenant_a.id):
            assert InternetPayment.objects.count() == 1

    def test_invoice_of_other_tenant_not_payable(self, tenant_a, tenant_b, payments_admin_client, provisioned_service):
        record = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments",
            {"method": "cash", "amount": "10000"},
            headers={"Idempotency-Key": "iso-2"},
        ).json()
        # Invoice tenant B tidak bisa dialokasi via sesi tenant A → 404 (bukan 422)
        with tenant_scope(tenant_b.id):
            from domains.customers.models import Customer as C

            customer = C.objects.create(tenant=tenant_b, display_name="X", customer_code="CX")
            service = Service.objects.create(
                tenant=tenant_b, customer=customer, service_code="SVC-B1",
                lifecycle=Service.Lifecycle.PROVISIONED, start_date=date(2026, 1, 1),
            )
            foreign = InternetInvoice.objects.create(
                tenant=tenant_b, service=service, kind="prepaid", state="open",
                period_index=0, period_start=date(2026, 1, 1), period_end=date(2026, 2, 1),
                doc_number=f"INV-{tenant_b.namespace}-202601-0001",
                total_amount=Decimal("10000.00"), due_date=date(2026, 1, 1),
            )
        verify = payments_admin_client.post(
            f"/api/v1/tenants/{tenant_a.id}/payments/{record['id']}/verify",
            {"allocations": [{"invoice_id": str(foreign.id), "amount": "10000"}]},
            headers={"Idempotency-Key": "iso-3"},
        )
        assert verify.status_code == 404  # RLS: invoice asing tidak terlihat → 404 generik
