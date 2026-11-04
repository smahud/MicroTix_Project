# MicroTix — kebutuhan produk

Revisi dokumentasi 2.2, 5 November 2026 (Asia/Jakarta). Pemilik produk: Huda Choirul Anam.

Tujuan awal: satu aplikasi web untuk pengusaha RT/RW Net Indonesia, mulai dari menghubungkan MikroTik dan mengadopsi pelanggan existing ke RADIUS perusahaan, sampai penagihan, pembayaran, pembukuan, backup, monitoring, dan operasional. Pelanggan tetap milik perusahaan ketika router dipindah atau diganti.

Dokumen ini memiliki kebutuhan bisnis, harga, kuota, dan fase R1–R4. Detail implementasi dimiliki dokumen domain yang ditautkan dari [indeks](README.md). Nilai default teknis terstruktur berada di [defaults.json](defaults.json). Semua pernyataan “wajib” adalah acceptance, bukan klaim fitur telah dibangun.

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

**TEN-02** Setiap perusahaan, termasuk Free, mendukung minimal satu Owner, satu Teknisi, dan satu Admin Pembayaran; Owner boleh merangkap. Otorisasi berbasis **permission granular**; Owner/Teknisi/Admin Pembayaran adalah bundel default. Bundel **Akuntan**, **Viewer**, **Kolektor** (hanya penerimaan tunai dan setoran sendiri), dan **Agen/Reseller** (portal agen terbatas) dibentuk dari permission yang sama. Batas anggota tim aktif (termasuk Owner) adalah batas sistem, bukan klaim pemasaran:

| Paket | Free | Bronze | Silver | Gold | Diamond | Platinum |
|---|---:|---:|---:|---:|---:|---:|
| Anggota tim aktif | 3 | 5 | 8 | 12 | 20 | 50 (fair use) |

Kolektor dan agen eksternal dihitung sebagai gabungan identitas unik; seseorang dengan dua peran dihitung sekali. Mereka tidak dihitung sebagai anggota tim; mereka memiliki akun terbatas dengan batas jumlah per paket (Free 5, Bronze 20, Silver 50, Gold 100, Diamond 200, Platinum 500).

**TEN-03** Otorisasi diterapkan di backend, worker, query metrik, object storage, export, notifikasi, dan RADIUS provisioning; menyembunyikan tombol tidak cukup. Relasi antarentitas wajib dari tenant yang sama. Scope router/lokasi berlaku pada operasi massal.

**Sesi dan autentikasi**: email + password (min. 12 karakter, Argon2id); MFA TOTP (RFC 6238) dengan kode pemulihan sekali pakai. MFA wajib untuk semua peran platform; setiap aktor tenant yang menjalankan izin sensitif wajib MFA+reauth sebelum aksi tersebut (ubah rekening/izin, unduh kunci, cutover/rollback RADIUS, restore, reopen periode, ekspor sensitif, tampilkan kredensial layanan). Reautentikasi berlaku 10 menit. Sesi tenant: idle 8 jam, absolut 24 jam; peran platform: idle 30 menit, absolut 12 jam. Perubahan peran membatalkan sesi yang tidak berhak. Tidak ada WhatsApp OTP. Email transaksional akun (verifikasi, reset, undangan) memakai SMTP terkonfigurasi; pada development ditangkap lokal.

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

**Harga final dan pajak**: harga di atas adalah harga final yang dibayar. Konfigurasi pajak per PlanVersion tersedia dengan tarif default 0 dan flag inklusif/eksklusif.

**SUB-01 Aturan hitung kuota**. Satu layanan internet terkelola (satu `access_account` PPPoE atau satu pengguna Hotspot terkelola) = satu unit kuota.

| Dihitung | Tidak dihitung |
|---|---|
| Layanan `provisioned`, offline, terisolir, manual-disabled, imported | Layanan `terminated` atau `archived` |
| Reservasi aktif (adopsi, migrasi, commit CSV, pembuatan akun, reaktivasi arsip) dan item `pending` | Draft manual tanpa reservasi |
| Router offline (tetap memakai slot sampai dilepas) | Akun router di luar pilihan adopsi |
| Voucher Hotspot yang diterbitkan dan masih valid (belum kedaluwarsa/dicabut) | Voucher habis, kedaluwarsa, atau dicabut |

Pelanggan dengan rumah dan toko = dua layanan; beberapa HP di satu rumah bukan layanan tambahan. **Batas draft manual per tenant** = `max(10, ceil(25% × batas layanan))`, maksimum 500 (Free 13, Bronze 38, Silver 75, Gold 125, Diamond 188, Platinum 500).

**Pelepasan dan penggantian router**: Owner dapat *melepas* router (arsip; slot bebas; akun RADIUS tetap milik tenant dan tidak terpengaruh) atau *mengganti* router (mode `replacing`; memakai slot router lama; tidak dihitung ganda selama tumpang tindih maksimum 30 hari). Karena identitas pelanggan berada pada basis RADIUS tenant, penggantian router **tidak memerlukan pemetaan ulang akun**: router baru di-enroll, di-cutover RADIUS, dan binding paket/pool diterapkan. Histori penuh tersimpan.

**SUB-02** Used = committed_counted_accounts + reserved_unmaterialized_units. Reservasi yang sudah menjadi akun dikonsumsi dalam transaksi yang sama; pending yang sudah mempunyai akun tidak dihitung lagi. Entitlement lock menserialisasi reserve/consume/release/expiry dan ganti paket. Reservasi kuota atomik sebelum pembuatan akun/impor. Reservasi dilepas otomatis bila gagal sebelum perubahan data; item yang tak dapat dipastikan menjadi `pending` yang tetap dihitung sampai diselesaikan atau dibatalkan. Reservasi tanpa kemajuan kedaluwarsa setelah 60 menit. Reaktivasi arsip memeriksa kuota.

Satu replacement aktif per router asal; router baru tidak menggantikan dua asal. Pada batas30 hari tandai replacement_overdue dan hitung keduanya bila masih terdaftar; blokir penambahan over-quota, jangan memutus pelanggan atau menghapus router otomatis. Slot pelepasan bebas setelah scheduling writer dihentikan/fenced dan NAS/peer ditangani sesuai scope; arsip record saja tidak mencabut akses.

**SUB-03 Platinum dan fair use**: tanpa batas lisensi, bukan batas penyimpanan, polling, concurrency, atau jaminan satu server. Plafon operasional default Platinum: 25 router dan 5.000 layanan per tenant; dapat dinaikkan Super Admin per tenant setelah pemeriksaan kapasitas (G4). Kuota perangkat ACS = batas layanan. Backup manual dan pre-change masing-masing maksimal 10 generasi per router. Retensi metrik: raw 15 hari, agregat 5 menit 90 hari, agregat 1 jam 400 hari; accounting RADIUS mentah 90 hari, agregat harian 400 hari. Fair use dipublikasikan di landing sebelum Platinum dijual.

**SUB-04 Periode, renewal, anniversary**:
1. Periode memakai **tanggal kalender** pada zona waktu perusahaan (platform: Asia/Jakarta), `[start_date, end_date)`.
2. Simpan **hari jangkar** `A` (hari-dalam-bulan `start_date` periode pertama). Periode ke-k mulai pada `clamp(A, bulan_awal + k)` dengan `clamp(A, bulan) = min(A, hari_terakhir_bulan)`; jangkar tidak bergeser. Contoh `A=31`, mulai 31 Jan: [31 Jan, 28 Feb) (29 Feb pada tahun kabisat), [28/29 Feb, 31 Mar), [31 Mar, 30 Apr). Tahunan berakhir pada `clamp(A, bulan_awal + 12)`.
3. **Renewal aktif** dimulai pada `end_date` periode berjalan dan mempertahankan jangkar. **Renewal sesudah expired** dimulai pada tanggal lokal approval; jangkar baru = hari tanggal itu; tidak ada penagihan mundur.
4. **Upgrade**: quotation → pembayaran → perubahan entitlement atomik; tanpa prorata uang; periode baru mulai pada tanggal approval dengan paket baru; sisa hari kalender utuh periode lama ditambahkan sebagai hari bonus; jangkar baru = hari tanggal approval.
Simpan anchor_date, period_index, dan bonus_offset_days terpisah. bonus_days=max(0,old_end_date-tanggal_lokal_approval). Boundary term baru=clamp(anchor,bulan_asal+bulan_kumulatif)+bonus_offset_days; renewal berikut dihitung dari bulan asal, bukan tanggal hasil clamp. Bonus diterapkan sekali, bukan bertambah pada setiap renewal/retry.
5. **Downgrade**: berlaku pada renewal berikutnya; ditolak `quota_exceeded` bila pemakaian melebihi batas paket tujuan; tidak ada terminasi otomatis.
6. **Refund SaaS**: hanya untuk kesalahan sistem/pembayaran ganda, lewat dokumen koreksi.

