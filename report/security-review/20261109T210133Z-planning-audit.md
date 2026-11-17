# Independent Security & Tenant Isolation Review

- **Author/role:** `/root/security_review` — independent Security Reviewer.
- **Objective:** Static audit of tenant isolation, authorization, session/MFA, credential boundaries, private storage and future module requirements.
- **Starting branch:** `docs/planning-audit-20261110`.
- **Baseline:** `main` at `16085f825fef25ee4112d74b729c57e623b0bb05`.
- **Repository:** `smahud/MicroTix_Project`.
- **Suggested report path:** `report/security-review/20261109T210032Z-planning-audit.md`.
- **Report persistence:** Orchestrator must persist this complete handoff under CONTRACT §10; reviewer was assigned read-only access and wrote no files.
- **Remote status:** **NOT PUSHED** by this reviewer.
- **Completion:** Static review completed; **REQUEST CHANGES before affected production workflows are enabled**.
- **Runtime verification:** No tests, database operations, deployments, installers or service operations executed.

The existing tenant-scoped view and PostgreSQL RLS mechanisms are material implementation evidence. They do not establish that authorization and isolation are complete across jobs, privileged processes, support access and exceptional paths. No cross-tenant exploit was executed or demonstrated during this review.

## 1. Requirements and inspected evidence

Primary requirements: CONTRACT §§2–4, 8–10; ARCHITECTURE §§2–7; ACCEPTANCE T10/T19/T20 and G2; ROUTEROS enrollment/download requirements; RADIUS facade requirements; FINANCE ACC-06/ACC-12 and separation of tenant/platform books. The test catalogue contains relevant requirements for membership, per-object scope, context reuse, before-send permission changes, backup authorization and immutable accounting evidence.

Inspected implementation paths:

- `backend/domains/common/{views,tenant_context,middleware,migration_sql,crypto}.py`.
- `backend/domains/tenancy/{models,permissions}.py`.
- `backend/domains/identity/{models,services,views,authentication}.py` and identity migrations.
- `backend/domains/audit/{models,views}.py` and RLS migration.
- `backend/domains/jobs/{engine,models,views}.py`, job RLS migration and `runworker.py`.
- `backend/domains/network/{services,views,handlers}.py`, enrollment bridge policy, M3 RLS/composite migration.
- `backend/domains/customers/handlers.py` and selected audit call sites in customer services/views.
- `backend/domains/subscriptions/{views,services,upload}.py`.
- `backend/domains/documents/{services,views}.py` and immutable/RLS migration.
- `backend/domains/backups/{service,views,urls}.py`.
- `backend/domains/radius/{views,handlers,projection}.py`, schema/facade/session-list migrations and `setup_radius.py`.
- `backend/microtix/settings.py`, PostgreSQL development bootstrap, `grant_runtime.py`.
- Installer credential creation and API/worker unit generation at `instalasi.sh:153–192,275–315`.
- `backend/tests/integration/{test_rls,test_jobs_engine,test_auth_flow,test_documents_api,test_ops_platform_admin,test_ops_backups}.py`.
- `backend/tests/unit/test_audit_permissions.py`, test client configuration.
- `backend/adapters/routeros/apiclient.py`, TLS/pin handling.
- Relevant sections of authoritative documents listed above.

`docs/planning_mvp/` is absent on this baseline. Compatibility with unseen Tax planning documents is **UNVERIFIED**. The SSTP work in PR #7 is unmerged and is not counted as implemented on `main`.

## 2. Implemented controls worth preserving

