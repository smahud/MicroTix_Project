# Independent Architecture and Frontend Review — MicroTix Planning Audit

- **Author / role:** `/root/architecture_review` — Independent Architecture and Frontend Reviewer.
- **Objective:** Assess actual modularity, ownership, dependency direction, maintainability, frontend contracts, and extension safety.
- **Repository:** `smahud/MicroTix_Project`.
- **Local checkout:** `/workspace/scratch/9459f0c7494a/MicroTix_Project`.
- **Starting branch:** `docs/planning-audit-20261110`.
- **Audited baseline:** `16085f825fef25ee4112d74b729c57e623b0bb05` — canonical `main`.
- **Date:** 2026-11-10.
- **Changes:** None. Static read-only review.
- **Reviewer commit / remote status:** NOT PUSHED. The orchestrator must persist this handoff under `report/architecture-review/<UTC>-planning-audit.md`, as permitted by CONTRACT §10.
- **Completion:** Static review complete. Runtime verification remains unperformed.

## Verdict

Retain the modular monolith. The code already contains useful domain services, typed RouterOS adapters, PostgreSQL tenant context, durable job records, RLS migrations, document integrity checks, lazy frontend routes, and a shared typed frontend API interface.

However, domain directories do not currently provide consistently enforced ownership. Several feature and reliability contracts remain incomplete. The strongest blockers identified here are payment allocation concurrency, quota concurrency, import selection loss, and actor-independent idempotency.

**Planning assessment: READY WITH CONDITIONS**, provided the finalized documents explicitly preserve these unresolved implementation defects and require their acceptance evidence. **Release assessment: NOT READY** based on this static review; no runtime or lab claim is made.

Open SSTP PR #7 at `d7fa35e5583bc36848e3b45497d2511739298c8a` must remain separate from implemented-on-main claims.

## Reviewed requirements and evidence

Read CONTRACT.md, docs/ARCHITECTURE.md, PRODUCT.md, FINANCE.md, IMPLEMENTATION_PLAN.md, ACCEPTANCE.md, and relevant test-cases.json structure. Applicable requirements include ARCHITECTURE §§1–6; SUB-02; BIL-01/03/08; IMP-02/03; UX-02/04; T02, T05, T10, T18; and the requirement→implementation→test→evidence chain.

Static inventory inspected all domain Python imports and model declarations, plus service/view/handler paths in customers, subscriptions, billing, network, radius, jobs, documents, backups, identity, monitoring, common, config, tenancy, audit, and i18n. Frontend inspected API contracts/client/http/live adapter, router composition, session state, permissions/release flags, imports, billing, activation, and customer feature flows. Related backend contract and integration test sources were inspected.

`docs/planning_audit/` and `docs/planning_mvp/` are **NOT FOUND on main**. Tax compatibility cannot be verified against absent planning_mvp contents. No such contents were invented.

## Domain inventory and ownership

There are **15 actual backend domain directories**.

