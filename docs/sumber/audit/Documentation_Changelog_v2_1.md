# Documentation Changelog — MicroTix v2.1

Dokumen: `sumber/audit/Documentation_Changelog_v2_1.md`  
Revisi paket: **2.1-macro.1** · Tanggal: **29 Oktober 2026, Asia/Jakarta**  
Lingkup: konsolidasi tata kelola dokumentasi, integritas repositori, desain uji dan ekspor artefak. Tidak ada implementasi aplikasi, akses server, deployment, pengiriman notifikasi, atau perubahan release flag.

## 1. Riwayat dan atribusi bukti

| Tahap | Isi perubahan | Kedudukan bukti pada konsolidasi ini |
|---|---|---|
| Baseline v1.4 | Kebutuhan produk, keputusan dan domain dasar | Manifest provenance dipertahankan; arsip v1.4 terpisah tidak tersedia untuk verifikasi ulang |
| Paket quality-ready v2.0, 28 Oktober 2026 | 32 berkas; 31 entri manifest; 549.017 byte menurut audit terdahulu | Klaim historis, bukan hasil observasi ulang atas arsip asli pada tahap ini |
| Audit Sol v2.1, 29 Oktober 2026 | 46 kelompok koreksi AUD; kontrak lengkap, template typed, registry 64+20, proyeksi quality dan audit baru | Paket langsung 37 berkas/1.016.000 byte; 36/36 ukuran+hash diperiksa kembali dan cocok |
| Konsolidasi makro 2.1-macro.1, 29 Oktober 2026 | Tiga kontrol utama ditulis ulang; MAC-01–08 disinkronkan; dependency dan assertion diperketat; lineage, verifier, manifest dan ZIP diperbarui | Hasil statis/self-review dan byte aktual; seluruh runtime NOT_RUN; kesiapan G0–G5 BLOCKED |

Versi arsitektur tetap 2.1. Sufiks paket `macro.1` membedakan byte final ini dari keluaran Sol pada tanggal yang sama. Nama sumber v2.1 dipertahankan agar referensi stabil. Tidak ada file source yang dihapus. Dua manifest lama tetap byte-identik terhadap paket langsung. SHA-256 paket masukan langsung: `5e55d03ce8c166c6c16befc9ed4f5f5f356cc5bc345f9325048e86af88d31c5c`.

## 2. Ringkasan seluruh amandemen AUD-01–46

| AUD | Perubahan sistem dan dampak dependensi |
|---|---|
| 01–04 | Amendemen mengatasi larangan edit historis; precedence tunggal; Mode A/B/C ortogonal; one-shot hanya menjalankan scope yang input/izin/dependency-nya lengkap |
| 05–07 | Integritas byte dan provenance dibedakan; bootstrap lama audit-only; pengganti TK-001 fail-closed; rujukan master prompt yang hilang digantikan kontrak self-contained |
| 08–11 | Kuota identitas gabungan, reservasi atomik, registri parameter typed, kalender half-open, anchor/bonus, grace/ended/offboarding yang deterministik |
| 12–14 | FK tenant komposit, namespace username, HTTP/error/idempotency, outbox, lease/uncertain/recovery dan stale-writer fencing |
| 15–18 | Role/RLS/secret/SSRF, enrollment minimum yang terotorisasi, panen S1 terpisah dengan cleanup, merge/password/CSV dan preview revision |
| 19–21 | Tenant dari transport NAS, proyeksi multiatribut, facade DB transaction-local, NAS desired/applied revision, validasi cache/revoke dan batas process-vs-host HA |
| 22–25 | Cutover B0–B6, no-local-shadow canary, observasi waktu nyata, rollback baseline+delta, bukti suspend positif dan restore berarah Accept |
| 26–28 | Session directory, accounting delta/partisi, strict concurrent admission, edge Linux terenkripsi/ditandatangani/TTL dan batas partition |
| 29–32 | Siklus billing, dedup transfer dan allocation, ledger immutable tiga lapis, period locks, prepaid memorandum, recognition rounding, credit/refund/tax |
| 33–35 | Backup size+transfer completion/durable, katalog retained, metrics tier aktual, RTO dari outage dan RPO dari acknowledged events; restore+rekonsiliasi sebelum isolir |
| 36–39 | ACS gateway/NBI/claim/model mapping, rotasi dengan recovery, UI/permission/i18n snapshot, GNS3 API inventory, PPPoE L2, route/failure domain/resource |
| 40–42 | Registry 64 child+20 QA-SEC, ASVS 5.0 mapping, WCAG 2.2 AA, profil load/soak/sample/percentile dan minimum gate per fitur |
| 43–46 | Evidence per assertion, status/reviewer faktual, raw capture terbatasi, PDP Pasal 46 dan pencabutan klaim all-pass lama |

