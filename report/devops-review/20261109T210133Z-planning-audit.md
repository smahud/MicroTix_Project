# Independent DevOps Review — MicroTix Planning Audit

- **Author/role:** `/root/devops_review`, Independent DevOps Reviewer.
- **Objective:** Audit actual installer, deployment, release, upgrade, recovery, service lifecycle and evidence without changing application or infrastructure.
- **Baseline:** `smahud/MicroTix_Project`, default `main`, SHA `16085f825fef25ee4112d74b729c57e623b0bb05`.
- **Working branch:** `docs/planning-audit-20261110`.
- **Suggested persistent report:** `report/devops-review/20261109T210015Z-planning-audit.md`.
- **Mutation policy:** No files, services, dependencies, database, installer or application were changed by this reviewer. Orchestrator persists this complete report under CONTRACT §10.
- **Commit/remote status:** Reviewer produced no commit; **NOT PUSHED**.
- **Assessment:** Current production installation and upgrade readiness is **NOT READY**. Documentation can become **READY WITH CONDITIONS** for bounded remediation planning. The existing claim that only external host/domain evidence blocks beta is contradicted by statically identifiable installer defects.

## Requirements and inspected scope

Applicable requirements: CONTRACT §§3–4, 7–11; ARCHITECTURE §§1–4, 6–7; OPERATIONS §§3–4; ACCEPTANCE T01, T16–T18, T20–T21, G1–G2, G4–G5; README installer promises; existing BETA_RELEASE_STATUS and BETA_TEST_EVIDENCE claims.

Inspected files:

- `instalasi.sh`, entire 678 lines, all dispatch modes.
- `.github/workflows/ci.yml`.
- `backend/pyproject.toml`, `apps/web/package.json`.
- `backend/microtix/settings.py`, `backend/microtix/urls.py`.
- `backend/domains/config/registry.py`, `branding.py`, `views.py`, `management/commands/grant_runtime.py`.
- `backend/domains/documents/rendering.py`, `services.py`, `views.py` import references.
- `backend/domains/network/management/commands/render_wg_config.py`.
- `backend/domains/radius/reconciler.py`, `management/commands/setup_radius.py`, `management/commands/render_radius_config.py`.
- `backend/domains/jobs/management/commands/runworker.py`; engine/model lifecycle references.
- `backend/domains/backups/service.py`.
- `backend/tests/integration/test_ops_backups.py`, `backend/tests/contracts/test_ops_contract.py`; inventory and references of jobs, RADIUS, WireGuard, billing tests.
- `CONTRACT.md`, README, `backend/README.md`.
- `docs/ARCHITECTURE.md`, `OPERATIONS.md`, `ACCEPTANCE.md`, `PRODUCT.md`, `IMPLEMENTATION_PLAN.md`, `FINANCE.md`, `BETA_RELEASE_STATUS.md`, `BETA_TEST_EVIDENCE.md`, `defaults.json`, `test-cases.json`.
- `report/LATEST_HANDOFF.md` from inherited root discovery.
- Read-only diff/log of `origin/session/2026-11-07-sstp-phase2`.

`deploy/` and `ops/` were **NOT FOUND** in the inspected tree. Absence of those particular paths does not imply infrastructure is entirely absent: installer embeds unit/proxy configuration.

## Actual deployment inventory

| Area | Current implementation | Status |
|---|---|---|
| Official target | Installer checks VERSION_ID 13, x86_64/aarch64, disk ≥10GB, RAM ≥2GB | IMPLEMENTED; actual clean-host success UNVERIFIED |
| Modes | `install`, `status`, `doctor`, `upgrade`, `repair`; first/second argument dry-run handling | IMPLEMENTED |
| Release input | Current checkout/backend and apps/web directories | IMPLEMENTED; immutable artifact verification absent |
| Application | Native `/opt/microtix/backend`, shared venv and web-dist | IMPLEMENTED |
| Main architecture deployment | Compose application plus privileged systemd/native PostgreSQL | DOCUMENTED; actual installer diverges |
| Persistent state | `/etc/microtix`, `/var/lib/microtix/storage`, `/var/log/microtix`; PostgreSQL external to code tree | IMPLEMENTED |
| API/worker | Two embedded systemd units, same OS user/group/env; API loopback 8300 | IMPLEMENTED |
| WireGuard | Preserve keypair, create root config, adopt public key, render desired peer bundle | PARTIAL; active application deliberately manual |
| Firewall | Warn/check nftables activity; no MicroTix isolation policy installed | PARTIAL |
| RADIUS | Optional apt install, render bundle, restart stock service | PARTIAL with installation blockers |
| Upgrade backup | PostgreSQL custom dump then `pg_restore --list` | PARTIAL; no restore proof/full recovery set |
| Upgrade activation | In-place rsync, migrations, frontend build, proxy/WG setup, API+worker restart | IMPLEMENTED but unsafe sequence |
| Rollback command | No rollback mode or application snapshot/activation path | NOT IMPLEMENTED in inspected installer |
| Drain/graceful worker shutdown | No drain flag or signal handling in worker command | NOT IMPLEMENTED in inspected worker command |
| Billing scheduler | Command `issue_due_invoices` exists; no timer created by installer | PARTIAL |
| HA/near-zero downtime | No basis for claims in this deployment | UNVERIFIED |

