# TUGAS — Implementasi Platform SaaS Manajemen RT/RW Net

[REVISI MACRO 2.1-macro.1] Dependency TK existing dipertahankan. TK-001 menerapkan MAC-02; TK-003/107 MAC-08; TK-306/307 MAC-05; TK-701–705 MAC-03; TK-1006 MAC-04. Minimum gate, pilot scope dan blocker mengikuti kontrol final. Salinan decisions dibuat hanya jika belum ada, tanpa overwrite. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


Versi 1.5 · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.3 (11 Oktober 2026) → 1.4 (28 Oktober 2026; duplikasi lintas dokumen diganti rujukan ke sumber kebenaran — putusan DOC pada `decisions_log.md` Bagian E) → 1.5 (28 Oktober 2026; menambah prasyarat kualitas dan lab: rujukan `sumber/quality/` (di repo: `docs/quality/`), gerbang desain QG-QA, skema bukti uji, urutan lab awal yang aman — tanpa mengubah definisi TK-xxx, urutan P0–P10, maupun pemetaan T01–T24).
Target pelaksana: AI coding agent (Codex, Claude Code, Antigravity).
Status: instruksi pembangunan dan pengujian; **bukan** bukti aplikasi selesai atau siap produksi.

Dokumen ini diselaraskan dengan amendemen v2.1 terhadap dengan `PRD_SaaS_RTRWNet_v2_1.md`, `Technical_Design_RTRWNet_v2_1.md`, `UIUX_Design_RTRWNet_v2_1.md` dan dokumen normatif pendamping: `Spesifikasi_RADIUS_dan_Migrasi_v2_1.md`, `Playbook_RouterOS_v2_1.md`, `Spesifikasi_ACS_TR069_v2_1.md`, `Panduan_Akuntansi_ISP_v2_1.md`, `Spesifikasi_i18n_v2_1.md`. Seluruh keputusan tercatat di `decisions_log.md`; pilihan desain audit telah ditetapkan; input lingkungan dan sign-off runtime yang diperlukan belum tersedia. Yang tersisa adalah gerbang pembuktian (lab, uji, otorisasi rilis).

## 1. Mandat utama

Bertindak sebagai lead engineer full-stack yang memahami database transaksional, keamanan multi-tenant, RouterOS, RADIUS (AAA), TR-069, akuntansi, dan operasi RT/RW Net di Indonesia. Bangun solusi end-to-end yang nyata: kode, migrasi, UI multi bahasa (default Indonesia), adapter, pengujian, dokumentasi, konfigurasi deployment — bukan rencana atau dashboard dummy. Kerjakan bertahap dengan hasil yang dapat dijalankan dan diverifikasi. Prioritaskan adopsi akun existing ke basis RADIUS perusahaan dan kemudahan manajemen pelanggan. Jangan mengorbankan integritas pembayaran, isolasi tenant, atau keselamatan jaringan demi kecepatan.

Tugas ini mengizinkan pembangunan dan pengujian pada workspace serta lingkungan development/lab yang **telah diotorisasi**. Tugas ini sendiri tidak mengizinkan: perubahan router pelanggan, deployment produksi, publikasi rekening, pengiriman pesan kepada pelanggan, atau pemakaian kredensial produksi. Siapkan perubahan dan bukti uji; tindakan produksi hanya dalam scope otorisasi yang benar-benar diberikan.

## 2. Sumber kebenaran dan persiapan

Letakkan di repository: `AGENTS.md` (dari `agent/AGENTS_v2_1.md`) dan `tugas.md` (dari `agent/tugas_v2_1.md`) di root; berkas normatif sumber di docs/source, quality di docs/quality, audit di docs/audit; sumber hanya direvisi melalui mandat/ADR yang berlaku: `PRD_SaaS_RTRWNet_v2_1.md`, `Technical_Design_RTRWNet_v2_1.md`, `UIUX_Design_RTRWNet_v2_1.md`, `Spesifikasi_RADIUS_dan_Migrasi_v2_1.md`, `Playbook_RouterOS_v2_1.md`, `Spesifikasi_ACS_TR069_v2_1.md`, `Panduan_Akuntansi_ISP_v2_1.md`, `Spesifikasi_i18n_v2_1.md`, `decisions_log.md`, `source-manifest_v2_1.md` (v1_4/v2_0 provenance). [REVISI AUD-06] Legacy bootstrap_docs.sh tidak boleh dieksekusi; kontrak penempatan pengganti memetakan `sumber/quality/` → `docs/quality/` dan `sumber/audit/` → `docs/audit/`, lalu memverifikasi seluruh path/ukuran/hash terhadap source-manifest_v2_1.md sebelum penempatan.

Hitung SHA-256 dengan `sha256sum` dan bandingkan dengan `source-manifest_v2_1.md` (paket aktif; v2_0 provenance); `source-manifest_v1_4.md` dipertahankan sebagai provenance paket sumber. Bila berbeda, catat perbedaannya dan telaah ulang sebelum melanjutkan. Seluruh dokumen berformat Markdown; sketsa ASCII pada UI/UX adalah spesifikasi tata letak.

Urutan kewenangan dokumen didefinisikan pada **AGENTS.md** (sumber kebenaran). Teks normatif dan acceptance criteria mengalahkan sketsa. Angka default pada ED (timeout, retry, TTL, polling, batas berkas) adalah parameter terkonfigurasi (registri TD §16), bukan SLA.

Jika dokumen sumber tidak tersedia, cari hanya di workspace/lampiran; laporkan yang hilang, jangan mengaku telah membaca. Boleh menyiapkan fondasi reversible, tandai `source_review_pending`.

**Jika menemukan konflik atau celah baru:** jangan menebak dan jangan mengubah parameter terkunci. Tambahkan entri `X-nn` pada bagian "Temuan implementasi" di `docs/decisions.md` (log temuan kerja yang merujuk `docs/source/decisions_log.md`, bukan otoritas pengganti) berisi temuan, dampak, usulan, dan default aman reversible; lanjutkan pekerjaan yang tidak bergantung. Parameter terkunci hanya berubah lewat instruksi eksplisit pemilik + ADR.

## 3. Cara bekerja dan melanjutkan sesi

1. Periksa repository, `AGENTS.md`, branch, perubahan pengguna, runtime/tools. Jangan menghapus perubahan pengguna, force-push, atau rewrite tanpa alasan disetujui.
2. Repo kosong → buat struktur baseline. Sudah ada implementasi → gap analysis dan pertahankan yang memenuhi kontrak.
3. Buat backlog ber-ID dengan dependency, rujukan sumber, acceptance, bukti. Pecah menjadi vertical slice: schema → service → API → UI → test → dokumentasi.
4. Ambil task siap dikerjakan berdasarkan dependency; implementasikan, jalankan tes relevan, perbaiki, catat hasil. Jangan minta izin berulang untuk pilihan teknis rutin yang reversible.
5. Empat status (jangan dicampur): `implemented` = kode, migrasi, tes unit/integrasi ada; `verified_local` = lulus pada PostgreSQL nyata + simulator di workspace dengan evidence; `verified_lab` = lulus pada RouterOS nyata/CHR/CPE lab terotorisasi dengan versi tercatat (mock tidak pernah cukup); `release_enabled` = flag rilis menyala setelah gerbang fase lulus dan pemilik memberi otorisasi. Hanya `release_enabled` yang tampil di menu harian.
6. Lab/kredensial/otorisasi belum tersedia → tandai `blocked` dengan alasan spesifik; bangun simulator dan kontrak berlabel; lanjutkan task independen; fitur produksi terkait tetap mati.
7. Jangan menghapus tes, menurunkan assertion, menonaktifkan TLS/RLS/CSRF, atau mengubah requirement supaya build lulus.
8. Sebelum sesi berakhir perbarui checkpoint; sesi berikutnya baca checkpoint dan `git diff` dulu.
9. Verifikasi detail API/dependency dari dokumentasi resmi versi terpilih; pin versi/lockfile/digest dengan tanggal pemeriksaan; jangan `latest` tanpa evaluasi.
10. Laporkan faktual: kode berubah, command uji dan hasil, yang belum diuji, blocker, task berikutnya. Jangan menulis "production-ready" tanpa semua gerbang terkait lulus.
11. Pakai ID kebutuhan asli (IMP-03, ACT-02, ED21, U07, C/D/N) pada commit, backlog, tes, evidence. Jangan menciptakan ID baru untuk requirement yang sudah punya ID.

