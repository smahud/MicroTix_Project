# AGENTS.md — Aturan tetap untuk agent coding (v2.1)

[REVISI MACRO 2.1-macro.1] MAC-01–08 mengikat semua task. Mode A mengizinkan Python untuk pemeriksaan/ekspor dokumen, bukan implementasi aplikasi. Verifier paket tidak memberi izin menjalankan bootstrap legacy. Profil lokal/CI dan lab dibedakan menurut MAC-06; self-review tetap bukan reviewer independen. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


Versi 1.4 · 28 Oktober 2026. Riwayat: 1.2 (11 Oktober 2026) → 1.3 (28 Oktober 2026; penyelarasan referensi dan sumber kebenaran — putusan DOC pada `decisions_log.md` Bagian E) → 1.4 (28 Oktober 2026; menambah mode otorisasi kerja A/B/C, kebijakan pengujian dan bukti, keselamatan lab GNS3, serta rujukan dokumen kualitas `sumber/quality/` — paket MicroTix-Documentation-Quality-Ready).

Proyek: Platform SaaS Manajemen RT/RW Net (solusi end-to-end bagi pengusaha RT/RW Net di Indonesia; antarmuka multi bahasa, default Indonesia). Pemilik produk: Huda Choirul Anam.
File ini singkat dan **selalu berlaku**. Instruksi kerja lengkap ada di `tugas.md` (dari `tugas_v2_1.md`). Letakkan file ini di root repository sebagai `AGENTS.md`.

## Baca dahulu (berurutan)

1. Baca kontrak master §0–2, §23 dan klausul domain task; manifest aktif serta blocker `docs/audit/Unresolved_Issues_v2_1.md`. Lalu baca bagian task terpilih di `tugas.md` beserta dependency dan acceptance yang dirujuk; tidak perlu memuat seluruh registry case untuk satu task.
2. Keputusan kanonik: `docs/source/decisions_log.md`; `docs/decisions.md` hanya log temuan X-nn dan bukan salinan otoritas kedua. Keputusan C/D/N/T/DOC yang sudah disetujui tetap berlaku; konflik/celah baru dilaporkan, tidak dianggap selesai karena keputusan lama final. ID keputusan `T-01` berbeda dari parent test `T01`.
3. Baca hanya keputusan dan bagian PRD/TD/domain/UI terkait task beserta prerequisite lintas domain. Path paket `sumber/` dipetakan oleh manifest ke `docs/source/`, `docs/quality/`, atau `docs/audit/`; path root master tetap. Jangan mengubah sumber normatif diam-diam.
4. `docs/progress.md` dan `git diff` bila melanjutkan sesi.
5. Baca quality gate applicable dan common test contract, lalu case yang terkait task dari registry JSON atau proyeksi Markdown (cukup salah satu representasi full-text). PRD §26 dibaca bersama AUD/MAC dan detail gate quality yang didelegasikan. Provenance/historical hanya dimuat bila bukti atau sengketa sumber memerlukannya.

Urutan kewenangan [REVISI AUD-02]: instruksi pemilik yang berlaku → kontrak audit v2.1 pada pokok yang dikoreksi → decisions → PRD → TD → domain → UI/UX → tugas → quality/audit. Teks normatif mengalahkan sketsa.

## Larangan keras

**Lingkungan dan data**
- Jangan menyentuh router pelanggan, deployment produksi, kredensial produksi, atau mengirim pesan ke pelanggan. Hanya lab/dev yang diotorisasi. Jangan mengakses IP/host di luar lab yang diizinkan.
- Jangan menyimpan secret di git, log, fixture, error, analytics, atau browser. Jangan menaruh password/token/skrip bootstrap di URL.
- Satu-satunya email yang boleh dikirim adalah email transaksional akun SaaS (dev: Mailpit/penangkap lokal).

