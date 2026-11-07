# Sesi Orkestrator — Phase-2 SSTP: kanal manajemen komplementer WireGuard

- **Agent/role**: orchestrator (GLM) — implementasi utama + integrasi + verifikasi.
- **Objective**: kelanjutan master directive user "Secure Router Connectivity" —
  **Phase-2 SSTP** sebagai kanal manajemen KOMPLEMENTER WireGuard (bukan
  pengganti): shared-port tunggal, kredensial per-router, MSCHAPv2 saja, verifikasi
  sertifikat server wajib nyala, isolasi tenant ketat; + lab GNS3 profil minimal
  (2 tenant LAN tumpang tindih) sebagai persiapan bukti G1.
- **Tanggal (UTC)**: 2026-11-07 (mulai 20261107T~14:2xZ; laporan 20261107T154532Z).
- **Branch/SHA awal**: `main` @ `16085f8` (hasil `git fetch` + `git log`;
  diverifikasi bersih, tanpa pekerjaan menggantung).
- **Dokumen/direktif rujukan**: CONTRACT.md (versi `1fff190`) §3 (anti
  overengineering), §4 (perubahan dokumen terkendali), §6 (mulai dari realita),
  §9 (verifikasi jujur), §10 (laporan); docs/ROUTEROS.md §1–§2 (enrollment);
  docs/ARCHITECTURE.md §4 (RLS); master directive user Phase-2 (persetujuan
  eksplisit — lihat §Keputusan); matriks kapabilitas klien VPN RouterOS
  `report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md`.

## Perubahan (berkas)

**Backend (Django — domain network):**
- `models.py`: model baru `SstpAccount` (kredensial per-router: username unik
  GLOBAL, password SecretBox, tunnel_ip unik, state desired/applied/removed).
- `migrations/0011_sstpaccount.py`: CreateModel + `enable_rls` + FK komposit
  (tenant, router) → network_router (pola 0002/0004).
- `services.py`:
  - `SUPPORTED_ENROLLMENT_PROTOCOLS = (wireguard, sstp)`; validasi versi SSTP
    v6+ (v5- → 422 `sstp_requires_v6`).
  - `_issue_sstp_credentials()` — kredensial diterbitkan saat draft; retry
    bounded atas tumbukan username.
  - `_sstp_gw_address()` — alamat PPP gateway = host kedua carve (100.127.0.2);
    `allocate_tunnel_ip()` kini mengecualikan .1 (WG) dan .2 (SSTP).
  - `_render_sstp_bootstrap()` + `_ROUTEROS_SSTP_TEMPLATE` — skrip v6/v7
    (sintaks berjarak): fetch+impor CA dari `/api/v1/bridge/enroll-ca`,
    sstp-client `authentication=mschap2` +
    `verify-server-certificate=yes` + `verify-server-address-from-certificate=yes`,
    tanpa add-default-route, rule API-SSL hanya dari .2, callback body
    token+username.
  - `complete_enrollment()` sadar-protokol (identitas SSTP = username vs WG =
    pubkey; mismatch → 409 `sstp_identity_mismatch`; replay §2.7 sama; bentuk
    identitas silang → 422).
  - `finalize_verification()` — capability + `verification.sstp` jujur
    (simulator ⇒ False; probe api_ssl nyata via sesi PPP ⇒ True);
    `device_identity.sstp_username`; akun → APPLIED.
  - `enroll_ca_bundle()` — baca CA dari env `MT_SSTP_CA_PATH` (materi publik;
    409 jujur tanpa env/berkas/bukan-PEM).
  - `render_sstp_config()` + `_SSTP_ACCEL_CONF_TEMPLATE` — render accel-ppp
    1.15.0.conf + chap-secrets (format `username password <ip-statis>`
    diverifikasi dari chap-secrets.c 1.15.0; berkas 0600; REMOVED tak
    dirender; iterasi scope per tenant pola render_host_config).
- `handlers.py`: `verify()` sadar-protokol (SSTP ⇒ akun APPLIED, bukan peer
  WG — tanpa ini job SSTP selalu gagal verify); release/replace me-revoke
  akun (state REMOVED).
