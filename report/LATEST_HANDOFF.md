# LATEST_HANDOFF — Kanonis (sesi 2026-11-06 lanjutan 4: TK-604 UI billing U09/U10)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` |
| **Commit remote terverifikasi** | **`62595f4eb5eeca5e0306c7667ff0dc7797b2b0e2`** (handoff lanjutan 3; diverifikasi `git ls-remote` + API sesi ini; CI hijau; 0 PR terbuka saat mulai) |
| **PR sesi ini** | `session/2026-11-06-tk604-billing-ui` → PR (lihat §5 untuk SHA merge setelah diverifikasi) — TK-604 UI U09/U10 + kursor billing + field service akun + seed_billing_e2e |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan tunggal tetap Gate A/G (instalasi host Debian 13 nyata root+domain), BUKAN pekerjaan kode |
| CONTRACT.md | Versi `1fff190` (tidak diubah sesi ini; tidak ada amendment) |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata)

1. **TK-604 — U09 Tagihan dan Pembayaran** (`features/billing/BillingPage.tsx`):
   tiga tab Invoice·Pengajuan (submitted/ditolak)·Pembayaran terverifikasi;
   periode filter selalu terlihat; strip aging 5 bucket; catat penerimaan
   (tunai/transfer/e-wallet/kolektor; bukti wajib transfer/e-wallet base64
   ≤5 MiB); verifikasi dana dua tahap + editor alokasi (≤ payment, ≤ sisa;
   sisa = "Saldo kredit belum dialokasikan"); tolak beralasan; PDF
   invoice/kwitansi same-origin; partial menampilkan sisa; banner pasca-
   verifikasi "N layanan menunggu aktivasi" + CTA U10 (jumlah = kandidat
   eligible terkini).
2. **TK-604 — U10 Aktivasi** (`features/activation/ActivationPage.tsx`):
   kandidat akun suspended + kelayakan tagihan NYATA (`lib/billing-eligibility.ts`
   — tanpa tertunggak + pernah lunas; `fetchAllPages` maks 10×200); snapshot
   konfirmasi (N layak/M tidak); validasi kondisi TERBARU per item sebelum
   PATCH (refetch akun+invoice); item asing/berubah BLOK ITEM ITU SAJA —
   keberhasilan tidak diurungkan (e2e: "1 berhasil, 1 diblokir"); hasil per
   item + retry item belum berhasil; label jujur router non-otoritatif
   "Belum dijamin di router ini" (router tak dikenal ≠ dijamin). Aktivasi
   SELALU manual terpisah (PRODUCT §13) — tidak ada job engine baru.
3. **Backend additif**: `radius_account_row` + `service_id/service_code/
   customer_name`; kursor masuk DITERAPKAN pada `/invoices` + `/payments`
   (pra-ada: diabaikan — halaman 2 tak terjangkau; +4 tes); BARU
   `seed_billing_e2e` (tenant ketiga "RT Net Billing Demo (e2e)" via jalur
   services nyata; reset state-mutabel antar-run; bukti immutable tak
   disentuh — percobaan delete tenant terbukti diblokir FK audit + trigger).
4. **Integrasi FE**: contracts.ts + 9 metode ApiClient live+mock paritas
   (mock activate/suspend → `services.activate` + idempoten paritas 204);
   rute `/billing`+`/activation`; release-flag billing+activation → true;
   tab Tagihan CustomerDetailPage diisi; kolom payment/isolation
   CustomersPage tone benar; i18n +134 kunci (1042, paritas penuh).
5. **Verifikasi penuh** (PG 17.11 nyata): backend **359/355+4**,
   makemigrations --check bersih, FreeRADIUS nyata **15/15**, FE tsc/eslint
   0 + vitest **61/42+19** + i18n PASS, build live OK + build mock DITOLAK,
   `make e2e` **10/7+3** (Chromium nyata; PDF %PDF diverifikasi, blokir per
   item, verifikasi→kwitansi→aktivasi), docs check PASS, bash -n OK.
6. **Review independen** (sub-agent): REQUEST_CHANGES → semua P0/P1 + P2
   layak-perbaiki DISELESAIKAN + verifikasi ulang hijau — disposition di
   `report/reviewer/20261106T173900Z-tk604-independent-review.md`.
