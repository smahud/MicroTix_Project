# 04 — Review gates dan handoff implementasi

Baseline **`main@16085f825fef25ee4112d74b729c57e623b0bb05`**, 10 November 2026 WIB. **FINAL FOR OWNER REVIEW.** Gate tambahan di sini memakai prefix **PA-G** agar tidak mengubah arti G0–G5 di [ACCEPTANCE](../ACCEPTANCE.md). Semua kontrol keamanan dan release existing tetap berlaku.

## 1. Status akhir yang boleh dinyatakan

| Status | Syarat |
|---|---|
| READY FOR IMPLEMENTATION PLANNING | Bukti repository/scope lengkap, kontrak konsisten, konflik kritis diputuskan; planning berikutnya tidak perlu menebak baseline |
| READY WITH CONDITIONS | Tidak ada konflik arsitektur kritis unresolved; kondisi nonkritis dibatasi owner/scope/deadline dan tidak mengizinkan rilis gagal |
| NOT READY | Konflik kritis/baseline deployment belum diputuskan, integrasi docs wajib gagal, atau input penting membuat implementasi perlu menebak |

**Disposisi paket saat ini: NOT READY untuk implementasi berdasarkan paket tanpa keputusan tambahan.** DEC-01 (deployment) dan DEC-02 (manifest) masih PROPOSED. Dokumen selesai untuk ditinjau pemilik; bukan draft checklist kosong. Code defects P0/P1 sudah memiliki rencana/acceptance, tetapi tidak diperbaiki. Runtime release juga NOT READY; tidak diubah menjadi ready karena dokumen final.

Reviewer individual menyatakan planning dapat READY WITH CONDITIONS sesudah temuan/conditions dimasukkan. Orchestrator memakai status lebih ketat karena konflik kontrak deployment dan manifest belum ditutup. Perbedaan ini dicatat, bukan disamarkan sebagai persetujuan bulat.

## 2. Gate review engineering

| Gate | Scope dan pemilik review | PASS | FAIL / BLOCKED | Hubungan existing |
|---|---|---|---|---|
| PA-G0 Reality/evidence | Orchestrator + documentation reviewer | Default branch/HEAD, dirty diff, PR/CI, file inventory dan status fakta tepat; main dipisahkan dari PR | Asumsi cabang/fitur atau test PASS tanpa bukti = FAIL; akses bukti tidak tersedia = BLOCKED yang spesifik | CONTRACT §6/9/10, G0 |
| PA-G1 Architecture | Architecture reviewer, domain owners | Single modular monolith, tanggung jawab dan source of truth jelas, DEC-01 disposed, solusi sederhana dengan manfaat konkret | Critical contradictory architecture atau speculative platform = FAIL; owner decision belum ada = BLOCKED | ARCHITECTURE §1–§2, G0 |
| PA-G2 Modular boundary | Owner + reviewer caller independen | Ownership/read-write/transaction/error contracts dan allowed edges jelas; touched cycle tidak bertambah tanpa alasan | Mutasi lintas owner melewati invariant, silent signal bypass, contract/API ambiguity = FAIL | ARCHITECTURE §4–§6, PA-006–010 |
| PA-G3 Database compatibility | Database/reliability reviewer | Expanded schema dan N/N−1/pending job compatibility, locks/backfill/constraint/RLS, failed migration recovery terbukti | Lost acknowledged write, overallocate, unsafe reverse/drop, unbounded locks atau incompatible rollback = FAIL | FINANCE, G2/G5 |
| PA-G4 Security/tenant | Security reviewer | Runtime role/credential terpisah, current authority/object scope, MFA, RLS/FK/GUC, storage/scan/audit negatives sesuai fitur | Leak/privilege widening/ambiguous scope/secret exposure = FAIL; hardware target belum ada = BLOCKED lab terkait | G2, T10/T19/T20 |
| PA-G5 Deployment safety | DevOps + reliability | Candidate staging, honest status, drain/effect recovery, complete restore dan preserved router/RADIUS identities terbukti | Success palsu, incomplete recovery atau unsafe in-place upgrade = FAIL; host/lab belum tersedia = BLOCKED untuk uji itu | OPERATIONS, G1/G5; host Gate A/G historis |
| PA-G6 Release readiness | Integrator + independent reviewer; owner sesuai release | Semua gate fitur relevan PASS, evidence pinned, known limitations/flags jujur, rollback/recovery dan owner approvals terpenuhi | P0/P1 aktif belum dibuktikan tertutup, pending mandatory evidence atau docs CI gagal = tidak boleh release/merge dianggap lolos | ACCEPTANCE per feature G0–G5, CONTRACT §11 |

