# MicroTix — spesifikasi UI dan alur operator

Perilaku dan harga dimiliki PRODUCT; API/status dimiliki ARCHITECTURE; domain cutover dimiliki RADIUS. Implementasikan halaman berdasarkan fase, bukan semua menu sekaligus. Nama produk dari resolved branding; default id, en wajib.

## Prinsip yang mengikat

Bahasa sederhana di permukaan, detail teknis di panel lanjutan. Pekerjaan harian mengutamakan pelanggan, tagihan, tindakan berikutnya. Yang tidak diketahui ditulis "tidak diketahui" (bukan nol). Sukses sebagian dilaporkan per layanan. Aksi yang mengubah perangkat selalu menampilkan status job; "berhasil" hanya setelah diverifikasi. 202/toast bukan hasil router.

---

# 1 Arsitektur informasi dan peran

| ID | Route konseptual | Isi utama dan fase |
|---|---|---|
| U01 | `/` | Landing, fitur tersedia, paket, masuk, daftar; R1 |
| U02 | `/register`, `/login` | Akun, verifikasi email, TOTP, pemulihan, pembuatan perusahaan; R1 |
| U03 | `/app/{tenant}/overview` | Dashboard pekerjaan harian; R1 bertahap |
| U04 | `/app/{tenant}/customers` | Daftar dan detail customer/service; R1 (kolom tagihan/isolir R2) |
| U05 | `/app/{tenant}/routers/new` | Enrollment dan skrip bootstrap; R1 |
| U06 | `/app/{tenant}/routers/{id}` | Status VPN/API/RADIUS, capability, discovery, lepas/ganti router; R1 |
| U07 | `/app/{tenant}/imports/router` | Adopsi dan migrasi akun existing ke RADIUS (8 langkah); R1 |
| U08 | `/app/{tenant}/imports/csv` | Template, validasi, preview, hasil; R1 |
| U09 | `/app/{tenant}/billing` | Invoice, pembayaran, filter periode; R2 |
| U10 | `/app/{tenant}/activation` | Kelayakan dan hasil aktivasi massal; R2 |
| U11 | `/app/{tenant}/finance` | Kas/piutang, ledger, laporan; R2 |
| U12 | `/app/{tenant}/backups` | Jadwal, histori, unduhan; R1 |
| U13 | `/app/{tenant}/monitoring` | Router, interface, insiden; R1 bertahap |
| U14 | `/admin/subscriptions` | Approval platform, rekening, kondisi tenant; R1 |
| U15 | `/app/{tenant}/devices` | ACS, inventaris, tiket/field work; R3 |
| U16 | `/app/{tenant}/jobs/{id}` | Pusat pekerjaan lintas modul; R1 |
| U17 | `/app/{tenant}/configuration` | Wizard pelanggan terpisah dari uplink; R4 |
| U18 | `/app/{tenant}/settings` | Tim, paket aplikasi, bahasa, audit, support grant; R1 |
| U19 | `/app/{tenant}/radius` | Basis akun akses RADIUS, status per router, cutover dan rollback; R1 |
| U20 | `/app/{tenant}/vouchers`, `/collectors`, `/agents` | Voucher Hotspot, agen/reseller, kolektor dan setoran; R2–R3 |

**Navigasi desktop: sidebar 5 kelompok** yang memetakan 13 menu produk PRD (ditambah tautan **Bantuan**, bukan menu produk): **Operasional** (Beranda, Pelanggan, Paket dan Profile, Tagihan dan Pembayaran, Gangguan dan Teknisi) · **Jaringan** (Router dan Monitoring, Backup, Perangkat ACS, Inventaris dan Peta, Konfigurasi) · **Keuangan** (Keuangan) · **Perusahaan** (Perusahaan dan Tim, Paket Aplikasi) · **Bantuan**. Menu Keuangan mengikuti role. Modul belum `release_enabled` disembunyikan; halaman roadmap boleh menjelaskan status tanpa tombol palsu.

**Header (final):** ruang tenant memakai header terang (surface putih, garis bawah border). Ruang `/admin` (Super Admin) memakai header **navy `#0F2A4A` dengan teks putih** plus label "ADMIN PLATFORM" agar jelas berbeda; kontras diuji pada implementasi.

Owner melihat seluruh menu tenant. Teknisi: pelanggan operasional, router, perangkat, backup berizin, tiket; nominal tagihan disembunyikan bila tak dibutuhkan. Admin Pembayaran: pelanggan, invoice, payment, aktivasi; tidak membuka konfigurasi WAN. Akuntan: Keuangan. Viewer: hanya baca.

Tenant switcher selalu tampak. Berpindah tenant dengan form belum tersimpan → "Simpan draft" atau "Batalkan perubahan"; pilihan checkbox tidak terbawa. Filter router/periode berada di header halaman.

---

# 2 Sistem desain dan komponen

Tema terang berorientasi tabel dan tugas. Warna bukan satu-satunya penanda status.

| Token | Nilai | Pemakaian |
|---|---|---|
| Background / surface | `#F4F6F8` / `#FFFFFF` | Halaman / kartu |
| Text / secondary | `#172B4D` / `#475569` | Konten / keterangan |
| Primary | `#1D4ED8` | Aksi utama, tautan, focus ring |
| Success | `#166534` pada `#DCFCE7` | Terverifikasi |
| Warning | `#92400E` pada `#FEF3C7` | Perlu tindakan / data usang |
| Danger | `#B91C1C` pada `#FEE2E2` | Gagal/berdampak; bukan untuk semua offline |
| Admin header | `#0F2A4A` (teks putih) | Hanya ruang `/admin` |
| Border | `#CBD5E1` | Batas visual |
| Tipografi | Sans-serif sistem; body 16, label 14, judul 24–32; tabel desktop ≥14 | Mobile tidak dikecilkan |
| Spacing / radius | 4, 8, 12, 16, 24, 32 / 8 | Ritme komponen |

