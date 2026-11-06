# MicroTix — checkpoint kemajuan

Rekam jejak eksekusi agent per IMPLEMENTATION_PLAN.md §2.5. Terakhir diperbarui: 2026-11-06 (Asia/Jakarta).

## Checkpoint SESI-2026-11-06 (lanjutan 4) — TK-604 UI billing U09/U10

**Scope**: mulai dari `main` @ `62595f4` (handoff lanjutan 3; CI hijau
diverifikasi via API; 0 PR terbuka). Prioritas handoff §5 urutan 1: **TK-604**
(konsumsi API billing nyata TK-601/TK-109 oleh UI). Orkestrasi sub-agent per
CONTRACT §5: 2 explorer read-only (laporan API-contract + pola FE di
report/backend-explorer|frontend-explorer/) + 1 reviewer independen
(REQUEST_CHANGES → P0/P1 + P2 layak-perbaiki diselesaikan; lihat
report/reviewer/20261106T173900Z-tk604-independent-review.md).

**TK-604 — U09 Tagihan dan Pembayaran + U10 Aktivasi (R2 aktif)**:
- **U09** `features/billing/BillingPage.tsx`: tiga tab Invoice·Pengajuan
  (submitted/ditolak)·Terverifikasi; periode filter selalu terlihat;
  strip aging 5 bucket (BIL-05); catat penerimaan (bukti wajib
  transfer/e-wallet, base64 ≤5 MiB); verifikasi dana dua tahap dengan editor
  alokasi (≤ payment, ≤ sisa tagihan; sisa=kredit "belum dialokasikan");
  tolak + alasan wajib; PDF invoice/kwitansi via tautan same-origin (sesi
  cookie); pasca-verifikasi banner "N menunggu aktivasi" → CTA U10.
- **U10** `features/activation/ActivationPage.tsx`: kandidat akun suspended
  (`access-accounts?state=`) + kelayakan dari invoice nyata
  (`lib/billing-eligibility.ts`: tanpa tertunggak + pernah lunas;
  `fetchAllPages` menilai >1 halaman, maks 10×200); snapshot konfirmasi
  (N layak/M tidak) → validasi kondisi TERBARU per item (refetch akun+invoice)
  → PATCH per item; item asing/berubah blok item itu saja (keberhasilan
  tidak diurungkan — done_when teruji e2e "1 berhasil, 1 diblokir"); hasil
  per item + retry item belum berhasil; label jujur router non-otoritatif
  "Belum dijamin di router ini" (router tak dikenal ≠ dijamin).
- **Backend additif**: `radius_account_row` + service_id/service_code/
  customer_name (identitas U10; kontrak uji diperbarui); kursor masuk
  DITERAPKAN pada /invoices + /payments (pra-ada: next_cursor diterbitkan
  tapi cursor diabaikan — +4 tes); BARU `seed_billing_e2e` (tenant ketiga
  terpisah; jalur services nyata; reset state-mutabel antar-run, bukti
  immutable tak disentuh — proteksi DB terbukti saat percobaan delete).
- **Integrasi FE**: contracts.ts + 9 metode ApiClient (live+mock paritas;
  mock activate/suspend permission diselaraskan ke `services.activate` +
  idempoten paritas 204); rute + release-flag billing/activation → true
  (uji flag diperbarui); tab Tagihan CustomerDetail diisi (invoice per
  layanan); kolom payment/isolation CustomersPage kini tone benar
  (`paymentTone`/`isolationTone` — latent terekspos flag); i18n +134 kunci
  (1042 total, paritas penuh) + grup enum baru di check_i18n.
- **E2E**: `e2e/specs/billing.spec.ts` (3 spec: PDF nyata %PDF; blokir per
  item; verifikasi+kwitansi→aktivasi→kosong) + run.sh seed/ekspor tenant.

