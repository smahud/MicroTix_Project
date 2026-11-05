# MicroTix

Aplikasi SaaS untuk pengusaha RT/RW Net Indonesia: MikroTik, pelanggan berbasis RADIUS per perusahaan, penagihan, pembayaran, pembukuan, monitoring dan backup.

**Status: Beta R1-core — BETA_READY_WITH_LIMITATIONS** (penetapan berbasis gate dan bukti; lihat [docs/BETA_RELEASE_NOTES.md](docs/BETA_RELEASE_NOTES.md)). Frontend + backend terintegrasi nyata (mode mock dilarang pada build produksi), PostgreSQL 17 dengan RLS per tenant, job engine, enrollment router MikroTik + WireGuard + API-SSL, akun akses AAA dengan proyeksi `radius.*` multi-tenant, layanan pelanggan + impor CSV. Cutover RADIUS B0–B6 sengaja belum aktif sampai gate lab (G1) lulus.

Struktur repository:

- `apps/web/` — frontend R1 (React + TypeScript + Vite + TanStack Query + FormatJS).
- `backend/` — backend Django 5.2 + DRF (domain modular: identity, tenancy, jobs, subscriptions, network/enrollment, access/RADIUS, customers).
- `backend/infra/freeradius/` — template konfigurasi FreeRADIUS 3.2 + runbook lab.
- `locales/{id,en}/` — katalog i18n domain `web`.
- `docs/` — kontrak produk, arsitektur, UI/UX, rencana implementasi, catatan rilis beta.
- `instalasi.sh` — installer resmi Debian 13 (install/status/doctor/upgrade/repair/--dry-run).

## Instalasi (produksi, Debian 13 amd64/arm64)

```bash
sudo MT_DOMAIN=isp.example.id bash instalasi.sh install
```

Prasyarat host: Debian 13, ≥10GB disk, ≥2GB RAM, domain mengarah ke host
(untuk HTTPS via Caddy). Router MikroTik TIDAK diubah installer — enrollment
router dilakukan lewat aplikasi dengan otorisasi Owner (docs/ROUTEROS.md §2).
Hasil instalasi dilaporkan jujur: `INSTALL_SUCCESS` / `INSTALL_PARTIAL`
(domain/TLS belum) / `INSTALL_FAILED` (gate wajib gagal).

## Pengembangan lokal

```bash
make bootstrap          # dependensi pinned + PostgreSQL + migrasi + seed
make test               # unit
make test-integration   # PostgreSQL nyata: RLS/transaksi/race
make test-contract      # OpenAPI/envelope/permission
make smoke              # alur live 20 asersi (runserver + curl)
make i18n-check         # paritas katalog id/en
python3 docs/tools/check_docs.py
```

Frontend: `cd apps/web && pnpm install && pnpm dev` (mode mock terisolasi
berlabel; integrasi nyata: `VITE_API_MODE=live pnpm build` — build produksi
tanpa ini **ditolak**).

Mulai dari [indeks dokumen](docs/README.md). Untuk meminta coding agent
melanjutkan pembangunan, gunakan [master prompt eksekusi](docs/MASTER_PROMPT.md).
Rekam jejak verifikasi per checkpoint: [docs/progress.md](docs/progress.md).

Pemeriksaan dokumen dari akar repository:

```bash
python3 docs/tools/check_docs.py
```

[Kebutuhan produk](docs/PRODUCT.md) memiliki harga dan kebijakan; [arsitektur](docs/ARCHITECTURE.md) memiliki stack/API/job/data; [rencana implementasi](docs/IMPLEMENTATION_PLAN.md) mengatur urutan; [audit](docs/AUDIT_REPORT.md) menjelaskan temuan dan perlakuan seluruh 77 berkas sumber.

Nama tampilan dikendalikan [branding.json](docs/branding.json), dengan override PROJECT_NAME/APP_NAME/BRAND_NAME. Identitas internal, data, sesi dan integrasi tetap stabil ketika nama display berubah.
