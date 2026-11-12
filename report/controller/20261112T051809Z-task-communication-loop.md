# MicroTix — pemeriksaan dan pelengkapan jalur komunikasi task

Author/role: Codex / ChatGPT Work controller. Tanggal: 12 November 2026 (Asia/Jakarta). Starting branch `docs/task-communication-loop-20261112`, isolated worktree pada `main@a0f653e89bf77b1238ca0ed9bcdb0e2f0aee612e`. Objective: memeriksa bukti hasil task dan memastikan loop controller→coding agent→review→koreksi/task berikutnya persisten di GitHub, kemudian mengembalikan pekerjaan ke task eligible yang tertunda.

## 1. Scope, keputusan pemilik dan fakta baseline

Instruksi pengguna sesi ini secara eksplisit meminta pemeriksaan alur dan menyiapkan yang belum ada: semua komunikasi reviewer/coding agent terdokumentasi di GitHub, tanpa salah persepsi, lalu melanjutkan jalur menuju Beta. Ini mengotorisasi pelengkapan workflow dokumentasi. Perubahan CONTRACT §6A merupakan penajaman aturan komunikasi yang telah disetujui 12 November 2026, bukan perubahan product scope, arsitektur, hak deployment atau release gates.

Remote/PR/CI diperiksa langsung, tidak hanya dari chat lama:

| Item | Evidence aktual |
|---|---|
| Main | a0f653e89bf77b1238ca0ed9bcdb0e2f0aee612e; tree63916f4ee48b60642a95184cc61cebb8239cd492 |
| PR10 workflow | MERGED, 12 November2026 03:26:58Z; entry/packet/CONTRACT sudah ada di main |
| CI main | Run43148282521 completed/success; tidak direrun controller pada pemeriksaan awal |
| Task0010/PA006 | ready/not_submitted; tested SHA, candidate PR, execution/review report belum diserahkan; tidak ada _done file |
| Published implementation result | Tidak ditemukan task0010/PA006 implementation branch/PR/report pada remote refs, daftar PR dan tree yang diperiksa; ini bukan klaim bahwa tidak pernah ada pekerjaan lokal yang belum dipush |
| Open PR lain | PR7 SSTP/lab dan PR8 planning audit; keduanya tidak disentuh |
| Last implementation | PA001 PR9 sudah merged; PR10 setelahnya documentation-only. Tidak ada bukti task0010 dikerjakan hanya karena instruksinya tersedia |

## 2. Penilaian alur sebelum perubahan

Fondasi sudah mendukung: entry permanen, ID/suffix/status, required reports, controller/executor roles dan exact-SHA review. Mekanisme itu belum menjelaskan secara cukup eksplisit isi komunikasi dua arah dan publikasi per pergantian peran.

| Gap | Dampak | Koreksi minimum |
|---|---|---|
| Execution report generic tanpa acceptance→actual evidence matrix yang eksplisit | Reviewer dapat menerima jumlah tes tanpa tahu assertion/scope mana yang terbukti | Wajibkan matrix hasil nyata/FAIL/NOT_RUN/BLOCKED, tested/published SHA, report/CI pointer dan unfinished work |
| Review tidak dirumuskan sebagai persisted controller record dengan corrections/next actor | Keputusan bisa hanya tersimpan di chat atau disalahartikan sebagai internal executor review | Versioned review report exact SHA + finding/closure + verdict + next actor/action; controller owns acceptance |
| Main ready dapat dibaca tanpa memeriksa hasil di unmerged PR | Agent baru dapat mengulang implementasi yang sebenarnya menunggu review | Cari task ID pada refs/PR/report; instruction/result ref dinyatakan eksplisit |
| Handoff belum punya pointer hasil/review dan pihak berikutnya yang terpisah | Coding/reviewer bisa saling menunggu atau melompat ke task0020 | Tampilkan active task/status/result/review/actor/action; pending0010 kembali ke coding agent |

Independent reviewer mengonfirmasi gap ini. Tidak diperlukan queue service, daemon, repository code abstraction atau produk backlog kedua. Tidak membuat template/record hasil kode palsu.

## 3. Change record — CONTRACT §4

Approval: instruksi pemilik sesi ini meminta pelengkapan langsung bila alur belum cukup. Penajaman sebelumnya→baru:

- CONTRACT §6A: existing workflow generik → record GitHub per role wajib, cross-ref/PR discovery, acceptance evidence matrix, separate controller review dan next actor/action sebelum dependent work.
- task/0000-start-here.md: existing selection/completion → cek unmerged candidate ID dan protokol komunikasi §6: task→delivery→review→same-ID correction atau accepted→next task. Domain docs tetap authoritative; docs/tasks.json tetap satu backlog.
- task0010: combined unset pointer → field candidate, execution report, controller review/reviewed SHA, next actor/action dan truthful empty result summary. Acceptance PA006 tidak diubah atau diperlemah; belum ada implementasi/done.
- docs/MASTER_PROMPT dan AGENT_HANDOFF: tautkan protokol yang sama, internal executor review bukan controller acceptance.
- Latest handoff/progress: refresh observed main/PR10 evidence; active task0010 dengan coding_agent sebagai actor berikutnya. Riwayat implementation PR9 dipertahankan, tidak dianggap hasil PA006.
- Active-doc manifest diperbarui dengan checker existing setelah review edit; validator, task backlog, technical defaults dan application code tidak diubah.

