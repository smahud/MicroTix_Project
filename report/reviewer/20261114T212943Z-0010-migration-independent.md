# Independent migration and concurrency-evidence review — task0010 / PA-006

- Author/role: `/root/migration_review`, independent controller sub-agent. Objective: inspect migration/retained-key safety and the concrete concurrency/failure evidence for the third submission, without changing application code.
- Starting branch/head: `review/0010-pa006-controller-20261115` at **`9e9bf2d42002a00a69d54fc355b77384897b9478`**, PR19. Source ancestor: `c99838c`; main baseline: `9903d9b0cf09d737b553da3c21067b4810e956c0`; previous controller instruction/review: `b6a0cb8` / PR18. The root fetched these refs; this sub-agent did not independently access GitHub or verify remote CI.
- Applicable authority: AGENTS.md; CONTRACT §§2–6A/9–13; task/0000-start-here.md; docs/MASTER_PROMPT_REVIEWER.md; task0010's original acceptance and four correction findings; ARCHITECTURE §5 (scope, same-action replay, canonical body/file, retained-key/business uniqueness), FINANCE and ACCEPTANCE §4 as referenced by the packet.
- Method: read-only source/diff/test review. No PostgreSQL, HTTP, migration, installer or network execution by this sub-agent. Root owns actual runtime reproductions and the final verdict.
- Scope: `jobs/migrations/0004_idempotency_identity.py`, idempotency model/helper, payment-proof replay guard, actual baseline helper/route/auth flow, submitted migration/concurrency tests and previous controller probes/reports.
- Files changed by this sub-agent: this report only. Application/config/schema untouched. Report commit/publication: **NOT PUSHED by sub-agent**; to be integrated and verified by root.

## Assessment

**Changes requested on source review:** REV-1311-01 is only partially corrected. The new migration preserves ordinary three-part no-response guards and supplies conservative legacy replay, but still deletes a valid old scope when a UUID was supplied in URN form. The root is independently reproducing this against actual main HTTP/schema and candidate migration; this report does not claim that execution as its own.

REV-1411-04 has substantial real improvements: separate authenticated clients/connections, complete HTTP dispatch, required lock observation rather than permissive timeout, and after-write leader rollback with contender takeover. The observation helper still identifies only a generic lock wait rather than the asserted blocker/query. Root can establish the precise chain independently, or the executor should strengthen that assertion. This evidence qualification is separate from the confirmed migration parser defect.

## REV-1311-01 — P1, partial correction; valid URN scopes are discarded

Candidate migration `backend/domains/jobs/migrations/0004_idempotency_identity.py:104–107` runs `str(scope or '').split(':')` and deletes every row with a part count other than three. The actual deletion occurs at lines151–152. This is broader than corrupt data: valid UUID URNs themselves contain colons.

On main9903d9b, `backend/domains/common/idempotency.py` builds `scope = f'{operation}:{tenant_part}:{resource}'` directly from raw URL kwargs. Routes use `<str:tenant_id>` and `<str:resource>`; Django's string converter permits colons. `common/views.py:33–44,71–85` passes the raw tenant UUID spelling to Django's UUIDField membership lookup; `:113–114` uses the membership's canonical UUID for the RLS scope while preserving raw handler kwargs. A valid `urn:uuid:<tenant-uuid>` therefore can be recorded verbatim in a successful old scope. The candidate helper explicitly supports UUID aliases including URNs in its documented canonicalization contract.

Concrete valid shapes affected:

| Actual old logical identity | Valid retained old scope | Candidate treatment |
|---|---|---|
| Tenant quotation | `quotation:urn:uuid:<T>:` | Five parts; deleted |
| Tenant payment proof | `payment_submission:urn:uuid:<T>:` | Five parts; deleted |
| Resource operation | `<operation>:<T>:urn:uuid:<R>` | Five parts; deleted |
| Both tenant and resource aliases | `<operation>:urn:uuid:<T>:urn:uuid:<R>` | Seven parts; deleted |

After deletion, neither the normal tuple lookup nor the `payment_submission` empty-resource legacy fallback can find the old completed/ambiguous action. A retry claims a fresh tuple and executes its handler. For payment proof this can write another submission/file; for a retained unknown-outcome claim this removes the intended safety guard. This is the same loss-of-legacy-identity risk covered by REV-1311-01, so retain that stable finding rather than inventing another task.

Minimum correction: parse and canonicalize valid baseline tenant/resource spellings using the known operation/resource shape (including supported UUID URNs) before considering a row invalid. Do not erase an uncertain retained key merely because the delimiter parser cannot reconstruct it; fail-stop or preserve a conservative guard until explicit reconciliation when safe mapping is impossible. Keep the corrected principal scope, platform remap, migration-wide atomicity and no-response protection.

Closing acceptance: real main HTTP proof upload using valid URN tenant/resource aliases → candidate migration on the same disposable database → same owner/invoice/key/body retry must return the original logical result with one submission and one physical proof file. Exercise completed and no-response old rows; aliases must map to canonical retry identity; changed body and wrong target must remain409; malformed retained data must not silently unlock a second effect. Root's actual evidence is required before treating the impact as runtime-verified.