| Control | Evidence | Assessment |
|---|---|---|
| Membership before tenant handler execution | `common/views.py:33–44,101–118` | **IMPLEMENTED**: authenticated membership and role check precede `tenant_scope`. |
| Non-member generic 404 | `resolve_membership`, resource scope comparisons | **IMPLEMENTED** in inspected paths; comprehensive endpoint coverage remains unverified. |
| Transaction-local tenant GUC and nested restoration | `common/tenant_context.py`, `test_rls.py:40–58` | **IMPLEMENTED**; existing tests cover normal/nested exit. Exceptional/pool combinations require broader evidence. |
| ENABLE + FORCE RLS helper | `common/migration_sql.py:34–47` | **IMPLEMENTED**; coverage must be checked per table and exception, not inferred from the helper’s existence. |
| Composite foreign-key mechanism | `migration_sql.composite_fk`, domain migrations, `test_rls.py:61–70` | **IMPLEMENTED** for selected relations; one negative test does not prove all tenant references. |
| CSRF for anonymous and authenticated unsafe requests | `identity/authentication.py:24–36` | **IMPLEMENTED** in source. Existing general fixture disables CSRF checks; separate strict-client evidence is needed. |
| Tenant-sensitive step-up | `common/views.py:63–86`, `identity/services.py:356–379` | **IMPLEMENTED** for views using the permission hook; job and platform gaps below. |
| Private document storage and immutable reprints | `documents/services.py`, immutable migration, `DocumentArtifactView` | **IMPLEMENTED**: opaque files, 0600, hash check and tenant-scoped lookup. Physical storage shares a service principal; do not claim host-level isolation per tenant. |
| Email verification token consumption | `identity/services.py:104–129` | **IMPLEMENTED** with atomic transaction and row lock; useful existing pattern for other single-use credentials. |
| Separate SaaS and tenant payment flow | subscription platform endpoints and billing endpoints | **PARTIAL** economic/authorization separation; future platform/tenant ledger remains a separate requirement. |

## 3. Findings

### SEC-01 — Runtime processes receive migrator credentials

**Priority:** P1
**Status:** **CONFLICT** with ARCHITECTURE §4 privilege separation; statically confirmed configuration, exploitation untested.

**Evidence:** `instalasi.sh:174–191` writes `DATABASE_URL`, `MIGRATE_DATABASE_URL`, `MT_PG_PASSWORD_MIGRATOR` and application secrets into one environment file owned by root and the runtime group, mode 0640. Both API (`:285`) and worker (`:308`) load that file.

**Impact/preconditions:** The default application connection uses `mtx_app`, but a compromised application process also possesses the schema-owner credentials. This undermines the intended migration/runtime boundary. It does **not** mean `mtx_app` itself has BYPASSRLS, nor does this review establish an unauthenticated exploit.

**Smallest fix:** Separate runtime environment from root-only installation/migration credentials. Pass migration credentials only to bounded privileged maintenance steps. Retain separate PostgreSQL roles.

**Alternative/cost:** Keeping one file avoids work but does not meet the boundary; no new service or secret-management platform is needed.

**Acceptance:** API and worker environment/file-access tests cannot retrieve migration credentials; runtime cannot connect as migrator, create/alter objects or obtain unapproved role membership. Upgrade still migrates using its dedicated credentials, preserves secrets and restores permissions on failure.

**Affected modules/order:** Installer, all runtime domains, future ledger; fix before production privilege assertions or ledger implementation depend on this separation.

**Downtime/rollback:** Controlled API/worker restart is expected for environment changes. Preserve existing credentials securely; rollback must retain separation, not re-expose migrator credentials.

### SEC-02 — Job retry/cancel and execution lack operation-specific authorization

**Priority:** P1
**Status:** **CONFLICT** with ARCHITECTURE §§3,5,6.

**Evidence:**

- `jobs/views.py:70–97`: retry/cancel use `ActiveTenantApiView`, check tenant ownership and job state but do not check underlying operation permission or sensitive reauthentication.
- `common/views.py:132–147`: that base verifies active membership, not a domain permission.
- `jobs/engine.py:227–247`: worker preflight does not enforce current actor membership/permissions.
- `network/handlers.py:119–129` and `radius/handlers.py:249–254`: representative preflights check resource state, not current actor authorization.
- Existing `test_jobs_engine.py:162–183` checks a quotation permission denial, not job retry/cancel authorization.

**Impact/preconditions:** An authenticated same-tenant low-privilege member can reach retry/cancel logic for an eligible job. A queued job may proceed after its actor’s membership or permission changes. This is not a demonstrated cross-tenant exploit. Current simulator/device limitations reduce some external effects, not database authorization requirements.

