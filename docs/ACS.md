# MicroTix — ACS dan TR-069

R3, ACS-01–ACS-10. Tidak menjadi dependency R1/R2. Model/firmware nyata diperlukan untuk verified_lab model tersebut; kode adapter dan simulator dapat dibuat lebih dahulu.

## 1 Ruang lingkup dan batas

Platform mengelola CPE pelanggan (ONT/ONU, router Wi-Fi, modem) melalui TR-069 menggunakan **GenieACS** sebagai mesin CWMP, dengan adapter internal yang menegakkan tenant, izin, dan keamanan. Tidak semua CPE mendukung TR-069; tidak semua parameter writable; model data dan ekstensi vendor berbeda. Platform tidak menjamin dukungan berdasarkan merek. ACS tidak menggantikan provisioning OLT (registrasi ONU, service-port, profil GPON/EPON) dan tidak menggantikan RADIUS (autentikasi layanan).

## 2 Arsitektur (ACS-01)

| Komponen | Port/akses | Keputusan |
|---|---|---|
| GenieACS CWMP | Publik HTTPS 443 pada hostname ACS; CWMP internal 7547 | HTTP reverse proxy; port publik lain hanya jika manifest eksplisit mengizinkan, menurut bagian ini. |
| GenieACS NBI | 7557, internal | Private bind/firewall dan service-auth proxy/mTLS bila lintas proses/host; jangan mengasumsikan autentikasi bawaan. |
| GenieACS FS | 7567 | Internal; berkas firmware/konfigurasi disajikan ke CPE melalui URL bertoken |
| GenieACS UI | 3000 | Tidak diaktifkan untuk tenant; akses operator platform saja melalui jalur admin |
| MongoDB | 27017 | Internal; versi sesuai dukungan GenieACS yang dipin; backup bersama off-host |
| Adapter ACS | internal | Satu-satunya jalan tenant ke data ACS; memetakan Device internal ↔ DeviceID |

Satu instance GenieACS melayani banyak tenant; **isolasi dilakukan oleh adapter**, bukan oleh tag GenieACS (tag hanya metadata). Skala: sesi CWMP ~222/detik rata-rata pada skenario 200.000 CPE inform 900 detik; sizing dan sharding (beberapa instance per kelompok tenant) ditetapkan dari benchmark G4.

## 3 Menghubungkan CPE ke ACS (ACS-02)

CPE harus tahu URL ACS dan memiliki jalur IP ke ACS. Jalur yang didukung (per model, dibuktikan lab):

1. **Konfigurasi manual/ACS URL awal** oleh teknisi (halaman web CPE) — jalur dasar.
2. **DHCP option 43 / vendor class** (TR-111 / DHCP vendor-specific information) dari server DHCP pada jaringan pelanggan — memerlukan konfigurasi operator; platform hanya menyediakan nilai.
3. **Provisioning OLT/OMCI** (ME *TR-069 management server*) bila OLT mendukung — di luar kendali platform; dicatat sebagai prasyarat model.
4. **WAN manajemen terpisah (VLAN/IP)** untuk ONT — dirancang operator; platform tidak membuatnya diam-diam. Jalur PPPoE layanan dapat dipakai bila ACS dapat dijangkau melalui internet, dengan konsekuensi isolir (bagian 8).

VPN router tidak mendaftarkan ONT otomatis. CPE di belakang NAT tidak diasumsikan reachable untuk Connection Request HTTP; mapping/reachability harus terbukti. Jika tidak, gunakan **UDP Connection Request/STUN (TR-069 Annex G)** bila CPE mendukung, atau tugas menunggu **Periodic Inform** (default interval inform 900 detik; konfigurasi per kelompok model). Tugas berstatus `waiting_inform` sampai CPE terhubung.

## 4 Autentikasi dan kepemilikan (ACS-03)

- **CPE → ACS**: HTTPS; HTTP Digest (atau Basic di atas TLS) dengan **kredensial unik per perangkat** (`ManagementServer.Username/Password`). Mode *accept-any* dilarang. Kredensial dibangkitkan platform saat klaim enrollment dan diterapkan melalui provisioning awal; kredensial pabrik bersama tidak boleh meluluskan ownership claim; provisioning awal memasang credential unik atau memakai bootstrap terisolasi yang terotorisasi.
- **Klaim enrollment**: teknisi/Owner mendaftarkan perangkat dengan serial + OUI + product class + secret sekali pakai (label/QR). ACS menerima Inform pertama dari DeviceID yang cocok dengan klaim, mengaitkan perangkat ke tenant, memutar kredensial, lalu mengeluarkannya dari karantina. Konflik serial/DeviceID antar-tenant ditahan; tenant tidak dapat mengklaim serial milik tenant lain.
- **Penandaan tenant**: setelah klaim valid, skrip provisioning GenieACS menandai perangkat dengan `tenant:<id>` hanya sebagai metadata pencarian; keputusan otorisasi selalu dari database platform.
- **ACS → CPE (Connection Request)**: kredensial connection request unik per perangkat.
- **Skrip/preset**: dikelola platform; tenant tidak mengirim JavaScript atau preset mentah.

