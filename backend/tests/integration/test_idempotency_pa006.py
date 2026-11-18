"""Tes integrasi PA-006 — HTTP idempotency aman terhadap scope dan race.

Matriks acceptance packet task/0010 + koreksi REV-1311-01/02/03 dan
REV-1411-04, diuji pada PostgreSQL nyata melalui peran runtime non-superuser
mtx_app (FORCE RLS berlaku pada tabel tenant):

Boundary HTTP (klien terautentikasi independen):
- Same identity/key/body → SATU aksi logis; replay respons logis sama.
- Same key beda body → 409 idempotency_conflict tanpa efek kedua.
- Beda principal / tenant / platform / operation / resource → respons dan
  aksi tidak tertukar; business uniqueness tetap berlaku.
- UUID alias (huruf besar/tanpa hyphen, URL maupun body ter-typed) → scope
  canonical sama; malformed → 422.
- SaaS proof invoice A vs B dengan key/body sama → target B tidak
  memperoleh submission/respons A (termasuk record legacy resource='').
- Platform operator berpindah active tenant → scope platform tidak bergeser.
- Permission/sensitive step-up tidak sah saat replay → tidak membocorkan
  respons cache, aksi tidak dijalankan.

Konkurensi HTTP nyata (REV-1411-04) — tiap thread memakai klien HTTP
terautentikasi SENDIRI melalui dispatch penuh (middleware, routing,
permission, outer tenant transaction). Interleaving DIPAKSA (kunci baris
domain dipegang thread utama) dan KONDISI TERBLOKIR DIASSERTI lewat
pg_stat_activity — observer gagal mengamati lock membuat tes GAGAL:
- Same-key same-body bersamaan → pemilik klaim menunggu kunci domain,
  penantang menunggu klaim INSERT unik; setelah selesai penantang MEREPLAY
  respons (bukan 409 permanen, bukan duplicate write/500).
- Same-key beda body bersamaan → 409 tanpa efek kedua.
- Keputusan platform konkuren → replay 204; efek keputusan tepat satu.
- 8 thread same-key → tanpa unique-violation 500.
- Takeover: kegagalan DISUNTIK setelah writes domain/audit/outbox sebelum
  respons dipersist → seluruh transaksi leader ter-rollbalik (klaim + efek
  + cache); penantang same-key yang menunggu mengambil alih dan mengeksekusi
  bersih → satu aksi logis terkomit.

Kegagalan/pemulihan:
- Gagal sebelum DB commit → klaim+efek ter-rollbalik konsisten; retry
  memakai key semula mengeksekusi ulang dengan bersih.
- Record terkomit tanpa respons (crash setelah commit domain sebelum respons
  tersimpan pada protokol lama) → ditolak aman tanpa eksekusi ulang buta;
  rekonsiliasi lalu replay.

Legacy/migrasi 0004 (REV-1311-01/02):
- Record legacy payment_submission resource='' → replay asli setelah
  replay_guard memverifikasi submission→invoice/tenant; target beda → 409.
- Record tanpa respons TIDAK dihapus migrasi; retry → 409 aman.
- Transisi aktual: schema main (0003) → record format lama → migrasi 0004
  nyata → retry HTTP → submission/keputusan semula, tanpa efek kedua.
- Operasi platform scope active-tenant lama → remap 'platform' → replay.
- identity_conflict_resolve: identitas menyertakan migration UUID; parent
  divalidasi sebelum replay; record group-only lama ditolak aman.
"""
from __future__ import annotations

import base64
import threading
import time
import uuid as _uuid
from types import SimpleNamespace
from unittest import mock

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


@pytest.fixture(autouse=True)
def _restore_latest_migrations():
    """Pulihkan state migrasi ke TERBARU setelah tiap tes (task0020 R4).

    Tes migrasi PA-006 (0003<->0004/0005) meninggalkan app jobs pada state
    historis tanpa pemulihan; kebocoran ini laten selama 0005 masih migrasi
    data-only (skema identik antar state). Migration additive task0020 R4
    (0006 writer receipt) mengubah skema, sehingga tanpa pemulihan tes
    berikutnya gagal pada kolom yang absen. Fixture ini TIDAK mengubah
    asersi mana pun — hanya mengembalikan state migrasi ke terbaru.
    """
    yield
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


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


def _client_for(user, tenant_id=None, *, reauth_until=None, raise_request_exception=True):
    """Klien HTTP terautentikasi independen (sesi + csrf seperti SPA).

    Aman dipakai per-thread: tiap thread membuat instansinya sendiri;
    permintaan melalui dispatch penuh (middleware + routing + permission +
    outer tenant transaction pada koneksi thread-lokal).

    CATATAN concurrency (REV-1411-04): Django menangkap exception request
    lewat signal global got_request_exception; dua klien yang overlap akan
    saling menulari exc_info. Untuk tes konkurensi yang mengandung request
    gagal (injeksi rollback), pakai raise_request_exception=False sehingga
    klien penantang tidak salah menaikkan exception milik leader — kegagalan
    leader dibuktikan lewat respons 500 + state DB.
    """
    from tests.conftest import CsrfAPIClient

    client = CsrfAPIClient(enforce_csrf_checks=False)
    client.raise_request_exception = raise_request_exception
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


def _make_platform_submission(world, *, state=PaymentSubmission.State.SUBMITTED) -> PaymentSubmission:
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
            state=state,
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


def _body_hash_legacy_of(body) -> str:
    from domains.common.idempotency import _body_hash_legacy

    return _body_hash_legacy(body)


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
# B. Kegagalan dan pemulihan (sekuensial)
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

        # TTL habis: record terhapus → replay mengeksekusi ulang, tetapi
        # business uniqueness domain (external_ref unik tenant) menahan
        # duplikasi → 409 domain, bukan duplicate write.
        IdempotencyKey.objects.filter(idem_key="pa006-fail-3").delete()
        r2 = client.post(f"/api/v1/tenants/{world.tenant.id}/payments", body, headers=headers)
        assert r2.status_code == 409
        assert r2.json()["code"] == "conflict"
        assert _count_in_tenant(InternetPayment, world.tenant.id) == 1


