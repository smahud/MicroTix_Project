# Task0020 independent authority and handler review

- **Author/role:** OpenAI Codex sub-agent `/root/review_authority`; independent controller-side source and focused probe author. Main controller owns final verdict and publication.
- **Objective:** verify current authority, router-scoped HTTP actions, handler transaction boundaries and negative verifier behavior for J20-A02/A06/A07/A09.
- **Repository/worktree:** `smahud/MicroTix_Project`, local branch `review/0020-controller-20261117`; starting and reviewed candidate **`bd37c14e6c41339a8743b3d4b723ee74f13bef08`** (PR27), implementation/tested ancestor **`7118cce0db330acb02be0b3b774b1b1628d55d7a`**. Base main **`41d1f33f16508491a34f66b767830b9dd3e5954e`**; instruction **`ea7b8a17ad8d6339eed45769bbff1626ea279665`**, PR26.
- **Applicable authority:** AGENTS.md; CONTRACT §§5–6A/8–13; reviewer prompt and start guide; packet0020 J20-A02/A06/A07/A09; PRODUCT TEN-03/JOB-02–05/SUB-05/SEC-01/04/05; ARCHITECTURE §§3–6; executor and internal reviewer reports dated `20261117T010218Z`.
- **Files changed by this reviewer:** this report; focused acceptance probe `report/controller-evidence/20261117T134100Z-0020-review/test_authority_review.py`; pure source probe `source_authority_probe.py` in the same directory. No application, requirements, schema, shared contract or branch changes; no commit/push by this reviewer.
- **Status:** **CHANGES_REQUESTED** recommendation. Four source findings were subsequently reproduced by the root controller on real split-role PostgreSQL; see the final attributed runtime addendum. No acceptance, integration, deployment or device verification claimed.

## Findings

The reviewer-local IDs below are stable within this report; the controller may map them to final task-level finding IDs without duplicating work. Findings are grounded in current candidate source, not copied from prior audits.

### RV-AUTH20-01 — P1: revoked authority after preflight still reaches a production effect

**Acceptance:** J20-A06; ARCHITECTURE §6 current actor/permission before effects.

**Locations:** `backend/domains/jobs/engine.py:531–546` checks authority before preflight; `:591–606` enters executing and invokes execute without another authority check. `backend/domains/network/handlers.py:142–155` performs router release without a fresh authority check. Import, migration, replacement, backup and discovery similarly have no effect-boundary authority check; cutover B2/B5 is the narrow exception.

**Concrete sequence:** a legitimate owner enqueues/claims `router_release`; real production preflight completes; another connection commits membership revocation or demotion to viewer while worker is held before returning from preflight. Worker then heartbeat-checks lease and executes release, marks WireGuardPeer removed and deprojects NAS although membership no longer permits the action. Lease ownership is distinct from actor authority.

Existing `TestCurrentAuthority` tests mutate membership **before** `run_claimed`, so those tests do not cover this required after-preflight interval.

**Minimum correction:** check fresh authority at the effect boundary after preflight and before actual domain/send effects; preserve tenant/resource scope and per-chunk checks. This does not require storing session secrets or cancelling ordinary async work when the browser closes.

**Closure:** independent connections plus Event/barrier after real preflight; revoke and demote; both must produce zero release/peer/NAS effects and an honest authority-denied outcome. Preserve valid actorless enrollment provenance and valid normal async execution.

### RV-AUTH20-02 — P1: direct job endpoints ignore membership router scope

**Acceptance:** J20-A07; PRODUCT TEN-03; ARCHITECTURE §4 membership role/scope before reading data and §5 non-owned 404.

**Locations:** `backend/domains/jobs/views.py:47–66` verifies tenant and kind permission but never `request.mt_membership.router_scope`. Detail `:89–96`, retry `:99–119` and cancel `:123–138` all rely on this helper. Worker-level `check_current_authority` has a router-scope check; it cannot prevent an unauthorized HTTP cancel or data read.

**Concrete sequence:** same-tenant technician/owner has `router_scope=[A]` and backups.run; job for router B is known via its ID. GET passes and reveals its record; POST cancel passes and durably cancels a queued job for B; POST retry creates a new job for B before worker eventually rejects it. The membership's scope excludes B throughout.

**Own pure probe:** extracting the actual `_require_job_authority` AST and supplying scope `[router-allowed]` with job router `router-denied` returned normally for GET and POST. This is control-flow evidence, not a full HTTP/PG test.