**Smallest fix:** Map each implemented job kind to its owning operation permission and effect policy. Enforce that policy at retry/cancel endpoints and immediately before an effect; keep explicit, narrowly scoped service identities for legitimate system jobs.

**Acceptance:** Viewer/agent cannot retry/cancel privileged jobs; original allowed actor loses permission between enqueue and execute and the worker refuses the effect; sensitive retry requires current step-up where required. Authorized system jobs remain possible without pretending to be a user. Foreign tenant remains generic 404. Record refusals without secrets.

**Alternative/cost:** A small explicit kind-to-policy mapping reuses existing permission functions. A generic policy framework is unnecessary.

**Affected modules/order:** Jobs and every registered handler; implement before enabling additional network/financial effects.

**Downtime/rollback:** No schema downtime inherently required; drain/reassess existing queued jobs during rollout. Rollback should disable affected actions rather than restore unrestricted execution.

### SEC-03 — Platform MFA policy is not enforced when MFA is absent

**Priority:** P1
**Status:** **CONFLICT** with ARCHITECTURE §3.

**Evidence:** `identity/services.py:185–191` requires the second factor only if `user.mfa_enabled`; otherwise it establishes a session regardless of `platform_admin`. `subscriptions/views.py:142–148` verifies authenticated platform-admin status without MFA assurance. `test_ops_platform_admin.py:29–46` creates a platform admin with no MFA and force-logins the fixture.

**Impact:** A platform-admin account without configured MFA can receive a full password-only session and access the cross-tenant SaaS payment queue. This concerns platform authority, not ordinary tenant login policy.

**Smallest fix:** Enforce platform MFA at full-session establishment and privileged request entry, with a constrained enrollment/recovery path that grants no platform business access before completing MFA.

**Acceptance:** A platform admin without MFA cannot reach platform APIs using password only; confirmed MFA is required; direct calls after privilege promotion or stale session creation are also denied until assurance is established. Tenant password-only login remains as authorized in the existing contract. Tests use real login flow alongside unit-level forced sessions.

**Affected modules/order:** Identity, platform subscription/payment routes; fix before privileged platform operations.

**Downtime/rollback:** No schema requirement established. Existing platform sessions should be invalidated or revalidated at rollout. Rollback by restricting platform access, not weakening MFA policy.

### SEC-04 — Absolute session lifetime is checked only by the session endpoint

**Priority:** P2
**Status:** **PARTIAL** implementation.

**Evidence:** `identity/services.py:306–314` defines absolute lifetime. Repository search finds its request-path use at `identity/views.py:126` in `SessionView.get`; `SessionAuthentication.authenticate` and common tenant/platform bases do not enforce it.

**Impact/preconditions:** Direct business requests are not independently guarded by the stated absolute-lifetime policy. The current eight-hour Django session cookie often expires before the longer absolute limits, which mitigates the immediate path; it does not establish that idle/absolute semantics work as designed, especially if renewal is introduced.

**Smallest fix:** Enforce session-age policy at the shared authentication boundary and specify actual idle-renewal behavior. Reuse existing policy values.

**Acceptance:** A valid-cookie synthetic session with expired `auth_at` is refused by direct tenant and platform APIs without a preceding `/auth/session` call; logout clears session state. Test ordinary idle expiration and absolute expiration separately.

**Affected modules:** Identity/authentication and all APIs; no deployment architecture change.

**Downtime/rollback:** Application rollout only; no necessary data rollback. Reauthentication is an expected user-facing effect.

### SEC-05 — Enrollment lookup enables a session-scoped RLS exception without guaranteed cleanup

**Priority:** P1
**Status:** **PARTIAL**; exceptional reuse exposure is **UNVERIFIED** dynamically.

**Evidence:** `network/services.py:733–736` sets `app.enroll_bridge='on'` with `is_local=false`, queries, then sets it off with no `finally`. `network/migrations/0007_enroll_bridge_policy.py:12–15` grants SELECT visibility on all enrollment rows while that GUC is on.

**Impact/preconditions:** A query exception between the statements can leave the session-level exception enabled on a surviving/reused connection. Existing tenant filters mitigate many subsequent API reads, but the fail-closed connection invariant is broken. No actual data leak was exercised.

