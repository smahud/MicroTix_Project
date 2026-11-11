# Sesi Executor Sandbox — Verifikasi independen & integrasi merge PR #9 (PA-001 tuntas di main)

- **Role/author**: Executor (sesi integrasi tunggal, tanpa sub-agent — packet verifikasi+merge
  kecil dan kohesif sesuai CONTRACT §5; sub-agent tidak menambah nilai: verifikasi adalah
  menjalankan command deterministik dan membaca hasil).
- **Tanggal (UTC)**: 2026-11-11T14:46Z mulai; laporan ditulis 2026-11-11T14:54Z
  (waktu lokal sandbox Asia/Jakarta 21:46–21:54).
- **Objective**: (1) Menjalankan packet §8 dokumen review controller 2026-11-11 pada keadaan
  aktual repository; (2) verifikasi independen kandidat kedua PR #9 (`482602e`) di sandbox
  segar (sandbox platform didaur ulang penuh sejak sesi verifikasi kedua — lingkungan
  dibangun ulang dari nol); (3) integrasi merge PR #9 ke main atas wewenang eksplisit
  pemilik repo (PAT GitHub diserahkan pemilik via kanal chat dengan instruksi
  "commit, merge, atau push" — hirarki keputusan CONTRACT §12: keputusan user disetujui
  eksplisit mengikat).
- **Starting state**: clone segar; `main` @ `16085f825fef25ee4112d74b729c57e623b0bb05`
  (identik snapshot controller 2026-11-11T07:42:25Z — diverifikasi fetch ulang);
  PR #9 head `482602ecad6616167d14f2b30cd60e2039093fe9` (BERUBAH sejak review
  `3b20b56` → delta 2 commit koreksi dieksekutor sebelumnya, direview delta-first
  sesuai instruksi packet §8.1). PR #7 (`d7fa35e`) / PR #8 (`6bb57c9`) tidak tersentuh.
- **Requirement/finding IDs**: instruksi packet §8 dokumen review
  `report/controller/20261111T074225Z-repo-handoff-review.md`; acceptance Lampiran A
  (finance reviewer); CONTRACT §10 (laporan), §11 (integrasi git), §12 (hirarki keputusan);
  REV-1111-01/02/03/10 (koreksi yang diverifikasi ulang).

## 1. Review delta sejak SHA review (packet §8.1 — SHA berubah, delta direview dulu)

`3b20b56..482602e` = 2 commit executor sebelumnya:

1. `47d1bf7` `fix(billing)` — REV-1111-01/02: `_canonical_invoice_id` (uuid.UUID →
   kanonik; salah bentuk → 422 `ApiError.validation`), merge + `sorted()` pada identitas
   kanonik, hasil dikembalikan urutan permintaan teragregasi semula (customer/bahasa
   kwitansi I18N-01 tetap invoice pertama-diminta).
2. `482602e` `docs(handoff)` — REV-1111-10 + REV-1111-03 (tes): handoff/progress
   dikoreksi (code blockers eksplisit), 6 tes regresi baru (alias merge; malformed 422;
   kwitansi multi-customer; rollback pasca-tulis; kontensi terkontrol pg_stat_activity +
   probe NOWAIT; konkurensi campuran ejaan), 3 laporan review dipersist verbatim di
   `report/` (CONTRACT §10).

Audit delta oleh sesi ini: kode `services.py` dibaca baris-per-baris (implementasi sesuai
"smallest correction" reviewer — tanpa migrasi, tanpa kontrak API baru, tanpa penolakan
representasi valid yang sebelumnya diterima); ketiga laporan persist diverifikasi lengkap
(Lampiran B bersih dari fragmen duplikat tempelan upload — keputusan didukung: seluruh
kalimat fragmen sudah ada utuh di badan dokumen); klaim dua komentar PR #9 (eksekusi
09:39Z, verifikasi ulang 13:29Z) dikonfirmasi via API.

## 2. Verifikasi independen sesi ini (sandbox segah, PostgreSQL 17.11 nyata)

Lingkungan dibangun ulang dari nol (bukan artefak sesi sebelumnya):
`docs/tools/setup_env.sh` (PG 17.11 deb-extract non-root `/home/z/pgbase` + FreeRADIUS
3.2.7 deb-extract) → `MT_PG_BIN=… bash backend/scripts/dev_bootstrap.sh` (venv
`uv venv --python /usr/bin/python3.13` 3.13.5; peran `mtx_migrator`/`mtx_app`; migrasi +
`grant_runtime`; seed dev). `DATABASE_URL` ambien sandbox (sqlite Next.js) dibersihkan
untuk `manage.py check`.

