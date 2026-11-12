# MicroTix — mulai atau lanjutkan pekerjaan agent

Panduan permanen, disetujui pemilik proyek 12 November 2026. File ini tidak diberi `_done`.
Aturan wajib: [CONTRACT.md §6A](../CONTRACT.md). Status sesi aktual: [LATEST_HANDOFF](../report/LATEST_HANDOFF.md).

Pilih prompt sesuai peran sesi: [executor/coding agent](../docs/MASTER_PROMPT_EXECUTOR.md) atau [controller reviewer](../docs/MASTER_PROMPT_REVIEWER.md). Keduanya berlaku untuk semua sesi baru/resume, mengambil task/ref aktual dari GitHub dan memakai workflow yang sama di bawah. Prompt default bukan packet dan tidak diberi `_done`.

## 1. Mulai dari kondisi aktual

1. Baca instruksi workspace/AGENTS yang berlaku, CONTRACT, handoff kanonis dan checkpoint terbaru [progress](../docs/progress.md).
2. Fetch remote refs; periksa default branch, PR, CI, worktree, status/diff dan pekerjaan pihak lain. Jangan reset, force-push atau menimpa pekerjaan itu. Buat branch/worktree terisolasi dari baseline yang dinyatakan task setelah memeriksa delta terhadap main aktual.
3. Cari ID task pada file `task/`, candidate branches/PR terbuka dan report yang ditautkan. Status `ready` di main tidak membuktikan task belum dikerjakan: hasil `_done`/pending-review bisa masih di branch PR. Gunakan ref kandidat yang dipublikasikan untuk memeriksa hasil; jangan membuat implementasi duplikat.
4. Daftar packet menurut nama. Abaikan `0000-start-here.md`; pilih nomor terkecil yang belum selesai dan dependency/review prasyaratnya terpenuhi. Nomor adalah urutan baca, bukan bukti dependency selesai.
5. Baca packet itu dan hanya kebutuhan/domain yang relevan. [docs/tasks.json](../docs/tasks.json) tetap backlog produk; packet Markdown adalah instruksi eksekusi terbatas, bukan salinan seluruh roadmap.
6. Mulai/resume pekerjaan yang sama dari evidence terakhir. Task `_done` atau kandidat yang menunggu review tidak diimplementasikan ulang. Jika tidak ada task eligible, laporkan blocker/next action yang tepat; jangan mengarang task atau memperluas fitur sendiri.

Status/prioritas aktual ditemukan pada latest handoff, packet dan refs yang diverifikasi. Jangan mengunci prompt permanen pada task awal atau SHA historis. File penerus belum otomatis diotorisasi hanya karena disebut di roadmap.

## 2. Peran dan sumber keputusan

| Pemilik | Tanggung jawab |
|---|---|
| Controller / reviewer | Menulis packet di repository, mengalokasikan ID/file ownership, menetapkan acceptance dari kebutuhan existing, mereview exact SHA dan mencatat keputusan |
| Executor z.ai / Claude Code atau agent yang ditugaskan | Mengimplementasikan scope, menjalankan tes, memakai reviewer/sub-agent yang relevan sesuai CONTRACT, membuat laporan, commit/push dan menyerahkan bukti |
| Pemilik proyek | Keputusan yang mengubah kontrak normatif, scope produk atau kewenangan rollout yang memang memerlukan persetujuan menurut CONTRACT |

[PRODUCT](../docs/PRODUCT.md), [ARCHITECTURE](../docs/ARCHITECTURE.md), dokumen domain dan [ACCEPTANCE](../docs/ACCEPTANCE.md) tetap memiliki kebutuhan. Scope awal adalah perbaikan menuju Beta terbatas, bukan otomatis seluruh R1–R4. Pertahankan modular monolith, PostgreSQL dan jobs/outbox existing; jangan menambah infrastruktur/task engine untuk membaca Markdown.

## 3. Penamaan dan status

Gunakan nomor empat digit yang permanen dan slug lowercase-hyphen. Contoh:

- Belum selesai: `0010-pa006-idempotency.md`.
- Selesai oleh executor: `0010-pa006-idempotency_done.md`.
- Koreksi setelah request changes: buka kembali nama pertama dengan **ID 0010 yang sama**; simpan bukti review lama di report.

Controller mengalokasikan nomor berikutnya; jangan renumber atau membuat kedua versi unfinished/done sekaligus. Nama empat digit memungkinkan urutan alfabet stabil. Semua tautan masuk umum harus menuju panduan ini yang tidak berubah nama, bukan mengandalkan nama packet yang akan direname.