**Berkas progres wajib:** `docs/backlog.md`, `docs/progress.md`, `docs/decisions.md` (+ `docs/adr/`), `docs/traceability.md`, `docs/compatibility.md`, `docs/release-readiness.md`, `docs/contracts/enums.md`, `docs/contracts/state-machines.md`.

## 4. Invariant produk yang tidak boleh berubah

- SaaS terpusat pada VM Debian pemilik dengan IP publik; target ~1.000 perusahaan (belum dibuktikan pada satu VM). Solusi end-to-end untuk pengusaha RT/RW Net Indonesia; **antarmuka multi bahasa, default Indonesia (`id`), wajib `en`**.
- Tenant = perusahaan; user punya membership (bisa banyak tenant). Router dimiliki satu tenant; satu controller penulis aktif.
- **Basis pengguna PPPoE/Hotspot terkelola = RADIUS per tenant**, dibagi seluruh router tenant. Identitas pelanggan independen dari router: pindah router atau ganti perangkat tidak memerlukan input ulang. Username unik per tenant (case-sensitive).
- Sumber kebenaran akun adalah `access_account` pada database aplikasi; `radius.*` adalah proyeksi yang ditulis hanya oleh service layer dalam transaksi yang sama.
- Tidak ada port Ethernet manajemen khusus. VPN = jalur manajemen dan RADIUS, bukan transit internet pelanggan; tidak ada route seluruh LAN tenant atau default route via server; **tidak ada `0.0.0.0/0` sebagai allowed route manajemen**.
- Uplink/failover/PCC terpisah dari manajemen pelanggan.
- Discovery, adopsi, dan commit migrasi **hanya membaca router dan menulis database**. Menulis konfigurasi RADIUS ke router terjadi hanya pada cutover per router (eksplisit, ber-backup, ber-canary, dapat di-rollback). Tidak reset, reboot, ganti profile, atau membuat ulang akun.
- Penegakan isolir/kecepatan/pool melalui atribut RADIUS dan Disconnect/CoA; dijamin hanya pada router `radius_authoritative`.
- Pembayaran SaaS (platform) terpisah dari pembayaran internet (tenant): buku, permission, namespace nomor, rekening.
- Isolir otomatis setelah policy tenant diaktifkan (default off); pembukaan setelah bayar manual (Owner/Admin Pembayaran).
- Invoice lunas, kelayakan, isolir, koneksi, job = dimensi berbeda (ED21). Router offline atau RADIUS terputus tidak membatalkan pembayaran sah.
- Tidak ada isolir pelanggan internet karena tunggakan SaaS tenant; autentikasi RADIUS tetap dilayani selama masa ended sampai penarikan terjadwal.
- Akun hasil migrasi `automation_enabled=false` sampai data lengkap, simulasi ditinjau, policy diaktifkan eksplisit.
- Backup rutin disimpan di server: maks. 100 generasi berhasil per router; gagal transfer tidak menghapus backup valid. Data RADIUS ikut recovery platform.
- Super Admin melihat kesehatan platform dan agregat tenant; bukan data pelanggan, ledger, akun RADIUS, atau rahasia tanpa SupportGrant sah.
- Tidak menjanjikan nol downtime, semua ONT kompatibel, infrastruktur unlimited, atau exactly-once lintas DB-router.
- Identitas objek router = tenant + router + tipe objek + referensi terverifikasi; `.id` hanya handle lokal.
- Collector gagal/data hilang = gap/unknown/stale, bukan nol dan bukan router mati. Status koneksi layanan dari accounting RADIUS.
- "RT RW Net" nama kerja; brand/domain/logo/kontak dari konfigurasi `BRAND_*`.
- Tidak ada pesan nyata (email/WhatsApp/SMS) ke siapa pun selain email transaksional akun SaaS; development memakai penangkap lokal (Mailpit).
- Platform tidak pernah mengubah FastTrack/firewall pelanggan pada R1–R3; hanya mendeteksi dan melaporkan.
- Dilarang `verify=false` pada TLS router; sertifikat API dipin. Secret RADIUS unik per router; `Message-Authenticator` wajib.
- Teks tampil kepada manusia tidak di-hardcode; kode mesin (enum, error, atribut RADIUS) tidak diterjemahkan.

## 5. Paket, harga, kuota, dan pembayaran platform

Harga paket, batas router/layanan/anggota tim (termasuk plafon fair use Platinum), dan seed rekening/nomor konfirmasi pembayaran adalah data produk pada **PRD §3–§4** (sumber kebenaran; seed editable, bukan hardcode frontend). Jangan menggandakan nilai tersebut di kode atau dokumen lain; implementasikan persis dan uji.

Kedua batas (router dan layanan) berlaku bersamaan. Aturan hitung kuota, draft cap (`max(10, ceil(25% × limit))`, maks. 500), reservasi atomik (TTL 60 menit; `pending` tidak kedaluwarsa), pelepasan/penggantian router (tumpang tindih 30 hari), upgrade (tanpa prorata, hari bonus), downgrade (saat renewal, ditolak bila melebihi batas), refund (hanya kesalahan), dan siklus SaaS (grace 7 hari, restricted sampai hari ke-30, ended; VPN 60 hari; data 180 hari) — **rinci pada PRD §3 dan TD §4/§9/§16**; implementasikan persis dan uji.

**Anniversary (terkunci):** periode tanggal kalender `[start, end)`; jangkar tidak bergeser; `clamp(A, bulan)`. Gunakan fungsi dan vektor uji pada TD §4 (31 Jan → 28/29 Feb → 31 Mar; tahunan; renewal aktif dari `end_date`; renewal sesudah expiry dari tanggal approval).

**Alur SaaS:** pilih paket/periode → quotation → invoice (kedaluwarsa 7 hari) → transfer → upload bukti (JPEG/PNG/PDF ≤5 MiB, scan, path opaque) → verifikasi dana oleh staf berizin → approval atomik (transaksi + outbox). Bukti ≠ dana diterima. Idempotency mencegah approval ganda memperpanjang dua kali. Partial payment tidak mengaktifkan entitlement; overpayment = kredit.

