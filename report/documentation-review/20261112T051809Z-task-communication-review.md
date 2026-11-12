# Independent review — controller/executor communication loop

Author: Codex documentation/security reviewer (`/root/security_jobs_review`). Date: 12 November 2026. Starting branch: `docs/task-communication-loop-20261112`; base HEAD `a0f653e89bf77b1238ca0ed9bcdb0e2f0aee612e`. Worktree: `/workspace/scratch/9459f0c7494a/task-communication-loop-20261112`.

Scope: bounded read-only assessment of the existing repository task workflow and the controller's documentation-only communication additions. No PA-006 implementation, task 0020 creation, application configuration/source changes or deployment work is authorized by this review. Parent supplied current remote main/PR/CI observations; this reviewer verifies the local draft and reports those remote observations only as parent-provided context.

**Final verdict: APPROVED for the reviewed documentation-only communication clarification.** All five baseline communication gaps below are addressed by the in-place additions. No remaining blocker identified in this bounded scope. Publication, required CI and any documentation integration remain the controller's responsibility; PA-006 implementation remains ready/not_submitted and unreviewed.

## Baseline gap assessment

The repository already has a workable core: CONTRACT §6A assigns controller/executor roles, permanent guide and numbered task identity, exact-SHA review, evidence/report requirements, `_done` as executor delivery, same-ID correction and separate merge/deployment authority. `task/0010-pa006-idempotency.md` is ready/not_submitted and has acceptance, scope limits, report location and no implementation SHA. A second task should not be invented to bypass the unavailable PA-006 result. GitHub files and PRs can persist the loop; no new orchestration framework is needed.

The minimal missing communication details observed before drafting were:

1. **Executor evidence mapping is implicit.** CONTRACT §10 and task 0010 ask for reports/test evidence but do not prescribe a compact acceptance assertion → actual command/environment/effect evidence → outcome/NOT_RUN mapping. Without this, a report may list green commands without demonstrating each required invariant.
2. **Controller's return message is underspecified.** Review ownership/exact SHA exists, but the required persisted verdict, finding → required correction/acceptance mapping and explicit next actor/action are not yet spelled out. A chat-only verdict can be lost at the external agent boundary.
3. **Main's task status is not sufficient work-claim evidence.** Guide asks to inspect PRs and avoid repeating pending review; it does not explicitly require following the task ID's result/candidate/report on an unmerged branch before treating a ready file on main as unclaimed. Work can be published while main legitimately still shows ready.
4. **Handoff publication checkpoints need an explicit role boundary.** Task/report/review pointers should resolve to an observed published ref/SHA/PR before the next role uses them. Instructions drafted locally, a code candidate, a tested ancestor, and a controller verdict are distinct artifacts; file metadata must not imply they already exist remotely.
5. **Current status needs refreshing.** Baseline latest handoff retained pre-PR10 main and instruction-publication snapshots. Historical reports should stay intact, while current handoff should name the latest observed main/instruction state and say the next actor is the coding executor on task 0010, because no PA-006 candidate has been published in the parent's checked remote scope.

These are document-level communication gaps, not evidence that GitHub cannot support the human/agent handoff. Existing tests or green main CI do not demonstrate that PA-006 was executed. A task file does not launch an external agent or run a background scheduler.

## Minimal review criteria for the additions

- Keep instructions/status/pointers in the task and guide, detailed evidence in executor reports, controller decisions/corrections in controller reports and current navigation/next actor in latest handoff. Link these artifacts; do not copy the full backlog, audit or reports into each file.
- Executor delivery identifies task ID, original instructions/baseline, implementation/tested SHA, actual published candidate/PR, acceptance evidence and remaining work. Do not demand a report embed its own future commit SHA.
- Controller review identifies the exact reviewed candidate, outcome and findings, expected correction/acceptance, report publication and next actor. Changes requested reopen the same ID; accepted applies to that source candidate, with relevant revalidation after changes.
- Read the currently published instruction/task and active PR/result/review refs together. Reconcile stale/conflicting pointers before dependent work; do not treat lack of an updated main filename as proof no one has worked on the task. Preserve other work and branch ownership.
- Publish and verify the necessary handoff artifacts before the other role relies on them. Controller alone prepares the next dependent task once prerequisites are satisfied. No automatic merge, deployment, feature activation, new queue/daemon/framework or premature task 0020.
- Keep PA-006 implementation acceptance intact, including eventual replay of the same action/result; communication edits must not soften the prior correction.

