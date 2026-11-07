# MicroTix — Status Rilis Beta (BETA_RELEASE_STATUS)

Ditetapkan: 2026-11-05 (Asia/Jakarta) — hasil konsolidasi dua agent paralel
(master prompt V5; rekam jejak lengkap: [progress.md](progress.md) checkpoint
INTEGRATION-1; bukti eksekusi: [BETA_TEST_EVIDENCE.md](BETA_TEST_EVIDENCE.md)).

## Version candidate

- **Kandidat**: `v0.1.0-beta.1` — commit kandidat: **`1ccf264`** (CI hijau:
  backend+frontend+docs).
- **Status tagging: NOT_READY (§15)** — tag DITUNDA sampai **Gate A/G**
  (instalasi bersih pada host Debian 13 nyata: root + `MT_DOMAIN` + DNS →
  `INSTALL_SUCCESS`) dieksekusi dan lulus. Sandbox konsolidasi tidak dapat
  memverifikasinya (tanpa root/domain). Setelah Gate A/G lulus, tag dibuat
  menunjuk tepat ke commit main teruji — bukan commit yang belum diverifikasi.
- **Basis kanonis**: `main` @ **`8da2c2d`** (merge commit PR #1 dari
  `integration/beta-0.1`; CI GitHub Actions hijau: backend+frontend+docs).
- **Sumber kebenaran tunggal**: `main`. Branch `parallel/beta-be2` dan
  `integration/beta-0.1` disimpan sebagai arsip riwayat — agent berikutnya
  WAJIB memulai dari `main`.

## Release scope (R1-core)

### Fitur AKTIF (di-back oleh bukti nyata)

