#!/usr/bin/env bash
# Controller verification; synthetic disposable PG cluster, application read-only.
set -uo pipefail
REPO=/workspace/scratch/a17cbf44829f/MicroTix_Project
EVIDENCE="$REPO/report/controller-evidence/20261116T101809Z-pa006-r5"
PY=/workspace/scratch/2c3ec21ce9a5/review-venv/bin/python
PGBIN=/tmp/mtxr5r/pgbin/pg17/bin
export LD_LIBRARY_PATH=/tmp/mtxr5r/pgbin/pg17/lib:/tmp/mtxr5r/frdeb/extracted/usr/lib/x86_64-linux-gnu:/tmp/mtxr5r/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/tmp/mtxr5r/frdeb/extracted/usr/sbin/freeradius
export MT_FREERADIUS_ROOT=/tmp/mtxr5r/frdeb/extracted
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55437/microtix
export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT=/tmp/mtxr5r/storage-tests
"$PGBIN/initdb" -D /tmp/mtxr5r/data -U postgres --auth=trust -E UTF8 --locale=C > "$EVIDENCE/initdb.log" 2>&1 || exit 2
"$PGBIN/pg_ctl" -D /tmp/mtxr5r/data -o "-p 55437 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l /tmp/mtxr5r/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mtxr5r/data -m fast stop >/dev/null 2>&1' EXIT
"$PGBIN/psql" -h 127.0.0.1 -p 55437 -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE mtx_app LOGIN CREATEDB NOSUPERUSER NOBYPASSRLS; CREATE ROLE mtx_migrator LOGIN NOSUPERUSER NOBYPASSRLS;' > "$EVIDENCE/setup-role.log" 2>&1 || exit 2
"$PGBIN/createdb" -h 127.0.0.1 -p 55437 -U postgres -O mtx_app microtix || exit 2
failed=0
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -5 "$EVIDENCE/$name.log"
    [ "$result" -eq 0 ] || failed=1
}
runcheck environment "$PGBIN/psql" -h 127.0.0.1 -p 55437 -U mtx_app -d microtix -c 'SELECT version(), current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user;'
runcheck versions "$PY" -c 'import sys,django,psycopg,pytest; print(sys.version); print("Django",django.get_version()); print("psycopg",psycopg.__version__); print("pytest",pytest.__version__)'
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
runcheck full "$PY" -m pytest tests -q --reuse-db
runcheck prior-probes "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T153739Z-pa006/test_scope_review.py" "$REPO/report/controller-evidence/20261114T153739Z-pa006/test_legacy_review.py" -q -s --reuse-db
runcheck edges "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T212816Z-pa006/test_review_edges.py" -q -s --tb=short --reuse-db
runcheck effects "$PY" -m pytest -c pytest.ini "$REPO/report/controller-evidence/20261114T212816Z-pa006/test_review_effects.py" -q -s --tb=short --reuse-db
runcheck check "$PY" manage.py check
runcheck consistency "$PY" manage.py makemigrations --check --dry-run
runcheck rls "$PGBIN/psql" -h 127.0.0.1 -p 55437 -U mtx_app -d test_microtix -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN ('subs_payment_submission','billing_payment','customers_access_account'); SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='uq_idem_identity';"
cd "$REPO" || exit 2
runcheck docs python3 docs/tools/check_docs.py
exit "$failed"
