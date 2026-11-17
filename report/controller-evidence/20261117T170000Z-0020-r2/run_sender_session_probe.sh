#!/usr/bin/env bash
# Own disposable runtime DB session only; never targets another environment.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE="$REPO/report/controller-evidence/20261117T170000Z-0020-r2"
WORK="${MT_REVIEW_WORK:?}"
PGROOT="${MT_REVIEW_PGROOT:?}"
PGBIN="$PGROOT/usr/lib/postgresql/17/bin"
PY="${MT_REVIEW_PY:?}"
PORT="${MT_REVIEW_PORT:-55447}"
export LD_LIBRARY_PATH="$PGROOT/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:$PORT/microtix_r2_edges"
export DATABASE_URL="$TEST_DATABASE_URL"
export MT_STORAGE_ROOT="$WORK/storage-edges"
export MT_SECRET_KEY=synthetic-controller-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-controller-box-0123456789abcdef
export PYTHONPATH="$REPO/backend"
"$PGBIN/pg_ctl" -D "$WORK/pgdata" -o "-p $PORT -h 127.0.0.1 -c unix_socket_directories=''" -l "$WORK/postgres.log" start || exit 2
trap '"$PGBIN/pg_ctl" -D "$WORK/pgdata" -m fast stop >/dev/null 2>&1' EXIT
cd "$REPO/backend" || exit 2
"$PY" -m pytest -c pytest.ini "$EVIDENCE/lifecycle/test_r2_lifecycle_edges.py::test_database_session_loss_does_not_prove_adapter_writer_stopped" -q -s --reuse-db --tb=short > "$EVIDENCE/r2-sender-session.log" 2>&1
result=$?
printf 'r2-sender-session %s\n' "$result" >> "$EVIDENCE/exit-codes.txt"
cat "$EVIDENCE/r2-sender-session.log"
exit "$result"
