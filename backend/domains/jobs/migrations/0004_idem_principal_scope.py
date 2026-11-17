"""PA-006: identity idempotency mencakup principal.

UNIQUE(scope, idem_key) → UNIQUE(principal, scope, idem_key). Kunci
Idempotency-Key dimiliki principal: dua pengguna (atau pengguna yang sama
lintas tenant/platform) yang memakai ejaan kunci sama kini mendapat record
masing-masing — tidak saling mengunci (409 palsu) dan tidak saling
membocorkan respons tersimpan.

Kebijakan legacy record (tanpa rewrite data):
- Baris lama DIPERTAHANKAN apa adanya — tidak dihapus/ditulis ulang; TTL
  retensi 7 hari tetap berlaku pada jalur pembersihan.
- Lookup baru selalu menyertakan principal + scope baru; baris lama dengan
  ejaan scope identik tetap dapat di-replay oleh principal yang sama dengan
  key semula (kompatibel), dan tidak pernah memberikan respons ke
  principal/target lain.
- Baris lama TANPA respons (in-flight pra-PA-006) tidak dieksekusi ulang
  buta oleh jalur replay baru — ditolak fail-safe 409 sampai TTL;
  business uniqueness domain (mesin state, unique constraint, FOR UPDATE)
  tetap menjaga efek ganda.

Urutan operasi: constraint baru DITAMBAHKAN dulu, constraint lama dihapus
kemudian — uniqueness selalu terjaga selama migrasi. Penambahan constraint
baru tidak dapat gagal pada data lama: (scope, idem_key) unik ⟹
(principal, scope, idem_key) unik.

Kegagalan/rollback: DDL ADD/DROP CONSTRAINT atomik per statement; gagal di
tengah meninggalkan kombinasi subset yang tetap benar (kedua constraint
sama-sama menjamin subset relasi). Reverse mengembalikan constraint lama
dan dapat gagal bila baris pasca-migrasi lintas-principal dengan
(scope, idem_key) sama sudah ada — jalur yang disarankan adalah fix-forward
(constraint baru idempoten); untuk rollback penuh, tunggu purge TTL atau
bersihkan baris pasca-migrasi secara eksplisit terlebih dahulu.
"""
from django.db import migrations
from django.db.models import UniqueConstraint


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0003_alter_job_kind"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=UniqueConstraint(
                fields=["principal", "scope", "idem_key"],
                name="uq_idem_principal_scope_key",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="idempotencykey",
            name="uq_idem_scope_key",
        ),
    ]
