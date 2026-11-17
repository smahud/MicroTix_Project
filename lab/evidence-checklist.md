# Checklist bukti lab G1 — onboarding router aman (Phase-1 + Phase-2 SSTP)

Status: **RENCANA EKSEKUSI LAB — BELUM DIJALANKAN** (aset CHR/controller
belum tersedia; lihat lab/README.md). Setiap item lulus HANYA bila artefak
nyata disimpan; simulator tidak pernah menjadi bukti (CONTRACT.md §9).

Konvensi bukti: simpan di luar repo (ruang bukti lab), catat pada
`docs/BETA_TEST_EVIDENCE.md` ringkas + tautan/SHA artefak. Perintah contoh
di bawah dijalankan pada CHR (Terminal) / host gateway (root) sesuai label.

## G1-WG — WireGuard (fase 1, chr-a v7)

| ID | Bukti | Langkah | Kriteria lulus |
|---|---|---|---|
| G1-WG-1 | Sintaks skrip v7 nyata | Enrollment tenant A (chr-a, wireguard, 7.15.3) → tempel skrip di Terminal CHR | Tidak ada error sintaks; `/interface wireguard print` menampilkan mtx-wg; `/interface wireguard peers print` menampilkan endpoint gateway publik |
| G1-WG-2 | Handshake nyata | Host gw: `wg show` | latest-handshakes untuk peer chr-a < 180 s; `probe_wg` JSON updated≥1 |
| G1-WG-3 | Callback + verifikasi nyata | Pantau wizard sampai "Siap" | `verification.source=api_ssl` (bukan simulator); probe TLS ke /32 berhasil; pin = fingerprint teramati |

## G1-SSTP — SSTP (fase 2, chr-a v7 + chr-b v6.49)

| ID | Bukti | Langkah | Kriteria lulus |
|---|---|---|---|
| G1-SSTP-1 | Sintaks skrip v7 nyata | Enrollment tenant A (chr-a, sstp, 7.15.3) | `authentication=mschap2`; `verify-server-certificate=yes` diterima; antarmuka mtx-sstp running |
| G1-SSTP-2 | Sintaks skrip v6.49 nyata (GAP: paritas field v6) | Enrollment tenant B (chr-b, sstp, 6.49.13) | Skrip berjalan tanpa error; catat apakah `verify-server-address-from-certificate` tersedia — bila tidak ada, laporkan sebagai temuan (skrip menunggu keputusan revisi) |
| G1-SSTP-3 | Sesi PPP nyata + audit | Host gw: `accel-cmd show sessions` (telnet 127.0.0.1:2000); `journalctl -u microtix-sstp` | Sesi username `mtx-<kode>-<suffix>` dengan IP /32 sesuai enrollment; log up/down tercatat |
| G1-SSTP-4 | TLS benar-benar diverifikasi (bukan dipasang gelap) | CHR: matikan SNI/ubah CA? uji negatif — hapus CA `MicroTix-CA` lalu reconnect | Koneksi DITOLAK (verifikasi sertifikat bekerja). Bukti negatif wajib. |
| G1-SSTP-5 | Isolasi kredensial | Coba kredensial tenant A dari chr-b | Auth GAGAL (username unik global per router; accel-ppp log auth-fail) |

## G1-ISO — isolasi dua tenant LAN sama (tahap B)

| ID | Bukti | Langkah | Kriteria lulus |
|---|---|---|---|
| G1-ISO-1 | LAN overlap tidak menjembatani | client-a: `ping 192.168.88.x` milik client-b (via internet gw? tidak — lokal saja) | TIDAK tercapai (LAN lokal independen; tidak ada rute lintas) |
| G1-ISO-2 | Peer→peer default deny | chr-a: `ping <tunnel_ip chr-b>` | TIDAK tercapai (host gw nftables deny peer→peer) |
| G1-ISO-3 | Router tidak capai DB/SSH/metadata | chr-a: coba TCP 5432/22/80/page metadata ke host gw | DITOLAK semua |
| G1-ISO-4 | API-SSL hanya dari /32 server | chr-b: coba akses API gw dari sumber lain | Hanya jalur via tunnel yang diterima rule `rtrw-mgmt-api` |

## G1-FETCH — gap fetch check-certificate (skrip v2, PROPOSED)

| ID | Bukti | Langkah | Kriteria lulus |
|---|---|---|---|
| G1-FETCH-1 | `/tool fetch check-certificate=yes` + SNTP | CHR: set NTP lab; fetch `https://<MT_DOMAIN>/api/v1/health/live` dengan check-certificate=yes | Fetch sukses pada v6.49 dan v7.15 → dasar mengaktifkan check-certificate pada skrip v2 (keputusan PROPOSED sesi Phase-1 dijalankan) |
| G1-FETCH-2 | Skrip v2 akun API-SSL platform | Jalankan skrip v2 (buat akun read-only platform di router) saat tersedia | Login API-SSL penuh via tunnel diverifikasi; pin dibandingkan |

## G1-REV — revoke

| ID | Bukti | Langkah | Kriteria lulus |
|---|---|---|---|
| G1-REV-1 | Lepas router mencabut akses | UI: lepaskan chr-a; render ulang: `manage.py render_sstp_config` | Akun chr-a TIDAK ada di chap-secrets; sesi aktif chr-a terputus (accel-ppp) |
| G1-REV-2 | Peer WG dicabut | `manage.py render_wg_config` + `wg show` | Peer chr-a tidak dirender; handshake berhenti |

## Setelah lulus

1. Perbarui `docs/BETA_TEST_EVIDENCE.md` (ringkas + artefak), `docs/progress.md`
   (status verified_lab per item), dan `report/LATEST_HANDOFF.md`.
2. Aktifkan `MT_ROUTEROS_ADAPTER=api_ssl` untuk jalur nyata; buka keputusan
   cutover B3–B5 (docs/AGENT_HANDOFF.md).
