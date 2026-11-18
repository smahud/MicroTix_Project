# Review independen task 0020 R4 — kewenangan dan batas commit

| Field | Bukti |
|---|---|
| Reviewer | OpenAI Codex `/root/authority`, 18 November 2026 WIB |
| Scope | PA-003 REV-1711-05, J20-A06/A07/A08, serta batas transaksi dan lease J20-A01/A02/A05 yang tersentuh |
| Instruksi | PR35 `e0d306a718e59361a3e3bc27bce747eb90f1b5dc`, [controller R4](../controller/20261118T025143Z-0020-r4-review.md), [laporan executor](../orchestrator/20261118T035535Z-0020-r4-correction.md) |
| Source yang diperiksa | Implementation/tested `77a4a9056c1c5cf9b0b0874b0630a16dd350aa09` |
| Ref penyerahan dan main | PR36 `3eaae2add1a4b4e9415bd51fabcf1eb0601444de`, starting main `5c452763e8c8fb8976d06dad16d0b68c7da14f95` |
| Otoritas | `CONTRACT.md` §§5–6A/8–10, PRODUCT TEN-03/JOB-02–05/SEC-01/04/05, ARCHITECTURE §§3–6 dan acceptance task yang berlaku |
| Verdict mandiri | **changes_requested** pada kewenangan dan fencing commit. Verdict akhir dan pemutakhiran packet milik controller. |
| Perubahan dan publikasi | Kode, test suite, probe beku, kontrak, serta konfigurasi dibaca saja. Handoff Markdown ini adalah satu-satunya perubahan sub-review. NOT COMMITTED / NOT PUSHED oleh reviewer ini. |

## Verifikasi source dan bukti yang diwariskan

