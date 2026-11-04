# MicroTix — bundle penyerahan 2.1-build.1

Tanggal penyerahan: 31 Oktober 2026, Asia/Jakarta. Architecture v2.1.

**Kontrak fondasi siap untuk build lokal berscope setelah mandat workspace Mode C. Full final audit BLOCKED; operasional BLOCKED.** SEC-DEC-01 dan review semantik independen B05/B11 belum selesai. Tidak ada aplikasi atau runtime test dijalankan, deployment, perubahan jaringan, ataupun akses produksi dalam pekerjaan ini.

Baca `FINAL_AUDIT_REPORT.md`, `Unresolved_Decisions_and_Blockers.md`, lalu `Claude_Code_Implementation_Handoff.md`. Keputusan konkret yang tersisa ada dalam `Owner_Decision_Requests.md`; panduan review berbeda penulis ada pada `Independent_Semantic_Review_Packet.md`.

## Susunan

- `MicroTix-Documentation-v2_1-build_1.zip`: satu paket kanonik aktif, 57 berkas/56 payload manifest. SHA-256 `e39bec94208b077b55a609bd56504e8c88f36d08c0d43a244e54ec735a8fd8b9`.
- Sebelas laporan audit wajib dan dua pendukung review/keputusan: evidence dan navigation, bukan authority bisnis baru.
- `MicroTix-Control-Export-v2_1-build_1.md`: proyeksi tiga kontrol dengan paritas byte; tidak mengganti ZIP kanonik.
- `evidence/`: hasil pemeriksaan, diff lengkap, katalog sumber, antrean review dan Git history bundle.
- `build_tools/`: script pembuatan dan pemeriksaan dokumentasi; tidak membangun aplikasi.
- `reproduction_inputs/`: input audit.2, standar ASVS terpin dan konteks audit yang diperlukan untuk source replay.
- `provenance/`: bundle audit.2 utuh yang menyimpan arsip asal dan bukti historis; jangan gunakan sebagai kontrak implementasi aktif.
- `Bundle_Inventory.json`: ukuran dan SHA-256 semua member selain inventory itu sendiri. Checksum ZIP disediakan di luar arsip agar tidak terjadi self-reference.

Path `sumber/...`, `agent/...` dan `tools/...` dalam laporan merujuk root paket kanonik setelah diekstrak. Path `evidence/...` dan `build_tools/...` merujuk root bundle ini. Hash dan nomor baris harus dibaca terhadap revisi yang disebut, bukan hasil penempatan ke repo aplikasi.

Penyimpanan input audit.2 pada reproduction_inputs dan salinannya di dalam arsip provenance adalah pengulangan historis yang disengaja: replay mandiri dan preservasi bukti asal. Paket kanonik tidak mengandung duplikat file identik. Bundle ini tidak menambahkan archive/report sebagai authority baru.

## Pemeriksaan yang dapat diulang

Gunakan Python 3.12.14 dan zlib 1.3.2 untuk reproduksi byte yang telah dibuktikan. Verifikasi bundle dengan perintah berikut dari direktori ekstraknya, menggunakan path ZIP bundle yang sebenarnya:

```bash
python3 build_tools/verify_handoff_bundle.py /path/to/MicroTix-Build-Handoff-Bundle-v2_1-build_1.zip
python3 build_tools/reproduce_build.py
```

Reproducer memverifikasi input audit.2, bekerja di temporary directory baru, menjalankan transformasi dokumentasi dan memeriksa hash hasil. Ia tidak memakai jaringan, kredensial atau aplikasi. Script penghasil laporan lain disertakan untuk provenance; hanya driver `reproduce_build.py` yang menjadi entry point rekonstruksi portable dan dibuktikan menghasilkan ZIP kanonik identik. Jangan menjalankan script lama `bootstrap_docs.sh` dari arsip mana pun.

Setelah mengekstrak ZIP kanonik ke direktori baru yang hanya berisi payload paket, jalankan dari root paket tersebut:

```bash
python3 tools/verify_repository_v2_1.py --root .
python3 tools/validate_execution_docs_v2_1.py --root .
python3 tools/task_context_v2_1.py --root . --task TK-001
```

Verifier strict menolak file tambahan, termasuk metadata Git atau output pemeriksaan yang disimpan ke dalam paket sumber. Jalankan terhadap salinan kanonik immutable. Simpan evidence baru di luarnya. G0–G5 memerlukan bukti implementasi/runtime sesuai scope; hasil statis ini tidak mengubah gate operasional menjadi PASS.

Commit sumber lokal: `bb94636ba07e812f8d3b96e077c5881b1e648fe5`. Tidak ada push atau deployment. Perubahan payload berikutnya wajib memakai revisi baru, menyinkronkan projection, dan mengulangi seal order.
