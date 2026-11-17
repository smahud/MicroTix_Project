# 02 — Kontrak modul dan ekstensi

Baseline: `main@16085f825fef25ee4112d74b729c57e623b0bb05`. Status: **FINAL FOR OWNER REVIEW**. Semua rujukan path/line merujuk baseline, bukan nomor baris setelah patch masa depan. Register cacat ada di [01](01_MODULARITY_AUDIT.md); mekanisme release di [03](03_UPGRADE_PATCH_SAFETY.md).

## 1. Baseline modular monolith

**BASELINE — ARCHITECTURE §1, §4–§8.** Satu codebase backend, satu PostgreSQL dengan schema sesuai kebutuhan existing, domain service langsung dalam proses, adapter eksternal kecil. API/worker dan proses privileged boleh terpisah karena hak/kegagalan berbeda. Tidak perlu HTTP internal, service per domain, ORM pengganti, repository wrapper semua model, DI container, event bus kedua atau plugin framework.

Kontrak ini menjelaskan cara menegakkan kebutuhan existing pada kode aktual. Nama public service di bawah adalah entry point yang ditemukan, bukan jaminan semua invariant sudah dipenuhi. `common.views`, signals RADIUS, dan registry handler adalah composition points yang perlu batas eksplisit; seluruh import lintas domain tidak otomatis salah.

## 2. Ownership state dan migrasi

| Owner aktual | Model/state utama | Mutasi dan konsumen yang sah |
|---|---|---|
| tenancy | Tenant, Membership, Role | Identity mengorkestrasi onboarding; domain lain memeriksa membership/tenant dan membaca metadata seperlunya |
| identity | User, TOTPDevice, RecoveryCode, EmailToken, LoginAttempt, SupportGrant | Login/sesi/step-up melalui service identity; tenant role tetap milik tenancy |
| subscriptions | PlanVersion, Subscription, QuotaReservation, SaaSInvoice, PaymentSubmission, PlatformPaymentSourceEvent | Kuota dan pembayaran SaaS, terpisah dari invoice internet; customers/network meminta reservasi dan commit/release |
| customers | Customer, Service, AccessAccount, CsvImport, MigrationSession, MigrationAccountDecision | Sumber layanan/akun; billing membaca service, radius membentuk proyeksi dari perubahan akun yang sah |
| network | Router, RouterEnrollment, WireGuardHost/Peer, DiscoverySnapshot/Object, DeviceOperation, RouterHealthSample | Enrollment/discovery/connectivity/router desired state; consumers membaca registry yang telah diverifikasi |
| radius | Nas, proyeksi RadCheck/Reply/GroupReply/UserGroup, RadAcct/PostAuth, CutoverRun; fungsi schema radius | Projection writer terbatas dan handler cutover; perubahan akun pelanggan tetap dari owner customers |
| billing | BillingPackage, ServiceCharge, InternetInvoice/Line, InternetPayment, PaymentAllocation | Invoice/payment internet; documents menerbitkan artefak; tidak memutuskan aktivasi otomatis |
| documents | IssuedDocument dan artefak invoice/receipt immutable | Domain sumber menyerahkan snapshot; documents menjaga template/version/hash/storage dan akses download |
| jobs | Job/JobDetail, OutboxEvent, IdempotencyKey | Engine memiliki lease/outcome/retry; domain handler memiliki invariant efek bisnis |
| backups | BackupArtifact, BackupSchedule dan retention/router backup workflow | Router registry dibaca melalui network; bukan owner backup seluruh platform |
| audit | AuditEvent | Penulisan event redacted existing `audit.models.record`; domain sumber memiliki arti action |
| monitoring | Endpoint agregat, belum mempunyai model sendiri | Pembacaan bounded dari network/registry; tidak menjadi owner desired state router |
| config | Registry/defaults dan public config, belum model sendiri | Validasi config dan snapshot; seed command adalah composition, bukan dependency bisnis yang diwajibkan |
| i18n | Resolusi locale/katalog, tanpa tabel bisnis | Fallback/format pesan; tidak menyimpan harga/kuota |
| common | Envelope/error, pagination, crypto, tenant scope, bases/idempotency | Utilitas teknis; model bisnis tetap di owner di atas |
| finance/ledger, tax, access, ACS/ONT, OLT | Direktori domain tersebut NOT FOUND pada main yang diperiksa | Finance/ledger dan network management lanjutan DOCUMENTED. AccessAccount aktual ada di customers; jangan mengarang `domains.access` yang sudah aktif |

