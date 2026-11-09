# 03 — Upgrade, patch dan recovery safety

Baseline `main@16085f825fef25ee4112d74b729c57e623b0bb05`. **FINAL FOR OWNER REVIEW.** Ini audit dan rencana implementasi, bukan runbook yang sudah diuji. Tidak ada perintah installer, migrasi, restart, upgrade atau restore dijalankan dalam sesi ini.

## 1. Deployment aktual dan urutan sasaran

| Komponen | Bukti aktual | Status |
|---|---|---|
| Target | `instalasi.sh:79–108`, Debian 13, Python 3.13, PostgreSQL 17, preflight disk/RAM/arsitektur | IMPLEMENTED pemeriksaan; clean-host success UNVERIFIED |
| API/worker | Unit systemd embedded `:275–319`, user/group sama, API loopback 8300, worker runworker | IMPLEMENTED; privilege split belum lengkap |
| Code/frontend | `/opt/microtix/backend`, shared venv, web-dist; sumber checkout | IMPLEMENTED, release artifact/staging PARTIAL |
| Persistent state | `/etc/microtix`, `/var/lib/microtix/storage`, PostgreSQL native, log terpisah dari backend tree | IMPLEMENTED pemisahan lokasi; complete backup UNVERIFIED |
| Caddy | Generated config, reverse proxy HTTP ke API, TLS/domain branch | IMPLEMENTED; public HTTPS/proxy scheme UNVERIFIED |
| WireGuard | Keypair dipertahankan, config render dan adopt public key | PARTIAL; render bukan apply/handshake/isolasi |
| Firewall | `setup_firewall:327–335` hanya check/warn | PARTIAL; required peer isolation belum dipasang oleh jalur ini |
| RADIUS | Optional MT_ENABLE_RADIUS=1, role/setup/render/restart | PARTIAL, blocker OPS-03 |
| Job drain/rollback/release pin | Tidak ditemukan mekanisme lengkap dalam installer/worker yang diperiksa | NOT IMPLEMENTED dalam scope ini |
| App Compose | ARCHITECTURE §1 dan OPERATIONS §3 | DOCUMENTED; CONFLICT dengan native systemd installer (DEC-01) |

Baseline kontrak tetap Compose sampai proposal DEC-01 diputuskan. Sketsa versioned-release di bawah adalah **PROPOSED** untuk mekanisme aktivasi sederhana; bentuk unit/container mengikuti keputusan deployment. Ia tidak mengubah privilege, tenant isolation, stack atau service per domain.

| Sasaran | Makna acceptance | Status saat audit |
|---|---|---|
| P0 Data integrity | Upgrade normal mempertahankan semua acknowledged transaction, key, artifact dan identity; tidak bergantung destructive restore untuk sukses | Belum dibuktikan |
| P1 Safe upgrade | Preflight, candidate validation, complete recovery set dan failure/recovery diuji | PARTIAL |
| P2 Minimal disruption | Hentikan hanya proses/operasi terdampak; ukur interruption aplikasi dan AAA terpisah | UNVERIFIED |
| P3 Near-zero downtime | Hanya untuk patch kompatibel setelah reload/activation/drain dibuktikan pada topologi aktual | Future conditional, bukan janji |
| P4 High availability | Failure domain kedua dan state/key/routing recovery nyata | Tahap berikutnya sesuai G4/G5, bukan baseline satu VPS |

P0–P4 tabel ini adalah urutan hasil operasional, bukan pengganti severity temuan. Single VPS tidak menjanjikan zero downtime saat reboot, gangguan DB/storage/network, atau migrasi locking.

## 2. Temuan installer dan operasi

Path tanpa prefix pada tabel berikut berarti `instalasi.sh` di baseline. Rincian lengkap setiap temuan, alternatif, blast radius dan commands disimpan dalam [review DevOps](../../report/devops-review/20261109T210133Z-planning-audit.md). **Tidak ada perbaikan diterapkan.**

