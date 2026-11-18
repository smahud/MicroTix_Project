#!/usr/bin/env bash
# Koreksi R5 task0020 — seluruh probe beku R1-R4 + regresi controller + tes R5
# pada DB split-role (schema milik migrator, runtime mtx_app
# non-superuser/NOBYPASSRLS, FORCE RLS) — pola runner koreksi sebelumnya.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
EVIDENCE="$REPO/report/executor-evidence/20261118T113641Z-0020-r5-correction"
PGBIN="/tmp/pg17/usr/lib/postgresql/17/bin"
PY="$REPO/backend/.venv/bin/python"
DB=test_microtix_split_r5
export MT_ENV=test DJANGO_SETTINGS_MODULE=microtix.settings_test
export MT_STORAGE_ROOT=/tmp/mtx-r5-storage
export MT_SECRET_KEY=synthetic-executor-key-0123456789abcdef
export MT_SECRET_BOX_KEY=synthetic-executor-box-0123456789abcdef
mkdir -p "$EVIDENCE" "$MT_STORAGE_ROOT"
runcheck() {
    local name=$1
    shift
    "$@" > "$EVIDENCE/$name.log" 2>&1
    local result=$?
    printf '%s exit=%s\n' "$name" "$result" >> "$EVIDENCE/exit-codes.txt"
    printf '%s exit=%s\n' "$name" "$result"
    tail -3 "$EVIDENCE/$name.log"
}

# --- Environment record ---
{
  uname -a
  "$PY" --version
  "$PY" -c "import django,psycopg,pytest;print('Django',django.get_version(),'pytest',pytest.__version__,'psycopg',psycopg.__version__)"
  "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -tAc "SELECT version();"
} > "$EVIDENCE/environment.log" 2>&1

# --- Split-role DB: schema milik migrator, runtime mtx_app ---
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DB;" >/dev/null
"$PGBIN/createdb" -h 127.0.0.1 -p 55432 -U postgres -O mtx_migrator "$DB" || exit 2
cd "$REPO/backend" || exit 2
runcheck split-migrate env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55432/$DB "$PY" manage.py migrate --noinput
runcheck split-grant env DJANGO_SETTINGS_MODULE=microtix.settings DATABASE_URL=postgresql://mtx_migrator@127.0.0.1:55432/$DB "$PY" manage.py grant_runtime
runcheck split-test-cleanup-grant "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d "$DB" -v ON_ERROR_STOP=1 -c 'GRANT TRUNCATE ON ALL TABLES IN SCHEMA public,radius TO mtx_app;'
runcheck split-roles-rls "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U mtx_app -d "$DB" -c "SELECT version(),current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user; SELECT n.nspname,c.relname,c.relowner::regrole,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relkind='r' AND n.nspname IN ('public','radius') ORDER BY 1,2;"

export TEST_DATABASE_URL=postgresql://mtx_app@127.0.0.1:55432/$DB
export DATABASE_URL="$TEST_DATABASE_URL"

CE="$REPO/report/controller-evidence"

# --- Probe beku R1-R4 (FROZEN, tanpa modifikasi) ---
runcheck r1-lifecycle "$PY" -m pytest -c pytest.ini "$CE/20261117T134100Z-0020-review/test_lifecycle_review.py" -q -s --reuse-db --tb=short
runcheck r1-authority "$PY" -m pytest -c pytest.ini "$CE/20261117T134100Z-0020-review/test_authority_review.py" -q -s --reuse-db --tb=short
runcheck r2-lifecycle "$PY" -m pytest -c pytest.ini "$CE/20261117T170000Z-0020-r2/lifecycle/test_r2_lifecycle_edges.py" -q -s --reuse-db --tb=short
runcheck r2-authority "$PY" -m pytest -c pytest.ini "$CE/20261117T170000Z-0020-r2/authority/test_authority_r2.py" -q -s --reuse-db --tb=short
runcheck r3-lifecycle "$PY" -m pytest -c pytest.ini "$CE/20261117T212042Z-0020-r3/test_r3_lifecycle_edges.py" -q -s --reuse-db --tb=short
runcheck r3-authority "$PY" -m pytest -c pytest.ini "$CE/20261117T212042Z-0020-r3/test_r3_authority.py" -q -s --reuse-db --tb=short
runcheck r4-lifecycle "$PY" -m pytest -c pytest.ini "$CE/20261118T025143Z-0020-r4/test_r4_lifecycle_edges.py" -q -s --reuse-db --tb=short
runcheck r4-authority "$PY" -m pytest -c pytest.ini "$CE/20261118T025143Z-0020-r4/test_r4_authority_credentials.py" -q -s --reuse-db --tb=short

# --- Regresi controller R4-correction (test_terminal_lease_review.py) ---
runcheck controller-terminal-lease "$PY" -m pytest -c pytest.ini "$CE/20261118T050714Z-0020-r4-correction/test_terminal_lease_review.py" -q -s --reuse-db --tb=short

# --- Tes regresi baru R5 (CI) ---
runcheck r5-residuals "$PY" -m pytest -c pytest.ini tests/integration/test_jobs_r5_residuals.py -q -s --reuse-db --tb=short

# --- Failing-before pada source base (decision head): bukti reproduksi temuan ---
# (dijalankan terpisah oleh run_failing_before.sh — lihat evidence)

# --- Checks wajib ---
runcheck check "$PY" manage.py check
runcheck makemigrations "$PY" manage.py makemigrations --check --dry-run
runcheck create-roles "$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d "$DB" -tAc "SELECT 1"

# --- Suite penuh pada DB runtime role (seperti CI) ---
runcheck full-suite "$PY" -m pytest tests -q --tb=short

# --- Docs validator dari akar repo ---
cd "$REPO" || exit 2
runcheck docs "$PY" docs/tools/check_docs.py

# --- Teardown DB split ---
"$PGBIN/psql" -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $DB;" >/dev/null
echo "=== SEMUA SELESAI ==="
cat "$EVIDENCE/exit-codes.txt"
