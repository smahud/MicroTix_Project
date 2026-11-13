# LATEST_HANDOFF — Kanonis (13 November 2026: PA-006 diserahkan, menunggu review controller)

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md), wajib menurut CONTRACT §6A. Handoff ini menyimpan status sesi aktual; docs/AGENT_HANDOFF.md hanya panduan navigasi/bootstrap.

## 0. Status sesi executor PA-006 — 13 November 2026

Sesi executor (coding agent z.ai sandbox) mengimplementasikan task **0010 / PA-006** pada branch kandidat dari `origin/main@9903d9b` (PR12 merged; delta terhadap baseline packet `a0f653e` docs-only, source PA-006 tidak berubah). Seluruh acceptance packet diuji; penyerahan diverifikasi remote; review controller **belum** dimulai.

| Field handoff | Status / pointer |
|---|---|
| Active task | **0010 / PA-006** — `task/0010-pa006-idempotency_done.md` |
| Execution / review | `done` / `pending` (submission; acceptance milik controller) |
| Candidate branch / PR | `session/2026-11-13-pa006-idempotency`; tested SHA `159f7ed` (commit penyerahan); PR dibuat sesi ini — nomor pada commit metadata terakhir branch |
| Execution report / acceptance evidence | [20261113T003000Z-0010-pa006-idempotency.md](orchestrator/20261113T003000Z-0010-pa006-idempotency.md) — matriks acceptance→actual→evidence + tabel 28 call site + kebijakan legacy + konflik material §7 |
| Internal reviewer (executor-internal) | [20261113T001500Z-0010-pa006-review.md](reviewer/20261113T001500Z-0010-pa006-review.md) — PASS_WITH_FINDINGS, 0 P1; P2 (takeover leader-gagal) + P3 (alias resource) ditutup tes tambahan; P3 tersisa dicatat pada laporan eksekusi §6 |
| Controller review / reviewed SHA | Belum ada — `controller_reviewer` berikutnya |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA kandidat PR atas matriks acceptance; perhatikan resolusi konflik material 404→422 malformed id (laporan §7) dan catatan follow-up (tenant_id malformed 500 pra-existing di luar dekorator). Verdict → `report/controller/<UTC>-0010-pa006-review.md` diikat pada reviewed SHA; changes_requested membuka task0010 ID sama; accepted → siapkan PA-002/PA-003 |
| Instruction ref sesi ini | `main@9903d9b` + task packet yang sama (rename `_done` ikut commit penyerahan) |

