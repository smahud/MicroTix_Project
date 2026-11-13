"""Tes integrasi PA-006 — HTTP idempotency aman terhadap scope dan race.

Membuktikan acceptance packet task/0010 pada PostgreSQL nyata dengan klien
HTTP terautentikasi independen (satu koneksi PostgreSQL per thread; PID tiap
thread diverifikasi berbeda) dan interleaving TERPAKSA (leader ditahan di
dalam handler + observasi pg_stat_activity), bukan barrier lalu berharap
race terjadi.

Matriks acceptance → tes:
1. Same identity/key/body bersamaan ....... TestConcurrentSameIdentity
   (satu aksi logis; replay hasil sama; tanpa duplicate/500; tidak ada
   record in-flight ter-commit — dibuktikan dari koneksi pengamat).
2. Same identity/key beda body ............ TestBodyConflict
3. Beda principal/tenant/platform/op/resource TestPrincipalTenantPlatformSeparation
   (+ concurrent beda principal tanpa unique-violation 500).
4. UUID alias / malformed ................. TestCanonicalIdentity
5. SaaS proof invoice A vs B key sama ..... TestSaasProofResourceScope
6. Platform operator pindah active tenant . TestPlatformScopeStability
7. Permission/session/step-up saat replay . TestReplayAuthorization
8. Gagal sebelum DB commit ................ TestFailureRollback
9. Crash setelah commit sebelum respons ... TestAtomicClaimResponse
   (protokol: klaim+efek+respons SATU transaksi — record tanpa respons
   commit tak terjadi; record tanpa respons (legacy/terputus) TIDAK
   dieksekusi ulang buta).
10. TTL dan legacy records ................ TestTtlAndLegacyRecords
    (business uniqueness tetap; tidak ada respons ke principal/target salah).

Marker `transaction=True` wajib agar setup ter-commit dan terlihat oleh
koneksi thread; `available_apps` membatasi flush teardown (tabel subscriptions
dibersihkan via TRUNCATE CASCADE dari tenancy, PlanVersion seed selamat).
"""
from __future__ import annotations

import base64
import datetime
import threading
import time
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.db import connection as dj_connection
from django.utils import timezone
from rest_framework.test import APIClient

from domains.audit.models import AuditEvent
from domains.common.envelope import ApiError
from domains.common.idempotency import _body_hash
from domains.common.tenant_context import tenant_scope
from domains.identity.models import User
from domains.jobs.models import IdempotencyKey, OutboxEvent
from domains.subscriptions import services as sub_services
from domains.subscriptions.models import PaymentSubmission, SaaSInvoice
from domains.tenancy.models import Membership, Role, Tenant

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db(
        transaction=True,
        available_apps=[
            "domains.tenancy",
            "domains.identity",
            "domains.customers",
            "domains.billing",
            "domains.documents",
            "domains.audit",
            "domains.jobs",
        ],
    ),
]

JOIN_TIMEOUT_S = 90
TEST_PASSWORD = "test-password-1234567890"
PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
PNG2_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"1" * 64).decode()