**Minimum correction:** enforce current router/resource scope in the common job-authority path with generic 404 for an out-of-scope resource. Preserve same-tenant/no-permission 403 and sensitive step-up. Do not grant scope merely because role permission exists.

**Closure:** actual HTTP GET/cancel/retry for an out-of-scope router return 404, leave state unchanged, create zero retry jobs; in-scope operations still follow existing role and step-up rules.

### RV-AUTH20-03 — P2: B6 rollback still performs adapter I/O inside a database transaction

**Acceptance:** J20-A02; ARCHITECTURE §6 short transactions and no DB transaction across network I/O.

**Locations:** `backend/domains/radius/handlers.py:326–346` opens `ctx.scope()` then invokes `_PHASE_FN[B6]` before exiting the scope. `_b6_rollback` at `:255–270` calls adapter APPLY and VERIFY at `:262–263`. `backend/domains/common/tenant_context.py` implements tenant_scope as `transaction.atomic()`; leaving an inner scope cannot exit the outer transaction.

**Own pure probe:** executing the actual extracted `_run_phases` and `_b6_rollback` with a scope-depth tracker records APPLY and VERIFY at depth 1. The code comment saying I/O is outside a transaction is false on this branch. B2/B5 use the corrected structure; B6 does not.

**Minimum correction:** load B6 DB state in a short unit, leave the outer tenant transaction, perform authorized/fenced rollback APPLY/VERIFY, then commit verified evidence in a separate short unit. Preserve rollback outcome and recovery truthfulness.

**Closure:** production rollback handler with a controlled blocking adapter; observer sees committed durable state and no worker transaction retained across APPLY/VERIFY. At minimum the focused probe's real connection must be autocommit/outside atomic at both calls; root may add an independent pg_stat_activity observer.

### RV-AUTH20-04 — P1: negative rollback readback is reported as successful rollback

**Acceptance:** J20-A07 negative verifier never succeeds; J20-A04 truthful unknown outcomes.

**Locations:** `backend/domains/radius/handlers.py:263–270` stores `rollback_readback_ok=False` but unconditionally changes router enforcement to local and run state to rolled_back. Handler verify at `:307–324` then unconditionally returns `ok=True` whenever any run exists.

**Concrete sequence:** B6 APPLY returns, VERIFY returns `{"verified": false}`. Current code records the negative evidence, reports LOCAL and ROLLED_BACK, and engine terminal commit succeeds. B2/B5 correctly reject negative readback; B6 must follow the same invariant while retaining recovery information if effects are uncertain.

**Own pure probe:** extracted current functions with verified=False produced `run.state=rolled_back`, `router.enforcement_mode=local`, stored `rollback_readback_ok=false`, followed by `handler.verify={ok:true,phase:B6,state:rolled_back}`. No real device is claimed.

**Minimum correction:** explicit negative/unknown B6 verifier handling; do not assert LOCAL/ROLLED_BACK or job succeeded without positive readback. Make final cutover verify validate the documented successful/pending-observation/rollback state and evidence rather than returning unconditional true.

**Closure:** actual engine+PG B6 with controlled negative readback must not return succeeded, mark rolled_back or claim LOCAL. Positive rollback and honest B3/B4 pending observation remain valid. Preserve redacted evidence needed for recovery.

## Independent checks and test ownership

1. `git rev-parse HEAD` returned exact candidate `bd37c14e6c41339a8743b3d4b723ee74f13bef08`.
2. `git diff --stat 7118cce0... bd37c14... -- backend/ apps/` was empty, confirming unchanged application/test source relative to the designated tested ancestor for these paths.
3. Read current packet, authority/permission helpers, jobs engine/views, touched customers/network/backup/radius handlers, network service effect boundaries and relevant tests. Traced current call paths outside the diff where needed.
4. `python3 /tmp/microtix_authority_source_probe.py` exited 0 and printed the concrete helper/rollback outcomes above. The portable retained copy is `report/controller-evidence/20261117T134100Z-0020-review/source_authority_probe.py`. This executes actual source function ASTs with fake managers/adapters, so it proves control flow only.
5. Both retained Python probe files compiled successfully via `compile(source,path,'exec')`; no application files changed.
6. Authored seven acceptance tests in `test_authority_review.py`: HTTP detail/cancel/retry scope (3), after-preflight revoke/demote with independent DB connection and bounded Event/join (2), negative B6 verifier (1), actual transaction-boundary observation (1). Assertions express required acceptance and are expected to FAIL current defects. **Root/controller owns PG execution and raw log; this reviewer did not run them against the shared DB.**

