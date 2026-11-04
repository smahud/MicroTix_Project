# Spesifikasi RADIUS, Identitas Akses, dan Migrasi — Platform SaaS Manajemen RT/RW Net

[REVISI MACRO 2.1-macro.1] MAC-05 memperinci verified NAS transport, transaction-local facade, accounting/postauth/cache/edge isolation dan revoke semua instance. Paket/proyeksi SQL lama yang bertentangan dengan AUD-19–21 atau MAC-05 bukan kode yang boleh disalin. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


**Versi 1.1** · 28 Oktober 2026 · Pemilik produk: Huda Choirul Anam
Riwayat: 1.0 (11 Oktober 2026) → 1.1 (28 Oktober 2026; B2 memverifikasi aturan 3799 dari enrollment, kolom `static_ip_by_router` ditambahkan — putusan DOC pada `decisions_log.md` Bagian E)
Dokumen normatif pendamping `PRD_SaaS_RTRWNet_v2_1.md` (bagian 9, 13, 14) dan `Technical_Design_RTRWNet_v2_1.md`. ID kebutuhan: RAD-01 s/d RAD-14.

## 1 Prinsip

1. **RADIUS adalah database pengguna (AAA) untuk seluruh akun PPPoE dan Hotspot** yang dikelola platform. Satu perusahaan (tenant) memiliki **satu basis identitas akses**; seluruh router milik tenant memakainya bersama.
2. Pelanggan tidak terikat pada router. Memindahkan pelanggan ke router lain, atau mengganti perangkat router, **tidak memerlukan input ulang** data pengguna selama router berada pada tenant yang sama.
3. Aplikasi (PostgreSQL, tabel `access_account`) adalah sumber kebenaran; tabel RADIUS (`radius.*`) adalah proyeksi yang ditulis hanya oleh service layer dalam **transaksi database yang sama**.
4. Adopsi dan migrasi data bersifat database-only. Mengubah konfigurasi router agar memakai RADIUS adalah operasi **cutover** terpisah, eksplisit, per router, dengan backup, canary, dan rollback.
5. Penegakan isolir, kecepatan, pool, dan batas sesi dilakukan melalui atribut RADIUS dan pesan Disconnect/CoA, bukan dengan mengubah akun lokal router.
6. RADIUS tidak membuka akses ke router; ia hanya menjawab permintaan autentikasi/akuntansi dari router terdaftar melalui tunnel WireGuard.

## 2 Komponen dan topologi (RAD-01)

| Komponen | Keputusan |
|---|---|
| Server | FreeRADIUS seri 3.2 (rilis ≥ 3.2.5 yang memuat mitigasi BlastRADIUS; versi dipin pada TK-002) dengan modul `rlm_sql` PostgreSQL; proses `radius` terpisah dengan akun OS sendiri |
| Bind | Hanya alamat tunnel server (`vpn.pool_cidr`), UDP 1812 (auth) dan 1813 (acct). Tidak ada listener pada antarmuka publik |
| Klien (NAS) | Satu baris `radius.nas` per router: `nasname` = alamat tunnel /32, `shortname` = router_id, `secret` acak 32 karakter per router, dimuat dari SQL (`read_clients = yes`). Paket dari alamat tak terdaftar dibuang |
| Disconnect/CoA | Dispatcher mengirim Disconnect-Request/CoA-Request ke router UDP 3799 melalui tunnel |
| Database | Skema `radius` pada PostgreSQL; role RADIUS EXECUTE-only pada facade transaksi AUD-20/MAC-05. Projection-writer aplikasi scoped tenant; tidak memberi direct SELECT/INSERT/UPDATE lintas tenant. |
| Kebutuhan ketersediaan | [REVISI AUD-21] Dua proses radius pada host gateway (redundansi proses, bukan host HA) pada G4; edge replica opsional (bagian 9) |

Firewall server (TD §2): peer dapat mencapai alamat tunnel server pada UDP 1812/1813 dari /32 miliknya; server dapat mencapai peer pada UDP 3799 dan port API. Selain itu default-deny.

## 3 Model data (RAD-02)

