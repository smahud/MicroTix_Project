# Independent source review — task0020 implementasi (concurrency/recovery + authority)

- **Author:** sub-agent reviewer independen GLM (delegasi orchestrator sesuai
  CONTRACT §5; prompt berisi tujuan, baseline, batas read-only, dan permintaan
  laporan terformat). Persist oleh orchestrator sesuai CONTRACT §10 karena
  sub-agent berjalan read-only tanpa akses tulis repository.
- **Report path:** `report/reviewer/20261117T010218Z-0020-job-lifecycle-independent.md`
- **Baseline:** `main@41d1f33f16508491a34f66b767830b9dd3e5954e` · **Kandidat saat review:** worktree `ea7b8a1` (branch `session/2026-11-17-0020-job-lifecycle-authority`)
- **Metode:** review source diff penuh `git diff 41d1f33 -- backend/` + file tes baru; penelusuran interleaving level kode; pemetaan ke acceptance J20-A01..A09 dan temuan sumber JS-0020-01..10. Review bersifat SOURCE-LEVEL — reviewer TIDAK menjalankan tes/runtime/PostgreSQL; klaim PASS executor tidak diverifikasi ulang.
- **Perubahan oleh reviewer:** tidak ada (read-only; tidak ada commit/push).
- **Publication:** bagian dari commit penyerahan executor di branch kandidat.

## Verdict: CHANGES_REQUESTED (pada saat review)

Implementasi menutup mayoritas defect JS-0020-01..10 secara substantif, tetapi
reviewer menemukan **satu defect P1** (duplikat efek logis lewat retry origin
saat kandidat uncertain — pelanggaran A04) dan tiga P2 (fence hasil
non-atomik; readback basi pada resolve; tanpa pembaruan lease untuk handler
panjang) yang perlu ditutup sebelum acceptance.

> **Catatan orchestrator (bukan bagian laporan reviewer):** seluruh temuan
> REV-2011-01..10 ditindaklanjuti pada penyerahan ini — 01..04 + 05..09
> diperbaikan di kode dengan tes baru (lihat matriks pada laporan eksekusi
> `report/orchestrator/20261117T010218Z-0020-job-lifecycle-authority_done.md`);
> REV-2011-10 ditutup sebagai runbook non-normatif di laporan eksekusi
> (menghindari perubahan manifest docs untuk file baru). Verdict di atas
> adalah penilaian reviewer terhadap KANDIDAT PRA-KOREKSI (`ea7b8a1`),
> dipertahankan apa adanya untuk audit.

## Temuan

### REV-2011-01 — P1: `retry_job` tidak menganggap kandidat `uncertain`/`recovery_required` sebagai aktif → duplikat efek logis dari outcome tak diketahui (pelanggaran A04)

- **Lokasi:** `backend/domains/jobs/engine.py` (retry_job, pintu masuk `backend/domains/jobs/views.py` JobRetryView)
- **Fakta kode:** `active_states` lama = {queued, claimed, preflight, waiting_dependency, retry_wait, executing, verifying}; `uncertain` dan `recovery_required` tidak termasuk padahal keduanya nonterminal dan uncertain berarti efek mungkin sudah terjadi.
- **Interleaving konkret (sekuensial):** origin FAILED+retryable → retry → kandidat Y → Y kirim efek lalu timeout → UNCERTAIN → operator retry origin LAGI → guard tidak cocok (Y uncertain) → job Z dibuat → Z mengeksekusi → efek dikirim lagi dari outcome yang belum diketahui.
- **Koreksi minimum:** masukkan uncertain/recovery_required ke active_states; tes failing-before/passing-after.

### REV-2011-02 — P2: commit hasil terminal read-then-write by-id, bukan CAS — window TOCTOU dapat menimpa keputusan reconcile/resolve (A01)

- **Lokasi:** `run_claimed` (blok hasil+SUCCEEDED) dan `_verify_only`
- **Fakta:** SELECT fresh lalu `Job.objects.filter(id=...).update(...)` tanpa filter lease di WHERE; `detail.save` by-pk. Reconcile worker lain dapat meng-commit UNCERTAIN tepat di antara SELECT dan UPDATE → terus ditimpa SUCCEEDED.
- **Koreksi minimum:** pindahkan guard ke klausa WHERE UPDATE (id+token+epoch+state=verifying) + rowcount.

### REV-2011-03 — P2: `resolve_uncertain(applied=False)` requeue tanpa membuktikan penulis lama berhenti — readback "belum diterapkan" bisa basi terhadap send in-flight (A03/A04)

- **Interleaving:** W1 pegang advisory lock mid-send → reconcile → UNCERTAIN → ops readback (command belum sampai) "belum diterapkan" → resolve(False) → requeue → W1 selesai send (efek TERJADI) → W2 acquire lock → resend → efek ganda.
- **Koreksi minimum:** wajib bukti penulis lama berhenti (advisory lock bebas) sebelum requeue; ops mengulang readback setelahnya.

### REV-2011-04 — P2: tidak ada pembaruan lease selama handler berjalan — job >30 detik pada deployment multi-worker dipaksa uncertain mid-run

- **Lokasi:** hanya `ctx.heartbeat()` sebelum execute/verify; `progress()` tidak memperpanjang lease; tidak ada handler produksi memanggil heartbeat; LEASE_S=30 vs backup.job_deadline_s=1800.
- **Konsekuensi:** reconcile worker lain menandai UNCERTAIN saat worker asli masih bekerja → hasil valid dibuang (CAS gagal) dan wajib intervensi ops.
- **Koreksi minimum:** perpanjang lease di `progress()` (fenced, di luar transaksi lain) dan/atau heartbeat per fase handler.