**SUB-05 Siklus SaaS dan batas non-destruktif**. Tidak ada isolir internet pelanggan karena utang SaaS. Status: `free/pending → active → grace → restricted → ended`.

| Status | Mulai | Perilaku |
|---|---|---|
| grace | `end_date` | 7 hari; fitur penuh; banner peringatan |
| restricted | hari ke-8 s/d ke-30 | Tidak dapat menambah router/layanan baru; operasi layanan existing, autentikasi RADIUS, accounting, backup, monitoring, akses bayar, export, dan pemulihan tetap berjalan |
| ended | hari ke-31 | Read-only + pembayaran + export; **autentikasi RADIUS pelanggan tetap dilayani** selama masa retensi VPN; automation isolir dijeda dengan notifikasi; peer VPN dan RADIUS dipertahankan 60 hari dengan notifikasi 7/3/1 hari sebelum penarikan; data dipertahankan 180 hari lalu alur penghapusan (export ditawarkan lebih dulu) |

Definisi waktu: E=midnight lokal end_date. Grace [E,E+7 hari), restricted [E+7,E+30 hari), ended_at=E+30 hari. Penarikan VPN/RADIUS paling awal ended_at+60 hari=E+90 hari; data biasa ended_at+180 hari. Notifikasi H-7/H-3/H-1 harus benar-benar terkirim dan recovery export/rollback tersedia; jika tidak, withdrawal_blocked, bukan disconnect otomatis.

Penarikan layanan RADIUS tidak pernah mendadak: sebelum penarikan, Owner menerima panduan rollback cutover (secret lokal) dan export akun. Retensi dokumen keuangan minimum 10 tahun kalender dari akhir tahun buku, tidak dapat dikurangi; hold, arsip dan purge mengikuti OPERATIONS.md §5 serta review akuntan/legal. Paket Free tidak kedaluwarsa.

**AC-SUB:** retry approval dan dua reservasi bersamaan tidak menggandakan masa atau melewati kuota. Uji 29/30/31 Januari, tahun kabisat, renewal aktif/sesudah expiry, upgrade hari bonus, downgrade melebihi kuota, perilaku RADIUS pada status ended.

---

# 4 Pembayaran platform dan Super Admin

**PAY-01** Alur wajib: pilih paket/periode → quotation → invoice → transfer → unggah bukti → verifikasi dana → approval → aktivasi. Bukti transfer bukan bukti final penerimaan bank. Status invoice, payment submission, subscription, dan activation job dipisahkan. Invoice SaaS kedaluwarsa 7 hari sesudah terbit (konfigurasi).

**PAY-02** Form: invoice, nama pengirim, metode, nominal, waktu, referensi opsional, file, catatan. File JPEG/PNG/PDF maksimum 5 MiB, divalidasi MIME (magic bytes), dipindai, disimpan privat dengan path opaque. File yang belum selesai dipindai tidak dapat dilihat/diunduh staf. Approval mencatat petugas, waktu, rekening, referensi, alasan; reject/needs revision wajib beralasan. Bukti dengan hash SHA-256 sama atau kombinasi (nominal, pengirim, tanggal) sama menghasilkan peringatan.

Rekening tujuan atas nama **Huda Choirul Anam** (data dari pemilik produk; kepemilikan bank belum diverifikasi eksternal):

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

**Aturan data rekening:** simpan `display_value` persis (termasuk spasi), `normalized_digits` hanya untuk pencocokan, nol di depan dipertahankan; tiap tujuan memiliki `status` aktif/nonaktif, `ownership_verified=false` dan `published=false` secara default. **Rekening tidak tampil pada landing publik**; instruksi pembayaran tampil pada invoice terautentikasi sebagai snapshot. Invariant rekening tidak tampil pada landing tetap berlaku; reauth/audit saja tidak memberi izin mengubahnya menjadi publik.

**PAY-03** Semua tujuan pembayaran dapat diedit/dinonaktifkan dengan audit dan reautentikasi. Invoice menyimpan snapshot instruksi. Perubahan rekening menangani invoice terbuka secara eksplisit (tetap memakai snapshot; opsi menerbitkan ulang dengan alasan). Admin pembayaran platform dapat menyetujui transfer tanpa akses mengganti rekening.

**PAY-04** Partial payment (invoice `partial`, entitlement tidak aktif sampai lunas atau kedaluwarsa), selisih lebih (kredit platform atas tenant, dipakai pada invoice berikutnya; bukan pendapatan tambahan), bukti duplikat, pembayaran invoice expired (finance memulihkan invoice dengan alasan atau menjadikannya kredit), refund, dan salah approval masuk **alur koreksi** dengan dokumen sumber; riwayat tidak dihapus. Approval ke subscription memakai transaksi database + outbox.

**AC-PAY:** dua approver untuk submission/transfer yang sama menghasilkan satu Payment dan satu entitlement event bila invoice SaaS lunas. Dua transfer nyata ke invoice sama tetap dua Payment; allocation dibatasi outstanding dan sisa menjadi kredit. Aktivasi internet manual terpisah. Bukti sama memicu peringatan, bukan dedup dana berdasarkan invoice. Landing tidak memublikasikan rekening nonaktif atau `published=false`.

---

# 5 Navigasi, pengalaman pengguna, dan multi bahasa

## Website publik

**UX-01** Landing berisi manfaat, fitur yang benar-benar tersedia (`release_enabled`), harga bulanan/tahunan, plafon fair use Platinum, kompatibilitas, panduan, kontak (konfigurasi), registrasi, login, kebijakan privasi dan layanan. Demo memakai data simulasi terpisah. Klaim tanpa downtime dibatasi pada adopsi yang lulus uji; tidak mengiklankan semua ONT atau infrastruktur unlimited. Nama merek, domain, logo, dan kontak publik dari konfigurasi `BRAND_*`; "RT RW Net" adalah nama kerja; landing tidak dipublikasikan bila `BRAND_*` belum terisi.

## Dashboard perusahaan

Menu produk (13): Beranda; Pelanggan; Paket dan Profile; Tagihan dan Pembayaran; Keuangan; Router dan Monitoring; Perangkat ACS; Backup; Gangguan dan Teknisi; Inventaris dan Peta; Konfigurasi; Perusahaan dan Tim; Paket Aplikasi — ditambah tautan **Bantuan** (bukan menu produk). UI memetakan 13 menu produk ke **5 kelompok sidebar**: Operasional (Beranda, Pelanggan, Paket dan Profile, Tagihan dan Pembayaran, Gangguan dan Teknisi); Jaringan (Router dan Monitoring, Backup, Perangkat ACS, Inventaris dan Peta, Konfigurasi); Keuangan; Perusahaan (Perusahaan dan Tim, Paket Aplikasi); Bantuan. Modul yang belum `release_enabled` tidak memenuhi menu harian.

**UX-02** Tenant aktif selalu terlihat. Filter lokasi/router dan pencarian dipertahankan dalam scope tenant. Beranda mengutamakan pekerjaan: sudah bayar menunggu aktivasi, data impor belum lengkap, router tidak terpantau, backup gagal, RADIUS bermasalah, tiket prioritas. Semua grafik/status memiliki timestamp pembaruan. Kartu modul R2 disembunyikan pada R1, bukan ditampilkan sebagai nol.

**UX-03** Daftar pelanggan: identitas, username, router terakhir terlihat, jenis layanan, paket, status koneksi, subscription, invoice periode terpilih, job; empat status terpisah (bayar, isolir, koneksi, job). Filter: router, profile/paket, online/offline/unknown, lunas/belum/sebagian, isolir, pending activation, incomplete mapping, kolektor, area. Pencarian: nama, customer code, username, telepon, invoice. Tab cepat: Semua; Belum bayar; Sudah bayar menunggu aktivasi; Terisolir; Data belum lengkap.

**UX-04** Tindakan massal membedakan halaman ini dan seluruh hasil filter. Snapshot seleksi dibekukan, jumlah ditampilkan, hak akses dan kondisi terbaru diperiksa per item sebelum eksekusi. Hasil per baris menyediakan retry hanya untuk kegagalan layak.

