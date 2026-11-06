import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge, StatusBadge } from '../../design-system/components/StatusBadge';
import { BulkActionBar } from '../../design-system/components/DataParts';
import { ConfirmAction } from '../../design-system/components/Notices';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { accountStateTone } from '../../lib/statuses';
import { formatMoney, formatDateShort } from '../../lib/format';
import type { ApiError } from '../../api/http';
import { evaluateActivationCandidates, fetchAllPages } from '../../lib/billing-eligibility';
import type { ActivationCandidate } from '../../lib/billing-eligibility';
import type { RadiusAccountRow } from '../../api/contracts';

/**
 * U10 — Kelayakan dan hasil aktivasi massal (UI_UX.md §8, TK-604, ACT-05/UX-04).
 *
 * - Aktivasi SELALU tindakan manual terpisah dari pembayaran (PRODUCT §13).
 * - Snapshot seleksi dibekukan pada konfirmasi; kondisi TERBARU (state akun +
 *   pembayaran) divalidasi ulang per item SEBELUM eksekusi.
 * - Item asing/berubah memblokir item itu saja — keberhasilan valid tidak
 *   diurungkan (TK-604 done_when).
 * - Hasil per item: Berhasil / Perlu tinjau / Gagal; retry hanya item gagal.
 * - Label jujur NAS: router belum Otoritatif → "belum dijamin di router ini".
 */
type ItemOutcome = 'success' | 'changed' | 'failed';

interface ActivationResult {
  candidate: ActivationCandidate;
  outcome: ItemOutcome;
  message?: string;
}

