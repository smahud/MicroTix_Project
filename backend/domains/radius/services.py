"""Status RADIUS tenant — RouterStatus U19 (kontrak contracts.ts).

Semua angka dari query nyata (radacct/radpostauth); tanpa data → null,
bukan nol palsu (§8: missing ≠ kosong).
"""
from __future__ import annotations

from django.db import connection
from django.utils import timezone


def radius_primary() -> str:
    from domains.network.models import WireGuardHost

    host = WireGuardHost.objects.first()
    if host is None:
        return "unconfigured"
    # Alamat host WireGuard = host pertama subnet carve (mis. 100.127.0.0/16
    # → 100.127.0.1); port auth RADIUS standar 1812.
    prefix = host.subnet_cidr.split("/")[0]
    octets = prefix.split(".")
    if len(octets) == 4:
        octets[3] = "1"
        return f"{'.'.join(octets)}:1812"
    return "100.127.0.1:1812"


def _stats_24h(tenant_id: str):
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FILTER (WHERE reply = 'Access-Accept'), COUNT(*) "
            "FROM radius.radpostauth WHERE tenant_id = %s AND authdate >= %s",
            [tenant_id, cutoff],
        )
        accepted, total = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) FROM radius.radacct WHERE tenant_id = %s AND acctstarttime >= %s",
            [tenant_id, cutoff],
        )
        sessions = cur.fetchone()[0]
        cur.execute(
            "SELECT MAX(acctupdatetime) FROM radius.radacct WHERE tenant_id = %s",
            [tenant_id],
        )
        last = cur.fetchone()[0]
    ratio = round(accepted / total, 4) if total else None
    return ratio, sessions, last


def _migrated_accounts(tenant_id: str, router_id: str | None = None) -> int:
    with connection.cursor() as cur:
        if router_id:
            cur.execute(
                "SELECT COUNT(DISTINCT rc.username) FROM radius.radcheck rc "
                "JOIN radius.nas n ON n.tenant_id = rc.tenant_id "
                "WHERE rc.tenant_id = %s AND n.router_id::text = %s AND rc.attribute = 'Cleartext-Password'",
                [tenant_id, router_id],
            )
        else:
            cur.execute(
                "SELECT COUNT(DISTINCT username) FROM radius.radcheck "
                "WHERE tenant_id = %s AND attribute = 'Cleartext-Password'",
                [tenant_id],
            )
        return cur.fetchone()[0]


def radius_status_for_tenant(tenant_id: str) -> list[dict]:
    from domains.network.models import Router

    out: list[dict] = []
    ratio, sessions, last = _stats_24h(tenant_id)
    for router in Router.objects.filter(tenant_id=tenant_id, released_at=None):
        out.append(_status_row(router, tenant_id, ratio, sessions, last))
    return out


def radius_status_detail(tenant_id: str, router_id: str) -> dict | None:
    from domains.network.models import Router

    router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
    if router is None:
        return None
    ratio, sessions, last = _stats_24h(tenant_id)
    return _status_row(router, tenant_id, ratio, sessions, last)


def _status_row(router, tenant_id: str, ratio, sessions, last) -> dict:
    from domains.radius.projection import nas_state

    nas = nas_state(router)
    if nas is None:
        client_status = "missing_client"
    elif nas[2] != nas[3]:
        client_status = "degraded"  # desired != applied → reconciler belum selesai
    else:
        client_status = "ok"
    return {
        "router_id": str(router.id),
        "enforcement_mode": router.enforcement_mode,
        "migrated_accounts": _migrated_accounts(tenant_id, str(router.id)),
        "auth_success_ratio_24h": ratio,
        "inbound_sessions_24h": sessions,
        "last_accounting_at": last.isoformat() if last else None,
        "radius_primary": radius_primary(),
        "radius_secondary": None,  # Beta: tanpa HA — jujur (RADIUS.md §2).
        "client_status": client_status,
    }
