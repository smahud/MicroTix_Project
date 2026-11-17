# Laporan eksekusi task0020 — PA-002 + PA-003: job aman terhadap stale worker dan perubahan kewenangan

- **Executor:** coding agent Z.ai (sandbox), sesi `session/2026-11-17-0020-job-lifecycle-authority`
- **Task:** [0020](../../task/0020-job-lifecycle-authority_done.md) — execution `done`, review `pending`
- **Instruction ref:** `review/0020-job-lifecycle-authority-20261117` @ `ea7b8a1` (PR26; packet + laporan controller/reviewer di-baca dari ref tersebut)
- **Baseline kode:** `main@41d1f33f16508491a34f66b767830b9dd3e5954e` (delta terhadap main saat mulai: kosong — verifikasi `git diff 41d1f33..ea7b8a1 --stat` hanya docs/report)
- **Implementation/tested SHA:** `7118cce0db330acb02be0b3b774b1b1628d55d7a` = engine `6e96ce33` + perbaikan test-infra (password DB URL untuk subprocess drain di CI; tanpa perubahan engine/handler). Commit laporan ini adalah descendant report-only
- **Lingkungan:** PostgreSQL 17.11 nyata, peran runtime `mtx_app` NOSUPERUSER NOBYPASSRLS CREATEDB (FORCE RLS via migrasi), Python 3.13.5, Django 5.2.19, psycopg 3.2.13, pytest 8.4.2 ([environment.txt](../executor-evidence/20261117T000000Z-0020-job-lifecycle/environment.txt)). Host/lab/GNS3 tidak tersedia — tidak ada klaim perangkat nyata.

## 1. Inventaris kind aktif (prasyarat packet, sebelum edit)

| Kind | Asal enqueue | Izin origin | Provenance aktor | Batas efek | Verifier | Deadline/heartbeat/retry |
|---|---|---|---|---|---|---|
| `import_commit` | customers/views ImportCommitView | imports.run | request.user (view) | DB-only (commit_csv) | status CsvImport committed | tanpa deadline_s; backoff 2^n·5s cap 300s; max 5 attempt |
| `commit_migration` | customers/views MigrationCommitView | migration.run | request.user (view) | DB-only (Tahap A) | status MigrationSession committed | idem |
| `harvest_passwords` | customers/views PasswordHarvestView | migration.run | request.user (view) | preflight gagal lab_required (jujur) | — | idem |
| `discover_router` | network/views DiscoveryStartView; customers/services.start_migration | routers.enroll; migration.run | request.user / actor start_migration | adapter list_accounts+read_health (I/O) + snapshot/objek (DB) | snapshot status succeeded | idem |
| `verify_api_ssl` | network/services.bootstrap_complete (bridge perangkat, tanpa sesi) | routers.enroll (provenance enrollment) | **dulu actorless** → kini enrollment.created_by | probe TCP/TLS (I/O jalur api_ssl) + Router/peer (DB) | router+peer applied | retry bounded api_ssl_unreachable |
| `router_release` | network/views RouterReleaseView | routers.release | request.user (view) | DB-only (released_at, peer, NAS) | released_at | idem |
| `router_replace` | network/views RouterReplaceView | **dulu routers.enroll (salah)** → kini routers.release (ARCHITECTURE §5) | request.user (view) | DB-only (release + enrollment baru) | released_at | idem |
| `backup_router` | backups/views RunBackupView | backups.run | request.user (view) | DB (artifact) + file manifest + adapter create_backup (I/O) | manifest fisik + size + commit katalog | deadline_s=backup.job_deadline_s (1800) |
| `radius_cutover_step` | radius/views RadiusCutoverView (sensitif, step-up) | radius.cutover | request.user (view) | B0/B1/B3/B4 DB; B2/B5/B6 APPLY/VERIFY adapter (I/O) | state run + evidence per fase | TANPA deadline_s — jendela observasi B3 1800s/B4 86400s dipertahankan |

Kind lain pada JOB_KINDS tidak punya handler (create_job menolak) → fail-closed
pra-enqueue. Kind uji `_test*` tanpa syarat izin (bukan operasi produksi).

## 2. Solusi minimum dan alasan

