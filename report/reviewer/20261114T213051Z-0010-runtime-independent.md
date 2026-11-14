# Independent runtime/source review — task0010 / PA-006 PR19

- Author/role: delegated controller sub-agent `runtime_review`; independent source review, not the executor's internal reviewer.
- Review date: 15 November 2026 Asia/Jakarta; report filename uses UTC.
- Objective: review runtime identity, replay, authorization, tenant boundaries and body canonicalization against the full task0010 acceptance and prior findings.
- Starting branch: `review/0010-pa006-controller-20261115`; reviewed candidate **`9e9bf2d42002a00a69d54fc355b77384897b9478`**, PR19 `session/2026-11-15-pa006-idempotency`. Product baseline `main@9903d9b0cf09d737b553da3c21067b4810e956c0`; previous controller instruction `b6a0cb863f52cbbf512b23dceafc4231ff9c7d74`; tested source ancestor `c99838c`.
- Scope authority read: AGENTS.md, CONTRACT.md, task/0000-start-here.md, docs/MASTER_PROMPT_REVIEWER.md, task/0010-pa006-idempotency_done.md, report/LATEST_HANDOFF.md; relevant ARCHITECTURE §4–6/§5 idempotency, ACCEPTANCE §4/security, PRODUCT CSV-01/02/AC-CSV and RADIUS §10.1. Reviewed executor report and previous controller decision for evidence limits.
- Allowed writes: this report only. Application, tests, schema, configuration, contracts and shared database remained read-only. No commit, push, review submission, merge or deployment by this sub-agent.

## Verdict

**CHANGES_REQUESTED recommendation from source review.** The ordinary fresh principal/platform transaction design and the group-parent correction are materially improved. REV-1311-01 still has a valid legacy UUID-shape hole; REV-1311-03 is incomplete for a live monetary operation and normalizes a selected-ID hash without normalizing the operation's selected IDs. One explicit no-plaintext-secret replay requirement also remains unsatisfied. Parent controller should confirm the concrete probes below on its PostgreSQL environment, allocate final finding IDs and record its own runtime evidence separately.

These are source-confirmed paths; this sub-agent did **not** execute HTTP or PostgreSQL tests. Expected probe results below are predictions from exact code flow, not claimed observed runtime results.

## RT-01 — valid legacy URN UUID scopes are deleted as malformed

Related finding: **REV-1311-01**, recommended P1.

- Current migration `backend/domains/jobs/migrations/0004_idempotency_identity.py:104–109` splits the entire legacy scope on every `:` and deletes rows unless the number of pieces is exactly three.
- Actual baseline helper at `main:backend/domains/common/idempotency.py:53–55` formats raw URL/session values as `operation:tenant:resource`. Baseline routes use `<str:tenant_id>` / `<str:invoice_id>` (`backend/domains/subscriptions/urls.py:8–10`). A UUID URN such as `urn:uuid:<canonical-uuid>` is an accepted UUID representation: membership and invoice filters use UUIDField conversion; `backend/domains/common/tenant_context.py:19–21` canonicalizes using `uuid.UUID`.
- A baseline successful request with tenant URN writes `payment_submission:urn:uuid:<tenant>:`. A baseline resource URN similarly contributes extra colons to operations with a resource. These are valid old records, not corrupt cache. The migration deletes their completed response or unresolved-effect guard. Candidate canonical retry cannot find the deleted guard and wins a fresh claim; a proof upload can create a second submission/file. The revision's policy to preserve no-response guards is therefore incomplete for valid aliases.

Minimum correction: parse supported old operation/UUID/platform/opaque shapes without confusing UUID URN colons with delimiters; preserve unresolved records or fail-stop safely when a live identity cannot be reconstructed. Do not silently delete an accepted UUID alias's guard. Keep the existing migration atomicity/drain policy and no business-history mutations.

Closing acceptance: actual baseline HTTP request with tenant URN, and a separate resource URN operation, followed by real 0003→0004 migration and canonical/alias retry; prove same logical response/effect, retained uncertainty guard and no second file/submission/job. Include identical-body and conflicting-body cases.

## RT-02 — live payment allocation UUIDs still hash as raw strings

Related finding: **REV-1311-03**, recommended P2.