Breakpoint: desktop ≥1200, tablet 768–1199, mobile <768. Target sentuh produk 44×44 px (WCAG 2.2 AA minimum 24×24). Kontras: teks normal 4,5:1, teks besar dan kontrol bermakna 3:1 — **diukur pada implementasi**. Fokus terlihat dan tidak tertutup sticky footer. [W1–W3]

**Komponen wajib:** AppShell, TenantSwitcher, PageHeader, FilterBar, DataTable, MobileServiceCard, StatusBadge, FreshnessLabel, JobProgress, BulkActionBar, ConfirmAction, FieldError, PermissionNotice, EmptyState, MetricCard, ChartWithTable, AuditTimeline — masing-masing punya default/loading/empty/error/disabled/focus bila relevan. Tombol primer maksimum satu per langkah; aksi destruktif terpisah dan menyebut objek; tombol disabled disertai alasan terlihat dekat kontrol (tooltip saja tidak cukup); tautan untuk navigasi, tombol untuk aksi. Tabel: sticky header, pagination server, column selector; detail luas pada halaman, bukan modal bertumpuk.

Form: label permanen, helper sebelum error, validasi server sebagai otoritas. Nominal berformat Rupiah, disimpan presisi. Prefix IP berpetunjuk `192.0.2.2/24` (contoh dokumentasi). Password tidak pernah di tabel, analytics, atau ringkasan error.

**StatusBadge (teks + warna + ikon):** Sukses/Terverifikasi (hijau), Perlu tindakan/Usang (kuning), Gagal (merah), Netral (abu), Dalam proses (biru). "Offline" memakai netral/kuning, bukan merah.

---

# 3 Alur tugas dan keputusan pengguna

| Alur | Urutan layar | Titik kontrol |
|---|---|---|
| Owner baru | U01 → U02 → U03 → U05 | Perusahaan dibuat sebelum router; Free otomatis |
| Router existing | U05 → U06 → U07 → U19 (cutover) → U04 | VPN dan API diverifikasi; adopsi database-only; cutover RADIUS terpisah dan dapat dibatalkan |
| Pindah/ganti router | U06 → U05 → U19 | Akun tidak diinput ulang; hanya klien RADIUS dan pool router baru |
| CSV pelengkap | U04 → U08 → preview → hasil U16 | Mode jelas; kosong tidak menghapus |
| Bayar internet | U09 → verifikasi → U10 → U16 | Uang tercatat dulu; aktivasi manual terpisah |
| Tagih tunai | U20 (kolektor) → setoran → U09 | Penerimaan tercatat "belum disetor" sampai diverifikasi |
| Jual voucher | U20 → batch → cetak/ekspor | Kuota direservasi saat batch diterbitkan |
| Bayar aplikasi | U18 → invoice → unggah bukti → U14 | Super Admin memeriksa dana |
| Gangguan | U03 → U13 → U06/U15 | Bukti, freshness, pekerjaan berikutnya |
| Backup | U06/U12 → jadwal → hasil → unduh | Per router; retensi 100; restore terpisah |


**U02 (final):** form daftar: nama, email, password (min. 12 karakter, indikator kekuatan), nama perusahaan. Verifikasi email lewat tautan (email transaksional). Login: email + password, lalu kode TOTP bila MFA aktif; kode pemulihan sekali pakai tersedia. Pemilih bahasa tersedia pada halaman daftar/login. Tidak ada WhatsApp OTP. Pesan gagal login/pemulihan password selalu sama ("Email atau password tidak cocok" / "Jika email terdaftar, tautan telah dikirim") agar tidak mengungkap akun. Operator tenant didorong mengaktifkan MFA saat login pertama; setiap aktor yang menjalankan izin sensitif wajib MFA+reauth sebelum aksi tersebut (dialog "Aktifkan verifikasi dua langkah untuk melanjutkan"). Peran platform wajib MFA. Reautentikasi dialog: "Konfirmasi identitas Anda" (password + TOTP), berlaku 10 menit.

**Checklist onboarding U03:** Buat perusahaan; Hubungkan router; Adopsi akun; Petakan paket; Lengkapi tagihan (R2; tidak memblokir); Undang tim. Progress = langkah selesai, bukan persentase tanpa dasar.

**Tambah pelanggan (U04):** enam field awal (nama/label, router, jenis layanan, paket, mulai layanan, kontak opsional); bagian Lanjutan (alamat, lokasi, IP, MAC/serial, ODP). Pilihan akhir dan keterangan dampak (router bersifat opsional; akun berlaku pada semua router perusahaan kecuali dibatasi):

| Pilihan | Keterangan yang tampil |
|---|---|
| Simpan draft | "Tidak mengubah router. Tidak memakai kuota." |
| Hubungkan akun existing | "Menyimpan pemetaan ke akun yang sudah ada. Tidak mengubah router. Memakai 1 kuota." |
| Buat akun | "Membuat akun pelanggan di basis RADIUS perusahaan. Tidak menulis ke router. Berlaku pada router yang sudah memakai RADIUS. Memakai 1 kuota." |
| Buat dan aktifkan | "Membuat akun dan mengaktifkannya (berlaku pada router yang sudah memakai RADIUS)." |

