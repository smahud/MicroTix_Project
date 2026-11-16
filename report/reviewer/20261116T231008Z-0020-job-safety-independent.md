# Independent source review — task0020 PA-002 / PA-003

- **Author:** `/root/job_safety_review`, independent read-only reviewer.
- **Report path:** `report/reviewer/20261116T231008Z-0020-job-safety-independent.md`
- **Baseline:** `main@41d1f33f16508491a34f66b767830b9dd3e5954e`.
- **Objective:** validate the minimum next packet for existing PostgreSQL jobs, worker lifecycle, fencing and current authority.
- **Changes:** no branch/ref writes, application edits, merge or deployment; immutable report blob only on follow-up root authorization.
- **Publication:** NOT PUSHED by this reviewer; root must persist this complete report.
- **Publication follow-up:** an unreferenced immutable report blob is created on root's follow-up assignment; publishing a branch/ref containing this report remains root's responsibility.
- **Disposition:** the next PA-002/PA-003 packet is justified. This source review grants no implementation acceptance. Keep accepted PA-006 and PA-001 closed.

## Authority and scope

Read `AGENTS.md`, `CONTRACT.md`, `docs/MASTER_PROMPT_REVIEWER.md`, relevant sections of `ARCHITECTURE.md`, `PRODUCT.md`, `OPERATIONS.md`, `defaults.json`, `test-cases.json`, and the existing controller register `report/controller/20261111T074225Z-repo-handoff-review.md`.

Applicable requirements:

- ARCHITECTURE §3–6: granular permission and resource scope; current actor/permission/policy/revision before effects; short transactions; lease/epoch fencing; readback before uncertain retry.
- PRODUCT TEN-03, JOB-02–05, SYNC-03, NET-05/08 and SUB-05.
- Test catalog T06-CRASH-01/02/03, T10-TEN-03, VC-JOB-02/03/04/05, VC-TEN-03 and VC-SYNC-03.
- Existing REV-1111-06 remains substantively reproducible from current source.

The packet should repair existing active handlers and their API boundaries. It should not introduce another queue, infrastructure service, generic workflow language, future-phase handlers, RouterOS mutation support or production activation.

## Confirmed current source defects

These are source-confirmed execution paths. PostgreSQL/process/network reproductions were **NOT_RUN** in this review.