**UX-05** Antarmuka multi bahasa dengan **Bahasa Indonesia sebagai default**; format IDR; zona WIB/WITA/WIT; aturan lengkap pada `I18N.md`. Label pelanggan "download ke pelanggan" dan "upload dari pelanggan"; adapter menerjemahkan arah rx/tx. Warna status selalu disertai teks. Form dapat dipakai pada lebar ponsel.

**UX-06** Rename router hanya mengubah `display_name` dan audit. Wizard impor menyimpan progres per tenant; setelah tertunda lama, snapshot divalidasi ulang. Tampilan awal Keuangan menonjolkan tagihan, kas masuk terverifikasi, piutang, tunggakan; laba akuntansi hanya dari ledger yang sesuai.

## Multi bahasa

**I18N-01 s/d I18N-10** (rincian pada `I18N.md`): bahasa default `id`; bahasa `en` tersedia sejak R1; bahasa tambahan lewat paket terjemahan tanpa perubahan kode; teks tampil dari katalog pesan (ICU di frontend, gettext di backend); kode mesin (enum, kode error, atribut RADIUS) tidak diterjemahkan; bahasa ditentukan per pengguna, per tenant, dan per pelanggan; dokumen (invoice, kwitansi, laporan) menyimpan bahasa terbit; API melokalkan `message` berdasarkan `Accept-Language`; fallback ke `id`; pseudo-locale untuk uji.

**AC-UX:** operator menemukan pelanggan sudah bayar pada periode tertentu dan menjalankan aktivasi tanpa membuka menu routing. Menutup tab tidak membatalkan job. Data usang diberi label. Empty state memberi tindakan relevan. Seluruh layar dapat dirender dalam `id`, `en`, dan pseudo-locale tanpa teks tertanam.

---
# 6 Arsitektur dan prasyarat infrastruktur

Modular monolith dengan worker terpisah, PostgreSQL untuk bisnis/outbox/job/RADIUS, FreeRADIUS terpisah, WireGuard untuk manajemen, Caddy HTTPS, Prometheus internal, dan pipeline upload privat. GenieACS/MongoDB baru pada R3. Keputusan stack dan batas proses: [ARCHITECTURE.md](ARCHITECTURE.md).

**INF-01** Target implementasi Debian 13; versi dependency aktual dipin saat TK-002, bukan dibuat-buat oleh audit dokumen. **INF-02** Publik hanya HTTPS 443, UDP WireGuard terkonfigurasi, dan endpoint ACS HTTPS saat R3 diaktifkan. DB, RADIUS, metrik, storage management, NBI, dan MongoDB internal. Trafik internet pelanggan tidak transit melalui SaaS.

**INF-03** Inventory CPU/RAM/disk/IOPS, jaringan/NAT/DNS/UDP, backup off-host, dan failure domain diperlukan sebelum deployment. Data itu bukan prasyarat membuat kode di workspace. Satu VM pilot adalah satu failure domain. Kapasitas 1.000 tenant adalah target bisnis yang diuji bertahap; bukan alasan membuat cluster sejak awal.

---

# 7 Onboarding VPN dan API

**NET-01** WireGuard adalah transport utama RouterOS v7. Satu peer dan alamat tunnel /32 unik per router; route/allowed-address hanya /32 endpoint server yang benar-benar dipakai. Pool awal pada defaults wajib diperiksa terhadap overlap/CGNAT. Tidak ada default route atau seluruh LAN tenant melalui SaaS.

**NET-02** Router memulai tunnel; keepalive hanya bila perlu NAT. UDP terblokir ditampilkan sebagai masalah konektivitas. RouterOS v6 tetap hanya baca dan tidak di-upgrade otomatis. Jalur baca v6 memerlukan koneksi aman yang sudah tersedia; jangan mencoba memasang WireGuard pada v6.

**NET-03** Token enrollment acak, hashed, sekali pakai, terikat tenant/router, TTL menurut defaults. Skrip preview hanya menambah objek manajemen milik platform. Read-only berarti akun operasional sesudah enrollment; pemasangan tunnel/sertifikat tetap merupakan perubahan konfigurasi. Tidak reset/reboot atau mengubah default route/bridge/DHCP/DNS/akun existing. Token/kredensial tidak masuk log atau URL.

**NET-04** Native API-SSL dengan pin sertifikat adalah default; REST HTTPS alternatif mati default. Pin dari enrollment terautentikasi; mismatch ditolak. Shared resource api-ssl existing tidak ditimpa tanpa rencana yang ditinjau.

**NET-05** Mode read_only default; manage memakai kredensial penulis terpisah dan izin sesuai aksi. S1 memakai akun migrasi sementara dengan cleanup absolut terverifikasi, maksimum 24 jam. **NET-06** Firewall host default-deny, peer tidak boleh mengakses peer lain/DB/SSH/metadata/jaringan internal; API/Disconnect hanya dari server, RADIUS/receiver hanya dari /32 NAS terdaftar. **NET-07** Custom group mengikuti hasil uji policy minimum, bukan asumsi grup bawaan read aman. **NET-08** Revoke token, peer VPN, akun API, dan klien NAS adalah empat efek yang dilacak terpisah.

Prosedur dan bukti AC-NET: [ROUTEROS.md](ROUTEROS.md), T01/T10/T19. Cutover RADIUS terpisah; enrollment tidak mengubah AAA.

---

# 8 Discovery akun dan profile existing

**IMP-01** Discovery memakai operasi baca dengan properti minimum. Objek: PPP secrets/profile/active, PPPoE server, Hotspot user/profile/server/active, pools, queue relevan, firewall filter (hanya deteksi FastTrack), IP/interface, konfigurasi RADIUS/`ppp aaa` yang ada, script/scheduler terkait. **Discovery tidak membaca password**; pembacaan password adalah langkah migrasi terpisah (bagian 9). Batasi ukuran, waktu, frekuensi (read timeout 15 detik; tidak lebih dari satu discovery per router bersamaan).

PPP secret dapat dipakai layanan selain PPPoE: hanya `service` pppoe atau `any` yang dapat dimigrasikan; `any` ditinjau; layanan lain (l2tp, sstp, ovpn, dll.) dan akun administrator RouterOS tetap lokal dan dilabeli `unmanaged`. Sesi aktif adalah data runtime, bukan daftar akun. RADIUS eksternal yang sudah ada tidak dapat direkonstruksi dari sesi aktif; akunnya masuk jalur impor eksternal (RAD-09 S4).

**IMP-02** Hasil disimpan sebagai snapshot discovery bertimestamp dan versi adapter, status `discovered, selected, adopted, ignored, conflict, stale`. Tampilkan jumlah per tipe/profile, enabled/disabled, akun tanpa pemetaan, duplikat lintas router, dampak kuota. Profile dibaca tanpa otomatis menjadi paket komersial.

**IMP-03** Wizard adopsi dan migrasi (8 langkah): **Sumber → Pilih/filter akun → Gabungkan identitas lintas router → Petakan pelanggan → Petakan profile/paket → Sumber password → Validasi dan tinjau → Simpan**; lalu laporan. Commit adopsi **database-only**: membuat `access_account`, `Service`, proyeksi `radius.*`, dan jejak sumber; tidak menulis akun, profile, comment, scheduler, atau firewall ke router. Automation isolir/penagihan `automation_enabled=false` sampai data lengkap, simulasi ditinjau, dan policy diaktifkan.

**IMP-04** Satu akun = satu service. Bila identitas bisnis belum ada, label pelanggan sementara = username. Penggabungan beberapa service ke satu customer wajib ditinjau; kemiripan nama/MAC/telepon tidak cukup. Identitas objek router = tenant + router + tipe objek + referensi terverifikasi; `.id` hanya handle lokal. **Identitas akses** (username) unik **per tenant** dan sama pada seluruh router tenant [DATA-01].

**IMP-05** Profile default tidak diubah massal. Comment dan on-login/on-logout dibaca sebagai data tidak tepercaya, tidak dieksekusi. Format Mikhmon/operator lain memerlukan adapter versi khusus yang menunjukkan hasil parsing untuk konfirmasi; tidak menebak tunggakan dari comment.

**FastTrack vs Queue (final)**: discovery membaca aturan FastTrack. Bila aturan `fasttrack-connection` dapat mencakup trafik PPPoE/Hotspot sementara kecepatan diatur lewat `rate-limit`/antrean, capability `fasttrack_may_bypass_queue=true` dan peringatan tampil pada pemetaan paket. **Platform tidak mengubah FastTrack atau firewall pelanggan pada R1–R3**; remediasi oleh operator dan diuji lab (TK-508). Pada R4 templat hanya menambah pengecualian untuk objek miliknya setelah lulus lab.

