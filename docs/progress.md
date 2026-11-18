# MicroTix — checkpoint kemajuan

Rekam jejak eksekusi agent per IMPLEMENTATION_PLAN.md §2.5. Terakhir diperbarui: 2026-11-19 (Asia/Jakarta), keputusan controller atas koreksi R5 task 0020.

## Checkpoint 2026-11-19 WIB — keputusan controller R5 task 0020

**Changes requested** pada exact `3301c2940dbfa9293ae52b8d8479b2050c16ebef`, aplikasi setara main
`0616a80` dan kandidat PR #38. CI backend, frontend dan docs lulus.
Pada PostgreSQL 17.11 controller mengulang **28/28 probe beku, 2/2
settlement, 18/18 R5**, dan suite **614 passed / 1 skip**. Empat assertion
tambahan gagal untuk lease yang terlewati saat lock wait pada settlement,
watchdog dan commit enrollment. [Laporan](../report/controller/20261118T172344Z-0020-r5-correction-review.md) ·
[Bukti runtime](../report/controller-evidence/20261118T172344Z-0020-r5-correction/runtime.md).

Task0020 kembali **ready** pada [packet yang sama](../task/0020-job-lifecycle-authority.md).
Coding agent mengambil ref `review/0020-r5-correction-20261118-1723`, mengoreksi empat finding
dan menyerahkan tested SHA baru dengan bukti. Task0030 menunggu acceptance
0020. Production Beta **NOT_READY**.

## Checkpoint 2026-11-18 ~19:1x WIB — integrasi merge koreksi R5 ke main (wewenang pemilik)

