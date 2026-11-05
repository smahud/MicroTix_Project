import { expect, test } from '@playwright/test';
import { SEEDED_OWNER, login } from '../helpers/harness';

/**
 * Sistem navigasi + i18n + viewport mobile (360px) pada data nyata.
 */

test('landing publik dirender (i18n default id)', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/MicroTix/i);
  await expect(page.getByRole('link', { name: 'Masuk', exact: false }).first()).toBeVisible();
});

test('navigasi mobile 360px: drawer → Pelanggan (empty state jujur)', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page, SEEDED_OWNER.email, SEEDED_OWNER.password);
  // Buka drawer navigasi (viewport sempit → tombol menu ber-aria-label jelas).
  await page.getByRole('button', { name: 'Buka menu navigasi' }).click();
  const linkPelanggan = page.getByRole('link', { name: 'Pelanggan' }).first();
  await linkPelanggan.click();
  await page.waitForURL(/\/customers$/);
  // Tenant seed kosong → EmptyState jujur (bukan data palsu).
  await expect(page.getByText('Belum ada pelanggan')).toBeVisible({ timeout: 15_000 });
});
