# Onboarding dan akses — MicroTix v2.1

[REVISI AUD-01–46 / MAC-01–08] Proyeksi normatif kontrak master v2.1 revisi 2.1-macro.1. Bagian AUD di bawah dihasilkan dari master; §23 MAC memperinci retensi/PDP/RADIUS/dependency/gate. Baca master §23 dan Quality_Gates_and_Release_Readiness_v2_1.md sebelum implementasi. Status runtime NOT_RUN.

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

## 19. GNS3, jaringan lab, dan resource

[REVISI AUD-39] Jangan mengunci GNS3 API v2 tanpa inventaris. Pilih family v2/v3 dari endpoint versi yang diizinkan dan dokumentasi versi aktual; controller/compute compatibility diverifikasi; base URL disimpan lengkap dengan prefix sekali, bukan menambahkan /v2 pada URL yang sudah mempunyai /v3. MCP opsional, bukan dependency. Version discovery hanya host/port yang sudah diotorisasi; tidak memindai jaringan mencari server.

Lab0: Linux gateway WireGuard+FreeRADIUS+PostgreSQL lokal sebagai baseline produksi co-located, AUT mengakses lewat route/firewall eksplisit; CHR adalah NAS; Linux PPPoE client menggunakan pppd/plugin PPPoE pada segmen L2 pelanggan, bukan DHCP client; Hotspot client memakai segmen L2 terpisah dan browser uji. Klien pelanggan tidak dijadikan peer manajemen WG. Lab1 menambah dua NAS tenantA dan satu NAS tenantB; Lab2 cutover; Lab3 fault/load; Lab4 ACS per model dan WAN per topologi. Emulator CPE hanya bukti kontrak, bukan sertifikasi model fisik.

Contoh alokasi logis, belum merupakan alamat host pemilik: management10.255.0.0/24; AUT10.255.10.0/24; tunnel100.127.0.0/16; WAN192.0.2.0/24 dan198.51.100.0/24; pelangganA10.77.0.0/16 danB10.88.0.0/16. RFC5737 tidak dirutekan ke internet. Alamat100.127 adalah shared address space, bukan ruang bebas konflik; periksa CGNAT/VPN/router host dan pilih pool yang sah sebelum provision. Benturan→BLOCKED, tidak mengubah jaringan host untuk “membuatnya cocok”.

Contoh baseline satu gateway: server tunnel100.127.0.1, NAS .11/.12/.13. Primary RADIUS/receiver pada .1. Secondary hanya diisi jika tersedia. Jika alias .2 dan proses kedua berada pada gateway yang sama, peer allowed-address terdiri .1/32 dan.2/32, bind/firewall/route harus cocok, dan hasil hanya redundancy proses. HA lintas host memerlukan peer/route/tunnel ke gateway kedua yang tetap hidup saat gateway pertama mati; alamat sekunder melalui gateway pertama tidak memenuhi uji host failure.

Project baru menggunakan prefix `rtrw-lab-<run_id>` dan kepemilikan ID run. Management menuju controller bukan Cloud bridge ke LAN pelanggan. NAT internet untuk download/updates hanya melalui allowlist manifest; tidak pernah menjadi route transit pelanggan lewat VPN SaaS. Stop/restart/restore/hapus hanya resource owned, termasuk dua host bila terpisah; baseline host/controller bersama tidak di-restore otomatis.

Resource estimate lama bukan kuota. File2 wajib menyediakan budget vCPU/RAM/disk/parallel/rate/biaya/durasi. Preflight memeriksa available headroom≥alokasi+snapshot+evidence; kekurangan→BLOCKED. Threshold operasional abort memakai limit eksplisit manifest, clock skew>5detik, disk watermark, evidence sink failure dan akses yang dicabut. Kill-switch: stop harness dan pengiriman mutasi baru; amankan evidence; rollback resource owned sesuai rencana; tidak blind restore seluruh server. Cleanup memverifikasi diff ID objek sebelum/sesudah; kegagalan cleanup dicatat, tidak menghapus evidence dahulu.
