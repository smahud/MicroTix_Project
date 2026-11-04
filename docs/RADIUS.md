# MicroTix — RADIUS dan migrasi pelanggan

Sumber tunggal RAD-01–RAD-14, cutover B0–B6 dan bukti suspend/restore. [PRODUCT.md](PRODUCT.md) memiliki kebijakan billing; [ARCHITECTURE.md](ARCHITECTURE.md) memiliki DB/API/job.

## 1 Prinsip

1. **RADIUS adalah database pengguna (AAA) untuk seluruh akun PPPoE dan Hotspot** yang dikelola platform. Satu perusahaan (tenant) memiliki **satu basis identitas akses**; seluruh router milik tenant memakainya bersama.
2. Pelanggan tidak terikat pada router. Memindahkan pelanggan ke router lain, atau mengganti perangkat router, **tidak memerlukan input ulang** data pengguna selama router berada pada tenant yang sama.
3. Aplikasi (PostgreSQL, tabel `access_account`) adalah sumber kebenaran; tabel RADIUS (`radius.*`) adalah proyeksi yang ditulis hanya oleh service layer dalam **transaksi database yang sama**.
4. Adopsi dan migrasi data bersifat database-only. Mengubah konfigurasi router agar memakai RADIUS adalah operasi **cutover** terpisah, eksplisit, per router, dengan backup, canary, dan rollback.
5. Penegakan isolir, kecepatan, pool, dan batas sesi dilakukan melalui atribut RADIUS dan pesan Disconnect/CoA, bukan dengan mengubah akun lokal router.
6. RADIUS tidak membuka akses ke router; ia hanya menjawab permintaan autentikasi/akuntansi dari router terdaftar melalui tunnel WireGuard.

## 2 Komponen dan topologi (RAD-01)

FreeRADIUS seri 3.2 pada patch terpilih yang masih memenuhi mitigasi keamanan, rlm_sql PostgreSQL, bind hanya tunnel UDP1812/1813. Satu NAS/router dengan alamat sumber tunnel unik dan secret CSPRNG unik. Skema radius adalah proyeksi AccessAccount, bukan sumber bisnis kedua. Dispatcher mengirim RFC5176 Disconnect ke port3799 yang dikonfigurasi eksplisit; CoA hanya capability per build/fitur teruji.

Enrollment membuat desired NAS revision. SQL read_clients tidak menjamin klien langsung terpasang/hilang/berotasi pada daemon hidup. Reconciler trusted menghasilkan konfigurasi, memvalidasinya dengan tool versi terpin, lalu menerapkan restart/reload yang didukung dan diuji. Tulis applied_revision setelah probe membuktikan secret baru diterima dan lama ditolak di semua instance. Jika perlu restart, pertahankan instance lain atau jendela lab/pilot yang sesuai; jangan mengarang hot reload.

Dua instance satu host hanya redundansi proses. Host HA memerlukan failure domain jaringan/host/database yang independen dan bukti G4; endpoint sekunder hanya dipasang jika alamat, route, secret dan daemon benar-benar ada. Ini bukan prasyarat membuat kode R1.

## 3 Model data (RAD-02)

```text
access_account            (sumber kebenaran, tenant-scoped)
  id uuid PK, tenant_id, service_id (FK Service), username text NOT NULL,
  kind (pppoe | hotspot), state (active | suspended | disabled | expired),
  secret_ref (rujukan rahasia terenkripsi), credential_state (unknown | ready | rotation_pending),
  simultaneous_use int DEFAULT 1,
  mac_lock text NULL, static_ip inet NULL, static_ip_by_router jsonb NULL,  -- override IP statis per router
  allowed_router_ids uuid[] NULL,                                          -- NULL = semua router tenant
  valid_from date, valid_until date NULL, revision int
  UNIQUE (tenant_id, username)                                              -- satu namespace per tenant, case-sensitive
access_account_source     (jejak migrasi: router_id, namespace, external_handle, fingerprint, imported_at)
radius.nas                (tenant_id, router_id, nasname, shortname, secret, type='other')
radius.radcheck           (tenant_id, id, account_id, username, attribute, scope, ordinal, op, value)
radius.radreply           (tenant_id, id, account_id, username, attribute, scope, ordinal, op, value)
radius.radgroupreply      (tenant_id, id, groupname, attribute, op, value, router_id NULL)
radius.radusergroup       (tenant_id, username, groupname, priority)
radius.radacct            (skema FreeRADIUS standar + tenant_id, router_id, service_id; dipartisi bulanan)
radius.radpostauth        (tenant_id, username, reply, authdate, nas_ip)
```