**Keamanan**
- Jangan mematikan atau melemahkan TLS, RLS (ENABLE+FORCE), CSRF, validasi host, atau menghapus/melemahkan tes agar build lulus.
- Jangan memakai `verify=false` pada koneksi RouterOS; sertifikat API wajib dipin (sidik jari SHA-256).
- Jangan memberi role runtime superuser/BYPASSRLS; jangan memberi `INSERT/UPDATE/DELETE` langsung pada tabel ledger kepada role runtime.
- Jangan menerima raw RouterOS command, URL host, SQL/Mongo, script, atau JavaScript ACS dari pengguna; jangan mengeksekusi comment/on-login/script yang dibaca dari router.
- Jangan membuka Prometheus, Grafana datasource, ACS NBI, MongoDB, atau FreeRADIUS ke browser/tenant/internet. FreeRADIUS hanya mendengarkan alamat tunnel.
- Jangan menulis password layanan atau secret RADIUS ke log, audit, export, error, analytics, atau tabel UI. Jangan memakai kembali secret RADIUS antarrouter.
- Jangan membuat kueri RADIUS yang tidak memfilter `tenant_id` dari klien NAS; jangan menentukan tenant dari username.

**Jaringan dan RADIUS**
- Jangan route default atau seluruh LAN tenant lewat VPN SaaS. Jangan `0.0.0.0/0` sebagai allowed route manajemen. Jangan mengizinkan peer-ke-peer.
- Jangan menulis konfigurasi RADIUS ke router di luar operasi cutover (`CutoverRun`) yang eksplisit, ber-backup, ber-canary, dapat di-rollback, dan hanya pada mode `manage` + permission `radius.cutover`.
- Jangan menonaktifkan/menghapus secret atau user lokal router kecuali objek tersebut cocok dengan `access_account_source` dan revision-nya, per batch, setelah backup, pada mode otoritatif. Jangan menghapus otomatis; jangan memigrasikan secret `service` selain pppoe/any.
- Jangan membaca password dari router kecuali lewat akun migrasi sementara (≤ 24 jam, penghapus otomatis, batas laju) atas persetujuan Owner + reautentikasi.
- Jangan mengklaim isolir/kecepatan/pindah-router dijamin pada router yang bukan `radius_authoritative`.
- Jangan menyalakan/mematikan FastTrack atau mengubah firewall pelanggan pada R1–R3 (hanya deteksi dan lapor).
- Jangan membuat PCC pada router yang memiliki Hotspot server aktif.
- Jangan auto-upgrade firmware, reboot, restore binary, atau reset router (termasuk sebagai rollback). Safe Mode bukan transaksi.
- Jangan membuat akun, reset, reboot, atau ganti profile router saat discovery/adopsi (hanya baca; commit adopsi database-only).

**Uang dan data**
- Jangan memakai float untuk uang (`numeric(20,2)`, JSON string). Jangan memakai `.id` RouterOS sebagai identitas bisnis; identitas akses = (tenant, username).
- Jangan menjurnal invoice prabayar yang belum dibayar; jangan menjurnal invoice historis bersama piutang saldo awal.
- Jangan mengedit/menghapus journal posted (hanya reversal/adjustment); jangan memposting ke periode closed.
- Jangan mengisolir pelanggan internet karena tunggakan SaaS. Pembukaan setelah bayar tetap manual. Hold (security/technical/manual) mengalahkan pembayaran.
- Jangan mengubah nomor rekening dan nomor konfirmasi pembayaran dari pemilik (nomor konfirmasi: 082319199930); jangan memublikasikan rekening di landing.
- Jangan menandai bukti upload sebagai dana diterima.

**Bahasa dan UI**
- Jangan menanamkan teks tampil pada kode; semua lewat katalog pesan. Bahasa default `id`, wajib `en`. Jangan menerjemahkan kode mesin (enum, kode error, atribut RADIUS).

**Proses**
- Jangan menandai selesai berdasarkan mock/simulator. Jangan menulis "production-ready" tanpa gerbang lulus. Jangan menyatakan kompatibilitas tanpa `verified_lab`.
- Jangan mengubah parameter terkunci, enum, atau arti status tanpa instruksi eksplisit pemilik + ADR + sinkron ke TD.
- Jangan mengarang persetujuan, hasil uji, atau versi yang belum diperiksa.

## Status yang dipakai (jangan dicampur)

