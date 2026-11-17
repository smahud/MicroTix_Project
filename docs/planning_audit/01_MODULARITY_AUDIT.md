# 01 — Audit aktual modularitas dan maintainability

Baseline: **`main@16085f825fef25ee4112d74b729c57e623b0bb05`**. Tanggal: 10 November 2026 WIB. **FINAL FOR OWNER REVIEW — audit statis**. Kesiapan dan keputusan ada di [README](README.md); kontrak target di [02](02_MODULE_CONTRACTS.md); operasi di [03](03_UPGRADE_PATCH_SAFETY.md).

## 1. Kesimpulan engineering

**Pertahankan modular monolith.** Struktur domain/service, PostgreSQL/RLS, job records, adapter RouterOS, typed frontend client dan dokumen immutable sudah memberi fondasi yang berguna. Tidak ada bukti bahwa pemecahan menjadi microservices akan memperbaiki masalah yang ditemukan.

Namun invariant penting belum konsisten: transaksi pembayaran, job fencing/recovery/permission, atomic enrollment, kuota, serta kesesuaian pilihan UI dengan efek backend. Ada direct writes lintas owner dan implicit projection hooks yang perlu kontrak kecil. Installer dan recovery mempunyai blocker terpisah. Klaim handoff bahwa beta hanya menunggu host tidak dapat dipakai sebagai kesimpulan audit ini.

Tidak ada skor kualitas numerik, benchmark, exploit, atau test runtime baru. “Terbukti statis” berarti bentuk kode ditemukan; konsekuensi race/exploit tetap **UNVERIFIED runtime** sampai acceptance dijalankan. Severity menunjukkan risiko bila jalur digunakan, bukan insiden yang telah terjadi.

## 2. Scope, reality check dan bukti