Model hanya dimutasi oleh service owner atau satu orchestration point yang disebutkan dan diuji. Pemilikan tabel aktual mengikuti `Meta.db_table` dan migration masing-masing app; nama Python bukan alasan mengubah tabel. Migrasi FK lintas app memiliki dependency eksplisit pada migration pembentuk tabel parent. Perubahan schema `radius` tetap direview bersama owner radius dan tenancy. Future ledger tidak boleh memperoleh grant generik DML posted.

**PROPOSED minimum ownership corrections:** customers mengakhiri discovery adoption melalui service network, bukan menulis `DiscoveryObject` secara bebas; radius meminta perubahan enforcement router melalui entry point network. Jangan memindahkan semua model/access ke direktori baru hanya agar nama folder sesuai diagram. Koreksi ini ditautkan ke PA-010 pada [01](01_MODULARITY_AUDIT.md).

## 3. Allowed dependencies dan batas ORM

| Jenis akses | Diperbolehkan | Batas/review |
|---|---|---|
| Baca ORM sederhana lintas owner | Lookup immutable snapshot, tenant metadata, router registry, service invoice | Tenant scope/permission aktif; field minimal stabil; query bounded; consumer tidak menentukan ulang invariant owner |
| Query aggregate untuk kuota | Satu sumber committed count customers/network + reservasi subscriptions | Hitung di bawah lock yang sama dengan keputusan/reservasi; jangan duplikasi perhitungan yang berbeda |
| Pemanggilan service sinkron | Billing → documents; customers/network → quota service; identity → onboarding composition | Input tervalidasi, caller transaction diketahui, error mesin stabil, side effect eksternal tidak tersembunyi |
| Mutasi model owner lain | Hanya melalui service owner atau projection transaction yang dikontrak | Direct `.save()`/`.update()` lintas owner perlu diganti/diisolasi jika melewati invariant; sebut callsite dan test, bukan larangan import umum |
| FK lintas domain | Diperbolehkan dalam satu DB | FK komposit tenant, indeks dan migration dependency; tidak membutuhkan repository abstraction |
| Signals | Projection hook existing `radius.apps.ready` | Registrasi idempoten; tidak I/O jaringan; jelas transaksi/error/ordering; tests bulk path yang melewati signal |
| Technical helper | crypto/error/locale/context tanpa business policy baru | Upload policy subscriptions yang dipakai billing adalah coupling PA-010; pindahkan helper kecil ke lokasi teknis hanya ketika caller nyata dan tests tersedia |
| Adapter | Handler/collector mengirim typed call ke target registry | API tidak memperoleh hak mutasi router; target/pin/credential resolver tidak dipilih dari URL bebas browser |

Read-only cross-domain bukan akses lintas tenant. Object id yang tampak valid tetap harus dibuktikan kepemilikannya. Query raw SQL tetap parameterized dengan role dan GUC yang benar. Untuk kasus satu proses/DB, service Python cukup; jangan menambah internal API, DTO hierarki atau global interface untuk satu fungsi.

Graph aktual mengandung cycle karena signals, orchestration dan reverse dependency common. **PROPOSED:** jangan menambah cycle bisnis baru; rawat allowlist kecil callsite existing dengan alasan, owner dan acceptance. Uji import startup dan alur pemanggilan; dependency cycle tidak otomatis membuktikan circular-import crash. Putus loop pada kontrak paling kecil yang bermasalah, bukan memindahkan semua service ke common.

## 4. Kontrak service internal

Setiap service yang menjadi boundary menyatakan singkat dalam docstring/test:

1. Owner operasi, actor, `tenant_id` atau platform scope tepercaya, resource/revision yang diharapkan.
2. Field input bertipe/tervalidasi, perbedaan missing/null/`[]`, precondition dan permission sensitif.
3. Hasil bisnis dan stable error code. Response API tetap mengikuti ARCHITECTURE §5, bukan exception detail database.
4. Siapa membuka transaksi, row-lock order, batas efek eksternal, idempotency/business uniqueness, audit.
5. Kemungkinan dipanggil ulang dari worker/retry, failure ambiguity dan verifier.

Contoh aktual, beserta batasnya:

| Callsite | Kontrak yang dipertahankan | Gap/test wajib |
|---|---|---|
| `billing.services.verify_payment(tenant_id, payment_id, body, actor=...)` | Uang → allocation + receipt; tidak mengaktivasi service | PA-001: lock invoice sebelum validasi outstanding; dua payment konkuren, total allocation konsisten |
| `documents.services.issue_document(...)` | Snapshot, locale, timezone, template version, digest; hasil issued immutable | Gagal rendering/storage membatalkan hasil bisnis yang belum committed; filesystem bukan bagian rollback DB, orphan cleanup terbatas diperlukan |
| `subscriptions.services.reserve/commit_reservation/release_reservation` | Lock subscription; konsumsi satu kali bersamaan materialisasi akun | PA-007: committed count services bukan nol, pending memakai jumlah units, bukan jumlah row |
| `network.services.complete_enrollment(token, wg_public_key)` | Token TTL/sekali pakai, identitas router dan peer konsisten | PA-005: atomic row consume + peer + job; callback ulang tidak mengganti identitas |
| `jobs.engine.create_job` dan `audit.models.record` | Job/detail dan audit/outbox di transaksi pemilik perubahan | Tidak menjamin event terkirim: `dispatch_outbox` baru placeholder; PA-009 |

Contoh ini tidak mengizinkan copy-paste kode yang belum diuji sebagai patch. Kekurangan yang ditemukan tetap berstatus PARTIAL/CONFLICT.

## 5. Transaksi, lock dan side effect

**BASELINE — ARCHITECTURE §4, §6.** Perubahan bisnis, audit redacted, job/outbox yang diwajibkan committed bersama. Tentukan row-lock order konsisten untuk resource yang berbagi invariant. Payment lock sendiri tidak melindungi outstanding invoice yang dipakai dua payment berbeda. Reservasi harus menghitung state setelah lock, bukan precheck sebelum antre lock.

Transaksi pendek untuk persiapan/claim → commit → I/O eksternal → transaksi pendek dengan fence+tenant scope untuk readback/outcome. `tenant_scope` membuka `transaction.atomic`; menaruh seluruh handler di dalamnya berarti I/O masih memegang transaksi. Pecah transaction section sambil mengaktifkan kembali tenant context pada setiap section DB; jangan melepas RLS agar transaksi lebih singkat.

`transaction.on_commit` boleh wake-up, bukan transport durable tunggal. Polling job/outbox tetap pulih setelah crash. Snapshot config/actor/resource/revision yang dibutuhkan disimpan tanpa secret literal; sebelum efek, validasi membership/permission/policy/revision terkini. Kegagalan setelah request eksternal tidak dihapus lewat rollback DB: masuk uncertain/readback/recovery.

Urutan lock yang dipilih harus didokumentasikan per operasi (misalnya payment lalu invoice UUID terurut lalu nomor receipt), dan dibuktikan bebas lost update/deadlock pada transaksi nyata. Jangan menganggap order contoh ini keputusan global sebelum memeriksa caller lain yang mengambil tenant/subscription lock.

## 6. Jobs dan outbox

Engine existing dan handler registry dipertahankan. Handler baru wajib mencatat kind, version input, dedup business key, owner/actor scope, deadline/attempt, effect boundary, verifier dan recovery. Tidak perlu DSL generik.

