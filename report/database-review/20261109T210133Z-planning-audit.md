# Independent Database & Reliability Review — MicroTix Planning Audit

- **Author/role:** `/root/database_reliability_review`, independent Database & Reliability Reviewer.
- **Objective:** Read-only assessment of PostgreSQL ownership, migrations, RLS, transactions, job recovery, outbox, billing integrity, and recovery readiness.
- **Baseline:** `main` commit `16085f825fef25ee4112d74b729c57e623b0bb05`.
- **Working branch:** `docs/planning-audit-20261110`.
- **Changes by reviewer:** None. Orchestrator must persist this complete handoff under `report/database-review/<UTC>-planning-audit.md`.
- **Commit/remote status:** Baseline verified locally. Reviewer changes **NOT PUSHED**.
- **Evidence level:** Static source inspection. No database, application, installer, migration, or runtime test executed.
- **Excluded implementation:** Open SSTP PR #7 is unmerged and is not counted as canonical `main`.

## Conclusion

The PostgreSQL modular-monolith baseline is appropriate. Existing RLS helpers, composite foreign keys, distinct runtime/migrator settings, transactional domain writes, and real PostgreSQL-oriented tests provide useful foundations.

Those foundations do **not** establish complete reliability. A payment-allocation race creates a critical financial-integrity risk. Worker state transitions and recovery do not consistently enforce their documented fencing rules. Enrollment token completion is neither fully serialized nor atomic with durable follow-up job creation. Outbox delivery remains a placeholder.

**Recommendation:** Documentation can support implementation planning after these deficiencies and acceptance gates are incorporated. Current code is not established as release-safe by this review.

## Applicable requirements

- `CONTRACT.md` §§2–5, 8–11: authoritative requirements, controlled changes, simple architecture, network/tenant safety, evidence and reports.
- `docs/ARCHITECTURE.md` §§4–8: tenant/composite references, idempotency, atomic business/audit/outbox, short job transactions, fencing, ledger enforcement.
- `docs/FINANCE.md` §§4, 13–16: allocations, immutable posting, platform books, reconciliation and retention.
- `docs/RADIUS.md` §§3–8: tenant projection, trusted facade, current policy, accounting and session identity.
- `docs/OPERATIONS.md` §§3–4: privilege separation, complete backup, ordered restore, measurable recovery targets.
- `docs/ACCEPTANCE.md` and `docs/test-cases.json`: reviewed for associated data, outbox, isolation, backup, and recovery requirements. Their existence does not prove execution.

## Migration ownership and RLS inventory

There are **39 numbered migration files across 11 migrated domain apps** at the baseline. Config, i18n, monitoring, and common have no numbered domain migrations.

| Owner | Migration count/latest | Tables or ownership | Static assessment |
|---|---:|---|---|
| tenancy | 2 / `0002_locale.py` | `tenancy_tenant`, `tenancy_membership` | Shared trust/control data; no tenant RLS migration identified. Permissions remain an application trust boundary. |
| identity | 3 / `0003_emailtoken_meta.py` | Users, TOTP, recovery, attempts, email tokens, support grants | Shared identity/control tables; no RLS migration identified. Tenant-related grants require explicit policy treatment. |
| audit | 3 / `0003_rls.py` | `audit_event` | FORCE tenant RLS present. |
| jobs | 3 / `0003_alter_job_kind.py` | Envelope, detail, outbox, idempotency | Detail has FORCE RLS and composite job reference. Envelope deliberately shared. Outbox and idempotency are shared infrastructure with business metadata; not evidence of blanket tenant isolation. |
| subscriptions | 3 / `0003_paymentsubmission_reviewed_by.py` | Plan versions, subscription, quota, SaaS invoice, submissions, platform source event | FORCE RLS on subscription, reservation, invoice, submission. Composite submission→invoice reference. Platform source events have immutable trigger; distinct platform policy must be preserved. |
| network | 10 / `0010_routerenrollment_protocol_and_more.py` | Router, health, enrollment, WG host/peer, discovery, device operation | Tenant RLS and several composite constraints present; WG host deliberately shared. Enrollment bridge adds special lookup policy. |
| customers | 3 / `0003_customer_locale_service_billing_package.py` | Customer, service, access account, CSV import, migration session/decision | FORCE RLS and composite constraints present, including service→billing package added separately. |
| billing | 2 / `0002_rls_composite.py` | Package, service charge, invoice/line, payment/allocation | FORCE RLS on six tables; composite parent references present. They do not prevent same-tenant concurrent allocation races. |
| documents | 2 / `0002_rls_immutable.py` | Issued documents | FORCE RLS and immutable trigger present. |
| backups | 2 / `0002_rls_composite.py` | Artifact and schedule | FORCE RLS and router composite references present. Real backup transfer/recovery remains distinct from simulator manifests. |
| radius | 6 / `0006_session_key_and_session_list.py` | `radius.nas`, check/reply/group/session/postauth plus cutover | FORCE RLS in radius schema; cutover has composite router FK. Several projection-table references remain single-column FKs. |

