# Test Coverage Matrix v2.1 — 2.1-audit.2

Generated from test-case-registry_v2_1.json. Requirement tags are declared design associations, not proof of complete requirement coverage. All 84 cases remain NOT_RUN; no runtime assertion is PASS. Parent/gate product rules follow PRD §26 plus AUD/MAC.

| Parent | Child ID exact | Requirement | Gate relevan | Status |
|---|---|---|---|---|
| T01 | T01-BOOT-01, T01-BOOT-02, T01-BOOT-03, T01-BOOT-NEG-01 | NET-03, NET-04, NET-05, NET-07 | G1 | NOT_RUN |
| T02 | T02-IMP-01, T02-IMP-02, T02-IMP-NEG-01 | IMP-01, IMP-03, SUB-02 | G1 | NOT_RUN |
| T03 | T03-SEC-01, T03-SEC-02, T03-SEC-03 | IMP-01, RAD-09 | G1 | NOT_RUN |
| T04 | T04-CSV-01, T04-CSV-02, T04-CSV-NEG-01 | CSV-01, CSV-02, CSV-03 | G2 | NOT_RUN |
| T05 | T05-RACE-01, T05-RACE-02, T05-BULK-01 | ACT-02, ACT-05, PAY-04 | G2 | NOT_RUN |
| T06 | T06-CRASH-01, T06-CRASH-02, T06-CRASH-03 | JOB-02, JOB-03, JOB-05 | G1, G2 | NOT_RUN |
| T07 | T07-ISO-01, T07-ISO-02 | ACT-03, ACT-04 | G1, G2 | NOT_RUN |
| T08 | T08-BKP-01, T08-BKP-02 | BKP-01, BKP-03, BKP-06 | G1, G2 | NOT_RUN |
| T09 | T09-RST-01 | BKP-05 | G2 | NOT_RUN |
| T10 | T10-TEN-01, T10-TEN-02, T10-TEN-03 | SEC-04, SEC-05, TEN-03 | G2 | NOT_RUN |
| T11 | T11-ACS-01, T11-ACS-02, T11-ACS-NEG-01 | ACS-03, ACS-04, ACS-05, ACS-06 | G1, G2 | NOT_RUN |
| T12 | T12-LED-01, T12-LED-02, T12-LED-03, T12-LED-NEG-01 | ACC-01, ACC-02, ACC-03, ACC-07, ACC-11 | G2 | NOT_RUN |
| T13 | T13-WAN-01, T13-WAN-02, T13-WAN-03 | CFG-02, WAN-01, WAN-02, WAN-03, WAN-04 | G1 | NOT_RUN |
| T14 | T14-OUT-01 | NFR-02, NFR-04 | G5 | NOT_RUN |
| T15 | T15-SOAK-01, T15-REC-01 | MON-02, NFR-01 | G4 | NOT_RUN |
| T16 | T16-AUTH-01, T16-AUTH-02, T16-AUTH-03, T16-ATTR-01, T16-AUTH-NEG-01, T16-AUTH-NEG-02 | RAD-01, RAD-03, RAD-04, RAD-05 | G1 | NOT_RUN |
| T17 | T17-CHR-01, T17-CHR-02 | RAD-10 | G1 | NOT_RUN |
| T18 | T18-XR-01, T18-RPL-01 | RAD-11, SUB-01 | G1 | NOT_RUN |
| T19 | T19-TEN-01, T19-NEG-01 | RAD-03 | G1, G2 | NOT_RUN |
| T20 | T20-ISO-01, T20-ISO-02, T20-ISO-NEG-01 | ACT-03, ACT-05, RAD-06 | G1, G2 | NOT_RUN |
| T21 | T21-ACC-01, T21-SIM-01 | RAD-07 | G1, G2 | NOT_RUN |
| T22 | T22-HA-01, T22-EDGE-01 | RAD-08 | G4 | NOT_RUN |
| T23 | T23-I18-01, T23-I18-02, T23-I18-NEG-01 | I18N-01, I18N-10, UX-05 | G2 | NOT_RUN |
| T24 | T24-VCH-01, T24-AGT-01 | ACC-05, AGT-01, HSP-02, HSP-03 | G1, G2 | NOT_RUN |
| QA-SEC | QA-SEC-01, QA-SEC-02, QA-SEC-03, QA-SEC-04, QA-SEC-05, QA-SEC-06, QA-SEC-07, QA-SEC-08, QA-SEC-09, QA-SEC-10, QA-SEC-11, QA-SEC-12, QA-SEC-13, QA-SEC-14, QA-SEC-15, QA-SEC-16, QA-SEC-17, QA-SEC-18, QA-SEC-19, QA-SEC-20 | ACC-11, ACS-03, ACS-08, API-02, BKP-03, CSV-01, CSV-02, IMP-01, JOB-01, JOB-05, NET-01, NET-03, OPS-SEC, PAY-02, PDP-01, PDP-02, PDP-03, PDP-04, RAD-03, SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, TEN-02, TEN-03 | G2 | NOT_RUN |

Dependencies, fixtures, deadline and cleanup are per-case and common contract. Missing execution profile, fixture, grant or asset blocks execution. Per-assertion release applicability and task-to-acceptance closure remain open in the audit blocker register.
