# LATEST_HANDOFF — 17 November 2026: task0020 koreksi REV-1711-01–09 diserahkan (pending review)

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
| Active task | **[ID0020 PA-002+PA-003](../task/0020-job-lifecycle-authority_done.md)** — **done / pending review / not integrated** |
| Correction branch + PR | `session/2026-11-17-0020-job-lifecycle-correction` (base `0e45157` membawa source PR27); implementation/tested **`2681a3d`**, published head **`062a017`**; candidate **[PR30](https://github.com/smahud/MicroTix_Project/pull/30)** target main; CI exact head **[run44119619011](https://github.com/smahud/MicroTix_Project/actions/runs/44119619011) backend/frontend/docs success 3/3** terverifikasi ([ci evidence](executor-evidence/20261117T150000Z-0020-correction/ci-pr30.txt)) |
| Decision ref | **[PR29](https://github.com/smahud/MicroTix_Project/pull/29)** `review/0020-controller-20261117`; verdict acceptance tetap [controller R1](controller/20261117T134100Z-0020-job-lifecycle-review.md) sampai controller mereview SHA koreksi |
| Correction evidence root | [executor-evidence/20261117T150000Z-0020-correction/](executor-evidence/20261117T150000Z-0020-correction/) — failing-before/passing-after probe, split-role migrate/grant/RLS, check, makemigrations, docs, full-suite 562, targeted subsets, environment |
| Coreksi inti | Guard ownership DALAM transaksi unit domain (scope+assert_owned; heartbeat/progress raise); no_effect eksplisit + default uncertain post-efek; retry lineage root-lock+BFS; hold durable router unknown (+expired-executing); authority di batas efek pasca-preflight; HTTP router scope 404; B6 APPLY/VERIFY di luar transaksi; B6 readback negatif jujur; +bukti SIGINT/active-barrier/stop-claim/long-phase/crash-after-commit/current-policy |
| Independent reviewer | [Koreksi](reviewer/20261117T160500Z-0020-correction-independent.md); [lifecycle](reviewer/20261117T140000Z-0020-lifecycle-independent.md), [authority](reviewer/20261117T140000Z-0020-authority-independent.md) histori R1 |
| Next actor | **controller_reviewer** |
| Exact next action | Review exact SHA koreksi atas REV-1711-01–09 (jalankan ulang probe R1 + matriks [laporan koreksi §5](orchestrator/20261117T160000Z-0020-correction-delivery.md)), delta main/candidate+CI; changes-requested membuka kembali ID0020 yang sama; jangan buka task0030 sebelum prasyarat terpenuhi |
| Accepted predecessor | **Task0010/PA-006 tetap accepted/integrated**, PR24/25 merged; P3 R5 thread assertions preserved; tidak dibuka kembali |
| Other refs | PR26 instruction, PR27 kandidat pertama bd37c14, PR28@8204ba0 report-only, PR29 decision, histori PR task0010 serta PR7/8/14 dipertahankan; tidak ada merge/close/force-push pekerjaan pihak lain |
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

