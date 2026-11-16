#!/usr/bin/env bash
set -uo pipefail
REPO=/workspace/scratch/6d59f64531e9/MicroTix_Project
BASELINE=/workspace/scratch/6d59f64531e9/mtx-baseline
EVIDENCE=$REPO/report/controller-evidence/20261114T153739Z-pa006
PY=$REPO/.venv-review/bin/python
PGBIN=/tmp/mt1411/pgbin/pg17/bin
export LD_LIBRARY_PATH=/tmp/mt1411/pgbin/pg17/lib:/tmp/mt1411/frdeb/extracted/usr/lib/x86_64-linux-gnu:/tmp/mt1411/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/tmp/mt1411/frdeb/extracted/usr/sbin/freeradius
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/microtix
export DATABASE_URL=$TEST_DATABASE_URL
export MT_STORAGE_ROOT=/tmp/mt1411/storage-tests
mkdir -p "$EVIDENCE"
runcheck() {
  local name=$1
  shift
  "$@" > "$EVIDENCE/$name.log" 2>&1
  local result=$?
  printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
  printf '%s exit=%s\n' "$name" "$result"
  tail -5 "$EVIDENCE/$name.log"
  return 0
}
"$PGBIN/initdb" -D /tmp/mt1411/data -U postgres --auth=trust -E UTF8 --locale=C > /tmp/mt1411/initdb.log 2>&1 || exit 2
"$PGBIN/pg_ctl" -D /tmp/mt1411/data -o "-p 55432 -h 127.0.0.1 -c unix_socket_directories=''" -l /tmp/mt1411/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mt1411/data -m fast stop >/dev/null 2>&1' EXIT
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE mtx_app LOGIN CREATEDB NOSUPERUSER NOBYPASSRLS;'
"$PGBIN/createdb" -h 127.0.0.1 -p 55432 -U postgres -O mtx_app microtix
"$PGBIN/createdb" -h 127.0.0.1 -p 55432 -U postgres -O mtx_app review_upgrade
runcheck environment "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d microtix -c 'SELECT version(), current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user;'
runcheck versions "$PY" -c 'import sys,django,psycopg; print(sys.version);print("Django",django.get_version());print("psycopg",psycopg.__version__)'
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
runcheck targeted "$PY" -m pytest tests/integration/test_idempotency_pa006.py tests/integration/test_idempotency_quota.py tests/integration/test_ops_platform_admin.py tests/integration/test_billing_payment_concurrency.py -q
runcheck full "$PY" -m pytest tests -q
runcheck probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_scope_review.py" "$EVIDENCE/test_legacy_review.py" -q -s
runcheck check "$PY" manage.py check
runcheck consistency "$PY" manage.py makemigrations --check --dry-run
# Real schema/source transition: original main code then reviewed code; same DB,
# retained key, owner, invoice and storage. No installer/host rehearsal claim.
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/review_upgrade
export DATABASE_URL=$TEST_DATABASE_URL
export MT_STORAGE_ROOT=/tmp/mt1411/storage-upgrade
cd "$BASELINE/backend" || exit 2
export PYTHONPATH=$PWD
runcheck upgrade-before-migrate "$PY" manage.py migrate --noinput
runcheck upgrade-before-http "$PY" "$EVIDENCE/live_upgrade_probe.py" before /tmp/mt1411/upgrade-state.json
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
runcheck upgrade-after-migrate "$PY" manage.py migrate --noinput
runcheck upgrade-after-http "$PY" "$EVIDENCE/live_upgrade_probe.py" after /tmp/mt1411/upgrade-state.json
runcheck rls "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d review_upgrade -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN ('subscriptions_paymentsubmission','subscriptions_payment_submission','customers_migration_session','billing_internet_payment'); SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='uq_idem_identity';"
cd "$REPO" || exit 2
runcheck docs python3 docs/tools/check_docs.py