**Smallest fix:** Scope the exceptional lookup to one explicit transaction with transaction-local state, narrowly bounded query, and guaranteed cleanup/connection discard on failure. Do not make broad visibility the normal worker/API solution.

**Acceptance:** Inject lookup/query/serialization failures; assert bypass GUC and tenant context are reset before another tenant request uses the connection. Ordinary blank-context queries remain empty. Confirm exceptional permission cannot be used for writes.

**Affected modules:** Network enrollment and shared connection lifecycle.

**Downtime/rollback:** No expected schema downtime for state-handling correction; rollback by disabling enrollment if cleanup cannot be proven.

### SEC-06 — Router-limited membership scope is stored but not enforced

**Priority:** P1 when scoped delegation is used; otherwise P2 incomplete capability
**Status:** **PARTIAL**.

**Evidence:** `tenancy/models.py:63–64` stores `router_scope` with `null = all tenant routers`. Repository search finds it in model/migration only. `TenantPermission` checks membership role and `network/views.py` checks tenant, but neither uses router scope. Handler preflights likewise omit it.

**Impact/preconditions:** A membership configured with a restricted router list is effectively tenant-wide for permitted operations. This is intra-tenant authority leakage and should not be described as a verified cross-tenant breach.

**Smallest fix:** Add one reusable scope predicate to resource lookup and handler authorization. Until implemented, do not expose scoped delegation as enforced.

**Acceptance:** Restrict technician to router A; direct API and queued jobs targeting same-tenant router B are denied. Verify null/all, empty/none and explicit lists as distinct values; revoked scope changes are respected before effects.

**Affected modules:** Tenancy, network, backups, RADIUS, monitoring and resource-based job policies.

**Downtime/rollback:** No required database downtime. Disable restricted delegation if reverting the enforcement; never silently widen it.

### SEC-07 — Recovery-code and TOTP single-use guarantees lack concurrency enforcement

**Priority:** P1
**Status:** **PARTIAL**, concurrency outcome **UNVERIFIED**.

**Evidence:** `identity/services.py:215–232` reads unused recovery code/current TOTP step and then saves it without row lock or compare-and-set. Sequential recovery single-use is tested at `test_auth_flow.py:90–103`; no concurrent assertion was found in inspected tests. In contrast, email verification uses an atomic transaction plus `select_for_update` at `services.py:104–115`.

**Impact/preconditions:** Two concurrent requests using the same valid factor can both observe unused state before either save. Atomicity must be proven rather than inferred from sequential replay tests. The TOTP completion path also does not visibly apply the login-failure limiter to second-factor attempts.

**Smallest fix:** Reuse database row locks/CAS for factor consumption in a bounded transaction; apply explicit bounded failure tracking to MFA completion/reauth as appropriate.

**Acceptance:** Two real PostgreSQL connections synchronized before consume produce exactly one accepted factor use. Wrong-factor attempts are bounded and cannot reset/bypass enforcement with the same pending session. Sequential flow remains correct.

**Affected modules:** Identity login, recovery and sensitive reauth.

**Downtime/rollback:** No schema change necessarily required; application rollout only. Invalidate pending authentication challenges when necessary.

### SEC-08 — Upload scanner fails open unless explicitly configured

**Priority:** P1 before accepting production payment proofs
**Status:** **CONFLICT** with ARCHITECTURE §1 private-storage/ClamAV baseline.

**Evidence:** `subscriptions/upload.py:79–96` defaults `MT_SCAN_MODE` to `disabled` and scans only for the exact value `clamav`; other/unknown values store accepted bytes without scan. Installer-created environment does not establish the scan mode in the inspected secret-creation block. The ClamAV path imports `clamd` before the exception handler.

**Impact:** Payment evidence upload can accept unscanned files despite the documented fail-closed baseline. No malicious file was submitted or executed. Private opaque storage reduces direct exposure; it does not replace scan policy before evidence review.

**Smallest fix:** Explicit production scan policy with startup/preflight validation, reject unknown mode, fail closed when required scanner/client is unavailable; retain clearly labeled isolated development behavior.

**Acceptance:** Production upload with missing scanner, missing client module, unknown mode, scanner timeout and infected response refuses the upload with stable errors; clean-file acceptance requires scanner evidence. No proof is exposed to reviewers before completion.