`(tenant_id, username)` unik pada `access_account`; satu akun mempunyai banyak baris atribut pada `radcheck`. Uniqueness atribut dan resolver mengikuti §3–§5; username dibandingkan **persis** (case-sensitive; spasi tepi dilarang; maks. 64 karakter dan 64 byte UTF-8; karakter kontrol dilarang). Username berbeda hanya huruf besar/kecil memicu peringatan duplikat dan tidak digabung otomatis. Tabel `radius.*` memakai RLS yang sama untuk akses aplikasi; role FreeRADIUS hanya membaca melalui kueri yang memfilter tenant (bagian 4).

## 4 Penentuan tenant per permintaan (RAD-03)

Urutan trust: peer WireGuard terdaftar → source NAS /32 unik → client/secret dan authenticator tervalidasi → router aktif dengan applied revision → tenant → query scoped. User-Name, realm, NAS-IP-Address dan identifier yang dibawa paket tidak berwenang memilih tenant. Metadata Client-Shortname dari konfigurasi daemon sendiri bukan input publik; jangan menerima nilai bernama sama dari payload sebagai otoritas.

Role RADIUS hanya EXECUTE facade authorize/accounting/postauth/session yang dibatasi, bukan broad SELECT/DML lintas tenant. Bootstrap lookup hanya metadata minimum untuk loader client tepercaya. Satu pemanggilan fungsi mengikat NAS terverifikasi, menetapkan konteks transaction-local dan menjalankan query pada transaksi/koneksi sama; tidak SET tenant terpisah pada pool. Owner fungsi non-BYPASSRLS/non-owner tabel, trusted search_path, PUBLIC EXECUTE dicabut. Aplikasi biasa tidak boleh memanggil facade dengan klaim verified NAS arbitrary. Daemon RADIUS adalah bagian trusted computing base; desain ini tidak melindungi dari daemon yang sepenuhnya kompromi.

Projection writer aplikasi scoped tenant menulis AccessAccount + atribut atomik. Attribute row unik (tenant,account,attribute,scope,ordinal); satu account mempunyai banyak check/reply. Cache memasukkan tenant+NAS+account+policy/credential/client revision. Suspend/revoke/rotation invalidasi semua instance; tidak selesai bila instance lama belum diperiksa.

Unknown NAS/Message-Authenticator Access-Request hilang atau invalid tidak boleh menghasilkan Accept; secure discard sah. Accounting Request Authenticator dan response authenticator juga divalidasi sesuai protokol. Semua authorize/reply/group/accounting/postauth/admission/usage/Disconnect memakai konteks tenant/NAS yang sama. Satu wrong Accept atau satu kebocoran tenant adalah kegagalan kritis, tanpa toleransi persentase.

## 5 Resolver atribut (RAD-04)

| Jenis | Atribut/aturan |
|---|---|
| Kontrol internal server | Cleartext-Password; Auth-Type Reject untuk suspend; Simultaneous-Use; Expiration; Max-All-Session hanya bila modul counter terbukti |
| Reply NAS | Mikrotik-Rate-Limit; Framed-Pool atau Framed-IP-Address; Acct-Interim-Interval; Session-Timeout; Idle-Timeout; atribut vendor sesuai dictionary terpin |
| Kecepatan | rx = upload dari pelanggan, tx = download ke pelanggan; integer bit/s, burst dari paket tervalidasi |
| Pool/IP | Override router → static_ip jika valid subnet → pool hanya saat static_ip null; nilai invalid ditolak, tidak fallback diam-diam |
| Expiry | valid_until eksklusif pada midnight timezone bisnis, konversi UTC; Session-Timeout tidak melewatinya |
| Precedence | Override router > paket > tenant; tepat satu nilai efektif atribut single-value; jangan bergantung urutan UNION SQL |
| Eligibility | Kind sesuai service PPPoE/Hotspot, account state/credential ready, valid_from/until, allowed routers, binding, MAC dan hold harus lulus |

