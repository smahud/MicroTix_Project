# LATEST_HANDOFF — 15 November 2026: controller PR19 changes_requested

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md);
CONTRACT §6A wajib. Fetch refs/PR sebelum bertindak. Keputusan terbaru dapat
berada di branch belum merged; unfinished filename main bukan bukti belum
ada penyerahan. Semua tanggal di sini Asia/Jakarta; evidence filenames UTC.

## 0. Task aktif dan exact next action

| Field | Status / pointer |
|---|---|
| Canonical main teramati | **9903d9b0cf09d737b553da3c21067b4810e956c0**, tidak berubah |
| Active task | [0010 / PA-006](../task/0010-pa006-idempotency.md), reopened ID sama |
| Execution / review | **ready / changes_requested**; third submission tidak diterima seluruh scope |
| Reviewed candidate / PR | [PR19](https://github.com/smahud/MicroTix_Project/pull/19), `session/2026-11-15-pa006-idempotency` @ **9e9bf2d42002a00a69d54fc355b77384897b9478** |
| Tested source ancestor | **c99838cd6e9f144adf53bb44ed792fba15a432fe**, implementation1780e15; candidate descendants report-only pada source/config terkait |
| Latest instruction/decision ref | [PR20](https://github.com/smahud/MicroTix_Project/pull/20), **review/0010-pa006-controller-20261115**, target candidate PR19 branch; first verified decision ancestor2c2797b37ba536100fdf67c8dd08ceab793c5ff9; records-only delta |
| Controller decision | [15 November review](controller/20261114T212816Z-0010-pa006-review.md); OPEN01/03/05, CLOSED02/04 pada SHA yang diperiksa |
| Executor/history | [Third executor report](orchestrator/20261114T164816Z-0010-pa006-idempotency.md), [internal review](reviewer/20261114T164816Z-0010-pa006-review.md), [previous controller](controller/20261114T153739Z-0010-pa006-review.md); klaim all-PASS lama ditolak untuk scope yang masih gagal |
| Independent controller source review | [Runtime](reviewer/20261114T213051Z-0010-runtime-independent.md), [migration](reviewer/20261114T212943Z-0010-migration-independent.md); root runtime/effect evidence terpisah pada laporan keputusan |
| Next actor | **coding_agent** |
| Exact next action | Fetch ref keputusan ini+PR19; bawa records semantik, tutup REV-1311-01/03 dan REV-1511-05 minimum pada ID0010; serahkan finding→change→closing test→actual evidence dan exact candidate+CI baru |
| Dependencies | PA-002/003 belum eligible; tidak ada task0020 baru, merge/deploy/tag/feature activation |

## Publication record

**PUBLISHED**, [PR20](https://github.com/smahud/MicroTix_Project/pull/20)
menargetkan `session/2026-11-15-pa006-idempotency`. First verified decision
ancestor **2c2797b37ba536100fdf67c8dd08ceab793c5ff9**, remote tree
**43a03b4683165a6d647044d82093b05b26305919** cocok byte-content dengan
local reviewed records. Fetch+local checkout remote commit terverifikasi;
source/config delta dari input9e9bf2d tetap kosong. Commit metadata berikutnya
hanya menyimpan pointer publikasi yang sudah ada; reviewed application SHA
tetap9e9bf2d. Main dan input PR19 tidak diubah.

Publication CI [43644492925](https://github.com/smahud/MicroTix_Project/actions/runs/43644492925)
terverifikasi **completed / success** pada ancestor2c2797b: backend,
frontend dan docs masing-masing success. Final metadata head/required CI
diverifikasi lewat PR sebelum handoff. Status CI record
tidak menutup failure acceptance aplikasi. Detail publikasi ada pada laporan
controller; tidak ada SHA masa depan file yang dikarang.

## 1. Hasil review terbaru

- **REV-1311-01 P1 partial OPEN**: canonical old-code proof upload→0004→retry
  replay asli, submission/file tetap1. Valid URN tenant scope dihapus sebagai
  malformed; completed dan ambiguous old keys keduanya membuat submission
  dan physical proof file **1→2** sesudah migrasi+retry.
- **REV-1311-03 P2 partial OPEN**: nested money `allocations[].invoice_id`
  alias belum canonical di hash (HTTP200/409/200); declared selected-ID hash
  canonical tetapi preview/payload raw (alias202 memilih0 vs canonical1,
  retry mereplay job salah). Correction sebatas identity/effect, bukan PA003.
- **REV-1511-05 P1 NEW**, path pra-ada: CSV validation preview password
  tersimpan plaintext di response cache dan direplay. Mandatory no-secret
  replay acceptance belum dipenuhi. Logs hanya presence booleans.
- **REV-1311-02 CLOSED**: migration parent+opaque group, current parent
  validation, keputusan A/B[2,2], malformed422/missing404, legacy409.
- **REV-1411-04 CLOSED dengan root supplement**: per-thread authenticated
  HTTP dan injected after-write rollback/takeover PASS. Empat wait graphs
  mengassert query+`pg_blocking_pids`, leader→holder dan contender→leader.

Root menjalankan PostgreSQL17.11 NOSUPERUSER/NOBYPASSRLS: **67 targeted,
426 full,6 prior probes PASS**, tiga pre-existing adapter-thread warnings;
PA00110 lulus. Check/migration/docs PASS. Exact candidate CI43618187731
backend/frontend/docs success. Tiga new HTTP conformance probes dan dua
actual-source URN upgrade cases FAIL; canonical upload upgrade PASS.
Harness process lifetime/query truncation diperbaiki dan diatribusikan
terpisah, bukan defect produk. Raw commands/exit/log serta NOT_RUN lengkap
pada laporan controller. Perbaikan aplikasi dikembalikan ke coding agent.

Histori ID0010 dipertahankan: PR15→review16→PR17→review18→PR19→review ini.
Preserve principal/platform/atomic-claim/PA001 yang benar. Jangan mengulang
finding yang telah ditutup atau membuka task dependent untuk menghindari
koreksi. Beta **NOT_READY**; host/lab/DR/capacity belum terverifikasi.

## 2. Bloker beta — tidak berubah

Register bukti: `report/controller/20261111T074225Z-repo-handoff-review.md` §4.
Code blockers REV-1111-04/05/06/07/08/09/12 tetap terbuka; REV-1111-11
(idempotency) **tetap OPEN**: review PR19 changes_requested. Finding group-parent
REV-1311-02 dan concurrency-evidence REV-1411-04 ditutup, tetapi01/03/05
memerlukan koreksi sesuai keputusan terbaru.
Environment blockers (Gate A/G host Debian 13, lab G1 MikroTik, lab GNS3)
tetap ada. Kandidat Beta **NOT_READY**.

## 3. Cabang kerja

- `session/2026-11-15-pa006-idempotency` — kandidat penyerahan ketiga (dari
  `review/0010-pa006-controller-20261114@b6a0cb8`).
- Terbuka milik pihak lain (JANGAN ditimpa): PR7 SSTP Phase-2, PR8 planning
  audit, PR13 submission check, PR14 DANA planning draft, PR15/PR16/PR17/PR18 (riwayat task0010).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2`,
  `integration/beta-0.1`, `session/2026-11-06/07/11/13/14-*`.

## 4. Prioritas eksekusi berikutnya (urut, menunggu keputusan controller)

1. **Coding agent mengoreksi task0010** findings REV-1311-01/03 dan REV-1511-05 dari ref keputusan controller; resubmit candidate exact SHA+evidence.
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
