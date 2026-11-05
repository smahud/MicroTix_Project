# MicroTix — checkpoint kemajuan

Rekam jejak eksekusi agent per IMPLEMENTATION_PLAN.md §2.5. Terakhir diperbarui: 2026-11-05 (Asia/Jakarta).

## Checkpoint BE-2 — Konsolidasi beta: M3 inti (enrollment/RADIUS/proyeksi) + M4 fondasi + installer hardened (frontend live ditegakkan)

**Scope**: konsolidasi lanjutan dari BE-1 sesuai master prompt V4 — bukan rewrite. Menutup inti R1 yang memungkinkan alur beta nyata: enrollment router (TK-301/302), klien API-SSL native (TK-304), domain akses AAA + proyeksi radius.* + facade SQL multi-tenant (TK-306/307 sebagian), layanan pelanggan + CSV S2 (TK-405/404 subset), hardening instalasi.sh (§9), gate frontend live. Status rilis dinyatakan pada [BETA_RELEASE_NOTES.md](BETA_RELEASE_NOTES.md): **BETA_READY_WITH_LIMITATIONS**.

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bugfix grant_runtime | done | SQL lama memakai %-formatting Python di atas %I PostgreSQL → ValueError pada DB nyata (tidak pernah tereksekusi sebelumnya). Ditulis ulang: identifier tervalidasi regex + %%I ter-escape; kini mencakup skema public+radius; diverifikasi mtx_app mendapat SELECT/INSERT |
| tenant_scope reentrant | done | BUG SISTEMIK ditemukan tes: scope dalam reset GUC ke '' saat keluar → memutus konteks scope luar (view→service). Kini menyimpan+memulihkan nilai sebelumnya; tanpa scope luar tetap fail-closed. Semua 142 tes lulus |
| Enrollment router (TK-301/302) | done | Draft+issue: token 256-bit hanya hash+TTL 15 mnt; /32 reserved dari 100.127.0.0/16 via jalur GUC platform_service (UNIQUE global, alokasi lintas-tenant); bootstrap script bernamespace rtrw- idempoten (password API CSPRNG platform disuntik kanal rahasia §2.5; allowed-address hanya /32 server; TIDAK menyentuh konfigurasi pelanggan); probe endpoint mesin (token di body, bukan URL) → konsumsi atomik: Router read_only + credential_ref AEAD + NAS desired rev 1 + audit; replay nonce/identitas sama = logical; identitas beda = 409; produksi memverifikasi sumber IP tunnel (MT_ENROLL_VERIFY_SOURCE default on di production) |
| Skema radius.* + facade (TK-306) | done | Migrasi 0003: nas/radcheck/radreply/radusergroup/radgroupreply/radacct/radpostauth + RLS tenant identik + policy bootstrap (radius_svc) + facade SECURITY DEFINER (lookup_nas menetapkan GUC sempit lalu binding tenant; check/reply tetap RLS GUC; search_path terkualifikasi). Facade: NAS IP = SATU-SATUNYA pengikat tenant; NAS tak dikenal = secure discard |
| Proyeksi + resolver (RAD-02..05) | done | access_account sumber kebenaran (username case-sensitive 64chr/64B, secret_ref AEAD); project_account hapus+tulis ulang atomik; suspend → Auth-Type Reject TANPA Cleartext-Password; activate → atribut terkini; rotate_password satu transaksi; resolver murni: precedence override router > statis > pool, rate rx/tx bit/s, Expiration midnight lokal, eligibility (state/credential/validitas/kind/allowed routers) |
| NAS lifecycle + reconciler (TK-307) | done | ensure_nas/rotate (desired_revision naik; applied hanya setelah probe), radius_reconcile --dry-run/--apply (validasi freeradius -C; tanpa binary = BLOCKED jujur exit≠0)/--mark-applied (probe revision harus cocok desired) |
| Klien API-SSL (TK-304) | done | Protokol biner RouterOS lengkap (length-prefixed words, !re/!done/!trap), TLS + PINNING fingerprint SHA-256, bounded connect/read/word/response, koneksi hanya ke tunnel IP terdaftar (anti-SSRF), login modern; mutation/cutover/backup menolak jujur "pending_lab". 14 tes termasuk server TLS in-process (handshake nyata + pin mismatch ditolak) |
| Discovery (TK-401) | done-partial | Job router_discovery read-only via adapter aktif (simulator dev; api_ssl produksi): akun PPP/Hotspot TANPA password + snapshot fingerprint/summary; health probe job menulis sampel jujur (unreachable = sampel down, bukan job gagal). Wizard 8 langkah belum |
| Layanan + CSV (TK-405/404) | done-partial | POST /services: customer+service+akun AAA+kuota atomik (reservasi commit/release benar) + proyeksi sekaligus; reveal reauth-gated (tes 403 tanpa reauth); list/filter kursor; connection_state jujur unknown. CSV S2: validasi tanpa tulis + preview + commit job idempoten per baris (username existing skipped), batas 10k/10MiB |
| instalasi.sh hardened (§9) | done | Tanpa eval (array quoting); dependensi eksplisit + nodejs/pnpm/rsync/wireguard-tools; password psql via STDIN+escape; unsupported OS DITOLAK (bukan warning); WireGuard host keypair+wg0.conf+env pubkey; FreeRADIUS opsional MT_ENABLE_RADIUS=1; upgrade kini rebuild frontend+layanan+backup terverifikasi pg_restore --list; collectstatic; GATE NYATA: exit 2 INSTALL_FAILED / exit 3 INSTALL_PARTIAL (domain/TLS) / 0 SUCCESS — kegagalan health/worker/artefak/izin membuat installer GAGAL |
| Frontend live gate (§5) | done | Plugin vite menolak build produksi tanpa VITE_API_MODE=live (terverifikasi exit 1 vs 0); runtime juga menolak (belt & braces); adapter live telah mengimplementasikan seluruh ApiClient sejak BE-1 |
| i18n backend | done | Katalog enrollment.*/access.* id/en untuk error baru |

