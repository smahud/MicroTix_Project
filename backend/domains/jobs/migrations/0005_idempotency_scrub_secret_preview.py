"""PA-006/REV-1511-05 — scrub plaintext credential pada cache replay CSV.

`csv_import_validate` (customers/services.validate_csv) mengembalikan preview
baris CSV; kode pra-koreksi menyalin seluruh row — termasuk field `password`
plaintext — ke dalam `IdempotencyKey.response_body`, lalu mereplay-nya. Ini
melanggar ARCHITECTURE §5 ("Secret pada request dibanding HMAC; jangan cache
plaintext secret/reveal response") pada jalur pre-existing yang ditemukan
controller (REV-1511-05, P1).

Kebijakan migrasi (kecil, milik jobs; packet task0010 koreksi 15 November):
- Record retained dengan respons yang memuat plaintext pada
  `response_body["preview"][*]["password"]` → nilai diganti penanda tetap
  `********` (sama dengan proyeksi `customers.services.PREVIEW_SECRET_MASK`
  pada kode baru — konstanta disalin ke sini supaya migrasi tidak mengimpor
  kode aplikasi pada runtime historis).
- PENJAGA TIDAK DIHAPUS dan klaim tidak dibuka ulang: hanya proyeksi nilai
  yang diubah — `response_status`, identitas, body_hash, dan seluruh field
  nonsecret lain tetap utuh, sehingga replay tetap mengembalikan hasil logis
  nonsecret yang sama tanpa eksekusi ulang buta. Record tanpa respons tidak
  disentuh (tidak ada yang bisa bocor; penjaga ambigu tetap).
- Scrub idempoten dan aman diulang: penanda tidak mengubah record yang sudah
  bersih. Reverse TIDAK menulis kembali plaintext yang sudah hilang
  (irreversible by design — secret yang dihapus tidak dipulihkan); reverse
  hanya no-op agar rollback skema tetap teknis mungkin.
- Hanya operasi `csv_import_validate` yang diproses (inventaris jalur
  respons ber-plaintext; jalur lain tidak menyimpan credential — lihat
  laporan executor untuk inventaris safe-response).

Ordering/atomicity: Django menjalankan migrasi PostgreSQL dalam SATU
transaksi (DML atomik); kegagalan → rollback penuh, data lama utuh, ulangi
setelah perbaikan. Jalankan bersama rantai 0004 (write-freeze/drain yang
sama): 0004 menormalkan identitas, 0005 mensterilkan proyeksi respons.
"""
from django.db import migrations

_MASK = "********"


def _scrub_preview_rows(response_body):
    """Mask `password` plaintext pada preview; kembalikan (body_baru, changed)."""
    if not isinstance(response_body, dict):
        return response_body, False
    preview = response_body.get("preview")
    if not isinstance(preview, list):
        return response_body, False
    changed = False
    new_preview = []
    for row in preview:
        if isinstance(row, dict) and isinstance(row.get("password"), str) and row["password"]:
            row = {**row, "password": _MASK}
            changed = True
        new_preview.append(row)
    if changed:
        response_body = {**response_body, "preview": new_preview}
    return response_body, changed


def _scrub_secret_preview(apps, schema_editor):
    IdempotencyKey = apps.get_model("jobs", "IdempotencyKey")
    scrubbed = 0
    scanned = 0
    for record in (
        IdempotencyKey.objects.filter(operation="csv_import_validate")
        .exclude(response_body__isnull=True)
        .iterator()
    ):
        scanned += 1
        body, changed = _scrub_preview_rows(record.response_body)
        if changed:
            record.response_body = body
            record.save(update_fields=["response_body"])
            scrubbed += 1
    print(
        "jobs.0005 idempotency secret-preview scrub: "
        f"scanned={scanned} scrubbed={scrubbed} guards_deleted=0"
    )


def _noop_reverse(apps, schema_editor):
    # Plaintext yang sudah di-scrub tidak dipulihkan (irreversible by design);
    # reverse hanya menjamin rollback skema tetap mungkin.
    print("jobs.0005 reverse: no-op (secret scrub tidak dipulihkan)")


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0004_idempotency_identity"),
    ]

    operations = [
        migrations.RunPython(_scrub_secret_preview, _noop_reverse),
    ]
