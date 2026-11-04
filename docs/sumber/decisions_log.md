# Decisions Log — Keputusan Final Platform SaaS Manajemen RT/RW Net

[REVISI MACRO 2.1-macro.1] MAC-01–08 merupakan keputusan konsolidasi dokumentasi yang baru, bukan penulisan ulang keputusan historis pemilik. Nilai efektif/approval aktual belum diobservasi. ADR implementasi wajib menautkan rule version dan dampak gate. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


Versi 1.2 · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.1 (11 Oktober 2026) → 1.2 (28 Oktober 2026; menambah Bagian E — putusan penyelarasan dokumentasi; Bagian Temuan implementasi menjadi Bagian F, registri parameter menjadi Bagian G)

Berkas ini mencatat **keputusan final** produk dan arsitektur. Setiap keputusan sudah diterapkan secara konsisten pada: `PRD_SaaS_RTRWNet_v2_1.md` (PRD), `Technical_Design_RTRWNet_v2_1.md` (TD), `UIUX_Design_RTRWNet_v2_1.md` (UX), `tugas_v2_1.md` (TGS), `AGENTS_v2_1.md` (AGT), dan dokumen normatif pendamping (RAD = `Spesifikasi_RADIUS_dan_Migrasi`, ROS = `Playbook_RouterOS`, ACS = `Spesifikasi_ACS_TR069`, ACC = `Panduan_Akuntansi_ISP`, I18N = `Spesifikasi_i18n`); dokumen kualitas `sumber/quality/` merujuk keputusan ini tanpa mengubah maknanya.

**Cara memakai:** agent menyalin berkas ini ke `docs/decisions.md` dan hanya menambah bagian "Temuan implementasi" (Bagian F). Keputusan pada Bagian A–D dan putusan penyelarasan pada Bagian E bersifat **terkunci**; berubah hanya lewat instruksi eksplisit pemilik + ADR. "Gerbang" pada kolom bukti berarti syarat bukti sebelum `release_enabled`, bukan keputusan yang menggantung. Perhatikan: ID keputusan teknis pada Bagian D memakai tanda hubung (`T-01`–`T-09`) dan berbeda dari ID uji `T01`–`T24` (PRD §26).

Dasar keputusan: standar RouterOS dan operasi jaringan (dokumentasi resmi MikroTik), RFC RADIUS, spesifikasi TR-069, praktik SaaS multi-tenant, standar akuntansi double-entry, dan kebutuhan pengusaha RT/RW Net Indonesia. Prinsip: aman, reversible bila ragu, tidak mengklaim melebihi bukti.

---

## Bagian A — Keputusan produk dan arsitektur (C-01 – C-21)

