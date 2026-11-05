MicroTix — Agent Execution Contract

Status: MANDATORY
Scope: All coding agents, orchestrators, sub-agents, reviewers, integrators, and deployment agents.

1. Mandatory Reporting

Every agent execution MUST produce a persistent Markdown report inside the repository root directory "report/".

This requirement applies to:

- Repository inspection and audits.
- Architecture and planning.
- Code implementation.
- Testing and verification.
- Security review.
- Git integration and merge.
- Installation and deployment.
- Release preparation.

No agent may claim its task is complete without a report.

2. Report Location and Naming

Reports MUST follow:

"report/<agent-role>/<UTC-timestamp>-<task-slug>.md"

Use UTC timestamps formatted as "YYYYMMDDTHHMMSSZ".

Report filenames MUST be unique. Existing reports MUST NOT be overwritten.

3. Required Report Content

Every report MUST contain:

1. Agent identity and execution role.
2. Task objective and scope.
3. Starting branch and commit SHA.
4. Documentation and contract references.
5. Files created, modified, or deleted.
6. Implementation decisions and rationale.
7. Tests executed, commands, and actual results.
8. Unexecuted tests and reasons.
9. Security and compatibility findings.
10. Remaining blockers and known limitations.
11. Commit SHA and remote push verification.
12. Final task status and next-step handoff.

All claims MUST be evidence-based.

4. Reporting Rules

- Reports MUST distinguish verified facts from assumptions.
- Reports MUST NOT contain credentials, tokens, passwords, or secrets.
- Failed tests MUST be documented.
- Skipped tests MUST NOT be reported as passed.
- Agent failures and incomplete work MUST be recorded.
- Reports MUST be committed with the corresponding changes whenever possible.
- Agents MUST preserve existing reports.
- Parallel agents MUST use isolated worktrees or clones.
- Agents MUST NOT modify reports owned by another agent.
- Reports MUST identify the source commit of the code being evaluated.
- If a task fails before committing, the agent MUST preserve its report and provide the recovery location.

5. Integration Requirements

The integration owner MUST inspect reports from all participating agents before merging.

The integration report MUST include:

- Branches and commits consolidated.
- Merge conflicts and their resolutions.
- Django migration validation.
- OpenAPI contract verification.
- Regression and integration test results.
- Installer verification.
- Outstanding release blockers.
- Final integrated commit SHA.

A merge MUST NOT be considered complete until the remote canonical branch has been verified.

6. Release Requirements

A beta release MUST include a consolidated release report under "report/release/".

The report MUST reference actual test evidence, deployment verification, release limitations, and the release commit/tag.

A release MUST NOT be marked ready solely on the basis of agent assertions.

7. Contract Enforcement

The orchestrator MUST provide this contract to every sub-agent.

Each delegated task MUST explicitly include the reporting requirement and report destination.

CI SHOULD validate report presence and required metadata for agent-authored changes, without blocking unrelated changes or allowing reports to substitute for real tests.

Failure to produce the required report constitutes a task-contract violation.

8. Authority and Precedence

This contract governs agent execution and reporting.

Existing MicroTix product, architecture, security, network safety, acceptance, and release contracts remain authoritative for their respective domains.

An agent MUST NOT weaken an existing requirement to satisfy this reporting contract.

Only the designated integration owner may coordinate final integration into canonical "main", subject to repository policy and release gates.