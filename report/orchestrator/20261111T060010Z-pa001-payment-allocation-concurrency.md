# Sesi Executor Sandbox — PA-001 (P0): Integritas alokasi pembayaran internet

- **Role/author**: Executor utama (z.ai / sesi orchestrator tunggal, tanpa sub-agent — scope
  kecil dan kohesif; CONTRACT §5 memungkinkan serialisasi bila isolasi tidak dibutuhkan).
- **Tanggal (UTC)**: 2026-11-11T06:00Z (waktu lokal sandbox Asia/Jakarta 13:00).
- **Objective**: Menutup finding audit planning **PA-001 (P0)** — "dua payment berbeda dapat
  memakai invoice balance stale" — pada SHA aktual, dengan bukti PostgreSQL nyata dua koneksi,
  lalu commit/push/PR sesuai mandat master prompt revisi 2026-11-10 (sandbox terlebih dahulu).
- **Base branch/SHA**: `main` @ `16085f825fef25ee4112d74b729c57e623b0bb05` (clean tree saat
  mulai; diverifikasi `git status` + `git log`). Baseline audit planning merujuk SHA yang sama.
- **Requirement/finding IDs**: PA-001 (acceptance: dua koneksi PostgreSQL nyata, no
  overallocate/lost update, paid=sum allocation, receipt/audit atomic); kontrak produk
  BIL-03/AC-BIL (docs/PRODUCT.md), ARCHITECTURE.md §4/§5/§6 (tenant_scope = transaksi + RLS;
  idempotency; outbox/audit per kejadian domain).

## 1. Root cause (diverifikasi pada SHA aktual, bukan asumsi audit)

`backend/domains/billing/services.py::_parse_allocations` membaca baris invoice TANPA kunci
(`InternetInvoice.objects.filter(...).first()`) dan mengembalikan snapshot `paid_amount` ke
`verify_payment`, yang kemudian mengeksekusi read-modify-write Python
(`invoice.paid_amount += amount; invoice.save(...)`). `verify_payment` mengunci baris PAYMENT
(`select_for_update`) — itu hanya menserialisasi verifikasi payment yang SAMA. Dua payment
BERBEDA yang diverifikasi bersamaan terhadap invoice yang sama:

1. Kedua thread membaca `paid_amount` basi (keduanya 0) → validasi `outstanding` lolos ganda.
2. UPDATE kedua menimpa nilai pertama (lost update) → `paid_amount != SUM(alokasi)`.
3. Dua baris `PaymentAllocation` tetap tercatat → total alokasi bisa melebihi total tagihan.

`verify_payment` adalah satu-satunya penulis runtime `paid_amount` (diluar `seed_billing_e2e`
dev-only) — diperiksa via pencarian seluruh repo.

## 2. Reproduksi pada SHA dasar (bukti jujur, file sementara sudah dihapus)

Test reproduksi sementara (start-barrier antar thread, TANPA monkeypatch jalur produksi):
dua thread = dua koneksi PostgreSQL nyata (PID backend berbeda, diperiksa
`SELECT pg_backend_pid()`), masing-masing memanggil `services.verify_payment` di dalam
`tenant_scope` persis seperti view produksi. Invoice total 300.000; dua payment tunai
masing-masing 200.000; alokasi 200.000 per payment.

Hasil pada kode belum diperbaiki (`16085f8`): kedua verifikasi **"ok"**;
`paid=200000.00` tetapi **SUM(alokasi)=400000.00** pada invoice total 300000.00;
state invoice `partial`. → **Lost update + over-alocation terbukti** (PA-001 terkonfirmasi,
bukan hanya narasi audit). Transkrip: `RESULTS={'p1':'ok','p2':'ok'}`,
`PIDS={'p1':23601,'p2':23600}` (berbeda antar run — koneksi benar-benar terpisah).

## 3. Perubahan (smallest change)

