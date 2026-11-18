"""Tes integrasi task0020 R3 — sisa defect lifecycle/authority/enrollment.

Regresi kompak di suite CI untuk koreksi temuan controller R3
(report/controller/20261117T212042Z-0020-r3-review.md):

- REV-1711-01: seluruh jalur renewal/transisi/terminal worker wajib lease
  berlaku — lease kedaluwarsa tidak dihidupkan kembali oleh
  heartbeat/progress/CAS envelope tanpa menunggu reconciler.
- REV-1711-04: ``resolve_uncertain(applied=False)`` menolak membuka antrian
  ulang pada job yang attempt-nya masih berjalan di proses ini (kehilangan
  sesi DB ≠ penulis lama aman).
- REV-1711-05: kewenangan dibaca segar DI BAWAH kunci baris enrollment pada
  batas tulisan sensitif — guard dipanggil ulang setelah menunggu lock.
- REV-1811-01: penolakan finalize duplikat memakai galat ter-tipe
  JobError(enrollment_state), bukan NameError → internal_error → uncertain.

Probe controller R3 (FROZEN, 7 assertion) tetap bukti acceptance; tes ini
pin invariant yang sama agar dijaga oleh CI `pytest tests`.
"""
from __future__ import annotations

import threading
import time
import uuid

import pytest
from django.db import connection, connections, transaction
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.engine import JobError
from domains.jobs.models import Job, JobState
from domains.network.models import Router, RouterEnrollment, WireGuardPeer
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


def _tenant_actor(tag: str):
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"{tag}-{suffix}@test.local", full_name=tag.upper(),
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"{tag} {suffix}", namespace=f"rtrw-{tag}-{suffix}"
    )
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    return tenant, actor


def _claimed_job(tenant_id, actor, kind: str = "_test_r3_resid") -> Job:
    job = engine.create_job(tenant_id=tenant_id, kind=kind, actor=actor)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    return claimed


def test_expired_lease_blocks_worker_renewal_paths():
    """REV-1711-01 (R3): heartbeat/progress tidak menghidupkan lease mati.

    Lease kedaluwarsa (tanpa reconciler dijalankan) → kepemilikan hilang untuk
    seluruh jalur pembaruan worker; lease tetap mati, tidak diperpanjang.
    """
    tenant, actor = _tenant_actor("r3-resid-renew")
    job = _claimed_job(tenant.id, actor)
    fresh = Job.objects.get(id=job.id)
    ctx = engine.JobContext(job=fresh, payload={})
    # Kontrol negatif: lease berlaku → renewal sah.
    assert ctx.heartbeat() is True
    # Kontrol negatif: progress pada lease berlaku tetap sah.
    assert ctx.progress(phase="mid") is True
    expired_at = timezone.now() - timezone.timedelta(seconds=5)
    Job.objects.filter(id=job.id).update(lease_expires_at=expired_at)
    ctx_expired = engine.JobContext(job=Job.objects.get(id=job.id), payload={})
    with pytest.raises(engine.OwnershipLost):
        ctx_expired.heartbeat()
    with pytest.raises(engine.OwnershipLost):
        ctx_expired.progress(phase="late")
    after = Job.objects.get(id=job.id)
    assert after.lease_expires_at == expired_at, "lease mati tidak boleh hidup kembali"


def test_envelope_transition_requires_valid_lease():
    """REV-1711-01 (R3): CAS transisi/terminal worker wajib lease berlaku."""
    tenant, actor = _tenant_actor("r3-resid-cas")
    job = _claimed_job(tenant.id, actor)
    Job.objects.filter(id=job.id).update(state=JobState.EXECUTING)
    job = Job.objects.get(id=job.id)
    # Lease berlaku → transisi envelope sah.
    assert engine._fenced_update(
        job, [JobState.EXECUTING], state=JobState.VERIFYING
    ) is True
    expired_at = timezone.now() - timezone.timedelta(seconds=5)
    Job.objects.filter(id=job.id).update(
        state=JobState.EXECUTING, lease_expires_at=expired_at
    )
    job = Job.objects.get(id=job.id)
    # Lease kedaluwarsa → transisi envelope ditolak tanpa menunggu reconciler.
    assert engine._fenced_update(
        job, [JobState.EXECUTING], state=JobState.VERIFYING
    ) is False
    assert Job.objects.get(id=job.id).state == JobState.EXECUTING


def test_resolve_uncertain_rejects_inflight_same_job():
    """REV-1711-04 (R3/R4): readback not-applied ditolak selama attempt hidup.

    Sesi DB mati melepas advisory lock, tetapi adapter lama bisa masih hidup;
    reclaim job yang sama tidak boleh membuka kirim kedua sampai attempt
    run_claimed selesai di proses ini. Job dibuat uncertain lewat jalur NYATA
    (attempt eksekusi gagal uncertain) — uncertain sintetis tanpa identitas
    penulis kini ditolak fail-closed (lihat tes R4: unverifiable).
    """
    tenant, actor = _tenant_actor("r3-inflight")
    executions = []

    class Handler(engine.JobHandler):
        kind = "_test_r3_inflight_uncertain"

        def execute(self, ctx):
            executions.append("run")
            raise JobError(code="simulated_uncertain", retryable=True, uncertain=True)

        def verify(self, ctx):
            raise AssertionError("uncertain tidak boleh masuk verifier")

    engine._REGISTRY[Handler.kind] = Handler()
    try:
        job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor)
        claimed = engine.claim_next()
        assert claimed is not None and claimed.id == job.id
        result = engine.run_claimed(claimed)
        assert result.state == JobState.UNCERTAIN
        uncertain = Job.objects.get(id=job.id)
        try:
            engine._INFLIGHT_ATTEMPTS.add(str(job.id))
            with pytest.raises(ValueError, match="writer_active"):
                engine.resolve_uncertain(uncertain, applied=False)
        finally:
            engine._INFLIGHT_ATTEMPTS.discard(str(job.id))
        # Attempt selesai (receipt writer_ended_at tertulis di finally) +
        # penulis lama terbukti aman (router_id None → tanpa advisory lock)
        # → antrian ulang dibuka dengan fence epoch.
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        assert resolved.state == JobState.RETRY_WAIT
        assert resolved.lease_epoch > uncertain.lease_epoch
    finally:
        engine._REGISTRY.pop(Handler.kind, None)


