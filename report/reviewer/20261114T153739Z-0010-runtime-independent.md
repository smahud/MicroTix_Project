# Independent runtime-source review — task0010 / PA-006 / PR17

- Author/role: delegated `idempotency_review`, independent source reviewer for the controller; application source read-only.
- Review performed: 14 November 2026, approximately 15:30–15:40 UTC. The filename is the controller integration identifier; original assigned draft ID was 20261114T160000Z.
- Objective: inspect identity, request canonicalization, transaction/replay boundaries, authorization and the submitted concurrency evidence; verify closure of the preceding controller findings.
- Branch/workspace: `review/0010-pa006-controller-20261114`, `/workspace/scratch/6d59f64531e9/MicroTix_Project`.
- Exact candidate: `37a87291ae66a0fa9167f0c72d1e8340aa5fd245` (PR17); canonical main/base `9903d9b0cf09d737b553da3c21067b4810e956c0`.
- Previous controller revision: `origin/review/0010-pa006-controller-20261113` / `5da0d801c71b020fbb8b977294502ea5a09e7bcb`, particularly `report/controller/20261113T114222Z-0010-pa006-review.md` and its reopened task0010 packet. These records are absent from the PR17 tree and were read with `git show`, not assumed from historical chat.
- Governing requirements: `AGENTS.md`, `CONTRACT.md` §§2/4/5/6A/9–13, `task/0000-start-here.md`, `docs/MASTER_PROMPT_REVIEWER.md`, original task0010 mandatory work2/4/5/6/7 and acceptance, `ARCHITECTURE.md` §5 (line116 canonical body/identity/replay), `ACCEPTANCE.md` §4 and FINANCE's money/data boundaries.
- Proposed verdict: **changes_requested**. The three prior application findings remain open; the submitted race/failure evidence additionally has the limitations below. Root owns the final verdict and actual PostgreSQL reproductions.
- Changes: this report only. No application/test/migration/config/installer/contract edits; no publish, merge, deploy or router access.
- Publication: **NOT PUSHED by this reviewer**; controller owns integration/publication. The report cannot contain its own future commit SHA.

## 1. Prior findings are still present in this exact candidate

### REV-1311-01 — P1, OPEN: legacy proof identity is not reconciled; migration also destroys ambiguous claims

At `backend/domains/subscriptions/views.py:99–102`, the new identity uses `invoice_id`. Migration `backend/domains/jobs/migrations/0004_idempotency_identity.py:66–102` mechanically copies the old empty proof resource to `resource=''`; there is no reconciliation with its cached submission or invoice. The runtime lookup `backend/domains/common/idempotency.py:104–110` and claim `:93–99` use only the new exact tuple. Therefore an old successful `payment_submission:<tenant>:` row is retained under an identity that a normal invoice-scoped retry never looks up. `subscriptions/views.py:111–120` writes a fresh proof and submission. This is the same concrete no-response-delivery upgrade flow previously rejected: an old committed successful action, same actor/invoice/key/body retried after upgrade, can create a second submission/file. It is a payment-proof duplication finding, not proof of double ledger posting.

The current migration further deletes every legacy row with `response_status is None` (`0004:82–85,97–98`), including a nonexpired row whose domain effect may already exist. A subsequent identical request can claim again and execute the handler. The post-migration defensive409 branch (`idempotency.py:179–185`) cannot protect records already deleted by migration. Calling the row a seven-day cache does not establish that a *nonexpired* ambiguous effect may be blindly retried; this directly conflicts with original task work7. `test_stuck_claim_without_response_no_blind_reexecution` mutates a row *after* migration (`test_idempotency_pa006.py:499–508`) and therefore does not test this unsafe migration path. The migration test explicitly requires deletion (`:985–991,1019`) instead of asserting safe outcome preservation.

Minimum correction and closing acceptance remain the prior controller's REV-1311-01: narrowly reconcile or safely block retained completed/ambiguous legacy identities by principal, tenant, actual target and body. Validate cached submission ownership/invoice before replay; invoice B must not receive A. Exercise actual old-code upload → migration → new-code retry for completed and no-response rows, concurrent retries, changed body, platform/session/UUID legacy shape changes and unrelated-domain preservation. Preserve original submission/file count and logical response for successful A; unknown effects must not create a second action. No new infrastructure is necessary.

### REV-1311-02 — P1, OPEN: cached group decision is shared between migration sessions

`backend/domains/customers/views.py:572–575` still builds `identity_conflict_resolve` resource solely from `group_id` and sets `resource_uuid=False`; it omits `migration_id`. A group ID is derived from sorted usernames, independently of session (`customers/services.py:572–575,604–611`). Effects are written against the specific session (`:637–643`); `_get_session` and UUID validation occur inside the decorated handler (`customers/views.py:578–583`), after replay can return.

Concrete flow: principal P/tenant T resolves group G in session A with K/body B, then posts identical K/B for G in session B. The identity is identical and the cached204 returns before B's session lookup or writes. B sees success without its decisions. A malformed or missing parent can likewise receive the cached204. This is within-tenant cross-resource false success, not an observed cross-tenant leak. No code in PR17 closes the prior finding.

