# Lab GNS3 MicroTix — profil minimal Phase-2 (konektivitas router aman)

Status: **IMPLEMENTED (berkas) — BELUM VERIFIED_LAB**. Harness ini belum
dijalankan terhadap controller GNS3 sungguhan (aset CHR berlisensi + host
lab belum tersedia di sesi ini; CONTRACT.md §7/§9: jangan klaim verified_lab
tanpa bukti). Semua berkas di sini disiapkan agar eksekusi lab reproduktif
saat prasyarat tersedia.

## Tujuan (master directive "Secure Router Connectivity")

1. **Bukti lab G1 onboarding** — sintaks skrip bootstrap pada CHR NYATA
   (WireGuard v7; SSTP v6+v7), impor CA + `verify-server-certificate=yes`,
   handshake/enroll nyata, dan dua tenant dengan **LAN tumpang tindih**
   (192.168.88.0/24) tetap terisolasi.
2. **Reproduksibilitas** — topologi deklaratif (`topology-phase2.yaml`) +
   provisioner API-driven (`provision.py`) + daftar bukti terukur
   (`evidence-checklist.md`); teardown aman dan berulang.

## Prasyarat (di luar repo — tidak didistribusikan)

| Item | Catatan |
|---|---|
| Controller GNS3 (v2/v3) | URL + autentikasi dari ops; family API dideteksi dari endpoint `/version` (docs/OPERATIONS.md — jangan menambah prefix /v2 secara buta) |
| Template node CHR MikroTik | **Image CHR berlisensi dari sumber resmi MikroTik** — TIDAK didistribusikan repo ini (CONTRACT.md §7; tanpa hak redistribusi). Lisensi CHR free-tier memadai untuk uji manajemen. |
| Template node klien | Alpine/Debian cloud-init atau VPCS sesuai template controller |
| Host lab | Terisolasi dari produksi; jaringan lab ≠ jaringan pelanggan; budget CPU/RAM/disk + scope cleanup per OPERATIONS.md |
| Gateway MicroTix | Instalasi Debian 13 via `instalasi.sh` (lab host terpisah) dengan `MT_DOMAIN` + DNS lab; `MT_ENABLE_SSTP=1` setelah `backend/scripts/build_accel_ppp.sh` |

## Isi direktori

- `topology-phase2.yaml` — topologi deklaratif dua tahap:
  - **Tahap A**: gw (MicroTix) + `chr-a` (tenant A) + `client-a`.
  - **Tahap B**: + `chr-b` + `client-b` (tenant B, **LAN sama 192.168.88.0/24**
    dengan tenant A — uji isolasi manajemen plane §7; perhatikan: overlap LAN
    pelanggan TIDAK memengaruhi tunnel IP /32 yang unik global).
- `provision.py` — provisioner GNS3 API (Python stdlib; tanpa dependensi
  baru): deteksi family API dari `/version`, buat project + node dari template
  + tautan sesuai YAML; idempoten berdasarkan nama project; `--cleanup` hanya
  menghapus milik run ini (prefix nama) — sesuai OPERATIONS.md.
- `evidence-checklist.md` — peta item bukti G1 → langkah konkret → artefak
  yang disimpan (log/capture/JSON) → kriteria lulus.

## Eksekusi (ringkas)

```bash
# 1) Gateway MicroTix pada host lab (terpisah): instalasi + SSTP aktif
sudo bash backend/scripts/build_accel_ppp.sh
MT_DOMAIN=lab-gw.microtix.test MT_ENABLE_SSTP=1 sudo bash instalasi.sh install

# 2) Provision topologi (controller + template disiapkan ops lab)
python3 lab/provision.py --controller http://127.0.0.1:3080 \
  --topology lab/topology-phase2.yaml --stage A --project microtix-phase2-a

# 3) Enrollment via UI nyata (tenant A: chr-a WireGuard v7; tahap B: chr-b
#    SSTP v6.49) — ikuti evidence-checklist.md untuk setiap bukti.

# 4) Teardown (hanya milik run ini)
python3 lab/provision.py --controller http://127.0.0.1:3080 \
  --project microtix-phase2-a --cleanup
```

## Kejujuran bukti

- Hasil lab dicatat sebagai `VERIFIED_LAB` hanya bila checklist terpenuhi
  dengan artefak nyata (log + output perintah) — bukan karena skrip exit 0.
- Simulator (adapter `simulator`) TIDAK PERNAH dipakai sebagai bukti
  konektivitas perangkat nyata (kebijakan sejak Phase-1).
- Bila aset belum tersedia: status tetap BLOCKED untuk item terkait; kode/tes
  independen tetap berjalan (CONTRACT.md §6).