**Verifikasi aktual** (PG 17.11 nyata; sandbox Debian 13 non-root):
backend **359/355+4 PASS**; makemigrations --check bersih; FreeRADIUS nyata
**15/15**; FE tsc/eslint 0 + vitest **61/42+19** + i18n paritas; build live
OK + build mock DITOLAK; `make e2e` **10/7+3** (Chromium nyata); docs check
PASS; bash -n instalasi.sh OK.

**Honest gap**: bukti transfer belum dapat diperbesar (backend tanpa endpoint
bukti — hanya `has_proof`); verifikasi belum menyebut rekening (tak ada di
kontrak M6); "Menunggu koneksi" butuh bukti NAS (G1) — digantikan label
jujur; kelayakan dibatasi 10 halaman×200; spec e2e billing bergantung
urutan (workers:1). Detail: report/orchestrator/20261106T174500Z-tk604-billing-ui.md.

## Checkpoint SESI-2026-11-06 (lanjutan 3) — M6 billing engine (TK-601) + dokumen PDF (TK-109)

**Scope**: mulai dari `main` @ `79c42ec` (CI hijau diverifikasi via API;
0 PR terbuka; cabang arsip di-port saat INTEGRATION-1 — tanpa pekerjaan
yang belum digabung). Lingkungan sandbox dibangun ulang via
`docs/tools/setup_env.sh` (deb-extract PG 17.11 + FreeRADIUS 3.2.7).
Titik masuk topologis R2: **TK-109** (render PDF — prasyarat build TK-601,
tugas M1 terakhir `not_started`) → **TK-601** (mesin invoice internet).
Orkestrasi sub-agent per CONTRACT §5: implementasi `domains.documents`
(TK-109) didelegasikan ke sub-agent di worktree terisolasi
(`session/2026-11-06-docs-tk109`; diff direview + diintegrasikan oleh
orchestrator); `domains.billing` (TK-601) dikerjakan orchestrator.

**TK-109 — dokumen terbit PDF immutable** (`domains.documents`):
- `IssuedDocument` (tenant, kind, doc_number UNIQUE(tenant,kind,number),
  ref_type/ref_id polimorfik, locale/timezone/template_version/values
  snapshot, storage_path opaque 0600, sha256, size) — **trigger DB
  immutability** (BEFORE UPDATE OR DELETE, pola subs source event).
- Renderer HTML→PDF per ARCHITECTURE.md §1 ("Dokumen"): **xhtml2pdf 0.2.28**
  dipin (murni Python/wheels — tanpa pango/cairo; reportlab
  `rl_config.invariant=1` → **PDF byte-deterministik**; keputusan solusi
  terkecil dicatat di laporan sesi). Pembatasan jaringan/file dua lapis:
  `ResourceAccessPolicy(allow_remote=False)` + guard `src=/href=` eksternal
  (422) — tanpa fetch URL/berkas; semua nilai di-escape (anti injeksi HTML);
  label dari katalog i18n (doc.*), bulan `doc.month.1..12`, format IDR
  `Rp1.500.000` / `IDR 1,500,000` (I18N-03).
- Bahasa rantai I18N-01 §2 (pelanggan → tenant → id; fallback parent),
  snapshot saat issued; **reprint membaca artifact tersimpan + cek sha256**
  (template v2 tidak pernah mengubah reprint — T23-I18-02 teruji).
- API: GET /tenants/{t}/documents (kursor+filter) + GET .../{id} (PDF,
  application/pdf, filename sanitasi) — customers.read; 401/403/404 jujur.
- Tes: 15 unit + 9 integrasi (determinisme byte, escaping, guard eksternal,
  trigger, konflik nomor, isolasi tenant, reprint snapshot, integritas).

**TK-601 — mesin invoice internet M6** (`domains.billing`):
- `BillingPackage` (BIL-02: siklus fixed_monthly/anniversary, prepaid/
  postpaid, due_day clamp, first_period_policy full/prorata_daily ceil
  Rp100/free; **anniversary + policy≠full ditolak jujur** — tanpa batas
  kalender eksplisit; nama unik per tenant).
