# Laporan Orkestrator — Phase-1: Onboarding Router Aman (WireGuard) + Kesinambungan Beta

- **Role**: GLM main orchestrator (sesi tunggal aktif — CONTRACT §5).
- **Sesi**: 2026-11-06T18:16Z s.d. 2026-11-06T19:56Z (UTC).
- **Baseline**: `main` @ `7d600146bd643b48f41b71ce5412c8d5abb89e06` (clone bersih,
  terverifikasi `git fetch --all --prune`; working tree bersih saat mulai).
- **Direktif user (otoritas produk)**: master prompt "MicroTix Secure Router
  Connectivity & Beta Continuation" — P0 onboarding MikroTik aman + arsitektur
  multi-protokol shared-port + perlindungan rilis beta. Diposkan langsung oleh
  pemilik repo di kanal sesi (bukan file); tidak mengubah dokumen normatif tanpa
  approval — semua amendment teknis dicatat **PROPOSED** di bawah.
- **Dokumen acak**: CONTRACT.md (v `1fff190`), ROUTEROS.md §1–§4, ARCHITECTURE §4/§6,
  UI_UX §7, defaults.json (rev 2.2→2.3), BETA_RELEASE_STATUS, ACCEPTANCE,
  LATEST_HANDOFF 2026-11-06 lanjutan 4.

## 1. Pemetaan requirement → implementasi → tes → bukti

| Kebutuhan (direktif §) | Implementasi | Tes | Bukti |
|---|---|---|---|
| §9 Alur: Tambah Router → versi → protokol → preview → copy → paste → verify | Wizard U05 ada; +pemilih versi RouterOS (v7/v6) & protokol (WireGuard aktif; SSTP/L2TP/OpenVPN disabled berlabel "direncanakan") di langkah Identitas; baris endpoint gateway + skrip di langkah Skrip; polling → Siap | `RouterNewPage.test.tsx` (5) + e2e `routers.spec.ts` (2) | vitest 66/66; e2e 12/12 |
| §9 Skrip dibangkitkan BACKEND dari state tervalidasi (bukan string FE) | `bootstrap_script()` render dari WireGuardHost + enrollment + gateway config; FE hanya menyalin | `test_bootstrap_script_*` | 373/373 |
| §9 Endpoint publik + §6 gateway hostname terkonfigurasi | `gateway_hostname()`: registri `vpn.gateway_hostname` (defaults.json rev 2.3) → `MT_PUBLIC_HOST` → `MT_DOMAIN` → dev/test `microtix.invalid` → produksi 409 `gateway_hostname_unconfigured`; validasi hostname/IPv4 (tanpa scheme/port/path; oktet 0-255) | `test_bootstrap_script_uses_public_gateway_not_tunnel_ip`, `..._gateway_override_via_registry`, `test_gateway_hostname_rejects_url_like_values` | idem |
| §9 Sintaks benar utk versi terpilih; idempoten; tanpa reset/route/NAT/DHCP/bridge/akun; firewall minimal; private key router; token body; expiry bootstrap | Template `_ROUTEROS_WG_TEMPLATE` (v7): hapus artefak SCEP + baris `:local privkey` rusak; port dari state; allowed-address /32 server; rule input API-SSL hanya dari /32 server; token di body POST; TTL skrip 900 s; komentar gap G1 pada callback | `test_bootstrap_script_uses_public_gateway_not_tunnel_ip` (assert tanpa `scep`, tanpa `endpoint-address="100.127.0.1"`) | idem |
| §10 False-positive verification dimatikan; §10 state terpisah | `capability.source` = adapter AKTIF; simulator ⇒ `api_ssl/wireguard=False` + note; `verification` ternormalisasi di progress + detail router; UI banner/chip "Simulasi" | `test_capability_honest_no_real_connection_claim`, `test_progress_verification_labeled_simulator`, `test_router_detail_verification_field` | idem |
| §10 Verifikasi nyata (jalur api_ssl) | `probe_connectivity()` TCP+TLS NYATA ke tunnel IP sebelum Router dibuat; pin = fingerprint TERAMATI; gagal → JobError retryable (re-entry VERIFYING, bounded `max_attempts=5`) | `test_probe_failure_retries_then_completes_with_observed_pin` | idem |
| §7 Isolasi: kredensial/kunci unik per router | `uq_wgpeer_pubkey_active` (partial unique, peer AKTIF) + 409 `wg_public_key_registered` lintas tenant tanpa bocoran | `test_duplicate_public_key_cross_tenant_409` | idem |
| §7 Keunikan IP tunnel global (bug RLS) | `allocate_tunnel_ip()` kumpulkan IP terpakai lintas tenant via iterasi scope (konvensi `_any_active_peer`) | test RTR-DUP (memicu kasusnya) + 373 suite | idem |
| §6 Konfigurasi non-rahasia via mekanisme yang ada | defaults.json `vpn.gateway_hostname` (rev 2.3; +1 param → 115) + env; TIDAK ada tabel setting baru (anti-overengineering — lihat §3 keputusan) | `test_registry_loads_all_parameters` (114→115 terdokumentasi) | idem |
| §13 Phase 1 "Preserve API compatibility" | Field baru opsional (default wireguard/"7"); respons additive-only; klien lama sah | `test_legacy_payload_without_protocol_still_valid` | idem |
| §14 Browser onboarding E2E | `routers.spec.ts` + `runworker` proses terpisah di `e2e/run.sh`; callback bridge dengan CSRF seperti SPA | `make e2e` **12/12** (Chromium nyata) | log sesi |
| §11 Installer prasyarat hostname | `MT_DOMAIN` diteruskan ke env aplikasi (heredoc + append-if-missing idempoten; tanpa menyentuh secret) | `bash -n` + reviu reviewer | PASS |
| §8/§16 Riset kapabilitas multi-protokol bersumber vendor | Sub-agent researcher → matriks (WireGuard v7.1+; SSTP klien tanpa EAP — server wajib terima MSCHAPv2; OpenVPN klien v6 TCP-only tanpa NCP; L2TP auto-IKEv1 `main-l2tp`; CHR lisensi) | — | `report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md` |

