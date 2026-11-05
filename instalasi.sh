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
#   - TANPA eval; argumen dieksekusi sebagai array (quoting aman).
#   - Secret dibuat CSPRNG; tanpa password publik default; tidak ada secret
#     plaintext di log maupun argumen proses (psql membaca dari stdin).
#   - Idempoten; database dipertahankan; backup sebelum upgrade.
#   - TIDAK mengubah perangkat MikroTik pelanggan — router tetap memerlukan
#     enrollment terotorisasi melalui aplikasi (docs/ROUTEROS.md).
#
# Hasil: INSTALL_SUCCESS | INSTALL_PARTIAL | INSTALL_FAILED (exit ≠ 0).
# INSTALL_PARTIAL: komponen inti sehat tetapi prasyarat publik (domain/TLS)
# belum lengkap — BUKAN public-beta-ready.
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
BACKUP_DIR="/var/lib/microtix/backups"
LOG_DIR="/var/log/microtix"
RUN_USER="microtix"
RUN_GROUP="microtix"
DB_NAME="microtix"
DB_MIGRATOR="mtx_migrator"
DB_APP="mtx_app"
ENV_FILE="$ETC_DIR/microtix.env"
WG_DIR="$ETC_DIR/wireguard"
WG_CONF="$WG_DIR/wg0.conf"
MIN_DISK_GB=10
MIN_RAM_MB=2048
PY_REQUIRED="3.13"
PG_MAJOR_REQUIRED=17
NODE_MAJOR_REQUIRED=20
# Komponen beta jaringan: WireGuard host selalu disiapkan (keypair + config);
# FreeRADIUS opsional eksplisit (MT_ENABLE_RADIUS=1) — fase M3 gate G1.
ENABLE_RADIUS="${MT_ENABLE_RADIUS:-0}"

log()  { echo -e "[instalasi] $*"; }
warn() { echo -e "[instalasi] PERINGATAN: $*" >&2; }
die()  { echo -e "[instalasi] GAGAL: $*" >&2; exit 1; }

# Eksekusi tanpa eval — argumen array dikutip apa adanya (master prompt §9.4).
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %q ' "$@"
    echo
  else
    "$@"
  fi
}

run_sh() {
  # Sub-shell dengan string aman (hanya konstanta, tanpa input pengguna).
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] bash -c $1"
  else
    bash -c "$1"
  fi
}

GATE_FAILURES=0
GATE_WARNINGS=0
gate_fail() { echo -e "[instalasi] GATE GAGAL: $*" >&2; GATE_FAILURES=$((GATE_FAILURES+1)); }
gate_warn() { echo -e "[instalasi] GATE SEBAGIAN: $*" >&2; GATE_WARNINGS=$((GATE_WARNINGS+1)); }

