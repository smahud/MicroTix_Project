# LATEST_HANDOFF — Kanonis (sesi 2026-11-07 lanjutan: Phase-2 SSTP)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` |
| **Commit remote main terverifikasi** | **`16085f8`** (docs handoff pasca-PR #6; diverifikasi `git fetch` awal sesi) |
| **Pekerjaan sesi ini** | branch **`session/2026-11-07-sstp-phase2`** — **PUSHED**; head sesi: **`8f10b909882dc2b0d0921ba1d9c5059a7e889c5e`** (feat Phase-2 SSTP + handoff ini; diverifikasi `git ls-remote` setelah push; PR dibuka untuk review — MERGE menunggu persetujuan reviewer, CONTRACT §11) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan tunggal tetap Gate A/G (instalasi host Debian 13 nyata root+domain), BUKAN pekerjaan kode |
| CONTRACT.md | Versi `1fff190` (tidak diubah) |
| defaults.json | **rev 2.4** (param ke-116: `vpn.sstp_listen_port`) — amendemen ROUTEROS.md §2.3 status APPROVED (basis: master directive user Phase-2; catatan keputusan: report/orchestrator/20261107T154532Z-*.md) |
| Prioritas aktif | Master directive "Secure Router Connectivity": ~~Phase-1~~ + ~~Phase-2 SSTP~~ **SELESAI & TERINTEGRASI** (belum VERIFIED_LAB); Phase-3 L2TP/IPsec+OpenVPN menyusul per fase |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata)

1. **SSTP aktif sebagai transport komplementer** untuk RouterOS **v6.49.x +
   v7** (v6 kini dapat onboarding read-only — titik penting: v6 tidak
   memuat WireGuard). v5- ditolak 422 jujur; WireGuard tetap v7.1+.
2. **Kredensial per-router** `SstpAccount` (migrasi **0011** + RLS + FK
   komposit): username **unik global lintas tenant** + password CSPRNG
   192-bit SecretBox; terbit saat draft; revoke (REMOVED) saat
   release/replace — tak dirender chap-secrets lagi.
3. **Skrip bootstrap SSTP v6/v7** (render backend dari state tervalidasi):
   MSCHAPv2 SAJA, `verify-server-certificate=yes` +
   `verify-server-address-from-certificate=yes` WAJIB nyala, CA platform
   diunduh dari endpoint **publik** `/api/v1/bridge/enroll-ca` lalu diimpor,
   rule API-SSL hanya dari alamat PPP server (100.127.0.2), TANPA
   add-default-route, /32 dialokasikan server-side (chap-secrets) — bukan
   diketik di router.
4. **Bridge sadar-protokol**: identitas SSTP = username kredensial
   (mismatch 409 `sstp_identity_mismatch`; replay identitas sama = hasil
   logis sama §2.7; bentuk identitas silang protokol = 422).
5. **Kejujuran verifikasi diperluas**: `verification.sstp` — simulator ⇒
   False (tidak pernah klaim sesi PPP nyata); jalur adapter api_ssl dengan
   probe nyata via tunnel ⇒ True; `wireguard` tetap False untuk enrollment
   SSTP.
6. **Server SSTP = accel-ppp 1.15.0** — build dari sumber dipin SHA-256
   (`backend/scripts/build_accel_ppp.sh`; tidak ada paket resmi Debian —
   keputusan + bukti di laporan sesi): TLS 1.2 saja +
   `AES256-SHA:AES256-GCM-SHA384`, **shared-port** tunggal
   `vpn.sstp_listen_port` (default 4443 — 443 milik Caddy; klien v6 tanpa
   SNI), `single-session=replace`, `mppe=deny`; render
   `manage.py render_sstp_config` (accel-ppp.conf + chap-secrets 0600;
   format baris diverifikasi dari chap-secrets.c 1.15.0).
7. **Installer fase-aware** `MT_ENABLE_SSTP=1` (pola MT_ENABLE_RADIUS): CA
   privat 10 th + sertifikat gateway SAN=MT_DOMAIN (auto-regen bila SAN
   berubah), env `MT_SSTP_CA_PATH`, unit `microtix-sstp.service`, health
   gate jujur + doctor + repair/upgrade idempoten; `bash -n` OK
   (ShellCheck belum — sandbox; CI tidak menjalankannya).
8. **Lab GNS3 profil minimal Phase-2** (`lab/`): topologi deklaratif 2 tahap
   (B: dua tenant **LAN sama 192.168.88.0/24** — bukti isolasi manajemen
   plane), provisioner API-driven stdlib (family API dari `/version`),
   checklist bukti G1 lengkap (termasuk uji NEGATIF verifikasi
   sertifikat). Status: **IMPLEMENTED — BELUM VERIFIED_LAB**.
