# Eksekusi koreksi task0020 — tutup REV-1711-01–09 pada ID yang sama

## 1. Identifikasi dan baseline

| Field | Nilai |
|---|---|
| Task ID / packet | **0020** [PA-002+PA-003](../../task/0020-job-lifecycle-authority.md) — koreksi `changes_requested` R1, ID sama, bukan task baru |
| Peran | coding agent (executor) Z.ai sandbox |
| Instruction ref | [PR29](https://github.com/smahud/MicroTix_Project/pull/29) `review/0020-controller-20261117` — fetched sampai `0e45157` (checkpoint resume 21:48 WIB); keputusan acceptance tetap [controller R1 §3](../controller/20261117T134100Z-0020-job-lifecycle-review.md) |
| Baseline canonical main | `41d1f33f16508491a34f66b767830b9dd3e5954e` — tidak berubah saat sesi; delta dicek ulang sebelum kerja |
| Source kandidat yang dikoreksi | PR27 `bd37c14` (impl ancestor `7118cce`) dibawa oleh decision ref; branch kerja `session/2026-11-17-0020-job-lifecycle-correction` dari `0e45157` |
| Implementasi | commit koreksi ini (lihat §8; kode+tes satu commit) |
| Tested SHA | SHA commit koreksi (suite penuh + probe dijalankan pada tree persis ini) |
| Published candidate | branch di atas + PR (lihat §8) |
| Acceptance owner | controller — laporan ini adalah penyerahan koreksi, bukan acceptance |

## 2. Ringkasan hasil

Seluruh **REV-1711-01–09** ditutup dengan perubahan minimum pada stack
existing (engine jobs, handler network/radius/backups/customers, views job,
runworker; tanpa migrasi schema baru, tanpa framework/layanan baru).
Reproduksi probe controller R1 (kedua file, 11 assertion):

- **Failing-before** pada source kandidat bd37c14: **11 failed**
  ([log](../executor-evidence/20261117T150000Z-0020-correction/failing-before-probes.log)).
- **Passing-after** pada tree koreksi: **11 passed**
  ([log](../executor-evidence/20261117T150000Z-0020-correction/passing-after-probes.log));
  diulang pada DB split-role (schema milik migrator, runtime `mtx_app`
  NOSUPERUSER/NOBYPASSRLS, 59 tabel FORCE RLS): **exit 0 semua**
  ([exit codes](../executor-evidence/20261117T150000Z-0020-correction/exit-codes.txt)).
- Regresi penuh: **562 passed, 1 skipped, 3 warnings** (suite backend penuh,
  PG 17.12 nyata; +8 tes baru REV-1711-09/penutup). PA-001 33 passed;
  PA-006 R1–R5 125 passed; RLS 8 passed; jobs targeted 60 passed.

## 3. Inventaris ringkas (prasyarat packet)

Active kind saat ini dan asal enqueue: `verify_api_ssl`+`discover_router`
+`router_release`/`router_replace` (network), `radius_cutover_step`
(radius), `backup_router` (backups), `import_commit`/`commit_migration`/
`harvest_passwords` (customers; harvest fail-closed lab_required),
`_test_*` (uji). Peta izin `KIND_PERMISSION_FALLBACK` tetap fail-closed
untuk kind produksi tanpa peta. Effect boundary: DB-only (release/replace/
import/cutover fase B0/B1/B3/B4) vs adapter I/O (discovery list_accounts/
read_health, backup create_backup, cutover B2/B5/B6 APPLY/VERIFY). Verifier
per kind tetap typed; `verify_api_ssl` actorless → provenance
enrollment.created_by + karantina authority_unresolved (dipertahankan dari
penyerahan pertama; tidak dibuka ulang).

## 4. Temuan → perubahan → bukti (REV-1711-01–09)

### REV-1711-01 P1 — stale worker commit domain setelah reconcile

Perubahan ([engine.py](../../../backend/domains/jobs/engine.py)):
`JobContext.scope()` kini menjalankan **guard ownership DI DALAM transaksi
unit** (entry + sebelum commit) via `assert_owned()` — baca segar
lease_token+epoch+state; kehilangan kepemilikan membatalkan unit domain
SEBELUM commit (atomic cek+commit). `heartbeat()`/`progress()` kini
**melempar OwnershipLost** saat CAS gagal (bukan return False yang dapat
diabaikan pemanggil — backup tidak lagi melanjutkan kirim adapter setelah
progress gagal). Guard diteruskan ke unit milik service:
`run_discovery(..., ownership_guard=ctx.assert_owned)` (snapshot,
objek, health, cleanup unit) dan `finalize_verification(...,
ownership_guard=...)` (commit router/peer/enrollment).

Bukti: probe `stale-discovery-domain-commit` — setelah reconcile:
**object_count=0, health_count=0, snapshot tidak succeeded** (failing-before
succeeded+objek+health). Tes unit `_DomainCommitHandler` + drain SIGKILL
tetap recovery-durable.

### REV-1711-02 P1 — error setelah efek backup membuka retry otomatis

Perubahan: `JobError.no_effect` (bukti eksplisit pra-efek). Kegagalan
generic pada tahap executing → **default uncertain** (`internal_error`,
tahan; readback ops). `retryable` tanpa bukti no-effect → uncertain.
Retry otomatis dari executing HANYA via `no_effect=True` melalui
**komposisi transisi sah tabel §6**: executing→uncertain (teramati jujur)
lalu uncertain→retry_wait dengan bukti "belum diterapkan" = deklarasi
handler (backoff/attempt kebijakan lama; `on_retry` tetap). Handler
menandai no_effect pada kegagalan terbukti pra-efek: probe baca-saja
`api_ssl_unreachable`, `router_unreachable`/RouterOsError pra-kirim
backup (Unreachable = tidak pernah terkirim; PermissionDenied/
RevisionConflict = ditolak sebelum diterapkan), `dependency_unavailable`
konversi ApiError (transaksi domain rollback bersih).

Bukti: probe `backup-generic-after-send` — **first_state=uncertain,
send_count=1, reclaimed=false** (failing-before: retry_wait, send kedua,
artifact kedua). `test_job_retry_then_backoff`/re-entry VERIFYING api_ssl
tetap lulus (no_effect eksplisit).

### REV-1711-03 P1 — retry ancestor melewati descendant uncertain

Perubahan: `retry_job` menghitung lineage root (`_lineage_root_id`) dan
**mengunci baris akar** (serialisasi retry serentak origin/child pada
lineage sama), lalu `_lineage_active_exists` BFS turun seluruh
descendant — kandidat aktif nonterminal manapun (uncertain/recovery/
aktif) menolak retry. Retry atas terminal dengan outcome final tetap sah.

Bukti: probe `retry-uncertain-grandchild` — **extra_retry_created=false,
error=retry_active_exists, send_count=1** (failing-before: sibling baru
dikirim saat grandchild uncertain).

### REV-1711-04 P1 — pemilik router berikutnya mengirim sebelum readback unknown

Perubahan: sebelum acquire advisory sender, engine memeriksa **hold
durable** — job router sama pada state `uncertain`/`recovery_required`
(id berbeda) menahan mutasi router berkonflik ke `retry_wait`
`router_outcome_unknown` (attempt tidak dikonsumsi) sampai old
writer/readback membuktikan kelanjutan aman; router lain tetap maju.
Advisory lock sesi tetap untuk penulis hidup; resolve_uncertain(applied=
False) tetap menolak selama penulis lama aktif.

Bukti: probe `router-unknown-predecessor` — **second_state=retry_wait,
send_count=1** (failing-before: successor langsung mengirim). Tes
existing `same-router-single-sender` dan `resolve_not_applied_refused_
while_old_writer_active` tetap lulus.

### REV-1711-05 P1 — revoke/demote setelah preflight tetap melepas router

Perubahan: engine menjalankan `check_current_authority` **pada batas efek
SETELAH preflight dan sebelum kirim** (selain cek awal sebelum preflight)
— revoke/demote/scope-narrowing di jendela preflight → `authority_denied`,
nol release/peer/NAS/send. Per-chunk B2/B5 `ctx.recheck_authority()`
dipertahankan.

Bukti: probe `after_preflight_revoke`/`demote` — **state=failed,
error_code=authority_denied, router_released=false**, koneksi DB worker ≠
controller terbukti (pid berbeda) (failing-before: dua kasus succeeded,
router terlepas).

### REV-1711-06 P1 — endpoint job mengabaikan router scope membership

Perubahan: `_require_job_authority` (jobs/views.py) memeriksa
**membership.router_scope** untuk job ber-router di jalur
detail/retry/cancel: non-scope → **404 generik** sebelum aksi (nol
perubahan state/job/nol job baru); in-scope tanpa izin tetap 403;
step-up sensitif tetap; milik tenant tanpa scope membatasi (scope=None)
tidak terdampak. List exposure tetap mengikuti izin baca existing
(customers.read) tanpa perluasan privilege.

Bukti: probe `http_scope_{detail,cancel,retry}` — **404,
job_state_before==after, job_count_before==after** (failing-before:
GET 200 / cancel 204 / retry 202 dengan job kedua dibuat).

### REV-1711-07 P2 — B6 rollback menahan transaksi saat adapter I/O

Perubahan (radius/handlers.py): cabang rollback keluar dari unit
`ctx.scope()` luar — `_run_phases` memuat router/run dalam unit pendek,
keluar, lalu memanggil `_PHASE_FN[B6]` **tanpa transaksi terbuka**;
APPLY/VERIFY adapter berjalan autocommit; evidence+enforcement di-commit
dalam unit pendek ter-fence terpisah.

Bukti: probe `b6_transaction_boundary` — APPLY dan VERIFY
**in_atomic_block=false, autocommit=true** (failing-before: keduanya
di dalam transaksi terbuka).

### REV-1711-08 P1 — B6 negative verifier mengklaim rollback berhasil

Perubahan: `_b6_rollback` menyimpan evidence readback jujur; readback
negatif → **run FAILED** (bukan LOCAL/ROLLED_BACK), enforcement router
tidak ditimpa, job FAILED `cutover_rollback_readback_failed`. `verify()`
kini menilai state: run FAILED → `ok:False` (tidak sekadar "run ada");
AUTHORITATIVE/PENDING_OBSERVATION/ROLLED_BACK tetap hasil sah (B3/B4
pending tidak dipercepat/diubah jadi device-complete).

Bukti: probe `b6_negative_verifier` — **job failed, run failed,
enforcement tetap radius_authoritative, readback_ok=false tersimpan**
(failing-before: succeeded/rolled_back/local). Probe transaksi (verified
true) tetap job succeeded + run rolled_back + router local — positive
rollback tetap benar.

### REV-1711-09 P2 — bukti acceptance wajib dilengkapi (bukan defect kode)

Tes baru (drain + lifecycle):
- **SIGINT nyata**: idle → exit 0 `drain selesai`; blocked I/O + deadline
  → exit 3, job uncertain `drained_mid_execute`, pulih via resolve+reclaim.
- **Sinyal SAAT fase DB aktif (barrier)** SIGTERM **dan** SIGINT: job
  diselesaikan kooperatif (exit 0, SUCCEEDED, items 2/2) — bukan ditahan;
  **stop-claim assertion**: job kedua yang antri tetap queued attempt 0
  dan tidak muncul di log worker.
- **Fase panjang aktif vs reconciler serentak** (LEASE_S diskalakan 1 s,
  10 fase progress+sleep nyata): worker tidak pernah uncertain, hasil
  SUCCEEDED — renewal per fase terbukti terhadap reconcile nyata (mapping
  LEASE30s/backup1800s berskala).
- **Crash SETELAH commit domain** (handler domain-commit nyata +
  verify-gate): lease habis → reconcile → uncertain; resolve applied=True →
  verify-only SUCCEEDED **tanpa efek domain kedua** (count tetap 1).
- **Current-policy/SUB-05 jalur aktif**: subscription `restricted` dan
  `ended` — operasi existing (discovery) tetap SUCCEEDED, policy tidak
  diubah job, nol efek isolasi akun diperkenalkan jalur job (tidak
  membangun auto-isolir R2).
- Marker kesiapan `worker siap` (flush) pada runworker membuat uji proses
  deterministik (sinyal tidak lagi bertabrakan dengan pemasangan handler).

## 5. Matriks acceptance → hasil aktual → evidence

| ID | Hasil | Evidence aktual |
|---|---|---|
| J20-A01 | **PASS (koreksi)** | Guard ownership dalam transaksi unit domain + heartbeat/progress melempar; probe stale-discovery 0 objek/0 health/snapshot-running; suite fencing 41 tes lulus |
| J20-A02 | **PASS (koreksi)** | B6 APPLY/VERIFY autocommit (probe boundary); unit domain ter-fence; `test_no_db_transaction_across_blocked_io` tetap (observer idle+no txnid lock); RLS 8 lulus split-role FORCE |
| J20-A03 | **PASS (koreksi)** | Durable hold router unknown (probe second retry_wait, 1 send); single-sender lain-router tetap; cancel pra-efek atomic tetap; resolve writer-active tetap |
| J20-A04 | **PASS (koreksi)** | Generic-after-effect → uncertain (probe backup 1 send, tidak reclaimable); lineage retry penuh (grandchild); applied=True verify tanpa resend; unknown tetap tertahan |
| J20-A05 | **PASS (bukti dilengkapi)** | Long-phase vs reconciler serentak SUCCEEDED; crash setelah commit domain → uncertain → resolve applied → nol efek kedua; reconcile renew-aware tetap; B3/B4 window tidak berubah |
| J20-A06 | **PASS (koreksi+policy)** | after-preflight revoke/demote → authority_denied nol release (probe); per-chunk B2/B5 tetap; SUB-05 restricted/ended: operasi existing tetap sah, nol isolasi akun, policy tidak diubah |
| J20-A07 | **PASS (koreksi)** | HTTP scope 404 tiga aksi (probe, state/job tidak berubah); B6 negative verifier honest; positive rollback tetap benar; permission/step-up/403/404 tetap; missing handler fail-closed tetap |
| J20-A08 | **PASS (bukti dilengkapi)** | SIGTERM+SIGINT idle/active-barrier/blocked-I/O nyata; stop-claim assertion; exit 0/3 dibedakan; SIGKILL+reconcile recovery tetap; runbook urutan stop-claims→drain→reconcile/readback→resume tetap |
| J20-A09 | **PASS (regresi)** | Suite penuh 562/1 skip; PA-001 33; PA-006 125 (R1–R5 replay); makemigrations No changes; check 0 issue; docs PASS; P3 thread assertion tetap |

## 6. Kompatibilitas, migrasi, recovery

Tanpa migrasi schema (jobs.0004/0005 tak tersentuh). Kebijakan drain/
compatibility lama dipertahankan; payload lama tetap sah; karantina
actorless + resume tetap. Perubahan perilaku yang disengaja (dan diuji
ulang): retry otomatis dari executing kini hanya dengan bukti no_effect
eksplisit — kegagalan tanpa bukti ditahan uncertain untuk readback ops
(jalur pemulihan: resolve not-applied setelah penulis aman → klaim ulang).
Terminal immutable tetap; state table §6 dihormati pada semua jalur baru.

## 7. Batas dan NOT_RUN

Sandbox engine/PG/proses nyata saja: RouterOS/CHR/GNS3 nyata, readback
perangkat, systemd/produksi drain, OS install/upgrade/restore/DR,
browser E2E, benchmark/scale/soak NOT_RUN. CI frontend pada kandidat
menjalankan tsc/eslint/vitest/i18n/build pada tree apps/ yang tidak
berubah dari bd37c14 (delta apps/ kosong). Simulator/controlled adapter
membuktikan engine, bukan perangkat nyata. Beta tetap NOT_READY; bloker
register 11 Nov (installer/upgrade/worker ops/restore/secret/scheduler/
DEC-01/02/host/lab/kapasitas) tidak tersentuh sesi ini.

## 8. Penyerahan

- Branch: `session/2026-11-17-0020-job-lifecycle-correction` (dari
  decision ref `0e45157`), commit koreksi kode+tes+packet+laporan ini +
  rename packet `_done.md`; implementation/tested/published SHA:
  **`2681a3d090710c3855e66cfecc77b8af80fb1098`** (suite penuh + probe
  dijalankan pada tree persis ini; record SHA di atas ditulis setelah
  commit tersebut ada — descendant metadata-only, kode tidak berubah).
- Evidence root: [executor-evidence/20261117T150000Z-0020-correction/](../executor-evidence/20261117T150000Z-0020-correction/)
  (failing-before/passing-after probe, split-role migrate/grant/RLS,
  check, makemigrations, docs, full-suite 562, targeted subsets,
  environment).
- Reviewer independen: [report reviewer sesi ini](../reviewer/20261117T160500Z-0020-correction-independent.md)
  (read-only; laporan terpisah). Verdict reviewer: **REV-1711-01–09 CLOSED**,
  nol pelemahan assertion/kontrol. Temuan baru reviewer ditindaklanjuti
  sebelum commit: **CORR-REV-01** (P2) — `no_effect` blanket pada
  RouterOsError generik backup DISEMPITKAN ke subkelas terbukti pra-kirim
  (Unreachable/PermissionDenied/RevisionConflict); RouterOsError generik
  kini default ditahan uncertain (bisa terbit pasca-kirim pada trap
  protokol). **CORR-REV-02** (P2) — jendela penulis hard-crash pasca-kirim
  SEBELUM reconcile ditutup: hold durable router kini juga memblokir job
  router sama pada executing/verifying dengan lease kedaluwarsa (job hidup
  lease-aktif tetap dibedakan advisory lock). Suite penuh + probe diulang
  setelah kedua penutupan (562 passed; 11 probe passed).
- Next actor: **controller_reviewer** — review exact SHA koreksi atas
  REV-1711-01–09 dan matriks §5, jalankan ulang probe yang relevan,
  delta main/candidate+CI; changes-requested membuka kembali ID0020 yang
  sama. Tidak ada task0030 sebelum prasyarat terpenuhi.

## 9. Catatan infrastruktur uji (kejujuran bukti)

Suite penuh dijalankan ulang pada **test DB SEGAR** (tanpa --reuse-db)
setelah ditemukannya flake `test_quota_reservation_atomic` pada test DB
yang dipakai ulang: akar masalah adalah **kontaminasi lintas sesi pytest**
— file probe (available_apps memuat `domains.subscriptions`) menjalankan
flush/TRUNCATE tabel subs_* termasuk `subs_plan_version`, lalu sesi suite
berikutnya `ensure_free_subscription` membuat fallback plan FREE
`routers_limit=NULL` pada konteks transactional-test yang tidak diflush —
plan tanpa limit menetap di DB reuse → klaim kuota tidak terpicu. Bukan
defect produk (kode subs/quota tak tersentuh diff); controller R1 memakai
DB disposable terpisah untuk probe dengan alasan yang sama. Hasil kanonik
CI-paritas: **562 passed/1 skipped/3 warnings pada fresh DB**
([full-suite-fresh-db.log](../executor-evidence/20261117T150000Z-0020-correction/full-suite-fresh-db.log)).
CI GitHub selalu DB segar per run — tidak terdampak.
