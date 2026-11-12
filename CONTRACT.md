MicroTix — Engineering, Agent Execution & Delivery Contract

Status: MANDATORY
Applies to: Every main agent, GLM orchestrator, sub-agent, reviewer, integrator, deployment process, and future agent session.
Repository: smahud/MicroTix_Project
Primary outcome: One coherent, secure, deployable MicroTix product progressing toward evidence-based Beta Launch.


1. Product Mission Is Non-Negotiable

MicroTix is a multi-tenant ISP/RT-RW Net operations platform, not merely a billing dashboard. It must progressively deliver customer/service management, MikroTik/RouterOS, PPPoE/Hotspot, RADIUS, secure connectivity, monitoring, billing, subscriptions, and the documented subsequent network-management phases. Protect existing networks and customer connectivity.


The initial deliverables are an integrated, installable application on Debian 13 and a reproducible, isolated GNS3 laboratory for validating real network workflows. The project must remain aligned with its original purpose as features evolve. Feature growth is not permission for scope drift. Implement all authoritative requirements according to their documented phases; do not move future-phase features into beta without a justified release decision.


2. Documentation Compliance — Mandatory

All applicable repository documentation is binding, including docs/PRODUCT.md, ARCHITECTURE.md, UI_UX.md, ROUTEROS.md, RADIUS.md, ACS.md, FINANCE.md, OPERATIONS.md, ACCEPTANCE.md, IMPLEMENTATION_PLAN.md, I18N.md, MASTER_PROMPT.md, tasks.json, test-cases.json, defaults.json, branding.json, and other applicable files discovered in the current tree. Consult docs/README.md and actual repository references for scope and authority.

The persistent agent entry point is [task/0000-start-here.md](task/0000-start-here.md). Repository task packets describe the currently authorized execution scope; docs/tasks.json remains the product backlog, and the domain documents retain ownership of requirements. Task packets do not replace or weaken those requirements.


Before modifying code, identify applicable requirements and acceptance criteria. Maintain traceability requirement → implementation → test → evidence → report. Never silently omit, weaken, or reinterpret a requirement to match defective code. A test passing against mocks does not establish real integration. A missing implementation remains a documented gap, not a completed feature.


If documents conflict, stop the affected decision, document exact file/section references and impact, select the narrowest safe resolution supported by product intent and evidence, and obtain approval when the resolution changes product scope, security, external behavior, or release criteria. Unaffected work may continue.


3. STRICT PROHIBITION OF OVERENGINEERING

Overengineering is strictly forbidden. Every new abstraction, dependency, service, framework, queue, cache, microservice, infrastructure component, or architectural layer requires a concrete, documented necessity. Reuse the established stack and existing working code. Do not add Redis, Celery, Kafka, Kubernetes, or comparable infrastructure merely for hypothetical scale or convenience when the documented design does not require it.


Prefer the simplest solution that satisfies the actual requirement, operational safety, maintainability, and measurable acceptance criteria. No speculative generalization, duplicate implementation, parallel architecture, unnecessary rewrite, decorative framework, or premature optimization. Do not over-simplify away security, tenant isolation, recovery, or other mandatory controls.


For any nontrivial design change, record: current deficiency; evidence; simpler alternatives; why the selected change is necessary; affected requirements; operational and maintenance cost; rollback; tests. If a simpler compliant solution exists, choose it.


4. Controlled Documentation Changes

Documentation is authoritative but may evolve through a controlled change process. Never edit documentation merely to make failing code appear compliant. Every normative change must include a decision record in report/ with:



Exact document path, heading, and previous/new contract or proposed diff.

Problem statement and why the current wording is incorrect, incomplete, contradictory, unsafe, or no longer applicable.

Supporting evidence: code references, tests, reproducible observations, vendor documentation, measured performance, or explicit user decision; distinguish fact from inference.

Impact on original product goals, beta scope, security, network behavior, backwards compatibility, and future phases.

Alternatives, including keeping the current contract, and why rejected.

Required implementation, tests, migrations, and rollback actions.

Approval status, reviewer, date, and associated commit/PR.


Typographical and non-normative clarifications may be corrected with a concise explanation. Normative changes to scope, security, architecture, network mutation, or acceptance gates require explicit user approval before adoption unless already authorized by an unambiguous higher-authority project decision. Record proposals as PROPOSED, not APPROVED, until approval exists. Preserve traceability and avoid conflicting duplicate sources of truth.


5. Sequential Main-Agent Sessions; Specialized Sub-agents

Only one main development session is active at a time. There are no permanent Agent A/Agent B roles. The current GLM orchestrator owns coordination, integration, and handoff for its session. Discover actual Task sub-agent types, model choices, and isolation guarantees at runtime; do not invent capabilities.


