#!/usr/bin/env bash
# Executor r5 — live upgrade evidence runner (REV-1311-01 correction).
# For each variant: fresh PostgreSQL DB + physical storage dir,
# OLD backend (main@9903d9b worktree) does the real HTTP upload through the
# old idempotency writer, then NEW backend (candidate worktree) migrates
# jobs.0004/0005 and retries the same principal/key/body canonically.
set -uo pipefail

REPO=/home/z/my-project/repo-microtix
OLD=/home/z/my-project/oldmain
BASE=/tmp/mtxr5
VARIANTS=("canonical" "urn" "urn_ambiguous" "uuid_only" "uuid_only_ambiguous" "urn_only" "platform_uuid_resource")
PGBIN=/home/z/pgbase/pgbin/pg17/bin
export LD_LIBRARY_PATH="$PGBIN/../lib:${LD_LIBRARY_PATH:-}"
PGHOST=127.0.0.1; PGPORT=55432
VENV="$REPO/backend/.venv/bin/python"
SECRET="r5-live-upgrade-secret-key-0123456789abcdef"
RESULTS="$BASE/results.json"
PROBE=/home/z/my-project/scripts/probe_live_upgrade.py

mkdir -p "$BASE"
echo '{"variants": {}}' > "$RESULTS"

for variant in "${VARIANTS[@]}"; do
  echo "=== variant: $variant ==="
  db="mtxr5_$(echo "$variant" | tr - _)"
  storage="$BASE/storage_$variant"
  state="$BASE/state_$variant.json"
  export PGHOST PGPORT
  PSQL() { "$PGBIN/psql" -h "$PGHOST" -p "$PGPORT" -U postgres -v ON_ERROR_STOP=1 "$@"; }
  PSQL -d postgres -c "DROP DATABASE IF EXISTS $db" >/dev/null 2>&1
  PSQL -d postgres -c "CREATE DATABASE $db OWNER mtx_migrator" >/dev/null
  PSQL -d "$db" -c "GRANT ALL ON DATABASE $db TO mtx_app" >/dev/null
  rm -rf "$storage"; mkdir -p "$storage"
  rm -f "$state"

  run_backend() {  # $1=backend-dir $2=phase
    local dir="$1" phase="$2"
    (cd "$dir" && \
      PYTHONPATH="$dir" \
      DATABASE_URL="postgresql://mtx_app@$PGHOST:$PGPORT/$db" \
      MIGRATE_DATABASE_URL="postgresql://mtx_migrator@$PGHOST:$PGPORT/$db" \
      MT_SECRET_KEY="$SECRET" MT_SECRET_BOX_KEY="$SECRET-box" \
      MT_STORAGE_ROOT="$storage" MT_ENV=dev DJANGO_SETTINGS_MODULE=microtix.settings \
      "$VENV" "$PROBE" "$phase" "$variant" "$state")
  }
  migrate_backend() {  # $1=backend-dir
    (cd "$1" && \
      DATABASE_URL="postgresql://mtx_migrator@$PGHOST:$PGPORT/$db" \
      MT_SECRET_KEY="$SECRET" MT_SECRET_BOX_KEY="$SECRET-box" \
      MT_STORAGE_ROOT="$storage" MT_ENV=dev DJANGO_SETTINGS_MODULE=microtix.settings \
      "$VENV" manage.py migrate --noinput && \
      DATABASE_URL="postgresql://mtx_migrator@$PGHOST:$PGPORT/$db" \
      MT_SECRET_KEY="$SECRET" MT_SECRET_BOX_KEY="$SECRET-box" \
      MT_STORAGE_ROOT="$storage" MT_ENV=dev DJANGO_SETTINGS_MODULE=microtix.settings \
      "$VENV" manage.py grant_runtime)
  }

  ok=1
  migrate_backend "$OLD/backend" || ok=0
  [ $ok -eq 1 ] && run_backend "$OLD/backend" before || ok=0
  [ $ok -eq 1 ] && migrate_backend "$REPO/backend" || ok=0
  [ $ok -eq 1 ] && run_backend "$REPO/backend" after || ok=0

  python3 - "$RESULTS" "$variant" "$ok" <<'PYEOF'
import json, sys
path, variant, ok = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
data = json.load(open(path))
data["variants"][variant] = "PASS" if ok else "FAIL"
json.dump(data, open(path, "w"), indent=2)
PYEOF
done

echo "=== SUMMARY ==="
cat "$RESULTS"
grep -q FAIL "$RESULTS" && exit 1 || exit 0
