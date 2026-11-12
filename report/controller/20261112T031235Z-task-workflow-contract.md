# MicroTix — keputusan workflow task dan perubahan CONTRACT/docs

Author: Codex / ChatGPT Work controller. Tanggal: 12 November 2026 (Asia/Jakarta). Starting branch: `docs/task-workflow-20261112`, worktree terisolasi dari `origin/main@a2207b66cc705fece79645034ea45900e81a9f38`. Objective: menyimpan instruksi agent di repository, memberlakukan workflow yang telah disetujui dan menyediakan packet PA-006 berikutnya tanpa patch aplikasi.

## 1. Persetujuan normatif dan alasan

**Approval: APPROVED oleh pemilik proyek, 12 November 2026.** Instruksi eksplisit setelah breakdown: “Sip Setuju Masukkan ke contract docs jug agar kedepannya anda atau agent tahu apa yg perlu d lakukan”. Breakdown yang disetujui mencakup task/0000-start-here.md, packet berurutan, suffix _done untuk executor delivery, review terpisah, sandbox-first dan pelaporan/commit/push. Ini izin perubahan workflow/CONTRACT/docs yang konkret, bukan persetujuan untuk implementasi PA-006 pada sesi controller ini atau rollout aplikasi.

Masalah: instruksi tersebar di chat; pengguna perlu menyalin master prompt berulang, dan file handoff lama mengarahkan agent ke prioritas/claim deployment yang sudah ditarik. Bukti: main a2207b6 belum memiliki task/; MASTER_PROMPT menyuruh menyalin prompt dan default menjalankan seluruh roadmap; AGENT_HANDOFF masih memuat snapshot f575388 dan klaim host penahan tunggal tag. Latest handoff aktual justru menetapkan PA-006, lalu PA-002/003, dengan code blockers masih terbuka.

Koreksi minimum: file Markdown dengan nomor tetap dan satu guide; tidak membuat scheduler, database status, orchestrator atau dependency baru. docs/tasks.json tetap backlog produk. Product mission, modular monolith, tenant/network security dan gates tidak diubah.

## 2. Change record (CONTRACT §4)

| Path / bagian | Sebelumnya | Sekarang / alasan |
|---|---|---|
| CONTRACT §2 | Dokumen engineering binding; belum menunjuk task repository | Link entry tetap; packet memiliki scope eksekusi, tidak mengambil otoritas kebutuhan |
| CONTRACT §6A (baru) | Tidak ada naming/status/review/completion convention | Stable 4-digit ID, NNNN-slug[_done].md, controller/executor ownership, same-ID corrections, evidence exact SHA dan verified push, no automatic merge/deploy |
| task/0000-start-here.md (baru) | Pengguna harus meneruskan instruksi dari chat | Entry/resume, eligibility/dependencies, statuses, reports dan completion steps; file guide tidak direname |
| task/0010-pa006-idempotency.md (baru) | PA-006 hanya dirujuk handoff/report | Packet implementasi siap: source evidence, limits, acceptance HTTP/PG, legacy/transaction policy, required review dan penyerahan. Status ready/not_submitted, bukan done |
| README, docs/README | Agent diarahkan menyalin master prompt; README fixed historical test counts | Link entry tetap dan status dari latest handoff, task/ structure; counters historis tetap di report/progress |
| docs/MASTER_PROMPT | Prompt umum default seluruh R1–R4 | Compatibility entry dan general engineering tetap ada, tetapi scope eksekusi dari packet; produk R1–R4 tidak dihapus |
| docs/IMPLEMENTATION_PLAN §2/§3 | Task backlog/milestones saja | Execution packet menaut ke backlog yang sama; _done/review/verifikasi dibedakan |
| docs/AGENT_HANDOFF | Salinan snapshot/prioritas/counter lama + path sandbox tetap | Panduan navigasi/bootstrap stabil; status hanya latest handoff; histori tetap tersedia pada Git/progress/report |
| report/LATEST_HANDOFF, docs/progress | Sesi implementasi PR9 | Tambahkan sesi docs workflow, instruction ref dan task0010, pertahankan riwayat PR9 dan blockers |
| docs/repository-manifest.json | Hash dokumen sebelum edit | Refresh existing checker setelah review; tidak mengecualikan dokumen atau mengubah validator |

