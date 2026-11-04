# Technical Design — Platform SaaS Manajemen RT/RW Net

[REVISI MACRO 2.1-macro.1] Registri parameter dan runtime profile mengikuti MAC-08; retensi/incident clock serta NAS trust boundary menurut MAC-03–05. Exact image/dependency pins masih wajib dibuktikan di TK-002, bukan dianggap telah terisi oleh audit statis. Sumber normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` §23.

[REVISI AUD-01–46 · 29 Oktober 2026] Edisi aktif dokumen ini: **2.1**. Baca `MicroTix-File-1-Kontrak-Revisi-Lengkap.md` pada akar paket terlebih dahulu. Klausul yang dikoreksi AUD menggantikan teks/ilustrasi baseline lama pada pokok yang sama; riwayat lama bukan keputusan baru. Input server aktual hanya dari `MicroTix-Template-Onboarding-Server-GNS3.md` versi2.1. Dokumen ini adalah spesifikasi; tidak membuktikan implementasi atau eksekusi.


**Engineering Document v1.3** · 28 Oktober 2026
Riwayat: 1.2 Final (11 Oktober 2026) → 1.3 (28 Oktober 2026; struktur repository kanonik, registri parameter dilengkapi, aturan posting dipindahkan ke Panduan Akuntansi — putusan DOC pada `decisions_log.md` Bagian E)
Baseline produk: `PRD_SaaS_RTRWNet_v2_1.md` (dibaca bersama amendemen v2.1).
Pendamping normatif: `Spesifikasi_RADIUS_dan_Migrasi_v2_1.md`, `Playbook_RouterOS_v2_1.md`, `Spesifikasi_ACS_TR069_v2_1.md`, `Panduan_Akuntansi_ISP_v2_1.md`, `Spesifikasi_i18n_v2_1.md`, `UIUX_Design_RTRWNet_v2_1.md`, `tugas_v2_1.md`, `AGENTS_v2_1.md`, `decisions_log.md`, `source-manifest_v2_0.md`, dokumen kualitas `quality/` (uji, lab, bukti).
Pemilik produk: Huda Choirul Anam.

Dokumen ini mengubah kebutuhan PRD menjadi rancangan implementasi (backend, frontend, jaringan, database, RADIUS, operasional). Keputusan utama: modular monolith dengan proses worker terpisah; PostgreSQL sebagai sumber kebenaran bisnis, antrean job, outbox, dan basis pengguna RADIUS per tenant; koneksi manajemen dan RADIUS melalui VPN WireGuard; trafik internet pelanggan tidak transit di server.

**Status.** Baseline desain final untuk implementasi. Tidak ada kode produksi, benchmark VM, atau sertifikasi kompatibilitas yang dinyatakan selesai. Kontrak build dilengkapi EXE-01–08 dan registri eksekusi. Input lingkungan, keputusan yang dicatat, serta **gerbang pembuktian G0–G5** tetap dinilai menurut scope; status final berada di audit readiness saat ini.

## Aturan interpretasi

ED = keputusan engineering. PRD menentukan perilaku produk; perubahan harga, kuota, aktivasi manual, akses data tenant, atau scope rilis memerlukan perubahan PRD. Angka timeout, batas berkas, dan frekuensi adalah parameter terkonfigurasi (default pada bagian 16), bukan SLA. Fitur dibuka melalui capability dan release flag, bukan hanya hadirnya menu. Kode `[Cxx]/[Dxx]/[Nxx]` menunjuk `decisions_log.md`. Enum dan nama status pada dokumen ini adalah kontrak bersama dengan frontend (registry di `docs/contracts/enums.md`).

Fokus R1: tenant, role, i18n, langganan aplikasi, VPN, discovery/adopsi, RADIUS dan cutover, CRUD pelanggan, CSV, monitoring dasar, backup. R2: billing internet, isolir via RADIUS, aktivasi, kolektor, ledger. R3: Hotspot voucher/agen, ACS, operasional, edge replica. R4: wizard WAN, OLT.

---

# 1 Keputusan arsitektur dan teknologi (final)

| ID | Keputusan | Alasan dan konsekuensi |
|---|---|---|
| ED01 | Python 3.13 dan **Django 5.2 LTS**; Django REST Framework + drf-spectacular untuk kontrak OpenAPI; Gunicorn di belakang reverse proxy | Transaksi, autentikasi, migrasi terpusat; patch dipin saat build (ADR TK-002) |
| ED02 | React + TypeScript (Vite, pnpm, TanStack Query, Vitest, Playwright); Node.js LTS aktif saat TK-002 | Tabel, wizard, status job; lockfile wajib; typed client dihasilkan dari OpenAPI |
| ED03 | **PostgreSQL 17** native Debian (paket PGDG) | Constraint, transaksi, row lock, RLS, deferred constraint trigger; metrik besar tidak disimpan di tabel layanan |
| ED04 | Antrean job **persisten di PostgreSQL** (tabel `job`, `outbox_event`), worker Python sendiri dengan `SELECT … FOR UPDATE SKIP LOCKED`; **tanpa Celery/Redis** pada baseline | Mengurangi komponen; broker hanya lewat ADR baru |
| ED05 | WireGuard + nftables pada host gateway Debian; VPN manager = proses systemd terpisah | Satu peer per router; API web tanpa CAP_NET_ADMIN dan tanpa socket Docker |
| ED06 | Prometheus internal (agregat); endpoint query tidak dibuka ke tenant | Query lewat template berotorisasi |
| ED07 | Storage privat beradapter (`StorageAdapter`); pilot = filesystem pada volume khusus non-executable; scan upload ClamAV via antarmuka scanner [N07] | Object storage dapat menggantikan tanpa mengganti identity artifact |
| ED08 | GenieACS layanan terpisah pada R3 dengan datastore yang didukung versinya | Adapter tenant; GenieACS bukan database bisnis |
| ED34 | Reverse proxy **Caddy 2** (TLS otomatis via TLS-ALPN-01 pada 443; tidak membuka port 80) | Mendukung batas ukuran/timeout per route; menyajikan build web statis |
| ED35 | Klien RouterOS native API(-SSL) **ditulis internal** mengikuti protokol resmi [S02]; library pihak ketiga hanya lewat ADR + review lisensi | Menghindari dependensi tak terpelihara/berlisensi bermasalah; mudah mengatur pin sertifikat dan timeout |
| ED36 | Deployment: aplikasi (api, worker, dispatcher, collector, web) via **Docker Compose** tanpa Docker socket; gateway (WireGuard, nftables, VPN manager, receiver backup, FreeRADIUS) via **systemd** pada host; PostgreSQL native | Pemisahan hak; Kubernetes tidak dipakai |
| ED37 | **FreeRADIUS 3.2 (≥ 3.2.5)** dengan `rlm_sql` PostgreSQL, proses terpisah pada host gateway, bind hanya alamat tunnel; skema `radius`; tenant ditentukan dari klien NAS | Basis pengguna PPPoE/Hotspot per tenant (RAD-01…14); rincian di `Spesifikasi_RADIUS_dan_Migrasi` |
| ED38 | **i18n**: frontend FormatJS (ICU MessageFormat); backend Django i18n (gettext `.po`, plural CLDR) untuk pesan API, email, dokumen; kunci stabil dengan uji paritas; default `id`, wajib `en`; kode mesin tidak diterjemahkan | `Spesifikasi_i18n` |
| ED39 | Pembuatan dokumen PDF (invoice, kwitansi, laporan) oleh layanan render terpisah dari templat per bahasa (HTML→PDF); bahasa terbit disnapshot | Cetak ulang konsisten |
| ED40 | Semua penulisan ke router (termasuk Disconnect/CoA RADIUS) hanya oleh `dispatcher-router`; `radius` tidak menerima perintah dari API selain melalui basis data | Satu pemilik mutasi |

Versi di atas adalah **versi mayor yang dikunci**; patch/minor dipin di lockfile/digest dan dicatat bersama `docs/compatibility.md` pada TK-002. Engineering membuat *compatibility manifest* berisi OS, Python, Django, driver PostgreSQL, lockfile frontend, image digest, RouterOS, firmware CPE sebelum pilot.

**Struktur repository (kanonik; `tugas.md` §6 merujuk ke sini):**

```text
apps/web/
backend/domains/{identity,tenancy,subscriptions,customers,access,billing,ledger,network,jobs,backups,i18n}/
adapters/{routeros,radius,acs,storage}/
infra/{compose,systemd,nftables,caddy,freeradius}/
tests/{contracts,integration,router_lab,radius_lab,e2e}/
docs/{source,adr,runbooks,evidence,contracts}/
locales/{id,en}/
```

Domain monitoring dan field operations ditambahkan pada fase terkait. Modul saling memanggil **service layer**, bukan menulis tabel domain lain.

**Proses terpisah dengan kredensial berbeda:** `api`, `worker-finance` (job keuangan dan scheduler), `dispatcher-router` (satu-satunya pengirim perintah ke router, termasuk Disconnect/CoA), `collector`, `backup-receiver`, `vpn-manager`, `radius` (FreeRADIUS), `radius-janitor` (pembersih sesi basi dan agregasi usage). Boleh berada pada satu VM pilot tetapi berbagi kegagalan host.

**Outbox (ED04):** event ditulis dalam transaksi bisnis yang sama. Callback `on_commit` hanya mempercepat wake-up; polling outbox (interval 2 detik, konfigurasi) tetap menemukan event bila proses mati. [E01, E02]

---

# 2 Batas sistem dan komunikasi

Teks ini normatif [C09]; diagram bersifat ilustratif:

```text
Browser ──HTTPS──▶ Caddy ──▶ api (Django) ──▶ PostgreSQL (app + skema radius)
                                   │                ▲  ▲
                                   ▼                │  │ SQL (soket lokal, role radius_ro/radius_acct)
                           dispatcher-router ◀─(outbox/job)   FreeRADIUS (host gateway)
                                   │ API-SSL (pin cert) / REST (alt, off) / RADIUS Disconnect-CoA UDP 3799
                                   ▼                              ▲  UDP 1812/1813
                       [wg0 gateway: nftables default-deny] ◀─────┘
                                   ▲
 Router ──UDP WireGuard──▶ gateway │   Router ──SFTP (Fetch) via tunnel──▶ backup-receiver
                                                         │ staging → verify → StorageAdapter
 collector ──(akun baca)──▶ router ; collector ──▶ Prometheus (internal)
 CPE ──CWMP/HTTPS (R3)──▶ GenieACS ◀── ACS adapter (internal)