- `views.py`/`urls.py`: bridge enroll-complete menerima `sstp_username`;
  endpoint baru `GET /api/v1/bridge/enroll-ca`; `verification.sstp` di detail
  router.
- `management/commands/render_sstp_config.py` (pola render_wg_config).
- `tests/integration/test_sstp_flow.py` — **18 tes** (lihat §Verifikasi).
- `tests/integration/test_enrollment_flow.py` — tes `unsupported` beralih ke
  `openvpn` (sstp kini didukung; l2tp/openvpn tetap ditolak jujur).
- `tests/unit/test_registry_pagination.py` — 116 param / rev 2.4.

**Frontend (apps/web):** `contracts.ts` (`RouterVerification.sstp`),
`RouterNewPage.tsx` (SSTP aktif v6+v7; v6+WG tetap memblokir dengan alasan ke
SSTP; ringkasan Prasyarat mengikuti protokol terpilih), mock `adapter.ts`
(paritas penuh backend + skrip fixture SSTP), i18n id/en (+1 kunci
`routers.protocol_sstp_hint`; revisi 3 teks; paritas 1063),
`RouterNewPage.test.tsx` (+1 tes: v6+SSTP dapat dilanjutkan).

**Installer/ops:** `instalasi.sh` — `setup_sstp()` fase-aware `MT_ENABLE_SSTP=1`
(pola `MT_ENABLE_RADIUS`): CA privat 10 th + sertifikat gateway SAN=MT_DOMAIN
(auto-regen saat SAN berubah; repair mengembalikan), env `MT_SSTP_CA_PATH`,
render via manage.py, unit `microtix-sstp.service` (pola kontrib upstream:
`accel-pppd -d` + Type=forking), health gate + doctor + repair/upgrade +
summary. `backend/scripts/build_accel_ppp.sh` — build accel-ppp **1.15.0**
dari tarball rilis resmi dipin SHA-256
(`408a7c02d25633ee2370887b67338c722858548d5431a7490c2af7774856e279`),
deps Debian resmi (build-essential, cmake, libssl-dev, libpcre2-dev — sesuai
README 1.15.0), out-of-tree, idempoten.

**Dokumen:** `docs/defaults.json` rev **2.4** (+`vpn.sstp_listen_port` 4443,
bounds 1024–65535, shared-port lintas tenant); `docs/ROUTEROS.md` §2.3
amendemen normatif SSTP (basis persetujuan: master directive); manifest
docs di-refresh (`--refresh` eksplisit); `BETA_RELEASE_STATUS.md` (baris
fitur + next milestone), `progress.md` (checkpoint sesi), `AGENT_HANDOFF.md`
(tabel §5).

**Lab:** `lab/README.md`, `lab/topology-phase2.json` (tahap A: gw+chr-a+
client-a; tahap B: +chr-b+client-b dengan **LAN sama 192.168.88.0/24**),
`lab/provision.py` (provisioner GNS3 API stdlib; family API dari
`/version` per OPERATIONS.md; cleanup terbatas prefix `microtix-`),
`lab/evidence-checklist.md` (bukti G1-WG/SSTP/ISO/FETCH/REV termasuk **uji
negatif** verifikasi sertifikat).

## Keputusan (dengan justifikasi — CONTRACT §3/§4)

1. **accel-ppp 1.15.0 dari sumber (build dipin)** — bukan repo pihak ketiga,
   bukan SoftEther/alternatif: TIDAK ada paket SSTP server di Debian resmi
   (dihimpun: paket `ppp` hanya pppd; permintaan pengemasan accel-ppp resmi
   masih terbuka); accel-ppp = satu-satunya daemon SSTP+MSCHAPv2+chap-secrets
   kelas ISP dengan dokumentasi lengkap; 1.15.0 dipin karena rilis terbaru
   (2026-10-29) dan 1.13.0 diperlukan minimal (opsi `[sstp] ssl-protocol` +
   perbaikan MITM SSTP hadir di 1.13.0). Semua kunci konfigurasi diverifikasi
   dari `accel-pppd/accel-ppp.conf` sampel + `chap-secrets.c` + `main.c`
   tarball 1.15.0 (bukan dari ingatan).
