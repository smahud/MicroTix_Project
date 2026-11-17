# Independent lifecycle review — task0020 / PR27

- Author/role: Codex independent lifecycle reviewer, `/root/review_lifecycle`;
  delegated by the session controller under CONTRACT §5. No application edit,
  branch change, commit, merge, push, deployment or device access by this reviewer.
- Repository: `smahud/MicroTix_Project`, local branch
  `review/0020-controller-20261117`.
- Baseline: `main@41d1f33f16508491a34f66b767830b9dd3e5954e`.
- Instruction: `review/0020-job-lifecycle-authority-20261117` /
  `ea7b8a17ad8d6339eed45769bbff1626ea279665`, PR26.
- Candidate reviewed: PR27,
  `bd37c14e6c41339a8743b3d4b723ee74f13bef08`, reported tested ancestor
  `7118cce0db330acb02be0b3b774b1b1628d55d7a`.
- Scope: jobs engine/runworker, active network/backup/radius/customer handler
  boundaries and lifecycle/drain tests; J20-A01–A05/A08/A09. Authority HTTP
  and product-policy review is separately owned by the authority reviewer.
- Requirements read: AGENTS, CONTRACT, default reviewer prompt, task0020,
  execution/internal review `20261117T010218Z`, ARCHITECTURE §6,
  PRODUCT JOB-02–05/SYNC-03 and OPERATIONS §§3–4.
- Files written by this reviewer: this report and
  `report/controller-evidence/20261117T134100Z-0020-review/test_lifecycle_review.py`
  (additional evidence-file ownership explicitly delegated by the controller).
- Publication: **NOT PUSHED by this sub-agent**; controller owns versioned
  integration/publication/readback. No claim of full task acceptance.

## Independent recommendation

**CHANGES_REQUESTED.** CAS on envelope terminal/result writes and session
sender locks improve the submitted implementation, but they do not yet
fence domain effects or cover all unknown-outcome retry paths. At least the
first two findings below are directly reachable in active production kinds.
Controller should allocate final stable finding IDs and independently
validate the supplied reproductions before publishing its verdict.

This sub-agent performed source review and compiled the reproduction module;
the controller, not this reviewer, owns the PostgreSQL execution and final
runtime logs. Executor suite counts are executor evidence, not this
reviewer's independent test results.

## Findings

### LIFE-0020-01 — P1: domain commits and later effects are not fenced by current lease

Acceptance: J20-A01/A02/A05; ARCHITECTURE §6 and PRODUCT JOB-03/05.

`backend/domains/jobs/engine.py:173–184` (`JobContext.scope`) checks only
the local `ctx.lost` flag before/after `tenant_scope`. It neither checks
current token/epoch/state/lease nor holds a short ownership guard through the
domain commit. `ctx.lost` becomes true only after a failed heartbeat/progress,
and production handlers ignore the return value of `progress`.

Concrete active path: `DiscoverRouterHandler.execute`,
`backend/domains/network/handlers.py:110–114`, calls `run_discovery(router)`
without JobContext. `backend/domains/network/services.py:928–978` creates
a snapshot, performs adapter I/O, then independently commits discovery
objects, snapshot success, migration linkage and a health sample. Expiring
and reconciling the lease while `list_accounts` is blocked does not stop
those later domain writes. The final envelope CAS fails, leaving job
`uncertain` while stale domain effects have already committed.

Related active path: `backend/domains/backups/service.py:217–229` ignores
failed `ctx.progress` and writes a physical manifest anyway. Radius B2/B5
also enter a scope after I/O without fresh ownership validation.

Supplied reproduction:
`test_actual_discovery_cannot_commit_after_reconcile` uses the actual
registered discovery handler/service, an Event-blocked controlled adapter,
separate worker connection, actual lease reconciliation, bounded join and
complete exception/result checking. Assertions require zero new discovery
objects/health samples and no post-reconcile success snapshot.

Minimum correction: make each short domain commit conditional on current
worker ownership within the same transaction, including service-owned
transactions; loss must abort/roll back that unit. Every post-I/O effect
boundary and checkpoint return must stop stale execution. Do not reintroduce
a database transaction/row lock across adapter I/O.

Closure: block an active handler at real effect boundary, reconcile/transfer
its lease, resume it, prove zero subsequent domain/file/send effects and
preserve the new owner's state/result/progress; then prove the healthy path
still commits under FORCE RLS.

### LIFE-0020-02 — P1: generic failure after possible effect automatically retries

Acceptance: J20-A04/A05; PRODUCT JOB-05, ARCHITECTURE §6.

`backend/domains/jobs/engine.py:593–606` durably marks `effect_state=maybe`
before execute. On an arbitrary exception, `613–615` constructs
`JobError(code="internal_error", retryable=True)` without an uncertainty
classification. `_finish_execute_failure` (`735–744`) falls through to
`_retry_or_fail` (`747–770`), which queues `retry_wait` despite the possible
effect. This path even writes executing→retry_wait outside the §6 state
table; the safety concern is the resend, not the spelling of the transition.

