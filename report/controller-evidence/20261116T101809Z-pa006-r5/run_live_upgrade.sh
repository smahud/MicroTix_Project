#!/usr/bin/env bash
# Independent controller old-source -> real migration -> canonical HTTP replay.
set -uo pipefail
REPO=/workspace/scratch/a17cbf44829f/MicroTix_Project
OLD=/workspace/scratch/a17cbf44829f/MicroTix_baseline
EVIDENCE="$REPO/report/controller-evidence/20261116T101809Z-pa006-r5"
BASE=/tmp/mtxr5r
PGBIN="$BASE/pgbin/pg17/bin"
PY=/workspace/scratch/2c3ec21ce9a5/review-venv/bin/python
export LD_LIBRARY_PATH="$BASE/pgbin/pg17/lib"
export MT_ENV=dev DJANGO_SETTINGS_MODULE=microtix.settings
export MT_SECRET_KEY=controller-r5-synthetic-key-0123456789abcdef
export MT_SECRET_BOX_KEY=controller-r5-synthetic-box-key-0123456789abcdef
"$PGBIN/pg_ctl" -D "$BASE/data" -o "-p 55437 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l "$BASE/postgres.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$BASE/data" -m fast stop >/dev/null 2>&1' EXIT
failed=0
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/upgrade-exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -3 "$EVIDENCE/$name.log"
    [ "$result" -eq 0 ] || failed=1
}
for variant in canonical urn urn_ambiguous uuid_only uuid_only_ambiguous urn_only repeat_uuid repeat_uuid_ambiguous platform_uuid_resource platform_repeat_uuid_resource; do
    db="controller_r5_$variant"
    "$PGBIN/createdb" -h 127.0.0.1 -p 55437 -U postgres -O mtx_migrator "$db" || exit 2
    export DATABASE_URL="postgresql://mtx_app@127.0.0.1:55437/$db"
    export MIGRATE_DATABASE_URL="postgresql://mtx_migrator@127.0.0.1:55437/$db"
    export MT_STORAGE_ROOT="$BASE/storage-$variant"
    state="$BASE/$variant-state.json"
    cd "$OLD/backend" || exit 2
    export PYTHONPATH=$PWD
    runcheck "upgrade-$variant-old-migrate" env DATABASE_URL="$MIGRATE_DATABASE_URL" "$PY" manage.py migrate --noinput
    runcheck "upgrade-$variant-old-grant" env DATABASE_URL="$MIGRATE_DATABASE_URL" "$PY" manage.py grant_runtime
    runcheck "upgrade-$variant-old-http" "$PY" "$EVIDENCE/live_upgrade_probe.py" before "$variant" "$state"
    cd "$REPO/backend" || exit 2
    export PYTHONPATH=$PWD
    runcheck "upgrade-$variant-new-migrate" env DATABASE_URL="$MIGRATE_DATABASE_URL" "$PY" manage.py migrate --noinput
    runcheck "upgrade-$variant-new-grant" env DATABASE_URL="$MIGRATE_DATABASE_URL" "$PY" manage.py grant_runtime
    runcheck "upgrade-$variant-new-http" "$PY" "$EVIDENCE/live_upgrade_probe.py" after "$variant" "$state"
done
runcheck split-role-rls "$PGBIN/psql" -h 127.0.0.1 -p 55437 -U mtx_app -d controller_r5_canonical -c "SELECT current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT relname,relowner::regrole,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('subs_payment_submission','subs_saas_invoice','billing_internet_payment'); SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='uq_idem_identity';"
exit "$failed"
