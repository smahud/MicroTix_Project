# LATEST_HANDOFF — Kanonis (sesi 2026-11-11 final: PR #9 diverifikasi independen & MERGED — PA-001 tuntas di main)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` @ **`8ce94d468232eda77cd675f6d18e5fcb41f3d708`** (merge PR #9; diverifikasi fetch ulang pasca-merge) — memuat PA-001 + seluruh koreksi REV-1111-01/02/03/10 |
| **PR sesi sebelumnya** | **#9 MERGED** (`session/2026-11-11-pa001-payment-concurrency`; kandidat pertama `3b20b56` REQUEST CHANGES → kandidat kedua `482602e` diverifikasi independen 2× + CI hijau → merge commit `8ce94d4` atas wewenang pemilik repo; lihat `report/orchestrator/20261111T145417Z-pr9-merge-integration.md`) |
| PR lain terbuka | **#7** SSTP Phase-2 (head `d7fa35e`; CI backend/frontend success, docs FAIL **manifest mismatch** — bukan bukti SSTP gagal runtime; disposition = packet terpisah) · **#8** docs planning-audit DRAFT (head `6bb57c9`; CI docs FAIL manifest mismatch = pekerjaan DEC-02, branch itu pemilik file manifest — jaga ownership disjoint) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — bloker = code blockers (§3) + environment blockers; klaim lama "penahan tunggal host / BUKAN pekerjaan kode" SUDAH DICABUT (REV-1111-10) |
| CONTRACT.md | Versi `1fff190` (tidak diubah) |
| Prioritas aktif | Mandat master prompt user 2026-11-10 (sandbox terlebih dahulu). PA-001 tuntas; packet berikutnya **PA-006** (uang/idempotency), lalu **PA-002+PA-003** (job lifecycle) |

## 2. Ringkasan sesi terakhir (bukti penuh di laporan orchestrator sesi masing-masing)

Sesi 2026-11-11 terdiri dari tiga tahap (semua laporan persist di `report/`):

1. **PA-001 + PR #9 kandidat pertama** (`3b20b56`; laporan
   `20261111T060010Z-pa001-payment-allocation-concurrency.md`): kunci baris invoice
   FOR UPDATE urutan deterministik + 4 tes konkurensi PostgreSQL; 376 passed.
