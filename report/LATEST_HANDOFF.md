# LATEST_HANDOFF — Kanonis (sesi 2026-11-11 lanjutan: koreksi PR #9 sesuai review REV-1111)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` @ **`16085f825fef25ee4112d74b729c57e623b0bb05`** (clean; diverifikasi fetch ulang sesi ini; CI main pada SHA itu success — diverifikasi controller via API check-runs) |
| **PR sesi ini** | **#9 OPEN** (`session/2026-11-11-pa001-payment-concurrency` → main). Kandidat PERTAMA (`3b20b56`) mendapat verdict review **REQUEST CHANGES** (register REV-1111, lihat `report/controller/20261111T074225Z-repo-handoff-review.md`); kandidat KEDUA (koreksi REV-1111-01/02/03/10 — lihat §2) di-push sesi ini dan **menunggu review ulang controller pada SHA baru, BUKAN siap merge otomatis** |
| PR lain terbuka | **#7** SSTP Phase-2 (head `d7fa35e`; CI backend/frontend success, docs FAIL **manifest mismatch** — ditelusuri controller: bukan bukti SSTP gagal runtime; belum diinvestigasi packet terpisah) · **#8** docs planning-audit DRAFT (head `6bb57c9`; CI docs FAIL manifest mismatch = pekerjaan DEC-02, branch itu pemilik file manifest — jaga ownership disjoint) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan beta BUKAN hanya host: terdapat **code blockers** (§3) dan **environment blockers**. Klaim lama "penahan tunggal Gate A/G / BUKAN pekerjaan kode" DIKOREKSI sesuai REV-1111-10 |
| CONTRACT.md | Versi `1fff190` (tidak diubah sesi ini) |
| Prioritas aktif | Mandat master prompt user 2026-11-10 (sandbox terlebih dahulu). Sesi ini = packet koreksi PR #9 sesuai instruksi controller §8; urutan berikutnya menunggu verdict review ulang |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata, dipisah eksplisit)

**Packet koreksi PR #9 (REV-1111-01/02/03/10)** — base kandidat pertama `3b20b56`
(SHA main/PR7/PR8 diverifikasi TIDAK berubah sejak snapshot review controller):

1. **Implemented** (kode):
   - `backend/domains/billing/services.py`: `_canonical_invoice_id` (uuid.UUID → identitas
     kanonik; salah bentuk → 422 `ApiError.validation` pola `billing/views._parse_uuid`);
     `_parse_allocations` merge + `sorted()` pada identitas kanonik (anti-deadlock
     REV-1111-01), hasil dikembalikan dalam **urutan permintaan teragregasi semula**
     (customer/bahasa kwitansi I18N-01 tetap invoice pertama-diminta — REV-1111-02).
   - `backend/tests/integration/test_billing_payment_concurrency.py`: +6 tes (alias 4 ejaan
     tergabung satu alokasi; malformed 422 + UUID-valid-tak-dikenal tetap 404; kwitansi
     multi-customer urutan permintaan; rollback pasca-tulis via bloker dedup outbox dengan
     file yatim dihitung terpisah; kontensi terkontrol: kunci ditahan + pg_stat_activity +
     probe NOWAIT membuktikan urutan kunci canonical; konkurensi campuran ejaan tanpa
     deadlock). Tes klaim-berlebihan lama direname + deskripsi disempitkan
     (validasi-di-muka, bukan rollback pasca-tulis).
   - Persistensi laporan review (CONTRACT §10): `report/controller/20261111T074225Z-…`,
     `report/reviewer/20261111T073744Z-…` (finance), `report/reviewer/20261111T073747Z-…`
     (operasi) — verbatim, tanpa secret/PII.
   - Koreksi handoff ini + checkpoint `docs/progress.md` (REV-1111-10).
