# Source manifest v2.0 — MicroTix-Documentation-Quality-Ready

Dibuat 28 October 2026 bersamaan dengan paket output MODE A (master prompt v2.0), di atas paket sumber v1.4.
Agent wajib menghitung ulang dengan `sha256sum` setelah berkas ditempatkan; bila berbeda, catat perbedaannya dan telaah ulang sebelum melanjutkan (alur yang sama dengan TK-001 pada manifest v1_4). Berkas ini tidak mencantumkan hash dirinya sendiri. Jalur berkas relatif terhadap akar paket. `sumber/source-manifest_v1_4.md` **dipertahankan sebagai provenance** paket sumber (13/13 hash telah diverifikasi OK pada audit MODE A — lihat `sumber/audit/Documentation_Audit_Report_v1_0.md` bagian B); verifikasi bootstrap memakai manifest ini (v2_0).

Total berkas paket: 32 (termasuk manifest ini; 31 hash tercantum).

## A. Dokumen sumber kebenaran (Markdown, `sumber/`)

| Berkas | Versi dokumen | Ukuran (byte) | SHA-256 | Lokasi di repository |
|---|---|---:|---|---|
| sumber/PRD_SaaS_RTRWNet_v1_4.md | PRD 1.4 | 94859 | 433e8b783cd7dedcf67f949ed4a86e725f3622f2c11c1c05cd72636efb64fe93 | docs/source/ |
| sumber/Panduan_Akuntansi_ISP_v1_1.md | Akuntansi ISP 1.1 | 13090 | 10a6aa39ac88ceee751981f998fe9acd75904c6f9610bbdbd5a97005bf019268 | docs/source/ |
| sumber/Playbook_RouterOS_v1_1.md | Playbook RouterOS 1.1 | 10771 | 1bee9f035d9c88b194f799ee82cfcde3f3d1685a9d5685a04f62f5b7d3ab56de | docs/source/ |
| sumber/Spesifikasi_ACS_TR069_v1_1.md | ACS TR-069 1.1 | 10451 | 98e6acc2170215433f6c93467a9f5ce3028d63fcb3a78d5a429913af339e8b9e | docs/source/ |
| sumber/Spesifikasi_RADIUS_dan_Migrasi_v1_1.md | RADIUS dan Migrasi 1.1 | 20427 | ac36b087f5112cc2b888ca33551e47e35bdb617d81957c907f50a396423d3786 | docs/source/ |
| sumber/Spesifikasi_i18n_v1_1.md | i18n 1.1 | 7155 | 095f61abd62889eb1c1cf1457b582a3d902e0994e3fc5e622c8312794d3577db | docs/source/ |
| sumber/Technical_Design_RTRWNet_v1_3.md | Engineering 1.3 | 64963 | 4371f46a24e3a889e8c425c4edd42787a0cbad01081e80b7e99d28c91e19a89d | docs/source/ |
| sumber/UIUX_Design_RTRWNet_v1_3.md | UI/UX 1.3 | 41550 | ad642cd5daca3d9079dc1f235239b111525f8d79289270f8ba5fa301f159a286 | docs/source/ |
| sumber/decisions_log.md | Decisions Log 1.2 | 15760 | c0634fdcaf18802934d50bf040b32f4f2afbd990c9bf76771027960a6950a92b | docs/source/ |
| sumber/source-manifest_v1_4.md | Manifest 1.4 provenance | 3654 | 3bee1548dd4409a2835f6f7ef48e30cf9b4bf6130ad4a9307d9b16e1eeee757e | docs/source/ |

## B. Berkas instruksi agent (`agent/`)

| Berkas | Versi | Ukuran (byte) | SHA-256 | Lokasi di repository |
|---|---|---:|---|---|
| agent/AGENTS_v1_4.md | AGENTS 1.4 | 12746 | 6cbd851ae1dfe3c48f1606e64675ee1e2537e84890e0d90b4a7ad3623d6dc384 | root, diganti nama menjadi `AGENTS.md`/`tugas.md` |
| agent/tugas_v1_5.md | Tugas 1.5 | 44540 | e418764506ecea66d6b4fac5f017fa4e6ee67528ffd1bc2534283c66b8345ae7 | root, diganti nama menjadi `AGENTS.md`/`tugas.md` |

## C. Berkas pendukung (akar paket)

| Berkas | Fungsi | Ukuran (byte) | SHA-256 |
|---|---|---:|---|
| README.md | Indeks paket dan urutan baca | 11652 | dacd7aaf564da91a0a331cfdbe897057b783e38b16b98e2d83b3db2e780eb15b |
| bootstrap_docs.sh | Skrip penempatan dan verifikasi hash | 3023 | a2b5916910116bb19f5b1ce0276afbff1989a81d1073878a7f71ef12b897cb77 |

## D. Dokumen kualitas (`sumber/quality/`)

