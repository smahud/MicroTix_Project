# MicroTix — Beta Release Notes (R1-core)

Status rilis: **BETA_READY_WITH_LIMITATIONS** — ditetapkan 2026-11-05
berdasarkan gate dan bukti aktual di bawah, bukan persepsi. Basis commit:
lihat `docs/progress.md` checkpoint BE-2.

## 1. Apa yang benar-benar berfungsi (diverifikasi lokal)

Semua butir di bawah memiliki tes otomatis yang lulus pada PostgreSQL 17.4
nyata (142 tes; lihat §4) DAN alur smoke live 20 asersi (runserver + HTTP
nyata; `make smoke`):

| Kemampuan | Bukti |
|---|---|
| Instalasi satu perintah `instalasi.sh install` (dry-run penuh + sintaks) | `bash -n` + dry-run 17 langkah + preflight menolak disk/OS tak memenuhi |
| Registrasi/login/MFA/sesi/tenant-switch/reauth | 30 tes integrasi + smoke |
| Isolasi tenant: RLS FORCE + konteks fail-closed + 404 generik | tes integrasi `test_rls.py` + smoke asersi 20 |
| Job engine (state machine, lease+fencing, outbox, uncertain) | `test_jobs_engine.py` |
| Subscription + kuota atomik (plan 6 paket PRODUCT.md §3) | `test_idempotency_quota.py` |
| **Enrollment router**: draft → token hashed TTL 15 mnt → /32 WireGuard reserved → bootstrap script bernamespace rtrw- → probe konsumsi token (replay-safe, identitas beda 409) → router read_only + NAS desired revision — atomik | `test_enrollment.py` (11 tes) + smoke asersi 7–15 |
| **Discovery read-only** (job; tanpa password; snapshot) | `handlers.py` + smoke asersi 15–16 |
| **Akun akses AAA** (sumber kebenaran + proyeksi radius.radcheck/radreply dalam transaksi sama; suspend → Auth-Type Reject; activate; rotasi) | `test_access_radius.py` (14 tes) + smoke |
| **Facade SQL RADIUS multi-tenant** (EXECUTE-only; NAS IP satu-satunya pengikat tenant; NAS tak dikenal = secure discard) | `test_access_radius.py::TestFacade` (4 tes) |
| **Isolasi RLS pada skema radius.\*** (tenant A tidak melihat B; username sama lintas tenant diproyeksikan terpisah) | `TestRadiusTenantIsolation` |
| **Layanan pelanggan** (customer+service+akun AAA+kuota atomik; reveal reauth-gated) | `test_services_csv.py` + smoke |
| **Impor CSV S2** (validasi tanpa tulis; commit idempoten per baris; batas 10k/10MiB) | `test_services_csv.py::TestCsvImport` |
| **Klien API-SSL RouterOS native** (protokol biner + TLS + pinning sertifikat; mutation jujur "pending_lab") | `test_apiclient.py` (14 tes termasuk server TLS in-process) |
| **NAS lifecycle + reconciler** (desired/applied revision; `radius_reconcile --dry-run/--apply/--mark-applied`) | `test_access_radius.py::TestNasLifecycle` |
| Frontend produksi TIDAK bisa build mode mock (gate vite + runtime) | `VITE_API_MODE=live` wajib; tanpa itu exit 1 |

## 2. Documentation Compliance Matrix (ringkas)

Format: DOC → REQUIREMENT → TASK → CODE → TEST → STATUS.
Status penuh per task: `docs/progress.md` checkpoint BE-2.

| Doc | Requirement inti | Task | Implementasi | Status |
|---|---|---|---|---|
| ROUTEROS.md §2 | Enrollment pulihkan, token hashed TTL, /32 unik, namespace rtrw-, tanpa reset | TK-301/302 | `domains/network/enrollment.py`, `views.py` | COMPLIANT (verified_local; lab G1 BLOCKED) |
| ROUTEROS.md §4 | Adapter typed, bounded I/O, pinning, tanpa command bebas | TK-304 | `adapters/routeros/apiclient.py` | COMPLIANT (verified_local; firmware lab BLOCKED) |
| ROUTEROS.md §3 | Discovery bounded tanpa password | TK-401 | `domains/network/handlers.py` | PARTIAL (wizard 8 langkah U07 belum; simulator-lengkap) |
| RADIUS.md §2–§5 | Proyeksi + facade + resolver + NAS lifecycle | TK-306/307 | `domains/access/*`, migrasi 0003 | COMPLIANT (verified_local) |
| RADIUS.md §6 | Suspend/restore proyeksi atomik | TK-501(partial) | `services.set_account_state` | COMPLIANT (Disconnect eksternal menunggu lab) |
| RADIUS.md §10.1 | Adopsi database-only S2 CSV | TK-404 | `domains/customers/csv_import.py` | PARTIAL (S1/S3/S4 belum) |
| RADIUS.md §10.2 | Cutover B0–B6 | TK-509 | — | MISSING (disengaja: gate G1 T16–T18/T21 belum lulus) |
| ARCHITECTURE §4 | RLS FORCE semua tabel tenant termasuk radius.* | TK-102/106* | migrasi RLS + tenant_scope reentrant | COMPLIANT |
| ARCHITECTURE §5 | Kontrak API + envelope + idempotency | TK-104 | live adapter FE + tes kontrak | COMPLIANT |
| ACCEPTANCE §3 | Gate fitur (tabel G0–G5) | — | release flags R2–R4 off | COMPLIANT (tidak ada klaim release_enabled) |
| PRODUCT §7–§9 | Pelanggan/layanan | TK-405 | `domains/customers` | PARTIAL (billing/isolir R2 jujur "not_billed") |
| OPERATIONS | Installer + backup + upgrade | §17 | `instalasi.sh` hardened | PARTIAL (instalasi produksi nyata belum diuji host root) |

