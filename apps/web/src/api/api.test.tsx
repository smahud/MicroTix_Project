import { beforeEach, describe, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { IntlProvider } from 'react-intl';
import { MemoryRouter } from 'react-router-dom';
import idWeb from '@locales/id/web.json';
import { MockApiClient } from './mock/adapter';

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderWithProviders(ui: React.ReactElement) {
  const qc = makeClient();
  return render(
    <IntlProvider locale="id" messages={idWeb as Record<string, string>}>
      <QueryClientProvider client={qc}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </IntlProvider>,
  );
}

/**
 * Adapter mock — kontrak perilaku yang diharapkan UI:
 * pesan gagal login seragam, TOTP wajib, CSV validasi per baris,
 * progres job berjalan, reveal memerlukan reauth.
 */
describe('MockApiClient', () => {
  let api: MockApiClient;

  beforeEach(() => {
    api = new MockApiClient();
  });

  it('login memerlukan TOTP bila MFA aktif', async () => {
    const res = await api.login('huda@example.dev', 'password-12-char');
    expect(res.requires_totp).toBe(true);
  });

  it('pesan gagal login seragam — tidak membocorkan akun', async () => {
    await expect(api.login('huda@example.dev', 'short')).rejects.toThrow(/Email atau password tidak cocok/);
    await expect(api.login('tidakada@example.dev', 'short')).rejects.toThrow(/Email atau password tidak cocok/);
  });

  it('register menolak password < 12 karakter dengan field error', async () => {
    await expect(
      api.register({ full_name: 'Budi', email: 'b@x.id', password: 'short', company_name: 'RT Net' }),
    ).rejects.toMatchObject({ code: 'validation_error' });
  });

  it('TOTP salah → validation_error', async () => {
    await expect(api.loginTotp('12')).rejects.toMatchObject({ code: 'validation_error' });
  });

  it('CSV validasi menandai baris tanpa username', async () => {
    const draft = await api.createCsvImport('b3f0a2de-1111-4000-8000-tenant01', {
      mode: 'create',
      file_name: 't.csv',
      rows: [
        { username: 'a', full_name: 'A' },
        { username: '', full_name: 'B' },
      ],
    });
    const res = await api.validateCsvImport('b3f0a2de-1111-4000-8000-tenant01', draft.id);
    expect(res.total_rows).toBe(2);
    expect(res.valid_rows).toBe(1);
    expect(res.row_errors[0]?.field).toBe('username');
  });

  it('reveal kredensial tanpa reauth ditolak forbidden', async () => {
    await expect(
      api.revealCredential('b3f0a2de-1111-4000-8000-tenant01', 'svc-001'),
    ).rejects.toMatchObject({ code: 'forbidden' });
  });

  it('cutover tanpa reauth ditolak forbidden', async () => {
    await expect(
      api.startRadiusCutover('b3f0a2de-1111-4000-8000-tenant01', 'rtr-101'),
    ).rejects.toMatchObject({ code: 'forbidden' });
  });

  it('reauth berhasil memberi jendela 10 menit, cutover lalu diterima', async () => {
    const { valid_until } = await api.reauthenticate('password-12', '123456');
    expect(new Date(valid_until).getTime()).toBeGreaterThan(Date.now());
    const res = await api.startRadiusCutover('b3f0a2de-1111-4000-8000-tenant01', 'rtr-101');
    expect(res.job_id).toBeTruthy();
  });

  it('job berjalan lalu selesai (polling state)', async () => {
    const job = await api.runBackupNow('b3f0a2de-1111-4000-8000-tenant01', 'rtr-101');
    const early = await api.getJob('b3f0a2de-1111-4000-8000-tenant01', job.job_id);
    expect(['queued', 'executing', 'verifying', 'succeeded']).toContain(early.state);
    // Router dengan VPN down → backup gagal dengan router_unreachable
    const bad = await api.runBackupNow('b3f0a2de-1111-4000-8000-tenant01', 'rtr-103');
    await new Promise((r) => setTimeout(r, 6500));
    const badJob = await api.getJob('b3f0a2de-1111-4000-8000-tenant01', bad.job_id);
    expect(badJob.state).toBe('failed');
    expect(badJob.error_code).toBe('router_unreachable');
  }, 10_000);

  it('listServices memfilter quick_tab incomplete', async () => {
    const page = await api.listServices(
      'b3f0a2de-1111-4000-8000-tenant01',
      { quick_tab: 'incomplete' },
      { limit: 50 },
    );
    expect(page.items.length).toBeGreaterThan(0);
    expect(page.items.every((s) => s.incomplete_mapping)).toBe(true);
  });

  it('pembayaran platform: approve tanpa alasan ok, reject wajib alasan', async () => {
    const subs = await api.listPlatformSubmissions('submitted');
    expect(subs.length).toBeGreaterThan(0);
    await api.approvePlatformSubmission(subs[0]!.id);
    await expect(api.rejectPlatformSubmission('sub-02', ' ')).rejects.toMatchObject({ code: 'validation_error' });
  });
});

describe('StatusBadge terhadap kontrak aksesibilitas', () => {
  it('render label + ikon — warna bukan satu-satunya penanda', async () => {
    const { StatusBadge } = await import('../design-system/components/StatusBadge');
    renderWithProviders(<StatusBadge tone="warning" label="Data usang" />);
    const el = await screen.findByText('Data usang');
    expect(el).toBeTruthy();
    expect(el.closest('.mt-badge')?.querySelector('svg')).toBeTruthy();
  });
});