Perubahan PA-006 (ringkas): `backend/domains/common/idempotency.py` — identity `principal + tenant|platform + operation + resource kanonik + key`, protokol claim/replay SATU transaksi (INSERT tunggu unique index → replay/eksekusi segar; record tanpa respons ditolak fail-safe), scope platform eksplisit tanpa fallback sesi, kanonikalisasi UUID (alias → scope sama; malformed → 422), purge TTL SKIP LOCKED. `jobs` UNIQUE(principal, scope, idem_key) via migration 0004 (Add-before-Remove, legacy tanpa rewrite). `payment_submission` menscope `invoice_id`; `identity_conflict_resolve` resource opaque. Bukti: 25 tes baru (HTTP konkuren independen, interleave dipaksa, pg_stat_activity), suite penuh **408 passed** (baseline 383), PA-001 10/10, `manage.py check` 0, migrations bersih, docs PASS.

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` @ `9903d9b` (snapshot sesi ini; fetch HEAD aktual sebelum bertindak) |
| PR terbuka | **Kandidat 0010/PA-006** (`session/2026-11-13-pa006-idempotency`) menunggu review · **#7** SSTP Phase-2 (head `d7fa35e`; docs CI FAIL manifest mismatch — bukan bukti runtime) · **#8** docs planning-audit DRAFT (pemilik file manifest; ownership dijaga) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — code blockers (§3) + environment blockers; PA-006 menutup bagian REV-1111-11 (idempotency/principal scope) pada jalur yang diuji, bukan seluruh register |
| CONTRACT.md | §6A tetap berlaku (packet workflow, default prompts, komunikasi via GitHub) |
| Prioritas aktif | Review kandidat 0010 → PA-002/PA-003 (job fencing/drain/authority) setelah accepted |

## 2. Riwayat implementasi — PA-006 (bukti pada execution report)

Detail lengkap (solusi, alternatif, tabel call site, matriks acceptance, temuan internal, NOT_RUN): [orchestrator/20261113T003000Z-0010-pa006-idempotency.md](orchestrator/20261113T003000Z-0010-pa006-idempotency.md). Ringkasan verifikasi: PostgreSQL 17.11 user-space (peran non-superuser, FORCE RLS aktif); klien HTTP terautentikasi independen per thread (PID koneksi diverifikasi berbeda); interleave dipaksa (leader ditahan dalam handler + observasi `pg_stat_activity`), bukan barrier + harapan. 408 passed penuh; sensitivitas konkurensi lama (unique-violation 500 lintas principal) hilang; regression PA-001 tetap hijau.

## 3. Bloker beta — CODE blockers (jujur)

Register lengkap + baris bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4. Setelah PA-006 diserahkan: REV-1111-11 (security/idempotency) berkurang pada jalur idempotency HTTP yang diuji — **penutupan final menunggu review controller**; seleksi kontrak/scanner fail-closed lain tetap terbuka.

| Code blocker (defect source, terbuka) | Temuan | Packet |
|---|---|---|
| Installer gagal clean-install (argumen ter-join; dependensi duplikat tanpa `xhtml2pdf`) | REV-1111-04 (P1) | S4 |
| Upgrade/repair exit sukses palsu; repair dapat menurunkan HTTPS; readiness hanya SELECT 1 | REV-1111-05 (P1) | S4 |
| Worker tanpa drain/fencing; upgrade overwrite+migrate saat proses aktif | REV-1111-06 (P1) | PA-002/PA-003 (S2) |
| Restore end-to-end + pemisahan secret migrator belum terbukti | REV-1111-07 (P1) | S4 |
| Topology deployment belum konsisten (native vs Compose) — **DEC-01 belum resolved** | REV-1111-08 (P1) | keputusan pemilik |
| Scheduler invoice BELUM diimplementasikan | REV-1111-09 (P1) | S4 |
| Seleksi kontrak/scanner fail-closed (permission operasi, selected-set, scanner) — sisa REV-1111-11 di luar idempotency | REV-1111-11 (P1) | S1, S2, S3 |
| Kapasitas 1.000×1.000 belum dibuktikan benchmark | REV-1111-12 (P2) | S6/G4-G5 |
| Baru (follow-up PA-006, non-blocking): `tenant_id` malformed pada route tenant tetap 500 di `resolve_membership` (pra-existing, di luar jangkauan dekorator) | laporan PA-006 §7 | kandidat packet kecil |

Environment blockers (prasyarat eksternal, TETAP ADA): Gate A/G host Debian 13 nyata; G1 lab MikroTik CHR/fisik; lab GNS3 API-driven (CONTRACT §7).

## 4. Cabang kerja

- `session/2026-11-13-pa006-idempotency` — kandidat PA-006, menunggu review controller (JANGAN ditimpa).
- Terbuka milik pihak lain (jangan diubah): `docs/planning-audit-20261110` (PR #8), `session/2026-11-07-sstp-phase2` (PR #7).
- Arsip riwayat: `session/2026-11-11-pa001-payment-concurrency` (MERGED PR #9), `parallel/beta-be2`, `integration/beta-0.1`, `session/2026-11-06/07-*`.

## 5. Prioritas eksekusi berikutnya (urut)

1. **Review controller kandidat 0010/PA-006** (exact SHA; matriks acceptance; konflik 404→422 §7).
2. **PA-002 + authority PA-003 (P1)** — job lifecycle fencing/drain (termasuk risiko tersisa: penahan kunci invoice selama render PDF dalam transaksi; runworker tanpa drain; write tanpa ownership check; follower same-key menunggu I/O dalam transaksi leader).
3. **DEC-01** — keputusan topology (sebelum rehearsal S4).
4. **DEC-02** — PR #8 docs/manifest (ownership branch itu).
5. **PR #7 disposition** (SSTP Phase-2).
6. Installer/upgrade/restore/scheduler (REV-1111-04/05/07/09) — S4 setelah DEC-01.

## 6. Contoh bootstrap sandbox

```bash
git fetch origin --prune
# Baca task/0000-start-here.md, packet aktif, dan handoff ini sebelum bertindak.
MT_SANDBOX_BASE=/home/z/my-project bash docs/tools/setup_env.sh   # PG 17.11 + FreeRADIUS 3.2.7
cd backend && MT_PG_BIN=/home/z/my-project/pgbin/pg17 bash scripts/dev_bootstrap.sh
# (venv: uv venv .venv --python /usr/bin/python3.13 --seed bila python3.13-venv absen)
MT_ENV=test .venv/bin/python -m pytest tests -q   # 408 passed pasca-PA-006 (PG nyata)
env -u DATABASE_URL MT_ENV=test .venv/bin/python manage.py check   # 0 issue
python3 docs/tools/check_docs.py
```

## 7. Risiko & keterbatasan yang diketahui

- PA-006 teruji di sandbox PostgreSQL nyata (HTTP konkuren lintas koneksi), BUKAN bukti host/lab/DR/kapasitas; `_done` + CI hijau bukan acceptance — review controller exact SHA yang memutuskan.
- Follower same-key menunggu selama transaksi leader (termasuk I/O render kwitansi) — perbaikan struktural di PA-002.
- Tes konkurensi tetap level HTTP test-client in-process (bukan jaringan penuh); koneksi DB per thread nyata dan terpisah.
- Mutasi router tetap jalur simulator; gap G1 dan risiko lama: handoff 2026-11-07 §7.
- Kapasitas 1.000×1.000 tetap klaim desain; xhtml2pdf 0.2.28 dipin (pantau advisori).
- PAT GitHub hanya dipakai untuk fetch/push dari sandbox (tidak pernah di-commit; scan diff bersih). Rotasi PAT tetap disarankan karena melewati kanal chat.