## Findings

### OPS-01 — P1: Fresh install fails at directory/user command invocation

**Status:** CONFLICT; **verification:** statically verified, not executed.

**Evidence:** `instalasi.sh:59–64` implements `run()` as `"$@"`. `create_users_dirs()` passes whole shell commands as one quoted argument:

- `:139` — `run "useradd --system ..."`
- `:142` — `run "mkdir -p '$d'"`
- `:144–147` — similarly quoted chown/chmod commands.

The shell attempts to execute a filename containing the command plus spaces. Even if service user already exists, the first directory call has this problem.

**Impact:** A clean normal install stops before secrets/database/application setup. This contradicts installer deployability and beta descriptions. Syntax validation alone does not detect it.

**Smallest repair proposal:** Pass command and arguments separately to `run`, retaining its no-eval contract. Do not restore generic eval or add a shell abstraction.

**Alternative:** Explicit `run_sh` only where actual shell composition is necessary; not needed for these simple commands.

**Dependencies/order:** First bounded installer patch, followed by artifact completeness OPS-02.

**Acceptance:** Isolated Debian 13 fresh VM creates missing user/directories with correct ownership, then completes installation. Repeat installation preserves identities and data. Record actual exit/status; a dry-run is insufficient.

**Downtime/rollback:** No existing service downtime for a clean install. Existing host changes require preserving previous ownership; do not delete state to retry.

### OPS-02 — P1: Installed application lacks declared dependency and runtime configuration assets

**Status:** CONFLICT; **verification:** statically verified packaging mismatch.

**Evidence:**

- `instalasi.sh:238` duplicates Python dependency pins manually and omits `xhtml2pdf`.
- `backend/pyproject.toml` declares `xhtml2pdf==0.2.28`.
- `backend/domains/documents/rendering.py:30–31` imports xhtml2pdf eagerly; `services.py:24`, `views.py:25`, and `microtix/urls.py:18` connect that import to URL loading.
- `instalasi.sh:241–242` copies backend only; no copy of runtime `docs/defaults.json` or `branding.json`, and no `MT_DOCS_DIR` is generated.
- `backend/microtix/settings.py:158–159` defaults installed docs location to `/opt/microtix/docs`.
- `config/registry.py:102–106` reads `defaults.json`; `config/branding.py:18` reads `branding.json`.

**Impact:** Fresh application startup/checks may fail on missing xhtml2pdf. Configuration and branding paths fail even after dependency repair. A developer checkout has files that deployed artifact lacks.

**Smallest repair proposal:** Derive dependencies from the existing authoritative package declaration using an appropriate reproducible installation method; stage required runtime JSON and other discovered runtime assets with release code. Do not duplicate authoritative JSON into unrelated config formats.

**Alternative:** Set explicit runtime paths to shipped immutable assets. Depending on a mutable checkout remaining beside the installation is fragile.

**Dependencies/order:** After OPS-01; before proxy/readiness validation.

**Acceptance:** Stage/install in an empty directory without the source checkout present. Verify application import, Django checks, meta/config, branding, document generation, and startup as service user. Record artifact manifest/digests and dependency provenance.

**Downtime/rollback:** Stage-first implementation needs activation downtime only. Current in-place reinstall risks failure midway; retain prior code and compatible environment.

### OPS-03 — P1: RADIUS installation does not establish daemon identity or connect generated configuration to the service

