"""Tes integrasi task0020 R5 — residual koreksi R4 (changes_requested).

Regresi kompak di suite CI untuk koreksi temuan controller atas koreksi R4
(report/controller/20261118T050714Z-0020-r4-correction-review.md):

- REV-1811-02 (P2 PARTIAL): worker dengan lease kedaluwarsa TIDAK boleh
  menetapkan failed/retry_wait pada attempt final/nonfinal no-effect — row
  tetap executing dengan token/epoch awal sampai reconciler memutuskan
  (kasus regresi controller test_terminal_lease_review.py). Settlement
  no-effect kini SATU transaksi pendek: step-1 wajib lease valid, step-2
  terikat epoch attempt, on_retry di luar unit, penyelesaian ganda ditolak.
- REV-1711-04 (P1 PARTIAL): readback APPLIED ditolak selama penulis attempt
  masih hidup lintas proses (readback positif ≠ writer berhenti — adapter
  lama bisa masih mengirim); verify-only tanpa resend hanya SETELAH penulis
  terbukti berhenti; nol kirim penerus router sama selama writer hidup;
  router lain tetap maju; resolusi dengan snapshot epoch basi ditolak.
- REV-1711-05 (P1 PARTIAL): penonaktifan akun (identity_user.is_active)
  yang ter-commit SELAMA worker menunggu lock kredensial membatalkan seluruh
  unit efek — Router 0, kredensial PENDING, enrollment belum completed,
  job gagal authority_denied (baris user dikunci + is_active dibaca segar
  DI BAWAH kunci pada batas commit).
- REV-1711-01 (P1 PARTIAL): lease kedaluwarsa selama tunggu lock kredensial
  (tanpa renewal efektif) tidak commit efek DB — validasi token/epoch/state/
  expiry DI BAWAH kunci baris job SETELAH seluruh guard yang dapat menunggu;
  kontrol lease valid menyelesaikan unit tepat sekali.

Probe controller R1–R4 (FROZEN, 28 assertion) tetap bukti acceptance; tes
ini pin invariant yang sama agar dijaga oleh CI `pytest tests`.
"""
from __future__ import annotations

import multiprocessing
import os
import threading
import time
import uuid

import pytest
from django.db import close_old_connections, connection, connections, transaction
from django.test import override_settings
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.engine import JobError
from domains.jobs.models import Job, JobState
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer
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


def _tenant_actor_router(tag: str):
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r5-{tag}-{suffix}@test.local", full_name=f"R5 {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"R5 {tag}", namespace=f"rtrw-r5-{tag}-{suffix}"[:32]
    )
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    router = None
    return tenant, actor, router


def _make_router(tenant, code: str, ip: str) -> Router:
    with tenant_scope(tenant.id):
        return Router.objects.create(
            tenant_id=tenant.id, display_name=code, router_code=code[:16],
            tunnel_ip=ip, mode=Router.Mode.MANAGED, credential_ref="enc:r5-controlled",
        )


# ---------------------------------------------------------------------------
# REV-1811-02 — settlement no-effect wajib lease valid (regresi controller)

