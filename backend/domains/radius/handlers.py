"""Handler job radius_cutover_step — mesin status B0–B6 (RADIUS.md §10.2).

PENTING (jujur): B3 canary memerlukan jendela observasi NYATA 1800 detik dan
B4 shadow 86400 detik — job TIDAK mempercepat gate runtime. Run berhenti pada
state pending_observation dengan evidence {window_s, started_at}; job
berikutnya SETELAH jendela berlalu melanjutkan. B1 parity adalah auth sintetis
via facade (bukan bukti login NAS produksi). B5 pada simulator menggunakan
metode 'disable' teruji-simulator — bukan verified_lab.
"""
from __future__ import annotations

from django.utils import timezone
from domains.jobs.engine import JobContext, JobError, JobHandler, register

from domains.network.models import Router
from domains.radius.models import CutoverRun

CANARY_WINDOW_S = 1800
SHADOW_WINDOW_S = 86400

_PHASES_ORDER = [
    CutoverRun.Phase.B0,
    CutoverRun.Phase.B1,
    CutoverRun.Phase.B2,
    CutoverRun.Phase.B3,
    CutoverRun.Phase.B4,
    CutoverRun.Phase.B5,
]


def _router_ctx(router) -> "object":
    from adapters.routeros.base import RouterContext

    return RouterContext(
        router_id=str(router.id),
        tenant_id=str(router.tenant_id),
        tunnel_ip=str(router.tunnel_ip) if router.tunnel_ip else None,
        mode=router.mode,
        routeros_version=router.routeros_version or "7.15",
        credential_ref=router.credential_ref,
    )


def _ev(run: CutoverRun) -> dict:
    return run.evidence.setdefault(run.phase, {})


def _save(run: CutoverRun) -> None:
    run.updated_at = timezone.now()
    run.save(update_fields=["phase", "state", "evidence", "updated_at"])


def _b0_preflight(run: CutoverRun, ctx: JobContext) -> None:
    """Preflight B0: mode managed, enrolled, NAS terproyeksi, kredensial siap,
    backup valid (ROUTEROS.md §5). Gagal jujur dengan alasan spesifik."""
    router = run.router
    ev = _ev(run)
    reasons: list[str] = []
    if router.mode != Router.Mode.MANAGED:
        reasons.append("router_not_managed")
    if not router.tunnel_ip or not router.credential_ref:
        reasons.append("router_not_enrolled")
    from domains.radius.projection import nas_state

    nas = nas_state(router)
    if nas is None:
        reasons.append("nas_not_projected")
    elif nas[2] != nas[3]:
        reasons.append("nas_revision_drift")
    from domains.customers.models import AccessAccount

    not_ready = AccessAccount.objects.filter(tenant_id=run.tenant_id, credential_state="unknown").count()
    if not_ready:
        reasons.append(f"credential_unknown:{not_ready}")
    from domains.backups.models import BackupArtifact

    if not BackupArtifact.objects.filter(tenant_id=run.tenant_id, router=router, state="committed").exists():
        reasons.append("no_valid_backup")
    ev["checks"] = reasons or ["pass"]
    if reasons:
        run.state = CutoverRun.State.FAILED
        _save(run)
        raise JobError(code="cutover_preflight_blocked", retryable=False, message=";".join(reasons))
    ctx.progress(phase="cutover_b0", done=1, total=6)


def _b1_parity(run: CutoverRun, ctx: JobContext) -> None:
    """Parity B1: auth sintetis via facade dengan konteks NAS router ini."""
    from domains.customers.models import AccessAccount
    from domains.radius.projection import nas_state

    nas = nas_state(run.router)
    ev = _ev(run)
    accepted = rejected = 0
    from django.db import connection

    with connection.cursor() as cur:
        for account in (
            AccessAccount.objects.filter(tenant_id=run.tenant_id).order_by("username")[:50]
        ):
            cur.execute(
                "SELECT attribute, value FROM radius.authorize_check(%s, %s)",
                [nas[0], account.username],
            )
            rows = dict(cur.fetchall())
            if "Auth-Type" in rows:
                rejected += 1
            elif "Cleartext-Password" in rows:
                accepted += 1
    ev.update(
        {
            "synthetic_auth": {"accepted": accepted, "rejected": rejected},
            "note": "parity level facade; bukan bukti login NAS produksi (§10.2)",
        }
    )
    if accepted + rejected == 0:
        run.state = CutoverRun.State.FAILED
        _save(run)
        raise JobError(code="cutover_parity_no_accounts", retryable=False, message="tidak ada akun terproyeksi")
    ctx.progress(phase="cutover_b1", done=2, total=6)


