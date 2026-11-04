# MicroTix — checkpoint kemajuan

Rekam jejak eksekusi agent per IMPLEMENTATION_PLAN.md §2.5. Terakhir diperbarui: 2026-11-05 (Asia/Jakarta).

## Checkpoint FE-1 — Fondasi frontend R1 (documention-first → aplikasi berjalan)

**Scope**: seluruh frontend R1 sesuai docs/UI_UX.md (U01–U08, U12–U14, U16, U18–U19) pada `apps/web`, tanpa perubahan backend/domain (belum ada backend — repository documentation-first).

### Status implementasi

| Area | Status | Catatan |
|---|---|---|
| Bootstrap `apps/web` (Vite+React18+TS+pnpm) | done | pnpm 12; deps: react-router-dom, @tanstack/react-query, react-intl (stack ARCHITECTURE.md §1) |
| Design tokens (tokens.css) | done | Warna/tipografi/spacing/radius persis UI_UX.md §2 |
| i18n FormatJS | done | `locales/{id,en}/web.json`, 908 kunci, paritas placeholder 100%; default `id`; pemilih bahasa cookie fungsional |
| Branding resolver | done | Placeholder dev berlabel; publication_blocked sesuai branding.json |
| Permission & release flags | done | Bundel peran ARCHITECTURE.md §3; flag R2–R4 off → menu disembunyikan |
| API boundary typed + mock adapter | done | Endpoint terdokumentasi §5 persis; PENDING_BACKEND ditandai di `client.ts`; banner "MODE PENGEMBANGAN" membedakan fixture dari produksi |
| 17 komponen wajib UI_UX.md §2 | done | AppShell, TenantSwitcher, PageHeader, FilterBar, DataTable, MobileServiceCard, StatusBadge, FreshnessLabel, JobProgress, BulkActionBar, ConfirmAction, FieldError, PermissionNotice, EmptyState, MetricCard, ChartWithTable, AuditTimeline |
| Halaman R1 | done | U01 landing, U02 login/register/verify/recover (+TOTP), U03 overview, U04 list+detail+tambah pelanggan, U05 enrollment 5 langkah, U06 detail router 7 tab, U07 wizard 8 langkah, U08 CSV, U12 backup, U13 monitoring, U14 admin (header navy), U16 job center+detail, U18 settings (tim/langganan/audit), U19 radius (akun/router/cutover B0–B6), plus halaman Paket dan Profile (kontrak TK-408 PENDING_BACKEND) |

### Verifikasi aktual (command + hasil)

| Command (dari `apps/web`) | Exit | Hasil |
|---|---|---|
| `tsc -b --pretty false` | 0 | typecheck bersih (strict, noUncheckedIndexedAccess) |
| `eslint src --ext ts,tsx` | 0 | 0 error/0 warning |
| `vitest run` | 0 | 42/42 test lulus (format, status tone, permission, katalog, adapter mock, badge a11y) |
| `python3 scripts/check_i18n.py` | 0 | 908 kunci; missing id=0, en=0, extra=0; paritas placeholder OK |
| `python3 scripts/check_contrast.py` | 0 | 13/13 pasangan warna ≥4,5:1 (WCAG 2.2 AA, diukur) |
| `vite build` | 0 | 2,6 MiB dist; vendor 164 kB (gzip 54 kB); code splitting per rute |
| `python3 docs/tools/check_docs.py` (akar repo) | 0 | dokumentasi tetap valid |

