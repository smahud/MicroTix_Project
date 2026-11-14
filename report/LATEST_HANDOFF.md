# LATEST_HANDOFF — Kanonis (14 November 2026: PA-006 diserahkan untuk review)

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md), wajib menurut CONTRACT §6A. Handoff ini menyimpan status sesi aktual; docs/AGENT_HANDOFF.md hanya panduan navigasi/bootstrap.

## 0. Status sesi — penyerahan task0010/PA-006 (14 November 2026)

Sesi executor sandbox: implementasi PA-006 selesai pada branch kandidat `session/2026-11-14-pa006-idempotency` (base `main@9903d9b`, head terkini lihat PR, PR12 merged; source PA-006 pada baseline identik dengan `a0f653e` karena PR10–12 hanya dokumentasi). Tested SHA **`774b191`** (source produksi implementasi `5922e1f`: protokol idempotency 5-tuple canonical + claim/replay satu transaksi + migrasi jobs 0004 + 18 tes PA-006; `774b191` = fix portabilitas observer tes untuk CI service port 5432 tanpa perubahan source produksi; suite 401 passed pada konten `774b191`); commit metadata setelahnya report/metadata-only. Fetch HEAD aktual sebelum bertindak; jangan mengunci pada snapshot ini.

| Field handoff | Status / pointer |
|---|---|
| Active task | ID0010 / PA-006 — **penyerahan executor selesai** (`0010-pa006-idempotency_done.md` pada branch kandidat) |
| Execution / review | `done` / `pending` — menunggu controller review exact SHA |
| Candidate branch / tested SHA / PR | `session/2026-11-14-pa006-idempotency`; tested SHA `5922e1f`; **[PR #17](https://github.com/smahud/MicroTix_Project/pull/17)** (head terverifikasi `7243c263d35af7749c5133e8591b6854bff95257`) |
| Execution report / acceptance evidence | `report/orchestrator/20261114T150000Z-0010-pa006-idempotency.md` — matriks SEMUA acceptance → actual result → evidence (18/18 PASS; suite penuh 401 passed; PA-001 10/10) + tabel 28 call site + kebijakan migrasi/legacy |
| Internal reviewer | `report/reviewer/20261114T150000Z-0010-pa006-review.md` — LULUS DENGAN CATATAN (6 temuan P3, tanpa P1/P2; koreksi minimum diterapkan sebelum penyerahan). Review internal executor, BUKAN acceptance controller |
| Controller review / reviewed SHA | Belum ada — next actor controller_reviewer |
| Next actor | **controller_reviewer** |
| Exact next action | Review kandidat exact SHA `774b191` (source produksi `5922e1f`; `774b191` hanya fix portabilitas observer tes CI — diff 1 file tes): tabel call-site, interleaving tes konkuren, kebijakan migrasi/legacy 0004 (backfill/dedupe/purge/preservasi opaque), no auth bypass, dan tiga FUP terdokumentasi (FUP-001 resolve_membership malformed tenant 500; FUP-002 berkas yatim; FUP-003 iterasi antrean platform). Changes requested → buka kembali task0010 ID sama (rename balik unfinished) |

Protokol lengkap ada pada panduan tetap §6 dan CONTRACT §6A. Verdict/corrections dan next actor/action harus dipush/verified di GitHub sebelum berganti peran; tidak ditinggalkan hanya di chat. Internal executor review bukan controller acceptance.

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` @ **`9903d9b`** (default prompts PR12 merged). Instruksi kandidat PA-006 pada branch `session/2026-11-14-pa006-idempotency` sampai integrasi; fetch HEAD aktual, bukan menganggap snapshot selalu terbaru |
| **Kandidat aktif** | **task0010/PA-006** di **[PR #17](https://github.com/smahud/MicroTix_Project/pull/17)** (branch `session/2026-11-14-pa006-idempotency`, head `7243c26`, tested SHA `5922e1f`); execution report + internal review terpublish pada branch yang sama; menunggu controller review |
| PR lain terbuka | **#7** SSTP Phase-2 (head `d7fa35e`; CI backend/frontend success, docs FAIL **manifest mismatch** — bukan bukti SSTP gagal runtime; disposition = packet terpisah) · **#8** docs planning-audit DRAFT (head `6bb57c9`; CI docs FAIL manifest mismatch = pekerjaan DEC-02, branch itu pemilik file manifest — jaga ownership disjoint) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — bloker = code blockers (§3) + environment blockers; REV-1111-11 (idempotency HTTP) ditutup pada kandidat PA-006 menunggu review exact SHA |
| CONTRACT.md | §6A task workflow/komunikasi tetap berlaku, ditambah default prompts per peran (12 November 2026) |
| Prioritas aktif | Review PA-006 (controller) → setelah accepted: PA-002/PA-003 (job fencing/drain/authority), DEC-01 topology, DEC-02 manifest docs |

## 2. Riwayat implementasi terakhir — task0010/PA-006 (bukti di laporan eksekutor)

Sesi 2026-11-14 (sandbox Z.ai, PostgreSQL 17.11 nyata, peran runtime non-superuser `mtx_app`):

1. **Protokol claim/replay satu transaksi** (`common/idempotency.py`): identitas
   canonical 5-tuple (principal + tenant/platform + operation + resource + key);
   claim `INSERT … ON CONFLICT DO NOTHING RETURNING`; konkuren same-identity menunggu
   lalu MEREPLAY (bukan 409 permanen/500/duplikat); respons 2xx tersimpan dalam
   transaksi yang sama dengan efek; exception → rollback klaim+efek → retry key
   semula; record tanpa respons ditolak aman (bukan eksekusi ulang buta).
2. **Migrasi jobs 0004**: kolom identitas + `uq_idem_identity`; backfill canonical;
   dedupe alias (terbaru ber-respons dipertahankan); purge klaim tanpa respons/
   salah bentuk; resource opaque (`identity_conflict_resolve` group_id) dipertahankan
   verbatim; reverse jujur (tabel kosong) + fix-forward terdokumentasi.
3. **Call-site**: `payment_submission` resource `invoice_id` (bug scope packet);
   `platform_submission_approve/reject/revision` `platform=True` (scope platform
   stabil lintas active tenant); `identity_conflict_resolve` `resource_uuid=False`.
4. **Bukti**: 18 tes PA-006 (interleaving dipaksa penahanan kunci baris + observasi
   `pg_stat_activity` via pengamat psycopg; klien HTTP independen per principal);
   suite penuh **401 passed** (baseline 383); PA-001 **10/10** tetap; `manage.py
   check` 0; `makemigrations --check` bersih; docs PASS; frontend tsc/eslint/
   vitest 66/i18n/build-live bersih. Matriks acceptance lengkap di laporan eksekusi §5.

## 3. Bloker beta — CODE blockers (jujur; BUKAN hanya host/environment)

Register lengkap + baris bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4. Pembaruan status setelah kandidat PA-006:

| Code blocker (defect source, terbuka) | Temuan | Status PA-006 |
|---|---|---|
| Installer gagal clean-install (argumen ter-join; dependensi duplikat tanpa `xhtml2pdf`) | REV-1111-04 (P1) | TERBUKA (S4) |
| Upgrade/repair exit sukses palsu; repair turunkan HTTPS; readiness SELECT 1 | REV-1111-05 (P1) | TERBUKA (S4) |
| Worker tanpa drain/fencing; upgrade overwrite+migrate saat proses aktif | REV-1111-06 (P1) | TERBUKA (PA-002/PA-003, S2) |
| Restore end-to-end + pemisahan secret migrator belum terbukti | REV-1111-07 (P1) | TERBUKA (S4) |
| Topology deployment belum konsisten dengan ARCHITECTURE — DEC-01 belum resolved | REV-1111-08 (P1) | TERBUKA (keputusan pemilik) |
| Scheduler invoice belum diimplementasikan | REV-1111-09 (P1) | TERBUKA (S4) |
| Security/idempotency/seleksi kontrak terbuka | REV-1111-11 (P1) | **KANDIDAT TERTUTUP pada SHA `5922e1f`** (principal-scoped idempotency, HTTP replay/race, selected-set terkait idempotency) — menunggu review exact SHA; temuan turunan baru: FUP-001 (`resolve_membership` malformed tenant 500), FUP-002 (berkas yatim), FUP-003 (iterasi antrean platform) — dicatat berbukti, belum ditugaskan |
| Kapasitas target 1.000×1.000 belum dibuktikan benchmark | REV-1111-12 (P2) | TERBUKA (S6/G4-G5) |

Environment blockers (prasyarat eksternal, TETAP ADA): Gate A/G host Debian 13 nyata; G1 lab MikroTik CHR/fisik; lab GNS3 API-driven (CONTRACT §7).

## 4. Cabang kerja

- `session/2026-11-14-pa006-idempotency` — **KANDIDAT task0010/PA-006, PR #17**
  (tested SHA `5922e1f`; head `7243c26` — report-only metadata commits setelah
  tested SHA; remote diverifikasi).
- Terbuka milik pihak lain (JANGAN ditimpa): `docs/planning-audit-20261110` (PR #8),
  `session/2026-11-07-sstp-phase2` (PR #7).
- `session/2026-11-11-pa001-payment-concurrency` — MERGED (PR #9; arsip riwayat).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2` (unmerged),
  `integration/beta-0.1`, `session/2026-11-06/07-*`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **Review controller PA-006** pada exact SHA `774b191` (kandidat PR #17 di atas; source produksi `5922e1f`).
   Changes requested → koreksi ID sama; accepted → catat SHA + evidence, siapkan
   task penerus.
2. **PA-002 + authority PA-003 (P1)** — job lifecycle fencing/drain (termasuk risiko
   tersisa PA-001: penahan kunci invoice selama render kwitansi PDF dalam transaksi;
   runworker tanpa drain; write tanpa ownership check).
3. **DEC-01** — keputusan topology (wajib sebelum rehearsal S4; executor menyiapkan
   proposal biaya/risiko/isolasi, BUKAN mengubah ARCHITECTURE/CONTRACT).
4. **DEC-02** — PR #8 docs/manifest (branch itu pemilik file — jaga ownership disjoint).
5. **PR #7 disposition** (SSTP Phase-2; docs CI fail = manifest mismatch).
6. Installer/upgrade/restore/scheduler code blockers (REV-1111-04/05/07/09) — S4
   setelah DEC-01; ops host Gate A/G setelah code blocker ditutup.
7. FUP-001/002/003 hasil PA-006 — masukkan ke packet berikutnya yang relevan
   (FUP-001 kandidat packet API hygiene kecil; FUP-002 bersama pekerjaan dokumen;
   FUP-003 bersama PA-002/003).

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
MT_ENV=test .venv/bin/python -m pytest tests -q   # 401 passed pasca-PA-006 (383 baseline)
env -u DATABASE_URL MT_ENV=test .venv/bin/python manage.py check   # 0 issue
python3 docs/tools/check_docs.py
```

## 7. Risiko & keterbatasan yang diketahui

- Penahan kunci baris invoice selama transaksi verifikasi (termasuk render PDF
  kwitansi) — pemindahan I/O keluar transaksi = lingkup **PA-002**.
- Tes konkurensi PA-006 protokol memanggil method view terdekorasi langsung
  (jalur produksi decorator+service, tanpa test client multi-thread yang diketahui
  tidak thread-safe); boundary HTTP diuji klien independen sekuensial — bukti
  multi-request HTTP truly-paralel tetap lewat CI runner.
- Observasi `pg_stat_activity` lintas sesi pada sandbox ini flaky bila dilakukan
  dari koneksi Django main (superuser selalu melihat) — tes PA-006 memakai pengamat
  psycopg terpisah yang stabil; dicatat pada laporan eksekusi (keanehan sandbox,
  bukan produk).
- Mutasi router tetap jalur simulator (capability.source=simulator) — tidak ada
  klaim perangkat nyata (G1).
- Kapasitas 1.000 tenant × 1.000 online tetap klaim desain, bukan benchmark.
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan.
- Verdict review controller PA-006 belum diterbitkan — register REV-1111 tetap
  rujukan; REV-1111-11 hanya ditutup jika review menerima kandidat.
- **PAT GitHub hanya dipakai untuk fetch/push/PR dari sandbox (tidak pernah
  di-commit; scan diff bersih). Rotasi PAT tetap disarankan** karena melewati
  kanal chat.
