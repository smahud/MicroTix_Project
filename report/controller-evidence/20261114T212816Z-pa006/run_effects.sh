#!/usr/bin/env bash
# Supplementary controller probes. PostgreSQL must capture the full SELECT
# for platform proof/invoice joins; default track_activity_query_size=1024
# truncates before FOR UPDATE and is insufficient for query attribution.
set -uo pipefail
REPO=$(git rev-parse --show-toplevel)
EVIDENCE="$REPO/report/controller-evidence/20261114T212816Z-pa006"
PGBIN=/tmp/mt1511/pgbin/pg17/bin
PY=/workspace/scratch/2fa1f5475b19/review-venv/bin/python
export LD_LIBRARY_PATH=/tmp/mt1511/pgbin/pg17/lib
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/microtix
export DATABASE_URL="$TEST_DATABASE_URL" MT_STORAGE_ROOT=/tmp/mt1511/storage-effects
"$PGBIN/pg_ctl" -D /tmp/mt1511/data -o "-p 55432 -h 127.0.0.1 -c unix_socket_directories='' -c track_activity_query_size=8192" -l /tmp/mt1511/postgres.log start || exit 2
trap '"$PGBIN/pg_ctl" -D /tmp/mt1511/data -m fast stop >/dev/null 2>&1' EXIT
cd "$REPO/backend" || exit 2
export PYTHONPATH=$PWD
"$PY" -m pytest -c pytest.ini "$EVIDENCE/test_review_effects.py" -k 'platform_decision or leader_rollback' -q -s --tb=short > "$EVIDENCE/lock-attribution-corrected.log" 2>&1
result=$?
printf 'lock-attribution-corrected %s\n' "$result" >> "$EVIDENCE/exit-codes.txt"
tail -9 "$EVIDENCE/lock-attribution-corrected.log"
exit "$result"