Cleartext-Password, Simultaneous-Use, Expiration dan Auth-Type bukan reply universal yang dikirim ke router. Modul server mengevaluasi kontrol itu; counter byte/waktu kumulatif memerlukan accounting, tidak cukup baris radreply. Service kind ditentukan dari atribut layanan NAS yang terverifikasi dan binding: PPP/Framed-Protocol untuk PPPoE, jalur Hotspot yang teruji untuk Hotspot; atribut ambigu ditolak, tidak menebak dari nama pengguna. PAP/CHAP/MS-CHAPv2 diuji pada PPPoE sesuai capability; Hotspot diuji metode login yang benar-benar didukung (http-chap/PAP/MAC/cookie), tidak diwajibkan MS-CHAPv2 pada seluruh mode.

## 6 Kredensial (RAD-05)

1. Password layanan disimpan **terenkripsi** pada `secret_ref` (kunci data per tenant, dibungkus kunci utama di luar database); proyeksi `radcheck` memuat `Cleartext-Password` karena kompatibilitas CHAP memerlukan known cleartext; baseline yang sama melayani PAP/MS-CHAPv2 tanpa menyatakan semua metode selalu memerlukan plaintext. Risiko ini dikendalikan: role `radius_ro` terbatas pada host gateway; koneksi database dari proses `radius` hanya lewat soket lokal/loopback; backup terenkripsi; kolom tidak pernah muncul di log, export, audit, atau error.
2. Penampilan password mengikuti kebijakan kredensial layanan (PRD CUS-01): permission `services.reveal_credentials`, reautentikasi, audit, auto-sembunyi 30 detik.
3. Rotasi password adalah aksi terpisah: ubah `secret_ref` + `radcheck` dalam satu transaksi; bila CPE menyimpan kredensial PPPoE (ACS), koordinasikan sesuai `ACS.md` §8.
4. Secret RADIUS per router (`radius.nas.secret`) dibangkitkan platform (32 karakter acak), dikirim ke router melalui skrip cutover, dirotasi saat penggantian router; tidak digunakan ulang antarrouter.
5. Server mewajibkan `Message-Authenticator` pada Access-Request (mitigasi BlastRADIUS); lalu lintas hanya di dalam tunnel WireGuard.

## 7 Penegakan dan aktivasi (RAD-06)

Suspend: worker mengunci service, recheck pembayaran seluruh outstanding terkait, policy_version, grace/exemption, hold, termination dan revision. Simulasi policy harus belum melampaui TTL dan hash policy/data/scope tetap cocok; revisi berubah membuat simulasi stale. Grace selesai pada midnight lokal setelah due_date+grace_days; scheduler 01:00 hanya menghasilkan kandidat yang sudah melewati batas.

Commit Account suspended + Reject projection + audit/outbox atomik; Disconnect setiap sesi target di semua NAS adalah efek eksternal terpisah. Bukti suspend wajib lengkap: (1) policy revision Reject dan auth transport sah ditolak karena policy target, bukan secret/NAS salah; (2) Disconnect ACK tiap sesi diketahui atau bukti positif sesi tak ada; (3) Acct-Stop/readback NAS membuktikan sesi target tidak aktif; (4) recheck sesudah60 detik tanpa sesi baru dan kontrol non-target tetap sesuai baseline. Tanpa bukti positif, unknown/uncertain; absennya interim60 detik bukan bukti putus pada interval300 detik. Jangan mengklaim verifikasi sesi di NAS tanpa berinteraksi dengan NAS/accounting.

Restore hanya tindakan manual aktor services.activate. Recheck hold/binding/paid eligibility, commit atribut normal terkini dan verify auth Accept dengan reply sesuai NAS. verified_active berarti kelayakan autentikasi pulih; perangkat boleh masih offline/unknown. Jangan memakai test Reject untuk restore dan jangan mengembalikan snapshot kecepatan lama jika paket berubah. Hold manual/security/technical hanya dioverride dengan izin+step-up+alasan yang menyebut hold tersebut.