```text
access_account            (sumber kebenaran, tenant-scoped)
  id uuid PK, tenant_id, service_id (FK Service), username text NOT NULL,
  kind (pppoe | hotspot), state (active | suspended | disabled | expired),
  secret_ref (rujukan rahasia terenkripsi), simultaneous_use int DEFAULT 1,
  mac_lock text NULL, static_ip inet NULL, static_ip_by_router jsonb NULL,  -- override IP statis per router
  allowed_router_ids uuid[] NULL,                                          -- NULL = semua router tenant
  valid_from date, valid_until date NULL, revision int
  UNIQUE (tenant_id, username)                                              -- satu namespace per tenant, case-sensitive
access_account_source     (jejak migrasi: router_id, namespace, external_handle, fingerprint, imported_at)
radius.nas                (tenant_id, router_id, nasname, shortname, secret, type='other')
radius.radcheck           (tenant_id, id, username, attribute, op, value)
radius.radreply           (tenant_id, id, username, attribute, op, value)
radius.radgroupreply      (tenant_id, id, groupname, attribute, op, value, router_id NULL)
radius.radusergroup       (tenant_id, username, groupname, priority)
radius.radacct            (skema FreeRADIUS standar + tenant_id, router_id, service_id; dipartisi bulanan)
radius.radpostauth        (tenant_id, username, reply, authdate, nas_ip)
```

[REVISI AUD-19] `(tenant_id, username)` unik pada `access_account`; satu akun mempunyai banyak baris atribut pada `radcheck`. Uniqueness atribut dan resolver mengikuti kontrak v2.1 §10; username dibandingkan **persis** (case-sensitive; spasi tepi dilarang; maks. 64 karakter dan 64 byte UTF-8; karakter kontrol dilarang). Username berbeda hanya huruf besar/kecil memicu peringatan duplikat dan tidak digabung otomatis. Tabel `radius.*` memakai RLS yang sama untuk akses aplikasi; role FreeRADIUS hanya membaca melalui kueri yang memfilter tenant (bagian 4).

## 4 Penentuan tenant per permintaan (RAD-03)

[REVISI AUD-19–21] Tenant ditentukan dari klien transport NAS terverifikasi. Semua query authorize/reply/group/accounting/postauth/session memakai facade transaksi tenant-scoped sebagaimana kontrak v2.1 §10. Snippet unlang/interpolasi SQL sebelumnya dihapus karena tidak menyelesaikan RLS dan pool reuse secara aman. NAS-IP-Address payload bukan otoritas; resolver memilih satu nilai efektif per atribut. read_clients bukan live reload; required/applied revision dan rolling reconciliation wajib.

## 5 Atribut yang dikirim (RAD-04)

| Tujuan | Atribut | Sumber |
|---|---|---|
| Password | `Cleartext-Password :=` (radcheck) | `secret_ref` (bagian 6) |
| Satu sesi per akun | `Simultaneous-Use :=` 1 (bawaan; dapat dinaikkan per layanan) | `access_account.simultaneous_use` |
| Kunci MAC | `Calling-Station-Id ==` (radcheck) | `mac_lock` |
| Kecepatan | `Mikrotik-Rate-Limit` `rx/tx` (rx = unggah dari pelanggan, tx = unduh ke pelanggan; dapat memuat burst) | `CommercialPackage` |
| Pool alamat | `Framed-Pool` | `PackageRouterBinding` (per router, melalui `radgroupreply.router_id`) |
| IP statis | `Framed-IP-Address` | `static_ip` (override per router bila subnet berbeda) |
| Interim accounting | `Acct-Interim-Interval` 300 detik (konfigurasi) | tenant |
| Batas sesi/waktu | `Session-Timeout`, `Idle-Timeout`, `Mikrotik-Total-Limit`, `Max-All-Session` | paket/voucher |
| Masa berlaku | `Expiration` | `valid_until` |
| Isolir penuh | `Auth-Type := Reject` (radcheck) | `state = suspended` |
| Isolir terbatas (opsional) | `Framed-Pool` pool isolir + `Mikrotik-Address-List` | bagian 7 |
| Grup profil router | `Mikrotik-Group` (opsional) | `PackageRouterBinding` |

Arah kecepatan: antarmuka pengguna memakai "download ke pelanggan"/"upload dari pelanggan"; adapter menerjemahkan ke urutan `rx/tx` MikroTik (rx = unggah dari pelanggan). Nilai disimpan integer bit/s dan diformat saat dikirim.

## 6 Kredensial (RAD-05)

