"""Run `before STATE.json` on main9903d9b, then `after STATE.json` on candidate.

Use a disposable PostgreSQL database, the same test settings/SECRET_KEY and
MT_STORAGE_ROOT in both processes. All data is synthetic. The after-phase
assertion is expected to fail on candidate7480c80.
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

phase, state_path = sys.argv[1], Path(sys.argv[2])
body = {"file_b64": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode(), "mime": "image/png"}
if phase == "before":
    services.seed_plans()
    owner = User.objects.create_user(email="upgrade-review@test.local", full_name="Synthetic review owner", password="test-password-1234567890", is_active=True)
    tenant = Tenant.objects.create(display_name="Upgrade review", namespace="review-live-upgrade")
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
response = client.post(f'/api/v1/tenants/{state["tenant_id"]}/saas-invoices/{state["invoice_id"]}/payment-submissions', body, format="json", headers={"Idempotency-Key": "review-live-upgrade-key"})
with tenant_scope(state["tenant_id"]):
    submissions = list(PaymentSubmission.objects.filter(invoice_id=state["invoice_id"]).values_list("id", flat=True))
observed = {
    "phase": phase,
    "status": response.status_code,
    "response": response.json(),
    "submission_count": len(submissions),
    "proof_file_count": len(list((settings.MT_STORAGE_ROOT / "payment-proofs").glob("*"))),
    "retained_scopes": list(IdempotencyKey.objects.filter(idem_key="review-live-upgrade-key").values_list("scope", flat=True)),
}
print(json.dumps(observed, default=str, sort_keys=True), flush=True)
if phase == "before":
    assert response.status_code == 201 and len(submissions) == 1
    state["original_response"] = response.json()
    state_path.write_text(json.dumps(state))
else:
    assert response.status_code == 201 and response.json() == state["original_response"] and len(submissions) == 1, "legacy retry created a second logical proof submission after actual migration"
