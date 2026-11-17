# Independent review — koreksi task0020 (REV-1711-01–09)

- Author/role: reviewer independen read-only (Task ID sub-agent:
  **R1-correction-review**), didelegasikan untuk memeriksa penyerahan koreksi
  executor atas verdict `changes_requested` controller R1.
- Task ID: **0020** (PA-002+PA-003) — koreksi pada ID yang sama, bukan task baru.
- Mode: **READ-ONLY terhadap seluruh repo**. Reviewer ini TIDAK mengubah kode,
  tes, migrasi, packet, branch, commit, merge, push, deployment, dan tidak
  mengakses perangkat. Satu-satunya tulisan reviewer: laporan ini.
- Diff yang diperiksa: **working tree belum di-commit di atas `0e45157`**
  (branch `session/2026-11-17-0020-job-lifecycle-correction`, HEAD =
  `0e45157`, `git status` = 12 file backend termodifikasi + 3 path report
  untracked; tidak ada perubahan `task/`, settings, CI, atau migrasi).
- Input: [Controller R1 §3](../controller/20261117T134100Z-0020-job-lifecycle-review.md)
  (REV-1711-01–09 + minimum correction), [laporan penyerahan executor]
  (../orchestrator/20261117T160000Z-0020-correction-delivery.md), `git diff`
  penuh (740 insertions/71 deletions), evidence
  [20261117T150000Z-0020-correction](../executor-evidence/20261117T150000Z-0020-correction/),
  serta probe controller asli (tidak berubah di working tree).
- Standar pemeriksaan: setiap temuan harus TERTUTUP tanpa melemahkan assertion,
  requirement, atau kontrol keamanan; tabel state §6; RLS/tenant scope; tidak
  ada jalur blind-retry yang masih terjangkau.

## Ringkasan verdict

**REKOMENDASI: koreksi diterima untuk controller re-review** — REV-1711-01–08
tertutup nyata pada source + probe; REV-1711-09 tertutup sebagai suplemen
bukti. Ada 2 temuan baru berkelas P2 (CORR-REV-01 latent no-effect blanket,
CORR-REV-04 langkah publikasi belum dilakukan) dan risiko residual tercatat.
Tidak ditemukan pelemahan assertion/kontrol pada diff.

## 1. Matriks verdict per temuan R1

