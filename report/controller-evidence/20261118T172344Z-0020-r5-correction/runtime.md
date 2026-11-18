# Bukti PostgreSQL untuk review R5 task 0020

Controller menjalankan pemeriksaan dari worktree detached pada
`3301c2940dbfa9293ae52b8d8479b2050c16ebef`. Working tree source bersih. Debian 13.6, Python 3.13.5,
Django 5.2.19, pytest 8.4.2, pytest-django 4.14.0, psycopg 3.2.13 dan
PostgreSQL 17.11 pada loopback cluster disposable. Migrate bersih sebagai
`mtx_migrator`, `manage.py grant_runtime`, lalu probe sebagai
`mtx_app` dengan `rolsuper=false` dan `rolbypassrls=false`. Katalog
menunjukkan 37 tabel FORCE RLS di `public` dan `radius` milik
`mtx_migrator`. Grant TRUNCATE terbatas pada DB tes untuk cleanup pytest.
Angka 37 juga sesuai baris katalog executor. Ringkasan executor menyebut 38.
Suite penuh memakai role runtime yang sama dan DB buatan pytest seperti CI.

## Command dan exit

Command pytest dijalankan dari `backend/`. Untuk probe, set
`TEST_DATABASE_URL` ke database loopback dengan role `mtx_app` dan base
name yang menghasilkan DB `test_<nama>` yang sudah dimigrasi oleh
`mtx_migrator`. Pengulangan memakai
`python -m pytest -c pytest.ini <file> -q -s --reuse-db --tb=short`.

