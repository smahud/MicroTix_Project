"""Controller probes for PR27 exact bd37c14. Safety assertions should fail
on the submitted candidate where the independently reviewed defect exists.

Run from backend with the real PostgreSQL test URL supplied by controller.
No production device access; adapters below are controlled fault injection.
"""
from __future__ import annotations

import json
import threading

import pytest
from django.conf import settings
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.models import EffectState, Job, JobState
from domains.network.models import (
    DiscoveryObject,
    DiscoverySnapshot,
    Router,
    RouterHealthSample,
)
from domains.tenancy.models import Membership, Role, Tenant

pytest_plugins = ["tests.conftest"]
pytestmark = pytest.mark.django_db(
    transaction=True,
    # Match the existing integration harness: an explicit application set
    # enables CASCADE during transactional flush, including unmanaged
    # FreeRADIUS foreign keys. This is test cleanup, not altered assertions.
    available_apps=list(settings.INSTALLED_APPS),
)


def _actor_router(tag):
    owner = User.objects.create_user(
        email=f"review-{tag}@test.local",
        full_name=f"Controller {tag}",
        password="test-password-1234567890",
        is_active=True,
    )
    tenant = Tenant.objects.create(
        display_name=f"Controller {tag}", namespace=f"rtrw-review-{tag}"
    )
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant_id=tenant.id,
            display_name=f"Controller {tag}",
            router_code=f"REV-{tag}"[:16],
            tunnel_ip="100.127.120.1",
            mode=Router.Mode.MANAGED,
            credential_ref="enc:review-controlled",
        )
    return tenant, owner, router


def _emit(case, **observed):
    print(json.dumps({"case": case, **observed}, sort_keys=True, default=str), flush=True)


def test_backup_manifest_failure_after_send_must_hold_unknown(monkeypatch):
    """A04: actual BackupRunHandler sends, then local staging disk fails.

    Durable engine outcome must hold the possible remote effect; it must
    not automatically resend the same logical backup.
    """
    from domains.backups import service
    from domains.backups.models import BackupArtifact

    tenant, owner, router = _actor_router("generic")
    sends = []

    class Adapter:
        def create_backup(self, ctx, *, category):
            sends.append((ctx.router_id, category))
            return {"size_bytes": 256, "hash": "a" * 64, "simulated": True}

    def fail_staging(*args, **kwargs):
        raise OSError("controlled ENOSPC after successful create_backup")

    monkeypatch.setattr(service, "select_adapter", lambda: Adapter())
    monkeypatch.setattr(service, "_write_manifest", fail_staging)
    job = engine.create_job(
        tenant_id=tenant.id, kind="backup_router", actor=owner, router=router,
        payload={"category": "manual"},
    )
    first = engine.run_claimed(engine.claim_next())
    first_state = first.state
    first_effect = first.effect_state
    Job.objects.filter(id=job.id).update(
        available_at=timezone.now() - timezone.timedelta(seconds=1)
    )
    second = engine.claim_next()
    if second is not None:
        engine.run_claimed(second)
    with tenant_scope(tenant.id):
        artifacts = BackupArtifact.objects.filter(router_id=router.id).count()
    _emit(
        "backup-generic-after-send", first_state=first_state,
        effect_state=first_effect, send_count=len(sends), artifact_count=artifacts,
        reclaimed=second is not None,
    )
    assert first_state in {JobState.UNCERTAIN, JobState.RECOVERY_REQUIRED}, (
        "successful adapter effect followed by staging failure must not become retry_wait"
    )
    assert len(sends) == 1, "unknown first effect must not be blindly sent twice"