def test_duplicate_finalize_raises_typed_enrollment_state():
    """REV-1811-01 (R3): penolakan duplikat memakai JobError ter-tipe.

    Sebelumnya JobError tanpa import → NameError → internal_error →
    uncertain palsu; kini penolakan definitif enrollment_state tanpa efek
    Router tambahan.
    """
    tenant, actor = _tenant_actor("r3-resid-dupe")
    suffix = uuid.uuid4().hex[:10]
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id, display_name="dupe", router_code=f"r3d-{suffix}"[:16],
            tunnel_ip="100.128.1.9", mode=Router.Mode.READ_ONLY,
            credential_ref="synthetic",
        )
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="dupe enroll", router_code=f"r3e-{suffix}",
            protocol="wireguard", tunnel_ip="100.128.1.10",
            token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.COMPLETED, created_by=actor, router=router,
        )
        WireGuardPeer.objects.create(
            tenant=tenant, enrollment=enrollment, allowed_ip="100.128.1.10",
            public_key=f"r3-dupe-{suffix}", state=WireGuardPeer.State.PENDING,
        )
    from domains.network import services

    with tenant_scope(tenant.id):
        with pytest.raises(JobError) as excinfo:
            services.finalize_verification(enrollment, source="simulator")
    assert excinfo.value.code == "enrollment_state"
    assert excinfo.value.retryable is False
    with tenant_scope(tenant.id):
        assert Router.objects.filter(tenant=tenant).count() == 1, "tidak ada Router kedua"


def test_finalize_revalidates_authority_under_enrollment_lock():
    """REV-1711-05 (R3): guard kewenangan dipanggil ulang DI BAWAH kunci.

    Entry unit memanggil guard sekali sebelum menunggu kunci baris
    enrollment; setelah tunggu lama (pencabutan bisa ter-commit di sela),
    guard wajib dipanggil LAGI di bawah kunci sebelum Router/kredensial
    ditulis.
    """
    tenant, actor = _tenant_actor("r3-resid-lock")
    suffix = uuid.uuid4().hex[:10]
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="lock enroll", router_code=f"r3l-{suffix}",
            protocol="wireguard", tunnel_ip="100.128.2.7",
            token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        WireGuardPeer.objects.create(
            tenant=tenant, enrollment=enrollment, allowed_ip="100.128.2.7",
            public_key=f"r3-lock-{suffix}", state=WireGuardPeer.State.PENDING,
        )
    from domains.network import services

    calls: list[float] = []
    calls_lock = threading.Lock()
    router_done = threading.Event()
    outcomes: dict = {}

    def authority_guard() -> None:
        with calls_lock:
            calls.append(time.monotonic())

    def worker():
        from django.db import close_old_connections

        close_old_connections()
        try:
            with tenant_scope(tenant.id):
                services.finalize_verification(
                    RouterEnrollment.objects.get(id=enrollment.id),
                    source="simulator",
                    authority_guard=authority_guard,
                )
            router_done.set()
        except BaseException as exc:  # pragma: no cover - gagal jujur
            outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    thread = threading.Thread(target=worker, name="r3-under-lock")
    thread.start()
    try:
        # Pegang kunci baris enrollment dari koneksi pengujian ini selama
        # worker menunggu — guard entry sudah terpanggil, guard bawah kunci
        # BELUM. Scope tenant wajib agar baris terlihat (RLS).
        with tenant_scope(tenant.id), transaction.atomic():
            RouterEnrollment.objects.select_for_update().get(id=enrollment.id)
            deadline = time.monotonic() + 5
            while len(calls) < 1 and time.monotonic() < deadline:
                time.sleep(0.02)
            assert len(calls) == 1, "guard entry unit harus terpanggil"
            # Worker menunggu kunci: belum ada Router, belum ada pemanggilan
            # guard kedua (di bawah kunci).
            assert thread.is_alive(), "worker harus menunggu kunci enrollment"
            with tenant_scope(tenant.id):
                assert Router.objects.filter(tenant=tenant).count() == 0
            time.sleep(0.3)  # jendela tunggu nyata di bawah kunci
            assert len(calls) == 1, "guard bawah kunci belum boleh terpanggil selama menunggu"
        # Kunci dilepas: worker mendapat kunci, guard kedua terpanggil di
        # bawah kunci, Router dibuat, lalu guard ketiga pada BATAS COMMIT
        # setelah seluruh tulisan sensitif unit (REV-1711-05 R4 — termasuk
        # tunggu lock kredensial).
        assert router_done.wait(10), outcomes
        thread.join(10)
        assert "exception" not in outcomes, outcomes
        assert len(calls) == 3, "guard wajib dipanggil ulang di bawah kunci + batas commit (R4)"
        with tenant_scope(tenant.id):
            assert Router.objects.filter(tenant=tenant).count() == 1
            enrollment.refresh_from_db()
            assert enrollment.status == RouterEnrollment.Status.COMPLETED
    finally:
        thread.join(10)
        from django.db import close_old_connections

        close_old_connections()