**Status:** PARTIAL; **verification:** static defects established; live daemon behavior UNVERIFIED.

**Evidence:**

- `instalasi.sh:198–229` creates `mtx_migrator` and `mtx_app`, not `mtx_radius`.
- `instalasi.sh:451–458` generates a RADIUS DB password and calls `setup_radius`; it never creates/sets the daemon database role/password.
- `setup_radius.py:23–31` explicitly fails if the preexisting daemon role is missing.
- Installer renders into `/etc/freeradius/3.0/microtix` (`:454–457`) then restarts stock `freeradius` (`:465`) without wiring its config directory/unit.
- `radius/reconciler.py:21–26`, `:128` use sandbox-specific `/home/z/my-project/frdeb/extracted` defaults for binary/library root.
- Installer does not call renderer `--validate`; renderer supports it (`render_radius_config.py:31,60–65`).
- Render binds loopback (`instalasi.sh:456`), while authoritative network design expects private tunnel transport for actual NAS.
- `.radius-configured` short-circuits future setup (`:435–438`).

**Impact:** Fresh enabled-RADIUS install fails before daemon readiness. On an already provisioned role, service activity could refer to stock configuration rather than MicroTix façade. Restarting service is not proof of tenant-aware AAA or NAS applied revision.

**Smallest repair proposal:** Explicitly create the constrained daemon role/password through the privileged setup boundary, retain credential across upgrades, render into the verified production package layout, validate before activation, wire the service deliberately, then perform real isolated auth/accounting readback.

**Alternative:** A dedicated unit for the generated bundle is viable if it avoids conflicting listeners and has explicit ownership; no new RADIUS architecture is necessary.

**Dependencies/order:** OPS-01/02 first; daemon role/config repair before claiming production RADIUS readiness.

**Acceptance:** Empty PostgreSQL/clean Debian install with RADIUS enabled, second run, failure/recovery, credential preservation, daemon command/config introspection, known-valid auth/accounting and negative unknown-NAS/tenant cases. Verify actual listener address and firewall.

**Downtime/rollback:** RADIUS activation/reload can interrupt AAA; use a maintenance window until measured. Preserve prior validated bundle/role credentials and restore them on failed candidate activation. Never assume existing customer sessions prove new authentication works.

### OPS-04 — P1: Upgrade rewrites live code and schema before a validated candidate exists

**Status:** PARTIAL; **verification:** static sequence verified.

**Evidence:**

- `deploy_backend` recreates/updates shared venv, pip-upgrades, rsyncs with deletion and migrates (`instalasi.sh:236–250`).
- `do_upgrade:635–639` performs backend deployment/migration **before** frontend build and restarts both application processes only at the end.
- No staging release directory, activation pointer, installed-version verification, worker drain, migration compatibility classification or failure trap is present.
- `runworker.py` loops claim/run/reconcile with no graceful drain or signal policy.
- Systemd worker unit has no explicit deployment drain/stop timeout contract (`instalasi.sh:299–319`).

**Impact:** Running processes can mix old imported modules and new on-disk code; failures after schema/code changes leave partial upgrade. Jobs may execute during incompatible migrations. A candidate frontend failure occurs after database migration. Stop/restart during external effect can leave `uncertain`, requiring reconciliation rather than blind retry.

**Smallest repair proposal:** Build/validate a versioned candidate backend/venv/frontend first; classify migration compatibility; pause admission/claim of affected mutation work, drain bounded jobs, take consistent recovery checkpoint, migrate under explicit lock/time budget, activate candidate and restart gracefully, verify before reopening mutations.

**Alternative:** Initially use a short, explicit maintenance window and a retained prior release rather than introducing blue-green infrastructure.

**Dependencies/order:** After complete deploy artifact and honest health status; before production upgrade evidence.

**Acceptance:** A→B→B repeat and failed B upgrades with injected failure before/after build, migrate, activation and worker interruption. Assert acknowledged payments/effects retained, no duplicate network mutation, no active incompatible worker/schema pair, and old-code/new-schema compatibility for rollback window.

**Downtime/rollback:** Planned, measured application interruption on single VPS. Code rollback only if schema/data compatibility remains valid; database restore is a different recovery action with write reconciliation.

### OPS-05 — P1: Backup listing is treated as recoverability; recovery set and rollback mechanism are incomplete

