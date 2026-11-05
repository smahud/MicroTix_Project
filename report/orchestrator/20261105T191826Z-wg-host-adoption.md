# WG-1 — Adopsi keypair WireGuard host + render peers + probe handshake

- **Agent/Peran**: Orchestrator utama (implementasi langsung; explorasi read-only didelegasikan ke sub-agent Explore).
- **ID tugas**: WG-1 (handoff §5 P1 "Aktifasi WireGuard host: adopsi keypair installer + probe handshake").
- **Baseline**: `main` @ `bbee21c` (CONTRACT.md baru; working tree bersih).
- **Referensi dokumen**: CONTRACT.md; docs/AGENT_HANDOFF.md §5/§8; docs/ROUTEROS.md §2.1/§2.3/§2.7/§2.8; docs/ARCHITECTURE.md §2/§4/§6; docs/BETA_RELEASE_STATUS.md batasan 2/4; instalasi.sh §9.13 (setup_wireguard).
- **Lingkungan**: sandbox Linux (Debian 13 userland) non-root; PostgreSQL 17.11 deb-extract (patch jalur share non-root, di luar repo: `/home/z/my-project/pgbin`, `pg_17`, `pglib`); FreeRADIUS 3.2.7; Python 3.13 (uv venv); Node 24 + pnpm 12.16.1. Tanpa root → interface wg / systemd TIDAK tersedia (dicatat jujur sebagai BLOCKED).

## Tujuan & latar

Installer membuat keypair X25519 NYATA (`wg genkey/pubkey`) di
`/etc/microtix/wireguard/`, `wg0.conf`, dan menulis env `MT_WG_SERVER_PUBKEY`
(Instalasi §9.13) — tetapi backend MENGABAIKANNYA: `_wg_host()` membuat kunci
sendiri + publikasi placeholder sha256-deterministik, sehingga skrip bootstrap
memuat kunci yang TIDAK cocok dengan interface host produksi → tunnel tidak
akan pernah handshake. Tugas: adopsi keypair oleh model `WireGuardHost`,
render konfigurasi peers host, dan probe handshake — tanpa melemahkan kontrak
RLS/keamanan apa pun.

## Perubahan

- `backend/microtix/wg.py` (baru): `validate_public_key()` murni — X25519 base64 32-byte; salah format → ValueError (settings → ImproperlyConfigured saat boot); kosong → fallback dev.
- `backend/microtix/settings.py`: konsumsi env `MT_WG_SERVER_PUBKEY` tervalidasi. Catatan: patch jalur non-root TIDAK menyentuh repo.
- `backend/domains/network/models.py`: `WireGuardHost` + `key_source` (installer_env|generated_dev) + `adopted_at`; migrasi `0009` (AddField×2, non-destruktif; pengecualian RLS host tetap seperti 0004).
- `backend/domains/network/services.py`: `_wg_host()` mengadopsi env saat membuat; `adopt_wg_host_key()` (idempoten; **rotasi DITOLAK bila ada peer aktif** — peers memegang kunci lama; check_only tanpa mutasi termasuk tanpa membuat baris → no_host); `render_host_config()` (peers lintas-tenant via `tenant_scope` eksplisit per tenant, bukan broad SELECT; berkas 0600; PrivateKey HANYA dengan `--private-key-file`; REMOVED tidak dirender); `parse_handshake_output()` (epoch 0 = belum pernah; baris tak dikenal/absurd diabaikan non-fatal); `probe_handshakes()` (subprocess argv tanpa shell, timeout 10s, pembaruan `last_handshake_at` monotonik, drift evidence unknown/missing, label evidence host_wg vs stub jujur).
- Commands baru: `adopt_wg_host` (--check; JSON; exit 1 refused/mismatch), `render_wg_config` (JSON), `probe_wg` (JSON; **BLOCKED exit 2** bila binary/interface tak ada — tidak pernah PASS palsu).
- `backend/domains/jobs/models.py`: gap registri pra-ada `verify_api_ssl` DIPERBAIKI (dipakai services/handlers tapi hilang dari JOB_KINDS/JobKind) + migrasi state `jobs/0003_alter_job_kind` (temuan reviewer F1, P1).
- `docs/ARCHITECTURE.md` §6: daftar kind + `verify_api_ssl` (paritas registri).
- `instalasi.sh`: `setup_wireguard()` memanggil `adopt_wg_host` (gagal = die — bootstrap dengan kunci salah = tunnel diam-diam rusak) + `render_wg_config` ke `$WG_DIR/rendered` (tanpa PrivateKey); doctor + cek `adopt_wg_host --check`; upgrade menjalankan `setup_wireguard` (idempoten); pesan dry-run diperbarui.
- Keputusan desain: TIDAK menambah job kind probe — worker produksi non-root, `wg show` butuh root → job akan selalu gagal di produksi; probe adalah command ops (anti-job-palsu, §5).

## Verifikasi aktual

| Perintah | Hasil |
|---|---|
| `MT_ENV=test pytest tests -q` (sebelum perubahan; baseline ulang) | **222 passed** |
| `MT_ENV=test pytest tests -q` (setelah WG + review-fix) | **252 passed** (222 + 23 WG + 7 hardening: validasi pubkey murni ×5, parser overflow, --check no_host) |
| `manage.py makemigrations --check --dry-run` | **CLEAN** (setelah jobs/0003) |
| `manage.py check` | 0 issue |
| `bash scripts/test_radius.sh` (FreeRADIUS nyata) | **PASS 15/15** (T16/T19/T20/T21) |
| `bash -n instalasi.sh` + `shellcheck -S error` | OK / **0 error** |
| `python3 docs/tools/check_docs.py` | **PASS** (manifest --refresh untuk perubahan dokumen disengaja) |
| `manage.py adopt_wg_host` (dev, tanpa env) | `no_env` jujur |
| `manage.py probe_wg` (sandbox tanpa wg) | **BLOCKED exit 2** jujur |

Tes tidak dieksekusi + alasan: probe pada interface host NYATA + `wg-quick@wg0` (butuh root host — BLOCKED sandbox); verifikasi lab perangkat (G1) tidak tersedia.

## Keamanan & kompatibilitas

- Kunci privat host TIDAK pernah masuk proses aplikasi (hanya publik dari env; private_key_ref dikosongkan saat adopsi); render tanpa PrivateKey default; 0600.
- Isolasi tenant: iterasi eksplisit per-tenant `tenant_scope` (pola §4); tanpa raw SQL baru; peers RLS tetap fail-closed.
- Produksi tidak dilemahkan: pengecualian RLS host tidak berubah (platform singleton, 0004); installer tetap tidak menyentuh router pelanggan.
- Reviewer independen (sub-agent, read-only, menjalankan ulang sendiri 252/42/tsc/eslint/docs/makemigrations): **APPROVE-WITH-NOTES**; temuan F1 (P1) diperbaiki sebelum merge; F2–F6/F8 diperbaiki sesi ini; F7/F10 dicatat sebagai catatan lanjutan.

## Status & handoff

- **Status tugas: SELESAI untuk scope kode+tes** (implemented + verified_local); verified_lab/host = BLOCKED (root/host).
- Commit/remote: lihat `report/LATEST_HANDOFF.md` (diperbarui atomik setelah push terverifikasi).
- Lanjutan: eksekusi ops host Gate A/G (`systemctl enable --now wg-quick@wg0`, `manage.py probe_wg`, render+apply dengan PrivateKey host), lalu catat bukti pada BETA_TEST_EVIDENCE.
