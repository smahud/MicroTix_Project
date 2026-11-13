# 0010 — PA-006: HTTP idempotency yang aman terhadap scope dan race

| Field | Nilai |
|---|---|
| Task ID | `0010` |
| Execution status | `ready` — reopened for corrections on ID0010 |
| Review status | `changes_requested` |
| Controller | ChatGPT Work / reviewer proyek |
| Executor | Coding agent z.ai (sandbox); sesi 13 November 2026 |
| Baseline yang diperiksa | `main@a0f653e89bf77b1238ca0ed9bcdb0e2f0aee612e`, 12 November 2026; PR10 hanya dokumentasi, source PA-006 tetap sama. Fetch sesi ini: `origin/main` = `9903d9b` (PR12 merged, docs-only — `git log a0f653e..9903d9b -- backend/` kosong) |
| Dependency | PA-001 merged PR #9, merge `8ce94d468232eda77cd675f6d18e5fcb41f3d708`; semua source PR9 ada pada baseline |
| Implementation / tested SHA | `159f7ed` (commit penyerahan; seluruh tes dijalankan persis pada tree ini) |
| Candidate branch / published SHA / PR | [PR #15](https://github.com/smahud/MicroTix_Project/pull/15) `session/2026-11-13-pa006-idempotency`; exact reviewed head `7480c80e2c27b8b06048b77132d235efe6b3a3c2`, code/tested ancestor `159f7edac42d6cb49093feeba3fa8cd0b1e775a1` |
| Execution report / acceptance evidence | [report/orchestrator/20261113T003000Z-0010-pa006-idempotency.md](../report/orchestrator/20261113T003000Z-0010-pa006-idempotency.md) — matriks acceptance→actual→evidence lengkap; internal reviewer [report/reviewer/20261113T001500Z-0010-pa006-review.md](../report/reviewer/20261113T001500Z-0010-pa006-review.md) (PASS_WITH_FINDINGS, 0 P1; P2+E-P3-1 ditutup tes tambahan sebelum penyerahan) |
| Controller review report / reviewed SHA | [20261113T114222Z-0010-pa006-review.md](../report/controller/20261113T114222Z-0010-pa006-review.md), `changes_requested` pada `7480c80e2c27b8b06048b77132d235efe6b3a3c2`; keputusan pada branch `review/0010-pa006-controller-20261113`, belum integrated ke main/PR15 |
| Next actor | `coding_agent` |
| Next action | Fetch ref controller; bawa record/task ini secara semantik, perbaiki REV-1311-01/02/03 pada kandidat existing, jalankan closing tests dan resubmit SHA baru pada ID0010; PA-002/PA-003 belum eligible |

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

**Riwayat penyerahan awal executor, 13 November 2026 (belum accepted):** executor melaporkan selesai sesuai scope. Review controller di bawah membuktikan tiga gap; ringkasan awal berikut dipertahankan sebagai atribusi penyerahan, bukan keputusan acceptance.

- `backend/domains/common/idempotency.py`: identity `principal + tenant|platform + operation + resource kanonik + key`; protokol claim/replay SATU transaksi (klaim INSERT + handler + respons) — pesaing same-identity menunggu unique index lalu replay (commit) atau eksekusi segar (rollback); record tanpa respons ditolak fail-safe 409 (tidak blind-execute); scope platform eksplisit (tanpa fallback sesi); kanonikalisasi UUID (alias bergabung, malformed → 422); purge TTL `FOR UPDATE SKIP LOCKED`.
- `jobs/models.py` + `migrations/0004`: UNIQUE(principal, scope, idem_key); legacy dipertahankan tanpa rewrite (Add-before-Remove; kebijakan legacy pada laporan §2).
- Views: `payment_submission` kini menscope `invoice_id`; `identity_conflict_resolve` resource opaque (`resource_is_uuid=False`). Tidak ada perubahan bentuk respons API.
- Bukti (PostgreSQL 17.11 nyata, klien HTTP independen per thread, interleave dipaksa + observasi pg_stat_activity): **25 tes baru PA-006 lulus; suite penuh backend 408 passed** (baseline 383); PA-001 konkurensi 10/10 tetap lulus; `manage.py check` 0 issue; `makemigrations --check` bersih; docs check PASS. Matriks per baris acceptance pada execution report §4, termasuk konflik material 404→422 malformed (§7) yang menunggu keputusan controller.
- CI kandidat (backend/frontend/docs) dijalankan pada PR; hasil diverifikasi sebelum status done dipertahankan. Bukan bukti host/lab/DR; Beta tetap NOT_READY.

## Koreksi controller 13 November 2026 — ID0010 yang sama

Review exact head `7480c80`: **changes_requested**. Root menjalankan 55 tes terarah dan suite penuh 408 passed pada PostgreSQL17.11 NOSUPERUSER/NOBYPASSRLS. Lima conformance probes tambahan gagal dan membuktikan gap di bawah; bukti/command/NOT_RUN pada [report controller](../report/controller/20261113T114222Z-0010-pa006-review.md). Implementasi yang sudah benar dipertahankan; jangan ulang PA-001 atau membuat task pengganti.

| Finding | Koreksi minimum | Acceptance penutup |
|---|---|---|
| **REV-1311-01 P1**, legacy proof scope berubah | Rekonsiliasi/compatibility retained key lama per principal/tenant/target. Validasi submission→invoice/actor sebelum replay; record ambigu tidak boleh blind-create. Jelaskan juga platform/UUID-alias legacy shape dan urutan upgrade tanpa proses kode lama+baru bersamaan. | Old-scope success lalu retry owner/invoice/key/body sama tidak membuat submission/file kedua; original response sama. Uji invoice B, beda body, no-response legacy, concurrent retry dan actual migration. Jangan replay A ke B. |
| **REV-1311-02 P1**, parent sesi migrasi hilang | Identity resource mencakup canonical migration_id + opaque group_id; semua structured component divalidasi sebelum replay; legacy group-only ditangani aman. | Same group/key/body untuk sesi A/B menyimpan keputusan masing-masing; retry A replay; parent alias sama identity; malformed422 dan missing404 tetap benar walau cache grup sudah ada. |
| **REV-1311-03 P2**, typed body UUID belum canonical sebelum hash | Normalize field identity yang declared/typed pada handler aktif sebelum HMAC; preserve exact-case username/password/string, array semantics dan real body/file conflict. | package_id canonical/uppercase-compact alias pada service/key sama replay200; package berbeda409; cek field UUID body lain yang relevan serta compatibility retained hash. |

Probes reproduksi disimpan di `report/controller-evidence/20261113T114222Z-pa006/`; source aplikasi tidak diubah reviewer. Correct migration0004 recovery narrative: default PostgreSQL/Django migration atomic, bukan partial-per-statement; dokumentasikan drain/write-freeze, ordering dan fix-forward tanpa memperluas task ke installer. Perubahan expectation malformed platform404→422 **diterima sesuai kontrak existing**; non-platform404 tetap terjaga.

Sumber scope/pekerjaan/acceptance awal di atas tetap berlaku; koreksi ini membuat acceptance yang belum terpenuhi konkret, tidak mengubah produk, release gate atau menambah framework. Executor memperbarui laporan aktual per finding dan menautkan controller report; jangan mengklaim semua acceptance lulus hanya karena 408 tes existing hijau.

Penyiapan instruksi/workflow bukan implementasi PA-006; laporan awal executor tetap historis dan koreksi diserahkan dengan SHA/evidence baru.

Isi metadata di atas, update [LATEST_HANDOFF](../report/LATEST_HANDOFF.md) dan [progress](../docs/progress.md), lalu ikuti penutupan pada panduan tetap: completion rename ke `0010-pa006-idempotency_done.md` ikut commit, push/remote/CI diverifikasi, review menjadi pending. Task ini baru accepted ketika controller mencatat review exact SHA. Jangan memasukkan secret/runtime/unrelated files ke commit atau merge otomatis ke main.

Next setelah accepted: controller menyiapkan PA-002/PA-003 untuk job fencing/drain/authority, termasuk fresh HTTP RLS payload dan uncertain/cancel/stale-writer cases. Kandidat Beta tetap NOT_READY selama gates terkait belum dipenuhi. Tidak ada izin rollout atau tanggal peluncuran yang dibuat oleh task ini.