| Finding | Current evidence and consequence | Minimum closure |
|---|---|---|
| **JS-0020-01 — P1: lifecycle transactions encompass handler I/O** | `backend/domains/jobs/engine.py:227` wraps the entire preflight/execute/verify sequence in `tenant_scope`; `backend/domains/common/tenant_context.py:51` implements that scope using `transaction.atomic()`. Job updates and domain locks remain uncommitted throughout adapter calls. Another connection may see the last committed `claimed` state while the worker is executing. Reconciliation only searches executing/verifying. | Durable, bounded lifecycle transactions; tenant-scoped transactions around actual DB work; no transaction or row lock retained during network I/O. Prove visibility and lock behavior from a second PG connection. Preserve domain-change/audit/outbox atomicity. |
| **JS-0020-02 — P1: stale workers can overwrite state and result** | `transition_claimed` writes by ID at `engine.py:213`; `_mark` at `288`; retry at `311`; result at `270–271`. These bypass the lease/epoch helper. `_fenced_save` at `194–199` only protects one effect-state write and its false return is ignored at `247`. Heartbeat/progress at `61–76` check token, omit expected state/epoch/expiry, and do not report ownership loss. | Every worker-originated lifecycle/result/progress/error write must verify current ownership, expected state and permitted validity. Losing ownership must stop further effects. CAS failure cannot be treated as success. Terminal results remain immutable. |
| **JS-0020-03 — P1: false cancellation during possible effects** | Effect remains `none` until **after** `handler.execute` returns (`engine.py:245–247`). `cancel_job` accepts executing/verifying with `none` at `375–378`, without proving no outstanding send or fencing the old connection. Its snapshot-based save can race with worker transitions. | Atomic cancellation protocol. Before-effect cancellation must prevent subsequent send/commit. In-flight or ambiguous effects must reject cancellation or enter uncertainty/recovery. `none` alone is insufficient proof. |
| **JS-0020-04 — P1: recovery misses early crashes and races with live work** | `reconcile_expired_leases`, `engine.py:337–353`, only handles executing/verifying. A process dying after claim or in preflight leaves unrecovered jobs. Iteration reads a snapshot and then updates by ID without rechecking token/epoch/state/expiry; it can invalidate a renewed lease or overwrite a concurrent outcome. | Recover each applicable nonterminal state according to proven effect boundary. Reconciliation must compare the state and lease observed. Concurrent heartbeat/completion/cancel and repeated reconciliation must not lose valid results or authorize duplicate effects. |
| **JS-0020-05 — P1: uncertain retry bypasses readback** | `jobs/views.py:75–77` allows a retryable uncertain job through; `engine.py:383–399` creates a new queued job with the old payload. Neither requires readback or proof the previous sender cannot send. `resolve_uncertain`, `356–364`, can move `applied=None` to verifying by model save without a complete ownership/recovery protocol. | Unknown and possibly applied outcomes remain blocked. Retry only after evidence of no application plus safe writer fencing. Applied outcome verifies without resending. Preserve origin, action identity and evidence; concurrent retry requests must not schedule duplicate effects. |
| **JS-0020-06 — P1: no enforced per-router sender ownership** | `claim_next`, `engine.py:161–191`, locks only the selected job. Two eligible jobs for the same router can be claimed independently. Handler code does not acquire a shared router mutation owner. A new job/lease is therefore not evidence that the old process/connection has stopped. | Serialize conflicting mutations for a router using the existing PostgreSQL/process design. Release or transfer ownership only with the required old-writer fence and outcome reconciliation. Different routers must remain independently executable. |
| **JS-0020-07 — P1: worker has no drain protocol or enforced job deadline** | `runworker.py` repeatedly reconciles/claims/runs and sleeps; no SIGTERM/SIGINT stop-claim/drain path. `engine.py:141` may set `deadline_at`, but execution/claim never checks it. The `now` argument of `run_claimed` is assigned and unused. Heartbeat is only called before execute/verify; a long handler has no periodic renewal. | Bounded drain that stops new claims, records the active job truthfully, exits predictably, and handles deadline expiry at effect boundaries. Renew lease during bounded long work; do not run a heartbeat in a transaction that remains invisible. Do not impose the simple-operation 60-second deadline on durable B3/B4 observation windows. |
| **JS-0020-08 — P1: worker does not revalidate current authority** | `engine.py:224–247` has no actor/user-active/membership/permission/router-scope/policy/revision check. Customer handler preflights check existence only (`customers/handlers.py:33–37,65–69`); network/radius preflights likewise omit current actor authority. Revoking/demoting the actor after enqueue does not stop the effect. | Check the operation-specific current authority before each affected effect boundary. Enforce tenant/resource ownership, relevant router scope and revision/policy. Revoked actor or changed policy must produce zero prohibited effect and a truthful non-success outcome. |
| **JS-0020-09 — P1: retry/cancel and replace have authority gaps** | `jobs/views.py:70–97` inherits membership-only `ActiveTenantApiView` (`common/views.py:129–147`) and checks tenant equality, but no underlying action permission, router scope or sensitive-action step-up. A tenant Viewer can reach those mutations. `network/views.py:200–214` requires only `routers.enroll` for replacement, while ARCHITECTURE §5 line106 requires `routers.release`; replacement handler releases the old router at `network/handlers.py:156–159`. | Job action permission must follow the underlying operation and current scope. Deny same-tenant unauthorized actions with403, foreign resources with generic404; preserve sensitive reauth. Align replacement with its release authority. |
| **JS-0020-10 — P2: false success on absent handler or negative verifier** | `handler_for` may return `None` (`engine.py:106–107,224`); execution skips all handler work and still marks succeeded. After a real handler returns a verifier result, the engine never checks a negative outcome before success (`255–278`). Existing network verifiers return `{"ok": False}` for missing resources/readback (`network/handlers.py:73–81,99–107`). | Missing handlers fail closed without effects. Active handlers have an explicit success/failure verifier contract; a negative verifier cannot produce succeeded. Preserve valid cutover “pending observation” semantics without claiming completed device mutation. |

## Legacy and system-job compatibility

An important concrete compatibility case must be part of PA-003.

`network/services.py:789–793` creates `verify_api_ssl` jobs without an actor. The related `RouterEnrollment` already stores `created_by` at `network/models.py:130`.

Therefore:

- Do not define `actor=None` as automatically privileged “system”.
- Define and validate the trusted origin for legitimate asynchronous enrollment verification.
- Preserve or recover the initiating actor/resource provenance where applicable.
- Document conservative treatment for already queued payloads that lack newly required metadata. A migration or explicit quarantine/recovery policy may be necessary.
- Do not require an HTTP session credential inside the worker. Sensitive request authorization and durable execution authority are different boundaries.
- Test user deletion, revoked membership, scope changes and pending legacy jobs separately.

This is not permission to rewrite identity or implement every future system job.

## Required independent verification for task0020

