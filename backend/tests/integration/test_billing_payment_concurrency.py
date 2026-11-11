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

Koreksi review 2026-11-11 (REV-1111-01/02/03 — PR #9 REQUEST CHANGES):
- Identitas canonical: semua ejaan UUID satu invoice (besar/kecil,
  hyphen/compact) tergabung jadi SATU alokasi; id salah bentuk → 422
  validation (bukan 404); pasangan invoice sama selalu mengunci urutan
  identitas database yang sama.
- Urutan hasil = urutan permintaan teragregasi semula: header customer,
  bahasa kwitansi (I18N-01) dan urutan baris `applies_to` mengikuti invoice
  PERTAMA DIMINTA — urutan kunci tidak mengubah semantik dokumen.
- Bukti rollback DIPISAHKAN: (a) validasi ditolak SEBELUM mutasi (409),
  (b) kegagalan terkontrol SETELAH seluruh mutasi DB (bloker unique
  outbox) → seluruh efek DB ter-rollbalik, file artifact yatim
  dihitung terpisah (perilaku diakui issue_document).
- Contention terkontrol: koneksi tes MENAHAN kunci baris invoice
  canonical-pertama, menunggu thread benar-benar terblokir (pg_stat_activity),
  lalu membuktikan urutan akuisisi via probe NOWAIT — bukan barrier + harapan
  interleaving.

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
import time
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.conf import settings
from django.db import DatabaseError, IntegrityError
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


def _setup_world(
    namespace: str,
    *,
    invoice_totals: list[str],
    invoice_ids: list[UUID] | None = None,
) -> SimpleNamespace:
    """Setup ter-commit: tenant, payments admin, layanan, dan N invoice open.

    `invoice_ids` opsional untuk tes yang butuh UUID deterministik (mis. urutan
    canonical vs ejaan alias); panjangnya harus sama dengan `invoice_totals`.
    """
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
            explicit_id = invoice_ids[idx] if invoice_ids else None
            invoices.append(
                InternetInvoice.objects.create(
                    id=explicit_id,
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


def _setup_two_customer_world(namespace: str) -> SimpleNamespace:
    """Setup dua customer beda bahasa + dua invoice UUID deterministik.

    Invoice pertama-diminta (customer "en") sengaja diberi UUID canonical
    LEBIH BESAR daripada invoice kedua — implementasi yang mengembalikan hasil
    urut UUID akan salah memilih customer/bahasa kwitansi (REV-1111-02).
    """
    tenant = Tenant.objects.create(display_name=f"Kwitansi {namespace}", namespace=namespace)
    with tenant_scope(tenant.id):
        customer_en = Customer.objects.create(
            tenant=tenant, display_name="Alpha EN Customer",
            customer_code=f"CU-EN-{namespace}", locale="en",
        )
        customer_id = Customer.objects.create(
            tenant=tenant, display_name="Beta ID Customer",
            customer_code=f"CU-ID-{namespace}", locale="",
        )
        package = BillingPackage.objects.create(
            tenant=tenant, name=f"Paket {namespace}", monthly_price=Decimal("100000")
        )
        service_en = Service.objects.create(
            tenant=tenant, customer=customer_en, service_code=f"SV-EN-{namespace}",
            lifecycle=Service.Lifecycle.PROVISIONED, start_date=date(2026, 12, 1),
            billing_package=package,
        )
        service_id = Service.objects.create(
            tenant=tenant, customer=customer_id, service_code=f"SV-ID-{namespace}",
            lifecycle=Service.Lifecycle.PROVISIONED, start_date=date(2026, 12, 1),
            billing_package=package,
        )
        # UUID canonical: cccccccc… > aaaaaaa2… → diminta pertama, terurut kedua.
        invoice_first = InternetInvoice.objects.create(
            id=UUID("cccccccc-1111-4222-8333-000000000001"),
            tenant=tenant, service=service_en, kind="prepaid",
            state=InternetInvoice.State.OPEN, period_index=0,
            period_start=date(2026, 12, 1), period_end=date(2027, 1, 1),
            doc_number=f"INV-{namespace}-EN-0001",
            total_amount=Decimal("100000"), due_date=date(2026, 12, 1),
        )
        invoice_second = InternetInvoice.objects.create(
            id=UUID("aaaaaaa2-2222-4333-8444-000000000002"),
            tenant=tenant, service=service_id, kind="prepaid",
            state=InternetInvoice.State.OPEN, period_index=0,
            period_start=date(2027, 1, 1), period_end=date(2027, 2, 1),
            doc_number=f"INV-{namespace}-ID-0002",
            total_amount=Decimal("100000"), due_date=date(2027, 1, 1),
        )
    return SimpleNamespace(
        tenant=tenant, customer_en=customer_en, customer_id=customer_id,
        invoice_first=invoice_first, invoice_second=invoice_second,
    )


def _wait_backend_lock_wait(pid: int, *, deadline_s: float = 30.0) -> bool:
    """Tunggu (dibatasi waktu) backend PostgreSQL benar-benar menunggu lock.

    Polling pg_stat_activity adalah pendeteksi KONDISI, bukan pengatur race:
    interleaving sendiri dikendalikan kunci baris yang ditahan pemanggil.
    """
    from django.db import connection

    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                [pid],
            )
            row = cur.fetchone()
        if row is not None and row[0] == "Lock":
            return True
        time.sleep(0.05)
    return False


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


class TestAllocationValidationBeforeMutation:
    def test_invalid_second_allocation_rejected_before_any_mutation(self):
        """Alokasi [valid, melebihi sisa] → 409 pada _parse_allocations
        SEBELUM mutasi apa pun (validasi-di-muka). Ini BUKAN bukti rollback
        pasca-tulis — kasus itu dibuktikan terpisah oleh TestPostWriteRollback
        (kegagalan terkontrol SETELAH seluruh mutasi DB)."""
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


class TestCanonicalInvoiceIdentity:
    """REV-1111-01: identitas UUID canonical sebelum merge/sort/kunci."""

    def test_alias_spellings_of_one_invoice_merge_into_single_allocation(self):
        """Satu invoice via empat ejaan (kecil-hyphen, BESAR-hyphen,
        kecil-compact, BESAR-compact) → SATU alokasi tergabung; tanpa
        normalisasi, ejaan berbeda lolos penggabungan dan menabrak
        uq_bilalloc_pair / menghasilkan baris alokasi ganda."""
        world = _setup_world("rtrw-cc000005", invoice_totals=["300000"])
        invoice = world.invoices[0]
        payment = _record_payment(world, "200000")
        aliases = [
            str(invoice.id),              # lowercase + hyphen (kanonik)
            str(invoice.id).upper(),      # UPPERCASE + hyphen
            invoice.id.hex,               # lowercase compact (tanpa hyphen)
            invoice.id.hex.upper(),       # UPPERCASE compact
        ]

        with tenant_scope(world.tenant.id):
            services.verify_payment(
                str(world.tenant.id), str(payment.id),
                {
                    "allocations": [
                        {"invoice_id": aliases[0], "amount": "100000"},
                        {"invoice_id": aliases[1], "amount": "50000"},
                        {"invoice_id": aliases[2], "amount": "25000"},
                        {"invoice_id": aliases[3], "amount": "25000"},
                    ]
                },
                actor=None,
            )

            allocs = list(PaymentAllocation.objects.filter(payment_id=payment.id))
            assert len(allocs) == 1, "alias satu invoice harus tergabung satu alokasi"
            assert allocs[0].amount == Decimal("200000.00")
            assert allocs[0].invoice_id == invoice.id

            inv = InternetInvoice.objects.get(id=invoice.id)
            assert inv.paid_amount == Decimal("200000.00")
            assert inv.state == InternetInvoice.State.PARTIAL

            receipt = IssuedDocument.objects.get(
                kind=IssuedDocument.Kind.RECEIPT, ref_id=str(payment.id)
            )
            assert receipt.values["applies_to"] == [
                {"invoice_number": invoice.doc_number, "amount": "200000.00"}
            ]

    def test_malformed_invoice_id_rejected_422_without_effects(self):
        """invoice_id salah bentuk → 422 error.validation (pola
        billing.views._parse_uuid) SEBELUM kunci/query; tanpa efek apa pun.
        UUID valid yang tidak ada tetap 404 (jalur lama utuh)."""
        world = _setup_world("rtrw-cc000006", invoice_totals=["300000"])
        payment = _record_payment(world, "100000")

        for bad in ["bukan-uuid", "", None, "12345", 3.14, ["uuid"], "aaaa-aaaa-aaaa"]:
            with tenant_scope(world.tenant.id):
                with pytest.raises(ApiError) as excinfo:
                    services.verify_payment(
                        str(world.tenant.id), str(payment.id),
                        {"allocations": [{"invoice_id": bad, "amount": "1000"}]},
                        actor=None,
                    )
                assert excinfo.value.status_code == 422, bad
                assert excinfo.value.code == "validation_error", bad
                assert "allocations" in (excinfo.value.field_errors or {}), bad

        # UUID valid tapi tidak dikenal tenant → tetap 404 not_found (bukan 422).
        with tenant_scope(world.tenant.id):
            with pytest.raises(ApiError) as excinfo:
                services.verify_payment(
                    str(world.tenant.id), str(payment.id),
                    {"allocations": [
                        {"invoice_id": "99999999-9999-4999-8999-999999999999", "amount": "1000"}
                    ]},
                    actor=None,
                )
            assert excinfo.value.status_code == 404
            assert excinfo.value.code == "not_found"

        with tenant_scope(world.tenant.id):
            assert PaymentAllocation.objects.count() == 0
            fresh = InternetPayment.objects.get(id=payment.id)
            assert fresh.state == InternetPayment.State.SUBMITTED
            assert fresh.allocated_amount == Decimal("0")
            effects = _payment_effects(payment.id)
            assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (0, 0, 0, 0)


class TestReceiptRequestOrderCompatibility:
    """REV-1111-02: header/bahasa kwitansi mengikuti invoice PERTAMA DIMINTA."""

    def test_receipt_customer_locale_and_lines_follow_first_requested_invoice(self):
        """Invoice pertama-diminta (customer "en") memiliki UUID canonical LEBIH
        BESAR — kwitansi tetap memakai customer/bahasa invoice pertama yang
        diminta dan baris applies_to urutan permintaan; implementasi yang
        mengembalikan hasil terurut UUID akan memakai customer "id" salah."""
        world = _setup_two_customer_world("rtrw-cc000007")
        payment = _record_payment(world, "150000")

        with tenant_scope(world.tenant.id):
            services.verify_payment(
                str(world.tenant.id), str(payment.id),
                {
                    "allocations": [
                        # Diminta pertama: UUID cccccccc… (terbesar secara canonical).
                        {"invoice_id": str(world.invoice_first.id), "amount": "100000"},
                        # Alias huruf besar dari UUID aaaaaaa2… (terkecil).
                        {"invoice_id": str(world.invoice_second.id).upper(), "amount": "50000"},
                    ]
                },
                actor=None,
            )

            receipt = IssuedDocument.objects.get(
                kind=IssuedDocument.Kind.RECEIPT, ref_id=str(payment.id)
            )
            assert receipt.values["customer_name"] == "Alpha EN Customer"
            assert receipt.locale == "en"
            assert [row["invoice_number"] for row in receipt.values["applies_to"]] == [
                world.invoice_first.doc_number,
                world.invoice_second.doc_number,
            ]
            assert [row["amount"] for row in receipt.values["applies_to"]] == [
                "100000.00", "50000.00",
            ]

            for invoice, expected in (
                (world.invoice_first, Decimal("100000.00")),
                (world.invoice_second, Decimal("50000.00")),
            ):
                fresh = InternetInvoice.objects.get(id=invoice.id)
                assert fresh.paid_amount == expected


class TestPostWriteRollback:
    """REV-1111-03: rollback DB SESUDAH seluruh mutasi dibuktikan langsung."""

    def test_failure_after_all_writes_rolls_back_every_db_effect(self):
        """Bloker unique pada dedup_key outbox (insert TERAKHIR verifikasi)
        gagal SETELAH alokasi/update invoice/update payment/kwitansi/audit
        tertulis → transaksi tenant_scope ter-rollbalik penuh; error ditangkap
        DI LUAR tenant_scope. File artifact yatim dihitung TERPISAH dari
        rollback DB (perilaku yang diakui issue_document: artifact ditulis
        sebelum row; paling buruk file yatim, tidak pernah row tanpa file)."""
        world = _setup_world("rtrw-cc000008", invoice_totals=["300000"])
        invoice = world.invoices[0]
        payment = _record_payment(world, "200000")

        # Bloker outbox ter-commit (dedup_key unique global): insert outbox
        # verifikasi pasti IntegrityError — kegagalan terkontrol tanpa
        # monkeypatch jalur produksi.
        with tenant_scope(world.tenant.id):
            OutboxEvent.objects.create(
                tenant=world.tenant,
                event_type="internet_payment.verified",
                aggregate_type="internet_payment",
                aggregate_id=payment.id,
                dedup_key=f"internet_payment:verified:{payment.id}",
                payload={"blocker": "post-write-rollback-test"},
            )

        documents_dir = settings.MT_STORAGE_ROOT / "documents"
        files_before = set()
        if documents_dir.is_dir():
            files_before = {p.name for p in documents_dir.iterdir() if p.is_file()}

        # Error ditangkap DI LUAR tenant_scope (transaksi sudah ter-rollbalik
        # saat keluar scope).
        with pytest.raises(IntegrityError):
            with tenant_scope(world.tenant.id):
                services.verify_payment(
                    str(world.tenant.id), str(payment.id),
                    {"allocations": [{"invoice_id": str(invoice.id), "amount": "200000"}]},
                    actor=None,
                )

        with tenant_scope(world.tenant.id):
            fresh_inv = InternetInvoice.objects.get(id=invoice.id)
            assert fresh_inv.paid_amount == Decimal("0")
            assert fresh_inv.state == InternetInvoice.State.OPEN
            assert PaymentAllocation.objects.count() == 0
            fresh_pay = InternetPayment.objects.get(id=payment.id)
            assert fresh_pay.state == InternetPayment.State.SUBMITTED
            assert fresh_pay.allocated_amount == Decimal("0")
            assert fresh_pay.verified_at is None
            # Kwitansi + audit ikut ter-rollbalik.
            assert IssuedDocument.objects.filter(
                kind=IssuedDocument.Kind.RECEIPT, ref_id=str(payment.id)
            ).count() == 0
            assert AuditEvent.objects.filter(
                action_code="internet_payment.verified", target_id=str(payment.id)
            ).count() == 0
            # Outbox: HANYA bloker pra-buat yang tersisa (event verifikasi
            # yang tertulis sebelum kegagalan ikut ter-rollbalik).
            outbox_rows = list(OutboxEvent.objects.filter(aggregate_id=payment.id))
            assert len(outbox_rows) == 1
            assert outbox_rows[0].payload == {"blocker": "post-write-rollback-test"}

        # Akuntansi file yatim TERPISAH dari rollback DB: paling buruk satu
        # artifact PDF kwitansi tertulis tanpa row-nya.
        files_after = set()
        if documents_dir.is_dir():
            files_after = {p.name for p in documents_dir.iterdir() if p.is_file()}
        orphans = files_after - files_before
        assert len(orphans) <= 1, f"maksimal satu file yatim kwitansi: {orphans}"


class TestControlledLockContention:
    """REV-1111-01/03: contention PostgreSQL TERKONTROL (bukan barrier + harapan).

    Urutan akuisisi kunci dibuktikan DETERMINISTIK: koneksi tes menahan kunci
    baris invoice canonical-PERTAMA; thread verifikasi (dengan ejaan alias yang
    pada kode lama mengurut terbalik) harus mengunggu invoice itu DULU — probe
    NOWAIT pada invoice kedua membuktikan thread BELUM memegang kunci kedua
    saat terblokir.
    """

    def test_lock_acquisition_follows_canonical_identity_order(self):
        inv_a_id = UUID("aaaaaaaa-2222-4333-8444-00000000000a")
        inv_b_id = UUID("bbbbbbbb-3333-4444-8555-00000000000b")
        world = _setup_world(
            "rtrw-cc000009", invoice_totals=["100000", "100000"],
            invoice_ids=[inv_a_id, inv_b_id],
        )
        payment = _record_payment(world, "200000")

        results: dict[str, str] = {}
        pids: dict[str, int] = {}
        started = threading.Event()

        def runner():
            from django.db import connection

            try:
                with tenant_scope(world.tenant.id):
                    pids["t1"] = _pg_pid()
                    started.set()
                    services.verify_payment(
                        str(world.tenant.id), str(payment.id),
                        {
                            # Ejaan alias: A lowercase-hyphen + B UPPERCASE —
                            # pada kode lama urutan teks mentah membalik
                            # urutan kunci (B dulu, baru A).
                            "allocations": [
                                {"invoice_id": str(inv_a_id), "amount": "100000"},
                                {"invoice_id": str(inv_b_id).upper(), "amount": "100000"},
                            ]
                        },
                        actor=None,
                    )
                results["t1"] = "ok"
            except ApiError as exc:
                results["t1"] = f"ApiError({exc.status_code}/{exc.code})"
            except Exception as exc:  # noqa: BLE001
                results["t1"] = f"EXC({type(exc).__name__}: {exc})"
            finally:
                from django.db import connection

                connection.close()

        thread = threading.Thread(target=runner)
        thread.daemon = True
        try:
            with tenant_scope(world.tenant.id):
                # 1) Tahan kunci invoice canonical-pertama (A) di koneksi tes.
                list(
                    InternetInvoice.objects.select_for_update()
                    .filter(id=inv_a_id, tenant_id=world.tenant.id)
                )
                thread.start()
                assert started.wait(timeout=10), "thread tidak mencapai transaksi"
                # 2) Tunggu thread benar-benar TERBLOKIR menunggu lock.
                assert _wait_backend_lock_wait(pids["t1"]), (
                    "thread verifikasi tidak terblokir pada lock invoice"
                )
                # 3) Probe NOWAIT invoice kedua (B): harus MASIH BEBAS —
                #    thread menunggu A dulu (urutan canonical), bukan
                #    memegang B (urutan teks mentah).
                try:
                    list(
                        InternetInvoice.objects.select_for_update(nowait=True)
                        .filter(id=inv_b_id, tenant_id=world.tenant.id)
                    )
                    second_held_by_thread = False
                except DatabaseError:
                    second_held_by_thread = True
                assert not second_held_by_thread, (
                    "verifikasi memegang kunci invoice kedua sebelum invoice "
                    "pertama — urutan kunci mengikuti teks mentah, bukan "
                    "identitas canonical (REV-1111-01)"
                )
            # 4) Lepas kunci (commit scope) → thread menyelesaikan verifikasi.
        finally:
            thread.join(timeout=JOIN_TIMEOUT_S)
        assert not thread.is_alive(), "thread menggantung (deadlock/timeout)"
        assert results == {"t1": "ok"}, results

        with tenant_scope(world.tenant.id):
            for inv_id in (inv_a_id, inv_b_id):
                fresh = InternetInvoice.objects.get(id=inv_id)
                alloc_sum = PaymentAllocation.objects.filter(invoice_id=inv_id).aggregate(
                    total=Sum("amount")
                )["total"]
                assert fresh.paid_amount == Decimal("100000.00")
                assert alloc_sum == fresh.paid_amount
            effects = _payment_effects(payment.id)
            assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (2, 1, 1, 1)

    def test_concurrent_alias_spellings_serialize_without_deadlock(self):
        """Dua verifikasi pasangan invoice sama dengan campuran ejaan alias
        (kanonik vs BESAR-hyphen/kecil-compact): urutan kunci identitas sama →
        terserialisasi bersih, keduanya berhasil, paid == SUM(alokasi)."""
        inv_a_id = UUID("aaaaaaaa-2222-4333-8444-00000000000a")
        inv_b_id = UUID("bbbbbbbb-3333-4444-8555-00000000000b")
        world = _setup_world(
            "rtrw-cc000010", invoice_totals=["200000", "200000"],
            invoice_ids=[inv_a_id, inv_b_id],
        )
        pay1 = _record_payment(world, "200000")
        pay2 = _record_payment(world, "200000")

        results: dict[str, str] = {}
        pids: dict[str, int] = {}
        start = threading.Barrier(2, timeout=30)
        threads = _start_threads(
            [
                _run_verify("p1", world.tenant.id, pay1.id,
                            [{"invoice_id": str(inv_a_id), "amount": "100000"},
                             {"invoice_id": str(inv_b_id), "amount": "100000"}], start, results, pids),
                _run_verify("p2", world.tenant.id, pay2.id,
                            [{"invoice_id": str(inv_b_id).upper(), "amount": "100000"},
                             {"invoice_id": inv_a_id.hex, "amount": "100000"}], start, results, pids),
            ]
        )
        assert all(not t.is_alive() for t in threads), "thread menggantung ( deadlock/timeout )"
        assert pids["p1"] != pids["p2"], "harus dua koneksi PostgreSQL berbeda"
        assert results == {"p1": "ok", "p2": "ok"}, results

        with tenant_scope(world.tenant.id):
            for inv_id in (inv_a_id, inv_b_id):
                fresh = InternetInvoice.objects.get(id=inv_id)
                alloc_sum = PaymentAllocation.objects.filter(invoice_id=inv_id).aggregate(
                    total=Sum("amount")
                )["total"]
                assert fresh.paid_amount == Decimal("200000.00"), fresh.paid_amount
                assert alloc_sum == fresh.paid_amount == fresh.total_amount
                assert fresh.state == InternetInvoice.State.PAID
            for pay in (pay1, pay2):
                effects = _payment_effects(pay.id)
                assert (effects.allocations, effects.receipts, effects.audit, effects.outbox) == (2, 1, 1, 1)