# ----------------------------------------------------------------------------
# Preflight OS / sumber daya — versi tidak didukung DITOLAK (bukan warning).
# ----------------------------------------------------------------------------
preflight() {
  [ "$(id -u)" -eq 0 ] || die "Jalankan dengan sudo/root."
  if [ ! -f /etc/debian_version ]; then
    die "OS tidak didukung: target resmi adalah Debian 13. /etc/debian_version tidak ditemukan."
  fi
  . /etc/os-release
  if [ "${VERSION_ID:-}" != "13" ]; then
    die "OS tidak didukung: Debian ${VERSION_ID:-?} terdeteksi; hanya Debian 13 yang diverifikasi (tolak, bukan lanjut)."
  fi
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
# Instal dependensi sistem (paket resmi Debian) — EKSPLISIT lengkap.
# ----------------------------------------------------------------------------
install_dependencies() {
  log "Memasang dependensi sistem (python ${PY_REQUIRED}, postgresql-${PG_MAJOR_REQUIRED}, nodejs, caddy, nftables, wireguard-tools, rsync)..."
  run apt-get update -qq
  # rsync, curl, openssl, ca-certificates: eksplisit (sebelumnya rsync hilang
  # dari daftar meski dipakai deploy_backend — bug #2 audit).
  run apt-get install -y -qq \
    "python${PY_REQUIRED}" "python${PY_REQUIRED}-venv" python3-pip \
    "postgresql-${PG_MAJOR_REQUIRED}" caddy nftables \
    curl openssl ca-certificates rsync wireguard-tools
  # Node.js: Debian 13 menyediakan nodejs >= 20 (cukup untuk build frontend).
  run apt-get install -y -qq nodejs npm
  NODE_V="$(node --version 2>/dev/null | tr -dc '0-9.' )"
  NODE_MAJOR="${NODE_V%%.*}"
  [ "${NODE_MAJOR:-0}" -ge "$NODE_MAJOR_REQUIRED" ] || die "Node.js ${NODE_V:-?} < ${NODE_MAJOR_REQUIRED} — pasang Node ${NODE_MAJOR_REQUIRED}+ manual."
  # pnpm via corepack (versi terpin dari packageManager project).
  if ! command -v pnpm >/dev/null 2>&1; then
    run corepack enable
    run corepack prepare pnpm@12.16.1 --activate
  fi
  command -v pnpm >/dev/null 2>&1 || die "pnpm tidak tersedia setelah corepack."
  log "Dependensi terpasang: $(python${PY_REQUIRED} --version 2>&1), node $(node --version), pnpm $(pnpm --version)."
}

# ----------------------------------------------------------------------------
# Pengguna layanan & direktori persisten (terpisah dari kode aplikasi).
# ----------------------------------------------------------------------------
create_users_dirs() {
  log "Membuat pengguna layanan dan direktori persisten..."
  if ! id -u "$RUN_USER" >/dev/null 2>&1; then
    run useradd --system --home "$STATE_DIR" --shell /usr/sbin/nologin "$RUN_USER"
  fi
  for d in "$INSTALL_ROOT" "$ETC_DIR" "$STATE_DIR" "$STORAGE_DIR" "$BACKUP_DIR" "$LOG_DIR" "$WG_DIR"; do
    run mkdir -p "$d"
  done
  run chown -R "$RUN_USER:$RUN_GROUP" "$STORAGE_DIR" "$LOG_DIR" "$BACKUP_DIR"
  run chown root:"$RUN_GROUP" "$ETC_DIR" "$WG_DIR"
  run chmod 750 "$ETC_DIR" "$STORAGE_DIR" "$LOG_DIR" "$BACKUP_DIR"
  run chmod 700 "$WG_DIR"
}

# ----------------------------------------------------------------------------
# Secret aman (CSPRNG; tanpa default publik) — idempoten, dipertahankan.
# ----------------------------------------------------------------------------
secure_secrets() {
  if [ -f "$ENV_FILE" ] && [ "$DRY_RUN" -ne 1 ]; then
    log "Environment ada — secret dipertahankan."
    return
  fi
  log "Membuat secret CSPRNG..."
  SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-')"
  SECRET_BOX="$(openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-')"
  UPLOAD_KEY="$(openssl rand -base64 32 | tr -d '\n' | tr '/+' '_-')"
  DB_PASS_MIG="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
  DB_PASS_APP="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] menulis $ENV_FILE (secret CSPRNG, tidak ditampilkan)"
    return
  fi
  cat > "$ETC_DIR/env.pending" <<EOF
# Dibuat oleh instalasi.sh — jangan commit; berisi secret. Mode 640 root:microtix.
MT_ENV=production
DATABASE_URL=postgresql://${DB_APP}:${DB_PASS_APP}@127.0.0.1:5432/${DB_NAME}
MIGRATE_DATABASE_URL=postgresql://${DB_MIGRATOR}:${DB_PASS_MIG}@127.0.0.1:5432/${DB_NAME}
MT_SECRET_KEY=${SECRET_KEY}
MT_SECRET_BOX_KEY=${SECRET_BOX}
MT_UPLOAD_SIGNING_KEY=${UPLOAD_KEY}
MT_STORAGE_ROOT=${STORAGE_DIR}
MT_STATIC_ROOT=${INSTALL_ROOT}/static
MT_ALLOWED_HOSTS=${MT_ALLOWED_HOSTS:-localhost,127.0.0.1}
MT_LOG_LEVEL=INFO
MT_DOMAIN=${MT_DOMAIN:-}
MT_WG_ENDPOINT=${MT_WG_ENDPOINT:-}
MT_PUBLIC_BASE_URL=${MT_PUBLIC_BASE_URL:-}
MT_ROUTEROS_ADAPTER=api_ssl
MT_PG_PASSWORD_MIGRATOR=${DB_PASS_MIG}
MT_PG_PASSWORD_APP=${DB_PASS_APP}
EOF
  chmod 640 "$ETC_DIR/env.pending"
  mv "$ETC_DIR/env.pending" "$ENV_FILE"
  chown root:"$RUN_GROUP" "$ENV_FILE"
  log "Secret ditulis ke $ENV_FILE (mode 640, root:$RUN_GROUP)."
}

# ----------------------------------------------------------------------------
# PostgreSQL: peran terpisah migrator/runtime + database.
# Password dikirim via STDIN (bukan argumen proses yang terbaca di ps).
# ----------------------------------------------------------------------------
setup_postgres() {
  log "Menyiapkan PostgreSQL ${PG_MAJOR_REQUIRED} (peran migrator terpisah dari runtime)..."
  [ "$DRY_RUN" -eq 1 ] && { echo "[dry-run] pg_isready + peran + database"; return; }
  systemctl is-active --quiet "postgresql@${PG_MAJOR_REQUIRED}-main" || pg_ctlcluster "$PG_MAJOR_REQUIRED" main start || systemctl start postgresql
  su - postgres -c "psql -v ON_ERROR_STOP=1" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_migrator') THEN
    CREATE ROLE mtx_migrator LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_app') THEN
    CREATE ROLE mtx_app LOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='radius_svc') THEN
    CREATE ROLE radius_svc LOGIN;
  END IF;
END $$;
SQL
  # Password dari env → STDIN psql (tidak muncul di daftar proses/log).
  # Berkas sementara 600 + escaping kutip tunggal (defense-in-depth; charset
  # CSPRNG base64url memang tidak mengandung kutip).
  DB_PASS_MIG="$(grep '^MT_PG_PASSWORD_MIGRATOR=' "$ENV_FILE" | cut -d= -f2-)"
  DB_PASS_APP="$(grep '^MT_PG_PASSWORD_APP=' "$ENV_FILE" | cut -d= -f2-)"
  esc_sql() { printf '%s' "$1" | sed "s/'/''/g"; }
  TMP_SQL="$(mktemp)"
  chmod 600 "$TMP_SQL"
  {
    printf "ALTER ROLE %s PASSWORD '%s';\n" "$DB_MIGRATOR" "$(esc_sql "$DB_PASS_MIG")"
    printf "ALTER ROLE %s PASSWORD '%s';\n" "$DB_APP" "$(esc_sql "$DB_PASS_APP")"
    printf "ALTER ROLE %s NOCREATEDB NOBYPASSRLS;\n" "$DB_APP"
  } > "$TMP_SQL"
  su - postgres -c "psql -v ON_ERROR_STOP=1 -q -f -" < "$TMP_SQL"
  rm -f "$TMP_SQL"
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
  run "python${PY_REQUIRED}" -m venv "$INSTALL_ROOT/venv"
  run "$INSTALL_ROOT/venv/bin/pip" install -q --upgrade pip
  # Pinned persis pyproject.toml (tidak mengambang).
  run "$INSTALL_ROOT/venv/bin/pip" install -q \
    Django==5.2.19 djangorestframework==3.16.1 drf-spectacular==0.28.0 \
    'psycopg[binary]==3.2.13' argon2-cffi==25.1.0 cryptography==50.0.2 gunicorn==26.2.0
  # rsync --delete HANYA pada direktori kode murni (backend/ tanpa data persisten;
  # storage/env/log ada di /var/lib dan /etc — terpisah sesuai §9.5).
  run rsync -a --delete --exclude .venv --exclude __pycache__ --exclude pgdata --exclude pgrun --exclude .storage "$BACKEND_DIR/" "$INSTALL_ROOT/backend/"
  # Migrasi dengan peran migrator (ARCHITECTURE §4), lalu GRANT runtime.
  if [ "$DRY_RUN" -ne 1 ]; then
    (
      cd "$INSTALL_ROOT/backend"
      set -a; . "$ENV_FILE"; set +a
      DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py migrate --noinput
      DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py grant_runtime
      MT_ENV=production "$INSTALL_ROOT/venv/bin/python" manage.py collectstatic --noinput >/dev/null
    )
  else
    echo "[dry-run] migrate (peran migrator) + grant_runtime + collectstatic"
  fi
}