Harga, kuota komersial, rekening/nomor konfirmasi, R1–R4, 24 parent T01–T24 dan ID TK existing dipertahankan. Tidak ada exact version deployment atau kompatibilitas perangkat yang ditebak. Kebutuhan legal/akuntansi yang membutuhkan review nyata tetap menjadi prasyarat produksi.

## 3. Keputusan makro pada revisi ini

| ID | Temuan/resolusi | Berkas/kontrak terdampak | Bukti atau gerbang |
|---|---|---|---|
| MAC-01 | 32 berkas historis dibedakan dari 37 input langsung; status dokumentasi tidak sama runtime | Master, README, audit, manifest | Input inventory/lineage Python |
| MAC-02 | Manifest, self-exclusion, payload root, mapping target dan envelope ekspor tanpa siklus | Manifest, Source-to-Output, verifier, laporan statis | Verifikasi tree dan ZIP setelah seal |
| MAC-03 | Retensi 10 tahun minimum dari akhir tahun buku; dasar KUP/PP/dokumen perusahaan dibedakan dari SAK; legal hold/offboarding/purge/key recovery tegas | Master, TD, PRD, panduan akuntansi, quality | QA-SEC-20, G2/G5 + review profesional |
| MAC-04 | Tenggat PDP 72 jam, eskalasi prosesor ≤24 jam di dalam window, clock konservatif, bukti pengiriman dan kanal aktual | Master, PRD, TD, evidence/security, tugas | QA-SEC-20, G2/G5 + counsel |
| MAC-05 | Trust boundary NAS→tenant menyeluruh; pool reuse, revoke/cache/projection/accounting/edge ikut scoped | Master, RADIUS, TD, security/compatibility | T16/T19/T21, QA-SEC-09/11/12, G1/G2/G4 |
| MAC-06 | Local integration profile tidak diwajibkan inventaris server; dependency cutover/restore/ACS/fault tegas tanpa loop | Registry, spesifikasi, CI, template, gates | DAG/parity statis; runtime tetap NOT_RUN |
| MAC-07 | Gate formal dibedakan dari prasyarat; G0–G5 BLOCKED; QG formal NOT_EVALUATED; pilot capability berbeda dari flag umum | Gates, audit results, unresolved, PRD/tugas | Evaluasi kesiapan tanpa hasil runtime buatan |
| MAC-08 | Parameter tambahan typed dan owner per kontrol; default pilot scoped tanpa mengubah kuota komersial | Master, TD/decision log, gates | Effective config/ADR/review saat implementasi |

MAC adalah keputusan dokumentasi berdasarkan mandat konsolidasi, bukan persetujuan historis pemilik yang direkayasa. Ketentuan baru ditetapkan di master §23; quality tidak menjadi sumber kebijakan tandingan. Salinan blok normatif diperiksa berparitas. Parameter runtime, grant, penerima notifikasi dan reviewer tetap diisi dari fakta aktual.

## 4. Pencabutan hasil lama dan posisi audit

Klaim **QG-DOC 10/10 PASS** dan **QG-QA 12/12 PASS** pada baseline lama dicabut sesuai AUD-46. Mismatch hitungan kasus, gap spesifikasi, mapping ASVS dan cacat semantik tidak mendukung klaim all-pass. Registry sumber sebelumnya memiliki 62 child pada matriks, 35 blok spesifikasi, 27 gap dan dua negatif T16 dalam narasi; audit Sol menyatukannya menjadi 64 child + 20 QA-SEC. Konsolidasi ini mempertahankan seluruh ID dan menambahkan assertion pada ID existing.

Pemeriksaan input langsung **36/36 PASS** berarti byte cocok dengan manifest input; tidak berarti sumber historis v2.0 diverifikasi ulang, tidak berarti semua desain aman, dan tidak berarti runtime PASS. Klaim 31/31 pada audit Sol dipertahankan sebagai rekam historis. `static-verification_v2_1.json` diregenerasikan untuk tahap konsolidasi dan secara eksplisit tidak mengandung hasil seal yang akan membuat siklus hash.

