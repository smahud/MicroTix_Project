"""Independent acceptance probes; application source stays read-only.

Assertions describe required behavior, not PR19's current failures.
All credentials and data are synthetic; logs contain only secret-presence
booleans, never the synthetic password value.
"""
import json

import pytest

from domains.common.tenant_context import tenant_scope
from domains.jobs.models import IdempotencyKey, OutboxEvent
from domains.subscriptions import services as sub_services
from tests.integration.test_idempotency_pa006 import (
    _world, _client_for, REAUTH_FAR_FUTURE,
)
from tests.integration.test_billing_payment_concurrency import (
    _setup_world, _record_payment,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(transaction=True, available_apps=[
        "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
        "domains.tenancy", "domains.identity", "domains.network", "domains.customers",
        "domains.subscriptions", "domains.billing", "domains.documents", "domains.audit",
        "domains.jobs",
    ]),
]


def test_payment_allocation_uuid_alias_must_replay_original_action():
    from domains.audit.models import AuditEvent
    from domains.billing.models import PaymentAllocation
    from domains.documents.models import IssuedDocument

    sub_services.seed_plans()
    world = _setup_world("review-nested-uuid", invoice_totals=["100000"])
    payment = _record_payment(world, "100000")
    client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
    url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
    body = {"allocations": [{"invoice_id": str(world.invoices[0].id), "amount": "100000"}]}
    alias_body = {"allocations": [{"invoice_id": world.invoices[0].id.hex.upper(), "amount": "100000"}]}
    headers = {"Idempotency-Key": "review-nested-uuid"}
    first = client.post(url, body, format="json", headers=headers)
    alias = client.post(url, alias_body, format="json", headers=headers)
    identical = client.post(url, body, format="json", headers=headers)
    with tenant_scope(world.tenant.id):
        counts = {
            "allocations": PaymentAllocation.objects.filter(payment=payment).count(),
            "receipts": IssuedDocument.objects.filter(ref_id=str(payment.id)).count(),
            "audit": AuditEvent.objects.filter(target_id=payment.id, action_code="internet_payment.verified").count(),
        }
    counts["outbox"] = OutboxEvent.objects.filter(aggregate_id=payment.id, event_type="internet_payment.verified").count()
    print("OBSERVED nested allocation UUID", json.dumps({
        "statuses": [first.status_code, alias.status_code, identical.status_code],
        "alias_error": alias.json().get("code"), "effect_counts": counts,
    }, sort_keys=True))
    assert first.status_code == identical.status_code == 200
    assert first.json() == identical.json()
    assert counts == {"allocations": 1, "receipts": 1, "audit": 1, "outbox": 1}
    assert alias.status_code == 200 and alias.json() == first.json(), "typed nested UUID alias must replay same logical verification"


def test_csv_validation_must_not_cache_or_replay_plaintext_credential():
    import secrets

    sub_services.seed_plans()
    world = _world("review-secret-cache")
    client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
    sentinel = secrets.token_urlsafe(24)
    created = client.post(
        f"/api/v1/tenants/{world.tenant.id}/imports",
        {"mode": "create", "file_name": "synthetic.csv", "rows": [
            {"username": "review.synthetic", "password": sentinel, "kind": "pppoe", "customer_name": "Synthetic"},
        ]}, format="json", headers={"Idempotency-Key": "review-secret-create"},
    )
    assert created.status_code == 201
    url = f"/api/v1/tenants/{world.tenant.id}/imports/{created.json()['id']}/validate"
    headers = {"Idempotency-Key": "review-secret-validate"}
    first = client.post(url, format="json", headers=headers)
    replay = client.post(url, format="json", headers=headers)
    record = IdempotencyKey.objects.get(idem_key="review-secret-validate")
    observed = {
        "statuses": [first.status_code, replay.status_code],
        "plaintext_in_initial_response": sentinel in json.dumps(first.json()),
        "plaintext_in_cached_response": sentinel in json.dumps(record.response_body),
        "plaintext_in_replayed_response": sentinel in json.dumps(replay.json()),
    }
    print("OBSERVED secret cache", json.dumps(observed, sort_keys=True))
    assert first.status_code == replay.status_code == 200
    assert not observed["plaintext_in_cached_response"], "idempotency response cache must not persist a plaintext credential"
    assert not observed["plaintext_in_replayed_response"], "retry must not replay a plaintext credential"
