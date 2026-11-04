# Panduan Akuntansi dan Keuangan ISP RT/RW Net — Platform SaaS Manajemen RT/RW Net

[REVISI MACRO 2.1-macro.1] Retensi 10 tahun adalah minimum dokumen finansial menurut MAC-03; dasar hukum retensi dibedakan dari standar SAK EMKM. Posted ledger tetap immutable; purge arsip yang sah memakai principal/proses terpisah dan review profesional sebelum produksi. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


**Versi 1.1** · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.0 (11 Oktober 2026) → 1.1 (28 Oktober 2026; ditetapkan sebagai sumber kebenaran tunggal aturan posting, aturan refund dipindahkan dari TD — putusan DOC pada `decisions_log.md` Bagian E)
Dokumen normatif pendamping PRD v1.4 bagian 12, 15, 16 dan TD v1.3 bagian 10. ID kebutuhan ACC-01 s/d ACC-12. Dokumen ini adalah **sumber kebenaran tunggal aturan posting** (COA, akun per kejadian, jadwal pengakuan); dokumen lain merujuk ke sini dan tidak mengulang tabel posting. Seluruh aturan posting adalah kebijakan awal yang dapat dikonfigurasi per tenant dan wajib ditinjau tenaga akuntansi sebelum pembukuan produksi (G2). Dokumen ini bukan nasihat pajak atau hukum; tarif, objek pajak, dan kewajiban perizinan diverifikasi tenant bersama konsultan.

## 1 Dasar

- Pembukuan **double-entry**: setiap jurnal memiliki jumlah debit sama dengan kredit lintas seluruh barisnya; basis **akrual**; mata uang IDR (numeric(20,2)); satu buku per tenant ditambah buku platform terpisah.
- Kerangka pelaporan default **SAK EMKM** (dapat memilih SAK Entitas Privat); `FrameworkVersion` dan tanggal efektif tersimpan. Aplikasi membantu penerapan; tidak menyatakan kepatuhan otomatis. Pemisahan kekayaan usaha dan pribadi dijaga lewat akun ekuitas (modal, prive).
- Periode fiskal bulanan; tahun fiskal default tahun kalender; zona waktu tenant (WIB/WITA/WIT) menentukan batas tanggal.
- Dokumen sumber wajib untuk setiap jurnal (`source_document_id`, `source_event` unik); jurnal posted tidak diubah (reversal/adjustment).

## 2 Chart of accounts default (ACC-01)

| Kode | Akun | Normal |
|---|---|---|
| 1-1100 | Kas | D |
| 1-1150 | Kas di Kolektor/Agen (clearing) | D |
| 1-1200 | Bank | D |
| 1-1300 | E-wallet Usaha | D |
| 1-1400 | Piutang Usaha (control) | D |
| 1-1450 | Cadangan Kerugian Piutang (kontra) | K |
| 1-1500 | Persediaan Perangkat dan Material | D |
| 1-1600 | Beban Dibayar di Muka | D |
| 1-1700 | Uang Muka/Panjar Teknisi | D |
| 1-2100 | Peralatan Jaringan | D |
| 1-2200 | Kendaraan dan Peralatan Lapangan | D |
| 1-2900 | Akumulasi Penyusutan (kontra) | K |
| 2-1100 | Utang Usaha | K |
| 2-1200 | Beban yang Masih Harus Dibayar | K |
| 2-1300 | Pendapatan Diterima di Muka | K |
| 2-1400 | Kredit dan Deposit Pelanggan | K |
| 2-1500 | Utang Pajak | K |
| 2-1600 | Utang Komisi Agen/Reseller | K |
| 2-2100 | Pinjaman | K |
| 3-1100 | Modal | K |
| 3-2100 | Saldo Laba | K |
| 3-3100 | Prive/Distribusi | D |
| 4-1100 | Pendapatan Internet Berlangganan | K |
| 4-1150 | Pendapatan Voucher Hotspot | K |
| 4-1200 | Pendapatan Instalasi | K |
| 4-1300 | Penjualan Perangkat | K |
| 4-1400 | Pendapatan Jasa Lain | K |
| 4-9000 | Diskon dan Retur Pendapatan (kontra) | D |
| 5-1000 | Harga Pokok Perangkat Terjual | D |
| 5-1100 | Beban Bandwidth/Upstream | D |
| 5-1200 | Listrik | D |
| 5-1250 | Sewa Lokasi/Tiang/Ruang | D |
| 5-1300 | Gaji dan Upah | D |
| 5-1400 | Beban Teknisi dan Pemasangan | D |
| 5-1500 | Transportasi | D |
| 5-1550 | Komisi Agen/Reseller | D |
| 5-1600 | Biaya Bank dan Payment Fee | D |
| 5-1700 | Software dan Langganan | D |
| 5-1800 | Penyusutan | D |
| 5-1900 | Kerugian Piutang | D |
| 5-1950 | Selisih Kas | D |

