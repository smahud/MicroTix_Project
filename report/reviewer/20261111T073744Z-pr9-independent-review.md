# PR #9 independent review — REQUEST CHANGES

**Author:** Codex reviewer `/root/finance_review_1111`  
**UTC:** 2026-11-11T07:37:44Z  
**Objective:** Independently assess PA-001 allocation integrity, lock ordering, compatibility, and evidence.

**Worktree:** `/workspace/scratch/9459f0c7494a/review-latest-20261111`  
**Reviewed detached HEAD:** `3b20b562db37f5b59bc1e13df886264dd8bfa55c`  
**Base main:** `16085f825fef25ee4112d74b729c57e623b0bb05`  
**Executor must persist this handoff at:** `report/reviewer/20261111T073744Z-pr9-independent-review.md`. Reviewer did not write it.

**Requirements consulted:** CONTRACT §§2–5, 9–12; ARCHITECTURE §§4–6; PRODUCT BIL-01/03/08, AC-BIL; FINANCE §§3–4, 15–16; ACCEPTANCE §§1, 4–6; I18N §§2, 5; VC-BIL-03/08.

## Findings

**P1 — Canonicalize invoice identities before merging and sorting.**  
`backend/domains/billing/services.py:558–570`, especially new lock-order loop at **567**.

The keys are caller-supplied strings. Accepted UUID representations can identify the same database UUID while sorting differently. For invoices `aaaaaaaa-…` and `bbbbbbbb-…`, a lowercase request locks A→B, while a request containing `aaaaaaaa-…` and `BBBBBBBB-…` locks B→A. Concurrent verification can therefore deadlock despite the new deterministic-order claim. The database exception has no domain translation and becomes an error rather than the intended successful serialization.

Distinct spellings of one invoice also evade merging at 560: both checks read the same original balance, followed by duplicate allocation insertion against `uq_bilalloc_pair`. That alias defect predates this PR, but identity normalization is necessary for the newly introduced locking guarantee. Malformed invoice IDs also lack the established 422 validation path.

**Smallest correction:** Convert every invoice ID through `uuid.UUID`, translate invalid values into `ApiError.validation`, then merge and sort canonical identities. Existing UUID parsing patterns are available in `billing/views.py:44–48` and `common/tenant_context.py:16–20`.

**Acceptance:** Cover uppercase/lowercase and hyphenated/compact aliases; one invoice through multiple aliases produces one summed allocation; malformed IDs return 422; overlapping multi-invoice verifications use the same database identity order. These are static findings; runtime reproduction was **NOT_RUN**.

**P2 — Lock ordering changes receipt customer and language selection.**  
`backend/domains/billing/services.py:567–580`, downstream **633–643** and **659–662**.

The function now returns sorted allocations. `verify_payment` derives receipt `customer_name` and locale from `allocations[0]`; it therefore selects the lowest string UUID instead of the first requested invoice. Tenant-scoped invoices belonging to different customers are currently allowed. A request beginning with customer A’s invoice can now issue the immutable receipt header and language using customer B. The report describes only stable receipt line ordering and misses this behavior change.

**Smallest correction:** Acquire locks in canonical sorted order, but return the locked objects in original merged request order. This preserves existing receipt behavior without defining a new product policy.

**Acceptance:** Use fixed UUIDs and customers with different names/locales; assert the receipt header, language, and allocation presentation preserve the existing first-invoice behavior.

**P2 — “Full rollback” evidence does not exercise rollback after mutation.**  
`backend/tests/integration/test_billing_payment_concurrency.py:328–354`; claims in `report/orchestrator/20261111T060010Z-pa001-payment-allocation-concurrency.md:99,136–137`.

The failure occurs inside `_parse_allocations`, before any write at service lines 614 onward. The exception is caught inside `tenant_scope`. Unchanged rows therefore demonstrate validation-before-mutation, not rollback of allocation/payment/receipt/audit/outbox effects after a later failure.

**Smallest correction:** Retain this useful validation test but narrow its description. Add one controlled failure after domain writes, catch it outside `tenant_scope`, and assert database rollback across the relevant effects. Account separately for the document service’s acknowledged filesystem-orphan behavior.

## Sound portions and evidence limits

For canonical UUID inputs, locking invoice rows before reading balances is an appropriate, minimal correction. API dispatch and the development seed call verification inside `tenant_scope`, whose `transaction.atomic()` encloses allocation, payment, receipt-row, audit, and outbox writes. Tenant predicates and composite foreign keys remain intact.

The inspected ordinary paths use payment→invoice→tenant. Invoice issuance takes tenant then inserts a new invoice; I found no ordinary existing-invoice lock inversion in that issuance path. Receipt numbering remains serialized by the tenant row. Invoice locks now also remain held during PDF rendering/storage; the executor correctly records this unresolved transaction-duration risk.

The tests meaningfully assert paid-versus-allocation sums, winner/loser states and side-effect counts, separate PostgreSQL backend PIDs, and receipt-number uniqueness. Settings require PostgreSQL; SQLite would not establish this evidence.

However, the barrier at test lines **135–139** precedes transaction entry and balance reads. Separate PIDs do not prove overlapping execution or an observed lock wait. Each race runs once, so an unlocked implementation can occasionally pass through serial scheduling. The reported old-code failures and repeat runs are useful empirical evidence, not deterministic sensitivity. Add a controlled real PostgreSQL contention case that forces the relevant interleaving. Service calls with `actor=None` do not exercise concurrent HTTP idempotency, permissions, or actor auditing; those remain separate work.

## Verification and disposition

**Executed read-only:** `pwd`, `date -u`, `git rev-parse HEAD`, `git status --short`, `git diff --stat`, exact-base `git diff`, `rg`, `nl`, `sed`, and `cat` on repository files. Final status was clean. Some exploratory searches returned missing-path errors; corrected paths were subsequently inspected.

**Runtime NOT_RUN:** No application execution, tests, dependency installation, database access/mutation, CI reruns, or production access. Controller supplied successful backend/frontend/docs CI run `42970045333`; this reviewer did not independently execute it. Executor runtime claims were inspected as reported evidence.

**Verdict: REQUEST CHANGES.** Correct canonical identity ordering and preserve receipt semantics, strengthen/narrow the identified evidence, then return the new SHA for review. Green CI does not address the uncovered alias inputs.

Production financial integrity/retry gates, applicable accountant review before production bookkeeping, network/lab gates, installer rehearsal, and measured capacity remain unestablished by this review. Sandbox correction requires none of those production accesses.

**Reviewer modifications:** none. **NOT_PUSHED** — no commit, push, merge, or other mutation attempted.
