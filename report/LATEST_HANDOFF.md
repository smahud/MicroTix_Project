# LATEST_HANDOFF — Kanonis (14 November 2026: controller meminta koreksi PA-006)

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md); CONTRACT §6A wajib. Fetch refs sebelum bertindak. Status main bisa tertinggal dari keputusan/candidate yang belum merged; jangan mengulang implementasi dari unfinished filename main saja.

## 0. Task aktif dan exact next action

| Field | Status / pointer |
|---|---|
| Canonical main | `9903d9b0cf09d737b553da3c21067b4810e956c0` — diperiksa sesi14 November; tidak diubah controller |
| Active task | [0010 / PA-006](../task/0010-pa006-idempotency.md), filename unfinished kembali pada ref keputusan; ID tetap |
| Execution / review | **ready / changes_requested**; tiga finding lama masih terbuka dan satu gap bukti wajib |
| Candidate / reviewed SHA | [PR17](https://github.com/smahud/MicroTix_Project/pull/17), `session/2026-11-14-pa006-idempotency@37a87291ae66a0fa9167f0c72d1e8340aa5fd245` |
| Executor implementation / tested SHA | Produksi5922e1f, tested774b191; descendant37a8729 hanya metadata terhadap backend/apps/config. Root checks pada candidate source37a8729 |
| Execution / internal review | [Executor report](orchestrator/20261114T150000Z-0010-pa006-idempotency.md), [internal review](reviewer/20261114T150000Z-0010-pa006-review.md); dipertahankan sebagai riwayat executor, bukan acceptance |
| Controller decision | [Review14 November](controller/20261114T153739Z-0010-pa006-review.md) — `changes_requested`, reviewed37a8729; independent runtime-source/migration reports ditautkan di dalam |
| Instruction / decision branch | `review/0010-pa006-controller-20261114`, record-only descendant PR17, belum integrated; publication SHA/PR diverifikasi setelah commit dan dicatat di report |
| Prior correction history | [PR16 record exact5da0d80](https://github.com/smahud/MicroTix_Project/blob/5da0d801c71b020fbb8b977294502ea5a09e7bcb/report/controller/20261113T114222Z-0010-pa006-review.md) atas PR15; tidak dibawa oleh PR17, tiga finding tetap berlaku; refs historis dipertahankan |
| Next actor | **coding_agent** |
| Exact next action | Fetch ref keputusan ini; bawa packet/riwayat secara semantik, tutup REV-1311-01/02/03 dan REV-1411-04, jalankan closing tests + acceptance/regression penuh, resubmit exact SHA baru pada ID0010 |
| Dependent work | PA-002/003 belum eligible; task0020 tidak dibuka; tidak ada merge/deploy/release otomatis |

## 1. Hasil review dan batas bukti

Root PostgreSQL17.11 nyata, Python3.13.5, peran runtime NOSUPERUSER/NOBYPASSRLS; RLS+FORCE tetap aktif. Targeted48 passed (termasuk PA-00110/10); full401 passed (3 adapter-thread warnings); check/migration consistency/docs PASS. Candidate CI [43609853986](https://github.com/smahud/MicroTix_Project/actions/runs/43609853986) backend/frontend/docs success pada37a8729. **Enam conformance probes gagal** dengan assertion acceptance, tanpa setup/teardown error pada run final. Semua command/log/limits ada di laporan controller.

- **REV-1311-01 P1 OPEN**: actual main upload→migration0004→same-key retry menghasilkan submission/file1→2; injected old-schema no-response claim dipurge lalu retry menambah invoice kedua.
- **REV-1311-02 P1 OPEN**: sesi migrasi A/B menerima204/204 tetapi decision count[2,0]; cache grup melewati parent malformed422/missing404.
- **REV-1311-03 P2 OPEN**: equivalent package UUID body alias200→409; raw typed identity belum canonical sebelum HMAC.
- **REV-1411-04 P2**: race tests direct `.post`/fake request, lock observations tidak diwajibkan berhasil, after-write rollback+waiting-contender takeover belum terbukti melalui HTTP authenticated.

Perbaikan principal/fresh invoice/platform/atomic yang benar tetap dipertahankan. Kebutuhan dan tabel acceptance awal dipulihkan pada packet lengkap; klaim executor seluruh PASS dan penutupan REV-1111-11 dibantah bukti. Histori executor tidak dihapus atau diedit agar tampak lulus.

NOT_RUN: host Gate A/G, install/upgrade/restore/DR, CHR/GNS3/live network, live RADIUS auth/accounting, pilot, benchmarkS6; frontend lokal tidak dijalankan (bukti CI diatribusikan ke GitHub). Actual sandbox source/schema transition bukan rehearsal installer host. Beta tetap **NOT_READY**.

## 2. Riwayat kandidat dan kepemilikan

PR9/PA-001 sudah merged; tidak diulang. PR15 calon13 November ditolak oleh PR16. PR17 calon14 November berawal dari main, bukan descendant koreksi PR16, dan gagal closing acceptance yang sama. Controller tidak mengimplementasikan aplikasi. Seluruh laporan dan refs lama tetap tersedia; packet saat ini menautkan record immutable agar executor tidak kehilangan konteks.

## 3. Bloker beta — CODE blockers (jujur; BUKAN hanya host/environment)

Register lengkap + baris bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4. Snapshot blocker existing; sesi ini memverifikasi scope PA-006, bukan mengaudit ulang scope lain:

| Code blocker (defect source, terbuka) | Temuan | Status PA-006 |
|---|---|---|
| Installer gagal clean-install (argumen ter-join; dependensi duplikat tanpa `xhtml2pdf`) | REV-1111-04 (P1) | TERBUKA (S4) |
| Upgrade/repair exit sukses palsu; repair turunkan HTTPS; readiness SELECT 1 | REV-1111-05 (P1) | TERBUKA (S4) |
| Worker tanpa drain/fencing; upgrade overwrite+migrate saat proses aktif | REV-1111-06 (P1) | TERBUKA (PA-002/PA-003, S2) |
| Restore end-to-end + pemisahan secret migrator belum terbukti | REV-1111-07 (P1) | TERBUKA (S4) |
| Topology deployment belum konsisten dengan ARCHITECTURE — DEC-01 belum resolved | REV-1111-08 (P1) | TERBUKA (keputusan pemilik) |
| Scheduler invoice belum diimplementasikan | REV-1111-09 (P1) | TERBUKA (S4) |
| Security/idempotency/seleksi kontrak terbuka | REV-1111-11 (P1) | **TERBUKA** — PR17 changes_requested: REV-1311-01/02/03 + REV-1411-04; PA-006 belum accepted. Permission lifecycle/selected-set/scanner bukan ditutup oleh perbaikan idempotency |
| Kapasitas target 1.000×1.000 belum dibuktikan benchmark | REV-1111-12 (P2) | TERBUKA (S6/G4-G5) |

Environment blockers (prasyarat eksternal, TETAP ADA): Gate A/G host Debian 13 nyata; G1 lab MikroTik CHR/fisik; lab GNS3 API-driven (CONTRACT §7).

## 4. Cabang/PR belum merged — jangan ditimpa

| PR | Branch / fungsi |
|---|---|
| 17 | `session/2026-11-14-pa006-idempotency` — candidate37a8729, changes_requested oleh keputusan sesi ini |
| 16 | `review/0010-pa006-controller-20261113` — prior corrections5da0d80 atas PR15 |
| 15 | `session/2026-11-13-pa006-idempotency` — candidate lama7480c80, belum accepted |
| 14 | `docs/payment-point-planning-20261113` — DANA planning, terpisah/default disabled, bukan task Beta ini |
| 13 | `review/0010-pa006-submission-check-20261112` — snapshot not_submitted historis, sudah ada candidate setelahnya |
| 8 | `docs/planning-audit-20261110` — docs/manifest ownership tetap terpisah; status CI historis di register |
| 7 | `session/2026-11-07-sstp-phase2` — SSTP terpisah; tidak dihitung integrated main |

Branch keputusan sesi ini `review/0010-pa006-controller-20261114` memuat report/task/handoff/progress/evidence; PR-nya dicatat setelah publication. Tidak ada PR lama ditutup/di-merge, force-push atau destructive cleanup. Arsip branch lain tetap dipertahankan.

## 5. Urutan kelanjutan

1. Coding agent koreksi task0010 empat finding di atas; kembali ke controller untuk exact-SHA review, belum ke PA-002/003.
2. Setelah acceptance/integration prerequisites terpenuhi, controller menyiapkan PA-002/PA-003 job fencing/drain/authority dari backlog existing.
3. DEC-01 topology sebelum rehearsalS4; DEC-02 docs/manifest milik PR8; PR7 SSTP disposition tetap terpisah.
4. Installer/upgrade/restore/scheduler blockersS4 dan host gates mengikuti prasyarat existing. FUP-001/002/003 dicatat untuk scope relevan; tidak memperluas0010 diam-diam.

## 6. Contoh bootstrap sandbox — pilih scope dari task guide

```bash
git fetch origin --prune
# Periksa status/worktree; gunakan branch task dari main aktual atau instruction ref yang sah.
# Jangan switch/reset di atas perubahan pihak lain; baca task/0000-start-here.md.
git log --oneline -5
# Sandbox uji (PostgreSQL 17 user-space + Python 3.13; tanpa systemd di sandbox z.ai):
MT_SANDBOX_BASE=/home/z/my-project bash docs/tools/setup_env.sh   # PG 17.11 + FreeRADIUS 3.2.7 deb-extract
cd backend && MT_PG_BIN=/home/z/my-project/pgbin/pg17 bash scripts/dev_bootstrap.sh
# (venv: uv venv .venv --python /usr/bin/python3.13 --seed bila python3.13-venv absen)
MT_ENV=test .venv/bin/python -m pytest tests -q   # root401 passed pada candidate37a8729; bukan seluruh acceptance PASS
env -u DATABASE_URL MT_ENV=test .venv/bin/python manage.py check   # 0 issue
python3 docs/tools/check_docs.py
```

## 7. Risiko dan batas verifikasi

- Lock invoice selama render kwitansi dalam transaksi tetap scopePA-002; sesi ini tidak mengubahnya.
- PA-006 concurrent HTTP/forced lock/after-write rollback+contender takeover **BELUM TERBUKTI** sesuai REV-1411-04. CI menjalankan suite yang sama dan tidak menambahkan bukti concurrent HTTP yang hilang.
- Klaim observasi Django pg_stat_activity flaky berasal dari laporan executor; root tidak menggeneralisasikannya sebagai fakta platform. PID saja tidak membuktikan lock yang diwajibkan.
- Mutasi router tetap simulator; G1 nyata belum verified. Kapasitas1.000×1.000 belum dibenchmark.
- Controller meminta changes_requested; record/versioned publication pada §0 dan laporan controller. REV-1111-11 tetap terbuka.
- Tidak ada kredensial produksi atau akses deployment diserahkan; sesi controller memakai koneksi GitHub yang tersedia dan tidak memakai PAT percakapan lama.
