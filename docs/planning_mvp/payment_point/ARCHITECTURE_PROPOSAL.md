# Architecture Proposal — Optional Payment Point

**Status PROPOSED. Tidak mengubah implementasi atau perilaku produksi.**

## Boundary
- Reuse invoice, Payment, allocation, posting double-entry dan permissions MicroTix yang sudah ada. Tidak ada ledger keuangan paralel atau database kedua. Pisahkan buku tenant dan buku platform sesuai `docs/FINANCE.md`.
- Tambahkan adapter DANA hanya saat task implementasi disetujui; reuse Django/DRF, PostgreSQL/RLS, dan existing durable jobs/outbox. Tidak menambah microservice, Redis, Celery, Kafka atau infrastruktur baru tanpa bukti kebutuhan.
- Merchant pusat: MicroTix. Mapping internal `tenant_id ↔ dana_shop_id` (jika DANA mendukung secara kontraktual); Shop adalah label provider, **bukan akun bank atau saldo DANA milik tenant**. Pertimbangkan Division hanya jika DANA mensyaratkannya.
- Simpan referensi terpisah: invoice ID, internal payment attempt/order ID, provider order ID, provider transaction ID, Shop ID, settlement batch ID, withdrawal ID, provider disbursement ID. Referential integrity, unique constraints dan tenant ownership wajib.

## Alur pembayaran
1. Tenant opt-in secara eksplisit setelah fitur global release-enabled; default OFF. Tidak mengubah pembayaran manual.
2. Pelanggan memilih kanal Payment Point yang disetujui. Server menghitung payable dari invoice; biaya layanan Rp1.000 **tidak ditambahkan ke checkout**. Kode unik hanya jika diperbolehkan kanal dan disetujui sebagai kebijakan tersendiri.
3. Server membuat payment attempt idempotent dan order DANA; order terikat ke tenant, invoice, Shop mapping, nominal dan masa berlaku.
4. Webhook diterima sebagai input tak tepercaya: verifikasi signature/authenticity, payload, nominal, mata uang, order, merchant, Shop (jika ada), status dan replay. Query provider bila status ambigu. Tidak menganggap redirect browser sebagai bukti bayar.
5. Satu payment sukses terverifikasi menghasilkan alokasi invoice satu kali; fee MicroTix Rp1.000 satu kali per successful Payment Point payment; provider fee sesuai data settlement aktual/kontrak, tidak diperkirakan sebagai fakta.
6. Rekonsiliasi mencocokkan provider payment, provider settlement, buku platform, kewajiban kepada tenant dan invoice. Selisih masuk exception queue, tidak disembunyikan.
7. Pembayaran manual sebelum checkout selesai harus memicu upaya cancel/expire order jika didukung; jika dana ganda masuk, proses exception/refund, bukan double allocation.

## Model saldo dan fee
- Pusat memegang/mengelola dana riil hanya setelah model bisnis dan perizinan disetujui. Ledger internal mencatat kewajiban MicroTix kepada tenant, **bukan e-money terbitan MicroTix**.
- Per tenant: `pending` (sukses belum settled/clear), `available` (sudah layak tarik), `reserved_withdrawal`, `withdrawn`, `adjustment/dispute`. Tidak mengkredit available hanya karena callback sukses.
- Contoh **ilustratif**: 100 pembayaran sukses x Rp150.000 = Rp15.000.000; fee layanan MicroTix 100 x Rp1.000 = Rp100.000; hak tenant sebelum provider fee = Rp14.900.000. Biaya DANA dan bank tidak diketahui sampai kontrak/settlement. Refund/reversal wajib jurnal koreksi; jangan mengubah jurnal posted.
- Pendapatan platform dicatat terpisah dari kewajiban tenant. Jika provider fee belum diketahui, catat estimasi hanya bila kebijakan akuntansi dan bukti mendukung, lalu lakukan true-up; jangan menampilkan saldo tersedia yang belum terverifikasi.
- Dashboard tenant: transaksi sukses, gagal/pending, gross payment, fee MicroTix, provider fee, saldo pending, saldo tersedia, withdrawal, rekonsiliasi/selisih, periode dan timestamp. Pembayaran manual tampil dalam Billing tetapi tidak masuk penghitung fee Payment Point.

## Withdrawal
- Tenant meminta nominal maksimal `available`; sistem reservasi atomik agar tidak double-spend. Tidak ada fee MicroTix untuk withdrawal. Biaya transfer eksternal ditampilkan menurut tanggung jawab yang ditetapkan provider/bank.
- Rekening tujuan diverifikasi dan perubahan rekening memerlukan kontrol sensitif/MFA. Super Admin menyetujui, tetapi tidak dapat mengabaikan saldo dan batas otorisasi.
- Kirim satu disbursement idempotent; status pending/unknown **tidak boleh diulang buta**. Query status dan settlement file sebelum retry/kompensasi. Release reservasi hanya setelah kegagalan final terverifikasi; completed dicatat setelah bukti final.
- Target 1x24 jam adalah aspirasi operasional, **bukan SLA** sebelum kontrak, cut-off, hari libur dan provider latency diverifikasi.

## Security, correctness dan operasi
RLS FORCE, principal/tenant scoped idempotency, atomic ledger, unique source-event, replay protection, rate limiting, signature validation, audit immutable, secret rotation, outbox, reconciliation, provider outage recovery, dual-control untuk tindakan sensitif, report dan backup/restore. Jangan menyimpan informasi rekening/PII lebih dari yang diperlukan. Uji concurrency dan tenant isolation pada PostgreSQL nyata. Hindari dependensi pada task PA-006 yang belum diterima reviewer.

## Aktivasi layanan internet
Dokumen saat ini memisahkan pembayaran dan aktivasi layanan. Payment Point **hanya melunasi invoice** sesuai mekanisme yang berlaku. Auto-activation merupakan keputusan produk dan gate pengujian terpisah, bukan implikasi dari webhook sukses.

## Regulatory gate
Kontrak DANA/ketentuan Bank Indonesia mengenai dana milik ISP independen, split/aggregator settlement, QRIS, biaya transaksi dan refund harus mendapat pemeriksaan sebelum transaksi nyata. Identitas Shop dan ledger internal tidak dengan sendirinya mengizinkan custody dana pihak ketiga.