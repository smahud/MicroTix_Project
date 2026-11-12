# MicroTix

Aplikasi SaaS untuk pengusaha RT/RW Net Indonesia: MikroTik, pelanggan berbasis RADIUS per perusahaan, penagihan, pembayaran, pembukuan, monitoring dan backup.

**Status: kandidat beta 0.1 — NOT_READY untuk Production Beta.** Status aktual, exact SHA, PR dan code/environment blockers ada di [report/LATEST_HANDOFF.md](report/LATEST_HANDOFF.md). Bukti historis: [docs/BETA_TEST_EVIDENCE.md](docs/BETA_TEST_EVIDENCE.md) dan [docs/progress.md](docs/progress.md); hasil lokal/CI tidak menggantikan gate perangkat, install/upgrade dan recovery.

**Agent mulai/resume dari [task/0000-start-here.md](task/0000-start-here.md).** Controller menulis penugasan Markdown bernomor; executor mengimplementasikan, menguji, membuat laporan, commit/push dan menutup dengan `_done.md`. Review exact SHA tetap terpisah sesuai [CONTRACT.md §6A](CONTRACT.md).

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
- `task/` — panduan masuk tetap dan packet eksekusi agent; `docs/tasks.json` tetap backlog produk.

## Pengembangan

```bash
python3 docs/tools/check_docs.py          # validasi dokumen (kontrak)
cd backend && bash scripts/dev_bootstrap.sh   # PostgreSQL lokal + migrasi + seed
# backend:  .venv/bin/python -m pytest tests -q
# frontend: cd ../apps/web && pnpm install && pnpm exec vitest run
```

Mulai dari [panduan agent](task/0000-start-here.md) dan [indeks dokumen](docs/README.md). [MASTER_PROMPT](docs/MASTER_PROMPT.md) serta [AGENT_HANDOFF](docs/AGENT_HANDOFF.md) menautkan workflow yang sama; tidak perlu menyalin prompt panjang setiap task. Fetch main aktual dan lanjutkan packet eligible; seluruh roadmap R1–R4 tetap scope produk, sementara task aktif membatasi pekerjaan menuju Beta. Kode/tes sandbox independen tidak menunggu akses yang hanya diperlukan untuk lab.

[Kebutuhan produk](docs/PRODUCT.md) memiliki harga dan kebijakan; [arsitektur](docs/ARCHITECTURE.md) memiliki stack/API/job/data; [rencana implementasi](docs/IMPLEMENTATION_PLAN.md) mengatur urutan; [audit](docs/AUDIT_REPORT.md) menjelaskan temuan dan perlakuan seluruh 77 berkas sumber.

Nama tampilan dikendalikan [branding.json](docs/branding.json), dengan override PROJECT_NAME/APP_NAME/BRAND_NAME. Identitas internal, data, sesi dan integrasi tetap stabil ketika nama display berubah.
