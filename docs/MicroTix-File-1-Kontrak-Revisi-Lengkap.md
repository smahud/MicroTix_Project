# MicroTix — Kontrak Dokumen Hasil Audit v2.1

Tanggal revisi: 29 Oktober 2026, Asia/Jakarta. Pemilik produk menurut sumber: Huda Choirul Anam.
Mandat audit ini: perbaikan dokumen dan desain pengujian; bukan implementasi, akses server, atau pelaksanaan pengujian aplikasi.

## 0. Cara membaca, lingkup, dan anotasi

[TAMBAHAN AUD-01] Dokumen ini merupakan amendemen normatif lengkap untuk paket dokumentasi yang dilampirkan. Ia tidak menghapus kebutuhan produk atau backlog asal yang tidak dikoreksi. Seluruh dokumen pendamping tetap disertakan dalam ZIP revisi. `MicroTix-File-1-Seluruh-Isi-Arsip.md` adalah salinan gabungan input Sol, bukan proyeksi paket final setelah konsolidasi. Ekspor final terdiri dari satu dokumen konsolidasi tiga kontrol dan satu ZIP; lihat §23 MAC-02.

Penanda perubahan:

- `[REVISI AUD-nn]`: mengganti aturan atau klaim lama pada pokok yang disebutkan.
- `[TAMBAHAN AUD-nn]`: melengkapi kontrak yang sebelumnya belum ditentukan.
- `BASELINE`: keputusan produk yang dipertahankan.
- `AUDIT_DEFAULT`: pilihan desain yang ditetapkan dalam revisi berdasarkan mandat perbaikan dokumen ini; bukan fakta server atau persetujuan eksekusi.
- `OBSERVED`: hanya diisi dari pemeriksaan atau eksekusi yang benar-benar dilakukan.
- `BLOCKED`: prasyarat tidak terpenuhi; tidak boleh dianggap PASS.

Aturan “jangan mengubah dokumen sumber” dalam paket lama tidak membatasi audit yang secara eksplisit diminta pemilik sekarang. Keputusan komersial, rekening, dan nomor konfirmasi dipertahankan. Koreksi teknis dijelaskan dan ditautkan ke AUD-nn; tidak diklaim sebagai keputusan historis pemilik.

## 1. Kewenangan, sumber kebenaran, dan satu kali perintah

[REVISI AUD-02] Urutan kewenangan: instruksi eksplisit pemilik yang berlaku → amendemen v2.1 ini untuk pokok yang dikoreksi → keputusan produk pada decisions log → PRD → Technical Design → spesifikasi domain → UI/UX → tugas → dokumen quality dan audit. Temuan baru tidak boleh diselesaikan dengan memilih sumber yang paling mudah diimplementasikan. Catat konflik, pilih default aman yang sudah ditentukan, dan blokir hanya pekerjaan yang bergantung pada konflik tersebut.

Sumber kebenaran tetap: PRD untuk kebutuhan, harga, dan gerbang; TD untuk API/job/registri parameter; panduan akuntansi untuk posting; spesifikasi RADIUS/ACS untuk protokol; UI/UX untuk layar; tasks untuk dependency TK; File 2 untuk deklarasi akses aktual. Saat ada koreksi AUD, bagian sumber yang ditunjuk wajib membacanya sebagai pengganti klausul lama. `docs/decisions.md` hanya menjadi catatan implementasi dan ADR baru, bukan salinan keputusan yang boleh menyimpang diam-diam.

[REVISI AUD-03] Mode kerja bukan tangga kewenangan:

| Mode | Diizinkan | Prasyarat |
|---|---|---|
| A | Membaca/menulis dokumen, analisis statis dan integritas di workspace | Mandat audit dokumen |
| B | Inventaris dan pengujian pada target nonproduksi tertentu | Manifest File 2 terotorisasi; setiap operasi tercantum pada scope |
| C | Implementasi kode dan aktivitas repository pada workspace tertentu | Mandat implementasi eksplisit; deploy/staging/prod masing-masing harus tercakup |

Mode C tidak otomatis memberi akses server; Mode B tidak otomatis mengizinkan pengembangan aplikasi; Mode A tidak mengizinkan keduanya. Lingkungan produksi dan router pelanggan tidak menjadi target Mode B. Pilot G3 memakai mandat perubahan produksi tersendiri, bukan perluasan tersirat izin lab. Semua kredensial teknis hanya sarana akses.

[TAMBAHAN AUD-04] Satu kali perintah berarti agent menjalankan seluruh dependency yang sudah memiliki input dan otorisasi, kemudian menghasilkan hasil terminal yang deterministik. Itu tidak berarti agent dapat mengarang alamat host, citra, lisensi, hasil review akuntan, atau persetujuan produksi. Jangan meminta persetujuan ulang untuk aksi yang sudah tercakup manifest yang masih berlaku. Pratinjau/diff menjadi artefak run; tidak selalu merupakan checkpoint interaktif baru.

Urutan terminal: `FAILED` bila invariant dilanggar; jika tidak, `BLOCKED` bila ada item wajib yang belum dapat dikerjakan; jika tidak, `COMPLETED`. `COMPLETED` selalu menyebut scope, misalnya `documentation_revision`, dan tidak berarti aplikasi selesai. Aksi independen yang aman tetap dilanjutkan. Hasil wajib menyebut missing fields, blocker, pekerjaan selesai, dan pekerjaan yang tidak dijalankan.

## 2. Integritas paket, versi, referensi, dan bootstrap

[REVISI AUD-05; HISTORIS TAHAP SOL] Paket masukan audit sebelumnya berisi 32 berkas, total 549.017 byte sebelum direktori ZIP dihitung. Verifikasi ulang terhadap manifest v2.0 menemukan 31/31 entri sesuai ukuran dan SHA-256. Klaim “13/13 sumber v1.4 telah diverifikasi” dalam laporan lama adalah catatan historis; arsip sumber v1.4 yang terpisah tidak disertakan sehingga audit sekarang tidak menyatakan telah memverifikasinya ulang.

Manifest v1.4 dan v2.0 dipertahankan sebagai provenance, bukan manifest aktif. Hanya `sumber/source-manifest_v2_1.md` memvalidasi berkas aktif. Manifest tidak memuat hash dirinya sendiri. Integritas hash membuktikan kesesuaian byte dengan manifest yang diterima, bukan autentisitas penerbit; untuk distribusi lintas trust boundary gunakan tanda tangan atau checksum melalui kanal tepercaya.

[REVISI AUD-06] `bootstrap_docs.sh` lama hanya disertakan untuk audit; jangan dijalankan sebagai jalur instalasi v2.1. Cacat konseptualnya: berkas hilang dapat dilewati, parser bisa menghasilkan nol entri tanpa gagal, ukuran/kelengkapan tidak dipastikan, dan salinan dapat menimpa berkas repository berbeda. Audit ini tidak menulis pengganti kode instalasinya.

Kontrak penerus bootstrap untuk TK-001: validasi seluruh manifest sebelum membuat/mengganti target; minimal satu entri dan tepat seluruh berkas yang diwajibkan; cocokkan path, ukuran, dan hash; tolak path traversal, duplikat, symlink target, dan berkas hilang; berkas tujuan identik boleh dilewati; berkas tujuan berbeda wajib menjadi conflict atau disimpan ke staging review, tanpa overwrite otomatis. Keberhasilan menyalin sebagian bukan keberhasilan bootstrap. Manifest hasil penempatan harus memetakan source path ke target path, termasuk AGENTS/tugas dan quality/audit. Jangan menulis hasil verifikasi ke manifest yang sedang diverifikasi.

[REVISI AUD-07] Referensi ke “master prompt §10/§14/§16” dalam paket lama bukan dependency yang tersedia. Kontrak v2.1 ini menggantikan kebutuhan referensi tersebut. Versi dokumen aktif yang direvisi memakai v2.1; riwayat dan manifest provenance tetap bertanggal/berversi asal. File 2 wajib menyatakan pasangan `document_contract_version: "2.1"`.

## 3. Baseline produk yang dipertahankan

Tenant adalah perusahaan; user global memperoleh membership dan scope tenant. Router milik satu tenant; satu controller penulis aktif. Pelanggan dapat memiliki beberapa service; satu access account terkelola PPPoE/Hotspot adalah satu unit layanan. Identitas akses tidak terikat perangkat. Discovery/adopsi/commit data tidak menulis konfigurasi router. Cutover adalah operasi terpisah.

Fase produk: R1 fondasi, i18n, SaaS billing, VPN, discovery/adopsi, RADIUS/cutover, CSV, pelanggan, monitoring dan backup; R2 billing internet, isolir/aktivasi, kolektor dan ledger; R3 voucher/agen, ACS, portal, tiket, inventaris, ODP, instalasi, notifikasi, FUP dan edge replica; R4 WAN, failover/PCC, templat jaringan dan OLT per model. Tidak ada klaim semua perangkat didukung atau satu VM pasti melayani 1.000 tenant.

| Paket | Router | Layanan | Tim aktif | Kolektor/agen eksternal maksimum | Bulanan IDR | Tahunan IDR |
|---|---:|---:|---:|---:|---:|---:|
| Free | 1 | 50 | 3 | 5 | 0 | 0 |
| Bronze | 2 | 150 | 5 | 20 | 500000.00 | 5000000.00 |
| Silver | 3 | 300 | 8 | 50 | 1000000.00 | 10000000.00 |
| Gold | 4 | 500 | 12 | 100 | 1500000.00 | 15000000.00 |
| Diamond | 5 | 750 | 20 | 200 | 2000000.00 | 20000000.00 |
| Platinum | 25 operasional | 5000 operasional | 50 | 500 | 4000000.00 | 40000000.00 |

Platinum tetap dipasarkan tanpa batas lisensi dengan plafon fair use yang terlihat. Peningkatan plafon memerlukan bukti kapasitas dan konfigurasi entitlement, bukan perubahan hardcode. Tahunan membeli 12 bulan dengan harga 10 bulan. Batas eksternal pada tabel berlaku gabungan identitas kolektor/agen unik; orang dengan kedua peran dihitung sekali, bukan mendapat dua kuota terpisah [AUDIT_DEFAULT AUD-08].

Rekening seed atas nama Huda Choirul Anam, belum diverifikasi eksternal:

| Metode | display_value |
|---|---|
| BCA Digital via BI Fast | 0022 0322 2222 |
| BCA | 3300589323 |
| Mandiri | 1710007451217 |
| SeaBank | 901635594814 |
| Bank Jago | 108337184986 |
| Superbank | 000029261674 |
| Krom Bank | 770080857777 |
| DANA/GoPay/OVO | 082319199930 |

Nomor konfirmasi: `082319199930`. Simpan sebagai teks; nol awal dan spasi tampilan dipertahankan. Invoice menyimpan snapshot. Rekening hanya tampil pada halaman pembayaran terautentikasi; `published=false` tidak boleh dinyalakan untuk menghindari aturan landing. Perubahan rekening dilakukan oleh permission terpisah dengan MFA/reauth/audit. Klik WhatsApp adalah navigasi oleh pengguna; agent tidak mengirim pesan otomatis. BRAND_NAME/DOMAIN/LOGO/CONTACT wajib sebelum publikasi, tidak diisi dengan tebakan.

## 4. Registri parameter dan nilai efektif

[REVISI AUD-09] Setiap parameter wajib mempunyai `key`, tipe, satuan, default, scope, batas, klasifikasi, sumber, versi efektif, dan aturan perubahan. `null` berbeda dari `0`, string kosong, atau daftar kosong. Unit biner: MiB=1.048.576 byte, GiB=1.073.741.824 byte; bandwidth bit/detik; waktu durasi memakai detik kecuali key eksplisit `_days/_months/_years`. Persentase disimpan sebagai rasio decimal. Jangan mengonversi uang melalui float.

Nilai baseline TD §16 dipertahankan, dengan normalisasi berikut:

| Kelompok parameter | Default dan batas operasional |
|---|---|
| csv.max_bytes/max_rows | 10485760/10000; plafon 20971520/20000; kedua batas berlaku; kenaikan hanya setelah uji beban |
| csv.temp_file_ttl_s | 86400; plaintext password tidak disimpan selama TTL, segera dienkripsi saat masuk |
| enroll.token_ttl_s | 900; integer 60..3600; token 256 bit; sekali pakai pada complete |
| vpn.pool_cidr/keepalive_s/mtu | 100.127.0.0/16; 25 jika NAT; 1420 nilai awal yang diuji; overlap menghentikan enrollment |
| router.connect/read/job_deadline_s | 5/15/60; deadline 60 untuk job sederhana, tidak untuk backup/cutover/ACS/soak |
| job.max_attempts/backoff_cap_s | 5 total attempt termasuk pertama; 300; retry hanya kegagalan terbukti aman |
| job.outbox_poll_s/circuit_failures/half_open_s | 2/5/60 |
| job.lease_s/heartbeat_s | 30/10, AUDIT_DEFAULT; lease habis tidak mengizinkan dua penulis |
| poll.health/inventory/detail_s | 60/900/15; detail hanya saat halaman aktif, shared cache dan budget |
| drift.scan_interval_s/discovery.concurrent_per_router | 21600/1 |
| quota.reservation_ttl_s/draft_ratio/min/max | 3600/0.25/10/500; pending tidak kedaluwarsa otomatis |
| saas.grace/restricted_until/vpn_retention/data_retention_days | 7/30/60/180; titik awal menurut §5 |
| saas.invoice_expiry_days/router.replace_overlap_days | 7/30 |
| isolation.grace_days/enabled/simulation_ttl_s | 3, integer 0..30 / false / 86400; jadwal 01:00 zona tenant |
| invoice.lead_prepaid/postpaid_due_days | 7/7 |
| backup.routine/manual/prechange_max | 100/10/10, plafon katalog per kategori per router |
| backup.max_artifact_bytes/warn_ratio/stop_ratio | 67108864/0.80/0.90 |
| backup.job_deadline_s/download.url_ttl_s | 1800 AUDIT_DEFAULT / 300; perpanjangan deadline harus masuk profil run |
| idempotency.retention_days | 7; business uniqueness tidak ikut berakhir |
| log.app/access/security_days | 30/90/400; audit finansial mengikuti dokumen keuangan |
| metrics.raw/aggregate_5m/aggregate_1h_days | 15/90/400 |
| auth.failed_max/window_s/password_min_chars | 5/900/12; per akun dan per IP mempunyai counter terpisah |
| session.tenant_idle/absolute_s | 28800/86400 |
| session.platform_idle/absolute_s | 1800/43200 |
| reauth.valid_s/credentials.reveal_s | 600/30; dicabut saat role/session berubah |
| service.password_chars/backup.password_chars/radius.secret_chars | 16/32/32; CSPRNG terverifikasi |
| radius.interim_s/stale_grace_s/simultaneous_default | 300/60/1; stale setelah >3×interim+grace |
| radius.acct/usage/radpostauth_days | 90/400/30 |
| radius.auth_timeout_s/canary_s/full_observation_s | 3/1800/86400; waktu nyata |
| radius.dynamic_authorization_port | 3799 dikonfigurasi eksplisit; bukan asumsi default perangkat |
| migration.harvest_ttl_s/rate_per_min/batch_size | 86400 maksimum / 60 / 100 |
| acs.inform_s/task_ttl_s | 900/86400 |
| mon.wan_fail_down/success_up/poll_fail_threshold | 3/5/3 |
| billing.first_period_policy/reminder_offsets_days | full / [-3,0,3] |
| collector.settlement_alert_days | 3 |
| asset.capitalization_idr/useful_life_years/residual_idr | 2500000.00/4/0.00; konfigurasi kategori; review akuntan |
| ledger.retention_years | 10 tahun kalender minimum sejak akhir tahun buku; tidak boleh dikurangi; formula/hold/purge menurut MAC-03 |
| i18n.default/enabled | id / [id,en]; xx-pseudo hanya untuk pengujian |

