"""Fixture terkontrol untuk harness verifikasi RADIUS nyata (test_radius.sh).

Idemponen: namespace harness dibuat ulang tiap pemanggilan. Dua tenant dengan
username SAMA ('budi.santoso') tetapi password/rate berbeda — bukti isolasi
T19. NAS harness: 127.0.0.2 (tenant A) / 127.0.0.3 (tenant B) karena radclient
tidak dapat bind alamat sumber; harness memakai relay UDP per-NAS.
Secret NAS CSPRNG dan dikembalikan HANYA via stdout JSON sesi harness
(lingkungan disposabel; produksi tidak pernah mencetak secret).
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from domains.common.tenant_context import tenant_scope
from domains.customers.models import AccessAccount, Customer, Service
from domains.customers.services import set_password
from domains.identity.models import User
from domains.network.models import Router
from domains.radius.projection import project_nas
from domains.tenancy.models import Membership, Role, Tenant

NS_A = "smoke-rad-a"
NS_B = "smoke-rad-b"
USERNAME = "budi.santoso"
SUSPENDED_USERNAME = "tunda.user"


def _ensure_tenant(namespace: str, display: str, owner_email: str) -> Tenant:
    user, _ = User.objects.get_or_create(
        email=owner_email, defaults={"full_name": f"Owner {display}", "is_active": True}
    )
    tenant = Tenant.objects.filter(namespace=namespace).first()
    if tenant is None:
        tenant = Tenant.objects.create(display_name=display, namespace=namespace)
    Membership.objects.get_or_create(user=user, tenant=tenant, defaults={"role": Role.OWNER})
    return tenant


class Command(BaseCommand):
    help = "Seed fixture harness RADIUS (dua tenant, username sama, NAS loopback)"

    def handle(self, *args, **options) -> None:
        from domains.radius.projection import deproject_nas

        with transaction.atomic():
            # Idempoten: tenant harness DIPERTAHANKAN (FK subscription), isi
            # domainnya di-reset dalam scope (RLS: di luar scope = 0 baris).
            for stale in Tenant.objects.filter(namespace__in=(NS_A, NS_B)):
                with tenant_scope(stale.id):
                    for router in Router.objects.filter(tenant_id=stale.id):
                        deproject_nas(router)
                        router.delete()
                    AccessAccount.objects.filter(tenant_id=stale.id).delete()
                    Service.objects.filter(tenant_id=stale.id).delete()
                    Customer.objects.filter(tenant_id=stale.id).delete()

            ta = _ensure_tenant(NS_A, "RT Radius Smoke A", "owner-smoke-rad-a@check.local")
            tb = _ensure_tenant(NS_B, "RT Radius Smoke B", "owner-smoke-rad-b@check.local")

            summary: dict[str, dict] = {}
            for tenant, nas_ip, password, rate in (
                (ta, "127.0.0.2", "pw-check-123456", "20M/10M"),
                (tb, "127.0.0.3", "pw-other-654321", "50M/50M"),
            ):
                with tenant_scope(tenant.id):
                    router = Router.objects.create(
                        tenant_id=tenant.id,
                        display_name=f"Router Smoke {tenant.namespace[-1].upper()}",
                        router_code=f"rtr-smoke-{tenant.namespace[-1]}",
                        mode=Router.Mode.MANAGED,
                        tunnel_ip=nas_ip,
                        credential_ref="harness:enrolled",
                    )
                    secret = project_nas(router)  # CSPRNG per-router (§6.4)
                    customer = Customer.objects.create(
                        tenant_id=tenant.id,
                        display_name=f"Pelanggan {USERNAME}",
                        customer_code=f"CUS-SMOKE-{tenant.namespace[-1].upper()}",
                    )
                    service = Service.objects.create(
                        tenant_id=tenant.id,
                        customer=customer,
                        service_code=f"SVC-SMOKE-{tenant.namespace[-1].upper()}",
                        package_name=rate,
                        kind=Service.Kind.PPPOE,
                        lifecycle=Service.Lifecycle.PROVISIONED,
                        router=router,
                    )
                    # Username sama lintas tenant — inti uji T19.
                    account = AccessAccount(
                        tenant_id=tenant.id, service=service, username=USERNAME, kind="pppoe"
                    )
                    set_password(account, password)
                    account.save()
                    if tenant == ta:
                        # Akun suspended dengan password BENAR — tolak karena
                        # policy (Auth-Type Reject), bukan password salah (T20).
                        suspended = AccessAccount(
                            tenant_id=tenant.id,
                            service=service,
                            username=SUSPENDED_USERNAME,
                            kind="pppoe",
                            state="suspended",
                        )
                        set_password(suspended, "pw-tunda-123456")
                        suspended.save()
                    summary[tenant.namespace] = {
                        "tenant_id": str(tenant.id),
                        "nas_ip": nas_ip,
                        "nas_secret": secret,
                        "username": USERNAME,
                        "password_known_by_harness": True,
                    }

        self.stdout.write(json.dumps({"tenants": summary}))