- `InternetInvoice` (+lines): snapshot harga/kebijakan saat terbit
  (perubahan harga paket TIDAK mengubah invoice issued — teruji);
  **UNIQUE(tenant, service, kind, period_start, period_end)** mencegah
  scheduler ganda (AC-BIL teruji dua run hari sama + IntegrityError langsung);
  nomor `INV-{ns}-{YYYYMM}-{urut}` via kunci baris tenant (terserialisasi);
  state draft/open/partial/paid/void; total 0 (free_until_next_period) →
  paid jujur.
- `ServiceCharge` (BIL-07): add_on/diskon nominal/persen + jendela masa
  berlaku — semua disnapshot ke line; total negatif ditolak
  (billing.invalid_total, bukan dipotong diam-diam).
- `InternetPayment` (BIL-03 dua tahap): submitted (bukti upload ≠ posted;
  transfer/e-wallet WAJIB bukti via pipeline TK-106 magic-bytes) →
  verified (allocation ke ≥1 invoice + kwitansi) | rejected (alasan wajib);
  `external_ref` unik per tenant (event bank sama dedup → 409; dua transfer
  nyata tetap dua payment); alokasi ≤ nilai payment (sisa=kredit) dan ≤
  sisa tagihan; partial tidak melunasi; **pembayaran TIDAK menyentuh
  lifecycle service** (payment cannot auto-activate — teruji).
- Kwitansi `RCP-{ns}-{YYYYMM}-{urut}` (BIL-08) terbit saat verify (dokumen
  PDF menaut payment); alokasi kosong → kwitansi kredit penuh.
- Aging bucket 0-30/31-60/61-90/>90 + not_due vs due_date (BIL-05; laporan
  level invoice).
- Scheduler `manage.py issue_due_invoices` (--date/--tenant/--dry-run;
  tanggal tenant-lokal WIB/WITA/WIT — batas tengah hari lintas zona teruji;
  catch-up periode terutang; layanan bermasalah dilewati tanpa menghentikan
  tenant lain). **Pemasangan systemd timer 01:00 = langkah ops host Gate
  A/G** (tidak dipasang diam-diam).
- Field `Tenant.locale` (default id) + `Customer.locale` (kosong=belum diset)
  — rantai bahasa dokumen I18N-01/I18N-06; `Service.billing_package` FK
  PROTECT (paket dipakai tidak bisa dihapus — nonaktifkan via active).
- RLS FORCE + policy tenant_isolation pada 6 tabel billing; FK komposit
  (tenant,service)→customers_service, (tenant,invoice)→internet_invoice,
  (tenant,payment)/(tenant,invoice)→allocation; allocation PROTECT dua sisi
  (bukti keuangan tidak ikut terhapus).
- API (services.provision/customers.read/payments.verify sesuai metode;
  Idempotency-Key wajib pada mutasi; 401/403/404 generik sesuai §5):
  packages CRUD, service↔package, charges, invoices list/detail/aging,
  payments list/record/verify/reject/detail. UI U09/U10 = TK-604 (berikutnya).

**Bug latensi pra-ada diperbaiki**: `Makefile` `PY`/`MANAGE` relatif rusak
setelah `cd backend` (`backend/backend/.venv`) — target make test*
gagal menjalankan venv; kini absolut `$(CURDIR)`. CI tak terdampak
(CI memakai `python -m pytest` langsung) — make target kini benar-benar
dipakai lokal per IMPLEMENTATION_PLAN §4.

**Verifikasi aktual (PostgreSQL 17.11 nyata; peran mtx_migrator/mtx_app)**:
`pytest tests -q` **355/355 PASS** (252 baseline + 103 baru: 32 unit
kalender + 23 invoice flow + 21 payment + 24 documents + 3 kontrak);
`makemigrations --check` no changes; `manage.py check` 0 isu;
`make test` 138 / `make test-integration` 217 / `make test-contract` 29
semua PASS; FreeRADIUS nyata **15/15** (T16/T19/T20/T21); FE tsc/eslint
0 error, vitest **42/42**, build live OK, build mock DITOLAK (exit 1);
`make e2e` **7/7** (Chromium nyata, backend nyata); `bash -n instalasi.sh`
OK; docs check PASS.