| Temuan | Verdict | Bukti file:baris (dari diff/working tree + log probe) |
|---|---|---|
| REV-1711-01 (P1, stale worker commit domain) | **CLOSED** | `engine.py:194–217` `assert_owned()` baca segar token/epoch/state; `engine.py:219–236` `scope()` memanggil guard SEBELUM dan SESUDAH body, keduanya DI DALAM `tenant_scope` — dan `tenant_context.py:34–54` membuktikan `tenant_scope` membungkus `transaction.atomic()`, sehingga guard+commit domain atomik (kehilangan mid-unit → raise → rollback unit, bukan hanya envelope CAS). `engine.py:144–156` `_fenced` kini MELEMPAR `OwnershipLost` (heartbeat/progress tidak bisa diabaikan — semua pemanggil produksi memanggil `ctx.progress(...)` tanpa memeriksa return: `radius/handlers.py:99,140,180,216,224,252`, `backups/service.py:184,222,282`, `customers/handlers.py:47,56,84,91`). Guard diteruskan ke unit milik service: `network/services.py:874–880` (`finalize_verification` guard di dalam transaksi commit router/peer/enrollment), `network/services.py:940–988` (guard di dalam TIAP unit `run_discovery`: snapshot, failed-mark, objek+snapshot SUCCEEDED+link migrasi, health), pemanggilan `network/handlers.py:78–80,115–121`. Probe executor (controller file asli): `lifecycle-probes-after.log:2` → `object_count=0, health_count=0, snapshot_status=["running"]`, worker bounded (failing-before: objek+health+succeeded). |
| REV-1711-02 (P1, error pasca-efek → retry otomatis) | **CLOSED** (dengan catatan CORR-REV-01) | `engine.py:60–80` `JobError.no_effect` = bukti eksplisit pra-efek; `engine.py:697–703` exception generic saat executing → `internal_error` **uncertain=True** (bukan retryable); `engine.py:823–853` `_finish_execute_failure`: `retryable` TANPA `no_effect` → ditahan **UNCERTAIN**; `retryable+no_effect` → `engine.py:856–906` `_retry_no_effect` komposisi DUA LANGKAH sah tabel §6: executing→uncertain→retry_wait (`models.py:93–103`: EXECUTING tidak memuat retry_wait; UNCERTAIN→RETRY_WAIT sah — tidak ada transisi tabel dilanggar). Kegagalan pra-efek tetap boleh retry (claimed/preflight→retry_wait via `_retry_or_fail`, legal pra-efek). Klasifikasi handler jujur: `backups/service.py:198–218` (TimeoutAfterSend tetap uncertain; Unreachable pra-kirim no_effect), `customers/handlers.py:15–28` (dependency_unavailable — handler DB-only dalam `ctx.scope()`, rollback bersih), `network/handlers.py:81–88` (probe baca-saja api_ssl). Probe: `lifecycle-probes-after.log:1` → `first_state=uncertain, send_count=1, reclaimed=false, artifact_count=1` (failing-before: retry_wait + send kedua). Tes existing `test_job_retry_then_backoff` tetap lulus via no_effect eksplisit. |
| REV-1711-03 (P1, retry ancestor melewati descendant uncertain) | **CLOSED** | `engine.py:1140–1148` `_RETRY_BLOCKING_STATES` (seluruh nonterminal termasuk uncertain/recovery_required); `engine.py:1151–1164` `_lineage_root_id` (naik ke akar, guard siklus depth-64); `engine.py:1167–1186` `_lineage_active_exists` BFS SELURUH descendant (bukan child langsung); `engine.py:1189–1238` `retry_job` mengunci baris origin + baris AKAR lineage (serialisasi retry serentak origin/descendant; urutan lock origin→akar konsisten, root holder tidak menunggu baris lain → tidak ada deadlock siklus), tolak `retry_active_exists`; retry atas terminal dengan outcome final tetap sah. `create_job` berjalan dalam transaksi yang sama dengan lock akar → cek+create atomik. Probe: `lifecycle-probes-after.log:3` → `extra_retry_created=false, error=retry_active_exists, send_count=1`. |
| REV-1711-04 (P1, pemilik router berikutnya kirim sebelum readback unknown) | **CLOSED** (residual CORR-REV-02) | `engine.py:635–659` sebelum acquire advisory sender: cek **hold durable** — job router sama lain pada state `uncertain`/`recovery_required` (id berbeda) → job ini `RETRY_WAIT` `router_outcome_unknown` (`attempt=F("attempt")-1` — attempt tidak dikonsumsi), state DB bertahan melewati proses; `engine.py:660–673` advisory session lock tetap untuk penulis hidup; `engine.py:1011–1017` `resolve_uncertain(applied=False)` tetap menolak selama penulis lama aktif (REV-2011-03 dipertahankan). Router lain tetap mandiri. Probe: `lifecycle-probes-after.log:4` → `second_state=retry_wait, send_count=1` (failing-before: successor langsung mengirim). |
| REV-1711-05 (P1, revoke/demote setelah preflight melepas router) | **CLOSED** | `engine.py:602–609` — `check_current_authority(job, payload)` dipanggil ulang pada **batas efek SETELAH preflight dan sebelum kirim** (di luar cek awal `engine.py:583–587`); `check_current_authority` membaca segar User/membership/peran izin/router RLS+scope (`engine.py:464–548`) — bukan snapshot enqueue. Per-chunk B2/B5 `ctx.recheck_authority()` dipertahankan (`radius/handlers.py:391–401`). Probe: `authority-probes-after.log:7–8` → `state=failed, error_code=authority_denied, router_released=false, distinct_db_connections=true` (pid worker ≠ controller). |
| REV-1711-06 (P1, endpoint job abaikan router scope membership) | **CLOSED** | `jobs/views.py:47–77` `_require_job_authority` kini memeriksa `membership.router_scope` untuk job ber-router → **404 generik SEBELUM aksi** (nol perubahan state/job/nol job baru); urutan: tenant-scope 404 → router-scope 404 → izin 403 → step-up sensitif tetap. Dipakai pada detail/retry/cancel (`views.py:105,115,139`). Semantik `router_scope=None` = tidak dibatasi — konsisten dengan implementasi worker-side `engine.py:540–548` yang sudah diterima R1. List (`views.py:79–96`) tidak diubah — tetap izin baca `customers.read` existing, tanpa perluasan privilege. Probe: `authority-probes-after.log:1–6` → 404 untuk ketiga aksi; `job_state_before==after`, `job_count_before==after`. |
| REV-1711-07 (P2, B6 rollback menahan transaksi saat adapter I/O) | **CLOSED** | `radius/handlers.py:353–388` — `_run_phases` memuat router/run dalam unit scope pendek, KELUAR, lalu cabang rollback memanggil `_PHASE_FN[B6]` **di luar transaksi**; `radius/handlers.py:255–293` `_b6_rollback` menjalankan APPLY/VERIFY adapter tanpa transaksi terbuka, evidence+enforcement commit dalam unit pendek ter-fence terpisah (`ctx.scope()`). Probe: `authority-probes-after.log:10` → `apply/verify: in_atomic_block=false, autocommit=true` (failing-before `failing-before-probes.log:1`: keduanya `true/false`). Standar pembuktian sama dengan probe controller sendiri (introspeksi koneksi nyata pada adapter terkontrol). |
| REV-1711-08 (P1, B6 negative verifier klaim rollback berhasil) | **CLOSED** | `radius/handlers.py:272–293` — readback negatif → evidence `rollback_readback_ok=false` TERSIMPAN, `run.state=FAILED` (bukan LOCAL/ROLLED_BACK), enforcement router TIDAK ditimpa, `JobError cutover_rollback_readback_failed retryable=False` → job FAILED jujur; `radius/handlers.py:340–344` `verify()` menilai state: run FAILED → `ok:False` (`cutover_run_failed`), tidak lagi "run ada = ok". Jalur positif tetap benar; B3/B4 `pending_observation` tidak diubah/dipercepat (`radius/handlers.py:209–224`). Probe: `authority-probes-after.log:9` → `job failed, run failed, enforcement radius_authoritative, readback_ok=false`; jalur positif (`:10`) → `succeeded/rolled_back/local` tetap. |
| REV-1711-09 (P2, gap bukti acceptance) | **CLOSED** (suplemen bukti; catatan lingkup SUB-05) | Sinyal nyata SIGINT idle → exit 0 `drain selesai` (`test_jobs_drain_pa002.py:155–170`); SIGINT blocked-I/O + deadline → exit 3, `uncertain drained_mid_execute`, pulih via resolve+reclaim (`:235–261`); sinyal SAAT fase DB aktif di balik barrier (SIGTERM **dan** SIGINT, parametrized) → job diselesaikan kooperatif exit 0 SUCCEEDED items 2/2, **stop-claim assertion** job kedua tetap queued attempt 0 dan tidak muncul di log worker (`:189–233`) + handler barrier `tests/drain_handlers.py:26–52`; marker deterministik `runworker.py:80–84`. Fase panjang aktif vs reconciler serentak (LEASE_S diskalakan 1 s, 10 fase progress+sleep nyata, reconcile loop nyata) → SUCCEEDED tanpa pernah uncertain (`test_jobs_lifecycle_pa002.py:1222–1263`). Crash SETELAH commit domain → lease habis → reconcile → uncertain → resolve applied=True → verify-only TANPA efek kedua (count tetap 1) (`:1265–1312`). Current-policy/SUB-05 jalur aktif restricted/ended: operasi existing (discovery) SUCCEEDED, policy tidak diubah job, nol efek isolasi akun (`:1314–1352`). Catatan: matriks policy hanya jalur job/discovery; jalur HTTP/payment/hold tetap via applicability — sesuai opsi minimum R1 ("atau beri applicability"). |

