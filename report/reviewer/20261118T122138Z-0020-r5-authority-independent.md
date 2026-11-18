# Review independen task 0020 R5 — kewenangan dan batas commit

| Field | Nilai |
|---|---|
| Peran | Reviewer independen kewenangan dan kompatibilitas |
| Instruction/base | PR #37, `2d5b7f1be4dbe2ed49203b8a7a97545125500c94` |
| Implementasi diperiksa | `3301c2940dbfa9293ae52b8d8479b2050c16ebef` |
| Penyerahan | PR #38, `ccea781458b4b90a40f97f5b07139965b4a85963` |
| Main saat penetapan scope | `0616a8063f6f40b370495aa7cfe8ae1d4db656dc` |
| Dasar penerimaan | Packet 0020 J20-A01/A05/A06/A08/A09, keputusan R4-correction §2–3, PRODUCT TEN-03/JOB-02–05/SUB-05 |

## Putusan pada scope reviewer

**Koreksi enrollment WG/SSTP yang diminta pada REV-1711-05 dan REV-1711-01 memenuhi jadwal R4.** J20-A06 secara keseluruhan masih **PARTIAL** karena unit efek release/replace yang aktif belum mempertahankan kewenangan hingga commit. Ini temuan source pada kandidat R5 dan sudah ada di baseline. Pemeriksaan runtime independen kandidat dan setiap keputusan acceptance berada pada controller.

| Butir | Bukti dan batas |
|---|---|
| REV-1711-05 pada enrollment | `network/handlers.py:88–96` memasang pemeriksaan final terkunci. `jobs/engine.py:706–750` mengunci baris user, membaca `is_active` segar, lalu mengunci baris membership tenant dan menilai izin dari peran saat ini. `network/services.py:1285–1400` meletakkan guard setelah lock enrollment, insert router dan update kredensial WG/SSTP di transaksi yang sama. Akun yang telah dinonaktifkan atau membership yang sudah dicabut sebelum batas final membatalkan unit. Perubahan identitas yang datang ketika lock user sudah dipegang terurut sesudah unit commit. Fallback actorless tetap mencari pembuat enrollment yang ada di scope tenant (`jobs/engine.py:640–653`); aktor hilang gagal tertutup pada kind produksi. |
| REV-1711-01 pada enrollment | Guard authority berjalan sebelum guard lease pada `network/services.py:1378–1400`. `JobContext.guard_commit` memperoleh lock baris job dahulu lalu membandingkan token, epoch, state dan expiry dengan waktu segar (`jobs/engine.py:371–401`). Lock user/membership tetap dipegang sampai unit commit. Probe konektivitas berada sebelum transaksi efek (`network/services.py:1227–1242,1285–1286`). Review jalur fence lain, khususnya UPDATE yang mengikat waktu sebelum menunggu row lock, berada pada review lease/controller. |
| Bukti enrollment yang tersedia | R5 `test_jobs_r5_residuals.py:448–614` mengamati UPDATE kredensial WG/SSTP yang benar-benar menunggu dan memeriksa Router 0, kredensial pending, enrollment belum completed dan job gagal atau tetap untuk reconciler. Kontrol sah memeriksa Router 1, kredensial applied dan job succeeded. Pada `:616–790`, observer mengidentifikasi wait membership dan memeriksa hasil deactivation/expiry; detail batas bukti di bawah. Log executor mencatat 18/18 regresi R5 lulus dan 2/2 probe beku R4 authority lulus dengan hasil efek eksplisit. Controller memberi kabar bahwa seluruh 48 kasus yang diserahkan lulus saat dijalankan ulang. |
| A06 SUB-05 dan provenance | Baseline yang dipertahankan mencakup tenant/platform out-of-scope, aktor nonaktif, actorless legacy dan resume dengan provenance (`backend/tests/integration/test_jobs_lifecycle_pa002.py:702–850`). Tes SUB-05 pada `:1314–1352` membuktikan discovery tetap boleh untuk restricted/ended, state subscription tetap dan nol akun isolasi pada fixture. Bukti itu terbatas pada jalur aktif discovery tersebut. |
| A08 | Perubahan R5 tidak menyentuh command worker atau tes drain. `test_jobs_drain_pa002.py:139–291` memuat SIGTERM/SIGINT idle, cooperative DB job, blocked I/O, deadline dan SIGKILL→reconcile pada proses disposable. Tidak ada rerun proses oleh reviewer ini. |
| A09 | Delta kode R5 terdiri dari engine, service network dan satu file tes. Tidak ada migrasi R5 baru. `jobs.0006_writer_attempt_receipt` dan hardening thread PA-006 (`test_idempotency_pa006_r5.py:421–425`) tetap. Evidence executor melaporkan suite 614 passed, 1 skip, 3 warnings. Ini tidak memverifikasi mixed-version live upgrade atau rollback worker lama. |