Checkout baru bersih; branch dokumentasi `docs/planning-audit-20261110` dibuat dari HEAD di atas. Clone mencakup histori dan remote refs. GitHub API mengonfirmasi default branch dan CI HEAD success [run 42285141174](https://github.com/smahud/MicroTix_Project/actions/runs/42285141174). CI ini memeriksa backend PostgreSQL, frontend dan docs; tidak membuktikan clean install/upgrade/restore/CHR.

| Area diminta | Hasil discovery di main |
|---|---|
| README, CONTRACT, ARCHITECTURE, PRODUCT, FINANCE | FOUND; dibaca sebagai pemilik kebutuhan, tidak diubah |
| IMPLEMENTATION_PLAN, ACCEPTANCE, test-cases.json | FOUND; katalog 85 task dan 256 designed cases/662 assertions, bukan 256 hasil PASS |
| `docs/planning_audit/` | NOT FOUND; lima dokumen dibuat dalam sesi ini |
| `docs/planning_mvp/` | NOT FOUND; tidak dibuat/diubah. Empat draft Tax eksternal dibaca hanya untuk compatibility konseptual |
| `backend/domains/` | 15 direktori termasuk common; 14 domain app terdaftar di settings |
| `backend/adapters/` | RouterOS base/factory/simulator/native API-SSL; radius/storage/ACS adapters terpisah NOT FOUND di lokasi contoh architecture |
| `apps/web/` | React/TypeScript; API live/mock, feature folders, query/session, permissions, design-system, tests/E2E |
| Database | 39 numbered migrations pada 11 domain apps; business dan schema radius; ledger belum ditemukan |
| Jobs/outbox | Engine PostgreSQL, management command, handlers; delivery outbox masih placeholder |
| Deployment/CI | `instalasi.sh` dan `.github/workflows/ci.yml`; unit/Caddy/firewall dibentuk installer. Root `infra/`, `deploy/`, `ops/` NOT FOUND; `backend/infra/postgres/` FOUND |
| GNS3 | Harness pada main NOT FOUND dalam scope inventory; artefak `lab/` ada pada PR #7 belum merged |
| Laporan/handoff | `report/` FOUND. Handoff main historis menyebut 8bb20c3; HEAD terbaru 16085f8 |

Open [PR #7](https://github.com/smahud/MicroTix_Project/pull/7) pada `d7fa35e5583bc36848e3b45497d2511739298c8a` menambah SSTP, migration 0011, installer dan lab. Review sesi ini hanya membedakan cabang dan memeriksa diff relevan; **bukan audit penuh PR #7**. Seluruh path/line temuan di bawah mengacu main. Bukti bisa dibuka dengan pola `https://github.com/smahud/MicroTix_Project/blob/16085f825fef25ee4112d74b729c57e623b0bb05/<path>#L<line>`.

Inventaris lengkap 379 file tracked baseline, blob SHA, import callsites dan metode cakupan tersedia di laporan/inventory yang ditautkan [laporan utama](../../report/planning-audit/20261109T210133Z-finalization.md). Inventaris/AST seluruh file tidak sama dengan membaca seluruh histori dan setiap baris secara manual. Runtime, perangkat, deployed privileges, konfigurasi host dan pemulihan tetap UNVERIFIED.

## 3. Domain inventory dan dependency map

| Domain | Model/state yang ditemukan | Status lingkup |
|---|---|---|
| identity | User, TOTP, recovery, token, support grant | IMPLEMENTED auth subset; support enforcement PARTIAL |
| tenancy | Tenant, Membership, Role/router_scope | IMPLEMENTED fondasi; router scope belum enforced |
| subscriptions | Plan, subscription, reservations, SaaS invoices/submissions/source events | PARTIAL kuota/otorisasi |
| customers | Customer, Service, AccessAccount, import/migration/decisions | PARTIAL workflow dan boundary |
| network | Router, enrollment, WG host/peer, discovery, operation, health | PARTIAL; simulator dan API-SSL dibedakan; CHR belum diverifikasi di sesi ini |
| radius | NAS, auth projection, accounting, cutover | PARTIAL; composite references dan deploy/lab gap |
| billing | Packages, service charges, internet invoice/line/payment/allocation | PARTIAL; payment tidak mengaktivasi service otomatis, tetapi race integritas belum ditutup |
| documents | IssuedDocument, snapshot/template/hash/artifact | IMPLEMENTED subset invoice/receipt; recovery storage UNVERIFIED |
| jobs | Envelope/detail, idempotency/outbox, engine | PARTIAL fencing/recovery/delivery |
| backups | Artifact, schedule, handler | PARTIAL; simulator manifest bukan backup router nyata/platform DR |
| audit | AuditEvent | IMPLEMENTED; redaction array PARTIAL |
| monitoring | Aggregate endpoint membaca network samples | PARTIAL; jangan mengklaim collector penuh/grafana setara |
| config | Defaults/branding/health, seed/grant | IMPLEMENTED fondasi; readiness DB-only belum schema-ready |
| i18n | Locale/enums/catalog | IMPLEMENTED fondasi |
| common | Context, crypto, envelope, pagination, base views, idempotency | IMPLEMENTED teknis dengan reverse dependencies |
| finance/ledger/tax/access/ACS/OLT | Domain directory NOT FOUND pada main | DOCUMENTED fase relevan; AccessAccount aktual milik customers |

Model/table/migration ownership detail: [02 §2](02_MODULE_CONTRACTS.md). Jangan memindahkan model semata agar sama dengan contoh directory dalam arsitektur.

### Import statis antardomain

Metode: Python AST; mengecualikan migrations dan management commands untuk tabel runtime berikut; menyertakan import deferred dan `AppConfig.ready`. Seed/management edges tetap dicatat terpisah di evidence inventory. Import relatif/dynamic string yang tidak membentuk `domains.*` membutuhkan review manual; graph bukan bukti semua dependency runtime telah ditemukan.

| Source | Target yang diimpor |
|---|---|
| audit | common |
| backups | common, config, jobs, network, tenancy |
| billing | audit, common, customers, documents, jobs, subscriptions, tenancy |
| common | i18n, identity, jobs, tenancy |
| config | common, i18n |
| customers | audit, common, jobs, network, subscriptions |
| documents | common, i18n |
| i18n | Tidak ada import domain lain terdeteksi |
| identity | common, i18n, subscriptions, tenancy |
| jobs | common |
| monitoring | common, config, network |
| network | common, config, customers, jobs, radius, tenancy |
| radius | backups, common, customers, jobs, network |
| subscriptions | audit, common, jobs, network, tenancy |
| tenancy | Tidak ada import domain lain terdeteksi |

Ada strongly connected component besar: audit/backups/common/config/customers/identity/jobs/network/radius/subscriptions. Penyebab meliputi signal registration, composition points, deferred imports dan mutasi bisnis dua arah. Ini **tidak membuktikan import crash**; tidak ada alasan untuk menghapus seluruh cycle melalui rewrite.

| Jenis dependency | Contoh | Disposisi |
|---|---|---|
| Sah | Billing baca service dan memanggil documents.issue_document; monitoring baca health network; identity membuat subscription saat onboarding | Pertahankan, kontrak input/scope/transaksi diuji |
| Perlu dibatasi | Quota membaca jumlah router/customer; common.views mengimpor identity; jobs/common saling membutuhkan | Document composition dan field/read contract; jangan sebar business policy ke common |
| Melewati owner | Customers menulis DiscoveryObject; radius menulis Router; billing view mengubah Service | PA-010, koreksi entry point kecil |
| Cyclic business coupling | Customers ↔ network, network ↔ radius, subscriptions → network di graph gabungan | Review callsites dan effect boundary; jangan menyebut semua import lintas domain pelanggaran |

## 4. Risk register dan prioritas

P0: kemungkinan kerusakan data/kebocoran/gangguan fatal; P1: risiko tinggi batas domain/permission/recovery; P2: maintainability/coverage; P3: cosmetic/developer experience. P0 yang ditemukan adalah **risiko integritas**, bukan laporan kerugian finansial aktual. Tidak ada P3 yang dijadikan blocker.

| ID | Prioritas | Masalah | Status fakta | Bukti review independen |
|---|---|---|---|---|
| PA-001 | P0 | Invoice balance/allocation race | CONFLICT | Database DB-01; Architecture AR-01 |
| PA-002 | P1 | Fencing, transaksi panjang, early-state recovery/cancel | CONFLICT/PARTIAL | Database DB-02/03 |
| PA-003 | P1 | Job permission dan router scope | CONFLICT/PARTIAL | Security SEC-02/06 |
| PA-004 | P1; session age P2 | Platform MFA, single-use concurrency, session policy | CONFLICT/PARTIAL | Security SEC-03/04/07 |
| PA-005 | P1 | Enrollment token/job atomicity dan leaked bypass GUC | CONFLICT/PARTIAL | Database DB-07; Security SEC-05 |
| PA-006 | P1 | Idempotency principal dan concurrent replay | CONFLICT | Database DB-05; Architecture AR-04 |
| PA-007 | P1 | Service quota count/lock/reservation units | CONFLICT | Architecture AR-02 |
| PA-008 | P1 selection; lainnya P2 | UI migration selection, filter, tenant-local drafts | CONFLICT | Architecture AR-03/08/09 |
| PA-009 | P1 sebelum consumer nyata | Outbox menandai tanpa delivery | PARTIAL | Database DB-04 |
| PA-010 | P2 | Ownership writes, implicit signals, storage helper coupling | PARTIAL | Architecture AR-05/06/07 |
| PA-011 | P1 | Composite RADIUS references dan privilege hardening | CONFLICT/PARTIAL | Database DB-06; Security tambahan |
| PA-012 | P1 upload; redaction P2 | Production scanner fail-open dan array audit redaction | CONFLICT/PARTIAL | Security SEC-08/09 |
| PA-013 | P2 sekarang; P1 sebelum real backup | Backup job menguji artifact terbaru, bukan miliknya | PARTIAL | Database DB-08 |
| OPS-01–09 | P1/P2 | Install, packaging, RADIUS, upgrade, restore, health, privilege, topology dan CI | Lihat [03 §2](03_UPGRADE_PATCH_SAFETY.md) | DevOps OPS-01–09; Security SEC-01 = OPS-07 |

Setiap bagian berikut memuat evidence, dampak, solusi minimum/alternatif, dependency/urutan, acceptance, downtime/rollback dan verifikasi. Detail reviewer lengkap dipertahankan di report; perbedaan severity AR-01 P1 versus DB-01 P0 diselesaikan dengan P0 karena invariant uang dapat rusak.

### PA-001 — Pembayaran berbeda dapat menulis outstanding yang sama

**Bukti:** `backend/domains/billing/services.py:587` mengunci payment; `_parse_allocations:559–567` membaca invoice tanpa `select_for_update`; `:602–608` menulis hasil penjumlahan Python dari nilai lama. `_lock_tenant:623` datang setelah update invoice. `billing/models.py:180–189` tidak menjaga kesamaan aggregate allocations dengan paid_amount.

**Dampak/risiko jika dibiarkan:** dua payment Rp200.000 pada invoice Rp300.000 sama-sama membaca paid=0, menerima alokasi, lalu update kedua menulis paid=Rp200.000 dari object lama; total alokasi dapat Rp400.000. Ini interleaving statis, **belum direproduksi**. Receipt, laporan dan sumber ledger/Tax menjadi tidak konsisten.

**Solusi paling sederhana:** lock invoice target dalam urutan deterministik sebelum validasi outstanding; validasi+update+allocation+receipt+audit/outbox tetap atomik. Alternatif lock tenant lebih awal menserialisasi seluruh uang tenant, sederhana tetapi lebih luas; ukur contention dan urutan lock dengan caller lain. Tidak perlu ledger baru untuk menutup race ini.

**Urutan/impact:** prioritas implementasi pertama; billing/documents dan consumer masa depan. **Acceptance:** dua koneksi PostgreSQL nyata, dua payment berbeda, barrier sebelum validasi; tidak overallocate; paid sama dengan jumlah allocation committed; sisa menjadi kredit/reject yang benar; multi-invoice reverse order bebas deadlock dan gagal tanpa receipt parsial.

**Downtime/rollback:** patch aplikasi dengan drain singkat bila diperlukan; constraint baru mengikuti expand/validate. Rollback kode tidak memperbaiki data historis; audit/reconcile dahulu, tidak otomatis mengubah uang. **Verifikasi:** CONFLICT statis, test concurrency NOT_RUN.

### PA-002 — Lifecycle worker belum fenced dan recoverable konsisten

**Bukti:** `jobs/engine.py:194` menyediakan `_fenced_save`, tetapi `transition_claimed:215`, `_mark:288`, retry `:311`, reconciler `:346` menulis berdasarkan id tanpa fence ekuivalen; hasil update fence juga tidak selalu menghentikan writer. `run_claimed:222` membungkus execute/verify dalam `tenant_scope`, yang membuka `transaction.atomic` di `common/tenant_context.py:51`. Reconciler `engine.py:340–343` hanya executing/verifying. Cancel `:367–379` memakai effect none, sementara maybe diatur setelah execute kembali (`:246`).

**Dampak:** writer lama dapat menimpa outcome, transaksi panjang menahan lock/progress, crash dapat meninggalkan committed CLAIMED yang tidak dipulihkan, cancel dapat dilabel aman saat send masih outstanding. Risiko menyentuh router/AAA ketika adapter nyata diaktifkan. Terminal retry juga berkonflik dengan ARCHITECTURE §6 (DEC-03).

**Solusi minimum/alternatif:** setiap state/result write memeriksa lease token+epoch+expected prior state dan berhenti bila authority hilang; commit tahap pendek, I/O di luar transaksi; recovery semua early states, heartbeat/deadline/drain. Tandai effect boundary sebelum potensi send; readback untuk ambiguity. Single dispatcher per router existing tetap perlu fence, bukan alternatif untuk menghilangkannya.

**Urutan:** bersama PA-003 sebelum real mutation/parallel worker dan OPS-04. **Acceptance:** stale worker dua koneksi tidak bisa success/retry/cancel/result; kill di semua state, long I/O tanpa DB transaction terbuka, progress terlihat koneksi lain, cancellation selama send bukan cancelled palsu; terminal tidak dihidupkan kembali. Job baru menautkan terminal asal jika retry diminta.

**Downtime/rollback:** drain worker; pending payload/state kompatibel; uncertain disimpan untuk readback, tidak blind replay saat rollback. **Verifikasi:** CONFLICT/PARTIAL statis; semua failure tests NOT_RUN.

### PA-003 — Otorisasi resource tidak diwariskan ke retry/cancel dan worker

**Bukti:** `jobs/views.py:70–97` memakai ActiveTenantApiView; `common/views.py:132–147` memverifikasi membership, bukan permission operasi. `jobs/engine.py:227–247`, `network/handlers.py:119–129`, `radius/handlers.py:249–254` tidak menguji kembali authority actor. `tenancy/models.py:63–64` menyimpan `router_scope`; pencarian production source menemukan pemakaian hanya model/migration.

**Dampak:** anggota tenant berizin rendah dapat mencapai aksi job tertentu; role/membership/router scope yang dicabut setelah enqueue belum menghentikan efek. Ini risiko intra-tenant, bukan bukti cross-tenant exploit.

**Solusi minimum:** mapping kecil job kind → owner permission/resource/step-up dan system-principal policy, reuse pemeriksaan existing saat request dan tepat sebelum efek; predicate router scope dipakai API/handler. Alternatif sementara nonaktifkan aksi yang belum mampu menegakkan scope dengan keputusan release eksplisit. Jangan framework policy baru.

**Acceptance:** viewer/agent tidak retry/cancel privileged job; revoke setelah enqueue menolak efek; system job tetap punya authority eksplisit; null/all, `[]`/none dan daftar router dibedakan; tenant asing 404. **Urutan/impact:** jobs/tenancy/network/radius/backups/monitoring sebelum ekspansi fitur. **Downtime/rollback:** re-evaluate backlog; rollback dengan menutup aksi terdampak, tidak memperluas izin. **Verifikasi:** CONFLICT/PARTIAL, runtime NOT_RUN.

### PA-004 — Platform MFA dan single-use belum ditegakkan menyeluruh

**Bukti:** `identity/services.py:185–191` membentuk sesi password-only bila MFA belum aktif, termasuk platform_admin; `subscriptions/views.py:142–148` hanya memeriksa platform flag. Faktor sekali pakai `identity/services.py:215–232` read-then-save tanpa lock/CAS. `session_expired:306–314` hanya dipanggil SessionView (`identity/views.py:126`), tidak shared authentication. Cookie delapan jam mengurangi jangkauan masalah absolute lifetime tetapi bukan bukti policy lengkap.

**Dampak:** privileged platform dapat password-only; race factor consumption mungkin menerima dua penggunaan; direct API tidak menjalankan seluruh policy umur sesi. Test force-login bukan bukti flow MFA.

**Solusi minimum:** platform session assurance pada login dan privileged entry dengan alur enrollment/recovery terbatas; row-lock/CAS untuk consume factor dan limiter tahap MFA; umur sesi pada shared auth. Tenant login password-only tetap sah sesuai baseline; jangan memaksakan policy login baru untuk semua tenant.

**Acceptance:** password-only platform tidak memperoleh business access, termasuk promote/stale session; dua koneksi satu recovery/TOTP → satu penerimaan; direct API menolak auth_at expired tanpa lebih dahulu GET session; idle dan absolute diuji terpisah. **Urutan/impact:** identity/subscriptions sebelum platform payment production. **Downtime/rollback:** revalidate/revoke sesi platform, tidak perlu schema diasumsikan; batasi akses bila rollback. **Verifikasi:** statis CONFLICT/PARTIAL, concurrency/abuse NOT_RUN.

### PA-005 — Enrollment tidak atomik dengan follow-up dan bypass tidak guaranteed-clean

**Bukti:** `network/services.py:734–736` mengaktifkan `app.enroll_bridge` session-level (`false`) tanpa finally. Policy `network/migrations/0007_enroll_bridge_policy.py:12–15` membuka SELECT enrollment ketika flag on. Lookup `services.py:735` tanpa lock; state check `:746–756` sebelum transaction `:758–785`; job baru dibuat `:789` setelah commit; replay `:752–753` tidak memulihkan job hilang. Callback `network/views.py:222` plain APIView.

**Dampak:** exception dapat menyisakan bypass pada koneksi reuse; crash sesudah token consume dapat strand enrollment; dua callback berbeda key berpotensi menulis identitas dari stale object. Tidak ada kebocoran atau takeover yang diuji pada sesi ini.

**Solusi minimum:** lookup exception sempit transaction-local/cleanup guaranteed; lock dan re-read pada trusted tenant transaction; token+peer+dedup job/outbox committed bersama. Gunakan pola existing email verify row-lock, bukan mekanisme token baru. Alternatif disable enrollment sementara jika cleanup/identity tidak dapat dibuktikan.

**Acceptance:** dua callback sama token/key → satu job; beda key → satu winner tanpa overwrite; crash setiap boundary tidak membuat accepted bootstrap tanpa durable follow-up; query failure mengembalikan GUC/koneksi fail-closed sebelum tenant lain. **Urutan/impact:** network/jobs/connection lifecycle sebelum onboarding produksi. **Downtime/rollback:** pertahankan identity/peer; reconcile stranded enrollment, jangan regenerate key otomatis. **Verifikasi:** statis CONFLICT; race/error reuse NOT_RUN.

### PA-006 — Identitas idempotency menghilangkan principal

**Bukti:** `common/idempotency.py:53–61` membangun/query scope operation+tenant+resource+key; principal hanya tersimpan `:70–75`, update response `:79` tanpa principal. UNIQUE `jobs/models.py:221` adalah scope+idem_key. Incomplete response mengizinkan reexecution (`idempotency.py:67–68`).

**Dampak:** actor berbeda dengan key sama dapat conflict/replay respons actor lain; concurrent same-key insert/recovery belum terdefinisi. Ini bukan bukti semua transaksi mengganda karena beberapa operasi punya business uniqueness.

**Solusi minimum:** principal konsisten dalam identity constraint/lookup/update; serialize claim/replay pada DB existing dan recovery per operasi. Preserve business dedup setelah TTL tujuh hari. Alternatif memakai satu server logical-action record per operasi, tanpa queue baru; perlu tetap memenuhi scope actor.

**Acceptance:** same actor/key/body replay, body beda 409, actor beda sesuai kontrak independent; permission diperiksa sebelum replay; dua request bersamaan satu logical effect, koneksi hilang setelah commit tidak menggandakan efek. **Urutan/impact:** common/jobs dan semua mutasi, sesudah PA-001 dan sebelum perluasan uang/network. **Downtime/rollback:** migration compatibility untuk old key; jangan hapus seluruh key; code rollback hanya dalam window yang ditentukan. **Verifikasi:** CONFLICT statis; concurrent tests NOT_RUN.

### PA-007 — Kuota dihitung pada batas lock yang salah

**Bukti:** `customers/services.py:120–136` memeriksa committed services sebelum subscription lock; `subscriptions/services.py:83–89` masih mengembalikan nol untuk services; `:125` lock baru terjadi kemudian; `_reserved:101–103` menghitung row, bukan SUM(units); usage `:175` nol service.

**Dampak:** dua create dekat limit dapat lolos stale check; batch reservation dan angka UI salah. **Solusi minimum:** satu keputusan quota di bawah subscription lock, committed count dari customers read contract dan SUM pending units; materialisasi+consume atomik. Alternatif koordinasi lock sempit lintas owner, bukan quota framework.

**Acceptance:** parallel create/import hanya menghabiskan kapasitas tersisa; units>1 benar; expiry/retry tidak double count; usage sesuai data nyata. **Urutan/impact:** subscriptions/customers/import/network dan UI sebelum paid entitlement relied upon. **Downtime/rollback:** patch kompatibel, reconcile account yang diterima; jangan menghapus akun berlebih otomatis saat rollback. **Verifikasi:** CONFLICT statis; race NOT_RUN.

### PA-008 — Pilihan UI tidak sampai ke efek dan state lokal tidak scoped

**Bukti utama:** `apps/web/src/features/imports/ImportRouterPage.tsx:94–103` menyimpan selection/profile/password lokal lalu commit tanpa payload; `api/live/adapter.ts:198–199` body undefined; `backend/domains/customers/views.py:594–614` missing dan `[]` menjadi None; `customers/services.py:749,763–766` None berarti semua snapshot. UI hanya mengambil 200 awal (`ImportRouterPage.tsx:53–56`).

**Bukti tambahan:** live adapter `:123–124` mengabaikan filters yang dikirim CustomersPage `:54–67`, meski backend mendukungnya. Draft `adapter.ts:184–193` mengabaikan tenant/router dan membaca key localStorage pertama; session cache clear tidak membersihkan localStorage. Profile/password choice dan hardcoded package wizard belum bukti workflow lengkap.

**Dampak:** memilih satu dapat mengadopsi akun lain termasuk halaman tak terlihat; tampilan filter menyesatkan; draft tenant/router lama dapat muncul di browser bersama. Tidak ada server cross-tenant leak yang dibuktikan.

**Solusi minimum:** typed selection+preview_revision sampai job; server membuktikan anggota snapshot; `[]` bukan all; kirim filter yang benar; namespace actor/tenant/router/migration/version dan validasi stored state. Alternatif tutup commit sementara dengan release decision, bukan mengubah requirement seleksi agar sesuai bug.

**Acceptance:** snapshot 201 akun, pilih satu → tepat satu; kosong → none/reject; stale/cross-scope ids conflict; actual query filter cocok hasil; dua tenant tidak memulihkan draft masing-masing; JSON rusak gagal aman. **Urutan/impact:** FE/customers/network/subscriptions/radius sebelum import aktif. **Downtime/rollback:** app/bundle patch, audit adoption historis secara eksplisit; invalidasi legacy local draft tanpa menghapus data server. **Verifikasi:** CONFLICT jalur statis, browser/runtime NOT_RUN.

### PA-009 — Outbox belum melakukan delivery

**Bukti:** `jobs/engine.py:406–417` hanya mengisi dispatched_at/attempts dengan komentar placeholder. **Dampak:** insertion atomik tidak berarti consumer menerima; future ledger/Tax tidak boleh bergantung pada flag ini. **Solusi minimum:** implementasi consumer pertama beserta ack/retry/dedup dan backfill event lama yang sudah ditandai, dalam engine existing. Alternatif panggilan service sinkron satu DB untuk invariant yang memang harus atomik; jangan event bus baru.

**Acceptance:** crash sebelum/sesudah source commit, consumer commit, ack; replay satu logical consumer effect; delivery gagal tetap recoverable; concurrent dispatcher tidak kehilangan event. **Urutan/impact:** sebelum feature bergantung pada delivery, bukan alasan memaksa seluruh future consumer masuk R1. **Downtime/rollback:** pause dispatcher bila perlu; rollback tidak menghidupkan event yang terlanjur marked, butuh replay/backfill sah. **Verifikasi:** PARTIAL eksplisit dalam kode, consumer proof NOT_RUN.

### PA-010 — Ownership dan side effect implisit memperluas coupling

**Bukti:** `customers/services.py:647,853` menulis network.DiscoveryObject; `network/services.py:930–934` menulis customers.MigrationSession; `radius/handlers.py:207` menulis network.Router; `billing/views.py:226–237` mengubah customers.Service.billing_package. `radius/apps.py:8–27` post_save/post_delete memproyeksikan AccessAccount sinkron. `billing/services.py:54` memakai subscriptions upload policy; proof ditulis `:497` sebelum claimed MIME ditolak `:498–501`. `documents/services.py:100–102` menulis file sebelum row DB; cleanup orphan masih disebut future.

**Dampak:** owner invariant/revision/audit bisa terlewat, bulk update dapat melewati signal, perubahan SaaS upload memengaruhi billing, rollback DB meninggalkan file. Rendering dalam transaksi memperpanjang lock, tetapi ukuran dampak belum diukur.

**Solusi minimum:** owner transition/assignment functions pada callsite nyata, documented synchronous projector contract dan test bulk/rollback; satu helper policy/storage kecil dengan dua caller; validasi sebelum write dan janitor orphan bounded dengan DB reference/age. Alternatif coordinator exception bernama dengan field/transaction test. Jangan pecah file karena panjang atau pindahkan semua query ke repository.

**Acceptance:** projected fields selalu berubah atomik dengan source, bulk tidak silent bypass; owner revision/audit konsisten; gagal MIME/DB/render tidak menyisakan orphan aktif setelah policy cleanup; hash/opaque path tetap. **Urutan/impact:** setelah P0/P1, pada touched flows dan sebelum volume dokumen/Tax naik. **Downtime/rollback:** biasanya code-only; file jangan dipurge bila masih dirujuk release lama/backup. **Verifikasi:** IMPLEMENTED callsites, enforcement PARTIAL; performance/cleanup NOT_RUN.

### PA-011 — RLS row visibility belum membuktikan seluruh reference/privilege invariant

**Bukti:** `radius/migrations/0001_radius_schema.py:27,41,55,73,89–90` FK router/account/service satu kolom. Composite cutover ada di `0004_cutover_run_rls.py:23–26`; tidak otomatis melindungi proyeksi lainnya. `config/management/commands/grant_runtime.py` memberi DML seluruh schema non-system, berbahaya bila future posted ledger mengikuti grant itu. Facade search_path `radius, public` dan owner/CREATE/TEMP grants perlu audit deployed DB; hardened property belum dibuktikan.

**Dampak:** row tenant A dapat merujuk parent tenant B akibat bug aplikasi walau RLS row visibility aktif; future ledger bisa mendapat direct DML. Ini gap invariant DB, bukan exploit API terbukti. **Solusi minimum:** inventory tiap reference tenant vs global, additive composite FK dan precheck data; privilege manifest sempit, facade owner/search_path/EXECUTE/CREATE review. Jangan per-tenant DB.

**Acceptance:** direct negative insert/update setiap reference tenant gagal; facade masih auth/accounting benar; runtime bukan owner/super/BYPASS, tidak memegang migrator secret (OPS-07); future posted tables ditolak direct DML/DDL/TRUNCATE. **Urutan/impact:** radius/tenancy/customers dan schema owners sebelum isolation sign-off/ledger expansion. **Downtime/rollback:** large radacct lock budget dan validation terpisah; melepas constraint tidak memperbaiki bad data. **Verifikasi:** PARTIAL/CONFLICT statis; grants/function-role behavior UNVERIFIED runtime.

### PA-012 — Production upload scanner default off; redactor tidak melintasi array

**Bukti:** `subscriptions/upload.py:79–96` default MT_SCAN_MODE=disabled, scan hanya exact clamav, unknown mode juga lewat; `clamd` import sebelum handler. Installer tidak menetapkan policy scanner produksi. Selain itu, **jalur billing internet saat ini** `billing/services.py:_store_proof:447–469` menulis berkas setelah sniff MIME/size tanpa memanggil scanner; import dari subscriptions hanya constants/sniff, bukan upload pipeline lengkap. Mengaktifkan scanner subscriptions saja tidak melindungi upload InternetPayment. `audit/models.py:28–40` membersihkan dict tetapi list dikembalikan apa adanya. Callsite yang diperiksa tidak membuktikan secret aktual tersimpan dalam list.

**Dampak:** proof dapat diterima tanpa scan yang diwajibkan; payload batch future dapat melewati redaction. **Solusi minimum:** explicit production fail-closed dan startup/preflight client/daemon validation; unknown mode reject; recursive list/tuple sanitization dengan allowlist event. Alternatif disable uploads saat scanner tidak sehat; tidak melemahkan baseline.

**Acceptance:** pada **kedua route SaaS dan internet payment proof**, absent scanner/client, timeout, infected, unknown mode menolak dengan error stabil; clean file punya bukti scan sebelum dapat ditinjau; nested list/dict secret redacted. **Urutan/impact:** subscriptions dan billing uploads existing, audit serta future documents sebelum file ditinjau di produksi. **Downtime/rollback:** service scanner/setup bila perlu; safe fallback menutup upload; data historis ditangani hanya jika bukti kebocoran ditemukan. **Verifikasi:** CONFLICT/PARTIAL statis, malicious-upload tests NOT_RUN.

### PA-013 — Verifier backup dapat memilih artifact job lain

**Bukti:** `backups/service.py:166–182` generation MAX+1 dan create; execute mengembalikan id `:223`; verify `:236–244` justru mengambil generating artifact terbaru router/category. `:118–129` masih simulator manifest, receiver/cleanup future.

**Dampak:** backup concurrent dapat race generation dan cross-commit artifact; tidak ada bukti restore binary. **Solusi minimum:** persisted exact job→artifact id, verifikasi bytes/hash milik itu, serialize generation dengan owner row/constraint. Alternatif satu backup aktif/router/category dengan constraint sederhana.

**Acceptance:** dua job tidak cross-verify; crash staging/commit/prune mempertahankan generasi recoverable terakhir; real transfer/restore gate tetap dibutuhkan. **Urutan/impact:** backups/network/jobs sebelum release real backup. **Downtime/rollback:** pause backup jobs, jangan prune last recoverable saat rollback. **Verifikasi:** PARTIAL; race/restore NOT_RUN.

## 5. Maintainability assessment dan keep-as-is

Pisahkan data ownership, I/O, transaction dan authorization karena alasan teruji di atas, bukan jumlah baris. File besar billing/customers/network mempunyai banyak tanggung jawab, tetapi baris panjang sendiri tidak menetapkan “god module”. Kandidat ekstraksi yang nyata: allocation lock/validation, migration selection contract, owner discovery transition, policy upload helper. Tidak perlu refactor massal services/views.

View/serializer boleh memvalidasi transport, tetapi perubahan Service.billing_package di billing view harus melalui owner agar audit/revision tidak ganda. Shared error envelope dan `/api/v1` dipertahankan. Catch/retry harus menyatakan definitive failure vs ambiguous external effect; pesan database tidak diekspos. Existing config registry dan snapshot dipertahankan; installer harus mengirim asset yang dibacanya.

Frontend sudah memakai route lazy loading (`App.tsx:8–30`), feature folders, design-system, shared typed client, strict TypeScript/noUncheckedIndexedAccess, serta tenant query keys pada banyak jalur. Pencarian reviewer tidak menemukan direct sibling-feature imports pada source yang diperiksa. Tidak perlu lazy-loading rewrite atau route plugin framework. Perbaiki selection/filter/draft dan flag/API behavior terlebih dahulu. Default idempotency UUID baru per adapter call perlu disimpan selama logical action, terutama ambiguity retry.

Domain/model ownership tetap satu codebase. Synchronous RADIUS projection dapat dipertahankan bila transaction semantics dan semua bypass path diuji. Permission role, locale/catalog, Decimal, issued-document hash/immutability, production live-mode guard, dan PostgreSQL tests adalah kontrol positif yang harus dipertahankan.

## 6. Kapasitas dan Tax compatibility

Target satu juta client tidak berarti polling satu juta client tiap detik. Aggregate network/router/session metrics by default; real-time hanya client terpilih dengan budget/TTL. Profile benchmark harus mencatat tenant, online sessions, auth/accounting rate, retention, reconnect storm, DB locks/IO, queue fairness, topology dan firmware. OPERATIONS §6 masih memakai contoh 300 service/tenant; CONTRACT §7 memakai target 1.000 online/tenant. Ini **coverage profile gap**, bukan izin menurunkan sasaran atau menaikkan klaim kapasitas. Proposal profile lanjutan perlu G4/G5, tidak diwajibkan untuk setiap R1 docs PR.

Tax compatibility terbatas pada ownership/scope/snapshot dan noninterference. Operator SaaS, tenant internet billing dan ledger/book bukan satu objek ekonomi. Tax/ledger belum implemented; platform source event immutable sudah ada, tetapi outbox belum consumer-ready. Tidak ada schema Tax, tarif, submission endpoint atau klaim compliance baru. Empat draft eksternal Tax diperiksa oleh orchestrator; reviewer yang menyatakan planning_mvp absent benar untuk repository, bukan bukti draft itu sudah masuk main. Batas modul ada di [02 §9](02_MODULE_CONTRACTS.md).

## 7. Urutan implementasi minimum dan test traceability

| Tahap berikutnya | Temuan | Bukti wajib sebelum menutup |
|---|---|---|
| Keputusan/integrasi docs | DEC-01/02 pada README | Disposisi owner dan docs CI valid tanpa pengecualian palsu |
| Integritas efek dan uang | PA-001/002/003/005/006 | PostgreSQL dua koneksi, crash boundaries, permissions, effect readback |
| Identity dan scope | PA-004/011/012, OPS-07 | Full-login, direct API, deployed role/tenant/scan negatives |
| Install/recovery nyata | OPS-01–06/08/09 | Clean/repeat Debian install, staged upgrade failure, full restore |
| UI/kuota/boundary terarah | PA-007/008/010 | Preview→payload→job exact set, concurrent quota, contract regression |
| Ekstensi berisiko | PA-009/013, future Tax | First-consumer replay, exact artifact recovery, flag-off noninterference |

Tahap dapat paralel hanya pada branch/worktree terisolasi dan dependency jelas. P0 uang tidak menunggu redesign deployment untuk dianalisis, tetapi produksi tidak dibuka sebelum gate terkait. Setiap patch punya report dan independent review; [04](04_REVIEW_GATES.md) mendefinisikan evidence matrix.
