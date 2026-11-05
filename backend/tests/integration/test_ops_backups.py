"""Tes integrasi backup M5 — pipeline bertahap, retensi, kejujuran beta.

Skenario wajib slice: job backup pada router tersimulasi menghasilkan
artifact committed + prune retensi; router belum terenroll gagal jujur
"router_not_enrolled"; isolasi tenant 404.
"""
from __future__ import annotations

import pytest

from domains.backups.models import BackupArtifact, BackupSchedule
from domains.common.tenant_context import tenant_scope
from domains.jobs import engine
from domains.network.models import Router

pytestmark = pytest.mark.integration

from tests.conftest import TEST_PASSWORD  # noqa: E402


@pytest.fixture
def enrolled_router(tenant_a):
    """Router terenroll: tunnel_ip + credential_ref terpasang (ROUTEROS §2)."""
    with tenant_scope(tenant_a.id):
        return Router.objects.create(
            tenant=tenant_a,
            display_name="Router Utama",
            router_code="RTR-A1",
            tunnel_ip="100.127.10.1",
            credential_ref="cred:encrypted-ref",
            routeros_version="7.15",
        )


@pytest.fixture
def unenrolled_router(tenant_a):
    """Router draft tanpa tunnel/credential — belum dikelola platform."""
    with tenant_scope(tenant_a.id):
        return Router.objects.create(
            tenant=tenant_a,
            display_name="Router Draft",
            router_code="RTR-A2",
        )


def _run_one_job():
    """Worker uji: klaim satu job antrean lalu jalankan sampai terminal."""
    job = engine.claim_next()
    assert job is not None, "job tidak masuk antrean"
    return engine.run_claimed(job)


def _post_backup(client, tenant, router, *, key="bk-key-1", body=None):
    return client.post(
        f"/api/v1/tenants/{tenant.id}/routers/{router.id}/backups",
        body or {},
        headers={"Idempotency-Key": key},
    )


class TestBackupRunPipeline:
    def test_accepted_and_committed(self, tenant_a, enrolled_router, auth_client):
        resp = _post_backup(auth_client, tenant_a, enrolled_router, key="bk-acc-1")
        assert resp.status_code == 202
        body = resp.json()
        assert set(body.keys()) == {"job_id", "status_url"}
        assert body["status_url"] == f"/api/v1/jobs/{body['job_id']}"

        result = _run_one_job()
        assert result.state == "succeeded"
        assert result.kind == "backup_router"

        with tenant_scope(tenant_a.id):
            artifact = BackupArtifact.objects.get()
            assert artifact.state == "committed"
            assert artifact.generation == 1
            assert artifact.category == "manual"  # tombol "backup sekarang"
            assert artifact.size_bytes == 1024 * 1024
            assert len(artifact.sha256) == 64
            assert artifact.committed_at is not None
            # Password per router tersimpan terenkripsi (bukan plaintext).
            assert artifact.password_ref and "password" not in artifact.password_ref
            # Path opaque; tidak pernah mengekspos binary via API.
            assert artifact.storage_path.startswith("backups/")
            detail = result.detail
            # Kejujuran beta: hasil simulator bersumber simulator, bukan verified.
            assert detail.result["evidence"]["source"] == "simulator"
            assert detail.result["evidence"]["verified_lab"] is False

    def test_retention_prunes_oldest_beyond_limit(self, tenant_a, enrolled_router, auth_client):
        with tenant_scope(tenant_a.id):
            # Retensi manual 2 generasi (default 10) — uji commit-before-prune.
            schedule = BackupSchedule.objects.create(tenant=tenant_a, router=enrolled_router, manual_retention=2)
            assert schedule.retention == 100

        for i in range(3):
            resp = _post_backup(auth_client, tenant_a, enrolled_router, key=f"bk-ret-{i}")
            assert resp.status_code == 202
            job = _run_one_job()
            assert job.state == "succeeded"

        with tenant_scope(tenant_a.id):
            committed = list(
                BackupArtifact.objects.filter(state=BackupArtifact.State.COMMITTED).order_by("generation")
            )
            pruned = list(BackupArtifact.objects.filter(state=BackupArtifact.State.PRUNED))
            assert [a.generation for a in committed] == [2, 3]
            assert [a.generation for a in pruned] == [1]

        # Daftar hanya menampilkan retained membership (pruned keluar katalog).
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backups")
        assert resp.status_code == 200
        items = resp.json()
        assert [i["generation"] for i in items] == [3, 2]

    def test_unenrolled_router_fails_honestly(self, tenant_a, unenrolled_router, auth_client):
        resp = _post_backup(auth_client, tenant_a, unenrolled_router, key="bk-unen-1")
        assert resp.status_code == 202  # diterima antrean; kejujuran di hasil job
        result = _run_one_job()
        assert result.state == "failed"
        assert result.error_code == "router_not_enrolled"
        assert result.retryable is False
        with tenant_scope(tenant_a.id):
            assert BackupArtifact.objects.count() == 0
        # Status job dapat dipoll pemanggil (idempoten antar retry browser).
        resp = auth_client.get(f"/api/v1/jobs/{result.id}")
        assert resp.status_code == 200
        assert resp.json()["state"] == "failed"
        assert resp.json()["error_code"] == "router_not_enrolled"

    def test_idempotency_key_replay_and_conflict(self, tenant_a, enrolled_router, auth_client):
        first = _post_backup(auth_client, tenant_a, enrolled_router, key="bk-idem-1", body={"category": "prechange"})
        assert first.status_code == 202
        # Isi sama + key sama → aksi logis sama (job_id identik).
        replay = _post_backup(auth_client, tenant_a, enrolled_router, key="bk-idem-1", body={"category": "prechange"})
        assert replay.status_code == 202
        assert replay.json()["job_id"] == first.json()["job_id"]
        # Isi berbeda + key sama → 409 idempotency_conflict (§5).
        clash = _post_backup(auth_client, tenant_a, enrolled_router, key="bk-idem-1", body={"category": "manual"})
        assert clash.status_code == 409
        assert clash.json()["code"] == "idempotency_conflict"

    def test_invalid_category_422(self, tenant_a, enrolled_router, auth_client):
        resp = _post_backup(auth_client, tenant_a, enrolled_router, key="bk-cat-1", body={"category": "monthly"})
        assert resp.status_code == 422
        assert "category" in resp.json()["field_errors"]

    def test_missing_idempotency_key_422(self, tenant_a, enrolled_router, auth_client):
        resp = auth_client.post(f"/api/v1/tenants/{tenant_a.id}/routers/{enrolled_router.id}/backups", {})
        assert resp.status_code == 422


