# MicroTix — checkpoint kemajuan

Rekam jejak eksekusi agent per IMPLEMENTATION_PLAN.md §2.5. Terakhir diperbarui: 2026-11-05 (Asia/Jakarta).

## Checkpoint BE-2 — Konsolidasi + M3/M4/M5 slice beta (audit → fix → integrasi → verifikasi nyata)

**Scope**: konsolidasi baseline BE-1/FE-1 (bukan rebuild): perbaikan bug nyata hasil audit, penutupan M4 (pelanggan/layanan/akun akses/CSV/migrasi DB-only), M5-ops (backup/monitoring/approval platform), M3 inti (enrollment WireGuard+API-SSL, discovery, cutover B0–B6, **FreeRADIUS NYATA dengan verifikasi radclient**), guard anti-mock frontend, hardening instalasi.sh, pengujian menyeluruh.

### Bug konsolidasi yang ditemukan & diperbaiki (bukti: sebelumnya gagal/jalan-setengah)

| Bug | Dampak | Perbaikan |
|---|---|---|
| `dev_bootstrap.sh` path `BACKEND="$ROOT/backend"` | Skrip dev gagal di langkah 5 | `BACKEND="$ROOT"` |
| `grant_runtime.py` %-formatting Python vs `%I` SQL | `ValueError` — command TIDAK PERNAH berjalan (instalasi.sh hanya di-dry-run; test DB dimiliki mtx_app sehingga tak tersentuh) | f-string + validasi identifier |
| Env test non-deterministik | `pytest tests/unit` gagal bergantung env shell (pytest-django memuat settings sebelum conftest; MT_SECRET_BOX_KEY terbeku kosong) | `microtix/settings_test.py` sebagai DJANGO_SETTINGS_MODULE pytest.ini |
| `instalasi.sh` build frontend tanpa `VITE_API_MODE=live` | **Deployment produksi akan membundle MOCK** (§5 dilanggar) | Guard build vite (gagal jelas) + runtime guard + installer set eksplisit |
| `instalasi.sh` Caddy `handle_path /api/*` | **Seluruh API produksi 404** (prefix dikupas; backend melayani /api/v1 penuh) | `handle /api/*` |
| `instalasi.sh` tanpa Node.js/pnpm/rsync | Build frontend pasti gagal di Debian 13 bersih | apt nodejs/npm + corepack pnpm@12.16.1 + rsync |
| `run()` memakai `eval` | Risiko shell-injection | Eksekusi langsung + run_sh majemuk |
| Signal `weak=True` (closure di `ready()`) | **Proyeksi RADIUS diam-diam mati** setelah GC closure — dibuktikan repro minimal lalu diperbaiki | `weak=False` |
| Scope bersarang `tenant_scope` saling me-reset GUC | Kegagalan RLS tak terduga di job handler | Konvensi caller-provides-scope konsisten |

### Status implementasi (per area)

