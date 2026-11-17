# Controller review — integrated PA-006 and next task0020

**Result: PA-006 remains done / accepted / integrated; task0020 PA-002 + PA-003 is ready / not_submitted. Production Beta NOT_READY.**

Controller: ChatGPT Work `/root`. User-facing date: **17 November 2026 (Asia/Jakarta)**; evidence filenames use UTC. Session started from remote `main@41d1f33f16508491a34f66b767830b9dd3e5954e`, tree `9036b3e4ce473df39d569eabb11c813b14956bb2`. Instruction: user explicitly requested execution of [default reviewer prompt](../../docs/MASTER_PROMPT_REVIEWER.md), following [AGENTS](../../AGENTS.md), [CONTRACT](../../CONTRACT.md), [start guide](../../task/0000-start-here.md), packet/handoff/progress.

This is a continuity/dependency review plus a scoped executor assignment. There is **no new PA-002/PA-003 implementation candidate to accept or reject**. No application fix, merge, deployment, feature activation or release was performed. Root could read and write GitHub via the connected app; a shell call returned `No usable execution environment is available`. Local worktrees/uncommitted work, local Python/PG/process execution and local clone verification were unavailable, not silently assumed clean.

## 1. Actual remote state and prerequisite

Root fetched the main ref, complete recursive tree (not truncated), all27 branches and10 open PRs. There is only task0000 + task0010_done on baseline; no packet0020, implementation branch or designated pending-review submission for that ID was found in current refs/PRs/reports. Open PR7/8/14 and earlier PA-006 submissions/reviews remain preserved. Historical PA-006 PRs left open are not new candidates requiring a sixth submission.

