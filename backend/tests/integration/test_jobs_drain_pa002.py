"""Tes drain worker proses NYATA (J20-A08 / task0020).

Subprocess `python -m tests.drain_worker` (loop claim→run) diberi sinyal
nyata: SIGTERM idle, SIGTERM saat job DB kooperatif, drain deadline saat I/O
terblokir, dan SIGKILL + rekonsiliasi. Status keluar membedakan drained (0)
vs deadline drain terlampaui/incomplete (3). Ini bukan rehearsal
systemd/installer produksi.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time

import pytest

from domains.jobs import engine
from domains.jobs.models import Job, JobState

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
        ],
    ),
]

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXIT_DRAINED = 0
EXIT_DRAIN_DEADLINE = 3


@pytest.fixture(autouse=True)
def _register_drain_handlers():
    """Handler drain harus terdaftar di PROSES TES juga: jalur pemulihan
    (resolve → claim → run) dieksekusi di sini, bukan di subprocess."""
    from tests.drain_handlers import register_all

    register_all()
    yield


def _db_url() -> str:
    """URL koneksi DB uji untuk subprocess (termasuk password bila ada —
    CI memakai password auth, sandbox lokal trust)."""
    from urllib.parse import quote

    from django.db import connection

    settings = connection.settings_dict
    user = quote(settings["USER"] or "", safe="")
    password = quote(settings.get("PASSWORD") or "", safe="")
    auth = f"{user}:{password}@" if password else f"{user}@"
    return (
        f"postgresql://{auth}{settings['HOST']}:{settings['PORT']}/{settings['NAME']}"
    )


def _spawn(*args: str) -> subprocess.Popen:
    env = {
        **os.environ,
        "TEST_DATABASE_URL": _db_url(),
        "MT_STORAGE_ROOT": tempfile.mkdtemp(prefix="mtx-drain-storage-"),
    }
    env.pop("DATABASE_URL", None)
    return subprocess.Popen(
        [sys.executable, "-m", "tests.drain_worker", *args],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_state(job_id, states, timeout_s: float = 20.0) -> Job:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        job = Job.objects.get(id=job_id)
        if job.state in states:
            return job
        time.sleep(0.1)
    return Job.objects.get(id=job_id)


def _make_job(kind: str, payload: dict | None = None):
    from domains.identity.models import User
    from domains.tenancy.models import Membership, Role, Tenant

    owner = User.objects.create_user(
        email=f"drain-{kind}-{int(time.time())}@test.local", full_name="Drain",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"Drain {kind}", namespace=f"rtrw-drain-{int(time.time()*1000)%100000}"
    )
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    return engine.create_job(tenant_id=tenant.id, kind=kind, actor=owner, payload=payload or {})


class TestDrainProcesses:
    def test_sigterm_idle_exits_drained(self):
        """Worker idle menerima SIGTERM: berhenti mengklaim, keluar 0."""
        proc = _spawn("--loop", "--interval", "0.2", "--drain-timeout", "5")
        try:
            time.sleep(1.5)  # biarkan beberapa siklus polling idle
            proc.send_signal(signal.SIGTERM)
            out, _ = proc.communicate(timeout=15)
        finally:
            if proc.poll() is None:  # pragma: no cover
                proc.kill()
                proc.communicate()
        assert proc.returncode == EXIT_DRAINED, out
        assert "drain selesai" in out

    def test_sigterm_completes_cooperative_db_job(self):
        """SIGTERM saat job DB kooperatif berjalan: job DISELESAIKAN, worker
        keluar 0 tanpa klaim baru setelahnya."""
        job = _make_job("_test_drain_db")
        proc = _spawn("--loop", "--interval", "0.2", "--drain-timeout", "10")
        try:
            done = _wait_state(job.id, {JobState.SUCCEEDED, JobState.FAILED}, timeout_s=25)
            proc.send_signal(signal.SIGTERM)
            out, _ = proc.communicate(timeout=15)
        finally:
            if proc.poll() is None:  # pragma: no cover
                proc.kill()
                proc.communicate()
        assert done.state == JobState.SUCCEEDED
        assert proc.returncode == EXIT_DRAINED, out
        assert str(job.id) in out

    def test_drain_deadline_on_blocked_io_holds_job_honestly(self, tmp_path):
        """I/O terblokir melebihi batas drain: job ditahan jujur (uncertain),
        keluar 3 (incomplete, bukan menggantung); pulih lewat resolve+retry."""
        sentinel = tmp_path / "sentinel.txt"
        job = _make_job("_test_drain_io", {"sentinel": str(sentinel)})
        proc = _spawn("--loop", "--interval", "0.2", "--drain-timeout", "2")
        try:
            executing = _wait_state(job.id, {JobState.EXECUTING}, timeout_s=25)
            assert executing.state == JobState.EXECUTING
            proc.send_signal(signal.SIGTERM)
            out, _ = proc.communicate(timeout=20)
        finally:
            if proc.poll() is None:  # pragma: no cover
                proc.kill()
                proc.communicate()
        assert proc.returncode == EXIT_DRAIN_DEADLINE, out
        held = Job.objects.get(id=job.id)
        assert held.state == JobState.UNCERTAIN
        assert held.error_code == "drained_mid_execute", held.error_code
        # Pemulihan: sentinel tersedia → resolve(not applied) → klaim ulang.
        sentinel.write_text("go")
        resolved = engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        assert resolved.state == JobState.RETRY_WAIT
        reclaimed = engine.claim_next()
        assert reclaimed is not None and str(reclaimed.id) == str(job.id)
        finished = engine.run_claimed(reclaimed)
        assert finished.state == JobState.SUCCEEDED

    def test_sigkill_then_reconcile_recovers(self, tmp_path):
        """Proses dibunuh paksa (SIGKILL) saat executing: lease kedaluwarsa →
        reconcile → uncertain; sentinel + resolve → tuntas (recoverability)."""
        sentinel = tmp_path / "sentinel-kill.txt"
        job = _make_job("_test_drain_io", {"sentinel": str(sentinel)})
        proc = _spawn("--loop", "--interval", "0.2", "--drain-timeout", "60")
        try:
            executing = _wait_state(job.id, {JobState.EXECUTING}, timeout_s=25)
            assert executing.state == JobState.EXECUTING
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:  # pragma: no cover
                proc.kill()
                proc.communicate()
        # Lease "kedaluwarsa" (simulasi berlalunya waktu) → recovery durable.
        from django.utils import timezone as tz

        Job.objects.filter(id=job.id).update(lease_expires_at=tz.now() - tz.timedelta(seconds=1))
        assert engine.reconcile_expired_leases() >= 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        sentinel.write_text("go")
        engine.resolve_uncertain(Job.objects.get(id=job.id), applied=False)
        reclaimed = engine.claim_next()
        assert reclaimed is not None and str(reclaimed.id) == str(job.id)
        finished = engine.run_claimed(reclaimed)
        assert finished.state == JobState.SUCCEEDED