class TestExpiredLeaseSettlement:
    @pytest.mark.parametrize("max_attempts", [1, 2], ids=["final", "nonfinal"])
    def test_expired_attempt_leaves_settlement_to_reconcile(self, monkeypatch, max_attempts):
        """Kasus regresi controller (test_terminal_lease_review.py): lease
        kedaluwarsa saat handler melaporkan no-effect → settlement DITOLAK;
        row tetap EXECUTING dengan token/epoch awal tanpa error_code sampai
        reconciler yang memutuskan."""
        tenant, actor, _router = _tenant_actor_router("expired-ne")
        observed = []

        class LocalNoEffect(engine.JobHandler):
            kind = "_test_r5_expired_no_effect"

            def execute(self, ctx):
                expired_at = timezone.now() - timezone.timedelta(seconds=1)
                updated = Job.objects.filter(id=ctx.job.id).update(lease_expires_at=expired_at)
                assert updated == 1
                observed.append("no external effect")
                raise engine.JobError(code="controlled_no_effect", retryable=True, no_effect=True)

            def verify(self, ctx):
                pytest.fail("job no-effect tidak boleh masuk verifier")

        monkeypatch.setitem(engine._REGISTRY, LocalNoEffect.kind, LocalNoEffect())
        job = engine.create_job(tenant_id=tenant.id, kind=LocalNoEffect.kind, actor=actor)
        Job.objects.filter(id=job.id).update(max_attempts=max_attempts)
        claimed = engine.claim_next()
        assert claimed is not None and claimed.id == job.id and claimed.attempt == 1

        returned = engine.run_claimed(claimed)
        fresh = Job.objects.get(id=job.id)
        assert observed == ["no external effect"]
        assert (fresh.state, fresh.lease_token, fresh.lease_epoch, fresh.error_code) == (
            JobState.EXECUTING, claimed.lease_token, claimed.lease_epoch, None,
        ), "lease kedaluwarsa tidak boleh menetapkan settlement sebelum reconcile"
        assert returned.state == JobState.EXECUTING

    def test_no_effect_settlement_rejects_competing_reconcile(self, monkeypatch):
        """Perubahan kepemilikan (reconcile menuntaskan lease) SEBELUM worker
        menulis settlement → step-1 CAS kalah: row uncertain milik reconciler
        tidak ditimpa jalur no-effect worker basi (settlement menunggu
        reconciler; run_claimed mengembalikan row apa adanya)."""
        tenant, actor, _router = _tenant_actor_router("settle-race")

        class Handler(engine.JobHandler):
            kind = "_test_r5_settle_race"

            def execute(self, ctx):
                # Lease kedaluwarsa saat bukti no-effect dideklarasikan —
                # settlement attempt ini harus DITOLAK (row tetap executing).
                Job.objects.filter(id=ctx.job.id).update(
                    lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
                )
                raise JobError(code="router_unreachable", retryable=True, no_effect=True)

            def verify(self, ctx):
                raise AssertionError("tidak boleh masuk verifier")

        monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
        job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor)
        Job.objects.filter(id=job.id).update(max_attempts=2)
        claimed = engine.claim_next()
        assert claimed is not None
        # Settlement attempt ini ditolak (lease basi): row tetap EXECUTING.
        stale_snapshot = engine.run_claimed(claimed)
        assert stale_snapshot.state == JobState.EXECUTING
        assert Job.objects.get(id=job.id).state == JobState.EXECUTING
        # Pihak lain (reconciler) kemudian memindahkan row → UNCERTAIN.
        assert engine.reconcile_expired_leases() == 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        # Worker basi (snapshot executing/token lama) mencoba settlement
        # ulang setelah reconcile → step-1 CAS kalah, row tidak ditimpa.
        with pytest.raises(engine.OwnershipLost):
            engine._retry_no_effect(
                stale_snapshot,
                JobError(code="router_unreachable", retryable=True, no_effect=True),
            )
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN

    def test_no_effect_settlement_single_transition_and_retry_callback_outside(self, monkeypatch):
        """Settlement no-effect lease-valid: tepat SATU penyelesaian (panggilan
        ulang ditolak), transisi tunggal uncertain→retry_wait teramati, dan
        callback on_retry melihat state FINAL (sudah commit) — bukan di dalam
        unit settlement."""
        tenant, actor, _router = _tenant_actor_router("settle-once")
        on_retry_states: list[str] = []
        observed_uncertain = {}

        class Handler(engine.JobHandler):
            kind = "_test_r5_settle_once"

            def execute(self, ctx):
                # Step-1 settlement (executing→uncertain) tidak boleh teramati
                # pihak luar sebagai state akhir: unit settlement selesai atomik.
                raise JobError(code="router_unreachable", retryable=True, no_effect=True)

            def verify(self, ctx):
                raise AssertionError("tidak boleh masuk verifier")

            def on_retry(self, ctx):
                on_retry_states.append(ctx.job.state)

        monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
        job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor)
        Job.objects.filter(id=job.id).update(max_attempts=2)
        claimed = engine.claim_next()
        assert claimed is not None
        result = engine.run_claimed(claimed)
        assert result.state == JobState.RETRY_WAIT
        observed_uncertain["state_after"] = Job.objects.get(id=job.id).state
        assert observed_uncertain["state_after"] == JobState.RETRY_WAIT
        assert on_retry_states == [JobState.RETRY_WAIT], (
            "on_retry wajib melihat state final ter-commit (callback di luar unit settlement)"
        )
        # Penyelesaian ganda dengan snapshot yang sama ditolak (idempotence).
        with pytest.raises(engine.OwnershipLost):
            engine._retry_no_effect(
                Job.objects.get(id=job.id),
                JobError(code="router_unreachable", retryable=True, no_effect=True),
            )
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.RETRY_WAIT and fresh.attempt == 1


