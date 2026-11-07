#!/usr/bin/env bash
# Bangun + pasang accel-ppp 1.15.0 — server SSTP manajemen router MicroTix
# (Phase-2, master directive konektivitas). Jalankan sebagai root di host
# gateway Debian 13 SEBELUM 'MT_ENABLE_SSTP=1 bash instalasi.sh install'.
#
# Mengapa build dari sumber: accel-ppp TIDAK ada di repo resmi Debian
# (permintaan pengemasan resmi masih terbuka); satu-satunya jalur yang dapat
# diverifikasi = tarball rilis resmi GitHub yang dipin SHA-256. Tidak ada
# repo pihak-ketiga yang dipercaya untuk daemon keamanan.
#
# Versi dipin: 1.15.0 (rilis 2026-10-29; sertifikat GPG terverifikasi di
# GitHub). 1.15.0 >= 1.13.0 diperlukan karena opsi [sstp] ssl-protocol +
# perbaikan keamanan SSTP MITM hadir pada 1.13.0 (changelog rilis).
#
# Depedensi (Debian 13): build-essential cmake libssl-dev libpcre2-dev
# (README resmi 1.15.0; header kernel TIDAK diperlukan — modul kernel
# PPPoEQ/IPoE/vlan_mon tidak dipakai MicroTix; driver ctrl/sstp terpasang
# bawaan build default: accel-pppd/ctrl/CMakeLists.txt ADD_SUBDIRECTORY(sstp)).
#
# Idempoten: unduhan + build di direktori kerja sementara; binary terpasang
# /usr/local/sbin/accel-pppd (dipakai unit microtix-sstp.service installer).
set -euo pipefail

VERSION="1.15.0"
SHA256="408a7c02d25633ee2370887b67338c722858548d5431a7490c2af7774856e279"
URL="https://github.com/accel-ppp/accel-ppp/archive/refs/tags/${VERSION}.tar.gz"
PREFIX="/usr/local"

[ "$(id -u)" -eq 0 ] || { echo "build_accel_ppp.sh: jalankan sebagai root (sudo)." >&2; exit 1; }

echo "== accel-ppp ${VERSION} (SSTP server MicroTix Phase-2) =="
if [ -x "$PREFIX/sbin/accel-pppd" ] && "$PREFIX/sbin/accel-pppd" -V 2>/dev/null | grep -q "${VERSION}"; then
  echo "accel-pppd ${VERSION} sudah terpasang di $PREFIX/sbin/accel-pppd — tidak dibangun ulang."
  exit 0
fi

echo "1/5 Dependensi build (Debian 13 resmi)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential cmake libssl-dev libpcre2-dev ca-certificates curl

WORK="$(mktemp -d /tmp/accel-ppp-build.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

echo "2/5 Unduh tarball rilis resmi (dipin SHA-256)..."
curl -fsSL -o "$WORK/accel-ppp.tar.gz" "$URL"
echo "${SHA256}  $WORK/accel-ppp.tar.gz" | sha256sum -c - || {
  echo "GAGAL: checksum tarball accel-ppp ${VERSION} tidak cocok — unduhan ditolak." >&2
  exit 1
}

echo "3/5 Ekstrak..."
tar -xzf "$WORK/accel-ppp.tar.gz" -C "$WORK"
SRC="$WORK/accel-ppp-${VERSION}"

echo "4/5 Build (out-of-tree, Release)..."
cmake -S "$SRC" -B "$WORK/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$WORK/build" -j"$(nproc)"

echo "5/5 Pasang ke $PREFIX..."
cmake --install "$WORK/build"

"$PREFIX/sbin/accel-pppd" -V
echo "SELESAI: $PREFIX/sbin/accel-pppd — lanjutkan: MT_ENABLE_SSTP=1 sudo bash instalasi.sh install"
