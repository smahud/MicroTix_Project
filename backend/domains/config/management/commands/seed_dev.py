"""Seed data pengembangan: PlanVersion (idempoten) + dua tenant sintetis.

Tenant sintetis untuk pengujian lokal sesuai IMPLEMENTATION_PLAN M0:
"migrasi awal/seed dua tenant". Kredensial seed hanya untuk dev dan ditandai
jelas; tidak dipakai produksi.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from domains.common.tenant_context import tenant_scope
from domains.identity import services as identity_services
from domains.identity.models import User
from domains.subscriptions import services as subs_services
from domains.subscriptions.models import PlanVersion, Subscription
from domains.tenancy.models import Membership, Role, Tenant

DEV_SEED_PASSWORD = "dev-seed-only-2026"  # khusus dev; jangan dipakai di produksi


class Command(BaseCommand):
    help = "Seed paket + dua tenant sintetis (idempoten, dev saja)"

    def handle(self, *args, **options) -> None:
        created_plans = subs_services.seed_plans()
        self.stdout.write(f"plans: {created_plans} baru (total {PlanVersion.objects.count()})")

        free = PlanVersion.objects.filter(code="free").order_by("version").first()

        with transaction.atomic():
            for spec in (
                {"company": "RT Net Nusantara (dev)", "owner_email": "owner-nusantara@dev.local", "owner_name": "Owner Nusantara"},
                {"company": "RW Net Cemara (dev)", "owner_email": "owner-cemara@dev.local", "owner_name": "Owner Cemara"},
            ):
                tenant = Tenant.objects.filter(display_name=spec["company"]).first()
                if tenant is None:
                    tenant = identity_services.create_tenant(spec["company"])
                user = User.objects.filter(email=spec["owner_email"]).first()
                if user is None:
                    user = User.objects.create_user(
                        email=spec["owner_email"],
                        full_name=spec["owner_name"],
                        password=DEV_SEED_PASSWORD,
                        is_active=True,
                    )
                if not Membership.objects.filter(user=user, tenant=tenant).exists():
                    Membership.objects.create(user=user, tenant=tenant, role=Role.OWNER)
                # Tulis data tenant dalam konteks RLS tenant yang benar.
                with tenant_scope(tenant.id):
                    if not Subscription.objects.filter(tenant=tenant).exists():
                        Subscription.objects.create(tenant=tenant, plan=free, state=Subscription.State.FREE)
                self.stdout.write(f"tenant: {tenant.display_name} ({tenant.id}) owner={user.email}")

        self.stdout.write("Seed dev selesai. Password owner seed hanya untuk lingkungan dev.")
