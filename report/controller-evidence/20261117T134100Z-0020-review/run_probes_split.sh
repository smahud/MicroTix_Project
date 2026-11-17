#!/usr/bin/env bash
# Corrected focused harness: real PG17, migrator-owned schema + runtime DML.
# Extra TRUNCATE privilege exists only for disposable pytest cleanup.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
WORK="$(dirname "$REPO")"
EVIDENCE="$REPO/report/controller-evidence/20261117T134100Z-0020-review"
PGBIN="$WORK/pg17root/usr/lib/postgresql/17/bin"
PY="$REPO/.venv/bin/python"
export LD_LIBRARY_PATH="$WORK/pg17root/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55439/microtix_review
export DATABASE_URL="$TEST_DATABASE_URL"
export MT_STORAGE_ROOT="$WORK/storage-probes-split"
export MT_SECRET_KEY=synthetic-controller-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-controller-box-0123456789abcdef
"$PGBIN/pg_ctl" -D "$WORK/pg17data" -o "-p 55439 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l "$WORK/pg17.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$WORK/pg17data" -m fast stop >/dev/null 2>&1' EXIT
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -8 "$EVIDENCE/$name.log"
}
"$PGBIN/createdb" -h 127.0.0.1 -p 55439 -U postgres -O mtx_migrator microtix_review || exit 2
"$PGBIN/createdb" -h 127.0.0.1 -p 55439 -U postgres -O mtx_migrator test_microtix_review || exit 2
cd "$REPO/backend" || exit 2
export PYTHONPATH="$REPO/backend"
runcheck split-migrate env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55439/test_microtix_review "$PY" manage.py migrate --noinput
runcheck split-grant env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55439/test_microtix_review "$PY" manage.py grant_runtime
runcheck split-test-cleanup-grant "$PGBIN/psql" -h 127.0.0.1 -p 55439 -U postgres -d test_microtix_review -v ON_ERROR_STOP=1 -c 'GRANT TRUNCATE ON ALL TABLES IN SCHEMA public,radius TO mtx_app;'
runcheck split-roles-rls "$PGBIN/psql" -h 127.0.0.1 -p 55439 -U mtx_app -d test_microtix_review -c "SELECT version(),current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT n.nspname,c.relname,c.relowner::regrole,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relkind='r' AND n.nspname IN ('public','radius') ORDER BY 1,2;"
runcheck lifecycle-probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_lifecycle_review.py" -q -s --reuse-db --tb=short
runcheck authority-probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_authority_review.py" -q -s --reuse-db --tb=short
# Nonzero acceptance probe exits are the observed candidate defects.
