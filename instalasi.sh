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
BACKUP_DIR="/var/lib/microtix/backups"
LOG_DIR="/var/log/microtix"
WG_DIR="$ETC_DIR/wireguard"
WG_CONF="$WG_DIR/wg0.conf"
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

# Eksekusi perintah TANPA eval (input tidak di-interpretasi ulang shell).
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

# Untuk perintah majemuk lama (cd X && Y) — subshell eksplisit, bukan eval.
run_sh() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] sh: %s\n' "$*"
  else
    bash -c "$1"
  fi
}

# ----------------------------------------------------------------------------
# Preflight OS / sumber daya
# ----------------------------------------------------------------------------
preflight() {
  if [ "$DRY_RUN" -eq 1 ]; then
    log "[dry-run] preflight dilewati level-privilege (tidak ada mutasi sistem)."
  else
    [ "$(id -u)" -eq 0 ] || die "Jalankan dengan sudo/root."
  fi
  if [ ! -f /etc/debian_version ]; then
    die "OS tidak didukung: target resmi adalah Debian 13. /etc/debian_version tidak ditemukan."
  fi
  . /etc/os-release
  # Kebijakan §9.2: OS selain Debian 13 DITOLAK (bukan warning lalu lanjut).
  [ "${VERSION_ID:-}" = "13" ] || die "Debian ${VERSION_ID:-?} tidak didukung — hanya Debian 13 terverifikasi."
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
  log "Memasang dependensi sistem (python ${PY_REQUIRED}, postgresql-17, caddy, nftables, nodejs, rsync, wireguard-tools)..."
  run apt-get update -qq
  # Node.js Debian 13 (20.x) memenuhi Vite; pnpm via corepack (terpin 12.16.1).
  run apt-get install -y -qq python3.13 python3.13-venv python3-pip \
      postgresql-17 caddy nftables curl openssl ca-certificates \
      nodejs npm rsync wireguard-tools >/dev/null
  if [ "$DRY_RUN" -ne 1 ]; then
    corepack enable >/dev/null 2>&1 || npm install -g corepack >/dev/null
    corepack prepare pnpm@12.16.1 --activate
    command -v pnpm >/dev/null || die "pnpm tidak tersedia setelah corepack."
  else
    echo "[dry-run] corepack enable + pnpm@12.16.1"
  fi
  # FreeRADIUS 3.2 — fase-gated (M3/beta RADIUS): dipasang bila MT_ENABLE_RADIUS=1.
  if [ "${MT_ENABLE_RADIUS:-0}" = "1" ]; then
    run apt-get install -y -qq freeradius freeradius-postgresql freeradius-utils >/dev/null
    log "FreeRADIUS 3.2 + rlm_sql postgresql terpasang (MT_ENABLE_RADIUS=1)."
  else
    log "FreeRADIUS dilewati (set MT_ENABLE_RADIUS=1 untuk mengaktifkan; jujur — tidak dipasang diam-diam)."
  fi
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
  for d in "$INSTALL_ROOT" "$ETC_DIR" "$STATE_DIR" "$STORAGE_DIR" "$BACKUP_DIR" "$LOG_DIR" "$WG_DIR"; do
    run "mkdir -p '$d'"
  done
  run "chown -R $RUN_USER:$RUN_GROUP '$STORAGE_DIR' '$LOG_DIR'"
  run "chmod 750 '$ETC_DIR' '$STORAGE_DIR' '$LOG_DIR'"
  run "chown root:$RUN_GROUP '$WG_DIR'"
  run "chmod 700 '$WG_DIR'"
}

