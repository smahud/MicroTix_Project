# Mulai build MicroTix — 2.1-build.1

Paket ini memuat dokumentasi, bukan aplikasi. Mandat saat penyusunan hanya Mode A. Mulai implementasi setelah pemilik memberi workspace dan scope Mode C; jangan akses server/GNS3/produksi dari mandat lokal.

1. Dari akar paket, jalankan `python3 tools/verify_repository_v2_1.py --root .` dan `python3 tools/validate_execution_docs_v2_1.py --root .`. Keduanya hanya pemeriksaan dokumen.
2. Baca AGENTS, master §0–2/§24, lalu `sumber/audit/Unresolved_Issues_v2_1.md`. Pilih TK paling awal dengan dependency lengkap di task-contracts_v2_1.json. Gunakan `python3 tools/task_context_v2_1.py --root . --task TK-001` untuk reading map; tidak perlu memuat semua laporan/case.
3. Verifikasi seluruh source sebelum penempatan target; manifest adalah mapping aktif. Preserve baseline, branch terisolasi, conflict jika target berbeda. Jangan menjalankan bootstrap_docs.sh.
4. Kerjakan objective/allowed paths/acceptance task. Prasyarat kode/fixture dibangun oleh TK upstream; fakta/grant/perangkat tidak dikarang. SEC-DEC-01 menahan final policy/auth security gate; OLT menunggu model nyata. Lanjutkan task independen.
5. Jalankan test applicable hanya dalam profil sah, kumpulkan actual+cleanup. Claude implement → automated test → Codex review → Claude fix → revalidate, maksimum3 putaran dengan temuan actionable. Review berbeda dari author; mock bukan proof perangkat.
6. Checkpoint: task/milestone, commit+diff, perintah+exit, assertion actual, blocker tepat, dependency berikut, fitur produksi tetap nonaktif. Jangan menyebut build siap produksi hanya karena dokumen/CI statis lulus.

Prompt handoff setelah mandat tersedia: “Baca START_BUILD dan AGENTS. Verifikasi paket dan mandate workspace. Eksekusi DAG task dalam scope yang sah, mulai TK-001. Bekukan config/test applicability. Selesaikan pekerjaan independen; hentikan hanya task bergantung blocker. Jangan ubah keputusan sumber atau naikkan hak operasi. Serahkan diff dan evidence kepada Codex untuk review, maksimal3 putaran per task. Laporkan hasil terminal berscope.”
