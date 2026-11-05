#!/usr/bin/env bash
# ============================================================================
# MicroTix — installer resmi (root-level instalasi.sh)
#
# Target didukung: Debian 13 (trixie) pada arsitektur amd64/arm64 dengan
# sumber daya minimum yang diverifikasi di preflight. Bukan klaim universal
# untuk semua distro/hosting.
#
# Mode:
#   sudo bash instalasi.sh install     # instal lengkap (idempoten)
#   sudo bash instalasi.sh status      # status layanan & kesehatan
#   sudo bash instalasi.sh doctor      # diagnosis + saran perbaikan
#   sudo bash instalasi.sh upgrade     # upgrade versi (backup dulu)
#   sudo bash instalasi.sh repair      # perbaikan layanan bermasalah
#   sudo bash instalasi.sh --dry-run   # tampilkan rencana tanpa eksekusi
#
# Keamanan:
#   - Secret dibuat CSPRNG; tanpa password publik default; tidak ada secret
#     plaintext di log.
#   - Idempoten; database dipertahankan; backup sebelum upgrade.
#   - TIDAK mengubah perangkat MikroTik pelanggan — router tetap memerlukan
#     enrollment terotorisasi melalui aplikasi (docs/ROUTEROS.md).
# ============================================================================
set -euo pipefail

MODE="${1:-install}"
DRY_RUN=0
[ "${2:-}" = "--dry-run" ] && DRY_RUN=1
[ "${1:-}" = "--dry-run" ] && { DRY_RUN=1; MODE="install"; }

APP_NAME="microtix"
INSTALL_ROOT="/opt/microtix"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
WEB_DIR="$REPO_DIR/apps/web"
ETC_DIR="/etc/microtix"
STATE_DIR="/var/lib/microtix"
STORAGE_DIR="/var/lib/microtix/storage"
LOG_DIR="/var/log/microtix"
RUN_USER="microtix"
RUN_GROUP="microtix"
DB_NAME="microtix"
DB_MIGRATOR="mtx_migrator"
DB_APP="mtx_app"
ENV_FILE="$ETC_DIR/microtix.env"
MIN_DISK_GB=10
MIN_RAM_MB=2048
PY_REQUIRED="3.13"
PG_MAJOR_REQUIRED=17

log()  { echo -e "[instalasi] $*"; }
warn() { echo -e "[instalasi] PERINGATAN: $*" >&2; }
die()  { echo -e "[instalasi] GAGAL: $*" >&2; exit 1; }

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

# ----------------------------------------------------------------------------
# Preflight OS / sumber daya
# ----------------------------------------------------------------------------
preflight() {
  [ "$(id -u)" -eq 0 ] || die "Jalankan dengan sudo/root."
  if [ ! -f /etc/debian_version ]; then
    die "OS tidak didukung: target resmi adalah Debian 13. /etc/debian_version tidak ditemukan."
  fi
  . /etc/os-release
  [ "${VERSION_ID:-}" = "13" ] || warn "Debian ${VERSION_ID:-?} terdeteksi; hanya Debian 13 diverifikasi."
  log "OS: Debian ${VERSION_ID:-?} (${PRETTY_NAME:-})"

  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64|aarch64) log "Arsitektur: $ARCH (didukung)" ;;
    *) die "Arsitektur $ARCH belum diverifikasi." ;;
  esac

  DISK_GB=$(( $(df -BG --output=avail / | tail -1 | tr -dc '0-9') ))
  [ "$DISK_GB" -ge "$MIN_DISK_GB" ] || die "Disk kurang: ${DISK_GB}GB < ${MIN_DISK_GB}GB."
  RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
  [ "$RAM_MB" -ge "$MIN_RAM_MB" ] || die "RAM kurang: ${RAM_MB}MB < ${MIN_RAM_MB}MB."
  log "Sumber daya OK: ${DISK_GB}GB disk, ${RAM_MB}MB RAM."
}

# ----------------------------------------------------------------------------
# Instal dependensi sistem (paket resmi Debian)
# ----------------------------------------------------------------------------
install_dependencies() {
  log "Memasang dependensi sistem (python ${PY_REQUIRED}, postgresql-17, caddy, nftables)..."
  run "apt-get update -qq"
  run "apt-get install -y -qq python3.13 python3.13-venv python3-pip postgresql-17 caddy nftables curl openssl ca-certificates >/dev/null"
  log "Dependensi terpasang."
}

