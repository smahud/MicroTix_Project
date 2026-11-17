"""Independent controller conformance probes; expected to fail on candidate.

Run from candidate/backend with --ds=microtix.settings_test. Real PostgreSQL,
authenticated HTTP client and real domain writes; no production access.
"""
from decimal import Decimal
from uuid import uuid4

import pytest
from domains.billing.models import BillingPackage
from domains.common.tenant_context import tenant_scope
from domains.customers.models import Customer, Service, MigrationAccountDecision, MigrationSession
from domains.customers.services import conflict_group_id
from domains.network.models import Router, DiscoverySnapshot, DiscoveryObject
from domains.subscriptions import services as sub_services
from tests.integration.test_idempotency_pa006 import _setup_world, _client

pytestmark = pytest.mark.django_db


def _migration_world(namespace):
    sub_services.seed_plans()
    world = _setup_world(namespace)
    client = _client(world.owner, active_tenant=world.tenant.id)
    with tenant_scope(world.tenant.id):
        sessions = []
        for i, username in enumerate(("scope.repro", "Scope.Repro")):
            router = Router.objects.create(tenant=world.tenant, display_name=f"Scope R{i}", router_code=f"scope-r{i}")
            snapshot = DiscoverySnapshot.objects.create(tenant=world.tenant, router=router, status=DiscoverySnapshot.Status.SUCCEEDED)
            DiscoveryObject.objects.create(tenant=world.tenant, router=router, snapshot=snapshot, username=username, kind=DiscoveryObject.Kind.PPPOE)
            sessions.append(MigrationSession.objects.create(tenant=world.tenant, router=router, snapshot=snapshot, state=MigrationSession.State.DISCOVERED))
    return world, client, sessions, conflict_group_id(["scope.repro", "Scope.Repro"])


def test_same_key_same_group_different_session_must_apply_second_resolution():
    world, client, sessions, group_id = _migration_world("scope-parent")
    body = {"resolution": "merge"}
    headers = {"Idempotency-Key": "scope-parent-key"}
    base = f"/api/v1/tenants/{world.tenant.id}/migrations"
    first = client.post(f"{base}/{sessions[0].id}/identity-conflicts/{group_id}", body, format="json", headers=headers)
    assert first.status_code == 204, first.content
    second = client.post(f"{base}/{sessions[1].id}/identity-conflicts/{group_id}", body, format="json", headers=headers)
    assert second.status_code == 204, second.content
    with tenant_scope(world.tenant.id):
        counts = [MigrationAccountDecision.objects.filter(session=s).count() for s in sessions]
        print("OBSERVED per-session decisions after 204/204:", counts)
        assert counts == [2, 2], "second 204 replayed first session; second session remained unresolved"


@pytest.mark.parametrize("bad_parent,expected", [("not-a-uuid",422), (str(uuid4()),404)])
def test_cached_group_must_not_skip_invalid_or_missing_parent(bad_parent, expected):
    world, client, sessions, group_id = _migration_world("scope-bad-parent"+str(expected))
    body = {"resolution": "merge"}
    headers = {"Idempotency-Key": "scope-bad-parent-key"}
    base = f"/api/v1/tenants/{world.tenant.id}/migrations"
    valid = client.post(f"{base}/{sessions[0].id}/identity-conflicts/{group_id}", body, format="json", headers=headers)
    assert valid.status_code == 204, valid.content
    invalid = client.post(f"{base}/{bad_parent}/identity-conflicts/{group_id}", body, format="json", headers=headers)
    print("OBSERVED cached resolution with invalid parent:", bad_parent, invalid.status_code)
    assert invalid.status_code == expected, "cached group response bypassed parent identity validation/lookup"


def test_body_uuid_alias_must_replay_canonical_identity():
    sub_services.seed_plans()
    world = _setup_world("scope-body-alias")
    client = _client(world.owner, active_tenant=world.tenant.id)
    with tenant_scope(world.tenant.id):
        customer = Customer.objects.create(tenant=world.tenant, display_name="Scope alias", customer_code="C-SCOPE")
        service = Service.objects.create(tenant=world.tenant, customer=customer, service_code="S-SCOPE")
        package = BillingPackage.objects.create(tenant=world.tenant, name="Scope alias package", monthly_price=Decimal("50000"))
    url = f"/api/v1/tenants/{world.tenant.id}/services/{service.id}/billing-package"
    headers = {"Idempotency-Key":"scope-body-alias-key"}
    first = client.post(url, {"package_id":str(package.id)}, format="json", headers=headers)
    assert first.status_code == 200, first.content
    alias = client.post(url, {"package_id":package.id.hex.upper()}, format="json", headers=headers)
    print("OBSERVED equivalent package UUID body alias:", first.status_code, alias.status_code, alias.content)
    assert alias.status_code == 200, "structured identity in body was hashed before UUID canonicalization"
    assert alias.json() == first.json()
