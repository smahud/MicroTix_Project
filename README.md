# MicroTix

Aplikasi SaaS untuk pengusaha RT/RW Net Indonesia: MikroTik, pelanggan berbasis RADIUS per perusahaan, penagihan, pembayaran, pembukuan, monitoring dan backup.

Repository ini masih pada tahap dokumentasi. Revisi **2.2** merapikan kontrak eksekusi tanpa mengubah harga, kuota atau roadmap R1–R4. Belum ada kode aplikasi atau hasil pengujian runtime.

Mulai dari [indeks dokumen](docs/README.md). Untuk meminta coding agent membangun aplikasi, gunakan [master prompt eksekusi](docs/MASTER_PROMPT.md). Agent menyelesaikan R1, lalu R2, kemudian R3/R4; menulis kode lokal tidak menunggu akses perangkat yang hanya diperlukan untuk verifikasi lab.

Pemeriksaan dokumen dari akar repository:

```bash
python3 docs/tools/check_docs.py
```

[Kebutuhan produk](docs/PRODUCT.md) memiliki harga dan kebijakan; [arsitektur](docs/ARCHITECTURE.md) memiliki stack/API/job/data; [rencana implementasi](docs/IMPLEMENTATION_PLAN.md) mengatur urutan; [audit](docs/AUDIT_REPORT.md) menjelaskan temuan dan perlakuan seluruh 77 berkas sumber.

Nama tampilan dikendalikan [branding.json](docs/branding.json), dengan override PROJECT_NAME/APP_NAME/BRAND_NAME. Identitas internal, data, sesi dan integrasi tetap stabil ketika nama display berubah.
