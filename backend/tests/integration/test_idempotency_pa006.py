"""Tes integrasi PA-006 — HTTP idempotency aman terhadap scope dan race.

Matriks acceptance packet task/0010, diuji pada PostgreSQL nyata melalui
peran runtime non-superuser mtx_app (FORCE RLS berlaku pada tabel tenant):

Boundary HTTP (klien terautentikasi independen):
- Same identity/key/body → SATU aksi logis; replay respons logis sama.
- Same key beda body → 409 idempotency_conflict tanpa efek kedua.
- Beda principal / tenant / platform / operation / resource → respons dan
  aksi tidak tertukar; business uniqueness tetap berlaku.
- UUID alias (huruf besar) → scope canonical sama; malformed → 422.
- SaaS proof invoice A vs B dengan key/body sama → target B tidak
  memperoleh submission/respons A.
- Platform operator berpindah active tenant → scope platform tidak bergeser.
- Permission/sensitive step-up tidak sah saat replay → tidak membocorkan
  respons cache, aksi tidak dijalankan.

Protokol konkuren (interleaving dipaksa + lock observation pg_stat_activity,
dua koneksi PostgreSQL nyata dengan PID berbeda):
- Same-key same-body bersamaan → satu efek; yang kalah menunggu lalu
  MEREPLAY respons (bukan 409 permanen, bukan duplicate write/500).
- Same-key beda body bersamaan → 409 tanpa efek kedua.
- Keputusan platform konkuren → replay 204; efek keputusan tepat satu.
- 8 thread same-key → tanpa unique-violation 500.

Kegagalan/pemulihan:
- Gagal sebelum DB commit → klaim+efek ter-rollbalik konsisten; retry
  memakai key semula mengeksekusi ulang dengan bersih.
- Record terkomit tanpa respons (crash setelah commit domain sebelum
  respons tersimpan pada protokol lama) → ditolak aman tanpa eksekusi
  ulang buta; rekonsiliasi lalu replay.

TTL/legacy:
- Record kedaluwarsa terhapus → eksekusi ulang ditahan business
  uniqueness domain (external_ref unik), bukan duplikat diam-diam.
- Record legacy (backfill migrasi 0004) hanya mereplay untuk principal
  dan target canonical yang sama.
- Migrasi 0004: backfill canonical + dedupe alias + purge klaim tanpa
  respons/bermacam; constraint identitas dipasang.
"""
from __future__ import annotations

import base64
import threading
import time
import uuid as _uuid
from types import SimpleNamespace

import pytest

from domains.common.envelope import ApiError
from domains.identity.models import User
from domains.jobs.models import IdempotencyKey
from domains.subscriptions import services as sub_services
from domains.subscriptions.models import PaymentSubmission, PlanVersion, SaaSInvoice
from domains.tenancy.models import Membership, Role, Tenant

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(
        transaction=True,
        available_apps=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "domains.tenancy",
            "domains.identity",
            "domains.network",
            "domains.customers",
            "domains.subscriptions",
            "domains.billing",
            "domains.audit",
            "domains.jobs",
        ],
    ),
]

JOIN_TIMEOUT_S = 90
REAUTH_FAR_FUTURE = "2099-01-01T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _plans_available():
    """Flush transactional (available_apps) memotong tabel subscriptions —
    termasuk katalog PlanVersion yang di-seed sekali per sesi; re-seed
    idempoten sebelum tiap tes supaya katalog selalu tersedia."""
    sub_services.seed_plans()
    yield


# ---------------------------------------------------------------------------
# Helper setup (ter-commit; klien terautentikasi independen per pengguna)
# ---------------------------------------------------------------------------


def _world(namespace: str, *, extra_member=False) -> SimpleNamespace:
    """Tenant + owner (Role.OWNER: subscription.manage + payments.verify)."""
    tenant = Tenant.objects.create(display_name=f"PA006 {namespace}", namespace=namespace)
    owner = User.objects.create_user(
        email=f"owner-{namespace}@test.local",
        full_name=f"Owner {namespace}",
        password="test-password-1234567890",
        is_active=True,
    )
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    from domains.common.tenant_context import tenant_scope

    with tenant_scope(tenant.id):
        sub_services.ensure_free_subscription(tenant)
    world = SimpleNamespace(tenant=tenant, owner=owner)
    if extra_member:
        member = User.objects.create_user(
            email=f"member-{namespace}@test.local",
            full_name=f"Member {namespace}",
            password="test-password-1234567890",
            is_active=True,
        )
        Membership.objects.create(user=member, tenant=tenant, role=Role.OWNER)
        world.member = member
    return world