**Honest gaps (bukan klaim)**: UI U09/U10 belum (TK-604); scheduler belum
dipasang sebagai timer host (Gate A/G); TK-602 isolir/TK-607 saldo
pembuka/TK-608 dokumen koreksi/TK-609 kolektor belum; ledger M7 (TK-701+)
belum — invoice/payment saat ini catatan sumber, tanpa posting ledger
(disesuaikan urutan topologis TK-701 setelah TK-601 build); dokumen
saas_invoice/report = kind terdaftar tanpa template (404 jujur).

**Push**: branch sesi + PR → merge ke `main` via PAT (diverifikasi
`git ls-remote` + CI hijau — lihat laporan sesi untuk SHA final).


## Checkpoint SESI-2026-11-06 (lanjutan 2) — setup_env.sh in-repo + fix harness T19 + push via PAT

**Scope**: sesi lanjutan setelah konteks habis DAN sandbox terdaur ulang di
tengah sesi (insiden: `/home/z/my-project` direset — commit lokal bagian-1
`64ac004`/`18cf506` hilang sebelum ter-push karena PAT belum tersedia).
Bagian-2: PAT diterima dari pengguna → lab dipulihkan dari `/tmp`, repo
di-clone ulang (`main` @ `f284ce8` terverifikasi), kedua commit
direkonstruksi byte-exact dari konteks + diverifikasi ulang penuh.

**Perubahan**: (1) `docs/tools/setup_env.sh` in-repo (`1e326dc`) — bootstrap
sandbox PG17+FreeRADIUS AGENT_HANDOFF §8; `MT_SANDBOX_BASE` overridable;
rebuild BYTE-IDENTIK (sha256 postgres+initdb); idempoten fresh+no-op;
shellcheck 0 findings; manifest `--refresh` 21→22 (docs PASS). (2)
`backend/scripts/test_radius.sh` (`98ea90d`) — fix klasifikasi T19:
no-reply radclient tidak lagi diklaim "KEBOCORAN TENANT" (konflasi terbukti
dari kode; 1x FAIL run pertama sesi ini, reproduksi 4/4 PASS, akar tidak
terbukti/bukti hilang — dugaan no-reply transient; lihat laporan sesi).
(3) Laporan: `report/orchestrator/20261106T063225Z-setup-env-inrepo-push.md`
+ handoff ini.

**Verifikasi ulang pasca-rekonstruksi**: backend **252/252** (2x), RADIUS
nyata **15/15** (6/7 run; 1 FAIL-T19 terinvestigasi + difix), docs PASS
(22 file), `instalasi.sh` bash -n OK (shellcheck 0 error, warning
pre-existing). FE: bit-identik dengan `f575388` CI-hijau — dijalankan CI
GitHub pada PR sesi ini.

**Push**: via PAT (hanya di `.git/config` lokal, tidak pernah di-commit).
**MERGED**: PR #3 → main `1d26b7e39ad8c4b0766cac0899eca708b4edfe27`
(diverifikasi `git ls-remote`; CI GitHub pada `8f6b173` HIJAU:
backend/frontend/docs success). Blokir beta tetap: Gate A/G, G1 lab
MikroTik, lab GNS3 §7.

## Checkpoint SESI-2026-11-06 — WireGuard host adoption + harness E2E (audit truth → WG-1 → E2E-1)