Tambahan wajib untuk profil eksekusi: pagination 50/maksimum 200; import chunk 100 baris; batas bulk 1000 service per request; clock skew maksimum 5 detik; polling kesiapan 5 detik/deadline 120 detik; polling job 2 detik lalu 5 detik; image/dependency wajib versi exact+digest; task tanpa deadline kind tidak runnable. Parameter tambahan ini AUDIT_DEFAULT dan tidak mengubah SLA.

Nilai timeout harus memenuhi `connect ≤ read ≤ deadline`; lease mempunyai heartbeat < lease/2; kapasitas/concurrency/resource aktual harus tersedia dalam File 2. Nilai tak dikenal di luar registry ditolak, bukan diabaikan. Nilai efektif disnapshot per run; perubahan default tidak mengubah invoice/plan/period yang sudah diterbitkan.

## 5. Kuota, tanggal, subscription, dan penghentian

[REVISI AUD-10] Kuota layanan dihitung sebagai himpunan identitas, bukan penjumlahan service dan reservasi yang mewakili identitas sama. `used = committed_counted_accounts + reserved_unmaterialized_units`. Reservasi yang sudah menjadi akun dikonsumsi dalam transaksi yang sama; item pending yang sudah memiliki akun tidak dihitung lagi. Kunci entitlement tenant menserialisasi reserve/consume/release/expiry dan pergantian paket. Proyeksi usage harus direkonsiliasi dengan sumber identitas.

Draft manual tidak mengurangi kuota; cap `min(500,max(10,ceil(0.25×limit_services)))`. Satu akun gabungan lintas router tetap satu kuota. Layanan offline/suspended/imported/disabled tetap dihitung sampai terminated/archived. Voucher issued dan belum habis/expired/revoked dihitung sekali sebagai access account, bukan ditambah lagi sebagai voucher. Reservasi active tanpa kemajuan kedaluwarsa; pending dengan hasil tidak pasti tetap menahan kapasitas sampai rekonsiliasi.

Penggantian router: maksimum satu replacement aktif per router asal, satu router baru tidak boleh menggantikan dua asal. Slot gabungan berlaku 30 hari sejak replacement dibuat. Pada batas waktu, tandai `replacement_overdue`, hitung kedua router bila keduanya masih terdaftar, blokir penambahan jika over quota; jangan memutus pelanggan atau menghapus router otomatis. Pelepasan baru efektif setelah pengendali berhenti menjadwalkan write dan NAS/peer ditangani sesuai scope; arsip database saja tidak mencabut akses RADIUS.

[REVISI AUD-11] Hari/tanggal bisnis menggunakan timezone tenant yang disnapshot; event UTC RFC3339. Periode `[start_date,end_date)`; anniversary menyimpan bulan asal dan anchor A, kemudian clamp tiap boundary dari bulan asal, bukan dari hasil clamp sebelumnya. Tahunan menambah 12 bulan kalender. Renewal aktif mulai dari end_date; renewal setelah expired mulai dari tanggal approval dan memperoleh anchor baru. Free tidak expired.

Upgrade SaaS: pada tanggal lokal approval D, `bonus_days=max(0,old_end_date-D)` hari kalender; paid term baru dimulai D. Paid term dasar berakhir clamp bulan ke-1/12, lalu ditambah bonus. Simpan `anchor_date`, `period_index`, dan `bonus_offset_days` terpisah. Boundary sesudah term pertama dihitung dari anchor + jumlah bulan kumulatif + bonus_offset, bukan dari tanggal hasil yang dapat drift. Bonus hanya ditambahkan sekali, tidak diulang pada setiap renewal. Quote menyajikan tanggal aktual; retry tidak menambah bonus kedua kali. Downgrade hanya pada renewal dan ditolak bila usage tujuan terlampaui.

SaaS expired: E adalah midnight lokal end_date. Grace `[E,E+7 hari)`; restricted `[E+7,E+30 hari)`; ended mulai `E+30 hari` (hari expired ke-31 bila E disebut hari ke-1). VPN/RADIUS dipertahankan sampai `ended_at+60 hari = E+90 hari`; notifikasi H-7/H-3/H-1 terhadap waktu itu. Retensi data biasa dihitung 180 hari sejak ended_at; dokumen keuangan/audit/legal hold mengikuti retensinya sendiri. Perbedaan penomoran “hari ke-91” adalah label kalender, bukan tambahan satu hari durasi.

Tunggakan SaaS tidak menjadwalkan isolir internet. Restricted tetap mengizinkan operasi existing, pembayaran, export, pemulihan, monitoring, backup dan RADIUS. Ended mengizinkan baca/bayar/export dan RADIUS existing; automation isolir dijeda. Penarikan RADIUS harus memenuhi offboarding, notifikasi yang benar-benar terkirim, coverage rollback, dan mandat yang berlaku. Bila salah satu tidak tersedia, tandai withdrawal_blocked dan laporkan; jangan mengganti kegagalan notifikasi dengan klaim telah diberitahukan.

## 6. Model identitas dan kontrak API

[REVISI AUD-12] UUID internal; FK komposit `(tenant_id,id)` untuk seluruh relasi tenant, termasuk access/source, pool binding, device, invoice/allocation, job, backup dan ledger. Kunci stabil router memakai UUID/code + jenis + fingerprint/revision; `.id` hanya handle sesi perangkat. `Service.preferred_router_id` nullable menggantikan indeks contoh yang menyebut kolom router_id yang tidak ada. Pembatasan router menggunakan relasi tenant-scoped; daftar kosong berarti tidak ada router diizinkan, null berarti semua router tenant yang memenuhi binding/capability.

Username dibandingkan exact/case-sensitive; maksimum 64 byte UTF-8 dan 64 karakter; tanpa kontrol atau spasi tepi; jangan lowercase/trim diam-diam. Unicode diterima hanya bila adapter teruji mampu round-trip exact; selain itu invalid dengan alasan, bukan diubah. `kind=pppoe|hotspot` diperiksa pada auth; satu namespace username per tenant tetap berlaku lintas kind. `credential_state=unknown|ready|rotation_pending` terpisah dari state akun `active|suspended|disabled|expired`. Akun unknown tidak menerbitkan material autentikasi aktif.

[REVISI AUD-13] API prefix `/api/v1`; tenant path/header adalah permintaan scope yang harus diverifikasi membership. Resource tenant lain selalu 404 generik; aktor yang melihat resource tetapi tidak berizin aksi menerima 403. Pencarian/cursor/filter/cache/realtime selalu scoped tenant dan locale yang relevan. Limit >200, nol, negatif, cursor rusak, atau filter tak dikenal →422; tidak ada pilihan “ditolak atau di-clamp”.

Error shape tetap `{code,message,request_id,field_errors,retryable,locale}`. Field_errors berisi daftar `{code,message}` per field. HTTP deterministik:

| Code | HTTP atau tempat pemakaian |
|---|---|
| validation_error | 422 |
| unauthorized | 401 |
| forbidden | 403 |
| not_found | 404 |
| quota_exceeded, revision_conflict, idempotency_conflict, conflict | 409 |
| rate_limited | 429 dengan Retry-After integer detik |
| router_unreachable, dependency_unavailable | 503 pada pemeriksaan sinkron; pada job tersimpan di safe_error |
| unsupported_capability | 409 untuk aksi pada konfigurasi yang belum didukung |
| verification_failed | hasil job; request sinkron yang memang memverifikasi memakai 409 |

Endpoint TD §5 dipertahankan. Lengkapi kontrak yang hilang: `POST /enroll/validate` (200, validasi token tanpa konsumsi); `POST /enroll/complete` (200, atomik consume+credential/peer registry+outbox); `POST /imports/{id}/commit` (202, preview_revision); `GET /jobs/{id}` (200, permission resource); `GET /health/live` dan `/health/ready` hanya status minimal tanpa secrets; CRUD paket/binding berada pada resource tenant-scoped yang dispesifikasikan di OpenAPI sebelum UI memakai. Endpoint platform dan tenant tidak berbagi permission verifikasi pembayaran.

202 berarti antrean, disertai job_id/parent_job_id dan URL status; keberhasilan akhir hanya dari status+bukti. 201 access account adalah keberhasilan record DB/proyeksi, tidak menyatakan sesi pelanggan terbentuk. Body mengandung expected_revision pada update; field yang boleh berubah adalah allowlist, tidak ada raw RouterOS/SQL/Mongo/ACS JavaScript/URL arbitrary.

Idempotency wajib untuk uang, akun/provisioning, cutover, activation, voucher, import commit, backup request, dan tugas ACS. Scope `(principal,tenant_or_platform,operation,key)` dengan hash canonical body, path resource, serta file hash bila multipart; secret body di-HMAC untuk pembandingan dan tidak disimpan plaintext pada response cache. Retry key sama+body sama mengembalikan logical action yang sama; key sama+beda →409. Reveal/onetime credential response tidak boleh tersimpan dalam cache idempotency umum. Business event keys tetap unik setelah tujuh hari.

## 7. Job, lease, status, dan dependency

[REVISI AUD-14] Domain change, audit yang telah diredaksi, dan outbox ditulis satu transaksi; job.event_id unik; on_commit hanya wake-up. Claim memakai transaksi pendek SKIP LOCKED. Transaksi tidak ditahan selama I/O router. Mutasi finansial tidak menunggu collector/backup. Job memiliki actor, permission snapshot untuk audit, expected_revision, config_version, deadline, dedup key, attempt dan lease_epoch; permission terkini diperiksa lagi sebelum efek.

| State asal | State berikut yang sah |
|---|---|
| queued | claimed, cancelled |
| claimed | preflight, retry_wait, failed, cancelled |
| preflight | executing, waiting_dependency, retry_wait, failed, cancelled |
| executing | verifying, uncertain, failed, recovery_required, cancelled hanya menurut EXE-01 |
| verifying | succeeded, uncertain, failed, recovery_required |
| waiting_dependency/retry_wait | queued, cancelled, failed |
| uncertain | verifying setelah readback, retry_wait hanya bila terbukti tidak diterapkan, recovery_required, failed |
| recovery_required | verifying setelah recovery terotorisasi, failed |
| succeeded/failed/cancelled | terminal; permintaan baru memakai job baru yang menautkan asal |

Lease habis saat executing/verifying → uncertain, bukan langsung queued. Dispatcher memeriksa epoch sebelum setiap kirim; RouterOS tidak memahami fence tersebut. Pemilik baru hanya menulis setelah proses/koneksi lama dipastikan tidak dapat mengirim lagi dan resource direkonsiliasi. Perintah yang telah terkirim tidak dapat ditarik kembali oleh lock DB. RADIUS write berarti update proyeksi DB + job Disconnect; bukan membuat user lokal pada router.

Retry total maksimum lima hanya untuk kegagalan terbukti sebelum efek; exponential full jitter cap 300 detik. Policy/hold/permission berubah sebelum efek →cancelled dengan alasan dan bukti EXE-01; bila efek mungkin terjadi, gunakan uncertain dan rekonsiliasi. Timeout sesudah efek mungkin terkirim →uncertain dan readback. `partial` ringkasan parent: jumlah succeeded/failed/blocked/pending; bukan state job anak. Parent tidak selesai sebelum seluruh anak terminal atau secara eksplisit ditahan dengan blocker. `stale` adalah kualitas observasi.

Kind dasar TD tetap; tambahan enrollment reconciliation, NAS client reload, import commit, router release/replace dan ChangePlan harus mempunyai kontrak kind sebelum executable. Konflik jenis/deadline yang belum terdaftar menahan kind terkait, tidak memblokir semua modul.

## 8. Batas keamanan dan rahasia

[REVISI AUD-15] Runtime aplikasi, FreeRADIUS, collector, dispatcher, receiver, VPN manager, janitor, migrator, dan ledger memiliki principal/role berbeda. Runtime bukan superuser, owner tabel, atau BYPASSRLS; tidak boleh TRUNCATE, ALTER, mengubah policy, atau menjadi owner melalui role inheritance. ENABLE+FORCE RLS berlaku pada tabel tenant. `set_config` selalu transaction-local setelah membership terverifikasi; konteks kosong gagal tertutup; uji connection-pool reuse wajib. RLS tidak mengamankan backend yang sudah sepenuhnya kompromi.

SupportGrant memerlukan Owner, scope, actor, alasan, expiry dan audit; tidak membuka password, kunci, atau raw backup. Super Admin tidak mempunyai permission tenant otomatis. MFA platform wajib; MFA+reauth pada aksi sensitif berlaku untuk semua aktor yang didelegasikan aksi itu, bukan hanya Owner. Login rate limit per akun dan per IP mencegah serangan menyebar dan penguncian satu akun oleh IP berbeda.

Rahasia boleh berada dalam kanal terautentikasi dan penyimpanan yang memang diperlukan, termasuk secret proyeksi RADIUS terkontrol. Larangan “tidak di browser” berarti tidak pada tabel, URL, history, analytics, persistent cache, atau log; reveal berizin di memori halaman sementara adalah pengecualian eksplisit. Token email verifikasi/reset adalah pengecualian URL terbatas: acak, singkat, sekali pakai, log redacted, no-referrer; token router tidak memakai URL.

