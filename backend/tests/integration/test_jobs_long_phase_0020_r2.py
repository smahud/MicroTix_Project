"""Tes integrasi task0020 R2 — pemetaan bukti fase panjang (REV-1711-09).

Menutup batas evidence yang diminta controller R2
(report/controller/20261117T170000Z-0020-r2-review.md §3 REV-1711-09):

1. Satu pemanggilan adapter PANJANG (tidak ada titik progress kooperatif di
   dalamnya) tetap memperbarui lease melalui watchdog heartbeat engine
   (HEARTBEAT_S dipakai nyata) sehingga reconciler konkuren yang berulang
   tidak memaksa job menjadi uncertain selama worker masih sah memegang
   lease. Ini membuktikan renewal melewati SATU fase adapter panjang —
   bukan hanya loop progress pendek berulang.
2. Watchdog TIDAK pernah menghidupkan kembali lease kedaluwarsa: pembaruan
   bersyarat (lease masih berlaku saat pembaruan) berhenti jujur setelah
   lease habis/kepemilikan berpindah — keputusan reconcile yang sah tidak
   tertimpa pembaruan lama, dan worker basi tetap di-fence setelah kembali.

Mapping A05/A08 lengkap (assertion → tes → efek durable) ada pada laporan
eksekusi sesi ini. Marker transaction=True: thread worker dan reconciler
memakai koneksi independen; semua participant dibatasi join dan hasilnya
dikumpulkan (exception worker ikut menggagalkan tes).
"""
from __future__ import annotations

import threading
import time

import pytest
from django.utils import timezone as tz

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.engine import JobHandler
from domains.jobs.models import Job, JobState
from domains.network.models import Router
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


def _setup(tag):
    actor = User.objects.create_user(
        email=f"r2lp-{tag}@test.local", full_name=f"R2LP {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R2LP {tag}", namespace=f"rtrw-r2lp-{tag}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id, display_name=tag, router_code=f"R2LP-{tag}"[:16],
            tunnel_ip="100.127.122.1", mode=Router.Mode.MANAGED,
            credential_ref="enc:r2lp-controlled",
        )
    return tenant, actor, router


def _thread(claimed, outcomes, key):
    def run():
        from django.db import connections

        try:
            outcomes[key] = {"state": engine.run_claimed(claimed).state}
        except BaseException as exc:  # pragma: no cover - tes gagal jujur
            outcomes[key] = {"exception": f"{type(exc).__name__}: {exc}"}
        finally:
            connections.close_all()

    worker = threading.Thread(target=run, name=key)
    worker.start()
    return worker


