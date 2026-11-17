# Integrasi merge-all branch ke main — 17 November 2026 (wewenang pemilik repo)

## 1. Otorisasi dan dasar

Pemilik repo menginstruksikan eksplisit: "Pastikan master/main selalu hijau
setelah commit, merge all branch and tree, and push" dengan PAT
commit/merge/push — preseden wewenang merge pemilik (PR9, PR24/PR25).
Sesi executor task0020 (koreksi REV-1711-01–09) selesai terlebih dahulu
(PR30, CI 3/3 success) sebelum merge-all dijalankan.

## 2. Urutan merge dan keputusan penyelesaian

| Branch | Perlakuan |
|---|---|
| `session/2026-11-17-0020-job-lifecycle-correction` (PR30) + ancestornya (PR26/27/29) | Merge penuh (koreksi task0020 + decision/candidate lineage). Suite 562 lulus pada tree ini sebelum push. |
| `session/2026-11-15-pa006-executor-state-check`, `session/2026-11-17-0020-executor-state-check`, `docs/payment-point-planning-20261113` | Merge penuh — report/docs-only additive; manifest di-refresh. |
| `review/0010-pa006-submission-check-20261112`, `review/0010-pa006-controller-20261113` | Record historis ditambahkan; konflik kode diselesaikan ke versi accepted current (R5 PR24/25); packet lama 0010 tidak dihidupkan ulang (`_done` tetap kanonik); varian migration awal `0004_idem_principal_scope` DIHAPUS (bentrok nomor dengan `0004_idempotency_identity` accepted). |
| `session/2026-11-13-pa006-idempotency` | Menjadi ancestor melalui merge controller-20261113 (record terbawa). |
| `session/2026-11-07-sstp-phase2` | Union: fencing task0020 (scope/guard ownership) + fitur SSTP (SstpAccount model+0011, kredensial APPLIED, revoke pada release/replace, render command, lab files). 3 uji historis diselaraskan ke kontrak authority current (provenance aktor sah; actorless dikarantina sejak R1) — semantik pengujian tidak dilemahkan. Suite penuh 580 lulus. |
| `parallel/beta-be2` | Kode current kanonik dipertahankan SELURUHNYA (delta backend/apps = 0 baris): konsolidasi beta-0.1 sudah port selektif; modul varian paralel (access/, enrollment/csv_import, migrasi 0002–0005 bentrok nomor, uji lama) DIHAPUS agar graf migrasi sah; record laporan/evidence historis branch tetap ditambahkan. |
| `docs/planning-audit-20261110` (PR8) | Dokumen planning audit ditambahkan sebagai RECORD historis; LATEST_HANDOFF current dipertahankan; tidak mengaktivasi perubahan normatif apa pun (packet task0020 tetap tidak mengadopsi PR8 sebagai instruksi). |

## 3. Verifikasi hijau

- Setiap batch merge diverifikasi lokal sebelum push: **suite backend penuh
  580 passed/1 skipped** (PG 17.12 nyata, fresh test DB) pada tree final;
  antara batch, `makemigrations --check` "No changes detected", `manage.py
  check` 0 issue, `docs/tools/check_docs.py` PASS (manifest di-refresh dua
  kali setelah review diff additive).
- Semua branch kini merged (`git branch -r --no-merged main` = kosong);
  tidak ada force-push/reset; histori PR7/8/14 dan seluruh report lama
  dipertahankan.
- CI GitHub pada head final diverifikasi setelah push (lihat §4 update).

## 4. Batas

Merge-all adalah keputusan integrasi GIT pemilik — BUKAN acceptance
controller: review koreksi task0020 tetap **pending** pada PR30
(controller_reviewer masih pemilik verdict), dan merge bukan
deployment/aktivasi/release. Production Beta tetap NOT_READY
(installer/upgrade/restore/secret/scheduler/DEC-01/02/host/lab/kapasitas
belum terbukti). PR historis otomatis ter-tutup karena head-nya kini
ancestor main — tanpa close paksa.

Status sesi ditulis ulang pada [LATEST_HANDOFF](../LATEST_HANDOFF.md).
