"""Handler job radius_cutover_step — mesin state B0–B6 (RADIUS.md §10.2).

PENTING (jujur): B3 canary memerlukan jendela observasi NYATA 1800 detik dan
B4 shadow 86400 detik — job TIDAK mempercepat gate runtime. Run berhenti pada
state pending_observation dengan evidence {window_s, started_at}; job
berikutnya SETELAH jendela berlalu melanjutkan. B1 parity adalah auth sintetis
via facade (bukan bukti login NAS produksi). B5 pada simulator menggunakan
metode 'disable' teruji-simulator — bukan verified_lab.

PA-002/task0020: kerja DB per fase berjalan dalam unit transaksi tenant
pendek (ctx.scope()); APPLY/VERIFY adapter (I/O jaringan) pada B2/B5/B6
berada DI LUAR unit — tidak ada transaksi/lock DB yang tertahan melintasi
send/readback. Jendela observasi B3/B4 tidak diberi deadline pendek.
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

# Fase APPLY/VERIFY adapter (B2/B5/B6) melakukan I/O jaringan — unit DB
# dikelola internal oleh masing-masing fungsi agar send/readback berada di
# luar transaksi (PA-002).
_IO_PHASES = frozenset({CutoverRun.Phase.B2, CutoverRun.Phase.B5})


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


def _b0_preflight(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    """Preflight B0: mode managed, enrolled, NAS terproyeksi, kredensial siap,
    backup valid (ROUTEROS.md §5). Gagal jujur dengan alasan spesifik.
    Evidence kegagalan di-COMMIT dalam unit scope, JobError dilempar SETELAH
    unit selesai — kegagalan tetap terlihat jujur (PA-002)."""
    ev = _ev(run)
    reasons: list[str] = []
    error: JobError | None = None
    with ctx.scope():
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
            error = JobError(code="cutover_preflight_blocked", retryable=False, message=";".join(reasons))
    if error:
        raise error
    ctx.progress(phase="cutover_b0", done=1, total=6)


def _b1_parity(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    """Parity B1: auth sintetis via facade dengan konteks NAS router ini.
    DB-only dalam unit scope; kegagalan di-commit lalu dilempar setelahnya."""
    from domains.customers.models import AccessAccount
    from domains.radius.projection import nas_state

    ev = _ev(run)
    accepted = rejected = 0
    error: JobError | None = None
    with ctx.scope():
        nas = nas_state(router)
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
            error = JobError(code="cutover_parity_no_accounts", retryable=False, message="tidak ada akun terproyeksi")
    if error:
        raise error
    ctx.progress(phase="cutover_b1", done=2, total=6)


def _b2_install(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    """Install B2: klien RADIUS + rule sempit via adapter aktif (default simulator).

    Unit DB (nas read, evidence commit) terpisah dari APPLY/VERIFY adapter
    yang berjalan di luar transaksi (PA-002).
    """
    from adapters.routeros.factory import active_routeros_adapter

    from domains.radius.projection import nas_state
    from domains.radius.services import radius_primary

    adapter = active_routeros_adapter()
    with ctx.scope():
        nas = nas_state(router)
        # PLAN murni (tanpa I/O): boleh dalam unit DB.
        plan = adapter.install_radius_client(
            _router_ctx(router),
            {"primary": radius_primary(), "secret": nas[1], "tunnel_ip": str(router.tunnel_ip)},
        )
    # APPLY → VERIFY = I/O jaringan — DI LUAR transaksi DB.
    adapter.apply_action(_router_ctx(router), plan)
    readback = adapter.verify_action(_router_ctx(router), plan)
    ok = bool(readback.get("verified", False))
    error: JobError | None = None
    with ctx.scope():
        _ev(run).update(
            {
                "plan_fingerprint": plan.changes[0].fingerprint if plan.changes else "",
                "readback_ok": ok,
            }
        )
        if not ok:
            run.state = CutoverRun.State.FAILED
            _save(run)
            error = JobError(code="cutover_install_readback_failed", retryable=False, message="readback gagal")
    if error:
        raise error
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


def _b3_canary(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    with ctx.scope():
        if _observation_pending(run, CANARY_WINDOW_S):
            return
        _ev(run).update(
            {"canary_result": "simulator_ok", "note": "login canary nyata menunggu NAS produksi"}
        )
    ctx.progress(phase="cutover_b3", done=4, total=6)


def _b4_shadow(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    with ctx.scope():
        if _observation_pending(run, SHADOW_WINDOW_S):
            return
        _ev(run)["shadow_result"] = "window_elapsed"
    ctx.progress(phase="cutover_b4", done=5, total=6)


def _b5_authoritative(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    """B5: AAA authoritative — PLAN dalam unit DB; APPLY/VERIFY adapter di
    luar transaksi; evidence + mode router commit dalam unit berikutnya."""
    from adapters.routeros.factory import active_adapter_name, active_routeros_adapter

    adapter = active_routeros_adapter()
    # PLAN murni (tanpa I/O).
    plan = adapter.set_aaa(_router_ctx(router), {"use_radius": "yes"})
    # APPLY → VERIFY = I/O jaringan — DI LUAR transaksi DB (PA-002).
    adapter.apply_action(_router_ctx(router), plan)
    readback = adapter.verify_action(_router_ctx(router), plan)
    ok = bool(readback.get("verified", False))
    error: JobError | None = None
    with ctx.scope():
        _ev(run).update({"aaa_readback_ok": ok, "method": f"{active_adapter_name()}_disable"})
        if not ok:
            run.state = CutoverRun.State.FAILED
            _save(run)
            error = JobError(code="cutover_aaa_readback_failed", retryable=False, message="readback AAA gagal")
        else:
            Router.objects.filter(id=run.router_id, tenant_id=run.tenant_id).update(
                enforcement_mode=Router.Enforcement.RADIUS_AUTHORITATIVE
            )
    if error:
        raise error
    ctx.progress(phase="cutover_b5", done=6, total=6)


def _b6_rollback(run: CutoverRun, ctx: JobContext, router: Router) -> None:
    """B6 rollback — readback menentukan outcome yang jujur (REV-1711-08).

    PLAN murni; APPLY/VERIFY = I/O di luar transaksi DB (REV-1711-07 — fase ini
    dipanggil dari luar unit scope luar). Evidence + mode router di-commit
    dalam unit pendek ter-fence TERPISAH setelah I/O selesai. Readback
    negatif/unknown TIDAK boleh mengklaim LOCAL/ROLLED_BACK/succeeded:
    run FAILED dengan error jujur, enforcement router tidak ditimpa.
    """
    from adapters.routeros.simulator import RouterOsSimulator as SimulatorAdapter

    adapter = SimulatorAdapter()
    baseline = run.evidence.get("B2", {})
    plan = adapter.rollback_radius(_router_ctx(router), baseline)
    # APPLY → VERIFY = I/O jaringan — DI LUAR transaksi DB (REV-1711-07).
    adapter.apply_action(_router_ctx(router), plan)
    readback = adapter.verify_action(_router_ctx(router), plan)
    ok = bool(readback.get("verified", False))
    error: JobError | None = None
    with ctx.scope():
        _ev(run)["rollback_readback_ok"] = ok
        if not ok:
            # Readback negatif: TIDAK ada klaim LOCAL/ROLLED_BACK/succeeded —
            # evidence tersimpan, run gagal jujur (REV-1711-08).
            run.state = CutoverRun.State.FAILED
            _save(run)
            error = JobError(
                code="cutover_rollback_readback_failed",
                retryable=False,
                message="readback rollback negatif — tidak ada klaim rolled_back",
            )
        else:
            Router.objects.filter(id=run.router_id, tenant_id=run.tenant_id).update(
                enforcement_mode=Router.Enforcement.LOCAL
            )
            run.state = CutoverRun.State.ROLLED_BACK
            _save(run)
    if error:
        raise error


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
    Router dimuat segar dalam unit tenant; fase DB-only berjalan dalam
    ctx.scope(), fase adapter (B2/B5/B6) menempatkan APPLY/VERIFY di luar
    unit DB (PA-002).
    """

    kind = "radius_cutover_step"

    def preflight(self, ctx: JobContext) -> None:
        if ctx.job.router_id is None:
            raise JobError(code="router_missing", retryable=False, message="job tanpa router")

    def execute(self, ctx: JobContext) -> dict:
        result = self._run_phases(ctx)
        # verify() menggantikan result execute (engine §6) — simpan agar
        # verify dapat menggabungkan informasi fase ke hasil akhir.
        ctx.__dict__.setdefault("_cutover_result", result)
        return result

    def verify(self, ctx: JobContext) -> dict:
        with ctx.scope():
            run = (
                CutoverRun.objects.filter(tenant_id=ctx.job.tenant_id, router_id=ctx.job.router_id)
                .order_by("-created_at")
                .first()
            )
            base = dict(getattr(ctx, "_cutover_result", {}) or {})
            if run is None:
                return {**base, "ok": False, "reason": "cutover_run_missing"}
            # Hasil yang sah: terminal B5, pending observasi, atau rollback
            # TERBUKTI (readback positif). Run FAILED ≠ sukses (REV-1711-08:
            # verifier menilai state/evidence, bukan sekadar run ada).
            if run.state == CutoverRun.State.FAILED:
                return {**base, "ok": False, "reason": "cutover_run_failed", "state": run.state}
            return {
                **base,
                "ok": True,
                "phase": run.phase,
                "state": run.state,
                "note": "state cutover tersimpan dengan evidence per fase",
            }

    def _run_phases(self, ctx: JobContext) -> dict:
        with ctx.scope():
            router = (
                Router.objects.filter(id=ctx.job.router_id).first()
                if ctx.job.router_id
                else None
            )
            if router is None:
                raise JobError(code="router_missing", retryable=False, message="job tanpa router")
            rollback = bool(ctx.payload.get("rollback"))
            run = (
                CutoverRun.objects.filter(tenant_id=ctx.job.tenant_id, router=router)
                .order_by("-created_at")
                .first()
            )
            rollback_run = None
            if rollback:
                if run is None:
                    raise JobError(code="cutover_no_run", retryable=False, message="tidak ada run untuk rollback")
                run.phase = CutoverRun.Phase.B6
                rollback_run = run
            else:
                if run is None or run.state == CutoverRun.State.FAILED:
                    run = CutoverRun.objects.create(
                        tenant_id=ctx.job.tenant_id, router=router, created_by=ctx.job.actor
                    )
                if run.state in (CutoverRun.State.AUTHORITATIVE, CutoverRun.State.ROLLED_BACK):
                    raise JobError(
                        code="cutover_terminal", retryable=False, message="run terminal; buat run baru"
                    )
        if rollback_run is not None:
            # B6 dipanggil DI LUAR unit scope luar (REV-1711-07): APPLY/VERIFY
            # adapter berjalan tanpa transaksi DB terbuka; fase mengelola unit
            # commit evidence tersendiri.
            _PHASE_FN[CutoverRun.Phase.B6](rollback_run, ctx, router)
            return {"phase": rollback_run.phase, "state": rollback_run.state}

        while run.phase in _PHASES_ORDER:
            if run.phase in (CutoverRun.Phase.B2, CutoverRun.Phase.B5):
                # Batas kirim sensitif berikutnya: kewenangan diperiksa ulang
                # dari DB mutakhir (A06 per-chunk; REV-2011-07) — pencabutan
                # setelah B2 menghentikan B5 tanpa efek baru.
                try:
                    ctx.recheck_authority()
                except JobError as exc:
                    with ctx.scope():
                        run.state = CutoverRun.State.FAILED
                        _save(run)
                    raise exc
            _PHASE_FN[run.phase](run, ctx, router)  # tiap fase mengelola unit scope-nya
            if run.state == CutoverRun.State.PENDING_OBSERVATION:
                return {"phase": run.phase, "state": run.state, "waiting": "observation_window"}
            idx = _PHASES_ORDER.index(run.phase)
            if idx + 1 < len(_PHASES_ORDER):
                run.phase = _PHASES_ORDER[idx + 1]
            else:
                break
        with ctx.scope():
            run.state = CutoverRun.State.AUTHORITATIVE  # B5 selesai
            _save(run)
        return {"phase": run.phase, "state": run.state}


register(RadiusCutoverStepHandler())
