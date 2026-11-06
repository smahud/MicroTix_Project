/**
 * Kelayakan aktivasi massal (TK-604 / U10 — ACT-05, UX-04).
 *
 * Aturan jujur berbasis data billing nyata (TK-601), dihitung di sisi klien
 * dari daftar invoice + akun akses (bukan field turunan beta):
 * - Layak  : akun suspended + layanan punya ≥1 invoice LUNAS + tidak ada
 *   invoice open/partial (tidak ada tagihan tertunggak).
 * - "Sudah bayar menunggu aktivasi" berarti benar-benar sudah dibayar —
 *   akun suspended tanpa tagihan lunas bukan kandidat billing-eligible.
 * - Validasi kegunaan tetap ditegakkan server per item (PATCH state
 *   transition + izin services.activate); modul ini hanya presentasi.
 */
import type { InternetInvoice, RadiusAccountRow, CursorPage } from '../api/contracts';
import type { PageParams } from '../api/http';

/**
 * Ambil seluruh halaman kursor (maks. `maxPages`) — kelayakan U10 harus
 * melihat invoice tertunggak LEBIH DARI halaman pertama; dibatasi agar tetap
 * terukur (jujur: data di luar batas tidak dinilai).
 */
export async function fetchAllPages<T>(
  fetchPage: (page: PageParams) => Promise<CursorPage<T>>,
  maxPages = 10,
): Promise<T[]> {
  const out: T[] = [];
  let cursor: string | null = null;
  for (let i = 0; i < maxPages; i++) {
    const page = await fetchPage({ cursor, limit: 200 });
    out.push(...page.items);
    if (!page.next_cursor) break;
    cursor = page.next_cursor;
  }
  return out;
}

export type ActivationEligibility = 'eligible' | 'outstanding' | 'no_paid_invoice';

export interface ActivationCandidate {
  account: RadiusAccountRow;
  eligibility: ActivationEligibility;
  /** Total tagihan tertunggak (open/partial) milik layanan akun ini. */
  outstandingTotal: string;
  /** Invoice lunas terakhir layanan (info tampilan). */
  lastPaidInvoice: InternetInvoice | null;
}

function money(n: number): string {
  return n.toFixed(2);
}

/** Sum outstanding invoice open/partial per service_id. */
export function outstandingByService(invoices: InternetInvoice[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const inv of invoices) {
    if (inv.state === 'open' || inv.state === 'partial') {
      map.set(inv.service_id, (map.get(inv.service_id) ?? 0) + Number(inv.outstanding));
    }
  }
  return map;
}

/** Invoice lunas terakhir per service_id (urut issued_at terbaru). */
export function lastPaidInvoiceByService(invoices: InternetInvoice[]): Map<string, InternetInvoice> {
  const map = new Map<string, InternetInvoice>();
  const paid = invoices
    .filter((i) => i.state === 'paid')
    .sort((a, b) => b.issued_at.localeCompare(a.issued_at));
  for (const inv of paid) {
    if (!map.has(inv.service_id)) map.set(inv.service_id, inv);
  }
  return map;
}

/**
 * Evaluasi daftar kandidat aktivasi dari akun suspended + invoice tenant.
 * Akun non-suspended tetap dievaluasi defensif (dianggap bukan kandidat
 * billing-eligible) — pemanggil memfilter state di query.
 */
export function evaluateActivationCandidates(
  accounts: RadiusAccountRow[],
  invoices: InternetInvoice[],
): ActivationCandidate[] {
  const outstanding = outstandingByService(invoices);
  const lastPaid = lastPaidInvoiceByService(invoices);
  return accounts.map((account) => {
    const out = outstanding.get(account.service_id) ?? 0;
    const paid = lastPaid.get(account.service_id) ?? null;
    let eligibility: ActivationEligibility;
    if (account.state !== 'suspended') {
      // Bukan kandidat isolir-aktivasi (aktif/hold) — blokir jujur.
      eligibility = 'no_paid_invoice';
    } else if (out > 0) {
      eligibility = 'outstanding';
    } else if (!paid) {
      eligibility = 'no_paid_invoice';
    } else {
      eligibility = 'eligible';
    }
    return { account, eligibility, outstandingTotal: money(out), lastPaidInvoice: paid };
  });
}

export function isEligible(c: ActivationCandidate): boolean {
  return c.eligibility === 'eligible';
}
