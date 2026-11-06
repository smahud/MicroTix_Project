# LATEST_HANDOFF — Kanonis (sesi 2026-11-07: Phase-1 onboarding router aman)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` |
| **Commit remote terverifikasi** | **`8bb20c33d3bab15a469ade01bb4c665f56a8738a`** (merge PR #6; diverifikasi `git ls-remote` + API 2026-11-07; CI pada head PR `4ed2145` **HIJAU**: backend/frontend/docs semua success — diverifikasi via check-runs) |
| **PR sesi ini** | **#6 SUDAH MERGED** (`session/2026-11-07-wg-onboarding`: Phase-1 onboarding router aman WireGuard — lihat §2) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan tunggal tetap Gate A/G (instalasi host Debian 13 nyata root+domain), BUKAN pekerjaan kode |
| CONTRACT.md | Versi `1fff190` (tidak diubah; amendment teknis dicatat PROPOSED di report/orchestrator/20261106T195642Z-*.md §3) |
| Prioritas aktif | **Master directive user "Secure Router Connectivity"** (P0) — Phase-1 SELESAI & TERINTEGRASI; Phase-2 SSTP menunggu keputusan/lanjutan direktif; Gate A/G tetap penahan beta |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata)

1. **Perbaikan bug P0 skrip bootstrap** (`services.bootstrap_script`):
   endpoint peer = hostname gateway PUBLIK terkonfigurasi — rantai
   `vpn.gateway_hostname` (defaults.json **rev 2.3**, param ke-115) →
   `MT_PUBLIC_HOST` → `MT_DOMAIN`; produksi tanpa nilai = **409 jujur**
   (`gateway_hostname_unconfigured`); dev/test = `microtix.invalid`
   (TLD .invalid — tidak dapat diresolve). Menggantikan bug lama:
   endpoint IP tunnel internal `100.127.0.1` + fallback palsu
   `microtix.example`. Artefak SCEP + baris `:local privkey` (tanpa kurung,
   membaca private key) DIHAPUS; port dari state host/enrollment; JSON body
   callback dengan escape RouterOS benar; token tetap hash-only+SecretBox+
   cleared-on-consume+di-body (§2.2). Komentar gap G1 pada callback fetch.
2. **Kejujuran verifikasi (false-positive dimatikan)**: `capability.source`
   = adapter AKTIF (`MT_ROUTEROS_ADAPTER`), simulator ⇒ `api_ssl/wireguard
   = False` + catatan (sebelumnya `True` tanpa bukti apa pun). Jalur
   `api_ssl`: **probe TCP+TLS NYATA** (`probe_connectivity`) sebelum Router
   dibuat; pin = **fingerprint TERAMATI**; gagal → JobError retryable
   (bounded `max_attempts=5`, re-entry VERIFYING — bug "retry terkunci"
   diperbaiki). `verification` ternormalisasi di progress + detail router.
3. **Protokol + versi RouterOS**: `RouterEnrollment.protocol`+
   `routeros_version` (migrasi **0010**; default `wireguard`/`"7"` — API lama
   tetap sah, additive-only). WireGuard wajib **v7.1+** (v6/v7.0 ditolak 422
   beralasan); SSTP/L2TP/OpenVPN ditolak jujur `unsupported` (tampil
   "direncanakan" di UI). UI wizard: pemilih versi+protokol, baris endpoint
   gateway (§2.2), banner "Simulasi" di langkah Siap, chip sumber verifikasi
   di detail router; mock adapter paritas penuh (bug regex vV diperbaiki).
4. **Isolasi diperkuat**: constraint `uq_wgpeer_pubkey_active` (kunci publik
   WG unik global utk peer AKTIF; 409 `wg_public_key_registered` lintas
   tenant tanpa bocoran info) + **perbaikan bug alokasi IP tunnel buta-RLS**
   (dua tenant bisa memilih /32 sama → IntegrityError; kini iterasi scope
   per tenant, konvensi `_any_active_peer`).
5. **Installer**: `MT_DOMAIN` diteruskan ke env aplikasi (pembuatan +
   append-if-missing idempoten) — sumber hostname gateway di produksi.
6. **E2E harness**: `e2e/run.sh` kini menjalankan **runworker** proses
   terpisah; spec baru `routers.spec.ts` (2): alur PENUH backend+worker
   nyata (wizard→skrip→bridge CSRF→job verify→"Siap" berlabel Simulasi→
   detail router) + v6 memblokir kelanjutan.
7. **Riset kapabilitas multi-protokol bersumber vendor** (WireGuard 7.1+;
   SSTP klien tanpa EAP → server wajib MSCHAPv2; OpenVPN klien v6 TCP-only
   tanpa NCP; L2TP auto-IKEv1; lisensi CHR):
   `report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md`.