`backend/domains/billing/services.py` (+17/−4, satu fungsi):

- `_parse_allocations` kini mengambil baris invoice dengan
  `InternetInvoice.objects.select_for_update()` **dalam urutan `sorted(merged)` (id
  deterministik)**. Sisa tagihan dibaca dari baris terkunci; verifikasi dua payment berbeda
  pada invoice yang sama terserialisasi di level baris PostgreSQL sampai transaksi selesai
  (receipt+audit+outbox satu transaksi via `tenant_scope` yang sudah ada).
- Urutan kunci seragam (id terurut) mencegah deadlock antar verifikasi dengan pasangan
  invoice tumpang tindih tetapi urutan body dibalik.
- Seluruh pemanggil existing (view API via `TenantApiView.dispatch` → `tenant_scope`, dan
  `seed_billing_e2e` dev command) sudah berjalan dalam transaksi aktif — kontrak `select_for_update`
  terpenuhi; tidak ada pemanggil baru.

File test baru: `backend/tests/integration/test_billing_payment_concurrency.py` (4 tes;
lihat §5).

**Alternatif dipertimbangkan dan ditolak (CONTRACT §3)**:
- CHECK constraint DB `paid_amount <= total_amount` (butuh migrasi skema): ditunda — perbaikan
  behavioral sudah menutup acceptance; satu-satunya penulis runtime sudah dikunci; permukaan
  migrasi/installer tidak perlu diperluas dalam packet P0 ini. Dicatat sebagai kandidat bila
  packet hardening skema (mis. PA-011) menghendakinya.
- UPDATE ekspresi `F()` + guard SQL: redundan — kunci baris dipegang sampai commit dan hanya
  ada satu kelas penulis; menambah kompleksitas tanpa menutup celah baru.
- `select_for_update(nowait=True)` + retry: mengubah semantik API (409 vs tunggu) tanpa
  kebutuhan; default blocking adalah serialisasi yang diinginkan.

## 4. Lingkungan sandbox (disposable, milik run ini)

- Container: Debian 13 (trixie), user non-root `z` (uid 1001), 2 vCPU/4 GB RAM, **tanpa
  systemd** (PID 1 = tini) → rehearsal installer S4 tidak mungkin di sesi ini (dicatat NOT_RUN,
  memang di luar scope PA-001).
- PostgreSQL **17.5** server user-space (binari build resmi PostgreSQL hasil redistribusi
  Zonky `embedded-postgres-binaries-linux-amd64` 17.5.0, Maven Central) di `/tmp/pgbin/pg17`;
  cluster initdb trust-auth di `backend/pgdata`, port 55432, peran `mtx_migrator` +
  `mtx_app` (CREATEDB) dan database `microtix` sesuai kontrak `backend/scripts/dev_bootstrap.sh`
  (langkah 1–2 direplikasi via psycopg karena binari `psql` tidak tersedia — skrip bootstrap
  di /home/z/my-project/scripts/mtx_pg_bootstrap.py, di luar repo). Migrasi dijalankan sebagai
  `mtx_migrator` + `manage.py grant_runtime` (paritas Makefile/CI).
- Python **3.13.5** venv terisolasi; dependensi patch-exact dari `pyproject.toml`
  (`pip install -e .` + pytest 8.4.2 + pytest-django 4.14.0) — Django 5.2.19, DRF 3.16.1,
  psycopg 3.2.13, xhtml2pdf 0.2.28 (identik pin CI).
- Fixture/sintetis semata (tenant `rtrw-cc00000x`, payment tunai) — tidak ada data pelanggan
  nyata, tidak ada target produksi, tidak ada credential apa pun dalam diff (scan bersih).

## 5. Bukti test (perintah nyata, cwd `backend/`, keluaran sesuai)

