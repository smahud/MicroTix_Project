"""Handler job domain jaringan: discovery read-only + health probe.

- router_discovery (TK-401): membaca akun PPP/Hotspot via adapter aktif,
  MENYIMPAN snapshot; tidak pernah menulis router dan tidak membaca password.
- router_health_probe (TK-303): sampel kesehatan terpisah per dimensi
  (vpn/api) — data unavailable tidak pernah ditulis sebagai nol.

Adapter aktif dipilih MT_ROUTEROS_ADAPTER (default simulator). Hasil
simulator TIDAK pernah dianggap bukti lab — snapshot mencatat adapternya.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone as dj_timezone

from domains.jobs.engine import JobContext, JobError, JobHandler, register
from domains.network.models import Router, RouterDiscoverySnapshot, RouterHealthSample


def _router_context(router: Router):
    from adapters.routeros.base import RouterContext

    return RouterContext(
        router_id=str(router.id),
        tenant_id=str(router.tenant_id),
        tunnel_ip=router.tunnel_ip,
        mode=router.mode,
        routeros_version=router.routeros_version or "7.15",
        credential_ref=router.credential_ref,
    )


def _adapter():
    from django.conf import settings

    choice = getattr(settings, "MT_ROUTEROS_ADAPTER", "simulator")
    if choice == "simulator":
        from adapters.routeros.simulator import RouterOsSimulator

        return RouterOsSimulator()
    from adapters.routeros.apiclient import ApiSslAdapter

    return ApiSslAdapter()


class RouterDiscoveryHandler(JobHandler):
    kind = "router_discovery"

    def preflight(self, ctx: JobContext) -> None:
        router = Router.objects.filter(id=ctx.payload.get("router_id")).first()
        if router is None:
            raise JobError(code="router_not_found", retryable=False)
        if router.mode not in (Router.Mode.READ_ONLY, Router.Mode.MANAGED):
            raise JobError(code="router_mode_invalid", retryable=False)

    def execute(self, ctx: JobContext) -> dict[str, Any]:
        router = Router.objects.filter(id=ctx.payload.get("router_id")).first()
        assert router is not None
        adapter = _adapter()
        try:
            capabilities = adapter.discover_capabilities(_router_context(router))
            accounts = []
            for kind in ("pppoe", "hotspot"):
                for row in adapter.list_accounts(_router_context(router), kind=kind):
                    # Discovery TIDAK membaca/menyimpan password (ROUTEROS.md §3).
                    accounts.append(
                        {
                            "name": row.get("name"),
                            "kind": kind,
                            "profile": row.get("profile", ""),
                            "disabled": bool(row.get("disabled", False)),
                            "comment": row.get("comment", ""),
                            "remote_address": row.get("remote-address"),
                            "caller_id": row.get("caller-id"),
                        }
                    )
        except Exception as exc:  # adapter errors → JobError dengan kode map
            code = getattr(exc, "code", "router_error")
            raise JobError(code=code, retryable=code in ("router_unreachable",), message=str(exc)) from exc
        from django.conf import settings

        adapter_name = getattr(settings, "MT_ROUTEROS_ADAPTER", "simulator")
        snapshot = RouterDiscoverySnapshot.objects.create(
            tenant_id=router.tenant_id,
            router=router,
            adapter=adapter_name,
            routeros_version=router.routeros_version or "",
            accounts=accounts,
            summary={
                "total": len(accounts),
                "pppoe": sum(1 for a in accounts if a["kind"] == "pppoe"),
                "hotspot": sum(1 for a in accounts if a["kind"] == "hotspot"),
                "disabled": sum(1 for a in accounts if a["disabled"]),
                "capability": [{"name": c.name, "supported": c.supported} for c in capabilities],
            },
            observed_at=dj_timezone.now(),
        )
        ctx.progress(total=len(accounts), done=len(accounts))
        return {"snapshot_id": str(snapshot.id), "summary": snapshot.summary}

    def verify(self, ctx: JobContext) -> dict[str, Any] | None:
        # Readback: snapshot terbaru untuk router ini benar-benar tersimpan.
        snapshot = (
            RouterDiscoverySnapshot.objects.filter(router_id=ctx.payload.get("router_id"))
            .order_by("-created_at")
            .first()
        )
        if snapshot is None:
            raise JobError(code="snapshot_missing", retryable=False)
        # Hasil execute (snapshot_id + summary) dipertahankan engine.
        return None


class RouterHealthProbeHandler(JobHandler):
    kind = "router_health_probe"

    def preflight(self, ctx: JobContext) -> None:
        if not Router.objects.filter(id=ctx.payload.get("router_id")).exists():
            raise JobError(code="router_not_found", retryable=False)

    def execute(self, ctx: JobContext) -> dict[str, Any]:
        router = Router.objects.filter(id=ctx.payload.get("router_id")).first()
        assert router is not None
        adapter = _adapter()
        try:
            health = adapter.read_health(_router_context(router))
        except Exception as exc:
            code = getattr(exc, "code", "router_error")
            # Router unreachable = sampel down yang JUJUR, bukan job gagal.
            if code == "router_unreachable":
                RouterHealthSample.objects.create(
                    tenant_id=router.tenant_id,
                    router=router,
                    vpn_up=False,
                    api_up=False,
                    quality="unreachable",
                    source="adapter",
                )
                return {"vpn_up": False, "api_up": False, "quality": "unreachable"}
            raise JobError(code=code, retryable=code in ("router_unreachable",), message=str(exc)) from exc
        now = dj_timezone.now()
        RouterHealthSample.objects.create(
            tenant_id=router.tenant_id,
            router=router,
            vpn_up=health.get("vpn_up"),
            api_up=health.get("api_up"),
            cpu_percent=health.get("cpu_percent"),
            memory_percent=health.get("memory_percent"),
            uptime_s=health.get("uptime_s"),
            observed_at=now,
            collected_at=now,
            source="adapter",
            quality="ok",
        )
        return {"vpn_up": health.get("vpn_up"), "api_up": health.get("api_up")}

    def verify(self, ctx: JobContext) -> dict[str, Any] | None:
        latest = (
            RouterHealthSample.objects.filter(router_id=ctx.payload.get("router_id")).order_by("-observed_at").first()
        )
        if latest is None:
            raise JobError(code="sample_missing", retryable=False)
        return None


def settings_or_default(name: str):
    from django.conf import settings

    return getattr(settings, name, None)


def register_handlers() -> None:
    from domains.jobs.engine import handler_for

    if handler_for(RouterDiscoveryHandler.kind) is None:
        register(RouterDiscoveryHandler())
    if handler_for(RouterHealthProbeHandler.kind) is None:
        register(RouterHealthProbeHandler())