| Domain | Actual ownership / implementation | Assessment |
|---|---|---|
| identity | User, TOTPDevice, RecoveryCode, LoginAttempt, EmailToken, SupportGrant; authentication, MFA, verification | IMPLEMENTED; tenant creation and initial subscription are legitimate onboarding orchestration |
| tenancy | Tenant, Membership, role permissions | IMPLEMENTED; foundation metadata owner |
| subscriptions | PlanVersion, Subscription, QuotaReservation, SaaSInvoice, PaymentSubmission, PlatformPaymentSourceEvent | PARTIAL; platform economic flow separate from tenant internet billing; quota concerns below |
| customers | Customer, Service, AccessAccount, CsvImport, MigrationSession, MigrationAccountDecision | PARTIAL; owns service/account lifecycle; mutates network discovery records |
| network | Router, RouterHealthSample, RouterEnrollment, WireGuardHost/Peer, DiscoverySnapshot/Object, DeviceOperation | PARTIAL; RouterOS/WireGuard support exists; discovery mutates customer migration sessions |
| radius | NAS and RADIUS projection/accounting models, CutoverRun; projection and cutover | PARTIAL; synchronous signal projection, router-state writes, lab prerequisites |
| jobs | Job, JobDetail, OutboxEvent, IdempotencyKey; shared worker engine | PARTIAL; foundation used broadly; outbox delivery not implemented |
| backups | BackupArtifact, BackupSchedule; backup handler | PARTIAL; operational/recovery verification belongs to separate review |
| billing | BillingPackage, ServiceCharge, InternetInvoice/Line, InternetPayment, PaymentAllocation | PARTIAL; tenant internet financial flow exists; allocation race and ownership problems |
| documents | IssuedDocument; restricted PDF render, immutable snapshot, artifact hash verification | IMPLEMENTED subset; rendering inside billing transactions adds coupling |
| audit | AuditEvent and redacted record helper | IMPLEMENTED foundation |
| monitoring | Read-only aggregation of network health samples | PARTIAL; interfaces empty, RADIUS block null; no full monitoring pipeline established here |
| config | Defaults/branding registry, health/meta endpoints; seed/grant commands | IMPLEMENTED foundation |
| common | Tenant scope, API base views/errors/pagination/idempotency/crypto | IMPLEMENTED foundation with reverse dependencies |
| i18n | Catalogs and enums | IMPLEMENTED foundation |

No `finance`, `ledger`, `tax`, `access`, `ACS`, or `OLT` domain directory exists at this baseline. Some are documented future phases, rather than missing mandatory work for every R1 commit. Current access-account ownership is customers, not the example `access` directory named in ARCHITECTURE §1.

## Dependency map

The following imports were derived using Python AST, excluding migrations and management commands. The map includes deferred imports and AppConfig composition imports; it does not imply every edge is a business dependency.

| Source | Other domains imported |
|---|---|
| audit | common |
| backups | common, config, jobs, network, tenancy |
| billing | audit, common, customers, documents, jobs, subscriptions, tenancy |
| common | i18n, identity, jobs, tenancy |
| config | common, i18n |
| customers | audit, common, jobs, network, subscriptions |
| documents | common, i18n |
| identity | common, i18n, subscriptions, tenancy |
| jobs | common |
| monitoring | common, config, network |
| network | common, config, customers, jobs, radius, tenancy |
| radius | backups, common, customers, jobs, network |
| subscriptions | audit, common, jobs, network, tenancy |

A strongly connected component contains audit, backups, common, config, customers, identity, jobs, network, radius, and subscriptions. This reflects foundation reverse dependencies, dynamic imports, composition, and real cross-domain coupling. **It is not proof of a runtime circular-import exception.** Do not use it to justify a rewrite.

Examples of legitimate dependencies:

- identity verification calls subscription creation during initial tenant onboarding: identity/services.py:119–128.
- billing reads Customer/Service and calls documents.services.issue_document.
- monitoring reads network health.
- domain handlers call jobs.create_job.
- radius projects AccessAccount changes through a controlled synchronous hook.

Dependencies requiring restriction:

- Cross-domain ORM reads should name their purpose and fields, remain tenant-scoped, and never become ad hoc writes.
- Direct model mutations across owners and shared upload policy imported from subscriptions need targeted correction.

## Findings

### AR-01 — P1: Concurrent payments can lose invoice balance updates

**Status:** CONFLICT; code path established statically, race inferred, runtime UNVERIFIED.

**Evidence:**

- billing/services.py:587–591 locks the Payment record.
- `_parse_allocations`, billing/services.py:559–567, reads Invoice without `select_for_update`.
- billing/services.py:601–608 calculates and saves `invoice.paid_amount` from that potentially stale object.
- The tenant numbering lock at line 623 occurs after invoice mutation.
- billing/models.py:178–189 lacks an invoice `paid_amount <= total_amount` or aggregate-allocation integrity constraint.
- Existing test_billing_payments.py tests sequential overpayment and same-payment replay; source inspection found no two-connection race test.

