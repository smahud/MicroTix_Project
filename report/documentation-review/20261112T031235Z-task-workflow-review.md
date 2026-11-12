# Independent review — approved repository task workflow

Author: Codex documentation/security reviewer (`/root/security_jobs_review`). Date: 12 November 2026. Starting branch: `docs/task-workflow-20261112`. Base HEAD: `a2207b66cc705fece79645034ea45900e81a9f38`. Worktree: `/workspace/scratch/9459f0c7494a/task-workflow-20261112`. Reviewed material: the controller's uncommitted documentation draft; this report is not a review of a future commit SHA.

Objective: independently assess consistency of CONTRACT §6A, the permanent task entry, PA-006 packet and related navigation/handoff documents against the owner's approved workflow. The parent supplied the explicit owner approval and authorized documentation-only scope. No authority to implement PA-006, merge application changes or deploy follows from this review.

**Final verdict: APPROVED for the reviewed documentation-only workflow and PA-006 instruction packet. DTR-01 is CLOSED after direct reread of the controller's correction.** Final publication and required checks remain the controller's responsibility; this is not acceptance of a PA-006 implementation.

## Initial verdict

**REQUEST CHANGES — one narrow PA-006 acceptance clarification (DTR-01).** The workflow design, authorization separation and other reviewed content are suitable. This request is a documentation correction, not an application patch or new architectural requirement. Once the controller resolves DTR-01, re-read the changed text and record the final review outcome below.

### DTR-01 — P2: concurrent same-body acceptance must require eventual replay

`task/0010-pa006-idempotency.md:53` initially permits “replay atau documented in-progress/conflict yang stabil” for concurrent same-identity/key/body. `:42` prohibits duplicate effects/500 and asks for stable documented replay/conflict, but does not explicitly require a subsequent retry after an in-progress answer to recover the original outcome. Read literally, an implementation could satisfy the table with one successful action and permanently conflicting identical retries. That would not establish the logical-action replay required by `docs/ARCHITECTURE.md:116`.

Smallest correction: say that any in-progress response is temporary and uses an existing/documented contract, and subsequent same-body retry must obtain the same action/result once resolved; a same-body request must not be mislabeled `idempotency_conflict` or end in a permanent generic conflict that substitutes for replay. Preserve safe reconciliation for a genuinely ambiguous prior external effect; do not promise external exactly-once. Add that subsequent-retry assertion to the concurrent test acceptance, rather than requiring a new status protocol/framework.

Verification criterion: read the final task table and mandatory-work wording together; they must no longer permit permanent identical-body conflicts to count as completed PA-006. No runtime test is required to correct the instruction; executor runtime evidence remains a future deliverable.

## Reviewed properties that pass

- **Owner approval and normative change record:** controller report quotes the explicit approval, records the previous/new workflow, reasons, alternatives, impact and documentation-only rollback. Product mission and domain authority remain intact.
- **Permanent entry and task identity:** CONTRACT §2/§6A and README/MASTER_PROMPT/IMPLEMENTATION_PLAN/index/AGENT_HANDOFF point to `task/0000-start-here.md`; the guide is not executable and is never renamed. Stable four-digit IDs, centralized allocation, no duplicate unfinished/done files and same-ID reopening are explicit.
- **Executor delivery versus acceptance:** `_done` denotes executor delivery with required evidence. Controller owns exact-SHA acceptance. Merge, tag, feature activation and deployment have separate authority/gates. CONTRACT §6A expressly distinguishes this milestone from §13's fuller task Definition of Done. There is no false claim that PA-006 has been implemented.
- **Publication and resumption:** completion rename is included in the delivered commit; remote publication/checks precede a done declaration. Failed/blocked work stays unfinished with evidence and resume step. Pending-review or completed actions are not repeated. Correction reopens the original ID and preserves review history.
- **Freshness and dependencies:** fetch actual refs, preserve other work, inspect changed baseline, record instruction ref if not merged, and review the actual tested code SHA. Report-only descendants identify the tested ancestor rather than requiring self-referential future SHAs. Number order is insufficient without dependencies; independent authorized work remains possible.
- **Bounded ownership:** controller defines task, executor implements/tests/reports/commits/pushes; packet 0010 permits only minimal idempotency-related modules/migrations/decorators/tests and documentation evidence. It excludes job lifecycle, scanner/MFA, quota policy, adapters, installer, ledger/Tax/ACS/OLT and normative contract changes.
- **Actionable PA-006 coverage:** call-site inventory; principal and canonical tenant/platform/resource identity; SaaS invoice target; platform scope independent of active tenant; auth/permission/step-up before replay; HMAC and no secret caching; real PostgreSQL/nonprivileged RLS; forced interleaving; rollback and interrupted outcome; retained business uniqueness/legacy records; PA-001 regressions. The packet requires evidence of effects and target/actor scope, not status codes alone.
- **No parallel backlog/framework:** `docs/tasks.json` remains the product backlog, domain documents own requirements, and packets link instead of copying the roadmap. No registry, daemon, scheduler, new dependency or task engine was introduced. Naming a future jobs packet does not authorize it automatically.
- **Deployment information and readiness:** task files contain no actual deployment URLs or credentials. Sandbox-first, withheld access details and truthful lab/DR/scale/downtime limits are explicit. Beta remains NOT_READY. Historical claims/counters remain in the appropriate reports rather than masquerading as current readiness.

