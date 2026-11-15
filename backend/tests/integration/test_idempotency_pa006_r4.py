"""Tes integrasi PA-006 — koreksi penyerahan keempat (task0010, 15 Nov 2026).

Menutup finding controller pada PR19 exact SHA 9e9bf2d (keputusan PR20):
- REV-1311-01 (P1, OPEN partial): parser migrasi 0004 menghapus penjaga
  legacy dengan ejaan UUID URN (`urn:uuid:<hex>` — URL kwargs mentah main
  memakai router <str:...>). Ditutup dengan parser scope toleran URN +
  kebijakan fail-safe (scope tak terurai DIPERTAHANKAN sebagai baris mati
  ber-penanda operasi khusus, bukan dihapus).
- REV-1311-03 (P2, OPEN partial): identitas UUID bertingkat belum konsisten
  — nested `allocations[].invoice_id` belum dinormalkan sebelum hash
  (409 palsu pada alias satu invoice logis), dan selected_account_ids yang
  canonical pada hash belum mencapai preview/payload job/consumption.
- REV-1511-05 (P1, NEW): preview validasi CSV menyalin password plaintext ke
  respons → di-cache IdempotencyKey dan direplay. Ditutup dengan proyeksi
  mask + migrasi 0005 scrub record retained.

Semua tes memakai PostgreSQL nyata via peran runtime non-superuser dan
klien HTTP terautentikasi independen (dispatch penuh), mengikuti konvensi
test_idempotency_pa006.
"""
from __future__ import annotations

import threading
import uuid as _uuid

import pytest

from domains.jobs.models import IdempotencyKey, JobDetail
from domains.subscriptions import services as sub_services
from tests.integration.test_idempotency_pa006 import (
    REAUTH_FAR_FUTURE,
    _PROOF_BODY,
    _client_for,
    _count_in_tenant,
    _idem_count,
    _world,
)
from tests.integration.test_billing_payment_concurrency import _record_payment, _setup_world

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
            "domains.documents",
            "domains.audit",
            "domains.jobs",
        ],
    ),
]


@pytest.fixture(autouse=True)
def _plans_available():
    sub_services.seed_plans()
    yield


# ---------------------------------------------------------------------------
# REV-1311-01 — legacy URN/alias scope bertahan migrasi 0004 (fail-safe)
# ---------------------------------------------------------------------------