Connector hanya target registry terotorisasi; IP hasil DNS harus cocok allowlist, termasuk IPv6. Redirect dan DNS rebinding ditolak; bukan larangan semua private IP karena lab/manajemen memang private. CWMP connection request dan URL firmware/diagnostics juga melalui kebijakan egress; URL dari CPE adalah input tidak tepercaya. Render PDF tidak mengakses URL arbitrary/file lokal; gunakan aset terdaftar.

Upload menggunakan MIME/magic bytes, ukuran, parser bounded, ClamAV nyata dan definisi yang sehat untuk gate; scanner unavailable/quarantine →tidak dapat dilihat atau disetujui. Stub hanya dev dan selalu dilabeli simulated; hasilnya tidak memenuhi G2. Signed download melewati gateway autentikasi yang memeriksa tenant/permission saat penukaran, TTL 300 detik, bukan bearer object-store URL yang diklaim dapat memeriksa sesi.

## 9. Enrollment, discovery, sumber password, dan penggabungan

[REVISI AUD-16] Bootstrap read_only tetap menulis objek manajemen minimum; istilah read_only mengacu kredensial operasi sesudah enrollment, bukan klaim tidak ada perubahan apa pun. Penambahan interface/peer/rute /32/cert/group/user/firewall sempit hanya bila tercakup preview dan ownership. Existing default route/bridge/DNS/DHCP/user dan FastTrack tidak diubah. `/ip service api-ssl` adalah objek global: jangan menimpa sertifikat/address existing; jika berbeda, tampilkan diff dan blokir sampai perubahan shared resource tercakup mandat. Namespace/comment saja tidak membuktikan ownership.

Skrip memvalidasi token dan TLS server sebelum langkah berhak tinggi. Fetch HTTPS wajib validasi sertifikat, waktu sehat dan hostname benar; jangan mengandalkan default Fetch. Private key WG dibuat pada router; password generator router harus dibuktikan kriptografis, jika tidak gunakan injeksi CSPRNG melalui kanal rahasia terotorisasi. Kredensial tidak menjadi literal artefak skrip.

Complete enrollment consume token dan menyimpan registrasi atomik; provisioning peer eksternal melalui outbox sehingga kegagalan dapat direkonsiliasi. Replay complete dengan nonce/router key sama mengembalikan enrollment yang sama tanpa mengirim ulang secrets; identity berbeda →409. Pengulangan skrip pada router yang sama membaca ownership yang sudah ada, tidak membuat user/peer kedua dan tidak membutuhkan token lama untuk mendaftarkan identitas baru. Revoke token/peer/API/NAS adalah empat state terpisah.

[REVISI AUD-17] Discovery/adopsi database-only mengecualikan provisioning akun panen S1: pembuatan/penghapusan akun migrasi adalah operasi privileged terpisah dengan scope sendiri. Default S2 CSV, S3 password baru, atau S4 ekspor RADIUS tidak menulis router. S3/rename tidak dianggap kompatibel dengan CPE existing sebelum perubahan CPE selesai. Akun non-PPPoE tetap unmanaged; service=any perlu keputusan per objek; akun admin tidak pernah diadopsi sebagai pelanggan.

S1 maksimal 24 jam; scheduler harus memakai waktu kedaluwarsa absolut dan startup cleanup sebagai cadangan. Jadwal startup saja tidak memenuhi TTL. Sebelum panen, buktikan cleanup aktif, waktu benar, dan permission minimum dari lab; bila cleanup tidak dapat dijamin, jangan membuat akun. Setelah panen hapus dan readback; kegagalan penghapusan menjadi blocker keamanan, tidak cukup menunggu timer.

[REVISI AUD-18] Wizard tetap delapan langkah. Pada langkah gabung sebelum password diperoleh, status hanya structural_candidate; jangan menyatakan “password sama”. Langkah sumber password memperkaya kandidat, lalu langkah tinjau mengulang klasifikasi dengan pembandingan rahasia in-memory/HMAC sementara. Merge memerlukan kind/identitas/paket/hold kompatibel dan keputusan tercatat. keep_one mengecualikan sumber lain dari adopsi, bukan menghapusnya. Rename hanya menciptakan desired identity DB dan rencana perubahan kredensial/CPE yang terpisah; tidak mengklaim akun lokal telah diganti.

CSV satu mode per batch: create, enrich, update, device_mapping, password_migrasi. Tidak ada mode “update+create” implisit. Header UTF-8 baku, BOM boleh; duplikat header/kolom tak dikenal invalid; nomor baris fisik dan nomor record dicatat untuk quoted multiline. Batas rows menghitung record data, tidak header/blank line; chunk 100; semua baris satu identitas harus lolos uniqueness sebelum commit chunk. Kolom kosong mempertahankan nilai; clear-field memakai daftar field eksplisit yang diizinkan. Preview_revision mengikat file hash, mapping, akun, paket dan snapshot sumber. Baris gagal tidak mengubah jurnal/payment/isolir; retry committed row tidak menggandakan efek.

## 10. RADIUS: tenant, skema, atribut, dan lifecycle NAS

[REVISI AUD-19] Tenant berasal dari identitas transport klien NAS terdaftar dan secret yang diverifikasi, bukan User-Name, NAS-IP-Address di payload, atau Client-Shortname yang diterima dari pengguna. Secret unik per NAS; seluruh paket melalui tunnel. Unknown client atau Message-Authenticator invalid/absent pada Access-Request dibuang sesuai kebijakan; negative test lulus bila tidak ada Access-Accept dan tidak ada kebocoran, bukan wajib menerima Access-Reject.

`radius.nas` unik pada router dan source IP terdaftar. Satu username dapat mempunyai banyak check/reply attribute: hapus klaim UNIQUE(tenant_id,username) pada radcheck. Uniqueness proyeksi memakai tenant+account+attribute+scope+ordinal; atribut single-value memiliki tepat satu nilai efektif setelah resolver menerapkan override router > paket > tenant. Konflik pool/group/reply tidak diselesaikan oleh urutan UNION SQL.

[REVISI AUD-20] Snippet SQL/unlang lama adalah ilustrasi yang digantikan kontrak berikut, bukan kode siap salin. Role RADIUS hanya EXECUTE facade fungsi DB yang telah diaudit: lookup NAS minimum untuk bootstrap; authorize, accounting, postauth, dan session admission dalam transaksi masing-masing. Facade mengikat router terverifikasi ke tenant, memakai query parameter/escaping sesuai driver, mengaktifkan konteks RLS transaction-local, dan mengembalikan hasil terbatas. Tidak ada SET tenant lalu query berikut di pool tanpa transaksi yang sama. Owner facade tidak memiliki BYPASSRLS/ownership exemption; search_path hanya schema tepercaya dan pg_temp terakhir; revoke EXECUTE PUBLIC dan CREATE pada schema tepercaya. Kunci fungsi tidak boleh menerima tenant dari packet sebagai otoritas.

App service menulis access_account dan proyeksi melalui principal projection-writer dalam transaksi bisnis yang sama; bukan broad DML lintas tenant. radius_ro/radius_acct adalah nama peran fungsional; akses langsung lintas tenant ke tabel bukan solusi untuk RLS yang memblokir query. Secret plaintext pada radcheck/nas adalah pengecualian penyimpanan yang eksplisit: host/role terbatas, backup terenkripsi, no debug dump, tidak untuk UI/export umum. PAP dapat diverifikasi dengan skema tertentu; cleartext dipilih baseline untuk kompatibilitas CHAP dan MS-CHAPv2, bukan klaim semua protokol selalu membutuhkan bentuk sama.

| Kelompok | Kontrak |
|---|---|
| Control/check internal | Cleartext-Password, Auth-Type Reject, Simultaneous-Use, Expiration; Max-All-Session hanya bila modul akumulasi terbukti |
| Reply ke NAS | Mikrotik-Rate-Limit, Framed-Pool atau Framed-IP-Address, Acct-Interim-Interval, Session/Idle-Timeout; atribut vendor sesuai dictionary versi terpin |
| Resolver | enforce kind, state, valid_from/until, allowed routers, binding, static subnet, MAC, FUP dan hold sebelum Accept |
| Kecepatan | rx=upload dari pelanggan, tx=download ke pelanggan; integer bit/s dikonversi tanpa pembulatan float |
| Static IP | override router → static_ip bila subnet valid → pool hanya bila static_ip null; IP terkonfigurasi invalid ditolak, tidak diam-diam berubah ke pool |
| Kedaluwarsa | valid_until eksklusif pada midnight timezone bisnis; konversi UTC; Session-Timeout tidak melewati batas itu |

Max-All-Session, Expiration dan Simultaneous-Use bukan atribut reply universal. Batas byte/waktu kumulatif memerlukan modul counter/server policy serta accounting, bukan hanya baris radreply. Hotspot http-chap/PAP/MAC/cookie diuji sesuai kemampuan yang benar; jangan mewajibkan MS-CHAPv2 pada seluruh jenis login Hotspot.

[REVISI AUD-21] `read_clients` SQL tidak berarti registrasi NAS live otomatis. Enrollment/revoke/rotation membuat desired NAS revision, kemudian privileged reconciler menghasilkan konfigurasi tervalidasi dan rolling restart/reload yang memang didukung versi terpin. Tandai `nas_applied_revision` hanya setelah probe menerima/menolak sesuai target. Jangan mengklaim revoke selesai sebelum cache klien kedua instance dicabut. Dua proses pada satu VM hanya redundansi proses; tidak menjamin host, disk, DB, listrik atau tunnel tetap hidup. Host HA memerlukan failure domain independen dan bukti G4.

Default Dynamic Authorization adalah Disconnect-Request RFC5176 pada port 3799 yang dipasang eksplisit; jangan menyebut PoD sebagai protokol ekuivalen yang pasti didukung RouterOS. CoA hanya capability per fitur/build yang terbukti; jika tidak, perubahan berlaku pada sesi berikutnya atau Disconnect yang dampaknya sudah diotorisasi. Sumber IP dispatcher, shared secret dan identifier sesi harus cocok NAS target.

## 11. Cutover dan rollback B0–B6

[REVISI AUD-22] Pencocokan akun lokal dapat mengalahkan RADIUS. Mengaktifkan use-radius saja tidak membuktikan canary. PPP AAA umumnya scope global; jangan mengeklaim bisa diaktifkan per satu PPPoE server tanpa capability yang membuktikannya. B0 wajib menilai dampak ke semua protokol PPP pada router, bukan hanya akun terpilih.

| Tahap | Prasyarat, aksi, dan kriteria keluar |
|---|---|
| B0 preflight | mode manage, radius.cutover+MFA+reauth, izin valid selama langkah, versi/build teruji, backup valid, jalur recovery, baseline seluruh shared setting, coverage rollback dan snapshot revision cocok; RADIUS eksternal tanpa rencana coexistence →BLOCKED |
| B1 parity | per akun ready: auth sintetis memakai NAS test terdaftar dan konteks tenant/router yang sama melalui facade uji terotorisasi; uji credential/kind/pool/rate/state; nol kegagalan dan nol binding ambigu; tes ini bukan bukti login lewat NAS produksi |
| B2 install | pasang hanya klien platform, incoming port, dan rule sempit yang direncanakan; restore baseline shared resource harus tersimpan; endpoint primer/sekunder dan route /32 terjangkau; readback lulus |
| B3 canary | gunakan akun sintetis/canary yang tidak cocok akun lokal, atau metode penghilangan shadow yang sudah diuji dan diotorisasi per objek; PPP global side effect termasuk rencana; amati 1800 detik nyata; minimal 100 auth valid, keberhasilan ≥99%, nol salah Accept/atribut/tenant, Start/Interim/Stop benar, sesi kontrol existing tetap sesuai baseline |
| B4 shadow_active | enable scope penuh yang direncanakan dan observasi 86400 detik nyata; job memakai deadline kind dan grant/window yang cukup; belum selesai observasi →pending/BLOCKED, bukan dipercepat untuk gate runtime |
| B5 authoritative | batch≤100; setiap source mendapat ownership consent, fingerprint/revision cocok, tidak ada local shadow yang tersisa; uji login nyata membuktikan RADIUS; hanya lalu router ditandai authoritative |
| B6 rollback | cabang dari tahap yang telah mengubah router; restore snapshot nilai sebelum operasi, bukan hardcode use-radius=no; pulihkan hanya objek/run yang masih cocok revision; probe login+accounting, pertahankan data DB dan audit |

B5 memilih metode berdasarkan matriks lab exact: disable bila terbukti menghilangkan shadow; jika tidak, archive_rename bila terbukti menjaga sesi dan rollback; delete hanya jika secara eksplisit diotorisasi, backup memuat semua material pemulihan dan restore sudah diuji. Jika tidak ada metode sah, B5 BLOCKED; jangan menghapus otomatis karena disable gagal. Akun sumber existing tidak wajib punya prefix rtrw, tetapi harus memiliki consent ownership per-object dalam CutoverRun.

[REVISI AUD-23] Rollback tidak boleh mengaktifkan semua user yang sebelumnya disabled, menghapus RADIUS pihak lain, mengubah global AAA seenaknya, atau menghidupkan akun yang sekarang ditahan security/manual. Backup awal hanya mencakup akun saat itu; akun baru, rename dan password yang berubah sesudah cutover memerlukan recovery export terkini. Jika coverage ini tidak lengkap, rollback lama tidak dinyatakan aman. Buat delta recovery yang diotorisasi atau tandai recovery_required. Rollback tidak menggunakan reset/reboot/restore binary rutin.

`enforcement_mode=local|radius_shadow|radius_authoritative|degraded` adalah status router, bukan status bisnis akun. Login/pindah router hanya dinyatakan terjamin dalam batas lab yang terbukti, binding lengkap dan tidak ada jalur autentikasi alternatif yang melewati policy. Tidak ada janji nol downtime universal.

## 12. Isolir, aktivasi, hold, dan bukti arah

[REVISI AUD-24] Worker menilai ulang payment, seluruh overdue yang memengaruhi akses, policy_version, grace, exemption, termination, hold dan expected_revision setelah service lock. Grace berakhir pada midnight lokal setelah due_date+grace_days; scheduler 01:00 mengeksekusi kandidat yang sudah melewati batas. Simulasi policy mengikat policy/price/opening-balance revisions dan hash scope; belum 24 jam tetapi datanya berubah →simulasi stale, harus dihitung ulang.