| Fitur | Bukti |
|---|---|
| Registrasi/login/MFA TOTP/sesi/tenant-switch/reauth | 222 tes backend + smoke |
| Isolasi tenant: RLS FORCE + konteks fail-closed **reentrant** + 404 generik | `test_rls.py` (8 tes termasuk regresi scope-bersarang) |
| Job engine (state machine §6, lease+fencing, outbox, uncertain→readback) | `test_jobs_engine.py` |
| Subscription + kuota atomik (6 paket PRODUCT.md §3) + approval platform M2 | `test_idempotency_quota.py`, `test_ops_platform_admin.py` |
| Pelanggan/layanan/akun akses AAA + reveal reauth-gated + CSV S2 + **migrasi identitas DB-only** (discovery→konflik→merge/keep_one/rename→commit) | `test_customers_api.py`, `test_migration_flow.py` |
| Enrollment router: draft→token hash TTL→bootstrap idempoten TANPA reset/reboot→probe konsumsi atomik→read-only + peer WG | `test_enrollment_flow.py` |
| Discovery read-only (tanpa password) + snapshot | `test_enrollment_flow.py` |
| **RADIUS AAA nyata**: skema radius.* + RLS + facade SECURITY DEFINER + proyeksi (suspend→Reject) + reconciler + accounting idempoten/monotonik | **FreeRADIUS 3.2.7 + radclient NYATA: 15/15 (T16/T19/T20/T21)** |
| Cutover B0–B6 (preflight jujur→parity→install→observasi NYATA→authoritative→rollback) | `test_radius_cutover.py` |
| Backup router (commit-before-prune, retention) + monitoring (unknown ≠ down) | `test_ops_backups.py`, `test_ops_monitor.py` |
| **Klien API-SSL RouterOS native** (TLS + pin SHA-256 + bounded + anti-SSRF) — tersedia via `MT_ROUTEROS_ADAPTER=api_ssl`; default simulator | `test_apiclient.py` (14 tes, server TLS in-process) |
| Frontend live adapter penuh (CSRF, idempotency) + **gate anti-mock** (build produksi tanpa live DITOLAK) | 42/42 FE + verifikasi build sesi ini |
| Installer `instalasi.sh`: install/status/doctor/repair/upgrade/dry-run; 17 langkah; WireGuard host; exit 1/3/0 | `bash -n` + shellcheck 0 error + dry-run + gerbang preflight terbukti menolak |
| **Dokumen terbit PDF (TK-109, sesi 2026-11-06 lanjutan 3)**: invoice internet & kwitansi — snapshot bahasa/zona/templat/nilai + sha256, reprint dari artifact tersimpan (T23-I18-02), renderer terbatas jaringan/file (xhtml2pdf invariant; tanpa fetch eksternal), immutable via trigger DB | `tests/unit/test_documents_render.py` (15) + `tests/integration/test_documents_api.py` (9) |
| **Billing internet M6 core (TK-601, sesi 2026-11-06 lanjutan 3)**: paket penagihan BIL-02 (fixed_monthly/anniversary, prepaid/postpaid, due_day clamp, first_period_policy), invoice + snapshot harga + UNIQUE periode anti-scheduler-ganda (AC-BIL), penerimaan dua tahap submitted→verified/rejected + alokasi ≤ nilai/sisa + kredit + kwitansi bernomor + aging bucket; pembayaran tidak otomatis aktivasi; scheduler `issue_due_invoices` zona tenant (idempoten, dry-run) | `test_billing_calendar.py` (32 unit) + `test_billing_invoice_flow.py` (23) + `test_billing_payments.py` (21) + `test_billing_contract.py` (3); backend 355/355 |
| **UI billing U09/U10 (TK-604, sesi 2026-11-06 lanjutan 4)**: U09 tiga tab (Invoice·Pengajuan·Terverifikasi) + periode filter + aging strip + catat penerimaan (bukti wajib transfer/e-wallet) + verifikasi dana dengan editor alokasi + tolak beralasan + PDF invoice/kwitansi same-origin; U10 kandidat suspended + kelayakan tagihan nyata (tanpa tertunggak + pernah lunas, >1 halaman) + snapshot massal + validasi kondisi terbaru per item (item asing/berubah blok item itu saja) + hasil per item + retry aman + label jujur router non-otoritatif; aktivasi SELALU manual terpisah (PRODUCT §13) | `test_billing_invoice_flow.py` (+2 kursor) + `test_billing_payments.py` (+2 kursor) + `test_customers_api.py`/`test_customers_contract.py` (field service) — backend **359/359**; FE vitest **61/61** (eligibility/adapter/halaman); e2e `billing.spec.ts` **3/3** (PDF nyata, blokir per item, verifikasi→aktivasi) — `make e2e` **10/10** |
| **Onboarding router aman Phase-1 (sesi 2026-11-07, master directive konektivitas)**: pilih protokol (WireGuard aktif; SSTP/L2TP/OpenVPN tampil "direncanakan" — ditolak 422 jujur) + versi RouterOS (v7.1+ wajib utk WG; v6 diblokir dengan alasan); skrip bootstrap RouterOS v7 dibangkitkan BACKEND dari state tervalidasi — endpoint publik gateway terkonfigurasi (`vpn.gateway_hostname`/MT_PUBLIC_HOST/MT_DOMAIN; produksi tanpa nilai = DITOLAK, bukan fallback palsu; dev/test = `microtix.invalid`), port dari state host/enrollment, allowed-address hanya /32 server, tanpa artefak SCEP/pembacaan private-key, token di body callback; alokasi IP tunnel kini sadar-lintas-tenant (RLS); kunci publik WG unik global untuk peer AKTIF (409 lintas tenant); verifikasi jujur: `capability.source` = adapter aktif, simulator ⇒ api_ssl/wireguard **False** (bukan klaim terhubung); jalur api_ssl melakukan probe TCP+TLS NYATA (pin = fingerprint teramati) dengan retry re-entry VERIFYING | `test_enrollment_flow.py` **22 tes** (protokol/versi/gateway/kejujuran/konflik-pubkey/retry-probe) — backend **373/373**; FE vitest RouterNewPage **5 tes**; e2e `routers.spec.ts` **2/2** (alur penuh backend+worker NYATA: skrip→bridge→terverifikasi berlabel Simulasi; v6 memblokir) — `make e2e` **12/12** |
| **Phase-2 SSTP — kanal manajemen komplementer WireGuard (sesi 2026-11-07 lanjutan, master directive konektivitas)**: `protocol=sstp` aktif untuk RouterOS **v6.49.x + v7** (v6 kini dapat di-onboard read-only; v5- ditolak 422 jujur); kredensial per-router (`SstpAccount` migrasi 0011 + RLS/FK komposit): username **unik global** lintas tenant + password CSPRNG 192-bit SecretBox — terbit saat draft, dirender HANYA ke skrip bootstrap (TTL 15 mnt) + chap-secrets ops host (0600); skrip bootstrap v6/v7 (sintaks berjarak) — MSCHAPv2 SAJA, `verify-server-certificate=yes` + `verify-server-address-from-certificate=yes` WAJIB nyala, CA platform diimpor via endpoint publik `/api/v1/bridge/enroll-ca` (env `MT_SSTP_CA_PATH`; tanpa env = 409 jujur), TANPA add-default-route, /32 dialokasikan server-side; bridge enroll-complete sadar-protokol (identitas SSTP = username — mismatch 409 `sstp_identity_mismatch`; replay semantik sama §2.7); kejujuran verifikasi diperluas `verification.sstp` (simulator ⇒ False; probe api_ssl nyata via sesi PPP ⇒ True); release/replace me-revoke akun (REMOVED — tak dirender lagi); server = **accel-ppp 1.15.0** (build sumber dipin sha256 `backend/scripts/build_accel_ppp.sh` — tidak ada paket resmi Debian; diverifikasi dari tarball rilis): TLS 1.2 saja + ciphers `AES256-SHA:AES256-GCM-SHA384` (dua suite terdokumentasi klien RouterOS), listener **shared-port** `vpn.sstp_listen_port` (defaults rev 2.4; default 4443 — 443 milik Caddy), `single-session=replace`, `mppe=deny`, render `manage.py render_sstp_config` (accel-ppp.conf + chap-secrets format `username password <ip-statis>` diverifikasi dari chap-secrets.c 1.15.0); installer `setup_sstp` fase-aware `MT_ENABLE_SSTP=1` (CA privat 10 th + cert gateway SAN=MT_DOMAIN auto-regen; unit `microtix-sstp.service`; gerbang health jujur); lab GNS3 profil minimal Phase-2 (`lab/` — topologi 2 tahap termasuk 2 tenant LAN sama 192.168.88.0/24 + provisioner API-driven + checklist bukti G1) — **BELUM VERIFIED_LAB** (menunggu aset CHR/controller) | `test_sstp_flow.py` **18 tes** (draft v6/v7+kredensial unik lintas tenant+RLS, isi skrip: mschap2/verify-yes/tanpa default-route/tanpa IP tunnel, bridge mismatch/replay/422 silang-protokol, kejujuran simulator vs api_ssl, revoke, render accel-ppp.conf+chap-secrets 0600+akun REMOVED tak dirender, endpoint CA 409/PEM/non-PEM, alokasi /32 skip .1/.2) — backend **391/391**; FE vitest RouterNewPage **6 tes** (SSTP aktif; v6+SSTP lanjut) — vitest **67/67**; e2e **12/12**; docs check PASS |

