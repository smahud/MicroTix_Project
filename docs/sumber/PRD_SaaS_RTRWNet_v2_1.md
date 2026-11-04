# PRD — Platform SaaS Manajemen RT/RW Net

[REVISI MACRO 2.1-macro.1] Persyaratan PDP/retensi/RADIUS dibaca bersama MAC-03–05. Gerbang minimum PRD §26 diperketat pada dokumen Quality Gates; keputusan fitur berlaku per versi/topologi/load. Retensi dan review profesional tidak mengubah harga/kuota produk. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


**Versi 1.4** · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.3 Final (11 Oktober 2026) → 1.4 (28 Oktober 2026; penyelarasan referensi, label turunan, dan satu sumber kebenaran — putusan DOC-01–DOC-21 pada `decisions_log.md` Bagian E).

Dokumen pendamping yang berlaku bersama dan saling selaras:
`Technical_Design_RTRWNet_v2_1.md` · `UIUX_Design_RTRWNet_v2_1.md` · `Spesifikasi_RADIUS_dan_Migrasi_v2_1.md` · `Playbook_RouterOS_v2_1.md` · `Spesifikasi_ACS_TR069_v2_1.md` · `Panduan_Akuntansi_ISP_v2_1.md` · `Spesifikasi_i18n_v2_1.md` · `tugas_v2_1.md` · `AGENTS_v2_1.md` · `decisions_log.md` · `source-manifest_v2_0.md` · dokumen kualitas `quality/` (strategi uji, matriks, lab GNS3, bukti).

Platform ini adalah **solusi end-to-end bagi pengusaha RT/RW Net di Indonesia**: dari pendaftaran perusahaan, penghubungan router MikroTik, migrasi pelanggan existing ke basis pengguna RADIUS bersama, penagihan dan pembayaran, isolir dan aktivasi, pembukuan, monitoring, backup, pengelolaan perangkat pelanggan (TR-069), sampai operasional lapangan dan portal pelanggan. Antarmuka mendukung banyak bahasa dengan **Bahasa Indonesia sebagai default**.

Dokumen ditujukan kepada pemilik produk, product manager, pengembang (termasuk AI coding agent), engineer jaringan, QA, akuntan, dan pengelola infrastruktur.

## Status dan arti validasi

- **Kebutuhan** = keputusan pemilik produk; baseline implementasi.
- **Parameter terkunci** = nilai keputusan final (rujukan C-xx, D-xx, N-xx pada `decisions_log.md`). Mengubahnya memerlukan instruksi eksplisit pemilik produk dan ADR.
- **Target uji** = angka penerimaan yang harus dibuktikan; bukan SLA.
- **Gerbang (G0–G5)** = bukti pengujian/otorisasi sebelum fitur diaktifkan (bagian 26).
- **Fakta teknis** bersumber dari dokumentasi resmi (bagian 28). Dokumentasi bukan audit server atau pengujian router nyata.

Spesifikasi VM, kapasitas uplink, versi RouterOS, firmware CPE, dan volume pelanggan belum diukur. Dokumen tidak menjamin satu VM melayani 1.000 perusahaan, semua ONT kompatibel, atau setiap perubahan router tanpa gangguan. Pernyataan teknis berbentuk persyaratan; hasil operasi nyata hanya boleh dinyatakan setelah diuji.

## Hasil utama yang diharapkan

Owner menghubungkan router, meninjau hasil penemuan, mengadopsi akun existing ke basis RADIUS perusahaan, melakukan cutover RADIUS per router, lalu menjalankan operasional harian dari satu aplikasi. Adopsi bersifat database-only. Pembuatan akun, pembayaran, isolir, dan aktivasi memiliki hasil terverifikasi serta audit. Pelanggan dapat dipindahkan antarrouter dalam satu perusahaan, dan router dapat diganti, tanpa input ulang data pengguna.

**Keputusan produk yang mengikat:** tidak ada port manajemen fisik khusus; trafik internet pelanggan tidak melewati server SaaS; periode harga bulanan atau tahunan; backup rutin maksimal 100 generasi berhasil per router; **seluruh akun PPPoE dan Hotspot yang dikelola berada pada basis RADIUS perusahaan**; isolir otomatis berjalan setelah policy diaktifkan tenant dan aktivasi setelah pembayaran dilakukan manual.

## Petunjuk penggunaan

ID kebutuhan (mis. RAD-09) dipakai pada backlog, tiket, dan uji. "Wajib" = syarat penerimaan, bukan fitur yang sudah tersedia. Label R1–R4 = fase pengiriman. Bila teks normatif bertentangan dengan sketsa/diagram, teks menang. Dokumen pendamping memuat rincian normatif untuk bidangnya; PRD ini menetapkan kebutuhan dan batas.

---

# 1 Tujuan produk dan ruang lingkup

## Sasaran

Platform adalah SaaS multi-company pada server milik pemilik produk (VM Debian, IP publik). Target bisnis sekitar 1.000 perusahaan RT/RW Net; setiap perusahaan memiliki anggota tim, router, pelanggan, dan perangkat sesuai hak paket. Pengguna cukup memakai web.

**GOAL-01** Meminimalkan input ulang melalui impor langsung MikroTik, migrasi ke RADIUS, dan CSV.
**GOAL-02** Menyatukan status pembayaran, langganan, koneksi, dan pekerjaan tanpa mencampurkan artinya.
**GOAL-03** Mempertahankan layanan pelanggan selama observasi, adopsi, dan cutover.
**GOAL-04** Menyediakan pembukuan dan histori yang dapat ditelusuri.
**GOAL-05** Menjadikan identitas pelanggan independen dari perangkat: satu basis pengguna RADIUS per perusahaan, dibagi seluruh router perusahaan.
**GOAL-06** Melayani pengusaha RT/RW Net Indonesia secara menyeluruh (siklus pelanggan, penagihan lokal, kolektor/agen, perangkat, lapangan) dengan antarmuka multi bahasa, default Indonesia.

## Cakupan bertahap

| Fase | Hasil yang wajib tersedia |
|---|---|
| R1 fondasi dan pelanggan | Landing, tenant, peran, paket, pembayaran SaaS manual, VPN/API, discovery dan adopsi, **RADIUS (basis pengguna, cutover per router)**, CSV, profile dan paket, pelanggan, monitoring dasar (termasuk accounting RADIUS), backup, multi bahasa (id, en) |
| R2 operasional bisnis | Invoice internet, isolir dan aktivasi via RADIUS, kolektor/kas, pembukuan, rekonsiliasi, laporan, penguatan kapasitas |
| R3 perangkat, voucher, lapangan | Hotspot voucher dan agen/reseller, ACS TR-069 untuk model terpilih, portal pelanggan, tiket, inventaris, ODP/peta, work order, prospek dan instalasi, notifikasi, FUP/kuota data, RADIUS edge replica |
| R4 jaringan lanjutan | Wizard single/failover/weighted PCC untuk topologi bersertifikasi, templat PPPoE/Hotspot, adapter OLT terpilih, perluasan skala |

Modul hanya tampil di menu harian dan dipasarkan setelah lulus gerbangnya dan flag rilis dinyalakan pemilik. Isolir produksi tidak diaktifkan sebelum uji kondisi balapan pembayaran, gangguan router, dan perilaku RADIUS lulus (T05, T20).

## Di luar klaim rilis

Tidak ada jaminan semua versi RouterOS, seluruh vendor ONT/OLT, atau semua perilaku RADIUS pada seluruh versi. Tidak ada upstream transit melalui server, bandwidth bonding universal, inspeksi isi trafik pelanggan, reset router, atau penggantian otomatis konfigurasi arbitrary. Kepatuhan pajak, perizinan penyelenggaraan jasa, dan standar akuntansi tidak dijamin hanya karena menggunakan software.

## Ukuran keberhasilan

Pilot usability: sedikitnya 8 dari 10 operator dapat mengadopsi 50 akun lokal ke RADIUS setelah koneksi siap tanpa CLI tambahan. Integritas: nol akun ganda pada retry, nol transaksi finansial ganda, nol akses lintas tenant. Perpindahan pelanggan antarrouter dan penggantian router tanpa input ulang pada fixture uji (T18). Semua perubahan produksi memiliki audit dan hasil per objek. Angka ini target evaluasi, bukan hasil.

---

# 2 Pengguna dan hak akses

## Model organisasi

**TEN-01** Tenant adalah perusahaan dan pemilik subscription. User memperoleh akses melalui membership; satu user dapat menjadi anggota beberapa tenant; berpindah tenant mereset scope tampilan, seleksi, cache, dan koneksi realtime. Router dimiliki satu tenant dengan satu controller penulis aktif. Lokasi/cabang opsional.

**Peran bawaan (bundel permission default)**:

| Kewenangan | Owner | Teknisi | Admin Pembayaran |
|---|---|---|---|
| Seluruh menu perusahaan sesuai paket | Ya | Tidak | Tidak |
| Subscription dan anggota tim | Ya | Tidak | Tidak |
| Router dan diagnosis | Ya | Sesuai scope | Ringkasan layanan |
| Profile, paket, dan konfigurasi | Ya | Sesuai izin | Tidak |
| Cutover RADIUS | Ya | Izin khusus | Tidak |
| Backup dan unduh | Ya (reautentikasi untuk kunci/unduh sensitif) | Sesuai izin | Tidak |
| Invoice dan verifikasi pembayaran | Ya | Tidak | Ya |
| Aktivasi satuan dan massal | Ya | Izin khusus | Ya |
| Kebijakan isolir | Ya | Tidak | Delegasi khusus |
| Akuntansi dan tutup periode | Ya | Tidak | Delegasi terpisah |

**TEN-02** Setiap perusahaan, termasuk Free, mendukung minimal satu Owner, satu Teknisi, dan satu Admin Pembayaran; Owner boleh merangkap. Otorisasi berbasis **permission granular**; Owner/Teknisi/Admin Pembayaran adalah bundel default. Bundel **Akuntan**, **Viewer**, **Kolektor** (hanya penerimaan tunai dan setoran sendiri), dan **Agen/Reseller** (portal agen terbatas) dibentuk dari permission yang sama. Batas anggota tim aktif (termasuk Owner) adalah batas sistem, bukan klaim pemasaran [N11]:

| Paket | Free | Bronze | Silver | Gold | Diamond | Platinum |
|---|---:|---:|---:|---:|---:|---:|
| Anggota tim aktif | 3 | 5 | 8 | 12 | 20 | 50 (fair use) |

Kolektor dan agen eksternal tidak dihitung sebagai anggota tim; mereka memiliki akun terbatas dengan batas jumlah per paket (Free 5, Bronze 20, Silver 50, Gold 100, Diamond 200, Platinum 500).

**TEN-03** Otorisasi diterapkan di backend, worker, query metrik, object storage, export, notifikasi, dan RADIUS provisioning; menyembunyikan tombol tidak cukup. Relasi antarentitas wajib dari tenant yang sama. Scope router/lokasi berlaku pada operasi massal.

**Sesi dan autentikasi** [N05]: email + password (min. 12 karakter, Argon2id); MFA TOTP (RFC 6238) dengan kode pemulihan sekali pakai. MFA wajib untuk semua peran platform; untuk Owner wajib sebelum aksi sensitif (ubah rekening/izin, unduh kunci, cutover/rollback RADIUS, restore, reopen periode, ekspor sensitif, tampilkan kredensial layanan). Reautentikasi berlaku 10 menit. Sesi tenant: idle 8 jam, absolut 24 jam; peran platform: idle 30 menit, absolut 12 jam. Perubahan peran membatalkan sesi yang tidak berhak. Tidak ada WhatsApp OTP. Email transaksional akun (verifikasi, reset, undangan) memakai SMTP terkonfigurasi; pada development ditangkap lokal.

## Tim platform

Super Admin mengelola operasi platform. Permission terpisah: admin pembayaran platform, pengelola perusahaan, dukungan teknis, operator infrastruktur. Verifikasi pembayaran tidak memberi izin mengubah rekening tujuan. Akun individual wajib.

## Penerimaan

**AC-TEN:** user tenant A mencoba ID router, invoice, pekerjaan, URL backup, akun RADIUS, dan perangkat ACS tenant B melalui UI/API/export; semua ditolak tanpa membocorkan isi (404 generik). Teknisi tidak dapat mengaktifkan pembayaran lewat endpoint tersembunyi. Perubahan peran membatalkan sesi. Hilangnya Owner terakhir dicegah sampai kepemilikan dialihkan sah.

---

# 3 Paket dan aturan subscription

Batas router dan layanan berlaku bersamaan; total layanan dihitung di seluruh router perusahaan. Masa tahunan = 12 bulan dengan harga 10 kali bulanan.

| Paket | Router | Layanan | Bulanan | Tahunan |
|---|---|---|---|---|
| Free | 1 | 50 | Gratis | Gratis |
| Bronze | 2 | 150 | Rp500.000 | Rp5.000.000 |
| Silver | 3 | 300 | Rp1.000.000 | Rp10.000.000 |
| Gold | 4 | 500 | Rp1.500.000 | Rp15.000.000 |
| Diamond | 5 | 750 | Rp2.000.000 | Rp20.000.000 |
| Platinum | Unlimited* | Unlimited* | Rp4.000.000 | Rp40.000.000 |

\* Unlimited = tanpa batas **lisensi**, bukan tanpa batas operasional (SUB-03).

**Harga final dan pajak** [D06]: harga di atas adalah harga final yang dibayar. Konfigurasi pajak per PlanVersion tersedia dengan tarif default 0 dan flag inklusif/eksklusif.

**SUB-01 Aturan hitung kuota** [C12, N03, N10]. Satu layanan internet terkelola (satu `access_account` PPPoE atau satu pengguna Hotspot terkelola) = satu unit kuota.