# ----------------------------------------------------------------------------
# Frontend: build produksi LIVE (build mock DITOLAK oleh gate vite)
# ----------------------------------------------------------------------------
build_frontend() {
  log "Build frontend produksi (pnpm + vite, VITE_API_MODE=live wajib)..."
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] pnpm install --frozen-lockfile && VITE_API_MODE=live vite build"
    return
  fi
  (
    cd "$WEB_DIR"
    pnpm install --frozen-lockfile
    # Gate produksi (master prompt §5): tanpa ini build GAGAL — tidak ada
    # fallback mock diam-diam.
    VITE_API_MODE=live pnpm exec vite build --outDir "$INSTALL_ROOT/web-dist" --emptyOutDir
  )
  run chown -R "$RUN_USER:$RUN_GROUP" "$INSTALL_ROOT/web-dist"
}

# ----------------------------------------------------------------------------
# WireGuard host: keypair + config (peers ditambah reconciler saat enrollment).
# TIDAK mengaktifkan forwarding publik; interface diaktifkan mode repair/start.
# ----------------------------------------------------------------------------
setup_wireguard() {
  log "Menyiapkan WireGuard host (keypair CSPRNG, jaringan 100.127.0.0/16)..."
  [ "$DRY_RUN" -eq 1 ] && { echo "[dry-run] keypair + wg0.conf + env MT_WG_SERVER_PUBKEY"; return; }
  if [ ! -f "$WG_DIR/server_private.key" ]; then
    umask 077
    wg genkey > "$WG_DIR/server_private.key"
    wg pubkey < "$WG_DIR/server_private.key" > "$WG_DIR/server_public.key"
    chmod 600 "$WG_DIR/server_private.key"
    chmod 644 "$WG_DIR/server_public.key"
    log "Keypair WireGuard dibuat (private 600 di $WG_DIR)."
  else
    log "Keypair WireGuard sudah ada — dipertahankan."
  fi
  PUB="$(cat "$WG_DIR/server_public.key")"
  if [ ! -f "$WG_CONF" ]; then
    # Private key ditulis via berkas (bukan argumen proses) dengan mode 600.
    {
      echo "# MicroTix — antarmuka manajemen router (peers dihasilkan reconciler)."
      echo "# Aktifkan: systemctl enable --now wg-quick@wg0"
      echo "[Interface]"
      echo "Address = 100.127.0.1/32"
      echo "ListenPort = 51820"
      echo "PrivateKey = $(cat "$WG_DIR/server_private.key")"
    } > "$WG_CONF"
    chmod 600 "$WG_CONF"
    log "Konfigurasi $WG_CONF dibuat (alamat 100.127.0.1/32, port 51820)."
  else
    log "Konfigurasi $WG_CONF sudah ada — dipertahankan."
  fi
  # Publikasikan pubkey ke env aplikasi (bootstrap script memerlukannya).
  if grep -q '^MT_WG_SERVER_PUBKEY=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^MT_WG_SERVER_PUBKEY=.*|MT_WG_SERVER_PUBKEY=${PUB}|" "$ENV_FILE"
  else
    echo "MT_WG_SERVER_PUBKEY=${PUB}" >> "$ENV_FILE"
  fi
  chown root:"$RUN_GROUP" "$ENV_FILE"; chmod 640 "$ENV_FILE"
}

