"""Tes integrasi PA-006 — koreksi kelima: REV-1311-01 grammar penuh (16 Nov 2026).

Menutup sisa finding controller R4 pada PR21 exact SHA 634da42 (keputusan
PR23, report/controller/20261115T053138Z-0010-pa006-r4-review.md):

Parser 0004 versi cacat hanya mengenali `urn:uuid:` tetap / dua segmen
polos. Padahal writer baseline menyimpan kwargs URL MENTAH dan view baseline
mengonversinya dengan stdlib uuid.UUID — yang MENERIMA ejaan `uuid:<hex>`,
`urn:<hex>` (tanpa `uuid`), prefix berulang `urn:uuid:uuid:<hex>`,
`urn:urn:uuid:<hex>` di posisi tenant MAUPUN resource. Ejaan itu jatuh ke
baris mati `__unparsed__` → penjaga hilang → lookup canonical melewatinya →
retry pasca-upgrade membuat submission + file fisik KEDUA (bukti live
controller: 1→2, tiga varian FAIL).

Ditutup dengan parser GRAMMAR-DRIVEN (koreksi minimum R4): kandidat
pemisahan = semua posisi kolon; validitas tenant/resource menurut uuid.UUID
yang sama persis dengan writer baseline (tenant boleh literal `platform`);
interpretasi sah unik terbukti; >1 interpretasi = fail-stop migrasi atomik
(AmbiguousLegacyScope), bukan tebak/baris mati.

Semua tes integrasi memakai PostgreSQL nyata via peran runtime
non-superuser, migrasi NYATA (MigrationExecutor turun ke 0003 lalu naik
melalui 0004), dan klien HTTP terautentikasi independen (dispatch penuh).
"""
from __future__ import annotations

import importlib
import threading
import uuid as _uuid

import pytest

from domains.jobs.models import IdempotencyKey
from domains.subscriptions import services as sub_services
from tests.integration.test_idempotency_pa006 import (
    REAUTH_FAR_FUTURE,
    _PROOF_BODY,
    _body_hash_of,
    _client_for,
    _count_in_tenant,
    _idem_count,
    _world,
)

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


def _migration_module():
    return importlib.import_module("domains.jobs.migrations.0004_idempotency_identity")


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


# Ejaan UUID yang DITERIMA grammar writer baseline (stdlib uuid.UUID) dan
# pernah gagal dipetakan parser 0004 versi cacat (matriks controller R4:
# parser-matrix.json — 8 kombinasi prefix-position FAIL). mixed/uuid_repeat
# adalah kasus property tambahan (prefix berulang tanpa `urn`/campuran).
PREFIX_SPELLINGS = {
    "uuid_only": lambda v: "uuid:" + v,
    "urn_only": lambda v: "urn:" + v,
    "repeat_uuid": lambda v: "urn:uuid:uuid:" + v,
    "repeat_urn": lambda v: "urn:urn:uuid:" + v,
    "mixed": lambda v: "uuid:urn:uuid:" + v,
    "uuid_repeat": lambda v: "uuid:uuid:" + v,
}

# Kontrol ejaan standar (sudah PASS pada parser lama — harus tetap PASS).
CONTROL_SPELLINGS = {
    "canonical": lambda v: v,
    "upper": lambda v: v.upper(),
    "compact": lambda v: _uuid.UUID(v).hex,
    "braced": lambda v: "{" + v + "}",
    "urn": lambda v: "urn:uuid:" + v,
    "braced_urn": lambda v: "{urn:uuid:" + v + "}",
}

ALL_SPELLINGS = {**CONTROL_SPELLINGS, **PREFIX_SPELLINGS}


# ---------------------------------------------------------------------------
# 1. Matriks grammar parser — unit (tanpa DB), mencerminkan parser-matrix R4
# ---------------------------------------------------------------------------