# ---------------------------------------------------------------------------
# REV-1711-04 — readback applied + epoch basi

class TestAppliedReadbackWriterProof:
    def test_positive_readback_rejected_while_cross_process_writer_alive(self, monkeypatch):
        """Readback positif (applied=True) tetap DITOLAK selama penulis
        attempt lintas proses masih HIDUP (sesi DB-nya dimatikan, advisory
        lock bebas — /proc starttime yang membuktikan writer aktif); nol
        kirim penerus router sama; router lain tetap maju; SETELAH penulis
        terverifikasi berhenti, verify-only tanpa resend menuntaskan job."""
        tenant, actor, _ = _tenant_actor_router("xproc-applied")
        router = _make_router(tenant, "R5-XPA", "100.127.126.1")
        mp = multiprocessing.get_context("fork")
        finish_writer = mp.Event()
        observer, child_pipe = mp.Pipe(duplex=False)
        parent_pid = os.getpid()
        sends: list[str] = []

        class Handler(engine.JobHandler):
            kind = "_test_r5_xproc_applied"

            def execute(self, ctx):
                if os.getpid() != parent_pid:
                    with connection.cursor() as cur:
                        cur.execute("SELECT pg_backend_pid()")
                        pg_pid = cur.fetchone()[0]
                    child_pipe.send({"event": "entered", "pg_pid": pg_pid})
                    if not finish_writer.wait(30):
                        raise RuntimeError("parent tidak melepas adapter")
                else:
                    sends.append(str(ctx.job.id))
                return {"sent": True}

            def verify(self, ctx):
                return {"ok": True}

        monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
        job = engine.create_job(
            tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router
        )
        claimed = engine.claim_next()
        assert claimed is not None and claimed.id == job.id
        connections.close_all()

        def old_worker():
            try:
                engine.run_claimed(claimed)
                child_pipe.send({"event": "outcome", "state": "returned"})
            except BaseException as exc:
                child_pipe.send({"event": "outcome", "exception": f"{type(exc).__name__}: {exc}"})
            finally:
                connections.close_all()
                child_pipe.close()

        old = mp.Process(target=old_worker, name="r5-old-live-writer-applied")
        old.start()
        child_pipe.close()
        rejected_alive = None
        successor_outcome = None
        other_router_outcome = None
        try:
            assert observer.poll(15), "child harus memasuki adapter terkontrol"
            entered = observer.recv()
            assert entered["event"] == "entered"
            with connection.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(%s, 5000)", [entered["pg_pid"]])
                cur.fetchone()
            assert old.is_alive() and not finish_writer.is_set()
            # Advisory lock sesi mati → bebas; BUKAN bukti writer berhenti.
            assert engine.acquire_router_sender(router.id)
            engine.release_router_sender(router.id)
            Job.objects.filter(id=job.id).update(
                lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
            )
            assert engine.reconcile_expired_leases() == 1
            assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
            # Readback positif saat writer masih hidup → DITOLAK (R5).
            try:
                engine.resolve_uncertain(Job.objects.get(id=job.id), applied=True)
            except ValueError as exc:
                rejected_alive = str(exc)
            assert rejected_alive is not None and "writer_active" in rejected_alive, (
                "readback applied tidak boleh dilepas selama writer lintas proses hidup"
            )
            # Job penerus pada router SAMA ditahan durable hold (nol kirim).
            successor = engine.create_job(
                tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=router
            )
            claimed_successor = engine.claim_next()
            assert claimed_successor is not None and claimed_successor.id == successor.id
            successor_result = engine.run_claimed(claimed_successor)
            successor_outcome = (successor_result.state, successor_result.error_code)
            assert successor_outcome == (
                JobState.RETRY_WAIT, "router_outcome_unknown",
            ), "penerus router sama wajib ditahan selama outcome unknown"
            assert sends == [], "nol kirim penerus router sama selama writer hidup"
            # Router LAIN tetap maju (isolasi hold per-router).
            other_router = _make_router(tenant, "R5-XPB", "100.127.126.2")
            other_job = engine.create_job(
                tenant_id=tenant.id, kind=Handler.kind, actor=actor, router=other_router
            )
            claimed_other = engine.claim_next()
            assert claimed_other is not None and claimed_other.id == other_job.id
            other_result = engine.run_claimed(claimed_other)
            other_router_outcome = other_result.state
            assert other_router_outcome == JobState.SUCCEEDED, "router lain tetap maju"
            live_at_check = old.is_alive() and not finish_writer.is_set()
            assert live_at_check
        finally:
            finish_writer.set()
            old.join(25)
            if old.is_alive():
                old.terminate()
                old.join(5)
        assert not old.is_alive() and old.exitcode == 0
        assert observer.poll(5), "outcome child harus terkumpul"
        outcome = observer.recv()
        observer.close()
        # Penulis terverifikasi berhenti (proses mati) → readback applied
        # diterima: verify-only TANPA resend, jumlah kirim tidak berubah.
        sends_before = len(sends)
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=True)
        assert resolved.state == JobState.SUCCEEDED
        assert len(sends) == sends_before, "verify-only tanpa resend"
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.SUCCEEDED

    @pytest.mark.parametrize("applied", [False, True, None], ids=["not-applied", "applied", "unknown"])
    def test_stale_epoch_resolution_rejected(self, monkeypatch, applied):
        """Snapshot resolve dari epoch LAMA ditolak: bukti/readback epoch
        lama tidak berlaku untuk row uncertain pada attempt baru (epoch naik)."""
        tenant, actor, _router = _tenant_actor_router("stale-epoch")

        class Handler(engine.JobHandler):
            kind = "_test_r5_stale_epoch"

            def execute(self, ctx):
                raise JobError(code="link_flap", retryable=True)  # tanpa no_effect → uncertain

            def verify(self, ctx):
                return {"ok": True}

        monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
        job = engine.create_job(tenant_id=tenant.id, kind=Handler.kind, actor=actor)
        first = engine.claim_next()
        assert first is not None
        assert engine.run_claimed(first).state == JobState.UNCERTAIN
        stale_snapshot = Job.objects.get(id=job.id)  # epoch attempt-1

        # Attempt baru: resolve not-applied (penulis attempt-1 selesai
        # in-process dengan receipt) → retry_wait → claim ulang (epoch naik)
        # → gagal uncertain lagi pada epoch lebih tinggi.
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        assert resolved.state == JobState.RETRY_WAIT
        Job.objects.filter(id=job.id).update(available_at=timezone.now())
        second = engine.claim_next()
        assert second is not None and second.lease_epoch > stale_snapshot.lease_epoch
        assert engine.run_claimed(second).state == JobState.UNCERTAIN
        current_epoch = Job.objects.get(id=job.id).lease_epoch
        assert current_epoch > stale_snapshot.lease_epoch

        # Resolve memakai snapshot epoch lama → DITOLAK, row tidak berubah.
        with pytest.raises(ValueError, match="stale_epoch"):
            engine.resolve_uncertain(stale_snapshot, applied=applied)
        fresh = Job.objects.get(id=job.id)
        assert fresh.state == JobState.UNCERTAIN
        assert fresh.lease_epoch == current_epoch, "epoch attempt baru tidak tertimpa resolve basi"


