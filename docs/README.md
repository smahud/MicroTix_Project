# MicroTix — indeks dokumentasi

Indeks kebutuhan/arsitektur hasil konsolidasi revisi 2.2; alur agent diperbarui 12 November 2026 (Asia/Jakarta). Tujuan: membangun aplikasi RT/RW Net sesuai kebutuhan awal dengan arsitektur sederhana. Dokumen engineering ada di docs; [CONTRACT](../CONTRACT.md) mengatur kewajiban dan [task/0000-start-here.md](../task/0000-start-here.md) menjadi pintu masuk tetap. Packet task di luar docs menyimpan instruksi eksekusi terbatas. Riwayat sebelum konsolidasi tetap tersedia di commit sumber pada AUDIT_REPORT.

| Dokumen | Memiliki |
|---|---|
| [PRODUCT.md](PRODUCT.md) | Tujuan, fase R1–R4, harga/kuota, pembayaran dan kebijakan produk |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, boundary, DB/tenant, API, job/state, konfigurasi dan privilege |
| [RADIUS.md](RADIUS.md) | AAA, session/accounting, migrasi, cutover B0–B6, suspend/restore |
| [ROUTEROS.md](ROUTEROS.md) | Enrollment/adapter, ownership, discovery, backup, monitoring dan WAN |
| [FINANCE.md](FINANCE.md) | COA, posting, recognition, ledger dan laporan |
| [UI_UX.md](UI_UX.md) | Layar U01–U20, navigasi dan interaksi operator |
| [I18N.md](I18N.md) | Bahasa id/en, format dan snapshot dokumen |
| [ACS.md](ACS.md) | TR-069, device ownership/task/parameter dan rotasi (R3) |
| [OPERATIONS.md](OPERATIONS.md) | Input target saat diperlukan, GNS3, deployment, DR, retensi dan kapasitas |
| [ACCEPTANCE.md](ACCEPTANCE.md) | Acceptance T01–T24, status dan gate per fitur |
| [test-cases.json](test-cases.json) | Katalog actions/assertions terinci; bukan bukti eksekusi |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Milestone, loop kerja, command dan batas kompleksitas |
| [tasks.json](tasks.json) | Satu backlog85 task dengan dependency; tidak perlu backlog salinan |
| [MASTER_PROMPT.md](MASTER_PROMPT.md) | Indeks kompatibel dan instruksi singkat untuk memilih peran sesi |
| [MASTER_PROMPT_EXECUTOR.md](MASTER_PROMPT_EXECUTOR.md) | Prompt default coding agent: discovery/resume, scope, implementasi, tes dan penyerahan |
| [MASTER_PROMPT_REVIEWER.md](MASTER_PROMPT_REVIEWER.md) | Prompt default controller: review exact SHA, verdict/koreksi dan packet berikutnya |
| [task/0000-start-here.md](../task/0000-start-here.md) | Cara memilih/menutup packet Markdown, `_done`, review exact SHA dan resume |
| [defaults.json](defaults.json) | Nilai default teknis bertipe; harga/kuota tetap dimiliki PRODUCT |
| [branding.json](branding.json) | Resolver nama tampilan dan metadata publik |
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | Temuan, koreksi, sumber resmi dan disposition seluruh berkas lama |
| [repository-manifest.json](repository-manifest.json) | Inventory/hash dokumen aktif; bukan hash paket arsip lama |
| [tools/check_docs.py](tools/check_docs.py) | Validator statis docs, tidak menilai aplikasi production ready |

Urutan otoritas: instruksi pengguna yang berlaku→dokumen pemilik konsep di tabel ini. Dokumen lain menautkan, bukan mengubah kebijakan konsep itu. Konflik konkret diperbaiki pada sumbernya dan dilacak di checkpoint; jangan menambah lapisan amendemen di atas amendemen. Pilihan implementasi rutin dicatat singkat, tanpa memperbesar scope bisnis.

Untuk mulai: baca panduan task, CONTRACT dan latest handoff; fetch refs aktual, pilih packet eligible, baca IMPLEMENTATION_PLAN/domain relevan dan jalankan validator dari akar repo. Saat resume cukup checkpoint+diff+packet/evidence terakhir. Jangan memuat seluruh katalog/riwayat atau menyalin master prompt panjang setiap perubahan. `docs/tasks.json` tetap satu backlog produk; packet bukan sumber kebutuhan tandingan.

Kesiapan dokumen berarti dapat menjadi input implementasi. verified_local, verified_lab dan release_enabled memerlukan bukti berbeda; tidak ada hasil runtime aplikasi yang dinyatakan oleh paket ini.
