"""Disposable functional regression for expired lease handling, with no router or I/O."""
from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.tenancy.models import Tenant


@pytest.mark.django_db(
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
)
@pytest.mark.parametrize("max_attempts", [1, 2], ids=["final", "nonfinal"])
def test_expired_attempt_leaves_settlement_to_reconcile(monkeypatch, max_attempts):
    tenant = Tenant.objects.create(display_name="Test lease", namespace=f"test-lease-{uuid4().hex[:10]}")
    observed = []

    class LocalNoEffect(engine.JobHandler):
        kind = "_test_expired_no_effect"

        def execute(self, ctx):
            expired_at = timezone.now() - timedelta(seconds=1)
            updated = Job.objects.filter(id=ctx.job.id).update(lease_expires_at=expired_at)
            assert updated == 1
            observed.append("no external effect")
            raise engine.JobError(code="controlled_no_effect", retryable=True, no_effect=True)

        def verify(self, ctx):
            pytest.fail("No-effect job advanced to verifier")

    monkeypatch.setitem(engine._REGISTRY, LocalNoEffect.kind, LocalNoEffect())
    job = engine.create_job(tenant_id=tenant.id, kind=LocalNoEffect.kind)
    Job.objects.filter(id=job.id).update(max_attempts=max_attempts)
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id and claimed.attempt == 1

    returned = engine.run_claimed(claimed)
    fresh = Job.objects.get(id=job.id)
    print(f"max_attempts={max_attempts} actual={fresh.state} returned={returned.state} "
          f"error={fresh.error_code} same_epoch={fresh.lease_epoch == claimed.lease_epoch}")
    assert observed == ["no external effect"]
    assert (fresh.state, fresh.lease_token, fresh.lease_epoch, fresh.error_code) == (
        JobState.EXECUTING, claimed.lease_token, claimed.lease_epoch, None,
    ), "An expired lease must not settle the job before reconciliation"
