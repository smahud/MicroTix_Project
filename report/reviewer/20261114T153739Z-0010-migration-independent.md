# Independent migration/compatibility review — task0010 / PA-006, PR17

- Author/role: delegated `migration_review`, independent DB/compatibility source reviewer; application and tests read-only.
- Objective: verify legacy identity, retained-key, tenant/principal/resource, ambiguity and migration recovery against the existing packet and previous controller findings.
- Starting branch: `review/0010-pa006-controller-20261114`.
- Exact reviewed candidate: `37a87291ae66a0fa9167f0c72d1e8340aa5fd245`, PR17, executor branch `session/2026-11-14-pa006-idempotency`.
- Canonical base: `9903d9b0cf09d737b553da3c21067b4810e956c0`.
- Earlier correction record inspected: `origin/review/0010-pa006-controller-20261113@5da0d801c71b020fbb8b977294502ea5a09e7bcb`, packet `task/0010-pa006-idempotency.md` and controller report `report/controller/20261113T114222Z-0010-pa006-review.md` on that ref.
- Requirements read: AGENTS.md; CONTRACT §§2–6A/9–13; task/0000-start-here.md; current handoff; docs/MASTER_PROMPT_REVIEWER.md; ARCHITECTURE §5 (line116); original/correction packet mandatory work2/6/7 and acceptance; relevant FINANCE/ACCEPTANCE references and owner handlers/models.
- Proposed verdict: **changes_requested**. Existing findings REV-1311-01/02/03 are not closed. Root owns the final verdict and all PostgreSQL runtime verification.
- File changes by this sub-reviewer: this report only. Commit/publication: **NOT PUSHED; root-owned integration/publication**.

## 1. REV-1311-01 — P1 remains open: the schema backfill does not reconcile changed identities

Source inspected on the exact candidate:

- `backend/domains/jobs/migrations/0004_idempotency_identity.py:66–101` splits the old `operation:tenant:resource` and copies its canonical components; it never resolves a cached submission back to its invoice/actor, and never changes old tenant-scoped platform rows into the explicit platform scope.
- `backend/domains/subscriptions/views.py:99–102` now chooses invoice UUID, whereas main's successful proof record has an empty resource.
- `backend/domains/common/idempotency.py:93–110` claims/looks up only the new exact identity; there is no old-shape lookup/reconciliation.
- `backend/domains/subscriptions/views.py:109–120` stores a fresh file then inserts a new PaymentSubmission when the new identity is absent. `subscriptions/models.py:155–190` has no retained-request uniqueness bridging these records. `subscriptions/upload.py:98–106` chooses a new opaque path for every upload.

Therefore an old successful proof with `payment_submission:<tenant>:` survives migration at resource empty, but the same owner/invoice/key/body retry looks for resource invoice UUID. It claims a new row and executes the handler again. This is the same unresolved source flow as the prior controller reproduction, not a claim that this sub-reviewer ran the old runtime experiment against PR17. Fresh A-versus-B tests cannot establish safe old-to-new retry.

The changed platform scope has the same compatibility gap: old platform operations could store the active tenant from session; backfill preserves that tenant UUID while new decorators (`subscriptions/views.py:187–237`) always choose literal `platform`. Domain decision uniqueness may prevent some duplicate downstream actions, but the retained original replay is still not recovered. This report does not claim a demonstrated double ledger posting.

**Additional unsafe migration branch within this finding:** `0004:82–86` deletes every no-response record, including nonexpired claims whose effects are unknown. The runtime helper would reject an existing ambiguous record (`idempotency.py:179–186`), but that protection cannot run after migration deletes it. The migration comment that deletion prevents blind execution contradicts the actual absent-record claim path. Clearing an uncertain cache record does not prove that its domain/external effects did not occur. Tenant handlers usually have an outer transaction (`common/views.py:113–114`); platform handlers previously did not have a global HTTP transaction. In any case, the packet explicitly requires retained unknown effects to be reconciled/blocked, not discarded and retried blindly.

A source-function inspection was executed without a DB: AST-load the exact `_backfill_identity` function and its UUID helper/constants; provide a fake historical model with three synthetic records. Actual observed output:

| Input retained record | Backfill actual output |
|---|---|
| completed payment_submission / tenant T / empty resource | retained as tenant T, operation payment_submission, **resource empty** |
| no-response quotation / tenant T / key unknown-effect | **deleted** |
| completed platform_submission_approve / tenant T / submission S | retained as **tenant T**, operation platform_submission_approve, resource S |

This is deterministic execution of the data transformation against synthetic in-memory rows, **not PostgreSQL migration or HTTP integration evidence**. Root must bind its runtime results separately.

Minimum correction: carry the prior correction policy forward, preserve or safely reconcile nonexpired ambiguous legacy identity, resolve old proof results through the actual submission/invoice/owner before replay, and handle old platform scope explicitly. Do not replay invoice A to B, and do not purge uncertainty as a substitute for proving no effect. No extra queue/framework or installer implementation is requested.

