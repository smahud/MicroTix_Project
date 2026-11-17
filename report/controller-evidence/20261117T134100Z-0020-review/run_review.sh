#!/usr/bin/env bash
# Controller review of exact PR27 bd37c14; application source remains read-only.
# Run PG and clients in this one process namespace. User-local PG17 packages
# are extracted, never installed as a host service. Synthetic trust-auth DB.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
WORK="$(dirname "$REPO")"
EVIDENCE="$REPO/report/controller-evidence/20261117T134100Z-0020-review"
PGBIN="${MT_REVIEW_PGBIN:-$WORK/pg17root/usr/lib/postgresql/17/bin}"
PY="${MT_REVIEW_PY:-$REPO/.venv/bin/python}"
export LD_LIBRARY_PATH="$WORK/pg17root/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55439/microtix
export DATABASE_URL="$TEST_DATABASE_URL"
export MT_STORAGE_ROOT="$WORK/storage-tests"
export MT_SECRET_KEY=synthetic-controller-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-controller-box-0123456789abcdef
"$PGBIN/pg_ctl" -D "$WORK/pg17data" -o "-p 55439 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l "$WORK/pg17.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$WORK/pg17data" -m fast stop >/dev/null 2>&1' EXIT
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -8 "$EVIDENCE/$name.log"
}
cd "$REPO/backend" || exit 2
export PYTHONPATH="$REPO/backend"
runcheck full-suite "$PY" -m pytest tests -q --reuse-db
runcheck lifecycle-probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_lifecycle_review.py" -q -s --reuse-db --tb=short
runcheck authority-probes "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_authority_review.py" -q -s --reuse-db --tb=short
runcheck check "$PY" manage.py check
runcheck makemigrations "$PY" manage.py makemigrations --check --dry-run
runcheck rls "$PGBIN/psql" -h 127.0.0.1 -p 55439 -U mtx_app -d test_microtix -c "SELECT current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT relname,relowner::regrole,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('jobs_jobdetail','customers_discoveryobject','network_discoveryobject','network_discoverysnapshot','backups_backupartifact');"
cd "$REPO" || exit 2
runcheck source-authority "$PY" "$EVIDENCE/source_authority_probe.py"
runcheck docs python3 docs/tools/check_docs.py
# The probe exit codes intentionally remain nonzero when acceptance is violated.
# This runner completes all evidence collection; consult exit-codes.txt.