| Area | Status | Catatan |
|---|---|---|
| M4 Pelanggan/layanan/akun akses | done | Customer/Service/AccessAccount (RADIUS §3: UNIQUE(tenant,username), secret_ref AEAD, credential_state jujur); CRUD + reveal (reauth + no-store); CSV create/link/validate/commit; migrasi: discovery→konflik identitas (merge/keep_one/rename)→commit DB-only (router TIDAK diubah); mode belum tersedia → 503 jujur |
| M5 Backup | done | job backup_router: commit-before-prune, retention per kategori, evidence {source:simulator, verified_lab:false}; router belum enroll → gagal jujur |
| M5 Monitoring | done | /monitor dari RouterHealthSample; unknown ≠ down; radius null tanpa data |
| M2 Approval platform | done | /platform/payment-submissions (platform_admin; 404 generik); approve atomik → invoice paid + subscription ACTIVE + source event immutable + audit/outbox |
| M3 Enrollment | done | Draft→token 256-bit hash-only (TTL 24 j; plaintext SecretBox, dibersihkan saat konsumsi)→skrip bootstrap idempoten TANPA reset/reboot, rule input sempit /32, token di BODY→bridge (replay identitas sama = logis sama; beda = 409)→job verify (simulator; capability jujur)→router read-only + peer WG |
| M3 Discovery | done | Snapshot+DiscoveryObject; password TIDAK dibaca; sesi migrasi tertaut |
| M3 RADIUS skema+facade | done | Skema `radius` + RLS + policy bootstrap; facade SECURITY DEFINER transaksi-local; authorize 5 kolom posisi rlm_sql; accounting idempoten + monotonik + late-Start tanpa reopen; session_count/list; post_auth |
| M3 RADIUS proyeksi+reconciler | done | Signal transaksi-sama; Auth-Type Reject saat suspend; rate hanya dari package pola sah; NAS secret CSPRNG + revision; clients.conf + modul sql via facade (%{Packet-Src-IP-Address}) + site; `freeradius -C` lulus |
| M3 Cutover B0–B6 | done | B0 preflight jujur (alasan spesifik); B1 parity sintetis; B2 install+readback; B3/B4 jendela observasi NYATA (pending_observation, tidak dipercepat); B5 authoritative; B6 rollback |
| M3 Release/replace | done | router_release (peer REMOVED + NAS deproyeksi; router fisik tidak disentuh) + router_replace |
| Guard frontend anti-mock | done | Build produksi tanpa live gagal jelas; runtime guard; installer set live |
| instalasi.sh hardening | done | Node/pnpm/rsync/wireguard-tools; FreeRADIUS fase-gated (MT_ENABLE_RADIUS=1) via reconciler; password psql via stdin; tolak non-Debian-13; gerbang wajib → INSTALL_FAILED exit≠0 / INSTALL_PARTIAL tanpa domain; upgrade = backup+verifikasi+frontend+Caddy; collectstatic; admin non-interaktif opsional |

### Verifikasi aktual (command + hasil)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (PostgreSQL 17 nyata) | 0 | **207/207 lulus** (72 BE-1 + 42 ops + 51 customers + 12 radius-config + 14 radius integration/contract + 16 enrollment dll.) |
| `bash scripts/test_radius.sh` (FreeRADIUS 3.2.7 NYATA + radclient + relay UDP) | 0 | **15/15 PASS**: T16 PAP valid→Accept+Mikrotik-Rate-Limit; salah password→Reject; restart→tetap Accept; secret salah→secure discard; radpostauth tanpa password. T19 username sama via NAS B→Accept data B; password A→Reject (isolasi). T20 suspended→Reject. T21 Start/Interim/Stop + counter monotonik + late-Start tanpa reopen + Simultaneous-Use=1 |
| `make test-radius` | 0 | harness sama |
| `tsc -b && eslint && vitest run` | 0 | 42/42; 0 error |
| `vite build` TANPA live | ≠0 | gagal jelas (guard anti-mock sesuai desain) |
| `VITE_API_MODE=live vite build` | 0 | bundle produksi live |
| `bash -n instalasi.sh` + dry-run 17 langkah | 0 | sintaks OK; preflight menolak disk<10GB; RADIUS jujur nonaktif tanpa flag |
| `python3 docs/tools/check_docs.py` | 0 | dokumentasi valid |

Lingkungan: Linux sandbox Debian 13; Python 3.13; PostgreSQL 17.4 nyata (peran mtx_migrator/mtx_app); FreeRADIUS 3.2.7 + radclient NYATA (binary deb trixie, non-root); Node 24 + pnpm 12.16.1. **Tanpa perangkat MikroTik fisik** — enrollment/discovery/cutover jalur simulator (capability: source=simulator, verified_lab=false).

### Keputusan engineering (reversible, dicatat)

