# Quality Gates and Release Readiness — MicroTix v2.1

Dokumen: `sumber/quality/Quality_Gates_and_Release_Readiness_v2_1.md`  
Revisi paket: **2.1-macro.1** · Efektif: **29 Oktober 2026, Asia/Jakarta**  
Kewenangan: kontrak master AUD-01–AUD-46 dan MAC-01–MAC-08. Status: kontrol final dokumentasi; **rilis operasional BLOCKED**.

## 1. Keputusan dan objek evaluasi

Evaluasi dilakukan per `release + feature + adapter_version + topology + load_profile`, bukan satu boolean untuk seluruh R1–R4. Kontrak minimum PRD §26 tetap berlaku dengan penguatan lintas fitur di sini. Dokumen/registry yang lengkap adalah input implementasi; desain uji bukan eksekusi uji. Tidak ada hasil CHR, RADIUS, ACS, benchmark, pilot atau DR yang dibuat oleh konsolidasi ini.

| Objek | Status paket ini | Dasar |
|---|---|---|
| Konsolidasi makro | COMPLETED, scope dokumentasi | Dokumen kontrol, sinkronisasi sumber, dan pemeriksaan statis |
| Desain kasus | 64 child T01–T24 + 20 QA-SEC | 84 ID unik, spesifikasi JSON/Markdown berparitas |
| Eksekusi runtime | NOT_RUN, 0 dari 84 | Aplikasi/runner/target/grant belum disediakan |
| Prasyarat G0–G5 | BLOCKED | Kesiapan dinilai; bukti wajib belum tersedia, bukan kegagalan runtime |
| QG-DOC/QG-QA formal | NOT_EVALUATED | Tidak ada review formal independen; hasil statis dicatat terpisah |
| Feature release flags | Tidak diubah | Tidak ada mandat/bukti rilis produksi |

Kasus memiliki status `NOT_RUN`, `BLOCKED`, `RUNNING`, `PASS`, `FAIL`, atau `NOT_APPLICABLE`. Gate memiliki `NOT_EVALUATED`, `BLOCKED`, `PASS`, atau `FAIL`. `implemented`, `verified_local`, `verified_lab`, dan `release_enabled` adalah dimensi bukti terpisah. N/A hanya untuk kebutuhan yang benar-benar tidak berlaku pada scope terdaftar dan disetujui; hardware/izin/runner yang hilang bukan N/A.

## 2. Prasyarat lintas gerbang

| Area | Syarat masuk | Jika tidak terpenuhi |
|---|---|---|
| Integritas dokumen | Manifest aktif, seluruh path/size/hash, payload root, versi kontrak dan projection cocok | FAIL pemeriksaan integritas; hentikan penggunaan baseline |
| Konfigurasi | Key/type/unit/range/classification/source/version/change policy lengkap; effective config hash; deadline setiap kind | BLOCKED kind/fitur terkait; unknown key ditolak |
| Implementasi | Source commit/artifact, dirty diff, migration/schema dan runner nyata; exact versions + dependency/image digests; TK-001–004 sesuai scope | BLOCKED; versi mayor pada desain bukan exact pin deployment |
| Otorisasi | Mode A/B/C tidak saling memberi izin; target/operation/window/resource/recovery/evidence tercakup; grant dapat dibuktikan | BLOCKED sebelum akses/efek; lanjut pekerjaan independen |
| Lab | V0–V4 File 2; host identity/pin; nonproduksi; CHR/image legal; controller/compute/API family terverifikasi; resource dan subnet bebas overlap | BLOCKED target/case yang memerlukan lab |
| Keamanan | Synthetic fixtures; secrets runtime binding; RLS+roles; ACL egress; clock skew ≤5 detik; evidence sink sehat | Blokir mulai atau hentikan mutasi; pelanggaran invariant menjadi FAIL |
| Pemulihan | Baseline, ownership exact ID, snapshot dan restore capability; cleanup window serta emergency scope | BLOCKED sebelum fault/mutasi berisiko |
| Review | Identitas reviewer, jenis review, scope/rule version, waktu dan report nyata | BLOCKED gate yang memerlukan reviewer; self-review tidak dipromosikan |

Profil lokal/CI aplikasi yang tidak memerlukan perangkat mengikuti MAC-06. Remote access tetap wajib V1–V3; rule ini tidak mengubah template DRAFT menjadi grant. Prasyarat test bukan kewajiban seluruh gate upstream sudah PASS. Uji yang membentuk satu gate boleh dijalankan setelah prerequisite test-nya sah sehingga tidak muncul ketergantungan sirkular.

## 3. Definisi operasional G0–G5

### G0 — Baseline desain, implementability, dan toolchain

**Masuk:** paket arsitektur v2.1 pada revisi manifest aktif terverifikasi; mandat workspace untuk TK implementasi; traceability kebutuhan dan MAC/AUD tersedia. CHR/CPE bukan syarat G0.

**Keluar PASS:** TK-001 memberi laporan penempatan fail-closed dan conflict handling; TK-002 menyediakan ADR stack, exact dependency/image pins, lisensi, toolchain dan CI yang benar-benar berjalan; TK-003 menetapkan schema/API/permission/enum/state/job-kind/deadline/registri parameter, threat model dan desain ledger; TK-004 menyediakan strategi fixture/simulator berlabel serta rencana lab. Source→requirement→task→case→assertion terlacak, dependency DAG tidak bersiklus, setiap fitur mempunyai minimum gate. Kontrak shell/Makefile yang belum diwujudkan tidak dihitung tes lulus. Rencana legal/retensi/tenant isolation sudah terikat MAC-03–05.

**Bukti:** commit/artifact dan dependency locks, CI logs nyata, ADR, traceability, schema/API contract, parameter snapshot dan review arsitektur. **Penanggung jawab:** architecture/engineering owner dan reviewer yang identitasnya dicatat. **Saat ini BLOCKED:** R-03; source/toolchain/ADR implementasi tidak tersedia.

### G1 — Kebenaran protokol dan perangkat pada lab terotorisasi

**Masuk:** baseline G0 untuk implementasi yang diuji; File 2 V0–V4; Lab0/1 untuk jaringan, Lab2 untuk cutover, Lab4 untuk ACS/WAN yang relevan. CHR memakai RouterOS build exact+image hash+lisensi; FreeRADIUS 3.2 baseline minimum 3.2.5 dengan patch exact, dictionary dan PostgreSQL terpin. Versi exact ditentukan inventaris, bukan angka dari situs dokumentasi. RouterOS v6 tidak memperoleh kemampuan mutasi v7.

**Keluar PASS per capability:**