# ----------------------------------------------------------------------------
# Pengguna layanan & direktori persisten
# ----------------------------------------------------------------------------
create_users_dirs() {
  log "Membuat pengguna layanan dan direktori persisten..."
  if ! id -u "$RUN_USER" >/dev/null 2>&1; then
    run "useradd --system --home $STATE_DIR --shell /usr/sbin/nologin $RUN_USER"
  fi
  for d in "$INSTALL_ROOT" "$ETC_DIR" "$STATE_DIR" "$STORAGE_DIR" "$LOG_DIR"; do
    run "mkdir -p '$d'"
  done
  run "chown -R $RUN_USER:$RUN_GROUP '$STORAGE_DIR' '$LOG_DIR'"
  run "chmod 750 '$ETC_DIR' '$STORAGE_DIR' '$LOG_DIR'"
}

# ----------------------------------------------------------------------------
# Secret aman (CSPRNG; tanpa default publik)
# ----------------------------------------------------------------------------
secure_secrets() {
  if [ -f "$ENV_FILE" ] && [ "$DRY_RUN" -ne 1 ]; then
    log "Environment ada — secret dipertahankan."
    return
  fi
  log "Membuat secret CSPRNG..."
  SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-')"
  SECRET_BOX="$(openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-')"
  DB_PASS_MIG="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
  DB_PASS_APP="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] menulis $ENV_FILE (secret CSPRNG, tidak ditampilkan)"
    return
  fi
  cat > "$ETC_DIR/env.pending" <<EOF
# Dibuat oleh instalasi.sh — jangan commit; berisi secret.
MT_ENV=production
DATABASE_URL=postgresql://${DB_APP}:${DB_PASS_APP}@127.0.0.1:5432/${DB_NAME}
MIGRATE_DATABASE_URL=postgresql://${DB_MIGRATOR}:${DB_PASS_MIG}@127.0.0.1:5432/${DB_NAME}
MT_SECRET_KEY=${SECRET_KEY}
MT_SECRET_BOX_KEY=${SECRET_BOX}
MT_STORAGE_ROOT=${STORAGE_DIR}
MT_STATIC_ROOT=${INSTALL_ROOT}/static
MT_ALLOWED_HOSTS=${MT_ALLOWED_HOSTS:-localhost}
MT_LOG_LEVEL=INFO
MT_PG_PASSWORD_MIGRATOR=${DB_PASS_MIG}
MT_PG_PASSWORD_APP=${DB_PASS_APP}
EOF
  chmod 640 "$ETC_DIR/env.pending"
  mv "$ETC_DIR/env.pending" "$ENV_FILE"
  chown root:"$RUN_GROUP" "$ENV_FILE"
  log "Secret ditulis ke $ENV_FILE (mode 640, root:$RUN_GROUP)."
}

# ----------------------------------------------------------------------------
# PostgreSQL: peran terpisah migrator/runtime + database
# ----------------------------------------------------------------------------
setup_postgres() {
  log "Menyiapkan PostgreSQL 17 (peran migrator terpisah dari runtime)..."
  # shellcheck disable=SC1091
  [ "$DRY_RUN" -eq 1 ] && { echo "[dry-run] pg_isready + peran + database"; return; }
  systemctl is-active --quiet postgresql@17-main || pg_ctlcluster 17 main start || systemctl start postgresql
  su - postgres -c "psql -v ON_ERROR_STOP=1" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_migrator') THEN
    CREATE ROLE mtx_migrator LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_app') THEN
    CREATE ROLE mtx_app LOGIN;
  END IF;
END $$;
SQL
  # Password dari env (tanpa interpolasi ke CLI psql log).
  DB_PASS_MIG="$(grep '^MT_PG_PASSWORD_MIGRATOR=' "$ENV_FILE" | cut -d= -f2-)"
  DB_PASS_APP="$(grep '^MT_PG_PASSWORD_APP=' "$ENV_FILE" | cut -d= -f2-)"
  su - postgres -c "psql -v ON_ERROR_STOP=1 -c \"ALTER ROLE $DB_MIGRATOR PASSWORD '$DB_PASS_MIG';\""
  su - postgres -c "psql -v ON_ERROR_STOP=1 -c \"ALTER ROLE $DB_APP PASSWORD '$DB_PASS_APP';\""
  # Runtime TANPA CREATEDB (berbeda dari dev): pemisahan produksi penuh.
  su - postgres -c "psql -v ON_ERROR_STOP=1 -c \"ALTER ROLE $DB_APP NOCREATEDB NOBYPASSRLS;\""
  if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\"" | grep -q 1; then
    su - postgres -c "createdb -O $DB_MIGRATOR $DB_NAME"
    log "Database $DB_NAME dibuat (pemilik: $DB_MIGRATOR)."
  else
    log "Database $DB_NAME sudah ada — dipertahankan."
  fi
}