**AC-IMP:** fixture 50 PPPoE, Hotspot, profile bersama, secret non-PPPoE, akun disabled, RADIUS eksternal, username sama pada dua router. Impor dua kali tanpa duplikasi; tidak mengubah export konfigurasi router (setelah normalisasi field volatil); tidak memutus sesi; kuota diperiksa atomik; akun di luar pilihan tetap tidak dikelola.

---

# 9 Identitas akses, RADIUS, dan migrasi

**RAD-01** Seluruh akun PPPoE/Hotspot yang dikelola berada pada basis RADIUS per tenant dan dapat dipakai seluruh router tenant sesuai binding. **RAD-02** AccessAccount sumber kebenaran; proyeksi radius ditulis atomik bersamanya. **RAD-03** Tenant berasal dari NAS transport terverifikasi, bukan username/payload. **RAD-04** Resolver paket/binding memilih kecepatan, pool/IP, masa berlaku, dan batas sesi. **RAD-05** Password aplikasi terenkripsi; cleartext projection adalah pengecualian terkendali untuk kompatibilitas protokol, tidak ditampilkan/log/export umum.

**RAD-06** Suspend memakai Reject + Disconnect; restore memulihkan kelayakan autentikasi, dengan bukti berbeda. **RAD-07** Accounting sumber koneksi/pemakaian; stale berarti unknown. **RAD-08** Dua endpoint RADIUS direncanakan; hanya pasang endpoint sekunder yang benar-benar ada. Dua proses satu host bukan host HA; host HA dan edge dibuktikan pada gate terkait, tidak menghalangi build lokal.

**RAD-09** Discovery/adopsi DB-only; empat sumber password S1–S4 dan penggabungan identitas ditinjau. **RAD-10** Cutover per router B0–B6 terpisah, ber-backup, canary, observasi, dan rollback. **RAD-11** Pindah/ganti router tanpa input ulang akun, dengan binding dan otorisasi NAS tujuan benar. **RAD-12** Hotspot/voucher memakai RADIUS. **RAD-13** Secret unik per NAS, Message-Authenticator wajib pada Access-Request, listener hanya tunnel, rotasi terverifikasi. **RAD-14** Acceptance T16–T22.

**DATA-01** Objek tenant membawa tenant_id; mapping router menyimpan natural key/fingerprint/generation, bukan memakai.id sebagai identitas permanen. **DATA-02** UUID, UTC, uang decimal IDR, bandwidth integer; arsip menjaga dokumen finansial, penghapusan PII memakai retensi terpisah.

Kontrak lengkap dan satu-satunya definisi B0–B6: [RADIUS.md](RADIUS.md).

---

# 10 Profile, paket, dan sinkronisasi

**PRO-01** `TechnicalProfile` = konfigurasi router (pool, alamat lokal, DNS, MSS; pada Hotspot profil server). `CommercialPackage` = nama jual, harga, periode, **kecepatan (rx/tx bit/s dengan burst opsional)**, batas data/FUP, `first_period_policy`, kebijakan. `PackageRouterBinding` = paket ke profil/pool per router. Kecepatan dikirim lewat RADIUS dari paket, sehingga mengubah paket tidak mengubah profil router. Nama profile tidak menjadi harga atau periode otomatis. Owner dapat memetakan seluruh akun satu profile ke paket sekali; binding menyimpan versi/hash profile yang ditinjau. Atribut profil tidak didukung tetap terlihat pada detail teknis.

**PRO-02** Edit **profil router** (pool, alamat lokal, DNS) hanya melalui alur terkontrol (R4) dengan analisis dampak: jumlah akun managed (RADIUS) dan unmanaged (lokal) yang merujuk profil. Bila unmanaged terdampak, edit langsung diblokir; default membuat profil baru. Perubahan **kecepatan** dilakukan pada paket (atribut RADIUS) dengan efek pada sesi berikutnya atau segera melalui CoA/Disconnect; tidak dijanjikan penerapan live universal. FastTrack dapat melewati antrean sehingga efektivitas wajib diuji.

**SYNC-01** Pisahkan desired state, observed state, dan provenance per field. Identitas dan atribut akses berasal dari aplikasi (RADIUS); kondisi sesi dari accounting; konfigurasi router tetap observed kecuali objek bernamespace milik platform. Perubahan manual via WinBox ditampilkan sebagai drift. Deteksi drift: scan penuh default tiap 6 jam, on-demand, dan preflight tiap write. Drift yang dipantau khusus: klien RADIUS atau `use-radius` hilang (`radius_client_missing`, mode turun ke `degraded`), secret/user lokal baru pada router otoritatif (`local_account_shadow`, diusulkan adopsi atau dinonaktifkan atas persetujuan), profil/pool yang dirujuk binding hilang (`binding_invalid`).

**SYNC-02** Akun yang hilang pada router tidak memengaruhi akun RADIUS (identitas milik tenant). Objek router yang hilang ditandai `missing_source`; akun baru di router masuk daftar belum diadopsi; rename, restore router, perubahan `.id`, profile hilang memicu pemeriksaan mapping (jenis, router, identifier, fingerprint; review bila ambigu). Akun dinonaktifkan manual di luar aplikasi: `hold_unknown` sampai ditinjau.

**SYNC-03** Setiap job router menyimpan expected configuration revision; kondisi berubah → `conflict` (tidak menimpa). Write timeout = `uncertain`; baca ulang sebelum retry; retry add memeriksa objek yang mungkin sudah dibuat.

**AC-PRO / AC-SYNC:** perubahan kecepatan paket diterapkan ke seluruh akun paket tanpa mengubah profil router; edit profil router yang dipakai 100 akun menunjukkan seluruh dampak; clone tidak mengubah 90 akun di luar seleksi; putus respons setelah router menulis tidak menggandakan objek; restore router yang mengubah `.id` tidak menghubungkan invoice ke pelanggan lain.

---

# 11 Pelanggan, siklus layanan, dan impor CSV

**CUS-01** Form ringkas: nama/label, router (opsional; default semua router tenant), tipe layanan (PPPoE/Hotspot), paket, kebijakan mulai layanan; kontak boleh menyusul. Pilihan akhir (masing-masing menyatakan apakah menulis router): **Simpan draft** (tidak menulis), **Hubungkan akun existing** (database-only), **Buat akun** (membuat `access_account` + proyeksi RADIUS; tidak menulis router; efektif pada router berstatus `radius_authoritative`), **Buat dan aktifkan**. Username unik per tenant; password dibangkitkan aman (CSPRNG, 16 karakter). MAC dan IP opsional.

**Kebijakan kredensial layanan**: password baru tampil **sekali** kepada aktor berizin; tersimpan terenkripsi; tampil ulang oleh pemegang `services.reveal_credentials` dengan reautentikasi, audit, auto-sembunyi 30 detik; tidak ada di tabel, log, analytics, export, pesan error. Password existing tidak berubah saat kosong; rotasi aksi terpisah dengan peringatan dampak CPE (ACS-06).

**CUS-02** Data pelanggan tersimpan walau provisioning gagal. Lifecycle service: `draft, pending, provisioning, provisioned, conflict, failed, terminated, archived`; dimensi lain (billing, isolasi, jaringan, koneksi, job) terpisah (bagian 23). UI memberi remediasi, bukan meminta membuat pelanggan ulang.

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

**CSV-03** CSV bukan skrip. Output di-escape terhadap formula spreadsheet; input tidak diteruskan ke CLI. **Batas final**: **10 MiB dan 10.000 baris, keduanya berlaku**; konfigurasi dengan plafon keras 20 MiB / 20.000 baris, dinaikkan hanya setelah uji beban. Proses streaming/chunk; file sementara TTL 24 jam. Impor tidak menghasilkan jurnal, pembayaran, atau isolir.

**AC-CSV:** leading zero telepon terjaga; koma dalam alamat; baris gagal tidak merusak baris lain; preview lintas tenant ditolak; unggah ulang tidak menggandakan; username duplikat dalam tenant ditolak; password tidak muncul pada laporan.

---
# 12 Billing internet dan penagihan