### Fitur TIDAK aktif (jujur — jangan diaktifkan tanpa gate)

| Fitur | Penyebab | Gate yang menunggu |
|---|---|---|
| `MT_ROUTEROS_ADAPTER=api_ssl` sebagai default | Tanpa bukti perangkat lab | **G1**: T01/T16–T18/T20–T21 pada CHR/fisik |
| Mutasi konfigurasi router (apply/cutover/backup via API-SSL) | Adapter menolak `*_pending_lab` | G1 + pilot G3 |
| Cutover authoritative pada NAS produksi | B3/B4 butuh jendela observasi nyata | G1/G3 |
| R2 sisa M6/M7 (isolir otomatis TK-602, saldo pembuka TK-607, dokumen koreksi TK-608, kolektor TK-609, ledger M7 TK-701+) | M6 core + dokumen + **UI U09/U10 (TK-604) sudah aktif sesi 2026-11-06 lanjutan 4**; sisanya backlog | Roadmap M6/M7 lanjutan |
| R3 ACS, R4 OLT/WAN advanced | Deferred (master prompt §7 P3) | Roadmap R3/R4 |
| Auto-isolir pelanggan | Tanpa bukti keamanan + pilot | G2/G3 |

## Supported environment

- **Server**: Debian 13 (trixie) x86_64; ≥10GB disk; ≥2GB RAM; root untuk
  installer produksi.
- **Stack**: Python 3.13.5 (deps patch-exact), Django 5.2.19, DRF 3.16.1,
  PostgreSQL 17, Node 20+/24 + pnpm 12.16.1, Caddy, nftables, wireguard-tools,
  FreeRADIUS 3.2 (opsional `MT_ENABLE_RADIUS=1`).
- **Browser**: Chrome/Edge/Firefox modern (SPA React 18).

## Tes: lulus / terblokir

| Suite | Hasil |
|---|---|
| Backend unit+integrasi+kontrak (PostgreSQL nyata) | **373/373 PASS** (359 + 14 onboarding Phase-1: protokol/versi/gateway/kejujuran/konflik-pubkey-lintas-tenant/retry-probe-api-ssl, sesi 2026-11-07) |
| Frontend (tsc/eslint/vitest/i18n) | **66/66 + 0 error + paritas 1062** |
| RADIUS nyata (FreeRADIUS+radclient) | **15/15 PASS** |
| Smoke live API (runserver+curl, alur pendaftaran→enrollment→layanan) | **20/20 PASS** (basis be2) |
| Docs static check | **PASS** (21 file, 85 task, 240 edge, 256 kasus) |
| Installer: sintaks + shellcheck + dry-run | **PASS** (preflight menolak disk 8GB<10GB dengan benar) |
| **verified_lab perangkat MikroTik fisik (G1)** | **BLOCKED** — tidak ada perangkat/lab CHR |
| **Instalasi produksi nyata host root + domain (Gate A/G)** | **BLOCKED** — sandbox tanpa root/domain |
| Browser E2E Playwright | **12/12 PASS** (sesi 2026-11-07: 10 sebelumnya + 2 onboarding router — alur penuh backend+worker NYATA: skrip→bridge→terverifikasi berlabel Simulasi; v6 memblokir kelanjutan) |
| CI GitHub Actions (backend/frontend/docs) | **HIJAU** pada `8da2c2d` (backend ✓ frontend ✓ docs ✓) |

