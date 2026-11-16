"""Independent effect and blocker evidence; no application modifications."""
import json

import pytest

from domains.common.tenant_context import tenant_scope
from domains.subscriptions import services as sub_services
from tests.integration import test_idempotency_pa006 as candidate_tests
from tests.integration.test_idempotency_pa006 import _world, _client_for, REAUTH_FAR_FUTURE
from test_review_edges import pytestmark


def test_selected_uuid_alias_must_select_same_target_before_replay():
    from domains.customers.models import MigrationSession
    from domains.customers.services import preview_migration_summary
    from domains.jobs.models import JobDetail
    from domains.network.models import DiscoveryObject, DiscoverySnapshot, Router

    sub_services.seed_plans()
    world = _world("review-selected-alias")
    client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
    with tenant_scope(world.tenant.id):
        router = Router.objects.create(tenant=world.tenant, display_name="Synthetic", router_code="review-selected")
        snapshot = DiscoverySnapshot.objects.create(tenant=world.tenant, router=router, status=DiscoverySnapshot.Status.SUCCEEDED)
        obj = DiscoveryObject.objects.create(tenant=world.tenant, router=router, snapshot=snapshot, username="review.selected", kind=DiscoveryObject.Kind.PPPOE)
        session = MigrationSession.objects.create(tenant=world.tenant, router=router, snapshot=snapshot, state=MigrationSession.State.DISCOVERED)
        canonical_counts = preview_migration_summary(session, [str(obj.id)])
    alias_body = {"selected_account_ids": [obj.id.hex.upper()]}
    body = {"selected_account_ids": [str(obj.id)]}
    url = f"/api/v1/tenants/{world.tenant.id}/migrations/{session.id}/commit"
    headers = {"Idempotency-Key": "review-selected-alias"}
    first = client.post(url, alias_body, format="json", headers=headers)
    retry = client.post(url, body, format="json", headers=headers)
    assert first.status_code == retry.status_code == 202
    assert first.json() == retry.json()
    with tenant_scope(world.tenant.id):
        session.refresh_from_db()
        detail = JobDetail.objects.get(job_id=first.json()["job_id"])
    observed = {
        "statuses": [first.status_code, retry.status_code],
        "same_job": first.json() == retry.json(),
        "canonical_expected_to_create": canonical_counts["to_create"],
        "actual_alias_to_create": session.counts["to_create"],
        "actual_alias_unchanged": session.counts["unchanged"],
        "payload_selected_is_canonical": detail.payload.get("selected_account_ids") == [str(obj.id)],
    }
    print("OBSERVED selected alias effect", json.dumps(observed, sort_keys=True))
    assert canonical_counts["to_create"] == 1
    assert session.counts["to_create"] == 1 and detail.payload["selected_account_ids"] == [str(obj.id)], "hash-equivalent UUID must select the same logical target in preview and job payload"


@pytest.mark.parametrize("method_name", [
    "test_concurrent_http_same_identity_waits_then_replays_single_effect",
    "test_concurrent_http_same_key_different_body_conflict",
    "test_concurrent_http_platform_decision_replay_204_single_effect",
    "test_http_leader_rollback_after_writes_contender_takes_over",
])
def test_concurrency_evidence_asserts_query_and_actual_blocker(monkeypatch, method_name):
    """Supplement candidate's generic Lock assertion with SQL/blocker proof.

    Use existing production HTTP paths and state assertions unchanged. The
    test-only observation wrapper asserts leader->test holder and contender
    ->leader edges; absence/wrong SQL/blocker is a hard failure.
    """
    sub_services.seed_plans()
    original_assert = candidate_tests._assert_lock_wait
    holder_pid = candidate_tests._pg_pid()
    observed = []

    def stronger_assert(observer, pid, *, context, deadline_s=30.0):
        original_assert(observer, pid, context=context, deadline_s=deadline_s)
        with observer.cursor() as cur:
            cur.execute("SELECT query, pg_blocking_pids(pid) FROM pg_stat_activity WHERE pid=%s", (pid,))
            query, blockers = cur.fetchone()
        if not observed:
            assert "FOR UPDATE" in query.upper(), (context, "expected domain row lock")
            assert holder_pid in blockers, (context, blockers, holder_pid)
            observed.append({"role": "leader", "pid": pid, "blockers": blockers, "query_kind": "domain SELECT FOR UPDATE"})
        else:
            assert "INSERT INTO jobs_idempotency_key" in query and "ON CONFLICT" in query, (context, "expected idempotency INSERT")
            assert observed[0]["pid"] in blockers, (context, blockers, observed[0]["pid"])
            observed.append({"role": "contender", "pid": pid, "blockers": blockers, "query_kind": "claim INSERT ON CONFLICT"})

    monkeypatch.setattr(candidate_tests, "_assert_lock_wait", stronger_assert)
    getattr(candidate_tests.TestConcurrentHttpClaimReplay(), method_name)()
    assert len(observed) == 2
    assert observed[0]["pid"] != observed[1]["pid"]
    print("OBSERVED forced HTTP wait graph", json.dumps({"case": method_name, "edges": observed}, sort_keys=True))
