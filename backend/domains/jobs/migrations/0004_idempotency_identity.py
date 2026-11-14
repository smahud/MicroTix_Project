"""PA-006 — identitas idempotency canonical + protokol claim/replay.

Perubahan skema jobs_idempotency_key:
- Kolom identitas baru `tenant_scope`, `operation`, `resource` (canonical:
  UUID lowercase / 'platform' / ''), di-backfill dari `scope` lama berformat
  `operation:tenant:resource`.
- Unique constraint identitas `(principal, tenant_scope, operation, resource,
  idem_key)` menggantikan `(scope, idem_key)`; kolom `scope` lama dihapus.

Kebijakan legacy record (PA-006 pekerjaan wajib no. 6; koreksi REV-1311-01):
- Record TANPA respons TIDAK DIHAPUS. Protokol lama (pra-0004) meng-commit
  klaim terpisah dari efek dan respons, sehingga record tanpa respons =
  keadaan efek tak terbukti (crash window main). Menghapusnya = menghapus
  penjaga lalu mengeksekusi ulang buta. Record ini dipertahankan; runtime
  menolak aman (409 idempotency_conflict) pada identitas sama maupun bentuk
  legacy, sampai ops merekonsiliasi respons sesuai outcome.
- Operasi platform (platform_submission_approve/reject/revision): scope lama
  memakai active-tenant operator (defek pra-PA006). Keputusan platform
  lintas tenant → tenant_scope dinormalkan ke 'platform' sehingga retry
  pasca-upgrade menemukan record semula dan MEREPLAY (bukan aksi baru),
  termasuk ketika operator berpindah active tenant.
- `identity_conflict_resolve`: resource lama adalah group_id opaque TANPA
  migration UUID. Identitas baru menyertakan migration UUID (REV-1311-02),
  sehingga bentuk lama TIDAK dapat direkonsiliasi migrasi — dipertahankan
  apa adanya; runtime menolak aman (legacy_replay=False) dan tidak pernah
  mereplay lintas session.
- `payment_submission`: scope lama `payment_submission:<tenant>:` tanpa
  resource. Rekonsiliasi ke invoice dilakukan RUNTIME saat replay via
  legacy_shapes + replay_guard (verifikasi submission→invoice/tenant) —
  migrasi sengaja TIDAK membaca tabel tenant subs_payment_submission karena
  FORCE RLS berlaku juga bagi migrator tanpa konteks tenant.
- Bentuk scope yang tidak terurai (bukan 3 bagian / operation kosong)
  dihapus sebagai data cache rusak (jumlah dicatat). Identitas yang tidak
  dapat dipetakan (tenant/resource bukan UUID padahal operasinya UUID)
  dipertahankan dengan nilai mentah — baris mati yang tak pernah cocok,
  bukan dihapus.
- Tabrakan identitas canonical setelah normalisasi alias (mis. ejaan huruf
  besar vs kecil): dipertahankan satu record TERBARU YANG PUNYA RESPONS
  (bukti aksi selesai); bila tidak ada yang punya respons, terbaru. Sisanya
  dihapus.

Ordering/atomicity: Django menjalankan satu migrasi PostgreSQL dalam SATU
transaksi (DDL+DML atomik per migrasi). Kegagalan migrasi → rollback penuh,
skema+data lama utuh; ulangi migrasi setelah perbaikan (idempoten terhadap
baris sudah ter-backfill: kolom baru diisi ulang dari scope bila masih ada).

Write-freeze/drain dan urutan old/new-code (REV-1311-01): jalankan migrasi
saat penulis DIBERHENTIKAN (drain request / stop worker): kode lama
bergantung pada kolom `scope` yang dihapus, kode baru bergantung pada kolom
identitas baru — tidak ada window tulis campuran; migrasi atomik adalah
titik write-freeze-nya. Setelah sukses, nyalakan kode baru. Jalur pemulihan
data nyata adalah fix-forward (protokol baru); reverse penuh hanya didukung
pada tabel kosong (rollback dev) — re-add kolom NOT NULL pada tabel berisi
baris ditolak PostgreSQL, dan reverse bersifat lossy (ejaan alias/normalisasi
platform tidak dipulihkan). Baris yang dihapus (cache ≤7 hari) tidak
dibangkitkan kembali.
"""
from django.db import migrations, models
import uuid as _uuid

