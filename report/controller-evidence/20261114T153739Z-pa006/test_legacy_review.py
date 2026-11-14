"""Controller conformance probes on candidate37a8729; synthetic PostgreSQL data.

Run from backend with pytest.ini and PYTHONPATH=.; these assert acceptance,
not the current defective behavior. Application source stays unchanged.
"""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from domains.common.idempotency import _body_hash
from domains.common.tenant_context import tenant_scope
from domains.jobs.models import IdempotencyKey
from domains.subscriptions import services
from domains.subscriptions.models import PaymentSubmission, SaaSInvoice
from tests.integration.test_idempotency_pa006 import (
    _world, _client_for, _make_invoice, _PROOF_BODY, REAUTH_FAR_FUTURE,
)

from tests.integration.test_idempotency_pa006 import pytestmark


def test_retained_old_proof_scope_must_replay_without_second_submission():
    services.seed_plans()
    world = _world("review-old-proof")
    invoice = _make_invoice(world)
    with tenant_scope(world.tenant.id):
        original = PaymentSubmission.objects.create(
            tenant=world.tenant, invoice=invoice, amount=invoice.amount,
            proof_path="payment-proofs/synthetic-old", proof_mime="image/png",
            proof_size=64, submitted_by=world.owner,
        )
    response_old = {"submission_id": str(original.id), "state": original.state}
    # Exactly the result of migration0004 on a successful main-format row:
    # old scope payment_submission:<tenant>: becomes resource=''.
    old_record = IdempotencyKey.objects.create(
        principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
        operation="payment_submission", resource="", idem_key="review-old-proof-key",
        body_hash=_body_hash(_PROOF_BODY), response_status=201,
        response_body=response_old, created_at=timezone.now(),
    )
    client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
    response = client.post(
        f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
        _PROOF_BODY, headers={"Idempotency-Key": "review-old-proof-key"},
    )
    with tenant_scope(world.tenant.id):
        count = PaymentSubmission.objects.filter(invoice=invoice).count()
    print("OBSERVED legacy proof", response.status_code, response.json(),
          "original", response_old, "submission_count", count,
          "legacy_preserved", IdempotencyKey.objects.filter(pk=old_record.pk).exists())
    assert response.status_code == 201 and response.json() == response_old and count == 1


def test_actual_migration_must_not_erase_ambiguous_committed_effect_guard():
    services.seed_plans()
    world = _world("review-ambiguous-migration")
    body = {"plan_code": "gold", "term": "monthly"}
    # Emulate main's crash window: business effect committed, response absent.
    with tenant_scope(world.tenant.id):
        invoice, _ = services.create_quotation(world.tenant.id, "gold", "monthly")
    IdempotencyKey.objects.all().delete()  # reverse0004 requires empty cache
    executor = MigrationExecutor(connection)
    executor.migrate([("jobs", "0003_alter_job_kind")])
    old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
    old_model = old_apps.get_model("jobs", "IdempotencyKey")
    old_model.objects.create(
        principal=str(world.owner.id), scope=f"quotation:{world.tenant.id}:",
        idem_key="review-ambiguous-key", body_hash=_body_hash(body),
        response_status=None, response_body=None, created_at=timezone.now(),
    )
    # Actual Django/PostgreSQL migration, then a real authenticated HTTP retry.
    MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])
    guard_count = IdempotencyKey.objects.filter(idem_key="review-ambiguous-key").count()
    client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
    response = client.post(
        f"/api/v1/tenants/{world.tenant.id}/quotations", body,
        headers={"Idempotency-Key": "review-ambiguous-key"},
    )
    with tenant_scope(world.tenant.id):
        invoice_count = SaaSInvoice.objects.filter(tenant=world.tenant).count()
    print("OBSERVED ambiguous migration", "guard_count", guard_count,
          "retry_status", response.status_code, "invoice_count", invoice_count,
          "original_invoice", str(invoice.id))
    assert invoice_count == 1, "migration erased unknown-effect guard and retry wrote a second invoice"
    assert response.status_code == 409 or response.json().get("invoice_id") == str(invoice.id)