## 3. Batasan beta yang DINYATAKAN (jujur — bukan klaim siap)

1. **FreeRADIUS daemon belum berjalan di sandbox** — proyeksi + facade SQL
   teruji langsung di PostgreSQL, tetapi autentikasi end-to-end via daemon
   nyata (radclient, T16/T19/T21) menunggu host Debian 13 + root
   (`make test-radius` jujur BLOCKED). **Jangan gunakan mode otoritatif
   produksi sebelum runbook `infra/freeradius/README.md` selesai.**
2. **Cutover B0–B6 TIDAK diimplementasikan** — gate G1 belum lulus; tidak
   ada endpoint yang mengubah konfigurasi RADIUS router. Router hasil
   enrollment selalu `read_only` + `enforcement_mode=local`.
3. **Perangkat MikroTik fisik tidak tersedia di sandbox** — klien API-SSL
   teruji protokol+TLS+pinning terhadap server in-process; perilaku per
   firmware menunggu lab (G1). Adapter default produksi tetap tersedia
   (`MT_ROUTEROS_ADAPTER=api_ssl`) tetapi BELUM berstatus verified_lab.
4. **Instalasi produksi nyata belum dieksekusi** — dry-run penuh + sintaks
   + preflight terverifikasi; eksekusi `install` pada host Debian 13 root
   dengan domain publik masih harus dijalankan operator (hasil yang jujur:
   INSTALL_SUCCESS/PARTIAL/FAILED dari gate nyata).
5. **Wizard migrasi U07 8-langkah belum penuh** — discovery + snapshot +
   CSV tersedia; penggabungan identitas lintas router (TK-410) dan S1/S3/S4
   belum.
6. **Monitoring U13/Prometheus (TK-502/503) belum** — sampel kesehatan
   per-probe tersedia (job), collector berkala belum.
7. **Playwright E2E browser belum** — digantikan smoke live 20 asersi;
   harness tetap todo.
8. **Billing/isolir R2** — status pembayaran tampil jujur "not_billed"
   (tidak dipalsukan).

## 4. Verifikasi aktual (lingkungan + command)

Lingkungan: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL **17.4 asli**
(binary zonky, tanpa root — bukan SQLite); Node v24 + pnpm 12.16.1;
Tanpa perangkat MikroTik/FreeRADIUS nyata (lihat §3).

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (backend) | 0 | **142/142 lulus** — 96 unit/integrasi lama + 46 baru (resolver, protokol API-SSL, proyeksi RADIUS, facade, RLS radius.*, enrollment+replay, services+CSV) |
| `bash scripts/smoke_live.sh` | 0 | **20/20 PASS** — health, register/verify, enrollment→bootstrap→probe→replay→discovery job, service+proyeksi, suspend/activate, CSV, isolasi tenant |
| `tsc -b --pretty false` (web) | 0 | typecheck bersih |
| `eslint src --ext ts,tsx` | 0 | 0 error/0 warning |
| `vitest run` | 0 | 42/42 lulus |
| `check_i18n.py` / `check_contrast.py` | 0 | 908 kunci paritas; 13/13 kontras AA |
| `VITE_API_MODE= pnpm exec vite build` | 1 | **DITOLAK** (gate live — bukti tidak ada fallback mock) |
| `VITE_API_MODE=live pnpm exec vite build` | 0 | dist produksi (vendor 164 kB gzip 54 kB) |
| `bash -n instalasi.sh` + dry-run penuh | 0 | 17 langkah; preflight menolak disk<10GB & non-Debian-13 |
| `python3 docs/tools/check_docs.py` | 0 | dokumentasi valid (21 file, 85 task) |
| `make test-radius` | 1 | BLOCKED jujur (tanpa FreeRADIUS di sandbox) |

## 5. Cara menjalankan beta (Debian 13, setelah prasyarat host)

```bash
git clone https://github.com/smahud/MicroTix_Project && cd MicroTix_Project
sudo MT_DOMAIN=isp.example.id bash instalasi.sh install
# Ikuti onboarding admin, login, buat tenant, enroll router pertama
# melalui UI (U05) — router TIDAK pernah disentuh tanpa enrollment sah.
```

Pengembangan lokal: `make bootstrap && make test && make smoke`.