**Seed rekening** (8 tujuan atas nama Huda Choirul Anam, termasuk DANA/GoPay/OVO `082319199930`): daftar lengkap, aturan penyimpanan (`display_value` persis, `normalized_digits`, `published=false`, tidak tampil di landing), **nomor konfirmasi pembayaran `082319199930`** (tombol "Konfirmasi via WhatsApp" pada invoice/halaman pembayaran terautentikasi; landing mengikuti `BRAND_CONTACT`), serta aturan perubahan tujuan mengikuti **PRD §4** — sumber kebenaran; jangan menggandakan nilai tersebut.

## 6. Baseline arsitektur dan stack (terkunci)

Python 3.13 + Django 5.2 LTS + DRF + drf-spectacular + Gunicorn; React + TypeScript (Vite, pnpm, TanStack Query, FormatJS, Vitest, Playwright); PostgreSQL 17 native (skema aplikasi + `radius` + `ledger`); **FreeRADIUS 3.2 (≥ 3.2.5) dengan rlm_sql PostgreSQL**; antrean job + outbox di PostgreSQL (tanpa Celery/Redis); WireGuard + nftables host gateway; Prometheus internal; Caddy 2; ClamAV via antarmuka scanner; klien RouterOS native API(-SSL) internal; layanan render PDF; Compose (app) + systemd (gateway, FreeRADIUS) tanpa Docker socket; GenieACS + MongoDB terpisah pada R3. Patch/minor dipin pada TK-002 lewat ADR bertanggal. Jika repo memakai stack lain yang memenuhi kontrak, tulis ADR sebelum migrasi; jangan rewrite otomatis. **Struktur repository kanonik** (termasuk domain `access`/`i18n`, adapter `radius`, `tests/radius_lab`, dan `locales/`) ditetapkan pada **TD §1** — jangan menyimpang tanpa ADR.

Semua akses lintas domain via service layer. Backup: router → receiver terbatas (SFTP via VPN) → staging → verifikasi → storage durable; reverse proxy, VPN manager, receiver, FreeRADIUS, Prometheus, pipeline upload wajib ada. API, dispatcher, collector, receiver, VPN manager, FreeRADIUS = proses/credential terpisah; API tanpa root/CAP_NET_ADMIN/Docker socket; VPN manager hanya operasi typed; FreeRADIUS hanya lewat role DB `radius_ro`/`radius_acct`.

Sediakan dev bootstrap, `.env.example` tanpa secret, migrasi, seed sintetis, CI, lab RADIUS (FreeRADIUS + CHR). **Antarmuka perintah standar (Makefile):** `make bootstrap`, `make lint`, `make typecheck`, `make test`, `make test-integration`, `make test-contract`, `make test-radius`, `make i18n-check`, `make e2e`, `make build`; isi ditetapkan di TK-002 dan dicatat pada `AGENTS.md`. Produksi memakai server aplikasi produksi dan reverse proxy HTTPS; artefak dibangun di CI dan didistribusikan dengan digest.

## 7. Kontrak data, keamanan, dan API

- UUID internal; UTC `timestamptz`; tanggal akuntansi/periode `DATE` + timezone bisnis (default Asia/Jakarta, bahasa Indonesia).
- Uang `numeric(20,2)`, JSON string; bandwidth integer bit/s dengan label arah pelanggan benar.
- Tabel tenant: `tenant_id`, indeks tenant-first, FK komposit; unik untuk customer/service code, source event, periode billing, idempotency scope. RLS (ENABLE+FORCE) sebagai lapisan tambahan; runtime bukan owner/superuser/BYPASSRLS; migrator terpisah; fail closed; uji pool reuse.
- Membership/permission diperiksa di backend, worker, export, download, query metrik, gateway ACS. Job pengguna memeriksa ulang hak saat eksekusi. Permission granular (TD §3); tiga peran = bundel default; Akuntan, Viewer, Kolektor, dan Agen tersedia.
- Cookie HttpOnly/Secure/SameSite + CSRF; rate limit (5 gagal/15 menit); Argon2id; MFA TOTP + kode pemulihan; sesi idle tenant 8 jam/platform 30 menit; reauth 10 menit.
- Kredensial terenkripsi, kunci di luar DB; tidak di browser umum, log, analytics, fixture, exception, git. Password layanan: tampil sekali; reveal ulang butuh `services.reveal_credentials` + reauth + audit + auto-sembunyi 30 detik.
- Upload privat: validasi MIME (magic bytes)/ukuran, scan fail-closed, path opaque, non-executable, unduhan berizin (signed URL 5 menit). Export CSV menetralkan formula.
- SupportGrant: actor, tenant, scope, alasan, expiry, persetujuan Owner.

**API `/api/v1`:** OpenAPI sebagai kontrak; cursor stabil, limit 50/maks. 200; filter allowlist. **202 = diterima antrean.** Mutasi finansial/provisioning: `Idempotency-Key` + canonical body hash + scope (retensi 7 hari); key sama/body beda → 409 `idempotency_conflict`. Optimistic `expected_revision`. Error `{code, message, locale, request_id, field_errors, retryable}`; HTTP: 401, 403, 404 (resource tidak dimiliki), 409, 422, 429 + `Retry-After`, 503.

Kode error kanonik (13) beserta pemetaan HTTP-nya didefinisikan pada **TD §5** (sumber kebenaran). `unsupported` (UI) = `unsupported_capability`; `partial` = ringkasan parent bulk; `stale` = label kesegaran. Registry enum di `docs/contracts/enums.md`; `message` error dilokalkan sesuai `Accept-Language`, `code` tetap.

Endpoint kanonik: lihat TD §5 (daftar lengkap, termasuk `/migrations`, `/access-accounts`, `/routers/{id}/radius-cutover`, `/voucher-batches`, `/collections`, `/meta/enums`). Domain lain dilengkapi via OpenAPI berversi dengan pola sama.

## 8. Mesin pekerjaan (wajib sebelum connector mutasi)

Mesin pekerjaan mengikuti **TD §6** (status job, jenis job, kebijakan retry/`uncertain`, fairness, circuit breaker, dispatcher tunggal per router, `lease_epoch`) dan **PRD §23** (state machine seluruh objek). Materialisasi wajib: `docs/contracts/state-machines.md` dan `docs/contracts/enums.md` dengan uji transisi ilegal.

Domain change + audit redacted + OutboxEvent dalam satu transaksi; `on_commit` hanya wake-up; polling outbox wajib; claim `SKIP LOCKED` dengan transaksi pendek. Timeout sebelum write terbukti aman → retry bounded berjitter; write mungkin terkirim → `uncertain` + readback. Cancel hanya tahap belum jalan; policy berubah → `cancelled` (`policy_changed`). Collector/backup terpisah dari antrean pembayaran/pemulihan. Sebelum connector mutasi router dipakai, mesin pekerjaan lulus uji crash dan stale writer (TK-103, T06).

---
## 9. Backlog eksekusi bertahap

ID TK adalah ID task; ID PRD/ED/U/T merujuk dokumen sumber. Gerbang memakai G0–G5 (PRD §26).

### P0 — Audit dan fondasi