1. **Engine CAS penuh (A01):** semua tulisan worker (transisi, terminal/error,
   retry, heartbeat, progress, result) via `_fenced_update`/`JobContext._fenced`
   yang memfilter `id + lease_token + lease_epoch + expected_state` (dan
   mengecualikan terminal). Kehilangan kepemilikan → `OwnershipLost` → worker
   berhenti tanpa menulis; commit hasil terminal adalah CAS di klausa WHERE
   (bukan read-then-write). Tanpa framework baru; PostgreSQL existing.
2. **Transaksi pendek per unit (A02):** `run_claimed` tidak lagi membungkus
   seluruh preflight/execute/verify dalam satu `tenant_scope`. Handler memakai
   `ctx.scope()` (transaksi tenant pendek) per unit DB; I/O adapter/probe/file
   di luar unit. `progress()`/`heartbeat()` commit pendek sendiri (terlihat
   observer). Handler network/radius/backups/customers direstrukturisasi
   (PLAN murni boleh dalam unit; APPLY/VERIFY di luar).
3. **Cancel + penulis eksternal (A03):** `effect_state=maybe` ditulis ATOMIK
   dengan entering EXECUTING → cancel hanya sah pada state pra-efek via CAS
   yang sekaligus menaikkan epoch (fence worker); executing/verifying jujur
   ditolak (409). Satu pemilik pengirim per router via `pg_try_advisory_lock`
   (session-level; dua worker/job router sama tidak mengirim bersamaan; router
   lain mandiri; koneksi mati melepas otomatis; job busy kembali ke antrian
   tanpa mengonsumsi attempt). Lease/epoch DB tidak diklaim menarik command
   RouterOS (eksplisit di docstring).
4. **Uncertain/retry (A04):** uncertain tidak retry-able langsung (API 409,
   engine menolak); `resolve_uncertain`: False → retry_wait + fence epoch +
   (job router) wajib penulis lama terbukti berhenti (advisory lock bebas)
   sebelum requeue; True → verify TANPA resend (`_verify_only`); None →
   recovery_required tertahan. Retry serentak diserialisasi (row-lock origin)
   dan ditolak bila ada kandidat aktif — termasuk uncertain/recovery_required
   (REV-2011-01). `request_id` asal dipertahankan (identitas idempotensi).
5. **Crash/reconcile/deadline (A05):** reconcile kini state/effect-aware:
   claimed/preflight kadaluarsa → retry_wait (via jalur tabel) atau failed
   bila attempt habis; executing/verifying → uncertain; CAS memfilter
   state+token+masa lease teramati (tidak menimpa heartbeat renewed, hasil
   selesai, cancel bersamaan); dapat diulang. Deadline diperiksa saat claim
   (queued lewat deadline → failed tanpa kirim) dan sebelum efek (dibaca segar
   dari DB); B3/B4 tanpa deadline 60s (cutover tanpa deadline_s — jendela
   observasi dipertahankan). `progress()` kini memperpanjang lease (renewal
   pekerjaan panjang; REV-2011-04).
6. **Kewenangan terkini (A06):** `check_current_authority` dari DB segar
   sebelum efek: aktor aktif + membership tidak dicabut + izin operasi
   (peta kind; discover_router any-of dua asal sah) + router milik tenant
   (RLS) + router_scope membership. Aktor non-aktif/dicabut/demosi → gagal
   authority_denied tanpa efek. Actorless produksi → karantina FAILED
   `authority_unresolved` retryable (resume = retry dengan provenance; bukan
   privilege sistem). `verify_api_ssl` menurunkan provenance dari
   `enrollment.created_by` (enqueue bridge kini menyimpan aktor tersebut).
   Worker tidak memeriksa sesi/reauth HTTP (menutup browser tidak membatalkan
   pekerjaan sah). Fase kirim cutover B2/B5 memeriksa ulang kewenangan
   (`ctx.recheck_authority()`, REV-2011-07). SUB-05 tidak dilanggar: tidak
   ada blokir operasi layanan berdasarkan status subscription pada jalur ini.
