# Independent Review — Phase-1 WireGuard Router Onboarding (secure enrollment slice)

- Reviewer: sub-agent independen (security & contract review, read-only terhadap kode)
- Tanggal: 2026-11-06T19:46:38Z (UTC)
- Branch: `main` @ 7d600146bd643b48f41b71ce5412c8d5abb89e06 — **diff belum di-commit** (working tree, 19 file, +920/−133, +3 file baru)
- Dokumen acuan: CONTRACT.md (§3, §8, §9), docs/ROUTEROS.md §1–§2, master directive P0 onboarding
- Verdict: **REQUEST_CHANGES** (0 P0, 2 P1, 9 P2) — dua P1 berada tepat pada klaim inti slice (retry jujur & konten skrip §2.2), keduanya perbaikan kecil dan terisolasi; fondasi slice (isolasi tenant, kejujuran simulator, kompatibilitas API, konfigurasi fail-closed) sudah benar.

## Ringkasan temuan

### P1 (should-fix sebelum integrasi)

1. **Retry `verify_api_ssl` efektif mati — klaim "bounded retry" tidak benar.**
   `handlers.py:46-49` menolak status selain `BOOTSTRAPPED` (non-retryable), namun
   `handlers.py:51-52` sudah mempersist `status=VERIFYING` **sebelum** probe dijalankan.
   Urutan kejadian pada adapter `api_ssl`: attempt-1 probe gagal → `JobError(retryable=True)`
   (`handlers.py:58-63`) → `RETRY_WAIT` → attempt-2 langsung `JobError(enrollment_state,
   retryable=False)` → job `FAILED` permanen. Enrollment tertinggal di `verifying`:
   `create_enrollment` memblokir `router_code` sama selama status `verifying`
   (`services.py:276-279`) dan tidak ada endpoint cancel/recovery → tenant terkunci
   tanpa jalur keluar. Docstring handler sendiri mengklaim "retry bounded max_attempts"
   (`handlers.py:26-27`) — klaim itu tidak teruji (tidak ada tes untuk
   `api_ssl_unreachable`). Jalur simulator (default beta) tidak pernah memicunya;
   jalur produksi (`MT_ROUTEROS_ADAPTER=api_ssl`, pasca-lab G1) selalu memicunya pada
   kegagalan transien pertama.
   **Fix (satu baris):** guard menerima re-entry — `if enrollment.status not in
   (BOOTSTRAPPED, VERIFYING): raise ...` (idempoten; `finalize_verification` atomik),
   atau kembalikan status ke `BOOTSTRAPPED` pada kegagalan retryable. Tambah tes
   integrasi kegagalan probe → retry → sukses.

2. **Callback skrip `/tool/fetch` tanpa `check-certificate=yes` — melanggar ROUTEROS.md §2.2 pada sisi router.**
   `services.py:454-455` (template `_ROUTEROS_WG_TEMPLATE`): `/tool/fetch url="https://{GATEWAY}/..."` tidak memuat
   `check-certificate`. §2.2 mensyaratkan "Validasi token dan HTTPS server dengan
   hostname/CA/waktu benar sebelum langkah privileged". Default `check-certificate`
   RouterOS fetch adalah **no** (dokumentasi vendor — INFERENCE, perlu konfirmasi lab G1),
   sehingga token one-time dikirim pada kanal TLS yang tidak mengautentikasi server →
   MITM pada jalur WAN router dapat mencuri token dan menyelesaikan enrollment dengan
   kunci publik milik penyerang (mendapat identitas peer + /32 tunnel). Prinsip repo yang
   sama pada backup ("Tidak boleh ignore host verification diam-diam", ROUTEROS.md §5)
   berlaku juga di sini. Skrip lama pun tanpa flag ini, namun template skrip DIKETIK
   ULANG penuh pada diff ini sehingga gap ini berada dalam scope; tidak ada catatan gap
   terdokumentasi (CONTRACT §2: missing implementation = documented gap).
   **Fix:** tambah `check-certificate=yes` pada fetch + dokumenkan prasyarat SNTP/CA
   (waktu router benar §2.2), atau catat gap eksplisit + kontrol kompensasi; verifikasi
   perilaku aktual di lab G1.

### P2 (nice-to-have)