## 2. Temuan reviewer ini (baru)

### CORR-REV-01 — P2 — klaim `no_effect` blanket pada kelas `RouterOsError` generik (latent)

**Bukti:** `backups/service.py:211–218` — klausa `except RouterOsError as exc: ...
raise JobError(code=exc.code, retryable=True, no_effect=True)`. Komentar
menyatakan hanya subkelas pra-kirim (PermissionDenied/RevisionConflict)
yang no-effect dan "kesalahan lain tetap default ditahan uncertain", tetapi
kode menandai SELURUH `RouterOsError` yang jatuh ke klausa itu (termasuk
`router_error` generik). Pada adapter api client, `router_error` generik
dapat terbit di lapisan protokol SETELAH perintah terkirim
(`apiclient.py:124` `routeros_trap`, `:102–105` `word/response_too_large`).
Hari ini TIDAK terjangkau sebagai klaim palsu: simulator `create_backup`
hanya terbit `UnreachableError` pra-kirim (`simulator.py:99–103,213–222`)
dan api client `create_backup` terbit `backup_pending_lab` pra-kirim
(`apiclient.py:316–317`) — namun bentuk ini berpotensi membuka kembali
kelas defect REV-1711-02 ketika backup nyata diimplementasikan (M3+):
`routeros_trap` pasca-send akan dianggap no-effect → auto-retry → kirim
kedua. Ini bertentangan dengan minimum R1 "retry hanya dari bukti
no-effect/safe outcome yang EKSPLISIT".

