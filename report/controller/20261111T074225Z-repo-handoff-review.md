# MicroTix — Review repository terbaru dan handoff, 11 November 2026

**Peran:** ChatGPT controller / principal architecture reviewer.  
**Putusan:** NOT READY untuk deployment Production Beta; REQUEST CHANGES untuk PR #9 pada SHA yang diperiksa.  
**Batas tindakan:** read-only pada repository dan GitHub. Tidak memperbaiki aplikasi, mengubah kontrak, merge/push, memasang layanan, mengakses lingkungan produksi, atau menjalankan migrasi. Seluruh koreksi, tes aplikasi, commit/push dan integrasi berikutnya dilakukan executor di sandbox.

Dokumen ini adalah addendum review berbasis snapshot, bukan pengganti PRODUCT, CONTRACT, ARCHITECTURE, ACCEPTANCE, atau backlog. “Zero download” dipahami sebagai maksud meminimalkan downtime; kemampuan near-zero downtime belum terbukti. Tidak ada tanggal peluncuran baru yang ditetapkan.

## 1. Snapshot kanonis dan cabang yang benar-benar tersedia

Pemeriksaan ulang GitHub dilakukan pada **2026-11-11T07:42:25Z / 14:42 WIB**. Default branch aktual adalah main. Kondisi dapat berubah setelah waktu ini; executor wajib fetch dan mencatat SHA baru sebelum bekerja.