**Affected modules:** Subscription upload, installer/environment checks and any future upload feature reusing the pipeline.

**Downtime/rollback:** Optional scanner setup may require a maintenance step; application can disable uploads safely while the scanner is unavailable.

### SEC-09 — Audit redaction does not traverse arrays

**Priority:** P2
**Status:** **PARTIAL**.

**Evidence:** `audit/models.py:28–40` recursively cleans dictionaries but returns lists unchanged. `test_audit_permissions.py:8–22` only tests a list of scalars. Current inspected audit call sites mostly pass scalar/summary dictionaries; an actual committed secret in an array was **not** found.

**Impact:** Future batch payloads such as `{"items":[{"password":"..."}]}` bypass the generic redactor.

**Smallest fix:** Recursively sanitize list/tuple elements and retain explicit payload allowlists for sensitive events. Do not rely solely on a redactor to decide which data should be logged.

**Acceptance:** Nested dict/list mixed structures redact sensitive keys at every depth while preserving safe fields; current scalar/summary events remain readable.

**Affected modules:** Audit and all future batch/outbox/log consumers.

**Downtime/rollback:** None expected beyond application rollout. Historical remediation is required only if a separate evidence review actually finds persisted sensitive values.

## 4. Additional boundaries requiring explicit status

- **SupportGrant:** Model and fields exist at `identity/models.py:130–145`; no operational grant/expiry/revoke/banner enforcement was found in inspected request paths. Mark **PARTIAL/DOCUMENTED**, not operational support access. There is no evidence here that platform admins automatically receive tenant application access.
- **Platform queue:** `subscriptions/services.py:240–280` iterates explicit `tenant_scope` contexts for SaaS submissions. This is not a general RLS bypass. It should remain a tightly controlled platform use case with limited projection and pagination; do not generalize it into access to tenant finance.
- **Backup downloads:** `backups/urls.py` has list/schedule/run routes, no implemented authorized download/redeem route on this baseline. Token redemption, permission revocation and restore isolation are therefore **NOT IMPLEMENTED in the inspected route set/UNVERIFIED operationally**, not demonstrated secure.
- **Backup generation:** `backups/service.py:118–125` explicitly describes stored manifests and missing SFTP receiver; do not treat committed simulator manifests as recoverable router backups.
- **Enrollment transport:** `network/services.py:463–469` documents the missing RouterOS callback `check-certificate` validation. Preserve it as an open G1 network-security requirement. Encryption in transit without authenticated server identity is not equivalent to verified TLS.
- **SQL facade hardening:** Facades use `SECURITY DEFINER`, `row_security=on`, revoke PUBLIC execution and select a NAS from transport-source input. Their `search_path=radius, public` omits explicit trailing `pg_temp`; owners/CREATE/TEMP grants must be checked on a real deployed database. Do not call privilege or search-path hardening verified from source alone.
- **Projection ownership:** `grant_runtime.py` gives runtime DML over every non-system schema/table. RLS still applies, but future ledger/no-direct-DML and projection-writer restrictions require a narrower privilege manifest; coordinate with the database review.
- **Shared storage:** Opaque filenames, 0600 mode and authorized row lookup are useful controls. A shared application OS user is not independent host-level tenant isolation. No recommendation for separate databases or containers per tenant is warranted by this review.

## 5. Required tenant/module invariants

These restate existing architectural requirements; they do not introduce a new security policy:

1. Authenticate the actor; validate current membership, role and resource scope before tenant data or effects.
2. Treat browser tenant selection, body tenant IDs and job payload IDs as untrusted requests.
3. Enter tenant context transaction-locally on the same connection; blank/error/rollback/reused connection must fail closed.
4. Tenant model ownership includes RLS coverage, composite references and negative tests for every relationship added.
5. Shared operational envelopes carry the minimum information needed; payload, result and secrets retain tenant boundaries.
6. Jobs revalidate authority and desired revision at effect time; retries/cancel/recovery do not bypass the original permission.
7. External network effects require the existing authorize/apply/readback/audit and fencing contract.
8. Platform scope is explicit and bounded. SaaS operator money and tenant internet money cannot share untyped payment, book or tax contexts.
9. Storage downloads resolve artifacts through authorized tenant records and verify authority again at any token redemption.
10. Sensitive changes append a sanitized audit event within the business transaction; no plaintext credentials in jobs/outbox/audit.
11. New privileged functions receive explicit owner, search-path and EXECUTE/CREATE privileges; helpers do not blanket-grant future schemas.
12. Backups and restore preserve secrets and economic identities, restore into isolation and rerun tenant/security checks before exposure.

