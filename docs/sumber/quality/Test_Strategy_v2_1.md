# Strategi pengujian — MicroTix v2.1

[REVISI AUD-01–46 / MAC-01–08] Proyeksi normatif kontrak master v2.1 revisi 2.1-macro.1. Bagian AUD di bawah dihasilkan dari master; §23 MAC memperinci retensi/PDP/RADIUS/dependency/gate. Baca master §23 dan Quality_Gates_and_Release_Readiness_v2_1.md sebelum implementasi. Status runtime NOT_RUN.

## 7. Job, lease, status, dan dependency

[REVISI AUD-14] Domain change, audit yang telah diredaksi, dan outbox ditulis satu transaksi; job.event_id unik; on_commit hanya wake-up. Claim memakai transaksi pendek SKIP LOCKED. Transaksi tidak ditahan selama I/O router. Mutasi finansial tidak menunggu collector/backup. Job memiliki actor, permission snapshot untuk audit, expected_revision, config_version, deadline, dedup key, attempt dan lease_epoch; permission terkini diperiksa lagi sebelum efek.

| State asal | State berikut yang sah |
|---|---|
| queued | claimed, cancelled |
| claimed | preflight, retry_wait, failed, cancelled |
| preflight | executing, waiting_dependency, retry_wait, failed, cancelled |
| executing | verifying, uncertain, failed, recovery_required, cancelled hanya menurut EXE-01 |
| verifying | succeeded, uncertain, failed, recovery_required |
| waiting_dependency/retry_wait | queued, cancelled, failed |
| uncertain | verifying setelah readback, retry_wait hanya bila terbukti tidak diterapkan, recovery_required, failed |
| recovery_required | verifying setelah recovery terotorisasi, failed |
| succeeded/failed/cancelled | terminal; permintaan baru memakai job baru yang menautkan asal |

Lease habis saat executing/verifying → uncertain, bukan langsung queued. Dispatcher memeriksa epoch sebelum setiap kirim; RouterOS tidak memahami fence tersebut. Pemilik baru hanya menulis setelah proses/koneksi lama dipastikan tidak dapat mengirim lagi dan resource direkonsiliasi. Perintah yang telah terkirim tidak dapat ditarik kembali oleh lock DB. RADIUS write berarti update proyeksi DB + job Disconnect; bukan membuat user lokal pada router.

Retry total maksimum lima hanya untuk kegagalan terbukti sebelum efek; exponential full jitter cap 300 detik. Policy/hold/permission berubah sebelum efek →cancelled dengan alasan dan bukti EXE-01; bila efek mungkin terjadi, gunakan uncertain dan rekonsiliasi. Timeout sesudah efek mungkin terkirim →uncertain dan readback. `partial` ringkasan parent: jumlah succeeded/failed/blocked/pending; bukan state job anak. Parent tidak selesai sebelum seluruh anak terminal atau secara eksplisit ditahan dengan blocker. `stale` adalah kualitas observasi.

Kind dasar TD tetap; tambahan enrollment reconciliation, NAS client reload, import commit, router release/replace dan ChangePlan harus mempunyai kontrak kind sebelum executable. Konflik jenis/deadline yang belum terdaftar menahan kind terkait, tidak memblokir semua modul.

## 20. Desain pengujian, standar, dan gerbang

[REVISI AUD-40] Penghitungan sumber: matriks lama memuat62 child ID setelah shorthand diurai; spesifikasi memuat35 blok id, bukan30. Ada27 ID matriks tanpa blok lengkap dan dua ID negatif T16 yang hanya disebut di narasi. Registry v2.1 menyatukan64 child ID dan20 QA-SEC case. Jumlah di laporan/matriks dihasilkan dari registry, bukan diketik sebagai58. Setiap case mempunyai ID tunggal, dependency, fixture seed/hash, setup, aksi, expected assertion, deadline, bukti dan cleanup. Semua eksekusi aplikasi tetap NOT_RUN.

Spec common mengikat semua row registry: data sintetis seed261029; clock terkontrol untuk unit tetapi waktu nyata untuk protokol/canary/soak; dua tenantA/B, NASA1/A2/B1, dua akun kontrol non-target; actor/permission sesuai operasi; snapshot state sebelum efek; status NOT_RUN sampai actual observation ada; PASS hanya semua assertion benar, bukti lengkap dan cleanup aman. Missing required field→BLOCKED sebelum aksi. Runtime runner/harness belum ada adalah blocker tersendiri, bukan hanya “akses belum tersedia”. Registry dan spesifikasi final disertakan pada quality/Test_Case_Specifications_v2_1.md.

