# Source manifest v1.4

Dibuat 28 Oktober 2026 bersamaan dengan paket dokumen v1.4. Agent wajib menghitung ulang dengan `sha256sum` setelah berkas ditempatkan (TK-001); bila berbeda, catat perbedaannya pada bagian "Catatan verifikasi" dan telaah ulang sebelum melanjutkan. Berkas ini tidak mencantumkan hash dirinya sendiri. Jalur berkas relatif terhadap akar paket.

## A. Dokumen sumber kebenaran (Markdown, `sumber/`)

| Berkas | Versi dokumen | Ukuran (byte) | SHA-256 | Lokasi di repository |
|---|---|---:|---|---|
| sumber/PRD_SaaS_RTRWNet_v1_4.md | PRD 1.4 | 94787 | 397fff6949116c3f3bcd7aa90df1295b92e90648ad9dc3e535fc5688fbbdb97a | docs/source/ |
| sumber/Technical_Design_RTRWNet_v1_3.md | Engineering 1.3 | 64916 | 75b35e8d4bae8691e928fc679761e38094fb7633253bd8da3e8d736162de0aac | docs/source/ |
| sumber/UIUX_Design_RTRWNet_v1_3.md | UI/UX 1.3 | 41550 | ad642cd5daca3d9079dc1f235239b111525f8d79289270f8ba5fa301f159a286 | docs/source/ |
| sumber/Spesifikasi_RADIUS_dan_Migrasi_v1_1.md | RADIUS dan Migrasi 1.1 | 20427 | ac36b087f5112cc2b888ca33551e47e35bdb617d81957c907f50a396423d3786 | docs/source/ |
| sumber/Playbook_RouterOS_v1_1.md | Playbook RouterOS 1.1 | 10771 | 1bee9f035d9c88b194f799ee82cfcde3f3d1685a9d5685a04f62f5b7d3ab56de | docs/source/ |
| sumber/Spesifikasi_ACS_TR069_v1_1.md | ACS TR-069 1.1 | 10451 | 98e6acc2170215433f6c93467a9f5ce3028d63fcb3a78d5a429913af339e8b9e | docs/source/ |
| sumber/Panduan_Akuntansi_ISP_v1_1.md | Akuntansi ISP 1.1 | 13090 | 10a6aa39ac88ceee751981f998fe9acd75904c6f9610bbdbd5a97005bf019268 | docs/source/ |
| sumber/Spesifikasi_i18n_v1_1.md | i18n 1.1 | 7155 | 095f61abd62889eb1c1cf1457b582a3d902e0994e3fc5e622c8312794d3577db | docs/source/ |
| sumber/decisions_log.md | Decisions Log 1.2 | 15678 | f683fc136b89b63d29466a1f8719a9d8ca4887f5f7835ac9afc10e1260640184 | docs/source/ (salinan kerja: docs/decisions.md) |

## B. Berkas instruksi agent (`agent/`)

| Berkas | Versi | Ukuran (byte) | SHA-256 | Lokasi di repository |
|---|---|---:|---|---|
| agent/tugas_v1_4.md | Tugas 1.4 | 41980 | a1f78ce01e05191284f31a1669b7b06884ef84acb9c40dbb67bc0fdde13db71a | root, diganti nama menjadi `tugas.md` |
| agent/AGENTS_v1_3.md | AGENTS 1.3 | 8039 | 2d2101354241b4a8254254a3f35423c30bccd91ba144563cd5af8df980376663 | root, diganti nama menjadi `AGENTS.md` |

## C. Berkas pendukung (akar paket)

| Berkas | Fungsi | Ukuran (byte) | SHA-256 |
|---|---|---:|---|
| README.md | Petunjuk paket dan indeks | 6839 | 491628f3c64afc39b7f782c10de61555d6126570031e8b0b17ceddc5ef4d1afc |
| bootstrap_docs.sh | Skrip penempatan dan verifikasi hash | 1610 | 9f4681be19840adf9e67b5400d07af66921beb6f58474c016bf3128c798ae16a |

## D. Penempatan di repository

```text
AGENTS.md                       <- agent/AGENTS_v1_3.md
tugas.md                        <- agent/tugas_v1_4.md
docs/source/PRD_SaaS_RTRWNet_v1_4.md
docs/source/Technical_Design_RTRWNet_v1_3.md
docs/source/UIUX_Design_RTRWNet_v1_3.md
docs/source/Spesifikasi_RADIUS_dan_Migrasi_v1_1.md
docs/source/Playbook_RouterOS_v1_1.md
docs/source/Spesifikasi_ACS_TR069_v1_1.md
docs/source/Panduan_Akuntansi_ISP_v1_1.md
docs/source/Spesifikasi_i18n_v1_1.md
docs/source/decisions_log.md
docs/source/source-manifest_v1_4.md
docs/decisions.md               <- salinan kerja decisions_log.md (agent hanya menambah Bagian F)
```

Skrip `bootstrap_docs.sh` menempatkan berkas dan memverifikasi hash.

## E. Catatan verifikasi (diisi agent pada TK-001)

Agent mencatat di sini: hasil `sha256sum` vs tabel A-C (OK/BEDA per berkas), perintah dan alat yang dipakai, serta tanggal verifikasi. Bagian ini memang kosong sebelum TK-001 dijalankan; kekosongannya bukan temuan.