# ----------------------------------------------------------------------------
# Secret aman (CSPRNG; tanpa default publik)
# ----------------------------------------------------------------------------
secure_secrets() {
  if [ -f "$ENV_FILE" ] && [ "$DRY_RUN" -ne 1 ]; then
    log "Environment ada — secret dipertahankan."
    # Upgrade-safe: pastikan MT_DOMAIN (hostname publik gateway VPN untuk skrip
    # bootstrap router — vpn.gateway_hostname) tersedia bagi aplikasi bila operator
    # mensetnya dan berkas lama belum memuatnya. Idempoten; tanpa menimpa nilai lain.
    if [ -n "${MT_DOMAIN:-}" ] && ! grep -q '^MT_DOMAIN=' "$ENV_FILE" 2>/dev/null; then
      printf 'MT_DOMAIN=%s\n' "$MT_DOMAIN" >> "$ENV_FILE"
      log "MT_DOMAIN ditambahkan ke $ENV_FILE (gateway hostname bootstrap)."
    fi
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
MT_ALLOWED_HOSTS=${MT_ALLOWED_HOSTS:-${MT_DOMAIN:-localhost}}
MT_DOMAIN=${MT_DOMAIN:-}
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
  # Password dikirim via stdin psql — tidak muncul di argv/ps/log (§9.4).
  DB_PASS_MIG="$(grep '^MT_PG_PASSWORD_MIGRATOR=' "$ENV_FILE" | cut -d= -f2-)"
  DB_PASS_APP="$(grep '^MT_PG_PASSWORD_APP=' "$ENV_FILE" | cut -d= -f2-)"
  printf 'ALTER ROLE %s PASSWORD %s;\n' "$DB_MIGRATOR" "'$DB_PASS_MIG'" \
    | su - postgres -c "psql -v ON_ERROR_STOP=1"
  printf 'ALTER ROLE %s PASSWORD %s;\n' "$DB_APP" "'$DB_PASS_APP'" \
    | su - postgres -c "psql -v ON_ERROR_STOP=1"
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
  run python3.13 -m venv "$INSTALL_ROOT/venv"
  run "$INSTALL_ROOT/venv/bin/pip" install -q --upgrade pip
  run "$INSTALL_ROOT/venv/bin/pip" install -q Django==5.2.19 djangorestframework==3.16.1 drf-spectacular==0.28.0 'psycopg[binary]==3.2.13' argon2-cffi==25.1.0 cryptography==50.0.2 gunicorn==26.2.0
  # rsync --delete HANYA pada direktori kode aplikasi; state persisten
  # ($STORAGE_DIR, DB, env) berada di luar pohon ini (§9.5).
  run rsync -a --delete --exclude .venv --exclude .storage --exclude pgdata --exclude __pycache__ --exclude .env \
      "$BACKEND_DIR/" "$INSTALL_ROOT/backend/"
  # Migrasi dengan peran migrator (ARCHITECTURE §4), lalu GRANT runtime.
  if [ "$DRY_RUN" -ne 1 ]; then
    (
      cd "$INSTALL_ROOT/backend"
      set -a; . "$ENV_FILE"; set +a
      DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py migrate --noinput
      DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py grant_runtime
      "$INSTALL_ROOT/venv/bin/python" manage.py collectstatic --noinput -v0
    )
  else
    echo "[dry-run] migrate (peran migrator) + grant_runtime"
  fi
}