- [ ] TK-001 Baca sumber, verifikasi hash terhadap manifest, gap analysis, traceability (seed Lampiran A), buat `docs/decisions.md` hanya bila belum ada, sebagai log X-nn dengan rujukan ke `docs/source/decisions_log.md`; jangan menimpa keputusan existing.
- [ ] TK-002 ADR stack (pin patch/minor), toolchain (Makefile §6), dependency manifest, **review lisensi (GPL/AGPL; FreeRADIUS GPLv2 berjalan sebagai proses terpisah)** di `docs/compatibility.md`, ClamAV (stub dev), Mailpit, layout repository, dev bootstrap, CI, lab RADIUS.
- [ ] TK-003 Schema domain, API, permission (TD §3), enum, feature/capability flag, threat model; model status terpisah ED21; desired/observed/provenance; registry enum + state machine; **ledger tiga lapis sebagai ADR + prototipe dengan tes bypass**; registri konfigurasi.
- [ ] TK-004 Simulator RouterOS deterministik + failure injection + rencana lab nyata/CHR; fixture RADIUS (radclient).
- [ ] TK-107 Registri konfigurasi dan release flag (seluruh kunci TD §16, `BRAND_*`, `contact_confirmation`); landing publik menolak rilis bila `BRAND_*` kosong.

Lulus P0: repo dapat dibootstrap dari dokumentasi; CI berjalan; kontrak dan dependency tersedia. (G0)

### P1 — Identitas, tenant, i18n, job, kerangka UI (R1) — dependency P0

- [ ] TK-101 User, tenant, membership, peran bawaan + Akuntan + Viewer + Kolektor + Agen, scope router, proteksi Owner terakhir; peran platform; MFA TOTP + kode pemulihan, reauth 10 menit, kebijakan sesi, rate limit login, email transaksional.
- [ ] TK-102 RLS/constraint, audit redaction, secret boundary, SupportGrant, suite negatif tenant.
- [ ] TK-103 Outbox/job/attempt/lease/reconciliation dan U16; tes crash dan stale writer.
- [ ] TK-104 U01 (rangka), U02, U03 (kartu modul yang ada; R2 disembunyikan), U18, AppShell (sidebar 5 kelompok; header admin navy), tenant switcher, navigasi per permission, komponen status.
- [ ] TK-105 Seed PlanVersion/kuota; reservasi atomik, release/reconcile, renewal, usage projection; draft cap; plafon Platinum; aturan hitung.
- [ ] TK-106 Storage adapter privat + pipeline upload (MIME, ukuran, scan fail-closed, path opaque, signed URL 5 menit).
- [ ] TK-108 **Framework i18n**: katalog `id`/`en` (FormatJS + gettext), kunci stabil, ekstraksi CI, uji paritas, pseudo-locale, `Accept-Language`, `GET /meta/enums`, pemilih bahasa, bahasa tenant/pengguna/pelanggan, format IDR/tanggal/zona WIB-WITA-WIT, fallback ke `id` (I18N-01–10).
- [ ] TK-109 Render PDF invoice/kwitansi/laporan; snapshot issued bahasa, timezone, template version, nilai dan artifact/hash final sesuai AUD-38; reprint konsisten.

Lulus P1: dua tenant terisolasi pada API/DB/UI/job/storage; retry event tidak menggandakan logical job; seluruh layar P1 dirender id/en/pseudo-locale tanpa teks tertanam.

### P2 — Subscription platform dan approval (R1) — dependency P1

- [ ] TK-201 Quotation/invoice/upload/verification/approval + entitlement transaksi+outbox; U14 dan subscription U18; upgrade (hari bonus), downgrade.
- [ ] TK-202 Peran platform terpisah; approve/reject/revision dengan audit.
- [ ] TK-203 Partial, selisih lebih (kredit), duplikat (peringatan), invoice expired, refund/koreksi, retry approval.
- [ ] TK-204 Harga di U01; PaymentDestination editable (seed §5), `published=false`; kontak konfirmasi 082319199930; fair use Platinum pada landing.
- [ ] TK-205 Mesin status SaaS (grace 7, restricted ≤ 30, ended; VPN/RADIUS 60 hari dengan notifikasi 7/3/1; data 180 hari) dengan job harian; **autentikasi RADIUS tenant tetap dilayani saat ended**; tanpa isolir internet.

Lulus P2: approval konkuren hanya satu entitlement; expiry SaaS tidak berdampak ke internet pelanggan. (T05 sisi SaaS)

### P3 — VPN, adapter baca, dan RADIUS dasar (R1) — dependency P1; klaim kompatibilitas butuh G1

- [ ] TK-301 Registry peer/alamat unik, token hashed sekali pakai (TTL 15 menit), expiry/revoke/rotation, VPN manager typed, nftables default-deny termasuk RADIUS 1812/1813 dan 3799.
- [ ] TK-302 Bootstrap bernamespace idempoten (Playbook §2–§5): preview, validasi enrollment, private key di router, kredensial dibangkitkan di router, mode `read_only`/`manage`, sertifikat api-ssl, pemeriksaan overlap; **tidak menyentuh `/radius`, `/ppp aaa`, profil Hotspot**.
- [ ] TK-303 Health tunnel/API/auth/permission/TLS/capability terpisah; U05/U06.
- [ ] TK-304 Klien native API-SSL internal dengan pin sidik jari; REST alternatif (flag mati); custom group dari lab; egress gateway SSRF.
- [ ] TK-305 Uji NAT/CGNAT, UDP tertutup, reload firewall, IPv6, LAN sama antar-tenant, replay/expiry, reboot, v6 unsupported, isolasi peer.
- [ ] TK-306 FreeRADIUS multi-tenant melalui facade EXECUTE-only AUD-20/MAC-05; projection-writer scoped tenant dalam transaksi bisnis; Message-Authenticator, bind tunnel, client revision/reload terverifikasi. Dua proses adalah process redundancy, bukan host HA; klaim HA menunggu failure domain independen/G4 (AUD-21).
- [ ] TK-307 Lifecycle klien NAS (`radius.nas`) bersama enrollment/revoke/replace; rotasi secret; uji isolasi tenant (T19) dan atribut (T16) dengan radclient.

Lulus P3: T01/T10/T16/T19 di lab; bootstrap tidak mengubah default route/bridge/akun; RADIUS menjawab hanya klien terdaftar.

### P4 — Discovery, migrasi RADIUS, CSV, layanan (R1) — dependency P1 + kontrak P3

- [ ] TK-401 Discovery PPP/Hotspot/pools/interface/queue/firewall(FastTrack)/RADIUS/`ppp aaa`; bounded reads; tanpa password.
- [ ] TK-402 Snapshot/fingerprint/mapping; filter `service` (pppoe/any dimigrasi; lainnya `unmanaged`); `service=any` direview; RADIUS eksternal → jalur S4.
- [ ] TK-403 **Wizard adopsi/migrasi U07 8 langkah** (database-only), progres per tenant, revalidasi snapshot, peringatan FastTrack.
- [ ] TK-404 U08 CSV: template berversi, mode (termasuk password migrasi), streaming validation, preview, chunk commit idempoten; batas 10 MiB/10.000 baris (plafon 20/20.000 setelah uji beban).
- [ ] TK-405 U04 CRUD/pencarian/filter; pilihan akhir yang menyatakan efek ke router; password dibangkitkan, tampil sekali, reveal berizin (reauth, audit, 30 dtk); rotasi aksi terpisah; tab Akses.
- [ ] TK-406 Drift (scan 6 jam + on-demand + preflight): `missing_source`, `needs_review`, `hold_unknown`, `local_account_shadow`, `binding_invalid`, `radius_client_missing`.
- [ ] TK-407 Rename router; export berizin; archive/termination; offboarding (export akun RADIUS terenkripsi); **pelepasan dan penggantian router** (akun tidak dipetakan ulang; 30 hari tumpang tindih).
- [ ] TK-408 TechnicalProfile/CommercialPackage(kecepatan, FUP, `first_period_policy`)/PackageRouterBinding(pool); hash profil.
- [ ] TK-409 Analisis dampak edit profil router (baca saja); blok edit langsung bila unmanaged terdampak.
- [ ] TK-410 **Mesin penggabungan identitas lintas router**: kandidat gabung/konflik/peringatan; keputusan `merge/keep_one/rename`; uji dengan fixture dua router.
- [ ] TK-411 **Sumber password S1–S4**: akun migrasi sementara (≤ 24 jam, penghapus otomatis, batas laju, verifikasi hilang), CSV, password baru, impor RADIUS eksternal; `password_unknown` tidak diproyeksikan.
- [ ] TK-412 U19 bagian Akun (daftar, reveal, tangguhkan, MAC lock, batas sesi) dan status per router.