- `backend/domains/billing/views.py:429–432` decorates `internet_payment_verify` without any declared body UUID field.
- The actual handler consumes `body.allocations[].invoice_id`: `backend/domains/billing/services.py:537–552,590–597` explicitly canonicalizes UUID aliases before merging/locking and treats canonical, uppercase and compact forms as one invoice. This is established PA-001 behavior and must remain intact.
- `backend/domains/common/idempotency.py:81–108` only normalizes declared top-level fields or scalar elements of their lists; it cannot reach an invoice ID inside an allocation object. At `:258–259,307–308` the second same-key body spelling hashes differently and returns false `409 idempotency_conflict` before replay, despite selecting the same invoice and amount.

Minimum correction: declare and canonically hash the actual typed nested allocation identity. Preserve allocation order and opaque exact-case fields; do not introduce global UUID-looking-string rewriting or reorder arrays. Bring retained-hash compatibility policy to this path too.

Closing acceptance: independent authenticated HTTP verify with one invoice, retry same key/payment/amount with uppercase-compact/URN invoice alias; receive the original 200 and exact action, with one allocation/receipt/audit/outbox outcome. A different invoice or amount must still return409. Include concurrent alias retries and relevant PA-001 regression.

### Complete current body-identity inventory

All 28 current decorator call sites were traced. Actual request identity fields are:

| Operation | Actual typed body identity | Candidate treatment |
|---|---|---|
| service_billing_package | package_id | Declared top-level normalization |
| service_provision | router_id | Declared top-level normalization; ORM accepts UUID aliases |
| migration_commit | selected_account_ids[] | Declared scalar-list hash normalization; handler mismatch RT-03 |
| internet_payment_verify | allocations[].invoice_id | **Missing** nested normalization |

Conflict resolution body is `resolution/new_username`; its opaque group stays exact-case and parent belongs in resource identity. CSV create/link rows use username/service_code strings, and current CSV commit ignores a selected body rather than consuming UUIDs. Network replacement consumes display_name; RADIUS cutover and backup use URL router IDs. Do not normalize usernames, passwords, package names, reasons, external references, group tokens or array order.

## RT-03 — selected-ID hash equivalence does not match actual migration operation

Related finding: **REV-1311-03** identity correctness; recommended P2. This is narrower than the separate planned selected-set/PA-003 policy work.

- New `backend/domains/customers/views.py:623–626` declares `selected_account_ids` for hash canonicalization.
- The handler still passes raw IDs to preview at `:643–644` and persists raw IDs in job payload at `:652–654`.
- `backend/domains/customers/services.py:663,675–679` forms a raw string set and compares each canonical `str(obj.id)`. `commit_migration` repeats this raw set at `:749` and the same canonical comparison at `:765–768`; `backend/domains/customers/handlers.py:74–77` forwards the persisted raw selection unchanged.
- Thus an alias-first request can return202 with preview to_create0 and a job that adopts none, even though a canonical-first request selects the intended object. Candidate same-key canonical retry now hashes identically and replays the wrongly parameterized job. Hash canonicalization alone does not establish equivalent domain actions. This requires a domain-effect assertion, not just unit proof that hash strings match.

Minimum correction: pass the canonical declared identity values through validation, preview and durable job payload/consumption as well as hash identity, retaining the same logical selected set and array semantics. Reject malformed typed IDs with the established schema response. Do not use this finding as permission to implement unrelated PA-003 lifecycle or selection-policy changes.

Closing acceptance: fresh alias-first and canonical-first equivalent migration selections must produce matching preview counts, canonical IDs in the durable job and the same selected-account effects when the existing handler runs; retry must replay one job. Different selected identities remain409, and invalid identity values must not silently select zero accounts.

## RT-04 — plaintext CSV credential is persisted in replay response

New safe-replay acceptance gap; recommended P1, **pre-existing**, not claimed introduced by PR19.

- Packet mandatory work5 and ARCHITECTURE §5 prohibit cached plaintext secret/reveal responses.
- `backend/domains/customers/views.py:430–437` caches `csv_import_validate` and returns the validation result.
- `backend/domains/customers/services.py:413` puts complete raw CSV rows into response `preview`; `:497–499` confirms that `row.password` is an actual accepted access credential, not an unrelated label. Existing test `backend/tests/integration/test_customers_api.py:342–343,367–373` deliberately includes passwords and asserts raw preview equals the source rows, so existing green tests enforce the unsafe result.
- `backend/domains/common/idempotency.py:329–332` persists that complete response into `jobs_idempotency_key.response_body`. This table has no tenant RLS policy; the new key tuple prevents ordinary cross-principal HTTP replay but does not turn plaintext at-rest credential copies into compliant storage. A later authorized retry returns the same plaintext preview. Request HMAC does not protect cached response data.