# ----------------------------------------------------------------------------
# systemd: API (gunicorn) + worker
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
After=network.target postgresql@${PG_MAJOR_REQUIRED}-main.service
Wants=postgresql@${PG_MAJOR_REQUIRED}-main.service

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
ReadWritePaths=$STORAGE_DIR $LOG_DIR $STATE_DIR $INSTALL_ROOT/static

[Install]
WantedBy=multi-user.target
EOF
  cat > /etc/systemd/system/microtix-worker.service <<EOF
[Unit]
Description=MicroTix worker (PostgreSQL job + outbox)
After=network.target postgresql@${PG_MAJOR_REQUIRED}-main.service microtix-api.service

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
# nftables: isolasi dasar — tidak menimpa rules existing; rekomendasi saja.
# ----------------------------------------------------------------------------
setup_firewall() {
  log "Memeriksa nftables (isolasi; TIDAK menimpa rules existing tanpa review)..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] verifikasi nftables aktif"; return; fi
  if ! systemctl is-active --quiet nftables; then
    warn "nftables belum aktif. Aktifkan dan terapkan isolasi WireGuard/RADIUS sebelum pilot (lihat docs/OPERATIONS.md)."
    gate_warn "nftables tidak aktif"
    return
  fi
  log "nftables aktif. Aturan spesifik MicroTix diterapkan bersama integrasi jaringan."
}

