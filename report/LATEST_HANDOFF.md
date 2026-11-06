# LATEST_HANDOFF — Kanonis (sesi 2026-11-06 lanjutan 3: M6 billing TK-601 + dokumen TK-109)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` |
| **Commit remote terverifikasi** | **`cb1bf8501bb42352acff04dfef78f849e4a453c7`** (merge PR #4; diverifikasi `git ls-remote` + API 2026-11-06; CI pada merge commit **HIJAU**: backend/frontend/docs semua success — diverifikasi via check-runs; CI pada head PR `4394635` juga hijau) |
| **PR** | #1–#3 (sebelumnya) + **#4 SUDAH MERGED** (tidak ada PR terbuka) |
| Branch sesi (SUDAH MERGED) | `session/2026-11-06-billing-docs` (skeleton `7e46d67` → sub-agent docs `43f328d` → integrasi `beb4fec` → billing `190e2f8` → fix CI `4394635`); sub-branch sub-agent `session/2026-11-06-docs-tk109` (arsip riwayat) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan tunggal tetap Gate A/G (instalasi host Debian 13 nyata root+domain), BUKAN pekerjaan kode |
| CONTRACT.md | Versi `1fff190` (tidak diubah sesi ini; tidak ada amendment) |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata)

1. **TK-109 — dokumen terbit PDF immutable** (`domains.documents`; sub-agent
   worktree terisolasi, diff direview + diintegrasikan orchestrator):
   `IssuedDocument` snapshot (locale/timezone/template_version/values/sha256),
   trigger DB immutability, reprint baca artifact tersimpan + cek sha256
   (T23-I18-02: template v2 tidak mengubah reprint), HTML→PDF **xhtml2pdf
   0.2.28** per ARCHITECTURE §1 (reportlab invariant=1 → byte-deterministik
   terbukti; renderer terbatas jaringan/file DUA lapis; escape nilai; label
   dari katalog i18n; format IDR I18N-03). 24 tes.
2. **TK-601 — mesin invoice internet M6** (`domains.billing`; orchestrator):
   BillingPackage BIL-02 (fixed_monthly/anniversary + prepaid/postpaid +
   due_day clamp + first_period_policy prorata ceil Rp100; anniversary
   non-full DITOLAK jujur); InternetInvoice+lines snapshot harga (issued
   price unchanged — teruji) + **UNIQUE periode** (AC-BIL: dua run scheduler
   hari sama → 1 invoice) + nomor INV via kunci baris tenant; ServiceCharge
   BIL-07 (add-on/diskon + masa berlaku); InternetPayment dua tahap BIL-03
   (bukti ≠ posted; transfer wajib bukti magic-bytes; external_ref dedup
   event bank; alokasi ≤ nilai/≤ sisa; sisa=kredit; partial tidak melunasi;
   **pembayaran tidak menyentuh lifecycle service**); kwitansi RCP (BIL-08)
   terbit saat verify; aging 0-30/31-60/61-90/>90 + not_due; scheduler
   `manage.py issue_due_invoices` (--date/--tenant/--dry-run; tanggal zona
   tenant WIB/WITA/WIT lintas tengah hari teruji; idempoten; catch-up).
   RLS FORCE + FK komposit + PROTECT dua sisi alokasi. Tenant.locale +
   Customer.locale (rantai I18N-01 §2). 79 tes billing.
3. **Fix bug pra-ada**: Makefile PY/MANAGE absolut (make test* sebelumnya
   tidak bisa menjalankan venv — CI tidak terdampak karena memakai pytest
   langsung); **fix CI backend**: instalasi dependensi kini dari pyproject
   (`pip install -e .`) — daftar hardcode ganda membuat CI gagal
   ModuleNotFoundError reportlab saat pertama PR #4 (ditemukan + diperbaiki
   sesi ini; hijau setelahnya).
4. **Verifikasi penuh** (PG 17.11 nyata, peran mtx_migrator/mtx_app):
   backend **355/355** (252 baseline + 103 baru), make test 138 /
   test-integration 217 / test-contract 29, makemigrations --check bersih,
   FreeRADIUS nyata **15/15**, FE tsc/eslint 0 + vitest **42/42** + build
   live OK + build mock DITOLAK (guard utuh), `make e2e` **7/7** (Chromium
   nyata), bash -n instalasi.sh OK, docs check PASS.
