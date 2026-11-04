# MicroTix — hasil audit mendalam dokumentasi

Revisi 2.2 · 5 November 2026 Asia/Jakarta. Scope: dokumentasi dan alat pemeriksa dokumentasi, bukan implementasi aplikasi. Reviewer: satu agent, self_review; tidak diklaim review independen atau sign-off profesional.

Kesimpulan: tujuan awal tetap **aplikasi SaaS operasional RT/RW Net**, dengan identitas pelanggan/RADIUS per perusahaan yang independen dari router. Arsitektur modular monolith sudah tepat. Hambatan utama berasal dari penumpukan kontrak audit, jalur paket lama, dan pencampuran build readiness dengan release readiness. Koreksi menyederhanakan kontrak dan urutan kerja sambil mempertahankan seluruh fase produk.

## 1 Basis dan metode

Sumber terbaru diperiksa melalui GitHub: [smahud/MicroTix_Project commit19b9543](https://github.com/smahud/MicroTix_Project/tree/19b954308a7573bc449f551400d053fba1c089d7). Seluruh77 file lokal dicocokkan terhadap Git blob SHA sumber;77cocok,0mismatch. Ukuran sumber5.203.562 byte. Review mendalam berfokus pada PRD, keputusan pemilik, kontrak teknis/domain, task dependency dan isi acceptance. Semua JSON diparse dan inventory/duplikasi/ref dianalisis; laporan historis diperlakukan sebagai evidence lama, bukan kebutuhan baru.

Paket aktif kini21 file termasuk root README,19 payload docs dan manifest. Tidak dibuat arsip ZIP atau direktori salinan sejarah baru. Versi sumber lengkap tetap dapat dibaca dari parent commit; tabel §7 memetakan **setiap** path lama. Dokumen master amendemen dipecah dan koreksinya dimasukkan pada pemilik konsep, sehingga agent tidak harus menafsirkan AUD→MAC→EXE untuk mengetahui perilaku akhir.

Audit ini bukan pembuktian seluruh kemungkinan bug atau setiap kombinasi firmware. Requirement yang memiliki172ID tetap terlacak; kelengkapan ID bukan sertifikat kelengkapan semua klausul. Katalog uji adalah desain, bukan hasil runtime.

## 2 Temuan yang dikoreksi

| ID | Temuan konkret dan dampak | Koreksi minimum |
|---|---|---|
| DX-01 | START_BUILD/CLAUDE/README merujuk agent/, docs/contracts/ dan tools/ yang tidak cocok dengan layout repo docs/ | Satu entry MASTER_PROMPT dan indeks; semua tautan aktif ke file yang benar; tidak menyalin docs ke layout kedua |
| DX-02 | Validator dari root gagal: hidden file/directory is not packaged; task validator mencari agent/task-contracts di root | check_docs.py menarget docs+README, tidak memeriksa .git sebagai payload; default root dari lokasi script |
| DX-03 | --root docs membuat checker struktur35check lulus tetapi integrity checker tetap file set size mismatch | Satu manifest repository aktif, refresh eksplisit; tidak menganggap hash ZIP/manifest pra-rename membuktikan bytes sekarang |
| DX-04 | Dua kelompok file identik: Owner_Decision_Requests dan Requirements_Traceability_Matrix, ditambah proyeksi JSON/Markdown berulang | Satu backlog dan satu acceptance catalog; audit-history/materialisasi lama hanya di riwayat commit |
| DX-05 | Mode A/B/C, mandate lokal, formulir server besar dan review audit lama dapat membuat agent berhenti sebelum menulis kode | Kewenangan mengikuti instruksi pengguna/akses aktual; input remote hanya diminta untuk tindakan yang memakainya; build lokal independen |
| DX-06 | Global topological_order memungkinkan taskR3 siap lebih awal daripada pekerjaan intiR1 | Filter faseR1→R2→R3→R4 dahulu, lalu dependency; shared ops hanya scope fitur aktif |
| DX-07 | TK-003 memaksa prototipe ledger luas pada fondasiR1, padahal buku penuhR2 | FondasiR1 hanya interface/source event pembayaran immutable; penegakan ledger lengkap TK-701 |
| DX-08 | TK-1002 build bergantung inventory target lengkap TK-1001, sehingga packaging lokal dapat tertahan fakta server | Dependency menjadi kontrak input, inventory actual tetap wajib sebelum target deployment/verification |
| DX-09 | SEC-DEC-01 menuntut keputusan perluasan MFA seluruh login untuk klaim fullASVSL2 yang tidak menjadi kebutuhan produk asli | Pertahankan platformMFA dan step-up semua aktor sensitif; tanpa klaim fullL2, tidak mengarang approval/exception; blocker global lama dicabut |
| DX-10 | Siklus review wajib nama dua model dan maksimum3putaran dapat meninggalkan bug meski masih bisa diperbaiki | Claude implement/Codex review bila tersedia; self_review jujur bila satu agent; lanjut berdasarkan temuan actionable |
| DX-11 | Django5.2+tenant composite FK belum menjelaskan keterbatasan relasi ORM | UUID PK + UNIQUE(tenant,id) dan constraint FK SQL melalui migration reversibel; bukan memaksakan CompositePrimaryKey semua model |
| DX-12 | Tabel RADIUS lama mencampur kontrol internal dan reply, serta klaim auth yang sama untuk seluruh metode Hotspot | Resolver satu sumber; Cleartext-Password/Expiration/Simultaneous-Use/Auth-Type kontrol server, reply NAS terpisah; test sesuai actual login method |
| DX-13 | read_clients dapat dibaca sebagai NAS live reload; dua alamat/proses bisa disalahklaim hostHA | Desired/applied revision, lifecycle restart/reload teruji dan revoke semua instance; HA harus failure domain independen |
| DX-14 | Penjelasan payment offline dapat terbaca memulihkan atribut otomatis; verifikasi suspend/restore berpotensi disamakan | Pembayaran tidak auto active; Reject+positif sesi putus untuk suspend, Accept eligibility untuk restore; perangkat online dimensi terpisah |
| DX-15 | Aturan kuota, replacement30 hari, bonus upgrade, expiry SaaS dan first-period tersebar pada amendemen | Formula efektif dimasukkan ke PRODUCT; reservation tidak double count, bonus tidak drift/double, E/ended/retention dan due/prorata eksplisit |
| DX-16 | Ledger source lama belum satu tempat untuk prepaid memorandum/recognized receivable, credit, empty posted entry, period close dan direct bypass | FINANCE dan ARCHITECTURE memuat posting, DB enforcement dan semua edge tersebut langsung |
| DX-17 | Katalog T05 platform race dilabel R2; edgeT22 dilabel R1; generic dependencies berpotensi mewajibkan semua lab di semua fase | T05-RACE-01 R1, T22-EDGE-01 R3; assertion applicability mengikuti resource/feature aktual, tidak PASS sebagian case |
| DX-18 | Config lama mempunyai124 records, termasuk salinan kuota/brand/kontak dan alias sebelum ada aplikasi legacy |114 default teknis dipertahankan;10 nilai dipusatkan ke PRODUCT/branding. Tidak membangun importer draft config yang belum ada datanya |
| DX-19 | Mutable nama brand belum menjelaskan runtime config Vite atau kestabilan namespace/session | Backend resolver→public frontend config; display override fallback jelas, ID/encryption/API/cookie/namespace rtrw stabil; rename regression wajib |
| DX-20 | Matriks/standar/checksum dan laporan dapat disalahartikan hasil aplikasi atau kapasitas nyata | Status designed/NOT_RUN, local/lab/release terpisah, waktu canary nyata dan evidence actual; tidak klaim production ready dari pemeriksaan docs |
| DX-21 | Kepemilikan sumber/durasi limit migrasi dan penggabungan sebelum password belum sepenuhnya eksplisit | Structural candidate dahulu, reclassify setelah credential; keep_one/rename tidak menulis sumber, consumed/remaining quota direview; recovery export terkini |

## 3 Yang dipertahankan

- GOAL-01–06 dan seluruh172ID kebutuhan; R1 fondasi/pelanggan, R2 bisnis, R3 voucher/ACS/lapangan, R4 WAN/OLT. Tidak mengganti aplikasi dengan proyek orkestrasi AI.
- Harga enam paket, tahunan12 bulan setara10bulanan, router/layanan/team/agen/fair-use, tujuan pembayaran dan kontak pemilik. Seed data tetap bukan verifikasi kepemilikan bank dan tidak tampil pada landing publik.
- Satu tenant/company, granular roles, RLS+FK, basis pengguna RADIUS per tenant, username exact, adopsi DB-only, cutover terpisah, pindah/ganti router tanpa input ulang.
- Isolir default off dan aktivasi setelah bayar selalu manual; tunggakan SaaS tidak menjadi isolir internet; status bayar/isolir/koneksi/job tetap terpisah.
- Backup100routine/10manual/10prechange, commit-before-prune, key recovery, off-host/DR; session accounting/strict admission dan trust boundary NAS; retensi finansial/legal hold dan PDP.
- Python3.13/Django5.2/React/PostgreSQL17/FreeRADIUS3.2, PostgreSQL outbox tanpa Redis/Celery, WireGuard/nftables/Caddy; target Debian13 dan lab GNS3 saat inputnya tersedia.
-85 ID TK,256 scenario ID,662 assertion ID. Expected wording diperbaiki hanya untuk menghilangkan referensi amendemen yang dihapus dan blockerMFA lama; ID tetap stabil. Tidak menciptakan hasil uji.

Keputusan historis C-01–C-21, D01–D10, N01–N20 dan T-01–T-09 ditelusuri melalui topiknya pada PRODUCT/domain. DOC-01/02/19 tentang nama file/struktur paket/lapisan authority diperbarui oleh konsolidasi ini sesuai mandat penyederhanaan; bukan kebijakan bisnis baru. Nama file stabil tanpa versi, revisi tersimpan dalam paket. Default keamanan/uang tidak dilonggarkan demi mengurangi jumlah dokumen.

## 4 Sumber primer yang diperiksa

| Pokok | Sumber | Penggunaan/batas |
|---|---|---|
| Python/Django | [Django5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/) | Python3.13 kompatibel; exact patch dipin saat build, bukan klaim patch sudah diinstal |
| Composite FK/ORM | [Django5.2 composite primary keys](https://docs.djangoproject.com/en/5.2/topics/composite-primary-key/) | Batas relational field mengharuskan desain UUID+constraint tenant SQL; pilihan implementasi adalah inferensi engineering audit |
| RLS | [PostgreSQL17 row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html) | Runtime/table owner/BYPASSRLS diperhatikan; RLS bukan pelindung backend sepenuhnya kompromi |
| Local shadow/Disconnect | [MikroTik RADIUS](https://manual.mikrotik.com/docs/authentication-authorization-accounting/radius/) | Prioritas akun lokal dan incoming Disconnect memerlukan prosedur per build, bukan use-radius saja |
| Session race | [FreeRADIUS3.2.8 simultaneous use](https://www.freeradius.org/documentation/freeradius-server/3.2.8/tutorials/simultaneous_use.html) | Accounting/admission race perlu dibuktikan; strict reservation adalah desain proyek, bukan jaminan default FreeRADIUS |
| Expiry | [FreeRADIUS expiration](https://wiki.freeradius.org/modules/rlm-expiration) | Kontrol expiry server memengaruhi Session-Timeout; bukan seluruh control attribute menjadi reply |
| PDP | [JDIH UU27/2022](https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/) | Pasal46; clock internal24/48 jam adalah policy proyek, bukan teks undang-undang |
| Retensi | [DJP UU28/2007](https://www.pajak.go.id/id/undang-undang-nomor-28-tahun-2007), [PP50/2022](https://stats.pajak.go.id/index.php/id/peraturan/tata-cara-pelaksanaan-hak-dan-pemenuhan-kewajiban-perpajakan) | Minimal10 tahun; penerapan/legal hold dibahas OPERATIONS, bukan sertifikasi kepatuhan |
| Security reference | [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | Referensi kontrol relevan; tidak ada klaim fullL2 atau replacement policy login tersirat |

Halaman daring diperiksa5 November 2026. Implementasi masih harus memeriksa dokumentasi untuk exact binary/build/dependency yang dipilih; tidak memakai manual versi baru sebagai bukti firmware lama telah diuji.

## 5 Verifikasi paket dan batasnya

Command yang dapat dijalankan dari checkout: `python3 docs/tools/check_docs.py`. Refresh manifest setelah perubahan yang telah direview: `python3 docs/tools/check_docs.py --refresh`. Checker tidak menulis aplikasi, melakukan deploy, membaca secret atau menghubungi router. Root ditemukan dari script; file aplikasi baru, .git dan checkpoint/evidence dinamis tidak diperlakukan payload docs.

Pemeriksaan: semua payload manifest/hash, tautan Markdown aktif,85taskunik+240edge DAG tanpa target hilang,256caseunik+662assertionunik,172requirement ID terdefinisi,114defaultbertipe dan batas kritis, resolver branding dan pencegahan hasil runtime fiktif. Uji negatif pemeriksa dilakukan di salinan sementara untuk perubahan hash, file/link hilang, duplicate IDs/JSON, dependency salah/cycle, angka invalid dan status desain palsu. Hasil aktual: 10 pemeriksaan positif lulus dan 17 fixture negatif seluruhnya ditolak dengan exit nonzero. Pemeriksaan positif juga membandingkan tabel harga/rekening persis, 114 nilai default yang dipertahankan, set ID task/case/assertion dan seluruh 172 requirement ID. Detail ringkas hasil statis ada pada command checker; jumlah assertion bukan nilai kualitas/coverage kode.

Validator hanya membuktikan properti struktural yang diperiksa. Ia tidak memvalidasi seluruh semantik bisnis atau menguji implementasi, protokol, compliance, kapasitas dan desain visual. Review isi dilakukan terpisah oleh agent yang sama, bukan reviewer independen. Tidak ada source test dari aplikasi karena aplikasi belum ada.

## 6 Status akhir dan langkah berikutnya

| Penilaian | Status |
|---|---|
| Dokumentasi untuk memulai implementasi | Siap setelah static checker lulus pada commit yang diserahkan |
| Aplikasi dibangun/diuji oleh audit ini | Belum;0runtime application tests |
| Firmware/CHR/CPE/OLT kompatibel | Belum dibuktikan |
| Deployment/pilot/isolir produksi | Tidak dijalankan/diaktifkan |
| Professional sign-off dan production readiness | Belum dievaluasi untuk implementasi nyata |
| Tindakan berikut | Jalankan MASTER_PROMPT pada checkout, mulai TK-001 lalu vertical slice R1 |

Masukan eksternal tersisa adalah input lingkungan nyata ketika hendak memakainya: CHR/GNS3/license, host/DNS/UDP, CPE/OLT model, endpoint sekunder/failure domain, kapasitas/budget, tujuan publik dan reviewer pemakaian resmi. Tidak satu pun menghalangi agent menulis kode lokal dan test independen. Jika model OLT/CPE belum dipilih, jangan mengarang adapter bersertifikat; laporkan batas model tersebut dan lanjut modul independen.

## 7 Disposition seluruh77 file sumber

Setiap path sumber berikut telah dibaca sebagai dokumen/struktur atau dipetakan sebagai proyeksi historis. Snapshot persis dapat dibuka dari commit sumber §1. Tidak ada file lama yang masih berwenang secara diam-diam di checkout baru.

| Path sumber | Pengganti/perlakuan aktif |
|---|---|
| `README.md` | README.md |
| `docs/MicroTix-File-1-Kontrak-Revisi-Lengkap.md` | docs/PRODUCT.md, ARCHITECTURE.md, RADIUS.md, FINANCE.md, OPERATIONS.md |
| `docs/MicroTix-Template-Onboarding-Server-GNS3.md` | docs/OPERATIONS.md |
| `docs/NAME_MIGRATION.md` | docs/branding.json dan ARCHITECTURE.md §9 |
| `docs/README.md` | docs/README.md |
| `docs/agent/AGENTS_v2_1.md` | docs/MASTER_PROMPT.md dan IMPLEMENTATION_PLAN.md |
| `docs/agent/CLAUDE.md` | docs/MASTER_PROMPT.md |
| `docs/agent/START_BUILD.md` | docs/MASTER_PROMPT.md |
| `docs/agent/task-contracts_v2_1.json` | docs/tasks.json |
| `docs/agent/tugas_v2_1.md` | docs/tasks.json dan IMPLEMENTATION_PLAN.md |
| `docs/audit-history/AI_Context_and_Handoff_Optimization.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Claude_Code_Implementation_Handoff.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Contradiction_and_Resolution_Register.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Delivery_Verification.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Documentation_Change_Log.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Duplicate_and_Overlap_Register.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/FINAL_AUDIT_REPORT.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Final_Integrity_Verification.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Independent_Semantic_Review_Packet.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/MicroTix-Control-Export-v2_1-build_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Normative_Authority_Registry.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Owner_Decision_Requests.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/README_BUNDLE.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Requirements_Traceability_Matrix.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Requirements_Traceability_Matrix.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/audit-history/Unresolved_Decisions_and_Blockers.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/bootstrap_docs.sh` | Dihapus dari jalur aktif; docs sudah berada pada repository, tidak perlu copier |
| `docs/branding.json` | docs/branding.json |
| `docs/repository-manifest.json` | docs/repository-manifest.json |
| `docs/sumber/PRD_SaaS_RTRWNet_v2_1.md` | docs/PRODUCT.md |
| `docs/sumber/Panduan_Akuntansi_ISP_v2_1.md` | docs/FINANCE.md |
| `docs/sumber/Playbook_RouterOS_v2_1.md` | docs/ROUTEROS.md |
| `docs/sumber/Spesifikasi_ACS_TR069_v2_1.md` | docs/ACS.md |
| `docs/sumber/Spesifikasi_RADIUS_dan_Migrasi_v2_1.md` | docs/RADIUS.md |
| `docs/sumber/Spesifikasi_i18n_v2_1.md` | docs/I18N.md |
| `docs/sumber/Technical_Design_RTRWNet_v2_1.md` | docs/ARCHITECTURE.md dan defaults.json |
| `docs/sumber/UIUX_Design_RTRWNet_v2_1.md` | docs/UI_UX.md |
| `docs/sumber/audit/Documentation_Audit_Report_v2_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/Documentation_Changelog_v2_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/Documentation_Quality_Gate_Results_v2_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/Macro_Consolidation_Report_v2_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/Requirements_Traceability_Matrix.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/Source_to_Output_Map_v2_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/Unresolved_Issues_v2_1.md` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/input-provenance_v2_1.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/audit/static-verification_v2_1.json` | Riwayat di commit sumber; temuan aktif dikonsolidasikan pada AUDIT_REPORT/kontrak domain |
| `docs/sumber/contracts/Execution_Design_v2_1.md` | docs/IMPLEMENTATION_PLAN.md, ARCHITECTURE.md, OPERATIONS.md |
| `docs/sumber/contracts/Owner_Decision_Requests.md` | MFA baseline ARCHITECTURE.md §3; permintaan perluasan lama bukan blocker build |
| `docs/sumber/contracts/execution-profile.schema.json` | Input minimum scope aktual pada OPERATIONS.md, tanpa registry grant terpisah |
| `docs/sumber/contracts/job-kind-registry_v2_1.json` | docs/ARCHITECTURE.md §6 |
| `docs/sumber/contracts/parameter-registry_v2_1.json` | docs/defaults.json; nilai komersial PRODUCT, display branding.json |
| `docs/sumber/contracts/target-registry.schema.json` | Input target aktual pada OPERATIONS.md |
| `docs/sumber/decisions_log.md` | Pemilik konsep pada PRODUCT/ARCHITECTURE/domain; provenance commit sumber |
| `docs/sumber/quality/CI_Test_Orchestration_v2_1.md` | docs/IMPLEMENTATION_PLAN.md dan ACCEPTANCE.md |
| `docs/sumber/quality/Compatibility_and_Hardware_Matrix_v2_1.md` | docs/OPERATIONS.md dan progress per build/model |
| `docs/sumber/quality/GNS3_Lab_Architecture_v2_1.md` | docs/OPERATIONS.md §2 |
| `docs/sumber/quality/Lab_Onboarding_and_Access_v2_1.md` | docs/OPERATIONS.md §1–2 |
| `docs/sumber/quality/Performance_Reliability_DR_Plan_v2_1.md` | docs/OPERATIONS.md §4/6 |
| `docs/sumber/quality/Quality_Gates_and_Release_Readiness_v2_1.md` | docs/ACCEPTANCE.md §3–6 |
| `docs/sumber/quality/Quality_Standards_v2_1.md` | docs/ACCEPTANCE.md dan ARCHITECTURE.md |
| `docs/sumber/quality/Security_Test_Plan_v2_1.md` | docs/ACCEPTANCE.md dan security cases di test-cases.json |
| `docs/sumber/quality/Test_Case_Specifications_v2_1.md` | docs/test-cases.json; salinan Markdown kedua dihapus |
| `docs/sumber/quality/Test_Coverage_Matrix_v2_1.md` | docs/test-cases.json requirement_ids; tidak ada proyeksi matrix kedua |
| `docs/sumber/quality/Test_Evidence_and_Reporting_v2_1.md` | docs/ACCEPTANCE.md §5 |
| `docs/sumber/quality/Test_Strategy_v2_1.md` | docs/ACCEPTANCE.md dan IMPLEMENTATION_PLAN.md |
| `docs/sumber/quality/asvs-applicability_v2_1.json` | Security acceptance relevan; tidak mengadopsi full conformance tanpa keputusan produk |
| `docs/sumber/quality/asvs/ASVS_5.0.0_en.csv` | Sumber standar tetap di riwayat; referensi resmi ASVS untuk review yang relevan |
| `docs/sumber/quality/asvs/README.md` | Atribusi sumber standar di riwayat; tautan resmi pada laporan ini |
| `docs/sumber/quality/release-applicability_v2_1.json` | docs/ACCEPTANCE.md dan release/features per case |
| `docs/sumber/quality/supplemental-test-registry_v2_1.json` | docs/test-cases.json (172 skenario/344 assertion); checklist task pada tasks.json |
| `docs/sumber/quality/test-case-registry_v2_1.json` | docs/test-cases.json (84 kasus/318 assertion) |
| `docs/sumber/source-manifest_v1_4.md` | Provenance di commit sumber; inventory aktif repository-manifest.json |
| `docs/sumber/source-manifest_v2_0.md` | Provenance di commit sumber; inventory aktif repository-manifest.json |
| `docs/sumber/source-manifest_v2_1.md` | Provenance di commit sumber; inventory aktif repository-manifest.json |
| `docs/tools/task_context_v2_1.py` | Pilih task/requirement dengan rg atau JSON; tanpa wrapper konteks wajib |
| `docs/tools/validate_execution_docs_v2_1.py` | docs/tools/check_docs.py |
| `docs/tools/verify_repository_v2_1.py` | docs/tools/check_docs.py |