3. **`api_cert_fingerprint` tetap sintetis pada jalur api_ssl.**
   `services.py:812` menurunkan fingerprint dari `token_hash[:32]` (pre-existing), padahal
   jalur api_ssl kini memegang fingerprint TERAMATI `probe["cert_sha256"]`
   (`apiclient.py:250-256`). Field didokumentasikan sebagai "Fingerprint sertifikat
   API-SSL yang dipin dari enrollment complete" (`models.py:46`) — jika jalur login
   kelak memakainya sebagai `cert_pin` (`base.py:28`), pinning akan selalu mismatch.
   Bukti teramati memang tersimpan di `capability.probe` + `device_identity.probe`
   (jujur), tetapi field-nya menyesatkan; `enrollment_progress` juga memakai
   kebenaran field ini untuk state `discovery_ready` (`services.py:312`).
   **Fix:** jalur api_ssl menyimpan `probe["cert_sha256"]`; jalur simulator diberi
   penanda sintetis yang eksplisit.
4. **Bug paritas mock:** `adapter.ts` (mock createEnrollment) memakai
   `.replace(/^vV/, '')` — regex literal "vV", bukan karakter kelas `[vV]+`.
   Input "v7.15.3" → mock 422 `invalid`, backend 201 (normalisasi "7.15.3").
   Kode 422 lain paritas (`unsupported`, `wireguard_requires_v7`) sudah sama.
5. **Migrasi 0010 berpotensi gagal pada data beta/dev existing** —
   `AddConstraint uq_wgpeer_pubkey_active` (migrations/0010:24-27) akan error bila ada
   dua peer AKTIF ber-`public_key` sama (mis. hasil uji replay lintas /32 berbeda).
   Tidak ada pre-check/dedupe. Reasoning-only (migrasi tidak dijalankan reviewer).
   Saran: cek dedupe pra-migrasi atau dokumentasikan risiko pada runbook upgrade.
6. **`_validate_gateway_hostname` longgar** (`services.py:468-469`): literal IPv4
   diterima tanpa validasi oktet (999.999.999.999 lolos) dan tanpa tolak rentang
   privat/reserved — padahal semantik kunci adalah hostname gateway PUBLIK.
   Saran: parse via `ipaddress.IPv4Address` + tolak private/reserved.
7. **Gate versi WireGuard hanya bandingkan major** (`services.py:261`): "7.0" lolos
   padahal pesan (dan riset) menyatakan butuh 7.1+. Bandingkan minor juga.
8. **Langkah "Menunggu verifikasi" tanpa pesan kegagalan** — state `conflict`/`expired`
   hanya menampilkan ikon merah pada stage-0 (`RouterNewPage.tsx:379-391`); jalur gagal
   baru terjangkau nyata lewat kegagalan api_ssl (P1-1). Tambah teks + CTA (buat ulang).
9. **Observasi pre-existing yang berada dalam jalur yang diubah** (bukan regresi diff,
   dicatat untuk follow-up): (a) GUC `app.enroll_bridge` on/off tanpa try/finally
   (`services.py:715-718`) — bocor ke koneksi pooled bila query di tengah raise;
   (b) `ENROLL_TOKEN_TTL_S=24h` hardcoded (`services.py:46`) tidak membaca
   `enroll.token_ttl_s` (defaults.json:65-78, default 900s) — copy UI "kedaluwarsa
   15 menit" understates jendela sensitivitas token (token tetap konsumable 24 jam);
   (c) `/interface/wireguard/peers/remove [find interface=$iface]`
   (`services.py:438`) menghapus SEMUA peer pada interface — aman selama nama
   `mtx-wg` platform-unique, tapi melanggar semangat §2.3 bila interface bernama sama
   sudah ada milik pihak lain; (d) `print("BRIDGE_BODY:", ...)` sisa debug
   (`test_enrollment_flow.py:93`); (e) GET bootstrap (berisi token) tanpa
   `Cache-Control: no-store` (`views.py:147-152`).

## Jawaban eksplisit checklist (bukti per butir)