7. **HTTP authority + verifier (A07):** detail/retry/cancel job memakai izin
   operasi yang mendasari (peta kind): member tanpa izin → 403; luar scope →
   404 generik; mutasi kind sensitif (radius.cutover) → step-up reauth.
   `RouterReplaceView` → `routers.release` (selaras ARCHITECTURE §5 dan mock
   frontend yang sudah memakai routers.release). Handler hilang → FAILED
   `handler_missing` (fail-closed); verifier `ok:False` → FAILED
   `verification_failed`; pending_observation B3/B4 tetap succeeded tanpa
   klaim mutasi perangkat selesai.
8. **Drain proses (A08):** `runworker` memasang SIGTERM/SIGINT → stop klaim
   baru segera (sleep dibangunkan via Event), `--drain-timeout` (default 60)
   memasang alarm HANYA saat job aktif; job aktif diselesaikan atau ditahan
   jujur (uncertain `drained_mid_*` / retry_wait `drained_before_effect`);
   exit 0 (drained) vs 3 (deadline terlampaui/incomplete) dibedakan;
   SIGKILL → reconcile → resolve → tuntas. Uji dengan SUBPROSES NYATA + sinyal
   nyata. Runbook di §7.
9. **Kompabilitas (A09):** TANPA migrasi schema (peta izin per-kind di kode —
   `manage.py makemigrations --check` bersih; tidak menyentuh jobs/0004/0005
   sehingga tes replay migrasi PA-006 R4/R5 tak terganggu). Payload/state
   lama: job actorless dikarantina dengan alasan + resume (teruji). P3
   REV-1611-TEST-01 ditutup test-only di test_idempotency_pa006_r5.py (assert
   kedua thread selesai + kedua hasil ada; PA-006 tidak dibuka).

## 3. Temuan → perubahan → failing-before/passing-after

Tes baru: `backend/tests/integration/test_jobs_lifecycle_pa002.py` (37 tes),
`backend/tests/integration/test_jobs_drain_pa002.py` (4 tes proses nyata),
helper `backend/tests/drain_handlers.py` + `backend/tests/drain_worker.py`.
**Failing-before** (file tes final dijalankan pada baseline main@41d1f33 —
worktree disposable, tidak di-push): **33/37 lifecycle GAGAL + 4/4 drain
GAGAL** ([lifecycle](../executor-evidence/20261117T000000Z-0020-job-lifecycle/failing-before-lifecycle.log),
[drain](../executor-evidence/20261117T000000Z-0020-job-lifecycle/failing-before-drain.log));
4 tes lifecycle yang lulus di baseline menguji perilaku yang memang sudah benar
(cancel queued/retry_wait, immutability ValueError, klaim dasar). Passing-after
pada kandidat: 41/41.

| Defect (sumber) | Perubahan | Bukti failing→passing |
|---|---|---|
| Tulisan worker unfenced menimpa state/hasil (JS-0020-02) | CAS token+epoch+expected-state di semua jalur; OwnershipLost | `TestOwnershipFencing` (4 tes) |
| Transaksi engine melintasi I/O handler (JS-0020-01) | unit `ctx.scope()` pendek; I/O di luar | `test_no_db_transaction_across_blocked_io` (pg_stat_activity idle + nol lock transaksi saat I/O terblokir; state executing+maybe terkomit terlihat observer) |
| False cancel saat kirim outstanding (JS-0020-03) | effect_state=maybe atomik pra-execute; cancel CAS + epoch bump; executing ditolak | `TestExternalWriterAndCancel` |
| Dua pengirim router sama (JS-0020-06) | pg_try_advisory_lock per router; busy → antrian ulang | `test_same_router_single_sender_other_router_independent` |
| Uncertain retry buta (JS-0020-05) | uncertain tidak retryable; resolve readback protocol | `TestUncertainAndRetry` (5 tes) |
| Recovery lewatnya crash claimed/preflight + race reconcile (JS-0020-04) | reconcile state/effect-aware + CAS | `TestCrashReconcileDeadline` (6 tes) |
| Worker tanpa drain/deadline (JS-0020-07) | runworker signal + drain-timeout + exit code; deadline claim/batas-efek | `TestDrainProcesses` (4 tes proses nyata) + 2 tes deadline |
| Authority tidak diperiksa ulang (JS-0020-08) | check_current_authority fresh-DB + provenance verify_api_ssl | `TestCurrentAuthority` (6 tes) |
| Authority HTTP / replace (JS-0020-09) | izin operasi dasar + step-up; routers.release | `TestHttpAuthorityAndVerifier` (6 tes) |
| Handler hilang / verifier negatif sukses palsu (JS-0020-10) | fail-closed handler_missing; ok:False → failed | `test_missing_handler_fails_closed`, `test_negative_verifier_never_succeeds` |
| REV-2011-01 (review independen, P1) | active_states mencakup uncertain/recovery_required | `test_retry_origin_blocked_while_child_uncertain` |
| REV-2011-02 (P2) | CAS klausa WHERE pada commit hasil + _verify_only | tercakup `TestOwnershipFencing` + suite |
| REV-2011-03 (P2) | resolve(False) wajib advisory lock router bebas | `test_resolve_not_applied_refused_while_old_writer_active` |
| REV-2011-04 (P2) | progress() memperpanjang lease | `test_progress_renews_lease_for_long_work` |
| REV-2011-05/06/07/08/09 (P3) | jalur tabel state §6; timer drain hanya saat aktif + sleep interruptible; recheck_authority fase kirim cutover; fail-closed kind tak terpetakan; tes drain pra-efek | suite penuh + `test_drain_before_effect_holds_job_requeueable` |