def test_long_active_phase_renews_lease_against_concurrent_reconciler(monkeypatch):
    """REV-1711-09: SATU fase adapter panjang tetap renew lease via watchdog.

    Handler terblokir di dalam satu pemanggilan adapter (tanpa progress
    kooperatif) selama ~3.2s dengan LEASE_S=4/HEARTBEAT_S=0.5; reconciler
    konkuren mencoba expire berulang. Tanpa watchdog, lease habis di tengah
    fase → reconciler memaksa uncertain padahal worker masih hidup dan sah.
    """
    monkeypatch.setattr(engine, "LEASE_S", 4)
    monkeypatch.setattr(engine, "HEARTBEAT_S", 0.5)
    tenant, actor, router = _setup("long-phase")
    release = threading.Event()
    entered = threading.Event()
    outcomes = {}

    class Handler(JobHandler):
        kind = "_test_r2_long_phase"

        def execute(self, ctx):
            entered.set()
            if not release.wait(20):
                raise RuntimeError("root tidak melepas fase adapter panjang")
            return {"ok": True, "kind": "long"}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    worker = _thread(claimed, outcomes, "long-phase")
    try:
        assert entered.wait(15), "worker harus masuk fase adapter"
        initial = Job.objects.get(id=job.id).lease_expires_at
        attempts = 0
        uncertain_seen = False
        renewed_mid = None
        deadline = time.monotonic() + 3.2
        while time.monotonic() < deadline:
            attempts += 1
            assert engine.reconcile_expired_leases() == 0, "reconciler memaksa job uncertain"
            fresh = Job.objects.get(id=job.id)
            if fresh.state != JobState.EXECUTING:
                uncertain_seen = True
                break
            renewed_mid = fresh.lease_expires_at
            time.sleep(0.3)
        assert not uncertain_seen, "job meninggalkan EXECUTING selama fase panjang"
        assert attempts >= 3, "reconciler harus mencoba berulang"
        assert renewed_mid is not None and renewed_mid > initial, (
            "lease harus diperpanjang watchdog melewati nilai claim awal"
        )
        release.set()
    finally:
        release.set()
        worker.join(25)
    assert not worker.is_alive(), "worker harus berhenti terbatas"
    assert set(outcomes) == {"long-phase"}, outcomes
    assert "exception" not in outcomes["long-phase"], outcomes
    assert outcomes["long-phase"]["state"] == JobState.SUCCEEDED, outcomes
    # Watchdog tidak menyisakan thread: pembaruan berikutnya tidak terjadi
    # setelah job terminal (state terminal dikecualikan pembaruan).
    before = Job.objects.get(id=job.id).lease_expires_at
    time.sleep(1.2)
    after = Job.objects.get(id=job.id).lease_expires_at
    assert after == before, "watchdog tidak boleh memperbarui job terminal"


def test_watchdog_does_not_resurrect_expired_lease(monkeypatch):
    """REV-1711-09: pembaruan bersyarat — lease kedaluwarsa tidak dihidupkan
    kembali; keputusan reconcile sah tidak tertimpa pembaruan lama, dan
    worker basi tetap di-fence setelah fase panjangnya selesai.
    """
    monkeypatch.setattr(engine, "LEASE_S", 4)
    monkeypatch.setattr(engine, "HEARTBEAT_S", 0.5)
    tenant, actor, router = _setup("no-resurrect")
    release = threading.Event()
    entered = threading.Event()
    outcomes = {}

    class Handler(JobHandler):
        kind = "_test_r2_no_resurrect"

        def execute(self, ctx):
            entered.set()
            if not release.wait(20):
                raise RuntimeError("root tidak melepas fase adapter panjang")
            return {"ok": True, "kind": "long"}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    worker = _thread(claimed, outcomes, "no-resurrect")
    try:
        assert entered.wait(15), "worker harus masuk fase adapter panjang"
        # Biarkan watchdog memperbarui minimal satu kali (lease maju).
        initial = Job.objects.get(id=job.id).lease_expires_at
        time.sleep(1.2)
        renewed = Job.objects.get(id=job.id).lease_expires_at
        assert renewed > initial, "watchdog harus sempat memperbarui lease"
        # Lease dipaksa habis (operator/reconcile sah); watchdog yang masih
        # hidup TIDAK boleh menghidupkannya kembali.
        expired_at = tz.now() - tz.timedelta(seconds=1)
        Job.objects.filter(id=job.id).update(lease_expires_at=expired_at)
        time.sleep(1.5)  # > 2*HEARTBEAT_S: jendela pembaruan berikutnya lewat
        fresh = Job.objects.get(id=job.id)
        assert fresh.lease_expires_at == expired_at, (
            "lease kedaluwarsa tidak boleh diperpanjang kembali oleh watchdog"
        )
        assert engine.reconcile_expired_leases() == 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        # Worker basi kembali dari fase panjang → tulisan berikutnya di-fence.
        release.set()
    finally:
        release.set()
        worker.join(25)
    assert not worker.is_alive(), "worker harus berhenti terbatas"
    assert set(outcomes) == {"no-resurrect"}, outcomes
    assert "exception" not in outcomes["no-resurrect"], outcomes
    final = Job.objects.get(id=job.id)
    assert final.state == JobState.UNCERTAIN, outcomes
    assert final.lease_token is None, outcomes