**Pengujian browser nyata (agent-browser + Chrome headless, dev server Vite)**:
- Login → TOTP → redirect `/app/{tenant}/overview`: PASS (diperbaiki: route `/app` redirect kini eksplisit).
- Tenant switch RT Net Nusantara → RW Net Cemara: PASS; menu per teknisi menyembunyikan Perusahaan dan Tim/Paket Aplikasi sesuai izin (diperbaiki: pola `queryClient.clear()` memutus observer; kini removeQueries selektif + setQueryData).
- Wizard tambah pelanggan → pilihan "Buat akun" → job dibuat → navigasi ke job detail → status berakhir "Succeeded — verified" via polling: PASS.
- Cutover RADIUS + dialog reauth (password+TOTP) → job radius_cutover_step: PASS.
- Drawer mobile 360px → navigasi Pelanggan: PASS; MobileServiceCard 6 kartu; kolom bayar/isolir R2 tersembunyi (diperbaiki agar sesuai fase).
- Sweep 20 halaman × 4 viewport (1440/1280/768/360): 0 horizontal overflow (diperbaiki: header flex-wrap + tenant switcher ringkas mobile, split-view admin 1 kolom <1024px).
- Keyboard: skip link adalah fokus pertama; Tab menelusuri nav; `:focus-visible` + focus ring terukur di DOM.
- VLM visual: overview/customers/radius/admin/monitoring PASS; ditemukan & diperbaiki: (1) `--mt-space-9` tak terdefinisi → ikon search menimpa placeholder (kini 38px); (2) `landing.css` tidak diimpor Landing.tsx → hero full-width (kini terkontrol 780px); (3) nomor `<ol>` stepper bertabrakan label (kini `list-style:none` + wrap); (4) step disabled terlalu pudar (digelapkan).

### Keputusan engineering (reversible, dicatat)

1. **Stack tepat sesuai ARCHITECTURE.md §1**: React+TS+Vite+pnpm+TanStack Query+FormatJS. Tambahan: react-router-dom (routing U01–U20 standar industri), vitest+@testing-library (pengujian §1). Tanpa UI framework eksternal — CSS token murni demi kontrol kontras/ukuran dan kepatuhan tanpa dependensi berlebih.
2. **Katalog di `locales/{id,en}/web.json`** (domain `web` per I18N.md §3) di luar root vite — alias `@locales` + `server.fs.allow`.
3. **Mock adapter in-browser** (default `VITE_API_MODE=mock`) mengimplementasikan `ApiClient` typed; endpoint terdokumentasi §5 mengikuti kontrak persis (202→job_id, error envelope, kursor); endpoint auth/list-router PENDING_BACKEND ditandai eksplisit. Banner dev permanen saat mode mock.
4. **Uang string desimal** (numeric 20,2) → format `Rp1.500.000`/`IDR 1,500,000` hanya di lapisan tampilan.
5. **Offline ≠ merah**: tone warning/netral sesuai UI_UX.md §2; StatusBadge selalu ikon+teks.
6. Grafik SVG ringan dengan gap tetap gap + tabel alternatif (tanpa library chart).

### Blocker / dependency

- **Backend belum ada** (repository documentation-first): seluruh integrasi live BLOCKED sampai M0–M1 backend tersedia. Batas integrasi typed sudah siap (`src/api/client.ts` + `http.ts`); ganti `VITE_API_MODE=live` + proxy.
- Endpoint PENDING_BACKEND menunggu OpenAPI TK-408 (packages/bindings) dan skema auth/daftar router — daftar di header `client.ts`.
- Playwright E2E (`make e2e`): NOT_RUN — runtime browser automation memakai agent-browser manual; harness CI belum dibangun.
- verified_lab / release_enabled: tidak ada klaim.

### Langkah berikutnya

1. Backend M0–M1 → sambungkan `ApiClient` live (cookie+CSRF), hapus fixture dev dari alur uji.
2. Kontrak OpenAPI auth & routers → konfirmasi/segarkan tipe PENDING_BACKEND.
3. R2 (U09–U11, kolektor) setelah `release_enabled` — struktur route/flag sudah disiapkan.
4. Harness Playwright + pseudo-locale (xx-pseudo) ke CI.

## Lingkungan pengujian

- Linux sandbox; Node v24.22.2; pnpm 12.16.1; Chrome headless via agent-browser; tanpa DB/router nyata (frontend-only scope).
- Semua angka bisnis pada tampilan berasal dari fixture dev berlabel — bukan data produksi.