# ---------------------------------------------------------------------------
# REV-1711-05 + REV-1711-01 — batas commit enrollment setelah tunggu kredensial

def _credential_wait_setup(tag: str, protocol: str):
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r5c-{tag}-{suffix}@test.local", full_name=f"R5 cred {tag}",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"R5 cred {tag}", namespace=f"rtrw-r5c-{tag}-{suffix}"[:32]
    )
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    ip = f"100.124.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}"
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name=f"R5 {tag}", router_code=f"R5{tag[:4].upper()}-{suffix}"[:16],
            protocol=protocol, tunnel_ip=ip, token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        if protocol == "sstp":
            credential = SstpAccount.objects.create(
                tenant=tenant, enrollment=enrollment, tunnel_ip=ip,
                username=f"r5-{suffix}", password_ref="synthetic-not-decrypted",
                state=SstpAccount.State.PENDING,
            )
        else:
            credential = WireGuardPeer.objects.create(
                tenant=tenant, enrollment=enrollment, allowed_ip=ip,
                public_key=f"r5-{suffix}", state=WireGuardPeer.State.PENDING,
            )
    job = engine.create_job(
        tenant_id=tenant.id, kind="verify_api_ssl", actor=actor,
        payload={"enrollment_id": str(enrollment.id)},
    )
    return tenant, actor, enrollment, credential, job


