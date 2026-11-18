#!/usr/bin/env bash
# Failing-before: regresi controller (terminal-lease) + tes R5 dijalankan pada
# source BASE (decision head review/0020-r4-correction-20261118-0507 = 2d5b7f1)
# via worktree — mereproduksi temuan controller sebelum perbaikan R5.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
EVIDENCE="$REPO/report/executor-evidence/20261118T113641Z-0020-r5-correction"
PGBIN="/tmp/pg17/usr/lib/postgresql/17/bin"
PY="$REPO/backend/.venv/bin/python"
DB=test_microtix_r5_base
WT=/tmp/wt-r5-base
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export MT_STORAGE_ROOT=/tmp/mtx-r5-storage
export MT_SECRET_KEY=synthetic-executor-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-executor-box-0123456789abcdef
mkdir -p "$EVIDENCE"
cd "$REPO" || exit 2
git worktree remove --force "$WT" >/dev/null 2>&1 || true
git worktree add --detach "$WT" 2d5b7f1 >/dev/null || exit 2
# Salin file tes R5 (baru) ke worktree base — tes sama, source base.
cp "$REPO/backend/tests/integration/test_jobs_r5_residuals.py" "$WT/backend/tests/integration/"

"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DB;" >/dev/null
"$PGBIN/createdb" -h 127.0.0.1 -p 55432 -U postgres -O mtx_migrator "$DB" || exit 2
cd "$WT/backend" || exit 2
env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55432/$DB "$PY" manage.py migrate --noinput > "$EVIDENCE/base-migrate.log" 2>&1 || exit 2
env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55432/$DB "$PY" manage.py grant_runtime >> "$EVIDENCE/base-migrate.log" 2>&1 || exit 2
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d "$DB" -v ON_ERROR_STOP=1 -c 'GRANT TRUNCATE ON ALL TABLES IN SCHEMA public,radius TO mtx_app;' >/dev/null

export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/$DB
export DATABASE_URL="$TEST_DATABASE_URL"
CE="$REPO/report/controller-evidence"
{
  echo "=== BASE: $(git -C "$WT" rev-parse HEAD) (decision head R4-correction) ==="
  echo "--- controller-terminal-lease (diharapkan 2 FAIL: temuan controller) ---"
  "$PY" -m pytest -c pytest.ini "$CE/20261118T050714Z-0020-r4-correction/test_terminal_lease_review.py" -q --tb=line --reuse-db 2>&1 | tail -6
  echo "--- r5-residuals pada BASE (diharapkan FAIL pada tes residual R5) ---"
  "$PY" -m pytest -c pytest.ini tests/integration/test_jobs_r5_residuals.py -q --tb=line --reuse-db 2>&1 | tail -14
} > "$EVIDENCE/failing-before-base.log" 2>&1
echo "exit=$?" >> "$EVIDENCE/failing-before-base.log"
tail -24 "$EVIDENCE/failing-before-base.log"

cd "$REPO" || exit 2
git worktree remove --force "$WT" >/dev/null 2>&1 || true
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DB;" >/dev/null
echo "SELESAI failing-before"