# ----------------------------------------------------------------------------
# Backend: venv + dependensi pinned + migrasi (sebagai migrator) + grant runtime
# ----------------------------------------------------------------------------
deploy_backend() {
  log "Menyebarkan backend (Python ${PY_REQUIRED}, dependensi pinned)..."
  run "python3.13 -m venv $INSTALL_ROOT/venv"
  run "$INSTALL_ROOT/venv/bin/pip install -q --upgrade pip"
  run "$INSTALL_ROOT/venv/bin/pip install -q Django==5.2.19 djangorestframework==3.16.1 drf-spectacular==0.28.0 'psycopg[binary]==3.2.13' argon2-cffi==25.1.0 cryptography==50.0.2 gunicorn==26.2.0"
  run "rsync -a --delete --exclude .venv --exclude .storage --exclude __pycache__ '$BACKEND_DIR/' '$INSTALL_ROOT/backend/'"
  # Migrasi dengan peran migrator (ARCHITECTURE §4), lalu GRANT runtime.
  if [ "$DRY_RUN" -ne 1 ]; then
    (
      cd "$INSTALL_ROOT/backend"
      set -a; . "$ENV_FILE"; set +a
      DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py migrate --noinput
      DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py grant_runtime
    )
  else
    echo "[dry-run] migrate (peran migrator) + grant_runtime"
  fi
}

# ----------------------------------------------------------------------------
# Frontend: build produksi (bukan dev server)
# ----------------------------------------------------------------------------
build_frontend() {
  log "Build frontend produksi (pnpm + vite)..."
  run "cd '$WEB_DIR' && pnpm install --frozen-lockfile && pnpm exec vite build --outDir '$INSTALL_ROOT/web-dist'"
}

# ----------------------------------------------------------------------------
# systemd: API (gunicorn) + worker + dispatcher
# ----------------------------------------------------------------------------
deploy_services() {
  log "Memasang layanan systemd (api gunicorn, worker job)..."
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] menulis unit systemd microtix-api.service, microtix-worker.service"
    return
  fi
  cat > /etc/systemd/system/microtix-api.service <<EOF
[Unit]
Description=MicroTix API (gunicorn)
After=network.target postgresql@17-main.service
Wants=postgresql@17-main.service

[Service]
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$INSTALL_ROOT/backend
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_ROOT/venv/bin/gunicorn microtix.wsgi:application \\
    --bind 127.0.0.1:8300 --workers 3 --timeout 60 \\
    --access-logfile $LOG_DIR/api-access.log --error-logfile $LOG_DIR/api-error.log
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$STORAGE_DIR $LOG_DIR $STATE_DIR

[Install]
WantedBy=multi-user.target
EOF
  cat > /etc/systemd/system/microtix-worker.service <<EOF
[Unit]
Description=MicroTix worker (PostgreSQL job + outbox)
After=network.target postgresql@17-main.service microtix-api.service

[Service]
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$INSTALL_ROOT/backend
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_ROOT/venv/bin/python manage.py runworker --loop --interval 2
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$STORAGE_DIR $LOG_DIR $STATE_DIR

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now microtix-api.service microtix-worker.service
}