Executor's 554-pass suite, frontend/CI and prior reviewer claims are inputs read, **not** this reviewer's own test results. Controller should link exact runtime output and any corrections before adopting findings as its final verdict.

## Acceptance/evidence limits

| Acceptance | Reviewer conclusion |
|---|---|
| J20-A02 | FAIL by current B6 call-path analysis and pure tracker; actual PG observer delegated to controller |
| J20-A06 | FAIL by missing after-preflight boundary check; own full PG reproduction pending controller |
| J20-A07 | FAIL by HTTP scope helper and negative B6 readback control flow; full HTTP/PG reproduction pending controller |
| J20-A09 | No schema change in this review; designated source ancestor equality confirmed. Full regression/legacy repair/drain compatibility not independently executed by this sub-agent |

The A06 executor matrix also asserts PASS for current policy, but its six authority tests do not exercise policy/hold/payment/SUB-05 transitions. Engine does not inspect subscription/policy/revision; active import/create quota paths use reserve()'s quantity checks. Record this as an **evidence gap** for controller assessment; this reviewer does not propose a new generic policy framework or future R2 implementation. SUB-05 requires preserving existing service/RADIUS operations in restricted and preventing destructive SaaS-debt isolation; current lack of subscription checks alone does not prove the whole policy contract.

NOT_RUN by this reviewer: PostgreSQL/HTTP/thread tests (root coordinated), whole backend suite, frontend, CI fetch, production OS install/upgrade/restore, real RouterOS/CHR/GNS3, RADIUS daemon, browser E2E, scale benchmark. Controlled adapter/source probes do not establish real device recovery, sender fencing or zero downtime.

## Security, compatibility and handoff

No requirements, application code, persisted customer data or credentials were changed. Probe fixtures use disposable random identities and test-only credential refs; no runtime secrets are printed. The focused tests preserve bound joins and collect worker exceptions/results so a missing participant fails the harness.

**Commit/remote status:** NOT PUSHED by sub-agent; controller will integrate and publish the report with task/packet/handoff updates. **Next actor:** controller reviewer: execute focused probes on exact candidate using real disposable PostgreSQL, inspect observed durable effects, combine lifecycle review findings and publish changes_requested on **ID0020** with minimum corrections and closure acceptance. Keep PA-006 accepted/integrated; do not create a duplicate task or claim Production Beta readiness.

## Runtime-harness correction (controller feedback; before final rerun)

The first controller PG run of this reviewer's seven tests produced the expected adverse HTTP/B6/demotion observations but errored during teardown: the initial `transaction=True` marker lacked `available_apps`, so Django's TRUNCATE did not cascade unmanaged RADIUS projection foreign keys (`radius.nas`). A queued HTTP-retry artifact then contaminated the subsequent revoke case's claim. **That first revoke outcome is discarded as unreliable; no result from the contaminated run closes acceptance.**

On controller request, this reviewer corrected the test harness marker to an explicit applicable installed-app list, enabling `allow_cascade` in Django's fixture teardown consistently with the repository race suites. No acceptance assertion or application source changed. Syntax validation passed. Controller retains the first log and runs the corrected probes against a fresh disposable test DB; final runtime outcomes must be attributed to that rerun.

## Final attributed controller runtime addendum

**Execution owner:** root/controller `/root`, not this sub-agent. After the harness correction above, root ran the seven retained acceptance probes on a **fresh disposable PostgreSQL 17.11** database using [run_probes_split.sh](../controller-evidence/20261117T134100Z-0020-review/run_probes_split.sh). The sub-agent subsequently read the resulting raw log and role evidence; the outcomes below are attributed to root's execution.