**1. Security — secrets**
- Token: hash SHA-256 saja untuk lookup (`services.py:219-220`); plaintext TERENKRIPSI
  SecretBox selama TTL (`services.py:291`, AES-256-GCM `crypto.py:33-49`); dikosongkan
  saat konsumsi atomik (`services.py:747`); di BODY callback bukan URL
  (`services.py:451-455`, `views.py:222-237`); GET skrip dibatasi pembuat
  (`views.py:149-151`); payload job hanya `enrollment_id` (`services.py:771-775`);
  tidak ada pencatatan token ke log/analytics. Replay identitas sama = hasil logis sama,
  identitas beda = 409 (`services.py:728-736`) — §2.7 terpenuhi. TTL terbatas 24 jam
  (bounded), namun lihat P2-9b (inkonsistensi dengan defaults.json 900s).
- API password: `SecretBox.encrypt(f"{code}\x00{password}")` (`services.py:845`) —
  **konsisten** dengan parser `apiclient._credentials` (`apiclient.py:221-222`,
  `partition("\x00")` → `rtrw-ro-{code}`). Format LAMA
  (`apiuser=...;password=...`) justru tidak parseable — diff ini MEMPERBAIKI
  inkonsistensi tersebut. Password CSPRNG per-router unik
  (`secrets.token_urlsafe(24)`, `services.py:811`).
