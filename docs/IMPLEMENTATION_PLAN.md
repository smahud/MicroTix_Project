# MicroTix — rencana eksekusi agent

Target adalah aplikasi yang dapat dipakai sesuai [PRODUCT.md](PRODUCT.md), bukan menghasilkan audit dokumentasi berikutnya. [tasks.json](tasks.json) satu backlog; 85 ID TK dipertahankan supaya jejak pekerjaan lama tetap dapat dipakai. [MASTER_PROMPT.md](MASTER_PROMPT.md) adalah perintah eksekusi. Seluruh fase R1–R4 tetap berada dalam scope produk; jangan membangun modul fase lanjut sebelum inti yang diperlukan selesai.

## 1 Urutan pengiriman

| Milestone | Task utama | Hasil yang harus dapat dicoba |
|---|---|---|
| M0 — bootstrap | TK-001–004,107 | Backend+frontend berjalan, PostgreSQL nyata, migrasi awal/seed dua tenant, CI/command standar dan simulator failure; belum perlu schema semua modul |
| M1 — identitas dan shell | TK-101–109 | Daftar/login/MFA baseline, tenant switch, permission/RLS/secret/storage, i18n id/en, job center dan quota; API serta UI terhubung |
| M2 — subscription SaaS | TK-201–205 | Paket/invoice/upload/approval atomik, renewal/upgrade/grace; rekening snapshot, pembayaran platform terpisah |
| M3 — router dan RADIUS | TK-301–307,408,510 | Enrollment/health, API-SSL pin, NAS revision, auth multi-tenant, package binding, accounting/session admission; local FreeRADIUS nyata dahulu |
| M4 — pelanggan existing | TK-401–407,409–412,501 | Discovery, wizard8langkah, S1–S4, merge, CSV, CRUD/service, drift dan replacement tanpa input ulang; adopsi DB-only |
| M5 — operasi R1 | TK-502–507,509,511 | Monitoring, backup commit-before-prune, cutover B0–B6 dan rollback; end-to-end R1 lokal, lab terkait saat tersedia |
| M6 — penagihan R2 | TK-601–609 | Invoice internet→verifikasi dana→aktivasi manual; simulasi isolir default off, payment race/hold/retry, opening balance dan kolektor |
| M7 — pembukuan R2 | TK-701–705 | Ledger enforced di DB, recognition, rekonsiliasi, closing, laporan dan buku platform; tie-out finansial |
| M8 — R3 | TK-801–811 | Voucher/agen/FUP, portal, ACS model tertentu, tiket/work order/inventaris/ODP, notifikasi opt-in, edge opsional |
| M9 — R4 | TK-508,901–906 | Profile/WAN ChangePlan, single/failover/PCC bersyarat dan adapter OLT terpilih; per topology/model |
| Operasi lintas fase | TK-1001–1006 | Packaging, input inventory, observability, backup/DR, runbook dan pengujian kapasitas scope yang sudah dibangun |

Tabel memberi alur produk; dependency task di JSON menentukan kesiapan teknis. Dalam fase aktif, ambil task siap menurut topological_order. Jangan mengikuti order global yang kebetulan membuat TK-801 siap sebelum pekerjaan R1: filter release lebih dahulu. Task shared SCOPED_R1_R4 diambil untuk scope fitur saat ini, bukan mewajibkan ACS atau load1.000 tenant pada R1.

Jika hanya verifikasi lab R1 menunggu akses, kode dan pengujian R2 yang independen boleh diteruskan setelah R1 local acceptance lulus. Jangan melabeli R1 verified_lab atau released. Scope implementasi default seluruh R1–R4; jika pengguna memilih target R1/R2 tertentu, hentikan setelah seluruh pekerjaan independen target itu selesai dan laporkan sisa roadmap. Pilihan ini tidak menghapus kebutuhan fase lain.

## 2 Cara mengerjakan satu task

1. Baca objective, dependency dan requirements task; lalu hanya bagian dokumen domain yang relevan. PRODUCT memiliki kebijakan, ARCHITECTURE kontrak lintas domain, dokumen domain detail. Audit report bukan bahan yang harus dibaca ulang setiap task.
2. Nyatakan acceptance yang benar-benar akan dibuktikan. Pilih skenario relevan dari test-cases.json serta invariant lintas tenant/uang/efek perangkat. Case majemuk dipisah per assertion/resource; tidak ada PASS semua case dari satu happy path.
3. Bangun vertical slice: migration/constraint→service/transaction→API/OpenAPI→UI→automated test. UI memakai API nyata. Hindari menyelesaikan seluruh backend atau seluruh mockup sebelum satu alur bisa dicoba.
4. Jalankan test relevan dengan dependency nyata; perbaiki akar masalah. Review diff untuk race/security/UX. Jika reviewer terpisah tersedia, serahkan diff, acceptance dan hasil test ringkas. Satu agent dapat self-review secara jujur; jangan berhenti karena nama model reviewer tidak tersedia.
5. Perbarui docs/progress.md setelah milestone atau sebelum jeda: task/substep, commit/diff, command+exit, assertion actual/evidence, keputusan engineering, blocker tepat dan langkah berikutnya. Catat environment test: simulator, Linux/FreeRADIUS, CHR, atau perangkat fisik.

