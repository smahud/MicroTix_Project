# LATEST_HANDOFF — Kanonis (sesi 2026-11-11: PA-001 integritas alokasi pembayaran)

Diperbarui atomik SETELAH verifikasi sesi. Dokumen ini adalah titik masuk
WAJIB agent berikutnya (CONTRACT.md §10; dokumen handoff lain di
docs/AGENT_HANDOFF.md tetap sebagai panduan alur — perbarui statusnya,
jangan duplikasi laporan penuh).

## 1. Status kanonis SAAT INI

| Item | Nilai |
|---|---|
| **Branch kanonis** | `main` @ **`16085f825fef25ee4112d74b729c57e623b0bb05`** (clean; diverifikasi fetch/clone 2026-11-11; CI main pada SHA itu **success** — diverifikasi via API check-runs) |
| **PR sesi ini** | **#9 OPEN** (`session/2026-11-11-pa001-payment-concurrency` → main; PA-001 P0 — lihat §2; menunggu review controller, BUKAN siap merge otomatis) |
| PR lain terbuka | **#7** SSTP Phase-2 (head `d7fa35e`; CI **failure** — belum diinvestigasi sesi ini) · **#8** docs planning-audit (head `6bb57c9`; CI **failure** job docs — pola manifest belum refresh = pekerjaan DEC-02, belum ditugaskan) |
| Rilis kandidat | `v0.1.0-beta.1` tetap **NOT_READY** — penahan tetap Gate A/G (host Debian 13 nyata), BUKAN pekerjaan kode |
| CONTRACT.md | Versi `1fff190` (tidak diubah sesi ini) |
| Prioritas aktif | **Mandat master prompt user 2026-11-10 (sandbox terlebih dahulu)**: PA-001 P0 SELESAI di sandbox + PR #9; urutan berikutnya menunggu verdict review controller |

## 2. Yang diselesaikan + diverifikasi sesi ini (bukti nyata)

**PA-001 (P0) — "dua payment berbeda dapat memakai invoice balance stale"** (base
`16085f8`, bersih):

1. **Root cause diverifikasi pada SHA aktual**: `backend/domains/billing/services.py::
   _parse_allocations` membaca invoice tanpa kunci; `verify_payment` menulis
   read-modify-write Python dari snapshot basi; kunci hanya pada baris payment.
   Reproduksi dua koneksi PostgreSQL nyata (PID beda, diverifikasi
   `pg_backend_pid`): kedua verifikasi "ok", `paid=200.000` ≠ SUM alokasi
   `400.000` pada invoice total `300.000` → lost update + over-alocation terbukti.
2. **Perbaikan smallest change (+17/−4, satu fungsi)**: `select_for_update()` pada
   baris invoice dalam urutan id deterministik; sisa tagihan dibaca dari baris
   terkunci; tanpa migrasi skema; seluruh pemanggil existing sudah dalam transaksi
   `tenant_scope`. Alternatif ditolak + alasannya dicatat (CHECK constraint DB
   ditunda ke packet hardening skema; F() redundan; nowait+retry mengubah semantik).
3. **Tes regresi permanen** `tests/integration/test_billing_payment_concurrency.py`
   (4): over-allocation ditolak 409 bersih (pemenang lengkap allocation/receipt/
   audit/outbox; yang kalah nihil efek, payment tetap submitted); 100rb+200rb
   terkumpul penuh tanpa lost update; pasangan invoice urutan body dibalik tanpa
   deadlock + kwitansi unik; kegagalan alokasi multi-invoice rollback penuh.
   **Sensitivitas: 3/4 GAGAL pada kode lama, 4/4 hijau setelah perbaikan.**
4. **Verifikasi penuh** (PostgreSQL 17 nyata sandbox): backend **376/376** (+4;
   baseline base-SHA 372/372), `manage.py check` 0 issue, docs check PASS (22
   files). NOT_RUN jujur: FreeRADIUS daemon (bineri tak tersedia), frontend jobs
   (diff tidak menyentuh `apps/web`; CI PR memverifikasi), Playwright e2e,
   rehearsal installer (sandbox tanpa systemd/root — di luar scope PA-001).
   Laporan lengkap + transkrip: `report/orchestrator/
   20261111T060010Z-pa001-payment-allocation-concurrency.md`.

## 3. Bloker beta tetap (jujur — prasyarat eksternal, bukan kode)

| Bloker | Butuh |
|---|---|
| **Gate A/G** (penahan tunggal tag `v0.1.0-beta.1`) | Host Debian 13 nyata + root + `MT_DOMAIN` + DNS → `sudo bash instalasi.sh install` → `INSTALL_SUCCESS`; termasuk timer host `issue_due_invoices` (01:00) |
| **G1 lab MikroTik** (CHR/fisik) | Lab untuk T01/T16–T18/T20–T21 + bukti lab onboarding Phase-1 (lihat handoff 2026-11-07 §3); aktifkan `MT_ROUTEROS_ADAPTER=api_ssl`, cutover B3–B5 |
| **Lab GNS3 API-driven** (CONTRACT §7) | Infrastruktur GNS3 + image CHR berlisensi; harness reproducible + profil topologi |