**Important interpretation:** Shared tables are not automatically violations. Their permitted contents, callers and access paths must be documented explicitly. “All tenant tables have RLS” must not conceal shared infrastructure exceptions or imply all cross-tenant references are constrained.

## Findings

### DB-01 — Concurrent distinct payments can overallocate an invoice and lose its paid balance

- **Priority:** **P0 — Critical**.
- **Status:** **CONFLICT** with documented billing integrity; defect identified by static interleaving analysis, **runtime reproduction UNVERIFIED**.
- **Evidence:**
  - `backend/domains/billing/services.py:587`: `verify_payment` locks the payment row using `select_for_update()`.
  - `services.py:559`: `_parse_allocations` reads invoices without a row lock.
  - `services.py:564`: outstanding is calculated from that potentially stale object.
  - `services.py:602–608`: Python increments `invoice.paid_amount` and writes the computed value.
  - `services.py:623`: tenant serialization lock is acquired **after** invoice writes.
  - `backend/domains/billing/models.py:180–189`: invoice constraints enforce uniqueness/nonnegative values, not agreement between allocation sums and paid balance.
- **Concrete interleaving:** Two separate Rp200,000 payments target one Rp300,000 invoice. Both read Rp0 paid and pass their Rp200,000 allocation against Rp300,000 outstanding. The second invoice UPDATE waits for the first transaction, then writes its stale computed Rp200,000. Both allocation rows can exist, totaling Rp400,000, while the invoice says Rp200,000 paid.
- **Impact:** Financial records disagree; over-allocation, misleading outstanding/receipts, and invalid future ledger/tax sources.
- **Smallest fix:** Lock every target invoice in a deterministic order before validating outstanding; keep validation, updates, allocations, audit, document issuance and outbox atomic. A tenant lock acquired before reading is a simpler but broader alternative; assess contention.
- **Affected modules:** Billing, documents, future finance/Tax, reporting.
- **Acceptance:** Two independent PostgreSQL connections synchronize before allocation validation. Overlapping allocations never exceed total; stored paid balance equals committed allocation sum; excess funds remain credit or the conflicting allocation is rejected. Include different invoice ordering to detect deadlocks and rollback-all assertions.
- **Sequence:** First implementation priority.
- **Downtime/rollback:** Usually application patch with brief worker/API maintenance as needed; no data correction may be inferred automatically. Reconcile existing data before changing it. Rolling code back does not reverse already inconsistent financial records.

### DB-02 — Worker fencing is bypassed by principal state-writing paths

- **Priority:** **P1 — High**, with core-network effect risk.
- **Status:** **PARTIAL / CONFLICT**; static evidence, concurrent failure outcomes unexecuted.
- **Evidence:** `backend/domains/jobs/engine.py`:
  - `_fenced_save` at approximately `185` filters lease token and epoch.
  - `transition_claimed` at `215`, `_mark` at `288`, retry at `311`, and reconciler at `346` update by job ID without equivalent fencing.
  - `run_claimed` calls `_fenced_save` without treating a zero-row update as loss of authority.
  - `cancel_job:375–379` permits executing/verifying cancellation when in-memory effect state is `none`.
  - Effect state becomes `maybe` only **after** `handler.execute()` returns (`246`).
