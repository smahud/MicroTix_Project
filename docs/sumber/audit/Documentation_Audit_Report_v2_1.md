# Documentation Audit Report — MicroTix v2.1

[REVISI AUD-46; CATATAN HISTORIS SOL] Audit sebelumnya dilakukan terhadap32berkas ZIP dan satu template onboarding. Ini audit dokumen, bukan penulisan kode aplikasi atau eksekusi server. Seluruh source dibaca; input integrity31/31cocok. Original ZIP SHA256 `ae643be87a746d97b966d534221e8d55dc45375e4c673f76cbc977c0d0dca140`; original onboarding SHA256 `7d494656126435a98ee336730d7ffe478e293f435d4f2aa821bf20813bd1a2dc`. Original v1.4terpisah tidak tersedia, sehingga13/13historis tidakdiverifikasiulang.

Severity di bawah menilai dampak bila rancangan lama diwujudkan; ini bukan klaim exploit runtime telah dibuktikan. Koreksi desain tidak sama bukti bug implementasi telah diperbaiki.

| ID | Severity | Temuan | Resolusi dokumentasi |
|---|---|---|---|
| AUD-01 | HIGH | Klausul locked/jangan ubah menghalangi koreksi yang diminta | Hierarchy amendemen dan anotasi; lihat kontrak v2.1 AUD-01 |
| AUD-02 | HIGH | SSOT dan salinan decisions dapat bercabang | Satu precedence dan log ADR; lihat kontrak v2.1 AUD-02 |
| AUD-03 | HIGH | ModeB/C, produksi dan mandat saling tumpang tindih | Mode orthogonal dan action grant; lihat kontrak v2.1 AUD-03 |
| AUD-04 | HIGH | One-shot menjanjikan fakta/izin yang belum ada | Terminal status, missing fields dan dependency; lihat kontrak v2.1 AUD-04 |
| AUD-05 | MEDIUM | Provenance historis diklaim telah diverifikasi ulang | 31/31 current terverifikasi; historis dibatasi; lihat kontrak v2.1 AUD-05 |
| AUD-06 | HIGH | Bootstrap fail-open pada missing/zero entries dan overwrite | Legacy tidak untuk eksekusi; kontrak pengganti fail-closed; lihat kontrak v2.1 AUD-06 |
| AUD-07 | MEDIUM | Dependency master prompt tidak disertakan | Kontrak self-contained dan versi pasangan; lihat kontrak v2.1 AUD-07 |
| AUD-08 | MEDIUM | Kuota agen/kolektor ambigu per jenis atau gabungan | Gabungan identity unik; harga/rekening dipertahankan; lihat kontrak v2.1 AUD-08 |
| AUD-09 | HIGH | Parameter tanpa tipe, scope, range atau deadline kind | Registry typed, units, immutable effective snapshot; lihat kontrak v2.1 AUD-09 |
| AUD-10 | HIGH | Kuota service plus reservation dihitung ganda | Himpunan identity dan consume atomik; lihat kontrak v2.1 AUD-10 |
| AUD-11 | HIGH | Batas hari ended/retensi/bonus anniversary ambigu | Half-open intervals dan anchor+offset eksplisit; lihat kontrak v2.1 AUD-11 |
| AUD-12 | HIGH | Identity/kind/credentialunknown/static relational scope tidak lengkap | Credential state, byte limit dan FK scoped; lihat kontrak v2.1 AUD-12 |
| AUD-13 | MEDIUM | HTTP409/422, cursor/clamp dan endpoint validate ambigu | Error deterministik dan endpoint tambahan; lihat kontrak v2.1 AUD-13 |
| AUD-14 | HIGH | Lease/retry/cancel tidak mempunyai transisi deterministik | State transitions, safe retry dan stale writer fence; lihat kontrak v2.1 AUD-14 |
| AUD-15 | HIGH | RLS/privilege/reveal/URL dan upload mempunyai pengecualian tidak jelas | Role boundary, TLS, runtime secret exceptions dan gateway; lihat kontrak v2.1 AUD-15 |
| AUD-16 | HIGH | Bootstrap mengubah global api-ssl walau klaim tidak menyentuh existing | Shared resource preflight; token TLS dan complete idempotent; lihat kontrak v2.1 AUD-16 |
| AUD-17 | HIGH | S1 bertentangan database-only; timer startup tidak memberi TTL24jam | Privilege operation terpisah dan absolute cleanup; lihat kontrak v2.1 AUD-17 |
| AUD-18 | MEDIUM | Merge password terjadi sebelum sumber password; rename seolah telah ke router | Structural candidate, reclassification dan DB-only semantics; lihat kontrak v2.1 AUD-18 |
| AUD-19 | CRITICAL | radcheck unik username menolak multiatribut; tenant dari input tidak tegas | Attribute uniqueness dan verified transport NAS; lihat kontrak v2.1 AUD-19 |
| AUD-20 | CRITICAL | SQL tenant filtering bertentangan FORCE RLS/pool context | Facade request transaction-scoped dan minimal roles; lihat kontrak v2.1 AUD-20 |
| AUD-21 | HIGH | read_clients dianggap live; dua proses disebut hostHA; CoA/PoD tidak dibatasi | NAS applied revision, rolling reconciliation dan RFC5176 baseline; lihat kontrak v2.1 AUD-21 |
| AUD-22 | CRITICAL | Canary tetap memakai akun lokal; PPP AAA dianggap per server | Canary tanpa shadow, global scope dan realtime observation; lihat kontrak v2.1 AUD-22 |
| AUD-23 | CRITICAL | Rollback mematikan RADIUS existing dan menghidupkan user/hold salah | Baseline restore dengan delta credential dan ownership/revision; lihat kontrak v2.1 AUD-23 |
| AUD-24 | CRITICAL | No interim60s dianggap bukti putus padahal interval300s | Positive session evidence dan valid policy Reject; lihat kontrak v2.1 AUD-24 |
| AUD-25 | HIGH | Restore memakai assertion Reject dan klaim akun online | Restore Accept; verified_active berbeda online; lihat kontrak v2.1 AUD-25 |
| AUD-26 | HIGH | Session identity/partisi/counter/late packet ambigu; stale dianggap Stop nyata | Session directory, monotonic deltas dan unknown; lihat kontrak v2.1 AUD-26 |
| AUD-27 | HIGH | COUNT radacct tidak mencegah dua login paralel | Strict admission reservation dan fail-closed unknown occupancy; lihat kontrak v2.1 AUD-27 |
| AUD-28 | HIGH | Edge diCHR, snapshot tanpa expiry dan global limit saat partition | Linux replica, signed revision/TTL dan explicit limitation; lihat kontrak v2.1 AUD-28 |
| AUD-29 | HIGH | full first period mengubah fixed_monthly menjadi anniversary | Policy per cycle dan due-day deterministic; lihat kontrak v2.1 AUD-29 |
| AUD-30 | CRITICAL | Satu invoice satuPayment menghapus transfer nyata; allocation/overpay salah | Dedup transfer source dan credit hanya selisih; lihat kontrak v2.1 AUD-30 |
| AUD-31 | CRITICAL | Ledger trigger mengizinkan INSERT line ke posted dan header kosong | Header/line bypass contract, privileges dan period locks; lihat kontrak v2.1 AUD-31 |
| AUD-32 | HIGH | Prepaidmemorandum disamakan piutang; refund/recognition dapat negatif | Recognized subledger dan funded/earned/tax rules; lihat kontrak v2.1 AUD-32 |
| AUD-33 | HIGH | Hash server dianggap checksum sumber; cleanup regex/file partial | Size+close+hash, exact cleanup dan retained catalog; lihat kontrak v2.1 AUD-33 |
| AUD-34 | HIGH | Retensi tier90/400 tidak terwujud otomatis diPrometheus15hari | Persistent aggregate store dan collector/accounting distinction; lihat kontrak v2.1 AUD-34 |
| AUD-35 | HIGH | RTO dimulai saat restore; RPO tidak memeriksa acknowledged money | Outage-to-full-ready dan source sequence reconciliation; lihat kontrak v2.1 AUD-35 |
| AUD-36 | HIGH | PortACS/NBI auth/claim secret/parameter path tidak tegas | HTTPS gateway, installed credential proof dan versioned mapping; lihat kontrak v2.1 AUD-36 |
| AUD-37 | CRITICAL | CPE password diubah sebelum RADIUS dapat memutus jalur verifikasi | Independent management/recovery profile dan uncertain state; lihat kontrak v2.1 AUD-37 |
| AUD-38 | MEDIUM | Menu paket hilang, permissionU19/copy conflict/active/succeeded keliru | SubrouteU04 dan context-appropriate copy/i18n snapshot; lihat kontrak v2.1 AUD-38 |
| AUD-39 | HIGH | Lab mengunci APIv2, PPPoEpakaiDHCP, WGrouteAAA/HA tidak lengkap | Typed inventory, protocol L2, exact routing dan resource ownership; lihat kontrak v2.1 AUD-39 |
| AUD-40 | HIGH | Klaim58/30; sebenarnya62matriks/35blocks/27missing+2naratif | Registry64child+20QA-SEC dengan spesifikasi lengkap; lihat kontrak v2.1 AUD-40 |
| AUD-41 | HIGH | ASVS5 memakai babversi4; WCAG baseline dijadikan usulan | MappingASVS5 dan klasifikasi standards benar; lihat kontrak v2.1 AUD-41 |
| AUD-42 | HIGH | Performance thresholds menggantung;500/s disebutribuan;sample tidak tegas | Load defaults, denominators, percentiles dan profile scope; lihat kontrak v2.1 AUD-42 |
| AUD-43 | HIGH | Evidence hash disebut signature dan selfreview disebut independent | Assertion mapping, statusdimensi dan factual reviewer; lihat kontrak v2.1 AUD-43 |
| AUD-44 | HIGH | RawPCAP/debug dapat membocorkan credential walau anonymized | Defaultoff, restricted rawTTL dan sanitized semantic evidence; lihat kontrak v2.1 AUD-44 |
| AUD-45 | HIGH | PDP deadline dan controller/prosessor blanket tidak lengkap | Pasal46 dan escalation serta role-specific processing; lihat kontrak v2.1 AUD-45 |
| AUD-46 | HIGH | All-pass desain tidak didukung oleh gap yang ditemukan | Cabut historical all-pass; laporkan statis versus runtime; lihat kontrak v2.1 AUD-46 |