Alternatif: menganggap aturan generik cukup (ambiguity masih ada); membuat workflow engine/template registry (biaya tak perlu); menyimpan verdict hanya di chat/PR comment (tidak memenuhi permintaan durable repo communication). Pilihan: tambahan in-place pada guide/packet/contract dan report existing layout.

Impact: no product/tenant/security/network/financial/release scope change, no dependency/migration/deployment/downtime. Koordinasi berbasis file selama sesi aktif; tidak mengklaim menjalankan/membangunkan external agent. Rollback dokumentasi melalui reviewed revert bila perlu; preserve evidence/task IDs yang sudah dipakai. Tidak ada application rollback.

## 4. Validasi, review dan batas evidence

Checks awal: git fetch/status/refs/log/tree/diff, current task/CONTRACT/handoff/report read; GitHub main/PR/workflow metadata. Review source diff dari pre-PR10 terhadap baseline menunjukkan workflow docs tidak mengimplementasikan PA006. Code execution/race tetap NOT_RUN.

Post-edit `python3 docs/tools/check_docs.py --refresh`, lalu tanpa refresh: exit0/PASS22files/78links/85tasks/240edges/256designedcases/662assertions, runtime0/production NOT_EVALUATED. Hanya hash/size MASTER_PROMPT berubah pada manifest; validator tidak diubah. Manual changed-Markdown linkcheck pada draft40local-links PASS; task status ready/not_submitted, next actor coding_agent dan no _done/access values PASS. Mandatory work dan acceptance PA006 diekstrak/dibandingkan ke base dan identik. `git diff --check` exit0; application/config/installer/Makefile/CI/locales diff kosong.

Independent final review **APPROVED**, tidak ada blocker: [laporan reviewer lengkap](../documentation-review/20261112T051809Z-task-communication-review.md). Kelima gap baseline ditutup; evaluator memverifikasi40local-links, PA006 work/acceptance/verification tetap utuh dan source diff kosong. Approval hanya dokumentasi komunikasi; bukan acceptance implementasi PA006. Checks parent terakhir mencakup link laporan yang baru ditambahkan di paragraf ini sebelum publikasi.

NOT_RUN sesi controller: app pytest/frontend browser, DB/HTTP/migrations/jobs, installer/upgrade/restore, FreeRADIUS/CHR/GNS3, benchmarking dan production access. No dependency install. Tes yang tercantum dalam packet adalah acceptance untuk executor, bukan hasil sesi ini.

## 5. Penyerahan dan kelanjutan aktual

Paket instruksi/keputusan **PUBLISHED dan remote terverifikasi**: [PR11](https://github.com/smahud/MicroTix_Project/pull/11), branch `docs/task-communication-loop-20261112`, commit `7e7f90e930311e5da5e3b35d77a490c6e9c7100d`. Remote tree `612e128ecfb32fc12d0337f8d243d96ed95c88d1` identik local staged tree. Diff10files seluruhnya dokumentasi/manifest; independent review APPROVED. Closure metadata sesudahnya hanya mencatat pointer publikasi, tidak mengubah acceptance atau source.

CI first package run43161320513 masih in_progress pada checkpoint publikasi ini; tidak diklaim PASS sebelum teramati. Final head/ref/CI dan outcome integration tercatat di metadata PR/Git setelah checkpoint ini. Controller memverifikasi required CI pada final head, scope diff, main delta dan expected-head sebelum mengintegrasikan perubahan dokumentasi yang diminta pemilik. Ini bukan approval merge kode aplikasi atau deployment. Report tidak diminta memuat SHA akhir commit dirinya sendiri; gunakan hubungan tested/reviewed ancestor dan published candidate yang aktual.

Next actor untuk pekerjaan produk: **coding_agent**. Next action: baca entry tetap, fetch refs/PR aktual, claim/resume task0010/PA006 di sandbox dan kirim candidate+execution report dengan evidence. Hasil belum dipublikasikan berarti controller tidak memaksakan review hasil kosong atau membuka task0020. Setelah PA006 accepted dan dependency integration sah, controller menyiapkan PA002/PA003.

Communication workflow menjadi siap setelah checks/review/publikasi penajaman ini; **Production Beta tetap NOT_READY** sampai required code, deploy/recovery dan feature-specific lab gates terbukti. Tidak ada klaim implementasi atau start external z.ai/Claude dari sesi ini.
