"""Engine pekerjaan: claim, lease, fencing, transisi, rekonsiliasi (TK-103).

Aturan (ARCHITECTURE.md §6):
- Claim SKIP LOCKED, transaksi pendek, tanpa menahan lock saat I/O jaringan.
- Actor/permission/policy/revision diperiksa ulang sebelum efek.
- Lease habis pada executing/verifying → uncertain (bukan failed).
- Kompensasi hanya objek/revision yang benar; tidak ada reset global.
- Terminal state tidak dapat diubah; permintaan baru = job baru menautkan asal.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from django.db import transaction
from django.utils import timezone as dj_timezone
from django.db.models import Q
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.jobs.models import (
    CANCEL_OK_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    EffectState,
    Job,
    JobDetail,
    JobState,
    OutboxEvent,
)

logger = logging.getLogger(__name__)

LEASE_S = 30
HEARTBEAT_S = 10
BACKOFF_CAP_S = 300
MAX_ATTEMPTS = 5
OUTBOX_POLL_S = 2


class JobError(Exception):
    """Galat handler: kategorisasi hasil untuk engine."""

    def __init__(self, *, code: str, retryable: bool = False, uncertain: bool = False,
                 recovery_required: bool = False, message: str = "") -> None:
        self.code = code
        self.retryable = retryable
        self.uncertain = uncertain
        self.recovery_required = recovery_required
        self.message = message
        super().__init__(message or code)


@dataclass
class JobContext:
    job: Job
    payload: dict[str, Any] = field(default_factory=dict)

    def heartbeat(self) -> None:
        """Perpanjang lease selama eksekusi berjalan (heartbeat < lease/2)."""
        Job.objects.filter(id=self.job.id, lease_token=self.job.lease_token).update(
            lease_expires_at=timezone.now() + timezone.timedelta(seconds=LEASE_S)
        )

    def progress(self, *, phase: str | None = None, done: int | None = None, total: int | None = None) -> None:
        updates: dict[str, Any] = {}
        if phase is not None:
            updates["phase_label_code"] = phase
        if done is not None:
            updates["items_done"] = done
        if total is not None:
            updates["items_total"] = total
        if updates:
            Job.objects.filter(id=self.job.id, lease_token=self.job.lease_token).update(**updates)


class JobHandler:
    """Antarmuka handler ter-tipe per kind (tidak ada DSL generik)."""

    kind: str = ""

    def preflight(self, ctx: JobContext) -> None:  # default: siap
        return None

    def execute(self, ctx: JobContext) -> dict[str, Any]:
        raise NotImplementedError

    def verify(self, ctx: JobContext) -> dict[str, Any]:
        raise NotImplementedError

    def on_retry(self, ctx: JobContext) -> None:  # default: tidak ada
        return None


_REGISTRY: dict[str, JobHandler] = {}


def register(handler: JobHandler) -> None:
    if handler.kind in _REGISTRY:
        raise ValueError(f"Handler duplikat: {handler.kind}")
    _REGISTRY[handler.kind] = handler


def handler_for(kind: str) -> JobHandler | None:
    return _REGISTRY.get(kind)


# ---------------------------------------------------------------------------
# Pembuatan job + outbox satu transaksi domain


def create_job(
    *,
    tenant_id,
    kind: str,
    actor=None,
    actor_display: str = "",
    router=None,
    payload: dict | None = None,
    request_id: str | None = None,
    deadline_s: int | None = None,
    priority: int = 100,
    origin_job=None,
) -> Job:
    """Buat job + detail + outbox satu transaksi; dikembalikan dalam state queued."""
    if kind not in _REGISTRY and not kind.startswith("_test"):
        # Kind fase aktif hanya yang punya handler terdaftar; mencegah job
        # palsu untuk fitur yang belum dibangun.
        raise ValueError(f"Kind tanpa handler terdaftar: {kind}")
    with tenant_scope(tenant_id):
        with transaction.atomic():
            job = Job.objects.create(
                tenant_id=tenant_id,
                kind=kind,
                actor=actor,
                actor_display=actor_display or getattr(actor, "full_name", "") or getattr(actor, "email", ""),
                router=router,
                request_id=request_id,
                deadline_at=(timezone.now() + timezone.timedelta(seconds=deadline_s)) if deadline_s else None,
                priority=priority,
                origin_job=origin_job,
            )
            JobDetail.objects.create(job=job, tenant_id=tenant_id, payload=payload or {})
            OutboxEvent.objects.create(
                tenant_id=tenant_id,
                event_type="job.created",
                aggregate_type="job",
                aggregate_id=job.id,
                dedup_key=f"job:created:{job.id}",
                payload={"kind": kind},
            )
            return job


# ---------------------------------------------------------------------------
# Claim + eksekusi


def claim_next(worker_id: str | None = None) -> Job | None:
    """Klaim satu job queued (atau retry_wait yang telah jatuh tempo).

    SELECT ... FOR UPDATE SKIP LOCKED; transaksi pendek tanpa I/O jaringan.
    """
    now = timezone.now()
    with transaction.atomic():
        job = (
            Job.objects.select_for_update(skip_locked=True)
            .filter(
                Q(state=JobState.QUEUED, available_at__lte=now)
                | Q(state=JobState.RETRY_WAIT, available_at__lte=now)
            )
            .order_by("priority", "id")
            .first()
        )
        if job is None:
            return None
        previous = job.state
        job.state = JobState.CLAIMED
        job.attempt += 1
        job.lease_token = uuid.uuid4()
        job.lease_epoch += 1
        job.lease_expires_at = now + timezone.timedelta(seconds=LEASE_S)
        if previous == JobState.RETRY_WAIT:
            # retry_wait → queued → claimed sesuai mesin state.
            job.state = JobState.QUEUED
            job.save()
            job.state = JobState.CLAIMED
        job.save()
        return job


def _fenced_save(job: Job, **fields) -> bool:
    """Simpan hanya bila lease masih milik worker ini (fencing epoch)."""
    rows = Job.objects.filter(id=job.id, lease_token=job.lease_token, lease_epoch=job.lease_epoch).update(
        **fields
    )
    return rows > 0


def transition_claimed(job: Job, new_state: str, **fields) -> None:
    """Transisi state dengan validasi mesin state (dipakai worker & API).

    Memakai queryset update agar kemajuan items (ditulis heartbeat/progress
    di jalur lain) tidak tertimpa nilai basi pada objek Python.
    """
    if job.state in TERMINAL_STATES:
        raise ValueError("Job terminal tidak dapat berubah")
    if new_state not in VALID_TRANSITIONS.get(job.state, frozenset()):
        raise ValueError(f"Transisi tidak sah: {job.state} → {new_state}")
    updates = {"state": new_state, **fields, "updated_at": dj_timezone.now()}
    Job.objects.filter(id=job.id).update(**updates)
    job.refresh_from_db()


def run_claimed(job: Job, *, now=None) -> Job:
    """Jalankan satu job ter-claim: preflight → execute → verify.

    Worker memegang lease; semua query isi tenant berjalan dalam tenant_scope.
    Handler mengembalikan JobError untuk klasifikasi galat; hasil diverifikasi
    sebelum succeeded (jawaban 'sukses kirim' ≠ 'perubahan berhasil').
    """
    handler = handler_for(job.kind)
    now = now or timezone.now()

    with tenant_scope(job.tenant_id):
        detail = getattr(job, "detail", None) or JobDetail.objects.get(job_id=job.id)
        ctx = JobContext(job=job, payload=detail.payload)

        # --- preflight ---
        transition_claimed(job, JobState.PREFLIGHT, phase_label_code="preflight")
        try:
            if handler is not None:
                handler.preflight(ctx)
        except JobError as exc:
            return _finish_preflight_failure(job, exc)

        # --- execute ---
        transition_claimed(job, JobState.EXECUTING, phase_label_code="executing")
        result: dict = {}
        try:
            if handler is not None:
                ctx.heartbeat()
                result = handler.execute(ctx) or {}
                job.effect_state = EffectState.MAYBE
                _fenced_save(job, effect_state=EffectState.MAYBE)
        except JobError as exc:
            return _finish_execute_failure(job, exc)
        except Exception:
            logger.exception("job %s gagal tak terduga", job.id)
            return _finish_execute_failure(job, JobError(code="internal_error", retryable=True))

        # --- verify: readback sebelum menyatakan berhasil ---
        transition_claimed(job, JobState.VERIFYING, phase_label_code="verifying")
        try:
            if handler is not None:
                ctx.heartbeat()
                result = handler.verify(ctx) or result
        except JobError as exc:
            if exc.uncertain:
                return _mark(job, JobState.UNCERTAIN, error_code=exc.code, retryable=exc.retryable)
            if exc.recovery_required:
                return _mark(job, JobState.RECOVERY_REQUIRED, error_code=exc.code, retryable=False)
            return _retry_or_fail(job, exc)
        except Exception:
            logger.exception("job %s verify gagal tak terduga", job.id)
            return _mark(job, JobState.UNCERTAIN, error_code="verification_error", retryable=True)

        detail.result = result
        detail.save(update_fields=["result"])
        return _mark(
            job,
            JobState.SUCCEEDED,
            effect_state=EffectState.CONFIRMED,
            phase_label_code=None,
            retryable=False,
        )


def _mark(job: Job, state: str, **fields) -> Job:
    updates = {"state": state, **fields, "updated_at": dj_timezone.now()}
    if state == JobState.SUCCEEDED and job.items_total is not None:
        # Selesaikan item bila handler tidak melapor; jangan menimpa nilai nyata.
        current = Job.objects.filter(id=job.id).values_list("items_done", flat=True).first()
        if current is None:
            updates["items_done"] = job.items_total
    Job.objects.filter(id=job.id).update(**updates)
    job.refresh_from_db()
    return job


def _finish_preflight_failure(job: Job, exc: JobError) -> Job:
    if exc.recovery_required:
        return _mark(job, JobState.RECOVERY_REQUIRED, error_code=exc.code, retryable=False)
    return _retry_or_fail(job, exc)


def _finish_execute_failure(job: Job, exc: JobError) -> Job:
    if exc.uncertain:
        # Perintah mungkin sudah terkirim/terjalankan: status uncertain, bukan failed.
        return _mark(job, JobState.UNCERTAIN, error_code=exc.code, retryable=exc.retryable)
    if exc.recovery_required:
        return _mark(job, JobState.RECOVERY_REQUIRED, error_code=exc.code, retryable=False)
    return _retry_or_fail(job, exc)


def _retry_or_fail(job: Job, exc: JobError) -> Job:
    if exc.retryable and job.attempt < job.max_attempts:
        backoff = min(BACKOFF_CAP_S, 2 ** job.attempt * 5)
        Job.objects.filter(id=job.id).update(
            state=JobState.RETRY_WAIT,
            available_at=dj_timezone.now() + dj_timezone.timedelta(seconds=backoff),
            error_code=exc.code,
            retryable=True,
            lease_token=None,
            lease_expires_at=None,
            updated_at=dj_timezone.now(),
        )
        job.refresh_from_db()
        handler = handler_for(job.kind)
        if handler is not None:
            handler.on_retry(_ctx_for(job))
        return job
    return _mark(job, JobState.FAILED, error_code=exc.code, retryable=exc.retryable)


def _ctx_for(job: Job) -> JobContext:
    detail = getattr(job, "detail", None)
    return JobContext(job=job, payload=detail.payload if detail else {})


# ---------------------------------------------------------------------------
# Rekonsiliasi lease & pemulihan


def reconcile_expired_leases() -> int:
    """Lease habis pada executing/verifying → uncertain (writer lama difence)."""
    now = timezone.now()
    jobs = Job.objects.filter(
        state__in=[JobState.EXECUTING, JobState.VERIFYING],
        lease_expires_at__lt=now,
    )
    count = 0
    for job in jobs:
        Job.objects.filter(id=job.id).update(
            state=JobState.UNCERTAIN,
            error_code="lease_expired",
            retryable=True,
            lease_token=None,
        )
        count += 1
    return count


def resolve_uncertain(job: Job, *, applied: bool | None, error_code: str | None = None) -> Job:
    """Hasil readback uncertain: terbukti belum diterapkan → retry; else verify/recovery."""
    if job.state != JobState.UNCERTAIN:
        raise ValueError("Bukan uncertain")
    if applied is False:
        return _retry_or_fail(job, JobError(code=error_code or "readback_not_applied", retryable=True))
    job.state = JobState.VERIFYING
    job.save()
    return job


def cancel_job(job: Job, reason: str) -> Job:
    """Batal hanya bila nol efek terbukti (§6); selain itu 409."""
    if job.state in CANCEL_OK_STATES and job.effect_state == EffectState.NONE:
        job.state = JobState.CANCELLED
        job.cancelled_reason = reason
        job.lease_token = None
        job.save()
        return job
    if job.state in (JobState.EXECUTING, JobState.VERIFYING) and job.effect_state == EffectState.NONE:
        job.state = JobState.CANCELLED
        job.cancelled_reason = reason
        job.save()
        return job
    raise ValueError("not_cancellable")


def retry_job(job: Job, actor=None) -> Job:
    """Job terminal retryable → job baru menautkan asal (key idempotensi semula)."""
    if job.state not in (JobState.FAILED, JobState.CANCELLED, JobState.UNCERTAIN):
        raise ValueError("not_retryable")
    detail = getattr(job, "detail", None)
    return create_job(
        tenant_id=job.tenant_id,
        kind=job.kind,
        actor=actor or job.actor,
        actor_display=job.actor_display,
        router=job.router,
        payload=detail.payload if detail else {},
        request_id=job.request_id,
        deadline_s=None,
        priority=job.priority,
        origin_job=job,
    )


# ---------------------------------------------------------------------------
# Outbox


def dispatch_outbox(max_events: int = 100) -> int:
    """Kirim event outbox yang belum terkirim (polling, bukan on_commit blocking)."""
    events = OutboxEvent.objects.filter(dispatched_at=None).order_by("created_at")[:max_events]
    count = 0
    for event in events:
        # Endpoint distribusi nyata (webhook/monitor) datang bersama fiturnya;
        # M1: tandai terkirim agar outbox tidak menumpuk.
        event.dispatched_at = timezone.now()
        event.attempts += 1
        event.save(update_fields=["dispatched_at", "attempts"])
        count += 1
    return count