def _client_for(user, tenant_id=None, *, reauth_until=None):
    """Klien HTTP terautentikasi independen (sesi + csrf seperti SPA)."""
    from tests.conftest import CsrfAPIClient

    client = CsrfAPIClient(enforce_csrf_checks=False)
    client.get("/api/v1/auth/session")
    client.force_login(user)
    session = client.session
    session["auth_at"] = time.time()
    if tenant_id is not None:
        session["active_tenant_id"] = str(tenant_id)
    if reauth_until is not None:
        session["reauth_until"] = reauth_until
    session.save()
    return client


def _platform_admin(email="platform-pa006@test.local") -> User:
    admin = User.objects.create_user(
        email=email, full_name="Admin Platform PA006",
        password="test-password-1234567890", is_active=True,
    )
    admin.platform_admin = True
    admin.save(update_fields=["platform_admin"])
    return admin


def _make_invoice(world, *, plan_code="gold") -> SaaSInvoice:
    from domains.common.tenant_context import tenant_scope

    gold = PlanVersion.objects.filter(code=plan_code).first()
    import datetime
    from django.utils import timezone

    with tenant_scope(world.tenant.id):
        return SaaSInvoice.objects.create(
            tenant_id=world.tenant.id,
            plan=gold,
            term_months=1,
            amount=gold.monthly_price,
            period_start=datetime.date.today(),
            period_end=datetime.date.today() + datetime.timedelta(days=30),
            due_at=timezone.now(),
        )


def _make_platform_submission(world) -> PaymentSubmission:
    from domains.common.tenant_context import tenant_scope

    with tenant_scope(world.tenant.id):
        invoice, _ = sub_services.create_quotation(world.tenant.id, "silver", "monthly")
        return PaymentSubmission.objects.create(
            tenant_id=world.tenant.id,
            invoice=invoice,
            amount=invoice.amount,
            proof_path="payment-proofs/pa006",
            proof_mime="image/png",
            proof_size=1024,
            submitted_by=world.owner,
        )


_PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"PA006-PROOF" * 6).decode()
_PROOF_BODY = {"file_b64": _PNG_B64, "mime": "image/png", "file_name": "bukti.png"}


def _idem_count(**filters) -> int:
    return IdempotencyKey.objects.filter(**filters).count()


def _count_in_tenant(model, tenant_id, **filters) -> int:
    """Hitung baris tabel tenant-RLS dalam konteks scope yang sah."""
    from domains.common.tenant_context import tenant_scope

    with tenant_scope(tenant_id):
        return model.objects.filter(tenant_id=tenant_id, **filters).count()


def _body_hash_of(body) -> str:
    from domains.common.idempotency import _body_hash

    return _body_hash(body)


# ---------------------------------------------------------------------------
# A. Boundary HTTP — scope identitas lengkap
# ---------------------------------------------------------------------------


