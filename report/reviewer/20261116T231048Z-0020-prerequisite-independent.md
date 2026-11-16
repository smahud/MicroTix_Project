# Independent prerequisite review — task0020 / PA-002 + PA-003

Author: ChatGPT Work sub-agent `/root/integration_packet_review`. Review time: 2026-11-16T23:10:48Z / 17 November 2026 WIB. Role: read-only prerequisite and scope reviewer, delegated by controller `/root` under the explicitly invoked MASTER_PROMPT_REVIEWER and CONTRACT §5. Baseline: immutable `main@41d1f33f16508491a34f66b767830b9dd3e5954e`, tree `9036b3e4ce473df39d569eabb11c813b14956bb2`. No local branch/worktree exists for this subtask; repository reads used the GitHub connector at that SHA. No repository writes, application changes, PR operations or merges were performed by this reviewer. Report publication at handoff: NOT PUSHED by this sub-agent; root must persist this complete attributed report.

## Verdict and dependency

**ELIGIBLE TO AUTHOR task0020 for current job lifecycle and authority scope.** Task0010/PA-006 remains **done / accepted / integrated**. This is a prerequisite/scope decision, not acceptance of PA-002/PA-003 implementation, which has not been submitted. Do not reopen PA-006 or demand a sixth submission. Production Beta remains NOT_READY.

The normative authority already exists in current main: ARCHITECTURE §§3–6; OPERATIONS §3; ACCEPTANCE T05 and §4; CONTRACT §§6A/8–13. The PA-002/PA-003 labels originated in planning records, but PR8 remains an unmerged draft. A task can trace those labels for audit continuity while deriving every required behavior from current authoritative main documents. Do not silently promote draft planning_audit to main contract.

## Actual independent verification

The reviewer read current CONTRACT, permanent start guide, reviewer prompt, task0010, latest handoff/progress, R5 controller decision and integration report. It independently fetched GitHub PR24, PR25, PR8, current exact-head check-runs and the comparison from R5 decision head to current main.

| Item | Actual observed result | Limit |
|---|---|---|
| PR24 | closed + merged; head `a301a94c2b3268679065e85bbef66f35949483f7`; merge `532862be2711f26d537ae1df540258bbdcae2052` | GitHub readback, no merge performed |
| PR25 | closed + merged; head `c352bce4e3f4cfe87ae62ee23e3c1e2a4cfbb450`; merge `fd0f3faa84ea87c142d37da5dacf01e22a493f90` | Versioned accepted R5 decision is present on baseline |
| Current main CI | three completed check-runs, backend/frontend/docs all success, exact `41d1f33`; run `43857508367` | Existing GitHub CI, not reviewer execution |
| c352bce → 41d1f33 comparison | ahead; all 17 changed paths are progress/handoff/task0010/integration report/evidence | No application/config/test delta; prior code acceptance remains attributable to its exact reviewed ancestor |
| PR8 | open, draft, head `6bb57c9251f3a7a67b71b9523c01e507fdb1b601`, not merged | Its draft docs must not replace current normative authority |
| Scope review | Source inspection of jobs engine/worker/views/models, tenant context and permissions, active customers/network/radius handlers, billing service and owning tests | Static findings below, runtime reproduction NOT_RUN |

Endpoints: `/repos/smahud/MicroTix_Project/pulls/{24,25,8}`, `/commits/41d1f33f16508491a34f66b767830b9dd3e5954e/check-runs`, `/compare/c352bce4e3f4cfe87ae62ee23e3c1e2a4cfbb450...41d1f33f16508491a34f66b767830b9dd3e5954e`, and immutable file reads. Tool calls completed successfully. There are no shell command exits to report.

Integration report claims of local 514-pass backend regression, actual old-code HTTP/migration probes and FreeRADIUS execution remain **attributed historical evidence**. This reviewer did not rerun them and does not represent the CI count alone as proving worker safety.

## Existing contract and minimum scope

ARCHITECTURE.md:122 already requires short SKIP LOCKED claims, no DB locks during network I/O, current actor/permission/policy/revision before effects and one mutation dispatcher per router. Lines126–136 define transitions, effect_state, cancellation proof, expired execution → uncertain, and the important limit that RouterOS does not understand the database epoch. Lines138–140 require per-handler effect boundary, verification, retry safety, deadline and cleanup/recovery. OPERATIONS.md:36 requires worker drain and reconciliation before mutation resumes;:40 requires current policy/account/payment after restart. ACCEPTANCE.md:79 requires crash/send/ack/stale-writer/cancel verification.

The next packet should cover current registered kinds and HTTP job detail/retry/cancel only to the extent necessary to enforce this contract. It should not build future handlers, add queues/services or redesign product permissions. The executor must inventory active human-authorized kinds, trusted system-created jobs, permission requirements, resource/router scope, mutable revision/policy and effect/readback boundaries. A null actor must not become universal bypass; legitimate existing system authority needs explicit narrow treatment. Current authentication should be re-evaluated from trusted persisted identity and current membership/policy, without storing browser session credentials in job payloads.

## Current source findings to close with tests

These are static confirmed implementation patterns with concrete failure paths; runtime interleavings remain unexecuted in this review. Root owns final finding IDs and integration into its report.

