# MicroTix

SaaS pengelolaan RTRWNet/ISP. Repository ini dimulai dari dokumentasi. Nama repository `MicroTix_Project`; nama proyek dan aplikasi **MicroTix**.

## Mulai dari dokumen

1. Baca [panduan agent](docs/agent/START_BUILD.md), [aturan agent](docs/agent/AGENTS_v2_1.md), lalu [kontrak normatif](docs/MicroTix-File-1-Kontrak-Revisi-Lengkap.md).
2. Baca [PRD](docs/sumber/PRD_SaaS_RTRWNet_v2_1.md), [desain teknis](docs/sumber/Technical_Design_RTRWNet_v2_1.md), dan domain yang relevan untuk tugas aktif.
3. Gunakan [backlog](docs/agent/tugas_v2_1.md) dan [kontrak tugas](docs/agent/task-contracts_v2_1.json). Kerjakan dependency dahulu; jangan memuat seluruh dokumentasi untuk setiap tugas.
4. Tutup keputusan yang memblokir scope; implementasi Claude Code → automated test → review Codex → perbaikan → revalidasi. Batasi tiga putaran actionable per task/cycle dan eskalasi bila belum selesai.

## Branding yang dapat diganti

Sumber konfigurasi: [docs/branding.json](docs/branding.json). Aplikasi yang dibangun wajib menyediakan satu resolver branding bersama dengan override deployment `PROJECT_NAME`, `APP_NAME`, dan `BRAND_NAME`. Semua label produk berasal dari resolver, termasuk frontend, email, laporan dan judul halaman. Identitas internal, key database, API, tenant, signature dan kredensial harus stabil serta terpisah dari nama tampilan. Uji pergantian nama wajib membuktikan data, sesi dan integrasi tetap berfungsi. Resolver ini adalah kontrak implementasi; kode aplikasi belum dibuat.

## Status dan integritas

Arsitektur v2.1; revisi repository `2.1-microtix.1`. Berkas disajikan langsung dalam `docs/`, tanpa ZIP. Semua referensi nama proyek pada salinan ini telah diganti sesuai mandat pemilik. Baseline audit terdahulu tetap tersimpan di luar repository ini.

Laporan pada `docs/audit-history/` adalah bukti historis sebelum perubahan nama. Hash, hasil pemeriksaan, dan identitas paket yang disebut di dalamnya tidak menyatakan salinan yang telah diganti namanya lulus audit baru. Manifest sumber lama juga merupakan catatan migrasi; inventory aktif repository adalah `docs/repository-manifest.json`. Jangan menjalankan legacy bootstrap.

Audit penuh tetap BLOCKED oleh keputusan cakupan MFA SEC-DEC-01 dan review semantik independen B05/B11. Tes runtime aplikasi: 0. Tidak ada klaim production ready. Perintah pembuatan repo ini mengizinkan commit/push dokumentasi, bukan deploy atau akses jaringan produksi. Mulai build hanya sesuai scope implementasi yang ditetapkan pemilik.
