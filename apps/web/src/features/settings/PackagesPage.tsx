import { useQuery } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { Icon } from '../../design-system/primitives/Icon';
import { accountStateTone } from '../../lib/statuses';
import type { RadiusAccountRow } from '../../api/contracts';

/**
 * "Paket dan Profile" (menu PRD; TK-408 — kontrak OpenAPI belum diterbitkan).
 * R1: tampilan baca binding paket→profile per router tanpa tombol tulis palsu.
 */
export default function PackagesPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const { can } = useSession();
  const routersQ = useQuery({ queryKey: ['routers', tenantId], queryFn: () => api.listRouters(tenantId) });
  const accountsQ = useQuery({
    queryKey: ['radius-accounts', tenantId],
    queryFn: () => api.listRadiusAccounts(tenantId, {}, { limit: 200 }),
  });

  const packages = Array.from(
    new Set((accountsQ.data?.items ?? []).map((a) => a.package_name).filter((p): p is string => !!p)),
  );

  const columns: Column<RadiusAccountRow>[] = [
    {
      key: 'username',
      header: t('radius.col_username'),
      render: (a) => <span className="mt-mono mt-small">{a.username}</span>,
    },
    {
      key: 'package',
      header: t('packages.col_package'),
      render: (a) => a.package_name ?? <span className="mt-xs mt-muted">{t('common.not_set')}</span>,
    },
    {
      key: 'state',
      header: t('radius.col_state'),
      render: (a) => <EnumBadge group="account_state" value={a.state} tone={accountStateTone(a.state)} />,
    },
    {
      key: 'router',
      header: t('packages.col_restriction'),
      render: (a) => a.restricting_router_id ?? t('customers.access_all_routers'),
      hideOnMobile: true,
    },
  ];

  return (
    <AppShell tenantId={tenantId} title={t('nav.packages')}>
      <PageHeader
        title={t('packages.title')}
        description={t('packages.desc')}
      />
      <div className="mt-stack">
        <p className="mt-banner mt-banner-info">
          <Icon name="info" size={18} />
          {t('packages.binding_note')}
        </p>

        <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          {packages.map((p) => (
            <div key={p} className="mt-card mt-card-pad mt-stack-sm">
              <strong>{p}</strong>
              <span className="mt-xs mt-muted">
                {(accountsQ.data?.items ?? []).filter((a) => a.package_name === p).length} {t('packages.accounts_count')}
              </span>
            </div>
          ))}
        </div>

        {can('profiles.write') ? (
          <p className="mt-xs mt-muted">{t('packages.write_note')}</p>
        ) : null}

        <DataTable
          rows={accountsQ.data?.items ?? []}
          columns={columns}
          rowKey={(a) => a.id}
          loading={accountsQ.isLoading}
          emptyTitle={t('packages.empty_title')}
          emptyDescription={t('packages.empty_desc')}
          caption={t('packages.table_caption')}
        />
      </div>
      <span className="mt-visually-hidden">{routersQ.data?.length}</span>
    </AppShell>
  );
}
