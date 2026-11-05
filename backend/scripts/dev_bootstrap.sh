#!/usr/bin/env bash
# Bootstrap pengembangan lokal MicroTix (TK-002).
# - Menyiapkan PostgreSQL (memakai instance sistem atau binary lokal),
#   peran mtx_migrator/mtx_app, database microtix.
# - Migrasi skema sebagai migrator; seed paket + dua tenant sintetis.
# - Idempoten; tidak memasang layanan host produksi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
PGHOST="${MT_PGHOST:-127.0.0.1}"
PGPORT="${MT_PGPORT:-55432}"
export PGHOST PGPORT

# --- 1. Pastikan PostgreSQL hidup ---
if command -v pg_ctl >/dev/null 2>&1; then
  PG_BIN_DIR="$(dirname "$(command -v pg_ctl)")"
elif [ -x "${MT_PG_BIN:-/tmp/pgbin/pg17}/bin/pg_ctl" ]; then
  PG_BIN_DIR="${MT_PG_BIN:-/tmp/pgbin/pg17}/bin"
else
  echo "PostgreSQL tidak ditemukan. Set MT_PG_BIN ke direktori binary PG17." >&2
  exit 1
fi
export LD_LIBRARY_PATH="${MT_PG_BIN:-/tmp/pgbin/pg17}/lib:${LD_LIBRARY_PATH:-}"

PGDATA="$ROOT/pgdata"
if [ ! -f "$PGDATA/PG_VERSION" ]; then
  "$PG_BIN_DIR/initdb" -D "$PGDATA" -U postgres --auth=trust -E UTF8 --locale=C
fi
if ! "$PG_BIN_DIR/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  mkdir -p "$ROOT/pgrun"
  "$PG_BIN_DIR/pg_ctl" -D "$PGDATA" \
    -o "-p $PGPORT -k $ROOT/pgrun -h 127.0.0.1 -c listen_addresses=127.0.0.1" \
    -l "$PGDATA/server.log" start
  sleep 2
fi
"$PG_BIN_DIR/pg_isready" -h "$PGHOST" -p "$PGPORT" >/dev/null

# --- 2. Peran + database (idempoten) ---
psql_bin() { "$PG_BIN_DIR/psql" -h "$PGHOST" -p "$PGPORT" -U postgres -v ON_ERROR_STOP=1 "$@"; }
psql_bin -d postgres -c "DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_migrator') THEN
    CREATE ROLE mtx_migrator LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_app') THEN
    CREATE ROLE mtx_app LOGIN CREATEDB;
  END IF;
END \$\$;"
psql_bin -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='microtix'" | grep -q 1 || \
  psql_bin -d postgres -c "CREATE DATABASE microtix OWNER mtx_migrator"
psql_bin -d microtix -c "GRANT ALL ON DATABASE microtix TO mtx_app;" >/dev/null

# --- 3. Environment ---
cd "$BACKEND"
if [ ! -d .venv ]; then
  python3.13 -m venv .venv 2>/dev/null || virtualenv -p python3.13 .venv
fi
.venv/bin/pip install -q -e . pytest pytest-django 2>/dev/null || .venv/bin/pip install -q Django==5.2.19 djangorestframework==3.16.1 drf-spectacular==0.28.0 "psycopg[binary]==3.2.13" argon2-cffi==25.1.0 cryptography==50.0.2 gunicorn==26.2.0 pytest==8.4.2 pytest-django==4.14.0

cat > "$BACKEND/.env" <<EOF
MT_ENV=dev
DATABASE_URL=postgresql://mtx_app@$PGHOST:$PGPORT/microtix
MIGRATE_DATABASE_URL=postgresql://mtx_migrator@$PGHOST:$PGPORT/microtix
MT_SECRET_KEY=dev-secret-key-change-me-0123456789abcdef
MT_SECRET_BOX_KEY=dev-secret-box-key-change-me-0123456789abcdef
MT_STORAGE_ROOT=$BACKEND/.storage
EOF

set -a; . "$BACKEND/.env"; set +a

# --- 4. Migrasi sebagai migrator ---
DATABASE_URL="$MIGRATE_DATABASE_URL" .venv/bin/python manage.py migrate --noinput

# --- 5. Seed (paket + dua tenant sintetis bila belum ada) ---
.venv/bin/python manage.py seed_dev

echo "Bootstrap selesai. API: cd backend && .venv/bin/python manage.py runserver 127.0.0.1:8000"