class TestLegacyUrnMigration:
    """Actual main-shaped records (URL kwargs mentah, termasuk URN) →
    migrasi 0004 NYATA → retry HTTP → replay/penjaga tanpa efek kedua."""

    @pytest.mark.parametrize(
        "spelling", ["upper", "compact", "braced", "urn", "braced_urn"]
    )
    def test_actual_migration_tenant_alias_spellings_retry_replays_original(
        self, spelling
    ):
        """Old-code upload dengan ejaan tenant non-canonical (UPPER/compact/
        braced/URN/braced-URN — semua ejaan kwargs URL valid main yang
        diterima stdlib uuid.UUID) → migrasi 0004 → retry key/body sama
        mengembalikan submission semula; submission tetap 1."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world(f"rtrw-r4-urn-{spelling}")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r4-urn", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        tenant_id = str(world.tenant.id)
        spelling_value = {
            "upper": tenant_id.upper(),
            "compact": _uuid.UUID(tenant_id).hex,
            "braced": "{" + tenant_id + "}",
            "urn": "urn:uuid:" + tenant_id,
            "braced_urn": "{urn:uuid:" + tenant_id + "}",
        }[spelling]
        # Scope era main: kwargs URL MENTAH (termasuk bentuk berkolon URN).
        old_scope = f"payment_submission:{spelling_value}:"

        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id), scope=old_scope,
            idem_key=f"r4-urn-{spelling}",
            body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body=response_old, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        # Penjaga TIDAK dihapus; identitas dikanonikalisasi ke tenant canonical.
        migrated = IdempotencyKey.objects.get(idem_key=f"r4-urn-{spelling}")
        assert migrated.tenant_scope == tenant_id
        assert migrated.operation == "payment_submission"
        assert migrated.resource == ""

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": f"r4-urn-{spelling}"},
        )
        assert retry.status_code == 201, "known legacy success must replay its original result"
        assert retry.json() == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    @pytest.mark.parametrize("spelling", ["upper", "compact", "braced", "urn", "braced_urn"])
    def test_actual_migration_tenant_alias_ambiguous_no_response_stays_guarded(self, spelling):
        """Ejaan tenant alias + crash-window lama (domain terkomit, respons
        absen) → migrasi mempertahankan penjaga; retry ditolak 409 aman,
        bukan eksekusi ulang buta (semua ejaan alias — paritas completed)."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world(f"rtrw-r4-ambig-{spelling}")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r4-ambig", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        tenant_id = str(world.tenant.id)
        spelling_value = {
            "upper": tenant_id.upper(),
            "compact": _uuid.UUID(tenant_id).hex,
            "braced": "{" + tenant_id + "}",
            "urn": "urn:uuid:" + tenant_id,
            "braced_urn": "{urn:uuid:" + tenant_id + "}",
        }[spelling]
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"payment_submission:{spelling_value}:",
            idem_key=f"r4-ambig-{spelling}", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=None, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": f"r4-ambig-{spelling}"},
        )
        assert retry.status_code == 409
        assert retry.json()["code"] == "idempotency_conflict"
        # Penjaga tetap ada; submission/file tetap satu.
        assert _idem_count(idem_key=f"r4-ambig-{spelling}") == 1
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    def test_actual_migration_urn_resource_platform_decision_replays(self):
        """Scope legacy dengan RESOURCE ber-URN (mis. keputusan platform
        `platform_submission_approve:<tenant>:urn:uuid:<sub>`) → migrasi
        menormalkan resource canonical → retry MEREPLAY 204 tanpa keputusan
        baru."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r4-urn-res")
        admin = _platform_admin_for("platform-r4-urn@test.local")
        submission = _platform_submission_for(world, state=PaymentSubmission.State.APPROVED)
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(admin.id),
            scope=f"platform_submission_approve:{world.tenant.id}:urn:uuid:{submission.id}",
            idem_key="r4-urn-res", body_hash=_legacy_body_hash(None),
            response_status=204, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        record = IdempotencyKey.objects.get(idem_key="r4-urn-res")
        assert record.tenant_scope == "platform"  # remap operasi platform
        assert record.resource == str(submission.id)  # URN → canonical

        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent

        client = _client_for(admin, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "r4-urn-res"},
        )
        assert response.status_code == 204  # replay, bukan keputusan baru
        assert _idem_count(idem_key="r4-urn-res") == 1
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 0
        assert _count_in_tenant(
            AuditEvent, world.tenant.id, action_code="payment_submission.approve"
        ) == 0

    def test_actual_migration_urn_tenant_concurrent_retry_both_replay_original(self):
        """Retry konkuren pasca-migrasi pada penjaga URN legacy: kedua klien
        independen MEREPLAY submission semula (bukan duplicate write/500)."""
        from django.db import connection as conn
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r4-urn-conc")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r4-conc", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection=conn)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"payment_submission:urn:uuid:{world.tenant.id}:",
            idem_key="r4-urn-conc", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body=response_old, created_at=timezone.now(),
        )
        MigrationExecutor(connection=conn).migrate([("jobs", "0004_idempotency_identity")])

        url = f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions"
        results: dict[str, dict] = {}
        barrier = threading.Barrier(2, timeout=30)

        def run(tag):
            try:
                client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
                barrier.wait()
                response = client.post(url, _PROOF_BODY, headers={"Idempotency-Key": "r4-urn-conc"})
                results[tag] = {"status": response.status_code, "data": response.json()}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        threads = [threading.Thread(target=run, args=("A",)), threading.Thread(target=run, args=("B",))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=45)
        for tag, res in results.items():
            assert "exception" not in res, (tag, res)
            assert res["status"] == 201
            assert res["data"] == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        assert _idem_count(operation="payment_submission", idem_key="r4-urn-conc") == 1


def _make_invoice_for(world):
    from tests.integration.test_idempotency_pa006 import _make_invoice

    return _make_invoice(world)


def _platform_admin_for(email: str):
    from tests.integration.test_idempotency_pa006 import _platform_admin

    return _platform_admin(email)


def _platform_submission_for(world, *, state):
    from tests.integration.test_idempotency_pa006 import _make_platform_submission

    return _make_platform_submission(world, state=state)


def _legacy_body_hash(body):
    from tests.integration.test_idempotency_pa006 import _body_hash_legacy_of

    return _body_hash_legacy_of(body)


# ---------------------------------------------------------------------------
# REV-1311-03A — nested money identity: allocations[].invoice_id
# ---------------------------------------------------------------------------


class TestNestedAllocationUuidIdentity:
    """Verifikasi dana (internet_payment_verify): ejaan alias UUID pada
    `allocations[].invoice_id` adalah SATU invoice logis — hash v2
    bertingkat membuat alias mereplay aksi semula (bukan 409 palsu)."""

    def test_nested_allocation_uuid_alias_replays_original_verification(self):
        from domains.audit.models import AuditEvent
        from domains.billing.models import PaymentAllocation
        from domains.documents.models import IssuedDocument
        from domains.jobs.models import OutboxEvent

        world = _setup_world("r4-nested-alias", invoice_totals=["100000"])
        payment = _record_payment(world, "100000")
        client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        body = {"allocations": [{"invoice_id": str(world.invoices[0].id), "amount": "100000"}]}
        alias_body = {
            "allocations": [{"invoice_id": world.invoices[0].id.hex.upper(), "amount": "100000"}]
        }
        headers = {"Idempotency-Key": "r4-nested-alias"}

        first = client.post(url, body, format="json", headers=headers)
        alias = client.post(url, alias_body, format="json", headers=headers)
        identical = client.post(url, body, format="json", headers=headers)

        assert first.status_code == identical.status_code == 200
        assert first.json() == identical.json()
        assert alias.status_code == 200, "typed nested UUID alias must replay the same logical verification"
        assert alias.json() == first.json()
        assert _count_in_tenant(PaymentAllocation, world.tenant.id, payment=payment.id) == 1
        assert _count_in_tenant(IssuedDocument, world.tenant.id, ref_id=str(payment.id)) == 1
        assert _count_in_tenant(
            AuditEvent, world.tenant.id, target_id=payment.id, action_code="internet_payment.verified"
        ) == 1
        assert OutboxEvent.objects.filter(
            aggregate_id=payment.id, event_type="internet_payment.verified"
        ).count() == 1

    def test_nested_allocation_alias_first_then_canonical_replays(self):
        world = _setup_world("r4-nested-alias-first", invoice_totals=["100000"])
        payment = _record_payment(world, "100000")
        client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        alias_body = {
            "allocations": [{"invoice_id": "urn:uuid:" + str(world.invoices[0].id), "amount": "100000"}]
        }
        canonical_body = {
            "allocations": [{"invoice_id": str(world.invoices[0].id), "amount": "100000"}]
        }
        headers = {"Idempotency-Key": "r4-alias-first"}

        first = client.post(url, alias_body, format="json", headers=headers)
        retry = client.post(url, canonical_body, format="json", headers=headers)

        assert first.status_code == retry.status_code == 200
        assert first.json() == retry.json()

    def test_nested_allocation_genuinely_different_target_conflicts(self):
        from domains.billing.models import PaymentAllocation

        world = _setup_world("r4-nested-conflict", invoice_totals=["100000", "100000"])
        payment = _record_payment(world, "100000")
        client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        headers = {"Idempotency-Key": "r4-nested-conflict"}

        first = client.post(
            url,
            {"allocations": [{"invoice_id": str(world.invoices[0].id), "amount": "100000"}]},
            format="json", headers=headers,
        )
        different = client.post(
            url,
            {"allocations": [{"invoice_id": str(world.invoices[1].id), "amount": "100000"}]},
            format="json", headers=headers,
        )
        different_amount = client.post(
            url,
            {"allocations": [{"invoice_id": world.invoices[0].id.hex.upper(), "amount": "50000"}]},
            format="json", headers=headers,
        )

        assert first.status_code == 200
        assert different.status_code == 409
        assert different.json()["code"] == "idempotency_conflict"
        assert different_amount.status_code == 409
        assert different_amount.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentAllocation, world.tenant.id, payment=payment.id) == 1

    def test_nested_allocation_malformed_invoice_id_422(self):
        world = _setup_world("r4-nested-malformed", invoice_totals=["100000"])
        payment = _record_payment(world, "100000")
        client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        response = client.post(
            url,
            {"allocations": [{"invoice_id": "bukan-uuid", "amount": "100000"}]},
            format="json", headers={"Idempotency-Key": "r4-nested-malformed"},
        )
        assert response.status_code == 422

    def test_nested_allocation_retained_raw_hash_record_alias_replays(self):
        """Record era main (hash v1 raw, body asli canonical) + retry ejaan
        alias → v2(alias) == v1(canonical asli) → replay aksi semula."""
        from django.utils import timezone
        from domains.billing.models import PaymentAllocation

        world = _setup_world("r4-nested-retained", invoice_totals=["100000"])
        payment = _record_payment(world, "100000")
        client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        canonical_body = {
            "allocations": [{"invoice_id": str(world.invoices[0].id), "amount": "100000"}]
        }
        response_old = {"state": "verified"}  # placeholder; isi tidak dipakai domain
        IdempotencyKey.objects.create(
            principal=str(world.admin.id), tenant_scope=str(world.tenant.id),
            operation="internet_payment_verify", resource=str(payment.id),
            idem_key="r4-nested-retained",
            body_hash=_legacy_body_hash(canonical_body),
            response_status=200, response_body=response_old, created_at=timezone.now(),
        )
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        alias_body = {
            "allocations": [{"invoice_id": world.invoices[0].id.hex.upper(), "amount": "100000"}]
        }
        retry = client.post(url, alias_body, format="json", headers={"Idempotency-Key": "r4-nested-retained"})
        assert retry.status_code == 200
        assert retry.json() == response_old
        assert _count_in_tenant(PaymentAllocation, world.tenant.id, payment=payment.id) == 0

    def test_nested_allocation_reordered_array_is_different_body(self):
        """Semantik urutan array dipertahankan (REV-1311-03: jangan
        mengurutkan arrays): alokasi sama dengan URUTAN berbeda = body
        berbeda → 409 tanpa efek kedua; efek tetap satu."""
        from domains.billing.models import PaymentAllocation

        world = _setup_world("r4-nested-order", invoice_totals=["60000", "40000"])
        payment = _record_payment(world, "100000")
        client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        headers = {"Idempotency-Key": "r4-nested-order"}
        a = {"invoice_id": str(world.invoices[0].id), "amount": "60000"}
        b = {"invoice_id": str(world.invoices[1].id), "amount": "40000"}

        first = client.post(url, {"allocations": [a, b]}, format="json", headers=headers)
        reordered = client.post(url, {"allocations": [b, a]}, format="json", headers=headers)

        assert first.status_code == 200
        assert reordered.status_code == 409
        assert reordered.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentAllocation, world.tenant.id, payment=payment.id) == 2
        assert _idem_count(operation="internet_payment_verify", idem_key="r4-nested-order") == 1

    def test_concurrent_http_nested_alias_body_contender_replays_leader(self):
        """Same-key konkuren, leader body canonical, penantang body alias
        (satu invoice logis): penantang menunggu klaim INSERT lalu MEREPLAY
        respons leader — bukan 409 permanen, bukan efek ganda."""
        from domains.billing.models import PaymentAllocation

        world = _setup_world("r4-nested-conc", invoice_totals=["100000"])
        payment = _record_payment(world, "100000")
        url = f"/api/v1/tenants/{world.tenant.id}/payments/{payment.id}/verify"
        canonical_body = {
            "allocations": [{"invoice_id": str(world.invoices[0].id), "amount": "100000"}]
        }
        alias_body = {
            "allocations": [{"invoice_id": world.invoices[0].id.hex.upper(), "amount": "100000"}]
        }
        results: dict[str, dict] = {}
        barrier = threading.Barrier(2, timeout=30)

        def run(tag, body):
            from django.db import connection as conn

            try:
                client = _client_for(world.admin, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
                barrier.wait()
                response = client.post(
                    url, body, format="json", headers={"Idempotency-Key": "r4-nested-conc"}
                )
                results[tag] = {"status": response.status_code, "data": response.json()}
            except Exception as exc:  # noqa: BLE001
                results[tag] = {"exception": f"{type(exc).__name__}: {exc}"}
            finally:
                conn.close()

        threads = [
            threading.Thread(target=run, args=("leader", canonical_body)),
            threading.Thread(target=run, args=("contender", alias_body)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        for tag, res in results.items():
            assert "exception" not in res, (tag, res)
            assert res["status"] == 200, (tag, res)
        assert results["leader"]["data"] == results["contender"]["data"]
        assert _count_in_tenant(PaymentAllocation, world.tenant.id, payment=payment.id) == 1
        assert _idem_count(operation="internet_payment_verify", idem_key="r4-nested-conc") == 1


# ---------------------------------------------------------------------------
# REV-1311-03B — selected_account_ids canonical pada hash, preview, payload
# ---------------------------------------------------------------------------


class TestMigrationCommitSelectedCanonical:
    """Selected alias dan canonical menghasilkan preview/payload/effect yang
    sama dan SATU job (REV-1311-03B)."""

    def _setup_session(self, namespace: str):
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import MigrationSession
        from domains.network.models import DiscoveryObject, DiscoverySnapshot, Router

        world = _world(namespace)
        with tenant_scope(world.tenant.id):
            router = Router.objects.create(
                tenant=world.tenant, display_name="Synthetic R4", router_code=f"r4-{namespace}"
            )
            snapshot = DiscoverySnapshot.objects.create(
                tenant=world.tenant, router=router, status=DiscoverySnapshot.Status.SUCCEEDED
            )
            obj = DiscoveryObject.objects.create(
                tenant=world.tenant, router=router, snapshot=snapshot,
                username=f"r4.{namespace}", kind=DiscoveryObject.Kind.PPPOE,
            )
            session = MigrationSession.objects.create(
                tenant=world.tenant, router=router, snapshot=snapshot,
                state=MigrationSession.State.DISCOVERED,
            )
        return world, session, obj

    def test_selected_alias_and_canonical_same_preview_payload_single_job(self):
        from domains.customers.services import preview_migration_summary

        world, session, obj = self._setup_session("rtrw-r4-selected")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)

        from domains.common.tenant_context import tenant_scope

        with tenant_scope(world.tenant.id):
            canonical_counts = preview_migration_summary(session, [str(obj.id)])
        assert canonical_counts["to_create"] == 1

        alias_body = {"selected_account_ids": [obj.id.hex.upper()]}
        canonical_body = {"selected_account_ids": [str(obj.id)]}
        url = f"/api/v1/tenants/{world.tenant.id}/migrations/{session.id}/commit"
        headers = {"Idempotency-Key": "r4-selected-alias"}

        first = client.post(url, alias_body, format="json", headers=headers)
        retry = client.post(url, canonical_body, format="json", headers=headers)

        assert first.status_code == retry.status_code == 202
        assert first.json() == retry.json()
        with tenant_scope(world.tenant.id):
            session.refresh_from_db()
            detail = JobDetail.objects.get(job_id=first.json()["job_id"])
        # Preview/payload/effect identitas canonical — bukan raw alias.
        assert session.counts["to_create"] == 1
        assert session.counts["unchanged"] == 0
        assert detail.payload["selected_account_ids"] == [str(obj.id)]
        assert _idem_count(operation="migration_commit", idem_key="r4-selected-alias") == 1

    def test_selected_reordered_array_is_different_body(self):
        """Urutan selected_account_ids signifikan (jangan mengurutkan array):
        reorder = body berbeda → 409; satu job/efek tetap."""
        from domains.common.tenant_context import tenant_scope
        from domains.network.models import DiscoveryObject

        world, session, obj = self._setup_session("rtrw-r4-selected-order")
        with tenant_scope(world.tenant.id):
            obj2 = DiscoveryObject.objects.create(
                tenant=world.tenant, router=session.router, snapshot=session.snapshot,
                username="r4.order.second", kind=DiscoveryObject.Kind.PPPOE,
            )
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/migrations/{session.id}/commit"
        headers = {"Idempotency-Key": "r4-selected-order"}

        first = client.post(
            url,
            {"selected_account_ids": [str(obj.id), str(obj2.id)]},
            format="json", headers=headers,
        )
        reordered = client.post(
            url,
            {"selected_account_ids": [str(obj2.id), str(obj.id)]},
            format="json", headers=headers,
        )

        assert first.status_code == 202
        assert reordered.status_code == 409
        assert reordered.json()["code"] == "idempotency_conflict"
        assert _idem_count(operation="migration_commit", idem_key="r4-selected-order") == 1

    def test_selected_malformed_uuid_422(self):
        world, session, obj = self._setup_session("rtrw-r4-selected-bad")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = f"/api/v1/tenants/{world.tenant.id}/migrations/{session.id}/commit"
        response = client.post(
            url,
            {"selected_account_ids": ["bukan-uuid"]},
            format="json", headers={"Idempotency-Key": "r4-selected-bad"},
        )
        assert response.status_code == 422

    def test_selected_service_consumption_canonicalizes_alias_ids(self):
        """Konsumsi domain (preview + commit) menormalkan ejaan alias —
        menutup payload job lama yang menyimpan ejaan mentah."""
        from domains.customers.services import commit_migration, preview_migration_summary
        from domains.common.tenant_context import tenant_scope

        world, session, obj = self._setup_session("rtrw-r4-selected-svc")
        with tenant_scope(world.tenant.id):
            alias_counts = preview_migration_summary(session, [obj.id.hex.upper()])
            canonical_counts = preview_migration_summary(session, [str(obj.id)])
            assert alias_counts == canonical_counts
            assert alias_counts["to_create"] == 1
            # Payload era lama (raw alias) → commit mengenai objek yang sama.
            summary = commit_migration(session, selected_ids=[obj.id.hex.upper()])
        assert summary["to_create"] == 1
        assert summary["unchanged"] == 0
        from domains.customers.models import AccessAccount

        assert _count_in_tenant(
            AccessAccount, world.tenant.id, username=f"r4.rtrw-r4-selected-svc"
        ) == 1


# ---------------------------------------------------------------------------
# REV-1511-05 — preview CSV/validasi bebas plaintext credential
# ---------------------------------------------------------------------------


class TestCsvSecretFreeCache:
    """Respons validasi CSV, cache idempotency, dan replay TIDAK memuat
    plaintext password (ARCHITECTURE §5 no-plaintext-cache); penanda
    menyatakan keberadaan kredensial tanpa nilainya."""

    _SENTINEL_ROWS = [
        {"username": "r4.synthetic", "password": "SENTINEL-PLACEHOLDER", "kind": "pppoe", "customer_name": "Syn"},
    ]

    def test_csv_validation_response_and_cache_secret_free(self):
        import secrets

        sentinel = secrets.token_urlsafe(24)
        rows = [{**self._SENTINEL_ROWS[0], "password": sentinel}]
        world = _world("rtrw-r4-secret-cache")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)

        created = client.post(
            f"/api/v1/tenants/{world.tenant.id}/imports",
            {"mode": "create", "file_name": "synthetic.csv", "rows": rows},
            format="json", headers={"Idempotency-Key": "r4-secret-create"},
        )
        assert created.status_code == 201
        url = f"/api/v1/tenants/{world.tenant.id}/imports/{created.json()['id']}/validate"
        headers = {"Idempotency-Key": "r4-secret-validate"}

        import json as _json

        first = client.post(url, format="json", headers=headers)
        replay = client.post(url, format="json", headers=headers)
        record = IdempotencyKey.objects.get(idem_key="r4-secret-validate")

        assert first.status_code == replay.status_code == 200
        assert first.json() == replay.json()
        # Initial/cached/replayed respons bebas sentinel; penanda hadir.
        assert sentinel not in _json.dumps(first.json())
        assert sentinel not in _json.dumps(record.response_body)
        assert sentinel not in _json.dumps(replay.json())
        assert first.json()["preview"][0]["password"] == "********"
        assert first.json()["preview"][0]["username"] == "r4.synthetic"
        # Efek tidak ganda: satu record, replay sama, tanpa eksekusi ulang.
        assert _idem_count(operation="csv_import_validate", idem_key="r4-secret-validate") == 1

    def test_csv_validation_rows_without_password_untouched(self):
        world = _world("rtrw-r4-secret-plain")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        rows = [{"username": "r4.nopass", "kind": "hotspot", "customer_name": "NoPass"}]
        created = client.post(
            f"/api/v1/tenants/{world.tenant.id}/imports",
            {"mode": "create", "file_name": "plain.csv", "rows": rows},
            format="json", headers={"Idempotency-Key": "r4-secret-plain"},
        )
        assert created.status_code == 201
        response = client.post(
            f"/api/v1/tenants/{world.tenant.id}/imports/{created.json()['id']}/validate",
            format="json", headers={"Idempotency-Key": "r4-secret-plain-v"},
        )
        assert response.status_code == 200
        assert response.json()["preview"][0] == rows[0]

    def test_csv_retained_plaintext_cache_scrubbed_by_migration_0005(self):
        """Record retained era pra-koreksi (plaintext di response_body) →
        migrasi 0005 mensterilkan proyeksi TANPA menghapus penjaga; replay
        pasca-migrasi mengembalikan hasil nonsecret yang sama."""
        import secrets

        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone

        sentinel = secrets.token_urlsafe(24)
        world = _world("rtrw-r4-secret-mig")
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        rows = [{"username": "r4.mig", "password": sentinel, "kind": "pppoe"}]
        created = client.post(
            f"/api/v1/tenants/{world.tenant.id}/imports",
            {"mode": "create", "file_name": "mig.csv", "rows": rows},
            format="json", headers={"Idempotency-Key": "r4-secret-mig-create"},
        )
        assert created.status_code == 201
        import_id = created.json()["id"]

        # Record retained PRA-KOREKSI: respons menyimpan preview plaintext.
        legacy_response = {
            "total_rows": 1, "valid_rows": 1, "error_rows": 0, "row_errors": [],
            "preview": [rows[0]],
        }
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0004_idempotency_identity")])  # 0005 → unapplied
        IdempotencyKey.objects.create(
            principal=str(world.owner.id), tenant_scope=str(world.tenant.id),
            operation="csv_import_validate", resource=str(import_id),
            idem_key="r4-secret-mig-v", body_hash=_legacy_body_hash(None),
            response_status=200, response_body=legacy_response, created_at=timezone.now(),
        )
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0005_idempotency_scrub_secret_preview")])

        record = IdempotencyKey.objects.get(idem_key="r4-secret-mig-v")
        import json as _json

        assert sentinel not in _json.dumps(record.response_body)
        assert record.response_status == 200  # penjaga tidak dihapus/dibuka ulang
        assert record.response_body["preview"][0]["password"] == "********"
        assert record.response_body["preview"][0]["username"] == "r4.mig"

        # Replay pasca-scrub: hasil logis nonsecret, tanpa eksekusi ulang.
        replay = client.post(
            f"/api/v1/tenants/{world.tenant.id}/imports/{import_id}/validate",
            format="json", headers={"Idempotency-Key": "r4-secret-mig-v"},
        )
        assert replay.status_code == 200
        assert replay.json() == record.response_body
        assert sentinel not in _json.dumps(replay.json())
        assert _idem_count(operation="csv_import_validate", idem_key="r4-secret-mig-v") == 1