## 4. Cabang kerja

- `session/2026-11-11-pa001-payment-concurrency` — sesi ini (**PR #9 OPEN**; code
  commit `a9eca6c` + docs commit handoff ini; SHA head PR diverifikasi via API
  setelah push).
- Terbuka milik pihak lain (JANGAN ditimpa): `docs/planning-audit-20261110` (PR #8),
  `session/2026-11-07-sstp-phase2` (PR #7).
- Arsip riwayat (remote, tidak diubah): `parallel/beta-be2` (unmerged),
  `integration/beta-0.1`, `session/2026-11-06/07-*`.

## 5. Prioritas eksekusi berikutnya (urut — menunggu verdict review PR #9)

1. **Review PR #9** (controller): diff + bukti §2 → ACCEPTED FOR NEXT SANDBOX STEP /
   REQUEST CHANGES; koreksi kembali ke executor.
2. **PA-002 (P1)** — job fencing/transaksi panjang (kandidat packet berikutnya sesuai
   tabel prioritas master prompt; terkait risiko tersisa PA-001: penahan kunci baris
   selama render kwitansi PDF).
3. **DEC-02** — PR #8 docs/manifest (CI failure job docs; branch itu pemilik file —
   jaga ownership disjoint), atau penugasan ulang eksplisit dari controller.
4. **PR #7 disposition** (SSTP Phase-2; CI failure perlu diinvestigasi packet terpisah).
5. **Ops host Gate A/G saat host tersedia** (penahan beta tunggal).

## 6. Titik mulai EKSAK agent berikutnya

```bash
git fetch origin --prune
git switch main && git pull --ff-only        # main @ 16085f8 (lihat §1)
git log --oneline -5
# Kandidat PA-001 untuk review (jangan merge tanpa verdict controller):
git fetch origin session/2026-11-11-pa001-payment-concurrency
git diff main...origin/session/2026-11-11-pa001-payment-concurrency
# Sandbox uji (PostgreSQL 17 user-space + Python 3.13; tanpa systemd di sandbox z.ai):
bash docs/tools/setup_env.sh                # atau initdb/pg_ctl manual port 55432
cd backend && bash scripts/dev_bootstrap.sh
MT_ENV=test .venv/bin/python -m pytest tests -q   # 376 tes (PostgreSQL nyata)
python3 docs/tools/check_docs.py
```

Lingkungan sandbox z.ai saat ini (jika sesi lanjut memakai sandbox sama): PG 17.5
user-space `/tmp/pgbin/pg17` aktif di port 55432 (cluster `backend/pgdata`; bila
proses mati karena daur ulang sandbox: `LD_LIBRARY_PATH=/tmp/pgbin/pg17/lib
/tmp/pgbin/pg17/bin/pg_ctl -D pgdata -o "-p 55432 -k $PWD/pgrun -h 127.0.0.1
-c listen_addresses=127.0.0.1" -l pgdata/server.log start`); venv `backend/.venv`
Python 3.13.5 dengan dependensi pinned terpasang; binari freeradius TIDAK tersedia
(1 tes radius-config SKIP wajar; `scripts/test_radius.sh` NOT_RUN).

## 7. Risiko & keterbatasan yang diketahui

- **Daur ulang sandbox platform menghapus `/home/z/my-project`** — pekerjaan PA-001
  SUDAH di-push (PR #9); sisa artefak sandbox dapat dibangun ulang via §6.
- Penahan kunci baris invoice selama transaksi verifikasi (termasuk render PDF
  kwitansi) — kelas penahan sama dengan kunci tenant yang sudah ada; pemindahan I/O
  keluar transaksi = lingkup **PA-002** (bukan diperluas di packet PA-001).
- Tes konkurensi PA-001 di level service (bukan HTTP multi-request; DRF test client
  tidak thread-safe); idempotency/principal scope HTTP = **PA-006**.
- Mutasi router tetap jalur simulator (capability.source=simulator) — tidak ada
  klaim perangkat nyata (G1). Gap G1 dan daftar lengkap risiko lama: handoff
  2026-11-07 §7 (masih berlaku).
- Kapasitas 1.000 tenant × 1.000 online tetap klaim desain, bukan benchmark.
- xhtml2pdf 0.2.28 dipin — pantau advisori keamanan.
- **PAT GitHub hanya di konfigurasi remote sandbox (tidak pernah di-commit; scan
  diff bersih). Rotasi PAT tetap disarankan** karena pernah melewati kanal chat.