Pembayaran tidak otomatis membuka layanan. Payment sebelum efek isolir membatalkan kandidat lama; setelah Reject terlanjur committed, pembayaran tetap sah dan layanan menunggu aktivasi manual. Jangan otomatis mengganti active untuk pembayaran yang baru diterima. Isolir Reject diperbarui atomik dengan keputusan DB; Disconnect terpisah lewat outbox. Suspend mencakup semua sesi target pada semua NAS terkait; multi-router/dual-stack/local shadow diuji.

Verifikasi suspend wajib menggabungkan: (1) policy/proyeksi revision Reject benar dan auth test valid secara transport memang Reject karena state target, bukan karena NAS/secret salah; (2) Disconnect ACK untuk setiap sesi yang diketahui atau bukti positif sesi sudah tidak ada; (3) Acct-Stop atau readback NAS minimum yang membuktikan sesi target tidak aktif; (4) recheck setelah 60 detik tanpa sesi baru. Absennya interim selama 60 detik tidak membuktikan putus karena interim default 300 detik. Jika tidak ada bukti positif sesi, status unknown/uncertain; jangan menunggu satu menit lalu menganggap PASS.

[REVISI AUD-25] Restore memakai assertion berbeda: akun active, hold tidak ada, atribut/binding terkini benar, auth test valid menghasilkan Accept. Perangkat mungkin belum login; connection_state tetap offline/unknown. `verified_active` berarti kelayakan autentikasi dipulihkan, bukan internet sudah online. Label UI: “Akses dipulihkan dan autentikasi diizinkan; perangkat mungkin belum tersambung.” `verified_suspended` hanya setelah seluruh bukti suspend lengkap. Jangan menjalankan test Reject yang sama untuk restore.

Simpan alasan isolir dan atribut milik aplikasi sebelumnya, tetapi jangan mengembalikan snapshot rate lama bila paket sudah berubah; resolver memakai desired revision terkini. Hold override perlu permission+MFA+reauth+alasan, ditautkan ke hold tertentu, tidak memalsukan pelunasan.

## 13. Accounting RADIUS, batas sesi, FUP, dan edge

[REVISI AUD-26] Session identity memuat tenant+router+NAS boot/session identity, bukan username atau Acct-Session-Id global. Sediakan session directory unik lintas partisi; partisi radacct ditentukan awal sesi, sehingga Interim/Stop bulan berikutnya memperbarui sesi sama. Dedup retransmission; paket out-of-order tidak menurunkan counter atau membuka sesi yang telah ditutup. Gabungkan octet/gigaword dan reset/wrap secara eksplisit. Usage harian memakai delta nonnegatif dan alokasi interval lintas midnight sesuai timezone snapshot; late correction mempunyai version, bukan menjumlah ulang total counter kumulatif.

Fresh session: update ≤3×interim+grace. Data basi membuat `connection_state=unknown`; janitor boleh menandai stale secara administratif, tetapi tidak menciptakan Acct-Stop seolah-olah dikirim NAS dan tidak menganggap sesi pasti mati. Kolektor health router dan jalur accounting adalah dependency berbeda. Retensi tidak menghapus state sesi aktif; arsip/summarize sesi lama memakai directory tetap.

[REVISI AUD-27] COUNT(radacct) saja tidak menjamin Simultaneous-Use saat dua login paralel. Baseline strict mode memerlukan admission lock per tenant+account, reservasi autentikasi idempoten per request, pending slot, accounting confirmation, dan rekonsiliasi positif sebelum melepaskan slot yang mungkin sudah menjadi sesi. Tes dua NAS dengan request serentak wajib membuktikan satu Accept untuk limit1. Accounting hilang →unknown/hold admission, bukan slot bebas otomatis. Jika adaptor tidak membuktikan kontrol ini, klaim batas sesi strict dan fitur terkait belum release_enabled; jangan menutupi keterbatasannya dengan PASS satu login berurutan.

FUP dan cumulative voucher quota bukan jaminan nol overshoot pada interval accounting 300 detik. Simpan data limit, counter version, accounting lag, aksi, dan batas overshoot terukur per model; tidak menjadikannya tagihan uang tanpa paket meter/bukti terpisah. Expired/revoked tidak hanya menolak login baru: Disconnect sesi yang masih aktif bila policy/dampak sudah diotorisasi.

[REVISI AUD-28] Edge replica adalah host Linux/OS yang mendukung FreeRADIUS, bukan instalasi FreeRADIUS langsung di CHR. Default off sampai G4. Snapshot ditandatangani, terenkripsi, tenant-scoped, monotonic revision, expiry 900 detik AUDIT_DEFAULT; replay/rollback revision ditolak. Setelah snapshot expired, login baru ditolak, sesi existing tidak diputus semata karena expiry. Accounting store-and-forward memiliki limit disk, dedup event dan alarm.

Saat terpartisi, edge tidak dapat menjanjikan limit sesi global strict atau mengetahui suspend baru pusat. Baseline memilih fail closed untuk login yang memerlukan koordinasi global; opsi availability-first harus ADR/otorisasi terpisah dan menampilkan keterbatasan, tidak dianggap strict. Dua alamat pada NAS harus mempunyai source-IP/secret/client revision serta route /32 yang nyata; menambahkan alamat sekunder tanpa jalur/kunci tidak memberi redundancy.

## 14. Billing internet, pembayaran, dan koreksi

[REVISI AUD-29] Invoice/payment/submission/allocation adalah entitas berbeda. Unik invoice `(tenant,service,period_start,period_end,kind)`; harga, pajak, bahasa, timezone dan policy disnapshot. Due date tidak mengubah service period. Fixed_monthly selalu `[awal bulan,awal bulan berikut)`; anniversary mengikuti anchor §5.

Periode pertama fixed_monthly yang dimulai tengah bulan berakhir awal bulan berikut. `full` menagih harga penuh untuk potongan periode pertama itu; `prorata_daily` menagih harga×hari aktif/hari kalender bulan, ceil ke Rp100 sebagai kebijakan tenant tersnapshot; `free_until_next_period` bernilai nol sampai batas bulan berikut. Pada anniversary, full memberikan satu term penuh dari aktivasi; dua policy lain ditolak sampai ada batas kalender pertama eksplisit dalam package. Tidak ada policy yang diam-diam mengubah fixed_monthly menjadi anniversary.

Prepaid issue pada start-7 hari atau segera saat service baru dibuat bila tanggal itu sudah berlalu; due default start_date, tidak sebelum issue_date. Postpaid issue pada end_date eksklusif pukul00 lokal, due issue+7 hari. Jika due_day eksplisit pada fixed_monthly, pilih tanggal clamp pertama pada/selepas due default; field ini tidak berlaku untuk anniversary. Semua tanggal perhitungan dicantumkan saat preview.

[REVISI AUD-30] Serialisasikan submission+invoice+allocation+entitlement dalam urutan lock konsisten. Unik verified external payment reference per rekening+provider+source identity; dua approver untuk submission/transfer sama menghasilkan satu Payment. Dua transfer nyata ke invoice sama tetap dua Payment, dengan sisa menjadi credit; jangan membuang dana kedua demi assertion “satu invoice satu payment”. Nominal allocation≤payment_unallocated dan≤invoice_outstanding saat lock. Payment total dapat melebihi outstanding; hanya selisih masuk 2-1400, bukan seluruh pembayaran ditambah posting pembayaran normal.

Invoice SaaS partial tidak mengaktifkan entitlement; paid invoice menimbulkan satu entitlement event. Invoice expired memerlukan koreksi/reissue yang menautkan asal atau credit, tidak diubah paid tanpa audit. Bukti upload hanya submission. Kolektor receipt bernomor membuat pembayaran terhadap clearing 1-1150 sejak penerimaan yang sah; setoran bukan pengakuan pendapatan kedua. Kekurangan setoran diverifikasi sebagai selisih/piutang kolektor sesuai kebijakan, bukan dianggap lunas otomatis.

## 15. Ledger, pengakuan, dan akuntansi

[REVISI AUD-31] Baseline COA dan laporan panduan tetap; buku tenant dan platform mempunyai book_id eksplisit, FK dan scope terpisah. `scope=platform` bukan cara melewati RLS tenant dengan tenant_id null. Source event+posting_kind+book unik; event sama dengan payload hash berbeda →conflict. Setiap journal minimal dua line, nilai decimal≥0, tepat satu sisi per line positif, total debit=kredit, satu book/currency/period.

Tiga lapis ledger tetap wajib: runtime tanpa direct DML/TRUNCATE/DDL; posting facade SECURITY DEFINER yang memvalidasi scope dan mengunci fiscal period; constraint dan immutability DB. Tambahkan kontrol yang hilang dari snippet lama: entry posted tanpa line ditolak; INSERT line ke entry posted ditolak; pemindahan line ke entry lain, DELETE line terakhir, perubahan status posted dan update header ke buku lain ditolak. Constraint dicek saat transaksi commit pada header dan line, bukan hanya AFTER INSERT/UPDATE line. Draft editable hanya lewat prosedur berizin; posted immutable. SECURITY DEFINER tidak boleh mengandalkan schema yang dapat ditulis runtime.

Closing memakai FOR UPDATE pada baris period yang posting kunci FOR SHARE; kedua proses lock buku/sequence konsisten. `effective_service_date` berbeda dari `posting_date`; period closed menolak posting mundur. Koreksi periode lama diposting pada periode terbuka dengan referensi tanggal sumber, bukan mengaku effective_date lama berarti boleh masuk period closed. Reopen tahun merupakan prosedur terpisah dengan dua approver berbeda; satu orang berperan ganda tidak memenuhi dua persetujuan.

[REVISI AUD-32] Prabayar belum dibayar adalah memorandum, tidak menghasilkan piutang ledger. Aging memisahkan tagihan prepaid memorandum dari piutang recognized; rekonsiliasi control account 1-1400 hanya memakai recognized receivables, termasuk opening balance approved, bukan semua invoice outstanding. Pembayaran prepaid bagian teralokasi →D kas/bank/clearing; K2-1300. Pembayaran postpaid →K1-1400; overpayment →K2-1400. Kredit dipakai prepaid →D2-1400 K2-1300, postpaid →D2-1400 K1-1400. Deposit refundable tidak diakui pendapatan.

Pengakuan berbasis layanan yang benar-benar diberikan dan nilai kontrak bersih yang dibiayai. Untuk V dan H hari, setiap bulan round_half_up(V×hari_layanan_bulan/H,2); bulan terakhir memperoleh V-total sebelumnya sehingga total tepat V, bukan sekadar≤V. Contoh nonkabisat 2026, 300000.00 untuk 1Jan–1Apr: 103333.33, 93333.33, 103333.34. Belum diterima dana prepaid →tidak mengakui liability/pendapatan fiktif; jika layanan tetap diberikan secara kredit, ubah kontrak menjadi postpaid/recognized receivable melalui kebijakan eksplisit, bukan di latar belakang.

Pembayaran terlambat untuk layanan yang sudah diberikan membentuk jadwal catch-up terkontrol di periode terbuka; tidak menggandakan recognition lama. Partial funded amount mempunyai jadwal alokasi proporsional tersnapshot, recognition tidak melebihi liability yang tersedia. Pajak dipisahkan dari basis revenue; pajak diterima tidak seluruhnya masuk 2-1300. Refund unearned →debit liability; earned →retur/adjustment, pajak mengikuti TaxRule; jangan mendebit liability yang sudah habis. Batas refund “hanya kesalahan/ganda” berlaku SaaS; refund internet karena terminasi/kontrak mengikuti kebijakan tenant yang disahkan.

Voucher: pilih kebijakan unredeemed liability sampai redemption/expiry yang sah; jangan mengaku seluruh multi-day voucher sebagai revenue saat pemakaian pertama bila masih ada kewajiban layanan. Bila recognize_on_sale dipilih, flag review akuntan wajib sebelum produksi. Agen dipilih reseller principal atau sales-agent; jangan memakai harga agen net sekaligus menambah komisi yang sama dua kali. Commission event unik dan payable sampai dibayar. Pembayaran setelah write-off memakai recovery rule yang tepat; mengkredit cadangan tanpa rekonstruksi piutang bukan default. Akun pemulihan khusus dipetakan sebelum fitur aktif.

Kerangka SAK EMKM/EP, pajak, kapitalisasi, penyusutan, FIFO/rata-rata, komisi dan posting rules tetap memerlukan review akuntan sebelum pembukuan produksi. Audit ini menetapkan konsistensi sistem; tidak mengarang sign-off profesional.

## 16. Backup, monitoring, dan pemulihan

[REVISI AUD-33] Generation routine/manual/prechange mempunyai batas terpisah 100/10/10. Retensi berarti anggota katalog retained, bukan jumlah blob fisik saat prune tertunda. File baru harus lengkap, size valid, sumber transfer selesai, terenkripsi dan durable sebelum commit katalog; hash server saja tidak membuktikan file sumber tidak terpotong. Cocokkan metadata ukuran/readback sumber dan sinyal protokol close yang terautentikasi. Bila checksum sumber didukung, bandingkan; jika tidak, nyatakan batas verifikasi dan buktikan restore sampel.

Staging reserve menghitung seluruh artifact wajib dan transfer bersamaan; headroom≥max(5GiB,2×artifact_terbesar×transfer_parallel). Periksa watermark dan free headroom keduanya; 90% stop backup baru. Gagal/partial tidak mengurangi backup valid. Prune crash idempoten; cleanup router menggunakan ID/nama file exact milik generation, bukan regex longgar yang bisa menghapus file lain. Password binary per router terkelola dengan key version, rotasi tidak membatalkan akses backup generasi lama.

SFTP push melalui VPN tetap baseline; configure src-path dan dst-path tanpa secret di URL. Jika versi RouterOS mendukung known-host validation, wajib enable dan pin melalui kanal tepercaya; opsi ignore dilarang. Versi yang belum mendukung dapat menggunakan kontrol kompensasi WireGuard+/32 sesuai baseline hanya setelah risiko dan bukti TK-505 tercatat; jangan menyebutnya verifikasi SSH host-key. Pull fallback memerlukan SSH/SFTP permission dan host pin sendiri, bukan dianggap sudah tersedia dari enrollment API-only.