class _ConnectivityAdapter:
    """Probe TLS terkontrol: menandai fase probe lalu menunggu sinyal."""

    def __init__(self, probe_active: threading.Event, finish_probe: threading.Event, pids: dict):
        self.probe_active = probe_active
        self.finish_probe = finish_probe
        self.pids = pids

    def probe_connectivity(self, router_context):
        assert not connection.in_atomic_block
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            self.pids["worker"] = cursor.fetchone()[0]
        self.probe_active.set()
        assert self.finish_probe.wait(15), "observasi TLS tidak dilepas"
        return {"ok": True, "cert_sha256": "b" * 64}


def _run_credential_wait_scenario(monkeypatch, protocol: str, *, mutate_during_wait):
    """Kerangka bersama: worker memasuki unit efek, UPDATE kredensial diblokir
    lock koneksi lain, mutasi (deaktivasi akun / kadaluarsa lease) ter-commit
    SELAMA tunggu, lalu lock dilepas → klaim hasil akhir unit."""
    tag = "deact" if mutate_during_wait else "control"
    tenant, actor, enrollment, credential, job = _credential_wait_setup(tag, protocol)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    probe_active, finish_probe = threading.Event(), threading.Event()
    locked, release_lock = threading.Event(), threading.Event()
    outcomes: dict = {}
    errors: list = []
    lock_outcomes: dict = {}
    pids: dict = {}
    credential_model = type(credential)
    table = credential_model._meta.db_table

    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter",
        lambda: _ConnectivityAdapter(probe_active, finish_probe, pids),
    )

    def worker():
        close_old_connections()
        try:
            final = engine.run_claimed(Job.objects.get(id=claimed.id))
            outcomes.update(state=final.state, error=final.error_code)
        except BaseException as exc:
            errors.append(repr(exc))
        finally:
            connections.close_all()

    def locker():
        close_old_connections()
        try:
            with tenant_scope(tenant.id), transaction.atomic():
                credential_model.objects.select_for_update().get(id=credential.id)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids["locker"] = cursor.fetchone()[0]
                locked.set()
                assert release_lock.wait(20), "lock kredensial tidak dilepas"
            lock_outcomes["committed"] = True
        except BaseException as exc:
            lock_outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    worker_thread = threading.Thread(target=worker, name=f"r5-cred-{tag}-{protocol}")
    lock_thread = threading.Thread(target=locker, name=f"r5-lock-{tag}-{protocol}")
    blocked = False
    observed_query = ""
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        worker_thread.start()
        try:
            assert probe_active.wait(15), "handler tidak sampai TLS"
            lock_thread.start()
            assert locked.wait(15), "baris kredensial tidak terkunci"
            finish_probe.set()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT %s = ANY(pg_blocking_pids(pid)), query "
                        "FROM pg_stat_activity WHERE pid=%s",
                        [pids["locker"], pids["worker"]],
                    )
                    row = cursor.fetchone()
                blocked = bool(row and row[0])
                if blocked:
                    observed_query = row[1]
                    break
                time.sleep(0.01)
            assert blocked, "PG harus mengamati kontensi lock kredensial nyata"
            assert table in observed_query and observed_query.lstrip().upper().startswith("UPDATE"), observed_query
            # Mutasi ter-commit pada koneksi terpisah SELAMA UPDATE sensitif
            # masih tertahan — setelah seluruh pembacaan authority entry.
            mutate_during_wait(tenant=tenant, actor=actor, job_id=claimed.id)
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [
                    pids["locker"], pids["worker"],
                ])
                assert cursor.fetchone()[0], "worker lolos sebelum mutasi ter-commit"
        finally:
            finish_probe.set()
            release_lock.set()
            if lock_thread.ident is not None:
                lock_thread.join(20)
            worker_thread.join(25)
    assert not lock_thread.is_alive() and not worker_thread.is_alive(), "partisipan terbatas"
    assert lock_outcomes == {"committed": True}, lock_outcomes
    assert not errors and "state" in outcomes, {"errors": errors, "outcomes": outcomes}
    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        routers = Router.objects.filter(tenant=tenant).count()
    return {
        "outcomes": outcomes, "routers": routers,
        "enrollment": enrollment, "credential": credential,
        "blocked": blocked, "observed_query": observed_query,
        "actor": actor, "tenant": tenant, "job_id": claimed.id,
    }