**Status:** PARTIAL / NOT IMPLEMENTED for installer rollback; **verification:** static inventory verified; restoration UNVERIFIED.

**Evidence:**

- `instalasi.sh:627–631` creates only a local DB dump and checks `pg_restore --list`.
- No copy of storage blobs, key material/version, env/proxy/WG/RADIUS configs, role definitions or prior code/venv is captured here.
- No rollback mode in dispatcher `:655–677`.
- OPERATIONS §4 requires DB/WAL, private blobs, keys, configs, off-host encryption and measured restore.
- Router backup implementation (`backups/service.py:118–125,267`) explicitly stores simulator manifests and `verified_lab=False`; these are not platform recovery backups or real router binary restore evidence.

**Impact:** A readable dump catalog is not a restored database. DB references can outlive/mismatch blobs; missing encryption keys make retained encrypted data unreadable. Restoring a pre-upgrade dump after accepting writes loses later acknowledged operations unless reconciled.

**Smallest repair proposal:** Define a complete recovery manifest and perform restore into a fresh isolated target. Preserve encryption keys safely and separately, include required blobs/config/roles and previous release, verify cross-store consistency. Add off-host copies according to existing policy.

**Alternative:** Start with a quiesced, consistent full recovery snapshot under a measured window rather than claiming PITR/WAL streaming before it is implemented.

**Acceptance:** Restore from retained recovery artifacts on another host/database, decrypt historical records, reconcile invoice/payment/outbox sequences, recover NAS/VPN registry and private document access, then measure RPO/RTO from actual service disruption. Include corrupt/missing artifact and missing-key drills.

**Downtime/rollback:** Checkpoint may require brief write pause. Recovery downtime is measured; no zero-data-loss or RTO claim follows from listing a dump.

### OPS-06 — P1: Upgrade/repair can return success despite failed health, and proxy readiness checks are insufficient

**Status:** CONFLICT; **verification:** control-flow defect static; proxy failure modes require live proof.

**Evidence:**

- `health_checks` records failures in variables (`:480–505`).
- Only `summary` converts flags into exit 1/3 (`:539–578`).
- `install` calls summary; upgrade/repair do not (`:635–650`, `:673–676`).
- Upgrade logs “Upgrade selesai” after health (`:640`).
- `repair` masks restart failure with `|| true` (`:646,648`).
- Health uses `curl -f` without exact 200/JSON assertions; redirects count as curl success.
- Production `SECURE_SSL_REDIRECT=True` (`settings.py:133`), but no `SECURE_PROXY_SSL_HEADER` was found in settings; Caddy forwards HTTP to loopback (`instalasi.sh:419–420`).
- Generated `MT_ALLOWED_HOSTS` normally contains domain alone (`:183`); local checks send Host `127.0.0.1` (`:487–490`).
- `HealthReadyView` docstring says DB+migrations but implementation runs only `SELECT 1` (`config/views.py:77–85`).
- Smoke uses `-k` then HTTP fallbacks (`instalasi.sh:497–500`); separate HTTPS check exists but only sets partial flag.

**Impact:** False-success CLI exit/status and tests that can validate redirects rather than actual health. Real production proxy may redirect repeatedly because Django does not recognize original HTTPS; local probe may fail Host validation. These need production-faithful testing before declaring exact observed failure.

**Smallest repair proposal:** Apply one mode-independent final result mapping. Read persisted deployment context without exposing secrets, validate proxy-trust configuration against actual topology, require expected 200 JSON through TLS with bounded timeout/redirect handling, and use explicit valid Host for loopback checks. Add separate schema/capability checks rather than relabeling `SELECT 1`.

**Acceptance:** Stop API/worker, disconnect DB, stale migration/schema, invalid TLS, redirect loop and wrong Host each produce nonzero or explicit partial as applicable; successful health must return actual expected JSON through Caddy. `upgrade` and `repair` must not exit 0 after mandatory failures.

**Downtime/rollback:** Health checks themselves no downtime. Proxy changes validate before reload and retain old config.

### OPS-07 — P1: Runtime service receives migration credentials

**Status:** CONFLICT; **verification:** static boundary violation; no exploitation attempted.