[REVISI AUD-34] Metrics mempunyai observed_at/collected_at/source/unit/quality. Stale health/detail setelah >3×interval; accounting memakai aturan §13 tersendiri. Collector outage tidak berarti router down. Prometheus raw retention satu durasi tidak otomatis menghasilkan tier 15/90/400 hari. Baseline tier: raw Prometheus 15 hari; agregat 5 menit dan1jam dipersistenkan oleh job idempoten ke tabel aggregate PostgreSQL dengan retention90/400 hari. Recording rule saja pada TSDB15 hari tidak memenuhi retensi90/400. Tidak ada username/telepon/invoice label pada Prometheus.

Probe WAN minimal dua target independen per ISP pada route yang dipaksa. Down setelah tiga siklus gagal seluruh target, up setelah lima siklus sukses minimal satu target; hasil tiap target tetap tersimpan. Rate traffic menggunakan monotonic counters+elapsed time, reset/wrap bukan nilai negatif. Jangan menjumlah WAN+LAN sebagai trafik total dua kali.

[REVISI AUD-35] RTO diukur sejak gangguan layanan yang diinjeksi/deteksi dimulai sampai seluruh layanan inti target dan rekonsiliasi pulih; tidak mulai saat operator baru menekan restore. Catat detection, decision, provisioning, restore, radius_ready dan full_ready terpisah. RPO dihitung dari transaksi yang sudah di-ack sebelum outage versus transaksi terakhir yang pulih, memakai event sequence+timestamp; WAL timestamp saja tidak cukup membuktikan saldo.

Restore order: key/recovery capability dan konfigurasi aman →DB+radius pada jaringan tertutup →gateway+FreeRADIUS dengan state tervalidasi →API dan rekonsiliasi payment/policy/session →worker mutasi →artifact/ACS/modul sesuai dependency. Data/kunci/konfigurasi saling harus konsisten. RADIUS boleh dipulihkan lebih awal hanya setelah state akun dan keys valid; jangan melayani auth dari state yang belum diperiksa. RTO untuk R1 tidak menunggu ACS yang belum dirilis, tetapi harus mencantumkan scope. RPO≤15menit dan RTO≤4jam tetap target, bukan hasil.

Setelah restore, pembayaran/aksi yang terjadi sesudah backup harus direkonsiliasi dari sumber eksternal/jejak durable sebelum isolir berjalan. Target RPO15menit dapat berarti ada transaksi perlu direkonstruksi; jangan bersamaan menjanjikan nol lost transaction tanpa bukti durability tambahan. Runbook krusial backup/restore/rollback harus dipraktikkan untuk gate; tabletop cukup untuk review prosedur, tidak membuktikan RTO/restore.

## 17. ACS/CPE dan rotasi kredensial

[REVISI AUD-36] Default publik ACS menggunakan hostname HTTPS terpisah pada443; port7547 adalah CWMP internal/contoh port bila manifest secara eksplisit membukanya. NBI7557/FS7567/UI3000/Mongo27017 tetap internal. File download CPE melalui endpoint gateway bertoken, path/hash/model allowlist; FS internal tidak otomatis dapat dijangkau CPE. NBI tidak diasumsikan mempunyai autentikasi bawaan; wajib private bind/firewall dan service-auth proxy/mTLS bila lintas proses/host. Caddy HTTP reverse proxy tidak memerlukan plugin stream untuk CWMP HTTP; fitur non-HTTP memerlukan desain tersendiri.

DeviceID serial+OUI+product_class adalah identifier, bukan bukti kepemilikan. Claim memakai secret sekali pakai yang benar-benar dipasang pada kredensial CWMP sebelum Inform; secret di QR yang tidak pernah dikirim/periksa tidak memberi jaminan. Factory credential bersama tidak boleh meluluskan claim; gunakan provisioning lokal atau isolated bootstrap enrollment yang sudah diotorisasi. Karantina berlaku setelah identitas transport diverifikasi, tanpa mengirim password PPPoE ke perangkat belum terikat tenant. Alias serial yang berpindah tenant mengikuti proses transfer ownership, bukan auto-claim.

TR-098 path harus penuh berawalan InternetGatewayDevice.; TR-181 berawalan Device. Indeks ditemukan, pemetaan menghubungkan WiFi.Radio/SSID/AccessPoint melalui reference, bukan menyamakan nomor instance. Password sering write-only/masked; GetParameterValues tidak dianggap dapat membaca password aktual. Capability/version per model harus menyatakan mekanisme verifikasi: RPC/status, parameter key/config revision, dan functional reconnect bila writable secret tidak readable.

[REVISI AUD-37] Rotasi password memakai dua profil. Profil default otomatis hanya jika ada jalur manajemen CPE independen dari PPPoE yang diubah: simpan pending+old version; Set CPE; verifikasi RPC/config revision; update RADIUS; uji PPP login baru via NAS; commit rotation; hapus old secret sesuai retensi aman. Jika update CPE mungkin sudah diterapkan tetapi response hilang, status uncertain, bukan “RADIUS lama pasti aman dan pelanggan tidak terputus”. Baca state/fungsional sebelum retry.

Jika ACS berbagi koneksi PPPoE yang akan putus, automated rotation BLOCKED kecuali recovery lokal atau mekanisme overlap dua credential yang telah diuji per PAP/CHAP/MS-CHAP dan diotorisasi tersedia. Tidak mengarang transaksi atomik ACS↔RADIUS. Kompensasi memulihkan sisi yang benar-benar berubah memakai old version dan readback; kegagalan recovery →recovery_required dengan pekerjaan independen tetap berjalan.

Status task perangkat ACS adalah queued/waiting_inform/running/verifying/succeeded/failed/expired/cancelled; hasil job pembungkus menggunakan AUD-14 termasuk uncertain/recovery_required, dipetakan eksplisit oleh EXE-02; NBI200 atau202 disimpan terpisah dari job API platform. Task disappeared bukan bukti sukses karena bisa dihapus/expired; gunakan outcome RPC/fault dan readback/fungsi yang relevan. ID hilang setelah timeout submit →uncertain, cari korelasi task sebelum kirim ulang. Reboot/download/reset tidak diulang buta. Connection Request di balik NAT mungkin dimungkinkan dengan mapping/UDP/STUN yang telah diuji; default tetap waiting_inform. Jangan mewajibkan STUN bila tidak tersedia. TTL24jam mencabut task tertunda yang dimiliki run sebelum expired dinyatakan selesai, agar tidak terlaksana belakangan tanpa izin.

## 18. UI, permission layar, dan i18n

[REVISI AUD-38] U01–U20 dan13 menu tetap. Pengelolaan Paket dan Profile ditetapkan eksplisit sebagai subroute U04 `/app/{tenant}/packages`, dengan tab Paket Komersial, Binding Router, dan Profile Teramati. R1 create/edit paket dan binding adalah DB; perubahan profil fisik router hanya R4 melalui ChangePlan. Navigasi U06 ganti/lepas router menuju enrollment/cutover, bukan wizard pemetaan ulang akun. U19 read memakai customers.read/routers.read sesuai area, bukan mewajibkan radius.cutover hanya untuk melihat akun; tiap tombol memakai permission aksinya.

Copy conflict409: “Data bentrok dengan kondisi terkini.” Aksi “Muat ulang dan tinjau”. verified_active mengikuti §12. Copy succeeded generik: “Pekerjaan selesai dan hasilnya telah diverifikasi sesuai jenis tindakan”; jangan selalu “pada router” untuk journal/import DB. Waiting_dependency menyebut dependency aktual, bukan selalu router. Keamanan/uang yang gagal tidak ditutupi toast.

Desain token, header admin navy, lima kelompok, tab cepat lima, empat dimensi status, mobile44px, kontras4.5:1/3:1, keyboard/fokus, chart+table, unknown/gap tetap dipertahankan. WCAG2.2AA sudah baseline normatif UI/UX, bukan usulan baru. Test browser: Chromium/Firefox/WebKit versi yang dipin Playwright, viewport360×800,768×1024,1280×800; ini AUDIT_DEFAULT dan bukan klaim telah diuji.

Bahasa id default, en wajib, pseudo-locale test-only. FormatJS dan gettext tidak memerlukan syntax pesan yang identik: semantic message_id, nama/tipe placeholder dan makna sama; formatter syntax masing-masing diverifikasi. Pilihan API Accept-Language mengikuti bobot q valid→bahasa pengguna→tenant→id; fallback parent seperti en-GB→en. Respons Content-Language/locale konsisten; cache memvariasikan locale+tenant. Dokumen issued menyimpan bahasa, timezone, template version, nilai snapshot dan artifact/hash final; bahasa saja tidak menjamin cetak ulang identik setelah template berubah. CSV machine import memakai ISO date, decimal titik, header baku; export display terlokalisasi harus dibedakan dari reimportable export.

Satu role belum release_enabled tetap dapat mengakses sandbox QA melalui flag lingkungan terotorisasi; gate tidak boleh melarang pengujian yang diperlukan untuk lulus gate itu sendiri. Menu harian produksi hanya fitur released; backend menegakkan flag/capability.

## 19. GNS3, jaringan lab, dan resource

[REVISI AUD-39] Jangan mengunci GNS3 API v2 tanpa inventaris. Pilih family v2/v3 dari endpoint versi yang diizinkan dan dokumentasi versi aktual; controller/compute compatibility diverifikasi; base URL disimpan lengkap dengan prefix sekali, bukan menambahkan /v2 pada URL yang sudah mempunyai /v3. MCP opsional, bukan dependency. Version discovery hanya host/port yang sudah diotorisasi; tidak memindai jaringan mencari server.

Lab0: Linux gateway WireGuard+FreeRADIUS+PostgreSQL lokal sebagai baseline produksi co-located, AUT mengakses lewat route/firewall eksplisit; CHR adalah NAS; Linux PPPoE client menggunakan pppd/plugin PPPoE pada segmen L2 pelanggan, bukan DHCP client; Hotspot client memakai segmen L2 terpisah dan browser uji. Klien pelanggan tidak dijadikan peer manajemen WG. Lab1 menambah dua NAS tenantA dan satu NAS tenantB; Lab2 cutover; Lab3 fault/load; Lab4 ACS per model dan WAN per topologi. Emulator CPE hanya bukti kontrak, bukan sertifikasi model fisik.

Contoh alokasi logis, belum merupakan alamat host pemilik: management10.255.0.0/24; AUT10.255.10.0/24; tunnel100.127.0.0/16; WAN192.0.2.0/24 dan198.51.100.0/24; pelangganA10.77.0.0/16 danB10.88.0.0/16. RFC5737 tidak dirutekan ke internet. Alamat100.127 adalah shared address space, bukan ruang bebas konflik; periksa CGNAT/VPN/router host dan pilih pool yang sah sebelum provision. Benturan→BLOCKED, tidak mengubah jaringan host untuk “membuatnya cocok”.

Contoh baseline satu gateway: server tunnel100.127.0.1, NAS .11/.12/.13. Primary RADIUS/receiver pada .1. Secondary hanya diisi jika tersedia. Jika alias .2 dan proses kedua berada pada gateway yang sama, peer allowed-address terdiri .1/32 dan.2/32, bind/firewall/route harus cocok, dan hasil hanya redundancy proses. HA lintas host memerlukan peer/route/tunnel ke gateway kedua yang tetap hidup saat gateway pertama mati; alamat sekunder melalui gateway pertama tidak memenuhi uji host failure.

Project baru menggunakan prefix `rtrw-lab-<run_id>` dan kepemilikan ID run. Management menuju controller bukan Cloud bridge ke LAN pelanggan. NAT internet untuk download/updates hanya melalui allowlist manifest; tidak pernah menjadi route transit pelanggan lewat VPN SaaS. Stop/restart/restore/hapus hanya resource owned, termasuk dua host bila terpisah; baseline host/controller bersama tidak di-restore otomatis.

Resource estimate lama bukan kuota. File2 wajib menyediakan budget vCPU/RAM/disk/parallel/rate/biaya/durasi. Preflight memeriksa available headroom≥alokasi+snapshot+evidence; kekurangan→BLOCKED. Threshold operasional abort memakai limit eksplisit manifest, clock skew>5detik, disk watermark, evidence sink failure dan akses yang dicabut. Kill-switch: stop harness dan pengiriman mutasi baru; amankan evidence; rollback resource owned sesuai rencana; tidak blind restore seluruh server. Cleanup memverifikasi diff ID objek sebelum/sesudah; kegagalan cleanup dicatat, tidak menghapus evidence dahulu.

## 20. Desain pengujian, standar, dan gerbang

[REVISI AUD-40] Penghitungan sumber: matriks lama memuat62 child ID setelah shorthand diurai; spesifikasi memuat35 blok id, bukan30. Ada27 ID matriks tanpa blok lengkap dan dua ID negatif T16 yang hanya disebut di narasi. Registry v2.1 menyatukan64 child ID dan20 QA-SEC case. Jumlah di laporan/matriks dihasilkan dari registry, bukan diketik sebagai58. Setiap case mempunyai ID tunggal, dependency, fixture seed/hash, setup, aksi, expected assertion, deadline, bukti dan cleanup. Semua eksekusi aplikasi tetap NOT_RUN.

Spec common mengikat semua row registry: data sintetis seed261029; clock terkontrol untuk unit tetapi waktu nyata untuk protokol/canary/soak; dua tenantA/B, NASA1/A2/B1, dua akun kontrol non-target; actor/permission sesuai operasi; snapshot state sebelum efek; status NOT_RUN sampai actual observation ada; PASS hanya semua assertion benar, bukti lengkap dan cleanup aman. Missing required field→BLOCKED sebelum aksi. Runtime runner/harness belum ada adalah blocker tersendiri, bukan hanya “akses belum tersedia”. Registry dan spesifikasi final disertakan pada quality/Test_Case_Specifications_v2_1.md.

[REVISI AUD-41] ASVS5.0 mapping yang benar: V1Encoding/Sanitization; V2Validation/Business Logic; V3Web Frontend; V4API/Web Service; V5File Handling; V6Authentication; V7Session; V8Authorization; V9Self-contained Tokens; V10OAuth/OIDC; V11Cryptography; V12Secure Communication; V13Configuration; V14Data Protection; V15Secure Coding/Architecture; V16Security Logging/Error Handling; V17WebRTC. OAuth/token/WebRTC hanya N/A beralasan bila tidak digunakan. Jangan menyalin nomor bab ASVS4 sebagai ASVS5. Target baseline audit adalah applicable L2 beserta inherited L1; klaim conformance membutuhkan register setiap requirement+hasil, tidak cukup daftar bab.