# ----------------------------------------------------------------------------
# Caddy reverse proxy + HTTPS
# ----------------------------------------------------------------------------
setup_caddy() {
  log "Mengonfigurasi Caddy (HTTPS, same-origin /api)..."
  DOMAIN="${MT_DOMAIN:-$(grep '^MT_DOMAIN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)}"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] menulis /etc/caddy/Caddyfile (domain: ${DOMAIN:-belum diisi})"
    return
  fi
  if [ -z "$DOMAIN" ]; then
    warn "MT_DOMAIN kosong — Caddy memakai :80 (PUBLIKASI TIDAK SIAP). Set MT_DOMAIN=lalu 'instalasi.sh repair'."
    gate_warn "domain/TLS belum dikonfigurasi (INSTALL_PARTIAL)"
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
# FreeRADIUS: opsional eksplisit (MT_ENABLE_RADIUS=1) — fase M3.
# Tanpa itu: jujur TIDAK dipasang; status RADIUS tetap terlihat di aplikasi.
# ----------------------------------------------------------------------------
setup_radius() {
  if [ "$ENABLE_RADIUS" != "1" ]; then
    log "FreeRADIUS tidak dipasang (MT_ENABLE_RADIUS≠1) — fase M3 gate G1; aplikasi tetap mengelola desired NAS revision."
    return
  fi
  log "Memasang FreeRADIUS 3.2 + rlm_sql PostgreSQL (MT_ENABLE_RADIUS=1)..."
  run apt-get install -y -qq freeradius freeradius-postgresql
  if [ "$DRY_RUN" -ne 1 ]; then
    # Skema radius.* + facade sudah dibuat migrasi aplikasi.
    install -d -o freerad -g freerad /etc/freeradius/3.0/mods-enabled
    log "Salin template infra/freeradius (sql-microtix, site-microtix) + clients via radius_reconcile."
    (
      cd "$INSTALL_ROOT/backend"
      set -a; . "$ENV_FILE"; set +a
      "$INSTALL_ROOT/venv/bin/python" manage.py radius_reconcile --dry-run || true
    )
    warn "Selesaikan provisioning RADIUS via runbook infra/freeradius/README.md (role radius_svc + clients.conf + freeradius -C)."
  fi
}

# ----------------------------------------------------------------------------
# Health gates NYATA — kegagalan komponen wajib membuat installer GAGAL.
# ----------------------------------------------------------------------------
health_checks() {
  log "Health checks (gate instalasi)..."
  [ "$DRY_RUN" -eq 1 ] && { echo "[dry-run] /health/live, /health/ready, worker, frontend, TLS"; return; }
  sleep 2
  # 1) API hidup + siap (PostgreSQL).
  if curl -sf http://127.0.0.1:8300/api/v1/health/live >/dev/null; then
    log "  [OK]    health/live"
  else
    gate_fail "health/live gagal — journalctl -u microtix-api -n 50"
  fi
  if curl -sf http://127.0.0.1:8300/api/v1/health/ready >/dev/null; then
    log "  [OK]    health/ready (PostgreSQL reachable)"
  else
    gate_fail "health/ready gagal — koneksi database bermasalah"
  fi
  # 2) Worker berjalan.
  if systemctl is-active --quiet microtix-worker; then
    log "  [OK]    microtix-worker aktif"
  else
    gate_fail "microtix-worker tidak aktif"
  fi
  # 3) Artefak frontend ada.
  if [ -f "$INSTALL_ROOT/web-dist/index.html" ]; then
    log "  [OK]    artefak frontend (web-dist/index.html)"
  else
    gate_fail "artefak frontend tidak ditemukan"
  fi
  # 4) TLS publik (bila domain dikonfigurasi).
  DOMAIN="$(grep '^MT_DOMAIN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
  if [ -n "$DOMAIN" ]; then
    if curl -sf "https://${DOMAIN}/api/v1/health/live" >/dev/null; then
      log "  [OK]    HTTPS https://${DOMAIN}"
    else
      gate_fail "HTTPS https://${DOMAIN} tidak sehat (Caddy ACME? DNS?)"
    fi
  else
    gate_warn "domain/TLS belum dikonfigurasi — tidak public-beta-ready (INSTALL_PARTIAL)"
  fi
  # 5) Izin secret.
  PERM="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo 000)"
  if [ "$PERM" = "640" ]; then
    log "  [OK]    izin $ENV_FILE (640)"
  else
    gate_fail "izin $ENV_FILE = $PERM (harus 640)"
  fi
  # 6) Storage persisten dapat ditulis oleh pengguna layanan.
  if runuser -u "$RUN_USER" -- test -w "$STORAGE_DIR" 2>/dev/null; then
    log "  [OK]    storage persisten dapat ditulis"
  else
    gate_fail "storage $STORAGE_DIR tidak dapat ditulis oleh $RUN_USER"
  fi
}

