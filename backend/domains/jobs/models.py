"""Model pekerjaan — envelope terpisah dari isi tenant (ARCHITECTURE.md §4/§6).

jobs_job (envelope): terlihat worker tanpa RLS; hanya berisi kolom operasional
(kind/state/lease/deadline/kode galat) — bukan payload bisnis.
jobs_jobdetail (isi tenant): payload + hasil; dilindungi RLS tenant.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone as dj_timezone

JOB_KINDS = (
    "discover_router",
    "harvest_passwords",
    "commit_migration",
    "radius_cutover_step",
    "disconnect_session",
    "apply_account_attributes",
    "suspend_service",
    "activate_service",
    "backup_router",
    "acs_task",
    "issue_vouchers",
    "recognize_revenue",
    "lifecycle_saas",
    "radius_janitor",
    "enrollment_reconcile",
    "nas_client_reload",
    "import_commit",
    "router_release",
    "router_replace",
    "change_plan",
)


class JobKind(models.TextChoices):
    DISCOVER_ROUTER = "discover_router"
    HARVEST_PASSWORDS = "harvest_passwords"
    COMMIT_MIGRATION = "commit_migration"
    RADIUS_CUTOVER_STEP = "radius_cutover_step"
    DISCONNECT_SESSION = "disconnect_session"
    APPLY_ACCOUNT_ATTRIBUTES = "apply_account_attributes"
    SUSPEND_SERVICE = "suspend_service"
    ACTIVATE_SERVICE = "activate_service"
    BACKUP_ROUTER = "backup_router"
    ACS_TASK = "acs_task"
    ISSUE_VOUCHERS = "issue_vouchers"
    RECOGNIZE_REVENUE = "recognize_revenue"
    LIFECYCLE_SAAS = "lifecycle_saas"
    RADIUS_JANITOR = "radius_janitor"
    ENROLLMENT_RECONCILE = "enrollment_reconcile"
    NAS_CLIENT_RELOAD = "nas_client_reload"
    IMPORT_COMMIT = "import_commit"
    ROUTER_RELEASE = "router_release"
    ROUTER_REPLACE = "router_replace"
    CHANGE_PLAN = "change_plan"


class JobState(models.TextChoices):
    QUEUED = "queued"
    CLAIMED = "claimed"
    PREFLIGHT = "preflight"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    WAITING_DEPENDENCY = "waiting_dependency"
    RETRY_WAIT = "retry_wait"
    UNCERTAIN = "uncertain"
    RECOVERY_REQUIRED = "recovery_required"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EffectState(models.TextChoices):
    NONE = "none"
    MAYBE = "maybe"
    CONFIRMED = "confirmed"


# Transisi sah — ARCHITECTURE.md §6 (tabel state).
VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    JobState.QUEUED: frozenset({JobState.CLAIMED, JobState.CANCELLED}),
    JobState.CLAIMED: frozenset({JobState.PREFLIGHT, JobState.RETRY_WAIT, JobState.FAILED, JobState.CANCELLED}),
    JobState.PREFLIGHT: frozenset(
        {JobState.EXECUTING, JobState.WAITING_DEPENDENCY, JobState.RETRY_WAIT, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.EXECUTING: frozenset(
        {JobState.VERIFYING, JobState.UNCERTAIN, JobState.FAILED, JobState.RECOVERY_REQUIRED, JobState.CANCELLED}
    ),
    JobState.VERIFYING: frozenset(
        {JobState.SUCCEEDED, JobState.UNCERTAIN, JobState.FAILED, JobState.RECOVERY_REQUIRED}
    ),
    JobState.WAITING_DEPENDENCY: frozenset({JobState.QUEUED, JobState.CANCELLED, JobState.FAILED}),
    JobState.RETRY_WAIT: frozenset({JobState.QUEUED, JobState.CANCELLED, JobState.FAILED}),
    JobState.UNCERTAIN: frozenset(
        {JobState.VERIFYING, JobState.RETRY_WAIT, JobState.RECOVERY_REQUIRED, JobState.FAILED}
    ),
    JobState.RECOVERY_REQUIRED: frozenset({JobState.VERIFYING, JobState.FAILED}),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}

TERMINAL_STATES = frozenset({JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED})
CANCEL_OK_STATES = frozenset(
    {JobState.QUEUED, JobState.CLAIMED, JobState.PREFLIGHT, JobState.WAITING_DEPENDENCY, JobState.RETRY_WAIT}
)


class Job(models.Model):
    """Envelope pekerjaan — tanpa payload bisnis (lihat JobDetail)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="jobs", db_column="tenant_id")
    kind = models.CharField(max_length=32, choices=JobKind.choices)
    state = models.CharField(max_length=20, choices=JobState.choices, default=JobState.QUEUED, db_index=True)
    effect_state = models.CharField(max_length=10, choices=EffectState.choices, default=EffectState.NONE)

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, db_column="actor_id", related_name="jobs")
    actor_display = models.CharField(max_length=120, blank=True, default="")
    router = models.ForeignKey("network.Router", null=True, blank=True, on_delete=models.SET_NULL, db_column="router_id", related_name="jobs")

    phase_label_code = models.CharField(max_length=48, null=True, blank=True)
    items_total = models.IntegerField(null=True, blank=True)
    items_done = models.IntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=48, null=True, blank=True)
    request_id = models.CharField(max_length=32, null=True, blank=True)
    retryable = models.BooleanField(default=False)

    attempt = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    priority = models.IntegerField(default=100)  # kecil = lebih dulu (ORDER BY priority, id)

    # Fencing: worker lama dicegah menulis setelah lease berpindah.
    lease_token = models.UUIDField(null=True, blank=True)
    lease_epoch = models.IntegerField(default=0)
    lease_expires_at = models.DateTimeField(null=True, blank=True)

    available_at = models.DateTimeField(default=dj_timezone.now)
    deadline_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    origin_job = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, db_column="origin_job_id", related_name="retries")
    cancelled_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "jobs_job"
        indexes = [
            models.Index(fields=["state", "available_at", "priority", "id"], name="ix_job_state_avail_prio"),
            models.Index(fields=["tenant", "created_at", "id"], name="ix_job_tenant_created"),
        ]

    def transition(self, new_state: str, *, save: bool = True, **fields) -> None:
        if new_state not in VALID_TRANSITIONS.get(self.state, frozenset()):
            raise ValueError(f"Transisi tidak sah: {self.state} → {new_state}")
        self.state = new_state
        for name, value in fields.items():
            setattr(self, name, value)
        if save:
            self.save()


