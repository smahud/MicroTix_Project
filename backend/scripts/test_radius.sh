#!/usr/bin/env bash
# Harness verifikasi RADIUS NYATA MicroTix (RADIUS.md §13: T16/T19/T20/T21).
#
# Menjalankan daemon FreeRADIUS 3.2 nyata (binary ekstraksi deb, non-root)
# dengan proyeksi radius.* pada PostgreSQL nyata + facade tenant-aware, lalu
# menguji lewat radclient nyata. Tanpa tiruan: daemon gagal start → BLOCKED
# exit 2 (dengan bukti log); uji gagal → exit 1; semua lulus → exit 0.
#
# Topologi (loopback non-root, §4 resolusi tenant dari ALAMAT SUMBUNGA paket):
#   daemon A: 127.0.0.1:18120 auth / 18121 acct, klien = 127.0.0.2 (tenant A)
#   daemon B: 127.0.0.1:18122 auth / 18123 acct, klien = 127.0.0.3 (tenant B)
#   relay UDP (domains/radius/harness/udp_relay.py) meneruskan paket radclient
#   dengan alamat sumber 127.0.0.2/127.0.0.3 — radclient sendiri tidak punya
#   opsi bind sumber. NAS-IP-Address payload sengaja DECOY (127.0.0.99) untuk
#   membuktikan resolusi tenant TIDAK dari atribut payload (§4).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # .../backend
MT_PG_BIN="${MT_PG_BIN:-/home/z/my-project/pgbin/pg17}"
FR_ROOT="${MT_FREERADIUS_ROOT:-/home/z/my-project/frdeb/extracted}"
FREERADIUS_BIN="${MT_FREERADIUS_BIN:-$FR_ROOT/usr/sbin/freeradius}"
RADCLIENT_BIN="${MT_RADCLIENT_BIN:-$FR_ROOT/usr/bin/radclient}"
FR_DICT="${MT_FREERADIUS_DICT:-$FR_ROOT/usr/share/freeradius}"
PGHOST="${MT_PGHOST:-127.0.0.1}"
PGPORT="${MT_PGPORT:-55432}"
PY="$ROOT/.venv/bin/python"
MANAGE=("$PY" "$ROOT/manage.py")

# Library PG + FreeRADIUS sama-sama dibutuhkan proses anak.
export LD_LIBRARY_PATH="$MT_PG_BIN/lib:$FR_ROOT/usr/lib/x86_64-linux-gnu:$FR_ROOT/usr/lib/freeradius:${LD_LIBRARY_PATH:-}"

PSQL="$MT_PG_BIN/bin/psql -h $PGHOST -p $PGPORT -U postgres -v ON_ERROR_STOP=1"
PGDATA="$ROOT/pgdata"

WORK="$(mktemp -d /tmp/mtx-radius-harness.XXXXXX)"
PIDS=()
PASS=0
FAIL=0
FAILED_CASES=()