Minimum correction: ensure safe CSV validation response/replay excludes plaintext credential fields while preserving useful preview/error information and existing authorization. Handle already retained cached secret payloads safely; do not re-expose them via legacy replay. Keep secret-input HMAC and no-secret response rules. The broader CSV staging encryption issue is separate and is not proposed for expansion here.

Closing acceptance: use only an ephemeral synthetic sentinel in memory, create/validate a supported password CSV, assert the sentinel is absent from original/replayed public response and persisted idempotency response; same-key replay remains the same nonsecret logical result. Check retained cache behavior. Log boolean/count outcomes only, never sentinel or credential data. Correct the old raw-preview equality assertion to the authoritative no-secret contract with explicit evidence; do not weaken acceptance to match the defect.

## Confirmed improvements and prior finding disposition

| Area | Source review result and limit |
|---|---|
| New principal/tenant/platform/resource isolation | Claim SQL, lookup and uniqueness use the same five-part identity; platform=True removes active-tenant drift. No new bypass found by tracing. Runtime independently pending at parent. |
| Transaction protocol | Tenant handler runs inside TenantApiView.dispatch→tenant_scope atomic transaction; decorator atomic savepoint contains claim/domain/response. Platform decorator is outer atomic; domain tenant_scope nests. SQL ON CONFLICT serializes same-identity claims, rather than SELECT-then-insert. No source contradiction found in fresh ordinary paths. |
| Permission/step-up | TenantPermission/PlatformApiView.initial run before handler/decorator replay. Current membership/role and required sensitive reauth are checked before cached response returns. |
| REV-1311-02 group parent | **Closed at source level**: resource includes canonical migration UUID plus group; parent existence checked before all replay paths; opaque group regex bounds length; group-only legacy fails safely. Parent's runtime probe establishes final closure. |
| REV-1311-01 | Ordinary completed payment legacy and ordinary no-response records now retained/replayed/blocked correctly at source; valid URN-shaped records RT-01 still unsafe. |
| REV-1311-03 | package_id case fixed at source; nested allocation identity RT-02 and actual selected-ID action RT-03 remain. Retained noncanonical v1 hash conservative409 policy is explicitly documented and tested, not a duplicate-effect path by itself. |
| REV-1411-04 | Tests now construct per-thread authenticated HTTP clients, assert lock observation and thread completion, and inject failure after domain/audit/outbox writes with waiting contender. Root owns execution; this sub-agent does not independently claim runtime closure. |

## Commands, evidence and limits

Commands run by this sub-agent were read-only `cat`, `rg`, `sed`, `nl -ba`, `git show`, `git diff`, `git status`, `git rev-parse` and UTC timestamp lookup. Successful scoped reads/diffs returned exit0. Two combined exploration calls returned exit2 because guessed paths (`backend/config/urls.py`, `backend/domains/billing/upload.py`) did not exist; actual module files were then located with rg and read successfully. These were exploration errors, not product failures.

`git rev-parse HEAD` returned the full PR19 SHA above. `git diff --name-only c99838c..9e9bf2d -- backend apps instalasi.sh` returned empty, verifying the application/test/config portion of the published candidate matches that tested ancestor. Diff from previous controller base showed only the permitted application modules and tests plus records. Sub-agent ran **no pytest, Django checks, migration, CI read or HTTP probe**, and did not inspect live production, GNS3, real routers, install/upgrade/recovery or capacity. Executor 426-pass and six-probe claims are attributed to its report and are not this reviewer's observed runtime evidence.

Security/compatibility: preserve all passing principal/platform/transaction changes and PA-001, maintain RLS and current permission checks. No new infrastructure or policy/CONTRACT change is necessary for these corrections. No zero-downtime or release readiness claim follows from source review.

## Handoff/publication

- Report completion state: source review complete; root controller owns runtime confirmation, final verdict and integration.
- Report publication state at authoring: **NOT PUSHED** by this sub-agent; report has no future self-SHA claim. Parent may commit/publish it with the controller decision and record exact remote readback there.
- Next actor/action: root controller runs the concrete focused probes, reconciles these source findings with migration reviewer/runtime evidence, publishes same-ID task0010 corrections if confirmed, updates handoff/progress and verifies remote publication. No dependent task or deployment is unlocked by this report.
