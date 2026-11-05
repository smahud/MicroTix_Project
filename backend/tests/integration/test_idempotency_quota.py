"""Idempotency + kuota + storage upload (TK-105/TK-106)."""
from __future__ import annotations

import base64
import pytest

pytestmark = pytest.mark.integration


def test_quotation_idempotent_replay(auth_client, tenant_a, owner):
    # Pasang reauth agar aksi sensitif lolos.
    import time as _time

    session = auth_client.session
    session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()
    headers = {"Idempotency-Key": "quote-1"}
    body = {"plan_code": "gold", "term": "monthly"}
    resp1 = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/quotations", body, headers=headers)
    assert resp1.status_code == 201
    # Replay key sama + isi sama → respons logis sama, tidak ada invoice baru.
    resp2 = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/quotations", body, headers=headers)
    assert resp2.status_code == 201
    assert resp2.json()["invoice_id"] == resp1.json()["invoice_id"]
    # Key sama + isi BERBEDA → 409 idempotency_conflict.
    resp3 = auth_client.post(
        f"/api/v1/tenants/{tenant_a.id}/quotations",
        {"plan_code": "gold", "term": "yearly"},
        headers=headers,
    )
    assert resp3.status_code == 409
    assert resp3.json()["code"] == "idempotency_conflict"
    # Tanpa Idempotency-Key → 422.
    resp4 = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/quotations", body)
    assert resp4.status_code == 422


def test_quota_reservation_atomic(tenant_a, db):
    """Siklus SUB-02: pending dihitung; release membebaskan; commit = materialisasi."""
    from domains.common.envelope import ApiError
    from domains.common.tenant_context import tenant_scope
    from domains.network.models import Router
    from domains.subscriptions import services

    # Free: routers_limit=1 → reservasi pertama OK, kedua quota_exceeded (pending dihitung).
    first = services.reserve(tenant_a.id, "routers")
    assert first.state == "pending"
    with pytest.raises(ApiError) as exc:
        services.reserve(tenant_a.id, "routers")
    assert exc.value.code == "quota_exceeded"

    # Release reservasi pending → slot bebas kembali.
    services.release_reservation(first)
    second = services.reserve(tenant_a.id, "routers")
    assert second.state == "pending"

    # Commit dalam transaksi yang sama dengan materialisasi router (SUB-02).
    with tenant_scope(tenant_a.id):
        Router.objects.create(tenant_id=tenant_a.id, display_name="R1", router_code="rtr-1")
        services.commit_reservation(second)
    with pytest.raises(ApiError):
        services.reserve(tenant_a.id, "routers")


def test_draft_cap_formula():
    from domains.subscriptions.services import draft_cap

    assert draft_cap(50) == 13  # max(10, ceil(0.25*50)) = 13
    assert draft_cap(8) == 10  # min draft_min
    assert draft_cap(100000) == 500  # max draft_max
    assert draft_cap(None) == 500  # unlimited → max


def test_payment_proof_upload_pipeline(auth_client, tenant_a, db, tmp_path):
    from domains.subscriptions.models import PlanVersion, SaaSInvoice
    from django.utils import timezone
    import datetime

    session = auth_client.session
    session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()
    from domains.common.tenant_context import tenant_scope

    gold = PlanVersion.objects.filter(code="gold").first()
    with tenant_scope(tenant_a.id):
        invoice = SaaSInvoice.objects.create(
            tenant_id=tenant_a.id,
            plan=gold,
            term_months=1,
            amount=gold.monthly_price,
            period_start=datetime.date.today(),
            period_end=datetime.date.today() + datetime.timedelta(days=30),
            due_at=timezone.now(),
        )
    png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
    resp = auth_client.post(
        f"/api/v1/tenants/{tenant_a.id}/saas-invoices/{invoice.id}/payment-submissions",
        {"file_b64": png, "mime": "image/png", "file_name": "bukti.png"},
        headers={"Idempotency-Key": "proof-1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["state"] == "submitted"

    # MIME dusta ditolak: klaim PDF tapi isi PNG.
    resp = auth_client.post(
        f"/api/v1/tenants/{tenant_a.id}/saas-invoices/{invoice.id}/payment-submissions",
        {"file_b64": png, "mime": "application/pdf"},
        headers={"Idempotency-Key": "proof-2"},
    )
    # PDF klaim diizinkan tapi magic bytes PNG → sniff PNG, klaim pdf tidak cocok magic → ditolak
    assert resp.status_code == 422

    # Berkas terlalu besar ditolak (5 MiB).
    big = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 10)).decode()
    resp = auth_client.post(
        f"/api/v1/tenants/{tenant_a.id}/saas-invoices/{invoice.id}/payment-submissions",
        {"file_b64": big, "mime": "image/png"},
        headers={"Idempotency-Key": "proof-3"},
    )
    assert resp.status_code == 422

    # Path tersimpan opaque (bukan nama asli) — dibaca dalam konteks tenant.
    from domains.common.tenant_context import tenant_scope
    from domains.subscriptions.models import PaymentSubmission

    with tenant_scope(tenant_a.id):
        sub = PaymentSubmission.objects.get(id=data["submission_id"])
    assert "bukti" not in sub.proof_path and "/" in sub.proof_path
