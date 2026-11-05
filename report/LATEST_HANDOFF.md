# LATEST_HANDOFF — Kanonis (sesi 2026-11-06)

Diperbarui atomik SETELAH integrasi terverifikasi. Dokumen ini adalah titik
masuk WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya, jangan
duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` |
| **Commit remote terverifikasi** | **`f5753884ff99f397c27b4f6b4993b9b40a385bb6`** (merge PR #2; diverifikasi via GitHub API `branches/main` 2026-11-05T19:2xZ; lokal `git rev-parse origin/main` = `f575388`) |
| **CI pada commit merge** | **HIJAU**: backend ✓ frontend ✓ docs ✓ (GitHub Actions, jobs semua `completed success`) |
| PR | **#2** `session/2026-11-06-wg-e2e` → main (merged, commit sesi `b07504a`) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY (§15)** — penahan tunggal tetap Gate A/G (instalasi host Debian 13 nyata root+domain), BUKAN pekerjaan kode |
| CONTRACT.md | Diperbarui pemilik DURASI sesi ini (`1fff190`) — kewajiban BARU: lab GNS3 API-driven (§7), target kapasitas 1.000 tenant (§7), proses perubahan dokumen terkontrol (§4). Laporan sesi ini SUDAH patuh format §10 |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata)

1. **Baseline diaudit ulang dari nol** (bukan percaya klaim): 222/222 backend,
   RADIUS nyata 15/15, FE 42/42 + tsc/eslint/build live, docs PASS, shellcheck 0
   error — pada environment sandbox BARU (PostgreSQL 17.11 deb-extract + patch
   jalur share non-root; FreeRADIUS 3.2.7 deb + rlm_sql_postgresql).
2. **WG-1 (P1)**: adopsi keypair installer X25519 NYATA oleh `WireGuardHost`
   (`MT_WG_SERVER_PUBKEY` tervalidasi murni `microtix/wg.py`); `adopt_wg_host`
   (rotasi dengan peer aktif DITOLAK; `--check` read-only); `render_wg_config`
   (peers lintas-tenant via scope eksplisit; 0600; tanpa PrivateKey default);
   `probe_wg` (`wg show`; BLOCKED exit 2 jujur tanpa binary; pembaruan
   `last_handshake_at` monotonik). Installer memanggil adopt+render; doctor
   cek adopsi; upgrade idempoten. **252/252** (222 + 30 baru).
3. **E2E-1 (P1)**: `make e2e` NYATA (menggantikan NOT_RUN) — Playwright 1.57 +
   Chromium + backend PG17/RLS nyata. **7/7 PASS**: login happy/error, guard,
   **isolasi tenant (404 envelope + nol kebocoran)**, **register→verifikasi
   email→login tenant baru**, i18n, mobile 360px. **Menemukan + memperbaiki 2
   bug nyata**: navigasi login non-MFA (FE; era mock hanya uji TOTP) + CSRF
   dev-topology (produksi tetap kosong — tidak dilemahkan).
4. **Gap registri pra-ada**: `verify_api_ssl` masuk `JOB_KINDS`/`JobKind` +
   migrasi state `jobs/0003` (temuan reviewer F1/P1 — diperbaiki sebelum merge;
   `makemigrations --check` CLEAN).
5. **Review independen** (sub-agent, menjalankan ulang verifikasi sendiri):
   APPROVE-WITH-NOTES → F1–F6/F8 diterapkan → laporan `report/reviewer/20261105T191840Z-independent-review.md`.
6. **Laporan kontrak**: `report/orchestrator/20261105T191826Z-wg-host-adoption.md`,
   `report/orchestrator/20261105T191830Z-e2e-harness.md` (+ handoff ini).

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (satu-satunya penahan tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; lalu `manage.py adopt_wg_host` + `systemctl enable --now wg-quick@wg0` + `manage.py probe_wg` + render/apply wg0.conf |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7 BARU) | Infrastruktur GNS3 (server/VM) + image CHR berlisensi; harness reproducible + profil topologi + bukti machine-readable |
| Probe wg interface host nyata | Termasuk Gate A/G (sandbox tanpa root) |

## 4. Cabang tidak tergabung

Tidak ada. `session/2026-11-06-wg-e2e` sudah merged (PR #2) — cabang arsip
`parallel/beta-be2` + `integration/beta-0.1` tetap dipertahankan (riwayat).

## 5. Prioritas eksekusi berikutnya (urut)

1. **M6/M7 billing/ledger R2** (P2 handoff; FINANCE.md) — pekerjaan kode
   independen TERBESAR berikutnya yang tidak butuh lab: ledger double-entry
   DB-enforced (TK-701), invoice prabayar/pascabayar (TK-601+), pengakuan
   bulanan + residual, alokasi/overpayment. Vertical slice per task, ikuti
   FINANCE.md §16 (posting minimal 2 baris, debit=kredit deferred, dsb.).
2. **Lab GNS3 harness** (CONTRACT §7 baru): mulai dari harness API-driven
   reproducible + profil topologi dasar — catat blocker image CHR berlisensi
   dengan tepat; jangan overengineer (CONTRACT §3).
3. **Ops host Gate A/G** saat host tersedia (P0 — penahan tag).
4. Follow-up minor: CI job e2e opsional (caching browser + stabilitas);
   doctor hint mismatch vs refused (F7); Makefile `playwright install || true`
   (F10); perluas spec e2e (enrollment→job polling, CSV, reauth sensitif);
   status WG host di UI (opsional, hindari tambah API surface tanpa kebutuhan).

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ f575388 (terverifikasi)
git log --oneline -5
cd backend && bash scripts/dev_bootstrap.sh  # idempoten (butuh MT_PG_BIN bila sandbox baru)
MT_ENV=test .venv/bin/python -m pytest tests -q          # 252 tes (PostgreSQL nyata)
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && cd ../.. && make e2e              # 7/7 browser+backend nyata
python3 docs/tools/check_docs.py && bash -n instalasi.sh
```

Lingkungan sandbox baru: jalankan `bash /home/z/my-project/scripts/setup_env.sh`
(PostgreSQL 17.11 deb + patch share-path non-root + FreeRADIUS + libs), venv via
`uv venv .venv --python /usr/bin/python3.13 --seed`, pnpm wrapper
`corepack pnpm@12.16.1`, Playwright 1.57 (Chromium 1200 sudah di cache
`~/.cache/ms-playwright`), browser headless: `agent-browser`.

Baca: CONTRACT.md (VERSI BARU `1fff190` — khususnya §7 GNS3 + kapasitas),
docs/AGENT_HANDOFF.md §5/§7, docs/progress.md checkpoint SESI-2026-11-06,
docs/BETA_TEST_EVIDENCE.md §3, report/orchestrator/ + report/reviewer/ sesi ini.

## 7. Risiko & keterbatasan yang diketahui

- Semua interaksi router tetap jalur simulator (capability: source=simulator,
  verified_lab=false) — TIDAK ada klaim perangkat nyata (G1).
- WireGuard: adopsi keypair + render + probe DIIMPLEMENTASI; interface host
  belum pernah hidup di mana pun (Gate A/G); fallback dev tetap placeholder
  deterministik berlabel `generated_dev`.
- E2E menguji alur auth/isolasi/onboarding/i18n/mobile; alur router nyata
  menunggu lab; CI GitHub belum menjalankan e2e (hanya lokal/ops).
- Vendor dipegang via `.git/config` lokal (PAT tidak pernah ditulis ke repo;
  scan commit bersih).