Empat status pembuktian (`implemented` → `verified_local` → `verified_lab` → `release_enabled`) didefinisikan pada `tugas.md` §3. Test tidak dijalankan = `NOT RUN` + alasan; `skipped` bukan lulus. Hanya `release_enabled` tampil di menu harian.

## Mode otorisasi kerja (jangan dicampur)

- **MODE A — dokumentasi dan desain uji.** Audit, penulisan, penyelarasan dokumen; verifikasi hash dan analisis statis di workspace terisolasi. Dilarang: implementasi aplikasi, deploy, akses server/router/GNS3, runtime testing, atau klaim hasil uji.
- **MODE B — validasi lab non-produksi (hanya setelah instruksi tertulis pemilik: target, jalur akses, scope, tingkat izin, persetujuan menjalankan uji).** Kredensial/IP/SSH **bukan** persetujuan mutasi. Awali inventaris read-only; bedakan produksi/staging/dev/lab. Uji hanya pada lab terisolasi, data sintetis, image legal, batas resource; simpan bukti aktual. Tanpa mutasi produksi atau router pelanggan. Pilot produksi (G3) butuh mandat tersendiri.
- **MODE C — implementasi/rilis.** Pelaksanaan TK-xxx, modifikasi kode, commit/push, deploy, pengaktifan fitur — memerlukan mandat implementasi eksplisit pemilik. Akses produksi, termasuk inventory read-only, tetap memerlukan mandat target/scope; tidak diberikan oleh audit dokumentasi atau Mode C lokal.

Pisahkan status: **document validated**, **test case designed**, **environment ready**, **test executed**, **test passed**, **verified_lab**, **release_enabled** — bukan sinonim. Persetujuan kelas aksi (READ / NON-DESTRUCTIVE LAB WRITE / DESTRUCTIVE LAB WRITE / PRODUCTION CHANGE) berbeda dari sekadar memegang akses teknis; matriks lengkap di `Lab_Onboarding_and_Access_v2_1.md`.

## Kebijakan pengujian dan bukti

- Kelulusan **desain** uji (QG-QA, `Quality_Gates_and_Release_Readiness_v2_1.md`) tidak sama dengan kelulusan **eksekusi** (G0–G5, PRD §26). Jangan menyebut keduanya sebagai satu hal.
- Test tidak dijalankan = `NOT RUN — ACCESS/APPROVAL NOT PROVIDED` (atau `BLOCKED` bila ada blocker spesifik) + alasan; `skipped` bukan lulus. Runtime test tanpa lab terotorisasi tidak boleh ditandai PASS/FAIL.
- `verified_lab` hanya untuk eksekusi nyata pada RouterOS nyata/CHR/CPE lab terotorisasi dengan versi/topologi tercatat; simulator/stub paling jauh `verified_local` sesuai kontrak task (tugas §3).
- Setiap eksekusi uji mencatat bukti sesuai skema `Test_Evidence_and_Reporting_v2_1.md`: run_id, versi, topologi, expected vs observed, hash artefak, redaksi PII/secret, timestamp UTC. Tanpa bukti = tidak lulus.
- **Anti-gaming (DILARANG):** mengubah/menonaktifkan tes agar PASS; menurunkan threshold/severity tanpa keputusan pemilik; mock menyamar sebagai CHR; menyimpulkan PASS dari HTTP 202; rerun selektif hanya kasus lulus; menyetel expected output agar cocok bug tanpa review; menghapus log kegagalan; memalsukan benchmark. Flaky test diisolasi untuk root-cause, bukan dihitung PASS dari rerun.
- Kegagalan keamanan/isolasi tenant/ledger = blocker rilis terlepas dari pass rate lain. Temuan kritis/high yang dapat dieksploitasi memblokir `release_enabled` (PRD AC-SEC).
- Verifikasi independen (reviewer ≠ pelaksana, atau checklist verifikasi eksplisit) membaca kembali acceptance dan artefak sebelum mengklaim gerbang lulus.

## Keselamatan lab jaringan dan GNS3