| Berkas | Versi | Ukuran (byte) | SHA-256 | Lokasi di repository |
|---|---|---:|---|---|
| sumber/quality/CI_Test_Orchestration_v1_0.md | Quality 1.0 | 6729 | fbbbf20bd35795f414049508ef4c868d2103f205da836c19ef0b5fa479c93d82 | docs/quality/ |
| sumber/quality/Compatibility_and_Hardware_Matrix_v1_0.md | Quality 1.0 | 6428 | f0869e348dd2faf7ffb26d4772c42d1be4da8868996d8e2ed65fb8f9650c45d2 | docs/quality/ |
| sumber/quality/GNS3_Lab_Architecture_v1_0.md | Quality 1.0 | 12865 | 968ab4f28ec53baec83d2620ad42b09ea781221d1846a7bbe2bb5d555cca93e2 | docs/quality/ |
| sumber/quality/Lab_Onboarding_and_Access_v1_0.md | Quality 1.0 | 9088 | 35fa70e6fac3ae45664202a31400280607a47a6b7427d99f73d66f35df5a80ea | docs/quality/ |
| sumber/quality/Performance_Reliability_DR_Plan_v1_0.md | Quality 1.0 | 10161 | c25102efcdddfb1d9f9493193608b88a4d6aa3a11a7d51996d4caf31fa529f9e | docs/quality/ |
| sumber/quality/Quality_Gates_and_Release_Readiness_v1_0.md | Quality 1.0 | 7155 | 542703d0046082ef3405faac1cff0f487d85723c30cff8922d9e423c835fdba0 | docs/quality/ |
| sumber/quality/Quality_Standards_v1_0.md | Quality 1.0 | 15531 | cf66f251c61ee41cc30299294e052838e24cbca2a1aaf3418e70733c633c85dc | docs/quality/ |
| sumber/quality/Security_Test_Plan_v1_0.md | Quality 1.0 | 10786 | 939c1d26cfe2ef892188b51895c15d591c2363ab18eb9d0fc93cbdb53b4edffc | docs/quality/ |
| sumber/quality/Test_Case_Specifications_v1_0.md | Quality 1.0 | 34610 | 789529d61be2d6a3e96d35b017bb4e849eabdb845298be82bf7faf761fa356ee | docs/quality/ |
| sumber/quality/Test_Coverage_Matrix_v1_0.md | Quality 1.0 | 12464 | 03ae4db5a5c29f253803caca476d8675a870be2e00b8ee626fdbfcb0d1af7024 | docs/quality/ |
| sumber/quality/Test_Evidence_and_Reporting_v1_0.md | Quality 1.0 | 9400 | 9470f46364068e9c0a3d3744031d7109bbb3ccdd189e1d608f962ee9e90d7eab | docs/quality/ |
| sumber/quality/Test_Strategy_v1_0.md | Quality 1.0 | 9966 | 89f1964a457d6477a10f321748decd8f8141be56ce40856e85afcd36c447c8be | docs/quality/ |

## E. Artefak audit (`sumber/audit/`)

| Berkas | Versi | Ukuran (byte) | SHA-256 | Lokasi di repository |
|---|---|---:|---|---|
| sumber/audit/Documentation_Audit_Report_v1_0.md | Audit 1.0 | 14735 | 1f061df25a3f145d4b3903709c18a428e76cb3eb964e9ddf7022d4dd79f6bd22 | docs/audit/ |
| sumber/audit/Documentation_Changelog_v1_0.md | Audit 1.0 | 7140 | c5713d87465a359e0ec3a863f2253f9e8be824ac045461c2eff0720688017eeb | docs/audit/ |
| sumber/audit/Documentation_Quality_Gate_Results_v1_0.md | Audit 1.0 | 8213 | d45b80bededeb3ea881f9c603ae0b14eb5b1086c5eaa33637635897e0278a17a | docs/audit/ |
| sumber/audit/Source_to_Output_Map_v1_0.md | Audit 1.0 | 6571 | 4e81f6927d8d28d0d27303dc278b47615e80fc7c8db20a13eb3f46014ae7f848 | docs/audit/ |
| sumber/audit/Unresolved_Issues_v1_0.md | Audit 1.0 | 5350 | 97efd36e49c30f4aa21f5ca07dde1b4fbc02006ec42712bbf3eed8a233032fc8 | docs/audit/ |

## F. Penempatan di repository

```text
AGENTS.md                       <- agent/AGENTS_v1_4.md
tugas.md                        <- agent/tugas_v1_5.md
docs/source/<seluruh berkas sumber normatif + kedua manifest>
docs/quality/<12 berkas kualitas>  <- sumber/quality/
docs/audit/<5 berkas audit>        <- sumber/audit/
docs/decisions.md               <- salinan kerja decisions_log.md (agent hanya menambah Bagian F)
```

Skrip `bootstrap_docs.sh` menempatkan berkas dan memverifikasi hash terhadap manifest ini (v2_0).

## G. Catatan verifikasi MODE A (28 Oktober 2026)

Verifikasi paket sumber v1.4 dilakukan auditor MODE A sebelum pembuatan paket output: seluruh 13 hash tabel A-C manifest v1_4 **cocok** (alat `sha256sum`, workspace terisolasi; detail pada `sumber/audit/Documentation_Audit_Report_v1_0.md` bagian B). Bagian E manifest v1_4 dibiarkan kosong untuk catatan TK-001 agent implementasi di repository (kekosongan tersebut bukan temuan). Hash pada manifest ini dihitung dari berkas final paket output; verifikasi ulang wajib setelah ekstraksi.
