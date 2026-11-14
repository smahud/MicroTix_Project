# 0010 — PA-006: HTTP idempotency yang aman terhadap scope dan race

| Field | Nilai |
|---|---|
| Task ID | `0010` — ID tetap; dibuka kembali untuk koreksi |
| Execution status | `done` (executor; scope + tes wajib selesai, menunggu review controller) |
| Review status | `pending` |
| Controller | ChatGPT Work / reviewer proyek |
| Executor | Coding agent sandbox; penyerahan ketiga Z.ai 15 November 2026 |
| Baseline / dependency | `main@9903d9b0cf09d737b553da3c21067b4810e956c0`; PA-001 merged PR9 (`8ce94d4`); tidak diulang |
| Instruction revision | Kebutuhan awal pada main; koreksi [PR16 exact ref](https://github.com/smahud/MicroTix_Project/blob/5da0d801c71b020fbb8b977294502ea5a09e7bcb/task/0010-pa006-idempotency.md) + keputusan [PR18](https://github.com/smahud/MicroTix_Project/pull/18) — keduanya dibawa semantik pada kandidat ini |
| Candidate branch / exact tested SHA | `session/2026-11-15-pa006-idempotency`; implementation `1780e150695a6b7bbb4109b6f13ea44df54fa6a0` + hardening `c99838c` (tree uji identik); base `review/0010-pa006-controller-20261114@b6a0cb8` |
| Published SHA / PR / CI | [PR19](https://github.com/smahud/MicroTix_Project/pull/19) base main; first verified publication `35507eb04d6c9a4a1276315dd608a6ef03bd863b`; required CI pada SHA itu **backend/frontend/docs success** (diverifikasi 15 November); commit metadata berikutnya report-only |
| Execution report / internal reviewer | [Executor](../report/orchestrator/20261114T164816Z-0010-pa006-idempotency.md) (matriks finding→perubahan→tes→evidence + acceptance + call-site table); [independent review](../report/reviewer/20261114T164816Z-0010-pa006-review.md) — PASS_WITH_NOTES, temuan P3 ditutup/didokumentasikan |
| Controller review | [Keputusan 14 November](../report/controller/20261114T153739Z-0010-pa006-review.md) `changes_requested` pada `37a8729` — kandidat ini menutup keempat finding; review baru belum ada |
| Next actor | **controller_reviewer** |
| Exact next action | Review kandidat exact SHA (`1780e15`+`c99838c`, head publikasi di handoff) terhadap REV-1311-01/02/03 + REV-1411-04 dan acceptance awal; keputusan di `report/controller/<UTC>-0010-pa006-review.md` |

Mulai dari [panduan tetap](0000-start-here.md) dan [CONTRACT](../CONTRACT.md). Ini task implementasi, **bukan bukti PA-006 selesai**. Fetch refs dan review delta bila remote berubah; pilih branch baru dari main aktual dengan packet ini tersedia. Jika instruksi belum merged, catat instruction ref/PR dan bawa perubahan dokumentasi yang sah secara semantik; jangan menimpa pekerjaan lain atau menganggap SHA baseline sebagai main untuk selamanya.

## Tujuan dan bukti masalah

Tutup PA-006 memakai PostgreSQL dan mekanisme existing. Request uang/provisioning yang diretry atau bersamaan harus mewakili satu logical action sesuai scope yang sah. Jangan mengulang perbaikan locking invoice PA-001 yang sudah benar.

Sumber kebutuhan: [ARCHITECTURE §5](../docs/ARCHITECTURE.md), [FINANCE](../docs/FINANCE.md), [ACCEPTANCE §4](../docs/ACCEPTANCE.md), serta [register review sebelumnya](../report/controller/20261111T074225Z-repo-handoff-review.md). Mapping task produk yang terdampak dirujuk dari [tasks.json](../docs/tasks.json); jangan membuat backlog pengganti.

Bukti source pada baseline:

- [common/idempotency.py](../backend/domains/common/idempotency.py):53–79 menyimpan principal tetapi tidak memasukkannya dalam scope/lookup/update; query existing lalu insert tidak memiliki conflict-safe concurrent reservation. Record tanpa response mengizinkan eksekusi ulang tanpa pembuktian keadaan efek.
- [jobs/models.py](../backend/domains/jobs/models.py):203–223 uniqueness hanya `(scope, idem_key)`.
- [subscriptions/views.py](../backend/domains/subscriptions/views.py):99 `payment_submission` tidak menyertakan `invoice_id`; platform decorators memperoleh tenant dari session pada helper yang sama.
- URL UUID bisa mempunyai beberapa representasi untuk identitas yang sama. Scope raw text dapat memisahkan logical target yang sebenarnya sama. Review semua decorated call sites, bukan satu payment endpoint saja.
- Tes [test_idempotency_quota.py](../backend/tests/integration/test_idempotency_quota.py) membuktikan sequential quotation replay/conflict; tes itu belum membuktikan concurrent HTTP/principal/resource/platform boundaries.

## Scope dan ownership

Diizinkan: `backend/domains/common/idempotency.py`; bagian model/migration idempotency milik jobs bila perlu; decorator resource/platform scope dan metadata API terkait pada views pemilik; tes relevan; laporan/task/progress/handoff. Hanya perubahan minimum yang dibutuhkan kontrak ini.

Tidak termasuk: implementasi PA-002/003 engine lifecycle, scanner/MFA, quota policy, network adapters/mutation, installer/deployment, ledger/Tax/ACS/OLT, perubahan CONTRACT atau kebijakan normatif. Bila incidental defect tidak diperlukan untuk PA-006, catat follow-up berbukti. Tidak ada deployment atau akses router/host produksi. Jangan menambah Redis/Celery/broker/framework/repository abstraction.

## Pekerjaan wajib

1. Buat tabel ringkas **seluruh** `@idempotent` call sites di laporan: operation, principal, tenant/platform, canonical target, body/file hash, transaction boundary, current auth/permission/step-up dan safe replay response. Source path/line harus aktual.
2. Samakan identity untuk claim, lookup, uniqueness, response update dan replay: **principal + canonical tenant/platform + operation + canonical resource + key**. Canonicalize identitas terstruktur sebelum scope/hash; jangan mengubah username/password/semantic string yang exact-case secara umum.
3. Resource SaaS proof mencakup invoice; operasi platform mempunyai scope eksplisit yang tidak berubah karena pengguna berpindah active tenant. Platform SaaS dan pembayaran internet tenant tidak boleh berbagi response/aksi.
4. Terapkan claim/replay transaction protocol yang conflict-safe pada PostgreSQL. Same-key concurrent requests tidak boleh menghasilkan duplicate effect atau unique-violation 500. Pending/in-progress record tidak menjadi izin blind replay. Jika ada temporary in-progress response yang sah menurut kontrak, retry sesudah penyelesaian harus memperoleh logical action/result yang sama; jangan menjadikan same-body sebagai idempotency_conflict atau permanent generic conflict pengganti replay. Pertahankan stable documented response; jangan membuat kontrak baru diam-diam.
5. Auth/membership/current permission dan sensitive step-up tetap diperiksa sebelum replay. Hash secret dengan HMAC; tidak menyimpan plaintext secret/reveal response. Pertahankan transaction-local RLS dan business uniqueness setelah TTL.
6. Jika schema/index berubah, buat migration kecil milik jobs dengan kebijakan legacy record, ordering/compatibility, failure dan rollback/fix-forward yang eksplisit. Jangan drop history, menulis ulang uang/kuitansi, atau melemahkan RLS untuk memudahkan concurrency.
7. Bedakan committed DB effect, response persistence dan external/file side effects. Pilih strategi paling sederhana yang benar untuk jalur aktif. Jika efek lama ambigu, fail safely dan rekonsiliasi; jangan menyatakan exactly-once eksternal hanya dari unique key DB.

## Acceptance yang wajib dibuktikan

Gunakan PostgreSQL nyata, role non-superuser/non-BYPASSRLS dan independent authenticated HTTP clients/connections untuk boundary. Gunakan forced interleaving/lock observation/failure injection yang relevan, bukan hanya barrier lalu berharap race terjadi.

| Kasus | Hasil wajib |
|---|---|
| Same identity/key/body bersamaan | Satu logical action/effect; replay hasil yang sama. Jika temporary in-progress response diperlukan dan sah, retry setelah selesai wajib replay action/result yang sama; tidak boleh permanent409 atau idempotency_conflict untuk same-body; bukan duplicate write/500 |
| Same identity/key beda body/file | 409 idempotency_conflict tanpa efek kedua |
| Beda principal/tenant/platform/operation/resource | Tidak tertukar response atau logical action; business uniqueness tetap berlaku |
| UUID alias / malformed | Alias target sama menjadi scope sama; input malformed structured 422 |
| SaaS proof invoice A vs B, key/body sama | Target B tidak memperoleh submission/response A |
| Platform operator pindah active tenant | Tidak membuat scope/efek platform baru untuk aksi yang sama |
| Permission/session/step-up tidak sah saat replay | Tidak membocorkan cached response atau menjalankan aksi; respons sesuai kontrak |
| Gagal sebelum DB commit | Domain writes/audit/outbox/replay state konsisten rollback |
| Crash/interupsi setelah logical commit sebelum response tersimpan | Tidak blind execute efek kedua; recover/replay/reconcile dengan evidence sesuai outcome |
| TTL dan legacy records | Business uniqueness tidak hilang; record lama tidak memberi response ke principal/target salah |
| Regression PA-001 | Sepuluh tes konkurensi tetap lulus; paid=sum allocations, receipt/audit/outbox konsisten |

Assertion harus memeriksa state/effect count dan tenant/actor/target, bukan status HTTP saja. Request creation tanpa resource ID memakai identity operation/body yang jelas, bukan target buatan. ID/body normalization dan permission policy tetap sesuai kontrak existing.

## Verifikasi dan review

- Jalankan targeted idempotency/HTTP concurrency tests, lalu regression backend; `manage.py check`, migration consistency dan API/schema checks yang terdampak; docs check serta required CI pada candidate. Frontend contract checks bila bentuk respons/API berubah; required frontend CI tetap harus lulus.
- Gunakan runtime sandbox/bootstrap existing sesuai [IMPLEMENTATION_PLAN](../docs/IMPLEMENTATION_PLAN.md). RLS/race tidak dibuktikan SQLite. Tidak perlu menyiapkan server produksi untuk pekerjaan ini.
- Independent reviewer memeriksa call-site scope table, interleaving, transaction error/savepoint behavior, compatibility/legacy record dan no auth bypass; laporan tiap sub-agent sesuai CONTRACT. Pilih reviewer yang benar-benar tersedia, tidak mengarang hasil.
- Catat actual command, versi/environment, exit, assertion, duration, evidence path dan NOT_RUN. Jangan menggeneralisasi CI hijau sebagai host/lab/DR verification atau menghapus assertion gagal.

## Penyerahan dan batas selesai

Laporan executor: `report/orchestrator/<UTC>-0010-pa006-idempotency.md`; internal reviewer di `report/<reviewer-role>/<UTC>-0010-pa006-review.md`. Sertakan minimal solution/alternatives, migration/recovery policy, scope table, **setiap baris acceptance → actual result → evidence**, risiko/unfinished work dan next actor/action. Laporan internal executor tidak menggantikan keputusan controller.

Coding agent mengisi ringkasan hasil singkat di packet (apa yang berubah, acceptance yang sudah/belum terbukti, pointer report/candidate/CI), lalu mengalihkan next actor ke `controller_reviewer` hanya setelah candidate/report dipublikasikan dan diverifikasi. Jika blocked/failed, catat batasnya dan pihak yang benar-benar dapat membuka blocker, bukan mengklaim selesai.

Controller menyimpan keputusan implementasi di `report/controller/<UTC>-0010-pa006-review.md`, menautkannya ke metadata packet dan mengikatnya pada exact reviewed SHA. Report memuat verdict, finding→koreksi→acceptance, evidence limits serta next actor/action. Changes requested membuka kembali task0010 yang sama; coding agent memperbaiki finding dan menyerahkan SHA baru. Accepted mengembalikan kendali ke controller untuk penyiapan task penerus sesuai dependencies/integration. Publish keputusan di ref GitHub yang disebut di handoff sebelum pergantian peran; jangan meninggalkan keputusan hanya di chat.

**Riwayat penyerahan:** PR15 (13 November), PR17 (14 November), dan kandidat ini (15 November) adalah hasil executor pada ID0010 yang sama; dua pertama changes_requested. Laporan historis dipertahankan.

**Ringkasan hasil implementasi (penyerahan ketiga, executor):** koreksi empat finding controller — (1) REV-1311-01: migrasi 0004 menahan record tanpa respons + remap platform + dedupe berrespons; runtime legacy_shapes/replay_guard merekonsiliasi payment_submission resource='' dengan verifikasi submission→invoice/tenant (transisi migrasi NYATA 0003→0004 dibuktikan: retry pasca-upgrade mereplay submission semula, count 1, beda body 409); (2) REV-1311-02: identitas identity_conflict_resolve = migration UUID + group; parent divalidasi SEBELUM klaim/replay (422/404); session A/B menulis keputusan masing-masing [2,2]; legacy group-only 409 aman; (3) REV-1311-03: hash v2 field UUID body dideklarasikan (package_id/router_id/selected_account_ids) + kompatibilitas v1 raw; alias replay, beda nyata 409; (4) REV-1411-04: tes konkurensi HTTP klien terautentikasi per-thread melalui dispatch penuh, observasi lock DIASSERTI, takeover test injeksi kegagalan setelah writes dengan penantang menunggu (rollback menyeluruh + 1 aksi terkomit). Bukti: suite penuh **426 passed** (PG 17.11 nyata, role non-superuser, FreeRADIUS aktif), targeted 65 passed, **6/6 probe acceptance controller PASS**, `manage.py check` 0 issue, `makemigrations --check` bersih, docs PASS. Review internal independen PASS_WITH_NOTES (temuan P3 ditutup pada `c99838c` atau didokumentasikan). Semua baris acceptance packet terpetakan PASS pada laporan executor §3; NOT_RUN: host/lab/E2E/benchmark (di luar scope). Detail + evidence: laporan executor di atas.

Isi metadata di atas, update [LATEST_HANDOFF](../report/LATEST_HANDOFF.md) dan [progress](../docs/progress.md), lalu ikuti penutupan pada panduan tetap: completion rename ke `0010-pa006-idempotency_done.md` ikut commit, push/remote/CI diverifikasi, review menjadi pending. Task ini baru accepted ketika controller mencatat review exact SHA. Jangan memasukkan secret/runtime/unrelated files ke commit atau merge otomatis ke main.

## Koreksi controller 14 November 2026 — lanjutkan ID0010

Tiga finding 13 November tetap **OPEN** pada PR17; jangan menganggap main yang belum merged sebagai satu-satunya instruction. Original scope/pekerjaan/acceptance di atas dipertahankan lengkap. Perbaikan principal isolation, fresh invoice scope, explicit platform scope dan atomic claim/response yang sudah benar tetap dipertahankan.

| Finding | Koreksi minimum | Acceptance penutup |
|---|---|---|
| **REV-1311-01 P1**, legacy retry/migrasi tidak aman | Rekonsiliasi completed/ambiguous retained key berdasarkan principal/tenant/target/body; validasi submission→invoice/actor. Jangan purge nonexpired no-response claim lalu blind-execute. Tinjau old platform/session/UUID scopes; dokumentasikan drain/write-freeze, migrasi atomic Django/PostgreSQL, ordering dan fix-forward. | Actual main HTTP upload→0004→retry owner/invoice/key/body yang sama mengembalikan submission semula, submission/file tetap1; B tidak replay A; beda body409; no-response legacy tetap aman, termasuk actual migration; concurrent retry; tidak ada mutasi history uang. |
| **REV-1311-02 P1**, grup cache kehilangan parent | Identity mencakup canonical migration_id dan exact opaque group_id; validasi parent sebelum replay; tangani old group-only cache dengan aman. | A/B memakai group/key/body sama menghasilkan keputusan masing-masing; retry A replay; parent alias sama; cached group tidak mengubah malformed422/missing404 menjadi204. |
| **REV-1311-03 P2**, body typed UUID raw sebelum HMAC | Normalize field identity yang declared pada handler aktif sebelum hash; preserve string exact-case, array semantics dan real body/file conflict; kebijakan retained hash eksplisit. | service/key sama + package_id canonical/uppercase-compact alias replay200; package berbeda409; field UUID body lain relevan dan retained-hash compatibility dibuktikan. |
| **REV-1411-04 P2**, bukti konkurensi/failure belum memenuhi packet | Gunakan klien HTTP authenticated terpisah per thread/koneksi; force dan assert blocker/query/lock yang benar. Inject leader rollback setelah writes sebelum response persistence saat contender same-key menunggu. Koreksi matriks klaim sesuai bukti actual. | HTTP same-key same/different body dan boundary terkait lewat dispatch+auth+outer tenant transaction; observer gagal mendeteksi lock membuat tes gagal; rollback/takeover membuktikan domain/audit/outbox/cache konsisten, satu committed action dan replay benar. |

Source reproducer dan command/log ada pada [evidence controller](../report/controller-evidence/20261114T153739Z-pa006/test_scope_review.py) dan laporan keputusan. Probe menguji acceptance yang diwajibkan; jangan menurunkan assertion agar kandidat hijau. Initial harness/FreeRADIUS setup correction dijelaskan terpisah; bukan defect aplikasi atau alasan mengabaikan failure acceptance.

Histori PR15/PR16 tetap di GitHub pada ref yang ditautkan; laporan executor PR17 tetap utuh. Saat resubmit wajib tulis matriks **finding→perubahan→closing test→actual evidence**, lalu acceptance awal seluruhnya. Koreksi expectation malformed platform404→422 sudah diterima sesuai kontrak existing, tidak perlu approval/implementasi ulang; non-platform generic404 tetap dijaga. Tidak ada perluasan ke PA-002/003, installer, Tax atau release gates.

Next setelah accepted: controller menyiapkan PA-002/PA-003 untuk job fencing/drain/authority, termasuk fresh HTTP RLS payload dan uncertain/cancel/stale-writer cases. Kandidat Beta tetap NOT_READY selama gates terkait belum dipenuhi. Tidak ada izin rollout atau tanggal peluncuran yang dibuat oleh task ini.
