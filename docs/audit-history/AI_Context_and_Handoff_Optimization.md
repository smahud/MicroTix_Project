# AI Context and Handoff Optimization — 2.1-build.1

Read START_BUILD → AGENTS → master §0–2/§24 and relevant amendment IDs → one task contract and direct dependencies → authoritative source clauses → selected cases/assertions → current diff/checkpoint. Historical audit/provenance only for a source dispute. JSON/Markdown full baseline tests are identical; choose one.

Task-specific retrieval command from canonical package: `python3 tools/task_context_v2_1.py --root . --task TK-xxx`. Resolve common-controls pointers. Registry size is not mandatory prompt size; avoid opening all85 task cards or all84 cases by default.

Intermediate repeated text removed: task controls160161 bytes; supplemental248497 bytes; ASVS profiles51276 bytes. These are reductions from unnormalized generated registries, NOT from the smaller original40-file package. Package grew to materialize missing execution contracts. No tokenizer-dependent savings or guaranteed token budget claimed.

Common bundles: P0 source/manifest/TD§1+6+16/EXE; identity tenant AUD12–15; network/RADIUS AUD16–25+MAC05; finance AUD26–32+MAC03; backups/monitoring AUD33–35; ACS AUD36–37+EXE02; UI/i18n AUD38; lab/quality AUD39–46+MAC06–08. Each task below adds its own source requirement IDs.