# ----------------------------------------------------------------------------
# Frontend: build produksi (bukan dev server)
# ----------------------------------------------------------------------------
build_frontend() {
  log "Build frontend produksi (pnpm + vite; VITE_API_MODE=live wajib — guard build menolak mock)..."
  # Guard di vite.config.ts menggagalkan build tanpa live (§5 anti mock-fallback).
  run_sh "cd '$WEB_DIR' && pnpm install --frozen-lockfile && VITE_API_MODE=live pnpm exec vite build --outDir '$INSTALL_ROOT/web-dist'"
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
# WireGuard host (§9.13) — keypair CSPRNG + wg0.conf idempoten (port be2)
# ----------------------------------------------------------------------------
setup_wireguard() {
  log "Menyiapkan WireGuard host (keypair CSPRNG, jaringan 100.127.0.0/16)..."
  [ "$DRY_RUN" -eq 1 ] && { echo "[dry-run] keypair + wg0.conf + env MT_WG_SERVER_PUBKEY + adopt_wg_host + render_wg_config"; return; }
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
  # Adopsi pubkey oleh model WireGuardHost backend (idempoten; rotasi dengan
  # peer aktif ditolak jujur oleh command). Gagal adopsi = bootstrap script
  # akan memuat kunci salah → install dihentikan (jujur, bukan diam-diam).
  (
    cd "$INSTALL_ROOT/backend"
    set -a; . "$ENV_FILE"; set +a
    "$INSTALL_ROOT/venv/bin/python" manage.py adopt_wg_host \
      || die "adopt_wg_host gagal — pubkey host tidak diadopsi backend (lihat JSON di atas)."
  )
  # Render konfigurasi host (peers desired) untuk ops — TANPA PrivateKey
  # (privat tetap di $WG_DIR/server_private.key milik root; berkas 0600).
  (
    cd "$INSTALL_ROOT/backend"
    set -a; . "$ENV_FILE"; set +a
    "$INSTALL_ROOT/venv/bin/python" manage.py render_wg_config \
      --target "$WG_DIR/rendered" \
      || die "render_wg_config gagal (render peers host)."
    chown -R root:"$RUN_GROUP" "$WG_DIR/rendered"; chmod -R o-rwx "$WG_DIR/rendered"
  )
  log "Pubkey host diadopsi backend; render peers: $WG_DIR/rendered/wg0.conf (tanpa PrivateKey)."
  log "Aktivasi interface tetap langkah ops (§9.13): systemctl enable --now wg-quick@wg0."
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
  # PERBAIKAN: handle_path MENGUPAS prefix /api — backend melayani /api/v1/*
  # penuh, jadi pakai handle (prefix dipertahankan).
  cat > /etc/caddy/Caddyfile <<EOF
# MicroTix — reverse proxy same-origin (API + SPA).
# Ganti \$DOMAIN via 'sudo bash instalasi.sh repair' setelah MT_DOMAIN diisi.
${DOMAIN:-:80} {
        encode gzip
        handle /api/* {
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
  if [ "${MT_ENABLE_RADIUS:-0}" != "1" ]; then
    log "RADIUS nonaktif (MT_ENABLE_RADIUS≠1) — jujur: tidak dikonfigurasi, tidak diklaim siap."
    return
  fi
  log "Mengonfigurasi FreeRADIUS 3.2 (listener 127.0.0.1/WG; reconciler via aplikasi)..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] setup_radius + render konfigurasi"; return; fi
  # Peran daemon + render konfigurasi via management command (sumber sama
  # dengan harness verifikasi test_radius.sh).
  (
    cd "$INSTALL_ROOT/backend"
    set -a; . "$ENV_FILE"; set +a
    export MT_RADIUS_DB_PASSWORD="$(openssl rand -base64 32 | tr -d '\n' | tr '/+' '_-')"
    DATABASE_URL="$MIGRATE_DATABASE_URL" "$INSTALL_ROOT/venv/bin/python" manage.py setup_radius \
      || die "setup_radius gagal (lihat output di atas)."
    "$INSTALL_ROOT/venv/bin/python" manage.py render_radius_config \
      --target /etc/freeradius/3.0/microtix --db-name "$DB_NAME" \
      --db-password "$MT_RADIUS_DB_PASSWORD" --bind-ip 127.0.0.1 \
      --auth-port 1812 --acct-port 1813 \
      || die "render konfigurasi RADIUS gagal."
    chown -R freeradius:freeradius /etc/freeradius/3.0/microtix
    chmod -R o-rwx /etc/freeradius/3.0/microtix
    # Simpan password daemon untuk upgrade (0600, tanpa cetak).
    umask 077
    printf 'MT_RADIUS_DB_PASSWORD=%s\n' "$MT_RADIUS_DB_PASSWORD" > "$ETC_DIR/radius.env"
  )
  systemctl restart freeradius
  touch "$INSTALL_ROOT/.radius-configured"
  log "FreeRADIUS terkonfigurasi (reconciler NAS berjalan via aplikasi; listener loopback/WG)."
}

# ----------------------------------------------------------------------------
# Health checks + onboarding admin
# ----------------------------------------------------------------------------
# Status instalasi final (§9.6): SUCCESS hanya bila seluruh gerbang wajib
# lulus; PARTIAL bila ada prasyarat produksi belum ada (mis. domain/HTTPS);
# BLOCKED/FAILED jujur. Installer TIDAK exit 0 bila gerbang wajib gagal.
INSTALL_STATUS="INSTALL_SUCCESS"
FAIL_REASONS=""
PARTIAL_REASONS=""

gate_fail()    { FAIL_REASONS="$FAIL_REASONS; $1"; INSTALL_STATUS="INSTALL_FAILED"; }
gate_partial() { PARTIAL_REASONS="$PARTIAL_REASONS; $1"; [ "$INSTALL_STATUS" = "INSTALL_SUCCESS" ] && INSTALL_STATUS="INSTALL_PARTIAL"; }

health_checks() {
  log "Health checks (gerbang wajib — gagal = instalasi gagal)..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] /health/live, /health/ready, worker, smoke"; return; fi
  sleep 2
  curl -sf http://127.0.0.1:8300/api/v1/health/live >/dev/null \
    && log "health/live: OK" || gate_fail "health/live gagal (journalctl -u microtix-api -n 50)"
  curl -sf http://127.0.0.1:8300/api/v1/health/ready >/dev/null \
    && log "health/ready: OK (PostgreSQL reachable)" || gate_fail "health/ready gagal (koneksi database)"
  systemctl is-active --quiet microtix-api \
    && log "layanan microtix-api: aktif" || gate_fail "microtix-api tidak aktif"
  systemctl is-active --quiet microtix-worker \
    && log "layanan microtix-worker: aktif" || gate_fail "microtix-worker tidak aktif"
  # Smoke API publik melewati Caddy (domain atau localhost).
  SMOKE_HOST="${MT_DOMAIN:-localhost}"
  curl -skf "https://${SMOKE_HOST}/api/v1/health/live" >/dev/null 2>&1 \
    || curl -sf "http://${SMOKE_HOST}/api/v1/health/live" >/dev/null 2>&1 \
    || curl -sf "http://127.0.0.1/api/v1/health/live" >/dev/null 2>&1 \
    && log "smoke API via proxy: OK" || gate_fail "smoke API via proxy gagal (Caddy)"
  # HTTPS valid hanya bila domain produksi diset (prasyarat beta publik).
  if [ -n "${MT_DOMAIN:-}" ]; then
    curl -sf "https://${MT_DOMAIN}/api/v1/health/live" >/dev/null 2>&1 \
      && log "HTTPS domain: OK (${MT_DOMAIN})" \
      || gate_partial "HTTPS domain belum valid (periksa DNS + sertifikat Caddy)"
  else
    gate_partial "MT_DOMAIN kosong — HTTP :80 saja; BUKAN beta publik (§9.6)"
  fi
  # RADIUS hanya gerbang bila diaktifkan eksplisit.
  if [ "${MT_ENABLE_RADIUS:-0}" = "1" ]; then
    systemctl is-active --quiet freeradius \
      && log "FreeRADIUS: aktif" || gate_fail "FreeRADIUS diminta (MT_ENABLE_RADIUS=1) tetapi tidak aktif"
  else
    log "RADIUS: tidak diaktifkan (opsional pada mode ini)."
  fi
}

admin_onboarding() {
  log "Onboarding administrator platform..."
  if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] membuat admin platform"; return; fi
  if [ -f "$STATE_DIR/.platform-admin-created" ]; then
    log "Admin platform sudah ada — lewati."
    return
  fi
  (
    cd "$INSTALL_ROOT/backend"
    set -a; . "$ENV_FILE"; set +a
    if [ -n "${MT_ADMIN_EMAIL:-}" ] && [ -n "${MT_ADMIN_PASSWORD:-}" ]; then
      # Mode non-interaktif (otomasi) — password dari env, tidak pernah dicetak.
      DJANGO_SUPERUSER_EMAIL="$MT_ADMIN_EMAIL" DJANGO_SUPERUSER_PASSWORD="$MT_ADMIN_PASSWORD" \
        "$INSTALL_ROOT/venv/bin/python" manage.py createsuperuser --noinput
    else
      echo "Buat akun Super Admin platform (akun individual; wajib MFA setelah login):"
      "$INSTALL_ROOT/venv/bin/python" manage.py createsuperuser
    fi
  ) && touch "$STATE_DIR/.platform-admin-created" || warn "Admin belum dibuat — jalankan repair nanti."
}

summary() {
  if [ "$DRY_RUN" -ne 1 ] && [ "$INSTALL_STATUS" = "INSTALL_FAILED" ]; then
    echo
    die "INSTALASI GAGAL — gerbang wajib tidak lulus:${FAIL_REASONS}. Perbaiki lalu jalankan 'sudo bash instalasi.sh repair'."
  fi
  if [ "$DRY_RUN" -ne 1 ] && [ "$INSTALL_STATUS" = "INSTALL_PARTIAL" ]; then
    log "INSTALASI PARSIAL — komponen inti sehat, namun:${PARTIAL_REASONS}."
    log "Instalasi parsial TIDAK dinyatakan siap beta publik (§9.6)."
  fi
  cat <<EOF

================ MicroTix — ringkasan instalasi ================
Status      : $INSTALL_STATUS${FAIL_REASONS}${PARTIAL_REASONS}
Mode        : $MODE
URL aplikasi: ${MT_DOMAIN:-http://localhost} (Caddy same-origin /api)
Lokasi      : $INSTALL_ROOT (backend+venv+web-dist), $ETC_DIR (env), $STORAGE_DIR (penyimpanan privat)
Database    : PostgreSQL 17 '$DB_NAME' (migrator: $DB_MIGRATOR, runtime: $DB_APP — NOBYPASSRLS)
Layanan     : microtix-api (gunicorn 127.0.0.1:8300), microtix-worker (job engine)
Proxy/TLS   : Caddy (HTTPS same-origin /api; sertifikat otomatis bila MT_DOMAIN diset)
WireGuard   : host keypair + $WG_CONF disiapkan (port be2; idempoten);
              aktifkan: systemctl enable --now wg-quick@wg0 — peers ditambah
              reconciler saat router di-enroll via aplikasi
RADIUS      : $( [ "${MT_ENABLE_RADIUS:-0}" = "1" ] && echo "terpasang + dikonfigurasi (listener loopback/WG; NAS via reconciler)" || echo "TIDAK diaktifkan (MT_ENABLE_RADIUS=1 untuk mengaktifkan)" )
Router      : BELUM ada router terhubung — enrollment via aplikasi dengan
              otorisasi Owner (docs/ROUTEROS.md); installer tidak menyentuh router.
Onboarding  : $( [ -f "$STATE_DIR/.platform-admin-created" ] && echo "admin platform dibuat — login lalu aktifkan MFA" || echo "admin belum dibuat — jalankan repair" )
Perintah    : systemctl status microtix-api microtix-worker
              sudo bash instalasi.sh status | doctor | repair | upgrade
              cd backend && bash scripts/test_radius.sh   # verifikasi RADIUS nyata
===============================================================
EOF
  # Exit code jujur (konsolidasi beta-0.1, port be2): gagal → 1,
  # parsial (inti sehat, prasyarat publik belum lengkap) → 3, sukses → 0.
  if [ "$INSTALL_STATUS" = "INSTALL_FAILED" ]; then
    exit 1
  fi
  if [ "$INSTALL_STATUS" = "INSTALL_PARTIAL" ]; then
    exit 3
  fi
  return 0
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
  # WireGuard host: env pubkey diadopsi backend? (read-only --check; tanpa mutasi)
  if [ -f "$ENV_FILE" ] && [ -d "$INSTALL_ROOT/backend" ]; then
    (
      cd "$INSTALL_ROOT/backend"
      set -a; . "$ENV_FILE"; set +a
      "$INSTALL_ROOT/venv/bin/python" manage.py adopt_wg_host --check >/dev/null 2>&1 \
        || warn "WireGuard host: pubkey env belum diadopsi backend (jalankan: manage.py adopt_wg_host) — atau cek koneksi DB."
    )
  fi
  [ "$PREFLIGHT_OK" -eq 1 ] && log "Doctor: semua pemeriksaan utama sehat." || log "Doctor: temuan di atas perlu ditindak."
}

do_upgrade() {
  log "Upgrade (backup + verifikasi → backend+frontend → migrasi → restart → health)..."
  [ -f "$ENV_FILE" ] || die "Belum terinstal."
  if [ "$DRY_RUN" -ne 1 ]; then
    # Backup + VERIFIKASI backup (§9.5) — jangan lanjut bila dump rusak.
    BACKUP_FILE="/var/lib/postgresql/microtix-pre-upgrade-$(date +%Y%m%d%H%M%S).dump"
    su - postgres -c "pg_dump -Fc $DB_NAME > $BACKUP_FILE" || die "pg_dump gagal — upgrade dibatalkan."
    su - postgres -c "pg_restore --list $BACKUP_FILE" >/dev/null \
      || die "backup TIDAK valid (pg_restore --list gagal) — upgrade dibatalkan."
    log "Backup valid: $BACKUP_FILE"
  else
    echo "[dry-run] pg_dump + pg_restore --list (verifikasi backup)"
  fi
  deploy_backend
  build_frontend
  setup_caddy
  setup_wireguard   # idempoten: keypair dipertahankan; pubkey env + adopsi backend + render peers diperbarui
  [ "$DRY_RUN" -ne 1 ] && { systemctl restart microtix-api microtix-worker; health_checks; }
  log "Upgrade selesai."
}

do_repair() {
  log "Repair: restart layanan + reload konfigurasi..."
  [ "$DRY_RUN" -ne 1 ] || { echo "[dry-run] restart api/worker/caddy(+radius)"; return; }
  systemctl restart microtix-api microtix-worker || true
  setup_caddy
  [ "${MT_ENABLE_RADIUS:-0}" = "1" ] && systemctl restart freeradius || true
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
    setup_wireguard
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