## REV-1711-05 — P1 PARTIAL pada release dan replace yang aktif

Kedua job dapat dibuat dari jalur HTTP normal dengan izin `routers.release` (`backend/domains/network/views.py:180–223`; peta engine `backend/domains/jobs/engine.py:241–250`). Engine membaca kewenangan setelah preflight (`engine.py:899–906`), sebelum akuisisi sender, transisi state dan heartbeat yang mendahului eksekusi (`:932–1030`).

`RouterReleaseHandler.execute` menyimpan `released_at`, mengubah state WG/SSTP dan mendeproyeksikan NAS dalam satu `ctx.scope()` (`backend/domains/network/handlers.py:173–190`, `backend/domains/radius/projection.py:145–147`). `RouterReplaceHandler.execute` menyimpan `released_at`, mengubah state kredensial dan membuat enrollment pengganti dalam unit setara (`network/handlers.py:210–236`). Unit ini hanya memeriksa ownership pada entry dan di batas commit (`jobs/engine.py:403–420`). Ia tidak membaca ulang actor/membership/role/scope sebelum commit. Dengan demikian perubahan kewenangan yang sudah commit saat unit masih menunggu lock tulisan domain tidak membatalkan efek release atau replace selama lease tetap sah. Lease dan izin adalah prasyarat yang terpisah pada J20-A01/A06.

Probe beku R1 `report/controller-evidence/20261117T134100Z-0020-review/test_authority_review.py:111–166` membuktikan perubahan kewenangan yang telah commit selama preflight menghentikan release melalui pemeriksaan engine berikutnya. Probe itu tidak mencakup unit efek setelah pembacaan tersebut. Temuan ini berasal dari alur source, tanpa reproduksi runtime tersendiri.

**Koreksi minimum.** Terapkan pemeriksaan authority dari DB mutakhir pada batas commit transaksi efek release/replace. Gunakan pemeriksaan dan penguncian user/membership yang sudah ada dengan urutan konsisten. Pertahankan pemeriksaan lease pada batas terakhir dan semantik izin HTTP/tenant/scope. Pada acceptance kedua job, bila perubahan kewenangan lebih dulu commit saat unit efek masih tertahan, harapkan Router tetap aktif, state WG/SSTP dan NAS tidak berubah, nol enrollment pengganti baru dan job tidak sukses. Sertakan kontrol berizin yang membuktikan perubahan yang sah commit satu kali. Pertahankan seluruh regresi WG/SSTP yang sudah lulus.

## Catatan ketepatan bukti tes

`test_jobs_r5_residuals.py:669–693` melepas adapter sebelum memulai locker membership. Worker dapat mendahului akuisisi lock, sehingga tes bisa gagal sebelum mengukur keadaan yang dimaksud. Di `:730–755`, tes deactivation memiliki event started yang tidak dibaca dan mengandalkan batas tunggu satu detik untuk menyatakan deactivator tertahan. Cabang itu akan lebih deterministik jika locker sudah siap sebelum probe dilepas dan observer mengonfirmasi blocker user aktual. Source R5 dan probe credential-wait memberi bukti terpisah untuk koreksi enrollment. Kasus expiry dalam membership/credential-wait memakai perubahan expiry terkontrol. Kasus tersebut membuktikan pembacaan expiry baru setelah kontensi, dengan cakupan berbeda dari clock yang lewat ketika UPDATE atas baris job yang sama sudah menunggu.

## Pemeriksaan independen

`git show`, `git grep` dan `git diff 2d5b7f1..3301c29` membaca source, packet, tes dan bukti yang ditunjuk. `git diff --exit-code 3301c29..ccea781 -- backend apps infra .github` exit 0. Reviewer ini membaca log yang tersimpan dan tidak menjalankan PostgreSQL, CI, simulator, jaringan atau perangkat sendiri. Perubahan kode, rollout dan kesiapan produksi berada di luar penyerahan review ini.
