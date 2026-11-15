# Controller checkpoint — task0010 / PA-006, correction submission check

**Existing verdict remains `changes_requested` on PR19 exact SHA
`9e9bf2d42002a00a69d54fc355b77384897b9478`.** No fourth/corrected
implementation submission was found in the observed remote refs/PRs.
Task0010 stays **ready / changes_requested**; correction delivery is
**not_submitted**. Next actor **coding_agent**. Production Beta **NOT_READY**.

## Identity, authority and baseline

- Author/role: ChatGPT Work controller `/root`, executing the owner's
  request to run `docs/MASTER_PROMPT_REVIEWER.md`. Session date
  **15 November 2026, Asia/Jakarta**; evidence filenames use UTC.
- Starting local checkout: clean main
  `9903d9b0cf09d737b553da3c21067b4810e956c0`, one worktree, no prior local
  changes. Fetched remote refs; isolated local branch
  `review/0010-pa006-controller-check-20261115` starts at the current
  instruction/decision ref below. No existing remote branch was replaced.
- Canonical main remains **9903d9b0cf09d737b553da3c21067b4810e956c0**.
- Candidate: [PR19](https://github.com/smahud/MicroTix_Project/pull/19),
  `session/2026-11-15-pa006-idempotency` at **9e9bf2d42002a00a69d54fc355b77384897b9478**.
- Latest instruction/decision: [PR20](https://github.com/smahud/MicroTix_Project/pull/20),
  `review/0010-pa006-controller-20261115`, observed starting head
  **2f2416b3ebda64bf45d6f305c153ac0418db3b0c**; this session appends
  records to that existing controller PR, without a new task or PR.
- Tested source ancestor named by the prior review:
  **c99838cd6e9f144adf53bb44ed792fba15a432fe**. Both ancestry segments
  ancestor→PR19 and PR19→decision head have empty protected application,
  config, installer, CONTRACT and manifest deltas. This is a submission
  checkpoint, not a claim of new runtime review or acceptance.
- Read AGENTS, CONTRACT, permanent task guide, default reviewer prompt,
  task0010 including acceptance/corrections, current and submitted
  handoffs/progress, prior controller decision, linked evidence and
  relevant current source. CONTRACT §§5/6A/10–13 govern delegation,
  reporting, review and delivery; application code remains read-only.

## What was verified this session

| Check | Actual result / evidence |
|---|---|
| GitHub remote inventory | **22 branches, 10 open PRs**; PR19 candidate and PR20 decision unchanged. [Snapshot](../controller-evidence/20261115T005847Z-pa006-resubmission/remote-snapshot.json). |
| Task identity and ancestry | Current packet is task0010; main's old ready pointer and candidate's historical `_done` do not supersede PR20 correction decision. Task files inspected on all remote tips; symbolic origin/HEAD excluded from branch count. [Ref/source check](../controller-evidence/20261115T005847Z-pa006-resubmission/ref-source-checks.json). |
| Source/config identity | `git merge-base --is-ancestor` and protected `git diff --exit-code` exit0 on both segments; critical file SHA256 recorded. No unreviewed application changes found after the existing decision. |
| Candidate CI | Run [43618187731](https://github.com/smahud/MicroTix_Project/actions/runs/43618187731), exact PR19 SHA, completed/success; backend/frontend/docs each success. Independently retrieved existing CI, not rerun local tests. |
| Starting decision CI | Run [43644712277](https://github.com/smahud/MicroTix_Project/actions/runs/43644712277), exact starting PR20 SHA, completed/success; all three jobs success. [Job readback](../controller-evidence/20261115T005847Z-pa006-resubmission/existing-ci-jobs.json). |
| Documentation validator | `python3 docs/tools/check_docs.py` exit0, **PASS24 files /106 internal links**, static-only; zero runtime tests. [Source/docs output](../controller-evidence/20261115T005847Z-pa006-resubmission/source-and-docs.log). |
| Independent review | Delegated `/root/verify_resubmission`, read-only on source and disjoint report ownership; [independent record](../reviewer/20261115T005900Z-0010-resubmission-independent.md). Root reconciles its result before publication. |
| Final record QA | Independent reviewer **APPROVED**; root scope/link/secret-pattern/diff checks PASS, entire packet body below metadata byte-identical to starting decision. [Validation](../controller-evidence/20261115T005847Z-pa006-resubmission/record-checks.json). |

All counts refer to the recorded discovery snapshot, before this session's
records commit. Remote refs and publication are checked again before handoff.

## Finding disposition and acceptance

No new findings or closure claims are created. The [previous exact-SHA
controller decision](20261114T212816Z-0010-pa006-review.md) remains the
implementation review and owns the detailed reproduction, acceptance and
correction requirements. Current source still contains the reported paths;
content identity proves no correction has been published on the designated
candidate/decision refs.

| Finding | Disposition retained | Current source / existing evidence |
|---|---|---|
| REV-1311-01 P1 | **OPEN, partial** | `jobs/migrations/0004_idempotency_identity.py:104–108,151–152` still treats colon-containing URN scope as malformed and deletes its guard. Previous actual-source HTTP upgrade probes show submission/file1→2; not rerun this session. |
| REV-1311-03 P2 | **OPEN, partial** | `billing/views.py:429–432` still lacks nested allocation UUID declaration; `customers/services.py:663,749` still uses raw selected-ID sets. Previous nested UUID conflict and selected preview/payload failures remain uncorrected. |
| REV-1511-05 P1 | **OPEN, pre-existing path** | `customers/services.py:413` still includes raw CSV rows in preview; prior evidence proves plaintext in persisted/replayed response. No credential values were read into or added to session reports. |
| REV-1311-02 | **CLOSED on reviewed SHA** | Parent+group/current validation fix retained; do not reimplement it. |
| REV-1411-04 | **CLOSED on reviewed SHA** | Authenticated HTTP, after-write rollback/takeover and prior query/blocker supplement retained. |

Acceptance disposition therefore stays PARTIAL/FAIL for legacy URN upgrade,
nested/selected UUID identity and safe secret-free replay, as recorded in
the prior decision. Passing principal/platform/atomic-claim/group-parent
behavior and PA-001 are preserved. Green CI does not resolve the failing
acceptance probes. Historical root results **67 targeted /426 full /6 prior
probes passed** belong to the previous session; they are not new tests here.

NOT_RUN this session: application/PostgreSQL runtime tests, migrations,
frontend local tests, browser E2E, host install/upgrade/restore, lab
GNS3/CHR/router/RADIUS, deployment, DR and capacity benchmark. No source
delta warrants repeating the completed application audit; the owner needs
a corrected executor candidate before another implementation review.

## Changes, decisions and next action

Changes are append-only session reports/evidence and a small pointer
checkpoint in task0010, LATEST_HANDOFF and progress. Original packet
objective, mandatory work, acceptance and verification blocks remain
byte-identical. No application/schema/config/dependency/installer/CI,
CONTRACT/manifest or product requirements are changed. Security and
compatibility requirements remain those of the existing correction packet.

Next actor **coding_agent**: fetch
`review/0010-pa006-controller-20261115` and PR19, preserve closed fixes and
history, correct **REV-1311-01/03 and REV-1511-05** on **task0010**, supply
finding→change→failing-before/passing-after closing test→actual evidence,
then publish a new exact candidate SHA with required regressions and CI.
Existing acceptance and scope are sufficient; do not create another packet.

PA-002/003 remain dependent and ineligible; DEC-01/02 and other Beta blockers
remain unchanged. No merge, release tag, deployment, feature activation or
external coding-agent start is performed. Repository records provide the
handoff; they do not start an executor automatically.

Publication at authoring: **NOT PUSHED**. The controller will append this
checkpoint to existing PR20 using a fast-forward update with the observed
head as lease, then verify remote tree/content and exact-head CI. A later
publication record may cite an already-existing commit; no future self-SHA
is invented.

## Publication verified — existing PR20

Initial checkpoint commit **25f96a6f7a56f427e26ee3f77e67727fef5d5c7b**
is **PUBLISHED** on `review/0010-pa006-controller-20261115` in existing
[PR20](https://github.com/smahud/MicroTix_Project/pull/20), whose base stays
the reviewed PR19 branch at9e9bf2d. Remote tree
**27500dba43144b9dad6287c25d3f5d5f2b61ddec** exactly matches the validated
local index. Connector commit/ref/report readback, local fetch and clean
detached checkout confirm publication. The update fast-forwarded from
2f2416b with an expected-head lease; no force push or new PR was used.

Exact-head initial checkpoint CI
[43661329292](https://github.com/smahud/MicroTix_Project/actions/runs/43661329292)
completed **success**. This is GitHub CI for a records-only descendant;
it does not close the application findings or represent newly run local
PostgreSQL acceptance probes. Final metadata records this already verified
publication and is checked again through PR20 before handoff.

Session publication changes ten files at the initial commit: three existing
pointer/checkpoint files, two new reviewer/controller reports and five new
evidence files. The final publication record only appends existing facts.
Protected delta stays empty; main9903d9b and input PR19@9e9bf2d unchanged.
Task0010 remains ready/changes_requested; coding_agent is the next actor.
