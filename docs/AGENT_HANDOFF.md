# MicroTix — panduan handoff agent

Diperbarui 12 November 2026 (Asia/Jakarta), sesuai keputusan pemilik tentang task berbasis repository.

**Mulai/resume dari [task/0000-start-here.md](../task/0000-start-here.md).** Aturan wajib ada di [CONTRACT §6A](../CONTRACT.md); status sesi aktual hanya di [report/LATEST_HANDOFF.md](../report/LATEST_HANDOFF.md). File ini adalah panduan navigasi/bootstrap, bukan salinan status main, prioritas atau gate rilis.

## 1. Sebelum bekerja

- Fetch default branch dan refs PR aktual; periksa git status/diff/worktrees/CI. Pertahankan pekerjaan pihak lain dan arsip branch lama. Buat branch/worktree sesuai packet; jangan memakai archive branch sebagai main.
- Baca latest handoff, checkpoint [progress](progress.md), lalu packet bernomor eligible. Dependency dan review prasyarat menentukan kelayakan, bukan nomor saja.
- Jangan mengulang task `_done` atau kandidat pending-review. Jika baseline berubah, review delta; update/rerun relevant checks sebelum melanjutkan.
- Scope sekarang sandbox-first menuju Beta terbatas. Sebuah merge/CI success tidak membuktikan install, upgrade, restore, perangkat atau release_enabled.

## 2. Penyerahan dan kelanjutan

Controller menulis task dan mereview exact SHA; executor mengimplementasikan, menguji, membuat laporan, commit/push dan memverifikasi remote. Completion rename `_done.md`, reopening same-ID, evidence, statuses dan authority mengikuti panduan tetap/CONTRACT; tidak ada queue framework baru.

Setiap sesi/sub-agent tetap membuat report unik. Latest handoff menyebut actual main, instruction/task ref bila belum merged, hasil terverifikasi, PR terbuka, blocker dan next eligible packet. Progress adalah checkpoint ringkas; report menyimpan bukti rinci. Jangan mengganti handoff baru dengan status historis dari branch lain.

Keterangan handoff lama yang menyatakan host sebagai satu-satunya penahan Beta sudah ditarik melalui review 11 November 2026. Riwayat dan hasil test bertanggal tetap ada di progress, report dan Git; gunakan status/gates aktual untuk instruksi berikutnya. PA-001 telah merged melalui PR9; prioritas berikutnya dirujuk dari latest handoff dan task, bukan tabel statis di file ini.

## 3. Bootstrap/verifikasi sandbox

Gunakan [setup_env.sh](tools/setup_env.sh) dan [backend dev_bootstrap.sh](../backend/scripts/dev_bootstrap.sh) sesuai runtime yang tersedia; baca parameter/path aktual, jangan mengasumsikan direktori dari sesi agent lain masih ada. Referensi command: [IMPLEMENTATION_PLAN §4](IMPLEMENTATION_PLAN.md) dan [backend README](../backend/README.md).

Jalankan tests yang diwajibkan packet, Django/migration/API checks yang relevan, frontend checks bila terdampak serta validator docs. PostgreSQL nyata wajib untuk transaksi/RLS/race. Daemon FreeRADIUS, CHR/GNS3, browser E2E dan rehearsal install/upgrade/restore hanya dinyatakan PASS bila benar-benar dijalankan pada scope yang sesuai; ketidaktersediaan dicatat NOT_RUN/BLOCKED, bukan sukses simulasi.

Deployment dan akses perangkat mengikuti [OPERATIONS](OPERATIONS.md), [ACCEPTANCE](ACCEPTANCE.md) serta kewenangan yang sudah diberikan. Jangan menaruh informasi akses deployment di packet atau meminta/menyerahkannya sebelum candidate lolos readiness review.