Pembayaran sebelum efek Reject membatalkan kandidat isolir lama. Pembayaran setelah Reject tetap sah dan menunggu aktivasi manual; tidak otomatis memproyeksikan active. Router offline tidak membatalkan uang. Restore kelayakan di DB dapat selesai sementara bukti perangkat terkait tetap tertunda; laporkan dimensi itu terpisah.

Isolir terbatas/walled garden R3 memakai pool/aturan operator teruji; tidak mengubah firewall diam-diam, tidak menjanjikan redirect HTTPS arbitrer, IPv4-only tidak diklaim mengisolir IPv6. Perubahan kecepatan berlaku sesi berikutnya, atau CoA/Disconnect yang capability+dampaknya telah diuji dan diotorisasi.

Strict session limit: lock per tenant+account, reservasi pending auth idempoten terhadap retransmission, confirmation dari accounting. Dua NAS serentak pada limit1 menghasilkan paling banyak satu Accept yang sah. COUNT(radacct) saja tidak cukup. Auth gagal/response Accept hilang ditangani oleh hasil postauth+reconciliation; pending tidak dibiarkan permanen dan tidak dibebaskan hanya karena timer saat mungkin ada sesi aktif. Sediakan bounded check/readback NAS dan remediasi operator bila bukti hilang. Jika strict control belum terbukti, fitur belum dirilis; jangan melabeli dua login berurutan sebagai bukti race.

## 8 Accounting dan koneksi (RAD-07)

Identitas sesi mencakup tenant+router+boot/session identity, bukan username atau Acct-Session-Id global. Directory sesi unik bertahan lintas partisi bulan sehingga Interim/Stop bulan berikutnya memperbarui sesi sama. Dedup retransmission dan paket out-of-order; Stop tidak dibuka kembali oleh Start lama. Counter octet/gigaword dipadukan, wrap/reset eksplisit; delta nonnegatif dialokasikan lintas midnight timezone snapshot, koreksi late event berversi.

Fresh≤3×interim+stale_grace. Data basi→connection_state unknown; janitor tidak memalsukan Acct-Stop dari NAS dan tidak menganggap sesi pasti mati. Retensi raw90 hari/usage400 hari tidak menghapus identitas sesi aktif. Kesehatan collector router dan accounting terpisah. Pemakaian accounting/FUP bukan billing uang tanpa paket metered yang eksplisit; accounting lag/overshoot harus diukur.

## 9 Ketersediaan dan mode kegagalan (RAD-08)

Karena autentikasi bergantung pada server pusat, ketersediaan RADIUS menjadi bagian dari kontrak layanan tenant.

| Skenario | Perilaku dan mitigasi |
|---|---|
| Server platform mati atau tunnel putus | Sesi existing dapat terus berjalan selama tidak mencapai timeout/expiry/re-auth; hasil per build/topology diuji. Login baru memerlukan RADIUS yang reachable. Mitigasi: dua alamat RADIUS pada router (primer platform, sekunder = node HA atau **edge replica**), timeout 3 dtk × retry sesuai lab; peringatan insiden platform; runbook rollback lokal |
| Edge replica (opsional, R3) | Host Linux/OS FreeRADIUS, default off sampai G4. Snapshot signed/encrypted/tenant-scoped, revision monotonik dan TTL 900 detik; signature/encryption/tenant scope diverifikasi, revision lama/replay ditolak. Saat partisi, login yang membutuhkan koordinasi global strict fail closed; expiry menolak login baru, tidak memutus sesi existing semata karena expiry. Store-and-forward accounting memiliki batas disk/retry/TTL, dedup event dan alarm; konfigurasi batas konkret sebelum edge diaktifkan. |
| Rollback darurat | Hanya melalui B6 §10.2: restore snapshot/revision dan recovery export terkini, mempertahankan security/manual hold serta RADIUS pihak lain. Coverage tidak cukup → recovery_required; tidak hardcode AAA atau mengaktifkan semua akun. |
| Basis data lambat | Antrian autentikasi dibatasi; kolam koneksi SQL dan batas thread; alarm queue age |
| Kebijakan setelah pulih | Rekonsiliasi akun/atribut terbaru sebelum job isolir lama diproses; job usang dibatalkan |

