# MicroTix — arsitektur dan kontrak implementasi

Pemilik kontrak engineering. Kebutuhan dan harga: [PRODUCT.md](PRODUCT.md). Nilai teknis: [defaults.json](defaults.json). Protokol/migrasi: [RADIUS.md](RADIUS.md), [ROUTEROS.md](ROUTEROS.md). Posting: [FINANCE.md](FINANCE.md). Tidak ada lapisan amendemen lain yang harus ditafsirkan agent.

## 1 Stack dan batas kompleksitas

| Bagian | Baseline |
|---|---|
| OS target | Debian 13; local CI boleh lingkungan kompatibel yang dicatat |
| Backend | Python 3.13, Django 5.2 LTS, DRF, drf-spectacular, Gunicorn |
| Frontend | React, TypeScript, Vite, pnpm, TanStack Query, FormatJS |
| Data | PostgreSQL 17; schema bisnis, radius, ledger |
| Pekerjaan | PostgreSQL job + transactional outbox + worker Python; tanpa Redis/Celery |
| AAA | FreeRADIUS 3.2, minimum 3.2.5 dan patch keamanan yang berlaku; rlm_sql PostgreSQL |
| Jaringan | WireGuard + nftables; native RouterOS API-SSL dengan pin; REST alternatif default off |
| Web | Caddy 2, HTTPS; SPA dan API same-origin |
| Penyimpanan | Adapter privat, filesystem volume khusus untuk pilot; ClamAV fail-closed |
| Monitoring | Prometheus internal untuk agregat platform/router; data sesi layanan di PostgreSQL |
| Dokumen | HTML→PDF dengan renderer dibatasi jaringan/file dan resource |
| R3 | GenieACS + MongoDB pada versi kompatibel terpin; belum dipasang pada R1 |
| Pengujian | pytest/Django, Vitest, Playwright, PostgreSQL nyata, FreeRADIUS nyata, CHR/GNS3 saat tersedia |

TK-002 memilih exact patch, Node LTS, pnpm dan dependensi pendukung yang kompatibel; verifikasi sumber resmi/security dan simpan lockfile/digest. Versi mayor di atas dipertahankan. Jangan mengisi versi atau digest fiktif. Tidak perlu mengaudit ulang seluruh dokumen untuk menentukan patch rutin. Ketidaktersediaan registry jaringan adalah blocker instalasi yang spesifik, bukan alasan mengganti stack.

Modular monolith: domain memanggil service layer. Jangan membuat microservices bisnis, Kubernetes, event bus, plugin framework, custom ORM, SDK multi-vendor generik, atau platform orkestrasi AI di dalam aplikasi. Adapter RouterOS internal tetap kecil dan mengikuti protokol resmi; pemakaian library eksternal memerlukan alasan kompatibilitas/lisensi, bukan rewrite seluruh aplikasi.

Pisahkan proses ketika hak/kegagalannya berbeda: API, worker bisnis, dispatcher-router, collector, backup-receiver, vpn-manager, FreeRADIUS, janitor accounting. Gunakan codebase/image yang sama untuk worker aplikasi; jangan membuat service bisnis baru per domain. Proses berhak host memakai systemd; aplikasi Compose; PostgreSQL native pada target produksi. Dev Compose boleh PostgreSQL/FreeRADIUS terisolasi, tanpa klaim setara deployment host.

Struktur implementasi: apps/web; backend/domains/{identity,tenancy,subscriptions,customers,access,network,jobs,backups,i18n}, kemudian billing/ledger/monitoring/field operations saat diperlukan; adapters/{routeros,radius,storage,acs}; infra/{compose,systemd,nftables,caddy,freeradius}; tests/{contracts,integration,router_lab,radius_lab,e2e}; locales/{id,en}. Docs tetap di tempatnya; tidak ada bootstrap untuk menyalin ulang dokumentasi.

## 2 Boundary jaringan dan privilege

Browser→Caddy→API memakai HTTPS dan cookie HttpOnly/Secure/SameSite=Lax + CSRF. API tidak memiliki root, CAP_NET_ADMIN, Docker socket, atau koneksi mutasi langsung ke router. Hanya dispatcher mengirim API mutasi dan RFC5176 Disconnect/CoA. Collector memakai credential baca. VPN manager menerima operasi typed create_peer/revoke_peer/reconcile lewat kanal lokal yang memverifikasi peer UID; tidak menerima shell atau ruleset bebas.