- Enrollment/API/WireGuard T01 membuktikan TLS/pin, permission minimum, replay, overlap, idempotency serta tidak mengganggu dua sesi kontrol. Jalur manajemen /32 dan isolasi antarpeer benar; tidak ada transit default/LAN pelanggan melalui VPN platform.
- RADIUS T16/T19/T21 membuktikan PAP/CHAP/MS-CHAPv2 sesuai kemampuan PPPoE dan metode Hotspot yang relevan, exact username, tenant terikat NAS, attribute resolver, accounting, session identity dan admission serentak. Pool PostgreSQL transaction-local diuji setelah commit/rollback/error; source spoof, wrong secret dan Message-Authenticator invalid tidak menghasilkan Accept. Port UDP 1812/1813 privat dan Disconnect 3799 dikonfigurasi eksplisit.
- Cutover T17/T18 memerlukan T01, T16, T19, T21 dan T08/T09 relevan, ready credentials, no-shadow canary, baseline shared setting dan recovery delta. B3 berlangsung **1.800 detik nyata**, ≥100 valid auth, sukses ≥99%, nol wrong Accept/tenant/atribut. B4 berlangsung **86.400 detik nyata**. Keterlambatan observasi tidak dipercepat dengan fake clock. B5 batch ≤100; disable/rename/delete hanya metode yang terbukti dan diotorisasi. B6 memulihkan baseline spesifik, bukan `use-radius=no` global atau menghidupkan akun tertahan.
- Isolir T07/T20 memerlukan Reject yang terbukti berasal policy target, ACK/bukti positif sesi hilang, Acct-Stop/readback, lalu recheck 60 detik. Diamnya interim bukan bukti putus. Restore memakai Accept dan `verified_active` bukan klaim online. Seluruh NAS, local shadow, IPv4/IPv6 dan jalur bypass pada scope diuji.
- Backup spike TK-505 dan T08/T09 membuktikan size+transfer completion, enkripsi/durable storage, generasi 101→100 retained valid, exact ownership cleanup, dan restore lab. Fake file/hash server sendiri bukan bukti restore.
- ACS T11 dan QA-SEC-16 hanya PASS model produksi setelah model/firmware/data-model/path mapping teruji pada perangkat fisik relevan. Emulator membuktikan kontrak saja. HTTPS 443 gateway, NBI/Mongo privat, installed claim proof, task RPC/fault, write-only verification dan independent management/recovery untuk rotasi wajib. Timeout/task hilang bukan sukses; tanpa jalur recovery rotasi BLOCKED.
- WAN T13 dinilai per topologi dan model yang tersedia; PCC tidak dipadukan dengan Hotspot aktif. CHR tidak membuktikan radio/ASIC/OLT fisik.

**Bukti:** topology, target identity, exact firmware/license/image/dictionary, sanitized protocol outcomes, before/after revision, continuous control-session probes, per-assertion actual, cleanup. **Penanggung jawab:** network/adapter owner; reviewer sesuai gate record. **Saat ini BLOCKED:** R-01/02/03/04.

### G2 — Isolasi, integritas transaksi, privasi, dan restore

**Masuk:** implementasi nyata + G0; G1 applicable hanya untuk assertion yang bergantung perangkat. Unit/DB/API/ledger/i18n lokal tidak menunggu CHR atau CPE yang tidak digunakan. Seluruh applicable QA-SEC dan uji finansial/retry wajib terpilih, termasuk kasus negatif, concurrency, fault dan recovery yang relevan.

**Keluar PASS:** T10 membuktikan tenant/RBAC/SupportGrant/RLS/connection reuse; T19 membuktikan isolasi RADIUS pada jalur nyata; T05/T06 membuktikan idempotency, payment allocation, race, lease dan stale writer; T12 membuktikan ledger tiga lapis, immutable posted entries, period locking, prepaid vs recognized receivables, rounding exact dan rekonsiliasi; T04/T23 membuktikan CSV/i18n/a11y dan dokumen issued immutable; T08/T09 relevan membuktikan restore, bukan hanya backup listing. ClamAV nyata dengan definisi sehat wajib untuk upload release.

QA-SEC-20 dan assertion MAC membuktikan minimum retensi 10 tahun dari akhir tahun buku, batas tahun kabisat, hold/purge race, offboarding 180 hari, pemisahan data operasional, arsip yang dapat dipulihkan dan penghapusan pascarestore. Uji insiden sintetis membuktikan jam 24/48/72 tanpa reset, pengendali/prosesor, retry kanal, bukti pengiriman dan minimisasi. Tabel kontak/kanal aktual, DPA/retention schedule dan review hukum wajib sebelum produksi yang memproses data pribadi. Review akuntan atas posting/COA/framework/tax/retensi wajib untuk fitur pembukuan/keuangan terkait; tanda tangan profesional tidak digantikan assertion test.

Applicable ASVS **5.0 L2 beserta inherited L1** dipetakan per requirement, bukan hanya bab; WCAG **2.2 AA** menjadi baseline UI. ISO/IEC 25010:2023 digunakan sebagai model perencanaan, tanpa klaim sertifikasi. Traceability requirement kritis 100%; seluruh assertion kritis PASS; line coverage kode unit-testable yang berubah ≥85% sebagai AUDIT_DEFAULT. Tidak ada critical/high exploitable issue terbuka, cross-tenant disclosure, unbalanced/duplicate/lost acknowledged financial effect atau wrong-target network effect. Rerun/flaky/quarantine tidak meluluskan kebutuhan wajib.

**Bukti:** hasil aplikasi/DB nyata, bypass/negative tests, laporan rekonsiliasi, review akuntan/legal dengan versi aturan, privacy runbook dan restore evidence. **Penanggung jawab:** QA/security/finance/privacy owner sesuai fitur. **Saat ini BLOCKED:** R-03/05/06; dependency lab R-01/02/04 hanya bila applicable.

### G3 — Pilot terbatas dengan mandat produksi tersendiri

**Masuk:** G0 serta G1/G2 applicable PASS; change plan pilot dengan tenant/router/service exact, risiko, baseline traffic/sesi, window, monitoring, kill-switch, rollback dan kontak; inventory VM/NAT/UDP aktual. Mode B tidak memberi mandat pilot produksi. Sandbox fixture atau hasil demo bukan pilot.

**MACRO_DEFAULT pilot:** paling banyak **1 tenant, 1 router, 50 layanan**, durasi observasi minimal **7 hari kalender nyata** termasuk satu siklus billing/isolation terjadwal yang relevan. Bila siklus itu belum terjadi, observasi dilanjutkan sampai terpenuhi dalam window baru yang sah. Batas tersebut hanya pembatasan pilot, bukan perubahan kuota paket. Perubahan cap/durasi memerlukan profil pilot+ADR yang disetujui sebelum run; tidak boleh memperkecil observasi demi kelulusan. Approval pilot dapat mengaktifkan capability khusus tenant target untuk pengujian, tanpa menyalakan flag umum yang justru menunggu G3.

**Keluar PASS:** baseline vs observed terdokumentasi; sesi kontrol kontinu dan tindakan target sesuai kebijakan; tidak ada salah isolir/tenant/posting; anomaly ditangani dan direkonsiliasi; rollback pada scope aman terbukti; keberatan/insiden yang memblokir selesai; owner operasional menerima hasil. Auto-isolir tetap default off sebelum minimum G1+G2+G3 terpenuhi dan policy tenant diaktifkan melalui mandatnya.

