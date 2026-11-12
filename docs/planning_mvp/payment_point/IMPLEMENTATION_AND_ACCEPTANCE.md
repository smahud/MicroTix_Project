# Deferred Implementation Plan & Acceptance Gates

Status: **PLANNING ONLY — NO EXECUTION TASK AUTHORIZED**. Prioritas aktif tetap Production Beta, termasuk `task/0010-pa006-idempotency.md` dan blocker yang tercatat di `report/LATEST_HANDOFF.md` (snapshot harus dicek ulang sebelum eksekusi).

## Tahap 0 — sekarang, dokumentasi saja
- Review dokumen ini terhadap `CONTRACT.md`, `docs/PRODUCT.md`, `docs/FINANCE.md`, `docs/ARCHITECTURE.md`, `docs/UI_UX.md`, `docs/ACCEPTANCE.md` dan kode aktual.
- Tetapkan semua konflik/perubahan normatif sebagai PROPOSED, simpan decision record di `report/` saat hendak mengadopsi; jangan diam-diam mengubah scope Beta.
- Validasi katalog DANA dan kumpulkan pertanyaan vendor. Jangan buat endpoint, migration, feature flag aktif, akun live, ataupun task executor baru.

## Tahap 1 — setelah Beta tidak terganggu dan ada persetujuan
- Dapatkan konfirmasi DANA mengenai merchant pusat untuk banyak ISP, Shop/Division, settlement, disbursement, fee, QRIS dan refund.
- Pilih **satu** checkout utama yang didukung (Hosted Checkout kandidat), tidak mengimplementasikan semua keluarga API.
- Tetapkan kontrak API dan data model minimal berdasarkan field nyata; reviewer menyetujui revisi dokumen normatif dan acceptance.

## Tahap 2 — sandbox vertical slice (task terpisah kelak)
- Feature flag OFF default; UI Accounting discoverable tetapi jelas belum tersedia.
- Shop provisioning/mapping, create order, verified webhook, query status, idempotent invoice allocation, ledger liability/platform fee, settlement reconciliation, withdrawal reserve/approve/disburse/status; satu kanal dulu.
- Gunakan existing billing/accounting/jobs; migrasi expand-compatible; rollback dan audit.

## Tahap 3 — UAT, pilot, rilis terkontrol
- Uji multi-tenant, concurrency, provider downtime, refund/dispute, settlement discrepancy, beneficiary changes, withdrawal failure, bank cutoff, accounting close/reversal, backup/restore dan data export.
- Pilot terbatas setelah legal/provider approval dan kontrol dana; baru pertimbangkan opt-in tenant. Tidak pernah auto-enable semua tenant.

## Acceptance minimum
| ID | Kriteria |
|---|---|
| PP-01 | Tenant default OFF; tidak ada order/fee provider sebelum opt-in dan release gate |
| PP-02 | Pembayaran manual tidak membuat MicroTix Payment Point fee |
| PP-03 | Fee Rp1.000 tepat satu kali per transaksi sukses terverifikasi, tercatat terpisah dan terlihat di dashboard |
| PP-04 | Pending, failed, expired, canceled tidak memicu fee MicroTix; refund/reversal ditangani dengan jurnal koreksi |
| PP-05 | Webhook replay/out-of-order dan dua callback bersamaan tidak menggandakan payment, allocation atau fee |
| PP-06 | Tenant A tidak dapat membaca/mengubah order, saldo, Shop mapping atau withdrawal tenant B, termasuk akses admin tanpa izin |
| PP-07 | Rekonsiliasi provider payment + settlement + disbursement terhadap internal ledger; mismatch dapat ditelusuri |
| PP-08 | Withdrawal hanya dari available, reserve atomik, approval, validasi rekening, query status, tidak double transfer |
| PP-09 | Saldo tenant tidak diklaim sebagai saldo DANA per Shop dan tidak dapat melebihi hak yang terverifikasi |
| PP-10 | Tidak ada aktivasi jaringan otomatis akibat pembayaran tanpa kebijakan dan gate terpisah |
| PP-11 | Persetujuan DANA/aturan dana pihak ketiga, biaya dan QRIS terdokumentasi sebelum produksi |
| PP-12 | Tidak ada regresi Billing/Accounting dan tidak ada dependency infra yang tidak perlu |

## Bukti yang diperlukan
Untuk setiap kriteria: requirement → test → command → environment → result → evidence → SHA → independent reviewer. PostgreSQL nyata untuk RLS/ledger/races, sandbox DANA untuk API, settlement sample untuk audit, serta laporan `report/<role>/...` dan handoff sesuai `CONTRACT.md`. `PASS` hanya bila benar-benar dijalankan.

## Explicit non-goals saat ini
Tidak membuat kode, tidak mengubah `docs/tasks.json`, tidak membuat packet `task/`, tidak mengubah `CONTRACT.md`, tidak mengubah `docs/PRODUCT.md`/`FINANCE.md`, tidak menyatakan Beta siap, tidak mengaktifkan DANA live, tidak menjanjikan SLA withdrawal.