# ---------------------------------------------------------------------------
# C. Konkurensi HTTP nyata — interleaving dipaksa + observasi lock DIASSERTI
#    (REV-1411-04: tiap thread = klien HTTP terautentikasi sendiri melalui
#    dispatch penuh: middleware + routing + auth/permission + outer tenant
#    transaction pada koneksi thread-lokal yang terpisah)
# ---------------------------------------------------------------------------


def _pg_pid() -> int:
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        return cur.fetchone()[0]


def _observer_conn():
    """Koneksi pengamat psycopg dengan parameter koneksi Django aktif.

    Host/port/user/dbname diambil dari DATABASES (berlaku untuk sandbox
    user-space 55432 maupun service CI 5432 — bukan hardcode). Observasi
    pg_stat_activity lintas sesi dari koneksi psycopg stabil pada klaster
    uji ini (koneksi Django main menunjukkan flakiness visibilitas lintas
    sesi yang tidak dapat diandalkan untuk bukti).
    """
    import psycopg
    from django.db import connection as dj_conn

    params = dj_conn.get_connection_params()
    kwargs = {k: params[k] for k in ("host", "port", "dbname", "user", "password") if params.get(k)}
    return psycopg.connect(autocommit=True, **kwargs)


def _wait_pid(pids: dict, tag: str, *, deadline_s: float = 30.0) -> int:
    """Tunggu thread terdaftar PID koneksi PostgreSQL-nya; gagal = tes gagal."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        pid = pids.get(tag)
        if pid is not None:
            return pid
        time.sleep(0.02)
    raise AssertionError(f"thread {tag} tidak terdaftar PID koneksi dalam {deadline_s}s")


def _assert_lock_wait(observer, pid: int, *, context: str, deadline_s: float = 30.0) -> None:
    """ASSERT backend pid benar-benar TERBLOKIR menunggu lock.

    REV-1411-04: observer yang gagal mengamati kondisi terblokir harus
    membuat tes GAGAL — bukan sekadar break dan berharap race terjadi.
    """
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        cur = observer.cursor()
        cur.execute(
            "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", (pid,)
        )
        row = cur.fetchone()
        cur.close()
        if row is not None and row[0] == "Lock":
            return
        time.sleep(0.05)
    raise AssertionError(f"{context}: pid {pid} tidak teramati menunggu lock dalam {deadline_s}s")


def _response_data(response):
    """Payload JSON respons (204 tanpa isi → None)."""
    if response.status_code == 204 or not getattr(response, "content", b""):
        return None
    return response.json()


def _thread(fn):
    t = threading.Thread(target=fn)
    t.start()
    return t


def _join(threads):
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT_S)
        assert not t.is_alive(), f"thread {t.name} tidak selesai dalam {JOIN_TIMEOUT_S}s"


def _http_post_runner(tag, *, user, tenant_id, url, body, key, results, pids,
                      raise_request_exception=True):
    """Runner thread: klien HTTP terautentikasi SENDIRI + POST dispatch penuh."""

    def run():
        from django.db import connection as conn

        try:
            client = _client_for(
                user, tenant_id, reauth_until=REAUTH_FAR_FUTURE,
                raise_request_exception=raise_request_exception,
            )
            pids[tag] = _pg_pid()
            response = client.post(url, body, headers={"Idempotency-Key": key})
            results[tag] = {"status": response.status_code, "data": _response_data(response)}
        except ApiError as exc:
            results[tag] = {"api_error": exc.code, "status": exc.status_code}
        except Exception as exc:  # noqa: BLE001
            results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
        finally:
            conn.close()

    return run


class TestConcurrentHttpClaimReplay:
    def test_concurrent_http_same_identity_waits_then_replays_single_effect(self):
        """Same identity/key/body bersamaan via HTTP penuh: pemilik klaim
        menunggu kunci domain (dipaksa), penantang memblok pada INSERT unik
        klaim (diamati pg_stat_activity); setelah selesai, penantang MEREPLAY
        respons — bukan 409 permanen, bukan duplicate write/500."""
        world = _world("rtrw-pa000014")
        body = {"plan_code": "gold", "term": "monthly"}
        key = "pa006-race-1"
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import Subscription

        run_a = _http_post_runner("A", user=world.owner, tenant_id=world.tenant.id,
                                  url=url, body=body, key=key, results=results, pids=pids)
        run_b = _http_post_runner("B", user=world.owner, tenant_id=world.tenant.id,
                                  url=url, body=body, key=key, results=results, pids=pids)

        # Kunci baris subscription dipegang thread utama → memaksa interleaving:
        # A terblokir DI DALAM handler (setelah klaim INSERT), B terblokir pada
        # klaim INSERT unik milik A (speculative unique wait PostgreSQL).
        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            Subscription.objects.select_for_update().get(tenant=world.tenant.id)
            ta = _thread(run_a)
            a_pid = _wait_pid(pids, "A")
            _assert_lock_wait(observer, a_pid, context="A (dispatch HTTP) menunggu kunci subscription")
            tb = _thread(run_b)
            b_pid = _wait_pid(pids, "B")
            _assert_lock_wait(observer, b_pid, context="B (dispatch HTTP) menunggu klaim INSERT unik A")
        finally:
            scope.__exit__(None, None, None)  # lepaskan kunci → A selesai → B replay
            observer.close()

        _join([ta, tb])
        assert pids["A"] != pids["B"], "kedua thread harus koneksi PostgreSQL terpisah"

        # Satu aksi logis; penantang mereplay respons identik; tanpa exception.
        assert "exception" not in results.get("A", {}), results
        assert "exception" not in results.get("B", {}), results
        assert results["A"]["status"] == 201
        assert results["B"]["status"] == 201
        assert results["B"]["data"] == results["A"]["data"]
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1
        assert _idem_count(operation="quotation", idem_key=key) == 1

    def test_concurrent_http_same_key_different_body_conflict(self):
        world = _world("rtrw-pa000015")
        key = "pa006-race-2"
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import Subscription

        run_a = _http_post_runner("A", user=world.owner, tenant_id=world.tenant.id, url=url,
                                  body={"plan_code": "gold", "term": "monthly"}, key=key,
                                  results=results, pids=pids)
        run_b = _http_post_runner("B", user=world.owner, tenant_id=world.tenant.id, url=url,
                                  body={"plan_code": "silver", "term": "monthly"}, key=key,
                                  results=results, pids=pids)

        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            Subscription.objects.select_for_update().get(tenant=world.tenant.id)
            ta = _thread(run_a)
            _assert_lock_wait(observer, _wait_pid(pids, "A"), context="A menunggu kunci subscription")
            tb = _thread(run_b)
            _assert_lock_wait(observer, _wait_pid(pids, "B"), context="B menunggu klaim INSERT unik A")
        finally:
            scope.__exit__(None, None, None)
            observer.close()

        _join([ta, tb])
        statuses = sorted(r.get("status") for r in results.values())
        assert statuses == [201, 409], results
        loser = results["A"] if results["A"]["status"] == 409 else results["B"]
        assert loser["data"]["code"] == "idempotency_conflict"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

    def test_concurrent_http_platform_decision_replay_204_single_effect(self):
        world = _world("rtrw-pa000016")
        admin = _platform_admin("platform-race-pa006@test.local")
        submission = _make_platform_submission(world)
        key = "pa006-race-3"
        url = f"/api/v1/platform/payment-submissions/{submission.id}/approve"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope

        run_a = _http_post_runner("A", user=admin, tenant_id=None, url=url,
                                  body=None, key=key, results=results, pids=pids)
        run_b = _http_post_runner("B", user=admin, tenant_id=None, url=url,
                                  body=None, key=key, results=results, pids=pids)

        # Paksa interleaving: pegang kunci baris submission (RLS → dalam scope).
        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            PaymentSubmission.objects.select_for_update().get(id=submission.id)
            ta = _thread(run_a)
            _assert_lock_wait(observer, _wait_pid(pids, "A"),
                              context="A (HTTP platform) menunggu kunci submission")
            tb = _thread(run_b)
            _assert_lock_wait(observer, _wait_pid(pids, "B"),
                              context="B (HTTP platform) menunggu klaim INSERT unik A")
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
        from domains.common.tenant_context import tenant_scope as _ts

        with _ts(world.tenant.id):
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
        with _ts(world.tenant.id):
            sub = Subscription.objects.get(tenant_id=world.tenant.id)
        assert sub.state == Subscription.State.ACTIVE
        assert sub.period_index == 1

    def test_http_eight_threads_same_key_no_unique_violation_500(self):
        world = _world("rtrw-pa000017")
        key = "pa006-race-4"
        body = {"plan_code": "gold", "term": "monthly"}
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        results: dict[str, dict] = {}
        barrier = threading.Barrier(8, timeout=30)

        def run(tag):
            from django.db import connection as conn

            try:
                client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
                barrier.wait()
                response = client.post(url, body, headers={"Idempotency-Key": key})
                results[tag] = {"status": response.status_code, "data": _response_data(response)}
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

    def test_http_concurrent_different_principal_same_key_both_execute(self):
        world = _world("rtrw-pa000018", extra_member=True)
        key = "pa006-race-5"
        body = {"plan_code": "gold", "term": "monthly"}
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        results: dict[str, dict] = {}
        barrier = threading.Barrier(2, timeout=30)

        def run(tag, user):
            from django.db import connection as conn

            try:
                client = _client_for(user, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
                barrier.wait()
                response = client.post(url, body, headers={"Idempotency-Key": key})
                results[tag] = {"status": response.status_code, "data": _response_data(response)}
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

    def test_http_leader_rollback_after_writes_contender_takes_over(self):
        """REV-1411-04: kegagalan DISUNTIK setelah writes domain/audit/outbox
        sebelum respons dipersist, SAAT penantang same-key menunggu klaim.
        Transaksi leader harus ter-rollbalik utuh (klaim+efek+cache); penantang
        mengambil alih dan mengeksekusi bersih → SATU aksi logis terkomit."""
        world = _world("rtrw-pa000021")
        admin = _platform_admin("platform-takeover-pa006@test.local")
        submission = _make_platform_submission(world)
        key = "pa006-race-6"
        url = f"/api/v1/platform/payment-submissions/{submission.id}/approve"
        results: dict[str, dict] = {}
        pids: dict[str, int] = {}
        observer = _observer_conn()

        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions import services as sub_services

        real_decide = sub_services.decide_platform_submission
        fail_once = threading.Event()

        def flaky_decide(*args, **kwargs):
            # Panggil implementasi nyata: state submission, audit event, outbox
            # event, source event — semuanya ditulis dalam transaksi request.
            result = real_decide(*args, **kwargs)
            if fail_once.is_set():
                fail_once.clear()  # satu-kali: hanya leader yang gagal
                raise RuntimeError(
                    "injected: kegagalan setelah domain/audit/outbox writes, "
                    "sebelum respons idempotency dipersist"
                )
            return result

        run_a = _http_post_runner("A", user=admin, tenant_id=None, url=url,
                                  body=None, key=key, results=results, pids=pids,
                                  raise_request_exception=False)
        run_b = _http_post_runner("B", user=admin, tenant_id=None, url=url,
                                  body=None, key=key, results=results, pids=pids,
                                  raise_request_exception=False)

        scope = tenant_scope(world.tenant.id)
        scope.__enter__()
        try:
            # A terblokir di dalam handler (sebelum writes) pada kunci baris
            # submission; B terblokir pada klaim INSERT unik milik A.
            PaymentSubmission.objects.select_for_update().get(id=submission.id)
            with mock.patch.object(
                sub_services, "decide_platform_submission", side_effect=flaky_decide
            ):
                ta = _thread(run_a)
                _assert_lock_wait(observer, _wait_pid(pids, "A"),
                                  context="A terblokir di dalam handler (dispatch HTTP)")
                tb = _thread(run_b)
                _assert_lock_wait(observer, _wait_pid(pids, "B"),
                                  context="B menunggu klaim INSERT unik A")
                # Suntik kegagalan satu-kali SETELAH writes decide_platform_
                # submission, SEBELUM respons dipersist oleh dekorator.
                fail_once.set()
        finally:
            # Lepaskan kunci → A menyelesaikan writes lalu GAGAL (rollback
            # transaksi request: klaim + efek + cache); B mengambil alih.
            scope.__exit__(None, None, None)
            observer.close()

        _join([ta, tb])

        # Leader A gagal setelah writes → seluruh transaksinya ter-rollbalik;
        # klien tes menangkapnya sebagai respons 500 (raise_request_exception
        # dimatikan agar signal exception Django tidak menular ke klien B).
        assert results["A"]["status"] == 500, results

        # Penantang B mengambil alih klaim yang sudah ter-rollbalik → 204.
        assert results["B"]["status"] == 204, results

        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent
        from domains.subscriptions.models import PlatformPaymentSourceEvent, Subscription
        from domains.common.tenant_context import tenant_scope as _ts

        # SATU aksi logis terkomit: efek A ter-rollbalik, hanya efek B yang
        # tersisa — klaim/cache tepat satu record dan dimiliki penyerahan B.
        assert _idem_count(idem_key=key) == 1
        record = IdempotencyKey.objects.get(idem_key=key)
        assert record.response_status == 204
        assert record.tenant_scope == "platform"
        assert record.operation == "platform_submission_approve"
        with _ts(world.tenant.id):
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
        with _ts(world.tenant.id):
            sub = Subscription.objects.get(tenant_id=world.tenant.id)
        assert sub.state == Subscription.State.ACTIVE

        # Retry setelah takeover → replay respons B (aksi logis yang sama).
        client = _client_for(admin, reauth_until=REAUTH_FAR_FUTURE)
        r3 = client.post(url, headers={"Idempotency-Key": key})
        assert r3.status_code == 204
        assert _idem_count(idem_key=key) == 1
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 1


# ---------------------------------------------------------------------------
# D. Legacy record & migrasi 0004 (REV-1311-01/02/03)
# ---------------------------------------------------------------------------


def _migration_world(namespace):
    """Dua session migrasi (router beda) dengan grup konflik identitas sama."""
    from domains.common.tenant_context import tenant_scope
    from domains.customers.models import MigrationSession
    from domains.customers.services import conflict_group_id
    from domains.network.models import DiscoveryObject, DiscoverySnapshot, Router

    sub_services.seed_plans()
    world = _world(namespace)
    client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
    with tenant_scope(world.tenant.id):
        sessions = []
        for i, username in enumerate(("scope.repro", "Scope.Repro")):
            router = Router.objects.create(tenant=world.tenant, display_name=f"Scope R{i}", router_code=f"scope-r{i}")
            snapshot = DiscoverySnapshot.objects.create(tenant=world.tenant, router=router, status=DiscoverySnapshot.Status.SUCCEEDED)
            DiscoveryObject.objects.create(tenant=world.tenant, router=router, snapshot=snapshot, username=username, kind=DiscoveryObject.Kind.PPPOE)
            sessions.append(MigrationSession.objects.create(tenant=world.tenant, router=router, snapshot=snapshot, state=MigrationSession.State.DISCOVERED))
    return world, client, sessions, conflict_group_id(["scope.repro", "Scope.Repro"])


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

    # -- REV-1311-01: legacy payment_submission (resource='') ---------------

    def test_retained_old_proof_scope_replays_without_second_submission(self):
        """Record hasil migrasi 0004 dari scope lama payment_submission:<t>:
        (resource='') — retry owner/invoice/key/body sama HARUS mereplay
        submission semula, bukan menulis submission/file kedua."""
        sub_services.seed_plans()
        from domains.common.tenant_context import tenant_scope
        from django.utils import timezone

        world = _world("rtrw-pa000022")
        invoice = _make_invoice(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-old", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        # Persis hasil migrasi 0004 pada baris sukses format main:
        # scope payment_submission:<tenant>: → resource='' + respons utuh.
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="payment_submission", resource="", idem_key="pa006-legacy-proof-1",
            body_hash=_body_hash_legacy_of(_PROOF_BODY), response_status=201,
            response_body=response_old, created_at=timezone.now(),
        )
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "pa006-legacy-proof-1"},
        )
        assert response.status_code == 201
        assert response.json() == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    def test_legacy_proof_replay_guard_rejects_wrong_invoice_target(self):
        """Record legacy milik invoice A: retry key sama ke invoice B → 409
        (B tidak memperoleh respons/submission A), tanpa efek kedua."""
        sub_services.seed_plans()
        from domains.common.tenant_context import tenant_scope
        from django.utils import timezone

        world = _world("rtrw-pa000023")
        inv_a, inv_b = _make_invoice(world), _make_invoice(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=inv_a, amount=inv_a.amount,
                proof_path="payment-proofs/synthetic-old-b", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="payment_submission", resource="", idem_key="pa006-legacy-proof-2",
            body_hash=_body_hash_legacy_of(_PROOF_BODY), response_status=201,
            response_body={"submission_id": str(original.id), "state": original.state},
            created_at=timezone.now(),
        )
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{inv_b.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "pa006-legacy-proof-2"},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "idempotency_conflict"
        # Tidak ada efek kedua: submission B tidak terbentuk, A tetap satu.
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=inv_a.id) == 1
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=inv_b.id) == 0

    def test_legacy_proof_without_response_blocked_safe(self):
        """Record legacy TANPA respons (efek tak terbukti — crash window
        protokol lama): retry → 409 aman, tidak blind-execute."""
        sub_services.seed_plans()
        from django.utils import timezone

        world = _world("rtrw-pa000024")
        invoice = _make_invoice(world)
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="payment_submission", resource="", idem_key="pa006-legacy-proof-3",
            body_hash=_body_hash_legacy_of(_PROOF_BODY),
            created_at=timezone.now(),
        )
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "pa006-legacy-proof-3"},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 0

    def test_actual_migration_must_not_erase_ambiguous_committed_effect_guard(self):
        """Transisi migrasi NYATA (0003 → 0004): klaim quotation tanpa respons
        (crash window main) TIDAK BOLEH dihapus migrasi; retry HTTP tidak
        menulis invoice kedua."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone

        world = _world("rtrw-pa000025")
        body = {"plan_code": "gold", "term": "monthly"}
        # Emulasi crash window main: efek bisnis terkomit, respons absen.
        from domains.common.tenant_context import tenant_scope

        with tenant_scope(world.tenant.id):
            invoice, _ = sub_services.create_quotation(world.tenant.id, "gold", "monthly")
        IdempotencyKey.objects.all().delete()  # reverse 0004 butuh tabel kosong
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id), scope=f"quotation:{world.tenant.id}:",
            idem_key="pa006-mig-guard-1", body_hash=_body_hash_legacy_of(body),
            response_status=None, response_body=None, created_at=timezone.now(),
        )
        # Migrasi Django/PostgreSQL nyata, lalu retry HTTP terautentikasi.
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])
        guard_count = IdempotencyKey.objects.filter(idem_key="pa006-mig-guard-1").count()
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations", body,
            headers={"Idempotency-Key": "pa006-mig-guard-1"},
        )
        assert guard_count == 1, "migrasi menghapus penjaga klaim ambigu"
        assert response.status_code == 409, "retry mengeksekusi ulang efek tak terbukti"
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 1

    def test_actual_migration_payment_submission_retry_replays_original(self):
        """Acceptance REV-1311-01: upload format main → migrasi 0004 nyata →
        retry owner/invoice/key/body sama mengembalikan submission semula;
        submission/file tetap 1; beda body → 409."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope

        sub_services.seed_plans()
        world = _world("rtrw-pa000026")
        invoice = _make_invoice(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-main-upgrade", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id), scope=f"payment_submission:{world.tenant.id}:",
            idem_key="pa006-mig-proof-1", body_hash=_body_hash_legacy_of(_PROOF_BODY),
            response_status=201, response_body=response_old, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        # Retry identik → submission semula; tidak ada submission/file kedua.
        r_retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "pa006-mig-proof-1"},
        )
        assert r_retry.status_code == 201
        assert r_retry.json() == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        # Body beda pada key yang sama → 409 idempotency_conflict.
        r_conflict = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            {**_PROOF_BODY, "file_name": "bukti-lain.png"},
            headers={"Idempotency-Key": "pa006-mig-proof-1"},
        )
        assert r_conflict.status_code == 409
        assert r_conflict.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    def test_actual_migration_platform_active_tenant_scope_replayed(self):
        """Legacy scope platform_submission_approve:<active-tenant>:<sub>
        (defek pra-PA006) → migrasi 0004 remap tenant_scope='platform' →
        retry platform admin MEREPLAY 204 tanpa keputusan baru."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone

        sub_services.seed_plans()
        world = _world("rtrw-pa000027")
        admin = _platform_admin("platform-mig-pa006@test.local")
        submission = _make_platform_submission(world, state=PaymentSubmission.State.APPROVED)
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(admin.id),
            scope=f"platform_submission_approve:{world.tenant.id}:{submission.id}",
            idem_key="pa006-mig-platform-1", body_hash=_body_hash_legacy_of(None),
            response_status=204, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])
        record = IdempotencyKey.objects.get(idem_key="pa006-mig-platform-1")
        assert record.tenant_scope == "platform"  # remap dari active-tenant lama
        assert record.resource == str(submission.id)

        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent

        client = _client_for(admin, reauth_until=REAUTH_FAR_FUTURE)
        r = client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "pa006-mig-platform-1"},
        )
        assert r.status_code == 204  # replay, bukan eksekusi ulang keputusan
        assert _idem_count(idem_key="pa006-mig-platform-1") == 1
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 0
        assert _count_in_tenant(
            AuditEvent, world.tenant.id, action_code="payment_submission.approve"
        ) == 0

    def test_migration_0004_backfill_canonical_dedupe_and_fail_safe_retention(self):
        """Migrasi jobs.0004: backfill identitas canonical dari scope lama,
        dedupe alias; scope tak terurai DIPERTAHANKAN sebagai baris mati
        (fail-safe REV-1311-01); record tanpa respons DIPERTAHANKAN (penjaga
        efek ambigu); constraint identitas dipasang."""
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

        world = _world("rtrw-pa000028")
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
        # 3) klaim tanpa respons (crash window protokol lama) → DIPERTAHANKAN
        #    sebagai penjaga; runtime menolak aman (409) pada retry.
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope=f"quotation:{world.tenant.id}:",
            idem_key="mig-stale",
            body_hash=body_h,
            created_at=now - _dt.timedelta(days=2),
        )
        # 4) scope salah bentuk → baris mati DIPERTAHANKAN (fail-safe
        #    REV-1311-01: kegagalan parser delimiter bukan izin menghapus
        #    penjaga efek non-expired — bukti rekonsiliasi ops tetap ada).
        IdemOld.objects.create(
            principal=str(world.owner.id),
            scope="tidak-terurai",
            idem_key="mig-bad",
            body_hash=body_h,
            response_status=201,
            created_at=now - _dt.timedelta(days=2),
        )
        # 5) resource opaque sah (identity_conflict_resolve group sha256[:16])
        #    → DIPERTAHANKAN apa adanya (bentuk legacy; runtime menolak aman).
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

        # Klaim tanpa respons DIPERTAHANKAN (bukan dihapus).
        assert IdempotencyKey.objects.filter(idem_key="mig-stale").count() == 1
        # Scope tak terurai → baris mati RETAINED (bukan dihapus): penanda
        # operasi khusus tidak pernah cocok dengan klaim runtime baru; respons
        # (evidence aksi selesai) tetap utuh untuk rekonsiliasi ops.
        bad = IdempotencyKey.objects.get(idem_key="mig-bad")
        assert bad.operation == "__unparsed__"
        assert bad.response_status == 201
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

        # Klaim tanpa respons hasil backfill → ditolak aman saat retry.
        r_stale = ca.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            body, headers={"Idempotency-Key": "mig-stale"},
        )
        assert r_stale.status_code == 409
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 0

        # Key record opaque pada operasi BERBEDA → aksi baru sah (identity
        # terpisah per operasi; blocking legacy hanya pada operasinya).
        r_opaque = ca.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            body, headers={"Idempotency-Key": "mig-opaque"},
        )
        assert r_opaque.status_code == 201  # operasi beda → aksi baru sah

        # Key record tak-terurai pada operasi apa pun → aksi baru sah: baris
        # mati ber-penanda operasi khusus tidak pernah cocok (tidak menahan,
        # tidak 500); penjaga/evidence tetap tersimpan untuk ops.
        r_bad = ca.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            body, headers={"Idempotency-Key": "mig-bad"},
        )
        assert r_bad.status_code == 201

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
        # Tiga invoice total: aksi baru key mig-opaque, aksi baru key
        # mig-bad (baris mati tak terurai tidak menahan), dan aksi baru
        # principal member — keduanya bukan replay legacy.
        assert _count_in_tenant(SaaSInvoice, world.tenant.id) == 3