| # | Perintah (cwd `backend/`) | Hasil |
|---|---|---|
| 1 | `MT_ENV=test .venv/bin/python -m pytest tests/integration/test_billing_payment_concurrency.py -q` | **10 passed** (4.59s) |
| 2 | idem, diulang 2× | **10 passed** (5.29s; 5.71s) — stabil 3 run |
| 3 | Sensitivitas: `git show 3b20b56:…services.py > …/services.py` lalu #1 | **5 dari 6 tes baru GAGAL**: alias-merge (IntegrityError `uq_bilalloc_pair`), malformed-422 (kode lama 404), receipt-order (customer/bahasa salah), probe urutan kunci (invoice kedua terkunci sebelum pertama), konkurensi alias — **`OperationalError: deadlock detected … while locking tuple … in relation "billing_internet_invoice"`** (PostgreSQL nyata; persis prediksi REV-1111-01). Rollback pasca-tulis lolos di kedua kode (kemampuan rollback, bukan penolak defect lama — konsisten laporan sebelumnya) |
| 4 | Restore kode fix (`cp /tmp/services_fixed.py`) lalu #1 | **10 passed** (5.63s); `git status` clean |
| 5 | `MT_ENV=test .venv/bin/python -m pytest tests -q` | **382 passed, 1 skipped, 3 warnings** (38.93s) — paritas CI (skip = biner freeradius belum di-path, pre-existing) |
| 6 | `LD_LIBRARY_PATH=…frdeb… MT_FREERADIUS_BIN=… MT_FREERADIUS_ROOT=… MT_ENV=test pytest tests -q` | **383 passed, 3 warnings** (38.72s) — tes radius real-binary 3.2.7 ikut hijau |
| 7 | `env -u DATABASE_URL MT_ENV=test .venv/bin/python manage.py check` | **0 issues** |
| 8 | `python3 docs/tools/check_docs.py` | **PASS** (22 files, 67 internal links; runtime tests 0 — static check saja) |

