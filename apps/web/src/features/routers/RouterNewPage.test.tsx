import { describe, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { IntlProvider } from 'react-intl';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import idWeb from '@locales/id/web.json';
import { SessionProvider } from '../../state/session';
import type { AuthContextShape } from '../../api/client';
import { PERMISSIONS } from '../../permissions/permissions';
import RouterNewPage from './RouterNewPage';

const T = 'b3f0a2de-1111-4000-8000-tenant01';

/** Sesi owner tenant01 — cache 'session' di-seed agar can() aktif. */
const SESSION_CTX: AuthContextShape = {
  user: { id: 'usr-owner-01', email: 'huda@example.dev', full_name: 'Huda', mfa_enabled: true, platform_admin: false },
  tenants: [{ id: T, display_name: 'RT Net Nusantara', role: 'owner' }],
  active_tenant_id: T,
  permissions: [...PERMISSIONS].filter((p) => !p.startsWith('platform.')),
  sensitive_reauth_until: null,
};

function renderNew() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['session'], SESSION_CTX);
  return render(
    <IntlProvider locale="id" messages={idWeb as Record<string, string>}>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[`/app/${T}/routers/new`]}>
          <SessionProvider>
            <Routes>
              <Route path="/app/:tenantId/routers/new" element={<RouterNewPage tenantId={T} />} />
            </Routes>
          </SessionProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </IntlProvider>,
  );
}

/**
 * U05 Phase-2 (master directive konektivitas): pemilih protokol + versi
 * RouterOS yang jujur — WireGuard aktif (v7.1+), SSTP aktif (v6.49.x + v7.x,
 * komplementer); L2TP/OpenVPN tampil "direncanakan". RouterOS v6 + WireGuard
 * memblokir kelanjutan dengan alasan; v6 + SSTP dapat dilanjutkan.
 */
describe('RouterNewPage (U05 — protokol & versi RouterOS)', () => {
  it('menampilkan pilihan versi + protokol; WireGuard & SSTP aktif, L2TP/OpenVPN direncanakan', () => {
    renderNew();
    expect(screen.getByText('WireGuard (disarankan)')).toBeTruthy();
    expect(screen.getByText(/TLS 1.2 \+ MSCHAPv2; RouterOS v6 dan v7/)).toBeTruthy();
    expect(screen.getAllByText('Direncanakan — belum tersedia di rilis ini.').length).toBe(2);
    expect(screen.getByText('RouterOS v7 (7.1+)')).toBeTruthy();
    expect(screen.getByText('RouterOS v6 atau lebih lama')).toBeTruthy();
  });

  it('RouterOS v6 menonaktifkan WireGuard + memblokir Lanjutkan dengan alasan jujur', () => {
    renderNew();
    fireEvent.click(screen.getByText('RouterOS v6 atau lebih lama'));
    // Alasan kompatibilitas WireGuard↔v6 terlihat (hint radio + alasan tombol).
    expect(screen.getAllByText(/WireGuard membutuhkan RouterOS v7\.1\+/).length).toBeGreaterThan(0);
    const btn = screen.getByRole('button', { name: /Lanjutkan/ });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it('RouterOS v6 + SSTP dapat dilanjutkan (Phase-2: v6 via SSTP)', async () => {
    renderNew();
    fireEvent.click(screen.getByText('RouterOS v6 atau lebih lama'));
    fireEvent.click(screen.getByText('SSTP', { exact: true }));
    fireEvent.change(screen.getByLabelText(/Nama tampilan/), { target: { value: 'Router V6 SSTP' } });
    fireEvent.change(screen.getByLabelText(/Kode router/), { target: { value: 'RTR-V6-01' } });
    const btn = screen.getByRole('button', { name: /Lanjutkan/ });
    expect((btn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(btn);
    expect(await screen.findByText('Prasyarat perangkat')).toBeTruthy();
    expect(screen.getByText(/Protokol terpilih: SSTP/)).toBeTruthy();
  });

  it('submit v7 + WireGuard valid → lanjut ke Prasyarat dengan ringkasan terpilih', async () => {
    renderNew();
    fireEvent.change(screen.getByLabelText(/Nama tampilan/), { target: { value: 'Router Uji Protokol' } });
    fireEvent.change(screen.getByLabelText(/Kode router/), { target: { value: 'RTR-UJI-01' } });
    fireEvent.click(screen.getByRole('button', { name: /Lanjutkan/ }));
    expect(await screen.findByText('Prasyarat perangkat')).toBeTruthy();
    expect(screen.getByText(/Protokol terpilih: WireGuard/)).toBeTruthy();
  });

  it('kode router tidak valid memblokir lanjut dengan galat isian', () => {
    renderNew();
    fireEvent.change(screen.getByLabelText(/Nama tampilan/), { target: { value: 'Router Uji' } });
    fireEvent.change(screen.getByLabelText(/Kode router/), { target: { value: 'kode salah!' } });
    fireEvent.click(screen.getByRole('button', { name: /Lanjutkan/ }));
    expect(screen.getByText('Kode router 2–16 karakter: huruf besar, angka, tanda hubung')).toBeTruthy();
    // Masih di langkah Identitas.
    expect(screen.queryByText('Prasyarat perangkat')).toBeNull();
  });

  it('langkah Skrip menampilkan baris endpoint gateway (ROUTEROS.md §2.2)', async () => {
    renderNew();
    fireEvent.change(screen.getByLabelText(/Nama tampilan/), { target: { value: 'Router Gateway Uji' } });
    fireEvent.change(screen.getByLabelText(/Kode router/), { target: { value: 'RTR-GWU-1' } });
    fireEvent.click(screen.getByRole('button', { name: /Lanjutkan/ }));
    await screen.findByText('Prasyarat perangkat');
    fireEvent.click(screen.getAllByRole('button', { name: /Lanjutkan/ })[0]!);
    await waitFor(() => {
      expect(screen.getByTestId('gateway-line').textContent).toContain('microtix.invalid');
      expect(screen.getByTestId('gateway-line').textContent).toContain('51820');
    });
    expect(screen.getByTestId('bootstrap-script').textContent).toContain('endpoint-address="microtix.invalid"');
  });
});
