"""Integrasi cutover B0–B6 — kejujuran gate + transisi fase (RADIUS.md §10.2).

Semua akses objek tenant (Router/CutoverRun) berjalan dalam tenant_scope —
RLS fail-closed tanpa konteks. create_job membuka scope sendiri dan TIDAK
dibungkus scope luar (scope bersarang saling me-reset GUC).
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.customers.services import provision_service_draft
from domains.jobs import engine
from domains.network.models import Router
from domains.radius.models import CutoverRun

pytestmark = pytest.mark.integration

_IP = iter(f"100.127.7.{i}" for i in range(10, 100))


def _make_router(tenant, **kw):
    defaults = dict(
        tenant_id=tenant.id, display_name="RC", router_code=f"rtr-cut-{next(_IP)}", tunnel_ip=next(_IP),
        mode=Router.Mode.MANAGED, credential_ref="enc:test",
    )
    defaults.update(kw)
    with tenant_scope(tenant.id):
        return Router.objects.create(**defaults)


def _enroll_and_backup(tenant, router):
    """Siapkan prasyarat B0: akun siap + backup committed + NAS terproyeksi+applied."""
    with tenant_scope(tenant.id):
        provision_service_draft(
            tenant,
            {
                "customer_name": "Pelanggan Cut",
                "username": "cut.user",
                "password": "pw-cut-12345678",
                "kind": "pppoe",
                "package_name": "10M/5M",
                "router_id": str(router.id),
            },
        )
        from domains.backups.models import BackupArtifact
        from domains.radius.projection import project_nas
        from domains.radius.reconciler import mark_applied

        project_nas(router)
        mark_applied(router)  # probe reconciler dianggap lulus (fixture lab)
        BackupArtifact.objects.create(
            tenant_id=tenant.id, router=router, category="prechange",
            generation=1, state="committed", file_name="b.backup",
        )


def _run_cutover_job(tenant, router, *, rollback=False):
    # create_job membuka tenant_scope sendiri — jangan dibungkus scope luar.
    job = engine.create_job(
        tenant_id=tenant.id,
        kind="radius_cutover_step",
        router=router,
        payload={"router_id": str(router.id), **({"rollback": True} if rollback else {})},
    )
    claimed = engine.claim_next()
    assert claimed is not None and str(claimed.id) == str(job.id)
    job = engine.run_claimed(claimed)
    with tenant_scope(tenant.id):  # JobDetail RLS — baca dalam konteks tenant
        job.detail.refresh_from_db()
        result = dict(job.detail.result or {})
    return result, job.state


def _latest_run(tenant, router) -> CutoverRun:
    with tenant_scope(tenant.id):
        return CutoverRun.objects.filter(tenant_id=tenant.id, router=router).latest("created_at")


def _router_mode(tenant, router) -> str:
    with tenant_scope(tenant.id):
        router.refresh_from_db()
        return router.enforcement_mode


class TestCutover:
    def test_b0_fails_honestly_for_read_only_router(self, tenant_a):
        router = _make_router(tenant_a, mode=Router.Mode.READ_ONLY)
        _enroll_and_backup(tenant_a, router)
        result, job_state = _run_cutover_job(tenant_a, router)
        assert job_state == "failed"  # JobError preflight → result tidak tersimpan
        run = _latest_run(tenant_a, router)
        assert run.state == CutoverRun.State.FAILED
        assert "router_not_managed" in run.evidence["B0"]["checks"]

    def test_b0_fails_without_backup(self, tenant_a):
        router = _make_router(tenant_a)
        with tenant_scope(tenant_a.id):
            provision_service_draft(
                tenant_a,
                {"customer_name": "P", "username": "cut2.user", "password": "pw-1234567890ab", "kind": "pppoe"},
            )
            from domains.radius.projection import project_nas
            from domains.radius.reconciler import mark_applied

            project_nas(router)
            mark_applied(router)
        result, job_state = _run_cutover_job(tenant_a, router)
        assert job_state == "failed"
        run = _latest_run(tenant_a, router)
        assert "no_valid_backup" in run.evidence["B0"]["checks"]

    def test_happy_path_reaches_b3_pending_observation(self, tenant_a):
        router = _make_router(tenant_a)
        _enroll_and_backup(tenant_a, router)
        result, job_state = _run_cutover_job(tenant_a, router)
        # B0→B1→B2 selesai; B3 menandai jendela observasi NYATA lalu berhenti.
        assert result["state"] == "pending_observation"
        assert result["waiting"] == "observation_window"
        run = _latest_run(tenant_a, router)
        assert run.phase == CutoverRun.Phase.B3
        assert run.evidence["B3"]["window_s"] == 1800
        assert "started_at" in run.evidence["B3"]
        assert _router_mode(tenant_a, router) == Router.Enforcement.LOCAL  # belum authoritative

    def test_b3_continues_after_window_elapsed(self, tenant_a):
        router = _make_router(tenant_a)
        _enroll_and_backup(tenant_a, router)
        result, _js = _run_cutover_job(tenant_a, router)
        assert result["state"] == "pending_observation"
        # Simulasikan jendela B3+B4 sudah terlewat (backdate evidence — dalam scope).
        from datetime import timedelta

        with tenant_scope(tenant_a.id):
            run = CutoverRun.objects.filter(tenant_id=tenant_a.id, router=router).latest("created_at")
            run.evidence["B3"]["started_at"] = (timezone.now() - timedelta(seconds=1801)).isoformat()
            # B4 belum dimulai — job pertama berhenti di B3; jendela B4 cukup
            # dianggap terlewat karena eksekusi kedua mensimulasikan waktu jauh
            # setelah B3 selesai (konvensi lab: window_s dipenuhi monotonic).
            # B4 dianggap sudah dimulai lama (konvensi lab: waktu jauh maju).
            run.evidence["B4"] = {
                "window_s": 86400,
                "started_at": (timezone.now() - timedelta(seconds=86401)).isoformat(),
            }
            run.save(update_fields=["evidence"])
        result2, _js2 = _run_cutover_job(tenant_a, router)
        assert result2["state"] == "authoritative"
        assert _router_mode(tenant_a, router) == Router.Enforcement.RADIUS_AUTHORITATIVE
        run2 = _latest_run(tenant_a, router)
        assert run2.state == CutoverRun.State.AUTHORITATIVE

    def test_b6_rollback_restores_local(self, tenant_a):
        router = _make_router(tenant_a)
        _enroll_and_backup(tenant_a, router)
        result, _js = _run_cutover_job(tenant_a, router)
        assert result["state"] == "pending_observation"
        result2, _js2 = _run_cutover_job(tenant_a, router, rollback=True)
        assert result2["state"] == "rolled_back"
        assert _router_mode(tenant_a, router) == Router.Enforcement.LOCAL
