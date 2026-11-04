# Standar kualitas dan klasifikasi — MicroTix v2.1

[REVISI AUD-01–46 / MAC-01–08] Proyeksi normatif kontrak master v2.1 revisi 2.1-macro.1. Bagian AUD di bawah dihasilkan dari master; §23 MAC memperinci retensi/PDP/RADIUS/dependency/gate. Baca master §23 dan Quality_Gates_and_Release_Readiness_v2_1.md sebelum implementasi. Status runtime NOT_RUN.

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

## 20. Desain pengujian, standar, dan gerbang

[REVISI AUD-40] Penghitungan sumber: matriks lama memuat62 child ID setelah shorthand diurai; spesifikasi memuat35 blok id, bukan30. Ada27 ID matriks tanpa blok lengkap dan dua ID negatif T16 yang hanya disebut di narasi. Registry v2.1 menyatukan64 child ID dan20 QA-SEC case. Jumlah di laporan/matriks dihasilkan dari registry, bukan diketik sebagai58. Setiap case mempunyai ID tunggal, dependency, fixture seed/hash, setup, aksi, expected assertion, deadline, bukti dan cleanup. Semua eksekusi aplikasi tetap NOT_RUN.

Spec common mengikat semua row registry: data sintetis seed261029; clock terkontrol untuk unit tetapi waktu nyata untuk protokol/canary/soak; dua tenantA/B, NASA1/A2/B1, dua akun kontrol non-target; actor/permission sesuai operasi; snapshot state sebelum efek; status NOT_RUN sampai actual observation ada; PASS hanya semua assertion benar, bukti lengkap dan cleanup aman. Missing required field→BLOCKED sebelum aksi. Runtime runner/harness belum ada adalah blocker tersendiri, bukan hanya “akses belum tersedia”. Registry dan spesifikasi final disertakan pada quality/Test_Case_Specifications_v2_1.md.

[REVISI AUD-41] ASVS5.0 mapping yang benar: V1Encoding/Sanitization; V2Validation/Business Logic; V3Web Frontend; V4API/Web Service; V5File Handling; V6Authentication; V7Session; V8Authorization; V9Self-contained Tokens; V10OAuth/OIDC; V11Cryptography; V12Secure Communication; V13Configuration; V14Data Protection; V15Secure Coding/Architecture; V16Security Logging/Error Handling; V17WebRTC. OAuth/token/WebRTC hanya N/A beralasan bila tidak digunakan. Jangan menyalin nomor bab ASVS4 sebagai ASVS5. Target baseline audit adalah applicable L2 beserta inherited L1; klaim conformance membutuhkan register setiap requirement+hasil, tidak cukup daftar bab.

ISO25010:2023 dipakai sebagai model perencanaan, bukan sertifikasi. Safety meliputi dampak tindakan keliru terhadap pengguna/operasi, misalnya isolir salah target atau kehilangan layanan; privasi ditempatkan dalam security/data protection. Target WCAG2.2AA tetap baseline. Traceability requirement kritis100%; semua assertion security/finance kritis wajib teruji; line coverage berubah≥85% adalah AUDIT_DEFAULT untuk kode unit-testable, bukan pengganti bukti integrasi atau perangkat. N/A memerlukan alasan dan approval scope yang sudah ada; kebutuhan kritis tidak dapat di-N/A-kan agar lulus.

[REVISI AUD-42] Profil performa default: tahap10/100/1000 tenant,2router/tenant,300service/tenant; CPE200/tenant hanya R3. Steady auth50request/s untuk NAS profil awal dan accounting=active_sessions/300s. Ramp10menit, warmup10menit tidak masuk sampel, steady30menit, soak8jam tahap10/100 dan24jam tahap1000. Storm10% sesi aktif reconnect60detik: pada300000sesi=500auth/s tambahan; uji “ribuan/s” adalah stress profile2000auth/s60detik tersendiri, bukan salah turunan10%. Minimal10000 sampel per metrik percentile; nearest-rank pada sampel mentah, jangan rata-rata p95 tiap menit.

Pass steady: p95list/enqueue≤2detik, p95auth≤100ms, p95aktivasi normal≤60detik dengan jam mulai enqueue hingga policy/auth verified (belum berarti perangkat online); error non-injected<0.1%; tidak ada cross-tenant/unbalanced/duplicate/lost acknowledged effect. Timeout dihitung gagal, bukan dikeluarkan dari sampel; injected failures mempunyai denominator terpisah. Seluruh tenant aktif mendapat progress dalam60detik AUDIT_DEFAULT; queue age resource tetap dalam budget manifest. Fixture100000service/tenant untuk uji query adalah khusus lab capacity_override, tidak mengubah plafon komersial5000. DR drill2kali/tahun adalah kebijakan operasional default setelah deploy, bukan automation yang dibuat oleh audit ini.

Gerbang dievaluasi per `release+feature+adapter_version+topology+load_profile`, bukan semua modul R1 menunggu CPE R3. G0 desain/ADR actual; G1 protokol/perangkat relevan; G2 tenant/security/finance/restore relevan; G3 pilot terbatas; G4 load/soak/availability; G5 operasional/DR. Gate prerequisite bukan izin untuk menjalankan tes; izin ditentukan scope manifest. G0 dapat mengevaluasi desain tanpa lab; TK002/pin/ADR yang belum dibuat tetap BLOCKED. Fitur memiliki flag sandbox terpisah dari produksi.

Prasyarat fitur PRD26 tetap: inti R1 G0+G2T10/T23; VPN G1T01; cutover G1T16/T17/T18/T21; backup G1spike+G2T08/T09; penjualan G2T05SaaS+otorisasi; autoisolir G1T20+G2T05+G3; ledger G2T12+akuntan; voucher G1T16+G2T24; ACS per modelG1/T11; WAN per topologyG1/T13; edgeG4T22; peningkatan kapasitasG4/G5. Kegagalan satu fitur tidak menyembunyikan hasil fitur independen.
