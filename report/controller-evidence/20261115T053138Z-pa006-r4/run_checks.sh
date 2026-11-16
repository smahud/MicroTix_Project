#!/usr/bin/env bash
set -uo pipefail
REPO=/workspace/scratch/903b731e7b71/MicroTix_Project
EVIDENCE="$REPO/report/controller-evidence/20261115T053138Z-pa006-r4"
PY=/workspace/scratch/2c3ec21ce9a5/review-venv/bin/python
PGBIN=/tmp/mtxr4/pgbin/pg17/bin
export LD_LIBRARY_PATH=/tmp/mtxr4/pgbin/pg17/lib:/tmp/mtxr4/frdeb/extracted/usr/lib/x86_64-linux-gnu:/tmp/mtxr4/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/tmp/mtxr4/frdeb/extracted/usr/sbin/freeradius
export MT_FREERADIUS_ROOT=/tmp/mtxr4/frdeb/extracted
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55436/microtix
export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT=/tmp/mtxr4/storage-tests
[ -f /tmp/mtxr4/data/PG_VERSION ] || "$PGBIN/initdb" -D /tmp/mtxr4/data -U postgres --auth=trust -E UTF8 --locale=C > "$EVIDENCE/initdb.log" 2>&1
"$PGBIN/pg_ctl" -D /tmp/mtxr4/data -o "-p 55436 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l /tmp/mtxr4/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mtxr4/data -m fast stop >/dev/null 2>&1' EXIT
"$PGBIN/psql" -h 127.0.0.1 -p 55436 -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE mtx_app LOGIN CREATEDB NOSUPERUSER NOBYPASSRLS' > "$EVIDENCE/setup-role.log" 2>&1 || exit 2
"$PGBIN/createdb" -h 127.0.0.1 -p 55436 -U postgres -O mtx_app microtix || exit 2
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -5 "$EVIDENCE/$name.log"
}
runcheck environment "$PGBIN/psql" -h 127.0.0.1 -p 55436 -U mtx_app -d microtix -c 'SELECT version(), current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user;'
runcheck versions "$PY" -c 'import sys,django,psycopg,pytest; print(sys.version); print("Django",django.get_version()); print("psycopg",psycopg.__version__); print("pytest",pytest.__version__)'
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
runcheck targeted "$PY" -m pytest tests/integration/test_idempotency_pa006.py tests/integration/test_idempotency_pa006_r4.py tests/integration/test_idempotency_quota.py tests/integration/test_ops_platform_admin.py tests/integration/test_billing_payment_concurrency.py -q
runcheck prior-probes "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T153739Z-pa006/test_scope_review.py" "$REPO/report/controller-evidence/20261114T153739Z-pa006/test_legacy_review.py" -q -s
runcheck edges "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T212816Z-pa006/test_review_edges.py" -q -s --tb=short
runcheck effects "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T212816Z-pa006/test_review_effects.py" -q -s --tb=short
runcheck full "$PY" -m pytest tests -q
runcheck check "$PY" manage.py check
runcheck consistency "$PY" manage.py makemigrations --check --dry-run
cd "$REPO" || exit 2
runcheck docs python3 docs/tools/check_docs.py
