import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { JobProgress } from '../../design-system/components/JobProgress';
import { Skeleton } from '../../design-system/primitives/Misc';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { ConfirmAction } from '../../design-system/components/Notices';
import { formatDateTime } from '../../lib/format';

/**
 * U16 detail — Progress tahap dan item selesai, tanpa ETA bila tak terukur;
 * retry hanya bila retryable; cancel menjelaskan tahap yang masih bisa dibatalkan;
 * uncertain/recovery_required tetap terlihat setelah refresh (UI_UX.md §10).
 */
export default function JobDetailPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  const jobQ = useQuery({
    queryKey: ['job', tenantId, jobId],
    queryFn: () => api.getJob(tenantId, jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.state;
      return s && !['succeeded', 'failed', 'cancelled'].includes(s) ? 2000 : false;
    },
  });

  const job = jobQ.data;
  const terminal = job ? ['succeeded', 'failed', 'cancelled'].includes(job.state) : false;

  const doRetry = async () => {
    if (!jobId) return;
    try {
      const res = await api.retryJob(tenantId, jobId);
      if (res) {
        toast(t('jobs.retry_submitted'), 'success');
        navigate(`/app/${tenantId}/jobs/${res.job_id}`);
      }
    } catch (err) {
      const e = err as { envelope?: { message?: string } };
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
    }
  };

  const doCancel = async () => {
    if (!jobId) return;
    setCancelling(true);
    try {
      await api.cancelJob(tenantId, jobId, cancelReason || t('jobs.cancel_default_reason'));
      setCancelOpen(false);
      toast(t('jobs.cancel_done'), 'info');
      await jobQ.refetch();
    } catch (err) {
      const e = err as { envelope?: { message?: string } };
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
    } finally {
      setCancelling(false);
    }
  };

  return (
    <AppShell tenantId={tenantId} title={t('nav.jobs')}>
      <PageHeader
        breadcrumbs={[
          { label: t('jobs.title'), to: `/app/${tenantId}/jobs` },
          { label: jobId ?? '…' },
        ]}
        title={job ? t(`job.kind.${job.kind}` as never, undefined as never) : <Skeleton w={200} h={28} />}
        description={job ? `${job.id} · ${formatDateTime(job.created_at, locale)}` : undefined}
        actions={
          job ? (
            <>
              {job.retryable && job.state === 'failed' ? (
                <Button variant="secondary" icon="refresh" onClick={doRetry}>
                  {t('jobs.retry_cta')}
                </Button>
              ) : null}
              {!terminal ? (
                <Button variant="danger" onClick={() => setCancelOpen(true)}>
                  {t('jobs.cancel_cta')}
                </Button>
              ) : null}
            </>
          ) : undefined
        }
      />

      {jobQ.isLoading ? (
        <Skeleton h={200} />
      ) : !job ? (
        <div className="mt-banner mt-banner-danger">
          <Icon name="alertCircle" size={20} /> {t('common.not_found')}{' '}
          <Link to={`/app/${tenantId}/jobs`}>{t('common.back_to_list')}</Link>
        </div>
      ) : (
        <div className="mt-stack">
          <div className="mt-card mt-card-pad mt-stack">
            <JobProgress job={job} />
          </div>

          <div className="mt-card mt-card-pad">
            <h2 style={{ fontSize: 'var(--mt-text-base)', marginBottom: 'var(--mt-space-3)' }}>{t('jobs.detail_title')}</h2>
            <dl className="mt-deflist">
              <dt>{t('jobs.col_actor')}</dt>
              <dd>{job.actor_display}</dd>
              <dt>{t('jobs.col_created')}</dt>
              <dd>{formatDateTime(job.created_at, locale)}</dd>
              <dt>{t('jobs.col_updated')}</dt>
              <dd>{formatDateTime(job.updated_at, locale)}</dd>
              <dt>{t('jobs.col_router')}</dt>
              <dd>
                {job.router_id ? (
                  <Link to={`/app/${tenantId}/routers/${job.router_id}`} className="mt-mono">
                    {job.router_id}
                  </Link>
                ) : (
                  '—'
                )}
              </dd>
              <dt>request_id</dt>
              <dd className="mt-mono">{job.request_id ?? '—'}</dd>
            </dl>
            {job.error_code ? (
              <p className="mt-banner mt-banner-danger" style={{ marginTop: 'var(--mt-space-3)', marginBottom: 0 }}>
                <Icon name="alertCircle" size={18} />
                {t('job.error_with_code', { code: job.error_code, requestId: job.request_id ?? '—' })}
              </p>
            ) : null}
            {job.state === 'uncertain' ? (
              <p className="mt-banner mt-banner-warning" style={{ marginTop: 'var(--mt-space-3)', marginBottom: 0 }}>
                <Icon name="alertTriangle" size={18} />
                {t('jobs.uncertain_note')}
              </p>
            ) : null}
            {job.state === 'recovery_required' ? (
              <p className="mt-banner mt-banner-warning" style={{ marginTop: 'var(--mt-space-3)', marginBottom: 0 }}>
                <Icon name="alertTriangle" size={18} />
                {t('jobs.recovery_note')}
              </p>
            ) : null}
          </div>

          <p className="mt-xs mt-muted">{t('jobs.leave_note')}</p>
        </div>
      )}

      <ConfirmAction
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={doCancel}
        loading={cancelling}
        title={t('jobs.cancel_confirm_title')}
        intent={t('jobs.cancel_confirm_intent')}
        scopeLines={[t('jobs.cancel_scope_note')]}
        confirmLabel={t('jobs.cancel_cta')}
        confirmTone="danger"
      >
        <label className="mt-field">
          <span className="mt-label">{t('jobs.cancel_reason_label')}</span>
          <input
            className="mt-input"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder={t('jobs.cancel_reason_placeholder')}
          />
        </label>
      </ConfirmAction>
    </AppShell>
  );
}