Lulus P4: T02–T04, T18 (data); impor ulang tanpa duplikat dan tanpa write router; reservasi kuota konkuren aman; username sama pada dua router diselesaikan lewat wizard; password tidak bocor di log.

### P5 — Cutover RADIUS, akun, monitoring, backup (R1) — dependency P3/P4 + job engine

- [ ] TK-501 Pembuatan/ubah akun akses idempoten (DB + proyeksi) dan job atribut (CoA/Disconnect); `uncertain` tidak diulang buta; "Buat akun"/"Buat dan aktifkan".
- [ ] TK-509 **Cutover engine B0–B6** (RAD-10): preflight+backup, paritas server-side, pasang klien (Playbook §6), canary, aktif penuh, otoritatif per batch, rollback; `enforcement_mode`; metode B5 sesuai lab; U19 bagian Cutover. Hanya mode `manage` dan `radius.cutover`.
- [ ] TK-510 Ingest accounting (`radacct` dipartisi), `connection_state`, janitor sesi basi, `usage_daily`, retensi; `Simultaneous-Use` lintas router.
- [ ] TK-511 Monitoring RADIUS (rasio auth, latensi, antrean, klien hilang), insiden, runbook rollback; dua alamat RADIUS pada router.
- [ ] TK-502 Monitoring U13: collector bounded, timestamps, stale (>3× interval)/unknown/gap, counter reset/wrap, circuit breaker, insiden dedup, status router, insiden platform saat collector gagal.
- [ ] TK-503 Prometheus internal; query template; tanpa label username/telepon/invoice; retensi 15/90/400 hari.
- [ ] TK-504 U12 jadwal backup per router/timezone; password binary dibangkitkan platform; kategori routine/manual/prechange; backup pre-change otomatis sebelum cutover.
- [ ] TK-505 **Spike transfer**: SFTP push via VPN (primer), pull dengan host key dipin (cadangan); ukuran 64 MiB; receiver tanpa shell.
- [ ] TK-506 Staging → verifikasi → enkripsi + durable → commit → retensi transaksional → prune async; orphan recovery; watermark; headroom.
- [ ] TK-507 Unduh berizin + audit; kunci pemulihan (reauth+MFA); manual/prechange; restore hanya lewat runbook lab.
- [ ] TK-508 **R4/P9**: edit/clone profil fisik router melalui ChangePlan; dependency kontrak P9, capability G1 dan recovery teruji. P5 hanya discovery profil dan uji FastTrack/queue di lab; tidak membuka mutasi profil produk R1 (AUD-38, PRO-02).

Lulus P5/R1: T06/T08/T09/T10/T17/T18/T21 relevan; generasi 101 → 100 katalog valid; demo E2E R1 memakai backend nyata; cutover + rollback teruji di lab. (G1, G2)

### P6 — Billing internet, auto-isolir, aktivasi, kolektor (R2) — dependency R1

- [ ] TK-601 Invoice/periode/due date/payment/allocation/partial/overpayment/aging; `fixed_monthly`/`anniversary`, `prepaid`/`postpaid`, `first_period_policy`; scheduler unik; snapshot harga; dokumen per bahasa; promo/add-on (BIL-07).
- [ ] TK-602 Scheduler isolir (harian 01:00 zona tenant) hanya kandidat berversi; worker baca ulang payment/policy/hold/revision; simulasi (ID 24 jam) wajib; policy default off; grace 3 hari.
- [ ] TK-603 Isolir/aktivasi via RADIUS (RAD-06, ED22, AUD-24–25): suspend memproyeksikan Reject, restore memproyeksikan Accept sesuai hold/binding; Disconnect terpisah dan verifikasi sesuai arah. Isolir terbatas opsional R3; hanya enforcement authoritative yang terbukti.
- [ ] TK-604 U09/U10: filter periode; aktivasi manual; snapshot; validasi per item; retry item aman.
- [ ] TK-605 Restore atribut hanya milik aplikasi yang cocok; hold mengalahkan pembayaran; override izin+alasan.
- [ ] TK-606 Uji bayar sebelum/sesudah enqueue, saat eksekusi, router offline, aktivasi ganda; policy berubah → `cancelled`.
- [ ] TK-607 Migrasi saldo: opening balance cutover; review paid-through/tunggakan; tanpa double count.
- [ ] TK-608 Dokumen koreksi: refund, diskon, write-off, pembatalan, deposit.
- [ ] TK-609 **Kolektor**: bundel/portal terbatas, penerimaan tunai bernomor, saldo "belum disetor", setoran, selisih, laporan; pengingat penagihan (BIL-06).

Lulus P6: T05/T20; payment tercatat saat router/RADIUS gagal; job lama dibatalkan bila belum berjalan; terlanjur isolir → `paid-awaiting-activation`.

### P7 — Akuntansi (R2) — dependency P6

- [ ] TK-701 COA default (Panduan §2), opening balance, FrameworkVersion, journal/line, posting rules, period lock; ledger tiga lapis dengan tes bypass; buku platform.
- [ ] TK-702 Posted immutable; reversal/adjustment; source-event dedup; closed-period; rounding; sisa pengakuan ke periode terakhir.
- [ ] TK-703 Piutang, kas/bank/e-wallet, pendapatan diterima di muka + recognition, utang/beban, persediaan, aset/penyusutan, **kolektor, cadangan piutang, payment fee, `TaxRule`**.
- [ ] TK-704 Statement import dedup, split/merge match, tie-out subledger/control.
- [ ] TK-705 U11: jurnal, buku besar, neraca saldo, laba-rugi, posisi keuangan, arus kas, aging, penerimaan harian, saldo kolektor, pendapatan per paket/router/area; basis/periode/drill-down; "Belum final".

Lulus P7: T12; laporan reconcile; **review akuntan atas posting rules (G2)**.

### P8 — Voucher, agen, ACS, operasional (R3)

