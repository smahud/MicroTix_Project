#!/usr/bin/env bash
# Controller verification of PR19@9e9bf2d. Disposable local DB, synthetic data.
set -uo pipefail
REPO=$(git rev-parse --show-toplevel)
EVIDENCE="$REPO/report/controller-evidence/20261114T212816Z-pa006"
PY=/workspace/scratch/2fa1f5475b19/review-venv/bin/python
PGBIN=/tmp/mt1511/pgbin/pg17/bin
export MT_PG_BIN=/tmp/mt1511/pgbin/pg17
export LD_LIBRARY_PATH=/tmp/mt1511/pgbin/pg17/lib:/tmp/mt1511/frdeb/extracted/usr/lib/x86_64-linux-gnu:/tmp/mt1511/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/tmp/mt1511/frdeb/extracted/usr/sbin/freeradius
export MT_FREERADIUS_ROOT=/tmp/mt1511/frdeb/extracted
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/microtix
export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT=/tmp/mt1511/storage-tests
"$PGBIN/pg_ctl" -D /tmp/mt1511/data -o "-p 55432 -h 127.0.0.1 -c unix_socket_directories=''" -l /tmp/mt1511/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mt1511/data -m fast stop >/dev/null 2>&1' EXIT
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -4 "$EVIDENCE/$name.log"
}
runcheck environment "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d microtix -c 'SELECT version(), current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user;'
runcheck versions "$PY" -c 'import sys,django,psycopg; print(sys.version); print("Django",django.get_version()); print("psycopg",psycopg.__version__)'
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
runcheck targeted "$PY" -m pytest tests/integration/test_idempotency_pa006.py tests/integration/test_idempotency_quota.py tests/integration/test_ops_platform_admin.py tests/integration/test_billing_payment_concurrency.py -q
runcheck full "$PY" -m pytest tests -q
runcheck prior-probes "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T153739Z-pa006/test_scope_review.py" "$REPO/report/controller-evidence/20261114T153739Z-pa006/test_legacy_review.py" -q -s
runcheck check "$PY" manage.py check
runcheck consistency "$PY" manage.py makemigrations --check --dry-run
runcheck new-probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_review_edges.py" -q -s --tb=short
cd "$REPO" || exit 2
runcheck docs python3 docs/tools/check_docs.py