1. **Unfenced outcome/detail writes.** `backend/domains/jobs/engine.py:202–214` validates transition against a Python job snapshot then updates by `id` alone. `_mark`:281–289 and retry update:308–321 likewise lack expected state/token/epoch. `detail.save` at:270–271 is not tied to current ownership. `_fenced_save`:194–199 exists but its boolean outcome after execute is ignored. A stale worker can continue through these writes after reconciliation/replacement/cancellation. Acceptance needs stale snapshots and forced transfer/interleaving, checking state, detail, progress, heartbeat and domain effects separately; a return boolean alone is insufficient.

2. **Long worker transaction.** `engine.py:227–278` wraps preflight/execute/verify in `tenant_scope`; `backend/domains/common/tenant_context.py:44–53` makes that scope an atomic transaction. Network handlers call adapter-dependent services during execute. A blocked network operation therefore remains inside that transaction and can hold earlier row locks; a heartbeat on the same connection is uncommitted until outer scope ends. Refactor into short tenant-scoped DB units around bounded I/O while preserving fail-closed RLS and deliberate domain atomicity. Validate heartbeat visibility from another connection and that blocked network I/O does not retain protected unrelated business locks.

3. **Cancellation/unknown retry proof missing.** `engine.py:375–379` permits executing/verifying cancellation when the stale effect_state says none, without proving no outstanding send or fencing external writer. `retry_job`:383–399 creates a new job from uncertain state without readback, while `resolve_uncertain`:356–364 trusts a boolean without an external-writer-stop proof. Cancellation and retry must not enable duplicate remote effects; RouterOS epoch limitation must stay explicit. Test a controllable outstanding send, lost ack, cancelled/stale writer, completed vs not-applied readback and safe re-entry. Do not interpret lease expiry as external fencing.

4. **Incomplete recovery/drain/current authority.** `reconcile_expired_leases`:337–353 only scans executing/verifying and writes by id, so claimed/preflight crash recovery and reconciliation-vs-renewal need explicit treatment. `runworker.py:32–49` has no stop-claims signal handling, bounded drain or reported timeout result. Default handler preflight and current customers/network preflight do not centrally recheck actor membership/permissions. Test revoke/demote/router-scope change after enqueue and after preflight, plus unknown handler/missing actor fail-closed behavior.

5. **HTTP underlying permission boundary.** `jobs/views.py:61–98` implements detail/retry/cancel through `ActiveTenantApiView`, which verifies active membership and `in_scope` but does not itself enforce the permission of the job's underlying operation. An active low-privilege tenant member can reach these paths for a privileged-kind job. Test direct authenticated HTTP endpoints, current revoked/demoted roles and router scopes; no reliance on hidden UI controls. Cross-tenant records retain generic404 behavior.

The trusted global **Job envelope is intentional**, not a newly discovered RLS defect: `jobs/migrations/0002_rls_composite.py:1–3,17–30` explicitly distinguishes global envelope from tenant-RLS JobDetail. Preserve that narrow dispatcher boundary; do not solve worker isolation by granting broad tenant detail access or turning off FORCE RLS.

## Finance and compatibility boundary

`billing/services.py:555–620` deliberately normalizes invoice identities, acquires row locks in canonical order and returns request-order allocations;:623–714 locks the payment and commits allocations, immutable receipt, audit and outbox in one caller transaction. This is the accepted PA-001 invariant. The job short-transaction requirement does not authorize removing financial locks or committing half a payment. Keep owning finance services/API behavior unchanged unless a small specifically justified integration change is necessary, and preserve all PA-001 concurrency/rollback/receipt assertions. PDF/blob rollback or shortening the financial transaction is a separate scoped follow-up; it must not be smuggled into job fencing.

Old queued payloads, job states and nullable actor histories need an explicit compatibility/recovery table. New fencing/authority fields may justify minimal expand-only migrations; do not rewrite applied PA-0060004/0005 or finance history. Rollback/downgrade that restores unsafe workers cannot be called safe. Pending/unknown effects remain held until old senders are stopped and readback completes.

## Required evidence and next actor

Task0020 should require deterministic PostgreSQL tests with independent connections/runtime NOSUPERUSER/NOBYPASSRLS, assertions that both threads/processes complete, explicit blocker/wait observation when contention is claimed, actual side-effect counters and domain/audit/outbox checks. Prove signal/worker drain with a real disposable subprocess; handler-controlled simulator/fake-I/O tests establish sandbox behavior only, never CHR/RouterOS external fencing. Run relevant backend/RLS/PA-001/PA-006 regressions and Django migration checks. The P3 REV-1611-TEST-01 thread-completion assertion may be bundled as test-only hardening without reopening task0010.

NOT_RUN by this reviewer: shell, Python/pytest/Django/docs validator, PostgreSQL races, signal/drain subprocess, installer/upgrade/restore/DR, real router/GNS3/CHR, browser E2E and capacity. No installed code or network was mutated. Existing installer/topology/restore/scheduler/host/lab blockers persist.

Next actor: controller `/root` publishes one scoped task0020 with this attributed report and consistent handoff/progress, then coding_agent implements and submits evidence on that packet. At report handoff no task0020 implementation is accepted, integrated or released. Sub-agent completion: read-only prerequisite/scope review COMPLETE; optional draft-packet QA remains available on follow-up.