**Evidence:** Shared generated env contains `MIGRATE_DATABASE_URL`, `MT_PG_PASSWORD_MIGRATOR` (`instalasi.sh:174–187`). The same file is readable by `microtix` group (`:189–192`) and injected into both API/worker (`:285,308`). This weakens the documented runtime/migrator separation even though normal runtime DATABASE_URL uses `mtx_app`.

**Impact:** Compromised application code can obtain stronger schema-owner credentials. NOBYPASSRLS on the normal role does not preserve the intended boundary when the migrator secret is supplied to that process.

**Smallest repair proposal:** Separate root-only migration/bootstrap secret file from least-privilege runtime env; only maintenance process obtains migrator credentials. Preserve application encryption keys across this split.

**Acceptance:** API/worker process environment, readable files and unit configuration contain no migrator credentials; their OS identity cannot read migration secret file; migrations still work via controlled privileged maintenance path.

**Downtime/rollback:** One planned service restart may be needed. Rollback restores compatible runtime configuration without restoring broader credentials to the app.

### OPS-08 — P2: Deployment topology and lifecycle descriptions exceed implementation

**Status:** CONFLICT / PARTIAL; **verification:** static comparison verified.

**Evidence:**

- ARCHITECTURE §1 describes Compose application and distinct dispatcher/collector/privileged host managers. Installer supplies native API+one worker.
- `setup_firewall:327–335` warns/checks activity rather than installing required peer isolation.
- WireGuard config is under `/etc/microtix/wireguard`; installer says activation via `wg-quick@wg0` without explicitly wiring standard unit/config lookup (`:395–396,558–560`).
- `render_wg_config` explicitly does not apply to live interface; installer renders a second bundle without private key (`:385–395`).
- Billing command exists but installer contains no unit/timer despite canonical handoff requiring daily scheduler.
- `repair` only restarts services/rebuilds Caddy; it does not create missing admin despite admin-onboarding warning directing user to repair (`:536`, `:643–650`).
- `status` and `doctor` mostly log findings; do not provide complete machine-readable failure status.

**Impact:** Operators infer capabilities that a successful service restart does not provide. Router management/AAA can remain disconnected while core API is live.

**Smallest repair proposal:** Document actual baseline and propose a narrow authoritative deployment decision; do not silently mandate Compose rewrite. Define each mode’s scope honestly. Add only required host wiring, scheduler and safety checks after approval of any normative topology change.

**Acceptance:** Inspect actual unit/config paths and activation, verify WG handshake and isolation with two tenants sharing LAN prefix, confirm billing timer triggers timezone-safe idempotent issue command, demonstrate repair behavior for each claimed recovery action.

**Downtime/rollback:** Host networking changes require isolated lab proof, explicit approved window, preserved existing WG/firewall config and targeted revert.

### OPS-09 — P2: CI validates developer execution but does not protect installer/upgrade invariants

**Status:** PARTIAL; **verification:** workflow inspection verified, CI results not fetched or rerun by reviewer.

**Evidence:** `.github/workflows/ci.yml` runs PostgreSQL-backed backend tests, FE types/lint/Vitest/i18n/build and docs check. It does not execute clean Debian installer, repeated install, shellcheck, upgrade/rollback, real FreeRADIUS harness, browser E2E, restore, or migration compatibility checks. Backend uses `pip install -e .`, masking installer dependency duplication. Main tests cover simulator router-backup flow, not full platform DR.

**Impact:** A green workflow can coexist with OPS-01–08. Existing historical shellcheck/syntax success does not establish installability.

**Smallest repair proposal:** Risk-based installer smoke and failure-injection tests, artifact packaging check and real install/upgrade/restore evidence lane. Keep expensive CHR/DR suites stage-gated rather than adding them to every documentation PR.

**Acceptance:** Pipeline or release evidence must reject actual broken invocation/missing artifact, failed health exit and interrupted activation; publish SHA, environment, exact commands, assertions and artifacts. Preserve backend RLS and FE production-live checks.

**Downtime/rollback:** Tests use disposable environments; no production changes.

## Recommended upgrade architecture

Keep modular monolith and PostgreSQL jobs/outbox. No Kubernetes, queue or service mesh.