**Bukti:** change plan, grant, inventory, scope/simulation hash, telemetry mentah yang tersanitasi, daftar perubahan, signed-off acceptance faktual dan rollback record. **Penanggung jawab:** product/release owner dan operator tenant yang ditunjuk. **Saat ini BLOCKED:** R-01/03/06/07 dan gate upstream applicable.

### G4 — Kapasitas, soak, reconnect, dan availability

**Masuk:** G0 dan gate fungsional/security applicable PASS; load/fault grant, budget CPU/RAM/disk/concurrency/rate/biaya/window, generator terpisah, baseline hardware/topology dan metrics sink. Pilot G3 wajib bila scope adalah perluasan dari pilot produksi; benchmark lab tidak otomatis memerlukan mutasi produksi.

| Parameter | Nilai wajib baseline AUD-42 |
|---|---|
| Tahap | 10 → 100 → 1.000 tenant; hanya tahap yang diotorisasi dan diuji boleh diklaim |
| Workload | 2 router + 300 service per tenant; 200 CPE per tenant hanya fitur R3 |
| Auth/accounting steady | Auth 50 request/detik pada profil awal; accounting = active_sessions / 300 detik |
| Waktu | Ramp 10 menit, warmup 10 menit dikeluarkan dari sampel, steady ≥30 menit; soak 8 jam tahap 10/100 dan 24 jam tahap 1.000 |
| Storm | 10% sesi aktif reconnect dalam 60 detik; 300.000 sesi menghasilkan tambahan 500 auth/detik |
| Stress terpisah | 2.000 auth/detik selama 60 detik bila diotorisasi; bukan inferensi dari storm |
| Sampel percentile | ≥10.000 sampel tiap metrik yang diklaim; nearest-rank atas sampel mentah; tidak merata-ratakan p95 per menit |
| Batas steady | p95 list/enqueue ≤2 detik; p95 auth ≤100 ms; p95 aktivasi normal ≤60 detik dari enqueue hingga policy/auth verified |
| Error/progress | Error non-injected <0,1%; timeout termasuk gagal; injected denominator terpisah; semua tenant aktif memperoleh progress ≤60 detik |
| Invariant | Nol kebocoran tenant, salah target, unbalanced/duplicate/lost acknowledged effect; resource/queue age dalam budget |

T15/T22 dan kasus relevan membuktikan counter/replay/accounting, reconnect, starvation, backpressure dan failure recovery. Sampel kurang berarti tidak cukup bukti percentile, bukan PASS. Mock NAS tidak memberi klaim kapasitas CHR/fisik; hasil menyatakan kapasitas server, generator, NAS dan link secara terpisah. Fixture 100.000 service/tenant adalah capacity override lab, bukan kuota komersial.

Dua proses satu host hanya process redundancy. Host HA membutuhkan kegagalan host primer tanpa kehilangan jalur sekundernya, state DB/key yang valid dan bukti independent failure domain. Edge snapshot ditandatangani/terenkripsi, tenant-scoped, revision monotonik, TTL 900 detik; partition tidak menjanjikan global strict limit atau suspend pusat yang belum diterima. Edge tetap off sebelum T22/G4 PASS.

**Bukti:** workload manifest, hardware/version/digests, raw samples+method, resource graphs, fault timeline, fairness, reconciliations dan cleanup. **Penanggung jawab:** performance/SRE/network owner. **Saat ini BLOCKED:** R-01/02/03/06 serta gate applicable.

### G5 — Operasi, observability, insiden, dan pemulihan bencana

**Masuk:** fitur dan kapasitas yang akan dioperasikan sudah memiliki gate applicable; operator/on-call, monitoring, key recovery, storage dan lokasi retensi nyata; runbook backup/restore/rollback/incident yang dapat dijalankan; review profesional terkait; grant drill dan emergency scope.

**Keluar PASS:** T14 end-to-end memulihkan layanan inti dengan **RPO ≤900 detik dan RTO ≤14.400 detik** sesuai scope rilis. RTO dimulai sejak outage yang diinjeksi/dideteksi, mencakup detection/decision/provisioning/restore/radius_ready/full_ready. RPO membandingkan acknowledged event sequence+timestamp sebelum outage dengan yang pulih; bukan WAL timestamp saja. Payment/policy/session pascabackup direkonsiliasi sebelum worker isolir berjalan. Restore keys/config/DB/RADIUS/gateway/API/workers/artifacts/ACS mengikuti dependency; ACS R3 tidak menunda RTO R1 yang memang tidak mencakupnya.

Restore dari backup aktual, recovery kunci, rollback aplikasi/migrasi, alert escalation, retention/hold/purge, offboarding dan incident communication drill terbukti. Tabletop dapat membuktikan review runbook; tidak membuktikan restore/RTO. Rujukan controller/processor, kanal insiden yang diverifikasi dan cadangan pengirim tersedia, tanpa menunggu forensik selesai untuk tenggat. Target RPO tidak berarti janji nol transaksi hilang; rekonstruksi dari sumber durable/eksternal dicatat. Kebijakan drill setelah go-live minimal **dua kali per tahun**, dievaluasi ulang setelah perubahan besar; dokumen ini tidak membuat automation terjadwal.

SLA eksternal hanya boleh ditawarkan setelah G5 pada scope/kapasitas yang benar-benar terbukti dan otorisasi komersial. Single VM tetap SPOF. **Bukti:** recovery timeline, event reconciliation, backup/key restore, monitoring/alert outcomes, incident synthetic delivery, runbook versi terkunci, penugasan on-call dan review. **Penanggung jawab:** operations/release owner. **Saat ini BLOCKED:** R-01/02/03/05/06/07 sesuai scope.

## 4. Matriks aktivasi fitur dan urutan dependency

G0 adalah fondasi semua rilis. G2 security/privacy applicable berlaku bagi semua fitur yang memproses data tenant; tambahan di bawah adalah minimum khusus fitur, bukan pembebasan dari invariant lintas fitur. Ketiadaan ACS tidak memblokir R1 yang tidak menggunakan ACS.

| Fitur | Prasyarat minimum khusus | Bukti/ketergantungan utama |
|---|---|---|
| R1 inti, CSV, i18n, adopsi DB-only | G0 + G2 | T04/T10/T23 dan QA-SEC applicable; discovery perangkat tetap G1 bila digunakan |
| VPN/koneksi/mutasi router | G1 | T01; TLS/pin/permission/route ownership |
| RADIUS authoritative/cutover | G1 + G2 isolation | T16/T17/T18/T19/T21; T08/T09 backup/recovery; no-shadow canary |
| Backup | G1 spike TK-505 + G2 | T08/T09; restore nyata |
| Penjualan SaaS berbayar | G2 + otorisasi pemilik | T05 sisi SaaS, financial/privacy controls, tujuan pembayaran terverifikasi |
| Auto-isolir | G1 + G2 + G3 | T07/T20 dan T05; hold, multiNAS, policy simulation fresh |
| Pembukuan produksi | G2 + review akuntan | T12, QA-SEC-10/20, MAC-03; review rule/book version |
| Voucher/agen | G1 + G2 | T16/T21/T24; quota, counter, expiry dan commission |
| ACS | G1 + G2 per model | T11, QA-SEC-16, physical capability/recovery |
| WAN | G1 + G2 applicable per topologi | T13; ChangePlan, control path dan rollback |
| Edge RADIUS | G4 + security applicable | T22; partition/expiry/strict-mode boundaries |
| Kenaikan kapasitas 10→100→1.000 | G4 + G5 pada tahap tujuan | Hasil tahap sebelumnya tidak mensertifikasi tahap berikutnya |
| SLA operasional | G5 + otorisasi komersial | Scope, RPO/RTO, availability dan tanggung jawab nyata |