class JobDetail(models.Model):
    """Isi pekerjaan tenant — payload & hasil; RLS tenant (migration)."""

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="detail", db_column="job_id")
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id")
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict)

    class Meta:
        db_table = "jobs_jobdetail"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "job"], name="uq_jobdetail_tenant_job"),
        ]


class OutboxEvent(models.Model):
    """Outbox transaksional — event domain dikirim setelah commit (polling)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", null=True, on_delete=models.SET_NULL, db_column="tenant_id")
    event_type = models.CharField(max_length=64)
    aggregate_type = models.CharField(max_length=48)
    aggregate_id = models.UUIDField()
    dedup_key = models.CharField(max_length=128, unique=True)
    payload = models.JSONField(default=dict)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=dj_timezone.now)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jobs_outbox_event"
        indexes = [models.Index(fields=["dispatched_at", "created_at"], name="ix_outbox_pending")]


class IdempotencyKey(models.Model):
    """Idempotency-Key — scope principal+tenant+operation+resource+key (§5).

    Retensi 7 hari; body dibandingkan HMAC; respons disimpan untuk replay.
    """

    id = models.BigAutoField(primary_key=True)
    principal = models.CharField(max_length=64)  # user id / 'anonymous'
    scope = models.CharField(max_length=256)
    idem_key = models.CharField(max_length=128)
    body_hash = models.CharField(max_length=64)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "jobs_idempotency_key"
        constraints = [
            models.UniqueConstraint(fields=["scope", "idem_key"], name="uq_idem_scope_key"),
        ]
        indexes = [models.Index(fields=["created_at"], name="ix_idem_created")]