- [ ] TK-801 GenieACS terpisah, NBI internal, enrollment CPE (kredensial per-device).
- [ ] TK-802 Capability per model/firmware; task lifecycle; karantina; matriks dari lab; virtual parameter TR-098/181.
- [ ] TK-803 U15 Wi-Fi/config/optical hanya yang didukung; reboot/firmware dengan review; **rotasi password PPPoE terkoordinasi ACS↔RADIUS**.
- [ ] TK-804 Tiket/insiden/work order, inventaris (biaya ke akuntansi), assignment history, ODP, alokasi port atomik.
- [ ] TK-805 Portal pelanggan (berbahasa pilihan) dan portal agen/kolektor berscope.
- [ ] TK-806 Notifikasi (default off; email SMTP tenant + adapter provider; templat per bahasa; dedup, rate limit).
- [ ] TK-807 **Voucher Hotspot**: batch, reservasi kuota atomik, atribut RADIUS, cetak/ekspor, cabut/perpanjang, kedaluwarsa.
- [ ] TK-808 **Agen/reseller**: stok, penjualan, komisi, setoran, jurnal.
- [ ] TK-809 **FUP/kuota data** berbasis accounting + aksi (turunkan kecepatan/isolir) dan CoA/Disconnect.
- [ ] TK-810 **Prospek, survei, instalasi, work order** dan siklus pelanggan (LIF-01–04).
- [ ] TK-811 **RADIUS edge replica** (sinkron tarikan bertanda tangan, antrean accounting).

Lulus P8: T11/T10/T22/T24; queued ≠ sukses; konflik identitas tidak membocorkan kredensial; model tak teruji = unsupported.

### P9 — Wizard jaringan pelanggan dan uplink (R4)

- [ ] TK-901 U17 dua pintu; static IP/prefix/gateway; DHCP lease.
- [ ] TK-902 ChangePlan immutable (snapshot, template, ownership, diff, impact, expiry, backup, recovery).
- [ ] TK-903 Single, failover recursive (≥2 target; hysteresis 3/5), weighted PCC hanya topologi teruji; PCC diblokir bila ada Hotspot server; probe lewat ISP benar; rute VPN/RADIUS tetap valid saat failover.
- [ ] TK-904 Local/VPN/DNAT/return path/FastTrack (pengecualian objek templat)/queue/IPv6; templat PPPoE/Hotspot server, pool, profil (Playbook §7) untuk router pengganti.
- [ ] TK-905 Apply bertahap + checkpoint/readback; `uncertain/recovery_required`; recovery hook bila lulus lab.
- [ ] TK-906 Adapter OLT terpilih setelah matriks model/protokol disahkan (ACS-07).

Lulus P9: T13 per fixture; tidak apply bila mengancam satu-satunya jalur kontrol/RADIUS tanpa recovery teruji.

### P10 — Operasional dan skala (bertahap sepanjang fase)

- [ ] TK-1001 Formulir inventory VM/hypervisor/vCPU/RAM/IOPS/uplink/IP-NAT/DNS/UDP/UPS/off-host.
- [ ] TK-1002 Deployment reproducible (Compose+systemd), secret injection, health check, resource limit, rotasi log, sertifikat, expand/contract, worker drain.
- [ ] TK-1003 Observability (queue age, uncertain, API/DB lock, disk/staging, backup lag, collector lag, auth failure RADIUS).
- [ ] TK-1004 Off-host DB/WAL/artifact/key/VPN/ACS/RADIUS config backup; drill restore; tahan mutasi sampai rekonsiliasi; RADIUS dipulihkan lebih dulu.
- [ ] TK-1005 Benchmark 10 → 100 → 1.000 tenant (router/service/CPE/RADIUS auth+acct), soak, reconnect storm, fairness; HA RADIUS; tentukan spesifikasi VM dari hasil.
- [ ] TK-1006 Runbook incident, rotasi kredensial/secret RADIUS, kunci hilang, job macet, support access, offboarding router, rollback cutover, restore, insiden kebocoran data (PDP-04).

Target (bukan hasil): p95 list/enqueue ≤2 dtk; aktivasi sehat ≤60 dtk; p95 autentikasi RADIUS ≤100 ms; RPO ≤15 menit; RTO ≤4 jam; SLA tidak ditawarkan sebelum G5. Satu VM = SPOF.

## 10. Ketentuan UI/UX lintas fase

Implementasikan U01–U20 sesuai UI/UX v1.3 (antarmuka multi bahasa). Komponen: AppShell, TenantSwitcher, PageHeader, FilterBar, DataTable, MobileServiceCard, StatusBadge, FreshnessLabel, JobProgress, BulkActionBar, ConfirmAction, FieldError, PermissionNotice, EmptyState, MetricCard, ChartWithTable, AuditTimeline. Sidebar 5 kelompok (13 menu PRD terpetakan); header tenant terang, header `/admin` navy `#0F2A4A`. Token: background `#F4F6F8`, surface putih, text `#172B4D`, secondary `#475569`, primary `#1D4ED8`, success `#166534/#DCFCE7`, warning `#92400E/#FEF3C7`, danger `#B91C1C/#FEE2E2`, border `#CBD5E1`; body 16, label 14, tabel ≥14, radius 8, spacing 4/8/12/16/24/32; breakpoint ≥1200/768–1199/<768; target sentuh 44 px; WCAG 2.2 AA; ukur kontras pada implementasi. Copy status mengikuti tabel UI/UX §12 (tidak mengubah arti enum).

Setiap layar: loading/empty/error/forbidden/unsupported/stale/partial bila relevan; unknown ≠ nol; warna disertai teks; tenant dan filter terlihat; chart punya tabel. Billing/isolir/koneksi/job terpisah. Bulk memakai snapshot. Offline blokir mutasi baru. 202/toast ≠ hasil router. Fitur belum lulus flag/capability disembunyikan; backend tetap menolak. Data demo tidak bercampur produksi. Analytics hanya event allowlist (`import_started`, `import_committed`, `cutover_started`, `cutover_completed`, `activation_reviewed`, `activation_result_viewed`, `onboarding_step_completed`, `language_changed`) dengan `safe_error_code`.

| Layar | Fase | Task |
|---|---|---|
| U01 | R1 | TK-104, TK-204 |
| U02 | R1 | TK-101, TK-104 |
| U03 | R1 bertahap | TK-104; kartu R2 di TK-601/604 |
| U04 | R1 (kolom R2 menyusul) | TK-405; TK-601/604 |
| U05, U06 | R1 | TK-303, TK-407 |
| U07 | R1 | TK-403, TK-410, TK-411 |
| U08 | R1 | TK-404 |
| U09, U10 | R2 | TK-604 |
| U11 | R2 | TK-705 |
| U12 | R1 | TK-504, TK-507 |
| U13 | R1 bertahap | TK-502 |
| U14 | R1 | TK-201, TK-202, TK-204 |
| U15 | R3 | TK-803, TK-804 |
| U16 | R1 | TK-103 |
| U17 | R4 | TK-901 |
| U18 | R1 | TK-104, TK-201, TK-102, TK-205, TK-108 |
| U19 | R1 | TK-412, TK-509, TK-511 |
| U20 | R2–R3 | TK-609, TK-807, TK-808 |

## 11. Matriks pengujian wajib

Definisi dan kriteria lulus T01–T24 ada pada **PRD §26** (sumber kebenaran); rincian domain RADIUS pada `Spesifikasi_RADIUS_dan_Migrasi_v2_1.md` §13 dan ACS pada `Spesifikasi_ACS_TR069_v2_1.md` §12. Gerbang G0–G5 dan prasyarat aktivasi fitur: PRD §26.

**Prasyarat kualitas (berlaku lintas fase):**

