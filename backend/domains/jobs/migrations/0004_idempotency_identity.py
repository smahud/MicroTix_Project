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
- Scope legacy menyimpan URL kwargs MENTAH: ejaan UUID apa pun yang diterima
  konversi stdlib uuid.UUID pada view baseline bisa tersimpan — termasuk
  `urn:uuid:<hex>`, `uuid:<hex>`, `urn:<hex>`, prefix berulang
  (`urn:uuid:uuid:<hex>`, `urn:urn:uuid:<hex>`), berkurung, dan campuran
  kolonnya (REV-1311-01: parser 0004 versi cacat hanya mengenali
  `urn:uuid:` tetap/dua segmen polos, sehingga ejaan prefix lain jatuh ke
  `__unparsed__` dan retry pasca-upgrade menduplikasi submission/file
  1→2). Parser sekarang GRAMMAR-DRIVEN: kandidat pemisahan = semua posisi
  kolon, validitas tenant/resource menurut uuid.UUID yang sama persis
  (tenant boleh literal fallback `platform`); tanpa daftar pengecualian
  prefix per ejaan. Interpretasi sah terbukti paling banyak satu; lebih
  dari satu = keadaan mustahil/data asing → AmbiguousLegacyScope
  menghentikan migrasi secara aman (rollback atomik), bukan menebak.
- Bentuk scope yang TIDAK dapat direkonstruksi (tidak ada satu pun posisi
  kolon yang menghasilkan tenant/resource sah menurut grammar writer)
  DIPERTAHANKAN sebagai baris mati ber-penanda operasi khusus — BUKAN
  dihapus: kegagalan parser bukan izin menghapus penjaga efek non-expired.
  Baris mati ini tidak akan pernah cocok dengan identitas runtime baru
  (kolom operation memakai nilai penanda yang bukan operasi decorator
  mana pun), sehingga tetap hanya berfungsi sebagai bukti rekonsiliasi
  ops. Baris mati hanya jatuh ke input yang TIDAK pernah bisa ditulis
  writer baseline sah (view baseline menolak kwargs non-UUID SEBELUM efek
  dijalankan, jadi keluaran writer valid selalu terurai — dibuktikan tes
  matriks grammar); penjaga aksi-selesai tidak hilang ke baris mati.
- Affected-state policy (REV-1311-01, tuntutan review R4): migrasi ini
  BELUM DIRILIS — tidak ada pada main, installer, tag, maupun deployment
  (kandidat Beta NOT_READY; seluruh rantai PA-006 masih di PR). Edit file
  ini HANYA berlaku untuk upgrade yang menjalankan 0004 versi baru dari
  state pra-0004. Environment yang TELANJUR menjalankan 0004 versi cacat
  (sejauh ini hanya CI/sandbox/review yang disposabel) TIDAK diperbaiki
  oleh edit ini: kolom `scope` asli sudah dihapus dan baris `__unparsed__`
  hanya menyimpan potongan 64 karakter — pemulihannya adalah fix-forward
  dari snapshot pra-0004 (restore lalu jalankan ulang upgrade), atau
  rekonsiliasi manual baris `__unparsed__` berbasis bukti ops SEBELUM
  efek baru diizinkan; tidak ada klaim reparasi in-place atas environment
  tersebut.
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

# Penanda operasi untuk scope yang TIDAK dapat direkonstruksi (REV-1311-01):
# nilai ini bukan nama operasi decorator mana pun sehingga identitas baris
# mati tidak akan pernah cocok dengan klaim runtime baru.
_UNPARSED_OPERATION = "__unparsed__"

# Literal fallback writer lama pada posisi tenant (main:
# kwargs.get("tenant_id") or session active_tenant_id or "platform").
_PLATFORM_LITERAL = "platform"


class AmbiguousLegacyScope(RuntimeError):
    """Scope legacy mempunyai >1 interpretasi grammar baseline yang sah.

    Tidak pernah terjadi pada grammar stdlib uuid.UUID (bukti keunikan
    pada docstring _split_legacy_scope); dipertahankan sebagai fail-stop
    defensif: seluruh migrasi dibatalkan (rollback atomik — schema+data
    lama utuh) dan rekonsiliasi eksplisit diperlukan sebelum melanjutkan.
    Menebak satu interpretasi dapat mengikat penjaga ke target salah;
    menjadikannya baris mati menghapus penjaga aksi yang valid.
    """