COA dapat diubah sebelum cutover; setelah ada jurnal posted, akun hanya dinonaktifkan, tidak dihapus. Pemetaan fungsi ke akun (mis. akun bank per rekening) disimpan sebagai `account_role`.

## 3 Siklus pendapatan (ACC-02)

| Peristiwa | Jurnal |
|---|---|
| Invoice **prabayar** terbit, belum dibayar | Tidak ada (memorandum); status invoice `open` |
| Pembayaran prabayar terverifikasi | D Bank/Kas/Kas Kolektor; K 2-1300 |
| Pengakuan prabayar (harian, diposting per bulan kalender) | D 2-1300; K 4-1100 |
| Invoice **pascabayar** terbit pada akhir periode | D 1-1400; K 4-1100 |
| Pembayaran piutang | D Bank/Kas; K 1-1400 |
| Pembayaran melebihi tagihan | Bagian teralokasi mengikuti jurnal prepaid/postpaid; hanya selisih masuk K 2-1400, debit Bank sekali sebesar penerimaan. Tidak memposting seluruh payment lagi sebagai credit (AUD-30). |
| Kredit pelanggan dipakai | D 2-1400; K 1-1400 atau 2-1300 |
| Diskon susulan | D 4-9000; K 1-1400/2-1300 (dokumen koreksi) |
| Biaya instalasi ditagih | D 1-1400; K 4-1200 (diakui saat instalasi selesai) |
| Deposit perangkat/jaminan diterima | D Bank; K 2-1400 (dikembalikan: D 2-1400, K Bank) |

**Pengakuan prabayar**: untuk kontrak `[start, end)` senilai V, H = jumlah hari; untuk tiap bulan kalender dengan h_m hari layanan diakui `round_half_up(V × h_m / H, 2)`; sisa pembulatan masuk ke bulan terakhir; total tepat V setelah residual bulan terakhir. Contoh: Rp300.000 untuk 1 Januari–1 April (90 hari): Januari 31/90 = 103.333,33; Februari 28/90 = 93.333,33; Maret 31/90 = 103.333,33 ditambah sisa pembulatan 0,01 sehingga 103.333,34; total 300.000,00.

**Periode pertama** (aktivasi di tengah periode): kebijakan per paket `first_period_policy`: [REVISI AUD-29] `full` mengikuti cycle: fixed_monthly mengenakan harga penuh untuk sisa periode kalender pertama, anniversary memberi satu term penuh dari aktivasi, `prorata_daily` (tagihan awal = harga × hari/total hari periode kalender, dibulatkan ke atas ke Rp100 terdekat; dikonfigurasi), atau `free_until_next_period`. Kebijakan tersimpan pada invoice (snapshot) dan terlihat pelanggan.

**Pajak (ACC-06)**: konfigurasi `TaxRule` (jenis, tarif, versi, tanggal efektif, inklusif/eksklusif, pembulatan, akun utang pajak). Default tidak ada pajak. Bila aktif, invoice memuat baris pajak; jurnal mengikuti timing AUD-32: prepaid belum dibayar tetap memorandum; pembayaran prepaid memisahkan DPP ke 2-1300 dan pajak ke 2-1500 sesuai TaxRule. Postpaid recognized memakai piutang/pendapatan dan pajak sesuai TaxRule; jangan mengakui revenue prepaid hanya karena dana diterima. Penentuan status PKP, PPN, PPh final, BHP/USO telekomunikasi, dan perizinan penyelenggaraan jasa akses internet adalah tanggung jawab tenant dengan konsultan; aplikasi hanya menyediakan mekanisme dan laporan pendukung. Tanggal efektif tarif memastikan invoice lama tidak berubah.

## 4 Penerimaan pembayaran (ACC-03)