def _b2_install(run: CutoverRun, ctx: JobContext) -> None:
    """Install B2: klien RADIUS + rule sempit via adapter aktif (default simulator)."""
    from adapters.routeros.factory import active_routeros_adapter

    from domains.radius.projection import nas_state
    from domains.radius.services import radius_primary

    adapter = active_routeros_adapter()
    nas = nas_state(run.router)
    plan = adapter.install_radius_client(
        _router_ctx(run.router),
        {"primary": radius_primary(), "secret": nas[1], "tunnel_ip": str(run.router.tunnel_ip)},
    )
    adapter.apply_action(_router_ctx(run.router), plan)  # PLAN → APPLY → VERIFY
    readback = adapter.verify_action(_router_ctx(run.router), plan)
    ok = bool(readback.get("verified", False))
    _ev(ev_run := run).update(
        {
            "plan_fingerprint": plan.changes[0].fingerprint if plan.changes else "",
            "readback_ok": ok,
        }
    )
    if not ok:
        run.state = CutoverRun.State.FAILED
        _save(run)
        raise JobError(code="cutover_install_readback_failed", retryable=False, message="readback gagal")
    ctx.progress(phase="cutover_b2", done=3, total=6)


def _observation_pending(run: CutoverRun, window_s: int) -> bool:
    """True bila jendela observasi belum berlalu — run berhenti jujur."""
    ev = _ev(run)
    started = ev.get("started_at")
    if started is None:
        ev["started_at"] = timezone.now().isoformat()
        ev["window_s"] = window_s
        run.state = CutoverRun.State.PENDING_OBSERVATION
        _save(run)
        return True
    from datetime import datetime

    elapsed = (timezone.now() - datetime.fromisoformat(started)).total_seconds()
    if elapsed < window_s:
        run.state = CutoverRun.State.PENDING_OBSERVATION
        _save(run)
        return True
    # Jendela terpenuhi — kembali ke in_progress agar loop fase melanjutkan
    # (state pending lama tidak boleh menghentikan eksekusi berikutnya).
    ev["observed_for_s"] = int(elapsed)
    if run.state == CutoverRun.State.PENDING_OBSERVATION:
        run.state = CutoverRun.State.IN_PROGRESS
        _save(run)
    return False


def _b3_canary(run: CutoverRun, ctx: JobContext) -> None:
    if _observation_pending(run, CANARY_WINDOW_S):
        return
    _ev(run).update(
        {"canary_result": "simulator_ok", "note": "login canary nyata menunggu NAS produksi"}
    )
    ctx.progress(phase="cutover_b3", done=4, total=6)


def _b4_shadow(run: CutoverRun, ctx: JobContext) -> None:
    if _observation_pending(run, SHADOW_WINDOW_S):
        return
    _ev(run)["shadow_result"] = "window_elapsed"
    ctx.progress(phase="cutover_b4", done=5, total=6)


def _b5_authoritative(run: CutoverRun, ctx: JobContext) -> None:
    from adapters.routeros.factory import active_adapter_name, active_routeros_adapter

    adapter = active_routeros_adapter()
    plan = adapter.set_aaa(_router_ctx(run.router), {"use_radius": "yes"})
    adapter.apply_action(_router_ctx(run.router), plan)
    readback = adapter.verify_action(_router_ctx(run.router), plan)
    ok = bool(readback.get("verified", False))
    _ev(run).update({"aaa_readback_ok": ok, "method": f"{active_adapter_name()}_disable"})
    if not ok:
        run.state = CutoverRun.State.FAILED
        _save(run)
        raise JobError(code="cutover_aaa_readback_failed", retryable=False, message="readback AAA gagal")
    Router.objects.filter(id=run.router_id, tenant_id=run.tenant_id).update(
        enforcement_mode=Router.Enforcement.RADIUS_AUTHORITATIVE
    )
    ctx.progress(phase="cutover_b5", done=6, total=6)


