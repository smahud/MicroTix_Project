# Bootstrap in-repo `setup_env.sh` + perbaikan harness T19 + push via PAT (sesi lanjutan)

- **Agent/Peran**: Orchestrator utama (GLM; sesi berlanjut — konteks sesi sebelumnya habis, lalu sandbox terdaur ulang di tengah sesi).
- **Objektif**: (1) Commit + push hasil pekerjaan sesi ke GitHub via PAT yang disediakan pengguna; (2) menutup gap handoff: `setup_env.sh` (bootstrap sandbox PG17+FreeRADIUS, AGENT_HANDOFF §8) hanya hidup di sandbox dan hilang saat daur ulang; (3) investigasi jujur atas kegagalan harness RADIUS yang muncul sekali saat verifikasi ulang.
- **Baseline**: `main` @ `f284ce8` (clone segar; remote diverifikasi `git ls-remote`; tree kode identik dengan `f575388` yang CI-hijau terverifikasi sesi sebelumnya).
- **Referensi dokumen**: CONTRACT.md §6 (mulai dari realitas), §9 (bukti verifikasi jujur; jangan klaim tanpa eksekusi), §10 (laporan wajib), §11 (git + bukti remote), §3 (anti-overengineering); docs/AGENT_HANDOFF.md §8; report/LATEST_HANDOFF.md §6.

## Kronologi sesi (termasuk insiden)

1. **Sesi bagian 1** (konteks lama, sebelum daur ulang): commit `64ac004`
   (setup_env.sh in-repo) + `18cf506` (laporan+handoff) dibuat pada sandbox;
   push BLOCKED (PAT hilang bersama konteks). Diverifikasi saat itu: backend
   252/252, RADIUS nyata 15/15, docs PASS 21→22 file, rebuild setup_env
   BYTE-IDENTIK, shellcheck 0 findings.
2. **Daur ulang sandbox** (insiden, ~2026-11-06T06:19Z): `/home/z/my-project`
   direset platform — clone lokal + kedua commit di atas HILANG (risiko yang
   sendirinya terdokumentasi di handoff bagian 1). Lab asli selamat di
   `/tmp/my-project` (pgbin/pg_17/pglib/frdeb + .deb + shellcheck).
3. **Sesi bagian 2 (ini)**: pengguna menyediakan PAT → rekonstruksi penuh:
   lab dipulihkan; repo di-clone ulang (`f284ce8` terverifikasi); kedua
   commit direkonstruksi **byte-exact dari konteks sesi** (SHA baru:
   `1e326dc` tools + commit docs ini) dan DIVERIFIKASI ULANG (bukan sekadar
   dipercaya).

## Perubahan

- `docs/tools/setup_env.sh` (BARU, commit `1e326dc`): versi in-repo bootstrap
  sandbox AGENT_HANDOFF §8. `MT_SANDBOX_BASE` overridable + diekspor; patch
  path PG17 digeneralisasi NUL-pad.
- `docs/repository-manifest.json` (commit `1e326dc`): `--refresh` 21→22 file.
- `backend/scripts/test_radius.sh` (commit `98ea90d`): klasifikasi T19
  no-reply vs accept (lihat investigasi).
- `docs/progress.md`, `report/LATEST_HANDOFF.md`, laporan ini (commit docs).

## Investigasi kegagalan harness T19 (bukti lengkap, jujur)

**Fakta**: run pertama verifikasi ulang (urutan: bootstrap fresh → pytest
252 → radius) melaporkan `FAIL [T19] password tenant A diterima tenant B —
KEBOCORAN TENANT` 1x; run kedua langsung PASS 15/15. RC_OUT run pertama
hilang (harness `rm -rf $WORK` saat cleanup).

**Investigasi**:
1. Analisis kode `test_radius.sh`: `rad_expect_reject` false BUKAN hanya saat
   Access-Accept — juga saat **tidak ada balasan sama sekali** (radclient
   `-t 2 -r 1` timeout). Cabang FAIL T19 lama mengklaim "KEBOCORAN TENANT"
   untuk KEDUANYA → klaim kebocoran tenant **tanpa bukti Access-Accept**
   (konflasi terbukti dari kode).
2. Analisis `seed_radius_check.py`: data deterministik per run
   (reset-and-recreate dalam scope tenant); password tenant A/B berbeda
   secara konstan; tidak ada jalur data yang berubah antar-run.
3. Reproduksi (semua dengan output penuh): (a) DB fresh + bootstrap + radius
   → **PASS 15/15**; (b) urutan PERSIS run pertama (bootstrap fresh → pytest
   252 → radius) → **PASS 15/15**; (c) 2 run tambahan → **PASS 15/15**.
   Total 4/4 reproduksi PASS.