## 4. Matriks acceptance → hasil aktual → evidence

Command dasar: `python -m pytest tests/... -q` dari `backend/`, PostgreSQL nyata
(non-superuser), exit 0 semua kecuali disebut. Path log relatif ke
`report/executor-evidence/20261117T000000Z-0020-job-lifecycle/`.

| ID | Hasil aktual (PASS/FAIL/NOT_RUN/BLOCKED) | Evidence |
|---|---|---|
| **J20-A01** ownership seluruh write | **PASS** — stale snapshot pasca-cancel/transfer: nol overwrite state/result/progress, nol efek DB/send (assert penghitung kirim + released_at); CAS gagal menghentikan worker; terminal immutable; heartbeat/progress melaporkan kehilangan (False + ctx.lost + scope ditolak). Failing-before: baseline menimpa cancelled→succeeded dan mengeksekusi efek. | `TestOwnershipFencing` 4/4; failing-before-lifecycle.log; full-suite.log |
| **J20-A02** transaksi & RLS | **PASS** — adapter diblokir terkendali (Event): koneksi observer melihat `executing`+`maybe` TERKOMIT + heartbeat; `pg_stat_activity.state='idle'` (bukan idle-in-transaction) dan nol lock `transactionid` pada backend worker saat I/O; GUC fail-closed antar unit (JobDetail tak terlihat tanpa scope); semua unit berjalan pada koneksi sama dengan konteks tenant tepercaya. PA-001 atomic lock tak diubah (regresi 55/55 billing lulus). | `test_no_db_transaction_across_blocked_io`, `test_tenant_context_fail_closed_between_units`; test_billing_payment_concurrency (dalam passing-after-targeted.log) |
| **J20-A03** writer eksternal & cancel | **PASS** — dua job router sama: pengirim kedua TIDAK mengirim (retry_wait router_sender_busy, attempt tak dikonsumsi) selama penulis lama hidup; router lain maju mandiri; queued/preflight cancel atomik CAS + epoch-bump fence (race cancel-execute teruji dua arah); executing/verifying + maybe ditolak (409), tidak ada false cancelled; lease/epoch tidak diklaim menarik command RouterOS (docstring eksplisit; pemilik baru menunggu advisory lock bebas). | `TestExternalWriterAndCancel` 4/4; failing-before |
| **J20-A04** uncertain & retry | **PASS** — uncertain ditolak retry (engine + API 409); resolve False → retry_wait + fence epoch (+ job router: ditolak `writer_active` selama penulis lama memegang lock — readback tidak dipercaya sebelum penulis berhenti); True → verify tanpa resend (penghitung kirim tetap); None → recovery_required tertahan; retry serentak → 202+409, satu kandidat aktif; retry origin saat kandidat uncertain → 409. | `TestUncertainAndRetry` 5/5 + `TestReviewerCorrections::test_retry_origin_blocked_while_child_uncertain`, `test_resolve_not_applied_refused_while_old_writer_active` |
| **J20-A05** crash/reconcile/deadline | **PASS** — crash pasca-claim/preflight → retry_wait (jalur tabel) dan tuntas saat diklaim ulang; attempt habis → failed; CAS reconcile tidak menimpa lease hidup/hasil selesai; reconcile idempotent; deadline lewat saat queued → failed tanpa kirim; deadline pra-efek (dibaca segar) → failed tanpa kirim; uncertain pasca-efek via jalur timeout-after-send; B3 1800s/B4 86400s tidak dipercepat (cutover tanpa deadline_s; tes existing cutover tetap lulus). | `TestCrashReconcileDeadline` 6/6; test_radius_cutover (suite); failing-before |
| **J20-A06** current authority | **PASS** — membership dicabut / owner→viewer / aktor non-aktif / aktor luar tenant → FAILED authority_denied dengan NOL efek (released_at tetap None); router di luar scope membership → ditolak; actorless produksi → karantina FAILED authority_unresolved retryable + resume via retry dengan provenance (teruji tuntas); verify_api_ssl actorless → provenance enrollment.created_by (creator sah → sukses; creator dicabut → gagal jujur); tanpa pemeriksaan sesi HTTP (menutup browser tidak membatalkan); cutover B2/B5 recheck kewenangan antar fase kirim. | `TestCurrentAuthority` 6/6 |
| **J20-A07** HTTP authority & verifier | **PASS** — viewer detail job backup → 403 (owner 200; lintas tenant 404); retry/cancel cutover: teknisi tanpa radius.cutover → 403, owner tanpa reauth → 403 (step-up), dengan reauth → 202/204; replace router oleh teknisi (routers.enroll saja) → 403 (baseline: 202 — failing-before), owner → 202; kind tanpa handler → FAILED handler_missing (baseline: sukses palsu); verifier ok:False → FAILED verification_failed (baseline: sukses palsu); pending_observation tetap succeeded jujur dengan hasil menunggu jendela. | `TestHttpAuthorityAndVerifier` 6/6; failing-before |
| **J20-A08** drain proses | **PASS** — SUBPROSES NYATA: SIGTERM idle → exit 0 "drain selesai" (baseline: exit -15); job DB kooperatif diselesaikan lalu exit 0; I/O terblokir + drain-timeout 2s → job uncertain `drained_mid_execute` + exit 3 (dibedakan dari drained), lalu pulih via resolve+reclaim → succeeded; SIGKILL saat executing → reconcile → uncertain → resolve → tuntas; drain pra-efek (stop_check) → retry_wait `drained_before_effect` nol efek + requeue menuntaskan. Alarm hanya aktif saat job berjalan (tidak ada exit-3 palsu saat idle). Belum rehearsal systemd/installer (lihat NOT_RUN). | `TestDrainProcesses` 4/4 + `test_drain_before_effect_holds_job_requeueable`; failing-before-drain.log |
| **J20-A09** compatibility & regresi | **PASS** — tanpa migrasi schema (makemigrations bersih; jobs/0004/0005 tak tersentuh → tes replay R4/R5 lulus utuh); inventaris payload lama: job actorless dikarantina dengan alasan + resume tepat (bukan dipurge); PA-001 penuh + PA-006 (grammar/migration/permission/selected IDs/secret scrub) lulus; P3 REV-1611-TEST-01 ditutup test-only (assert kedua thread selesai + kedua hasil ada) tanpa membuka task0010; frontend typecheck/lint/66 tes/i18n/build lulus. | full-suite.log **554 passed, 1 skipped**; passing-after-targeted.log **176 passed** (lifecycle+drain+R5+PA-001+PA-006+R4); makemigrations.log; frontend di bawah |