| ID/risiko/status | Bukti konkret dan dampak | Solusi paling sederhana / alternatif |
|---|---|---|
| OPS-01 P1 CONFLICT | run() `:59–64` memakai `"$@"`, tetapi useradd/mkdir/chown/chmod `:139–147` diberikan sebagai satu string. Normal fresh install mencoba menjalankan nama executable yang mengandung argumen | Pass argv terpisah; pertahankan no-eval. run_sh hanya untuk shell composition nyata, tidak perlu bagi operasi ini |
| OPS-02 P1 CONFLICT | `:238` duplicate dependency list tanpa xhtml2pdf yang ada di pyproject; eager import documents/rendering. `:241–242` hanya copy backend, tidak runtime defaults/branding; settings `:158–159` mencari `/opt/microtix/docs` | Install dari deklarasi dependency existing dengan provenance; stage runtime assets yang dibaca. Alternatif MT_DOCS_DIR ke asset immutable yang ikut release, bukan checkout mutable |
| OPS-03 P1 PARTIAL | `:198–229` tidak membuat mtx_radius, setup_radius.py `:23–31` mensyaratkannya. Password render tidak diterapkan ke role. Config ke `/etc/freeradius/3.0/microtix` lalu restart stock service `:454–465`, tanpa wiring/validate; reconciler.py `:21–26,128` sandbox paths; listener loopback | Provision daemon role/password terbatas, persist, render ke layout produksi, validate dan activate service yang benar. Alternatif dedicated unit untuk bundle existing dengan listener tak konflik |
| OPS-04 P1 PARTIAL | `:236–250,635–639` ubah live venv/code dan migrate sebelum frontend build, tanpa staged candidate, drain atau recovery trap | Stage matched release, drain, migrate kompatibel, activate dan gate health. Alternatif maintenance window singkat dengan previous release, bukan blue-green wajib |
| OPS-05 P1 PARTIAL | `:627–631` local DB dump + pg_restore --list saja; rollback CLI/snapshot aplikasi tidak ada; file/key/config/off-host tidak ikut | Complete recovery manifest + restore drill terisolasi. Alternatif awal checkpoint quiesced terukur, bukan klaim PITR yang belum ada |
| OPS-06 P1 CONFLICT | health `:480–505` hanya set flags; summary `:539–578` dipanggil install saja; upgrade `:640` bisa log selesai, repair `:646–650` menutup kegagalan restart. curl -f bisa menerima redirect; readiness config/views.py `:77–85` hanya SELECT 1 | Satu mapping result/exit semua mode, exact JSON/status/TLS/schema check dan proxy-trust/Host yang benar. Jangan menonaktifkan TLS/Host validation untuk meloloskan probe |
| OPS-07 P1 CONFLICT | env `:174–191` berisi migrator URL/password, dibaca API `:285` dan worker `:308` | Pisah root-only migrator env dari runtime env; role existing dipertahankan. Tidak perlu vault service baru; rollback tidak boleh mengembalikan broad credential |
| OPS-08 P2; isolasi release P1 PARTIAL/CONFLICT | Topologi contract ≠ installer; WG config `:385–396` belum wired/apply nyata; firewall hanya warn; billing command ada tanpa timer; repair tidak membuat admin meski pesan menyarankan repair | DEC-01 eksplisit; dokumentasikan mode secara akurat, wiring host minimum dan scheduler idempoten. Alternatif penuhi Compose existing; jangan mengubah kontrak diam-diam |
| OPS-09 P2 PARTIAL | CI backend/FE/docs tidak menjalankan clean/repeat install, upgrade/rollback/restore, real daemon harness atau CHR | Evidence lane berbasis risiko pada disposable Debian host; keep expensive lab terpisah. Jangan menambah seluruh suite ke setiap docs PR |

Proxy perlu perhatian khusus: production `SECURE_SSL_REDIRECT=True`, Caddy meneruskan HTTP, dan `SECURE_PROXY_SSL_HEADER` tidak ditemukan. Generated ALLOWED_HOSTS dapat domain-only sementara loopback probe memakai 127.0.0.1. Ini **hipotesis kegagalan yang didukung konfigurasi**, bukan hasil uji redirect loop/400 aktual. Uji topology-faithful dan trusted forwarding, jangan percaya header arbitrary dari internet.

### Acceptance, urutan, downtime dan rollback tiap temuan

