"""R4 authority: a credential UPDATE wait follows the new enrollment guard.

Read-only review of a636166/16db545 app source; real handler/service/PG locks,
synthetic identities and a controlled read-only TLS adapter; no device I/O.
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


@pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
def test_credential_lock_wait_does_not_outlive_authority(monkeypatch, protocol):
    """A committed revoke during a real credential-row wait prevents activation.

    The worker has already acquired enrollment and passed the newly added
    fresh check. A second connection holds the *credential* row, so its UPDATE
    is blocked. The controller verifies the exact PG query/blocker, commits
    membership revocation, verifies the worker still blocked, then releases
    the row. No product guard is patched or replaced.
    """
    suffix = uuid.uuid4().hex[:10]
    actor = User.objects.create_user(
        email=f"r4cred-{suffix}@test.local", full_name="Controller R4 credential",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name="R4 credential", namespace=f"rtrw-r4-{suffix}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    ip = f"100.122.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}"
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="R4 enrollment", router_code=f"R4-{suffix}",
            protocol=protocol, tunnel_ip=ip, token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        if protocol == "sstp":
            credential = SstpAccount.objects.create(
                tenant=tenant, enrollment=enrollment, tunnel_ip=ip,
                username=f"r4-{suffix}", password_ref="synthetic-not-decrypted",
                state=SstpAccount.State.PENDING,
            )
        else:
            credential = WireGuardPeer.objects.create(
                tenant=tenant, enrollment=enrollment, allowed_ip=ip,
                public_key=f"r4-probe-{suffix}", state=WireGuardPeer.State.PENDING,
            )
    credential_model = type(credential)
    table = credential_model._meta.db_table
    job = engine.create_job(
        tenant_id=tenant.id, kind="verify_api_ssl", actor=actor,
        payload={"enrollment_id": str(enrollment.id)},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    probe_active, finish_probe = threading.Event(), threading.Event()
    locked, release_lock = threading.Event(), threading.Event()
    outcomes, errors, lock_outcomes, pids = {}, [], {}, {}

    class ConnectivityAdapter:
        def probe_connectivity(self, router_context):
            assert not connection.in_atomic_block
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["worker"] = cursor.fetchone()[0]
            probe_active.set()
            assert finish_probe.wait(15), "TLS observation not released"
            return {"ok": True, "cert_sha256": "a" * 64}

    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter", lambda: ConnectivityAdapter()
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
                assert release_lock.wait(20), "credential lock not released"
            lock_outcomes["committed"] = True
        except BaseException as exc:
            lock_outcomes["exception"] = repr(exc)
        finally:
            connections.close_all()

    worker_thread = threading.Thread(target=worker, name=f"r4-credential-{protocol}")
    lock_thread = threading.Thread(target=locker, name=f"r4-credential-lock-{protocol}")
    observed_query, blocked = "", False
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        worker_thread.start()
        try:
            assert probe_active.wait(15), "handler never reached TLS"
            lock_thread.start()
            assert locked.wait(15), "credential row never locked"
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["controller"] = cursor.fetchone()[0]
            assert len(set(pids.values())) == 3
            finish_probe.set()
            deadline = time.monotonic() + 10
            poll = threading.Event()
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
                poll.wait(0.01)
            assert blocked, "PG must observe actual credential row contention"
            assert table in observed_query and observed_query.lstrip().upper().startswith("UPDATE"), observed_query
            # Revocation is committed on a separate connection while the real
            # sensitive UPDATE remains blocked after all entry authority reads.
            assert Membership.objects.filter(user=actor, tenant=tenant).update(
                revoked_at=timezone.now()
            ) == 1
            assert Membership.objects.get(user=actor, tenant=tenant).revoked_at is not None
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [
                    pids["locker"], pids["worker"],
                ])
                assert cursor.fetchone()[0], "worker escaped before committed revoke"
        finally:
            finish_probe.set()
            release_lock.set()
            if lock_thread.ident is not None:
                lock_thread.join(20)
            worker_thread.join(20)
    assert not lock_thread.is_alive() and not worker_thread.is_alive(), "bounded participants"
    assert lock_outcomes == {"committed": True}, lock_outcomes
    assert not errors and "state" in outcomes, {"errors": errors, "outcomes": outcomes}
    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        routers = Router.objects.filter(tenant=tenant).count()
    observed = {
        "probe": "credential-lock-wait-authority", "protocol": protocol,
        **outcomes, "routers_created": routers, "enrollment": enrollment.status,
        "credential": credential.state, "separate_connections": True,
        "postgres_observed_lock_wait": blocked, "blocked_query_table": table,
        "membership_revoked": Membership.objects.get(user=actor, tenant=tenant).revoked_at is not None,
    }
    print(json.dumps(observed, sort_keys=True))
    assert routers == 0 and credential.state == "pending", observed
    assert outcomes["state"] != JobState.SUCCEEDED, observed