**Scope**: sesi pertama di bawah CONTRACT.md (report/). Mulai dari `main` @
`bbee21c`. Baseline diverifikasi ulang dari nol pada sandbox baru (PostgreSQL
17.11 deb-extract + patch jalur share non-root; FreeRADIUS 3.2.7 deb + libtalloc
/libpcap/libpq/rlm_sql_postgresql): **222/222 + RADIUS nyata 15/15 + FE 42/42 +
build live + docs PASS** — klaim konsolidasi sebelumnya TERKONFIRMASI.

### WG-1: adopsi keypair installer WireGuard host + render peers + probe (P1 handoff §5)

**Latar**: installer membuat keypair X25519 NYATA + `wg0.conf` + env
`MT_WG_SERVER_PUBKEY`, tapi backend MENGABAIKANNYA — `_wg_host()` membuat kunci
sendiri + publikasi placeholder deterministik (sha256 hex). Bootstrap script
memuat placeholder → tunnel tak akan pernah handshake pada host produksi.

**Implementasi** (jujur, tanpa weakening):
- `settings.py`: `MT_WG_SERVER_PUBKEY` divalidasi (X25519 base64 32-byte; salah → ImproperlyConfigured). Kunci privat TIDAK pernah masuk proses aplikasi.
- Model `WireGuardHost`: +`key_source` (installer_env|generated_dev) +`adopted_at` (migrasi 0009). RLS host tetap dikecualikan (platform singleton, sesuai 0004).
- `adopt_wg_host_key()` + command `adopt_wg_host` (--check utk doctor): idempoten; **rotasi DITOLAK bila ada peer aktif** (peers memegang kunci lama — rotasi = operasi jaringan terjadwal, bukan silent break); tanpa peer → adopsi + revision bump + private_key_ref dibersihkan.
- `render_host_config()` + command `render_wg_config`: render wg0.conf dari state host+peers lintas-tenant via `tenant_scope` eksplisit per tenant (§4, bukan broad SELECT); berkas 0600; **PrivateKey hanya dengan --private-key-file (root)**; PENDING/APPLIED/DRIFT dirender (desired), REMOVED tidak.
- `probe_handshakes()` + `probe_wg`: `wg show <iface> latest-handshakes` → pembaruan `last_handshake_at` monotonik + drift evidence (unknown_on_interface/missing_on_interface); binary/interface tak ada → **BLOCKED exit 2 jujur** (stub berlabel hanya utk jalur pembaruan di tes, source=stub — bukan klaim host).
- Desain: TIDAK menambah job kind — worker produksi berjalan non-root, `wg show` butuh root → job probe akan selalu gagal di topologi produksi; probe = command ops (jujur, anti-job-palsu). Gap registri `verify_api_ssl` (dipakai tapi hilang dari JOB_KINDS) DIPERBAIKI + daftar kind ARCHITECTURE §6 disinkronkan.
- Installer: `setup_wireguard()` kini memanggil `adopt_wg_host` (gagal = die, karena bootstrap dengan kunci salah = tunnel diam-diam rusak) + `render_wg_config` ke `$WG_DIR/rendered`; doctor menambah cek `adopt_wg_host --check`; upgrade menjalankan `setup_wireguard` (idempoten).

**Verifikasi**: **252/252** (222 + 23 WG + 7 hardening post-review: validasi pubkey X25519 murni teruji unit (F6), parser epoch overflow tidak fatal (F5), `--check` tanpa baris host = no_host read-only (F2), evidence source stub vs host_wg jujur (F3), migrasi state jobs/0003_alter_job_kind (F1 — P1 dari reviewer), gitignore artefak playwright (F4), asersi judul diperkuat (F8)). `make e2e` 7/7 hijau. Docs check PASS (manifest --refresh, perubahan disengaja).

### E2E-1: harness Playwright `make e2e` (P1 handoff §5 — mengganti NOT_RUN)