| ID | Acceptance sebelum ditutup | Urutan/impact, downtime dan recovery |
|---|---|---|
| OPS-01 | Clean Debian13 user/directories absent → install selesai; ulang → data/identity/ownership tetap | Awal patch installer, tidak menghapus state untuk retry; pada clean host tidak ada downtime layanan lama |
| OPS-02 | Artifact dijalankan tanpa source checkout: import/check/config/branding/PDF/startup service user berhasil; matched dependency provenance | Setelah 01 sebelum deployment; stage dahulu, retain previous release/venv |
| OPS-03 | Fresh role+DB, second run, config validation, actual daemon command/config/listener, real auth/accounting dan unknown-NAS/tenant negative, password sama sesudah upgrade | Setelah01/02; AAA window sampai terbukti; restore previous validated bundle/credential jika candidate gagal |
| OPS-04 | A→B→B; fault build/migrate/activation/worker; acknowledged data tetap, tidak mixed incompatible worker/schema, old app masih bekerja pada expanded DB | Setelah02/06 dan PA-002/003; drain + measured interruption; code rollback hanya kompatibel |
| OPS-05 | Restore ke target baru dari DB+blob+key+config; decrypt/count/reconcile/source sequence, VPN/NAS identity dan document download; corrupt/missing-key negative | Sebelum live upgrade; checkpoint write pause jika perlu; restore DB membutuhkan reconciliation writes setelah checkpoint |
| OPS-06 | DB down, API/worker stopped, invalid TLS/Host, redirect, stale schema → nonzero/explicit partial; sukses exact expected JSON public HTTPS | Sebelum klaim sukses; probes read-only, config validate sebelum reload; retain Caddy lama |
| OPS-07 | API/worker env dan readable files tanpa migrator creds; OS identity tidak membaca maintenance secret; migrator masih berfungsi controlled | Sebelum privilege sign-off; controlled restart; key encryption lama tetap, rollback tidak melonggarkan hak |
| OPS-08 | WG active path+handshake+peer isolation dua tenant LAN sama, billing timer menjalankan idempotent timezone-safe command, repair memenuhi tiap klaim | Keputusan deployment dahulu; network change via lab/window terotorisasi, targeted revert, keys/peers dipertahankan |
| OPS-09 | Release evidence menolak invocation/asset/health/interrupt defects nyata; SHA/version/exit/assertion/artifact tersedia | Disposable test target, tidak produksi; CI green saja bukan install success |

## 3. Arti CLI sekarang dan target yang diusulkan

| Mode aktual | Perilaku yang ditemukan | Batas dan target rencana |
|---|---|---|
| `install` (default tanpa argumen) | Preflight, dependency/user/secret/DB, backend+frontend, services/network/proxy/RADIUS optional, health, admin, summary | Memiliki blocker01/02/03; target idempoten dan resumable dengan checkpoint fase, tidak menghapus DB/data/key |
| `status` | systemctl/curl log | Read-only diagnostic; output DOWN belum result machine-readable lengkap; target non-mutating dan outcome jujur |
| `doctor` | Prerequisite/service/env checks, WG adopt --check | Bukan repair; target lengkap role/schema/config/health tanpa menulis secret atau mengaktifkan network |
| `repair` | Restart API/worker, setup Caddy, optional restart RADIUS, health | Bukan reinstall/dependency/migration/admin recovery. Target non-destructive targeted action, mandatory result nonzero saat gagal |
| `upgrade` | DB dump/list, deploy in-place, frontend, Caddy/WG, restart API/worker, health | Belum staged/rollback-safe; target §4–§7 |
| `--dry-run` / `<mode> --dry-run` | Parser positional, beberapa langkah dilewati/dicetak | Bukan bukti installability/permission/secret preservation atau restore; tidak mengklaim parser option lain |
| `rollback` / `restore` | Mode NOT IMPLEMENTED dalam installer | Nama command masa depan belum ditetapkan. Rencana recovery di sini bukan instruksi menjalankan mode yang belum ada |

Status akhir yang disyaratkan harus dipakai semua mode mutation, bukan hanya install. Kelanjutan setelah gagal membutuhkan hasil fase faktual; `set -e` saja tidak menyediakan rollback dan `|| true` tidak membuktikan perbaikan.

## 4. Proposed release workflow sederhana

**BASELINE:** preflight, expand/contract, drain/reconcile, complete backup dan evidence berasal dari ARCHITECTURE/OPERATIONS/CONTRACT. **PROPOSED implementation detail:** release directories dan activation pointer, tanpa infrastructure baru.