1. Relay UDP harness (radclient tak bisa bind sumber) — resolusi tenant dari alamat sumber; decoy NAS-IP payload diabaikan (§4).
2. Kunci sesi accounting derivat host(NAS):Acct-Session-Id bila Acct-Unique-Session-Id absen.
3. rlm_sql 3.2: authorize 5 kolom posisi; accounting `type{}` + reference (tolower dari rlm_expr — modul expr ditambahkan); post-auth bersarang.
4. Policy bootstrap GUC konsisten: `facade_bootstrap` (radius.nas) + `enroll_bridge` (network_router_enrollment) — SELECT terbatas tanpa melemahkan RLS.
5. Token enrollment plaintext hanya SecretBox-terenkripsi selama TTL; dikosongkan saat konsumsi.
6. Konvensi caller-provides-scope ditegakkan semua handler/service.
7. `weak=False` wajib untuk receiver lokal di AppConfig.ready().
8. Respons 202 ketat {job_id, status_url}; ringkasan migrasi server-side (session.counts).

### Blocker / keterbatasan beta (jujur)

- Perangkat MikroTik fisik tidak tersedia → bukti simulator; T01/T10/T17 belum verified_lab.
- Interface WireGuard host tak bisa dibuat non-root → reconciler menulis konfigurasi; penerapan wg = langkah ops host (didokumentasikan), bukan klaim tunnel aktif.
- B3/B4 cutover menunggu jendela observasi NYATA — bukti penuh butuh NAS produksi.
- HTTPS produksi butuh MT_DOMAIN+DNS — tanpa itu INSTALL_PARTIAL (bukan beta publik).
- Gate A (instalasi produksi nyata Debian 13 + root) belum dapat dijalankan di sandbox.

### Langkah berikutnya

1. Lab MikroTik fisik/CHR: enrollment nyata, API-SSL pin, cutover B3–B5 penuh.
2. Penerapan WireGuard host via systemd + probe handshake.
3. M6/M7 billing/ledger R2 sesuai roadmap.
4. Playwright e2e (`make e2e`) — harness belum dibangun (NOT_RUN jujur).

## Checkpoint BE-1 — Backend M0 fondasi + M1 identitas/job/subscription (frontend mock → backend nyata)