export default function ActivationPage({ tenantId }: { tenantId: string }): ReactNode {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { can } = useSession();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ActivationResult[] | null>(null);

  const accountsQ = useQuery({
    queryKey: ['radius-accounts', tenantId, 'suspended'],
    queryFn: () => fetchAllPages((page) => api.listRadiusAccounts(tenantId, { state: 'suspended' }, page)),
  });
  const invoicesQ = useQuery({
    queryKey: ['billing-invoices', tenantId, 'all'],
    queryFn: () => fetchAllPages((page) => api.listInvoices(tenantId, {}, page)),
  });
  const routerStatusQ = useQuery({
    queryKey: ['radius-status', tenantId],
    queryFn: () => api.listRadiusRouterStatus(tenantId),
  });

  const candidates = useMemo(
    () => evaluateActivationCandidates(accountsQ.data ?? [], invoicesQ.data ?? []),
    [accountsQ.data, invoicesQ.data],
  );

  /** Router pembatas HANYA dijamin bila terdaftar dan Otoritatif (§8).
   *  Router tak terdaftar/tidak dikenal → belum dijamin (unknown ≠ guaranteed). */
  const isUnguaranteed = useMemo(() => {
    const authoritative = new Set(
      (routerStatusQ.data ?? [])
        .filter((r) => r.enforcement_mode === 'radius_authoritative')
        .map((r) => r.router_id),
    );
    return (routerId: string | null): boolean => routerId == null || !authoritative.has(routerId);
  }, [routerStatusQ.data]);

  const eligibleCount = candidates.filter((c) => c.eligibility === 'eligible').length;
  const selectedCandidates = candidates.filter((c) => selected.has(c.account.id));
  const selectedEligible = selectedCandidates.filter((c) => c.eligibility === 'eligible').length;
  const selectedNotEligible = selectedCandidates.length - selectedEligible;

  const toggleSelect = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  /** Eksekusi per item: validasi kondisi TERBARU → PATCH → hasil per item. */
  const runActivation = async (items: ActivationCandidate[]) => {
    setRunning(true);
    const fresh: ActivationResult[] = [];
    try {
      // Validasi kondisi terbaru SEBELUM eksekusi (UX-04): akun + pembayaran
      // diambil ulang — bukan memakai snapshot layar.
      const [freshAccounts, freshInvoices] = await Promise.all([
        fetchAllPages((page) => api.listRadiusAccounts(tenantId, { state: 'suspended' }, page)),
        fetchAllPages((page) => api.listInvoices(tenantId, {}, page)),
      ]);
      const freshById = new Map<string, RadiusAccountRow>(freshAccounts.map((a) => [a.id, a]));
      const freshEligibility = new Map(
        evaluateActivationCandidates(freshAccounts, freshInvoices).map((c) => [
          c.account.id,
          c.eligibility,
        ]),
      );
      for (const item of items) {
        const current = freshById.get(item.account.id);
        if (!current || current.state !== 'suspended') {
          // Item asing/berubah → blokir item ini saja (done_when TK-604).
          fresh.push({ candidate: item, outcome: 'changed' });
          continue;
        }
        if (freshEligibility.get(item.account.id) !== 'eligible') {
          fresh.push({ candidate: item, outcome: 'changed' });
          continue;
        }
        try {
          await api.activateRadiusAccount(tenantId, item.account.id);
          fresh.push({ candidate: item, outcome: 'success' });
        } catch (err) {
          const e = err as ApiError;
          fresh.push({ candidate: item, outcome: 'failed', message: e.envelope?.message });
        }
      }
    } catch (err) {
      const e = err as ApiError;
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
      return;
    } finally {
      setRunning(false);
    }
    setResults(fresh);
    setSelected(new Set());
    await queryClient.invalidateQueries({ queryKey: ['radius-accounts'] });
    await queryClient.invalidateQueries({ queryKey: ['services'] });
    const ok = fresh.filter((r) => r.outcome === 'success').length;
    const blocked = fresh.length - ok;
    if (blocked === 0) toast(t('activation.finished_toast', { count: ok }), 'success');
    else toast(t('activation.partial_toast', { ok, blocked }), 'warning');
  };

  const columns: Column<ActivationCandidate>[] = [
    {
      key: 'customer',
      header: t('activation.col_customer'),
      render: (c) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 500 }}>{c.account.customer_name}</div>
          <div className="mt-xs mt-muted mt-mono mt-small">
            {c.account.service_code} · {c.account.username}
          </div>
        </div>
      ),
    },
    {
      key: 'package',
      header: t('activation.col_package'),
      render: (c) => c.account.package_name ?? <span className="mt-xs mt-muted">{t('common.not_set')}</span>,
      hideOnMobile: true,
    },
    {
      key: 'state',
      header: t('activation.col_state'),
      render: (c) => (
        <EnumBadge group="account_state" value={c.account.state} tone={accountStateTone(c.account.state)} />
      ),
    },
    {
      key: 'billing',
      header: t('activation.col_billing'),
      render: (c) => {
        if (c.eligibility === 'eligible') {
          return (
            <div>
              <StatusBadge tone="success" label={t('activation.eligible_badge')} icon="checkCircle" />
              <div className="mt-xs mt-muted mt-small">
                {c.lastPaidInvoice
                  ? t('activation.last_paid', {
                      invoice: c.lastPaidInvoice.doc_number,
                      date: formatDateShort(c.lastPaidInvoice.issued_at, locale),
                    })
                  : null}
              </div>
            </div>
          );
        }
        if (c.eligibility === 'outstanding') {
          return (
            <div>
              <StatusBadge tone="warning" label={t('activation.reason_outstanding')} icon="alertTriangle" />
              <div className="mt-xs mt-muted mt-small">
                {t('activation.outstanding_amount', { amount: formatMoney(c.outstandingTotal, locale) })}
              </div>
            </div>
          );
        }
        return <StatusBadge tone="neutral" label={t('activation.reason_no_paid')} icon="hash" />;
      },
    },
    {
      key: 'router',
      header: t('activation.col_router'),
      render: (c) =>
        isUnguaranteed(c.account.restricting_router_id) ? (
          <span className="mt-xs mt-muted mt-small" title={t('activation.not_guaranteed')}>
            <Icon name="alertTriangle" size={13} style={{ verticalAlign: -2 }} />{' '}
            {t('activation.not_guaranteed_short')}
          </span>
        ) : (
          <span className="mt-xs mt-small">{t('activation.guaranteed')}</span>
        ),
      hideOnMobile: true,
    },
  ];

  const resultTone = (o: ItemOutcome) => (o === 'success' ? 'success' : o === 'changed' ? 'warning' : 'danger');

  return (
    <AppShell
      tenantId={tenantId}
      title={
        <PageHeader
          title={t('activation.title')}
          description={t('activation.desc')}
          meta={
            <span className="mt-small">
              {t('activation.counts', { eligible: eligibleCount, total: candidates.length })}
            </span>
          }
        />
      }
    >
      <div className="mt-stack">
        <div className="mt-banner mt-banner-info">
          <Icon name="info" size={18} style={{ flexShrink: 0 }} />
          <span className="mt-small">{t('activation.manual_note')}</span>
        </div>

        <DataTable
          rows={candidates}
          columns={columns}
          rowKey={(c) => c.account.id}
          loading={accountsQ.isLoading || invoicesQ.isLoading}
          error={accountsQ.error || invoicesQ.error ? t('common.error_generic') : undefined}
          emptyTitle={t('activation.empty')}
          emptyDescription={t('activation.empty_desc')}
          caption={t('activation.table_caption')}
          selectable={can('services.activate')}
          selectedIds={selected}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={(checked) =>
            setSelected(checked ? new Set(candidates.map((c) => c.account.id)) : new Set())
          }
          allSelected={candidates.length > 0 && selected.size === candidates.length}
          someSelected={selected.size > 0 && selected.size < candidates.length}
        />

        <BulkActionBar
          selectedCount={selected.size}
          totalCount={candidates.length}
          onClear={() => setSelected(new Set())}
          onSelectAllResults={() => setSelected(new Set(candidates.map((c) => c.account.id)))}
        >
          <Button
            variant="primary"
            size="sm"
            icon="check"
            disabled={selectedEligible === 0}
            title={selectedEligible === 0 ? t('activation.none_eligible') : undefined}
            onClick={() => setConfirmOpen(true)}
          >
            {t('activation.select_cta', { count: selected.size })}
          </Button>
        </BulkActionBar>

        {results ? (
          <div className="mt-card mt-card-pad mt-stack">
            <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
              {t('activation.result_title')}
            </h2>
            <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none' }} className="mt-stack-sm">
              {results.map((r) => (
                <li
                  key={r.candidate.account.id}
                  className="mt-row"
                  style={{ gap: 'var(--mt-space-2)', alignItems: 'flex-start', flexWrap: 'wrap' }}
                >
                  <StatusBadge
                    tone={resultTone(r.outcome)}
                    label={t(`activation.result_${r.outcome}` as never, undefined as never)}
                  />
                  <span className="mt-small">
                    <strong>{r.candidate.account.customer_name}</strong>{' '}
                    <span className="mt-muted mt-mono mt-small">{r.candidate.account.username}</span>
                    {r.outcome === 'changed' ? (
                      <span className="mt-muted mt-small"> — {t('activation.result_changed_reason')}</span>
                    ) : null}
                    {r.outcome === 'failed' && r.message ? (
                      <span className="mt-muted mt-small"> — {r.message}</span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
            {results.some((r) => r.outcome !== 'success') ? (
              <div>
                <Button
                  variant="secondary"
                  size="sm"
                  icon="rotate"
                  loading={running}
                  onClick={() => {
                    const retryItems = results
                      .filter((r) => r.outcome !== 'success')
                      .map((r) => r.candidate);
                    void runActivation(retryItems);
                  }}
                >
                  {t('activation.retry_failed')}
                </Button>
                <p className="mt-xs mt-muted mt-small" style={{ marginTop: 'var(--mt-space-2)' }}>
                  {t('activation.retry_note')}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}

        <p className="mt-xs mt-muted mt-small">
          {t('activation.nas_note')}{' '}
          <Link to={`/app/${tenantId}/radius`}>{t('activation.radius_link')}</Link>
        </p>
      </div>

      <ConfirmAction
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          setResults(null);
          void runActivation(selectedCandidates);
        }}
        loading={running}
        title={t('activation.confirm_title')}
        intent={t('activation.confirm_intent', {
          eligible: selectedEligible,
          total: selectedCandidates.length,
        })}
        scopeLines={[
          t('activation.confirm_scope_eligible', { eligible: selectedEligible, blocked: selectedNotEligible }),
          t('activation.confirm_scope_manual'),
          t('activation.confirm_scope_nas'),
        ]}
        confirmLabel={t('activation.confirm_cta')}
      />
    </AppShell>
  );
}