**Risk:** Two distinct payments may each read the same outstanding amount, then overwrite the invoice balance while both allocations persist. Row locking on separate payments does not serialize their common invoice.

**Smallest fix:** Lock affected invoices in stable UUID order before checking outstanding, allocation, and balance changes. Keep payment and invoice locks plus receipt/audit/outbox in one transaction. Add a simple invariant check appropriate to the final schema.

**Alternative:** Lock the tenant before any financial balance read; simpler but serializes all tenant payments and should be assessed against actual contention.

**Affected modules:** billing, documents, future ledger/tax consumers.

**Acceptance:** Two PostgreSQL connections verify different payments against one invoice; aggregate allocations equal paid balance; over-allocation cannot occur; reversed multi-invoice input ordering does not deadlock; one failed transaction leaves no successful allocation/receipt event.

**Order / downtime / rollback:** Before billing production use. Application patch may require a short worker/API drain; any constraint addition follows expand/migrate/contract. Roll back application only within compatible schema; reconcile corrupted historical balances before claiming recovery.

### AR-02 — P1: Quota ownership is split across an unsafe lock boundary

**Status:** CONFLICT; stale-check race inferred statically, runtime UNVERIFIED.

**Evidence:**

- customers/services.py:120–136 checks committed services plus pending reservations before calling subscription reservation.
- subscriptions/services.py:125 obtains the subscription lock only later.
- subscriptions/services.py:83–89 returns zero committed services.
- subscriptions/services.py:101–103 counts reservation rows instead of summing `units`.
- subscriptions/services.py:175 reports zero service usage.

**Risk:** Parallel requests near the limit can both pass the pre-lock customer check; after the first commits, the second does not recheck actual committed services under the lock. Multi-unit reservations and displayed usage are also inaccurate.

**Smallest fix:** One quota decision under the existing subscription row lock, obtaining committed usage through an explicit customer-owned read function and summing live reservation units. Keep customer creation and reservation consumption atomic.

**Alternative:** Retain current domain ownership but move the shared lock to a narrow agreed service entry point; no registry/framework is needed.

**Affected modules:** subscriptions, customers, imports, onboarding, frontend usage.

**Acceptance:** Concurrent near-limit creation admits only remaining capacity; batch reservation counts units; expiration is deterministic; displayed committed and reserved usage matches actual records; repeated import does not double count.

**Order / downtime / rollback:** Before enabling quota-dependent paid offers. No new infrastructure. Short compatible app patch; rollback must preserve already accepted accounts and reconcile usage.

### AR-03 — P1: Import UI loses the operator's selected account set

**Status:** CONFLICT; end-to-end code path statically established, runtime NOT RUN.

**Evidence:**

- ImportRouterPage.tsx:94–103 saves selected IDs/profile map/password source only to a local draft, then calls `commitMigration` without them.
- api/live/adapter.ts:198–199 sends undefined request body.
- customers/views.py:594–614 treats missing selection, and explicit empty `[]`, as `None`.
- customers/services.py:749 and 763–766 interprets `None` as all snapshot objects.
- ImportRouterPage.tsx:53–56 loads only the first 200 discovered accounts.

**Risk:** Selecting one displayed account may adopt unselected accounts, including accounts beyond the visible first page. The preview and authorized scope differ.

**Smallest fix:** Carry selected IDs and a validated preview revision through typed frontend/API/job contracts. Preserve the semantic distinction between absent selection and empty selection. The server validates selection membership against the selected snapshot.

**Alternative:** Temporarily disable the commit action until the supported scope is represented honestly; requires explicit release decision and must not weaken product requirements.

**Affected modules:** frontend imports, customers, network discovery, subscription quota, RADIUS projection.

**Acceptance:** A 201-account snapshot with only one selected results in exactly one adopted account; an empty selection adopts none or is rejected; stale snapshot/preview conflicts; cross-tenant or unrelated selected IDs are rejected; repeat submission has one logical result.

**Order / downtime / rollback:** Before import release. Compatible app patch; no router effects. Revert code if necessary, retaining audit and explicit review of mistakenly adopted records.