| Dihitung | Tidak dihitung |
|---|---|
| Layanan `provisioned`, offline, terisolir, manual-disabled, imported | Layanan `terminated` atau `archived` |
| Reservasi aktif (adopsi, migrasi, commit CSV, pembuatan akun, reaktivasi arsip) dan item `pending` | Draft manual tanpa reservasi |
| Router offline (tetap memakai slot sampai dilepas) | Akun router di luar pilihan adopsi |
| Voucher Hotspot yang diterbitkan dan masih valid (belum kedaluwarsa/dicabut) | Voucher habis, kedaluwarsa, atau dicabut |

Pelanggan dengan rumah dan toko = dua layanan; beberapa HP di satu rumah bukan layanan tambahan. **Batas draft manual per tenant** = `max(10, ceil(25% × batas layanan))`, maksimum 500 (Free 13, Bronze 38, Silver 75, Gold 125, Diamond 188, Platinum 500).

**Pelepasan dan penggantian router** [C19, N12]: Owner dapat *melepas* router (arsip; slot bebas; akun RADIUS tetap milik tenant dan tidak terpengaruh) atau *mengganti* router (mode `replacing`; memakai slot router lama; tidak dihitung ganda selama tumpang tindih maksimum 30 hari). Karena identitas pelanggan berada pada basis RADIUS tenant, penggantian router **tidak memerlukan pemetaan ulang akun**: router baru di-enroll, di-cutover RADIUS, dan binding paket/pool diterapkan. Histori penuh tersimpan.

**SUB-02** Reservasi kuota atomik sebelum pembuatan akun/impor. Reservasi dilepas otomatis bila gagal sebelum perubahan data; item yang tak dapat dipastikan menjadi `pending` yang tetap dihitung sampai diselesaikan atau dibatalkan. Reservasi tanpa kemajuan kedaluwarsa setelah 60 menit. Reaktivasi arsip memeriksa kuota.

**SUB-03 Platinum dan fair use** [D07]: tanpa batas lisensi, bukan batas penyimpanan, polling, concurrency, atau jaminan satu server. Plafon operasional default Platinum: 25 router dan 5.000 layanan per tenant; dapat dinaikkan Super Admin per tenant setelah pemeriksaan kapasitas (G4). Kuota perangkat ACS = batas layanan. Backup manual dan pre-change masing-masing maksimal 10 generasi per router [N11]. Retensi metrik: raw 15 hari, agregat 5 menit 90 hari, agregat 1 jam 400 hari; accounting RADIUS mentah 90 hari, agregat harian 400 hari. Fair use dipublikasikan di landing sebelum Platinum dijual.

**SUB-04 Periode, renewal, anniversary** [C14, N02, D06]:
1. Periode memakai **tanggal kalender** pada zona waktu perusahaan (platform: Asia/Jakarta), `[start_date, end_date)`.
2. Simpan **hari jangkar** `A` (hari-dalam-bulan `start_date` periode pertama). Periode ke-k mulai pada `clamp(A, bulan_awal + k)` dengan `clamp(A, bulan) = min(A, hari_terakhir_bulan)`; jangkar tidak bergeser. Contoh `A=31`, mulai 31 Jan: [31 Jan, 28 Feb) (29 Feb pada tahun kabisat), [28/29 Feb, 31 Mar), [31 Mar, 30 Apr). Tahunan berakhir pada `clamp(A, bulan_awal + 12)`.
3. **Renewal aktif** dimulai pada `end_date` periode berjalan dan mempertahankan jangkar. **Renewal sesudah expired** dimulai pada tanggal lokal approval; jangkar baru = hari tanggal itu; tidak ada penagihan mundur.
4. **Upgrade**: quotation → pembayaran → perubahan entitlement atomik; tanpa prorata uang; periode baru mulai pada tanggal approval dengan paket baru; sisa hari kalender utuh periode lama ditambahkan sebagai hari bonus; jangkar baru = hari tanggal approval.
5. **Downgrade**: berlaku pada renewal berikutnya; ditolak `quota_exceeded` bila pemakaian melebihi batas paket tujuan; tidak ada terminasi otomatis.
6. **Refund SaaS**: hanya untuk kesalahan sistem/pembayaran ganda, lewat dokumen koreksi.

**SUB-05 Siklus SaaS dan batas non-destruktif** [C21, D05]. Tidak ada isolir internet pelanggan karena utang SaaS. Status: `free/pending → active → grace → restricted → ended`.

| Status | Mulai | Perilaku |
|---|---|---|
| grace | `end_date` | 7 hari; fitur penuh; banner peringatan |
| restricted | hari ke-8 s/d ke-30 | Tidak dapat menambah router/layanan baru; operasi layanan existing, autentikasi RADIUS, accounting, backup, monitoring, akses bayar, export, dan pemulihan tetap berjalan |
| ended | hari ke-31 | Read-only + pembayaran + export; **autentikasi RADIUS pelanggan tetap dilayani** selama masa retensi VPN; automation isolir dijeda dengan notifikasi; peer VPN dan RADIUS dipertahankan 60 hari dengan notifikasi 7/3/1 hari sebelum penarikan; data dipertahankan 180 hari lalu alur penghapusan (export ditawarkan lebih dulu) |

Penarikan layanan RADIUS tidak pernah mendadak: sebelum penarikan, Owner menerima panduan rollback cutover (secret lokal) dan export akun. Retensi dokumen keuangan minimum 10 tahun kalender dari akhir tahun buku, tidak dapat dikurangi; hold, arsip dan purge mengikuti MAC-03 serta review akuntan/legal. Paket Free tidak kedaluwarsa.

**AC-SUB:** retry approval dan dua reservasi bersamaan tidak menggandakan masa atau melewati kuota. Uji 29/30/31 Januari, tahun kabisat, renewal aktif/sesudah expiry, upgrade hari bonus, downgrade melebihi kuota, perilaku RADIUS pada status ended.

---

# 4 Pembayaran platform dan Super Admin

**PAY-01** Alur wajib: pilih paket/periode → quotation → invoice → transfer → unggah bukti → verifikasi dana → approval → aktivasi. Bukti transfer bukan bukti final penerimaan bank. Status invoice, payment submission, subscription, dan activation job dipisahkan. Invoice SaaS kedaluwarsa 7 hari sesudah terbit (konfigurasi).

**PAY-02** Form: invoice, nama pengirim, metode, nominal, waktu, referensi opsional, file, catatan. File JPEG/PNG/PDF maksimum 5 MiB, divalidasi MIME (magic bytes), dipindai, disimpan privat dengan path opaque. File yang belum selesai dipindai tidak dapat dilihat/diunduh staf. Approval mencatat petugas, waktu, rekening, referensi, alasan; reject/needs revision wajib beralasan. Bukti dengan hash SHA-256 sama atau kombinasi (nominal, pengirim, tanggal) sama menghasilkan peringatan.

Rekening tujuan atas nama **Huda Choirul Anam** (data dari pemilik produk; kepemilikan bank belum diverifikasi eksternal) [C13, N04]:

| Metode | Nomor tujuan (`display_value` persis) |
|---|---|
| BCA Digital via BI Fast | 0022 0322 2222 |
| BCA | 3300589323 |
| Mandiri | 1710007451217 |
| SeaBank | 901635594814 |
| Bank Jago | 108337184986 |
| Superbank | 000029261674 |
| Krom Bank | 770080857777 |
| DANA atau GoPay atau OVO | 082319199930 |

Nomor konfirmasi pembayaran: **082319199930** (kontak WhatsApp/telepon pemilik; sama dengan nomor dompet digital di atas). Konfirmasi tampil sebagai tombol "Konfirmasi via WhatsApp" pada invoice dan halaman pembayaran terautentikasi; penayangan pada landing mengikuti konfigurasi `BRAND_CONTACT`.

**Aturan data rekening:** simpan `display_value` persis (termasuk spasi), `normalized_digits` hanya untuk pencocokan, nol di depan dipertahankan; tiap tujuan memiliki `status` aktif/nonaktif, `ownership_verified=false` dan `published=false` secara default. **Rekening tidak tampil pada landing publik**; instruksi pembayaran tampil pada invoice terautentikasi sebagai snapshot. [REVISI AUD-08] Invariant rekening tidak tampil pada landing tetap berlaku; reauth/audit saja tidak memberi izin mengubahnya menjadi publik.

**PAY-03** Semua tujuan pembayaran dapat diedit/dinonaktifkan dengan audit dan reautentikasi. Invoice menyimpan snapshot instruksi. Perubahan rekening menangani invoice terbuka secara eksplisit (tetap memakai snapshot; opsi menerbitkan ulang dengan alasan). Admin pembayaran platform dapat menyetujui transfer tanpa akses mengganti rekening.

**PAY-04** Partial payment (invoice `partial`, entitlement tidak aktif sampai lunas atau kedaluwarsa), selisih lebih (kredit platform atas tenant, dipakai pada invoice berikutnya; bukan pendapatan tambahan), bukti duplikat, pembayaran invoice expired (finance memulihkan invoice dengan alasan atau menjadikannya kredit), refund, dan salah approval masuk **alur koreksi** dengan dokumen sumber; riwayat tidak dihapus. Approval ke subscription memakai transaksi database + outbox.

**AC-PAY:** dua approver untuk submission/transfer yang sama menghasilkan satu Payment dan satu entitlement event bila invoice SaaS lunas. Dua transfer nyata ke invoice sama tetap dua Payment; allocation dibatasi outstanding dan sisa menjadi kredit. Aktivasi internet manual terpisah. Bukti sama memicu peringatan, bukan dedup dana berdasarkan invoice. Landing tidak memublikasikan rekening nonaktif atau `published=false`.

---

# 5 Navigasi, pengalaman pengguna, dan multi bahasa

## Website publik

**UX-01** Landing berisi manfaat, fitur yang benar-benar tersedia (`release_enabled`), harga bulanan/tahunan, plafon fair use Platinum, kompatibilitas, panduan, kontak (konfigurasi), registrasi, login, kebijakan privasi dan layanan. Demo memakai data simulasi terpisah. Klaim tanpa downtime dibatasi pada adopsi yang lulus uji; tidak mengiklankan semua ONT atau infrastruktur unlimited. Nama merek, domain, logo, dan kontak publik dari konfigurasi `BRAND_*`; "RT RW Net" adalah nama kerja [N06, D01]; landing tidak dipublikasikan bila `BRAND_*` belum terisi.

## Dashboard perusahaan

Menu produk (13): Beranda; Pelanggan; Paket dan Profile; Tagihan dan Pembayaran; Keuangan; Router dan Monitoring; Perangkat ACS; Backup; Gangguan dan Teknisi; Inventaris dan Peta; Konfigurasi; Perusahaan dan Tim; Paket Aplikasi — ditambah tautan **Bantuan** (bukan menu produk). UI memetakan 13 menu produk ke **5 kelompok sidebar** [C06]: Operasional (Beranda, Pelanggan, Paket dan Profile, Tagihan dan Pembayaran, Gangguan dan Teknisi); Jaringan (Router dan Monitoring, Backup, Perangkat ACS, Inventaris dan Peta, Konfigurasi); Keuangan; Perusahaan (Perusahaan dan Tim, Paket Aplikasi); Bantuan. Modul yang belum `release_enabled` tidak memenuhi menu harian.

**UX-02** Tenant aktif selalu terlihat. Filter lokasi/router dan pencarian dipertahankan dalam scope tenant. Beranda mengutamakan pekerjaan: sudah bayar menunggu aktivasi, data impor belum lengkap, router tidak terpantau, backup gagal, RADIUS bermasalah, tiket prioritas. Semua grafik/status memiliki timestamp pembaruan. Kartu modul R2 disembunyikan pada R1, bukan ditampilkan sebagai nol [C11].

**UX-03** Daftar pelanggan: identitas, username, router terakhir terlihat, jenis layanan, paket, status koneksi, subscription, invoice periode terpilih, job; empat status terpisah (bayar, isolir, koneksi, job) [C08]. Filter: router, profile/paket, online/offline/unknown, lunas/belum/sebagian, isolir, pending activation, incomplete mapping, kolektor, area. Pencarian: nama, customer code, username, telepon, invoice. Tab cepat: Semua; Belum bayar; Sudah bayar menunggu aktivasi; Terisolir; Data belum lengkap.

**UX-04** Tindakan massal membedakan halaman ini dan seluruh hasil filter. Snapshot seleksi dibekukan, jumlah ditampilkan, hak akses dan kondisi terbaru diperiksa per item sebelum eksekusi. Hasil per baris menyediakan retry hanya untuk kegagalan layak.

**UX-05** Antarmuka multi bahasa dengan **Bahasa Indonesia sebagai default**; format IDR; zona WIB/WITA/WIT; aturan lengkap pada `Spesifikasi_i18n_v2_1.md`. Label pelanggan "download ke pelanggan" dan "upload dari pelanggan"; adapter menerjemahkan arah rx/tx. Warna status selalu disertai teks. Form dapat dipakai pada lebar ponsel.

**UX-06** Rename router hanya mengubah `display_name` dan audit. Wizard impor menyimpan progres per tenant; setelah tertunda lama, snapshot divalidasi ulang. Tampilan awal Keuangan menonjolkan tagihan, kas masuk terverifikasi, piutang, tunggakan; laba akuntansi hanya dari ledger yang sesuai.

## Multi bahasa

**I18N-01 s/d I18N-10** (rincian pada `Spesifikasi_i18n_v2_1.md`): bahasa default `id`; bahasa `en` tersedia sejak R1; bahasa tambahan lewat paket terjemahan tanpa perubahan kode; teks tampil dari katalog pesan (ICU di frontend, gettext di backend); kode mesin (enum, kode error, atribut RADIUS) tidak diterjemahkan; bahasa ditentukan per pengguna, per tenant, dan per pelanggan; dokumen (invoice, kwitansi, laporan) menyimpan bahasa terbit; API melokalkan `message` berdasarkan `Accept-Language`; fallback ke `id`; pseudo-locale untuk uji.