### Checks lain (dampak sesuai packet §Verifikasi 3–4)

- `python manage.py check` → 0 issue, exit 0 ([check.log](../executor-evidence/20261117T000000Z-0020-job-lifecycle/check.log))
- `python manage.py makemigrations --check --dry-run` → No changes detected, exit 0
- `python3 docs/tools/check_docs.py` → PASS 24 files/106 links (docs normatif tak diubah validator-nya)
- Frontend (dampak tidak langsung — permission backend saja): `tsc -b` 0 error; `eslint` 0 error; `vitest run` **66/66**; `check_i18n.py` OK; `vite build` (VITE_API_MODE=live) sukses. OpenAPI/schema: tidak ada perubahan bentuk respons (JobRecord tak berubah); tes kontrak lulus (dalam suite).
- CI kandidat exact head: diperbarui di PR setelah observasi (lihat §Pointer).

## 5. Keputusan engineering & kompatibilitas

1. **Tanpa kolom `required_permission` di envelope.** Dicoba dahulu sebagai
   migrasi additive; tes replay migrasi PA-006 (turun ke 0003/0004 lalu naik)
   meninggalkan schema pada state menengah tanpa kolom → model tak cocok.
   Solusi lebih sederhana yang compliant: peta izin per-kind di engine
   (`KIND_PERMISSION_FALLBACK`) — discover_router any-of {routers.enroll,
   migration.run} identik dengan himpunan pengenqueue sahnya. Fail-closed:
   kind produksi tak terpetakan ditolak saat create_job/authority check.
