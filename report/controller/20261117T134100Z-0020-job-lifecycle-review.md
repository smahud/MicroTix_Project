# Controller R1 — task0020 PA-002 + PA-003: changes_requested

## 1. Keputusan dan revision yang diperiksa

**Verdict `changes_requested` pada exact PR27
`bd37c14e6c41339a8743b3d4b723ee74f13bef08`.** Task0020 dibuka kembali
menjadi **`ready / changes_requested`**, ID tetap, next actor **coding_agent**.
Delapan defect terkonfirmasi oleh sebelas acceptance probes PostgreSQL nyata;
gap verifikasi wajib dicatat terpisah sebagai REV-1711-09. Tidak ada task0030,
acceptance, merge, deployment, aktivasi fitur atau release tag dalam sesi ini.
Production Beta tetap **NOT_READY**. PA-006/task0010 tetap accepted/integrated.

| Field | Evidence / revision |
|---|---|
| Author / role | OpenAI Codex `/root`, controller reviewer; dua reviewer independen sesuai CONTRACT §5 |
| Baseline / canonical main | `41d1f33f16508491a34f66b767830b9dd3e5954e` |
| Instruction | PR26 `review/0020-job-lifecycle-authority-20261117` @ `ea7b8a17ad8d6339eed45769bbff1626ea279665` |
| Candidate / reviewed SHA | PR27 `session/2026-11-17-0020-job-lifecycle-authority` @ **`bd37c14e6c41339a8743b3d4b723ee74f13bef08`** |
| Executor tested ancestor | `7118cce0db330acb02be0b3b774b1b1628d55d7a`; `git diff 7118cce bd37c14 -- backend/ apps/` kosong |
| Local branch | `review/0020-controller-20261117`, dibuat dari exact candidate pada checkout baru yang bersih; tidak ada pekerjaan pengguna ditimpa |
| Decision ref | `review/0020-controller-20261117`; target PR kandidat, publikasi/readback ada pada §8 dan `publication.json` |
| Packet reopened | [0020-job-lifecycle-authority.md](../../task/0020-job-lifecycle-authority.md) |
| Executor input | [Report](../orchestrator/20261117T010218Z-0020-job-lifecycle-authority.md), [internal reviewer](../reviewer/20261117T010218Z-0020-job-lifecycle-independent.md) |
| Controller evidence | [Directory](../controller-evidence/20261117T134100Z-0020-review/), [summary](../controller-evidence/20261117T134100Z-0020-review/review-results.json) |

AGENTS, CONTRACT, panduan tetap/default reviewer dan packet dibaca. Authority
tetap PRODUCT TEN-03/JOB-02–05/SUB-05/SEC-01/04/05; ARCHITECTURE §§3–6;
OPERATIONS §§3–4; ACCEPTANCE §4. Tidak mengadopsi PR8 draft, mengubah kebutuhan
normatif, installer/topology, migration PA-0060004/0005 atau fitur fase depan.

Discovery remote memeriksa **30 branches / 13 open PRs**; main masih41d1f33.
PR26 adalah instruksi, PR27 kandidat implementasi, PR28@8204ba0 hanya laporan
executor state-check pada ID0020, bukan koreksi source. Current task tidak
disimpulkan dari filename/main saja. PR7/8/14 dan histori task0010 dipertahankan.
Snapshot awal [remote-inputs.json](../controller-evidence/20261117T134100Z-0020-review/remote-inputs.json)
dan pemeriksaan ref sebelum publikasi membatasi freshness verdict.

## 2. Pemeriksaan independen dan hasil nyata

Root menelusuri acceptance → source/handler → state/effect → assertion,
membaca diff dan jalur kritis di luar diff, memeriksa probe kedua reviewer,
lalu **menjalankan sendiri** full suite dan semua focused probes. Reviewer
menulis laporan/source probes; output mereka tidak diterima sebagai runtime
PASS tanpa pemeriksaan root.