- Rancang dan jalankan uji mengikuti `docs/quality/Test_Strategy_v2_1.md` (tingkat, lingkungan, batas `verified_local` vs `verified_lab`); ID turunan memakai pola `T<induk>-<AREA>-<nn>` atau `QA-<AREA>-xxx` **tanpa** menimpa makna T01–T24 pada PRD §26.
- Petakan cakupan per `docs/quality/Test_Coverage_Matrix_v2_1.md` (operasional; PRD §26 tetap SSOT); setiap uji wajib mencakup happy path + negative/boundary/security/concurrency/recovery bila relevan, dengan justifikasi `NOT APPLICABLE` bila tidak.
- Sebelum eksekusi lab jaringan apa pun (MODE B), penuhi `docs/quality/Lab_Onboarding_and_Access_v2_1.md` (inventaris host/GNS3, scope izin, approval checkpoint) dan topologi `docs/quality/GNS3_Lab_Architecture_v2_1.md` (Lab-0..Lab-4). Tanpa akses terotorisasi: `NOT RUN — ACCESS/APPROVAL NOT PROVIDED`.
- Simpan bukti sesuai skema `docs/quality/Test_Evidence_and_Reporting_v2_1.md` (run_id, versi/topologi, expected/observed, hash, redaksi). Uji keamanan mengikuti `docs/quality/Security_Test_Plan_v2_1.md`; beban/DR mengikuti `docs/quality/Performance_Reliability_DR_Plan_v2_1.md` (G4/G5).
- Kompatibilitas versi/image dicatat di `docs/compatibility.md` dan `docs/quality/Compatibility_and_Hardware_Matrix_v2_1.md`; tanpa `verified_lab`, tampil `unsupported`/fitur tetap mati.
- Kelulusan gerbang desain dokumen QG-QA-01..12 (`docs/quality/Quality_Gates_and_Release_Readiness_v2_1.md`) menilai kelengkapan desain uji, **bukan** pengganti G0–G5.

| Uji | Fase dan task utama |
|---|---|
| T01 | P3: TK-302, TK-305 |
| T02, T03 | P4: TK-401–403 |
| T04 | P4: TK-404 |
| T05 | P2: TK-201, TK-203; P6: TK-604, TK-606 |
| T06 | P1: TK-103 (fake adapter); P5: TK-501, TK-509 (nyata) |
| T07, T20 | P6: TK-603 |
| T08 | P5: TK-506 |
| T09 | P5: TK-507 |
| T10 | P1: TK-102; P3: TK-305; P5: TK-503, TK-507; P8: TK-801 |
| T11 | P8: TK-801, TK-802 |
| T12 | P7: TK-701–704 |
| T13 | P9: TK-903–905 |
| T14, T15 | P10: TK-1004, TK-1005 |
| T16, T19 | P3: TK-306, TK-307 |
| T17 | P5: TK-509 |
| T18 | P4: TK-410; P5: TK-509; P4: TK-407 |
| T21 | P5: TK-510 |
| T22 | P8: TK-811; P10: TK-1005 |
| T23 | P1: TK-108 (dan seluruh fase UI) |
| T24 | P8: TK-807, TK-808 |

Unit: policy, eligibility, allocation, rounding, periode (vektor TD §4), parser, katalog i18n. Integration: PostgreSQL nyata (RLS/lock/constraint/ledger/RADIUS tenant), receiver/storage, outbox. Contract: OpenAPI, enum, error, capability. E2E: R1 dan bayar → aktivasi manual (R2). Lab: RouterOS nyata/CHR, FreeRADIUS, dan CPE; mock tidak menggantikan. Negatif: SSRF, upload/traversal, formula injection, permission dicabut, CSRF, TLS/pin salah, eskalasi peran, bulk lintas tenant, kebocoran secret (termasuk password layanan dan secret RADIUS), ledger bypass, peer-to-peer. Jangan mengakses IP/host di luar lab yang diizinkan.

Evidence mencatat ID sumber, commit, versi, topologi, command, waktu, expected/actual, log redacted. Tidak dijalankan = `NOT RUN` + alasan; `skipped` bukan lulus. Pilot desain ≥5 peserta (2 non-ahli), target ≥80% tugas inti dan nol salah-tenant/salah-aktivasi; uji adopsi 50 akun oleh 8 dari 10 operator — dua studi berbeda, jangan saling menggantikan.

## 12. Parameter terkunci dan gerbang aktivasi

[REVISI AUD-04] Keputusan C/D/N yang disetujui tetap berlaku. Celah implementability yang belum diselesaikan dalam audit lanjutan tercatat di `sumber/audit/Unresolved_Issues_v2_1.md` (target `docs/audit/Unresolved_Issues_v2_1.md`); selain bukti runtime, task terkait menunggu klarifikasi desain. Tidak mengarang default. Registri nilai TD §16 dibaca bersama AUD-09/MAC-08.

Gerbang minimum per fitur memakai satu tabel kanonik: `sumber/quality/Quality_Gates_and_Release_Readiness_v2_1.md` §4 (target `docs/quality/Quality_Gates_and_Release_Readiness_v2_1.md`). G0 berlaku semua rilis; G2 security/privacy applicable tidak hilang untuk cutover, ACS atau WAN. Persyaratan khusus seperti G1 spike backup, G3 auto-isolir dan G4 edge tetap pada tabel tersebut. Landing tetap menunggu `BRAND_*` (TK-107); rekening tidak dipublikasikan. Tabel gate tidak memberi otorisasi produksi.

Gerbang desain QG-QA-01..12 (dokumentasi/test-design) dievaluasi terpisah dari tabel di atas: kelulusannya tidak mengaktifkan fitur apa pun dan tidak menggantikan syarat G0–G5. Urutan run lab awal yang aman (setelah akses disetujui): inventaris read-only → smoke aplikasi terisolasi → T10/T19 negatif isolasi → T16 autentikasi → T01 keselamatan bootstrap → T17 cutover bertahap dengan canary/rollback — **proposal urutan kerja** (`sumber/quality/Quality_Gates_and_Release_Readiness_v2_1.md` §4, target `docs/quality/Quality_Gates_and_Release_Readiness_v2_1.md`), bukan perubahan dependency kanonik backlog ini.

## 13. Definition of Done dan hasil akhir

Task DONE bila implementasi tersambung end-to-end, migrasi/permission/error path benar, tes relevan lulus, sumber terlacak, dokumentasi diperbarui. Task dapat `implemented` namun belum `release_enabled`; tulis terpisah. Rilis siap hanya bila semua gerbang fase lulus, tanpa blocker kritis, deployment/rollback/recovery teruji, dan otorisasi pilot tersedia.

Deliverables: source backend/frontend/adapter + migrasi + seed sintetis; OpenAPI + typed client, state machine, permission matrix; tes dan evidence T01–T24 serta child registry64 dan QA-SEC20 yang relevan per fase; compatibility manifest; CI, lockfile, build reproducible, template deployment, `.env.example`; runbook dan panduan (onboarding/import/pembayaran/aktivasi/backup/troubleshooting); traceability, ADR, backlog/progress, release-readiness yang jujur.

**Format checkpoint:**

```markdown
## Checkpoint
- Fase dan task aktif:
- Implementasi selesai:
- File/commit terkait:
- Pengujian dijalankan dan hasil:
- Belum diuji / blocked dan alasannya:
- Fitur produksi tetap nonaktif:
- Temuan baru (X-nn) dan default aman yang dipakai:
- Task siap dikerjakan berikutnya:
```

## 14. Perintah mulai untuk agent