## 2. Audit awal (paralel, read-only — CONTRACT §5)

- `report/backend-explorer/20261106T182013Z-router-onboarding-audit.md` —
  temuan kunci: skrip memuat `endpoint-address` IP tunnel internal
  100.127.0.1 (salah), callback fallback `microtix.example` (palsu),
  artefak SCEP, port hardcode; `capability` mengklaim `api_ssl/wireguard
  True` tanpa verifikasi nyata; tidak ada field protokol/hostname; peer
  pubkey tidak unik; token/SecretBox/RLS sudah benar.
- `report/frontend-explorer/20261106T181615Z-router-onboarding-ux-audit.md` —
  wizard 5 langkah + copy + polling sudah ada; tidak ada pemilih
  protokol/versi; tidak ada pelabelan simulasi per-item.
- Reviewer independen: `report/reviewer/20261106T194638Z-wg-onboarding-independent-review.md`
  (REQUEST_CHANGES 2 P1 — keduanya diselesaikan/didakumentasikan; disposition
  terlampir di berkas yang sama).

## 3. Keputusan rekayasa (dengan justifikasi CONTRACT §3/§4)

1. **Gateway hostname via registri+env, BUKAN tabel setting Super Admin baru.**
   Kekurangan saat ini: hanya env `MT_PUBLIC_HOST` (tidak pernah diset
   installer) dengan fallback palsu. Alternatif dipertimbangkan: (a) model
   PlatformConfig DB-backed + API tulis Super Admin; (b) registri defaults.json
   + env (dipilih). Alasan: mekanisme konfigurasi yang sudah ada
   (TK-107 registry), kanal konfigurasi beta satu-host = installer env
   (Gate A/G memang mensyaratkan `MT_DOMAIN`); menambah tabel+API tulis untuk
   nilai yang dipakai render skrip = infrastruktur baru tanpa kebutuhan
   terukur (§3). Direktif "Super Admin configuration" (§6) dipenuhi bertahap:
   kini hanya-baca via `GET /meta/config` (sudah ada); API tulis + audit =
   **PROPOSED** untuk Phase-4 bersama protocol enablement (butuh validasi/
   preview/apply/readback/audit/rollback sesuai §6 — jangan ditulis
   tergesa-tesi dari field UI tak tervalidasi).
2. **`protocol` pada RouterEnrollment saja (bukan Router).** Router masih
   secara efektif WireGuard-satu-transport; menambah kolom `Router.protocol`
   sekarang = generalisasi spekulatif (§3). Setelah SSTP nyata (Phase-2)
   menambahkan kolom router murah (satu migrasi additive).
