# 0020 — PA-002 + PA-003: job aman terhadap stale worker dan perubahan kewenangan

| Field | Nilai |
|---|---|
| Task ID | `0020`; satu packet untuk lifecycle + authority yang saling bergantung |
| Execution status | **done** — koreksi R6 diserahkan pada ID0020 (rename `_done` bagian commit penyerahan); menunggu review controller |
| Review status | **pending** untuk koreksi R6 (kandidat baru). Histori: changes_requested R5 pada exact `3301c29` [sudah ditindaklanjuti koreksi R6 ini](../report/orchestrator/20261119T083000Z-0020-r6-correction.md). |
| Resume controller 17 Nov ~21:48 WIB | Histori checkpoint sebelum koreksi: [checkpoint](../report/controller/20261117T144620Z-0020-resume-review.md); klaim closure executor REV-1711-01–09 dinilai ulang pada R2/R3 |
| Controller / executor | ChatGPT Work controller / coding agent sandbox |
| Baseline | Koreksi R6 dari main `51158c0` (merge PR #39 decision records R5; delta terhadap `0616a80` hanya packet/laporan/handoff/progress). |
| Original instruction ref | PR26 `review/0020-job-lifecycle-authority-20261117` @ `ea7b8a17ad8d6339eed45769bbff1626ea279665`; histori instruksi awal |
| Current correction instruction ref | `review/0020-r5-correction-20261118-1723` @ `b32203a` (PR #39, integrated `51158c0`), [keputusan dan acceptance koreksi](../report/controller/20261118T172344Z-0020-r5-correction-review.md). Ref R4-correction dan PR #37 tersimpan sebagai histori. |
| Accepted predecessor | [0010 / PA-006](0010-pa006-idempotency_done.md), accepted exact `a301a94c2b3268679065e85bbef66f35949483f7` pada [R5 review](../report/controller/20261116T101809Z-0010-pa006-r5-review.md); PR24+PR25 merged ke main, [integrasi](../report/orchestrator/20261116T111835Z-0010-pa006-integration.md) |
| Authority | [CONTRACT](../CONTRACT.md) §§5–6A/8–13; [PRODUCT](../docs/PRODUCT.md) TEN-03, JOB-02–05, SEC-01/04/05, SUB-05; [ARCHITECTURE](../docs/ARCHITECTURE.md) §§3–6; [OPERATIONS](../docs/OPERATIONS.md) §§3–4; [ACCEPTANCE](../docs/ACCEPTANCE.md) §4 |
| Backlog / tests | Existing TK-101/102/103 dan bagian drain TK-1002; katalog T06-CRASH-01/02/03, T10-TEN-03; T05/T14 hanya invariant current-state yang relevan, bukan seluruh fitur R2/DR |
| Controller report | [Keputusan current R5](../report/controller/20261118T172344Z-0020-r5-correction-review.md), [bukti PostgreSQL](../report/controller-evidence/20261118T172344Z-0020-r5-correction/runtime.md). [Review R4-correction](../report/controller/20261118T050714Z-0020-r4-correction-review.md) dan penyerahan sebelumnya tetap menjadi histori. |
| Correction implementation / tested / candidate | **Histori koreksi R2 (kandidat yang dinilai R3):** impl/tested **`cd6eea378cd2134ca38924e8b181d1cd601f33ec`** (kode+tes saja) dari base main `0c6403de` (PR31 merged); published candidate = head PR32 (commit penyerahan, report-only descendant). Histori koreksi R1: impl2681a3d, PR30 head19023737 merged (9eb5dacf) |
| Koreksi R2 — laporan & bukti | [Laporan eksekusi](../report/orchestrator/20261117T194548Z-0020-r2-correction.md) — matriks A01–A09 + pemetaan presisi A05/A08; [reviewer independen](../report/reviewer/20261117T194548Z-0020-r2-correction-independent.md): 5/5 temuan R2 CLOSED + 5 temuan baru REV-R2C-01..05 (semua ditutup sesi ini); [evidence](../report/executor-evidence/20261117T191917Z-0020-r2-correction/) — probe R2 6/6 + R1 11/11 lulus tanpa pelemahan (file probe controller FROZEN), suite penuh 583 passed/1 skip, check/makemigrations/docs/frontend PASS |
| Histori bukti executor R1 | **Probe controller R1: failing-before 11 failed → passing-after 11 passed** (diulang pada DB split-role migrator-owned + FORCE RLS); **suite penuh 562 passed + 1 skip** (+8 tes bukti REV-1711-09: SIGINT/active-barrier/stop-claim, fase panjang vs reconciler, crash setelah commit domain, current-policy/SUB-05); PA-001 33 + PA-006 125 + RLS 8 lulus; check/makemigrations/docs PASS; [evidence root](../report/executor-evidence/20261117T150000Z-0020-correction/) |
| Historical correction execution report | [Orchestrator koreksi](../report/orchestrator/20261117T160000Z-0020-correction-delivery.md) — matriks A01–A09 + temuan→perubahan→bukti; [reviewer independen](../report/reviewer/20261117T160500Z-0020-correction-independent.md): REV-1711-01–09 CLOSED, temuan P2 CORR-REV-01/02 ditutup sebelum commit; [laporan penyerahan pertama](../report/orchestrator/20261117T010218Z-0020-job-lifecycle-authority.md) histori |
| Next actor / action | **controller_reviewer**. Review exact implementation/tested SHA koreksi R6 (lihat baris Koreksi R6 di bawah): ulang probe lock-wait controller 6/6 + 28 probe beku + 18 regresi R5 + 15 regresi R6 + suite penuh; nilai matriks A01–A09 laporan R6. accepted ⇒ siapkan task dependent; changes_requested ⇒ buka ID sama. |
| Koreksi R6 implementation / tested | **`6ba52c720f43dd6ca1587e095f91b3b011f2a994`** (kode+tes+evidence) pada branch `session/2026-11-19-0020-r6-correction` (base `51158c0`); published candidate = head PR (commit penyerahan, report-only descendant). |
| Koreksi R6 — laporan & bukti | [Laporan eksekusi R6](../report/orchestrator/20261119T083000Z-0020-r6-correction.md) — temuan→perubahan→bukti + matriks A01–A09 + batas; [evidence](../report/executor-evidence/20261119T083000Z-0020-r6-correction/) — probe controller lock-wait **6/6 PASS** (BASE R5: 4 FAIL) + 28 probe beku R1–R4 + regresi controller 2/2 + regresi R3/R4/R5 **31/31** + **15 regresi R6 baru** (failing-before BASE `51158c0`: 11 FAIL/4 kontrol PASS) + suite penuh **629 passed/1 skip** + check/makemigrations/docs PASS, split-role migrator-owned + mtx_app NOSUPERUSER/NOBYPASSRLS FORCE RLS PG17.4, tanpa migration baru |
| Koreksi R5 implementation / tested | `3301c2940dbfa9293ae52b8d8479b2050c16ebef` (histori — changes_requested, ditindaklanjuti R6); [PR #38](https://github.com/smahud/MicroTix_Project/pull/38) `ccea781458b4b90a40f97f5b07139965b4a85963`, integrated `e19b08f`. |
| Koreksi R5 — laporan & bukti | [Laporan eksekusi R5](../report/orchestrator/20261118T115321Z-0020-r5-correction.md) — temuan→perubahan→bukti + matriks A01–A09 + batas; [evidence](../report/executor-evidence/20261118T113641Z-0020-r5-correction/) — 28 probe beku R1–R4 PASS + regresi controller terminal-lease 2/2 + **18 regresi R5 baru** (failing-before BASE: 2+11 FAIL identik temuan) + suite penuh **614 passed/1 skip** + check/makemigrations/docs PASS, split-role migrator-owned + mtx_app NOSUPERUSER/NOBYPASSRLS FORCE RLS PG17.12 |
| Koreksi R4 implementation / tested | **`77a4a90`** (kode+tes+evidence; base decision head `e0d306a`) |
| Koreksi R4 — laporan & bukti | [Laporan eksekusi R4](../report/orchestrator/20261118T035535Z-0020-r4-correction.md) — matriks A01–A09 + failing-before/passing-after; [evidence](../report/executor-evidence/20261118T035535Z-0020-r4-correction/) — probe R4 **4/4 PASS** (cross-process resolve DITOLAK writer_active/nol successor send; no-effect final FAILED; credential-wait WG+SSTP Router0/PENDING/failed authority_denied), frozen R1/R2/R3 **24/24 PASS tanpa pelemahan**, suite penuh **596 passed/1 skip/3 warnings** (588 baseline + 8 regresi R4), check/makemigrations/docs PASS, split-role migrator-owned + mtx_app NOSUPERUSER/NOBYPASSRLS FORCE RLS |
| Koreksi R3 implementation / tested | **`16db545`** (kode+tes saja; base decision head `05d268d`) |
| Histori executor R3 — laporan & bukti | [Laporan eksekusi](../report/orchestrator/20261118T022200Z-0020-r3-correction.md) — matriks A01–A09 + failing-before/passing-after executor; [reviewer independen](../report/reviewer/20261118T022200Z-0020-r3-correction-independent.md): 01/05/1811-01 CLOSED, 04 cukup untuk scope probe + residual REV-R3C-01 (P2 laten, terdokumentasi dengan analisis konflik terhadap closure R1) & REV-R3C-02 (P3, didokumentasikan); [evidence](../report/executor-evidence/20261118T000000Z-0020-r3-correction/) — probe R3 7/7 + frozen R1/R2 17/17 lulus tanpa pelemahan (file probe FROZEN), suite penuh 589 passed/0 skip (583 baseline + 1 radius unskip sandbox + 5 tes baru), check/makemigrations/docs PASS |

PA-002/PA-003 adalah label kontinuitas audit, bukan otoritas baru. PR8 planning_audit kini terintegrasi sebagai record historis melalui merge-all; kebutuhan packet ini tetap diturunkan dari kontrak/domain requirements di atas. Prasyarat PA-006 sudah accepted/integrated dan tidak dibuka kembali. PA-001 pembayaran juga dipertahankan. Packet ini tidak memberi izin merge, deploy, tag atau aktivasi fitur.

## Penyerahan koreksi R6, 19 November 2026

**done / pending review.** Executor menutup empat residual PARTIAL controller
([keputusan R5-correction](../report/controller/20261118T172344Z-0020-r5-correction-review.md))
pada ID0020 yang sama di atas decision head `b32203a` (branch instruksi
`review/0020-r5-correction-20261118-1723`/PR #39, ter-merge ke main sebagai
`51158c0` atas wewenang pemilik), branch kerja `session/2026-11-19-0020-r6-correction`:

- **REV-1811-02** — settlement no-effect menilai lease SEGAR SETELAH kunci
  baris job diperoleh (step-0 lock-first): final/nonfinal yang lease habis
  SELAMA tunggu lock tetap EXECUTING dengan token/epoch awal tanpa error
  sampai reconciler; kontrol lease valid tetap FAILED/RETRY_WAIT sekali.
- **REV-1711-01 (watchdog)** — watchdog kunci baris job dulu lalu menilai
  expiry pasca-lock: lease kedaluwarsa selama tunggu TIDAK dihidupkan
  kembali (expiry lama dipertahankan); pola lock-first juga diterapkan ke
  seluruh fence worker (`_fenced`, `_fenced_update`, result commit,
  verify-only commit).
- **REV-1711-01 (enrollment FK deferred)** — akuisisi kunci referensial
  tenant (`FOR KEY SHARE`) DI DALAM unit efek SEBELUM fence akhir: tunggu
  pemeriksaan FK DEFERRABLE di COMMIT kini selesai sebelum validasi expiry
  segar terakhir — lease yang habis selama tunggu → NOL efek domain
  (Router 0, kredensial PENDING, enrollment VERIFYING).
- **REV-1711-04** — readback negatif terikat urutan bukti stop→observasi
  pada job/epoch sama: parameter `readback_observed_at`; pra-stop DITOLAK
  (`readback_before_stop`), attestasi tanpa receipt DITOLAK fail-closed
  (`readback_unbound`), pasca-stop sah membuka pemulihan tanpa kirim
  duplikat; jalur positive/stale/unknown tetap.
- **REV-1711-05** — batas efek `router_release`/`router_replace` memakai
  guard authority TERKUNCI (user+membership sampai commit) SETELAH seluruh
  tulisan unit yang dapat menunggu lock domain: penonaktifan/pencabutan
  yang ter-commit selama tunggu → rollback unit (router tetap aktif,
  kredensial/NAS tetap, NOL enrollment pengganti, job FAILED
  authority_denied); replace juga mengunci referensial tenant sebelum
  INSERT enrollment pengganti.

Bukti: probe controller lock-wait **6/6 PASS** (sebelumnya 4 assertion FAIL
pada R5) + **28/28 probe beku R1–R4 PASS tanpa pelemahan** + regresi
controller terminal-lease **2/2 PASS** + regresi R3/R4/R5 **31/31 PASS** +
**15 regresi R6 baru PASS** (failing-before pada BASE `51158c0`: 11 FAIL /
4 kontrol PASS) + suite penuh **629 passed/1 skip/3 warnings** (614 baseline
+ 15 R6) + check/makemigrations/docs PASS, semua pada PostgreSQL 17.4
split-role migrator-owned, `mtx_app` NOSUPERUSER/NOBYPASSRLS, FORCE RLS.
Tanpa migration baru. [Laporan R6
eksekusi](../report/orchestrator/20261119T083000Z-0020-r6-correction.md)
memuat temuan→perubahan→bukti + matriks A01–A09 + batas;
[evidence](../report/executor-evidence/20261119T083000Z-0020-r6-correction/).
Next actor: **controller_reviewer** mereview exact implementation/tested
SHA koreksi R6.

## Koreksi controller atas penyerahan R5 — 19 November 2026 WIB (histori, ditindaklanjuti R6 di atas)

**`ready / changes_requested`** untuk exact tested `3301c2940dbfa9293ae52b8d8479b2050c16ebef`.
[Laporan controller](../report/controller/20261118T172344Z-0020-r5-correction-review.md) memetakan temuan dan J20-A01–A09.
Controller mengulang 28 probe beku, 2 regresi settlement terdahulu,
18 regresi R5 dan suite penuh 614 passed / 1 skip. [Bukti tambahan](../report/controller-evidence/20261118T172344Z-0020-r5-correction/runtime.md)
mencatat 4 assertion gagal, 2 kontrol lulus dan 0 error harness pada
PostgreSQL 17.11 split-role. CI PR #38 dan main masing-masing 3/3 sukses.

| Finding | Koreksi minimum dan bukti penutup |
|---|---|
| **REV-1711-01 P1 PARTIAL** | Pada seluruh fence worker terdampak, evaluasi token, epoch, state dan expiry sesudah kunci yang dapat menunggu. Selesaikan pemeriksaan referensial yang dapat menunggu sebelum fence akhir domain. Buktikan watchdog tidak menghidupkan lease lama, nol overwrite atau commit efek setelah expiry, dan kontrol valid renew/commit sekali. Enrollment yang melewati expiry dalam tunggu constraint harus menghasilkan Router 0, kredensial pending dan enrollment belum completed. |
| **REV-1811-02 P2 PARTIAL** | Validasi lease settlement sesudah memperoleh lock job. Pertahankan transaksi atomik, epoch, backoff dan callback pascacommit. Final dan nonfinal yang melewati expiry saat terkunci tetap `executing` dengan token/epoch awal dan error kosong hingga reconciler. Kontrol final valid failed sekali dan nonfinal valid backoff. |
| **REV-1711-04 P1 PARTIAL** | Pertahankan positive verify-only setelah penulis berhenti, CAS epoch, karantina unknown dan progres router lain. Ikat negative readback ke stop proof serta job/epoch yang sama. Observasi pra-stop dan visibilitas writer yang belum terbukti tetap menahan mutasi. Buktikan negative readback sah pasca-stop dengan nol send duplikat. |
| **REV-1711-05 P1 PARTIAL** | Pertahankan closure enrollment WG/SSTP. Periksa dan serialisasikan fakta authority pada batas efek `router_release`/`router_replace`. Jika perubahan authority commit lebih dulu, buktikan router tetap aktif, kredensial/NAS tetap, enrollment pengganti 0 dan job tidak sukses. Kontrol berizin tetap commit sekali. |

Jalankan [probe lock-wait controller](../report/controller-evidence/20261118T172344Z-0020-r5-correction/test_review_lock_wait.py)
serta seluruh **48 tes yang sudah lulus** sesuai [matriks runtime](../report/controller-evidence/20261118T172344Z-0020-r5-correction/runtime.md).
Untuk finding source, tambahkan bukti sandbox pada regresi terarah. Gunakan
PostgreSQL nyata dengan runtime non-superuser/NOBYPASSRLS, migrator
terpisah, FORCE RLS, blocker/waiter terukur dan state/effect durable.
Tambahkan tes regresi yang relevan ke suite CI dan pertahankan assertion
lama. Laporkan failing-before dan passing-after, schema check, suite penuh,
dokumen serta input/hasil per J20-A01–A09. Source-only dan NOT_RUN dilabeli
sesuai bukti. Jaga I/O di luar transaksi, kompatibilitas PA-001/PA-006 dan
aturan HTTP/RLS. Task0030 menunggu acceptance ID0020. Production Beta **NOT_READY**.

## Histori koreksi controller atas penyerahan R4 — 18 November 2026

Review exact source `77a4a9056c1c5cf9b0b0874b0630a16dd350aa09` selesai dengan **changes_requested**.
[Laporan](../report/controller/20261118T050714Z-0020-r4-correction-review.md) dan
[bukti runtime](../report/controller-evidence/20261118T050714Z-0020-r4-correction/runtime.md)
mencatat 28/28 probe R1–R4 PASS, 596 passed/1 skip, dua assertion
tambahan expired no-effect FAIL, serta temuan source pada guard
authority/lease dan recovery. Pertahankan closure not-applied dengan
writer hidup, revoke WG/SSTP saat tunggu kredensial, final no-effect
dengan lease valid, dan seluruh hasil R1–R3.

| Finding | Koreksi minimum dan bukti penutup |
|---|---|
| **REV-1711-04 P1 PARTIAL** | Hold mutasi konflik sampai writer pada attempt yang sama aman dan readback lengkap. Buktikan nol kirim penerus saat writer hidup walau readback positif, verify-only tanpa resend ketika aman, progres router lain, serta penolakan readback/resolve dari epoch lama. Identitas atau visibility yang belum pasti tetap tertahan. |
| **REV-1711-05 P1 PARTIAL** | Serialisasikan status akun aktif dan membership yang relevan hingga commit. Buktikan akun yang sudah nonaktif sebelum batas commit memberi Router 0, kredensial pending, enrollment belum completed dan job tidak sukses. Kontrol WG/SSTP yang sah commit sekali. |
| **REV-1711-01 P1 PARTIAL** | Validasi token, epoch, state dan expiry setelah lock yang bisa menunggu dengan urutan konsisten. Buktikan lock wait yang melampaui lease tanpa renewal efektif tidak commit efek DB. Pertahankan perlindungan authority dan I/O di luar transaksi. |
| **REV-1811-02 P2 PARTIAL** | Wajibkan lease valid pada awal no-effect settlement dan fence seluruh perubahan pada attempt yang sama. Kedua [tes expired no-effect](../report/controller-evidence/20261118T050714Z-0020-r4-correction/test_terminal_lease_review.py) harus lulus. Buktikan perubahan ownership antar-step tidak tertimpa bila step tetap terpisah, final valid failed sekali dan nonfinal valid backoff. |

Ambil baseline dari ref keputusan di atas. Jalankan ulang 28 kasus
probe beku sesuai laporan, tes regresi baru, pengujian penutup dan suite
backend penuh pada PostgreSQL nyata, ditambah checks pada §Verifikasi.
Laporkan per-assertion expected/actual, state dan efek, command/exit,
exact implementation/tested dan published SHA serta kandidat CI.
Task0010 tetap accepted/integrated. Task0030 menunggu acceptance 0020.
Production Beta **NOT_READY**.

## Histori penyerahan koreksi R5, 18 November 2026

**done / pending review.** Executor menutup empat residual changes_requested
controller pada ID0020 yang sama di atas decision head `2d5b7f1`
(branch `review/0020-r4-correction-20261118-0507`, PR #37; main saat mulai
`5c45276`), branch kerja `session/2026-11-18-0020-r5-correction`:

- **REV-1811-02** — settlement no-effect (final/nonfinal) kini SATU transaksi
  pendek: step-1 wajib lease masih berlaku (row tetap EXECUTING dengan
  token/epoch awal sampai reconciler — regresi controller terminal-lease
  2/2 kini PASS), step-2 terikat epoch attempt, `on_retry` di luar unit,
  penyelesaian ganda ditolak.
- **REV-1711-04** — readback **applied=True** kini wajib bukti penulis
  berhenti (in-flight + receipt/liveness /proc): readback positif saat writer
  lintas-proses hidup DITOLAK, nol kirim penerus router sama, router lain
  maju, verify-only tanpa resend hanya setelah penulis terbukti berhenti;
  seluruh CAS resolve terikat epoch snapshot (penolakan `stale_epoch`);
  identitas writer tidak lengkap (`start_ticks` NULL) → karantina fail-closed
  meski /proc hilang.
- **REV-1711-05** — guard authority terkunci mengunci baris **USER** lebih
  dulu (urutan user→membership) dan memvalidasi `is_active` segar DI BAWAH
  kunci sampai commit: penonaktifan akun selama tunggu lock kredensial
  ATAU membership → unit batal (Router 0, kredensial PENDING, enrollment
  belum completed, job FAILED authority_denied); penonaktifan berkompetisi
  terbukti ter-serialisasi lock user (BASE membiarkannya lolos).
- **REV-1711-01** — urutan guard batas commit `finalize_verification`
  dibalik: `final_authority_guard` (kunci user+membership, dapat menunggu)
  SEBELUM `commit_guard` (kunci baris job + validasi token/epoch/state/expiry)
  TERAKHIR — lease kedaluwarsa selama tunggu (tanpa renewal efektif; watchdog
  tidak terhalang lock job lagi) → NOL efek domain commit; kontrol lease
  valid commit tepat sekali.

Bukti: **28/28 probe beku R1–R4 PASS tanpa pelemahan** + regresi controller
`test_terminal_lease_review.py` **2/2 PASS** + **18 regresi R5 baru PASS**
(failing-before pada BASE `2d5b7f1`: 2+11 FAIL identik temuan controller) +
suite penuh **614 passed/1 skip/3 warnings** + check/makemigrations/docs PASS,
semua pada PostgreSQL 17.12 split-role migrator-owned, `mtx_app`
NOSUPERUSER/NOBYPASSRLS, FORCE RLS. Tanpa migration baru. [Laporan R5
eksekusi](../report/orchestrator/20261118T115321Z-0020-r5-correction.md)
memuat temuan→perubahan→bukti + matriks A01–A09 + batas;
[evidence](../report/executor-evidence/20261118T113641Z-0020-r5-correction/).
Next actor: **controller_reviewer** mereview exact implementation/tested SHA.

## Histori penyerahan koreksi R4, 18 November 2026

**done / pending review.** Executor menutup REV-1711-04 (bukti penulis
lintas proses: identitas writer dipersist ATOMIK saat EXECUTING + receipt
finally + liveness /proc starttime; unknown fail-closed ditahan), REV-1711-05
(kewenangan dibaca segar TERKUNCI pada batas commit unit setelah seluruh
tulisan sensitif termasuk tunggu lock kredensial; revoke saat tunggu →
rollback unit penuh) dan REV-1811-02 (CAS terminal final no-effect koheren
dengan lease yang dilepas step-1) pada ID0020 yang sama di atas decision
head `e0d306a`. Probe controller R4 **FROZEN 4/4 PASS tanpa pelemahan**
(failing-before executor identik temuan controller 4 gagal), frozen
R1/R2/R3 **24/24 PASS**, suite penuh **596 passed/1 skip/3 warnings**
(588 baseline controller + 8 regresi R4 baru), check/makemigrations/docs
PASS. [Laporan R4 eksekusi](../report/orchestrator/20261118T035535Z-0020-r4-correction.md)
berisi temuan→perubahan→bukti + matriks A01–A09 + batas;
[evidence](../report/executor-evidence/20261118T035535Z-0020-r4-correction/).
Next actor: **controller_reviewer** mereview exact SHA `77a4a90`.

**Riwayat instruksi R4 (changes_requested, kini ditindaklanjuti):**

**ready / changes_requested**, koreksi R4 sebelumnya **not_submitted**. Root mereview
actual integrated main **a636166**, source identik implementation/tested
**16db545**. Merge PR34/CI hijau bukan acceptance. **588 passed/1 skip/3
warnings + seluruh24 frozen R1/R2/R3 PASS**, tetapi **4 assertion baru FAIL,
0 harness errors final runs**. Satu baseline control4b03efe PASS membuktikan
regresi no-effect baru. [Controller R4](../report/controller/20261118T025143Z-0020-r4-review.md)
§§3/7 dan [evidence](../report/controller-evidence/20261118T025143Z-0020-r4/)
memiliki actual/expected, command/exit, batas dan minimum correction.

| Finding aktif | Koreksi minimum / measurable closure |
|---|---|
| **REV-1711-04 P1 PARTIAL** (executor residual REV-R3C-01) | Registry proses sendiri + advisory lock bebas tidak membuktikan writer lintas-proses berhenti. Actual OS child masih hidup setelah sesi PG mati; same-job resolve(False) membuka send kedua/succeeded. Unknown writer tetap hold; butuh bukti termination/completion attempt yang berlaku + readback sebelum requeue. Probe cross-process wajib nol successor sends, lalu positive recovery setelah writer terbukti berhenti. Scope helper/additive migration yang memang perlu sudah diizinkan; jangan menurunkan acceptance karena belum ada caller ops/API. |
| **REV-1711-05 P1 PARTIAL** | Enrollment-lock guard kini lulus, tetapi credential UPDATE menunggu lock sesudah guard: revoke committed masih menghasilkan Router1/APPLIED/completed/succeeded pada WG/SSTP. Fresh current authority wajib valid pada akhir sensitive effect unit, sesudah blocking operations dan konsisten melalui commit; preserve ownership fencing/I/O di luar transaksi. Kedua credential-wait probes wajib Router0, credential pending, no success; seluruh schedule lama tetap PASS. |
| **REV-1811-02 P2 OPEN** (regresi konkret terkait REV-R3C-02) | `_retry_no_effect` menghapus expiry/token lalu final-attempt memanggil CAS yang kini mensyaratkan expiry>now; hasil tersangkut uncertain. Same assertion sebelumnya4b03efe FAILED terminal sah; current uncertain. Perbaiki recovery transition yang ter-fence tanpa melemahkan general valid-lease guard. Final no-effect→FAILED, nonfinal backoff tetap benar, stale/unknown/competing attempts tetap aman; masukkan tes CI. |

**Retain CLOSED:** REV-1711-01 expiry-resurrection schedules/healthy renewal,
REV-1811-01 duplicate typed failure, REV02/03/06/07/08, REV09 pada batas
process/sandbox terdokumentasi. PA001/PA006/task0010 tetap accepted/integrated.
Jangan ulang perbaikan yang terbukti. A01–A09 di bawah **tidak diubah**;
A03/A04/A06 FAIL, A01/A05 PARTIAL dan A09 gagal regresi baru menurut matriks R4.

Jalankan [2 lifecycle assertions](../report/controller-evidence/20261118T025143Z-0020-r4/test_r4_lifecycle_edges.py)
dan [2 WG/SSTP authority assertions](../report/controller-evidence/20261118T025143Z-0020-r4/test_r4_authority_credentials.py),
serta **seluruh24 probe beku** R1/R2/R3 tanpa melemahkan assertion; positive
safe recovery setelah writer benar-benar berhenti tetap harus lolos.
Tes yang mengharapkan recovery sesudah writer joined bukan konflik normatif
dengan penolakan saat writer proses lain masih hidup. Pilih minimum compliant
fix; jangan menambah service/framework/task baru. Laporan harus memisahkan
runtime root, executor dan source-review; seluruh A01–A09 dinilai ulang.

Next **coding_agent**, same ID0020. Task0030/deploy/aktivasi tetap ineligible.
Satu skip radius karena binary tidak tersedia di controller; bukan FAIL
produk atau bukti RADIUS deployment. NOT_RUN host/lab/systemd/E2E/scale tetap.

## Histori koreksi controller R3 — digantikan verdict R4 di atas


**done / pending review.** Executor menutup REV-1711-01/04/05 +
REV-1811-01 pada ID0020 yang sama di atas decision head05d268d
(main4b03efe + records R3). Probe controller R3 **FROZEN 7/7 PASS tanpa
pelemahan** (failing-before executor di wt-base identik temuan controller:
3+3 gagal/1 positif), frozen R1/R2 **17/17 PASS**, suite penuh **589 passed/
0 skipped** (583 baseline + 1 radius unskip sandbox + 5 tes baru
`test_jobs_r3_residuals.py`), check/makemigrations/docs PASS.
[Laporan R3 eksekusi](../report/orchestrator/20261118T022200Z-0020-r3-correction.md)
berisi temuan→perubahan→bukti + matriks A01–A09 + batas;
[evidence](../report/executor-evidence/20261118T000000Z-0020-r3-correction/).
Reviewer independen: 01/05/1811-01 CLOSED; REV-1711-04 PARTIAL pada lingkup
probe (residual lintas-proses REV-R3C-01 P2 laten terdokumentasi — tidak
dapat ditutup otomatis tanpa berkonflik dengan closure R1; next step konkret
tercatat). Next actor: **controller_reviewer** mereview exact SHA.

| Finding | Koreksi minimum / acceptance penutup |
|---|---|
| **REV-1711-01 P1 PARTIAL** | Seluruh worker renewal/transition/domain/terminal boundary wajib token+epoch+expected active state+valid lease, tanpa menunggu reconciler. Watchdog sudah menolak expiry tetapi ctx.progress dan returning-I/O heartbeat masih revive lalu succeeded. Dua probe R3 harus nol new-send/verify/success; preserve locked commit/healthy renewal. |
| **REV-1711-04 P1 PARTIAL** | resolve_uncertain(applied=False) setelah sesi DB mati tidak boleh menganggap advisory lock bebas sebagai old-writer-safe proof. Reclaim job ID sama kini mengirim kedua saat old adapter hidup. Hold sampai writer benar-benar aman + readback applicable; unknown tetap tertahan, router lain maju. |
| **REV-1711-05 P1 PARTIAL** | Enrollment WG/SSTP: acquire potentially blocking enrollment lock sebelum fresh authority check di sensitive write boundary. Probe pg_blocking_pids membuktikan revoke committed selama worker menunggu; saat ini tetap Router1/credentials applied. Closure nol Router/activation pasca-revoke. |
| **REV-1811-01 P2 OPEN** | Duplicate finalize references undefined JobError → internal_error/uncertain. Gunakan typed nonretryable enrollment_state atau safe verified replay, exactly1 Router dan dua worker outcomes lengkap. |

**CLOSED tetap: REV-1711-02/03/06/07; REV08 kini CLOSED** (active B6 adapter,
lab gate/negative readback jujur). **REV09 evidence mapping/healthy long phase
CLOSED within sandbox/process limits**: tambahan root satu I/O melewati expiry
awal,25 reconciler attempts PASS; expiry resurrection tetap defect REV01.
Preserve atomic domain commit fix, different-job hold/session-loss fix,
post-TLS authority check, B5/B6 checks, PA001/PA006/SSTP, seluruh17 probe lama.

**Jalankan semua7 probe R3**, bukan hanya6 yang gagal: file
[life4](../report/controller-evidence/20261117T212042Z-0020-r3/test_r3_lifecycle_edges.py)
dan [authority3](../report/controller-evidence/20261117T212042Z-0020-r3/test_r3_authority.py).
FROZEN assertions tidak dilemahkan; gate bersifat observation/control timing,
bukan substitusi product decisions. Seluruh A01–A09 di bawah tetap berlaku.
Koreksi R3 **not_submitted**. Task0010 accepted/integrated; task0030/deploy/
aktivasi belum eligible. Application fixes tetap responsibility executor.

## Histori koreksi controller R2 — hasil dinilai ulang oleh R3

**R2 changes_requested pada actual integrated main64b68f8.** Koreksi PR30
sudah merged; merge bukan acceptance. Full backend **580 passed/1skip/3warnings**
dan **11 original R1 probes passed**, tetapi **6 assertion R2 gagal/0 errors**.
[Laporan R2](../report/controller/20261117T170000Z-0020-r2-review.md) memiliki
reproduksi, expected/actual, source lines dan closure lengkap; [evidence](../report/controller-evidence/20261117T170000Z-0020-r2/).

| Finding tetap | Koreksi minimum / penutup |
|---|---|
| **REV-1711-01 P1 PARTIAL** | Guard SELECT di transaksi tidak mengunci ownership sampai commit. Actual discovery guard→reconcile→resume commit object1/snapshot succeeded. Serialize ownership-changing updates vs short domain commit; valid expected state/token/epoch/lease; seluruh service units juga aman. Preserve I/O di luar transaksi. |
| **REV-1711-04 P1 PARTIAL** | Cek durable unknown harus konsisten dengan sender acquisition; predecessor menjadi uncertain setelah SELECT masih menghasilkan send2. Selain itu putusnya DB session melepas advisory lock sementara adapter worker masih hidup: successor send2 saat lease predecessor masih valid. Tahan sampai old adapter writer aman **dan** readback selesai; jangan hanya memindah SELECT lalu mengklaim seluruh closure. Router lain tetap maju. |
| **REV-1711-05 P1 PARTIAL** | Post-I/O enrollment harus cek current authority pada effect unit; revoke saat TLS probe saat ini tetap membuat Router1 dan apply peer/akun pada WG **dan** SSTP. Nol efek baru sesudah revoke, dengan helpers/stack existing. |
| **REV-1711-08 P1 PARTIAL** | B6 wajib memakai adapter aktif existing; selected api_ssl saat ini dibypass simulator sehingga false succeeded/rolled_back/local. Hormati cutover_pending_lab tanpa mengaktifkan live mutasi baru; negative/unknown tetap jujur, positive simulator berlabel. |
| **REV-1711-09 P2 PARTIAL evidence** | Preserve SIGTERM/SIGINT/active-progress/stop-claim dan SUB-05 yang sudah terbukti. Map renewal fase panjang existing terhadap concurrent reconciler secara tepat; short progress loop bukan satu long adapter call. Simulasi thread expiry setelah domain commit bukan actual process kill. Lengkapi applicable evidence/justifikasi, tanpa menambah fitur fase depan. |

**CLOSED dan harus dipertahankan: REV02/03/06/07**, original preflight
revocation fix, seluruh11 probe R1, PA001/PA006 dan SSTP yang sudah
terintegrasi. Jangan ulang perbaikan yang sudah terbukti atau buka task0010.
Original A01–A09 di bawah **tidak berubah**. Uji enam assertion baru dari
file lifecycle (3) dan authority (3), jangan melemahkan assertion; root
mencatat first2 lifecycle dan third sender-session pada log terpisah.
Kandidat koreksi R2 belum diserahkan; tetap filename unfinished. Baseline
current64b68f8 harus dipertahankan, bukan checkout source PR27/41d1f33 lama.
Task0030/deploy/aktivasi belum eligible. Decision branch R2 harus difetch
bila PR dokumentasi belum merged.

## Histori koreksi controller R1 — hasilnya dinilai ulang oleh R2

Verdict pada **PR27@bd37c14** adalah `changes_requested`: **8 defect kode
terkonfirmasi melalui 11 assertion PostgreSQL gagal**, bukan 11 error harness.
Root full suite554 passed/1skip/3warning tetap tidak memenuhi acceptance yang
probe ini buktikan gagal. [Matriks evidence dan koreksi lengkap](../report/controller/20261117T134100Z-0020-job-lifecycle-review.md)
menjadi instruksi koreksi; A01–A09 di bawah tidak dikurangi. Current source
PR27 dibawa oleh decision ref; main41d1f33 belum memuat packet/kandidat ini.

| ID | Koreksi minimum / tes penutup |
|---|---|
| **REV-1711-01 P1** | Guard lease/token/epoch/state/validity **dalam transaksi domain**; actual blocked discovery→reconcile→resume tidak commit object/health/success atau efek berikutnya; failed checkpoint menghentikan worker |
| **REV-1711-02 P1** | Generic/staging failure sesudah backup send ditahan uncertain/recovery; nol resend otomatis/manual tanpa bukti no-effect/readback |
| **REV-1711-03 P1** | Retry lineage serialized: ancestor retry tidak melewati descendant uncertain/recovery/active; concurrent ancestor/child menghasilkan nol efek duplikat |
| **REV-1711-04 P1** | Mutasi router berkonflik ditahan durable sampai old-writer aman **dan** readback unknown predecessor selesai; router lain tetap maju |
| **REV-1711-05 P1** | Current authority di effect boundary setelah preflight/per-chunk; revoke/demote/narrow-scope barrier→nol release/peer/NAS/send |
| **REV-1711-06 P1** | HTTP detail/retry/cancel menghormati membership router scope; non-scope404+state/job tidak berubah, in-scope403/step-up tetap benar |
| **REV-1711-07 P2** | B6 APPLY/VERIFY keluar dari outer DB transaction; independent observer membuktikan no transaction/row-lock saat adapter diblokir |
| **REV-1711-08 P1** | B6 negative/unknown readback tidak mengklaim succeeded/rolled_back/local; positive dan pending_observation tetap jujur |
| **REV-1711-09 P2 evidence gap** | Buktikan SIGTERM+SIGINT idle/active-DB/blocked-I/O dengan barrier+efek durable+complete outcomes, long-phase/heartbeat/recovery dan current-policy/SUB05 assertions yang applicable; jangan membangun fitur R2 untuk tes |

Reproduksi final disimpan di [controller-evidence](../report/controller-evidence/20261117T134100Z-0020-review/).
Tutup finding dengan perubahan minimum dan passing-after assertion yang sama
atau lebih kuat; jangan mengubah requirement atau melemahkan probe untuk lulus.
PA-006/task0010 tetap accepted/integrated, P3 thread assertions dipertahankan.
Tidak ada task0030/deploy/merge/aktivasi otomatis. Ringkasan internal reviewer
lama ditandai histori; controller R1 adalah keputusan acceptance current.

## Tujuan dan batas

Perbaiki jalur job **yang sudah terdaftar saat ini** agar pemilik lama tidak bisa menimpa hasil/mengirim efek setelah kehilangan kewenangan, pembatalan/retry tidak menyembunyikan efek tak pasti, dan worker dapat drain dengan hasil durable. Reuse modular monolith dan PostgreSQL jobs/outbox existing. Jangan membangun handler fase depan, queue/broker, orchestration service, generic DSL atau framework authorization baru.

Sebelum edit, tulis inventory ringkas di laporan: setiap active kind dan enqueue origin, permission/membership/router scope, actor atau trusted-system provenance, policy/revision, effect boundary DB/send/file, verifier, deadline/heartbeat, retry/recovery. Cakup customers, network, radius dan backup handler existing. Identifikasi DB-only vs external effects; jangan menganggap semua execute sama. Default `actor=None` bukan izin system. Jalur `verify_api_ssl` dari enrollment kini actorless; telusuri enrollment/created_by/ownership dan tetapkan compatibility yang aman.

Baca [temuan source independen](../report/reviewer/20261116T231008Z-0020-job-safety-independent.md) dan [prasyarat/batas finance](../report/reviewer/20261116T231048Z-0020-prerequisite-independent.md). Root report memberi ID finding final. Source review belum merupakan reproduksi runtime; executor wajib failing-before/passing-after pada defect yang diperbaiki.

## Scope perubahan

Boleh diubah hanya sejauh diperlukan:

- `backend/domains/jobs/{engine.py,models.py,views.py}`, command `runworker.py`, helper lokal jobs kecil bila konkret, serta migration jobs **baru additive** bila bukti mengharuskan.
- Existing handlers `customers/handlers.py`, `network/handlers.py`, `radius/handlers.py`, `backups/service.py`; enqueue/view/service domain yang sudah ada untuk trusted provenance/current authority/revision dan pemisahan DB/I/O yang relevan.
- Existing shared identity/tenancy/common helper seperlunya, tanpa melemahkan HTTP/session/CSRF/RLS. Shared helper ownership tetap terserialisasi oleh orchestrator.
- Focused unit/integration/process tests dan fixture yang sah; `backend/tests/integration/test_idempotency_pa006_r5.py` hanya hardening P3 REV-1611-TEST-01 (assert kedua thread selesai dan kedua hasil ada).
- Packet ini, laporan/evidence tersanitasi, latest handoff/progress dan catatan operasi non-normatif di laporan; bila perlu runbook singkat gunakan `docs/runbooks/`.

Tidak mengubah CONTRACT/domain requirements/defaults/test-design agar kode lulus; tidak mengadopsi PR8, mengubah dependency stack/CI/installer/topology, mengaktifkan kemampuan mutasi RouterOS yang lab-required, merombak backup/PDF/storage, Tax/DANA/SSTP atau scheduler. Jangan edit migration applied PA-0060004/0005, replay/hash/cache protocol, atau history uang. Jika perubahan normative sungguh perlu, laporkan PROPOSED sesuai CONTRACT dan tahan hanya keputusan terdampak.

## Acceptance wajib

| ID | Hasil yang harus dibuktikan |
|---|---|
| **J20-A01 — ownership seluruh write** | Transition, terminal/error/result/detail, retry, heartbeat, progress dan domain commit yang terkait memiliki guard current lease token+epoch+expected state/validity yang benar. CAS gagal menghentikan worker lama. Force lease transfer/reconcile/cancel lalu jalankan stale snapshot: nol overwrite state/result/progress, nol efek DB/send baru. Terminal state tetap immutable. Jangan hanya menambahkan helper yang return-nya diabaikan. |
| **J20-A02 — transaksi dan RLS** | Claim/transisi/checkpoint serta DB domain/audit/outbox memakai transaksi pendek dengan konteks tenant tepercaya pada koneksi yang sama. Tidak ada transaksi/row lock DB terbuka melintasi network I/O. Block adapter secara terkendali; koneksi observer membuktikan committed state+heartbeat terlihat dan tidak ada lock/transaksi worker tertahan saat send/readback. Tenant context setelah commit/rollback/pool reuse fail-closed. Payment/PA-001 atomic locks tetap utuh; pekerjaan network tidak menahan lock dana yang tak diperlukan. |
| **J20-A03 — writer eksternal dan cancel** | Satu pemilik mutasi konflik per router; dua worker/job router sama tidak mengirim bersamaan, router lain tetap dapat maju. Lease/epoch DB **tidak** dianggap menarik kembali command RouterOS. Pemilik baru menunggu bukti penulis/koneksi lama tidak dapat mengirim dan readback selesai. Queued/pre-effect cancel atomik menghasilkan nol efek berikutnya; outstanding send/maybe/confirmed tidak diberi false cancelled. Race cancel/execute/reconcile diperiksa dari efek dan state durable. |
| **J20-A04 — uncertain dan retry** | Timeout setelah send/ack hilang/generic error setelah possible effect menjadi uncertain/recovery sesuai bukti, tidak blind retry. API retry, retry_job, resolve_uncertain dan automatic retry tidak membuka efek baru dari unknown outcome. Readback applied→verify tanpa resend; not-applied→retry hanya setelah old writer aman; unknown tetap tertahan. Concurrent retry tidak menghasilkan duplicate logical effect; origin/action identity dan audit tetap traceable. |
| **J20-A05 — crash/reconcile/deadline** | Crash claimed/preflight/executing/verifying dan sebelum/sesudah DB effect commit mempunyai recovery durable yang benar; expired lease compare-and-set tidak menimpa lease renewed/completed/cancelled. Recovery diulang aman. Deadline/attempt/backoff/heartbeat memakai defaults existing dan boundary effect yang eksplisit; expired sebelum efek tidak mengirim, expired setelah possible effect jujur uncertain. B3/B4 observation window durable tidak dipercepat atau diberi batas60s yang salah. |
| **J20-A06 — current authority** | Actor aktif, membership/permission, tenant/resource/router scope dan policy/revision yang relevan diperiksa dari DB mutakhir sebelum setiap efek/chunk sensitif, bukan objek/payload enqueue yang basi. Revoke/demote/delete/scope change setelah enqueue atau sesudah preflight menghasilkan nol efek yang kini dilarang. Sensitive proof/reauth/revocation mengikuti kontrak existing; jangan menyimpan cookie/token/secret sesi di payload. Menutup browser tidak membatalkan pekerjaan async biasa yang tetap sah. Trusted-system origin sempit, server-derived dan dapat diaudit; null/deleted actor tidak otomatis system. Platform-only actor bukan pemilik tenant. Preserve SUB-05: restricted bukan mematikan operasi layanan existing; ended tidak mengisolir internet karena utang SaaS. Policy/hold/pembayaran diuji pada jalur aktif; jangan membangun auto-isolir R2 untuk tes ini. |
| **J20-A07 — HTTP authority dan verifier** | Direct HTTP detail/retry/cancel memakai underlying operation/read permission dan router scope yang benar; sensitive mutation memerlukan step-up yang berlaku. Non-milik404 generik, milik tanpa izin403. Router replacement tidak melepas router dengan izin enroll saja; trace ARCHITECTURE§5 routers.release. Missing handler/payload authority fail-closed. Verifier negatif tidak menghasilkan succeeded; verifier kontrak eksplisit pada semua active kind, preserve hasil valid DB-only dan cutover pending_observation tanpa klaim perangkat selesai. |
| **J20-A08 — drain proses** | Uji **proses nyata disposable** SIGTERM dan SIGINT pada idle, cooperative DB job dan blocked I/O: stop claim baru segera, batas waktu drain jelas, active job diselesaikan/ditahan jujur, exit/status membedakan drained vs deadline/incomplete. Paksa process kill lalu reconcile membuktikan recoverability. Deadline habis tidak mengklaim sender telah aman bila belum dibuktikan. Runbook menyebut urutan stop-claims→drain/stop old writers→reconcile/readback→resume. Ini belum rehearsal installer/systemd/produksi. |
| **J20-A09 — compatibility dan regresi** | Inventory old queued/in-progress/actorless payload serta authority baru: proven valid diproses tanpa privilege escalation; unknown/quarantined memiliki alasan dan resume yang tepat, tidak sekadar dipurge. Additive migration dan kode lama/baru memiliki kebijakan drain/compatibility/fix-forward yang teruji, tanpa klaim rollback aman ke worker lama yang defective. Preserve PA-001 seluruh10 kasus, PA-006 termasuk grammar/migration/permission/selected IDs/secret scrub. Tutup P3 REV-1611-TEST-01 sebagai test-only: missing participant harus FAIL; tidak membuka task0010 lagi. |

## Verifikasi dan bukti

1. Reproduksi minimum failing-before untuk jalur unfenced write, cancel-in-flight, uncertain retry, revoked authority dan missing/negative verifier; lalu passing-after yang sama. Harness mengamati state durable dan efek, bukan sekadar mock-call/status.
2. PostgreSQL nyata, runtime NOSUPERUSER/NOBYPASSRLS dan FORCE RLS; jika mengklaim paritas produksi gunakan migrator owner terpisah. Independent connections/processes untuk race; Events/barriers serta query/blocker observer saat mengklaim lock contention. Jangan memakai sleep sebagai satu-satunya pengatur. Semua thread/process wajib bounded join, sudah berhenti dan setiap hasil terisi; exceptions worker ikut menggagalkan tes.
3. Jalankan targeted jobs/authority/recovery/drain tests, RLS/pool reuse, PA-001 dan PA-006 regressions. Jalankan suite backend penuh, `manage.py check`, `manage.py makemigrations --check --dry-run`, migration/compatibility checks yang terpengaruh dan `python3 docs/tools/check_docs.py`. Jangan refresh manifest yang tidak berubah.
4. Jalankan checks API/schema/contracts dan frontend/typecheck/build sesuai dampak; full candidate CI backend/frontend/docs harus exact published SHA (atau synthetic PR merge SHA dengan ancestry/source delta eksplisit). Browser E2E/perangkat/OS/DR/benchmark tetap NOT_RUN kecuali benar-benar dijalankan.
5. Setiap assertion matriks A01–A09 dilaporkan PASS/FAIL/NOT_RUN/BLOCKED dengan command, environment/version, exit, expected/actual, state/effect count, log path dan tested SHA. Simulator/controlled adapter membuktikan engine sandbox saja; CHR fencing, lab dan zero downtime tidak dinyatakan terbukti.

Host/lab unavailable tidak menghalangi pengembangan sandbox ini. Bila mandatory sandbox test belum dapat dijalankan, status blocked/failed sesuai sebab dan filename tetap unfinished; jangan menandai done dengan daftar tes yang belum dijalankan.

## Penyerahan

Orchestrator memakai reviewer independen sesuai CONTRACT§5 untuk concurrency/recovery dan authority/compatibility; read-only boleh paralel, writes disjoint hanya jika isolation terverifikasi. Laporan utama `report/orchestrator/<UTC>-0020-job-lifecycle-authority_done.md`; setiap reviewer `report/<role>/<UTC>-0020-*.md`; evidence tersanitasi sesuai CONTRACT§10.

Laporan memuat inventory, minimum solution/alternatives, finding→change→failing-before/passing-after, **seluruh A01–A09→actual evidence**, migration/legacy/recovery, batas source vs PG vs process vs device, exact instruction/base/implementation/tested/published SHA, PR+CI, risiko dan next actor/action. Tidak cukup melaporkan jumlah tes.

Setelah scope/tes wajib tuntas: update packet/report/handoff/progress, rename **file ini** ke `0020-job-lifecycle-authority_done.md` pada commit penyerahan, push branch dan verifikasi remote+CI; review menjadi pending. Bila controller meminta koreksi, buka kembali ID0020 yang sama dan preserve laporan. `_done` bukan acceptance, merge, deploy atau release. Next actor controller mereview exact SHA hasil; task dependent baru menunggu keputusan/integrasi yang disyaratkan.

Production Beta tetap **NOT_READY**: installer/upgrade/restore/secret separation/scheduler/topology DEC-01/DEC-02 dan gates host/GNS3/pilot/kapasitas berada di scope terpisah. Penyerahan packet ini tidak otomatis menjalankan external coding agent.