## 10 Migrasi akun existing ke RADIUS (RAD-09)

### 10.1 Tahap A — Discovery dan adopsi (database-only)

Pada langkah gabung sebelum credential tersedia hanya structural_candidate, belum klaim password sama. Sesudah S1–S4 siap, bandingkan in-memory/HMAC sementara; kind, paket, identitas dan hold harus kompatibel. Perubahan klasifikasi kembali ditinjau. keep_one mengecualikan sumber lain, tidak menghapusnya. Rename membuat desired identity DB dan rencana credential/CPE terpisah, bukan rename lokal diam-diam.

Batas uptime/byte yang sudah terpakai harus dibawa sebagai consumed/remaining pada snapshot cutover jika sumber menyediakan data yang dapat dipercaya. Tanpa bukti, tandai needs_review dan tahan aktivasi akun/quota tersebut, bukan mereset limit penuh atau menebak sisa dari comment. Credential unknown adalah field credential_state, bukan account state kelima.

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

### 10.2 Tahap B — Cutover dan rollback B0–B6

Pencocokan akun lokal dapat mengalahkan RADIUS. Mengaktifkan use-radius saja tidak membuktikan canary. PPP AAA umumnya scope global; jangan mengeklaim bisa diaktifkan per satu PPPoE server tanpa capability yang membuktikannya. B0 wajib menilai dampak ke semua protokol PPP pada router, bukan hanya akun terpilih.

| Tahap | Prasyarat, aksi, dan kriteria keluar |
|---|---|
| B0 preflight | mode manage, radius.cutover+MFA+reauth, izin valid selama langkah, versi/build teruji, backup valid, jalur recovery, baseline seluruh shared setting, coverage rollback dan snapshot revision cocok; RADIUS eksternal tanpa rencana coexistence →BLOCKED |
| B1 parity | per akun ready: auth sintetis memakai NAS test terdaftar dan konteks tenant/router yang sama melalui facade uji terotorisasi; uji credential/kind/pool/rate/state; nol kegagalan dan nol binding ambigu; tes ini bukan bukti login lewat NAS produksi |
| B2 install | pasang hanya klien platform, incoming port, dan rule sempit yang direncanakan; restore baseline shared resource harus tersimpan; endpoint primer dan setiap sekunder yang dikonfigurasi beserta route /32 terjangkau; readback lulus |
| B3 canary | gunakan akun sintetis/canary yang tidak cocok akun lokal, atau metode penghilangan shadow yang sudah diuji dan diotorisasi per objek; PPP global side effect termasuk rencana; amati 1800 detik nyata; minimal 100 auth valid, keberhasilan ≥99%, nol salah Accept/atribut/tenant, Start/Interim/Stop benar, sesi kontrol existing tetap sesuai baseline |
| B4 shadow_active | enable scope penuh yang direncanakan dan observasi 86400 detik nyata; job memakai deadline kind dan grant/window yang cukup; belum selesai observasi →pending/BLOCKED, bukan dipercepat untuk gate runtime |
| B5 authoritative | batch≤100; setiap source mendapat ownership consent, fingerprint/revision cocok, tidak ada local shadow yang tersisa; uji login nyata membuktikan RADIUS; hanya lalu router ditandai authoritative |
| B6 rollback | cabang dari tahap yang telah mengubah router; restore snapshot nilai sebelum operasi, bukan hardcode use-radius=no; pulihkan hanya objek/run yang masih cocok revision; probe login+accounting, pertahankan data DB dan audit |

B5 memilih metode berdasarkan matriks lab exact: disable bila terbukti menghilangkan shadow; jika tidak, archive_rename bila terbukti menjaga sesi dan rollback; delete hanya jika secara eksplisit diotorisasi, backup memuat semua material pemulihan dan restore sudah diuji. Jika tidak ada metode sah, B5 BLOCKED; jangan menghapus otomatis karena disable gagal. Akun sumber existing tidak wajib punya prefix rtrw, tetapi harus memiliki consent ownership per-object dalam CutoverRun.