**AC-UX:** operator menemukan pelanggan sudah bayar pada periode tertentu dan menjalankan aktivasi tanpa membuka menu routing. Menutup tab tidak membatalkan job. Data usang diberi label. Empty state memberi tindakan relevan. Seluruh layar dapat dirender dalam `id`, `en`, dan pseudo-locale tanpa teks tertanam.

---
# 6 Arsitektur dan prasyarat infrastruktur

## Rancangan referensi (terkunci)

Modular monolith dengan proses worker terpisah; PostgreSQL untuk data bisnis, buku besar, antrean job, transactional outbox, dan skema `radius`; **FreeRADIUS** sebagai server AAA terpisah; Prometheus internal untuk metrik agregat; GenieACS pada R3. Stack final ada pada Technical Design ED01–ED08 dan ED34–ED41 (Python + Django 5.2 LTS, React + TypeScript, PostgreSQL 17, FreeRADIUS 3.2, WireGuard + nftables, Caddy, Prometheus, ClamAV). [D03]

| Batas komponen | Jalur komunikasi |
|---|---|
| Browser → reverse proxy → API | HTTPS; autentikasi user dan tenant |
| API → database/outbox | Jaringan internal; transaksi bisnis |
| Dispatcher → MikroTik | Tunnel WireGuard; native API-SSL (default) dengan sertifikat dipin, REST HTTPS sebagai adapter alternatif (mati default); RADIUS Disconnect/CoA UDP 3799 |
| MikroTik → FreeRADIUS | Tunnel WireGuard; UDP 1812 (auth) dan 1813 (acct) ke alamat tunnel server |
| Collector → router → metrics store | Akun baca; polling terbatas; sesi dari accounting RADIUS |
| Router → penerima backup | Upload terbatas melalui VPN |
| CPE → ACS → adapter internal | CWMP/HTTPS (R3) |
| API → ACS NBI | Internal; otorisasi tenant pada gateway |

**INF-01** Debian, runtime, dan dependency dipin; artefak dibangun di CI dan diambil produksi dengan digest. Database, queue, FreeRADIUS, ACS NBI, dan storage management tidak dibuka ke publik.

**INF-02** Publik hanya: web HTTPS (443), port UDP VPN yang dikonfigurasi, dan endpoint ACS (R3). RADIUS **hanya** pada alamat tunnel. SSH administratif dibatasi. Sinkronisasi waktu, DNS, sertifikat dan renewal dipantau.

**INF-03** Inventory pra-deploy (TK-1001): vCPU, RAM, disk/IOPS, hypervisor, jaringan, IP publik langsung atau NAT, port forwarding, DNS, UPS, backup off-host. **Tidak ada klaim spesifikasi/kapasitas sebelum benchmark G4** [D02]. Satu VM adalah single point of failure; karena autentikasi pelanggan bergantung pada RADIUS pusat, ketersediaan RADIUS termasuk bagian readiness (bagian 9, RAD-08).

---

# 7 Onboarding VPN dan API

**NET-01** WireGuard pada RouterOS v7 adalah transport utama. Satu peer per router; alamat tunnel unik /32 dari pool deploy (default `100.127.0.0/16`, konfigurasi; bootstrap memeriksa overlap pada router dan berhenti dengan alasan); registry alamat terpusat. Peer pada router hanya mengizinkan **/32 server** (bukan `0.0.0.0/0`, bukan LAN tenant). [S03]

**NET-02** Router memulai tunnel ke server; keepalive 25 detik hanya bila di balik NAT. Uji MTU, UDP diblokir, gateway berubah, endpoint server tidak tersedia. Kegagalan UDP ditampilkan; fallback bukan membuka API plaintext. RouterOS v6 tidak di-upgrade otomatis; statusnya **hanya baca** dan tidak didukung untuk mutasi maupun cutover RADIUS [D03]. Perubahan status dukungan v6 hanya melalui instruksi eksplisit pemilik produk + ADR.

**NET-03** Bootstrap: token enrollment berumur pendek (default 15 menit, maksimum 60), sekali pakai, satu router, satu tenant, tersimpan hanya sebagai hash. Skrip bernamespace `rtrw` (templat pada `Playbook_RouterOS_v2_1.md`) membangkitkan private key WireGuard dan kredensial API **di router**; hanya public key, sidik jari sertifikat API, dan kredensial (sekali, HTTPS ber-token) dikirim ke server. Skrip memvalidasi enrollment sebelum langkah berhak tinggi, mendeteksi konflik nama/subnet, dan berhenti dengan alasan. Hanya menambah akses manajemen minimum setelah review; tidak reset, reboot, mengganti default route, DHCP, DNS, atau bridge. Penghapusan hanya objek milik platform.

**NET-04** Native API-SSL dan REST HTTPS adalah adapter berbeda [D03]. **Default: native API-SSL dengan sertifikat dipin** (sidik jari SHA-256 disimpan pada tahap `api_verified`; ketidakcocokan ditolak; `verify=false` dilarang; layanan api-ssl dibatasi /32 server). REST HTTPS: alternatif, mati default, bounded calls, pin sama. Data string RouterOS dinormalisasi dengan validator tipe. Credential router tidak pernah ke browser. [S01, S02]

**NET-05** Mode enrollment: **read-only** (default; akun `rtrw-mon`) atau **manage** (menambah `rtrw-mut` untuk cutover RADIUS, pengelolaan objek bernamespace, backup, dan Disconnect/CoA terkait). Peningkatan mode memakai skrip pendek bertoken baru. Akun migrasi sementara `rtrw-mig` (policy `sensitive` hanya untuk panen password) dibuat hanya oleh skrip peningkatan khusus dengan persetujuan Owner, berumur ≤ 24 jam, dan dihapus setelah panen. Akun dan grup menggunakan custom group RouterOS dengan policy minimum yang dibuktikan lab; health check membedakan tunnel, API, autentikasi, izin, kompatibilitas.

**NET-06** Endpoint UDP WireGuard server reachable dari router. Firewall server (nftables, tabel khusus, dimuat atomik dan dipulihkan setelah reload) menerapkan **default-deny**: tolak forwarding peer-ke-peer; peer hanya boleh mencapai dari /32-nya sendiri: port receiver backup, UDP 1812/1813 RADIUS; server dapat mencapai peer pada port API-SSL dan UDP 3799. Tolak akses peer ke DB, queue, metrics, SSH host, metadata (169.254.169.254), loopback, jaringan container; tolak IPv6 pada interface WireGuard kecuali diizinkan eksplisit.

**NET-07** Group bawaan `read` RouterOS dapat memuat hak tambahan; namanya bukan jaminan least privilege. Izin write tidak membatasi per objek; command allowlist backend adalah lapisan tambahan. Kredensial penulis yang bocor tetap berdampak sesuai izin. Daftar policy per fungsi tersimpan di `docs/compatibility.md`. [S18]

**NET-08** Token mengotorisasi registrasi server; bukan pengaman universal skrip offline. Server menolak peer tak terdaftar/revoked; kredensial sementara dirotasi setelah sukses. Skrip yang disalin tetap sensitif. Expiry tidak menghapus objek lokal. Revoke token, peer, akun API, dan klien RADIUS adalah tindakan berbeda.

**AC-NET:** router di balik NAT tersambung setelah bootstrap; ulang skrip tidak menambah objek; trafik tenant A ke peer B dan jaringan internal ditolak; route default dan sesi existing tidak berubah; token lama tidak mendaftarkan router tambahan; private key dan secret RADIUS tidak terlihat di error/log/export; uji UDP tertutup, probe lintas peer dan port internal, token expired/replay, reload firewall, rename router saat job berjalan, akun migrasi terhapus setelah panen.

---

# 8 Discovery akun dan profile existing

**IMP-01** Discovery memakai operasi baca dengan properti minimum. Objek: PPP secrets/profile/active, PPPoE server, Hotspot user/profile/server/active, pools, queue relevan, firewall filter (hanya deteksi FastTrack), IP/interface, konfigurasi RADIUS/`ppp aaa` yang ada, script/scheduler terkait. **Discovery tidak membaca password**; pembacaan password adalah langkah migrasi terpisah (bagian 9). Batasi ukuran, waktu, frekuensi (read timeout 15 detik; tidak lebih dari satu discovery per router bersamaan).

PPP secret dapat dipakai layanan selain PPPoE: hanya `service` pppoe atau `any` yang dapat dimigrasikan; `any` ditinjau; layanan lain (l2tp, sstp, ovpn, dll.) dan akun administrator RouterOS tetap lokal dan dilabeli `unmanaged`. Sesi aktif adalah data runtime, bukan daftar akun. RADIUS eksternal yang sudah ada tidak dapat direkonstruksi dari sesi aktif; akunnya masuk jalur impor eksternal (RAD-09 S4). [S06, S07]

**IMP-02** Hasil disimpan sebagai snapshot discovery bertimestamp dan versi adapter, status `discovered, selected, adopted, ignored, conflict, stale`. Tampilkan jumlah per tipe/profile, enabled/disabled, akun tanpa pemetaan, duplikat lintas router, dampak kuota. Profile dibaca tanpa otomatis menjadi paket komersial.

**IMP-03** Wizard adopsi dan migrasi (8 langkah): **Sumber → Pilih/filter akun → Gabungkan identitas lintas router → Petakan pelanggan → Petakan profile/paket → Sumber password → Validasi dan tinjau → Simpan**; lalu laporan. Commit adopsi **database-only**: membuat `access_account`, `Service`, proyeksi `radius.*`, dan jejak sumber; tidak menulis akun, profile, comment, scheduler, atau firewall ke router. Automation isolir/penagihan `automation_enabled=false` sampai data lengkap, simulasi ditinjau, dan policy diaktifkan.

**IMP-04** Satu akun = satu service. Bila identitas bisnis belum ada, label pelanggan sementara = username. Penggabungan beberapa service ke satu customer wajib ditinjau; kemiripan nama/MAC/telepon tidak cukup. Identitas objek router = tenant + router + tipe objek + referensi terverifikasi; `.id` hanya handle lokal. **Identitas akses** (username) unik **per tenant** dan sama pada seluruh router tenant [DATA-01].

**IMP-05** Profile default tidak diubah massal. Comment dan on-login/on-logout dibaca sebagai data tidak tepercaya, tidak dieksekusi. Format Mikhmon/operator lain memerlukan adapter versi khusus yang menunjukkan hasil parsing untuk konfirmasi; tidak menebak tunggakan dari comment.

**FastTrack vs Queue (final)** [S04]: discovery membaca aturan FastTrack. Bila aturan `fasttrack-connection` dapat mencakup trafik PPPoE/Hotspot sementara kecepatan diatur lewat `rate-limit`/antrean, capability `fasttrack_may_bypass_queue=true` dan peringatan tampil pada pemetaan paket. **Platform tidak mengubah FastTrack atau firewall pelanggan pada R1–R3**; remediasi oleh operator dan diuji lab (TK-508). Pada R4 templat hanya menambah pengecualian untuk objek miliknya setelah lulus lab.

**AC-IMP:** fixture 50 PPPoE, Hotspot, profile bersama, secret non-PPPoE, akun disabled, RADIUS eksternal, username sama pada dua router. Impor dua kali tanpa duplikasi; tidak mengubah export konfigurasi router (setelah normalisasi field volatil); tidak memutus sesi; kuota diperiksa atomik; akun di luar pilihan tetap tidak dikelola.

---

# 9 Identitas akses, RADIUS, dan migrasi

Rincian normatif: `Spesifikasi_RADIUS_dan_Migrasi_v2_1.md`. Ringkasan kebutuhan:

**RAD-01** Seluruh akun PPPoE dan Hotspot terkelola berada pada **basis RADIUS per perusahaan** (FreeRADIUS + `rlm_sql` PostgreSQL), dibagi oleh seluruh router perusahaan. Server RADIUS hanya mendengarkan alamat tunnel; satu klien NAS per router dengan secret unik.

**RAD-02** Sumber kebenaran adalah `access_account` pada database aplikasi; tabel `radius.*` adalah proyeksi yang ditulis hanya oleh service layer dalam transaksi yang sama. Username unik per tenant, case-sensitive, tidak terikat router.

**RAD-03** Tenant ditentukan dari klien NAS (router), bukan dari username; seluruh kueri RADIUS memfilter tenant. Username yang sama pada dua tenant tidak saling terlihat.

**RAD-04** Atribut balasan berasal dari paket dan binding router: kecepatan (`Mikrotik-Rate-Limit`), pool (`Framed-Pool`, per router), IP statis, interim accounting, batas sesi/data, masa berlaku, `Simultaneous-Use` (default 1), kunci MAC opsional. Kecepatan paket tidak bergantung pada profil router.

**RAD-05** Password layanan tersimpan terenkripsi; proyeksi RADIUS memuat nilai asli karena protokol PPPoE (PAP/CHAP/MS-CHAPv2) memerlukannya; dikendalikan lewat role, jaringan, backup terenkripsi, dan pelarangan muncul pada log/export/audit. Secret RADIUS per router unik; `Message-Authenticator` wajib.

**RAD-06** Penegakan: isolir penuh = `Auth-Type := Reject` + Disconnect-Request; aktivasi memulihkan atribut; isolir terbatas opsional (R3) memerlukan templat router milik operator; perubahan paket memakai update atribut + CoA/Disconnect.

**RAD-07** Accounting RADIUS menjadi sumber status koneksi dan penggunaan data; sesi basi dibersihkan; retensi mentah 90 hari, agregat harian 400 hari.

**RAD-08** Ketersediaan: dua alamat RADIUS pada router (primer, sekunder), HA lokal pada G4, edge replica opsional (R3), runbook rollback. Sesi yang sudah terbentuk tetap berjalan saat RADIUS tak terjangkau; sambungan baru mengikuti perilaku yang dirancang dan diuji (T22).