Publik: 443 dan UDP WireGuard yang dipilih deployment. RADIUS 1812/1813 dan backup receiver hanya bind alamat tunnel; API-SSL dan incoming Disconnect hanya dari alamat server yang diizinkan. Tolak peer-ke-peer, forwarding transit internet, akses peer ke DB/SSH/metrics/container/metadata/loopback; IPv6 deny kecuali dirancang dan diuji. Allowed-address peer router hanya endpoint server /32 yang nyata; tidak 0.0.0.0/0 atau subnet pelanggan.

Connector hanya menjangkau target registry terverifikasi (router_id→tunnel_ip+port). IP private yang memang target lab/manajemen diperbolehkan; metadata, loopback, redirect, DNS rebinding dan target arbitrary dilarang. Revalidate alamat saat koneksi. URL CPE/firmware juga input tidak tepercaya. Tidak perlu gateway jaringan generik; satu validator egress dan pembatasan host cukup untuk baseline.

TLS-ALPN pada Caddy memerlukan 443 langsung yang sesuai ACME. Jika deployment berbeda, pilih challenge/sertifikat yang benar sesuai akses aktual. Jangan menganggap domain, IP publik, Cloudflare Tunnel, atau port UDP sudah tersedia.

## 3 Identitas, tenant, dan akses

User global mempunyai membership pada beberapa tenant. Tenant aktif dari browser adalah permintaan konteks, diverifikasi setiap request/job/download/export/cache/metrics. Tenant switch membersihkan seleksi, namespace query cache dan subscription UI. Owner terakhir tidak boleh dihapus/didemote sebelum transfer sah.

Permission granular, bundel Owner, Teknisi, Admin Pembayaran, Akuntan, Viewer, Kolektor, Agen. Default Teknisi membaca operasional, tidak memverifikasi uang; Admin Pembayaran memverifikasi uang dan aktivasi manual, tidak mengubah WAN; Akuntan mengelola buku; Viewer baca; Kolektor hanya assignment dan penerimaan/setorannya; Agen hanya stok/penjualannya. Owner mengelola subscription/tim dan delegasi. Permission platform terpisah untuk pembayaran, rekening, dukungan, infrastruktur. Verifier pembayaran tidak otomatis mengubah rekening.

Nama izin minimum: customers.read/write, imports.run, migration.run, services.provision/activate/reveal_credentials, routers.read/enroll/release/configure, radius.cutover, profiles.write, backups.run/download, payments.verify, isolation.policy.manage, collections.receive/settle, vouchers.manage, agents.manage, devices.manage, prospects.manage, workorders.manage, ledger.post, period.close/reopen, platform.*. OpenAPI tiap aksi menyatakan izin; uji endpoint langsung, tidak cukup menyembunyikan tombol.

Autentikasi baseline: email+password Argon2id minimum 12 karakter; TOTP+recovery codes sekali pakai. Platform wajib MFA pada akses sesi. Operator tenant dapat login password; **semua aktor** yang menjalankan aksi sensitif wajib TOTP+reauth. Aksi sensitif: izin/rekening, cutover/rollback/restore, reveal secret/kunci, ekspor sensitif, override hold dan reopen periode. Reauth berlaku 600 detik dan batal saat sesi/role berubah. Login gagal dibatasi per akun dan per IP; pesan tidak mengungkap eksistensi akun. Sesi idle/absolut mengikuti defaults. Verifikasi/reset/invitation email berversi, sekali pakai, berumur pendek, redacted; development memakai Mailpit. Tidak ada WhatsApp OTP.

Policy ini mempertahankan kebutuhan produk. ASVS adalah referensi pengujian keamanan yang relevan; paket ini tidak mengklaim conformance penuh L2. Permintaan audit lama agar semua portal/operator dipaksa MFA login bukan keputusan produk yang telah disetujui. Perubahan policy tersebut dibuat eksplisit bila pemilik memintanya; tidak menjadi blocker global build. Portal R3 mengikuti credential individu, scope sempit, rate limit, recovery, dan step-up sensitif yang sama; jangan memberi sesi operator ke portal.

Super Admin hanya agregat kesehatan/kuota/paket/outcome. SupportGrant memerlukan Owner tenant, actor, alasan, scope, expiry, audit, banner, revoke; tidak membuka credential/key/raw backup. Root host tetap berkuasa secara teknis; jangan mengklaim zero access.

## 4 Data dan transaksi