# ----------------------------------------------------------------------------
# Onboarding administrator platform (dibuat SEKALI; interaktif atau env).
# ----------------------------------------------------------------------------
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
  ) && touch "$STATE_DIR/.platform-admin-created" || gate_warn "admin platform belum dibuat — jalankan 'instalasi.sh repair'"
}

summary() {
  DOMAIN="$(grep '^MT_DOMAIN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo '(belum diisi)')"
  cat <<EOF

================ MicroTix — ringkasan instalasi ================
Mode        : $MODE
Aplikasi    : $( [ -n "$DOMAIN" ] && [ "$DOMAIN" != "(belum diisi)" ] && echo "https://$DOMAIN" || echo "http://<host> (MT_DOMAIN belum diisi — jalankan repair setelah diisi)")
Lokasi      : $INSTALL_ROOT (backend+venv+web-dist+static), $ETC_DIR (env), $STORAGE_DIR (penyimpanan privat)
Database    : PostgreSQL 17 '$DB_NAME' (migrator: $DB_MIGRATOR, runtime: $DB_APP — NOBYPASSRLS)
Layanan     : microtix-api (gunicorn 127.0.0.1:8300), microtix-worker
Proxy       : Caddy (HTTPS same-origin /api)
Firewall    : nftables (periksa status; isolasi WG/RADIUS saat pilot)
WireGuard   : host keypair + $WG_CONF siap (aktifkan: systemctl enable --now wg-quick@wg0)
RADIUS      : $( [ "$ENABLE_RADIUS" = "1" ] && echo "FreeRADIUS dipasang — selesaikan runbook infra/freeradius" || echo "BELUM dipasang (MT_ENABLE_RADIUS=1 untuk fase M3)" )
Enrollment  : Router MikroTik TIDAK diubah installer ini; enrollment melalui
              aplikasi dengan otorisasi Owner (docs/ROUTEROS.md §2).
Perintah    : systemctl status microtix-api microtix-worker
              sudo bash instalasi.sh status | doctor | upgrade | repair
              backup: sudo -u postgres pg_dump -Fc $DB_NAME > $BACKUP_DIR/db-\$(date +%F).dump
===============================================================
EOF
}

# ----------------------------------------------------------------------------
# Mode: status / doctor / upgrade / repair
# ----------------------------------------------------------------------------
do_status() {
  log "Status layanan:"
  for svc in microtix-api microtix-worker caddy "postgresql@${PG_MAJOR_REQUIRED}-main"; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      echo "  [OK]    $svc"
    else
      echo "  [DOWN]  $svc"
    fi
  done
  log "Endpoint:"
  curl -sf -o /dev/null http://127.0.0.1:8300/api/v1/health/live && echo "  [OK]    health/live" || echo "  [DOWN]  health/live"
  curl -sf -o /dev/null http://127.0.0.1:8300/api/v1/health/ready && echo "  [OK]    health/ready" || echo "  [DOWN]  health/ready"
  if systemctl is-active --quiet wg-quick@wg0 2>/dev/null; then
    echo "  [OK]    wireguard wg0"
  else
    echo "  [OFF]   wireguard wg0 (aktifkan saat router mulai di-enroll)"
  fi
  log "Integrasi jaringan: router belum ter-enroll = normal untuk instalasi baru."
}