**Scope**: backend/ dari nol sesuai `docs/ARCHITECTURE.md`; M0 (TK-002, TK-003, TK-004 sebagian simulator, TK-107) + M1 inti (TK-101, TK-102, TK-103, TK-105, TK-108, TK-104 live adapter). Endpoint fase M2+ sengaja tidak dibangun (anti API palsu, §5) — 404 envelope `not_found`.

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bootstrap backend (TK-002) | done | Python 3.13.5, Django 5.2.19, DRF 3.16.1, drf-spectacular 0.28.0, psycopg 3.2.13, argon2-cffi 25.1.0, cryptography 50.0.2, gunicorn 26.2.0 — semua patch-exact di `backend/pyproject.toml`; Makefile target standar; CI GitHub Actions; dev bootstrap `backend/scripts/dev_bootstrap.sh` |
| Skema fondasi (TK-003) | done | PK UUID; tenant-first index; FK komposit (tenant_id,parent)→(tenant_id,id) via RunSQL dengan reverse; UNIQUE(tenant_id,id) induk; ENABLE+FORCE RLS semua tabel tenant; event sumber pembayaran platform immutable (trigger); envelope job terpisah dari isi tenant |
| Simulator RouterOS (TK-004) | done | Deterministik + failure injection (unreachable/permission/timeout-after-send→uncertain/revision conflict/drift); discovery tidak pernah membaca password; hasil simulator tidak pernah klaim verified_lab |
| Registri konfigurasi (TK-107) | done | 114 parameter defaults.json dimuat typed; unknown/duplicate ditolak; bounds `approved_default_only` divalidasi; override env hanya bila bounds mengizinkan; release flag R1=true R2-R4=false; branding resolve + publication_blocked |
| Identitas (TK-101) | done | Argon2id min 12; TOTP RFC 6238 (vektor uji Appendix B lulus, anti-replay per step); 10 kode pemulihan HMAC pepper; login 2 tahap MFA via sesi pending 300s; reauth 600s batal saat tenant switch; rate limit 5/900s per akun+IP dengan pesan generik; register→verifikasi email (token hash)→tenant+Owner+subscription free; owner terakhir dilindungi |
| Isolasi tenant (TK-102) | done | RLS FORCE aktif (diverifikasi pg_class); konteks transaction-local `set_config(...,true)` + reset fail-closed saat keluar scope; runtime role bukan superuser/BYPASSRLS; non-milik→404 generik; audit redaction kunci sensitif; secret TOTP AEAD (kunci di luar DB) |
| Job engine (TK-103) | done | State machine §6 penuh (transisi sah divalidasi, terminal tak bisa diubah); claim FOR UPDATE SKIP LOCKED; lease 30s + fencing token/epoch; reconcile lease-expired→uncertain; uncertain→readback resolve; cancel hanya zero-effect; retry menautkan origin; outbox dedup key; worker `runworker`; kind tanpa handler ditolak (anti job palsu) |
| Subscription (TK-105) | done | PlanVersion 6 paket harga persis PRODUCT.md §3 (Free/BRZ/SLV/GLD/DMD/PLT + plafon operasional Platinum); reservasi atomik (entitlement lock SELECT FOR UPDATE, used=committed+pending, TTL 60m, expiry hanya yang terlewat); draft cap formula; quotation snapshot nilai/periode/locale/timezone; Idempotency-Key scope+body-hash, replay & 409 isi beda |
| i18n backend (TK-108) | done | Katalog id/en pesan mesin; /meta/enums?locale terautentikasi; Accept-Language q-weighted fallback id; label enum identik dengan mock FE |
| Storage/upload (TK-106) | done | Pipeline bukti bayar: base64 bounded, magic-bytes sniff (PNG/JPEG/WebP/PDF), klaim MIME wajib cocok isi, ukuran ≤5MiB, path opaque 0600, ClamAV fail-closed saat dikonfigurasi (dev `disabled` berlabel) |
| Live adapter FE (TK-104) | done | `apps/web/src/api/live/adapter.ts` mengimplementasikan seluruh ApiClient via http.ts; CSRF dari cookie mtx_csrf → header x-csrf-token; Idempotency-Key per aksi; pemilihan adapter `VITE_API_MODE=live` |
| instalasi.sh (§17) | done-partial | 17 langkah lengkap; mode install/status/doctor/upgrade/repair/--dry-run; secret CSPRNG; migrator terpisah; runtime NOBYPASSRLS no-CREATEDB; RADIUS fase M3 jujur; TIDAK menyentuh router pelanggan. Teruji: `bash -n` + dry-run penuh di sandbox (root dinetralkan untuk uji); instalasi produksi nyata BELUM dites (butuh host root) |
| Enrollment/discovery/cutover (M3) | not_started | Sesuai urutan IMPLEMENTATION_PLAN; registri router model fondasi sudah ada |
| Customers/services/migrasi CSV (M4) | not_started | Endpoint tidak dibangun — 404 jujur |
| Billing/ledger (M2) | not_started | Event sumber pembayaran platform immutable sudah disiapkan (TK-003) |
| TK-109 PDF | not_started | Belum dikerjakan (lihat langkah berikutnya) |