PK UUID tunggal; setiap tabel tenant memiliki tenant_id, UNIQUE(tenant_id,id), indeks tenant-first, serta FK komposit (tenant_id,parent_id)→(tenant_id,id). Django ForeignKey biasa boleh tetap dipakai untuk ORM, tetapi migration SQL wajib menambah constraint komposit tersebut dengan reverse SQL dan uji negatif PostgreSQL. Jangan mengganti seluruh model dengan CompositePrimaryKey; dukungan relasi Django 5.2 terbatas.

ENABLE + FORCE RLS berlaku pada data tenant, termasuk proyeksi radius/ledger. Runtime dan owner fungsi bukan superuser, BYPASSRLS atau pemilik tabel yang dikecualikan. Migrator terpisah. Setelah membership tepercaya diverifikasi, set konteks tenant transaction-local pada koneksi/transaksi yang sama; konteks kosong gagal tertutup. Jangan SET tenant pada satu statement lalu berharap query berikut pada pool memakai koneksi sama. Uji commit/rollback/error/pool reuse. GUC sendiri bukan bukti identitas terhadap backend yang kompromi; query parameterized dan boundary autentikasi tetap wajib.

Envelope minimum job/NAS untuk dispatcher tepercaya dipisah dari isi tenant. Jangan memberi broad SELECT/DML semua tenant agar worker global mudah bekerja. Projection writer adalah principal terbatas: perubahan AccessAccount+radius projection tetap transaksi bisnis yang sama. Facade RADIUS dijelaskan di RADIUS.md. Fungsi SECURITY DEFINER memakai owner terbatas, trusted search_path, pg_temp terakhir, EXECUTE PUBLIC dicabut dan CREATE schema tepercaya dibatasi.

| Objek | Invariant minimum |
|---|---|
| Tenant/User/Membership | Membership aktif+role/scope sebelum data tenant dibaca |
| Router/VPNPeer/NAS | Satu tenant/router, tunnel IP unik global; credential refs; desired/applied revision; satu controller penulis |
| Customer/Service | customer_code/service_code unik tenant; satu customer dapat banyak service; preferred_router_id nullable |
| AccessAccount/Source | UNIQUE(tenant,username), exact case; kind/state/credential_state terpisah; banyak sumber router boleh menunjuk satu akun |
| Profile/Package/Binding | Profile observed perangkat; paket harga+upload/download; binding pool/profile per router beserta fingerprint versi |
| Reservation | Used = counted committed accounts + reserved units yang belum dimaterialisasikan; consume+account atomik; pending tidak double count |
| SaaS/internet invoice | Namespace/buku/rekening/permission terpisah; snapshot harga, periode, bahasa, timezone, tujuan pembayaran |
| Invoice tenant | UNIQUE(tenant,service,period_start,period_end,kind); issued lines immutable |
| Payment/Allocation | Payment sumber dana nyata unik; alokasi ≤nilai payment dan outstanding; row lock dengan urutan konsisten |
| Job/Outbox | event_id/dedup key unik; actor, resource, revision, deadline, config snapshot; tidak menyimpan secret literal |
| Ledger | Satu book per entry; source_event+posting_kind unik; debit=kredit lintas baris, posted immutable |
| Backup | Kategori dan retained membership per router; artifact immutable opaque id/path, size/hash/key_ref |

Waktu kejadian UTC timestamptz; tanggal bisnis DATE + timezone snapshot. Uang numeric(20,2)/Decimal, JSON string; tidak float. Bandwidth bit/detik integer. Username ≤64 karakter dan ≤64 byte UTF-8, tanpa kontrol/spasi tepi, tidak ditrim/lowercase diam-diam; Unicode hanya bila adapter round-trip exact teruji. allowed_router_ids null=semua router tenant dengan binding valid, []=tidak ada; relasi router tetap tenant-scoped. Static override router→static_ip valid→pool hanya bila static_ip null. Null, kosong, nol dan [] bukan sinonim.

Index awal berdasarkan query aktual: Service(tenant,preferred_router,lifecycle,id), Invoice(tenant,state,due_at,id), Job(state,available_at,priority,id), Source(tenant,router,namespace,natural_key). Trigram untuk pencarian jika query membutuhkan; partition accounting saat retensi/volume memerlukannya dengan directory sesi lintas partisi. Jangan membuat sharding atau seluruh indeks spekulatif.

## 5 API dan hasil asynchronous

Prefix /api/v1. Route tenant diverifikasi terhadap membership; route resource mengambil tenant dari record pada konteks aktif. Non-milik→404 generik; milik tetapi aksi tak diizinkan→403. 401 tidak login; 422 schema/parameter invalid. Cursor opaque urutan stabil (sort_key,id), limit default 50/maks 200; >maks/≤0/filter asing/cursor rusak ditolak 422. Locale memvariasikan response/cache bersama tenant.