- Runtime `mtx_app`: NOSUPERUSER, NOBYPASSRLS, non-owner; all 59 tables in the checked schemas were owned by `mtx_migrator`. Tenant tables retained FORCE RLS. Role/table evidence: [split-roles-rls.log](../controller-evidence/20261117T134100Z-0020-review/split-roles-rls.log).
- TRUNCATE privilege was granted **only** for disposable pytest fixture cleanup; this is a stated harness deviation, not a proposed production permission. It does not authorize application operations.
- Root command: from `backend/`, configured TEST_DATABASE_URL to the disposable instance, then `../.venv/bin/python -m pytest -c pytest.ini <evidence>/test_authority_review.py -q -s --reuse-db --tb=short` (the exact absolute interpreter/path and setup are in the retained runner).
- **Final result: seven failed acceptance assertions, zero harness errors, 2.91 seconds, exit 1.** Raw evidence: [authority-probes.log](../controller-evidence/20261117T134100Z-0020-review/authority-probes.log). These failures are confirmed candidate defects, not test-infrastructure failures.
- The first teardown-contaminated run is superseded by this corrected clean run and remains retained as history.

| Controller finding | Reviewer-local finding | Final root-observed effect |
|---|---|---|
| **REV-1711-05** | RV-AUTH20-01 | Both independent-connection **revoke and demote after real preflight** produced `state=succeeded`, `error_code=null`, **router_released=true**. Worker and controller PIDs differed and joined cleanly. Required result was zero release and authority_denied. |
| **REV-1711-06** | RV-AUTH20-02 | Same-tenant but out-of-router-scope actual HTTP **GET 200**, **cancel 204** with queued→cancelled, **retry 202** with job count **1→2**. Required result was 404 with zero state/job-count changes. |
| **REV-1711-07** | RV-AUTH20-03 | Actual B6 APPLY and VERIFY both saw **`connection.in_atomic_block=true`, `autocommit=false`** on the real worker connection. Required result was I/O outside the transaction. |
| **REV-1711-08** | RV-AUTH20-04 | Negative B6 verifier stored **readback_ok=false** yet durable job **succeeded**, run **rolled_back**, router **local**, result **ok=true**. Required result was no successful rollback/local claim. |
| **REV-1711-09** | Policy/SUB-05 evidence gap | Separate incomplete-coverage item, not mislabeled as a runtime reproduction by these seven probes. Controller owns the final closure matrix for policy/deadline/compatibility/drain evidence. |

Root separately executed the existing full backend suite: **554 passed, 1 skipped, 3 warnings**, exit 0; the skip was the real FreeRADIUS binary test unavailable in this environment. See [full-suite.log](../controller-evidence/20261117T134100Z-0020-review/full-suite.log). This successful existing suite does not supersede the seven confirmed acceptance failures above. The focused probes are the split-role runtime evidence; do not imply the entire existing suite was run under that same split-role setup.

Final recommendation remains **changes_requested on exact candidate bd37c14**, return the minimum corrections to **ID0020**, preserve prior closed PA-006 and valid existing behavior, then rerun these exact acceptance probes and relevant regressions on the corrected SHA. Controller publishes the final verdict/task/handoff; no new dependent task, merge, deployment or feature activation follows from this report.

## Final documentation/record QA before publication

On root request, this reviewer read the final controller report `report/controller/20261117T134100Z-0020-job-lifecycle-review.md`, reopened `task/0020-job-lifecycle-authority.md`, current top of LATEST_HANDOFF/progress, and `review-results.json`.

- Exact reviewed PR27 `bd37c14`, executor ancestor `7118cce`, base/main `41d1f33`, original PR26 instruction `ea7b8a1`, current decision branch and coding-agent next action agree across current records.
- Eight confirmed defects REV-1711-01–08 are distinguished from eleven failed probes and the separate REV-1711-09 evidence gap. Full-suite 554/1skip/3warnings and focused split-role 11 failed/0errors are attributed and bounded correctly; no acceptance/main integration/deployment is claimed for task0020. PA-006 remains accepted/integrated.
- `git diff --stat bd37c14e6c41339a8743b3d4b723ee74f13bef08 -- backend/ apps/` remained empty: app/test source unchanged.
- **One pointer ambiguity reported to root:** packet table's `Instruction ref` row still tells the reader to consume the packet at original PR26 `review/0020-job-lifecycle-authority-20261117`, while current correction requires `review/0020-controller-20261117`. The next-actor row already has the correct decision ref. Minimum clarification: distinguish **original instruction ref** from **current correction instruction ref** in the table so an executor cannot accidentally use the earlier packet. Root owns this shared-doc edit; this reviewer did not modify it.
- Publication §8 is explicitly NOT PUSHED at this QA snapshot. It must be filled/read back only after actual publication; this QA is not a remote-publication claim.

No additional concrete current-record inconsistency was found within this QA scope. Root retains ownership of final link/docs validation and GitHub publication.