cleanup() {
  local pid
  for pid in ${PIDS[@]+"${PIDS[@]}"}; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

# Proses run lama yang masih memegang port harness (daemon/relay yatim dari
# eksekusi sebelumnya) harus mati dulu — bind gagal kalau masih hidup.
pkill -f "domains.radius.harness.udp_relay" >/dev/null 2>&1 || true
pkill -f "$FREERADIUS_BIN" >/dev/null 2>&1 || true
sleep 0.5

say() { printf '%s\n' "$*"; }
result() { # result PASS|FAIL <id> <deskripsi>
  if [ "$1" = "PASS" ]; then
    PASS=$((PASS + 1)); say "PASS [$2] $3"
  else
    FAIL=$((FAIL + 1)); FAILED_CASES+=("[$2] $3"); say "FAIL [$2] $3"
  fi
}
blocked() { say "BLOCKED: $*"; exit 2; }

# ---------------------------------------------------------------------------
# 1. PostgreSQL hidup (pola backend/scripts/dev_bootstrap.sh)

if ! "$MT_PG_BIN/bin/pg_isready" -h "$PGHOST" -p "$PGPORT" >/dev/null 2>&1; then
  [ -f "$PGDATA/PG_VERSION" ] || blocked "PGDATA $PGDATA tidak ada — jalankan dev_bootstrap.sh dulu"
  mkdir -p "$ROOT/pgrun"
  "$MT_PG_BIN/bin/pg_ctl" -D "$PGDATA" \
    -o "-p $PGPORT -k $ROOT/pgrun -h 127.0.0.1 -c listen_addresses=127.0.0.1" \
    -l "$PGDATA/server.log" start >/dev/null 2>&1 || blocked "pg_ctl gagal start (lihat $PGDATA/server.log)"
  sleep 2
  "$MT_PG_BIN/bin/pg_isready" -h "$PGHOST" -p "$PGPORT" >/dev/null 2>&1 \
    || blocked "PostgreSQL tidak merespons setelah start"
fi

# Env Django dev (DATABASE_URL app; migrator untuk migrasi).
if [ -f "$ROOT/.env" ]; then
  set -a; . "$ROOT/.env"; set +a
fi
export MT_ENV="${MT_ENV:-dev}"
export DATABASE_URL="${DATABASE_URL:-postgresql://mtx_app@$PGHOST:$PGPORT/microtix}"
export MIGRATE_DATABASE_URL="${MIGRATE_DATABASE_URL:-postgresql://mtx_migrator@$PGHOST:$PGPORT/microtix}"
DB_NAME="$(printf '%s' "$DATABASE_URL" | awk -F/ '{print $NF}')"

[ -x "$FREERADIUS_BIN" ] || blocked "binary freeradius tidak ditemukan: $FREERADIUS_BIN"
[ -x "$RADCLIENT_BIN" ] || blocked "binary radclient tidak ditemukan: $RADCLIENT_BIN"

# ---------------------------------------------------------------------------
# 2. Peran daemon mtx_radius (cluster, via superuser trust) + password acak

RPASS="mtxh-$(head -c 24 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 28)"
$PSQL -d postgres -c "DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mtx_radius') THEN
    CREATE ROLE mtx_radius LOGIN;
  END IF;
END \$\$;" >/dev/null || blocked "tidak dapat membuat peran mtx_radius (butuh superuser trust)"
$PSQL -d postgres -c "ALTER ROLE mtx_radius LOGIN PASSWORD '$RPASS';
  ALTER ROLE mtx_radius SET search_path = radius, public;" >/dev/null \
  || blocked "tidak dapat mengatur password/search_path mtx_radius"
say "== peran daemon mtx_radius siap (password di $WORK saja, tidak pernah dicetak)"

# ---------------------------------------------------------------------------
# 3. Migrasi + privilege (migrator; grant_runtime public + setup_radius radius)

DATABASE_URL="$MIGRATE_DATABASE_URL" "${MANAGE[@]}" migrate --noinput >/dev/null 2>&1 \
  || blocked "migrate gagal sebagai migrator (lihat error di atas dengan menghapus >/dev/null)"
DATABASE_URL="$MIGRATE_DATABASE_URL" "${MANAGE[@]}" grant_runtime >/dev/null \
  || blocked "grant_runtime gagal"
DATABASE_URL="$MIGRATE_DATABASE_URL" "${MANAGE[@]}" setup_radius >"$WORK/setup_radius.json" \
  || { cat "$WORK/setup_radius.json" 2>/dev/null || true; blocked "setup_radius gagal"; }
grep -q '"status": "ok"' "$WORK/setup_radius.json" 2>/dev/null \
  || grep -q '"grant_daemon", "status": "ok"' "$WORK/setup_radius.json" \
  || blocked "grant daemon tidak ok: $(cat "$WORK/setup_radius.json")"

# ---------------------------------------------------------------------------
# 4. Seed fixture uji (app role) — dua tenant, username sama lintas tenant

SEED_JSON="$("${MANAGE[@]}" seed_radius_check 2>"$WORK/seed.err")" \
  || { cat "$WORK/seed.err" >&2; blocked "seed_radius_check gagal"; }
eval "$(printf '%s' "$SEED_JSON" | "$PY" -c '
import json, shlex, sys
d = json.load(sys.stdin)
a, b = d["tenants"]["smoke-rad-a"], d["tenants"]["smoke-rad-b"]
out = {
    "TENANT_A_ID": a["tenant_id"], "NAS_A": a["nas_ip"], "SECRET_A": a["nas_secret"],
    "TENANT_B_ID": b["tenant_id"], "NAS_B": b["nas_ip"], "SECRET_B": b["nas_secret"],
}
for k, v in out.items():
    print(f"{k}={shlex.quote(str(v))}")
')" || blocked "tidak dapat mem-parse keluaran seed_radius_check"
# Kunci identitas sesi diderivasi facade: host(NAS) ':' Acct-Session-Id
# (Acct-Unique-Session-Id 3.2 = atribut internal, tidak pernah di kawat).
SK1="$NAS_A:sess-t21-a1"
say "== seed OK: tenant A ($NAS_A) + tenant B ($NAS_B), username sama 'budi.santoso'"

# ---------------------------------------------------------------------------
# 5. Render bundle konfigurasi dua instance (klien per-tenant via --nas-ip)

"${MANAGE[@]}" render_radius_config --target "$WORK/instA" \
  --db-name "$DB_NAME" --db-password "$RPASS" \
  --auth-port 18120 --acct-port 18121 --nas-ip "$NAS_A" >"$WORK/renderA.json" \
  || blocked "render instance A gagal: $(cat "$WORK/renderA.json" 2>/dev/null || true)"
"${MANAGE[@]}" render_radius_config --target "$WORK/instB" \
  --db-name "$DB_NAME" --db-password "$RPASS" \
  --auth-port 18122 --acct-port 18123 --nas-ip "$NAS_B" >"$WORK/renderB.json" \
  || blocked "render instance B gagal: $(cat "$WORK/renderB.json" 2>/dev/null || true)"

# ---------------------------------------------------------------------------
# 6. Validasi konfigurasi dengan binary terpinned (freeradius -C)

for inst in instA instB; do
  if ! "$FREERADIUS_BIN" -C -d "$WORK/$inst" -D "$FR_DICT" -l stdout \
      >"$WORK/$inst.check.log" 2>&1; then
    blocked "freeradius -C gagal untuk $inst:"$'\n'"$(grep -vE 'Info:' "$WORK/$inst.check.log" | head -20)"
  fi
done
say "== freeradius -C lulus untuk kedua instance"

# ---------------------------------------------------------------------------
# 7. Jalankan relay UDP (sumber /32 per tenant) + dua daemon

start_bg() { # start_bg <logfile> <cmd...>
  local log="$1"; shift
  "$@" >"$log" 2>&1 &
  PIDS+=("$!")
}
cd "$ROOT"
start_bg "$WORK/relayA-auth.log" "$PY" -m domains.radius.harness.udp_relay \
  --listen "$NAS_A:18120" --source "$NAS_A" --target 127.0.0.1:18120
start_bg "$WORK/relayA-acct.log" "$PY" -m domains.radius.harness.udp_relay \
  --listen "$NAS_A:18121" --source "$NAS_A" --target 127.0.0.1:18121
start_bg "$WORK/relayB-auth.log" "$PY" -m domains.radius.harness.udp_relay \
  --listen "$NAS_B:18122" --source "$NAS_B" --target 127.0.0.1:18122
start_bg "$WORK/relayB-acct.log" "$PY" -m domains.radius.harness.udp_relay \
  --listen "$NAS_B:18123" --source "$NAS_B" --target 127.0.0.1:18123
start_bg "$WORK/daemonA.log" "$FREERADIUS_BIN" -f -l stdout -d "$WORK/instA" -D "$FR_DICT"
start_bg "$WORK/daemonB.log" "$FREERADIUS_BIN" -f -l stdout -d "$WORK/instB" -D "$FR_DICT"
sleep 1

# Radclient helper: cetak perintah bukti + simpan keluaran.
RC_OUT=""
rad_run() { # rad_run <dest> <command> <secret> <attrfile>
  say "  \$ radclient -D \$FR_DICT $1 $2 '***' -f $(basename "$4")"
  RC_OUT="$("$RADCLIENT_BIN" -x -t 2 -r 1 -D "$FR_DICT" "$1" "$2" "$3" -f "$4" 2>&1 || true)"
}
rad_expect_accept() { printf '%s' "$RC_OUT" | grep -q "Received Access-Accept"; }
rad_expect_reject() { printf '%s' "$RC_OUT" | grep -q "Received Access-Reject"; }
rad_no_reply()      { ! printf '%s' "$RC_OUT" | grep -qE "Received Access-(Accept|Reject)"; }
sql_scalar() { $PSQL -d "$DB_NAME" -tA -c "$1"; }

# ---------------------------------------------------------------------------
# 8. Readiness — daemon harus menjawab (bukan sekadar hidup)

cat >"$WORK/auth-ok.txt" <<'EOF'
User-Name = "budi.santoso"
User-Password = "pw-check-123456"
Message-Authenticator = 0x00
NAS-IP-Address = 127.0.0.99
EOF

READY=0
for _ in $(seq 1 30); do
  if ! kill -0 "${PIDS[${#PIDS[@]}-2]}" 2>/dev/null || ! kill -0 "${PIDS[${#PIDS[@]}-1]}" 2>/dev/null; then
    blocked "daemon mati saat startup:"$'\n'"$(tail -20 "$WORK/daemonA.log")"
  fi
  RC_OUT="$("$RADCLIENT_BIN" -x -t 1 -r 1 -D "$FR_DICT" "$NAS_A:18120" auth "$SECRET_A" -f "$WORK/auth-ok.txt" 2>&1 || true)"
  if printf '%s' "$RC_OUT" | grep -q "Received Access-Accept"; then READY=1; break; fi
  sleep 0.5
done
[ "$READY" = 1 ] || blocked "daemon tidak menjawab auth dalam 15s:"$'\n'"$(tail -30 "$WORK/daemonA.log")"
say "== daemon A+B siap (Access-Accept pertama diterima)"

# ---------------------------------------------------------------------------
# 9. Baterai uji (RADIUS.md §13)

# --- T16: PAP valid → Accept + atribut rate dari paket tenant A
rad_run "$NAS_A:18120" auth "$SECRET_A" "$WORK/auth-ok.txt"
if rad_expect_accept; then
  if printf '%s' "$RC_OUT" | grep -q 'Mikrotik-Rate-Limit = "20M/10M"'; then
    result PASS T16 "PAP valid → Access-Accept + Mikrotik-Rate-Limit 20M/10M (paket tenant A)"
  else
    result FAIL T16 "Access-Accept tanpa Mikrotik-Rate-Limit 20M/10M: $(printf '%s' "$RC_OUT" | grep -A20 Received | tr '\n' ';')"
  fi
else
  result FAIL T16 "auth valid tidak Accept: $(printf '%s' "$RC_OUT" | tail -3 | tr '\n' ' ')"
fi

# --- T16: password salah → Reject
cat >"$WORK/auth-bad.txt" <<'EOF'
User-Name = "budi.santoso"
User-Password = "password-salah-total"
Message-Authenticator = 0x00
NAS-IP-Address = 127.0.0.99
EOF
rad_run "$NAS_A:18120" auth "$SECRET_A" "$WORK/auth-bad.txt"
if rad_expect_reject; then result PASS T16 "password salah → Access-Reject"
else result FAIL T16 "password salah tidak Reject: $(printf '%s' "$RC_OUT" | tail -3 | tr '\n' ' ')"; fi

# --- T20: akun suspended → Reject (Auth-Type := Reject, bukan password)
cat >"$WORK/auth-susp.txt" <<'EOF'
User-Name = "tunda.user"
User-Password = "pw-tunda-123456"
Message-Authenticator = 0x00
NAS-IP-Address = 127.0.0.99
EOF
rad_run "$NAS_A:18120" auth "$SECRET_A" "$WORK/auth-susp.txt"
if rad_expect_reject; then result PASS T20 "akun suspended ditolak walau password benar"
else result FAIL T20 "suspended tidak Reject: $(printf '%s' "$RC_OUT" | tail -3 | tr '\n' ' ')"; fi

# --- T19: username sama via instance B (tenant B) → Accept data tenant B
cat >"$WORK/auth-b.txt" <<'EOF'
User-Name = "budi.santoso"
User-Password = "pw-other-654321"
Message-Authenticator = 0x00
NAS-IP-Address = 127.0.0.99
EOF
rad_run "$NAS_B:18122" auth "$SECRET_B" "$WORK/auth-b.txt"
if rad_expect_accept && printf '%s' "$RC_OUT" | grep -q 'Mikrotik-Rate-Limit = "50M/50M"'; then
  result PASS T19 "username sama via NAS tenant B → Accept + rate tenant B (50M/50M)"
else
  result FAIL T19 "NAS tenant B tidak melayani data tenant B: $(printf '%s' "$RC_OUT" | tail -3 | tr '\n' ' ')"
fi

# --- T19: password tenant A via instance B → Reject (bukan kebocoran silang)
cat >"$WORK/auth-b-wrong.txt" <<'EOF'
User-Name = "budi.santoso"
User-Password = "pw-check-123456"
Message-Authenticator = 0x00
NAS-IP-Address = 127.0.0.99
EOF
rad_run "$NAS_B:18122" auth "$SECRET_B" "$WORK/auth-b-wrong.txt"
if rad_expect_reject; then result PASS T19 "password tenant A ditolak oleh tenant B (isolasi)"
else result FAIL T19 "password tenant A diterima tenant B — KEBOCORAN TENANT"; fi

# --- T21: accounting Start → Interim → Stop pada port acct + verifikasi DB
cat >"$WORK/acct-start.txt" <<EOF
User-Name = "budi.santoso"
Acct-Status-Type = Start
Acct-Session-Id = "sess-t21-a1"
Acct-Unique-Session-Id = "t21a1-0001"
Acct-Delay-Time = 0
Acct-Session-Time = 0
Acct-Input-Octets = 0
Acct-Output-Octets = 0
NAS-IP-Address = 127.0.0.99
Framed-IP-Address = 10.7.0.5
EOF
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-start.txt"
if printf '%s' "$RC_OUT" | grep -q "Received Accounting-Response"; then
  result PASS T21 "Accounting Start → Accounting-Response"
else
  result FAIL T21 "Start tidak dijawab: $(printf '%s' "$RC_OUT" | tail -3 | tr '\n' ' ')"
fi
ROW_OK="$(sql_scalar "SELECT (tenant_id = '$TENANT_A_ID'::uuid) AND acctstoptime IS NULL AND acctinputoctets = 0 AND username = 'budi.santoso' FROM radius.radacct WHERE acctuniqueid = '$SK1'")"
if [ "$ROW_OK" = "t" ]; then result PASS T21 "radacct: baris Start tenant A, sesi terbuka, decoy NAS-IP diabaikan"
else result FAIL T21 "radacct Start tidak sesuai (got: $ROW_OK)"; fi

# Interim dengan counter naik; lalu interim LAGI dengan counter turun (monotonik)
cat >"$WORK/acct-interim.txt" <<EOF
User-Name = "budi.santoso"
Acct-Status-Type = Interim-Update
Acct-Session-Id = "sess-t21-a1"
Acct-Unique-Session-Id = "t21a1-0001"
Acct-Delay-Time = 0
Acct-Session-Time = 300
Acct-Input-Octets = 1000000
Acct-Output-Octets = 2000000
NAS-IP-Address = 127.0.0.99
Framed-IP-Address = 10.7.0.5
EOF
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-interim.txt"
INTERIM_OK="$(sql_scalar "SELECT acctinputoctets = 1000000 AND acctoutputoctets = 2000000 AND acctstoptime IS NULL FROM radius.radacct WHERE acctuniqueid = '$SK1'")"
if printf '%s' "$RC_OUT" | grep -q "Received Accounting-Response" && [ "$INTERIM_OK" = "t" ]; then
  result PASS T21 "Interim memperbarui counter (in=1000000, out=2000000)"
else
  result FAIL T21 "Interim tidak memperbarui counter (db: $INTERIM_OK)"
fi
sed -e 's/Acct-Input-Octets = 1000000/Acct-Input-Octets = 1000/' \
    -e 's/Acct-Output-Octets = 2000000/Acct-Output-Octets = 2000/' \
    "$WORK/acct-interim.txt" > "$WORK/acct-interim-old.txt"
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-interim-old.txt"
MONO_OK="$(sql_scalar "SELECT acctinputoctets = 1000000 AND acctoutputoctets = 2000000 FROM radius.radacct WHERE acctuniqueid = '$SK1'")"
if [ "$MONO_OK" = "t" ]; then result PASS T21 "Interim basi (counter turun) diabaikan — monotonik"
else result FAIL T21 "Counter mundur diterima (db: $MONO_OK)"; fi

cat >"$WORK/acct-stop.txt" <<EOF
User-Name = "budi.santoso"
Acct-Status-Type = Stop
Acct-Session-Id = "sess-t21-a1"
Acct-Unique-Session-Id = "t21a1-0001"
Acct-Delay-Time = 0
Acct-Session-Time = 600
Acct-Input-Octets = 1500000
Acct-Output-Octets = 2500000
Acct-Terminate-Cause = User-Request
NAS-IP-Address = 127.0.0.99
Framed-IP-Address = 10.7.0.5
EOF
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-stop.txt"
STOP_OK="$(sql_scalar "SELECT acctstoptime IS NOT NULL AND acctterminatecause = 'User-Request' AND acctinputoctets = 1500000 FROM radius.radacct WHERE acctuniqueid = '$SK1'")"
if printf '%s' "$RC_OUT" | grep -q "Received Accounting-Response" && [ "$STOP_OK" = "t" ]; then
  result PASS T21 "Stop menutup sesi + cause User-Request + counter akhir"
else
  result FAIL T21 "Stop tidak menutup sesi dengan benar (db: $STOP_OK)"
fi

# Start ulang (retransmit) SETELAH Stop tidak membuka kembali sesi (§8)
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-start.txt"
NOREOPEN="$(sql_scalar "SELECT acctstoptime IS NOT NULL FROM radius.radacct WHERE acctuniqueid = '$SK1'")"
if printf '%s' "$RC_OUT" | grep -q "Received Accounting-Response" && [ "$NOREOPEN" = "t" ]; then
  result PASS T21 "Start terlambat setelah Stop tidak membuka ulang sesi"
else
  result FAIL T21 "Late Start membuka ulang sesi (db: $NOREOPEN)"
fi

# --- T21: Simultaneous-Use=1 — sesi kedua ditolak saat sesi pertama terbuka
cat >"$WORK/acct-start2.txt" <<EOF
User-Name = "budi.santoso"
Acct-Status-Type = Start
Acct-Session-Id = "sess-t21-a2"
Acct-Unique-Session-Id = "t21a2-0002"
Acct-Delay-Time = 0
Acct-Session-Time = 0
Acct-Input-Octets = 0
Acct-Output-Octets = 0
NAS-IP-Address = 127.0.0.99
Framed-IP-Address = 10.7.0.6
EOF
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-start2.txt"
printf '%s' "$RC_OUT" | grep -q "Received Accounting-Response" \
  || result FAIL T21 "Start sesi kedua tidak dijawab"
S2_OPEN="$(sql_scalar "SELECT acctstoptime IS NULL AND username = 'budi.santoso' FROM radius.radacct WHERE acctuniqueid = '$NAS_A:sess-t21-a2'")"
[ "$S2_OPEN" = "t" ] || result FAIL T21 "sesi kedua tidak tercatat terbuka sebelum uji Simultaneous-Use (db: $S2_OPEN)"
rad_run "$NAS_A:18120" auth "$SECRET_A" "$WORK/auth-ok.txt"
if rad_expect_reject; then
  result PASS T21 "Simultaneous-Use=1: auth saat sesi terbuka lain → Reject"
else
  result FAIL T21 "Simultaneous-Use tidak ditegakkan (auth kedua lolos): $(printf '%s' "$RC_OUT" | tail -3 | tr '\n' ' ')"
fi
cat >"$WORK/acct-stop2.txt" <<EOF
User-Name = "budi.santoso"
Acct-Status-Type = Stop
Acct-Session-Id = "sess-t21-a2"
Acct-Unique-Session-Id = "t21a2-0002"
Acct-Delay-Time = 0
Acct-Session-Time = 60
Acct-Input-Octets = 500
Acct-Output-Octets = 500
Acct-Terminate-Cause = User-Request
NAS-IP-Address = 127.0.0.99
EOF
rad_run "$NAS_A:18121" acct "$SECRET_A" "$WORK/acct-stop2.txt"
printf '%s' "$RC_OUT" | grep -q "Received Accounting-Response" \
  || result FAIL T21 "Stop sesi kedua tidak dijawab"

# --- T16 (persistensi): matikan daemon A, start ulang, auth tetap Accept
DAEMON_A_PID="${PIDS[${#PIDS[@]}-2]}"
kill "$DAEMON_A_PID" >/dev/null 2>&1 || true
sleep 1
start_bg "$WORK/daemonA-restart.log" "$FREERADIUS_BIN" -f -l stdout -d "$WORK/instA" -D "$FR_DICT"
sleep 1
RESTART_OK=0
for _ in $(seq 1 20); do
  RC_OUT="$("$RADCLIENT_BIN" -x -t 1 -r 1 -D "$FR_DICT" "$NAS_A:18120" auth "$SECRET_A" -f "$WORK/auth-ok.txt" 2>&1 || true)"
  if printf '%s' "$RC_OUT" | grep -q "Received Access-Accept"; then RESTART_OK=1; break; fi
  sleep 0.5
done
if [ "$RESTART_OK" = 1 ]; then
  result PASS T16 "restart daemon: state DB bertahan, auth ulang → Accept"
else
  result FAIL T16 "auth gagal setelah restart daemon: $(tail -5 "$WORK/daemonA-restart.log" | tr '\n' ' ')"
fi

# --- T16 (keamanan): secret salah → tidak ada jawaban valid (secure discard)
rad_run "$NAS_A:18120" auth "secret-yang-salah" "$WORK/auth-ok.txt"
if rad_no_reply; then result PASS T16 "secret NAS salah → tidak ada balasan valid (secure discard)"
else result FAIL T16 "secret salah tetap dijawab: $(printf '%s' "$RC_OUT" | tail -2 | tr '\n' ' ')"; fi

# --- radpostauth terisi (bukti jalur post-auth; tanpa password — §12)
PA_OK="$(sql_scalar "SELECT count(*) >= 3 FROM radius.radpostauth WHERE tenant_id = '$TENANT_A_ID'::uuid AND username IN ('budi.santoso','tunda.user') AND reply IN ('Access-Accept','Access-Reject')")"
if [ "$PA_OK" = "t" ]; then result PASS T16 "radpostauth terisi (hasil auth per tenant, tanpa password)"
else result FAIL T21 "radpostauth tidak terisi jalur facade"; fi

# ---------------------------------------------------------------------------
# 10. Ringkasan

say ""
say "=========================================="
say "RADIUS harness: PASS $PASS/$((PASS+FAIL))  (gagal: $FAIL)"
if [ "$FAIL" -gt 0 ]; then
  say "Kasus gagal:"
  for c in ${FAILED_CASES[@]+"${FAILED_CASES[@]}"}; do say "  - $c"; done
  say "Log daemon: $WORK/daemonA.log $WORK/daemonB.log"
  exit 1
fi
say "SEMUA UJI RADIUS NYATA LULUS (T16/T19/T20/T21)"
exit 0
