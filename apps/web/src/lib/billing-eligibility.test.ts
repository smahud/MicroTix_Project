import { describe, expect, it } from 'vitest';
import {
  evaluateActivationCandidates,
  outstandingByService,
  lastPaidInvoiceByService,
} from './billing-eligibility';
import type { InternetInvoice, RadiusAccountRow } from '../api/contracts';

function inv(over: Partial<InternetInvoice> = {}): InternetInvoice {
  return {
    id: 'inv-x',
    doc_number: 'INV-ns-202611-0001',
    service_id: 'svc-1',
    service_code: 'SVC-1',
    customer_name: 'Pelanggan',
    kind: 'prepaid',
    state: 'open',
    period_index: 0,
    period_start: '2026-11-01',
    period_end: '2026-12-01',
    due_date: '2026-11-01',
    issued_at: '2026-11-01T00:00:00Z',
    total_amount: '300000.00',
    paid_amount: '0.00',
    outstanding: '300000.00',
    first_period_policy: 'full',
    locale: 'id',
    timezone: 'Asia/Jakarta',
    document_id: null,
    ...over,
  };
}

function acc(over: Partial<RadiusAccountRow> = {}): RadiusAccountRow {
  return {
    id: 'acc-x',
    username: 'user01',
    kind: 'pppoe',
    state: 'suspended',
    credential_state: 'ready',
    service_id: 'svc-1',
    service_code: 'SVC-1',
    customer_name: 'Pelanggan',
    package_name: 'Paket 20M',
    restricting_router_id: null,
    last_active_session_at: null,
    ...over,
  };
}

describe('billing-eligibility (TK-604/U10)', () => {
  it('suspended + ada invoice lunas + tanpa tertunggak → eligible', () => {
    const out = evaluateActivationCandidates(
      [acc()],
      [inv({ state: 'paid', paid_amount: '300000.00', outstanding: '0.00' })],
    );
    expect(out).toHaveLength(1);
    expect(out[0]?.eligibility).toBe('eligible');
    expect(out[0]?.lastPaidInvoice?.doc_number).toBe('INV-ns-202611-0001');
  });

  it('ada invoice open/partial → tidak eligible (outstanding)', () => {
    const out = evaluateActivationCandidates(
      [acc()],
      [
        inv({ state: 'paid', outstanding: '0.00', paid_amount: '300000.00' }),
        inv({ id: 'inv-2', state: 'open', period_index: 1, period_start: '2026-12-01', period_end: '2027-01-01' }),
      ],
    );
    expect(out[0]?.eligibility).toBe('outstanding');
    expect(out[0]?.outstandingTotal).toBe('300000.00');
  });

  it('tanpa invoice sama sekali → tidak eligible (bukan "sudah bayar")', () => {
    const out = evaluateActivationCandidates([acc()], []);
    expect(out[0]?.eligibility).toBe('no_paid_invoice');
  });

  it('invoice open saja (belum lunas) → didahulukan alasan outstanding', () => {
    const out = evaluateActivationCandidates([acc()], [inv({ state: 'open' })]);
    expect(out[0]?.eligibility).toBe('outstanding');
  });

  it('invoice layanan lain tidak memengaruhi kelayakan akun ini', () => {
    const out = evaluateActivationCandidates(
      [acc({ service_id: 'svc-1' })],
      [
        inv({ state: 'paid', outstanding: '0.00', paid_amount: '300000.00' }),
        inv({ service_id: 'svc-2', state: 'open', id: 'inv-other' }),
      ],
    );
    expect(out[0]?.eligibility).toBe('eligible');
  });

  it('partial dijumlahkan sebagai tertunggak; paid terbaru dipakai sebagai info', () => {
    const outstanding = outstandingByService([
      inv({ state: 'partial', paid_amount: '100000.00', outstanding: '200000.00' }),
      inv({ id: 'i2', state: 'open', period_index: 1, period_start: '2026-12-01', period_end: '2027-01-01', outstanding: '150000.00' }),
    ]);
    expect(outstanding.get('svc-1')).toBe(350000);
    const lastPaid = lastPaidInvoiceByService([
      inv({ state: 'paid', issued_at: '2026-10-01T00:00:00Z', outstanding: '0.00', paid_amount: '300000.00' }),
      inv({ id: 'i3', state: 'paid', issued_at: '2026-11-02T00:00:00Z', outstanding: '0.00', paid_amount: '300000.00' }),
    ]);
    expect(lastPaid.get('svc-1')?.id).toBe('i3');
  });

  it('akun non-suspended dievaluasi defensif — bukan eligible', () => {
    const out = evaluateActivationCandidates(
      [acc({ state: 'active' })],
      [inv({ state: 'paid', outstanding: '0.00', paid_amount: '300000.00' })],
    );
    expect(out[0]?.eligibility).toBe('no_paid_invoice');
  });
});
