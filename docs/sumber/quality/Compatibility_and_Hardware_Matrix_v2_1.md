# Kompatibilitas dan batas hardware — MicroTix v2.1

[REVISI AUD-01–46 / MAC-01–08] Proyeksi normatif kontrak master v2.1 revisi 2.1-macro.1. Bagian AUD di bawah dihasilkan dari master; §23 MAC memperinci retensi/PDP/RADIUS/dependency/gate. Baca master §23 dan Quality_Gates_and_Release_Readiness_v2_1.md sebelum implementasi. Status runtime NOT_RUN.

## 10. RADIUS: tenant, skema, atribut, dan lifecycle NAS

[REVISI AUD-19] Tenant berasal dari identitas transport klien NAS terdaftar dan secret yang diverifikasi, bukan User-Name, NAS-IP-Address di payload, atau Client-Shortname yang diterima dari pengguna. Secret unik per NAS; seluruh paket melalui tunnel. Unknown client atau Message-Authenticator invalid/absent pada Access-Request dibuang sesuai kebijakan; negative test lulus bila tidak ada Access-Accept dan tidak ada kebocoran, bukan wajib menerima Access-Reject.

`radius.nas` unik pada router dan source IP terdaftar. Satu username dapat mempunyai banyak check/reply attribute: hapus klaim UNIQUE(tenant_id,username) pada radcheck. Uniqueness proyeksi memakai tenant+account+attribute+scope+ordinal; atribut single-value memiliki tepat satu nilai efektif setelah resolver menerapkan override router > paket > tenant. Konflik pool/group/reply tidak diselesaikan oleh urutan UNION SQL.

[REVISI AUD-20] Snippet SQL/unlang lama adalah ilustrasi yang digantikan kontrak berikut, bukan kode siap salin. Role RADIUS hanya EXECUTE facade fungsi DB yang telah diaudit: lookup NAS minimum untuk bootstrap; authorize, accounting, postauth, dan session admission dalam transaksi masing-masing. Facade mengikat router terverifikasi ke tenant, memakai query parameter/escaping sesuai driver, mengaktifkan konteks RLS transaction-local, dan mengembalikan hasil terbatas. Tidak ada SET tenant lalu query berikut di pool tanpa transaksi yang sama. Owner facade tidak memiliki BYPASSRLS/ownership exemption; search_path hanya schema tepercaya dan pg_temp terakhir; revoke EXECUTE PUBLIC dan CREATE pada schema tepercaya. Kunci fungsi tidak boleh menerima tenant dari packet sebagai otoritas.

App service menulis access_account dan proyeksi melalui principal projection-writer dalam transaksi bisnis yang sama; bukan broad DML lintas tenant. radius_ro/radius_acct adalah nama peran fungsional; akses langsung lintas tenant ke tabel bukan solusi untuk RLS yang memblokir query. Secret plaintext pada radcheck/nas adalah pengecualian penyimpanan yang eksplisit: host/role terbatas, backup terenkripsi, no debug dump, tidak untuk UI/export umum. PAP dapat diverifikasi dengan skema tertentu; cleartext dipilih baseline untuk kompatibilitas CHAP dan MS-CHAPv2, bukan klaim semua protokol selalu membutuhkan bentuk sama.

| Kelompok | Kontrak |
|---|---|
| Control/check internal | Cleartext-Password, Auth-Type Reject, Simultaneous-Use, Expiration; Max-All-Session hanya bila modul akumulasi terbukti |
| Reply ke NAS | Mikrotik-Rate-Limit, Framed-Pool atau Framed-IP-Address, Acct-Interim-Interval, Session/Idle-Timeout; atribut vendor sesuai dictionary versi terpin |
| Resolver | enforce kind, state, valid_from/until, allowed routers, binding, static subnet, MAC, FUP dan hold sebelum Accept |
| Kecepatan | rx=upload dari pelanggan, tx=download ke pelanggan; integer bit/s dikonversi tanpa pembulatan float |
| Static IP | override router → static_ip bila subnet valid → pool hanya bila static_ip null; IP terkonfigurasi invalid ditolak, tidak diam-diam berubah ke pool |
| Kedaluwarsa | valid_until eksklusif pada midnight timezone bisnis; konversi UTC; Session-Timeout tidak melewati batas itu |

