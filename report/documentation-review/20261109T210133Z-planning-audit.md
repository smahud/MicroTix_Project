# Independent Documentation Review — MicroTix Planning Audit

- **Author/role:** `/root/documentation_review`, Independent Documentation Reviewer.
- **Objective:** Review completeness, consistency, evidence traceability, authority, scope and handoff of the finalized planning package.
- **Repository/branch:** `smahud/MicroTix_Project`, `docs/planning-audit-20261110`.
- **Baseline:** `main@16085f825fef25ee4112d74b729c57e623b0bb05`.
- **Date:** 10 November 2026 WIB.
- **Persistence:** Orchestrator to save this complete report at `report/documentation-review/20261109T210133Z-planning-audit.md`.
- **Reviewer changes:** None; all work read-only.
- **Commit/remote:** No reviewer commit; **NOT PUSHED**.
- **Runtime tests:** **NOT_RUN**.

## Disposition

**REQUEST CHANGES on documentation until DOC-02 is incorporated.** DOC-01 was corrected during review; DOC-03 is a small factual correction.

After those corrections and completion of the deliberately pending integration records, the package is suitable for owner review. Its engineering readiness should remain **NOT READY** while DEC-01/DEC-02 remain unresolved. This review does not approve implementation, merge, production use or deployment.

## Inspected scope

Reviewed:

- All five files in `docs/planning_audit/`.
- `report/planning-audit/20261109T210133Z-finalization.md`.
- `report/planning-audit/20261109T210133Z-source-inventory.md`.
- `report/LATEST_HANDOFF.md`.
- Four specialist handoffs supplied in inherited context and their mapping in the final report.
- Relevant source sections in `backend/domains/common/tenant_context.py`, billing services, audit models and RADIUS AppConfig.
- `docs/ACCEPTANCE.md`, manifest records, current Git diff/untracked inventory.

Applicable requirements: user documentation-only scope; CONTRACT §§4–5, 9–11; ARCHITECTURE tenant-context and upload invariants; ACCEPTANCE evidence distinctions; user deliverables and definition of done.

## Findings

### DOC-01 — P2: Nested tenant-context invariant could instruct an incorrect reset

**Evidence:** The original `02_MODULE_CONTRACTS.md` §7 stated that after success/error/**nesting**/pool reuse no tenant context remains. Actual nested `tenant_scope` restores the previously active outer context; clearing it would break the outer operation.

**Risk:** A literal implementation could weaken correct nested transaction behavior while attempting to satisfy the new contract.

**Required correction:** Distinguish nested restoration from outermost cleanup:

- Nested exit restores the previous trusted outer context.
- Outermost exit, context-ending failure and reused connections retain no context/bypass from the completed operation.

**Status:** **CORRECTED during review.** Latest source text in §7 reflects this distinction.

**Acceptance:** Keep nested A→B→A and outermost/error/pool-reuse fail-closed tests separate. This was a documentation correction; those runtime tests were not executed here.

### DOC-02 — P1: Scanner finding understates an existing billing upload bypass

**Evidence:**

- `01_MODULARITY_AUDIT.md`, PA-012, describes the subscriptions scanner default and lists billing impact conditionally: “upload billing jika reuse pipeline.”
- `backend/domains/billing/services.py:447–469`, `_store_proof`, currently performs MIME/size validation and writes private proof bytes directly.
- Billing imports `sniff_mime` and constants from subscriptions, **not** the subscriptions scanning operation.

**Risk:** A future agent could fix production `MT_SCAN_MODE`/ClamAV handling in subscriptions and incorrectly consider the complete payment-proof upload requirement closed. Existing internet-payment proof uploads would still bypass scanning.

**Required correction:**

1. Add the current billing `_store_proof` callsite to PA-012 evidence.
2. State explicitly that production internet-payment proofs also lack scanner enforcement in this path.
3. Require fail-closed acceptance for **both SaaS payment-proof and internet-payment-proof routes**.
4. Keep the recommendation small: reuse one concrete scanning policy/helper across the existing callers, or otherwise prove both routes enforce the same invariant. No generic storage framework is necessary.

**Verification:** Static call-path evidence; no malicious payload, upload request or scanner test executed.

**Acceptance:** For both routes, absent client/daemon, timeout, infected response and unsupported production mode refuse storage/exposure appropriately; clean-file acceptance has actual scanner evidence.

