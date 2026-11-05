"""Integrasi alur migrasi Tahap A (U07) — discovery→conflict→commit (M4).

Router + snapshot/objek discovery di-seed via ORM (handler discover_router
domain network dikerjakan paralel); commit diverifikasi: akun dibuat di DB,
objek adopted, router TIDAK dimutasi (tidak ada DeviceOperation).
"""
from __future__ import annotations

import pytest

from domains.common.tenant_context import tenant_scope
from domains.customers.models import AccessAccount, MigrationSession
from domains.customers.services import conflict_group_id
from domains.network.models import DeviceOperation, DiscoveryObject, DiscoverySnapshot, Router

pytestmark = pytest.mark.integration

IDEM = {"Idempotency-Key": "mig-test-1"}


@pytest.fixture
def routers_a(tenant_a):
    """Dua router tenant A + snapshot terakhir berisi objek tumpang tindih."""
    with tenant_scope(tenant_a.id):
        r1 = Router.objects.create(tenant_id=tenant_a.id, display_name="Router Tower", router_code="rtr-tower")
        r2 = Router.objects.create(tenant_id=tenant_a.id, display_name="Router Kampus", router_code="rtr-kampus")
        snap1 = DiscoverySnapshot.objects.create(
            tenant_id=tenant_a.id, router=r1, status=DiscoverySnapshot.Status.SUCCEEDED
        )
        snap2 = DiscoverySnapshot.objects.create(
            tenant_id=tenant_a.id, router=r2, status=DiscoverySnapshot.Status.SUCCEEDED
        )
        DiscoveryObject.objects.create(
            tenant_id=tenant_a.id, snapshot=snap1, router=r1, username="budi.migration",
            kind=DiscoveryObject.Kind.PPPOE, profile="PPPF-20M", comment="tower budi",
        )
        # Username sama (beda kapital) di router lain → grup konflik struktural.
        DiscoveryObject.objects.create(
            tenant_id=tenant_a.id, snapshot=snap2, router=r2, username="Budi.Migration",
            kind=DiscoveryObject.Kind.PPPOE, profile="PPPF-20M", comment="kampus budi",
        )
        DiscoveryObject.objects.create(
            tenant_id=tenant_a.id, snapshot=snap2, router=r2, username="kos.mawar",
            kind=DiscoveryObject.Kind.HOTSPOT, profile="HS-1D", disabled_on_router=True,
        )
    return {"r1": r1, "r2": r2, "snap1": snap1, "snap2": snap2}


def _run_job(job_id) -> object:
    from domains.jobs import engine

    for _ in range(20):
        claimed = engine.claim_next()
        if claimed is None:
            break
        result = engine.run_claimed(claimed)
        if str(claimed.id) == str(job_id):
            return result
    raise AssertionError(f"job {job_id} tidak dapat diklaim/dijalankan")


