#!/usr/bin/env bash
# Disposable PG17 review harness; no host services or production targets.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE="$REPO/report/controller-evidence/20261118T025143Z-0020-r4"
WORK="${MT_REVIEW_WORK:?set a new disposable runtime directory}"
PGROOT="${MT_REVIEW_PGROOT:?set extracted PostgreSQL17 package root}"
PGBIN="$PGROOT/usr/lib/postgresql/17/bin"
PY="${MT_REVIEW_PY:?set Python3.13 interpreter with pinned dependencies}"
PORT="${MT_REVIEW_PORT:-55518}"
export LD_LIBRARY_PATH="$PGROOT/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:$PORT/microtix_r4"
export DATABASE_URL="$TEST_DATABASE_URL"
export MT_STORAGE_ROOT="$WORK/storage"
export MT_SECRET_KEY=synthetic-controller-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-controller-box-0123456789abcdef
export PYTHONPATH="$REPO/backend"
mkdir -p "$WORK" "$MT_STORAGE_ROOT"
if [ ! -f "$WORK/pgdata/PG_VERSION" ]; then
    "$PGBIN/initdb" -D "$WORK/pgdata" -U postgres -A trust > "$EVIDENCE/initdb.log" 2>&1 || exit 2
fi
"$PGBIN/pg_ctl" -D "$WORK/pgdata" -o "-p $PORT -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l "$WORK/postgres.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$WORK/pgdata" -m fast stop > "$EVIDENCE/review-cleanup.log" 2>&1' EXIT
# Supplemental runners restart this disposable cluster in their own command session.
overall=0
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    if [ "$result" -ne 0 ]; then overall=1; fi
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -6 "$EVIDENCE/$name.log"
}
"$PGBIN/psql" -h 127.0.0.1 -p "$PORT" -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE mtx_app LOGIN CREATEDB NOSUPERUSER NOBYPASSRLS; CREATE ROLE mtx_migrator LOGIN NOSUPERUSER NOBYPASSRLS;' > "$EVIDENCE/create-roles.log" 2>&1 || exit 2
"$PGBIN/createdb" -h 127.0.0.1 -p "$PORT" -U postgres -O mtx_migrator microtix_r4 || exit 2
cd "$REPO/backend" || exit 2
runcheck environment "$PY" -c 'import sys,django,pytest,psycopg,platform; print(platform.platform()); print(sys.version); print("Django",django.get_version(),"pytest",pytest.__version__,"psycopg",psycopg.__version__)'
runcheck check "$PY" manage.py check
runcheck makemigrations "$PY" manage.py makemigrations --check --dry-run
runcheck full-suite "$PY" -m pytest tests -q --tb=short
export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:$PORT/microtix_r4_probes"
export DATABASE_URL="$TEST_DATABASE_URL"
"$PGBIN/createdb" -h 127.0.0.1 -p "$PORT" -U postgres -O mtx_migrator microtix_r4_probes || exit 2
"$PGBIN/createdb" -h 127.0.0.1 -p "$PORT" -U postgres -O mtx_migrator test_microtix_r4_probes || exit 2
runcheck split-migrate env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL="postgresql://mtx_migrator@127.0.0.1:$PORT/test_microtix_r4_probes" "$PY" manage.py migrate --noinput
runcheck split-grant env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL="postgresql://mtx_migrator@127.0.0.1:$PORT/test_microtix_r4_probes" "$PY" manage.py grant_runtime
runcheck split-test-cleanup-grant "$PGBIN/psql" -h 127.0.0.1 -p "$PORT" -U postgres -d test_microtix_r4_probes -v ON_ERROR_STOP=1 -c 'GRANT TRUNCATE ON ALL TABLES IN SCHEMA public,radius TO mtx_app;'
runcheck split-roles-rls "$PGBIN/psql" -h 127.0.0.1 -p "$PORT" -U mtx_app -d test_microtix_r4_probes -c "SELECT version(),current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT n.nspname,c.relname,c.relowner::regrole,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relkind='r' AND n.nspname IN ('public','radius') ORDER BY 1,2;"
runcheck r3-lifecycle "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T212042Z-0020-r3/test_r3_lifecycle_edges.py" -q -s --reuse-db --tb=short
runcheck r3-authority "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T212042Z-0020-r3/test_r3_authority.py" -q -s --reuse-db --tb=short
runcheck r2-lifecycle "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T170000Z-0020-r2/lifecycle/test_r2_lifecycle_edges.py" -q -s --reuse-db --tb=short
runcheck r2-authority "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T170000Z-0020-r2/authority/test_authority_r2.py" -q -s --reuse-db --tb=short
runcheck r1-lifecycle "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T134100Z-0020-review/test_lifecycle_review.py" -q -s --reuse-db --tb=short
runcheck r1-authority "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261117T134100Z-0020-review/test_authority_review.py" -q -s --reuse-db --tb=short
cd "$REPO" || exit 2
runcheck docs "$PY" docs/tools/check_docs.py

exit "$overall"
