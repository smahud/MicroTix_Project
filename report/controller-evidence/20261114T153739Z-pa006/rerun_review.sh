#!/usr/bin/env bash
set -uo pipefail
REPO=/workspace/scratch/6d59f64531e9/MicroTix_Project
EVIDENCE=$REPO/report/controller-evidence/20261114T153739Z-pa006
PY=$REPO/.venv-review/bin/python
PGBIN=/tmp/mt1411/pgbin/pg17/bin
export LD_LIBRARY_PATH=/tmp/mt1411/pgbin/pg17/lib:/tmp/mt1411/frdeb/extracted/usr/lib/x86_64-linux-gnu:/tmp/mt1411/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/tmp/mt1411/frdeb/extracted/usr/sbin/freeradius
export MT_FREERADIUS_ROOT=/tmp/mt1411/frdeb/extracted
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/microtix
export DATABASE_URL=$TEST_DATABASE_URL MT_STORAGE_ROOT=/tmp/mt1411/storage-tests
runcheck() {
  local name=$1
  shift
  "$@" > "$EVIDENCE/$name.log" 2>&1
  local result=$?
  printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes-corrected.txt"
  printf '%s exit=%s\n' "$name" "$result"
  tail -5 "$EVIDENCE/$name.log"
  return 0
}
"$PGBIN/pg_ctl" -D /tmp/mt1411/data -o "-p 55432 -h 127.0.0.1 -c unix_socket_directories=''" -l /tmp/mt1411/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mt1411/data -m fast stop >/dev/null 2>&1' EXIT
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
runcheck full "$PY" -m pytest tests -q
runcheck probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_scope_review.py" "$EVIDENCE/test_legacy_review.py" -q -s
runcheck rls "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d review_upgrade -c "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('subs_payment_submission','subs_saas_invoice','customers_migration_session','billing_internet_payment'); SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='uq_idem_identity';"