| Pemeriksaan | File atau command | Exit / actual |
|---|---|---|
| R1 | [lifecycle](../20261117T134100Z-0020-review/test_lifecycle_review.py), [authority](../20261117T134100Z-0020-review/test_authority_review.py) | 0 dan 0. **4 + 7 passed**. Discovery stale 0 objek/health. Backup uncertain dengan satu send. Revoke/demote saat preflight menggagalkan release. |
| R2 | [lifecycle](../20261117T170000Z-0020-r2/lifecycle/test_r2_lifecycle_edges.py), [authority](../20261117T170000Z-0020-r2/authority/test_authority_r2.py) | 0 dan 0. **3 + 3 passed**. Recovery sesi DB saat adapter hidup menahan kirim penerus. Revoke selama probe I/O WG/SSTP memberi Router 0. B6 memakai adapter yang dipilih, dengan gate lab. |
| R3 | [lifecycle](../20261117T212042Z-0020-r3/test_r3_lifecycle_edges.py), [authority](../20261117T212042Z-0020-r3/test_r3_authority.py) | 0 dan 0. **4 + 3 passed**. Fase panjang lease sehat melewati expiry awal dengan 25 reconcile attempts. Progress/return setelah expiry di awal operasi menghasilkan nol efek lanjutan. Duplicate enrollment berhasil pada satu job dan memberi error bertipe pada job lain. |
| R4 | [lifecycle](../20261118T025143Z-0020-r4/test_r4_lifecycle_edges.py), [authority](../20261118T025143Z-0020-r4/test_r4_authority_credentials.py) | 0 dan 0. **2 + 2 passed**. Negative readback saat writer hidup tertahan. Final no-effect sah `failed` sekali. Revoke saat lock kredensial memberi Router 0, credential pending dan `failed/authority_denied`. |
| Settlement controller sebelumnya | [regresi R4-correction](../20261118T050714Z-0020-r4-correction/test_terminal_lease_review.py) | 0. **2 passed**. Expiry sudah lewat ketika settlement mulai. Final/nonfinal tetap `executing`, error kosong, epoch sama. |
| Regresi R5 | [test_jobs_r5_residuals.py](https://github.com/smahud/MicroTix_Project/blob/3301c2940dbfa9293ae52b8d8479b2050c16ebef/backend/tests/integration/test_jobs_r5_residuals.py#L77) | 0. **18 passed**. Termasuk readback positif dan epoch, penonaktifan akun, expiry sebelum guard terakhir dan kontrol WG/SSTP. |
| Lease pada lock wait | [tes controller](test_review_lock_wait.py) | **1. 4 assertion gagal, 2 kontrol lulus, 0 error harness** pada pengulangan final. |
| Suite backend | `python -m pytest tests -q --tb=short` | 0. **614 passed, 1 skipped, 3 warnings**, 130.13 s. Skip `test_radius_config.py:133` karena biner FreeRADIUS tidak tersedia. Tiga warning thread berasal dari suite adapter lama. |
| Schema dan docs | `manage.py migrate --noinput`, `manage.py grant_runtime`, `manage.py check`, `manage.py makemigrations --check --dry-run`, `python docs/tools/check_docs.py` | Semua 0. Migrasi termasuk `jobs.0006`, 0 system issues, no changes detected, docs 34 files / 147 links pada source yang direview. |

## Assertion tambahan controller

Peran DB setara dengan probe beku. Dua koneksi independen dan event
menempatkan worker pada batas yang diukur. `pg_blocking_pids()` dan
`pg_stat_activity` mengonfirmasi waiter, blocker dan fase SQL. Clock
masih di bawah expiry saat wait teramati. Pada kasus expiry, clock benar-benar
melewati expiry saat kunci masih dipegang tanpa transaksi yang mengganti
token, epoch atau state. Semua worker dihentikan dengan bounded join dan
menghasilkan satu hasil. Seluruh data dan adapter test bersifat sintetis.

| Kasus | Expected | Actual pada R5 |
|---|---|---|
| Settlement final valid + lock wait | Failed sekali dengan error no-effect, token dilepas | **PASS**. `failed / controlled_no_effect`, token dilepas, epoch tetap. |
| Settlement nonfinal valid + lock wait | Backoff retry dan token dilepas | **PASS**. `retry_wait / controlled_no_effect`, token dilepas, epoch tetap. |
| Settlement final lewat expiry saat UPDATE menunggu | `executing`, token dan epoch awal, error kosong | **FAIL**. `failed / controlled_no_effect`, token dilepas, epoch tetap. |
| Settlement nonfinal lewat expiry saat UPDATE menunggu | `executing`, token dan epoch awal, error kosong | **FAIL**. `retry_wait / controlled_no_effect`, token dilepas, epoch tetap. |
| Watchdog melewati expiry saat UPDATE menunggu | Expiry lama dipertahankan untuk reconciler | **FAIL**. Expiry diperpanjang sesudah lock wait. State `executing` dan token sama. |
| Enrollment WG lewat expiry saat COMMIT menunggu | Router 0, kredensial pending, enrollment verifying | **FAIL**. Router 1, kredensial applied, enrollment completed. Job tertinggal `executing`. |

FK `network_router.tenant_id → tenancy_tenant.id` tercatat
`condeferrable=true` dan `condeferred=true`. Tunggu COMMIT teramati
dengan kunci baris tenant yang setara dengan kunci [penomoran billing](https://github.com/smahud/MicroTix_Project/blob/3301c2940dbfa9293ae52b8d8479b2050c16ebef/backend/domains/billing/services.py#L188-L214).
Probe ini mengukur commit data domain dalam job WG dengan konektivitas
terkontrol. Tes resume/retry perangkat, efek perangkat fisik dan live
enrollment SSTP pada jadwal FK khusus masih NOT_RUN. Probe WG/SSTP yang
diserahkan untuk kredensial dan membership tetap lulus.

Percobaan pertama menghasilkan assertion yang sama, dengan error cleanup
Django saat flush tabel terkait `radius.nas`. Controller mengulang dengan
fixture `available_apps` yang sama dengan suite R5 dan memperbaiki
pencatatan token awal yang sebelumnya ikut termutasi oleh refresh ORM.
Assertion domain tetap sama. Pengulangan final menghasilkan 4 gagal,
2 lulus dan 0 error setup/cleanup.
