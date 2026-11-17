# Independent resume review — task0020, 17 November 2026

## Scope and starting revision

Author: OpenAI Codex `/root/verify_0020_resume`, independent reviewer delegated
by the controller under CONTRACT §5. Objective: verify current submission,
instruction and dependency state without repeating runtime review of unchanged
source. Review observed GitHub at **2026-11-17 ~14:47Z / 21:47 WIB**.

Shared checkout: local `review-0020-resume`, starting at decision
`43043be4b0562f982316593cf6ef4e5d5b6951a6`; no branch/ref mutations,
application changes, commit, push, merge or external network actions by this
reviewer. Only this report was written. Parent owns integration/publication.

Applicable instructions read: AGENTS.md, CONTRACT §§5–6A/10–13,
task/0000-start-here.md, docs/MASTER_PROMPT_REVIEWER.md,
report/LATEST_HANDOFF.md, task/0020-job-lifecycle-authority_done.md and controller R1
`report/controller/20261117T134100Z-0020-job-lifecycle-review.md`.
Requirements remain those in the existing packet, including J20-A01–A09;
this state review introduces no normative requirement or new finding ID.

## Observed state and checks

| Check | Actual result and evidence boundary |
|---|---|
| GitHub branch inventory | REST `branches?per_page=100`: **31 branches**, main **41d1f33f16508491a34f66b767830b9dd3e5954e**, candidate branch **bd37c14e6c41339a8743b3d4b723ee74f13bef08**, decision branch **43043be4b0562f982316593cf6ef4e5d5b6951a6**. No new correction branch. |
| Open PR inventory | REST `pulls?state=open&per_page=100`: **14 PRs**. PR26 instruction ea7b8a1; PR27 first implementation bd37c14; PR28 report-only state check8204ba0; PR29 controller decision43043be. PR29 still targets PR27 branch. No correction submission identified. |
| Task/report inventory across refs | `git for-each-ref refs/remotes/origin` followed by `git ls-tree -r --name-only <ref> task/ report/controller/ report/orchestrator/` on each of the31 branch refs (origin/HEAD excluded from branch count): only task IDs0000/0010/0020. No task0030 or newer executor correction report. Candidate has0020_done; decision correctly reopens0020 unfinished. Main lacks0020 and cannot replace current decision instructions. |
| Tested ancestry | `git merge-base --is-ancestor 7118cce0db330acb02be0b3b774b1b1628d55d7a bd37c14e6c41339a8743b3d4b723ee74f13bef08` and candidate→decision43043be both exit0. |
| Tested→published delta | `git diff --name-only 7118cce bd37c14`: four task/report paths only. Application/test/config source unchanged. |
| Candidate→decision delta | `git diff --name-only bd37c14 43043be`: only `task/`, `report/` and `docs/progress.md`; no application/config source change. Retained reproduction Python under report is evidence, not a backend implementation change. Explicit `git diff --exit-code ... -- backend/ apps/ .github/ instalasi.sh deployment/ locales/` exits0 for both revision pairs. |
| Candidate exact-head CI | REST `commits/bd37c14e6c41339a8743b3d4b723ee74f13bef08/check-runs?per_page=100`: backend/frontend/docs **completed/success3/3**, each head SHA matches candidate. Existing CI, not new runtime verification. |
| Decision exact-head CI | Same endpoint for **43043be4b0562f982316593cf6ef4e5d5b6951a6**: backend/frontend/docs **completed/success3/3**. This updates PR29's earlier in-progress observation; it does not close acceptance failures. |

All local inventory/delta/ancestry commands completed exit0. GitHub REST
reads completed successfully. Remote observed branch SHAs agree with the
fresh clone's matching refs. Root must recheck relevant refs before publishing
because this is an observation at the stated time, not a lock on later work.

## Decision, evidence limits and next actor

**Concur: task0020 remains `ready / changes_requested`; correction delivery
is `not_submitted` at this observation.** These are distinct: a first
implementation exists and has been reviewed; no replacement implementing
R1 corrections is yet published. PR28's earlier pending-review text is a
historical observation superseded by PR29, not evidence that R1 is absent.

Keep **REV-1711-01–08** (eight confirmed defects) and **REV-1711-09**
(mandatory-evidence gap) open as controller R1 recorded. Prior root runtime
evidence **554 passed,1 skipped,3 warnings** plus **11 failed acceptance
assertions/0 final harness errors** is attributed to R1, not rerun or newly
established by this reviewer. Source is unchanged, so no new implementation
verdict or acceptance is warranted. No finding closure is inferred from
green ordinary CI. No new inconsistency requires a product decision.

Task0010/PA-006 remains accepted/integrated. Task0030/dependent work cannot
be unlocked before0020 review and integration prerequisites are satisfied.
PR7/8/14 and all unrelated/historical refs remain preserved. Production Beta
is **NOT_READY**. PostgreSQL probes/full backend/frontend tests, OS installation,
upgrade/restore, real drain/systemd, RouterOS/CHR/GNS3, live RADIUS, browser E2E
and benchmark are **NOT_RUN by this reviewer**.

Next actor **coding_agent**: fetch `review/0020-controller-20261117` current
head, close REV-1711-01–09 on **the same task0020** using packet/R1 closure
assertions, preserve PA-001/PA-006 and submit new exact implementation/tested
SHA, execution evidence and CI for controller review. Do not restart from
stale main or request another copy of the first submission.

Completion: independent state/prerequisite review complete; report **NOT
PUSHED by this reviewer**, delegated to parent for versioned publication on
the existing decision ref. No acceptance, merge, deployment, activation or
release authority is created by this report.