1. **Identifikasi.** Catat installed SHA/version, candidate SHA/digest, migration graph, schema compatibility, job payload/config snapshot version dan enabled features. Pastikan seluruh artefak dibangun dari satu revision yang dipin. Verifikasi disk untuk candidate+previous+checkpoint; dependency/network failure abort sebelum produksi berubah.
2. **Stage.** Candidate code+matched venv/frontend+runtime JSON/assets disiapkan terpisah. Contoh layout `/opt/microtix/releases/<sha>/` dengan pointer current/previous adalah usulan, bukan path yang sudah ada. Secret/blob/log/WG/RADIUS state tetap di lokasi persistent. Build tidak mengganti shared venv hidup, tidak bergantung checkout tersisa.
3. **Validasi pra-aktivasi.** Integrity/provenance, import/schema/API/config dan frontend live-mode gate; test memakai isolated DB/target. Schema migration belum dijalankan di DB live hanya untuk menguji artifact. Transitive Python dependency resolution/build tools juga direkam; exact direct pins saja tidak menjamin reproducibility penuh.
4. **Checkpoint dan drain.** Catat acknowledged boundary dan ambil recovery set konsisten. Pause admission/claim yang terdampak, drain bounded requests/jobs. Saat kontrak drain belum ada, pilih maintenance window eksplisit setelah implementasi drain; jangan menganggap kill proses sama dengan cancel tanpa efek. Audit in-flight/uncertain dan last applied revision.
5. **Migrasi kompatibel.** Gunakan maintenance credential terbatas, lock/time budget dan plan §5. Apabila old code tidak kompatibel dengan expanded schema, stop dan buat keputusan window/recovery dahulu; jangan switch dengan worker lama masih jalan.
6. **Aktivasi.** Pointer/code switch terkontrol lalu graceful lifecycle sesuai runtime yang disetujui. Atomic symlink hanya atomic untuk nama path; tidak membuat DB, process env dan frontend activation atomik. Existing proses mungkin memegang modul lama; lifecycle harus membuktikan versi aktif.
7. **Health-gated resume.** Verifikasi public/internal health, schema compatibility, worker progress, money/document dan tenant negatives. Keep mutation admission tertutup bila gagal. Hentikan hanya layanan yang berubah; patch UI/Tax tidak secara otomatis restart RADIUS/WG/DB.
8. **Observe dan close.** Rekonsiliasi current actor/policy/revision, resume bertahap, monitor queue age/uncertain, API/AAA errors/latency, DB locks/disk, document hashes, NAS revisions dan peer handshakes. Simpan previous release sampai rollback window ditutup eksplisit.