Baca `AGENTS.md` lebih dulu. Urutan sesi pertama: (1) verifikasi seluruh source path/ukuran/SHA-256 dan pemetaan manifest aktif di staging, tanpa legacy bootstrap dan sebelum menulis target; (2) setelah seluruhnya valid, tempatkan sesuai manifest, skip identik, conflict untuk target beda dan tolak symlink; buat `docs/decisions.md` hanya bila belum ada sebagai log temuan X-nn yang merujuk keputusan kanonik; (3) buat backlog dan traceability; (4) kerjakan TK-002–TK-004/TK-107 hanya dalam mandat workspace; lanjutkan dependency yang lengkap. Kode aplikasi menunggu langkah 1–3, kecuali scaffold TK-002 terotorisasi. Jika kontrak task kurang lengkap, task terkait BLOCKED; lanjutkan pekerjaan independen.

## Lampiran A — Peta cakupan ID PRD ke task (seed `docs/traceability.md`)

| ID PRD | Task |
|---|---|
| GOAL-01, GOAL-03 | TK-401–404, TK-410, TK-411, TK-509 |
| GOAL-02 | TK-003, TK-601, TK-604 |
| GOAL-04 | TK-701–705 |
| GOAL-05 | TK-306, TK-410, TK-407, TK-509 |
| GOAL-06 | TK-108, TK-609, TK-807–810 |
| TEN-01, TEN-02, TEN-03 | TK-101, TK-102, TK-104 |
| SUB-01, SUB-02, SUB-03 | TK-105, TK-404, TK-407 |
| SUB-04 | TK-201, TK-203 |
| SUB-05 | TK-205 |
| PAY-01, PAY-02 | TK-201, TK-106 |
| PAY-03 | TK-202, TK-204 |
| PAY-04 | TK-203 |
| UX-01 | TK-104, TK-107, TK-204 |
| UX-02, UX-05 | TK-104, TK-108 |
| UX-03, UX-04 | TK-405, TK-604 |
| UX-06 | TK-403, TK-407, TK-705 |
| I18N-01–I18N-10 | TK-108, TK-109 |
| INF-01 | TK-002, TK-1002 |
| INF-02, INF-03 | TK-1001, TK-1002 |
| NET-01, NET-03 | TK-301, TK-302 |
| NET-02 | TK-305 |
| NET-04, NET-05, NET-07 | TK-304, TK-411 |
| NET-06, NET-08 | TK-301, TK-302, TK-305 |
| IMP-01 | TK-401 |
| IMP-02, IMP-04 | TK-402, TK-403 |
| IMP-03 | TK-403, TK-410, TK-411 |
| IMP-05 | TK-401, TK-402 |
| RAD-01, RAD-02, RAD-03 | TK-306, TK-307 |
| RAD-04, RAD-05 | TK-306, TK-408, TK-501 |
| RAD-06 | TK-501, TK-603 |
| RAD-07 | TK-510 |
| RAD-08 | TK-511, TK-811 |
| RAD-09 | TK-410, TK-411, TK-403 |
| RAD-10 | TK-509 |
| RAD-11 | TK-407, TK-509 |
| RAD-12 | TK-807 |
| RAD-13 | TK-102, TK-306, TK-1006 |
| RAD-14 | TK-306, TK-509, TK-510, TK-811 |
| PRO-01 | TK-408 |
| PRO-02 | TK-409, TK-508 |
| SYNC-01 | TK-003, TK-406 |
| SYNC-02 | TK-406 |
| SYNC-03 | TK-103, TK-501 |
| CUS-01, CUS-02 | TK-405, TK-501 |
| LIF-01–LIF-04 | TK-810, TK-407 |
| CSV-01, CSV-02, CSV-03 | TK-404 |
| BIL-01, BIL-02, BIL-03 | TK-601 |
| BIL-04 | TK-607 |
| BIL-05 | TK-608 |
| BIL-06 | TK-609, TK-806 |
| BIL-07, BIL-08 | TK-601, TK-109 |
| COL-01–COL-03 | TK-609 |
| ACT-01, ACT-02 | TK-602 |
| ACT-03, ACT-04 | TK-603 |
| ACT-05 | TK-604, TK-605 |
| HSP-01–HSP-04 | TK-807 |
| HSP-05 | TK-809 |
| AGT-01–AGT-03 | TK-808 |
| ACC-01, ACC-05 | TK-701, TK-702, TK-808 |
| ACC-02 | TK-702, TK-703 |
| ACC-03 | TK-703, TK-609 |
| ACC-04 | TK-703 |
| ACC-06 | TK-703 |
| ACC-07 | TK-704 |
| ACC-08, ACC-09 | TK-607, TK-702 |
| ACC-10 | TK-705 |
| ACC-11 | TK-003, TK-701 |
| ACC-12 | TK-701 |
| MON-01–MON-04 | TK-502, TK-503, TK-510 |
| MON-05 | TK-502, TK-511, TK-806 |
| MON-06 | TK-503 |
| BKP-01, BKP-02, BKP-04 | TK-504, TK-506, TK-507 |
| BKP-03 | TK-505 |
| BKP-05 | TK-507, TK-1004 |
| BKP-06 | TK-506 |
| ACS-01–ACS-06 | TK-801–803 |
| ACS-07 | TK-804, TK-906 |
| ACS-08–ACS-10 | TK-801, TK-802 |
| WAN-01–WAN-04, CFG-01, CFG-02 | TK-901–905 |
| OPS-01–OPS-03 | TK-804, TK-810 |
| OPS-04 | TK-805 |
| OPS-05 | TK-806 |
| OPS-SEC | TK-102, TK-1003 |
| PDP-01–PDP-05 | TK-102, TK-407, TK-1006 |
| DATA-01, DATA-02 | TK-003, TK-102, TK-402 |
| DATA-03, API-01, API-02 | TK-003, TK-103 |
| JOB-01 | TK-003 |
| JOB-02–JOB-05 | TK-103 |
| SEC-01 | TK-101, TK-102 |
| SEC-02 | TK-304 |
| SEC-03 | TK-106, TK-404 |
| SEC-04, SEC-05 | TK-102 |
| NFR-01, NFR-03 | TK-1003, TK-1005 |
| NFR-02, NFR-04 | TK-1004 |


## 15. Kontrak eksekusi individual dan dependency 2.1-build.1

Registry `agent/task-contracts_v2_1.json` adalah detail normatif task menurut EXE-04, dengan15 field eksekusi dan DAG eksplisit. Path target `docs/contracts/task-contracts_v2_1.json`. Objective dan ID TK-001..TK-1006 tetap backlog ini; tidak ada task baru tersembunyi. Stage contract/build/verified/release_enabled berbeda. Milestone lokal P0 tidak menunggu bukti perangkat; prototype ledger tidak dianggap production posting. Task ledger P7 mengikat event finansial P2/P6 sebelum verifikasi pembukuan final. Test source dan scenario tambahan di `sumber/quality/supplemental-test-registry_v2_1.json`;84 kasus baseline tetap utuh sebagai registry utama, bukan total seluruh spesifikasi supplemental.

Kontrak parameter/kind/profil/fixture: `sumber/contracts/Execution_Design_v2_1.md`. Applicability assertion: `sumber/quality/release-applicability_v2_1.json`. Readiness saat ini dan keputusan tersisa: `sumber/audit/Unresolved_Issues_v2_1.md`. Full-audit PASS menunggu decision/review; local foundation build hanya setelah mandat workspace yang sesuai. Agent dilarang menggunakan status dokumen sebagai pengganti mandat.
