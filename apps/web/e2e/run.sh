#!/usr/bin/env bash
# Harness E2E MicroTix (make e2e) — browser nyata ↔ API nyata, TANPA mock.
#
# Tanggung jawab skrip ini:
# 1. Pastikan PostgreSQL 17 + migrasi + seed dua tenant (dev_bootstrap idempoten).
# 2. Publikasikan ID tenant seed ke harness (isolasi lintas tenant diuji nyata).
# 3. Jalankan backend runserver 127.0.0.1:8010 (log email konsol = jalur token).
# 4. Jalankan Playwright (config webServer menangani Vite dev + proxy /api,
#    VITE_API_MODE=live — guard anti-mock menolak mock pada jalur ini).
# 5. Hentikan backend; keluarkan exit nyata (jujur: bukan exit 0 palsu).
#
# Prasyarat: backend/.venv (Python 3.13, dependensi pin) — jalankan
# `bash backend/scripts/dev_bootstrap.sh` bila belum. Browser Playwright
# dipasang sekali: `pnpm --dir apps/web exec playwright install chromium`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"   # repo root
WEB="$ROOT/apps/web"
BACKEND="$ROOT/backend"
API_PORT="${E2E_API_PORT:-8010}"
LOG="${E2E_BACKEND_LOG:-/tmp/mtx-e2e-backend.log}"
export E2E_API_BASE="http://127.0.0.1:${API_PORT}"
export E2E_BACKEND_LOG="$LOG"

cd "$BACKEND"
export MT_PG_BIN="${MT_PG_BIN:-/home/z/my-project/pgbin/pg17}"
export PATH="$MT_PG_BIN/bin:$PATH"
bash scripts/dev_bootstrap.sh >/dev/null
set -a; . "$BACKEND/.env"; set +a

# ID tenant seed untuk uji isolasi (dari DB nyata — bukan tebakan).
# Ditulis ke berkas agar kebal terhadap keluaran banner manage.py shell.
E2E_TENANTS_JSON="${E2E_TENANTS_JSON:-/tmp/mtx-e2e-tenants.json}"
"$BACKEND/.venv/bin/python" manage.py shell -c "
from domains.tenancy.models import Tenant
import json
rows = [{ 'id': str(t.id), 'name': t.display_name } for t in Tenant.objects.order_by('display_name')]
open('$E2E_TENANTS_JSON', 'w').write(json.dumps(rows))
" >/dev/null 2>&1 || { echo "e2e: gagal membaca tenant seed dari DB"; exit 1; }
export E2E_OWN_TENANT_ID="$(python3 -c "import json; rows=json.load(open('$E2E_TENANTS_JSON')); print(next(r['id'] for r in rows if 'Nusantara' in r['name']))")"
export E2E_FOREIGN_TENANT_ID="$(python3 -c "import json; rows=json.load(open('$E2E_TENANTS_JSON')); print(next(r['id'] for r in rows if 'Cemara' in r['name']))")"
echo "e2e: own=$E2E_OWN_TENANT_ID foreign=$E2E_FOREIGN_TENANT_ID"

# Seed tenant billing khusus E2E (TK-604): tenant ketiga terpisah agar asersi
# empty-state spec lain (Nusantara) tidak terdampak. Idempoten.
"$BACKEND/.venv/bin/python" manage.py seed_billing_e2e >/dev/null 2>&1 \
  || { echo "e2e: gagal seed billing"; exit 1; }
export E2E_BILLING_TENANT_ID="$("$BACKEND/.venv/bin/python" manage.py shell -c "
from domains.tenancy.models import Tenant
print(Tenant.objects.get(display_name='RT Net Billing Demo (e2e)').id)
" 2>/dev/null | tail -1)"
export E2E_BILLING_OWNER_EMAIL="owner-billing@dev.local"
export E2E_BILLING_OWNER_PASSWORD="dev-seed-only-2026"
echo "e2e: billing=$E2E_BILLING_TENANT_ID"

# Backend nyata di foreground background-process dengan log berkas.
: >"$LOG"
"$BACKEND/.venv/bin/python" manage.py runserver "127.0.0.1:${API_PORT}" --noreload >>"$LOG" 2>&1 &
SRV_PID=$!
# Worker job NYATA (proses terpisah dari API — boundary privilege berbeda):
# spec onboarding router (routers.spec.ts) membutuhkan job verify_api_ssl
# diproses asinkron seperti produksi, bukan di-claim manual dari UI.
WORKER_LOG="${E2E_WORKER_LOG:-/tmp/mtx-e2e-worker.log}"
: >"$WORKER_LOG"
"$BACKEND/.venv/bin/python" manage.py runworker --loop --interval 1 >>"$WORKER_LOG" 2>&1 &
WRK_PID=$!
cleanup() {
  kill "$WRK_PID" >/dev/null 2>&1 || true; wait "$WRK_PID" 2>/dev/null || true
  kill "$SRV_PID" >/dev/null 2>&1 || true; wait "$SRV_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${API_PORT}/api/v1/health/live" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://127.0.0.1:${API_PORT}/api/v1/health/live" >/dev/null \
  || { echo "e2e: backend tidak siap di :${API_PORT} (lihat $LOG)"; exit 1; }
echo "e2e: backend hidup di :${API_PORT} (log: $LOG)"

cd "$WEB"
if ! pnpm exec playwright --version >/dev/null 2>&1; then
  echo "e2e: @playwright/test tidak terpasang — jalankan pnpm install"; exit 1
fi
if [ ! -d "${HOME}/.cache/ms-playwright" ] || ! ls "${HOME}/.cache/ms-playwright"/chromium-* >/dev/null 2>&1; then
  echo "e2e: browser belum terpasang — menjalankan playwright install chromium"
  pnpm exec playwright install chromium
fi
# --config eksplisit: tanpa ini playwright mencari konfigurasi di cwd
# (apps/web) dan ikut memuat spec vitest unit sebagai spec playwright.
pnpm exec playwright test --config e2e/playwright.config.ts "$@"