| Operasi | Endpoint | Hasil/izin |
|---|---|---|
| Services | GET /tenants/{t}/services | 200; customers.read |
| Enrollment | POST /tenants/{t}/router-enrollments | 201; routers.enroll |
| Router bootstrap | POST /enroll/validate, /enroll/complete | 200; token body/kanal rahasia, bukan URL |
| Discovery | POST /routers/{id}/discoveries | 202; routers.read |
| Migration/CSV | POST /migrations/{id}/validate, /imports/{id}/validate; GET /migrations/{id}/identity-conflicts | 202/200; migration.run/imports.run |
| Commit | POST /migrations/{id}/commit, /imports/{id}/commit | 202 + preview_revision |
| Harvest S1 | POST /routers/{id}/password-harvest | 202; migration.run + step-up |
| Access | POST /access-accounts; PATCH /access-accounts/{id} | 201/200; services.provision |
| Packages/bindings | Tenant-scoped CRUD ditetapkan OpenAPI pada TK-408 | customers.read atau profiles.write |
| Cutover/status | POST /routers/{id}/radius-cutover; GET /routers/{id}/radius-status | 202 radius.cutover+step-up / 200 routers.read |
| Reveal | POST /services/{id}/reveal-credentials | 200; services.reveal_credentials+step-up; no-store |
| SaaS | POST /tenants/{t}/quotations; POST /saas-invoices/{id}/payment-submissions; GET /tenants/{t}/subscription | 201/201/200; subscription.manage |
| Platform payment | GET /platform/payment-submissions; POST /platform/payment-submissions/{id}/approve, /reject, /request-revision | Izin platform sesuai aksi, tidak payments.verify tenant |
| Rekening platform | PUT /platform/payment-destinations/{id} | Izin rekening platform + step-up |
| Internet payment | POST /payments/{id}/verify | 200; payments.verify; tidak mengirim aktivasi otomatis |
| Aktivasi | POST /service-action-batches | 202 parent_job_id; services.activate |
| Isolir policy | POST /tenants/{t}/isolation-simulations; PUT /tenants/{t}/isolation-policy | 201/200; isolation.policy.manage, simulation_id valid |
| Backup/download | POST /routers/{id}/backups; GET /backup-artifacts/{id}/download | 202/authorized download gateway; backups.run/download |
| Release/replace router | POST /routers/{id}/release, /replace | 202/201; routers.release |
| Job | GET /jobs/{id} | 200; izin resource yang mendasari |
| Meta/health | GET /meta/enums?locale=id; /health/live; /health/ready | Enum authenticated; health hanya status minimal |
| R2 kolektor | POST /collections, /settlements | collections.receive/settle |
| R3 voucher/ACS | POST /voucher-batches; POST /vouchers/{id}/revoke; POST /devices/{id}/tasks | 202/202/202; izin domain |

OpenAPI mengikat request/response/status/permission/validation/idempotency sebelum frontend memakainya. Endpoint domain lain dibuat pada fase aktif dengan pola yang sama; jangan membangun API palsu untuk fitur masa depan.

Error: {code,message,request_id,locale,field_errors,retryable}; field_errors[field] adalah daftar {code,message}. Kode: validation_error 422, unauthorized 401, forbidden 403, not_found 404, quota_exceeded/revision_conflict/idempotency_conflict/conflict/unsupported_capability 409, rate_limited 429+Retry-After integer detik, router_unreachable/dependency_unavailable 503 pada probe sinkron atau safe_error job, verification_failed pada outcome job (409 untuk request sinkron yang memang memverifikasi). Kode mesin stabil, message dilokalkan.

Idempotency-Key wajib untuk uang, provisioning akun, commit import, cutover, aktivasi, voucher, backup request dan ACS. Scope principal+tenant/platform+operation+resource+key; hash canonical body/file. Sama+isi sama mengembalikan logical action yang sama; isi berbeda→409. Secret pada request dibanding HMAC; jangan cache plaintext secret/reveal response. Retensi key tujuh hari tidak menghapus business uniqueness. expected_revision pada update menolak stale write.

202 mengembalikan job_id/status_url atau parent_job_id/count; 201 akun hanya record/proyeksi, bukan perangkat online. Frontend poll status memakai defaults, menutup browser tidak membatalkan pekerjaan. Retry hasil tak pasti memakai key semula; jangan menciptakan efek baru dengan key baru.

