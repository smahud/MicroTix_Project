import * as fs from 'node:fs';
import { expect, type Page } from '@playwright/test';

/**
 * Helper E2E — hanya perancah pengujian; TIDAK ada jalur produksi.
 *
 * Token verifikasi email dibaca dari LOG KONSOL runserver (backend email
 * konsol di dev — jalur email nyata untuk lingkungan ini), seperti operator
 * membaca inbox. Tidak ada endpoint rahasia / mock / bypass API.
 */

export const SEEDED_OWNER = {
  email: process.env.E2E_SEEDED_EMAIL ?? 'owner-nusantara@dev.local',
  password: process.env.E2E_SEEDED_PASSWORD ?? 'dev-seed-only-2026',
};

export const OWN_TENANT_ID = process.env.E2E_OWN_TENANT_ID ?? '';
export const FOREIGN_TENANT_ID = process.env.E2E_FOREIGN_TENANT_ID ?? '';

const BACKEND_LOG = process.env.E2E_BACKEND_LOG ?? '/tmp/mtx-e2e-backend.log';

/** Ambil token verifikasi untuk email tertentu dari log email konsol. */
export async function readVerificationToken(email: string, marker: string): Promise<string> {
  // Email konsol Django berisi blok "To: <email>" lalu baris token tunggal
  // setelah "Kode verifikasi email Anda:".
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (fs.existsSync(BACKEND_LOG)) {
      const text = fs.readFileSync(BACKEND_LOG, 'utf-8');
      const regex = new RegExp(
        `To: ${email.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\r?\\n[\\s\\S]{0,600}?Kode verifikasi email Anda:\\s*\\r?\\n\\s*\\r?\\n([A-Za-z0-9_-]{20,80})`,
      );
      const m = text.match(regex);
      const found = m?.[1];
      if (found && found !== marker) return found;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`token verifikasi untuk ${email} tidak ditemukan di log backend dalam 30s`);
}

/** Login email+password → menunggu redirect ke /app/<tenant>/overview. */
export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Masuk' }).click();
  await page.waitForURL(/\/app\/[0-9a-f-]+\/overview/);
  await expect(page.getByRole('heading', { name: 'Beranda' })).toBeVisible();
}