def _canonical_uuid(value):
    """Canonical lowercase bila value diterima grammar UUID writer baseline.

    Grammar PERSIS stdlib uuid.UUID yang dipakai view baseline untuk
    mengonversi kwargs URL (tenant_context._validate_uuid dan lookup
    model ber-UUIDField): hapus SEMUA substring `urn:`/`uuid:` (case
    sensitif), strip `{}` di ujung, hapus SEMUA `-`, lalu harus tepat 32
    digit hex. Semua ejaan yang diterima writer lama — canonical/upper/
    compact/braced/urn/braced-urn/`uuid:`/`urn:` tanpa `uuid`, bahkan
    prefix berulang — diurai fungsi ini; ejaan yang DITOLAK uuid.UUID
    (mis. `URN:UUID:` huruf besar) juga ditolak di sini. Tidak ada
    reimplementasi grammar dan tidak ada pengecualian prefix per ejaan
    (koreksi REV-1311-01).
    """
    try:
        return str(_uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def _split_legacy_scope(scope, *, tenant_valid=None, resource_valid=None):
    """Uraikan scope lama `operation:tenant:resource` secara grammar-driven.

    Writer lama menyimpan kwargs URL MENTAH: scope =
    f"{operation}:{tenant_part}:{resource}" (common/idempotency.py main).
    Tenant/resource dapat berupa SEMUA ejaan UUID yang diterima konversi
    view baseline — termasuk ejaan berkolon — plus literal `platform`
    fallback pada posisi tenant; resource boleh kosong (operasi tanpa
    resource URL) atau token opaque (operasi _OPAQUE_RESOURCE_OPERATIONS).

    Metode (koreksi REV-1311-01): kandidat pemisahan = SETIAP posisi kolon
    pada `rest`; kandidat sah bila tenant DAN resource keduanya sah
    menurut grammar baseline. Tidak ada aturan prefix tetap per ejaan.

    Interpretasi sah SELALU paling banyak satu (bukti): bila dua posisi
    kolon berbeda i<j sama-sama sah maka tenant_j = tenant_i + ":" + sisa,
    sehingga kolon batas i harus dihapus oleh replace('urn:'/'uuid:')
    dalam transformasi tenant_j — itu menuntut tenant_i berakhir dengan
    teks literal `urn`/`uuid`; teks itu bukan digit hex dan tidak pernah
    dihapus oleh transformasi tenant_i sendiri (tidak ada kolon di
    belakangnya di dalam tenant_i), jadi tenant_i tidak mungkin menjadi
    32-hex yang valid. Kasus tenant kosong/`platform` serupa: kolon pada
    posisi 0 atau tepat setelah `platform` tidak pernah menjadi bagian
    prefix yang bisa dihapus. Karena itu >1 interpretasi mustahil pada
    data writer yang sah — hanya terjadi pada data asing → fail-stop
    AmbiguousLegacyScope (rollback atomik migrasi), BUKAN menebak atau
    memindahkan penjaga valid ke baris mati.

    `tenant_valid`/`resource_valid` hanya untuk penyuntikan tes jalur
    fail-stop; jalur produksi selalu memakai grammar baseline.
    """
    s = str(scope or "")
    operation, sep, rest = s.partition(":")
    if not sep or not operation:
        return None
    if tenant_valid is None:

        def tenant_valid(part: str) -> bool:
            # Ejaan UUID grammar baseline ATAU literal fallback writer
            # (exact-case: writer lama hanya menulis "platform" lowercase
            # — kwargs URL non-UUID ditolak view baseline sebelum efek;
            # 'PLATFORM' huruf besar bukan keluaran writer sah dan tidak
            # diberi split hidup — REV-R5-01).
            return part == _PLATFORM_LITERAL or _canonical_uuid(part) is not None

    if resource_valid is None:
        opaque = operation in _OPAQUE_RESOURCE_OPERATIONS

        def resource_valid(part: str) -> bool:
            if opaque:
                return True  # token opaque (group_id) — sisa verbatim
            return part == "" or _canonical_uuid(part) is not None

    matches = []
    for i, ch in enumerate(rest):
        if ch != ":":
            continue
        tenant_raw, resource_raw = rest[:i], rest[i + 1 :]
        if tenant_valid(tenant_raw) and resource_valid(resource_raw):
            matches.append((operation, tenant_raw, resource_raw))
    if not matches:
        return None
    if len(matches) > 1:
        raise AmbiguousLegacyScope(
            f"jobs.0004: scope legacy ambigu — {len(matches)} interpretasi grammar sah: {scope!r}"
        )
    return matches[0]


def _backfill_identity(apps, schema_editor):
    IdempotencyKey = apps.get_model("jobs", "IdempotencyKey")
    stats = {
        "kept": 0,
        "kept_no_response": 0,
        "platform_remapped": 0,
        "legacy_opaque": 0,
        "unparsed_retained": 0,
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
        parsed = _split_legacy_scope(scope)
        if parsed is None:
            # REV-1311-01 fail-safe: identitas TIDAK dapat direkonstruksi —
            # pertahankan sebagai baris mati (penanda operasi khusus yang
            # tak pernah cocok dengan klaim runtime baru), jangan hapus
            # penjaga efek non-expired. Sisa scope mentah disimpan pada
            # tenant_scope sebagai bukti rekonsiliasi ops (truncated 64).
            operation = _UNPARSED_OPERATION
            tenant_c = str(scope or "").partition(":")[2][:64] or "_"
            resource_c = ""
            stats["unparsed_retained"] += 1
        else:
            operation, tenant_raw, resource_raw = parsed
            if operation in _PLATFORM_OPERATIONS:
                tenant_c = _PLATFORM_LITERAL
                if tenant_raw and tenant_raw.lower() != _PLATFORM_LITERAL:
                    stats["platform_remapped"] += 1
            elif str(tenant_raw).lower() == _PLATFORM_LITERAL:
                tenant_c = _PLATFORM_LITERAL
            else:
                # UUID canonical (grammar penuh writer: semua ejaan sah
                # termasuk prefix berkolon/berkurung/berulang); nilai
                # mentah yang tidak valid tetap disimpan (baris mati
                # yang tak pernah cocok — bukan dihapus).
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
            stats["duplicate_deleted"] += 1
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
        f"unparsed_retained={stats['unparsed_retained']} "
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
