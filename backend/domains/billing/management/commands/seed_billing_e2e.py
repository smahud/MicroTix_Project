"""Seed tenant billing khusus E2E browser (TK-604) — TIDAK untuk produksi.

Membuat tenant sintetis ketiga (terpisah dari seed_dev Nusantara/Cemara agar
asersi empty-state spec lain tidak terdampak) dengan skenario billing nyata:

- Layanan A: invoice LUNAS (dua tahap record→verify lewat services nyata)
  + akun suspended → layak aktivasi (U10 jalur positif).
- Layanan B: invoice OPEN belum dibayar + akun suspended → TIDAK layak
  (validasi pembayaran per item, U10 jalur negatif).
- Layanan C: akun aktif → bukan kandidat aktivasi.

Semua data dibuat melalui jalur services nyata (paket → scheduler issuance →
payment dua tahap) supaya dokumen PDF/kwitansi dan outbox ikut terbentuk.

Reset antar-run harness: bukti keuangan terbit (dokumen/audit) bersifat
immutable by design (trigger DB + FK PROTECT) sehingga TIDAK dihapus —
reset memulihkan state mutabel (payment/alokasi dihapus, state invoice &
akun dikembalikan) agar awal tiap run deterministik.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone as dj_timezone

from domains.billing import services as billing_services
from domains.billing.models import BillingPackage, InternetInvoice, InternetPayment, PaymentAllocation
from domains.common.tenant_context import tenant_scope
from domains.customers.models import AccessAccount, Customer, Service
from domains.identity import services as identity_services
from domains.identity.models import User
from domains.subscriptions.models import PlanVersion, Subscription
from domains.tenancy.models import Membership, Role, Tenant

# Kredensial dev yang sama dengan seed_dev (satu sumber; hanya dev/e2e).
from domains.config.management.commands.seed_dev import DEV_SEED_PASSWORD

TENANT_NAME = "RT Net Billing Demo (e2e)"
OWNER_EMAIL = "owner-billing@dev.local"


class Command(BaseCommand):
    help = "Seed tenant billing E2E (reset state mutabel, dev/e2e saja — jangan produksi)"

    def handle(self, *args, **options) -> None:
        existing = Tenant.objects.filter(display_name=TENANT_NAME).first()
        if existing is not None:
            self._reset(existing)
            self.stdout.write(f"seed_billing_e2e: state tenant dipulihkan ({TENANT_NAME})")
            return
        self._create()
        self.stdout.write(
            f"seed_billing_e2e: {TENANT_NAME} siap (owner={OWNER_EMAIL}; "
            "A=lunas+suspended, B=open+suspended, C=active)"
        )

    def _reset(self, tenant: Tenant) -> None:
        """Pulihkan state mutabel ke titik awal seed.

        Dokumen terbit + audit tetap (immutable by design; artefak lama tidak
        menyetel ulang kwitansi run baru karena lookup per ref_id payment).
        """
        with tenant_scope(tenant.id):
            # Alokasi PROTECT dua sisi → hapus alokasi dulu, lalu payment.
            PaymentAllocation.objects.filter(tenant_id=tenant.id).delete()
            InternetPayment.objects.filter(tenant_id=tenant.id).delete()
            # Invoice kembali ke state awal: A lunas, B terbuka.
            for service_code, state, paid in (("SVC-EB1", InternetInvoice.State.PAID, Decimal("300000")),
                                              ("SVC-EB2", InternetInvoice.State.OPEN, Decimal("0"))):
                invoice = InternetInvoice.objects.filter(
                    tenant_id=tenant.id, service__service_code=service_code
                ).order_by("-period_start").first()
                if invoice is None:
                    raise CommandError(f"reset e2e: invoice {service_code} hilang — jalankan reset DB dev")
                invoice.paid_amount = paid
                invoice.state = state
                invoice.save(update_fields=["paid_amount", "state"])
            # State akun kembali ke awal: A/B suspended, C active.
            for username, state in (("lunas01", AccessAccount.State.SUSPENDED),
                                    ("terbuka02", AccessAccount.State.SUSPENDED),
                                    ("aktif03", AccessAccount.State.ACTIVE)):
                AccessAccount.objects.filter(tenant_id=tenant.id, username=username).update(state=state)

    def _create(self) -> None:
        free = PlanVersion.objects.filter(code="free").order_by("version").first()
        today = dj_timezone.now().date()
        # Periode berjalan: prepaid diterbitkan pada awal periode — start_date
        # awal bulan berjalan menghasilkan tepat satu invoice periode 0.
        period_start = date(today.year, today.month, 1)

        with transaction.atomic():
            tenant = identity_services.create_tenant(TENANT_NAME)
            owner = User.objects.create_user(
                email=OWNER_EMAIL,
                full_name="Owner Billing Demo",
                password=DEV_SEED_PASSWORD,
                is_active=True,
            )
            Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
            with tenant_scope(tenant.id):
                Subscription.objects.create(tenant=tenant, plan=free, state=Subscription.State.FREE)

                package = BillingPackage.objects.create(
                    tenant=tenant,
                    name="Paket 300rb (e2e)",
                    monthly_price=Decimal("300000"),
                )

                def _service(code: str, customer_name: str, username: str, state: str) -> Service:
                    customer = Customer.objects.create(
                        tenant=tenant, display_name=customer_name, customer_code=f"CUST-{code}"
                    )
                    service = Service.objects.create(
                        tenant=tenant,
                        customer=customer,
                        service_code=f"SVC-{code}",
                        lifecycle=Service.Lifecycle.PROVISIONED,
                        start_date=period_start,
                        billing_package=package,
                    )
                    AccessAccount.objects.create(
                        tenant=tenant,
                        service=service,
                        username=username,
                        kind=AccessAccount.Kind.PPPOE,
                        state=state,
                        credential_state=AccessAccount.CredentialState.READY,
                    )
                    return service

                svc_a = _service("EB1", "Andi Lunas", "lunas01", AccessAccount.State.SUSPENDED)
                svc_b = _service("EB2", "Bella Terbuka", "terbuka02", AccessAccount.State.SUSPENDED)
                _service("EB3", "Citra Aktif", "aktif03", AccessAccount.State.ACTIVE)

                # Terbitkan invoice periode berjalan untuk A dan B (jalur
                # scheduler nyata — dokumen PDF ikut terbit).
                for svc in (svc_a, svc_b):
                    billing_services.issue_invoice_for_service(
                        tenant=tenant, service=svc, today=today, actor_display="seed_billing_e2e"
                    )

                # Pelunasan A: dua tahap nyata (record → verify + kwitansi).
                invoice_a = InternetInvoice.objects.filter(service_id=svc_a.id).first()
                payment = billing_services.record_payment(
                    tenant.id,
                    {"method": "cash", "amount": "300000"},
                    actor=owner,
                )
                billing_services.verify_payment(
                    tenant.id,
                    str(payment.id),
                    {"allocations": [{"invoice_id": str(invoice_a.id), "amount": "300000"}]},
                    actor=owner,
                )
