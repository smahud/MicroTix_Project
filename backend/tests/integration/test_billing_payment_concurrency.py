"""Tes integrasi konkurensi alokasi pembayaran internet — PA-001 (P0).

Kelas race yang ditemukan planning audit 2026-11-10: verifikasi dua payment
BERBEDA terhadap invoice yang sama pada DUA KONEKSI PostgreSQL nyata (satu
koneksi per thread; PID tiap thread diverifikasi berbeda). Sebelum perbaikan,
`_parse_allocations` membaca `paid_amount` tanpa kunci baris dan loop verifikasi
menimpa nilainya dari snapshot basi (lost update) sehingga dua alokasi bisa
melebihi total tagihan.

Invarian yang diuji (acceptance PA-001):
- Tidak ada over-allocation: gabungan alokasi per invoice tidak pernah
  melebihi sisa tagihan yang dibaca pembaca terkunci (FOR UPDATE).
- Tidak ada lost update: `invoice.paid_amount == SUM(alokasi invoice itu)`
  untuk semua interleaving.
- Satu efek logis per verifikasi: pemenang terbit lengkap dan atomik
  (allocation + state invoice/payment + kwitansi + audit + outbox); yang
  kalah ditolak 409 dan tidak menyisakan efek apa pun.
- Urutan kunci deterministik: verifikasi dengan pasangan invoice yang sama
  tetapi urutan body dibalik tidak deadlock.
- Penomoran kwitansi RCP tetap unik di bawah konkurensi (kunci baris tenant).

Pengujian memakai start-barrier antar thread TANPA monkeypatch jalur produksi;
service dipanggil persis seperti view produksi (tenant_scope + transaksi).
Marker `transaction=True` wajib agar setup ter-commit dan terlihat oleh
koneksi thread (semantik rollback TestCase akan menyembunyikannya dari
koneksi lain). `available_apps` membatasi flush teardown ke aplikasi yang
dikotori tes ini; TRUNCATE ... CASCADE menghindari FK tabel radius yang
unmanaged (jalur TransactionTestCase polos gagal di sini).
"""
from __future__ import annotations

import threading
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.db.models import Sum

from domains.audit.models import AuditEvent
from domains.billing import services
from domains.billing.models import (
    BillingPackage,
    InternetInvoice,
    InternetPayment,
    PaymentAllocation,
)
from domains.common.envelope import ApiError
from domains.common.tenant_context import tenant_scope
from domains.customers.models import Customer, Service
from domains.documents.models import IssuedDocument
from domains.identity.models import User
from domains.jobs.models import OutboxEvent
from domains.tenancy.models import Membership, Role, Tenant

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(
        transaction=True,
        available_apps=[
            "domains.tenancy",
            "domains.identity",
            "domains.customers",
            "domains.billing",
            "domains.documents",
            "domains.audit",
            "domains.jobs",
        ],
    ),
]

JOIN_TIMEOUT_S = 90