class TestGrammarParserMatrix:
    """Semua ejaan yang diterima uuid.UUID (grammar writer baseline) HARUS
    terurai menjadi identitas canonical pada KEDUA posisi — termasuk 8
    kombinasi prefix yang FAIL pada parser 0004 versi cacat."""

    @pytest.mark.parametrize("spelling", sorted(ALL_SPELLINGS))
    @pytest.mark.parametrize("position", ["tenant", "resource"])
    def test_all_baseline_accepted_spellings_map_to_canonical_identity(
        self, spelling, position
    ):
        m = _migration_module()
        value = "abcdef12-2345-6789-abcd-ef1234567890"
        other = "fedcba98-7654-3210-abcd-ef1234567890"
        spelled = ALL_SPELLINGS[spelling](value)
        # Precondition: grammar baseline (stdlib) memang menerima ejaan ini.
        assert str(_uuid.UUID(spelled)) == value
        scope = (
            f"payment_submission:{spelled}:"
            if position == "tenant"
            else f"router_backup:{other}:{spelled}"
        )
        parts = m._split_legacy_scope(scope)
        assert parts is not None, f"{spelling}/{position}: ejaan diterima writer tapi tak terurai"
        operation, tenant_raw, resource_raw = parts
        assert operation == ("payment_submission" if position == "tenant" else "router_backup")
        if position == "tenant":
            assert m._canonical_uuid(tenant_raw) == value
            assert resource_raw == ""
        else:
            assert m._canonical_uuid(tenant_raw) == other
            assert m._canonical_uuid(resource_raw) == value

    def test_grammar_mirrors_stdlib_acceptance_and_rejection(self):
        """_canonical_uuid == uuid.UUID persis: terima yang diterima stdlib,
        tolak yang ditolak stdlib (tidak ada grammar lain yang menyelundup)."""
        m = _migration_module()
        v = "abcdef12-2345-6789-abcd-ef1234567890"
        accepted = [ALL_SPELLINGS[s](v) for s in ALL_SPELLINGS]
        rejected = [
            "URN:UUID:" + v,  # prefix huruf besar — replace stdlib case-sensitif
            v + "  ",  # spasi — gagal len-check
            "abcdef1223456789abcdef123456789_",  # underscore — len 33
            "not-a-uuid",
            "",
            "uuid",
            "urn",
        ]
        for s in accepted:
            assert m._canonical_uuid(s) == v, s
        for s in rejected:
            with pytest.raises((ValueError, AttributeError, TypeError)):
                _uuid.UUID(s)
            assert m._canonical_uuid(s) is None, s

    def test_platform_literal_tenant_position_is_valid(self):
        """Literal fallback writer `platform` sah di posisi tenant (bukan
        UUID); tidak sah di posisi resource operasi UUID."""
        m = _migration_module()
        v = "abcdef12-2345-6789-abcd-ef1234567890"
        parts = m._split_legacy_scope(f"platform_submission_approve:platform:{v}")
        assert parts == ("platform_submission_approve", "platform", v)
        # Resource 'platform' untuk operasi UUID-resource → tidak ada split sah.
        assert m._split_legacy_scope(f"router_backup:{v}:platform") is None

    def test_platform_literal_is_exact_case_only(self):
        """Writer lama hanya menulis literal \"platform\" lowercase (kwargs
        URL non-UUID ditolak view baseline sebelum efek). 'PLATFORM' huruf
        besar bukan keluaran writer sah → tidak diberi split hidup
        (REV-R5-01: baris garbage tidak boleh menjadi guard no-response
        yang tampak sah)."""
        m = _migration_module()
        v = "abcdef12-2345-6789-abcd-ef1234567890"
        assert m._split_legacy_scope(f"platform_submission_approve:PLATFORM:{v}") is None
        assert m._split_legacy_scope(f"platform_submission_approve:Platform:{v}") is None
        assert m._split_legacy_scope(f"router_backup:PLATFORM:{v}") is None

    def test_opaque_operation_resource_is_verbatim_remainder(self):
        """Operasi opaque (identity_conflict_resolve): resource = sisa apa pun
        setelah tenant sah (group_id sha256[:16]), termasuk bila tenant
        ber-ejaan prefix."""
        m = _migration_module()
        v = "abcdef12-2345-6789-abcd-ef1234567890"
        for spelling in PREFIX_SPELLINGS:
            spelled = PREFIX_SPELLINGS[spelling](v)
            parts = m._split_legacy_scope(
                f"identity_conflict_resolve:{spelled}:0f1e2d3c4b5a6978"
            )
            assert parts == ("identity_conflict_resolve", spelled, "0f1e2d3c4b5a6978")

    def test_genuinely_unresolvable_input_returns_none(self):
        """Input yang tidak mungkin ditulis writer baseline sah (view baseline
        menolak kwargs non-UUID sebelum efek) → None → baris mati, bukan
        exception, bukan tebakan."""
        m = _migration_module()
        v = "abcdef12-2345-6789-abcd-ef1234567890"
        assert m._split_legacy_scope("payment_submission:zz:not-a-uuid:x:") is None
        assert m._split_legacy_scope("payment_submission") is None
        assert m._split_legacy_scope("payment_submission:URN:UUID:" + v + ":") is None
        assert m._split_legacy_scope("payment_submission:" + v) is None  # tanpa kolon resource
        assert m._split_legacy_scope("") is None
        assert m._split_legacy_scope(None) is None

    def test_ambiguous_interpretation_fail_stops(self):
        """>1 interpretasi sah = mustahil pada grammar baseline (bukti pada
        docstring parser); disuntik validator permisif untuk membuktikan
        jalur fail-stop AmbiguousLegacyScope, bukan tebak/baris mati."""
        m = _migration_module()
        with pytest.raises(m.AmbiguousLegacyScope):
            m._split_legacy_scope(
                "op:a:b:c", tenant_valid=lambda p: True, resource_valid=lambda p: True
            )
        # Grammar produksi: kasus yang sama TIDAK ambigu (tidak ada yang sah).
        assert m._split_legacy_scope("op:a:b:c") is None