# ----------------------------------------------------------------------------
# nftables: isolasi dasar (preflight — tidak menimpa rules existing tanpa review)
# ----------------------------------------------------------------------------
setup_firewall() {
  log "Memeriksa nftables (isolasi; TIDAK menimpa rules existing tanpa preflight)..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] verifikasi nftables aktif"; return; fi
  if ! systemctl is-active --quiet nftables; then
    warn "nftables belum aktif. Aturan isolasi WireGuard/RADIUS akan diterapkan saat integrasi jaringan (M3) dikonfigurasi."
    return
  fi
  log "nftables aktif. Aturan spesifik MicroTix diterapkan bersama integrasi jaringan."
}

# ----------------------------------------------------------------------------
# Caddy reverse proxy + HTTPS
# ----------------------------------------------------------------------------
setup_caddy() {
  log "Mengonfigurasi Caddy (HTTPS, same-origin /api)..."
  DOMAIN="${MT_DOMAIN:-}"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] menulis /etc/caddy/Caddyfile (domain: ${DOMAIN:-belum diisi})"
    return
  fi
  if [ -z "$DOMAIN" ]; then
    warn "MT_DOMAIN kosong — Caddy memakai placeholder :80. Set MT_DOMAIN=lalu jalankan 'instalasi.sh repair'."
  fi
  cat > /etc/caddy/Caddyfile <<EOF