class TestCredentialWaitCommitBoundary:
    @pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
    def test_user_deactivation_during_credential_wait_cancels_unit(self, monkeypatch, protocol):
        """REV-1711-05 (R5): akun dinonaktifkan SEBELUM batas commit (selama
        worker menunggu lock kredensial) → Router 0, kredensial PENDING,
        enrollment belum completed, job gagal authority_denied — baris user
        dikunci dan is_active dibaca segar DI BAWAH kunci pada batas commit."""

        def deactivate(*, tenant, actor, job_id):
            assert User.objects.filter(id=actor.id).update(is_active=False) == 1
            assert User.objects.get(id=actor.id).is_active is False

        result = _run_credential_wait_scenario(monkeypatch, protocol, mutate_during_wait=deactivate)
        assert result["routers"] == 0, "akun nonaktif tidak boleh mengaktifkan router"
        assert result["credential"].state == "pending"
        assert result["enrollment"].status != RouterEnrollment.Status.COMPLETED
        assert result["outcomes"]["state"] == JobState.FAILED
        assert result["outcomes"]["error"] == "authority_denied"
        fresh_job = Job.objects.get(id=result["job_id"])
        assert fresh_job.state == JobState.FAILED and fresh_job.error_code == "authority_denied"

    @pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
    def test_lease_expiry_during_credential_wait_cancels_unit(self, monkeypatch, protocol):
        """REV-1711-01 (R5): lease kedaluwarsa selama tunggu lock kredensial
        (tanpa renewal efektif — watchdog bersyarat tidak menghidupkan ulang)
        → NOL efek domain commit: validasi expiry DI BAWAH kunci baris job
        SETELAH seluruh guard yang dapat menunggu; job tidak sukses."""

        def expire_lease(*, tenant, actor, job_id):
            # Baris job TIDAK dikunci worker selama tunggu (urutan R5) —
            # mutasi ini commit bebas; watchdog hanya memperbarui lease yang
            # masih berlaku sehingga tidak menghidupkan kembali.
            Job.objects.filter(id=job_id).update(
                lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
            )

        result = _run_credential_wait_scenario(monkeypatch, protocol, mutate_during_wait=expire_lease)
        assert result["routers"] == 0, "lease basi tidak boleh commit efek domain"
        assert result["credential"].state == "pending"
        assert result["enrollment"].status != RouterEnrollment.Status.COMPLETED
        assert result["outcomes"]["state"] != JobState.SUCCEEDED
        fresh_job = Job.objects.get(id=result["job_id"])
        assert fresh_job.state == JobState.EXECUTING, (
            "ownership hilang jujur: row tetap milik reconciler, bukan failed palsu"
        )
        assert fresh_job.error_code is None

    @pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
    def test_valid_lease_enrollment_commits_once(self, monkeypatch, protocol):
        """Kontrol REV-1711-01/05: lease valid + authority sah → unit efek
        commit TEPAT SEKALI (Router 1, kredensial APPLIED, enrollment
        COMPLETED, job SUCCEEDED) — pengerasan guard tidak memblokir jalur sah."""

        def no_mutation(*, tenant, actor, job_id):
            return None

        result = _run_credential_wait_scenario(monkeypatch, protocol, mutate_during_wait=no_mutation)
        assert result["routers"] == 1
        assert result["credential"].state == "applied"
        assert result["enrollment"].status == RouterEnrollment.Status.COMPLETED
        assert result["outcomes"]["state"] == JobState.SUCCEEDED
        assert result["outcomes"]["error"] is None