| ID | Pokok | **Keputusan final** | Diterapkan di | Bukti |
|---|---|---|---|---|
| C-01 | Batas CSV | **10 MiB dan 10.000 baris, keduanya berlaku**; plafon keras konfigurasi 20 MiB/20.000 setelah uji beban | PRD CSV-03; TD §8, §16; UX §6; TGS TK-404 | Uji beban; T04 |
| C-02 | Penomoran gerbang | **G0–G5** tunggal: G0 desain/ADR, G1 lab (RouterOS, RADIUS, CPE), G2 tenant/security/finance/restore, G3 pilot, G4 load/soak + HA RADIUS, G5 DR/runbook | PRD §26; TD §15; TGS §11–12 | Evidence per gerbang |
| C-03 | Status job | **queued, claimed, preflight, executing, verifying, succeeded, waiting_dependency, retry_wait, failed, uncertain, cancelled, recovery_required**; `partial` = ringkasan parent; `stale` = label kesegaran | PRD §23; TD §6; UX §12 | Contract test enum |
| C-04 | Status enrollment | draft → enrollment_issued → bootstrap_pending → tunnel_seen → api_verified → discovery_ready; conflict, expired, revoked | PRD §23; TD §7 | T01 |
| C-05 | Path API | Path TD §5 kanonik | PRD §22; TD §5 | Contract test |
| C-06 | Navigasi | **5 kelompok sidebar memetakan 13 menu**; header tenant terang; header `/admin` navy `#0F2A4A` | PRD §5; UX §1–2 | Uji kontras |
| C-07 | Wizard adopsi | **8 langkah**: Sumber → Pilih → Gabungkan identitas → Petakan pelanggan → Petakan profile/paket → Sumber password → Tinjau → Simpan | PRD IMP-03; UX §6 | T02 |
| C-08 | Daftar pelanggan | **5 tab cepat**, **4 status terpisah** (bayar, isolir, koneksi, job) | PRD UX-03; UX §5 | E2E |
| C-09 | Komponen arsitektur | Reverse proxy, VPN manager, receiver backup, **FreeRADIUS**, Prometheus, pipeline upload wajib | PRD §6; TD §2 | G1 |
| C-10 | Dimensi service | Tujuh dimensi (ED21); lifecycle: draft, pending, provisioning, provisioned, conflict, failed, terminated, archived | PRD JOB-01; TD §4 | Contract test |
| C-11 | Dashboard R1 | Kartu R2 disembunyikan (bukan nol) | PRD UX-02 | E2E |
| C-12 | Kuota draft | Draft manual tidak memakai kuota; adopsi/migrasi/CSV/pembuatan akun/voucher mereservasi; batas draft `max(10, ceil(25% × limit))`, maks. 500 | PRD SUB-01 | Uji race |
| C-13 | Publikasi rekening | `published=false`; rekening hanya pada invoice terautentikasi | PRD PAY-02/03 | AC-PAY |
| C-14 | Anniversary | Jangkar tanpa drift, clamp akhir bulan, `[start,end)`, tanggal kalender | PRD SUB-04; TD §4 | Vektor uji |
| C-15 | Interval detail router | 15 detik (konfigurasi) | PRD MON-02 | T15 |
| C-16 | Konvensi ID | BIL-xx dan ACT-xx | PRD | Traceability |
| C-17 | Autentikasi | Email+password (Argon2id), MFA TOTP + kode pemulihan, email transaksional SMTP (dev Mailpit), tanpa WhatsApp OTP | PRD §2; UX §3 | T10 |
| C-18 | Peran | Permission granular; bundel Owner/Teknisi/Admin Pembayaran, Akuntan, Viewer, Kolektor, Agen | PRD TEN-02; TD §3 | Matriks permission |
| C-19 | Penggantian router | Pelepasan dan penggantian router tanpa pemetaan ulang akun (akun milik tenant di RADIUS) | PRD SUB-01; RAD §10.3 | T18 |
| C-20 | Backup manual/pre-change | 10 generasi per kategori per router (FIFO) | PRD BKP-01 | T08 |
| C-21 | SaaS grace | Grace 7 hari; restricted hari 8–30; ended hari ke-31; RADIUS tenant tetap dilayani sampai penarikan | PRD SUB-05 | Uji state |

## Bagian B — Parameter bisnis dan teknis (D01 – D10)

| ID | Keputusan final | Diterapkan di | Gerbang |
|---|---|---|---|
| D01 | Merek/domain/logo/kontak dari konfigurasi `BRAND_*`; **nomor konfirmasi pembayaran 082319199930** (kontak WhatsApp/telepon pemilik; sama dengan nomor DANA/GoPay/OVO) | PRD §4–5; UX §9 | Pemeriksaan rilis `BRAND_*` |
| D02 | Inventory VM wajib; tidak ada klaim spesifikasi/kapasitas sebelum benchmark | PRD INF-03, §25 | G3, G4 |
| D03 | RouterOS v7 untuk mutasi/cutover; v6 read-only; native API-SSL dengan sertifikat dipin = default; REST alternatif (mati default); klien API internal; group custom, mode `read_only` default | PRD NET-02/04/05/07; ROS §3–4 | G1 (T01) |
| D04 | Backup: SFTP push via VPN + kontrol kompensasi; cadangan pull; 64 MiB/artifact; password binary dibangkitkan platform; kunci pemulihan via reauth+MFA | PRD BKP-02/03 | G1 (TK-505) |
| D05 | SaaS grace 7/restricted ≤30/ended; VPN dan RADIUS 60 hari dengan notifikasi 7/3/1; data 180 hari; isolir internet grace 3 hari (0–30), default off, simulasi 24 jam | PRD SUB-05, ACT-01 | G3 |
| D06 | Tanpa prorata SaaS; upgrade = periode baru + hari bonus; downgrade saat renewal; refund hanya kesalahan/ganda; harga final, pajak default 0 | PRD SUB-04, PAY-04 | AC-SUB |
| D07 | Plafon Platinum 25 router/5.000 layanan; anggota tim 3/5/8/12/20/50; metrik 15 hari/90 hari/400 hari; accounting RADIUS 90 hari/400 hari | PRD TEN-02, SUB-03 | G4 |
| D08 | Autentikasi CPE per-device; tidak ada model pra-didukung; OLT inventaris manual, adapter R4 | PRD ACS-03/04; ACS | G1, T11 |
| D09 | COA default, pengakuan harian diposting bulanan, SAK EMKM default, buku platform terpisah | PRD ACC-01/02; ACC | G2 (T12 + akuntan) |
| D10 | RPO ≤15 menit, RTO ≤4 jam sebagai target; SLA hanya setelah G5 | PRD NFR-02 | G5 |