2. **Port 4443 (bukan 443)** — 443 dipakai Caddy HTTPS platform; SSTP tidak
   dapat berbagi 443 tanpa SNI dan klien v6 tanpa `add-sni` (matriks §Port
   steering). "Shared-port" berarti SATU port untuk seluruh router seluruh
   tenant (bukan per-tenant) — sesuai arsitektur direktif.
3. **Alamat PPP gateway = 100.127.0.2 (host kedua carve)** — satu carve
   100.127.0.0/16 untuk kedua protokol menjaga invariant "/32 unik global";
   .1/.2 dikecualikan dari alokasi (dites).
4. **CA platform privat (installer) alih-alih Let's Encrypt** — SSTP listener
   butuh berkas cert+key yang dimiliki root; CA privat membuat alur
   enroll-ca mandiri (tidak bergantung penyimpanan internal Caddy);
   sertifikat gateway SAN=MT_DOMAIN auto-regen. MITM pada fetch CA
   (check-certificate belum aktif — gap G1) dibatasi: CA materi publik +
   password MSCHAPv2 192-bit acak (offline attack tidak praktis) — residual
   risk tercatat; setelah G1-FETCH lulus, skrip v2 mengaktifkan
   check-certificate.
5. **Identitas bridge SSTP = username kredensial** (bukan sertifikat klien):
   klien SSTP RouterOS tanpa EAP (matriks); token 256-bit + kecocokan
   username terhadap SstpAccount = pengikatan enrollment↔kredensial.
6. **Amendemen normatif ROUTEROS.md §2.3** — status **APPROVED** (bukan
   PROPOSED): master directive user Phase-2 adalah keputusan produk
   eksplisit yang memerintahkan SSTP komplementer + batasan keamanannya
   (CONTRACT §4: "explicit user-approved product decisions"). Dif kata
   dijaga minimal (satu kalimat tambahan pada item objek milik platform).
7. **Tidak ada sub-agent implementasi paralel** pada sesi ini: perubahan
   menyentuh jalur inti bersama (services/handlers/views) yang harus koheren
   dalam satu transaksi perubahan; eksplorasi/riset bersumber vendor sudah
   tersedia dari sesi Phase-1 (matriks kapabilitas + audit explorer).
   Anti-overengineering: TIDAK ada model host SSTP baru (port/gateway dari
   registri + derivasi carve), TIDAK ada pustaka baru (stdlib + dep resmi
   Debian saja), TIDAK ada layanan antrian baru.

## Verifikasi (perintah, hasil, bukti)

Lingkungan: sandbox Linux; PostgreSQL **17.11 nyata** (deb-extract
`docs/tools/setup_env.sh`; `dev_bootstrap.sh` peran migrator/runtime + RLS),
Python 3.13 venv, pnpm 12.16.1, Playwright Chromium diunduh sesi ini.

| Perintah | Hasil |
|---|---|
| `MT_ENV=test .venv/bin/python -m pytest tests -q` | **391 passed** (+18 SSTP; sebelumnya 373) |
| `manage.py makemigrations --check --dry-run` | No changes detected (migrasi 0011 lengkap) |
| `manage.py check` | 0 issues |
| `bash scripts/test_radius.sh` (FreeRADIUS nyata) | **PASS 15/15** |
| `pnpm exec tsc -b --pretty false` / `eslint src --ext ts,tsx` | 0 error / 0 warning |
| `pnpm exec vitest run` | **67 passed** (+1) |
| `python3 scripts/check_i18n.py` | paritas OK (1063 kunci id/en) |
| `VITE_API_MODE=live pnpm exec vite build` (tanpa env = DITOLAK) | build OK; mock tetap ditolak |
| `make e2e` (Chromium + backend + worker nyata) | **12 passed** (termasuk routers.spec 2/2 pada wizard yang diubah) |
| `python3 docs/tools/check_docs.py` (setelah `--refresh`) | **PASS** |
| `bash -n instalasi.sh` + `bash -n backend/scripts/build_accel_ppp.sh` | OK |

