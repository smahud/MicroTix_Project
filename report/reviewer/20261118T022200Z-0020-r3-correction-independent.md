# Reviewer independen — koreksi R3 task0020 (read-only)

## 1. Identitas review

| Field | Nilai |
|---|---|
| Peran | Reviewer independen internal (CONTRACT §5; review executor — **bukan** acceptance controller) |
| Metode | Read-only: laporan controller R3, diff working tree, source engine/services/handlers, file tes baru, log bukti executor; **tidak menjalankan tes/runtime apa pun** |
| Obyek | Branch `session/2026-11-18-0020-r3-correction` @ `05d268d` + working tree (koreksi REV-1711-01/04/05 + REV-1811-01) |
| Instruksi yang dinilai | [Controller R3 changes_requested](../controller/20261117T212042Z-0020-r3-review.md) pada main `4b03efe` |
| Batas | Verdict CLOSED/PARTIAL di bawah adalah analisis source; bukti eksekusi dibaca dari log executor, tidak direproduksi sendiri |

## 2. Verdict per temuan controller R3

| Temuan | Verdict | Inti alasan (path:baris tree koreksi) |
|---|---|---|
| **REV-1711-01 (P1)** | **CLOSED** | `_fenced` (engine.py:166-184) menambah `lease_expires_at__gt` → heartbeat (:186-192)/progress (:203-220) tidak bisa menghidupkan lease mati; `_fenced_update` (:439-454) menutup seluruh CAS transisi/terminal run_claimed; commit sukses terminal (:944-952) dan `_verify_only` (:1299-1311) wajib lease berlaku. Kontrol lain (watchdog bersyarat R2 :640-652, `guard_commit` :259-272, `scope()` :279-298) tetap utuh. |
| **REV-1711-04 (P1)** | **PARTIAL (cukup untuk scope probe)** | Registry in-proses `_INFLIGHT_ATTEMPTS` (:60-79) mendaftar attempt `run_claimed` dari awal (:701-705) sampai `finally` (:962-971); `resolve_uncertain(applied=False)` menolak job sama saat attempt hidup (:1210-1218, **sebelum** cek advisory lock :1219) → probe R3 lulus (sends 1, `resolve_rejected` terisi). Residual lintas-proses: lihat REV-R3C-01. |
| **REV-1711-05 (P1)** | **CLOSED** | `finalize_verification`: `authority_guard()` dipanggil DI BAWAH `SELECT FOR UPDATE` baris enrollment (services.py:1284-1307) sebelum `Router.objects.create` :1308, update enrollment :1322, pemasangan kredensial :1341-1350; guard = lambda `check_current_authority` segar (handlers.py:90) → revoke yang ter-commit selama tunggu kunci terlihat (READ COMMITTED per-statement) → rollback unit. Entry call R2 (:1275-1276) dipertahankan. |
| **REV-1811-01 (P2)** | **CLOSED** | `from domains.jobs.engine import JobError` (services.py:42); tanpa shadowing `ApiError`/nama lain; tanpa circular import (engine meng-import `domains.network.models` hanya di dalam fungsi :519/:599); raise ter-tipe `enrollment_state` retryable=False (:1293-1297) → FAILED definitif, bukan internal_error/uncertain. |

## 3. Temuan baru reviewer

| ID | Severity | Temuan | Status penanganan executor |
|---|---|---|---|
| **REV-R3C-01** | P2 (laten) | Proteksi old-writer `resolve_uncertain(applied=False)` hanya per-PROSES: deployment nyata multi-proses (runworker vs API/ops) tidak terlindungi saat sesi DB penulis mati namun adapter masih hidup — lock advisory lepas bersama sesi, registry proses lain kosong → requeue job sama dimungkinkan. `resolve_uncertain` hari ini **tidak punya pemanggil produksi** (grep: hanya tes) — paparan laten. | **DIDOKUMENTASIKAN, tidak diubah pada sesi ini — konflik material dengan tes R1 beku.** Analisis: (1) `tests/integration/test_jobs_lifecycle_pa002.py::test_resolve_not_applied_refused_while_old_writer_active` (REV-2011-03, frozen dalam histori suite) memakai job **router + error_code `lease_expired`** dan SETELAH penulis in-proses selesai mensyaratkan `resolve_uncertain(applied=False)` → RETRY_WAIT; guard durable berbasis state DB (router+lease_expired → tolak/recovery) akan mematahkan tes itu dan jalur R1 yang di-accept. (2) State DB identik (UNCERTAIN, lease_expired, router, lock advisory bebas) TIDAK MEMBEDAKAN "penulis in-proses selesai" dari "penulis lintas-proses mati sesinya, adapter hidup" — tanpa bukti terminasi yang dapat diamati engine, penutupan otomatis akan memalsukan bukti. (3) Perkakas bukti terminasi lintas-proses (marker durable baru) = perubahan model/migrasi di luar "minimum source changes" R3. Next step konkret: saat jalur ops/API resolve pertama kali dibangun (task scheduler/ops), wajib parameter bukti terminasi operator eksplisit (atau marker attempt durable) sebelum `applied=False` membuka requeue job ber-`router_id`; lihat catatan batas pada `engine.py:60-71` dan laporan eksekusi §6. |
| **REV-R3C-02** | P3 | `_retry_no_effect` step-1/step-2 CAS tanpa klausa lease-validity (engine.py:1054-1081) — konsistensi literal batas transisi. | **DIDOKUMENTASIKAN, tidak diubah.** Rationale: jalur hanya dicapai via deklarasi `no_effect` eksplisit handler yang di-accept R2 (REV-1711-02); step-1 menulis `lease_token=None, lease_expires_at=None` (tidak memperpanjang/menghidupkan lease) dan menarget state `uncertain` — identik dengan hasil reconciler atas lease yang sama; bukan resureksi/terminal palsu. Menambah klausa justru mengubah jalur REV-1711-02 yang di-accept tanpa probe pengganti. |

