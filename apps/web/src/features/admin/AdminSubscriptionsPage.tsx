import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AdminShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { Tabs } from '../../design-system/primitives/Misc';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { ConfirmAction } from '../../design-system/components/Notices';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { TextArea } from '../../design-system/primitives/Input';
import { submissionStateTone } from '../../lib/statuses';
import { formatDateTime, formatMoney } from '../../lib/format';
import type { PlatformPaymentSubmission } from '../../api/contracts';

/**
 * U14 — Super Admin (UI_UX.md §9): antrean Menunggu verifikasi, Perlu perbaikan,
 * Disetujui, Ditolak. Split view bukti/data/invoice/keputusan.
 * Approve mensyaratkan konfirmasi "Dana telah diterima di rekening".
 */
export default function AdminSubscriptionsPage() {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { ctx } = useSession();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [queue, setQueue] = useState<PlatformPaymentSubmission['state']>('submitted');
  const [selected, setSelected] = useState<PlatformPaymentSubmission | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  const subsQ = useQuery({
    queryKey: ['platform-submissions', queue],
    queryFn: () => api.listPlatformSubmissions(queue),
    refetchInterval: 30_000,
  });

  const act = async (fn: () => Promise<void>, okMsg: string) => {
    setBusy(true);
    try {
      await fn();
      toast(okMsg, 'success');
      await queryClient.invalidateQueries({ queryKey: ['platform-submissions'] });
      setSelected(null);
    } catch (err) {
      const e = err as { envelope?: { message?: string } };
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
    } finally {
      setBusy(false);
    }
  };

  const columns: Column<PlatformPaymentSubmission>[] = [
    {
      key: 'tenant',
      header: t('admin.col_tenant'),
      render: (s) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 500 }}>{s.tenant_display_name}</div>
          <div className="mt-xs mt-muted mt-mono">{s.saas_invoice_id}</div>
        </div>
      ),
    },
    {
      key: 'plan',
      header: t('admin.col_plan'),
      render: (s) => `${t(`landing.plan_${s.plan_code}` as never, undefined as never)} · ${s.period_months} bln`,
      hideOnMobile: true,
    },
    {
      key: 'amount',
      header: t('admin.col_amount'),
      align: 'right',
      render: (s) => <span style={{ fontVariantNumeric: 'tabular-nums' }}>{formatMoney(s.amount, locale)}</span>,
    },
    {
      key: 'submitted',
      header: t('admin.col_submitted'),
      render: (s) => formatDateTime(s.submitted_at, locale),
      hideOnMobile: true,
    },
    {
      key: 'state',
      header: t('admin.col_state'),
      render: (s) => <EnumBadge group="submission_state" value={s.state} tone={submissionStateTone(s.state)} />,
    },
  ];

  return (
    <AdminShell
      title={
        <PageHeader
          title={t('admin.title')}
          description={t('admin.desc')}
        />
      }
    >
      <div className="mt-stack">
        <Tabs
          ariaLabel={t('admin.queue_tabs')}
          active={queue}
          onChange={(q) => {
            setQueue(q as PlatformPaymentSubmission['state']);
            setSelected(null);
          }}
          items={[
            { id: 'submitted', label: t('admin.queue_submitted') },
            { id: 'revision_requested', label: t('admin.queue_revision') },
            { id: 'approved', label: t('admin.queue_approved') },
            { id: 'rejected', label: t('admin.queue_rejected') },
          ]}
        />

        <div className="mt-admin-split">
          <DataTable
            rows={subsQ.data ?? []}
            columns={columns}
            rowKey={(s) => s.id}
            loading={subsQ.isLoading}
            emptyTitle={t('admin.empty_queue')}
            onRowClick={setSelected}
            caption={t('admin.table_caption')}
          />

          {/* Split view keputusan */}
          <div className="mt-card mt-card-pad mt-stack">
            <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('admin.detail_title')}</h2>
            {!selected ? (
              <p className="mt-muted mt-small">{t('admin.detail_empty')}</p>
            ) : (
              <>
                <dl className="mt-deflist">
                  <dt>{t('admin.col_tenant')}</dt>
                  <dd>{selected.tenant_display_name}</dd>
                  <dt>{t('admin.col_plan')}</dt>
                  <dd>
                    {t(`landing.plan_${selected.plan_code}` as never, undefined as never)} · {selected.period_months} {t('admin.months')}
                  </dd>
                  <dt>{t('admin.col_amount')}</dt>
                  <dd>{formatMoney(selected.amount, locale)}</dd>
                  <dt>{t('admin.col_submitted')}</dt>
                  <dd>{formatDateTime(selected.submitted_at, locale)}</dd>
                  <dt>{t('admin.assignee')}</dt>
                  <dd>{selected.assignee ?? '—'}</dd>
                </dl>

                <div className="mt-banner mt-banner-info">
                  <Icon name="fileText" size={18} />
                  <div>
                    <strong>{t('admin.proof_title')}</strong>
                    <p className="mt-small">{t('admin.proof_note')}</p>
                    <Button variant="secondary" size="sm" icon="eye" onClick={() => toast(t('admin.proof_scanning'), 'info')}>
                      {t('admin.view_proof')}
                    </Button>
                  </div>
                </div>

                {selected.state === 'submitted' ? (
                  <div className="mt-row" style={{ gap: 'var(--mt-space-2)' }}>
                    <Button variant="primary" icon="check" onClick={() => setApproveOpen(true)}>
                      {t('admin.approve_cta')}
                    </Button>
                    <Button variant="secondary" onClick={() => setRevisionOpen(true)}>
                      {t('admin.request_revision_cta')}
                    </Button>
                    <Button variant="danger" onClick={() => setRejectOpen(true)}>
                      {t('admin.reject_cta')}
                    </Button>
                  </div>
                ) : (
                  <p className="mt-small mt-muted">{t('admin.decision_done_note')}</p>
                )}
              </>
            )}
          </div>
        </div>

        <p className="mt-xs mt-muted">
          <Icon name="lock" size={14} style={{ verticalAlign: -2 }} /> {t('admin.privacy_note')}
        </p>
        <span className="mt-visually-hidden">{ctx?.user?.email}</span>
      </div>

      <ConfirmAction
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        onConfirm={() => {
          if (!selected) return;
          void act(() => api.approvePlatformSubmission(selected.id), t('admin.approved_toast'));
          setApproveOpen(false);
        }}
        loading={busy}
        title={t('admin.approve_title')}
        intent={t('admin.approve_intent', { tenant: selected?.tenant_display_name ?? '', amount: selected ? formatMoney(selected.amount, locale) : '' })}
        scopeLines={[t('admin.approve_scope_funds'), t('admin.approve_scope_entitlement')]}
        confirmLabel={t('admin.approve_cta')}
        requiresReauth
      />

      <ConfirmAction
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        onConfirm={() => {
          if (!selected) return;
          void act(() => api.rejectPlatformSubmission(selected.id, reason), t('admin.rejected_toast'));
          setRejectOpen(false);
          setReason('');
        }}
        loading={busy}
        title={t('admin.reject_title')}
        intent={t('admin.reject_intent')}
        scopeLines={[t('admin.reason_required_note')]}
        confirmLabel={t('admin.reject_cta')}
        confirmTone="danger"
      >
        <TextArea label={t('admin.reason_label')} value={reason} onChange={(e) => setReason(e.target.value)} required />
      </ConfirmAction>

      <ConfirmAction
        open={revisionOpen}
        onClose={() => setRevisionOpen(false)}
        onConfirm={() => {
          if (!selected) return;
          void act(() => api.requestRevisionPlatformSubmission(selected.id, reason), t('admin.revision_toast'));
          setRevisionOpen(false);
          setReason('');
        }}
        loading={busy}
        title={t('admin.revision_title')}
        intent={t('admin.revision_intent')}
        scopeLines={[t('admin.reason_required_note')]}
        confirmLabel={t('admin.request_revision_cta')}
      >
        <TextArea label={t('admin.reason_label')} value={reason} onChange={(e) => setReason(e.target.value)} required />
      </ConfirmAction>
    </AdminShell>
  );
}