2. **Koreksi REV-1111** (`47d1bf7`+`482602e`; laporan
   `20261111T092854Z-pa001-canonical-identity-corrections.md`): identitas UUID kanonik
   sebelum merge/urutan lock (REV-1111-01), hasil urutan permintaan semula — kwitansi
   I18N-01 kompatibel (REV-1111-02), +6 tes termasuk rollback pasca-tulis dan kontensi
   terkontrol pg_stat_activity+NOWAIT (REV-1111-03), handoff/progress dikoreksi + 3 laporan
   review dipersist (REV-1111-10). Verifikasi ulang independen sandbox segar 13:29Z
   (komentar PR #9): 10 passed file konkurensi; 5/6 tes baru gagal pada kode kandidat
   pertama termasuk deadlock nyata PostgreSQL; 383 passed suite penuh.
3. **Verifikasi independen + merge** (laporan
   `20261111T145417Z-pr9-merge-integration.md`): sandbox dibangun ulang dari nol
   (setup_env.sh PG 17.11 + FreeRADIUS 3.2.7 deb-extract); 10 passed stabil 3×;
   sensitivitas dikonfirmasi (5/6 gagal pada `3b20b56`, deadlock nyata); suite penuh
   **383 passed** (termasuk radius real-binary); `manage.py check` 0 issue; docs PASS;
   CI `482602e` 3 job success; scan credential diff bersih; **merge PR #9** atas
   wewenang eksplisit pemilik repo (PAT "commit, merge, atau push") — merge ≠ deploy.

## 3. Bloker beta — CODE blockers (jujur; BUKAN hanya host/environment)

Register lengkap + baris bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4.

| Code blocker (defect source, terbuka) | Temuan | Packet |
|---|---|---|
| Installer gagal clean-install (argumen ter-join satu string; dependensi duplikat tanpa `xhtml2pdf`) | REV-1111-04 (P1; reviewer ops P0) | S4 / pekerjaan installer |
| Upgrade/repair bisa exit sukses palsu; repair dapat menurunkan HTTPS ke :80; readiness hanya SELECT 1 | REV-1111-05 (P1) | S4 |
| Worker tanpa drain/fencing; upgrade overwrite+migrate saat proses aktif | REV-1111-06 (P1) | PA-002/PA-003 (S2) |
| Restore end-to-end + pemisahan secret migrator belum terbukti | REV-1111-07 (P1) | S4 |
| Topology deployment belum konsisten dengan ARCHITECTURE (native vs Compose) — **DEC-01 belum resolved** | REV-1111-08 (P1) | keputusan pemilik |
| Scheduler invoice BELUM diimplementasikan (command ada; timer/unit tidak ditemukan) | REV-1111-09 (P1) | S4 |
| Security/idempotency/seleksi kontrak terbuka (permission operasi, principal-scoped idempotency, selected-set, scanner fail-closed) | REV-1111-11 (P1) | PA-006/S1, S2, S3 |
| Kapasitas target 1.000×1.000 belum dibuktikan benchmark | REV-1111-12 (P2) | S6/G4-G5 |

Environment blockers (prasyarat eksternal, TETAP ADA):

| Environment blocker | Butuh |
|---|---|
| **Gate A/G** | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS` (SETELAH code blocker installer ditutup) |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 + bukti lab onboarding Phase-1; aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-11-pa001-payment-concurrency` — **MERGED ke main** (PR #9; branch
  remote dibiarkan sebagai arsip riwayat).
- Terbuka milik pihak lain (JANGAN ditimpa): `docs/planning-audit-20261110` (PR #8),
  `session/2026-11-07-sstp-phase2` (PR #7).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2` (unmerged),
  `integration/beta-0.1`, `session/2026-11-06/07-*`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **PA-006 (P1)** — menuntaskan uang/idempotency: principal-scoped idempotency, HTTP
   replay/race konkuren (rekomendasi review controller §8: "Packet selanjutnya sesudah
   PR9 diterima: PA-006"). Rujukan: `common/idempotency.py` (scope tanpa principal),
   jobs/views permission operasi (REV-1111-11 sebagian).
2. **PA-002 + authority PA-003 (P1)** — job lifecycle fencing/drain (termasuk risiko
   tersisa PA-001: penahan kunci invoice selama render kwitansi PDF dalam transaksi;
   runworker tanpa drain; write tanpa ownership check).
3. **DEC-01** — keputusan topology (wajib sebelum menetapkan rehearsal S4; executor
   menyiapkan proposal biaya/risiko/isolasi, BUKAN mengubah ARCHITECTURE/CONTRACT).
4. **DEC-02** — PR #8 docs/manifest (branch itu pemilik file — jaga ownership disjoint).
5. **PR #7 disposition** (SSTP Phase-2; docs CI fail = manifest mismatch, bukan bukti runtime).
6. Installer/upgrade/restore/scheduler code blockers (REV-1111-04/05/07/09) — S4 setelah
   DEC-01; ops host Gate A/G setelah code blocker ditutup.

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ 8ce94d4 (lihat §1)
git log --oneline -5
# Sandbox uji (PostgreSQL 17 user-space + Python 3.13; tanpa systemd di sandbox z.ai):
MT_SANDBOX_BASE=/home/z/pgbase bash docs/tools/setup_env.sh   # PG 17.11 + FreeRADIUS 3.2.7 deb-extract
cd backend && MT_PG_BIN=/home/z/pgbase/pgbin/pg17 bash scripts/dev_bootstrap.sh
# (venv: uv venv .venv --python /usr/bin/python3.13 --seed bila python3.13-venv absen)
MT_ENV=test .venv/bin/python -m pytest tests -q   # 382 tes + 1 skip radius (PostgreSQL nyata;
#   tambah LD_LIBRARY_PATH/MT_FREERADIUS_BIN=…/frdeb/extracted/… untuk 383 penuh)
env -u DATABASE_URL MT_ENV=test .venv/bin/python manage.py check   # 0 issue (hindari DATABASE_URL ambien sqlite)
python3 docs/tools/check_docs.py
```

## 7. Risiko & keterbatasan yang diketahui

- Penahan kunci baris invoice selama transaksi verifikasi (termasuk render PDF kwitansi)
  — pemindahan I/O keluar transaksi = lingkup **PA-002**.
- Tes konkurensi PA-001 di level service (bukan HTTP multi-request; DRF test client
  tidak thread-safe); idempotency/principal scope HTTP = **PA-006**.
- Mutasi router tetap jalur simulator (capability.source=simulator) — tidak ada klaim
  perangkat nyata (G1). Gap G1 dan daftar lengkap risiko lama: handoff 2026-11-07 §7.
- Kapasitas 1.000 tenant × 1.000 online tetap klaim desain, bukan benchmark.
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan.
- Verdict re-review controller pasca-merge belum diterbitkan — register REV-1111 tetap
  rujukan temuan; temuan PA-001 spesifik ditutup via acceptance Lampiran A + bukti
  (lihat `report/orchestrator/20261111T145417Z-pr9-merge-integration.md` §2–§3);
  temuan REV-1111-04–09/11/12 TETAP TERBUKA.
- **PAT GitHub hanya dipakai untuk fetch/push/merge dari sandbox (tidak pernah
  di-commit; scan diff bersih). Rotasi PAT tetap disarankan** karena melewati kanal chat.
