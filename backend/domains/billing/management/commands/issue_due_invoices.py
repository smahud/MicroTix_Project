"""Scheduler penerbitan invoice internet (TK-601/BIL-02).

Pemakaian:
    manage.py issue_due_invoices [--date YYYY-MM-DD] [--tenant NAMESPACE]
                                 [--dry-run]

Perilaku (BIL-02 + AC-BIL):
- Jalankan untuk tiap tenant aktif; "hari ini" dihitung pada ZONA TENANT
  (WIB/WITA/WIT — batas tanggal penagihan mengikuti kalender tenant).
- Layanan layak: lifecycle=provisioned, paket penagihan aktif, start_date
  terisi. Semua periode terutang diterbitkan (catch-up jujur bila scheduler
  lama tidak jalan); UNIQUE periode mencegah duplikat (dua scheduler
  berlomba → satu invoice).
- --dry-run: pratinjau tanpa menulis (jumlah + periode per layanan).
- Idempoten: dijalankan berulang pada hari yang sama tidak menghasilkan
  invoice ganda (lanjutan dari period_index terakhir + UNIQUE DB).

Pemasangan host (systemd timer 01:00) = langkah ops Gate A/G — TIDAK
dipasang diam-diam di sandbox (jujur; instalasi.sh mengaturnya saat gate).
"""
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from domains.billing import services
from domains.common.tenant_context import tenant_scope
from domains.customers.models import Service
from domains.tenancy.models import Tenant


def today_in_timezone(timezone_name: str, *, now=None) -> date:
    """Tanggal kalender 'hari ini' pada zona tenant (I18N-03 WIB/WITA/WIT)."""
    moment = now or dj_timezone.now()
    try:
        return moment.astimezone(ZoneInfo(timezone_name)).date()
    except (KeyError, ValueError, OSError):
        # Zona tak dikenal → default WIB, jangan gagal scheduler seluruh tenant.
        return moment.astimezone(ZoneInfo("Asia/Jakarta")).date()


class Command(BaseCommand):
    help = "Terbitkan invoice internet yang jatuh tempo hari ini (idempoten, zona tenant)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--date", dest="date", default=None, help="Override tanggal (YYYY-MM-DD; default: hari ini per zona tenant)")
        parser.add_argument("--tenant", dest="tenant", default=None, help="Batasi ke namespace tenant tertentu")
        parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Pratinjau tanpa menulis")

    def handle(self, *args, **options) -> None:
        forced_date: date | None = None
        if options["date"]:
            try:
                forced_date = date.fromisoformat(str(options["date"]))
            except ValueError:
                self.stderr.write("Format --date harus YYYY-MM-DD")
                return
        dry_run = bool(options["dry_run"])
        tenants = Tenant.objects.filter(archived_at=None).order_by("created_at", "id")
        if options["tenant"]:
            tenants = tenants.filter(namespace=options["tenant"])
            if not tenants.exists():
                self.stderr.write(f"Tenant namespace tidak ditemukan: {options['tenant']}")
                return

        total_issued = 0
        for tenant in tenants:
            today = forced_date or today_in_timezone(tenant.timezone)
            with tenant_scope(tenant.id):
                due_services = (
                    Service.objects.filter(
                        tenant_id=tenant.id,
                        lifecycle=Service.Lifecycle.PROVISIONED,
                        billing_package__isnull=False,
                        start_date__isnull=False,
                    )
                    .select_related("billing_package", "customer")
                    .order_by("created_at", "id")
                )
                issued_here = 0
                skipped = 0
                for service in due_services:
                    package = service.billing_package
                    if not package.active:
                        continue
                    if dry_run:
                        from domains.billing import calendar as billing_calendar
                        from django.db.models import Max
                        from domains.billing.models import InternetInvoice

                        last = (
                            InternetInvoice.objects.filter(service_id=service.id, kind=package.timing)
                            .aggregate(m=Max("period_index"))
                            ["m"]
                        )
                        indices = billing_calendar.due_period_indices(
                            cycle=package.billing_cycle,
                            timing=package.timing,
                            service_start=service.start_date,
                            last_index_issued=-1 if last is None else last,
                            today=today,
                        )
                        for index in indices:
                            ps, pe = billing_calendar.period_bounds(package.billing_cycle, service.start_date, index)
                            self.stdout.write(
                                f"[DRY] {tenant.namespace} {service.service_code}: "
                                f"{package.timing} #{index} {ps.isoformat()}..{pe.isoformat()}"
                            )
                        continue
                    try:
                        invoices = services.issue_invoice_for_service(
                            tenant=tenant, service=service, today=today
                        )
                        issued_here += len(invoices)
                    except Exception as exc:  # layanan bermasalah tidak menghentikan tenant lain
                        skipped += 1
                        self.stderr.write(
                            f"[SKIP] {tenant.namespace}/{service.service_code}: {type(exc).__name__}: {exc}"
                        )
                total_issued += issued_here
                if issued_here or dry_run:
                    self.stdout.write(
                        f"{tenant.namespace}: terbit {issued_here} invoice (tanggal tenant: {today.isoformat()})"
                    )
        if not dry_run:
            self.stdout.write(f"issue_due_invoices: total {total_issued} invoice terbit")
