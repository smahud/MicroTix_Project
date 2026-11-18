"""R3 authority probes, exact app source4b03efe read-only.

Real PostgreSQL row-lock wait, production handler/service, controlled TLS I/O.
No device/network I/O. Required safety assertions intentionally expose defects.
"""
from __future__ import annotations

import json
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
from domains.jobs.models import Job, JobState
from domains.network import handlers as network_handlers
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer
from domains.tenancy.models import Membership, Role, Tenant

pytest_plugins = ["tests.conftest"]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(transaction=True, available_apps=[
        "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
        "domains.tenancy", "domains.identity", "domains.network", "domains.customers",
        "domains.jobs", "domains.audit", "domains.radius", "domains.backups",
        "domains.subscriptions",
    ]),
]


def _identity(label):
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r3-{label}-{suffix}@test.local", full_name="Controller R3",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R3 {label}", namespace=f"rtrw-r3-{suffix}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    return tenant, actor


@pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
def test_enrollment_lock_wait_does_not_outlive_current_authority(monkeypatch, protocol):
    """Authority read before enrollment lock wait must not authorize later effects.

    1. Real job enters controlled TLS read outside DB transaction.
    2. Controller locks enrollment row; job's REAL authority check succeeds.
    3. PostgreSQL confirms job blocked on controller's enrollment row lock.
    4. Separate controller connection commits revocation while lock remains held.
    5. Locker releases enrollment lock after revocation is durably visible.
    6. Required: worker must revalidate before Router/credential activation.
    """
    tenant, actor = _identity(protocol)
    suffix = uuid.uuid4().hex[:10]
    ip = f"100.124.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}"
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="R3 enrollment", router_code=f"R3-{suffix}",
            protocol=protocol, tunnel_ip=ip, token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        if protocol == "sstp":
            credential = SstpAccount.objects.create(
                tenant=tenant, enrollment=enrollment, tunnel_ip=ip,
                username=f"r3-{suffix}", password_ref="synthetic-not-decrypted",
                state=SstpAccount.State.PENDING,
            )
        else:
            credential = WireGuardPeer.objects.create(
                tenant=tenant, enrollment=enrollment, allowed_ip=ip,
                public_key=f"r3-probe-{suffix}", state=WireGuardPeer.State.PENDING,
            )
    job = engine.create_job(
        tenant_id=tenant.id, kind="verify_api_ssl", actor=actor,
        payload={"enrollment_id": str(enrollment.id)},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    probe_active, finish_probe, authority_passed = (
        threading.Event(), threading.Event(), threading.Event()
    )
    outcomes, errors, pids = {}, [], {}

    class ControlledConnectivityAdapter:
        def probe_connectivity(self, router_context):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["worker"] = cursor.fetchone()[0]
            assert not connection.in_atomic_block
            probe_active.set()
            assert finish_probe.wait(15), "controller failed to release TLS probe"
            return {"ok": True, "cert_sha256": "a" * 64}

    real_authority = network_handlers.check_current_authority

    def record_authority(*args, **kwargs):
        real_authority(*args, **kwargs)
        authority_passed.set()  # observation only; no pause or behavior substitution

    monkeypatch.setattr(network_handlers, "check_current_authority", record_authority)
    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter", lambda: ControlledConnectivityAdapter()
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

    locked, release_lock = threading.Event(), threading.Event()
    lock_outcomes = {}

    def locker():
        close_old_connections()
        try:
            with tenant_scope(tenant.id), transaction.atomic():
                RouterEnrollment.objects.select_for_update().get(id=enrollment.id)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids["locker"] = cursor.fetchone()[0]
                locked.set()
                assert release_lock.wait(20), "controller failed to release enrollment lock"
            lock_outcomes["committed"] = True
        except BaseException as exc:
            lock_outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    blocked = False
    lock_thread = threading.Thread(target=locker, name="r3-enrollment-locker")
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        thread = threading.Thread(target=worker, name="r3-enrollment-lock-authority")
        thread.start()
        try:
            assert probe_active.wait(15), "handler never reached TLS probe"
            lock_thread.start()
            assert locked.wait(15), "locker never acquired enrollment row"
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["controller"] = cursor.fetchone()[0]
            assert len(set(pids.values())) == 3, "three independent DB connections required"
            finish_probe.set()
            assert authority_passed.wait(15), "post-I/O authority callback did not pass"
            deadline = time.monotonic() + 10
            poll = threading.Event()
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [
                        pids["locker"], pids["worker"],
                    ])
                    blocked = bool(cursor.fetchone()[0])
                if blocked:
                    break
                poll.wait(0.01)
            assert blocked, "PostgreSQL must observe actual enrollment lock contention"
            assert Membership.objects.filter(user=actor, tenant=tenant).update(
                revoked_at=timezone.now()
            ) == 1
            assert Membership.objects.get(user=actor, tenant=tenant).revoked_at is not None
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [
                    pids["locker"], pids["worker"],
                ])
                assert cursor.fetchone()[0], "worker escaped lock before revocation commit"
        finally:
            finish_probe.set()
            release_lock.set()
            if lock_thread.ident is not None:
                lock_thread.join(20)
            thread.join(20)
    assert not lock_thread.is_alive(), "locker must finish within bound"
    assert lock_outcomes == {"committed": True}, lock_outcomes
    assert not thread.is_alive(), "worker did not finish within bound"
    assert not errors, errors
    assert "state" in outcomes, "missing worker outcome"
    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        routers = Router.objects.filter(tenant=tenant).count()
    observed = {
        "probe": "enrollment-lock-wait-authority", "protocol": protocol,
        **outcomes, "routers_created": routers, "enrollment": enrollment.status,
        "credential": credential.state, "separate_connections": True,
        "postgres_observed_lock_wait": blocked,
        "membership_revoked": Membership.objects.get(user=actor, tenant=tenant).revoked_at is not None,
    }
    print(json.dumps(observed, sort_keys=True))
    assert routers == 0 and credential.state == "pending", observed
    assert outcomes["state"] != JobState.SUCCEEDED, observed