def _pg_pid() -> int:
    """PID backend PostgreSQL koneksi thread ini (bukti koneksi terpisah)."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        return cur.fetchone()[0]


def _setup_world(namespace: str, *, invoice_totals: list[str]) -> SimpleNamespace:
    """Setup ter-commit: tenant, payments admin, layanan, dan N invoice open."""
    tenant = Tenant.objects.create(display_name=f"Konkurensi {namespace}", namespace=namespace)
    admin = User.objects.create_user(
        email=f"{namespace}@test.local", full_name="Admin Konkurensi",
        password="test-password-1234567890", is_active=True,
    )
    Membership.objects.create(user=admin, tenant=tenant, role=Role.PAYMENTS_ADMIN)
    with tenant_scope(tenant.id):
        customer = Customer.objects.create(
            tenant=tenant, display_name="Pak Konkurensi", customer_code=f"CUST-{namespace}"
        )
        package = BillingPackage.objects.create(
            tenant=tenant, name=f"Paket {namespace}", monthly_price=Decimal(invoice_totals[0])
        )
        service = Service.objects.create(
            tenant=tenant, customer=customer, service_code=f"SVC-{namespace}",
            lifecycle=Service.Lifecycle.PROVISIONED, start_date=date(2026, 12, 1),
            billing_package=package,
        )
        invoices = []
        for idx, total in enumerate(invoice_totals):
            invoices.append(
                InternetInvoice.objects.create(
                    tenant=tenant, service=service, kind="prepaid",
                    state=InternetInvoice.State.OPEN,
                    period_index=idx,
                    period_start=date(2026, 12, 1) + timedelta(days=31 * idx),  # periode berbeda
                    period_end=date(2027, 1, 1) + timedelta(days=31 * idx),
                    doc_number=f"INV-{namespace}-202611-{idx + 1:04d}",
                    total_amount=Decimal(total), due_date=date(2026, 12, 1),
                )
            )
    return SimpleNamespace(tenant=tenant, admin=admin, invoices=invoices)


def _record_payment(world, amount: str) -> InternetPayment:
    with tenant_scope(world.tenant.id):
        payment = InternetPayment.objects.create(
            tenant=world.tenant, method=InternetPayment.Method.CASH, amount=Decimal(amount)
        )
    return payment


def _run_verify(tag, tenant_id, payment_id, allocations, start, results, pids):
    """Isi thread: panggil services.verify_payment persis seperti view produksi."""

    def body():
        from django.db import connection

        try:
            start.wait()
            with tenant_scope(tenant_id):
                pids[tag] = _pg_pid()
                services.verify_payment(
                    str(tenant_id), str(payment_id), {"allocations": allocations}, actor=None
                )
            results[tag] = "ok"
        except ApiError as exc:
            results[tag] = f"ApiError({exc.status_code}/{exc.code})"
        except Exception as exc:  # noqa: BLE001
            results[tag] = f"EXC({type(exc).__name__}: {exc})"
        finally:
            from django.db import connection

            connection.close()

    return body


def _start_threads(targets) -> list[threading.Thread]:
    threads = [threading.Thread(target=t) for t in targets]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT_S)
    return threads


def _payment_effects(payment_id: str) -> SimpleNamespace:
    """Kumpulkan seluruh efek samping sebuah verifikasi payment (untuk
    menegaskan atomisitas: efek yang ada harus lengkap, yang ditolak nihil)."""
    return SimpleNamespace(
        allocations=PaymentAllocation.objects.filter(payment_id=payment_id).count(),
        receipts=IssuedDocument.objects.filter(
            kind=IssuedDocument.Kind.RECEIPT, ref_id=str(payment_id)
        ).count(),
        audit=AuditEvent.objects.filter(
            action_code="internet_payment.verified", target_id=str(payment_id)
        ).count(),
        outbox=OutboxEvent.objects.filter(
            event_type="internet_payment.verified", aggregate_id=str(payment_id)
        ).count(),
    )


class TestConcurrentVerification:
    def test_two_payments_same_invoice_overallocation_rejected_cleanly(self):
        """200rb + 200rb pada invoice 300rb: tepat satu lolos; yang kalah 409
        `billing.allocation_exceeds_outstanding` tanpa efek sisa apa pun."""
        world = _setup_world("rtrw-cc000001", invoice_totals=["300000"])
        invoice = world.invoices[0]
        pay1 = _record_payment(world, "200000")
        pay2 = _record_payment(world, "200000")

        results: dict[str, str] = {}
        pids: dict[str, int] = {}
        start = threading.Barrier(2, timeout=30)
        threads = _start_threads(
            [
                _run_verify("p1", world.tenant.id, pay1.id,
                            [{"invoice_id": str(invoice.id), "amount": "200000"}], start, results, pids),
                _run_verify("p2", world.tenant.id, pay2.id,
                            [{"invoice_id": str(invoice.id), "amount": "200000"}], start, results, pids),
            ]
        )
        assert all(not t.is_alive() for t in threads), "thread menggantung ( deadlock/timeout )"
        assert pids["p1"] != pids["p2"], "harus dua koneksi PostgreSQL berbeda"

        # Tepat satu pemenang; yang kalah konflik over-allocation (deterministik:
        # siapa pun yang lebih dulu memegang kunci baris, yang satunya melihat
        # sisa tagihan yang sudah diperbarui).
        winners = [tag for tag, res in results.items() if res == "ok"]
        losers = [tag for tag, res in results.items() if res != "ok"]
        assert len(winners) == 1 and len(losers) == 1, results
        assert results[losers[0]] == "ApiError(409/billing.allocation_exceeds_outstanding)", results

        winner_pay = pay1 if winners[0] == "p1" else pay2
        loser_pay = pay2 if winners[0] == "p1" else pay1

        with tenant_scope(world.tenant.id):
            inv = InternetInvoice.objects.get(id=invoice.id)
            alloc_sum = PaymentAllocation.objects.filter(invoice_id=inv.id).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")
            # Invarian inti PA-001: paid == SUM(alokasi) <= total, tanpa lost update.
            assert inv.paid_amount == Decimal("200000.00"), inv.paid_amount
            assert alloc_sum == inv.paid_amount, (alloc_sum, inv.paid_amount)
            assert inv.paid_amount <= inv.total_amount
            assert inv.state == InternetInvoice.State.PARTIAL
            assert PaymentAllocation.objects.count() == 1

            winner = InternetPayment.objects.get(id=winner_pay.id)
            assert winner.state == InternetPayment.State.VERIFIED
            assert winner.allocated_amount == Decimal("200000.00")
            effects = _payment_effects(winner_pay.id)
            assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (1, 1, 1, 1)

            loser = InternetPayment.objects.get(id=loser_pay.id)
            assert loser.state == InternetPayment.State.SUBMITTED
            assert loser.allocated_amount == Decimal("0")
            effects = _payment_effects(loser_pay.id)
            assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (0, 0, 0, 0)

    def test_two_complementary_payments_no_lost_update(self):
        """100rb + 200rb pada invoice 300rb: keduanya boleh lolos dan hasil
        akhirnya paid == 300rb == SUM(alokasi) — update pertama tidak tertimpa."""
        world = _setup_world("rtrw-cc000002", invoice_totals=["300000"])
        invoice = world.invoices[0]
        pay1 = _record_payment(world, "100000")
        pay2 = _record_payment(world, "200000")

        results: dict[str, str] = {}
        pids: dict[str, int] = {}
        start = threading.Barrier(2, timeout=30)
        threads = _start_threads(
            [
                _run_verify("p1", world.tenant.id, pay1.id,
                            [{"invoice_id": str(invoice.id), "amount": "100000"}], start, results, pids),
                _run_verify("p2", world.tenant.id, pay2.id,
                            [{"invoice_id": str(invoice.id), "amount": "200000"}], start, results, pids),
            ]
        )
        assert all(not t.is_alive() for t in threads), "thread menggantung ( deadlock/timeout )"
        assert pids["p1"] != pids["p2"], "harus dua koneksi PostgreSQL berbeda"
        assert results == {"p1": "ok", "p2": "ok"}, results

        with tenant_scope(world.tenant.id):
            inv = InternetInvoice.objects.get(id=invoice.id)
            alloc_sum = PaymentAllocation.objects.filter(invoice_id=inv.id).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")
            assert inv.paid_amount == Decimal("300000.00"), inv.paid_amount
            assert alloc_sum == inv.paid_amount == inv.total_amount
            assert inv.state == InternetInvoice.State.PAID
            for pay in (pay1, pay2):
                payment = InternetPayment.objects.get(id=pay.id)
                assert payment.state == InternetPayment.State.VERIFIED
                effects = _payment_effects(pay.id)
                assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (1, 1, 1, 1)

    def test_multi_invoice_reversed_body_order_no_deadlock(self):
        """Dua verifikasi dengan pasangan invoice sama, urutan body dibalik
        ([A,B] vs [B,A]): urutan kunci deterministik → tanpa deadlock, kedua
        invoice terkumpul penuh, kwitansi tetap unik."""
        world = _setup_world("rtrw-cc000003", invoice_totals=["200000", "200000"])
        inv_a, inv_b = world.invoices
        pay1 = _record_payment(world, "200000")
        pay2 = _record_payment(world, "200000")

        results: dict[str, str] = {}
        pids: dict[str, int] = {}
        start = threading.Barrier(2, timeout=30)
        threads = _start_threads(
            [
                _run_verify("p1", world.tenant.id, pay1.id,
                            [{"invoice_id": str(inv_a.id), "amount": "100000"},
                             {"invoice_id": str(inv_b.id), "amount": "100000"}], start, results, pids),
                _run_verify("p2", world.tenant.id, pay2.id,
                            [{"invoice_id": str(inv_b.id), "amount": "100000"},
                             {"invoice_id": str(inv_a.id), "amount": "100000"}], start, results, pids),
            ]
        )
        assert all(not t.is_alive() for t in threads), "thread menggantung ( deadlock/timeout )"
        assert pids["p1"] != pids["p2"], "harus dua koneksi PostgreSQL berbeda"
        assert results == {"p1": "ok", "p2": "ok"}, results

        with tenant_scope(world.tenant.id):
            for inv in (inv_a, inv_b):
                fresh = InternetInvoice.objects.get(id=inv.id)
                alloc_sum = PaymentAllocation.objects.filter(invoice_id=inv.id).aggregate(
                    total=Sum("amount")
                )["total"]
                assert fresh.paid_amount == Decimal("200000.00"), fresh.paid_amount
                assert alloc_sum == fresh.paid_amount
                assert fresh.state == InternetInvoice.State.PAID
            # Kwitansi dua payment berbeda tetap bernomor unik (kunci tenant).
            receipt_numbers = list(
                IssuedDocument.objects.filter(kind=IssuedDocument.Kind.RECEIPT).values_list(
                    "doc_number", flat=True
                )
            )
            assert len(receipt_numbers) == len(set(receipt_numbers)) == 2, receipt_numbers


class TestAllocationRollback:
    def test_failed_multi_allocation_rolls_back_everything(self):
        """Alokasi [valid, melebihi sisa] → 409; TIDAK ada efek parsial:
        invoice valid tak tersentuh, payment tetap submitted, tanpa kwitansi/
        audit/outbox (satu efek logis — acceptance PA-001)."""
        world = _setup_world("rtrw-cc000004", invoice_totals=["300000", "100000"])
        inv_a, inv_b = world.invoices
        payment = _record_payment(world, "400000")

        with tenant_scope(world.tenant.id):
            with pytest.raises(ApiError) as excinfo:
                services.verify_payment(
                    str(world.tenant.id), str(payment.id),
                    {
                        "allocations": [
                            {"invoice_id": str(inv_a.id), "amount": "299999"},  # valid…
                            {"invoice_id": str(inv_b.id), "amount": "100001"},  # …melebihi sisa B
                        ]
                    },
                    actor=None,
                )
            assert excinfo.value.code == "billing.allocation_exceeds_outstanding"

            fresh_a = InternetInvoice.objects.get(id=inv_a.id)
            assert fresh_a.paid_amount == Decimal("0")
            assert fresh_a.state == InternetInvoice.State.OPEN
            fresh_b = InternetInvoice.objects.get(id=inv_b.id)
            assert fresh_b.paid_amount == Decimal("0")
            assert fresh_b.state == InternetInvoice.State.OPEN

            assert PaymentAllocation.objects.count() == 0
            fresh_pay = InternetPayment.objects.get(id=payment.id)
            assert fresh_pay.state == InternetPayment.State.SUBMITTED
            assert fresh_pay.allocated_amount == Decimal("0")
            effects = _payment_effects(payment.id)
            assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (0, 0, 0, 0)