**BIL-01** Invoice: line item, service period, due date, currency IDR, nominal, discount, tax configuration, outstanding. Status invoice internet: `draft, open, partial, paid, void`, terpisah dari payment submission. Unik (tenant, service, periode, jenis) mencegah scheduler ganda. Harga disnapshot; perubahan harga paket tidak mengubah invoice lama. Nomor dokumen unik per tenant dan jenis (`INV-{kode_tenant}-{YYYYMM}-{urut}`), namespace berbeda dari invoice SaaS. Dokumen memuat bahasa terbit (I18N-04).

**BIL-02** Kebijakan penagihan per paket: siklus `fixed_monthly` (periode = bulan kalender) atau `anniversary` (aturan jangkar SUB-04). `due_day` hanya berlaku pada fixed_monthly, memilih tanggal clamp pertama pada/selepas due default; waktu `prepaid` atau `postpaid`; `first_period_policy` (`full`, `prorata_daily`, `free_until_next_period`; default `full`). Default: prepaid diterbitkan 7 hari sebelum periode mulai dan jatuh tempo pada tanggal mulai periode; postpaid diterbitkan pada akhir periode dan jatuh tempo 7 hari sesudah terbit (konfigurasi). Masa kalender, uptime Hotspot, dan kuota byte adalah konsep berbeda.

Periode fixed_monthly pertama dari tanggal aktivasi sampai awal bulan berikut: full=harga penuh untuk potongan itu; prorata_daily=harga×hari_aktif/hari_kalender_bulan, ceil ke Rp100 sesuai policy tersnapshot; free_until_next_period=nol. Anniversary full=satu term penuh; dua policy lain ditolak kecuali batas kalender pertama didefinisikan eksplisit pada paket. Prepaid issue=start-7 hari atau segera saat service baru bila tanggal itu lewat, due default=start dan tidak sebelum issue. Postpaid issue=end_date eksklusif pukul00lokal, due=issue+7 hari; due_day fixed_monthly memilih tanggal clamp pertama pada/selepas due default. Tampilkan seluruh tanggal dalam preview.

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

**ACT-01** Kebijakan: isolir otomatis sesudah due date + grace (**default grace 3 hari**, rentang 0–30, per tenant). **Policy isolir default nonaktif per tenant**; layanan hasil migrasi `automation_enabled=false`. Sebelum mengaktifkan, Owner menjalankan **simulasi** "siapa yang akan diisolir" (ID simulasi berlaku 24 jam) dan meninjau paket, due date, saldo pembuka. Isolir otomatis hanya bagi layanan pada router `radius_authoritative`. Aktivasi (pembukaan) selalu manual oleh Owner/Admin Pembayaran (atau delegasi).

**ACT-02** Scheduler hanya membuat kandidat (harian 01:00 zona tenant dan saat perubahan due/payment). Worker mengunci scope service, membaca payment dan policy terbaru, memeriksa exemption, termination, hold, dan observed state. Job memuat `policy_version`; bila policy berubah/dimatikan sebelum eksekusi, job `cancelled` (`policy_changed`); scheduler menilai ulang.

**ACT-03** Suspend melalui Reject+Disconnect dan bukti positif sesi menurut [RADIUS.md](RADIUS.md) §7. Absennya interim60 detik tidak membuktikan sesi terputus pada interval300 detik. Auth test harus menggunakan transport/secret yang sah dan Reject karena policy target. Restore wajib Accept dengan atribut normal; verified_active tidak berarti perangkat sudah online. Semua sesi target lintas NAS/jalur terkelola dan kontrol non-target diperiksa.

**ACT-04** Isolir terbatas (walled garden/halaman pembayaran) tersedia opsional pada R3 melalui pool dan address-list isolir yang membutuhkan aturan router milik operator (templat tersedia); platform tidak membuat aturan itu diam-diam. HTTPS arbitrer tidak dijanjikan redirect. IPv4-only tidak diklaim memblokir IPv6; dual stack diuji.

**ACT-05** Bulk activation: snapshot pilihan → ringkasan → validasi hak/pembayaran → job anak per service → verify → hasil per item. Akun `security_hold`/`technical_hold`/`manual_hold` tidak dibuka hanya karena invoice lunas (override butuh izin + alasan). Simpan alasan isolir; aktivasi hanya membalik perubahan isolir milik aplikasi yang revision-nya masih cocok.

## Kondisi balapan

| Kejadian | Hasil |
|---|---|
| Lunas sebelum scheduler | Tidak ada kandidat |
| Lunas sesudah enqueue, sebelum eksekusi | Preflight membatalkan job lama |
| Lunas saat eksekusi berjalan | Uang dicatat; rekonsiliasi; `paid-awaiting-activation` bila terlanjur isolir |
| Lunas saat router/RADIUS terputus | Uang sah; tidak otomatis mengubah akun menjadi active. Aktivasi manual terpisah; verifikasi NAS yang diperlukan boleh waiting_dependency |
| Aktivasi dua kali | Satu logical action; periode tidak diperpanjang dua kali |

Perubahan status akun RADIUS adalah transaksi database (atomik dengan keputusan bisnis); Disconnect/CoA adalah langkah job terpisah. Kompensasi terdefinisi, audit tersimpan. **AC-ACT:** payment sebelum enqueue, sesudah enqueue, saat eksekusi, router timeout setelah Disconnect, restart worker, retry ganda, IPv6, manual hold, router berstatus `radius_shadow` (isolir tidak dijamin dan UI menyatakannya).

---

# 14 Hotspot, voucher, dan reseller

**HSP-01** Hotspot memakai RADIUS (autentikasi pengguna, MAC-auth opsional, accounting). Hotspot user hasil adopsi menjadi `access_account` kind `hotspot`; setiap user terkelola = satu unit kuota. **HSP-02 Voucher (R3)**: batch voucher dengan paket (durasi, batas data, kecepatan, masa berlaku), kode acak, cetak/ekspor; kontrol internal Expiration/Max-All-Session dan reply Session-Timeout/Mikrotik-Total-Limit/Mikrotik-Rate-Limit sesuai resolver RADIUS.md §5; bukan semua atribut itu dikirim sebagai reply. Voucher yang diterbitkan dan masih valid dihitung dalam kuota (SUB-01); penerbitan batch mereservasi kuota atomik. **HSP-03** Pencabutan, perpanjangan, dan penggantian voucher memiliki jejak audit; voucher kedaluwarsa tidak dihitung.

**AGT-01 Agen/reseller**: akun agen (bundel terbatas) membeli/menjual voucher dengan harga agen dan komisi; portal agen menampilkan stok, penjualan, komisi, setoran. **AGT-02** Penjualan agen mengikuti kebijakan pengakuan pendapatan voucher (`FINANCE.md`, bagian 6); komisi sebagai utang komisi sampai dibayar. **AGT-03** Batas jumlah agen per paket (TEN-02).

**HSP-04** Hotspot + PCC pada satu router tidak didukung (bagian 20). Hotspot + single WAN atau failover didukung setelah lab login, walled garden, return traffic, dan failover lulus. **HSP-05** FUP/kuota data berbasis accounting RADIUS (R3): batas harian/bulanan, aksi saat terlampaui (turunkan kecepatan melalui atribut, atau isolir sesuai kebijakan paket), diuji dengan counter dan Disconnect/CoA; bukan dasar penagihan uang kecuali paket berbasis kuota diaktifkan dan diuji.

**AC-HSP:** batch voucher mereservasi kuota; voucher dipakai pada dua router tenant yang sama tetap satu sesi (`Simultaneous-Use`); kedaluwarsa menolak login; kuota data habis memicu aksi kebijakan; penjualan agen menghasilkan komisi dan jurnal benar.

---

# 15 Akuntansi dan kontrol transaksi

Rincian: `FINANCE.md`. **ACC-01 Double-entry ledger**: setiap perusahaan memiliki buku terpisah (COA, fiscal period, opening balances, journal entry/lines, subledger). **Setiap entry seimbang: jumlah debit = kredit lintas semua baris**, satu tenant, mata uang IDR, satu periode. Uang `numeric(20,2)`; tanpa float; multi-currency di luar cakupan. Buku platform terpisah (cakupan `platform`) untuk pendapatan SaaS; tidak tampil pada buku tenant dan tidak dilihat Super Admin biasa. Kerangka default **SAK EMKM** (dapat SAK Entitas Privat) dengan `FrameworkVersion` dan tanggal efektif; aplikasi membantu penerapan, tidak menyatakan kepatuhan otomatis.

