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

### Fitur TIDAK aktif (jujur — jangan diaktifkan tanpa gate)

| Fitur | Penyebab | Gate yang menunggu |
|---|---|---|
| `MT_ROUTEROS_ADAPTER=api_ssl` sebagai default | Tanpa bukti perangkat lab | **G1**: T01/T16–T18/T20–T21 pada CHR/fisik |
| Mutasi konfigurasi router (apply/cutover/backup via API-SSL) | Adapter menolak `*_pending_lab` | G1 + pilot G3 |
| Cutover authoritative pada NAS produksi | B3/B4 butuh jendela observasi nyata | G1/G3 |
| R2 billing/ledger penuh, isolir otomatis | Belum diimplementasi (backlog) | Roadmap M6/M7 |
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
| Backend unit+integrasi+kontrak (PostgreSQL nyata) | **252/252 PASS** (222 konsolidasi + 23 WG-1 + 7 hardening post-review; sesi 2026-11-06) |
| Frontend (tsc/eslint/vitest/i18n) | **42/42 + 0 error + parity 908** |
| RADIUS nyata (FreeRADIUS+radclient) | **15/15 PASS** |
| Smoke live API (runserver+curl, alur pendaftaran→enrollment→layanan) | **20/20 PASS** (basis be2) |
| Docs static check | **PASS** (21 file, 85 task, 240 edge, 256 kasus) |
| Installer: sintaks + shellcheck + dry-run | **PASS** (preflight menolak disk 8GB<10GB dengan benar) |
| **verified_lab perangkat MikroTik fisik (G1)** | **BLOCKED** — tidak ada perangkat/lab CHR |
| **Instalasi produksi nyata host root + domain (Gate A/G)** | **BLOCKED** — sandbox tanpa root/domain |
| Browser E2E Playwright | **7/7 PASS** (sesi 2026-11-06: `make e2e` — Chromium nyata ↔ backend nyata; login happy/error, guard, isolasi tenant 404, register→verifikasi email→login tenant baru, i18n, mobile 360px) |
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
   cutover B3–B5 dengan NAS nyata.
3. Playwright E2E harness (`make e2e`).
4. M6/M7: billing/ledger R2 (invoice, pembayaran, buku besar).
5. Adopsi keypair WG installer oleh backend + probe handshake.
