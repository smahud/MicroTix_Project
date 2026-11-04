# MicroTix — adapter MikroTik dan prosedur jaringan

NET-01–NET-08, IMP-01–IMP-05, PRO/SYNC, MON dan BKP. Perilaku bisnis: [PRODUCT.md](PRODUCT.md); AAA dan B0–B6: [RADIUS.md](RADIUS.md). Tidak ada skrip deployment siap jalankan di paket dokumentasi; agent membangun adapter dan menguji sintaks terhadap exact build RouterOS.

## 1 Scope dan ownership

RouterOS v7 untuk mutasi/cutover, v6 hanya baca melalui jalur aman yang sudah tersedia. Tidak auto-upgrade. Simpan versi/build/architecture dan capability per fungsi, bukan sekadar label merek. Firmware berubah membatalkan evidence yang terdampak.

Objek buatan platform memakai identifier internal stabil rtrw dan database ownership (router,jenis,natural key,fingerprint,run). Prefix/comment saja tidak memberi izin menghapus..id hanya handle sesi. Rename display router tidak mengganti identity perangkat, peer atau akun pelanggan.

Enrollment hanya menambah manajemen minimum dalam preview. Tidak mengubah default route/bridge/DNS/DHCP/akun existing, tidak reset/reboot. Pada R1–R3 FastTrack/firewall pelanggan hanya dideteksi dan dilaporkan; firewall manajemen tambahan harus sempit dan milik plan. Shared settings seperti api-ssl, incoming RADIUS dan PPP AAA wajib baseline+diff+impact, tidak ditimpa oleh skrip generik.

## 2 Enrollment yang dapat dipulihkan

1. Owner membuat draft router dan mode read_only default. Server reserve /32 unik, token acak256 bit hashed dengan TTL, dan desired NAS belum applied. Cek subnet/route overlap termasuk shared address space100.127/16; berhenti bila bentrok, bukan mengubah jaringan host agar cocok.
2. UI menunjukkan tujuan endpoint dan diff semua objek. Validasi token dan HTTPS server dengan hostname/CA/waktu benar sebelum langkah privileged. Token pada body/kanal rahasia, bukan URL/log/analytics. Skrip bersifat sensitif selama token masih berlaku.
3. Buat/reuse hanya objek yang ownership+fingerprint cocok: interface WireGuard, peer dengan /32 server yang nyata, alamat tunnel dan route /32 server. Private key dibuat router, tidak dikirim ke platform. Jika ada endpoint RADIUS kedua, /32/rute/key-nya baru ditambahkan setelah benar-benar tersedia.
4. Native API-SSL default; sertifikat dipin dari complete enrollment terautentikasi. Jangan menimpa certificate/address pada layanan api-ssl global existing tanpa diff yang ditinjau dan recovery. Jangan mematikan verifikasi TLS. REST HTTPS alternatif default off.
5. Custom group/account baca terpisah dari akun mutasi mode manage. Policy minimum dibuktikan dengan command allow/deny lab; grup bawaan read tidak diasumsikan aman. Password CSPRNG: generator router hanya bila terbukti aman pada build tersebut; alternatif injeksi secret CSPRNG melalui kanal rahasia yang sah. Jangan menaruh secret literal dalam skrip tersimpan.
6. Aturan input tambahan API-SSL dan UDP3799 hanya server /32 pada interface manajemen; urutan terhadap existing drop diverifikasi. Tidak membuka API publik. Host nftables memblokir peer→peer/DB/SSH/metrics/metadata/container; peer hanya RADIUS1812/1813 dan receiver. Server→peer hanya API dan Disconnect sesuai scope. IPv6 diblokir kecuali diizinkan+diuji.
7. Complete consume token+store peer/credential references+audit/outbox atomik; host provisioning lewat reconciler. Replay dengan nonce/router key sama mengembalikan logical enrollment tanpa mengulang secret; identitas berbeda ditolak409. Ulang skrip tidak menggandakan peer/user. Revoke token/peer/API/NAS empat state berbeda.
8. Health dipisah: tunnel_seen, API TLS, auth, permission, compatible, discovery_ready. Tunnel aktif saja bukan router siap. Upgrade read_only→manage skrip pendek bertoken baru, tidak memberi izin perubahan layanan lain.

