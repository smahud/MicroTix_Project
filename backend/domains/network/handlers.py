"""Handler job domain network: verify_api_ssl, discover_router,
router_release, router_replace (interface engine: preflight/execute/verify).

PA-002: setiap unit kerja DB berjalan dalam ctx.scope() (transaksi tenant
pendek); I/O adapter/probe berada DI LUAR unit — tidak ada transaksi/lock
DB yang tertahan melintasi send/readback.
"""
from __future__ import annotations

from django.utils import timezone
from domains.jobs.engine import JobContext, JobError, JobHandler, register

from adapters.routeros.base import RouterOsError
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer


def _ctx_router(ctx: JobContext) -> Router:
    """Router job dari DB segar (RLS tenant aktif di dalam ctx.scope())."""
    router = (
        Router.objects.filter(id=ctx.job.router_id).first()
        if ctx.job.router_id
        else None
    )
    if router is None:
        raise JobError(code="router_missing", retryable=False, message="job tanpa router")
    return router


class VerifyApiSslHandler(JobHandler):
    """Verifikasi pasca-bootstrap: tunnel → API-SSL → buat router read-only.

    Sumber verifikasi = adapter AKTIF (MT_ROUTEROS_ADAPTER) — bukan klaim
    statis. Jalur simulator menyelesaikan enrollment dengan bukti BERLABEL
    jujur (capability.source=simulator, api_ssl/wireguard=False — tidak ada
    koneksi nyata yang dilakukan). Jalur api_ssl melakukan probe TCP+TLS
    nyata; kegagalan → JobError retryable (bounded max_attempts) dengan
    re-entry status VERIFYING pada attempt berikutnya — enrollment TIDAK
    diselesaikan palsu.
    """

    kind = "verify_api_ssl"

    def preflight(self, ctx: JobContext) -> None:
        enrollment_id = ctx.payload.get("enrollment_id")
        if not enrollment_id:
            raise JobError(code="enrollment_missing", retryable=False, message="payload tanpa enrollment_id")

    def execute(self, ctx: JobContext) -> dict:
        from domains.network import services

        # Unit DB pendek: baca enrollment + tandai VERIFYING (commit cepat,
        # terlihat observer) — probe di luar transaksi.
        with ctx.scope():
            enrollment = RouterEnrollment.objects.filter(id=ctx.payload["enrollment_id"]).first()
            if enrollment is None:
                raise JobError(code="enrollment_missing", retryable=False, message="enrollment tidak ditemukan")
            if enrollment.status == RouterEnrollment.Status.COMPLETED and enrollment.router_id:
                return {"status": "completed", "router_id": str(enrollment.router_id), "replay": True}
            # Re-entry sah: BOOTSTRAPPED (attempt pertama) maupun VERIFYING
            # (attempt ulang setelah probe gagal — attempt sebelumnya
            # mempersist VERIFYING; tanpa ini retry terkunci state non-retryable).
            if enrollment.status not in (
                RouterEnrollment.Status.BOOTSTRAPPED,
                RouterEnrollment.Status.VERIFYING,
            ):
                raise JobError(
                    code="enrollment_state", retryable=False, message=f"status {enrollment.status} tidak sah"
                )
            enrollment.status = RouterEnrollment.Status.VERIFYING
            enrollment.save(update_fields=["status"])
        from adapters.routeros.factory import active_adapter_name

        source = active_adapter_name()
        try:
            # Probe (I/O) di luar transaksi DB; commit router+peer dalam unit
            # tenant tersendiri di dalam service — difence guard ownership
            # (REV-1711-01).
            router = services.finalize_verification(
                enrollment, source=source, ownership_guard=ctx.assert_owned
            )
        except RouterOsError as exc:
            # Probe API-SSL nyata gagal (router belum bootstrap penuh / tunnel
            # belum naik) — probe BACA-SAJA tanpa efek: retry bounded eksplisit
            # no-effect (re-entry VERIFYING), tanpa penyelesaian palsu.
            raise JobError(
                code="api_ssl_unreachable", retryable=True, no_effect=True,
                message=f"verifikasi API-SSL gagal: {exc.message}",
            ) from exc
        return {"status": "completed", "router_id": str(router.id), "evidence": source}

    def verify(self, ctx: JobContext) -> dict:
        with ctx.scope():
            enrollment = RouterEnrollment.objects.filter(id=ctx.payload.get("enrollment_id")).first()
            if enrollment is None or enrollment.router_id is None:
                return {"ok": False, "reason": "router_not_created"}
            router = Router.objects.filter(id=enrollment.router_id).first()
            ok = router is not None and router.tunnel_ip == enrollment.tunnel_ip and bool(router.credential_ref)
            if enrollment.protocol == "sstp":
                # SSTP: bukti pemasangan = akun kredensial APPLIED (pola peer WG).
                account = SstpAccount.objects.filter(router=router).first()
                return {"ok": bool(ok and account and account.state == SstpAccount.State.APPLIED)}
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

        with ctx.scope():
            router = _ctx_router(ctx)
        # run_discovery mengelola unit DB pendeknya sendiri; guard ownership
        # dipanggil DI DALAM tiap unit sehingga kehilangan lease membatalkan
        # commit domain sebelum terjadi (REV-1711-01); list_accounts /
        # read_health (I/O adapter) berjalan di luar transaksi.
        return services.run_discovery(router, ownership_guard=ctx.assert_owned)

    def verify(self, ctx: JobContext) -> dict:
        from domains.network.models import DiscoverySnapshot

        with ctx.scope():
            router = _ctx_router(ctx)
            snapshot = (
                DiscoverySnapshot.objects.filter(router=router).order_by("-started_at").first()
            )
            ok = snapshot is not None and snapshot.status == DiscoverySnapshot.Status.SUCCEEDED
            return {"ok": ok, "snapshot_id": str(snapshot.id) if snapshot else None}


