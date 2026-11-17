# 0020 — PA-002 + PA-003: job aman terhadap stale worker dan perubahan kewenangan

| Field | Nilai |
|---|---|
| Task ID | `0020`; satu packet untuk lifecycle + authority yang saling bergantung |
| Execution status | **`ready`** — dibuka kembali controller R2; source koreksi sebelumnya sudah terintegrasi, residual wajib ditutup pada ID sama |
| Review status | **`changes_requested`** pada exact main **`64b68f8d74b0aa593f379c75d6b5702402fd9d78`**; empat residual P1 + batas evidence09 |
| Resume controller 17 Nov ~21:48 WIB | Histori checkpoint sebelum koreksi: [checkpoint](../report/controller/20261117T144620Z-0020-resume-review.md); REV-1711-01–09 ditutup pada sesi koreksi berikutnya |
| Controller / executor | ChatGPT Work controller / coding agent sandbox |
| Baseline | **`main@64b68f8d74b0aa593f379c75d6b5702402fd9d78`** untuk koreksi R2; baseline awal41d1f33 adalah histori, bukan current main |
| Original instruction ref | PR26 `review/0020-job-lifecycle-authority-20261117` @ `ea7b8a17ad8d6339eed45769bbff1626ea279665`; histori instruksi awal |
| Current correction instruction ref | **[PR31](https://github.com/smahud/MicroTix_Project/pull/31)** `review/0020-controller-r2-20261117`, initial verified443b1dc/tree d86c1216; [controller R2](../report/controller/20261117T170000Z-0020-r2-review.md) §§3/7; PR29/R1 tetap histori |
| Accepted predecessor | [0010 / PA-006](0010-pa006-idempotency_done.md), accepted exact `a301a94c2b3268679065e85bbef66f35949483f7` pada [R5 review](../report/controller/20261116T101809Z-0010-pa006-r5-review.md); PR24+PR25 merged ke main, [integrasi](../report/orchestrator/20261116T111835Z-0010-pa006-integration.md) |
| Authority | [CONTRACT](../CONTRACT.md) §§5–6A/8–13; [PRODUCT](../docs/PRODUCT.md) TEN-03, JOB-02–05, SEC-01/04/05, SUB-05; [ARCHITECTURE](../docs/ARCHITECTURE.md) §§3–6; [OPERATIONS](../docs/OPERATIONS.md) §§3–4; [ACCEPTANCE](../docs/ACCEPTANCE.md) §4 |
| Backlog / tests | Existing TK-101/102/103 dan bagian drain TK-1002; katalog T06-CRASH-01/02/03, T10-TEN-03; T05/T14 hanya invariant current-state yang relevan, bukan seluruh fitur R2/DR |
| Controller report | **[R2 changes_requested](../report/controller/20261117T170000Z-0020-r2-review.md)** pada main64b68f8; [R1](../report/controller/20261117T134100Z-0020-job-lifecycle-review.md) dan instruksi awal dipertahankan |
| Correction implementation / tested / candidate | Histori koreksi executor: impl2681a3d, PR30 actual head19023737 **merged** (9eb5dacf); source current berbeda karena merge SSTP. **Controller tested/reviewed64b68f8**; kandidat koreksi R2 **not_submitted** |
| Histori bukti executor R1 | **Probe controller R1: failing-before 11 failed → passing-after 11 passed** (diulang pada DB split-role migrator-owned + FORCE RLS); **suite penuh 562 passed + 1 skip** (+8 tes bukti REV-1711-09: SIGINT/active-barrier/stop-claim, fase panjang vs reconciler, crash setelah commit domain, current-policy/SUB-05); PA-001 33 + PA-006 125 + RLS 8 lulus; check/makemigrations/docs PASS; [evidence root](../report/executor-evidence/20261117T150000Z-0020-correction/) |
| Historical correction execution report | [Orchestrator koreksi](../report/orchestrator/20261117T160000Z-0020-correction-delivery.md) — matriks A01–A09 + temuan→perubahan→bukti; [reviewer independen](../report/reviewer/20261117T160500Z-0020-correction-independent.md): REV-1711-01–09 CLOSED, temuan P2 CORR-REV-01/02 ditutup sebelum commit; [laporan penyerahan pertama](../report/orchestrator/20261117T010218Z-0020-job-lifecycle-authority.md) histori |
| Next actor / action | **coding_agent**: fetch decision branch R2; tutup residual **REV-1711-01/04/05/08** + pemetaan evidence09, pertahankan CLOSED02/03/06/07; jalankan6 assertion R2 dan11 probe lama + regresi wajib, publish SHA baru pada ID0020 |

PA-002/PA-003 adalah label kontinuitas audit, bukan otoritas baru. PR8 planning_audit kini terintegrasi sebagai record historis melalui merge-all; kebutuhan packet ini tetap diturunkan dari kontrak/domain requirements di atas. Prasyarat PA-006 sudah accepted/integrated dan tidak dibuka kembali. PA-001 pembayaran juga dipertahankan. Packet ini tidak memberi izin merge, deploy, tag atau aktivasi fitur.

## Koreksi controller R2 — instruksi current pada ID0020 yang sama

**R2 changes_requested pada actual integrated main64b68f8.** Koreksi PR30
sudah merged; merge bukan acceptance. Full backend **580 passed/1skip/3warnings**
dan **11 original R1 probes passed**, tetapi **6 assertion R2 gagal/0 errors**.
[Laporan R2](../report/controller/20261117T170000Z-0020-r2-review.md) memiliki
reproduksi, expected/actual, source lines dan closure lengkap; [evidence](../report/controller-evidence/20261117T170000Z-0020-r2/).

| Finding tetap | Koreksi minimum / penutup |
|---|---|
| **REV-1711-01 P1 PARTIAL** | Guard SELECT di transaksi tidak mengunci ownership sampai commit. Actual discovery guard→reconcile→resume commit object1/snapshot succeeded. Serialize ownership-changing updates vs short domain commit; valid expected state/token/epoch/lease; seluruh service units juga aman. Preserve I/O di luar transaksi. |
| **REV-1711-04 P1 PARTIAL** | Cek durable unknown harus konsisten dengan sender acquisition; predecessor menjadi uncertain setelah SELECT masih menghasilkan send2. Selain itu putusnya DB session melepas advisory lock sementara adapter worker masih hidup: successor send2 saat lease predecessor masih valid. Tahan sampai old adapter writer aman **dan** readback selesai; jangan hanya memindah SELECT lalu mengklaim seluruh closure. Router lain tetap maju. |
| **REV-1711-05 P1 PARTIAL** | Post-I/O enrollment harus cek current authority pada effect unit; revoke saat TLS probe saat ini tetap membuat Router1 dan apply peer/akun pada WG **dan** SSTP. Nol efek baru sesudah revoke, dengan helpers/stack existing. |
| **REV-1711-08 P1 PARTIAL** | B6 wajib memakai adapter aktif existing; selected api_ssl saat ini dibypass simulator sehingga false succeeded/rolled_back/local. Hormati cutover_pending_lab tanpa mengaktifkan live mutasi baru; negative/unknown tetap jujur, positive simulator berlabel. |
| **REV-1711-09 P2 PARTIAL evidence** | Preserve SIGTERM/SIGINT/active-progress/stop-claim dan SUB-05 yang sudah terbukti. Map renewal fase panjang existing terhadap concurrent reconciler secara tepat; short progress loop bukan satu long adapter call. Simulasi thread expiry setelah domain commit bukan actual process kill. Lengkapi applicable evidence/justifikasi, tanpa menambah fitur fase depan. |

**CLOSED dan harus dipertahankan: REV02/03/06/07**, original preflight
revocation fix, seluruh11 probe R1, PA001/PA006 dan SSTP yang sudah
terintegrasi. Jangan ulang perbaikan yang sudah terbukti atau buka task0010.
Original A01–A09 di bawah **tidak berubah**. Uji enam assertion baru dari
file lifecycle (3) dan authority (3), jangan melemahkan assertion; root
mencatat first2 lifecycle dan third sender-session pada log terpisah.
Kandidat koreksi R2 belum diserahkan; tetap filename unfinished. Baseline
current64b68f8 harus dipertahankan, bukan checkout source PR27/41d1f33 lama.
Task0030/deploy/aktivasi belum eligible. Decision branch R2 harus difetch
bila PR dokumentasi belum merged.

## Histori koreksi controller R1 — hasilnya dinilai ulang oleh R2

Verdict pada **PR27@bd37c14** adalah `changes_requested`: **8 defect kode
terkonfirmasi melalui 11 assertion PostgreSQL gagal**, bukan 11 error harness.
Root full suite554 passed/1skip/3warning tetap tidak memenuhi acceptance yang
probe ini buktikan gagal. [Matriks evidence dan koreksi lengkap](../report/controller/20261117T134100Z-0020-job-lifecycle-review.md)
menjadi instruksi koreksi; A01–A09 di bawah tidak dikurangi. Current source
PR27 dibawa oleh decision ref; main41d1f33 belum memuat packet/kandidat ini.

| ID | Koreksi minimum / tes penutup |
|---|---|
| **REV-1711-01 P1** | Guard lease/token/epoch/state/validity **dalam transaksi domain**; actual blocked discovery→reconcile→resume tidak commit object/health/success atau efek berikutnya; failed checkpoint menghentikan worker |
| **REV-1711-02 P1** | Generic/staging failure sesudah backup send ditahan uncertain/recovery; nol resend otomatis/manual tanpa bukti no-effect/readback |
| **REV-1711-03 P1** | Retry lineage serialized: ancestor retry tidak melewati descendant uncertain/recovery/active; concurrent ancestor/child menghasilkan nol efek duplikat |
| **REV-1711-04 P1** | Mutasi router berkonflik ditahan durable sampai old-writer aman **dan** readback unknown predecessor selesai; router lain tetap maju |
| **REV-1711-05 P1** | Current authority di effect boundary setelah preflight/per-chunk; revoke/demote/narrow-scope barrier→nol release/peer/NAS/send |
| **REV-1711-06 P1** | HTTP detail/retry/cancel menghormati membership router scope; non-scope404+state/job tidak berubah, in-scope403/step-up tetap benar |
| **REV-1711-07 P2** | B6 APPLY/VERIFY keluar dari outer DB transaction; independent observer membuktikan no transaction/row-lock saat adapter diblokir |
| **REV-1711-08 P1** | B6 negative/unknown readback tidak mengklaim succeeded/rolled_back/local; positive dan pending_observation tetap jujur |
| **REV-1711-09 P2 evidence gap** | Buktikan SIGTERM+SIGINT idle/active-DB/blocked-I/O dengan barrier+efek durable+complete outcomes, long-phase/heartbeat/recovery dan current-policy/SUB05 assertions yang applicable; jangan membangun fitur R2 untuk tes |

Reproduksi final disimpan di [controller-evidence](../report/controller-evidence/20261117T134100Z-0020-review/).
Tutup finding dengan perubahan minimum dan passing-after assertion yang sama
atau lebih kuat; jangan mengubah requirement atau melemahkan probe untuk lulus.
PA-006/task0010 tetap accepted/integrated, P3 thread assertions dipertahankan.
Tidak ada task0030/deploy/merge/aktivasi otomatis. Ringkasan internal reviewer
lama ditandai histori; controller R1 adalah keputusan acceptance current.

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
