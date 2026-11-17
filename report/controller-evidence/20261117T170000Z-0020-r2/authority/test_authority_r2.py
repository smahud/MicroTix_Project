"""Independent R2 acceptance probes, app source read-only at main64b68f8.

Controlled I/O is explicitly sandbox evidence; real PostgreSQL and two
connections observe authority revocation and committed domain state.
Assertions state required safety, so confirmed defects intentionally FAIL.
"""
from __future__ import annotations

import json
import threading
import uuid

import pytest
from django.db import close_old_connections, connection, connections
from django.test import override_settings
from django.utils import timezone

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs import engine
from domains.jobs.models import Job, JobState
from domains.network.models import Router, RouterEnrollment, SstpAccount, WireGuardPeer
from domains.radius.models import CutoverRun
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
        email=f"r2-{label}-{suffix}@test.local", full_name="Controller R2",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"R2 {label}", namespace=f"rtrw-r2-{suffix}")
    Membership.objects.create(user=actor, tenant=tenant, role=Role.OWNER)
    return tenant, actor


@pytest.mark.parametrize("protocol", ["wireguard", "sstp"])
def test_revocation_during_enrollment_probe_prevents_new_router(monkeypatch, protocol):
    """I/O returns after actor revocation: no fresh router/credential commit.

    Both production VerifyApiSslHandler and finalize_verification are used;
    only remote TLS probe is controlled with an Event barrier.
    """
    tenant, actor = _identity(protocol)
    suffix = uuid.uuid4().hex[:10]
    ip = f"100.125.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}"
    with tenant_scope(tenant.id):
        enrollment = RouterEnrollment.objects.create(
            tenant=tenant, display_name="R2 enrollment", router_code=f"R2-{suffix}",
            protocol=protocol, tunnel_ip=ip, token_hash=uuid.uuid4().hex,
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
            status=RouterEnrollment.Status.BOOTSTRAPPED, created_by=actor,
        )
        if protocol == "sstp":
            credential = SstpAccount.objects.create(
                tenant=tenant, enrollment=enrollment, tunnel_ip=ip,
                username=f"r2-{suffix}", password_ref="synthetic-not-decrypted",
                state=SstpAccount.State.PENDING,
            )
        else:
            credential = WireGuardPeer.objects.create(
                tenant=tenant, enrollment=enrollment, allowed_ip=ip,
                public_key=f"r2-probe-{suffix}", state=WireGuardPeer.State.PENDING,
            )
    job = engine.create_job(
        tenant_id=tenant.id, kind="verify_api_ssl", actor=actor,
        payload={"enrollment_id": str(enrollment.id)},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    probe_active, finish_probe = threading.Event(), threading.Event()
    results, errors, pids = {}, [], {}

    class ControlledConnectivityAdapter:
        def probe_connectivity(self, router_context):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["worker"] = cursor.fetchone()[0]
            assert not connection.in_atomic_block, "I/O must be outside DB transaction"
            probe_active.set()
            assert finish_probe.wait(15), "controller failed to release TLS probe"
            return {"ok": True, "cert_sha256": "a" * 64}

    monkeypatch.setattr(
        "adapters.routeros.factory.active_routeros_adapter", lambda: ControlledConnectivityAdapter()
    )

    def worker():
        close_old_connections()
        try:
            final = engine.run_claimed(Job.objects.get(id=claimed.id))
            results.update(state=final.state, error=final.error_code)
        except BaseException as exc:
            errors.append(repr(exc))
        finally:
            connections.close_all()

    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        thread = threading.Thread(target=worker, name="r2-enrollment-revocation")
        thread.start()
        try:
            assert probe_active.wait(15), "actual handler never reached TLS probe"
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids["controller"] = cursor.fetchone()[0]
            assert pids["controller"] != pids["worker"]
            assert Membership.objects.filter(user=actor, tenant=tenant).update(revoked_at=timezone.now()) == 1
        finally:
            finish_probe.set()
            thread.join(20)
    assert not thread.is_alive(), "worker did not finish"
    assert not errors, errors
    assert "state" in results, "missing thread outcome"
    with tenant_scope(tenant.id):
        enrollment.refresh_from_db()
        credential.refresh_from_db()
        routers = Router.objects.filter(tenant=tenant).count()
    observed = {
        "probe": "revoked-during-enrollment-io", "protocol": protocol,
        **results, "routers_created": routers, "enrollment": enrollment.status,
        "credential": credential.state, "separate_connections": True,
    }
    print(json.dumps(observed, sort_keys=True))
    assert routers == 0 and credential.state == "pending", observed


def test_b6_uses_selected_adapter_instead_of_simulator_success(monkeypatch):
    """Actual api_ssl adapter gates unverified cutover mutations.

    No remote I/O is possible here: real ApiSslAdapter.rollback_radius
    deliberately raises cutover_pending_lab. B6 must respect that gate.
    """
    tenant, actor = _identity("b6-selected")
    with tenant_scope(tenant.id):
        router = Router.objects.create(
            tenant=tenant, display_name="R2 rollback", router_code="r2-rollback",
            tunnel_ip="100.125.252.252", mode=Router.Mode.MANAGED,
            credential_ref="synthetic", enforcement_mode=Router.Enforcement.RADIUS_AUTHORITATIVE,
        )
        run = CutoverRun.objects.create(
            tenant=tenant, router=router, created_by=actor,
            phase=CutoverRun.Phase.B5, state=CutoverRun.State.AUTHORITATIVE,
            evidence={"B2": {"baseline": "controlled"}},
        )
    job = engine.create_job(
        tenant_id=tenant.id, kind="radius_cutover_step", actor=actor, router=router,
        payload={"rollback": True},
    )
    claimed = engine.claim_next()
    assert claimed is not None and claimed.id == job.id
    with override_settings(MT_ROUTEROS_ADAPTER="api_ssl"):
        # Spy on the selected production adapter method without changing it.
        from adapters.routeros.apiclient import ApiSslAdapter
        real_rollback = ApiSslAdapter.rollback_radius
        selected_adapter_calls = []

        def record_rollback(self, context, baseline):
            selected_adapter_calls.append("api_ssl.rollback_radius")
            return real_rollback(self, context, baseline)

        monkeypatch.setattr(ApiSslAdapter, "rollback_radius", record_rollback)
        final = engine.run_claimed(claimed)
    with tenant_scope(tenant.id):
        run.refresh_from_db()
        router.refresh_from_db()
    observed = {
        "probe": "b6-selected-adapter", "selected_adapter": "api_ssl",
        "selected_adapter_calls": selected_adapter_calls,
        "job": final.state, "error": final.error_code,
        "run": run.state, "enforcement": router.enforcement_mode,
        "readback": run.evidence.get("B6", {}).get("rollback_readback_ok"),
    }
    print(json.dumps(observed, sort_keys=True))
    assert selected_adapter_calls and final.state != JobState.SUCCEEDED, observed
    assert router.enforcement_mode == Router.Enforcement.RADIUS_AUTHORITATIVE, observed