Urutan minimum lab: integritas/V0 → grant/inventory V1–V2 → rencana V3 → app smoke/RLS → T10/T19 negatif dan T16 baseline → T01 CHR → T08/T09 serta fixture T18/T21 → T17 → T20/fault/load/DR applicable → V5 cleanup dan review. Setiap panah adalah dependency pada bukti yang relevan, bukan izin memperluas scope. Protokol baseline sebelum T01 dapat memakai NAS harness terdaftar untuk persiapan, tetapi hasil G1 RouterOS tetap membutuhkan CHR/NAS nyata.

## 5. Checklist formal dokumentasi dan desain pengujian

Checklist di bawah mendefinisikan kembali QG-DOC-01–10 dan QG-QA-01–12; seluruh status formal saat ini **NOT_EVALUATED**. Tidak ada warisan angka 10/10 atau 12/12 PASS. Pemeriksaan statis otomatis mendukung beberapa item, tanpa menggantikan review semantik/independen.

| ID | Kriteria formal |
|---|---|
| QG-DOC-01 | Sumber, precedence, baseline dan provenance dapat ditelusuri |
| QG-DOC-02 | Seluruh file/path/byte/hash dan exclusion manifest konsisten |
| QG-DOC-03 | AUD/MAC dipetakan ke dokumen, task dan assertion |
| QG-DOC-04 | Parameter, unit, nilai efektif, null/empty dan boundary tegas |
| QG-DOC-05 | API, error, state machine, idempotency dan recovery tidak bertentangan |
| QG-DOC-06 | Tenant/secret/NAS trust boundary dan prinsip least privilege jelas |
| QG-DOC-07 | Finance, retensi/hold dan PDP memiliki keputusan serta dasar yang tepat |
| QG-DOC-08 | Target/izin/asset/reviewer yang hilang menjadi blocker terstruktur |
| QG-DOC-09 | Status historis, statis, runtime, reviewer dan rilis dibedakan |
| QG-DOC-10 | Dokumen kontrol final, mapping deployment dan bukti ekspor dapat direproduksi |
| QG-QA-01 | Registry unik: 64 child, 20 QA-SEC, seluruh 24 parent |
| QG-QA-02 | Matrix dan blok spesifikasi berparitas dengan registry |
| QG-QA-03 | Fixture/seed/hash dan before-state deterministik |
| QG-QA-04 | Setup/action/expected/assertion ID/deadline/cleanup lengkap |
| QG-QA-05 | Happy/negative/boundary/concurrency/fault/recovery applicable terpilih |
| QG-QA-06 | Dependency DAG, local profile dan lab preflight tanpa cycle |
| QG-QA-07 | Protocol/CHR/hardware dibedakan dari stub/emulator |
| QG-QA-08 | Tenant isolation, finance immutability dan wrong-target nol toleransi |
| QG-QA-09 | Load/soak/sample/percentile/RPO/RTO terukur dan tidak dapat diganti mock |
| QG-QA-10 | Evidence assertion expected/actual, redaction, retention dan integrity lengkap |
| QG-QA-11 | Cleanup/rollback, no-blind-retry dan uncertainty diuji |
| QG-QA-12 | Applicability, professional review, invalidasi bukti dan minimum gate fitur jelas |

## 6. Evidence, perhitungan, dan invalidasi

Setiap run merekam schema/version, run UUID, case/parent/requirement/AUD/MAC, authorization ID+scope hash, target IDs, effective-config hash, manifest hash, commit/artifact hash dan dirty diff, exact image/dependency/license, fixture seed/hash, UTC start/end dan durasi monotonic, langkah aktual, assertion ID expected/actual/result, raw metrics reference, artifact path/byte/hash/classification, executor/reviewer, cleanup dan blocker. Actual null tetap NOT_RUN. Evidence tanpa sumber atau expected-only tidak lulus.

Gate record merekam tuple scope, daftar applicable cases/assertions, requirement hash, evidence index digest, review refs, evaluated_at, evaluator_type, keputusan, blocker dan feature flag disposition. Semua bukti harus dari baseline konsisten atau disertai analisis kompatibilitas yang disetujui; tidak menggabungkan PASS versi berbeda diam-diam. Salah tenant/uang/target, critical/high exploitable finding, evidence palsu, dan recovery tidak aman memblokir rilis.

Execution coverage = executed cases dengan actual step evidence / applicable required cases. Pass rate = PASS/(PASS+FAIL); denominator nol menghasilkan null. NOT_RUN/BLOCKED tetap gap; N/A sah dikeluarkan dari denominator dengan alasan. Design coverage berbeda dari verified coverage. Gate membutuhkan semua assertion wajib, bukan angka rata-rata yang menutupi kegagalan kritis. Release evidence disimpan selama rilis berlaku ditambah ≥90 hari setelah superseded; insiden ≥400 hari; finansial mengikuti MAC-03; raw capture terotorisasi ≤24 jam. Metadata sanitized dapat disimpan pada repository privat; raw log/PCAP/backup/secrets tidak dimasukkan.

Perubahan hash requirement/test/assertion/config/schema/adapter/topology/firmware/load memerlukan impact assessment. Status gate terdampak kembali BLOCKED sampai re-verification yang diperlukan selesai; sejarah PASS lama tidak dihapus. Perubahan editorial tanpa dampak semantik dicatat dan diperiksa terpisah. Reviewer profesional yang diwajibkan belum ada berarti BLOCKED, bukan disamakan dengan self-review.

## 7. Blokir yang diketahui dan tindakan berikutnya

| ID | Input/bukti yang belum tersedia | Dampak | Penutupan |
|---|---|---|---|
| R-01 | Grant File 2 nyata, target identity, window dan action allowlist | Mode B, G1/G3/G4/G5 remote | Manifest AUTHORIZED + proof + V1–V3 lulus |
| R-02 | Images/digest/license, KVM/resource, routing dan evidence sink | Protocol/load/DR lab | Inventaris terverifikasi, budget/recovery dan sink sehat |
| R-03 | Source aplikasi, artifact, runner, ADR/toolchain/CI exact | G0 dan semua runtime | Implementasi terotorisasi serta bukti build/test nyata |
| R-04 | Model/firmware/hardware dan capability | ACS/OLT/perangkat terkait saja | Uji per model; emulator tetap scope kontrak |
| R-05 | Review akuntan/legal, lokasi arsip dan kanal insiden aktual | G2/G5 fitur terkait | Identitas reviewer, versi rule, report dan bukti kanal/lokasi |
| R-06 | Hasil integration/network/load/DR/pilot | G1–G5 applicable | Run evidence lengkap + cleanup + review |
| R-07 | Mandat pilot/deploy/release flag produksi | G3 dan aktivasi umum | Change plan/otorisasi terpisah yang memenuhi gate |