class RouterReleaseHandler(JobHandler):
    """Lepas router: released_at + peer ditarik + NAS deproyeksi.

    Router fisik TIDAK diubah oleh job ini (operator RouterOS menghapus objek
    rtrw sendiri atau via re-enroll); bukti dicatat jujur. DB-only → satu
    unit transaksi tenant pendek.
    """

    kind = "router_release"

    def preflight(self, ctx: JobContext) -> None:
        if _ctx_router(ctx).released_at is not None:
            raise JobError(code="already_released", retryable=False, message="router sudah dilepas")

    def execute(self, ctx: JobContext) -> dict:
        from domains.radius.projection import deproject_nas

        with ctx.scope():
            router = _ctx_router(ctx)
            router.released_at = timezone.now()
            router.save(update_fields=["released_at"])
            WireGuardPeer.objects.filter(router=router).update(state=WireGuardPeer.State.REMOVED)
            # Revoke kredensial SSTP (master directive §8: audit revoke — akun
            # dikecualikan dari render chap-secrets berikutnya).
            SstpAccount.objects.filter(router=router).update(state=SstpAccount.State.REMOVED)
            try:
                deproject_nas(router)
                nas_removed = True
            except Exception:
                nas_removed = False
            return {"released": True, "nas_deprojected": nas_removed,
                    "note": "objek rtrw pada router dihapus operator (dokumen runbook)"}

    def verify(self, ctx: JobContext) -> dict:
        with ctx.scope():
            return {"ok": _ctx_router(ctx).released_at is not None}


class RouterReplaceHandler(JobHandler):
    """Ganti perangkat: lepas lama (lifecycle replacing) + draft enrollment baru.

    Kewenangan mengikuti routers.release (ARCHITECTURE §5) — job dibuat oleh
    view dengan izin itu; engine memeriksa ulang dari DB mutakhir.
    """

    kind = "router_replace"

    def preflight(self, ctx: JobContext) -> None:
        if _ctx_router(ctx).released_at is not None:
            raise JobError(code="already_released", retryable=False, message="router sudah dilepas")

    def execute(self, ctx: JobContext) -> dict:
        from domains.network import services

        with ctx.scope():
            router = _ctx_router(ctx)
            router.released_at = timezone.now()
            router.save(update_fields=["released_at"])
            WireGuardPeer.objects.filter(router=router).update(state=WireGuardPeer.State.REMOVED)
            # Revoke kredensial SSTP saat penggantian perangkat (§8 audit revoke).
            SstpAccount.objects.filter(router=router).update(state=SstpAccount.State.REMOVED)
            # create_enrollment mengikuti konvensi caller-provides-scope
            # (scope bersarang reentrant).
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
        with ctx.scope():
            return {"ok": _ctx_router(ctx).released_at is not None}


register(VerifyApiSslHandler())
register(DiscoverRouterHandler())
register(RouterReleaseHandler())
register(RouterReplaceHandler())