**RAD-09 Migrasi akun existing**: (A) discovery dan adopsi database-only dengan penggabungan identitas lintas router dan sumber password (S1 baca dari router lewat akun migrasi sementara, S2 CSV, S3 password baru, S4 impor RADIUS eksternal); (B) cutover per router.

**RAD-10 Cutover RADIUS per router** (operasi terpisah, hanya mode `manage`): preflight dan backup → uji paritas server-side → pasang klien RADIUS bernamespace → canary → aktifkan penuh → mode otoritatif (menonaktifkan secret lokal ber-ownership per batch) → rollback tersedia. `enforcement_mode`: `local`, `radius_shadow`, `radius_authoritative`, `degraded`. Isolir otomatis, kecepatan berbasis paket, dan perpindahan antarrouter hanya dijamin pada `radius_authoritative`.

**RAD-11** Perpindahan pelanggan antarrouter dan penggantian router tidak memerlukan input ulang data pengguna; `allowed_router_ids` opsional membatasi akun; IP statis berbeda subnet memakai override per router.

**RAD-12** Hotspot dan voucher memakai RADIUS (bagian 14).

**RAD-13** Keamanan RADIUS: tidak ada listener publik, secret per router, log autentikasi tanpa password, insiden pada lonjakan kegagalan, rotasi secret tercatat.

**RAD-14** Pengujian T16–T22 (bagian 26).

**DATA-01** Semua objek tenant memiliki `tenant_id`. `RouterObjectMapping` menyimpan router, object_type, external_handle, natural key, fingerprint, last_seen, generation. **Identitas akses unik per (tenant, username)**; `RouterObjectMapping` (per router) menjadi jejak sumber migrasi dan pencocokan drift, bukan identitas bisnis. **DATA-02** UUID internal; UTC; uang `numeric(20,2)`; bandwidth integer bit/s; soft archive tidak menghapus invoice/jurnal; penghapusan PII mengikuti retensi dan UU PDP (bagian 24).

---

# 10 Profile, paket, dan sinkronisasi

**PRO-01** `TechnicalProfile` = konfigurasi router (pool, alamat lokal, DNS, MSS; pada Hotspot profil server). `CommercialPackage` = nama jual, harga, periode, **kecepatan (rx/tx bit/s dengan burst opsional)**, batas data/FUP, `first_period_policy`, kebijakan. `PackageRouterBinding` = paket ke profil/pool per router. Kecepatan dikirim lewat RADIUS dari paket, sehingga mengubah paket tidak mengubah profil router. Nama profile tidak menjadi harga atau periode otomatis. Owner dapat memetakan seluruh akun satu profile ke paket sekali; binding menyimpan versi/hash profile yang ditinjau. Atribut profil tidak didukung tetap terlihat pada detail teknis.

**PRO-02** Edit **profil router** (pool, alamat lokal, DNS) hanya melalui alur terkontrol (R4) dengan analisis dampak: jumlah akun managed (RADIUS) dan unmanaged (lokal) yang merujuk profil. Bila unmanaged terdampak, edit langsung diblokir; default membuat profil baru. Perubahan **kecepatan** dilakukan pada paket (atribut RADIUS) dengan efek pada sesi berikutnya atau segera melalui CoA/Disconnect; tidak dijanjikan penerapan live universal. FastTrack dapat melewati antrean sehingga efektivitas wajib diuji. [S04]

**SYNC-01** Pisahkan desired state, observed state, dan provenance per field. Identitas dan atribut akses berasal dari aplikasi (RADIUS); kondisi sesi dari accounting; konfigurasi router tetap observed kecuali objek bernamespace milik platform. Perubahan manual via WinBox ditampilkan sebagai drift. Deteksi drift: scan penuh default tiap 6 jam, on-demand, dan preflight tiap write. Drift yang dipantau khusus: klien RADIUS atau `use-radius` hilang (`radius_client_missing`, mode turun ke `degraded`), secret/user lokal baru pada router otoritatif (`local_account_shadow`, diusulkan adopsi atau dinonaktifkan atas persetujuan), profil/pool yang dirujuk binding hilang (`binding_invalid`).

**SYNC-02** Akun yang hilang pada router tidak memengaruhi akun RADIUS (identitas milik tenant). Objek router yang hilang ditandai `missing_source`; akun baru di router masuk daftar belum diadopsi; rename, restore router, perubahan `.id`, profile hilang memicu pemeriksaan mapping (jenis, router, identifier, fingerprint; review bila ambigu). Akun dinonaktifkan manual di luar aplikasi: `hold_unknown` sampai ditinjau.

**SYNC-03** Setiap job router menyimpan expected configuration revision; kondisi berubah → `conflict` (tidak menimpa). Write timeout = `uncertain`; baca ulang sebelum retry; retry add memeriksa objek yang mungkin sudah dibuat.

**AC-PRO / AC-SYNC:** perubahan kecepatan paket diterapkan ke seluruh akun paket tanpa mengubah profil router; edit profil router yang dipakai 100 akun menunjukkan seluruh dampak; clone tidak mengubah 90 akun di luar seleksi; putus respons setelah router menulis tidak menggandakan objek; restore router yang mengubah `.id` tidak menghubungkan invoice ke pelanggan lain.

---

# 11 Pelanggan, siklus layanan, dan impor CSV

**CUS-01** Form ringkas: nama/label, router (opsional; default semua router tenant), tipe layanan (PPPoE/Hotspot), paket, kebijakan mulai layanan; kontak boleh menyusul. Pilihan akhir (masing-masing menyatakan apakah menulis router): **Simpan draft** (tidak menulis), **Hubungkan akun existing** (database-only), **Buat akun** (membuat `access_account` + proyeksi RADIUS; tidak menulis router; efektif pada router berstatus `radius_authoritative`), **Buat dan aktifkan**. Username unik per tenant; password dibangkitkan aman (CSPRNG, 16 karakter). MAC dan IP opsional.

**Kebijakan kredensial layanan**: password baru tampil **sekali** kepada aktor berizin; tersimpan terenkripsi; tampil ulang oleh pemegang `services.reveal_credentials` dengan reautentikasi, audit, auto-sembunyi 30 detik; tidak ada di tabel, log, analytics, export, pesan error. Password existing tidak berubah saat kosong; rotasi aksi terpisah dengan peringatan dampak CPE (ACS-06).

**CUS-02** Data pelanggan tersimpan walau provisioning gagal. Lifecycle service: `draft, pending, provisioning, provisioned, conflict, failed, terminated, archived` [C10]; dimensi lain (billing, isolasi, jaringan, koneksi, job) terpisah (bagian 23). UI memberi remediasi, bukan meminta membuat pelanggan ulang.

**LIF-01 Siklus pelanggan end-to-end**: `prospect → survey → scheduled_install → installed → active → suspended → terminated`, dengan `churn_reason`; prospek dan work order instalasi pada R3, sedangkan `active/suspended/terminated` mengikuti dimensi service sejak R1. **LIF-02** Instalasi: biaya instalasi, deposit perangkat, perangkat dipinjamkan, checklist teknisi, foto, aktivasi layanan setelah instalasi diverifikasi. **LIF-03** Berhenti: tanggal efektif, penghitungan tagihan akhir, pengembalian perangkat/deposit, arsip. **LIF-04** Pindah paket/pindah lokasi/pindah router dicatat sebagai perubahan dengan histori; pindah router tidak memerlukan input ulang (RAD-11).

**CSV-01** Template UTF-8 (BOM diterima), kamus kolom, contoh sintetis, daftar kode router/paket tenant. Satu baris = satu layanan; `customer_code` sama boleh punya `service_code` berbeda. Mode **create / enrich imported / update / device mapping / password migrasi (S2)** dipilih eksplisit; versi skema template tercantum.

| Kolom | Aturan |
|---|---|
| customer_code, customer_name | Kode stabil atau dibangkitkan; nama wajib untuk baru |
| service_code, service_type | `pppoe` atau `hotspot`; wajib sesuai mode |
| username, package_code | Username unik per tenant; paket divalidasi |
| password | Hanya mode create/password migrasi; terenkripsi; dihapus dari staging |
| router_code | Opsional (pembatasan router); milik tenant |
| phone, email, address | Opsional; phone teks, normalisasi E.164 untuk pencocokan |
| start_date, due_day, paid_through_date | ISO date; `due_day` 1–31 dengan clamp akhir bulan; paid-through hanya data migrasi yang direview |
| static_ip, mac_lock | Opsional; cek konflik |
| device_serial, device_oui, product_class | Opsional; tidak mengesahkan kepemilikan |
| wan_mac, location_code, odp_code, odp_port | Opsional; normalisasi tanpa menghapus nilai asli |
| language | `id`/`en`/lainnya yang tersedia; bahasa komunikasi pelanggan |

**CSV-02** Staging tidak mengubah router dan tidak menulis ke RADIUS. Validasi per baris, preview create/update/no-change/conflict/error, cek kuota, lalu commit batch terpilih (commit menulis `access_account` dan proyeksi RADIUS). Upsert memakai kode eksplisit; kosong mempertahankan data kecuali penanda clear-field. Kesalahan memberi nomor baris dan alasan tanpa password. Upload ulang dikenali via key baris + hash batch.

**CSV-03** CSV bukan skrip. Output di-escape terhadap formula spreadsheet; input tidak diteruskan ke CLI. **Batas final** [C01, N01]: **10 MiB dan 10.000 baris, keduanya berlaku**; konfigurasi dengan plafon keras 20 MiB / 20.000 baris, dinaikkan hanya setelah uji beban. Proses streaming/chunk; file sementara TTL 24 jam. Impor tidak menghasilkan jurnal, pembayaran, atau isolir.

**AC-CSV:** leading zero telepon terjaga; koma dalam alamat; baris gagal tidak merusak baris lain; preview lintas tenant ditolak; unggah ulang tidak menggandakan; username duplikat dalam tenant ditolak; password tidak muncul pada laporan.

---
# 12 Billing internet dan penagihan

**BIL-01** Invoice: line item, service period, due date, currency IDR, nominal, discount, tax configuration, outstanding. Status invoice internet: `draft, open, partial, paid, void`, terpisah dari payment submission. Unik (tenant, service, periode, jenis) mencegah scheduler ganda. Harga disnapshot; perubahan harga paket tidak mengubah invoice lama. Nomor dokumen unik per tenant dan jenis (`INV-{kode_tenant}-{YYYYMM}-{urut}`), namespace berbeda dari invoice SaaS. Dokumen memuat bahasa terbit (I18N-04).

**BIL-02** Kebijakan penagihan per paket: siklus `fixed_monthly` (periode = bulan kalender) atau `anniversary` (aturan jangkar SUB-04). `due_day` hanya berlaku pada fixed_monthly, memilih tanggal clamp pertama pada/selepas due default (AUD-29); waktu `prepaid` atau `postpaid`; `first_period_policy` (`full`, `prorata_daily`, `free_until_next_period`; default `full`) [N18]. Default: prepaid diterbitkan 7 hari sebelum periode mulai dan jatuh tempo pada tanggal mulai periode; postpaid diterbitkan pada akhir periode dan jatuh tempo 7 hari sesudah terbit (konfigurasi). Masa kalender, uptime Hotspot, dan kuota byte adalah konsep berbeda.

**BIL-03** Pembayaran diterima manual: transfer/e-wallet (bukti → verifikasi dana), tunai langsung, atau **tunai melalui kolektor/agen** (COL-01). Bukti upload bukan posted payment. Verifikasi dana membuat transaksi + allocation ke satu/lebih invoice; mendukung partial payment dan unallocated credit. Pembayaran SaaS dan pembayaran internet memakai namespace dan rekening berbeda; rekening tujuan pembayaran internet adalah milik tenant.

**BIL-04** Migrasi: batch opening balance dengan tanggal cutover; paid-through dan tunggakan dari CSV wajib review; hanya saldo piutang pembuka per pelanggan yang dijurnal (tanpa menjurnal invoice historis). Owner menerima ringkasan saldo pembuka sebelum automation aktif.

**BIL-05** Refund, diskon susulan, write-off, pembatalan layanan, dan deposit memiliki dokumen koreksi, otorisasi, audit. Aktivasi berbeda dari perpanjangan periode. "Sudah bayar" selalu terkait invoice/periode yang difilter.

**BIL-06 Pengingat dan penagihan (dunning)**: jadwal pengingat per tenant (mis. H-3, H, H+3; konfigurasi) dengan templat per bahasa; pengiriman nyata hanya setelah Owner mengaktifkan kanal (OPS-05); pengingat dihentikan otomatis saat lunas.

**BIL-07 Promo dan biaya tambahan**: diskon (nominal/persen, masa berlaku, kode), biaya instalasi, add-on (IP publik statis, perangkat sewa), paket multi-layanan per pelanggan; semua tersnapshot pada invoice.

**BIL-08 Kwitansi dan dokumen**: kwitansi pembayaran dan invoice dapat dicetak/PDF dalam bahasa dokumen; nomor kwitansi unik; e-meterai atau materai ditangani sebagai lampiran/opsi tenant bila diperlukan.

## Aturan pada kondisi gangguan

Pembayaran sah tetap tercatat saat router offline atau RADIUS terputus; service menjadi `paid-awaiting-activation` (label turunan). Keputusan finansial disimpan dalam transaksi DB; job lewat outbox. Timeout browser setelah submit mengembalikan hasil transaksi yang sama via idempotency key. Pembayaran yang disahkan menghalangi job isolir lama yang belum berjalan; pembukaan isolir tetap menunggu aksi admin.

**AC-BIL:** dua scheduler pada periode sama → satu invoice; partial payment tidak lunas; satu payment dialokasikan tidak lebih dari nilainya; harga baru tidak mengubah invoice issued; 29/30/31, tahun kabisat, batas zona waktu WIB/WITA/WIT; prorata deterministik.