ISO25010:2023 dipakai sebagai model perencanaan, bukan sertifikasi. Safety meliputi dampak tindakan keliru terhadap pengguna/operasi, misalnya isolir salah target atau kehilangan layanan; privasi ditempatkan dalam security/data protection. Target WCAG2.2AA tetap baseline. Traceability requirement kritis100%; semua assertion security/finance kritis wajib teruji; line coverage berubah≥85% adalah AUDIT_DEFAULT untuk kode unit-testable, bukan pengganti bukti integrasi atau perangkat. N/A memerlukan alasan dan approval scope yang sudah ada; kebutuhan kritis tidak dapat di-N/A-kan agar lulus.

[REVISI AUD-42] Profil performa default: tahap10/100/1000 tenant,2router/tenant,300service/tenant; CPE200/tenant hanya R3. Steady auth50request/s untuk NAS profil awal dan accounting=active_sessions/300s. Ramp10menit, warmup10menit tidak masuk sampel, steady30menit, soak8jam tahap10/100 dan24jam tahap1000. Storm10% sesi aktif reconnect60detik: pada300000sesi=500auth/s tambahan; uji “ribuan/s” adalah stress profile2000auth/s60detik tersendiri, bukan salah turunan10%. Minimal10000 sampel per metrik percentile; nearest-rank pada sampel mentah, jangan rata-rata p95 tiap menit.

Pass steady: p95list/enqueue≤2detik, p95auth≤100ms, p95aktivasi normal≤60detik dengan jam mulai enqueue hingga policy/auth verified (belum berarti perangkat online); error non-injected<0.1%; tidak ada cross-tenant/unbalanced/duplicate/lost acknowledged effect. Timeout dihitung gagal, bukan dikeluarkan dari sampel; injected failures mempunyai denominator terpisah. Seluruh tenant aktif mendapat progress dalam60detik AUDIT_DEFAULT; queue age resource tetap dalam budget manifest. Fixture100000service/tenant untuk uji query adalah khusus lab capacity_override, tidak mengubah plafon komersial5000. DR drill2kali/tahun adalah kebijakan operasional default setelah deploy, bukan automation yang dibuat oleh audit ini.

Gerbang dievaluasi per `release+feature+adapter_version+topology+load_profile`, bukan semua modul R1 menunggu CPE R3. G0 desain/ADR actual; G1 protokol/perangkat relevan; G2 tenant/security/finance/restore relevan; G3 pilot terbatas; G4 load/soak/availability; G5 operasional/DR. Gate prerequisite bukan izin untuk menjalankan tes; izin ditentukan scope manifest. G0 dapat mengevaluasi desain tanpa lab; TK002/pin/ADR yang belum dibuat tetap BLOCKED. Fitur memiliki flag sandbox terpisah dari produksi.

Prasyarat fitur PRD26 tetap: inti R1 G0+G2T10/T23; VPN G1T01; cutover G1T16/T17/T18/T21; backup G1spike+G2T08/T09; penjualan G2T05SaaS+otorisasi; autoisolir G1T20+G2T05+G3; ledger G2T12+akuntan; voucher G1T16+G2T24; ACS per modelG1/T11; WAN per topologyG1/T13; edgeG4T22; peningkatan kapasitasG4/G5. Kegagalan satu fitur tidak menyembunyikan hasil fitur independen.

## 21. Evidence, privasi, dan pelaporan yang dapat diaudit

[REVISI AUD-43] Case status kanonik: `NOT_RUN`, `BLOCKED`, `RUNNING`, `PASS`, `FAIL`, `NOT_APPLICABLE`. Gate status: `NOT_EVALUATED`, `BLOCKED`, `PASS`, `FAIL`. Feature evidence: implemented, verified_local, verified_lab, release_enabled; ini dimensi berbeda. Staging aplikasi bisa memenuhi verified_local untuk aplikasi nyata; verified_lab jaringan hanya CHR/perangkat relevan. Tidak mewajibkan router untuk fitur i18n/ledger yang tidak memakai router; prod flag tetap menunggu gate fitur.

Evidence record wajib: schema_version, run_id UUID, case_id, parent, requirements, AUD references, authorization_id+scope hash, approved target IDs, effective config hash, manifest hash, commit/artifact hash dan dirty diff bila ada, exact versions/images/license, fixture seed/hash, started/ended UTC, monotonic duration, steps, assertion_id expected/actual/result, metrics raw reference, artifacts{path,sha256,size,classification}, executor, reviewer_type, cleanup_result, status, blocker. Jangan menyimpan expected dan actual sebagai dua daftar yang tidak mempunyai assertion mapping.

Hash bukan tanda tangan dan tidak membuktikan reviewer independen. Satu agent boleh melakukan self-review checklist tetapi `reviewer_type=self_review`; tidak diklaim independent. Gate yang mewajibkan human/professional/external approval tetap BLOCKED bila belum tersedia; tidak menciptakan reviewer fiktif. Source/test/assertion hash menjadi dasar invalidasi bukti: perubahan schema/policy/adapter/firmware/topology/load membatalkan gate terdampak; pengecekan ulang dokumen saja tidak memperpanjang validitas run lama.

[REVISI AUD-44] Raw PCAP RADIUS/PPP dapat memuat material credential/challenge yang sensitif meski semua akun sintetis. Jangan mengunggah raw capture/debug -X sebagai evidence umum. Capture opsional hanya scope khusus; simpan sementara pada volume terbatasi/enkripsi, ekstrak semantik yang sudah disaring (tipe paket, status, pseudonym sesi, waktu), verifikasi redaksi, hash artefak tersanitasi lalu hapus raw sesuai TTL manifest. Jangan menganggap anonimisasi IP/MAC sudah menghapus password/CHAP material. Jangan memakai hash plaintext password sebagai “redaksi aman”. Bukti bayar/secret/recovery keys tidak ditempatkan pada screenshot/JUnit/nama file.

Execution coverage=executed_cases/applicable_required_cases, dengan executed mempunyai actual step evidence; PASS/FAIL terpisah dari BLOCKED yang sudah mulai. Pass rate=PASS/(PASS+FAIL); denominator nol→null, bukan100%. Requirement design coverage dan requirement verified coverage dilaporkan terpisah. NOT_APPLICABLE yang sah dikeluarkan denominator; NOT_RUN/BLOCKED tetap gap wajib. Flaky/quarantine tidak dihitung PASS dan tetap memblokir gate wajib.

Retensi evidence gate≥umur rilis terkait+90hari setelah superseded; incident400hari; financial10tahun atau legal hold; raw transient capture TTL manifest maksimum24jam default. Metadata sanitized dapat di git privat; raw logs/backup tidak di git. Artifact store failure menahan run yang membutuhkan evidence. Cleanup evidence tidak dilakukan sebelum review/retention/legal hold dipenuhi.

[REVISI AUD-45] UU PDP: tenant bertindak pengendali data pelanggan dan platform prosesor untuk pemrosesan itu; platform dapat menjadi pengendali untuk data akun/billingnya sendiri. Runbook insiden tidak boleh hanya “waktu nanti ditinjau”. Pasal46 UU27/2022 memuat kewajiban pemberitahuan tertulis pengendali paling lambat3×24jam kepada subjek dan lembaga, dengan konten pokok insiden. Kontrak internal menetapkan eskalasi platform kepada pengendali segera, target≤24jam sejak diketahuinya kegagalan, agar pengendali dapat memenuhi tenggat; detail pemicu dan kanal diverifikasi counsel saat rilis. Kewajiban ini bukan pengiriman notifikasi yang dilakukan audit sekarang.

## 22. Hasil audit dan perintah kerja berikutnya

[REVISI AUD-46] Klaim lama QG-DOC10/10 danQG-QA12/12 PASS dicabut sebagai penilaian yang berlaku untuk baseline masukan: temuan teknis, mismatch registry kasus, mapping ASVS dan gap prasyarat bertentangan dengan klaim lengkap/konsisten. V2.1 mencatat hasil statis aktual pada laporan audit, tanpa menandai aplikasi/lab PASS.

Status historis tahap Sol (bukan pengukuran ulang arsip v2.0 pada konsolidasi): dokumen dibaca dan dikoreksi;31/31 hash masukan v2.0 dilaporkan cocok; registri kasus/rujukan/manifest revisi diperiksa statis. Aplikasi, server, GNS3, protokol, benchmark dan DR tidak diakses/dijalankan. Tidak ada compatibility baru, sign-off akuntan/hukum, atau release_enabled yang dibuat.

Perintah tunggal bagi agent berikutnya:

“Baca README, AGENTS, tugas, kontrak dokumen v2.1, spesifikasi domain dan File2 yang berpasangan. Validasi integritas dan input. Jalankan hanya scope yang telah diotorisasi, sesuai dependency dan budget, tanpa persetujuan ulang untuk aksi yang sudah tercakup. Jika input/fakta/izin/reviewer/perangkat wajib tidak tersedia, keluarkan BLOCKED dengan field/reason tepat, lalu lanjutkan pekerjaan independen. Jangan mengarang hasil atau memperluas target. Simpan expected/actual, evidence dan cleanup, dan evaluasi gate per fitur. Untuk mandat audit dokumen saja, berhenti setelah validasi/revisi dokumen dan laporan; jangan menjalankan TK implementasi atau mengakses server.”

Referensi primer yang diperiksa untuk koreksi teknis pada29Oktober2026: MikroTik RADIUS/API/PPP/User/WireGuard/Fetch/SSH, FreeRADIUS SQL readclients, PostgreSQL17 Row Security, GNS3 controller API v3 dan proyek resmi, GenieACS API/environment/connection-request, OWASP ASVS5.0 resmi, WCAG2.2 W3C, ISO25010:2023 metadata, dan UU27/2022 JDIH Komdigi. URL dan batas verifikasi dicatat pada laporan audit. Versi exact server/paket nyata tetap OBSERVED saat implementasi/preflight, bukan diisi berdasarkan versi website.

## 23. Konsolidasi makro normatif 2.1-macro.1

<!-- BEGIN MACRO-NORMATIVE-2.1-macro.1 -->
### MAC-01 — Kewenangan, baseline, dan batas klaim

Tanggal efektif dokumen: **29 Oktober 2026, Asia/Jakarta**. Versi arsitektur tetap **2.1**; revisi paket **2.1-macro.1**. MAC-01–MAC-08 melengkapi AUD-01–AUD-46 berdasarkan mandat konsolidasi pemilik. Pada pokok yang diperinci MAC, klausul MAC berlaku; selain itu hierarki AUD-02 tetap. Ketentuan MAC disimpan di kontrak master §23 dan diproyeksikan utuh ke dokumen gerbang. Perubahan tidak memberi izin eksekusi server, produksi, atau komunikasi kepada pihak lain.

Paket langsung yang diperiksa pada konsolidasi ini memuat **37 berkas, 1.016.000 byte tidak terkompresi**, dengan **36/36** entri manifest cocok. Angka **32 berkas, 549.017 byte, 31/31** adalah baseline audit sebelumnya sebagaimana dicatat Sol; arsip 32 berkas tersebut tidak tersedia sebagai input terpisah pada tahap ini. Klaim historis itu tidak diberi label OBSERVED baru. Manifest v1.4/v2.0 dipertahankan byte-identik terhadap paket langsung, bukan bukti pemeriksaan ulang semua sumber historisnya.

Status `COMPLETED` hanya berlaku untuk `documentation_macro_consolidation`. Dokumen siap menjadi input implementasi yang terikat prasyarat. Aplikasi, runner runtime, exact deployment pins, inventaris host, lisensi CHR, grant lab, review profesional, dan bukti operasional belum tersedia. Parameter desain yang sudah ditetapkan tidak sama dengan konfigurasi deployment yang sudah diamati.

### MAC-02 — Rantai integritas dan penempatan

Rantai verifikasi adalah **byte payload → entri manifest aktif → hash manifest pada dokumen konsolidasi eksternal → hash ZIP pada dokumen eksternal yang sama**. Manifest mengecualikan hanya dirinya sendiri; semua berkas lain, termasuk provenance, bootstrap legacy, alat verifikasi, dan audit, wajib terdaftar. Dokumen konsolidasi eksternal tidak dimasukkan ke ZIP. ZIP tidak menyimpan hash dirinya sendiri. `static-verification_v2_1.json` menyimpan pemeriksaan sebelum penyegelan; hasil pemeriksaan manifest dan ZIP sesudah penyegelan dicatat pada amplop ekspor eksternal sehingga tidak timbul siklus hash.

Daftar payload diurutkan berdasarkan byte UTF-8 path POSIX. Akar payload dihitung sebagai SHA-256 atas gabungan baris `sha256<TAB>size_decimal<TAB>path<LF>`. Berkas di-hash sebagai byte asli; tidak ada normalisasi newline, encoding, whitespace, atau penghapusan komentar saat verifikasi. Root digest bukan tanda tangan dan bukan bukti autentisitas penerbit. Distribusi lintas batas kepercayaan memerlukan digest melalui kanal tepercaya atau tanda tangan yang benar-benar tersedia; paket ini tidak mengarang tanda tangan.

Verifikasi menolak path absolut, traversal, backslash, nama duplikat atau benturan case-fold, symlink, entri hilang/tambahan, hash salah, ukuran salah, dan tabel kosong. TK-001 memverifikasi seluruh paket sebelum menempatkan satu berkas pun. Target identik boleh dilewati; target berbeda menjadi conflict/staging review. `docs/decisions.md` hanya dibuat bila belum ada dan tidak ditimpa. `bootstrap_docs.sh` tetap **LEGACY / AUDIT_ONLY**, bukan penerus bootstrap yang aman. Alat Python dalam paket hanya memeriksa dokumen/arsip secara baca-saja, bukan installer atau runner aplikasi.

### MAC-03 — Retensi finansial dan hak penghapusan

**Sepuluh tahun merupakan minimum retensi dokumen finansial, bukan batas maksimum dan bukan masa simpan seluruh data pelanggan.** SAK EMKM mengatur pelaporan keuangan bagi entitas yang memenuhi syarat; angka retensi ini dirujuk pada UU KUP Pasal 28 ayat (11), PP 50/2022 Pasal 11, serta UU 8/1997 Pasal 11 untuk dokumen perusahaan yang tercakup. Pilihan SAK EMKM/kerangka lain dan penerapannya tetap memerlukan review akuntan. [L1–L4]

Kontrak implementasi berikut merupakan kebijakan sistem MicroTix untuk menjalankan kewajiban tersebut:

