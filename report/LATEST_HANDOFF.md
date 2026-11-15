# LATEST_HANDOFF — 15 November 2026: executor task0010 penyerahan keempat (koreksi 01/03/05)

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md);
CONTRACT §6A wajib. Fetch refs/PR sebelum bertindak. Keputusan terbaru dapat
berada di branch belum merged; unfinished filename main bukan bukti belum
ada penyerahan. Semua tanggal di sini Asia/Jakarta; evidence filenames UTC.

## 0. Task aktif dan exact next action

Penyerahan **keempat** executor pada **ID0010 yang sama**, menutup tiga
finding OPEN keputusan [PR20](https://github.com/smahud/MicroTix_Project/pull/20)
(changes_requested pada reviewed SHA `9e9bf2d`):
REV-1311-01 (parser URN menghapus penjaga legacy), REV-1311-03A/03B
(nested `allocations[].invoice_id`; selected identity vs effect), REV-1511-05
(plaintext credential pada cache replay CSV). **Execution `done` / review
`pending`** — packet direname `_done` dalam commit penyerahan; BUKAN
acceptance. Next actor **controller_reviewer** atas exact SHA kandidat
keempat.

Kandidat: branch `session/2026-11-15-pa006-idempotency-correction` dari
decision head `review/0010-pa006-controller-20261115@e507175` (descendant
PR19 — histori review + closed fixes REV-1311-02/REV-1411-04 terbawa,
tidak diimplementasikan ulang). **Implementation `b71574d8b6ba1dc30d132551684791f760e8abc6`**.

| Field | Status / pointer |
|---|---|
| Canonical main teramati | **9903d9b0cf09d737b553da3c21067b4810e956c0**, tidak berubah |
| Active task | [0010 / PA-006](../task/0010-pa006-idempotency_done.md) — penyerahan keempat |
| Execution / review | **done / pending** — menunggu controller review exact SHA keempat |
| Candidate branch / implementation SHA | `session/2026-11-15-pa006-idempotency-correction`; **implementation `b71574d`** (pohon uji seluruh verification run); base decision head `e507175` |
| Published SHA / PR / CI | [PR21](https://github.com/smahud/MicroTix_Project/pull/21) base main; head **`0372dc4c0a6f3c238e69276bf0f02579ae646d44`**; required CI run [43678518336](https://github.com/smahud/MicroTix_Project/actions/runs/43678518336) exact-head **backend/frontend/docs success** |
| Execution report / internal reviewer | [Executor keempat](orchestrator/20261115T044621Z-0010-pa006-idempotency.md); [independent review r4](reviewer/20261115T044616Z-0010-pa006-r4-review.md) — PASS_WITH_NOTES, tiga temuan (F-01 P2 braced-URN parser, F-02/F-03 P3) DITUTUP pada kandidat |
| Evidence executor | [executor-evidence/20261115T044338Z-0010-pa006](executor-evidence/20261115T044338Z-0010-pa006/) — probe controller PR20 dijalankan ulang utuh dari worktree baseline main: 15/15 langkah upgrade live exit 0 (URN completed 201 replay / ambiguous 409 aman; submission+file tetap 1), review-edges 2 passed (nested alias replay; plaintext false×3), review-effects 5 passed (selected canonical; 4 wait-graph query/blocker), targeted 93, full-suite **452 passed** |
| Controller decision (input kandidat ini) | [15 November review](controller/20261114T212816Z-0010-pa006-review.md) + [resubmission check](controller/20261115T005847Z-0010-pa006-resubmission-review.md) pada PR20 |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA kandidat keempat atas matriks finding→perubahan→closing test→actual evidence (report executor §2) dan acceptance matrix (§5); changes_requested membuka kembali ID0010 yang sama; accepted membuka penyiapan PA-002/PA-003 |
| Dependencies | PA-002/003 belum eligible sampai accepted; tidak ada task0020; tanpa merge/deploy/tag/aktivasi fitur oleh penyerahan ini |

## Publication record — PR21

**PUBLISHED.** [PR21](https://github.com/smahud/MicroTix_Project/pull/21)
base main, branch `session/2026-11-15-pa006-idempotency-correction`, head
**`0372dc4c0a6f3c238e69276bf0f02579ae646d44`** = implementation `b71574d`
(fix + tes + executor-evidence) + delivery `0372dc4` (report/packet `_done`
/handoff/progress). Remote push diverifikasi; required CI
[43678518336](https://github.com/smahud/MicroTix_Project/actions/runs/43678518336)
pada exact head **completed/success** (backend, frontend, docs — GitHub
results, bukan rerun lokal). CI hijau bukan acceptance; keputusan tetap
milik controller_reviewer pada exact SHA. Metadata descendant ini hanya
mencatat fakta publikasi yang sudah ada; tidak ada source delta. Final PR
head saat ini **`7b574d097d816d4735167bae59859af95b75dae4`** (descendant
report-only dari 0372dc4 — pohon source identik) dengan required CI
[43678886349](https://github.com/smahud/MicroTix_Project/actions/runs/43678886349)
exact-head backend/frontend/docs **success** juga terverifikasi; SHA masa
depan file ini tidak dikarang.

## 1. Hasil penyerahan keempat (ringkas)

- **REV-1311-01 CLOSED (dibuktikan probe controller utuh)**: parser scope
  legacy migrasi 0004 toleran URN/braced-URN pada tenant dan resource;
  scope tak-terurai DIPERTAHANKAN sebagai baris mati `__unparsed__`
  (fail-safe, bukan dihapus). Live upgrade baseline main → migrasi nyata →
  retry: URN completed **201 replay submission semula (submission/file 1)**;
  URN ambiguous **409 aman (submission/file 1)** — dua kasus yang dulu
  1→2 kini PASS; RLS + `uq_idem_identity` terverifikasi; retry konkuren
  pasca-migrasi keduanya replay.
- **REV-1311-03A CLOSED**: hash v2 bertingkat `allocations[].invoice_id`
  (grammar `a[].b`; opaque/urutan/field lain utuh; body tak termutasi) —
  alias satu invoice logis mereplay 200 (dulu 200/409/200); beda
  invoice/amount 409; malformed 422; retained raw-hash replay; konkuren
  alias-vs-canonical mereplay leader.
- **REV-1311-03B CLOSED**: selected_account_ids dikanonikalisasi sebelum
  preview counts/payload job durable (422 malformed) + konsumsi domain
  (`_canonical_selected_ids` melindungi payload job lama); alias-first ==
  canonical (to_create 1, payload canonical, satu job).
- **REV-1511-05 CLOSED**: preview CSV bebas plaintext (mask `********`);
  migrasi **0005** scrub record retained TANPA menghapus penjaga; replay
  pasca-scrub steril; probe controller: `plaintext_in_initial/cached/
  replayed_response` **false×3** (dulu true×3); mock frontend paritas;
  inventaris safe-response pada laporan.
- **Tetap CLOSED (terbawa, tidak diulang)**: REV-1311-02 (parent+group),
  REV-1411-04 (authenticated HTTP per-thread, after-write rollback/takeover,
  4 wait-graph query/blocker diasserti), PA-001 (10 tes konkurensi lulus).
- Verification: suite penuh **452 passed** (PG 17.11 nyata, peran
  non-superuser, FreeRADIUS aktif), `manage.py check` 0,
  `makemigrations --check` bersih, docs PASS, frontend typecheck/lint/
  Vitest 66/i18n/contrast/live-build sukses; scan kredensial evidence bersih.

## 2. Bloker beta — tidak berubah oleh penyerahan ini

Register bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4.
Code blockers REV-1111-04/05/06/07/08/09/12 tetap terbuka; REV-1111-11
(idempotency) menunggu **controller review kandidat keempat**. Environment
blockers (Gate A/G host Debian 13, lab G1 MikroTik, lab GNS3) tetap ada.
Kandidat Beta **NOT_READY**; `_done`/CI hijau bukan acceptance/merge/deploy.

## 3. Cabang kerja

- `session/2026-11-15-pa006-idempotency-correction` — kandidat keempat
  (dari `review/0010-pa006-controller-20261115@e507175`).
- Terbuka milik pihak lain (JANGAN ditimpa): PR7 SSTP Phase-2, PR8 planning
  audit, PR13 submission check, PR14 DANA planning draft,
  PR15/PR16/PR17/PR18/PR19/PR20 (riwayat task0010 — PR20 adalah base
  keputusan kandidat ini).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2`,
  `integration/beta-0.1`, `session/2026-11-06/07/11/13/14-*`.

## 4. Prioritas eksekusi berikutnya (urut, menunggu keputusan controller)

1. **Controller review kandidat keempat** — exact SHA, matriks
   finding→change→test→evidence (report executor §2); changes_requested
   membuka kembali ID0010, accepted memindahkan kendali penyiapan task.
2. Bila accepted → controller menyiapkan **PA-002 + authority PA-003**
   (job lifecycle fencing/drain; risiko tersisa PA-001: penahanan kunci
   invoice saat render kwitansi dalam transaksi; runworker tanpa drain).
3. DEC-01 topology (native vs Compose) — sebelum rehearsal S4.
4. DEC-02 PR8 docs/manifest; PR7 disposition.
5. Installer/upgrade/restore/scheduler code blockers (REV-1111-04/05/07/09)
   — S4 setelah DEC-01.

## 5. Risiko & keterbatasan yang diketahui (delta sesi ini)

- Batas terdokumentasi retained v1-hash: record pra-v2 yang ASLINYA
  non-canonical + retry beda ejaan → 409 aman (tes eksplisit; bukan
  eksekusi kedua).
- Baris mati `__unparsed__` inert terhadap klaim runtime (penanda operasi
  bukan operasi decorator mana pun); sisa scope mentah ter-truncate 64
  pada tenant_scope sebagai bukti rekonsiliasi ops; reverse 0004 lossy
  (telah terdokumentasi sejak kebijakan pra-koreksi).
- External/file side effect upload (proof_path fisik) tidak diklaim
  exactly-once dari unique key DB; jalur aktif atomic-commit + rekonsiliasi
  legacy terverifikasi; FUP-002 (file yatim rollback) tetap follow-up.
- FUP-001 (500 tenant URL malformed), FUP-003 (iterasi antrean platform)
  tetap follow-up di luar scope PA-006.
- NOT_RUN: host install/upgrade/restore, lab GNS3/CHR, live RADIUS jaringan
  nyata, E2E browser, benchmark kapasitas, worker adoption probe.
- Verdict re-review controller pasca-merge PR9 tetap belum diterbitkan;
  register REV-1111 tetap rujukan.

## 6. Contoh bootstrap sandbox

```bash
git fetch origin --prune
git log --oneline -5
MT_SANDBOX_BASE=/home/z/my-project bash docs/tools/setup_env.sh
cd backend && uv venv .venv --python /usr/bin/python3.13 --seed
MT_PG_BIN=/home/z/my-project/pgbin/pg17 bash scripts/dev_bootstrap.sh
export LD_LIBRARY_PATH=/home/z/my-project/pgbin/pg17/lib:/home/z/my-project/frdeb/extracted/usr/lib/x86_64-linux-gnu:/home/z/my-project/frdeb/extracted/usr/lib/freeradius
export MT_FREERADIUS_BIN=/home/z/my-project/frdeb/extracted/usr/sbin/freeradius MT_FREERADIUS_DICT=/home/z/my-project/frdeb/extracted/usr/share/freeradius
MT_ENV=test .venv/bin/python -m pytest tests -q   # 452 passed + 3 warning (PG nyata)
env -u DATABASE_URL .venv/bin/python manage.py check
python3 docs/tools/check_docs.py
```