## Checks actually run

Read directly: CONTRACT §2/§6A; `task/0000-start-here.md`; `task/0010-pa006-idempotency.md`; README; docs/MASTER_PROMPT, IMPLEMENTATION_PLAN, README, AGENT_HANDOFF and progress; latest handoff; controller decision report. Inspected `git diff`, `git diff --stat/--numstat/--name-only`, `git status --short` and `git rev-parse HEAD`.

- Read-only Python Markdown file-target check across 10 reviewed documents: **80 local links checked, zero missing targets**, zero incoming links to renameable task packets. This validates path existence, not heading anchors or rendered layout.
- Task-file URL scan: **zero HTTP(S) URL occurrences** in the guide/packet. Also read the text for access/credential leakage; no actual deployment values found.
- `git diff --check`: **exit 0**.
- Tracked diff inventory remains documentation/CONTRACT/README/manifest/handoff; no application source/configuration change was observed. Task files and decision report are new documentation.
- Existing manifest refresh was ongoing/planned by the controller; stale hashes during drafting are not a product defect. The parent owns final validator/manifest checks, final diff review, publication and required CI.

**NOT_RUN:** application pytest/frontend tests, dependency installation, DB/RLS/HTTP/migration/worker execution, API runtime, installer/FreeRADIUS/CHR/GNS3, restore, production access, GitHub writes, CI execution, final canonical docs validator. Application testing is unnecessary for this documentation-only review; the task's future tests are not claimed as passes.

Only this review report was authored. No task, contract, source, configuration, manifest or handoff edited by the reviewer. **NO_COMMIT / NO_PUSH.** Starting worktree was already dirty with the controller's authorized draft; those changes were preserved.

## Final recheck

**DTR-01 CLOSED.** Re-read `task/0010-pa006-idempotency.md:42,53` after the controller's edit: temporary in-progress handling is conditional on the existing contract; retry after completion must replay the same logical action/result; same-body permanent generic conflict or `idempotency_conflict` cannot satisfy acceptance. This resolves the identified ambiguity without prescribing a new API status or overstating external exactly-once guarantees.

Re-ran `git diff --check` (exit 0); `git diff --name-only -- backend apps instalasi.sh` was empty; base HEAD remains `a2207b66cc705fece79645034ea45900e81a9f38`. Parent separately reported the canonical docs validator PASS (22 files/78 links); that is attributed controller evidence, not a reviewer execution. The reviewer's own 80-link file-target check remains valid because the correction changed no links.

**APPROVED within this bounded documentation-only scope, with no remaining review blocker.** A later change to meaning or candidate content requires relevant revalidation; this report does not approve application merge or deployment. Task 0010 remains ready/not_submitted with implementation/tested SHA unfilled, as required.