1. Password layanan disimpan **terenkripsi** pada `secret_ref` (kunci data per tenant, dibungkus kunci utama di luar database); proyeksi `radcheck` memuat `Cleartext-Password` karena protokol CHAP/MS-CHAP yang lazim pada PPPoE memerlukan nilai asli. Risiko ini dikendalikan: role `radius_ro` terbatas pada host gateway; koneksi database dari proses `radius` hanya lewat soket lokal/loopback; backup terenkripsi; kolom tidak pernah muncul di log, export, audit, atau error.
2. Penampilan password mengikuti kebijakan kredensial layanan (PRD CUS-01): permission `services.reveal_credentials`, reautentikasi, audit, auto-sembunyi 30 detik.
3. Rotasi password adalah aksi terpisah: ubah `secret_ref` + `radcheck` dalam satu transaksi; bila CPE menyimpan kredensial PPPoE (ACS), koordinasikan sesuai `Spesifikasi_ACS_TR069` §8.
4. Secret RADIUS per router (`radius.nas.secret`) dibangkitkan platform (32 karakter acak), dikirim ke router melalui skrip cutover, dirotasi saat penggantian router; tidak digunakan ulang antarrouter.
5. Server mewajibkan `Message-Authenticator` pada Access-Request (mitigasi BlastRADIUS); lalu lintas hanya di dalam tunnel WireGuard.

## 7 Penegakan: isolir, aktivasi, kecepatan (RAD-06)

- **Isolir penuh (baseline)**: `access_account.state = suspended` → proyeksi `Auth-Type := Reject` → dispatcher mengirim **Disconnect-Request** ke router yang menampung sesi aktif (`Acct-Session-Id` dari `radacct`). Verifikasi: (a) Disconnect-ACK; (b) sesi tertutup melalui Acct-Stop atau readback NAS positif; absennya interim bukan bukti putus; (c) **uji autentikasi sintetis server-side** terhadap FreeRADIUS lokal menghasilkan Access-Reject; (d) pemeriksaan ulang +60 detik tidak menunjukkan sesi baru. Bukti ini valid tanpa menyentuh router pelanggan; pengujian login ulang pada perangkat nyata tetap dilakukan di lab (T20).
- **Aktivasi**: `state = active` → proyeksi atribut normal. Sesi baru terbentuk saat perangkat pelanggan menyambung ulang; platform tidak memaksa.
- **Isolir terbatas (opsional per tenant, R3)**: akun tetap diterima dengan `Framed-Pool` pool isolir dan `Mikrotik-Address-List=isolir`; operator wajib memasang aturan firewall/NAT/redirect pada router (templat tersedia; platform tidak membuatnya diam-diam). Dual-stack diuji; IPv4-only tidak diklaim memblokir IPv6.
- **Perubahan paket** (kecepatan baru): update atribut + **CoA-Request** (bila didukung versi RouterOS) atau Disconnect agar sesi berikutnya memakai nilai baru; UI menyatakan bahwa efek bisa menunggu sambung ulang.
- **Satu sesi per akun [REVISI AUD-27]**: strict admission memerlukan lock+pending reservation dan accounting confirmation; COUNT(radacct) saja tidak cukup saat auth konkuren. Sesi unknown tidak otomatis dilepaskan; lihat kontrak§13.
- Hold keamanan/teknis/manual mengalahkan kelayakan pembayaran: akun tidak diaktifkan oleh pelunasan bila hold ada.

## 8 Akuntansi dan status koneksi (RAD-07)

Accounting-Start/Interim/Stop mengikuti AUD-26: session directory lintas partisi, dedup, counter/delta nonnegatif dan koreksi berversi. Fresh ≤3×interim+grace 60 detik; stale menjadi `unknown`, bukan Acct-Stop sintetis. Kesehatan collector berbeda dari jalur accounting. Retensi mentah 90 hari dan usage 400 hari tidak menghapus state sesi aktif. Byte pemakaian bukan dasar tagihan uang tanpa paket meter dan bukti terpisah.

## 9 Ketersediaan dan mode kegagalan (RAD-08)

Karena autentikasi bergantung pada server pusat, ketersediaan RADIUS menjadi bagian dari kontrak layanan tenant.