def _wait_backend_blocked(*, exclude_pids: tuple[int, ...], deadline_s: float = 30.0) -> tuple | None:
    """Tunggu backend KLIENT lain terlihat aktif-menunggu (bukti blokir,
    pola PA-001 _wait_backend_lock_wait) — bukan barrier + harapan."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        with dj_connection.cursor() as cur:
            cur.execute(
                "SELECT pid, wait_event_type, wait_event FROM pg_stat_activity "
                "WHERE datname = current_database() AND backend_type = 'client backend' "
                "AND state = 'active' AND wait_event_type IS NOT NULL "
                "AND pid <> ALL(%s)",
                [list(exclude_pids)],
            )
            row = cur.fetchone()
        if row is not None:
            return tuple(row)
        time.sleep(0.05)
    return None


def _pg_pid() -> int:
    """PID backend PostgreSQL koneksi thread ini (bukti koneksi terpisah)."""
    with dj_connection.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        return cur.fetchone()[0]


def _setup_world(namespace: str, *, members: int = 1, second_tenant: bool = False) -> SimpleNamespace:
    """Setup ter-commit: tenant(+opsi tenant kedua), owner(+member tambahan)."""
    tenant = Tenant.objects.create(display_name=f"PA006 {namespace}", namespace=f"pa006-{namespace}")
    owner = User.objects.create_user(
        email=f"{namespace}-owner@test.local", full_name="Owner PA006",
        password=TEST_PASSWORD, is_active=True,
    )
    Membership.objects.create(user=owner, tenant=tenant, role=Role.OWNER)
    with tenant_scope(tenant.id):
        sub_services.ensure_free_subscription(tenant)
    others = []
    for i in range(members - 1):
        other = User.objects.create_user(
            email=f"{namespace}-member{i}@test.local", full_name=f"Member {i}",
            password=TEST_PASSWORD, is_active=True,
        )
        Membership.objects.create(user=other, tenant=tenant, role=Role.OWNER)
        others.append(other)
    tenant_b = None
    owner_b = None
    if second_tenant:
        tenant_b = Tenant.objects.create(display_name=f"PA006 B {namespace}", namespace=f"pa006b-{namespace}")
        owner_b = User.objects.create_user(
            email=f"{namespace}-owner-b@test.local", full_name="Owner B",
            password=TEST_PASSWORD, is_active=True,
        )
        Membership.objects.create(user=owner_b, tenant=tenant_b, role=Role.OWNER)
        with tenant_scope(tenant_b.id):
            sub_services.ensure_free_subscription(tenant_b)
    return SimpleNamespace(tenant=tenant, owner=owner, others=others, tenant_b=tenant_b, owner_b=owner_b)


def _client(user, *, active_tenant=None, reauth=True) -> APIClient:
    """Klien HTTP terautentikasi dengan sesi sendiri (independen per thread)."""
    client = APIClient(enforce_csrf_checks=False)
    client.force_login(user)
    session = client.session
    if active_tenant is not None:
        session["active_tenant_id"] = str(active_tenant)
    session["auth_at"] = time.time()
    if reauth:
        session["reauth_until"] = "2099-01-01T00:00:00+00:00"
    session.save()
    return client


def _platform_admin(email: str) -> User:
    user = User.objects.create_user(
        email=email, full_name="Admin Platform", password=TEST_PASSWORD, is_active=True
    )
    user.platform_admin = True
    user.save(update_fields=["platform_admin"])
    return user


def _make_invoice(tenant, *, plan_code: str = "gold", term: str = "monthly") -> SaaSInvoice:
    with tenant_scope(tenant.id):
        invoice, _plan = sub_services.create_quotation(tenant.id, plan_code, term)
    return invoice


def _make_submission(tenant, invoice, actor) -> PaymentSubmission:
    with tenant_scope(tenant.id):
        return PaymentSubmission.objects.create(
            tenant=tenant,
            invoice=invoice,
            amount=invoice.amount,
            proof_path="payment-proofs/pa006",
            proof_mime="image/png",
            proof_size=1024,
            submitted_by=actor,
        )


def _idem_count(scope: str) -> int:
    return IdempotencyKey.objects.filter(scope=scope).count()


def _run_in_thread(target) -> threading.Thread:
    thread = threading.Thread(target=target)
    thread.start()
    return thread


def _close_thread_connection() -> None:
    try:
        dj_connection.close()
    except Exception:  # pragma: no cover - koneksi sudah tertutup
        pass


# ---------------------------------------------------------------------------
# 1. Same identity/key/body bersamaan — satu aksi logis + replay
# ---------------------------------------------------------------------------


class TestConcurrentSameIdentity:
    def test_concurrent_same_key_single_logical_action_and_replay(self, monkeypatch):
        """Dua klien HTTP konkuren (sesi terpisah, user sama, koneksi PG
        berbeda) dengan key+body sama → SATU invoice, keduanya 201 dengan
        respons logis sama; handler dieksekusi SEKALI; tidak ada 500."""
        world = _setup_world("conc-same")
        leader_entered = threading.Event()
        release_leader = threading.Event()
        evidence: dict = {}
        original = sub_services.create_quotation
        calls = []

        def slow_create_quotation(tenant_id, plan_code, term, locale="id"):
            evidence["leader_pid"] = _pg_pid()
            calls.append(threading.get_ident())
            leader_entered.set()
            assert release_leader.wait(JOIN_TIMEOUT_S), "leader tidak pernah dilepas"
            return original(tenant_id, plan_code, term, locale=locale)

        monkeypatch.setattr(sub_services, "create_quotation", slow_create_quotation)

        body = {"plan_code": "gold", "term": "monthly"}
        results: dict = {}

        def leader():
            try:
                client = _client(world.owner, active_tenant=world.tenant.id)
                results["leader"] = client.post(
                    f"/api/v1/tenants/{world.tenant.id}/quotations", body,
                    headers={"Idempotency-Key": "race-1"},
                )
            except Exception as exc:  # pragma: no cover
                results["leader_error"] = repr(exc)
            finally:
                _close_thread_connection()

        def follower():
            try:
                client = _client(world.owner, active_tenant=world.tenant.id)
                results["follower"] = client.post(
                    f"/api/v1/tenants/{world.tenant.id}/quotations", body,
                    headers={"Idempotency-Key": "race-1"},
                )
            except Exception as exc:  # pragma: no cover
                results["follower_error"] = repr(exc)
            finally:
                _close_thread_connection()

        leader_thread = _run_in_thread(leader)
        assert leader_entered.wait(JOIN_TIMEOUT_S), "handler leader tidak pernah masuk"

        # Leader sedang berjalan (klaim belum commit). Dari koneksi pengamat:
        # TIDAK ada record idempotency ter-commit — klaim+efek+respons SATU
        # transaksi; window "commit tanpa respons" tidak terjadi (PA-006).
        scope = f"quotation:{world.tenant.id}:"
        assert _idem_count(scope) == 0
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 0

        follower_thread = _run_in_thread(follower)
        # Follower menunggu klaim leader: observasi pg_stat_activity (bukan
        # barrier + harapan). INSERT pesaing menunggu unique index spekulatif
        # sampai transaksi pemimpin selesai; koneksi follower adalah backend
        # klien aktif-menunggu di luar main+leader.
        main_pid = _pg_pid()
        leader_pid = evidence["leader_pid"]
        observed_wait = _wait_backend_blocked(exclude_pids=(main_pid, leader_pid))
        # Follower terlihat MENUNGGU (bukan 500/unique-violation instan).
        assert observed_wait is not None, "follower tidak teramati menunggu klaim"
        evidence["follower_wait"] = observed_wait
        # Follower belum selesai saat leader masih ditahan.
        assert "follower" not in results

        release_leader.set()
        leader_thread.join(JOIN_TIMEOUT_S)
        follower_thread.join(JOIN_TIMEOUT_S)
        assert not leader_thread.is_alive() and not follower_thread.is_alive()

        assert "leader_error" not in results and "follower_error" not in results
        leader_resp, follower_resp = results["leader"], results["follower"]
        assert leader_resp.status_code == 201, leader_resp.content
        assert follower_resp.status_code == 201, follower_resp.content
        assert follower_resp.json()["invoice_id"] == leader_resp.json()["invoice_id"]

        # Satu aksi logis: handler dieksekusi SEKALI, satu invoice, satu
        # record idempotency dengan respons tersimpan.
        assert len(calls) == 1
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1
        records = IdempotencyKey.objects.filter(scope=scope, idem_key="race-1")
        assert records.count() == 1
        record = records.get()
        assert record.response_status == 201
        assert record.response_body["invoice_id"] == leader_resp.json()["invoice_id"]
        # Bukti koneksi independen + observasi tunggu (evidence interleave).
        assert evidence["leader_pid"] != main_pid
        assert observed_wait[0] not in (main_pid, leader_pid)
        assert evidence["follower_wait"] is not None

    def test_concurrent_leader_failure_follower_takes_over_fresh(self, monkeypatch):
        """Kodefekt lama: klaim ter-commit tanpa respons → retry buta/duplikat.
        Protokol baru: leader GAGAL setelah klaim (rollback klaim+efek);
        pesaing yang menunggu mengambil alih dan mengeksekusi SEGER — bukan
        409 permanen, bukan duplikat, tanpa efek sisa dari leader."""
        world = _setup_world("leader-fail")
        leader_entered = threading.Event()
        release_leader = threading.Event()
        original = sub_services.create_quotation
        calls = []

        def flaky_create(tenant_id, plan_code, term, locale="id"):
            calls.append(threading.get_ident())
            if len(calls) == 1:
                # Pemimpin: ditahan lalu gagal (transaksi rollback).
                leader_entered.set()
                assert release_leader.wait(JOIN_TIMEOUT_S)
                raise ApiError.validation(
                    {"plan_code": [{"code": "injected", "message": "injected leader failure"}]}
                )
            return original(tenant_id, plan_code, term, locale=locale)

        monkeypatch.setattr(sub_services, "create_quotation", flaky_create)
        body = {"plan_code": "gold", "term": "monthly"}
        results: dict = {}

        def leader():
            try:
                client = _client(world.owner, active_tenant=world.tenant.id)
                results["leader"] = client.post(
                    f"/api/v1/tenants/{world.tenant.id}/quotations", body,
                    headers={"Idempotency-Key": "takeover-1"},
                )
            except Exception as exc:  # pragma: no cover
                results["leader_error"] = repr(exc)
            finally:
                _close_thread_connection()

        def follower():
            try:
                client = _client(world.owner, active_tenant=world.tenant.id)
                results["follower"] = client.post(
                    f"/api/v1/tenants/{world.tenant.id}/quotations", body,
                    headers={"Idempotency-Key": "takeover-1"},
                )
            except Exception as exc:  # pragma: no cover
                results["follower_error"] = repr(exc)
            finally:
                _close_thread_connection()

        leader_thread = _run_in_thread(leader)
        assert leader_entered.wait(JOIN_TIMEOUT_S), "leader tidak pernah masuk handler"
        follower_thread = _run_in_thread(follower)
        # Follower menunggu klaim leader yang belum commit.
        assert (
            _wait_backend_blocked(exclude_pids=(_pg_pid(),)) is not None
        ), "follower tidak teramati menunggu klaim"
        assert "follower" not in results

        release_leader.set()  # leader gagal sekarang
        leader_thread.join(JOIN_TIMEOUT_S)
        follower_thread.join(JOIN_TIMEOUT_S)
        assert not leader_thread.is_alive() and not follower_thread.is_alive()

        assert "leader_error" not in results and "follower_error" not in results
        # Leader gagal jujur (422); klaimnya ikut rollback.
        assert results["leader"].status_code == 422
        # Follower mengambil alih: INSERT-nya berlanjut setelah rollback
        # leader, mengeksekusi segar, dan menyimpan responsnya.
        follower_resp = results["follower"]
        assert follower_resp.status_code == 201, follower_resp.content
        assert len(calls) == 2  # leader gagal + follower sukses
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1
        records = IdempotencyKey.objects.filter(
            scope=f"quotation:{world.tenant.id}:", idem_key="takeover-1"
        )
        assert records.count() == 1
        assert records.get().response_status == 201


# ---------------------------------------------------------------------------
# 2. Same key beda body → 409 tanpa efek kedua
# ---------------------------------------------------------------------------


class TestBodyConflict:
    def test_same_key_different_body_409_without_second_effect(self):
        world = _setup_world("body-conflict")
        client = _client(world.owner, active_tenant=world.tenant.id)
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        first = client.post(url, {"plan_code": "gold", "term": "monthly"}, headers={"Idempotency-Key": "bc-1"})
        assert first.status_code == 201
        second = client.post(url, {"plan_code": "gold", "term": "yearly"}, headers={"Idempotency-Key": "bc-1"})
        assert second.status_code == 409
        assert second.json()["code"] == "idempotency_conflict"
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1  # tanpa efek kedua

    def test_same_key_different_proof_file_conflict(self):
        """Body/file hash: bukti berbeda dengan key sama → 409, bukan duplikat."""
        world = _setup_world("file-conflict")
        invoice = _make_invoice(world.tenant)
        client = _client(world.owner, active_tenant=world.tenant.id)
        url = f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions"
        body_a = {"file_b64": PNG_B64, "mime": "image/png", "file_name": "a.png"}
        body_b = {"file_b64": PNG2_B64, "mime": "image/png", "file_name": "b.png"}
        first = client.post(url, body_a, headers={"Idempotency-Key": "fc-1"})
        assert first.status_code == 201, first.content
        second = client.post(url, body_b, headers={"Idempotency-Key": "fc-1"})
        assert second.status_code == 409
        assert second.json()["code"] == "idempotency_conflict"
        with tenant_scope(world.tenant.id):
            assert PaymentSubmission.objects.count() == 1


# ---------------------------------------------------------------------------
# 3. Beda principal/tenant/platform/operation/resource — tidak tertukar
# ---------------------------------------------------------------------------


class TestPrincipalTenantPlatformSeparation:
    def test_different_principal_same_key_independent_actions(self):
        """Key dimiliki principal: pengguna kedua dengan key sama mendapat
        aksi dan respons SENDIRI — tidak menerima respons pengguna pertama."""
        world = _setup_world("principal", members=2)
        second = world.others[0]
        client_a = _client(world.owner, active_tenant=world.tenant.id)
        client_b = _client(second, active_tenant=world.tenant.id)
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        body = {"plan_code": "gold", "term": "monthly"}
        resp_a = client_a.post(url, body, headers={"Idempotency-Key": "share-1"})
        resp_b = client_b.post(url, body, headers={"Idempotency-Key": "share-1"})
        assert resp_a.status_code == 201 and resp_b.status_code == 201
        assert resp_b.json()["invoice_id"] != resp_a.json()["invoice_id"]
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 2
        # Dua record idempotency milik masing-masing principal.
        scope = f"quotation:{world.tenant.id}:"
        rows = IdempotencyKey.objects.filter(scope=scope, idem_key="share-1")
        assert rows.count() == 2
        assert set(rows.values_list("principal", flat=True)) == {
            str(world.owner.id), str(second.id),
        }

    def test_concurrent_different_principal_no_unique_violation_500(self):
        """Kodefekt lama: dua principal konkuren dengan key sama saling
        bertabrakan pada UNIQUE(scope, idem_key) → 500. Identity baru tidak
        bertabrakan: keduanya mengeksekusi aksinya sendiri tanpa 500."""
        world = _setup_world("principal-race", members=2)
        second = world.others[0]
        barrier = threading.Barrier(2, timeout=JOIN_TIMEOUT_S)
        results: dict = {}
        body = {"plan_code": "gold", "term": "monthly"}

        def poster(user, tag):
            try:
                client = _client(user, active_tenant=world.tenant.id)
                barrier.wait()
                results[tag] = client.post(
                    f"/api/v1/tenants/{world.tenant.id}/quotations", body,
                    headers={"Idempotency-Key": "share-race"},
                )
            except Exception as exc:  # pragma: no cover
                results[f"{tag}_error"] = repr(exc)
            finally:
                _close_thread_connection()

        t1 = _run_in_thread(lambda: poster(world.owner, "a"))
        t2 = _run_in_thread(lambda: poster(second, "b"))
        t1.join(JOIN_TIMEOUT_S)
        t2.join(JOIN_TIMEOUT_S)
        assert "a_error" not in results and "b_error" not in results
        assert results["a"].status_code == 201, results["a"].content
        assert results["b"].status_code == 201, results["b"].content
        assert results["b"].json()["invoice_id"] != results["a"].json()["invoice_id"]
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 2

    def test_different_tenant_same_key_not_swapped(self):
        world = _setup_world("tenant-sep", second_tenant=True)
        client_a = _client(world.owner, active_tenant=world.tenant.id)
        client_b = _client(world.owner_b, active_tenant=world.tenant_b.id)
        body = {"plan_code": "gold", "term": "monthly"}
        resp_a = client_a.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations", body, headers={"Idempotency-Key": "cross-1"}
        )
        resp_b = client_b.post(
            f"/api/v1/tenants/{world.tenant_b.id}/quotations", body, headers={"Idempotency-Key": "cross-1"}
        )
        assert resp_a.status_code == 201 and resp_b.status_code == 201
        assert resp_b.json()["invoice_id"] != resp_a.json()["invoice_id"]
        with tenant_scope(world.tenant.id):
            invoice_a = SaaSInvoice.objects.get()
            assert str(invoice_a.id) == resp_a.json()["invoice_id"]
        with tenant_scope(world.tenant_b.id):
            invoice_b = SaaSInvoice.objects.get()
            assert str(invoice_b.id) == resp_b.json()["invoice_id"]

    def test_platform_and_tenant_operations_do_not_share_response(self):
        """SaaS platform dan pembayaran internet tenant dengan key sama
        tidak berbagi response/aksi: scope operation+target berbeda."""
        world = _setup_world("op-sep")
        invoice = _make_invoice(world.tenant)
        submission = _make_submission(world.tenant, invoice, world.owner)
        admin = _platform_admin("op-sep-admin@test.local")
        tenant_client = _client(world.owner, active_tenant=world.tenant.id)
        platform_client = _client(admin)
        key = "op-sep-key"

        # Operasi tenant: quotation (op=quotation, target tenant).
        resp_quote = tenant_client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations",
            {"plan_code": "silver", "term": "monthly"},
            headers={"Idempotency-Key": key},
        )
        assert resp_quote.status_code == 201
        # Operasi tenant lain: pembayaran internet (op=internet_payment_record).
        resp_pay = tenant_client.post(
            f"/api/v1/tenants/{world.tenant.id}/payments",
            {"method": "cash", "amount": "50000"},
            headers={"Idempotency-Key": key},
        )
        assert resp_pay.status_code == 201, resp_pay.content
        assert "invoice_id" not in resp_pay.json()
        # Operasi platform (op=platform_submission_approve, target platform).
        resp_approve = platform_client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": key},
        )
        assert resp_approve.status_code == 204
        # Tidak ada satupun yang saling me-replay respons operasi lain.
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 2  # invoice awal + quotation
            submission.refresh_from_db()
            assert submission.state == PaymentSubmission.State.APPROVED
        from domains.billing.models import InternetPayment

        with tenant_scope(world.tenant.id):
            assert InternetPayment.objects.count() == 1


# ---------------------------------------------------------------------------
# 4. UUID alias / malformed
# ---------------------------------------------------------------------------


class TestCanonicalIdentity:
    def test_alias_spellings_share_scope_replay(self):
        """Ejaan alias UUID (huruf besar / tanpa hyphen) dari identitas sama
        menghasilkan scope sama → replay respons logis sama."""
        world = _setup_world("alias")
        client = _client(world.owner, active_tenant=world.tenant.id)
        body = {"plan_code": "gold", "term": "monthly"}
        canonical = str(world.tenant.id)
        upper = canonical.upper()
        compact = canonical.replace("-", "")
        resp1 = client.post(f"/api/v1/tenants/{canonical}/quotations", body, headers={"Idempotency-Key": "al-1"})
        resp2 = client.post(f"/api/v1/tenants/{upper}/quotations", body, headers={"Idempotency-Key": "al-1"})
        resp3 = client.post(f"/api/v1/tenants/{compact}/quotations", body, headers={"Idempotency-Key": "al-1"})
        assert resp1.status_code == 201, resp1.content
        assert resp2.status_code == 201 and resp2.json()["invoice_id"] == resp1.json()["invoice_id"]
        assert resp3.status_code == 201 and resp3.json()["invoice_id"] == resp1.json()["invoice_id"]
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1

    def test_resource_alias_spellings_share_scope_replay(self):
        """Alias ejaan resource id (invoice huruf besar) → scope sama: replay
        mengembalikan submission yang sama, bukan duplikat upload bukti."""
        world = _setup_world("alias-res")
        invoice = _make_invoice(world.tenant)
        client = _client(world.owner, active_tenant=world.tenant.id)
        body = {"file_b64": PNG_B64, "mime": "image/png", "file_name": "bukti.png"}
        key = "al-res-1"
        first = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            body, headers={"Idempotency-Key": key},
        )
        upper = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{str(invoice.id).upper()}/payment-submissions",
            body, headers={"Idempotency-Key": key},
        )
        assert first.status_code == 201, first.content
        assert upper.status_code == 201
        assert upper.json()["submission_id"] == first.json()["submission_id"]
        with tenant_scope(world.tenant.id):
            assert PaymentSubmission.objects.count() == 1
        assert IdempotencyKey.objects.filter(idem_key=key).count() == 1

    def test_malformed_resource_uuid_422_without_claim_or_effect(self):
        world = _setup_world("malformed")
        invoice = _make_invoice(world.tenant)
        client = _client(world.owner, active_tenant=world.tenant.id)
        resp = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/not-a-uuid/payment-submissions",
            {"file_b64": PNG_B64, "mime": "image/png"},
            headers={"Idempotency-Key": "mf-1"},
        )
        assert resp.status_code == 422
        assert "resource_id" in resp.json()["field_errors"]
        # Tidak ada klaim yang tersimpan dan tidak ada efek (bukan 500).
        assert (
            IdempotencyKey.objects.filter(scope__contains=str(world.tenant.id)).count() == 0
        )
        with tenant_scope(world.tenant.id):
            assert PaymentSubmission.objects.count() == 0
        # Invoice sah tetap dapat dipakai setelahnya (key tidak terbakar).
        good = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            {"file_b64": PNG_B64, "mime": "image/png"},
            headers={"Idempotency-Key": "mf-1"},
        )
        assert good.status_code == 201, good.content


# ---------------------------------------------------------------------------
# 5. SaaS proof invoice A vs B, key/body sama
# ---------------------------------------------------------------------------


class TestSaasProofResourceScope:
    def test_same_key_proof_for_invoice_a_does_not_reach_invoice_b(self):
        world = _setup_world("proof-ab")
        invoice_a = _make_invoice(world.tenant)
        invoice_b = _make_invoice(world.tenant, plan_code="silver")
        client = _client(world.owner, active_tenant=world.tenant.id)
        key = "proof-shared"
        body = {"file_b64": PNG_B64, "mime": "image/png", "file_name": "bukti.png"}
        resp_a = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice_a.id}/payment-submissions",
            body, headers={"Idempotency-Key": key},
        )
        resp_b = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice_b.id}/payment-submissions",
            body, headers={"Idempotency-Key": key},
        )
        assert resp_a.status_code == 201, resp_a.content
        assert resp_b.status_code == 201, resp_b.content
        # Target B membuat submission sendiri — BUKAN replay respons A.
        assert resp_b.json()["submission_id"] != resp_a.json()["submission_id"]
        with tenant_scope(world.tenant.id):
            sub_a = PaymentSubmission.objects.get(id=resp_a.json()["submission_id"])
            sub_b = PaymentSubmission.objects.get(id=resp_b.json()["submission_id"])
            assert sub_a.invoice_id == invoice_a.id
            assert sub_b.invoice_id == invoice_b.id
            assert PaymentSubmission.objects.count() == 2
        # Dua scope resource berbeda → dua record idempotency.
        assert IdempotencyKey.objects.filter(idem_key=key).count() == 2


# ---------------------------------------------------------------------------
# 6. Platform operator pindah active tenant — scope platform stabil
# ---------------------------------------------------------------------------


class TestPlatformScopeStability:
    def test_active_tenant_switch_does_not_create_new_platform_scope(self):
        world = _setup_world("plat-switch", second_tenant=True)
        invoice = _make_invoice(world.tenant)
        submission = _make_submission(world.tenant, invoice, world.owner)
        admin = _platform_admin("plat-switch-admin@test.local")
        client = _client(admin, active_tenant=world.tenant.id)
        url = f"/api/v1/platform/payment-submissions/{submission.id}/approve"

        first = client.post(url, headers={"Idempotency-Key": "ps-1"})
        assert first.status_code == 204

        # Operator berpindah active tenant; replay key sama harus tetap
        # mengenali aksi platform yang sama (scope "platform" eksplisit).
        session = client.session
        session["active_tenant_id"] = str(world.tenant_b.id)
        session.save()
        replay = client.post(url, headers={"Idempotency-Key": "ps-1"})
        assert replay.status_code == 204
        with tenant_scope(world.tenant.id):
            assert PaymentSubmission.objects.filter(id=submission.id, state="approved").count() == 1
            # Satu aksi keputusan: audit/outbox/source-event masing-masing 1.
            assert AuditEvent.objects.filter(
                tenant_id=world.tenant.id, action_code="payment_submission.approve"
            ).count() == 1
            from domains.subscriptions.models import PlatformPaymentSourceEvent

            assert PlatformPaymentSourceEvent.objects.filter(submission=submission).count() == 1
            assert OutboxEvent.objects.filter(event_type="subscription.activated").count() == 1
        # Scope idempotency platform TIDAK mengikuti tenant sesi.
        assert IdempotencyKey.objects.filter(
            scope=f"platform_submission_approve:platform:{submission.id}", idem_key="ps-1"
        ).count() == 1
        assert IdempotencyKey.objects.filter(idem_key="ps-1").count() == 1

    def test_concurrent_platform_approve_single_decision(self, monkeypatch):
        """Konkurensi jalur platform (tanpa tenant_scope): dua klien admin
        dengan key sama → satu keputusan + replay; tanpa duplicate effect."""
        world = _setup_world("plat-race")
        invoice = _make_invoice(world.tenant)
        submission = _make_submission(world.tenant, invoice, world.owner)
        admin = _platform_admin("plat-race-admin@test.local")
        leader_entered = threading.Event()
        release_leader = threading.Event()
        evidence: dict = {}
        original = sub_services.decide_platform_submission
        calls = []

        def slow_decide(submission_id, decision, **kwargs):
            evidence["leader_pid"] = _pg_pid()
            calls.append(threading.get_ident())
            leader_entered.set()
            assert release_leader.wait(JOIN_TIMEOUT_S)
            return original(submission_id, decision, **kwargs)

        monkeypatch.setattr(sub_services, "decide_platform_submission", slow_decide)
        results: dict = {}

        def poster(tag):
            try:
                client = _client(admin)
                results[tag] = client.post(
                    f"/api/v1/platform/payment-submissions/{submission.id}/approve",
                    headers={"Idempotency-Key": "pr-1"},
                )
            except Exception as exc:  # pragma: no cover
                results[f"{tag}_error"] = repr(exc)
            finally:
                _close_thread_connection()

        t_leader = _run_in_thread(lambda: poster("leader"))
        assert leader_entered.wait(JOIN_TIMEOUT_S)
        t_follower = _run_in_thread(lambda: poster("follower"))
        assert (
            _wait_backend_blocked(exclude_pids=(_pg_pid(), evidence["leader_pid"])) is not None
        ), "follower tidak teramati menunggu klaim platform"
        assert "follower" not in results  # masih menunggu klaim leader
        release_leader.set()
        t_leader.join(JOIN_TIMEOUT_S)
        t_follower.join(JOIN_TIMEOUT_S)
        assert "leader_error" not in results and "follower_error" not in results
        assert results["leader"].status_code == 204, results["leader"].content
        assert results["follower"].status_code == 204, results["follower"].content
        assert len(calls) == 1
        with tenant_scope(world.tenant.id):
            assert AuditEvent.objects.filter(
                tenant_id=world.tenant.id, action_code="payment_submission.approve"
            ).count() == 1
            assert OutboxEvent.objects.filter(event_type="subscription.activated").count() == 1


# ---------------------------------------------------------------------------
# 7. Permission/session/step-up tidak sah saat replay
# ---------------------------------------------------------------------------


class TestReplayAuthorization:
    def _approved_world(self):
        world = _setup_world("replay-auth")
        client = _client(world.owner, active_tenant=world.tenant.id)
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        body = {"plan_code": "gold", "term": "monthly"}
        first = client.post(url, body, headers={"Idempotency-Key": "ra-1"})
        assert first.status_code == 201
        return world, url, body

    def test_replay_denied_without_reauth(self):
        """Sensitive step-up kedaluwarsa saat replay → 403, respons cache
        tidak bocor (initial() tetap diperiksa sebelum dekorator)."""
        world, url, body = self._approved_world()
        no_reauth = _client(world.owner, active_tenant=world.tenant.id, reauth=False)
        replay = no_reauth.post(url, body, headers={"Idempotency-Key": "ra-1"})
        assert replay.status_code == 403
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1  # aksi baru tidak dijalankan

    def test_replay_denied_after_permission_revoked(self):
        world, url, body = self._approved_world()
        Membership.objects.filter(user=world.owner, tenant=world.tenant).update(role=Role.VIEWER)
        demoted = _client(world.owner, active_tenant=world.tenant.id)
        replay = demoted.post(url, body, headers={"Idempotency-Key": "ra-1"})
        assert replay.status_code == 403
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1

    def test_replay_denied_after_membership_revoked(self):
        world, url, body = self._approved_world()
        Membership.objects.filter(user=world.owner, tenant=world.tenant).update(
            revoked_at=timezone.now()
        )
        outsider = _client(world.owner, active_tenant=world.tenant.id)
        replay = outsider.post(url, body, headers={"Idempotency-Key": "ra-1"})
        assert replay.status_code == 404  # non-member → 404 generik (§5)

    def test_replay_denied_anonymous(self):
        world, url, body = self._approved_world()
        anon = APIClient(enforce_csrf_checks=False)
        replay = anon.post(url, body, headers={"Idempotency-Key": "ra-1"})
        # Perilaku kontrak existing route tenant: IsAuthenticated + sesi
        # tanpa WWW-Authenticate menolak anonim 403 (lihat PlatformApiView
        # docstring) — yang penting: respons cache TIDAK bocor dan tidak
        # ada aksi baru.
        assert replay.status_code in (401, 403)
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1

    def test_platform_replay_denied_after_platform_role_revoked(self):
        world = _setup_world("replay-plat")
        invoice = _make_invoice(world.tenant)
        submission = _make_submission(world.tenant, invoice, world.owner)
        admin = _platform_admin("replay-plat-admin@test.local")
        client = _client(admin)
        url = f"/api/v1/platform/payment-submissions/{submission.id}/approve"
        assert client.post(url, headers={"Idempotency-Key": "rp-1"}).status_code == 204
        User.objects.filter(id=admin.id).update(platform_admin=False)
        replay = client.post(url, headers={"Idempotency-Key": "rp-1"})
        assert replay.status_code == 404  # non-platform → 404 generik (§5)
        with tenant_scope(world.tenant.id):
            assert AuditEvent.objects.filter(
                tenant_id=world.tenant.id, action_code="payment_submission.approve"
            ).count() == 1


# ---------------------------------------------------------------------------
# 8. Gagal sebelum DB commit — rollback konsisten
# ---------------------------------------------------------------------------


class TestFailureRollback:
    def test_handler_failure_rolls_back_claim_and_effects_key_not_burned(self, monkeypatch):
        world = _setup_world("rollback")
        original = sub_services.create_quotation

        def failing_create(tenant_id, plan_code, term, locale="id"):
            result = original(tenant_id, plan_code, term, locale=locale)
            raise ApiError.validation(
                {"plan_code": [{"code": "injected", "message": "injected failure"}]}
            )

        monkeypatch.setattr(sub_services, "create_quotation", failing_create)
        client = _client(world.owner, active_tenant=world.tenant.id)
        url = f"/api/v1/tenants/{world.tenant.id}/quotations"
        body = {"plan_code": "gold", "term": "monthly"}

        failed = client.post(url, body, headers={"Idempotency-Key": "rb-1"})
        assert failed.status_code == 422
        # Klaim, invoice, apapun efek handler: semua rollback.
        assert _idem_count(f"quotation:{world.tenant.id}:") == 0
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 0

        # Key tidak terbakar: permintaan ulang yang sehat mengeksekusi segar.
        monkeypatch.setattr(sub_services, "create_quotation", original)
        retried = client.post(url, body, headers={"Idempotency-Key": "rb-1"})
        assert retried.status_code == 201, retried.content
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1


# ---------------------------------------------------------------------------
# 9. Crash/interupsi setelah commit sebelum respons — protokol atomik
# ---------------------------------------------------------------------------


class TestAtomicClaimResponse:
    def test_committed_record_without_response_is_not_blindly_reexecuted(self):
        """Simulasi record in-flight/terputus TANPA respons (warisan
        pra-PA-006): permintaan ulang key+body sama DITOLAK 409 fail-safe —
        tidak dieksekusi ulang buta; business uniqueness domain tetap
        menjaga efek."""
        world = _setup_world("interrupted")
        body = {"plan_code": "gold", "term": "monthly"}
        scope = f"quotation:{world.tenant.id}:"
        IdempotencyKey.objects.create(
            principal=str(world.owner.id),
            scope=scope,
            idem_key="int-1",
            body_hash=_body_hash(body),
            created_at=timezone.now(),
        )
        client = _client(world.owner, active_tenant=world.tenant.id)
        resp = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations", body,
            headers={"Idempotency-Key": "int-1"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "idempotency_conflict"
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 0  # tidak ada efek kedua
        # Record asli tidak diubah menjadi replay.
        assert IdempotencyKey.objects.filter(scope=scope, idem_key="int-1").count() == 1

    def test_no_committed_claim_without_response_during_handler(self, monkeypatch):
        """Bukti protokol: SELAMA handler berjalan, record klaim tidak pernah
        ter-commit tanpa respons (klaim+efek+respons satu transaksi) —
        window "crash setelah commit sebelum respons tersimpan" tertutup."""
        world = _setup_world("window")
        leader_entered = threading.Event()
        release_leader = threading.Event()
        original = sub_services.create_quotation

        def slow_create(tenant_id, plan_code, term, locale="id"):
            leader_entered.set()
            assert release_leader.wait(JOIN_TIMEOUT_S)
            return original(tenant_id, plan_code, term, locale=locale)

        monkeypatch.setattr(sub_services, "create_quotation", slow_create)
        results: dict = {}

        def poster():
            try:
                client = _client(world.owner, active_tenant=world.tenant.id)
                results["resp"] = client.post(
                    f"/api/v1/tenants/{world.tenant.id}/quotations",
                    {"plan_code": "gold", "term": "monthly"},
                    headers={"Idempotency-Key": "win-1"},
                )
            except Exception as exc:  # pragma: no cover
                results["error"] = repr(exc)
            finally:
                _close_thread_connection()

        thread = _run_in_thread(poster)
        try:
            assert leader_entered.wait(JOIN_TIMEOUT_S)
            # Dari koneksi pengamat: belum ada record ter-commit sama sekali.
            scope = f"quotation:{world.tenant.id}:"
            assert _idem_count(scope) == 0
            with tenant_scope(world.tenant.id):
                assert SaaSInvoice.objects.count() == 0
        finally:
            release_leader.set()
        thread.join(JOIN_TIMEOUT_S)
        assert results["resp"].status_code == 201
        records = IdempotencyKey.objects.filter(scope=scope, idem_key="win-1")
        assert records.count() == 1
        record = records.get()
        # Setelah commit: record HADIR BERSAMA respons (tidak pernah
        # ter-commit dalam keadaan tanpa respons).
        assert record.response_status == 201
        assert record.response_body is not None


# ---------------------------------------------------------------------------
# 10. TTL dan legacy records
# ---------------------------------------------------------------------------


class TestTtlAndLegacyRecords:
    def test_expired_record_not_replayed_fresh_action_executes(self):
        world = _setup_world("ttl")
        body = {"plan_code": "gold", "term": "monthly"}
        scope = f"quotation:{world.tenant.id}:"
        IdempotencyKey.objects.create(
            principal=str(world.owner.id),
            scope=scope,
            idem_key="ttl-1",
            body_hash=_body_hash(body),
            response_status=201,
            response_body={"quotation_id": "stale", "invoice_id": "stale", "amount": "1.00"},
            created_at=timezone.now() - datetime.timedelta(days=8),
        )
        client = _client(world.owner, active_tenant=world.tenant.id)
        resp = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations", body,
            headers={"Idempotency-Key": "ttl-1"},
        )
        assert resp.status_code == 201
        # Respons stale TIDAK di-replay: aksi baru dijalankan (retensi habis).
        assert resp.json()["invoice_id"] != "stale"
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1

    def test_legacy_record_of_other_principal_never_leaks_response(self):
        world = _setup_world("legacy-other")
        body = {"plan_code": "gold", "term": "monthly"}
        scope = f"quotation:{world.tenant.id}:"
        IdempotencyKey.objects.create(
            principal=str(UUID("00000000-0000-0000-0000-000000000001")),
            scope=scope,
            idem_key="leg-1",
            body_hash=_body_hash(body),
            response_status=201,
            response_body={"quotation_id": "milik-lain", "invoice_id": "milik-lain", "amount": "1.00"},
            created_at=timezone.now(),
        )
        client = _client(world.owner, active_tenant=world.tenant.id)
        resp = client.post(
            f"/api/v1/tenants/{world.tenant.id}/quotations", body,
            headers={"Idempotency-Key": "leg-1"},
        )
        assert resp.status_code == 201
        assert resp.json()["invoice_id"] != "milik-lain"
        with tenant_scope(world.tenant.id):
            assert SaaSInvoice.objects.count() == 1

    def test_business_uniqueness_survives_ttl_on_platform_decision(self):
        """Setelah TTL idempotency habis, replay approve dengan key semula
        tetap ditolak mesin state domain (409) — business uniqueness tidak
        hilang bersama record idempotency."""
        world = _setup_world("ttl-biz")
        invoice = _make_invoice(world.tenant)
        submission = _make_submission(world.tenant, invoice, world.owner)
        admin = _platform_admin("ttl-biz-admin@test.local")
        client = _client(admin)
        url = f"/api/v1/platform/payment-submissions/{submission.id}/approve"
        assert client.post(url, headers={"Idempotency-Key": "tb-1"}).status_code == 204
        # TTL record idempotency berakhir.
        IdempotencyKey.objects.filter(idem_key="tb-1").update(
            created_at=timezone.now() - datetime.timedelta(days=8)
        )
        replay = client.post(url, headers={"Idempotency-Key": "tb-1"})
        assert replay.status_code == 409
        assert replay.json()["code"] == "conflict"  # penolakan mesin state, bukan replay
        with tenant_scope(world.tenant.id):
            assert AuditEvent.objects.filter(
                tenant_id=world.tenant.id, action_code="payment_submission.approve"
            ).count() == 1  # tidak ada keputusan kedua