## 6 Job, deadline, dan fencing

Domain change + audit redacted + outbox satu transaksi. on_commit hanya wake-up; polling tetap wajib. Job claim memakai SKIP LOCKED, transaksi pendek, tidak menahan lock DB saat I/O jaringan. Actor/permission/policy/revision terkini diperiksa sebelum efek. Maksimum attempt/backoff/lease mengikuti defaults; satu dispatcher pemilik mutasi per router. Fairness tenant dan pool collector/backup terpisah mencegah pembayaran/recovery kelaparan.

| State | Berikut yang sah |
|---|---|
| queued | claimed, cancelled |
| claimed | preflight, retry_wait, failed, cancelled |
| preflight | executing, waiting_dependency, retry_wait, failed, cancelled |
| executing | verifying, uncertain, failed, recovery_required; cancelled hanya zero effect+fence |
| verifying | succeeded, uncertain, failed, recovery_required |
| waiting_dependency, retry_wait | queued, cancelled, failed |
| uncertain | verifying setelah readback; retry_wait hanya bila terbukti belum diterapkan; recovery_required, failed |
| recovery_required | verifying setelah recovery berizin, failed |
| succeeded, failed, cancelled | Terminal; permintaan baru menjadi job baru yang menautkan asal |

effect_state none/maybe/confirmed adalah efek tujuan, termasuk commit proyeksi auth/posting keuangan. executing tidak otomatis berarti sudah ada efek; cancelled sah hanya none terbukti, tanpa pengiriman outstanding dan semua worker/koneksi lama telah dihentikan/difence. maybe/confirmed tidak dapat dilabeli cancelled untuk menyembunyikan efek. Lease habis pada executing/verifying→uncertain. Epoch dicek sebelum kirim; RouterOS tidak mengenal epoch DB. Pemilik baru tidak mengirim sampai penulis lama tidak dapat mengirim dan readback selesai. Kompensasi menjaga audit dan hanya objek/revision yang benar, bukan inverse global.

Kind yang dibangun saat fase terkait: discover_router, harvest_passwords, commit_migration, radius_cutover_step, disconnect_session, apply_account_attributes, suspend_service, activate_service, backup_router, acs_task, issue_vouchers, recognize_revenue, lifecycle_saas, radius_janitor, enrollment_reconcile, nas_client_reload, import_commit, router_release, router_replace, change_plan, verify_api_ssl. Handler harus mendefinisikan typed input, dedup, effect boundary, verifier, retry aman, deadline, cleanup/recovery. Tidak perlu membuat generic DSL/registry service.

Deadline engineering awal: simple operation memakai router.job_deadline_s; backup memakai backup.job_deadline_s; ACS memakai acs.task_ttl_s termasuk menunggu Inform. Discovery/import/recognition dikerjakan dalam chunk bounded dengan deadline per task yang ditetapkan adapter/worker dan dicatat di config; agent boleh memilih nilai terukur di lokal tanpa meminta keputusan bisnis. Cutover/WAN/soak/fault memerlukan run budget eksplisit: B3 minimal 1.800 detik observasi, B4 minimal 86.400 detik, ditambah setup/recovery. Jangan memakai deadline 60 detik untuk observasi itu. Kegagalan efek tak pasti tidak pernah dibuat aman hanya dengan retry budget.

## 7 State domain dan kredensial

| Objek | State/arti |
|---|---|
| Enrollment | draft→enrollment_issued→bootstrap_pending→tunnel_seen→api_verified→discovery_ready; conflict/expired/revoked |
| Discovery object | discovered/selected/adopted/ignored/conflict/stale; drift missing_source/needs_review/hold_unknown/local_account_shadow/binding_invalid |
| Migration/import | uploaded atau discovered→validating→review→committing→completed/partial/failed; cancelled/expired |
| Cutover | planned→preflight→parity_check→client_installed→canary→shadow_active→authoritative; failed/rolled_back; B0–B6 di RADIUS |
| Router enforcement | local/radius_shadow/radius_authoritative/degraded |
| Account | active/suspended/disabled/expired; credential unknown/ready/rotation_pending terpisah |
| Service lifecycle | draft/pending/provisioning/provisioned/conflict/failed/terminated/archived |
| Billing eligibility | not_billed/current/overdue/exempt |
| Isolation reason | none/overdue/policy/manual_hold/security_hold/technical_hold |
| Desired / observed network | active/suspended/unmanaged / enabled/disabled/missing/unknown |
| Connection | online/offline/unknown dari accounting, bukan payment atau enabled |
| Isolation operation | normal→requested→applying→verified/failed/unknown; arah suspend/restore tersimpan |
| Payment submission | submitted→reviewing→approved/revision_requested/rejected |
| Internet invoice | draft/open/partial/paid/void; SaaS juga expired |
| SaaS subscription | free atau pending→active→grace→restricted→ended; renewal mengikuti PRODUCT |
| Backup | scheduled→creating→transferring→verifying→committed→expired; failed/abandoned |
| ACS task | queued/waiting_inform/running/verifying/succeeded/failed/expired/cancelled; outcome job terpisah |
| Prospect/install | prospect→survey→scheduled_install→installed→active; lost |
| Ticket | open→triaged→assigned→in_progress→resolved→closed; reopen tercatat |