- **Impact:** A stale worker can overwrite reconciled or terminal states. Concurrent cancellation can be based on stale state; “none” does not prove no command is in flight.
- **Smallest fix:** Make worker-owned state/result writes conditional on current lease token, epoch and permitted previous state; stop when ownership is lost. Treat the effect boundary explicitly before possible external send. Restrict cancellation to proven zero effect plus effective fencing.
- **Alternatives:** Serialize a single mutation dispatcher per router using the established engine; this still needs correct DB fencing and cannot replace it.
- **Acceptance:** Two-connection tests expire/revoke lease while an old worker runs; stale worker cannot write progress, result, success, retry or terminal state. Cancellation during send cannot report safe cancellation. No terminal state resurrection.
- **Sequence:** Before enabling real router mutations or increasing worker concurrency.
- **Downtime/rollback:** Drain mutation jobs before worker version switch. Preserve uncertain jobs for readback; reverting the worker cannot undo external effects.

### DB-03 — Entire worker handler runs inside a database transaction; crash recovery omits early claimed states

- **Priority:** **P1 — High**.
- **Status:** **CONFLICT**, statically established.
- **Evidence:**
  - `backend/domains/jobs/engine.py:222`: `run_claimed` wraps preflight, execute and verify in `tenant_scope`.
  - `backend/domains/common/tenant_context.py:51–54`: that scope opens `transaction.atomic()`.
  - Therefore handler external I/O and job state updates remain inside that outer transaction.
  - `engine.py:340–343`: expiry reconciliation selects only executing/verifying.
  - `backend/domains/jobs/management/commands/runworker.py`: synchronous handler loop; no independent periodic heartbeat/drain mechanism in this command.
- **Impact:** Long transactions hold locks and obscure progress from other connections. A process crash can roll back executing/verifying state to the previously committed claimed state; that state is not recovered by the current reconciler. Stored deadlines alone do not establish execution deadline enforcement.
- **Smallest fix:** Use bounded tenant-scoped transactions for claim, preflight decisions, effect reservation, and outcome writes; perform external I/O outside those transactions, then re-establish scoped transactions. Recover claimed/preflight leases as safe/no-effect only when proven; executing ambiguity goes to uncertain/readback. Establish heartbeat and deadline handling.
- **Acceptance:** Separate connection sees committed transitions while handler is paused; database transaction is absent during network wait; kill worker in each state, then prove bounded recovery, no duplicate external mutation and truthful uncertain outcomes. Verify lease/deadline behavior for operations exceeding 30 seconds.
- **Sequence:** Together with DB-02.
- **Downtime/rollback:** Drain workers; backward compatibility for stored job payload/state required. Do not blindly replay uncertain jobs after restart.

### DB-04 — Outbox dispatcher acknowledges events without delivering them

- **Priority:** **P1 before adding event-dependent finance/Tax**, otherwise explicitly limited scaffold.
- **Status:** **PARTIAL**.
- **Evidence:** `backend/domains/jobs/engine.py:406–417` selects pending events and sets `dispatched_at`/attempts; comment explicitly says real endpoints arrive with their features. No consumer dispatch is performed there.
- **Impact:** Domain state plus outbox insertion can be atomic, while delivery is still absent. Future ledger, Tax or notification modules must not interpret current `dispatched_at` as proof that a consumer completed work.
- **Smallest fix:** Before introducing the first real consumer, implement its explicit delivery/acknowledgment and replay behavior in the existing engine. Preserve immutable source events and define backfill for events previously acknowledged by the placeholder.
- **Avoid:** New broker, generic event platform, exactly-once claims.
- **Acceptance:** Crash before/after business commit, consumer commit and acknowledgment; replay produces one logical consumer effect through durable business deduplication. Failed deliveries remain recoverable. Multiple dispatchers do not lose delivery ownership.
- **Affected modules:** Jobs, subscriptions, billing, future finance/Tax/documents notifications.
- **Sequence:** Before any feature relies on outbox delivery.
- **Downtime/rollback:** Pause dispatcher for rollout if required. Reverting code does not replay marked events; recovery requires a deliberate source-event/backfill plan.

### DB-05 — Idempotency implementation omits principal from identity and lacks concurrent-request handling