## 5 Model data dan pemetaan parameter (ACS-04)

CPE memakai **TR-098** (`InternetGatewayDevice.`) atau **TR-181** (`Device.`). Adapter menyediakan *virtual parameter* GenieACS sebagai lapisan abstraksi sehingga UI/API platform tidak bergantung pada root data model.

| Fungsi | Contoh jalur TR-098 | Contoh jalur TR-181 | Catatan |
|---|---|---|---|
| Identitas | `InternetGatewayDevice.DeviceInfo.{parameter}` | `Device.DeviceInfo.*` | Dibaca saat Inform pertama |
| Wi-Fi SSID | `InternetGatewayDevice.LANDevice.{j}.WLANConfiguration.{i}.SSID` | `Device.WiFi.SSID.{i}.SSID` | Indeks instance ditemukan lewat discovery, tidak di-hardcode |
| Wi-Fi password | `InternetGatewayDevice.LANDevice.{j}.WLANConfiguration.{i}.PreSharedKey.{k}.KeyPassphrase` | `Device.WiFi.AccessPoint.{i}.Security.KeyPassphrase` | Disimpan terenkripsi; tampil sesaat sesuai izin |
| Kanal Wi-Fi | `InternetGatewayDevice.LANDevice.{j}.WLANConfiguration.{i}.Channel` | `Device.WiFi.Radio.{i}.Channel` | |
| WAN PPPoE | `InternetGatewayDevice.WANDevice.{i}.WANConnectionDevice.{j}.WANPPPConnection.{k}.{Username|Password}` | `Device.PPP.Interface.{i}.Username/Password` | Sinkron dengan RADIUS (bagian 8) |
| Perangkat terhubung | `InternetGatewayDevice.LANDevice.{i}.Hosts.Host.{n}` | `Device.Hosts.Host.{n}` | Dibatasi; PII |
| Statistik | Path penuh `InternetGatewayDevice.` ditetapkan mapping model | Path penuh `Device.` ditetapkan mapping model | Delta/reset; belum ada path model yang disahkan → capability BLOCKED |
| Diagnostik | `InternetGatewayDevice.IPPingDiagnostics`, `InternetGatewayDevice.DownloadDiagnostics` (TR-143) | `Device.IP.Diagnostics.*` | Terbatas, tidak menjenuhkan ISP |
| Optik | Ekstensi vendor (`X_<VENDOR>_…`) atau profil GPON TR-156/TR-281 bila ada | idem | Tidak tersedia = "Tidak didukung", bukan 0 dBm |

Placeholder `{...}`, alternatif dan wildcard dalam tabel bukan path RPC literal. Mapping model harus mengekspansi ke path penuh yang ditemukan dan teruji; relasi Radio/SSID/AccessPoint ditelusuri lewat reference, bukan kesamaan nomor instance.

Setiap model memiliki **berkas pemetaan** versi (JSON/YAML) yang menyatakan root data model, jalur fungsi, tipe, writable, validasi nilai (panjang SSID, aturan password WPA2/3), dan *capability flags*: `read_identity`, `wifi_read`, `wifi_write`, `associated_devices`, `wan_ppp_write`, `diagnostics`, `reboot`, `firmware_download`, `optical_read`, `factory_reset`, `connection_request_udp`. Model di luar matriks berstatus `unsupported_capability`. Firmware di luar daftar yang diizinkan ditolak untuk tugas tulis.

## 6 Tugas dan siklus hidup (ACS-05)

`queued → waiting_inform → running → verifying → succeeded / failed / expired / cancelled`. Operasi RPC yang dipakai: `GetParameterValues`, `SetParameterValues`, `GetParameterNames`, `AddObject`, `DeleteObject`, `Reboot`, `Download` (firmware/konfigurasi), `Upload` (log/konfigurasi), `FactoryReset` (izin khusus), `GetRPCMethods`. Aturan:

- API NBI menerima tugas ≠ perangkat melaksanakan; status berasal dari hasil CPE dan pembacaan ulang.
- ID tugas disimpan sebelum retry; sebelum mengirim ulang, baca status/nilai aktual; timeout tidak membuat tugas duplikat.
- `SetParameterValues` diverifikasi menurut capability model: readback hanya parameter readable; secret write-only memakai RPC/config revision dan functional reconnect, tanpa menuntut plaintext. Simpan status respons 0/1 serta outcome yang relevan.
- TTL default 24 jam: cabut task tertunda milik run dan buktikan tidak dapat dieksekusi kemudian sebelum `expired` dinyatakan selesai. Respons submit hilang → uncertain dan korelasi/readback sebelum retry; recovery gagal → recovery_required.
- Firmware dan reboot dijadwalkan di luar jam sibuk, memutus layanan, dan memerlukan konfirmasi dampak; factory reset bukan tombol rutin.
- Batas laju per tenant dan per perangkat; antrean tugas tidak memblokir job pembayaran/pemulihan.