## Other migration/replay observations

- Lines110–113 explicitly remap the three old platform operations from active-tenant scope to `platform`. Resource UUID canonicalization preserves ordinary uppercase/compact/braced aliases once the colon split succeeds.
- Lines130–150 select the newest responsive canonical duplicate, otherwise the newest no-response guard; unrelated business/history tables are not touched. Removing an ambiguous duplicate in favor of a known completed response does not by itself permit a new execution of that surviving identity.
- Ordinary three-part no-response records are retained. Runtime `common/idempotency.py` rejects such rows safely with409 instead of blind execution. `payment_submission` empty-resource fallback verifies the cached submission's tenant and invoice before replay. Group-only legacy identities are conservatively blocked rather than reused across migration sessions.
- Migration-wide PostgreSQL/Django atomicity and required write-freeze/drain are now documented correctly at migration lines42–56. Reverse only with an empty cache is explicitly limited; production recovery is fix-forward. No mixed old/new writer compatibility is claimed.
- The migration loads all retained rows into memory and validates field length only during updates. The latter fails atomically for overlong corrupt data; neither observation has measured evidence sufficient to assert an additional Beta blocker.

## REV-1411-04 — improved tests; exact wait attribution remains limited

`tests/integration/test_idempotency_pa006.py:655–675` now constructs one authenticated HTTP client inside each worker, registers that connection's PostgreSQL PID, then calls `client.post` through dispatch. Same-body and changed-body tests explicitly hold a subscription row lock; platform tests hold the submission row lock. State/effect assertions check invoice/submission/audit/outbox/source-event counts and replay results.

The rollback/takeover test at lines894–1003 calls real `decide_platform_submission`, injects a RuntimeError after domain/audit/outbox writes, and checks leader500, contender204, one completed idempotency row and one committed audit/outbox/source effect. A later same-key retry replays204. The leader enters the patched wrapper before blocking in the real service; exiting the patch scope before releasing the held lock does not prevent the already-running wrapper from injecting the failure. The contender enters its handler after the patch is removed and executes the real service normally. This is meaningful failover evidence, subject to actual root execution.

However, `_assert_lock_wait` at lines616–633 only queries `wait_event_type` and accepts any `Lock` wait. It does not inspect `query`, `wait_event`, `pg_blocking_pids` or which backend holds the lock, despite contexts saying the contender is blocked on the leader's unique claim. The forced setup and final effect assertions are useful; a generic lock flag alone is not a direct observation of the claimed chain. Recommended minimum evidence improvement: assert the leader's domain-lock query and blocker, then assert the contender's `jobs_idempotency_key INSERT` query and leader PID among its blockers. An observer miss must still fail.

## Submitted migration-test evidence limits

`test_actual_migration_payment_submission_retry_replays_original` at lines1195–1242 executes real 0003→0004 migration and candidate HTTP retry, but creates the original submission through ORM with a synthetic `proof_path`; it does not run original main HTTP or create/count a physical proof file. Its useful result is fixture compatibility, not independently observed physical-file preservation through a real source transition. The executor report should preserve that distinction. Existing `report/controller-evidence/20261114T153739Z-pa006/live_upgrade_probe.py` is suitable for a root-controlled actual baseline-source transition, with URN variants added as independent conformance cases.

The ordinary legacy fixture tests, old six controller probes, parent-session identity tests and typed-body hash tests address the earlier concrete cases. They contain no retained URN-scope migration case, which explains why an all-green submitted suite does not refute the parser finding.

## Commands / results / limits

- Read `AGENTS.md`, `CONTRACT.md`, role master prompt, permanent start guide, task0010 packet and current handoff; inspected relevant ARCHITECTURE/FINANCE/ACCEPTANCE references.
- Inspected numbered current migration/helper/model/views/tests, baseline `git show main:backend/domains/common/idempotency.py`, prior controller review and actual-upgrade reproducer.
- `git rev-parse HEAD`: `9e9bf2d42002a00a69d54fc355b77384897b9478`.
- `git diff --quiet c99838c..HEAD -- backend apps .github instalasi.sh`: exit0; checked application/config content matches the submitted source ancestor for those paths.
- All other commands were read-only `cat`, `sed`, `rg`, `nl`, `git show`/`git diff`; no application edits, DB mutations or tests by this sub-agent.
- NOT_RUN: all runtime tests/migrations/HTTP, remote branch/CI verification, live RADIUS, frontend/browser, Debian install/upgrade/recovery, CHR/GNS3/device mutation and capacity. No claim of deployment readiness, scale validation or external exactly-once effects.

Security/compatibility: no RLS/auth relaxation found in the migration changes; the legacy key deletion is the material compatibility/duplicate-effect risk. CandidateBeta remains NOT_READY. No deploy/merge permission inferred.

Next actor/action: root controller combines this source review with its independently executed actual-source upgrade, concurrency/rollback checks and exact-head CI. Keep task0010 open for minimum same-ID correction if the valid-URN legacy deletion is confirmed; close proven prior findings individually rather than repeat working implementation. Root publishes the final task/handoff/progress/decision record and report; this sub-agent neither commits nor pushes.