do_doctor() {
  PREFLIGHT_OK=1
  [ -f /etc/debian_version ] || { warn "Bukan Debian."; PREFLIGHT_OK=0; }
  "python${PY_REQUIRED}" --version >/dev/null 2>&1 || { warn "python${PY_REQUIRED} tidak ada."; PREFLIGHT_OK=0; }
  pg_lsclusters 2>/dev/null | grep -q "${PG_MAJOR_REQUIRED} .* online" || { warn "PostgreSQL ${PG_MAJOR_REQUIRED} tidak online."; PREFLIGHT_OK=0; }
  [ -f "$ENV_FILE" ] || { warn "$ENV_FILE tidak ada."; PREFLIGHT_OK=0; }
  [ "$(stat -c '%a' "$ENV_FILE" 2>/dev/null)" = "640" ] || { warn "Izin $ENV_FILE bukan 640."; PREFLIGHT_OK=0; }
  id -u "$RUN_USER" >/dev/null 2>&1 || { warn "Pengguna $RUN_USER tidak ada."; PREFLIGHT_OK=0; }
  for svc in microtix-api microtix-worker; do
    systemctl is-active --quiet "$svc" || { warn "$svc tidak aktif: journalctl -u $svc -n 50"; PREFLIGHT_OK=0; }
  done
  curl -sf http://127.0.0.1:8300/api/v1/health/ready >/dev/null || { warn "health/ready gagal."; PREFLIGHT_OK=0; }
  command -v pnpm >/dev/null 2>&1 || warn "pnpm tidak ada (dibutuhkan upgrade frontend)."
  DOMAIN="$(grep '^MT_DOMAIN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)"
  [ -n "$DOMAIN" ] || warn "MT_DOMAIN belum diisi — HTTPS publik belum aktif."
  [ "$PREFLIGHT_OK" -eq 1 ] && log "Doctor: semua pemeriksaan utama sehat." || log "Doctor: temuan di atas perlu ditindak."
}

do_upgrade() {
  log "Upgrade (backup database + env → deploy ulang seluruh komponen → restart)..."
  [ -f "$ENV_FILE" ] || die "Belum terinstal."
  if [ "$DRY_RUN" -ne 1 ]; then
    STAMP="$(date +%Y%m%d%H%M%S)"
    run_sh "su - postgres -c 'pg_dump -Fc $DB_NAME' > '$BACKUP_DIR/db-pre-upgrade-$STAMP.dump'"
    # Verifikasi backup VALID (bukan sekadar file ada) sebelum melanjutkan.
    if ! su - postgres -c "pg_restore --list '$BACKUP_DIR/db-pre-upgrade-$STAMP.dump'" >/dev/null 2>&1; then
      die "Backup pre-upgrade tidak valid — upgrade dibatalkan."
    fi
    cp -a "$ENV_FILE" "$BACKUP_DIR/env-pre-upgrade-$STAMP"
    log "Backup valid: $BACKUP_DIR/db-pre-upgrade-$STAMP.dump"
  fi
  deploy_backend
  build_frontend
  deploy_services
  [ "$DRY_RUN" -ne 1 ] && { systemctl restart microtix-api microtix-worker; health_checks; }
  log "Upgrade selesai (seluruh komponen diperbarui: backend + frontend + layanan)."
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
    setup_wireguard
    deploy_services
    setup_firewall
    setup_caddy
    setup_radius
    health_checks
    admin_onboarding
    summary
    if [ "$GATE_FAILURES" -gt 0 ]; then
      echo "[instalasi] HASIL: INSTALL_FAILED ($GATE_FAILURES gate gagal). Perbaiki lalu jalankan 'instalasi.sh repair'." >&2
      exit 2
    elif [ "$GATE_WARNINGS" -gt 0 ]; then
      echo "[instalasi] HASIL: INSTALL_PARTIAL (inti sehat; prasyarat publik belum lengkap — lihat GATE SEBAGIAN di atas)." >&2
      exit 3
    else
      echo "[instalasi] HASIL: INSTALL_SUCCESS."
    fi
    ;;
  status)  do_status ;;
  doctor)  do_doctor ;;
  upgrade) preflight; do_upgrade ;;
  repair)  preflight; do_repair ;;
  *) die "Mode tidak dikenal: $MODE (install|status|doctor|upgrade|repair|--dry-run)" ;;
esac