- **Priority:** **P1 for money/network operations**.
- **Status:** **CONFLICT**.
- **Evidence:**
  - `backend/domains/common/idempotency.py:53–55`: scope is operation + tenant + resource.
  - `:61`: lookup uses scope/key only.
  - `:70–75`: principal is recorded but is not part of lookup identity.
  - `backend/domains/jobs/models.py:219` onward: unique identity is scope/key.
  - `idempotency.py:67–68`: a record without response allows execution again.
- **Impact:** Two authorized actors with the same key collide or replay each other’s operation instead of following the documented principal scope. Concurrent identical-key insertion can fail rather than return one logical action. Incomplete response recovery is not a generic proof of safe re-execution.
- **Smallest fix:** Include trusted principal in identity, and serialize/reconcile concurrent requests using the existing DB. Preserve business uniqueness beyond seven-day key retention. Define operation-specific interrupted-request recovery.
- **Acceptance:** Same actor/key/body replay; different body conflict; different actors follow documented independent scope; two concurrent identical requests yield one logical action; connection loss after durable business write does not duplicate money or provisioning.
- **Sequence:** After DB-01, before widening mutation use.
- **Downtime/rollback:** Schema constraint/scope transition may require additive migration and a defined old-key compatibility window. No wholesale deletion of existing idempotency records.

### DB-06 — RADIUS projection relationships lack several documented composite tenant foreign keys

- **Priority:** **P1 tenant-data invariant gap**.
- **Status:** **PARTIAL / CONFLICT**.
- **Evidence:**
  - `backend/domains/radius/migrations/0001_radius_schema.py`: single-column router/account/service references in NAS (`27`), radcheck (`41`), radreply (`55`), group reply (`73`) and accounting (`89–90`).
  - RLS checks each row’s tenant, while those references do not prove the referenced parent belongs to the same tenant.
  - `radius/0004_cutover_run_rls.py:23–26` demonstrates a composite tenant/router FK for cutover only.
- **Impact:** Application mistakes may persist cross-tenant parent references despite a tenant-scoped insert. This is a database invariant failure, not proof of an exposed API exploit.
- **Smallest fix:** Inventory each tenant-bearing reference, add the missing `(tenant_id,parent_id)` constraints where ownership requires them, and explicitly justify true shared/global references. Precheck old data before validation.
- **Acceptance:** Direct negative PostgreSQL INSERT/UPDATE tests for each projection reference reject tenant-A row → tenant-B parent, while valid same-tenant projections and daemon accounting continue.
- **Sequence:** Before extending tenant modules and production isolation approval.
- **Downtime/rollback:** Review lock duration on populated `radacct`; stage validation rather than assume an instantaneous ALTER. Constraint removal does not repair bad historic references.

### DB-07 — Enrollment completion is not serialized or atomic with verification-job creation

- **Priority:** **P1 — High**; security reviewer should assess combined identity impact.
- **Status:** **CONFLICT**, statically established.
- **Evidence:**
  - `backend/domains/network/services.py:735`: token lookup without row lock occurs before tenant transaction.
  - `:746–756`: replay/state decisions use that previously read object.
  - `:758–785`: enrollment consumption and peer update occur in tenant transaction.
  - `:789`: verification job is created **after** the transaction exits.
  - `backend/domains/network/views.py:222`: callback is a plain APIView, not an enclosing `TenantApiView`.
  - `services.py:752–753`: replay returns without repairing a missing verification job.
- **Impact:** Crash between consumption commit and job creation leaves a consumed token/bootstrapped enrollment without durable verification work. Concurrent callbacks can both pass stale status checks; different identities can race to overwrite state.
- **Smallest fix:** Resolve then lock/re-read the enrollment in its trusted tenant transaction; serialize identity/replay decisions and create the deduplicated verification job/outbox atomically with token and peer state. Always restore special lookup context on error.
- **Acceptance:** Two concurrent callbacks with same token/key produce one logical job; different keys produce one winner and conflict without overwritten identity. Inject crash at every boundary; persisted accepted bootstrap always has durable follow-up or explicit recovery.
- **Sequence:** Before treating router onboarding as production-safe.
- **Downtime/rollback:** Application patch, ideally additive uniqueness if needed; preserve existing peers and reconcile stranded enrollments without regeneration of trusted identities.

