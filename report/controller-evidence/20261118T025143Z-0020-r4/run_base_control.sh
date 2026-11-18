#!/usr/bin/env bash
# Requires this review's isolated cluster and split-role test DB from run_review.sh.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE="$REPO/report/controller-evidence/20261118T025143Z-0020-r4"
WORK="${MT_REVIEW_WORK:?set disposable review runtime directory}"
PY="${MT_REVIEW_PY:?set Python3.13 with pinned dependencies}"
PORT="${MT_REVIEW_PORT:-55518}"
PGROOT="${MT_REVIEW_PGROOT:?set extracted PostgreSQL17 package root}"
PGBIN="$PGROOT/usr/lib/postgresql/17/bin"
export LD_LIBRARY_PATH="$PGROOT/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
"$PGBIN/pg_ctl" -D "$WORK/pgdata" -o "-p $PORT -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l "$WORK/postgres.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$WORK/pgdata" -m fast stop > "$EVIDENCE/base-cleanup.log" 2>&1' EXIT
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:$PORT/microtix_r4_probes"
export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT="$WORK/storage"
export MT_SECRET_KEY=synthetic-controller-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-controller-box-0123456789abcdef
BASE="${MT_REVIEW_BASE:?set clean detached4b03efe worktree}"
export PYTHONPATH="$BASE/backend"
cd "$BASE/backend" || exit 2
overall=0
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    if [ "$result" -ne 0 ]; then overall=1; fi
    printf '%s %s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -12 "$EVIDENCE/$name.log"
}
runcheck base-no-effect-control "$PY" -m pytest -c pytest.ini "$EVIDENCE/test_r4_lifecycle_edges.py::test_proven_no_effect_at_max_attempts_reaches_terminal_failure" -q -s --reuse-db --tb=short
exit "$overall"