Closing acceptance: actual old-source request plus migration plus same-key candidate retry; completed and no-response legacy cases; same principal/tenant/target returns original result or safely blocks/reconciles with no additional effect/file; B and changed body remain safe; concurrent retry; platform old-session identity; unrelated business rows remain intact.

## 2. REV-1311-02 — P1 remains open: the migrated opaque group is still missing its parent session

`customers/views.py:572–575` chooses only opaque group_id. Migration0004 preserves that group verbatim (`:74–75`) without parent migration_id, and replay (`idempotency.py:176–188`) precedes `_get_session` and `_validate_uuid` in `customers/views.py:579`. `customers/services.py:572–611` computes reusable groups across the tenant, while `:637–650` writes decisions for a particular migration session. Thus sessions A and B with the same group/key/body still collide. A cached204 can make B appear resolved without B decisions; it can also bypass malformed/missing parent validation. The previous controller finding is unchanged by the new schema representation.

Minimum correction/acceptance: resource identity must include canonical migration_id and exact opaque group_id; all structured components validated before replay; legacy group-only records reconciled safely. Verify HTTP A/B each writes its own decisions, A retry replays, parent alias identifies A, malformed422/missing404 cannot become cached204. Preserve principal/tenant/permission boundaries.

## 3. REV-1311-03 — P2 remains open: retained hash/body identity not normalized

`common/idempotency.py:46–48,165` still hashes raw request.data with JSON key ordering; it has no declaration of typed payload identity fields. `billing/views.py:221–238` subsequently normalizes package_id. The equivalent package UUID alias therefore hashes differently before the handler validates it; retained old hashes have no reconciliation policy. Existing resource-UUID alias tests do not cover this request-body identity.

Minimum correction/acceptance: normalize declared UUID body fields before HMAC with narrow owner-aware rules; keep passwords/usernames/arbitrary strings and array meaning intact. Same service/key and equivalent package UUID representation replays original200; real different package gives409; cover other applicable typed fields and retained hash compatibility. Root's runtime reviewer owns reproduction results.

## 4. Migration ordering/recovery evidence gaps

Migration0004 is a default Django migration with no `atomic=False`; on PostgreSQL its DDL+RunPython is migration-transaction atomic. The docstring `0004:34–36` and executor report lines150–151 still describe per-statement retry/partial-backfill behavior, contrary to the explicit prior correction. Dropping old scope also makes concurrent old application code incompatible immediately. The candidate report's ordering section (`report/orchestrator/20261114T150000Z-0010-pa006-idempotency.md:148–156`) provides no drain/write-freeze and old/new source ordering. Required correction: document quiesce/backup/migrate/new-code/restart and failure/fix-forward for the supported topology, without claiming rolling versions or implementing out-of-scope installer work. The reverse is intentionally limited to empty cache, with destructive forward purge not reversible; this is not a demonstrated production rollback.

The submitted migration test (`tests/integration/test_idempotency_pa006.py:936–1071`) creates generic quotation records, a no-response claim and an opaque group, then explicitly asserts no-response deletion (:1019). It neither follows an old successful payment proof into an invoice-scoped new request nor validates the side effects of unknown claims after migration. The standalone stuck-claim test (:488–518) removes a response **after new-schema creation**, so it proves the defensive runtime branch, not preservation through migration. Both distinctions matter to the all-PASS legacy acceptance claim.

The current packet replaces the acceptance table with an assertion that all rows passed, while the earlier same-ID controller correction block is not present on this branch. Do not treat rewritten executor status as authority to remove measurable acceptance or close findings. Root should preserve previous reports and same-ID correction history semantically in the published handoff.

## 5. Commands, limits, next action

Commands executed successfully for source inspection: `cat`/`nl -ba` on the named entry/contract/packet/report/source/test paths; `git show` of main's helper/model/migration and the exact prior correction record; `git diff --stat origin/main...HEAD`; `git log --oneline origin/main..HEAD`; `rg -n` for idempotency requirements and migration/legacy tests. AST-loaded backfill inspection exited0 and printed the three outcomes above. No application files or tests were edited.

NOT_RUN by this sub-reviewer: PostgreSQL/HTTP/concurrency suite, actual DB migration/rollback, CI, installer, host upgrade, restore, GNS3/CHR, RADIUS network integration, deployment, capacity measurement. No shared DB was started or mutated. No CI or executor test results are adopted as this reviewer's own results.

Security/compatibility: new tuple includes principal and explicit tenant/platform and is an improvement for new-format requests; RLS is not weakened by the inspected migration, and no plaintext request secret is introduced by this code. These improvements do not close old-shape compatibility or nested-target identity. Beta readiness remains a separate decision.

Next actor/action: root controller independently verifies/reproduces the observed paths, persists a changes_requested decision on candidate37a8729 with the same task0010, and returns the narrowly scoped corrections/tests to coding_agent. Do not unlock PA-002/003 or claim merge/deploy acceptance from this report. This sub-review task is complete; root must publish and verify its integration.