| Invariant | Acceptance minimum |
|---|---|
| Claim `SKIP LOCKED`, lease dan epoch | Dua worker tidak memiliki hak penulis resource yang sama; stale epoch tidak dapat mengubah terminal/outcome |
| Permission saat eksekusi | Membership/role/router scope dicabut setelah enqueue → efek ditolak; system job punya principal policy eksplisit |
| Effect ambiguity | Cancel saat I/O masih mungkin terjadi tidak dilabel cancelled/none; semua writer lama dihentikan/difence sebelum readback/retry |
| Crash recovery | CLAIMED/PREFLIGHT/EXECUTING/VERIFYING mempunyai recovery bounded; tidak mengantre selamanya atau blind replay |
| Terminal state | FAILED/SUCCEEDED/CANCELLED immutable; permintaan terminal baru menautkan job asal sesuai baseline |
| Outbox | Consumer pertama nyata menyatakan ack, dedup, payload version, retry/dead-letter yang diperlukan; tidak mark dispatched sebelum consumer berhasil |
| Rolling/rollback compatibility | Worker baru memahami pending payload lama; worker lama menolak versi tak dikenal tanpa efek; failed migration tidak meluncurkan backlog mutasi |

PA-002/003/009 adalah gap aktual. Tepat-satu efek tidak dibuktikan oleh satu unique key atau boolean dispatched. Gunakan at-least-once delivery dengan dedup/readback yang telah menjadi kontrak; jangan membangun distributed transaction framework.

## 7. Tenant, privilege, audit dan storage invariants

**BASELINE — ARCHITECTURE §2–§4, §7, CONTRACT §8.** Selalu berlaku pada endpoint, command, worker, export/download dan modul baru:

- Actor authenticated dan membership aktif diverifikasi sebelum konteks tenant. Tenant dari browser adalah permintaan, bukan bukti.
- Runtime non-superuser/NOBYPASSRLS; migrator berbeda dan credential-nya tidak tersedia pada proses API/worker. `ENABLE` + `FORCE RLS`, `WITH CHECK`, FK komposit dan fail-closed tanpa GUC.
- Scope transaction-local pada koneksi/transaksi yang memakai query. Keluar dari scope nested memulihkan konteks outer tepercaya yang sebelumnya aktif. Keluar dari scope terluar, error yang mengakhiri konteks, atau koneksi yang dipakai ulang tidak menyisakan tenant/bypass dari operasi sebelumnya.
- Platform permission terpisah dari role tenant; support grant bukan akses umum ke data/kunci tenant. Scope global job envelope minimum berbeda dari isi JobDetail tenant.
- Otorisasi object/operation/resource sebelum aksi. Retry/cancel/download/restore mewarisi permission operasi asal serta step-up yang relevan.
- Audit action/actor/resource/scope/request/revision/outcome dapat ditelusuri; tidak memuat token, password, private key, proof pembayaran, atau XML pajak mentah.
- Path opaque privat milik scope, bukan path browser. Download menguji izin saat penukaran; hash/size/type diperiksa. File storage harus ikut backup/recovery.
- Public API process tidak memegang CAP_NET_ADMIN/root/Docker socket atau credential mutasi router. Manager host memakai operasi typed terautentikasi lokal.