Gate T01/T10/T19: NAT/CGNAT, UDP tertutup, MTU, overlap, reload firewall, reboot, replay/expiry, pin mismatch, policy kurang, dua tenant dengan LAN sama, IPv6 dan default route unchanged. Client credential tidak keluar ke browser umum.

## 3 Discovery, migrasi dan drift

Discovery bounded hanya properti minimum PPP secret/profile/active, PPPoE server, Hotspot user/profile/server/active, pool, interface/IP, queue, FastTrack, RADIUS/AAA, script/scheduler sebagai data. **Tidak membaca password** dan tidak menjalankan komentar/on-login/script. Hanya service pppoe atau any yang dapat diadopsi; any direview per objek; l2tp/sstp/ovpn dan admin router tetap unmanaged. Sesi aktif bukan directory akun dan tidak dapat merekonstruksi RADIUS eksternal.

Snapshot menyimpan timestamp, adapter/version, fingerprint dan revision. Wizard delapan langkah serta S1–S4 mengikuti RADIUS. Commit hanya DB/proyeksi, tidak membuat user/comment/profile/firewall di router. Unknown credential tidak menghasilkan auth aktif. FastTrack dapat melewati queue; capability warning terlihat ketika memetakan paket.

S1 akun panen sementara operasi privileged terpisah: maksimum24 jam, expiry absolut+startup cleanup, clock sehat, cleanup dipastikan sebelum akun dibuat. Policy sensitive hanya jika dibutuhkan lab. Rate/batch menurut defaults; setelah panen hapus+readback, failure cleanup blocker keamanan spesifik. Startup-only timer tidak cukup. S2 CSV/S4 export RADIUS tidak mengubah router; S3 password baru memerlukan rencana update CPE.

Drift scan menurut defaults, juga on-demand dan preflight tiap write: missing_source, needs_review, hold_unknown, local_account_shadow, binding_invalid, radius_client_missing. Shared config manual berubah→revision_conflict/degraded, bukan auto overwrite. Router restore yang mengubah.id tidak mengalihkan invoice/customer ke akun lain. TechnicalProfile observed tidak otomatis menjadi paket harga.

## 4 Adapter dan mutasi

Interface kecil: discover_capabilities, list_accounts, read_object, plan_action, apply_action, verify_action, create_backup, read_health; domain cutover install_radius_client/set_aaa/resolve_local_shadow/rollback_radius; dispatcher Disconnect. Semua menerima konteks router terdaftar, bukan command/URL bebas.

Normalisasi string RouterOS→tipe divalidasi. Bounded connect/read/max response/deadline dan cancel/fencing mengikuti ARCHITECTURE §6. Mutasi hanya dispatcher; preflight permission/mode/capability/revision/ownership. Timeout setelah kirim→uncertain, readback, lalu retry hanya bila terbukti belum diterapkan. Backup/recovery sebelum shared change. Jangan menganggap Safe Mode sebagai transaksi API.

Kecepatan paket ke Mikrotik-Rate-Limit: rx upload dari pelanggan, tx download ke pelanggan. Profile router memuat pool/alamat lokal/DNS/MSS, bukan harga. Binding menyimpan profile hash; account tidak terikat fisik router. Perubahan profile fisik/clone R4 memakai impact terhadap managed+unmanaged, blok perubahan yang menyentuh unmanaged; default profile baru.

## 5 Backup router

Kategori routine100/manual10/prechange10 adalah generasi berhasil per router. Binary terenkripsi dengan password per router CSPRNG, key_ref/version terenkripsi di platform. Export tanpa show-sensitive default; pilihan sensitive perlu Owner step-up. Binary/export memiliki cakupan pemulihan berbeda dan kompatibilitas restore dibuktikan lab.

