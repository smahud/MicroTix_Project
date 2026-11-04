# MicroTix — lingkungan, lab, dan operasi

Pembangunan aplikasi di workspace tidak memerlukan formulir izin server baru. Instruksi pengguna dan konfigurasi akses yang berlaku menentukan kewenangan. Input target diperlukan ketika sebuah langkah benar-benar memakai server, GNS3, router, CPE atau produksi. Kredensial bukan pengganti informasi target/scope.

## 1 Input minimum saat diperlukan

| Kegiatan | Input yang diperlukan | Tanpa input |
|---|---|---|
| Build/test lokal | Repo/workspace yang diberikan; runtime/resource tersedia | Agent membuat bootstrap/config dev/fixture yang dapat direproduksi |
| Lab lokal Linux/FreeRADIUS | Port terisolasi, resource dan target milik run | Bangun harness; laporkan test yang belum dapat dijalankan |
| GNS3/CHR | Controller URL+version/auth binding, project/compute yang boleh dipakai, image+lisensi, alamat/jalur manajemen, budget CPU/RAM/disk/durasi, scope fault+cleanup | Blokir verified_lab yang terkait, lanjut kode/tes independen |
| CPE/OLT | Model/firmware, akses dan recovery, mapping parameter/protokol yang diuji | Adapter/simulator boleh dibuat; tidak klaim dukungan perangkat |
| Deployment/pilot | Target host/IP/NAT/DNS, secret bindings, backup/recovery, scope perubahan+window dan akses yang telah diizinkan pengguna | Siapkan artefak/runbook; jangan deploy ke target tebakan |
| Penjualan/publikasi | Domain/logo/kontak dan tujuan pembayaran yang diverifikasi operator, konten layanan/privasi, fitur yang telah memenuhi gate | Local preview tetap berjalan; jangan memublikasikan klaim/rekening |

Catat target lokal/remote dan batas operasi singkat di docs/progress.md atau config privat yang diabaikan git. Metadata minimum: target_id, environment, URL/host, expected identity/TLS atau SSH pin, permitted operations, budget, secret binding names, recovery, evidence path. Nilai null berarti belum diketahui, bukan wildcard. Scope yang sudah diberikan tidak diminta ulang. Tidak perlu 200 field/grant registry untuk menjalankan unit test.

Jangan commit password/PAT/token/private key/bukti bayar/PII. Gunakan injection secret runtime. Metadata privat host/contacts boleh tetap di config privat;.env.example hanya nama variabel dan contoh development yang jelas. GNS3 family v2/v3 ditemukan dari endpoint versi pada controller yang diizinkan, bukan scanning jaringan atau menambah prefix /v2 secara buta.

## 2 Lab bertahap

Lab minimum: Linux gateway WireGuard+FreeRADIUS+PostgreSQL, satu CHR sebagai NAS, Linux pppd/plugin PPPoE client pada segmen L2 pelanggan, Hotspot client/browser pada segmen terpisah. Client pelanggan bukan peer WireGuard manajemen. Tambah NAS A2 dan B1 untuk multi-router dan isolasi tenant A/B. Gunakan dua akun/sesi kontrol non-target, fixture seed261029, data sintetis dan build/versi tercatat.

Tahap: (1) transport/API/enrollment/backup spike; (2) RADIUS tenant/auth/accounting; (3) cutover/rollback dan local shadow; (4) fault/crash/load; (5) ACS per model dan WAN per topology saat fase aktif. Simulator/emulator hanya bukti kontrak. Synthetic radclient bukan bukti PPPoE client nyata; CHR bukan bukti kapasitas perangkat fisik CCR/hAP.

Alamat contoh RFC5737 dan pool100.127/16 bukan alamat aktual pengguna. Verifikasi overlap CGNAT/LAN/VPN/host sebelum provision. Dua endpoint pada gateway sama bukan host HA. Untuk host HA, gateway/route/data/key kedua harus hidup ketika primer hilang; alamat kedua yang tetap melewati gateway primer tidak cukup.