| # | Perintah | Hasil | Keterangan |
|---|---|---|---|
| 1 | `MT_ENV=test .venv/bin/python -m pytest tests -q` (SEBELUM perubahan) | **372 passed, 1 skipped** | Baseline jujur pada `16085f8`; skip = `tests/unit/test_radius_config.py:133` (binari freeradius tidak tersedia — alasan sah, pre-existing) |
| 2 | Test repro sementara pada kode dasar | **Bug TERBUKTI** | Kedua verifikasi ok; paid=200.000 ≠ SUM alokasi=400.000 > total 300.000; dua koneksi PG nyata (PID beda) |
| 3 | Skenario sama SETELAH perbaikan | **Satu ok + satu `ApiError(409/billing.allocation_exceeds_outstanding)`**; paid=200.000 == SUM alokasi=200.000; 1 alokasi | File repro dihapus setelah bukti dicatat |
| 4 | `MT_ENV=test .venv/bin/python -m pytest tests/integration/test_billing_payment_concurrency.py -q` | **4 passed** | (a) over-allocation ditolak bersih: tepat satu pemenang lengkap (allocation+state+kwitansi+audit+outbox=1/1/1/1), yang kalah nihil efek (0/0/0/0) dan payment tetap `submitted`; (b) 100rb+200rb: paid=300.000 == SUM == total, state `paid`, tanpa lost update; (c) pasangan invoice urutan body dibalik ([A,B] vs [B,A]): kedua invoice penuh, tanpa deadlock, nomor kwitansi unik; (d) alokasi [valid, melebihi sisa] → 409 dan TIDAK ada efek parsial |
| 5 | Sensitivitas regresi (stash perbaikan → jalankan tes baru) | **3 dari 4 GAGAL pada kode lama** (restore perbaikan → 4 passed) | Tes baru benar-benar menolak defect, bukan kosmetik |
| 6 | `MT_ENV=test .venv/bin/python -m pytest tests -q` (SETELAH perbaikan) | **376 passed, 1 skipped** | 372 baseline + 4 baru; 3 warning pre-existing (thread cleanup pytest); tidak ada regresi |
| 7 | Ulang file konkurensi 3× | **4 passed** tiap run | Stabilitas race test |
| 8 | `.venv/bin/python manage.py check` | **0 issues** | |
| 9 | `python3 docs/tools/check_docs.py` | **PASS** (22 files) | docs/** tidak diubah; manifest tidak perlu refresh |

Marker test: `django_db(transaction=True, available_apps=[domains.tenancy, identity,
customers, billing, documents, audit, jobs])` — commit nyata diperlukan agar setup terlihat
 oleh koneksi thread; flush teardown terbatas aplikasi yang dikotori + TRUNCATE CASCADE
(menghindari FK tabel radius unmanaged yang membuat `TransactionTestCase` polos gagal —
jalur ini belum pernah dipakai suite existing). RLS tetap aktif (seluruh query dalam
`tenant_scope`; suite `test_rls.py` hijau dalam run penuh).

## 6. NOT_RUN / BLOCKED (jujur, dengan alasan)

- `bash scripts/test_radius.sh` (daemon FreeRADIUS nyata): **NOT_RUN** — binari freeradius
  tidak terpasang di sandbox ini; jalur RADIUS tidak tersentuh diff (suite pytest radius
  tetap hijau dalam run penuh).
- Frontend tsc/eslint/vitest/i18n/build: **NOT_RUN di sandbox** — diff tidak menyentuh
  `apps/web`/`locales/`; job `frontend` CI akan memverifikasi pada SHA kandidat.
- `make e2e` (Playwright): **NOT_RUN** — UI billing tidak berubah pada packet ini (PA-008
  yang mengurus kontrak UI→API); biaya unduhan browser tidak proporsional.
- Rehearsal installer/upgrade (S4): **NOT_RUN** — tanpa systemd/root di sandbox; memang di
  luar scope PA-001; tidak ada migrasi skema sehingga `instalasi.sh` tidak terdampak.

## 7. Kompatibilitas & keamanan

- **Tanpa migrasi skema / tanpa perubahan API kontrak**: 372 tes existing hijau; satu-satunya
  perubahan perilaku = verifikasi yang berlomba kini ditolak 409 `billing.allocation_exceeds_outstanding`
  (sebelumnya: korupsi senyap). Urutan `resolved` kini id-terurut (kwitansi multi-invoice
  tampil urut stabil — tes existing order-insensitive tetap hijau).
- Urutan kunci: payment → invoice(s) terurut → tenant (penomoran kwitansi). Jalur penerbitan
  invoice mengunci tenant → INSERT (tanpa kunci invoice existing) — tidak ada inversi.
- Kunci baris invoice kini dipegang selama transaksi verifikasi (termasuk render PDF kwitansi
  — kelas penahan yang sama dengan kunci tenant yang sudah ada sebelumnya). Pemindahan I/O
  keluar transaksi adalah lingkup **PA-002**, sengaja tidak diperluas di sini (disiplin scope).
- Tenant isolation/RLS tidak berubah; audit `record()` + outbox tetap satu transaksi dengan
  alokasi (atomik, dibuktikan tes d).
- Tidak ada secret/credential/token pada diff (scan `github_pat|password|secret|token` bersih);
  PAT GitHub hanya dipakai untuk push dari sandbox, tidak pernah masuk repo. **Rotasi PAT tetap
  disarankan** (pernah melewati kanal chat — konsisten catatan handoff sebelumnya).

## 8. Observasi di luar scope (untuk controller, tidak dieksekusi)

- **PR #8** (`docs/planning-audit-20261110`, head `6bb57c9`) — CI **failure** (job docs;
  pola kegagalan konsisten dengan manifest yang belum di-refresh setelah edit docs = pekerjaan
  DEC-02, belum ditugaskan ke sesi ini). Branch itu pemilik file docs/manifest — packet ini
  sengaja tidak menyentuhnya agar ownership tetap disjoint.
- **PR #7** (`session/2026-11-07-sstp-phase2`, head `d7fa35e`) — CI failure; belum
  diinvestigasi (packet terpisah).
- `report/LATEST_HANDOFF.md` di main masih menyimpan SHA kanonis `8bb20c3` padahal main kini
  `16085f8` (dua commit docs sesudahnya) — diperbarui oleh sesi ini bersama checkpoint
  progress.md (tanpa menyalin laporan penuh).

## 9. Status publikasi

- Branch fitur: `session/2026-11-11-pa001-payment-concurrency` (dibuat dari `main` @ `16085f8`).
- Commit: source+tests (`fix(billing)`), laporan+handoff+progress (`docs(handoff)`).
- PR ke `main`: dibuka via API; SHA remote kandidat + status CI diverifikasi via API Git
  setelah push (angka final dicatat di LATEST_HANDOFF.md §1 sesuai hasil aktual — lihat
  handoff untuk SHA/CI terverifikasi; bila push/PR gagal, akan tercatat `NOT_PUSHED` + error
  aman).
- Tidak ada direct-push main, tidak ada force-push, pekerjaan pihak lain tidak disentuh.

## 10. Remaining risk & next step eksak

- Risiko tersisa: penahan kunci selama render PDF (PA-002); pengujian konkurensi di level
  service (bukan HTTP multi-request nyata — DRF test client tidak thread-safe; idempotency
  HTTP layer = PA-006); kapasitas 1.000×1.000 tetap klaim desain, bukan benchmark.
- Next step eksak untuk reviewer/controller: review PR (diff §3, bukti §5) → verdict
  ACCEPTED FOR NEXT SANDBOX STEP / REQUEST CHANGES. Kandidat packet berikutnya menurut
  prioritas master prompt: **PA-002** (job fencing/transaksi panjang) atau **DEC-02**
  (manifest + PR #8) bila controller memprioritaskan kebersihan CI docs.