**ACC-02 Pengakuan pendapatan**: invoice tidak selalu berarti pendapatan. Bukti belum terverifikasi tidak menjurnal Bank. Templat posting berversi dengan `source_document_id` dan event key unik. Prabayar: invoice belum dibayar tidak dijurnal; pembayaran → pendapatan diterima di muka → pengakuan harian diposting bulanan (sisa pembulatan ke periode terakhir); pascabayar: piutang dan pendapatan saat terbit pada akhir periode; selisih lebih = kredit pelanggan (bukan pendapatan). Voucher mengikuti kebijakan tenant. Contoh dan akun: panduan bagian 3 dan 6.

**ACC-03** Penerimaan: transfer/e-wallet, tunai, kolektor (akun clearing, setoran), biaya payment fee, alokasi lintas invoice. **ACC-04** Piutang: aging, cadangan kerugian opsional, write-off dengan dokumen koreksi. **ACC-05** Voucher/agen: pendapatan diterima di muka, komisi sebagai utang. **ACC-06** Perangkat/persediaan/aset: klasifikasi menurut tujuan, ambang kapitalisasi (default Rp2.500.000), rata-rata bergerak, penyusutan garis lurus (umur default 4 tahun), disposal; pajak sebagai konfigurasi (`TaxRule`) tanpa tarif universal hardcode.

**ACC-07 Rekonsiliasi bank/e-wallet**: impor mutasi (CSV terkonfigurasi) dengan kunci unik, pencocokan, split/merge, exception; saldo statement ≠ saldo buku. **ACC-08 Tutup periode** (bulanan, tahun): daftar periksa, kunci, reversal/adjustment, reopen dengan permission+reautentikasi+alasan, tidak melintasi tutup tahun. **ACC-09** Saldo pembuka. **ACC-10** Laporan (bagian 16). **ACC-11 Penegakan teknis**: role runtime tanpa INSERT/UPDATE/DELETE pada tabel jurnal; prosedur `ledger.post_entry` (SECURITY DEFINER) dengan period lock; constraint trigger deferred debit=kredit; trigger immutability ([ARCHITECTURE.md](ARCHITECTURE.md) §8). **ACC-12** Buku platform.

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

SAK EMKM mensyaratkan minimum laporan posisi keuangan, laba rugi, dan catatan atas laporan keuangan dengan informasi komparatif; label "patuh standar" tidak dipakai tanpa melengkapi syarat kerangka. Laporan memuat periode, basis, waktu generasi, status penutupan; dari saldo pembuka belum disetujui berlabel "Belum final". Export dengan periode dan waktu generasi; Super Admin tidak melihat buku tenant.

**AC-REPORT:** total subledger piutang = control account setelah rekonsiliasi; periode tertutup menolak posting mundur; refund memiliki tautan sumber; laba berbeda dari kas bila ada prabayar/piutang; laporan lintas dimensi menjumlah ke total yang sama.

---
# 17 Monitoring dan pengelolaan insiden

**MON-01** Koleksi dibagi: health router, interface traffic, status sesi (dari accounting RADIUS), WAN probes, jobs, ACS last inform, kesehatan RADIUS. Akun baca dan bounded calls. REST bukan streaming monitor. Setiap metric membawa `source`, `observed_at`, `collected_at`, `unit`, `quality`.

**MON-02** Parameter terkunci (konfigurasi; target uji, bukan janji realtime): health/traffic 60 detik; inventaris 15 menit; **detail router 15 detik** hanya saat halaman dibuka, dalam budget, dengan shared cache. Jitter, backoff, deadline, dan kuota per tenant mencegah overload. Sample `stale` bila usia > 3× interval. SNMPv3 baca-saja opsional.

**MON-03** Counter delta menangani restart/wrap dan interface berubah. Gap tetap gap, bukan nol. WAN dan LAN tidak dijumlah ganda. Traffic interface bukan dasar billing byte. Pemakaian data per layanan berasal dari accounting RADIUS (RAD-07). Metrik per pelanggan (high-cardinality) tidak masuk Prometheus; data per layanan tinggal di PostgreSQL (`usage_daily`).

**MON-04** Probe tiap ISP dipaksa pada jalurnya; ping sukses lewat ISP lain tidak membuktikan ISP target sehat. Minimal 2 target independen per ISP; debounce down setelah 3 kegagalan berturut-turut, up setelah 5 sukses (konfigurasi, divalidasi lab). Health server-ke-router ≠ pengalaman pengguna akhir.

**MON-05** Insiden: sumber, severity, start/end, resource, evidence, acknowledgement, owner, maintenance window. Status router: `healthy`, `degraded`, `management_unreachable` (3 polling gagal berturut-turut), `unmonitored`, `stale`. Status RADIUS per router: sesi masuk/keluar, rasio autentikasi gagal, accounting terakhir; lonjakan kegagalan memicu insiden. Dampak ke layanan dikorelasikan hanya bila topologi tersedia. **Kegagalan collector = insiden platform ("data tidak tersedia")**, bukan ribuan router down. Notifikasi dedup (tenant+resource+signal), rate limit, recovery notice sekali per transisi.

**MON-06** Dashboard owner menggabungkan jaringan dan pekerjaan bisnis tanpa mengungkap destination browsing. Packet capture, torch massal, speed test yang menyaturasi ISP, dan connection table penuh bukan polling default. Grafana opsional internal dengan otorisasi query tenant; tenant tidak memperoleh datasource global.

**AC-MON:** restart router tidak menghasilkan traffic negatif/spike fiktif; collector mati → stale; satu uplink putus diuji dari jalur benar; kegagalan NTP terdeteksi; tenant tidak membaca metrik tenant lain; data expired dihapus sesuai retensi; sesi hilang akibat RADIUS terputus dibedakan dari pelanggan offline.

---

# 18 Backup dan pemulihan MikroTik

**BKP-01** Jadwal tenant: router, harian/mingguan/custom, timezone, notifikasi, jenis file. Retensi rutin maksimal **100 generasi berhasil per router**. Satu generasi dapat terdiri dari binary + export. Generasi ke-101 menggantikan tertua hanya setelah semua artifact wajib generasi baru tersimpan dan valid. Gagal/partial tidak mengurangi 100 generasi valid. Backup manual dan pre-change masing-masing 10 per router (FIFO per kategori). Backup otomatis pre-change dibuat sebelum cutover RADIUS dan sebelum perubahan WAN.

**BKP-02** Binary backup dienkripsi dengan password eksplisit **dibangkitkan platform per router** (32 karakter acak), disimpan terenkripsi (kunci data per tenant dibungkus kunci utama di luar database). Kosong bukan dianggap terenkripsi. Owner memperoleh kunci pemulihan lewat reautentikasi + MFA dengan audit. Binary memuat data sensitif dan MAC; restore ditujukan untuk perangkat/kondisi sesuai. Export tidak memuat rahasia secara default (`show-sensitive` hanya atas pilihan eksplisit Owner) dan bukan backup lengkap. Data pengguna PPPoE/Hotspot berada pada basis RADIUS platform sehingga ikut recovery platform (BKP-05), bukan hanya backup router.

**BKP-03** Transfer berkas: API memerintahkan pembuatan file; binary tidak ditransfer via satu respons API. **Baseline: RouterOS Fetch upload SFTP melalui VPN ke receiver terbatas** yang mendengarkan hanya pada alamat tunnel server dengan akun/path scoped per router (rotasi per generasi), tanpa shell dan tanpa path bebas. Kontrol identitas server: tunnel WireGuard terautentikasi dua arah, tujuan dipin /32, verifikasi host-key bila RouterOS mendukung, kredensial tidak muncul di log. **Cadangan**: adapter *pull* (SFTP/SCP dengan host key dipin saat enrollment). Bila keduanya gagal lab (TK-505), backup tidak diaktifkan (G1). **Ukuran maksimum default 64 MiB per artifact**. HTTP fetch bukan baseline untuk binary.

Generasi: staging → received → size/hash verified → enkripsi + durable storage → committed → perubahan membership retensi → cleanup/prune asinkron. Hash server membuktikan integritas penyimpanan. Sinyal selesai harus terautentikasi dan diverifikasi bersama ukuran.

**BKP-04** Simpan router/model/versi/timezone, type, size, hash, key reference, status, audit unduh. Setelah commit, hapus hanya file sementara buatan aplikasi di router. Unduh terotorisasi; **signed URL 5 menit**, diperiksa saat penerbitan dan penukaran, tidak lintas tenant, tidak dicatat di log.

