import { expect, test } from '@playwright/test';
import { login } from '../helpers/harness';

/**
 * E2E billing U09/U10 (TK-604) — browser nyata ↔ backend nyata.
 *
 * Tenant seed khusus (seed_billing_e2e, via e2e/run.sh):
 * - Andi Lunas  (SVC-EB1): invoice LUNAS + akun suspended  → layak aktivasi.
 * - Bella Terbuka (SVC-EB2): invoice OPEN + akun suspended → TIDAK layak
 *   sampai dibayar (uji validasi pembayaran per item).
 * - Citra Aktif (SVC-EB3): akun aktif → bukan kandidat.
 *
 * Alur: U09 tiga tab + verifikasi dana dua tahap + dokumen PDF →
 * U10 kelayakan + aktivasi massal per item (snapshot + kondisi terbaru).
 */
const BILLING_TENANT_ID = process.env.E2E_BILLING_TENANT_ID ?? '';
const BILLING_OWNER = {
  email: process.env.E2E_BILLING_OWNER_EMAIL ?? 'owner-billing@dev.local',
  password: process.env.E2E_BILLING_OWNER_PASSWORD ?? 'dev-seed-only-2026',
};

test.describe('billing U09/U10 (backend nyata)', () => {
  test('U09 invoice seed + aging + dokumen PDF terbit', async ({ page }) => {
    test.skip(!BILLING_TENANT_ID, 'seed_billing_e2e tidak tersedia');
    await login(page, BILLING_OWNER.email, BILLING_OWNER.password);
    await expect(page.getByRole('link', { name: 'Tagihan dan Pembayaran' })).toBeVisible();
    await page.getByRole('link', { name: 'Tagihan dan Pembayaran' }).click();
    await page.waitForURL(new RegExp(`/app/${BILLING_TENANT_ID}/billing`));

    // Invoice seed: Andi (lunas) + Bella (terbuka) — nama + tautan PDF.
    await expect(page.getByText('Andi Lunas')).toBeVisible();
    await expect(page.getByText('Bella Terbuka')).toBeVisible();
    const pdfLink = page.getByRole('link', { name: 'Lihat PDF' }).first();
    await expect(pdfLink).toBeVisible();
    const href = await pdfLink.getAttribute('href');
    expect(href).toMatch(new RegExp(`/api/v1/tenants/${BILLING_TENANT_ID}/documents/`));
    // Dokumen nyata: sesi browser menarik PDF (content-type + byte signature).
    const resp = await page.request.get(href!);
    expect(resp.status()).toBe(200);
    expect(resp.headers()['content-type'] ?? '').toContain('application/pdf');
    expect((await resp.body()).subarray(0, 4)).toEqual(Buffer.from('%PDF'));
    // Aging strip tampil (bucket label selalu ada, bukan angka palsu).
    await expect(page.getByText('Belum jatuh tempo')).toBeVisible();
  });

  test('U10: Bella diblokir (tagihan belum lunas); Andi berhasil — per item', async ({ page }) => {
    test.skip(!BILLING_TENANT_ID, 'seed_billing_e2e tidak tersedia');
    await login(page, BILLING_OWNER.email, BILLING_OWNER.password);
    await page.goto(`/app/${BILLING_TENANT_ID}/activation`);

    await expect(page.getByText('Andi Lunas')).toBeVisible();
    await expect(page.getByText('Bella Terbuka')).toBeVisible();
    await expect(page.getByText('Layak diaktifkan').first()).toBeVisible();
    await expect(page.getByText('Ada tagihan belum lunas').first()).toBeVisible();

    // Pilih KEDUA baris: konfirmasi menyatakan 1 layak / 1 tidak layak.
    await page.getByRole('row', { name: /Andi Lunas/ }).getByRole('checkbox').check();
    await page.getByRole('row', { name: /Bella Terbuka/ }).getByRole('checkbox').check();
    await page.getByRole('button', { name: /Aktifkan 2 terpilih/ }).click();
    await expect(page.getByText(/1 layak, 1 tidak layak/)).toBeVisible();
    await page.getByRole('button', { name: 'Aktifkan', exact: true }).click();

    // Hasil per item: Andi berhasil; Bella perlu tinjau (diblokir, tidak
    // mengurungkan keberhasilan Andi) — done_when TK-604.
    await expect(page.getByText('Berhasil diverifikasi').first()).toBeVisible();
    await expect(page.getByText('Perlu tinjau').first()).toBeVisible();
    await expect(page.getByText('1 berhasil, 1 diblokir')).toBeVisible();
  });

  test('U09 verifikasi dana dua tahap + kwitansi → U10 aktivasi Bella', async ({ page }) => {
    test.skip(!BILLING_TENANT_ID, 'seed_billing_e2e tidak tersedia');
    await login(page, BILLING_OWNER.email, BILLING_OWNER.password);
    await page.goto(`/app/${BILLING_TENANT_ID}/billing`);

    // 1) Catat penerimaan tunai 300.000 (BIL-03 tahap 1).
    await page.getByRole('tab', { name: 'Pengajuan pembayaran' }).click();
    await page.getByRole('button', { name: 'Catat penerimaan' }).click();
    await page.getByLabel(/Nominal/).fill('300000');
    await page.getByRole('button', { name: 'Catat', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Verifikasi dana' }).first()).toBeVisible();

    // 2) Tolak penerimaan kecil (alasan wajib) — tombol Tolak di barisnya.
    await page.getByRole('button', { name: 'Catat penerimaan' }).click();
    await page.getByLabel(/Nominal/).fill('10000');
    await page.getByRole('button', { name: 'Catat', exact: true }).click();
    await expect(page.getByText('Rp10.000')).toBeVisible();
    const rejectRow = page.getByRole('row', { name: /Rp10\.000/ });
    await rejectRow.getByRole('button', { name: 'Tolak', exact: true }).click();
    await page.getByLabel(/Alasan penolakan/).fill('Nominal uji tidak cocok');
    await page.getByRole('button', { name: 'Tolak', exact: true }).last().click();
    await page.getByRole('button', { name: 'Ditolak' }).click();
    await expect(page.getByText('Nominal uji tidak cocok')).toBeVisible();

    // 3) Verifikasi dana 300.000 dengan alokasi ke invoice Bella (tahap 2).
    await page.getByRole('button', { name: 'Menunggu verifikasi' }).click();
    await page.getByRole('button', { name: 'Verifikasi dana' }).first().click();
    await expect(page.getByText('Alokasi ke invoice')).toBeVisible();
    const allocRow = page.getByRole('checkbox').first();
    await allocRow.check();
    await page.getByRole('button', { name: 'Verifikasi dana' }).last().click();

    // Banner U09→U10 (aktivasi manual terpisah, bukan otomatis).
    await expect(page.getByText(/menunggu aktivasi/)).toBeVisible();

    // 4) Tab terverifikasi: alokasi + kwitansi PDF nyata.
    await page.getByRole('tab', { name: 'Pembayaran terverifikasi' }).click();
    await expect(page.getByText('Dialokasikan')).toBeVisible();
    const receipt = page.getByRole('link', { name: 'Kwitansi PDF' }).first();
    await expect(receipt).toBeVisible();
    const rHref = await receipt.getAttribute('href');
    const rResp = await page.request.get(rHref!);
    expect(rResp.status()).toBe(200);
    expect(rResp.headers()['content-type'] ?? '').toContain('application/pdf');

    // 5) U10: Bella kini layak → aktivasi berhasil.
    await page.getByRole('button', { name: 'Buka daftar aktivasi' }).click();
    await page.waitForURL(new RegExp(`/app/${BILLING_TENANT_ID}/activation`));
    await expect(page.getByText('Bella Terbuka')).toBeVisible();
    await page.getByRole('row', { name: /Bella Terbuka/ }).getByRole('checkbox').check();
    await page.getByRole('button', { name: /Aktifkan 1 terpilih/ }).click();
    await page.getByRole('button', { name: 'Aktifkan', exact: true }).click();
    await expect(page.getByText('Berhasil diverifikasi').first()).toBeVisible();
    // Selesai: tidak ada lagi akun terisolir di tenant ini.
    await expect(page.getByText('Tidak ada akun terisolir')).toBeVisible({ timeout: 15_000 });
  });
});
