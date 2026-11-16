# Independent acceptance review — task0010 / PA-006, PR24 R5

Author: independent reviewer `/root/acceptance_review`, delegated by the
controller on 16 November 2026. This is a read-only source/evidence review;
database and HTTP execution belong to the controller's separate verification.

**Recommendation: accept the PA-006 scope if the controller's real PostgreSQL
regression, upgrade and current-head CI checks pass.** No new application
defect was confirmed. R4 closures remain supported by unchanged source and
meaningful assertions. One P3 test-completeness note below is not a runtime
blocker; it must not be presented as proof of a missing runtime guarantee.

## Identity, instructions and permitted changes

- Reviewed candidate: PR24 exact
  `a301a94c2b3268679065e85bbef66f35949483f7`.
- Executor implementation ancestor:
  `7338a720b5d64a4ccb47b9abe7d3dc6feca0a476`.
- Previous independently reviewed code:
  `634da4224f15dd6a5a4e9010fe1811dec8c7954d` (R4/PR21).
- Canonical main baseline: `9903d9b0cf09d737b553da3c21067b4810e956c0`.
- Starting checkout was detached at candidate `a301a94`; the controller may
  subsequently create its publication branch without changing reviewed code.
- Read AGENTS, CONTRACT, the default reviewer prompt, permanent task guide,
  current packet/handoff, R4 controller report, R5 executor report, relevant
  ARCHITECTURE §5 / FINANCE / ACCEPTANCE requirements, owning source/tests
  and the retained controller conformance probes.
- Allowed writing only this report. No application/test/task/handoff/CI/
  installer/contract/ref/database changes made. No merge, push or deployment.

## Verification performed by this reviewer

All commands were run from the local repository supplied by the controller.
`git rev-parse HEAD` returned exact `a301a94`. `git diff --name-status
634da42 HEAD -- backend apps instalasi.sh .github CONTRACT.md` showed only
the migration parser and added R5 test file among those paths. The changes
relative to main retain the earlier PA-006 implementation; they are not a
replacement implementation from main.

A Python check compared `git show <ref>:<path>` bytes for twelve relevant
files on R4 and R5. All twelve were identical: common/idempotency; owning
subscriptions/customers/billing views; customers/billing services; jobs
model; scrub migration0005; PA-006 base/R4 test files; PA-001 concurrency
test file; and retained controller `test_review_effects.py`. This verifies
preservation rather than relying on the executor's claim.

A pure-Python AST probe executed the exact current normalization helper
definitions without importing Django or connecting to a database. Eight
assertions passed: nested UUID alias normalization, two nested targets,
unchanged amount/memo/secret strings, no mutation of the caller's body,
selected-array order preservation and malformed-value preservation for
domain validation. It printed `pure_normalization_checks=8, result=PASS`.
This is helper evidence only, not HTTP/permission/effect verification.

AST inspection of the new concurrent-retry test confirmed the P3 note
below. Read-only `rg`, `nl` and `sed` inspection traced the following matrix.
No project test suite was run by this sub-agent. Executor log counts such
as 514 passed are executor evidence, not this reviewer's results. CI was
not independently fetched by this sub-agent; final-head checks are root-owned.

## Acceptance and retained finding disposition