**Harness**: `apps/web/e2e` — Playwright 1.57 (Chromium 1200), backend runserver
NYATA (PG17+RLS, dev_bootstrap idempoten, seed 2 tenant), Vite dev + proxy
`/api` + `VITE_API_MODE=live` (guard anti-mock tetap berlaku); token verifikasi
email dibaca dari LOG email konsol (jalur email dev nyata — tanpa bypass API);
ID tenant seed diekspor dari DB utk uji isolasi; `--config` eksplisit (tanpa ini
playwright memuat spec vitest unit → 0 tes); vitest `exclude e2e/**`; tsconfig
baru `tsconfig.e2e.json` masuk `tsc -b`.

**Alur teruji (7/7, exit 0)**: login happy (owner seed) → overview data nyata;
login salah → pesan generik; `/app` tanpa sesi → redirect login; **isolasi
tenant: URL tenant asing → 404 envelope + nol data bocor di UI**; **register →
email (token konsol) → verify (klik) → login → tenant baru tampil**; landing
i18n id; mobile 360px drawer → empty state jujur.

**2 bug nyata ditemukan + diperbaiki harness** (bukti nilai harness):
1. FE: login non-MFA TIDAK pernah navigasi (`LoginPage` hanya menangani
   requires_totp; jalur TOTP-lah yang dites era mock). Fix: `navigate('/app')`
   + refresh konteks sesi paritas loginTotp.
2. CSRF: topologi dev proxy → Django 4+ menolak Origin 5173 (403 login di
   browser). Fix: `CSRF_TRUSTED_ORIGINS` non-produksi saja; produksi same-origin
   tetap kosong.

### Blocker (tetap, jujur)
- Gate A/G (host Debian 13 root+domain) + G1 (lab MikroTik) — prasyarat eksternal.
- Probe WG interface nyata + `wg-quick@wg0` — langkah ops host (BLOCKED di sandbox).
- CI e2e job di GitHub Actions belum ditambahkan (harness lokal hijau; caching browser CI = pekerjaan lanjutan).

### Langkah berikutnya
1. M6/M7 billing/ledger R2 (P2; docs/FINANCE.md) — slice vertikal berikutnya.
2. CI job e2e (opsional, hati-hati flakiness).
3. Ops host Gate A/G → `adopt_wg_host` + `probe_wg` + render pada host nyata.

## Checkpoint INTEGRATION-1 — Recovery dua agent paralel + konsolidasi beta-0.1 (preserve → audit → port → verifikasi)

**Scope**: master prompt V5. Dua agent bekerja paralel dari baseline `ee15ada`: Agent A mendorong 9 commit ke `main` (konsolidasi M3/M4/M5 + RADIUS nyata), Agent B mendorong 7 commit ke `parallel/beta-be2` (M3 inti + klien API-SSL + installer hardened; push sempat BLOCKED di environment asal, kemudian ter-push ke branch tersebut). Misi: selamatkan seluruh pekerjaan, audit keduanya, konsolidasikan tanpa duplikasi backend, verifikasi, siapkan beta.

### Pemetaan branch (zero work loss)

| Branch | Isi | Status |
|---|---|---|
| `main` (`cd5142c`) | 9 commit Agent A: M3 penuh (enrollment/discovery/cutover B0–B6/release-replace), M4 penuh (pelanggan/layanan/CSV/migrasi identitas), M5 (backup/monitoring/approval M2), RADIUS dengan **verifikasi FreeRADIUS nyata 15/15**, guard anti-mock, installer hardened | Diverifikasi ulang sesi ini: 207/207 tes + 15/15 RADIUS nyata |
| `parallel/beta-be2` (`c9023e6`) | 7 commit Agent B: enrollment/API-SSL native/facade radius multi-tenant/resolver/CSV subset/installer hardened/BETA_RELEASE_NOTES | Diverifikasi ulang sesi ini: 142/142 tes + smoke live 20/20 |
| `integration/beta-0.1` | Dari `origin/main` + port aset unik be2 (lihat bawah) | Kanonis kandidat beta |

Kedua branch dipertahankan apa adanya di remote (tidak ada force-push/reset; `parallel/beta-be2` tidak dihapus).

