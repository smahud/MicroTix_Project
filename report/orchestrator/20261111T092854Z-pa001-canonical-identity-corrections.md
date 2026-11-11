# Sesi Executor Sandbox — Koreksi PR #9 sesuai review REV-1111 (PA-001 lanjutan)

- **Role/author**: Executor utama (sesi orchestrator tunggal, tanpa sub-agent — packet koreksi
  kecil dan kohesif sesuai CONTRACT §5).
- **Tanggal (UTC)**: 2026-11-11T09:28Z (waktu lokal sandbox Asia/Jakarta 16:28).
- **Objective**: Menjalankan packet koreksi PR #9 dari review controller 2026-11-11
  (putusan REQUEST CHANGES): menutup **REV-1111-01** (urutan lock memakai teks UUID mentah),
  **REV-1111-02** (sorting mengubah nama/bahasa kuitansi), **REV-1111-03** (bukti rollback dan
  race perlu dipertegas), dan **REV-1111-10** (handoff menyembunyikan code blockers) — tanpa
  memperluas fitur, tanpa deploy, tanpa menyentuh PR #7/#8.
- **Base branch/SHA**: branch PR #9 `session/2026-11-11-pa001-payment-concurrency` @
  `3b20b562db37f5b59bc1e13df886264dd8bfa55c` (kandidat review); `main` @
  `16085f825fef25ee4112d74b729c57e623b0bb05`. **Delta sejak review: TIDAK ADA** — ketiga SHA
  (main `16085f8`, PR #9 `3b20b56`, PR #8 `6bb57c9`) diverifikasi identik dengan snapshot
  controller 2026-11-11T07:42:25Z via fetch ulang sebelum bekerja; worktree bersih saat mulai.
- **Requirement/finding IDs**: REV-1111-01/02/03/10 (register review controller); acceptance
  dari Lampiran A (finance) §Findings 1–3; kontrak BIL-03/AC-BIL, BIL-08, I18N-01 §2,
  ARCHITECTURE §4/§5/§6. Temuan lain (REV-1111-04–09, 11–12) BUKAN scope sesi ini.

## 1. Akar masalah yang dikoreksi (dari review, diverifikasi ulang pada SHA kandidat)

`_parse_allocations` pada kandidat PR #9 menggabungkan dan mengurutkan kunci lock berdasarkan
STRING MENTAH penelepon: ejaan berbeda dari UUID yang sama (besar/kecil, hyphen/compact)
(a) tidak tergabung saat merge → insert alokasi ganda menabrak `uq_bilalloc_pair`,
(b) dapat MEMBALIK urutan akuisisi kunci antar pemanggil → deadlock; dan hasil dikembalikan
urut UUID sehingga `allocations[0]` (sumber customer/bahasa kwitansi, I18N-01) berpindah dari
invoice pertama-diminta ke invoice ber-UUID terkecil. Id salah bentuk juga lolos validasi dan
mati sebagai 404, bukan 422. Klaim "rollback penuh" pada laporan sesi sebelumnya hanya
dibuktikan pada kegagalan VALIDASI (sebelum mutasi), bukan pasca-tulis.

## 2. Perubahan (smallest change)

### 2.1 `backend/domains/billing/services.py` (+46/−5, satu fungsi + helper)

- Helper baru `_canonical_invoice_id`: normalisasi tiap invoice_id lewat `uuid.UUID` →
  string kanonik; input salah bentuk → `ApiError.validation` **422** dengan `field_errors`
  pada `allocations` (pola yang sama dengan `billing/views.py::_parse_uuid` dan
  `common/tenant_context.py` — rujukan eksplisit reviewer). Tidak ada representasi yang
  sebelumnya diterima yang kini ditolak (alternatif strict canonical-only TIDAK diambil,
  sesuai catatan review agar tidak mengubah kompatibilitas diam-diam).
- `_parse_allocations`: (a) merge dan `sorted()` kini pada IDENTITAS kanonik → urutan kunci
  selalu urutan identitas database yang sama untuk semua pemanggil; (b) urutan permintaan
  teragregasi semula disimpan (`request_order`) dan hasil dikembalikan dalam urutan itu —
  kunci diambil urut canonical, hasil kembali urutan permintaan (REV-1111-02); (c) `select_for_update()`
  tetap (PA-001 inti tidak diubah).
- `verify_payment`: hanya komentar penjelas diperbarui (sumber customer/bahasa kwitansi =
  invoice pertama yang DIMINTA).

Tanpa migrasi skema, tanpa API kontrak baru, tanpa model/queue baru — sesuai batas
"solusi minimum" pada register review.

### 2.2 `backend/tests/integration/test_billing_payment_concurrency.py` (+468/−7)

Enam tes baru (total kelas file: 10 tes):

| Tes | Menutup | Isi |
|---|---|---|
| `TestCanonicalInvoiceIdentity::test_alias_spellings_of_one_invoice_merge_into_single_allocation` | REV-1111-01 | Satu invoice via 4 ejaan (kecil-hyphen, BESAR-hyphen, kecil-compact, BESAR-compact) → SATU alokasi tergabung 200.000; kwitansi `applies_to` satu baris |
| `TestCanonicalInvoiceIdentity::test_malformed_invoice_id_rejected_422_without_effects` | REV-1111-01 | 7 variasi id salah bentuk → 422 `validation_error` + `field_errors.allocations`, tanpa efek; UUID valid tak dikenal tetap 404 (jalur lama utuh) |
| `TestReceiptRequestOrderCompatibility::test_receipt_customer_locale_and_lines_follow_first_requested_invoice` | REV-1111-02 | Dua customer beda bahasa ("en" vs default "id"); invoice pertama-diminta ber-UUID canonical TERBESAR → kwitansi tetap memakai customer/bahasa invoice pertama + baris urutan permintaan |
| `TestPostWriteRollback::test_failure_after_all_writes_rolls_back_every_db_effect` | REV-1111-03 | Bloker `dedup_key` outbox (unique, pra-dibuat ter-commit) → insert outbox TERAKHIR verifikasi gagal IntegrityError SETELAH alokasi/invoice/payment/kwitansi/audit tertulis; error ditangkap DI LUAR `tenant_scope`; seluruh efek DB ter-rollbalik; file artifact yatim dihitung TERPISAH (maks 1, perilaku diakui `issue_document`) |
| `TestControlledLockContention::test_lock_acquisition_follows_canonical_identity_order` | REV-1111-01/03 | Koneksi tes MENAHAN kunci invoice canonical-pertama → thread verifikasi (ejaan alias yang pada kode lama mengurut terbalik) diverifikasi benar-benar TERBLOKIR via `pg_stat_activity` (poll dibatasi waktu) → probe `select_for_update(nowait=True)` pada invoice kedua membuktikan thread BELUM memegang kunci kedua → urutan kunci = urutan identitas kanonik. BUKAN barrier + harapan interleaving |
| `TestControlledLockContention::test_concurrent_alias_spellings_serialize_without_deadlock` | REV-1111-01 | Dua verifikasi pasangan invoice sama, campuran ejaan kanonik vs alias → keduanya "ok", paid == SUM(alokasi) == total |

Tes lama `test_failed_multi_allocation_rolls_back_everything` DIRENAME menjadi
`test_invalid_second_allocation_rejected_before_any_mutation` (kelas
`TestAllocationValidationBeforeMutation`) dengan deskripsi disempitkan: membuktikan
validasi-di-muka 409, BUKAN rollback pasca-tulis — sesuai koreksi klaim REV-1111-03.
Invarian dua-payment dan paid == SUM(alokasi) dari 4 tes PA-001 lama tetap utuh.

### 2.3 Persistensi laporan review (CONTRACT §10, instruksi controller §8.8)

- `report/controller/20261111T074225Z-repo-handoff-review.md` — dokumen controller utama
  (§1–§10), verbatim dari artefak review.
- `report/reviewer/20261111T073744Z-pr9-independent-review.md` — Lampiran A (finance),
  verbatim.
- `report/reviewer/20261111T073747Z-ops-readiness.md` — Lampiran B (operasi), verbatim
  sampai akhir natural dokumen (baris "Executor persistence path"). **Catatan transparan**:
  file upload berisi fragmen duplikat tempelan setelah akhir natural dokumen (mengulang
  paragraf "Acceptance and downtime limits"/"Evidence and handoff" dan terpotong
  kata "NOT_"); fragmen duplikat TIDAK disalin karena bukan bagian dokumen reviewer,
  seluruh kalimatnya sudah ada utuh di badan dokumen. Tidak ada secret/credential/PII
  pada ketiga file (scan `github_pat_|ghp_|password` bersih).

### 2.4 Koreksi handoff/progress (REV-1111-10)

`report/LATEST_HANDOFF.md` dan `docs/progress.md` ditulis ulang untuk sesi ini:
menghapus klaim "penahan beta hanya host/Gate A/G", "BUKAN pekerjaan kode", "penahan
tunggal" (baris 15/49/53/77 handoff lama); memisahkan implemented / verified_local /
NOT_RUN; mencatat code blockers yang masih terbuka (REV-1111-04–09) BESERTA environment
blockers; PA-001 berstatus MENUNGGU REVIEW ulang (bukan accepted/closed); klaim rollback
dibatasi sesuai bukti tes aktual (validasi-di-muka + pasca-tulis kini keduanya terbukti);
klaim timer `issue_due_invoices` dicabut (scheduler belum terbukti — REV-1111-09);
kegagalan docs CI PR #7/#8 = manifest mismatch (bukan bukti SSTP gagal runtime).

## 3. Lingkungan sandbox (disposable, milik run ini)

- Container: Debian 13 (trixie), user non-root `z` (uid 1001), tanpa systemd (PID 1 = tini).
- PostgreSQL **17.5** user-space (build resmi PostgreSQL hasil redistribusi Zonky
  `embedded-postgres-binaries-linux-amd64` 17.5.0, Maven Central) di `/tmp/pgbin/pg17`;
  cluster initdb trust-auth di `backend/pgdata`, port 55432, peran `mtx_migrator` +
  `mtx_app` (CREATEDB, NOBYPASSRLS — paritas CI) dan database `microtix` sesuai
  `backend/scripts/dev_bootstrap.sh` (langkah 1–2 direplikasi via psycopg karena binari
  `psql` tidak tersedia dalam paket; skrip bootstrap di luar repo:
  `/home/z/my-project/scripts/mtx_pg_bootstrap.py`). Migrasi dijalankan sebagai
  `mtx_migrator` + `manage.py grant_runtime` (paritas Makefile/CI).
- Python **3.13.5** venv terisolasi; dependensi patch-exact dari `pyproject.toml`
  (`pip install -e .` + pytest 8.4.2 + pytest-django 4.14.0) — Django 5.2.19, DRF 3.16.1,
  psycopg 3.2.13, xhtml2pdf 0.2.28 (identik pin CI).
- Fixture/sintetis semata (tenant `rtrw-cc0000xx`) — tidak ada data pelanggan nyata,
  tidak ada target produksi, tidak ada credential dalam diff.

## 4. Bukti test (perintah nyata, cwd `backend/`, keluaran sesuai)

| # | Perintah | Hasil | Keterangan |
|---|---|---|---|
| 1 | `MT_ENV=test .venv/bin/python -m pytest tests/integration/test_billing_payment_concurrency.py -q` | **10 passed** (5.3s) | 4 tes PA-001 lama + 6 tes baru REV-1111 |
| 2 | Sensitivitas: `git checkout pr9-head -- backend/domains/billing/services.py` lalu perintah #1 | **5 dari 6 tes baru GAGAL** | (a) alias-merge gagal (IntegrityError `uq_bilalloc_pair`), (b) malformed-id 422 gagal (kode lama 404), (c) receipt order gagal (customer/bahasa salah), (d) probe urutan kunci gagal (invoice kedua TERKUNCI sebelum pertama), (e) konkurensi alias gagal — **PostgreSQL melaporkan deadlock nyata** ("deadlock detected ... while locking tuple in relation billing_internet_invoice") — persis konsekuensi yang diprediksi REV-1111-01. 4 tes PA-001 lama tetap lolos pada kode lama (memang dirancang untuk defect PA-001, bukan alias). Tes rollback pasca-tulis lolos di kedua kode (membuktikan kemampuan rollback transaksi, bukan menolak defect lama) |
| 3 | Restore perbaikan (`cp /tmp/services_fixed.py`) lalu perintah #1 | **10 passed** | Kode fix dikembalikan; bersih |
| 4 | Perintah #1 diulang 3× | **10 passed** tiap run | Stabilitas race test (total 4 run hijau beruntun) |
| 5 | `MT_ENV=test .venv/bin/python -m pytest tests -q` | **382 passed, 1 skipped, 3 warnings** (39.4s) | 376 baseline + 6 baru; skip = `tests/unit/test_radius_config.py:133` (binari freeradius tidak tersedia — pre-existing); 3 warning pre-existing (thread cleanup pytest) |
| 6 | `MT_ENV=test .venv/bin/python manage.py check` | **0 issues** | |
| 7 | `python3 docs/tools/check_docs.py` | **PASS** (22 files, 67 internal links) | `docs/progress.md` = dynamic file (tidak di-hash manifest); `report/**` di luar cakupan manifest → tidak perlu `--refresh`; tidak ada file kontrak docs yang diubah |

Marker tes dan strategi identik dengan sesi PA-001 sebelumnya
(`django_db(transaction=True, available_apps=[...])`; tanpa monkeypatch jalur produksi;
kegagalan terkontrol pasca-tulis disuntik lewat bloker data natural, bukan patch kode).

## 5. NOT_RUN / BLOCKED (jujur, dengan alasan)

- `bash scripts/test_radius.sh` (daemon FreeRADIUS nyata): **NOT_RUN** — binari freeradius
  tidak terpasang di sandbox; jalur RADIUS tidak tersentuh diff (suite pytest radius tetap
  hijau dalam run penuh #5).
- Frontend tsc/eslint/vitest/i18n/build: **NOT_RUN di sandbox** — diff tidak menyentuh
  `apps/web`/`locales/`; job `frontend` CI memverifikasi pada SHA kandidat.
- `make e2e` (Playwright): **NOT_RUN** — UI tidak berubah pada packet ini.
- Rehearsal installer/upgrade (S4): **NOT_RUN** — sandbox tanpa systemd/root; di luar scope
  packet koreksi (code blocker installer REV-1111-04 TIDAK dikerjakan sesi ini).
- HTTP idempotency/principal-scope konkurensi: **NOT_RUN** — tetap packet **PA-006**
  (pemisahan eksplisit sesuai catatan reviewer finance).
- Job engine fencing/drain (PA-002): **NOT_RUN** — packet terpisah.
- Verifikasi CI GitHub Actions pada SHA push: dilakukan **setelah push** via API (lihat §8);
  angka lokal di atas adalah bukti sandbox.

## 6. Kompatibilitas & keamanan

- **Tanpa migrasi skema / tanpa perubahan kontrak API**: 382 tes existing+hijau; perubahan
  perilaku yang disengaja dan dicatat: (a) `invoice_id` salah bentuk kini 422
  `validation_error` (sebelumnya 404 "invoice tidak ada" — sesuai acceptance REV-1111-01);
  (b) ejaan alias satu invoice tergabung satu alokasi (sebelumnya menabrak constraint /
  baris ganda); (c) urutan hasil + customer/bahasa kwitansi KEMBALI ke perilaku pra-PA-001
  (invoice pertama-diminta) — memperbaiki regresi semantik yang diperkenalkan kandidat
  PR #9.
- Urutan kunci: payment → invoice(s) urut identitas canonical → tenant (penomoran
  kwitansi). Penahan kunci selama render PDF dalam transaksi tetap (risiko dicatat;
  pemindahan I/O keluar transaksi = PA-002, sengaja tidak diperluas).
- Tenant isolation/RLS tidak berubah; audit + outbox tetap satu transaksi dengan alokasi.
- Tidak ada secret/credential/token pada diff (scan `github_pat|password|secret|token`
  bersih); PAT GitHub hanya dipakai untuk push dari sandbox, tidak pernah masuk repo.
  **Rotasi PAT tetap disarankan** (melewati kanal chat).

## 7. Observasi di luar scope (untuk controller, tidak dieksekusi)

- Code blockers REV-1111-04–09 (installer, upgrade/repair gates, worker fencing, restore,
  topology DEC-01, scheduler) **tetap terbuka** dan kini tercantum eksplisit di
  LATEST_HANDOFF.md §3 — tidak dikerjakan sesi ini sesuai batas packet.
- REV-1111-11 (security/idempotency/seleksi) menunggu packet PA-006/PA-002/PA-003.
- PR #8 docs manifest (DEC-02) dan PR #7 SSTP tetap milik branch masing-masing; tidak
  disentuh.

## 8. Status publikasi

- Branch: `session/2026-11-11-pa001-payment-concurrency` (branch PR #9 milik executor —
  lanjutan pada branch yang sama, bukan branch baru; PR #7/#8 tidak tersentuh).
- Commit: `fix(billing)` (services + tests) dan `docs(handoff)` (persist 3 laporan review +
  laporan ini + koreksi LATEST_HANDOFF.md + checkpoint progress.md).
- PR #9 diperbarui otomatis oleh push; SHA remote kandidat + status CI diverifikasi via
  API Git **setelah push** (angka final dicatat pada komentar PR #9 oleh sesi ini dan
  menjadi input review controller berikutnya; bila push gagal, sesi ini mencatat
  NOT_PUSHED + error aman).
- Tidak ada direct-push main, tidak ada force-push, tidak ada merge (menunggu verdict
  review controller pada SHA baru), tidak ada deploy.

## 9. Remaining risk & next step eksak

- Risiko tersisa PA-001: penahan kunci selama render PDF (PA-002); tes level service bukan
  HTTP multi-request nyata (PA-006); representasi non-UUID (mis. int besar) tetap ditolak
  422 sesuai desain.
- Next step eksak untuk controller: review ulang PR #9 pada SHA baru (diff §2, bukti §4,
  acceptance Lampiran A terpenuhi: alias/compact/uppercase tergabung satu identitas +
  urutan identitas konsisten terbukti kontensi terkontrol; malformed 422; header/bahasa
  kuitansi kompatibel; rollback pasca-tulis + file yatim terpisah) → verdict
  ACCEPTED FOR NEXT SANDBOX STEP / REQUEST CHANGES. Packet berikutnya sesuai prioritas
  review: **PA-006** (uang/idempotency tuntas) atau **PA-002+PA-003** (job lifecycle
  authority/fencing); DEC-01 wajib sebelum topology rehearsal.