RLS bukan pengganti authentication dan row ownership bukan pengganti permission. PostgreSQL mendokumentasikan pengecualian superuser/BYPASSRLS dan owner; uji role aktual, bukan hanya nama `mtx_app` ([PostgreSQL 17 RLS](https://www.postgresql.org/docs/17/ddl-rowsecurity.html), diakses 10 November WIB).

## 8. Frontend dan API compatibility

Feature pages memakai `api/contracts.ts`/live adapter; komponen visual tetap di design-system, query/session di state, aturan presentasi di helper kecil. App route dan menu adalah composition point yang wajar; tidak perlu plugin route registry.

**BASELINE:** `/api/v1`, envelope kode mesin stabil, permission backend, opaque pagination dan nilai uang string/Decimal. Additive optional field tidak boleh mengubah arti default existing. Missing/null/`[]` dipertahankan end-to-end. Response TypeScript bukan validasi runtime; adapter tidak boleh membuat nilai sukses palsu ketika field/version tidak didukung.

**PROPOSED checks:** request/response fixtures per aksi penting, status/error/permission dan idempotency; bandingkan schema dengan baseline yang dipin saat perubahan API. Test nyata selection wizard → payload → job effect lebih penting daripada hanya path berada di OpenAPI. Breaking semantic change `/v1` memerlukan compatibility/transition decision; jangan diam-diam menambah `/v2` seluruh aplikasi.

Tenant switch membersihkan selection/query subscription dan state lokal sensitif. Local draft key mengandung actor+tenant+router+migration serta version, nilai dibuktikan konsisten saat dibaca; hapus/abaikan data tenant lama dan JSON rusak. PA-008 mencatat pelanggaran existing. Session cache clear saja tidak membersihkan localStorage.

Feature flag UI existing bukan security gate. Modul future default off di backend dan UI sampai acceptance fase terpenuhi. Flags yang sudah true tidak diubah pada sesi ini; jangan menyamakan true dengan release evidence. Lazy loading dipilih berdasarkan bundle/route cost yang diukur; tidak menjadi alasan rewrite.

## 9. Tax/Finance: kontrak masa depan, tanpa schema baru

`backend/domains/finance`, `ledger`, `tax` dan `docs/planning_mvp/` NOT FOUND pada main. FINANCE §3/§13/§16 menetapkan TaxRule dan posting ledger, tetapi bukan bukti implementasi. Empat draft Tax tambahan diperiksa sebagai kebutuhan konseptual; tidak diubah dan tidak dianggap disetujui.

| Owner | Memberi Tax kelak | Dilarang |
|---|---|---|
| billing | Snapshot commercial invoice/payment internet dengan tenant dan source reference | Tax mengubah outstanding, payment state, aktivasi atau harga historis |
| subscriptions | Snapshot SaaS invoice/source event operator | Mencampur pemasukan SaaS operator ke penjualan internet tenant |
| finance/ledger kelak | Posting/account/period dan TaxRule yang telah disetujui | Ledger kedua di Tax; menulis posted journal tanpa service/prosedur pemilik |
| tenancy/identity | Actor, scope owner/entitas yang dibuktikan, permission dan step-up | Tenant id sintetis untuk operator, null tenant sebagai bypass, support sebagai kuasa pajak otomatis |
| documents | Artefak/version/digest dan download authorized | XML export disebut submitted/issued/accepted tanpa bukti resmi |
| jobs | Ekspor/reconciliation via engine existing yang sudah diperbaiki | Queue/event bus kedua, blind retry provider |

Operator dan tenant adalah pemilik ekonomi berbeda. Hubungan satu tenant dengan satu atau beberapa entitas hukum tetap DEC-04; tidak memilih model multi-entity tanpa use case. Kontrak membawa owner scope dan source snapshot sehingga tidak memaksakan schema sekarang. Credentials/provider/storage/export/audit ikut scope yang sama; tidak ada fallback ke platform ketika tenant tidak terisi.

Tax OFF atau gagal tidak boleh menggagalkan penerimaan pembayaran, AAA atau konektivitas. Future Tax mengonsumsi boundary yang stabil, bukan menambahkan import Tax wajib di semua jalur inti. Coretax/PJAP, tarif dan compliance hukum tidak diverifikasi ulang pada audit engineering ini; tidak ada klaim integrasi atau opini perpajakan.

## 10. Kebijakan penambahan modul dan pengujian

Sebelum modul baru: satu tanggung jawab nyata, owner model/migration, daftar caller dan izin, paling sedikit satu workflow, acceptance risiko, config/flag default serta recovery. Reuse service/adapter existing. Jika belum ada caller, hindari abstraksi generik.

Review diff imports/model writes dan migration dependency; negative tenant/permission tests; service transaction/concurrency tests; request/job/response contract; backward schema compatibility dan smoke terarah. Usulan pemeriksaan otomatis hanya rencana, bukan tool baru pada sesi ini. Allowlist dependency existing memiliki path/alasan/owner, bukan wildcard permanen; bersihkan ketika callsite diperbaiki.

Kriteria selesai boundary: invariant pemilik dijaga, error/rollback dapat diuji, tidak ada akses tenant baru, caller lama kompatibel, dan laporan menunjuk bukti. Tidak mensyaratkan pemecahan file karena jumlah baris. [04](04_REVIEW_GATES.md) menetapkan siapa menilai dan bukti apa yang diperlukan.
