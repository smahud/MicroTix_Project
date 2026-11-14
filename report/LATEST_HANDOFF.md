# LATEST_HANDOFF — Kanonis (15 November 2026: executor menutup 4 finding PA-006, menunggu controller review)

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md); CONTRACT §6A wajib. Fetch refs sebelum bertindak. Status main bisa tertinggal dari keputusan/candidate yang belum merged; jangan mengulang implementasi dari unfinished filename main saja.

## 0. Task aktif dan exact next action

| Field | Status / pointer |
|---|---|
| Canonical main | `9903d9b0cf09d737b553da3c21067b4810e956c0` — diperiksa sesi 15 November; tidak berubah |
| Active task | [0010 / PA-006](../task/0010-pa006-idempotency_done.md) — execution `done`, review `pending` (executor scope + tes wajib tuntas; bukan acceptance) |
| Execution / review | **done / pending** — penyerahan ketiga pada ID0010 yang sama |
| Candidate branch / implementation SHA | `session/2026-11-15-pa006-idempotency`; implementation `1780e150695a6b7bbb4109b6f13ea44df54fa6a0` + hardening `c99838c`; base keputusan `review/0010-pa006-controller-20261114@b6a0cb8` (packet + riwayat koreksi dibawa semantik) |
| Published head / PR / CI | PR kandidat base main — pointer aktual + required CI diisi executor pada file ini setelah verifikasi remote (lihat baris "Publication record" di bawah) |
| Execution / internal review | [Executor report](orchestrator/20261114T164816Z-0010-pa006-idempotency.md) — matriks finding→perubahan→tes→evidence, acceptance lengkap, tabel 28 call site; [independent review](reviewer/20261114T164816Z-0010-pa006-review.md) PASS_WITH_NOTES (temuan P3 ditutup pada `c99838c` atau didokumentasikan) |
| Controller decision terbaru | [Review 14 November](controller/20261114T153739Z-0010-pa006-review.md) `changes_requested` pada `37a8729` — kandidat ini adalah jawaban atas keputusan itu; review controller atas SHA baru belum ada |
| Next actor | **controller_reviewer** |
| Exact next action | Review kandidat exact SHA (`1780e15`+`c99838c`; head publikasi PR di bawah) terhadap REV-1311-01/02/03 + REV-1411-04 dan acceptance awal packet; keputusan di `report/controller/<UTC>-0010-pa006-review.md`, publish + verify sebelum pergantian peran |
| Dependent work | PA-002/003 belum eligible sampai task0010 accepted; task0020 tidak dibuka; tidak ada merge/deploy/release otomatis |

## Publication record (diisi executor setelah verifikasi remote)

Placeholder ini diisi/diperbarui saat penyerahan: PR kandidat, head publikasi
terverifikasi, dan status required CI (backend/frontend/docs). Bila baris ini
belum terisi, penyerahan belum final dan next actor tetap `coding_agent`.

## 1. Ringkasan penyerahan ketiga (executor, 15 November 2026)

Koreksi empat finding keputusan PR18 pada ID0010 yang sama, tanpa mengulang
PA-001 dan tanpa melemahkan assertion:

1. **REV-1311-01** — migrasi `jobs/0004` ditulis ulang: record tanpa respons
   DIPERTAHANKAN (penjaga efek ambigu; hanya scope tak-terurai 3-bagian yang
   dihapus), operasi platform legacy di-remap `tenant_scope='platform'`,
   dedupe alias memilih record berrespons terbaru; runtime `legacy_shapes` +
   `replay_guard` merekonsiliasi `payment_submission` `resource=''` dengan
   verifikasi submission→tenant(RLS)→invoice sebelum replay; migrasi tidak
   membaca tabel tenant (FORCE RLS berlaku bagi migrator). Transisi migrasi
   NYATA 0003→0004 dibuktikan tes: retry pasca-upgrade mereplay submission
   semula (count 1), beda body 409, no-response guard tetap menahan (409).
2. **REV-1311-02** — `identity_conflict_resolve` identitas =
   `<canonical migration UUID>:<group_id sha256[:16]>`; parent divalidasi
   SEBELUM klaim/replay (malformed 422 / missing 404 — cache tidak dapat
   melewati); session A/B menulis keputusan masing-masing [2,2]; record
   legacy group-only → 409 aman (tidak menyeberang session).
3. **REV-1311-03** — hash body v2: field UUID yang dideklarasikan
   (`package_id`, `router_id`, `selected_account_ids`) dinormalkan sebelum
   HMAC; perbandingan menerima v2 ATAU v1 raw (retained hash), konstan-waktu;
   string opaque exact-case dan urutan array dipertahankan; alias → replay,
   beda nyata → 409.
4. **REV-1411-04** — tes konkurensi ditulis ulang: klien HTTP terautentikasi
   per-thread melalui dispatch penuh; `_assert_lock_wait` gagal-tes saat
   observasi gagal; takeover test menyuntik kegagalan SETELAH writes
   domain/audit/outbox sebelum respons dipersist dengan penantang same-key
   terblokir (diassert) — transaksi leader ter-rollbalik utuh, penantang
   takeover, satu aksi terkomit, retry pasca-takeover replay.

