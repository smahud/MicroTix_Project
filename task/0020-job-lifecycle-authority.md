# 0020 — PA-002 + PA-003: job aman terhadap stale worker dan perubahan kewenangan

| Field | Nilai |
|---|---|
| Task ID | `0020`; satu packet untuk lifecycle + authority yang saling bergantung |
| Execution status | `ready` |
| Review status | `not_submitted`; belum ada kandidat implementasi atau hasil tes task ini |
| Controller / executor | ChatGPT Work controller / coding agent sandbox |
| Baseline | `main@41d1f33f16508491a34f66b767830b9dd3e5954e`; fetch ulang dan periksa delta sebelum bekerja |
| Instruction ref | `review/0020-job-lifecycle-authority-20261117`; baca packet ini pada ref tersebut atau descendant yang sudah diintegrasikan, bukan packet0010 dari branch lama |
| Accepted predecessor | [0010 / PA-006](0010-pa006-idempotency_done.md), accepted exact `a301a94c2b3268679065e85bbef66f35949483f7` pada [R5 review](../report/controller/20261116T101809Z-0010-pa006-r5-review.md); PR24+PR25 merged ke main, [integrasi](../report/orchestrator/20261116T111835Z-0010-pa006-integration.md) |
| Authority | [CONTRACT](../CONTRACT.md) §§5–6A/8–13; [PRODUCT](../docs/PRODUCT.md) TEN-03, JOB-02–05, SEC-01/04/05, SUB-05; [ARCHITECTURE](../docs/ARCHITECTURE.md) §§3–6; [OPERATIONS](../docs/OPERATIONS.md) §§3–4; [ACCEPTANCE](../docs/ACCEPTANCE.md) §4 |
| Backlog / tests | Existing TK-101/102/103 dan bagian drain TK-1002; katalog T06-CRASH-01/02/03, T10-TEN-03; T05/T14 hanya invariant current-state yang relevan, bukan seluruh fitur R2/DR |
| Controller report | [Review dan dasar packet](../report/controller/20261116T231131Z-0020-job-lifecycle-review.md) |
| Implementation / tested SHA / candidate / CI | Belum diserahkan; isi dengan bukti aktual saat delivery |
| Next actor / action | `coding_agent`: fetch instruction ref, implementasikan dan buktikan acceptance di bawah; serahkan exact SHA untuk controller review |

PA-002/PA-003 adalah label kontinuitas audit, bukan otoritas baru. PR8 planning_audit masih draft/unmerged; kebutuhan packet ini seluruhnya diturunkan dari kontrak main di atas. Prasyarat PA-006 sudah accepted/integrated dan tidak dibuka kembali. PA-001 pembayaran juga dipertahankan. Packet ini tidak memberi izin merge, deploy, tag atau aktivasi fitur.

## Tujuan dan batas

Perbaiki jalur job **yang sudah terdaftar saat ini** agar pemilik lama tidak bisa menimpa hasil/mengirim efek setelah kehilangan kewenangan, pembatalan/retry tidak menyembunyikan efek tak pasti, dan worker dapat drain dengan hasil durable. Reuse modular monolith dan PostgreSQL jobs/outbox existing. Jangan membangun handler fase depan, queue/broker, orchestration service, generic DSL atau framework authorization baru.

Sebelum edit, tulis inventory ringkas di laporan: setiap active kind dan enqueue origin, permission/membership/router scope, actor atau trusted-system provenance, policy/revision, effect boundary DB/send/file, verifier, deadline/heartbeat, retry/recovery. Cakup customers, network, radius dan backup handler existing. Identifikasi DB-only vs external effects; jangan menganggap semua execute sama. Default `actor=None` bukan izin system. Jalur `verify_api_ssl` dari enrollment kini actorless; telusuri enrollment/created_by/ownership dan tetapkan compatibility yang aman.

Baca [temuan source independen](../report/reviewer/20261116T231008Z-0020-job-safety-independent.md) dan [prasyarat/batas finance](../report/reviewer/20261116T231048Z-0020-prerequisite-independent.md). Root report memberi ID finding final. Source review belum merupakan reproduksi runtime; executor wajib failing-before/passing-after pada defect yang diperbaiki.

## Scope perubahan

Boleh diubah hanya sejauh diperlukan:

- `backend/domains/jobs/{engine.py,models.py,views.py}`, command `runworker.py`, helper lokal jobs kecil bila konkret, serta migration jobs **baru additive** bila bukti mengharuskan.
- Existing handlers `customers/handlers.py`, `network/handlers.py`, `radius/handlers.py`, `backups/service.py`; enqueue/view/service domain yang sudah ada untuk trusted provenance/current authority/revision dan pemisahan DB/I/O yang relevan.
- Existing shared identity/tenancy/common helper seperlunya, tanpa melemahkan HTTP/session/CSRF/RLS. Shared helper ownership tetap terserialisasi oleh orchestrator.
- Focused unit/integration/process tests dan fixture yang sah; `backend/tests/integration/test_idempotency_pa006_r5.py` hanya hardening P3 REV-1611-TEST-01 (assert kedua thread selesai dan kedua hasil ada).
- Packet ini, laporan/evidence tersanitasi, latest handoff/progress dan catatan operasi non-normatif di laporan; bila perlu runbook singkat gunakan `docs/runbooks/`.

