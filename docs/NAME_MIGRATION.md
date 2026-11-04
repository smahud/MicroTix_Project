# Migrasi identitas MicroTix

Mandat pemilik: seluruh nama proyek/aplikasi menjadi MicroTix; repo MicroTix_Project; seluruh payload dokumentasi berada di docs/. Revisi 2.1-microtix.1 mengganti nama dan path produk. Ini merupakan derivasi baru; checksum paket sebelumnya tidak digunakan untuk memvalidasi byte baru.

Kontrak branding pada branding.json dan README root adalah amendemen eksplisit untuk nama produk. Keputusan bisnis lain dan blocker keamanan tetap berlaku. Nama tampilan dapat berubah tanpa mengubah ID internal atau migrasi data. Dokumentasi historis yang direlabel tidak dianggap sebagai bukti integritas pascamigrasi. Validator paket lama memiliki asumsi paket dan source hash sebelum migrasi; jangan gunakan hasil lamanya sebagai PASS untuk repository baru. Inventory repository dihitung ulang dari byte aktual.