[REVISI AUD-41] ASVS5.0 mapping yang benar: V1Encoding/Sanitization; V2Validation/Business Logic; V3Web Frontend; V4API/Web Service; V5File Handling; V6Authentication; V7Session; V8Authorization; V9Self-contained Tokens; V10OAuth/OIDC; V11Cryptography; V12Secure Communication; V13Configuration; V14Data Protection; V15Secure Coding/Architecture; V16Security Logging/Error Handling; V17WebRTC. OAuth/token/WebRTC hanya N/A beralasan bila tidak digunakan. Jangan menyalin nomor bab ASVS4 sebagai ASVS5. Target baseline audit adalah applicable L2 beserta inherited L1; klaim conformance membutuhkan register setiap requirement+hasil, tidak cukup daftar bab.

ISO25010:2023 dipakai sebagai model perencanaan, bukan sertifikasi. Safety meliputi dampak tindakan keliru terhadap pengguna/operasi, misalnya isolir salah target atau kehilangan layanan; privasi ditempatkan dalam security/data protection. Target WCAG2.2AA tetap baseline. Traceability requirement kritis100%; semua assertion security/finance kritis wajib teruji; line coverage berubah≥85% adalah AUDIT_DEFAULT untuk kode unit-testable, bukan pengganti bukti integrasi atau perangkat. N/A memerlukan alasan dan approval scope yang sudah ada; kebutuhan kritis tidak dapat di-N/A-kan agar lulus.

[REVISI AUD-42] Profil performa default: tahap10/100/1000 tenant,2router/tenant,300service/tenant; CPE200/tenant hanya R3. Steady auth50request/s untuk NAS profil awal dan accounting=active_sessions/300s. Ramp10menit, warmup10menit tidak masuk sampel, steady30menit, soak8jam tahap10/100 dan24jam tahap1000. Storm10% sesi aktif reconnect60detik: pada300000sesi=500auth/s tambahan; uji “ribuan/s” adalah stress profile2000auth/s60detik tersendiri, bukan salah turunan10%. Minimal10000 sampel per metrik percentile; nearest-rank pada sampel mentah, jangan rata-rata p95 tiap menit.

Pass steady: p95list/enqueue≤2detik, p95auth≤100ms, p95aktivasi normal≤60detik dengan jam mulai enqueue hingga policy/auth verified (belum berarti perangkat online); error non-injected<0.1%; tidak ada cross-tenant/unbalanced/duplicate/lost acknowledged effect. Timeout dihitung gagal, bukan dikeluarkan dari sampel; injected failures mempunyai denominator terpisah. Seluruh tenant aktif mendapat progress dalam60detik AUDIT_DEFAULT; queue age resource tetap dalam budget manifest. Fixture100000service/tenant untuk uji query adalah khusus lab capacity_override, tidak mengubah plafon komersial5000. DR drill2kali/tahun adalah kebijakan operasional default setelah deploy, bukan automation yang dibuat oleh audit ini.

Gerbang dievaluasi per `release+feature+adapter_version+topology+load_profile`, bukan semua modul R1 menunggu CPE R3. G0 desain/ADR actual; G1 protokol/perangkat relevan; G2 tenant/security/finance/restore relevan; G3 pilot terbatas; G4 load/soak/availability; G5 operasional/DR. Gate prerequisite bukan izin untuk menjalankan tes; izin ditentukan scope manifest. G0 dapat mengevaluasi desain tanpa lab; TK002/pin/ADR yang belum dibuat tetap BLOCKED. Fitur memiliki flag sandbox terpisah dari produksi.

Prasyarat fitur PRD26 tetap: inti R1 G0+G2T10/T23; VPN G1T01; cutover G1T16/T17/T18/T21; backup G1spike+G2T08/T09; penjualan G2T05SaaS+otorisasi; autoisolir G1T20+G2T05+G3; ledger G2T12+akuntan; voucher G1T16+G2T24; ACS per modelG1/T11; WAN per topologyG1/T13; edgeG4T22; peningkatan kapasitasG4/G5. Kegagalan satu fitur tidak menyembunyikan hasil fitur independen.