Tidak mengubah CONTRACT/domain requirements/defaults/test-design agar kode lulus; tidak mengadopsi PR8, mengubah dependency stack/CI/installer/topology, mengaktifkan kemampuan mutasi RouterOS yang lab-required, merombak backup/PDF/storage, Tax/DANA/SSTP atau scheduler. Jangan edit migration applied PA-0060004/0005, replay/hash/cache protocol, atau history uang. Jika perubahan normative sungguh perlu, laporkan PROPOSED sesuai CONTRACT dan tahan hanya keputusan terdampak.

## Acceptance wajib

| ID | Hasil yang harus dibuktikan |
|---|---|
| **J20-A01 — ownership seluruh write** | Transition, terminal/error/result/detail, retry, heartbeat, progress dan domain commit yang terkait memiliki guard current lease token+epoch+expected state/validity yang benar. CAS gagal menghentikan worker lama. Force lease transfer/reconcile/cancel lalu jalankan stale snapshot: nol overwrite state/result/progress, nol efek DB/send baru. Terminal state tetap immutable. Jangan hanya menambahkan helper yang return-nya diabaikan. |
| **J20-A02 — transaksi dan RLS** | Claim/transisi/checkpoint serta DB domain/audit/outbox memakai transaksi pendek dengan konteks tenant tepercaya pada koneksi yang sama. Tidak ada transaksi/row lock DB terbuka melintasi network I/O. Block adapter secara terkendali; koneksi observer membuktikan committed state+heartbeat terlihat dan tidak ada lock/transaksi worker tertahan saat send/readback. Tenant context setelah commit/rollback/pool reuse fail-closed. Payment/PA-001 atomic locks tetap utuh; pekerjaan network tidak menahan lock dana yang tak diperlukan. |
| **J20-A03 — writer eksternal dan cancel** | Satu pemilik mutasi konflik per router; dua worker/job router sama tidak mengirim bersamaan, router lain tetap dapat maju. Lease/epoch DB **tidak** dianggap menarik kembali command RouterOS. Pemilik baru menunggu bukti penulis/koneksi lama tidak dapat mengirim dan readback selesai. Queued/pre-effect cancel atomik menghasilkan nol efek berikutnya; outstanding send/maybe/confirmed tidak diberi false cancelled. Race cancel/execute/reconcile diperiksa dari efek dan state durable. |
| **J20-A04 — uncertain dan retry** | Timeout setelah send/ack hilang/generic error setelah possible effect menjadi uncertain/recovery sesuai bukti, tidak blind retry. API retry, retry_job, resolve_uncertain dan automatic retry tidak membuka efek baru dari unknown outcome. Readback applied→verify tanpa resend; not-applied→retry hanya setelah old writer aman; unknown tetap tertahan. Concurrent retry tidak menghasilkan duplicate logical effect; origin/action identity dan audit tetap traceable. |
| **J20-A05 — crash/reconcile/deadline** | Crash claimed/preflight/executing/verifying dan sebelum/sesudah DB effect commit mempunyai recovery durable yang benar; expired lease compare-and-set tidak menimpa lease renewed/completed/cancelled. Recovery diulang aman. Deadline/attempt/backoff/heartbeat memakai defaults existing dan boundary effect yang eksplisit; expired sebelum efek tidak mengirim, expired setelah possible effect jujur uncertain. B3/B4 observation window durable tidak dipercepat atau diberi batas60s yang salah. |
| **J20-A06 — current authority** | Actor aktif, membership/permission, tenant/resource/router scope dan policy/revision yang relevan diperiksa dari DB mutakhir sebelum setiap efek/chunk sensitif, bukan objek/payload enqueue yang basi. Revoke/demote/delete/scope change setelah enqueue atau sesudah preflight menghasilkan nol efek yang kini dilarang. Sensitive proof/reauth/revocation mengikuti kontrak existing; jangan menyimpan cookie/token/secret sesi di payload. Menutup browser tidak membatalkan pekerjaan async biasa yang tetap sah. Trusted-system origin sempit, server-derived dan dapat diaudit; null/deleted actor tidak otomatis system. Platform-only actor bukan pemilik tenant. Preserve SUB-05: restricted bukan mematikan operasi layanan existing; ended tidak mengisolir internet karena utang SaaS. Policy/hold/pembayaran diuji pada jalur aktif; jangan membangun auto-isolir R2 untuk tes ini. |
| **J20-A07 — HTTP authority dan verifier** | Direct HTTP detail/retry/cancel memakai underlying operation/read permission dan router scope yang benar; sensitive mutation memerlukan step-up yang berlaku. Non-milik404 generik, milik tanpa izin403. Router replacement tidak melepas router dengan izin enroll saja; trace ARCHITECTURE§5 routers.release. Missing handler/payload authority fail-closed. Verifier negatif tidak menghasilkan succeeded; verifier kontrak eksplisit pada semua active kind, preserve hasil valid DB-only dan cutover pending_observation tanpa klaim perangkat selesai. |
| **J20-A08 — drain proses** | Uji **proses nyata disposable** SIGTERM dan SIGINT pada idle, cooperative DB job dan blocked I/O: stop claim baru segera, batas waktu drain jelas, active job diselesaikan/ditahan jujur, exit/status membedakan drained vs deadline/incomplete. Paksa process kill lalu reconcile membuktikan recoverability. Deadline habis tidak mengklaim sender telah aman bila belum dibuktikan. Runbook menyebut urutan stop-claims→drain/stop old writers→reconcile/readback→resume. Ini belum rehearsal installer/systemd/produksi. |
| **J20-A09 — compatibility dan regresi** | Inventory old queued/in-progress/actorless payload serta authority baru: proven valid diproses tanpa privilege escalation; unknown/quarantined memiliki alasan dan resume yang tepat, tidak sekadar dipurge. Additive migration dan kode lama/baru memiliki kebijakan drain/compatibility/fix-forward yang teruji, tanpa klaim rollback aman ke worker lama yang defective. Preserve PA-001 seluruh10 kasus, PA-006 termasuk grammar/migration/permission/selected IDs/secret scrub. Tutup P3 REV-1611-TEST-01 sebagai test-only: missing participant harus FAIL; tidak membuka task0010 lagi. |