Gunicorn mendukung graceful TERM dan HUP dengan syarat terkait configuration/preload; itu opsi teknis, bukan bukti zero downtime deployment ini ([signal reference](https://gunicorn.org/signals/)). systemd unit, socket ownership, cwd, environment/key version dan graceful timeout aktual harus diuji. Blue-green hanya dipertimbangkan jika kebutuhan interruption terukur tidak dipenuhi alur sederhana dan resource/compatibility cukup; bukan default.

## 5. Database migration dan compatibility window

Setiap release menyatakan tepat pasangan versi **N/N−1** yang didukung beserta schema/job-payload/template/config versions. N/N−1 adalah minimum usulan pengujian rollback window, bukan janji semua versi lama didukung. Owner tabel menulis migration; parent lintas domain memberi dependency dan review; already-applied migrations tidak diedit ulang untuk menyembunyikan drift.

| Tahap | Kebijakan dan bukti |
|---|---|
| Expand | Additive table/nullable column/index atau constraint staged; old application masih berfungsi. Non-null/default/table rewrite diperiksa, bukan dianggap bebas lock |
| Migrate/backfill | Batch bounded/resumable/idempotent, checkpoint dan counts/tie-out; tidak satu transaction jutaan row. Rate/IO/lock budget diukur, parameter dipilih sesuai data nyata |
| Activate behavior | New app memahami representation lama selama backfill; dual read/write hanya bila diperlukan, owner dan expiry jelas; jangan dua aturan bisnis permanen |
| Validate | FK/CHECK negatives, RLS FORCE/WITH CHECK, runtime/facade privileges, money invariants, index state dan migration consistency |
| Contract | Drop/rename/tighten hanya sesudah old app/worker/pending payload dan rollback window tidak membutuhkannya; separate release/window bila locking/destructive |

Large accounting, health, audit dan job tables memerlukan SQL plan, ukuran data dan lock budget. PostgreSQL17 mendukung staged validation untuk constraint yang relevan dan concurrent index creation dengan batas transaksinya; pilih hanya bila diperlukan ([ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html), [CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)). Tentukan `lock_timeout`/statement budget per operasi berdasarkan rehearsal, tidak angka SLA rekaan. Non-atomic migration/concurrent index failure membutuhkan pemeriksaan invalid index dan retry plan; tidak cukup melihat migration row sudah ada.

| Compatibility pair | Gate |
|---|---|
| App N−1 + expanded schema | Seluruh jalur kritis lama dan tenant/permission tetap sah |
| App N + expanded schema saat backfill belum selesai | Tidak salah hitung/menyembunyikan data; fallback terdefinisi |
| Worker N−1 dengan job payload baru | Compatible atau menolak tanpa efek; tidak memakan job secara silent |
| Worker N dengan pending payload lama | Memproses/reconcile tanpa duplicate effect |
| Browser bundle lama + API N | Payload/status/error semantik tetap benar selama cache/rollout window |
| Rollback app N−1 + schema expanded | Berfungsi tanpa destructive DB reversal |
| RLS/facade role sebelum/sesudah migration | Fail-closed dan privilege minimum tetap |

Jika migration gagal, simpan schema state/SQL/migration record yang nyata; tentukan transaction rollback vs partial non-atomic work. Pilih forward repair kecil atau app rollback yang kompatibel. Reverse SQL yang drop schema/table atau mengembalikan facade lama tidak otomatis aman. Database restore adalah keputusan pemulihan, bukan retry installer normal.

## 6. Backup, restore, secrets dan rollback

**BASELINE — OPERATIONS §4, PRODUCT BKP-05:** recovery set mencakup DB/schema bisnis+radius/future ledger, WAL bila mekanisme tersedia, private blobs, key material/version, env/config, RADIUS config/NAS registry, WireGuard identity/peers dan datastore ACS ketika fase aktif. Off-host encrypted dengan key recovery terpisah. Runtime user tidak membaca root migration credentials. Existing keypair/encryption keys tidak dirotasi sebagai efek samping install/repair/upgrade.

`pg_dump` konsisten untuk database yang didump; global roles dan file eksternal perlu mekanisme tersendiri ([pg_dump17](https://www.postgresql.org/docs/17/app-pgdump.html)). `pg_restore --list` hanya catalog inspection, bukan restore data/invariant ([pg_restore17](https://www.postgresql.org/docs/17/app-pgrestore.html)). Audit ini tidak mengasumsikan WAL/PITR/off-host sudah terpasang.

Proposed recovery manifest berisi revision/config identifiers, hashes/sizes artefak, DB checkpoint/acknowledged sequence, schema/role versions, private key references, blob inventory/consistency boundary, source identity, expected counts dan pemilik recovery. Manifest publik tidak memuat secret values atau customer data. Untuk awal, quiesced checkpoint dapat menjaga kesesuaian DB+blob; target RPO existing memerlukan mekanisme incremental/WAL dan drill sebelum diklaim terpenuhi.

| Kondisi | Tindakan aman | Batas rollback |
|---|---|---|
| Stage/build/preflight gagal | Abort; current tetap berjalan | Tidak ada DB/code live berubah |
| Expand migration gagal atomik | Periksa rollback transaksi; current boleh lanjut hanya jika compatibility terbukti | Jangan hapus migration state dengan tebakan |
| Non-atomic migration/backfill gagal | Stop tahap terkait, inspect checkpoint/schema/index, resume bounded/forward repair | Reverse SQL dapat merusak data; perlu rencana khusus |
| Candidate unhealthy, schema kompatibel | Tahan writes/effects terkait, switch previous code+matched env, smoke dan reconcile | Tidak mengembalikan DB ke titik lama |
| Acknowledged writes sudah masuk setelah checkpoint | Pertahankan dan reconcile semua writes pada code rollback | Restore checkpoint tanpa replay/reconstruction berarti kehilangan data |
| Schema destructive/incompatible | Stop traffic mutation, keputusan forward repair atau DR yang disetujui | Tidak ada automatic destructive restore/drop |
| Router command mungkin terkirim | Quiesce old writer, readback target/revision, uncertain/recovery sesuai kontrak | Rollback aplikasi tidak membatalkan efek router |
| Missing/corrupt blob/key | Gagal gate, gunakan copy/key version recoverable, simpan evidence | DB restore saja tidak memulihkan artefak terenkripsi |

Urutan restore isolated sesuai OPERATIONS: key/config → DB+radius/roles dalam jaringan tertutup → gateway/FreeRADIUS setelah state valid → API+rekonsiliasi payment/policy/session → worker mutasi setelah authority/revision/effect diperiksa → artefak/ACS/modul relevan dipulihkan dan diverifikasi sebelum ekspos. Artefak yang dibutuhkan API sudah harus tersedia sebelum jalur download dibuka. Jangan memberi AAA dari state akun yang belum divalidasi.

Ukur RPO dari acknowledged sequence yang benar-benar pulih dan RTO dari gangguan mulai sampai core recovery+reconciliation selesai. Target existing RPO≤15 menit/RTO≤4 jam bukan hasil sesi ini dan bukan nol transaksi hilang. Upgrade normal memiliki target tidak kehilangan acknowledged data; DR setelah bencana mempunyai recovery budget terpisah.

## 7. Health, continuity dan failure scenarios

Liveness menyatakan proses mampu merespons. Readiness menyatakan kemampuan minimum release ini, termasuk schema dan dependency yang diperlukan; jangan overexpose detail publik atau membuat every optional dependency mematikan core. Worker heartbeat saja tidak membuktikan queue progress. Probe RADIUS/WG tidak digantikan API 200.

| Scope health | Bukti setelah candidate activation |
|---|---|
| Public API | Valid TLS/hostname, expected exact 200 JSON, no redirect loop, login/CSRF/permissions, active revision |
| DB/schema | Runtime least privilege, migration compatibility dan RLS negative, business invariant reads |
| Worker/outbox | Active version/payload compatibility, completed canary job, no stale lease, uncertainty preserved; delivery consumer hanya jika nyata |
| Storage/documents | Existing encrypted data decryptable, historical PDF/hash/download authorized, new document creation, free disk |
| Finance/billing | Paid/allocations tie-out, idempotency, daily issuance progress; no automatic activation |
| Router/WG | Existing identity/allowed-address/listener/peer count retained, handshake/target API readback; isolation dua tenant LAN sama |
| RADIUS | Daemon memakai validated bundle dan role, auth/accounting canary dan control sessions, no unexpected NAS/secret change |

Failure rehearsal mencakup disk full, backup corruption, missing key, stage failure, migration lock timeout/partial backfill, power/process kill tiap activation point, stale worker, duplicate request, provider outage, invalid Caddy/TLS, PostgreSQL reconnect, incompatible pending job, RADIUS config failure dan WG apply failure. Tabel [04](04_REVIEW_GATES.md) menetapkan acceptance dan evidence; semua rehearsal itu **NOT_RUN dalam audit ini**.

Patch UI/Tax tidak menimbulkan restart AAA/WG otomatis. Bila patch menyentuh daemon/peer/firewall, preserve validated config+identity, lakukan lab/window dan targeted rollback/readback. Existing customer sessions dan authentication baru adalah dua metrik berbeda; keduanya diukur, tidak diasumsikan kontinu.

## 8. Tahap delivery dan referensi resmi

Urutan minimum: OPS-01/02/06/07 artifact+privilege+honest status → PA-002/003 drain/effect lifecycle → OPS-03/08 verified host wiring → OPS-04/05 staged upgrade+full restore → OPS-09 release evidence. Perbaikan PA-001 uang tetap prioritas paralel terisolasi; deployment patch tidak membuktikan billing correctness.

Referensi vendor diperiksa 10 November 2026 WIB: [Django5.2 transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/) untuk transaksi pendek dan callback sesudah commit, [proxy scheme trust](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header), PostgreSQL17 links di atas, dan Gunicorn signal reference. `on_commit` bukan durable delivery pengganti outbox. Dokumentasi vendor menjelaskan mekanisme, bukan mensertifikasi konfigurasi MicroTix. Versi/pins existing tidak dianggap security-approved hanya karena tercatat; review advisori/dependency khusus diperlukan ketika patch dependency hendak dirilis.