def test_concurrent_enrollment_finalize_has_typed_non_uncertain_rejection(monkeypatch):
    """Two already-started jobs finalize same enrollment; duplicate is explicit.

    Both jobs legitimately reach VERIFYING/TLS before first completes; this
    executes the new guarded duplicate-finalize branch without fabricating
    completed state. No extra Router is permitted and an expected duplicate
    must not fall through NameError -> internal_error -> uncertain.
    """
    tenant, actor = _identity("duplicate")
    suffix = uuid.uuid4().hex[:10]
    ip = f"100.123.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}"
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="R3 duplicate", router_code=f"R3-{suffix}",
            protocol="wireguard", tunnel_ip=ip, token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        WireGuardPeer.objects.create(
            tenant=tenant, enrollment=enrollment, allowed_ip=ip,
            public_key=f"r3-dupe-{suffix}", state=WireGuardPeer.State.PENDING,
        )
    jobs = [engine.create_job(
        tenant_id=tenant.id, kind="verify_api_ssl", actor=actor,
        payload={"enrollment_id": str(enrollment.id)},
    ) for _ in range(2)]
    claims = [engine.claim_next(), engine.claim_next()]
    assert {claim.id for claim in claims if claim is not None} == {job.id for job in jobs}
    entered = [threading.Event(), threading.Event()]
    release = [threading.Event(), threading.Event()]
    outcomes, errors = {}, {}

    class ControlledConnectivityAdapter:
        def probe_connectivity(self, router_context):
            idx = int(threading.current_thread().name[-1])
            assert not connection.in_atomic_block
            entered[idx].set()
            assert release[idx].wait(20), "TLS probe not released"
            return {"ok": True, "cert_sha256": "a" * 64}

    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter", lambda: ControlledConnectivityAdapter()
    )

    def worker(idx):
        close_old_connections()
        try:
            final = engine.run_claimed(Job.objects.get(id=claims[idx].id))
            outcomes[idx] = {"state": final.state, "error": final.error_code}
        except BaseException as exc:
            errors[idx] = repr(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(idx,), name=f"r3-dupe-{idx}") for idx in range(2)]
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        try:
            threads[0].start()
            assert entered[0].wait(15), "first did not reach TLS"
            threads[1].start()
            assert entered[1].wait(15), "second did not reach TLS"
            release[0].set()
            threads[0].join(20)
            assert not threads[0].is_alive()
            assert outcomes.get(0, {}).get("state") == JobState.SUCCEEDED, outcomes
            release[1].set()
        finally:
            for event in release:
                event.set()
            for thread in threads:
                if thread.ident is not None:
                    thread.join(20)
    assert not any(thread.is_alive() for thread in threads), "bounded participants"
    assert not errors and len(outcomes) == 2, {"outcomes": outcomes, "errors": errors}
    with tenant_scope(tenant.id):
        routers = Router.objects.filter(tenant=tenant).count()
    observed = {"probe": "duplicate-finalize", "outcomes": outcomes, "routers_created": routers}
    print(json.dumps(observed, sort_keys=True))
    assert routers == 1, observed
    assert outcomes[1]["error"] != "internal_error", observed
    assert outcomes[1]["state"] != JobState.UNCERTAIN, observed