# ---------------------------------------------------------------------------
# 2. Migrasi NYATA — ejaan prefix tenant (kasus FAIL live controller)
# ---------------------------------------------------------------------------


class TestPrefixTenantSpellingMigration:
    """Old-writer scope dengan ejaan prefix tenant (uuid:/urn:/berulang) →
    migrasi 0004 nyata → identitas canonical → retry HTTP kanonik."""

    @pytest.mark.parametrize("spelling", sorted(PREFIX_SPELLINGS))
    def test_completed_retry_replays_original_single_submission(self, spelling):
        """Varian FAIL controller (completed uuid:/urn:): record legacy
        ber-respons 201 → migrasi menormalkan identitas → retry key/body sama
        MEREPLAY respons semula; submission tetap 1 (bukan 2), record 1."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world(f"rtrw-r5-{spelling}")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r5", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        tenant_id = str(world.tenant.id)
        spelled = PREFIX_SPELLINGS[spelling](tenant_id)
        old_scope = f"payment_submission:{spelled}:"

        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id), scope=old_scope,
            idem_key=f"r5-{spelling}",
            body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body=response_old, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        # Penjaga TIDAK jadi baris mati; identitas dikanonikalisasi penuh.
        migrated = IdempotencyKey.objects.get(idem_key=f"r5-{spelling}")
        assert migrated.operation == "payment_submission", "penjaga valid jadi __unparsed__"
        assert migrated.tenant_scope == tenant_id
        assert migrated.resource == ""

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": f"r5-{spelling}"},
        )
        assert retry.status_code == 201, "known legacy success must replay its original result"
        assert retry.json() == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        assert _idem_count(operation="payment_submission", idem_key=f"r5-{spelling}") == 1

    @pytest.mark.parametrize("spelling", sorted(PREFIX_SPELLINGS))
    def test_crash_window_no_response_stays_guarded_409(self, spelling):
        """Varian FAIL controller (ambiguous uuid:/urn: — domain terkomit,
        respons absen): migrasi mempertahankan penjaga; retry ditolak 409
        aman, TIDAK mengeksekusi ulang buta (submission tetap 1)."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world(f"rtrw-r5-cw-{spelling}")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r5-cw", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        spelled = PREFIX_SPELLINGS[spelling](str(world.tenant.id))
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"payment_submission:{spelled}:",
            idem_key=f"r5-cw-{spelling}", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=None, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": f"r5-cw-{spelling}"},
        )
        assert retry.status_code == 409
        assert retry.json()["code"] == "idempotency_conflict"
        assert _idem_count(idem_key=f"r5-cw-{spelling}") == 1
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    def test_concurrent_retry_both_replay_original(self):
        """Retry konkuren pasca-migrasi (ejaan prefix): dua klien independen
        MEREPLAY submission semula — bukan duplicate write/500."""
        from django.db import connection as conn
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r5-conc")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r5-conc", proof_mime="image/png",
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
            scope=f"payment_submission:uuid:{world.tenant.id}:",
            idem_key="r5-conc", body_hash=_legacy_body_hash(_PROOF_BODY),
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
                response = client.post(url, _PROOF_BODY, headers={"Idempotency-Key": "r5-conc"})
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
        # REV-1611-TEST-01 (P3, task0020/A09): kedua partisipan wajib BENAR-BENAR
        # selesai dan kedua hasil terisi — bukan hanya yang teramati pertama.
        for t in threads:
            assert not t.is_alive(), "thread peserta harus selesai (bounded join)"
        assert set(results.keys()) == {"A", "B"}, results
        for tag, res in results.items():
            assert "exception" not in res, (tag, res)
            assert res["status"] == 201
            assert res["data"] == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        assert _idem_count(operation="payment_submission", idem_key="r5-conc") == 1

    def test_wrong_body_conflicts_without_second_effect(self):
        """Key sama + body BERBEDA pasca-migrasi → 409 idempotency_conflict;
        tidak ada efek kedua (submission tetap 1, record tetap 1)."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r5-body")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r5-body", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"payment_submission:urn:{world.tenant.id}:",
            idem_key="r5-body", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body=response_old, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        other_body = {
            "file_b64": _PROOF_BODY["file_b64"], "mime": "image/png",
            "file_name": "bukti-lain.png",
        }
        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            other_body, headers={"Idempotency-Key": "r5-body"},
        )
        assert retry.status_code == 409
        assert retry.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        assert _idem_count(idem_key="r5-body") == 1

    def test_other_invoice_target_never_receives_cached_response(self):
        """Key/body sama tapi target invoice BERBEDA (satu tenant) → replay
        guard 409; respons A tidak bocor ke B, tidak ada submission baru."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r5-target")
        invoice_a = _make_invoice_for(world)
        invoice_b = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice_a, amount=invoice_a.amount,
                proof_path="payment-proofs/synthetic-r5-target", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"payment_submission:uuid:{world.tenant.id}:",
            idem_key="r5-target", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body=response_old, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice_b.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "r5-target"},
        )
        assert retry.status_code == 409
        assert retry.json()["code"] == "idempotency_conflict"
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice_a.id) == 1
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice_b.id) == 0