Agent berikutnya memeriksa baseline dan dependency, menjalankan seluruh pekerjaan independen yang input serta otorisasinya sudah lengkap, dan melaporkan field/reason tepat untuk yang tertahan. Tidak mengulang permintaan izin dalam scope yang sudah sah. Tidak ada request approval tambahan yang dibutuhkan untuk menyelesaikan paket dokumentasi ini.

## 8. Ketetapan makro normatif yang tersinkron

<!-- BEGIN MACRO-NORMATIVE-2.1-macro.1 -->
### MAC-01 — Kewenangan, baseline, dan batas klaim

Tanggal efektif dokumen: **29 Oktober 2026, Asia/Jakarta**. Versi arsitektur tetap **2.1**; revisi paket **2.1-macro.1**. MAC-01–MAC-08 melengkapi AUD-01–AUD-46 berdasarkan mandat konsolidasi pemilik. Pada pokok yang diperinci MAC, klausul MAC berlaku; selain itu hierarki AUD-02 tetap. Ketentuan MAC disimpan di kontrak master §23 dan diproyeksikan utuh ke dokumen gerbang. Perubahan tidak memberi izin eksekusi server, produksi, atau komunikasi kepada pihak lain.

Paket langsung yang diperiksa pada konsolidasi ini memuat **37 berkas, 1.016.000 byte tidak terkompresi**, dengan **36/36** entri manifest cocok. Angka **32 berkas, 549.017 byte, 31/31** adalah baseline audit sebelumnya sebagaimana dicatat Sol; arsip 32 berkas tersebut tidak tersedia sebagai input terpisah pada tahap ini. Klaim historis itu tidak diberi label OBSERVED baru. Manifest v1.4/v2.0 dipertahankan byte-identik terhadap paket langsung, bukan bukti pemeriksaan ulang semua sumber historisnya.

Status `COMPLETED` hanya berlaku untuk `documentation_macro_consolidation`. Dokumen siap menjadi input implementasi yang terikat prasyarat. Aplikasi, runner runtime, exact deployment pins, inventaris host, lisensi CHR, grant lab, review profesional, dan bukti operasional belum tersedia. Parameter desain yang sudah ditetapkan tidak sama dengan konfigurasi deployment yang sudah diamati.

### MAC-02 — Rantai integritas dan penempatan

Rantai verifikasi adalah **byte payload → entri manifest aktif → hash manifest pada dokumen konsolidasi eksternal → hash ZIP pada dokumen eksternal yang sama**. Manifest mengecualikan hanya dirinya sendiri; semua berkas lain, termasuk provenance, bootstrap legacy, alat verifikasi, dan audit, wajib terdaftar. Dokumen konsolidasi eksternal tidak dimasukkan ke ZIP. ZIP tidak menyimpan hash dirinya sendiri. `static-verification_v2_1.json` menyimpan pemeriksaan sebelum penyegelan; hasil pemeriksaan manifest dan ZIP sesudah penyegelan dicatat pada amplop ekspor eksternal sehingga tidak timbul siklus hash.

Daftar payload diurutkan berdasarkan byte UTF-8 path POSIX. Akar payload dihitung sebagai SHA-256 atas gabungan baris `sha256<TAB>size_decimal<TAB>path<LF>`. Berkas di-hash sebagai byte asli; tidak ada normalisasi newline, encoding, whitespace, atau penghapusan komentar saat verifikasi. Root digest bukan tanda tangan dan bukan bukti autentisitas penerbit. Distribusi lintas batas kepercayaan memerlukan digest melalui kanal tepercaya atau tanda tangan yang benar-benar tersedia; paket ini tidak mengarang tanda tangan.

Verifikasi menolak path absolut, traversal, backslash, nama duplikat atau benturan case-fold, symlink, entri hilang/tambahan, hash salah, ukuran salah, dan tabel kosong. TK-001 memverifikasi seluruh paket sebelum menempatkan satu berkas pun. Target identik boleh dilewati; target berbeda menjadi conflict/staging review. `docs/decisions.md` hanya dibuat bila belum ada dan tidak ditimpa. `bootstrap_docs.sh` tetap **LEGACY / AUDIT_ONLY**, bukan penerus bootstrap yang aman. Alat Python dalam paket hanya memeriksa dokumen/arsip secara baca-saja, bukan installer atau runner aplikasi.

### MAC-03 — Retensi finansial dan hak penghapusan

**Sepuluh tahun merupakan minimum retensi dokumen finansial, bukan batas maksimum dan bukan masa simpan seluruh data pelanggan.** SAK EMKM mengatur pelaporan keuangan bagi entitas yang memenuhi syarat; angka retensi ini dirujuk pada UU KUP Pasal 28 ayat (11), PP 50/2022 Pasal 11, serta UU 8/1997 Pasal 11 untuk dokumen perusahaan yang tercakup. Pilihan SAK EMKM/kerangka lain dan penerapannya tetap memerlukan review akuntan. [L1–L4]

Kontrak implementasi berikut merupakan kebijakan sistem MicroTix untuk menjalankan kewajiban tersebut:

1. `ledger.retention_years=10` bertipe integer tahun kalender; minimum 10. Penurunan di bawah 10 ditolak. Kenaikan memerlukan dasar retensi, versi kebijakan, dan review; perubahan konfigurasi tidak memendekkan `retain_until` yang telah disimpan.
2. Simpan `book_id`, `tenant_or_platform_scope`, `fiscal_year_end_date`, `book_timezone`, `record_class`, `retention_policy_version`, `retain_until_utc`, dan daftar `legal_hold_id` pada arsip. Tahun buku terkait ditentukan dari dokumen bisnis, bukan tanggal unggah/backup/penutupan akun. Metadata wajib yang tidak diketahui memblokir purge objek itu.
3. Batas aman paling awal dihitung sebagai awal hari setelah ulang tahun kalender ke-10 dari tanggal akhir tahun buku, pada zona waktu buku. Contoh tahun buku berakhir **31 Desember 2026**: arsip terlindungi sampai akhir **31 Desember 2036**; kandidat penghapusan paling awal **1 Januari 2037 pukul 00.00 Asia/Jakarta**, yakni **2036-12-31T17:00:00Z**, jika semua syarat lain terpenuhi. Tahun kabisat memakai clamp kalender yang konsisten. Koreksi yang masuk tahun buku berikutnya disimpan dengan periode postingnya; relasi bukti yang masih diperlukan memperpanjang retensi dokumen terkait sampai batas terlama.
4. `effective_retain_until = max(financial_floor, applicable_legal_or_contractual_dates, dependent_evidence_dates)`. Legal hold aktif selalu menolak purge walau tanggal terlampaui. Hold memiliki penerbit berwenang, alasan, scope, tanggal, review, dan bukti pencabutan; expiry numerik saja tidak mencabut hold. Proses purge dan aktivasi hold diserialisasi agar hold baru tidak kalah oleh job lama.
5. Cakupan finansial: jurnal dan line, invoice yang menjadi bukti transaksi, payment/allocation, bukti pembayaran yang diperlukan, rekonsiliasi, dokumen pajak, laporan issued, approval/reversal, audit finansial dan versi aturan untuk menafsirkan catatan. Ledger tenant terpisah dari buku platform. Data RADIUS `radacct` bukan buku besar keuangan; default 90 hari mentah/400 hari agregat tetap. Bila subset usage menjadi bukti tagihan, simpan snapshot pembuktian minimal yang terkait invoice dengan retensi finansial, bukan semua packet/raw traffic selama 10 tahun.
6. Retensi SaaS umum 180 hari sejak `ended_at` tidak menghapus arsip finansial/hold dan tidak memaksa penyimpanan semua PII selama 10 tahun. Data yang tidak lagi diperlukan dihapus/diminimalkan sesuai dasar pemrosesan; identitas yang diperlukan sebagai bukti dipertahankan secara terbatas, dapat dipertanggungjawabkan, dan tidak dipakai untuk pemasaran. Penolakan/penundaan sebagian permintaan penghapusan menjelaskan kategori, dasar, dan tanggal evaluasi kepada pengendali/subjek melalui proses berwenang.
7. Lokasi penyimpanan arsip wajib memenuhi ketentuan penyimpanan di Indonesia pada L1/L2; lokasi dan akses faktual dibuktikan sebelum produksi. Enkripsi, pembatasan akses, integritas, keterbacaan format, versi kunci, ekspor dan uji restore berlaku sepanjang masa simpan. Menghancurkan kunci sebelum akhir retensi juga dilarang. Snapshot DR berumur pendek tidak menggantikan arsip finansial.
8. Purge hanya melalui job khusus dengan policy/version snapshot, legal-hold recheck sebelum efek, daftar objek exact, audit keputusan dan bukti penyelesaian. Aplikasi runtime tidak memperoleh DELETE pada jurnal posted. Penghapusan arsip setelah jatuh tempo memakai principal terpisah dan tidak melanggar immutability buku aktif. Backup lama berada pada akses pemulihan terbatas sampai masa rotasinya; deletion ledger diterapkan ulang sebelum hasil restore dibuka. Kegagalan purge/restore bukan alasan menandai penghapusan selesai.

### MAC-04 — Insiden PDP dan tenggat operasional

UU 27/2022 Pasal 46 menetapkan pemberitahuan tertulis oleh pengendali dalam batas **3 × 24 jam** kepada subjek dan lembaga, berisi data yang terungkap, kapan/bagaimana kejadian, serta penanganan dan pemulihan. Dalam kondisi tertentu ada pemberitahuan kepada masyarakat. Kegagalan mencakup kerahasiaan, integritas, dan ketersediaan; bukan hanya kebocoran. [L5]

Ketentuan sistem di bawah adalah **MACRO_DEFAULT operasional**, bukan kutipan penentuan awal jam oleh undang-undang:

- Simpan `incident_occurred_at` (boleh belum diketahui), `first_signal_at`, `processor_known_at`, `controller_known_at`, `clock_basis_at`, `notification_due_at`, sumber observasi, dan riwayat perubahan append-only. Jam pengendalian internal dimulai dari sinyal kredibel pertama yang menunjukkan kegagalan, tidak menunggu forensik lengkap, rapat, atau approval. Bila waktu kejadian yang dapat dipercaya lebih awal tersedia, deadline dihitung konservatif dari waktu lebih awal; discovery terlambat dicatat sebagai risiko keterlambatan, bukan mereset jam. Counsel menentukan kewajiban aktual dan dapat memperpendek tenggat; tidak boleh memperpanjang baseline internal diam-diam.
- Platform sebagai prosesor mengeskalasi segera kepada pengendali, batas internal maksimum **86.400 detik (24 jam)** sejak diketahui; waktu ini berada di dalam anggaran 72 jam, bukan tambahan 24 jam sebelum 72 jam. Platform sebagai pengendali atas akun/billingnya sendiri menjalankan kewajiban pengendali secara langsung. Pemetaan per kegiatan pemrosesan dan DPA mencatat kedua peran ini.
- `notification_due_at = clock_basis_at + 259200 detik`; gunakan waktu UTC dan durasi kalender terus-menerus, tanpa pengecualian akhir pekan/libur. Batas internal draft awal **24 jam**, verifikasi penerima/kanal dan kesiapan pengiriman **48 jam**, tenggat pengiriman **72 jam**. Penanggung jawab dan deputi sudah ditetapkan sebelum go-live. Temuan lebih awal atau kewajiban lebih ketat mempercepat jadwal.
- Pemberitahuan awal memuat informasi yang tersedia dan ketidakpastian faktual; investigasi berlanjut dengan pembaruan. Nomor insiden, pengendali, kategori data/subjek, waktu diketahui/kejadian, dampak, tindakan, kontak dan rencana pemulihan dicatat. Identitas tenant lain, password, secret dan raw packet tidak disertakan. Pernyataan bahwa pemberitahuan telah disampaikan memerlukan bukti kanal menerima pengiriman; draft/queued/attempted tidak cukup. Delivery/read acknowledgment dicatat terpisah.
- Daftar penerima subjek, identitas lembaga berwenang, kanal resmi, kanal alternatif sah, dan bukti verifikasi counsel adalah input rilis wajib; tidak ditebak dari nama kementerian. Pemberitahuan publik dinilai terhadap kondisi hukum dan dampak masyarakat. Ketiadaan kanal di produksi memicu eskalasi darurat dan usaha kanal alternatif sah, tidak menghentikan jam atau kewajiban. G2 readiness privasi dan G5 tetap BLOCKED bila kontak/kanal/reviewer wajib belum tersedia.
- Runbook memiliki incident commander, penanggung jawab privasi/legal, pemilik tenant, pengirim berwenang, deputi dan jadwal piket. Kontrak/proses harus memberikan kewenangan pengiriman insiden terlebih dahulu; tidak menggantungkan tenggat pada pemilik yang sedang tidak hadir. Pengujian memakai penerima sintetis dan notification sink terisolasi. Audit dokumen ini tidak mengirim pesan atau notifikasi nyata.
- Bukti insiden disimpan minimal 400 hari menurut AUD-43; legal hold atau kebutuhan finansial dapat memperpanjang subset terkait. Bukti tersanitasi, audit waktu, hash dan akses terbatas tetap berlaku; raw capture tetap maksimum TTL 24 jam bila diotorisasi.