### REV-2011-05 — P3: jalur CAS menulis transisi di luar tabel state §6

- Contoh: claimed→recovery_required (authority gagal pra-preflight); verifying→retry_wait (error retryable fase verify); claimed/preflight→queued langsung pada reconcile (seharusnya via retry_wait).
- **Koreksi minimum:** rutekan melalui transisi tabel sah.

### REV-2011-06 — P3: race signal runworker — exit-3 palsu saat idle (alarm dipasang saat tidak ada job aktif) dan klaim setelah stop

- **Koreksi minimum:** pasang timer drain hanya saat job aktif; sleep yang dapat dibangunkan sinyal.

### REV-2011-07 — P3: authority hanya diperiksa sekali per job (sebelum preflight), bukan per efek/chunk sensitif

- Cutover B0→B5 beruntun dalam satu execute; backup panjang (deadline 1800 s) juga.
- **Koreksi minimum:** recheck murah pada batas kirim berikutnya.

### REV-2011-08 — P3: default fail-open untuk kind produksi tanpa entri peta izin

- `authority_requirement()` → None membuat engine/view skip cek izin; kind baru yang lupa dipetakan diam-diam tanpa pemeriksaan.
- **Koreksi minimum:** default deny untuk kind non-`_test` tak terpetakan.

### REV-2011-09 — P3: jalur drain pre-effect (`drained_before_effect`) tidak teruji

- **Koreksi minimum:** tes engine-level stop_check → RETRY_WAIT + drained_before_effect + nol efek + requeue menuntaskan.

### REV-2011-10 — P3: runbook drain tidak ada sebagai dokumen

- A08 mensyaratkan runbook urutan stop-claims→drain/stop old writers→reconcile/readback→resume; saat review hanya ada di docstring runworker.

## Catatan minor (P3, digabung)

- `run_claimed(..., now=None)` param assigned-unused (sisa JS-0020-07).
- `return _hold_for_drain(...)` dead return (fungsi selalu raise).
- Assert lemah `or` pada tes stale-after-transfer.
- Job uncertain hasil `_finish_execute_failure` mempertahankan lease_token lama.

## Yang sudah benar (ringkas, verifikasi source reviewer)

- A01 fencing pada seluruh jalur tulisan worker via `_fenced_update`/`JobContext._fenced` (kecuali commit hasil — REV-2011-02); OwnershipLost menghentikan efek; heartbeat/progress melaporkan kehilangan; terminal tak tertimpa.
- A03: `effect_state=maybe` atomik dengan entering EXECUTING; cancel hanya pre-effect via CAS + epoch bump; executing/verifying jujur 409; advisory lock per-router non-blocking, dilepas `finally`, mati otomatis bersama sesi; router lain mandiri.
- A05: reconcile state/effect-aware + CAS (tidak menimpa lease hidup/hasil/cancel), idempotent; resolve False→retry_wait+epoch bump, True→verify tanpa resend, None→tertahan.
- A02: `run_claimed` tanpa scope luar; handler memisahkan unit `ctx.scope()` dari I/O adapter; fail-closed antar unit.
- A06/A07: authority fresh-DB; aktor non-aktif denied; actorless karantina; verify_api_ssl provenance enrollment.created_by; router_scope; 404/403; step-up sensitif; RouterReplaceView routers.release; handler hilang/verifier negatif fail-closed.
- A08: drain proses nyata SIGTERM/SIGINT/SIGKILL + exit code 0/3 + pemulihan reconcile.
- A09: tanpa migrasi schema; legacy actorless karantina + resume; R5 dikeraskan sesuai REV-1611-TEST-01.

## Pemetaan penutupan JS-0020 (versi reviewer, pra-koreksi)

| Temuan sumber | Status kandidat pra-koreksi |
|---|---|
| JS-0020-01 transaksi melintasi I/O | Tertutup |
| JS-0020-02 stale write | Tertutup kecuali commit hasil → REV-2011-02 |
| JS-0020-03 false cancel | Tertutup |
| JS-0020-04 recovery awal/race | Tertutup (+ nit REV-2011-05) |
| JS-0020-05 uncertain blind retry | Tertutup di jalur uncertain; bocor via retry origin → REV-2011-01; readback basi → REV-2011-03 |
| JS-0020-06 per-router sender | Tertutup (+ residual REV-2011-03) |
| JS-0020-07 drain/deadline/heartbeat | Drain+deadline tertutup; renewal lease belum → REV-2011-04 |
| JS-0020-08 authority recheck | Tertutup pre-effect (+ REV-2011-07 per-chunk) |
| JS-0020-09 authority retry/cancel/replace | Tertutup (+ REV-2011-08 default) |
| JS-0020-10 handler/verifier fail-closed | Tertutup |

## Batas keyakinan

1. Review source-level: tidak ada eksekusi runtime/race/proses oleh reviewer; klaim PASS berasal dari log executor.
2. Analisis interleaving diturunkan dari semantik PostgreSQL READ COMMITTED dan urutan statement; probabilitas REV-2011-02 rendah (window sub-ms) namun invariant-nya eksplisit diminta packet.
3. Efek ganda REV-2011-01/03 bergantung kind: sebagian handler ber-dedup desired-state; backup_router dan discover_router tidak.
4. Perilaku adapter API-SSL nyata tidak diverifikasi (mutasi masih lab-gated); kesimpulan fencing pada level DB/advisory-lock/simulator.
5. Reviewer tidak menilai frontend/CI/docs tooling/installer.

**Rekomendasi reviewer:** koreksi REV-2011-01..04 wajib (failing-before/passing-after), 05..10 boleh diikutsertakan/ditunda dengan catatan; regresi PA-001/PA-006 + suite penuh pada SHA baru sebelum acceptance.
