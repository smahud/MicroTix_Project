"""Handler job domain network: verify_api_ssl, discover_router,
router_release, router_replace (interface engine: preflight/execute/verify).

PA-002: setiap unit kerja DB berjalan dalam ctx.scope() (transaksi tenant
pendek); I/O adapter/probe berada DI LUAR unit — tidak ada transaksi/lock
DB yang tertahan melintasi send/readback.
"""
from __future__ import annotations

from django.db import connection
from django.utils import timezone
from domains.jobs.engine import (
    JobContext,
    JobError,
    JobHandler,
    check_current_authority,
    register,
)

from adapters.routeros.base import RouterOsError
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer


def _lock_tenant_referential(tenant_id) -> None:
    """REV-1711-01 (R6): akuisisi kunci referensial baris tenant DI DALAM unit.

    FK Django ke tenancy_tenant adalah DEFERRABLE INITIALLY DEFERRED —
    pemeriksaan referensial berlangsung pada COMMIT dan dapat MENUNGGU kunci
    baris tenant yang dipegang transaksi lain (penomoran billing memakai
    SELECT FOR UPDATE baris tenant). Tunggu SETELAH guard lease terakhir
    membiarkan lease habis selama penantian dan efek tetap commit. Kunci
    referensial (FOR KEY SHARE — mode minimal validasi FK) diambil SEBELUM
    fence akhir unit sehingga seluruh tunggu selesai lebih dulu dan expiry
    divalidasi segar pada batas commit.
    """
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM tenancy_tenant WHERE id = %s FOR KEY SHARE",
            [str(tenant_id)],
        )
        if cur.fetchone() is None:
            raise JobError(
                code="enrollment_state",
                retryable=False,
                message="tenant tidak ditemukan",
            )


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
            # (REV-1711-01) + kewenangan AKTUAL dibaca segar SETELAH I/O pada
            # entry unit efek (REV-1711-05 R2) + guard terkunci sebelum commit
            # (REV-1711-01 R2) + kewenangan final TERKUNCI pada batas commit
            # setelah seluruh tulisan sensitif unit termasuk tunggu lock
            # kredensial (REV-1711-05 R4).
            router = services.finalize_verification(
                enrollment,
                source=source,
                ownership_guard=ctx.assert_owned,
                authority_guard=lambda: check_current_authority(ctx.job, ctx.payload),
                commit_guard=ctx.guard_commit,
                final_authority_guard=lambda: check_current_authority(
                    ctx.job, ctx.payload, lock_membership=True
                ),
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
        # dipanggil DI DALAM tiap unit pada entry, dan commit_guard terkunci
        # (FOR UPDATE) sesaat sebelum commit tiap unit sehingga kehilangan
        # lease membatalkan commit domain sebelum terjadi (REV-1711-01 R2);
        # list_accounts / read_health (I/O adapter) berjalan di luar transaksi.
        return services.run_discovery(
            router, ownership_guard=ctx.assert_owned, commit_guard=ctx.guard_commit
        )

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
            # REV-1711-05 (R6): kewenangan DIBACA SEGAR DI BAWAH KUNCI pada
            # batas efek sensitif — SETELAH seluruh tulisan unit yang dapat
            # menunggu lock domain (baris router/peer/SSTP/NAS) dan SEBELUM
            # guard_commit (fence lease terakhir): guard terkunci memegang
            # baris user + membership sampai commit. Pencabutan/demosi/
            # penonaktifan yang ter-commit SELAMA worker menunggu lock domain
            # terlihat statement segar ini (READ COMMITTED) → unit di-rollback:
            # router tetap aktif, kredensial/NAS tetap. Lease yang valid bukan
            # izin aktor (A06); kontrol operasi berizin tetap commit sekali.
            check_current_authority(ctx.job, ctx.payload, lock_membership=True)
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
            # REV-1711-01 (R6): enrollment pengganti INSERT baris dengan FK
            # DEFERRABLE ke tenant — akuisisi kunci referensial tenant
            # SEBELUM tulisan dan fence akhir (bukan ditunda ke COMMIT yang
            # bisa menunggu lock tenant pihak lain setelah guard lease
            # terakhir dilewati).
            _lock_tenant_referential(router.tenant_id)
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
            # REV-1711-05 (R6): kewenangan DIBACA SEGAR DI BAWAH KUNCI pada
            # batas efek sensitif — SETELAH seluruh tulisan unit (release
            # router lama, revoke kredensial, INSERT enrollment pengganti —
            # termasuk tunggu lock domain dan kunci referensial tenant) dan
            # SEBELUM guard_commit: guard terkunci memegang baris user +
            # membership sampai commit; FK created_by enrollment pengganti
            # juga tercakup kunci user ini pada COMMIT. Pencabutan yang
            # ter-commit selama tunggu → unit di-rollback: router lama tetap
            # aktif, kredensial tetap, NOL enrollment pengganti baru.
            check_current_authority(ctx.job, ctx.payload, lock_membership=True)
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