Alternatif dipertimbangkan: terus copy-paste (ditolak sesuai permintaan pemilik); membangun task registry/daemon/framework (biaya dan kompleksitas tidak diperlukan); membuat seluruh task roadmap sekaligus (mudah stale dan duplikasi backlog, tidak dipilih). Hanya guide dan satu task siap dibuat; penerus akan ditulis controller ketika dependency dan scope siap.

Impact: product scope/harga/security/release gates tidak berubah. Agent bekerja pada packet bounded; pending-review tidak dieksekusi ulang. Controller acceptance tidak didapat dari filename, dan active session tidak dianggap background automation. Workflow hanya menambahkan metadata/dokumen; tidak ada migration/dependency/runtime changes atau downtime pada sesi ini.

Rollback workflow: revert perubahan dokumentasi melalui Git setelah keputusan pemilik yang relevan; pertahankan task ID/evidence/history yang sudah dipakai. Tidak ada DB/application rollback yang diperlukan. Reverting dokumen tidak mengubah status fitur menjadi released atau menutup defect.

## 3. Baseline dan readiness

Remote main a2207b6, PR9 merged at8ce94d4; PR7/PR8 tetap open dan tidak disentuh. CI main baseline run43043611465 success (backend382passed/1skip, frontend66passed, docsPASS), dibaca pada sesi breakdown sebelumnya; bukan evidence PA-006 implementation. PA-006 source principal/target/race gaps masih ada; task0010 tidak mengklaim perbaikan sudah dibuat. Beta tetap NOT_READY. Native-vs-Compose dan unresolved installer/security/network/recovery gates tidak diputuskan oleh workflow ini.

## 4. Validasi dan review

- Baseline: existing `python3 docs/tools/check_docs.py` PASS (22 files,67links), runtime0/production NOT_EVALUATED.
- `python3 docs/tools/check_docs.py --refresh`, kemudian validator tanpa refresh: exit0/PASS,22files/78links/85tasks/240edges/256designedcases/662assertions; runtime0/production NOT_EVALUATED. Refresh hanya empat hash/size dokumen aktif yang diedit; validator tidak diubah.
- Read-only check seluruh Markdown yang berubah/baru:80local-links PASS, packet naming/stable IDs/ready-not_submitted status dan no deployment access values PASS. `git diff --check` exit0; source/config diff pada backend/apps/installer/Makefile/CI/locales kosong.
- Independent review **APPROVED**: [laporan lengkap](../documentation-review/20261112T031235Z-task-workflow-review.md). DTR-01 meminta acceptance concurrent same-body menjamin eventual replay, bukan permanent409; wording work-item4 dan acceptance diperbaiki lalu dibaca ulang. Tidak ada blocker review tersisa. Approval ini documentation-only, bukan acceptance implementasi PA-006.
- NOT_RUN: application pytest/DB/HTTP/migration/worker/installer/FreeRADIUS/CHR/GNS3/upgrade/restore/production. Sesi ini tidak mengimplementasikan atau menjalankan PA-006.

## 5. Publication and handoff

Saat draft: **NOT PUSHED**; belum commit/PR/merge. Seluruh perubahan masih documentation-only pada branch di atas. SHA publikasi, reviewer outcome dan CI akan diverifikasi dan dicatat setelah validasi, bukan diasumsikan. File tidak diminta memuat SHA commit final dirinya sendiri.

Next executable task setelah instruksi tersedia: executor membaca guide, memverifikasi main/PR delta dan mengerjakan ID0010/PA-006 di sandbox. Panduan/packet tidak mengotorisasi deployment, menerima task sendiri atau merge otomatis. Setelah controller menerima exact PA-006 SHA, siapkan PA-002/PA-003 yang terarah.