# Operasi yang resource-nya token opaque exact-case (bukan UUID) — cermin
# resource_uuid=False pada decorator. Resource lama dipertahankan apa adanya;
# runtime legacy fallback (legacy_replay=False) menolak aman.
_OPAQUE_RESOURCE_OPERATIONS = frozenset({"identity_conflict_resolve"})

# Operasi platform lintas tenant — cermin platform=True pada decorator
# (subscriptions/views.py). Scope lama memakai active-tenant operator;
# dinormalkan ke 'platform' agar retry pasca-upgrade mereplay aksi semula.
_PLATFORM_OPERATIONS = frozenset(
    {"platform_submission_approve", "platform_submission_reject", "platform_submission_revision"}
)


def _canonical_uuid(value):
    try:
        return str(_uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def _backfill_identity(apps, schema_editor):
    IdempotencyKey = apps.get_model("jobs", "IdempotencyKey")
    stats = {
        "kept": 0,
        "kept_no_response": 0,
        "platform_remapped": 0,
        "legacy_opaque": 0,
        "malformed_deleted": 0,
        "duplicate_deleted": 0,
    }
    # Tahap 1: materialisasi seluruh baris (tanpa mutasi sambil iterasi).
    rows = list(
        IdempotencyKey.objects.all()
        .order_by("-created_at", "-id")
        .values_list("id", "principal", "scope", "idem_key", "response_status", "created_at")
    )
    # best[identity] = dict kandidat yang dipertahankan. Kandidat dipilih
    # berdasarkan rank = (punya_respons, created_at, id): utamakan bukti aksi
    # selesai, lalu yang terbaru. Baris lain dengan identitas canonical sama
    # adalah duplikat alias → dihapus.
    best: dict[tuple, dict] = {}
    delete_ids: list[int] = []
    for pk, principal, scope, idem_key, response_status, created_at in rows:
        parts = str(scope or "").split(":")
        if len(parts) != 3 or not parts[0]:
            delete_ids.append(pk)
            stats["malformed_deleted"] += 1
            continue
        operation, tenant_raw, resource_raw = parts
        if operation in _PLATFORM_OPERATIONS:
            tenant_c = "platform"
            if tenant_raw and tenant_raw.lower() != "platform":
                stats["platform_remapped"] += 1
        elif str(tenant_raw).lower() == "platform":
            tenant_c = "platform"
        else:
            # UUID canonical; nilai mentah yang tidak valid tetap disimpan
            # (baris mati yang tak pernah cocok — bukan dihapus).
            tenant_c = _canonical_uuid(tenant_raw) or str(tenant_raw)
        if operation in _OPAQUE_RESOURCE_OPERATIONS:
            # Bentuk lama group-only TIDAK dapat diikat ke migration UUID —
            # dipertahankan apa adanya; runtime menolak aman (REV-1311-02).
            resource_c = resource_raw
            stats["legacy_opaque"] += 1
        else:
            resource_c = _canonical_uuid(resource_raw) if resource_raw else ""
            if resource_raw and resource_c is None:
                resource_c = resource_raw  # baris mati, dipertahankan
        identity = (str(principal), tenant_c, operation, resource_c, str(idem_key))
        rank = (1 if response_status is not None else 0, created_at, pk)
        candidate = {
            "rank": rank,
            "pk": pk,
            "tenant": tenant_c,
            "operation": operation,
            "resource": resource_c,
            "has_response": response_status is not None,
        }
        prev = best.get(identity)
        if prev is None:
            best[identity] = candidate
        elif rank > prev["rank"]:
            delete_ids.append(prev["pk"])
            best[identity] = candidate
        else:
            delete_ids.append(pk)
            stats["duplicate_deleted"] += 1
    stats["kept"] = sum(1 for c in best.values() if c["has_response"])
    stats["kept_no_response"] = sum(1 for c in best.values() if not c["has_response"])
    if delete_ids:
        IdempotencyKey.objects.filter(id__in=delete_ids).delete()
    for candidate in best.values():
        IdempotencyKey.objects.filter(id=candidate["pk"]).update(
            tenant_scope=candidate["tenant"],
            operation=candidate["operation"],
            resource=candidate["resource"],
        )
    print(
        "jobs.0004 idempotency identity backfill: "
        f"kept_with_response={stats['kept']} kept_no_response={stats['kept_no_response']} "
        f"platform_remapped={stats['platform_remapped']} "
        f"legacy_opaque_group={stats['legacy_opaque']} "
        f"malformed_deleted={stats['malformed_deleted']} "
        f"duplicate_deleted={stats['duplicate_deleted']}"
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