# ---------------------------------------------------------------------------
# E. REV-1311-02 — identity_conflict_resolve terikat session migrasi
# ---------------------------------------------------------------------------


class TestConflictResolveSessionScope:
    def test_same_key_same_group_different_session_applies_both(self):
        """Group sama dipakai ulang lintas session: key/body sama pada session
        A lalu B → B menulis keputusannya SENDIRI (bukan replay 204 milik A)."""
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import MigrationAccountDecision

        world, client, sessions, group_id = _migration_world("rtrw-pa000029")
        body = {"resolution": "merge"}
        headers = {"Idempotency-Key": "pa006-crs-1"}
        base = f"/api/v1/tenants/{world.tenant.id}/migrations"
        first = client.post(f"{base}/{sessions[0].id}/identity-conflicts/{group_id}", body, headers=headers)
        assert first.status_code == 204, first.content
        second = client.post(f"{base}/{sessions[1].id}/identity-conflicts/{group_id}", body, headers=headers)
        assert second.status_code == 204, second.content
        with tenant_scope(world.tenant.id):
            counts = [MigrationAccountDecision.objects.filter(session=s).count() for s in sessions]
        assert counts == [2, 2], "204 kedua mereplay session pertama; session kedua tidak terselesaikan"

    def test_retry_same_session_replays_without_second_decision_set(self):
        """Retry session A (key/body sama) → replay 204; keputusan tidak
        diduplikasi; record idempotency tepat satu per session."""
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import MigrationAccountDecision

        world, client, sessions, group_id = _migration_world("rtrw-pa000030")
        body = {"resolution": "merge"}
        headers = {"Idempotency-Key": "pa006-crs-2"}
        url = f"/api/v1/tenants/{world.tenant.id}/migrations/{sessions[0].id}/identity-conflicts/{group_id}"
        first = client.post(url, body, headers=headers)
        assert first.status_code == 204
        retry = client.post(url, body, headers=headers)
        assert retry.status_code == 204
        with tenant_scope(world.tenant.id):
            count = MigrationAccountDecision.objects.filter(session=sessions[0]).count()
        assert count == 2
        assert _idem_count(operation="identity_conflict_resolve", idem_key="pa006-crs-2") == 1

    @pytest.mark.parametrize("bad_parent,expected", [("not-a-uuid", 422), (str(_uuid.uuid4()), 404)])
    def test_cached_group_must_not_skip_invalid_or_missing_parent(self, bad_parent, expected):
        """Respons cache tidak boleh melewati validasi parent: migration_id
        salah bentuk → 422; session tidak ditemukan → 404 (bukan 204 replay)."""
        world, client, sessions, group_id = _migration_world(f"rtrw-pa000031{expected}")
        body = {"resolution": "merge"}
        headers = {"Idempotency-Key": "pa006-crs-3"}
        base = f"/api/v1/tenants/{world.tenant.id}/migrations"
        valid = client.post(f"{base}/{sessions[0].id}/identity-conflicts/{group_id}", body, headers=headers)
        assert valid.status_code == 204, valid.content
        invalid = client.post(f"{base}/{bad_parent}/identity-conflicts/{group_id}", body, headers=headers)
        assert invalid.status_code == expected, "respons cache group melewati validasi/lookup parent"

    def test_parent_uuid_alias_same_identity_replays(self):
        """Ejaan alias migration UUID (huruf besar) → identitas canonical sama
        → replay, bukan aksi baru."""
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import MigrationAccountDecision

        world, client, sessions, group_id = _migration_world("rtrw-pa000032")
        body = {"resolution": "merge"}
        headers = {"Idempotency-Key": "pa006-crs-4"}
        base = f"/api/v1/tenants/{world.tenant.id}/migrations"
        first = client.post(f"{base}/{sessions[0].id}/identity-conflicts/{group_id}", body, headers=headers)
        assert first.status_code == 204
        alias = client.post(
            f"{base}/{str(sessions[0].id).upper()}/identity-conflicts/{group_id}", body, headers=headers
        )
        assert alias.status_code == 204
        with tenant_scope(world.tenant.id):
            count = MigrationAccountDecision.objects.filter(session=sessions[0]).count()
        assert count == 2
        assert _idem_count(operation="identity_conflict_resolve", idem_key="pa006-crs-4") == 1

    def test_legacy_group_only_record_rejected_safe(self):
        """Record pra-0004 (group-only, tanpa migration UUID) tidak dapat
        diikat ke session → retry key yang sama ditolak aman 409; keputusan
        session tidak dieksekusi ulang; session lain tidak terkena efek."""
        from domains.customers.models import MigrationAccountDecision
        from django.utils import timezone

        world, client, sessions, group_id = _migration_world("rtrw-pa000033")
        # Record legacy hasil backfill 0004 (resource = group saja).
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="identity_conflict_resolve", resource=group_id,
            idem_key="pa006-crs-legacy",
            body_hash=_body_hash_of({"resolution": "merge"}),
            response_status=204, response_body=None, created_at=timezone.now(),
        )
        body = {"resolution": "merge"}
        url = f"/api/v1/tenants/{world.tenant.id}/migrations/{sessions[0].id}/identity-conflicts/{group_id}"
        response = client.post(url, body, headers={"Idempotency-Key": "pa006-crs-legacy"})
        assert response.status_code == 409
        assert response.json()["code"] == "idempotency_conflict"
        assert MigrationAccountDecision.objects.filter(session=sessions[0]).count() == 0