2. **Jalur tabel state §6 dijaga:** kegagalan authority pra-efek → FAILED
   (authority_unresolved retryable = karantina dengan resume eksplisit,
   tanpa auto-retry); kegagalan readback retryable dari verifying → uncertain
   (tidak membuka eksekusi ulang); reconcile claimed/preflight → retry_wait
   (jalur tabel), bukan queued langsung.
3. **Provenance verify_api_ssl** disimpan saat enqueue (actor=enrollment.created_by,
   server-derived); worker tetap menurunkan ulang dari DB segar untuk payload
   lama yang actorless.
4. **Handler direstrukturisasi minimal:** pemisahan unit DB dari I/O pada
   run_discovery (snapshot FAILED jujur saat adapter gagal), finalize_verification
   (probe di luar unit tenant), BackupRunHandler (artifact/commit katalog dalam
   unit; adapter/file di luar), cutover B2/B5/B6 (APPLY/VERIFY di luar unit;
   evidence kegagalan di-commit lalu JobError dilempar setelah unit selesai).
   Perilaku domain dipertahankan (tes existing lulus); pengecualian: kegagalan
   discovery kini meninggalkan snapshot FAILED yang terlihat (lebih jujur
   daripada rollback diam-diam).
5. **Tes existing disesuaikan hanya untuk kontrak baru yang sah:** enrollment/
   cutover kini membuat job produksi dengan aktor sah (mensimulasikan alur API
   nyata yang selalu membawa aktor). PA-001/PA-006/R4/R5 TIDAK diubah
   kecuali hardening P3 REV-1611-TEST-01.

## 6. Bukti source vs runtime vs proses vs perangkat

- **Source + runtime PG nyata (dibuktikan):** semua matriks di atas — PG 17.11
  non-superuser, RLS FORCE aktif, koneksi/thread/proses independen, sinyal nyata.
- **Simulator/controlled adapter:** membuktikan properti engine sandbox saja.
- **NOT_RUN (di luar scope packet / butuh host-lab):** instalasi/upgrade/restore
  OS produksi, rehearsal systemd/installer nyata, drain service sistem,
  RouterOS/CHR/GNS3 nyata (fencing perangkat eksternal — adapter api_ssl masih
  lab-gated), RADIUS auth/accounting live, browser E2E, benchmark kapasitas.
  Simulator bukan bukti integrasi perangkat; CI hijau bukan acceptance.
- **Residual (dicatat jujur):** readback `resolve_uncertain` pada perangkat
  nyata bergantung kecepatan efek RouterOS sampai — protokol engine menolak
  resolve selama penulis lama hidup, namun jendela "efek nyata belum teramati"
  tetap milik domain readback; renewal lease hanya pada jalur yang melapor
  progress/heartbeat (semua handler fase-aktif melapor per fase).

## 7. Runbook drain worker (non-normatif; REV-2011-10)