### MAC-05 — Isolasi multi-tenant RADIUS

Alur kepercayaan wajib: **peer/tunnel terdaftar → transport source NAS yang unik → validasi secret dan authenticator → NAS/router terdaftar beserta applied revision → tenant → facade transaksi → atribut/sesi untuk tenant tersebut**. `User-Name`, `NAS-IP-Address`, realm, `Client-Shortname`, atau tenant pada payload tidak berwenang memilih tenant. Username sama di tenant A/B sah, dengan credential dan atribut masing-masing. Source IP tunnel yang sama tidak boleh terdaftar pada dua NAS; NAT/relay yang menghilangkan identitas source tanpa desain transport terverifikasi memblokir enrollment. [AUD-19–21]

Role RADIUS hanya EXECUTE facade yang dibatasi. Bootstrap lookup hanya mengembalikan metadata client minimum kepada komponen RADIUS tepercaya, bukan directory lintas tenant bagi aplikasi/UI. Konteks NAS berasal dari jalur daemon yang sudah memverifikasi transport; pemanggilan facade dari principal aplikasi atau packet mentah ditolak. Facade memvalidasi NAS aktif, revision, scope, dan binding sebelum transaksi scoped. Tidak tersedia endpoint publik yang menerima klaim `verified_nas_id` tanpa validasi jalur tepercaya. Kepercayaan kepada daemon tersebut dinyatakan eksplisit; desain tidak mengklaim tahan terhadap daemon/backend yang sepenuhnya kompromi.

`ENABLE` dan `FORCE RLS`, role non-owner/non-superuser/non-BYPASSRLS, FK komposit, fungsi dengan `search_path` tepercaya dan `EXECUTE PUBLIC` dicabut berlaku bersama. RLS adalah lapis tambahan; karena principal DB dapat mempunyai kemampuan mengatur variabel sesi, GUC tidak menjadi otoritas identitas yang berdiri sendiri. Semua keputusan tenant berasal dari boundary terverifikasi dan query terparameterisasi; tidak ada jalur arbitrary SQL. Konteks hanya transaction-local pada koneksi yang sama; commit, rollback, error, timeout dan pool reuse diuji. Tidak ada broad DML ke `radius.*` dari aplikasi atau role accounting. [AUD-15,20; R1]

Projection-writer menulis perubahan akun dan proyeksi atomik dengan transaksi bisnis. Uniqueness akun `(tenant,username)` berbeda dari uniqueness atribut `(tenant,account,attribute,scope,ordinal)`. Authorize, accounting, postauth, admission, cache, agregat, edge snapshot dan Disconnect memakai tenant+NAS+account/session yang sesuai. Cache memasukkan revision kebijakan/credential/NAS yang relevan; invalidasi suspend/revoke/rotation diperiksa pada semua instance. Revoke selesai hanya setelah old credential dan cache klien ditolak di semua instance target. Bila instance tidak dapat diperiksa, status belum applied dan fitur terkait ditahan; shutdown sesi existing mengikuti mandat terpisah.

Unknown NAS atau Access-Request dengan Message-Authenticator hilang/tidak sah tidak boleh menghasilkan Access-Accept. Secure discard sah; negative test tidak mensyaratkan balasan Reject. Kredensial tenant B tidak boleh diterima pada NAS tenant A. Uji mencakup response attribute, accounting/postauth, context pool, reset/rollback transaksi, concurrent same username, revocation, key rotation, session limit dan peer firewall. Satu Accept yang salah, satu byte data lintas tenant, atau satu sesi salah target adalah **FAIL kritis** tanpa toleransi persentase. [R2]

Baseline strict admission memakai lock/reservasi per tenant+account, konfirmasi accounting dan rekonsiliasi okupansi positif. Dua NAS serentak pada limit satu harus menghasilkan paling banyak satu Accept yang sah; accounting hilang tidak membebaskan slot. Edge saat terpartisi menolak login yang membutuhkan koordinasi global, dan snapshot kedaluwarsa 900 detik menolak login baru. Dua proses satu VM hanya redundansi proses; klaim host HA memerlukan failure domain, jalur jaringan, data dan kunci yang tetap tersedia saat host primer gagal. Disconnect-Request RFC 5176 menggunakan 3799 yang dikonfigurasi eksplisit; CoA hanya pada capability/build yang terbukti.

### MAC-06 — Dependency lokal, lab, dan produksi

G0 tidak mensyaratkan CHR/CPE. Implementasi/test lokal tetap membutuhkan mandat Mode C, source/build, runner, konfigurasi, dan target workspace yang jelas. Dalam registry, kasus aplikasi yang tidak bergantung perangkat memakai dependency `EXECUTION_PROFILE_READY` sebagai pengganti V1/V2/V3 generik. Profil ini memilih salah satu jalur secara eksplisit: **lokal/CI terotorisasi** (workspace+artifact+resource+evidence) atau **remote** (File 2 V1–V3 lengkap). Tidak ada pilihan otomatis dari null, dan tidak ada akses server melalui profil lokal. V0 dan V4 tetap diperiksa sesuai konteks; fakta eksternal tetap tidak boleh direkayasa.

Kasus jaringan, fault/DR/load, peer firewall, RADIUS transport, enrollment dan model ACS tetap memerlukan lab/target nyata serta grant sesuai operasi. Emulator ACS hanya membuktikan kontrak; release model fisik membutuhkan firmware/model nyata. Uji ledger/i18n tidak menunggu hardware ACS. Fake clock hanya untuk logika tanggal/retensi/deadline bisnis; tidak mengganti canary 1.800 detik, observasi B4 86.400 detik, TTL protokol dan soak waktu nyata.

Dependency persiapan berbeda dari gate rilis. T17 memakai fixture authoritative yang dibuat khusus dan terotorisasi untuk membuktikan T18/T21 sebelum cutover; fixture itu bukan hasil cutover. T09 restore lab dapat dijalankan untuk memenuhi prasyarat T17 tanpa menunggu seluruh G2 lulus; karena G2 sendiri juga memerlukan sebagian G1, menjalankan uji tidak boleh digantungkan pada gate yang akan dinilainya. Tidak ada lingkaran G1→G2→G1 atau G3→flag produksi→G3. Pilot memakai capability terbatas per change plan, bukan pengaktifan umum.

Pada pemilihan run, dependency case di-resolve transitif; missing/unknown dependency, cycle, scope di luar grant atau deadline/window tidak cukup menghasilkan BLOCKED. Dependency readiness token bukan hasil PASS yang boleh diasumsikan; setiap token mempunyai evidence dan pemeriksa. Registry tetap 64 child T01–T24 + 20 QA-SEC; assertion tambahan MAC memperketat ID existing. Semua case masih `NOT_RUN` sampai ada observasi aktual.

### MAC-07 — Keputusan gate dan kewenangan rilis