### Verifikasi aktual (command + hasil)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (backend, PostgreSQL 17.4 nyata via binary zonky; runtime role mtx_app) | 0 | **72/72 lulus** — 34 unit (TOTP RFC, kripto, state machine, simulator, registry, pagination, redaction, izin) + 30 integration (RLS fail-closed/konteks-salah/FK-komposit/bypass, auth end-to-end, MFA+anti-replay, rate-limit, reauth, owner-terakhir, job uncertain/lease/cancel/retry, idempotency, kuota atomik, upload MIME) + 8 contract (OpenAPI, envelope, health, enums, kursor) |
| `tsc -b --pretty false` (apps/web) | 0 | typecheck bersih termasuk adapter live baru |
| `eslint src --ext ts,tsx` | 0 | 0 error/0 warning |
| `vitest run` | 0 | 42/42 lulus (mock adapter tetap; tidak ada test dinonaktifkan) |
| `vite build` | 0 | dist produksi; vendor 164 kB (gzip 54 kB) |
| Smoke live (runserver + curl, skrip 16 asersi) | 0 | **16/16 PASS**: health live/ready; seed CSRF→login→session; POST tanpa CSRF→403; subscription/kuota free (draft_cap 13); 6 paket harga silver=1000000.00; jobs/routers kosong jujur; enums id; tenant asing→404; limit>200→422; register→verify-email→owner tenant baru |
| `python3 docs/tools/check_docs.py` | 0 | dokumentasi tetap valid |
| `bash -n instalasi.sh` + dry-run penuh | 0 | sintaks OK; alur 17 langkah terverifikasi dry-run; preflight menolak disk<10GB dengan benar |

Lingkungan uji: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL **17.4 asli** (binary zonky, tanpa root — bukan SQLite, bukan stub); Node v24.22.2 + pnpm 12.16.1. Tanpa perangkat MikroTik nyata — simulator deterministik saja (jujur: bukan verified_lab).

### Keputusan engineering (reversible, dicatat)

1. **PostgreSQL sandbox tanpa root**: binary PostgreSQL 17.4 (zonky embedded, mirror Aliyun) berjalan sebagai user biasa di 127.0.0.1:55432; peran `mtx_migrator` (pemilik skema) terpisah dari `mtx_app` (runtime, NOBYPASSRLS; CREATEDB hanya dev/test untuk pytest-django). Produksi: instalasi.sh membuat peran tanpa CREATEDN dengan password CSPRNG.
2. **CSRF ditegakkan di authentication DRF**, bukan middleware: DRF membungkus view dengan csrf_exempt sehingga middleware tidak berlaku; `SessionAuthentication` kami memeriksa CSRF untuk SEMUA unsafe method termasuk anonim (anti login-CSRF). SPA memperoleh token dari GET /auth/session (cookie mtx_csrf).
3. **Envelope job (global) vs JobDetail (RLS tenant)**: worker hanya melihat kolom operasional; payload/hasil bisnis dilindungi RLS; worker membuka tenant_scope per job eksplisit — bukan akses broad SELECT semua tenant (§4).
4. **`tenant_scope` reset GUC fail-closed saat keluar** (set_config ''): mencegah konteks bocor pada koneksi pooled/nes-transaction; teruji integrasi.
5. **Endpoint fase M2+ tidak dibangun** (services, migration wizard, CSV, backups, monitoring, RADIUS, platform admin) → 404 envelope. LiveApiClient meneruskan galat apa adanya — UI menampilkan status kosong/galat, bukan data palsu (§5 "jangan membangun API palsu untuk fitur masa depan").
6. **Draft wizard U07 di live mode** disimpan localStorage (berlabel) sampai backend M4 — pilihan sementara yang dicatat, bukan klaim fitur.
7. **TOTP diimplementasi sendiri** (RFC 6238, HMAC-SHA1, stdlib) + vektor uji resmi — tanpa dependensi baru; anti-replay per step.
8. **404 JSON via handler404** hanya untuk production (DEBUG off); dev memakai halaman teknis Django (standar) — diverifikasi di test suite kontrak.

### Blocker / dependency

- **Git push tidak tersedia** (tidak ada kredensial remote di sandbox) — commit lokal terstruktur dibuat; push menunggu akses.
- **Instalasi produksi nyata belum dites** (butuh host Debian 13 + root + domain); dry-run + sintaks terverifikasi.
- **FreeRADIUS/CHR/GNS3/WireGuard host tidak tersedia** di sandbox → `make test-radius` jujur exit 1 BLOCKED; kode M3 menunggu milestone-nya (bukan bloker M1).
- **Playwright e2e harness belum dibangun** (lanjutan dari FE-1) — `make e2e` jujur NOT_RUN.
- **imghdr dihapus dari Python 3.13** — upload memakai magic-bytes sniff sendiri (tanpa imghdr).