3. **Probe TCP+TLS tanpa login untuk jalur api_ssl.** Login butuh akun API
   platform pada router — skrip v2 (lab G1). Probe jangkauan+pin teramati =
   bukti jujur maksimum yang tersedia TANPA memalsukan login. Kegagalan →
   retry bounded; enrollment tidak pernah "completed" palsu.
4. **Pin = fingerprint TERAMATI (api_ssl) vs sintetis (simulator).** Pin
   sintetis hanya untuk dev/test (diberi label); pin teramati menjadi acuan
   pembandingan koneksi berikutnya (pinning nyata).
5. **`check-certificate` fetch — PROPOSED + gap terdokumentasi.** Mengaktifkan
   tanpa bukti lab berisiko mematikan onboarding nyata (RouterOS tidak membawa
   bundel CA lengkap bawaan — INFERENCE vendor; perlu import CA + SNTP). Gap
   MITM token dibatasi: token 256-bit sekali pakai, TTL skrip 15 mnt, konsumsi
   atomik, hash-only storage. Item gate G1 eksplisit (BETA_RELEASE_STATUS §7).
6. **defaults.json rev 2.2 → 2.3** (+`vpn.gateway_hostname`, 114→115 param) —
   perubahan teknis-aditif terdokumentasi (bukan pelonggaran normatif; rules
   "only add future-feature settings when implemented" dipenuhi — fiturnya
   implementasi sesi ini). Tes hitungan diperbarui mengikuti (tercatat di
   disposition reviewer — bukan pelemahan asersi).
7. **Prioritas sesi**: direktif user P0 mengesampingkan urutan handoff lama
   (TK-701/TK-602) — keputusan pemilik produk eksplisit; tanpa mengubah
   tasks.json (tidak ada field status di tasks.json; progres tetap di
   progress.md sesuai konvensi). Menambah TK baru untuk multi-protokol =
   **PROPOSED** (butuh perubahan dokumen rencana; matriks kapabilitas sudah
   tersedia sebagai dasar).

## 4. Berkas yang berubah

**Backend**: `domains/network/models.py` (+protocol/routeros_version;
+uq_wgpeer_pubkey_active), `services.py` (validasi protokol/versi; skrip v7
baru; gateway_hostname+validasi; alokasi IP lintas-tenant; complete_enrollment
409 pubkey; finalize_verification jujur+probe), `handlers.py` (source adapter
aktif; retry re-entry), `views.py` (echo protokol/versi; `verification`),
`adapters/routeros/{base,apiclient,simulator}.py` (+probe_connectivity;
peer_cert_sha256), `migrations/0010_routerenrollment_protocol_and_more.py`,
`tests/integration/test_enrollment_flow.py` (+3 kelas/14 tes),
`tests/unit/test_registry_pagination.py` (hitungan 115/rev 2.3).

**Frontend**: `api/contracts.ts` (+EnrollmentProtocol/BootstrapGateway/
RouterVerification; field opsional), `api/client.ts` (+EnrollmentProgress
field), `api/mock/adapter.ts` (paritas penuh), `features/routers/
RouterNewPage.tsx` (pemilih versi+protokol; gateway line; banner simulasi),
`features/routers/RouterDetailPage.tsx` (baris sumber verifikasi; filter
cap boolean), `features/routers/RouterNewPage.test.tsx` (baru, 5 tes),
`e2e/run.sh` (+runworker), `e2e/specs/routers.spec.ts` (baru, 2 spec),
`locales/{id,en}/web.json` (+21 kunci → 1062, paritas penuh).

**Docs/ops**: `docs/defaults.json` (rev 2.3 +vpn.gateway_hostname),
`instalasi.sh` (MT_DOMAIN passthrough idempoten), `docs/progress.md`,
`docs/BETA_RELEASE_STATUS.md`, `report/*` (4 laporan sub-agent+disposisi;
laporan ini), `report/LATEST_HANDOFF.md`.

## 5. Verifikasi aktual (perintah, versi, hasil)

Lingkungan: sandbox Debian 13 non-root; PostgreSQL 17.11 (deb-extract via
`docs/tools/setup_env.sh`); Python 3.13.5 venv (uv); pnpm 12.16.1 (corepack);
Playwright Chromium.

