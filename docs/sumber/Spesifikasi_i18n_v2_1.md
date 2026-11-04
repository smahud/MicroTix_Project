# Spesifikasi Multi Bahasa dan Lokalisasi — Platform SaaS Manajemen RT/RW Net

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


**Versi 1.1** · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.0 (11 Oktober 2026) → 1.1 (28 Oktober 2026; penyelarasan referensi versi dokumen — putusan DOC pada `decisions_log.md` Bagian E)
Dokumen normatif pendamping PRD v1.4 bagian 5 dan UI/UX v1.3. ID kebutuhan I18N-01 s/d I18N-10.

## 1 Prinsip

1. **Bahasa Indonesia (`id`) adalah bahasa default** untuk seluruh antarmuka, pesan, dokumen pelanggan, dan notifikasi. Bahasa Inggris (`en`) wajib tersedia sejak rilis pertama. Arsitektur menerima bahasa tambahan lewat paket terjemahan tanpa perubahan kode (kandidat berikutnya: bahasa daerah dan Melayu; tidak dijanjikan sebelum paket terjemahan disahkan).
2. Teks yang tampil kepada manusia **tidak pernah di-hardcode**; seluruhnya berasal dari katalog pesan dengan kunci stabil.
3. **Kode mesin tidak diterjemahkan**: enum status, kode error (`quota_exceeded`), ID, nama field API, atribut RADIUS, dan nilai konfigurasi tetap dalam bahasa Inggris/format baku. Hanya label tampilannya yang dilokalkan.
4. Lokalisasi menyentuh empat lapisan: antarmuka web, pesan API, dokumen keluaran (invoice, kwitansi, laporan, export), dan komunikasi (email transaksional, notifikasi pelanggan, portal pelanggan).

## 2 Penentuan bahasa (I18N-01)

| Konteks | Sumber bahasa (urutan) |
|---|---|
| Pengguna operator | Preferensi profil pengguna → bahasa default tenant → `id` |
| Pengguna sebelum login (landing, daftar) | Pilihan pengunjung (tersimpan di cookie fungsional) → `Accept-Language` yang didukung → `id` |
| Pelanggan akhir (portal, invoice, notifikasi) | Preferensi pelanggan pada customer record → bahasa default tenant → `id` |
| Respons API | `Accept-Language` berbobot q valid → bahasa pengguna → default tenant → `id`, dengan fallback parent; `Content-Language` dan `locale` konsisten, cache locale+tenant (AUD-38). |
| Dokumen yang dihasilkan | Snapshot bahasa, timezone, template version, nilai dan artifact/hash final saat issued (AUD-38); reprint tidak memakai template terbaru secara diam-diam. |
| Email akun SaaS | Bahasa pengguna penerima |

Rantai cadangan (fallback): bahasa diminta → bahasa induk (mis. `en-GB` → `en`) → `id`. Kunci yang belum diterjemahkan menampilkan teks `id`, tidak menampilkan kunci mentah, dan dicatat sebagai metrik "terjemahan hilang".

## 3 Katalog pesan (I18N-02)

- Frontend memakai **ICU MessageFormat** (FormatJS; plural, select, argumen bernama); backend memakai gettext (`.po`, plural CLDR) untuk pesan API, email, dan dokumen; katalog per bahasa per domain (`web`, `api`, `docs`, `mail`, `enum`) dengan kunci sumber yang sama dan uji paritas.
- Kunci hierarkis stabil (`service.status.paid_awaiting_activation`); kunci tidak dihapus tanpa alasan dan tidak dipakai ulang dengan makna lain.
- Pluralisasi mengikuti aturan CLDR bahasa terkait (bahasa Indonesia tidak berpluralisasi; bahasa lain dapat).
- Argumen tidak boleh dirangkai dengan penggabungan string; kalimat penuh menjadi satu pesan.
- Pesan yang mengandung istilah teknis (PPPoE, Hotspot, RADIUS, VPN) mempertahankan istilah tersebut; penjelasan tersedia pada panel bantuan.
- Teks hukum (kebijakan privasi, syarat layanan) berversi per bahasa; bahasa yang belum disahkan tidak ditampilkan sebagai pilihan.

## 4 Format regional (I18N-03)