Alur: create exact files milik generation→SFTP push RouterOS Fetch melalui VPN ke receiver tanpa shell dengan credential/path scoped→staging→source size + protocol completion + hash + enkripsi + durable storage→commit katalog→ubah retained membership→prune async→cleanup exact files milik generation. API membuat file, tidak memindahkan binary sebagai satu response API.

Fetch SFTP host verification memakai pin bila capability tersedia. Versi tanpa dukungan pin memerlukan kontrol kompensasi WireGuard+/32 dan catatan risiko/spike TK-505; jangan menyebutnya SSH host-key verification. Pull fallback hanya jika akses SFTP/SCP+host pin tersedia dan diuji, bukan dianggap tersedia dari akun API. Tidak boleh ignore host verification diam-diam.

Max artifact64 MiB default. Hash server saja tidak membuktikan file sumber lengkap; cocokkan size/readback sumber dan close transfer terautentikasi, checksum sumber bila tersedia, restore sampel. Staging headroom dan disk warn/stop mengikuti defaults; gagal transfer tidak menghapus backup valid. Generasi101 mengeluarkan tertua setelah seluruh artifact wajib generasi baru committed. Prune/delete retry idempoten; membership katalog berbeda dari blob yang belum terhapus. Jangan menghapus backup valid untuk memberi ruang. Kunci lama tetap tersedia untuk generasi lama sesudah rotasi.

Download gateway memeriksa tenant/permission saat issue+redeem, TTL300 detik, audit; kunci pemulihan Owner+MFA+reauth. Restore berisiko terpisah dan model/versi disahkan, bukan tombol rutin. Tidak memakai restore binary/reset/reboot sebagai kompensasi cutover umum. T08/T09/T17.

## 6 Monitoring

Health/traffic60 detik, inventory900 detik, detail15 detik hanya halaman aktif dengan shared cache/budget; semua angka dari defaults. Jitter/backoff dan kuota polling per router/tenant. Setiap sample source,observed_at,collected_at,unit,quality. Counter delta monotonic memperhitungkan reboot/wrap/interface berubah; missing sample gap, bukan nol. Jangan menjumlah WAN+LAN dua kali.

Status koneksi layanan dari accounting RADIUS; collector gagal menjadi insiden platform/data unavailable, bukan semua router down. Stale health>3×interval; accounting memakai rumus tersendiri. Prometheus tanpa label username/telepon/invoice; raw15 hari, agregat5 menit/1 jam dipersistenkan PostgreSQL90/400 hari. Recording rule pada TSDB15 hari tidak menyediakan history400 hari.

WAN probes hanya pada route ISP target; minimum2target independen, down setelah3siklus semua gagal, up setelah5siklus minimal satu sukses. Uji jalur aktual; health server→router bukan pengalaman internet pelanggan. SNMPv3 baca opsional; torch/packet capture/speedtest saturasi bukan polling default.

## 7 R4 jaringan lanjutan

PRODUCT §20 memiliki keputusan WAN/CFG. Wizard Jaringan Pelanggan terpisah dari Uplink. Existing topology tetap default. Static butuh interface+IP/prefix+gateway; DHCP membaca lease/gateway. Overlap modem, gateway identik antar-uplink, PPPoE WAN/VRF/VLAN hanya didukung setelah template spesifik diuji.

Single, recursive failover dan weighted PCC diuji per topology; PCC distribusi koneksi, bukan bonding sesi. **Hotspot+PCC pada satu router diblokir.** Hotspot single/failover main table perlu lab login/walled garden/return/failover. Template mengecualikan traffic local/VPN/RADIUS, menjaga NAT/DNAT/mark/return/queue dan hanya objek miliknya; tidak mengubah FastTrack massal.

ChangePlan immutable memuat baseline/revision, template, diff, impact, ownership, backup, expiry/window, health checks dan recovery. Terapkan checkpoint/readback bertahap; recovery hook lokal hanya setelah lab. Koneksi hilang→uncertain/recovery_required. Tidak global reset/flush conntrack/reboot atau hardcode rollback. T13 sebelum pilot topology; adapter OLT hanya model/firmware/protokol berfixture dan lab, bukan dukungan universal.
