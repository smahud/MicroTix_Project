import { beforeEach, describe, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { IntlProvider } from 'react-intl';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import idWeb from '@locales/id/web.json';
import { MockApiClient } from '../../api/mock/adapter';
import { SessionProvider } from '../../state/session';
import type { AuthContextShape } from '../../api/client';
import { PERMISSIONS } from '../../permissions/permissions';
import BillingPage from './BillingPage';
import ActivationPage from '../activation/ActivationPage';

const T = 'b3f0a2de-1111-4000-8000-tenant01';

/** Sesi owner tenant01 — cache 'session' di-seed agar can() aktif. */
const SESSION_CTX: AuthContextShape = {
  user: { id: 'usr-owner-01', email: 'huda@example.dev', full_name: 'Huda', mfa_enabled: true, platform_admin: false },
  tenants: [{ id: T, display_name: 'RT Net Nusantara', role: 'owner' }],
  active_tenant_id: T,
  permissions: [...PERMISSIONS].filter((p) => !p.startsWith('platform.')),
  sensitive_reauth_until: null,
};

function renderAt(path: string, element: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['session'], SESSION_CTX);
  return render(
    <IntlProvider locale="id" messages={idWeb as Record<string, string>}>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <SessionProvider>
            <Routes>
              <Route path="/app/:tenantId/billing" element={element} />
              <Route path="/app/:tenantId/activation" element={element} />
            </Routes>
          </SessionProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </IntlProvider>,
  );
}

/** U09 — render tiga tab + aging + verifikasi dua tahap lewat UI mock. */
describe('BillingPage (U09)', () => {
  beforeEach(async () => {
    const api = new MockApiClient();
    await api.login('huda@example.dev', 'password-12-char');
    await api.loginTotp('123456');
    await api.switchTenant(T);
  });

  it('tab Invoice menampilkan invoice mock + tautan PDF + strip aging', async () => {
    renderAt(`/app/${T}/billing`, <BillingPage tenantId={T} />);
    expect(await screen.findByText('INV-ns01-202611-0003')).toBeTruthy();
    expect(screen.getByText('Budi Santoso')).toBeTruthy();
    expect(screen.getAllByText('Lihat PDF').length).toBeGreaterThan(0);
    // Aging strip: bucket label tampil.
    expect(screen.getByText('0–30 hari')).toBeTruthy();
    expect(screen.getByRole('tab', { name: 'Pengajuan pembayaran' })).toBeTruthy();
    expect(screen.getByRole('tab', { name: 'Pembayaran terverifikasi' })).toBeTruthy();
  });

  it('tab Pengajuan: catat penerimaan tunai → verifikasi dengan alokasi → banner U10', async () => {
    renderAt(`/app/${T}/billing`, <BillingPage tenantId={T} />);
    fireEvent.click(await screen.findByRole('tab', { name: 'Pengajuan pembayaran' }));

    fireEvent.click(await screen.findByRole('button', { name: 'Catat penerimaan' }));
    // Label memuat tanda wajib (*) — pakai role input angka.
    const amountInput = await screen.findByRole('spinbutton');
    fireEvent.change(amountInput, { target: { value: '300000' } });
    fireEvent.click(await screen.findByRole('button', { name: /^Catat$/ }));

    // Tunggu dialog catat menutup (penerimaan baru terekam asinkron) dan
    // DUA tombol verifikasi tampil (penerimaan baru + fixture pay-001).
    await waitFor(() => {
      expect(screen.queryByText('Catat penerimaan pembayaran')).toBeNull();
    });
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Verifikasi dana' }).length).toBe(2);
    });
    fireEvent.click(screen.getAllByRole('button', { name: 'Verifikasi dana' })[0]!);

    // Dialog verifikasi: tunggu editor alokasi, pilih invoice open pertama
    // (SVC-004 — Agus, sisa 250.000; default min(250000, 300000)).
    await screen.findByText('Alokasi ke invoice');
    const allocCheckboxes = await screen.findAllByRole('checkbox');
    fireEvent.click(allocCheckboxes[0]!);
    const dialogs = screen.getAllByRole('button', { name: 'Verifikasi dana' });
    fireEvent.click(dialogs[dialogs.length - 1]!);

    // Banner U09→U10 muncul setelah verifikasi (mock: kandidat eligible).
    await waitFor(
      () => {
        expect(screen.getByText(/menunggu aktivasi/)).toBeTruthy();
      },
      { timeout: 4000 },
    );
    expect(screen.getByRole('button', { name: 'Buka daftar aktivasi' })).toBeTruthy();
  });

  it('filter periode menyaring invoice (server-side via adapter)', async () => {
    renderAt(`/app/${T}/billing?period_from=2026-11-01&period_to=2026-12-01`, <BillingPage tenantId={T} />);
    await screen.findByText('INV-ns01-202611-0001');
    // Invoice Oktober (INV-...-202610-0009) tidak tampil dalam rentang November.
    expect(screen.queryByText('INV-ns01-202610-0009')).toBeNull();
    // Bersihkan filter → invoice Oktober kembali.
    fireEvent.change(screen.getByLabelText('Periode dari'), { target: { value: '' } });
    fireEvent.change(screen.getByLabelText('Periode sampai'), { target: { value: '' } });
    await waitFor(() => {
      expect(screen.getByText('INV-ns01-202610-0009')).toBeTruthy();
    });
  });
});

/** U10 — kandidat suspended, kelayakan tagihan, aktivasi massal per item. */
describe('ActivationPage (U10)', () => {
  beforeEach(async () => {
    const api = new MockApiClient();
    await api.login('huda@example.dev', 'password-12-char');
    await api.loginTotp('123456');
    await api.switchTenant(T);
  });

  it('menampilkan kandidat suspended dengan kelayakan; aktivasi → daftar kosong', async () => {
    renderAt(`/app/${T}/activation`, <ActivationPage tenantId={T} />);

    // Mock: siti.aminah suspended + SVC-002 lunas → 1/1 layak.
    expect(await screen.findByText('Siti Aminah')).toBeTruthy();
    expect(screen.getByText('1 dari 1 kandidat layak diaktifkan')).toBeTruthy();
    expect(screen.getByText('Layak diaktifkan')).toBeTruthy();

    // Pilih baris (checkbox terakhir = baris; pertama = header tabel)
    // → konfirmasi → hasil per item sukses → daftar kosong jujur.
    const boxes = await screen.findAllByRole('checkbox');
    fireEvent.click(boxes[boxes.length - 1]!);
    fireEvent.click(screen.getByRole('button', { name: /Aktifkan 1 terpilih/ }));
    const confirm = await screen.findByRole('button', { name: /^Aktifkan$/ });
    fireEvent.click(confirm);
    expect(await screen.findByText('Berhasil diverifikasi')).toBeTruthy();
    await waitFor(
      () => {
        expect(screen.getByText('Tidak ada akun terisolir')).toBeTruthy();
      },
      { timeout: 5000 },
    );
  });
});
