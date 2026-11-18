# LATEST_HANDOFF — controller R4 task0020, 18 November 2026

**Current verdict: ready / changes_requested** pada exact integrated main
**a636166ece610f23a1cdafb491e3a5ecc9e9caf9**, source/config identik executor
implementation/tested **16db545442efd33d6dd3ca13f5222efb0e80c6c4**.
Root **588 passed/1 skipped/3 warnings**, seluruh **24 frozen R1/R2/R3 PASS**,
check/makemigrations/docs PASS dan exact-main CI backend/frontend/docs3/3
success. Tetapi **4 safety assertions baru FAIL / 0 errors final runs**;
no-effect baseline4b03efe PASS membuktikan regresi baru. Tabel ini menggantikan
seluruh status historis di bawah.

| Field | Current state / pointer |
|---|---|
| Active task | **[ID0020 PA002+PA003](../task/0020-job-lifecycle-authority.md)** — **ready / changes_requested**; koreksi R4 **not_submitted**; task0010 accepted/integrated |
| Reviewed / tested source | **a636166ece610f23a1cdafb491e3a5ecc9e9caf9**, tree5768a768; protected-source diff16db545→main kosong |
| Integration / starting discovery | PR34 head19cb430 merged906bfe0; PR33 records included. 37 remote-ref entries/0 outside main ancestry/0 open PRs sebelum publication R4. Owner merge bukan acceptance. |
| Controller decision | **[R4 report](controller/20261118T025143Z-0020-r4-review.md)** §§3/7; [lifecycle](reviewer/20261118T025143Z-0020-r4-lifecycle.md), [authority](reviewer/20261118T025143Z-0020-r4-authority.md) |
| Decision ref / publication | **`review/0020-controller-r4-20261118`**; initial SHA/PR/readback dicatat setelah publikasi di report/evidence. Sebelum readback status NOT PUSHED; fetch ref keputusan bila belum merged. |
| Required corrections | **REV-1711-04 PARTIAL P1** same-job resume lintas-proses masih send2 saat old adapter hidup; **REV-1711-05 PARTIAL P1** credential-row wait outlives authority pada WG/SSTP; **REV-1811-02 P2 OPEN** final no-effect attempt tersangkut uncertain setelah lease dihapus |
| Retained closures | REV-1711-01 expiry-resurrection/healthy renewal CLOSED; REV-1811-01 duplicate typed error CLOSED;02/03/06/07/08/09 tetap sesuai batas sandbox/process. Preserve semua24 frozen, PA001/PA006. |
| Evidence | [R4 directory](controller-evidence/20261118T025143Z-0020-r4/): full588/1skip, frozen24 PASS, new4 FAIL, baseline no-effect1 PASS, split migrator/runtime PG17.11 NOSUPERUSER/NOBYPASSRLS FORCE RLS. Earlier4 connection setup errors retained separately, bukan defect produk. |
| Exact reviewed-main CI | [run44223659118](https://github.com/smahud/MicroTix_Project/actions/runs/44223659118), exacta636166 backend/frontend/docs success3/3; bukan CI untuk decision head baru |
| Next actor | **coding_agent** |
| Exact next action | Fetch R4 decision ref + current main, baca reopened packet0020/report §§3/7; tutup04/05/1811-02 pada ID sama. Buktikan4 probe baru PASS tanpa pelemahan + preserve24/full regression, positive safe recovery dan matriks A01–A09; publish exact implementation/tested/candidate SHA+reports+CI untuk controller. |
| Dependency / Beta | Task0030 ineligible. Production Beta **NOT_READY**. Installer/upgrade/restore/secrets/scheduler/DEC01/02/host/GNS3/pilot/capacity tetap scope/gates terpisah. Device/live RADIUS/browser E2E/systemd/scale NOT_RUN. |

GitHub records tidak otomatis memulai coding agent eksternal. Aplikasi tetap
read-only dalam review ini. Keputusan acceptance/merge/deploy/tag/activation
terpisah; review ini tidak memberi otorisasi tindakan tersebut. Entry tetap
[task/0000-start-here.md](../task/0000-start-here.md).

## Historical handoffs — superseded by current R4 table

# LATEST_HANDOFF — executor menyerahkan koreksi R3 task0020, 18 November 2026 (WIB ~09:2x)

**Update integrasi (sesi sama, ~09:3x WIB):** atas instruksi pemilik repo
(merge all branch, main selalu hijau, PAT commit/merge/push — preseden
PR24/25/30/31/32), branch koreksi di-merge ke main: merge commit **`906bfe0`**
(includes decision records R3 `05d268d`), kode identik dengan tested
**`16db545`** (head penyerahan `19cb430` report-only descendant).
**Exact-main CI diverifikasi: [run44223255529](https://github.com/smahud/MicroTix_Project/actions/runs/44223255529) backend/frontend/docs 3/3 success** pada head906bfe0. Seluruh remote branch kini ancestor main (**0 unmerged**); PR33/PR34
ter-merge otomatis (head kini ancestor main). Merge pemilik bukan acceptance
controller — **review koreksi R3 tetap pending** untuk exact SHA `16db545`
(next actor controller_reviewer); residual terdokumentasi REV-R3C-01/02 tetap
terbuka sebagai catatan batas.

**Current delivery: koreksi R3 task0020 selesai dan `done/pending review`.**
Executor menutup REV-1711-01/04/05 (P1) + REV-1811-01 (P2) pada ID0020 yang
sama di atas decision head `05d268d` (main `4b03efe` + records R3 dari PR33).
Probe controller R3 **FROZEN 7/7 PASS tanpa pelemahan** — failing-before
executor pada wt-base identik temuan controller (3+3 gagal/1 positif);
frozen R1/R2 **17/17 PASS**; suite penuh **589 passed/0 skipped/3 warnings**
(583 baseline + 1 tes radius yang unskip karena binary FreeRADIUS tersedia di
sandbox executor + 5 tes baru), check/makemigrations/docs PASS. Reviewer
independen read-only: REV-1711-01/05 + REV-1811-01 CLOSED; REV-1711-04 cukup
untuk scope probe dengan residual lintas-proses **REV-R3C-01 (P2 laten)**
terdokumentasi (resolve_uncertain belum punya pemanggil produksi; penutupan
otomatis berkonflik dengan closure R1 — analisis + next step pada laporan).
Tabel ini menggantikan seluruh status historis di bawah.

| Field | Current state / pointer |
|---|---|
| Canonical main saat mulai | **`4b03efedd76815af3f1c6fdf99d0739cd8dccc87`**; basis koreksi = decision head `05d268d` (branch `review/0020-controller-r3-20261118`, PR33 — protected-source diff kosong terhadap main menurut controller §1) |
| Active task | **[ID0020 PA002+PA003](../task/0020-job-lifecycle-authority.md)** — **done / pending review**; task0010 tetap accepted/integrated; task0030 belum eligible |
| Implementation / tested SHA | **`16db545`** (kode+tes saja; seluruh probe/suite/gate dijalankan pada tree kode-identik ini) |
| Published candidate | Head branch `session/2026-11-18-0020-r3-correction` (commit penyerahan — report-only descendant dari `16db545`; kode identik) |
| Laporan / bukti | [Eksekusi orchestrator](orchestrator/20261118T022200Z-0020-r3-correction.md) (matriks A01–A09 + failing-before/passing-after); [reviewer independen](reviewer/20261118T022200Z-0020-r3-correction-independent.md) (01/05/1811-01 CLOSED; 04 + REV-R3C-01/02 terdokumentasi); [evidence](executor-evidence/20261118T000000Z-0020-r3-correction/) (probe R3 7/7, frozen 17/17, suite 589/0skip, check/makemigrations/docs PASS) |
| Perubahan inti | `jobs/engine.py`: klausa lease-validity pada `_fenced`/`_fenced_update`/commit-terminal/`_verify_only` (REV01) + registry in-flight proses untuk tolakan `resolve_uncertain(applied=False)` job sama saat attempt masih berjalan (REV04); `network/services.py`: import `JobError` ter-tipe untuk penolakan duplicate finalize (REV-1811-01) + `authority_guard()` dibaca segar DI BAWAH kunci baris enrollment sebelum Router/kredensial dibuat (REV05) |
| Tes baru | `backend/tests/integration/test_jobs_r3_residuals.py` — 5 tes regresi CI (fencing expiry renewal/CAS, tolakan resolve in-flight + pemulihan, duplicate ter-tipe, guard bawah-kunci dengan lock enrollment nyata) |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA kandidat terhadap instruksi [R3 §3/§7](controller/20261117T212042Z-0020-r3-review.md): 7 probe R3 tanpa pelemahan, 17 frozen, matriks A01–A09, penutupan REV-1711-01/04/05 + REV-1811-01, dan penilaian residual terdokumentasi REV-R3C-01 (P2 laten, dengan analisis konflik terhadap closure R1) & REV-R3C-02 (P3). Acceptance/integrasi/deploy/tag tetap keputusan terpisah; `_done`/CI hijau bukan acceptance. |
| Dependency / Beta | Task0030 ineligible sampai review R3 selesai. Production Beta **NOT_READY**; install/upgrade/restore/secrets/scheduler/DEC01/02/host/lab/pilot/capacity gates terpisah. NOT_RUN: perangkat nyata/GNS3, RADIUS daemon produksi, browser E2E, systemd rehearsal, scale/soak. |

GitHub records do not automatically start an external coding agent. Entry
remains [task/0000-start-here.md](../task/0000-start-here.md). Pada sesi ini
pemilik repo menginstruksikan merge-all + push (PAT) — merge bukan acceptance.

## Historical handoffs — superseded by current table above

### LATEST_HANDOFF — controller R3 task0020, 18 November 2026

**Current verdict: ready / changes_requested pada exact main4b03efe.**
Tiga residual P1 + satu P2 baru dikonfirmasi melalui **6 assertion gagal,
0 harness errors**. Existing **583 passed/1skip/3warnings**, semua **17 frozen
R1/R2 probes PASS**, check/makemigrations/docs PASS. Satu probe positif
healthy single-I/O beyond initial expiry PASS. Status di tabel ini
menggantikan seluruh histori di bawah.

| Field | Current state / pointer |
|---|---|
| Canonical main / reviewed source | **4b03efedd76815af3f1c6fdf99d0739cd8dccc87**, tree176255e0; source/config identik executor impl cd6eea3, sudah merged PR32 sebelum review |
| Active task | **[ID0020 PA002+PA003](../task/0020-job-lifecycle-authority.md)** — **ready / changes_requested**; correction R3 **not_submitted**; task0010 accepted/integrated |
| Integration facts | PR32 actual final head48b83d9 merged8a26a1f; subsequent main changes report/navigation only. Fresh refs:0 open PRs,0 remote branch heads outside main ancestry sebelum publikasi decision ini. Merge pemilik bukan acceptance. |
| Controller decision | **[R3 report](controller/20261117T212042Z-0020-r3-review.md)** §§3/7; independent [lifecycle](reviewer/20261117T212042Z-0020-r3-lifecycle.md), [authority](reviewer/20261117T212042Z-0020-r3-authority.md) |
| Decision ref / publication | **[PR33](https://github.com/smahud/MicroTix_Project/pull/33)** review/0020-controller-r3-20261118, initial **35e0d61/tree7e6bb3b**, all49 path checks MATCH +4 key files readback +clean local fetch. [Publication](controller-evidence/20261117T212042Z-0020-r3/publication.json), R3 §8. Fetch decision ref bila belum merged; descendants preserve reviewed4b03efe source. |
| Required corrections | **REV-1711-01/04/05 PARTIAL P1**: expired lease revival; same-job resolve-negative after DB death while old adapter live; authority before enrollment lock wait. **REV-1811-01 P2 OPEN**: undefined JobError duplicate-finalize. |
| Retained closures | **02/03/06/07 CLOSED**, **08 now CLOSED** selected adapter/readback; **09 mapping/healthy renewal CLOSED** within honest process/sandbox limits. Preserve all existing fixes. |
| Root evidence | [Directory](controller-evidence/20261117T212042Z-0020-r3/): full583/1skip, old17 PASS, new7 =6 FAIL/1 PASS/0 errors. New PG17.11 split migrator-owned/runtime NOSUPERUSER/NOBYPASSRLS FORCE RLS schemas. |
| Exact reviewed-main CI | [run44166000632](https://github.com/smahud/MicroTix_Project/actions/runs/44166000632), head4b03efe, backend/frontend/docs success3/3; does not close new failures |
| Next actor | **coding_agent** |
| Exact next action | Fetch R3 decision branch, read packet/report §§3/7, close3 residual P1+newP2 on **same ID0020**. Prove all7 R3 probes passing without weakening assertions and preserve17 old probes/full required regression. Publish implementation/tested/candidate SHA+CI+reports for controller. |
| Dependency / Beta | Task0030 ineligible; Production Beta **NOT_READY**. Installer/upgrade/restore/secrets/scheduler/DEC01/02/host/GNS3/pilot/capacity gates separate. Device/live RADIUS/browser E2E/systemd/scale NOT_RUN. |

GitHub records do not automatically start an external coding agent.
Application source stayed read-only for this controller; corrections return
to executor. No merge/deploy/tag/activation authority created. Permanent
entry: [task/0000-start-here.md](../task/0000-start-here.md).

## Historical handoffs — superseded by current R3 table

### LATEST_HANDOFF — executor menyerahkan koreksi R2 task0020, 18 November 2026 (WIB ~02:47)

**Update integrasi (sesi sama, ~03:0x WIB):** atas instruksi pemilik repo
(merge all branch, main selalu hijau, PAT commit/merge/push — preseden
PR24/25/30/31), PR32 di-merge ke main: merge commit **`8a26a1f`**, kode
identik dengan tested `cd6eea3` (PR32 head48b83d9 report-only descendant).
**Exact-main CI diverifikasi: [run44162639200](https://github.com/smahud/MicroTix_Project/actions/runs/44162639200) backend/frontend/docs 3/3 success** pada head8a26a1f. Seluruh remote branch kini ancestor main (0 unmerged); merge pemilik bukan acceptance controller — review R3 tetap pending di PR32/exact SHA.

**Current delivery: koreksi R2 task0020 selesai dan `done/pending review`.**
Executor menutup kelima temuan R2 pada ID0020 yang sama di atas main `0c6403de`
(PR31 ter-merge atas wewenang pemilik; bukan acceptance). Probe controller R2
**6/6 lulus tanpa pelemahan** (file probe FROZEN), R1 lama **11/11 tetap lulus**;
suite penuh **583 passed/1 skipped** (+3 tes baru), check/makemigrations/docs/
frontend PASS. Reviewer independen: 5/5 CLOSED + 5 temuan baru REV-R2C-01..05
yang **semuanya ditutup pada sesi yang sama**. Tabel ini menggantikan seluruh
status historis di bawah.

| Field | Current state / pointer |
|---|---|
| Canonical main saat mulai | **`0c6403de2a34d47382907bed396e70bf2bc4c008`** (merge PR31 oleh pemilik — record R2 + packet0020 reopened; terintegrasi, bukan acceptance) |
| Active task | **[ID0020 PA002+PA003](../task/0020-job-lifecycle-authority.md)** — **done / pending review**; task0010 tetap accepted/integrated; task0030 belum eligible |
| Implementation / tested SHA | **`cd6eea378cd2134ca38924e8b181d1cd601f33ec`** (kode+tes saja; seluruh bukti dijalankan pada tree ini) |
| Published candidate | **PR32** head = commit penyerahan (report-only descendant dari `cd6eea3` — kode identik) |
| Laporan / bukti | [Eksekusi orchestrator](orchestrator/20261117T194548Z-0020-r2-correction.md) (matriks A01–A09 + pemetaan presisi A05/A08); [reviewer independen](reviewer/20261117T194548Z-0020-r2-correction-independent.md); [evidence](executor-evidence/20261117T191917Z-0020-r2-correction/) (exit-codes seluruh 0; probe R2 6/6, R1 11/11, suite 583/1skip, gate lengkap) |
| Perubahan inti | guard commit terkunci `SELECT..FOR UPDATE` baris job pada exit unit domain (scope/run_discovery/finalize_verification); recheck durable di bawah kunci sender pasca-acquisition (tahan kematian sesi DB); authority aktual pasca-I/O enrollment + B5/B6 + pra-I/O cabang rollback; B6 memakai adapter aktif via factory (lab gate jujur no-effect; B2/B5 seragam); watchdog heartbeat bersyarat `HEARTBEAT_S` (tidak menghidupkan lease kedaluwarsa) + verify-only; kunci baris enrollment pada unit efek (anti finalize konkuren); factory resolve dinamis |
| Tes baru | `test_jobs_long_phase_0020_r2.py` (2: fase adapter panjang vs reconciler konkuren; non-resurrection + fencing worker basi) + `test_jobs_authority_postio_0020_r2.py` (1: revoke saat APPLY I/O B6) |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA kandidat PR32 terhadap instruksi [R2 §3/§7](controller/20261117T170000Z-0020-r2-review.md): 6 assertion R2 + 11 probe R1 tanpa pelemahan, matriks A01–A09, pemetaan A05/A08, penutupan temuan baru REV-R2C-01..05. Acceptance/integrasi/deploy/tag tetap keputusan terpisah; `_done`/CI hijau bukan acceptance. |
| Dependency / Beta | Task0030 ineligible sampai review R3 selesai. Production Beta **NOT_READY**; install/upgrade/restore/secrets/scheduler/DEC01/02/host/lab/pilot/capacity gates terpisah. NOT_RUN: perangkat nyata/GNS3, RADIUS daemon nyata, browser E2E, systemd rehearsal, scale/soak. |

GitHub records do not automatically start an external coding agent. Entry
remains [task/0000-start-here.md](../task/0000-start-here.md). Pada sesi ini
pemilik repo juga menginstruksikan merge-all (PR31) — merge bukan acceptance.

## Historical handoffs — superseded by current table above

### LATEST_HANDOFF — controller R2 task0020, 18 November 2026

**Current decision: `ready / changes_requested` pada integrated main64b68f8.**
Koreksi PR30 memang sudah merged; controller menemukan4 residual P1 melalui
6 assertion gagal. Original11 probe lulus dan full suite580/1skip tetap
dipertahankan. Tabel ini menggantikan seluruh status historis di bawah.

| Field | Current state / pointer |
|---|---|
| Canonical main teramati / reviewed | **64b68f8d74b0aa593f379c75d6b5702402fd9d78**, current tree diuji sendiri; bukan source-identical terhadap impl2681a3d |
| Active task | **[ID0020 PA002+PA003](../task/0020-job-lifecycle-authority.md)** — **ready / changes_requested**; task0010 tetap accepted/integrated |
| Integration facts | PR30 **merged**, actual final head19023737/merge9eb5dacf; main memuat SSTP dan merge-all source lain. Semua32 remote branches dan0 open PR diperiksa sebelum keputusan ini; data terbaru pada report R2. |
| Decision ref / publication | **[PR31](https://github.com/smahud/MicroTix_Project/pull/31)** `review/0020-controller-r2-20261117`; initial **443b1dc48c85b023f92f88432af39e38964a92ca/tree d86c1216**, all40 path readback MATCH, clean local fetch; [publication](controller-evidence/20261117T170000Z-0020-r2/publication.json). Fetch ref ini bila belum merged; metadata descendants preserve reviewed64b68f8 source. |
| Current controller review | **[R2 changes_requested](controller/20261117T170000Z-0020-r2-review.md)**; [lifecycle reviewer](reviewer/20261117T170000Z-0020-r2-lifecycle.md), [authority reviewer](reviewer/20261117T170000Z-0020-r2-authority.md) |
| Required corrections | **REV-1711-01/04/05/08 PARTIAL P1**: atomic domain fencing, durable router/sender lifecycle, post-I/O enrollment authority WG/SSTP, B6 active-adapter honest readback. **09 PARTIAL evidence**: long-phase/current process evidence mapping. **02/03/06/07 CLOSED**; preserve their fixes. |
| Root evidence | **580 passed/1 skipped/3 warnings**, original11 probes **PASS**; new6 safety assertions **FAIL/0 errors** on PG17.11 separate migrator-owner/runtime NOSUPERUSER/NOBYPASSRLS; [evidence](controller-evidence/20261117T170000Z-0020-r2/) |
| Exact reviewed-main CI | [run44125923116](https://github.com/smahud/MicroTix_Project/actions/runs/44125923116), head64b68f8, backend/frontend/docs success3/3; not closure of6 new failures |
| Next actor | **coding_agent** |
| Exact next action | Fetch decision R2, read reopened packet0020 + report §3/§7, close the residuals on **same ID0020**, prove6 probes passing without weakening them and preserve11 old probes + required full regression. Publish new exact implementation/tested/candidate SHA, independent reports and CI for controller re-review. New R2 correction delivery **not_submitted**. |
| Dependency / Beta | Task0030 ineligible. Production Beta **NOT_READY**; install/upgrade/restore/secrets/scheduler/DEC01/02/host/lab/pilot/capacity separate. No merge/deploy/tag/activation authorization created. |

GitHub records do not automatically start an external coding agent. Current
source was kept read-only by this controller; application fixes return to
executor. Entry remains [task/0000-start-here.md](../task/0000-start-here.md).


### LATEST_HANDOFF — 17 November 2026: task0020 koreksi diserahkan + merge-all branch ke main (wewenang pemilik)

**Update integrasi (sesi sama, ~00:5x WIB):** pemilik repo menginstruksikan
merge-all branch ke main dengan PAT commit/merge/push (preseden PR9/PR24/25).
Seluruh branch kini ter-merge; main maju jauh dari 41d1f33 melalui merge
koreksi task0020 (PR30 lineage) + branch historis; keputusan penyelesaian
record-only vs kode-canonical tercatat pada
[integrasi merge-all](orchestrator/20261117T170000Z-merge-all-integration.md).
Suite penuh 580 passed/1 skip + checks/docs PASS pada tree final sebelum
push. PR historis stale (16/18/20/23/29) ditutup dengan komentar penjelasan
karena head kini ancestor main — bukan close paksa: kontennya sudah
terintegrasi penuh di main.
REVIEW TASK0020 TETAP PENDING di PR30 — merge pemilik bukan acceptance
controller.

Pintu masuk: [task/0000-start-here.md](../task/0000-start-here.md).
Fetch current main, candidate dan decision ref sebelum melanjutkan. Tabel ini
menggantikan status historis di bawah; tanggal pengguna Asia/Jakarta.

**Penyerahan koreksi 17 November ~23:59 WIB (sesi ini):** coding agent
menutup **REV-1711-01–09 pada ID0020 yang sama** dari decision ref PR29
(fetched sampai `0e45157`). Probe controller R1 (11 assertion):
**failing-before 11 failed pada source kandidat bd37c14 → passing-after
11 passed** pada tree koreksi, diulang pada DB split-role (migrator-owned,
runtime NOSUPERUSER/NOBYPASSRLS, 59 tabel FORCE RLS). Suite penuh
**562 passed/1 skipped/3 warnings** (+8 tes bukti REV-1711-09);
PA-001 33, PA-006 125, RLS 8 lulus; check/makemigrations/docs PASS.
[Reviewer independen](reviewer/20261117T160500Z-0020-correction-independent.md):
REV-1711-01–09 **CLOSED**, nol pelemahan assertion; temuan P2 reviewer
(CORR-REV-01 no_effect blanket, CORR-REV-02 jendela hard-crash pra-reconcile)
ditutup sebelum commit. Execution status **done**, review **pending** —
bukan accepted; `_done` bukan acceptance/merge/deploy.

| Field | Current state / pointer |
|---|---|
| Canonical main teramati | **41d1f33f16508491a34f66b767830b9dd3e5954e**; main tidak diubah sesi ini |
| Active task | **[ID0020 PA-002+PA-003](../task/0020-job-lifecycle-authority.md)** — **done / pending review / not integrated** |
| Correction branch + PR | `session/2026-11-17-0020-job-lifecycle-correction` (base `0e45157` membawa source PR27); implementation/tested **`2681a3d`**, published head **`062a017`**; candidate **[PR30](https://github.com/smahud/MicroTix_Project/pull/30)** target main; CI exact head **[run44119619011](https://github.com/smahud/MicroTix_Project/actions/runs/44119619011) backend/frontend/docs success 3/3** terverifikasi ([ci evidence](executor-evidence/20261117T150000Z-0020-correction/ci-pr30.txt)) |
| Decision ref | **[PR29](https://github.com/smahud/MicroTix_Project/pull/29)** `review/0020-controller-20261117`; verdict acceptance tetap [controller R1](controller/20261117T134100Z-0020-job-lifecycle-review.md) sampai controller mereview SHA koreksi |
| Correction evidence root | [executor-evidence/20261117T150000Z-0020-correction/](executor-evidence/20261117T150000Z-0020-correction/) — failing-before/passing-after probe, split-role migrate/grant/RLS, check, makemigrations, docs, full-suite 562, targeted subsets, environment |
| Coreksi inti | Guard ownership DALAM transaksi unit domain (scope+assert_owned; heartbeat/progress raise); no_effect eksplisit + default uncertain post-efek; retry lineage root-lock+BFS; hold durable router unknown (+expired-executing); authority di batas efek pasca-preflight; HTTP router scope 404; B6 APPLY/VERIFY di luar transaksi; B6 readback negatif jujur; +bukti SIGINT/active-barrier/stop-claim/long-phase/crash-after-commit/current-policy |
| Independent reviewer | [Koreksi](reviewer/20261117T160500Z-0020-correction-independent.md); [lifecycle](reviewer/20261117T140000Z-0020-lifecycle-independent.md), [authority](reviewer/20261117T140000Z-0020-authority-independent.md) histori R1 |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA koreksi atas REV-1711-01–09 (jalankan ulang probe R1 + matriks [laporan koreksi §5](orchestrator/20261117T160000Z-0020-correction-delivery.md)), delta main/candidate+CI; changes-requested membuka kembali ID0020 yang sama; jangan buka task0030 sebelum prasyarat terpenuhi |
| Accepted predecessor | **Task0010/PA-006 tetap accepted/integrated**, PR24/25 merged; P3 R5 thread assertions preserved; tidak dibuka kembali |
| Other refs | PR26/27/28/29/30 kini ancestor main (merge-all pemilik — bukan acceptance); histori PR task0010 serta PR7/8/14 dipertahankan; tidak ada force-push/reset pekerjaan pihak lain |
| Beta / limits | **NOT_READY**; sandbox engine/PG/proses nyata saja — installer/upgrade/restore/secret/scheduler/DEC-01/02 dan host/GNS3/pilot/kapasitas tetap terpisah. OS/device/live RADIUS/browser/benchmark NOT_RUN; simulator bukan perangkat nyata |

## Histori — resume checkpoint & R1 (digantikan penyerahan koreksi di atas)

**Resume 17 November ~21:48 WIB:** 31 branches/14 open PRs diperiksa;
belum ada penyerahan koreksi baru (**correction delivery not_submitted**).
Main41d1f33, PR27bd37c14 dan starting decision43043be unchanged; seluruh
source/config identik. [Checkpoint controller](controller/20261117T144620Z-0020-resume-review.md)
dan [independent check](reviewer/20261117T144620Z-0020-resume-independent.md)
dipublikasikan pada existing PR29. Verdict R1 tetap **ready /
changes_requested**, next **coding_agent** menutup REV-1711-01–09 pada
ID0020 yang sama. Existing CI43043be kini **completed success3/3**, bukan
bukti penutupan finding atau CI commit checkpoint yang lebih baru.
Runtime review tidak diulang pada source yang tidak berubah. Publication
ancestor/readback mengikuti checkpoint §6; final-head CI mengikuti PR29.

| Field | Current state / pointer |
|---|---|
| Active task (saat resume) | **[ID0020](../task/0020-job-lifecycle-authority.md)** — **ready / changes_requested / not integrated** |
| Exact reviewed candidate | **[PR27](https://github.com/smahud/MicroTix_Project/pull/27)** `bd37c14e6c41339a8743b3d4b723ee74f13bef08`; executor tested ancestor7118cce, source/app delta kosong |
| Decision ref | **[PR29](https://github.com/smahud/MicroTix_Project/pull/29)** `review/0020-controller-20261117`, initial decision **3c4b71fa75ab0619bf12b84660a8678b99294e20/tree9b7d2405** verified |
| Evidence root R1 | Full backend **554 passed,1 skipped,3 warnings**; **11 acceptance probes FAIL / 0 harness errors** pada fresh PG17.11 migrator-owned schema + runtime nonowner/NOBYPASSRLS/FORCE RLS; [summary](controller-evidence/20261117T134100Z-0020-review/review-results.json) |
| Blocking findings | **REV-1711-01–08**: stale domain commit, blind retry setelah efek, retry lineage unknown, router unreadback hold, after-preflight authority, HTTP router scope, B6 I/O transaction dan B6 false success; **09** missing required evidence (drain SIGINT/active DB, long-phase/policy/recovery) |
| Candidate CI | Existing run43994355914 exact **bd37c14 success backend/frontend/docs3/3**; tidak menutup probe acceptance gagal |
| Independent reviewers R1 | [Lifecycle](reviewer/20261117T140000Z-0020-lifecycle-independent.md), [authority](reviewer/20261117T140000Z-0020-authority-independent.md); root memeriksa source+menjalankan PG probes |
| Next actor (saat resume) | **coding_agent**: fetch decision ref, tutup REV-1711-01–09 menurut packet/controller §3, preserve PA-001/006, submit kode+tes+matriks evidence+exact SHA baru+CI |
| Accepted predecessor | **Task0010/PA-006 tetap accepted/integrated**, PR24/25 merged; P3 R5 thread assertions preserved; tidak dibuka kembali |
| Other refs | PR26 instruction, PR28@8204ba0 report-only state check, histori PR task0010 serta PR7/8/14 dipertahankan; tidak ada merge/close/force-push |
| Beta / limits | **NOT_READY**; sandbox defects di atas + installer/upgrade/restore/secret/scheduler/DEC-01/02 dan host/GNS3/pilot/kapasitas tetap terpisah. OS/device/live RADIUS/browser/benchmark NOT_RUN; simulator bukan perangkat nyata |

Initial decision commit/ref/tree +39path readback MATCH, clean local fetch
terverifikasi; metadata descendant hanya mencatat publikasi yang sudah ada.
Final head/CI mengikuti PR29; packet tidak otomatis memulai external coding agent.

## Histori — penyerahan executor task0020 (digantikan review R1 di atas)

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md).
Fetch remote refs/PR dan baca CONTRACT §6A sebelum bertindak. Tanggal pengguna Asia/Jakarta, filename evidence UTC.

## Current state — 17 November 2026, ~08:10 WIB: executor menyerahkan task0020 (penyerahan pertama)

**Task0020 / PA-002+PA-003 done (scope executor + tes wajib) / pending review.**
Executor Z.ai sandbox mengambil packet dari instruction ref PR26
`review/0020-job-lifecycle-authority-20261117` @ ea7b8a1 setelah memverifikasi
main tidak berubah (41d1f33). PA-006 tetap accepted/integrated (tidak dibuka).

| Field handoff | Status / pointer |
|---|---|
| Canonical main teramati | **41d1f33f16508491a34f66b767830b9dd3e5954e** — tidak berubah saat sesi; fetch ulang sebelum bertindak |
| Active task | [ID0020 / PA-002+PA-003](../task/0020-job-lifecycle-authority.md) — **done / pending** |
| Candidate branch | `session/2026-11-17-0020-job-lifecycle-authority` dari instruction ref ea7b8a1; implementation/tested **`7118cce0db330acb02be0b3b774b1b1628d55d7a`** (engine 6e96ce3 + fix test-infra CI); **[PR27](https://github.com/smahud/MicroTix_Project/pull/27)** published head `6c8d9206a4a875dd07f3b1bc3b04cbb0d7758b76` — record di atas impl report-only, `git diff 7118cce 6c8d920 -- backend/ apps/` kosong |
| Perubahan inti | Engine jobs: CAS fencing penuh (termasuk commit hasil terminal di klausa WHERE), unit transaksi tenant pendek tanpa lock melintasi I/O adapter, cancel pra-efek atomik + epoch-bump (executing jujur 409), effect_state=maybe atomik pra-execute, advisory lock pengirim per-router (busy requeue tanpa konsumsi attempt), reconcile state/effect-aware CAS idempotent (claimed/preflight requeue via retry_wait; executing/verifying → uncertain), resolve readback protocol (penulis lama wajib terbukti berhenti; applied=True verify tanpa resend; unknown tertahan), retry diserialisasi (uncertain/recovery_required dianggap aktif), deadline claim + pra-efek (dibaca segar), progress memperpanjang lease; authority fresh-DB peta kind fail-closed + provenance verify_api_ssl dari enrollment.created_by + karantina actorless dengan resume + recheck antar fase kirim cutover; HTTP job detail/retry/cancel izin operasi dasar + step-up sensitif + 403/404; RouterReplaceView → routers.release; handler hilang/verifier negatif fail-closed; runworker drain SIGTERM/SIGINT + drain-timeout + exit 0/3. **Tanpa migrasi schema** (jobs/0004/0005 tak tersentuh) |
| Bukti kunci | **Full suite 554 passed + 1 skipped** (PG 17.11 nyata, peran non-superuser, FORCE RLS; +41 tes baru); **failing-before pada baseline 41d1f33: 33/37 lifecycle + 4/4 drain GAGAL → passing-after 41/41**; PA-001 + PA-006 (incl. R4/R5 replay migrasi) lulus utuh; check/makemigrations/docs PASS; frontend tsc/eslint/vitest 66/i18n/build lulus; P3 REV-1611-TEST-01 ditutup test-only |
| Review independen | [Reviewer](reviewer/20261117T010218Z-0020-job-lifecycle-independent.md) pra-koreksi **CHANGES_REQUESTED** (REV-2011-01 P1; 02–04 P2; 05–10 P3) — seluruh temuan ditindaklanjuti dengan koreksi + tes baru (matriks §3 laporan eksekusi); internal review ≠ acceptance |
| Execution report | [Orchestrator](orchestrator/20261117T010218Z-0020-job-lifecycle-authority.md) — inventaris kind, matriks A01–A09 → evidence, runbook drain, batas; [evidence dir](executor-evidence/20261117T000000Z-0020-job-lifecycle/) |
| Candidate CI | **[run 43993939448](https://github.com/smahud/MicroTix_Project/actions/runs/43993939448)** exact `6c8d920` **backend/frontend/docs 3/3 success** terverifikasi (01:16Z; [evidence](executor-evidence/20261117T000000Z-0020-job-lifecycle/ci-final.txt)); run awal fc6a425 backend gagal (password auth CI pada subprocess drain) — ditutup test-infra `7118cce`, suite diulang lokal 554 passed |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA `7118cce` (kode+tes; tree published identik — verifikasi `git diff 7118cce0db330acb02be0b3b774b1b1628d55d7a HEAD -- backend/ apps/` kosong) atas matriks acceptance J20-A01..A09 laporan eksekusi §4 dan penutupan REV-2011-01..10 §3; changes-requested membuka kembali ID0020 yang sama; jangan buka task0030 sebelum prasyarat review/integrasi terpenuhi |
| Batas / Beta | Production Beta **NOT_READY**; bloker register 11 Nov tidak berubah (installer/upgrade/worker ops/restore/DEC-01/DEC-02/scheduler/REV-1111-*/kapasitas + gates host/lab). OS install/upgrade/restore/DR, real drain service, CHR/GNS3/router/pilot, E2E browser, benchmark NOT_RUN; simulator/CI bukan bukti perangkat nyata |

## Prior controller publication — 17 November 2026: task0020 disiapkan (superseded oleh penyerahan di atas)

| Field | Current state / pointer |
|---|---|
| Canonical main observed | **41d1f33f16508491a34f66b767830b9dd3e5954e**; exact CI [43857508367](https://github.com/smahud/MicroTix_Project/actions/runs/43857508367) backend/frontend/docs3/3 success |
| Instruction ref | **`review/0020-job-lifecycle-authority-20261117`** — record/task branch belum merged saat disiapkan; fetch current head dan gunakan ref ini, bukan instruksi lama main |
| Active task | **[0020 — PA-002 + PA-003](../task/0020-job-lifecycle-authority.md)**, current jobs lifecycle/fencing/drain/authority |
| Execution / review / implementation | **ready / not_submitted**; belum ada kandidat kode, hasil tes atau acceptance0020 |
| Accepted predecessor | [0010_done](../task/0010-pa006-idempotency_done.md): **done / accepted / integrated**; R5 exacta301a94, PR24+PR25 merged. Tidak dibuka ulang |
| Controller decision | [Review current main + packet](controller/20261116T231131Z-0020-job-lifecycle-review.md), [remote state](controller-evidence/20261116T231131Z-0020-discovery/remote-state.json) |
| Scope / evidence | A01–A09: all-write fencing, short RLS DB units, external sender/cancel/readback, early-crash recovery, current authority, HTTP permissions/verifier, real-process drain, legacy compatibility. Dua independent source/prerequisite reviews + packet QA pada controller report |
| Main CI actual | Backend **513 passed,1 skipped,3 warnings** (FreeRADIUS binary unavailable); frontend66 tests; docs PASS24/106. Integrator historical514 real-binary tetap attributed; root tidak menjalankan ulang aplikasi |
| Publication | **[PR26](https://github.com/smahud/MicroTix_Project/pull/26)**; initial ancestor **e11d48b4fdc0c1757c52af7d9e528437b5afa0bc**, tree653db3cf. Ref/commit/PR dan seluruh10 file content+blob readback MATCH; [publication evidence](controller-evidence/20261116T231131Z-0020-discovery/publication.json). Metadata descendants record-only; final-head CI dicek terpisah pada PR26 |
| Next actor | **coding_agent** |
| Exact next action | Fetch instruction ref ini atau descendant yang sudah terintegrasi; jalankan task0020 dengan PG/race/process evidence, submit exact SHA+PR+report untuk controller. File tidak otomatis menjalankan external coding agent |
| Beta / remaining gates | **NOT_READY**; installer/upgrade/restore/secret/scheduler/topology DEC-01/DEC-02 dan host/CHR/GNS3/pilot/capacity belum ditutup. Tidak ada merge/deploy/aktivasi/tag dalam sesi reviewer ini |

Root environment lokal tidak tersedia: shell/PG/process/docs validator lokal NOT_RUN; source/refs/CI diperiksa langsung dari GitHub. Publication branch records hanya dokumen, bukan perbaikan aplikasi. PA-001 financial atomic locks dan PA-006 replay/security tetap preserved. PR7/8/14 serta historical branches dipertahankan.

## Historical handoff — superseded current pointers; audit trail retained

### LATEST_HANDOFF — 16 November 2026: PA-006 task0010 terintegrasi ke main (PR24+PR25); next packet PA-002/PA-003

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md),
CONTRACT §6A. Fetch remote refs/PR sebelum bertindak. Status integrasi di
bawah kini ada pada **main aktual** (bukan lagi branch kandidat); commit
record menaikkan main setelah merge — fetch HEAD aktual setiap sesi. Tanggal
Asia/Jakarta; evidence filename UTC.

## Latest state — 16 November 2026, ~18:25 WIB: integrasi task0010 selesai

**Task0010 / PA-006 done / accepted / integrated.** PR24 (kode exact
a301a94) dan PR25 (keputusan R5) merged ke main atas wewenang eksplisit
pemilik repo (PAT "commit, merge, atau push" — preseden PR9; approval =
R5 accepted; merge ≠ deploy). Bagian setelah tabel ini histori; status
current mengikuti tabel ini dan [laporan integrasi](orchestrator/20261116T111835Z-0010-pa006-integration.md).

| Field handoff | Status / pointer |
|---|---|
| Canonical main | **022e9d05f02e5a1f17de8ea7fe59adcea9a5f9fe** — commit record integrasi; remote readback terverifikasi + CI exact head **3/3 success** — di atas merge PR24 `532862be2711f26d537ae1df540258bbdcae2052` → merge PR25 `fd0f3faa84ea87c142d37da5dacf01e22a493f90`; tree aplikasi `f283fe9` byte-identik dengan head keputusan R5 `c352bce` yang diuji; fetch HEAD aktual setiap sesi |
| Active task | [ID0010 / PA-006](../task/0010-pa006-idempotency_done.md) — **integrated** |
| Execution / review / integration | **done / accepted / integrated**; merge bukan deployment/aktivasi/release |
| Integrasi | PR24 merged 11:17:20Z (parents 9903d9b+a301a94, tree bec63b5 = tree reviewed); PR25 retarget base main + merged 11:17:44Z (parents 532862b+c352bce, tree f283fe9 = tree teruji); remote readback SHA/tree/PR-state diverifikasi; PR7/8/14 tak tersentuh |
| Verifikasi integrasi (executor) | Full suite **514 passed** (PG 17.11 nyata non-superuser + FreeRADIUS 3.2.7 real binary) + check 0 issue + makemigrations no-change + docs PASS 24 files/106 links pada tree final; bootstrap migrasi bersih dari initdb (termasuk jobs.0004/0005); [laporan integrasi](orchestrator/20261116T111835Z-0010-pa006-integration.md) + [evidence](executor-evidence/20261116T111835Z-0010-pa006-integration/) |
| Candidate CI (exact tree) | [43846763713](https://github.com/smahud/MicroTix_Project/actions/runs/43846763713) success 3/3 pada a301a94; CI c352bce 3/3 success (tree = main final aplikasi); CI record commit `022e9d0` **3/3 success terverifikasi** (teramati 11:24Z; [evidence](executor-evidence/20261116T111835Z-0010-pa006-integration/ci-record-commit.txt)) |
| Keputusan controller | R5 accepted pada exact a301a94 — [review](controller/20261116T101809Z-0010-pa006-r5-review.md), publikasi PR25 (tabel histori di bawah); tetap verdict pemilik acceptance |
| Nonblocking follow-up | REV-1611-TEST-01 P3 (assert completion thread/hasil tes R5) tetap terbuka untuk hardening test-only di packet berikutnya; tidak membuka kembali PA-006 |
| Next actor | **controller_reviewer** |
| Exact next action | Siapkan packet **PA-002 bersama authority PA-003** (job lifecycle fencing/drain/authority) dari main terintegrasi, menautkan accepted a301a94 + R5 review; REV-1611-TEST-01 P3 dapat dibundel. Jangan minta submission keenam PA-006 atau buka task0020 sebelum packet itu dibuat |
| Batas / Beta | Production Beta **NOT_READY**; bloker register [review 11 Nov §4](controller/20261111T074225Z-repo-handoff-review.md) tidak berubah (installer/upgrade/worker/restore/DEC01/DEC02/scheduler/REV-1111-11/kapasitas + gates host/lab). OS install/upgrade/restore/DR, real drain, CHR/GNS3/router/pilot, E2E browser, benchmark NOT_RUN |

## Prior controller decision — 16 November 2026, 17:25 WIB (acceptance; selesai diintegrasikan di atas)

**Task0010 / PA-006 accepted pada exact PR24 a301a94. REV-1311-01 CLOSED.**
Seluruh closure R4 dipertahankan; tidak ada blocker baru dalam scope.
Bagian setelah tabel ini menyimpan histori penyerahan/keputusan lama;
status current mengikuti tabel ini dan ref keputusan R5 yang diverifikasi.

| Field handoff | Status / pointer |
|---|---|
| Canonical main | **9903d9b0cf09d737b553da3c21067b4810e956c0**, tidak berubah; PR24 belum merged |
| Active task | [ID0010 / PA-006](../task/0010-pa006-idempotency_done.md) |
| Execution / review / integration | **done / accepted / pending**; acceptance kode bukan release/merge |
| Candidate / exact reviewed SHA | [PR24](https://github.com/smahud/MicroTix_Project/pull/24), `session/2026-11-16-pa006-rev1311-01-correction` **a301a94c2b3268679065e85bbef66f35949483f7**, source ancestor7338a72 |
| Controller decision ref | **[PR25](https://github.com/smahud/MicroTix_Project/pull/25)** `review/0010-pa006-controller-r5-20261116`, targets PR24. Initial decision6201ae959a2d84556c9a54ec2d552d996e8063c9/tree31731ba5; ref/commit/PR +7file readback and clean local fetch verified. [R5 review](controller/20261116T101809Z-0010-pa006-r5-review.md) §7; metadata descendant record-only; final publication CI recorded in PR25 |
| Root evidence | **514 passed** backend +**13 passed** retained controller probes; actual old-code HTTP→0004/0005→canonical retry **10/10 PASS**,20 complete concurrent responses, submission/file/decision tetap1; split-role FORCE RLS; [summary](controller-evidence/20261116T101809Z-pa006-r5/upgrade-summary.json) |
| Candidate CI | [43846763713](https://github.com/smahud/MicroTix_Project/actions/runs/43846763713), exacta301a94, **success backend/frontend/docs3/3** |
| Independent reviewers | [migration](reviewer/20261116T101809Z-0010-r5-migration-independent.md), [acceptance](reviewer/20261116T101809Z-0010-r5-acceptance-independent.md); source/pure probes terpisah dari root PG/HTTP |
| Nonblocking follow-up | REV-1611-TEST-01 P3: assert kedua thread/hasil pada tes R5; acceptance dibuktikan probe root lengkap. Opaque-garbage>64 fail-stop tetap ops note |
| Next actor | **controller_reviewer** |
| Exact next action | Selesaikan integrasi PR24 + keputusan R5 sesuai CONTRACT §11 (authority/approval, current-main delta, locked head, CI, remote readback); setelah integration prerequisite terpenuhi, siapkan packet PA-002 bersama authority PA-003. Jangan minta submission keenam PA-006 atau buka0020 sebelum prasyarat terpenuhi |
| Batas / Beta | Production Beta **NOT_READY**; installer/recovery/scheduler/job lifecycle, DEC01/DEC02 dan host/GNS3 gates masih ada. Tidak ada merge/deploy/tag; install/OS/real service drain/DR/perangkat/pilot/benchmark NOT_RUN |

## Prior executor delivery — 16 November 2026, ~17:10 WIB


Executor (Z.ai sandbox) menyerahkan koreksi REV-1311-01 — satu-satunya
finding terbuka keputusan controller R4 (PR21 `634da42`, PR23) — pada ID
yang sama. Branch kandidat `session/2026-11-16-pa006-rev1311-01-correction`
dari head keputusan R4 `4bb7261` (kode PR21 + packet reopened dibawa
bersama); **implementation `7338a720b5d64a4ccb47b9abe7d3dc6feca0a476`**
(delivery docs report-only di atasnya). Perubahan source: satu file —
parser migrasi `jobs/0004` ditulis ulang grammar-driven (semua posisi
kolon; validitas menurut stdlib uuid.UUID yang sama dengan writer
baseline; literal `platform` exact-case; interpretasi unik; ambiguity →
fail-stop `AmbiguousLegacyScope` rollback atomik; 0 interpretasi → baris
mati seperti kebijakan lama) + kebijakan affected-state eksplisit.

| Field handoff | Status / pointer |
|---|---|
| Active task | ID0010 / PA-006 — **penyerahan kelima** |
| Execution / review | `done` (scope executor + tes wajib) / `pending` — menunggu controller review exact SHA |
| Candidate branch / tested SHA | **[PR24](https://github.com/smahud/MicroTix_Project/pull/24)** `session/2026-11-16-pa006-rev1311-01-correction`; implementation **`7338a72`**, published head **`a21624f`** (readback diverifikasi); CI [43846332048](https://github.com/smahud/MicroTix_Project/actions/runs/43846332048) exact-head **success 3/3** (backend/frontend/docs) — bukan acceptance |
| Bukti kunci | **Live upgrade 7/7 PASS** (old main@9903d9b HTTP → migrasi 0004/0005 → retry kanonik; parser cacat direproduksi GAGAL dulu 3 varian); **62 tes r5** (failing-before 21 GAGAL pada parser PR21); **full suite 514 passed** (PG nyata, non-superuser, FreeRADIUS real-binary); family 139 passed; check/makemigrations/docs PASS |
| Review internal | [Independent r5](reviewer/20261116T100420Z-0010-pa006-r5-independent.md) — **APPROVE_WITH_NOTES**; brute-force 33.674 pasangan ejaan valid writer 0 anomali, fuzz 400.000 string 0 fail-stop palsu, tidak ada counterexample; REV-R5-01/03 ditutup, REV-R5-02 (pre-existing P3) dicatat runbook ops |
| Execution report | [Executor kelima](orchestrator/20261116T100420Z-0010-pa006-idempotency.md) — matriks acceptance R4 §4 + evidence; [executor-evidence](executor-evidence/20261116T090000Z-0010-pa006-r5/) |
| Packet | [0010-pa006-idempotency_done.md](../task/0010-pa006-idempotency_done.md) — metadata penyerahan kelima + ringkasan hasil |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact head PR24 `a21624f` (pohon source identik `7338a72`) atas matriks koreksi R4 laporan executor §4; changes-requested membuka kembali ID0010 yang sama |
| Batas | NOT_RUN: install/upgrade/restore produksi, perangkat/lab, deployment, E2E browser, benchmark. Internal review ≠ acceptance. PA-002/003 belum eligible; Beta **NOT_READY**; tidak ada merge/deploy/tag |

## Prior state verification — 16 November 2026, 13:50 WIB

[Controller checkpoint](controller/20261116T065005Z-0010-pa006-state-review.md)
memeriksa25 branch /13 open PR dan exact-head CI: main9903d9b,
candidate PR21@634da42 serta starting decision PR23@82b2216 tidak berubah.
**Belum ada kandidat koreksi baru**; delivery **not_submitted**, task0010
**ready / changes_requested**, next **coding_agent** menutup REV-1311-01
pada ID yang sama. Semua closure R4 dipertahankan; PA-002/003 belum eligible,
Beta **NOT_READY**. Current source/config identik; hasil runtime R4 tidak
diulang. Existing CI43679221142 dan43715610125 masing-masing success3/3;
bukan acceptance atau CI publikasi baru. [Independent review](reviewer/20261116T065005Z-0010-pa006-state-review.md), record QA,
commit/ref/file readback dan CI publikasi berada pada report/PR23.

## Prior state verification — 15 November 2026, sesi19:39 WIB

[Controller checkpoint](controller/20261115T123944Z-0010-pa006-state-review.md)
dan [independent review](reviewer/20261115T123939Z-0010-pa006-state-review.md):
25 branch /13 open PR, main9903d9b dan candidate PR21@634da42 tetap;
starting decision PR23@80dfc89. **Belum ada kandidat koreksi baru**;
delivery `not_submitted`, task0010 **ready / changes_requested**, next
**coding_agent** memperbaiki REV-1311-01 saja pada ID sama. Seluruh closure
R4 dipertahankan. Source/config delta kosong; docs PASS24files/106links;
runtime acceptance tidak diulang. Existing candidate CI43679221142 dan
starting-decision CI43703894306 masing-masing success backend/frontend/docs.
Hasil80dfc89 ini menggantikan observasi lama17:23 WIB yang belum melihat
run; bukan CI checkpoint baru atau acceptance. Publikasi tetap existing
PR23, dengan remote readback dan final-head CI pada report/deskripsi PR.
PA-002/003 belum eligible; Beta **NOT_READY**.

## Prior state verification — 15 November 2026, 17:13 WIB

[Controller checkpoint](controller/20261115T101333Z-0010-pa006-state-review.md)
dan [independent review](reviewer/20261115T101317Z-0010-pa006-state-review.md):
25 branch /13 open PR; main9903d9b, candidate PR21@634da42 dan starting
decision PR23@1bc84a44 terkonfirmasi. **Belum ada kandidat koreksi baru.**
Correction delivery `not_submitted`; task0010 tetap **ready /
changes_requested**, next **coding_agent** menutup REV-1311-01 saja.
Semua closure R4 dipertahankan. Source/config identik; docs validator
PASS24files/106links. Tidak ada runtime acceptance ulang. Checkpoint pada
existing PR23; PA-002/003 tetap ineligible, Beta **NOT_READY**.
Publikasi/CI checkpoint ini mengikuti report dan deskripsi PR23; hasil CI
head lama tidak dianggap sebagai hasil head baru.

## Prior resume verification — 15 November 2026, mulai13:56 WIB

[Controller resume](controller/20261115T065656Z-0010-pa006-resume-review.md)
dan [independent state check](reviewer/20261115T065656Z-0010-reviewer-resume-state.md)
memeriksa25 branch/13 PR terbuka: main9903d9b, candidate PR21@634da42 dan
starting decision PR23@30ce815 tetap sama. **Belum ada kandidat koreksi baru**;
correction delivery `not_submitted`, existing task tetap **ready /
changes_requested**, next **coding_agent**. Keputusan R4 dan semua closure
di bawah tetap berlaku. PR22 state check mendahului PR23, bukan instruksi
untuk mengulang review634da42.

Pure parser probe20 kasus kembali menunjukkan8 pemetaan legacy gagal;
bukan tes HTTP/PG/file baru. Protected source/config identik dengan634da42;
docs validator PASS24files/106links. Existing candidate dan starting-decision
CI backend/frontend/docs success diverifikasi ulang dari GitHub; bukan CI
untuk checkpoint baru. Publikasi checkpoint dilanjutkan pada **existing PR23**.
Tidak ada task/PR baru atau dependency yang dibuka. Next action tetap
koreksi REV-1311-01 pada0010, lalu serahkan SHA baru untuk review.

Checkpoint publication verified: **d7be2ba8667149ed47ec4b11b5da10d5811e7a4a**,
treeefed9596, existing PR23; ref/PR/all10file readback dan clean local
fetch/checkout cocok. Metadata descendant hanya mencatat publikasi ini.
CI checkpoint baru belum terbit saat pencatatan (0 check-runs, belum ada
workflow untuk head baru); final observation ada pada deskripsi PR23.
Keberhasilan CI634da42/30ce815 tetap terikat pada SHA historis masing-masing.

## 0. Histori keputusan R4 — digantikan verdict R5 di atas

**Review penyerahan keempat PR21 selesai: changes_requested.**
**Satu finding terbuka REV-1311-01 P1 (partial)**: migrasi belum menangani
seluruh UUID prefix yang benar-benar diterima kode lama. Actual old HTTP
`uuid:<UUID>` completed/ambiguous dan `urn:<UUID>` completed→0004/0005→
canonical retry membuat submission **dan physical proof file1→2**.
Retained `__unparsed__` row tidak ditemukan lookup runtime. Standard URN
known/unknown sudah PASS. **03A/03B/05 CLOSED**;02/04 dan PA-001 tetap lulus.

| Field | Status / pointer |
|---|---|
| Canonical main teramati | **9903d9b0cf09d737b553da3c21067b4810e956c0**; belum berubah/merged |
| Active task | [0010 / PA-006](../task/0010-pa006-idempotency_done.md), ID sama dibuka kembali unfinished |
| Execution / review | **ready / changes_requested** |
| Candidate / exact reviewed SHA | [PR21](https://github.com/smahud/MicroTix_Project/pull/21), branch `session/2026-11-15-pa006-idempotency-correction` @ **634da4224f15dd6a5a4e9010fe1811dec8c7954d** |
| Tested source ancestry | Executor implementation **b71574d8b6ba1dc30d132551684791f760e8abc6**; root tests on exact634da42. Later delivery commits metadata only; app/config diff empty |
| Instruction ancestry | PR20 `e507175`→b71574d→delivery0372dc4→metadata7b574d0→634da42; preserve all prior valid work |
| Execution/internal reports | [Executor R4](orchestrator/20261115T044621Z-0010-pa006-idempotency.md), [internal review](reviewer/20261115T044616Z-0010-pa006-r4-review.md); executor closure claims are history, not controller acceptance |
| Latest controller decision | [Controller R4](controller/20261115T053138Z-0010-pa006-r4-review.md); [upgrade/security reviewer](reviewer/20261115T053213Z-0010-r4-upgrade-security.md), [HTTP identity reviewer](reviewer/20261115T053229Z-0010-r4-http-identity.md) |
| Decision ref / publication | [PR23](https://github.com/smahud/MicroTix_Project/pull/23), `review/0010-pa006-controller-r4-20261115`, targeting PR21 branch. Initial published ancestor **5c31ed63b5e88e2e6c92565c47e60d947dd81666**, tree0031a9ed, remote ref/files/local clean fetch verified; metadata descendant preserves source, controller report §7 |
| Candidate CI | [43679221142](https://github.com/smahud/MicroTix_Project/actions/runs/43679221142), exact634da42 backend/frontend/docs **success**; does not close failing upgrade acceptance |
| Next actor | **coding_agent** |
| Exact next action | Fetch this controller decision ref, fix remaining **REV-1311-01** accepted legacy UUID grammar/reconciliation on task0010, preserve CLOSED03A/03B/05/02/04/PA001, prove old-source migration/retry effects1 and resubmit new exact SHA + report + CI |
| Dependencies | PA-002/003 remain ineligible; no task0020, merge, deployment, activation or release tag |

## 1. Verified scope and evidence limits

Root independent PostgreSQL17.11 runtime NOSUPERUSER/NOBYPASSRLS:
**93 targeted +452 full +6 prior controller probes +2 conformance edges
+5 selected/wait-graph probes PASS**. All ten PA-001 cases pass. Django
system/migration/docs checks PASS. Four actual wait graphs assert query and
blocker, including after-write rollback/contender takeover. Secret presence
fresh/stored/replayed false×3; real retained cache scrub/replay test PASS.
Source-reviewed normalizer preserves opaque values/order and selected IDs
reach preview/durable payload/domain effects consistently.

Actual old-source upload+schema transition: canonical completed, URN
completed and URN ambiguous **PASS**; uuid-only completed/ambiguous and
urn-only completed **FAIL** with submission/file1→2. Unknown state explicitly
injected by clearing response after completed upload, not claimed OS crash.
Evidence [directory](controller-evidence/20261115T053138Z-pa006-r4/),
[runner](controller-evidence/20261115T053138Z-pa006-r4/run_upgrade_aliases.sh)
and controller report contain commands/exits/environment/assertions.

NOT_RUN: production install/reinstall/upgrade/restore/DR, real service drain,
GNS3/CHR/router actions, live deployment RADIUS auth/accounting, browser E2E,
scale/soak/one-million-client benchmark. Local PG schema transition and
FreeRADIUS binary test do not establish those gates. Full suite has three
pre-existing adapter-thread warnings. External/file effects not claimed
exactly-once; rollback-orphan FUP-002 remains separate.

## 2. Beta blockers and subsequent priority

**Production Beta NOT_READY.** Register:
[11 November review](controller/20261111T074225Z-repo-handoff-review.md) §4.

- Current **PA-006 / REV-1311-01** compatibility correction first; no repeat
  implementation of the newly closed03A/03B/05 or prior02/04/PA001.
- After accepted and required integration: PA-002 + authority PA-003 for
  job lifecycle fencing/drain/current authority, including invoice-lock
  duration and uncertain/cancel/stale-writer cases. Not yet an executable packet.
- DEC-01 native-vs-Compose topology decision before S4 rehearsal; DEC-02
  PR8 docs/manifest ownership; PR7 SSTP disposition remain separate.
- Installer/upgrade/restore/scheduler code blockers REV-1111-04/05/06/07/08/09
  remain; capacity evidence REV-1111-12 unverified.
- Gate A/G Debian13 host+root/domain/DNS, G1 MikroTik CHR/physical and
  licensed reproducible GNS3 lab remain environment prerequisites.

## 3. Open branches and preservation

PR21 is reviewed fourth submission, not accepted/integrated. PR22 is executor
report-only state check; it does not supersede this controller decision.
PR15/16/17/18/19/20 and PR13 preserve task0010 history. PR7 SSTP, PR8 planning
(draft), PR14 DANA planning (draft) and archived branches belong to other
work; do not overwrite/force-push/close/merge them as part of this task.

Current correction must fetch this decision branch; starting from stale
main packet alone loses newer fixes. Original requirements remain intact.
Affected deployments which already ran0004 need an explicit repair/fix-forward
policy or honest sandbox-only assumption; editing applied0004 alone cannot
be represented as a repair of their rows. Keep write-freeze/atomicity/RLS,
principal/platform and business history. No credentials in repository/task.

## 4. Role handoff

Coding agent implements/tests/reports/publishes same-ID correction, then
controller reviews the new exact SHA. Controller verdict and task evidence
must be versioned/verified before dependent work. `_done` and green CI are
not acceptance, integration, deployment or release authorization. Reports and
packet files do not automatically start an external coding agent.