4. **Kesimpulan jujur**: akar run pertama TIDAK TERBUKTI (bukti hilang);
   dugaan terkuat no-reply transient. TIDAK ada bukti kebocoran nyata
   (4/4 reproduksi lulus + analisis kode). Kegagalan yang sama akan muncul
   lagi suatu saat secara acak — maka perbaikan klasifikasi penting agar
   bukti yang dihasilkan jujur.

**Fix minimal** (commit `98ea90d`, hanya cabang yang mengklaim kebocoran):
Reject → PASS; Accept → FAIL kebocoran + bukti balasan; **no-reply → FAIL
"isolasi T19 TIDAK terverifikasi (bukan bukti kebocoran)"** + ekor RC_OUT.

## Verifikasi aktual (sesi bagian 2, pasca rekonstruksi)

| Perintah | Hasil |
|---|---|
| `git ls-remote origin` (pra-kerja) | `main` = `f284ce8`; PR #1/#2 merged; cabang sesi tidak ada di remote |
| `bash -n docs/tools/setup_env.sh` + `shellcheck` | OK / 0 findings |
| `bash docs/tools/setup_env.sh` jalur FRESH (pg17 dibuang → rebuild dari .deb) | exit 0; sha256 `postgres`+`initdb` **BYTE-IDENTIK** dengan artefak terverifikasi |
| `bash docs/tools/setup_env.sh` jalur NO-OP | exit 0 (idempoten) |
| `MT_PG_BIN=… dev_bootstrap.sh` (DB fresh, pasca `uv venv`) | migrasi + `grant_runtime` (public, radius) + seed OK |
| `MT_ENV=test pytest tests -q` | **252 passed** (23.5s; diulang pasca-fix harness: 252 passed 23.8s) |
| `bash scripts/test_radius.sh` (5x total sesi ini: 1 FAIL-T19 + 4 PASS + 2 pasca-fix) | run-1: FAIL T19 (1x, investigasi di atas); reproduksi 4/4 **PASS 15/15**; pasca-fix 2/2 **PASS 15/15** exit 0 |
| `python3 docs/tools/check_docs.py --refresh` → `check_docs.py` | PASS (22 file) |
| `bash -n instalasi.sh` / `shellcheck instalasi.sh` | OK / 0 error (SC1090/SC2034/SC2015 warning/info pre-existing di main) |

## Tidak dieksekusi (jujur + alasan)

- Suite frontend (tsc/eslint/vitest/build) + `make e2e` lokal: kode FE
  bit-identik dengan `f575388` (CI hijau terverifikasi); perubahan sesi ini
  docs/tools/harness-only → dijalankan oleh CI GitHub pada PR sesi ini.
- Gate A/G (instalasi host Debian 13 nyata) + G1 (lab MikroTik) + lab GNS3:
  prasyarat eksternal (tetap penahan tag `v0.1.0-beta.1`).

## Keamanan & kompatibilitas

- PAT GitHub: disimpan HANYA di `.git/config` lokal (remote URL) untuk
  operasi push sesi ini; TIDAK PERNAH ditulis ke berkas ter-commit, laporan,
  atau output yang dicetak (konvensi sesi-sesi lama; scan commit bersih).
- Tidak ada perubahan kode aplikasi (hanya docs/tools/harness shell);
  perbaikan harness T19 mengetatkan kejujuran bukti, bukan melonggarkan
  gate (no-reply tetap FAIL — run dianggap gagal dan harus diulang).
- Secrets harness (password NAS CSPRNG) hanya hidup di `$WORK` disposabel.

## Blokir

- Tidak ada blokir push lagi (PAT tersedia). Blokir beta tetap: Gate A/G,
  G1 lab MikroTik, lab GNS3 API-driven (CONTRACT §7).

## Status & handoff

- **Status: SELESAI (implementasi + verifikasi lokal + PUSH)** — branch
  `session/2026-11-06-bootstrap-inrepo`: `1e326dc` (tools) → `98ea90d`
  (fix harness T19) → commit docs (laporan ini). Status remote (push/PR/
  merge/SHA terverifikasi): lihat `report/LATEST_HANDOFF.md` (diperbarui
  atomik pasca-merge sesuai §10/§11).
- **Langkah eksak berikutnya**: setelah merge — prioritas P2 M6/M7
  billing/ledger R2 (FINANCE.md §16, vertical slice per task); ops host
  Gate A/G saat host tersedia.
