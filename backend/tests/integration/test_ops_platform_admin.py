"""Tes integrasi keputusan platform admin (M2) — PRODUCT PAY-01/PAY-04.

Approve = transaksi atomik: submission approved + invoice paid + subscription
aktif ke paket yang dikutip + audit + outbox. Reject/request-revision menyimpan
alasan. Non-platform → 404 generik; pelanggaran mesin state → 409 conflict.
"""
from __future__ import annotations

import time
import uuid

import pytest

from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.subscriptions import services as sub_services
from domains.subscriptions.models import (
    PaymentSubmission,
    PlatformPaymentSourceEvent,
    SaaSInvoice,
    Subscription,
)
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.integration


@pytest.fixture
def platform_admin(db):
    user = User.objects.create_user(
        email="platform-admin@test.local",
        full_name="Admin Platform Satu",
        password=TEST_PASSWORD,
        is_active=True,
    )
    user.platform_admin = True
    user.save(update_fields=["platform_admin"])
    return user


@pytest.fixture
def platform_client(api_client, platform_admin):
    api_client.force_login(platform_admin)
    session = api_client.session
    session["auth_at"] = time.time()
    session.save()
    return api_client


def _make_submission(tenant, actor, *, plan_code="silver", term="yearly"):
    """Quotation + submission bukti (jalur M1 disimulasikan lewat ORM)."""
    with tenant_scope(tenant.id):
        invoice, _plan = sub_services.create_quotation(tenant.id, plan_code, term)
        return PaymentSubmission.objects.create(
            tenant=tenant,
            invoice=invoice,
            amount=invoice.amount,
            proof_path="payment-proofs/uji",
            proof_mime="image/png",
            proof_size=1024,
            submitted_by=actor,
        )


def _tenant_client(user, tenant_id):
    """Klien sesi terpisah — fixture auth_client/platform_client berbagi
    objek api_client yang sama, jadi pengguna kedua perlu klien sendiri."""
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=False)
    client.force_login(user)
    session = client.session
    session["active_tenant_id"] = str(tenant_id)
    session["auth_at"] = time.time()
    session.save()
    return client


class TestPlatformApprove:
    def test_approve_pays_invoice_and_activates_subscription(
        self, tenant_a, owner, platform_admin, platform_client
    ):
        submission = _make_submission(tenant_a, owner)
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-appr-1"},
        )
        assert resp.status_code == 204

        with tenant_scope(tenant_a.id):
            submission.refresh_from_db()
            assert submission.state == "approved"
            assert submission.reviewed_at is not None
            assert submission.reviewed_by_id == platform_admin.id

            invoice = SaaSInvoice.objects.get(id=submission.invoice_id)
            assert invoice.state == "paid"
            assert invoice.paid_at is not None

            sub = Subscription.objects.get(tenant_id=tenant_a.id)
            assert sub.state == "active"
            assert sub.plan.code == "silver"
            assert sub.period_start == invoice.period_start
            assert sub.period_end == invoice.period_end
            assert sub.anchor_day == invoice.period_start.day

            # Event sumber pembayaran platform immutable (TK-003/ACC-12).
            assert PlatformPaymentSourceEvent.objects.filter(submission=submission).count() == 1
            # Audit tercatat pada tenant pemilik (redacted payload).
            assert tenant_a.audit_events.filter(action_code="payment_submission.approve").exists()

    def test_owner_sees_active_subscription_after_approval(
        self, tenant_a, owner, platform_client
    ):
        submission = _make_submission(tenant_a, owner, plan_code="bronze", term="monthly")
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-appr-2"},
        )
        assert resp.status_code == 204
        owner_client = _tenant_client(owner, tenant_a.id)
        resp = owner_client.get(f"/api/v1/tenants/{tenant_a.id}/subscription")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "active"
        assert data["plan"]["code"] == "bronze"
        assert data["pending_invoice"] is None  # invoice sudah paid

    def test_approve_replay_same_key_is_safe(self, tenant_a, owner, platform_client):
        submission = _make_submission(tenant_a, owner)
        first = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-appr-3"},
        )
        replay = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-appr-3"},
        )
        assert first.status_code == 204
        # Replay key+isi sama → respons logis sama, BUKAN 409 mesin state.
        assert replay.status_code == 204
        with tenant_scope(tenant_a.id):
            assert PaymentSubmission.objects.filter(id=submission.id, state="approved").count() == 1


class TestPlatformRejectAndRevision:
    def test_reject_stores_reason_and_keeps_invoice_open(self, tenant_a, owner, platform_client):
        submission = _make_submission(tenant_a, owner)
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/reject",
            {"reason": "Bukti tidak dapat dibaca"},
            headers={"Idempotency-Key": "pf-rej-1"},
        )
        assert resp.status_code == 204
        with tenant_scope(tenant_a.id):
            submission.refresh_from_db()
            assert submission.state == "rejected"
            assert submission.review_note == "Bukti tidak dapat dibaca"
            assert SaaSInvoice.objects.get(id=submission.invoice_id).state == "open"
            assert Subscription.objects.get(tenant_id=tenant_a.id).state == "free"

    def test_request_revision_stores_reason(self, tenant_a, owner, platform_client):
        submission = _make_submission(tenant_a, owner)
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/request-revision",
            {"reason": "Unggah ulang dengan nominal terlihat"},
            headers={"Idempotency-Key": "pf-rev-1"},
        )
        assert resp.status_code == 204
        with tenant_scope(tenant_a.id):
            submission.refresh_from_db()
            assert submission.state == "revision_requested"
            assert submission.review_note.startswith("Unggah ulang")

    @pytest.mark.parametrize("action", ["reject", "request-revision"])
    def test_reason_required_422(self, tenant_a, owner, platform_client, action):
        submission = _make_submission(tenant_a, owner)
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/{action}",
            {"reason": "   "},
            headers={"Idempotency-Key": f"pf-{action}-req"},
        )
        assert resp.status_code == 422
        assert "reason" in resp.json()["field_errors"]