**Minimum correction (disarankan sebelum commit):** sempitkan tanda
`no_effect=True` ke subkelas terbukti pra-kirim (`UnreachableError`,
`PermissionDeniedError`, `RevisionConflictError`); biarkan `RouterOsError`
generik jatuh ke default hold uncertain engine (sesuai komentar yang sudah
ditulis). Non-blocking untuk koreksi ini karena jalur saat ini tidak
terjangkau; wajib dicatat sebagai debt yang terlihat.

### CORR-REV-02 — P2 (residual) — jendela predecessor crash-belum-reconcile pada hold router durable

**Bukti:** `engine.py:641–659` hold durable hanya memeriksa state
`uncertain`/`recovery_required`. Bila predecessor hard-crash SETELAH send
namun SEBELUM reconcile (state masih `executing`, lease masih hidup, dan
advisory lock sesi sudah lepas karena proses mati), successor dapat lolos
cek `router_unknown`, meng-acquire advisory sender, dan mengirim SEBELUM
reconcile menandai predecessor uncertain. Jendela dibatasi LEASE_S (30 s)
+ kadensi reconciler dan memerlukan crash keras pada jendela sempit; probe
controller menutup kasus uncertain-sudah-tertulis (fixed), kasus ini tidak
diuji dan tidak ditutup oleh minimum kata-kata R1 secara harfiah ("outcome
unknown" vs "state uncertain").

**Minimum correction (opsional, future hardening):** perlakukan juga job
router sama pada `executing`/`verifying` dengan lease kedaluwarsa sebagai
pemblokir (penulis mati belum teramati), atau acquire sender hanya bila
lease predecessor tidak aktif. Tidak memblokir penerimaan koreksi ini;
catat di register risiko Beta.

### CORR-REV-03 — P3 (teoretis) — guard ownership check-then-act tanpa row lock

**Bukti:** `engine.py:194–217` `assert_owned` membaca lease/epoch/state via
SELECT biasa di dalam transaksi unit. Pada READ COMMITTED masih ada
mikro-jendela antara guard TERAKHIR (post-yield) dan COMMIT unit ketika
UPDATE reconcile milik transaksi lain dapat commit lebih dulu (INSERT
domain kita tidak konflik dengan UPDATE baris jobs) → efek domain stale
ikut ter-commit. Tidak terjangkau probe (loss SEBELUM/di TENGAH unit sudah
ditutup oleh pre/post-yield guard + rollback); menutup penuh memerlukan
`select_for_update` baris job di dalam unit (perlu analisis deadlock vs
reconcile/claim). Catat sebagai residual teoretis, bukan blocker.

### CORR-REV-04 — P2 (proses penyerahan) — klaim §8 delivery melebihi state nyata working tree

**Bukti:** laporan penyerahan §1 mengisi Implementasi/Tested/Published SHA
dengan placeholder ("commit koreksi ini (lihat §8)") dan §8 menyatakan
"commit koreksi kode+tes+packet+laporan ini + rename packet `_done.md`" —
namun `git status` menunjukkan koreksi MASIH uncommitted (12 file modified
+ 3 path report untracked), `task/0020-job-lifecycle-authority_done.md` BELUM
di-rename, belum ada commit/branch push/PR/CI pada tree koreksi. Bukti
probe/suite executor dijalankan pada working tree ini (konsisten dengan
isi diff), tetapi "tested SHA = published SHA" belum dapat diverifikasi
karena SHA belum ada.

**Minimum correction:** executor harus menyelesaikan langkah publikasi yang
dijanjikan (commit tunggal kode+tes+packet+laporan, rename packet, isi SHA
aktual, push branch kandidat + PR + CI pada SHA exact) SEBELUM controller
re-review, sesuai kontrak penyerahan R1 §7. Controller re-review harus
menunggu SHA exact tersebut; laporan ini hanya memverifikasi diff yang ada.

### CORR-REV-05 — P3 (catatan, bukan defect) — dua perilaku kecil pada `_retry_no_effect`

**Bukti:** `engine.py:879–893` — step-2 filter tanpa `lease_epoch`; bila
ops menjalankan `resolve_uncertain` di antara step-1/step-2, update
mengembalikan 0 baris → `OwnershipLost` dan job tertinggal di `uncertain`
dengan `error_code` terpasang (fail-safe: tidak ada efek ganda, tidak ada
state tidak-sah — tetap jalur recovery). `on_retry` dipanggil dengan ctx
job `retry_wait` (handler existing no-op). Diterima apa adanya; disarankan
 komentar saja. Tidak perlu koreksi.

## 3. Pemeriksaan pelemahan assertion/kontrol (apa yang dibandingkan)

1. **`test_heartbeat_progress_report_ownership_loss`**
   (`test_jobs_lifecycle_pa002.py:265–291`): lama `assert ctx.heartbeat() is
   False` / `assert ctx.progress(...) is False` → baru `pytest.raises(engine.
   OwnershipLost)` untuk keduanya. Ini **PENGUATAN, bukan pelemahan**:
   return False bisa diabaikan pemanggil (justru inti REV-1711-01),
   exception TIDAK bisa diabaikan tanpa `try` eksplisit; `ctx.lost is True`
   dan raise pada `ctx.scope()` tetap dipertahankan. Seluruh pemanggil
   produksi `heartbeat/progress` memanggil tanpa memeriksa return →
   semantik raise aman dan mempersempit jalur bypass.
2. **`test_jobs_engine.py:36–44` `_RetryableHandler`:** hanya menambah
   `no_effect=True` pada JobError yang dilempar handler uji pra-efek;
   SEMUA assertion `test_job_retry_then_backoff` tidak berubah
   (retry_wait, attempt==1, backoff masa depan, tidak reclaimable) —
   adaptasi jujur terhadap kebijakan baru, bukan pelemahan.
3. **Tes drain:** `test_sigterm_idle_exits_drained` assertion lama
   dipertahankan + diperkuat marker kesiapan; `test_sigterm_completes_
   cooperative_db_job`, `test_drain_deadline_on_blocked_io_holds_job_
   honestly`, `test_sigkill_then_reconcile_recovers` tidak diubah. Tes baru
   menambah assertion kuat (exit code eksplisit 0/3, SUCCEEDED items 2/2,
   queued attempt 0, kontainment log `str(second.id) not in out`).
   **Tidak ada assertion yang dihapus di seluruh diff** (dibaca penuh).
4. **RLS/tenant scope:** tidak ada perubahan migrasi/policy/permission;
   `makemigrations` = "No changes detected"; evidence split-role
   (`split-roles-rls.log`): 59 tabel milik `mtx_migrator`, FORCE RLS
   aktif, runtime `mtx_app` NOSUPERUSER/NOBYPASSRLS. `views.py` hanya
   MENAMBAH guard scope (404 sebelum 403/step-up) — tidak membuka bypass.
5. **Tabel state §6:** `_finish_execute_failure` tidak pernah menulis
   `retry_wait` dari `executing`; satu-satunya jalur baru
   executing→retry_wait adalah komposisi dua-langkah via uncertain
   (`models.py:93–103` keduanya edge sah). `PREFLIGHT→RETRY_WAIT` (hold
   router/drain pra-efek) edge yang sudah sah. `_hold_for_drain`
   mid-effect tetap → uncertain. Terminal tetap immutable.
6. **Blind retry:** jalur executing kini hold-uncertain default; retry
   hanya dengan `no_effect` eksplisit atau pra-efek (claimed/preflight).
   Probe `backup-generic-after-send` membuktikan tidak reclaimable.
7. **Kontrol keamanan lain:** tidak ada file settings/CI/dependency/
   installer yang berubah; hanya 12 file backend yang diperkirakan.

## 4. Yang dijalankan sendiri vs yang hanya dibaca (read-only distinction)

**Dijalankan reviewer (read-only, tidak menulis ke repo):**
- `git status`/`git diff`(penuh, per area)/`git log` pada repo.
- Pembacaan seluruh file terkait (engine.py, views.py, handlers
  network/radius/backups/customers, services, runworker, models.py,
  tenant_context.py, tes drain/lifecycle/engine, probe controller).
- `pg_isready` (server uji hidup) dan **SATU kali** targeted suite:
  `cd backend && TEST_DATABASE_URL="postgresql://mtx_app@127.0.0.1:55432/
  microtix" .venv/bin/python -m pytest tests/integration/
  test_jobs_lifecycle_pa002.py tests/integration/test_jobs_engine.py -q
  --reuse-db` → **52 passed in 19.72s** (konsisten dengan klaim targeted
  executor 60 = 52 + 8 tes drain).

**HANYA DIBACA (bukan hasil run reviewer):** seluruh log evidence executor
(failing-before 11 failed; passing-after 11 passed; lifecycle/authority
probes-after JSON; split-migrate/grant/rls; full-suite 562 passed/1 skipped;
targeted pa001/pa006/rls/jobs; check; makemigrations; docs PASS 24 file),
script `run_correction_probes.sh`, laporan penyerahan, dan laporan
controller R1. **Reviewer TIDAK menjalankan ulang probe PostgreSQL
controller, full suite, tes drain proses, split-role setup, atau CI** —
semua angka probe di matriks §1 adalah kutipan evidence executor yang
dibaca, bukan klaim eksekusi reviewer. Probe yang dipakai executor adalah
file probe controller asli (path controller-evidence, tidak berubah pada
working tree) — metode repro yang sahih.

## 5. Kesimpulan dan rekomendasi untuk controller

1. **REV-1711-01–08: tertutup pada source dengan desain minimal pada stack
   existing** (tanpa migrasi/framework baru), dan reproduksi memakai file
   probe controller asli menunjukkan 11/11 pass pada tree koreksi
   (failing-before 11/11 fail pada bd37c14 — konsisten dengan R1 root).
   **REV-1711-09: suplemen bukti memadai** (SIGINT, sinyal saat fase aktif
   + stop-claim, fase panjang vs reconciler, crash pasca-commit, policy
   jalur aktif) dengan catatan lingkup SUB-05 HTTP-path via applicability.
2. **Tidak ditemukan pelemahan assertion, bypass RLS/tenant scope, kontrol
   keamanan yang dimatikan, atau pelanggaran tabel state** pada diff.
3. **Risiko tersisa yang harus dibawa controller ke re-review:**
   - CORR-REV-01 (P2, latent): sempitkan `no_effect` blanket RouterOsError
     generik di backups (disarankan diperbaiki sebelum commit; kecil).
   - CORR-REV-04 (P2, proses): commit/rename/SHA/push/PR/CI penyerahan
     belum dilakukan — controller TIDAK dapat mereview "exact SHA koreksi"
     sebelum executor menyelesaikan publikasi; SHA §1 masih placeholder.
   - CORR-REV-02 (P2 residual) dan CORR-REV-03 (P3 teoretis): jendela
     sempit hard-crash pra-reconcile dan check-then-commit tanpa row lock —
     catat di register risiko, tidak memblokir.
4. **Rekomendasi:** controller **menerima koreksi ini untuk re-review**
   (changes_requested pada 8 defect dianggap terjawab pada diff), dengan
   syarat: (a) executor menyelesaikan publikasi exact-SHA+CI (CORR-REV-04)
   dan sebaiknya menutup CORR-REV-01 sebelum commit; (b) controller
   menjalankan ulang probe-nya pada SHA exact tersebut; (c) risiko
   CORR-REV-02/03 dicatat sebagai residual register Beta, bukan pembuka
   ulang ID0020. Acceptance/merge/deploy tetap keputusan controller
   terpisah; reviewer ini tidak mengklaim acceptance.