Urutan aman menghentikan/restart worker (juga di docstring `runworker.py`):

1. **Stop claims:** kirim SIGTERM/SIGINT → worker berhenti mengklaim job baru
   segera (sleep polling dibangunkan; tidak ada klaim baru setelah flag stop).
2. **Drain / stop old writers:** biarkan job aktif menyelesaikan dalam
   `--drain-timeout` (default 60 s). Job DB kooperatif selesai normal; I/O
   terblokir melebihi batas ditahan jujur di state durable
   (`uncertain drained_mid_execute` / `retry_wait drained_before_effect`) dan
   proses keluar exit 3 (incomplete, terbedakan dari exit 0). Jangan menunggu
   tanpa batas — deadline habis TIDAK mengklaim pengirim sudah aman.
3. **Reconcile/readback:** setelah worker berhenti (atau setelah SIGKILL +
   lease kedaluwarsa), jalankan `python manage.py runworker --reconcile-only`
   (atau biarkan loop worker berikutnya): claimed/preflight → antrian ulang;
   executing/verifying → uncertain. Untuk uncertain: readback router SETELAH
   penulis lama terbukti berhenti → `resolve_uncertain(applied=...)`
   (False = antrian ulang dengan fence; True = verify tanpa resend; None =
   recovery_required untuk keputusan manusia).
4. **Resume:** worker baru mengklaim antrean (SKIP LOCKED; per-router advisory
   lock mencegah dua pengirim). `retry_job` untuk terminal retryable bila
   diperlukan (menautkan origin + request_id semula).

Bukan rehearsal installer/systemd produksi (NOT_RUN).

## 8. Pointer penyerahan

| Field | Nilai |
|---|---|
| Instruction ref | `review/0020-job-lifecycle-authority-20261117` @ `ea7b8a17ad8d6339eed45769bbff1626ea279665` (PR26) |
| Base | `main@41d1f33f16508491a34f66b767830b9dd3e5954e` |
| Implementation/tested SHA | **`7118cce0db330acb02be0b3b774b1b1628d55d7a`** (engine `6e96ce33` + fix test-infra CI; seluruh evidence dijalankan pada tree kode tersebut) |
| Published candidate | branch `session/2026-11-17-0020-job-lifecycle-authority` + [PR27](https://github.com/smahud/MicroTix_Project/pull/27); remote readback head diverifikasi; SHA final + CI dicatat di handoff |
| Candidate CI | exact head — hasil diobservasi dan dicatat di PR setelah push |
| Review independen | [reviewer/20261117T010218Z-0020-job-lifecycle-independent.md](../reviewer/20261117T010218Z-0020-job-lifecycle-independent.md) — verdict pra-koreksi CHANGES_REQUESTED (REV-2011-01..10); seluruh temuan ditindaklanjuti di penyerahan ini (matriks §3) |
| Evidence dir | [executor-evidence/20261117T000000Z-0020-job-lifecycle/](../executor-evidence/20261117T000000Z-0020-job-lifecycle/) |

Laporan ini + packet `_done` + handoff/progress adalah descendant report-only
di atas implementation commit: `git diff 7118cce0db330acb02be0b3b774b1b1628d55d7a HEAD -- backend/ apps/` kosong
(hanya task/report/docs metadata). Perbaikan test-infra `7118cce0`: _db_url
subprocess drain kini menyertakan password (CI password auth) — tanpa perubahan
engine/handler; suite penuh diulang 554 passed pada tree ini.

## 9. Risiko, batas, dan next actor/action

- Risiko rendah-sisa: readback perangkat nyata (di atas), renewal lease pada
  handler yang tidak melapor, jalur authority per-chunk hanya di fase kirim
  cutover (kind fase aktif lain satu-chunk).
- Next actor: **controller_reviewer** — review exact SHA kandidat atas matriks
  A01–A09 §4 dan temuan reviewer §3; changes-requested membuka kembali ID0020
  yang sama.
- Production Beta tetap **NOT_READY**; installer/upgrade/restore/scheduler/
  DEC-01/DEC-02/gates host-lab/kapasitas tetap blocker terpisah. Penyerahan
  ini bukan merge/deploy/tag/aktivasi.