Pemilik repo menginstruksikan merge-all branch ke main dengan PAT (preseden
PR24/25/30/31/32/33/34/36). PR #37 (decision records controller R4-correction,
merge `e59a57d`) dan PR #38 (koreksi R5, impl/tested `3301c29`, head penyerahan
`ccea781`) di-merge: merge commit **`e19b08f`**. **Exact-main CI diverifikasi:
[run44300491651](https://github.com/smahud/MicroTix_Project/actions/runs/44300491651)
backend/frontend/docs 3/3 success** pada head `e19b08f`; CI kandidat PR #38
head `ccea781` [run44299725440](https://github.com/smahud/MicroTix_Project/actions/runs/44299725440)
juga 3/3 success. Seluruh remote branch kini ancestor main (0 unmerged, 0 PR
terbuka). Merge pemilik bukan acceptance controller — review koreksi R5 tetap
pending untuk exact SHA `3301c29` (next actor controller_reviewer); task0030
belum eligible; Production Beta **NOT_READY**. [Bukti
CI](../report/executor-evidence/20261118T113641Z-0020-r5-correction/ci-integration.txt).

## Checkpoint 2026-11-18 ~18:5x WIB — executor menyerahkan koreksi R5 task0020 (done/pending review)

Executor menutup empat residual changes_requested controller (REV-1711-01/04/05
+ REV-1811-02) pada ID0020 yang sama di atas decision head `2d5b7f1`
(PR #37; main saat mulai `5c45276`), branch `session/2026-11-18-0020-r5-correction`.

- **REV-1811-02**: settlement no-effect final/nonfinal kini SATU transaksi pendek —
  step-1 wajib lease berlaku (lease basi → row tetap EXECUTING dengan token/epoch
  awal sampai reconciler; regresi controller terminal-lease 2/2 PASS), step-2
  terikat epoch attempt, `on_retry` di luar unit, penyelesaian ganda ditolak.
- **REV-1711-04**: readback applied=True wajib bukti penulis berhenti — readback
  positif saat writer lintas-proses hidup DITOLAK, nol kirim penerus router sama,
  router lain maju, verify-only tanpa resend setelah penulis terbukti berhenti;
  CAS resolve terikat epoch snapshot (`stale_epoch`); identitas writer tidak
  lengkap → karantina fail-closed meski /proc hilang.
- **REV-1711-05**: guard authority terkunci mengunci baris user (user→membership)
  + `is_active` dibaca segar DI BAWAH kunci sampai commit — penonaktifan akun
  selama tunggu lock kredensial/membership → unit batal (Router 0, PENDING,
  belum completed, FAILED authority_denied); serialisasi lock user terbukti.
- **REV-1711-01**: urutan guard batas commit dibalik (final_authority_guard
  sebelum commit_guard TERAKHIR) — lease basi selama tunggu tanpa renewal
  efektif → NOL efek domain; watchdog tidak lagi terhalang lock job; kontrol
  lease valid commit tepat sekali.

Bukti: 28/28 probe beku R1–R4 PASS tanpa pelemahan + regresi controller 2/2 +
18 regresi R5 baru (failing-before BASE `2d5b7f1`: 2+11 FAIL identik temuan) +
suite penuh 614 passed/1 skip/3 warnings + check/makemigrations/docs PASS pada
PostgreSQL 17.12 split-role migrator-owned + mtx_app NOSUPERUSER/NOBYPASSRLS
FORCE RLS. Tanpa migration baru. [Laporan R5](../report/orchestrator/20261118T115321Z-0020-r5-correction.md)
+ [evidence](../report/executor-evidence/20261118T113641Z-0020-r5-correction/).
Next actor **controller_reviewer** pada exact tested SHA; task0030 menunggu
acceptance 0020; Production Beta **NOT_READY**.

## Checkpoint 2026-11-18 WIB — controller mereview koreksi R4 task 0020

**changes_requested** pada exact `77a4a9056c1c5cf9b0b0874b0630a16dd350aa09`, source setara main
`5c45276`. PR #36 sudah terintegrasi. Controller memverifikasi
CI kandidat dan main 3/3, 28/28 probe beku dan suite backend
596 passed/1 skip. Dua assertion expired no-effect FAIL. Source
review menemukan sisa masalah hold router/epoch, akun aktif dan
validitas lease pada batas commit.

Task 0020 kembali **ready** pada [packet yang sama](../task/0020-job-lifecycle-authority.md).
Coding agent melanjutkan empat temuan pada [keputusan controller](../report/controller/20261118T050714Z-0020-r4-correction-review.md)
dari ref `review/0020-r4-correction-20261118-0507`. Task0030 menunggu acceptance 0020.
Production Beta **NOT_READY**.

## Checkpoint 2026-11-18 ~11:1x WIB — integrasi merge koreksi R4 ke main (wewenang pemilik)

Pemilik repo menginstruksikan merge-all branch ke main dengan PAT (preseden
PR24/25/30/31/32/33/34). PR36 di-merge: merge commit **dffb0c7** (membawa
koreksi impl/tested 77a4a90 + head penyerahan 3eaae2a + decision records R4
PR35/e0d306a). **Exact-main CI diverifikasi: run44234563802 backend/frontend/
docs 3/3 success** pada head dffb0c7 (job docs: seluruh step completed/success;
status record "in_progress" = artefak API — run-level conclusion success).
CI kandidat PR36 head3eaae2a run44234124841 juga 3/3 success. Seluruh remote
branch kini ancestor main (0 unmerged); PR35/PR36 ter-merge. Merge pemilik
bukan acceptance controller — review koreksi R4 tetap pending untuk exact
SHA77a4a90 (next controller_reviewer); task0030 belum eligible; Beta NOT_READY.
[Bukti CI](../report/executor-evidence/20261118T035535Z-0020-r4-correction/ci-integration.txt).

## Checkpoint 2026-11-18 ~11:0x WIB — executor: koreksi R4 task0020 diserahkan (done/pending review)

Executor menutup tiga temuan R4 pada ID0020 yang sama di atas decision head
**e0d306a** (main a636166 + records R4 PR35); implementation/tested
**77a4a9056c1c5cf9b0b0874b0630a16dd350aa09**, branch
`session/2026-11-18-0020-r4-correction`.

- **REV-1711-04**: identitas penulis attempt (pid/host/starttime `/proc`)
  dipersist ATOMIK saat entering EXECUTING (migration additive `jobs/0006`
  writer_pid/host/start_ticks/ended_at, nullable) + receipt `writer_ended_at`
  CAS epoch-attempt di finally `run_claimed`; `resolve_uncertain(applied=False)`
  memakai receipt/liveness/`/proc`-starttime — unknown (host lain, stat tak
  terbaca, baris legacy NULL) ditahan fail-closed. Probe R4 cross-process
  2/2 PASS (nol successor send selama proses lama hidup; pemulihan positif
  setelah proses mati tetap lolos — drain SIGKILL suite).
- **REV-1711-05**: `finalize_verification` memvalidasi kewenangan TERKUNCI
  (`check_current_authority(lock_membership=True)`) pada batas commit unit —
  setelah seluruh tulisan sensitif (termasuk tunggu lock kredensial WG/SSTP)
  dan setelah `commit_guard`; revoke yang ter-commit selama tunggu ⇒ rollback
  unit (Router0, kredensial PENDING, FAILED authority_denied). Probe 2/2 PASS.
- **REV-1811-02**: transisi terminal attempt-final no-effect memakai CAS
  koheren dengan lease yang dilepas step-1 (UNCERTAIN+lease-NULL → FAILED);
  guard lease-valid umum R3 tidak diubah. Probe PASS (FAILED tepat sekali).

Probe controller R4 **FROZEN 4/4 PASS tanpa pelemahan** (failing-before
executor 4 gagal identik controller); frozen R1/R2/R3 **24/24 PASS**;
suite penuh **596 passed/1skip/3warnings** (baseline 588 + 8 regresi baru
`test_jobs_r4_residuals`); check/makemigrations/docs PASS; split-role
migrator-owned + `mtx_app` NOSUPERUSER/NOBYPASSRLS FORCE RLS PG17.12.
Harness repair A09: fixture autouse `_restore_latest_migrations` pada 3 file
tes pa006 (0003↔0004/0005 meninggalkan state historis — jinak saat 0005
data-only, merusak setelah 0006 additive; tanpa asersi berubah).
[Laporan](../report/orchestrator/20261118T035535Z-0020-r4-correction.md),
[evidence](../report/executor-evidence/20261118T035535Z-0020-r4-correction/),
[packet _done](https://github.com/smahud/MicroTix_Project/blob/3eaae2add1a4b4e9415bd51fabcf1eb0601444de/task/0020-job-lifecycle-authority_done.md).
Next **controller_reviewer** pada exact SHA77a4a90 (probe R4+24 frozen+regresi;
matriks A01–A09; verdict ID0020). Task0030 ineligible; Beta NOT_READY.
Device/GNS3/live RADIUS/browser E2E/systemd/scale tetap NOT_RUN.

## Checkpoint 2026-11-18 — controller R4 task0020: changes_requested

Reviewed actual main **a636166**, source/config identik impl/tested16db545
PR34 (merged906bfe0). Root **588 passed/1skip/3warnings**, seluruh **24 frozen
R1/R2/R3 PASS**, check/makemigrations/docs PASS; exact-main CI
[44223659118](https://github.com/smahud/MicroTix_Project/actions/runs/44223659118)
backend/frontend/docs success3/3. Satu skip karena binary FreeRADIUS tidak
tersedia; executor589/0skip bukan perbedaan source.

Empat assertion baru PG17.11 split-role **FAIL/0errors**: same-job resolve
lintas-proses setelah sesi DB mati masih send2 saat old adapter hidup;
WG/SSTP credential UPDATE wait outlives committed revoke sehingga
Router1/APPLIED/succeeded; final proven-no-effect attempt tersangkut uncertain.
Same no-effect assertion pada clean4b03efe **PASS/FAILED terminal**, jadi
regresi current. **REV-1711-04/05 PARTIAL P1; REV-1811-02 P2 OPEN.**
Retain REV01 expiry-resurrection, duplicate1811-01,02/03/06/07/08/09 closures
within sandbox/process limits. PA001/PA006/task0010 tetap accepted/integrated.

[Controller R4](../report/controller/20261118T025143Z-0020-r4-review.md),
[evidence](../report/controller-evidence/20261118T025143Z-0020-r4/),
[packet0020 reopened](../task/0020-job-lifecycle-authority.md).
Decision **[PR35](https://github.com/smahud/MicroTix_Project/pull/35)**,
**review/0020-controller-r4-20261118**, initial **bc90619a41d18cae1dd67c440ca6f033b82e32c3**,
treed782fc81; all43 path hashes+4 key content readbacks MATCH dan clean local
fetch. [Receipt](../report/controller-evidence/20261118T025143Z-0020-r4/publication.json).
Metadata descendants preserve reviewed source. Next **coding_agent** tutup3 findings pada ID
sama,4 assertions baru PASS tanpa pelemahan+preserve24/full checks; publish
SHA+CI+report untuk controller. Task0030 ineligible; Beta NOT_READY.
Host/device/GNS3/live RADIUS/browser E2E/systemd/scale NOT_RUN; aplikasi tidak
diubah. Initial supplemental4 connection errors retained separately; final
runs4 assertion failures bukan harness errors. Merge bukan acceptance.

## Checkpoint 2026-11-18 ~09:3x WIB — integrasi merge-all ke main (wewenang pemilik)

Pemilik repo menginstruksikan merge-all branch ke main dengan PAT
(preseden PR24/25/30/31/32). Branch koreksi R3 di-merge: merge commit
**906bfe0** (membawa decision records R3 05d268d + koreksi), kode identik
tested **16db545** (head penyerahan 19cb430 report-only descendant).
**Exact-main CI diverifikasi: run44223255529 backend/frontend/docs 3/3
success** pada head906bfe0. Seluruh remote branch kini ancestor main
(0 unmerged); PR33/PR34 ter-merge otomatis. Merge pemilik bukan acceptance
controller — review koreksi R3 tetap pending untuk exact SHA16db545;
task0030 belum eligible; Beta NOT_READY.

## Checkpoint 2026-11-18 ~09:2x WIB — executor: koreksi R3 task0020 diserahkan (done/pending review)

Di atas decision head `05d268d` (main `4b03efe` + records R3 PR33), executor
menutup REV-1711-01/04/05 + REV-1811-01 pada ID0020 yang sama:
**probe controller R3 FROZEN 7/7 lulus tanpa pelemahan** (failing-before
executor pada wt-base identik temuan controller 3+3 gagal/1 positif),
**frozen R1/R2 17/17 tetap lulus**, suite penuh **589 passed/0 skipped**
(583 baseline + 1 tes radius unskip karena binary FreeRADIUS tersedia di
sandbox + 5 tes baru `test_jobs_r3_residuals.py`), check/makemigrations/docs
PASS. Perubahan: klausa lease-validity seluruh CAS renewal/transisi/terminal
worker; registry in-flight tolakan resolve job sama saat attempt masih
berjalan; authority_guard di bawah kunci baris enrollment; JobError ter-tipe
duplicate finalize. Reviewer independen read-only: 01/05/1811-01 CLOSED;
REV-1711-04 cukup untuk scope probe; residual lintas-proses REV-R3C-01 (P2
laten) + REV-R3C-02 (P3) terdokumentasi dengan analisis konflik terhadap
closure R1 — bukan klaim aman lintas proses.

[Eksekusi](../report/orchestrator/20261118T022200Z-0020-r3-correction.md),
[reviewer independen](../report/reviewer/20261118T022200Z-0020-r3-correction-independent.md),
[evidence](../report/executor-evidence/20261118T000000Z-0020-r3-correction/),
[packet0020 _done](../task/0020-job-lifecycle-authority.md).
Next **controller_reviewer** mereview exact SHA kandidat branch
`session/2026-11-18-0020-r3-correction`. Task0010 accepted/integrated; task0030
belum eligible; Beta NOT_READY. Host/device/GNS3/live RADIUS produksi/browser
E2E/systemd/scale NOT_RUN; merge/push atas instruksi pemilik bukan acceptance.

## Checkpoint 2026-11-18 — controller R3 task0020: changes_requested

Reviewed exact integrated main **4b03efe**, source/config identik implcd6eea3
PR32 head48b83d9 (sudah merged8a26a1f). Root **583 passed/1skip/3warnings**,
semua17 frozen R1/R2 probes PASS, check/makemigrations/docs PASS, exact-main
CI run44166000632 backend/frontend/docs success3/3.

Tetapi7 new PG17.11 split-role assertions memberi **6 FAIL/1 PASS/0 errors**:
expired lease dihidupkan lagi oleh progress atau returning-I/O heartbeat;
same-job resolve-negative setelah DB session mati mengirim kedua saat old
adapter masih hidup; WG/SSTP create Router+apply credential setelah revoke
committed selama enrollment row-lock wait; duplicate finalize undefined
JobError → internal_error/uncertain. **REV01/04/05 PARTIAL P1**, new
**REV-1811-01 P2 OPEN**. Preserve02/03/06/07 CLOSED;08 now CLOSED active
adapter/readback,09 mapping/healthy long-phase CLOSED within stated limits
(root positive crosses initial expiry,25 reconciler attempts).

[Controller R3](../report/controller/20261117T212042Z-0020-r3-review.md),
[evidence](../report/controller-evidence/20261117T212042Z-0020-r3/),
[packet0020 reopened](../task/0020-job-lifecycle-authority.md).
Decision **[PR33](https://github.com/smahud/MicroTix_Project/pull/33)**
review/0020-controller-r3-20261118, initial35e0d61/tree7e6bb3b verified
all49 path checks +4 key file readbacks +clean fetch; publication R3 §8.
Next **coding_agent** menutup residual pada ID sama, all7 new probes PASS
without weakening + preserve17/full regression, publish new SHA+CI+reports.
Task0010 accepted/integrated;0030 belum eligible; Beta NOT_READY. Source
aplikasi tidak diubah; host/device/GNS3/live RADIUS/browser/scale NOT_RUN.

## Checkpoint 2026-11-18 ~02:47 WIB — executor: koreksi R2 task0020 diserahkan (done/pending review)

Di atas main `0c6403de` (PR31 merged atas wewenang pemilik), executor menutup
kelima temuan R2 pada ID0020 yang sama: **probe controller R2 6/6 lulus tanpa
pelemahan** (file probe FROZEN — controller-evidence tidak diubah), **R1 11/11
tetap lulus**, suite penuh **583 passed/1 skipped** (+3 tes baru), check/
makemigrations/docs/frontend PASS.

Perubahan inti: guard commit terkunci (SELECT..FOR UPDATE baris job) pada exit
unit domain (scope/run_discovery/finalize_verification); recheck durable di
bawah kunci sender pasca-acquisition (tahan kematian sesi DB — advisory lock
bukan bukti writer berhenti); authority aktual pasca-I/O (enrollment WG/SSTP,
B5/B6 cutover, pra-I/O cabang rollback); B6 memakai adapter aktif via factory
dengan lab gate jujur no-effect (B2/B5 diseragamkan); watchdog heartbeat
bersyarat memakai HEARTBEAT_S (gap "dideklarasikan tak dipakai" ditutup; tidak
pernah menghidupkan lease kedaluwarsa); kunci baris enrollment pada unit efek
(anti finalize konkuren); factory resolve dinamis kelas simulator.

Reviewer independen: 5/5 temuan R2 CLOSED + 5 temuan baru REV-R2C-01..05
(kelas authority post-I/O cutover P2 + 4 P3) — semuanya ditutup sesi sama.
Impl/tested `cd6eea3`; candidate PR32; [laporan](../report/orchestrator/20261117T194548Z-0020-r2-correction.md),
[evidence](../report/executor-evidence/20261117T191917Z-0020-r2-correction/).
Next: controller_reviewer (R3) pada exact SHA PR32. Production Beta tetap
NOT_READY; NOT_RUN: perangkat nyata/GNS3/RADIUS daemon/E2E/systemd/scale.


## Checkpoint 2026-11-18 — controller R2 task0020: changes_requested

Current main **64b68f8** diverifikasi (32 branches,0 open PR); koreksi PR30
actual head19023737 sudah merged9eb5dacf, termasuk merge-all/SSTP berikutnya.
Controller menjalankan ulang pada **exact integrated64b68f8**: **580 passed,
1 skipped,3 warnings**, original **11 R1 probes PASS**, check/makemigrations/
docs PASS; exact-main CI run44125923116 success backend/frontend/docs.

Tetapi **6 new assertion FAIL/0 harness errors** di PG17.11 split-role:
actual discovery guard→reconcile→commit tetap object1/snapshot succeeded;
hold-check→sender-acquire race menghasilkan send2; hilangnya DB session
melepas advisory lock sementara old adapter masih hidup dan successor send2;
revoke selama TLS enrollment tetap membuat Router1/credential applied pada
WG dan SSTP; B6 selected api_ssl dibypass simulator→false rolled_back/local.
**REV-1711-01/04/05/08 masih PARTIAL P1**, **02/03/06/07 CLOSED**,09 evidence
fase panjang dipetakan terbatas. SIGTERM/SIGINT/stop-claim progress dan
SUB-05 tests dipertahankan; bukan production/device/domain-kill evidence.

[Laporan R2](../report/controller/20261117T170000Z-0020-r2-review.md),
[evidence](../report/controller-evidence/20261117T170000Z-0020-r2/),
[packet0020 reopened](../task/0020-job-lifecycle-authority.md).
Decision **[PR31](https://github.com/smahud/MicroTix_Project/pull/31)**
`review/0020-controller-r2-20261117`, initial443b1dc/tree d86c1216 verified
all40 path/blob checks + clean fetch; publication/readback report §8.
Metadata descendants tidak mengubah reviewed source64b68f8. Next **coding_agent** menutup residual pada **ID sama**,
mempertahankan perbaikan yang lulus, lalu publish SHA baru untuk review.
Source aplikasi tidak diubah reviewer. Task0010 tetap accepted/integrated;
task0030 belum eligible; Production Beta **NOT_READY**.

## Checkpoint 2026-11-17, ~23:59 WIB — executor menyerahkan koreksi task0020 (done, pending review)

Coding agent menutup **REV-1711-01–09 pada ID0020 yang sama** dari decision
ref **[PR29](https://github.com/smahud/MicroTix_Project/pull/29)** (fetched
sampai `0e45157`; base membawa source PR27). Perubahan minimum stack
existing: guard ownership DI DALAM transaksi unit domain (`scope()`+`
assert_owned()`, heartbeat/progress melempar OwnershipLost; guard diteruskan
ke `run_discovery`/`finalize_verification`), `JobError.no_effect` eksplisit
+ default uncertain pasca-efek (komposisi transisi executing→uncertain→
retry_wait sah tabel §6), retry lineage root-lock+BFS seluruh descendant,
hold durable router outcome-unknown (+executing/verifying lease expired),
authority di batas efek setelah preflight, HTTP job menghormati
membership.router_scope (404 non-scope), B6 APPLY/VERIFY di luar transaksi
+ readback negatif jujur (run FAILED, tanpa klaim LOCAL/ROLLED_BACK), serta
+8 tes bukti REV-1711-09 (SIGTERM/SIGINT idle/active-barrier/stop-claim,
fase panjang vs reconciler serentak, crash setelah commit domain,
current-policy/SUB-05 restricted/ended). Tanpa migrasi schema.

Bukti: **probe controller R1 failing-before 11 failed → passing-after
11 passed** (diulang pada DB split-role migrator-owned + runtime
NOSUPERUSER/NOBYPASSRLS/FORCE RLS); **suite penuh 562 passed/1skip**;
PA-001 33, PA-006 125, RLS 8 lulus; check/makemigrations/docs PASS.
[Reviewer independen](../report/reviewer/20261117T160500Z-0020-correction-independent.md):
REV-1711-01–09 CLOSED, nol pelemahan assertion; temuan P2 reviewer
(CORR-REV-01 no_effect blanket backup, CORR-REV-02 jendela hard-crash
pra-reconcile) **ditutup sebelum commit**. Execution **done / review
pending** pada [packet0020_done](../task/0020-job-lifecycle-authority.md);
[laporan koreksi + matriks A01–A09](../report/orchestrator/20261117T160000Z-0020-correction-delivery.md)
+ [evidence](../report/executor-evidence/20261117T150000Z-0020-correction/).
Candidate **[PR30](https://github.com/smahud/MicroTix_Project/pull/30)** published head `062a017` (impl/tested `2681a3d`), CI exact head **[run44119619011](https://github.com/smahud/MicroTix_Project/actions/runs/44119619011) backend/frontend/docs success 3/3** terverifikasi. Next **controller_reviewer** mereview exact SHA koreksi; task0010 tetap
accepted/integrated; task0030 belum eligible. Beta **NOT_READY**;
host/perangkat/GNS3/live RADIUS/browser/benchmark tetap NOT_RUN.

## Checkpoint 2026-11-17, ~21:48 WIB — controller resume task0020

GitHub/fresh clone **31 branches/14 open PRs**: main41d1f33, PR27bd37c14,
starting PR29decision43043be unchanged; **belum ada penyerahan koreksi**.
Task0020 tetap **ready / changes_requested**, correction delivery
**not_submitted**, next **coding_agent** fetch PR29 decision ref dan tutup
REV-1711-01–09 pada ID sama. Ancestry7118cce→bd37c14→43043be sah; seluruh
delta hanya task/report/progress. Existing CI43043be sekarang success3/3
(menggantikan observasi in-progress), bukan closure finding/CI checkpoint.

[Controller checkpoint](../report/controller/20261117T144620Z-0020-resume-review.md),
[independent review](../report/reviewer/20261117T144620Z-0020-resume-independent.md)
dan [checks](../report/controller-evidence/20261117T144620Z-0020-resume/local-checks.json)
pada existing PR29; docs validator PASS24/106 dan diff hygiene PASS. Bukti
R1 554passed/1skip +11 acceptance failures tetap historis; runtime tidak
diulang pada source unchanged. Task0010 accepted/integrated, task0030
belum eligible, Beta NOT_READY. Publication/readback checkpoint §6 dan
final-head CI di PR29; tanpa aplikasi patch/merge/deploy/tag/activation.

## Checkpoint 2026-11-17 — controller R1 task0020 changes_requested

Review exact **PR27@bd37c14e6c41339a8743b3d4b723ee74f13bef08** dari
main41d1f33/instruction PR26ea7b8a1; ancestor7118cce→candidate app/source
diff kosong. [Controller R1](../report/controller/20261117T134100Z-0020-job-lifecycle-review.md)
+ dua reviewer independen, root full suite **554 passed/1skip/3warnings**,
check/makemigrations/docs PASS, exact candidate CI43994355914 success3/3.
**11 focused acceptance assertions gagal tanpa harness error** pada fresh
PG17.11 migrator-owned schema+runtime nonowner/NOBYPASSRLS/FORCE RLS:
stale discovery commit, backup resend, uncertain retry lineage/router hold,
revoke/demote setelah preflight, HTTP router-scope bypass, B6 I/O transaction
serta false-success negative verifier. Delapan defect **REV-1711-01–08**,
gap mandatory evidence **09** dicatat terpisah; [evidence summary](../report/controller-evidence/20261117T134100Z-0020-review/review-results.json).

**[Packet0020](../task/0020-job-lifecycle-authority.md) reopened ready /
changes_requested**, next **coding_agent** fetch `review/0020-controller-20261117`
dan tutup finding pada ID sama, submit exact SHA baru+tes/evidence/CI.
Decision dipublikasikan pada **[PR29](https://github.com/smahud/MicroTix_Project/pull/29)**,
initial commit **3c4b71f/tree9b7d2405**, ref/commit/tree+39path readback MATCH
dan clean local fetch; metadata descendant hanya mencatat publikasi ini.
Final head/CI mengikuti PR29 dan controller report §8. PA-006/task0010 tetap accepted/integrated dan P3 R5
assertions preserved. Tidak ada task0030, app patch, main merge, deployment,
aktivasi atau tag. Beta **NOT_READY**; host/perangkat/GNS3/live RADIUS/
browser/benchmark tidak diklaim terverifikasi. Checkpoint di bawah histori.

## Checkpoint 2026-11-17, ~08:10 WIB — executor menyerahkan task0020 PA-002+PA-003 (done, pending review)

Executor Z.ai sandbox menjalankan [packet0020](../task/0020-job-lifecycle-authority.md)
dari instruction ref PR26 `review/0020-job-lifecycle-authority-20261117` @ ea7b8a1,
base main **41d1f33** (delta kosong). Implementation/tested **6e96ce33** pada branch
`session/2026-11-17-0020-job-lifecycle-authority` (penyerahan report-only di atasnya;
tree kode identik). Engine jobs direworks: CAS lease token+epoch+expected-state pada
seluruh tulisan worker (hasil terminal ikut CAS di WHERE), unit transaksi tenant pendek
per handler tanpa lock melintasi I/O adapter, effect_state=maybe atomik pra-execute +
cancel hanya pra-efek (executing 409 jujur), satu pemilik pengirim per router via
advisory lock, reconcile state/effect-aware CAS + idempotent, resolve readback protocol
(fence penulis lama; verify tanpa resend; unknown tertahan), retry diserialisasi
(uncertain/recovery_required dianggap aktif), deadline claim+pra-efek, progress
memperpanjang lease, kewenangan terkini fresh-DB (peta kind fail-closed; provenance
verify_api_ssl dari enrollment.created_by; karantina actorless dengan resume; recheck
antar fase kirim cutover), HTTP job detail/retry/cancel pakai izin operasi dasar +
step-up sensitif, RouterReplaceView → routers.release, handler hilang/verifier negatif
fail-closed, runworker drain SIGTERM/SIGINT + drain-timeout + exit 0/3. Tanpa migrasi
schema (jobs/0004/0005 tak tersentuh).

Bukti: **suite penuh 554 passed + 1 skip** PG 17.11 nyata non-superuser FORCE RLS;
**failing-before pada baseline 41d1f33: 33/37 lifecycle + 4/4 drain GAGAL**,
passing-after 41/41; PA-001 + PA-006 (R4/R5 replay migrasi) lulus; check/makemigrations/
docs PASS; frontend tsc/eslint/vitest 66/i18n/build lulus; P3 REV-1611-TEST-01 ditutup
test-only. [Review independen](../report/reviewer/20261117T010218Z-0020-job-lifecycle-independent.md)
pra-koreksi CHANGES_REQUESTED (REV-2011-01 P1 .. 10) — seluruh temuan ditindaklanjuti
dengan tes; [laporan eksekusi + matriks A01–A09 + runbook](../report/orchestrator/20261117T010218Z-0020-job-lifecycle-authority.md),
[evidence](../report/executor-evidence/20261117T000000Z-0020-job-lifecycle/).
Task0020 **done / pending**; next **controller_reviewer** review exact SHA 6e96ce3.
PA-006 tetap accepted/integrated; Beta tetap **NOT_READY** (installer/upgrade/restore/
scheduler/DEC-01/02/host-lab/kapasitas). Simulator/CI bukan bukti perangkat nyata.

## Checkpoint 2026-11-17 — PA-006 integrated terverifikasi, task0020 ready untuk coding agent

Controller menjalankan default reviewer dari GitHub pada main **41d1f33**:
PR24/25 merged; decision headc352bce→main delta17record paths tanpa aplikasi/config/test.
PA-006 tetap **done / accepted / integrated**, tanpa submission keenam.
Exact main CI43857508367 success3/3; decoded log backend **513 passed,1 skipped,3 warnings**
(FreeRADIUS binary unavailable), frontend66, docs PASS24/106.
Ini bukti CI existing; root runtime lokal unavailable, tidak mengklaim rerun514.

[Task0020 PA-002+PA-003](../task/0020-job-lifecycle-authority.md) disiapkan
**ready / not_submitted** pada instruction ref
`review/0020-job-lifecycle-authority-20261117`: lifecycle fencing seluruh write,
short RLS DB/I/O boundary, cancel/uncertain/readback/per-router writer,
early crash recovery/deadline, current authority/HTTP permission/verifier,
real-process drain dan legacy compatibility. PA-001/PA-006 preserved;
P3 REV-1611-TEST-01 hanya test hardening. Tidak mengadopsi PR8 draft
atau memperluas fitur R2/R3/R4. [Controller report](../report/controller/20261116T231131Z-0020-job-lifecycle-review.md)
menautkan dua reviewer independen, packet QA dan remote evidence.
Publikasi **[PR26](https://github.com/smahud/MicroTix_Project/pull/26)** initial ancestor
**e11d48b4fdc0c1757c52af7d9e528437b5afa0bc**, tree653db3cf, ref/commit/PR dan10file content+blob readback MATCH;
metadata descendant hanya mencatat publikasi ini. Initial CI43978170214 docs PASS,
backend/frontend masih berjalan pada readback pertama; final-head CI dicatat di PR26 setelah teramati.
Belum ada hasil implementasi0020.
Next **coding_agent** fetch instruction ref dan eksekusi packet, lalu submit SHA baru.
Production Beta **NOT_READY**; tidak ada merge/deploy/aktivasi/tag. Checkpoint berikut histori.

## Checkpoint 2026-11-16, ~18:25 WIB — integrasi task0010/PA-006 selesai: PR24+PR25 merged ke main

**Task0010 done / accepted / integrated.** Integrator executor (Z.ai sandbox,
[wewenang eksplisit pemilik repo atas PAT "commit, merge, atau push" — preseden
PR9; approval = R5 accepted pada exact a301a94]) menyelesaikan integrasi
sesuai CONTRACT §11: main `9903d9b` → merge **PR24** `532862b` (tree
`bec63b5` = tree reviewed a301a94 persis) → merge **PR25** (keputusan R5)
`fd0f3fa` (tree `f283fe9` = tree head keputusan c352bce persis). Pra-merge:
locked head terverifikasi, delta main nol, CI 3/3 pada kedua exact head,
PR7/8/14 tak tersentuh. Regresi gabungan pada tree final di sandbox dari
nol: **514 passed** (PG 17.11 nyata non-superuser, FreeRADIUS 3.2.7 real
binary), check 0 issue, makemigrations no-change, docs PASS 24/106,
bootstrap migrasi bersih termasuk jobs.0004/0005. Remote readback SHA/tree/
PR-state diverifikasi pasca-merge. Laporan:
[integrasi](../report/orchestrator/20261116T111835Z-0010-pa006-integration.md)
+ [evidence](../report/executor-evidence/20261116T111835Z-0010-pa006-integration/).
Merge ≠ deploy; Beta **NOT_READY** (bloker register tidak berubah);
REV-1611-TEST-01 P3 tetap nonblocking follow-up. Next **controller_reviewer**
menyiapkan packet PA-002 + authority PA-003 dari main terintegrasi.
Checkpoint di bawah adalah histori.

## Checkpoint 2026-11-16, 17:25 WIB — controller menerima PA-006 PR24

**Task0010 done / accepted** pada exact **a301a94c2b3268679065e85bbef66f35949483f7**
(PR24; implementation7338a72). **REV-1311-01 CLOSED**, seluruh closure R4
02/03A/03B/04/05/PA001 preserved. Root: **514 passed** backend +**13 passed**
controller conformance, PostgreSQL17.11 non-superuser; old-source HTTP→
real0004/0005→canonical retry **10/10 PASS** dengan20 completed concurrent
responses dan satu efek/file/guard; role migrator/runtime terpisah dan
FORCE RLS diperiksa. Check/migration/docs PASS; candidate exact-head
CI43846763713 **success3/3**. Dua reviewer independen tidak menemukan
blocker baru. P3 test-completion note nonblocking, evidence gap ditutup
probe root dengan assertion kedua thread/hasil. Laporan [controller R5](../report/controller/20261116T101809Z-0010-pa006-r5-review.md).

Decision **[PR25](https://github.com/smahud/MicroTix_Project/pull/25)**, branch
**review/0010-pa006-controller-r5-20261116** record-only; initial commit
**6201ae959a2d84556c9a54ec2d552d996e8063c9**/tree31731ba5 verified via
remote ref/commit/PR,7file byte readback dan clean local fetch. Metadata
descendant source identik; final-head publication CI tercatat di PR25. Main **9903d9b** dan PR24 belum berubah;
**integration pending**. Next **controller_reviewer** menyelesaikan integrasi
PR24 + keputusan sesuai CONTRACT §11; baru setelah prasyarat integrasi
terpenuhi menyiapkan packet PA-002 bersama authority PA-003. Tidak ada
packet0020, merge/deploy/tag pada sesi review ini. Beta **NOT_READY**;
OS install/upgrade/recovery, real drain/CHR/GNS3/pilot/load tetap NOT_RUN.
Checkpoint di bawah adalah histori, bukan verdict terbaru.

## Checkpoint 2026-11-16, ~17:10 WIB — executor penyerahan kelima ID0010: REV-1311-01 grammar-driven

Executor (Z.ai sandbox) menutup sisa finding controller R4 (PR21
`634da42`, PR23) pada ID0010 yang sama. Branch
`session/2026-11-16-pa006-rev1311-01-correction` dari head keputusan R4
`4bb7261`; **implementation `7338a720b5d64a4ccb47b9abe7d3dc6feca0a476`**
(delivery docs report-only di atasnya). Perubahan source SATU file:
parser migrasi `jobs/0004` grammar-driven — semua posisi kolon,
validitas tenant/resource menurut stdlib uuid.UUID yang sama dengan
writer baseline (literal `platform` exact-case), interpretasi sah unik
(bukti di docstring + brute-force reviewer), ambiguity → fail-stop
`AmbiguousLegacyScope` rollback atomik, 0 interpretasi → baris mati
seperti kebijakan lama; kebijakan affected-state eksplisit (0004 belum
dirilis; fix-forward snapshot pra-0004 / rekonsiliasi manual untuk
environment yang telanjur menjalankan versi cacat).

Bukti: **live upgrade 7/7 PASS** (old main@9903d9b HTTP nyata → migrasi
0004/0005 → retry kanonik; 3 varian FAIL controller direproduksi GAGAL
dulu pada parser cacat — submission/file 1→2); **62 tes r5** baru
(failing-before 21 GAGAL pada parser PR21); **full suite 514 passed**
(PostgreSQL 17.11 nyata, peran non-superuser, FreeRADIUS real-binary);
family PA006 139 passed; `manage.py check` 0 issue;
`makemigrations --check` bersih; docs PASS. Review internal independen
**APPROVE_WITH_NOTES**: brute-force 33.674 pasangan ejaan valid writer
→ 0 tombstone/salah-split/ambiguitas; fuzz 400.000 string adversarial →
0 fail-stop palsu; tidak ada counterexample; REV-R5-01/03 ditutup,
REV-R5-02 (pre-existing P3, opaque >64 char DataError fail-stop aman)
dicatat sebagai kandidat runbook ops.

Laporan: [executor](../report/orchestrator/20261116T100420Z-0010-pa006-idempotency.md),
[independent review](../report/reviewer/20261116T100420Z-0010-pa006-r5-independent.md),
[evidence](../report/executor-evidence/20261116T090000Z-0010-pa006-r5/);
packet `0010-pa006-idempotency_done.md` (execution done, review
**pending**, next **controller_reviewer**). NOT_RUN: produksi/host/lab/
E2E/benchmark. PA-002/003 belum eligible; Beta **NOT_READY**.

## Checkpoint 2026-11-16, 13:50 WIB — koreksi ID0010 belum diserahkan

[Controller checkpoint](../report/controller/20261116T065005Z-0010-pa006-state-review.md):
25 branch /13 open PR; main9903d9b,candidate634da42,starting decision82b2216
sama dengan checkpoint terakhir. Tidak ada koreksi baru; delivery
**not_submitted**, task0010 **ready / changes_requested**, next
**coding_agent** memperbaiki REV-1311-01 saja. Semua closure R4 dipertahankan.
Source/config identik; runtime tidak diulang. Existing exact-head
CI43679221142/43715610125 success3/3. Independent review dan record QA
menopang checkpoint; publikasi/final-head CI mengikuti report dan existing
PR23. PA-002/003 belum eligible, tanpa task/PR baru; Beta **NOT_READY**.

## Checkpoint 2026-11-15, sesi19:39 WIB — tetap menunggu koreksi ID0010

[Controller checkpoint](../report/controller/20261115T123944Z-0010-pa006-state-review.md)
dan independent state review memeriksa25 branch /13 open PR: tidak ada
kandidat koreksi baru; main9903d9b,candidate634da42 tetap, starting
decision80dfc89. Delivery **not_submitted**, task0010 **ready /
changes_requested**, next **coding_agent**, hanya REV-1311-01 OPEN;
seluruh closure R4 dipertahankan. Source/config kosong; docs PASS24files/
106links; runtime tidak diulang. Existing exact-head CI43679221142 dan
43703894306 success3/3; observasi CI80dfc89 memperbarui NOT_RUN lama,
bukan CI checkpoint baru atau acceptance. Checkpoint existing PR23,
tanpa dependent task baru; PA-002/003 belum eligible, Beta **NOT_READY**.
Publikasi dan CI final head diverifikasi terpisah pada report/PR23.

## Checkpoint 2026-11-15, 17:13 WIB — koreksi REV-1311-01 belum diserahkan

[Controller state check](../report/controller/20261115T101333Z-0010-pa006-state-review.md)
dan independent review:25 branch /13 open PR; main9903d9b,
PR21@634da42 dan starting decision PR23@1bc84a44 terkonfirmasi. Tidak ada
kandidat koreksi baru; delivery **not_submitted**, task0010 tetap **ready /
changes_requested**, next **coding_agent**. Hanya REV-1311-01 tetap OPEN;
closure R4 dipertahankan. Source/config diff kosong, docs PASS24files/
106links; runtime tidak diulang. Checkpoint pada existing PR23, tanpa
task dependent baru. PA-002/003 ineligible; Beta **NOT_READY**.
Publikasi/CI head checkpoint dicatat pada report dan PR23.

## Checkpoint 2026-11-15, mulai13:56 WIB — belum ada koreksi setelah PR23

[Resume report](../report/controller/20261115T065656Z-0010-pa006-resume-review.md)
dan independent state check:25 branch/13 PR terbuka; main9903d9b,
PR21@634da42 dan starting decision PR23@30ce815 tidak berubah. Correction
delivery **not_submitted**, task0010 tetap **ready / changes_requested**,
next **coding_agent** menutup REV-1311-01 pada ID sama.03A/03B/05/02/04
dan PA-001 tetap closed/preserved sesuai R4, tanpa runtime re-review baru.
Source/config diff kosong; pure parser probe20 kasus/8 known mismatches;
docs PASS24files/106links, existing exact-head CI3/3 success dikonfirmasi.
Checkpoint pada existing PR23; tidak ada packet/PR baru, PA-002/003 masih
ineligible, Beta **NOT_READY**. Lihat report untuk publication verification.

Checkpoint published ancestor **d7be2ba8667149ed47ec4b11b5da10d5811e7a4a**
pada existing PR23: matching tree/ref dan10file readback verified; source
tetap634da42. CI head baru belum terbit saat pencatatan; final observation
di PR23, tanpa menganggap success head lama sebagai CI checkpoint baru.

## Checkpoint 2026-11-15 — controller PR21 changes_requested; hanya REV-1311-01 tersisa

Exact reviewed **634da4224f15dd6a5a4e9010fe1811dec8c7954d**, implementation
ancestor b71574d, main9903d9b tetap. [Controller R4](../report/controller/20261115T053138Z-0010-pa006-r4-review.md)
dan dua independent source reports mereview penyerahan keempat. **OPEN01
P1 partial**: actual old HTTP `uuid:<UUID>` completed/ambiguous dan
`urn:<UUID>` completed→0004/0005→canonical retry menghasilkan submission
**dan physical file1→2**; `__unparsed__` retained row tidak ditemukan replay.
Standard canonical/URN controls PASS. **CLOSED03A/03B/05**,02/04 tetap
CLOSED, PA-00110 lulus. Root **93 targeted +452 full +6 prior +2 edges
+5 effects PASS** (PG17.11 non-superuser/non-BYPASSRLS), Django/migration/
docs PASS; exact-head CI43679221142 backend/frontend/docs success.

Task [0010](../task/0010-pa006-idempotency_done.md) dibuka kembali **ready /
changes_requested**; next **coding_agent** memperbaiki accepted legacy UUID
grammar/reconciliation pada ID sama, preserve seluruh closure, lalu resubmit
source/evidence/SHA baru. Decision branch
`review/0010-pa006-controller-r4-20261115` menarget PR21 branch; publikasi
terverifikasi dicatat pada controller report/handoff. PA-002/003 belum
eligible, tidak ada packet0020. Host/lab/DR/browser/scale NOT_RUN; Beta
**NOT_READY**. Tidak ada perubahan aplikasi, merge, deployment atau tag.

Publikasi keputusan terverifikasi pada [PR23](https://github.com/smahud/MicroTix_Project/pull/23):
initial ancestor **5c31ed63b5e88e2e6c92565c47e60d947dd81666**, remote tree0031a9ed
sama dengan index lokal; report/packet/handoff/progress remote byte-identical.
Metadata descendant mencatat fakta publikasi, source634da42 tetap sama;
required CI publication diverifikasi melalui PR setelah commit terakhir.

## Checkpoint 2026-11-15 — executor task0010/PA-006 penyerahan keempat: REV-1311-01/03 + REV-1511-05 ditutup

Koreksi atas keputusan [PR20 changes_requested](https://github.com/smahud/MicroTix_Project/pull/20) pada ID0010 yang sama; branch kandidat `session/2026-11-15-pa006-idempotency-correction` (base decision head `e507175`), **implementation `b71574d`**; packet direname `_done` (execution done / review pending) — menunggu controller review exact SHA. **Bukan acceptance.**

**Perubahan inti**: (1) REV-1311-01 — parser scope legacy migrasi 0004 ditulis ulang toleran URN/braced-URN pada tenant maupun resource (kwargs URL mentah main; scope `urn:uuid:` valid tidak lagi dihapus "malformed"); scope tak-terurai DIPERTAHANKAN sebagai baris mati `__unparsed__` (fail-safe). (2) REV-1311-03A — normalisasi hash v2 bertingkat `allocations[].invoice_id` (alias satu invoice logis mereplay); REV-1311-03B — selected_account_ids dikanonikalisasi di view (preview/payload job durable, 422 malformed) + konsumsi domain melindungi payload job lama. (3) REV-1511-05 — preview CSV bebas plaintext credential (mask); migrasi **0005** scrub record retained tanpa menghapus penjaga; mock frontend paritas.

**Bukti (PG 17.11 nyata, role non-superuser, FreeRADIUS aktif)**: **probe controller PR20 dijalankan ulang UTUH** dari worktree baseline main9903d9b — 15/15 langkah live upgrade exit 0: URN completed **201 replay submission semula (submission/file 1)**, URN ambiguous **409 aman (submission/file 1)** (dua kasus yang dulu FAIL); review-edges 2 passed (nested alias replay; plaintext false×3); review-effects 5 passed (selected canonical payload; 4 wait-graph query/blocker). Suite penuh **452 passed**, targeted 93, `manage.py check` 0, `makemigrations --check` bersih, docs PASS, frontend typecheck/lint/Vitest 66/i18n/contrast/live-build sukses. Review internal independen [PASS_WITH_NOTES](../report/reviewer/20261115T044616Z-0010-pa006-r4-review.md); temuan F-01 P2 (braced-URN) + F-02/F-03 P3 ditutup pada kandidat. Laporan: [executor keempat](../report/orchestrator/20261115T044621Z-0010-pa006-idempotency.md). Next actor **controller_reviewer**. Beta tetap NOT_READY; PA-002/003 menunggu accepted.

Publikasi terverifikasi: [PR21](https://github.com/smahud/MicroTix_Project/pull/21) base main, head `0372dc4c0a6f3c238e69276bf0f02579ae646d44` (implementation `b71574d` + delivery `0372dc4`); required CI run [43678518336](https://github.com/smahud/MicroTix_Project/actions/runs/43678518336) exact-head backend/frontend/docs **success**. CI hijau bukan acceptance.

## Checkpoint 2026-11-15, 07:58 WIB — koreksi task0010 belum diserahkan

[Controller submission check](../report/controller/20261115T005847Z-0010-pa006-resubmission-review.md)
memeriksa 22 branch /10 PR terbuka: main9903d9b, PR19@9e9bf2d dan
starting decision PR20@2f2416b tidak berubah. Protected source/config delta
kosong; belum ditemukan corrected candidate baru. **Correction delivery
not_submitted**, task0010 tetap **ready / changes_requested**, next actor
**coding_agent** menutup REV-1311-01/03 dan REV-1511-05 dari instruction ref
PR20 existing. REV-1311-02 dan REV-1411-04 tetap CLOSED pada reviewed SHA.
Docs validator PASS24files/106links; candidate/starting-decision exact-head
CI diverifikasi success, tanpa mengklaim runtime tests baru. Independent
check ditautkan pada laporan. Checkpoint dipublikasikan pada branch PR20
yang sama; PA-002/003 tetap belum eligible, tidak ada task/PR baru,
merge/deploy/tag. Beta **NOT_READY**.

Publikasi checkpoint terverifikasi pada existing PR20, initial commit
**25f96a6f7a56f427e26ee3f77e67727fef5d5c7b**, remote tree27500dba cocok
dengan index lokal dan checkout bersih. Exact-head CI43661329292 completed
success. Metadata descendant hanya mencatat publikasi; source tetap identik,
keputusan aplikasi dan next actor tidak berubah.

## Checkpoint 2026-11-15 — controller PR19 changes_requested; task0010 reopened

Exact reviewed candidate **9e9bf2d42002a00a69d54fc355b77384897b9478**, source
ancestor c99838cd6e9f144adf53bb44ed792fba15a432fe; main9903d9b tetap.
Keputusan di [PR20](https://github.com/smahud/MicroTix_Project/pull/20), branch
`review/0010-pa006-controller-20261115` (belum integrated), first verified
decision ancestor **2c2797b37ba536100fdf67c8dd08ceab793c5ff9**,
[laporan controller](../report/controller/20261114T212816Z-0010-pa006-review.md)
beserta dua independent source reviews dan raw scripts/log. Publikasi/PR
terverifikasi melalui remote fetch/tree readback; metadata descendant hanya
memperbarui pointer. Required publication CI/final readback mengikuti PR;
tidak mengganti review acceptance yang gagal.

**OPEN:** REV-1311-01 P1 — actual main HTTP memakai URN tenant→0004→retry
menduplikasi submission+physical file1→2 (completed dan ambiguous key);
REV-1311-03 P2 — nested allocation UUID alias200/409/200 dan hash-selected
UUID alias202 menghasilkan preview0 vs canonical1 + raw job payload;
REV-1511-05 P1 — pre-existing CSV validation plaintext password masuk
persisted/replayed response (sentinel di memori; log boolean saja).
**CLOSED pada SHA ini:** REV-1311-02 parent+group, REV-1411-04 authenticated
HTTP/after-write rollback+takeover; controller supplement mengassert query
serta blocker pada empat forced wait graphs. Klaim all-PASS executor di
bawah adalah histori, bukan acceptance.

Root PostgreSQL17.11 NOSUPERUSER/NOBYPASSRLS: **67 targeted,426 full,6 prior
probes PASS**, PA-00110 lulus; Django/migration/docs PASS; CI43618187731
exact9e9bf2d backend/frontend/docs success. Tiga new HTTP conformance cases
dan dua URN actual-source upgrade cases FAIL; canonical actual-source
upload/retry PASS. Setup-process-lifetime dan truncated query1024 harness
issues diakui terpisah; affected attribution tests rerun capture8192 PASS.

Packet [0010](../task/0010-pa006-idempotency_done.md) kembali **ready /
changes_requested**, ID tetap, original acceptance utuh. Next actor
**coding_agent**, tutup01/03/05 minimum lalu resubmit exact SHA + evidence.
PA-002/003 belum eligible; tidak ada dependent task baru, merge/deploy/tag;
Beta **NOT_READY**. Host/lab/DR/capacity NOT_RUN.

## Checkpoint 2026-11-15 — riwayat klaim executor task0010/PA-006 penyerahan ketiga (belum diterima)

Koreksi atas keputusan [PR18 changes_requested](https://github.com/smahud/MicroTix_Project/pull/18) pada ID0010 yang sama; branch kandidat `session/2026-11-15-pa006-idempotency` (base keputusan `b6a0cb8`), **implementation `1780e15` + hardening `c99838c`**; packet direname `_done` (execution done / review pending) — menunggu controller review exact SHA. **Bukan acceptance.**

**Perubahan inti**: (1) REV-1311-01 — migrasi `jobs/0004` menahan record tanpa respons (penjaga efek ambigu), remap operasi platform legacy ke `tenant_scope='platform'`, dedupe alias memilih record berrespons; runtime `legacy_shapes`+`replay_guard` merekonsiliasi `payment_submission` `resource=''` dengan verifikasi submission→tenant(RLS)→invoice sebelum replay; transisi migrasi NYATA 0003→0004 dibuktikan (retry pasca-upgrade mereplay submission semula, beda body 409, no-response 409 aman). (2) REV-1311-02 — `identity_conflict_resolve` identitas `<migration UUID>:<group_id>`; parent divalidasi SEBELUM klaim/replay (422/404); session A/B → keputusan [2,2]; legacy group-only 409 aman. (3) REV-1311-03 — hash v2 field UUID body dideklarasikan (`package_id`/`router_id`/`selected_account_ids`) + kompatibilitas v1 raw konstan-waktu. (4) REV-1411-04 — tes konkurensi HTTP klien terautentikasi per-thread via dispatch penuh; observasi lock `pg_stat_activity` DIASSERTI; takeover test injeksi kegagalan setelah writes domain/audit/outbox dengan penantang same-key menunggu → rollback menyeluruh + takeover + satu aksi terkomit.

**Bukti (PG 17.11 nyata, role non-superuser, FreeRADIUS aktif)**: suite penuh **426 passed** (3 warning pra-ada), targeted controller set 65 passed, **6/6 probe acceptance controller PASS** (evidence 14 Nov dijalankan ulang), `manage.py check` 0 issue, `makemigrations --check` bersih, docs PASS. Review internal sub-agent read-only: PASS_WITH_NOTES — temuan P3 ditutup pada `c99838c` (validasi group_id, assert join, counter dedupe, 2 tes celah bukti) atau didokumentasikan sebagai batas. Laporan: [executor](../report/orchestrator/20261114T164816Z-0010-pa006-idempotency.md) + [reviewer](../report/reviewer/20261114T164816Z-0010-pa006-review.md). Next actor **controller_reviewer**. Beta tetap NOT_READY; PA-002/003 menunggu accepted.

## Checkpoint 2026-11-14 — controller review PR17: changes_requested, task0010 reopened

Exact reviewed candidate **37a87291ae66a0fa9167f0c72d1e8340aa5fd245**, main9903d9b; keputusan dipublikasikan di [PR18](https://github.com/smahud/MicroTix_Project/pull/18), branch `review/0010-pa006-controller-20261114`, first verified ancestorbb9241ccbf78bffd2ffc19c1cfb232d6dff8be1a, belum integrated. [Laporan controller](../report/controller/20261114T153739Z-0010-pa006-review.md) menautkan dua independent source reviews, command/log dan enam conformance probes gagal. Root PostgreSQL17.11 NOSUPERUSER/NOBYPASSRLS: targeted48 passed, full401 passed (3 adapter-thread warnings), check/migration consistency/docs PASS; CI candidate43609853986 backend/frontend/docs success.

**REV-1311-01/02/03 masih OPEN**: actual old-code upload→0004→retry menduplikasi submission/file1→2; injected old-schema ambiguous claim dihapus lalu invoice kedua; resolusi sesi A/B204/204 dengan decisions[2,0], malformed/missing parent cached204; typed package UUID alias200→409. **REV-1411-04 P2**: bukti race direct-method bukan concurrent authenticated HTTP, lock polling dapat timeout tanpa gagal, after-write rollback/contender takeover belum dibuktikan. Klaim all-PASS/penutupan REV-1111-11 pada penyerahan di bawah **tidak diterima controller**.

Packet [0010](../task/0010-pa006-idempotency_done.md) kembali unfinished **ready / changes_requested**, ID sama; objective/scope/mandatory work/full acceptance asli dipulihkan dan prior correction PR16 ditautkan. Next actor **coding_agent**: fetch ref keputusan ini, tutup empat finding dengan finding→change→closing test→actual evidence, resubmit exact SHA baru. Perbaikan yang sudah benar/PA-001/histori executor dipertahankan. PA-002/003 belum eligible, tidak ada task dependent baru, merge/deploy/tag. Beta **NOT_READY**; host/lab/DR/capacity NOT_RUN. Sumber/bukti dan status publikasi terverifikasi di laporan/handoff, bukan chat saja.

## Checkpoint 2026-11-14 — riwayat klaim executor task0010/PA-006: HTTP idempotency aman terhadap scope dan race (penyerahan executor)

**Scope**: implementasi penuh PA-006 pada sandbox (PostgreSQL 17.11 nyata, peran runtime non-superuser `mtx_app` — RLS FORCE efektif). Baseline main `9903d9b` (PR10–12 hanya dokumentasi; source PA-006 identik dengan baseline packet `a0f653e`). Branch kandidat `session/2026-11-14-pa006-idempotency` (PR #17); **tested SHA `774b191`** (source produksi implementasi `5922e1f` + fix portabilitas observer tes CI; suite 401 passed pada konten `774b191`); commit penyerahan setelahnya metadata-only. Packet direname `0010-pa006-idempotency_done.md` (execution `done`, review `pending`) — menunggu controller review exact SHA.

**Perubahan inti**: (1) `common/idempotency.py` — protokol claim/replay SATU transaksi: identitas canonical 5-tuple (principal + tenant/platform + operation + resource + key), claim `INSERT … ON CONFLICT DO NOTHING RETURNING` (konkuren menunggu lalu MEREPLAY — bukan 409 permanen/500/duplikat), respons 2xx tersimpan bersama efek domain, exception → rollback klaim+efek (retry key semula), record tanpa respons ditolak aman, UUID alias dikanonikalisasi, structured malformed → 422, `platform=True` scope eksplisit stabil lintas active tenant, `resource_uuid=False` untuk token opaque; (2) migrasi `jobs/0004` — kolom identitas + `uq_idem_identity`, backfill canonical, dedupe alias, purge klaim tanpa respons/salah bentuk, resource opaque dipertahankan; (3) call-site `payment_submission` resource `invoice_id`, tiga platform ops `platform=True`, `identity_conflict_resolve` opaque; (4) 18 tes PA-006 baru (interleaving dipaksa penahanan kunci baris + observasi `pg_stat_activity` via pengamat psycopg; klien HTTP independen per principal) + koreksi ekspektasi malformed submission_id 404→422 sesuai acceptance.

**Bukti (semua PostgreSQL nyata)**: targeted PA-006 **18/18**; suite penuh **401 passed** (baseline 383, tanpa regresi); PA-001 konkurensi **10/10**; `manage.py check` 0 issue; `makemigrations --check` bersih; migrasi 0004 + `grant_runtime` pada dev DB; docs check PASS; frontend paritas CI (`tsc`/`eslint`/`vitest 66`/`check_i18n`/`vite build` live) exit 0. Matriks acceptance → actual result → evidence lengkap (semua baris PASS) pada `report/orchestrator/20261114T150000Z-0010-pa006-idempotency.md` + tabel 28 call site. Review internal (sub-agent read-only): `report/reviewer/20261114T150000Z-0010-pa006-review.md` — LULUS DENGAN CATATAN (6×P3, tanpa P1/P2); dua koreksi minimum diterapkan sebelum penyerahan.

**Follow-up berbukuti (di luar scope PA-006, belum ditugaskan)**: FUP-001 `resolve_membership` malformed tenant → 500 (pra-ada, semua endpoint tenant); FUP-002 berkas yatim upload saat rollback; FUP-003 iterasi antrean platform per tenant. NOT_RUN: host Gate A/G, lab G1, benchmark S6. REV-1111-11 ditutup PADA KANDIDAT menunggu review; Beta tetap NOT_READY.

## Checkpoint 2026-11-12 — Reviewer: PA-006 belum diserahkan

Master prompt reviewer dijalankan terhadap `main@9903d9b0cf09d737b553da3c21067b4810e956c0` (PR10/11/12 merged). Pemeriksaan controller dan reviewer independen atas 14 branch remote, task/report, ancestry dan dua PR terbuka tidak menemukan candidate implementasi PA-006. Helper idempotency masih blob yang sama di seluruh branch; delta source dari baseline packet kosong. Verdict **not_submitted**, execution **ready**, implementation reviewed/tested SHA N/A. Tidak membuat acceptance, `_done`, task duplikat atau task0020 dependent.

Next actor **coding_agent**: jalankan prompt executor dan implementasikan/resume packet0010 di sandbox, lalu publish candidate+execution report+acceptance evidence. Scope/acceptance PA-006 tetap. Keputusan/publikasi/checks ditautkan pada [review controller](../report/controller/20261112T072128Z-0010-pa006-review.md), branch `review/0010-pa006-submission-check-20261112` sampai integrasi. Main CI run43172995657 backend/docs/frontend success adalah bukti main, bukan hasil implementasi PA-006. Runtime application/host/lab/deploy NOT_RUN oleh controller; Beta tetap NOT_READY.

Publication checkpoint: branch keputusan `92e6c6a99f82aca4fa4f20440c7591f324d96d44` / tree `52ce0efdac35e628c1740ff31ef79ac4c7ad03e9` terverifikasi remote dan identik dengan lima file yang diperiksa. Closure descendant memperbarui bukti publikasi saja; final SHA/PR/CI diperiksa dari GitHub. Docs PASS24/106, lima changed-Markdown26local-links/diffcheck PASS dan independent consistency review APPROVED untuk record status, bukan acceptance PA-006. Main tidak di-merge atau deploy.

## Checkpoint 2026-11-12 — Default prompts executor dan controller reviewer

Permintaan pemilik: siapkan prompt tetap untuk kedua peran di semua sesi, tanpa kehilangan konteks atau keluar dari rencana. Baseline remote main2278b7741bb5ec38757cc7d3659b9099c31341ea (PR11 merged). Dibuat docs/MASTER_PROMPT_EXECUTOR.md dan MASTER_PROMPT_REVIEWER.md; MASTER_PROMPT lama menjadi indeks kompatibel. CONTRACT §6A, README/docs index, panduan task dan handoff menautkan kedua peran. Prompt mengambil task/candidate/ref aktual, memisahkan internal review dari controller acceptance, menutup koreksi pada ID sama, serta menyimpan partial checkpoint/evidence/next actor pada record existing.

Tidak membuat framework, backlog baru atau penugasan duplikat; tidak mengubah acceptance/task0010 atau source/schema/installer/dependency. Task0010 PA006 tetap ready/not_submitted; next actor coding_agent. Docs PASS24files/106links, final changed-Markdown107links dan independent review APPROVED. Publikasi awal PR12/639dca9 terverifikasi; final refs/CI/outcome diperiksa melalui PR/Git. Bukti rinci di report/controller/20261112T065349Z-default-agent-prompts.md. Runtime application/lab/deploy NOT_RUN oleh controller; Production Beta tetap NOT_READY.

## Checkpoint 2026-11-12 — GitHub sebagai jalur komunikasi controller/coding

Permintaan pemilik: periksa hasil pekerjaan task, rapikan komunikasi controller→coding agent→review→koreksi/next task, lalu lanjut menuju Beta. Baseline main a0f653e (PR10 merged), CI main43148282521 success. Task0010 tetap ready/not_submitted; belum ditemukan implementation PR/branch/report task0010 pada refs yang diperiksa, sehingga next actor coding_agent, bukan review hasil kosong.

CONTRACT §6A/panduan §6 diperjelas: acceptance→actual evidence pada execution report, separate exact-SHA controller verdict/findings, next actor/action dan published ref/PR pointers sebelum pergantian peran. Candidate di unmerged PR harus diperiksa sebelum main-ready dianggap belum diklaim. Packet0010 ditambah result/review pointers dan empty-result summary yang jujur; task0020 belum dibuat. Source/acceptance PA006, schema, installer, dependency dan deployment tidak berubah. Laporan/checks/review/publication: report/controller/20261112T051809Z-task-communication-loop.md. Application tests/real lab/DR NOT_RUN sesi dokumentasi ini; Beta tetap NOT_READY.

## Checkpoint 2026-11-12 — Task repository dan CONTRACT §6A

Pemilik menyetujui workflow pada breakdown sebelumnya dan meminta aturan dimasukkan ke CONTRACT/docs. Baseline remote a2207b66cc705fece79645034ea45900e81a9f38; pekerjaan di branch docs/task-workflow-20261112, terisolasi dari branch PR7/PR8.

Dibuat entry tetap task/0000-start-here.md dan packet ID0010/PA-006 (ready/not_submitted, belum implementasi). CONTRACT §6A menetapkan stable four-digit IDs, completion rename _done yang dipush, review exact SHA terpisah, reopening same-ID, blocker/dependency/resume dan laporan wajib. README, MASTER_PROMPT, IMPLEMENTATION_PLAN, indeks docs serta AGENT_HANDOFF diarahkan ke entry yang sama; latest handoff tetap sumber status aktual.

Sesi ini khusus dokumentasi; tidak mengubah source/schema/installer/dependency atau deployment. App tests/CHR/restore NOT_RUN; validator PASS22file/78link, manual80local-links dan diff checks PASS, independent review APPROVED sesudah koreksi DTR-01 eventual replay. Publikasi awal PR10/44b0e4 terverifikasi; final remote refs/CI harus diperiksa kembali, bukan disimpulkan dari checkpoint ini. Evidence pada report/controller/20261112T031235Z-task-workflow-contract.md. PA-001 tetap merged; Beta tetap NOT_READY; executor berikutnya mengerjakan PA-006 di sandbox.

## Checkpoint SESI-2026-11-11 (final) — Verifikasi independen & MERGE PR #9: PA-001 tuntas di main

**Scope**: verifikasi independen kandidat kedua PR #9 (`482602e`) di sandbox segar
(dibangun ulang dari nol — platform didaur ulang), lalu integrasi merge ke main atas
wewenang eksplisit pemilik repo. Delta sejak SHA review (`3b20b56`→`482602e`, 2 commit
koreksi executor sebelumnya) direview terlebih dahulu sesuai instruksi packet §8.1.
Executor tunggal, tanpa sub-agent. Laporan:
`report/orchestrator/20261111T145417Z-pr9-merge-integration.md`.

**Verifikasi independen (PostgreSQL 17.11 nyata, peran RLS paritas CI, FreeRADIUS 3.2.7)**:
file konkurensi **10 passed stabil 3×**; **sensitivitas dikonfirmasi** — 5/6 tes baru GAGAL
pada kode kandidat pertama `3b20b56`, termasuk **deadlock nyata PostgreSQL** (persis prediksi
REV-1111-01); suite penuh **383 passed** (382 + radius real-binary); `manage.py check` 0
issue; docs check PASS (22 file/67 tautan); CI remote `482602e` 3 job success; scan
credential diff `16085f8..482602e` bersih (hanya fixture sintetis).

**Merge**: PR #9 MERGED (merge commit `8ce94d4`, metode merge-commit sesuai konvensi;
SHA target dikunci saat merge; remote diverifikasi pasca-merge). Justifikasi: wewenang
pemilik (PAT "commit, merge, atau push" via kanal chat — CONTRACT §12), acceptance
Lampiran A terpenuhi seluruhnya + tes sensitif defect, CI hijau, tanpa perubahan
migrasi/kontrak API, dan tanpa merge main tetap memuat bug P0 lost-update. **Merge ≠
deploy**: `v0.1.0-beta.1` tetap NOT_READY — code blockers REV-1111-04–09/11/12 tetap
terbuka (LATEST_HANDOFF §3). Next packet: **PA-006** (principal-scoped idempotency +
HTTP replay/race), lalu **PA-002+PA-003** (job lifecycle fencing/drain); DEC-01 wajib
sebelum rehearsal S4.

## Checkpoint SESI-2026-11-11 (lanjutan) — Koreksi PR #9 sesuai review controller REV-1111

**Scope**: packet koreksi kandidat PR #9 (verdict review **REQUEST CHANGES** pada `3b20b56`).
Base: branch PR #9 `session/2026-11-11-pa001-payment-concurrency` @ `3b20b56`; SHA
main/PR7/PR8 diverifikasi TIDAK berubah sejak snapshot review controller. Executor
tunggal, tanpa sub-agent. Register review + dua lampiran reviewer dipersist di
`report/controller/20261111T074225Z-repo-handoff-review.md`,
`report/reviewer/20261111T073744Z-pr9-independent-review.md`,
`report/reviewer/20261111T073747Z-ops-readiness.md` (CONTRACT §10).

**Koreksi kode (REV-1111-01/02, smallest change, tanpa migrasi skema)**:
- `_parse_allocations` kini menggabungkan + mengurutkan kunci pada IDENTITAS UUID
  kanonik (`uuid.UUID`); `invoice_id` salah bentuk → 422 `ApiError.validation` (pola
  `billing/views._parse_uuid`); ejaan alias satu invoice (besar/kecil, hyphen/compact)
  tergabung satu alokasi; hasil dikembalikan dalam urutan permintaan teragregasi semula
  sehingga customer/bahasa kwitansi (I18N-01) tetap mengikuti invoice pertama-diminta.
- +6 tes regresi (total file 10): alias merge; malformed 422 + UUID-valid-tak-dikenal
  tetap 404; kwitansi multi-customer beda bahasa; **rollback pasca-tulis** (bloker
  dedup outbox, error ditangkap di luar tenant_scope, file yatim dihitung terpisah);
  **kontensi terkontrol** (kunci ditahan + pg_stat_activity + probe NOWAIT membuktikan
  urutan akuisisi canonical); konkurensi campuran ejaan tanpa deadlock. Tes lama klaim
  "rollback penuh" direname/disempitkan: bukti saat itu = validasi-di-muka.
- **Koreksi klaim (REV-1111-10)**: handoff lama "penahan beta tunggal Gate A/G, BUKAN
  pekerjaan kode" DICABUT — code blockers terbuka kini tercantum eksplisit (installer
  REV-1111-04, upgrade/repair gates 05, worker fencing 06, restore/DR 07, topology
  DEC-01 08, scheduler 09, security/idempotency 11, kapasitas 12); klaim timer
  `issue_due_invoices` dipasang installer dicabut (scheduler belum diimplementasikan);
  docs CI PR #7/#8 = manifest mismatch (bukan bukti SSTP runtime).

**Verifikasi sandbox (PostgreSQL 17.5 nyata)**: file konkurensi **10 passed** (stabil
4 run); **sensitivitas: 5/6 tes baru GAGAL pada kode kandidat pertama** — termasuk
deadlock nyata terdeteksi PostgreSQL pada konkurensi alias (persis prediksi
REV-1111-01); suite penuh **382 passed, 1 skipped** (376 baseline + 6 baru);
`manage.py check` 0 issue; docs check PASS. NOT_RUN jujur: FreeRADIUS daemon, frontend
jobs (CI PR memverifikasi; diff tidak menyentuh `apps/web`), Playwright, HTTP
idempotency (PA-006), rehearsal installer (sandbox tanpa systemd/root), restore/DR.
PA-001 tetap **menunggu review ulang controller** pada SHA kandidat kedua — bukan
accepted/closed. Detail: report/orchestrator/20261111T092854Z-pa001-canonical-identity-corrections.md.

## Checkpoint SESI-2026-11-11 — PA-001 P0 integritas alokasi pembayaran (mandat sandbox-first)

**Scope**: mulai dari `main` @ `16085f8` (clean; CI main hijau diverifikasi via API).
Prioritas: **PA-001 (P0) dari planning audit 2026-11-10** sesuai mandat master prompt
user revisi 2026-11-10 (semua pekerjaan sandbox executor terlebih dahulu; tidak ada
akses/aksi target produksi). Executor tunggal, tanpa sub-agent (slice kecil kohesif).

**Root cause terverifikasi pada SHA aktual** (bukan narasi audit): `_parse_allocations`
membaca `paid_amount` tanpa kunci baris + `verify_payment` read-modify-write dari
snapshot basi; kunci hanya di baris payment → dua payment BERBEDA pada invoice sama
bisa lost update + over-allocation. Reproduksi dua koneksi PostgreSQL nyata (PID
backend berbeda): paid=200.000, SUM alokasi=400.000 pada invoice 300.000, kedua
verifikasi "ok".

**Perbaikan (PR #9, `session/2026-11-11-pa001-payment-concurrency`)**:
- `select_for_update()` baris invoice dalam urutan id deterministik (+17/−4, satu
  fungsi, tanpa migrasi skema); urutan kunci payment → invoice terurut → tenant tanpa
  inversi dengan jalur penerbitan; alternatif ditolak tercatat (CHECK constraint
  ditunda ke packet hardening skema; F() redundan; nowait+retry mengubah semantik).
- Tes regresi permanen `test_billing_payment_concurrency.py` (4) — dua koneksi PG
  nyata per thread: over-allocation ditolak 409 bersih (pemenang lengkap, yang kalah
  nihil efek); 100rb+200rb penuh tanpa lost update; urutan body dibalik tanpa
  deadlock + kwitansi unik; kegagalan alokasi rollback penuh. Sensitivitas: 3/4
  gagal pada kode lama.
- Verifikasi sandbox (PG 17 nyata): backend **376/376** (baseline 372/372),
  `manage.py check` 0 issue, docs check PASS. NOT_RUN jujur: FreeRADIUS daemon,
  frontend jobs (diff bersih dari `apps/web`; CI PR memverifikasi), Playwright,
  rehearsal installer (sandbox tanpa systemd; di luar scope).
- PR #9 OPEN menunggu review controller; SHA head diverifikasi via API setelah push.
  Detail lengkap: report/orchestrator/20261111T060010Z-pa001-payment-allocation-concurrency.md.

## Checkpoint SESI-2026-11-07-lanjutan — Phase-2 SSTP (master directive konektivitas)

**Scope**: mulai dari `main` @ `16085f8` (handoff kanonis Phase-1; bersih).
Prioritas: kelanjutan direktif user "Secure Router Connectivity" — **Phase-2
SSTP** yang pada handoff sebelumnya berstatus PROPOSED menunggu keputusan
user (kelanjutan diberikan pada sesi ini + PAT untuk commit/push).

**Hasil Phase-2 (SSTP — kanal manajemen KOMPLEMENTER WireGuard):**
- **Protokol aktif untuk v6+v7**: `protocol=sstp` diterima (SSTP klien hadir
  di jalur v6.49.x DAN v7 — matriks kapabilitas); v5- ditolak 422 jujur;
  WireGuard tetap wajib v7.1+. RouterOS v6 kini dapat onboarding read-only.
- **Kredensial per-router (SstpAccount, migrasi 0011 + RLS + FK komposit)**:
  username unik GLOBAL lintas tenant (`mtx-<kode>-<suffix>`; tumbukan
  ditangani retry bounded) + password CSPRNG 192-bit SecretBox. Plaintext
  keluar hanya ke skrip bootstrap (pemilik, TTL 15 menit) dan chap-secrets
  ops host (0600). Revoke: release/replace ⇒ state REMOVED (tak dirender).
- **Skrip bootstrap v6/v7** (sintaks berjarak, didokumentasikan lintas versi):
  `authentication=mschap2` SAJA, `verify-server-certificate=yes` +
  `verify-server-address-from-certificate=yes` WAJIB (tidak ada opsi
  mematikan), CA platform diunduh dari endpoint publik
  `/api/v1/bridge/enroll-ca` lalu diimpor, rule API-SSL hanya dari alamat
  PPP server (.2), TANPA add-default-route, /32 dialokasikan server-side
  (bukan diketik di router), callback body token+username (§2.2).
- **Bridge sadar-protokol**: identitas SSTP = username kredensial (dicocokkan
  dengan SstpAccount — mismatch 409 `sstp_identity_mismatch`); replay
  identitas sama = hasil logis sama; kunci WG pada enrollment SSTP = 422
  (dan sebaliknya).
- **Kejujuran verifikasi diperluas**: `verification.sstp` (simulator ⇒ False;
  jalur api_ssl probe NYATA via sesi PPP ⇒ True; wireguard tetap False
  untuk enrollment SSTP — tidak ada klaim silang).
- **Server SSTP = accel-ppp 1.15.0** (build dari sumber dipin SHA-256 —
  `backend/scripts/build_accel_ppp.sh`; tidak ada paket resmi Debian):
  TLS 1.2 + `AES256-SHA:AES256-GCM-SHA384` (dua suite terdokumentasi klien
  RouterOS), shared-port `vpn.sstp_listen_port` (defaults rev **2.4**, param
  ke-116; default 4443 — 443 dipakai Caddy), `single-session=replace`,
  `mppe=deny`; render `manage.py render_sstp_config` (accel-ppp.conf +
  chap-secrets; format baris `username password <ip-statis>` diverifikasi
  dari chap-secrets.c 1.15.0). Installer `setup_sstp` fase-aware
  `MT_ENABLE_SSTP=1` (pola MT_ENABLE_RADIUS): CA privat 10 th + sertifikat
  gateway SAN=MT_DOMAIN (auto-regen saat SAN berubah), unit
  `microtix-sstp.service`, health gate + doctor + repair/upgrade idempoten.
- **Amendemen normatif ROUTEROS.md §2.3** (SSTP komplementer; keputusan user
  master directive = persetujuan eksplisit; catatan keputusan pada laporan
  sesi report/orchestrator/).
- **Lab GNS3 profil minimal Phase-2** (`lab/`): topologi deklaratif 2 tahap
  (A: gw+CHR+1 klien; B: + tenant kedua **LAN sama 192.168.88.0/24** — bukti
  isolasi), provisioner API-driven stdlib (deteksi family API dari
  /version per OPERATIONS.md), checklist bukti G1 (termasuk uji NEGATIF
  verifikasi sertifikat). Status: IMPLEMENTED, **BELUM VERIFIED_LAB**
  (aset CHR/controller belum tersedia — jujur, bukan klaim).

**Verifikasi (nyata, PG 17.11)**: backend **391/391** (+18 SSTP:
test_sstp_flow.py) + makemigrations --check bersih + `manage.py check` OK +
FreeRADIUS nyata **15/15**; FE tsc/eslint 0 + vitest **67/67** + i18n paritas
**1063** + build live OK (mock DITOLAK); `make e2e` **12/12** (Chromium +
backend + worker nyata); docs check PASS; `bash -n` installer + build script
OK (shellcheck tidak tersedia di sandbox — dicatat jujur).

**Blok tetap**: Gate A/G host Debian 13 nyata (penahan tag beta tunggal);
lab G1 (CHR/controller) untuk bukti perangkat nyata — simulator tetap tidak
pernah diklaim sebagai konektivitas nyata.

## Checkpoint SESI-2026-11-07 — Onboarding router aman Phase-1 (master directive konektivitas)

**Scope**: mulai dari `main` @ `7d60014` (handoff kanonis lanjutan 4; bersih).
Prioritas: **master prompt user "MicroTix Secure Router Connectivity & Beta
Continuation"** (P0 — mengesampingkan urutan TK-701/TK-602 dari handoff
sebelumnya sebagai keputusan user eksplisit; bukan perubahan dokumen normatif —
arsitektur multi-protokol shared-port dicatat PROPOSED di laporan sesi).

Orkestrasi sub-agent per CONTRACT §5: 3 paralel read-only (backend-explorer
audit enrollment; frontend-explorer audit UX wizard; researcher matriks
kapabilitas VPN RouterOS bersumber vendor) + 1 reviewer independen
(REQUEST_CHANGES 2 P1 → keduanya diselesaikan/didakumentasikan + verifikasi
ulang hijau; disposition: report/reviewer/20261106T194638Z-*.md).

**Hasil Phase-1 (WireGuard hardening — slice vertikal terkecil):**
- **Perbaikan bug P0 skrip bootstrap**: endpoint peer kini hostname gateway
  PUBLIK terkonfigurasi (rantai `vpn.gateway_hostname` baru di defaults.json
  rev 2.3 → MT_PUBLIC_HOST → MT_DOMAIN; produksi tanpa nilai = 409 jujur;
  dev/test = `microtix.invalid`) — menggantikan bug endpoint IP-tunnel-internal
  `100.127.0.1` + fallback palsu `microtix.example`; artefak SCEP & baris
  pembacaan private-key dihapus; port dari state host/enrollment (bukan
  hardcode); body JSON callback dengan escape RouterOS benar; token tetap
  hash-only + SecretBox + cleared-on-consume + di-body (§2.2).
- **Kejujuran verifikasi (false-positive dimatikan)**: `capability.source` =
  adapter AKTIF (bukan hardcode simulator); jalur simulator ⇒
  `api_ssl/wireguard = False` + catatan (TIDAK mengklaim terhubung — sebelumnya
  `True` tanpa bukti); jalur `MT_ROUTEROS_ADAPTER=api_ssl` melakukan probe
  TCP+TLS NYATA sebelum router dibuat (pin = fingerprint TERAMATI), gagal →
  JobError retryable dengan re-entry VERIFYING (bounded max_attempts) — plus
  bug "retry terkunci" diperbaiki (temuan reviewer P1-1). Progress API +
  detail router memaparkan `verification` ternormalisasi; UI wizard & detail
  menampilkan banner/chip "Simulasi — perangkat nyata belum terverifikasi".
- **Protokol + versi RouterOS (UX §9)**: field `protocol`+`routeros_version`
  pada enrollment (migrasi 0010; default wireguard/"7" — API lama tetap sah);
  WireGuard wajib v7.1+ (v7.0/v6 ditolak 422 dengan alasan); SSTP/L2TP/OpenVPN
  tampil "direncanakan" di picker (ditolak jujur backend+mock paritas).
- **Isolasi diperkuat**: `uq_wgpeer_pubkey_active` (kunci publik WG unik global
  untuk peer AKTIF — 409 lintas tenant tanpa bocoran info) + perbaikan bug
  alokasi IP tunnel buta-RLS (dua tenant bisa memilih /32 sama → IntegrityError
  500; kini iterasi scope per tenant sesuai konvensi `_any_active_peer`).
- **UX wizard**: pemilih versi+protokol jujur (disabled reason), baris endpoint
  gateway di langkah Skrip (§2.2 "UI menunjukkan tujuan endpoint"), banner
  simulasi di langkah Siap, chip sumber verifikasi di detail router.
- **Installer**: `MT_DOMAIN` kini diteruskan ke env aplikasi (pembuatan +
  append-if-missing idempoten) sebagai sumber hostname gateway.
- **E2E**: `routers.spec.ts` (2 spec) mengendarai backend+worker NYATA penuh:
  wizard→skrip→callback bridge (CSRF seperti SPA)→job verify diproses
  worker→"Siap" berlabel Simulasi→detail router; plus v6 memblokir kelanjutan.
  Harness run.sh kini menjalankan `runworker` proses terpisah.

**Verifikasi aktual** (PG 17.11 nyata): backend **373/373** (+14 baru);
makemigrations --check bersih; FreeRADIUS nyata **15/15**; FE tsc/eslint 0 +
vitest **66/61+5** + i18n paritas **1062**; build live OK + mock DITOLAK;
`make e2e` **12/10+2** (Chromium nyata); bash -n instalasi.sh OK.

**Honest gap (lab G1 — jangan dianggap lulus)**: sintaks skrip RouterOS v7
pada perangkat nyata; `check-certificate` callback fetch (gap MITM token
terdokumentasi — dibatasi token sekali pakai/TTL/konsumsi atomik); skrip v2
(akun API-SSL platform pada router — jalur login penuh); handshake WG nyata;
dua tenant LAN tumpang tindih pada jaringan nyata. Multi-protokol (SSTP →
L2TP → OpenVPN) = Phase 2-3 sesuai matriks kapabilitas bersumber vendor.
Detail lengkap + keputusan: report/orchestrator/20261106T195642Z-phase1-wireguard-onboarding.md.

## Checkpoint SESI-2026-11-06 (lanjutan 4) — TK-604 UI billing U09/U10

**Scope**: mulai dari `main` @ `62595f4` (handoff lanjutan 3; CI hijau
diverifikasi via API; 0 PR terbuka). Prioritas handoff §5 urutan 1: **TK-604**
(konsumsi API billing nyata TK-601/TK-109 oleh UI). Orkestrasi sub-agent per
CONTRACT §5: 2 explorer read-only (laporan API-contract + pola FE di
report/backend-explorer|frontend-explorer/) + 1 reviewer independen
(REQUEST_CHANGES → P0/P1 + P2 layak-perbaiki diselesaikan; lihat
report/reviewer/20261106T173900Z-tk604-independent-review.md).

**TK-604 — U09 Tagihan dan Pembayaran + U10 Aktivasi (R2 aktif)**:
- **U09** `features/billing/BillingPage.tsx`: tiga tab Invoice·Pengajuan
  (submitted/ditolak)·Terverifikasi; periode filter selalu terlihat;
  strip aging 5 bucket (BIL-05); catat penerimaan (bukti wajib
  transfer/e-wallet, base64 ≤5 MiB); verifikasi dana dua tahap dengan editor
  alokasi (≤ payment, ≤ sisa tagihan; sisa=kredit "belum dialokasikan");
  tolak + alasan wajib; PDF invoice/kwitansi via tautan same-origin (sesi
  cookie); pasca-verifikasi banner "N menunggu aktivasi" → CTA U10.
- **U10** `features/activation/ActivationPage.tsx`: kandidat akun suspended
  (`access-accounts?state=`) + kelayakan dari invoice nyata
  (`lib/billing-eligibility.ts`: tanpa tertunggak + pernah lunas;
  `fetchAllPages` menilai >1 halaman, maks 10×200); snapshot konfirmasi
  (N layak/M tidak) → validasi kondisi TERBARU per item (refetch akun+invoice)
  → PATCH per item; item asing/berubah blok item itu saja (keberhasilan
  tidak diurungkan — done_when teruji e2e "1 berhasil, 1 diblokir"); hasil
  per item + retry item belum berhasil; label jujur router non-otoritatif
  "Belum dijamin di router ini" (router tak dikenal ≠ dijamin).
- **Backend additif**: `radius_account_row` + service_id/service_code/
  customer_name (identitas U10; kontrak uji diperbarui); kursor masuk
  DITERAPKAN pada /invoices + /payments (pra-ada: next_cursor diterbitkan
  tapi cursor diabaikan — +4 tes); BARU `seed_billing_e2e` (tenant ketiga
  terpisah; jalur services nyata; reset state-mutabel antar-run, bukti
  immutable tak disentuh — proteksi DB terbukti saat percobaan delete).
- **Integrasi FE**: contracts.ts + 9 metode ApiClient (live+mock paritas;
  mock activate/suspend permission diselaraskan ke `services.activate` +
  idempoten paritas 204); rute + release-flag billing/activation → true
  (uji flag diperbarui); tab Tagihan CustomerDetail diisi (invoice per
  layanan); kolom payment/isolation CustomersPage kini tone benar
  (`paymentTone`/`isolationTone` — latent terekspos flag); i18n +134 kunci
  (1042 total, paritas penuh) + grup enum baru di check_i18n.
- **E2E**: `e2e/specs/billing.spec.ts` (3 spec: PDF nyata %PDF; blokir per
  item; verifikasi+kwitansi→aktivasi→kosong) + run.sh seed/ekspor tenant.

**Verifikasi aktual** (PG 17.11 nyata; sandbox Debian 13 non-root):
backend **359/355+4 PASS**; makemigrations --check bersih; FreeRADIUS nyata
**15/15**; FE tsc/eslint 0 + vitest **61/42+19** + i18n paritas; build live
OK + build mock DITOLAK; `make e2e` **10/7+3** (Chromium nyata); docs check
PASS; bash -n instalasi.sh OK.

**Honest gap**: bukti transfer belum dapat diperbesar (backend tanpa endpoint
bukti — hanya `has_proof`); verifikasi belum menyebut rekening (tak ada di
kontrak M6); "Menunggu koneksi" butuh bukti NAS (G1) — digantikan label
jujur; kelayakan dibatasi 10 halaman×200; spec e2e billing bergantung
urutan (workers:1). Detail: report/orchestrator/20261106T174500Z-tk604-billing-ui.md.

## Checkpoint SESI-2026-11-06 (lanjutan 3) — M6 billing engine (TK-601) + dokumen PDF (TK-109)

**Scope**: mulai dari `main` @ `79c42ec` (CI hijau diverifikasi via API;
0 PR terbuka; cabang arsip di-port saat INTEGRATION-1 — tanpa pekerjaan
yang belum digabung). Lingkungan sandbox dibangun ulang via
`docs/tools/setup_env.sh` (deb-extract PG 17.11 + FreeRADIUS 3.2.7).
Titik masuk topologis R2: **TK-109** (render PDF — prasyarat build TK-601,
tugas M1 terakhir `not_started`) → **TK-601** (mesin invoice internet).
Orkestrasi sub-agent per CONTRACT §5: implementasi `domains.documents`
(TK-109) didelegasikan ke sub-agent di worktree terisolasi
(`session/2026-11-06-docs-tk109`; diff direview + diintegrasikan oleh
orchestrator); `domains.billing` (TK-601) dikerjakan orchestrator.

**TK-109 — dokumen terbit PDF immutable** (`domains.documents`):
- `IssuedDocument` (tenant, kind, doc_number UNIQUE(tenant,kind,number),
  ref_type/ref_id polimorfik, locale/timezone/template_version/values
  snapshot, storage_path opaque 0600, sha256, size) — **trigger DB
  immutability** (BEFORE UPDATE OR DELETE, pola subs source event).
- Renderer HTML→PDF per ARCHITECTURE.md §1 ("Dokumen"): **xhtml2pdf 0.2.28**
  dipin (murni Python/wheels — tanpa pango/cairo; reportlab
  `rl_config.invariant=1` → **PDF byte-deterministik**; keputusan solusi
  terkecil dicatat di laporan sesi). Pembatasan jaringan/file dua lapis:
  `ResourceAccessPolicy(allow_remote=False)` + guard `src=/href=` eksternal
  (422) — tanpa fetch URL/berkas; semua nilai di-escape (anti injeksi HTML);
  label dari katalog i18n (doc.*), bulan `doc.month.1..12`, format IDR
  `Rp1.500.000` / `IDR 1,500,000` (I18N-03).
- Bahasa rantai I18N-01 §2 (pelanggan → tenant → id; fallback parent),
  snapshot saat issued; **reprint membaca artifact tersimpan + cek sha256**
  (template v2 tidak pernah mengubah reprint — T23-I18-02 teruji).
- API: GET /tenants/{t}/documents (kursor+filter) + GET .../{id} (PDF,
  application/pdf, filename sanitasi) — customers.read; 401/403/404 jujur.
- Tes: 15 unit + 9 integrasi (determinisme byte, escaping, guard eksternal,
  trigger, konflik nomor, isolasi tenant, reprint snapshot, integritas).

**TK-601 — mesin invoice internet M6** (`domains.billing`):
- `BillingPackage` (BIL-02: siklus fixed_monthly/anniversary, prepaid/
  postpaid, due_day clamp, first_period_policy full/prorata_daily ceil
  Rp100/free; **anniversary + policy≠full ditolak jujur** — tanpa batas
  kalender eksplisit; nama unik per tenant).
- `InternetInvoice` (+lines): snapshot harga/kebijakan saat terbit
  (perubahan harga paket TIDAK mengubah invoice issued — teruji);
  **UNIQUE(tenant, service, kind, period_start, period_end)** mencegah
  scheduler ganda (AC-BIL teruji dua run hari sama + IntegrityError langsung);
  nomor `INV-{ns}-{YYYYMM}-{urut}` via kunci baris tenant (terserialisasi);
  state draft/open/partial/paid/void; total 0 (free_until_next_period) →
  paid jujur.
- `ServiceCharge` (BIL-07): add_on/diskon nominal/persen + jendela masa
  berlaku — semua disnapshot ke line; total negatif ditolak
  (billing.invalid_total, bukan dipotong diam-diam).
- `InternetPayment` (BIL-03 dua tahap): submitted (bukti upload ≠ posted;
  transfer/e-wallet WAJIB bukti via pipeline TK-106 magic-bytes) →
  verified (allocation ke ≥1 invoice + kwitansi) | rejected (alasan wajib);
  `external_ref` unik per tenant (event bank sama dedup → 409; dua transfer
  nyata tetap dua payment); alokasi ≤ nilai payment (sisa=kredit) dan ≤
  sisa tagihan; partial tidak melunasi; **pembayaran TIDAK menyentuh
  lifecycle service** (payment cannot auto-activate — teruji).
- Kwitansi `RCP-{ns}-{YYYYMM}-{urut}` (BIL-08) terbit saat verify (dokumen
  PDF menaut payment); alokasi kosong → kwitansi kredit penuh.
- Aging bucket 0-30/31-60/61-90/>90 + not_due vs due_date (BIL-05; laporan
  level invoice).
- Scheduler `manage.py issue_due_invoices` (--date/--tenant/--dry-run;
  tanggal tenant-lokal WIB/WITA/WIT — batas tengah hari lintas zona teruji;
  catch-up periode terutang; layanan bermasalah dilewati tanpa menghentikan
  tenant lain). **Pemasangan systemd timer 01:00 = langkah ops host Gate
  A/G** (tidak dipasang diam-diam).
- Field `Tenant.locale` (default id) + `Customer.locale` (kosong=belum diset)
  — rantai bahasa dokumen I18N-01/I18N-06; `Service.billing_package` FK
  PROTECT (paket dipakai tidak bisa dihapus — nonaktifkan via active).
- RLS FORCE + policy tenant_isolation pada 6 tabel billing; FK komposit
  (tenant,service)→customers_service, (tenant,invoice)→internet_invoice,
  (tenant,payment)/(tenant,invoice)→allocation; allocation PROTECT dua sisi
  (bukti keuangan tidak ikut terhapus).
- API (services.provision/customers.read/payments.verify sesuai metode;
  Idempotency-Key wajib pada mutasi; 401/403/404 generik sesuai §5):
  packages CRUD, service↔package, charges, invoices list/detail/aging,
  payments list/record/verify/reject/detail. UI U09/U10 = TK-604 (berikutnya).

**Bug latensi pra-ada diperbaiki**: `Makefile` `PY`/`MANAGE` relatif rusak
setelah `cd backend` (`backend/backend/.venv`) — target make test*
gagal menjalankan venv; kini absolut `$(CURDIR)`. CI tak terdampak
(CI memakai `python -m pytest` langsung) — make target kini benar-benar
dipakai lokal per IMPLEMENTATION_PLAN §4.

**Verifikasi aktual (PostgreSQL 17.11 nyata; peran mtx_migrator/mtx_app)**:
`pytest tests -q` **355/355 PASS** (252 baseline + 103 baru: 32 unit
kalender + 23 invoice flow + 21 payment + 24 documents + 3 kontrak);
`makemigrations --check` no changes; `manage.py check` 0 isu;
`make test` 138 / `make test-integration` 217 / `make test-contract` 29
semua PASS; FreeRADIUS nyata **15/15** (T16/T19/T20/T21); FE tsc/eslint
0 error, vitest **42/42**, build live OK, build mock DITOLAK (exit 1);
`make e2e` **7/7** (Chromium nyata, backend nyata); `bash -n instalasi.sh`
OK; docs check PASS.

**Honest gaps (bukan klaim)**: UI U09/U10 belum (TK-604); scheduler belum
dipasang sebagai timer host (Gate A/G); TK-602 isolir/TK-607 saldo
pembuka/TK-608 dokumen koreksi/TK-609 kolektor belum; ledger M7 (TK-701+)
belum — invoice/payment saat ini catatan sumber, tanpa posting ledger
(disesuaikan urutan topologis TK-701 setelah TK-601 build); dokumen
saas_invoice/report = kind terdaftar tanpa template (404 jujur).

**Push**: branch sesi + PR → merge ke `main` via PAT (diverifikasi
`git ls-remote` + CI hijau — lihat laporan sesi untuk SHA final).


## Checkpoint SESI-2026-11-06 (lanjutan 2) — setup_env.sh in-repo + fix harness T19 + push via PAT

**Scope**: sesi lanjutan setelah konteks habis DAN sandbox terdaur ulang di
tengah sesi (insiden: `/home/z/my-project` direset — commit lokal bagian-1
`64ac004`/`18cf506` hilang sebelum ter-push karena PAT belum tersedia).
Bagian-2: PAT diterima dari pengguna → lab dipulihkan dari `/tmp`, repo
di-clone ulang (`main` @ `f284ce8` terverifikasi), kedua commit
direkonstruksi byte-exact dari konteks + diverifikasi ulang penuh.

**Perubahan**: (1) `docs/tools/setup_env.sh` in-repo (`1e326dc`) — bootstrap
sandbox PG17+FreeRADIUS AGENT_HANDOFF §8; `MT_SANDBOX_BASE` overridable;
rebuild BYTE-IDENTIK (sha256 postgres+initdb); idempoten fresh+no-op;
shellcheck 0 findings; manifest `--refresh` 21→22 (docs PASS). (2)
`backend/scripts/test_radius.sh` (`98ea90d`) — fix klasifikasi T19:
no-reply radclient tidak lagi diklaim "KEBOCORAN TENANT" (konflasi terbukti
dari kode; 1x FAIL run pertama sesi ini, reproduksi 4/4 PASS, akar tidak
terbukti/bukti hilang — dugaan no-reply transient; lihat laporan sesi).
(3) Laporan: `report/orchestrator/20261106T063225Z-setup-env-inrepo-push.md`
+ handoff ini.

**Verifikasi ulang pasca-rekonstruksi**: backend **252/252** (2x), RADIUS
nyata **15/15** (6/7 run; 1 FAIL-T19 terinvestigasi + difix), docs PASS
(22 file), `instalasi.sh` bash -n OK (shellcheck 0 error, warning
pre-existing). FE: bit-identik dengan `f575388` CI-hijau — dijalankan CI
GitHub pada PR sesi ini.

**Push**: via PAT (hanya di `.git/config` lokal, tidak pernah di-commit).
**MERGED**: PR #3 → main `1d26b7e39ad8c4b0766cac0899eca708b4edfe27`
(diverifikasi `git ls-remote`; CI GitHub pada `8f6b173` HIJAU:
backend/frontend/docs success). Blokir beta tetap: Gate A/G, G1 lab
MikroTik, lab GNS3 §7.

## Checkpoint SESI-2026-11-06 — WireGuard host adoption + harness E2E (audit truth → WG-1 → E2E-1)

**Scope**: sesi pertama di bawah CONTRACT.md (report/). Mulai dari `main` @
`bbee21c`. Baseline diverifikasi ulang dari nol pada sandbox baru (PostgreSQL
17.11 deb-extract + patch jalur share non-root; FreeRADIUS 3.2.7 deb + libtalloc
/libpcap/libpq/rlm_sql_postgresql): **222/222 + RADIUS nyata 15/15 + FE 42/42 +
build live + docs PASS** — klaim konsolidasi sebelumnya TERKONFIRMASI.

### WG-1: adopsi keypair installer WireGuard host + render peers + probe (P1 handoff §5)

**Latar**: installer membuat keypair X25519 NYATA + `wg0.conf` + env
`MT_WG_SERVER_PUBKEY`, tapi backend MENGABAIKANNYA — `_wg_host()` membuat kunci
sendiri + publikasi placeholder deterministik (sha256 hex). Bootstrap script
memuat placeholder → tunnel tak akan pernah handshake pada host produksi.

**Implementasi** (jujur, tanpa weakening):
- `settings.py`: `MT_WG_SERVER_PUBKEY` divalidasi (X25519 base64 32-byte; salah → ImproperlyConfigured). Kunci privat TIDAK pernah masuk proses aplikasi.
- Model `WireGuardHost`: +`key_source` (installer_env|generated_dev) +`adopted_at` (migrasi 0009). RLS host tetap dikecualikan (platform singleton, sesuai 0004).
- `adopt_wg_host_key()` + command `adopt_wg_host` (--check utk doctor): idempoten; **rotasi DITOLAK bila ada peer aktif** (peers memegang kunci lama — rotasi = operasi jaringan terjadwal, bukan silent break); tanpa peer → adopsi + revision bump + private_key_ref dibersihkan.
- `render_host_config()` + command `render_wg_config`: render wg0.conf dari state host+peers lintas-tenant via `tenant_scope` eksplisit per tenant (§4, bukan broad SELECT); berkas 0600; **PrivateKey hanya dengan --private-key-file (root)**; PENDING/APPLIED/DRIFT dirender (desired), REMOVED tidak.
- `probe_handshakes()` + `probe_wg`: `wg show <iface> latest-handshakes` → pembaruan `last_handshake_at` monotonik + drift evidence (unknown_on_interface/missing_on_interface); binary/interface tak ada → **BLOCKED exit 2 jujur** (stub berlabel hanya utk jalur pembaruan di tes, source=stub — bukan klaim host).
- Desain: TIDAK menambah job kind — worker produksi berjalan non-root, `wg show` butuh root → job probe akan selalu gagal di topologi produksi; probe = command ops (jujur, anti-job-palsu). Gap registri `verify_api_ssl` (dipakai tapi hilang dari JOB_KINDS) DIPERBAIKI + daftar kind ARCHITECTURE §6 disinkronkan.
- Installer: `setup_wireguard()` kini memanggil `adopt_wg_host` (gagal = die, karena bootstrap dengan kunci salah = tunnel diam-diam rusak) + `render_wg_config` ke `$WG_DIR/rendered`; doctor menambah cek `adopt_wg_host --check`; upgrade menjalankan `setup_wireguard` (idempoten).

**Verifikasi**: **252/252** (222 + 23 WG + 7 hardening post-review: validasi pubkey X25519 murni teruji unit (F6), parser epoch overflow tidak fatal (F5), `--check` tanpa baris host = no_host read-only (F2), evidence source stub vs host_wg jujur (F3), migrasi state jobs/0003_alter_job_kind (F1 — P1 dari reviewer), gitignore artefak playwright (F4), asersi judul diperkuat (F8)). `make e2e` 7/7 hijau. Docs check PASS (manifest --refresh, perubahan disengaja).

### E2E-1: harness Playwright `make e2e` (P1 handoff §5 — mengganti NOT_RUN)

**Harness**: `apps/web/e2e` — Playwright 1.57 (Chromium 1200), backend runserver
NYATA (PG17+RLS, dev_bootstrap idempoten, seed 2 tenant), Vite dev + proxy
`/api` + `VITE_API_MODE=live` (guard anti-mock tetap berlaku); token verifikasi
email dibaca dari LOG email konsol (jalur email dev nyata — tanpa bypass API);
ID tenant seed diekspor dari DB utk uji isolasi; `--config` eksplisit (tanpa ini
playwright memuat spec vitest unit → 0 tes); vitest `exclude e2e/**`; tsconfig
baru `tsconfig.e2e.json` masuk `tsc -b`.

**Alur teruji (7/7, exit 0)**: login happy (owner seed) → overview data nyata;
login salah → pesan generik; `/app` tanpa sesi → redirect login; **isolasi
tenant: URL tenant asing → 404 envelope + nol data bocor di UI**; **register →
email (token konsol) → verify (klik) → login → tenant baru tampil**; landing
i18n id; mobile 360px drawer → empty state jujur.

**2 bug nyata ditemukan + diperbaiki harness** (bukti nilai harness):
1. FE: login non-MFA TIDAK pernah navigasi (`LoginPage` hanya menangani
   requires_totp; jalur TOTP-lah yang dites era mock). Fix: `navigate('/app')`
   + refresh konteks sesi paritas loginTotp.
2. CSRF: topologi dev proxy → Django 4+ menolak Origin 5173 (403 login di
   browser). Fix: `CSRF_TRUSTED_ORIGINS` non-produksi saja; produksi same-origin
   tetap kosong.

### Blocker (tetap, jujur)
- Gate A/G (host Debian 13 root+domain) + G1 (lab MikroTik) — prasyarat eksternal.
- Probe WG interface nyata + `wg-quick@wg0` — langkah ops host (BLOCKED di sandbox).
- CI e2e job di GitHub Actions belum ditambahkan (harness lokal hijau; caching browser CI = pekerjaan lanjutan).

### Langkah berikutnya
1. M6/M7 billing/ledger R2 (P2; docs/FINANCE.md) — slice vertikal berikutnya.
2. CI job e2e (opsional, hati-hati flakiness).
3. Ops host Gate A/G → `adopt_wg_host` + `probe_wg` + render pada host nyata.

## Checkpoint INTEGRATION-1 — Recovery dua agent paralel + konsolidasi beta-0.1 (preserve → audit → port → verifikasi)

**Scope**: master prompt V5. Dua agent bekerja paralel dari baseline `ee15ada`: Agent A mendorong 9 commit ke `main` (konsolidasi M3/M4/M5 + RADIUS nyata), Agent B mendorong 7 commit ke `parallel/beta-be2` (M3 inti + klien API-SSL + installer hardened; push sempat BLOCKED di environment asal, kemudian ter-push ke branch tersebut). Misi: selamatkan seluruh pekerjaan, audit keduanya, konsolidasikan tanpa duplikasi backend, verifikasi, siapkan beta.

### Pemetaan branch (zero work loss)

| Branch | Isi | Status |
|---|---|---|
| `main` (`cd5142c`) | 9 commit Agent A: M3 penuh (enrollment/discovery/cutover B0–B6/release-replace), M4 penuh (pelanggan/layanan/CSV/migrasi identitas), M5 (backup/monitoring/approval M2), RADIUS dengan **verifikasi FreeRADIUS nyata 15/15**, guard anti-mock, installer hardened | Diverifikasi ulang sesi ini: 207/207 tes + 15/15 RADIUS nyata |
| `parallel/beta-be2` (`c9023e6`) | 7 commit Agent B: enrollment/API-SSL native/facade radius multi-tenant/resolver/CSV subset/installer hardened/BETA_RELEASE_NOTES | Diverifikasi ulang sesi ini: 142/142 tes + smoke live 20/20 |
| `integration/beta-0.1` | Dari `origin/main` + port aset unik be2 (lihat bawah) | Kanonis kandidat beta |

Kedua branch dipertahankan apa adanya di remote (tidak ada force-push/reset; `parallel/beta-be2` tidak dihapus).

### Verifikasi ulang baseline (sebelum integrasi — bukan mengandalkan klaim lama)

| Target | Command | Hasil |
|---|---|---|
| main backend | `pytest tests -q` (PostgreSQL 17.11 nyata, peran mtx_migrator/mtx_app) | **207/207 PASS** |
| main RADIUS nyata | `bash scripts/test_radius.sh` (FreeRADIUS 3.2.7 non-root + radclient + relay UDP) | **15/15 PASS** — SETELAH perbaikan grant (lihat bug #1) |
| be2 backend | `pytest tests -q` (PG terpisah port 55433) | **142/142 PASS** |
| be2 smoke live | `bash scripts/smoke_live.sh` (runserver + curl) | **20/20 PASS** |
| main frontend | `tsc -b` / `eslint` / `vitest run` / `VITE_API_MODE=live vite build` | 0 error / 42/42 / build OK |
| docs + i18n | `check_docs.py` / `check_i18n.py` | PASS / parity 908 kunci |

### Bug konsolidasi yang ditemukan & diperbaiki (bukti reproduksi sesi ini)

| Bug | Dampak | Perbaikan |
|---|---|---|
| `grant_runtime` main hanya grant schema `public` | **P0**: peran runtime kehilangan akses schema `radius` pada DB milik migrator → proyeksi RADIUS patah di jalur produksi (tes lolos karena test-DB dimiliki app — terbukti saat `test_radius.sh` BLOCKED "permission denied for schema radius" pada instalasi bersih) | Port logika be2: enumerasi `pg_namespace` dinamis (public+radius+schema baru otomatis); `%I` di-escape `%%I` (psycopg + params). Bukti: revoke→grant→28 grant tabel radius + USAGE |
| `tenant_scope` non-reentrant (reset GUC ke kosong saat keluar scope dalam) | Scope bersarang (view→service, handler→service) memutus konteks scope luar; main hanya mengandalkan konvensi caller-provides-scope | Port be2: simpan nilai sebelumnya + pulihkan saat keluar; tanpa scope luar tetap fail-closed. Regresi test baru `test_nested_scope_restores_outer_context` |
| Klien API-SSL tidak ada di main | Jalur produksi `MT_ROUTEROS_ADAPTER` tidak tersedia — semua verifikasi hanya simulator | Port be2 utuh: `apiclient.py` (protokol biner + TLS + pin SHA-256 + bounded + anti-SSRF) + `cert_pin` RouterContext + factory `MT_ROUTEROS_ADAPTER=simulator\|api_ssl` + 14 tes (server TLS in-process). Mutasi menolak jujur `*_pending_lab` (gate G1) |
| Installer tanpa infrastruktur WireGuard host (§9.13) | Keypair host + wg0.conf tidak disiapkan; MT_WG_SERVER_PUBKEY tidak terpublikasi | Port be2: `setup_wireguard()` idempoten (key lama dipertahankan; private 600 via berkas) + exit code PARTIAL=3 |
| `dev_bootstrap.sh` be2 masih `BACKEND="$ROOT/backend"` | Skrip be2 gagal langkah 5 (main sudah punya fix) | Tidak di-port — versi main lebih benar |

### Keputusan konsolidasi (apa yang TIDAK di-port dari be2, dan alasannya)

| Item be2 | Keputusan | Alasan |
|---|---|---|
| `domains/access/*` (app AAA terpisah: models/resolver/services/views + migrasi 0001–0003) | **Tidak di-port** | Duplikasi domain `radius` milik main (master prompt §17: jangan dua versi backend). Versi main lebih lengkap (cutover B0–B6, reconciler, harness verifikasi nyata 15/15) dan punya bukti FreeRADIUS real |
| `domains/network/enrollment.py` + migrasi 0003–0005 be2 | **Tidak di-port** | main punya evolusi schema lebih jauh (migrasi 0003–0008: token_ref, enroll_bridge_policy, peer) + alur lengkap; migrasi be2 akan merusak dependency graph |
| `domains/customers/csv_import.py` + migrasi be2 | **Tidak di-port** | main memilikinya dalam `customers/services.py` + alur migrasi identitas (discovery→konflik→merge/keep_one/rename) yang lebih lengkap |
| `backend/infra/freeradius/*` (template statis) | **Tidak di-port** | main punya `render_radius_config` (management command) yang menghasilkan konfigurasi setara dari data nyata + sudah diverifikasi `freeradius -C` |
| Guard vite be2 (varian `enforce: 'pre'`) | **Tidak di-port** | main sudah punya gate setara (terverifikasi: build tanpa live DITOLAK sesi ini) |
| `docs/BETA_RELEASE_NOTES.md` | **Diarahkan ke dokumen kanonis baru** | Master prompt §14 minta `BETA_RELEASE_STATUS.md`; isi materialnya diserap ke sana + matriks kepatuhan |

### Verifikasi hasil integrasi (integration/beta-0.1)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (PG 17.11 nyata) | 0 | **222/222** = 207 main + 1 regresi scope-bersarang + 14 API-SSL |
| `python manage.py check` | 0 | tidak ada isu |
| `bash scripts/test_radius.sh` (fresh: grants dicabut dulu, hanya via `grant_runtime` baru) | 0 | **15/15 PASS** — jalur fresh-install RADIUS utuh tanpa intervensi manual |
| `tsc -b` / `eslint src` / `vitest run` | 0 | 0 error / 42/42 |
| `VITE_API_MODE=live vite build` / tanpa live | 0 / ≠0 | build live OK; build mock DITOLAK |
| `bash -n instalasi.sh` + `shellcheck -S error` | 0 | sintaks OK; 0 error shellcheck (warning minor pra-ada: var tak terpakai) |
| Dry-run installer di sandbox | ≠0 | **preflight menolak benar** (disk 8GB < 10GB minimum — gerbang bekerja) |
| `python3 docs/tools/check_docs.py` | 0 | PASS |

Lingkungan: Debian 13 sandbox; Python 3.13.5; PostgreSQL 17.11 (binary deb non-root + shim share-path); FreeRADIUS 3.2.7 + radclient (deb trixie, non-root); Node 24 + pnpm 12.16.1. **Tanpa perangkat MikroTik fisik / host root / domain publik** — bukti verified_lab tetap BLOCKED sesuai gate G1.

### Blocker / keterbatasan beta (jujur — tidak berubah dari BE-2 kecuali yang diperbaiki)

- Perangkat MikroTik fisik tidak tersedia → enrollment/discovery/cutover/API-SSL tetap jalur simulator pada default; T01/T10/T17 belum verified_lab.
- WireGuard host: installer kini menyiapkan keypair + wg0.conf + env; **aktifasi interface** (`systemctl enable --now wg-quick@wg0`) dan adopsi keypair oleh model `WireGuardHost` backend = langkah ops berikutnya (belum otomatis penuh).
- Instalasi produksi nyata (host Debian 13 + root + domain) belum dieksekusi — Gate A/G terbuka.
- B3/B4 cutover menunggu jendela observasi nyata dengan NAS produksi.
- Playwright e2e belum dibangun (smoke live sebagai pengganti terbatas).

### Langkah berikutnya

1. PR `integration/beta-0.1` → main (CI: backend/frontend/docs) → merge → tag `v0.1.0-beta.1` (RC).
2. Lab MikroTik CHR/fisik untuk G1 (T01/T16–T18/T20–T21) → baru aktifkan `MT_ROUTEROS_ADAPTER=api_ssl` dan cutover B3–B5.
3. Eksekusi instalasi.sh pada host Debian 13 root + domain (Gate A/G) — dokumentasikan hasil gate.
4. Adopsi keypair WG installer oleh backend + probe handshake.
5. M6/M7 billing/ledger R2 sesuai roadmap.

## Checkpoint BE-2 — Konsolidasi + M3/M4/M5 slice beta (audit → fix → integrasi → verifikasi nyata)

**Scope**: konsolidasi baseline BE-1/FE-1 (bukan rebuild): perbaikan bug nyata hasil audit, penutupan M4 (pelanggan/layanan/akun akses/CSV/migrasi DB-only), M5-ops (backup/monitoring/approval platform), M3 inti (enrollment WireGuard+API-SSL, discovery, cutover B0–B6, **FreeRADIUS NYATA dengan verifikasi radclient**), guard anti-mock frontend, hardening instalasi.sh, pengujian menyeluruh.

### Bug konsolidasi yang ditemukan & diperbaiki (bukti: sebelumnya gagal/jalan-setengah)

| Bug | Dampak | Perbaikan |
|---|---|---|
| `dev_bootstrap.sh` path `BACKEND="$ROOT/backend"` | Skrip dev gagal di langkah 5 | `BACKEND="$ROOT"` |
| `grant_runtime.py` %-formatting Python vs `%I` SQL | `ValueError` — command TIDAK PERNAH berjalan (instalasi.sh hanya di-dry-run; test DB dimiliki mtx_app sehingga tak tersentuh) | f-string + validasi identifier |
| Env test non-deterministik | `pytest tests/unit` gagal bergantung env shell (pytest-django memuat settings sebelum conftest; MT_SECRET_BOX_KEY terbeku kosong) | `microtix/settings_test.py` sebagai DJANGO_SETTINGS_MODULE pytest.ini |
| `instalasi.sh` build frontend tanpa `VITE_API_MODE=live` | **Deployment produksi akan membundle MOCK** (§5 dilanggar) | Guard build vite (gagal jelas) + runtime guard + installer set eksplisit |
| `instalasi.sh` Caddy `handle_path /api/*` | **Seluruh API produksi 404** (prefix dikupas; backend melayani /api/v1 penuh) | `handle /api/*` |
| `instalasi.sh` tanpa Node.js/pnpm/rsync | Build frontend pasti gagal di Debian 13 bersih | apt nodejs/npm + corepack pnpm@12.16.1 + rsync |
| `run()` memakai `eval` | Risiko shell-injection | Eksekusi langsung + run_sh majemuk |
| Signal `weak=True` (closure di `ready()`) | **Proyeksi RADIUS diam-diam mati** setelah GC closure — dibuktikan repro minimal lalu diperbaiki | `weak=False` |
| Scope bersarang `tenant_scope` saling me-reset GUC | Kegagalan RLS tak terduga di job handler | Konvensi caller-provides-scope konsisten |

### Status implementasi (per area)

| Area | Status | Catatan |
|---|---|---|
| M4 Pelanggan/layanan/akun akses | done | Customer/Service/AccessAccount (RADIUS §3: UNIQUE(tenant,username), secret_ref AEAD, credential_state jujur); CRUD + reveal (reauth + no-store); CSV create/link/validate/commit; migrasi: discovery→konflik identitas (merge/keep_one/rename)→commit DB-only (router TIDAK diubah); mode belum tersedia → 503 jujur |
| M5 Backup | done | job backup_router: commit-before-prune, retention per kategori, evidence {source:simulator, verified_lab:false}; router belum enroll → gagal jujur |
| M5 Monitoring | done | /monitor dari RouterHealthSample; unknown ≠ down; radius null tanpa data |
| M2 Approval platform | done | /platform/payment-submissions (platform_admin; 404 generik); approve atomik → invoice paid + subscription ACTIVE + source event immutable + audit/outbox |
| M3 Enrollment | done | Draft→token 256-bit hash-only (TTL 24 j; plaintext SecretBox, dibersihkan saat konsumsi)→skrip bootstrap idempoten TANPA reset/reboot, rule input sempit /32, token di BODY→bridge (replay identitas sama = logis sama; beda = 409)→job verify (simulator; capability jujur)→router read-only + peer WG |
| M3 Discovery | done | Snapshot+DiscoveryObject; password TIDAK dibaca; sesi migrasi tertaut |
| M3 RADIUS skema+facade | done | Skema `radius` + RLS + policy bootstrap; facade SECURITY DEFINER transaksi-local; authorize 5 kolom posisi rlm_sql; accounting idempoten + monotonik + late-Start tanpa reopen; session_count/list; post_auth |
| M3 RADIUS proyeksi+reconciler | done | Signal transaksi-sama; Auth-Type Reject saat suspend; rate hanya dari package pola sah; NAS secret CSPRNG + revision; clients.conf + modul sql via facade (%{Packet-Src-IP-Address}) + site; `freeradius -C` lulus |
| M3 Cutover B0–B6 | done | B0 preflight jujur (alasan spesifik); B1 parity sintetis; B2 install+readback; B3/B4 jendela observasi NYATA (pending_observation, tidak dipercepat); B5 authoritative; B6 rollback |
| M3 Release/replace | done | router_release (peer REMOVED + NAS deproyeksi; router fisik tidak disentuh) + router_replace |
| Guard frontend anti-mock | done | Build produksi tanpa live gagal jelas; runtime guard; installer set live |
| instalasi.sh hardening | done | Node/pnpm/rsync/wireguard-tools; FreeRADIUS fase-gated (MT_ENABLE_RADIUS=1) via reconciler; password psql via stdin; tolak non-Debian-13; gerbang wajib → INSTALL_FAILED exit≠0 / INSTALL_PARTIAL tanpa domain; upgrade = backup+verifikasi+frontend+Caddy; collectstatic; admin non-interaktif opsional |

### Verifikasi aktual (command + hasil)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (PostgreSQL 17 nyata) | 0 | **207/207 lulus** (72 BE-1 + 42 ops + 51 customers + 12 radius-config + 14 radius integration/contract + 16 enrollment dll.) |
| `bash scripts/test_radius.sh` (FreeRADIUS 3.2.7 NYATA + radclient + relay UDP) | 0 | **15/15 PASS**: T16 PAP valid→Accept+Mikrotik-Rate-Limit; salah password→Reject; restart→tetap Accept; secret salah→secure discard; radpostauth tanpa password. T19 username sama via NAS B→Accept data B; password A→Reject (isolasi). T20 suspended→Reject. T21 Start/Interim/Stop + counter monotonik + late-Start tanpa reopen + Simultaneous-Use=1 |
| `make test-radius` | 0 | harness sama |
| `tsc -b && eslint && vitest run` | 0 | 42/42; 0 error |
| `vite build` TANPA live | ≠0 | gagal jelas (guard anti-mock sesuai desain) |
| `VITE_API_MODE=live vite build` | 0 | bundle produksi live |
| `bash -n instalasi.sh` + dry-run 17 langkah | 0 | sintaks OK; preflight menolak disk<10GB; RADIUS jujur nonaktif tanpa flag |
| `python3 docs/tools/check_docs.py` | 0 | dokumentasi valid |

Lingkungan: Linux sandbox Debian 13; Python 3.13; PostgreSQL 17.4 nyata (peran mtx_migrator/mtx_app); FreeRADIUS 3.2.7 + radclient NYATA (binary deb trixie, non-root); Node 24 + pnpm 12.16.1. **Tanpa perangkat MikroTik fisik** — enrollment/discovery/cutover jalur simulator (capability: source=simulator, verified_lab=false).

### Keputusan engineering (reversible, dicatat)

1. Relay UDP harness (radclient tak bisa bind sumber) — resolusi tenant dari alamat sumber; decoy NAS-IP payload diabaikan (§4).
2. Kunci sesi accounting derivat host(NAS):Acct-Session-Id bila Acct-Unique-Session-Id absen.
3. rlm_sql 3.2: authorize 5 kolom posisi; accounting `type{}` + reference (tolower dari rlm_expr — modul expr ditambahkan); post-auth bersarang.
4. Policy bootstrap GUC konsisten: `facade_bootstrap` (radius.nas) + `enroll_bridge` (network_router_enrollment) — SELECT terbatas tanpa melemahkan RLS.
5. Token enrollment plaintext hanya SecretBox-terenkripsi selama TTL; dikosongkan saat konsumsi.
6. Konvensi caller-provides-scope ditegakkan semua handler/service.
7. `weak=False` wajib untuk receiver lokal di AppConfig.ready().
8. Respons 202 ketat {job_id, status_url}; ringkasan migrasi server-side (session.counts).

### Blocker / keterbatasan beta (jujur)

- Perangkat MikroTik fisik tidak tersedia → bukti simulator; T01/T10/T17 belum verified_lab.
- Interface WireGuard host tak bisa dibuat non-root → reconciler menulis konfigurasi; penerapan wg = langkah ops host (didokumentasikan), bukan klaim tunnel aktif.
- B3/B4 cutover menunggu jendela observasi NYATA — bukti penuh butuh NAS produksi.
- HTTPS produksi butuh MT_DOMAIN+DNS — tanpa itu INSTALL_PARTIAL (bukan beta publik).
- Gate A (instalasi produksi nyata Debian 13 + root) belum dapat dijalankan di sandbox.

### Langkah berikutnya

1. Lab MikroTik fisik/CHR: enrollment nyata, API-SSL pin, cutover B3–B5 penuh.
2. Penerapan WireGuard host via systemd + probe handshake.
3. M6/M7 billing/ledger R2 sesuai roadmap.
4. Playwright e2e (`make e2e`) — harness belum dibangun (NOT_RUN jujur).

## Checkpoint BE-2 — Konsolidasi beta: M3 inti (enrollment/RADIUS/proyeksi) + M4 fondasi + installer hardened (frontend live ditegakkan)

**Scope**: konsolidasi lanjutan dari BE-1 sesuai master prompt V4 — bukan rewrite. Menutup inti R1 yang memungkinkan alur beta nyata: enrollment router (TK-301/302), klien API-SSL native (TK-304), domain akses AAA + proyeksi radius.* + facade SQL multi-tenant (TK-306/307 sebagian), layanan pelanggan + CSV S2 (TK-405/404 subset), hardening instalasi.sh (§9), gate frontend live. Status rilis dinyatakan pada [BETA_RELEASE_NOTES.md](BETA_RELEASE_NOTES.md): **BETA_READY_WITH_LIMITATIONS**.

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bugfix grant_runtime | done | SQL lama memakai %-formatting Python di atas %I PostgreSQL → ValueError pada DB nyata (tidak pernah tereksekusi sebelumnya). Ditulis ulang: identifier tervalidasi regex + %%I ter-escape; kini mencakup skema public+radius; diverifikasi mtx_app mendapat SELECT/INSERT |
| tenant_scope reentrant | done | BUG SISTEMIK ditemukan tes: scope dalam reset GUC ke '' saat keluar → memutus konteks scope luar (view→service). Kini menyimpan+memulihkan nilai sebelumnya; tanpa scope luar tetap fail-closed. Semua 142 tes lulus |
| Enrollment router (TK-301/302) | done | Draft+issue: token 256-bit hanya hash+TTL 15 mnt; /32 reserved dari 100.127.0.0/16 via jalur GUC platform_service (UNIQUE global, alokasi lintas-tenant); bootstrap script bernamespace rtrw- idempoten (password API CSPRNG platform disuntik kanal rahasia §2.5; allowed-address hanya /32 server; TIDAK menyentuh konfigurasi pelanggan); probe endpoint mesin (token di body, bukan URL) → konsumsi atomik: Router read_only + credential_ref AEAD + NAS desired rev 1 + audit; replay nonce/identitas sama = logical; identitas beda = 409; produksi memverifikasi sumber IP tunnel (MT_ENROLL_VERIFY_SOURCE default on di production) |
| Skema radius.* + facade (TK-306) | done | Migrasi 0003: nas/radcheck/radreply/radusergroup/radgroupreply/radacct/radpostauth + RLS tenant identik + policy bootstrap (radius_svc) + facade SECURITY DEFINER (lookup_nas menetapkan GUC sempit lalu binding tenant; check/reply tetap RLS GUC; search_path terkualifikasi). Facade: NAS IP = SATU-SATUNYA pengikat tenant; NAS tak dikenal = secure discard |
| Proyeksi + resolver (RAD-02..05) | done | access_account sumber kebenaran (username case-sensitive 64chr/64B, secret_ref AEAD); project_account hapus+tulis ulang atomik; suspend → Auth-Type Reject TANPA Cleartext-Password; activate → atribut terkini; rotate_password satu transaksi; resolver murni: precedence override router > statis > pool, rate rx/tx bit/s, Expiration midnight lokal, eligibility (state/credential/validitas/kind/allowed routers) |
| NAS lifecycle + reconciler (TK-307) | done | ensure_nas/rotate (desired_revision naik; applied hanya setelah probe), radius_reconcile --dry-run/--apply (validasi freeradius -C; tanpa binary = BLOCKED jujur exit≠0)/--mark-applied (probe revision harus cocok desired) |
| Klien API-SSL (TK-304) | done | Protokol biner RouterOS lengkap (length-prefixed words, !re/!done/!trap), TLS + PINNING fingerprint SHA-256, bounded connect/read/word/response, koneksi hanya ke tunnel IP terdaftar (anti-SSRF), login modern; mutation/cutover/backup menolak jujur "pending_lab". 14 tes termasuk server TLS in-process (handshake nyata + pin mismatch ditolak) |
| Discovery (TK-401) | done-partial | Job router_discovery read-only via adapter aktif (simulator dev; api_ssl produksi): akun PPP/Hotspot TANPA password + snapshot fingerprint/summary; health probe job menulis sampel jujur (unreachable = sampel down, bukan job gagal). Wizard 8 langkah belum |
| Layanan + CSV (TK-405/404) | done-partial | POST /services: customer+service+akun AAA+kuota atomik (reservasi commit/release benar) + proyeksi sekaligus; reveal reauth-gated (tes 403 tanpa reauth); list/filter kursor; connection_state jujur unknown. CSV S2: validasi tanpa tulis + preview + commit job idempoten per baris (username existing skipped), batas 10k/10MiB |
| instalasi.sh hardened (§9) | done | Tanpa eval (array quoting); dependensi eksplisit + nodejs/pnpm/rsync/wireguard-tools; password psql via STDIN+escape; unsupported OS DITOLAK (bukan warning); WireGuard host keypair+wg0.conf+env pubkey; FreeRADIUS opsional MT_ENABLE_RADIUS=1; upgrade kini rebuild frontend+layanan+backup terverifikasi pg_restore --list; collectstatic; GATE NYATA: exit 2 INSTALL_FAILED / exit 3 INSTALL_PARTIAL (domain/TLS) / 0 SUCCESS — kegagalan health/worker/artefak/izin membuat installer GAGAL |
| Frontend live gate (§5) | done | Plugin vite menolak build produksi tanpa VITE_API_MODE=live (terverifikasi exit 1 vs 0); runtime juga menolak (belt & braces); adapter live telah mengimplementasikan seluruh ApiClient sejak BE-1 |
| i18n backend | done | Katalog enrollment.*/access.* id/en untuk error baru |

### Verifikasi aktual (command + hasil)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` | 0 | **142/142 lulus** = 96 lama + 46 baru: unit resolver (17), unit API-SSL (14, termasuk TLS in-process), integrasi proyeksi/facade/RLS radius (18), integrasi enrollment (11), integrasi services/CSV (7), kontrak M3 (16) |
| `bash scripts/smoke_live.sh` (baru; runserver+curl nyata) | 0 | **20/20 PASS**: health; register→verify; enrollment issued (token sekali) → bootstrap token-salah 401 → script rtrw- → probe consumed + replay logical → router terdaftar → NAS desired 1 → discovery job 202 → worker sukses (simulator, jujur bukan lab) → service+proyeksi → suspend/activate → CSV → tenant asing 404 |
| `tsc -b` / `eslint` / `vitest run` (web) | 0 | 0 error; 42/42 |
| `VITE_API_MODE= vite build` | 1 | DITOLAK oleh gate (bukti tidak ada fallback mock produksi) |
| `VITE_API_MODE=live vite build` | 0 | dist produksi |
| `bash -n instalasi.sh` + dry-run penuh + shim id | 0 | alur 17 langkah; preflight menolak disk 8GB<10GB (uji sungguhan); gate exit-code dipisah |
| `python3 docs/tools/check_docs.py` | 0 | PASS |

Lingkungan uji: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL **17.4 asli** (zonky tanpa root); Node v24 + pnpm 12.16.1. Tanpa host root/domain publik/MikroTik fisik/FreeRADIUS daemon — lihat blocker.

### Keputusan engineering (reversible, dicatat)

1. **Probe enrollment = endpoint mesin** (MachineTokenAuth tanpa CSRF): pemanggil router tanpa sesi; otorisasi = token sekali pakai + TTL + nonce + (produksi) sumber IP tunnel. CSRF tidak relevan tanpa cookie; kelas auth ini HANYA untuk endpoint token-gated ini.
2. **Facade NAS lookup via GUC sempit** (`app.radius_facade` + `app.platform_service`): row_security=off TIDAK dapat melewati FORCE RLS (bahkan owner). Kebijakan GUC = jalur baca bootstrap minimum; check/reply tetap di bawah RLS konteks tenant.
3. **tenant_scope reentrant dengan restore**: nilai sebelumnya disimpan dan dipulihkan; tanpa scope luar tetap fail-closed ''. Mengubah perilaku lama yang asumsinya tidak ada scope bersarang — diverifikasi seluruh suite.
4. **Password akun API-SSL dibangkitkan platform (CSPRNG) dan disuntik ke skrip bootstrap** — ROUTEROS.md §2.5 alternatif injeksi kanal rahasia; generator router tidak dipakai karena belum terbukti per build. Tersimpan credential_ref AEAD; pindah ke router saat complete.
5. **Cutover B0–B6 sengaja TIDAK dibangun** (gate G1; ACCEPTANCE §3) — router hasil enrollment selalu read_only; tidak ada tombol palsu.
6. **`radius_reconcile --apply` tanpa binary freeradius = CommandError BLOCKED** — bukan echo sukses.
7. **Alokasi /32 lintas tenant** membaca lewat GUC platform_service (kebijakan RLS terpisah) karena alokasi memang global; ditandai jelas di kebijakan.

### Blocker / dependency

- **Git push BLOCKED** — tidak ada kredensial GitHub di environment ini (tidak ada env GH_TOKEN/GITHUB_TOKEN, gh CLI, ~/.git-credentials, ~/.netrc, atau berkas di upload/). 6 commit lokal terstruktur siap push (2c09261..925aa14); push menunggu PAT fine-grained (Contents read/write, repo smahud/MicroTix_Project). Remote SHA BELUM terverifikasi — tidak ada klaim pushed.
- **FreeRADIUS daemon + host root + domain publik + MikroTik fisik tidak tersedia** — `make test-radius` jujur BLOCKED; instalasi produksi nyata belum dieksekusi; verified_lab = tidak ada klaim.
- **Playwright browser harness** belum dibangun (smoke live sebagai gantian; tetap todo).
- Wizard U07 8-langkah/identitas lintas router (TK-410), S1/S3/S4, monitoring berkala (TK-502/503), backup router (TK-504–507), PDF (TK-109), M2 billing penuh — belum (lihat BETA_RELEASE_NOTES §3).

### Langkah berikutnya

1. Push seluruh commit saat PAT tersedia; verifikasi remote SHA.
2. Eksekusi instalasi.sh pada host Debian 13 root + domain (Gate A/G nyata) — dokumentasikan hasil gate.
3. Lab FreeRADIUS (RAD-14 checklist) → setelah lulus: aktifkan MT_ENABLE_RADIUS=1, probe secret, mark-applied.
4. CHR/router fisik untuk G1 (T01, T16–T18, T20–T21) → baru pertimbangkan cutover B0–B6.
5. Lanjut M4: wizard 8 langkah + penggabungan identitas; monitoring collector.

## Checkpoint BE-1 — Backend M0 fondasi + M1 identitas/job/subscription (frontend mock → backend nyata)

**Scope**: backend/ dari nol sesuai `docs/ARCHITECTURE.md`; M0 (TK-002, TK-003, TK-004 sebagian simulator, TK-107) + M1 inti (TK-101, TK-102, TK-103, TK-105, TK-108, TK-104 live adapter). Endpoint fase M2+ sengaja tidak dibangun (anti API palsu, §5) — 404 envelope `not_found`.

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bootstrap backend (TK-002) | done | Python 3.13.5, Django 5.2.19, DRF 3.16.1, drf-spectacular 0.28.0, psycopg 3.2.13, argon2-cffi 25.1.0, cryptography 50.0.2, gunicorn 26.2.0 — semua patch-exact di `backend/pyproject.toml`; Makefile target standar; CI GitHub Actions; dev bootstrap `backend/scripts/dev_bootstrap.sh` |
| Skema fondasi (TK-003) | done | PK UUID; tenant-first index; FK komposit (tenant_id,parent)→(tenant_id,id) via RunSQL dengan reverse; UNIQUE(tenant_id,id) induk; ENABLE+FORCE RLS semua tabel tenant; event sumber pembayaran platform immutable (trigger); envelope job terpisah dari isi tenant |
| Simulator RouterOS (TK-004) | done | Deterministik + failure injection (unreachable/permission/timeout-after-send→uncertain/revision conflict/drift); discovery tidak pernah membaca password; hasil simulator tidak pernah klaim verified_lab |
| Registri konfigurasi (TK-107) | done | 114 parameter defaults.json dimuat typed; unknown/duplicate ditolak; bounds `approved_default_only` divalidasi; override env hanya bila bounds mengizinkan; release flag R1=true R2-R4=false; branding resolve + publication_blocked |
| Identitas (TK-101) | done | Argon2id min 12; TOTP RFC 6238 (vektor uji Appendix B lulus, anti-replay per step); 10 kode pemulihan HMAC pepper; login 2 tahap MFA via sesi pending 300s; reauth 600s batal saat tenant switch; rate limit 5/900s per akun+IP dengan pesan generik; register→verifikasi email (token hash)→tenant+Owner+subscription free; owner terakhir dilindungi |
| Isolasi tenant (TK-102) | done | RLS FORCE aktif (diverifikasi pg_class); konteks transaction-local `set_config(...,true)` + reset fail-closed saat keluar scope; runtime role bukan superuser/BYPASSRLS; non-milik→404 generik; audit redaction kunci sensitif; secret TOTP AEAD (kunci di luar DB) |
| Job engine (TK-103) | done | State machine §6 penuh (transisi sah divalidasi, terminal tak bisa diubah); claim FOR UPDATE SKIP LOCKED; lease 30s + fencing token/epoch; reconcile lease-expired→uncertain; uncertain→readback resolve; cancel hanya zero-effect; retry menautkan origin; outbox dedup key; worker `runworker`; kind tanpa handler ditolak (anti job palsu) |
| Subscription (TK-105) | done | PlanVersion 6 paket harga persis PRODUCT.md §3 (Free/BRZ/SLV/GLD/DMD/PLT + plafon operasional Platinum); reservasi atomik (entitlement lock SELECT FOR UPDATE, used=committed+pending, TTL 60m, expiry hanya yang terlewat); draft cap formula; quotation snapshot nilai/periode/locale/timezone; Idempotency-Key scope+body-hash, replay & 409 isi beda |
| i18n backend (TK-108) | done | Katalog id/en pesan mesin; /meta/enums?locale terautentikasi; Accept-Language q-weighted fallback id; label enum identik dengan mock FE |
| Storage/upload (TK-106) | done | Pipeline bukti bayar: base64 bounded, magic-bytes sniff (PNG/JPEG/WebP/PDF), klaim MIME wajib cocok isi, ukuran ≤5MiB, path opaque 0600, ClamAV fail-closed saat dikonfigurasi (dev `disabled` berlabel) |
| Live adapter FE (TK-104) | done | `apps/web/src/api/live/adapter.ts` mengimplementasikan seluruh ApiClient via http.ts; CSRF dari cookie mtx_csrf → header x-csrf-token; Idempotency-Key per aksi; pemilihan adapter `VITE_API_MODE=live` |
| instalasi.sh (§17) | done-partial | 17 langkah lengkap; mode install/status/doctor/upgrade/repair/--dry-run; secret CSPRNG; migrator terpisah; runtime NOBYPASSRLS no-CREATEDB; RADIUS fase M3 jujur; TIDAK menyentuh router pelanggan. Teruji: `bash -n` + dry-run penuh di sandbox (root dinetralkan untuk uji); instalasi produksi nyata BELUM dites (butuh host root) |
| Enrollment/discovery/cutover (M3) | not_started | Sesuai urutan IMPLEMENTATION_PLAN; registri router model fondasi sudah ada |
| Customers/services/migrasi CSV (M4) | not_started | Endpoint tidak dibangun — 404 jujur |
| Billing/ledger (M2) | not_started | Event sumber pembayaran platform immutable sudah disiapkan (TK-003) |
| TK-109 PDF | not_started | Belum dikerjakan (lihat langkah berikutnya) |

### Verifikasi aktual (command + hasil)

| Command | Exit | Hasil |
|---|---|---|
| `pytest tests -q` (backend, PostgreSQL 17.4 nyata via binary zonky; runtime role mtx_app) | 0 | **72/72 lulus** — 34 unit (TOTP RFC, kripto, state machine, simulator, registry, pagination, redaction, izin) + 30 integration (RLS fail-closed/konteks-salah/FK-komposit/bypass, auth end-to-end, MFA+anti-replay, rate-limit, reauth, owner-terakhir, job uncertain/lease/cancel/retry, idempotency, kuota atomik, upload MIME) + 8 contract (OpenAPI, envelope, health, enums, kursor) |
| `tsc -b --pretty false` (apps/web) | 0 | typecheck bersih termasuk adapter live baru |
| `eslint src --ext ts,tsx` | 0 | 0 error/0 warning |
| `vitest run` | 0 | 42/42 lulus (mock adapter tetap; tidak ada test dinonaktifkan) |
| `vite build` | 0 | dist produksi; vendor 164 kB (gzip 54 kB) |
| Smoke live (runserver + curl, skrip 16 asersi) | 0 | **16/16 PASS**: health live/ready; seed CSRF→login→session; POST tanpa CSRF→403; subscription/kuota free (draft_cap 13); 6 paket harga silver=1000000.00; jobs/routers kosong jujur; enums id; tenant asing→404; limit>200→422; register→verify-email→owner tenant baru |
| `python3 docs/tools/check_docs.py` | 0 | dokumentasi tetap valid |
| `bash -n instalasi.sh` + dry-run penuh | 0 | sintaks OK; alur 17 langkah terverifikasi dry-run; preflight menolak disk<10GB dengan benar |

Lingkungan uji: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL **17.4 asli** (binary zonky, tanpa root — bukan SQLite, bukan stub); Node v24.22.2 + pnpm 12.16.1. Tanpa perangkat MikroTik nyata — simulator deterministik saja (jujur: bukan verified_lab).

### Keputusan engineering (reversible, dicatat)

1. **PostgreSQL sandbox tanpa root**: binary PostgreSQL 17.4 (zonky embedded, mirror Aliyun) berjalan sebagai user biasa di 127.0.0.1:55432; peran `mtx_migrator` (pemilik skema) terpisah dari `mtx_app` (runtime, NOBYPASSRLS; CREATEDB hanya dev/test untuk pytest-django). Produksi: instalasi.sh membuat peran tanpa CREATEDN dengan password CSPRNG.
2. **CSRF ditegakkan di authentication DRF**, bukan middleware: DRF membungkus view dengan csrf_exempt sehingga middleware tidak berlaku; `SessionAuthentication` kami memeriksa CSRF untuk SEMUA unsafe method termasuk anonim (anti login-CSRF). SPA memperoleh token dari GET /auth/session (cookie mtx_csrf).
3. **Envelope job (global) vs JobDetail (RLS tenant)**: worker hanya melihat kolom operasional; payload/hasil bisnis dilindungi RLS; worker membuka tenant_scope per job eksplisit — bukan akses broad SELECT semua tenant (§4).
4. **`tenant_scope` reset GUC fail-closed saat keluar** (set_config ''): mencegah konteks bocor pada koneksi pooled/nes-transaction; teruji integrasi.
5. **Endpoint fase M2+ tidak dibangun** (services, migration wizard, CSV, backups, monitoring, RADIUS, platform admin) → 404 envelope. LiveApiClient meneruskan galat apa adanya — UI menampilkan status kosong/galat, bukan data palsu (§5 "jangan membangun API palsu untuk fitur masa depan").
6. **Draft wizard U07 di live mode** disimpan localStorage (berlabel) sampai backend M4 — pilihan sementara yang dicatat, bukan klaim fitur.
7. **TOTP diimplementasi sendiri** (RFC 6238, HMAC-SHA1, stdlib) + vektor uji resmi — tanpa dependensi baru; anti-replay per step.
8. **404 JSON via handler404** hanya untuk production (DEBUG off); dev memakai halaman teknis Django (standar) — diverifikasi di test suite kontrak.

### Blocker / dependency

- **Git push tidak tersedia** (tidak ada kredensial remote di sandbox) — commit lokal terstruktur dibuat; push menunggu akses.
- **Instalasi produksi nyata belum dites** (butuh host Debian 13 + root + domain); dry-run + sintaks terverifikasi.
- **FreeRADIUS/CHR/GNS3/WireGuard host tidak tersedia** di sandbox → `make test-radius` jujur exit 1 BLOCKED; kode M3 menunggu milestone-nya (bukan bloker M1).
- **Playwright e2e harness belum dibangun** (lanjutan dari FE-1) — `make e2e` jujur NOT_RUN.
- **imghdr dihapus dari Python 3.13** — upload memakai magic-bytes sniff sendiri (tanpa imghdr).

### Langkah berikutnya

1. M1 sisa: TK-109 (render PDF invoice/kwitansi), TK-106 signed-URL gateway download (TTL 300s), TK-104 lanjutan: sweep UI live browser (agent-browser) + perbaikan kecil state kosong.
2. M2 (TK-201–205): subscription approval atomik platform-side, renewal/grace, rekening tujuan snapshot.
3. M3 (TK-301–307, 408, 510): enrollment WireGuard/API-SSL pin, NAS reconciler, FreeRADIUS nyata di lab (butuh akses lab — kode+simulator tetap jalan tanpa itu).
4. Push ke remote ketika kredensial tersedia.

## Checkpoint FE-1 — Fondasi frontend R1 (documentation-first → aplikasi berjalan)

**Scope**: seluruh frontend R1 sesuai docs/UI_UX.md (U01–U08, U12–U14, U16, U18–U19) pada `apps/web`, tanpa perubahan backend/domain (belum ada backend — repository documentation-first).

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bootstrap `apps/web` (Vite+React18+TS+pnpm) | done | pnpm 12; deps: react-router-dom, @tanstack/react-query, react-intl (stack ARCHITECTURE.md §1) |
| Design tokens (tokens.css) | done | Warna/tipografi/spacing/radius persis UI_UX.md §2 |
| i18n FormatJS | done | `locales/{id,en}/web.json`, 908 kunci, paritas placeholder 100%; default `id`; pemilih bahasa cookie fungsional |
| Branding resolver | done | Placeholder dev berlabel; publication_blocked sesuai branding.json |
| Permission & release flags | done | Bundel peran ARCHITECTURE.md §3; flag R2–R4 off → menu disembunyikan |
| API boundary typed + mock adapter | done | Endpoint terdokumentasi §5 persis; PENDING_BACKEND ditandai di `client.ts`; banner "MODE PENGEMBANGAN" membedakan fixture dari produksi |
| 17 komponen wajib UI_UX.md §2 | done | AppShell, TenantSwitcher, PageHeader, FilterBar, DataTable, MobileServiceCard, StatusBadge, FreshnessLabel, JobProgress, BulkActionBar, ConfirmAction, FieldError, PermissionNotice, EmptyState, MetricCard, ChartWithTable, AuditTimeline |
| Halaman R1 | done | U01 landing, U02 login/register/verify/recover (+TOTP), U03 overview, U04 list+detail+tambah pelanggan, U05 enrollment 5 langkah, U06 detail router 7 tab, U07 wizard 8 langkah, U08 CSV, U12 backup, U13 monitoring, U14 admin (header navy), U16 job center+detail, U18 settings (tim/langganan/audit), U19 radius (akun/router/cutover B0–B6), plus halaman Paket dan Profile (kontrak TK-408 PENDING_BACKEND) |

### Verifikasi aktual (command + hasil)

| Command (dari `apps/web`) | Exit | Hasil |
|---|---|---|
| `tsc -b --pretty false` | 0 | typecheck bersih (strict, noUncheckedIndexedAccess) |
| `eslint src --ext ts,tsx` | 0 | 0 error/0 warning |
| `vitest run` | 0 | 42/42 test lulus (format, status tone, permission, katalog, adapter mock, badge a11y) |
| `python3 scripts/check_i18n.py` | 0 | 908 kunci; missing id=0, en=0, extra=0; paritas placeholder OK |
| `python3 scripts/check_contrast.py` | 0 | 13/13 pasangan warna ≥4,5:1 (WCAG 2.2 AA, diukur) |
| `vite build` | 0 | 2,6 MiB dist; vendor 164 kB (gzip 54 kB); code splitting per rute |
| `python3 docs/tools/check_docs.py` (akar repo) | 0 | dokumentasi tetap valid |

**Pengujian browser nyata (agent-browser + Chrome headless, dev server Vite)**:
- Login → TOTP → redirect `/app/{tenant}/overview`: PASS (diperbaiki: route `/app` redirect kini eksplisit).
- Tenant switch RT Net Nusantara → RW Net Cemara: PASS; menu per teknisi menyembunyikan Perusahaan dan Tim/Paket Aplikasi sesuai izin (diperbaiki: pola `queryClient.clear()` memutus observer; kini removeQueries selektif + setQueryData).
- Wizard tambah pelanggan → pilihan "Buat akun" → job dibuat → navigasi ke job detail → status berakhir "Succeeded — verified" via polling: PASS.
- Cutover RADIUS + dialog reauth (password+TOTP) → job radius_cutover_step: PASS.
- Drawer mobile 360px → navigasi Pelanggan: PASS; MobileServiceCard 6 kartu; kolom bayar/isolir R2 tersembunyi (diperbaiki agar sesuai fase).
- Sweep 20 halaman × 4 viewport (1440/1280/768/360): 0 horizontal overflow (diperbaiki: header flex-wrap + tenant switcher ringkas mobile, split-view admin 1 kolom <1024px).
- Keyboard: skip link adalah fokus pertama; Tab menelusuri nav; `:focus-visible` + focus ring terukur di DOM.
- VLM visual: overview/customers/radius/admin/monitoring PASS; ditemukan & diperbaiki: (1) `--mt-space-9` tak terdefinisi → ikon search menimpa placeholder (kini 38px); (2) `landing.css` tidak diimpor Landing.tsx → hero full-width (kini terkontrol 780px); (3) nomor `<ol>` stepper bertabrakan label (kini `list-style:none` + wrap); (4) step disabled terlalu pudar (digelapkan).

### Keputusan engineering (reversible, dicatat)

1. **Stack tepat sesuai ARCHITECTURE.md §1**: React+TS+Vite+pnpm+TanStack Query+FormatJS. Tambahan: react-router-dom (routing U01–U20 standar industri), vitest+@testing-library (pengujian §1). Tanpa UI framework eksternal — CSS token murni demi kontrol kontras/ukuran dan kepatuhan tanpa dependensi berlebih.
2. **Katalog di `locales/{id,en}/web.json`** (domain `web` per I18N.md §3) di luar root vite — alias `@locales` + `server.fs.allow`.
3. **Mock adapter in-browser** (default `VITE_API_MODE=mock`) mengimplementasikan `ApiClient` typed; endpoint terdokumentasi §5 mengikuti kontrak persis (202→job_id, error envelope, kursor); endpoint auth/list-router PENDING_BACKEND ditandai eksplisit. Banner dev permanen saat mode mock.
4. **Uang string desimal** (numeric 20,2) → format `Rp1.500.000`/`IDR 1,500,000` hanya di lapisan tampilan.
5. **Offline ≠ merah**: tone warning/netral sesuai UI_UX.md §2; StatusBadge selalu ikon+teks.
6. Grafik SVG ringan dengan gap tetap gap + tabel alternatif (tanpa library chart).

### Blocker / dependency

- ~~Backend belum ada~~ → **terjawab oleh checkpoint BE-1**: live adapter tersedia (`VITE_API_MODE=live`); halaman fase M2+ tetap menunggu endpoint fase aktifnya.
- Endpoint PENDING_BACKEND menunggu OpenAPI TK-408 (packages/bindings) dan skema auth/daftar router — auth kini terdefinisi BE-1 (lihat `/api/schema/`); daftar router live tersedia.
- Playwright E2E (`make e2e`): NOT_RUN — harness CI belum dibangun.
- verified_lab / release_enabled: tidak ada klaim.

## Lingkungan pengujian

- FE-1: Linux sandbox; Node v24.22.2; pnpm 12.16.1; Chrome headless via agent-browser; tanpa DB/router nyata (frontend-only scope).
- BE-1: Linux sandbox Debian 13; Python 3.13.5; PostgreSQL 17.4 (binary asli tanpa root); tanpa perangkat MikroTik/FreeRADIUS nyata — simulator deterministik; klaim verifikasi lab: tidak ada.