# ---------------------------------------------------------------------------
# 3. Migrasi NYATA — ejaan prefix RESOURCE (posisi resource, live controller)
# ---------------------------------------------------------------------------


class TestPrefixResourceSpellingMigration:
    @pytest.mark.parametrize("spelling", sorted(PREFIX_SPELLINGS))
    def test_platform_decision_resource_prefix_replays(self, spelling):
        """Keputusan platform dengan resource ber-ejaan prefix (posisi resource
        matriks controller) → migrasi menormalkan resource canonical → retry
        MEREPLAY 204 tanpa keputusan/outbox/audit baru."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.subscriptions.models import PaymentSubmission

        world = _world(f"rtrw-r5-res-{spelling}")
        admin = _platform_admin_for(f"platform-r5-res-{spelling}@test.local")
        submission = _platform_submission_for(world, state=PaymentSubmission.State.APPROVED)
        spelled = PREFIX_SPELLINGS[spelling](str(submission.id))
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(admin.id),
            scope=f"platform_submission_approve:{world.tenant.id}:{spelled}",
            idem_key=f"r5-res-{spelling}", body_hash=_legacy_body_hash(None),
            response_status=204, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        record = IdempotencyKey.objects.get(idem_key=f"r5-res-{spelling}")
        assert record.operation == "platform_submission_approve", "penjaga valid jadi __unparsed__"
        assert record.tenant_scope == "platform"  # remap operasi platform
        assert record.resource == str(submission.id)  # prefix → canonical

        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent

        client = _client_for(admin, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": f"r5-res-{spelling}"},
        )
        assert response.status_code == 204  # replay, bukan keputusan baru
        assert _idem_count(idem_key=f"r5-res-{spelling}") == 1
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 0
        assert _count_in_tenant(
            AuditEvent, world.tenant.id, action_code="payment_submission.approve"
        ) == 0

    @pytest.mark.parametrize("spelling", sorted(PREFIX_SPELLINGS))
    def test_platform_decision_resource_prefix_crash_window_stays_guarded(self, spelling):
        """Crash-window (domain terkomit, respons absen) pada posisi RESOURCE
        ber-ejaan prefix (REV-R5-03 — paritas posisi penuh): migrasi
        menormalkan identitas + mempertahankan penjaga → retry ditolak 409
        aman; keputusan/outbox/audit baru TIDAK dibuat (no blind execute)."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.subscriptions.models import PaymentSubmission

        world = _world(f"rtrw-r5-rescw-{spelling}")
        admin = _platform_admin_for(f"platform-r5-rescw-{spelling}@test.local")
        submission = _platform_submission_for(world, state=PaymentSubmission.State.SUBMITTED)
        spelled = PREFIX_SPELLINGS[spelling](str(submission.id))
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(admin.id),
            scope=f"platform_submission_approve:{world.tenant.id}:{spelled}",
            idem_key=f"r5-rescw-{spelling}", body_hash=_legacy_body_hash(None),
            response_status=None, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        # Penjaga no-response tetap terjangkau: identitas canonical utuh
        # (operation bukan __unparsed__, resource canonical, platform scope).
        record = IdempotencyKey.objects.get(idem_key=f"r5-rescw-{spelling}")
        assert record.operation == "platform_submission_approve"
        assert record.tenant_scope == "platform"
        assert record.resource == str(submission.id)
        assert record.response_status is None

        from domains.audit.models import AuditEvent
        from domains.jobs.models import OutboxEvent

        client = _client_for(admin, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": f"r5-rescw-{spelling}"},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "idempotency_conflict"
        assert _idem_count(idem_key=f"r5-rescw-{spelling}") == 1
        assert OutboxEvent.objects.filter(
            event_type="payment_submission.approve", aggregate_id=submission.id
        ).count() == 0
        assert _count_in_tenant(
            AuditEvent, world.tenant.id, action_code="payment_submission.approve"
        ) == 0
        from domains.common.tenant_context import tenant_scope

        with tenant_scope(world.tenant.id):
            submission.refresh_from_db()
        assert submission.state == PaymentSubmission.State.SUBMITTED  # tidak dieksekusi ulang

    def test_platform_tenant_literal_scope_migration_replays(self):
        """Scope platform dengan tenant literal fallback `platform` (operator
        tanpa active tenant saat menulis writer lama) → migrasi tetap sah →
        retry mereplay."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r5-plat")
        admin = _platform_admin_for("platform-r5-plat@test.local")
        submission = _platform_submission_for(world, state=PaymentSubmission.State.APPROVED)
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(admin.id),
            scope=f"platform_submission_approve:platform:{submission.id}",
            idem_key="r5-plat", body_hash=_legacy_body_hash(None),
            response_status=204, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        record = IdempotencyKey.objects.get(idem_key="r5-plat")
        assert record.tenant_scope == "platform"
        assert record.resource == str(submission.id)

        client = _client_for(admin, reauth_until=REAUTH_FAR_FUTURE)
        response = client.post(
            f"/api/v1/platform/payment-submissions/{submission.id}/approve",
            headers={"Idempotency-Key": "r5-plat"},
        )
        assert response.status_code == 204
        assert _idem_count(idem_key="r5-plat") == 1


# ---------------------------------------------------------------------------
# 4. Operasi opaque — penjaga prefix-spelling tetap terjangkau runtime
# ---------------------------------------------------------------------------


class TestOpaquePrefixSpellingMigration:
    def test_group_only_prefix_tenant_retained_and_rejected_safe(self):
        """`identity_conflict_resolve` group-only dengan tenant ber-ejaan
        prefix (uuid:) — parser lama menjadikannya __unparsed__ (penjaga
        hilang); parser baru MEMPERTAHANKAN operation+tenant canonical+group
        → runtime legacy lookup MENEMUKANNYA → 409 aman, keputusan tidak
        dieksekusi ulang (REV-1311-02 tetap tertutup untuk ejaan prefix)."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone

        world, _client, sessions, group_id = _migration_world_r5("rtrw-r5-opaque")
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"identity_conflict_resolve:uuid:{world.tenant.id}:{group_id}",
            idem_key="r5-opaque", body_hash=_body_hash_of({"resolution": "merge"}),
            response_status=204, response_body=None, created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        # Penjaga dipertahankan dengan operasi INTACT (bukan __unparsed__).
        record = IdempotencyKey.objects.get(idem_key="r5-opaque")
        assert record.operation == "identity_conflict_resolve"
        assert record.tenant_scope == str(world.tenant.id)
        assert record.resource == group_id

        from domains.customers.models import MigrationAccountDecision

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        url = (
            f"/api/v1/tenants/{world.tenant.id}/migrations/"
            f"{sessions[0].id}/identity-conflicts/{group_id}"
        )
        response = client.post(url, {"resolution": "merge"}, headers={"Idempotency-Key": "r5-opaque"})
        assert response.status_code == 409
        assert response.json()["code"] == "idempotency_conflict"
        assert MigrationAccountDecision.objects.filter(session=sessions[0]).count() == 0


def _migration_world_r5(namespace):
    from tests.integration.test_idempotency_pa006 import _migration_world

    return _migration_world(namespace)


# ---------------------------------------------------------------------------
# 5. Baris mati & fail-stop — batas aman parser
# ---------------------------------------------------------------------------


class TestDeadRowAndFailStopPolicy:
    def test_unresolvable_scope_retained_dead_and_never_leaks(self):
        """Scope yang tidak mungkin ditulis writer sah → baris mati
        DIPERTAHANKAN (penanda __unparsed__, respons utuh untuk ops) dan
        TIDAK PERNAH cocok dengan klaim runtime baru: retry kanonik
        mengeksekusi aksi baru yang sah tanpa membocorkan respons lama."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r5-dead")
        invoice = _make_invoice_for(world)
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope="payment_submission:zz:no-uuid-here:x:",
            idem_key="r5-dead", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201,
            response_body={"submission_id": "stale", "state": "submitted"},
            created_at=timezone.now(),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        dead = IdempotencyKey.objects.get(idem_key="r5-dead")
        assert dead.operation == "__unparsed__"
        assert dead.response_status == 201  # bukti rekonsiliasi ops utuh

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "r5-dead"},
        )
        assert retry.status_code == 201  # aksi baru sah; respons stale TIDAK direplay
        assert retry.json() != {"submission_id": "stale", "state": "submitted"}
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1
        assert _idem_count(idem_key="r5-dead") == 2  # baris mati + klaim baru

    def test_alias_prefix_and_canonical_dedupe_single_guard(self):
        """Dua record writer lama (tenant canonical + tenant uuid: — key sama;
        writer lama menganggapnya scope berbeda) → migrasi menormalkan keduanya
        ke identitas sama → dedupe mempertahankan SATU penjaga ber-respons →
        retry sekali mereplay; business uniqueness tidak hilang."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone
        from domains.common.tenant_context import tenant_scope
        from domains.subscriptions.models import PaymentSubmission

        world = _world("rtrw-r5-dedupe")
        invoice = _make_invoice_for(world)
        with tenant_scope(world.tenant.id):
            original = PaymentSubmission.objects.create(
                tenant=world.tenant, invoice=invoice, amount=invoice.amount,
                proof_path="payment-proofs/synthetic-r5-dedupe", proof_mime="image/png",
                proof_size=64, submitted_by=world.owner,
            )
        response_old = {"submission_id": str(original.id), "state": original.state}
        tenant_id = str(world.tenant.id)
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        # Alias prefix lebih baru TAPI tanpa respons; canonical lama ber-respons.
        old_model.objects.create(
            principal=str(world.owner.id), scope=f"payment_submission:{tenant_id}:",
            idem_key="r5-dedupe", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body=response_old,
            created_at=timezone.now() - timezone.timedelta(hours=2),
        )
        old_model.objects.create(
            principal=str(world.owner.id), scope=f"payment_submission:uuid:{tenant_id}:",
            idem_key="r5-dedupe", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=None, response_body=None,
            created_at=timezone.now() - timezone.timedelta(hours=1),
        )
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])

        assert _idem_count(idem_key="r5-dedupe") == 1  # dedupe → satu penjaga
        kept = IdempotencyKey.objects.get(idem_key="r5-dedupe")
        assert kept.tenant_scope == tenant_id
        assert kept.response_status == 201  # bukti aksi selesai dipertahankan

        client = _client_for(world.owner, world.tenant.id, reauth_until=REAUTH_FAR_FUTURE)
        retry = client.post(
            f"/api/v1/tenants/{world.tenant.id}/saas-invoices/{invoice.id}/payment-submissions",
            _PROOF_BODY, headers={"Idempotency-Key": "r5-dedupe"},
        )
        assert retry.status_code == 201
        assert retry.json() == response_old
        assert _count_in_tenant(PaymentSubmission, world.tenant.id, invoice_id=invoice.id) == 1

    def test_ambiguous_scope_fail_stop_rolls_back_atomically(self, monkeypatch):
        """>1 interpretasi (mustahil pada grammar baseline; disuntik) →
        migrasi GAGAL dan rollback PENUH: skema lama + baris utuh (kolom
        scope masih ada, data tidak berubah) — bukan tebakan, bukan baris
        mati. Setelah penyuntikan dilepas, migrasi ulang berhasil."""
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.utils import timezone

        world = _world("rtrw-r5-failstop")
        IdempotencyKey.objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate([("jobs", "0003_alter_job_kind")])
        old_apps = executor.loader.project_state(("jobs", "0003_alter_job_kind")).apps
        old_model = old_apps.get_model("jobs", "IdempotencyKey")
        old_model.objects.create(
            principal=str(world.owner.id),
            scope=f"payment_submission:uuid:{world.tenant.id}:",
            idem_key="r5-failstop", body_hash=_legacy_body_hash(_PROOF_BODY),
            response_status=201, response_body={"submission_id": "x"},
            created_at=timezone.now(),
        )

        m = _migration_module()
        original_split = m._split_legacy_scope

        def _ambiguous(scope, **kwargs):
            raise m.AmbiguousLegacyScope(f"injected ambiguity: {scope!r}")

        monkeypatch.setattr(m, "_split_legacy_scope", _ambiguous)
        with pytest.raises(m.AmbiguousLegacyScope):
            MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])
        monkeypatch.setattr(m, "_split_legacy_scope", original_split)

        # Rollback atomik: tabel kembali ke bentuk pra-0004.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'jobs_idempotency_key'"
            )
            columns = {row[0] for row in cur.fetchall()}
            cur.execute("SELECT scope FROM jobs_idempotency_key WHERE idem_key = 'r5-failstop'")
            rows = cur.fetchall()
        assert "scope" in columns, "rollback tidak memulihkan kolom scope lama"
        assert "tenant_scope" not in columns
        assert len(rows) == 1 and rows[0][0].startswith("payment_submission:uuid:")

        # Ulangi tanpa injeksi → migrasi berhasil (idempoten terhadap state).
        MigrationExecutor(connection).migrate([("jobs", "0004_idempotency_identity")])
        migrated = IdempotencyKey.objects.get(idem_key="r5-failstop")
        assert migrated.operation == "payment_submission"
        assert migrated.tenant_scope == str(world.tenant.id)
