"""Handler job domain network: verify_api_ssl, discover_router,
router_release, router_replace (interface engine: preflight/execute/verify)."""
from __future__ import annotations

from django.utils import timezone
from domains.jobs.engine import JobContext, JobError, JobHandler, register

from domains.network.models import Router, RouterEnrollment, WireGuardPeer


def _ctx_router(ctx: JobContext) -> Router:
    router = ctx.job.router
    if router is None:
        raise JobError(code="router_missing", retryable=False, message="job tanpa router")
    return router


class VerifyApiSslHandler(JobHandler):
    """Verifikasi pasca-bootstrap: tunnel → API-SSL → buat router read-only.

    BETA: jalur simulator — bukti dicatat; tanpa klaim verified_lab.
    """

    kind = "verify_api_ssl"

    def preflight(self, ctx: JobContext) -> None:
        enrollment_id = ctx.payload.get("enrollment_id")
        if not enrollment_id:
            raise JobError(code="enrollment_missing", retryable=False, message="payload tanpa enrollment_id")

    def execute(self, ctx: JobContext) -> dict:
        from domains.common.tenant_context import tenant_scope
        from domains.network import services

        enrollment = RouterEnrollment.objects.filter(id=ctx.payload["enrollment_id"]).first()
        if enrollment is None:
            raise JobError(code="enrollment_missing", retryable=False, message="enrollment tidak ditemukan")
        if enrollment.status == RouterEnrollment.Status.COMPLETED and enrollment.router_id:
            return {"status": "completed", "router_id": str(enrollment.router_id), "replay": True}
        if enrollment.status != RouterEnrollment.Status.BOOTSTRAPPED:
            raise JobError(
                code="enrollment_state", retryable=False, message=f"status {enrollment.status} tidak sah"
            )
        # Engine sudah membuka tenant_scope — scope bersarang me-reset GUC.
        enrollment.status = RouterEnrollment.Status.VERIFYING
        enrollment.save(update_fields=["status"])
        router = services.finalize_verification(enrollment, simulator=True)
        return {"status": "completed", "router_id": str(router.id), "evidence": "simulator"}

    def verify(self, ctx: JobContext) -> dict:
        # Engine sudah dalam tenant_scope — jangan buka scope bersarang.
        enrollment = RouterEnrollment.objects.filter(id=ctx.payload.get("enrollment_id")).first()
        if enrollment is None or enrollment.router_id is None:
            return {"ok": False, "reason": "router_not_created"}
        router = Router.objects.filter(id=enrollment.router_id).first()
        ok = router is not None and router.tunnel_ip == enrollment.tunnel_ip and bool(router.credential_ref)
        peer = WireGuardPeer.objects.filter(router=router).first()
        return {"ok": bool(ok and peer and peer.state == WireGuardPeer.State.APPLIED)}


class DiscoverRouterHandler(JobHandler):
    """Discovery bounded — snapshot + objek tanpa password (ROUTEROS.md §3)."""

    kind = "discover_router"

    def preflight(self, ctx: JobContext) -> None:
        router = _ctx_router(ctx)
        if not router.tunnel_ip:
            raise JobError(code="router_not_enrolled", retryable=False, message="router belum ter-enroll")

    def execute(self, ctx: JobContext) -> dict:
        from domains.network import services

        return services.run_discovery(_ctx_router(ctx))

    def verify(self, ctx: JobContext) -> dict:
        from domains.network.models import DiscoverySnapshot

        router = _ctx_router(ctx)
        snapshot = (
            DiscoverySnapshot.objects.filter(router=router).order_by("-started_at").first()
        )
        ok = snapshot is not None and snapshot.status == DiscoverySnapshot.Status.SUCCEEDED
        return {"ok": ok, "snapshot_id": str(snapshot.id) if snapshot else None}


class RouterReleaseHandler(JobHandler):
    """Lepas router: released_at + peer ditarik + NAS deproyeksi.

    Router fisik TIDAK diubah oleh job ini (operator RouterOS menghapus objek
    rtrw sendiri atau via re-enroll); bukti dicatat jujur.
    """

    kind = "router_release"

    def preflight(self, ctx: JobContext) -> None:
        if _ctx_router(ctx).released_at is not None:
            raise JobError(code="already_released", retryable=False, message="router sudah dilepas")

    def execute(self, ctx: JobContext) -> dict:
        from domains.radius.projection import deproject_nas

        router = _ctx_router(ctx)
        router.released_at = timezone.now()
        router.save(update_fields=["released_at"])
        WireGuardPeer.objects.filter(router=router).update(state=WireGuardPeer.State.REMOVED)
        try:
            deproject_nas(router)
            nas_removed = True
        except Exception:
            nas_removed = False
        return {"released": True, "nas_deprojected": nas_removed,
                "note": "objek rtrw pada router dihapus operator (dokumen runbook)"}

    def verify(self, ctx: JobContext) -> dict:
        router = _ctx_router(ctx)
        return {"ok": router.released_at is not None}


class RouterReplaceHandler(JobHandler):
    """Ganti perangkat: lepas lama (lifecycle replacing) + draft enrollment baru."""

    kind = "router_replace"

    def preflight(self, ctx: JobContext) -> None:
        router = _ctx_router(ctx)
        if router.released_at is not None:
            raise JobError(code="already_released", retryable=False, message="router sudah dilepas")

    def execute(self, ctx: JobContext) -> dict:
        from domains.network import services

        router = _ctx_router(ctx)
        router.released_at = timezone.now()
        router.save(update_fields=["released_at"])
        WireGuardPeer.objects.filter(router=router).update(state=WireGuardPeer.State.REMOVED)
        # create_enrollment kini mengikuti konvensi caller-provides-scope.
        enrollment = services.create_enrollment(
            str(router.tenant_id),
            {
                "display_name": ctx.payload.get("display_name") or f"{router.display_name} (baru)",
                "router_code": f"{router.router_code}-2"[:16],
                "mode": router.mode,
            },
            actor=ctx.job.actor,
        )
        Router.objects.filter(id=router.id).update(replaced_by=None)
        return {
            "released_router_id": str(router.id),
            "new_enrollment_id": str(enrollment.id),
            "state": "enrollment_issued",
        }

    def verify(self, ctx: JobContext) -> dict:
        router = _ctx_router(ctx)
        return {"ok": router.released_at is not None}


register(VerifyApiSslHandler())
register(DiscoverRouterHandler())
register(RouterReleaseHandler())
register(RouterReplaceHandler())
