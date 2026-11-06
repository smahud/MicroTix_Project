#!/usr/bin/env bash
# Bootstrap sandbox MicroTix non-root (AGENT_HANDOFF §8; versi in-repo).
# Menghasilkan lingkungan verifikasi lokal: PostgreSQL 17 client+server
# (deb-extract + patch jalur share non-root) dan FreeRADIUS 3.2.7
# (deb-extract) untuk dev_bootstrap.sh + test_radius.sh.
#
# BASE default /home/z/my-project (sandbox Z.ai; bertahan daur-ulang sandbox).
# Override: MT_SANDBOX_BASE=/path/bash setup_env.sh — semua artefak
# (pgbin/, pg_17/, pglib/, frdeb/) dibuat di bawah basis tersebut.
# Skrip idempoten: unduh+ekstrak hanya bila artefak belum ada.
#
# Layout (matches AGENT_HANDOFF §8 "deb-extract + shim share-path"):
#   $BASE/pgbin/pg17        — deb-extracted PostgreSQL 17.11 client+server
#                             binaries; `postgres` dan `initdb` byte-patched
#                             (panjang berkas sama) sehingga SHAREDIR menunjuk
#                             $BASE/pg_17 dan PKGLIBDIR ke $BASE/pglib (build
#                             Debian hard-code /usr/share/postgresql/17 dan
#                             /usr/lib/postgresql/17/lib; tidak bisa direlokasi
#                             tanpa root). Skrip repo tidak diubah.
#   $BASE/pg_17             — share/postgresql/17 (postgres.bki, extension, timezonesets…)
#   $BASE/pglib             — lib/postgresql/17/lib (*.so termasuk plpgsql)
#   $BASE/frdeb/extracted   — FreeRADIUS 3.2.7 deb-extract (harness test_radius.sh)
#
# Catatan: venv backend tidak dibuat di sini — `python3.13 -m venv` bisa
# gagal tanpa paket python3.13-venv; gunakan
# `uv venv .venv --python /usr/bin/python3.13 --seed` lalu dev_bootstrap.sh.
set -euo pipefail
BASE="${MT_SANDBOX_BASE:-/home/z/my-project}"
# Eksplisit agar patcher python (heredoc) selalu melihat basis yang sama.
export MT_SANDBOX_BASE="$BASE"
PGBIN="$BASE/pgbin"
PGVER="17.11-0+deb13u1"
FRV="3.2.7+dfsg-1+deb13u2"
mkdir -p "$PGBIN" "$BASE/frdeb"

echo "== 1. PostgreSQL 17 (deb extract, non-root) =="
if [ ! -x "$PGBIN/pg17/bin/pg_isready" ] || [ ! -f "$BASE/pg_17/postgres.bki" ]; then
  cd "$PGBIN"
  BASEURL="http://deb.debian.org/debian/pool/main/p/postgresql-17"
  for f in "postgresql-17_${PGVER}_amd64.deb" "postgresql-client-17_${PGVER}_amd64.deb" "libpq5_${PGVER}_amd64.deb"; do
    [ -f "$f" ] || curl -fsSL -o "$f" "$BASEURL/$f"
  done
  rm -rf stage pg17 "$BASE/pg_17" "$BASE/pglib"
  mkdir -p stage
  for d in *.deb; do dpkg-deb -x "$d" stage/; done
  mkdir -p pg17/bin pg17/lib
  cp -a stage/usr/lib/postgresql/17/bin/. pg17/bin/
  cp -a stage/usr/lib/x86_64-linux-gnu/. pg17/lib/
  mv stage/usr/share/postgresql/17 "$BASE/pg_17"
  mkdir -p "$BASE/pglib"
  cp -a stage/usr/lib/postgresql/17/lib/. "$BASE/pglib/"
  rm -rf stage
  python3 - <<'EOF'
import os
BASE = os.environ.get("MT_SANDBOX_BASE", "/home/z/my-project")
OLD_SHARE = b"/usr/share/postgresql/17"     # 24 bytes
NEW_SHARE = (BASE + "/pg_17").encode()      # target path
OLD_LIB   = b"/usr/lib/postgresql/17/lib"   # 26 bytes
NEW_LIB   = (BASE + "/pglib").encode()
def patch(data, old, new):
    if len(new) > len(old):
        raise SystemExit(f"path too long: {new!r} > {old!r}")
    out = bytearray(); i = 0; n = 0
    while True:
        j = data.find(old, i)
        if j < 0:
            out += data[i:]; break
        out += data[i:j] + new
        if len(new) < len(old):
            if data[j+len(old):j+len(old)+1] == b"\x00":
                out += b"\x00" * (len(old) - len(new))   # standalone: NUL-pad
            else:
                out += data[j+len(new):j+len(old)]       # embedded: keep old tail bytes
        n += 1
        i = j + len(old)
    return bytes(out), n
for name in ("postgres", "initdb"):
    p = os.path.join("pg17/bin", name)
    data = open(p, 'rb').read()
    orig = len(data)
    data, n1 = patch(data, OLD_SHARE, NEW_SHARE)
    data, n2 = patch(data, OLD_LIB, NEW_LIB)
    assert len(data) == orig, "file length changed"
    open(p, 'wb').write(data)
    print(f"patched {name}: share {n1}x, pkglib {n2}x")
EOF
fi
"$PGBIN/pg17/bin/pg_isready" --version

echo "== 2. FreeRADIUS 3.2 (deb extract, non-root) =="
if [ ! -x "$BASE/frdeb/extracted/usr/sbin/freeradius" ]; then
  cd "$BASE/frdeb"
  BASEURL="http://deb.debian.org/debian/pool/main/f/freeradius"
  for f in "freeradius_${FRV}_amd64.deb" "freeradius-common_${FRV}_all.deb" "freeradius-config_${FRV}_amd64.deb" "libfreeradius3_${FRV}_amd64.deb" "freeradius-utils_${FRV}_amd64.deb" "freeradius-postgresql_${FRV}_amd64.deb"; do
    [ -f "$f" ] || curl -fsSL -o "$f" "$BASEURL/$f" || echo "MISS: $f"
  done
  # runtime libs dari paket sistem (deb-extract non-root): talloc + libpcap + libpq(rlm_sql_postgresql)
  curl -fsSL -O http://deb.debian.org/debian/pool/main/t/talloc/libtalloc2_2.4.0-f2_amd64.deb
  curl -fsSL -O http://deb.debian.org/debian/pool/main/libp/libpcap/libpcap0.8t64_1.11.0-1_amd64.deb
  curl -fsSL -O "http://deb.debian.org/debian/pool/main/p/postgresql-17/libpq5_${PGVER}_amd64.deb"
  mkdir -p extracted
  for d in *.deb; do dpkg-deb -x "$d" extracted/ || echo "EXTRACT FAIL: $d"; done
fi
ls "$BASE/frdeb/extracted/usr/sbin/freeradius" >/dev/null && echo "freeradius OK"
echo "setup_env.sh: done"