Status gate pada laporan Sol adalah NOT_EVALUATED. Revisi ini menjalankan evaluasi **prasyarat** dan menetapkan G0–G5 BLOCKED dengan daftar R-01–R-07, tanpa mengubah kasus runtime dari NOT_RUN. Formal QG-DOC/QG-QA tetap NOT_EVALUATED. Tidak ada sign-off independen, akuntan, hukum atau production-ready yang disimulasikan.

## 5. Berkas audit, artefak tambahan dan provenance

Empat berkas kendali mutu pendamping yang dianalisis bersama master adalah `Documentation_Audit_Report_v2_1.md`, `Documentation_Quality_Gate_Results_v2_1.md`, `Source_to_Output_Map_v2_1.md`, dan `Unresolved_Issues_v2_1.md`. Changelog, gate, registry JSON/Markdown, matrix, proyeksi quality, File 2 dan laporan statis juga diperiksa untuk sinkronisasi.

| Kelompok | Perlakuan |
|---|---|
| 32 berkas asal | Mapping historis dipertahankan; berkas direvisi atau dipertahankan sebagai provenance sesuai sumber langsung; jumlah 32 adalah sumber historis, bukan jumlah output |
| Lima tambahan pada tahap Sol | Master kontrak, template onboarding, registry JSON, manifest aktif v2.1 dan laporan static-verification; 32 + 5 = 37 input langsung |
| Tambahan makro: `sumber/audit/Macro_Consolidation_Report_v2_1.md` | Catatan metode, temuan dependency/retensi/PDP/RADIUS, scope, batas dan hasil statis |
| Tambahan makro: `sumber/audit/input-provenance_v2_1.json` | Identitas byte empat lampiran langsung, inventory 37 file, hasil pairing, dan checksum historis yang diberi label reported |
| Tambahan makro: `tools/verify_repository_v2_1.py` | Verifier dokumen baca-saja menggunakan pustaka standar Python; bukan bootstrap, aplikasi atau test runner lab |
| Empat berkas audit pendamping | Report diberi addendum; results dan unresolved diperbarui; source map diperluas ke seluruh file final |
| Dua manifest lama | Tetap byte-identik terhadap input langsung; tidak dipakai memvalidasi file v2.1 final |
| Bootstrap lama | Tetap tersedia sebagai audit-only, tanpa klaim telah diperbaiki menjadi installer |

Jumlah akhir adalah **40 berkas**: 37 dipertahankan/direvisi + 3 tambahan makro. Manifest aktif memuat **39 entri**; pengecualian tunggal adalah manifest sendiri. Seluruh file final terpetakan ke target repository, termasuk alat verifikasi dan provenance. Dokumen konsolidasi eksternal tidak menambah jumlah isi ZIP.

## 6. Perubahan dependency dan dampak implementasi

1. TK-001 membutuhkan verifikasi tepat seluruh tree serta conflict handling sebelum penempatan; verifier yang disertakan membantu pemeriksaan sumber, tidak mengimplementasikan installer target.
2. TK-002/003/107 tetap mengisi exact deployment pins dan effective configuration dari implementasi aktual. Macro defaults tidak mengisi host/image/license/secret binding yang tidak tersedia.
3. TK-306/307 wajib facade scoped, context transaksi dan applied NAS revision; T19/QA-SEC-11 mendahului klaim cutover. T17 memerlukan backup/restore dan kasus RADIUS terkait; gate agregat tidak dipakai sebagai dependency sirkular untuk menjalankan test.
4. TK-701–705 dan TK-1006 memasukkan MAC-03/04: arsip finansial, hold/purge, incident clock, sender/deputy dan bukti delivery. QA-SEC-20 menguji logika dengan waktu sintetis tanpa menunggu 10 tahun/72 jam nyata; canary/soak/protocol TTL tetap waktu nyata.
5. Uji integration lokal memakai profil workspace terotorisasi; uji jaringan/fault/load/DR/ACS tetap membutuhkan input lab yang tepat. Fitur ACS model atau WAN topology yang belum tersedia tidak menghalangi fitur independen.
6. Scope pilot dan minimum feature gates diperketat; auto-isolir, edge, kapasitas besar dan SLA tetap tidak aktif sebelum bukti minimum terpenuhi. G4/G5 tidak diklaim karena dokumentasi disegel.

