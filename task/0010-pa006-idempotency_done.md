# 0010 — PA-006: HTTP idempotency yang aman terhadap scope dan race

| Field | Nilai |
|---|---|
| Task ID | `0010` |
| Execution status | `done` (penyerahan executor; bukan acceptance/merge/release) |
| Review status | `pending` (menunggu controller review exact SHA) |
| Controller | ChatGPT Work / reviewer proyek |
| Executor | Agent implementasi sandbox Z.ai — sesi 2026-11-14 |
| Baseline yang diperiksa | `main@a0f653e89bf77b1238ca0ed9bcdb0e2f0aee612e`, 12 November 2026; diverifikasi ulang terhadap main aktual `9903d9b` (PR10/11/12 hanya dokumentasi — source PA-006 identik) saat mulai sesi 14 November 2026 |
| Dependency | PA-001 merged PR #9, merge `8ce94d468232eda77cd675f6d18e5fcb41f3d708`; semua source PR9 ada pada baseline — tidak diulang (10 tes konkurensi PA-001 tetap lulus pada regression) |
| Implementation / tested SHA | `5922e1f` (commit implementasi pada branch kandidat — klaim, efek domain, dan respons dalam SATU transaksi; suite penuh **401 passed** pada konten tepat commit ini). Commit penyerahan/metadata setelahnya adalah report-only descendant atas kode yang tidak berubah |
| Candidate branch / published SHA / PR | `session/2026-11-14-pa006-idempotency`; head branch = commit penyerahan (packet+handoff+progress, tanpa perubahan source); PR dibuat setelah push — lihat LATEST_HANDOFF untuk ref/PR aktual |
| Execution report / acceptance evidence | `report/orchestrator/20261114T150000Z-0010-pa006-idempotency.md` (matriks acceptance → actual result → evidence untuk SEMUA baris; tabel 28 call site; kebijakan migrasi/legacy; command/exit) |
| Internal reviewer report | `report/reviewer/20261114T150000Z-0010-pa006-review.md` — LULUS DENGAN CATATAN (6 temuan P3, tanpa P1/P2; koreksi minimum diterapkan sebelum penyerahan; review internal executor, BUKAN acceptance controller) |
| Controller review report / reviewed SHA | Belum ada — review implementasi belum dimulai; controller mengikat verdict pada exact SHA kandidat |
| Next actor | `controller_reviewer` |
| Next action | Review exact SHA kandidat: matriks acceptance laporan eksekusi, tabel call-site, interleaving tes konkuren (lock observation via pengamat psycopg), kebijakan migrasi/legacy 0004, dan 3 FUP terdokumentasi. Changes requested → buka kembali task0010 ID sama |

Mulai dari [panduan tetap](0000-start-here.md) dan [CONTRACT](../CONTRACT.md). Ini task implementasi, **bukan bukti PA-006 selesai**. Fetch refs dan review delta bila remote berubah; pilih branch baru dari main aktual dengan packet ini tersedia. Jika instruksi belum merged, catat instruction ref/PR dan bawa perubahan dokumentasi yang sah secara semantik; jangan menimpa pekerjaan lain atau menganggap SHA baseline sebagai main untuk selamanya.

## Tujuan dan bukti masalah

Tutup PA-006 memakai PostgreSQL dan mekanisme existing. Request uang/provisioning yang diretry atau bersamaan harus mewakili satu logical action sesuai scope yang sah. Jangan mengulang perbaikan locking invoice PA-001 yang sudah benar.

Sumber kebutuhan: [ARCHITECTURE §5](../docs/ARCHITECTURE.md), [FINANCE](../docs/FINANCE.md), [ACCEPTANCE §4](../docs/ACCEPTANCE.md), serta [register review sebelumnya](../report/controller/20261111T074225Z-repo-handoff-review.md). Mapping task produk yang terdampak dirujuk dari [tasks.json](../docs/tasks.json); jangan membuat backlog pengganti.

Bukti source pada baseline (SEMUA telah ditutup oleh implementasi — lihat laporan eksekusi §1):

