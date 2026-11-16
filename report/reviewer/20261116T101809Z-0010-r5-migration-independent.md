# Independent migration review — task0010 / PA-006, PR24

Author: `/root/migration_review`, independent read-only source reviewer,
16 November 2026 (Asia/Jakarta). Publication status at authoring: **NOT
PUSHED**; the controller owns integration and verified remote publication.

## Identity, instructions and scope

- Exact inspected candidate: `a301a94c2b3268679065e85bbef66f35949483f7`
  (PR24); implementation ancestor
  `7338a720b5d64a4ccb47b9abe7d3dc6feca0a476`.
- Correction baseline: PR21
  `634da4224f15dd6a5a4e9010fe1811dec8c7954d`; old writer baseline:
  `main@9903d9b0cf09d737b553da3c21067b4810e956c0`.
- Read: AGENTS, CONTRACT §§4–6A/9–13, default reviewer prompt,
  `task/0000-start-here.md`, current task0010 acceptance/handoff,
  controller R4 `20261115T053138Z-0010-pa006-r4-review.md`, executor R5
  report and internal review, candidate migration0004 and R5 tests,
  current replay code/owning subscription and conflict handlers, and old
  writer/view/session/membership code. Relevant requirements: PA-006
  mandatory work2/4/5/6/7 and REV-1311-01 closing acceptance.
- Objective: challenge closure of the sole remaining R4 finding,
  REV-1311-01, without revisiting unrelated application architecture.
- Writes: **this report only**. No source, test, task, handoff, dependency,
  schema, DB, git-ref or deployment mutation; no push or merge.

## Assessment

**Recommend closing REV-1311-01 on the inspected source, subject to the
controller's independent PostgreSQL/HTTP verification. No new blocking
source defect found.** This is a source/pure-Python review, not a task
acceptance decision or an independent claim that DB/live-upgrade tests
passed.

| Concern | Inspected evidence and conclusion |
|---|---|
| Recover old UUID-bearing scopes | `jobs/migrations/0004_idempotency_identity.py:126` invokes the same stdlib UUID conversion used by old model/context validation; `:146–212` considers every delimiter and validates both sides. It accepts prefixes at arbitrary positions accepted by that conversion, rather than adding another spelling exception. |
| Unique interpretation | The boundary cannot be swallowed by a larger valid tenant UUID unless the smaller tenant ends in a removable `urn`/`uuid` token lacking its colon; those nonhex suffixes cannot make a valid smaller UUID. The exact `platform` literal cannot be extended to a valid UUID. The injected ambiguity path explicitly raises rather than guessing. |
| Completed/unknown replay guards | Backfill `:237–271` preserves principal, operation, canonical tenant/resource, body and response fields. Runtime `common/idempotency.py:310–338` checks retained resource-empty payment guards before fresh claim; absent response is409. Completed payment replay invokes subscription target/tenant validation at `subscriptions/views.py:97–123`. Direct canonical identity also rejects absent response before execution (`common/idempotency.py:343–358`). |
| Platform and opaque | Only the three platform decision operations remap to literal `platform` (`0004:100–102,251–255`). Old session setters use canonical UUIDField values or fallback `platform`. Opaque `identity_conflict_resolve` preserves the remainder verbatim (`:263–267`); current legacy lookup rejects group-only old records (`legacy_replay=False`), preserving session binding. |
| Dedupe | `0004:272–300` includes principal/tenant/operation/resource/key in identity; ranks response-bearing evidence before an unknown outcome and then newest. It never discards the last guard for a parsed logical identity. Existing alias duplicates already written by old code are not claimed to be undone. |
| Unresolvable input | Non-UUID tenant/resource shapes that cannot reach successful baseline UUID-bearing handlers remain retained dead rows. The new parser does not use this outcome for accepted UUID spellings in the independent matrix. The old conflict handler requires an actual generated conflict group; arbitrary long opaque garbage cannot produce a successful old conflict decision. |
| Atomicity and recovery | Migration operations remain one normal Django PostgreSQL migration (`0004:319–376`), with no `atomic=False`. The docstring explicitly requires old/new writer freeze and says reverse of nonempty state is unsupported. Lines56–67 limit this edit to pre0004 state and explicitly exclude automatic repair of a previously applied defective migration. |
| Scope preservation | `git diff --name-only 7338a72 a301a94 -- backend apps instalasi.sh .github CONTRACT.md AGENTS.md docs/manifest.json` returned no paths. Published descendants do not change inspected application/config contents. |