| Evidence | Actual observed result |
|---|---|
| Main | `41d1f33f16508491a34f66b767830b9dd3e5954e`, parent022e9d0; remote integration-record descendant |
| Accepted predecessor | R5 [controller decision](20261116T101809Z-0010-pa006-r5-review.md), exact `a301a94c2b3268679065e85bbef66f35949483f7` |
| PR24 | closed+merged, exact head a301a94; merge `532862be2711f26d537ae1df540258bbdcae2052`,2026-11-16T11:17:20Z |
| PR25 | closed+merged, head `c352bce4e3f4cfe87ae62ee23e3c1e2a4cfbb450`; merge `fd0f3faa84ea87c142d37da5dacf01e22a493f90`,11:17:44Z |
| Decision head→current main | GitHub comparison c352bce…41d1f33:17 changed paths, all integration records/task/progress/handoff/evidence. **Application/config/test delta empty.** Acceptance remains attached to a301a94; this session does not manufacture a new runtime acceptance |
| Exact current-main CI | [43857508367](https://github.com/smahud/MicroTix_Project/actions/runs/43857508367): backend/frontend/docs all completed success3/3 on41d1f33 |
| Draft authority | PR8 still open draft6bb57c9; docs/planning_audit is absent from main. Packet0020 derives requirements from main PRODUCT/ARCHITECTURE/ACCEPTANCE/OPERATIONS, without adopting draft policy |

[Remote state evidence](../controller-evidence/20261116T231131Z-0020-discovery/remote-state.json) records SHAs, refs, PRs, compare paths and check URLs. Integrator's [report](../orchestrator/20261116T111835Z-0010-pa006-integration.md) and R5 decision are preserved. Their historical claims of actual PG/schema/FreeRADIUS testing remain attributed to their authors; root did not rerun those commands.

## 2. Current source findings and minimum authorized correction

Root inspected jobs engine/models/views/worker, tenant context/permissions/current identity, active customers/network/radius/backup handlers and enqueue origins, existing job tests, relevant PA-006 tests and owning main docs. Independent reviewers traced the same boundary from immutable baseline. These are **confirmed source patterns with concrete failure paths**, not new runtime exploit/race reproductions. Existing REV-1111-06 remains open; packet0020 closes its worker scope plus the directly coupled PA-003 authority boundary.

| Stable finding | Current baseline evidence / risk | Packet closure |
|---|---|---|
| JS-0020-01 P1 | engine.py:227–278 wraps handler I/O in tenant_scope; tenant_context.py:51 opens atomic transaction. Updates/locks/heartbeat remain uncommitted through network operations | A02, A05: short DB units, observer visibility and no DB transaction/lock across I/O |
| JS-0020-02 P1 | engine.py:213,270–271,288,311 write transition/detail/outcome/retry without current token+epoch+expected-state guards; _fenced_save false return ignored:247 | A01: every affected write and domain commit guarded; stale ownership loss stops effects |
| JS-0020-03 P1 | engine.py:245–247 records maybe only after execute; cancel:375–379 accepts executing/none without no-outstanding-send proof | A03: atomic zero-effect cancellation, explicit writer/send fencing |
| JS-0020-04 P1 | engine.py:337–353 reconciles executing/verifying only, then updates by id after snapshot; misses claimed/preflight crashes and races with renewal/completion | A05: state/effect-aware crash recovery and conditional reconciliation |
| JS-0020-05 P1 | engine.py:383–399 and jobs/views.py:75–77 allow uncertain retry into new queued job without readback/old-writer proof | A04: applied/not-applied/unknown readback, safe retry identity and no duplicate effects |
| JS-0020-06 P1 | claim_next:161–191 locks a job only; no shared per-router sender ownership at active handler boundary | A03: serialize conflicting senders and preserve independence of different routers |
| JS-0020-07 P1 | runworker.py:32–49 has no signal/drain; engine deadline_at is not checked, heartbeat only before execute/verify | A05/A08: bounded deadlines/renewal, real-process drain/kill recovery |
| JS-0020-08 P1 | engine.run_claimed:224–247 and current handler preflight omit fresh user/membership/operation/router/policy authority checks | A06: authoritative current checks at effect boundary; legacy and narrow system origin policy |
| JS-0020-09 P1 | jobs/views.py:61–97 uses membership-only ActiveTenantApiView (common/views.py:129–147); underlying detail/retry/cancel privilege absent. network/views.py:200–214 replacement uses enroll though it releases old router | A07: resource-specific permission/router scope/sensitive proof, replacement release authority,403/404 |
| JS-0020-10 P2 | handler None skips work then succeeds; verifier result is not evaluated before succeeded:255–278; network verifiers may return ok:false | A07: explicit active-handler verifier success contract, missing/negative fail-closed |
| REV-1611-TEST-01 P3 | Existing accepted R5 nonblocking thread-completion note, test_idempotency_pa006_r5.py:398–408 | A09: test-only completion/results assertions; **PA-006 stays closed** |

No generic framework is prescribed. Jobs remain on the existing PostgreSQL engine; effects remain domain-owned. Trusted global job envelope is intentional; RLS tenant detail must remain separate and fail closed. Never broaden worker tenant access to simplify claim.

Ordinary asynchronous jobs do not require an open browser. Re-evaluate current actor/membership/policy from trusted durable identity, with existing sensitive authorization/reauth rules where applicable; do not persist cookies/session secrets. Current actorless verify_api_ssl origin (network/services.py:789–793) must be derived conservatively from enrollment ownership/provenance, not null=system privilege.

**Finance boundary:** PA-001 canonical lock ordering, request-order receipt semantics and atomic payment/allocation/receipt/audit/outbox remain mandatory. Short worker DB units do not authorize splitting a financial transaction or dropping its locks. Independent source reviewer inspected billing/services.py:555–714; PDF/file transaction refactoring remains outside task0020.

## 3. Packet and acceptance traceability

New [task0020](../../task/0020-job-lifecycle-authority.md) has one objective: safe execution/recovery/current authority for currently registered jobs. It provides baseline/instruction ref, accepted predecessor, allowed/forbidden ownership, nine acceptance groups, required actual PG/race/process checks, legacy migration/drain/recovery treatment and exact delivery protocol.

Main authorities: PRODUCT TEN-03/JOB-02–05/SEC-01/04/05/SUB-05; ARCHITECTURE §§3–6; OPERATIONS §§3–4; ACCEPTANCE §4. Existing backlog TK-101/102/103 and scoped drain TK-1002 remain the source backlog. T06-CRASH and T10 current-authority cases guide assertions; future R2 bulk activation and full DR are **not newly required implementations**. R3/R4/device/scale gates are not smuggled into sandbox DoD.

All J20-A01–A09 implementation results are currently **NOT_RUN / not_submitted**. Packet's expected outcomes are instructions, never actual PASS evidence. Host/lab access is not required for this coding scope. Real RouterOS fencing, clean OS deployment, installer upgrade, DR, browser E2E and million-client scale remain distinct gates.

## 4. Checks actually performed, with attribution

| Check / operation | Environment / actual result | Limit |
|---|---|---|
| GitHub GET main/branches/PRs/tree/compare/check-runs and immutable file reads | Root connector calls succeeded; exact ref/ancestry/source-continuity verified | Remote-only inspection; no shell exit code |
| Existing CI backend log read, job133265461113 | **513 passed,1 skipped,3 warnings**,89.29s; PostgreSQL17.12, Python3.13 CI; skipped FreeRADIUS binary unavailable | Different from integrator's514-pass real-binary environment; not root local run |
| Existing CI frontend log read, job133265461154 | **66 tests /9 files passed**, typecheck/lint/i18n/live-build success | No browser E2E claim |
| Existing CI docs log read, job133265460727 | `python3 docs/tools/check_docs.py` **PASS24files/106links**,85tasks/256cases/662assertions | Docs/static only; existing41d1f33 run |
| Root local execution attempt | Unavailable: exec_command returned no usable environment | Local validator/pytest/PG/process/clone/status NOT_RUN |
| Root staged record checks | JavaScript path/link/status/uniqueness/scope checks; results persisted separately before publication | Does not execute Python docs validator or application |
| New-publication CI | Observed separately on the publication ref/PR after creation; see publication record and PR | Old main CI never attributed to a new SHA |

Independent reports, complete handoffs persisted by root:

- [Job safety source review](../reviewer/20261116T231008Z-0020-job-safety-independent.md), author `/root/job_safety_review`.
- [Prerequisite/finance review](../reviewer/20261116T231048Z-0020-prerequisite-independent.md), author `/root/integration_packet_review`.
- [Packet QA](../reviewer/20261116T231131Z-0020-packet-qa.md), same prerequisite reviewer checking the prepared instruction, not reviewing its own application changes.

Reviewers had read-only source scope and separately owned report blobs; root integrated immutable report objects serially in one tree. There were no parallel shared-file edits or independent merges. Neither sub-agent ran application tests. Root assessed the findings rather than treating specialist output as runtime proof.

## 5. Changes, publication and next action

Changes are records only: task0020, task0010 **next-action metadata only**, this controller report, complete independent reports, sanitized remote/check evidence, LATEST_HANDOFF and progress. No application/config/migration/test, requirements, defaults, manifest or CI modification. No local written artifact outside this Git-backed project.

Starting/parent commit:41d1f33. New branch: `review/0020-job-lifecycle-authority-20261117`, based on that immutable SHA. Publication at initial authoring: **NOT PUSHED**; once readback is performed, a record-only descendant records the actual published ancestor SHA/tree/ref/file matches. The report never claims its own unknowable future commit hash. Exact final publication CI is recorded in the PR metadata after observation.

Next actor: **coding_agent**. Fetch this published instruction ref (or a verified integrated descendant), read task0000+CONTRACT+latest handoff and implement **0020**. Submit application/test/report evidence on that ID, then controller reviews exact tested/published SHA. Task0010 remains done/accepted/integrated. Neither packet publication nor CI starts an external coding agent automatically.

Unresolved Beta blockers: existing installer/upgrade/readiness/secret separation/restore/scheduler, deployment topology DEC-01 and documentation ownership DEC-02, other scoped security gaps and host/GNS3/pilot/capacity evidence. This session does not close them from old reports or represent unavailable runtime testing as PASS. No new deployment access or credentials were published.

## 6. Publication verified — PR26

Initial record commit **`e11d48b4fdc0c1757c52af7d9e528437b5afa0bc`**, parent exact41d1f33,
tree **`653db3cfc9c05e233004bbeae7e753b07b333938`**, is published on
`review/0020-job-lifecycle-authority-20261117` in **[PR26](https://github.com/smahud/MicroTix_Project/pull/26)**,
base main41d1f33. GitHub ref, commit/tree/parent, PR head/base and all
**10 files** were read back at that immutable commit: every content and blob
SHA matched the prepared file. Comparison to main contains only the declared
records; source/config/tests remain unchanged. New task0020 stays
**ready / not_submitted**; PA-006 stays accepted/integrated.

[Publication evidence](../controller-evidence/20261116T231131Z-0020-discovery/publication.json)
records exact refs, byte-content comparisons, independent packet-blob identity
and initial CI snapshot. At first readback run **43978170214** on exacte11d48b:
docs success; backend/frontend in_progress. This is not described as full
success. This publication-evidence descendant changes records only; final
head CI is separately checked and recorded in PR26 after observation.
No local clone/readback was possible or claimed. No merge/deploy/tag occurred.
Next actor remains **coding_agent**, executing task0020 on the published
instruction ref or a verified integrated descendant.
