"""Controller r4: actual main HTTP -> jobs0004/0005 -> PR21 HTTP, isolated DB/storage.

Usage: before|after canonical|urn|urn_ambiguous|uuid_only|uuid_only_ambiguous|urn_only STATE.json
Run before with main9903d9b backend on PYTHONPATH, after with PR21@634da42 backend.
Expected acceptance assertions deliberately fail if retry duplicates effects.
"""
import base64
import json
from pathlib import Path
import sys
import time

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

phase, variant, state_path_raw = sys.argv[1:]
state_path = Path(state_path_raw)
body = {"file_b64": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode(), "mime": "image/png"}
if phase == "before":
    services.seed_plans()
    owner = User.objects.create_user(email="edge-upgrade@test.local", full_name="Synthetic owner", password="test-password-1234567890", is_active=True)
    tenant = Tenant.objects.create(display_name="Synthetic upgrade", namespace="review-edge-upgrade")
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        services.ensure_free_subscription(tenant)
        invoice, _ = services.create_quotation(tenant.id, "gold", "monthly")
    state = {"owner_id": str(owner.id), "tenant_id": str(tenant.id), "invoice_id": str(invoice.id)}
else:
    state = json.loads(state_path.read_text())
    owner = User.objects.get(pk=state["owner_id"])

client = APIClient(enforce_csrf_checks=False, HTTP_HOST="127.0.0.1")
client.force_login(owner)
session = client.session
session["active_tenant_id"] = state["tenant_id"]
session["auth_at"] = time.time()
session["reauth_until"] = "2099-01-01T00:00:00+00:00"
session.save()
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
    body, format="json", headers={"Idempotency-Key": "edge-upgrade-key"},
)
if phase == "before" and variant.endswith("_ambiguous"):
    # Simulate the real old protocol's committed-domain / missing-response window.
    IdempotencyKey.objects.filter(idem_key="edge-upgrade-key").update(response_status=None, response_body=None)
with tenant_scope(state["tenant_id"]):
    submissions = list(PaymentSubmission.objects.filter(invoice_id=state["invoice_id"]).values_list("id", flat=True))
cache_fields = ("principal", "scope", "idem_key", "response_status") if phase == "before" else ("principal", "tenant_scope", "operation", "resource", "idem_key", "response_status")
observed = {
    "phase": phase, "variant": variant, "status": response.status_code,
    "response": response.json(), "submission_count": len(submissions),
    "proof_file_count": len(list((settings.MT_STORAGE_ROOT / "payment-proofs").glob("*"))),
    "retained_keys": list(IdempotencyKey.objects.filter(idem_key="edge-upgrade-key").values(*cache_fields)),
}
print(json.dumps(observed, default=str, sort_keys=True), flush=True)
if phase == "before":
    assert response.status_code == 201 and len(submissions) == 1 and observed["proof_file_count"] == 1
    state["original_response"] = response.json()
    state_path.write_text(json.dumps(state))
else:
    assert len(submissions) == 1 and observed["proof_file_count"] == 1, "migration/retry duplicated a real proof submission and physical file"
    if variant.endswith("_ambiguous"):
        assert response.status_code == 409 or response.json() == state["original_response"], "unknown legacy outcome must remain guarded or reconciled"
    else:
        assert response.status_code == 201 and response.json() == state["original_response"], "known legacy success must replay its original result"