class TestScopeBoundaries:
    def test_same_identity_replay_single_effect(self):
        world = _world("rtrw-pa000001")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        body = {"plan_code": "gold", "term": "monthly"}
        headers = {"Idempotency-Key": "pa006-scope-1"}

        r1 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r1.status_code == 201
        r2 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r2.status_code == 201
        assert r2.json() == r1.json()

        # Satu aksi logis: invoice tepat satu; record identitas canonical.
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
        assert _idem_count(operation="quotation", idem_key="pa006-scope-1") == 1
        rec = IdempotencyKey.objects.get(operation="quotation", idem_key="pa006-scope-1")
        assert rec.principal == str(world.owner.id)
        assert rec.tenant_scope == str(world.tenant.id)
        assert rec.resource == ""
        assert rec.response_status == 201

    def test_same_key_different_body_conflict_no_second_effect(self):
        world = _world("rtrw-pa000002")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        headers = {"Idempotency-Key": "pa006-scope-2"}
        body = {"plan_code": "gold", "term": "monthly"}

        r1 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r1.status_code == 201
        r2 = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            {"plan_code": "silver", "term": "monthly"},
            headers=headers,
        )
        assert r2.status_code == 409
        assert r2.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

    def test_different_principal_same_key_no_response_leak(self):
        world = _world("rtrw-pa000003", extra_member=True)
        ca = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        cb = _client_for(world.member, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        headers = {"Idempotency-Key": "pa006-scope-3"}
        body = {"plan_code": "gold", "term": "monthly"}

        ra = ca.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert ra.status_code == 201
        rb = cb.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert rb.status_code == 201

        # Aksi logis per principal: 2 invoice, 2 record, respons tidak tertukar.
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 2
        assert _idem_count(operation="quotation", idem_key="pa006-scope-3") == 2
        assert IdempotencyKey.objects.filter(
            operation="quotation", idem_key="pa006-scope-3", principal=str(world.owner.id)
        ).exists()
        assert IdempotencyKey.objects.filter(
            operation="quotation", idem_key="pa006-scope-3", principal=str(world.member.id)
        ).exists()
        # Replay masing-masing tetap mengembalikan respons miliknya.
        ra2 = ca.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        rb2 = cb.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert ra2.json()["invoice_id"] == ra.json()["invoice_id"]
        assert rb2.json()["invoice_id"] == rb.json()["invoice_id"]
        assert ra2.json()["invoice_id"] != rb2.json()["invoice_id"]

    def test_different_tenant_same_key_no_cross_response(self):
        wa = _world("rtrw-pa000004")
        wb = _world("rtrw-pa000005")
        ca = _client_for(wa.owner, wa.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        cb = _client_for(wb.owner, wb.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        headers = {"Idempotency-Key": "pa006-scope-4"}
        body = {"plan_code": "gold", "term": "monthly"}

        ra = ca.post(f"/api/v1/tenants/{wa.tenant.id}/quotations", body, headers=headers)
        rb = cb.post(f"/api/v1/tenants/{wb.tenant.id}/quotations", body, headers=headers)
        assert ra.status_code == 201 and rb.status_code == 201
        assert _count_in_tenant(SaaSInvoice, wa.tenant.id) == 1
        assert _count_in_tenant(SaaSInvoice, wb.tenant.id) == 1
        # Replay lintas tenant tidak saling membocorkan respons.
        rb2 = cb.post(f"/api/v1/tenants/{wb.tenant.id}/quotations", body, headers=headers)
        assert rb2.json()["invoice_id"] == rb.json()["invoice_id"]
        assert rb2.json()["invoice_id"] != ra.json()["invoice_id"]

    def test_platform_scope_disjoint_from_tenant_and_stable_across_active_tenant(self):
        world = _world("rtrw-pa000006")
        admin = _platform_admin()
        platform = _client_for(admin)
        tenant_client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        submission = _make_platform_submission(world)
        invoice_for_tenant = _make_invoice(world)
        key = "pa006-scope-5"

        # Operasi tenant (payment_submission) dengan key K → 201 milik tenant.
        rs = tenant_client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice_for_tenant.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": key},
        )
        assert rs.status_code == 201

        # Operasi platform dengan key K yang sama → scope berbeda → aksi terpisah.
        ra = platform.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": key},
        )
        assert ra.status_code == 204
        assert _idem_count(idem_key=key) == 2
        assert IdempotencyKey.objects.get(
            idem_key=key, tenant_scope=str(world.tenant.id), operation="payment_submission"
        ).response_status == 201
        prec = IdempotencyKey.objects.get(idem_key=key, tenant_scope="platform")
        assert prec.operation == "platform_submission_approve"
        assert prec.response_status == 204

        # Operator berpindah active tenant → scope platform TIDAK bergeser:
        # replay tetap respons yang sama, tanpa efek keputusan baru.
        from domains.common.tenant_context import tenant_scope
        from domains.jobs.models import OutboxEvent

        other_tenant = Tenant.objects.create(display_name="Lain", namespace="rtrw-pa000007")
        session = platform.session
        session["active_tenant_id"] = str(other_tenant.id)
        session.save()
        ra2 = platform.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": key},
        )
        assert ra2.status_code == 204
        assert _idem_count(idem_key=key, tenant_scope="platform") == 1
        from domains.common.tenant_context import tenant_scope as _ts

        with _ts(world.tenant.id):
            submission.refresh_from_db()
        assert submission.state == PaymentSubmission.State.APPROVED
        # Efek keputusan tepat satu (outbox dedup + satu event aktivasi).
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 1
        assert OutboxEvent.objects.filter(event_type="subscription.activated").count() == 1

    def test_uuid_alias_and_malformed_resource_identity(self):
        world = _world("rtrw-pa000008")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        invoice = _make_invoice(world)
        key = "pa006-scope-6"

        # Ejaan alias huruf BESAR (tenant + invoice) → identitas canonical sama.
        r1 = client.post(
            f"/api/v1/tenants/{str(world.tenant.id).upper()}/saas-invoices/{str(invoice.id).upper()}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": key},
        )
        assert r1.status_code == 201
        # Ejaan lowercase + key sama → replay, bukan aksi baru.
        r2 = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": key},
        )
        assert r2.status_code == 201
        assert r2.json() == r1.json()
        assert _count_in_tenant(PaymentSubmission, world.tenant.id) == 1
        assert _idem_count(operation="payment_submission", idem_key=key) == 1

        # Resource salah bentuk → 422 sebelum view; tanpa klaim/efek.
        r3 = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/bukan-uuid/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "pa006-scope-6b"},
        )
        assert r3.status_code == 422
        assert r3.json()["code"] == "validation_error"
        assert _idem_count(idem_key="pa006-scope-6b") == 0
        # CATATAN: tenant_id salah bentuk pada URL (gate membership §5,
        # resolve_membership) menimbulkan ValidationError ORM → 500 — defek
        # insidental PRA-ADA di luar scope PA-006 (bukan jalur protokol
        # idempotency); dicatat sebagai follow-up berbukti pada laporan.

    def test_saas_proof_invoice_a_vs_b_same_key_body(self):
        world = _world("rtrw-pa000009")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        inv_a, inv_b = _make_invoice(world), _make_invoice(world)
        key = "pa006-scope-7"

        ra = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{inv_a.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": key},
        )
        rb = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{inv_b.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": key},
        )
        assert ra.status_code == 201 and rb.status_code == 201
        # Target B tidak memperoleh submission/respons A (resource beda).
        assert ra.json()["submission_id"] != rb.json()["submission_id"]
        assert _idem_count(operation="payment_submission", idem_key=key) == 2
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=inv_a.id) == 1
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=inv_b.id) == 1
        # Replay masing-masing target tetap miliknya.
        ra2 = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{inv_a.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": key},
        )
        assert ra2.json()["submission_id"] == ra.json()["submission_id"]

    def test_replay_requires_current_permission_and_step_up(self):
        world = _world("rtrw-pa000010")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        body = {"plan_code": "gold", "term": "monthly"}
        headers = {"Idempotency-Key": "pa006-scope-8"}

        r1 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r1.status_code == 201

        # Step-up kedaluwarsa saat replay → 403, respons cache TIDAK bocor.
        session = client.session
        session["reauth_until"] = "2020-01-01T00:00:00+00:00"
        session.save()
        r2 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r2.status_code == 403
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

        # Reauth aktif kembali → replay mengembalikan respons logis semula.
        session = client.session
        session["reauth_until"] = REAUTH_FAR_FUTURE
        session.save()
        r3 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r3.status_code == 201
        assert r3.json() == r1.json()
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

        # Membership dicabut saat replay → tidak membocorkan respons cache
        # (404 generik sesuai §5 — non-milik tidak membocorkan keberadaan).
        from django.utils import timezone as _tz

        Membership.objects.filter(user=world.owner, tenant=world.tenant).update(
            revoked_at=_tz.now()
        )
        r4 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r4.status_code == 404