**BKP-05** Off-host backup platform melindungi database (termasuk skema `radius`), file, key material, metadata, konfigurasi FreeRADIUS, registry VPN, dan datastore ACS. Restore router memerlukan kompatibilitas, dampak reboot, jalur pemulihan, dan persetujuan spesifik; tidak otomatis; **tidak ada tombol restore umum sebelum G1 untuk model/versi tersebut**.

**BKP-06** "100" = generasi rutin retained yang terlihat di katalog setelah finalisasi. Headroom staging `max(5 GiB, 2 × artifact terbesar × transfer bersamaan)`. Watermark disk: peringatan 80%, hentikan backup baru 90%; **backup valid tidak pernah dihapus untuk memberi ruang**. Finalisasi mengubah membership katalog transaksional; penghapusan blob lewat antrean cleanup yang dapat dipulihkan.

**AC-BKP:** generasi 101 menghapus hanya tertua setelah commit; transfer putus tidak menghapus backup valid; disk penuh menghasilkan error; file besar tidak terpotong; akses lintas tenant ditolak; crash antara commit, katalog, dan delete diuji; restore sampel di lab membuktikan prosedur dan keterbatasan.

---

# 19 ACS, TR-069, dan perangkat pelanggan

Rincian: `ACS.md` (R3).

**ACS-01** GenieACS (CWMP, NBI, FS, UI internal) dengan MongoDB internal; adapter ACS satu-satunya jalan tenant. CPE harus mendukung TR-069, mengetahui ACS URL/credential, dan punya jalur IP; VPN router tidak mendaftarkan ONT otomatis. NBI/database tidak diekspos.

**ACS-02** Mapping memakai Device ID internal, DeviceID GenieACS, serial, OUI, product class, plus klaim enrollment tenant terautentikasi. MAC opsional dan bukan bukti kepemilikan.

**ACS-03** CPE baru masuk karantina. Autentikasi per-device (kredensial unik dari klaim enrollment); accept-any dilarang. Konflik serial/DeviceID ditahan. Tags hanya metadata.

**ACS-04** Capability per model: read identity, Wi-Fi, associated devices, WAN/PPPoE, diagnostics, reboot, firmware, optical, factory reset, connection request UDP. Model/firmware di luar matriks = `unsupported`. Tidak ada model yang dinyatakan didukung sebelum lulus lab; daftar model pertama ditetapkan oleh hasil G1. Virtual parameter menjembatani TR-098/TR-181; indeks instance ditemukan lewat discovery. Tenant tidak mengirim script/preset arbitrer.

**ACS-05** Status task perangkat terpisah dari job outcome uncertain/recovery_required menurut [ACS.md](ACS.md) §6. Tugas asinkron: `queued → waiting_inform → running → verifying → succeeded/failed/expired/cancelled`. API accepted ≠ executed; task ID disimpan sebelum retry; verifikasi lewat pembacaan ulang atau "verifikasi tidak tersedia".

**ACS-06** Rotasi password PPPoE terkoordinasi antara ACS dan RADIUS (alur versi kredensial dengan jalur manajemen independen atau recovery teruji menurut [ACS.md](ACS.md) §8); tidak atomik; pemulihan dicatat. Isolir via RADIUS dapat memutus jalur ACS yang berbagi koneksi PPPoE; WAN manajemen/VLAN dirancang operator. Firmware/reboot dijadwalkan; factory reset bukan tombol rutin.

**ACS-07** Inventaris CPE terhubung ke Service dan ODP/port; adapter OLT pada R4 per model. **ACS-08** Keamanan: TLS wajib pada CWMP, rate limit, tanpa kredensial di log. **ACS-09** Matriks kompatibilitas per model. **ACS-10** Pengujian T11.

**AC-ACS:** dua tenant dengan serial konflik tidak bercampur; tugas pending tidak tampil sukses; parameter optik tidak tersedia → "Tidak didukung"; firmware/model salah ditolak; gagal auth CPE tidak menerima kredensial layanan; CPE di belakang NAT diuji dengan dan tanpa UDP connection request.

---

# 20 Wizard jaringan dan uplink (R4)

**CFG-01** Jaringan pelanggan dan uplink adalah menu/wizard independen; menggunakan modul pelanggan tidak mensyaratkan mengubah WAN. Default memakai server PPPoE/Hotspot existing. Membuat bridge, VLAN, DHCP, pool, server PPPoE/Hotspot baru (templat pada `ROUTEROS.md`) memerlukan pilihan eksplisit, validasi kapasitas/subnet, dependency graph, review. Tidak ada port fisik wajib. Mengubah port pada bridge aktif dianggap berdampak layanan. Templat router baru (penggantian perangkat) membuat pool/profil yang dirujuk binding paket sehingga akun RADIUS langsung dapat login.

**WAN-01** Static WAN: interface, IP/prefix, gateway (prefix wajib). DHCP: baca lease dan perubahan gateway. Overlap subnet modem, gateway sama pada uplink berbeda, PPPoE WAN, VRF, VLAN uplink = `unsupported` sampai templat diuji. DNS tidak ditebak sebagai gateway.

**WAN-02** Mode: single, primary-backup, PCC+failover, weighted PCC. PCC membagi koneksi menurut classifier, bukan bonding per sesi. Bobot dari kapasitas yang diisi owner dengan jumlah bucket wajar. Failover recursive berjalan di router (tidak bergantung server SaaS) dengan multi-target dan hysteresis (MON-04). Trafik RADIUS/VPN ke server harus tetap keluar melalui jalur yang valid saat failover; templat memeriksa rute endpoint VPN.

**WAN-03** Templat memeriksa local destinations, trafik menuju router, endpoint VPN, NAT, connection marks, routing tables, route balik, DNAT, queue/FastTrack, DNS probes. FastTrack tidak diubah massal; templat hanya menambah pengecualian pada objek miliknya setelah lulus lab. Sesi existing dapat terputus saat IP publik berubah.

**WAN-04** Aturan topologi terkunci: (a) **Hotspot + PCC pada satu router tidak didukung** (preflight memblokir PCC bila Hotspot server aktif); (b) Hotspot + single WAN atau failover recursive pada main table didukung hanya setelah lab login, walled garden, return traffic, dan failover lulus; (c) PCC hanya untuk router tanpa Hotspot (PPPoE/DHCP) atau topologi gateway terpisah yang lulus lab.

**CFG-02** Setiap apply menyimpan precondition, planned diff, backup valid, versi templat, ownership, health checks. Kompensasi hanya objek yang diubah dan bila revision masih cocok. Tidak ada global reset, flush conntrack, reboot, atau restore binary sebagai rollback rutin. Safe Mode bukan transaksi API. Kandidat *recovery hook* (skrip+scheduler bernamespace yang mengembalikan objek milik plan setelah TTL kecuali dibatalkan server) aktif hanya bila lulus lab (T13). Koneksi hilang setelah apply → `uncertain`/`recovery_required`.

**AC-WAN:** gangguan tiap ISP, recovery flapping, DHCP renew, akses VPN dan RADIUS selama failover, internet router, inbound DNAT, established flow, Hotspot login sesuai matriks. Perubahan live hanya untuk topologi dengan prosedur pemulihan terbukti.

---

# 21 Tiket, inventaris, portal, dan notifikasi

**OPS-01** Customer, service, device, dan network location dihubungkan agar tiket memiliki konteks tagihan, sesi (accounting), CPE, router, kejadian. Data tidak diketahui = "unknown".

**OPS-02** Inventaris: serial, vendor/model, kepemilikan, status stock/assigned/repair/retired, lokasi, histori assignment, biaya perolehan (ke akuntansi). ODP: kapasitas port dan reservasi; alokasi port transaksional. Kabel/splitter pasif butuh input teknisi.

**OPS-03** Tiket: `open → triaged → assigned → in_progress → resolved → closed` dengan reopen; relasi ke incident bersama; prioritas, evidence, jadwal, teknisi, foto, checklist, material, outcome. **Work order** (instalasi, perbaikan, pencabutan) dengan SLA internal tenant; material terpakai mengurangi persediaan; lokasi/foto pribadi dibatasi hak dan retensi. Prospek dan survei (LIF-01) memakai alur yang sama.

**OPS-04** Portal pelanggan terpisah dari login operator: layanan, invoice, kwitansi, bukti bayar, tiket, pengumuman, opsi Wi-Fi yang diizinkan, pilihan bahasa. Upload bukti tidak membuka isolir; approval + aktivasi tetap manual. Tidak ada akses raw ACS/router. Portal agen/kolektor terpisah dengan scope sempit.