Max-All-Session, Expiration dan Simultaneous-Use bukan atribut reply universal. Batas byte/waktu kumulatif memerlukan modul counter/server policy serta accounting, bukan hanya baris radreply. Hotspot http-chap/PAP/MAC/cookie diuji sesuai kemampuan yang benar; jangan mewajibkan MS-CHAPv2 pada seluruh jenis login Hotspot.

[REVISI AUD-21] `read_clients` SQL tidak berarti registrasi NAS live otomatis. Enrollment/revoke/rotation membuat desired NAS revision, kemudian privileged reconciler menghasilkan konfigurasi tervalidasi dan rolling restart/reload yang memang didukung versi terpin. Tandai `nas_applied_revision` hanya setelah probe menerima/menolak sesuai target. Jangan mengklaim revoke selesai sebelum cache klien kedua instance dicabut. Dua proses pada satu VM hanya redundansi proses; tidak menjamin host, disk, DB, listrik atau tunnel tetap hidup. Host HA memerlukan failure domain independen dan bukti G4.

Default Dynamic Authorization adalah Disconnect-Request RFC5176 pada port 3799 yang dipasang eksplisit; jangan menyebut PoD sebagai protokol ekuivalen yang pasti didukung RouterOS. CoA hanya capability per fitur/build yang terbukti; jika tidak, perubahan berlaku pada sesi berikutnya atau Disconnect yang dampaknya sudah diotorisasi. Sumber IP dispatcher, shared secret dan identifier sesi harus cocok NAS target.

## 11. Cutover dan rollback B0–B6

[REVISI AUD-22] Pencocokan akun lokal dapat mengalahkan RADIUS. Mengaktifkan use-radius saja tidak membuktikan canary. PPP AAA umumnya scope global; jangan mengeklaim bisa diaktifkan per satu PPPoE server tanpa capability yang membuktikannya. B0 wajib menilai dampak ke semua protokol PPP pada router, bukan hanya akun terpilih.

| Tahap | Prasyarat, aksi, dan kriteria keluar |
|---|---|
| B0 preflight | mode manage, radius.cutover+MFA+reauth, izin valid selama langkah, versi/build teruji, backup valid, jalur recovery, baseline seluruh shared setting, coverage rollback dan snapshot revision cocok; RADIUS eksternal tanpa rencana coexistence →BLOCKED |
| B1 parity | per akun ready: auth sintetis memakai NAS test terdaftar dan konteks tenant/router yang sama melalui facade uji terotorisasi; uji credential/kind/pool/rate/state; nol kegagalan dan nol binding ambigu; tes ini bukan bukti login lewat NAS produksi |
| B2 install | pasang hanya klien platform, incoming port, dan rule sempit yang direncanakan; restore baseline shared resource harus tersimpan; endpoint primer/sekunder dan route /32 terjangkau; readback lulus |
| B3 canary | gunakan akun sintetis/canary yang tidak cocok akun lokal, atau metode penghilangan shadow yang sudah diuji dan diotorisasi per objek; PPP global side effect termasuk rencana; amati 1800 detik nyata; minimal 100 auth valid, keberhasilan ≥99%, nol salah Accept/atribut/tenant, Start/Interim/Stop benar, sesi kontrol existing tetap sesuai baseline |
| B4 shadow_active | enable scope penuh yang direncanakan dan observasi 86400 detik nyata; job memakai deadline kind dan grant/window yang cukup; belum selesai observasi →pending/BLOCKED, bukan dipercepat untuk gate runtime |
| B5 authoritative | batch≤100; setiap source mendapat ownership consent, fingerprint/revision cocok, tidak ada local shadow yang tersisa; uji login nyata membuktikan RADIUS; hanya lalu router ditandai authoritative |
| B6 rollback | cabang dari tahap yang telah mengubah router; restore snapshot nilai sebelum operasi, bukan hardcode use-radius=no; pulihkan hanya objek/run yang masih cocok revision; probe login+accounting, pertahankan data DB dan audit |

B5 memilih metode berdasarkan matriks lab exact: disable bila terbukti menghilangkan shadow; jika tidak, archive_rename bila terbukti menjaga sesi dan rollback; delete hanya jika secara eksplisit diotorisasi, backup memuat semua material pemulihan dan restore sudah diuji. Jika tidak ada metode sah, B5 BLOCKED; jangan menghapus otomatis karena disable gagal. Akun sumber existing tidak wajib punya prefix rtrw, tetapi harus memiliki consent ownership per-object dalam CutoverRun.