def _run_membership_wait_scenario(monkeypatch, protocol: str, *, on_worker_blocked):
    """Kerangka batas commit pada jendela tunggu lock MEMBERSHIP: worker
    memasuki unit efek tanpa kontensi kredensial, lalu guard authority
    terkunci (select_for_update user → membership) MENUNGGU lock membership
    yang dipegang koneksi lain. Selama tunggu itulah urutan guard R4 lama
    kehilangan validitas lease / fakta aktor segar (temuan REV-1711-01/05).
    """
    tag = "mwait"
    tenant, actor, enrollment, credential, job = _credential_wait_setup(tag, protocol)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    probe_active, finish_probe = threading.Event(), threading.Event()
    locked, release_lock = threading.Event(), threading.Event()
    outcomes: dict = {}
    errors: list = []
    lock_outcomes: dict = {}
    pids: dict = {}

    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter",
        lambda: _ConnectivityAdapter(probe_active, finish_probe, pids),
    )

    def worker():
        close_old_connections()
        try:
            final = engine.run_claimed(Job.objects.get(id=claimed.id))
            outcomes.update(state=final.state, error=final.error_code)
        except BaseException as exc:
            errors.append(repr(exc))
        finally:
            connections.close_all()

    def locker():
        close_old_connections()
        try:
            with tenant_scope(tenant.id), transaction.atomic():
                Membership.objects.select_for_update().get(user=actor, tenant=tenant)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids["locker"] = cursor.fetchone()[0]
                locked.set()
                assert release_lock.wait(25), "lock membership tidak dilepas"
            lock_outcomes["committed"] = True
        except BaseException as exc:
            lock_outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    worker_thread = threading.Thread(target=worker, name=f"r5-mwait-{protocol}")
    lock_thread = threading.Thread(target=locker, name=f"r5-mwait-lock-{protocol}")
    blocked = False
    observed_query = ""
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        worker_thread.start()
        try:
            assert probe_active.wait(15), "handler tidak sampai TLS"
            finish_probe.set()
            lock_thread.start()
            assert locked.wait(15), "baris membership tidak terkunci"
            # Tunggu worker benar-benar MENUNGGU lock membership (guard
            # authority terkunci di tengah unit efek).
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT %s = ANY(pg_blocking_pids(pid)), query "
                        "FROM pg_stat_activity WHERE pid=%s",
                        [pids["locker"], pids["worker"]],
                    )
                    row = cursor.fetchone()
                blocked = bool(row and row[0])
                if blocked:
                    observed_query = row[1]
                    break
                time.sleep(0.01)
            assert blocked, "PG harus mengamati worker menunggu lock membership"
            assert "tenancy_membership" in observed_query, observed_query
            on_worker_blocked(
                tenant=tenant, actor=actor, job_id=claimed.id, pids=pids,
                release=release_lock,
            )
        finally:
            finish_probe.set()
            release_lock.set()
            if lock_thread.ident is not None:
                lock_thread.join(20)
            worker_thread.join(25)
    assert not lock_thread.is_alive() and not worker_thread.is_alive(), "partisipan terbatas"
    assert lock_outcomes == {"committed": True}, lock_outcomes
    assert not errors and "state" in outcomes, {"errors": errors, "outcomes": outcomes}
    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        routers = Router.objects.filter(tenant=tenant).count()
    return {
        "outcomes": outcomes, "routers": routers,
        "enrollment": enrollment, "credential": credential,
        "blocked": blocked, "observed_query": observed_query,
        "actor": actor, "tenant": tenant, "job_id": claimed.id,
    }