### DB-08 — Backup verification resolves the newest staging artifact, not the artifact created by that job

- **Priority:** **P2 now; P1 before real concurrent backup release**.
- **Status:** **PARTIAL**, race not executed.
- **Evidence:**
  - `backend/domains/backups/service.py:166–182`: generation from `MAX+1`, then artifact created.
  - `:223`: execution returns artifact ID.
  - `:236–244`: verifier instead selects newest generating artifact for router/category.
  - `:118–129`: current stored file is simulator metadata manifest; receiver/physical cleanup are explicitly deferred.
- **Impact:** Concurrent jobs can race generation or verify another job’s artifact. A committed simulator manifest is not a restorable RouterOS binary or a platform database backup.
- **Smallest fix:** Persist exact job→artifact identity and verify that artifact; serialize generation allocation using an existing owner row/constraint and retry policy. Keep simulator evidence explicit until real transfer/checksum/recovery is verified.
- **Acceptance:** Two concurrent backups of same router/category never cross-commit artifacts; crash at staging/commit/prune retains last recoverable generation; verify actual bytes/hash/manifest for real adapter.
- **Sequence:** Before enabling real backups beyond current pending-lab capability.
- **Downtime/rollback:** Pause backup jobs for transition if necessary. Never prune the last recoverable generation during rollback.

## Positive controls and their limits

- `common/migration_sql.py` creates FORCE RLS and composite FK helpers with reverse SQL: **IMPLEMENTED**.
- `tenant_context.py` uses transaction-local tenant setting and restores nested scope: **IMPLEMENTED**; comprehensive pooled error/rollback behavior is **UNVERIFIED** in this review.
- `billing` separates payment recording, verification and service activation: **IMPLEMENTED** in examined source; payment does not automatically activate service.
- Billing uses Decimal and database uniqueness/nonnegative checks: **IMPLEMENTED**, insufficient to close DB-01.
- SaaS subscription/source-event tables and Internet billing tables are separate: **IMPLEMENTED**; full separate accounting books are **DOCUMENTED / NOT IMPLEMENTED** in examined domain inventory.
- Issued documents and platform source events have immutability triggers: **IMPLEMENTED**.
- `grant_runtime` iterates **all non-system schemas** granting runtime DML: **IMPLEMENTED**. Future posted ledger tables must be explicitly excluded/revoked according to `ARCHITECTURE §8`; merely creating a ledger schema would not establish privilege safety.
- No `backend/domains/ledger`, `finance`, or `tax` implementation was identified. `docs/planning_mvp/` is **NOT FOUND** on baseline. Tax compatibility must remain a proposed ownership contract, not an asserted implemented capability.

## Testing assessment

No tests below were executed.

| Area | Existing source evidence | Coverage limitation / next proof |
|---|---|---|
| RLS | `tests/integration/test_rls.py` tests empty/wrong/right/nested context, job-detail composite FK, no superuser/BYPASSRLS | Tests run as test DB/table owner; add actual separate migrator/runtime deployment permissions, error/commit/rollback and reused connection matrix, all tenant relationships. |
| Jobs | `test_jobs_engine.py` tests sequential success, timeout, retry, cancellation, manual expiry | No demonstrated two-worker stale lease, real cancellation race, kill-and-restart in every state, long I/O outside transaction or graceful drain proof. |
| Payments | `test_billing_payments.py` tests partial, excess credit, over-allocation rejection, replay and permissions | Sequential tests do not exercise DB-01. Add separate-connection concurrent payments and invoice lock-order tests. |
| Invoice issuance | `test_billing_invoice_flow.py` and calendar unit tests | Need concurrent scheduler evidence and immutable issued-state regression under compatible upgrade. |
| RADIUS | `test_radius_projection.py`, `test_radius_facade.py`, cutover tests, separate daemon harness | Preserve daemon/runtime role split; add missing composite reference negatives, real network workflow and rollout compatibility. |
| Router backup | `test_ops_backups.py` | Simulator pipeline tests do not prove physical transfer/restore; add concurrent artifact attribution and crash boundaries. |
| Platform recovery | `instalasi.sh:628–630` dumps DB and runs `pg_restore --list` | Archive listing is not full restore verification; no full key+blob+DB+RADIUS+VPN recovery drill executed. |
| Outbox | Atomic insertion visible in services | Dispatcher placeholder cannot satisfy delivery/replay consumer gates. |