5. **Laporan kontrak**:
   `report/orchestrator/20261106T151951Z-billing-m6-tk601-docs-tk109.md`
   (keputusan engineering lengkap + tes dilewati + alasan) +
   `report/documents-dev/20261106T145134Z-tk109-documents.md` (sub-agent).

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (penahan tunggal tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; termasuk memasang timer host `issue_due_invoices` (01:00) — scheduler siap, pemasangan = ops host |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-06-billing-docs` + `session/2026-11-06-docs-tk109` —
  **SUDAH MERGED** (PR #4 → main `cb1bf85`; SHA remote terverifikasi).
  Dipertahankan di remote sebagai arsip riwayat sesi (pola sesi sebelumnya).
- Arsip riwayat (remote): `parallel/beta-be2`, `integration/beta-0.1`,
  `session/2026-11-06-wg-e2e`, `session/2026-11-06-bootstrap-inrepo`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **TK-604 — UI U09/U10** (P2; UI_UX.md §8): konsumsi API billing nyata
   sesi ini (paket/invoices/aging/payments/verify + dokumen PDF) — filter
   periode, verifikasi dana, aktivasi manual TERPISAH, snapshot; perbarui
   kontrak FE (`contracts.ts`) + adapter live + e2e baru.
   **ATAU TK-701 — ledger M7** (P2; FINANCE.md §2/§13/§16, ARCHITECTURE §8):
   prasyarat TK-601 build KINI TERPENUHI — COA/books/periods/journal +
   post_entry SECURITY DEFINER + period lock + immutability + tes bypass
   T12-LED-01/T12-LED-NEG-01 + buku platform dari event sumber M2.
2. TK-602 isolir (default off + simulasi wajib), TK-607 saldo pembuka,
   TK-608 dokumen koreksi (refund/void), TK-609 kolektor (setoran/selisih).
3. Ops host Gate A/G saat host tersedia (termasuk timer `issue_due_invoices`).
4. Follow-up minor: CI job e2e opsional; doctor hint mismatch vs refused
   (F7); perluas spec e2e (alur billing setelah TK-604).

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ cb1bf85 (terverifikasi)
git log --oneline -5
cd backend && bash scripts/dev_bootstrap.sh  # idempoten (butuh MT_PG_BIN bila sandbox baru)
MT_ENV=test .venv/bin/python -m pytest tests -q          # 355 tes (PostgreSQL nyata)
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && cd ../.. && make e2e              # 7/7 browser+backend nyata
python3 docs/tools/check_docs.py && bash -n instalasi.sh
```

Lingkungan sandbox baru: `bash docs/tools/setup_env.sh` (in-repo; basis
default `/home/z/my-project`, override `MT_SANDBOX_BASE`), venv via
`uv venv .venv --python /usr/bin/python3.13 --seed`, pnpm wrapper
`corepack pnpm@12.16.1` (shim: `corepack enable --install-directory
~/.local/bin`), Playwright 1.57 (Chromium 1200). CATATAN sesi ini: curl
tandatangan-waktu-habis bisa menghasilkan .deb terpotong — unduhan PG gagal
1x dengan lzma error; hapus *.deb lalu unduh ulang (retry sukses; skrip
idempoten).

Baca: CONTRACT.md (versi `1fff190`), docs/AGENT_HANDOFF.md §5 (tabel
prioritas sudah diperbarui), docs/progress.md checkpoint teratas,
report/orchestrator/ terbaru, docs/BETA_RELEASE_STATUS.md (fitur aktif M6
core + dokumen dicatat).

## 7. Risiko & keterbatasan yang diketahui

- **Daur ulang sandbox platform menghapus `/home/z/my-project`** — push
  sesegera mungkin (insiden 2026-11-06 pagi); lab dibangun ulang via
  `docs/tools/setup_env.sh`.
- Mutasi router tetap jalur simulator (source=simulator,
  verified_lab=false) — tidak ada klaim perangkat nyata (G1).
- Scheduler invoice BELUM dipasang sebagai timer host (ops Gate A/G) —
  tanpa itu, invoice diterbitkan saat command dijalankan manual; JANGAN
  klaim otomasi harian aktif.
- UI U09/U10 belum ada — endpoint billing aktif tanpa UI (jujur; kontrak FE
  belum memuat tipe billing — dibuat saat TK-604; anti-API-palsu tetap:
  endpoint tak diimplementasi → 404).
- Ledger M7 belum — invoice/payment = catatan sumber (urutan topologis
  TK-701 setelah TK-601 build; T12-LED-* belum dijalankan).
- xhtml2pdf 0.2.28 baru ditambahkan → pantau advisori keamanan versi pin
  (kontrak TK-002 patch-exact; perubahan versi = keputusan terdokumentasi).
- PAT hanya di `.git/config` lokal (tidak pernah di-commit; scan bersih);
  PAT kedaluwarsa = push berikutnya BLOCKED (minta PAT baru).