Gate dievaluasi per tuple `release, feature, adapter_version, topology, load_profile` dan hash requirement/test/config. `NOT_EVALUATED` berarti evaluasi formal belum dilakukan; `BLOCKED` berarti pemeriksaan kesiapan/evaluasi mendapati prasyarat wajib tidak tersedia; `FAIL` berarti assertion/invariant atau kebijakan dilanggar; `PASS` hanya bila seluruh bukti dan review wajib memenuhi scope. Prioritas agregasi **FAIL > BLOCKED > PASS**; gate yang belum pernah dievaluasi tetap NOT_EVALUATED. Kegagalan kritis tidak diturunkan menjadi BLOCKED hanya karena bukti lain kurang.

Konsolidasi ini mengevaluasi **kesiapan prasyarat**, sehingga G0–G5 berstatus **BLOCKED**, dengan `runtime_executed=false`; tidak ada assertion runtime berstatus FAIL/PASS baru. QG-DOC/QG-QA formal tetap NOT_EVALUATED, sedangkan hasil pemeriksaan statis Python dilaporkan terpisah. Pencabutan all-pass historis tetap berlaku. Self-review bukan review independen atau sign-off akuntan/hukum.

`release_enabled` memerlukan implementasi, bukti lingkungan yang relevan, semua minimum gate fitur, tidak ada blocker kritis/high yang dapat dieksploitasi, persetujuan profesional yang diwajibkan, dan mandat perubahan produksi. Gate PASS tidak memberi akses produksi. Izin tidak menggantikan gate PASS. Sandbox flag terpisah dapat dipakai untuk pengujian terotorisasi. Perubahan schema/policy/adapter/firmware/topology/load/config atau assertion membatalkan bukti yang terdampak; perubahan editorial murni memakai analisis dampak tercatat, bukan retest otomatis semua perangkat.

### MAC-08 — Registri kontrol tambahan dan akuntabilitas

Tabel berikut merupakan perluasan TD §16; key existing `ledger.retention_years` diperketat, bukan dibuat dua sumber nilai. Seluruh nilai efektif disnapshot dalam profil run. Field kontak/kanal/reviewer merupakan data deployment yang harus nyata, bukan default hasil audit.

| Key | Tipe; satuan | Default/batas | Scope; sumber; versi efektif | Perubahan |
|---|---|---|---|---|
| `ledger.retention_years` | integer; tahun kalender | 10; minimum 10 | book; LEGAL_MINIMUM + MAC-03; 2.1-macro.1 | Tidak memendekkan batas tersnapshot; kenaikan beralasan dan direview |
| `privacy.incident.processor_escalation_max_s` | integer; detik | 86400; 1..86400 | platform/DPA; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Boleh diperketat, tidak ditambah di depan tenggat pengendali |
| `privacy.incident.initial_draft_max_s` | integer; detik | 86400; 1..86400 | incident response; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Draft ≤ delivery readiness ≤ notification deadline |
| `privacy.incident.delivery_ready_max_s` | integer; detik | 172800; 1..172800 | incident response; MACRO_DEFAULT MAC-04; 2.1-macro.1 | Kenaikan memerlukan revisi kontrak, bukan override runtime |
| `privacy.incident.notification_deadline_s` | integer; detik | 259200; 1..259200 | controller activity; LEGAL_LIMIT + operational clock MAC-04; 2.1-macro.1 | Boleh lebih ketat; interpretasi counsel dicatat tanpa mereset jam |
| `release.pilot.max_tenants` | integer; tenant | 1; baseline maksimum 1 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Profil/ADR disetujui sebelum run untuk mengubah cap |
| `release.pilot.max_routers` | integer; router | 1; baseline maksimum 1 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Profil/ADR disetujui sebelum run untuk mengubah cap |
| `release.pilot.max_services` | integer; layanan | 50; baseline maksimum 50 | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Tidak mengubah kuota paket komersial |
| `release.pilot.min_observation_days` | integer; hari kalender nyata | 7; minimum 7 dan mencakup siklus relevan | pilot; MACRO_DEFAULT MAC-08; 2.1-macro.1 | Perpanjang bila siklus belum teramati; tidak dipersingkat demi PASS |

Pemilik produk menetapkan scope; arsitek memelihara kontrak/dependency; maintainer/QA memelihara registry, assertion dan bukti; security owner menguji isolasi; finance owner bersama akuntan meninjau posting/retensi; privacy/legal owner memverifikasi pemrosesan dan kanal; release owner memutuskan aktivasi pada change plan; operations owner memegang recovery/insiden. Nama dan bukti penugasan aktual wajib saat gate terkait; gelar/role pada dokumen tidak berarti seseorang telah menyetujui.

Rujukan primer, diperiksa 29 Oktober 2026; rujukan ini membuktikan teks aturan/semantik yang dikutip, bukan inventaris deployment atau sertifikasi kepatuhan:

- **L1** — DJP, UU 28/2007 perubahan UU KUP, Pasal 28(11): https://stats.pajak.go.id/undang-undang-nomor-28-tahun-2007
- **L2** — DJP, PP 50/2022 Pasal 11: https://pajak.go.id/en/node/90278
- **L3** — Kementerian Keuangan, UU 8/1997 Pasal 11: https://fiskal.kemenkeu.go.id/files/peraturan/file/1997%20UU%208.pdf
- **L4** — IAI, Tentang SAK EMKM: https://web.iaiglobal.or.id/SAK-IAI/Tentang%20SAK%20EMKM
- **L5** — JDIH Komdigi, UU 27/2022 Pasal 46 dan penjelasannya: https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/
- **R1** — PostgreSQL 17, Row Security Policies: https://www.postgresql.org/docs/17/ddl-rowsecurity.html
- **R2** — MikroTik, RADIUS: https://manual.mikrotik.com/docs/authentication-authorization-accounting/radius/
<!-- END MACRO-NORMATIVE-2.1-macro.1 -->


## 7. Penyelesaian kontrak build — 2.1-build.1

EXE-01–08 master §24 berlaku. Registry task/parameter/kind/profile/traceability dan supplemental test memperjelas persiapan implementasi; tidak mengubah syarat keluar G0–G5. G0 tetap memerlukan toolchain/CI nyata. Baseline84 tetap NOT_RUN; assertion tambahan tidak mengubah angka historis. Formal-audit readiness menunggu SEC-DEC-01 dan review semantik independen/clause completeness; gate produksi tetap BLOCKED. P0 foundation yang kontraknya lengkap dapat dikerjakan setelah mandat Mode C lokal tanpa menunggu G1/CPE/akuntan yang tidak relevan dengan pekerjaan lokal tersebut.

ASVS5.0.0 registry253 requirement L1+L2 memakai sumber CSV terpin. N/A bukan label otomatis: absence harus dibuktikan dan reviewer dicatat. Authentication assurance6.3.3 tidak dihapus agar G2 lulus; keputusan pemilik terkait MFA tenant harus dicatat. Prototype ledger G0 dan ledger produksi adalah scope berbeda; ASVS/security assertions diterapkan ke komponen aktual, tidak diklaim lulus pada komponen yang belum ada.