Draft tersimpan di server dengan waktu simpan; bila sumber berubah selama jeda: "Data router berubah sejak tinjauan terakhir" + validasi ulang. Batas draft per tenant ditampilkan bila hampir penuh. **ConfirmAction** mencantumkan perusahaan, jumlah layanan, jenis perubahan, dampak; snapshot ID dibekukan; worker tetap memeriksa kelayakan terbaru per item.

**Hasil pembuatan akun:** password ditampilkan **sekali** dengan tombol Salin dan peringatan "Simpan sekarang; menampilkan ulang memerlukan konfirmasi identitas." Tampil ulang: tombol "Tampilkan password" (reautentikasi) yang auto-sembunyi 30 detik.

---

# 4 Dashboard owner (U03)

R1/R2 · PRD UX-02. Urutan baca: tenant dan periode → yang perlu dikerjakan → ringkasan usaha → kesehatan jaringan → aktivitas terbaru.

| Elemen | Perilaku |
|---|---|
| Menunggu aktivasi | Membuka U10 dengan filter periode dan billing eligible |
| Backup gagal | Membuka U12 hanya hasil gagal; tidak memulai backup otomatis |
| RADIUS bermasalah | Membuka U19: router dengan rasio autentikasi gagal tinggi, klien RADIUS hilang, atau mode `degraded` |
| Data belum lengkap | Membuka U04 filter incomplete mapping |
| Kesehatan router | Membuka U13; tunnel/API berbeda dari kualitas internet pelanggan |
| Grafik trafik | Rentang dan unit jelas; gap tetap gap; tabel alternatif |

**R1:** kartu tagihan/kas/piutang **tidak ditampilkan** (bukan nol). Skeleton loading tanpa nol palsu. Tenant kosong → aksi utama "Hubungkan router". Monitoring gagal tetapi billing tersedia → banner lokal pada kartu jaringan. Agregat tertunda → tampilkan waktu pembaruan + tautan daftar transaksi. Admin pembayaran tidak melihat log mentah/CPU sebagai informasi pertama. Kartu navigable keyboard dan berlabel periode + satuan.

---

# 5 Daftar pelanggan dan detail layanan (U04)

R1/R2 · UX-03–04. Satu baris = satu layanan; pelanggan dengan dua lokasi muncul dua kali (service_code berbeda); header menyebut jumlah layanan dan pelanggan unik.

Empat status terpisah per baris: **Bayar** (belum/sebagian/lunas/tidak ditagih), **Isolir** (normal/terisolir/menunggu verifikasi/hold), **Koneksi** (online/offline/tidak diketahui), **Job** (tidak ada/antre/berjalan/perlu ditinjau). Kolom R2 (bayar/isolir/invoice) tersembunyi pada R1. Checkbox hanya memilih. Query dipertahankan saat kembali dari detail; PII pencarian tidak masuk analytics.

BulkActionBar: "2 layanan dipilih di halaman ini"; "pilih seluruh hasil" adalah aksi kedua yang menyebut jumlah dan filter. Konfirmasi memakai snapshot; item tidak eligible diberi alasan, tidak dihilangkan. Export mengikuti role, tanpa password.

Detail layanan: tab Ringkasan, Tagihan, **Akses (akun RADIUS: username, state, batas sesi, kunci MAC, sesi aktif terakhir, router yang membatasi)**, Jaringan, Perangkat, Riwayat. Aksi "Pindahkan ke router lain" hanya mengubah pembatasan router (jika ada) dan menjelaskan bahwa data pengguna tidak berubah. Ringkasan memisahkan bayar/isolir/koneksi/job. Rename router (display name) tidak menyiratkan perubahan identity RouterOS. Hold manual tampil sebagai alasan terpisah; tagihan lunas tidak menyalakan tombol aktivasi bila ada hold. Tidak ada hapus permanen dengan transaksi; terminasi menjelaskan layanan yang dihentikan, tanggal efektif, dampak invoice; arsip tidak menghapus histori. Akun hilang di router = "Perlu ditinjau" (`missing_source`).

---

# 6 Adopsi, migrasi RADIUS, dan CSV (U07, U08)

R1 · adopsi database-only. **Stepper 8 langkah**: **Sumber → Pilih akun → Gabungkan identitas → Petakan pelanggan → Petakan profile/paket → Sumber password → Validasi dan tinjau → Simpan**.

Langkah **Gabungkan identitas** mula-mula menampilkan kandidat struktural dan peringatan case-sensitive. Sesudah sumber credential tersedia, klasifikasi ulang kandidat setara atau konflik password dan minta review keputusan yang berubah. Keputusan Owner: gabung, pilih satu, atau rename sesuai bukti. Langkah **Sumber password** menawarkan panen sementara, CSV, password baru atau impor RADIUS; tiap opsi menyebut dampak. Panen memerlukan akun sementara dengan TTL maksimal 24 jam dan cleanup terverifikasi; password baru memerlukan pembaruan CPE. Tanpa credential: "Password belum diketahui", tidak diaktifkan.

Discovery berjalan di latar belakang. Langkah Tinjau menampilkan jumlah buat/gabung/tidak berubah/konflik dan penggunaan kuota. Memilih profile tidak mengubah profile router; paket komersial (harga, kecepatan) diisi sekali per kelompok. Peringatan FastTrack bila `fasttrack_may_bypass_queue`: "Aturan FastTrack dapat melewati antrean bandwidth. Aplikasi tidak mengubahnya; periksa pada router." Progres wizard tersimpan per tenant; setelah lama, snapshot divalidasi ulang.