| Kolom dalam packet | Nilai/pemakaian |
|---|---|
| Execution status | `ready`, `in_progress`, `blocked`, `failed`, `done` |
| Review status | `not_submitted`, `pending`, `accepted`, `changes_requested` |
| Baseline / dependencies | SHA rencana awal dan syarat pekerjaan/review; verifikasi ulang remote saat mulai |
| Implementation / tested SHA | Commit kode yang benar-benar diuji; tidak harus commit metadata terakhir |
| Candidate / PR / reports | Remote SHA/PR, evidence per assertion, laporan session/reviewer dan keputusan controller |
| Next actor / action | `coding_agent`, `controller_reviewer` atau `project_owner`, dengan satu tindakan konkret dan alasan/dependency |

Executor tidak mengubah review menjadi accepted atas nama controller. `_done` adalah penyerahan hasil implementasi sesuai scope, bukan selesai review atau siap produksi. Jika acceptance wajib belum terbukti, status tetap belum done. NOT_RUN yang diizinkan karena di luar scope tetap dijelaskan, tidak diubah menjadi PASS.

## 4. Eksekusi dan penutupan

1. Tetapkan scope/acceptance packet dan branch; lanjutkan implementasi existing. Keputusan engineering rutin dapat diambil sesuai CONTRACT, tanpa meminta izin ulang yang sudah tersedia.
2. Jalankan tes yang bermakna untuk risiko perubahan, kemudian checks/regression yang diwajibkan. PostgreSQL nyata untuk transaksi/RLS/race; simulator bukan bukti perangkat nyata. Perbaiki implementation, bukan melemahkan assertion atau kontrol keamanan.
3. Simpan laporan session dan tiap reviewer di `report/<role>/<UTC>-<slug>.md`: baseline, perubahan, alasan, command/exit/actual evidence, NOT_RUN, risiko dan next step. Pertahankan semua histori.
4. Saat scope executor dan tes wajib tuntas, isi evidence dan set review `pending`; rename packet ke `_done.md` sebagai bagian commit penyerahan. Update handoff/progress, tinjau diff, commit file task yang sah dan push branch. Jangan commit secrets/runtime/pekerjaan tak terkait.
5. Verifikasi remote SHA dan required CI pada kandidat penyerahan. **Nyatakan done hanya setelah publikasi terverifikasi**. Jika publish/check gagal, jangan klaim selesai; pulihkan status/nama unfinished secara aman dan catat kendalanya. Untuk task tanpa perubahan source, bukti ancestor teruji dan diff metadata harus eksplisit. Jangan mencoba menulis SHA final sebuah file ke file itu sebelum commit tersebut ada.
6. Controller mereview kandidat exact SHA. Changes requested membuka kembali task yang sama; accepted mencantumkan SHA dan evidence. Review task sebelumnya harus memenuhi dependency sebelum task dependent berikutnya dijalankan. Independent authorized work boleh lanjut bila prasyaratnya memang terpisah.
7. Merge main, tag, deployment dan aktivasi fitur tetap mengikuti kewenangan serta gates masing-masing. Tidak ada tindakan itu yang otomatis terjadi karena suffix `_done` atau CI hijau.

## 5. Handoff dan batas lingkungan

Satu [LATEST_HANDOFF](../report/LATEST_HANDOFF.md) menyatakan actual main, instruction/task branch bila belum merged, completed work, PR belum merged, blocker dan next eligible task. [docs/AGENT_HANDOFF](../docs/AGENT_HANDOFF.md) hanya panduan navigasi/bootstrap. Jangan menyalin status dari branch lama di atas handoff yang lebih baru.

Seluruh implementasi saat ini dilakukan di sandbox. Persiapan installer/upgrade/recovery memakai lingkungan disposable; lab nyata membutuhkan target/image/lisensi/scope yang sah. Informasi akses deployment disimpan pengendali dan diberikan terpisah hanya saat kesiapan deploy sudah terbukti. Jangan menyimpannya di task. Satu juta client dan zero downtime adalah sasaran yang membutuhkan pengukuran, bukan status yang diperoleh dari dokumen ini.

Selama sesi aktif, lanjutkan task authorized yang eligible tanpa meminta pengguna menyalin prompt panjang lagi. Pada sesi baru, arahkan agent kembali ke file ini. File repository tidak membuat scheduler atau membangunkan agent secara otomatis.

## 6. Jalur komunikasi controller ↔ coding agent

Semua instruksi, hasil dan keputusan yang diperlukan untuk melanjutkan harus dapat ditemukan **di GitHub pada ref yang disebutkan**, tanpa bergantung pada percakapan sebelumnya. Paket dokumen tidak membuktikan pekerjaan kode telah dikerjakan.