# ---------------------------------------------------------------------------
# F. REV-1311-03 — body UUID ter-typed dinormalkan sebelum HMAC
# ---------------------------------------------------------------------------


class TestBodyUuidAliasNormalization:
    def _billing_world(self, namespace):
        from decimal import Decimal

        from domains.billing.models import BillingPackage
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import Customer, Service

        sub_services.seed_plans()
        world = _world(namespace)
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        with tenant_scope(world.tenant.id):
            customer = Customer.objects.create(tenant=world.tenant, display_name="Alias", customer_code="C-ALIAS")
            service = Service.objects.create(tenant=world.tenant, customer=customer, service_code="S-ALIAS")
            package = BillingPackage.objects.create(tenant=world.tenant, name="Alias package", monthly_price=Decimal("50000"))
            package_b = BillingPackage.objects.create(tenant=world.tenant, name="Alias package B", monthly_price=Decimal("60000"))
        return world, client, service, package, package_b

    def test_body_uuid_alias_replays_canonical_identity(self):
        """package_id ejaan alias (hex uppercase) pada body → hash canonical
        sama → REPLAY respons, bukan 409 konflik palsu."""
        world, client, service, package, _ = self._billing_world("rtrw-pa000034")
        url = f"/api/v1/tenants/{world.tenant.id}/services/{service.id}/billing-package"
        headers = {"Idempotency-Key": "pa006-body-1"}
        first = client.post(url, {"package_id": str(package.id)}, headers=headers)
        assert first.status_code == 200, first.content
        alias = client.post(url, {"package_id": package.id.hex.upper()}, headers=headers)
        assert alias.status_code == 200, "identitas UUID di body di-hash sebelum kanonikalisasi"
        assert alias.json() == first.json()

    def test_body_uuid_real_different_package_conflicts(self):
        """Package BENAR-BENAR berbeda pada key yang sama → 409 tanpa efek
        kedua (normalisasi tidak melebur target berbeda)."""
        world, client, service, package, package_b = self._billing_world("rtrw-pa000035")
        url = f"/api/v1/tenants/{world.tenant.id}/services/{service.id}/billing-package"
        headers = {"Idempotency-Key": "pa006-body-2"}
        first = client.post(url, {"package_id": str(package.id)}, headers=headers)
        assert first.status_code == 200
        conflict = client.post(url, {"package_id": str(package_b.id)}, headers=headers)
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "idempotency_conflict"
        # Efek pertama tetap: service masih terpasang package pertama.
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import Service

        with tenant_scope(world.tenant.id):
            service.refresh_from_db()
        assert str(service.billing_package_id) == str(package.id)

    def test_retained_raw_hash_record_replays_identical_and_alias_body(self):
        """Kompatibilitas hash raw pra-v2 (record era main): body identik
        byte-per-byte → replay; ejaan alias → replay karena original
        canonical (v2 == v1 canonical)."""
        world, client, service, package, _ = self._billing_world("rtrw-pa000036")
        from django.utils import timezone

        response_old = {
            "service_id": str(service.id),
            "billing_package_id": str(package.id),
        }
        # Record era main: hash v1 dari body canonical (lowercase).
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="service_billing_package", resource=str(service.id),
            idem_key="pa006-body-legacy",
            body_hash=_body_hash_legacy_of({"package_id": str(package.id)}),
            response_status=200, response_body=response_old, created_at=timezone.now(),
        )
        url = f"/api/v1/tenants/{world.tenant.id}/services/{service.id}/billing-package"
        # Body identik byte-per-byte → cocok via hash v1.
        identical = client.post(
            url, {"package_id": str(package.id)}, headers={"Idempotency-Key": "pa006-body-legacy"}
        )
        assert identical.status_code == 200
        assert identical.json() == response_old
        # Ejaan alias → v2(normalized) == v1(canonical original) → replay.
        alias = client.post(
            url, {"package_id": str(package.id).upper()}, headers={"Idempotency-Key": "pa006-body-legacy"}
        )
        assert alias.status_code == 200
        assert alias.json() == response_old
        # Package berbeda pada key legacy → 409 (body beda nyata).
        from domains.billing.models import BillingPackage
        from domains.common.tenant_context import tenant_scope

        with tenant_scope(world.tenant.id):
            other = BillingPackage.objects.create(tenant=world.tenant, name="Lain", monthly_price=1)
        conflict = client.post(
            url, {"package_id": str(other.id)}, headers={"Idempotency-Key": "pa006-body-legacy"}
        )
        assert conflict.status_code == 409

    def test_body_file_change_conflicts(self):
        """Bukti upload berbeda (file_b64 beda) pada key sama → 409 —
        normalisasi UUID tidak melebur perubahan isi file nyata."""
        world = _world("rtrw-pa000037")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        invoice = _make_invoice(world)
        url = f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions"
        headers = {"Idempotency-Key": "pa006-body-4"}
        first = client.post(url, _PROOF_BODY, headers=headers)
        assert first.status_code == 201
        other_png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"BUKTI-LAIN" * 6).decode()
        changed = client.post(
            url, {**_PROOF_BODY, "file_b64": other_png}, headers=headers
        )
        assert changed.status_code == 409
        assert changed.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    def test_concurrent_http_legacy_proof_retry_both_replay_original(self):
        """Celah bukti REV-1311-01 'concurrent retry': dua klien HTTP
        konkuren me-retry record legacy payment_submission resource='' —
        keduanya MEREPLAY submission semula; tidak ada submission kedua."""
        sub_services.seed_plans()
        from domains.common.tenant_context import tenant_scope
        from django.utils import timezone

        world = _world("rtrw-pa000038")
        invoice = _make_invoice(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-old-conc", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="payment_submission", resource="", idem_key="pa006-legacy-conc",
            body_hash=_body_hash_legacy_of(_PROOF_BODY), response_status=201,
            response_body=response_old, created_at=timezone.now(),
        )
        url = f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions"
        results: dict[str, dict] = {}
        barrier = threading.Barrier(2, timeout=30)

        def run(tag):
            from django.db import connection as conn

            try:
                client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
                barrier.wait()
                response = client.post(url, _PROOF_BODY, headers={"Idempotency-Key": "pa006-legacy-conc"})
                results[tag] = {"status": response.status_code, "data": _response_data(response)}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        threads = [_thread(lambda: run("A")), _thread(lambda: run("B"))]
        _join(threads)
        for tag, res in results.items():
            assert "exception" not in res, (tag, res)
            assert res["status"] == 201
            assert res["data"] == response_old
        # Record legacy statis (bukan klaim baru); submission tetap satu.
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        assert _idem_count(operation="payment_submission", idem_key="pa006-legacy-conc") == 1

    def test_retained_raw_hash_noncanonical_original_fails_safe_409(self):
        """Batas terdokumentasi kebijakan retained hash: record v1 yang
        ASLINYA memakai ejaan non-canonical + retry berbeda ejaan → 409 aman
        (bukan replay salah, bukan eksekusi kedua). Body identik byte-per-byte
        tetap replay (dibuktikan tes lain)."""
        sub_services.seed_plans()
        from domains.billing.models import BillingPackage
        from domains.common.tenant_context import tenant_scope
        from django.utils import timezone

        world = _world("rtrw-pa000039")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        with tenant_scope(world.tenant.id):
            from domains.customers.models import Customer, Service

            customer = Customer.objects.create(tenant=world.tenant, display_name="NC", customer_code="C-NC")
            service = Service.objects.create(tenant=world.tenant, customer=customer, service_code="S-NC")
            package = BillingPackage.objects.create(tenant=world.tenant, name="NC package", monthly_price=1)
            service.billing_package = package  # emulasi aksi era main yang sudah selesai
            service.save(update_fields=["billing_package"])
        # Record era main yang aslinya NON-canonical (uppercase hex).
        noncanon_body = {"package_id": package.id.hex.upper()}
        response_old = {"service_id": str(service.id), "billing_package_id": str(package.id)}
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="service_billing_package", resource=str(service.id),
            idem_key="pa006-nc-legacy",
            body_hash=_body_hash_legacy_of(noncanon_body),
            response_status=200, response_body=response_old, created_at=timezone.now(),
        )
        url = f"/api/v1/tenants/{world.tenant.id}/services/{service.id}/billing-package"
        # Retry dengan ejaan canonical (berbeda dari body asli) → 409 aman.
        canonical = client.post(
            url, {"package_id": str(package.id)}, headers={"Idempotency-Key": "pa006-nc-legacy"}
        )
        assert canonical.status_code == 409
        assert canonical.json()["code"] == "idempotency_conflict"
        # Retry identik byte-per-byte dengan body asli → tetap replay.
        identical = client.post(
            url, noncanon_body, headers={"Idempotency-Key": "pa006-nc-legacy"}
        )
        assert identical.status_code == 200
        assert identical.json() == response_old
        # Tidak ada aksi kedua: state service tidak berubah oleh 409/replay.
        with tenant_scope(world.tenant.id):
            service.refresh_from_db()
        assert str(service.billing_package_id) == str(package.id)