**COL-01 Kolektor dan agen penagih**: akun kolektor (bundel terbatas) mencatat penerimaan tunai per pelanggan; saldo kolektor berjalan sampai **setoran** diverifikasi pengelola; selisih ke akun selisih kas dengan persetujuan; laporan saldo kolektor per orang dan umur. **COL-02** Pembayaran via kolektor menghasilkan kwitansi bernomor dan tampil sebagai "diterima kolektor, belum disetor". **COL-03** Rute penagihan dan daftar tunggakan per area dapat diekspor tanpa data sensitif.

---

# 13 Isolir dan aktivasi massal

**ACT-01** Kebijakan: isolir otomatis sesudah due date + grace (**default grace 3 hari**, rentang 0–30, per tenant) [D05]. **Policy isolir default nonaktif per tenant**; layanan hasil migrasi `automation_enabled=false`. Sebelum mengaktifkan, Owner menjalankan **simulasi** "siapa yang akan diisolir" (ID simulasi berlaku 24 jam) dan meninjau paket, due date, saldo pembuka. Isolir otomatis hanya bagi layanan pada router `radius_authoritative`. Aktivasi (pembukaan) selalu manual oleh Owner/Admin Pembayaran (atau delegasi).

**ACT-02** Scheduler hanya membuat kandidat (harian 01:00 zona tenant dan saat perubahan due/payment). Worker mengunci scope service, membaca payment dan policy terbaru, memeriksa exemption, termination, hold, dan observed state. Job memuat `policy_version`; bila policy berubah/dimatikan sebelum eksekusi, job `cancelled` (`policy_changed`); scheduler menilai ulang.

**ACT-03 [REVISI AUD-24–25]** Suspend melalui Reject+Disconnect dan bukti positif sesi menurut kontrak v2.1 §12. Absennya interim60detik tidak membuktikan sesi terputus pada interval300detik. Auth test harus menggunakan transport/secret yang sah dan Reject karena policy target. Restore wajib Accept dengan atribut normal; verified_active tidak berarti perangkat sudah online. Semua sesi target lintas NAS/jalur terkelola dan kontrol non-target diperiksa.

**ACT-04** Isolir terbatas (walled garden/halaman pembayaran) tersedia opsional pada R3 melalui pool dan address-list isolir yang membutuhkan aturan router milik operator (templat tersedia); platform tidak membuat aturan itu diam-diam. HTTPS arbitrer tidak dijanjikan redirect. IPv4-only tidak diklaim memblokir IPv6; dual stack diuji.

**ACT-05** Bulk activation: snapshot pilihan → ringkasan → validasi hak/pembayaran → job anak per service → verify → hasil per item. Akun `security_hold`/`technical_hold`/`manual_hold` tidak dibuka hanya karena invoice lunas (override butuh izin + alasan). Simpan alasan isolir; aktivasi hanya membalik perubahan isolir milik aplikasi yang revision-nya masih cocok.

## Kondisi balapan

| Kejadian | Hasil |
|---|---|
| Lunas sebelum scheduler | Tidak ada kandidat |
| Lunas sesudah enqueue, sebelum eksekusi | Preflight membatalkan job lama |
| Lunas saat eksekusi berjalan | Uang dicatat; rekonsiliasi; `paid-awaiting-activation` bila terlanjur isolir |
| Lunas saat router/RADIUS terputus | Uang sah; perubahan atribut RADIUS tetap tercatat; Disconnect/aktivasi menunggu router (`waiting_dependency`) |
| Aktivasi dua kali | Satu logical action; periode tidak diperpanjang dua kali |

Perubahan status akun RADIUS adalah transaksi database (atomik dengan keputusan bisnis); Disconnect/CoA adalah langkah job terpisah. Kompensasi terdefinisi, audit tersimpan. **AC-ACT:** payment sebelum enqueue, sesudah enqueue, saat eksekusi, router timeout setelah Disconnect, restart worker, retry ganda, IPv6, manual hold, router berstatus `radius_shadow` (isolir tidak dijamin dan UI menyatakannya).

---

# 14 Hotspot, voucher, dan reseller

**HSP-01** Hotspot memakai RADIUS (autentikasi pengguna, MAC-auth opsional, accounting). Hotspot user hasil adopsi menjadi `access_account` kind `hotspot`; setiap user terkelola = satu unit kuota. **HSP-02 Voucher (R3)**: batch voucher dengan paket (durasi, batas data, kecepatan, masa berlaku), kode acak, cetak/ekspor; atribut RADIUS `Session-Timeout`, `Max-All-Session`, `Mikrotik-Total-Limit`, `Mikrotik-Rate-Limit`, `Expiration`. Voucher yang diterbitkan dan masih valid dihitung dalam kuota (SUB-01); penerbitan batch mereservasi kuota atomik. **HSP-03** Pencabutan, perpanjangan, dan penggantian voucher memiliki jejak audit; voucher kedaluwarsa tidak dihitung.

**AGT-01 Agen/reseller**: akun agen (bundel terbatas) membeli/menjual voucher dengan harga agen dan komisi; portal agen menampilkan stok, penjualan, komisi, setoran. **AGT-02** Penjualan agen mengikuti kebijakan pengakuan pendapatan voucher (`Panduan_Akuntansi_ISP`, bagian 6); komisi sebagai utang komisi sampai dibayar. **AGT-03** Batas jumlah agen per paket (TEN-02).

**HSP-04** Hotspot + PCC pada satu router tidak didukung (bagian 20). Hotspot + single WAN atau failover didukung setelah lab login, walled garden, return traffic, dan failover lulus. **HSP-05** FUP/kuota data berbasis accounting RADIUS (R3): batas harian/bulanan, aksi saat terlampaui (turunkan kecepatan melalui atribut, atau isolir sesuai kebijakan paket), diuji dengan counter dan Disconnect/CoA; bukan dasar penagihan uang kecuali paket berbasis kuota diaktifkan dan diuji.

**AC-HSP:** batch voucher mereservasi kuota; voucher dipakai pada dua router tenant yang sama tetap satu sesi (`Simultaneous-Use`); kedaluwarsa menolak login; kuota data habis memicu aksi kebijakan; penjualan agen menghasilkan komisi dan jurnal benar.

---

# 15 Akuntansi dan kontrol transaksi

Rincian: `Panduan_Akuntansi_ISP_v2_1.md`. **ACC-01 Double-entry ledger** [D09, N09]: setiap perusahaan memiliki buku terpisah (COA, fiscal period, opening balances, journal entry/lines, subledger). **Setiap entry seimbang: jumlah debit = kredit lintas semua baris**, satu tenant, mata uang IDR, satu periode. Uang `numeric(20,2)`; tanpa float; multi-currency di luar cakupan. Buku platform terpisah (cakupan `platform`) untuk pendapatan SaaS; tidak tampil pada buku tenant dan tidak dilihat Super Admin biasa. Kerangka default **SAK EMKM** (dapat SAK Entitas Privat) dengan `FrameworkVersion` dan tanggal efektif; aplikasi membantu penerapan, tidak menyatakan kepatuhan otomatis. [S14, S15]

**ACC-02 Pengakuan pendapatan**: invoice tidak selalu berarti pendapatan. Bukti belum terverifikasi tidak menjurnal Bank. Templat posting berversi dengan `source_document_id` dan event key unik. Prabayar: invoice belum dibayar tidak dijurnal; pembayaran → pendapatan diterima di muka → pengakuan harian diposting bulanan (sisa pembulatan ke periode terakhir); pascabayar: piutang dan pendapatan saat terbit pada akhir periode; selisih lebih = kredit pelanggan (bukan pendapatan). Voucher mengikuti kebijakan tenant. Contoh dan akun: panduan bagian 3 dan 6.

**ACC-03** Penerimaan: transfer/e-wallet, tunai, kolektor (akun clearing, setoran), biaya payment fee, alokasi lintas invoice. **ACC-04** Piutang: aging, cadangan kerugian opsional, write-off dengan dokumen koreksi. **ACC-05** Voucher/agen: pendapatan diterima di muka, komisi sebagai utang. **ACC-06** Perangkat/persediaan/aset: klasifikasi menurut tujuan, ambang kapitalisasi (default Rp2.500.000), rata-rata bergerak, penyusutan garis lurus (umur default 4 tahun), disposal; pajak sebagai konfigurasi (`TaxRule`) tanpa tarif universal hardcode.

**ACC-07 Rekonsiliasi bank/e-wallet**: impor mutasi (CSV terkonfigurasi) dengan kunci unik, pencocokan, split/merge, exception; saldo statement ≠ saldo buku. **ACC-08 Tutup periode** (bulanan, tahun): daftar periksa, kunci, reversal/adjustment, reopen dengan permission+reautentikasi+alasan, tidak melintasi tutup tahun. **ACC-09** Saldo pembuka. **ACC-10** Laporan (bagian 16). **ACC-11 Penegakan teknis**: role runtime tanpa INSERT/UPDATE/DELETE pada tabel jurnal; prosedur `ledger.post_entry` (SECURITY DEFINER) dengan period lock; constraint trigger deferred debit=kredit; trigger immutability (TD §10). **ACC-12** Buku platform.

**AC-ACC:** retry payment dan recognition bulanan tidak menggandakan jurnal; total debit = kredit; prabayar tidak memperbesar pendapatan sebelum jadwal; transfer internal bukan pendapatan; setoran kolektor dengan selisih; split match; bypass direct-write ditolak; templat posting ditinjau tenaga akuntansi sebelum laporan resmi (G2).

---

# 16 Laporan keuangan dan rekonsiliasi

| Laporan | Isi dan kontrol |
|---|---|
| Kas dan bank | Saldo awal, mutasi, saldo akhir per akun |
| Penerimaan harian | Per metode, rekening, kolektor |
| Arus kas | Operasi, investasi, pendanaan; rekonsiliasi kas |
| Laba rugi | Pendapatan/beban periode (akrual), komparatif |
| Posisi keuangan | Aset, liabilitas, ekuitas pada tanggal tertentu |
| Aging piutang | Umur 0–30, 31–60, 61–90, >90 hari; per pelanggan/paket/router/kolektor |
| Utang usaha dan komisi | Pemasok, agen, jatuh tempo |
| Buku besar/neraca saldo | Drill-down ke dokumen sumber |
| Pendapatan diterima di muka | Jadwal pengakuan |
| Aset dan penyusutan | Biaya, akumulasi, nilai buku |
| Pendapatan per paket/router/area | Dimensi analitik |
| Pajak (bila aktif) | Rekap DPP dan pajak |
| Catatan laporan | Kebijakan dan penjelasan |

SAK EMKM mensyaratkan minimum laporan posisi keuangan, laba rugi, dan catatan atas laporan keuangan dengan informasi komparatif [S16]; label "patuh standar" tidak dipakai tanpa melengkapi syarat kerangka. Laporan memuat periode, basis, waktu generasi, status penutupan; dari saldo pembuka belum disetujui berlabel "Belum final". Export dengan periode dan waktu generasi; Super Admin tidak melihat buku tenant.

**AC-REPORT:** total subledger piutang = control account setelah rekonsiliasi; periode tertutup menolak posting mundur; refund memiliki tautan sumber; laba berbeda dari kas bila ada prabayar/piutang; laporan lintas dimensi menjumlah ke total yang sama.

---
# 17 Monitoring dan pengelolaan insiden

**MON-01** Koleksi dibagi: health router, interface traffic, status sesi (dari accounting RADIUS), WAN probes, jobs, ACS last inform, kesehatan RADIUS. Akun baca dan bounded calls. REST bukan streaming monitor. Setiap metric membawa `source`, `observed_at`, `collected_at`, `unit`, `quality`. [S01]

**MON-02** Parameter terkunci (konfigurasi; target uji, bukan janji realtime) [C15]: health/traffic 60 detik; inventaris 15 menit; **detail router 15 detik** hanya saat halaman dibuka, dalam budget, dengan shared cache. Jitter, backoff, deadline, dan kuota per tenant mencegah overload. Sample `stale` bila usia > 3× interval. SNMPv3 baca-saja opsional.

**MON-03** Counter delta menangani restart/wrap dan interface berubah. Gap tetap gap, bukan nol. WAN dan LAN tidak dijumlah ganda. Traffic interface bukan dasar billing byte. Pemakaian data per layanan berasal dari accounting RADIUS (RAD-07). Metrik per pelanggan (high-cardinality) tidak masuk Prometheus; data per layanan tinggal di PostgreSQL (`usage_daily`).

**MON-04** Probe tiap ISP dipaksa pada jalurnya; ping sukses lewat ISP lain tidak membuktikan ISP target sehat. Minimal 2 target independen per ISP; debounce down setelah 3 kegagalan berturut-turut, up setelah 5 sukses (konfigurasi, divalidasi lab). Health server-ke-router ≠ pengalaman pengguna akhir.

**MON-05** Insiden: sumber, severity, start/end, resource, evidence, acknowledgement, owner, maintenance window. Status router: `healthy`, `degraded`, `management_unreachable` (3 polling gagal berturut-turut), `unmonitored`, `stale`. Status RADIUS per router: sesi masuk/keluar, rasio autentikasi gagal, accounting terakhir; lonjakan kegagalan memicu insiden. Dampak ke layanan dikorelasikan hanya bila topologi tersedia. **Kegagalan collector = insiden platform ("data tidak tersedia")**, bukan ribuan router down. Notifikasi dedup (tenant+resource+signal), rate limit, recovery notice sekali per transisi.

**MON-06** Dashboard owner menggabungkan jaringan dan pekerjaan bisnis tanpa mengungkap destination browsing. Packet capture, torch massal, speed test yang menyaturasi ISP, dan connection table penuh bukan polling default. Grafana opsional internal dengan otorisasi query tenant; tenant tidak memperoleh datasource global.

