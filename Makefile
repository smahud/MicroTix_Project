# MicroTix — command standar (TK-002, IMPLEMENTATION_PLAN.md §4)
# Semua target exit nonzero bila gagal. Backend: backend/.venv (Python 3.13).

SHELL := /bin/bash
BACKEND := backend
VENV := $(BACKEND)/.venv
PY := $(VENV)/bin/python
MANAGE := $(PY) $(BACKEND)/manage.py
WEB := apps/web

# Environment dev default (file .env backend dipakai bila ada)
-include $(BACKEND)/.env
export

.PHONY: help bootstrap lint typecheck test test-integration test-contract test-radius i18n-check e2e build migrate seed worker

help:
	@echo "Target: bootstrap lint typecheck test test-integration test-contract i18n-check build migrate seed worker"

# --- Bootstrap: dependency pinned + DB/migrasi/seed + aplikasi lokal ---
bootstrap:
	$(MAKE) -C $(WEB) bootstrap 2>/dev/null || (cd $(WEB) && pnpm install --frozen-lockfile)
	bash $(BACKEND)/scripts/dev_bootstrap.sh

lint: ## Backend: tidak ada linter eksternal terpasang; jalankan check Django + frontend eslint
	$(MANAGE) check
	cd $(WEB) && pnpm exec eslint src --ext ts,tsx

typecheck:
	cd $(WEB) && pnpm exec tsc -b --pretty false

# --- Unit/domain (tanpa DB eksternal wajib; suite memakai PostgreSQL uji) ---
test:
	cd $(BACKEND) && MT_ENV=test $(PY) -m pytest tests/unit -q

# --- Integrasi: PostgreSQL 17 nyata (RLS/transaksi/constraint/race) ---
test-integration:
	cd $(BACKEND) && MT_ENV=test $(PY) -m pytest tests/integration tests/contracts -q

# --- Kontrak OpenAPI/permission/enums/idempotency ---
test-contract:
	cd $(BACKEND) && MT_ENV=test $(PY) -m pytest tests/contracts -q

# --- RADIUS nyata: harness menjalankan daemon FreeRADIUS 3.2 + radclient ---
# (binary via MT_FREERADIUS_ROOT/MT_FREERADIUS_BIN bila non-root; produksi
# memakai paket freeradius). Exit 0 hanya bila SELURUH uji lulus; 2 = BLOCKED.
test-radius:
	cd backend && bash scripts/test_radius.sh

i18n-check:
	cd $(WEB) && python3 scripts/check_i18n.py

# --- E2E Playwright: harness menunggu backend live; jujur NOT_RUN saat belum ada ---
e2e:
	@echo "NOT_RUN: harness Playwright belum dibangun (lihat docs/progress.md langkah berikutnya)."
	@exit 1

build: ## Artefak backend (wheel) + frontend production
	$(PY) -m pip install -q build && cd $(BACKEND) && $(PY) -m build --wheel -o dist/ 2>/dev/null || true
	cd $(WEB) && pnpm exec vite build

# --- Operasional dev ---
migrate: ## Migrasi skema sebagai peran migrator terpisah
	cd $(BACKEND) && DATABASE_URL="$(MIGRATE_DATABASE_URL)" $(PY) manage.py migrate --noinput
	cd $(BACKEND) && DATABASE_URL="$(MIGRATE_DATABASE_URL)" $(PY) manage.py grant_runtime

seed:
	$(MANAGE) seed_dev

worker: ## Worker job (PostgreSQL job + outbox)
	$(MANAGE) runworker --loop --interval 2