```

| Batas | Izin komunikasi baseline |
|---|---|
| Publik → server | HTTPS 443; UDP WireGuard (port terkonfigurasi); CWMP hanya saat ACS aktif |
| Web → backend | Same-origin API; cookie HttpOnly/Secure/SameSite=Lax dan CSRF; credential router tidak pernah di browser |
| Backend → data | PostgreSQL internal; storage API privat; handler HTTP tidak menjalankan perintah RouterOS |
| Dispatcher → router | Hanya alamat tunnel terdaftar; port API-SSL/REST dan UDP 3799 |
| Router → server | Lewat VPN dari /32 miliknya: UDP 1812/1813 (RADIUS) dan port receiver backup; tolak DB, metrics, queue, peer lain |
| FreeRADIUS → DB | Soket lokal/loopback; `radius_ro`/`radius_acct` hanya EXECUTE facade tenant-scoped yang diaudit; tanpa direct DML lintas tenant. Owner non-BYPASSRLS, tanpa ownership exemption; kontrak AUD-20 dan MAC-05. |
| Staf infrastruktur | Jalur admin terpisah; SSH dibatasi; audit akses dan perubahan |

**ED09** VPN manager menerima operasi typed `create_peer / revoke_peer / reconcile` melalui kanal lokal terotorisasi (Unix socket dengan kredensial peer-uid), tanpa shell/config bebas. Registry peer memakai tulis-rename atomik dan rekonsiliasi restart. Intent NAS/peer, audit dan outbox ditulis dalam satu transaksi DB; efek file/WireGuard serta NAS reload direkonsiliasi dan diverifikasi terpisah. Tidak ada klaim transaksi atomik DB dengan host (AUD-14, AUD-16, AUD-21).

**nftables (tabel `inet rtrw`, dimuat atomik, dipasang oleh unit systemd yang berurutan setelah Docker):**

```text
chain input:   iif wg0 ip saddr @peer_ips tcp dport <receiver_port> ip daddr <server_tunnel_ip> accept
               iif wg0 ip saddr @peer_ips udp dport { 1812, 1813 } ip daddr <server_tunnel_ip> accept   # RADIUS
               iif wg0 drop                              # default-deny dari peer
chain forward: iif wg0 oif wg0 drop                      # tidak ada peer-ke-peer
               iif wg0 drop ; oif wg0 ct state established,related accept