- GitHub compare `e0d306a...77a4a90` dan recursive Git trees pada empat SHA di atas berhasil diperiksa. Seluruh pasangan path/mode/blob berubah dari tested SHA ke PR36 head hanya menyentuh enam path laporan/task/progress. Ke starting main hanya tujuh path laporan/task/progress berubah. Empat file probe authority R1–R4 memiliki blob dan mode identik pada decision base, tested SHA, published head dan starting main. Blob probe R4 `03068492e481ce914fd2530663c99d15b326e79f`.
- Jalur R4 pada [handler](../../backend/domains/network/handlers.py#L80-L106) meneruskan guard authority terkunci. [Service](../../backend/domains/network/services.py#L1349-L1379) menjalankannya di unit efek yang sama setelah perubahan kredensial WG/SSTP. [Guard](../../backend/domains/jobs/engine.py#L698-L718) mengunci baris membership unik user/tenant dan memeriksa role aktual. Revoke yang sudah commit ketika UPDATE kredensial tertahan terdeteksi dan seluruh unit efek rollback. Tahan hasil pengecekan itu dan seluruh koreksi sebelum R4.
- [Probe R4 beku](../controller-evidence/20261118T025143Z-0020-r4/test_r4_authority_credentials.py) mengamati blocker PostgreSQL pada UPDATE kredensial, revoke yang sudah commit, serta state Router, kredensial, enrollment dan job. [Log executor](../executor-evidence/20261118T035535Z-0020-r4-correction/r4-authority.log) mencatat **2 passed** untuk kedua protokol. [Regresi CI](../../backend/tests/integration/test_jobs_r4_residuals.py#L390) memeriksa pola yang sama. Hasil runtime ini diatribusikan kepada executor. Reviewer ini membaca kode, diff, blob dan log.
- TLS/readback awal berada di luar transaksi di [service](../../backend/domains/network/services.py#L1219-L1236). Unit efek sesudahnya masih memakai tenant scope yang sama. Pengecualian `JobError(authority_denied)` di callback memicu rollback dan jalur failure engine. Guard baru tidak memakai sesi/token HTTP. Tidak ada perubahan source pada API detail/retry/cancel ataupun kontrak verifier. Jalur duplicate-finalize masih menolak dengan galat ter-tipe `enrollment_state`.

## REV-1711-05 — PARTIAL P1 pada actor aktif

R4 menutup kasus perubahan **membership** selama wait kredensial. Invariant
aktor aktif pada J20-A06 belum tertutup. [engine.py:624–637](../../backend/domains/jobs/engine.py#L624-L637)
membaca actor dari `identity_user` dengan SELECT biasa. Pemeriksaan
[`is_active` di baris 676–696](../../backend/domains/jobs/engine.py#L676-L696)
menggunakan hasil baca itu, sebelum
[SELECT FOR UPDATE membership di baris 698–704](../../backend/domains/jobs/engine.py#L698-L704).
Kedua model memiliki baris berbeda. [Model User](../../backend/domains/identity/models.py#L37-L54)
menyimpan flag aktif, sedangkan [model Membership](../../backend/domains/tenancy/models.py#L56-L75)
menyimpan role, scope dan revoke. Penguncian membership sendiri tidak
menyerialisasi perubahan flag aktif. Pengubahan status akun yang sudah commit
selama guard menunggu row lock membership dapat meninggalkan snapshot actor
aktif sampai akhir transaksi. Guard berikutnya hanya mengecek membership dan
scope. Unit Router/kredensial/enrollment dapat commit dengan actor tersebut
telah nonaktif.

Ini temuan source pada batas authority yang diwajibkan task. Reviewer belum
menjalankan validasi runtime untuk urutan tambahan ini dan tidak
mengasumsikan tersedia endpoint HTTP penonaktifan akun. Dua probe credential
wait mengubah `revoked_at`; keduanya tidak memeriksa serialisasi flag akun.

**Koreksi minimum dan acceptance.** Lindungi sumber fakta actor aktif bersama
baris membership yang otoritatif hingga commit, dengan urutan lock konsisten
dan query tenant/RLS tetap scoped. Pemeriksaan final harus menangkap perubahan
yang sudah commit ketika unit menunggu. Validasi regresi termonitor pada PG
split-role harus membuktikan aktor dinonaktifkan sebelum batas commit
menghasilkan Router 0, kredensial tetap pending, enrollment belum completed
dan job tidak sukses. Pertahankan keberhasilan enrollment yang sah serta
semua probe revoke/demote/scope yang berlaku. Seluruh TLS/device I/O tetap
di luar transaksi.

## REV-1711-01 — PARTIAL pada urutan guard commit R4

[Guard ownership](../../backend/domains/jobs/engine.py#L355-L385)
mengunci row job dan menilai waktu expiry aktual. Pada R4,
[service](../../backend/domains/network/services.py#L1359-L1379)
menjalankan guard ini **sebelum** guard authority terkunci. Guard authority
dapat menunggu row membership. Saat itu job row tetap terkunci.
[Watchdog](../../backend/domains/jobs/engine.py#L759-L773) memakai UPDATE
baris job yang sama melalui koneksi lain, sehingga perpanjangannya tidak
commit selama kunci itu dipegang. Waktu lease dapat lewat sebelum lock
membership diperoleh. Setelah guard authority lulus, unit dapat commit
Router, enrollment selesai dan kredensial aktif tanpa penilaian ulang
validitas lease. Serialisasi perubahan token/epoch lewat job row lock
tetap berguna, tetapi expiry berbasis jam tidak dicegah oleh kunci.
Peralihan state job setelah transaksi tidak dapat membatalkan efek DB
yang telanjur commit.

**Koreksi minimum dan acceptance.** Validasi final token/epoch/state/lease
setelah seluruh penguncian authority/resource yang dapat menunggu, dengan
urutan lock konsisten. Terus pegang lock yang mendasari validasi authority
saat commit. Validasi regresi harus menunjukkan wait DB yang melampaui lease
awal tanpa renewal efektif menolak commit efek dan tidak melaporkan sukses.
Uji juga kasus lease masih aktif yang menyelesaikan unit sekali. Pertahankan
hasil probe expiry, renewal dan transfer R3. Temuan ini terbukti pada urutan
source. Validasi runtime tambahan NOT_RUN oleh reviewer ini.

## Handoff

| Acceptance | Penilaian reviewer |
|---|---|
| A01/A05 | **FAIL pada urutan source**. Validitas lease dapat lewat selama guard akhir yang baru. Scope proof proses/drain tidak diubah. |
| A02 | Mekanisme RLS dan pemisahan TLS/DB dipertahankan pada source. Bukti PG runtime milik executor/controller. |
| A06 | **FAIL pada urutan source**. Dua kasus revoke membership R4 lulus menurut executor, sedangkan flag actor aktif belum diserialisasi. |
| A07 | Tidak terlihat regresi source dalam diff R4. Probes API dan verifier tetap menjadi bukti runtime yang diatribusikan ke pelaksananya. |
| A08 | Existing suite mencakup SIGTERM/SIGINT idle, cooperative dan blocked, serta SIGKILL dan reconcile. Reviewer tidak menjalankan ulang proses atau systemd dan tidak mengklaim kesiapan host. |

Pemeriksaan mandiri selesai melalui pembacaan GitHub exact ref dan
perbandingan rekursif path/mode/blob. NOT_RUN oleh reviewer ini meliputi
pytest/Django, PG, proses drain, E2E, installer/upgrade/restore/systemd,
RADIUS langsung, RouterOS/CHR/GNS3 dan benchmark. Tidak ada keputusan
release atau perubahan produk dari sub-review. Controller mengintegrasikan
bukti dan mengarahkan coding agent mengoreksi acceptance terdampak pada
ID 0020, sambil mempertahankan closure dua skenario revoke R4.