**AC-MON:** restart router tidak menghasilkan traffic negatif/spike fiktif; collector mati → stale; satu uplink putus diuji dari jalur benar; kegagalan NTP terdeteksi; tenant tidak membaca metrik tenant lain; data expired dihapus sesuai retensi; sesi hilang akibat RADIUS terputus dibedakan dari pelanggan offline.

---

# 18 Backup dan pemulihan MikroTik

**BKP-01** Jadwal tenant: router, harian/mingguan/custom, timezone, notifikasi, jenis file. Retensi rutin maksimal **100 generasi berhasil per router**. Satu generasi dapat terdiri dari binary + export. Generasi ke-101 menggantikan tertua hanya setelah semua artifact wajib generasi baru tersimpan dan valid. Gagal/partial tidak mengurangi 100 generasi valid. Backup manual dan pre-change masing-masing 10 per router (FIFO per kategori) [N11]. Backup otomatis pre-change dibuat sebelum cutover RADIUS dan sebelum perubahan WAN.

**BKP-02** Binary backup dienkripsi dengan password eksplisit **dibangkitkan platform per router** (32 karakter acak), disimpan terenkripsi (kunci data per tenant dibungkus kunci utama di luar database). Kosong bukan dianggap terenkripsi. Owner memperoleh kunci pemulihan lewat reautentikasi + MFA dengan audit. Binary memuat data sensitif dan MAC; restore ditujukan untuk perangkat/kondisi sesuai. Export tidak memuat rahasia secara default (`show-sensitive` hanya atas pilihan eksplisit Owner) dan bukan backup lengkap. Data pengguna PPPoE/Hotspot berada pada basis RADIUS platform sehingga ikut recovery platform (BKP-05), bukan hanya backup router. [S08, S09]

**BKP-03** Transfer berkas [D04]: API memerintahkan pembuatan file; binary tidak ditransfer via satu respons API. **Baseline: RouterOS Fetch upload SFTP melalui VPN ke receiver terbatas** yang mendengarkan hanya pada alamat tunnel server dengan akun/path scoped per router (rotasi per generasi), tanpa shell dan tanpa path bebas. Kontrol identitas server: tunnel WireGuard terautentikasi dua arah, tujuan dipin /32, verifikasi host-key bila RouterOS mendukung, kredensial tidak muncul di log. **Cadangan**: adapter *pull* (SFTP/SCP dengan host key dipin saat enrollment). Bila keduanya gagal lab (TK-505), backup tidak diaktifkan (G1). **Ukuran maksimum default 64 MiB per artifact**. HTTP fetch bukan baseline untuk binary. [S10]

Generasi: staging → received → size/hash verified → enkripsi + durable storage → committed → perubahan membership retensi → cleanup/prune asinkron. Hash server membuktikan integritas penyimpanan. Sinyal selesai harus terautentikasi dan diverifikasi bersama ukuran.

**BKP-04** Simpan router/model/versi/timezone, type, size, hash, key reference, status, audit unduh. Setelah commit, hapus hanya file sementara buatan aplikasi di router. Unduh terotorisasi; **signed URL 5 menit**, diperiksa saat penerbitan dan penukaran, tidak lintas tenant, tidak dicatat di log.

**BKP-05** Off-host backup platform melindungi database (termasuk skema `radius`), file, key material, metadata, konfigurasi FreeRADIUS, registry VPN, dan datastore ACS. Restore router memerlukan kompatibilitas, dampak reboot, jalur pemulihan, dan persetujuan spesifik; tidak otomatis; **tidak ada tombol restore umum sebelum G1 untuk model/versi tersebut**.

**BKP-06** "100" = generasi rutin retained yang terlihat di katalog setelah finalisasi. Headroom staging `max(5 GiB, 2 × artifact terbesar × transfer bersamaan)`. Watermark disk: peringatan 80%, hentikan backup baru 90%; **backup valid tidak pernah dihapus untuk memberi ruang**. Finalisasi mengubah membership katalog transaksional; penghapusan blob lewat antrean cleanup yang dapat dipulihkan.

**AC-BKP:** generasi 101 menghapus hanya tertua setelah commit; transfer putus tidak menghapus backup valid; disk penuh menghasilkan error; file besar tidak terpotong; akses lintas tenant ditolak; crash antara commit, katalog, dan delete diuji; restore sampel di lab membuktikan prosedur dan keterbatasan.

---

# 19 ACS, TR-069, dan perangkat pelanggan

Rincian: `Spesifikasi_ACS_TR069_v2_1.md` (R3).

**ACS-01** GenieACS (CWMP, NBI, FS, UI internal) dengan MongoDB internal; adapter ACS satu-satunya jalan tenant. CPE harus mendukung TR-069, mengetahui ACS URL/credential, dan punya jalur IP; VPN router tidak mendaftarkan ONT otomatis. NBI/database tidak diekspos. [S11]

**ACS-02** Mapping memakai Device ID internal, DeviceID GenieACS, serial, OUI, product class, plus klaim enrollment tenant terautentikasi. MAC opsional dan bukan bukti kepemilikan. [S12]

**ACS-03** CPE baru masuk karantina. Autentikasi per-device (kredensial unik dari klaim enrollment); accept-any dilarang. Konflik serial/DeviceID ditahan. Tags hanya metadata. [S13]

**ACS-04** Capability per model: read identity, Wi-Fi, associated devices, WAN/PPPoE, diagnostics, reboot, firmware, optical, factory reset, connection request UDP. Model/firmware di luar matriks = `unsupported`. Tidak ada model yang dinyatakan didukung sebelum lulus lab; daftar model pertama ditetapkan oleh hasil G1. Virtual parameter menjembatani TR-098/TR-181; indeks instance ditemukan lewat discovery. Tenant tidak mengirim script/preset arbitrer.

**ACS-05** Status task perangkat terpisah dari job outcome uncertain/recovery_required menurut EXE-02. Tugas asinkron: `queued → waiting_inform → running → verifying → succeeded/failed/expired/cancelled`. API accepted ≠ executed; task ID disimpan sebelum retry; verifikasi lewat pembacaan ulang atau "verifikasi tidak tersedia".

**ACS-06** Rotasi password PPPoE terkoordinasi antara ACS dan RADIUS (alur versi kredensial dengan jalur manajemen independen atau recovery teruji menurut kontrak v2.1 §17); tidak atomik; pemulihan dicatat. Isolir via RADIUS dapat memutus jalur ACS yang berbagi koneksi PPPoE; WAN manajemen/VLAN dirancang operator. Firmware/reboot dijadwalkan; factory reset bukan tombol rutin.

**ACS-07** Inventaris CPE terhubung ke Service dan ODP/port; adapter OLT pada R4 per model. **ACS-08** Keamanan: TLS wajib pada CWMP, rate limit, tanpa kredensial di log. **ACS-09** Matriks kompatibilitas per model. **ACS-10** Pengujian T11.

**AC-ACS:** dua tenant dengan serial konflik tidak bercampur; tugas pending tidak tampil sukses; parameter optik tidak tersedia → "Tidak didukung"; firmware/model salah ditolak; gagal auth CPE tidak menerima kredensial layanan; CPE di belakang NAT diuji dengan dan tanpa UDP connection request.

---

# 20 Wizard jaringan dan uplink (R4)

**CFG-01** Jaringan pelanggan dan uplink adalah menu/wizard independen; menggunakan modul pelanggan tidak mensyaratkan mengubah WAN. Default memakai server PPPoE/Hotspot existing. Membuat bridge, VLAN, DHCP, pool, server PPPoE/Hotspot baru (templat pada `Playbook_RouterOS`) memerlukan pilihan eksplisit, validasi kapasitas/subnet, dependency graph, review. Tidak ada port fisik wajib. Mengubah port pada bridge aktif dianggap berdampak layanan. Templat router baru (penggantian perangkat) membuat pool/profil yang dirujuk binding paket sehingga akun RADIUS langsung dapat login.

**WAN-01** Static WAN: interface, IP/prefix, gateway (prefix wajib). DHCP: baca lease dan perubahan gateway. Overlap subnet modem, gateway sama pada uplink berbeda, PPPoE WAN, VRF, VLAN uplink = `unsupported` sampai templat diuji. DNS tidak ditebak sebagai gateway.

**WAN-02** Mode: single, primary-backup, PCC+failover, weighted PCC. PCC membagi koneksi menurut classifier, bukan bonding per sesi. Bobot dari kapasitas yang diisi owner dengan jumlah bucket wajar. Failover recursive berjalan di router (tidak bergantung server SaaS) dengan multi-target dan hysteresis (MON-04). Trafik RADIUS/VPN ke server harus tetap keluar melalui jalur yang valid saat failover; templat memeriksa rute endpoint VPN. [S05, S17]

**WAN-03** Templat memeriksa local destinations, trafik menuju router, endpoint VPN, NAT, connection marks, routing tables, route balik, DNAT, queue/FastTrack, DNS probes. FastTrack tidak diubah massal; templat hanya menambah pengecualian pada objek miliknya setelah lulus lab. [S04] Sesi existing dapat terputus saat IP publik berubah.

**WAN-04** Aturan topologi terkunci: (a) **Hotspot + PCC pada satu router tidak didukung** (preflight memblokir PCC bila Hotspot server aktif); (b) Hotspot + single WAN atau failover recursive pada main table didukung hanya setelah lab login, walled garden, return traffic, dan failover lulus; (c) PCC hanya untuk router tanpa Hotspot (PPPoE/DHCP) atau topologi gateway terpisah yang lulus lab. [S05]

**CFG-02** Setiap apply menyimpan precondition, planned diff, backup valid, versi templat, ownership, health checks. Kompensasi hanya objek yang diubah dan bila revision masih cocok. Tidak ada global reset, flush conntrack, reboot, atau restore binary sebagai rollback rutin. Safe Mode bukan transaksi API. Kandidat *recovery hook* (skrip+scheduler bernamespace yang mengembalikan objek milik plan setelah TTL kecuali dibatalkan server) aktif hanya bila lulus lab (T13). Koneksi hilang setelah apply → `uncertain`/`recovery_required`. [S09]

**AC-WAN:** gangguan tiap ISP, recovery flapping, DHCP renew, akses VPN dan RADIUS selama failover, internet router, inbound DNAT, established flow, Hotspot login sesuai matriks. Perubahan live hanya untuk topologi dengan prosedur pemulihan terbukti.

---

# 21 Tiket, inventaris, portal, dan notifikasi

**OPS-01** Customer, service, device, dan network location dihubungkan agar tiket memiliki konteks tagihan, sesi (accounting), CPE, router, kejadian. Data tidak diketahui = "unknown".

**OPS-02** Inventaris: serial, vendor/model, kepemilikan, status stock/assigned/repair/retired, lokasi, histori assignment, biaya perolehan (ke akuntansi). ODP: kapasitas port dan reservasi; alokasi port transaksional. Kabel/splitter pasif butuh input teknisi.

**OPS-03** Tiket: `open → triaged → assigned → in_progress → resolved → closed` dengan reopen; relasi ke incident bersama; prioritas, evidence, jadwal, teknisi, foto, checklist, material, outcome. **Work order** (instalasi, perbaikan, pencabutan) dengan SLA internal tenant; material terpakai mengurangi persediaan; lokasi/foto pribadi dibatasi hak dan retensi. Prospek dan survei (LIF-01) memakai alur yang sama.

**OPS-04** Portal pelanggan terpisah dari login operator: layanan, invoice, kwitansi, bukti bayar, tiket, pengumuman, opsi Wi-Fi yang diizinkan, pilihan bahasa. Upload bukti tidak membuka isolir; approval + aktivasi tetap manual. Tidak ada akses raw ACS/router. Portal agen/kolektor terpisah dengan scope sempit.

**OPS-05 Notifikasi** (R3; default **off**) [N05]: kanal per perusahaan = email SMTP milik tenant dan adapter provider (mis. WhatsApp) yang dikonfigurasi tenant. Platform tidak mengirim pesan kepada pelanggan internet; pengiriman nyata hanya setelah Owner tenant mengaktifkan. Templat per bahasa. Penerima diverifikasi dari customer record; password penuh tidak dikirim lewat notifikasi umum; retry dengan dedup key dan rate limit. Email transaksional akun SaaS dikecualikan dari batasan ini.

**Batas OLT/non-MikroTik:** adapter resmi/terdokumentasi per model (API/SNMP/SSH); ACS tidak menggantikan provisioning OLT; OLT/ODP awal boleh inventaris manual; parser CLI wajib fixture dan versi firmware.

**AC-OPS:** portal pelanggan tidak membaca invoice orang lain dengan mengganti ID; reservasi ODP tidak ganda; tiket menyimpan perubahan assignment; material work order mengurangi persediaan dan menjurnal; portal agen hanya melihat datanya.

---
# 22 Model data dan kontrak API

| Domain | Entitas |
|---|---|
| Organisasi | Tenant, User, Membership, Role, Permission, SupportGrant, Locale |
| Platform billing | PlanVersion, SaaSSubscription, SaaSInvoice, PaymentSubmission, PaymentDestination |
| Jaringan | Router, VPNPeer, CredentialRef, Capability, RouterObjectMapping, RadiusClient (NAS), CutoverRun |
| Identitas akses | AccessAccount, AccessAccountSource, radius.* (proyeksi), RadiusSession (radacct), UsageDaily |
| Migrasi | DiscoveryRun, DiscoveredObject, MigrationBatch, ImportBatch, ImportRow, Conflict |
| Pelanggan | Customer, Service, CommercialPackage, TechnicalProfile, PackageRouterBinding, QuotaReservation, Prospect |
| Finansial tenant | Invoice, InvoiceLine, Payment, Allocation, Collector, Settlement, Account, Journal, JournalLine, Period, StatementLine, Asset |
| Voucher/agen | VoucherBatch, Voucher, Agent, Commission |
| Perangkat | Device, ACSMapping, Assignment, NetworkAsset, Location |
| Operasional | Job, Attempt, OutboxEvent, AuditEvent, BackupGeneration, Artifact, Ticket, WorkOrder |
| Monitoring | MetricRef, Alert, Incident |