| Pemeriksaan root | Command / hasil / batas |
|---|---|
| Suite backend | `python -m pytest tests -q --reuse-db`: **554 passed, 1 skipped, 3 warnings**, exit0,98.09s; [log](../controller-evidence/20261117T134100Z-0020-review/full-suite.log) |
| Lifecycle acceptance probes | `python -m pytest -c pytest.ini .../test_lifecycle_review.py -q -s --reuse-db --tb=short`: **4 failed assertions, 0 errors**, exit1,1.83s; [final log](../controller-evidence/20261117T134100Z-0020-review/lifecycle-probes.log) |
| Authority/handler probes | Command sama untuk `test_authority_review.py`: **7 failed assertions, 0 errors**, exit1,2.91s; [final log](../controller-evidence/20261117T134100Z-0020-review/authority-probes.log) |
| Django checks | `manage.py check`:0 issue exit0; `makemigrations --check --dry-run`:No changes detected exit0, konsistensi DB diperiksa dengan server hidup |
| Schema + RLS | Fresh migrate dan grant exit0; [split-role/RLS](../controller-evidence/20261117T134100Z-0020-review/split-roles-rls.log):59table milik migrator; runtime nonowner NOSUPERUSER/NOBYPASSRLS, FORCE RLS pada tabel tenant terkait |
| Docs | `python3 docs/tools/check_docs.py`:PASS24files/106links, exit0; scope validator statis, bukan acceptance aplikasi |
| Pure control flow | `source_authority_probe.py` exit0:reproduksi helper/B6; bukti tambahan source, bukan pengganti HTTP/PG |
| Exact candidate CI | [run43994355914](https://github.com/smahud/MicroTix_Project/actions/runs/43994355914), SHA **bd37c14**, backend/frontend/docs **success3/3**, dibaca dari GitHub check-runs; ini CI existing, bukan root frontend rerun |

Lingkungan root: Debian13.6, Python3.13.5, Django5.2.19, psycopg3.2.13,
pytest8.4.2, **PostgreSQL17.11** dari paket Debian yang diekstrak user-local;
tidak memasang service host. [Environment](../controller-evidence/20261117T134100Z-0020-review/environment.log).
Suite memakai test DB milik runtime dengan FORCE RLS, sesuai harness repository.
**Focused probes dijalankan ulang pada DB baru dengan schema milik
`mtx_migrator`, runtime `mtx_app` terpisah**; extra TRUNCATE hanya untuk cleanup
pytest disposable, bukan rekomendasi privilege produksi. Ini menutup keterbatasan
owner pada bukti reproduksi, bukan klaim paritas seluruh deployment.

Runner: [run_review.sh](../controller-evidence/20261117T134100Z-0020-review/run_review.sh)
untuk suite/checks, [run_probes_split.sh](../controller-evidence/20261117T134100Z-0020-review/run_probes_split.sh)
untuk reproduksi final, [exit codes](../controller-evidence/20261117T134100Z-0020-review/exit-codes.txt).
Full suite mencakup PA-001 dan PA-006/R4/R5; tidak diulang setelah hanya harness
report-probe diperbaiki. App/test source kandidat tetap byte-identik sepanjang review.

Awal harness root gagal karena server PG dan client dijalankan pada namespace
exec berbeda; ini dikoreksi dengan satu runner. Probe awal juga mengalami
teardown FK `radius.nas` karena marker `available_apps` hilang; marker
diperbaiki mengikuti suite existing, assertion tidak dilemahkan, semua probe
diulang pada DB baru. **Hanya hasil final tanpa harness error dipakai**.
[Initial-harness note](../controller-evidence/20261117T134100Z-0020-review/initial-harness.log)
dan log `*-initial` mempertahankan jejak; hasil terkontaminasi bukan defect produk.

Satu skip root adalah binary FreeRADIUS tidak tersedia; tiga warning berasal
adapter-thread TLS suite existing. Tidak ada klaim menjalankan RADIUS daemon
atau frontend lokal. Controlled adapters/fault injection membuktikan engine,
HTTP dan transaksi sandbox, **bukan** RouterOS nyata, readback perangkat,
systemd, GNS3 atau zero downtime.

## 3. Temuan final dan acceptance koreksi

Nomor di bawah adalah finding controller final untuk **ID0020 yang sama**.
Mapping ke reviewer: LIFE01–04→REV-1711-01–04; AUTH01–04→REV-1711-05–08.
Semua severity mengacu dampak scope Beta aktif, bukan sasaran1juta client.

### REV-1711-01 — P1 — stale worker masih commit domain setelah reconcile

`jobs/engine.py:173–184` hanya memeriksa flag memori `ctx.lost`, tanpa guard
current lease/token/epoch/state pada unit commit. `network/handlers.py:110–114`
memanggil `network/services.py:906–978` tanpa konteks ownership job. Block
`list_accounts`, expire+reconcile lease lewat koneksi lain, lalu lepas worker:
**job uncertain, tetapi DiscoveryObject1, health sample1 dan snapshot succeeded**.
Final envelope CAS menghentikan hasil envelope, tetapi domain sudah berubah.
Failed progress juga diabaikan sebelum manifest backup berikutnya.

**Minimum:** fence setiap unit commit domain pada transaksi/koneksi tenant
yang sama dengan guard ownership yang valid; kehilangan ownership membatalkan
unit sebelum commit. Teruskan guard ke service-owned units dan hentikan efek
berikutnya saat checkpoint gagal. Jangan memegang transaksi DB melintasi I/O.
**Closure A01/A02/A05:** probe actual discovery+backup/cutover post-I/O,
lease transfer/reconcile/cancel, bounded participants; nol efek domain/file/send
baru setelah kehilangan ownership, new-owner result/state tetap utuh.

### REV-1711-02 — P1 — error setelah efek backup membuka retry otomatis

`jobs/engine.py:613–615,735–770` mengubah generic execute exception menjadi
retryable internal_error→retry_wait meskipun effect_state=MAYBE. Actual
`backups/service.py:197,218` create_backup berhasil lalu manifest OSError:
**retry_wait/maybe, reclaimed=True, send2, artifact2** tanpa readback.
Executing→retry_wait juga melewati state table ARCHITECTURE§6.

**Minimum:** kegagalan setelah possible effect default hold uncertain/recovery;
retry hanya dari bukti no-effect/safe outcome yang eksplisit. Preserve retry
pra-efek/DB rollback yang benar. **Closure A04/A05:** manifest/disk/generic
error sesudah send tidak menghasilkan second send/claimable retry; applied
readback verify tanpa resend, not-applied retry setelah old writer aman,
unknown tetap tertahan; jangan mengandalkan retry budget sebagai safety.

### REV-1711-03 — P1 — retry ancestor melewati descendant uncertain

`jobs/engine.py:999–1005` hanya mengunci origin yang diminta dan memeriksa
child langsung. O failed→retry C failed→retry G sends/uncertain→retry O
membuat sibling N. Probe menjalankan G dan N: **G tetap uncertain, extra
retry=True, send2**. Outcome logis unknown tidak aman hanya karena child
langsung terminal; klaim closure internal REV-2011-01 masih partial.

**Minimum:** pertahankan satu identitas/guard terserialisasi untuk lineage
retry logis, termasuk seluruh descendant aktif/uncertain/recovery, memakai
model/DB existing dan perubahan minimum. **Closure A04:** ancestor/child
concurrent retry tidak melewati descendant unknown, nol second effect;
retry atas terminal dengan outcome yang sudah diketahui tetap sah sesuai
kontrak. Jangan membuat graph/task framework baru.

### REV-1711-04 — P1 — pemilik router berikutnya mengirim sebelum readback unknown selesai

`jobs/engine.py:574–589,691–695` hanya menjaga advisory session lock saat
worker hidup. Timeout-after-send→uncertain melepas lock; job konflik berikutnya
langsung mengirim. Probe same-router/same-kind: **predecessor uncertain,
successor succeeded, send2**, belum ada resolve/readback predecessor.
PRODUCT JOB-03/05 dan ARCHITECTURE§6 meminta old writer aman **dan** readback.

**Minimum:** pertahankan hold durable untuk mutasi router yang berkonflik
dengan outcome unknown hingga old writer/readback membuktikan kelanjutan
aman; jangan menyamakan lock bebas dengan outcome selesai. Readback/recovery
yang aman dan router lain tetap boleh maju. **Closure A03/A04:** dua workers,
same-router unknown predecessor→nol conflicting send berikutnya sebelum
recovery; router lain independen; true/false/unknown readback dan writer
masih hidup teruji, tanpa lock DB melintasi adapter I/O.

### REV-1711-05 — P1 — revoke/demote setelah preflight tetap melepas router

`jobs/engine.py:531–546,591–606` mengecek authority sebelum preflight, tidak
di effect boundary setelahnya; `network/handlers.py:142–155` commit release
tanpa fresh authority. Event sesudah **real production preflight**, revoke
atau demote dari koneksi PG lain, lanjut worker: **dua kasus succeeded,
router_released=True**, error=None. Lease yang valid bukan izin actor.

**Minimum:** current authority pada batas efek setelah preflight dan sebelum
setiap sensitive chunk/commit yang relevan; resource/router/policy tidak
diambil dari snapshot lama. **Closure A06:** revoke/demote/delete/narrow-scope
di barrier tersebut→nol release/peer/NAS/new send, outcome honest denied;
valid async job dan provenance enrollment tetap bekerja tanpa session secret.

### REV-1711-06 — P1 — endpoint job mengabaikan router scope membership

`jobs/views.py:47–71,89–138` memeriksa tenant+kind permission tetapi tidak
membership.router_scope. Actual HTTP pada same-tenant user scope=[A], job B:
**GET200, cancel204 dengan state queued→cancelled, retry202 dengan job1→2**.
Worker kemudian menolak scope tidak mengembalikan kerahasiaan/unauthorized
cancel yang sudah terjadi. Ini bukan bug lintas-tenant yang direka.

**Minimum:** router/resource scope di authority path HTTP bersama, generic404
untuk non-scope; preserve milik tanpa izin403 dan sensitive step-up.
**Closure A07:** GET/cancel/retry out-of-scope404, nol perubahan state/job;
in-scope permission/step-up tetap lulus. Periksa list exposure sesuai izin
baca existing tanpa memperluas privilege atau melemahkan tenant isolation.

### REV-1711-07 — P2 — B6 rollback masih menahan transaksi saat adapter I/O

`radius/handlers.py:326–346` memanggil B6 dari dalam outer ctx.scope;
`:255–270` APPLY/VERIFY tetap berada pada transaksi outer, walau inner scope
terpisah. Probe real connection mencatat **APPLY dan VERIFY atomic=True,
autocommit=False**. Comment/docstring bukan bukti boundary aman.

**Minimum:** keluar dari unit load tenant sebelum B6 APPLY/VERIFY, lalu
commit evidence dalam unit pendek ter-fence terpisah. **Closure A02:**
controlled blocking adapter B6 dengan observer independent pg_stat_activity/
locks membuktikan state durable terlihat dan worker tidak idle-in-transaction
atau memegang transaksi/row lock di I/O; scope fail-closed sesudah unit.

### REV-1711-08 — P1 — B6 negative verifier tetap mengklaim rollback berhasil

`radius/handlers.py:263–270` menyimpan readback false tetapi mengubah
enforcement LOCAL/run ROLLED_BACK. `:307–324` mengembalikan ok=True selama
run ada. Actual engine+PG probe **readback_ok=False, job succeeded,
run rolled_back, router local**, result ok=True.

**Minimum:** negative/unknown readback B6 tidak menyatakan LOCAL/ROLLED_BACK/
succeeded; simpan evidence dan recovery outcome yang benar. Final cutover
verify harus menilai state/evidence yang sah. **Closure A07/A04:** negative
dan unknown rollback tidak false-success, positive rollback tetap benar,
B3/B4 pending_observation tidak diubah menjadi device-complete atau dipercepat.

### REV-1711-09 — P2 — evidence acceptance wajib belum lengkap

Ini **gap bukti**, terpisah dari delapan bug terkonfirmasi. Jangan menandai
seluruh A05/A06/A08 PASS hanya dari jumlah tes/full-suite:

- `test_jobs_drain_pa002.py:129–145` menunggu job terminal **sebelum** SIGTERM;
  `tests/drain_handlers.py:19–23` handler bernama DB tidak melakukan DB effect.
  Tidak ada tes SIGINT. Klaim drain aktif kooperatif/SIGINT belum terbukti.
- Matrix A06 tidak memetakan actual current-policy/hold/payment/SUB-05
  assertions pada jalur aktif. Source tanpa subscription check tidak sendiri
  membuktikan pelanggaran SUB-05; perlu bukti operasi existing tetap sah,
  restricted tidak mematikan layanan, ended tidak mengisolir internet utang SaaS.
- Heartbeat per fase/progress belum membuktikan valid long-running active
  phase terhadap concurrent reconciler; LEASE30s/HEARTBEAT10s vs backup1800s.
  State/effect/lease validity dan crash sebelum/sesudah domain commit harus
  dipetakan jujur ke tes, bukan klaim synthetic state sebagai kill-process.

**Closure A05/A06/A08/A09:** sinyal nyata SIGTERM **dan** SIGINT saat idle,
active cooperative DB effect dengan barrier, blocked I/O; stop-claim assertion,
bounded exit0/3, durable recovery dan seluruh process outcomes lengkap.
Tambahkan targeted current-policy/long-phase/recovery assertions pada jalur
existing atau beri applicability dengan exact source/test evidence; jangan
membangun auto-isolir R2, scheduler atau OS rehearsal untuk gap sandbox ini.
Perbaiki defect jika pengujian baru menemukannya; NOT_RUN tidak menjadi PASS.

## 4. Matriks acceptance controller

| ID | Verdict pada kandidat | Evidence / remaining |
|---|---|---|
| J20-A01 | **FAIL** | Envelope CAS membaik; stale discovery domain commit,REV01 |
| J20-A02 | **FAIL** | Normal I/O scopes terpisah; B6 outer transaction,REV07; domain-commit guard,REV01 |
| J20-A03 | **FAIL** | Active session lock/cancel pra-efek lulus suite; unreadback successor send,REV04 |
| J20-A04 | **FAIL** | Backup generic resend, lineage unknown dan router hold,REV02/03/04; B6 false-success08 |
| J20-A05 | **PARTIAL / FAIL affected** | Reconcile early/expired/deadline unit coverage lulus; post-I/O stale+retry02/01 dan long-phase/crash evidence09 belum cukup |
| J20-A06 | **FAIL; policy evidence partial** | Before-run revoke tests lulus; after-preflight revoke/demote gagal,REV05; policy09 belum dibuktikan |
| J20-A07 | **FAIL** | Missing-handler/negative generic verifier dan release permission lulus; HTTP scope06/B6 verifier08 gagal |
| J20-A08 | **PARTIAL** | Four suite process cases lulus; actual cooperative-DB/SIGINT/stop-claim evidence09 belum lengkap; OS drain NOT_RUN |
| J20-A09 | **PARTIAL** | Fresh split-role migrate/grant PASS; PA001/PA006 full regression/P3 thread assertions preserved; compatibility/recovery final perlu revalidation setelah koreksi |

## 5. Closure lama dan kemajuan yang dipertahankan

Jangan mengulang implementasi PA-006/PA-001 atau membuka task0010. Source
dan suite mendukung terminal/result CAS di WHERE (internal REV-2011-02),
cancel pra-efek epoch bump, explicit executing cancel conflict, missing-handler
dan generic negative-verifier fail-closed, actorless enrollment provenance,
legacy quarantine+resume, permissions/step-up dasar, router_replace release
permission, queued/pre-effect deadline dan R5 missing-participant assertions.
Perbaikan ini dipertahankan; bagian yang terbukti belum lengkap disebut di §3.

Internal REV-2011-01 tetap partial pada retry lineage (REV03); lock check
old-writer/REV-2011-03 tidak membuktikan durable unreadback router conflict
(REV04); progress-renew/REV-2011-04 bukan bukti long-phase lengkap (REV09).
Source engine/cutover comments yang menyatakan seluruh commit/I/O fenced
tidak dijadikan acceptance ketika probe membuktikan sebaliknya.

## 6. Perubahan sesi, risiko dan batas

Perubahan controller hanya packet rename/status/correction matrix, laporan
root+dua reviewer, evidence/probes, LATEST_HANDOFF/progress, serta incoming
navigation link pada executor report. Tidak mengubah app/backend/tests,
domain requirements, dependency/CI, applied migrations, CONTRACT atau installer.
Tidak mengklaim normative decision baru. Rollback dokumen melalui Git biasa;
kode kandidat tetap utuh. Tidak ada secret/production customer data di evidence.

Independent reports:
[lifecycle](../reviewer/20261117T140000Z-0020-lifecycle-independent.md) dan
[authority](../reviewer/20261117T140000Z-0020-authority-independent.md).
Masing-masing membedakan source/probe authorship dari root PG execution.
Temuan sub-agent diperiksa ulang root terhadap source dan hasil durable.

NOT_RUN: produksi install/reinstall/upgrade/restore/DR; systemd service drain;
RouterOS/CHR/GNS3/pilot; live RADIUS daemon; browser E2E; scale/soak/one-million
client benchmark; real external fencing. Installer/secret/recovery/scheduler/
topology DEC-01/DEC-02 dan gates host/lab/kapasitas tetap di register Beta
terpisah. Delapan defect sandbox ini tidak disamarkan sebagai kendala host.

## 7. Next actor dan penyerahan koreksi

**Coding agent:** fetch decision ref ini, baca packet0020 unfinished dan §3,
lanjutkan dari source PR27 yang dibawa branch review. Tutup REV-1711-01–09
pada ID0020 yang sama dengan perubahan minimum existing stack, failing-before/
passing-after, state/effect counts, complete concurrent participants, review
independen, full required regression/checks, laporan matriksA01–A09 dan exact
new implementation/tested/published SHA+CI. Preserve seluruh laporan lama.
Task baru dependent menunggu acceptance dan integration prerequisite.

**Controller berikutnya:** review exact SHA koreksi, jalankan lagi probe yang
relevan, periksa delta main/candidate+CI, publish verdict; accepted/merge/deploy
tetap keputusan terpisah. File packet tidak otomatis menjalankan external agent.

## 8. Publication record

**PUBLISHED_AND_VERIFIED**: initial decision commit
**`3c4b71fa75ab0619bf12b84660a8678b99294e20`**, tree
**`9b7d2405b61be23f333f83dc4a6e3999b63790e7`**, branch
`review/0020-controller-20261117`, **[PR29](https://github.com/smahud/MicroTix_Project/pull/29)**
open, targets PR27 candidate branch at exact **bd37c14**.

GitHub ref/commit/parent/full tree dan **39 changed/deleted paths** dibandingkan
ke staged blob IDs lokal: seluruhnya MATCH, tanpa truncated tree. Local fetch
+content/index equality dan clean worktree terverifikasi; source/config
protected delta terhadap bd37c14 kosong. Main tetap41d1f33, PR27 tetapbd37c14;
PR26/28 dan pekerjaan lain tidak diubah. [Publication record](../controller-evidence/20261117T134100Z-0020-review/publication.json)
menyimpan readback dan observasi CI awal pada commit tersebut.

Bagian ini serta publication record ditambahkan **sesudah** commit di atas
benar-benar terbit, pada descendant metadata-only. Commit descendant tidak
mengklaim SHA masa depannya sendiri. Root memverifikasi ulang head/ref/PR/file
final dan mencatat current-head CI pada deskripsi PR29; CI candidate bd37c14
atau ancestor dokumen tidak diinferensikan sebagai CI head baru. Verdict
review tetap terkait bd37c14; commit dokumen tidak menjadi acceptance kode.
