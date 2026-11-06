import { beforeEach, describe, expect, it } from 'vitest';
import { MockApiClient } from './mock/adapter';

/**
 * Adapter mock — kontrak perilaku billing M6 (paritas backend TK-601):
 * dua tahap record→verify, alokasi dibatasi, kwitansi terbit saat verify,
 * keputusan ganda 409, alasan wajib saat menolak, filter invoice.
 */
const T = 'b3f0a2de-1111-4000-8000-tenant01';

describe('MockApiClient billing (U09)', () => {
  let api: MockApiClient;

  beforeEach(async () => {
    api = new MockApiClient();
    await api.login('huda@example.dev', 'password-12-char');
    await api.loginTotp('123456');
    await api.switchTenant(T);
  });

  it('listInvoices memfilter state dan periode', async () => {
    const all = await api.listInvoices(T, {}, { limit: 50 });
    expect(all.items.length).toBeGreaterThanOrEqual(4);
    const paid = await api.listInvoices(T, { state: 'paid' }, { limit: 50 });
    expect(paid.items.every((i) => i.state === 'paid')).toBe(true);
    const nov = await api.listInvoices(T, { period_from: '2026-11-01', period_to: '2026-11-30' }, { limit: 50 });
    expect(nov.items.every((i) => i.period_start >= '2026-11-01' && i.period_end <= '2026-11-30')).toBe(true);
  });

  it('record → submitted; tunai tanpa bukti ok; transfer tanpa bukti ditolak', async () => {
    const pay = await api.recordInternetPayment(T, { method: 'cash', amount: '300000' });
    expect(pay.state).toBe('submitted');
    expect(pay.has_proof).toBe(false);
    await expect(
      api.recordInternetPayment(T, { method: 'bank_transfer', amount: '100000' }),
    ).rejects.toMatchObject({ code: 'validation_error' });
  });

  it('verify: alokasi penuh melunasi invoice + kwitansi terbit; kredit bila sisa', async () => {
    const pay = await api.recordInternetPayment(T, { method: 'cash', amount: '300000' });
    const inv = (await api.listInvoices(T, { state: 'open' }, { limit: 50 })).items[0]!;
    const detail = await api.verifyInternetPayment(T, pay.id, {
      allocations: [{ invoice_id: inv.id, amount: inv.outstanding }],
    });
    expect(detail.state).toBe('verified');
    expect(detail.allocations[0]?.invoice_id).toBe(inv.id);
    const after = await api.getInvoice(T, inv.id);
    expect(after.state).toBe('paid');
    expect(after.outstanding).toBe('0.00');
    const docs = await api.listDocuments(T, { kind: 'receipt', ref_type: 'billing_payment', ref_id: pay.id }, {});
    expect(docs.items[0]?.ref_id).toBe(pay.id);
  });

  it('verify dengan alokasi kosong → kredit penuh (kwitansi tetap terbit)', async () => {
    const pay = await api.recordInternetPayment(T, { method: 'cash', amount: '50000' });
    const detail = await api.verifyInternetPayment(T, pay.id, { allocations: [] });
    expect(detail.state).toBe('verified');
    expect(detail.credit).toBe('50000.00');
    const docs = await api.listDocuments(T, { kind: 'receipt', ref_id: pay.id }, {});
    expect(docs.items).toHaveLength(1);
  });

  it('alokasi melebihi pembayaran / sisa tagihan → conflict', async () => {
    const pay = await api.recordInternetPayment(T, { method: 'cash', amount: '100000' });
    const inv = (await api.listInvoices(T, { state: 'open' }, { limit: 50 })).items[0]!;
    await expect(
      api.verifyInternetPayment(T, pay.id, { allocations: [{ invoice_id: inv.id, amount: '999999' }] }),
    ).rejects.toMatchObject({ code: 'conflict' });
    // Alokasi > sisa tagihan invoice juga ditolak.
    const pay2 = await api.recordInternetPayment(T, { method: 'cash', amount: '999999' });
    await expect(
      api.verifyInternetPayment(T, pay2.id, { allocations: [{ invoice_id: inv.id, amount: '999999' }] }),
    ).rejects.toMatchObject({ code: 'conflict' });
  });

  it('keputusan ganda → conflict; tolak wajib alasan', async () => {
    const pay = await api.recordInternetPayment(T, { method: 'cash', amount: '10000' });
    await api.verifyInternetPayment(T, pay.id, { allocations: [] });
    await expect(api.verifyInternetPayment(T, pay.id, { allocations: [] })).rejects.toMatchObject({ code: 'conflict' });
    await expect(api.rejectInternetPayment(T, pay.id, 'alasan')).rejects.toMatchObject({ code: 'conflict' });

    const pay2 = await api.recordInternetPayment(T, { method: 'cash', amount: '10000' });
    await expect(api.rejectInternetPayment(T, pay2.id, '  ')).rejects.toMatchObject({ code: 'validation_error' });
    const rejected = await api.rejectInternetPayment(T, pay2.id, 'Nominal tidak cocok');
    expect(rejected.state).toBe('rejected');
    expect(rejected.rejected_reason).toBe('Nominal tidak cocok');
  });

  it('akun suspended diaktifkan → tidak lagi muncul di daftar suspended', async () => {
    const before = await api.listRadiusAccounts(T, { state: 'suspended' }, { limit: 200 });
    expect(before.items.length).toBeGreaterThan(0);
    const target = before.items[0]!;
    await api.activateRadiusAccount(T, target.id);
    const after = await api.listRadiusAccounts(T, { state: 'suspended' }, { limit: 200 });
    expect(after.items.find((a) => a.id === target.id)).toBeUndefined();
    // Aktivasi ulang state sama → idempoten (paritas backend 204).
    await expect(api.activateRadiusAccount(T, target.id)).resolves.toBeUndefined();
  });
});