Resource GNS3 milik run ditandai ID/prefix; cleanup hanya project/node/peer/objek yang dimiliki dan tercakup scope. Tidak restore seluruh shared host/controller. Abort bila akses dicabut, clock skew>5 detik, resource melebihi budget, disk/evidence sink gagal, atau hasil isolasi salah. Stop pengiriman mutasi baru, amankan evidence dan lakukan recovery yang sah. Catat leftover dan recovery_required; jangan menghapus evidence sebelum cleanup diverifikasi.

B3 1.800 detik/B4 86.400 detik, protocol TTL dan soak memakai waktu nyata. Fake clock hanya kalender/retensi logika bisnis. Worker observasi memiliki state durable dan resume; agent tidak perlu memegang tool call blocking sehari. Waktu belum terpenuhi berarti RUNNING/BLOCKED sesuai kondisi aktual, bukan PASS. Checkpoint menyimpan deadline, langkah tersisa dan pemantauan yang masih berjalan.

## 3 Deployment dan operasi awal

Pilot dapat satu VM dengan aplikasi Compose dan layanan privileged systemd, PostgreSQL17 native, private storage volume, backup off-host. Ini satu failure domain. Caddy/Gunicorn produksi; bukan Vite dev server/Django runserver. API tanpa root/CAP_NET_ADMIN/Docker socket. Typed host manager dengan akun OS/unit terpisah, nftables dimuat atomik dan diuji setelah Docker/firewall reload. Jangan membangun cluster sebelum pengukuran membutuhkannya.

Inventory host: vCPU/RAM/disk/IOPS, hypervisor, uplink/NAT/public IP, DNS/UDP reachability, NTP/TLS renewal, off-host destination dan key recovery. Pin image/package/lockfile dan cek lisensi, terutama FreeRADIUS/proses terpisah. Build artifact dari CI, distribusikan digest; schema expand/contract, drain worker dan rekonsiliasi sebelum resume mutasi. DB/FreeRADIUS/NBI/metrics tidak publik.

Observability minimum: latency/error API dan AAA, queue age/fairness/uncertain/recovery_required, DB locks/pool, disk+staging, backup/WAL lag, collector/accounting lag, auth failure dan NAS applied revision. Alert berbasis bukti, bukan memetakan collector mati menjadi router mati. Metrics retensi dan agregasi mengikuti ROUTEROS/defaults.

Feature flags sandbox dan produksi berbeda. Flag diperiksa backend serta UI. Daily menu/marketing hanya fitur released; environment QA boleh menguji fitur belum released. Flag produksi tidak berubah saat dokumen dicek atau test lokal lulus. Payment tetap tercatat ketika jaringan terganggu; setelah restart rekonsiliasi policy/account/payment terkini sebelum menjalankan mutasi lama.

## 4 Backup platform dan DR

Lindungi DB+WAL (bisnis/radius/ledger), blob privat, key material/version, config RADIUS, NAS/VPN registry, config aplikasi dan datastore ACS saat R3. Off-host terenkripsi, key recovery terpisah dan teruji. Backup oleh principal yang memang dapat mencakup semua scope; jangan menghasilkan backup sebagian akibat RLS lalu menyebutnya lengkap.

Urutan restore: key/recovery/config aman→DB+radius pada jaringan tertutup→gateway+FreeRADIUS setelah akun/secret valid→API dan rekonsiliasi payment/policy/session→worker mutasi→artifact/ACS/modul relevan. Jangan melayani auth dari state akun yang belum diperiksa. Sebelum isolir berjalan, transaksi setelah titik backup direkonstruksi/direkonsiliasi dari sumber durable/eksternal yang sah.

Target RPO≤15 menit, RTO≤4 jam. Ukur RTO sejak gangguan layanan dimulai hingga scope inti pulih+rekonsiliasi, termasuk detection/provisioning, bukan sejak tombol restore. RPO dari acknowledged transaction sequence yang pulih, bukan timestamp WAL saja. RPO15 menit tidak sekaligus berarti nol transaksi hilang. Latih restore/rollback, catat actual+cleanup; tabletop tidak membuktikan RTO. SLA hanya setelah G5 dan angka aktual. Drill2 kali/tahun adalah kebijakan operasional setelah deployment, bukan task terjadwal yang dibuat oleh audit ini.

## 5 Retensi dan privasi