## Batas hasil

Ledger, RADIUS, cutover, rotasi ACS dan jaringan membutuhkan implementasi serta pengujian actual. Tidak ada runtime test, compatibility claim, deploy, perubahan router, secret harvesting, benchmark, DR atau release flag yang dijalankan. Tidak ada sign-off profesional yang diada-adakan. Self-review dokumen bukan reviewer independen. Revisi memberi default teknis untuk menghilangkan keputusan rutin yang menggantung, tetapi target/izin/image/lisensi dan review actual tetap blocker bila tidak tersedia.

## Referensi primer dan batas pemeriksaan

- MikroTik RADIUS: https://manual.mikrotik.com/docs/authentication-authorization-accounting/radius/ — prioritas local match, incoming Disconnect dan port default; konfigurasi3799 adalah pilihan eksplisit proyek.
- MikroTik Fetch: https://manual.mikrotik.com/docs/cli-reference/tool/fetch/ ; SSH: https://manual.mikrotik.com/docs/management-tools/ssh/ — TLS/default Fetch dan host-key validation bergantung build, wajib capability actual.
- FreeRADIUS SQL readclients: https://networkradius.org/doc/current/raddb/mods-available/sql.html — startup client loading; lifecycle actual harus diuji pada pinned release.
- PostgreSQL17 RLS: https://www.postgresql.org/docs/17/ddl-rowsecurity.html — owner/BYPASSRLS, FORCE dan cakupan privilege; pengganti facade merupakan rancangan audit, belum implementasi teruji.
- GNS3 resmi: https://apiv3.gns3.net/ dan https://github.com/GNS3/gns3-server/discussions/1956 — family v2/v3 berbeda; tidak menyimpulkan server pemilik memakai v3.
- GenieACS API: https://docs.genieacs.com/en/stable/api-reference.html ; environment: https://docs.genieacs.com/en/stable/environment-variables.html ; source connection request: https://github.com/genieacs/genieacs/blob/master/lib/connection-request.ts — behavior actual tetap versi dipin.
- OWASP ASVS release resmi: https://github.com/OWASP/ASVS dan https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.xml — pemetaan bab5.0, bukan klaim conformance.
- WCAG2.2: https://www.w3.org/TR/WCAG22/ ; ISO25010 metadata: https://www.iso.org/standard/78176.html — rujukan model/target, bukan sertifikasi atau reproduksi standar ISO.
- UU27/2022 Pasal46: https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/ — kewajiban controller3x24jam; internal24jam adalah audit default escalation, bukan bunyi undang-undang.

