# Playbook RouterOS — Platform SaaS Manajemen RT/RW Net

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


**Versi 1.1** · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.0 (11 Oktober 2026) → 1.1 (28 Oktober 2026; templat akun `rtrw-mut` mode Kelola diperjelas, catatan aturan 3799 pada cutover — putusan DOC pada `decisions_log.md` Bagian E)
Dokumen normatif pendamping untuk bagian 7, 8, 9, 18, 20 PRD v1.4 dan TD v1.3. Memuat konvensi, templat perintah RouterOS v7, batas kemampuan, dan prosedur pemulihan. **Semua perintah adalah templat rancangan**: sintaks, nama properti, dan perilaku wajib dibuktikan pada RouterOS nyata/CHR (T01, T13, T16–T22) dan hasilnya dicatat pada `docs/compatibility.md` sebelum dipakai pada router pelanggan. Placeholder ditulis `<…>`.

## 1 Konvensi

- **Namespace**: setiap objek buatan platform membawa `comment` berawalan `rtrw:` diikuti jenis dan ID (mis. `rtrw:wg`, `rtrw:radius:<router_id>`). Penghapusan dan pembaruan hanya pada objek ber-namespace yang cocok dengan catatan kepemilikan di database (`ownership`).
- **Tanpa efek samping**: skrip tidak mengubah default route, bridge, DHCP, DNS, akun existing, atau firewall pelanggan; aturan firewall platform ditempatkan di atas dengan `place-before=0` hanya bila perlu dan selalu sempit (sumber /32 server, antarmuka `rtrw-wg`).
- **Idempoten**: setiap blok mencari objek ber-namespace (`find where comment="rtrw:…"`) sebelum menambah.
- **Rahasia** mengikuti AUD-16: hanya token enrollment berumur pendek dalam skrip salinan. Credential memakai CSPRNG terverifikasi; `:rndstr` tidak dinyatakan aman tanpa bukti exact build. Jika capability tidak terbukti, jalur tersebut BLOCKED; tidak mengganti dengan RNG lemah.
- **Versi**: RouterOS v7 (seri stable/long-term yang lulus lab). v6 hanya baca. Versi persis, arsitektur, dan paket yang diuji dicatat.
- Arah kecepatan: pada `rate-limit` MikroTik, bagian pertama (rx) adalah unggah dari pelanggan, bagian kedua (tx) adalah unduh ke pelanggan.

## 2 WireGuard (NET-01)

```routeros
/interface wireguard add name=rtrw-wg comment="rtrw:wg"          # private key dibuat router
/interface wireguard peers add interface=rtrw-wg public-key="<server_pub>" \
    endpoint-address=<server_host> endpoint-port=<server_udp_port> \
    allowed-address=<server_tunnel_ip>/32 persistent-keepalive=25s comment="rtrw:wg:peer"
/ip address add address=<router_tunnel_ip>/32 interface=rtrw-wg comment="rtrw:wg:addr"
/ip route add dst-address=<server_tunnel_ip>/32 gateway=rtrw-wg comment="rtrw:wg:route"
```

Catatan: `allowed-address` hanya /32 server. Pemeriksaan overlap (alamat/rute/bridge) dilakukan sebelum langkah ini. Public key router dibaca (`/interface wireguard get rtrw-wg public-key`) dan dikirim ke server. Keepalive hanya bila router di balik NAT. MTU diuji (nilai awal 1420; dikonfigurasi).

## 3 Sertifikat dan API-SSL (NET-04)

Template executable API-SSL ditahan sampai preflight membuktikan ownership/shared-setting baseline, jalur manajemen, consent perubahan dan rollback. Terapkan kontrak enrollment AUD-16; jangan menimpa certificate/address api-ssl existing secara global tanpa ChangePlan yang sah. Pin baru disimpan sesudah enrollment tervalidasi.

Sidik jari SHA-256 sertifikat dibaca dan dikirim ke server pada `enroll/complete`; server menyimpan dan memin. Pergantian sertifikat memerlukan tindakan rotasi yang tercatat.