Sub-agent use is mandatory when suitable sub-agents are available and materially useful. Delegate independent repository exploration, architecture/security review, implementation, deployment checks, and independent QA as appropriate. A sub-agent does not inherit chat context automatically: every delegation must specify objective, baseline SHA, branch/worktree, docs, permitted/forbidden files, dependencies, acceptance criteria, tests, report path, and handoff.


Prefer parallel read-only tasks. Parallel writes require verified isolated worktrees/clones and disjoint file ownership. Never concurrently edit migrations, shared contracts, installers, or shared API files. If safe isolation is unavailable, serialize writes. One active orchestrator integrates and verifies sub-agent output; no sub-agent may independently merge to canonical main.


6. Start Every Session From Reality

Fetch current remote refs; inspect main, outstanding branches/PRs, worktrees, uncommitted work, CI, docs, report/, and prior handoff. Preserve all valid work. Confirm the current code and test state rather than trusting historical claims. Select the highest-impact unblocked beta requirement and execute it. Do not repeatedly generate roadmaps when safe implementation is possible.


Use the workflow DISCOVER → PRIORITIZE → DELEGATE → IMPLEMENT → INTEGRATE → TEST → REVIEW → REPORT → COMMIT → HANDOFF. Continue independent safe tasks when a lab, credential, license, or hardware dependency blocks another task.


6A. Repository Task Packets — Mandatory

Approved by the project owner on 12 November 2026: future execution instructions are stored as Markdown files in task/, so users do not repeatedly copy long prompts between sessions. Every agent starts with task/0000-start-here.md, this contract and report/LATEST_HANDOFF.md, then verifies actual remote refs and selects the earliest eligible packet. The entry guide is permanent and is not an executable task.

The controller/reviewer authors and scopes packets, assigns stable four-digit IDs, and records review decisions. The executor implements, tests, reports, commits and pushes the scoped work from its sandbox. Use NNNN-lowercase-hyphen-slug.md; on completed executor delivery rename the same file to NNNN-lowercase-hyphen-slug_done.md. Keep IDs permanent; never renumber historical tasks or create a duplicate task to hide an unfinished correction. Do not create a second product backlog, queue service, daemon or task framework.

Each packet states its objective, baseline and dependencies, requirement references, permitted/forbidden changes, measurable acceptance, required tests, report locations and delivery evidence. Follow filename order only among tasks whose prerequisites are satisfied. Preserve unrelated work and declared file ownership; one main session allocates IDs. If the baseline changed, inspect the delta before implementing. Do not rerun completed work or duplicate an existing pending-review candidate.

Execution status is ready, in_progress, blocked, failed or done. Review status is not_submitted, pending, accepted or changes_requested. The executor updates execution evidence; the controller owns acceptance. Record the exact implementation/tested SHA, published candidate/PR and review evidence. The _done suffix means the executor delivered the declared scope with required tests and reports; it is not controller acceptance, merge, release_enabled or deployment authorization. Controller acceptance applies only to the reviewed code; later source changes require relevant revalidation. A report-only descendant must identify its tested ancestor and prove unchanged application content, rather than inventing a file's own future commit SHA.

Include the completion rename in the delivered commit, push it and verify remote publication before declaring done. Failed, blocked or incomplete tasks retain the unfinished filename and record a concrete blocker/resume step. A controller request for corrections reopens the same ID by removing _done, preserving review history in report/. Safe independent tasks may continue only when their own prerequisites permit it. Pending review is not permission to repeat the action or bypass a dependent gate.

Before handoff, update the task evidence, session/reviewer reports, report/LATEST_HANDOFF.md and docs/progress.md consistently. Executor completion does not replace the task-level Definition of Done in section 13, which also requires the applicable review and integration. An active session may process subsequent authorized eligible tasks; files alone do not schedule or restart agents in the background.

Until the candidate passes the relevant sandbox and deployment-readiness review, implementation remains sandbox-first. Do not put deployment access details or credentials in task packets or hand them to an executor prematurely. A reviewed task, green CI, or _done filename never grants an automatic merge, production deployment, feature activation or release tag. Those actions follow their separate existing authority and evidence requirements.


7. Beta Scope, Production Deployment & GNS3

Prioritize integrated real frontend/API/backend, PostgreSQL persistence and RLS, authentication/MFA, tenant onboarding, permissions, customers/services, approved subscriptions, durable jobs/outbox, RouterOS enrollment and API-SSL over WireGuard, FreeRADIUS auth/accounting, monitoring, backup/recovery, diagnostics, and instalasi.sh on Debian 13. Respect documented release stages and feature gates; R2–R4 are not automatically beta blockers.


The canonical installer is instalasi.sh. It must be idempotent, non-destructive, upgrade-safe, secret-safe, observable, and capable of checking prerequisites, dependencies, migrations, services, HTTPS prerequisites, health, and smoke tests. A successful install is not proof of real router connectivity or beta readiness.