### Verifikasi aktual (command + hasil)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` | 0 | **142/142 lulus** = 96 lama + 46 baru: unit resolver (17), unit API-SSL (14, termasuk TLS in-process), integrasi proyeksi/facade/RLS radius (18), integrasi enrollment (11), integrasi services/CSV (7), kontrak M3 (16) |
| `bash scripts/smoke_live.sh` (baru; runserver+curl nyata) | 0 | **20/20 PASS**: health; register→verify; enrollment issued (token sekali) → bootstrap token-salah 401 → script rtrw- → probe consumed + replay logical → router terdaftar → NAS desired 1 → discovery job 202 → worker sukses (simulator, jujur bukan lab) → service+proyeksi → suspend/activate → CSV → tenant asing 404 |
| `tsc -b` / `eslint` / `vitest run` (web) | 0 | 0 error; 42/42 |
| `VITE_API_MODE= vite build` | 1 | DITOLAK oleh gate (bukti tidak ada fallback mock produksi) |
| `VITE_API_MODE=live vite build` | 0 | dist produksi |
| `bash -n instalasi.sh` + dry-run penuh + shim id | 0 | alur 17 langkah; preflight menolak disk 8GB<10GB (uji sungguhan); gate exit-code dipisah |
| `python3 docs/tools/check_docs.py` | 0 | PASS |

Lingkungan uji: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL **17.4 asli** (zonky tanpa root); Node v24 + pnpm 12.16.1. Tanpa host root/domain publik/MikroTik fisik/FreeRADIUS daemon — lihat blocker.

### Keputusan engineering (reversible, dicatat)

1. **Probe enrollment = endpoint mesin** (MachineTokenAuth tanpa CSRF): pemanggil router tanpa sesi; otorisasi = token sekali pakai + TTL + nonce + (produksi) sumber IP tunnel. CSRF tidak relevan tanpa cookie; kelas auth ini HANYA untuk endpoint token-gated ini.
2. **Facade NAS lookup via GUC sempit** (`app.radius_facade` + `app.platform_service`): row_security=off TIDAK dapat melewati FORCE RLS (bahkan owner). Kebijakan GUC = jalur baca bootstrap minimum; check/reply tetap di bawah RLS konteks tenant.
3. **tenant_scope reentrant dengan restore**: nilai sebelumnya disimpan dan dipulihkan; tanpa scope luar tetap fail-closed ''. Mengubah perilaku lama yang asumsinya tidak ada scope bersarang — diverifikasi seluruh suite.
4. **Password akun API-SSL dibangkitkan platform (CSPRNG) dan disuntik ke skrip bootstrap** — ROUTEROS.md §2.5 alternatif injeksi kanal rahasia; generator router tidak dipakai karena belum terbukti per build. Tersimpan credential_ref AEAD; pindah ke router saat complete.
5. **Cutover B0–B6 sengaja TIDAK dibangun** (gate G1; ACCEPTANCE §3) — router hasil enrollment selalu read_only; tidak ada tombol palsu.
6. **`radius_reconcile --apply` tanpa binary freeradius = CommandError BLOCKED** — bukan echo sukses.
7. **Alokasi /32 lintas tenant** membaca lewat GUC platform_service (kebijakan RLS terpisah) karena alokasi memang global; ditandai jelas di kebijakan.

### Blocker / dependency

- **Git push BLOCKED** — tidak ada kredensial GitHub di environment ini (tidak ada env GH_TOKEN/GITHUB_TOKEN, gh CLI, ~/.git-credentials, ~/.netrc, atau berkas di upload/). 6 commit lokal terstruktur siap push (2c09261..925aa14); push menunggu PAT fine-grained (Contents read/write, repo smahud/MicroTix_Project). Remote SHA BELUM terverifikasi — tidak ada klaim pushed.
- **FreeRADIUS daemon + host root + domain publik + MikroTik fisik tidak tersedia** — `make test-radius` jujur BLOCKED; instalasi produksi nyata belum dieksekusi; verified_lab = tidak ada klaim.
- **Playwright browser harness** belum dibangun (smoke live sebagai gantian; tetap todo).
- Wizard U07 8-langkah/identitas lintas router (TK-410), S1/S3/S4, monitoring berkala (TK-502/503), backup router (TK-504–507), PDF (TK-109), M2 billing penuh — belum (lihat BETA_RELEASE_NOTES §3).

### Langkah berikutnya

1. Push seluruh commit saat PAT tersedia; verifikasi remote SHA.
2. Eksekusi instalasi.sh pada host Debian 13 root + domain (Gate A/G nyata) — dokumentasikan hasil gate.
3. Lab FreeRADIUS (RAD-14 checklist) → setelah lulus: aktifkan MT_ENABLE_RADIUS=1, probe secret, mark-applied.
4. CHR/router fisik untuk G1 (T01, T16–T18, T20–T21) → baru pertimbangkan cutover B0–B6.
5. Lanjut M4: wizard 8 langkah + penggabungan identitas; monitoring collector.

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
