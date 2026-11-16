# LATEST_HANDOFF — 16 November 2026: controller PR21 changes_requested, ID0010

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md),
CONTRACT §6A. Fetch remote refs/PR sebelum bertindak. Status ini berada pada
branch keputusan sampai integrasi; filename unfinished pada main tidak
membuktikan belum ada kandidat. Tanggal Asia/Jakarta; evidence filename UTC.

## Latest state verification — 16 November 2026, 13:50 WIB

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

## 0. Task aktif dan exact next action

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
| Active task | [0010 / PA-006](../task/0010-pa006-idempotency.md), ID sama dibuka kembali unfinished |
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
