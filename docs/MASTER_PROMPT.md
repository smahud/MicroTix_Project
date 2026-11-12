# MicroTix — master prompt default

Pilih peran sesi, lalu jalankan prompt tetap yang sesuai. Berlaku untuk sesi baru maupun resume; task, branch dan SHA aktual ditemukan dari repository, bukan disalin dari percakapan lama.

| Peran sesi | Prompt tetap | Hasil yang diserahkan |
|---|---|---|
| Coding agent / executor | [MASTER_PROMPT_EXECUTOR.md](MASTER_PROMPT_EXECUTOR.md) | Implementasi task eligible, tes nyata, execution report dan candidate PR |
| ChatGPT Work / controller reviewer | [MASTER_PROMPT_REVIEWER.md](MASTER_PROMPT_REVIEWER.md) | Review exact SHA, keputusan/koreksi terdokumentasi dan task berikutnya yang eligible |

Untuk memulai sesi executor, cukup instruksikan:

> Kerjakan MicroTix sesuai `docs/MASTER_PROMPT_EXECUTOR.md` pada repository `smahud/MicroTix_Project`. Temukan dan lanjutkan task eligible dari keadaan GitHub terbaru.

Untuk memulai sesi reviewer, cukup instruksikan:

> Review MicroTix sesuai `docs/MASTER_PROMPT_REVIEWER.md` pada repository `smahud/MicroTix_Project`. Periksa penyerahan terbaru, publikasikan keputusan dan siapkan kelanjutan yang eligible.

Keduanya masuk melalui [task/0000-start-here.md](../task/0000-start-here.md), tunduk pada [CONTRACT](../CONTRACT.md), dan memakai [LATEST_HANDOFF](../report/LATEST_HANDOFF.md) sebagai pointer status aktual. File ini dipertahankan sebagai alamat kompatibel untuk tautan lama, bukan prompt ketiga atau backlog baru. Prompt default dan panduan masuk tidak diberi `_done`; hanya packet eksekusi bernomor yang mengikuti completion rename.

Target tetap satu produk siap Production Beta dan lab GNS3 yang dapat direproduksi. [PRODUCT](PRODUCT.md), [ARCHITECTURE](ARCHITECTURE.md), dokumen domain dan [ACCEPTANCE](ACCEPTANCE.md) tetap memiliki kebutuhan/gates. Prompt tidak mengganti kontrak teknis, memperluas scope task, mengaktifkan fitur, atau memberi kewenangan rollout tambahan. File tidak menjalankan atau membangunkan agent secara otomatis.