**Related partial behavior:** Profile-map and password-source choices are currently stored locally; the demonstrated commit path does not implement them. Hardcoded package options occur at ImportRouterPage.tsx:324–329. Do not describe this as a fully implemented eight-step migration workflow.

### AR-04 — P1: Idempotency omits the authenticated principal

**Status:** CONFLICT.

**Evidence:**

- common/idempotency.py:53–61 builds and queries operation+tenant+resource+key, excluding principal.
- Principal is merely stored at lines 70–75.
- Response update at line 79 also omits principal.
- jobs/models.py:221 uniqueness is `(scope, idem_key)`.
- ARCHITECTURE §5 requires principal+tenant/platform+operation+resource+key.

**Risk:** Different authorized actors using the same key within the same operation scope can conflict or receive the other actor's logical response. Concurrent insertion with the same key also lacks an explicit conflict/replay wait strategy.

**Smallest fix:** Include principal consistently in uniqueness, lookup, update, retention-compatible replay, and concurrency handling. Do not cache secret/reveal response bodies.

**Acceptance:** Same actor+same key replays; same actor+changed body conflicts; different actors have independent scoped actions; concurrent equal key yields a controlled logical result, not unhandled IntegrityError; revoked permissions are checked before any replay.

**Affected modules:** Every decorated mutation; schema migration ownership belongs to jobs/common coordination.

**Order / downtime / rollback:** Before sensitive financial/provisioning flows; additive compatibility migration with an explicit old-key window. Rollback must not allow old/new code to disagree on uniqueness.

### AR-05 — P2: Model ownership is bypassed in several cross-domain flows

**Status:** IMPLEMENTED bypasses; contract enforcement PARTIAL.

**Evidence:**

- customers/services.py:647,853 mutates network.DiscoveryObject state.
- network/services.py:930–934 updates customers.MigrationSession.
- radius/handlers.py:207 updates network.Router.
- billing/views.py:226–237 directly assigns customers.Service.billing_package.
- subscriptions quotas read network.Router; cross-domain read itself is legitimate.

**Risk:** Owner invariants, revisions, audit hooks, and future changes can be bypassed. Bidirectional business writes increase regression scope.

**Smallest fix:** Introduce only the narrow functions already needed, e.g. network-owned discovery state transition, customer-owned migration-discovery completion and billing-package assignment, network-owned enforcement-mode transition. Keep orchestration in current caller and the same DB transaction.

**Alternative:** Formally document a constrained transaction coordinator exception with named models/fields and tests; do not permit unrestricted ORM mutation.

**Acceptance:** New unauthorized cross-owner mutation fails review/static allowlist checks; approved service boundary tests preserve RLS, state transitions, revisions, audit, and rollback.

**Order / downtime / rollback:** Target only touched paths after P1 defects; no bulk service abstraction or file-count refactor. Compatible code-only changes, usually no separate data migration.

### AR-06 — P2: Synchronous RADIUS projection is an implicit internal contract

**Status:** IMPLEMENTED mechanism, DOCUMENTED invariant, enforcement PARTIAL.

**Evidence:** radius/apps.py:8–27 registers post_save/post_delete AccessAccount projection with `weak=False`, within the business transaction.

**Risk:** Future bulk_create/update/queryset update can bypass signals; maintainers may not know a model save writes a different schema. Renaming or removing the hook can break authorization projection.

**Smallest fix:** Record this as a deliberate synchronous projection contract; prohibit signal-bypassing writes for projected fields unless an explicit projector call occurs. Test projection rollback when business transaction fails.

**Alternative:** Later move explicit calls into the few customer-owned mutation functions when modifying those paths. A separate event bus is unnecessary and could weaken atomicity.

**Acceptance:** Every account credential/state/revision operation updates radius projection in the same transaction; bulk operations are covered or rejected; no signal fires twice; failed projection rolls back owner mutation.

**Downtime / rollback:** None for documentation; later compatible service patch with projection reconciliation evidence.

### AR-07 — P2: Shared storage policy is coupled to subscriptions, and artifacts can become orphaned

