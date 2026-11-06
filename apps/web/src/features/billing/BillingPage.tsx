import { useMemo, useRef, useState } from 'react';
import type { ChangeEvent, ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader, FilterBar } from '../../design-system/components/PageHeader';
import { Tabs, CursorPagination } from '../../design-system/primitives/Misc';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge, StatusBadge } from '../../design-system/components/StatusBadge';
import { ConfirmAction } from '../../design-system/components/Notices';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { Dialog } from '../../design-system/primitives/Dialog';
import { TextInput, SelectInput, TextArea, Field } from '../../design-system/primitives/Input';
import { invoiceStateTone, paymentStateTone, agingBucketTone } from '../../lib/statuses';
import { formatMoney, formatDateShort, formatDateTime } from '../../lib/format';
import { documentArtifactUrl } from '../../api/http';
import type { ApiError } from '../../api/http';
import { evaluateActivationCandidates, fetchAllPages } from '../../lib/billing-eligibility';
import type { InternetInvoice, InternetPayment } from '../../api/contracts';

/**
 * U09 — Tagihan dan Pembayaran (UI_UX.md §8, TK-604).
 * Tiga tab: Invoice · Pengajuan pembayaran · Pembayaran terverifikasi.
 * Verifikasi dana dua tahap (BIL-03) + dokumen PDF (TK-109) + aging (BIL-05).
 * Aktivasi SELALU tindakan manual terpisah di U10 — pembayaran tidak
 * mengaktifkan akun (PRODUCT §13).
 */
const PAGE_SIZE = 50;
const AGING_BUCKETS = ['not_due', 'current', 'd31_60', 'd61_90', 'd90_plus'] as const;

type BillingTab = 'invoices' | 'submissions' | 'verified';