- ~~[common/idempotency.py](../backend/domains/common/idempotency.py) menyimpan principal tetapi tidak memasukkannya dalam scope/lookup/update; query existing lalu insert tidak memiliki conflict-safe concurrent reservation; record tanpa response mengizinkan eksekusi ulang tanpa pembuktian keadaan efek~~ → identitas 5-tuple + claim ON CONFLICT + satu transaksi protokol + tolak-aman klaim tanpa respons.
- ~~[jobs/models.py](../backend/domains/jobs/models.py) uniqueness hanya `(scope, idem_key)`~~ → `uq_idem_identity (principal, tenant_scope, operation, resource, idem_key)` via migrasi 0004 (backfill canonical + dedupe alias + purge klaim tanpa respons).
- ~~[subscriptions/views.py](../backend/domains/subscriptions/views.py) `payment_submission` tidak menyertakan `invoice_id`~~ → `resource_from=invoice_id`; platform decorators `platform=True`.
- ~~URL UUID bisa mempunyai beberapa representasi untuk identitas yang sama~~ → kanonikalisasi UUID (alias → satu scope); structured malformed → 422; `resource_uuid=False` untuk token opaque group_id.
- ~~Tes lama hanya membuktikan sequential quotation replay/conflict~~ → 18 tes baru mencakup concurrent HTTP/protocol race (interleaving dipaksa + observasi pg_stat_activity), boundary principal/tenant/platform/resource, alias, step-up saat replay, rollback, stuck-claim, TTL/legacy, dan migrasi.

## Scope dan ownership

Diizinkan: `backend/domains/common/idempotency.py`; bagian model/migration idempotency milik jobs bila perlu; decorator resource/platform scope dan metadata API terkait pada views pemilik; tes relevan; laporan/task/progress/handoff. Hanya perubahan minimum yang dibutuhkan kontrak ini.

Tidak termasuk: implementasi PA-002/003 engine lifecycle, scanner/MFA, quota policy, network adapters/mutation, installer/deployment, ledger/Tax/ACS/OLT, perubahan CONTRACT atau kebijakan normatif. Bila incidental defect tidak diperlukan untuk PA-006, catat follow-up berbukti. Tidak ada deployment atau akses router/host produksi. Jangan menambah Redis/Celery/broker/framework/repository abstraction.

Yang DIPAKAI dari daftar izin: `common/idempotency.py`; `jobs/models.py` (IdempotencyKey) + `jobs/migrations/0004_idempotency_identity.py`; `subscriptions/views.py` (payment_submission + 3 platform call sites); `customers/views.py` (identity_conflict_resolve `resource_uuid=False`); tes (`test_idempotency_pa006.py` baru + koreksi ekspektasi `test_ops_platform_admin.py`); laporan/task/progress/handoff. Redis/Celery/framework baru: tidak ditambah.

## Pekerjaan wajib

1. ~~Buat tabel ringkas seluruh `@idempotent` call sites~~ → laporan eksekusi §2 (28 call site; path:line aktual kandidat).
2. ~~Samakan identity untuk claim, lookup, uniqueness, response update dan replay~~ → 5-tuple canonical (lihat §1 laporan).
3. ~~Resource SaaS proof mencakup invoice; operasi platform scope eksplisit~~ → `resource_from=invoice_id`; `platform=True`.
4. ~~Claim/replay transaction protocol conflict-safe~~ → INSERT ON CONFLICT + atomic tunggal; konkuren menunggu lalu mereplay; tanpa 500/duplicate; record tanpa respons ditolak aman.
5. ~~Auth/membership/permission/step-up diperiksa sebelum replay; HMAC; tidak menyimpan plaintext~~ → gate `initial()` tetap sebelum decorator; HMAC-SHA256 body canonical dipertahankan; tidak ada respons ber-credential yang di-cache.
6. ~~Migration kecil milik jobs dengan kebijakan legacy eksplisit~~ → migrasi 0004 (backfill/dedupe/purge/ordering/reverse/fix-forward; RLS tidak dilemahkan; history bisnis tidak di-drop).
7. ~~Bedakan committed DB effect, response persistence, external/file side effects~~ → laporan eksekusi §4 (file yatim pra-ada dicatat; tanpa klaim exactly-once eksternal).