### Langkah berikutnya

1. M1 sisa: TK-109 (render PDF invoice/kwitansi), TK-106 signed-URL gateway download (TTL 300s), TK-104 lanjutan: sweep UI live browser (agent-browser) + perbaikan kecil state kosong.
2. M2 (TK-201–205): subscription approval atomik platform-side, renewal/grace, rekening tujuan snapshot.
3. M3 (TK-301–307, 408, 510): enrollment WireGuard/API-SSL pin, NAS reconciler, FreeRADIUS nyata di lab (butuh akses lab — kode+simulator tetap jalan tanpa itu).
4. Push ke remote ketika kredensial tersedia.

## Checkpoint FE-1 — Fondasi frontend R1 (documentation-first → aplikasi berjalan)

**Scope**: seluruh frontend R1 sesuai docs/UI_UX.md (U01–U08, U12–U14, U16, U18–U19) pada `apps/web`, tanpa perubahan backend/domain (belum ada backend — repository documentation-first).

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bootstrap `apps/web` (Vite+React18+TS+pnpm) | done | pnpm 12; deps: react-router-dom, @tanstack/react-query, react-intl (stack ARCHITECTURE.md §1) |
| Design tokens (tokens.css) | done | Warna/tipografi/spacing/radius persis UI_UX.md §2 |
| i18n FormatJS | done | `locales/{id,en}/web.json`, 908 kunci, paritas placeholder 100%; default `id`; pemilih bahasa cookie fungsional |
| Branding resolver | done | Placeholder dev berlabel; publication_blocked sesuai branding.json |
| Permission & release flags | done | Bundel peran ARCHITECTURE.md §3; flag R2–R4 off → menu disembunyikan |
| API boundary typed + mock adapter | done | Endpoint terdokumentasi §5 persis; PENDING_BACKEND ditandai di `client.ts`; banner "MODE PENGEMBANGAN" membedakan fixture dari produksi |
| 17 komponen wajib UI_UX.md §2 | done | AppShell, TenantSwitcher, PageHeader, FilterBar, DataTable, MobileServiceCard, StatusBadge, FreshnessLabel, JobProgress, BulkActionBar, ConfirmAction, FieldError, PermissionNotice, EmptyState, MetricCard, ChartWithTable, AuditTimeline |
| Halaman R1 | done | U01 landing, U02 login/register/verify/recover (+TOTP), U03 overview, U04 list+detail+tambah pelanggan, U05 enrollment 5 langkah, U06 detail router 7 tab, U07 wizard 8 langkah, U08 CSV, U12 backup, U13 monitoring, U14 admin (header navy), U16 job center+detail, U18 settings (tim/langganan/audit), U19 radius (akun/router/cutover B0–B6), plus halaman Paket dan Profile (kontrak TK-408 PENDING_BACKEND) |

### Verifikasi aktual (command + hasil)

| Command (dari `apps/web`) | Exit | Hasil |
|---|---|---|
| `tsc -b --pretty false` | 0 | typecheck bersih (strict, noUncheckedIndexedAccess) |
| `eslint src --ext ts,tsx` | 0 | 0 error/0 warning |
| `vitest run` | 0 | 42/42 test lulus (format, status tone, permission, katalog, adapter mock, badge a11y) |
| `python3 scripts/check_i18n.py` | 0 | 908 kunci; missing id=0, en=0, extra=0; paritas placeholder OK |
| `python3 scripts/check_contrast.py` | 0 | 13/13 pasangan warna ≥4,5:1 (WCAG 2.2 AA, diukur) |
| `vite build` | 0 | 2,6 MiB dist; vendor 164 kB (gzip 54 kB); code splitting per rute |
| `python3 docs/tools/check_docs.py` (akar repo) | 0 | dokumentasi tetap valid |

