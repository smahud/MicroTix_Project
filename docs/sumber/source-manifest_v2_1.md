# MicroTix — Active Source Manifest v2.1

Revisi paket: **2.1-build.1**. Arsitektur: **v2.1**. Tanggal30 Oktober2026 Asia/Jakarta. Manifest aktif tunggal; manifestv1.4/v2.0 tetap provenance. Nilai dihitung dari bytes final; manifest sendiri dikecualikan dari payload hash untuk menghindari self-reference.

## 1. Baseline dan status

Input langsung: MicroTix-Documentation-v2_1-audit_2.zip;348720byte;SHA-256 `b9de2888c6795a43a9cbae932c23607bc900a68cf2db5c29d6400cfdadd2150b`. Baseline sebelum modifikasi:40file,39payload sesuai,1174673byte terurai;manifest SHA-256 `5ccf575dd9ab933fbe604c10564dcd4ce9e5585668baf265ff2c2d356a831c3d`. Input awal2.1-macro.1 tetap ada dalam bundle provenance; SHA-256 `554123935857366a19fe3719c1abadbaf0fe836db581a436c7da7b402739ec8f`.

Revisi ini menambah17file kontrak/schema/test/source standar/agent/tool pendukung, tanpa menghapus40path baseline. Formal full-audit BLOCKED oleh SEC-DEC-01 dan review semantik/clause completeness independen; foundation documentation dapat dipakai untuk scope build setelah mandat Mode C. Semua runtime NOT_RUN. G0–G5/operasional BLOCKED. Hash tidak menyatakan autentisitas penerbit.

## 2. Metadata mesin

<!-- MANIFEST_META_BEGIN -->
```json
{
  "schema_version": "2.1",
  "package_revision": "2.1-build.1",
  "manifest_self_path": "sumber/source-manifest_v2_1.md",
  "package_file_count": 57,
  "payload_entries": 56,
  "payload_bytes": 3759147,
  "payload_root_sha256": "0509d8e41c3d0e0e41c169481e61e7c3c4011eb6e140d1a037d07e395b421be8"
}
```
<!-- MANIFEST_META_END -->

## 3. Source→target, class, size dan SHA-256

Verifikasi semua sumber sebelum menempatkan target mana pun. Target identik boleh dilewati; target berbeda conflict/staging review tanpa overwrite. Manifest sendiri ditempatkan pada `docs/source/source-manifest_v2_1.md` sesudah validasi keseluruhan. Semua source path relatif akar ZIP kanonik; target relatif root repository implementasi. Scripts --root menerima akar paket kanonik yang dipertahankan, bukan root repository aplikasi yang telah memiliki file tambahan. Legacy bootstrap AUDIT_ONLY tidak dijalankan.