PASS mengacu build+feature+adapter+topology+workload+config yang diuji. Gate dokumen tidak memberi izin network mutation. Menutup satu temuan tidak otomatis menutup seluruh gate. Kode yang belum ditest bukan FAIL test; requirement yang jelas dilanggar statis tetap defect/CONFLICT dengan runtime NOT_RUN.

## 3. Existing test evidence dan gap

Status eksekusi **seluruh runtime suite pada sesi audit ini: NOT_RUN**. Kolom “ada” berarti test source dibaca/inventoried. CI baseline historis success dapat diverifikasi pada [run 42285141174](https://github.com/smahud/MicroTix_Project/actions/runs/42285141174); itu tidak menutup gap assertion berikut.

| Area | Sumber yang ada | Penilaian kecukupan | Acceptance yang masih harus dibuktikan / environment |
|---|---|---|---|
| Domain contracts | `backend/tests/contracts/test_*_contract.py` | Ada, PARTIAL; banyak path/method/key set | Owner invariant, input/status/error semantics, no cross-owner bypass; backend + PostgreSQL |
| Cross-domain regression | Billing/customers/documents/radius integration files | Ada, PARTIAL | Failure rollback source+projection+receipt+audit+outbox, signal-bypassing bulk path; PostgreSQL nyata |
| Tenant isolation | `test_rls.py`, customer/job/doc tenant negatives | Ada, belum semua reference/process | Tiap new table/FK, role nyata, error/commit/rollback/pool reuse, platform scope, revoke-before-effect; separate runtime/migrator/daemon roles |
| API compatibility | Schema/contract tests, FE api tests | Ada, PARTIAL | Old client fixture, missing/null/[] semantics, statuses/permission/errors, concurrent idempotency, migration selected set; live adapter + backend |
| Migration compatibility | Migration source dan historical makemigrations check | Full N/N−1 upgrade suite NOT FOUND dalam inspected tests | Old/new app/worker + expanded schema, partial backfill, lock timeout/invalid index recovery; disposable PG17 dengan realistic table volume |
| Upgrade/rollback | Installer syntax/preflight historical evidence | End-to-end upgrade/recovery suite NOT FOUND dalam scope tests/CI | A→B→B, fault setiap phase, compatible code rollback tanpa kehilangan writes; disposable Debian13 root/systemd/domain/TLS |
| Worker lifecycle | `test_jobs_engine.py`, state-machine tests | Ada, sequential PARTIAL | Two-worker stale lease, kill each state, drain, heartbeat/deadline, cancel-in-flight, no terminal resurrection; two DB connections + separate processes |
| Outbox delivery | Event insertion di services; dispatch source | Consumer delivery proof NOT IMPLEMENTED pada engine inspected | Commit/ack crash replay/dedup dan old-event backfill; existing PG engine, consumer nyata pertama |
| Backup/router restore | `test_ops_backups.py` | Simulator pipeline saja | Exact artifact attribution, real bytes/hash/transfer, restore compatibility dan authorized download revoke; CHR/router lab + receiver |
| Platform backup/DR | Installer dump/list; OPERATIONS design | Full restore execution UNVERIFIED | Keys+DB+blob+config+roles+NAS/VPN recovered isolated; acknowledged sequence tie-out, RPO/RTO measured; disposable secondary target/off-host artefact |
| Router preservation | `test_enrollment_flow.py`, `test_wg_host.py`, api client/probe unit tests | Ada, lab UNVERIFIED | Token atomicity/fail-closed GUC; keys/peers/routes/pins tetap saat upgrade, two tenants LAN sama; CHR/GNS3 + WG gateway |
| RADIUS continuity | Projection/facade/cutover tests dan `backend/scripts/test_radius.sh` | Ada; daemon harness bukan PPPoE/Hotspot proof | Daemon config/role nyata, auth/accounting/control sessions sebelum/selama/sesudah patch, no wrong tenant/NAS; daemon + CHR clients |
| Billing/finance integrity | Calendar/invoice/payment tests | Billing ada, concurrency PARTIAL; ledger absent | PA-001/006/007 two-connection, sum/tie-out/replay, one source debit; full ledger tests hanya fase ledger aktif |
| Frontend flags | Permissions/release-flags tests, live build guard | Ada, UI flag bukan authorization | Direct route/API disabled behavior, flag-off noninterference, tenant-state reset; browser + live API |
| Security regression | Auth, audit, doc tests | Ada, PARTIAL; many fixtures bypass full auth/CSRF | Full platform login MFA, factor concurrency, direct session expiry, job permissions/router_scope, scanner failure pada SaaS DAN internet proof routes, nested redaction, strict CSRF; real auth + DB |
| Capacity/monitoring | Requirement profiles dan sample-based endpoints | Million-client benchmark UNVERIFIED | 10→100→1.000 tenants, sampai target1.000 online/tenant, aggregate+selected realtime, fairness/auth/accounting/storm/restore metrics; budgeted load/lab environment |

Test baru dipilih untuk risiko nyata di register; jangan 256 fungsi menyalin 256 katalog case atau assertions yang hanya meniru implementation. Existing test source yang memeriksa sequential flow tetap bermanfaat; tidak disebut cukup untuk concurrency.

## 4. Acceptance package minimum per patch

| Elemen | Isi wajib |
|---|---|
| Identity | run_id, UTC start/end/duration, base+candidate SHA, dirty diff bila ada, author/reviewer |
| Scope | Requirement/test-case/assertion IDs existing + finding ID; feature/adapter/firmware/topology/config dan target yang terotorisasi |
| Environment | Runtime/DB/tool/dependency versions, role ownership/grants, relevant flags, resource/load budget; tanpa secret value |
| Execution | Exact command/cwd, exit code, expected dan actual per assertion; NOT_RUN/BLOCKED/RUNNING/PASS/FAIL/N/A beralasan |
| Integrity | Sanitized artifact path/hash, counts/financial sequence dan cleanup/recovery status; retention sesuai data |
| Review | Independent disposition, findings closed/open, exception scope/expiry, approval reference yang benar |
| Integration | Files/diff, code vs docs dimension, commit/PR dan verified remote status atau NOT PUSHED, exact next steps |

Report setiap agent wajib `report/<role>/<UTC>-<slug>.md`; handoff kanonis `report/LATEST_HANDOFF.md`. Source requirement/test catalogue tidak ditimpa menjadi PASS. Jangan commit passwords, keys, raw customer evidence, raw RADIUS/PPP capture atau XML sensitif. Simpan hanya evidence tersanitasi yang perlu untuk review.

Dokumen status yang biasanya diubah (`docs/progress.md`, BETA status) tidak diubah sesi ini karena scope hanya planning_audit/report. Konflik klaim lama dicatat di laporan dan proposal; sesi berikutnya mengoreksinya lewat perubahan terotorisasi.

## 5. Current documentation gate dan change control

Sebelum penambahan planning_audit, `python3 docs/tools/check_docs.py` **PASS**: 22 files, 67 internal links, 85 tasks, 256 designed cases/662 assertions, 115 defaults. Setelah lima file ditambah, validator existing menemukan manifest mismatch karena `docs/repository-manifest.json` belum diperluas. **FAIL ini bukan diabaikan atau disebut PASS**; DEC-02 adalah syarat integrasi PR.

Pemeriksaan link/heading/whitespace scoped dapat memvalidasi paket tanpa mengubah manifest. Rehearsal refresh di salinan sementara boleh membuktikan proposal manifest saja, dengan label terpisah; ia bukan green CI working tree. Jangan menjalankan refresh pada repository asli di luar izin sesi. Tidak menambahkan exception path pada validator untuk menutupi kegagalan.

| Perubahan | Authority/status |
|---|---|
| Audit fakta, lima docs dan laporan | Diotorisasi pengguna pada sesi ini; boleh commit/doc PR |
| Persetujuan tulisan final | Review pemilik; tidak otomatis menyetujui semua proposal normatif |
| DEC-01 native-vs-Compose | Owner approval jika mengubah baseline arsitektur; sebelum itu Compose existing tetap berlaku |
| DEC-02 manifest extension | Owner perlu memperluas izin edit terbatas ke manifest; refresh bukan perubahan source app, tetapi tetap di luar path izin sekarang |
| Koreksi kode untuk memenuhi invariant existing | Sesi implementasi terotorisasi berikutnya, patch kecil + tests/review/report; bukan izin patch pada audit ini |
| Mengubah tujuan, kebijakan security/network, acceptance | Approval eksplisit sesuai CONTRACT §4, rationale/evidence/alternatives dan impact record |
| Merge ke main/tag/release/deploy | Required approvals/gates dan scope target; tidak dilakukan dalam sesi ini |

Koreksi status historis tidak menghapus evidence lama. PR #7 tetap direview terpisah sebelum digabung; audit snapshot harus di-rebase/delta-review bila HEAD berubah. Tidak ada push langsung main.

## 6. Exception policy

Exception tidak boleh menyatakan test tidak dijalankan sebagai PASS atau menutup kerusakan uang/tenant/secret/recovery kritis. Bila keputusan mengubah kontrak, catat PROPOSED sampai owner menyetujui; pembatasan fitur agar tidak digunakan harus nyata dan diuji.

Exception P2/P3 nonkritis dapat dipertimbangkan dengan ID, owner, scope release/feature, alasan, alternatif, mitigation, expiry, acceptance follow-up dan approval faktual. Sebut dependency yang dapat lanjut. Tidak menggunakan “Beta sementara” untuk melepaskan RLS, MFA platform, money consistency, verified recovery atau mandatory network authorization.

Ketiadaan CHR/controller/license/host/domain memblokir bukti lab/deploy itu; independent code/docs checks dapat lanjut. Budget dan akses baru diperlukan hanya saat operasi target tersebut dijalankan. Tidak ada permintaan kredensial untuk audit statis.

## 7. Hasil review independen dan disposisi

| Reviewer | Hasil dan penggunaan |
|---|---|
| [Architecture/Frontend](../../report/architecture-review/20261109T210133Z-planning-audit.md) | Pertahankan monolith; payment/quota/import/idempotency dan ownership/frontend gaps dimasukkan ke PA-001/006–010 |
| [Database/Reliability](../../report/database-review/20261109T210133Z-planning-audit.md) | REQUEST CHANGES pada klaim reliability; PA-001/002/005/006/009/011/013 dan migration/recovery matrix |
| [DevOps](../../report/devops-review/20261109T210133Z-planning-audit.md) | Production install/upgrade NOT READY; OPS-01–09 dan bounded staged release, bukan cluster |
| [Security](../../report/security-review/20261109T210133Z-planning-audit.md) | REQUEST CHANGES sebelum affected production; PA-003/004/005/011/012 dan OPS-07; tidak ada exploit claim |
| Documentation reviewer | Review silang paket final, evidence/report/link/status/main-vs-PR/proposal; hasil faktual di [laporan utama](../../report/planning-audit/20261109T210133Z-finalization.md) |

Semua reviewer teknis melakukan static read-only dan orchestrator mempertahankan handoff lengkap. Mereka agen independen dari penulis utama, bukan auditor manusia/akuntan/legal. Tax draft tambahan dibaca orchestrator; kompatibilitas regulatory/template/PJAP tetap UNVERIFIED dan di luar audit ini.

## 8. Handoff yang dapat dieksekusi sesi berikutnya

1. Baca [LATEST_HANDOFF](../../report/LATEST_HANDOFF.md), fetch remote, pin HEAD baru dan audit delta terhadap 16085f8. Preserve unmerged PR #7 dan perubahan pihak lain.
2. Selesaikan DEC-01/DEC-02 untuk paket ini; jangan silently edit CONTRACT atau planning_mvp. Integrasikan manifest melalui PR dokumentasi dengan izin path yang benar, lalu wajib docs CI PASS.
3. Saat implementasi diotorisasi, pilih patch PA-001 concurrency pertama; PA-002/003/005/006 dan OPS-01/02/06/07 dapat disiapkan terisolasi sesuai dependency. Buat failing regression relevan, minimum fix, independent review, report dan verified commit.
4. Uji clean/repeat Debian13 dan staged upgrade/restore setelah artefak/lifecycle aman. Jangan memakai produksi untuk menemukan kembali static blocker yang sudah dicatat.
5. Lanjut CHR/GNS3/protocol/AAA gates hanya dengan target/license/budget tersedia. Hardware/simulator/CI evidence dibedakan.
6. Tax/ledger setelah owner scope dan existing contracts aman; jangan menambah schema/model/queue baru pada sesi planning_audit ini atau memaksa fase masa depan menjadi blocker R1 yang tidak terkait.

Sesi audit ini berakhir dengan dokumen reviewable, laporan lengkap, diff documentation-only dan status jujur. Ia tidak menutup bug yang masih ada dan tidak memberi persetujuan deployment.