**OPS-05 Notifikasi** (R3; default **off**): kanal per perusahaan = email SMTP milik tenant dan adapter provider (mis. WhatsApp) yang dikonfigurasi tenant. Platform tidak mengirim pesan kepada pelanggan internet; pengiriman nyata hanya setelah Owner tenant mengaktifkan. Templat per bahasa. Penerima diverifikasi dari customer record; password penuh tidak dikirim lewat notifikasi umum; retry dengan dedup key dan rate limit. Email transaksional akun SaaS dikecualikan dari batasan ini.

**Batas OLT/non-MikroTik:** adapter resmi/terdokumentasi per model (API/SNMP/SSH); ACS tidak menggantikan provisioning OLT; OLT/ODP awal boleh inventaris manual; parser CLI wajib fixture dan versi firmware.

**AC-OPS:** portal pelanggan tidak membaca invoice orang lain dengan mengganti ID; reservasi ODP tidak ganda; tiket menyimpan perubahan assignment; material work order mengurangi persediaan dan menjurnal; portal agen hanya melihat datanya.

---
# 22 Model data dan kontrak API

**DATA-03** Endpoint dan schema mengikuti [ARCHITECTURE.md](ARCHITECTURE.md), prefix /api/v1. **API-01** Idempotency-Key untuk uang/provisioning dan expected_revision untuk perubahan; 202 berarti antrean, bukan efek selesai. **API-02** Tenant dari membership terverifikasi; setiap objek bulk diperiksa. Body bertipe, tidak menerima perintah/SQL/URL bebas. AC-DATA: FK lintas tenant, username/invoice race, timezone, dan retry key diuji di PostgreSQL nyata.

Detail tabel, constraint, kode error, job states, dan migration SQL berada di ARCHITECTURE; OpenAPI dibuat bersama vertical slice sebelum UI memakai endpoint. Tidak perlu menciptakan tabel semua fase pada fondasi R1.

---

# 23 State machine dan ketahanan pekerjaan

**JOB-01** Tujuh dimensi service tetap terpisah: lifecycle, billing_eligibility, isolation_reason, desired_network_state, observed_network_state, connection_state, pending_job. Lunas bukan online dan enabled bukan tersambung. Hold keamanan/teknis/manual mengalahkan kelayakan bayar.

**JOB-02** Commit domain + audit + outbox atomik; delivery at-least-once, handler idempoten. **JOB-03** Satu penulis per router, fairness tenant, recovery/pembayaran tidak menunggu backup. **JOB-04** Cancel hanya sebelum efek tujuan dan semua pengiriman outstanding sudah difence; partial adalah ringkasan bulk, stale adalah kesegaran. **JOB-05** Lease DB tidak menarik kembali perintah yang telah dikirim; timeout setelah kirim menjadi uncertain dan memerlukan readback, bukan retry buta.

Enum dan transisi tunggal: [ARCHITECTURE.md](ARCHITECTURE.md). AC-JOB: crash sebelum/sesudah commit/kirim/ack serta proses lama hidup kembali tidak menggandakan efek.

---

# 24 Keamanan, privasi, dan operasional

**SEC-01** TLS, Argon2id, MFA baseline pada §2, reauth, session revocation, CSRF, rate limit. **SEC-02** Connector hanya target registry terverifikasi; cegah SSRF/redirect/DNS rebinding. **SEC-03** Typed adapter, validasi upload privat + scanner fail-closed, export CSV aman. **SEC-04** Super Admin tidak otomatis membaca PII/ledger/secret tenant; SupportGrant Owner scoped+expiry+audit, tanpa reveal secret. **SEC-05** Filtering aplikasi + composite FK + ENABLE/FORCE RLS; runtime non-owner/non-superuser/non-BYPASSRLS, konteks tenant transaction-local.

**OPS-SEC** Retensi log/idempotency menurut defaults; audit finansial mengikuti retensi finansial. Offboarding menyediakan ekspor terenkripsi Owner, recovery dan pencabutan komponen tanpa reset router.

**PDP-01** DPA dan peran tenant/platform dijelaskan; **PDP-02** akses/koreksi/export/anonimisasi dengan pengecualian retensi keuangan; **PDP-03** minimisasi PII/foto/lokasi/log; **PDP-04** penanganan insiden dan pemberitahuan mengikuti runbook OPERATIONS; **PDP-05** persetujuan pemasaran terpisah. Retensi finansial minimum 10 tahun dan legal hold dipertahankan. Dasar hukum, clock operasional dan penanggung jawab: [OPERATIONS.md](OPERATIONS.md).

AC-SEC: semua resource fase aktif diuji negatif untuk IDOR, tenant leak, SSRF, injection, CSRF, replay, privilege, upload/download, RADIUS, dan kebocoran secret. Tidak ada klaim kepatuhan ASVS/standar penuh hanya karena checklist tersedia.

---

# 25 Kapasitas target dan pemulihan platform

Skenario awal 1.000 perusahaan × 2 router × 300 layanan menghasilkan 2.000 router dan 300.000 akun; accounting 300 detik sekitar 1.000 paket/detik jika semua sesi aktif. Ini input perencanaan, bukan hasil benchmark.

**NFR-01** Target p95 list/enqueue ≤2 detik, autentikasi RADIUS ≤100 ms pada beban normal yang diprofilkan, aktivasi sederhana router sehat ≤60 detik; uji query khusus 100.000 service/tenant tidak mengubah kuota komersial. **NFR-02** RPO ≤15 menit dan RTO ≤4 jam adalah target drill, bukan SLA. **NFR-03** Rilis kapasitas 10→100→1.000 tenant berdasarkan ukuran workload, resource, load/soak/restore. **NFR-04** Saat pusat gagal, hasil sesi existing dan login baru mengikuti batas protokol/perangkat yang diuji; jangan menjanjikan semua sesi tetap hidup tanpa batas. Rekonsiliasi payment/policy terkini sebelum backlog mutasi berjalan lagi.

Profil beban, HA, dan DR: [OPERATIONS.md](OPERATIONS.md). Tidak perlu menyiapkan Kubernetes, sharding atau edge di R1 untuk mengejar angka target.

---

# 26 Pengujian penerimaan dan gerbang rilis

[ACCEPTANCE.md](ACCEPTANCE.md) memiliki skenario T01–T24, kriteria G0–G5, serta gate per fitur. [test-cases.json](test-cases.json) menyimpan rincian kasus dan assertion yang dipertahankan dari baseline, tanpa salinan Markdown kedua. Status awal seluruh kasus NOT_RUN; pengukuran aktual ditulis saat build.

Done per vertical slice: schema/migration + service + API + UI + happy/error/security tests + dokumentasi dan bukti sesuai lingkungannya. Kode yang lulus simulator belum verified_lab. Fitur QA sandbox dapat diuji sebelum release flag produksi aktif; gate tidak menjadi siklus yang menghalangi uji untuk memenuhi gate itu sendiri.

---

# 27 Prioritas pelaksanaan

Bangun R1 sampai alur tenant→router→adopsi→RADIUS→pelanggan→backup/monitoring dapat dipakai. Lanjut R2 sampai invoice→pembayaran→aktivasi manual→pembukuan berjalan end-to-end. Sesudah itu R3 dan R4 sesuai fase di §1. Semua fase tetap kebutuhan produk; tidak ada penghapusan diam-diam.

[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) mengatur urutan milestone; [tasks.json](tasks.json) adalah satu backlog 85 ID TK, dengan dependency. [MASTER_PROMPT.md](MASTER_PROMPT.md) adalah perintah untuk agent. Hindari menghabiskan fase awal untuk registry, laporan audit baru, abstraksi multi-provider, atau komponen masa depan.

---

# 28 Sumber dan keputusan audit

Sumber proyek sebelum konsolidasi adalah commit 19b954308a7573bc449f551400d053fba1c089d7. Semua 77 path ditelusuri pada [AUDIT_REPORT.md](AUDIT_REPORT.md). Audit tersebut juga membedakan keputusan produk yang dipertahankan, koreksi teknis, dan pilihan engineering baru yang eksplisit. Tidak ada sign-off profesional atau tes perangkat yang direkayasa.

Dokumentasi resmi yang diverifikasi dan referensi versi implementasi berada pada laporan audit; implementer memeriksa lagi API/dependency untuk exact version yang dipakai. Nama aplikasi berasal dari [branding.json](branding.json), bukan identitas database/API/resource.

---