## 4. Analisis keamanan (a)–(g)

- **(a) renewal lease-valid tetap sah**: klausa lolos untuk lease berlaku — kontrol positif `test_jobs_r3_residuals.py` + probe positif `r3-cross-initial-expiry` (watchdog memperbarui lease melewati expiry awal) lulus.
- **(b) reconciler tetap berfungsi**: `reconcile_expired_leases` (:1137-1190) tidak diubah, CAS `token+state+lease_expires_at__lt=now` komplementer dengan gate worker `__gt`; probe R3 memakai `reconcile_expired_leases()==1` dan lulus.
- **(c) applied=True/None tidak terpengaruh negatif**: cek in-flight hanya cabang `applied is False` (:1211); applied=True memberi lease baru pemanggil (CAS epoch+1) + `_verify_only` watchdog; applied=None → RECOVERY_REQUIRED tanpa perubahan.
- **(d) job BERBEDA tetap berfungsi**: registry key per job-id; tanpa attempt in-flight → `acquire_router_sender` + requeue epoch-fence (tes baru + frozen R2 different-job lulus).
- **(e) double-call authority_guard aman**: entry call dipertahankan (frozen r1/r2 authority 4+7/3+3 lulus — perilaku R2 tak berubah); guard read-only idempoten; call bawah-kunci hanya menambah penolakan saat authority berubah selama tunggu.
- **(f) import JobError tanpa konflik**: hanya 2 kemunculan di services.py (import :42, raise :1293); `ApiError` envelope tidak tertimpa; import graph tanpa siklus.
- **(g) deadlock/regresi baru tidak ditemukan**: urutan lock konsisten enrollment → job (finalize: FOR UPDATE enrollment :1284 → commit_guard FOR UPDATE job :1355; arah sama dengan unit handler); guard bawah-kunci read-only; dua finalize konkuren terserialisasi baris enrollment (probe duplicate lulus bounded); `_INFLIGHT_LOCK` operasi set mikro tanpa I/O; `finally` discard dibungkus try/except.

## 5. Kejujuran tes baru (`backend/tests/integration/test_jobs_r3_residuals.py`, 5 tes)

Jujur, tidak melemahkan: tiap tes kontrol positif dulu (lease valid → renewal/transisi sah) lalu negatif; assertion ketat (`==`, `pytest.raises`, jumlah Router eksplisit); tanpa skip/disable; tidak mengubah tes lain. `test_finalize_revalidates_authority_under_enrollment_lock` memakai lock baris enrollment nyata + thread nyata + urutan teramati (Router 0 selama tunggu; guard ke-2 hanya setelah kunci lepas). Catatan: tes in-flight memanipulasi `engine._INFLIGHT_ATTEMPTS` langsung (white-box pin mekanisme — end-to-end tetap dipegang probe controller); guard pada tes lock adalah perekam no-op (revoke nyata tercakup probe controller). Dapat diterima; tidak ada pemalsuan hasil.

## 6. Batas keyakinan

1. Read-only — semua hasil eksekusi (589 passed, 7/7 probe R3, frozen 4+7/3+3, check/makemigrations/docs) dibaca dari log executor `report/executor-evidence/20261118T000000Z-0020-r3-correction/`, tidak direproduksi.
2. Analisis lintas-proses REV-R3C-01 berbasis pembacaan kode/model proses — tidak terobservasi runtime oleh sesi ini.
3. Environment executor: Python 3.13.5, Django 5.2.19, pytest 8.4.2, psycopg 3.2.13, PostgreSQL 17.11; full-suite 589/0 skip vs 583+1 skip controller — selisih konsisten kehadiran binary FreeRADIUS di sandbox executor (tes `skipif` berjalan); paritas environment tidak dinilai.
4. Tidak menilai publikasi/CI eksternal (PR/SHA) maupun NOT_RUN controller (install/upgrade/restore, systemd, RouterOS/GNS3, RADIUS nyata, browser E2E, skala) — batas itu tetap berlaku.
5. Lingkup diff minimum: 2 file sumber (+83/−4) + 1 file tes baru + bukti; tanpa perubahan probe beku/CONTRACT/migrasi/file terproteksi.