| Aspek | Aturan |
|---|---|
| Mata uang | Hanya IDR. Tampilan `Rp1.500.000` (id) / `IDR 1,500,000` (en). Disimpan `numeric(20,2)`; JSON string; pemformatan hanya di lapisan tampilan |
| Angka dan tanggal | Pemformat berbasis CLDR (`Intl`) mengikuti bahasa; tanggal penuh `11 Oktober 2026` (id) |
| Zona waktu | Disimpan UTC; tampil pada zona tenant: WIB (Asia/Jakarta), WITA (Asia/Makassar), WIT (Asia/Jayapura) dengan label zona; pelanggan mengikuti zona tenant |
| Telepon | Disimpan sebagai teks; normalisasi E.164 (`+62…`) untuk pencocokan, nilai asli dipertahankan (nol di depan tidak dibuang); validasi nomor Indonesia (08…, +628…) |
| Alamat | Format Indonesia (jalan, RT/RW, kelurahan/desa, kecamatan, kota/kabupaten, provinsi, kode pos) sebagai field terstruktur opsional |
| Nama | Satu field nama lengkap; tidak memecah nama depan/belakang |
| Pengurutan/pencarian | Collation sesuai bahasa; pencarian tidak sensitif huruf kapital dan diakritik untuk teks bebas (tidak untuk username RADIUS) |
| Arah teks | LTR; arsitektur tidak menutup dukungan RTL di masa depan (properti logis CSS) |

## 5 Dokumen dan komunikasi pelanggan (I18N-04)

- Invoice, kwitansi, laporan, dan export CSV/PDF memuat bahasa dokumen, zona waktu, dan format angka; header kolom CSV template tetap berbahasa Inggris baku (kontrak impor) dengan kamus kolom dilokalkan pada UI.
- Templat notifikasi (pengingat tagihan, konfirmasi pembayaran, pemberitahuan isolir/aktivasi) tersedia per bahasa dengan variabel bernama; Owner tenant dapat menyesuaikan teks per bahasa (draf dengan pratinjau; versi tersimpan). Pesan tidak memuat password penuh.
- Email transaksional akun SaaS tersedia `id` dan `en`.
- Landing page, panduan, dan kompatibilitas memiliki konten per bahasa; konten yang belum tersedia pada suatu bahasa jatuh ke `id`.

## 6 Alur terjemahan (I18N-05)

1. Sumber kebenaran pesan: berkas `id` (dan `en`) pada repository; ekstraksi kunci otomatis pada CI; build gagal bila kunci dipakai di kode tetapi tidak ada pada katalog `id`.
2. Terjemahan bahasa lain melalui berkas atau sistem manajemen terjemahan; status per kunci: `draft`, `reviewed`, `approved`. Hanya `approved` yang tampil pada produksi.
3. **Pseudo-locale** (`xx-pseudo`) untuk pengujian: teks diperpanjang dan diberi aksen untuk mendeteksi hardcode dan pemotongan tata letak.
4. Pengujian kualitas: pemeriksaan placeholder konsisten, panjang teks (tidak memotong tombol 44 px), plural, dan kontras tidak bergantung pada bahasa.

## 7 Antarmuka pemilih bahasa (I18N-06)

Pemilih bahasa pada landing, login, dan profil; nama bahasa ditulis dalam bahasanya sendiri ("Bahasa Indonesia", "English"). Perubahan bahasa tidak menghapus data input di formulir. Pengaturan tenant: bahasa default tenant dan bahasa dokumen default; per pelanggan: bahasa komunikasi.

## 8 Aksesibilitas bahasa (I18N-07)

Atribut `lang` pada dokumen dan pada potongan teks bahasa lain; label dan pesan error dibacakan pembaca layar dalam bahasa aktif; live region tidak mengumumkan setiap sampel monitoring.

## 9 API dan kontrak (I18N-08)

`message` pada error dilokalkan; `code` dan `field_errors[field][i].code` (daftar `{code,message}` per field menurut AUD-13) tetap. Respons memuat `locale` yang dipakai. Daftar enum dengan label dilokalkan tersedia pada `GET /api/v1/meta/enums?locale=id`. Perubahan label tidak mengubah kontrak.

## 10 Privasi dan data (I18N-09)

Preferensi bahasa adalah data pengguna/pelanggan biasa. Teks bebas yang diketik pengguna (catatan, komentar) tidak diterjemahkan otomatis dan tidak dikirim ke layanan terjemahan eksternal.

## 11 Pengujian (I18N-10)

Cakupan: seluruh layar dirender dalam `id`, `en`, dan pseudo-locale; invoice/kwitansi dicetak dalam kedua bahasa dengan angka/tanggal benar; kunci hilang jatuh ke `id`; `Accept-Language` pada API; bahasa dokumen terbekukan setelah terbit; zona WIB/WITA/WIT pada batas tanggal invoice; normalisasi telepon dan pencarian.