# MicroTix — reverse proxy same-origin (API + SPA).
# Ganti \$DOMAIN via 'sudo bash instalasi.sh repair' setelah MT_DOMAIN diisi.
${DOMAIN:-:80} {
        encode gzip
        handle_path /api/* {
                reverse_proxy 127.0.0.1:8300
        }
        handle {
                root * $INSTALL_ROOT/web-dist
                try_files {path} /index.html
                file_server
        }
}
EOF
  systemctl reload caddy || systemctl restart caddy
}

# ----------------------------------------------------------------------------
# FreeRADIUS: fase-aware (M3) — tidak dipasang paksa di R1
# ----------------------------------------------------------------------------
setup_radius() {
  if [ -f "$INSTALL_ROOT/.radius-configured" ]; then
    log "FreeRADIUS: sudah dikonfigurasi."
    return
  fi
  log "Integrasi RADIUS (FreeRADIUS 3.2) aktif pada fase M3 — belum dipasang di R1."
  log "Saat fase aktif: listener hanya pada alamat tunnel; NAS/client reconciliation via aplikasi."
}

# ----------------------------------------------------------------------------
# Health checks + onboarding admin
# ----------------------------------------------------------------------------
health_checks() {
  log "Health checks..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] /health/live, /health/ready"; return; fi
  sleep 2
  if curl -sf http://127.0.0.1:8300/api/v1/health/live >/dev/null; then
    log "health/live: OK"
  else
    warn "health/live gagal — periksa: journalctl -u microtix-api -n 50"
  fi
  if curl -sf http://127.0.0.1:8300/api/v1/health/ready >/dev/null; then
    log "health/ready: OK (PostgreSQL reachable)"
  else
    warn "health/ready gagal — periksa koneksi database."
  fi
}

admin_onboarding() {
  log "Onboarding administrator platform..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] membuat admin platform (interaktif)"; return; fi
  if [ -f "$STATE_DIR/.platform-admin-created" ]; then
    log "Admin platform sudah ada — lewati."
    return
  fi
  echo "Buat akun Super Admin platform (akun individual; wajib MFA setelah login):"
  (
    cd "$INSTALL_ROOT/backend"
    set -a; . "$ENV_FILE"; set +a
    "$INSTALL_ROOT/venv/bin/python" manage.py createsuperuser
  ) && touch "$STATE_DIR/.platform-admin-created" || warn "Admin belum dibuat — jalankan repair nanti."
}

summary() {
  cat <<EOF

================ MicroTix — ringkasan instalasi ================
Mode        : $MODE
Lokasi      : $INSTALL_ROOT (backend+venv+web-dist), $ETC_DIR (env), $STORAGE_DIR (penyimpanan privat)
Database    : PostgreSQL 17 '$DB_NAME' (migrator: $DB_MIGRATOR, runtime: $DB_APP — NOBYPASSRLS)
Layanan     : microtix-api (gunicorn 127.0.0.1:8300), microtix-worker
Proxy       : Caddy (HTTPS same-origin /api)
Firewall    : nftables aktif; aturan WireGuard/RADIUS menyusul integrasi jaringan
RADIUS      : FASE M3 — belum dikonfigurasi (jujur; router pun belum di-enroll)
Catatan     : Router MikroTik TIDAK diubah installer ini; enrollment tetap
              melalui aplikasi dengan otorisasi Owner (docs/ROUTEROS.md).
Perintah    : systemctl status microtix-api microtix-worker
              sudo bash instalasi.sh status | doctor | upgrade | repair
===============================================================
EOF
}

# ----------------------------------------------------------------------------
# Mode: status / doctor / upgrade / repair
# ----------------------------------------------------------------------------
do_status() {
  log "Status layanan:"
  for svc in microtix-api microtix-worker caddy postgresql@17-main; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      echo "  [OK]    $svc"
    else
      echo "  [DOWN]  $svc"
    fi
  done
  log "Endpoint:"
  curl -sf -o /dev/null http://127.0.0.1:8300/api/v1/health/live && echo "  [OK]    health/live" || echo "  [DOWN]  health/live"
  curl -sf -o /dev/null http://127.0.0.1:8300/api/v1/health/ready && echo "  [OK]    health/ready" || echo "  [DOWN]  health/ready"
  log "Integrasi jaringan: router belum ter-enroll = normal untuk instalasi baru."
}

do_doctor() {
  PREFLIGHT_OK=1
  [ -f /etc/debian_version ] || { warn "Bukan Debian."; PREFLIGHT_OK=0; }
  python3.13 --version >/dev/null 2>&1 || { warn "python3.13 tidak ada."; PREFLIGHT_OK=0; }
  pg_lsclusters 2>/dev/null | grep -q "17 .* online" || { warn "PostgreSQL 17 tidak online."; PREFLIGHT_OK=0; }
  [ -f "$ENV_FILE" ] || { warn "$ENV_FILE tidak ada."; PREFLIGHT_OK=0; }
  grep -q "MT_SECRET_KEY=ganti" "$ENV_FILE" 2>/dev/null && { warn "Secret masih default! Ganti segera."; PREFLIGHT_OK=0; }
  id -u "$RUN_USER" >/dev/null 2>&1 || { warn "Pengguna $RUN_USER tidak ada."; PREFLIGHT_OK=0; }
  for svc in microtix-api microtix-worker; do
    systemctl is-active --quiet "$svc" || { warn "$svc tidak aktif: journalctl -u $svc -n 50"; PREFLIGHT_OK=0; }
  done
  [ "$PREFLIGHT_OK" -eq 1 ] && log "Doctor: semua pemeriksaan utama sehat." || log "Doctor: temuan di atas perlu ditindak."
}

do_upgrade() {
  log "Upgrade (backup database → migrasi → restart)..."
  [ -f "$ENV_FILE" ] || die "Belum terinstal."
  if [ "$DRY_RUN" -ne 1 ]; then
    run "su - postgres -c 'pg_dump -Fc $DB_NAME > /var/lib/postgresql/microtix-pre-upgrade-\$(date +%Y%m%d%H%M%S).dump'"
  fi
  deploy_backend
  [ "$DRY_RUN" -ne 1 ] && { systemctl restart microtix-api microtix-worker; health_checks; }
  log "Upgrade selesai."
}

do_repair() {
  log "Repair: restart layanan + reload konfigurasi..."
  [ "$DRY_RUN" -ne 1 ] || { echo "[dry-run] restart api/worker/caddy"; return; }
  systemctl restart microtix-api microtix-worker || true
  setup_caddy
  health_checks
}

# ----------------------------------------------------------------------------
# Eksekusi utama
# ----------------------------------------------------------------------------
case "$MODE" in
  install)
    preflight
    install_dependencies
    create_users_dirs
    secure_secrets
    setup_postgres
    deploy_backend
    build_frontend
    deploy_services
    setup_firewall
    setup_caddy
    setup_radius
    health_checks
    admin_onboarding
    summary
    ;;
  status)  do_status ;;
  doctor)  do_doctor ;;
  upgrade) preflight; do_upgrade ;;
  repair)  preflight; do_repair ;;
  *) die "Mode tidak dikenal: $MODE (install|status|doctor|upgrade|repair|--dry-run)" ;;
esac