Bukti (PostgreSQL 17.11 nyata, role `mtx_app` NOSUPERUSER/NOBYPASSRLS,
FreeRADIUS aktif): suite penuh **426 passed** (3 warning pra-ada
adapter-thread), targeted controller set **65 passed**, **6/6 probe
acceptance controller PASS** persis seperti evidence 14 November dijalankan
ulang, `manage.py check` 0 issue, `makemigrations --check` bersih, docs
check PASS. Catatan harness: `raise_request_exception=False` pada klien tes
konkurensi (signal `got_request_exception` Django menulari exc_info antar
klien overlap — dibuktikan dan didokumentasikan pada laporan §1).

Riwayat ID0010: PR15 (13 Nov, changes_requested) → PR17 (14 Nov,
changes_requested, PR18 keputusan) → kandidat ini. Instruksi/koreksi PR16 +
PR18 dibawa semantik; PR15/16/17/18 dan seluruh report historis dipertahankan
tanpa force-push.

## 2. Bloker beta — tidak berubah

Register bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4.
Code blockers REV-1111-04/05/06/07/08/09/12 tetap terbuka; REV-1111-11
(idempotency) ditutup **pada kandidat ini menunggu review controller**.
Environment blockers (Gate A/G host Debian 13, lab G1 MikroTik, lab GNS3)
tetap ada. Kandidat Beta **NOT_READY**.

## 3. Cabang kerja

- `session/2026-11-15-pa006-idempotency` — kandidat penyerahan ketiga (dari
  `review/0010-pa006-controller-20261114@b6a0cb8`).
- Terbuka milik pihak lain (JANGAN ditimpa): PR7 SSTP Phase-2, PR8 planning
  audit, PR13 submission check, PR15/PR16/PR17/PR18 (riwayat task0010).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2`,
  `integration/beta-0.1`, `session/2026-11-06/07/11/13/14-*`.

## 4. Prioritas eksekusi berikutnya (urut, menunggu keputusan controller)

1. **Controller review task0010** atas exact SHA kandidat ketiga.
2. Bila accepted → controller menyiapkan **PA-002 + authority PA-003**
   (job lifecycle fencing/drain; risiko tersisa PA-001: penahanan kunci
   invoice saat render kwitansi dalam transaksi; runworker tanpa drain).
3. DEC-01 topology (native vs Compose) — sebelum rehearsal S4.
4. DEC-02 PR8 docs/manifest; PR7 disposition.
5. Installer/upgrade/restore/scheduler code blockers (REV-1111-04/05/07/09)
   — S4 setelah DEC-01.

## 5. Risiko & keterbatasan yang diketahui (delta sesi ini)

- Batas terdokumentasi retained v1-hash: record pra-v2 yang ASLINYA
  non-canonical + retry beda ejaan → 409 aman (tes eksplisit; bukan eksekusi
  kedua).
- Data korup >64 karakter pada tenant/resource mentah membuat migrasi 0004
  fail-stop atomik (tanpa kehilangan parsial; butuh pembersihan manual) —
  tanpa kasus nyata pada data main.
- FUP-001 (500 tenant URL malformed), FUP-002 (file fisik yatim saat
  rollback), FUP-003 (iterasi antrean platform) tetap follow-up di luar
  scope PA-006.
- NOT_RUN sesi ini: host install/upgrade/restore, lab GNS3/CHR, live RADIUS,
  E2E browser, frontend lokal (atribusi CI), benchmark kapasitas.
- Verdict re-review controller pasca-merge PR9 tetap belum diterbitkan;
  register REV-1111 tetap rujukan.
- PAT GitHub hanya dipakai untuk fetch/push dari sandbox (tidak pernah
  di-commit; scan diff bersih). Rotasi PAT tetap disarankan karena melewati
  kanal chat.

## 6. Contoh bootstrap sandbox

```bash
git fetch origin --prune
git log --oneline -5
MT_SANDBOX_BASE=/home/z/pgbase bash docs/tools/setup_env.sh
cd backend && uv venv .venv --python /usr/bin/python3.13 --seed
MT_PG_BIN=/home/z/pgbase/pgbin/pg17 bash scripts/dev_bootstrap.sh
export LD_LIBRARY_PATH=/home/z/pgbase/pgbin/pg17/lib:/home/z/pgbase/frdeb/extracted/usr/lib/x86_64-linux-gnu:/home/z/pgbase/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/home/z/pgbase/frdeb/extracted/usr/sbin/freeradius MT_FREERADIUS_ROOT=/home/z/pgbase/frdeb/extracted
MT_ENV=test .venv/bin/python -m pytest tests -q   # 426 passed + 3 warning (PG nyata)
env -u DATABASE_URL .venv/bin/python manage.py check
python3 docs/tools/check_docs.py
```
