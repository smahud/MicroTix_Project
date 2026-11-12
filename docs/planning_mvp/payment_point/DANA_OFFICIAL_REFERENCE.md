# DANA Enterprise — Official API Capability Reference

Sumber utama (resmi): https://dashboard.dana.id/api-docs-v2/llms.txt (diakses 2026-11-13). Ini **indeks API**, bukan bukti hak akses/izin merchant, struktur field tertentu, atau kemampuan settlement per Shop. Validasi ulang dokumen detail dan sandbox sebelum coding.

| Kebutuhan | Referensi resmi | Status desain |
|---|---|---|
| Onboarding & credential | https://dashboard.dana.id/api-docs-v2/llms/guide/getting-started/integration-overview.md | Perlu kontrak/credential sandbox |
| Auth SNAP dan signature | https://dashboard.dana.id/api-docs-v2/llms/guide/authentication/authentication-asymmetric.md | Implementasi sesuai varian produk terpilih |
| SDK dan sandbox | https://dashboard.dana.id/api-docs-v2/llms/guide/getting-started/libraries.md | Evaluasi SDK resmi; jangan membuat kriptografi sendiri bila ada SDK cocok |
| Hosted checkout | https://dashboard.dana.id/api-docs-v2/llms/guide/payment-gateway/hosted-checkout.md | Kandidat alur sederhana |
| Create order | https://dashboard.dana.id/api-docs-v2/llms/api/payment-gateway/create-order-hosted.md | Wajib verifikasi field/reference |
| Finish notify | https://dashboard.dana.id/api-docs-v2/llms/api/payment-gateway/finish-notify.md | Verifikasi signature, event dan status |
| Query payment | https://dashboard.dana.id/api-docs-v2/llms/api/payment-gateway/optional-api/query-payment.md | Reconciliation/fallback |
| Cancel/refund | https://dashboard.dana.id/api-docs-v2/llms/api/payment-gateway/optional-api/cancel-order.md dan https://dashboard.dana.id/api-docs-v2/llms/api/payment-gateway/optional-api/refund-order.md | Aturan refund dan fee belum final |
| QRIS MPM | https://dashboard.dana.id/api-docs-v2/llms/api/qris-acquirer/generate-qris.md | Kanal opsional; cek larangan surcharge |
| Shop management | https://dashboard.dana.id/api-docs-v2/llms/guide/merchant-management/shop.md dan https://dashboard.dana.id/api-docs-v2/llms/api/merchant-management/create-shop.md | Kandidat identitas tenant; **bukan bukti saldo/settlement per Shop** |
| Division management | https://dashboard.dana.id/api-docs-v2/llms/guide/merchant-management/division.md | Alternatif bila diwajibkan DANA; jangan menambah hierarki tanpa kebutuhan |
| Disbursement bank | https://dashboard.dana.id/api-docs-v2/llms/guide/disbursement/disbursement-to-bank.md dan https://dashboard.dana.id/api-docs-v2/llms/api/disbursement/transfer-to-bank.md | Kandidat withdrawal; konfirmasi eligibility dan limit |
| Validasi rekening & status transfer | https://dashboard.dana.id/api-docs-v2/llms/api/disbursement/optional-api/transfer-to-bank-account-inquiry.md dan https://dashboard.dana.id/api-docs-v2/llms/api/disbursement/optional-api/transfer-to-bank-inquiry-status.md | Verifikasi beneficiary dan transfer |
| Notify transfer | https://dashboard.dana.id/api-docs-v2/llms/api/disbursement/optional-api/transfer-to-bank-notify.md | Idempotent callback |
| Settlement pembayaran | https://dashboard.dana.id/api-docs-v2/llms/guide/settlement-file/payment-services.md | Cross-check provider vs internal ledger |
| Settlement disbursement | https://dashboard.dana.id/api-docs-v2/llms/guide/settlement-file/disbursement.md | Cross-check transfer dan saldo |
| UAT | https://dashboard.dana.id/api-docs-v2/llms/guide/scenario-testing.md | Gate sandbox sebelum pilot |

## Pertanyaan wajib ke DANA (bukan asumsi)
1. Apakah satu merchant MicroTix boleh menerima dana atas tagihan milik banyak ISP independen lalu mendisburse hasilnya? Apakah perlu skema aggregator/marketplace/submerchant khusus dan dokumen KYB tiap tenant?
2. Apakah Shop bisa digunakan sebagai identitas tenant, dan apakah `shop`/`division` terikat pada create order, callback, settlement file, serta disbursement? Field dan contoh payload apa yang berlaku?
3. Apakah rekening/akun disbursement pusat bisa mendanai transfer ke rekening bank milik ISP tenant, bagaimana limit, settlement delay, hold, dispute, refund, chargeback dan transfer failure?
4. Apakah tarif provider dihitung per kanal/transaksi, siapa menanggungnya, dan bagaimana transaksi gagal/refund memengaruhi fee?
5. Apakah nominal dengan kode unik dan/atau surcharge diperbolehkan untuk setiap kanal, terutama QRIS? Bila tidak, nonaktifkan mekanisme tersebut untuk kanal terkait.
6. Berapa batas jumlah Shop, throughput API, rate limit, token/key rotation, webhook retry, dan retensi file settlement untuk target 1.000 tenant?

## Bukti yang wajib dikumpulkan kemudian
Versi dokumentasi, produk DANA yang disetujui, akun sandbox, sample request/response teredaksi, daftar field dan status, contoh settlement file, surat/kontrak konfirmasi model dana terpusat, hasil UAT. Jangan menyimpan API key/private key pada repository atau laporan.