9. **Verifikasi penuh** (PG 17.11 nyata): backend **391/391** (+18
   `test_sstp_flow.py`; `test_enrollment_flow.py` tes unsupported beralih
   ke openvpn — sstp kini didukung), makemigrations --check bersih,
   `manage.py check` OK, FreeRADIUS nyata **15/15**, FE tsc/eslint 0 +
   vitest **66→67** + i18n paritas **1063**, build live OK + mock DITOLAK,
   `make e2e` **12/12** (Chromium+backend+worker nyata), docs check PASS.

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (penahan tunggal tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; termasuk timer host `issue_due_invoices` |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 + checklist baru **`lab/evidence-checklist.md`** (G1-WG lama + **G1-SSTP** skrip v6.49/v7 + sesi PPP + uji negatif verifikasi sertifikat + **G1-ISO** dua tenant LAN sama + G1-FETCH + G1-REV) → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, skrip v2, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness `lab/` tersedia namun **belum dijalankan** terhadap controller nyata |

## 4. Cabang kerja

- `session/2026-11-07-sstp-phase2` — sesi ini (PUSHED; PR menunggu review).
- Arsip riwayat (remote, tidak diubah): `session/2026-11-07-wg-onboarding`
  (PR #6 merged), `parallel/beta-be2` (masih unmerged — jangan ditimpa),
  `integration/beta-0.1`, `session/2026-11-06-*`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **Review + merge PR sesi ini** (reviewer independen disarankan —
   perubahan keamanan: skrip SSTP, kredensial, installer).
2. **Ops host Gate A/G saat host tersedia** (penahan beta tunggal) —
   termasuk `build_accel_ppp.sh` + `MT_ENABLE_SSTP=1` + repair.
3. **Lab G1**: jalankan `lab/` tahap A→B + checklist; bila
   `verify-server-address-from-certificate` ternyata tidak ada di v6.49,
   revisi skrip v6 (keputusan tercatat G1-SSTP-2) → aktifkan
   `MT_ROUTEROS_ADAPTER=api_ssl` + skrip v2.
4. **Phase-3 direktif** (L2TP/IPsec + OpenVPN per matriks kapabilitas)
   ATAU alternatif paralel aman: TK-701 ledger M7 / TK-602/607/608/609.
5. Follow-up minor Phase-1 yang masih terbuka: endpoint ambil bukti transfer
   (keputusan dokumen §8); enrollment cancel endpoint; GUC `enroll_bridge`
   try/finally.

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ 16085f8 (atau merge PR SSTP bila sudah disetujui)
git log --oneline -5
git ls-remote origin session/2026-11-07-sstp-phase2   # head PR SSTP sesi ini
bash docs/tools/setup_env.sh                 # sandbox baru (PG17+FreeRADIUS deb-extract)
cd backend && MT_PG_BIN=/home/z/my-project/pgbin/pg17 bash scripts/dev_bootstrap.sh
MT_ENV=test .venv/bin/python -m pytest tests -q          # 391 tes (PostgreSQL nyata)
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && python3 scripts/check_i18n.py && cd ../..
make e2e                                                  # 12/12 browser+backend+worker nyata
python3 docs/tools/check_docs.py && bash -n instalasi.sh && bash -n backend/scripts/build_accel_ppp.sh
```

Lingkungan sandbox: venv via `uv venv .venv --python /usr/bin/python3.13
--seed`; pnpm shim `corepack pnpm@12.16.1` (`~/.local/bin/pnpm`); Playwright
Chromium terunduh sesi ini. Setup PG kini CEPAT (deb mirror lancar).

Baca: CONTRACT.md (versi `1fff190`), docs/AGENT_HANDOFF.md §5,
docs/progress.md checkpoint teratas (SESI-2026-11-07-lanjutan),
report/orchestrator/20261107T154532Z-phase2-sstp-management-channel.md
(keputusan + bukti penuh), docs/BETA_RELEASE_STATUS.md (fitur aktif),
lab/README.md + lab/evidence-checklist.md.

## 7. Risiko & keterbatasan yang diketahui

- **Semua bukti SSTP = VERIFIED_UNIT/INTEGRATION pada jalur simulator/api_ssl
  stub — BUKAN VERIFIED_LAB**: sintaks skrip v6.49 pada perangkat nyata,
  paritas field `verify-server-address-from-certificate` v6, sesi PPP nyata
  (accel-ppp), dan isolasi dua-LAN-sama menunggu lab G1. Simulator tidak
  pernah dipresentasikan sebagai konektivitas nyata.
- accel-ppp 1.15.0 belum dibangun/dijalankan di sesi ini (butuh host
  Debian root); pin SHA-256 + kunci konfigurasi diverifikasi dari tarball
  rilis resmi (laporan sesi §Keputusan-1).
- Fetch CA oleh skrip masih tanpa check-certificate (gap G1 bersama Phase-1;
  residual risk dibatasi CA-publik + password CSPRNG 192-bit; naik ke
  check-certificate pada skrip v2 setelah G1-FETCH lulus).
- Audit connect/disconnect kini = log accel-ppp (level=3) + journalctl unit;
  ingest platform (audit domain) menyusul bersama lab.
- Alokasi IP tunnel tetap iterasi scope per tenant (O(tenant) per
  enrollment) — catatan fase kapasitas 1.000 tenant.
- e2e spec onboarding bergantung worker interval 1 s + urutan (workers:1).
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan.
- PAT hanya di remote URL klon sandbox (tidak pernah di-commit; scan bersih
  di bawah); **rotasi PAT disarankan** karena pernah melewati kanal chat.

## 8. Kejujuran sesi (CONTRACT §9)

Status pekerjaan sesi ini: **IMPLEMENTED + VERIFIED_UNIT + VERIFIED_INTEGRATION
(backend/FE/e2e nyata)** untuk SSTP; **IMPLEMENTED (belum diverifikasi)** untuk
harness lab; **BLOCKED** untuk Gate A/G + bukti lab G1 (prasyarat eksternal).
Tidak ada tes yang ditandai PASS tanpa dijalankan; semua angka di §2 berasal
dari perintah nyata sesi ini.