class TestBackupListAndSchedule:
    def test_list_filter_by_router(self, tenant_a, auth_client, enrolled_router, unenrolled_router):
        with tenant_scope(tenant_a.id):
            for gen, router in ((1, enrolled_router), (2, enrolled_router), (1, unenrolled_router)):
                BackupArtifact.objects.create(
                    tenant=tenant_a,
                    router=router,
                    category="routine",
                    generation=gen,
                    state=BackupArtifact.State.COMMITTED,
                    file_name=f"b-{gen}.backup",
                    size_bytes=1024,
                    sha256="a" * 64,
                    storage_path=f"backups/{gen}",
                    password_ref="enc",
                )
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backups?router_id={enrolled_router.id}")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert all(i["router_id"] == str(enrolled_router.id) for i in items)

    def test_pruned_not_listed(self, tenant_a, auth_client, enrolled_router):
        with tenant_scope(tenant_a.id):
            BackupArtifact.objects.create(
                tenant=tenant_a,
                router=enrolled_router,
                category="routine",
                generation=1,
                state=BackupArtifact.State.PRUNED,
                file_name="b-old.backup",
                storage_path="backups/old",
                password_ref="enc",
            )
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backups")
        assert resp.json() == []

    def test_schedule_defaults_per_router(self, tenant_a, auth_client, enrolled_router):
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backup-schedules")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        schedule = items[0]
        assert schedule["router_id"] == str(enrolled_router.id)
        # Retensi defaults.json backup.*_max (100/10/10) — §5.
        assert schedule["retention"] == 100
        assert schedule["manual_retention"] == 10
        assert schedule["prechange_retention"] == 10
        with tenant_scope(tenant_a.id):
            assert BackupSchedule.objects.filter(router=enrolled_router).exists()

    def test_router_filter_semantics(self, tenant_a, auth_client, enrolled_router):
        # Filter router_id yang bukan milik tenant → kosong (bukan error).
        resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/backups?router_id=00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 200
        assert resp.json() == []


class TestBackupAccessControl:
    def test_cross_tenant_backup_run_404(self, tenant_a, tenant_b, auth_client):
        with tenant_scope(tenant_b.id):
            other_router = Router.objects.create(
                tenant=tenant_b,
                display_name="Router B",
                router_code="RTR-B1",
                tunnel_ip="100.127.20.1",
                credential_ref="cred-b",
            )
        resp = auth_client.post(
            f"/api/v1/tenants/{tenant_a.id}/routers/{other_router.id}/backups",
            {},
            headers={"Idempotency-Key": "bk-cross-1"},
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "not_found"

    def test_cross_tenant_list_404(self, tenant_a, tenant_b, auth_client):
        # owner A bukan anggota tenant B → 404 generik (§5).
        resp = auth_client.get(f"/api/v1/tenants/{tenant_b.id}/backups")
        assert resp.status_code == 404

    def test_viewer_without_backups_run_403(self, tenant_a, enrolled_router):
        from domains.identity.models import User
        from domains.tenancy.models import Membership, Role
        from rest_framework.test import APIClient

        viewer = User.objects.create_user(
            email="viewer-bk@test.local", full_name="Viewer Backup", password=TEST_PASSWORD, is_active=True
        )
        Membership.objects.create(user=viewer, tenant=tenant_a, role=Role.VIEWER)
        client = APIClient(enforce_csrf_checks=False)
        client.force_login(viewer)
        session = client.session
        session["active_tenant_id"] = str(tenant_a.id)
        session["auth_at"] = __import__("time").time()
        session.save()
        resp = client.get(f"/api/v1/tenants/{tenant_a.id}/backups")
        # Milik tenant tetapi tanpa izin backups.run → 403 (§5).
        assert resp.status_code == 403
        assert resp.json()["code"] == "forbidden"