## Independent commands and actual results

Executed locally with Python **3.12.14**, exit0; no Django or DB imports:

1. AST-extracted the candidate functions `_canonical_uuid` and
   `_split_legacy_scope`, `AmbiguousLegacyScope`, and their two constant
   sets directly from the inspected file. No hand-reimplemented parser.
2. Generated deterministic spellings with seed16112026 from canonical,
   uppercase, compact, braced, repeated-brace, standard/repeated `urn:`
   and `uuid:` forms, prefix tokens inserted **inside** the UUID text,
   inserted hyphens, plus-sign, Unicode digit and underscore variations.
   Kept only inputs accepted by actual `uuid.UUID`.
3. Crossed **413** accepted tenant spellings with **408** accepted resource
   spellings: **168,504 pairs**, checked as UUID-resource, empty-resource
   and opaque-resource scopes (**505,512 scopes**, each within old
   scope max256). Compared returned raw tuple to the known writer boundary,
   not merely canonical equivalence. Added **408 platform-literal scopes**.
4. Result: **0 wrong splits, 0 lost accepted scopes, 0 unexpected ambiguity**.
   Explicit malformed/uppercase-PLATFORM cases returned no interpretation;
   injected permissive validators raised `AmbiguousLegacyScope`.
5. AST inventory using `git ls-tree`/`git show 9903d9b` found **28** actual
   baseline `@idempotent` call-sites: backup1, billing8, customers9,
   network4, radius1, subscriptions5. All resources are absent or UUID
   kwargs except the one group-only opaque operation. The internal executor
   review says30; this arithmetic discrepancy is an evidence-description
   issue, not a new code blocker. Do not repeat30 as a verified count.

The matrix output was:

```json
{"python":"3.12.14","tenant_spellings":413,"resource_spellings":408,
 "counts":{"pairs":168504,"valid_scopes":505512,"uuid":168504,
 "empty":168504,"opaque":168504,"platform":408},
 "mismatch_count":0,"first_mismatches":[]}
```

Source commands also checked old TenantApiView's exception/transaction
ordering (errors escape the tenant transaction before DRF conversion),
`identity/services.py` session setters, `resolve_conflict_group` generated
group lookup, complete migration operation ordering, and current replay
guards. The matrix uses this machine's3.12 UUID library; the controller's
supported runtime tests remain authoritative for DB/HTTP behavior.

## Tests reviewed, limits and next step

Read the added R5 tests for actual MigrationExecutor transitions,
response/record/effect assertions, both UUID positions, unknown outcome,
concurrent retry, target/body conflicts, opaque fallback, alias dedupe
and injected transactional rollback. The direct migration tests seed
old-format records; executor's separate old-source HTTP harness is the
claimed evidence for genuine old-writer behavior. These are distinct
methods and should retain separate attribution.

**NOT_RUN by this reviewer:** Django tests, migrations on PostgreSQL,
HTTP requests, real files, concurrency/wait graphs, frontend/CI,
install/upgrade/restore, router/GNS3/CHR, deployment, capacity tests. No
claim is made that this source-only result proves those acceptance items.
No secrets or production data were used. No unresolved blocking finding
was found in the delegated scope. The pre-existing opaque-garbage
length/DataError fail-stop note remains operational context, not a new
scope expansion.

Completion: delegated source review complete; report uncommitted/NOT
PUSHED at authoring. Next actor **controller_reviewer**: corroborate the
remaining acceptance using its actual PostgreSQL/HTTP results, integrate
this source assessment with evidence limits, and publish a separate
exact-SHA controller verdict. Acceptance does not authorize merge,
deployment, tag or a Production Beta readiness claim.