ipv6:          iif wg0 meta nfproto ipv6 drop
egress dispatcher: izinkan hanya ke @peer_ips : { port_api, udp 3799 }; blok 169.254.0.0/16, 127.0.0.0/8, jaringan container/internal
```

Alamat `@peer_ips` dipetakan satu-ke-satu dengan klien NAS RADIUS; paket RADIUS dari alamat selain klien terdaftar dibuang oleh FreeRADIUS. Berkas bukti bayar, CSV, backup, dan export adalah data tidak tepercaya; receiver menulis staging pada volume non-executable. Aturan ruleset diuji dari luar dan dari satu peer tenant.

# 3 Identitas tenant dan otorisasi

**ED10** User global dengan membership pada tenant. Session menyimpan `user_id`; tenant yang dipilih klien hanya permintaan konteks. Backend memeriksa membership aktif dan permission pada setiap request. Pergantian tenant membatalkan subscription realtime dan mengganti namespace cache frontend. Autentikasi: email + password (Argon2id), TOTP + kode pemulihan; kebijakan sesi pada PRD bagian 2 [N05].

**Permission granular (final) dan bundel peran** [C18]. `●` = termasuk bundel default; `○` = delegasi eksplisit/izin khusus.

| Permission | Owner | Teknisi | Admin Pembayaran | Akuntan | Viewer |
|---|:-:|:-:|:-:|:-:|:-:|
| customers.read | ● | ● (bidang operasional) | ● | ● | ● |
| customers.write, imports.run | ● | ● | ○ | | |
| services.provision, routers.configure, profiles.write | ● | ○ | | | |
| radius.cutover (cutover/rollback RADIUS per router), migration.run | ● (reauth) | ○ | | | |
| collections.receive (kolektor), collections.settle | ● | | ● (settle) | ○ | |
| vouchers.manage, agents.manage | ● | | ○ | | |
| prospects.manage, workorders.manage | ● | ● | | | |
| routers.enroll, routers.release, routers.read | ● | ● (read; enroll ○) | ringkasan | | ● (read) |
| services.activate | ● | ○ | ● | | |
| isolation.policy.manage | ● | | ○ | | |
| services.override_hold, services.reveal_credentials | ● | ○ | | | |
| invoices.read, invoices.manage, payments.verify | ● | | ● | ● (read) | |
| billing.correct (refund/write-off) | ● | | ○ | ○ | |
| backups.read, backups.run | ● | ○ | | | |
| backups.download, backups.restore | ● (reauth) | ○ | | | |
| ledger.read, reports.read | ● | | ○ | ● | ○ |
| ledger.post, bank.reconcile | ● | | ○ | ● | |
| period.close, period.reopen | ● (reauth) | | | ○ | |
| monitoring.read, devices.read | ● | ● | ringkasan | | ● |
| devices.manage, tickets.manage | ● | ● | | | |
| team.manage, support.grant, subscription.manage, audit.read | ● | | | | |

Bundel tambahan: **Kolektor** (`collections.receive` untuk pelanggan yang ditugaskan; melihat saldo dan setoran sendiri) dan **Agen/Reseller** (`vouchers.sell`, melihat stok/komisi sendiri). Akun kolektor/agen bukan anggota tim (TEN-02) dan tidak mendapat akses ke menu perusahaan.

Permission platform (terpisah dari tenant; MFA wajib): `platform.payments.verify`, `platform.accounts.manage`, `platform.tenants.manage`, `platform.support`, `platform.infra`, `platform.finance.read`. Super Admin = bundel semua permission platform; tidak memiliki permission tenant.

RBAC UI bukan kontrol keamanan: semua service layer dan unduhan memeriksa tenant, permission, resource ownership, dan hold. Worker memakai principal sistem terbatas jenis aksi; job pengguna memeriksa ulang kewenangan saat eksekusi; scheduler memakai policy aktif tenant, bukan sesi manusia.

**ED11** Tabel tenant: `tenant_id NOT NULL`, indeks tenant-first, FK komposit `(tenant_id, id)`. **RLS sebagai lapisan tambahan**: role runtime bukan owner/superuser/BYPASSRLS; migrator terpisah; `ENABLE` + `FORCE ROW LEVEL SECURITY` pada semua tabel tenant; tanpa konteks tenant, akses ditolak (fail closed). [E03]

```sql
ALTER TABLE service ENABLE ROW LEVEL SECURITY;
ALTER TABLE service FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON service
  USING      (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
-- backend, di awal tiap transaksi setelah membership diverifikasi:
-- SELECT set_config('app.tenant_id', :tenant_id, true);   -- is_local = true
```

Koneksi pooling tidak boleh membawa konteks lintas request (uji T10 pool reuse). RLS tidak melindungi dari backend yang telah dikompromikan. Dispatcher global hanya membaca *queue envelope* minimum; isi job dibuka dengan konteks tenant yang sesuai; tidak ada worker dengan BYPASSRLS. **SupportGrant:** tenant, scope, actor, alasan, `expires_at`, persetujuan Owner; tidak membuka password, kunci VPN, atau raw backup. Privasi bukan klaim zero-access.

---

# 4 Model data dan constraint

**ED12** PK UUID internal; waktu kejadian `timestamptz` UTC; tanggal akuntansi/periode `DATE` + timezone bisnis tersimpan; uang `numeric(20,2)` dan JSON string desimal; tarif/rounding eksplisit; bandwidth integer bit/s.

| Entitas | Kolom utama dan invariant |
|---|---|
| Router | tenant_id, id, code, display_name, tunnel_ip, credential_ref, api_cert_fingerprint, mode (`read_only`/`manage`), capability_version, revision, state (`active`/`replacing`/`retired`/`released`); `code` unik dalam tenant |
| RouterObjectMapping | router_id, namespace (`ppp_secret`/`hotspot_user`/`ppp_profile`/…), external_handle, natural_key, fingerprint, last_seen, generation; `.id` bukan identitas permanen |
| AccessAccount | tenant_id, id, service_id, username (case-sensitive), kind (`pppoe`/`hotspot`), state (`active`/`suspended`/`disabled`/`expired`), secret_ref, credential_state (`unknown`/`ready`/`rotation_pending`), simultaneous_use, mac_lock, static_ip, static_ip_by_router (override IP statis per router; NULL = pakai `static_ip`/pool), allowed_router_ids (NULL = semua), valid_from/until, revision; **UNIQUE (tenant_id, username)** |
| AccessAccountSource | access_account_id, router_id, namespace, external_handle, fingerprint, imported_at (jejak migrasi; satu akun dapat bersumber dari banyak router) |
| RadiusClient (radius.nas) | tenant_id, router_id, nasname (tunnel /32), shortname (router_id), secret (unik per router), enforcement_mode (`local`/`radius_shadow`/`radius_authoritative`/`degraded`) |
| CutoverRun | router_id, state (`planned…authoritative`/`failed`/`rolled_back`), per-step evidence, parity_report, backup_generation_id |
| Customer, Service | customer_code, service_code, customer_id, kind (`pppoe`/`hotspot`), preferred_router_id NULL, profile_binding_id, **lifecycle, billing_eligibility, isolation_reason, desired_network_state, observed_network_state, connection_state, pending_job_id** (ED21), automation_enabled, revision |
| QuotaReservation | tenant_id, kind (`adoption`/`csv`/`provision`/`reactivation`), count, state (`active`/`pending`/`consumed`/`released`), expires_at |
| CommercialPackage / PackageRouterBinding | package_version_id, harga, `download_bps`/`upload_bps` (+ burst), batas data/FUP, `billing_timing`, `cycle`, `due_day`, `first_period_policy`; binding: router_id, pool/profil router, profile_hash (kecepatan bukan bagian profil router) |
| Invoice, InvoiceLine | document_state, period_start/end (DATE), due_at, currency, amount, source_event; line issued tidak diubah |
| Payment, Allocation | verified_at, amount, source_reference, invoice_id; total allocation ≤ payment dan ≤ outstanding |
| PaymentDestination | display_value, normalized_digits, label, kind (`bank`/`ewallet`/`contact_confirmation`), status, `ownership_verified`, `published` |
| Job, Attempt | kind, tenant, resource, revision, dedup_key, state, deadline, lease_epoch, policy_version, result, timestamps |
| BackupGeneration | router, category (`routine`/`manual`/`prechange`), state, retained, created_at; artifact child: size/hash/key_ref/path |
| Collector, Settlement | collector_user_id, tenant_id, receipts (payment_id), settled_amount, settled_at, difference_account |
| VoucherBatch, Voucher, Agent, Commission | batch paket/masa berlaku, kode hash, state (`issued`/`active`/`used`/`expired`/`revoked`), agent_id, komisi, reservasi kuota |
| Journal, JournalLine | book_id, entry_no, source_event, posting_kind, effective_date, posted_at, account_id, debit, credit; posted immutable |

**Unique key minimum:** `(tenant_id, username)` untuk `access_account`, `(tenant_id, customer_code)`, `(tenant_id, service_code)`, `(book_id, source_event, posting_kind)`, `(tenant_id, idempotency_scope, key)`, `(tenant_id, service_id, period_start, period_end, kind)` untuk invoice, `(tenant_id, router_id, namespace, natural_key)` untuk mapping aktif, `(tenant_id, router_id)` untuk radius.nas, `(tenant_id, doc_type, doc_no)`. UNIQUE pada nilai nullable diberi perlakuan eksplisit (`NULLS NOT DISTINCT` atau kolom `COALESCE` pada indeks ekspresi) agar null tidak membolehkan duplikasi identitas wajib.

**Identitas akses:** username unik **per tenant** pada seluruh router tenant, dibandingkan persis (case-sensitive), maks. 64 karakter dan 64 byte UTF-8, tanpa spasi tepi dan karakter kontrol; perbedaan hanya huruf besar/kecil memicu peringatan. `RouterObjectMapping` (namespace `ppp_secret`/`hotspot_user` per router; PPP mencakup semua layanan PPP) hanya jejak sumber migrasi dan pencocokan drift. Handle eksternal yang berubah setelah restore menghasilkan `conflict/needs_review`, bukan relink dari nama saja.

**Indeks utama:** Service(tenant_id, preferred_router_id, lifecycle, id); Invoice(tenant_id, document_state, due_at, id); Allocation(tenant_id, invoice_id); Job(state, available_at, priority, id); Mapping(tenant_id, router_id, namespace, natural_key). Pencarian substring nama/telepon memakai trigram index (`pg_trgm`) dengan query plan terukur.

**Reservasi kuota atomik** (ED20, SUB-02):

[REVISI AUD-10] used = committed_counted_accounts + reserved_unmaterialized_units. Consume reservasi dan materialisasi akun satu transaksi; pending yang sudah punya akun tidak dihitung dua kali. Entitlement lock menserialisasi reserve/consume/release dan expiry.

Reservasi `active` kedaluwarsa pada `expires_at` (default 60 menit) oleh reaper; reservasi `pending` (provisioning gagal sesudah kemungkinan write) tidak kedaluwarsa dan tetap dihitung.

**Perhitungan periode (anniversary, N02) — fungsi referensi dan vektor uji:**

```python
from calendar import monthrange
from datetime import date

def clamp(anchor: int, y: int, m: int) -> date:
    return date(y, m, min(anchor, monthrange(y, m)[1]))

def add_months(y: int, m: int, k: int) -> tuple[int, int]:
    t = (y * 12 + (m - 1)) + k
    return t // 12, t % 12 + 1

def period_start(anchor: int, first: date, k: int) -> date:   # k = 0,1,2,…
    y, m = add_months(first.year, first.month, k)
    return clamp(anchor, y, m)

# period k = [period_start(k), period_start(k+1)) ; tahunan = k..k+11 → end = period_start(k+12)
# Vektor: anchor=31, first=2026-01-31 → 2026-01-31, 2026-02-28, 2026-03-31, 2026-04-30
#         anchor=31, first=2028-01-31 → 2028-01-31, 2028-02-29, 2028-03-31   (kabisat)
#         anchor=29, first=2028-02-29 → akhir tahunan 2029-02-28
```

Soft archive menjaga histori; penghapusan PII memakai kebijakan terpisah. Path artifact opaque dibuat server. Ledger/invoice SaaS platform memakai scope buku berbeda dari ledger tenant.

---

# 5 Kontrak API aplikasi

Prefix `/api/v1`. Session same-origin (cookie HttpOnly, Secure, SameSite); mutasi memeriksa CSRF. Setiap route ber-tenant melakukan membership check. List memakai cursor opaque dengan urutan stabil `(sort_key, id)`, limit default 50, maksimum 200, filter allowlist. Route tanpa tenant pada path mengambil tenant dari record terotorisasi dalam konteks aktif; resource tidak dimiliki → **404 generik**. Endpoint platform memakai permission berbeda tanpa bypass otomatis.

**Endpoint kanonik** [C05] (OpenAPI melengkapi domain lain dengan pola yang sama):

| Operasi | Endpoint → hasil | Permission |
|---|---|---|
| Daftar pelanggan | `GET /tenants/{t}/services` → 200 `data, next_cursor, observed_at` | customers.read |
| Enrollment router | `POST /tenants/{t}/router-enrollments` → 201 `enrollment_id, status` (body: `mode`) | routers.enroll |
| Selesaikan enrollment (dari skrip router) | `POST /enroll/complete` (token) → 200 | token sekali pakai |
| Discovery | `POST /routers/{id}/discoveries` → 202 `job_id` | routers.read |
| Validasi migrasi/impor | `POST /migrations/{id}/validate` dan `POST /imports/{id}/validate` → 202; `GET /migrations/{id}/identity-conflicts` | migration.run / imports.run |
| Panen password (S1) | `POST /routers/{id}/password-harvest` → 202 (reauth; akun migrasi sementara) | migration.run |
| Commit adopsi/migrasi | `POST /migrations/{id}/commit` → 202; membawa `preview_revision` | migration.run |
| Buat/ubah akun akses | `POST /access-accounts` → 201; `PATCH /access-accounts/{id}`; `expected_revision` | services.provision |
| Cutover RADIUS | `POST /routers/{id}/radius-cutover` → 202 (`step`: preflight, parity, install, canary, activate, authoritative, rollback) | radius.cutover |
| Status RADIUS router | `GET /routers/{id}/radius-status` → `enforcement_mode`, sesi, rasio auth | routers.read |
| Voucher | `POST /voucher-batches` → 202 (reservasi kuota); `POST /vouchers/{id}/revoke` | vouchers.manage |
| Kolektor | `POST /collections` (penerimaan), `POST /settlements` | collections.receive / collections.settle |
| Meta | `GET /meta/enums?locale=id` | autentikasi |
| Kredensial layanan | `POST /services/{id}/reveal-credentials` → 200 (reauth) | services.reveal_credentials |
| Verifikasi uang | `POST /payments/{id}/verify` → 200 `payment`, `activation_eligibility` | payments.verify |
| Aktivasi massal | `POST /service-action-batches` → 202 `parent_job_id, selected_count` | services.activate |
| Simulasi isolir | `POST /tenants/{t}/isolation-simulations` → 201 `simulation_id`; `PUT /tenants/{t}/isolation-policy` (butuh `simulation_id` ≤ 24 jam) | isolation.policy.manage |
| Backup | `POST /routers/{id}/backups` → 202; `GET /backup-artifacts/{id}/download` | backups.run / backups.download |
| ACS | `POST /devices/{id}/tasks` → 202 | devices.manage |
| Hasil job | `GET /jobs/{id}` → `state, stage, per_item_summary, safe_error` | sesuai resource |
| Router lifecycle | `POST /routers/{id}/release`, `POST /routers/{id}/replace` → 202/201 (tanpa pemetaan ulang akun) | routers.release |
| Subscription SaaS | `POST /tenants/{t}/quotations`; `POST /saas-invoices/{id}/payment-submissions` (multipart); `GET /tenants/{t}/subscription` | subscription.manage |
| Admin platform | `GET /platform/payment-submissions`; `POST /platform/payment-submissions/{id}/(approve\|reject\|request-revision)`; `PUT /platform/payment-destinations/{id}` (reauth) | platform.* |

**Idempotency.** Header `Idempotency-Key` wajib untuk aksi finansial dan provisioning. Simpan hash canonical body, scope (user/tenant/operation), dan hasil; key sama dengan body berbeda → 409 `idempotency_conflict`. **Retensi hasil key 7 hari** [N08]; unique source-event bisnis tetap melindungi setelah itu. Contoh body aktivasi:

```json
{"service_ids":["uuid"],"action":"activate","expected_revisions":{"uuid":12},"reason":"Pembayaran Oktober diverifikasi"}
```

**Error shape:** `{"code":"revision_conflict","message":"Data berubah. Tinjau ulang.","request_id":"uuid","locale":"id","field_errors":{},"retryable":false}`. Kode kanonik (13): `validation_error` (422), `unauthorized` (401), `forbidden` (403), `not_found` (404), `quota_exceeded` (409), `revision_conflict` (409), `idempotency_conflict` (409), `conflict` (409), `rate_limited` (429 + `Retry-After`), `router_unreachable` (503/job), `unsupported_capability` (409), `verification_failed` (job), `dependency_unavailable` (503). **202 hanya berarti diterima antrean**, bukan berhasil pada perangkat. Label UI `unsupported` dipetakan dari `unsupported_capability`.

**ED13** Frontend poll status job interval awal 2–5 detik lalu backoff; dapat diganti SSE setelah teruji. Retry mutasi selalu memakai key semula saat hasil belum diketahui; timeout jaringan tidak membuat key baru. Unduh artifact memeriksa permission terkini; URL sementara (TTL 5 menit) tidak masuk log.

---
# 6 Antrean pekerjaan dan konsistensi

**ED14** Transaksi bisnis menulis record domain, audit redacted, dan `OutboxEvent` sekaligus. Dispatcher memindahkan outbox ke `Job` dengan `event_id` unik; crash di tengah dapat diproses ulang. Claim kandidat memakai `FOR UPDATE SKIP LOCKED` (untuk queue, bukan untuk menghitung saldo). Transaksi claim pendek dan tidak menunggu I/O router. [E04]

**Jenis job (kind):** `discover_router`, `harvest_passwords`, `commit_migration`, `radius_cutover_step`, `disconnect_session`, `apply_account_attributes` (CoA hanya untuk capability/build teruji; alternatif sesi berikutnya atau Disconnect terotorisasi), `suspend_service`, `activate_service`, `backup_router`, `acs_task`, `issue_vouchers`, `recognize_revenue`, `lifecycle_saas`, `radius_janitor`. Setiap kind mendefinisikan dedup key, preflight, langkah verifikasi, dan kebijakan retry.

**Tahapan job (kanonik):** `queued → claimed → preflight → executing → verifying → succeeded`. Cabang: `waiting_dependency`, `retry_wait`, `failed`, `uncertain`, `cancelled`, `recovery_required`. Parent bulk menyimpan ringkasan (`partial` = agregat anak); status item adalah sumber hasil, bukan persentase animasi.

| Kegagalan | Tindakan wajib |
|---|---|
| Belum ada write, koneksi gagal | Retry berjitter dan berbatas waktu |
| Write terkirim, respons hilang | `uncertain`; readback sebelum write ulang |
| Worker mati setelah hasil router | Rekonsiliasi observed state dan revision; hindari double create |
| Lease habis, proses lama hidup | Hentikan pengiriman baru; karantina scope router sampai ownership selesai |
| Sebagian batch berhasil | Simpan sukses; retry hanya item gagal yang masih eligible |
| Pembayaran/policy berubah | Cancel keputusan lama sebelum write (`policy_changed`); bila terlanjur, tampilkan "perlu aktivasi" |
| Router offline saat aktivasi manual | `waiting_dependency`; pembayaran tetap tercatat |

**ED15** Satu dispatcher pemilik mutasi per router. `lease_epoch` diperiksa di dispatcher sebelum setiap pengiriman; RouterOS tidak memverifikasi epoch (JOB-05). Bila pemilik lama tak dapat dipastikan berhenti, node baru tidak mengambil write sampai koneksi lama dihentikan atau scope direkonsiliasi. Tidak ada janji exactly-once lintas DB/router.

**Default (konfigurasi, §16):** connect timeout 5 dtk, bounded read 15 dtk, job API sederhana deadline 60 dtk, backup deadline sendiri; maksimum 5 percobaan hanya untuk kegagalan terbukti aman; backoff eksponensial berjitter, cap 5 menit; circuit breaker per router (buka setelah 5 kegagalan berturut-turut, half-open 60 dtk). Scheduler adil per tenant dengan batas inflight per tenant/router. Recovery layanan dan pembayaran tidak menunggu antrean backup; collector punya proses dan pool sendiri. Job finansial tidak berhenti karena collector mati.

Cancel hanya bila efek aksi belum terjadi dan fence terbukti menurut EXE-01; executing boleh menuju cancelled hanya pada kondisi tersebut. Permission dicabut atau service `terminated` memblokir aksi baru. Hasil menyimpan intended revision, observed revision, versi adapter, dan bukti verifikasi; secret tidak disimpan sebagai payload mentah.

---

# 7 Enrollment VPN dan adapter MikroTik

**ED16** Server mengalokasikan alamat tunnel unik /32 dari pool deploy (default `100.127.0.0/16`, konfigurasi); bootstrap memeriksa overlap (alamat, rute, bridge) pada router dan berhenti dengan alasan. Private key WireGuard **dibuat di router**; server menyimpan public key, tenant/router, IP, status peer. Key server berada di secret store host dengan backup terkontrol. Templat perintah: `Playbook_RouterOS_v2_1.md`.

**Alur enrollment:** `draft → enrollment_issued → bootstrap_pending → tunnel_seen → api_verified → discovery_ready` (cabang `conflict`, `expired`, `revoked`).

1. Owner memilih `mode` (`read_only` default / `manage`) → server membuat enrollment, token acak 256-bit (simpan hash SHA-256; TTL 15 menit, maks. 60), alokasi IP tunnel, **klien NAS RADIUS** (`radius.nas`: secret acak 32 karakter, `enforcement_mode=local`) dibuat tetapi belum dipakai router.
2. UI menampilkan skrip untuk ditinjau (preview perubahan) lalu Owner menjalankannya di Terminal router.
3. Skrip (namespace `rtrw`, idempoten): preflight versi/capability, nama interface, overlap, routing manajemen; `POST /enroll/validate` (token) sebelum langkah berhak tinggi; interface WireGuard `rtrw-wg`, peer server dengan allowed-address **hanya /32 server**, alamat tunnel, rute ke /32 server; sertifikat self-signed `rtrw-api` dan api-ssl dibatasi /32 server; group `rtrw-read` (+ `rtrw-write` bila `manage`) dan akun `rtrw-mon` (+ `rtrw-mut`) dengan password acak yang dibangkitkan di router; aturan firewall input bernamespace (API-SSL dan UDP 3799 dari /32 server); `POST /enroll/complete` (HTTPS, token) berisi public key, sidik jari sertifikat, kredensial. Server menyimpan kredensial terenkripsi, mendaftarkan peer, menandai token terpakai. **Skrip tidak mengonfigurasi klien RADIUS dan tidak mengubah `/ppp aaa` atau profil Hotspot**; itu terjadi hanya pada cutover.
4. Server menunggu handshake (`tunnel_seen`), login API-SSL dengan pin (`api_verified`), lalu capability discovery (`discovery_ready`). Replay token tidak membuat peer baru. Rotasi kredensial sementara setelah sukses. Revoke token, peer, akun API, dan klien RADIUS adalah tindakan berbeda. Uninstall tidak menghapus objek existing; pembersihan hanya objek bernamespace milik platform.
5. Peningkatan mode `read_only → manage`: skrip pendek bertoken baru yang menambah `rtrw-write` + `rtrw-mut`.
6. **Akun migrasi sementara** (panen password, S1): skrip peningkatan terpisah bertoken, atas persetujuan Owner dan reautentikasi, membuat `rtrw-mig` (policy `read, api, sensitive`), berumur ≤ 24 jam dengan scheduler penghapus; server membaca secret dengan batas laju, menghapus akun lewat perintah terotorisasi, lalu membaca ulang untuk memastikan hilang.

Server UDP harus reachable; UDP terblokir menghasilkan alasan kegagalan, bukan fallback API publik. [E05]

**ED17** Capability record: RouterOS version/build, architecture, native API/TLS, REST, WireGuard, policy baca/tulis, **dukungan RADIUS client/incoming (CoA, Disconnect)**, `fasttrack_may_bypass_queue`, `hotspot_server_present`, `ppp_aaa_state`, `tested_features`. Snapshot baru dapat menurunkan capability setelah upgrade manual. **Native API-SSL dengan pin sertifikat = default; REST HTTPS = adapter alternatif, flag mati**; `verify=false` dilarang. RouterOS v7 untuk mutasi dan cutover; v6 read-only [D03]. Akun monitoring dan mutasi terpisah; group bawaan `read` tidak diasumsikan aman. [E06]

**Interface adapter:** `discover_capabilities; list_accounts; read_object; plan_action; apply_action; verify_action; create_backup; read_health; install_radius_client; set_aaa; disable_local_accounts; rollback_radius; disconnect_session (Disconnect-Request RFC5176, port eksplisit 3799)`. Semua menerima konteks resource terdaftar; tidak menerima shell string, URL arbitrer, atau DNS redirect bebas. Parser menormalisasi boolean/numerik/string RouterOS dan mengembalikan `unsupported_capability` eksplisit. **Egress gateway (SEC-02):** semua koneksi keluar connector melewati satu modul yang hanya mengizinkan (router_id → tunnel_ip terdaftar : port adapter/3799), menolak redirect, metadata endpoint, loopback, dan rentang internal.

**Uji wajib:** NAT/CGNAT dengan UDP keluar, reboot, overlap, kredensial salah, API disabled, sertifikat berbeda dari pin, LAN sama antar-tenant, reload firewall, router v6, IPv6. Skenario tidak lulus ditampilkan `unsupported`. Tidak ada auto-upgrade firmware.

---

# 8 Discovery, migrasi ke RADIUS, impor, dan perubahan manual

**ED18** Discovery hanya membaca field minimum dengan bounded read; snapshot menyimpan source/router/version/time/fingerprint. PPP secret non-PPPoE disaring (`service` bukan pppoe/any tetap lokal, `unmanaged`); `service=any` direview; RADIUS eksternal yang sudah ada = jalur impor S4; sesi aktif bukan daftar pelanggan; **password tidak dibaca saat discovery**. Aturan firewall dibaca hanya untuk deteksi FastTrack. Komentar/script adalah data tidak tepercaya, tidak dieksekusi.

**Pipeline migrasi (database-only)** — rincian `Spesifikasi_RADIUS_dan_Migrasi` §10:

| Tahap | Implementasi |
|---|---|
| Discovery | Snapshot per router; deteksi duplikat username lintas router |
| Penggabungan identitas | Discovery menghasilkan kandidat struktural tanpa membandingkan password. Sesudah sumber credential siap, klasifikasi ulang setara/konflik; keputusan Owner per username (`merge`, `keep_one`, `rename`) direview ulang bila bukti berubah (AUD-18). |
| Pemetaan | Pelanggan (placeholder = username), paket/pool (PackageRouterBinding), atribut (`caller-id`→`mac_lock`, `remote-address`→`static_ip`, `limit-uptime`→`Session-Timeout`, `limit-bytes-total`→`Mikrotik-Total-Limit`, `disabled`→`state=disabled`+`hold_unknown`) |
| Sumber password | S1 panen via akun migrasi; S2 CSV; S3 password baru; S4 impor RADIUS eksternal; tanpa password → `password_unknown` (tidak diproyeksikan) |
| Validasi | Kuota atomik; username unik per tenant; paritas atribut dengan profil router |
| Commit | Transaksi per chunk: `access_account`, `Service`, `access_account_source`, proyeksi `radius.*`; `automation_enabled=false`; **tidak ada penulisan router** |

**ED19** Antara preview dan commit, router/paket/kuota dapat berubah: commit memeriksa `preview_revision` dan mereservasi kuota atomik. Akun sumber hilang → baris `conflict` (tidak membuat akun fallback). Commit massal tidak diklaim atomik bila chunk sudah sukses.

| Tahap CSV | Implementasi |
|---|---|
| Upload | UTF-8/BOM; batas default **10 MiB dan 10.000 baris, keduanya berlaku** (plafon konfigurasi 20 MiB/20.000, naik setelah uji beban) [C01]; parse streaming; simpan privat; scan |
| Mapping | `schema_version`; mode `create / enrich / update / device_mapping / password_migrasi`; kode router/paket scoped tenant |
| Validate | Format, username unik per tenant, kuota, FK, mapping perangkat, IP/pool |
| Preview | created/updated/unchanged/conflict/invalid; diff non-secret; `preview_revision` |
| Commit | Unique row key + batch; transaksi per chunk dengan hasil per baris; retry tidak menggandakan |

Password pada CSV hanya pada mode create/password_migrasi, terenkripsi, dihapus dari staging, tidak diekspor sebagai error. `paid_through_date` hanya input review migrasi.

**Cutover RADIUS (ED41)** — `CutoverRun` mengikuti tabel B0–B6 tunggal di kontrak master §11 (AUD-22–23), melalui job dispatcher-router. Simpan baseline shared setting, ownership consent per objek, revision, recovery coverage dan bukti setiap langkah. B3/B4 memakai 1800/86400 detik nyata; B5 memilih metode yang teruji dan deletion memerlukan izin eksplisit. B6 memulihkan nilai snapshot yang masih sah, bukan nilai hardcode. Matriks exact build di `docs/compatibility.md` adalah keluaran TK-002/TK-509 yang belum tersedia; jika prasyarat belum ada, cutover BLOCKED.

**Drift reconciliation:** membandingkan desired vs observed per field dengan provenance. Scan penuh default tiap 6 jam, on-demand, preflight tiap write. Drift khusus: klien RADIUS/`use-radius` hilang → `radius_client_missing` (mode `degraded`, insiden); secret/user lokal baru pada router otoritatif → `local_account_shadow`; profil/pool binding hilang → `binding_invalid`; objek router hilang → `missing_source` (akun RADIUS tidak terpengaruh); manual disabled → `hold_unknown`.

**Offboarding:** export bisnis + akun RADIUS (ekspor terenkripsi untuk Owner) + daftar resource aplikasi, pencabutan akses, histori sesuai retensi, panduan rollback ke secret lokal; pelepasan lisensi tidak menghapus konfigurasi router.

---

# 9 Billing, pembayaran, dan isolir

**ED20** Invoice SaaS dan invoice internet berbeda domain, namespace nomor, permission, ledger. Harga memakai `PlanVersion`; invoice menyimpan snapshot. Tahunan = 10× bulanan untuk 12 bulan. Batas router dan service berlaku bersamaan; service terisolir tetap dihitung.

**Transaksi verifikasi uang:** lock payment submission dan invoice (urutan konsisten) → validasi dana/otorisasi/nominal → insert Payment + Allocation → update balance projection → source event + audit + outbox → commit. Klik ganda mengembalikan hasil semula. Payment sah tidak dibatalkan oleh router offline. Bukti unggahan tidak membuat payment verified.

**ED21** Dimensi service terpisah: `lifecycle, billing_eligibility, isolation_reason, desired_network_state, observed_network_state, connection_state, pending_job` (nilai enum pada PRD JOB-01). Label turunan `paid-awaiting-activation` = invoice periode terpilih `paid` ∧ `desired_network_state=suspended` ∧ `isolation_reason ∈ {overdue, policy}` ∧ tanpa hold. Hold mengalahkan kelayakan pembayaran.

| Urutan kejadian | Hasil |
|---|---|
| Lunas sebelum scheduler | Tidak ada kandidat isolir |
| Lunas sesudah enqueue sebelum write | Preflight membatalkan job lama |
| Lunas saat write berjalan | Catat uang; rekonsiliasi; `paid-awaiting-activation` bila terlanjur isolir |
| Lunas saat router offline | Uang sah; aktivasi manual → `waiting_dependency` |
| Aktivasi diklik dua kali | Satu logical action; periode tidak diperpanjang dua kali |
| Policy dimatikan/diubah saat job antre | `cancelled` (`policy_changed`) |

**ED22 [REVISI AUD-24–25]** Perubahan state/proyeksi Reject, audit dan outbox atomik; Disconnect RFC5176 menjadi job dispatcher terpisah. Suspend membutuhkan bukti policy revision, ACK atau absence positif, Acct-Stop/readback NAS positif dan recheck60detik. Restore memerlukan Accept, bukan assertion Reject yang sama. Rincian status/bukti/hold dan pool/rate resolution pada kontrak v2.1 §12; no-interim saja tidak memverifikasi sesi mati.

Job aktivasi memeriksa pembayaran periode relevan, exemption, hold, termination, revision. Restore hanya perubahan isolir milik aplikasi yang revision-nya masih cocok; aktivasi hanya memulihkan atribut; perangkat pelanggan tersambung ulang sendiri. Override butuh permission + alasan dan tidak memalsukan lunas. Perubahan paket (kecepatan) memperbarui atribut dan, bila versi RouterOS mendukung, mengirim CoA-Request; bila tidak, Disconnect terjadwal atas persetujuan operator.

**Scheduler:** isolir harian 01:00 zona tenant (dan saat perubahan due/payment); invoice generation sesuai `invoice_lead_days` (prabayar 7 hari); `due_at` mengikuti BIL-02; grace internet default 3 hari; policy per tenant default **off**; aktivasi policy butuh `simulation_id` ≤ 24 jam. Pengingat penagihan sesuai BIL-06. Job kolektor: umur saldo dan pengingat setoran. SaaS lifecycle job harian: `active→grace` pada `end_date`, `grace→restricted` pada hari ke-8, `restricted→ended` pada hari ke-31; **autentikasi RADIUS tenant tetap dilayani selama `ended`** sampai penarikan; notifikasi 7/3/1 hari sebelum penarikan VPN/RADIUS (hari ke-91 setelah `end_date`, yaitu 60 hari sejak `ended`). **Janitor RADIUS** (menit): menutup sesi basi (tanpa interim > 3× interval + grace) dan memperbarui `connection_state`; harian: agregasi `usage_daily`, partisi `radacct`, retensi 90 hari mentah.

---

# 10 Ledger akuntansi dan laporan

**ED23** Hanya posting service terotorisasi yang mengubah ledger. Entry `draft` dapat diperbaiki; sesudah `posted` hanya reversal/adjustment (entry baru dengan `reverses_entry_id`; entry asli tidak diubah; status "reversed" diturunkan lewat view). `source_event` unik mencegah posting ganda. Semua line satu tenant, mata uang, periode. **Period lock** dalam transaksi posting.

**Mekanisme penegakan (keputusan N09, final): kombinasi tiga lapis, semuanya wajib dan diuji bypass:**

1. Schema `ledger` dimiliki role `ledger_owner` (NOBYPASSRLS). Role runtime `app_runtime` hanya `SELECT` dan `EXECUTE ledger.post_entry(...)`; `INSERT/UPDATE/DELETE` pada `journal_entry`/`journal_line` dicabut.
2. `ledger.post_entry` (SECURITY DEFINER, `SET search_path = ledger, pg_temp`) memvalidasi `app.tenant_id`, mengambil `FOR SHARE` pada baris `fiscal_period` (closing memakai `FOR UPDATE` sehingga posting dan penutupan serial), idempoten lewat `(book_id, source_event, posting_kind)` dengan validasi scope book/tenant sesuai AUD-31, mengambil nomor dari `document_sequence` (row lock), menyisipkan entry + line.
3. Constraint trigger *deferred* memastikan debit = kredit lintas baris dan trigger immutability menolak UPDATE/DELETE pada entry/line yang sudah posted.

[REVISI AUD-31] Snippet trigger lama tidak lengkap (header tanpa line, INSERT ke posted, DELETE/move line, search_path). Ia diganti kontrak nonkode pada kontrak v2.1 §15. Implementasi TK-701 harus menguji seluruh jalur bypass, termasuk privileges TRUNCATE/DDL/role inheritance, bukan hanya debit=kredit pada INSERT line.

Uji T12 wajib: insert langsung sebagai `app_runtime` ditolak; entry tak seimbang ditolak saat commit; UPDATE/DELETE posted ditolak; posting ke periode closed ditolak; race posting vs closing; retry source_event tidak menggandakan.

**Aturan posting** (COA, akun per kejadian, jadwal pengakuan prabayar beserta contoh numerik, write-off/refund, kolektor, voucher/komisi, dan seluruh kejadian bisnis) ditetapkan pada `Panduan_Akuntansi_ISP_v2_1.md` bagian 2–9 — **sumber kebenaran tunggal aturan posting**; dokumen ini tidak mengulangnya. Pajak mengikuti versi tarif/rounding/inklusivitas `TaxRule` bila aktif. Aturan ditinjau tenaga akuntansi (G2).

Bank reconciliation: `StatementLine` dengan kunci impor unik (hash akun+tanggal+nominal+referensi+urut); `MatchAllocation` mendukung split (satu mutasi ↔ banyak payment); statement-match ≠ invoice-allocation; saldo buku tak ditimpa tanpa transaksi rekonsiliasi. Laporan laba/neraca membaca ledger posted; dashboard tagihan membaca projection invoice/payment dengan label basis; control account piutang direkonsiliasi dengan subledger; arus kas: kas awal + arus neto = kas akhir setelah penyesuaian yang dijelaskan. `FrameworkVersion` (default SAK EMKM), versi posting rule, dan tanggal efektif tersimpan per tenant; tidak ada klaim kepatuhan hanya karena jurnal seimbang. Buku platform memakai mesin yang sama dengan `scope=platform`.

---

# 11 Backup dan pemulihan berkas

**ED24** Satu generation memuat binary, export, metadata. Kategori `routine/manual/prechange` berkebijakan berbeda: routine **100 generasi retained per router**; manual 10; prechange 10 (FIFO per kategori). Password binary dibangkitkan platform per router, dienkripsi dengan data key tenant (dibungkus kunci utama di luar DB); Owner memperoleh kunci pemulihan via reautentikasi + MFA dengan audit. Export bukan pengganti binary/sertifikat. [E07]

**Alur:** schedule → preflight ruang/izin → API create file → transfer ke staging → verifikasi ukuran/hash server → enkripsi AES-256-GCM + durable save → commit generation → ubah membership retensi (transaksional) → delete lama asinkron → cleanup file sementara router. Generation tidak dipublikasikan sukses bila artifact wajib belum tersedia.

**ED25** Transfer **baseline: RouterOS Fetch SFTP upload melalui VPN ke `backup-receiver`** [D04]: receiver listen hanya pada alamat tunnel server, akun/path scoped per router (rotasi per generasi), tanpa shell, tanpa pemilihan path; identitas server dikendalikan oleh tunnel WireGuard terautentikasi + tujuan dipin /32 + verifikasi host-key bila RouterOS mendukung; kredensial tidak tampil di log. **Cadangan:** adapter *pull* SFTP/SCP dengan host key dipin saat enrollment. Spike TK-505 membuktikan ukuran (default maks. 64 MiB/artifact), timeout, hak RouterOS, dan cleanup; bila keduanya gagal, backup tetap off (G1). Dilarang mematikan validasi diam-diam. Sinyal selesai harus terautentikasi dan dicocokkan dengan keadaan transfer/ukuran; berkas pindah dari staging hanya setelah protokol close/finalize teruji. Hash server membuktikan integritas tersimpan, bukan kesamaan checksum sumber. [E08]

| Titik kegagalan | Pemulihan |
|---|---|
| Router membuat file, transfer gagal | Retry terkontrol; file sementara dicatat; bukan backup berhasil |
| Transfer selesai, commit DB gagal | Orphan scanner mencocokkan job/artifact; tidak publish tanpa metadata |
| Commit sukses, prune gagal | 100 katalog retained; blob lama pending-delete; alert + storage budget |
| Disk penuh | Hentikan backup baru; jangan hapus backup valid |
| Download terputus | Unduh ulang terotorisasi; resume hanya setelah teruji |
| Crash antara commit, katalog, delete | Idempotent finalize; diuji (BKP-06) |

Headroom staging ≥ `max(5 GiB, 2 × artifact terbesar × transfer bersamaan)`; watermark disk 80% peringatan, 90% hentikan backup baru.

**ED26** Filesystem pilot: volume privat terpisah, permission service user, fsync + atomic rename, kunci di luar database. Off-host backup mencakup PostgreSQL (base backup + WAL, termasuk skema `radius`), artifact, key recovery, VPN registry, konfigurasi FreeRADIUS dan secret klien NAS, ACS datastore, konfigurasi aplikasi. Backup router di server bukan backup server. Restore router = operasi berdampak (UI menampilkan router/model/versi, waktu, jenis file, risiko reboot; runbook lab); tidak ada tombol restore umum sebelum G1 untuk model/versi. Uji restore platform membuktikan data dan kunci pulih bersama. Signed URL TTL 5 menit.

---
# 12 Monitoring dan integrasi ACS

**ED27** Collector: scheduler dengan jitter, timeout, circuit breaker, concurrency terbatas. **Status sesi dan penggunaan data per layanan bersumber dari accounting RADIUS** (`radacct` → `connection_state`, `usage_daily`), bukan polling sesi aktif per router; collector hanya membaca health, interface, dan probe. Default health/interface 60 dtk; inventory 15 menit; detail router 15 dtk (shared cache + budget, hanya saat dibuka) [C15]. Setiap sample: `observed_at, collected_at, source, unit, quality`; stale bila usia > 3× interval.

Prometheus internal menyimpan metrik router/interface/RADIUS agregat (rasio autentikasi, latensi, antrean, sesi aktif per router), **tanpa label username, telepon, atau invoice**; data per layanan tinggal di PostgreSQL. API hanya menjalankan query template bernama setelah memeriksa kepemilikan router. Raw PromQL, datasource Grafana, dan endpoint Prometheus tidak dibuka ke tenant (label tenant bukan kontrol akses). [E09] Retensi: raw 15 hari, agregat 5 menit 90 hari, agregat 1 jam 400 hari.

Rate = delta counter / selisih waktu dengan penanganan reset/wrap. Gap bukan nol. WAN + LAN tidak dijumlah sebagai total ganda. Rate interface bukan dasar billing byte. Collector gagal → "data tidak tersedia" (insiden platform), bukan ribuan router mati.

**ED28** Insiden: dedup key `(tenant, resource, signal)`, severity, evidence. Status router: `healthy, degraded, management_unreachable, unmonitored, stale` (3 polling gagal berturut-turut → `management_unreachable`). Probe ISP dipaksa melalui jalur ISP; handshake VPN saja bukan bukti internet end-user sehat. Notifikasi pemulihan satu kali per transisi.

**ED29** (rincian: `Spesifikasi_ACS_TR069_v2_1.md`) Adapter ACS memetakan Device internal ke GenieACS DeviceID dan enrollment tenant. Serial/OUI/product class dipakai bersama bukti enrollment; MAC opsional, bukan bukti kepemilikan. CPE baru dikarantina; autentikasi per-device (kredensial unik dari klaim enrollment); accept-any dilarang [D08]. CPE harus punya jalur IP ke ACS. [E10]

Task perangkat ACS: `queued → waiting_inform → running → verifying → succeeded/failed/expired/cancelled`; outcome job uncertain/recovery_required terpisah dan mengikuti EXE-02. Task ID disimpan sebelum retry; baca status/nilai aktual sebelum kirim ulang. Preset/script hanya milik adapter teruji per model/firmware; tenant tidak mengirim JavaScript mentah. Capability menentukan field Wi-Fi/WAN/optical/firmware. Rotasi PPP password router+CPE tidak atomic (langkah, jalur alternatif, recovery disimpan). Isolir PPP dapat memutus jalur ACS yang memakai koneksi tersebut. NBI dan MongoDB tetap internal. Tidak ada model ONT/OLT pra-didukung; matriks model dibangun dari lab G1.

---

# 13 Mesin perubahan jaringan (R4)

**ED30** Menu jaringan pelanggan dan uplink independen. Planner menerima desired input terstruktur, membaca konfigurasi terbaru, membangun dependency graph dan planned diff, menghasilkan `ChangePlan` immutable (`snapshot_revision`, `template_version`, impact, expiry). Tidak mereset konfigurasi existing agar cocok template.

| Tahap | Syarat dan hasil |
|---|---|
| Discover | Interface, IP/prefix, gateway, route/rule, NAT/mangle, queue/FastTrack, VPN, Hotspot |
| Plan | Daftar create/update objek tertentu; ownership dan layanan terdampak |
| Validate | Dukungan topologi, overlap, return route, eksklusi, jalur API/recovery; **blok PCC bila Hotspot server ada** (WAN-04) |
| Approve | Owner/teknisi berwenang melihat dampak dan maintenance window |
| Apply | Revision cocok; backup valid; langkah kecil dengan checkpoint; *recovery hook* terpasang bila tersedia |
| Verify | Readback konfigurasi + probe traffic/sesi pada jalur benar |
| Compensate | Hanya perubahan plan yang aman dibalik; drift → `recovery_required` |

Static WAN: IP/prefix + gateway. DHCP WAN: handling lease/gateway berubah. Weighted PCC: bucket koneksi sesuai bobot kapasitas input (bukan bonding sesi). Recursive failover berjalan di router dengan ≥2 target independen dan hysteresis (down 3 gagal, up 5 sukses; konfigurasi). Template memperhitungkan local traffic, endpoint VPN, DNAT, return path, FastTrack. **Aturan topologi final:** Hotspot+PCC satu router tidak didukung; Hotspot+single/failover didukung bila lulus lab; PCC untuk router tanpa Hotspot atau gateway terpisah. Failover dapat memutus sesi saat public IP berubah; tidak berlabel seamless.

**ED31** Jalur kontrol dan recovery dinilai sebelum write; bila perubahan dapat memutus satu-satunya akses, fitur ditahan sampai ada prosedur recovery teruji. *Recovery hook* (kandidat): skrip+scheduler bernamespace di router yang mengembalikan hanya objek milik plan setelah TTL kecuali dibatalkan server; aktif hanya bila lulus T13. Safe Mode bukan transaksi API. Tidak ada restore binary/reboot otomatis karena satu health check gagal. Rollback tidak menimpa perubahan manual.

Fixture minimum: single WAN static, DHCP renew, dua ISP, gateway salah, gateway hidup internet putus, VPN di ISP gagal, inbound DNAT, FastTrack, PPPoE aktif, Hotspot login, IPv6. Topologi kompleks/VRF/overlap menunggu template bukti.

---

# 14 Deployment, kapasitas, dan operasi

**ED32** Artefak dibangun di CI, ditandatangani/diberi digest; produksi mengambil hasil build. Compose + systemd (ED36) dengan akun terpisah, volume persisten, resource limit, health check. Aplikasi tidak memegang Docker socket. Django: `DEBUG=false`, validasi host, TLS, `check --deploy`. [E01]

**Deploy:** backup DB/config → migrasi kompatibel mundur (expand/contract) → start versi baru → smoke auth/tenant/jobs → alihkan web → drain worker lama → aktifkan fitur bertahap. Penghapusan kolom menunggu semua versi lama nonaktif. Rollback aplikasi tidak menghapus transaksi baru dengan restore DB sembarang.

| Pengukuran kapasitas | Perencanaan |
|---|---|
| 1.000 tenant × 2 router | 2.000 router; 60 dtk ≈ 33 siklus/dtk |
| Backup 2 MiB × 100 × 2.000 | ≈ 391 GiB sebelum replika, staging, manual, DB |
| 200.000 CPE, inform 900 dtk | ≈ 222 sesi/dtk rata-rata; reconnect storm lebih tinggi |
| UI dan job | p95 list/enqueue ≤ 2 dtk; aktivasi sehat ≤ 60 dtk (di luar ACS waiting inform) |
| RADIUS | 300.000 akun/1.000 tenant; ≈ 1.000 accounting/dtk (sesi serentak, interim 300 dtk); p95 autentikasi ≤ 100 ms; HA dua proses; pool SQL dan thread dibatasi; `radacct` dipartisi bulanan |

Tidak ada angka RAM/vCPU yang diklaim sebelum inventory + benchmark G4 [D02]. Satu VM = SPOF termasuk listrik dan ISP; UPS, disk health, backup off-host, bandwidth upload, dan akses pemulihan host masuk readiness checklist. Skala 10 → 100 → 1.000 tenant berbasis evidence.

**ED33** Instrumentasi: queue age, job uncertainty, API latency/error, DB lock/pool, disk/staging, backup lag, cert expiry, tunnel health, collector lag. Log berisi request/job/tenant id internal; tidak ada password, token, raw script, bukti transfer. Retensi log: aplikasi 30 hari, akses 90 hari, keamanan/audit 400 hari [N08].

**DR (target uji, bukan SLA)** [D10]: RPO transaksi ≤ 15 menit (base backup + WAL off-host), RTO ≤ 4 jam; RPO artifact dicatat terpisah. Drill memulihkan DB (termasuk skema `radius`), file, secret, gateway, FreeRADIUS, ACS lalu **menahan mutasi sampai rekonsiliasi selesai**; autentikasi RADIUS dipulihkan lebih dulu agar sambungan baru pelanggan kembali. Setelah server pulih: baca policy dan pembayaran terbaru sebelum memproses backlog; job lama yang tak relevan dibatalkan. Saat server mati router mempertahankan konfigurasi terakhir; failover lokal tetap lokal.

---

# 15 Pengujian dan pemetaan kebutuhan

| PRD | Desain engineering | UI | Bukti penerimaan |
|---|---|---|---|
| NET-01–08 | ED05, ED09, ED16–17, ED34–35 | U05–U06 | Enrollment, firewall, TLS pin, reboot lab |
| IMP-01–05, DATA-01 | ED12, ED18–19 | U04, U07–U08 | Impor ulang tanpa write; konflik username/restore |
| SUB, PAY | ED20, PlanVersion, entitlement | U01–U03, U14, U18 | Approval ganda, race kuota, renewal, anniversary |
| RAD-01–14 | ED37, ED41, ED16–17, ED22 | U05–U07, U19 | T16–T22: PAP/CHAP/MS-CHAPv2, cutover/rollback, lintas router, isolasi tenant, Reject+Disconnect, accounting, outage |
| BIL, ACT-01–05 | ED20–22, ED14–15 | U09–U10, U16 | Payment race, manual hold, hasil per item |
| HSP, AGT, COL | ED22, ED23 | U09, U20 | T24: reservasi voucher, kedaluwarsa, komisi, setoran kolektor |
| I18N-01–10 | ED38–39 | Semua | T23: id/en/pseudo-locale, dokumen, fallback |
| ACC-01–06 | ED23 | U11 | Balance, period lock, bypass, rekonsiliasi, review akuntan |
| BKP-01–06 | ED24–26 | U12 | Generasi 101, crash, file besar, restore |
| MON, ACS | ED27–29 | U13, U15 | Gap/stale, auth CPE, queued vs executed |
| WAN, CFG | ED30–31 | U17 | Uji tiap ISP, sesi, return route, recovery |
| SEC, JOB, NFR | ED10–15, ED32–33 | Semua, U16, U18 | Cross-tenant, worker mati, DR, benchmark |

Unit: policy/eligibility, allocation, periode (vektor §4), rounding, parser. Integration: PostgreSQL nyata (constraint/RLS/lock/ledger bypass), receiver staging, fake adapter deterministik. Lab RouterOS nyata/CHR untuk routing, sesi, permission, backup — mock tidak menggantikan. Contract tests menyamakan schema error, enum job, capability dengan frontend. E2E: register → enroll → discover → adopt → complete billing → verify money → manual activate. Data UI sintetis.

Security negative suite: IDOR, SSRF, cache key lintas tenant, URL artifact, RLS pool reuse, support grant expired, malicious CSV, privilege escalation, CPE serial conflict, peer-to-peer forwarding, upload traversal, CSRF. Concurrency suite: bunuh worker sebelum/sesudah write, gandakan event, ubah payment saat isolir, restart receiver sebelum prune, dua reservasi kuota; assert invariant bisnis dan observed router state.

**Gerbang rilis (PRD §26):** G0 desain/ADR; G1 lab adapter/RADIUS/CPE; G2 tenant/security/finance/restore; G3 pilot terbatas; G4 load/soak/reconnect/HA RADIUS; G5 DR/runbook. Uji T01–T24. Fitur gagal gate tetap off. Setiap test menyimpan versi, topologi, input, expected/actual, timestamp, evidence tanpa secret.

---

# 16 Parameter terkunci dan referensi

## Registri konfigurasi (default final; semua dapat dikonfigurasi kecuali tertulis tetap)

| Kunci | Default | Rujukan |
|---|---|---|
| `csv.max_bytes` / `csv.max_rows` | 10 MiB / 10.000 (plafon 20 MiB / 20.000) | C01, N01 |
| `enroll.token_ttl_min` | 15 (maks. 60) | NET-03 |
| `vpn.pool_cidr` | 100.127.0.0/16 | NET-01 |
| `vpn.keepalive_s` | 25 (NAT) | NET-02 |
| `router.connect_timeout_s` / `read_timeout_s` / `job_deadline_s` | 5 / 15 / 60 | ED15 |
| `job.max_attempts` / `backoff_cap_s` | 5 / 300 | ED15 |
| `poll.health_s` / `inventory_s` / `detail_s` | 60 / 900 / 15 | MON-02 |
| `drift.scan_interval_h` | 6 | SYNC-01 |
| `quota.reservation_ttl_min` | 60 | SUB-02 |
| `quota.draft_ratio` / `draft_min` / `draft_max` | 0.25 / 10 / 500 | N03 |
| `saas.grace_days` / `restricted_until_day` / `vpn_retention_days` / `data_retention_days` | 7 / 30 / 60 / 180 | D05 |
| `saas.invoice_expiry_days` | 7 | PAY-01 |
| `isolation.grace_days` (per tenant) | 3 (0–30) | D05 |
| `isolation.enabled` (per tenant) | false | ACT-01 |
| `isolation.simulation_ttl_h` | 24 | ACT-01 |
| `invoice.lead_days_prepaid` / `postpaid_due_days` | 7 / 7 | BIL-02 |
| `backup.routine_max` / `manual_max` / `prechange_max` | 100 / 10 / 10 | BKP-01 |
| `backup.max_artifact_mib` | 64 | D04 |
| `backup.watermark_warn` / `stop` | 80% / 90% | BKP-06 |
| `download.signed_url_ttl_s` | 300 | BKP-04 |
| `idempotency.retention_days` | 7 | N08 |
| `log.retention_days` app / access / security | 30 / 90 / 400 | N08 |
| `metrics.retention` raw / 5m / 1h | 15 d / 90 d / 400 d | D07 |
| `session.idle` tenant / platform | 8 h / 30 min | PRD §2 |
| `reauth.window_min` | 10 | PRD §2 |
| `team.max_members` | 3/5/8/12/20/50 | N11 |
| `platinum.max_routers` / `max_services` | 25 / 5.000 | D07 |
| `router.replace_overlap_days` | 30 | N12 |
| `radius.interim_s` | 300 | RAD-04 |
| `radius.simul_use_default` | 1 | RAD-04 |
| `radius.stale_session_factor` | 3 × interim + grace 60 dtk | RAD-07 |
| `radius.acct_retention_days` / `usage_daily_retention_days` | 90 / 400 | RAD-07 |
| `radius.radpostauth_retention_days` | 30 | OPS-SEC |
| `radius.auth_timeout_s` (router) | 3 (uji lab) | RAD-08 |
| `radius.canary_minutes` | 30 | RAD-10 |
| `migration.harvest_account_ttl_h` | 24 | NET-05 |
| `migration.harvest_rate_per_min` | 60 objek | RAD-09 |
| `cutover.local_account_batch_size` | 100 | RAD-10 |
| `i18n.default_locale` / `i18n.enabled_locales` | `id` / `id,en` | I18N-01 |
| `billing.first_period_policy` | `full` | N18 |
| `billing.reminder_offsets_days` | -3, 0, 3 | BIL-06 |
| `collector.settlement_alert_days` | 3 | COL-01 |
| `asset.capitalization_threshold_idr` / `asset.useful_life_years` | 2.500.000 / 4 | ACC-06 |
| `agent.max_per_plan` | 5/20/50/100/200/500 | TEN-02 |
| `ledger.retention_years` | 10 tahun kalender minimum; tidak boleh dikurangi; batas/hold/purge MAC-03 | D05/D10 + MAC-03/08 |
| `BRAND_NAME/DOMAIN/LOGO/CONTACT` | wajib diisi sebelum landing publik | N06, D01 |
| `payment_destination.published` | false | N04 |
| `contact_confirmation.number` | 082319199930 | PAY-02 |
| `acs.inform_interval_s` | 900 | ACS-02 |
| `acs.task_ttl_h` | 24 | ACS-05 |
| `mon.wan_probe_fail_down` / `mon.wan_probe_success_up` | 3 / 5 | MON-04 |
| `mon.poll_fail_threshold` | 3 | MON-05 |
| `vpn.mtu` | 1420 (nilai awal; wajib uji lab) | NET-01 |
| `auth.login_max_failed` / `auth.login_window_min` | 5 / 15 | SEC-01 |
| `auth.password_min_len` | 12 | PRD §2 |
| `services.generated_password_length` | 16 | CUS-01 |
| `session.absolute_hours` tenant / platform | 24 / 12 | PRD §2 |
| `isolation.scheduler_hour` | 01:00 (zona tenant) | ACT-02 |
| `csv.temp_file_ttl_h` | 24 | CSV-03 |
| `discovery.per_router_concurrency` | 1 | IMP-01 |
| `upload.payment_proof_max_mib` | 5 | PAY-02 |

## Referensi

E01 Django deployment checklist — https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
E02 Django transactions — https://docs.djangoproject.com/en/5.2/topics/db/transactions/
E03 PostgreSQL row security — https://www.postgresql.org/docs/17/ddl-rowsecurity.html
E04 PostgreSQL SELECT (SKIP LOCKED) — https://www.postgresql.org/docs/17/sql-select.html
E05 MikroTik WireGuard — https://help.mikrotik.com/docs/spaces/ROS/pages/69664792/WireGuard
E06 MikroTik User — https://help.mikrotik.com/docs/spaces/ROS/pages/8978504/User
E07 MikroTik Backup — https://help.mikrotik.com/docs/spaces/ROS/pages/40992852/Backup
E08 MikroTik Fetch — https://help.mikrotik.com/docs/spaces/ROS/pages/8978514/Fetch
E09 Prometheus security — https://prometheus.io/docs/operating/security/
E10 GenieACS — https://docs.genieacs.com/en/stable/api-reference.html ; https://docs.genieacs.com/en/stable/cpe-authentication.html
E11 FreeRADIUS SQL module — https://www.freeradius.org/documentation/
E12 RFC 5176 Dynamic Authorization — https://www.rfc-editor.org/rfc/rfc5176
Sumber MikroTik/GenieACS/akuntansi/RADIUS/TR-069 lain: S01–S28 pada PRD v1.4 bagian 28.

## Prasyarat pembuktian (bukan keputusan)

Sebelum cutover RADIUS: lulus T16/T17/T18/T21 pada RouterOS nyata/CHR dan tercatat urutan prioritas lokal vs RADIUS serta perilaku secret lokal nonaktif (G1). Sebelum coding adapter: catat RouterOS/build/model uji di `docs/compatibility.md` (TK-002/304). Sebelum backup produksi: lulus spike TK-505. Sebelum posting finansial produksi: review akuntan atas COA default, posting rules, dan cutover (G2). Sebelum WAN/ACS: matriks topologi/model lulus lab (G1). Sebelum pilot publik: inventory dan ukur VM/NAT/UDP/IOPS/uplink (TK-1001, G3). Sebelum skala 1.000: benchmark dan drill (G4, G5). Tidak ada gerbang dianggap lulus hanya karena tertulis di dokumen ini.

## Perluasan registri tata kelola 2.1-macro.1

### MAC-08 — Registri kontrol tambahan dan akuntabilitas

Tabel berikut merupakan perluasan TD §16; key existing `ledger.retention_years` diperketat, bukan dibuat dua sumber nilai. Seluruh nilai efektif disnapshot dalam profil run. Field kontak/kanal/reviewer merupakan data deployment yang harus nyata, bukan default hasil audit.

| Key | Tipe; satuan | Default/batas | Scope; sumber; versi efektif | Perubahan |
|---|---|---|---|---|
| `ledger.retention_years` | integer; tahun kalender | 10; minimum 10 | book; LEGAL_MINIMUM + MAC-03; 2.1-macro.1 | Tidak memendekkan batas tersnapshot; kenaikan beralasan dan direview |
| `privacy.incident.processor_escalation_max_s` | integer; detik | 86400; 1..86400 | platform/DPA; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Boleh diperketat, tidak ditambah di depan tenggat pengendali |
| `privacy.incident.initial_draft_max_s` | integer; detik | 86400; 1..86400 | incident response; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Draft ≤ delivery readiness ≤ notification deadline |
| `privacy.incident.delivery_ready_max_s` | integer; detik | 172800; 1..172800 | incident response; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Kenaikan memerlukan revisi kontrak, bukan override runtime |
| `privacy.incident.notification_deadline_s` | integer; detik | 259200; 1..259200 | controller activity; LEGAL_LIMIT + operational clock MAC-04; 2.1-macro.1 | Boleh lebih ketat; interpretasi counsel dicatat tanpa mereset jam |
| `release.pilot.max_tenants` | integer; tenant | 1; baseline maksimum 1 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Profil/ADR disetujui sebelum run untuk mengubah cap |
| `release.pilot.max_routers` | integer; router | 1; baseline maksimum 1 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Profil/ADR disetujui sebelum run untuk mengubah cap |
| `release.pilot.max_services` | integer; layanan | 50; baseline maksimum 50 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Tidak mengubah kuota paket komersial |
| `release.pilot.min_observation_days` | integer; hari kalender nyata | 7; minimum 7 dan mencakup siklus relevan | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Perpanjang bila siklus belum teramati; tidak dipersingkat demi PASS |

Pemilik produk menetapkan scope; arsitek memelihara kontrak/dependency; maintainer/QA memelihara registry, assertion dan bukti; security owner menguji isolasi; finance owner bersama akuntan meninjau posting/retensi; privacy/legal owner memverifikasi pemrosesan dan kanal; release owner memutuskan aktivasi pada change plan; operations owner memegang recovery/insiden. Nama dan bukti penugasan aktual wajib saat gate terkait; gelar/role pada dokumen tidak berarti seseorang telah menyetujui.

## Kontrak eksekusi terstruktur 2.1-build.1

EXE-01–08 memperjelas state job/ACS, parameter, dependency dan readiness. Materialisasi TD §6/§16: `contracts/job-kind-registry_v2_1.json`, `contracts/parameter-registry_v2_1.json` dan `contracts/Execution_Design_v2_1.md`. Nilai lama di tabel §16 adalah proyeksi penjelas/alias, bukan definisi independen. Konsumen runtime menerima key kanonik registry; importer migrasi melakukan konversi exact.