1. **Transfer/e-wallet**: bukti diunggah → verifikasi dana (mutasi bank/aplikasi) → `Payment` → alokasi ke invoice → jurnal. Bukti saja bukan pembayaran. Biaya payment fee dijurnal terpisah (D 5-1600; K bank) saat mutasi bersih tercatat.
2. **Tunai oleh kolektor/agen**: pembayaran dicatat dengan akun clearing 1-1150 (D 1-1150; K 1-1400/2-1300) pada nama kolektor; **setoran** kolektor ke kas/bank (D Bank; K 1-1150) memerlukan rekonsiliasi; selisih ke 5-1950 dengan persetujuan. Saldo kolektor tampil per orang dan umur.
3. **Alokasi**: satu payment ke banyak invoice; tidak melebihi nilai payment; sisa → 2-1400. Pembayaran sebagian tidak melunasi invoice. Tidak ada alokasi ke periode yang berbeda tanpa jejak.
4. **Pembayaran saat router offline atau layanan terisolir**: uang dicatat; aktivasi manual terpisah (PRD §13).

## 5 Piutang, penagihan, dan penghapusan (ACC-04)

- Aging: 0–30, 31–60, 61–90, >90 hari terhadap `due_at`.
- **Cadangan kerugian piutang** (opsional per tenant): kebijakan persentase per bucket; jurnal D 5-1900; K 1-1450; pembalikan saat pelunasan.
- **Write-off**: dokumen koreksi, otorisasi dan alasan; D 1-1450 (atau 5-1900), K 1-1400. Pembayaran susulan memakai recovery rule dan pemetaan akun yang ditinjau sebelum fitur aktif; mengkredit cadangan tanpa rekonstruksi piutang bukan default (AUD-32).
- [REVISI AUD-32] **Refund** SaaS dibatasi kesalahan/ganda; refund internet mengikuti kontrak tenant. Pisahkan earned/unearned/tax dan jangan mendebit liability yang sudah habis. Dokumen koreksi + otorisasi wajib: D 2-1300 (prabayar) / 2-1400 (kredit pelanggan) / 4-9000 (retur pendapatan); K Bank/Kas.
- Pelanggan berhenti dengan tunggakan: layanan `terminated`, piutang tetap, tindak lanjut tercatat.

## 6 Voucher, agen, dan reseller (ACC-05)

- Penjualan voucher melalui agen mengikuti AUD-32: pilih reseller principal atau sales-agent; jangan menggabungkan harga net agen dengan komisi yang sama dua kali. Pembayaran di muka menjadi unredeemed liability 2-1300; pengakuan mengikuti kewajiban layanan/redemption/expiry yang sah, bukan seluruh voucher multi-day saat pemakaian pertama. Commission event unik; payable 2-1600 sampai dibayar.
- Penjualan langsung operator: D Kas; K 2-1300, lalu pengakuan sesuai layanan/redemption/expiry yang sah. Opsi `recognize_on_sale` memerlukan kebijakan terdokumentasi dan flag review akuntan sebelum produksi (AUD-32).
- Stok voucher tidak dijurnal sebagai persediaan kecuali dicetak fisik dengan biaya signifikan (kebijakan tenant).

## 7 Perangkat, persediaan, dan aset (ACC-06)

- **Klasifikasi pembelian** menurut tujuan: persediaan dijual (1-1500), material pemasangan (1-1500 lalu 5-1400 saat dipakai), aset (1-2100) bila memenuhi **ambang kapitalisasi tenant** (default Rp2.500.000 per unit, konfigurasi) dan umur manfaat > 1 tahun, atau langsung beban.
- Biaya persediaan: **rata-rata bergerak** (default) atau FIFO (opsi); penjualan perangkat: D Kas/Piutang; K 4-1300; D 5-1000; K 1-1500.
- Perangkat dipinjamkan ke pelanggan (ONT milik perusahaan) tetap aset/persediaan pinjaman; penugasan ke Service tidak menjurnal; pengembalian/penghapusan dicatat.
- **Penyusutan** garis lurus bulanan: umur default Peralatan Jaringan 4 tahun, Kendaraan 4 tahun (konfigurasi per kategori), nilai residu default 0; D 5-1800; K 1-2900. Disposal: hapus biaya perolehan dan akumulasi, selisih ke pendapatan/beban lain.

## 8 Pembelian, utang, dan beban

Faktur pemasok: D beban/persediaan/aset; K 2-1100. Pembayaran: D 2-1100; K Bank. Beban masih harus dibayar dan dibayar di muka (sewa, bandwidth) dengan jadwal amortisasi bulanan (D 5-xxxx; K 1-1600) memakai mekanisme penjadwalan yang sama dengan pengakuan prabayar.

## 9 Bank dan e-wallet: rekonsiliasi (ACC-07)

