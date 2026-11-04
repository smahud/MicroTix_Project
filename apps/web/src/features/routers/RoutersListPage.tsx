import { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge, FreshnessLabel } from '../../design-system/components/StatusBadge';
import { ButtonLink } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { enforcementTone } from '../../lib/statuses';
import type { RouterSummary } from '../../api/contracts';

/** Daftar router (U06 pembuka) — status VPN/API/RADIUS terpisah. */
export default function RoutersListPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const navigate = useNavigate();
  const routersQ = useQuery({ queryKey: ['routers', tenantId], queryFn: () => api.listRouters(tenantId) });

  const columns = useMemo<Column<RouterSummary>[]>(() => [
    {
      key: 'name',
      header: t('routers.col_router'),
      render: (r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 500 }}>{r.display_name}</div>
          <div className="mt-xs mt-muted mt-mono">
            {r.router_code} · {r.model ?? t('common.unknown')}
          </div>
        </div>
      ),
    },
    {
      key: 'health',
      header: t('routers.col_health'),
      render: (r) => (
        <div className="mt-stack-sm" style={{ gap: 4 }}>
          <span className="mt-small mt-row" style={{ gap: 6 }}>
            <Icon name="shield" size={14} style={{ color: r.health.vpn === 'up' ? 'var(--mt-success-fg)' : r.health.vpn === 'down' ? 'var(--mt-warning-fg)' : 'var(--mt-text-secondary)' }} />
            VPN: <EnumBadge group="vpn" value={r.health.vpn} tone={r.health.vpn === 'up' ? 'success' : r.health.vpn === 'down' ? 'warning' : 'neutral'} />
          </span>
          <span className="mt-small mt-row" style={{ gap: 6 }}>
            <Icon name="terminal" size={14} style={{ color: r.health.api === 'up' ? 'var(--mt-success-fg)' : r.health.api === 'down' ? 'var(--mt-danger-fg)' : 'var(--mt-text-secondary)' }} />
            API: <EnumBadge group="api" value={r.health.api} tone={r.health.api === 'up' ? 'success' : r.health.api === 'down' ? 'danger' : 'neutral'} />
          </span>
        </div>
      ),
    },
    {
      key: 'mode',
      header: t('routers.col_mode'),
      render: (r) => (r.mode === 'managed' ? t('routers.mode_managed') : t('routers.mode_read_only')),
      hideOnMobile: true,
    },
    {
      key: 'enforcement',
      header: t('routers.col_enforcement'),
      render: (r) => <EnumBadge group="enforcement_mode" value={r.enforcement_mode} tone={enforcementTone(r.enforcement_mode)} />,
    },
    {
      key: 'services',
      header: t('routers.col_services'),
      align: 'right',
      render: (r) => r.services_count,
      hideOnMobile: true,
    },
    {
      key: 'freshness',
      header: t('routers.col_observed'),
      render: (r) => <FreshnessLabel observedAt={r.health.observed_at} />,
      hideOnMobile: true,
    },
  ], [t]);

  return (
    <AppShell tenantId={tenantId} title={t('nav.routers')}>
      <PageHeader
        title={t('routers.list_title')}
        description={t('routers.list_desc')}
        actions={
          <ButtonLink to={`/app/${tenantId}/routers/new`} variant="primary" icon="plus">
            {t('routers.new_title')}
          </ButtonLink>
        }
      />
      <DataTable
        rows={routersQ.data ?? []}
        columns={columns}
        rowKey={(r) => r.id}
        loading={routersQ.isLoading}
        error={routersQ.error ? t('common.error_generic') : undefined}
        emptyTitle={t('routers.empty_title')}
        emptyDescription={t('routers.empty_desc')}
        emptyAction={
          <ButtonLink to={`/app/${tenantId}/routers/new`} variant="primary" icon="plus">
            {t('routers.new_title')}
          </ButtonLink>
        }
        onRowClick={(r) => navigate(`/app/${tenantId}/routers/${r.id}`)}
        mobileRender={(r) => (
          <div className="mt-stack-sm">
            <div className="mt-row-between">
              <Link to={`/app/${tenantId}/routers/${r.id}`} style={{ fontWeight: 600, color: 'var(--mt-text)', textDecoration: 'none' }}>
                {r.display_name}
              </Link>
              <EnumBadge group="enforcement_mode" value={r.enforcement_mode} tone={enforcementTone(r.enforcement_mode)} />
            </div>
            <span className="mt-xs mt-muted mt-mono">
              {r.router_code} · {r.model ?? t('common.unknown')}
            </span>
            <FreshnessLabel observedAt={r.health.observed_at} />
          </div>
        )}
        caption={t('routers.table_caption')}
      />
    </AppShell>
  );
}