## 4 Akun dan grup (NET-05, NET-07)

Template akun wajib memakai policy minimum teruji dan CSPRNG terverifikasi menurut AUD-16. Monitoring tidak mendapat write; mode manage memerlukan akun terpisah dan mandat. Kegagalan bukti RNG/policy menahan pembuatan credential; tidak ada snippet siap salin.

Daftar policy minimum per fungsi (baca, tulis PPP/Hotspot/RADIUS client, fetch/backup, firewall bernamespace) disusun dari uji lab dan disimpan di `docs/compatibility.md`. Policy `sensitive`, `policy`, `reboot`, `password`, `ftp`, `sniff`, `romon` tidak diberikan kecuali fungsi menuntut dan terdokumentasi. Grup `rtrw-migrate` (policy `read,api,sensitive`) hanya untuk akun migrasi sementara (bagian 8).

## 5 Firewall input bernamespace

```routeros
/ip firewall filter add chain=input action=accept protocol=tcp dst-port=8729 \
    src-address=<server_tunnel_ip>/32 in-interface=rtrw-wg comment="rtrw:fw:api" place-before=0
/ip firewall filter add chain=input action=accept protocol=udp dst-port=3799 \
    src-address=<server_tunnel_ip>/32 in-interface=rtrw-wg comment="rtrw:fw:coa" place-before=0
```

Aturan lain (drop terakhir, FastTrack) tidak diubah. Bila chain input pelanggan berakhir dengan `drop` umum, aturan platform harus berada di atasnya; preflight memeriksa urutan dan menolak apply bila tidak dapat ditempatkan dengan aman.

## 6 Klien RADIUS dan AAA (RAD-10)

```routeros
/radius add service=ppp,hotspot address=<server_tunnel_ip> secret=<radius_secret> \
    src-address=<router_tunnel_ip> authentication-port=1812 accounting-port=1813 \
    timeout=3s comment="rtrw:radius:primary"
/radius add service=ppp,hotspot address=<secondary_ip> secret=<radius_secret2> \
    src-address=<router_tunnel_ip> timeout=3s comment="rtrw:radius:secondary"      # node HA/edge replica bila ada
/radius incoming set accept=yes port=3799
/ppp aaa set use-radius=yes accounting=yes interim-update=5m
/ip hotspot profile set [find name=<hs_profile>] use-radius=yes
```

Cutover B0–B6 dan rollback hanya mengikuti kontrak master §11 AUD-22–23. Snippet §6 adalah nama properti ilustratif, bukan urutan executable: shared AAA/incoming harus masuk ChangePlan, readback dan baseline recovery; secondary hanya setelah jalur/key teruji. B5 deletion tidak otomatis; B6 restore snapshot/revision dengan hold tetap berlaku.

## 7 PPPoE, profil, pool, dan antrean (templat R4, referensi untuk adopsi)

```routeros
/ip pool add name=<pool_name> ranges=<a.b.c.d-a.b.c.e> comment="rtrw:pool"
/ppp profile add name=<rtrw-profile> local-address=<gw_ip> remote-address=<pool_name> \
    dns-server=<dns> only-one=no change-tcp-mss=yes comment="rtrw:profile"
/interface pppoe-server server add service-name=<svc> interface=<lan_if> default-profile=<rtrw-profile> \
    one-session-per-host=yes disabled=no comment="rtrw:pppoe"
```