### Verifikasi ulang baseline (sebelum integrasi — bukan mengandalkan klaim lama)

| Target | Command | Hasil |
|---|---|---|
| main backend | `pytest tests -q` (PostgreSQL 17.11 nyata, peran mtx_migrator/mtx_app) | **207/207 PASS** |
| main RADIUS nyata | `bash scripts/test_radius.sh` (FreeRADIUS 3.2.7 non-root + radclient + relay UDP) | **15/15 PASS** — SETELAH perbaikan grant (lihat bug #1) |
| be2 backend | `pytest tests -q` (PG terpisah port 55433) | **142/142 PASS** |
| be2 smoke live | `bash scripts/smoke_live.sh` (runserver + curl) | **20/20 PASS** |
| main frontend | `tsc -b` / `eslint` / `vitest run` / `VITE_API_MODE=live vite build` | 0 error / 42/42 / build OK |
| docs + i18n | `check_docs.py` / `check_i18n.py` | PASS / parity 908 kunci |

### Bug konsolidasi yang ditemukan & diperbaiki (bukti reproduksi sesi ini)

| Bug | Dampak | Perbaikan |
|---|---|---|
| `grant_runtime` main hanya grant schema `public` | **P0**: peran runtime kehilangan akses schema `radius` pada DB milik migrator → proyeksi RADIUS patah di jalur produksi (tes lolos karena test-DB dimiliki app — terbukti saat `test_radius.sh` BLOCKED "permission denied for schema radius" pada instalasi bersih) | Port logika be2: enumerasi `pg_namespace` dinamis (public+radius+schema baru otomatis); `%I` di-escape `%%I` (psycopg + params). Bukti: revoke→grant→28 grant tabel radius + USAGE |
| `tenant_scope` non-reentrant (reset GUC ke kosong saat keluar scope dalam) | Scope bersarang (view→service, handler→service) memutus konteks scope luar; main hanya mengandalkan konvensi caller-provides-scope | Port be2: simpan nilai sebelumnya + pulihkan saat keluar; tanpa scope luar tetap fail-closed. Regresi test baru `test_nested_scope_restores_outer_context` |
| Klien API-SSL tidak ada di main | Jalur produksi `MT_ROUTEROS_ADAPTER` tidak tersedia — semua verifikasi hanya simulator | Port be2 utuh: `apiclient.py` (protokol biner + TLS + pin SHA-256 + bounded + anti-SSRF) + `cert_pin` RouterContext + factory `MT_ROUTEROS_ADAPTER=simulator\|api_ssl` + 14 tes (server TLS in-process). Mutasi menolak jujur `*_pending_lab` (gate G1) |
| Installer tanpa infrastruktur WireGuard host (§9.13) | Keypair host + wg0.conf tidak disiapkan; MT_WG_SERVER_PUBKEY tidak terpublikasi | Port be2: `setup_wireguard()` idempoten (key lama dipertahankan; private 600 via berkas) + exit code PARTIAL=3 |
| `dev_bootstrap.sh` be2 masih `BACKEND="$ROOT/backend"` | Skrip be2 gagal langkah 5 (main sudah punya fix) | Tidak di-port — versi main lebih benar |

### Keputusan konsolidasi (apa yang TIDAK di-port dari be2, dan alasannya)

| Item be2 | Keputusan | Alasan |
|---|---|---|
| `domains/access/*` (app AAA terpisah: models/resolver/services/views + migrasi 0001–0003) | **Tidak di-port** | Duplikasi domain `radius` milik main (master prompt §17: jangan dua versi backend). Versi main lebih lengkap (cutover B0–B6, reconciler, harness verifikasi nyata 15/15) dan punya bukti FreeRADIUS real |
| `domains/network/enrollment.py` + migrasi 0003–0005 be2 | **Tidak di-port** | main punya evolusi schema lebih jauh (migrasi 0003–0008: token_ref, enroll_bridge_policy, peer) + alur lengkap; migrasi be2 akan merusak dependency graph |
| `domains/customers/csv_import.py` + migrasi be2 | **Tidak di-port** | main memilikinya dalam `customers/services.py` + alur migrasi identitas (discovery→konflik→merge/keep_one/rename) yang lebih lengkap |
| `backend/infra/freeradius/*` (template statis) | **Tidak di-port** | main punya `render_radius_config` (management command) yang menghasilkan konfigurasi setara dari data nyata + sudah diverifikasi `freeradius -C` |
| Guard vite be2 (varian `enforce: 'pre'`) | **Tidak di-port** | main sudah punya gate setara (terverifikasi: build tanpa live DITOLAK sesi ini) |
| `docs/BETA_RELEASE_NOTES.md` | **Diarahkan ke dokumen kanonis baru** | Master prompt §14 minta `BETA_RELEASE_STATUS.md`; isi materialnya diserap ke sana + matriks kepatuhan |

### Verifikasi hasil integrasi (integration/beta-0.1)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (PG 17.11 nyata) | 0 | **222/222** = 207 main + 1 regresi scope-bersarang + 14 API-SSL |
| `python manage.py check` | 0 | tidak ada isu |
| `bash scripts/test_radius.sh` (fresh: grants dicabut dulu, hanya via `grant_runtime` baru) | 0 | **15/15 PASS** — jalur fresh-install RADIUS utuh tanpa intervensi manual |
| `tsc -b` / `eslint src` / `vitest run` | 0 | 0 error / 42/42 |
| `VITE_API_MODE=live vite build` / tanpa live | 0 / ≠0 | build live OK; build mock DITOLAK |
| `bash -n instalasi.sh` + `shellcheck -S error` | 0 | sintaks OK; 0 error shellcheck (warning minor pra-ada: var tak terpakai) |
| Dry-run installer di sandbox | ≠0 | **preflight menolak benar** (disk 8GB < 10GB minimum — gerbang bekerja) |
| `python3 docs/tools/check_docs.py` | 0 | PASS |

Lingkungan: Debian 13 sandbox; Python 3.13.5; PostgreSQL 17.11 (binary deb non-root + shim share-path); FreeRADIUS 3.2.7 + radclient (deb trixie, non-root); Node 24 + pnpm 12.16.1. **Tanpa perangkat MikroTik fisik / host root / domain publik** — bukti verified_lab tetap BLOCKED sesuai gate G1.

### Blocker / keterbatasan beta (jujur — tidak berubah dari BE-2 kecuali yang diperbaiki)

- Perangkat MikroTik fisik tidak tersedia → enrollment/discovery/cutover/API-SSL tetap jalur simulator pada default; T01/T10/T17 belum verified_lab.
- WireGuard host: installer kini menyiapkan keypair + wg0.conf + env; **aktifasi interface** (`systemctl enable --now wg-quick@wg0`) dan adopsi keypair oleh model `WireGuardHost` backend = langkah ops berikutnya (belum otomatis penuh).
- Instalasi produksi nyata (host Debian 13 + root + domain) belum dieksekusi — Gate A/G terbuka.
- B3/B4 cutover menunggu jendela observasi nyata dengan NAS produksi.
- Playwright e2e belum dibangun (smoke live sebagai pengganti terbatas).

### Langkah berikutnya

1. PR `integration/beta-0.1` → main (CI: backend/frontend/docs) → merge → tag `v0.1.0-beta.1` (RC).
2. Lab MikroTik CHR/fisik untuk G1 (T01/T16–T18/T20–T21) → baru aktifkan `MT_ROUTEROS_ADAPTER=api_ssl` dan cutover B3–B5.
3. Eksekusi instalasi.sh pada host Debian 13 root + domain (Gate A/G) — dokumentasikan hasil gate.
4. Adopsi keypair WG installer oleh backend + probe handshake.
5. M6/M7 billing/ledger R2 sesuai roadmap.

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