For planned Tax, minimum contract inputs should explicitly identify economic entity/book, tenant/platform authority, source document and immutable rule/version snapshot. Tax may consume approved billing/finance facts through owner services; it must not infer operator identity from nullable tenant context, overwrite issued documents or treat SaaS revenue as tenant revenue. Exact Tax planning compatibility remains **UNVERIFIED** because `planning_mvp` is absent.

## 6. Evidence and testing assessment

| Existing evidence in source | Present scope | Additional required evidence |
|---|---|---|
| `test_rls.py` | Blank/correct/wrong tenant, nested context, one composite FK, non-super/non-BYPASS role | Every tenant table/reference; exceptions, rollback, pool reuse; role ownership/membership and deployed grants |
| `test_auth_flow.py` | Ordinary login, configured MFA, sequential recovery replay, switch clears reauth | Platform MFA absence/promotion, direct API lifetime, parallel factor consumption, MFA rate limiting |
| `test_jobs_engine.py` | Cross-tenant job 404, job states, retry linkage, generic quotation permission | Role-specific retry/cancel, revoke-after-enqueue, per-router scope, system actor policy |
| `test_ops_platform_admin.py` | Payment decision behavior with forced sessions | Full-login MFA enforcement and privilege assurance |
| `test_documents_api.py` | Tenant document routes and immutable/hash behavior | Deployed storage recovery and negative filesystem/download paths |
| `test_ops_backups.py` | Backup catalog/handler behavior | Real encrypted artifact, restore, authorized gateway issue/redeem/revoke |
| `test_audit_permissions.py` | Scalar/dict redaction and static role bundles | Arrays and all sensitive event shapes |
| General API fixture | `enforce_csrf_checks=False` | Explicit strict-CSRF cases, anonymous unsafe requests, origin/cookie behavior |

Every entry above describes inspected test code, **not a test execution or PASS**.

## 7. Commands, changes and limitations

Read-only commands used: `git rev-parse HEAD`, `git status --short`, `rg --files`, targeted `rg -n`, `cat`, `nl -ba`, `sed -n`, `date -u`. SHA matches the delegated baseline. Commands successfully provided the evidence summarized above. One requirements-glob search reported `backend/requirements*: NOT FOUND`; the relevant remaining checks were handled through known files rather than invented requirements files.

No code, configuration, migrations, dependencies, documentation or report files were changed by this reviewer. No production data or credential values were inspected or included.

All runtime, integration, concurrency, deployed-DB grant, browser, CHR/GNS3, actual restore and malicious-upload tests were **SKIPPED intentionally** under the documentation-only/static-read scope. No vulnerability scan or exhaustive security review is claimed.

## 8. Handoff and next actions

1. Orchestrator persists this report and normalizes duplicates with architecture/database/DevOps findings.
2. Keep shared modular monolith, PostgreSQL RLS and existing job/outbox; no new security framework or per-tenant infrastructure.
3. Put credential separation, job authorization, platform MFA, scoped GUC cleanup, single-use factor concurrency and production scan policy into the staged implementation plan with explicit tests.
4. Keep scoped router delegation, support grants, actual backup download/restore and authenticated RouterOS callback marked incomplete until their respective evidence exists.
5. Record findings as application release blockers for affected workflows. A finalized documentation package may be **READY WITH CONDITIONS** for a subsequent implementation-planning session; it must not claim operational security or release readiness.
6. No owner approval is needed merely to document these findings. If the implementation chooses to weaken existing MFA, isolation, scan or permission requirements, that would require explicit owner approval; this reviewer recommends enforcing the existing requirements instead.