**DATA-03** Kontrak endpoint kanonik mengikuti Technical Design bagian 5 (prefix `/api/v1`) [C05]. Contoh: `GET /tenants/{t}/services` (200); `POST /tenants/{t}/router-enrollments` (201); `POST /routers/{id}/discoveries` (202); `POST /migrations/{id}/validate` (202); `POST /migrations/{id}/commit` (202, `preview_revision`); `POST /routers/{id}/radius-cutover` (202); `POST /access-accounts` (201); `POST /payments/{id}/verify` (200); `POST /service-action-batches` (202); `POST /routers/{id}/backups` (202); `POST /devices/{id}/tasks` (202); `GET /jobs/{id}`; `GET /backup-artifacts/{id}/download`; `GET /meta/enums?locale=id`.

**API-01** Mutasi menerima `Idempotency-Key` (wajib untuk aksi finansial, pembuatan/perubahan akun RADIUS, dan cutover) dan `expected_revision` bila relevan. Job panjang → `202 + job_id`. Error `{code, message, locale, request_id, field_errors, retryable}` dengan `message` dilokalkan (I18N-08). Kode kanonik (13) dan pemetaan HTTP-nya didefinisikan pada **TD §5** (sumber kebenaran). Pagination cursor; default 50, maksimum 200.

**API-02** Tenant diambil dari membership terautentikasi; `tenant_id` dari klien tidak dipercaya. Endpoint massal memeriksa setiap objek. Body memakai schema, bukan raw command dari browser. **AC-DATA:** cross-tenant FK ditolak; uniqueness invoice dan username tahan race; batas zona waktu tidak menggandakan invoice; key berulang konsisten.

---

# 23 State machine dan ketahanan pekerjaan

| Objek | Transisi kanonik |
|---|---|
| Enrollment | `draft → enrollment_issued → bootstrap_pending → tunnel_seen → api_verified → discovery_ready`; cabang `conflict`, `expired`, `revoked` |
| DiscoveredObject | `discovered, selected, adopted, ignored, conflict, stale`; drift: `missing_source, needs_review, hold_unknown, local_account_shadow, binding_invalid` |
| Migration/Import | `uploaded/discovered → validating → review → committing → completed/partial/failed`; cabang `cancelled`, `expired` |
| Cutover RADIUS | `planned → preflight → parity_check → client_installed → canary → shadow_active → authoritative`; cabang `failed`, `rolled_back` |
| enforcement_mode (router) | `local`, `radius_shadow`, `radius_authoritative`, `degraded` |
| AccessAccount | `active, suspended, disabled, expired` |
| Payment submission | `submitted → reviewing → approved / revision_requested / rejected` |
| Invoice SaaS | `draft, open, partial, paid, void, expired` |
| Invoice internet | `draft, open, partial, paid, void` |
| SaaS subscription | `free/pending → active → grace → restricted → ended` |
| Service | lifecycle `draft, pending, provisioning, provisioned, conflict, failed, terminated, archived`; dimensi lain terpisah |
| Isolation | `normal → requested → applying → verified / failed / unknown` (arah `suspend` atau `restore`) |
| Job | `queued → claimed → preflight → executing → verifying → succeeded`; cabang `waiting_dependency, retry_wait, failed, uncertain, cancelled, recovery_required` |
| Backup generation | `scheduled → creating → transferring → verifying → committed → expired`; cabang `failed`, `abandoned` |
| Tugas ACS | `queued → waiting_inform → running → verifying → succeeded / failed / expired / cancelled` |
| Prospek/instalasi | `prospect → survey → scheduled_install → installed → active`; cabang `lost` |

`running` pada UI = `claimed/preflight/executing`; `partial` adalah ringkasan parent bulk; `stale` adalah label kesegaran; keduanya bukan state job. Label turunan lain (bukan state): `paid-awaiting-activation` (ED21) serta `verified_suspended`/`verified_active` — hasil verifikasi isolasi sesuai arah suspend/restore (ED22).

**JOB-01** Dimensi service terpisah: `lifecycle`; `billing_eligibility` (`not_billed`, `current`, `overdue`, `exempt`); `isolation_reason` (`none`, `overdue`, `policy`, `manual_hold`, `security_hold`, `technical_hold`); `desired_network_state` (`active`, `suspended`, `unmanaged`); `observed_network_state` (`enabled`, `disabled`, `missing`, `unknown`); `connection_state` (`online`, `offline`, `unknown`, diturunkan dari accounting RADIUS); `pending_job`. Enabled ≠ online; sesi hilang ≠ belum bayar. Hold keamanan/teknis mengalahkan kelayakan pembayaran.

**JOB-02** Commit DB dan outbox atomik. Delivery at-least-once dengan handler idempoten; tidak ada janji exactly-once pada router. Dedup key: tenant, target, action, versi policy/request. Lease/heartbeat dan fencing agar worker lama tidak menulis setelah lock diambil.

**JOB-03** Serialisasi mutasi per router; prioritas pemulihan layanan dan transaksi operator; concurrency monitoring terbatas. Backoff berjitter, retry budget (maks. 5 untuk kegagalan terbukti aman), circuit breaker per router, dead-letter queue, action center. Read timeout berbeda dari write-uncertain. Backup berat tidak memblokir job layanan tanpa batas.

**JOB-04** Cancel hanya bila belum ada efek aksi dan fence terbukti menurut EXE-01; state executing sendiri tidak membuktikan efek. Partial bulk mempertahankan sukses. Preflight dijalankan ulang bila job tertunda lama. Attempt menyimpan timestamp, actor/request, safe error, observed outcome.

**JOB-05** Lock/lease DB tidak menarik kembali perintah yang telah dikirim; fencing pada dispatcher mencegah pengiriman baru dari worker kedaluwarsa. Setelah timeout mutasi, tahan mutasi bertentangan sampai readback/rekonsiliasi selesai atau `recovery_required`. Uji worker lama hidup kembali saat lease baru diambil.

**AC-JOB:** kill worker sebelum/selama/sesudah langkah router dan sebelum acknowledgement; pulih tanpa akun/jurnal ganda. `uncertain` meminta readback/review, bukan retry destruktif buta.

---

# 24 Keamanan, privasi, dan operasional

**SEC-01** TLS web; credential encryption at rest dengan kunci di luar database; Argon2id; MFA TOTP; session expiry/revocation; rate limit login (5 gagal/15 menit per akun+IP lalu backoff); CSRF; validasi/XSS protection. Secret tidak ada di URL, log, analytics, export, browser.

**SEC-02** Router URL/host dan enrollment adalah permukaan SSRF. Connector hanya menjangkau target registry terverifikasi lewat **egress gateway**; blok metadata, loopback, jaringan internal platform, redirect arbitrer. Tes koneksi tidak dapat memindai.

**SEC-03** Raw SQL/Mongo, script RouterOS, ACS provision, shell command tidak diterima dari user biasa; typed adapter + escaping protokol. Upload privat, ukuran dibatasi, dipindai (ClamAV via antarmuka; **fail-closed**) [N07]. Output CSV menetralkan formula.

**SEC-04** Super Admin default melihat paket, jumlah layanan, health VPN/API/RADIUS, job/backup outcome, kapasitas. Tidak melihat password, ledger tenant, PII pelanggan detail, isi backup, atau isi tabel akun RADIUS. SupportGrant: consent Owner, scope, expiry, alasan, audit; banner sesi dukungan selalu terlihat. Root server tetap berkuasa secara teknis; tidak mengklaim zero-access encryption.

**SEC-05** DB role aplikasi bukan superuser; filtering tenant dipadukan constraint dan **row-level security (FORCE RLS)**. Role FreeRADIUS terpisah, minimal, dan hanya lewat soket lokal. Metrics, realtime, cache key, export, storage path, ACS, job membawa scope. Rekening bank pembayaran pelanggan internet ≠ rekening platform.

**OPS-SEC** Log keamanan/transaksi append-oriented, akses terbatas. Retensi [N08]: log aplikasi 30 hari; akses 90 hari; keamanan/audit 400 hari; `radpostauth` 30 hari; accounting mentah 90 hari; audit finansial mengikuti retensi dokumen keuangan; idempotency 7 hari. Perubahan rekening, privilege, restore, rotasi secret, cutover RADIUS, ekspor sensitif butuh reautentikasi. Offboarding memberi export (termasuk akun RADIUS dengan kredensial pada ekspor terenkripsi untuk Owner), daftar objek platform, pencabutan akses, masa hapus yang diberitahukan, panduan rollback ke secret lokal; tidak mereset router.

**PDP-01 Pelindungan data pribadi** (UU No. 27 Tahun 2022): data pelanggan akhir adalah data pribadi; tenant bertindak sebagai pengendali, platform sebagai prosesor; perjanjian pemrosesan data pada syarat layanan; tujuan dan retensi dinyatakan. **PDP-02** Hak subjek data (akses, koreksi, penghapusan/anonimisasi, penarikan persetujuan) didukung melalui alat Owner: pencarian subjek, export data pribadi, anonimisasi dengan pengecualian dokumen keuangan yang wajib disimpan. **PDP-03** Minimisasi: hanya field yang dibutuhkan; lokasi/foto/telepon dibatasi hak dan retensi; log tanpa PII berlebih. **PDP-04** Runbook TK-1006 mengikuti MAC-04: pengendali memberi pemberitahuan tertulis paling lambat 3×24 jam kepada subjek dan lembaga sesuai Pasal 46; prosesor mengeskalasi segera, maksimum internal 24 jam di dalam window tersebut. Clock, draft 24 jam, delivery readiness 48 jam, bukti pengiriman, deputi dan kanal aktual terverifikasi adalah kontrol wajib, bukan waktu yang ditentukan kemudian. **PDP-05** Persetujuan komunikasi pemasaran terpisah dari komunikasi transaksional.

**AC-SEC:** suite negatif: IDOR, SSRF, cross-tenant metrics/download/ACS/RADIUS, injection, replay token, privilege escalation, credential leak (termasuk password layanan dan secret RADIUS), malicious CSV, path traversal upload, CSRF. Temuan kritis/tinggi yang dapat dieksploitasi memblokir rilis; review lisensi (GPL/AGPL) menjadi gate dependency.

---

# 25 Kapasitas target dan pemulihan platform

## Skenario perencanaan (bukan hasil benchmark)

| Variabel | Asumsi |
|---|---|
| Perusahaan | 1.000 |
| Router rata-rata | 2/perusahaan = 2.000 router |
| Health interval | 60 detik ≈ 33 siklus router/detik |
| Generasi backup | 2 MiB (ilustrasi); 100 × 2.000 ≈ 391 GiB sebelum replika |
| Layanan PPPoE | 300/perusahaan = 300.000 akun RADIUS |
| Accounting interim 300 dtk | ≈ 1.000 pesan/detik bila 300.000 sesi aktif serentak |
| Autentikasi saat pemulihan massal | ribuan/detik dalam reconnect storm |
| CPE | 200/perusahaan = 200.000 perangkat; inform 900 dtk ≈ 222 sesi/detik |

Reconnect storm, login serentak, backup serentak, dan task provisioning lebih berat dari rata-rata. Tidak ada RAM/CPU minimum produksi disahkan sebelum workload diuji [D02]. Volume `radacct` dipartisi bulanan dan diarsipkan/diagregasi sesuai retensi.

**NFR-01** Target uji (profil beban bertanda tangan): p95 read API daftar pelanggan ≤ 2 detik; p95 enqueue action ≤ 2 detik; filter 100.000 service/tenant memakai indeks/pagination; **p95 autentikasi RADIUS ≤ 100 ms pada beban normal** dan tanpa kehilangan paket pada reconnect storm yang diuji; aktivasi sederhana pada router sehat p95 ≤ 60 detik. Bukan SLA.

**NFR-02** [D10] Target pemulihan: RPO transaksi ≤ 15 menit (base backup + WAL off-host), RTO platform ≤ 4 jam pada drill. **SLA tidak ditawarkan sebelum G5 lulus**; setelah itu SLA memakai angka terukur. Uji restore DB (termasuk `radius`), blob, ACS state, VPN registry, dan kunci bersama.

**NFR-03** Retensi cache/metrik/accounting, kuota per tenant, query timeout, disk watermark, pool koneksi (termasuk pool SQL FreeRADIUS), worker concurrency, dan load shedding terkonfigurasi. Kapasitas dirilis bertahap 10 → 100 → 1.000 tenant berdasarkan bukti.

**NFR-04** Saat server mati, sesi PPPoE/Hotspot yang sudah terbentuk tetap berjalan; sambungan baru bergantung RADIUS (RAD-08); failover WAN lokal tetap lokal; isolir/aktivasi pusat tertunda. Setelah pulih, rekonsiliasi policy, pembayaran, dan atribut RADIUS terbaru sebelum memproses backlog; job lama yang tak relevan dibatalkan.

---

# 26 Pengujian penerimaan dan gerbang rilis