## 21. Evidence, privasi, dan pelaporan yang dapat diaudit

[REVISI AUD-43] Case status kanonik: `NOT_RUN`, `BLOCKED`, `RUNNING`, `PASS`, `FAIL`, `NOT_APPLICABLE`. Gate status: `NOT_EVALUATED`, `BLOCKED`, `PASS`, `FAIL`. Feature evidence: implemented, verified_local, verified_lab, release_enabled; ini dimensi berbeda. Staging aplikasi bisa memenuhi verified_local untuk aplikasi nyata; verified_lab jaringan hanya CHR/perangkat relevan. Tidak mewajibkan router untuk fitur i18n/ledger yang tidak memakai router; prod flag tetap menunggu gate fitur.

Evidence record wajib: schema_version, run_id UUID, case_id, parent, requirements, AUD references, authorization_id+scope hash, approved target IDs, effective config hash, manifest hash, commit/artifact hash dan dirty diff bila ada, exact versions/images/license, fixture seed/hash, started/ended UTC, monotonic duration, steps, assertion_id expected/actual/result, metrics raw reference, artifacts{path,sha256,size,classification}, executor, reviewer_type, cleanup_result, status, blocker. Jangan menyimpan expected dan actual sebagai dua daftar yang tidak mempunyai assertion mapping.

Hash bukan tanda tangan dan tidak membuktikan reviewer independen. Satu agent boleh melakukan self-review checklist tetapi `reviewer_type=self_review`; tidak diklaim independent. Gate yang mewajibkan human/professional/external approval tetap BLOCKED bila belum tersedia; tidak menciptakan reviewer fiktif. Source/test/assertion hash menjadi dasar invalidasi bukti: perubahan schema/policy/adapter/firmware/topology/load membatalkan gate terdampak; pengecekan ulang dokumen saja tidak memperpanjang validitas run lama.

[REVISI AUD-44] Raw PCAP RADIUS/PPP dapat memuat material credential/challenge yang sensitif meski semua akun sintetis. Jangan mengunggah raw capture/debug -X sebagai evidence umum. Capture opsional hanya scope khusus; simpan sementara pada volume terbatasi/enkripsi, ekstrak semantik yang sudah disaring (tipe paket, status, pseudonym sesi, waktu), verifikasi redaksi, hash artefak tersanitasi lalu hapus raw sesuai TTL manifest. Jangan menganggap anonimisasi IP/MAC sudah menghapus password/CHAP material. Jangan memakai hash plaintext password sebagai “redaksi aman”. Bukti bayar/secret/recovery keys tidak ditempatkan pada screenshot/JUnit/nama file.

Execution coverage=executed_cases/applicable_required_cases, dengan executed mempunyai actual step evidence; PASS/FAIL terpisah dari BLOCKED yang sudah mulai. Pass rate=PASS/(PASS+FAIL); denominator nol→null, bukan100%. Requirement design coverage dan requirement verified coverage dilaporkan terpisah. NOT_APPLICABLE yang sah dikeluarkan denominator; NOT_RUN/BLOCKED tetap gap wajib. Flaky/quarantine tidak dihitung PASS dan tetap memblokir gate wajib.

Retensi evidence gate≥umur rilis terkait+90hari setelah superseded; incident400hari; financial10tahun atau legal hold; raw transient capture TTL manifest maksimum24jam default. Metadata sanitized dapat di git privat; raw logs/backup tidak di git. Artifact store failure menahan run yang membutuhkan evidence. Cleanup evidence tidak dilakukan sebelum review/retention/legal hold dipenuhi.

[REVISI AUD-45] UU PDP: tenant bertindak pengendali data pelanggan dan platform prosesor untuk pemrosesan itu; platform dapat menjadi pengendali untuk data akun/billingnya sendiri. Runbook insiden tidak boleh hanya “waktu nanti ditinjau”. Pasal46 UU27/2022 memuat kewajiban pemberitahuan tertulis pengendali paling lambat3×24jam kepada subjek dan lembaga, dengan konten pokok insiden. Kontrak internal menetapkan eskalasi platform kepada pengendali segera, target≤24jam sejak diketahuinya kegagalan, agar pengendali dapat memenuhi tenggat; detail pemicu dan kanal diverifikasi counsel saat rilis. Kewajiban ini bukan pengiriman notifikasi yang dilakukan audit sekarang.
