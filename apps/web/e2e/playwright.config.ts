import { defineConfig } from '@playwright/test';

/**
 * Harness E2E MicroTix — browser NYATA ↔ backend NYATA (IMPLEMENTATION_PLAN §4).
 *
 * - Backend Django nyata (PostgreSQL 17, RLS aktif) di 127.0.0.1:8010 —
 *   dikelola e2e/run.sh (dev bootstrap + seed + runserver), BUKAN oleh
 *   playwright (butuh DB idempoten + log email konsol untuk token verifikasi).
 * - Frontend: dev server Vite dengan proxy /api → backend (MICROTIX_API) dan
 *   VITE_API_MODE=live — adapter live saja, mock DITOLAK oleh guard anti-fake.
 * - Viewport terpilih: desktop 1280×720 (spek mobilitas mengatur 360px sendiri).
 */
export default defineConfig({
  testDir: './specs',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173',
    viewport: { width: 1280, height: 720 },
    locale: 'id-ID',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    // --host 127.0.0.1: vite default mengikat localhost yang bisa resolusi
    // ke ::1 (IPv6) — probe playwright dan browser wajib IPv4 konsisten.
    command: 'bash serve.sh',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      ...process.env,
      MICROTIX_API: process.env.E2E_API_BASE ?? 'http://127.0.0.1:8010',
      VITE_API_MODE: 'live',
    },
  },
});