| Skenario | Perilaku dan mitigasi |
|---|---|
| Server platform mati atau tunnel putus | Sesi PPP/Hotspot yang sudah terbentuk tetap berjalan; sambungan baru gagal sampai RADIUS pulih. Mitigasi: dua alamat RADIUS pada router (primer platform, sekunder = node HA atau **edge replica**), timeout 3 dtk × retry sesuai lab; peringatan insiden platform; runbook rollback lokal |
| Edge replica (opsional, R3) | Host Linux/OS FreeRADIUS, default off sampai G4. Snapshot signed/encrypted/tenant-scoped, revision monotonik dan TTL 900 detik. Saat partisi, login yang membutuhkan koordinasi global strict fail closed; expiry menolak login baru, tidak memutus sesi existing semata karena expiry. Store-and-forward accounting dibatasi/dedup menurut AUD-28. |
| Rollback darurat | Hanya melalui B6 AUD-22–23: restore snapshot/revision dan recovery export terkini, mempertahankan security/manual hold serta RADIUS pihak lain. Coverage tidak cukup → recovery_required; tidak hardcode AAA atau mengaktifkan semua akun. |
| Basis data lambat | Antrian autentikasi dibatasi; kolam koneksi SQL dan batas thread; alarm queue age |
| Kebijakan setelah pulih | Rekonsiliasi akun/atribut terbaru sebelum job isolir lama diproses; job usang dibatalkan |

## 10 Migrasi akun existing ke RADIUS (RAD-09)

### 10.1 Tahap A — Discovery dan adopsi (database-only)

1. Discovery membaca PPP secret (`service` pppoe atau `any`), profile, Hotspot user, profile, server, pool, aturan FastTrack, indikator RADIUS yang sudah ada. Secret dengan `service` bukan pppoe/any (mis. l2tp, sstp, ovpn) **tidak dimigrasikan** dan tetap lokal (dilabeli `unmanaged`).
2. **Sumber password** (dipilih per router/kelompok):
   - **S1 — Baca dari router**: skrip peningkatan bertoken membuat akun sementara `rtrw-mig` berkelompok `rtrw-migrate` dengan policy `read, api, sensitive` (hanya untuk panen password), berlaku maksimal 24 jam dan terhapus oleh skrip; panen dilakukan sekali, dibatasi laju. Ini satu-satunya penulisan router pada tahap ini dan memerlukan persetujuan Owner. (Pembacaan password memerlukan policy `sensitive`; dikonfirmasi lab.)
   - **S2 — CSV** dari Owner (kolom `username,password`), divalidasi dan dienkripsi saat masuk.
   - **S3 — Password baru**: sistem membangkitkan password baru untuk akun terpilih; pelanggan/CPE harus diperbarui; hanya dengan konfirmasi eksplisit.
   - **S4 — RADIUS eksternal**: impor dari ekspor tabel FreeRADIUS (`radcheck/radreply/radusergroup`) atau CSV; tidak ada koneksi langsung ke server eksternal.
   Akun tanpa password terpulihkan ditandai `password_unknown` dan tidak diaktifkan pada RADIUS sampai diselesaikan.
3. **Penggabungan identitas lintas router**: username yang sama pada beberapa router diklasifikasi:
   - sama password **dan** profil setara → *kandidat gabung* (Owner mengonfirmasi massal);
   - password berbeda → *konflik*: pilih salah satu, atau ubah nama salah satu akun (akun baru dibuat, tidak memutus yang lama), atau tandai sebagai pelanggan berbeda yang wajib diganti username;
   - perbedaan hanya huruf besar/kecil → peringatan.
4. **Pemetaan atribut** secret/user → `access_account` + atribut: `profile` → paket/pool (PackageRouterBinding), `caller-id`/`mac-address` → `mac_lock`, `remote-address` → `static_ip`, `limit-uptime` → `Session-Timeout`/`Max-All-Session`, `limit-bytes-total` → `Mikrotik-Total-Limit`, `disabled=yes` → `state=disabled` (`hold_unknown` sampai ditinjau), komentar → catatan (data tak tepercaya).
5. **Commit adopsi**: membuat/menggabungkan `access_account`, `Service`, proyeksi `radius.*`, `access_account_source`; kuota diperiksa atomik; **router tidak diubah** dan belum ada sesi yang diautentikasi lewat RADIUS.

### 10.2 Tahap B — Cutover RADIUS per router (operasi terpisah, RAD-10)

Prasyarat: tunnel dan API sehat; backup valid terbaru; mode `manage`; akun-akun router sudah diadopsi; simulasi paritas lulus; jendela pemeliharaan ditetapkan; RouterOS v7 teruji (lab T17).