## Bagian C — Keputusan tambahan (N01 – N20)

| ID | Keputusan final | Diterapkan di |
|---|---|---|
| N01 | Batas CSV (lihat C-01) | PRD CSV-03 |
| N02 | Aturan anniversary (lihat C-14) | PRD SUB-04; TD §4 |
| N03 | Reservasi kuota; TTL 60 menit; `pending` tetap dihitung | PRD SUB-01/02 |
| N04 | Rekening tidak dipublikasikan; hanya pada invoice terautentikasi | PRD PAY-02/03 |
| N05 | Autentikasi, sesi tenant idle 8 jam/platform 30 menit, reauth 10 menit | PRD §2; TD §3 |
| N06 | Nama/domain/logo/kontak = `BRAND_*`; token warna UI | PRD UX-01; UX §2 |
| N07 | Scanner upload ClamAV via antarmuka, **fail-closed**; bukti bayar JPEG/PNG/PDF ≤5 MiB | PRD PAY-02, SEC-03 |
| N08 | Idempotency 7 hari; log aplikasi 30/akses 90/keamanan-audit 400 hari; radpostauth 30 hari | PRD OPS-SEC |
| N09 | Ledger tiga lapis (role runtime tanpa DML langsung, `ledger.post_entry` SECURITY DEFINER dengan period lock, constraint trigger deferred + immutability) | PRD ACC-11; TD §10; ACC §13 |
| N10 | Satu Hotspot user terkelola = satu unit kuota; **voucher valid yang diterbitkan dihitung** (R3, reservasi atomik per batch) | PRD SUB-01, HSP-02 |
| N11 | Anggota tim per paket; backup manual/pre-change 10; kolektor/agen bukan anggota tim dengan batas per paket | PRD TEN-02, SUB-03 |
| N12 | Pelepasan/penggantian router: slot tidak dihitung ganda hingga 30 hari | PRD SUB-01 |
| N13 | **RADIUS wajib**: satu basis pengguna per tenant dibagi seluruh router; username unik per tenant, case-sensitive | PRD §9; RAD §1–3 |
| N14 | Password layanan terenkripsi di aplikasi; proyeksi `Cleartext-Password` pada `radius.radcheck` terkendali (role terbatas, soket lokal, backup terenkripsi, tidak ada di log/export) karena CHAP/MS-CHAPv2 | PRD RAD-05; RAD §6 |
| N15 | Adopsi/migrasi database-only; cutover per router terpisah (B0–B6), canary 30 menit, `enforcement_mode`, rollback; isolir/kecepatan/pindah-router dijamin hanya pada `radius_authoritative` | PRD RAD-09/10; RAD §10 |
| N16 | Dua alamat RADIUS pada router (primer/sekunder), HA lokal pada G4, edge replica opsional (R3), runbook rollback | PRD RAD-08; RAD §9 |
| N17 | Bahasa `id` default, `en` wajib; frontend ICU (FormatJS), backend gettext; kode mesin tidak diterjemahkan; fallback `id`; bahasa dokumen disnapshot | PRD I18N; I18N §1–6; TD ED38 |
| N18 | `first_period_policy` per paket: `full` (default), `prorata_daily`, `free_until_next_period` | PRD BIL-02; ACC §3 |
| N19 | Kolektor/agen: akun clearing 1-1150, setoran, komisi sebagai utang, pendapatan voucher sesuai kebijakan tenant | PRD COL, AGT; ACC §4, §6 |
| N20 | Voucher dan FUP/kuota data pada R3 berbasis accounting RADIUS; bukan dasar penagihan uang kecuali paket berbasis kuota diaktifkan dan diuji | PRD HSP-02/05 |