Status task perangkat dan job platform tersimpan terpisah. waiting_inform→job waiting_dependency setelah submission terkonfirmasi; running→executing; verifying→verifying. Task succeeded baru memberi job succeeded setelah verifier sesuai capability lulus. Task failed dengan efek tidak jelas→job uncertain/recovery_required. Task disappeared bukan sukses. Task cancelled/expired hanya memetakan job cancelled jika tidak ada efek dan pending task milik run sudah dicabut, sesuai ARCHITECTURE §6. UI mendahulukan uncertain/recovery_required di atas status task yang usang.

## 7 Peristiwa Inform dan penyimpanan status

Peristiwa yang diproses: `0 BOOTSTRAP`, `1 BOOT`, `2 PERIODIC`, `4 VALUE CHANGE`, `6 CONNECTION REQUEST`, `7 TRANSFER COMPLETE`, `M Reboot`, `M Download`. Platform menyimpan `last_inform_at`, versi firmware, alamat IP WAN, dan hasil tugas; tidak menyimpan seluruh pohon parameter. Perangkat tanpa Inform > 3× interval ditandai `stale`; **tidak** menjadi insiden "internet pelanggan mati" tanpa bukti lain.

## 8 Sinkronisasi dengan RADIUS dan layanan (ACS-06)

Kredensial bersumber dari access_account. Rotasi otomatis memerlukan jalur manajemen independen; simpan pending+old credential version, kirim Set CPE, verifikasi RPC/config revision, update RADIUS, uji PPP login baru melalui NAS, lalu commit rotation. Secret write-only tidak diverifikasi dengan menuntut readback plaintext. Timeout dapat berarti perubahan sudah diterapkan; reconciliasi sebelum resend dan gunakan old version hanya untuk sisi yang terbukti berubah. Recovery gagal menghasilkan recovery_required. Jika tidak ada jalur manajemen independen, automated rotation ditahan kecuali recovery lokal atau overlap dual-credential per protokol telah diuji dan diotorisasi. Kegagalan respons CPE tidak membuktikan perubahan belum diterapkan. Jika ACS berbagi PPPoE tanpa recovery teruji, rotasi otomatis BLOCKED.
- Isolir via Reject dapat memutus jalur ACS bila ACS dicapai melalui koneksi PPPoE yang sama; platform memperingatkan dan menyarankan WAN manajemen atau pengecualian operator. Walled garden/VLAN manajemen ONT tidak ditambahkan otomatis.
- Perubahan Wi-Fi menjelaskan risiko perangkat pengguna terputus.

## 9 Relasi dengan OLT dan inventaris (ACS-07)

Inventaris ONU/CPE (serial, vendor, model, status stock/assigned/repair/retired) terhubung ke Service dan ODP/port. Adapter OLT (R4, per model/protokol: SNMP, SSH/CLI, API vendor) menyediakan: daftar ONU, status online, daya optik (Rx/Tx), autofind, registrasi ONU, profil layanan. Adapter OLT hanya setelah matriks model/versi/firmware disahkan, dengan fixture dan parser berversi; platform tidak mengklaim dukungan universal. Sebelum itu OLT/ODP adalah inventaris manual.

## 10 Keamanan (ACS-08)

NBI, MongoDB, dan UI GenieACS tidak terekspos ke tenant atau internet. TLS wajib pada CWMP. Skrip provisioning ditinjau dan diberi versi. Kredensial CPE/ACS tidak muncul di log, audit plaintext, atau tabel. Rate limit CWMP per sumber dan deteksi reconnect storm. Tag tidak dipakai sebagai batas keamanan. Backup datastore ACS ikut recovery plan.

## 11 Matriks kompatibilitas (ACS-09)

Setiap model memiliki baris: vendor, model, product class, firmware yang diuji, data model (TR-098/181), flag capability (bagian 5), jalur ACS URL (bagian 3), dukungan connection request (langsung/UDP), parameter optik, hasil uji per RPC, tanggal, penguji. Hanya model berstatus `verified_lab` yang memunculkan fitur pada UI.

## 12 Pengujian (ACS-10)

T11: tugas pending bukan sukses; konflik serial/DeviceID antar-tenant; klaim salah tidak memperoleh kredensial; perangkat tanpa parameter optik → "Tidak didukung"; firmware/model salah ditolak; kegagalan auth CPE tidak menerima kredensial layanan; CPE di belakang NAT dengan dan tanpa UDP connection request; rotasi password PPPoE terkoordinasi dengan kegagalan di tengah; reconnect storm.
