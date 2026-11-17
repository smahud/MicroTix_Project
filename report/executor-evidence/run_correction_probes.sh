#!/usr/bin/env bash
# Koreksi task0020 — reproduksi probe controller pada DB split-role
# (schema milik migrator, runtime mtx_app non-superuser/NOBYPASSRLS, FORCE RLS).
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
EVIDENCE="$REPO/report/executor-evidence/20261117T150000Z-0020-correction"
PGBIN="/tmp/pgbin/pg17/usr/lib/postgresql/17/bin"
PY="$REPO/backend/.venv/bin/python"
DB=test_microtix_split_corr
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export MT_STORAGE_ROOT=/tmp/mtx-corr-storage
export MT_SECRET_KEY=synthetic-executor-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-executor-box-0123456789abcdef
mkdir -p "$EVIDENCE" "$MT_STORAGE_ROOT"
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s exit=%s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -4 "$EVIDENCE/$name.log"
}
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DB;" >/dev/null
"$PGBIN/createdb" -h 127.0.0.1 -p 55432 -U postgres -O mtx_migrator "$DB" || exit 2
cd "$REPO/backend" || exit 2
runcheck split-migrate env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55432/$DB "$PY" manage.py migrate --noinput
runcheck split-grant env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55432/$DB "$PY" manage.py grant_runtime
runcheck split-test-cleanup-grant "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d "$DB" -v ON_ERROR_STOP=1 -c 'GRANT TRUNCATE ON ALL TABLES IN SCHEMA public,radius TO mtx_app;'
runcheck split-roles-rls "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d "$DB" -c "SELECT version(),current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT n.nspname,c.relname,c.relowner::regrole,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relkind='r' AND n.nspname IN ('public','radius') ORDER BY 1,2;"
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/$DB
export DATABASE_URL="$TEST_DATABASE_URL"
runcheck lifecycle-probes-after "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T134100Z-0020-review/test_lifecycle_review.py" -q -s --reuse-db --tb=short
runcheck authority-probes-after "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T134100Z-0020-review/test_authority_review.py" -q -s --reuse-db --tb=short
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DB;" >/dev/null