| Task | Release | Direct dependencies | Requirement IDs |
|---|---|---|---|
| TK-001 | R1 |  | AUD-05, AUD-06, MAC-01, MAC-02 |
| TK-002 | R1 | TK-001 | INF-01 |
| TK-003 | R1 | TK-002 | ACC-11, API-01, API-02, DATA-01, DATA-02, DATA-03, GOAL-02, JOB-01, SYNC-01 |
| TK-004 | R1 | TK-003 | AUD-39, AUD-40, MAC-06 |
| TK-107 | R1 | TK-003 | UX-01 |
| TK-101 | R1 | TK-003, TK-004, TK-107 | SEC-01, TEN-01, TEN-02, TEN-03 |
| TK-102 | R1 | TK-101 | DATA-01, DATA-02, OPS-SEC, PDP-01, PDP-02, PDP-03, PDP-04, PDP-05, RAD-13, SEC-01, SEC-04, SEC-05, TEN-01, TEN-02, TEN-03 |
| TK-103 | R1 | TK-102, TK-107, TK-004 | API-01, API-02, DATA-03, JOB-02, JOB-03, JOB-04, JOB-05, SYNC-03 |
| TK-104 | R1 | TK-102, TK-103, TK-108 | TEN-01, TEN-02, TEN-03, UX-01, UX-02, UX-05 |
| TK-105 | R1 | TK-102, TK-107 | SUB-01, SUB-02, SUB-03 |
| TK-106 | R1 | TK-102, TK-107 | PAY-01, PAY-02, SEC-03 |
| TK-108 | R1 | TK-101, TK-107 | GOAL-06, I18N-01, I18N-02, I18N-03, I18N-04, I18N-05, I18N-06, I18N-07, I18N-08, I18N-09, I18N-10, UX-02, UX-05 |
| TK-109 | R1 | TK-106, TK-108 | BIL-07, BIL-08, I18N-01, I18N-02, I18N-03, I18N-04, I18N-05, I18N-06, I18N-07, I18N-08, I18N-09, I18N-10 |
| TK-201 | R1 | TK-103, TK-105, TK-106, TK-109 | PAY-01, PAY-02, SUB-04 |
| TK-202 | R1 | TK-201, TK-102 | PAY-03 |
| TK-203 | R1 | TK-201, TK-202 | PAY-04, SUB-04 |
| TK-204 | R1 | TK-104, TK-201, TK-107 | PAY-03, UX-01 |
| TK-205 | R1 | TK-201, TK-103 | SUB-05 |
| TK-301 | R1 | TK-102, TK-103, TK-107 | NET-01, NET-03, NET-06, NET-08 |
| TK-302 | R1 | TK-301, TK-304 | NET-01, NET-03, NET-06, NET-08 |
| TK-303 | R1 | TK-301, TK-304, TK-104 | MON-01, NET-04 |
| TK-304 | R1 | TK-102, TK-103, TK-004 | NET-04, NET-05, NET-07, SEC-02 |
| TK-305 | R1 | TK-301, TK-302, TK-304 | NET-02, NET-06, NET-08 |
| TK-306 | R1 | TK-102, TK-103, TK-105 | GOAL-05, RAD-01, RAD-02, RAD-03, RAD-04, RAD-05, RAD-13, RAD-14 |
| TK-307 | R1 | TK-301, TK-306 | RAD-01, RAD-02, RAD-03 |
| TK-401 | R1 | TK-304, TK-103 | GOAL-01, GOAL-03, IMP-01, IMP-05 |
| TK-402 | R1 | TK-401, TK-306 | DATA-01, DATA-02, GOAL-01, GOAL-03, IMP-02, IMP-04, IMP-05 |
| TK-403 | R1 | TK-402, TK-408, TK-410, TK-411, TK-105, TK-108 | GOAL-01, GOAL-03, IMP-02, IMP-03, IMP-04, RAD-09, UX-06 |
| TK-404 | R1 | TK-403, TK-106, TK-107 | CSV-01, CSV-02, CSV-03, GOAL-01, GOAL-03, SEC-03, SUB-01, SUB-02, SUB-03 |
| TK-405 | R1 | TK-104, TK-108, TK-408, TK-410, TK-411 | CUS-01, CUS-02, UX-03, UX-04 |
| TK-406 | R1 | TK-401, TK-402, TK-103 | SYNC-01, SYNC-02 |
| TK-407 | R1 | TK-405, TK-301, TK-307, TK-106 | GOAL-05, LIF-01, LIF-02, LIF-03, LIF-04, PDP-01, PDP-02, PDP-03, PDP-04, PDP-05, RAD-11, SUB-01, SUB-02, SUB-03, UX-06 |
| TK-408 | R1 | TK-102, TK-306, TK-107 | PRO-01, RAD-04, RAD-05 |
| TK-409 | R1 | TK-401, TK-408 | PRO-02 |
| TK-410 | R1 | TK-402, TK-105 | GOAL-01, GOAL-03, GOAL-05, IMP-03, RAD-09 |
| TK-411 | R1 | TK-304, TK-402, TK-106 | GOAL-01, GOAL-03, IMP-03, NET-04, NET-05, NET-07, RAD-09 |
| TK-412 | R1 | TK-405, TK-306, TK-108 | AUD-38, RAD-02, TEN-03 |
| TK-501 | R1 | TK-103, TK-306, TK-307, TK-405, TK-408 | CUS-01, CUS-02, RAD-04, RAD-05, RAD-06, SYNC-03 |
| TK-509 | R1 | TK-302, TK-403, TK-406, TK-501, TK-510, TK-507, TK-511 | GOAL-01, GOAL-03, GOAL-05, RAD-10, RAD-11, RAD-14 |
| TK-510 | R1 | TK-306, TK-103 | MON-01, MON-02, MON-03, MON-04, RAD-07, RAD-14 |
| TK-511 | R1 | TK-306, TK-307, TK-502, TK-503 | MON-05, RAD-08 |
| TK-502 | R1 | TK-303, TK-510, TK-103 | MON-01, MON-02, MON-03, MON-04, MON-05 |
| TK-503 | R1 | TK-502, TK-102 | MON-01, MON-02, MON-03, MON-04, MON-06 |
| TK-504 | R1 | TK-103, TK-106, TK-303 | BKP-01, BKP-02, BKP-04 |
| TK-505 | R1 | TK-304, TK-301, TK-106 | BKP-03 |
| TK-506 | R1 | TK-504, TK-505 | BKP-01, BKP-02, BKP-04, BKP-06 |
| TK-507 | R1 | TK-506, TK-102 | BKP-01, BKP-02, BKP-04, BKP-05 |
| TK-508 | R4 | TK-409, TK-902, TK-905 | PRO-02 |
| TK-601 | R2 | TK-203, TK-405, TK-109, TK-103 | BIL-01, BIL-02, BIL-03, BIL-07, BIL-08, GOAL-02 |
| TK-602 | R2 | TK-601, TK-406, TK-103 | ACT-01, ACT-02 |
| TK-603 | R2 | TK-509, TK-510, TK-602, TK-605 | ACT-03, ACT-04, RAD-06 |
| TK-604 | R2 | TK-601, TK-603, TK-104 | ACT-05, GOAL-02, UX-03, UX-04 |
| TK-605 | R2 | TK-501, TK-602 | ACT-05 |
| TK-606 | R2 | TK-603, TK-604 | ACT-02, EXE-01, JOB-04 |
| TK-607 | R2 | TK-601, TK-003 | ACC-08, ACC-09, BIL-04 |
| TK-608 | R2 | TK-601, TK-003 | BIL-05 |
| TK-609 | R2 | TK-601, TK-102, TK-109 | ACC-03, BIL-06, COL-01, COL-02, COL-03, GOAL-06 |
| TK-701 | R2 | TK-003, TK-601 | ACC-01, ACC-05, ACC-11, ACC-12, GOAL-04 |
| TK-702 | R2 | TK-701, TK-607, TK-608 | ACC-01, ACC-02, ACC-05, ACC-08, ACC-09, GOAL-04 |
| TK-703 | R2 | TK-702, TK-609 | ACC-02, ACC-03, ACC-04, ACC-06, GOAL-04 |
| TK-704 | R2 | TK-703 | ACC-07, GOAL-04 |
| TK-705 | R2 | TK-704, TK-109 | ACC-10, GOAL-04, UX-06 |
| TK-801 | R3 | TK-102, TK-103, TK-301, TK-106 | ACS-01, ACS-02, ACS-03, ACS-04, ACS-05, ACS-06, ACS-08, ACS-09, ACS-10 |
| TK-802 | R3 | TK-801, TK-004 | ACS-01, ACS-02, ACS-03, ACS-04, ACS-05, ACS-06, ACS-08, ACS-09, ACS-10 |
| TK-803 | R3 | TK-802, TK-501, TK-412 | ACS-01, ACS-02, ACS-03, ACS-04, ACS-05, ACS-06 |
| TK-804 | R3 | TK-703, TK-405, TK-102 | ACS-07, OPS-01, OPS-02, OPS-03 |
| TK-805 | R3 | TK-609, TK-804, TK-807, TK-808, TK-108 | OPS-04 |
| TK-806 | R3 | TK-103, TK-108, TK-609, TK-804 | BIL-06, MON-05, OPS-05 |
| TK-807 | R3 | TK-105, TK-306, TK-510, TK-408, TK-703 | GOAL-06, HSP-01, HSP-02, HSP-03, HSP-04, RAD-12 |
| TK-808 | R3 | TK-807, TK-703, TK-102 | ACC-01, ACC-05, AGT-01, AGT-02, AGT-03, GOAL-06 |
| TK-809 | R3 | TK-510, TK-501, TK-603, TK-807 | GOAL-06, HSP-05 |
| TK-810 | R3 | TK-804, TK-601, TK-405 | GOAL-06, LIF-01, LIF-02, LIF-03, LIF-04, OPS-01, OPS-02, OPS-03 |
| TK-811 | R3 | TK-306, TK-307, TK-510, TK-511 | RAD-08, RAD-14 |
| TK-901 | R4 | TK-304, TK-408, TK-104 | CFG-01, CFG-02, WAN-01, WAN-02, WAN-03, WAN-04 |
| TK-902 | R4 | TK-901, TK-406, TK-507, TK-103 | CFG-01, CFG-02, WAN-01, WAN-02, WAN-03, WAN-04 |
| TK-903 | R4 | TK-902, TK-502 | CFG-01, CFG-02, WAN-01, WAN-02, WAN-03, WAN-04 |
| TK-904 | R4 | TK-902, TK-903 | CFG-01, CFG-02, WAN-01, WAN-02, WAN-03, WAN-04 |
| TK-905 | R4 | TK-904, TK-103 | CFG-01, CFG-02, WAN-01, WAN-02, WAN-03, WAN-04 |
| TK-906 | R4 | TK-802, TK-804, TK-902 | ACS-07 |
| TK-1001 | SCOPED_R1_R4 | TK-001 | INF-02, INF-03 |
| TK-1002 | SCOPED_R1_R4 | TK-002, TK-107, TK-1001 | INF-01, INF-02, INF-03 |
| TK-1003 | SCOPED_R1_R4 | TK-103, TK-106, TK-502, TK-511 | NFR-01, NFR-03, OPS-SEC |
| TK-1004 | SCOPED_R1_R4 | TK-506, TK-507, TK-1002 | BKP-05, NFR-02, NFR-04 |
| TK-1005 | SCOPED_R1_R4 | TK-1002, TK-1003, TK-1004, TK-511 | NFR-01, NFR-03 |
| TK-1006 | SCOPED_R1_R4 | TK-102, TK-103, TK-205, TK-407, TK-507, TK-509, TK-1004 | PDP-01, PDP-02, PDP-03, PDP-04, PDP-05, RAD-13 |

Review packet: only current task scope, diff, source clause IDs, relevant contract excerpts, actual test/cleanup evidence and unresolved findings. Codex requests additional source only if needed. Bound3fix rounds; changed hypothesis/new evidence required for rerun. Facts/pricing/model versions are not supplied by this contract.

A separate semantic reviewer is still needed for formal documentation acceptance. A second parser process is described honestly as same-author static verification, not independent semantic review.
