#!/usr/bin/env bash
# Smoke test LIVE backend nyata (runserver + curl) — M1+M3/M4 flow.
# Dipakai progress.md sebagai bukti verifikasi lokal. Exit ≠ 0 bila ada
# asersi gagal. Menjalankan server sendiri lalu mematikannya.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
ROOT="$(cd .. && pwd)"

PY="${PY:-$ROOT/.venv/bin/python}"
BASE="${BASE:-http://127.0.0.1:8311}"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "  PASS: $*"; }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $*" >&2; }
assert_eq() { [ "$1" = "$2" ] && ok "$3 ($1)" || fail "$3: '$1' != '$2'"; }
assert_contains() { case "$2" in *"$1"*) ok "$3";; *) fail "$3: substring hilang";; esac; }

# Server uji (port khusus agar tidak bentrok dev).
MT_ENV=dev MT_SECRET_KEY=smoke-secret-key-0123456789abcdef \
MT_SECRET_BOX_KEY=smoke-secret-box-0123456789abcdef012345 \
MT_STORAGE_ROOT=/tmp/mtx-smoke-storage MT_WG_SERVER_PUBKEY=smokewgpubkey1234567890abcdef1234567890abcdef12 \
MT_ENROLL_VERIFY_SOURCE=0 MT_PUBLIC_BASE_URL=https://smoke.test MT_WG_ENDPOINT=wg.smoke.test:51820 \
PORT=8311 "$PY" "$ROOT/manage.py" runserver --noreload 127.0.0.1:8311 >/tmp/mtx-smoke-server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do curl -sf "$BASE/api/v1/health/live" >/dev/null 2>&1 && break; sleep 0.5; done
curl -sf "$BASE/api/v1/health/live" >/dev/null || { echo "server tidak siap"; exit 1; }

JAR=/tmp/mtx-smoke-cookies.txt; rm -f "$JAR"
# Seed cookie CSRF seperti SPA (GET /auth/session dulu).
curl -s -c "$JAR" "$BASE/api/v1/auth/session" >/dev/null
api() { # api METHOD path [json] — GET/PUBLIC (probe) tanpa CSRF
  local method="$1" path="$2" data="${3:-}"
  if [ -n "$data" ]; then
    curl -s -b "$JAR" -c "$JAR" -X "$method" -H 'content-type: application/json' -d "$data" "$BASE/api/v1$path"
  else
    curl -s -b "$JAR" -c "$JAR" -X "$method" "$BASE/api/v1$path"
  fi
}
csrf_header() { grep mtx_csrf "$JAR" | awk '{print $7}'; }
api_csrf() { # mutasi sesi — CSRF wajib (SessionAuthentication kami)
  local method="$1" path="$2" data="${3:-}"
  curl -s -b "$JAR" -c "$JAR" -X "$method" -H 'content-type: application/json' \
    -H "x-csrf-token: $(csrf_header)" ${data:+-d "$data"} "$BASE/api/v1$path"
}
api_idem() { # mutasi idempoten — CSRF + Idempotency-Key wajib
  local key="$1" method="$2" path="$3" data="${4:-}"
  curl -s -b "$JAR" -c "$JAR" -X "$method" -H 'content-type: application/json' \
    -H "x-csrf-token: $(csrf_header)" -H "Idempotency-Key: $key" ${data:+-d "$data"} "$BASE/api/v1$path"
}

echo "== 1. Health =="
assert_contains '"status":"live"' "$(api GET /health/live)" "health/live"
assert_contains '"status":"ready"' "$(api GET /health/ready)" "health/ready"

echo "== 2. Register + verify (konsol email dev) =="
R=$(api_csrf POST /auth/register '{"full_name":"Smoke Owner","email":"smoke@local.test","password":"password-1234567890","company_name":"Smoke Net"}')
assert_contains '"verification_sent":true' "$R" "register"

TOKEN_HASH=$(cd "$ROOT"; "$PY" - <<'PYEOF'
import os, django
os.environ.setdefault("MT_ENV","dev")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","microtix.settings")
django.setup()
from domains.identity.models import User, EmailToken
u = User.objects.get(email="smoke@local.test")
t = EmailToken.objects.filter(user=u).order_by("-created_at").first()
# token asli tidak tersimpan; keluarkan token baru via jalur dev yang sama
from domains.identity import services
fresh = services._issue_email_token(u, EmailToken.Kind.VERIFY_EMAIL)
print(fresh)
PYEOF
)
R=$(api_csrf POST /auth/verify-email "{\"token\":\"$TOKEN_HASH\"}")
assert_contains '"active_tenant_id"' "$R" "verify-email → sesi + tenant"

