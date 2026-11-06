import { expect, test } from '@playwright/test';
import { OWN_TENANT_ID, SEEDED_OWNER, login } from '../helpers/harness';

/**
 * Alur onboarding router U05 (master directive §1) pada backend NYATA:
 * Tambah router (protokol WireGuard + RouterOS v7) → prasyarat → skrip
 * (endpoint gateway publik) → callback bridge meniru perangkat → job
 * verify_api_ssl diproses worker NYATA → Siap dengan label jujur SIMULATOR.
 *
 * Tidak ada mock: PostgreSQL 17 + RLS + runserver + runworker (e2e/run.sh).
 */

test.describe('onboarding router (backend nyata)', () => {
  test('tambah router WireGuard → skrip → bridge → terverifikasi (label simulator)', async ({ page }) => {
    test.skip(!OWN_TENANT_ID, 'ID tenant seed tidak tersedia (set E2E_OWN_TENANT_ID)');
    await login(page, SEEDED_OWNER.email, SEEDED_OWNER.password);

    const stamp = Date.now().toString().slice(-6);
    const routerCode = `RTR-E2E-${stamp}`;

    // 1) Identitas: default RouterOS v7 + WireGuard aktif; SSTP/L2TP/OpenVPN
    //    tampil jujur sebagai "direncanakan" (disabled).
    await page.goto(`/app/${OWN_TENANT_ID}/routers/new`);
    await expect(page.getByText('WireGuard (disarankan)')).toBeVisible();
    await expect(page.getByText('SSTP', { exact: true })).toBeVisible();
    await page.getByLabel(/Nama tampilan/).fill(`Router E2E ${stamp}`);
    await page.getByLabel(/Kode router/).fill(routerCode);
    await page.getByRole('button', { name: 'Lanjutkan' }).click();

    // 2) Prasyarat: ringkasan pilihan terlihat.
    await expect(page.getByRole('heading', { name: 'Prasyarat perangkat' })).toBeVisible();
    await expect(page.getByText(/Protokol terpilih: WireGuard/)).toBeVisible();
    await page.getByRole('button', { name: 'Lanjutkan' }).click();

    // 3) Skrip: baris endpoint gateway PUBLIK (dev .invalid — bukan IP tunnel),
    //    dan skrip RouterOS v7 memuat endpoint-address gateway.
    const scriptEl = page.getByTestId('bootstrap-script');
    await expect(scriptEl).toBeVisible();
    const gatewayLine = page.getByTestId('gateway-line');
    await expect(gatewayLine).toContainText('microtix.invalid');
    await expect(gatewayLine).toContainText('51820');
    await expect(scriptEl).toContainText('endpoint-address="microtix.invalid"');
    await expect(scriptEl).toContainText('https://microtix.invalid/api/v1/bridge/enroll-complete');
    // Regresi bug lama: endpoint TIDAK boleh IP tunnel internal, tanpa artefak SCEP.
    await expect(scriptEl).not.toContainText('endpoint-address="100.127.0.1"');
    await expect(scriptEl).not.toContainText('scep');

    // 4) Meniru ROUTER: kirim callback bridge dengan token dari skrip (body,
    //    bukan URL) — persis apa yang dilakukan /tool/fetch pada perangkat.
    //    POST butuh header CSRF seperti klien SPA live (cookie mtx_csrf).
    const scriptText = await scriptEl.textContent();
    const token = scriptText?.match(/:local token "([^"]+)"/)?.[1];
    expect(token, 'token enrollment harus ada di skrip').toBeTruthy();
    const csrfCookie = (await page.context().cookies()).find((c) => c.name === 'mtx_csrf');
    const bridge = await page.request.post('/api/v1/bridge/enroll-complete', {
      headers: { 'x-csrf-token': csrfCookie?.value ?? '' },
      data: { token, wg_public_key: `wgpub-e2e-${stamp}` },
    });
    expect(bridge.status()).toBe(200);
    expect((await bridge.json()).status).toBe('bootstrap_accepted');

    // 5) Menunggu → worker NYATA memproses verify_api_ssl → langkah Siap.
    await page.getByRole('button', { name: 'Saya telah menjalankan skrip' }).click();
    await expect(page.getByRole('heading', { name: 'Menunggu verifikasi' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Router terverifikasi' })).toBeVisible({
      timeout: 30_000,
    });

    // 6) Kejujuran: langkah Siap memuat banner SIMULATOR — bukan klaim
    //    konektivitas perangkat nyata (lab G1 belum tersedia).
    const banner = page.getByTestId('simulated-verification-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('simulator');

    // 7) Detail router: sumber verifikasi jujur + versi RouterOS tercatat.
    //    (Anchor seluler disembunyikan CSS pada viewport desktop — ambil ID
    //    router dari API nyata, lalu buka halaman detail secara langsung.)
    const routersRes = await page.request.get(`/api/v1/tenants/${OWN_TENANT_ID}/routers`);
    expect(routersRes.status()).toBe(200);
    const routers = (await routersRes.json()) as Array<{
      id: string;
      router_code: string;
      routeros_version: string | null;
    }>;
    const created = routers.find((r) => r.router_code === routerCode);
    expect(created, 'router ter-enroll muncul di daftar (API nyata)').toBeTruthy();
    expect(created?.routeros_version).toBe('7'); // disalin dari enrollment ke registry
    await page.goto(`/app/${OWN_TENANT_ID}/routers/${created!.id}`);
    await expect(page.getByTestId('verification-source')).toContainText('Simulasi');
  });

  test('RouterOS v6 memblokir kelanjutan dengan alasan jujur', async ({ page }) => {
    test.skip(!OWN_TENANT_ID, 'ID tenant seed tidak tersedia (set E2E_OWN_TENANT_ID)');
    await login(page, SEEDED_OWNER.email, SEEDED_OWNER.password);
    await page.goto(`/app/${OWN_TENANT_ID}/routers/new`);
    await page.getByText('RouterOS v6 atau lebih lama').click();
    await expect(page.getByText(/WireGuard membutuhkan RouterOS v7\.1\+/).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Lanjutkan' })).toBeDisabled();
  });
});