Setelah **Simpan**: "Akun tersimpan di basis pengguna perusahaan. Router belum diubah dan belum memakai RADIUS." CTA utama "Lanjut ke cutover RADIUS" (U19) dan sekunder "Lengkapi data pelanggan". Billing dan isolir otomatis belum aktif.

**CSV (U08):** Unduh template, versi, contoh dua baris, batas berkas dari server (default 10 MiB / 10.000 baris), aturan kolom kosong. Mode **Buat / Hubungkan / Perbarui / Pemetaan perangkat / Password migrasi** dipilih sebelum mapping. Error per baris: baris, field, alasan, tindakan; laporan unduh tanpa secret. File sama dapat diproses ulang. Kuota kurang: jumlah akun tetap tampil; pilih subset atau buka paket. Partial: jumlah tersimpan + baris tertunda; retry tidak menduplikasi.

---

# 7 Koneksi router dan wizard konfigurasi (U05, U06, U17)

| Langkah | Isi dan aksi |
|---|---|
| Identitas | Nama tampilan, kode router, lokasi opsional, **mode: Hanya baca (default) / Kelola**; simpan draft |
| Prasyarat | Versi bila diketahui (RouterOS v7), internet tersedia, akses Terminal; tidak meminta port Ethernet khusus |
| Skrip | Preview perubahan, tujuan server, kedaluwarsa (15 menit), Salin skrip; tidak masuk analytics |
| Menunggu | Handshake VPN → API → autentikasi/izin → kompatibilitas; tiap tahap punya hasil sendiri |
| Siap | "Pindai akun existing" utama; monitoring sekunder |

Skrip hanya untuk role berwenang, tidak di link publik. Copy: "Skrip disalin. Jalankan pada router tujuan setelah meninjau perubahan." Jangan menulis "Router terhubung" sebelum handshake **dan** API terverifikasi. Kedaluwarsa → "Buat ulang" + penjelasan token lama dicabut. Peningkatan mode ke Kelola membuat skrip baru.

U06 header: nama, model/versi, VPN, API, observed_at, capability. Tab: Ringkasan; Akun ditemukan; Profile; Interface; Backup; Pekerjaan; Audit. Pesan berbeda untuk: API tidak aktif, izin kurang, TLS/sidik jari tidak cocok, tunnel terputus. Tombol belum didukung menjelaskan batas versi/topologi. Panel **RADIUS** menampilkan `enforcement_mode` (Lokal / Bayangan / Otoritatif / Terganggu), rasio autentikasi, sesi masuk, accounting terakhir, dan tombol "Buka cutover" (U19). Aksi "Lepas router" dan "Ganti router" (database-only untuk akun; menampilkan slot kuota dan batas tumpang tindih 30 hari; router baru hanya membutuhkan enrollment dan cutover).

**U17 (R4):** dua pintu terpisah: **Jaringan pelanggan** dan **Uplink**. Static WAN: interface, IP/prefix, gateway; DHCP menampilkan sumber lease. Mode: Single, Cadangan, PCC dengan failover, Weighted PCC (PCC dinonaktifkan dengan alasan bila ada Hotspot server: "PCC tidak didukung pada router dengan Hotspot"). Preview menampilkan objek dibuat/diubah, ownership, layanan terdampak, backup, kompatibilitas, jalur pemulihan. "Terapkan" nonaktif bila preflight gagal; perubahan berisiko memilih jendela pemeliharaan + alasan. Koneksi hilang setelah apply → U16: "Hasil belum dapat dipastikan. Pemeriksaan ulang diperlukan." Tidak ada tombol "Ulangi semua".

---
# 8 Pembayaran dan aktivasi massal (U09, U10)

R2 · aktivasi selalu tindakan manual terpisah. U09 memiliki tiga tab: **Invoice**, **Pengajuan pembayaran**, **Pembayaran terverifikasi**. Bukti transfer dapat diperbesar oleh role berwenang; nominal invoice, transfer, dan alokasi tampil terpisah. Tombol "Verifikasi dana" menyebut rekening, tanggal, jumlah, referensi; gambar bukti tidak dianggap hasil pencocokan bank. Payment partial menampilkan sisa; overpayment = "Saldo kredit belum dialokasikan" (bukan laba). Refund/pembatalan lewat alur koreksi + alasan. Periode filter selalu terlihat.

Setelah verifikasi: "Pembayaran tercatat. 3 layanan menunggu aktivasi." CTA "Buka daftar aktivasi" (tidak mengirim job).

Konfirmasi massal: jumlah layak/tidak layak dan snapshot. Layanan pada router yang belum `Otoritatif` diberi label "Isolir/aktivasi belum dijamin pada router ini". Hasil per item: **Berhasil diverifikasi / Menunggu koneksi / Perlu tinjau / Gagal**. Pembayaran tetap lunas bila router atau RADIUS gagal; pembayaran tidak mengaktifkan akun; sesudah aksi aktivasi manual, kelayakan DB dan bukti NAS ditampilkan terpisah. Menutup halaman tidak membatalkan job; tautan U16. Aktivasi tidak memperpanjang langganan; menambah masa tanpa bayar memakai tindakan berbeda (izin + alasan). Pengaktifan **kebijakan isolir** (di Konfigurasi/Tagihan): halaman simulasi "Siapa yang akan diisolir" (ID simulasi, berlaku 24 jam), review paket/due date/saldo pembuka, lalu tombol "Aktifkan kebijakan isolir".