Tanggal pemeriksaan rujukan29Oktober2026. Penetapan versi server dan kompatibilitas perangkat tetap preflight/implementasi; dokumentasi daring tidak dijadikan inventaris host.

## Addendum konsolidasi makro 2.1-macro.1

Audit historis di atas dipertahankan sebagai asal AUD-01–46. Konsolidasi ini mengamati paket langsung 37 berkas/1.016.000 byte dan memverifikasi 36/36 entri manifest. Arsip 32 berkas original dengan digest yang dicatat di atas tidak tersedia terpisah; hasil 31/31 tidak diklaim sebagai observasi baru. Pairing master/template dan 37 blok teks agregat cocok byte-per-byte.

Master §23 MAC-01–08 menutup ketidakjelasan retensi minimum/hold, tenggat PDP, trust boundary NAS, local/remote dependencies dan keputusan gate. Temuan serta batas konsolidasi dirinci pada Macro_Consolidation_Report_v2_1.md. Checklist QG formal tetap NOT_EVALUATED; kesiapan prasyarat G0–G5 BLOCKED; 84 kasus tetap NOT_RUN. Tidak ada sumber aplikasi, runner runtime, server/lab, review profesional atau release flag yang dianggap sudah ada. Verifier Python hanya memeriksa dokumen/arsip.
