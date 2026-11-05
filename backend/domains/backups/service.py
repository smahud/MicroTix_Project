"""Layanan backup: pipeline bertahap generate → manifest → commit → prune.

ROUTEROS.md §5: API memerintahkan pembuatan berkas; binary tidak berpindah
sebagai satu respons API. Beta M5 menyimulasikan pipeline bertahap dengan
adapter simulator (TK-004) — hasil simulator membawa evidence
{source: "simulator"} dan TIDAK dilabeli verified (kejujuran beta; verified
hanya lewat lab CHR/GNS3 sesuai §Pengujian ARCHITECTURE.md).

Urutan commit-sebelum-prune: "ubah retained membership → prune async"
(§5); beta melakukan prune sinkron SETELAH generasi baru committed.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone as dj_timezone

from adapters.routeros.base import RouterContext, RouterOsError, TimeoutAfterSendError, UnreachableError
from adapters.routeros.simulator import RouterOsSimulator
from domains.backups.models import BackupArtifact, BackupSchedule
from domains.common import crypto
from domains.config.registry import registry
from domains.jobs.engine import JobContext, JobError, JobHandler

logger = logging.getLogger(__name__)

# Kind pekerjaan M5 (spesifikasi slice): pipeline backup satu router.
# Catatan penamaan: ARCHITECTURE.md §6 mencantumkan "backup_router" sebagai
# kind kontrak frontend: backup_router (contracts.ts JobKind) —
# didiskusikan pada laporan slice sebelum menyatukan keduanya.
BACKUP_RUN_KIND = "backup_router"  # kontrak FE JobKind (§5)

# Alasan aman yang dibolehkan klien (kontrak kategori: pre_change).
API_CATEGORY = {"routine": "routine", "manual": "manual", "prechange": "pre_change"}


def select_adapter() -> RouterOsSimulator:
    """Seleksi adapter RouterOS untuk jalur backup.

    adapters/routeros/__init__.py belum memasang selektor (M5): dev/test
    memakai simulator deterministik. Klien API-SSL nyata aktif bersama
    enrollment terverifikasi (M3+) — saat itu seleksi pindah ke sana dan
    hasilnya boleh diverifikasi lab.
    """
    return RouterOsSimulator()


def _config_int(key: str) -> int:
    return registry().get_int(key)


def retention_for(schedule: BackupSchedule | None, category: str) -> int:
    """Retensi generasi berhasil per kategori (§5; defaults.json backup.*_max)."""
    defaults = {
        BackupArtifact.Category.ROUTINE: "backup.routine_max",
        BackupArtifact.Category.MANUAL: "backup.manual_max",
        BackupArtifact.Category.PRECHANGE: "backup.prechange_max",
    }
    if schedule is None:
        return _config_int(defaults[category])
    if category == BackupArtifact.Category.ROUTINE:
        return schedule.retention
    if category == BackupArtifact.Category.MANUAL:
        return schedule.manual_retention
    return schedule.prechange_retention


def prune_beyond_retention(tenant_id, router_id, category: str) -> int:
    """Prune generasi committed TERTUA di luar retensi (commit-before-prune).

    Hanya mengubah membership katalog (state=pruned); blob fisik dibersihkan
    asinkron — "membership katalog berbeda dari blob yang belum terhapus"(§5).
    Generasi failed tidak menghitung retensi (retensi = generasi berhasil)
    dan tetap terlihat sebagai riwayat kegagalan.
    """
    schedule = BackupSchedule.objects.filter(tenant_id=tenant_id, router_id=router_id).first()
    keep = retention_for(schedule, category)
    committed = list(
        BackupArtifact.objects.filter(
            tenant_id=tenant_id, router_id=router_id, category=category, state=BackupArtifact.State.COMMITTED
        ).order_by("-generation")
    )
    stale = committed[keep:]
    if stale:
        BackupArtifact.objects.filter(id__in=[a.id for a in stale]).update(state=BackupArtifact.State.PRUNED)
    return len(stale)


def _router_password(router_id, tenant_id: str) -> str:
    """Password per router CSPRNG; kunci lama dipertahankan antar generasi.

    Rotasi menghasilkan password baru hanya bila belum ada generasi sebelumnya;
    setiap artifact menyimpan salinan ref terenkripsi kunci yang dipakainya
    sehingga generasi lama tetap dapat dipulihkan setelah rotasi (§5).
    """
    prev = (
        BackupArtifact.objects.filter(tenant_id=tenant_id, router_id=router_id)
        .exclude(password_ref="")
        .order_by("-created_at")
        .first()
    )
    if prev is not None:
        try:
            return crypto.SecretBox.decrypt_str(prev.password_ref)
        except Exception:
            logger.warning("password_ref router %s gagal didekripsi — rotasi kunci", router_id)
    # backup.password_chars = 32 karakter urlsafe (defaults.json).
    return crypto.generate_token(24)


def _write_manifest(storage_path: str, manifest: dict) -> None:
    """Simpan manifest generasi ke penyimpanan privat (path opaque).

    Beta: isi tersimpan adalah manifest bertanda simulator, bukan binary
    RouterOS terenkripsi penuh; jalur SFTP receiver (BKP-03) datang bersama
    infrastruktur receiver. Penulisan file di luar transaksi DB — kegagalan
    transaksi dapat menyisakan file yatim; janitor pembersih menyusul
    bersama receiver.
    """
    target = settings.MT_STORAGE_ROOT / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, sort_keys=True, default=str))
    try:
        target.chmod(0o600)
    except OSError:  # pragma: no cover - platform tanpa chmod
        pass


class BackupRunHandler(JobHandler):
    """Handler kind backup_run: generate → store manifest → commit → prune."""

    kind = BACKUP_RUN_KIND

    # --- prasyarat: router terenroll dan masih dikelola ---

    def _load_router(self, ctx: JobContext):
        from domains.network.models import Router

        if ctx.job.router_id is None:
            raise JobError(code="router_not_enrolled", message="Job tanpa router")
        router = Router.objects.filter(id=ctx.job.router_id, released_at=None).first()
        # Router nyata hanya bisa dibackup bila terenroll: tunnel_ip (WireGuard
        # /32 aktif) + credential_ref (API-SSL) — tanpa itu jujur gagal
        # "router_not_enrolled" (recovery tidak diperlukan; bukan kerusakan).
        if router is None or not router.tunnel_ip or not router.credential_ref:
            raise JobError(code="router_not_enrolled", recovery_required=False)
        return router

    def preflight(self, ctx: JobContext) -> None:
        self._load_router(ctx)

    # --- tahap generate + staging manifest ---

    def execute(self, ctx: JobContext) -> dict[str, Any]:
        router = self._load_router(ctx)
        category = ctx.payload.get("category") or BackupArtifact.Category.MANUAL
        ctx.progress(phase="generate", done=0, total=1)

        generation = (
            BackupArtifact.objects.filter(tenant_id=router.tenant_id, router_id=router.id, category=category).aggregate(
                m=models.Max("generation")
            )["m"]
            or 0
        ) + 1
        password = _router_password(router.id, router.tenant_id)
        artifact = BackupArtifact.objects.create(
            tenant_id=router.tenant_id,
            router=router,
            category=category,
            generation=generation,
            state=BackupArtifact.State.GENERATING,
            file_name=f"{router.router_code or 'router'}-{category}-{generation}.backup"[:255],
            storage_path=f"backups/{uuid.uuid4().hex}",
            password_ref=crypto.SecretBox.encrypt(password),
        )

        adapter = select_adapter()
        rctx = RouterContext(
            router_id=str(router.id),
            tenant_id=str(router.tenant_id),
            tunnel_ip=router.tunnel_ip,
            mode=router.mode,
            routeros_version=router.routeros_version or "7.15",
            credential_ref=router.credential_ref,
        )
        try:
            metadata = adapter.create_backup(rctx, category=category)
        except TimeoutAfterSendError:
            artifact.state = BackupArtifact.State.FAILED
            artifact.save(update_fields=["state"])
            # Perintah mungkin sudah terkirim → uncertain, bukan failed (§6).
            raise JobError(code="timeout_after_send", uncertain=True) from None
        except UnreachableError:
            artifact.state = BackupArtifact.State.FAILED
            artifact.save(update_fields=["state"])
            raise JobError(code="router_unreachable", retryable=True) from None
        except RouterOsError as exc:
            artifact.state = BackupArtifact.State.FAILED
            artifact.save(update_fields=["state"])
            raise JobError(code=exc.code, retryable=True) from None

        # Staging manifest di penyimpanan privat (opaque; tidak via API).
        ctx.progress(phase="transfer", done=0, total=1)
        _write_manifest(
            artifact.storage_path,
            {
                "artifact_id": str(artifact.id),
                "router_id": str(router.id),
                "category": category,
                "generation": generation,
                "adapter_metadata": metadata,
                "simulated": bool(metadata.get("simulated")),
                "created_at": dj_timezone.now().isoformat(),
            },
        )
        return {"artifact_id": str(artifact.id), "generation": generation, "metadata": metadata}

    # --- tahap verify/commit katalog + prune ---

    def verify(self, ctx: JobContext) -> dict[str, Any]:
        """Readback staging sebelum commit: manifest harus benar-benar ada.

        Verify membaca ulang keadaan (bukan mempercaya memori execute):
        artifact generating terbaru untuk (router, kategori) + manifest
        fisik di penyimpanan privat.
        """
        router = self._load_router(ctx)
        category = ctx.payload.get("category") or BackupArtifact.Category.MANUAL
        artifact = (
            BackupArtifact.objects.filter(
                tenant_id=router.tenant_id,
                router_id=router.id,
                category=category,
                state=BackupArtifact.State.GENERATING,
            )
            .order_by("-generation")
            .first()
        )
        if artifact is None:
            raise JobError(code="verification_error", uncertain=True)
        try:
            manifest = json.loads((settings.MT_STORAGE_ROOT / artifact.storage_path).read_text())
            metadata = manifest.get("adapter_metadata", {})
        except (OSError, ValueError):
            # Staging tidak terbaca — hasil tak pasti, jangan failed diam-diam.
            raise JobError(code="staging_unreadable", uncertain=True) from None
        size = int(metadata.get("size_bytes") or 0)
        if size <= 0 or size > _config_int("backup.max_artifact_bytes"):
            artifact.state = BackupArtifact.State.FAILED
            artifact.save(update_fields=["state"])
            raise JobError(code="artifact_size_invalid", recovery_required=False)
        # Commit katalog dulu, prune setelahnya (§5 commit-before-prune).
        artifact.state = BackupArtifact.State.COMMITTED
        artifact.size_bytes = size
        artifact.sha256 = str(metadata.get("hash") or "")[:64]
        artifact.committed_at = dj_timezone.now()
        artifact.save(update_fields=["state", "size_bytes", "sha256", "committed_at"])
        pruned = prune_beyond_retention(artifact.tenant_id, artifact.router_id, artifact.category)
        ctx.progress(phase=None, done=1, total=1)
        evidence = {"source": "simulator" if metadata.get("simulated") else "routeros", "verified_lab": False}
        return {
            "artifact_id": str(artifact.id),
            "generation": artifact.generation,
            "category": artifact.category,
            "state": artifact.state,
            "pruned": pruned,
            "evidence": evidence,
        }

    def on_retry(self, ctx: JobContext) -> None:
        # Retry aman: generasi generating tertinggal tetap terlihat jujur
        # sebagai staging; nomor generasi baru dikonsumsi percobaan berikutnya.
        return None