2. **Verified_local/integration** (PostgreSQL 17.5 nyata, dua koneksi per thread,
   sandbox disposable — bukti perintah/exit di
   `report/orchestrator/20261111T092854Z-pa001-canonical-identity-corrections.md` §4):
   - File konkurensi: **10 passed** (4 PA-001 lama + 6 baru), stabil 4 run beruntun.
   - **Sensitivitas**: 5/6 tes baru GAGAL pada kode kandidat pertama — termasuk
     **deadlock nyata terdeteksi PostgreSQL** pada tes konkurensi alias (persis prediksi
     REV-1111-01); tes rollback pasca-tulis lolos di kedua kode (bukti kemampuan, bukan
     penolak defect lama — dicatat jujur).
   - Suite penuh: **382 passed, 1 skipped** (376 baseline + 6 baru; skip = binari
     freeradius tidak tersedia, pre-existing), `manage.py check` 0 issue, docs check PASS.
   - Invarian tetap: dua payment terhadap invoice sama → tepat satu lolos/409 bersih;
     paid == SUM(alokasi); kwitansi/audit/outbox atomik.
3. **Verified_lab / release_enabled**: TIDAK ADA perubahan — simulator saja, tidak ada
   perangkat nyata (G1), tidak ada rehearsal installer (S4), tidak ada deploy.
4. **NOT_RUN jujur**: daemon FreeRADIUS, frontend jobs (CI PR memverifikasi; diff tidak
   menyentuh `apps/web`), Playwright e2e, HTTP idempotency konkuren (PA-006), rehearsal
   installer (sandbox tanpa systemd/root), restore/DR.
5. Status CI GitHub Actions pada SHA push: diverifikasi via API **setelah** push; hasil
   aktual dicatat pada komentar PR #9 oleh sesi ini (handoff ditulis sebelum push —
   tidak ada klaim CI yang belum diverifikasi).

## 3. Bloker beta — CODE blockers (jujur; BUKAN hanya host/environment)

Tabel ini menggantikan klaim lama "penahan tunggal Gate A/G / BUKAN pekerjaan kode"
(REV-1111-10). Register lengkap + baris bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4.

| Code blocker (defect source, terbuka) | Temuan | Packet |
|---|---|---|
| Installer gagal clean-install (argumen ter-join satu string; dependensi duplikat tanpa `xhtml2pdf`) | REV-1111-04 (P1; reviewer ops P0) | S4 / pekerjaan installer |
| Upgrade/repair bisa exit sukses palsu; repair dapat menurunkan HTTPS ke :80; readiness hanya SELECT 1 | REV-1111-05 (P1) | S4 |
| Worker tanpa drain/fencing; upgrade overwrite+migrate saat proses aktif | REV-1111-06 (P1) | PA-002/PA-003 (S2) |
| Restore end-to-end + pemisahan secret migrator belum terbukti | REV-1111-07 (P1) | S4 |
| Topology deployment belum konsisten dengan ARCHITECTURE (native vs Compose) — **DEC-01 belum resolved** | REV-1111-08 (P1) | keputusan pemilik |
| Scheduler invoice BELUM diimplementasikan (command ada; timer/unit tidak ditemukan — klaim lama "timer 01:00 dipasang installer" DICABUT) | REV-1111-09 (P1) | S4 |
| Security/idempotency/seleksi kontrak terbuka (permission operasi, principal-scoped idempotency, selected-set, scanner fail-closed) | REV-1111-11 (P1) | PA-006/S1, S2, S3 |
| Kapasitas target 1.000×1.000 belum dibuktikan benchmark | REV-1111-12 (P2) | S6/G4-G5 |

Environment blockers (prasyarat eksternal, TETAP ADA):

| Environment blocker | Butuh |
|---|---|
| **Gate A/G** | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS` (setelah code blocker installer ditutup) |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 + bukti lab onboarding Phase-1; aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-11-pa001-payment-concurrency` — sesi ini (**PR #9 OPEN**; commit koreksi
  `fix(billing)` + `docs(handoff)`; SHA head remote diverifikasi via API setelah push).