## 7. Verifikasi final dan pengendalian perubahan berikutnya

Python memeriksa integrity input, pasangan lampiran, salinan teks arsip, provenance, ID/field/assertion registry, paritas JSON–Markdown, cakupan matrix, dependency DAG, proyeksi master, preservation ID task/keputusan/tujuan pembayaran, path/link internal yang relevan, encoding/fences, serta tree/ZIP final. Hasil pengujian alat verifier terhadap file hilang/tambahan, ukuran/hash salah, traversal/duplikasi/symlink dan manifest kosong dicatat sebagai pengujian alat dokumentasi, bukan uji MicroTix runtime.

Urutan seal: finalisasi source/quality/audit → hasil statis pra-seal → manifest 39 entri+payload root → verifikasi tree → ZIP deterministik → verifikasi ulang ZIP → dokumen konsolidasi eksternal berisi teks utuh ketiga kontrol serta checksum ekspor. Tidak ada perubahan payload setelah hashing. Riwayat perubahan dinilai dari hash input/output; ukuran dan hash keluaran selalu hasil perhitungan, bukan angka perkiraan.

Setiap perubahan berikutnya membuat revisi paket baru, memperbarui kontrak yang berwenang dan proyeksi yang terdampak, mempertahankan provenance, meregenerasikan manifest terakhir, serta mengulang seal dan impact assessment evidence. Jangan mengedit hash secara manual, menulis hasil run ke manifest, atau menggunakan salinan gabungan lama sebagai sumber aktif.

## Audit lanjutan 2.1-audit.2 — 29 Oktober 2026

Baseline ZIP SHA-256 `554123935857366a19fe3719c1abadbaf0fe836db581a436c7da7b402739ec8f`; 40 file/39 payload terverifikasi. Kontrak master, keputusan dan dua manifest historis dipertahankan byte-identik. Koreksi C01–C40 menyelaraskan projection DB/RADIUS/cutover, pembayaran/ledger, ACS, i18n, agent/task dan ekspektasi uji. C41 memperbarui hasil audit pendukung; C42 meregenerasi manifest/integritas. Tidak ada kode aplikasi atau operasi jaringan. 84 case/318 assertion tetap NOT_RUN. Dokumentasi FAIL karena B01–B09; full implementation dan operasi BLOCKED. Laporan before/after, traceability, tools dan evidence tersedia dalam bundle audit pendamping. Riwayat bagian terdahulu tetap berlaku sebagai hasil pada revisinya, bukan klaim audit terkini.

Revisi audit pertama 2.1-audit.1 telah disegel, lalu review lanjutan menemukan rujukan §runbook tidak ada dan tabel gate task yang menyimpang. Keduanya dikoreksi sebagai C43/C44 pada revisi baru 2.1-audit.2; audit.1 tidak ditimpa dan disimpan sebagai history dalam bundle pendamping. C45 mengubah metadata revisi; seluruh urutan static→manifest→tree→ZIP→verification diulang.


## 2.1-build.1 —30 Oktober2026 Asia/Jakarta

Input immutable2.1-audit.2; master mengadopsi klarifikasi EXE-01/02 sesuai tindak lanjut rekomendasi pemilik dan EXE-03–08 sebagai kontrak eksekusi. B01/B02 ditutup; proyeksi wajib diregenerasi exact. Ditambahkan task85/DAG241, parameter124+alias,kind20,profiles,source ASVS5.0.0/253requirements,scenario172/344assertion,applicability662,task-context CLI dan static validator. Baseline84case/318assertion expected tidak dihapus/diubah. Before/after lengkap pada patch pendamping dan change-log JSON; riwayat audit.2 dipertahankan.

Secondary review membetulkan T22-HA agar central HA tetap applicableR1, memperjelas multi-release facets, stale cancel prose TD, scope produksi agent dan rujukan CSV §11. SEC-DEC-01 tetap NEEDS_OWNER_DECISION. Independent semantic review dan runtime evidence tidak dipalsukan. Seal dilakukan ulang pada revisi baru; laporan final/hash berada di amplop eksternal agar tanpa hash cycle.
