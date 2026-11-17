#!/usr/bin/env bash
# Executor R2 correction — verifikasi probe controller TIDAK DIUBAH (frozen).
# Cluster PG17 disposable terpisah (port 55447); log ditulis ke direktori
# evidence sesi ini — bukan menimpa evidence controller (frozen).
# Lingkungan mengikuti run_edge_probes.sh/run_review.sh controller R2.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE="$(cd "$(dirname "$0")" && pwd)"
WORK="${MT_REVIEW_WORK:?set a new disposable runtime directory}"
PGROOT="${MT_REVIEW_PGROOT:?set extracted PostgreSQL17 package root}"
PGBIN="$PGROOT/usr/lib/postgresql/17/bin"
PY="${MT_REVIEW_PY:?set Python3.13 interpreter with pinned dependencies}"
PORT="${MT_REVIEW_PORT:-55447}"
R2EV="$REPO/report/controller-evidence/20261117T170000Z-0020-r2"
R1EV="$REPO/report/controller-evidence/20261117T134100Z-0020-review"
export LD_LIBRARY_PATH="$PGROOT/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:$PORT/microtix_r2_edges"
export DATABASE_URL="$TEST_DATABASE_URL"
export MT_STORAGE_ROOT="$WORK/storage-edges"
export MT_SECRET_KEY=synthetic-controller-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-controller-box-0123456789abcdef
export PYTHONPATH="$REPO/backend"
mkdir -p "$WORK" "$MT_STORAGE_ROOT"
if [ ! -f "$WORK/pgdata/PG_VERSION" ]; then
    "$PGBIN/initdb" -D "$WORK/pgdata" -U postgres -A trust > "$EVIDENCE/initdb.log" 2>&1 || exit 2
fi
"$PGBIN/pg_ctl" -D "$WORK/pgdata" -o "-p $PORT -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l "$WORK/postgres.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$WORK/pgdata" -m fast stop >/dev/null 2>&1' EXIT
overall=0
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    if [ "$result" -ne 0 ]; then overall=1; fi
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -14 "$EVIDENCE/$name.log"
}
"$PGBIN/psql" -h 127.0.0.1 -p $PORT -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DO \$\$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_app') THEN
        CREATE ROLE mtx_app LOGIN CREATEDB NOSUPERUSER NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_migrator') THEN
        CREATE ROLE mtx_migrator LOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
END \$\$;" > "$EVIDENCE/create-roles.log" 2>&1 || exit 2
"$PGBIN/dropdb" --if-exists -h 127.0.0.1 -p $PORT -U postgres microtix_r2_edges >/dev/null 2>&1 || true
"$PGBIN/dropdb" --if-exists -h 127.0.0.1 -p $PORT -U postgres test_microtix_r2_edges >/dev/null 2>&1 || true
"$PGBIN/createdb" -h 127.0.0.1 -p $PORT -U postgres -O mtx_migrator microtix_r2_edges || exit 2
"$PGBIN/createdb" -h 127.0.0.1 -p $PORT -U postgres -O mtx_migrator test_microtix_r2_edges || exit 2
cd "$REPO/backend" || exit 2
runcheck environment "$PY" -c 'import sys,django,pytest,psycopg,platform; print(platform.platform()); print(sys.version); print("Django",django.get_version(),"pytest",pytest.__version__,"psycopg",psycopg.__version__)'
runcheck edges-migrate env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL="postgresql://mtx_migrator@127.0.0.1:$PORT/test_microtix_r2_edges" "$PY" manage.py migrate --noinput
runcheck edges-grant env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL="postgresql://mtx_migrator@127.0.0.1:$PORT/test_microtix_r2_edges" "$PY" manage.py grant_runtime
runcheck edges-test-cleanup-grant "$PGBIN/psql" -h 127.0.0.1 -p $PORT -U postgres -d test_microtix_r2_edges -v ON_ERROR_STOP=1 -c 'GRANT TRUNCATE ON ALL TABLES IN SCHEMA public,radius TO mtx_app;'
runcheck edges-roles-rls "$PGBIN/psql" -h 127.0.0.1 -p $PORT -U mtx_app -d test_microtix_r2_edges -c "SELECT version(),current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT n.nspname,c.relname,c.relowner::regrole,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relkind='r' AND n.nspname IN ('public','radius') ORDER BY 1,2;"
# --- Probe R2 (6 assertion gagal di R2; file FROZEN milik controller) ---
runcheck r2-lifecycle "$PY" -m pytest -c pytest.ini "$R2EV/lifecycle/test_r2_lifecycle_edges.py" -q -s --reuse-db --tb=short
runcheck r2-authority "$PY" -m pytest -c pytest.ini "$R2EV/authority/test_authority_r2.py" -q -s --reuse-db --tb=short
runcheck r2-sender-session "$PY" -m pytest -c pytest.ini "$R2EV/lifecycle/test_r2_lifecycle_edges.py::test_database_session_loss_does_not_prove_adapter_writer_stopped" -q -s --reuse-db --tb=short
# --- Probe R1 lama (11; harus tetap lulus, tanpa pelemahan) ---
runcheck r1-lifecycle "$PY" -m pytest -c pytest.ini "$R1EV/test_lifecycle_review.py" -q -s --reuse-db --tb=short
runcheck r1-authority "$PY" -m pytest -c pytest.ini "$R1EV/test_authority_review.py" -q -s --reuse-db --tb=short
exit "$overall"