Tests declaring PostgreSQL integration are valuable, but fixtures (`backend/tests/conftest.py:5–6`) explicitly create the test database/tables as the app role. FORCE RLS can still work there; that test environment does not establish production ownership and privilege separation.

## Upgrade, migration and recovery requirements

These are implementation recommendations, not executed changes.

1. **Expand/migrate/contract:** Add compatible fields/constraints first. Deploy code that tolerates old/new representations. Backfill in bounded, restartable batches. Validate before making stricter requirements. Contract only after old code, worker payloads and rollback window no longer need the old representation.
2. **Migration ownership:** Domain owning a table owns its migration. Cross-domain FK additions need both owners’ review and explicit dependency ordering. Do not edit already-applied migrations to repair deployment drift.
3. **Locks and large tables:** Inspect generated SQL, row count, index needs and lock budget for accounting/health/audit/job tables. Consider staged constraint validation and concurrent index operations where justified; do not introduce partitioning solely because of the million-client design target.
4. **Version window:** Specify supported application N/N−1 schema and job-payload versions for each release. Old workers must drain or be proven compatible before schema activation.
5. **Rollback:** Application rollback is not schema reversal or restoration of external device effects. Some current reverse SQL drops schemas/tables or replaces facade bodies; its existence is not proof of production rollback safety.
6. **Backup scope:** DB business/RADIUS/future ledger plus blobs, encryption key versions, app/daemon configuration and VPN/NAS state. Full backup must use an authorized role that actually covers every tenant.
7. **Restore proof:** Isolated restore with role recreation/privileges, counts/integrity, decryptability, document/blob checks, RADIUS configuration/auth checks, retained router identities and suppressed mutation workers until reconciliation completes.
8. **Acknowledged writes:** Zero loss during normal upgrade requires quiescence or durable replay/reconciliation. Restoring the pre-upgrade dump after accepting new payments loses those writes unless captured/reconciled; RPO≤15 minutes is not a zero-loss claim.
9. **Worker recovery:** Stop claims, drain bounded tasks, record uncertain/in-flight effects, then switch code. Do not declare stopped process = safely cancelled task.
10. **Tax readiness:** Billing owns commercial invoice/payment facts; subscriptions owns operator SaaS facts; finance owns postings/books; Tax owns versioned assessment/submission state; documents owns immutable output; jobs transports durable work; tenancy supplies trusted scope. Require explicit economic entity/book identity and source-event dedup, never platform `tenant_id=NULL` as an RLS bypass.

## Commands, outcomes and limitations

Read-only commands used: `git status --short`, `git rev-parse HEAD`, `rg --files`, targeted `rg -n`, `cat`, numbered `nl -ba`/`sed` reads, and a Python `pathlib` count of migration filenames.

- Baseline HEAD resolved as stated.
- Initial working tree was clean.
- Numbered migration count: 39 across 11 apps.
- Some exploratory globs such as `test_backup*` returned no matching file; actual backup suite is `test_ops_backups.py`.
- All runtime tests, migration runs, installers, restore drills, remote deployment checks and benchmarks: **NOT RUN**, intentionally outside read-only scope.
- No credentials accessed or included.
- No repository file written by this reviewer.

## Independent disposition and next steps

**REQUEST CHANGES to any claim that code is already safe for production financial concurrency, fenced job recovery, atomic enrollment completion, or delivered outbox processing.**

Planning documents should include DB-01 through DB-08, narrow implementation plans and explicit evidence gates. The next implementation session should address DB-01 first, then worker/enrollment safety, without adding brokers, microservices, generic repositories or new transaction frameworks.

The review supports retaining PostgreSQL and the existing modular-monolith/job architecture. It does not support declaring those safety properties complete until the listed failure and concurrency tests produce actual evidence.