---

# 9 Landing subscription dan Super Admin (U01, U14, U18)

U01: manfaat adopsi existing, manajemen pelanggan, backup, fitur yang telah tersedia. CTA primer "Mulai gratis", sekunder "Masuk". Paket menampilkan dua batas terpisah (router dan layanan) dan toggle bulanan/tahunan; tahunan: "12 bulan dibayar setara 10 bulan" tanpa harga bulanan efektif sebagai total tagihan.

Nilai paket (harga bulanan/tahunan, batas router/layanan, plafon fair use Platinum) mengikuti **PRODUCT.md §3** — sumber kebenaran; nilai tidak diulang di sini. **Rekening bank tidak ditampilkan pada landing.** Merek, logo, dan kontak dari konfigurasi `BRAND_*`; landing tidak dipublikasikan bila `BRAND_*` belum terisi.

**U18 Paket aplikasi:** paket aktif, periode, pemakaian router/layanan, invoice tertunda, riwayat pembayaran. Status langganan: `active`, `grace` ("Masa tenggang 7 hari. Perpanjang untuk menghindari pembatasan."), `restricted` ("Penambahan router/layanan baru dibatasi. Layanan pelanggan Anda tetap berjalan."), `ended` (read-only + bayar + export). Tidak ada ancaman memutus internet pelanggan. Kuota penuh menahan penambahan. Downgrade menjelaskan bahwa berlaku saat perpanjangan dan ditolak bila pemakaian melebihi batas ("Kurangi 12 layanan atau pilih paket lebih besar"). Upgrade menjelaskan: periode baru mulai hari persetujuan, sisa hari ditambahkan sebagai hari bonus. Ringkasan order tanpa asumsi tersembunyi. Instruksi pembayaran (rekening) tampil pada invoice terautentikasi sebagai snapshot. Bukti: JPEG/PNG/PDF maks. 5 MiB; status pemindaian: "Sedang diperiksa" → bukti dapat dilihat setelah lolos.

**U14 Super Admin** (header navy): antrean Menunggu verifikasi, Perlu perbaikan, Disetujui, Ditolak. Kolom: perusahaan, invoice, paket/periode, nominal, waktu submit, umur antrean, petugas. Split view: bukti, data transfer, invoice, keputusan; peringatan bukti duplikat. Approve mensyaratkan konfirmasi "Dana telah diterima di rekening"; Reject/Perbaiki mensyaratkan alasan. Dua petugas pada record sama → `revision_conflict`. Status perusahaan hanya usage, health VPN/API, outcome job/backup, paket; tidak ada drill-down PII/ledger/rahasia. Akses dukungan: permintaan scope + alasan + durasi + persetujuan Owner; banner sesi dukungan selalu tampak dengan "Akhiri akses".

**Pengaturan rekening/konfirmasi** (terpisah dari approval): daftar tujuan dengan kolom nama bank, `display_value`, status aktif, "Kepemilikan terverifikasi", "Dipublikasikan" (default tidak). Edit butuh reautentikasi + audit. Kontak konfirmasi pembayaran 082319199930 tampil sebagai tombol "Konfirmasi via WhatsApp" pada invoice dan halaman pembayaran terautentikasi. Invoice terbuka mempertahankan snapshot instruksi; perubahan rekening menanyakan perlakuan invoice terbuka.

---

# 10 Monitoring, backup, dan pekerjaan (U13, U12, U16)

**U13** mengelompokkan: Sehat, Terganggu, Tidak terpantau, Data usang, plus "Manajemen tidak terjangkau" (VPN/API). Setiap status memuat waktu pengamatan dan sumber. VPN aktif + API gagal = kondisi manajemen; tidak menyebut internet pelanggan mati. Status RADIUS per router (rasio autentikasi sukses, sesi masuk, accounting terakhir) ditampilkan terpisah; sesi hilang akibat RADIUS terputus dibedakan dari pelanggan offline. Grafik: unit, rentang, gap, tabel angka. Detail insiden: bukti, resource, perkiraan dampak (bila topologi tersedia; selain itu "Belum diketahui"), timeline, assignment. Acknowledge ≠ Selesai; resolve butuh bukti pulih atau alasan manual. Notifikasi berulang dikelompokkan per insiden. Kolektor gagal → banner "Data pemantauan tidak tersedia" (bukan router mati).

| U12 komponen | Perilaku |
|---|---|
| Jadwal | Router, timezone, frekuensi, waktu, jenis artifact, notifikasi |
| Histori | Generasi, waktu, kategori, ukuran, hasil transfer, status enkripsi |
| Retensi | "100 generasi rutin terakhir per router"; manual dan pre-change (masing-masing 10) ditampilkan terpisah |
| Unduh | Pilih artifact; cek izin; reautentikasi/kunci pemulihan; tautan berlaku 5 menit |
| Kunci pemulihan | "Tampilkan kunci" (reautentikasi + MFA; auto-sembunyi 30 detik) |
| Kegagalan | Alasan aman, retry bila diperbolehkan, job_id; backup lama tetap terlihat |
| Restore | Menu berisiko terpisah; hanya bila versi/topologi didukung (gerbang) |

Staging dan cleanup tidak dihitung backup siap unduh. Pesan: "Backup terbaru tersimpan. Pembersihan berkas lama belum selesai." Disk hampir penuh: "Penyimpanan backup hampir penuh. Backup baru dijeda pada 90%; backup yang ada tidak dihapus." Restore menampilkan perangkat/versi, isi, potensi reboot, prosedur pemulihan.