# ---------------------------------------------------------------------------
# B. Kegagalan dan pemulihan
# ---------------------------------------------------------------------------


class TestFailureAndRecovery:
    def test_fail_before_db_commit_rolls_back_claim_then_retry_succeeds(self):
        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent

        world = _world("rtrw-pa000011")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        headers = {"Idempotency-Key": "pa006-fail-1"}

        # Gagal validasi domain SEBELUM commit → klaim + efek ter-rollbalik.
        r_bad = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            {"plan_code": "tidak-ada", "term": "monthly"},
            headers=headers,
        )
        assert r_bad.status_code == 422
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 0
        assert _idem_count(idem_key="pa006-fail-1") == 0
        assert _count_in_tenant(AuditEvent, world.tenant.id) == 0
        assert _count_in_tenant(OutboxEvent, world.tenant.id) == 0

        # Retry key semula (§5 retry hasil tak pasti) → eksekusi bersih.
        r_ok = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            {"plan_code": "gold", "term": "monthly"},
            headers=headers,
        )
        assert r_ok.status_code == 201
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
        assert _idem_count(idem_key="pa006-fail-1") == 1

    def test_stuck_claim_without_response_no_blind_reexecution(self):
        world = _world("rtrw-pa000012")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        body = {"plan_code": "gold", "term": "monthly"}
        headers = {"Idempotency-Key": "pa006-fail-2"}

        # Aksi pertama sukses (efek + respons terkomit).
        r1 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r1.status_code == 201
        invoice_id = r1.json()["invoice_id"]

        # Simulasi crash setelah commit domain SEBELUM respons tersimpan
        # (keadaan klaim protokol lama): respons dibuang dari record.
        IdempotencyKey.objects.filter(idem_key="pa006-fail-2").update(
            response_status=None, response_body=None
        )
        r2 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        # Tidak blind-eksekusi efek kedua: 409 aman, invoice tetap satu.
        assert r2.status_code == 409
        assert r2.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

        # Rekonsiliasi bertenaga (ops memulihkan respons sesuai outcome) →
        # replay kembali memberikan hasil aksi yang sama.
        IdempotencyKey.objects.filter(idem_key="pa006-fail-2").update(
            response_status=201, response_body={"quotation_id": invoice_id, "invoice_id": invoice_id, "amount": "1500000.00"}
        )
        r3 = client.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers=headers)
        assert r3.status_code == 201
        assert r3.json()["invoice_id"] == invoice_id
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

    def test_ttl_expiry_reexecute_blocked_by_business_uniqueness(self):
        world = _world("rtrw-pa000013")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        headers = {"Idempotency-Key": "pa006-fail-3"}
        body = {"method": "cash", "amount": "150000", "external_ref": "BANK-PA006-001"}

        r1 = client.post(f"/api/v1/tenants/{world.tenant.id}/payments", body, headers=headers)
        assert r1.status_code == 201
        from domains.billing.models import InternetPayment

        payment_id = r1.json()["id"]

        # TTL habis: record terhapus → replay mengeksekusi ulang, tetapi
        # business uniqueness domain (external_ref unik tenant) menahan
        # duplikasi → 409 domain, bukan duplicate write.
        IdempotencyKey.objects.filter(idem_key="pa006-fail-3").delete()
        r2 = client.post(f"/api/v1/tenants/{world.tenant.id}/payments", body, headers=headers)
        assert r2.status_code == 409
        assert r2.json()["code"] == "conflict"
        assert _count_in_tenant(InternetPayment, world.tenant.id) == 1