- Impor mutasi CSV format terkonfigurasi (bank/e-wallet) dengan kunci unik (hash akun+tanggal+nominal+referensi+urut) mencegah impor ganda.
- Pencocokan: nominal + tanggal ± toleransi + referensi/nama pengirim; saran otomatis ditinjau manusia; **split match** (satu mutasi untuk beberapa payment) dan **merge** (beberapa mutasi untuk satu payment).
- Saldo statement ≠ saldo buku; selisih dijelaskan (outstanding, biaya bank, error); tidak menimpa saldo buku. Transfer antarbank usaha: D bank tujuan; K bank sumber; bukan pendapatan.
- Mutasi tanpa pasangan masuk antrean *exception* dengan umur.

## 10 Tutup periode dan koreksi (ACC-08)

- Daftar periksa tutup bulan: semua pembayaran terverifikasi dialokasikan; rekonsiliasi bank selesai; jurnal pengakuan prabayar terposting; penyusutan terposting; kolektor tersetor atau dijelaskan; aging terekonsiliasi dengan control account.
- Tutup mengunci periode; posting mundur ditolak; koreksi lewat reversal/adjustment pada periode terbuka berikutnya dengan `effective_date` dan alasan; reopen oleh pemegang `period.reopen` dengan reautentikasi dan audit, tidak melintasi tutup tahun.
- **Tutup tahun**: laba/rugi ke 3-2100; saldo awal tahun berikutnya otomatis; tidak dapat dibuka kecuali prosedur reopen tahun dengan alasan dan persetujuan ganda (Owner + akuntan).

## 11 Saldo pembuka dan migrasi (ACC-09)

Batch saldo pembuka dengan tanggal cutover dan persetujuan; harus seimbang. Piutang pembuka per pelanggan; invoice historis tidak dijurnal ulang. Paid-through dan tunggakan dari CSV direview dan tidak menghasilkan jurnal sendiri. Ringkasan saldo pembuka ditampilkan kepada Owner sebelum automation penagihan aktif.

## 12 Laporan (ACC-10)

| Laporan | Basis dan kontrol |
|---|---|
| Neraca saldo, buku besar | Dari jurnal posted; drill-down ke dokumen |
| Laba rugi | Akrual; periode dan komparatif |
| Posisi keuangan | Per tanggal; tie-out |
| Arus kas | Metode langsung/tidak langsung (konfigurasi); rekonsiliasi kas |
| Aging piutang | Per pelanggan/paket/router/kolektor |
| Penerimaan harian | Menurut metode, rekening, kolektor |
| Pendapatan per paket/router/area | Dari jurnal dan dimensi analitik |
| Saldo kolektor | Umur dan setoran |
| Pendapatan diterima di muka | Rincian jadwal pengakuan |
| Aset dan penyusutan | Biaya, akumulasi, nilai buku |
| Pajak (bila aktif) | Rekap DPP dan pajak per periode |
| Catatan laporan | Kebijakan dan penjelasan |

Setiap laporan memuat periode, basis, waktu generasi, status penutupan; laporan dari saldo pembuka yang belum disetujui berlabel "Belum final". Dimensi analitik (router, area, paket, kolektor) disimpan pada baris jurnal tanpa mengubah keseimbangan.

## 13 Kontrol dan penegakan (ACC-11)

Penegakan teknis (TD §10): role runtime tanpa INSERT/UPDATE/DELETE pada tabel jurnal; prosedur `ledger.post_entry` (SECURITY DEFINER) dengan period lock `FOR SHARE`; constraint trigger deferred debit=kredit; trigger immutability. Nomor dokumen unik per tenant dan jenis; `created_at`, `effective_date`, `posted_at`, actor, source tersimpan. Super Admin tidak melihat buku tenant.

## 14 Buku platform (ACC-12)

Pendapatan langganan SaaS memakai mesin yang sama dengan cakupan `platform`: pembayaran tahunan → 2-1300 → pengakuan bulanan sesuai nilai kontrak (diskon tahunan diakui pada nilai tagih); pembayaran ganda/selisih → kredit tenant (2-1400); refund hanya kesalahan/ganda lewat dokumen koreksi. Akses hanya permission keuangan platform.

## 15 Pengujian (T12 dan tambahan)

Debit=kredit lintas baris; bypass direct-write ditolak; period lock dan race posting vs tutup; retry source_event; pengakuan prabayar (contoh bagian 3); setoran kolektor dengan selisih; split match; cadangan piutang dan write-off; penyusutan dan disposal; saldo pembuka; laporan saling tie-out (piutang control = subledger, kas/bank = rekonsiliasi). Review tenaga akuntansi atas seluruh templat sebelum produksi.
