#!/usr/bin/env bash
set -uo pipefail
REPO=$(git rev-parse --show-toplevel)
BASELINE=/workspace/scratch/2fa1f5475b19/mtx-baseline
EVIDENCE="$REPO/report/controller-evidence/20261114T212816Z-pa006"
PY=/workspace/scratch/2fa1f5475b19/review-venv/bin/python
PGBIN=/tmp/mt1511/pgbin/pg17/bin
export LD_LIBRARY_PATH=/tmp/mt1511/pgbin/pg17/lib
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
"$PGBIN/pg_ctl" -D /tmp/mt1511/data -o "-p 55432 -h 127.0.0.1 -c unix_socket_directories=''" -l /tmp/mt1511/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mt1511/data -m fast stop >/dev/null 2>&1' EXIT
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/upgrade-exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -4 "$EVIDENCE/$name.log"
}
for variant in canonical urn urn_ambiguous; do
    dbname="review_upgrade_$variant"
    "$PGBIN/createdb" -h 127.0.0.1 -p 55432 -U postgres -O mtx_app "$dbname" || exit 2
    export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:55432/$dbname"
    export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT="/tmp/mt1511/storage-$variant"
    cd "$BASELINE/backend" || exit 2
    export PYTHONPATH=$PWD
    runcheck "upgrade-$variant-before-migrate" "$PY" manage.py migrate --noinput
    runcheck "upgrade-$variant-before-http" "$PY" "$EVIDENCE/live_upgrade_edges.py" before "$variant" "/tmp/mt1511/$variant-state.json"
    cd "$REPO/backend" || exit 2
    export PYTHONPATH=$PWD
    runcheck "upgrade-$variant-after-migrate" "$PY" manage.py migrate --noinput
    runcheck "upgrade-$variant-after-http" "$PY" "$EVIDENCE/live_upgrade_edges.py" after "$variant" "/tmp/mt1511/$variant-state.json"
done
runcheck rls "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d review_upgrade_canonical -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN ('subs_payment_submission','subs_saas_invoice','customers_migration_session','billing_internet_payment'); SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='uq_idem_identity';"