| Perintah | Hasil |
|---|---|
| `MT_ENV=test .venv/bin/python -m pytest tests -q` | **373 passed** (359 baseline + 14 baru) |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `bash scripts/test_radius.sh` | **15/15 PASS** (FreeRADIUS+radclient nyata) |
| `pnpm exec tsc -b --pretty false` | 0 error |
| `pnpm exec eslint src --ext ts,tsx` | 0 error |
| `pnpm exec vitest run` | **66/66** (61 + 5 RouterNewPage) |
| `pnpm run i18n:check` | 1062/1062 paritas, placeholder OK |
| `pnpm run build` (tanpa live) | **DITOLAK guard anti-mock** (sesuai desain) |
| `VITE_API_MODE=live pnpm run build` | ✓ built |
| `make e2e` | **12/12** (backend runserver + **runworker** nyata; alur onboarding penuh) |
| `bash -n instalasi.sh` | OK |
| `python3 -m py_compile` (9 file) | OK |

## 6. Keamanan & kompatibilitas

- Token enrollment: hash-only, SecretBox saat TTL, dibersihkan saat konsumsi,
  hanya di body callback — tidak di URL/log/analytics (dipertahankan; direviu).
- Kunci privat WG: tetap dibangkitkan router; skrip tidak pernah membacanya
  (baris rusak lama dihapus).
- Kredensial API-SSL: format `kode\0password` (SecretBox) — kini KONSISTEN
  dengan parser `ApiSslAdapter._credentials` (memperbaiki mismatch lama).
- Isolasi: RLS tak dilemahkan (tidak ada policy/GUC baru); constraint DB baru
  justru MEMPERKETAT (pubkey aktif unik global); 409 lintas tenant generik.
- Kompatibilitas API: additive-only; OpenAPI contract test berbasis path —
  tidak ada path baru.
- Risiko migrasi 0010 pada data existing: `AddConstraint` gagal eksplisit jika
  ada duplikat pubkey aktif (DB beta; dianggap aman — bukan kegagalan senyap).

## 7. Yang TIDAK diverifikasi (jujur — jangan dianggap lulus)

1. **G1 / verified_lab perangkat nyata**: sintaks skrip pada RouterOS v7
   CHR/fisik; `check-certificate` fetch; SNTP/CA; skrip v2 (akun API-SSL);
   handshake WG nyata; dua tenant LAN tumpang tindih pada jaringan nyata.
2. **Gate A/G** (host Debian 13 root + `MT_DOMAIN` + DNS): tetap penahan
   tunggal tag `v0.1.0-beta.1` — tidak berubah (sandbox tanpa root/domain).
3. Live Demo §9 master prompt: belum dimulai (menunggu lab; pola seed demo
   tersedia via `seed_billing_e2e`).
4. Kapasitas alokasi IP tunnel O(tenant) per enrollment — cukup untuk beta;
   dicatat untuk fase 1.000-tenant (CONTRACT §7 capacity target).

## 8. Bloker & langkah eksekusi berikutnya (urut)

1. **Gate A/G** bila host Debian 13 nyata tersedia (instalasi + timer host
   `issue_due_invoices`) — penahan beta tunggal.
2. **Lab G1 (CHR)**: bukti sintaks skrip v7, `check-certificate`+SNTP/CA,
   skrip v2 akun API-SSL, handshake WG, isolasi dua tenant LAN sama →
   aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`.
3. **Phase-2 SSTP** (PROPOSED, menunggu keputusan lanjut direktif): server
   SSTP Debian (MSCHAPv2 — lihat matriks kapabilitas), model shared-port,
   skrip v6/v7, verifikasi TLS+identitas.
4. Alternatif paralel aman: TK-701 ledger M7 / TK-602/607/608/609 (urutan
   handoff lama tetap sah).

## 9. Git

- Branch sesi: `session/2026-11-07-wg-onboarding` dari `main` @ `7d60014`.
- Commit + push + PR + merge: dilakukan setelah laporan ini; status push
  dicatat di `report/LATEST_HANDOFF.md` dengan SHA remote terverifikasi
  (`git ls-remote`). Tidak ada force-push/reset destruktif.
- PAT: hanya di memori sesi (askpass) — tidak pernah di-commit/di-log
  (gitignore `.env`/`*.key`/`secret*.txt`; scan laporan bersih).