Concrete active path: `BackupRunHandler.execute` successfully invokes
`adapter.create_backup` at `backend/domains/backups/service.py:197`; a
subsequent disk-full/permission/OSError from `_write_manifest` at `218–229`
triggers automatic retry and another router backup command/generation,
without readback of the first effect.

Supplied reproduction:
`test_backup_manifest_failure_after_send_must_hold_unknown` uses the actual
registered backup handler and real BackupArtifact rows. A controlled adapter
counts successful sends; only local manifest writing is fault-injected.
The probe runs the scheduled retry if the engine exposes one, prints first
state/effect and actual send/artifact counts, then requires an uncertainty
hold and exactly one send.

Minimum correction: failures after a possible effect default to uncertain
or recovery unless the handler supplies positive, durable evidence of no
effect/safe retry. Preserve definite pre-effect and DB-rollback retries;
do not blanket-label all preflight failures uncertain.

Closure: active backup staging error after successful send cannot expose a
claimable retry, including repeated automatic workers and HTTP retry; actual
readback applied must verify without resend, not-applied may retry only
after old writer safety is established, unknown remains held.

### LIFE-0020-03 — P1: origin retry bypasses an uncertain descendant

Acceptance: J20-A04; previously claimed closure REV-2011-01 is incomplete
for multi-level retry lineage.

`backend/domains/jobs/engine.py:999–1005` checks only direct children
(`origin_job_id=origin.id`) for active/uncertain/recovery states. The origin
row lock serializes siblings, but distinct generations lock distinct rows.

Concrete sequence: origin O failed/retryable → retry C → C failed/retryable
→ retry G → G sends then becomes uncertain → retry O. The direct child C is
terminal, so the guard does not see G; a new sibling N is created and may
send while G's outcome remains unknown. This is not a source hypothetical:
every step is a supported engine/API state and operation.

Supplied reproduction:
`test_retry_origin_cannot_bypass_uncertain_grandchild` executes G with a
controlled send-then-timeout handler, attempts the origin retry and executes
the extra candidate if exposed; it asserts that no extra retry/send exists.

Minimum correction: serialize/check one stable logical action across all
retry generations or conservatively disallow retrying obsolete ancestors;
do not add a second task framework. Retain traceability and prevent
concurrent origin/child retries from branching an uncertain logical action.

Closure: origin/child/grandchild mixed concurrent retries, unknown/recovery
and completed descendants must preserve one logical effect; missing/no-effect
failed attempts remain recoverable through the supported retry path.

### LIFE-0020-04 — P1: a new conflicting router writer can send before predecessor readback

Acceptance: J20-A03/A04; ARCHITECTURE §6: new owner waits until old writer
cannot send **and readback is complete**.

`backend/domains/jobs/engine.py:574–589` checks only availability of the
session advisory lock. The lock is released in `finally` (`693–695`) when
a timeout-after-send job returns uncertain. No router-level unresolved
outcome guard/readback blocks the next conflicting queued job. A new job on
the same router can send immediately while the predecessor remains
uncertain. Advisory-lock availability proves only that the prior DB
session does not currently hold that lock; it does not prove completion of
outcome readback.

Supplied reproduction:
`test_new_router_writer_waits_for_unknown_predecessor_readback` executes a
controlled conflicting router handler that sends then times out, leaves
the first job uncertain without readback and starts another same-router
job. It requires send count to remain one.

Minimum correction: retain a durable conflict hold for unresolved router
effects, integrated with existing uncertain resolution. Permit independent
routers and safe read-only/recovery work; avoid an unbounded global queue
lock. Actual database-session loss while a network sender lives also needs
an explicit safe policy; session lock alone must not be documented as proof
that the network sender stopped.

Closure: new conflicting queued work cannot send before old-writer safety
and fresh readback are both satisfied; unknown stays held, applied verifies
without resend, another router still progresses.

## Required drain evidence is incomplete

J20-A08 explicitly requests real SIGTERM **and SIGINT** while idle,
cooperative DB work and blocked I/O are active. The submitted four process
tests cover SIGTERM idle, SIGTERM after a purported cooperative job is
already terminal, SIGTERM during blocked I/O, and SIGKILL/reconcile.

`backend/tests/integration/test_jobs_drain_pa002.py:129–145` waits for
SUCCEEDED/FAILED before sending SIGTERM. Consequently it does not test
draining active cooperative work. `tests/drain_handlers.py:19–23` also
performs no DB mutation. There is no SIGINT process test in that module.
These are missing mandatory observations, not proof that all SIGINT behavior
is broken. Require gated active DB work with durable assertions, both
signals, and a queued second job proving no new claim after stop. Keep
bounded process cleanup and distinguish incomplete from drained exit.

## Improvements retained / limits

- Envelope state/result commit now uses CAS token+epoch+verifying in the
  update WHERE; result details are written in the same tenant transaction.
