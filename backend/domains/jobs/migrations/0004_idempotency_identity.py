"""PA-006 — identitas idempotency canonical + protokol claim/replay.

Perubahan skema jobs_idempotency_key:
- Kolom identitas baru `tenant_scope`, `operation`, `resource` (canonical:
  UUID lowercase / 'platform' / ''), di-backfill dari `scope` lama berformat
  `operation:tenant:resource`.
- Unique constraint identitas `(principal, tenant_scope, operation, resource,
  idem_key)` menggantikan `(scope, idem_key)`; kolom `scope` lama dihapus.

Kebijakan legacy record (PA-006 pekerjaan wajib no. 6):
- Record TANPA respons dihapus: klaim protokol lama yang efeknya tidak bisa
  dibuktikan (klaim lama ter-commit terpisah dari efek dan respons; protokol
  baru menyimpan respons dalam transaksi yang sama dengan efek). Kelas data
  ini cache ber-TTL 7 hari (§5 "retensi key tujuh hari"), bukan history
  bisnis; business uniqueness domain tidak tersentuh. Penghapusan mencegah
  dua keburukan: replay buta (duplikat efek) dan konflik permanen.
- Bentuk scope yang tidak terurai (bukan 3 bagian / UUID salah bentuk /
  tenant bukan 'platform') dihapus sebagai data rusak (dicatat jumlahnya).
  Resource operasi opaque (identity_conflict_resolve group_id sha256[:16])
  dipertahankan apa adanya melalui _OPAQUE_RESOURCE_OPERATIONS —
  cermin resource_uuid=False pada decorator, sehingga record lama kelas itu
  tetap bisa mereplay setelah backfill.
- Tabrakan identitas canonical setelah normalisasi alias (mis. ejaan huruf
  besar vs kecil) di-dedupe: dipertahankan record TERBARU yang memiliki
  respons; sisanya dihapus.
- Reverse: memulihkan kolom `scope` dari komponen identitas. CATATAN:
  re-add kolom NOT NULL pada tabel berisi baris ditolak PostgreSQL, jadi
  reverse penuh hanya didukung pada tabel kosong (rollback dev); jalur
  pemulihan data nyata adalah fix-forward (jalankan ulang protokol baru).
  Baris yang dihapus tidak dibangkitkan kembali (data kelas cache ≤7 hari).

Ordering/compatibility: constraint lama `uq_idem_scope_key` di-dropy AFTER
backfill supaya kolom scope bisa dihapus; constraint baru dipasang setelah
backfill menjamin keunikan canonical. Kegagalan migrasi → transaksi DDL
PostgreSQL atomik per statement; ulangi migrasi (idempotent terhadap baris
sudah ter-backfill: kolom baru diisi ulang dari scope bila masih ada).
"""
from django.db import migrations, models
import uuid as _uuid

# Operasi yang resource-nya token opaque exact-case (bukan UUID) — cermin
# resource_uuid=False pada decorator. Migrasi mempertahankan resource baris
# operasi ini apa adanya (bukan dipurge sebagai "UUID salah bentuk").
_OPAQUE_RESOURCE_OPERATIONS = frozenset({"identity_conflict_resolve"})


def _canonical_uuid(value):
    try:
        return str(_uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def _backfill_identity(apps, schema_editor):
    IdempotencyKey = apps.get_model("jobs", "IdempotencyKey")
    stats = {"kept": 0, "no_response": 0, "malformed": 0, "duplicate_canonical": 0}
    # Tahap 1: materialisasi seluruh baris (tanpa mutasi sambil iterasi).
    rows = list(
        IdempotencyKey.objects.all()
        .order_by("-created_at", "-id")
        .values_list("id", "principal", "scope", "idem_key", "response_status")
    )
    seen: set[tuple[str, str, str, str, str]] = set()
    delete_ids: list[int] = []
    updates: list[tuple[int, str, str, str]] = []
    for pk, principal, scope, idem_key, response_status in rows:
        parts = str(scope or "").split(":")
        if len(parts) != 3:
            delete_ids.append(pk)
            stats["malformed"] += 1
            continue
        operation, tenant_raw, resource_raw = parts
        tenant_c = "platform" if tenant_raw.lower() == "platform" else _canonical_uuid(tenant_raw)
        if operation in _OPAQUE_RESOURCE_OPERATIONS:
            resource_c = resource_raw  # token opaque sah — tidak divalidasi sebagai UUID
        else:
            resource_c = _canonical_uuid(resource_raw) if resource_raw else ""
        if tenant_c is None or resource_c is None or not operation:
            delete_ids.append(pk)
            stats["malformed"] += 1
            continue
        if response_status is None:
            # Klaim lama tanpa respons: efek tak terbukti → hapus (lihat kebijakan).
            delete_ids.append(pk)
            stats["no_response"] += 1
            continue
        identity = (str(principal), tenant_c, operation, resource_c, str(idem_key))
        if identity in seen:
            # Terbaru diproses dulu (order desc): tabrakan alias canonical →
            # duplikat lebih lama dihapus.
            delete_ids.append(pk)
            stats["duplicate_canonical"] += 1
            continue
        seen.add(identity)
        updates.append((pk, tenant_c, operation, resource_c))
        stats["kept"] += 1
    if delete_ids:
        IdempotencyKey.objects.filter(id__in=delete_ids).delete()
    for pk, tenant_c, operation, resource_c in updates:
        IdempotencyKey.objects.filter(id=pk).update(
            tenant_scope=tenant_c, operation=operation, resource=resource_c
        )
    print(
        "jobs.0004 idempotency identity backfill: "
        f"kept={stats['kept']} no_response_deleted={stats['no_response']} "
        f"malformed_deleted={stats['malformed']} "
        f"duplicate_canonical_deleted={stats['duplicate_canonical']}"
    )


def _restore_scope(apps, schema_editor):
    IdempotencyKey = apps.get_model("jobs", "IdempotencyKey")
    for row in IdempotencyKey.objects.all():
        row.scope = f"{row.operation}:{row.tenant_scope}:{row.resource}"
        row.save(update_fields=["scope"])


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0003_alter_job_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="idempotencykey",
            name="tenant_scope",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="idempotencykey",
            name="operation",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="idempotencykey",
            name="resource",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.RunPython(_backfill_identity, _restore_scope),
        migrations.AlterField(
            model_name="idempotencykey",
            name="tenant_scope",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="operation",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="resource",
            field=models.CharField(max_length=64),
        ),
        migrations.RemoveConstraint(
            model_name="idempotencykey",
            name="uq_idem_scope_key",
        ),
        migrations.RemoveField(
            model_name="idempotencykey",
            name="scope",
        ),
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=models.UniqueConstraint(
                fields=["principal", "tenant_scope", "operation", "resource", "idem_key"],
                name="uq_idem_identity",
            ),
        ),
    ]