class TestMembershipWaitCommitBoundary:
    @pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
    def test_membership_wait_deactivation_serialized_under_user_lock(self, monkeypatch, protocol):
        """REV-1711-05 (R5): penonaktifan akun yang berkompetisi SELAMA guard
        authority menunggu lock membership TER-SERIALISASI oleh lock baris
        user (user dikunci lebih dulu, dipegang sampai commit): penonaktifan
        tidak dapat commit di bawah fakta authority yang dipakai unit — ia
        menunggu hingga unit commit, atau (bila lebih dulu) menang dan unit
        batal. Baseline R4 tanpa lock user membiarkan penonaktifan commit
        di tengah-tengah tunggu dengan snapshot aktor basi."""

        deactivation_started = threading.Event()
        deactivation_done = threading.Event()

        def on_worker_blocked(*, tenant, actor, job_id, pids, release):
            def deactivator():
                close_old_connections()
                try:
                    deactivation_started.set()
                    User.objects.filter(id=actor.id).update(is_active=False)
                    deactivation_done.set()
                finally:
                    connections.close_all()

            thread = threading.Thread(target=deactivator, name="r5-deactivator")
            thread.start()
            # Penonaktifan TIDAK boleh selesai selama unit memegang lock user
            # (serialized) — beri jendela pengamatan yang cukup.
            assert not deactivation_done.wait(1.0), (
                "penonaktifan tidak boleh commit di bawah fakta authority unit "
                "(baris user wajib dikunci guard sampai commit)"
            )
            # Lepas lock membership → worker menuntaskan unit (aktor masih
            # aktif pada batas commit) → penonaktifan baru mendarat SETELAHNYA.
            release.set()
            thread.join(30)
            assert deactivation_done.is_set(), "penonaktifan selesai setelah unit commit (serialized)"

        result = _run_membership_wait_scenario(monkeypatch, protocol, on_worker_blocked=on_worker_blocked)
        # Aktor masih aktif pada batas commit → unit sah commit tepat sekali;
        # penonaktifan mendarat SETELAHNYA (urutan serialisasi teramati).
        assert result["routers"] == 1
        assert result["credential"].state == "applied"
        assert result["enrollment"].status == RouterEnrollment.Status.COMPLETED
        assert result["outcomes"]["state"] == JobState.SUCCEEDED
        assert User.objects.get(id=result["actor"].id).is_active is False

    @pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
    def test_membership_wait_lease_expiry_cancels_unit(self, monkeypatch, protocol):
        """REV-1711-01 (R5): lease kedaluwarsa SELAMA guard authority menunggu
        lock membership (tanpa renewal efektif) → NOL efek domain: expiry
        divalidasi ulang DI BAWAH kunci baris job pada commit_guard TERAKHIR,
        setelah seluruh penguncian yang dapat menunggu — bukan sebelum wait
        (urutan R4) yang membiarkan commit dengan lease basi."""

        def expire_lease(*, tenant, actor, job_id, pids, release):
            # Baris job TIDAK dikunci worker selama tunggu membership (urutan
            # R5: commit_guard terakhir) → mutasi expiry commit bebas.
            Job.objects.filter(id=job_id).update(
                lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
            )

        result = _run_membership_wait_scenario(monkeypatch, protocol, on_worker_blocked=expire_lease)
        assert result["routers"] == 0, "lease basi saat tunggu membership tidak boleh commit efek"
        assert result["credential"].state == "pending"
        assert result["enrollment"].status != RouterEnrollment.Status.COMPLETED
        assert result["outcomes"]["state"] != JobState.SUCCEEDED
        fresh_job = Job.objects.get(id=result["job_id"])
        assert fresh_job.state == JobState.EXECUTING, (
            "ownership hilang jujur: row menunggu reconciler, bukan failed palsu"
        )
        assert fresh_job.error_code is None