| Acceptance / earlier finding | Source and assertion assessment |
|---|---|
| Principal/tenant/platform/operation/resource separation | `common/idempotency.py:281–342` uses authenticated principal, canonical tenant or explicit platform, operation, canonical resource and key consistently; `jobs/models.py:231–235` enforces the same uniqueness. Base tests exercise separate principals/tenants, invoice A/B and operator active-tenant changes. Source unchanged from R4. |
| Same identity/body concurrent replay; different-body conflict | Claim uses `INSERT ... ON CONFLICT ON CONSTRAINT uq_idem_identity DO NOTHING RETURNING` in the surrounding transaction (`idempotency.py:194–234,298–370`). After waiting, a fresh SELECT obtains the committed response. Different bodies conflict before another effect. Base tests use independent authenticated clients and database connections. |
| REV-1411-04 — forced interleaving and rollback | Retained controller `test_review_effects.py:52–88` strengthens generic Lock observation by checking actual SQL and `pg_blocking_pids`: leader waits for the held domain row, contender waits on leader's idempotency INSERT. Four scenarios include rollback after writes and contender takeover. These probes are unchanged; they must be distinguished from barrier-only R4/R5 tests. |
| Current authority before replay | `common/views.py:71–86,101–118` runs current membership/permission and sensitive reauthentication before invoking the decorated handler inside tenant_scope. `subscriptions/views.py:181–187` runs current platform authorization before its handler. Base tests447–481 explicitly assert expired step-up403, authorized replay and revoked membership404 without cached-response disclosure. No claim of exhaustive permission coverage. |
| REV-1311-02 — opaque conflict group bound to parent | `customers/views.py:570–617` validates/canonicalizes parent before replay, checks parent existence, validates exact opaque group and scopes to `<migration UUID>:<group>`. Old group-only caches are rejected with409 via `legacy_replay=False`. Base tests1468–1563 assert A/B session independence, replay and malformed/missing-parent behavior. |
| REV-1311-03A — nested money UUID identity | `billing/views.py:429–435` declares `allocations[].invoice_id`; recursive normalization preserves other values and array order. R4 tests327–531 verify alias-first/canonical, retained hash, target/body changes, malformed422 and effect counts. Source byte-identical to accepted R4 closure. |
| REV-1311-03B — selected identities | `customers/views.py:640–670` canonicalizes before preview and durable payload; `customers/services.py:676–705,791` canonicalizes consumption, including old payload aliases. R4 tests561–655 verify alias-first counts, canonical payload, one job and one resulting account, malformed422 and ordered-array conflict. Source unchanged. Empty-selection/lifecycle/authority policy belongs to the separately scoped PA-003 work. |
| REV-1511-05 — no plaintext replay preview | `customers/services.py:48–57,426–439` masks password before returning/storing validation; jobs migration0005 scrubs retained replay preview while preserving identity, hash, response status and guard. R4 tests672–778 assert fresh/stored/replayed secret absence and real migration scrub with replay. No generic claim about all CSV staging storage. |
| REV-1311-01 — legacy upgrade | R5 migration parser is grammar-driven and uses the baseline UUID parser instead of fixed URN branches. R5 tests cover both positions, repeated-prefix grammar, real MigrationExecutor transitions, completed/unknown outcomes, wrong target/body, opaque legacy rejection, dedupe and atomic rollback. The separate migration specialist/root verify grammar and real old-code HTTP/file behavior. Source read supports closure subject to those independent results. |
| Before-commit failure / unknown outcome | Domain/replay writes share the transaction; exceptions unwind claim and effects. Legacy no-response records fail safely with409 before domain execution. R5 unknown-state tests assert guards and no second effect; injected no-response state is not an observed OS crash. Existing physical-file orphan follow-up remains separate; no exactly-once external-effect claim. |
| TTL / PA-001 | TTL removes cache entries without removing owning business constraints. Base TTL test checks existing quotation business uniqueness; do not describe it as exhaustive for every operation. PA-001 service and ten concurrency/identity/rollback regressions are byte-identical to R4. Controller full regression remains required. |

## P3 note: R5 concurrent-retry test can omit a stalled participant

**ID: REV-1611-TEST-01, P3, test completeness only.**
`backend/tests/integration/test_idempotency_pa006_r5.py:398–408` joins each
thread with a timeout, then validates only `results.items()`. It does not
assert both threads finished or that results has exactly keys A and B.
If a worker remains stalled past the timeout, that worker's result is
absent and never checked; with no results, the loop is vacuous, and the
pre-existing one-submission/one-guard state still satisfies the final counts.
This is a static control-flow counterexample, not evidence that workers
actually stalled on this candidate. Related barrier tests predate this diff.

Minimum follow-up: assert each thread is no longer alive and
`set(results) == {"A", "B"}` before validating outcomes. A meaningful
test-sensitivity check makes a non-completing/missing-result participant
fail. Root should independently prove two completed responses for current
prefix replay; the existing forced-wait conformance cases remain necessary
for the runtime claim protocol. With that independent evidence, this note
does not justify another application correction cycle or reopening the
already-correct transaction/auth implementations.

## Limits, publication and next action

NOT_RUN by this reviewer: PostgreSQL/HTTP suites and migrations, actual
old-code upload/upgrade/file effects, current-head CI, frontend/browser,
installer/OS/service drain, production recovery, real CHR/GNS3/router,
deployment and capacity validation. No new blocker confirmed from source.
The pre-existing opaque-garbage resource-length fail-stop note remains an
ops/runbook follow-up; it is not silently converted into a new Beta gate.

Completion: source/evidence acceptance review complete, recommendation
reported to root. **NOT PUSHED** at report authoring. This report's future
commit SHA is not known and is not invented.

Next actor: **controller_reviewer**. Combine the independently executed
PostgreSQL/old-code upgrade/physical-effect checks, migration specialist
report and exact-head CI with this assessment. If they pass, publish the
exact-SHA PA-006 acceptance and preserve prior closures; determine
integration and next dependent packet eligibility separately. Acceptance
does not grant merge, deployment, tag or release permission. Beta remains
NOT_READY until its remaining existing gates are fulfilled.
