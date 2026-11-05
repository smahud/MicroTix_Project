# Backend MicroTix

Direktori ini dicadangkan untuk layanan backend MicroTix. **Belum ada kode backend yang diimplementasikan atau dikonfigurasi** — repository berangkat dari tahap documentation-first, dan frontend R1 berjalan pada adapter mock terisolasi (`apps/web`, `VITE_API_MODE=mock`).

Frontend dan backend sengaja dipisahkan direktori agar keduanya dapat dikonfigurasi dan berevolusi secara mandiri:

- `apps/web/` — frontend (React + TypeScript + Vite), sudah terimplementasi untuk R1.
- `backend/` — layanan backend, akan dikonfigurasi kemudian (direktori ini).

## Struktur yang direncanakan

Sesuai `docs/ARCHITECTURE.md` (§ Struktur implementasi), saat backend mulai dikonfigurasi, direktori ini diisi dengan:

```
backend/
  domains/    # identity, tenancy, subscriptions, customers, access,
              # network, jobs, backups, i18n; kemudian billing, ledger,
              # monitoring, field operations saat diperlukan
  adapters/   # routeros, radius, storage, acs
  infra/      # compose, systemd, nftables, caddy, freeradius
  tests/      # contracts, integration, router_lab, radius_lab, e2e
```

## Titik sambung frontend

Kontrak integrasi sudah disiapkan pada `apps/web/src/api/` (`client.ts`, `http.ts`, `contracts.ts`):

- Endpoint yang terdokumentasi di `docs/ARCHITECTURE.md` §5 diimplementasikan terhadap antarmuka `ApiClient` typed.
- Endpoint yang menunggu backend ditandai eksplisit `PENDING_BACKEND` di header `client.ts`.
- Beralih ke integrasi live: set `VITE_API_MODE=live` + proxy, tanpa mengubah komponen halaman.

Mulai dari `docs/IMPLEMENTATION_PLAN.md` (milestone M0–M1) dan `docs/ARCHITECTURE.md` sebelum menulis kode backend.