partial bulk dan stale freshness bukan state job. verified_active berarti autentikasi diizinkan, bukan perangkat online. paid-awaiting-activation label turunan, tidak memicu auto restore.

Credential terenkripsi dengan key di luar DB; secret projection radius dikecualikan hanya pada boundary daemon tepercaya. CSPRNG untuk semua token/password. Password baru tampil sekali; reveal ulang izin+step-up+audit, auto-hide 30 detik, no-store; bukan tabel/URL/log/analytics/export biasa. Encrypted offboarding export Owner adalah alur khusus. Kunci lama untuk backup generasi lama tetap dapat dipulihkan setelah rotasi.

Upload MIME magic bytes+ukuran+parser bounded, ClamAV nyata dan definisi sehat sebelum file dapat dilihat/disetujui; scanner unavailable/quarantine gagal tertutup. Stub hanya development berlabel dan tidak memenuhi gate upload. Path opaque non-executable, signed download TTL 300 detik melalui gateway yang memeriksa sesi+izin saat penukaran, bukan bearer URL publik. PDF hanya aset terdaftar, tanpa akses URL arbitrary/file lokal. CSV export formula-safe. Email reset token adalah pengecualian URL terbatas dengan redaction/no-referrer.

## 8 Penegakan ledger dan periode

FINANCE.md memiliki seluruh posting rules. Akses ledger melalui fungsi ledger.post_entry, runtime tanpa direct INSERT/UPDATE/DELETE tabel posted. Fungsi SECURITY DEFINER non-superuser/non-BYPASSRLS, scope book+tenant diperiksa, trusted search_path, EXECUTE PUBLIC dicabut. Period lock FOR SHARE pada posting dan lock eksklusif pada close; deferred constraint trigger debit=kredit seluruh baris; trigger immutability posted. Uji bypass langsung, mixed-tenant, race close/post dan event retry pada PostgreSQL nyata. Jangan menganggap validasi serializer cukup.

R1 menyimpan immutable source event pembayaran platform agar R2 dapat membentuk buku platform tanpa duplikasi. Buku penuh dan laporan resmi dibangun R2; tidak perlu framework accounting future di P0. Seed COA dan template dari FINANCE; tidak menyalin tabel harga atau rekening ke frontend.

## 9 Konfigurasi dan branding

defaults.json memiliki tipe/unit/default/scope/bounds/change rule. Precedence default→override sah→snapshot immutable per job/document. Validasi unknown/duplicate/alias collision, connect≤read≤deadline untuk operasi sederhana, heartbeat<lease/2, ratio warn<stop, dan nilai retensi minimum. Parameter future feature belum harus hadir pada runtime R1; tidak menghapus requirement fase itu.

branding.json di-resolve backend: override environment nonempty→file; PROJECT_NAME mengalir ke APP_NAME/BRAND_NAME jika override khusus tidak ada. Frontend memperoleh resolved public config dari backend, sehingga perubahan nama tidak memerlukan build ulang SPA. Nama display tidak menjadi DB name, cookie name, tenant UUID, API prefix, encryption context, namespace router atau signature. project_id stabil sesudah instalasi; namespace rtrw pada router adalah identifier internal, tidak ikut berubah saat brand diganti. Uji ubah nama lalu restart/reload config: sesi/data/pembayaran/RADIUS tetap berfungsi dan seluruh label produk berubah.

Saat build belum ada domain/logo/kontak publik, jalankan dev dengan placeholder lokal yang jelas. Publikasi memerlukan nilai nyata dan konten privasi/layanan; jangan memblokir unit test/fitur lokal karena metadata publik belum diisi.