- Cancel-before-effect CAS bumps epoch; in-flight executing/verifying cancel
  is rejected. Router session locks prevent simultaneous cooperating
  workers with healthy distinct PG sessions from entering send together.
- Reconcile distinguishes early crash from executing/verifying uncertainty
  and does not overwrite a renewed lease through its expiry predicate.
- Direct uncertain retry is rejected; applied readback takes verify-only.
- Missing handler and negative verifier are not silently succeeded in the
  normal engine path. These improvements should be preserved.
- Progress extends a lease only when invoked. A blocked phase longer than
  30 seconds can still be reconciled while alive; source review does not
  establish periodic heartbeat coverage for every active I/O handler.
- No new schema migration; PA-006 applied migrations remain untouched.
  This reviewer did not rerun their runtime compatibility regressions.
- Root and authority reviewer must independently assess current authority,
  policy/revision and HTTP scope; this report makes no pass claim there.

## Commands, evidence attribution and handoff

Executed by this sub-agent: source inspection using `rg`, `nl`, `sed`,
`cat`; syntax check
`.venv/bin/python3.13 -m py_compile report/controller-evidence/20261117T134100Z-0020-review/test_lifecycle_review.py`
→ **exit 0**. The reproduction module is committed evidence code, not a
modification to the application test suite or product requirement.

**NOT RUN by this sub-agent:** PostgreSQL probes/backend suite, migration
replays, process signals, live device/CHR/GNS3, production install/upgrade/
restore, systemd, browser E2E, performance/capacity. Controller runs the
probes serially against the disposable PostgreSQL instance and records
actual output under the same evidence directory; no executor result is
credited as this reviewer's own execution.

Next actor: controller reviewer. Run/inspect the four focused probes, map
confirmed defects and evidence gaps to final finding IDs, publish
changes_requested against exact PR27 SHA and reopen **task0020**, preserving
valid completed PA-001/PA-006 work. Coding corrections return to the same
ID. No successor task, acceptance, merge, deploy or release is authorized by
this independent source report. Production Beta remains NOT_READY.

## Addendum — controller's independent PostgreSQL execution

The controller ran the supplied probes serially using
`report/controller-evidence/20261117T134100Z-0020-review/run_probes_split.sh`.
This sub-agent then read `lifecycle-probes.log`, `exit-codes.txt`, the runner
and `split-roles-rls.log`; these are **controller executions**, not executions
performed by this sub-agent. The final run used real PostgreSQL 17.11 with
schema owner `mtx_migrator` and runtime `mtx_app` (nonowner, NOSUPERUSER,
NOBYPASSRLS), FORCE RLS. Extra TRUNCATE was solely for disposable pytest
cleanup; it is not a production privilege recommendation.

Final focused command:
`python -m pytest -c pytest.ini <evidence>/test_lifecycle_review.py -q -s --reuse-db --tb=short`
from `backend/`: **4 failed safety assertions, 0 pytest setup/teardown errors,
exit 1, 1.83s**. The application ERROR logs in the first probe are the
deliberately injected OSError; they are not harness errors.

| Final controller finding | Observed final state/effects |
|---|---|
| **REV-1711-01** = LIFE-0020-01 | Reconciled job remains `uncertain`; stale active discovery then commits **1 object**, **1 health sample**, and snapshot **succeeded**. Worker joined and returned complete result without exception. |
| **REV-1711-02** = LIFE-0020-02 | Actual backup handler: first state **retry_wait**, effect **maybe**; automatic reclaim succeeds; adapter sends **2**, artifact rows **2**, after successful create_backup followed by injected local staging OSError. |
| **REV-1711-03** = LIFE-0020-03 | Grandchild remains **uncertain**; retry of original ancestor creates an extra candidate; send count **2**. |
| **REV-1711-04** = LIFE-0020-04 | First same-router job remains **uncertain** without readback; next conflicting writer **succeeded**, send count **2**. |

The missing SIGINT/active cooperative DB drain evidence is mapped by the
controller to **REV-1711-09**. It remains an evidence gap; the four probes
above do not purport to execute those absent signal scenarios.

The initial probe run in `lifecycle-probes-initial.log` encountered Django
transactional teardown failure on the unmanaged `radius.nas` foreign key;
subsequent duplicate tunnel-IP cases from that run are discarded as
contaminated evidence. Only the marker was corrected to provide explicit
`available_apps=list(settings.INSTALLED_APPS)`, enabling the existing test
harness CASCADE flush behavior. Assertions and product expectations did not
change. The final split-role run started from a fresh migrated schema and
confirmed all four intended failures cleanly.

Controller separately reports the unchanged candidate's existing backend
suite **554 passed, 1 skipped, 3 warnings**, exit 0, in `full-suite.log`.
That suite used its own runtime-owned FORCE-RLS test schema and does not
replace the separately verified nonowner split-role probe evidence above.
Passing the existing suite therefore does not close REV-1711-01–04.