Build a reproducible API-driven GNS3 lab with basic, multi-router, and complex ISP topology profiles as required by the documentation. Validate MikroTik CHR, client provisioning, PPPoE, Hotspot, RADIUS, WireGuard, supported routing, failure injection, recovery, and machine-readable evidence. Use properly licensed CHR images from authorized sources; never redistribute images without rights. Keep lab networks and secrets isolated from production. Provisioning and teardown must be safe and repeatable.


Capacity target: design and progressively benchmark toward 1,000 tenants with approximately 1,000 simultaneously online clients per tenant. Use aggregate monitoring by default and targeted real-time per-client monitoring. Do not infer that all clients require continuous high-frequency polling. Record workload, bottlenecks, resource usage, and verified limits. Never claim scale validation without measured evidence.


8. Network and Tenant Safety

All router mutations follow DISCOVER → VALIDATE → PLAN → PREVIEW → AUTHORIZE → APPLY → READBACK → VERIFY → AUDIT. Never change existing routes, WAN/LAN, firewall, NAT, DHCP, DNS, bridge, AAA, or customer accounts without the documented authorization and release gate. Adoption of existing customers must not silently mutate routers. Follow documented staged RADIUS migration and rollback.


Use typed/capability-aware adapters, ownership checks, desired/observed state, durable jobs, idempotency, locks/fencing, readback, and recovery. Do not blind-retry ambiguous network mutations. Enforce tenant isolation and RLS. Never weaken TLS or expose private RADIUS services contrary to contract.


9. Verification and Release Evidence

Use docs/ACCEPTANCE.md, docs/test-cases.json, docs/OPERATIONS.md, and applicable gates. Run relevant Django checks, migrations, backend tests, PostgreSQL RLS tests, OpenAPI checks, frontend lint/typecheck/build/tests, browser E2E, installer ShellCheck/clean install/reinstall/upgrade, backup/restore, secret/security checks, FreeRADIUS and CHR lab integration, and failure/recovery tests.


Record actual command, environment/version, exit code, assertions, log/evidence path, and result. Distinguish IMPLEMENTED, VERIFIED_UNIT, VERIFIED_INTEGRATION, VERIFIED_LAB, PILOT_VERIFIED, RELEASE_ENABLED, BLOCKED. Never mark an unexecuted test PASS. Fix implementation defects instead of weakening acceptance. Beta release requires verified release gates and explicit documented limitations.


10. Mandatory Reports in report/

Every main-agent execution and delegated sub-agent task MUST produce a persistent Markdown report at report/<agent-role>/<YYYYMMDDTHHMMSSZ>-<task-slug>.md. Use unique filenames; preserve historical reports. If a sub-agent cannot write to the repository, the orchestrator must persist its complete handoff under that path, identifying its author and evidence limitations.


Each report must include: agent/role; objective; starting branch/SHA; relevant docs/requirement IDs; changes/files; decisions and justification; tests/commands/results; skipped tests; security/compatibility; unresolved blockers; commit SHA and verified remote status (or NOT PUSHED); completion state; and exact next steps. Never include tokens, secrets, passwords, private keys, or production customer data.


Maintain one canonical latest-session handoff at report/LATEST_HANDOFF.md unless an existing authoritative convention specifies another path. It must state canonical remote SHA, completed verified work, unmerged branches, beta blockers, evidence, and next executable priority. Update docs/progress.md consistently without copying whole reports. A session is not complete without its report and handoff.


11. Git Integration & Change Preservation

No destructive cleanup, force-push, hard reset, or unreviewed overwrites. Use safe branches and comply with GitHub protections. Integrate semantically, check migrations/OpenAPI, run combined regression tests, and inspect sub-agent reports. Only merge into main after required approvals and release gates. Verify remote main SHA after merge; never claim a push, merge, or tag without remote evidence. Unfinished work remains explicitly tracked and must not masquerade as released functionality.


12. Decision Hierarchy & Exceptions

Follow explicit user-approved product decisions and safety requirements; this contract governs agent behavior, scope discipline, reporting, and change control; domain-specific authoritative docs govern implementation. A conflict is not permission to silently choose the easier interpretation. Escalate material contradictions with evidence and a proposed minimal correction.


Security and network safety are never optional. A genuine emergency correction must be minimal, documented, tested, and reported; do not use an emergency as justification for architectural expansion.


13. Definition of Done

For a task: compliant code or automation, relevant tests with evidence, independent review where warranted, persistent report, safe integration, and a clear handoff.


For the declared beta scope: one integrated canonical codebase; clean Debian 13 installation; operational tenant workflow; real supported backend/network integration; reproducible GNS3 topology and tests; verified backup/restore and recovery; security and release gates passed; known limitations explicitly documented. Unverified capacity, devices, and future-phase features must remain labeled as such.


Final principle: Build the real product. Obey the documentation. Prohibit overengineering. Justify every contract change with evidence. Preserve networks and prior work. Orchestrate specialists safely. Test actual integrations. Report every execution. Deliver one verified MicroTix beta.