[REVISI AUD-23] Rollback tidak boleh mengaktifkan semua user yang sebelumnya disabled, menghapus RADIUS pihak lain, mengubah global AAA seenaknya, atau menghidupkan akun yang sekarang ditahan security/manual. Backup awal hanya mencakup akun saat itu; akun baru, rename dan password yang berubah sesudah cutover memerlukan recovery export terkini. Jika coverage ini tidak lengkap, rollback lama tidak dinyatakan aman. Buat delta recovery yang diotorisasi atau tandai recovery_required. Rollback tidak menggunakan reset/reboot/restore binary rutin.

`enforcement_mode=local|radius_shadow|radius_authoritative|degraded` adalah status router, bukan status bisnis akun. Login/pindah router hanya dinyatakan terjamin dalam batas lab yang terbukti, binding lengkap dan tidak ada jalur autentikasi alternatif yang melewati policy. Tidak ada janji nol downtime universal.

## 17. ACS/CPE dan rotasi kredensial

[REVISI AUD-36] Default publik ACS menggunakan hostname HTTPS terpisah pada443; port7547 adalah CWMP internal/contoh port bila manifest secara eksplisit membukanya. NBI7557/FS7567/UI3000/Mongo27017 tetap internal. File download CPE melalui endpoint gateway bertoken, path/hash/model allowlist; FS internal tidak otomatis dapat dijangkau CPE. NBI tidak diasumsikan mempunyai autentikasi bawaan; wajib private bind/firewall dan service-auth proxy/mTLS bila lintas proses/host. Caddy HTTP reverse proxy tidak memerlukan plugin stream untuk CWMP HTTP; fitur non-HTTP memerlukan desain tersendiri.

DeviceID serial+OUI+product_class adalah identifier, bukan bukti kepemilikan. Claim memakai secret sekali pakai yang benar-benar dipasang pada kredensial CWMP sebelum Inform; secret di QR yang tidak pernah dikirim/periksa tidak memberi jaminan. Factory credential bersama tidak boleh meluluskan claim; gunakan provisioning lokal atau isolated bootstrap enrollment yang sudah diotorisasi. Karantina berlaku setelah identitas transport diverifikasi, tanpa mengirim password PPPoE ke perangkat belum terikat tenant. Alias serial yang berpindah tenant mengikuti proses transfer ownership, bukan auto-claim.

TR-098 path harus penuh berawalan InternetGatewayDevice.; TR-181 berawalan Device. Indeks ditemukan, pemetaan menghubungkan WiFi.Radio/SSID/AccessPoint melalui reference, bukan menyamakan nomor instance. Password sering write-only/masked; GetParameterValues tidak dianggap dapat membaca password aktual. Capability/version per model harus menyatakan mekanisme verifikasi: RPC/status, parameter key/config revision, dan functional reconnect bila writable secret tidak readable.

[REVISI AUD-37] Rotasi password memakai dua profil. Profil default otomatis hanya jika ada jalur manajemen CPE independen dari PPPoE yang diubah: simpan pending+old version; Set CPE; verifikasi RPC/config revision; update RADIUS; uji PPP login baru via NAS; commit rotation; hapus old secret sesuai retensi aman. Jika update CPE mungkin sudah diterapkan tetapi response hilang, status uncertain, bukan “RADIUS lama pasti aman dan pelanggan tidak terputus”. Baca state/fungsional sebelum retry.

Jika ACS berbagi koneksi PPPoE yang akan putus, automated rotation BLOCKED kecuali recovery lokal atau mekanisme overlap dua credential yang telah diuji per PAP/CHAP/MS-CHAP dan diotorisasi tersedia. Tidak mengarang transaksi atomik ACS↔RADIUS. Kompensasi memulihkan sisi yang benar-benar berubah memakai old version dan readback; kegagalan recovery →recovery_required dengan pekerjaan independen tetap berjalan.

