"""Tes integrasi task0020 R2 — kewenangan aktual pada unit efek post-I/O
cutover (REV-R2C-01, kelas defect REV-1711-05).

Reviewer independen menemukan: unit efek post-I/O B5/B6 (flip
enforcement_mode) belum memeriksa ulang kewenangan SETELAH APPLY/VERIFY
adapter. Pencabutan/demosi membership yang terjadi SELAMA I/O harus
menghentikan commit efek sensitif tanpa efek baru — sama seperti jalur
enrollment (REV-1711-05).

Probe ini memakai handler+service produksi sungguhan; hanya I/O adapter
yang dikendalikan (barrier Event). Dua koneksi DB berbeda dibuktikan.
"""
from __future__ import annotations

import json
import threading
import uuid

import pytest
from django.db import connection
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.network.models import Router
from domains.radius.models import CutoverRun
from domains.tenancy.models import Membership, Role, Tenant

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(
        transaction=True,
        available_apps=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "domains.tenancy",
            "domains.identity",
            "domains.network",
            "domains.customers",
            "domains.jobs",
            "domains.audit",
            "domains.radius",
            "domains.backups",
            "domains.subscriptions",
        ],
    ),
]


def test_b6_revocation_during_apply_io_prevents_local_rollback(monkeypatch):
    """Revoke saat APPLY/VERIFY I/O B6: nol flip enforcement/ROLLED_BACK.

    Adapter terkontrol menahan APPLY sampai controller mencabut membership
    aktor dari koneksi DB kedua; SETELAH I/O selesai, unit efek post-I/O
    harus memeriksa kewenangan aktual dan menghentikan commit tanpa efek
    baru (REV-R2C-01).
    """
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r2c-{suffix}@test.local", full_name="R2C",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R2C {suffix}", namespace=f"rtrw-r2c-{suffix}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id, display_name="R2C rollback", router_code=f"r2c-{suffix}"[:16],
            tunnel_ip="100.125.253.253", mode=Router.Mode.MANAGED,
            credential_ref="synthetic", enforcement_mode=Router.Enforcement.RADIUS_AUTHORITATIVE,
        )
        run = CutoverRun.objects.create(
            tenant=tenant, router=router, created_by=actor,
            phase=CutoverRun.Phase.B5, state=CutoverRun.State.AUTHORITATIVE,
            evidence={"B2": {"baseline": "controlled"}},
        )
    job = engine.create_job(
        tenant_id=tenant.id, kind="radius_cutover_step", actor=actor, router=router,
        payload={"rollback": True},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id

    apply_entered, release_apply = threading.Event(), threading.Event()
    pids = {}

    class ControlledAdapter:
        def rollback_radius(self, ctx, baseline):
            return {"controlled_plan": True}

        def apply_action(self, ctx, plan):
            with connection.cursor() as cur:
                cur.execute("SELECT pg_backend_pid()")
                pids["worker"] = cur.fetchone()[0]
            assert not connection.in_atomic_block, "APPLY harus di luar transaksi DB"
            apply_entered.set()
            assert release_apply.wait(15), "controller tidak melepas APPLY"
            return {"applied": True}

        def verify_action(self, ctx, plan):
            return {"verified": True}

    monkeypatch.setattr(
        "adapters.routeros.simulator.RouterOsSimulator", ControlledAdapter
    )

    outcomes = {}

    def worker():
        from django.db import connections

        try:
            final = engine.run_claimed(Job.objects.get(id=job.id))
            outcomes["worker"] = {"state": final.state, "error": final.error_code}
        except BaseException as exc:  # pragma: no cover - tes gagal jujur
            outcomes["worker"] = {"exception": repr(exc)}
        finally:
            connections.close_all()

    thread = threading.Thread(target=worker, name="r2c-revoke-io")
    thread.start()
    results = {}
    try:
        assert apply_entered.wait(15), "handler tidak mencapai APPLY I/O"
        with connection.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            pids["controller"] = cur.fetchone()[0]
        assert pids["controller"] != pids["worker"], "dua koneksi DB berbeda"
        assert Membership.objects.filter(user=actor, tenant=tenant).update(
            revoked_at=timezone.now()
        ) == 1
    finally:
        release_apply.set()
        thread.join(20)

    assert not thread.is_alive(), "worker harus berhenti terbatas"
    assert "exception" not in outcomes.get("worker", {}), outcomes

    with tenant_scope(tenant.id):
        run.refresh_from_db()
        router.refresh_from_db()
        ev_b6 = (run.evidence or {}).get("B6", {})
    observed = {
        "probe": "b6-revoke-during-apply-io",
        **outcomes.get("worker", {}),
        "run_state": run.state,
        "enforcement": router.enforcement_mode,
        "authority_lost": ev_b6.get("authority_lost"),
        "separate_connections": True,
    }
    print(json.dumps(observed, sort_keys=True))
    assert observed.get("state") == JobState.FAILED, observed
    assert observed.get("error") == "authority_denied", observed
    assert run.state == CutoverRun.State.FAILED, observed
    assert router.enforcement_mode == Router.Enforcement.RADIUS_AUTHORITATIVE, observed
    assert ev_b6.get("authority_lost") == "authority_denied", observed
    assert run.state != CutoverRun.State.ROLLED_BACK, observed
