# MicroTix

Aplikasi SaaS untuk pengusaha RT/RW Net Indonesia: MikroTik, pelanggan berbasis RADIUS per perusahaan, penagihan, pembayaran, pembukuan, monitoring dan backup.

**Status: kandidat beta 0.1 (R1-core)** — frontend DAN backend keduanya terimplementasi dan teruji: 252 tes backend (PostgreSQL nyata + RLS), 42 tes frontend, E2E browser nyata 7/7, verifikasi FreeRADIUS nyata 15/15, smoke live API 20/20. Fitur jaringan pada perangkat fisik menunggu bukti lab (gate G1) — status jujur per fitur: [docs/BETA_RELEASE_STATUS.md](docs/BETA_RELEASE_STATUS.md); bukti eksekusi: [docs/BETA_TEST_EVIDENCE.md](docs/BETA_TEST_EVIDENCE.md); rekam jejak: [docs/progress.md](docs/progress.md).

## Instalasi resmi (satu perintah)

Server Debian 13 (≥10GB disk, ≥2GB RAM) dengan root dan — bila ingin HTTPS publik — domain yang mengarah ke server:

```bash
sudo bash instalasi.sh install
```

Mode lain: `status`, `doctor`, `repair`, `upgrade`, `--dry-run`. Hasil jujur: `INSTALL_SUCCESS` (exit 0) / `INSTALL_PARTIAL` (exit 3 — inti sehat, domain/TLS belum) / `INSTALL_FAILED` (exit ≠ 0). Installer menyiapkan PostgreSQL 17 (peran migrator/runtime terpisah + RLS), backend Django, build frontend **live** (build mock ditolak), worker job engine, Caddy HTTPS same-origin, nftables, keypair WireGuard host, dan — opsional — FreeRADIUS (`MT_ENABLE_RADIUS=1`). Installer **tidak pernah menyentuh router pelanggan**; enrollment router dilakukan lewat aplikasi setelah platform hidup.

Verifikasi RADIUS nyata pasca-instalasi (bila diaktifkan):

```bash
cd backend && bash scripts/test_radius.sh
```

## Struktur repository

- `apps/web/` — frontend React 18 + TypeScript + Vite (live adapter + mode mock dev terisolasi).
- `backend/` — backend Django 5.2 + DRF (domain: identity/tenancy/jobs/subscriptions/network/radius/customers/backups/monitoring; PostgreSQL 17 + RLS FORCE).
- `instalasi.sh` — installer produksi Debian 13.
- `locales/{id,en}/` — katalog i18n domain `web`.
- `docs/` — kontrak produk, arsitektur, UI/UX, dan rencana implementasi (documentation-first; kode tunduk pada dokumen).

## Pengembangan

```bash
python3 docs/tools/check_docs.py          # validasi dokumen (kontrak)
cd backend && bash scripts/dev_bootstrap.sh   # PostgreSQL lokal + migrasi + seed
# backend:  .venv/bin/python -m pytest tests -q
# frontend: cd ../apps/web && pnpm install && pnpm exec vitest run
```

Mulai dari [indeks dokumen](docs/README.md). Untuk meminta coding agent melanjutkan, gunakan [master prompt eksekusi](docs/MASTER_PROMPT.md) dan [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) (titik masuk agent: selalu dari `main` terbaru). Agent menyelesaikan R1, lalu R2, kemudian R3/R4; menulis kode lokal tidak menunggu akses perangkat yang hanya diperlukan untuk verifikasi lab.

[Kebutuhan produk](docs/PRODUCT.md) memiliki harga dan kebijakan; [arsitektur](docs/ARCHITECTURE.md) memiliki stack/API/job/data; [rencana implementasi](docs/IMPLEMENTATION_PLAN.md) mengatur urutan; [audit](docs/AUDIT_REPORT.md) menjelaskan temuan dan perlakuan seluruh 77 berkas sumber.

Nama tampilan dikendalikan [branding.json](docs/branding.json), dengan override PROJECT_NAME/APP_NAME/BRAND_NAME. Identitas internal, data, sesi dan integrasi tetap stabil ketika nama display berubah.