## Bagian D — Keputusan teknis RouterOS/RADIUS/ACS yang terkunci

| ID | Keputusan | Diterapkan di |
|---|---|---|
| T-01 | Panen password hanya lewat akun migrasi sementara (`read, api, sensitive`, ≤ 24 jam, penghapus otomatis, batas laju) atau CSV/password baru/impor RADIUS eksternal; discovery tidak membaca password | RAD §10.1; ROS §8 |
| T-02 | Secret/user lokal berservis selain pppoe/any tidak dimigrasikan; akun administrator tetap lokal | PRD IMP-01 |
| T-03 | Penonaktifan vs penghapusan secret lokal pada B5 mengikuti hasil lab T17; urutan prioritas lokal/RADIUS dicatat dari lab | RAD §10.2; ROS §6 |
| T-04 | Kecepatan paket dikirim lewat `Mikrotik-Rate-Limit` (rx = unggah dari pelanggan, tx = unduh); profil router memuat pool/alamat lokal/DNS saja | RAD §5; ROS §7 |
| T-05 | Isolir penuh = `Auth-Type := Reject` + Disconnect-Request; verifikasi 4 bukti termasuk uji autentikasi sintetis server-side; isolir terbatas opsional R3 dengan aturan router milik operator | RAD §7; PRD ACT-03/04 |
| T-06 | FastTrack hanya dideteksi/dilaporkan pada R1–R3; Hotspot+PCC satu router tidak didukung | PRD IMP-05, WAN-04 |
| T-07 | [REVISI AUD-37] Rotasi ACS↔RADIUS dengan versioned pending, jalur manajemen independen atau recovery teruji; respons hilang=uncertain, bukan unchanged | ACS §8 |
| T-08 | Tenant pada ACS dipisah oleh adapter (bukan tag); klaim enrollment serial+OUI+product class + secret sekali pakai; virtual parameter TR-098/TR-181 | ACS §2, §4–5 |
| T-09 | Autentikasi RADIUS tenant tetap dilayani saat status SaaS `ended` sampai penarikan terjadwal | PRD SUB-05 |

## Bagian E — Putusan penyelarasan dokumentasi (28 Oktober 2026)

Pemilik produk menginstruksikan optimasi menyeluruh paket dokumen: struktur rapi, satu sumber kebenaran per konsep, tanpa duplikasi/kontradiksi/placeholder. Instruksi pemilik yang telah diterapkan sejak v1.3 dan tetap berlaku: nomor konfirmasi pembayaran **082319199930**; perubahan tidak perlu ditandai; solusi end-to-end untuk pengusaha RT/RW Net Indonesia; antarmuka multi bahasa default `id`; basis pengguna RADIUS per tenant dibagi seluruh router tenant. Bekas `Laporan_Audit_v1_3.md` dihapus dari paket karena seluruh isinya terwakili: temuan→perlakuan pada dokumen normatif masing-masing, risiko terbuka pada TD §16 "Prasyarat pembuktian" dan gerbang PRD §26, instruksi pemilik pada Bagian E ini. Putusan berikut terkunci sama seperti Bagian A–D.