1. `ledger.retention_years=10` bertipe integer tahun kalender; minimum 10. Penurunan di bawah 10 ditolak. Kenaikan memerlukan dasar retensi, versi kebijakan, dan review; perubahan konfigurasi tidak memendekkan `retain_until` yang telah disimpan.
2. Simpan `book_id`, `tenant_or_platform_scope`, `fiscal_year_end_date`, `book_timezone`, `record_class`, `retention_policy_version`, `retain_until_utc`, dan daftar `legal_hold_id` pada arsip. Tahun buku terkait ditentukan dari dokumen bisnis, bukan tanggal unggah/backup/penutupan akun. Metadata wajib yang tidak diketahui memblokir purge objek itu.
3. Batas aman paling awal dihitung sebagai awal hari setelah ulang tahun kalender ke-10 dari tanggal akhir tahun buku, pada zona waktu buku. Contoh tahun buku berakhir **31 Desember 2026**: arsip terlindungi sampai akhir **31 Desember 2036**; kandidat penghapusan paling awal **1 Januari 2037 pukul 00.00 Asia/Jakarta**, yakni **2036-12-31T17:00:00Z**, jika semua syarat lain terpenuhi. Tahun kabisat memakai clamp kalender yang konsisten. Koreksi yang masuk tahun buku berikutnya disimpan dengan periode postingnya; relasi bukti yang masih diperlukan memperpanjang retensi dokumen terkait sampai batas terlama.
4. `effective_retain_until = max(financial_floor, applicable_legal_or_contractual_dates, dependent_evidence_dates)`. Legal hold aktif selalu menolak purge walau tanggal terlampaui. Hold memiliki penerbit berwenang, alasan, scope, tanggal, review, dan bukti pencabutan; expiry numerik saja tidak mencabut hold. Proses purge dan aktivasi hold diserialisasi agar hold baru tidak kalah oleh job lama.
5. Cakupan finansial: jurnal dan line, invoice yang menjadi bukti transaksi, payment/allocation, bukti pembayaran yang diperlukan, rekonsiliasi, dokumen pajak, laporan issued, approval/reversal, audit finansial dan versi aturan untuk menafsirkan catatan. Ledger tenant terpisah dari buku platform. Data RADIUS `radacct` bukan buku besar keuangan; default 90 hari mentah/400 hari agregat tetap. Bila subset usage menjadi bukti tagihan, simpan snapshot pembuktian minimal yang terkait invoice dengan retensi finansial, bukan semua packet/raw traffic selama 10 tahun.
6. Retensi SaaS umum 180 hari sejak `ended_at` tidak menghapus arsip finansial/hold dan tidak memaksa penyimpanan semua PII selama 10 tahun. Data yang tidak lagi diperlukan dihapus/diminimalkan sesuai dasar pemrosesan; identitas yang diperlukan sebagai bukti dipertahankan secara terbatas, dapat dipertanggungjawabkan, dan tidak dipakai untuk pemasaran. Penolakan/penundaan sebagian permintaan penghapusan menjelaskan kategori, dasar, dan tanggal evaluasi kepada pengendali/subjek melalui proses berwenang.
7. Lokasi penyimpanan arsip wajib memenuhi ketentuan penyimpanan di Indonesia pada L1/L2; lokasi dan akses faktual dibuktikan sebelum produksi. Enkripsi, pembatasan akses, integritas, keterbacaan format, versi kunci, ekspor dan uji restore berlaku sepanjang masa simpan. Menghancurkan kunci sebelum akhir retensi juga dilarang. Snapshot DR berumur pendek tidak menggantikan arsip finansial.
8. Purge hanya melalui job khusus dengan policy/version snapshot, legal-hold recheck sebelum efek, daftar objek exact, audit keputusan dan bukti penyelesaian. Aplikasi runtime tidak memperoleh DELETE pada jurnal posted. Penghapusan arsip setelah jatuh tempo memakai principal terpisah dan tidak melanggar immutability buku aktif. Backup lama berada pada akses pemulihan terbatas sampai masa rotasinya; deletion ledger diterapkan ulang sebelum hasil restore dibuka. Kegagalan purge/restore bukan alasan menandai penghapusan selesai.

### MAC-04 — Insiden PDP dan tenggat operasional

UU 27/2022 Pasal 46 menetapkan pemberitahuan tertulis oleh pengendali dalam batas **3 × 24 jam** kepada subjek dan lembaga, berisi data yang terungkap, kapan/bagaimana kejadian, serta penanganan dan pemulihan. Dalam kondisi tertentu ada pemberitahuan kepada masyarakat. Kegagalan mencakup kerahasiaan, integritas, dan ketersediaan; bukan hanya kebocoran. [L5]

Ketentuan sistem di bawah adalah **MACRO_DEFAULT operasional**, bukan kutipan penentuan awal jam oleh undang-undang:

- Simpan `incident_occurred_at` (boleh belum diketahui), `first_signal_at`, `processor_known_at`, `controller_known_at`, `clock_basis_at`, `notification_due_at`, sumber observasi, dan riwayat perubahan append-only. Jam pengendalian internal dimulai dari sinyal kredibel pertama yang menunjukkan kegagalan, tidak menunggu forensik lengkap, rapat, atau approval. Bila waktu kejadian yang dapat dipercaya lebih awal tersedia, deadline dihitung konservatif dari waktu lebih awal; discovery terlambat dicatat sebagai risiko keterlambatan, bukan mereset jam. Counsel menentukan kewajiban aktual dan dapat memperpendek tenggat; tidak boleh memperpanjang baseline internal diam-diam.
- Platform sebagai prosesor mengeskalasi segera kepada pengendali, batas internal maksimum **86.400 detik (24 jam)** sejak diketahui; waktu ini berada di dalam anggaran 72 jam, bukan tambahan 24 jam sebelum 72 jam. Platform sebagai pengendali atas akun/billingnya sendiri menjalankan kewajiban pengendali secara langsung. Pemetaan per kegiatan pemrosesan dan DPA mencatat kedua peran ini.
- `notification_due_at = clock_basis_at + 259200 detik`; gunakan waktu UTC dan durasi kalender terus-menerus, tanpa pengecualian akhir pekan/libur. Batas internal draft awal **24 jam**, verifikasi penerima/kanal dan kesiapan pengiriman **48 jam**, tenggat pengiriman **72 jam**. Penanggung jawab dan deputi sudah ditetapkan sebelum go-live. Temuan lebih awal atau kewajiban lebih ketat mempercepat jadwal.
- Pemberitahuan awal memuat informasi yang tersedia dan ketidakpastian faktual; investigasi berlanjut dengan pembaruan. Nomor insiden, pengendali, kategori data/subjek, waktu diketahui/kejadian, dampak, tindakan, kontak dan rencana pemulihan dicatat. Identitas tenant lain, password, secret dan raw packet tidak disertakan. Pernyataan bahwa pemberitahuan telah disampaikan memerlukan bukti kanal menerima pengiriman; draft/queued/attempted tidak cukup. Delivery/read acknowledgment dicatat terpisah.
- Daftar penerima subjek, identitas lembaga berwenang, kanal resmi, kanal alternatif sah, dan bukti verifikasi counsel adalah input rilis wajib; tidak ditebak dari nama kementerian. Pemberitahuan publik dinilai terhadap kondisi hukum dan dampak masyarakat. Ketiadaan kanal di produksi memicu eskalasi darurat dan usaha kanal alternatif sah, tidak menghentikan jam atau kewajiban. G2 readiness privasi dan G5 tetap BLOCKED bila kontak/kanal/reviewer wajib belum tersedia.
- Runbook memiliki incident commander, penanggung jawab privasi/legal, pemilik tenant, pengirim berwenang, deputi dan jadwal piket. Kontrak/proses harus memberikan kewenangan pengiriman insiden terlebih dahulu; tidak menggantungkan tenggat pada pemilik yang sedang tidak hadir. Pengujian memakai penerima sintetis dan notification sink terisolasi. Audit dokumen ini tidak mengirim pesan atau notifikasi nyata.
- Bukti insiden disimpan minimal 400 hari menurut AUD-43; legal hold atau kebutuhan finansial dapat memperpanjang subset terkait. Bukti tersanitasi, audit waktu, hash dan akses terbatas tetap berlaku; raw capture tetap maksimum TTL 24 jam bila diotorisasi.

### MAC-05 — Isolasi multi-tenant RADIUS

Alur kepercayaan wajib: **peer/tunnel terdaftar → transport source NAS yang unik → validasi secret dan authenticator → NAS/router terdaftar beserta applied revision → tenant → facade transaksi → atribut/sesi untuk tenant tersebut**. `User-Name`, `NAS-IP-Address`, realm, `Client-Shortname`, atau tenant pada payload tidak berwenang memilih tenant. Username sama di tenant A/B sah, dengan credential dan atribut masing-masing. Source IP tunnel yang sama tidak boleh terdaftar pada dua NAS; NAT/relay yang menghilangkan identitas source tanpa desain transport terverifikasi memblokir enrollment. [AUD-19–21]

Role RADIUS hanya EXECUTE facade yang dibatasi. Bootstrap lookup hanya mengembalikan metadata client minimum kepada komponen RADIUS tepercaya, bukan directory lintas tenant bagi aplikasi/UI. Konteks NAS berasal dari jalur daemon yang sudah memverifikasi transport; pemanggilan facade dari principal aplikasi atau packet mentah ditolak. Facade memvalidasi NAS aktif, revision, scope, dan binding sebelum transaksi scoped. Tidak tersedia endpoint publik yang menerima klaim `verified_nas_id` tanpa validasi jalur tepercaya. Kepercayaan kepada daemon tersebut dinyatakan eksplisit; desain tidak mengklaim tahan terhadap daemon/backend yang sepenuhnya kompromi.

`ENABLE` dan `FORCE RLS`, role non-owner/non-superuser/non-BYPASSRLS, FK komposit, fungsi dengan `search_path` tepercaya dan `EXECUTE PUBLIC` dicabut berlaku bersama. RLS adalah lapis tambahan; karena principal DB dapat mempunyai kemampuan mengatur variabel sesi, GUC tidak menjadi otoritas identitas yang berdiri sendiri. Semua keputusan tenant berasal dari boundary terverifikasi dan query terparameterisasi; tidak ada jalur arbitrary SQL. Konteks hanya transaction-local pada koneksi yang sama; commit, rollback, error, timeout dan pool reuse diuji. Tidak ada broad DML ke `radius.*` dari aplikasi atau role accounting. [AUD-15,20; R1]

Projection-writer menulis perubahan akun dan proyeksi atomik dengan transaksi bisnis. Uniqueness akun `(tenant,username)` berbeda dari uniqueness atribut `(tenant,account,attribute,scope,ordinal)`. Authorize, accounting, postauth, admission, cache, agregat, edge snapshot dan Disconnect memakai tenant+NAS+account/session yang sesuai. Cache memasukkan revision kebijakan/credential/NAS yang relevan; invalidasi suspend/revoke/rotation diperiksa pada semua instance. Revoke selesai hanya setelah old credential dan cache klien ditolak di semua instance target. Bila instance tidak dapat diperiksa, status belum applied dan fitur terkait ditahan; shutdown sesi existing mengikuti mandat terpisah.

Unknown NAS atau Access-Request dengan Message-Authenticator hilang/tidak sah tidak boleh menghasilkan Access-Accept. Secure discard sah; negative test tidak mensyaratkan balasan Reject. Kredensial tenant B tidak boleh diterima pada NAS tenant A. Uji mencakup response attribute, accounting/postauth, context pool, reset/rollback transaksi, concurrent same username, revocation, key rotation, session limit dan peer firewall. Satu Accept yang salah, satu byte data lintas tenant, atau satu sesi salah target adalah **FAIL kritis** tanpa toleransi persentase. [R2]

Baseline strict admission memakai lock/reservasi per tenant+account, konfirmasi accounting dan rekonsiliasi okupansi positif. Dua NAS serentak pada limit satu harus menghasilkan paling banyak satu Accept yang sah; accounting hilang tidak membebaskan slot. Edge saat terpartisi menolak login yang membutuhkan koordinasi global, dan snapshot kedaluwarsa 900 detik menolak login baru. Dua proses satu VM hanya redundansi proses; klaim host HA memerlukan failure domain, jalur jaringan, data dan kunci yang tetap tersedia saat host primer gagal. Disconnect-Request RFC 5176 menggunakan 3799 yang dikonfigurasi eksplisit; CoA hanya pada capability/build yang terbukti.

### MAC-06 — Dependency lokal, lab, dan produksi

G0 tidak mensyaratkan CHR/CPE. Implementasi/test lokal tetap membutuhkan mandat Mode C, source/build, runner, konfigurasi, dan target workspace yang jelas. Dalam registry, kasus aplikasi yang tidak bergantung perangkat memakai dependency `EXECUTION_PROFILE_READY` sebagai pengganti V1/V2/V3 generik. Profil ini memilih salah satu jalur secara eksplisit: **lokal/CI terotorisasi** (workspace+artifact+resource+evidence) atau **remote** (File 2 V1–V3 lengkap). Tidak ada pilihan otomatis dari null, dan tidak ada akses server melalui profil lokal. V0 dan V4 tetap diperiksa sesuai konteks; fakta eksternal tetap tidak boleh direkayasa.

Kasus jaringan, fault/DR/load, peer firewall, RADIUS transport, enrollment dan model ACS tetap memerlukan lab/target nyata serta grant sesuai operasi. Emulator ACS hanya membuktikan kontrak; release model fisik membutuhkan firmware/model nyata. Uji ledger/i18n tidak menunggu hardware ACS. Fake clock hanya untuk logika tanggal/retensi/deadline bisnis; tidak mengganti canary 1.800 detik, observasi B4 86.400 detik, TTL protokol dan soak waktu nyata.

Dependency persiapan berbeda dari gate rilis. T17 memakai fixture authoritative yang dibuat khusus dan terotorisasi untuk membuktikan T18/T21 sebelum cutover; fixture itu bukan hasil cutover. T09 restore lab dapat dijalankan untuk memenuhi prasyarat T17 tanpa menunggu seluruh G2 lulus; karena G2 sendiri juga memerlukan sebagian G1, menjalankan uji tidak boleh digantungkan pada gate yang akan dinilainya. Tidak ada lingkaran G1→G2→G1 atau G3→flag produksi→G3. Pilot memakai capability terbatas per change plan, bukan pengaktifan umum.

