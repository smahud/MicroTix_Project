# Paket review semantik independen — 2.1-build.1

Status: **PENDING**. Ini prosedur dan antrean review, bukan bukti bahwa reviewer berbeda telah memeriksa paket. Pemeriksaan kedua yang tersedia memakai parser/proses berbeda dengan penulis yang sama.

Identitas sumber: ZIP kanonik SHA-256 `e39bec94208b077b55a609bd56504e8c88f36d08c0d43a244e54ec735a8fd8b9`. Verifikasi byte sebelum review. Gunakan paket kanonik sebagai sumber; laporan ini tidak mengganti keputusan produk.

1. Catat identitas reviewer, tanggal, scope dan hash sumber. Reviewer harus berbeda dari penulis perubahan dan boleh melaporkan keterbatasan kompetensi domain.
2. Mulai dari master §1 untuk precedence, §24 untuk perubahan, keputusan produk, lalu PRD/TD/domain. Gunakan `evidence/Authority_Document_Catalog.json`; jangan menganggap semua proyeksi sebagai sumber yang berdiri sendiri.
3. Gunakan `evidence/Independent_Semantic_Review_Queue.json`: 172 ID produk dan 62 amendemen. Untuk setiap ID, baca seluruh bagian dan klausul terkait, pecah kondisi, larangan, default, scope tenant, transaksi, failure path dan recovery menjadi klausa atomik. Baris antrean bukan bukti bahwa seluruh klausul sudah tercakup.
4. Tambahkan klausul tanpa ID dari domain, keputusan, agent, parameter, quality dan fixture. Berikan ID pendukung stabil beserta path, section, exact text hash dan hubungan authority; jangan menulis kebutuhan produk baru.
5. Periksa setiap klausa terhadap design, task, acceptance predicate, positive/negative test dan gate. Buat status terpisah COVERED_BY_DESIGN, GAP, CONFLICT, NOT_APPLICABLE_WITH_RATIONALE. Bukti desain bukan hasil runtime PASS.
6. Untuk 85 tugas, periksa input/output, scope perubahan, dependency milestone, recovery dan bukti selesai. Untuk 124 parameter dan 20 job kind, periksa default/unit/bounds/effect boundary terhadap sumber. Untuk 253 ASVS L1/L2, review applicability termasuk SEC-DEC-01; jangan menyetujui N/A secara massal.
7. Laporkan temuan dengan dua lokasi sumber, trigger konkret, dampak, precedence dan koreksi terkecil. Jangan mengubah sealed payload. Temuan baru masuk revisi berikutnya; keputusan bisnis/security diserahkan kepada pemilik.
8. Tutup B05/B11 hanya setelah seluruh scope diperiksa, coverage klausul dinyatakan dengan bukti, dan tidak ada critical/high atau konflik aktif yang belum diselesaikan. Tandai keterbatasan eksplisit. Finance/legal/hardware sign-off tetap dilakukan oleh reviewer yang kompeten pada stage terkait.

Format bukti per klausa: `clause_id`, `source_path`, `section_or_anchor`, `source_text_sha256`, `authority`, `design_refs`, `task_ids`, `acceptance_ids`, `assertion_ids`, `gate`, `status`, `finding_id`, `reviewer`, `reviewed_at`, `evidence_refs`.

Review dapat dikerjakan tanpa mengakses produksi, mengubah jaringan, atau menjalankan aplikasi. Perubahan yang disepakati mengikuti urutan source finalization → static validation → manifest generation → tree verification → deterministic packaging → package verification. Full audit tetap BLOCKED sampai exit tersebut terpenuhi.