| Item | SHA lengkap | Status terbukti |
|---|---|---|
| [main](https://github.com/smahud/MicroTix_Project/tree/16085f825fef25ee4112d74b729c57e623b0bb05) | 16085f825fef25ee4112d74b729c57e623b0bb05 | Belum memuat PR #7/#8/#9 |
| [PR #9 — PA-001 pembayaran](https://github.com/smahud/MicroTix_Project/pull/9) | 3b20b562db37f5b59bc1e13df886264dd8bfa55c | OPEN, bukan draft; CI success; review ini REQUEST CHANGES |
| [PR #8 — planning audit](https://github.com/smahud/MicroTix_Project/pull/8) | 6bb57c9251f3a7a67b71b9523c01e507fdb1b601 | OPEN, DRAFT; docs CI failure |
| [PR #7 — SSTP Phase-2/lab](https://github.com/smahud/MicroTix_Project/pull/7) | d7fa35e5583bc36848e3b45497d2511739298c8a | OPEN; docs CI failure; belum menjadi fitur main |

Perubahan PR #9 terhadap main tepat lima path:

- backend/domains/billing/services.py
- backend/tests/integration/test_billing_payment_concurrency.py
- docs/progress.md
- report/LATEST_HANDOFF.md
- report/orchestrator/20261111T060010Z-pa001-payment-allocation-concurrency.md

Kode PA-001 berada pada commit a9eca6cb6cc2eef93b9aa711a039c08548c41644, dilanjutkan commit handoff 3b20b562db37f5b59bc1e13df886264dd8bfa55c. Tidak ada perubahan installer, job engine, security, frontend, migrasi atau deployment dalam PR tersebut. Temuan baseline pada komponen-komponen itu belum ditutup oleh PR #9.

**NOT FOUND pada main dan kandidat PR #9:** docs/planning_audit/ dan docs/planning_mvp/. Lima dokumen planning_audit tersedia pada PR #8, belum merged. Jangan menyatakan dokumen tersebut sudah menjadi kontrak main, atau mengarang isi planning_mvp yang tidak tersedia. PR #7 mempunyai tambahan lab sendiri; keberadaannya bukan bukti lab sudah dijalankan.

## 2. Handoff terakhir: kemajuan dan koreksi wajib

Handoff sesi terbaru adalah [report/LATEST_HANDOFF.md pada kandidat PR #9](https://github.com/smahud/MicroTix_Project/blob/3b20b562db37f5b59bc1e13df886264dd8bfa55c/report/LATEST_HANDOFF.md), sesi 11 November 2026. Handoff pada main masih historis. Gunakan kedua sumber untuk membedakan keadaan kanonis dan pekerjaan belum merged.

Yang dapat diakui:

- PA-001 memperkenalkan row lock invoice sebelum membaca outstanding; pendekatan ini sesuai kebutuhan integritas dengan perubahan kecil.
- Empat tes PostgreSQL baru memeriksa dua payment, agregat alokasi, urutan beberapa invoice, serta validasi sebelum mutasi.
- Executor melaporkan reproduksi bug lama dan sensitivitas tes; laporan itu tersedia pada path orchestrator di atas.
- SHA main, keberadaan PR terbuka, simulator vs perangkat nyata, serta batas lingkungan sandbox sudah disebut.
- Executor secara tepat tidak melakukan deployment sesudah push.

Koreksi wajib pada handoff:

- Baris 15, 49, 53, dan 77 masih menyatakan penahan Beta hanya host/Gate A/G, “BUKAN pekerjaan kode”, atau “penahan tunggal”. **CONFLICT:** terdapat defect kode installer, job lifecycle, permission/idempotency dan gap recovery yang belum ditutup.
- PA-001 tidak boleh berstatus accepted/closed sebelum temuan UUID dan kompatibilitas kuitansi pada §4 diperbaiki serta direview.
- Klaim “rollback penuh” harus dibatasi: tes saat ini gagal sebelum mutasi, sehingga belum membuktikan rollback setelah write.
- CI PR #7 telah ditelusuri dalam review ini: job docs gagal karena manifest mismatch; backend/frontend berhasil. Ini bukan bukti SSTP gagal runtime, juga bukan bukti SSTP berhasil di perangkat.
- “Timer issue_due_invoices dipasang installer” tidak didukung artefak timer/installer yang ditemukan. Ada command penagihan, tetapi lifecycle scheduler belum terbukti.

Handoff berikutnya harus memisahkan implemented, verified_local/integration, verified_lab, release_enabled, serta code blocker dari environment blocker.

## 3. Bukti pengujian yang benar-benar tersedia

Controller membaca metadata jobs dan log terdekode, tidak menjalankan suite aplikasi sendiri.

| Kandidat | Run CI | Bukti aktual | Batas bukti |
|---|---|---|---|
| PR #9, 3b20b562 | [42970045333](https://github.com/smahud/MicroTix_Project/actions/runs/42970045333) | docs/backend/frontend success; backend **376 passed, 1 skipped, 3 warnings**; frontend **66 tests / 9 files passed**, typecheck/lint/i18n/build berhasil | Skip karena binary freeradius tidak tersedia; tidak membuktikan installer, daemon RADIUS, browser E2E, CHR, DR atau kapasitas |
| PR #8, 6bb57c92 | [42703002243](https://github.com/smahud/MicroTix_Project/actions/runs/42703002243) | backend/frontend success; docs FAIL, “manifest mismatch; review changed docs, then run --refresh explicitly” | Perlu review perubahan dokumen dan refresh manifest secara eksplisit oleh pemilik branch; jangan bypass validator |
| PR #7, d7fa35e5 | [42388511877](https://github.com/smahud/MicroTix_Project/actions/runs/42388511877) | backend/frontend success; docs FAIL dengan pesan manifest yang sama | Review penuh SSTP/privilege/network dan lab tetap belum dibuktikan oleh status CI |
| main, 16085f82 | [42285141174](https://github.com/smahud/MicroTix_Project/actions/runs/42285141174) | Historical CI success pada SHA kanonis yang sama | Tidak menghapus defect yang belum tercakup tes |

Klaim executor: baseline 372 passed/1 skipped; fixed 376 passed/1 skipped; 3/4 tes gagal ketika koreksi dilepas; fixed diulang tiga kali. **Status:** REPORTED oleh executor; hasil fixed suite juga dikonfirmasi log CI. Controller tidak menjalankan ulang reproduksi maupun memverifikasi seluruh interleaving yang dilaporkan.

Barrier tes terjadi sebelum masuk tenant_scope; PID PostgreSQL berbeda membuktikan koneksi berbeda, belum membuktikan bahwa interleaving target/lock wait terjadi pada setiap run. Green CI berlaku untuk assertions yang ada, bukan semua input atau keseluruhan readiness.

## 4. Register temuan review terbaru

Seluruh path/line di bawah mengacu kandidat PR #9, kecuali dinyatakan lain. File selain billing/services dan file laporan baru identik dengan baseline main. Dampak runtime yang belum direproduksi diberi label eksplisit.

### REV-1111-01 — P1: urutan lock memakai teks UUID mentah

**Terkait:** PA-001. **Status:** CONFLICT; terbukti bentuk kode, konsekuensi deadlock UNVERIFIED runtime sesi review.

**Bukti:** billing/services.py:558–580 menggabungkan string input lalu mengunci sorted(merged). Django UUIDField menormalkan nilai ketika menyiapkan query, setelah urutan string ditentukan. Permintaan A lowercase + B uppercase dapat mengunci B→A; permintaan canonical lowercase mengunci A→B. Representasi berbeda dari satu UUID juga tidak digabung oleh dictionary awal.

**Dampak:** deadlock/error pada invoice bertumpang tindih; alias satu invoice dapat memicu uniqueness error. Constraint pasangan payment/invoice dan atomic transaction membatasi efek: review ini **tidak mengklaim duplikasi allocation berhasil committed**.

**Solusi minimum:** validasi UUID, canonicalize sebelum merge dan sort; invalid input menjadi ApiError.validation/422. Alternatif strict canonical-only input perlu evaluasi compatibility; jangan diam-diam menolak representasi yang sebelumnya diterima.

**Impact/urutan:** billing → documents/audit/jobs; koreksi PR #9 sebelum diterima. Tidak perlu model baru, queue baru atau migrasi hanya untuk normalisasi ini.

**Acceptance:** uppercase/lowercase, compact/hyphenated aliases; satu identitas teragregasi satu kali; invalid UUID 422; dua koneksi dengan contention yang dikendalikan membuktikan urutan identitas konsisten dan paid_amount = SUM(alokasi committed).

**Downtime/rollback:** patch aplikasi; saat nanti dirilis gunakan drain sesuai runbook. Revert ke main akan membuka kembali PA-001, sehingga bukan fallback finansial aman. Utamakan fix-forward atau hentikan verifikasi dana sampai versi aman aktif.

### REV-1111-02 — P2: sorting mengubah nama dan bahasa kuitansi

**Terkait:** PA-001 / compatibility. **Status:** IMPLEMENTED behavior change, runtime kasus lintas pelanggan NOT_RUN.

**Bukti:** _parse_allocations kini mengembalikan hasil urutan UUID (:567–580); verify_payment memakai allocations[0] untuk customer_name dan locale (:633–643). Beberapa invoice pelanggan berbeda dalam tenant yang sama belum dilarang oleh jalur ini.

**Dampak:** kuitansi immutable dapat memakai pelanggan/bahasa dari UUID terkecil, berbeda dari invoice pertama yang diminta. Ini perubahan semantik, bukan sekadar urutan baris dokumen.

**Solusi minimum:** akuisisi lock menurut UUID canonical terurut, lalu kembalikan hasil menurut urutan input teragregasi semula. Alternatif kebijakan satu customer per payment merupakan keputusan produk terpisah, tidak dibutuhkan untuk patch ini.

**Acceptance/urutan:** tes dengan UUID tetap dan nama/locale pelanggan berbeda membuktikan header, bahasa dan presentasi tetap kompatibel; satu packet dengan REV-1111-01.

**Downtime/rollback:** sama dengan patch PA-001; tidak merender ulang dokumen terbit secara diam-diam. Data uji sintetis saja.

### REV-1111-03 — P2: bukti rollback dan race perlu dipertegas

**Status:** CONFLICT pada klaim bukti; implementasi atomic wrapper memang ada.

**Bukti:** test_billing_payment_concurrency.py:328–354 memicu error di _parse_allocations sebelum writes layanan :614 onward. Barrier :135–139 mendahului tenant_scope.

**Dampak:** tes berguna dapat lolos tanpa membuktikan post-write rollback atau contention yang dimaksud; review tidak boleh melebihkan cakupannya.

**Solusi minimum:** pertahankan tes validasi, koreksi nama/klaim, tambah satu kegagalan terkontrol sesudah mutasi DB dan tangkap error di luar tenant_scope; cek allocation/payment/receipt-row/audit/outbox rollback. Bedakan orphan file dari rollback DB. Tambah contention PostgreSQL terkontrol; hindari sleep sebagai satu-satunya pengatur race.

**Acceptance:** failure point jelas, assertions before/after lengkap, tes sensitif terhadap defect dan tidak hang; HTTP idempotency/actor permission tetap packet PA-006/PA-003 terpisah.

**Downtime/rollback:** tidak ada, perubahan tes/laporan dan koreksi kecil yang relevan.

### REV-1111-04 — P1: clean installer dan packaging belum dapat dipercaya

**Terkait:** OPS-01/02. **Status:** IMPLEMENTED tetapi defective secara statis; rehearsal NOT_RUN.

**Bukti:** instalasi.sh:59–64 menjalankan argumen langsung; create_users_dirs:139,142,144–147 memasukkan satu string berisi command lengkap. Shell akan mencari nama executable yang mengandung spasi. Dependency installer :238 menduplikasi daftar pin dan tidak menyertakan xhtml2pdf yang diwajibkan pyproject.toml:23 dan diimpor documents/rendering.py:29–31.

**Dampak:** instalasi baru berpotensi gagal sebelum aplikasi dapat dipakai; startup/render PDF tidak lengkap meski dependency CI terpasang.

**Solusi minimum:** argumen terpisah dan dependency dari manifest authoritative; uji paket release sebenarnya. Jangan menambahkan framework deployment baru.

**Acceptance:** disposable Debian 13 dengan systemd: install bersih, install ulang, startup API/worker, invoice/PDF, secret/data tidak berubah saat pengulangan; command+exit/evidence tersimpan.

**Urutan/rollback:** S4 sebelum host rehearsal. Tidak menyentuh host produksi sekarang; rollback eksperimen adalah membuang VM uji milik run, bukan menghapus data target.

**Disposisi severity:** reviewer operasi memberi P0 sebagai clean-install blocker; controller mengklasifikasikan P1 untuk register lintas domain karena belum ada bukti kerusakan data/insiden produksi. Tetap menghalangi deploy.

### REV-1111-05 — P1: upgrade/repair dapat memberi exit sukses palsu dan mengubah HTTPS

**Terkait:** OPS health/config. **Status:** PARTIAL/CONFLICT.

**Bukti:** gate_fail hanya merekam status (:480), summary menerjemahkannya ke exit (:539–578), tetapi upgrade/repair tidak memanggil summary (:635–649,675–676). setup_caddy memakai MT_DOMAIN dari caller (:404,417); repair tidak memuat konfigurasi persisten dahulu. /health/ready hanya SELECT 1 (config/views.py:77–85).

**Dampak:** otomasi dapat menyebut upgrade sehat ketika gate gagal; repair tanpa ekspor domain dapat mengganti site menjadi :80; DB reachable belum berarti schema compatible.

**Solusi minimum:** load konfigurasi persisten tervalidasi, status/exit konsisten semua mode, health wait bounded, readiness mencakup kebutuhan release.

**Acceptance:** DB/worker mati, migration hilang, HTTPS invalid → nonzero sesuai kontrak; domain, kunci dan konfigurasi tetap saat repair berulang. Status/doctor tetap read-only; repair menjelaskan scope mutasi.

**Urutan/downtime/rollback:** S4; uji failure injection pada VM disposable. Simpan konfigurasi terakhir valid; aktivasi gagal tidak mengganti release sehat. Ukur gangguan, jangan menjanjikan nol.

### REV-1111-06 — P1: worker belum aman untuk drain, crash dan stale writer

**Terkait:** PA-002/003, OPS-04. **Status:** PARTIAL/CONFLICT, failure scenarios runtime NOT_RUN review ini.

**Bukti:** runworker.py:32–49 belum memiliki drain; jobs/engine.py:227–278 membungkus I/O handler dalam tenant_scope→atomic; writes :213,288,311 belum difence seperti _fenced_save. Upgrade menyalin code/venv dan migrate ketika proses masih aktif (instalasi.sh:241–250,635–639). Recovery expiry hanya executing/verifying (:340–351).

**Dampak:** transaksi/lock panjang, stale terminal overwrite, uncertain effect, klaim job terlantar, upgrade menjalankan campuran versi. Skalakan worker sebelum invariant ini ditutup akan menambah risiko.

**Solusi minimum:** stop claims; lease/epoch/expected-state pada setiap write; authority mutakhir sebelum efek; transaksi pendek; readback efek ambigu; recovery state awal; drain dengan deadline dan fallback jujur. Gunakan engine PostgreSQL yang ada.

**Acceptance:** crash di tiap state, lease transfer, old writer, revoke-after-enqueue, cancel-in-flight, deploy saat job berjalan; tidak ada duplicate effect/false cancel/stale outcome dan tidak blind-retry router.

**Urutan/downtime/rollback:** S2 sesudah koreksi PA-001; uji API/worker versi sebelumnya terhadap payload/state kompatibel. Drain singkat mungkin diperlukan; pekerjaan uncertain ditahan untuk rekonsiliasi sebelum resume, tidak diputar ulang otomatis.

### REV-1111-07 — P1: restore lengkap dan pemisahan secret belum terbukti

**Terkait:** OPS-05/07. **Status:** PARTIAL; restore end-to-end UNVERIFIED.

**Bukti:** upgrade hanya local pg_dump + pg_restore --list (:627–631). Runtime EnvironmentFile juga berisi MIGRATE_DATABASE_URL/password privileged (:178,186,285,308); RADIUS renderer menerima password melalui argv (:456). Router backup simulator manifest bukan platform DR.

**Positif yang terbukti:** CSPRNG dan preservation env/WireGuard key memang ada (:153–192,343–375); tidak boleh disebut sama sekali tidak ada.

**Dampak:** archive listing tidak membuktikan restore; kehilangan VPS bisa kehilangan backup; kompromi runtime bisa membuka secret migrator; argumen proses dapat mengungkap credential.

**Solusi minimum:** pisahkan migrator secrets dan hapus secret argv; recovery set DB/WAL/blob/key/config terenkripsi off-host sesuai OPERATIONS §4. Tidak perlu database per domain.

**Acceptance:** restore terisolasi mengembalikan acknowledged financial records, blob yang dapat didekripsi, radius/network registry, izin dan kunci; worker mutasi baru dibuka setelah rekonsiliasi. Ukur RPO/RTO aktual.

**Urutan/downtime/rollback:** S4 sebelum produksi; rollback aplikasi tidak menggantikan restore. Restore DB ke titik lama dapat menghilangkan transaksi setelah backup; jangan lakukan otomatis pada sistem hidup.

### REV-1111-08 — P1: keputusan topology deployment belum konsisten

**Terkait:** DEC-01. **Status:** CONFLICT, belum menjadi keputusan approved.

**Bukti:** ARCHITECTURE §1 / OPERATIONS §3 menetapkan aplikasi Compose, PostgreSQL native, proses privileged terpisah. Installer membentuk API/worker native dengan akun/env sama (:275–319); artefak Compose tidak ditemukan pada inventory deployment. Firewall hanya memeriksa/memperingatkan (:327–335); aktivasi WireGuard masih manual (:395–396).

**Solusi minimum:** ikuti desain authoritative; atau ajukan keputusan sempit mempertahankan native systemd dengan bukti biaya/manfaat dan kontrol isolasi setara. Controller tidak memilih perubahan kontrak tanpa persetujuan pemilik.

**Acceptance:** satu topology yang disetujui, satu runbook/installer sesuai; API tanpa root/CAP_NET_ADMIN/Docker socket; process privileges dan peer isolation diuji setelah reload.

**Urutan/downtime/rollback:** keputusan dibutuhkan sebelum menetapkan rehearsal S4; PA-001 dan pekerjaan independen S2 tetap dapat berjalan. Jangan memigrasikan deployment yang belum pernah dipasang; uji dari VM kosong.

### REV-1111-09 — P1: scheduler invoice belum memiliki lifecycle operasional

**Status:** command IMPLEMENTED, scheduler NOT IMPLEMENTED dalam installer/unit yang diperiksa.

**Bukti:** issue_due_invoices.py:18–19 menyatakan installer memasang timer 01:00; pencarian artefak tidak menemukan timer, OnCalendar, panggilan installer atau service scheduler.

**Dampak:** command bisa benar tetapi invoice berkala tidak terbit otomatis; upgrade bisa melewatkan jadwal/catch-up.

**Solusi minimum:** pasang scheduler kecil sesuai topology yang disetujui; idempotent run/catch-up, timezone dan monitoring. Jangan menambah platform scheduling baru.

**Acceptance:** timer benar-benar mengeksekusi command, miss/restart/catch-up tidak menggandakan invoice, multi-tenant scope aman, status/doctor memeriksa timer.

**Urutan/downtime/rollback:** S4 untuk billing yang diaktifkan; tes timer sandbox. Matikan trigger saat rollback bila compatibility belum terjamin; business uniqueness tetap dijaga.

### REV-1111-10 — P1: handoff menyembunyikan code blockers

**Status:** CONFLICT dokumentasi vs source; tidak memerlukan akses server untuk diperbaiki.

**Bukti:** handoff :15,49,53,77 dibanding REV-1111-04–09 dan register planning audit PR #8.

**Solusi minimum:** koreksi report/LATEST_HANDOFF.md dan docs/progress.md setelah verifikasi; jangan mengubah requirements agar cocok dengan implementasi. Cantumkan PR9 review findings dan open decision secara spesifik.

**Acceptance:** tidak ada klaim “host-only/penahan tunggal” selama code blockers ada; exact SHA, hasil tes, remaining blockers dan next packet konsisten. S0/S1 belum dinyatakan selesai seluruhnya.

**Urutan/downtime/rollback:** satu commit laporan dengan koreksi PR9; tanpa downtime. Pertahankan laporan historis, tidak overwrite evidence lama.

### REV-1111-11 — P1: kontrak security/idempotency/seleksi masih terbuka

**Terkait:** PA-003–008, PA-011/012 dari audit baseline; tidak semua merupakan temuan baru.

**Bukti yang dicek ulang:** jobs/views.py:70–97 memakai ActiveTenantApiView tanpa permission operasi; common/idempotency.py membentuk/query scope tanpa principal meskipun menyimpan principal; frontend ImportRouterPage.tsx:94–106 menyimpan selected set lalu commit tanpa meneruskannya; subscriptions/upload.py:94 onward memakai MT_SCAN_MODE default disabled tanpa guard produksi.

**Dampak:** membership saja belum resource authority; replay/race belum memenuhi one-logical-effect; seleksi UI dapat berbeda dari efek; upload bisa tanpa scanner. Review ini tidak menjalankan exploit atau membuktikan kebocoran lintas tenant aktual.

**Solusi minimum:** selesaikan owner service/permission dan actual selected-set contracts, principal-scoped idempotency dan production fail-closed scanner. Verifikasi PA-004/005/007/011 terhadap SHA aktif sebelum mengerjakan packet masing-masing.

**Acceptance:** Viewer denied; revoke-after-enqueue; principal/tenant/resource isolation; concurrent replay satu efek; snapshot 201 akun pilih1→adopt1, empty/null/missing berbeda; scanner down menolak upload produksi. Finance operator SaaS tetap terpisah dari billing tenant.

**Urutan/downtime/rollback:** S1 PA-006, S2 security, S3 UI/quota. Buat patch kecil berbasis invariant, tidak rewrite semua domain. Migration/index idempotency bila perlu memakai compatibility window, bukan menghapus key lama.

### REV-1111-12 — P2 sekarang / gate kapasitas: target beban belum terbukti

**Status:** DOCUMENTED target, benchmark UNVERIFIED.

**Bukti:** CONTRACT §7 menetapkan 1.000 tenant × sekitar 1.000 client online. OPERATIONS §6 profil 10/100/1.000 tenant menggunakan 300 service/tenant. Monitoring controller/collector dan workload agregat vs selected real-time belum memiliki bukti juta client pada snapshot ini.

**Solusi minimum:** pertahankan target asli; definisikan workload online/AAA/accounting/polling yang cocok, observability dan resource budget; benchmark bertahap. Profil 300 bukan pengganti target 1.000, tetapi valid sebagai tahap awal.

**Acceptance:** laporan kapasitas menyebut tenant, online clients, router, auth/accounting rate, collector interval/freshness, selected real-time concurrency, DB locks/pool/IO, latency/error/fairness dan soak; hasil hanya berlaku pada konfigurasi yang diuji.

**Urutan/downtime/rollback:** S6/kesiapan peningkatan kapasitas sesuai G4/G5. Beta terbatas tidak wajib menunggu kapasitas maksimum jika feature scope/gates terpenuhi. Jangan load test produksi atau mengklaim juta client tanpa data.

## 5. Penilaian modularitas pada snapshot aktual

**Fondasi modular monolith ada, invariant modular belum seluruhnya ditegakkan.** Inventory AST read-only di PR #9 menemukan 15 direktori termasuk common, 100 file Python runtime di bawah domains setelah mengecualikan migrations/management, dan 50 directed import edges antar domain. Deferred imports tetap dihitung; dynamic imports/string references tidak seluruhnya terwakili. Graph import bukan ukuran pelanggaran secara otomatis.

| Source | Domain target yang diimpor |
|---|---|
| audit | common |
| backups | common, config, jobs, network, tenancy |
| billing | audit, common, customers, documents, jobs, subscriptions, tenancy |
| common | i18n, identity, jobs, tenancy |
| config | common, i18n |
| customers | audit, common, jobs, network, subscriptions |
| documents | common, i18n |
| i18n | Tidak ditemukan import domains lain dalam metode ini |
| identity | common, i18n, subscriptions, tenancy |
| jobs | common |
| monitoring | common, config, network |
| network | common, config, customers, jobs, radius, tenancy |
| radius | backups, common, customers, jobs, network |
| subscriptions | audit, common, jobs, network, tenancy |
| tenancy | Tidak ditemukan import domains lain dalam metode ini |

Contoh dependency sah: billing membaca service dan memanggil documents untuk dokumen; monitoring membaca health network. Contoh perlu kontrak: customers/services.py:647,853 langsung mengubah DiscoveryObject milik network; common membawa dependensi identity/jobs; hubungan customers↔network dan network↔radius memerlukan review efek/ownership. Siklus graph tidak membuktikan import crash.

Persyaratan praktis untuk agent implementasi:

- Satu owner per model/table dan migration; mutasi lintas owner melalui entry point kecil pemilik. Read-only cross-domain boleh bila field/tenant scope dan compatibility jelas.
- Service uang mengikat validasi, write, audit dan outbox dalam transaksi; I/O eksternal dipisahkan dengan state durable, fencing dan verifikasi yang sesuai. Jangan memindahkan rendering ke async secara serampangan jika mengubah kontrak immutable receipt.
- Tenant context transaction-local, runtime RLS nonprivileged, composite reference dan permission resource; worker memeriksa authority saat eksekusi. Directory domain tidak cukup.
- Jobs/outbox yang ada dipertahankan; dispatch_outbox saat ini hanya menandai event. Delivery/ack/replay wajib sebelum consumer nyata mengandalkannya.
- Frontend tetap feature folders + typed API + backend flags. Uji efek seleksi/filter/cache lintas tenant dan role, bukan sekadar render komponen.
- Targeted boundary tests/checks pada owner writes dan dependency berisiko lebih berguna daripada repository abstraction atau framework plugin menyeluruh.
- Finance/ledger/tax belum menjadi domain implementasi lengkap yang ditemukan. Subscription operator, billing tenant dan calon Tax harus mempunyai economic-entity/book/source-event yang terpisah; issued documents immutable dan retry deduplicated. Tidak membuat implementasi Tax atau mengubah planning_mvp dalam review ini.

## 6. Deployment, upgrade dan standar yang harus dibuktikan

Standar berikut adalah kriteria verifikasi relevan, bukan klaim sertifikasi atau persyaratan seluruh fitur masa depan sebelum Beta terbatas.

| Sasaran | Baseline sekarang | Bukti wajib sebelum klaim |
|---|---|---|
| Mudah deploy | Installer ada; semantic command/dependency gaps | Install/reinstall Debian13 disposable, artefak lengkap, smoke API/UI/PDF/RADIUS sesuai scope |
| Mudah patch/upgrade | In-place overwrite+migrate; belum stage/drain | Immutable candidate, config/secrets persisten, preflight, drain, activation gated, rollback/reconciliation drill |
| Gangguan minimal | Tidak ada angka downtime hasil rehearsal | Ukur API errors/interruption, job drain, migration lock, AAA/new-login dan sesi kontrol sebelum/selama/sesudah patch |
| Aman data | Atomic/RLS fondasi; PA-001 partial; DR belum terbukti | Invariant keuangan/tenant, retry/crash, restore DB+blob+keys, no lost acknowledged effects pada upgrade normal |
| Scale up | Modular code + PG job engine; max workload belum diuji | Budget pool/worker/query/collector, telemetry, load/soak; ukur sebelum tambah infrastruktur |
| Industri/security | Kontrak merujuk ASVS5, least privilege, API versioning | Applicable negative tests, secret separation, CSRF/XSS/upload/SSRF sesuai scope; tidak menyebut full compliance dari CI hijau |

Strategi minimum yang diusulkan, belum diklaim sudah ada:

1. Tentukan topology approved (DEC-01), candidate SHA/artifact digest dan konfigurasi persisten.
2. Build terpisah dari runtime; jangan overwrite release aktif. Gunakan artefak/release immutable sesuai topology terpilih. Native versioned directories hanyalah salah satu opsi jika native disetujui; bukan keputusan otomatis mengganti Compose.
3. Preflight kapasitas, identity/config, backup dan restore readiness, migration plan, payload/schema compatibility.
4. Stop job claims, drain bounded; pekerjaan ambigu menjadi uncertain/recovery_required, tidak blind replay. Pertahankan layanan RADIUS/network ketika patch aplikasi tidak membutuhkan perubahannya.
5. Expand schema yang kompatibel; backfill bounded/resumable terpisah; validate; contract baru setelah compatibility window berakhir. Set lock/statement budgets dan rehearsal pada data representatif.
6. Start candidate, schema/readiness+smoke tests, baru aktivasi; graceful shutdown versi lama. Single-VPS mungkin memerlukan window gangguan pendek. Ukur, jangan beri label zero downtime tanpa bukti.
7. Rollback code hanya jika schema/payload tetap kompatibel; destructive migration memerlukan fix-forward/recovery plan. Restore backup bukan default rollback aplikasi.
8. Smoke dan rekonsiliasi payment/jobs/AAA, verifikasi secrets/WireGuard peers/customer sessions, backup masih berjalan. Catat UTC duration, expected/actual, abort point dan cleanup.

Referensi primer yang diperiksa:

- [Django 5.2 select_for_update](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update): row locks bertahan sampai transaksi selesai; relevan untuk PA-001 dan render di dalam transaksi.
- [Source Django UUIDField](https://github.com/django/django/blob/stable/5.2.x/django/db/models/fields/__init__.py) dan [Python UUID](https://docs.python.org/3.13/library/uuid.html): representasi dapat dipetakan ke identitas UUID yang sama; canonicalization dilakukan sebelum pengurutan bisnis.
- [PostgreSQL17 ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html): lock berbeda per operasi; jangan menganggap semua migration online.
- [Build/release/run](https://12factor.net/build-release-run) dan [graceful shutdown](https://12factor.net/disposability): praktik release terpisah dan proses yang dapat dihentikan dengan aman. Tidak mengharuskan broker/service tambahan.
- [OWASP ASVS](https://asvs.owasp.org/): referensi kontrol security relevan, bukan sertifikasi MicroTix.

## 7. Target dan timeline yang didukung bukti

Sumber kontinuitas: master prompt controller sandbox-first yang dibaca versi saat ini, CONTRACT, IMPLEMENTATION_PLAN, ACCEPTANCE dan OPERATIONS pada SHA yang diperiksa. Penelusuran konteks tidak menemukan tanggal kalender peluncuran Beta yang disepakati. Target “segera” bukan tanggal atau estimasi durasi. Karena itu tidak ada klaim terlambat/tepat jadwal maupun janji “selesai dalam X hari”.

| Tahap yang disepakati | Kondisi saat ini | Keluar tahap bila |
|---|---|---|
| S0 — baseline/docs | PARTIAL | Baseline SHA jelas; konflik/docs manifest PR8 selesai tanpa mengubah kontrak diam-diam |
| S1 — uang/idempotency | PARTIAL | PA-001 koreksi diterima, PA-006 dan invariant relevan teruji; bukan hanya suite hijau |
| S2 — jobs/security/enrollment | Belum terbukti selesai | Fencing/permission/MFA/enrollment dan negative tests relevan lulus |
| S3 — quota/UI boundaries | Belum terbukti selesai | Selected-set, quota race, tenant-local draft/API contract terbukti |
| S4 — installer/recovery | Belum terbukti selesai | DEC-01 resolved; VM uji bersih+upgrade/failure/restore/rollback |
| S5 — jaringan/lab | PARTIAL/simulator; real integration belum lengkap | Real daemon tests dan CHR/GNS3 gates sesuai fitur; licensed assets/resource tersedia |
| S6 — integrated candidate | Belum tercapai | Semua packet relevan committed+pushed, integrasi semantik, combined CI/regression dan independent review exact SHA |

Durasi nyata yang **sudah tertulis dalam dokumen**, bukan tambahan timeline baru:

- ACCEPTANCE §6: pilot awal 1 tenant / 1 router / 50 service, minimum **7 hari** dan mencakup siklus relevan.
- OPERATIONS §2: cutover B3 minimal **1.800 detik**, B4 **86.400 detik**, sesuai fitur dan tahap yang diaktifkan.
- OPERATIONS §6: soak **8 jam** pada profil 10/100 tenant, **24 jam** pada 1.000; warmup/ramp/steady dan minimum samples mengikuti dokumen.
- OPERATIONS §4: **RPO≤15 menit, RTO≤4 jam merupakan target**, belum hasil drill atau SLA. RPO target bukan izin kehilangan transaksi saat upgrade normal.

Durasi ini tidak dijumlahkan menjadi tanggal Beta rekaan; beberapa gate paralel, sebagian hanya berlaku saat fitur/kapasitas diaktifkan. Pilot minimal7hari tidak menghalangi instalasi kandidat ke lingkungan Beta terkontrol setelah gate predeploy relevan lulus; ia membatasi klaim PILOT_VERIFIED/public readiness sesuai scope. Keputusan rollout dan scope harus eksplisit.

## 8. Instruksi berikutnya untuk executor — sandbox only

Gunakan master prompt sandbox-first yang sudah berlaku, lalu tambahkan packet berikut. Jangan mengirim seluruh percakapan atau informasi akses deployment. Agent hanya membutuhkan repo, SHA, diff, requirements dan bukti terkait packet.

**Packet aktif: koreksi PR #9 dan handoff; jangan beralih ke deploy atau memperluas fitur.**

1. Fetch main dan PR9 aktual; catat SHA, worktree/status, preservation perubahan pihak lain. Jika SHA berubah, review delta terlebih dahulu.
2. Baca CONTRACT, bagian billing/transactions/API/I18N relevan, laporan PA-001 dan temuan REV-1111-01–03/10.
3. Gunakan branch PR9 yang dimiliki executor atau branch lanjut yang jelas; jangan overwrite PR7/8.
4. Validasi/canonicalize UUID sebelum merge dan lock sort. Kunci dalam urutan canonical; kembalikan hasil dalam urutan permintaan teragregasi semula.
5. Tambah regresi alias/malformed UUID, multi-customer locale/header compatibility, post-write rollback dan contention PostgreSQL terkontrol. Tetap pertahankan invariant dua payment dan paid=sum allocations.
6. Jalankan targeted tests PostgreSQL nyata, lalu regression/backend/docs dan checks frontend yang relevan melalui CI. Catat versi, command, exit, assertion dan NOT_RUN tanpa generalisasi.
7. Koreksi laporan dan handoff: PA-001 menunggu review, code blockers masih ada, tidak host-only; bukti rollback sesuai tes sebenarnya.
8. Persist report controller ini dan dua handoff reviewer lengkap dari lampiran ke report/ sesuai CONTRACT §10. Jangan memasukkan akses/secret/PII.
9. Tinjau diff, commit semua perubahan packet yang sah dan terkait; **push branch dari executor**, perbarui PR, verifikasi remote SHA dan CI pada SHA itu. Jangan commit file runtime/credential/unrelated work hanya untuk “push semua”.
10. Kembalikan URL PR, full SHA, laporan, diff summary, actual test results, keputusan yang masih dibutuhkan, serta next packet. Tunggu review untuk penerimaan/integrasi sesuai kontrak; tidak ada deploy otomatis setelah push.

Packet selanjutnya sesudah PR9 diterima: PA-006 untuk menuntaskan uang/idempotency; PA-002 bersama authority PA-003 untuk lifecycle jobs. DEC-02/docs manifest dan pekerjaan installer independen boleh diparalelkan hanya dengan owner/worktree disjoint. DEC-01 wajib diselesaikan sebelum menetapkan topology rehearsal. SSTP PR7 tidak otomatis mendahului inti WG Beta.

Hanya setelah exit criteria sandbox dan bukti predeploy relevan cukup, controller dapat menyatakan **SANDBOX_READY_FOR_DEPLOY_REVIEW**. Itu bukan DEPLOYED, PILOT_VERIFIED atau otorisasi mencoba lingkungan produksi.

## 9. Keputusan pemilik yang nyata, bukan pertanyaan izin rutin

- **DEC-01 belum resolved:** mengikuti Compose yang authoritative atau menyetujui perubahan native deployment yang sempit. Executor harus menyiapkan proposal biaya/risiko/isolasi, bukan langsung mengubah ARCHITECTURE/CONTRACT.
- **Scope fitur kandidat Beta:** WG default dan gates jaringan aktual; SSTP fase2/fitur lanjutan hanya jika memang dipilih dan terverifikasi. Jangan mempromosikan seluruh roadmap R2–R4 menjadi blocker global.
- **Budget gangguan saat rehearsal/rollout:** belum ditemukan angka maksimum gangguan yang disetujui. Ukur baseline di VM disposable, ajukan angka beserta recovery plan sebelum aktivasi target.
- **Tanggal kalender:** tidak ditemukan deadline agreed. Jika diperlukan, jadwal realistis disusun dari packet/evidence tersisa; jangan meminta keputusan ini untuk menahan koreksi kode yang sudah jelas.

Tidak diperlukan credential atau akses server untuk mengerjakan packet PR9, PA-006, PA-002/003, koreksi manifest dan persiapan installer di sandbox.

## 10. Cakupan, metode, batas dan perubahan

Bukti utama dianalisis: README/CONTRACT; ARCHITECTURE/PRODUCT/FINANCE/IMPLEMENTATION_PLAN/ACCEPTANCE/OPERATIONS; defaults/test-cases; progress/handoff/laporan PA001; planning_audit pada PR8; diff PR9; seluruh imports Python domains melalui AST; billing services/models/views/concurrency tests; jobs engine/views/worker; tenant context/idempotency; customer/network/radius ownership; documents renderer; subscriptions upload; feature imports/live adapter; installer/CI/deployment inventory.

Ini review incremental baseline main dan kandidat PR9, bukan klaim membaca ulang setiap baris repository/histori atau audit penuh SSTP PR7.

Dilakukan read-only: GitHub metadata refs/PR/runs/jobs/logs, git fetch/status/diff/show, rg inventory/search, targeted source reads, Python AST, official documentation checks, current controller prompt read dan penelusuran bukti timeline. Worktree review tetap bersih.

NOT_RUN oleh controller dan reviewer: suite aplikasi baru, exploit/race runtime, installer, migration, service/DB execution, FreeRADIUS daemon, browser E2E, CHR/GNS3, load/soak dan restore. CI hasil existing dibaca, tidak direrun. Tidak ada production probe.

Dua reviewer independen bekerja terpisah pada exact candidate dan mengkritisi hasil, bukan hanya menyetujui: reviewer finance/compatibility serta reviewer operations/reliability. Temuan lengkap dipertahankan pada lampiran. Review statis mereka bukan pengganti tes runtime executor.

**Repository files changed by controller/reviewers: NONE.** Tidak ada commit, push, merge, tag, perubahan source/config/dependency/deployment atau kontrak dari sesi review. Artefak laporan ini tersedia untuk executor, yang wajib mempersistensikannya di report/ dan melakukan commit/push sendiri.

Suggested persistence:
- report/controller/20261111T074225Z-repo-handoff-review.md — laporan ini.
- report/reviewer/20261111T073744Z-pr9-independent-review.md — lampiran finance lengkap.
- report/reviewer/20261111T073747Z-ops-readiness.md — lampiran operasi lengkap.

**Kesiapan:** dokumen controller siap dipakai untuk packet koreksi sandbox; **NOT READY untuk Production Beta**. Risiko terbuka tidak dapat ditutup dengan menambah VPS atau mengubah wording handoff. Tahap berikutnya adalah koreksi PR9 berbasis acceptance, kemudian review exact pushed SHA.