7. **Laporan kontrak**: `report/orchestrator/20261106T174500Z-tk604-billing-ui.md`
   (keputusan engineering + gap + langkah) + explorer reports
   (`report/backend-explorer/`, `report/frontend-explorer/`).

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (penahan tunggal tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; termasuk timer host `issue_due_invoices` (01:00) |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 → aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-06-tk604-billing-ui` — sesi ini (lihat §5 status push/PR).
- Arsip riwayat (remote): `parallel/beta-be2`, `integration/beta-0.1`,
  `session/2026-11-06-wg-e2e`, `session/2026-11-06-bootstrap-inrepo`,
  `session/2026-11-06-billing-docs`, `session/2026-11-06-docs-tk109`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **TK-701 — ledger M7** (P2; FINANCE.md §2/§13/§16, ARCHITECTURE §8):
   COA/books/periods/journal + post_entry SECURITY DEFINER + period lock +
   immutability + tes bypass T12-LED-01/T12-LED-NEG-01 + buku platform dari
   event sumber M2. **ATAU lanjutan M6**: TK-602 isolir (default off +
   simulasi wajib), TK-607 saldo pembuka, TK-608 dokumen koreksi
   (refund/void), TK-609 kolektor (setoran/selisih).
2. Keputusan kecil kontrak: endpoint ambil bukti transfer (§8 "dapat
   diperbesar") + field rekening pada verifikasi — butuh keputusan dokumen
   (CONTRACT §4) sebelum implementasi.
3. Ops host Gate A/G saat host tersedia (termasuk timer
   `issue_due_invoices`).
4. Follow-up minor: e2e opsional job CI; doctor hint mismatch vs refused
   (F7); quick_tab `paid_awaiting_activation` services-list masih stub
   backend (UI memakai perhitungan kelayakan sendiri — jujur).

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ merge PR TK-604 (lihat §1/§5)
git log --oneline -5
bash docs/tools/setup_env.sh                 # sandbox baru (PG17+FreeRADIUS deb-extract)
cd backend && MT_PG_BIN=/home/z/my-project/pgbin/pg17 bash scripts/dev_bootstrap.sh
MT_ENV=test .venv/bin/python -m pytest tests -q          # 359 tes (PostgreSQL nyata)
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && cd ../.. && make e2e              # 10/10 browser+backend nyata
python3 docs/tools/check_docs.py && bash -n instalasi.sh
```

Lingkungan sandbox baru: venv via `uv venv .venv --python /usr/bin/python3.13
--seed` (python3.13-venv tidak terpasang); pnpm wrapper `corepack pnpm@12.16.1`
(shim `~/.local/bin/pnpm`); Playwright Chromium 1200 ter-cache. CATATAN
proses background di sandbox: unduhan nohup bisa MANDek — jalankan
setup_env.sh FOREGROUND; .deb terpotong (lzma error) → hapus *.deb lalu
unduh ulang (idempoten).

Baca: CONTRACT.md (versi `1fff190`), docs/AGENT_HANDOFF.md §5 (tabel
prioritas diperbarui), docs/progress.md checkpoint teratas,
report/orchestrator/ terbaru, docs/BETA_RELEASE_STATUS.md (fitur aktif +
batasan 6).

## 7. Risiko & keterbatasan yang diketahui

- **Daur ulang sandbox platform menghapus `/home/z/my-project`** — push
  sesegera mungkin; lab dibangun ulang via `docs/tools/setup_env.sh`.
- Mutasi router tetap jalur simulator (source=simulator,
  verified_lab=false) — tidak ada klaim perangkat nyata (G1).
- Scheduler invoice BELUM dipasang sebagai timer host (ops Gate A/G) —
  JANGAN klaim otomasi harian aktif.
- Gap jujur TK-604 (§6 laporan sesi): bukti transfer belum dapat
  diperbesar (backend tanpa endpoint bukti); verifikasi belum menyebut
  rekening (tak ada di kontrak M6); "Menunggu koneksi" menunggu bukti NAS
  (G1); kelayakan menilai maks 10 halaman × 200; spec e2e billing
  bergantung urutan (workers:1).
- Live Demo (master directive §9) BELUM DIMULAI — menunggu GNS3 lab;
  `seed_billing_e2e` (tenant demo + reset state-mutabel) adalah pola seed
  yang dapat dikembangkan untuk demo tenant §9.3/§9.7.
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan (kontrak TK-002
  patch-exact; perubahan versi = keputusan terdokumentasi).
- PAT hanya di `.secrets/` sandbox (tidak pernah di-commit; scan bersih);
  PAT kedaluwarsa = push berikutnya BLOCKED (minta PAT baru).
