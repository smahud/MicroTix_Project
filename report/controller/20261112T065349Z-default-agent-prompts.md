# MicroTix — default prompts executor dan controller reviewer

Author/role: Codex / ChatGPT Work controller. Tanggal 12 November 2026 (Asia/Jakarta). Objective: dua master prompt default yang berlaku untuk seluruh sesi baru/resume, memastikan agent tetap memahami scope, konteks dan jalur menuju Production Beta. Starting branch `docs/default-agent-prompts-20261112`, isolated worktree dari `main@2278b7741bb5ec38757cc7d3659b9099c31341ea`, tree `8a7f8aec838811bcfc40a6c9c5e885137f45e0bc`.

## 1. Baseline dan keputusan yang diotorisasi

Instruksi pemilik secara eksplisit meminta prompt default executor dan reviewer untuk semua sesi, menjaga konteks/rencana. Ini melanjutkan persetujuan workflow task dan CONTRACT pada 12 November 2026. Aturan peran/checkpoint dalam CONTRACT §6A diotorisasi oleh permintaan tersebut; tidak mengubah product scope, kontrak teknis, kebijakan keamanan atau release gates. Requirement references: CONTRACT §2–6A/§9–13, task/0000-start-here.md §1–6, PRODUCT/ARCHITECTURE/ACCEPTANCE dan IMPLEMENTATION_PLAN.

Remote main/PR dan `git fetch`, refs/worktrees/status diperiksa langsung. PR10/PR11 sudah merged. PR7 SSTP dan PR8 planning-audit masih terbuka; tidak disentuh. Task0010 PA006 tetap ready/not_submitted: tidak ditemukan candidate implementasi/report penyerahan pada refs/PR yang diperiksa; ini tidak menyimpulkan tidak ada pekerjaan lokal yang belum dipush. PA001 PR9 sudah merged dan tidak diulang. Beta tetap NOT_READY.

Sebelum perubahan, docs/MASTER_PROMPT.md memberi instruksi umum executor, belum ada prompt tetap controller reviewer yang sejajar. Workflow/record komunikasi sudah tersedia, sehingga solusi hanya dua dokumen peran dan tautan ke aturan existing. Tidak diperlukan service, scheduler, workflow engine atau backlog lain.

## 2. Controlled documentation change — CONTRACT §4

| Dokumen/section | Sebelumnya → sekarang dan alasan |
|---|---|
| CONTRACT §6A | Entry/task/report protocol → tambahkan dua prompt peran permanen, dynamic GitHub discovery dan checkpoint existing; mencegah role/context drift sesuai permintaan pemilik |
| docs/MASTER_PROMPT.md | Prompt executor generik → indeks kompatibel dengan dua role links dan satu kalimat launch per peran; menghindari tiga prompt tandingan |
| docs/MASTER_PROMPT_EXECUTOR.md | Baru: discovery/resume→bounded implementation→tests→published delivery; tidak hardcode task/SHA atau menyusun kebijakan domain sendiri |
| docs/MASTER_PROMPT_REVIEWER.md | Baru: reconstruct candidate→targeted independent review→exact-SHA verdict/same-ID corrections→next eligible packet; application code read-only pada peran ini |
| AGENTS.md | Baru: entry singkat yang ditemukan agent saat masuk repo, menunjuk kontrak/guide dan prompt sesuai peran; bukan sumber kebijakan tandingan |
| task/0000, README, docs/README dan AGENT_HANDOFF | Tautan peran pada entry existing; hapus current-task hardcode pada guide permanen, status aktual tetap milik latest handoff/task/refs |
| LATEST_HANDOFF/progress | Refresh observed main/PR11 dan pointer prompts/report; PA006 status/acceptance tidak berubah |
| repository-manifest.json | Refresh inventory/hash menggunakan checker existing setelah diff ditinjau; validator tidak diubah |

Pilihan lain: mempertahankan prompt executor saja (reviewer tetap bergantung chat); menyalin semua kebijakan/roadmap ke tiap prompt (duplikasi dan stale context); membangun orchestrator (biaya berlebih). Dipilih bootstrap peran yang membaca sumber keputusan existing dan menyimpan checkpoint pada packet/report/handoff. Prompt bukan task dan tidak diberi `_done`.

