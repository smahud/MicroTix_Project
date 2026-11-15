# 0010 — PA-006: HTTP idempotency yang aman terhadap scope dan race

| Field | Nilai |
|---|---|
| Task ID | `0010` — ID tetap; penyerahan keempat pada ID yang sama |
| Execution status | `ready` — ID0010 dibuka kembali oleh controller setelah review PR21; koreksi REV-1311-01 belum tuntas |
| Review status | `changes_requested` — exact reviewed SHA `634da4224f15dd6a5a4e9010fe1811dec8c7954d` |
| Controller | ChatGPT Work / reviewer proyek |
| Executor | Coding agent sandbox; penyerahan keempat Z.ai 15 November 2026 |
| Baseline / dependency | `main@9903d9b0cf09d737b553da3c21067b4810e956c0` (tidak berubah); PA-001 merged PR9 (`8ce94d4`); tidak diulang |
| Instruction revision | Kebutuhan awal pada main + koreksi PR16/PR18 (dibawa semantik histori) + **keputusan input kandidat [PR20](https://github.com/smahud/MicroTix_Project/pull/20)** pada reviewed SHA `9e9bf2d42002a00a69d54fc355b77384897b9478` — kandidat ini descendant keputusan itu (base decision head `e507175`), membawa histori review + closed fixes. **Keputusan terbaru: controller R4** pada [report](../report/controller/20261115T053138Z-0010-pa006-r4-review.md), ref `review/0010-pa006-controller-r4-20261115` |
| Candidate branch / exact tested SHA | `session/2026-11-15-pa006-idempotency-correction` dari `review/0010-pa006-controller-20261115@e507175`; **implementation `b71574d8b6ba1dc30d132551684791f760e8abc6`** — seluruh tes §Verifikasi dijalankan pada pohon sumber commit ini |
| Published SHA / PR / CI | [PR21](https://github.com/smahud/MicroTix_Project/pull/21), actual reviewed head **`634da4224f15dd6a5a4e9010fe1811dec8c7954d`**; implementation `b71574d`; report-only descendants verified identical app content. Exact-head CI [43679221142](https://github.com/smahud/MicroTix_Project/actions/runs/43679221142) backend/frontend/docs success, not acceptance |
| Execution report / internal reviewer | [Executor keempat](../report/orchestrator/20261115T044621Z-0010-pa006-idempotency.md) — matriks finding→perubahan→closing test→actual evidence (01/03A/03B/05), tabel 28 call-site, matriks acceptance, kebijakan migrasi/recovery, NOT_RUN; [independent review r4](../report/reviewer/20261115T044616Z-0010-pa006-r4-review.md) — PASS_WITH_NOTES; tiga temuan reviewer (F-01 P2 braced-URN parser, F-02/F-03 P3 ketebalan tes) **DITUTUP pada kandidat ini** sebelum penyerahan |
| Controller review | [Controller R4 — 15 November](../report/controller/20261115T053138Z-0010-pa006-r4-review.md): **REV-1311-01 P1 OPEN partial**, actual old-code uuid:/urn: accepted-prefix retries duplicate submission/file1→2. **03A/03B/05 CLOSED**,02/04/PA001 preserved. Prior PR20 decision remains history |
| Controller publication | Decision branch `review/0010-pa006-controller-r4-20261115` (target PR21 branch); publication/PR/remote verification recorded in current controller report and handoff after it exists |
| Riwayat penyerahan | PR15 (13 Nov, changes_requested via PR16), PR17 (14 Nov, changes_requested via PR18), PR19 (15 Nov, changes_requested via PR20), **penyerahan keempat ini**; laporan historis dipertahankan di report/ + histori git |
| Next actor | **coding_agent** |
| Exact next action | Fetch current controller R4 decision ref, fix remaining **REV-1311-01 only** on ID0010; preserve CLOSED03A/03B/05/02/04/PA001; old-source accepted UUID grammar→migration→retry must keep original result/effects1. Resubmit new exact SHA + actual evidence |

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

Klarifikasi scope koreksi controller 15 November (memenuhi pekerjaan wajib2/5/6 existing, bukan perluasan produk): `customers/services.py` dan boundary handler terkait boleh dikoreksi **hanya** untuk menyamakan typed UUID selection pada hash/preview/durable payload/consumption serta proyeksi preview CSV tanpa plaintext credential. Cache replay/retained data dan tes API terkait boleh dikoreksi minimum; jangan mengubah kebijakan empty selection/authority/lifecycle PA-003, penyimpanan CSV staging secara luas, atau arsitektur. Justifikasi dan bukti ada pada keputusan controller terbaru.

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

**Riwayat penyerahan:** PR15 (13 November), PR17 (14 November), PR19 (15 November) dan kandidat keempat ini (15 November) adalah hasil executor pada ID0010 yang sama; tiga pertama changes_requested (PR16/PR18/PR20). Laporan historis dipertahankan; ringkasan penyerahan ketiga tetap pada histori git dan [laporan executor ketiga](../report/orchestrator/20261114T164816Z-0010-pa006-idempotency.md).

**Ringkasan hasil implementasi (penyerahan keempat, executor):** menutup tiga finding OPEN keputusan PR20 — (1) **REV-1311-01**: parser scope legacy migrasi 0004 ditulis ulang toleran URN/braced-URN pada posisi tenant MAUPUN resource (kwargs URL mentah main; scope `urn:uuid:` valid tidak lagi dihapus sebagai "malformed"); scope tak-terurai DIPERTAHANKAN sebagai baris mati `__unparsed__` (fail-safe — parser delimiter gagal bukan izin menghapus penjaga non-expired). Probe controller live-upgrade dijalankan ulang UTUH dari worktree baseline main 9903d9b: URN completed → **201 replay submission semula, submission/file tetap 1**; URN ambiguous → **409 aman, submission/file tetap 1** (dua kasus yang dulu FAIL kini PASS); RLS + `uq_idem_identity` terverifikasi; retry konkuren pasca-migrasi keduanya replay. (2) **REV-1311-03A**: normalisasi hash v2 bertingkat `allocations[].invoice_id` (alias satu invoice logis mereplay 200 — sebelumnya 200/409/200); beda invoice/amount 409; malformed 422; retained raw-hash replay; konkuren alias-vs-canonical mereplay leader. **REV-1311-03B**: selected_account_ids dikanonikalisasi sebelum preview counts, payload job durable, dan konsumsi domain (422 malformed; payload job lama ber-ejaan mentah tetap mengenai objek sama; satu job). (3) **REV-1511-05**: preview validasi CSV bebas plaintext credential (mask `********`); migrasi **0005** baru scrub record retained tanpa menghapus penjaga; replay pasca-scrub steril; probe controller: `plaintext_in_initial/cached/replayed_response` **false×3** (dulu true×3); mock frontend paritas. Bukti: **suite penuh 452 passed** (PG 17.11 nyata, peran non-superuser, FreeRADIUS aktif), probe controller 15/15 langkah exit 0 + edges 2 passed + effects 5 passed (termasuk 4 wait-graph query/blocker), targeted 93 passed, `manage.py check` 0 issue, `makemigrations --check` bersih, docs PASS, frontend typecheck/lint/Vitest 66/i18n/contrast/live-build sukses. Review internal independen PASS_WITH_NOTES; tiga temuan reviewer (braced-URN parser P2 + dua ketebalan tes P3) **ditutup pada kandidat** sebelum penyerahan. Semua baris acceptance packet terpetakan PASS pada laporan executor §5; NOT_RUN: host/lab/E2E/benchmark (di luar scope). Detail + evidence: [laporan executor keempat](../report/orchestrator/20261115T044621Z-0010-pa006-idempotency.md) + [executor-evidence](../report/executor-evidence/20261115T044338Z-0010-pa006/).

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

## Koreksi controller 15 November 2026 — review PR19 (historis), ID0010 tetap

Review exact PR19 **9e9bf2d42002a00a69d54fc355b77384897b9478**:
**changes_requested**. [Laporan controller](../report/controller/20261114T212816Z-0010-pa006-review.md)
mengalahkan klaim all-PASS executor di atas; klaim itu dipertahankan sebagai
histori penyerahan. Instruksi terbaru berada pada
`review/0010-pa006-controller-20261115` sampai integrasi. Jangan kembali ke
baseline main atau mengulang group-parent/atomic-claim yang sudah benar.

| Finding | Koreksi minimum | Acceptance penutup |
|---|---|---|
| **REV-1311-01 P1 OPEN (partial)** | Parse seluruh valid legacy UUID spellings, termasuk URN tenant/resource; jangan menghapus ambiguous guard karena parser delimiter gagal. Preserve canonical/platform/opaque handling dan atomicity/drain policy. | Actual main HTTP upload→real0004→retry canonical/alias: known response asli, submission/file1; unknown409/reconciliation terbukti, tetap1. Uji URN pada tenant/resource, completed/no-response, wrong body/target409, concurrent retry dan malformed retained data fail-safe. Root sudah membuktikan completed+ambiguous URN membuat submission/file1→2. |
| **REV-1311-03 P2 OPEN (partial)** | Lengkapi actual typed UUID body inventory: nested `allocations[].invoice_id`, serta selected IDs yang canonical di hash **dan** preview/job/consumption. Jangan normalize opaque strings atau reorder arrays. | Money canonical/uppercase-compact/URN alias same key mereplay200 dengan allocation/receipt/audit/outbox1; beda invoice/amount409; concurrency+retained hash terbukti. Alias-first selected target menghasilkan preview/payload/effect sama dengan canonical-first, satu job; malformed422. Root membuktikan200/409/200 dan alias202 to_create0 vs expected1. |
| **REV-1511-05 P1 NEW, pre-existing path** | Proyeksi CSV validation/preview/cache/replay harus tanpa plaintext credential; tangani retained cache dengan aman tanpa erase-guard/blind reexecution. Update inventory safe response dan assertion lama yang menuntut raw password preview dengan justifikasi security contract. | Ephemeral sentinel tidak ada dalam initial/replayed response atau persisted/retained response_body; logical replay nonsecret sama, current auth+HMAC utuh. Log boolean/count saja. Root membuktikan seluruh presence boolean true pada200/200. |

**CLOSED pada reviewed SHA:** REV-1311-02 (parent+group/current validation,
decisions[2,2], malformed422/missing404); REV-1411-04 (full authenticated
HTTP/after-write rollback+takeover). Query/blocker supplement controller
membuktikan empat wait graphs: leader→holder dan claim contender→leader.
Saat memelihara test terkait, bawa supplement assertions atau padanannya;
jangan mengulang implementasi yang sudah lulus atau mempertahankan klaim
Lock generik sebagai bukti query/blocker tertentu.

Root independen: **67 targeted +426 full +6 prior probes PASS**;
PA-001 semua10 tetap lulus, Django/migration/docs PASS; exact candidate CI
43618187731 backend/frontend/docs success. Tiga new HTTP effect/replay
probes FAIL (nested UUID,selected IDs,plaintext cache), dua actual URN
upgrade cases FAIL; canonical real-upload upgrade PASS. Dua kegagalan
awal harness query capture diperbaiki dengan8192-byte capture dan affected
platform/rollback probes PASS tanpa melemahkan assertion.
Evidence dan scripts berada di [controller evidence](../report/controller-evidence/20261114T212816Z-pa006/test_review_edges.py),
[effect/lock probes](../report/controller-evidence/20261114T212816Z-pa006/test_review_effects.py),
[actual-source upgrade](../report/controller-evidence/20261114T212816Z-pa006/live_upgrade_edges.py).

Penyerahan koreksi: preserve histori dan perbaikan yang benar; finding→code
change→failing-before/passing-after closing tests→actual evidence untuk
01/03/05, lalu acceptance awal lengkap, candidate+remote+CI exact SHA.
Execution `ready`, review `changes_requested`, next **coding_agent**.
PA-002/003 dan task dependent baru belum eligible; tidak merge/deploy/tag.

## Koreksi controller R4 — 15 November 2026, review PR21 (keputusan terbaru)

**changes_requested** pada exact PR21
**634da4224f15dd6a5a4e9010fe1811dec8c7954d**. Keputusan pada
[laporan controller R4](../report/controller/20261115T053138Z-0010-pa006-r4-review.md)
menggantikan klaim closure01 executor pada penyerahan keempat. Original
objective/work/acceptance/verification tetap utuh. ID0010 unfinished,
execution **ready**, review **changes_requested**, next **coding_agent**.

**Satu finding terbuka: REV-1311-01 P1, partial.** Standard URN completed
replay dan ambiguous409 kini benar. Tetapi actual main HTTP menerima
`uuid:<UUID>` dan `urn:<UUID>`; migrasi0004 memindahkannya ke operasi mati
`__unparsed__`, lookup canonical melewati penjaga, retry membuat
**submission dan file fisik1→2** (completed uuid, ambiguous uuid, completed
urn). Semua old HTTP/migration exit0; tiga post-upgrade assertions FAIL.
Menyimpan baris yang tidak mungkin ditemukan runtime bukan safe guard.

**Koreksi minimum:** petakan tenant/resource memakai grammar UUID yang
benar-benar diterima writer lama dengan satu interpretasi canonical; jangan
menambah cabang prefix khusus per contoh. Bila identitas sungguh ambigu,
fail-stop migrasi atau rekonsiliasi sebelum mengizinkan efek baru. Preserve
principal/platform/opaque semantics, completed/no-response guard, dedupe,
RLS, history, write-freeze dan fix-forward. Jelaskan affected-state recovery
bila0004 telanjur diterapkan; edit0004 saja tidak memperbaiki DB yang sudah
menjalankannya. Asumsi sandbox-only boleh dinyatakan eksplisit tanpa klaim
reparasi deployment yang tidak diuji. Tidak perlu framework/migration engine.

**Acceptance penutup:** jalankan ulang
[actual-source upgrade probe](../report/controller-evidence/20261115T053138Z-pa006-r4/live_upgrade_aliases.py)
dan [runner](../report/controller-evidence/20261115T053138Z-pa006-r4/run_upgrade_aliases.sh)
dengan backend main9903d9b pada fase before dan kandidat baru pada after:
canonical/URN controls, uuid-only completed+unknown dan urn-only completed
harus seluruhnya mempertahankan efek/file1. Known outcome201 mereplay ID
asli; unknown409/reconciliation tidak blind execute. Perluas grammar cases
pada **tenant dan resource**, termasuk prefix berulang yang diterima
baseline; unresolved input harus fail-safe. Cover canonical/alias retry,
wrong target/body409, concurrent retry, platform remap dan legacy opaque.
Jangan menyebut arbitrary corrupt input sebagai old-writer outcome tanpa
bukti. Tidak menurunkan assertion atau memutasi history uang.

**CLOSED pada634da42:** REV-1311-03A/03B (nested money+selected effect),
REV-1511-05 (fresh/stored/replay dan retained string-secret scrub),
REV-1311-02 (parent/group) dan REV-1411-04 (actual HTTP wait graphs +
after-write rollback/takeover). PA-001 semua10 lulus. Jangan implementasi
ulang bagian yang sudah benar. Root independen: **93 targeted,452 full,
6 prior probes,2 edges,5 effects PASS**, Django/migration/docs PASS;
exact-head CI3/3 success. Masalah parser tetap FAIL meski suite hijau.

Saat resubmit, matriks finding01→code→failing-before/passing-after→evidence
serta acceptance awal lengkap; source grammar/pure evidence harus dibedakan
dari actual HTTP/database/file effect. Koreksi wording test nested race:
barrier-only test tidak membuktikan lock waiting; query+blocker berasal dari
probe forced wait yang terpisah. No need repeat source implementation for
that attribution clarification. PA-002/003 tetap tertahan; tidak ada
packet0020/merge/deploy/tag. Beta **NOT_READY**.
