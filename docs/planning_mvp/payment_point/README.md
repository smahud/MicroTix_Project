# MicroTix Payment Point — Planning Index

Status: **PROPOSED / DOCUMENTATION ONLY / NOT IMPLEMENTED / DEFAULT DISABLED**  
Tanggal: 2026-11-13. Target lokasi repo: `docs/planning_mvp/payment_point/`.

## Tujuan dan batas
Add-on opsional pada Accounting untuk pembayaran invoice internet pelanggan ISP melalui integrasi DANA Enterprise, pencatatan hak tenant dan pencairan dana. **Tidak menjadi blocker Production Beta**, tidak mengubah task aktif, tidak membuat modul Billing/Accounting kedua. Belum ada otorisasi implementasi, aktivasi merchant produksi, perubahan kontrak produk, ataupun deploy.

## Keputusan bisnis pemilik
- Satu pengelolaan merchant/dana pusat MicroTix; pemisahan tenant pada internal ledger. Tenant diupayakan terpetakan ke identitas Shop DANA agar transaksi dapat ditelusuri silang. Apakah Shop cocok untuk ISP independen dan tersedia pada akun yang dikontrak harus diverifikasi.
- Fitur terlihat dalam Accounting, **OFF untuk seluruh tenant secara default**; opt-in eksplisit dan hanya setelah provider, legal, serta release gate disetujui.
- Biaya layanan MicroTix **Rp1.000 per transaksi Payment Point berhasil**, dipotong dari hak/saldo tenant; dashboard menampilkan jumlah transaksi berhasil dan total biaya layanan. Tidak menambahkan Rp1.000 ke checkout pelanggan.
- Pembayaran manual/langsung ke tenant tidak memicu biaya layanan Payment Point. Biaya DANA/provider sesuai tarif/kontrak aktual dicatat terpisah, tidak diasumsikan Rp tertentu. Withdrawal tidak dikenakan biaya tambahan MicroTix; biaya eksternal bank/provider mengikuti ketentuan aktual.
- Kode unik tiga digit pernah diusulkan, **belum final untuk setiap kanal**. Tidak boleh dipakai sebagai identitas transaksi utama, tidak boleh ditambahkan pada QRIS atau kanal lain tanpa verifikasi aturan provider dan regulasi.
- Dana pusat tidak sama dengan saldo tersedia tenant; catat pending, settled, available, reserved, withdrawn, refunded dan disputes dengan ledger yang dapat direkonsiliasi.

## Dokumen
- [DANA_OFFICIAL_REFERENCE.md](DANA_OFFICIAL_REFERENCE.md) — indeks resmi, pemetaan kemampuan, hal yang belum terbukti.
- [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md) — batas domain, alur dana, ledger, transaksi dan UX.
- [IMPLEMENTATION_AND_ACCEPTANCE.md](IMPLEMENTATION_AND_ACCEPTANCE.md) — tahapan non-blocking, acceptance dan release gates.

## Otoritas dan workflow
Ikuti `CONTRACT.md`, `docs/README.md`, `docs/PRODUCT.md` (kebijakan produk), `docs/FINANCE.md` (akuntansi), `docs/ARCHITECTURE.md` (tenant/API/DB), `docs/UI_UX.md`, `docs/ACCEPTANCE.md`, `task/0000-start-here.md` dan `report/LATEST_HANDOFF.md`. Dokumen ini **proposal**, bukan pengganti dokumen normatif. Bila diadopsi, reviewer menyiapkan decision record di `report/`, memperoleh persetujuan perubahan normatif, dan baru mengubah dokumen pemilik konsep. Tidak membuat task implementasi baru sebelum prioritas Beta mengizinkan.