Rollback tidak boleh mengaktifkan semua user yang sebelumnya disabled, menghapus RADIUS pihak lain, mengubah global AAA seenaknya, atau menghidupkan akun yang sekarang ditahan security/manual. Backup awal hanya mencakup akun saat itu; akun baru, rename dan password yang berubah sesudah cutover memerlukan recovery export terkini. Jika coverage ini tidak lengkap, rollback lama tidak dinyatakan aman. Buat delta recovery yang diotorisasi atau tandai recovery_required. Rollback tidak menggunakan reset/reboot/restore binary rutin.

`enforcement_mode=local|radius_shadow|radius_authoritative|degraded` adalah status router, bukan status bisnis akun. Login/pindah router hanya dinyatakan terjamin dalam batas lab yang terbukti, binding lengkap dan tidak ada jalur autentikasi alternatif yang melewati policy. Tidak ada janji nol downtime universal.


### 10.3 Pemindahan pelanggan dan penggantian router (RAD-11)

- Pelanggan baru pada router mana pun dalam tenant yang berstatus `radius_authoritative` dapat login memakai kredensial yang sama; pool dan paket menyesuaikan binding router tujuan. Tidak ada input ulang.
- **Penggantian perangkat**: router baru di-enroll (lifecycle replacing), cutover sampai B5 authoritative; PPPoE server/profile/pool dibuat oleh operator atau wizard R4 dengan nama pool yang dirujuk binding. Akun tidak berubah.
- **Pembatasan opsional**: `allowed_router_ids` membatasi akun pada router tertentu (mis. wilayah). Default semua router tenant.
- Static IP: override router → static_ip bila subnet valid → pool hanya bila static_ip null. Static IP terkonfigurasi yang invalid harus ditolak; tidak diam-diam dialihkan ke pool.

## 11 Hotspot dan voucher (RAD-12)

Hotspot memakai RADIUS untuk autentikasi pengguna (login halaman, MAC-auth opsional, cookie) dan accounting. Reply dan kontrol internal dipisahkan sesuai §5; counter/expiry/simultaneous-use bukan baris reply universal. Voucher = `access_account` kind `hotspot` dengan `valid_until`/batas pemakaian; penjelasan bisnis pada PRD bagian 14. Hotspot + PCC satu router tidak didukung (PRODUCT.md §20).

## 12 Keamanan (RAD-13)

Secret per router; Message-Authenticator wajib; tidak ada listener publik; log autentikasi (`radpostauth`) memuat username dan hasil, tanpa password, retensi 30 hari; percobaan gagal beruntun memicu insiden (ambang konfigurasi) dan tidak mengunci akun pelanggan secara otomatis; kolom password dikecualikan dari semua jalur ekspor/log; kebocoran secret router ditangani dengan rotasi (runbook TK-1006).

## 13 Pengujian dan bukti (RAD-14)

Kriteria lulus kanonik T01–T24 ada pada PRD §26; tabel ini merinci domain RADIUS:

| ID | Skenario | Lulus bila |
|---|---|---|
| T16 | PAP/CHAP/MS-CHAPv2 PPPoE serta metode Hotspot sesuai capability | Akun valid diterima, salah ditolak; atribut benar |
| T17 | Cutover B0–B6 dan rollback pada RouterOS nyata/CHR | Sesi lama tidak terputus; urutan prioritas lokal/RADIUS tercatat; rollback memulihkan |
| T18 | Akun dipakai pada dua router; penggantian router; pelanggan pindah router | Login berhasil tanpa input ulang; pool sesuai router |
| T19 | Isolasi tenant RADIUS | Username sama lintas tenant; NAS tenant A tak melihat data B |
| T20 | Isolir via Reject + Disconnect; aktivasi; hold | Sesi terputus, login baru ditolak, aktivasi memulihkan hanya akun target |
| T21 | Accounting dan Simultaneous-Use | Sesi tercatat, interim basi dibersihkan, sesi kedua ditolak |
| T22 | RADIUS outage dan edge replica | Sesi existing tetap; sambungan baru sesuai perilaku yang dirancang; backlog accounting terkirim |

Skala awal yang diuji: 5.000 akun per tenant uji, 50 autentikasi/detik puncak, accounting interim 300 detik; angka aktual dicatat pada `docs/progress.md` (bagian kompatibilitas) (G4).