## Known limitations

1. Semua interaksi router (enrollment/discovery/cutover) berjalan pada
   **simulator** secara default — capability evidence selalu mencatat
   `source=simulator, verified_lab=false`; tidak ada klaim perangkat nyata.
2. WireGuard: installer menyiapkan keypair + `wg0.conf` + env
   `MT_WG_SERVER_PUBKEY`; **adopsi keypair oleh model `WireGuardHost`
   (X25519 nyata) + render peers host + probe handshake kini DIIMPLEMENTASI**
   (`adopt_wg_host`/`render_wg_config`/`probe_wg`); **aktifasi interface
   (`systemctl enable --now wg-quick@wg0`) dan probe pada host nyata tetap
   langkah ops — belum ada bukti lab WG**.
3. HTTPS publik memerlukan `MT_DOMAIN` + DNS; tanpa itu installer jujur
   mengembalikan `INSTALL_PARTIAL` (exit 3) — bukan beta publik.
4. Publikasi kunci publik WG host: **jalur adopsi installer (X25519 nyata)
   aktif** via env `MT_WG_SERVER_PUBKEY` (fallback deterministik hanya bila
   env kosong — dev/test, berlabel `key_source=generated_dev`). Probe handshake
   pada interface host NYATA menunggu host root (bukan sandbox).
5. Email dev via konsol; SMTP produksi dikonfigurasi lewat env.
6. UI billing U09/U10 (TK-604): bukti transfer belum dapat diperbesar
   (backend belum menyediakan endpoint ambil bukti — hanya `has_proof`);
   dialog verifikasi belum menyebut rekening tujuan (tak ada di kontrak
   pembayaran M6); hasil per item "Menunggu koneksi" menunggu bukti NAS
   (G1) — digantikan label jujur "belum dijamin pada router ini";
   kelayakan aktivasi menilai maksimum 10 halaman × 200 invoice/akun.
7. Onboarding router Phase-1 (sesi 2026-11-07): sintaks skrip bootstrap
   RouterOS v7 DAN validasi sertifikat callback `/tool/fetch`
   (`check-certificate`) **belum terbukti pada perangkat nyata** — menunggu
   lab G1 (gap MITM token dibatasi oleh token sekali pakai + TTL 15 menit
   + konsumsi atomik; lihat laporan orkestrator sesi ini). Jalur
   `MT_ROUTEROS_ADAPTER=api_ssl` melakukan probe TCP+TLS nyata namun
   **login API penuh menunggu skrip v2** (akun API platform belum dibuat
   oleh skrip pada router — celah terdokumentasi G1). Alokasi IP tunnel
   kini sadar-lintas-tenant namun berbentuk iterasi scope per tenant
   (biaya O(tenant) per enrollment — dicatat untuk fase kapasitas).

## Deployment readiness

- **Private beta / self-hosted**: SIAP DICOBA dengan batasan di atas pada
  Debian 13 bersih (`sudo bash instalasi.sh install`).
- **Public beta**: BELUM — menunggu Gate A/G (instalasi nyata host
  root+domain) dan keputusan aktivasi RADIUS setelah lab.
- Instruksi resmi: README.md bagian instalasi; verifikasi RADIUS:
  `cd backend && bash scripts/test_radius.sh`.

## Next milestones

1. Gate A/G: instalasi produksi nyata + domain → INSTALL_SUCCESS penuh.
2. Lab MikroTik CHR (G1) → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl` →
   cutover B3–B5 dengan NAS nyata. Termasuk bukti lab item onboarding
   Phase-1: sintaks skrip v7 pada CHR, `check-certificate` fetch (+SNTP/CA),
   skrip v2 (akun API-SSL platform pada router), handshake WG nyata.
3. Master directive konektivitas: ~~Phase-2 SSTP~~ **SELESAI & TERINTEGRASI (sesi 2026-11-07 lanjutan)** — server accel-ppp 1.15.0 dipin (build sumber), skrip v6/v7, kredensial per-router, kejujuran verifikasi; bukti LAB (G1-SSTP/ISO) menunggu aset CHR/controller → Phase-3 L2TP/IPsec + OpenVPN → Phase-4 hardening (rotasi/cabut, Super-Admin config UI, demo) — matriks kapabilitas: `report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md`.
4. M6/M7 lanjutan: TK-701 ledger M7 atau TK-602/607/608/609 (lihat
   LATEST_HANDOFF urutan prioritas).
5. Harness GNS3 API-driven (blokir infrastruktur + image CHR berlisensi).