def test_actual_discovery_cannot_commit_after_reconcile(monkeypatch):
    """A01/A02: block actual discovery I/O, revoke its lease, then release.

    Existing snapshot creation before lease loss is allowed. New discovery
    objects, success status, migration updates and health samples afterwards
    must be fenced by current ownership within their DB transaction.
    """
    from adapters.routeros import factory

    tenant, owner, router = _actor_router("stale")
    entered = threading.Event()
    release = threading.Event()
    outcomes = {}

    class Adapter:
        def list_accounts(self, ctx):
            entered.set()
            if not release.wait(20):
                raise RuntimeError("controller failed to release blocked discovery")
            return [{"username": "post-lease-account", "service": "pppoe"}]

        def read_health(self, ctx):
            return {"vpn_up": True, "api_up": True, "uptime_s": 5}

    monkeypatch.setattr(factory, "active_routeros_adapter", lambda: Adapter())
    monkeypatch.setattr(factory, "active_adapter_name", lambda: "simulator")
    job = engine.create_job(
        tenant_id=tenant.id, kind="discover_router", actor=owner, router=router
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id

    def run():
        from django.db import connections

        try:
            outcomes["worker"] = {"state": engine.run_claimed(claimed).state}
        except BaseException as exc:
            outcomes["worker"] = {"exception": f"{type(exc).__name__}: {exc}"}
        finally:
            connections.close_all()

    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert entered.wait(15), "worker must reach adapter gate"
        Job.objects.filter(id=job.id).update(
            lease_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert engine.reconcile_expired_leases() == 1
        assert Job.objects.get(id=job.id).state == JobState.UNCERTAIN
        with tenant_scope(tenant.id):
            assert DiscoveryObject.objects.filter(router_id=router.id).count() == 0
    finally:
        release.set()
        worker.join(25)
    assert not worker.is_alive(), "worker must stop within bounded join"
    assert set(outcomes) == {"worker"}, outcomes
    assert "exception" not in outcomes["worker"], outcomes
    with tenant_scope(tenant.id):
        objects = DiscoveryObject.objects.filter(router_id=router.id).count()
        status = list(
            DiscoverySnapshot.objects.filter(router_id=router.id).values_list("status", flat=True)
        )
        health = RouterHealthSample.objects.filter(router_id=router.id).count()
    _emit(
        "stale-discovery-domain-commit", outcomes=outcomes,
        job_state=Job.objects.get(id=job.id).state, object_count=objects,
        snapshot_status=status, health_count=health,
    )
    assert objects == 0, "stale discovery writer committed new domain objects after reconcile"
    assert health == 0, "stale discovery writer committed new health sample after reconcile"
    assert "succeeded" not in status, "stale discovery marked its snapshot successful"


def test_retry_origin_cannot_bypass_uncertain_grandchild(monkeypatch):
    """A04: retry safety applies to the entire logical retry lineage."""
    tenant, owner, router = _actor_router("lineage")
    sends = []

    class Handler(engine.JobHandler):
        kind = "_test_review_lineage"

        def execute(self, ctx):
            sends.append(str(ctx.job.id))
            raise engine.JobError(code="timeout_after_send", uncertain=True)

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    origin = engine.create_job(
        tenant_id=tenant.id, kind=Handler.kind, actor=owner, router=router
    )
    Job.objects.filter(id=origin.id).update(state=JobState.FAILED, retryable=True)
    child = engine.retry_job(Job.objects.get(id=origin.id), actor=owner)
    Job.objects.filter(id=child.id).update(state=JobState.FAILED, retryable=True)
    grandchild = engine.retry_job(Job.objects.get(id=child.id), actor=owner)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == grandchild.id
    unknown = engine.run_claimed(claimed)
    assert unknown.state == JobState.UNCERTAIN and len(sends) == 1
    extra = None
    error = None
    try:
        extra = engine.retry_job(Job.objects.get(id=origin.id), actor=owner)
    except ValueError as exc:
        error = str(exc)
    if extra is not None:
        next_claim = engine.claim_next()
        assert next_claim is not None and next_claim.id == extra.id
        engine.run_claimed(next_claim)
    _emit(
        "retry-uncertain-grandchild", grandchild_state=Job.objects.get(id=grandchild.id).state,
        extra_retry_created=extra is not None, error=error, send_count=len(sends),
    )
    assert extra is None, "origin retry bypassed the unknown grandchild outcome"
    assert len(sends) == 1, "retry lineage sent a second effect while first outcome remained unknown"


def test_new_router_writer_waits_for_unknown_predecessor_readback(monkeypatch):
    """A03: a released session lock is not completed outcome readback."""
    tenant, owner, router = _actor_router("readback")
    sends = []

    class Handler(engine.JobHandler):
        kind = "_test_review_router_unknown"

        def execute(self, ctx):
            sends.append(str(ctx.job.id))
            if len(sends) == 1:
                raise engine.JobError(code="timeout_after_send", uncertain=True)
            return {"sent": True}

        def verify(self, ctx):
            return {"ok": True}

    monkeypatch.setitem(engine._REGISTRY, Handler.kind, Handler())
    first = engine.create_job(
        tenant_id=tenant.id, kind=Handler.kind, actor=owner, router=router
    )
    first = engine.run_claimed(engine.claim_next())
    assert first.state == JobState.UNCERTAIN and len(sends) == 1
    second = engine.create_job(
        tenant_id=tenant.id, kind=Handler.kind, actor=owner, router=router
    )
    after = engine.run_claimed(engine.claim_next())
    _emit(
        "router-unknown-predecessor", first_state=Job.objects.get(id=first.id).state,
        second_state=after.state, send_count=len(sends), second_job=second.id,
    )
    assert len(sends) == 1, "new conflicting router writer sent before predecessor readback"
