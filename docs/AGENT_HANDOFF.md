# MicroTix — Agent Handoff (AGENT_HANDOFF)

Diperbarui: 2026-11-05, sesi konsolidasi beta-0.1 (master prompt V5).
Dokumen ini adalah titik masuk WAJIB bagi agent berikutnya.

## 1. Aturan pertama

**Mulai SELALU dari `origin/main` terbaru.** Jangan memulai dari branch
pekerjaan lama (`parallel/beta-be2`, `integration/beta-0.1`) — keduanya
arsip riwayat, bukan sumber kebenaran. Sebelum bekerja:

```bash
git fetch origin --prune
git switch main && git pull --ff-only
git log --oneline -5
```

## 2. Status kanonis saat handoff ini ditulis

| Item | Nilai |
|---|---|
| Canonical main | `main` @ **`f575388`** (merge commit PR #2, sesi 2026-11-06; CI hijau: backend+frontend+docs pada f575388; diverifikasi via API). Handoff kanonis sesi terakhir: [report/LATEST_HANDOFF.md](../report/LATEST_HANDOFF.md) |
| Kandidat rilis | `v0.1.0-beta.1` — commit kandidat `1ccf264` (CI hijau). **Tag DITUNDA (§15: NOT_READY)** hingga Gate A/G (instalasi host nyata) lulus; jalankan lalu tag menunjuk commit teruji |
| Basis konsolidasi | `integration/beta-0.1` (dari `cd5142c` = main pra-integrasi) |
| Artefak terverifikasi terakhir | [BETA_TEST_EVIDENCE.md](BETA_TEST_EVIDENCE.md) (222/222 BE, 42/42 FE, RADIUS nyata 15/15, smoke 20/20, docs PASS; CI GitHub hijau pada 8da2c2d) |
| Status rilis | [BETA_RELEASE_STATUS.md](BETA_RELEASE_STATUS.md) — scope aktif/tidak aktif + gate |

## 3. Riwayat dua agent (context — jangan diulang)

- **Agent A** (backend integrator) → 9 commit di `main` (`ee15ada..cd5142c`):
  M3 penuh + M4 penuh + M5 + RADIUS nyata + installer hardened.
- **Agent B** (paralel) → 7 commit di `parallel/beta-be2`
  (`ee15ada..c9023e6`): M3 inti + klien API-SSL + facade radius + installer
  hardened. Push-nya sempat BLOCKED di environment asal, kemudian masuk ke
  branch tersebut.
- **Konsolidator (sesi ini)**: memverifikasi ulang KEDUA branch (bukan
  percaya klaim), lalu mem-port aset unik Agent B ke basis Agent A:
  grant_runtime multi-schema (bug P0), tenant_scope reentrant, klien API-SSL
  + factory `MT_ROUTEROS_ADAPTER`, setup_wireguard installer, exit code 3.
  Alasan lengkap apa yang tidak di-port: [progress.md](progress.md)
  checkpoint INTEGRATION-1.

## 4. Branch yang masih ada (dan maksudnya)

| Branch | Maksud |
|---|---|
| `main` | **Kanonis.** Semua pekerjaan berikutnya di sini (via branch fitur pendek + PR). |
| `parallel/beta-be2` | Arsip pekerjaan Agent B — JANGAN dihapus/ditimpa; jadikan referensi jika perlu bandingkan implementasi alternatif. |
| `integration/beta-0.1` | Arsip jalur integrasi (baseline kandidat beta-0.1). Boleh dihapus setelah tag rilis dibuat, tapi tidak wajib. |

## 5. Task prioritas berikutnya (urutan)

| Prioritas | Task | Catatan |
|---|---|---|
| P0 | **Master directive user "Secure Router Connectivity"** — ~~Phase-1 WireGuard onboarding~~ **SELESAI (sesi 2026-11-07, PR #6)**; ~~Phase-2 SSTP~~ **SELESAI & TERINTEGRASI (sesi 2026-11-07 lanjutan)**: `protocol=sstp` aktif v6.49.x+v7 (v5- 422 jujur); kredensial per-router `SstpAccount` (migrasi 0011 + RLS; username unik global + password CSPRNG SecretBox; revoke saat release/replace); skrip bootstrap v6/v7 — MSCHAPv2 saja, `verify-server-certificate=yes` WAJIB + CA via `/api/v1/bridge/enroll-ca`; bridge sadar-protokol (identitas = username; mismatch 409); `verification.sstp` jujur; server **accel-ppp 1.15.0** build sumber dipin (`backend/scripts/build_accel_ppp.sh`) — TLS 1.2 + AES256-SHA/GCM-SHA384, shared-port `vpn.sstp_listen_port` (defaults rev 2.4), render `render_sstp_config`; installer `setup_sstp` fase-aware `MT_ENABLE_SSTP=1` + unit `microtix-sstp.service`; lab GNS3 minimal `lab/` (2 tenant LAN sama) — **BELUM VERIFIED_LAB**; backend 391/391, FE 67/67, e2e 12/12 | **Phase-3 L2TP/IPsec + OpenVPN** menyusul per fase (matriks kapabilitas tersedia); bukti lab G1 (G1-SSTP/ISO/FETCH) menunggu aset CHR/controller; Gate A/G tetap penahan tag |
| P0 | Eksekusi instalasi produksi nyata: host Debian 13 + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → setelah lulus, **buat tag `v0.1.0-beta.1`** menunjuk commit teruji | Gate A/G; catat hasil gate di BETA_TEST_EVIDENCE.md; ini satu-satunya penahan tag |
| P0 | ~~Verifikasi CI GitHub Actions hijau pada main pasca-merge~~ **SELESAI** (8da2c2d; dan head PR #6 `4ed2145`: backend/frontend/docs hijau) | jobs backend/frontend/docs |
| P1 | Lab MikroTik CHR (atau fisik) untuk G1: jalankan T01/T16–T18/T20–T21 **+ item bukti onboarding Phase-1: sintaks skrip v7, `check-certificate` fetch (+SNTP/CA), skrip v2 akun API-SSL pada router, handshake WG nyata, dua tenant LAN sama** | Setelah lulus: `MT_ROUTEROS_ADAPTER=api_ssl` boleh diuji; cutover B3–B5 dengan NAS nyata |
| P1 | ~~Aktifasi WireGuard host~~ **SEBAGIAN SELESAI (sesi 2026-11-06)**: adopsi keypair installer oleh `WireGuardHost` + render peers host + probe handshake (`adopt_wg_host`/`render_wg_config`/`probe_wg`; installer memanggilnya; 23 tes baru). Sisa: `systemctl enable --now wg-quick@wg0` + probe host nyata = ops host (butuh Gate A/G) | Lihat report/ sesi 2026-11-06 + BETA_RELEASE_STATUS.md batasan 2/4 |
| P1 | ~~Harness Playwright E2E (`make e2e`)~~ **SELESAI (sesi 2026-11-06)**: `make e2e` — Chromium nyata + backend nyata; 7/7 PASS (login happy/error, guard, isolasi tenant, register→verify→login, i18n, mobile). Menemukan + memperbaiki 2 bug nyata: navigasi login non-MFA (FE) + CSRF_TRUSTED_ORIGINS dev-topologi | Spec: `apps/web/e2e/`; jalankan `make e2e` |
| P2 | ~~TK-109 render PDF~~ **SELESAI (sesi 2026-11-06 lanjutan 3)**: `domains.documents` — PDF immutable snapshot + reprint konsisten (T23-I18-02), renderer terbatas jaringan/file (xhtml2pdf 0.2.28, invariant, escape+guard) | report/documents-dev/ sesi terbaru |
| P2 | ~~M6 core engine TK-601~~ **SELESAI (sesi 2026-11-06 lanjutan 3)**: `domains.billing` — paket BIL-02, invoice prepaid/postpaid + snapshot + UNIQUE periode (AC-BIL), payment dua tahap + alokasi + kredit + kwitansi + aging, scheduler `issue_due_invoices`; 355/355 backend | UI U09/U10 lihat baris berikut |
| P2 | ~~TK-604 UI U09/U10~~ **SELESAI (sesi 2026-11-06 lanjutan 4)**: `features/billing` + `features/activation` — U09 tiga tab + periode filter + aging + verifikasi dana dua tahap + PDF; U10 kelayakan nyata + snapshot + validasi per-item + retry aman; release-flag billing/activation aktif; backend: kursor invoice/payment + field service akun + seed_billing_e2e; backend 359/359, FE 61/61, e2e 10/10 | Gap jujur (bukti diperbesar/rekening/Menunggu koneksi): report/orchestrator/20261106T174500Z-tk604-billing-ui.md |
| P2 | Berikutnya (urut): **TK-701 ledger M7** (TK-601 build ada → dependency puas) atau lanjutan M6: TK-602 isolir default-off / TK-607 saldo pembuka / TK-608 dokumen koreksi / TK-609 kolektor; keputusan endpoint bukti transfer (§8) | Ikuti FINANCE.md §16; ops host Gate A/G tetap P0 saat tersedia |
| P3 | ACS R3, OLT/WAN R4 | Jangan dipaksakan sebelum gate |

## 6. Input eksternal yang dibutuhkan (tidak bisa dikerjakan agent sendirian)

1. **Host Debian 13 dengan root + domain publik** (VPS) untuk instalasi nyata.
2. **Lab MikroTik CHR/router fisik + FreeRADIUS reachable** untuk G1.
3. **Domain + DNS** untuk HTTPS publik (Caddy ACME).
4. Keputusan bisnis: harga/konten paket sudah final di docs/PRODUCT.md —
   jangan diubah agent.

## 7. Konvensi yang HARUS dipertahankan

- Kontrak dokumen (docs/) adalah kebenaran: `python3 docs/tools/check_docs.py`
  wajib lulus; JANGAN melonggarkan dokumen agar implementasi lolos.
- Anti-API-palsu (§5): endpoint yang belum diimplementasi → 404 jujur;
  frontend menampilkan status jujur; build produksi wajib `VITE_API_MODE=live`.
- Mutasi router hanya via jalur DISCOVER→VALIDATE→PLAN→PREVIEW→AUTHORIZE→
  APPLY→READBACK→VERIFY→AUDIT; adapter api_ssl menolak `*_pending_lab`
  sampai G1 — jangan "bypass" penolakan ini.
- Pemisahan migrator/runtime DB + RLS FORCE; `grant_runtime` enumerasi
  schema dinamis (jangan kembalikan ke hardcode public).
- `tenant_scope` reentrant — aman bersarang; tetap jaga konvensi
  caller-provides-scope untuk kejelasan.
- Tidak ada secrets dalam commit (`.env` di-gitignore; token PAT tidak
  pernah ditulis ke repo).
- Commit pesan menjelaskan BUKTI (angka tes, reproduksi), bukan klaim.

## 8. Cara menjalankan verifikasi lokal (sandbox non-root)

Prasyarat binary (jika sandbox baru): PostgreSQL 17 deb-extract di
`/home/z/my-project/pgbin/pg17` (+ shim share-path), FreeRADIUS deb-extract
di `/home/z/my-project/frdeb/extracted`. Lalu:

```bash
cd backend && bash scripts/dev_bootstrap.sh   # idempoten
MT_ENV=test .venv/bin/python -m pytest tests -q          # 222 tes
bash scripts/test_radius.sh                               # 15/15 FreeRADIUS nyata
cd ../apps/web && pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false && pnpm exec eslint src --ext ts,tsx
pnpm exec vitest run && VITE_API_MODE=live pnpm exec vite build
cd ../.. && python3 docs/tools/check_docs.py
bash -n instalasi.sh
```