echo "== 3. Enrollment: create → bootstrap → probe → discovery =="
R=$(api_csrf POST /tenants/$(api GET /auth/session | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["active_tenant_id"])')/router-enrollments '{"display_name":"Smoke GW","router_code":"RT-SMOKE","location":"POP"}')
assert_contains '"state":"enrollment_issued"' "$R" "enrollment issued"
ENR_ID=$(echo "$R" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["id"])')
ENR_TOKEN=$(echo "$R" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["token"])')
TENANT=$(api GET /auth/session | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["active_tenant_id"])')

R=$(api GET "/tenants/$TENANT/router-enrollments/$ENR_ID/bootstrap?token=SALAH")
assert_contains '"code":"token_invalid"' "$R" "bootstrap token salah → 401"

R=$(api GET "/tenants/$TENANT/router-enrollments/$ENR_ID/bootstrap?token=$ENR_TOKEN")
assert_contains '"sensitive":true' "$R" "bootstrap script (sensitive)"
assert_contains 'rtrw-wg-RT-SMOKE' "$R" "bootstrap namespace rtrw-"

R=$(api POST "/router-enrollments/$ENR_ID/probe" "{\"token\":\"$ENR_TOKEN\",\"nonce\":\"smoke-nonce\",\"router_identity\":\"MikroTik-Smoke\",\"routeros_version\":\"7.15.3\",\"architecture\":\"arm64\",\"wireguard_pubkey\":\"smoke-pubkey\"}")
assert_contains '"state":"consumed"' "$R" "probe → router terdaftar (read_only)"
R=$(api POST "/router-enrollments/$ENR_ID/probe" "{\"token\":\"$ENR_TOKEN\",\"nonce\":\"smoke-nonce\",\"router_identity\":\"MikroTik-Smoke\",\"routeros_version\":\"7.15.3\",\"architecture\":\"arm64\",\"wireguard_pubkey\":\"smoke-pubkey\"}")
assert_contains '"state":"already_completed"' "$R" "probe replay = logical"

R=$(api GET /tenants/$TENANT/routers)
assert_contains 'RT-SMOKE' "$R" "router muncul di daftar"
R=$(api GET /tenants/$TENANT/radius-status)
assert_contains '"desired_revision":1' "$R" "NAS desired revision 1 (pending reconcile)"

ROUTER_ID=$(echo "$R" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)[0]["router_id"])')
R=$(api_csrf POST /tenants/$TENANT/routers/$ROUTER_ID/discoveries)
assert_contains '"job_id"' "$R" "discovery job 202"

echo "== 4. Worker: proses job discovery (simulator adapter) =="
( cd "$ROOT" && MT_ENV=dev MT_SECRET_KEY=smoke-secret-key-0123456789abcdef \
  MT_SECRET_BOX_KEY=smoke-secret-box-0123456789abcdef012345 \
  MT_STORAGE_ROOT=/tmp/mtx-smoke-storage MT_WG_SERVER_PUBKEY=x \
  MT_ROUTEROS_ADAPTER=simulator "$PY" manage.py runworker --once >/tmp/mtx-smoke-worker.log 2>&1 ) || true
R=$(api GET /tenants/$TENANT/jobs | "$PY" -c 'import json,sys; items=json.load(sys.stdin)["items"]; print(items[0]["state"] if items else "none")')
assert_eq "succeeded" "$R" "job discovery selesai (simulator, bukan klaim lab)"

echo "== 5. Services + akun akses + CSV =="
R=$(api_idem svc-smoke-1 POST /tenants/$TENANT/services '{"customer_name":"Smoke Customer","username":"smoke-001","password":"password-123","kind":"pppoe","rate_limit_rx_kbps":10000,"rate_limit_tx_kbps":50000}')
assert_contains '"state":"provisioned"' "$R" "service dibuat (kuota+proyeksi RADIUS)"
R=$(api GET "/tenants/$TENANT/access-accounts?query=smoke")
assert_contains 'smoke-001' "$R" "akun akses terlihat"

R=$(api_csrf PATCH /tenants/$TENANT/access-accounts/$(api GET "/tenants/$TENANT/access-accounts?query=smoke" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["items"][0]["id"])') '{"state":"suspended"}')
assert_contains '"state":"suspended"' "$R" "suspend akun (proyeksi Reject)"
R=$(api_csrf PATCH /tenants/$TENANT/access-accounts/$(api GET "/tenants/$TENANT/access-accounts?query=smoke" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["items"][0]["id"])') '{"state":"active"}')
assert_contains '"state":"active"' "$R" "activate akun"

R=$(api_idem csv-smoke-1 POST /tenants/$TENANT/imports '{"mode":"create","file_name":"smoke.csv","rows":[{"username":"csv-1","password":"password-c1"},{"username":"csv-2","password":"password-c2"}]}')
assert_contains '"state":"uploaded"' "$R" "impor CSV dibuat"

echo "== 6. Isolasi tenant (akun asing) =="
R=$(api GET /tenants/00000000-0000-0000-0000-0000000000aa/services)
assert_contains '"code":"not_found"' "$R" "tenant asing → 404 generik"

echo
echo "SMOKE: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ] || exit 1