**U16 Pusat pekerjaan:** header jenis aksi, actor, waktu, router, status. Progress menampilkan tahap dan item selesai, tanpa ETA bila tak terukur. Error aman + `request_id`. Retry hanya bila `retryable`; cancel menjelaskan tahap yang masih bisa dibatalkan. Setelah browser online kembali, ambil state authoritative; toast lama tidak mengubah state. `uncertain` dan `recovery_required` tetap terlihat setelah refresh. Meninggalkan halaman tidak menghentikan worker.

---

# 11 Keuangan, ACS, dan operasional lapangan (U11, U15)

**U11** halaman awal: tagihan diterbitkan, kas masuk terverifikasi, outstanding, aging periode terpilih; "Lihat transaksi sumber" pada tiap angka. Laba akuntansi hanya dari ledger posted; bila modul belum siap tidak diganti kas masuk dikurangi kas keluar berlabel Laba.

| Area | Pola layar |
|---|---|
| Setup pembukuan | Kerangka (SAK EMKM default)/kebijakan, COA, opening balance, preview, approval cutover |
| Jurnal | Draft/posted; debit/kredit, dokumen sumber, effective date; pembalik diturunkan |
| Rekonsiliasi | Statement kiri, kandidat payment/journal kanan; selisih jelas |
| Aset | Nilai perolehan, siap pakai, umur, residu, penyusutan, histori |
| Laporan | Periode, basis, status penutupan, komparatif, export, drill-down |
| Periode | Tutup/reopen dengan ringkasan exception, permission, alasan, reautentikasi |
| Kolektor | Saldo per kolektor, umur, setoran, selisih kas |
| Pajak (bila aktif) | Rekap DPP dan pajak per periode |

Jurnal posted tanpa Edit/Hapus; hanya "Buat pembalik" atau "Penyesuaian". Laporan dari saldo awal belum disetujui berlabel "Belum final". Tidak ada tarif pajak universal. Super Admin tidak punya menu laba tenant.

**U15 (R3):** model/firmware, serial, last inform, layanan terhubung, capability. Perangkat baru = "Belum dipasangkan" (tidak otomatis ditautkan karena serial/MAC cocok). Tab Wi-Fi hanya parameter writable teruji. Password baru tampil sesaat sesuai izin; tidak di tabel/audit plaintext. Task antre: "Menunggu perangkat terhubung". Reboot/firmware butuh konfirmasi dampak; Wi-Fi menjelaskan risiko pengguna terputus. Nilai lama tetap "observed" sampai readback. Optical tak tersedia = "Tidak didukung" (bukan 0 dBm). Model di luar matriks = "Belum didukung". Inventaris, peta objek manual, tiket (customer/service/incident), work order (teknisi, jadwal, checklist, material, foto); koordinat/foto/kontak dibatasi role; alokasi ODP terpakai menolak simpan. Portal pelanggan (R3): login terpisah; menu Layanan saya, Tagihan, Bukti bayar, Bantuan; upload bukti tidak membuka isolir.

---

# 12 Status, validasi, dan microcopy

| Keadaan (kode) | Copy | Aksi berikutnya |
|---|---|---|
| `queued` | Permintaan diterima dan menunggu giliran | Lihat pekerjaan |
| `claimed/preflight/executing` | Sedang diproses | Lihat pekerjaan |
| `verifying` | Memeriksa hasil sesuai jenis tindakan | Lihat pekerjaan |
| `waiting_dependency` | Menunggu dependency yang disebutkan pada pekerjaan; pembayaran yang sudah tercatat tetap tersimpan | Lihat dependency pekerjaan |
| `retry_wait` | Akan dicoba lagi otomatis | Lihat pekerjaan |
| `uncertain` | Hasil perubahan belum dapat dipastikan | Periksa hasil; tidak retry buta |
| `recovery_required` | Perlu pemulihan manual sebelum melanjutkan | Buka panduan pemulihan |
| `succeeded` | Pekerjaan selesai; hasil telah diverifikasi sesuai jenis tindakan | Lihat rincian |
| `failed` | Gagal. Kode: {request_id} | Lihat alasan; coba lagi bila diperbolehkan |
| `cancelled` | Dibatalkan ({alasan}, mis. kebijakan berubah) | Lihat rincian |
| ringkasan `partial` | 8 berhasil, 2 perlu ditangani | Tinjau 2 layanan |
| label `stale` | Data terakhir diperbarui 12 menit lalu | Segarkan sesuai budget |
| `paid-awaiting-activation` | Sudah bayar, menunggu aktivasi | Buka aktivasi |
| `hold_unknown` | Dinonaktifkan di luar aplikasi. Tinjau alasannya | Tinjau |
| `missing_source` | Akun tidak ditemukan di router. Perlu ditinjau | Tinjau |
| `needs_review` | Konfigurasi berubah di router. Perlu ditinjau | Tinjau |
| `enforcement_mode=local` | Router ini belum memakai RADIUS perusahaan | Buka cutover |
| `enforcement_mode=radius_shadow` | RADIUS aktif, akun lokal masih ada. Isolir belum dijamin | Lanjutkan ke mode otoritatif |
| `enforcement_mode=radius_authoritative` | Router memakai basis pengguna perusahaan | Lihat status |
| `enforcement_mode=degraded` | Klien RADIUS pada router tidak lengkap. Tinjau | Buka pemeriksaan |
| `password_unknown` | Password belum diketahui. Akun belum dapat diaktifkan | Pilih sumber password |
| `identity_conflict` | Username sama dengan password berbeda pada router lain | Selesaikan konflik |
| `local_account_shadow` | Akun baru ditemukan di router di luar aplikasi | Adopsi atau nonaktifkan |
| `binding_invalid` | Pool atau profil untuk paket ini tidak ditemukan di router | Perbaiki pemetaan |
| `suspended` (akses) | Akun ditangguhkan. Login baru ditolak | Lihat alasan |
| `verified_suspended` | Penangguhan terverifikasi: sesi terputus dan login ditolak | Lihat bukti |
| `verified_active` | Akses dipulihkan dan autentikasi diizinkan; perangkat mungkin belum tersambung | Lihat bukti |
| `conflict` | Data bentrok dengan kondisi terkini | Muat ulang dan tinjau |
| `collected_not_settled` | Diterima kolektor, belum disetor | Buka setoran |
| `quota_exceeded` | Batas layanan paket tercapai | Kurangi pilihan atau lihat paket |
| `revision_conflict` | Data berubah sejak Anda meninjaunya | Muat perubahan dan tinjau ulang |
| `idempotency_conflict` | Permintaan ini sudah pernah dikirim dengan isi berbeda | Muat ulang halaman |
| `unsupported_capability` ("unsupported") | Fitur belum didukung pada konfigurasi ini | Lihat kompatibilitas |
| `forbidden` | Anda tidak memiliki izin untuk tindakan ini | Hubungi Owner |
| `unauthorized` | Sesi berakhir. Masuk kembali | Masuk |
| `rate_limited` | Terlalu banyak percobaan. Coba lagi dalam {n} detik | Tunggu |
| `router_unreachable` | Router tidak terjangkau saat ini | Lihat kondisi router |
| `verification_failed` | Perubahan terkirim tetapi belum terverifikasi | Periksa hasil |
| `dependency_unavailable` | Layanan sementara tidak tersedia | Coba beberapa saat lagi |
| `validation_error` | {mis. Tanggal jatuh tempo belum diisi} | Fokus field bermasalah |
| `not_found` | Data tidak ditemukan | Kembali ke daftar |

