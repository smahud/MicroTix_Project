# MicroTix — independent review default agent prompts

Author/role: Codex sub-agent `/root/default_prompts_review`, independent documentation reviewer. Objective: memeriksa dua prompt default executor/controller reviewer agar dapat dipakai pada sesi baru/resume tanpa kehilangan scope, konteks, bukti atau kewenangan. Starting branch `docs/default-agent-prompts-20261112`, worktree terisolasi, baseline `main@2278b7741bb5ec38757cc7d3659b9099c31341ea` (tree `8a7f8aec838811bcfc40a6c9c5e885137f45e0bc`).

## Scope dan otoritas

Permintaan pemilik secara eksplisit: siapkan master prompt default kedua peran untuk seluruh sesi berikutnya; fokus Production Beta, tanpa overengineering. Acuan: CONTRACT §2–6A/§9–13, task/0000-start-here.md, packet0010 existing dan LATEST_HANDOFF sebagai konteks, serta dokumen pemilik kebutuhan yang ditautkan. Review ini hanya dokumentasi workflow; bukan acceptance implementasi PA-006 atau bukti Beta ready.

Files yang diperiksa: `docs/MASTER_PROMPT_EXECUTOR.md`, `docs/MASTER_PROMPT_REVIEWER.md`, perubahan CONTRACT/entry guide, serta navigation/handoff/report/manifest setelah final draft tersedia. Application code read-only; reviewer hanya menulis report ini. Tidak ada perubahan source, dependency, migrasi, installer atau deployment oleh reviewer.

## Findings dan closure

| ID | Risiko/evidence awal | Koreksi minimum dan acceptance | Status |
|---|---|---|---|
| DPR-01 (P2, wording) | Executor §4, awal line35: "Simulator/mocks/CI bukan bukti FreeRADIUS/CHR/GNS3... nyata" terlalu absolut; sebuah CI job dapat benar-benar menjalankan daemon/DB nyata | Bedakan status CI hijau saja dari runtime evidence dengan real dependencies; klaim tetap sebatas environment/assertions yang benar-benar dijalankan | **CLOSED**: final executor §4 membedakan CI status saja dari tes real dependency/environment/assertions; dibaca ulang dan diperiksa independen |

Final review tidak menemukan blocker lain. Role prompts terpisah, tetapi tetap memakai satu entry/workflow dan kebutuhan domain existing; tidak menduplikasi kebijakan teknis atau backlog. Root AGENTS.md hanya pointer singkat, bukan framework atau product policy baru. MASTER_PROMPT lama menjadi indeks kompatibel, sehingga tidak ada prompt executor ketiga yang berpotensi bertentangan.

| Acceptance review dokumentasi | Actual result / evidence |
|---|---|
| Reusable pada sesi berikutnya tanpa stale task/SHA | PASS: kedua prompt membaca actual refs/PR/candidate/report saat start/resume; scan tidak menemukan exact40hex SHA, task0010 atau PA-00x yang mengunci task aktif |
| Executor/controller memiliki scope dan authority jelas | PASS: executor implement/tests/reports; controller review exact SHA/keputusan/task, application-code correction kembali ke executor; acceptance/merge/rollout tetap terpisah |
| Same-ID corrections dan completion truthful | PASS: `_done` hanya completed executor delivery, pending review tidak diulang, findings membuka ID sama, required tests/published ref/CI diverifikasi; dependency tertahan hingga review/integration relevan |
| Context recovery dan komunikasi GitHub | PASS: task/instruction/base/candidate/tested/reviewed refs, status/evidence limits/next actor tersimpan pada packet/report/handoff; partial checkpoint tidak diklaim done; NOT PUSHED eksplisit |
| Fokus Beta tanpa overengineering | PASS: scope packet dan existing stack/domain tetap; read-only targeted review sesuai risiko, tidak ada service/engine/backlog baru; phase/scale belum terukur tidak diklaim siap |
| Entry/navigation dan status aktual konsisten | PASS: AGENTS, CONTRACT, guide, README, docs index, compatibility MASTER_PROMPT dan AGENT_HANDOFF menunjuk dua prompt; LATEST_HANDOFF menjelaskan snapshot main, draft instruction branch dan PA006 not_submitted |
| Evidence/perubahan source aman | PASS: doc validator/manual links/diff bersih; source/config/installer/CI/locales tidak berubah, packet0010 identik dan taskdir tidak ditambah/ditutup palsu |

## Pemeriksaan dan batas evidence

Initial checks: pembacaan file dengan `nl -ba`/`sed`, `git status --short`, `git rev-parse HEAD`, `git diff --stat` dan scoped `git diff`; exit0. Baseline/worktree cocok, packet0010 tetap ready/not_submitted dan belum ada penyerahan kode yang dinilai reviewer. Ini observasi draft lokal, bukan remote publication verification.

Final independent checks, seluruhnya exit0:

- `python3 docs/tools/check_docs.py`: PASS24staticfiles/106internal-links, 85tasks/240dependencyedges, 256designedcases/662assertions, runtime0/production NOT_EVALUATED. Reviewer tidak melakukan refresh manifest atau mengubah validator.
- Manual changed-Markdown linkcheck dengan `docs/tools/check_docs.py::check_links`: PASS106local-links pada13Markdown dari14changed/untrackedfiles; semua destination tersedia, termasuk report ini. Checker memeriksa file tujuan, bukan isi section anchor atau external URL.
- `git diff --check`: PASS. `git diff --quiet 2278b7741bb5ec38757cc7d3659b9099c31341ea -- backend apps instalasi.sh Makefile .github locales`: exit0, tidak ada source/config/installer/CI/locales change. `git diff --quiet <baseline> -- task/0010-pa006-idempotency.md`: exit0, packet existing identik.
- One-off Python scan dua prompts: tidak ada exact40hex SHA, PA-00x/task0010 hardcode atau access/credential markers yang diperiksa. Task directory tepat `0000-start-here.md` dan unfinished `0010-pa006-idempotency.md`; tidak ada `_done` atau successor palsu.

Reviewed prompt content SHA256: executor `fcdcefc5d2486a0dc17f451c223a5ebacf6c16f82c8048bd9de536f7ef286a82`; reviewer `1e3b8a14081befed67a5da0634307896f963476b7f25d97845b63e888cec8e11`. Ini identitas byte draft yang direview terhadap baseline, bukan klaim commit candidate sudah ada. Publication/ref final diverifikasi parent setelah commit.

Application tests, PostgreSQL/HTTP runtime, browser, installer/upgrade/restore, FreeRADIUS/CHR/GNS3, benchmark dan production access **NOT_RUN**, di luar scope review dokumen. Peninjauan tidak membuktikan execution PA006, deploy readiness atau release Beta.

## Penyerahan

Verdict: **APPROVED untuk dokumentasi default prompts**; DPR-01 closed, tidak ada finding terbuka atau blocker pada scope. Publication: **NOT PUSHED** oleh reviewer; parent bertanggung jawab mempublikasikan report/dokumen dan memverifikasi remote SHA/CI/integrasi sesuai kewenangan. Tidak ada klaim self-referential future commit SHA.

Next actor: controller `/root`; isi hasil checks/review pada report/handoff miliknya, publish documentation candidate, verifikasi final-head CI/diff/main delta dan integrasikan hanya sesuai kewenangan yang berlaku. Product next actor tetap coding agent sesuai task/handoff aktual; prompt/document review tidak menyelesaikan PA-006 atau memberi izin rollout.
