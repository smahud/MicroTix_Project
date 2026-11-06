# Independent Review — TK-604 (U09/U10 billing/activation UI)

- Reviewer: sub-agent independen (Task ID 9-a, model glm-5.3, read-only)
- Tanggal: 2026-11-06 (Asia/Jakarta)
- Branch: `session/2026-11-06-tk604-billing-ui` (basis main @ 62595f4) — diff belum di-commit saat review
- Verdict awal: **REQUEST_CHANGES** (1 P0, 2 P1, 8 P2)

## Temuan reviewer (asli)

### P0 (blocker)
1. TS error pada berkas uji: `exact: true` bukan anggota `ByRoleOptions`
   (BillingPage.test), factory `acc()`/`inv()` dipanggil tanpa argumen wajib.
   CI typecheck gagal.

### P1 (should-fix)
2. Tidak ada kontrol paginasi di U09 — `next_cursor` dibuang; fiks kursor
   backend di diff yang sama menjadi kode mati dari sisi UI (>50 baris tak
   terjangkau).
3. Kelayakan U10 + hitung menunggu-aktivasi hanya menilai 200 invoice pertama
   (limit backend) → jalur false-eligible bila invoice tertunggak ada di
   halaman 2+.

### P2 (nit)
4. Router tak terdaftar di status RADIUS diperlakukan "dijamin" — harusnya
   unknown ≠ guaranteed.
5. Fixture mock BILLING_AGING: totals kontradiktif dengan items.
6. Mock `activateRadiusAccount` state-sama → conflict; backend idempoten 204.
7. Mutasi module-level (RADIUS_ACCOUNTS, BILLING_PAYMENT_ALLOCATIONS)
   melanggar komentar isolasi per-instance.
8. Gap spesifikasi §8 yang tidak diimplementasi: bukti transfer dapat
   diperbesar (butuh endpoint bukti baru), "rekening" pada verifikasi (tidak
   ada di kontrak M6), status "Menunggu koneksi" (butuh bukti NAS).
9. Spec e2e bergantung urutan (workers:1 aman; --grep tunggal gagal).
10. Retry menyertakan item `changed` meski label "item gagal".
11. CustomersPage memakai `lifecycleTone` untuk kolom payment/isolation
    (latent, terekspos flag billing aktif) + kode mati kecil di BillingPage.

## Jawaban eksplisit reviewer
- (a) Isolasi tenant: **terjaga** (semua lewat TenantApiView+RLS; PDF same-origin
  aman; file_b64 dibatasi 5 MiB + MIME-sniff server; idempotency+CSRF via withIdem).
- (b) done_when TK-604: **terpenuhi** kedua klausa (snapshot + validasi
  kondisi terbaru per item + blokir item asing/berubah tanpa mengurungkan
  keberhasilan) — dengan kaveat temuan #3.
- (c) Regresi flag flip: satu paparan latent (CustomersPage tone, #11);
  lainnya bersih; perubahan permission mock justru menyelaraskan dengan
  backend live (`services.activate`).
- (d) Overengineering: marginal — kursor backend tak terpakai tanpa #2;
  sisanya proporsional.

## Disposisi orchestrator (perbaikan diterapkan sesi ini)

| Temuan | Disposisi |
|---|---|
| P0-1 | **FIXED** — `exact:true` → regex `/^Catat$/` dll.; factory `over = {}` default. tsc 0 error. |
| P1-2 | **FIXED** — `CursorPagination` (next/prev + riwayat kursor) pada ketiga tab U09. |
| P1-3 | **FIXED** — `fetchAllPages()` (maks 10 halaman × 200) untuk kelayakan U10 + hitung menunggu-aktivasi + validasi ulang pra-eksekusi. |
| P2-4 | **FIXED** — dijamin hanya bila router terdaftar DAN otoritatif (`isUnguaranteed`). |
| P2-5 | **FIXED** — fixture aging konsisten (current 1/250rb, d31_60 1/250rb + items). |
| P2-6 | **FIXED** — mock idempoten paritas backend; uji diperbarui. |
| P2-7 | **ACCEPTED (dev-mock)** — komentar isolasi dikoreksi perilaku: akun+alokasi tetap module-shared (singleton dev); vitest mengisolasi per berkas. |
| P2-8 | **DOCUMENTED** — gap §8 dicatat jujur di laporan sesi + progress (butuh endpoint backend baru: bukti/rekening/bukti-NAS — di luar slice TK-604). |
| P2-9 | **ACCEPTED** — harness `workers:1, fullyParallel:false`; ketergantungan urutan didokumentasikan. |
| P2-10 | **FIXED** — label "Coba lagi item belum berhasil" + validasi ulang kondisi terbaru. |
| P2-11 | **FIXED** — `paymentTone`/`isolationTone` di CustomersPage; kode mati dihapus; agingQ hanya tab invoice. |

Verifikasi ulang pasca-perbaikan: tsc 0 · eslint 0 · vitest **61/61** ·
i18n paritas OK · build live OK · build mock DITOLAK · e2e **10/10**
(Chromium+backend nyata). Backend tak berubah pasca-review (**359/355+4**).