Loading, empty, offline browser, dan server error berbeda. Empty search: "Hapus filter"; empty tenant: onboarding; 403 tidak tampil sebagai tabel kosong. Sesi habis meminta masuk ulang, menyimpan draft non-secret bila aman, tidak mengirim ulang mutasi otomatis. Validasi saat blur (format sederhana) dan saat submit (aturan bisnis); fokus pindah ke ringkasan error yang menautkan field; input valid tetap tersimpan. Nama/telepon bukan keunikan universal. IP memerlukan prefix; nominal/tanggal tidak ditebak dari comment.

Toast hanya untuk feedback singkat; hasil job, receipt, error penting tetap pada halaman/timeline. Screen reader memakai live region yang tidak mengumumkan tiap sample monitoring. Dialog mengunci fokus, bernama jelas, mengembalikan fokus ke pemicu. Konfirmasi destruktif spesifik: "Putuskan sesi layanan SVC-018?". CTA berverba: Verifikasi dana, Simpan pemetaan, Jalankan aktivasi — bukan "OK". Tidak menampilkan "100% aman", "tanpa downtime", atau "semua ONT didukung".

---

# 13 Responsive mobile dan aksesibilitas

Desktop ≥1200, tablet 768–1199, mobile <768. Mobile: sidebar menjadi drawer; tabel menjadi MobileServiceCard dengan empat status terpisah.

Pencarian dan filter dekat judul. Detail luas = halaman penuh. Pilih seluruh filter tetap butuh konfirmasi jumlah. Finansial mengikuti role. Form IP/WAN lanjutan boleh merekomendasikan desktop; alasan "tidak didukung" berbeda dari alasan layout.

WCAG 2.2 AA: urutan keyboard mengikuti visual; focus ring terlihat; label dan error terasosiasi; status memakai teks/ikon; zoom/reflow diuji; chart punya alternatif tabel; header tabel semantik; target sentuh 44 px; kontras diukur pada implementasi. Koneksi lambat: tampilkan cache terakhir bertimestamp lalu refresh tanpa menghapus filter. Browser offline memblokir mutasi baru ("Aksi belum dikirim"); tidak ada antrean pembayaran/isolir lokal diam-diam; saat online, ambil state server sebelum menawarkan retry.

---

# 14 Pengujian desain dan handoff

| Skenario | Peserta dan target |
|---|---|
| Hubungkan dan adopsi | Owner pemula menyelesaikan alur di lab tanpa mengubah akun existing |
| Cari yang sudah bayar | Admin menemukan periode benar, membedakan lunas dari aktif |
| Aktivasi sebagian gagal | Admin tahu item mana menunggu router dan tidak mengulang yang sukses |
| Gangguan monitoring | Teknisi membedakan VPN/API gagal dari internet pelanggan putus |
| Impor CSV konflik | Owner memperbaiki baris bermasalah tanpa input ulang seluruhnya |
| Keuangan | Owner membedakan kas masuk, piutang, laba |

Pilot desain: minimal lima peserta lintas owner/teknisi/admin termasuk dua non-ahli; ukur completion, waktu, bantuan, salah tindakan, pemahaman status. Target awal ≥80% tugas inti tanpa bantuan kritis dan nol salah-tenant/salah-aktivasi (target evaluasi kualitatif, bukan hasil). Terpisah dari target PRD 8 dari 10 operator mengadopsi 50 akun.

