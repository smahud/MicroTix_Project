# MicroTix — acceptance dan kesiapan rilis

Dokumen ini memiliki T01–T24 dan G0–G5. Detail desain berada pada [test-cases.json](test-cases.json): 84 kasus baseline (318 assertion) dan 172 skenario requirement (344 assertion). Ini katalog desain, bukan 256 hasil PASS atau kewajiban menulis 256 fungsi test yang saling menyalin. Satu automated test dapat membuktikan beberapa assertion yang sama, asalkan mapping expected→actual jelas. ID lama tetap dapat ditelusuri.

## 1 Scope dan fixture

Pilih fase/feature/resource yang sudah diimplementasikan, dua tenant sintetis A/B dengan username sama, NAS A1/A2/B1, sesi non-target, fixture seed261029. Simpan versi/config/commit dan input yang menentukan hasil. Jangan menerapkan semua assertion R3/R4 sebagai prasyarat build R1. Label environment/release kasar pada katalog adalah pengarah; tiap assertion mengikuti resource/operasi aktual dan tabel fitur di bawah.

Kategori bukti: unit untuk logika murni/kalender; integration PostgreSQL nyata untuk RLS/constraint/transaksi/races; FreeRADIUS Linux nyata untuk server auth/accounting; simulator RouterOS untuk kontrak dan fault deterministik; CHR/perangkat nyata untuk transport/priority/local-shadow/Disconnect/backup/cutover; CPE nyata untuk model/firmware; pilot/load/DR untuk operasi yang relevan. Database mock/SQLite tidak membuktikan RLS. Browser UI harus berinteraksi dengan API nyata.

Common execution: setup before-state, jalankan actions, ukur setiap assertion expected/actual, simpan bukti tersanitasi, cleanup hanya owned resources. Satu case yang baru teruji sebagian tetap belum wholly PASS. Retransmission/timeouts/crash dan kontrol non-target bukan opsional untuk uang/isolir/migrasi.

## 2 Skenario produk T01–T24

| ID | Skenario | Lulus bila |
|---|---|---|
| T01 | Bootstrap pada router existing | Tidak ada perubahan default route/bridge/akun existing; objek manajemen baru terbatas preview; sesi kontrol dipantau |
| T02 | Impor berulang dan profile bersama | Tidak duplikat; tidak menulis router; mapping benar |
| T03 | Secret non-PPPoE, `service=any`, RADIUS eksternal | Tidak salah adopsi; unsupported ditandai |
| T04 | CSV update dan data rusak | Preview benar; retry aman; tanpa jurnal |
| T05 | Payment race dan bulk activation | Satu posting; job memeriksa state terbaru; hasil per item |
| T06 | Worker crash di tengah langkah router | Readback dan dedup; tidak ada objek/akun ganda |
| T07 | Isolir pada kombinasi PPPoE/Hotspot/IPv6 | Hanya target; login ulang dan jalur alternatif diuji |
| T08 | Backup ke-101 dan transfer putus | 100 generasi valid; tak ada file terpotong berlabel sukses |
| T09 | Restore lab | Perangkat/versi yang disahkan pulih; keterbatasan tercatat |
| T10 | Akses tenant dan support | Percobaan lintas scope ditolak dan diaudit |
| T11 | ACS task dan konflik identitas | Pending ≠ sukses; klaim salah tak memperoleh kredensial |
| T12 | Akuntansi | Debit=kredit; subledger cocok; closed period; bypass direct-write ditolak; setoran kolektor |
| T13 | Failover/PCC/Hotspot | Lulus per topologi; batas sesi tercatat |
| T14 | Outage dan restore platform | Backlog tidak menjalankan keputusan lama; RPO/RTO terukur |
| T15 | Soak dan reconnect storm | Tanpa starvation/lost transaction; resource dalam budget |
| T16 | RADIUS PAP/CHAP/MS-CHAPv2 pada PPPoE dan metode Hotspot yang didukung | Valid diterima, salah ditolak; atribut benar |
| T17 | Cutover RADIUS dan rollback | Sesi lama tidak terputus; prioritas lokal/RADIUS tercatat |
| T18 | Akun lintas router, penggantian router, perpindahan | Login tanpa input ulang; pool sesuai router |
| T19 | Isolasi tenant RADIUS | Username sama lintas tenant tak saling terlihat |
| T20 | Isolir/aktivasi via Reject + Disconnect | Sesi terputus, login ditolak, aktivasi memulihkan hanya target |
| T21 | Accounting dan Simultaneous-Use | Sesi tercatat, interim basi dibersihkan, sesi kedua ditolak |
| T22 | RADIUS outage; edge replica hanya bila fitur edge dalam scope | Sesi existing tetap; perilaku sambungan baru sesuai rancangan |
| T23 | i18n | Semua layar dan dokumen dalam id/en/pseudo-locale; fallback; zona waktu |
| T24 | Voucher dan agen | Reservasi kuota, kedaluwarsa, komisi, jurnal |