Impact: no application/data/API/migration/dependency/deployment change, no downtime. Scope packet/requirement/domain/release authority tetap. Tidak ada deployment access details atau secret dalam prompt. Rollback melalui reviewed documentation revert bila perlu, mempertahankan task IDs dan laporan historis. Approval: instruksi pemilik sesi ini; independent documentation review di §3, publication di §4.

## 3. Checks dan review

Actual preliminary checks: GitHub main/open PR metadata, fetch refs, status/worktrees, current task/contract/handoff dan existing prompts diperiksa. Source implementasi PA006 tidak diubah atau diuji di sesi ini.

Post-edit `python3 docs/tools/check_docs.py --refresh` lalu tanpa refresh: exit0/PASS24files/106internal-links/85tasks/240edges/256designedcases/662assertions, runtime0/production NOT_EVALUATED. Manual changed-Markdown link check memakai fungsi validator existing: 106local-links PASS sebelum tautan report review ditambahkan. `git diff --check` exit0; diff source/backend/apps/installer/Makefile/CI/locales kosong. Packet0010 byte-identical dan task directory tetap hanya0000+0010 unfinished. Dua prompt tidak memuat historical task ID/SHA atau deployment access markers; root AGENTS dan entry lain menunjuk sumber yang sama.

Independent review **APPROVED**, tidak ada blocker terbuka, di [report reviewer](../documentation-review/20261112T065349Z-default-agent-prompts-review.md). Reviewer hanya menulis report miliknya sendiri dan mengulang docs/link/scope checks secara independen. DPR-01 closed: wording CI diperjelas agar CI dengan dependency nyata tetap dihitung sebagai bukti untuk environment/assertions yang benar-benar dijalankan; CI hijau saja tidak membuktikan gate lain. Approval hanya dokumentasi, bukan acceptance PA006. Parent final staged diffcheck/tautan: exit0/PASS107local-links pada14files sebelum publikasi awal. Dua prompt byte-identical dengan hash draft yang di-approve reviewer.

NOT_RUN oleh controller: application pytest/frontend/browser, DB/HTTP/migrations/jobs, install/upgrade/restore, FreeRADIUS/CHR/GNS3, benchmarking/pilot dan production deployment. Tidak ada dependency/runtime/host yang diubah. CI otomatis bila dijalankan akan dicatat terpisah, bukan diklaim sebagai tes controller atau perangkat nyata.

## 4. Publikasi, completion dan kelanjutan

Paket default prompts **PUBLISHED dan remote terverifikasi**: [PR12](https://github.com/smahud/MicroTix_Project/pull/12), branch `docs/default-agent-prompts-20261112`, commit `639dca9d7d9c1d8509cdc3dd0aa43597b37af9fc`, tree `8a3c956ab2857eed9281bd395c3ecfe4290114e0` identik staged tree lokal. Diff14files seluruhnya dokumentasi/manifest; independent review APPROVED. Closure descendant hanya memperbarui publication/checkpoint pada report/handoff/progress, tidak mengubah prompt/acceptance/source.

CI awal run43172575713 masih in_progress pada checkpoint publikasi ini; tidak diklaim PASS. Final head/ref/CI dan integration outcome dicatat pada metadata PR/Git setelah checkpoint ini. Controller memverifikasi required CI final head, scope diff, current main delta dan expected-head sebelum mengintegrasikan dokumentasi yang diminta pemilik; ini bukan approval merge aplikasi atau deployment. Record menunjuk published ancestor dan tidak mensyaratkan SHA final file sendiri.

Next actor pekerjaan produk: **coding_agent**. Exact action: jalankan docs/MASTER_PROMPT_EXECUTOR.md, fetch refs dan implementasikan/resume packet0010/PA006 yang eligible di sandbox; serahkan candidate/report sebelum controller mereview hasil. Prompt reviewer dipakai setelah penyerahan; bila belum ada, reviewer mencatat not_submitted dan mengarahkan ke packet existing, tidak membuka task0020 dependent.

Dokumentasi siap dipakai setelah checks/review/publikasi; **Production Beta tetap NOT_READY** sampai code/deploy/recovery/feature-specific lab gates terbukti. Sesi ini tidak menjalankan external executor atau mengimplementasikan PA006.