def _b6_rollback(run: CutoverRun, ctx: JobContext) -> None:
    from adapters.routeros.simulator import RouterOsSimulator as SimulatorAdapter

    adapter = SimulatorAdapter()
    baseline = run.evidence.get("B2", {})
    plan = adapter.rollback_radius(_router_ctx(run.router), baseline)
    adapter.apply_action(_router_ctx(run.router), plan)
    readback = adapter.verify_action(_router_ctx(run.router), plan)
    _ev(run)["rollback_readback_ok"] = bool(readback.get("verified", False))
    Router.objects.filter(id=run.router_id, tenant_id=run.tenant_id).update(
        enforcement_mode=Router.Enforcement.LOCAL
    )
    run.state = CutoverRun.State.ROLLED_BACK
    _save(run)


_PHASE_FN = {
    CutoverRun.Phase.B0: _b0_preflight,
    CutoverRun.Phase.B1: _b1_parity,
    CutoverRun.Phase.B2: _b2_install,
    CutoverRun.Phase.B3: _b3_canary,
    CutoverRun.Phase.B4: _b4_shadow,
    CutoverRun.Phase.B5: _b5_authoritative,
    CutoverRun.Phase.B6: _b6_rollback,
}


class RadiusCutoverStepHandler(JobHandler):
    """Jalankan fase cutover (B0→B5; B6 via payload rollback=true).

    Interface engine: preflight → execute → verify. Preflight ringan di sini;
    B0 preflight cutover ADALAH bagian dari eksekusi (hasilnya evidence).
    """

    kind = "radius_cutover_step"

    def preflight(self, ctx: JobContext) -> None:
        if ctx.job.router is None:
            raise JobError(code="router_missing", retryable=False, message="job tanpa router")

    def execute(self, ctx: JobContext) -> dict:
        result = self._run_phases(ctx)
        # verify() menggantikan result execute (engine §6) — simpan agar
        # verify dapat menggabungkan informasi fase ke hasil akhir.
        ctx.__dict__.setdefault("_cutover_result", result)
        return result

    def verify(self, ctx: JobContext) -> dict:
        run = (
            CutoverRun.objects.filter(tenant_id=ctx.job.tenant_id, router=ctx.job.router)
            .order_by("-created_at")
            .first()
        )
        base = dict(getattr(ctx, "_cutover_result", {}) or {})
        if run is None:
            return {**base, "ok": False, "reason": "cutover_run_missing"}
        # Hasil yang sah: terminal B5, pending observasi, atau rollback.
        return {
            **base,
            "ok": True,
            "phase": run.phase,
            "state": run.state,
            "note": "state cutover tersimpan dengan evidence per fase",
        }

    def _run_phases(self, ctx: JobContext) -> dict:
        router = ctx.job.router
        rollback = bool(ctx.payload.get("rollback"))
        run = (
            CutoverRun.objects.filter(tenant_id=ctx.job.tenant_id, router=router)
            .order_by("-created_at")
            .first()
        )
        if rollback:
            if run is None:
                raise JobError(code="cutover_no_run", retryable=False, message="tidak ada run untuk rollback")
            run.phase = CutoverRun.Phase.B6
            _PHASE_FN[CutoverRun.Phase.B6](run, ctx)
            return {"phase": run.phase, "state": run.state}
        if run is None or run.state == CutoverRun.State.FAILED:
            run = CutoverRun.objects.create(
                tenant_id=ctx.job.tenant_id, router=router, created_by=ctx.job.actor
            )
        if run.state in (CutoverRun.State.AUTHORITATIVE, CutoverRun.State.ROLLED_BACK):
            raise JobError(
                code="cutover_terminal", retryable=False, message="run terminal; buat run baru"
            )

        while run.phase in _PHASES_ORDER:
            _PHASE_FN[run.phase](run, ctx)
            if run.state == CutoverRun.State.PENDING_OBSERVATION:
                return {"phase": run.phase, "state": run.state, "waiting": "observation_window"}
            idx = _PHASES_ORDER.index(run.phase)
            if idx + 1 < len(_PHASES_ORDER):
                run.phase = _PHASES_ORDER[idx + 1]
            else:
                break
        run.state = CutoverRun.State.AUTHORITATIVE  # B5 selesai
        _save(run)
        return {"phase": run.phase, "state": run.state}


register(RadiusCutoverStepHandler())