## 3 Gate per fitur

Gate dinilai per release+feature+adapter/build+topology+load+config. G0 desain/kontrak tidak menunggu CPE R3; G2 ledger tidak memblokir desain UI R1. Izin menjalankan test terpisah dari hasil gate: QA sandbox boleh menguji fitur untuk memenuhi gate; tidak perlu menyalakan flag produksi dahulu.

| Gerbang | Isi |
|---|---|
| G0 | Desain/ADR: dokumen aktif, keputusan stack, kontrak enum/state yang dipakai fase aktif |
| G1 | Lab RouterOS nyata/CHR (termasuk RADIUS, T16–T17, T20–T21) dan CPE model; fixture dan versi terkunci; spike backup |
| G2 | Keamanan dan isolasi tenant, integritas finansial/retry, restore backup, review akuntan |
| G3 | Pilot tenant terbatas dengan baseline traffic dan sesi; inventory VM selesai |
| G4 | Benchmark workload, load/soak/reconnect storm, HA RADIUS |
| G5 | Observability, runbook, recovery drill (DR) |

**Prasyarat aktivasi fitur (`release_enabled`):**

| Fitur | Gerbang minimum |
|---|---|
| R1 inti (tenant, UI, CSV, adopsi database-only, multi bahasa) | G0, G2 (T10, T23) |
| Koneksi router/VPN | G1 (T01) |
| Cutover RADIUS dan mode otoritatif | G1 (T16, T17, T18, T21) |
| Backup | G1 (TK-505), G2 (T08, T09) |
| Penjualan paket berbayar | G2 (T05 sisi SaaS) + otorisasi pemilik |
| Auto-isolir produksi | G1 (T20), G2 (T05), G3 |
| Pembukuan produksi | G2 (T12 + review akuntan) |
| Voucher/agen | G1 (T16), G2 (T24) |
| ACS R3 (per model) | G1 (matriks CPE), T11 |
| Wizard WAN (per topologi) | G1, T13 |
| Edge replica RADIUS | G4 (T22) |
| Peningkatan kapasitas (10→100→1.000) | G4, G5 |

Semua fitur tetap mewarisi G0 dan kontrol tenant/security fase aktif. Tabel adalah tambahan bukti domain, bukan pengecualian keamanan umum. Penangguhan/restore manual akun R1 juga memerlukan T20 dan uji hold/retry arah yang relevan sebelum dipakai pada perangkat produksi; membangun UI akun tidak melewati gate itu.

## 4 Invariant dan negative tests yang tidak dapat dilewati

