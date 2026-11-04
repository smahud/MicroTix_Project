#!/usr/bin/env bash
# [REVISI AUD-06] LEGACY / AUDIT-ONLY. Jangan jalankan untuk paket v2.1.
# Kontrak pengganti fail-closed ada pada kontrak audit §2. Body lama dipertahankan
# untuk pemeriksaan dokumentasi, bukan bukti bootstrap aman.
# Menempatkan dokumen MicroTix v2.0 (Quality-Ready) ke struktur repository dan
# memverifikasi SHA-256 terhadap sumber/source-manifest_v2_0.md.
# Manifest v1_4 tetap disalin sebagai provenance (tidak dipakai verifikasi).
# Pemakaian: bash bootstrap_docs.sh /jalur/ke/repo   (jalankan dari folder hasil ekstraksi zip)
# Perilaku: non-destruktif (tanpa rm), idempoten, salin tmp+rename, tidak menimpa docs/decisions.md.
set -euo pipefail

REPO="${1:?jalur repository wajib}"
SRC="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="$SRC/sumber/source-manifest_v2_0.md"

[ -f "$MANIFEST" ] || { echo "Jalankan dari folder paket (yang berisi agent/ dan sumber/); manifest v2_0 tidak ditemukan"; exit 1; }
case "$REPO" in /*) ;; *) REPO="$(pwd)/$REPO";; esac
[ -d "$REPO" ] || { echo "Direktori repository tidak ada: $REPO"; exit 1; }

mkdir -p "$REPO/docs/source" "$REPO/docs/quality" "$REPO/docs/audit" \
         "$REPO/docs/adr" "$REPO/docs/runbooks" "$REPO/docs/evidence" "$REPO/docs/contracts" \
         "$REPO/locales/id" "$REPO/locales/en"

copy_atomic() {  # copy_atomic <src> <dst>
  cp -- "$1" "$2.tmp.$$" && mv -- "$2.tmp.$$" "$2"
}

echo "== Verifikasi SHA-256 (manifest v2_0) =="
fail=0
count_ok=0
count_skip=0
while read -r rel sha; do
  [ -n "$rel" ] || continue
  if [ ! -f "$SRC/$rel" ]; then echo "LEWAT $rel (tidak ada di paket)"; count_skip=$((count_skip+1)); continue; fi
  actual="$(sha256sum "$SRC/$rel" | cut -d' ' -f1)"
  if [ "$actual" = "$sha" ]; then echo "OK   $rel"; count_ok=$((count_ok+1));
  else echo "BEDA $rel"; fail=1; fi
done < <(awk -F'|' 'NF>=5 && $2 ~ /^[ \t]*[A-Za-z0-9_.\/-]+\.(md|sh)[ \t]*$/ && $5 ~ /^[ \t]*[0-9a-f]{64}[ \t]*$/ {gsub(/^[ \t]+|[ \t]+$/,"",$2); gsub(/^[ \t]+|[ \t]+$/,"",$5); print $2" "$5}' "$MANIFEST")

[ "$fail" -eq 0 ] || { echo "Ada hash berbeda: telaah sebelum melanjutkan (catat pada manifest v2_0 bagian verifikasi)."; exit 1; }
echo "Verifikasi: $count_ok cocok, $count_skip lewat, 0 beda."

echo "== Penempatan berkas =="
copy_atomic "$SRC/agent/AGENTS_v1_4.md" "$REPO/AGENTS.md"
copy_atomic "$SRC/agent/tugas_v1_5.md"  "$REPO/tugas.md"
for f in "$SRC"/sumber/*.md; do copy_atomic "$f" "$REPO/docs/source/$(basename "$f")"; done
for f in "$SRC"/sumber/quality/*.md; do copy_atomic "$f" "$REPO/docs/quality/$(basename "$f")"; done
for f in "$SRC"/sumber/audit/*.md;  do copy_atomic "$f" "$REPO/docs/audit/$(basename "$f")"; done
if [ ! -f "$REPO/docs/decisions.md" ]; then copy_atomic "$SRC/sumber/decisions_log.md" "$REPO/docs/decisions.md"; fi

echo "== Ringkasan penempatan =="
echo "AGENTS.md, tugas.md            -> root"
echo "sumber/*.md (normatif+manifest)-> docs/source/   (manifest v1_4 = provenance; v2_0 = aktual)"
echo "sumber/quality/*.md            -> docs/quality/"
echo "sumber/audit/*.md              -> docs/audit/"
echo "decisions_log.md               -> docs/decisions.md (hanya bila belum ada; Bagian F milik agent)"
echo "Selesai. Lanjut: buka AGENTS.md dan tugas.md di repository; sebelum pengujian baca docs/quality/."