Handoff per layar: route, role, PRD ID, API/query, schema field, state empty/loading/error/partial/forbidden, desktop/mobile, event analytics, acceptance test. Komponen sebagai variant. Dev tidak mengubah enum/arti status tanpa sinkron dengan ARCHITECTURE.md. Analytics hanya: `import_started`, `import_committed`, `cutover_started`, `cutover_completed`, `activation_reviewed`, `activation_result_viewed`, `onboarding_step_completed`, `language_changed`; properti tenant surrogate, role, step, count, duration, `safe_error_code`; tidak merekam password, nama pelanggan, isi pencarian, bukti bayar, atau skrip bootstrap.

Definition of Ready: flow disepakati, API/error tersedia, izin jelas, state mockup lengkap. Definition of Done: lint/aksesibilitas dasar, keyboard/mobile, contract test, E2E happy/error path, review desain. Fitur tidak dipasarkan karena mockup tersedia. Perubahan harga/kuota/expiry mengikuti PRD.

Referensi aksesibilitas (kode W1–W3): W1 WCAG 2.2 https://www.w3.org/TR/WCAG22/ · W2 Target Size https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html · W3 Focus Not Obscured https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html


---

# 15 Bahasa dan lokalisasi

Aturan normatif: `I18N.md`.

- **Pemilih bahasa** pada landing, halaman daftar/login, dan profil pengguna; nama bahasa ditulis dalam bahasanya sendiri ("Bahasa Indonesia", "English"). Bahasa default `id`. Mengganti bahasa tidak menghapus isian formulir. Pengaturan perusahaan (U18): bahasa default tenant, bahasa dokumen default, zona waktu (WIB/WITA/WIT). Pada detail pelanggan: bahasa komunikasi pelanggan.
- Semua teks berasal dari katalog pesan; tidak ada teks tertanam pada komponen. Istilah teknis (PPPoE, Hotspot, RADIUS, VPN) dipertahankan; penjelasan singkat tersedia pada panel bantuan "Apa ini?".
- Kode status, enum, dan kode error tidak diterjemahkan; label tampilannya dilokalkan. Pesan error server tampil dalam bahasa aktif dengan `request_id`.
- Format: `Rp1.500.000` (id) / `IDR 1,500,000` (en); tanggal "11 Oktober 2026"; zona waktu ditampilkan bersama waktu pada data operasional.
- Invoice, kwitansi, dan laporan memakai bahasa terbit yang tersimpan; pratinjau cetak menampilkan bahasa dokumen dan memungkinkan memilih bahasa lain sebelum terbit (setelah terbit tidak berubah).
- Templat notifikasi (U18) disunting per bahasa dengan variabel bernama dan pratinjau.
- Panjang teks bahasa lain tidak boleh memotong tombol 44 px; tata letak diuji dengan pseudo-locale.

---

# 16 Basis akun akses RADIUS dan cutover (U19)

R1 · Akses baca akun/router memakai permission resource; hanya tombol cutover/rollback memerlukan radius.cutover+MFA+reauth. Tiga area: **Akun**, **Router**, **Cutover**.

**Akun**: tabel akun akses (username, jenis, state, paket, router pembatas, sesi aktif terakhir) dengan pencarian dan filter; aksi per akun: tampilkan password (reautentikasi, auto-sembunyi 30 detik), ubah batas sesi/kunci MAC, tangguhkan/aktifkan, rotasi password (menjelaskan dampak CPE). Password tidak pernah tampil di tabel.

**Router**: kartu per router: mode (`Lokal`, `Bayangan`, `Otoritatif`, `Terganggu`), jumlah akun yang dimigrasikan, rasio autentikasi sukses 24 jam, sesi masuk, accounting terakhir, dua alamat RADIUS (primer/sekunder), status klien.

**Cutover** (stepper per router):

Aturan tampilan cutover mengikuti RADIUS.md §10.2: tampilkan scope shared setting, ownership consent, dampak dan evidence setiap langkah. Jangan menjanjikan nol downtime universal. Tombol lanjut aktif hanya bila exit criterion terpenuhi. Rollback menjelaskan pemulihan snapshot/revision yang masih sah serta hold yang dipertahankan; coverage recovery tidak lengkap → recovery_required. B5 menampilkan metode teruji, batch≤100, reautentikasi dan izin deletion eksplisit bila dipilih. Secondary/edge tidak dianggap HA sebelum jalur, secret, revision dan gate dibuktikan. Hasil ambigu → uncertain/recovery_required, tanpa "ulangi semua".

---

# 17 Voucher, agen, dan kolektor (U20)

**Voucher (R3)**: buat batch (paket: durasi, batas data, kecepatan, masa berlaku; jumlah; awalan kode), tampil sisa kuota ("Batch ini memakai 200 dari 250 sisa kuota") sebelum diterbitkan, cetak/ekspor, cabut, perpanjang. Status: Diterbitkan, Aktif, Terpakai, Kedaluwarsa, Dicabut.

**Agen (R3)**: daftar agen, stok, penjualan, komisi, setoran; portal agen menampilkan hanya data milik agen.

**Kolektor (R2)**: daftar tugas penagihan per area (tunggakan), input penerimaan tunai (kwitansi bernomor), saldo "diterima, belum disetor", setoran dengan pencocokan; selisih memerlukan alasan dan persetujuan. Kolektor melihat hanya pelanggan yang ditugaskan dan saldonya sendiri.

**Prospek dan instalasi (R3, bagian U15)**: papan status `Prospek → Survei → Terjadwal → Terpasang → Aktif`; work order dengan checklist, material, foto; aktivasi layanan setelah instalasi diverifikasi.