- Nol akses/atribut/accounting/backup/ledger lintas tenant, nol wrong Accept RADIUS dan nol aksi salah sasaran. Uji membership/role/SupportGrant, composite FK, RLS context rollback/pool reuse, cache/metrics/export/download dan portal berdasarkan resource fase aktif.
- Idempotency/source-event dan lock pada dana/alokasi/entitlement/invoice/kuota tahan retry dan race. Periode31Jan→28/29Feb→31Mar, annual leap-year, timezone WIB/WITA/WIT, upgrade bonus tidak drift/diterapkan dua kali. Debit=kredit, recognition/residual/tax split, closed period dan direct DML bypass diuji nyata.
- Discovery/adopsi/import tidak menulis router; credential unknown tidak memperoleh Accept; B5 local shadow dan rollback per revision diuji di CHR. Message-Authenticator/unknown NAS invalid tidak Accept; secure discard adalah hasil sah.
- Crash sebelum/sesudah DB commit/send/ack dan stale writer tidak menggandakan efek. uncertain memerlukan readback; cancel hanya none+fence. Payment tidak auto restore; manual hold mengalahkan lunas; suspend dan restore memakai verifier berbeda.
- Backup101 hanya prune sesudah complete/durable/committed, transfer terputus/disk penuh/prune crash tidak menghapus generasi valid. Restore sampel membuktikan recovery; hash file saja tidak membuktikan file sumber lengkap.
- Upload MIME/size/scan fail-closed, CSRF, XSS, SSRF/DNS rebinding/redirect, credential redaction, token expiry/replay, session revocation/recovery. Tidak ada raw script/SQL/URL arbitrary dari user.
- UI id/en/pseudo-locale, four-status separation, five quick tabs, role/phase menu, keyboard/focus/contrast dan mobile; rename branding tidak merusak sesi/data/integrasi. Tidak ada placeholder success/tombol tidak berfungsi.

ASVS5 menjadi referensi kontrol relevan dan WCAG2.2AA tetap target aksesibilitas; jangan mengklaim full ASVS L2/sertifikasi ISO dari jumlah checklist. Policy MFA baseline ARCHITECTURE §3 diuji. Kontrol standar yang akan menambah kebijakan pengguna dibuat keputusan eksplisit, bukan menahan semua pekerjaan karena audit lama belum punya signature.

## 5 Test status dan evidence

Status case: NOT_RUN/BLOCKED/RUNNING/PASS/FAIL/NOT_APPLICABLE. Gate: NOT_EVALUATED/BLOCKED/PASS/FAIL. Tidak menjalankan bukan FAIL; assertion salah bukan BLOCKED. FAIL kritis mengalahkan agregat lain. N/A hanya bila fitur/resource benar-benar tidak ada dalam scope dan alasan tercatat; bukan untuk menutupi kontrol yang gagal.

Evidence minimum: run_id/case/assertion_id, requirement, commit+dirty diff bila ada, exact versions/topology/config, target/akses yang dipakai, UTC start/end+duration, command+exit, expected/actual/result per assertion, artifact path/hash dan cleanup. Record hasil di docs/progress.md dan evidence tersanitasi atau CI; jangan menimpa katalog expected dengan PASS rekaan. PASS hanya seluruh assertion scope yang dipilih terbukti.

Tidak upload debug -X/raw PCAP PPP/RADIUS/password/bukti bayar/PII ke evidence umum. Capture hanya jika scope mengizinkan, encrypted/restricted sementara, ekstrak semantik redacted dan hapus raw sesuai TTL. Hash password bukan redaksi aman. Reviewer dicatat self_review atau reviewer faktual; satu penulis yang memakai dua parser bukan review independen. Review akuntan/legal sebelum penggunaan resmi yang memang memerlukannya tetap dicatat nyata, tidak menggantungkan build kode lokal.

## 6 Definition of Done

Per vertical slice: requirement terpenuhi, schema/API/UI berfungsi bersama, test relevan+error/security paths lulus, tidak ada known critical/high exploitable issue, checkpoint dan cara menjalankan tersedia. implemented/verified_local/verified_lab/release_enabled adalah dimensi berbeda. Menu harian produksi hanya release_enabled; sandbox flag terpisah untuk QA.

Pilot awal mengikuti defaults (1 tenant/1 router/50 service, observasi minimal7 hari dan mencakup siklus relevan). Load/soak, host HA, model CPE/OLT dan profesi review diminta saat fitur/kapasitas itu hendak diaktifkan. Long observations memakai waktu nyata dan checkpoint durable, bukan fake clock. Perubahan schema/policy/firmware/config membatalkan evidence terdampak.

Status saat audit dokumentasi ini: runtime aplikasi0, semua case NOT_RUN, gate aplikasi belum dievaluasi. Validator docs hanya memeriksa struktur/integritas. Dokumen siap menjadi input build; produksi baru siap setelah bukti dan scope perubahan terkait benar-benar terpenuhi.
