import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader, FilterBar } from '../../design-system/components/PageHeader';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { MobileServiceCard, BulkActionBar } from '../../design-system/components/DataParts';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { Button } from '../../design-system/primitives/Button';
import { SelectInput } from '../../design-system/primitives/Input';
import { Segmented, CursorPagination } from '../../design-system/primitives/Misc';
import { connectionTone, jobDimensionTone, paymentTone, isolationTone } from '../../lib/statuses';
import { isReleased } from '../../permissions/release-flags';
import { useSession } from '../../state/session';
import type { ServiceRow } from '../../api/contracts';
import { AddCustomerDialog } from './AddCustomerDialog';

const PAGE_SIZE = 50;

/**
 * U04 — Daftar pelanggan: satu baris = satu layanan (UI_UX.md §5).
 * Empat dimensi status terpisah; kolom bayar/isolir (R2) tersembunyi pada R1.
 * Query dipertahankan saat kembali dari detail (via search params).
 */
export default function CustomersPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const navigate = useNavigate();
  const { can } = useSession();
  const [params, setParams] = useSearchParams();
  const [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [addOpen, setAddOpen] = useState(false);

  const query = params.get('q') ?? '';
  const routerId = params.get('router') ?? '';
  const connection = params.get('connection') ?? '';
  const quickTab = params.get('quick_tab') ?? 'all';
  const incompleteOnly = quickTab === 'incomplete' || params.get('incomplete') === '1';

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    if (k !== 'cursor') setCursor(null);
    setParams(next, { replace: true });
  };

  const routersQ = useQuery({ queryKey: ['routers', tenantId], queryFn: () => api.listRouters(tenantId) });

  const servicesQ = useQuery({
    queryKey: ['services', tenantId, { query, routerId, connection, quickTab, incompleteOnly, cursor }],
    queryFn: () =>
      api.listServices(
        tenantId,
        {
          query: query || undefined,
          router_id: routerId || undefined,
          connection: (connection || undefined) as 'online' | 'offline' | 'unknown' | undefined,
          quick_tab: quickTab as 'all' | 'incomplete',
          incomplete_mapping: incompleteOnly || undefined,
        },
        { cursor, limit: PAGE_SIZE },
      ),
    placeholderData: (prev) => prev,
  });

  const rows = servicesQ.data?.items ?? [];
  const uniqueCustomers = useMemo(
    () => new Set((servicesQ.data?.items ?? []).map((r) => r.customer_code)).size,
    [servicesQ.data],
  );
  const selectedCount = selected.size;

  const toggleSelect = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const toggleSelectAll = (checked: boolean) => {
    setSelected(checked ? new Set(rows.map((r) => r.id)) : new Set());
  };

  const columns = useMemo<Column<ServiceRow>[]>(() => {
    const cols: Column<ServiceRow>[] = [
      {
        key: 'customer',
        header: t('customers.col.customer'),
        render: (r) => (
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 500 }}>{r.customer_name}</div>
            <div className="mt-xs mt-muted mt-mono">{r.customer_code} · {r.service_code}</div>
          </div>
        ),
      },
      {
        key: 'username',
        header: t('customers.col.username'),
        render: (r) => <span className="mt-mono mt-small">{r.username ?? t('common.not_set')}</span>,
      },
      {
        key: 'kind',
        header: t('customers.col.service_kind'),
        render: (r) => (r.kind === 'hotspot' ? 'Hotspot' : 'PPPoE'),
        hideOnMobile: true,
      },
      {
        key: 'package',
        header: t('customers.col.package'),
        render: (r) => r.package_name ?? <span className="mt-xs mt-muted">{t('customers.mapping_incomplete')}</span>,
        hideOnMobile: true,
      },
      {
        key: 'router',
        header: t('customers.col.router'),
        render: (r) => r.router_display_name ?? <span className="mt-xs mt-muted">{t('common.not_set')}</span>,
        hideOnMobile: true,
      },
      {
        key: 'connection',
        header: t('customers.col.connection'),
        render: (r) => <EnumBadge group="connection" value={r.connection} tone={connectionTone(r.connection)} />,
      },
      {
        key: 'job',
        header: t('customers.col.job'),
        render: (r) => <EnumBadge group="job_dimension" value={r.job} tone={jobDimensionTone(r.job)} />,
      },
    ];
    if (isReleased('billing')) {
      cols.splice(5, 0, {
        key: 'payment',
        header: t('customers.col.payment'),
        render: (r) => <EnumBadge group="payment" value={r.payment} tone={paymentTone(r.payment)} />,
      });
      cols.splice(6, 0, {
        key: 'isolation',
        header: t('customers.col.isolation'),
        render: (r) => <EnumBadge group="isolation" value={r.isolation} tone={isolationTone(r.isolation)} />,
      });
    }
    return cols;
  }, [t]);

  return (
    <AppShell tenantId={tenantId} title={t('nav.customers')}>
      <PageHeader
        title={t('customers.title')}
        description={t('customers.description', {
          services: servicesQ.data?.items.length ?? 0,
          customers: uniqueCustomers,
        })}
        actions={
          can('customers.write') ? (
            <Button variant="primary" icon="plus" onClick={() => setAddOpen(true)}>
              {t('customers.add')}
            </Button>
          ) : undefined
        }
      />

      <FilterBar>
        <div className="mt-input-wrap" style={{ flex: '1 1 220px', maxWidth: 340 }}>
          <span className="mt-input-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15Zm5.8-1.7L21 21" />
            </svg>
          </span>
          <input
            className="mt-input"
            placeholder={t('customers.search_placeholder')}
            value={query}
            onChange={(e) => setParam('q', e.target.value)}
            aria-label={t('customers.search_label')}
            type="search"
          />
        </div>
        <SelectInput
          label={t('customers.filter_router')}
          options={(routersQ.data ?? []).map((r) => ({ value: r.id, label: r.display_name }))}
          value={routerId}
          placeholderOption={t('common.all_routers')}
          onChange={(e) => setParam('router', e.target.value)}
          style={{ minWidth: 200 }}
        />
        <SelectInput
          label={t('customers.filter_connection')}
          options={[
            { value: 'online', label: t('enums.connection.online') },
            { value: 'offline', label: t('enums.connection.offline') },
            { value: 'unknown', label: t('enums.connection.unknown') },
          ]}
          value={connection}
          placeholderOption={t('common.all_statuses')}
          onChange={(e) => setParam('connection', e.target.value)}
          style={{ minWidth: 180 }}
        />
        <span className="mt-filterbar-spacer" />
        <Segmented
          ariaLabel={t('customers.quick_tabs')}
          value={quickTab === 'incomplete' ? 'incomplete' : 'all'}
          onChange={(v) => setParam('quick_tab', v === 'all' ? '' : v)}
          options={[
            { value: 'all', label: t('customers.tab_all') },
            { value: 'incomplete', label: t('customers.tab_incomplete') },
          ]}
        />
      </FilterBar>

      {selectedCount > 0 ? (
        <BulkActionBar
          selectedCount={selectedCount}
          totalCount={servicesQ.data?.items.length ?? 0}
          filterDescription={query ? t('customers.filter_matches', { q: query }) : undefined}
          onClear={() => setSelected(new Set())}
          onSelectAllResults={() => {
            setSelected(new Set(rows.map((r) => r.id)));
          }}
        >
          {/* Aksi massal R1: hanya aksi yang didukung — tanpa tombol palsu.
              Aksi isolir/aktivasi massal adalah R2 dan disembunyikan. */}
        </BulkActionBar>
      ) : null}

      <DataTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        loading={servicesQ.isLoading}
        error={servicesQ.error ? t('common.error_generic') : undefined}
        emptyTitle={query || routerId || connection ? t('customers.empty_filtered_title') : t('customers.empty_title')}
        emptyDescription={
          query || routerId || connection ? (
            <Button variant="secondary" size="sm" onClick={() => setParams(new URLSearchParams())}>
              {t('common.clear_filters')}
            </Button>
          ) : (
            t('customers.empty_desc')
          )
        }
        emptyAction={
          !query && !routerId && can('customers.write') ? (
            <Button variant="primary" icon="plus" onClick={() => setAddOpen(true)}>
              {t('customers.add')}
            </Button>
          ) : undefined
        }
        onRowClick={(r) => navigate(`/app/${tenantId}/customers/${r.id}?back=${encodeURIComponent(params.toString())}`)}
        selectable
        selectedIds={selected}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        allSelected={rows.length > 0 && rows.every((r) => selected.has(r.id))}
        someSelected={selectedCount > 0}
        mobileRender={(r) => <MobileServiceCard service={r} tenantId={tenantId} />}
        caption={t('customers.table_caption')}
      />

      <div style={{ marginTop: 'var(--mt-space-3)' }}>
        <CursorPagination
          hasNext={servicesQ.data?.next_cursor != null}
          hasPrev={cursor != null}
          onNext={() => setCursor(servicesQ.data?.next_cursor ?? null)}
          onPrev={() => setCursor(null)}
          loading={servicesQ.isFetching}
          rangeLabel={t('common.page_info', { count: rows.length })}
        />
      </div>

      <AddCustomerDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        tenantId={tenantId}
        routers={(routersQ.data ?? []).map((r) => ({ value: r.id, label: r.display_name }))}
      />
    </AppShell>
  );
}