Minimum correction: logical resource includes canonical migration/session UUID and exact opaque group ID; validate structured parent before replay and handle retained group-only cache safely. Closing acceptance: authenticated HTTP A/B each writes its own session decisions; A retry replays; A UUID aliases agree; malformed parent422/missing parent404 cannot become204 because G is cached; actor/tenant/permission checks remain intact.

### REV-1311-03 — P2, OPEN: structured body UUID aliases still hash differently

`backend/domains/common/idempotency.py:46–48,165` hashes the raw body before any declared body-field UUID normalization. `backend/domains/billing/views.py:229–234` later parses `package_id` into the actual UUID. Canonical lowercase-hyphenated package ID and uppercase compact alias refer to the same package but have different HMAC inputs; same service/key retry therefore conflicts409 instead of replaying200. This is an existing helper gap within mandatory task work2, not a new regression caused solely by PR17. PR17 changed neither this hash ordering nor this call-site behavior.

Minimum correction: normalize declared typed identity fields before HMAC with a narrow call-site mechanism; preserve exact username/password/opaque strings, array semantics and true changed-body/file409. Closing acceptance: equivalent package UUID aliases replay200; different real package409; other applicable declared UUID body fields and retained raw-hash compatibility are covered. Do not globally rewrite arbitrary strings or add a schema framework.

## 2. New evidence gap for controller disposition

Controller-allocated ID **REV-1411-04 (P2)**, acceptance evidence deficiency.

The required authenticated concurrent HTTP boundary/failure evidence is not established by the replacement test suite:

- Concurrency workers call view `.post` directly with `_fake_request` (`backend/tests/integration/test_idempotency_pa006.py:588–595,632–635,705–708,762–765`). This runs decorator/service code but bypasses DRF HTTP dispatch/auth/permission checks and the outer `TenantApiView` transaction. It is useful protocol testing, not independent authenticated concurrent HTTP testing. Original task's required boundary and targeted HTTP concurrency are explicit. The executor acknowledges this at report §7 while report §5's environment preamble and packet call the matrix full authenticated HTTP evidence.
- Forced-lock observations are polled but not required to succeed. In same-body test `:655–660,666–671`, a timeout still satisfies `assert a_pid is not None` / `b_pid is not None`; obtaining a PID is not evidence that a wait occurred or that B blocked on A's claim. Different-body/platform versions also fall through on timeout without an observed-lock assertion (`:722–732` and analogous platform loop). PID inequality only proves distinct connections.
- `test_fail_before_db_commit_rolls_back_claim_then_retry_succeeds` uses a sequential invalid plan; it is not failure injection after domain/audit/outbox writes and does not establish contender takeover after a leader rollback. No candidate PA006 test injects that interrupted-leader condition. The previous candidate's coverage must not be assumed to apply to this replacement source/migration/test design.

Minimum correction: restore meaningful per-thread authenticated HTTP clients/connections, force and *assert* the intended lock/interleaving (including correct blocked query/blocker), and inject leader failure after DB writes before response persistence while a same-key contender waits. Assert one committed logical effect, no leaked loser effects/audit/outbox/claim, correct replay/takeover and current authorization. Reconcile report claims with the checks actually run. This is the existing task's evidence scope, not a request for broad new architecture/testing.

## 3. Improvements preserved and review limits

The new-format identity is consistently included in claim/lookup/uniqueness, current platform decorators use explicit scope, and new DB effect/response persistence occur within one `transaction.atomic` envelope. INSERT-first ON CONFLICT avoids the earlier check-then-insert unique-violation design. Source inspection of `TenantApiView.dispatch` confirms `initial()` and current permission/step-up run before the decorated handler on real HTTP, while platform `initial()` rejects non-platform actors before replay. No new authorization bypass was found in those actual dispatch paths. Fresh invoice A/B scoping is useful and should remain while legacy transition is corrected.

This source review does **not** independently verify PostgreSQL runtime, the executor's 401 tests, CI status, retained-file counts or device/network effects. Root is running the actual runtime checks; historical controller failures are described as prior evidence and current defects are independently re-established from the present source flow. No external/file exactly-once guarantee is inferred. Existing malformed tenant URL500 and orphan file-on-rollback remain disclosed follow-ups; neither is silently expanded into this source review's patch scope.

## 4. Commands and completion

Actual read-only commands completed successfully: `git show` of the prior controller report/packet, `git diff origin/main..HEAD -- backend`, `git diff --stat origin/review/0010-pa006-controller-20261113..HEAD -- backend`, `nl -ba`/`sed` targeted reads of helper/views/services/migration/tests, and `rg` for idempotency call sites/requirements/failure-injection terms. `cat` reads covered AGENTS, CONTRACT, entry guide, master reviewer prompt, current handoff, executor report; candidate and original task acceptance were compared. No test commands were run by this delegated reviewer.

NOT_RUN: PostgreSQL/unit/integration/HTTP reproductions, CI re-execution, frontend, browser, install/upgrade host, restore/DR, CHR/GNS3, production or capacity. No secrets/customer data were accessed or persisted.

Independent review complete; application acceptance is **not granted**. Next actor: root controller, correlate these source findings with its PostgreSQL evidence, retain prior finding IDs, reopen the same task0010 for corrections, publish the versioned decision and consistent handoff/progress. PA-002/003 dependencies remain closed until relevant review/integration prerequisites pass.
