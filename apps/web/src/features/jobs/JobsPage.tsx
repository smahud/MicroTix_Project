import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { JobProgress } from '../../design-system/components/JobProgress';
import { CursorPagination } from '../../design-system/primitives/Misc';
import { formatDateTime } from '../../lib/format';
import { jobStateTone } from '../../lib/statuses';
import type { JobRecord } from '../../api/contracts';

/** U16 — Pusat pekerjaan lintas modul (UI_UX.md §10). */
export default function JobsPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const navigate = useNavigate();
  const [cursor, setCusor] = useState<null | string>(null);

  const jobsQ = useQuery({
    queryKey: ['jobs', tenantId, cursor],
    queryFn: () => api.listJobs(tenantId, { cursor, limit: 50 }),
    refetchInterval: 5_000, // job.status_poll_later_s
    placeholderData: (prev) => prev,
  });

  const columns: Column<JobRecord>[] = [
    {
      key: 'kind',
      header: t('jobs.col_kind'),
      render: (j) => <span className="mt-small">{t(`job.kind.${j.kind}` as never, undefined as never)}</span>,
    },
    {
      key: 'state',
      header: t('jobs.col_state'),
      render: (j) => <EnumBadge group="job_state" value={j.state} tone={jobStateTone(j.state)} />,
    },
    {
      key: 'router',
      header: t('jobs.col_router'),
      render: (j) => (j.router_id ? <span className="mt-mono mt-small">{j.router_id}</span> : '—'),
      hideOnMobile: true,
    },
    {
      key: 'actor',
      header: t('jobs.col_actor'),
      render: (j) => <span className="mt-small">{j.actor_display}</span>,
      hideOnMobile: true,
    },
    {
      key: 'created',
      header: t('jobs.col_created'),
      render: (j) => <span className="mt-small mt-muted">{formatDateTime(j.created_at, locale)}</span>,
      hideOnMobile: true,
    },
    {
      key: 'progress',
      header: t('jobs.col_progress'),
      render: (j) => <JobProgress job={j} compact />,
    },
  ];

  return (
    <AppShell tenantId={tenantId} title={t('nav.jobs')}>
      <PageHeader
        title={t('jobs.title')}
        description={t('jobs.desc')}
      />
      <DataTable
        rows={jobsQ.data?.items ?? []}
        columns={columns}
        rowKey={(j) => j.id}
        loading={jobsQ.isLoading}
        error={jobsQ.error ? t('common.error_generic') : undefined}
        emptyTitle={t('jobs.empty_title')}
        emptyDescription={t('jobs.empty_desc')}
        onRowClick={(j) => navigate(`/app/${tenantId}/jobs/${j.id}`)}
        mobileRender={(j) => (
          <div className="mt-stack-sm">
            <div className="mt-row-between">
              <span className="mt-small" style={{ fontWeight: 600 }}>
                {t(`job.kind.${j.kind}` as never, undefined as never)}
              </span>
              <EnumBadge group="job_state" value={j.state} tone={jobStateTone(j.state)} />
            </div>
            <JobProgress job={j} />
            <span className="mt-xs mt-muted">{j.actor_display}</span>
          </div>
        )}
        caption={t('jobs.table_caption')}
      />
      <div style={{ marginTop: 'var(--mt-space-3)' }}>
        <CursorPagination
          hasNext={jobsQ.data?.next_cursor != null}
          hasPrev={cursor != null}
          onNext={() => setCusor(jobsQ.data?.next_cursor ?? null)}
          onPrev={() => setCusor(null)}
          loading={jobsQ.isFetching}
          rangeLabel={t('common.page_info', { count: jobsQ.data?.items.length ?? 0 })}
        />
      </div>
    </AppShell>
  );
}