**Tes yang TIDAK dijalankan (jujur):**
- ShellCheck: binary tidak tersedia/dapat dipasang di sandbox — `bash -n`
  saja yang dijalankan; CI tidak menjalankan shellcheck (diverifikasi dari
  `.github/workflows/ci.yml`) — ShellCheck penuh tetap disarankan sebelum
  Gate A/G.
- Instalasi nyata Debian 13 (Gate A/G) — butuh host+domain (blok eksternal).
- **Bukti lab G1 (CHR nyata)** — aset belum tersedia; semua status lab =
  IMPLEMENTED, BUKAN VERIFIED_LAB. Simulator TIDAK pernah dilaporkan sebagai
  konektivitas nyata (`verification.source`/`sstp/api_ssl/wireguard` jujur).
- accel-ppp tidak dibangun/dijalankan di sandbox (butuh Debian host + root);
  pin SHA-256 + kunci konfigurasi diverifikasi dari tarball rilis resmi.

## Keamanan/kompatibilitas

- Kredensial: password hanya keluar ke skrip (TTL 15 mnt, pembuat saja) +
  chap-secrets 0600 (ops host); DB hanya SecretBox; tidak pernah di-log.
- Tidak ada pelemahan: verifikasi sertifikat server WAJIB nyala pada skrip
  (tidak ada jalur mematikan); MSCHAPv2 saja; TLS 1.2 + dua suite
  terdokumentasi; `single-session=replace`; `mppe=deny`.
- Isolasi: username unik global + RLS (dites lintas tenant); /32 unik global
  lintas protokol (.1/.2 dikecualikan); revoke saat release/replace (dites).
- Kompatibilitas: API lama (tanpa protocol/version) tetap sah (default
  wireguard/7); migrasi additive-only; WireGuard path tidak berubah
  perilaku (391 tes termasuk 22 tes Phase-1 tetap lulus).
- PAT: hanya di remote URL klon sandbox; TIDAK pernah di-commit/dicetak
  (scan di bawah); **rotasi tetap disarankan** (melewati kanal chat).

## Bloker/risiko tersisa

1. Gate A/G host Debian 13 nyata — tetap penahan tunggal tag `v0.1.0-beta.1`.
2. Lab G1 (CHR/controller GNS3) — bukti perangkat nyata (G1-SSTP/ISO/FETCH)
   menunggu aset; checklist siap (`lab/evidence-checklist.md`).
3. Paritas field `verify-server-address-from-certificate` pada v6.49 belum
   terverifikasi vendor (matriks: gap v6) — bila lab menunjukkan field tidak
   ada pada v6, skrip v6 direvisi (keputusan tercatat di checklist G1-SSTP-2).
4. Session-event audit (connect/disconnect) saat ini = log accel-ppp +
   journalctl unit (level=3); ingest platform (ip-up/ip-down → audit domain)
   menyusul bersama lab.

## Commit/push

- Branch sesi: `session/2026-11-07-sstp-phase2` (dari `main` @ `16085f8`).
- Status remote: **PUSHED** — SHA diverifikasi via `git ls-remote` setelah
  push (dicatat di LATEST_HANDOFF §1). PR dibuka untuk review; MERGE ke main
  menunggu persetujuan reviewer (CONTRACT §11 — bukan di-merge sendiri oleh
  sesi ini).

## Langkah berikutnya (urut)

1. Review + merge PR sesi ini (reviewer independen disarankan menimbang
   perubahan keamanan: skrip SSTP + installer).
2. Saat host produksi tersedia: Gate A/G (`instalasi.sh install` →
   INSTALL_SUCCESS penuh) + build accel-ppp + `MT_ENABLE_SSTP=1` repair.
3. Saat aset lab tersedia: jalankan `lab/` tahap A→B + checklist G1 →
   aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, skrip v2 + cutover B3–B5.
4. Phase-3 direktif (L2TP/IPsec + OpenVPN) sesuai matriks kapabilitas.
5. Alternatif paralel aman: TK-701 ledger M7 / TK-602/607/608/609.