CI remote diverifikasi via API: run [42996597547](https://github.com/smahud/MicroTix_Project/actions/runs/42996597547)
pada `482602e` — job **backend/frontend/docs seluruhnya success** (backend: unit+integrasi+
kontrak PostgreSQL nyata + peran runtime non-privilege; frontend: typecheck/lint/vitest/
i18n/build produksi; docs: static check). `mergeable_state: clean`.

Scan credential diff `16085f8..482602e` (2.181 baris): **bersih** — tidak ada
`github_pat_`/`ghp_`/AKIA/private key; satu-satunya "password" adalah fixture sintetis
user tes (`test-password-1234567890`) dan teks dokumentasi temuan.

## 3. Keputusan integrasi (merge) + justifikasi

**PR #9 MERGED ke main** (merge commit `8ce94d468232eda77cd675f6d18e5fcb41f3d708`,
metode merge-commit sesuai konvensi riwayat PR #4–#6; tidak ada force-push).

Justifikasi lengkap:

1. **Wewenang**: pemilik repo menyerahkan PAT via kanal chat dengan instruksi eksplisit
   "gunakan untuk commit, merge, atau push" — persetujuan pemilik atas integrasi
   (CONTRACT §11 "only merge after required approvals": approval = instruksi pemilik;
   CONTRACT §12 hirarki keputusan: keputusan user eksplisit mengikat).
2. **Acceptance Lampiran A terpenuhi seluruhnya** dan dibuktikan tes yang sensitif
   terhadap defect (sensitivitas diverifikasi ulang sesi ini, termasuk deadlock nyata
   pada kode kandidat pertama): alias/compact/uppercase tergabung satu identitas; urutan
   kunci = urutan identitas database (kontensi terkontrol); malformed 422; header/bahasa
   kwitansi kompatibel perilaku pra-PA-001; rollback pasca-tulis + file yatim terpisah.
3. **Release gates PR**: CI hijau 3 job pada SHA merge; suite penuh 383 passed di
   PostgreSQL nyata dengan peran RLS paritas CI; `manage.py check` 0 issue; docs PASS;
   tanpa perubahan migrasi/kontrak API (diff `16085f8..482602e`: 9 file — services.py,
   1 file tes, 3 laporan review persist, 1 laporan orchestrator, handoff, progress,
   dan tidak ada sentuhan installer/job engine/security/frontend).
4. **Tanpa merge, main tetap memuat bug P0** yang diakui controller ("PA-001 memperkenalkan
   row lock invoice sebelum membaca outstanding; pendekatan ini sesuai kebutuhan integritas
   dengan perubahan kecil"): lost-update/over-allocation dua payment konkuren — koreksi
   REV-1111 memperbaiki kandidat, bukan menolak pendekatannya.
5. **Merge ≠ deploy**: tidak ada deployment/aktivasi rilis; `v0.1.0-beta.1` tetap
   NOT_READY (bloker §3 LATEST_HANDOFF tidak berubah).

Batasan yang diakui: verdict re-review controller (ChatGPT) atas SHA `482602e` belum
diterbitkan saat merge — pemilik repo memutuskan integrasi langsung setelah dua putaran
verifikasi executor independen (sesi 13:29Z + sesi ini) dan CI hijau. Register temuan
REV-1111-04–09/11/12 TETAP TERBUKA dan kini menjadi bloker utama rilis (bukan PA-001).

## 4. Perubahan sesi ini

- **Tidak ada perubahan kode aplikasi** (verifikasi murni; worktree bersih sepanjang sesi
  kecuali jendela sensitivitas §2.3 yang direstorasi penuh).
- Merge PR #9 (GitHub API, `merge_method: merge`, SHA target dikunci `482602e`).
- Laporan ini + pembaruan `report/LATEST_HANDOFF.md` + checkpoint `docs/progress.md`
  (commit docs post-merge di main — pola sesi-sesi sebelumnya).

## 5. NOT_RUN / batas

- Rehearsal installer/upgrade (S4), restore/DR, daemon FreeRADIUS penuh
  (`scripts/test_radius.sh` — hanya `freeradius -C` validasi config via pytest yang
  dijalankan), Playwright e2e, HTTP idempotency konkuren (PA-006), perangkat nyata (G1):
  **NOT_RUN** — bukan scope packet; bloker terkait tetap terbuka di handoff §3.
- Review ulang controller (ChatGPT) pasca-merge atas `482602e`/`8ce94d4`: TIDAK DIHARAPKAN
  digantikan oleh laporan ini — register REV-1111 tetap rujukan; temuan PA-001 spesifik
  dianggap ditutup oleh acceptance Lampiran A + bukti §2, temuan lain tetap terbuka.

## 6. Keamanan & kompatibilitas

- PAT GitHub **tidak pernah ditulis ke repo** (scan diff bersih; hanya dipakai untuk
  fetch/push/merge via API). **Rotasi PAT tetap disarankan** (melewati kanal chat).
- Tanpa migrasi skema/kontrak API berubah; perubahan perilaku yang disengaja dan
  terdokumentasi (422 malformed id; alias merge; urutan kwitansi kembali perilaku
  pra-PA-001) — seluruhnya tercakup tes regresi permanen.
- Branch PR #7/#8 dan arsip tidak tersentuh; tidak ada force-push/destructive operation.

## 7. Status publikasi & verifikasi remote

- Merge diverifikasi: remote `main` @ `8ce94d468232eda77cd675f6d18e5fcb41f3d708`
  (fetch ulang pasca-merge; log menampilkan `Merge pull request #9 from
  smahud/session/2026-11-11-pa001-payment-concurrency`).
- Commit docs post-merge (laporan ini + handoff + progress):
  `6bd7be9c7a6979fd0d522a6f6250c928e157396f` + koreksi §7 ini — remote diverifikasi
  via fetch ulang setelah push (kontrak: tidak mengklaim push tanpa bukti remote).
- CI pada main pasca-merge diverifikasi via API check-runs:
  `6bd7be9` → **backend success, frontend success, docs success** (run lengkap
  termasuk suite 382 tes PostgreSQL + peran runtime non-privilege).
- Tidak ada tag rilis dibuat; `v0.1.0-beta.1` tetap NOT_READY.

## 8. Next step eksak

1. **PA-006 (P1)** — principal-scoped idempotency + HTTP replay/race (packet uang
   berikutnya sesuai rekomendasi review §8: "Packet selanjutnya sesudah PR9 diterima:
   PA-006").
2. **PA-002 + PA-003 (P1)** — job lifecycle fencing/drain/authority (termasuk risiko
   tersisa PA-001: penahan kunci invoice selama render PDF dalam transaksi).
3. **DEC-01** — keputusan topology deployment (wajib sebelum rehearsal S4; executor
   menyiapkan proposal, pemilik memutuskan).
4. **DEC-02** — PR #8 docs manifest (branch pemilik file; ownership disjoint).
5. **PR #7 disposition** — SSTP Phase-2 (docs CI fail = manifest mismatch).
6. Installer/upgrade/restore code blockers (REV-1111-04/05/07/09) — S4 setelah DEC-01.