**Status:** IMPLEMENTED coupling; cleanup PARTIAL.

**Evidence:**

- billing/services.py:54 imports MIME/size helpers from subscriptions.upload.
- billing/services.py:497 writes proof before validating the claimed MIME at 498–501.
- billing/services.py:447–468 writes opaque proof files; later validation/DB failures lack removal.
- documents/services.py:100–102 intentionally writes artifact before its DB row; line 69 mentions a future janitor.
- Billing renders PDFs inside invoice/payment transactions and tenant numbering locks.

**Risk:** Upload policy changes in SaaS unexpectedly alter tenant billing; failed actions leave private orphan files; rendering latency extends locks and financial transactions.

**Smallest fix:** One narrow shared storage/upload helper with existing consumers; validate before write; define orphan cleanup by age and DB reference; measure rendering transaction duration before moving rendering asynchronous.

**Alternative:** Retain duplicated adapters briefly but centralize only policy constants and scanner behavior, with parity tests.

**Acceptance:** Invalid MIME/duplicate/rolled-back transaction leaves no live orphan after defined retention; artifact hash checks preserved; render failure gives one transaction outcome; no user-supplied arbitrary filesystem/network access.

**Order / downtime / rollback:** Before heavy document volume and new tax documents; no generic repository/storage framework. Code-only change with preserved opaque paths.

### AR-08 — P2: Frontend live service filters are silently discarded

**Status:** CONFLICT.

**Evidence:** api/live/adapter.ts:123–124 accepts `_filters` but sends only pageQuery. CustomersPage.tsx:54–67 supplies search, router, connection, quick_tab, and incomplete_mapping. Backend customers/views.py:205–271 implements corresponding filter behavior.

**Risk:** UI appears filtered while data remains unfiltered; operational selection or billing interpretation can be wrong.

**Smallest fix:** Serialize supported filter values to query parameters in the existing adapter.

**Acceptance:** Live adapter test asserts actual query parameters; browser/API test proves router/search/incomplete filters return the same intended set; unknown filters follow 422 contract.

**Downtime / rollback:** No migration; normal frontend release. Revert bundle if required.

### AR-09 — P2: Local migration drafts are not namespaced by tenant/router

**Status:** CONFLICT; latent cross-scope API behavior.

**Evidence:** api/live/adapter.ts:184–193 ignores tenantId/routerId, stores `mt-migration-draft-{id}`, and returns the first matching localStorage item. SessionProvider cache clearing at state/session.tsx:44–50,79–82 does not clear localStorage.

**Risk:** Future/current callers can restore another tenant/router's cached migration metadata; logout on a shared browser leaves it behind. No server-side cross-tenant leak is claimed.

**Smallest fix:** Tenant+actor+router/session namespace, identity validation when loading, and clear/invalidate on logout/tenant switch according to the documented retention policy.

**Acceptance:** Two tenants with identical router display names never restore each other's draft; logout removes protected local drafts; malformed/obsolete stored JSON fails closed.

**Downtime / rollback:** Frontend patch; invalidate legacy unscoped draft keys without deleting server records.

### AR-10 — P2: API and feature-gate tests do not establish full behavioral compatibility

**Status:** PARTIAL.

**Evidence:**

- backend/tests/contracts/test_api_contract.py, test_customers_contract.py, test_billing_contract.py mainly verify path presence/methods/key sets plus selected status behavior.
- Many view `extend_schema` annotations provide summaries without explicit request/response serializers.
- app/App.tsx directly defines routes; release flags are primarily consumed in navigation and widgets.
- RELEASE_FLAGS is a static frontend object, not a server-side authorization control.

**Risk:** A schema rendering and endpoint-presence PASS does not protect semantic inputs, status behavior, permissions, feature-disabled direct routes, or migration selection. A frontend flag must not become a permission boundary.

**Smallest fix:** Add risk-focused request/response/status/error/permission and live adapter contract assertions; ensure disabled features have intentional direct-route and API behavior. No new schema framework is necessary.