| ID | Pokok | Putusan | Diterapkan di |
|---|---|---|---|
| DOC-01 | Nama/versi berkas | Konvensi `<Nama>_v<X_Y>.md` tanpa sufiks "Final" (status di dalam dokumen); seluruh versi dinaikkan serentak; rilis 28 Oktober 2026 | Seluruh berkas; README |
| DOC-02 | Struktur paket | Paket: akar (README, bootstrap) + `agent/` (AGENTS, tugas) + `sumber/` (dokumen normatif, decisions, manifest) | README; bootstrap_docs.sh |
| DOC-03 | Struktur repository | Versi lengkap (domain `access`/`i18n`, adapter `radius`, `tests/radius_lab`, `infra/freeradius`, `locales/`) ditetapkan di TD §1 sebagai sumber kebenaran; tugas §6 merujuk (sebelumnya kedua dokumen berbeda) | TD §1; tugas §6 |
| DOC-04 | SSOT harga paket | PRD §3; tugas §5 dan UX §9 merujuk (UX hanya aturan penyajian) | PRD §3; tugas §5; UX §9 |
| DOC-05 | SSOT rekening & nomor konfirmasi | PRD §4 (+ registri TD §16); tugas §5 merujuk; larangan perubahan tetap di AGENTS | PRD §4; tugas §5; AGENTS |
| DOC-06 | SSOT aturan posting jurnal | Panduan Akuntansi bagian 2–9 (termasuk aturan refund yang sebelumnya hanya di TD); TD §10 hanya penegakan teknis + merujuk | Panduan §5; TD §10 |
| DOC-07 | SSOT state machine | PRD §23; tugas §8 merujuk dan mematerialisasi `docs/contracts/state-machines.md` | PRD §23; tugas §8 |
| DOC-08 | SSOT kode error (13) | TD §5; PRD API-01, tugas §7, AGENTS merujuk | TD §5; tugas §7; AGENTS |
| DOC-09 | SSOT jenis job | TD §6; tugas §8 merujuk | TD §6; tugas §8 |
| DOC-10 | SSOT matriks uji T01–T24 | PRD §26; tugas §11 hanya pemetaan fase/task; kriteria domain di RAD §13 / ACS §12 | PRD §26; tugas §11 |
| DOC-11 | Keputusan vs nilai parameter | decisions_log Bagian A–D = keputusan (apa/mengapa); TD §16 = registri nilai default; PRD §27 menjadi peta rujukan tanpa mengulang nilai | PRD §27; TD §16 |
| DOC-12 | Label verifikasi isolir | State `verified` bersifat arah (suspend/restore); label UI `verified_suspended` (suspend) dan `verified_active` (restore) | PRD §23; TD §9 (ED22); UX §12 |
| DOC-13 | RouterOS v6 | Hanya baca adalah baseline tetap (frasa "sampai lulus lab" dihapus); mutasi/cutover hanya v7; perubahan lewat instruksi pemilik + ADR | PRD §7 (NET-02) |
| DOC-14 | Aturan firewall UDP 3799 | Dipasang saat enrollment (Playbook §5); cutover B2 memverifikasi keberadaannya (idempoten) | RAD §10.2; Playbook §6 |
| DOC-15 | Registri parameter | Seluruh parameter terkonfigurasi wajib terdaftar di TD §16; kunci yang tersebar ditambahkan (acs, mon probe/poll, vpn.mtu, auth login/password, session.absolute, isolation.scheduler, csv.temp, discovery, upload) | TD §16 |
| DOC-16 | Placeholder | Catatan "isi diisi setelah TK-002" pada daftar perintah AGENTS dihapus; kontrak antarmuka dijelaskan global | AGENTS |
| DOC-17 | Laporan audit | `Laporan_Audit_v1_3.md` dihapus; isinya terwakili penuh (lihat pembuka Bagian E) | README riwayat; Bagian E |
| DOC-18 | Navigasi | "13 menu produk + tautan Bantuan" dinyatakan eksplisit agar tidak salah hitung | PRD §5; UX §1 |
| DOC-19 | Urutan kewenangan | SSOT = AGENTS.md; tugas §2 merujuk | AGENTS; tugas §2 |
| DOC-20 | Model data | Kolom `static_ip_by_router` (override IP statis per router, dipakai RAD §10.3) ditambahkan ke `access_account` | RAD §3, §5, §10.3; TD §4 |
| DOC-21 | Protokol status pembuktian | SSOT definisi `implemented`/`verified_local`/`verified_lab`/`release_enabled` = tugas §3; AGENTS merujuk | AGENTS; tugas §3 |

## Bagian F — Temuan implementasi (diisi agent)

Format: `X-nn | Temuan | Dampak | Usulan | Default aman reversible | Status`. Mulai dari X-01. [REVISI AUD-01] Bagian A–E dibaca bersama amendemen v2.1; perubahan historis tidak diklaim sebagai keputusan lama.

## Bagian G — Registri parameter

Nilai default final seluruh parameter terkonfigurasi: `Technical_Design_RTRWNet_v2_1.md` §16.

## Bagian H — Konsolidasi makro 29 Oktober 2026

Keputusan MAC-01–08 berlaku menurut master §23. MAC-03 menetapkan minimum retensi dan legal hold; MAC-04 clock/eskalasi PDP; MAC-05 trust boundary RADIUS; MAC-06 dependency lokal/lab; MAC-07 gate; MAC-08 parameter dan owner. Ini keputusan normatif dokumentasi, bukan sign-off profesional atau izin produksi. Ringkasan dampak lengkap ada pada Documentation_Changelog_v2_1.md.