class TestPlatformStateMachine:
    def test_double_decision_conflict_409(self, tenant_a, owner, platform_client):
        submission = _make_submission(tenant_a, owner)
        first = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-sm-1"},
        )
        assert first.status_code == 204
        # Keputusan kedua (key berbeda = permintaan baru) → 409 error.conflict.
        second = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/reject",
            {"reason": "salah klik"},
            headers={"Idempotency-Key": "pf-sm-2"},
        )
        assert second.status_code == 409
        assert second.json()["code"] == "conflict"

    def test_approve_after_reject_conflict_409(self, tenant_a, owner, platform_client):
        submission = _make_submission(tenant_a, owner)
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/reject",
            {"reason": "bukan bukti sah"},
            headers={"Idempotency-Key": "pf-sm-3"},
        )
        assert resp.status_code == 204
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-sm-4"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "conflict"

    def test_idempotency_body_conflict_409(self, tenant_a, owner, platform_client):
        submission = _make_submission(tenant_a, owner)
        platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/reject",
            {"reason": "alasan pertama"},
            headers={"Idempotency-Key": "pf-sm-5"},
        )
        # Key sama dipakai untuk isi berbeda → 409 idempotency_conflict.
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/reject",
            {"reason": "alasan kedua"},
            headers={"Idempotency-Key": "pf-sm-5"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "idempotency_conflict"


class TestPlatformQueueAccess:
    def test_queue_lists_across_tenants(self, tenant_a, tenant_b, owner, platform_client):
        sub_a = _make_submission(tenant_a, owner)
        sub_b = _make_submission(tenant_b, owner, plan_code="gold")
        resp = platform_client.get("/api/v1/platform/payment-submissions?queue=submitted")
        assert resp.status_code == 200
        items = resp.json()
        ids = {i["id"] for i in items}
        assert {str(sub_a.id), str(sub_b.id)} <= ids
        by_id = {i["id"]: i for i in items}
        assert by_id[str(sub_a.id)]["tenant_display_name"] == "Tenant A"
        assert by_id[str(sub_a.id)]["plan_code"] == "silver"
        assert by_id[str(sub_a.id)]["assignee"] is None

    def test_queue_moves_after_decision_and_assignee_set(
        self, tenant_a, owner, platform_admin, platform_client
    ):
        submission = _make_submission(tenant_a, owner)
        assert platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pf-q-1"},
        ).status_code == 204
        submitted = platform_client.get("/api/v1/platform/payment-submissions?queue=submitted").json()
        assert str(submission.id) not in {i["id"] for i in submitted}
        approved = platform_client.get("/api/v1/platform/payment-submissions?queue=approved").json()
        entry = next(i for i in approved if i["id"] == str(submission.id))
        assert entry["assignee"] == platform_admin.full_name

    def test_queue_param_validation(self, platform_client):
        resp = platform_client.get("/api/v1/platform/payment-submissions")
        assert resp.status_code == 422
        assert "queue" in resp.json()["field_errors"]
        resp = platform_client.get("/api/v1/platform/payment-submissions?queue=everything")
        assert resp.status_code == 422

    def test_non_platform_user_404(self, tenant_a, owner, auth_client):
        submission = _make_submission(tenant_a, owner)
        # Owner tenant (bukan platform) → 404 generik, tidak membocorkan antrean.
        assert auth_client.get("/api/v1/platform/payment-submissions?queue=submitted").status_code == 404
        assert (
            auth_client.post(
                f"/api/v1/platform/payment-submissions/{submission.id}/approve",
                headers={"Idempotency-Key": "pf-np-1"},
            ).status_code
            == 404
        )
        # Belum masuk → 401 (envelope standar; klien benar-benar anonim).
        from rest_framework.test import APIClient

        anon = APIClient(enforce_csrf_checks=False)
        resp = anon.get("/api/v1/platform/payment-submissions?queue=submitted")
        assert resp.status_code == 401
        assert resp.json()["code"] == "unauthorized"

    def test_unknown_submission_404(self, platform_client):
        resp = platform_client.post(
            f"/api/v1/platform/payment-submissions/{uuid.uuid4()}/approve",
            headers={"Idempotency-Key": "pf-unk-1"},
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "not_found"

    def test_malformed_submission_id_422(self, platform_client):
        """submission_id salah bentuk → 422 (PA-006: idempotency layer
        memvalidasi identitas UUID terstruktur SEBELUM klaim; acceptance
        task/0010 "input malformed structured 422"). Ekspektasi lama 404
        diubah mengikuti acceptance PA-006; jalur 404-generik bagi
        non-platform tetap dijaga PlatformApiView.initial() sebelum
        dekorator (lihat test_platform_denied_*), tidak bocor apa pun."""
        resp = platform_client.post(
            "/api/v1/platform/payment-submissions/bukan-uuid/approve",
            headers={"Idempotency-Key": "pf-unk-2"},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "validation_error"