export default function BillingPage({ tenantId }: { tenantId: string }): ReactNode {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const navigate = useNavigate();
  const { can } = useSession();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<Array<string | null>>([]);
  const [tab, setTab] = useState<BillingTab>('invoices');
  const [paymentStateFilter, setPaymentStateFilter] = useState<'submitted' | 'rejected'>('submitted');
  const [recordOpen, setRecordOpen] = useState(false);
  const [verifyTarget, setVerifyTarget] = useState<InternetPayment | null>(null);
  const [rejectTarget, setRejectTarget] = useState<InternetPayment | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [awaitingCount, setAwaitingCount] = useState<number | null>(null);

  const periodFrom = params.get('period_from') ?? '';
  const periodTo = params.get('period_to') ?? '';
  const invoiceState = params.get('invoice_state') ?? '';

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setCursor(null);
    setCursorHistory([]);
    setParams(next, { replace: true });
  };

  const goToPage = (next: string | null) => {
    setCursorHistory((h) => [...h, cursor]);
    setCursor(next);
  };
  const goPrevPage = () => {
    setCursorHistory((h) => {
      const prev = h[h.length - 1] ?? null;
      setCursor(prev);
      return h.slice(0, -1);
    });
  };
  const resetPaging = () => {
    setCursor(null);
    setCursorHistory([]);
  };

  /* ---------- Queries ---------- */

  const invoicesQ = useQuery({
    queryKey: ['billing-invoices', tenantId, { periodFrom, periodTo, invoiceState, cursor }],
    queryFn: () =>
      api.listInvoices(
        tenantId,
        {
          period_from: periodFrom || undefined,
          period_to: periodTo || undefined,
          state: (invoiceState || undefined) as InternetInvoice['state'] | undefined,
        },
        { cursor, limit: PAGE_SIZE },
      ),
  });

  const agingQ = useQuery({
    queryKey: ['billing-aging', tenantId],
    queryFn: () => api.getInvoiceAging(tenantId),
    enabled: tab === 'invoices',
  });

  const paymentsQ = useQuery({
    queryKey: ['billing-payments', tenantId, { tab, paymentStateFilter, cursor }],
    queryFn: () =>
      api.listPayments(
        tenantId,
        { state: tab === 'verified' ? 'verified' : paymentStateFilter },
        { cursor, limit: PAGE_SIZE },
      ),
    enabled: tab !== 'invoices',
  });

  const receiptsQ = useQuery({
    queryKey: ['billing-receipts', tenantId],
    queryFn: () => api.listDocuments(tenantId, { kind: 'receipt' }, { limit: 200 }),
    enabled: tab === 'verified',
  });

  /** Invoice yang dapat dialokasi (open/partial) untuk editor verifikasi. */
  const payableQ = useQuery({
    queryKey: ['billing-payable', tenantId],
    queryFn: async () => {
      const [open, partial] = await Promise.all([
        api.listInvoices(tenantId, { state: 'open' }, { limit: 200 }),
        api.listInvoices(tenantId, { state: 'partial' }, { limit: 200 }),
      ]);
      return [...open.items, ...partial.items];
    },
    enabled: verifyTarget !== null,
  });

  const receiptsByPayment = useMemo(() => {
    const map = new Map<string, string>();
    for (const doc of receiptsQ.data?.items ?? []) map.set(doc.ref_id, doc.id);
    return map;
  }, [receiptsQ.data]);

  /** Filter periode pembayaran: waktu penerimaan (submitted_at) — jujur, klien. */
  const paymentsInPeriod = useMemo(() => {
    const items = paymentsQ.data?.items ?? [];
    if (!periodFrom && !periodTo) return items;
    return items.filter((p) => {
      const day = p.submitted_at.slice(0, 10);
      if (periodFrom && day < periodFrom) return false;
      if (periodTo && day > periodTo) return false;
      return true;
    });
  }, [paymentsQ.data, periodFrom, periodTo]);

  /* ---------- Aksi ---------- */

  const act = async (fn: () => Promise<unknown>, okMsg: string) => {
    setBusy(true);
    try {
      const result = await fn();
      toast(okMsg, 'success');
      await queryClient.invalidateQueries({ queryKey: ['billing-payments'] });
      await queryClient.invalidateQueries({ queryKey: ['billing-invoices'] });
      await queryClient.invalidateQueries({ queryKey: ['billing-aging'] });
      await queryClient.invalidateQueries({ queryKey: ['billing-receipts'] });
      return result;
    } catch (err) {
      const e = err as ApiError;
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  /** Hitung layanan menunggu aktivasi setelah verifikasi (U09 → U10). */
  const countAwaitingActivation = async (): Promise<number> => {
    const [accounts, invoices] = await Promise.all([
      fetchAllPages((page) => api.listRadiusAccounts(tenantId, { state: 'suspended' }, page)),
      fetchAllPages((page) => api.listInvoices(tenantId, {}, page)),
    ]);
    const candidates = evaluateActivationCandidates(accounts, invoices);
    // Jumlah = kandidat billing-eligible saat ini (bukan hanya alokasi payment
    // ini) — jujur terhadap state terkini tenant.
    return candidates.filter((c) => c.eligibility === 'eligible').length;
  };

  /* ---------- Render ---------- */

  const invoiceColumns: Column<InternetInvoice>[] = [
    {
      key: 'doc',
      header: t('billing.col_invoice'),
      render: (inv) => (
        <div style={{ minWidth: 0 }}>
          <div className="mt-mono mt-small" style={{ fontWeight: 500 }}>
            {inv.doc_number}
          </div>
          {inv.document_id ? (
            <a
              className="mt-xs mt-small"
              href={documentArtifactUrl(tenantId, inv.document_id)}
              target="_blank"
              rel="noreferrer"
            >
              <Icon name="fileText" size={13} style={{ verticalAlign: -2 }} /> {t('billing.view_pdf')}
            </a>
          ) : null}
        </div>
      ),
    },
    {
      key: 'customer',
      header: t('billing.col_customer'),
      render: (inv) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 500 }}>{inv.customer_name}</div>
          <div className="mt-xs mt-muted mt-mono mt-small">{inv.service_code}</div>
        </div>
      ),
    },
    {
      key: 'period',
      header: t('billing.col_period'),
      render: (inv) => `${formatDateShort(inv.period_start, locale)} – ${formatDateShort(inv.period_end, locale)}`,
      hideOnMobile: true,
    },
    {
      key: 'due',
      header: t('billing.col_due'),
      render: (inv) => formatDateShort(inv.due_date, locale),
      hideOnMobile: true,
    },
    {
      key: 'state',
      header: t('billing.col_state'),
      render: (inv) => <EnumBadge group="invoice_state" value={inv.state} tone={invoiceStateTone(inv.state)} />,
    },
    {
      key: 'total',
      header: t('billing.col_total'),
      align: 'right',
      render: (inv) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{formatMoney(inv.total_amount, locale)}</span>,
    },
    {
      key: 'outstanding',
      header: t('billing.col_outstanding'),
      align: 'right',
      render: (inv) => (
        <span style={{ fontVariantNumeric: 'tabular-nums' }}>
          {inv.paid_amount !== '0.00' && Number(inv.outstanding) > 0
            ? `${formatMoney(inv.paid_amount, locale)} / ${formatMoney(inv.total_amount, locale)}`
            : formatMoney(inv.outstanding, locale)}
        </span>
      ),
    },
  ];

  const paymentColumns = (mode: 'review' | 'verified'): Column<InternetPayment>[] => {
    const cols: Column<InternetPayment>[] = [
      {
        key: 'amount',
        header: t('billing.col_amount'),
        render: (p) => (
          <span style={{ fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{formatMoney(p.amount, locale)}</span>
        ),
      },
      {
        key: 'method',
        header: t('billing.col_method'),
        render: (p) => <EnumBadge group="payment_method" value={p.method} tone="neutral" />,
      },
      {
        key: 'ref',
        header: t('billing.col_ref'),
        render: (p) => (
          <div>
            <div className="mt-mono mt-small">{p.external_ref ?? '—'}</div>
            <div className="mt-xs">
              {p.has_proof ? (
                <StatusBadge tone="info" label={t('billing.proof_available')} icon="fileText" />
              ) : (
                <span className="mt-xs mt-muted mt-small">{t('billing.proof_none')}</span>
              )}
            </div>
          </div>
        ),
        hideOnMobile: true,
      },
      {
        key: 'submitted',
        header: t('billing.col_submitted_at'),
        render: (p) => formatDateTime(p.submitted_at, locale),
        hideOnMobile: true,
      },
    ];
    if (mode === 'review') {
      cols.push({
        key: 'state',
        header: t('billing.col_state'),
        render: (p) =>
          p.state === 'rejected' ? (
            <div>
              <EnumBadge group="payment_state" value={p.state} tone={paymentStateTone(p.state)} />
              {p.rejected_reason ? <div className="mt-xs mt-muted mt-small">{p.rejected_reason}</div> : null}
            </div>
          ) : (
            <EnumBadge group="payment_state" value={p.state} tone={paymentStateTone(p.state)} />
          ),
      });
      cols.push({
        key: 'actions',
        header: '',
        render: (p) =>
          p.state === 'submitted' && can('payments.verify') ? (
            <div className="mt-row" style={{ gap: 'var(--mt-space-2)' }}>
              <Button variant="primary" size="sm" icon="check" onClick={() => setVerifyTarget(p)}>
                {t('billing.verify_cta')}
              </Button>
              <Button variant="danger" size="sm" onClick={() => setRejectTarget(p)}>
                {t('billing.reject_cta')}
              </Button>
            </div>
          ) : null,
      });
    } else {
      cols.push(
        {
          key: 'allocated',
          header: t('billing.col_allocated'),
          render: (p) => (
            <div>
              <div style={{ fontVariantNumeric: 'tabular-nums' }}>{formatMoney(p.allocated_amount, locale)}</div>
              {Number(p.credit) > 0 ? (
                <div className="mt-xs mt-small">
                  <StatusBadge tone="warning" label={t('billing.credit_note')} icon="info" />
                </div>
              ) : null}
            </div>
          ),
        },
        {
          key: 'verified',
          header: t('billing.col_verified_at'),
          render: (p) => (p.verified_at ? formatDateTime(p.verified_at, locale) : '—'),
          hideOnMobile: true,
        },
        {
          key: 'receipt',
          header: t('billing.col_receipt'),
          render: (p) => {
            const docId = receiptsByPayment.get(p.id);
            return docId ? (
              <a href={documentArtifactUrl(tenantId, docId)} target="_blank" rel="noreferrer">
                <Icon name="fileText" size={13} style={{ verticalAlign: -2 }} /> {t('billing.view_receipt')}
              </a>
            ) : (
              <span className="mt-xs mt-muted mt-small">—</span>
            );
          },
        },
      );
    }
    return cols;
  };

  const agingTotals = agingQ.data?.totals;

  return (
    <AppShell
      tenantId={tenantId}
      title={
        <PageHeader
          title={t('billing.title')}
          description={t('billing.desc')}
          actions={
            can('payments.verify') ? (
              <Button variant="primary" icon="plus" onClick={() => setRecordOpen(true)}>
                {t('billing.record_cta')}
              </Button>
            ) : undefined
          }
        />
      }
    >
      <div className="mt-stack">
        {/* Periode filter selalu terlihat (UI_UX.md §8) */}
        <FilterBar>
          <div className="mt-row" style={{ gap: 'var(--mt-space-2)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <TextInput
              type="date"
              label={t('billing.period_from')}
              value={periodFrom}
              onChange={(e) => setParam('period_from', e.target.value)}
            />
            <TextInput
              type="date"
              label={t('billing.period_to')}
              value={periodTo}
              onChange={(e) => setParam('period_to', e.target.value)}
            />
            {tab === 'invoices' ? (
              <SelectInput
                label={t('billing.filter_state')}
                value={invoiceState}
                onChange={(e) => setParam('invoice_state', e.target.value)}
                placeholderOption={t('billing.state_all')}
                options={[
                  { value: 'open', label: t('enums.invoice_state.open') },
                  { value: 'partial', label: t('enums.invoice_state.partial') },
                  { value: 'paid', label: t('enums.invoice_state.paid') },
                  { value: 'void', label: t('enums.invoice_state.void') },
                ]}
              />
            ) : null}
          </div>
        </FilterBar>

        {awaitingCount !== null ? (
          <div className="mt-banner mt-banner-info" role="status">
            <Icon name="checkCircle" size={18} style={{ flexShrink: 0 }} />
            <div>
              <strong>{t('billing.verified_recorded')}</strong>{' '}
              {t('billing.awaiting_activation', { count: awaitingCount })}{' '}
              <Button
                variant="secondary"
                size="sm"
                iconRight="arrowRight"
                onClick={() => navigate(`/app/${tenantId}/activation`)}
              >
                {t('billing.open_activation')}
              </Button>
            </div>
          </div>
        ) : null}

        <Tabs
          ariaLabel={t('billing.tabs_label')}
          active={tab}
          onChange={(v) => {
            setTab(v as BillingTab);
            resetPaging();
          }}
          items={[
            { id: 'invoices', label: t('billing.tab_invoices') },
            { id: 'submissions', label: t('billing.tab_submissions') },
            { id: 'verified', label: t('billing.tab_verified') },
          ]}
        />

        {tab === 'invoices' ? (
          <>
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
              {AGING_BUCKETS.map((bucket) => (
                <div key={bucket} className="mt-card mt-card-pad" style={{ padding: 'var(--mt-space-3)' }}>
                  <div className="mt-xs mt-muted mt-small">
                    <StatusBadge
                      tone={agingBucketTone(bucket)}
                      label={t(`enums.aging_bucket.${bucket}` as never, undefined as never)}
                      icon="hash"
                    />
                  </div>
                  <div style={{ fontSize: 'var(--mt-text-lg)', fontWeight: 600, marginTop: 'var(--mt-space-2)' }}>
                    {agingTotals?.[bucket]?.count ?? '—'}
                  </div>
                  <div className="mt-xs mt-muted mt-small" style={{ fontVariantNumeric: 'tabular-nums' }}>
                    {agingTotals ? formatMoney(agingTotals[bucket].outstanding, locale) : '—'}
                  </div>
                </div>
              ))}
            </div>
            <DataTable
              rows={invoicesQ.data?.items ?? []}
              columns={invoiceColumns}
              rowKey={(inv) => inv.id}
              loading={invoicesQ.isLoading}
              error={invoicesQ.error ? t('common.error_generic') : undefined}
              emptyTitle={t('billing.empty_invoices')}
              emptyDescription={t('billing.empty_invoices_desc')}
              caption={t('billing.table_caption_invoices')}
            />
            <CursorPagination
              hasNext={Boolean(invoicesQ.data?.next_cursor)}
              hasPrev={cursorHistory.length > 0}
              onNext={() => goToPage(invoicesQ.data?.next_cursor ?? null)}
              onPrev={goPrevPage}
              loading={invoicesQ.isLoading}
              rangeLabel={t('common.page_info', { count: invoicesQ.data?.items.length ?? 0 })}
            />
          </>
        ) : null}

        {tab === 'submissions' ? (
          <>
            <div className="mt-row" style={{ gap: 'var(--mt-space-2)' }}>
              {(['submitted', 'rejected'] as const).map((s) => (
                <Button
                  key={s}
                  variant={paymentStateFilter === s ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => {
                    setPaymentStateFilter(s);
                    resetPaging();
                  }}
                >
                  {t(`enums.payment_state.${s}` as never, undefined as never)}
                </Button>
              ))}
            </div>
            <DataTable
              rows={paymentsInPeriod}
              columns={paymentColumns('review')}
              rowKey={(p) => p.id}
              loading={paymentsQ.isLoading}
              error={paymentsQ.error ? t('common.error_generic') : undefined}
              emptyTitle={
                paymentStateFilter === 'submitted' ? t('billing.empty_submissions') : t('billing.empty_rejected')
              }
              emptyDescription={t('billing.empty_submissions_desc')}
              caption={t('billing.table_caption_payments')}
            />
            <CursorPagination
              hasNext={Boolean(paymentsQ.data?.next_cursor)}
              hasPrev={cursorHistory.length > 0}
              onNext={() => goToPage(paymentsQ.data?.next_cursor ?? null)}
              onPrev={goPrevPage}
              loading={paymentsQ.isLoading}
              rangeLabel={t('common.page_info', { count: paymentsQ.data?.items.length ?? 0 })}
            />
          </>
        ) : null}

        {tab === 'verified' ? (
          <>
            <DataTable
              rows={paymentsInPeriod}
              columns={paymentColumns('verified')}
              rowKey={(p) => p.id}
              loading={paymentsQ.isLoading}
              error={paymentsQ.error ? t('common.error_generic') : undefined}
              emptyTitle={t('billing.empty_verified')}
              emptyDescription={t('billing.empty_verified_desc')}
              caption={t('billing.table_caption_verified')}
            />
            <CursorPagination
              hasNext={Boolean(paymentsQ.data?.next_cursor)}
              hasPrev={cursorHistory.length > 0}
              onNext={() => goToPage(paymentsQ.data?.next_cursor ?? null)}
              onPrev={goPrevPage}
              loading={paymentsQ.isLoading}
              rangeLabel={t('common.page_info', { count: paymentsQ.data?.items.length ?? 0 })}
            />
          </>
        ) : null}

        <p className="mt-xs mt-muted mt-small">
          {tab === 'invoices' ? t('billing.period_note_invoices') : t('billing.period_note_payments')}
        </p>
      </div>

      <RecordPaymentDialog
        open={recordOpen}
        onClose={() => setRecordOpen(false)}
        busy={busy}
        onSubmit={async (input) => {
          const created = await act(() => api.recordInternetPayment(tenantId, input), t('billing.record_ok'));
          if (created) setRecordOpen(false);
        }}
      />

      <VerifyPaymentDialog
        payment={verifyTarget}
        payableInvoices={payableQ.data ?? []}
        loading={payableQ.isLoading}
        busy={busy}
        onClose={() => setVerifyTarget(null)}
        onConfirm={async (allocations) => {
          if (!verifyTarget) return;
          const detail = await act(
            () => api.verifyInternetPayment(tenantId, verifyTarget.id, { allocations }),
            t('billing.verify_ok'),
          );
          if (detail) {
            setVerifyTarget(null);
            setAwaitingCount(await countAwaitingActivation());
          }
        }}
      />

      <ConfirmAction
        open={rejectTarget !== null}
        onClose={() => {
          setRejectTarget(null);
          setRejectReason('');
        }}
        onConfirm={async () => {
          if (!rejectTarget) return;
          const ok = await act(
            () => api.rejectInternetPayment(tenantId, rejectTarget.id, rejectReason),
            t('billing.reject_ok'),
          );
          if (ok !== undefined) {
            setRejectTarget(null);
            setRejectReason('');
          }
        }}
        loading={busy}
        title={t('billing.reject_title')}
        intent={t('billing.reject_intent')}
        scopeLines={[t('billing.reason_required_note')]}
        confirmLabel={t('billing.reject_cta')}
        confirmTone="danger"
      >
        <TextArea
          label={t('billing.reject_reason_label')}
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          required
        />
      </ConfirmAction>
    </AppShell>
  );
}

/* ---------- Dialog catat penerimaan (BIL-03 tahap 1) ---------- */

function RecordPaymentDialog({
  open,
  onClose,
  onSubmit,
  busy,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (input: {
    method: 'cash' | 'bank_transfer' | 'ewallet' | 'collector_cash';
    amount: string;
    external_ref?: string;
    collector_display?: string;
    file_b64?: string;
    mime?: string;
  }) => Promise<void>;
  busy: boolean;
}): ReactNode {
  const t = useT();
  const [method, setMethod] = useState<'cash' | 'bank_transfer' | 'ewallet' | 'collector_cash'>('cash');
  const [amount, setAmount] = useState('');
  const [externalRef, setExternalRef] = useState('');
  const [collector, setCollector] = useState('');
  const [proof, setProof] = useState<{ file_b64: string; mime: string } | null>(null);
  const [proofError, setProofError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const needsProof = method === 'bank_transfer' || method === 'ewallet';

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    setProofError(null);
    if (!f) {
      setProof(null);
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setProofError(t('billing.record_proof_too_large'));
      setProof(null);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? '');
      const b64 = result.includes(',') ? (result.split(',')[1] ?? result) : result;
      setProof({ file_b64: b64, mime: f.type });
    };
    reader.onerror = () => setProofError(t('common.error_generic'));
    reader.readAsDataURL(f);
  };

  const reset = () => {
    setMethod('cash');
    setAmount('');
    setExternalRef('');
    setCollector('');
    setProof(null);
    setProofError(null);
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <Dialog
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title={t('billing.record_title')}
      footer={
        <>
          <Button
            variant="secondary"
            onClick={() => {
              reset();
              onClose();
            }}
            disabled={busy}
          >
            {t('common.cancel')}
          </Button>
          <Button
            variant="primary"
            loading={busy}
            disabled={!amount || Number(amount) <= 0 || (needsProof && !proof)}
            onClick={() => {
              void onSubmit({
                method,
                amount,
                external_ref: externalRef || undefined,
                collector_display: method === 'collector_cash' && collector ? collector : undefined,
                file_b64: proof?.file_b64,
                mime: proof?.mime,
              }).then(() => reset());
            }}
          >
            {t('billing.record_submit')}
          </Button>
        </>
      }
    >
      <div className="mt-stack-sm">
        <SelectInput
          label={t('billing.record_method')}
          value={method}
          onChange={(e) => setMethod(e.target.value as typeof method)}
          required
          options={[
            { value: 'cash', label: t('enums.payment_method.cash') },
            { value: 'bank_transfer', label: t('enums.payment_method.bank_transfer') },
            { value: 'ewallet', label: t('enums.payment_method.ewallet') },
            { value: 'collector_cash', label: t('enums.payment_method.collector_cash') },
          ]}
        />
        <TextInput
          type="number"
          min={1}
          step="any"
          inputMode="decimal"
          label={t('billing.record_amount')}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          required
        />
        <TextInput
          label={t('billing.record_external_ref')}
          helper={t('billing.record_ref_help')}
          value={externalRef}
          onChange={(e) => setExternalRef(e.target.value)}
        />
        {method === 'collector_cash' ? (
          <TextInput
            label={t('billing.record_collector')}
            value={collector}
            onChange={(e) => setCollector(e.target.value)}
          />
        ) : null}
        {needsProof ? (
          <Field
            label={t('billing.record_proof')}
            helper={t('billing.record_proof_help')}
            error={proofError ?? undefined}
            required
          >
            {() => (
              <input
                ref={fileRef}
                type="file"
                className="mt-input"
                accept=".png,.jpg,.jpeg,.webp,.pdf"
                onChange={onFile}
              />
            )}
          </Field>
        ) : null}
      </div>
    </Dialog>
  );
}

/* ---------- Dialog verifikasi dana (BIL-03 tahap 2 + alokasi) ---------- */

function VerifyPaymentDialog({
  payment,
  payableInvoices,
  loading,
  busy,
  onClose,
  onConfirm,
}: {
  payment: InternetPayment | null;
  payableInvoices: InternetInvoice[];
  loading: boolean;
  busy: boolean;
  onClose: () => void;
  onConfirm: (allocations: Array<{ invoice_id: string; amount: string }>) => Promise<void>;
}): ReactNode {
  const t = useT();
  const locale = useActiveLocale();
  const [allocs, setAllocs] = useState<Map<string, { selected: boolean; amount: string }>>(new Map());

  // Reset editor tiap payment berbeda dibuka (derived-state reset pattern).
  const pid = payment?.id ?? null;
  const lastPid = useRef<string | null>(null);
  if (pid !== lastPid.current) {
    lastPid.current = pid;
    setAllocs(new Map());
  }

  const rows = payableInvoices.map((inv) => {
    const st = allocs.get(inv.id);
    return { invoice: inv, selected: st?.selected ?? false, amount: st?.amount ?? inv.outstanding };
  });
  const selectedRows = rows.filter((r) => r.selected);
  const allocatedTotal = selectedRows.reduce((s, r) => s + Number(r.amount || 0), 0);
  const paymentAmount = Number(payment?.amount ?? 0);
  const remaining = paymentAmount - allocatedTotal;
  const exceeds = remaining < -0.005;

  const toggle = (inv: InternetInvoice, checked: boolean) => {
    setAllocs((prev) => {
      const next = new Map(prev);
      let amount = (next.get(inv.id) ?? { selected: false, amount: inv.outstanding }).amount;
      if (checked) {
        // Default: min(sisa tagihan, sisa payment) — tidak melebihi keduanya.
        const rem =
          paymentAmount -
          [...next.entries()].reduce(
            (s, [id, v]) => (v.selected && id !== inv.id ? s + Number(v.amount || 0) : s),
            0,
          );
        amount = String(Math.min(Number(inv.outstanding), Math.max(0, rem)));
      }
      next.set(inv.id, { selected: checked, amount });
      return next;
    });
  };

  const setAllocAmount = (inv: InternetInvoice, raw: string) => {
    setAllocs((prev) => {
      const next = new Map(prev);
      const cur = next.get(inv.id) ?? { selected: true, amount: inv.outstanding };
      next.set(inv.id, { ...cur, amount: raw });
      return next;
    });
  };

  return (
    <ConfirmAction
      open={payment !== null}
      onClose={onClose}
      onConfirm={() => {
        if (exceeds) return;
        void onConfirm(
          selectedRows.map((r) => ({ invoice_id: r.invoice.id, amount: Number(r.amount || 0).toFixed(2) })),
        );
      }}
      loading={busy}
      title={t('billing.verify_title')}
      intent={
        payment
          ? t('billing.verify_intent', {
              method: t(`enums.payment_method.${payment.method}` as never, undefined as never),
              amount: formatMoney(payment.amount, locale),
              ref: payment.external_ref ?? t('billing.no_ref'),
              date: formatDateTime(payment.submitted_at, locale),
            })
          : ''
      }
      scopeLines={[t('billing.verify_scope_bank'), t('billing.verify_scope_manual')]}
      confirmLabel={t('billing.verify_cta')}
    >
      <div className="mt-stack-sm">
        <h3 style={{ fontSize: 'var(--mt-text-base)', margin: 0 }}>{t('billing.verify_allocations')}</h3>
        <p className="mt-xs mt-muted mt-small" style={{ margin: 0 }}>
          {t('billing.verify_alloc_help')}
        </p>
        {loading ? (
          <p className="mt-small mt-muted">{t('common.loading')}</p>
        ) : rows.length === 0 ? (
          <p className="mt-small mt-muted">{t('billing.verify_no_invoices')}</p>
        ) : (
          <div className="mt-stack-sm" style={{ maxHeight: 260, overflowY: 'auto' }}>
            {rows.map(({ invoice, selected, amount }) => (
              <label
                key={invoice.id}
                className="mt-card mt-card-pad"
                style={{
                  display: 'flex',
                  gap: 'var(--mt-space-2)',
                  alignItems: 'center',
                  padding: 'var(--mt-space-2)',
                  cursor: 'pointer',
                }}
              >
                <input type="checkbox" checked={selected} onChange={(e) => toggle(invoice, e.target.checked)} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="mt-mono mt-small">{invoice.doc_number}</div>
                  <div className="mt-xs mt-muted mt-small">
                    {invoice.customer_name} ·{' '}
                    {t('billing.remaining_label', { amount: formatMoney(invoice.outstanding, locale) })}
                  </div>
                </div>
                <input
                  type="number"
                  min={0}
                  step="any"
                  inputMode="decimal"
                  className="mt-input"
                  value={selected ? amount : ''}
                  disabled={!selected}
                  onChange={(e) => setAllocAmount(invoice, e.target.value)}
                  aria-label={t('billing.alloc_amount_label', { invoice: invoice.doc_number })}
                  style={{ maxWidth: 130 }}
                />
              </label>
            ))}
          </div>
        )}
        <p className="mt-small" style={{ margin: 0 }}>
          {exceeds ? (
            <span className="mt-banner mt-banner-danger" style={{ marginBottom: 0 }}>
              <Icon name="alertCircle" size={16} style={{ flexShrink: 0 }} /> {t('billing.verify_alloc_exceeds')}
            </span>
          ) : (
            <span className="mt-muted">
              {t('billing.verify_remaining', { amount: formatMoney(Math.max(0, remaining), locale) })}
            </span>
          )}
        </p>
      </div>
    </ConfirmAction>
  );
}