## Acceptance yang wajib dibuktikan

Seluruh baris dibuktikan PASS dengan PostgreSQL nyata, peran non-superuser/non-BYPASSRLS, klien HTTP terautentikasi independen, dan interleaving dipaksa (penahanan kunci baris domain + observasi pg_stat_activity via pengamat psycopg; PID thread dibuktikan berbeda). Matriks lengkap acceptance → actual result → evidence: **laporan eksekusi §5** (18/18 tes PA-006 lulus; suite penuh 401 passed; regression PA-001 10/10).

## Verifikasi dan review

- Dijalankan: targeted PA-006 (18), suite backend penuh (401), PA-001 konkurensi (10), `manage.py check` (0 issue), `makemigrations --check` (bersih), migrasi 0004 pada dev DB + `grant_runtime`, `check_docs.py` (PASS), frontend paritas CI (`tsc`, `eslint`, `vitest 66`, `check_i18n`, `vite build` live — semua exit 0). Command/environment/exit: laporan eksekusi §6.
- Independent reviewer (sub-agent read-only, CONTRACT §5): laporan `report/reviewer/20261114T150000Z-0010-pa006-review.md` — memeriksa call-site table, interleaving, transaction/savepoint behavior, compatibility/legacy, no auth bypass; verdict internal LULUS DENGAN CATATAN (6×P3); koreksi minimum (tabel call-site; preservasi legacy opaque) diterapkan sebelum commit penyerahan.
- NOT_RUN (di luar scope, tidak diklaim): install/upgrade host (Gate A/G), lab perangkat nyata (G1), benchmark kapasitas (S6).

## Penyerahan dan batas selesai

Laporan executor: `report/orchestrator/20261114T150000Z-0010-pa006-idempotency.md`; internal reviewer di `report/reviewer/20261114T150000Z-0010-pa006-review.md` — keduanya memuat solution/alternatives, migration/recovery policy, scope table 28 call site, setiap baris acceptance → actual result → evidence, risiko/unfinished work dan next actor/action. Laporan internal executor tidak menggantikan keputusan controller.

**Ringkasan hasil implementasi:** SELESAI SESUAI SCOPE EXECUTOR. Yang berubah: (1) protokol idempotency claim/replay satu-transaksi dengan identitas canonical 5-tuple pada `common/idempotency.py`; (2) model+migrasi jobs 0004 (kolom identitas, `uq_idem_identity`, backfill/dedupe/purge dengan preservasi resource opaque); (3) call-site `payment_submission` (resource invoice_id), tiga call-site platform (`platform=True`), `identity_conflict_resolve` (`resource_uuid=False`); (4) 18 tes PA-006 baru + satu koreksi ekspektasi lama (malformed submission_id 404→422 sesuai acceptance). Bukti: suite penuh 401 passed (baseline 383) pada tested SHA `5922e1f`; seluruh acceptance packet PASS (matriks laporan §5); regresi nol. Batas: review controller belum ada; merge/deploy tidak terjadi; FUP-001/002/003 dicatat untuk packet berikutnya; environment blocker beta tetap terbuka.

Controller menyimpan keputusan implementasi di `report/controller/<UTC>-0010-pa006-review.md`, menautkannya ke metadata packet ini dan mengikatnya pada exact reviewed SHA. Changes requested membuka kembali task0010 yang sama (rename balik ke nama unfinished dengan ID sama); coding agent memperbaiki finding dan menyerahkan SHA baru. Accepted mengembalikan kendali ke controller untuk penyiapan task penerus sesuai dependencies/integration. Publish keputusan di ref GitHub yang disebut di handoff sebelum pergantian peran; jangan meninggalkan keputusan hanya di chat.

Next setelah accepted: controller menyiapkan PA-002/PA-003 untuk job fencing/drain/authority, termasuk fresh HTTP RLS payload dan uncertain/cancel/stale-writer cases. Kandidat Beta tetap NOT_READY selama gates terkait belum dipenuhi. Tidak ada izin rollout atau tanggal peluncuran yang dibuat oleh task ini.
