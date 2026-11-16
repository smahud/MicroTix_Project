#!/usr/bin/env bash
# All checks are local synthetic HTTP requests against real PostgreSQL.
set -uo pipefail
REPO=/workspace/scratch/903b731e7b71/MicroTix_Project
BASELINE=/workspace/scratch/903b731e7b71/mtx-baseline
EVIDENCE="$REPO/report/controller-evidence/20261115T053138Z-pa006-r4"
PY=/workspace/scratch/2c3ec21ce9a5/review-venv/bin/python
PGBIN=/tmp/mtxr4/pgbin/pg17/bin
export LD_LIBRARY_PATH=/tmp/mtxr4/pgbin/pg17/lib
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
"$PGBIN/pg_ctl" -D /tmp/mtxr4/data -o "-p 55436 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l /tmp/mtxr4/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mtxr4/data -m fast stop >/dev/null 2>&1' EXIT
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/upgrade-exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -4 "$EVIDENCE/$name.log"
}
for variant in canonical urn urn_ambiguous uuid_only uuid_only_ambiguous urn_only; do
    dbname="review_r4_$variant"
    "$PGBIN/createdb" -h 127.0.0.1 -p 55436 -U postgres -O mtx_app "$dbname" || exit 2
    export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:55436/$dbname"
    export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT="/tmp/mtxr4/storage-$variant"
    cd "$BASELINE/backend" || exit 2
    export PYTHONPATH=$PWD
    runcheck "upgrade-$variant-before-migrate" "$PY" manage.py migrate --noinput
    runcheck "upgrade-$variant-before-http" "$PY" "$EVIDENCE/live_upgrade_aliases.py" before "$variant" "/tmp/mtxr4/$variant-state.json"
    cd "$REPO/backend" || exit 2
    export PYTHONPATH=$PWD
    runcheck "upgrade-$variant-after-migrate" "$PY" manage.py migrate --noinput
    runcheck "upgrade-$variant-after-http" "$PY" "$EVIDENCE/live_upgrade_aliases.py" after "$variant" "/tmp/mtxr4/$variant-state.json"
done
runcheck rls "$PGBIN/psql" -h 127.0.0.1 -p 55436 -U mtx_app -d review_r4_canonical -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN ('subs_payment_submission','subs_saas_invoice','customers_migration_session','billing_internet_payment'); SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='uq_idem_identity';"