1. **Preflight:** Confirm installed and candidate versions/digests; available disk for release+backup; schema compatibility; root-only migration credential; valid persisted domain/feature context; healthy DB, core workers and storage. Do not automatically apt-upgrade system packages as part of ordinary code patch.
2. **Stage:** Prepare `/opt/microtix/releases/<version-or-sha>` with code, matched venv, frontend and required runtime assets. Validate without mutating production DB.
3. **Checkpoint:** Obtain complete consistent recovery set. For initial single VPS, an explicit write pause is acceptable if needed. Record checkpoint boundary and acknowledged sequence.
4. **Drain:** Stop admission/claim of affected network jobs; allow bounded work to finish. Treat interrupted ambiguous effects as `uncertain`, reconcile/read back before retry. RADIUS/WG services remain independent where no config change is needed.
5. **Migrate:** Expand first; additive/backward-compatible changes before new code; bounded batched backfill; contract only after compatibility window and separate release decision. Set time/lock budgets.
6. **Activate:** Atomic application pointer or equally explicit retained-release activation followed by graceful process restart. Atomic pointer alone does not make migrations or process activation atomic.
7. **Verify:** Expected JSON health through validated TLS, exact schema compatibility, worker heartbeat/queue progress, tenant negative checks, finance/document smoke and integration-specific probes.
8. **Resume:** Open admission only after mandatory checks pass; reconcile jobs against current permissions/revisions/policy.
9. **Recover:** Compatible code rollback preserves new acknowledged writes. Incompatible migration means stop writes and use documented forward repair or deliberate database recovery with post-checkpoint reconstruction; never automatic destructive restore.

This is a proposed implementation plan, not a claim of current capability or approved change to authoritative topology.

## Failure scenarios and evidence gates

| Failure | Required behavior |
|---|---|
| Candidate build/dependency asset failure | Abort before production mutation |
| Backup corrupt/missing key/blob | Abort activation; retain current service |
| Migration lock timeout | Abort bounded migration, expose exact schema state |
| Process dies after external send | Mark/reconcile uncertainty; no blind repeat |
| New API unhealthy | Preserve maintenance state; roll back only within compatibility window |
| Worker incompatible with schema | Do not resume claims |
| RADIUS candidate invalid | Keep previous validated config active; do not reset NAS secrets |
| WG config update fails | Retain current keys/peers; targeted revert with readback |
| Recovery loses later transactions | Reconstruct/reconcile before exposing restored service |
| HTTPS redirects/invalid cert | Fail public-ready gate; do not accept `-k` as proof |
| Repeated repair | Preserve data, keys, identities and approved domain |

## Verification performed and limitations

Commands actually run:

- `bash -n instalasi.sh` — **exit 0**, syntax only.
- `command -v shellcheck` — **exit 1**, shellcheck unavailable; not installed.
- `rg --files`, `rg -n`, `nl -ba`/`sed` read-only inspection — successful except deliberately queried missing paths noted above.
- `git diff --stat main origin/session/2026-11-07-sstp-phase2 -- instalasi.sh .github backend/domains/radius/reconciler.py` — exit 0; installer has +132/−1 on unmerged branch.
- `git log -3 --oneline origin/session/2026-11-07-sstp-phase2` — exit 0, head `d7fa35e…`.
- `git status --short` at review check — exit 0, empty; root/other reviewers may subsequently create authorized docs.
- No installer mode was executed. No backend/frontend runtime tests, migrations, package install, DB connections, services, remote host or CHR operations ran.

Historical test numbers remain historical reported evidence and were **not independently reproduced** here.

PR #7 remains unmerged and its SSTP implementation must not count as default-main deployment capability. This review inspected its installer diff size/history, not a complete SSTP correctness audit.

## Decisions, compatibility and next actions

- Preserve actual product scope, existing secrets/data and modular monolith.
- Treat deployment topology reconciliation as **PROPOSED**, requiring owner approval if it changes authoritative architecture/privilege/external behavior.
- Do not weaken RLS, TLS, tenant isolation or release gates to accommodate installer faults.
- Do not describe simulator router backup as platform DR.
- No application patch is authorized in this docs-only task.
- **Next executable implementation priority:** bounded installer invocation/artifact/credential/health fixes under a later authorized code session, then clean Debian install and repeat-run evidence. Follow with staged upgrade and complete restore drill.
- **Open blockers:** OPS-01–07 preclude production install/upgrade readiness; OPS-08–09 require explicit evidence and topology disposition.
- **Completion state:** Independent static review complete; full handoff supplied for orchestrator persistence and incorporation into `planning_audit`.
