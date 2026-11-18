# Bukti runtime controller — task 0020

Source checkout `77a4a9056c1c5cf9b0b0874b0630a16dd350aa09`, bersih sebelum
dan sesudah tes. Controller memakai Debian 13, Linux 6.18.57, Python 3.13.5,
Django 5.2.19, pytest 8.4.2, psycopg 3.2.13, PostgreSQL 17.11, cluster baru
disposable di loopback. File/folder runtime dan cluster berada di luar repo.

Suite memakai role `mtx_app` NOSUPERUSER/NOBYPASSRLS dengan test DB yang
dibuat seperti CI. Pada seluruh probe, schema dimigrasi dan dimiliki
`mtx_migrator`, lalu role `mtx_app` mendapat grant runtime. Grant TRUNCATE
hanya untuk teardown fixture di DB uji. Catalog DB mengonfirmasi FORCE
RLS pada job detail, router, enrollment, peer WG, akun SSTP dan tabel
RADIUS. Envelope platform `jobs_job` memiliki kebijakan yang berbeda
dari tabel detail job.

## Command dan hasil

Command Python memakai interpreter di atas dari `backend/` kecuali
validator docs yang dijalankan dari root. Untuk tiap probe file digunakan
`python -m pytest -c pytest.ini <path> -q -s --reuse-db --tb=short`.
Daftar file dan mekanisme split-role mengikuti
[runner review sebelumnya](../20261118T025143Z-0020-r4/run_review.sh).
Runner sesi ini mengarahkan output ke direktori sementara dan menambah
dua file probe R4 yang sudah tersimpan. Isi 8 file probe R1–R4 identik
pada base instruksi dan source yang diuji.

| Command atau probe | Exit dan hasil |
|---|---|
| `python manage.py check` | 0, no issues |
| `python manage.py makemigrations --check --dry-run` | 0, no changes |
| `python -m pytest tests -q --tb=short` | 0, 596 passed / 1 skipped / 3 warnings, 111.73 s. Skip `tests/unit/test_radius_config.py:133`, binary FreeRADIUS tidak tersedia. |
| `python manage.py migrate --noinput` sebagai migrator | 0, initdb bersih, jobs.0006 applied |
| `python manage.py grant_runtime` dan pemeriksaan role/RLS memakai psql | 0 |
| [R1 lifecycle](../20261117T134100Z-0020-review/test_lifecycle_review.py) | 0, 4 passed |
| [R1 authority](../20261117T134100Z-0020-review/test_authority_review.py) | 0, 7 passed |
| [R2 lifecycle](../20261117T170000Z-0020-r2/lifecycle/test_r2_lifecycle_edges.py) | 0, 3 passed |
| [R2 authority](../20261117T170000Z-0020-r2/authority/test_authority_r2.py) | 0, 3 passed |
| [R3 lifecycle](../20261117T212042Z-0020-r3/test_r3_lifecycle_edges.py) | 0, 4 passed |
| [R3 authority](../20261117T212042Z-0020-r3/test_r3_authority.py) | 0, 3 passed |
| [R4 lifecycle](../20261118T025143Z-0020-r4/test_r4_lifecycle_edges.py) | 0, 2 passed. `writer_active`, OS process lama hidup, entri kirim penerus 0, total entri kirim 1. Attempt final valid mencapai failed/router_unreachable, lease NULL, satu eksekusi. |
| [R4 authority](../20261118T025143Z-0020-r4/test_r4_authority_credentials.py) | 0, 2 passed. PG mengamati blocker UPDATE pada kedua tabel kredensial, revoke committed, Router 0, kredensial pending, enrollment verifying, job failed/authority_denied. |
| [Regresi baru lease kedaluwarsa](test_terminal_lease_review.py) | 1, 2 assertion failed, 0 errors, 0.55 s pada rerun final. |
| `python docs/tools/check_docs.py` | 0, PASS, 34 docs, 147 internal links, 85 tasks dan 256 designed cases |
| Shutdown `pg_ctl -m fast stop` | 0, cluster uji berhenti sesudah kedua run |

## Data regresi baru

| Kasus | Expected sebelum reconcile | Actual durable dan hasil panggilan |
|---|---|---|
| Attempt 1/1, lease sudah lewat, tanpa efek | `executing`, token dan epoch lama, settlement menunggu reconciler | `failed`, token NULL, epoch sama, `controlled_no_effect` |
| Attempt 1/2, lease sudah lewat, tanpa efek | `executing`, token dan epoch lama, settlement menunggu reconciler | `retry_wait`, token NULL, epoch sama, `controlled_no_effect` |

Kedua tes memanggil `run_claimed` dengan handler sintetis yang
mencatat satu eksekusi lokal dan menghasilkan galat no-effect sesudah
lease lewat. Tidak ada router, efek eksternal atau verifier yang
dijalankan. Salinan tes di atas cocok dengan run final. Run awal
terhenti pada setup nama kind melebihi 32 karakter dan teardown
fixture skema lintas FK. Kind diperpendek dan daftar available_apps
mengikuti tes integrasi existing sebelum rerun. Dua kegagalan yang
dipakai sebagai temuan berasal dari assertion state pada rerun final.

Pemeriksaan baru untuk positive readback/writer hold, epoch basis resolve,
status aktif actor, serta lease saat wait guard akhir dibatasi ke source
review. Host, systemd, upgrade/restore, live RADIUS, perangkat, browser E2E,
pilot dan skala NOT_RUN.