| ID | Skenario | Lulus bila |
|---|---|---|
| T01 | Bootstrap pada router existing | Tidak ada perubahan default route/bridge/akun existing; objek manajemen baru terbatas preview; sesi kontrol dipantau |
| T02 | Impor berulang dan profile bersama | Tidak duplikat; tidak menulis router; mapping benar |
| T03 | Secret non-PPPoE, `service=any`, RADIUS eksternal | Tidak salah adopsi; unsupported ditandai |
| T04 | CSV update dan data rusak | Preview benar; retry aman; tanpa jurnal |
| T05 | Payment race dan bulk activation | Satu posting; job memeriksa state terbaru; hasil per item |
| T06 | Worker crash di tengah langkah router | Readback dan dedup; tidak ada objek/akun ganda |
| T07 | Isolir pada kombinasi PPPoE/Hotspot/IPv6 | Hanya target; login ulang dan jalur alternatif diuji |
| T08 | Backup ke-101 dan transfer putus | 100 generasi valid; tak ada file terpotong berlabel sukses |
| T09 | Restore lab | Perangkat/versi yang disahkan pulih; keterbatasan tercatat |
| T10 | Akses tenant dan support | Percobaan lintas scope ditolak dan diaudit |
| T11 | ACS task dan konflik identitas | Pending ≠ sukses; klaim salah tak memperoleh kredensial |
| T12 | Akuntansi | Debit=kredit; subledger cocok; closed period; bypass direct-write ditolak; setoran kolektor |
| T13 | Failover/PCC/Hotspot | Lulus per topologi; batas sesi tercatat |
| T14 | Outage dan restore platform | Backlog tidak menjalankan keputusan lama; RPO/RTO terukur |
| T15 | Soak dan reconnect storm | Tanpa starvation/lost transaction; resource dalam budget |
| T16 | RADIUS PAP/CHAP/MS-CHAPv2 (PPPoE, Hotspot) | Valid diterima, salah ditolak; atribut benar |
| T17 | Cutover RADIUS dan rollback | Sesi lama tidak terputus; prioritas lokal/RADIUS tercatat |
| T18 | Akun lintas router, penggantian router, perpindahan | Login tanpa input ulang; pool sesuai router |
| T19 | Isolasi tenant RADIUS | Username sama lintas tenant tak saling terlihat |
| T20 | Isolir/aktivasi via Reject + Disconnect | Sesi terputus, login ditolak, aktivasi memulihkan hanya target |
| T21 | Accounting dan Simultaneous-Use | Sesi tercatat, interim basi dibersihkan, sesi kedua ditolak |
| T22 | RADIUS outage dan edge replica | Sesi existing tetap; perilaku sambungan baru sesuai rancangan |
| T23 | i18n | Semua layar dan dokumen dalam id/en/pseudo-locale; fallback; zona waktu |
| T24 | Voucher dan agen | Reservasi kuota, kedaluwarsa, komisi, jurnal |

## Gerbang pengiriman (G0–G5)

| Gerbang | Isi |
|---|---|
| G0 | Desain/ADR: dokumen final, ADR stack, registry enum/state machine |
| G1 | Lab RouterOS nyata/CHR (termasuk RADIUS, T16–T17, T20–T21) dan CPE model; fixture dan versi terkunci; spike backup |
| G2 | Keamanan dan isolasi tenant, integritas finansial/retry, restore backup, review akuntan |
| G3 | Pilot tenant terbatas dengan baseline traffic dan sesi; inventory VM selesai |
| G4 | Benchmark workload, load/soak/reconnect storm, HA RADIUS |
| G5 | Observability, runbook, recovery drill (DR) |

**Prasyarat aktivasi fitur (`release_enabled`):**

| Fitur | Gerbang minimum |
|---|---|
| R1 inti (tenant, UI, CSV, adopsi database-only, multi bahasa) | G0, G2 (T10, T23) |
| Koneksi router/VPN | G1 (T01) |
| Cutover RADIUS dan mode otoritatif | G1 (T16, T17, T18, T21) |
| Backup | G1 (TK-505), G2 (T08, T09) |
| Penjualan paket berbayar | G2 (T05 sisi SaaS) + otorisasi pemilik |
| Auto-isolir produksi | G1 (T20), G2 (T05), G3 |
| Pembukuan produksi | G2 (T12 + review akuntan) |
| Voucher/agen | G1 (T16), G2 (T24) |
| ACS (per model) | G1 (matriks CPE), T11 |
| Wizard WAN (per topologi) | G1, T13 |
| Edge replica RADIUS | G4 (T22) |
| Peningkatan kapasitas (10→100→1.000) | G4, G5 |

Uji tanpa gangguan mencatat baseline, continuous probe, dan sesi yang dipertahankan selama adopsi dan cutover; hasil berlaku pada kombinasi yang diuji. Perubahan berisiko diuji di lab sebelum jendela pilot disetujui.

**Definition of Done:** requirement-ID terlacak ke implementasi dan test; audit/error path teruji; dokumentasi pengguna (id dan en); rollback aplikasi/migrasi diketahui; tidak ada blocker kritis. Modul yang belum lulus dinonaktifkan di UI dan tidak dipasarkan.

---

# 27 Parameter terkunci dan prioritas pelaksanaan

Seluruh parameter final. **Daftar keputusan (apa dan mengapa): `decisions_log.md` Bagian A–D. Registri nilai default (angka): TD §16.** Tabel berikut hanya memetakan ID keputusan ke pokok dan bagian PRD yang menerapkannya; nilai tidak diulang di dokumen ini.

| ID | Pokok keputusan | Bagian PRD |
|---|---|---|
| D01 | Merek/domain/kontak dari konfigurasi `BRAND_*`; nomor konfirmasi pembayaran | 4, 5 |
| D02 | Inventory VM wajib; tanpa klaim spesifikasi sebelum benchmark | 6, 25 |
| D03 | RouterOS v7 untuk mutasi/cutover; v6 hanya baca; API-SSL dipin | 7 |
| D04 | Transfer backup SFTP push via VPN + cadangan pull; batas artifact | 18 |
| D05 | Siklus SaaS (grace/restricted/ended); grace isolir internet; default off | 3, 13 |
| D06 | Harga final; tanpa prorata SaaS; upgrade hari bonus | 3, 4 |
| D07 | Plafon fair use Platinum; retensi metrik dan accounting | 3 |
| D08 | Autentikasi CPE per-device; tanpa model pra-didukung | 19 |
| D09 | COA default; pengakuan harian diposting bulanan; SAK EMKM; buku platform | 15 |
| D10 | Target RPO/RTO; SLA hanya setelah G5 | 25 |
| N13 | RADIUS wajib sebagai basis pengguna per tenant | 9 |
| N14 | Password layanan terenkripsi; proyeksi RADIUS terkendali | 9 |
| N15 | Adopsi database-only; cutover per router; mode otoritatif; rollback | 9 |
| N16 | Dua alamat RADIUS pada router; edge replica opsional (R3) | 9 |
| N17 | Bahasa `id` default, `en` wajib, tambahan lewat paket terjemahan | 5 |
| N18 | `first_period_policy` per paket | 12 |
| N19 | Kolektor/agen: akun clearing, setoran, komisi | 12, 14 |
| N20 | Voucher dan FUP (R3) berbasis accounting RADIUS | 14 |

## Backlog urutan pertama

1. Tenant isolation, autentikasi/MFA, i18n framework, audit, plan version, permission; uji negatif sebelum connector.
2. Skema RADIUS + proyeksi + FreeRADIUS multi-tenant pada lab; uji T16/T19.
3. Spike RouterOS read-only dan VPN pada topologi NAT; capability matrix; cutover di lab (T17).
4. Discovery, penggabungan identitas, mapping, profile binding, CSV staging; adopsi tanpa write router.
5. Customer workspace, pembuatan akun RADIUS idempoten, job center, backup terverifikasi.
6. Pembayaran SaaS dan billing tenant; kolektor; uji state dan saldo sebelum auto-isolir.
7. Isolir/aktivasi via RADIUS, akuntansi, monitoring penuh; pilot kecil.
8. Voucher/agen, ACS dan operasional lapangan, wizard WAN yang lulus lab.

## Risiko utama dan mitigasi

Salah adopsi/penggabungan identitas → preview dan review; ketergantungan RADIUS pusat → HA, edge replica, rollback runbook; gangguan router → read-only default, cutover bertahap dengan canary; fraud pembayaran → verifikasi dana dan audit; kebocoran tenant → otorisasi end-to-end dan RLS; kebocoran kredensial → enkripsi, role terbatas, rotasi; overload → kuota/budget dan pengukuran; kehilangan backup → commit-before-prune dan off-host recovery.

---

# 28 Register validasi teknis dan referensi

| Pokok | Kesimpulan yang boleh digunakan | Batas |
|---|---|---|
| RouterOS API/REST | Baca dan ubah konfigurasi dimungkinkan | Hak akses, TLS, timeout, versi diuji [S01–S02] |
| WireGuard | Tunnel manajemen dan RADIUS | Overlap/MTU/NAT diuji [S03] |
| PPP/Hotspot/RADIUS | Sumber lokal dan RADIUS dikonfigurasi pada router | Urutan lokal vs RADIUS dan perilaku secret disabled dibuktikan lab [S05–S07] |
| FastTrack | Dapat melewati queue | Platform tidak mengubah [S04] |
| RADIUS (FreeRADIUS) | AAA, accounting, Disconnect/CoA | Versi dipin; mitigasi BlastRADIUS [S19–S22] |
| Backup/export | Cakupan binary dan export berbeda | Tidak universal restore [S08–S10] |
| TR-069/GenieACS | NBI, tugas asinkron, provisioning | Per model/firmware dan auth [S11–S13, S23–S26] |
| Akuntansi | EMKM/EP memberi kerangka | Software tidak menjamin patuh [S14–S16] |
| Pelindungan data pribadi | UU PDP | Ditinjau konsultan hukum [S27] |
| Failover/PCC | Konsep routing terdokumentasi | Tidak menjamin sesi bertahan atau Hotspot cocok [S05, S17] |
| 1.000 perusahaan | Target bisnis | Belum benchmark |
| 100 backup rutin | Requirement produk | Per router; storage harus disediakan |
| Harga dan rekening | Data pemilik produk | Bukan verifikasi kepemilikan bank |

Rujukan ditinjau 11 Oktober 2026; dokumentasi daring dapat berubah. Versi yang dipakai implementasi dicatat pada `docs/compatibility.md`. Mikhmon, PHPNuxBill, daloRADIUS, MKTXP, dan provider Terraform hanya inspirasi desain; reuse lewat ADR, evaluasi lisensi, dan uji.

## Referensi resmi

- **S01** MikroTik REST API — https://help.mikrotik.com/docs/spaces/ROS/pages/47579162/REST+API
- **S02** MikroTik API — https://help.mikrotik.com/docs/spaces/ROS/pages/47579160/API
- **S03** MikroTik WireGuard — https://help.mikrotik.com/docs/spaces/ROS/pages/69664792/WireGuard
- **S04** MikroTik Connection tracking (FastTrack) — https://help.mikrotik.com/docs/spaces/ROS/pages/130220087/Connection+tracking
- **S05** MikroTik HotSpot — https://help.mikrotik.com/docs/spaces/ROS/pages/56459266/HotSpot+-+Captive+portal ; Per connection classifier — https://help.mikrotik.com/docs/spaces/ROS/pages/152600617/Per+connection+classifier
- **S06** MikroTik PPP AAA — https://help.mikrotik.com/docs/spaces/ROS/pages/132350049/PPP+AAA
- **S07** MikroTik RADIUS — https://help.mikrotik.com/docs/spaces/ROS/pages/328097/RADIUS
- **S08** MikroTik Backup — https://help.mikrotik.com/docs/spaces/ROS/pages/40992852/Backup
- **S09** MikroTik Configuration Management — https://help.mikrotik.com/docs/spaces/ROS/pages/328155/Configuration+Management
- **S10** MikroTik Fetch — https://help.mikrotik.com/docs/spaces/ROS/pages/8978514/Fetch
- **S11** GenieACS API Reference — https://docs.genieacs.com/en/stable/api-reference.html
- **S12** GenieACS Provisions — https://docs.genieacs.com/en/stable/provisions.html
- **S13** GenieACS CPE Authentication — https://docs.genieacs.com/en/stable/cpe-authentication.html
- **S14** IAI Tentang SAK EMKM — https://web.iaiglobal.or.id/SAK-IAI/Tentang%20SAK%20EMKM
- **S15** IAI Tentang SAK Entitas Privat — https://web.iaiglobal.or.id/SAK-IAI/Tentang%20SAK%20Entitas%20Privat%20%28EP%29
- **S16** IAI SAK EMKM Bab 3 — https://www.iaiglobal.or.id/v03/files/file_sak/emkm/files/basic-html/page20.html
- **S17** MikroTik Failover WAN Backup — https://help.mikrotik.com/docs/spaces/ROS/pages/26476608/Failover+WAN+Backup
- **S18** MikroTik User (groups dan policies) — https://help.mikrotik.com/docs/spaces/ROS/pages/8978504/User
- **S19** FreeRADIUS dokumentasi — https://www.freeradius.org/documentation/
- **S20** RFC 2865 (RADIUS) — https://www.rfc-editor.org/rfc/rfc2865 ; RFC 2866 (Accounting) — https://www.rfc-editor.org/rfc/rfc2866
- **S21** RFC 5176 (Dynamic Authorization: Disconnect/CoA) — https://www.rfc-editor.org/rfc/rfc5176
- **S22** BlastRADIUS (CVE-2024-3596) — https://www.blastradius.fail/
- **S23** Broadband Forum TR-069 (CWMP) — https://www.broadband-forum.org/
- **S24** TR-098 / TR-181 data model — https://cwmp-data-models.broadband-forum.org/
- **S25** TR-143 (diagnostik throughput) dan TR-111 (partial) — https://www.broadband-forum.org/
- **S26** GenieACS Virtual Parameters/Presets — https://docs.genieacs.com/en/stable/
- **S27** UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (JDIH) — https://peraturan.go.id/
- **S28** Unicode CLDR dan ICU MessageFormat — https://cldr.unicode.org/ ; https://unicode-org.github.io/icu/userguide/format_parse/messages/

---

## Persetujuan implementasi

Pemilik produk mengesahkan kebutuhan dan kebijakan komersial. Engineer jaringan mengesahkan matriks RouterOS/RADIUS/topologi. Penanggung jawab akuntansi mengesahkan posting dan pelaporan. QA mengesahkan evidence. Infrastruktur mengesahkan kapasitas, recovery, dan exposure jaringan. Persetujuan adalah gerbang pelaksanaan, bukan pernyataan bahwa pengujian telah dilakukan.