## Checks and limitations

Executed before draft additions: `git rev-parse HEAD` matched the supplied base; `git status --short` was clean; direct reads of CONTRACT §6A, task 0000, task 0010, latest handoff and the prior workflow decision/publication report, with targeted `rg` for report/review/pointer fields. These source reads substantiate the baseline gap assessment; no test or remote task execution was inferred.

**NOT_RUN:** PA-006/backend/frontend/application tests, dependencies, DB/HTTP concurrency, migrations, jobs, installer, recovery or device integration; production/network probing; GitHub API/CI or publication. No additional agent delegation. No task/contract/handoff/source/configuration edits by this reviewer. **NO_COMMIT / NO_PUSH**. The only authored file is this review report, per CONTRACT §10.

## Draft recheck and final verdict

After the controller's draft-ready message, directly reread the full draft diff for CONTRACT §6A, task 0000, task 0010, MASTER_PROMPT, AGENT_HANDOFF, latest handoff and progress, plus the new controller decision report. Base HEAD remains `a0f653e89bf77b1238ca0ed9bcdb0e2f0aee612e`; review covers the working-tree documentation draft rather than a future immutable publication SHA.

| Baseline gap | Closure in reviewed draft |
|---|---|
| Acceptance evidence mapping | Guide §6 now requires every mandatory acceptance to map to actual PASS/FAIL/NOT_RUN/BLOCKED, command/environment/exit and assertion/evidence; task0010 repeats the bounded delivery obligation and links the full report instead of duplicating it. |
| Persisted controller verdict/corrections | CONTRACT §6A and guide §6 require a separate report tied to exact candidate/reviewed SHA, evidence limits, finding IDs/minimal correction/closure acceptance and next actor/action; task0010 names the controller report location and same-ID correction loop. Internal executor review is explicitly not controller acceptance. |
| Main-ready versus unmerged results | Startup explicitly searches task ID in current files, published candidate branches, PRs and reports; candidate results can exist before main integration and are not overwritten/reimplemented just because main's file still says ready. |
| Publication and role boundaries | Each role publishes and verifies its report/task pointers before handover/dependent work; explicit refs are required for unmerged records, and chat/PR comments may point to but cannot replace the versioned record. Next dependent task is prepared only by controller when prerequisites are satisfied. |
| Current status/next actor | Latest handoff records observed main/PR10 integration and an active task table with absent execution candidate/report/review, coding_agent and one concrete next action. Task0010 truthfully retains ready/not_submitted, no implementation/tested SHA, no false `_done`; no task0020 was created. Historical reports remain intact. |

Additional checks actually executed on the ready draft:

- Read-only Markdown file-target check across seven reviewed documents: **40 local links checked, zero missing targets**, zero inbound links to renameable task packets. Path check does not validate heading anchors or rendered layout.
- Task guide/packet HTTP(S) URL count: **zero**. Direct text review found no actual deployment access values/credentials.
- Compared task0010's complete mandatory-work, acceptance and verification sections to base HEAD using `git show` and exact string comparison: **unchanged**. The prior eventual same-action/result replay requirement is retained; this change only adds communication metadata/delivery clarity.
- `git diff --check`: **exit 0**. Targeted diff inventory for `backend`, `apps`, `instalasi.sh`, Makefile, `.github` and locales: **empty**. General status/diff shows only authorized documentation/manifest/report/task changes.
- Parent reported the canonical docs validator PASS (22 files/78 links) after manifest refresh; this is attributed controller evidence, not a command run by this reviewer. No product bug is inferred from the planned/refreshed manifest.

**APPROVED**, with no further correction request. No new template, queue, schema, communication service, code implementation, premature dependent task or deployment claim was introduced. The files specify a persistent handoff protocol and do not claim to launch the external coding agent. Final publication/required CI must bind the delivered revision to the reviewed documentation draft. This verdict neither accepts an absent PA-006 implementation nor grants application merge/deployment authority.

The reviewer still authored only this report. **NO_COMMIT / NO_PUSH**; application tests and all previously listed runtime/production operations remain NOT_RUN.