Status task perangkat ACS adalah queued/waiting_inform/running/verifying/succeeded/failed/expired/cancelled; hasil job pembungkus menggunakan AUD-14 termasuk uncertain/recovery_required, dipetakan eksplisit oleh EXE-02; NBI200 atau202 disimpan terpisah dari job API platform. Task disappeared bukan bukti sukses karena bisa dihapus/expired; gunakan outcome RPC/fault dan readback/fungsi yang relevan. ID hilang setelah timeout submit →uncertain, cari korelasi task sebelum kirim ulang. Reboot/download/reset tidak diulang buta. Connection Request di balik NAT mungkin dimungkinkan dengan mapping/UDP/STUN yang telah diuji; default tetap waiting_inform. Jangan mewajibkan STUN bila tidak tersedia. TTL24jam mencabut task tertunda yang dimiliki run sebelum expired dinyatakan selesai, agar tidak terlaksana belakangan tanpa izin.

## 19. GNS3, jaringan lab, dan resource

[REVISI AUD-39] Jangan mengunci GNS3 API v2 tanpa inventaris. Pilih family v2/v3 dari endpoint versi yang diizinkan dan dokumentasi versi aktual; controller/compute compatibility diverifikasi; base URL disimpan lengkap dengan prefix sekali, bukan menambahkan /v2 pada URL yang sudah mempunyai /v3. MCP opsional, bukan dependency. Version discovery hanya host/port yang sudah diotorisasi; tidak memindai jaringan mencari server.

Lab0: Linux gateway WireGuard+FreeRADIUS+PostgreSQL lokal sebagai baseline produksi co-located, AUT mengakses lewat route/firewall eksplisit; CHR adalah NAS; Linux PPPoE client menggunakan pppd/plugin PPPoE pada segmen L2 pelanggan, bukan DHCP client; Hotspot client memakai segmen L2 terpisah dan browser uji. Klien pelanggan tidak dijadikan peer manajemen WG. Lab1 menambah dua NAS tenantA dan satu NAS tenantB; Lab2 cutover; Lab3 fault/load; Lab4 ACS per model dan WAN per topologi. Emulator CPE hanya bukti kontrak, bukan sertifikasi model fisik.

Contoh alokasi logis, belum merupakan alamat host pemilik: management10.255.0.0/24; AUT10.255.10.0/24; tunnel100.127.0.0/16; WAN192.0.2.0/24 dan198.51.100.0/24; pelangganA10.77.0.0/16 danB10.88.0.0/16. RFC5737 tidak dirutekan ke internet. Alamat100.127 adalah shared address space, bukan ruang bebas konflik; periksa CGNAT/VPN/router host dan pilih pool yang sah sebelum provision. Benturan→BLOCKED, tidak mengubah jaringan host untuk “membuatnya cocok”.

Contoh baseline satu gateway: server tunnel100.127.0.1, NAS .11/.12/.13. Primary RADIUS/receiver pada .1. Secondary hanya diisi jika tersedia. Jika alias .2 dan proses kedua berada pada gateway yang sama, peer allowed-address terdiri .1/32 dan.2/32, bind/firewall/route harus cocok, dan hasil hanya redundancy proses. HA lintas host memerlukan peer/route/tunnel ke gateway kedua yang tetap hidup saat gateway pertama mati; alamat sekunder melalui gateway pertama tidak memenuhi uji host failure.

Project baru menggunakan prefix `rtrw-lab-<run_id>` dan kepemilikan ID run. Management menuju controller bukan Cloud bridge ke LAN pelanggan. NAT internet untuk download/updates hanya melalui allowlist manifest; tidak pernah menjadi route transit pelanggan lewat VPN SaaS. Stop/restart/restore/hapus hanya resource owned, termasuk dua host bila terpisah; baseline host/controller bersama tidak di-restore otomatis.

Resource estimate lama bukan kuota. File2 wajib menyediakan budget vCPU/RAM/disk/parallel/rate/biaya/durasi. Preflight memeriksa available headroom≥alokasi+snapshot+evidence; kekurangan→BLOCKED. Threshold operasional abort memakai limit eksplisit manifest, clock skew>5detik, disk watermark, evidence sink failure dan akses yang dicabut. Kill-switch: stop harness dan pengiriman mutasi baru; amankan evidence; rollback resource owned sesuai rencana; tidak blind restore seluruh server. Cleanup memverifikasi diff ID objek sebelum/sesudah; kegagalan cleanup dicatat, tidak menghapus evidence dahulu.