| Langkah | Isi | Bukti/penghenti |
|---|---|---|
| B0–B6 | Definisi tunggal: kontrak master §11 AUD-22–23; gunakan setiap prasyarat, aksi, waktu observasi, exit criterion dan recovery di tabel itu. | Bukti `CutoverRun` harus mengikat consent per objek, snapshot/revision, exact build dan grant/window yang cukup. Tanpa prasyarat: BLOCKED. |

`enforcement_mode` per router: `local` (belum cutover), `radius_shadow` (B2–B4), `radius_authoritative` (B5), `degraded` (klien/konfigurasi RADIUS tidak lengkap). Isolir otomatis, kecepatan berbasis paket, dan klaim "pindah router tanpa input ulang" hanya aktif pada `radius_authoritative`.

Urutan prioritas autentikasi (lokal dahulu atau RADIUS dahulu) pada versi RouterOS yang didukung dicatat dari hasil lab (T17) dan menentukan apakah B5 memakai nonaktifkan atau hapus; rancangan tidak mengandalkan asumsi tersebut.

### 10.3 Pemindahan pelanggan dan penggantian router (RAD-11)

- Pelanggan baru pada router mana pun dalam tenant yang berstatus `radius_authoritative` dapat login memakai kredensial yang sama; pool dan paket menyesuaikan binding router tujuan. Tidak ada input ulang.
- **Penggantian perangkat**: router baru di-enroll (mode `replacing`), cutover RADIUS dilakukan (B2–B4); PPPoE server/profile/pool dibuat oleh operator atau wizard R4 dengan nama pool yang dirujuk binding. Akun tidak berubah.
- **Pembatasan opsional**: `allowed_router_ids` membatasi akun pada router tertentu (mis. wilayah). Default semua router tenant.
- Static IP: override router → static_ip bila subnet valid → pool hanya bila static_ip null. Static IP terkonfigurasi yang invalid harus ditolak; tidak diam-diam dialihkan ke pool (AUD-20).

## 11 Hotspot dan voucher (RAD-12)

Hotspot memakai RADIUS untuk autentikasi pengguna (login halaman, MAC-auth opsional, cookie) dan accounting. Atribut: `Session-Timeout`, `Idle-Timeout`, `Mikrotik-Rate-Limit`, `Mikrotik-Total-Limit`, `Max-All-Session`, `Expiration`, `Mikrotik-Group`. Voucher = `access_account` kind `hotspot` dengan `valid_until`/batas pemakaian; penjelasan bisnis pada PRD bagian 14. Hotspot + PCC satu router tidak didukung (PRD §20).

## 12 Keamanan (RAD-13)

Secret per router; Message-Authenticator wajib; tidak ada listener publik; log autentikasi (`radpostauth`) memuat username dan hasil, tanpa password, retensi 30 hari; percobaan gagal beruntun memicu insiden (ambang konfigurasi) dan tidak mengunci akun pelanggan secara otomatis; kolom password dikecualikan dari semua jalur ekspor/log; kebocoran secret router ditangani dengan rotasi (runbook TK-1006).

## 13 Pengujian dan bukti (RAD-14)

Kriteria lulus kanonik T01–T24 ada pada PRD §26; tabel ini merinci domain RADIUS:

| ID | Skenario | Lulus bila |
|---|---|---|
| T16 | PAP/CHAP/MS-CHAPv2 pada PPPoE dan Hotspot lewat RADIUS | Akun valid diterima, salah ditolak; atribut benar |
| T17 | Cutover B0–B6 dan rollback pada RouterOS nyata/CHR | Sesi lama tidak terputus; urutan prioritas lokal/RADIUS tercatat; rollback memulihkan |
| T18 | Akun dipakai pada dua router; penggantian router; pelanggan pindah router | Login berhasil tanpa input ulang; pool sesuai router |
| T19 | Isolasi tenant RADIUS | Username sama lintas tenant; NAS tenant A tak melihat data B |
| T20 | Isolir via Reject + Disconnect; aktivasi; hold | Sesi terputus, login baru ditolak, aktivasi memulihkan hanya akun target |
| T21 | Accounting dan Simultaneous-Use | Sesi tercatat, interim basi dibersihkan, sesi kedua ditolak |
| T22 | RADIUS outage dan edge replica | Sesi existing tetap; sambungan baru sesuai perilaku yang dirancang; backlog accounting terkirim |

Skala awal yang diuji: 5.000 akun per tenant uji, 50 autentikasi/detik puncak, accounting interim 300 detik; angka aktual dicatat pada `docs/compatibility.md` (G4).