Nilai log/app/access/security, accounting/usage dan idempotency di defaults; posted journal immutable. Dokumen keuangan minimum10 tahun kalender, sekurangnya sejak akhir tahun buku terkait menurut policy baseline, dan tersimpan di Indonesia sesuai kebutuhan penyimpanan yang berlaku. Contoh tahun buku berakhir31 Desember 2026: jangan purge sebelum1 Januari 2037. Legal hold atau masa dokumen lebih panjang menang; perubahan konfigurasi tidak memendekkan batas tersnapshot. Retensi10 tahun bukan durasi untuk seluruh PII pelanggan.

Purge/anonimisasi data nonkeuangan terpisah dari operational DML ledger. Penghapusan arsip finansial setelah waktunya memakai principal/prosedur terbatas dengan review, dependency legal hold, dry-run, audit dan pemulihan sesuai policy; runtime tidak memperoleh DELETE jurnal posted. Data/key/version yang diperlukan untuk bukti tetap dapat dipulihkan. Data biasa SaaS mengikuti ended_at+180 hari; dokumen finansial/hold dikecualikan. Tindakan purge tidak otomatis aktif hanya karena timer berjalan.

Peran pengendali/prosesor dan DPA dikonfirmasi untuk pemrosesan aktual. Tool Owner mendukung cari subjek, akses/export/koreksi/anonimisasi, minimisasi log/foto/lokasi, dan persetujuan pemasaran terpisah. Dokumen/software bukan sertifikat kepatuhan hukum/akuntansi.

Insiden PDP: simpan earliest known failure dan waktu diketahui dalam UTC, jangan reset clock saat pindah petugas. Policy baseline menggunakan deadline pemberitahuan pengendali maksimum3×24 jam, eskalasi prosesor internal maksimum24 jam **di dalam window itu**, draft≤24 jam, delivery readiness≤48 jam. Isi pemberitahuan memuat data yang terdampak, waktu/cara terungkap dan penanganan/pemulihan. Penanggung jawab/deputi dan kanal ke subjek serta lembaga yang sah diverifikasi sebelum go-live; jangan menebak kanal regulator atau menunggu seseorang hadir sampai lewat tenggat. Tindakan pengiriman nyata tetap sesuai kewenangan yang diberikan; pengujian memakai recipient sintetis/sink.

Dasar yang dicek5 November 2026: [UU27/2022 Pasal46](https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/), [UU28/2007 Pasal28(11)](https://www.pajak.go.id/id/undang-undang-nomor-28-tahun-2007), [PP50/2022 Pasal11](https://stats.pajak.go.id/index.php/id/peraturan/tata-cara-pelaksanaan-hak-dan-pemenuhan-kewajiban-perpajakan). Clock24/48 jam dan perhitungan akhir tahun adalah policy operasional proyek; jangan mengatribusikannya sebagai kutipan seluruh teks undang-undang. Review profesional dilakukan untuk penggunaan nyata terkait, bukan sebagai blocker menulis kode lokal.

## 6 Kapasitas dan gate per tahap

Profil bertahap10/100/1.000 tenant,2 router dan300 service/tenant; CPE200/tenant hanya R3. Baseline auth50 request/detik pada profil awal dan accounting=active_sessions/300 detik. Ramp10 menit, warmup10 menit tidak disampel, steady30 menit; soak8 jam untuk10/100,24 jam untuk1.000. Minimal10.000sampel percentile dengan nearest-rank pada sampel mentah; timeout masuk gagal, injected faults denominator terpisah.

Storm10% dari300.000 sesi reconnect60 detik=500auth/detik tambahan; stress2.000auth/detik60 detik profil terpisah. Pass target PRODUCT NFR-01, non-injected error<0,1%, nol tenant leak/unbalanced/duplicate/lost acknowledged effect; setiap tenant aktif mendapat progress dalam60 detik dalam budget. Fixture100.000 service/tenant khusus query lab tidak mengubah plafon Platinum5.000.

Jangan menjalankan beban/fault besar pada target tanpa budget CPU/RAM/disk/rate/durasi yang nyata. Hasil berlaku pada feature+adapter/firmware+topology+load profile+config yang diuji. Perubahan relevan membatalkan evidence terdampak, bukan seluruh test suite tanpa alasan. Kapasitas diperbesar setelah G4/G5; R1 lokal tidak menunggu benchmark1.000 tenant.
