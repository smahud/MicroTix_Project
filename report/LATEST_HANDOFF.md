# LATEST_HANDOFF — Kanonis (sesi 2026-11-06 lanjutan: bootstrap in-repo + fix harness T19)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` |
| **Commit remote terverifikasi** | **`1d26b7e39ad8c4b0766cac0899eca708b4edfe27`** (merge PR #3; diverifikasi via `git ls-remote` 2026-11-06T06:5xZ — lokal `git rev-parse origin/main` = `1d26b7e`; CI pada commit sesi `8f6b173` **HIJAU**: backend=success, frontend=success, docs=success — diverifikasi via API check-runs) |
| **Branch sesi (SUDAH MERGED)** | `session/2026-11-06-bootstrap-inrepo` → main via **PR #3** (merged; commits sesi: `1e326dc` tools → `98ea90d` fix harness T19 → `8f6b173` docs) |
| PR | #1, #2, **#3** SUDAH merged (tidak ada PR terbuka) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan tunggal tetap Gate A/G (instalasi host Debian 13 nyata root+domain), BUKAN pekerjaan kode |
| CONTRACT.md | Versi `1fff190` (lab GNS3 API-driven §7; kapasitas 1.000 tenant; proses perubahan dokumen terkontrol §4) |

## 2. Yang diselesaikan + diverifikasi sesi lanjutan ini (bukti nyata)

1. **Insiden daur ulang sandbox** (jujur): `/home/z/my-project` direset
   platform di tengah sesi — commit lokal bagian-1 (`64ac004`/`18cf506`)
   HILANG sebelum sempat ter-push (PAT belum tersedia saat itu). Pelajaran:
   push sesegera mungkin setelah verifikasi; jangan menumpuk commit lokal.
   Bagian-2 sesi ini merekonstruksi semuanya dan diverifikasi ulang penuh.
2. **`docs/tools/setup_env.sh` in-repo** (`1e326dc`): bootstrap sandbox
   PG17+FreeRADIUS AGENT_HANDOFF §8 — menutup gap "script hanya hidup di
   sandbox". `MT_SANDBOX_BASE` overridable + diekspor; **rebuild
   byte-identik** terbukti (sha256 postgres+initdb); jalur fresh + no-op
   idempoten exit 0; shellcheck 0 findings; manifest `--refresh` 21→22,
   docs PASS.
3. **Fix harness T19** (`98ea90d`): cabang FAIL uji isolasi T19 lama
   mengklaim "KEBOCORAN TENANT" juga saat radclient **tanpa balasan**
   (timeout) — klaim kebocoran tanpa bukti Access-Accept. Investigasi:
   1x FAIL pada run pertama sesi ini (RC_OUT hilang); reproduksi 4/4 PASS
   (termasuk urutan persis); konflasi terbukti dari kode; akar run pertama
   tidak terbukti (dugaan: no-reply transient). Fix: tiga luaran dibedakan
   (Reject=PASS / Accept=FAIL kebocoran+bukti / no-reply=FAIL "isolasi
   TIDAK terverifikasi, bukan bukti kebocoran"). Pasca-fix 2/2 PASS 15/15.
4. **Verifikasi ulang penuh pasca-rekonstruksi**: backend **252/252** (2x),
   RADIUS nyata **15/15** (total 7 run sesi ini: 1 FAIL-T19 terinvestigasi
   + 6 PASS), docs PASS (22 file), `instalasi.sh` bash -n OK.
5. **PUSH + PR + MERGE via PAT** (bukti, bukan klaim): push branch
   (`8f6b173` diverifikasi `git ls-remote`); PR #3 dibuat via API; CI pada
   `8f6b173` HIJAU (backend/frontend/docs semua success — poll API);
   merge PR #3 → **main `1d26b7e`** diverifikasi `git ls-remote` = SHA
   merge API. Commit handoff-lock ini menutup sesi.
6. **Laporan kontrak**:
   `report/orchestrator/20261106T063225Z-setup-env-inrepo-push.md`
   (kronologi insiden + investigasi T19 lengkap) + handoff ini.

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (penahan tunggal tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; lalu `adopt_wg_host` + `wg-quick@wg0` + `probe_wg` + render/apply wg0.conf |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-06-bootstrap-inrepo` — **SUDAH MERGED** (PR #3 → main
  `1d26b7e`; SHA remote terverifikasi). Tetap dipertahankan di remote
  sebagai arsip riwayat sesi (pola sesi sebelumnya).
- Arsip riwayat (remote): `parallel/beta-be2`, `integration/beta-0.1`,
  `session/2026-11-06-wg-e2e`, `session/2026-11-06-bootstrap-inrepo`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **M6/M7 billing/ledger R2** (P2; FINANCE.md) — pekerjaan kode independen
   TERBESAR berikutnya tanpa lab: ledger double-entry DB-enforced (TK-701),
   invoice prabayar/pascabayar (TK-601+), pengakuan bulanan + residual,
   alokasi/overpayment. Vertical slice per task, ikuti FINANCE.md §16.
2. **Lab GNS3 harness** (CONTRACT §7): harness API-driven reproducible +
   profil topologi dasar; catat blocker image CHR berlisensi dengan tepat.
3. **Ops host Gate A/G** saat host tersedia (P0 — penahan tag).
4. Follow-up minor: CI job e2e opsional; doctor hint mismatch vs refused
   (F7); Makefile `playwright install || true` (F10); perluas spec e2e.

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ 1d26b7e (terverifikasi)
git log --oneline -5
cd backend && bash scripts/dev_bootstrap.sh  # idempoten (butuh MT_PG_BIN bila sandbox baru)
MT_ENV=test .venv/bin/python -m pytest tests -q          # 252 tes (PostgreSQL nyata)
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && cd ../.. && make e2e              # 7/7 browser+backend nyata
python3 docs/tools/check_docs.py && bash -n instalasi.sh
```

Lingkungan sandbox baru: `bash docs/tools/setup_env.sh` (IN-REPO sejak
`1e326dc`; basis default `/home/z/my-project`, override `MT_SANDBOX_BASE`),
venv via `uv venv .venv --python /usr/bin/python3.13 --seed`
(`python3.13 -m venv` gagal tanpa paket venv), pnpm wrapper
`corepack pnpm@12.16.1`, Playwright 1.57 (Chromium 1200), browser headless:
`agent-browser`.

Baca: CONTRACT.md (versi `1fff190`), docs/AGENT_HANDOFF.md §5/§7/§8,
docs/progress.md checkpoint teratas, report/orchestrator/ terbaru.

## 7. Risiko & keterbatasan yang diketahui

- **Daur ulang sandbox platform menghapus `/home/z/my-project`** (terjadi
  2026-11-06): commit lokal yang belum ter-push HILANG. Push sesegera
  mungkin; lab dapat dibangun ulang via `docs/tools/setup_env.sh`.
- Semua interaksi router tetap jalur simulator (source=simulator,
  verified_lab=false) — tidak ada klaim perangkat nyata (G1). WireGuard:
  adopsi keypair + render + probe terimplementasi; interface host belum
  pernah hidup (Gate A/G).
- CI pada `f284ce8` sendiri tidak bisa dikonfirmasi ulang dari sandbox
  (`api.github.com` 403 anonim; dengan PAT sesi ini dapat diakses); tree
  kode identik dengan `f575388` yang CI-hijau.
- PAT disimpan HANYA di `.git/config` lokal (tidak pernah di-commit);
  scan commit bersih. PAT kedaluwarsa = push berikutnya BLOCKED lagi
  (minta PAT baru dari pengguna).
- Harness T19: run no-reply tetap FAIL (gate ketat) — ulangi run; kini
  pesannya jujur (bukan klaim kebocoran).
