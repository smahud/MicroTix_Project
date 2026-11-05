"""API monitoring — U13 (M5).

GET /tenants/{t}/monitor → [MonitorStatus] (routers.read).

Agregasi read-only dari network.Router + RouterHealthSample terbaru per
router — TIDAK membuat model baru. Kejujuran beta (ROUTEROS.md §6):
- Tanpa sampel → group unmonitored; sampel lebih tua 3× poll.health_s →
  stale_data; VPN/API gagal → management_unreachable (kondisi manajemen,
  BUKAN internet pelanggan); kualitas sampel bukan ok → disturbed.
- interfaces: RouterHealthSample belum menyimpan statistik per interface →
  daftar kosong (jujur; bukan angka palsu).
- radius: status layanan berasal dari accounting RADIUS — tanpa data
  accounting (beta) blok ini null, bukan rasio rekayasa.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.views import TenantApiView
from domains.config.registry import registry
from domains.network.models import Router, RouterHealthSample

# ROUTEROS.md §6: "Stale health>3×interval" — interval health defaults 60s.
STALE_MULTIPLIER = 3

# Kelompok U13: Sehat, Terganggu, Tidak terpantau, Data usang,
# "Manajemen tidak terjangkau" (VPN/API).
GROUP_HEALTHY = "healthy"
GROUP_DISTURBED = "disturbed"
GROUP_UNMONITORED = "unmonitored"
GROUP_STALE_DATA = "stale_data"
GROUP_MANAGEMENT_UNREACHABLE = "management_unreachable"

MONITOR_GROUPS = frozenset(
    {GROUP_HEALTHY, GROUP_DISTURBED, GROUP_UNMONITORED, GROUP_STALE_DATA, GROUP_MANAGEMENT_UNREACHABLE}
)


def stale_after_s() -> int:
    return STALE_MULTIPLIER * registry().get_int("poll.health_s")


def radius_block_available() -> bool:
    """Cek runtime: apakah domain radius (pekerjaan paralel) sudah memasang
    tabel accounting-nya. Tanpa tabel → blok radius null (jujur).
    """
    try:
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_schema = 'public' AND table_name LIKE 'radius\\_%'"
                ")"
            )
            return bool(cur.fetchone()[0])
    except Exception:  # pragma: no cover - introspeksi gagal → fail-closed null
        return False


def _radius_block() -> dict | None:
    """Blok radius MonitorStatus — dari accounting RADIUS saja (§6).

    Beta M5: agregasi accounting (rasio autentikasi, sesi masuk, accounting
    terakhir) dilayani domain radius pada /radius-status; monitor tidak
    merekayasa angka tanpa sumber data. Tabel belum ada → null.
    """
    if not radius_block_available():
        return None
    # Tabel radius sudah terpasang tetapi pemetaan agregasi accounting milik
    # domain radius — kembalikan null sampai agregator resmi tersambung.
    return None


def monitor_status(router: Router, latest: RouterHealthSample | None, *, now) -> dict:
    """Bentuk MonitorStatus kontrak frontend (contracts.ts)."""
    if latest is None:
        group = GROUP_UNMONITORED
        observed_at = None
        source = "none"
    else:
        observed_at = latest.observed_at
        source = latest.source or "poller"
        stale = (now - latest.observed_at).total_seconds() > stale_after_s()
        vpn_down = latest.vpn_up is False
        api_down = latest.api_up is False
        if stale:
            group = GROUP_STALE_DATA
        elif vpn_down or api_down:
            # VPN aktif + API gagal (atau sebaliknya) = kondisi manajemen;
            # tidak menyimpulkan internet pelanggan mati (UI_UX §10).
            group = GROUP_MANAGEMENT_UNREACHABLE
        elif (latest.quality or "ok") != "ok":
            group = GROUP_DISTURBED
        else:
            group = GROUP_HEALTHY
    return {
        "router_id": str(router.id),
        "group": group,
        "observed_at": observed_at.isoformat() if observed_at else None,
        "source": source,
        # Statistik per interface belum tersimpan pada sampel kesehatan (M5):
        # daftar kosong — missing sample adalah gap, bukan nol (§6).
        "interfaces": [],
        "radius": _radius_block(),
    }


class MonitorListView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Status monitoring router tenant (agregasi read-only)")
    def get(self, request: Request, tenant_id: str) -> Response:
        from django.utils import timezone

        now = timezone.now()
        statuses = []
        routers = Router.objects.filter(tenant_id=tenant_id, released_at=None).order_by("created_at")
        for router in routers:
            latest = router.health_samples.order_by("-observed_at").first()
            statuses.append(monitor_status(router, latest, now=now))
        return Response(statuses)