class TestMigrationFlow:
    def test_full_flow(self, auth_client, tenant_a, routers_a):
        # 1) Mulai sesi migrasi → 202 + migration_id (job discover_router
        #    milik domain network; job_id boleh null bila handler belum ada).
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/routers/{routers_a['r1'].id}/migrations",
            headers=IDEM,
        )
        assert resp.status_code == 202, resp.json()
        body = resp.json()
        assert body["migration_id"]
        migration_id = body["migration_id"]
        assert body["state"] == "pending_discovery"

        # 2) Simulasikan hasil discovery (network domain menautkan snapshot):
        #    pasang snapshot r1 ke sesi, state → discovered.
        with tenant_scope(tenant_a.id):
            session = MigrationSession.objects.get(id=migration_id)
            session.snapshot = routers_a["snap1"]
            session.state = MigrationSession.State.DISCOVERED
            session.save(update_fields=["snapshot", "state"])

        # 3) Daftar akun terdiscover: bentuk DiscoveredAccount persis kontrak.
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/accounts")
        assert resp.status_code == 200
        page = resp.json()
        assert set(page.keys()) == {"items", "next_cursor"}
        items = page["items"]
        assert len(items) == 1  # snapshot r1 saja
        row = items[0]
        assert set(row.keys()) == {
            "id", "username", "kind", "profile", "service", "disabled_on_router", "comment", "state",
        }
        assert row["username"] == "budi.migration"
        assert row["kind"] == "pppoe"
        assert row["profile"] == "PPPF-20M"
        assert row["service"] == "pppoe"
        assert row["state"] == "discovered"

        # 4) Konflik identitas lintas router (username sama case-insensitive).
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/identity-conflicts")
        assert resp.status_code == 200
        candidates = resp.json()
        assert len(candidates) == 1
        candidate = candidates[0]
        assert set(candidate.keys()) == {"candidate_group_id", "usernames", "routers", "kind", "resolution"}
        assert candidate["usernames"] == ["Budi.Migration", "budi.migration"]  # terurut
        assert sorted(candidate["routers"]) == ["Router Kampus", "Router Tower"]
        assert candidate["kind"] == "structural_match"
        assert candidate["resolution"] is None
        group_id = candidate["candidate_group_id"]
        assert group_id == conflict_group_id(["budi.migration", "Budi.Migration"])

        # 5) Resolusi merge → 204; resolusi terlihat pada daftar berikutnya.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/identity-conflicts/{group_id}",
            {"resolution": "merge"},
            headers={"Idempotency-Key": "mig-resolve-1"},
        )
        assert resp.status_code == 204
        candidates = auth_client.get(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/identity-conflicts"
        ).json()
        assert candidates[0]["resolution"] == "merge"

        # 6) Commit → 202 job commit_migration; jalankan inline → sukses.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/commit",
            headers={"Idempotency-Key": "mig-commit-1"},
        )
        assert resp.status_code == 202
        job = resp.json()
        assert set(job.keys()) == {"job_id", "status_url"}
        result = _run_job(job["job_id"])
        assert result.state == "succeeded"
        assert result.effect_state == "confirmed"

        # 7) Verifikasi adopsi DB-only:
        with tenant_scope(tenant_a.id):
            session.refresh_from_db()
            assert session.state == MigrationSession.State.COMMITTED
            assert session.committed_at is not None
            counts = session.counts
            assert set(counts.keys()) == {
                "to_create", "to_merge", "unchanged", "conflicts", "quota_used", "quota_limit",
            }
            assert counts["to_create"] == 1  # merge → SATU akun kanonik
            assert counts["to_merge"] == 1   # satu objek merge dalam snapshot sesi ini
            # Satu akun dengan username kanonik (min leksikografis grup).
            account = AccessAccount.objects.get(username="Budi.Migration")
            assert account.service.lifecycle == "provisioned"
            assert account.service.router_id == routers_a["r1"].id
            assert account.service.package_name == "PPPF-20M"
            assert account.credential_state == "unknown"  # tanpa sumber password — jujur
            # Objek snapshot sesi ini → adopted (objek router lain menunggu
            # sesi migrasi routernya sendiri — batas per sesi, bukan global).
            adopted = DiscoveryObject.objects.filter(state=DiscoveryObject.ObjState.ADOPTED).count()
            assert adopted == 1
            # Router TIDAK dimutasi (Tahap A): tanpa DeviceOperation.
            assert DeviceOperation.objects.filter(tenant_id=tenant_a.id).count() == 0

        # 8) Commit ulang (key berbeda) → 409; job replay idempoten key sama.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/commit",
            headers={"Idempotency-Key": "mig-commit-2"},
        )
        assert resp.status_code == 409
        replay = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/commit",
            headers={"Idempotency-Key": "mig-commit-1"},
        )
        assert replay.status_code == 202
        assert replay.json()["job_id"] == job["job_id"]

    def test_commit_skips_unresolved_conflicts_and_ignored(self, auth_client, tenant_a, routers_a):
        with tenant_scope(tenant_a.id):
            session = MigrationSession.objects.create(
                tenant_id=tenant_a.id, router=routers_a["r2"], snapshot=routers_a["snap2"],
                state=MigrationSession.State.DISCOVERED,
            )
            # Objek kos.mawar diabaikan operator.
            from domains.customers.models import MigrationAccountDecision

            kos = DiscoveryObject.objects.get(username="kos.mawar")
            MigrationAccountDecision.objects.create(
                tenant_id=tenant_a.id, session=session, discovery_object=kos,
                decision=MigrationAccountDecision.Decision.IGNORED,
            )
        # Grup konflik budi tanpa resolusi → objek budi (r2) tidak diadopsi.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/commit",
            headers={"Idempotency-Key": "mig-commit-skip"},
        )
        assert resp.status_code == 202
        result = _run_job(resp.json()["job_id"])
        assert result.state == "succeeded"
        with tenant_scope(tenant_a.id):
            session.refresh_from_db()
            assert session.counts["conflicts"] == 1  # butuh resolusi — needs_review
            assert AccessAccount.objects.filter(username="Budi.Migration").count() == 0
            assert AccessAccount.objects.filter(username="kos.mawar").count() == 0  # ignored
            assert DiscoveryObject.objects.filter(state="adopted").count() == 0

    def test_selected_ids_subset(self, auth_client, tenant_a, routers_a):
        with tenant_scope(tenant_a.id):
            session = MigrationSession.objects.create(
                tenant_id=tenant_a.id, router=routers_a["r2"], snapshot=routers_a["snap2"],
                state=MigrationSession.State.DISCOVERED,
            )
            kos = DiscoveryObject.objects.get(username="kos.mawar")
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/commit",
            {"selected_account_ids": [str(kos.id)]},
            headers={"Idempotency-Key": "mig-commit-subset"},
        )
        assert resp.status_code == 202
        _run_job(resp.json()["job_id"])
        with tenant_scope(tenant_a.id):
            # Hanya kos.mawar yang dipilih; disabled di router → state disabled.
            account = AccessAccount.objects.get(username="kos.mawar")
            assert account.state == AccessAccount.State.DISABLED
            assert account.service.lifecycle == "provisioned"
            assert AccessAccount.objects.filter(username="Budi.Migration").count() == 0

    def test_commit_before_discovery_conflict(self, auth_client, tenant_a, routers_a):
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/routers/{routers_a['r1'].id}/migrations",
            headers={"Idempotency-Key": "mig-nodisc"},
        )
        migration_id = resp.json()["migration_id"]
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{migration_id}/commit",
            headers={"Idempotency-Key": "mig-nodisc-c"},
        )
        assert resp.status_code == 409  # belum ada snapshot

    def test_rename_resolution(self, auth_client, tenant_a, routers_a):
        with tenant_scope(tenant_a.id):
            session = MigrationSession.objects.create(
                tenant_id=tenant_a.id, router=routers_a["r1"], snapshot=routers_a["snap1"],
                state=MigrationSession.State.DISCOVERED,
            )
        group_id = conflict_group_id(["budi.migration", "Budi.Migration"])
        # rename tanpa new_username → 422.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/identity-conflicts/{group_id}",
            {"resolution": "rename"},
            headers={"Idempotency-Key": "mig-rename-bad"},
        )
        assert resp.status_code == 422
        # rename dengan new_username → 204.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/identity-conflicts/{group_id}",
            {"resolution": "rename", "new_username": "budi.tower"},
            headers={"Idempotency-Key": "mig-rename-ok"},
        )
        assert resp.status_code == 204
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{session.id}/commit",
            headers={"Idempotency-Key": "mig-rename-commit"},
        )
        assert resp.status_code == 202
        _run_job(resp.json()["job_id"])
        with tenant_scope(tenant_a.id):
            # Akun dibuat dengan identitas BARU; akun lokal lama tidak dibuat.
            assert AccessAccount.objects.filter(username="budi.tower").count() == 1
            assert AccessAccount.objects.filter(username="budi.migration").count() == 0

    def test_cross_tenant_isolation(self, auth_client, tenant_a, tenant_b):
        with tenant_scope(tenant_b.id):
            router_b = Router.objects.create(
                tenant_id=tenant_b.id, display_name="Router B", router_code="rtr-b"
            )
            session_b = MigrationSession.objects.create(
                tenant_id=tenant_b.id, router=router_b, state=MigrationSession.State.PENDING_DISCOVERY
            )
        # Owner A tidak melihat sesi B (404 generik), bahkan dengan id valid.
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/migrations/{session_b.id}/accounts")
        assert resp.status_code == 404
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/migrations/{session_b.id}/commit",
            headers={"Idempotency-Key": "mig-cross"},
        )
        assert resp.status_code == 404
        # Router B milik tenant lain → 404 saat mulai migrasi dari konteks A.
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/routers/{router_b.id}/migrations",
            headers={"Idempotency-Key": "mig-cross-2"},
        )
        assert resp.status_code == 404


class TestPasswordHarvest:
    def test_honest_lab_required_failure(self, auth_client, tenant_a, routers_a):
        """S1 memerlukan lab (ROUTEROS.md §3) → job gagal jujur lab_required."""
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/routers/{routers_a['r1'].id}/password-harvest",
            headers={"Idempotency-Key": "harvest-1"},
        )
        assert resp.status_code == 202
        job = resp.json()
        assert job["status_url"] == f"/api/v1/jobs/{job['job_id']}"
        result = _run_job(job["job_id"])
        assert result.state == "failed"
        assert result.error_code == "lab_required"
        assert result.retryable is False
        # Tidak ada password yang dipanen/mutasi router.
        with tenant_scope(tenant_a.id):
            assert DeviceOperation.objects.filter(tenant_id=tenant_a.id).count() == 0