Each assertion must include actual state and effect counts, complete thread/process outcomes, command/exit code and sanitized evidence.

1. **Real PostgreSQL, non-superuser runtime with RLS:** concurrent claims, stale snapshot, lease transfer, token/epoch mismatch, terminal overwrite, stale result/progress write, and reconciliation vs heartbeat/completion.
2. **Transaction boundary:** block a controlled adapter at I/O; inspect another connection’s committed job state and PG locks. Assert no worker-owned long transaction/row lock spans that I/O. Tenant context must fail closed on reused connections and rollback.
3. **Crash matrix:** terminate a real worker after claim, during preflight, before/after DB effect commit, after send and before verify/result commit. Every job has a durable resume/recovery outcome. No duplicate DB projection/outbox or false cancellation.
4. **Two workers / same router:** pause old worker before send and after a possible send. New worker must not send until old process/connection is actually fenced and readback establishes the next safe action. Use two routers to prove independence.
5. **Cancellation:** queue/preflight, just before send, outstanding send and after confirmed effect. Race API cancellation with execution and with lease reconciliation. Check effect counters and durable outcome, not response alone.
6. **Uncertain recovery:** readback true/false/unknown; concurrent retries; unreconciled origin; detached/stale worker. An unknown outcome never directly becomes an executable duplicate.
7. **Authority:** enqueue as authorized user, revoke/demote/delete or narrow router scope before execution and before the effect barrier. Include resource from another tenant, platform-only user, Viewer retry/cancel and replacement permission. No unauthorized effects; proper403/404 and relevant sensitive step-up.
8. **Policy/revision:** change relevant resource revision/hold/subscription policy after enqueue. Honor existing SUB-05 semantics: restricted does not disable existing service operations; ended never causes SaaS-debt internet isolation.
9. **Process drain:** real SIGTERM/SIGINT with idle and active worker; no new claims after drain begins; bounded exit with truthful incomplete/uncertain recovery. Test a cooperative DB handler and blocked I/O. OS systemd/installer upgrade rehearsal remains a separate host gate unless actually run.
10. **Verifier failure:** missing handler and negative verification never succeed. Keep explicit source labels and existing real-network mutation guards.
11. **Regression:** PA-001 financial tests and PA-006 idempotency/upgrade/security tests remain valid; run required backend suite/check/migration/docs checks and exact candidate CI. Include REV-1611-TEST-01 test-completion hardening if root bundles it.

Tests must join all threads/processes and assert every result. Fake handler/adapter fault injection can prove sandbox engine properties; it cannot establish real RouterOS fencing or GNS3/host deployment readiness.

## Files and implementation boundaries

Expected allowed areas, only as necessary:

- Existing jobs engine/models/views/runworker and new additive jobs migrations.
- Existing active handler boundaries in customers/network/radius.
- Shared tenant/permission helpers if required by the actual fix.
- Existing enqueue call sites only to persist authority/revision/deadline metadata and preserve compatibility.
- Focused integration/unit/process tests, relevant operations notes, task/report/handoff/progress.

Preserve financial transaction semantics, PA-006 replay/secret protections, FORCE RLS and narrow runtime privileges. Do not alter historical accepted migrations merely for convenience. Installer topology/Compose decision, scheduler, upload/backup rewrites, SSTP PR7 and planning PR8/14 remain outside this packet.

No new queue/broker or generalized security framework is needed to establish these invariants.

## Checks and evidence limits

**Executed:** GitHub `fetch_file` reads of the immutable baseline; source tracing and numbered-line inspection; structured inspection of requirement/default/test catalogs. Relevant files read include jobs engine/models/views/worker/tests; tenant scope/common views/middleware; tenancy models/permissions; customers/network/radius handlers and selected views/services/models; subscriptions services/models; billing services; RouterOS base/api client/simulator.

**NOT_RUN:** shell commands, Django/pytest, PostgreSQL races/RLS, actual process drain, adapter/network calls, installer/systemd, OS upgrade/restore, FreeRADIUS, CHR/GNS3, production/pilot and benchmarks. There is no command exit-code evidence or new runtime PASS in this report.

**Security/compatibility:** source paths show concrete missing guards; exploit impact has not been runtime-demonstrated here. Real API-SSL mutation methods currently fail with lab-required guards; this review does not authorize enabling them. Legacy actorless verification requires explicit treatment, not blanket privilege.

**Completion:** independent source review complete; implementation remains `not_submitted`.

**Next actor/action:** root controller should persist this report, reconcile findings with its own evidence, and publish one task0020 packet from verified integrated main. Coding agent then implements/tests/submits that packet. Controller reviews its exact new SHA before acceptance or dependent work.
