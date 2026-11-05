"""Model backup router — ROUTEROS.md §5, ARCHITECTURE.md §4 (M5).

- Kategori routine/manual/prechange; retensi per kategori (100/10/10) adalah
  generasi BERHASIL per router (defaults.json backup.*_max).
- Artifact immutable: id/path opaque, size/hash, password_ref terenkripsi
  SecretBox (kunci di luar DB); binary TIDAK pernah dipindahkan via API.
- Password per router CSPRNG; kunci lama tetap terbaca setelah rotasi
  (setiap artifact menyimpan salinan ref kunci yang dipakainya).
"""
from __future__ import annotations

import uuid
from datetime import time

from django.db import models
from django.utils import timezone as dj_timezone

# Jendela jadwal rutin 03:00 lokal (trafik rendah) — kontrak BackupSchedule
# .time_local; model interval memakai jam lokal tenant.
ROUTINE_TIME_DEFAULT = time(3, 0)


class BackupArtifact(models.Model):
    """Satu generasi backup per (tenant, router, kategori).

    state mengikuti pipeline bertahap §5: generate/staging → committed;
    failed untuk generasi gagal; pruned = keluar dari retained membership
    katalog (blob cleanup asinkron, membership ≠ blob terhapus).
    """

    class Category(models.TextChoices):
        ROUTINE = "routine"
        MANUAL = "manual"
        PRECHANGE = "prechange"

    class State(models.TextChoices):
        GENERATING = "generating"    # dibuat di router + staging manifest
        COMMITTED = "committed"      # katalog committed (siap unduh via gateway)
        FAILED = "failed"
        PRUNED = "pruned"            # di luar retensi; tidak tampil di daftar

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="backup_artifacts", db_column="tenant_id"
    )
    router = models.ForeignKey(
        "network.Router", on_delete=models.CASCADE, related_name="backup_artifacts", db_column="router_id"
    )
    category = models.CharField(max_length=12, choices=Category.choices)
    # Inkremen per (router, kategori) — setiap percobaan mengonsumsi nomor
    # agar UNIQUE(tenant,router,kategori,generasi) tetap konsisten saat retry.
    generation = models.IntegerField()
    state = models.CharField(max_length=12, choices=State.choices, default=State.GENERATING)
    file_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField(null=True, blank=True)  # null = belum diketahui
    sha256 = models.CharField(max_length=64, blank=True, default="")
    # Path opaque penyimpanan privat — tidak pernah diekspos via API.
    storage_path = models.CharField(max_length=512, blank=True, default="")
    # Password per router terenkripsi AEAD (domain/common/crypto SecretBox).
    password_ref = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "backups_artifact"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "router", "category", "generation"], name="uq_backup_tenant_gen"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "router", "category", "generation"], name="ix_backup_member"),
        ]


class BackupSchedule(models.Model):
    """Jadwal + kebijakan retensi per router (satu baris per router).

    Retensi: routine = `retention` generasi berhasil; manual/prechange
    masing-masing `manual_retention`/`prechange_retention` (§5: 100/10/10).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="backup_schedules", db_column="tenant_id"
    )
    router = models.OneToOneField(
        "network.Router", on_delete=models.CASCADE, related_name="backup_schedules", db_column="router_id"
    )
    routine_interval_hours = models.IntegerField(default=24)
    # Jendela mulai rutin, waktu lokal tenant (kontrak BackupSchedule.time_local).
    routine_time_local = models.TimeField(default=ROUTINE_TIME_DEFAULT)
    retention = models.IntegerField(default=100)          # routine
    manual_retention = models.IntegerField(default=10)
    prechange_retention = models.IntegerField(default=10)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backups_schedule"
        indexes = [
            models.Index(fields=["tenant", "router"], name="ix_backup_sched_tenant_router"),
        ]
