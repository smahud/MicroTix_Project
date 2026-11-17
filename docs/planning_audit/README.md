# MicroTix — finalisasi planning audit

Tanggal review: **10 November 2026 WIB**. Baseline kode: default branch `main`, commit **`16085f825fef25ee4112d74b729c57e623b0bb05`**.

**Status dokumen: FINAL FOR OWNER REVIEW. Status kesiapan memasuki implementasi berdasarkan paket ini: NOT READY**, sampai keputusan integrasi dokumen dan konflik deployment di bawah diselesaikan. Ini bukan status kelengkapan fitur atau hasil benchmark. Aplikasi juga belum layak dinyatakan siap produksi berdasarkan audit statis ini.

## Tujuan dan batas kewenangan

Paket ini memetakan implementasi aktual dan menyiapkan perubahan kecil yang dapat diuji untuk modularitas, isolasi tenant, integritas transaksi, serta upgrade/recovery. Tetap satu backend modular monolith, PostgreSQL, job engine/outbox existing, adapter kecil dan operasi VPS sederhana. Target 1.000 tenant × 1.000 client online adalah sasaran desain; belum dibuktikan.

Perubahan sesi ini hanya pada `docs/planning_audit/` dan `report/`. Tidak ada perubahan kode, migrasi, dependency, installer, konfigurasi deployment, `CONTRACT.md`, maupun `docs/planning_mvp/`. Tidak ada install, deployment, restart, atau pengujian runtime aplikasi.

## Urutan baca

| Urut | Dokumen | Isi dan pemakaian |
|---|---|---|
| 1 | [01_MODULARITY_AUDIT.md](01_MODULARITY_AUDIT.md) | Reality check, domain/dependency, register temuan, rencana koreksi minimum |
| 2 | [02_MODULE_CONTRACTS.md](02_MODULE_CONTRACTS.md) | Ownership, transaksi, akses antardomain, tenant/jobs/API, ekstensi Tax |
| 3 | [03_UPGRADE_PATCH_SAFETY.md](03_UPGRADE_PATCH_SAFETY.md) | Installer aktual, failure/recovery, staged release dan kebijakan migrasi |
| 4 | [04_REVIEW_GATES.md](04_REVIEW_GATES.md) | Acceptance, bukti, pass/fail, exception dan handoff implementasi |

Laporan sesi dan review independen tersedia melalui [laporan audit](../../report/planning-audit/20261109T210133Z-finalization.md). Mulai sesi berikutnya dari [LATEST_HANDOFF](../../report/LATEST_HANDOFF.md).

## Hierarki sumber dan status keputusan

Instruksi pengguna yang berlaku dan [CONTRACT.md](../../CONTRACT.md) mengendalikan kewenangan. Pemilik kebutuhan tetap [PRODUCT](../PRODUCT.md), [ARCHITECTURE](../ARCHITECTURE.md), [FINANCE](../FINANCE.md), [OPERATIONS](../OPERATIONS.md), [ROUTEROS](../ROUTEROS.md), [RADIUS](../RADIUS.md), [IMPLEMENTATION_PLAN](../IMPLEMENTATION_PLAN.md), [ACCEPTANCE](../ACCEPTANCE.md), dan [test-cases.json](../test-cases.json).

Paket ini tidak menjadi kontrak arsitektur tandingan. Aturan yang mengulang invariant existing diberi **BASELINE**. Perubahan engineering atau perluasan kebijakan diberi **PROPOSED**; tidak otomatis APPROVED karena dokumen selesai atau PR dibuat. Pemilik menyetujui perubahan normatif sesuai CONTRACT §4; perbaikan untuk memenuhi kontrak existing tidak perlu diperlakukan sebagai perubahan tujuan produk. Sesi ini sendiri hanya mengotorisasi dokumentasi.

Enam label fakta digunakan konsisten:

| Label | Makna |
|---|---|
| IMPLEMENTED | Struktur/perilaku ditemukan dalam kode; bukan bukti runtime lulus |
| DOCUMENTED | Ketentuan ada dalam dokumen; bukti implementasi belum ada |
| PARTIAL | Sebagian jalur ada; invariant/komponen terkait belum lengkap |
| NOT IMPLEMENTED | Tidak ditemukan implementasi dalam ruang lingkup yang diperiksa; scope disebutkan |
| UNVERIFIED | Bukti tidak cukup untuk kesimpulan tersebut |
| CONFLICT | Bukti antarsumber atau kontrak dan implementasi bertentangan |

`NOT FOUND` berarti path tidak ditemukan, bukan kesimpulan bahwa fiturnya tidak pernah ada di cabang lain. Hasil pengujian memakai NOT_RUN/PASS/FAIL/BLOCKED sesuai ACCEPTANCE; status fakta di atas tidak menggantikannya.

## Snapshot yang perlu dipahami