## Verifikasi dan bukti

1. Reproduksi minimum failing-before untuk jalur unfenced write, cancel-in-flight, uncertain retry, revoked authority dan missing/negative verifier; lalu passing-after yang sama. Harness mengamati state durable dan efek, bukan sekadar mock-call/status.
2. PostgreSQL nyata, runtime NOSUPERUSER/NOBYPASSRLS dan FORCE RLS; jika mengklaim paritas produksi gunakan migrator owner terpisah. Independent connections/processes untuk race; Events/barriers serta query/blocker observer saat mengklaim lock contention. Jangan memakai sleep sebagai satu-satunya pengatur. Semua thread/process wajib bounded join, sudah berhenti dan setiap hasil terisi; exceptions worker ikut menggagalkan tes.
3. Jalankan targeted jobs/authority/recovery/drain tests, RLS/pool reuse, PA-001 dan PA-006 regressions. Jalankan suite backend penuh, `manage.py check`, `manage.py makemigrations --check --dry-run`, migration/compatibility checks yang terpengaruh dan `python3 docs/tools/check_docs.py`. Jangan refresh manifest yang tidak berubah.
4. Jalankan checks API/schema/contracts dan frontend/typecheck/build sesuai dampak; full candidate CI backend/frontend/docs harus exact published SHA (atau synthetic PR merge SHA dengan ancestry/source delta eksplisit). Browser E2E/perangkat/OS/DR/benchmark tetap NOT_RUN kecuali benar-benar dijalankan.
5. Setiap assertion matriks A01–A09 dilaporkan PASS/FAIL/NOT_RUN/BLOCKED dengan command, environment/version, exit, expected/actual, state/effect count, log path dan tested SHA. Simulator/controlled adapter membuktikan engine sandbox saja; CHR fencing, lab dan zero downtime tidak dinyatakan terbukti.

Host/lab unavailable tidak menghalangi pengembangan sandbox ini. Bila mandatory sandbox test belum dapat dijalankan, status blocked/failed sesuai sebab dan filename tetap unfinished; jangan menandai done dengan daftar tes yang belum dijalankan.

## Penyerahan

Orchestrator memakai reviewer independen sesuai CONTRACT§5 untuk concurrency/recovery dan authority/compatibility; read-only boleh paralel, writes disjoint hanya jika isolation terverifikasi. Laporan utama `report/orchestrator/<UTC>-0020-job-lifecycle-authority.md`; setiap reviewer `report/<role>/<UTC>-0020-*.md`; evidence tersanitasi sesuai CONTRACT§10.

Laporan memuat inventory, minimum solution/alternatives, finding→change→failing-before/passing-after, **seluruh A01–A09→actual evidence**, migration/legacy/recovery, batas source vs PG vs process vs device, exact instruction/base/implementation/tested/published SHA, PR+CI, risiko dan next actor/action. Tidak cukup melaporkan jumlah tes.

Setelah scope/tes wajib tuntas: update packet/report/handoff/progress, rename **file ini** ke `0020-job-lifecycle-authority_done.md` pada commit penyerahan, push branch dan verifikasi remote+CI; review menjadi pending. Bila controller meminta koreksi, buka kembali ID0020 yang sama dan preserve laporan. `_done` bukan acceptance, merge, deploy atau release. Next actor controller mereview exact SHA hasil; task dependent baru menunggu keputusan/integrasi yang disyaratkan.

Production Beta tetap **NOT_READY**: installer/upgrade/restore/secret separation/scheduler/topology DEC-01/DEC-02 dan gates host/GNS3/pilot/kapasitas berada di scope terpisah. Penyerahan packet ini tidak otomatis menjalankan external coding agent.