<!-- MANIFEST_ROWS_BEGIN -->
| Path sumber | Target repository | Kelas | Ukuran byte | SHA-256 |
|---|---|---|---:|---|
| MicroTix-File-1-Kontrak-Revisi-Lengkap.md | MicroTix-File-1-Kontrak-Revisi-Lengkap.md | ACTIVE | 103291 | 533d3269b3f156b0fb9409cfc7098d3fdbc16d5cf394055ab2a21c7fdf06928e |
| MicroTix-Template-Onboarding-Server-GNS3.md | MicroTix-Template-Onboarding-Server-GNS3.md | ACTIVE | 22030 | 8dfd2b3b937cab32074b4f46c9f12f59a4cbcd1373d4cfb8e948a70d69331510 |
| README.md | docs/audit/package-README_v2_1.md | ACTIVE | 2077 | 142a11b1895813d0021e0d5956cddc80d5bf9b60c6cc60b069e04265c22b932d |
| agent/AGENTS_v2_1.md | AGENTS.md | ACTIVE | 14340 | 4039d3879e9a603fa7bda477fc6984c299aba10a78039fdf04a030dbe89bf83d |
| agent/CLAUDE.md | CLAUDE.md | ACTIVE | 556 | 95a4d80e0b8e8fac4e2dec266ae7aca63b64248fb893996dcb0600c93aea4b39 |
| agent/START_BUILD.md | docs/contracts/START_BUILD.md | ACTIVE | 2081 | 4e78468809f3a629f068fd2cc5a222736778b94b1f0b03dcc3ead18ba97df762 |
| agent/task-contracts_v2_1.json | docs/contracts/task-contracts_v2_1.json | ACTIVE | 455781 | f66ffd8f479ff5fb03891588f8ae8203cc73b17fb323d1c9be0369ada66e3772 |
| agent/tugas_v2_1.md | tugas.md | ACTIVE | 47479 | 713f9095ff312f0c847a79f97261bebfd5c9b8e881e41ac323df2cd086075f6c |
| bootstrap_docs.sh | docs/audit/legacy/bootstrap_docs.sh | AUDIT_ONLY | 3241 | 6e52be1e12985c8da66337ccb9e6cbc02d36122228920b32c8230b35f5a11de4 |
| sumber/PRD_SaaS_RTRWNet_v2_1.md | docs/source/PRD_SaaS_RTRWNet_v2_1.md | ACTIVE | 96509 | 55e3bf34eb2933921ab707727fdcf2a9de8e68aca4ffb860c0d42d0d87a54cb0 |
| sumber/Panduan_Akuntansi_ISP_v2_1.md | docs/source/Panduan_Akuntansi_ISP_v2_1.md | ACTIVE | 14691 | 998a1aa138bba2032554ad36a4f71f20016a69f3600944ffb3fb043e71d6cdef |
| sumber/Playbook_RouterOS_v2_1.md | docs/source/Playbook_RouterOS_v2_1.md | ACTIVE | 10365 | ae6388f73707d325927bd497b2ea26d5f8213bebc8cdf553f9488a4098680454 |
| sumber/Spesifikasi_ACS_TR069_v2_1.md | docs/source/Spesifikasi_ACS_TR069_v2_1.md | ACTIVE | 11861 | a8167e0d986eb80a166e8c193deab1d966abc6041615aa450e9a0eb5d745e60c |
| sumber/Spesifikasi_RADIUS_dan_Migrasi_v2_1.md | docs/source/Spesifikasi_RADIUS_dan_Migrasi_v2_1.md | ACTIVE | 18927 | fa935fae5c797229571433e72c0c9bde015f86f5a4be231415952f815c2813ef |
| sumber/Spesifikasi_i18n_v2_1.md | docs/source/Spesifikasi_i18n_v2_1.md | ACTIVE | 7778 | 80a032f32292c827e7b2d2002fda89dd7ea175071c2b0f7cce346150105dd031 |
| sumber/Technical_Design_RTRWNet_v2_1.md | docs/source/Technical_Design_RTRWNet_v2_1.md | ACTIVE | 67514 | 499244df353670a84b6c96d05db6f3103d0036f5262f36b66f06c70d34ab71af |
| sumber/UIUX_Design_RTRWNet_v2_1.md | docs/source/UIUX_Design_RTRWNet_v2_1.md | ACTIVE | 42541 | 2c9e8c09bcb80bd6cd316f9e405dff0b3a974232e124bba17845484df51bd387 |
| sumber/audit/Documentation_Audit_Report_v2_1.md | docs/audit/Documentation_Audit_Report_v2_1.md | PROVENANCE | 11846 | 491ae36df5acdc7ee946226a14de596f7301b975917171beb70b80d460f1bce4 |
| sumber/audit/Documentation_Changelog_v2_1.md | docs/audit/Documentation_Changelog_v2_1.md | ACTIVE | 14464 | 5ad3751383a6f0a326a9f22946bd65a9427590089765d7dcc7deed47885c548d |
| sumber/audit/Documentation_Quality_Gate_Results_v2_1.md | docs/audit/Documentation_Quality_Gate_Results_v2_1.md | ACTIVE | 1847 | 8b9f35c6cd3a918a5ae3793e4927821faec3e13cb1944a296ff26a8b592a981b |
| sumber/audit/Macro_Consolidation_Report_v2_1.md | docs/audit/Macro_Consolidation_Report_v2_1.md | PROVENANCE | 3710 | 6ad42e103337a2ef969c2e84e47d5009c85f01fe3e83a9744591d245eb360de5 |
| sumber/audit/Requirements_Traceability_Matrix.json | docs/audit/Requirements_Traceability_Matrix.json | ACTIVE | 388247 | 7d792fc62fd9014b2a51b7b21f3482506c9b9ea610e7e12d6d6c5582b41984da |
| sumber/audit/Source_to_Output_Map_v2_1.md | docs/audit/Source_to_Output_Map_v2_1.md | PROVENANCE | 10971 | d4c07d26f82b4b2895854ca109cb25e8f0b64e148cec71305a967ab9688a2e50 |
| sumber/audit/Unresolved_Issues_v2_1.md | docs/audit/Unresolved_Issues_v2_1.md | ACTIVE | 3662 | efcc3f1928a8041c29f7ee1d209ad52769849b2ef4cee772af1a0ade8cb8e763 |
| sumber/audit/input-provenance_v2_1.json | docs/audit/input-provenance_v2_1.json | PROVENANCE | 11120 | e3063bfc74c7ff01a77a84e1d6531e4f08491428f201114a3dcdc6a77d6fcff2 |
| sumber/audit/static-verification_v2_1.json | docs/audit/static-verification_v2_1.json | PROVENANCE | 5685 | 3c13ed0562752f920830de0defa411805cab32c9de741bfafe91a9e01f7051fc |
| sumber/contracts/Execution_Design_v2_1.md | docs/contracts/Execution_Design_v2_1.md | ACTIVE | 13642 | e7a1ae25de4e657c7d005eb35a9608eb28f00ab5531d776081531f4b837b16a1 |
| sumber/contracts/Owner_Decision_Requests.md | docs/contracts/Owner_Decision_Requests.md | ACTIVE | 2606 | d79b7e9b0dcf6d153b124fb2f480b0c2186e74a6712a0693decf1ec2acf4e1c6 |
| sumber/contracts/execution-profile.schema.json | docs/contracts/execution-profile.schema.json | ACTIVE | 6560 | e20dd961252fa84903a5c5194bab796b8d72afbdd6772f069c7421068600c32d |
| sumber/contracts/job-kind-registry_v2_1.json | docs/contracts/job-kind-registry_v2_1.json | ACTIVE | 33312 | d5d6f50273d5f507e0662b11032d4aef544663521f214dc777637213d16c7c61 |
| sumber/contracts/parameter-registry_v2_1.json | docs/contracts/parameter-registry_v2_1.json | ACTIVE | 105470 | 1dfabf9495a1e957ec469961ff40a3a25af0992d8d06fede06e144ce87beaaeb |
| sumber/contracts/target-registry.schema.json | docs/contracts/target-registry.schema.json | ACTIVE | 5755 | 141538304780bee017152977595003103e9b9cced4ffbece690bf1ec871fe657 |
| sumber/decisions_log.md | docs/source/decisions_log.md | ACTIVE | 17114 | 713f649068763fb92db37a20c70793cb31bfd5708a8168667a9970e0affa2cce |
| sumber/quality/CI_Test_Orchestration_v2_1.md | docs/quality/CI_Test_Orchestration_v2_1.md | ACTIVE | 14057 | c8148cceb26a9a0371365124cf5c26b24ab82f577d94dac5c286d7cf1c077530 |
| sumber/quality/Compatibility_and_Hardware_Matrix_v2_1.md | docs/quality/Compatibility_and_Hardware_Matrix_v2_1.md | ACTIVE | 14975 | cfd9ecfbe41dbce7bd88556025b5fbaee044cb06d3e9dfda4e52b48cc1ef1d2c |
| sumber/quality/GNS3_Lab_Architecture_v2_1.md | docs/quality/GNS3_Lab_Architecture_v2_1.md | ACTIVE | 3348 | 0e6e788e854e727d8429173890c2c4946aca348eeda6b6b58a51404f5537c7a8 |
| sumber/quality/Lab_Onboarding_and_Access_v2_1.md | docs/quality/Lab_Onboarding_and_Access_v2_1.md | ACTIVE | 6095 | e802331663e7a182d5ed62011797b0ad22a0335f30bdbfc4581491242509604f |
| sumber/quality/Performance_Reliability_DR_Plan_v2_1.md | docs/quality/Performance_Reliability_DR_Plan_v2_1.md | ACTIVE | 11990 | abc72f6a37d1dfd800b61f686347b23fd36814e06fd386ae0d881d84cd8743b1 |
| sumber/quality/Quality_Gates_and_Release_Readiness_v2_1.md | docs/quality/Quality_Gates_and_Release_Readiness_v2_1.md | ACTIVE | 48264 | cdb36178469401c164f257ed71a8443780bc1eac2fd0e973b07e1864650d017d |
| sumber/quality/Quality_Standards_v2_1.md | docs/quality/Quality_Standards_v2_1.md | ACTIVE | 10944 | b34cfbfa2db15aae0a1decd1295651fe27fe53f81570db77984b9dfae191a7f2 |
| sumber/quality/Security_Test_Plan_v2_1.md | docs/quality/Security_Test_Plan_v2_1.md | ACTIVE | 20617 | 818cc42ab9c12587e823af56d58a800929131ca6529a63d61019e374fa317c47 |
| sumber/quality/Test_Case_Specifications_v2_1.md | docs/quality/Test_Case_Specifications_v2_1.md | ACTIVE | 224321 | 87e889ca778d81261dc40bfa5020221fac2d1af2de49780984f0435fcedaee93 |
| sumber/quality/Test_Coverage_Matrix_v2_1.md | docs/quality/Test_Coverage_Matrix_v2_1.md | ACTIVE | 3081 | 35f8db4f01ee8fc1e117085ef3a8a80eecac84a2b1969c7d270b7bf2f3442ac7 |
| sumber/quality/Test_Evidence_and_Reporting_v2_1.md | docs/quality/Test_Evidence_and_Reporting_v2_1.md | ACTIVE | 4193 | 573d47904e40f3d8e124fe79e7e6c284bee9d8d9bbc068367df8871118f9fb60 |
| sumber/quality/Test_Strategy_v2_1.md | docs/quality/Test_Strategy_v2_1.md | ACTIVE | 11306 | 411f976531dfa53cec1f732fd209fe323a98d64ef5d753f60572adca367537aa |
| sumber/quality/asvs-applicability_v2_1.json | docs/quality/asvs-applicability_v2_1.json | ACTIVE | 387700 | 49130600fcf294c1707df8af775fee0407067980a06d1d600d2fa4794208b84e |
| sumber/quality/asvs/ASVS_5.0.0_en.csv | docs/quality/asvs/ASVS_5.0.0_en.csv | ACTIVE | 105100 | 98c8fe911b9edb403af8ee05d3ce8201ecac2659e313b053890a62847cdcf680 |
| sumber/quality/asvs/README.md | docs/quality/asvs/README.md | ACTIVE | 960 | 9575c93b439605b64e0af6b3b3ffe31bec261902b22ea7c9dc3679b5556fd4f0 |
| sumber/quality/release-applicability_v2_1.json | docs/quality/release-applicability_v2_1.json | ACTIVE | 453872 | 0453a2506aef425bc4c6120a5060e26ef9ed887372655af29f30d77e00c8a9e4 |
| sumber/quality/supplemental-test-registry_v2_1.json | docs/quality/supplemental-test-registry_v2_1.json | ACTIVE | 605394 | 27c0228d4b2e324a3b3c514f99bbfced5e90d55bc9af62671c7903021945d89f |
| sumber/quality/test-case-registry_v2_1.json | docs/quality/test-case-registry_v2_1.json | ACTIVE | 240311 | 8851b7ea7f88dfd9dcec1cec6b34c2f149c785bfc44c7f8547934160d2624a70 |
| sumber/source-manifest_v1_4.md | docs/source/source-manifest_v1_4.md | PROVENANCE | 3654 | 3bee1548dd4409a2835f6f7ef48e30cf9b4bf6130ad4a9307d9b16e1eeee757e |
| sumber/source-manifest_v2_0.md | docs/source/source-manifest_v2_0.md | PROVENANCE | 7184 | 3a6276f781b89869c1e28431e9d10b94a07a854a8f5e611d4536ccee085b9934 |
| tools/task_context_v2_1.py | tools/task_context_v2_1.py | VERIFICATION_TOOL | 1613 | 8804c110b863808c0580a613059b5dd5f53831ca1d7c77169a134be29c2fd80c |
| tools/validate_execution_docs_v2_1.py | tools/validate_execution_docs_v2_1.py | VERIFICATION_TOOL | 15177 | 706fe3605d675b3972cc3f341b3658b58c1e4d1664fe55828b740100c35799b0 |
| tools/verify_repository_v2_1.py | tools/verify_repository_v2_1.py | VERIFICATION_TOOL | 7918 | a2e30142781230e5d50dac0adbd926f77d34b8437a3afe4b9bc24ace5867588b |
<!-- MANIFEST_ROWS_END -->

## 4. Seal dan reproducibility

Source Finalization → Static Validation → Manifest Generation → Tree Verification → Deterministic Packaging → Package Verification. Akar payload:SHA-256 konkatenasi baris sha256<TAB>size_decimal<TAB>source_path<LF> diurut byteUTF-8POSIX. Unknown/missing/extra/collision/symlink/traversal ditolak. ZIP berakar MicroTix-Documentation-v2_1-Final,57file tanpa directory entries; timestamp tetap2026-10-30T00:00:00,mode0644,DEFLATE9,urutanUTF-8. Byte reproducibility dinilai pada runtime Python/zlib yang dicatat; lintas versi kompresor tidak dijanjikan. Hasil pascaseal dan hashZIP/manifest di amplop eksternal, tidak menyunting payload tersegel.

Klasifikasi file termasuk manifest: {"ACTIVE": 46, "AUDIT_ONLY": 1, "PROVENANCE": 7, "VERIFICATION_TOOL": 3}. PROVENANCE mengacu sejarah audit dan tidak mengoverride kontrak aktif. ASVS source berlisensi/terpin adalah rujukan aktif untuk applicability, bukan klaim sertifikasi. Semua output audit pendamping adalah indeks/evidence, bukan keputusan produk baru.