- Controller/compute GNS3 tidak diekspos ke internet; akses hanya lewat VPN/SSH tunnel yang disetujui pemilik. Project GNS3 memakai namespace khusus per test run; tanpa bridging ke LAN/produksi (deny-by-default); egress allowlist; kuota CPU/RAM/disk per lab; snapshot sebelum dan cleanup + teardown setelah run.
- Gunakan GNS3 REST API yang **terverifikasi versinya** sebagai jalur otomasi; fitur MCP opsional hanya setelah verifikasi kemampuan/versi nyata — jangan mewajibkan fitur alpha/beta tanpa ADR + fallback.
- CHR adalah RouterOS virtual: bukan pembuktian radio/wireless/ASIC; hasil berlaku hanya untuk versi/lisensi/host yang diuji; catat lisensi uji dan batas validitas (`GNS3_Lab_Architecture_v2_1.md`).
- Sebelum lab pertama: baca `Lab_Onboarding_and_Access_v2_1.md`, lengkapi inventaris terstruktur (TBD menunggu pemilik), jalankan preflight izin/jaringan/image/backup/kapasitas, dan pastikan scope provisioning sudah diotorisasi; preview tersimpan sebagai artefak, tanpa meminta persetujuan ulang bila grant masih berlaku. Tidak ada tindakan pada router pelanggan di mode apa pun.

## Cara kerja

- Vertical slice: schema → service → API → UI → test → dokumen. Satu logical change per commit; ID sumber (mis. RAD-09, ED21, U19, TK-509) di pesan commit.
- **202 = diterima antrean**, bukan berhasil di perangkat. Timeout setelah langkah router = `uncertain` → readback, bukan retry buta. `partial` = ringkasan parent; `stale` = label kesegaran; keduanya bukan state job.
- Tenant diambil dari membership terautentikasi, bukan parameter klien. Resource tenant lain = 404 generik. Error pakai 13 kode kanonik (`docs/source/Technical_Design_RTRWNet_v2_1.md` §5); `message` dilokalkan.
- Aksi finansial/akun RADIUS/cutover wajib `Idempotency-Key`; mutasi router lewat job (outbox → dispatcher), tidak dari handler HTTP. Perubahan akun RADIUS dan keputusan bisnis dalam satu transaksi database.
- Password layanan tampil sekali; tampil ulang hanya dengan permission + reautentikasi + audit + auto-sembunyi 30 detik.
- Temuan konflik/ambiguitas baru: catat `X-nn` di `docs/decisions.md` (Bagian Temuan implementasi) dengan default aman reversible; lanjutkan pekerjaan yang tidak bergantung. Jangan menebak.
- Verifikasi API/dependency dari dokumentasi resmi; pin versi dan catat tanggal pemeriksaan di `docs/compatibility.md`. Review lisensi dependensi (GPL/AGPL) sebelum diintegrasikan.
- Akhiri setiap sesi dengan checkpoint (format di `tugas.md` §13) pada `docs/progress.md`.

## Perintah standar (kontrak antarmuka; belum menjadi hasil uji sampai TK-002 diwujudkan)

- Bootstrap: `make bootstrap`
- Lint/typecheck: `make lint` · `make typecheck`
- Test unit/integrasi/kontrak: `make test` · `make test-integration` · `make test-contract`
- RADIUS dan i18n: `make test-radius` · `make i18n-check`
- E2E: `make e2e`
- Build: `make build`

Sebelum TK-002 selesai, target di atas adalah kontrak antarmuka, bukan perintah yang sudah ada; jangan mengklaim lulus lint/test sebelum target tersebut benar-benar berjalan.


## Kontrak build 2.1-build.1

Mulai dari `agent/START_BUILD.md` pada paket (target `docs/contracts/START_BUILD.md`), task terpilih di `agent/task-contracts_v2_1.json` (target `docs/contracts/task-contracts_v2_1.json`) serta master §24 EXE-01–08. Registry melengkapi 85 task; tidak menghapus task yang belum dapat dieksekusi. Profil dan daftar assertion applicable dibekukan sebelum run. Sumber ASVS5.0.0 dan253 requirement L1/L2 dipin; SEC-DEC-01 belum memberi izin mengubah MFA tenant. Pekerjaan independen dapat berlanjut. Pembaruan source normatif harus menjadi revisi paket baru dan mengulang seal; jangan mengedit file tersegel.