- Kecepatan dikirim dari RADIUS (`Mikrotik-Rate-Limit`), sehingga profil router hanya memuat `local-address`, pool, DNS, MSS; profil tidak menyimpan harga atau paket.
- Antrean dinamis per sesi memakai CPU; untuk > ~1.000 sesi per router rancangan antrean (PCQ/queue tree) dan batas perangkat diuji pada lab; platform tidak mengubah antrean pelanggan pada R1–R3.
- **FastTrack**: aturan `fasttrack-connection` dapat membuat trafik melewati antrean sehingga `rate-limit` tidak efektif. Platform mendeteksi (`fasttrack_may_bypass_queue`), melaporkan, dan tidak mengubah. Remediasi oleh operator (mis. mengecualikan antarmuka pelanggan dari aturan FastTrack) dan diuji.
- Isolir terbatas (opsional): pool `rtrw-isolir`, `address-list=isolir`, aturan NAT/redirect dan filter milik operator; templat disediakan dan tidak diterapkan otomatis.
- Hotspot: profil dengan `use-radius=yes`, `login-by` (http-chap/http-pap/mac-cookie/mac), `walled-garden` untuk halaman pembayaran bila operator memilih. Hotspot + PCC satu router tidak didukung.

## 8 Akun migrasi sementara (RAD-09, panen password)

Sebelum akun migrasi dibuat, tersedia cleanup waktu absolut≤24 jam yang dibaca ulang serta fallback startup. Server menghapus dan memverifikasi akun setelah panen. Bila scheduling absolut/cleanup tidak dapat dibuktikan, S1 BLOCKED (AUD-17). Tidak ada template startup-only yang memenuhi TTL.

[REVISI AUD-17] Credential migrasi tidak disimpan setelah panen; password hasil pembacaan hanya berada pada penyimpanan terenkripsi. Hasil cleanup masuk evidence run.

## 9 Backup dan export (BKP)

```routeros
/system backup save name=rtrw-<router_code>-<ts> password=<backup_pass> dont-encrypt=no
/export file=rtrw-<router_code>-<ts>                  # tanpa show-sensitive secara default
/tool fetch url="sftp://<server_tunnel_ip>:<receiver_port>/<path>" src-path=rtrw-<...>.backup \
    upload=yes user=<scoped_user> password=<scoped_pass> mode=sftp
# Cleanup memakai daftar exact artifact ID milik generation yang telah committed; bukan regex/prefix (AUD-33).
```

Export dengan `show-sensitive` hanya bila Owner memilih secara eksplisit karena memuat kredensial. Binary backup memuat seluruh konfigurasi dan MAC; restore memerlukan perangkat/versi yang sesuai. Verifikasi host SFTP oleh Fetch tidak diasumsikan; kontrol kompensasi pada TD §11.

## 10 Monitoring (MON)

- Health: `/system resource print`, `/interface print stats`, jumlah sesi PPP/Hotspot dari `radacct` (bukan polling penuh), waktu NTP (`/system clock`, `/system ntp client`).
- Opsional SNMPv3 baca-saja (autentikasi/enkripsi), dengan sumber dibatasi alamat tunnel server.
- Probe WAN dipaksa melalui ISP target (route per target + scope); minimal 2 target independen; ambang down 3/up 5 (konfigurasi).
- Netwatch dipakai hanya untuk fungsi lokal yang disetujui (mis. peringatan RADIUS tak terjangkau); tidak mengubah konfigurasi pelanggan.

## 11 Tingkat pembuktian lab

| Aspek | Bukti wajib | Uji |
|---|---|---|
| Bootstrap idempoten, tanpa perubahan layanan | Konfigurasi baseline, probe, sesi | T01 |
| API-SSL dengan pin | Pin cocok/berbeda, sertifikat rotasi | T01 |
| Akun dan policy minimum | Matriks perintah yang berhasil/ditolak per grup | T01 |
| RADIUS cutover dan rollback | Prioritas lokal/RADIUS, secret nonaktif vs hapus, CoA/Disconnect | T17, T20 |
| Backup transfer | Ukuran, SFTP, cleanup | T08 |
| Failover/PCC/Hotspot | Per topologi | T13 |

## 12 Lab

CHR (RouterOS) pada hypervisor lab dengan lisensi uji; topologi minimum: WAN tunggal, dua ISP, PPPoE server + klien uji, Hotspot, WireGuard ke server uji, RADIUS uji. Perangkat keras nyata (RB/hAP/CCR) untuk uji CPU antrean dan jumlah sesi. Data dan kredensial sintetis; tidak ada router pelanggan.
