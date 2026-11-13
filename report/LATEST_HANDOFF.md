# LATEST_HANDOFF — 13 November 2026: controller requests PA-006 corrections

Pintu masuk tetap: [task/0000-start-here.md](../task/0000-start-here.md); CONTRACT §6A dan [prompt reviewer](../docs/MASTER_PROMPT_REVIEWER.md) berlaku. Ini snapshot terbaru keputusan controller pada ref di bawah; main dan branch executor belum memuat perubahan status ini sampai diintegrasikan.

## 0. Task dan tindakan berikutnya

| Field | Status / pointer |
|---|---|
| Active task | **0010 / PA-006**, reopened [0010-pa006-idempotency.md](../task/0010-pa006-idempotency.md), ID tetap |
| Execution / review | **ready / changes_requested** |
| Instruction / canonical main | `main@9903d9b0cf09d737b553da3c21067b4810e956c0`; source PA-001 sudah merged PR9 |
| Candidate reviewed | [PR #15](https://github.com/smahud/MicroTix_Project/pull/15), `session/2026-11-13-pa006-idempotency@7480c80e2c27b8b06048b77132d235efe6b3a3c2` |
| Executor code/tested ancestor | `159f7edac42d6cb49093feeba3fa8cd0b1e775a1`; delta source ke reviewed head kosong |
| Controller decision | [20261113T114222Z-0010-pa006-review.md](controller/20261113T114222Z-0010-pa006-review.md), **changes_requested**, bukan acceptance |
| Decision ref | `review/0010-pa006-controller-20261113`; publication commit/PR/verified status pada report controller §6. Belum merged ke main atau branch PR15 |
| Next actor | **coding_agent** |
| Exact next action | Fetch decision ref; bawa task/report/pointer secara semantik ke correction branch dari kandidat existing; perbaiki REV-1311-01/02/03, jalankan closing tests+regression+required CI dan resubmit exact SHA pada **ID0010 yang sama** |
| Dependency gate | PA-002/PA-003 **belum eligible**; PA-006 belum accepted/integrated. Jangan membuat packet duplikat atau mengulang PA-001 |

## 1. Bukti controller dan koreksi wajib

Dua sub-reviewer independen memeriksa semua 28 call sites dan protokol/race/migrasi secara read-only. Root memverifikasi source dan menjalankan PostgreSQL17.11 nyata dengan peran `mtx_app` NOSUPERUSER/NOBYPASSRLS: **55 targeted passed; full suite408 passed; lima additional conformance probes FAIL** yang membuktikan gap acceptance. CI kandidat exact head7480c80 run43336914973 backend/frontend/docs success; hijau bukan acceptance.

| Finding | Hasil aktual / koreksi |
|---|---|
| **REV-1311-01 P1** | Legacy proof scope lama dilewati saat upgrade → submission kedua. Rekonsiliasi retained key per actor/tenant/invoice dan ambiguous effects; jangan replay invoice A ke B |
| **REV-1311-02 P1** | Same group/key/body pada sesi migrasi A/B →204/204 tetapi keputusan **[2,0]**; malformed/missing parent juga replay204. Sertakan canonical migration_id + opaque group_id sebelum replay |
| **REV-1311-03 P2** | Typed UUID package_id alias dalam body →200 lalu409 untuk target sama. Canonicalize declared identity fields sebelum HMAC, preserve semantic strings dan actual body/file conflicts |

[Report controller](controller/20261113T114222Z-0010-pa006-review.md) memuat acceptance matrix, path/line, minimum fix, closing tests, bukti reproduksi dan batas verifikasi. Laporan [scope reviewer](controller-scope/20261113T113917Z-0010-pa006-scope-review.md) dan [race reviewer](controller-race/20261113T113941Z-0010-pa006-race-review.md) dipersist lengkap dengan atribusi; mereka tidak menjalankan tes runtime. Root menjalankan probes yang disiapkan reviewer.

INSERT-first atomic claim/effect/response, principal uniqueness, explicit new platform scope dan current permission/step-up-before-replay telah diverifikasi pada kasus existing. Executor-internal takeover/route-alias evidence gaps sudah ditutup; jangan mengimplementasikan ulang. Malformed platform submission404→422 konsisten kontrak existing dan diterima; non-platform404 tetap dijaga. Ini tidak menutup tiga finding di atas.

## 2. Submission dan cabang yang dipertahankan

- Penyerahan awal executor: [orchestrator report](orchestrator/20261113T003000Z-0010-pa006-idempotency.md) dan [internal reviewer](reviewer/20261113T001500Z-0010-pa006-review.md), historis/preserved. `_done` pada branch executor berarti delivered, bukan accepted; correction packet pada decision ref dibuka kembali.
- PR15 kandidat PA-006 tetap terbuka, tidak ditimpa/merged reviewer. PR13 `not_submitted` tanggal12 November adalah observasi lama, **superseded** oleh penyerahan PR15 dan review ini, bukan candidate implementasi alternatif.
- PR14 `docs/payment-point-planning-20261113@2a9803593c328ab014bab6695b298072ed4c1886` adalah proposal dokumentasi future Payment Point; tidak dipilih sebagai pekerjaan Beta aktif.
- PR8 `docs/planning-audit-20261110@6bb57c9` dan PR7 `session/2026-11-07-sstp-phase2@d7fa35e` tetap terpisah/unmerged; file ownership tidak disentuh. Dokumen manifest PR8 dan disposition PR7 belum diputus sesi ini.
- PR9 PA-001 sudah merged; arsip branch lama `session/2026-11-11-pa001-payment-concurrency`, `parallel/beta-be2`, `integration/beta-0.1` dan sesi06/07 tetap dipertahankan.

## 3. Beta tetap NOT_READY — code blockers dan environment gates

Register lama berbukti: [controller 20261111](controller/20261111T074225Z-repo-handoff-review.md). Review PA-006 ini tidak menghapus blocker lain.

| Blocker | Finding / dependency |
|---|---|
| PA-006 retained-key, nested resource dan typed body gaps | REV-1311-01/02/03, task0010 corrections |
| Installer clean-install: joined args + dependency xhtml2pdf | REV-1111-04, S4 |
| Upgrade/repair false success, HTTPS downgrade, shallow readiness | REV-1111-05, S4 |
| Worker drain/fencing/stale-writer/authority | REV-1111-06, PA-002/PA-003 setelah review/integration prerequisite |
| Restore end-to-end dan secret/migrator separation | REV-1111-07, S4 |
| Native vs Compose topology | DEC-01 / REV-1111-08, keputusan pemilik sebelum rehearsal S4 |
| Invoice scheduler belum terpasang | REV-1111-09, S4 |
| Selected-set/scanner/operation permission gaps lainnya | Sisa REV-1111-11, scope berikut sesuai dependency |
| Kapasitas 1.000 tenant ×1.000 online | REV-1111-12, belum dibenchmark; bukan otomatis blocker semua task |

Gate A/G host Debian13, real MikroTik/CHR G1, GNS3 API-driven berlisensi dan restore/DR tetap memerlukan eksekusi nyata setelah code/readiness gate terkait. Tidak ada akses/aksi deployment atau mutasi router sesi ini.

## 4. Batas dan resume

- PostgreSQL sandbox dan real-binary config check bukan verified_lab/perangkat, host install/upgrade, DR atau capacity.
- Atomic DB protocol tidak membuat file effects transactional; old/new code tidak aman overlap setelah constraint principal diperluas. Correction report harus menjelaskan drain/order/fix-forward; task0010 tidak memperluas ke installer.
- Disclosed preexisting malformed tenant URL500 berasal dari resolve_membership sebelum decorator; tetap follow-up di luar permitted helper/owner-view boundary, bukan klaim semua input422.
- Urutan berikut: **koreksi0010 → controller rereview exact new SHA → integration prerequisite → PA-002/PA-003**. DEC-01/DEC-02/PR7 serta S4 mengikuti wewenang/dependency existing.
- Saat resume, fetch actual main/candidate/decision refs dan PR/CI. Jangan menganggap status ready/not_submitted di main atau _done/pending di PR15 mengalahkan published controller decision. File tidak meluncurkan coding agent otomatis.
