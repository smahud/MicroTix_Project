# REVIEW-1 — Independent review sesi 2026-11-06 (WG-1 + E2E-1)

- **Agent/Peran**: Reviewer independen (sub-agent read-only; tidak memodifikasi/menulis/men-commit berkas apa pun).
- **Tugas**: Review keamanan/regresi/kualitas-tes/konsistensi-dokumen atas perubahan sesi 2026-11-06 sebelum integrasi ke `main`.
- **Baseline evaluasi**: `main` @ `bbee21c` + working tree sesi (18 berkas berubah, 559 insertions / 37 deletions + berkas baru).
- **Referensi**: CONTRACT.md (dibaca penuh); docs/ACCEPTANCE.md §4–§5; AGENT_HANDOFF.md §7 konvensi; BETA_RELEASE_STATUS.md; BETA_TEST_EVIDENCE.md.
- **Metode**: enumerasi diff (`git status`/`git diff --stat`), pembacaan penuh berkas yang disentuh, dan **menjalankan ulang verifikasi sendiri** (bukan memercayai klaim laporan).

## Verifikasi yang dijalankan reviewer (aktual)

| Perintah | Hasil |
|---|---|
| `git status` / `git diff --stat` | 18 berubah (559+/37−) + 9 path baru |
| `cd backend && set -a; . ./.env; set +a; MT_ENV=test .venv/bin/python -m pytest tests -q` | **245 passed, exit 0** (saat review; 252 setelah perbaikan F1/F2/F5/F6) |
| `pnpm exec tsc -b --pretty false` / `eslint src` / `vitest run` | 0 / 0 / **42 passed** |
| `python3 docs/tools/check_docs.py` | **PASS** (21 file, 67 link) |
| `bash -n instalasi.sh` + `shellcheck -S error` | OK / **0 error** |
| `manage.py check` (MT_ENV=test) | 0 issue |
| `manage.py makemigrations --check --dry-run` | **FAIL → temuan F1** (jobs/0003_alter_job_kind pending) — diperbaiki sesi ini, kini CLEAN |
| `make e2e` | TIDAK dijalankan (di luar scope review; orchestrator menjalankan: **7/7 PASS**) |

## Verdict per area

1. **SECURITY — PASS.** CSRF produksi byte-identical dengan baseline (daftar tetap kosong; ENV=production → []). Tidak ada broad SELECT lintas tenant — render/probe/adopt iterasi `tenant_scope` eksplisit per tenant (pola tenant_context.py:34–68), tanpa raw SQL baru. PrivateKey hanya dengan `--private-key-file`; berkas 0600; nilai privat tidak pernah direturn/di-log; `private_key_ref` dibersihkan saat adopsi. Subprocess probe: argv tanpa shell, timeout, stderr dibatasi. Validasi `MT_WG_SERVER_PUBKEY` (base64 validate + 32-byte) tanpa jalur bypass.
2. **REGRESSION — PASS (1 temuan P1).** `verify_api_ssl` adalah perbaikan gap registri pra-ada (dipakai di services/handlers, hilang dari JOB_KINDS; tidak ada enumerasi kind di tes kontrak/OpenAPI → tanpa dampak schema). Migrasi 0009 hanya AddField, pengecualian RLS host tetap terdokumentasi. Installer: `die` dalam subshell berperilaku benar (exit rc=1 → set -e); urutan upgrade benar (deploy_backend migrasi 0009 SEBELUM setup_wireguard adopt); DRY_RUN terjaga. FE login: predicate removeQueries mempertahankan query sesi; refetch hanya ['session']; mock adapter (requires_totp=true) tidak terdampak; paritas loginTotp logis.
3. **TEST QUALITY — PASS.** 23 tes baru non-vacuous: refusal test membuat peer VIA tenant_scope (RLS-visible — adopsi diam-diam pasti tertangkap); render menegaskan 0600 + tidak ada baris PrivateKey aktif + eksklusi REMOVED + inklusi PENDING; probe menegaskan pembaruan DB + monotonik; stub berlabel jujur (self-identifying version). E2E: 7 spec sesuai klaim; isolation memakai `page.request` terautentikasi + asersi nol kebocoran; run.sh gagal keras bila seed hilang (skip tidak bisa menyembunyikan degradasi).
4. **DOCS-CONSISTENCY — PASS (catatan minor).** Semua klaim runnable direproduksi persis (245→252/42/docs PASS/shellcheck); BLOCKED tetap jujur; tidak ada overclaim. Ditemukan: label evidence source (F3, fixed), referensi report/ yang belum ada (F9 — laporan ini kini mengisinya).

## Temuan + penanganan

| # | Tingkat | Lokasi | Temuan | Penanganan sesi ini |
|---|---|---|---|---|
| F1 | **P1** | backend/domains/jobs | Migrasi state `jobs/0003_alter_job_kind` tertinggal (makemigrations --check FAIL) | **Diperbaiki**: migrasi dibuat + diterapkan; `--check` kini CLEAN |
| F2 | P2 | services.py `adopt_wg_host_key` | `--check` membuat singleton via `_wg_host()` (bukan read-only murni) | **Diperbaiki**: check tanpa baris → status `no_host`, tidak membuat; +tes |
| F3 | P2 | services.py probe evidence | `source: "host_wg"` di-hardcode meski stub | **Diperbaiki**: label diturunkan dari binary (host_wg vs stub) |
| F4 | P2 | apps/web/.gitignore | artefak playwright tidak diignore | **Diperbaiki**: +test-results/, playwright-report/ |
| F5 | P2 | parse_handshake_output | epoch absurd → OverflowError tidak tertangkap | **Diperbaiki**: try/except (Overflow/OSError/ValueError) → skip; +tes |
| F6 | P2 | settings validasi pubkey | jalur validasi env tanpa tes | **Diperbaiki**: helper murni `microtix/wg.py` + 5 tes unit |
| F7 | P3 | instalasi.sh doctor | hint tidak membedakan mismatch vs refused | Catatan lanjutan (ops), tidak menghalangi |
| F8 | P3 | nav.spec.ts | asersi judul lemah | **Diperbaiki**: `toHaveTitle(/MicroTix/i)` |
| F9 | P3 | report/ | direktori belum ada | **Ditutup**: laporan sesi + review ini dipersist di report/ |
| F10 | P3 | Makefile e2e | `playwright install \|\| true` menelan kegagalan | Dimitigasi run.sh (cek ulang + exit 1); dicatat |

## Pernyataan akhir

**APPROVE-WITH-NOTES** — tanpa pelemahan keamanan; temuan P1 (F1) diperbaiki
sebelum integrasi; F2–F6/F8 ikut diperbaiki sesi ini; klaim dokumen
direproduksi persis oleh reviewer. Bloker rilis tetap jujur: Gate A/G + G1
adalah prasyarat eksternal host/lab, bukan pekerjaan kode.
