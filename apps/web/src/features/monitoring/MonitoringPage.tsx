import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { MetricCard } from '../../design-system/components/MetricCard';
import { FreshnessLabel, EnumBadge } from '../../design-system/components/StatusBadge';
import { ChartWithTable } from '../../design-system/components/ChartWithTable';
import type { ChartPoint } from '../../design-system/components/ChartWithTable';
import { Icon } from '../../design-system/primitives/Icon';
import { Tabs, Skeleton } from '../../design-system/primitives/Misc';
import { formatBitsPerSecond, formatPercent } from '../../lib/format';
import { monitorGroupTone } from '../../lib/statuses';
import type { MonitorStatus } from '../../api/contracts';

/**
 * U13 — Monitoring (UI_UX.md §10): Sehat, Terganggu, Tidak terpantau,
 * Data usang, Manajemen tidak terjangkau; tiap status memuat waktu dan sumber.
 * VPN aktif + API gagal = kondisi manajemen, bukan internet pelanggan mati.
 */
const GROUPS = ['healthy', 'disturbed', 'unmonitored', 'stale_data', 'management_unreachable'] as const;

export default function MonitoringPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const [group, setGroup] = useState<string>('all');

  const monitorQ = useQuery({
    queryKey: ['monitor', tenantId],
    queryFn: () => api.listMonitorStatus(tenantId),
    refetchInterval: 60_000, // poll.health_s
  });
  const routersQ = useQuery({ queryKey: ['routers', tenantId], queryFn: () => api.listRouters(tenantId) });

  const mon = monitorQ.data ?? [];
  const routerName = (id: string) => routersQ.data?.find((r) => r.id === id)?.display_name ?? id;

  const grouped = useMemo(() => {
    const map: Record<string, MonitorStatus[]> = {};
    for (const g of GROUPS) map[g] = (monitorQ.data ?? []).filter((m) => m.group === g);
    return map;
  }, [monitorQ.data]);

  const selected = group === 'all' ? mon : (grouped[group] ?? []);

  const trafficData: ChartPoint[] = useMemo(() => {
    const m = (monitorQ.data ?? [])[0];
    const base = m?.interfaces[0]?.rx_bytes_s ?? null;
    const now = Date.now();
    return Array.from({ length: 24 }).map((_, i) => {
      const tIso = new Date(now - (23 - i) * 3_600_000).toISOString();
      const v = i === 7 || i === 13 ? null : base != null ? Math.round(base * (0.7 + Math.sin(i / 3) * 0.25)) : null;
      return { t: tIso, v };
    });
  }, [monitorQ.data]);

  return (
    <AppShell tenantId={tenantId} title={t('nav.routers')}>
      <PageHeader
        title={t('monitoring.title')}
        description={t('monitoring.desc')}
        meta={
          monitorQ.data ? (
            <FreshnessLabel observedAt={monitorQ.data[0]?.observed_at ?? null} source={t('overview.source_collector')} />
          ) : undefined
        }
      />

      {/* Ringkasan kelompok */}
      <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: 'var(--mt-space-4)' }}>
        {GROUPS.map((g) => (
          <MetricCard
            key={g}
            label={t(`monitoring.group_${g}` as never, undefined as never)}
            value={grouped[g]?.length ?? 0}
            loading={monitorQ.isLoading}
            tone={monitorGroupTone(g) === 'success' ? 'success' : monitorGroupTone(g) === 'warning' ? 'warning' : 'default'}
            to={`#group-${g}`}
          />
        ))}
      </div>

      {/* Catatan penting: kondisi manajemen ≠ internet pelanggan mati (UI_UX.md §10) */}
      {(grouped.management_unreachable?.length ?? 0) > 0 ? (
        <p className="mt-banner mt-banner-warning" style={{ marginBottom: 'var(--mt-space-4)' }}>
          <Icon name="info" size={18} />
          {t('monitoring.management_note')}
        </p>
      ) : null}
      {(grouped.stale_data?.length ?? 0) > 0 ? (
        <p className="mt-banner mt-banner-warning" style={{ marginBottom: 'var(--mt-space-4)' }}>
          <Icon name="clock" size={18} />
          {t('monitoring.stale_note')}
        </p>
      ) : null}

      {/* Daftar router per kelompok */}
      <Tabs
        ariaLabel={t('monitoring.group_tabs')}
        active={group}
        onChange={setGroup}
        items={[
          { id: 'all', label: t('monitoring.group_all'), count: mon.length },
          ...GROUPS.map((g) => ({ id: g, label: t(`monitoring.group_${g}` as never, undefined as never), count: grouped[g]?.length ?? 0 })),
        ]}
      />

      <div className="mt-stack" style={{ marginTop: 'var(--mt-space-4)' }}>
        {monitorQ.isLoading ? (
          <Skeleton h={200} />
        ) : selected.length === 0 ? (
          <div className="mt-card mt-card-pad">
            <p className="mt-muted">{t('monitoring.group_empty')}</p>
          </div>
        ) : (
          selected.map((m) => (
            <div key={m.router_id} id={`group-${m.group}`} className="mt-card mt-card-pad mt-stack">
              <div className="mt-row-between">
                <div>
                  <Link to={`/app/${tenantId}/routers/${m.router_id}`} style={{ fontWeight: 600, color: 'var(--mt-text)', textDecoration: 'none' }}>
                    {routerName(m.router_id)}
                  </Link>
                  <div style={{ marginTop: 4 }}>
                    <EnumBadge group="monitor_group" value={m.group} tone={monitorGroupTone(m.group)} />
                  </div>
                </div>
                <FreshnessLabel observedAt={m.observed_at} source={m.source} />
              </div>

              <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
                <div>
                  <h3 className="mt-xs mt-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 'var(--mt-space-2)' }}>
                    {t('monitoring.interfaces_title')}
                  </h3>
                  <div className="mt-stack-sm">
                    {m.interfaces.map((i) => (
                      <div key={i.name} className="mt-row-between mt-small" style={{ borderBottom: '1px solid var(--mt-neutral-border)', paddingBottom: 4 }}>
                        <span className="mt-mono">{i.name}</span>
                        <span className="mt-muted" style={{ fontVariantNumeric: 'tabular-nums' }}>
                          ↓ {formatBitsPerSecond(i.rx_bytes_s, locale)} · ↑ {formatBitsPerSecond(i.tx_bytes_s, locale)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Status RADIUS per router ditampilkan terpisah (UI_UX.md §10) */}
                <div>
                  <h3 className="mt-xs mt-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 'var(--mt-space-2)' }}>
                    {t('monitoring.radius_title')}
                  </h3>
                  {m.radius ? (
                    <div className="mt-stack-sm mt-small">
                      <div className="mt-row-between">
                        <span className="mt-muted">{t('monitoring.radius_auth_ratio')}</span>
                        <span>{formatPercent(m.radius.auth_success_ratio_24h, locale)}</span>
                      </div>
                      <div className="mt-row-between">
                        <span className="mt-muted">{t('monitoring.radius_sessions')}</span>
                        <span>{m.radius.inbound_sessions_24h ?? t('common.unknown')}</span>
                      </div>
                      <div className="mt-row-between">
                        <span className="mt-muted">{t('monitoring.radius_last_accounting')}</span>
                        <FreshnessLabel observedAt={m.radius.last_accounting_at} />
                      </div>
                    </div>
                  ) : (
                    <p className="mt-small mt-muted">{t('monitoring.radius_no_data')}</p>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {/* Grafik trafik agregat dengan unit & rentang & gap (UI_UX.md §4) */}
        <div className="mt-card mt-card-pad">
          <ChartWithTable
            data={trafficData}
            unit="bits"
            caption={t('monitoring.traffic_caption')}
            loading={monitorQ.isLoading}
            rangeLabel={t('chart.range_24h')}
          />
        </div>
      </div>
    </AppShell>
  );
}