**Pengujian browser nyata (agent-browser + Chrome headless, dev server Vite)**:
- Login → TOTP → redirect `/app/{tenant}/overview`: PASS (diperbaiki: route `/app` redirect kini eksplisit).
- Tenant switch RT Net Nusantara → RW Net Cemara: PASS; menu per teknisi menyembunyikan Perusahaan dan Tim/Paket Aplikasi sesuai izin (diperbaiki: pola `queryClient.clear()` memutus observer; kini removeQueries selektif + setQueryData).
- Wizard tambah pelanggan → pilihan "Buat akun" → job dibuat → navigasi ke job detail → status berakhir "Succeeded — verified" via polling: PASS.
- Cutover RADIUS + dialog reauth (password+TOTP) → job radius_cutover_step: PASS.
- Drawer mobile 360px → navigasi Pelanggan: PASS; MobileServiceCard 6 kartu; kolom bayar/isolir R2 tersembunyi (diperbaiki agar sesuai fase).
- Sweep 20 halaman × 4 viewport (1440/1280/768/360): 0 horizontal overflow (diperbaiki: header flex-wrap + tenant switcher ringkas mobile, split-view admin 1 kolom <1024px).
- Keyboard: skip link adalah fokus pertama; Tab menelusuri nav; `:focus-visible` + focus ring terukur di DOM.
- VLM visual: overview/customers/radius/admin/monitoring PASS; ditemukan & diperbaiki: (1) `--mt-space-9` tak terdefinisi → ikon search menimpa placeholder (kini 38px); (2) `landing.css` tidak diimpor Landing.tsx → hero full-width (kini terkontrol 780px); (3) nomor `<ol>` stepper bertabrakan label (kini `list-style:none` + wrap); (4) step disabled terlalu pudar (digelapkan).

### Keputusan engineering (reversible, dicatat)

1. **Stack tepat sesuai ARCHITECTURE.md §1**: React+TS+Vite+pnpm+TanStack Query+FormatJS. Tambahan: react-router-dom (routing U01–U20 standar industri), vitest+@testing-library (pengujian §1). Tanpa UI framework eksternal — CSS token murni demi kontrol kontras/ukuran dan kepatuhan tanpa dependensi berlebih.
2. **Katalog di `locales/{id,en}/web.json`** (domain `web` per I18N.md §3) di luar root vite — alias `@locales` + `server.fs.allow`.
3. **Mock adapter in-browser** (default `VITE_API_MODE=mock`) mengimplementasikan `ApiClient` typed; endpoint terdokumentasi §5 mengikuti kontrak persis (202→job_id, error envelope, kursor); endpoint auth/list-router PENDING_BACKEND ditandai eksplisit. Banner dev permanen saat mode mock.
4. **Uang string desimal** (numeric 20,2) → format `Rp1.500.000`/`IDR 1,500,000` hanya di lapisan tampilan.
5. **Offline ≠ merah**: tone warning/netral sesuai UI_UX.md §2; StatusBadge selalu ikon+teks.
6. Grafik SVG ringan dengan gap tetap gap + tabel alternatif (tanpa library chart).

### Blocker / dependency

- ~~Backend belum ada~~ → **terjawab oleh checkpoint BE-1**: live adapter tersedia (`VITE_API_MODE=live`); halaman fase M2+ tetap menunggu endpoint fase aktifnya.
- Endpoint PENDING_BACKEND menunggu OpenAPI TK-408 (packages/bindings) dan skema auth/daftar router — auth kini terdefinisi BE-1 (lihat `/api/schema/`); daftar router live tersedia.
- Playwright E2E (`make e2e`): NOT_RUN — harness CI belum dibangun.
- verified_lab / release_enabled: tidak ada klaim.

## Lingkungan pengujian

- FE-1: Linux sandbox; Node v24.22.2; pnpm 12.16.1; Chrome headless via agent-browser; tanpa DB/router nyata (frontend-only scope).
- BE-1: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL 17.4 (binary asli tanpa root); tanpa perangkat MikroTik/FreeRADIUS nyata — simulator deterministik; klaim verifikasi lab: tidak ada.