Tidak ada batas tiga putaran perbaikan yang memaksa menyerah pada bug yang masih dapat diperbaiki. Retry harus berdasarkan hipotesis/bukti; berhenti mengulang perintah yang sama tanpa informasi baru. Blokir hanya dependency yang memerlukan fakta/akses/keputusan yang belum tersedia, lanjut pekerjaan independen. Jangan mengubah requirement atau menghapus assertion agar CI lulus.

## 3 Dependency dan status

contract = interface/schema/behavior yang konkret; build = implementasi+tes lokal yang relevan; verified = bukti runtime lingkungan yang diperlukan. Dependency verified membatasi verifikasi/rilis penerus, bukan larangan menulis interface/kode/test penerus. Jangan memakai stub yang mengembalikan sukses untuk menyatakan dependency selesai.

Catat per task: contract_complete, implemented, verified_local, verified_lab (jika relevan), release_enabled. Tidak perlu service registry/status database baru; checkpoint Markdown dan hasil CI cukup pada awal. Task internal berstatus todo/in_progress/done/blocked pada milestone yang dinyatakan. blocked mencantumkan item konkret, misalnya CHR image atau grant target, bukan “full audit belum sempurna”.

TK-003 hanya fondasi yang dipakai R1. Domain ledger lengkap R2; R1 menyimpan source event pembayaran platform immutable. TK-109 renderer berfungsi sebagai worker/module terbatas pada image yang sama jika cukup; tidak harus satu deployment bisnis baru. TK-1001 inventory remote tidak boleh menghalangi bootstrap kode lokal. TK-1005 scale/HA dijalankan saat mengaktifkan skala terkait, bukan prasyarat setiap commit.

## 4 Command standar yang dibangun TK-002

| Command | Hasil wajib |
|---|---|
| make bootstrap | Dependency pinned, dev config/secret lokal, DB/migration/seed sintetis dan aplikasi lokal; idempoten; tidak memasang layanan host produksi diam-diam |
| make lint / make typecheck | Pemeriksaan backend/frontend nyata, exit nonzero bila gagal |
| make test | Unit/domain logic, kalender, state/role/rounding; tidak mengganti tes DB |
| make test-integration | PostgreSQL17 nyata, transaksi/RLS/constraints/races/storage/outbox |
| make test-contract | OpenAPI/request/response/permission/enums/idempotency |
| make test-radius | Daemon FreeRADIUS nyata+PostgreSQL+radclient pada lab Linux terisolasi; nyatakan jika belum bisa dijalankan |
| make i18n-check | Key/placeholder/semantic parity id/en dan pseudo-locale |
| make e2e | Playwright alur UI↔API, happy/error/role paths pada viewport terpilih |
| make build | Build artefak backend/frontend pada dependency terpin |
| python3 docs/tools/check_docs.py | Static docs check dari akar repo; tersedia sebelum aplikasi dibangun |

CHR/GNS3 command ditambahkan saat harness dan target tersedia; harus fail/BLOCKED jujur bila tidak ada aset, bukan exit0 dengan echo. Jangan membuat test suite ribuan stub demi mencocokkan jumlah katalog. Katalog adalah desain; implementasikan tes bermakna sesuai fase. DB nyata tidak diganti SQLite untuk klaim transaksi/RLS. Mock scanner tidak membuktikan gate upload; simulator tidak membuktikan firmware.

## 5 Batas kompleksitas dan biaya konteks

Satu repo, satu backend modular, satu frontend, satu PostgreSQL, worker bersama. Adapter hanya integrasi yang diperlukan fase aktif. Jangan menambah Redis/Celery/Kafka/Kubernetes, orchestrator multi-model, custom task DSL, blanket CQRS/event sourcing, atau generic multi-tenant framework. Gunakan Django/DRF/React yang sudah tersedia; fungsi uang/kalender/state ditulis sekali.

Baca master sekali di awal/resume; berikutnya checkpoint+diff dan task aktif. Jangan memuat seluruh JSON test catalog/semua audit report setiap iterasi. Cari ID yang dibutuhkan dengan rg atau script kecil. Setiap review membawa diff dan hasil relevan, bukan seluruh percakapan.

## 6 Hasil terminal

COMPLETED hanya untuk scope implementasi yang benar-benar selesai; kode selesai lokal dapat berdampingan dengan verified_lab=BLOCKED. Jika pekerjaan wajib scope belum terimplementasi, status keseluruhan BLOCKED dengan pekerjaan selesai dan dependency konkret. FAILED bila invariant/test gagal dan belum diperbaiki; jangan menutupinya dengan status blocker.

Laporan akhir singkat: alur yang dapat dicoba dan command menjalankannya; commit/diff; test aktual+lingkungan; fitur belum diverifikasi; input yang diperlukan; flag produksi dan status gate. Dokumen yang lulus check bukan bukti production ready. Jangan menyatakan selesai ketika masih ada task independen yang dapat dikerjakan dalam scope.
