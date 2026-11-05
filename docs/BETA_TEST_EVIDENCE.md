# MicroTix — Bukti Uji Beta (BETA_TEST_EVIDENCE)

Rekam jejak perintah + hasil aktual yang DIEKSEKUSI (bukan diklaim) pada
sesi konsolidasi 2026-11-05. Lingkungan: Debian 13 (trixie) sandbox;
Python 3.13.5; PostgreSQL 17.11 nyata (binary deb non-root, peran terpisah
mtx_migrator/mtx_app, RLS aktif); FreeRADIUS 3.2.7 + radclient (deb trixie,
non-root); Node v24.22.2 + pnpm 12.16.1. Status per dokumen status rilis:
[BETA_RELEASE_STATUS.md](BETA_RELEASE_STATUS.md).

## 1. Verifikasi baseline (sebelum integrasi)

| # | Perintah | Target | Hasil |
|---|---|---|---|
| 1.1 | `pytest tests -q` | `main` @ `cd5142c` | **207 passed** |
| 1.2 | `bash scripts/test_radius.sh` | `main` (setelah grant manual sementara) | **PASS 15/15** (T16/T19/T20/T21) |
| 1.3 | `pytest tests -q` | `parallel/beta-be2` @ `c9023e6` | **142 passed** |
| 1.4 | `bash scripts/smoke_live.sh` | `parallel/beta-be2` | **SMOKE: 20 PASS, 0 FAIL** |
| 1.5 | `tsc -b` / `eslint src` / `vitest run` | `main` apps/web | 0 error / 0 error / **42 passed** |
| 1.6 | `VITE_API_MODE=live vite build` | `main` | sukses (bundle live) |
| 1.7 | `vite build` TANPA live | `main` | **DITOLAK** oleh gate anti-mock (sesuai desain §5) |
| 1.8 | `python3 docs/tools/check_docs.py` | `main` | **PASS** (21 file/85 task/240 edge/256 kasus/662 asersi) |
| 1.9 | `python3 scripts/check_i18n.py` | `main` | parity OK (id 908 / en 908, 0 hilang) |

### Bukti bug P0 grant (reproduksi sebelum perbaikan)

```
$ bash scripts/test_radius.sh   (main, instalasi bersih)
django.db.utils.ProgrammingError: permission denied for schema radius
BLOCKED: seed_radius_check gagal
$ psql -t -c "SELECT count(*) FROM information_schema.role_table_grants
              WHERE grantee='mtx_app' AND table_schema='radius';"
      0
```

## 2. Verifikasi hasil integrasi (`integration/beta-0.1`)

| # | Perintah | Hasil |
|---|---|---|
| 2.1 | `python manage.py check` | System check identified no issues |
| 2.2 | `pytest tests -q` | **222 passed** (207 + 1 regresi RLS bersarang + 14 API-SSL) |
| 2.3 | `REVOKE ALL ... radius` → `manage.py grant_runtime` | OK (skema: public, radius); grant tabel radius **0 → 28**; USAGE=t; public 180 tetap |
| 2.4 | `bash scripts/test_radius.sh` (jalur fresh tanpa grant manual) | **PASS 15/15** |
| 2.5 | `tsc -b --pretty false` | 0 error |
| 2.6 | `eslint src --ext ts,tsx` | 0 error / 0 warning |
| 2.7 | `vitest run` | **42 passed** (5 file) |
| 2.8 | `VITE_API_MODE=live vite build` | sukses |
| 2.9 | `python3 scripts/check_i18n.py` | parity OK |
| 2.10 | `bash -n instalasi.sh` | OK |
| 2.11 | `shellcheck -S error instalasi.sh` | **0 error** (warning minor pra-ada: SC2034/SC1090/SC2155) |
| 2.12 | `bash instalasi.sh --dry-run` | **preflight MENOLAK dengan benar** (disk 8GB < 10GB minimum) |
| 2.13 | `python3 docs/tools/check_docs.py` | **PASS** |

### Detail kasus RADIUS nyata yang dilulusi (1.2 / 2.4 — sama)

- T16: PAP valid → Access-Accept + Mikrotik-Rate-Limit; password salah →
  Reject; restart daemon → state DB bertahan → Accept; secret NAS salah →
  tanpa balasan valid (secure discard); radpostauth terisi tanpa password.
- T19: username sama via NAS tenant B → Accept data B; password tenant A →
  Reject (isolasi multi-tenant dari alamat sumber; decoy NAS-IP diabaikan).
- T20: akun suspended → Auth-Type Reject.
- T21: Start/Interim/Stop + counter monotonik (interim basi diabaikan) +
  late-Start tanpa reopen + Simultaneous-Use=1 (auth saat sesi terbuka →
  Reject).

## 3. Yang TIDAK dieksekusi (jujur)

| Item | Status | Penyebab |
|---|---|---|
| Tes lab perangkat MikroTik fisik/CHR (T01/T10/T17) | **BLOCKED** | Tidak ada perangkat/lab pada sandbox |
| Instalasi produksi host root + domain (Gate A/G) | **BLOCKED** | Sandbox tanpa root/domain publik |
| Browser E2E Playwright | **NOT_RUN** | Harness belum dibangun |
| CI GitHub Actions | Menunggu push PR | Eksekusi pasca-push (lihat progress.md) |

## 4. Ringkasan gate (ACCEPTANCE.md)

| Gate | Status scope beta |
|---|---|
| G0 desain & kontrak | LULUS (docs check PASS + tes kontrak 8+ dalam 222) |
| G1 RouterOS/RADIUS nyata | **SEBAGIAN**: RADIUS daemon nyata 15/15; perangkat router fisik BLOCKED → fitur mutasi router & api_ssl default TIDAK diaktifkan |
| G2 keamanan & isolasi | LULUS untuk scope aktif (RLS fail-closed + reentrant, CSRF, AEAD, redaction; secret scanning via review — tidak ada secret dalam commit) |
| G3 pilot terbatas | BELUM (menunggu instalasi nyata) |
| G4 benchmark/scale | N/A beta |
| G5 observability & recovery drill | SEBAGIAN (health/ready + backup job; drill penuh menunggu host nyata) |