**Status at final reviewer read:** **OPEN; sent to orchestrator for incorporation.**

### DOC-03 — P3: Manifest record count needs precise wording

**Evidence:** Main audit report DEC-02 calls the existing manifest “Manifest 22 file baseline.” The current `manifest.files` array contains **21 records**. The validator’s **22-file** result includes the manifest itself.

**Risk:** Small evidence-count ambiguity during the proposed manifest extension.

**Correction:** Say “21 manifest records; validator baseline covers 22 files including manifest.” Five additions produce 26 records/27 covered files.

**Status:** Correction requested; no readiness consequence by itself.

## Positive assessment

The package satisfies the substantive planning objectives:

- Keeps the established modular monolith and PostgreSQL/job architecture.
- Separates actual implementation, documented requirements, partial capability, conflicts and unverified behavior.
- Distinguishes default-main evidence from unmerged SSTP PR #7.
- Maps domain ownership, dependencies, permissible reads and prohibited ownership bypasses.
- Provides concrete risk, evidence, smallest repair, alternatives, acceptance and recovery for principal findings.
- Addresses tenant context, RLS, composite references, current authorization, privileged credentials, jobs and storage.
- Specifies realistic staged upgrade, compatibility window, migration/backfill, complete recovery and acknowledged-write handling.
- Avoids absolute zero-downtime, benchmark, hardware and compliance claims.
- Keeps Tax compatibility conceptual, without inventing an implemented Tax/ledger domain or changing planning_mvp.
- Preserves original G0–G5 meanings by naming the new review gates PA-G0–PA-G6.
- Records unresolved architecture/manifest decisions as PROPOSED and retains the more conservative NOT READY disposition.

No reason was found to introduce additional technologies, documentation fragments or a broad refactor.

## Checks and outcomes

Reviewer independently performed read-only Git inventory, Python AST/count checks, targeted source reads and relative-link validation.

Confirmed:

- **379** tracked files at the pinned baseline.
- **225** backend Python files parsed without syntax error.
- **15** actual domain directories.
- **39** numbered migrations across **11** migrated apps.
- Runtime dependency table is consistent with the documented **50** directed edges, excluding management/migrations.
- Relative-link check over the current **12** package/report files: **51 links**, **0 missing destinations**.
- Observed changed/untracked paths remain under `docs/planning_audit/` and `report/`.

AST parsing and link validation do not prove application correctness.

Parent-reported baseline docs PASS, original-tree manifest FAIL, and temporary-copy refresh PASS remain distinct evidence classes. The temporary rehearsal must not be described as passing original-repository CI. Original manifest scope remains unchanged.

## Limitations and next steps

No backend/frontend suite, SQL execution, installer, deployment, restore, daemon, browser, scanner, CHR/GNS3 or capacity testing was run. No current remote API verification was independently repeated by this reviewer.

The pending documentation-review/commit/PR sections were intentionally unfinished while review proceeded; they are not unexpected defects. Before final delivery, the orchestrator should:

1. Incorporate DOC-02 and DOC-03; record DOC-01 as corrected.
2. Persist this report and record the final disposition.
3. Repeat affected scoped validation after edits.
4. Finish integration/remote-status records truthfully.
5. Keep main unchanged and retain NOT READY with the specific DEC-01/DEC-02 conditions.

## Focused documentation recheck addendum

Read-only recheck confirms:

- **DOC-01 CLOSED:** `02_MODULE_CONTRACTS.md` §7 correctly distinguishes nested restoration from outermost cleanup.
- **DOC-02 CLOSED:** PA-012 explicitly identifies the existing unscanned billing path and requires scanner acceptance for **both SaaS and internet-payment proofs**. The security matrix in `04_REVIEW_GATES.md` matches.
- **DOC-03 CLOSED:** Main report DEC-02 correctly states **21 manifest records / 22 validator-covered files**.

**Final documentation disposition: corrections accepted; suitable for owner review.** No residual issue found in the focused recheck. Engineering readiness remains **NOT READY** pending DEC-01/DEC-02. No files changed or runtime tests executed by this reviewer; **NOT PUSHED**.

## Orchestrator persistence note

The complete reviewer handoff and its focused recheck are preserved above. Orchestrator wrote this report under CONTRACT §10; reviewer did not write repository files. Reviewer status NOT PUSHED describes the review handoff, not the eventual documentation-branch publication. See the main audit report for integration evidence.