1. Checkout baru bersih sebelum perubahan. `main` terkonfirmasi melalui GitHub API dan clone. CI historis HEAD [run 42285141174](https://github.com/smahud/MicroTix_Project/actions/runs/42285141174) berstatus success; audit ini tidak menjalankan ulang backend/frontend.
2. `docs/planning_audit/` dan `docs/planning_mvp/` **NOT FOUND di baseline main**. Lima dokumen audit dibuat pada sesi ini. Draft perencanaan yang diberikan sebelumnya dibaca sebagai input tambahan, bukan sebagai bukti fitur atau kontrak main.
3. [PR #7 SSTP](https://github.com/smahud/MicroTix_Project/pull/7), head `d7fa35e5583bc36848e3b45497d2511739298c8a`, masih terbuka ketika discovery. SSTP dan harness GNS3 pada PR itu bukan implementasi main. L2TP/IPsec dan OpenVPN juga tidak dianggap aktif.
4. Handoff lama menyebut `8bb20c3` sebagai SHA kanonis dan Gate A/G sebagai penahan tunggal beta. HEAD sekarang berbeda; temuan kode/operasional baru membatalkan asumsi “hanya perlu host”. Keterangan lama dipertahankan sebagai histori, bukan verifikasi saat ini.
5. Dasar modular monolith dapat dipertahankan. Risiko utama berasal dari invariant transaksi/permission, kontrak antarjalur yang belum konsisten, dan deployment yang belum terbukti, bukan kebutuhan mengganti stack.

## Konflik dan proposal integrasi yang memerlukan keputusan

| ID | Bukti dan konflik | Proposal minimum | Approval/status |
|---|---|---|---|
| DEC-01 | ARCHITECTURE §1 dan OPERATIONS §3 menetapkan aplikasi Compose + PostgreSQL native; installer memakai API/worker systemd native | Tentukan satu baseline. Rekomendasi audit: evaluasi mempertahankan native systemd existing untuk pilot bila privilege split, recovery dan acceptance setara; alternatif implementasikan Compose sesuai kontrak. Sebelum keputusan, kontrak Compose tetap berlaku dan kode tidak dinyatakan compliant | PROPOSED; pemilik diperlukan sebelum mengadopsi native sebagai baseline |
| DEC-02 | Validator `docs/tools/check_docs.py` memasukkan semua file baru dalam docs; manifest existing tidak mencakup planning_audit. Instruksi sesi melarang mengubah manifest | Setelah review paket, setujui perubahan terbatas `docs/repository-manifest.json` dengan lima file baru dan hash aktual melalui mekanisme refresh existing; jangan mengecualikan direktori audit untuk meloloskan CI | PROPOSED; belum diterapkan. CI docs pada diff ini akan gagal sampai integrasi manifest diotorisasi |
| DEC-03 | ARCHITECTURE §6 menetapkan failed terminal, tetapi `retry_job` dapat menghidupkan job FAILED yang sama | Ikuti baseline: retry request terminal membuat job baru dengan relasi asal; pertahankan dedup/logical effect. Bila ingin semantik berbeda, usulkan amendemen eksplisit dengan bukti | Koreksi baseline direkomendasikan; perubahan kebijakan alternatif belum disetujui |
| DEC-04 | Scope buku platform terpisah sudah ditetapkan FINANCE §16; pemetaan tenant ↔ legal entity Tax belum diputuskan | Tetap pisahkan operator dan tenant; tunda schema Tax, PJAP dan keputusan jumlah entitas sampai use case dan review khusus tersedia | PROPOSED untuk desain Tax masa depan; tidak menghalangi koreksi keamanan existing |

DEC-01 dan DEC-02 menahan status kesiapan paket untuk implementasi tanpa interpretasi tambahan. P0/P1 dalam register menahan aktivasi/release fitur terdampak; tidak mengharuskan rewrite atau menunda analisis/perencanaan perbaikan existing. Tidak ada persetujuan merge/deploy yang tersirat.

## Cara memakai hasil audit

Pilih temuan berdasarkan dampak dan dependensi, bukan jumlah file. Untuk setiap PR implementasi berikutnya: rujuk ID, sumber kebutuhan, invariant, perubahan minimum, acceptance, recovery dan bukti. Jangan menyalin seluruh backlog; [tasks.json](../tasks.json) tetap backlog produk, sedangkan register di sini adalah hasil audit snapshot.

Urutan: keputusan dokumentasi → koreksi integritas/permission/jobs → installer/recovery → kontrak UI/API dan coupling terarah → uji host/lab. R2 ledger dan Tax tidak dipaksakan sebagai blocker R1 di luar kontrol keamanan/integritas yang memang digunakan. Tidak ada janji zero downtime, kapasitas satu juta sesi, ataupun kepatuhan pajak.

Dokumen final untuk ditinjau tidak sama dengan desain sudah disetujui. Pemilik meninjau proposal konkret di atas; sesi ini tidak meminta izin untuk menjalankan perbaikan kode atau deployment.