# ---------------------------------------------------------------------------
# C. Konkurensi — interleaving dipaksa + observasi lock
# ---------------------------------------------------------------------------


def _pg_pid() -> int:
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        return cur.fetchone()[0]


def _observer_conn():
    """Koneksi pengamat psycopg (peran runtime yang sama, DB uji sama).

    Observasi pg_stat_activity lintas sesi dari koneksi raw psycopg stabil
    pada klaster uji ini (koneksi Django main menunjukkan flakiness
    visibilitas lintas-sesi yang tidak dapat diandalkan untuk bukti).
    """
    import psycopg
    from django.db import connection as dj_conn

    with dj_conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        dbname = cur.fetchone()[0]
    return psycopg.connect(
        f"postgresql://mtx_app@127.0.0.1:55432/{dbname}", autocommit=True
    )


def _wait_backend_lock_wait(observer, pid: int, *, deadline_s: float = 30.0) -> bool:
    """Polling pg_stat_activity (via pengamat raw) — deteksi KONDISI terblokir."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        cur = observer.cursor()
        cur.execute(
            "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", (pid,)
        )
        row = cur.fetchone()
        cur.close()
        if row is not None and row[0] == "Lock":
            return True
        time.sleep(0.05)
    return False


def _fake_request(user, *, data=None, idem_key=None):
    """Request minimal untuk pemanggilan langsung method view terdekorasi."""
    return SimpleNamespace(
        headers={"Idempotency-Key": idem_key} if idem_key else {},
        data=data or {},
        user=user,
        session={},
    )


def _thread(fn):
    t = threading.Thread(target=fn)
    t.start()
    return t


def _join(threads):
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT_S)


class TestConcurrentClaimReplay:
    def test_concurrent_same_identity_waits_then_replays_single_effect(self):
        """Same identity/key/body bersamaan: pemilik klaim menunggu kunci
        subscription (dipaksa), penantang memblok pada INSERT unik (diamati
        pg_stat_activity); setelah selesai, penantang MEREPLAY respons —
        bukan 409 permanen, bukan duplicate write/500."""
        world = _world("rtrw-pa000014")
        body = {"plan_code": "gold", "term": "monthly"}
        key = "pa006-race-1"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import Subscription

        def run(tag):
            from django.db import connection as conn

            try:
                pids[tag] = _pg_pid()
                from domains.subscriptions.views import QuotationView

                resp = QuotationView().post(
                    _fake_request(world.owner, data=body, idem_key=key),
                    tenant_id=str(world.tenant.id),
                )
                results[tag] = {"status": resp.status_code, "data": resp.data}
            except ApiError as exc:
                results[tag] = {"api_error": exc.code, "status": exc.status_code}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        # Kunci baris subscription dipegang main thread → memaksa interleaving.
        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            Subscription.objects.select_for_update().get(tenant=world.tenant.id)

            ta = _thread(lambda: run("A"))
            # Tunggu A benar-benar TERBLOKIR (pid thread sendiri; observasi
            # kondisi via pengamat raw — pola PA-001, bukan pengatur race).
            deadline = time.monotonic() + 30
            a_pid = None
            while time.monotonic() < deadline:
                a_pid = pids.get("A")
                if a_pid is not None and _wait_backend_lock_wait(observer, a_pid, deadline_s=1.0):
                    break
                time.sleep(0.05)
            assert a_pid is not None, "thread A belum teramati menunggu lock"

            tb = _thread(lambda: run("B"))
            # B memblok pada klaim INSERT A (speculative unique wait).
            deadline = time.monotonic() + 30
            b_pid = None
            while time.monotonic() < deadline:
                b_pid = pids.get("B")
                if b_pid is not None and _wait_backend_lock_wait(observer, b_pid, deadline_s=1.0):
                    break
                time.sleep(0.05)
            assert b_pid is not None, "thread B belum teramati menunggu pada klaim INSERT"
        finally:
            scope.__exit__(None, None, None)  # lepaskan kunci subscription
            observer.close()

        _join([ta, tb])
        assert pids["A"] != pids["B"]

        # Satu aksi logis; penantang mereplay respons identik; tanpa exception.
        assert "exception" not in results.get("A", {}), results
        assert "exception" not in results.get("B", {}), results
        assert results["A"]["status"] == 201
        assert results["B"]["status"] == 201
        assert results["B"]["data"] == results["A"]["data"]
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
        assert _idem_count(operation="quotation", idem_key=key) == 1

    def test_concurrent_same_key_different_body_conflict(self):
        world = _world("rtrw-pa000015")
        key = "pa006-race-2"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import Subscription

        def run(tag, body):
            from django.db import connection as conn

            try:
                pids[tag] = _pg_pid()
                from domains.subscriptions.views import QuotationView

                resp = QuotationView().post(
                    _fake_request(world.owner, data=body, idem_key=key),
                    tenant_id=str(world.tenant.id),
                )
                results[tag] = {"status": resp.status_code, "data": resp.data}
            except ApiError as exc:
                results[tag] = {"api_error": exc.code, "status": exc.status_code}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            Subscription.objects.select_for_update().get(tenant=world.tenant.id)
            ta = _thread(lambda: run("A", {"plan_code": "gold", "term": "monthly"}))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if pids.get("A") and _wait_backend_lock_wait(observer, pids["A"], deadline_s=1.0):
                    break
                time.sleep(0.05)
            tb = _thread(lambda: run("B", {"plan_code": "silver", "term": "monthly"}))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if pids.get("B") and _wait_backend_lock_wait(observer, pids["B"], deadline_s=1.0):
                    break
                time.sleep(0.05)
        finally:
            scope.__exit__(None, None, None)
            observer.close()

        _join([ta, tb])
        statuses = sorted(r.get("status") for r in results.values())
        assert statuses == [201, 409]
        loser = results["A"] if results["A"]["status"] == 409 else results["B"]
        assert loser["api_error"] == "idempotency_conflict"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

    def test_concurrent_platform_decision_replay_204_single_effect(self):
        world = _world("rtrw-pa000016")
        admin = _platform_admin("platform-race-pa006@test.local")
        submission = _make_platform_submission(world)
        key = "pa006-race-3"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope

        def run(tag):
            from django.db import connection as conn

            try:
                pids[tag] = _pg_pid()
                from domains.subscriptions.views import PlatformSubmissionApproveView

                resp = PlatformSubmissionApproveView().post(
                    _fake_request(admin, idem_key=key),
                    submission_id=str(submission.id),
                )
                results[tag] = {"status": resp.status_code, "data": resp.data}
            except ApiError as exc:
                results[tag] = {"api_error": exc.code, "status": exc.status_code}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        # Paksa interleaving: pegang kunci baris submission (RLS → dalam scope).
        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            PaymentSubmission.objects.select_for_update().get(id=submission.id)
            ta = _thread(lambda: run("A"))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if pids.get("A") and _wait_backend_lock_wait(observer, pids["A"], deadline_s=1.0):
                    break
                time.sleep(0.05)
            tb = _thread(lambda: run("B"))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if pids.get("B") and _wait_backend_lock_wait(observer, pids["B"], deadline_s=1.0):
                    break
                time.sleep(0.05)
        finally:
            scope.__exit__(None, None, None)
            observer.close()

        _join([ta, tb])
        # Kedua 204: satu keputusan, satu replay; tanpa 500/exception.
        assert results["A"]["status"] == 204, results
        assert results["B"]["status"] == 204, results

        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent
        from domains.subscriptions.models import PlatformPaymentSourceEvent, Subscription

        with tenant_scope(world.tenant.id):
            submission.refresh_from_db()
        assert submission.state == PaymentSubmission.State.APPROVED
        assert _count_in_tenant(
            AuditEvent, world.tenant.id, action_code="payment_submission.approve",
            target_id=submission.id,
        ) == 1
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 1
        assert _count_in_tenant(
            PlatformPaymentSourceEvent, world.tenant.id, submission=submission
        ) == 1
        sub = None
        with tenant_scope(world.tenant.id):
            sub = Subscription.objects.get(tenant_id=world.tenant.id)
        assert sub.state == Subscription.State.ACTIVE
        assert sub.period_index == 1

    def test_eight_threads_same_key_no_unique_violation_500(self):
        world = _world("rtrw-pa000017")
        key = "pa006-race-4"
        body = {"plan_code": "gold", "term": "monthly"}
        results: dict[str, dict] = {}
        barrier = threading.Barrier(8, timeout=30)

        def run(tag):
            from django.db import connection as conn

            try:
                barrier.wait()
                from domains.subscriptions.views import QuotationView

                resp = QuotationView().post(
                    _fake_request(world.owner, data=body, idem_key=key),
                    tenant_id=str(world.tenant.id),
                )
                results[tag] = {"status": resp.status_code, "data": resp.data}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        threads = [_thread(lambda t=f"T{i}": run(t)) for i in range(8)]
        _join(threads)

        for tag, res in results.items():
            assert "exception" not in res, (tag, res)
            assert res["status"] == 201
        datas = {str(sorted(r["data"].items())) for r in results.values()}
        assert len(datas) == 1  # semua mereplay aksi logis yang sama
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
        assert _idem_count(operation="quotation", idem_key=key) == 1

    def test_concurrent_different_principal_same_key_both_execute(self):
        world = _world("rtrw-pa000018", extra_member=True)
        key = "pa006-race-5"
        body = {"plan_code": "gold", "term": "monthly"}
        results: dict[str, dict] = {}
        barrier = threading.Barrier(2, timeout=30)

        def run(tag, user):
            from django.db import connection as conn

            try:
                barrier.wait()
                from domains.subscriptions.views import QuotationView

                resp = QuotationView().post(
                    _fake_request(user, data=body, idem_key=key),
                    tenant_id=str(world.tenant.id),
                )
                results[tag] = {"status": resp.status_code, "data": resp.data}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        threads = [
            _thread(lambda: run("A", world.owner)),
            _thread(lambda: run("B", world.member)),
        ]
        _join(threads)
        for res in results.values():
            assert "exception" not in res
            assert res["status"] == 201
        # Principal beda → dua aksi logis terpisah (bukan saling mereplay).
        assert results["A"]["data"]["invoice_id"] != results["B"]["data"]["invoice_id"]
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 2
        assert _idem_count(operation="quotation", idem_key=key) == 2


# ---------------------------------------------------------------------------
# D. Legacy record & migrasi 0004
# ---------------------------------------------------------------------------


class TestLegacyAndMigration:
    def test_legacy_record_replays_only_same_principal_and_target(self):
        world = _world("rtrw-pa000019", extra_member=True)
        ca = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        cb = _client_for(world.member, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        body = {"plan_code": "gold", "term": "monthly"}
        key = "pa006-legacy-1"

        # Record "legacy" (schema baru, backfill dari scope lama) milik owner.
        IdempotencyKey.objects.create(
            principal=str(world.owner.id),
            tenant_scope=str(world.tenant.id),
            operation="quotation",
            resource="",
            idem_key=key,
            body_hash=_body_hash_of(body),
            response_status=201,
            response_body={"quotation_id": "legacy-1", "invoice_id": "legacy-1", "amount": "1500000.00"},
        )

        # Replay oleh principal yang sama → respons legacy dikembalikan,
        # tanpa mengeksekusi invoice baru.
        ra = ca.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers={"Idempotency-Key": key})
        assert ra.status_code == 201
        assert ra.json()["invoice_id"] == "legacy-1"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 0

        # Principal berbeda memakai key sama → aksi BARU miliknya (tidak
        # memperoleh respons legacy), record tetap 2 dengan principal beda.
        rb = cb.post(f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers={"Idempotency-Key": key})
        assert rb.status_code == 201
        assert rb.json()["invoice_id"] != "legacy-1"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
        assert _idem_count(operation="quotation", idem_key=key) == 2

    def test_migration_0004_backfill_canonical_dedupe_and_purge(self):
        """Migrasi jobs.0004: backfill kolom identitas canonical dari scope
        lama, dedupe alias, purge klaim tanpa respons / scope salah bentuk,
        pasang uq_idem_identity, hapus kolom scope. Replay melalui protokol
        baru terhadap record hasil backfill terbukti."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = [m for m, _ in executor.migration_plan([("jobs", "0003_alter_job_kind")])]
        assert plan, "harus ada langkah rollback ke 0003"

        # Rollback 0004 pada tabel kosong (re-add kolom NOT NULL aman).
        IdempotencyKey.objects.all().delete()
        executor.migrate([("jobs", "0003_alter_job_kind")])

        apps_old = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        IdemOld = apps_old.get_model("jobs", "IdempotencyKey")

        world = _world("rtrw-pa000020")
        body = {"plan_code": "gold", "term": "monthly"}
        body_h = _body_hash_of(body)
        response_old = {"quotation_id": "aaa-legacy", "invoice_id": "aaa-legacy", "amount": "1500000.00"}
        response_latest = {"quotation_id": "bbb-legacy", "invoice_id": "bbb-legacy", "amount": "1500000.00"}
        import datetime as _dt
        from django.utils import timezone as _tz

        now = _tz.now()
        # 1) legacy canonical + respons → dipertahankan.
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope=f"quotation:{world.tenant.id}:",
            idem_key="mig-keep",
            body_hash=body_h,
            response_status=201,
            response_body=response_old,
            created_at=now - _dt.timedelta(days=3),
        )
        # 2) duplikat alias huruf besar, LEBIH BARU, sama identitas canonical
        #    dengan (1) → dedupe mempertahankan yang terbaru, hapus yang lama.
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope=f"quotation:{str(world.tenant.id).upper()}:",
            idem_key="mig-keep",
            body_hash=body_h,
            response_status=201,
            response_body=response_latest,
            created_at=now - _dt.timedelta(days=1),
        )
        # 3) klaim tanpa respons (protokol lama) → dihapus.
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope=f"quotation:{world.tenant.id}:",
            idem_key="mig-stale",
            body_hash=body_h,
            created_at=now - _dt.timedelta(days=2),
        )
        # 4) scope salah bentuk → dihapus.
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope="tidak-terurai",
            idem_key="mig-bad",
            body_hash=body_h,
            response_status=201,
            created_at=now - _dt.timedelta(days=2),
        )
        # 5) resource opaque sah (identity_conflict_resolve group_id sha256[:16])
        #    → DIPERTAHANKAN apa adanya (cermin resource_uuid=False), respons
        #    tetap bisa direplay pasca-migrasi.
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope=f"identity_conflict_resolve:{world.tenant.id}:0f1e2d3c4b5a6978",
            idem_key="mig-opaque",
            body_hash=_body_hash_of({"resolution": "merge"}),
            response_status=204,
            created_at=now - _dt.timedelta(days=2),
        )

        # Executor segar diperlukan: loader executor pertama masih mem-cache
        # status applied lama sehingga pemanggilan maju berikutnya no-op.
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0004_idempotency_identity")])

        assert IdempotencyKey.objects.filter(idem_key="mig-stale").count() == 0
        assert IdempotencyKey.objects.filter(idem_key="mig-bad").count() == 0
        kept = IdempotencyKey.objects.get(idem_key="mig-keep")
        assert kept.tenant_scope == str(world.tenant.id)  # alias terkanonikalisasi
        assert kept.operation == "quotation"
        assert kept.resource == ""
        # Resource opaque sah dipertahankan verbatim (tidak dipurge, tidak diubah).
        opaque = IdempotencyKey.objects.get(idem_key="mig-opaque")
        assert opaque.operation == "identity_conflict_resolve"
        assert opaque.resource == "0f1e2d3c4b5a6978"
        assert opaque.response_status == 204
        # Dedupe: record TERBARU (respons bbb) yang bertahan.
        assert kept.response_body == response_latest
        assert IdempotencyKey.objects.filter(idem_key="mig-keep").count() == 1

        with connection.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint WHERE conname IN "
                "('uq_idem_scope_key', 'uq_idem_identity')"
            )
            names = {row[0] for row in cur.fetchall()}
            cur.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_name = "
                "'jobs_idempotency_key' AND column_name = 'scope'"
            )
            scope_column_exists = cur.fetchone() is not None
        assert names == {"uq_idem_identity"}
        assert not scope_column_exists

        # Replay lewat protokol baru terhadap record backfill → respons legacy.
        ca = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        ra = ca.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            body, headers={"Idempotency-Key": "mig-keep"},
        )
        assert ra.status_code == 201
        assert ra.json() == response_latest
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 0

        # Principal berbeda tidak memperoleh respons legacy (target/principal salah).
        member = User.objects.create_user(
            email="member-mig@test.local", full_name="Member Migrasi",
            password="test-password-1234567890", is_active=True,
        )
        Membership.objects.create(user=member, tenant=world.tenant, role=Role.OWNER)
        cb = _client_for(member, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        rb = cb.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            body, headers={"Idempotency-Key": "mig-keep"},
        )
        assert rb.status_code == 201
        assert rb.json() != response_latest
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