8. **Review independen**: REQUEST_CHANGES (2 P1) → P1-1 retry re-entry
   DIPERBAIKI (+tes); P1-2 `check-certificate` DIDOKUMENTASIKAN gap G1 +
   PROPOSED (mengaktifkan tanpa bukti lab berisiko mematikan onboarding);
   P2 layak-perbaiki (pin teramati, regex mock, oktet IPv4, gate 7.0)
   diperbaiki. Disposisi: `report/reviewer/20261106T194638Z-*.md`.
9. **Verifikasi penuh** (PG 17.11 nyata): backend **373/373** (+14),
   makemigrations --check bersih, FreeRADIUS nyata **15/15**, FE
   tsc/eslint 0 + vitest **66/66** + i18n paritas **1062**, build live OK +
   mock DITOLAK, `make e2e` **12/12** (Chromium+backend+worker nyata),
   bash -n instalasi.sh OK, docs check di-refresh.

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (penahan tunggal tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; termasuk timer host `issue_due_invoices` (01:00) |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 + bukti lab onboarding Phase-1: sintaks skrip v7, `check-certificate` fetch (+SNTP/CA), **skrip v2** (akun API-SSL platform pada router — jalur login penuh), handshake WG, dua tenant LAN sama → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-07-wg-onboarding` — sesi ini (PR #6 **SUDAH MERGED**; SHA remote
  terverifikasi §1).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2` (masih unmerged —
  jangan ditimpa), `integration/beta-0.1`, `session/2026-11-06-*`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **Ops host Gate A/G saat host tersedia** (penahan beta tunggal; termasuk
   timer `issue_due_invoices`).
2. **Lab G1 (CHR)**: item bukti onboarding Phase-1 (lihat §3) → aktifkan
   `MT_ROUTEROS_ADAPTER=api_ssl` + skrip v2.
3. **Phase-2 SSTP** (master directive; matriks kapabilitas sudah tersedia):
   server SSTP Debian (MSCHAPv2, aes256-sha/gcm-sha384, TLS 1.2), listener
   shared-port, model protokol → skrip v6/v7, verifikasi TLS+identitas.
   PROPOSED menunggu lanjutan direktif user.
4. Alternatif paralel aman (handoff lama tetap sah): TK-701 ledger M7 ATAU
   TK-602/607/608/609.
5. Follow-up minor: endpoint ambil bukti transfer (keputusan dokumen §8);
   enrollment cancel endpoint (state `cancelled` masih dead); GUC
   `enroll_bridge` try/finally (pre-existing, direviu reviewer).

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ merge PR Phase-1 (lihat §1)
git log --oneline -5
bash docs/tools/setup_env.sh                 # sandbox baru (PG17+FreeRADIUS deb-extract)
cd backend && MT_PG_BIN=/home/z/my-project/pgbin/pg17 bash scripts/dev_bootstrap.sh
MT_ENV=test .venv/bin/python -m pytest tests -q          # 373 tes (PostgreSQL nyata)
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && cd ../.. && make e2e              # 12/12 browser+backend+worker nyata
python3 docs/tools/check_docs.py && bash -n instalasi.sh
```

Lingkungan sandbox baru: venv via `uv venv .venv --python /usr/bin/python3.13
--seed` (python3.13-venv tidak terpasang); pnpm wrapper `corepack pnpm@12.16.1`
(shim `~/.local/bin/pnpm`); Playwright Chromium ter-cache. CATATAN proses
background di sandbox: unduhan nohup bisa MANDek — jalankan setup_env.sh
FOREGROUND; .deb terpotong (lzma error) → hapus *.deb lalu unduh ulang
(idempoten).

Baca: CONTRACT.md (versi `1fff190`), docs/AGENT_HANDOFF.md §5, docs/progress.md
checkpoint teratas (SESI-2026-11-07), report/orchestrator/20261106T195642Z-*
(keputusan + PROPOSED), docs/BETA_RELEASE_STATUS.md (fitur aktif + batasan 7).

## 7. Risiko & keterbatasan yang diketahui

- **Daur ulang sandbox platform menghapus `/home/z/my-project`** — push
  sesegera mungkin; lab dibangun ulang via `docs/tools/setup_env.sh`.
- Mutasi router tetap jalur simulator (capability.source=simulator,
  verified_lab=false) — TIDAK ADA klaim perangkat nyata (G1). Kini dengan
  pelabelan jujur API+UI (`verification`) — simulator tidak pernah
  dipresentasikan sebagai konektivitas nyata.
- **Gap terdokumentasi G1** (lihat §3): `check-certificate` fetch (MITM token
  dibatasi sekali-pakai/TTL/atomik), skrip v2 akun API-SSL (login penuh),
  sintaks pada perangkat nyata, handshake WG.
- Alokasi IP tunnel = iterasi scope per tenant (O(tenant) per enrollment) —
  dicatat untuk fase kapasitas 1.000 tenant.
- e2e spec onboarding bergantung worker interval 1 s + urutan (workers:1).
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan.
- PAT hanya di `.secrets/` sandbox (tidak pernah di-commit; scan bersih);
  PAT kedaluwarsa = push berikutnya BLOCKED (minta PAT baru). **Rotasi PAT
  disarankan** karena pernah melewati kanal chat.