- Terbuka milik pihak lain (JANGAN ditimpa): `docs/planning-audit-20261110` (PR #8),
  `session/2026-11-07-sstp-phase2` (PR #7).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2` (unmerged),
  `integration/beta-0.1`, `session/2026-11-06/07-*`.

## 5. Prioritas eksekusi berikutnya (urut — menunggu verdict review ulang PR #9)

1. **Review ulang PR #9 oleh controller** pada SHA kandidat kedua (acceptance Lampiran A:
   alias/urutan identitas/422/kwitansi kompatibel/rollback pasca-tulis/kontensi terkontrol)
   → ACCEPTED FOR NEXT SANDBOX STEP / REQUEST CHANGES.
2. **PA-006 (P1)** — menuntaskan uang/idempotency (principal-scoped; HTTP replay/race)
   sesuai rekomendasi review ("Packet selanjutnya sesudah PR9 diterima: PA-006").
3. **PA-002 + authority PA-003 (P1)** — job lifecycle fencing/drain (terkait risiko tersisa
   PA-001: penahan kunci selama render kwitansi PDF).
4. **DEC-01** — keputusan topology (wajib sebelum menetapkan rehearsal S4; executor
   menyiapkan proposal biaya/risiko/isolasi, BUKAN mengubah ARCHITECTURE/CONTRACT).
5. **DEC-02** — PR #8 docs/manifest (branch itu pemilik file — jaga ownership disjoint).
6. **PR #7 disposition** (SSTP Phase-2; docs CI fail = manifest mismatch, ditelusuri
   controller; bukan bukti runtime).
7. Ops host Gate A/G saat host tersedia — SETELAH code blocker installer/upgrade (§3)
   ditutup dan DEC-01 resolved.

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ 16085f8 (lihat §1)
git log --oneline -5
# Kandidat PA-001 (koreksi REV-1111) untuk review (jangan merge tanpa verdict controller):
git fetch origin session/2026-11-11-pa001-payment-concurrency
git diff main...origin/session/2026-11-11-pa001-payment-concurrency
# Sandbox uji (PostgreSQL 17 user-space + Python 3.13; tanpa systemd di sandbox z.ai):
bash docs/tools/setup_env.sh                # atau initdb/pg_ctl manual port 55432
cd backend && bash scripts/dev_bootstrap.sh
MT_ENV=test .venv/bin/python -m pytest tests -q   # 382 tes (PostgreSQL nyata)
python3 docs/tools/check_docs.py
```

Lingkungan sandbox z.ai saat ini (jika sesi lanjut memakai sandbox sama): PG 17.5
user-space `/tmp/pgbin/pg17` aktif di port 55432 (cluster `backend/pgdata`; bila
proses mati karena daur ulang sandbox: `LD_LIBRARY_PATH=/tmp/pgbin/pg17/lib
/tmp/pgbin/pg17/bin/pg_ctl -D pgdata -o "-p 55432 -k $PWD/pgrun -h 127.0.0.1
-c listen_addresses=127.0.0.1" -l pgdata/server.log start`); venv `backend/.venv`
Python 3.13.5 dengan dependensi pinned terpasang; binari freeradius TIDAK tersedia
(1 tes radius-config SKIP wajar; `scripts/test_radius.sh` NOT_RUN). Bila sandbox
direcycle penuh, binari PG diambil ulang dari Maven Central (Zonky
embedded-postgres-binaries-linux-amd64 17.5.0) — langkah replikasi ada di laporan
orchestrator sesi ini §3.

## 7. Risiko & keterbatasan yang diketahui

- **Daur ulang sandbox platform menghapus `/home/z/my-project`** — pekerjaan koreksi ini
  akan SUDAH di-push (PR #9); artefak sandbox dapat dibangun ulang via §6.
- Penahan kunci baris invoice selama transaksi verifikasi (termasuk render PDF kwitansi)
  — kelas penahan sama dengan kunci tenant yang sudah ada; pemindahan I/O keluar
  transaksi = lingkup **PA-002** (bukan diperluas di packet koreksi ini).
- Tes konkurensi PA-001 di level service (bukan HTTP multi-request; DRF test client tidak
  thread-safe); idempotency/principal scope HTTP = **PA-006**.
- Mutasi router tetap jalur simulator (capability.source=simulator) — tidak ada klaim
  perangkat nyata (G1). Gap G1 dan daftar lengkap risiko lama: handoff 2026-11-07 §7
  (masih berlaku).
- Kapasitas 1.000 tenant × 1.000 online tetap klaim desain, bukan benchmark.
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan.
- **PAT GitHub hanya dipakai untuk push dari sandbox (tidak pernah di-commit; scan diff
  bersih). Rotasi PAT tetap disarankan** karena melewati kanal chat.