**Acceptance:** Contract fixtures cover new fields, omitted/null/empty meanings, actor/tenant scope, disabled feature direct navigation/API access, idempotent retry, and old client compatibility. Breaking change requires explicit version/migration plan.

**Downtime / rollback:** None for test planning; later bundle/API compatibility window.

## Frontend maintainability assessment

Positive evidence:

- App.tsx:8–30 uses route-level lazy loading already.
- Feature folders are mostly independent; searched imports found no direct sibling-feature imports.
- Shared primitives/components/API/i18n/permissions/session layers exist.
- tsconfig.app.json enables strict typing and noUncheckedIndexedAccess.
- ApiClient defines typed operations; HTTP normalizes error envelopes.
- Production API mode has a guard against mock use.
- TanStack Query keys commonly include tenant ID.

Needed boundaries:

- Keep feature UI dependent on typed API contracts, not another feature's internal state.
- Do not split the shared API interface or large feature solely by line count.
- Put reusable business rules in existing lib functions where there are real users, as done for billing eligibility.
- Persist idempotency keys for the lifetime of a logical action, including ambiguous manual retries; live adapter currently creates a new UUID when caller supplies none.
- Shared UI primitives such as DataParts currently know billing release policy; consider moving only concrete business widgets into their owner when changed.
- Tenant route changes can reuse mounted component state; add explicit reset/keying for selection, dialogs, and protected data. Cache removal alone is not proof all local state resets.

## Architecture extension and Tax boundaries

Retain:

1. One backend codebase and PostgreSQL transaction boundary.
2. Customer-owned service/account truth; network-owned device/enrollment/discovery truth.
3. subscriptions as the operator's SaaS economic flow; billing as tenant internet receivables.
4. documents as immutable rendered snapshots, not tax/accounting decision maker.
5. jobs as durable execution infrastructure, not owner of billing, tax, or entitlement policy.
6. Small typed external adapters.
7. Aggregate monitoring plus targeted client real-time monitoring; no inference that one million clients are polled continuously.

Future tax integration must identify the legal/economic entity and book explicitly. A SaaS invoice's tenant payer identifier does not make its transaction a tenant internet sale. `PlatformPaymentSourceEvent` and `InternetPayment` should feed separately owned books/documents through explicit source-event contracts. Documents must preserve issuer, recipient, currency, tax/version metadata, source linkage, and immutable snapshots once the tax design is approved.

The absence of planning_mvp and tax/ledger code prevents checking its concrete schema or regulatory behavior. Do not infer implementation or invent Coretax endpoints.

## Commands, results, and limitations

Executed read-only:

- `cat`, `nl -ba`, `sed -n`, and `rg` on the paths described above.
- Python `ast.parse` over **225 backend Python files**: **0 syntax parse failures**.
- AST import inventory excluding migrations/management; strongly connected component calculation.
- Static model/table/FK inventory.
- Static frontend import/release-flag/query/client inspections.
- Static contract and integration test-source inspection.

Not executed:

- pytest, Django checks, migration application, PostgreSQL concurrency/RLS tests.
- pnpm install, TypeScript compiler, lint, Vitest, Playwright.
- RouterOS, CHR/GNS3, FreeRADIUS, deployment, upgrade, backup/restore.
- No dependency installation, application mutation, DB mutation, or repository edits.

AST parse success is not application correctness or a test-suite PASS. All race/exploit consequences above remain runtime UNVERIFIED even where the missing lock/scope code is directly observable.

## Next steps

1. Persist this report and integrate evidence into planning_audit findings.
2. Require controlled acceptance evidence for AR-01–04 before enabling affected flows.
3. Establish narrow model ownership contracts for AR-05 and preserve synchronous projection invariants.
4. Plan AR-07–10 as bounded patches to touched paths, not a broad refactor.
5. Separately review PR #7 and real-host/lab gates; do not merge them into main evidence.
6. Have an independent documentation reviewer check that readiness, main versus PR state, proposed changes, and NOT RUN tests remain explicit.
