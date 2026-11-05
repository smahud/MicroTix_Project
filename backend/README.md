# Backend MicroTix

Backend Django 5.2 LTS + PostgreSQL 17 — modular monolith sesuai
`docs/ARCHITECTURE.md`. Status implementasi: **M0 fondasi + M1 identitas/job/subscription** (lihat `docs/progress.md` checkpoint BE-1).

## Struktur

```
backend/
  microtix/           # settings (env-driven), urls, dburl parser
  domains/
    common/           # envelope error, kursor, tenant context RLS, kripto, idempotency
    tenancy/          # Tenant, Membership, permission per peran
    identity/         # User, TOTP RFC 6238, kode pemulihan, sesi, reauth
    jobs/             # engine job (state machine §6), outbox, worker
    audit/            # audit event + redaction
    subscriptions/    # PlanVersion (harga PRODUCT.md), kuota atomik, invoice SaaS
    network/          # registri router (fondasi R1; enrollment M3)
    config/           # registri defaults.json, branding, health, enums, seed
    i18n/             # katalog pesan id/en + label enum
  adapters/routeros/  # antarmuka adapter + simulator deterministik (TK-004)
  infra/              # bootstrap SQL, Caddyfile contoh
  tests/              # unit / integration (PostgreSQL nyata) / contracts
```

## Menjalankan (dev)

```bash
# 1. PostgreSQL 17 + peran + database + migrasi + seed dua tenant
bash scripts/dev_bootstrap.sh        # atau: make bootstrap dari akar repo

# 2. API
.venv/bin/python manage.py runserver 127.0.0.1:8000

# 3. Worker job (opsional; tanpa worker, job tetap antre jujur)
.venv/bin/python manage.py runworker --loop
```

Environment (lihat `microtix/settings.py`): `MT_ENV`, `DATABASE_URL`
(peran runtime `mtx_app`), `MIGRATE_DATABASE_URL` (peran migrator `mtx_migrator`),
`MT_SECRET_KEY`, `MT_SECRET_BOX_KEY` (kunci AEAD di luar DB), `MT_STORAGE_ROOT`.

## Pengujian

```bash
.venv/bin/python -m pytest tests -q          # seluruh suite (PostgreSQL uji nyata)
.venv/bin/python -m pytest tests/unit -q     # domain murni
.venv/bin/python -m pytest tests/integration tests/contracts -q
```

`make test-radius` dan `make e2e` jujur NOT_RUN/BLOCKED — membutuhkan daemon
FreeRADIUS nyata dan harness Playwright (lihat progress.md).

## Live mode frontend

```bash
cd apps/web
MICROTIX_API=http://127.0.0.1:8000 VITE_API_MODE=live pnpm dev
```

Endpoint aktif M1: auth lengkap (login+TOTP, register, verifikasi, reauth),
tenant switch, meta/enums/branding/config, health, jobs (U16), audit timeline,
subscription/plans/quotations/payment-submissions, registri router (baca).
Endpoint fase M2+ mengembalikan 404 envelope `not_found` — tidak ada data palsu.
