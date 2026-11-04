# Contradiction and Resolution Register — 2.1-build.1

Audit.2 recorded35 contradiction groups,33 resolved and 2 unresolved. This revision resolves those2 with the owner-endorsed technical clarification. Prior33 remain preserved by baseline comparison; they were not reclassified as new findings. A newly exposed security-policy gap remains NEEDS_OWNER_DECISION; no unconditional final PASS.

| ID | Statement A / location | Statement B / location | Precedence / impact | Smallest correction and disposition |
|---|---|---|---|---|
| B01 | master §7 executing allowed transitions omitted cancelled | same §7 policy changes before effect→cancelled | Equal authority; stale worker could violate permission or falsely cancel an applied effect | EXE-01 condition zero-effect+fence; otherwise uncertain/reconcile. Master transition and dependent TD/PRD/projections updated. RESOLVED |
| B02 | master §17 device task states omit uncertain/recovery | same §17 lost response may already have changed CPE | Equal authority; UI/retry could conceal possible effect | EXE-02 separate device_task_state/job_state, correlation and expiry cleanup mapping. RESOLVED |
| DEP-01 | TD §6 Cancel hanya tahap yang belum dieksekusi | EXE-01 allows executing before proven effect | Higher master controls; stale lower prose ambiguous | Explicit TD zero-effect/fence wording. RESOLVED |
| DEP-02 | agent AGENTS Mode C production defaults read-only inventory | master AUD-03 requires concrete target scope | Master controls; default inventory could exceed mandate | Agent production inventory requires separate target grant. RESOLVED |
| SCOPE-01 | T22 parent includes central HA and edge replica | R1 central RADIUS / R3 edge scope | Parent grouping cannot defer all T22 to R3 | Assertion records T22-HA introducedR1, T22-EDGE R3. RESOLVED before seal |
| FIX-01 | common CSV referred PRD §10 and absent padding rule | actual CSV schema PRD §11 and exact-size oracle | Wrong section and unsupported padding would reject valid limit proof | Address-only deterministic generator with separate byte/row variants. Source and case setup corrected; app acceptance NOT_RUN. RESOLVED_DESIGN |
| SEC-DEC-01 | PRD §2/AUD15 MFA platform and sensitive step-up, ordinary tenant/portal assurance unstated | ASVS5.0.0 V6.3.3 requires MFA/combination or documented mitigated relaxation | G2 incorporates ASVS but cannot silently change owner policy; affected TK101/102, portal scopes | Owner chooses full factor scope or reviewed exception; proposed patch in Owner_Decision_Requests. NEEDS_OWNER_DECISION |

Downstream verification: baseline 84 case/318 expected retained;27 full projections+MAC parity;85 task DAG and explicit applicability; manifest57/56; exact replay hash. Static checks cannot prove every semantic implication or runtime behavior. Source normative registries retain precedence; reports are evidence only.
