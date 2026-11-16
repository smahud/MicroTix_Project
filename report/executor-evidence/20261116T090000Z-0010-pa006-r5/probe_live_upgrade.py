"""Executor r5: actual old-source HTTP -> real jobs0004/0005 migration -> new HTTP.

Adapted from the controller r4 live probe methodology
(report/controller-evidence/20261115T053138Z-pa006-r4/live_upgrade_aliases.py)
and extended with the resource-position platform variant.

Usage:
  probe.py before <variant> <state.json>   # run with OLD code (main@9903d9b)
  probe.py after  <variant> <state.json>   # run with NEW code (candidate)

Variants (tenant position): canonical | urn | urn_ambiguous | uuid_only |
    uuid_only_ambiguous | urn_only
Variant (resource position, platform decision): platform_uuid_resource

Deliberate acceptance assertions fail loudly if the migration/retry
duplicates effects (submission/physical file/decision 1->2).
"""
import base64
import json
import sys
import time
from pathlib import Path

import django

django.setup()

from django.conf import settings
from rest_framework.test import APIClient

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs.models import IdempotencyKey
from domains.subscriptions import services
from domains.subscriptions.models import PaymentSubmission
from domains.tenancy.models import Membership, Role, Tenant

phase, variant, state_path_raw = sys.argv[1:4]
state_path = Path(state_path_raw)
body = {
    "file_b64": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode(),
    "mime": "image/png",
}
key = f"r5-upgrade-{variant}"

if phase == "before":
    services.seed_plans()
    owner = User.objects.create_user(
        email=f"edge-r5-{variant}@test.local", full_name="Synthetic owner",
        password="test-password-1234567890", is_active=True,
    )
    tenant = Tenant.objects.create(display_name=f"Synthetic r5 {variant}", namespace=f"r5-{variant}")
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        services.ensure_free_subscription(tenant)
        invoice, _ = services.create_quotation(tenant.id, "gold", "monthly")
    state = {"owner_id": str(owner.id), "tenant_id": str(tenant.id), "invoice_id": str(invoice.id)}
    if variant == "platform_uuid_resource":
        admin = User.objects.create_user(
            email=f"platform-r5-{variant}@test.local", full_name="Synthetic platform admin",
            password="test-password-1234567890", is_active=True,
        )
        admin.platform_admin = True
        admin.save(update_fields=["platform_admin"])
        with tenant_scope(tenant.id):
            submission = PaymentSubmission.objects.create(
                tenant=tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/r5-platform", proof_mime="image/png",
                proof_size=64, submitted_by=owner,
            )
        state["admin_id"] = str(admin.id)
        state["submission_id"] = str(submission.id)
else:
    state = json.loads(state_path.read_text())

user = (
    User.objects.get(pk=state["admin_id"])
    if variant == "platform_uuid_resource"
    else User.objects.get(pk=state["owner_id"])
)
client = APIClient(enforce_csrf_checks=False, HTTP_HOST="127.0.0.1")
client.force_login(user)
session = client.session
session["active_tenant_id"] = state["tenant_id"]
session["auth_at"] = time.time()
session["reauth_until"] = "2099-01-01T00:00:00+00:00"
session.save()

if variant == "platform_uuid_resource":
    resource_url = state["submission_id"]
    if phase == "before":
        resource_url = "uuid:" + state["submission_id"]
    response = client.post(
        f"/api/v1/platform/payment-submissions/{resource_url}/approve",
        headers={"Idempotency-Key": key},
    )
else:
    tenant_url = state["tenant_id"]
    if phase == "before":
        if variant in ("urn", "urn_ambiguous"):
            tenant_url = "urn:uuid:" + state["tenant_id"]
        elif variant.startswith("uuid_only"):
            tenant_url = "uuid:" + state["tenant_id"]
        elif variant == "urn_only":
            tenant_url = "urn:" + state["tenant_id"]
    response = client.post(
        f'/api/v1/tenants/{tenant_url}/saas-invoices/{state["invoice_id"]}/payment-submissions',
        body, format="json", headers={"Idempotency-Key": key},
    )

if phase == "before" and variant.endswith("_ambiguous"):
    # Simulate the real old protocol's committed-domain / missing-response
    # window (same injection as controller r4 evidence).
    IdempotencyKey.objects.filter(idem_key=key).update(response_status=None, response_body=None)

if variant == "platform_uuid_resource":
    from domains.audit.models import AuditEvent
    from domains.jobs.models import OutboxEvent

    with tenant_scope(state["tenant_id"]):
        submission_count = PaymentSubmission.objects.filter(
            id=state["submission_id"], state=PaymentSubmission.State.APPROVED
        ).count()
        audit_count = AuditEvent.objects.filter(
            target_id=state["submission_id"], action_code="payment_submission.approve"
        ).count()
    outbox_count = OutboxEvent.objects.filter(
        aggregate_id=state["submission_id"], event_type="payment_submission.approve"
    ).count()
    effects = {
        "approved_submission_count": submission_count,
        "audit_approve_count": audit_count,
        "outbox_approve_count": outbox_count,
    }
else:
    with tenant_scope(state["tenant_id"]):
        submissions = list(
            PaymentSubmission.objects.filter(invoice_id=state["invoice_id"])
            .values_list("id", flat=True)
        )
    effects = {
        "submission_count": len(submissions),
        "proof_file_count": len(list((settings.MT_STORAGE_ROOT / "payment-proofs").glob("*"))),
    }

cache_fields = (
    ("principal", "scope", "idem_key", "response_status")
    if phase == "before"
    else ("principal", "tenant_scope", "operation", "resource", "idem_key", "response_status")
)
observed = {
    "phase": phase,
    "variant": variant,
    "status": response.status_code,
    "response": response.json() if response.content else None,
    **effects,
    "retained_keys": list(IdempotencyKey.objects.filter(idem_key=key).values(*cache_fields)),
}
print(json.dumps(observed, default=str, sort_keys=True), flush=True)

if phase == "before":
    if variant == "platform_uuid_resource":
        assert response.status_code == 204, "old platform approve must succeed"
        assert effects == {
            "approved_submission_count": 1, "audit_approve_count": 1, "outbox_approve_count": 1,
        }, effects
    else:
        assert response.status_code == 201 and effects["submission_count"] == 1 \
            and effects["proof_file_count"] == 1, (response.status_code, effects)
    state["original_response"] = response.json() if response.content else None
    state["original_status"] = response.status_code
    state_path.write_text(json.dumps(state))
else:
    if variant == "platform_uuid_resource":
        assert effects == {
            "approved_submission_count": 1, "audit_approve_count": 1, "outbox_approve_count": 1,
        }, f"migration/retry duplicated a real platform decision: {effects}"
        assert response.status_code == 204, "known legacy platform decision must replay 204"
    elif variant.endswith("_ambiguous"):
        assert effects["submission_count"] == 1 and effects["proof_file_count"] == 1, \
            f"migration/retry duplicated a real proof submission and physical file: {effects}"
        assert response.status_code == 409 or response.json() == state["original_response"], \
            "unknown legacy outcome must remain guarded or reconciled"
    else:
        assert effects["submission_count"] == 1 and effects["proof_file_count"] == 1, \
            f"migration/retry duplicated a real proof submission and physical file: {effects}"
        assert response.status_code == 201 and response.json() == state["original_response"], \
            "known legacy success must replay its original result"
print(f"PROBE {phase} {variant}: PASS", flush=True)