| Tahap | Penulis dan record yang diserahkan | Pihak/tindakan berikutnya |
|---|---|---|
| Penugasan | Controller menulis packet: tujuan, scope, baseline, dependency, acceptance dan laporan yang diminta | `coding_agent`: ambil/resume task eligible |
| Implementasi/penyerahan | Coding agent push kode/tes, packet/evidence, execution report dan PR kandidat; completion sesuai §4 | `controller_reviewer`: periksa hasil exact SHA, bukan hanya filename/CI |
| Koreksi | Controller push review report dengan finding ID+evidence+acceptance koreksi; buka task ID yang sama, review `changes_requested` | `coding_agent`: tutup finding pada task yang sama, tes dan push SHA baru |
| Bukti belum cukup | Reviewer tetap `pending`, catat evidence yang kurang dan pemilik tindakan; tidak membuat acceptance rekaan | Actor yang dinyatakan melengkapi bukti/keputusan; dependent task tetap tertahan |
| Diterima | Controller push review report `accepted`, reviewed SHA dan scope; integrasi mengikuti kewenangan/gates Git | `controller_reviewer`: siapkan task dependent berikutnya hanya setelah prasyaratnya terpenuhi |

### Isi penyerahan coding agent

Packet menautkan satu execution report di `report/`, tidak menyalin seluruh laporan ke task atau chat. Report memenuhi CONTRACT §10 dan setidaknya memuat:

- Task ID, instruction ref/path, baseline, branch/PR, implementation/tested SHA dan published candidate; jelaskan report-only descendant terhadap kode yang diuji.
- Perubahan aktual, file dan alasan; decision/compatibility/migration/recovery bila relevan; pekerjaan yang belum selesai dan blocker konkret.
- **Matriks acceptance → actual result → evidence** untuk semua acceptance wajib. Tiap baris menyebut PASS/FAIL/NOT_RUN/BLOCKED dan command/environment/exit serta assertion/log/CI yang mendukung; daftar jumlah tes saja tidak cukup.
- Laporan internal reviewer/sub-agent, risiko/NOT_RUN, serta next actor/action. Internal review executor tidak sama dengan acceptance controller.

Coding agent menyimpan pointer tersebut dan ringkasan hasil singkat di packet, lalu publish/verify remote sebelum menyerahkan. Bila belum ada hasil, tulis belum diserahkan; jangan mengisi expected assertion sebagai actual result atau memakai nama `_done` untuk pekerjaan yang belum tuntas.

### Isi keputusan controller

Controller membaca instruction revision, diff, execution report, evidence dan CI pada **candidate SHA aktual**. Review report di `report/` menyebut task ID, base/candidate/reviewed SHA, bagian yang diperiksa, checks yang dijalankan sendiri versus bukti executor/CI, verdict dan batas keyakinan. Setiap finding memiliki ID, path/evidence, risiko, koreksi minimum dan acceptance penutup; catat finding lama yang sudah ditutup dan yang masih terbuka.

Controller menautkan report dan verdict ke packet, mengisi next actor/action, lalu push dan memverifikasi ref keputusan. Jika belum merged, ref/PR tersebut wajib disebut di handoff supaya coding agent tidak membaca status lama main. Chat atau komentar PR boleh menunjuk record, tetapi tidak menggantikannya. Reviewer tidak menandai dirinya sebagai penulis hasil eksekusi yang tidak dijalankannya.

Jika ada beberapa candidate/ref atau pointer bertentangan, cocokkan task ID, instruction revision, Git ancestry dan designated candidate pada review/handoff controller. Jangan memilih berdasarkan filename atau timestamp terbaru saja. Catat konflik dan tahan aksi yang terdampak sampai pointer konsisten; pekerjaan independen tetap mengikuti prasyaratnya.

Setelah accepted, dependency task penerus menunjuk accepted SHA/review report, serta merge/integration status bila diperlukan. Jika masih changes_requested atau evidence belum cukup, kembali ke ID yang sama; jangan membuat task0020 untuk menutupi task0010 yang belum diterima. Fitur/deploy baru tetap mengikuti gates yang sudah ada.

### Ringkasan handoff minimum

[LATEST_HANDOFF](../report/LATEST_HANDOFF.md) selalu menampilkan task aktif, execution/review status, candidate/ref/PR, execution/review report, **next actor dan exact next action**, serta blocker. Ini ringkasan pointer; details tetap milik packet/report/PR yang dirujuk. Jika tidak ada hasil kode yang dipublikasikan, next actor tetap coding agent, bukan reviewer yang diminta menilai hasil kosong.
