import { expect, test } from '@playwright/test';
import {
  FOREIGN_TENANT_ID,
  OWN_TENANT_ID,
  SEEDED_OWNER,
  login,
  readVerificationToken,
} from '../helpers/harness';

/**
 * Alur UI↔API nyata (auth): happy / error / isolasi tenant.
 * Backend: PostgreSQL 17 nyata + RLS. Tidak ada mock.
 */

test.describe('autentikasi (backend nyata)', () => {
  test('login owner seed → overview tenant (happy path)', async ({ page }) => {
    await login(page, SEEDED_OWNER.email, SEEDED_OWNER.password);
    // Data tenant nyata dari API (nama perusahaan seed muncul di shell).
    await expect(page.getByText('RT Net Nusantara', { exact: false }).first()).toBeVisible();
  });

  test('password salah → pesan generik, TIDAK masuk (error path)', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(SEEDED_OWNER.email);
    await page.getByLabel('Password').fill('password-yang-benar-banget-tapi-salah');
    await page.getByRole('button', { name: 'Masuk' }).click();
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Email atau password tidak cocok');
    await expect(page).toHaveURL(/\/login/);
  });

  test('/app tanpa sesi → redirect ke /login (guard)', async ({ page }) => {
    await page.goto('/app');
    await page.waitForURL(/\/login/);
  });

  test('akses URL tenant asing → TIDAK menampilkan data tenant lain (isolasi)', async ({ page }) => {
    test.skip(!FOREIGN_TENANT_ID || !OWN_TENANT_ID, 'ID tenant seed tidak tersedia (set E2E_OWN_TENANT_ID/E2E_FOREIGN_TENANT_ID)');
    await login(page, SEEDED_OWNER.email, SEEDED_OWNER.password);
    // Pemilik Nusantara membuka URL tenant Cemara secara langsung.
    await page.goto(`/app/${FOREIGN_TENANT_ID}/overview`);
    // page.request MEMBAWA cookie sesi browser — probe terautentikasi.
    // Backend menolak dengan 404 envelope generik (RLS + resolve_membership).
    for (const probe of ['routers', 'monitor']) {
      const res = await page.request.get(`/api/v1/tenants/${FOREIGN_TENANT_ID}/${probe}`);
      expect(res.status()).toBe(404);
      const body = await res.json();
      expect(body.code).toBe('not_found');
    }
    // UI tidak pernah menampilkan data/identitas tenant asing.
    const leaked = await page.getByText('RW Net Cemara', { exact: false }).count();
    expect(leaked).toBe(0);
  });

  test('register → verifikasi email (token dari email konsol) → login tenant baru', async ({ page }) => {
    const stamp = Date.now();
    const email = `e2e-${stamp}@dev.local`;
    const company = `E2E RT Net ${stamp}`;
    const password = 'Passw0rdE2e!2026-kuat';
    await page.goto('/register');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Nama lengkap').fill(`Pemilik E2E ${stamp}`);
    await page.getByLabel('Nama perusahaan').fill(company);
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', { name: 'Daftar', exact: false }).click();
    await expect(page.getByText('Periksa email Anda')).toBeVisible();
    // Token dibaca dari jalur email dev (konsol backend) — bukan bypass API.
    const token = await readVerificationToken(email, '');
    await page.goto(`/verify?token=${token}`);
    // Verifikasi eksplisit (UX nyata: tombol, bukan auto-run).
    await page.getByRole('button', { name: 'Verifikasi sekarang' }).click();
    await expect(page.getByText('Email terverifikasi. Anda dapat masuk.')).toBeVisible();
    // Login kredensial baru → tenant baru dibuat (alur onboarding nyata).
    await page.goto('/login');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', { name: 'Masuk' }).click();
    await page.waitForURL(/\/app\/[0-9a-f-]+\/overview/);
    await expect(page.getByText(company, { exact: false }).first()).toBeVisible();
  });
});