Pada pemilihan run, dependency case di-resolve transitif; missing/unknown dependency, cycle, scope di luar grant atau deadline/window tidak cukup menghasilkan BLOCKED. Dependency readiness token bukan hasil PASS yang boleh diasumsikan; setiap token mempunyai evidence dan pemeriksa. Registry tetap 64 child T01–T24 + 20 QA-SEC; assertion tambahan MAC memperketat ID existing. Semua case masih `NOT_RUN` sampai ada observasi aktual.

### MAC-07 — Keputusan gate dan kewenangan rilis

Gate dievaluasi per tuple `release, feature, adapter_version, topology, load_profile` dan hash requirement/test/config. `NOT_EVALUATED` berarti evaluasi formal belum dilakukan; `BLOCKED` berarti pemeriksaan kesiapan/evaluasi mendapati prasyarat wajib tidak tersedia; `FAIL` berarti assertion/invariant atau kebijakan dilanggar; `PASS` hanya bila seluruh bukti dan review wajib memenuhi scope. Prioritas agregasi **FAIL > BLOCKED > PASS**; gate yang belum pernah dievaluasi tetap NOT_EVALUATED. Kegagalan kritis tidak diturunkan menjadi BLOCKED hanya karena bukti lain kurang.

Konsolidasi ini mengevaluasi **kesiapan prasyarat**, sehingga G0–G5 berstatus **BLOCKED**, dengan `runtime_executed=false`; tidak ada assertion runtime berstatus FAIL/PASS baru. QG-DOC/QG-QA formal tetap NOT_EVALUATED, sedangkan hasil pemeriksaan statis Python dilaporkan terpisah. Pencabutan all-pass historis tetap berlaku. Self-review bukan review independen atau sign-off akuntan/hukum.

`release_enabled` memerlukan implementasi, bukti lingkungan yang relevan, semua minimum gate fitur, tidak ada blocker kritis/high yang dapat dieksploitasi, persetujuan profesional yang diwajibkan, dan mandat perubahan produksi. Gate PASS tidak memberi akses produksi. Izin tidak menggantikan gate PASS. Sandbox flag terpisah dapat dipakai untuk pengujian terotorisasi. Perubahan schema/policy/adapter/firmware/topology/load/config atau assertion membatalkan bukti yang terdampak; perubahan editorial murni memakai analisis dampak tercatat, bukan retest otomatis semua perangkat.

### MAC-08 — Registri kontrol tambahan dan akuntabilitas

Tabel berikut merupakan perluasan TD §16; key existing `ledger.retention_years` diperketat, bukan dibuat dua sumber nilai. Seluruh nilai efektif disnapshot dalam profil run. Field kontak/kanal/reviewer merupakan data deployment yang harus nyata, bukan default hasil audit.

| Key | Tipe; satuan | Default/batas | Scope; sumber; versi efektif | Perubahan |
|---|---|---|---|---|
| `ledger.retention_years` | integer; tahun kalender | 10; minimum 10 | book; LEGAL_MINIMUM + MAC-03; 2.1-macro.1 | Tidak memendekkan batas tersnapshot; kenaikan beralasan dan direview |
| `privacy.incident.processor_escalation_max_s` | integer; detik | 86400; 1..86400 | platform/DPA; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Boleh diperketat, tidak ditambah di depan tenggat pengendali |
| `privacy.incident.initial_draft_max_s` | integer; detik | 86400; 1..86400 | incident response; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Draft ≤ delivery readiness ≤ notification deadline |
| `privacy.incident.delivery_ready_max_s` | integer; detik | 172800; 1..172800 | incident response; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Kenaikan memerlukan revisi kontrak, bukan override runtime |
| `privacy.incident.notification_deadline_s` | integer; detik | 259200; 1..259200 | controller activity; LEGAL_LIMIT + operational clock MAC-04; 2.1-macro.1 | Boleh lebih ketat; interpretasi counsel dicatat tanpa mereset jam |
| `release.pilot.max_tenants` | integer; tenant | 1; baseline maksimum 1 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Profil/ADR disetujui sebelum run untuk mengubah cap |
| `release.pilot.max_routers` | integer; router | 1; baseline maksimum 1 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Profil/ADR disetujui sebelum run untuk mengubah cap |
| `release.pilot.max_services` | integer; layanan | 50; baseline maksimum 50 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Tidak mengubah kuota paket komersial |
| `release.pilot.min_observation_days` | integer; hari kalender nyata | 7; minimum 7 dan mencakup siklus relevan | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Perpanjang bila siklus belum teramati; tidak dipersingkat demi PASS |

Pemilik produk menetapkan scope; arsitek memelihara kontrak/dependency; maintainer/QA memelihara registry, assertion dan bukti; security owner menguji isolasi; finance owner bersama akuntan meninjau posting/retensi; privacy/legal owner memverifikasi pemrosesan dan kanal; release owner memutuskan aktivasi pada change plan; operations owner memegang recovery/insiden. Nama dan bukti penugasan aktual wajib saat gate terkait; gelar/role pada dokumen tidak berarti seseorang telah menyetujui.

Rujukan primer, diperiksa 29 Oktober 2026; rujukan ini membuktikan teks aturan/semantik yang dikutip, bukan inventaris deployment atau sertifikasi kepatuhan:

- **L1** — DJP, UU 28/2007 perubahan UU KUP, Pasal 28(11): https://stats.pajak.go.id/undang-undang-nomor-28-tahun-2007
- **L2** — DJP, PP 50/2022 Pasal 11: https://pajak.go.id/en/node/90278
- **L3** — Kementerian Keuangan, UU 8/1997 Pasal 11: https://fiskal.kemenkeu.go.id/files/peraturan/file/1997%20UU%208.pdf
- **L4** — IAI, Tentang SAK EMKM: https://web.iaiglobal.or.id/SAK-IAI/Tentang%20SAK%20EMKM
- **L5** — JDIH Komdigi, UU 27/2022 Pasal 46 dan penjelasannya: https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/
- **R1** — PostgreSQL 17, Row Security Policies: https://www.postgresql.org/docs/17/ddl-rowsecurity.html
- **R2** — MikroTik, RADIUS: https://manual.mikrotik.com/docs/authentication-authorization-accounting/radius/
<!-- END MACRO-NORMATIVE-2.1-macro.1 -->


## 24. Kontrak penyelesaian dokumentasi untuk build — 2.1-build.1

Tanggal 30 Oktober 2026 Asia/Jakarta. Mandat pemilik: “Lakukan secara end to end sampai dokument benar-benar siap produksi ke fase build/eksekusi”, dilanjutkan “Lanjutkan”. Ini mengesahkan penyelesaian dokumentasi dan pilihan B01/B02 yang telah direkomendasikan; tidak mengubah Mode A menjadi izin implementasi aplikasi/akses infrastruktur. Arsitektur tetap v2.1. Tidak ada tanda tangan profesional atau grant server yang disimpulkan dari mandat ini.

### EXE-01 — Batas efek dan pembatalan job

`executing → cancelled` sah hanya bila `effect_state=none` terbukti untuk aksi job tersebut, tidak ada pengiriman outstanding dan setiap worker/koneksi lama telah difence atau dihentikan sehingga tidak dapat mengirim. Pemeriksaan permission/policy/hold/revision terakhir dilakukan sesaat sebelum efek. Perubahan DB/outbox persiapan bukan bukti efek perangkat; commit proyeksi autentikasi atau posting finansial yang merupakan tujuan aksi adalah efek. Setiap kind mendefinisikan boundary-nya dalam registry. `effect_state=maybe|confirmed`, response hilang, atau fence tidak terbukti melarang cancelled dan resend; gunakan uncertain, readback, lalu recovery_required bila diperlukan. DB lock sendiri bukan fence perangkat. Pembayaran tidak menjadi izin aktivasi otomatis. Kompensasi tetap memerlukan kewenangan, scope, baseline dan revision yang cocok; ia tidak menghapus histori aksi asli.

### EXE-02 — ACS: status perangkat dan outcome job

Task ACS dan job platform memiliki field terpisah: `device_task_state`, `device_task_observed_at`, `job_state`, `effect_state`, `correlation_id`, `remote_task_id` nullable sebelum identitas diketahui. Enum task perangkat mengikuti AUD-37; uncertainty/recovery adalah state job AUD-14. `queued` dipetakan ke queued/claimed/preflight; `waiting_inform` ke waiting_dependency setelah submission terkonfirmasi; `running` ke executing; `verifying` ke verifying; succeeded baru dipetakan succeeded sesudah RPC/fault+readback/fungsi sesuai capability membuktikan hasil. Task failed memetakan job failed hanya jika efek diketahui; jika tidak, uncertain/recovery_required. Expired/cancelled memetakan job cancelled dengan reason hanya setelah penghapusan pending task milik run terkonfirmasi dan tidak ada efek; kemungkinan efek mengikuti EXE-01. Hilangnya task tidak mengubah last-observed task menjadi succeeded. API/UI menampilkan job uncertain/recovery_required mendahului label task yang mungkin stale. Timeout submission tanpa remote_task_id dicari lewat correlation sebelum resend; tanpa bukti tidak terkirim, resend dilarang. Tidak ada transaksi atomik ACS–RADIUS baru.

### EXE-03 — Registri konfigurasi dan kind yang dapat divalidasi

TD §16 tetap pemilik konfigurasi; `sumber/contracts/parameter-registry_v2_1.json` adalah materialisasi terstruktur nilai AUD-09/MAC-08/TD. Alias lama hanya diterima pada import migrasi, dikonversi exact, lalu disimpan sebagai key kanonik. Dua alias/canonical bersamaan ditolak sekalipun nilainya sama. Unknown key/duplicate key/type salah ditolak. Angka decimal dikirim sebagai string, tanpa float. Bila sumber tidak menyetujui rentang, default yang ada dapat dipakai; override membutuhkan revisi registry/ADR, bukan rentang rekaan. Nilai deployment yang belum diketahui tetap required-input; bukan default produk. Precedence konfigurasi: default terpin → override sah pada scope yang diizinkan → snapshot immutable per job/run/document. Tidak ada override yang melemahkan constraint master. Job-kind registry menetapkan dedup, boundary, verifier, retry, compensation dan deadline policy. Kind kompleks tanpa angka yang disetujui menggunakan deadline eksplisit pada profil run dengan batas minimum struktural dan grant window; tidak fallback ke timeout job sederhana.

### EXE-04 — Kontrak task dan traceability

`agent/task-contracts_v2_1.json` melengkapi 85 TK pada tugas §9, bukan backlog kedua. Task ID, objective dan scope rilis dipertahankan; dependency task eksplisit mengalahkan urutan nomor. Dependency milestone `contract`, `build` dan `verified` berbeda; pekerjaan scaffold tidak menunggu hasil lab yang akan dibangunnya. Output prasyarat yang belum dibuat adalah pekerjaan TK upstream, bukan input owner yang boleh dikarang. `sumber/contracts/Execution_Design_v2_1.md` dan kontrak task adalah design elaboration, tunduk pada AUD/MAC/keputusan. Registry traceability menunjuk source clause, design, task, acceptance dan assertion; edge bukan bukti eksekusi. Tambahan test contract memperluas coverage tanpa menghapus 84 case dan 318 assertion baseline.

### EXE-05 — Applicability keamanan, test dan fixture

ASVS 5.0.0 L1+L2 dimaterialisasikan per requirement, sumber release terpin dan hash tersedia. N/A wajib memiliki predikat fitur, bukti absence dan reviewer; N/A tidak boleh dipakai untuk menutupi kontrol yang gagal. Kontrol ASVS yang berpotensi mengubah kebijakan autentikasi/otorisasi menjadi decision record, bukan override diam-diam. Case/asertion applicability dibekukan per release+feature+resource pada run. R1 tetap menguji isolasi seluruh resource R1; resource R3 yang belum dibangun tidak diwajibkan secara palsu dan tidak boleh bocor lewat endpoint tersembunyi. Case baru tetap TEST_DESIGNED/NOT_RUN. Fake time hanya logika bisnis; protocol canary/TTL/soak tetap real time. Kontrak fixture boundary dan replay ada di Execution Design; replay diberi label, bukan bukti real-time protocol.

### EXE-06 — Profil dan target yang eksplisit

`execution-profile.schema.json` menetapkan profil lokal/CI; `target-registry.schema.json` melengkapi resolver target File 2. Schema tidak menciptakan grant. Local profile hanya workspace/resource milik run, tidak membawa SSH/GNS3/produksi. Remote profile memerlukan File 2 V1–V3 plus target ID teresolusi, identity/pin/allowlist/window/operations yang cocok. Input DRAFT yang kosong dapat dibaca untuk persiapan, tidak dapat berstatus READY. Unknown fields/IDs, cycle jump host, compute yang tidak terdaftar, credential literal, placeholder, izin expired, dan scope mismatch ditolak. Null/empty bukan wildcard.

### EXE-07 — Tiga penilaian kesiapan

`DOCUMENTATION_READY_FOR_SCOPED_BUILD` hanya menyatakan kontrak task pada scope tertentu lengkap dan pemeriksaan statis lulus; bukan G0 PASS. `BUILD_AUTHORIZED` membutuhkan mandat Mode C dengan workspace dan scope eksplisit; paket ini tidak memberikan mandat tersebut. `OPERATIONAL_RELEASE_READY` membutuhkan G0–G5 applicable, review dan grant produksi. NOT_RUN adalah keadaan wajar sebelum implementasi. Prasyarat profesional/perangkat diterapkan pada milestone yang membutuhkannya; tidak memblokir penyusunan kode/fixture lokal yang independen. Task yang bergantung keputusan bisnis baru tetap BLOCKED sampai keputusan tersebut nyata.

### EXE-08 — Handoff Claude–Codex

Claude executor, Codex architecture reviewer. Siklus: CLAUDE_IMPLEMENT → AUTOMATED_TEST → CODEX_REVIEW → CLAUDE_FIX → REVALIDATE. Maksimum tiga putaran perbaikan per task per siklus; ini batas workflow, bukan retry produk. Hentikan lebih awal bila tidak ada perubahan hipotesis, butuh keputusan pemilik, grant, atau recovery tidak aman. Review harus menyebut trigger, source, expected/actual, severity dan koreksi minimum; balasan Claude menyertakan diff/commit, perintah aktual, exit code, assertion evidence dan cleanup. Reviewer implementasi bukan author perubahan yang sama. Validator terpisah dari penulis bukan bukti review semantik independen; label reviewer_type harus faktual. Definition of Done per task memisahkan contract_complete, implemented, verified dan release_enabled.