- Private key: tidak pernah dibaca skrip (baris `:local privkey` dan artefak SCEP
  hilang — diverifikasi grep + asersi `test_enrollment_flow.py` "scep"/":local privkey"
  tidak ada); interface dibuat tanpa `private-key` → RouterOS membangkitkan sendiri
  (konfirmasi vendor di report/researcher §1 "automatically generated upon interface
  creation"); host private key tetap di root (models.py:142-175).
- Skrip hanya membocorkan token one-time (inheren desain, diakui §2.2) — dengan caveats
  P1-2 (kanal) dan P2-9b (jendela TTL copy).

**2. Tenant isolation**
- `uq_wgpeer_pubkey_active` partial unique `public_key WHERE state != 'removed'`
  (models.py:203-213; migrasi 0010:24-27) — blokir reuse kunci lintas tenant pada
  level DB (RLS-independent). 409 `wg_public_key_registered` tanpa detail lintas tenant
  (`services.py:766-767`); enrollment tetap DRAFT (rollback transaksi, ditegaskan tes
  `test_duplicate_public_key_cross_tenant_409`).
- `allocate_tunnel_ip()` (`services.py:192-216`): iterasi per-tenant via `tenant_scope`
  (pola `_any_active_peer`) — BENAR di bawah RLS karena `tenancy_tenant` TIDAK
  ber-RLS (enumerasi tenant lengkap; verifikasi migrasi tenancy/network 0002/0004),
  dan `tenant_scope` reentrant dengan restore nilai luar (`tenant_context.py:33-68`).
  Race antar-create ditangkap unique constraint DB (tunnel_ip unique) → IntegrityError
  jujur (bukan pelanggaran senyap).
- Keterlihatan `tunnel_ip` global (unique=True) + pubkey global → keunikan kredensial
  per-router sesuai directive.

**3. Script correctness & safety (ROUTEROS.md §2)**
- Endpoint = gateway PUBLIK dari konfigurasi, TIDAK PERNAH IP tunnel
  (`services.py:381,440`; tes regresi menolak `endpoint-address="100.127.0.1"`).
- Port server dari state: `endpoint-port={WG_PORT}` ← `host.listen_port`
  (`services.py:389`), `dst-port={API_PORT}` ← `enrollment.api_port` (services.py:390);
  listen-port 13231 sisi router = default RouterOS (riset) — konstan yang tepat.
- allowed-address hanya /32 server (`services.py:441`); firewall input hanya
  API-SSL tcp dari /32 server pada interface manajemen, place-before=0, comment
  rtrw-mgmt-api (`services.py:447-450`); tanpa reset/reboot/route/NAT/DHCP/bridge/DNS.
- Private key ON-router ✓ (butir 1). Token di POST body ✓. Idempoten: find-guard
  interface/alamat/firewall; re-run script dalam TTL → callback replay = hasil logis
  sama tanpa duplikasi peer (update_or_create by allowed_ip) ✓; setelah token
  dikonsumsi, render skrip ditolak `token_issued_once` (`services.py:371-373`).
- **Tidak dapat diverifikasi reviewer:** sintaks RouterOS aktual (kontinuasi `\\`,
  path `/interface/wireguard/peers/*`, semantik fetch) — butuh lab G1; klaim apa pun
  di luar simulator TIDAK disetujui. Celah §2.2 `check-certificate` = P1-2.

**4. Verification honesty**
- Simulator: capability `source=simulator, verified_lab=False, api_ssl=False,
  wireguard=False` + note (`services.py:813-821`) — tidak ada klaim terhubung; UI
  banner peringatan pada step Siap (`RouterNewPage.tsx:406-409`) + baris sumber di
  detail (`RouterDetailPage.tsx:234-252`) + normalisasi `verification` di API
  (`views.py:79-91`, `services.py:336-341`).
- api_ssl: probe TCP+TLS NYATA via `apiclient.probe_connectivity` SEBELUM Router dibuat
  (`services.py:795-810`; handshake + fingerprint teramati `apiclient.py:235-256`);
  gagal → raise (`UnreachableError`) → JobError retryable — TANPA penyelesaian palsu
  (job FAILED jujur). Simulator `probe_connectivity` mengembalikan
  `performed=False` (`simulator.py:108-115`) — tidak pernah mengklaim probe nyata.
  Handler memakai `active_adapter_name()` (`handlers.py:53-55`) ✓.
- Handler `verify()` mengecek router+credential+peer APPLIED (`handlers.py:66-74`) ✓.
- Tidak ditemukan tempat lain menandai router terverifikasi tanpa bukti (satu-satunya
  penulis capability = `finalize_verification`, grep terbatas services.py:814/823).
- **Catatan:** klaim "bounded retry" dibatalkan oleh P1-1; `stage_detail` all-ok pada
  flow simulator (pre-existing) kontradiktif dengan verification.api_ssl=False —
  banner memperbaiki kejujuran tingkat UI, state machine belum (lihat P2-3/P2-8).

**5. Config**
- Rantai `gateway_hostname()`: registry `vpn.gateway_hostname` (env
  `MT_OVERRIDE_VPN__GATEWAY_HOSTNAME`, nilai JSON string, tervalidasi string oleh
  `_validate` registry.py:86-87) → `MT_PUBLIC_HOST` → `MT_DOMAIN` → dev/test
  fallback `microtix.invalid` (RFC 2606, tidak resolvable) → produksi 409
  `gateway_hostname_unconfigured` (`services.py:475-501`) — fail-closed, TIDAK ada
  endpoint salah senyap. Validasi menolak scheme/port/path/spasi (tes
  `test_gateway_hostname_rejects_url_like_values`). defaults.json: entri well-formed
  (type string, nullable true, default null, bounds null, scope deployment; file valid
  JSON, 115 parameter, revision 2.3, tanpa duplikat — diverifikasi reviewer via parser).
  Caveat kecil P2-6.
- Overengineering (CONTRACT §3): TIDAK ADA tabel settings Super Admin berbasis DB —
  env/registry yang existing dipakai (keputusan tepat, deferred). Tidak ada dependensi/
  layer baru; `probe_connectivity` pada protokol adapter adalah abstraksi terkecil yang
  dibutuhkan kejujuran verifikasi. Smallest-safe-change terpenuhi.

**6. API compatibility**
- Klien lama tanpa `protocol`/`routeros_version` tetap sah (default `wireguard`/`"7"`,
  `services.py:245,256`; tes `test_legacy_payload_without_protocol_still_valid`).
- Response hanya ADDITIVE: `request.protocol/routeros_version` (views.py:115-116),
  progress `protocol/routeros_version/verification`, bootstrap
  `protocol/routeros_version/gateway`, detail `verification`. Tidak ada field dihapus
  atau bentuk berubah. Tes OpenAPI path-based (render live + aserti keberadaan path,
  test_api_contract.py:9-18) — tanpa snapshot, tanpa breakage.

**7. Migration 0010**
- AddField `protocol` (default 'wireguard', NOT NULL) dan `routeros_version` (blank
  default '') aman pada data existing. AddConstraint `uq_wgpeer_pubkey_active`
  berisiko gagal bila data beta/dev memuat duplikat pubkey AKTIF (P2-5) — reasoning
  only; migrasi TIDAK dijalankan reviewer.

**8. Frontend**
- Picker jujur: WireGuard aktif hanya v7; SSTP/L2TP/OpenVPN disabled + alasan
  "Direncanakan" (`RouterNewPage.tsx:204-285`); v6 memblokir Lanjutkan +
  `disabledReason` (`RouterNewPage.tsx:87-88,287-292`).
- Baris gateway dirender dari `scriptQ.data.gateway` (meta backend) — BUKAN string
  frontend (`RouterNewPage.tsx:338-347`).
- Banner simulasi pada step Siap + baris "Sumber verifikasi" di detail ✓.
- Mock: kode 422 paritas backend (unsupported/wireguard_requires_v7/invalid) ✓,
  kecuali bug normalisasi `v`-prefix (P2-4); fixture skrip mock kini meniru bentuk
  skrip nyata TANPA radius/secret pura-pura (perbaikan kejujuran vs fixture lama).

**9. Tests**
- Tes baru menyatakan PROPERTI (bukan sekadar bentuk): kejujuran capability
  (api_ssl/wireguard/verified_lab False + note), regresi endpoint-bukan-IP-tunnel,
  tanpa-SCEP/tanpa-privkey, duplikasi kunci lintas tenant → 409 + enrollment tidak
  berubah diam-diam, kompatibilitas klien lama, echo normalisasi versi, override
  registry gateway, penolakan nilai URL-like, detail `verification`.
- Pelemahan asersi existing: SATU-SATUNYA perubahan pada tes existing =
  `test_registry_pagination.py` 114→115 + revision 2.2→2.3 (terdokumentasi, sesuai
  tambahan kunci defaults.json). Diff tes lain murni aditif (+226 baris) — tidak ada
  asersi dilemahkan; asersi lama (source simulator, verified_lab False) tetap lulus
  dengan bentuk capability baru.
- e2e `routers.spec.ts` mengendarai backend NYATA: login nyata → bridge POST dengan
  token dari skrip + header CSRF (meniru /tool/fetch) → worker NYATA
  (`runworker --loop`, run.sh:60-66) → banner SIMULATOR ditegaskan
  (routers.spec.ts:55-73) + `verification-source` berisi "Simulasi" di detail.
- Gap: tidak ada tes jalur retry/kegagalan probe (terkait P1-1).

**10. instalasi.sh**
- MT_DOMAIN passthrough: cabang create menambah `MT_DOMAIN=${MT_DOMAIN:-}` pada heredoc
  (instalasi.sh:184); cabang upgrade append-if-missing dengan guard `[ -n ... ]` +
  `grep -q '^MT_DOMAIN='` (instalasi.sh:159-161) — idempoten, tanpa menimpa nilai lain,
  no-op bila MT_DOMAIN unset (tidak ada perubahan perilaku), MT_DOMAIN bukan rahasia
  (hostname publik, sudah tercetak di ringkasan installer) — tanpa regresi secret.

## Apa yang diverifikasi & tidak dapat diverifikasi

Diverifikasi reviewer (tanpa DB, tanpa mutasi kode):
- `git diff`/`git status` penuh; pembacaan seluruh file yang berubah + file baseline via `git show`.
- **tsc --noEmit: 0 error**; **vitest run: 66/66 lulus** (termasuk 5 tes RouterNewPage baru).
- AST-parse Python lulus untuk 9 file backend yang berubah.
- defaults.json ter-parse: 115 parameter, revision 2.3, tanpa kunci duplikat.
- Grep: tanpa TODO/FIXME/debug-print/markdown-simbol pada kode baru; tanpa kredensial
  hardcoded baru (SEEDED_OWNER e2e = dev-seed env-overridable, pre-existing).

TIDAK dapat diverifikasi (jangan menjadikan bukti):
- Sintaks/semantik skrip pada RouterOS NYATA dan default `check-certificate` fetch —
  butuh lab G1 (semua klaim perangkat nyata tetap VERIFIED_SIMULATOR sampai itu).
- Eksekusi migrasi 0010 pada data existing (butuh DB).
- Suite backend pytest (butuh PostgreSQL) dan e2e Playwright (butuh backend+DB+browser)
  — tidak dijalankan reviewer; hasil orchestrator menjadi bukti terpisah.
- Perilaku real pada `MT_ROUTEROS_ADAPTER=api_ssl` (probe/pin/login) — belum ada lab.

## Langkah berikutnya yang disarankan

1. Perbaiki P1-1 (guard re-entry VERIFYING + tes retry probe) dan P1-2
   (`check-certificate=yes` + prasyarat SNTP/CA atau gap terdokumentasi).
2. Pertimbangkan P2-3 (fingerprint teramati pada jalur api_ssl) dan P2-4 (regex mock)
   pada diff yang sama (satu baris masing-masing).
3. Jalankan suite backend (RLS + integrasi) dan e2e via `apps/web/e2e/run.sh` sebagai
   bukti integrator; catat hasil di laporan sesi.
4. Simpan temuan lab-pending (sintaks skrip, fetch cert, SNTP) sebagai item gate G1
   eksplisit agar tidak hilang saat slice berikutnya.

---

## Disposisi orkestrator (pasca-review, 2026-11-07)

Verdict awal reviewer: REQUEST_CHANGES (0 P0, 2 P1, 9 P2). Disposisi:

| Temuan | Disposisi | Bukti |
|---|---|---|
| **P1-1** retry `verify_api_ssl` terkunci (`enrollment_state` non-retryable pada re-entry VERIFYING) | **DIPERBAIKI** — guard kini menerima `BOOTSTRAPPED` **atau** `VERIFYING` (handlers.py:47-56); docstring diluruskan; tes baru `test_probe_failure_retries_then_completes_with_observed_pin` membuktikan: attempt-1 gagal → `retry_wait` + enrollment tetap VERIFYING; attempt-2 re-entry sukses → COMPLETED dengan pin teramati | `backend/tests/integration/test_enrollment_flow.py::TestApiSslVerificationPath`; backend 373/373 |
| **P1-2** `/tool/fetch` tanpa `check-certificate` (token terekspos MITM; ROUTEROS.md §2.2) | **DIDOKUMENTASIKAN sebagai gap lab-G1 + PROPOSED** — mengaktifkan `check-certificate=yes` tanpa bukti lab berisiko mematikan onboarding pada perangkat nyata (RouterOS tidak membawa bundel CA lengkap secara bawaan; perlu import CA/SNTP — INFERENCE vendor-doc). Komentar gap ditambahkan langsung pada skrip (services.py template §5); dampak dibatasi token sekali pakai + TTL 15 mnt + konsumsi atomik. Item gate G1 eksplisit dicatat di laporan orkestrator + BETA_RELEASE_STATUS | services.py `_ROUTEROS_WG_TEMPLATE` §5; docs/BETA_RELEASE_STATUS.md Known limitations |
| P2-3 fingerprint sintetis padahal teramati tersedia | **DIPERBAIKI** — jalur api_ssl memakai `probe["cert_sha256"]` sebagai pin (services.py finalize_verification) | tes pin teramati di atas |
| P2-4 paritas mock `replace(/^vV/,'')` vs `lstrip("vV")` | **DIPERBAIKI** — `/^[vV]+/` | apps/web/src/api/mock/adapter.ts |
| P2 validasi IPv4 longgar (oktet > 255) | **DIPERBAIKI** — oktet divalidasi 0-255 | services.py `_validate_gateway_hostname` |
| P2 gate minor 7.0 | **DIPERBAIKI** — `wireguard_requires_v7_1` (backend + mock paritas) | create_enrollment; mock adapter |
| P2 migrasi 0010 AddConstraint pada data duplikat existing | **DITERIMA RISIKO** — DB beta; duplikat pubkey aktif akan menggagalkan migrasi dengan pesan eksplisit (bukan diam-diam); dicatat di laporan orkestrator | — |
| P2 GUC `enroll_bridge` tanpa try/finally | **PRE-EXISTING, DI LUAR SCOPE** — dicatat sebagai item tindak lanjut (tidak dilemahkan oleh diff ini) | — |
| P2 `peers/remove` menghapus semua peer interface | **PERILAKU TERSEAJA** — interface `mtx-wg` dimiliki platform; remove-lalu-add = idempotensi retry; dikomentari pada skrip | services.py template §2 |
| P2 langkah Menunggu tanpa pesan gagal / debug print pre-existing | **DICATAT** sebagai P2 masa depan | — |

Verifikasi ulang pasca-perbaikan (orkestrator): backend **373/373** (PostgreSQL 17.11 nyata),
FreeRADIUS nyata **15/15**, FE tsc/eslint 0 + vitest **66/66** + i18n paritas 1062 + build live
OK (build mock tetap DITOLAK guard), `make e2e` **12/12** (backend+worker NYATA).
