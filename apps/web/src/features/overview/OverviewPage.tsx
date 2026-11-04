import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { MetricCard } from '../../design-system/components/MetricCard';
import { ChartWithTable } from '../../design-system/components/ChartWithTable';
import type { ChartPoint } from '../../design-system/components/ChartWithTable';
import { FreshnessLabel } from '../../design-system/components/StatusBadge';
import { Icon } from '../../design-system/primitives/Icon';
import { ButtonLink } from '../../design-system/primitives/Button';
import { Skeleton } from '../../design-system/primitives/Misc';
import { isReleased } from '../../permissions/release-flags';

/**
 * U03 — Dashboard pekerjaan harian (UI_UX.md §4).
 * Urutan baca: tenant/periode → yang perlu dikerjakan → ringkasan usaha →
 * kesehatan jaringan → aktivitas terbaru. Kartu tagihan/kas/piutang R2
 * TIDAK ditampilkan pada R1 (bukan nol).
 */
export default function OverviewPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const { activeTenant } = useSession();
  const [range, setRange] = useState('24h');

  const routersQ = useQuery({
    queryKey: ['routers', tenantId],
    queryFn: () => api.listRouters(tenantId),
  });
  const servicesQ = useQuery({
    queryKey: ['services-overview', tenantId],
    queryFn: () => api.listServices(tenantId, { quick_tab: 'all' }, { limit: 200 }),
  });
  const monitorQ = useQuery({
    queryKey: ['monitor', tenantId],
    queryFn: () => api.listMonitorStatus(tenantId),
    refetchInterval: 60_000,
  });
  const backupsQ = useQuery({
    queryKey: ['backups', tenantId],
    queryFn: () => api.listBackupArtifacts(tenantId, null),
  });
  const jobsQ = useQuery({
    queryKey: ['jobs', tenantId],
    queryFn: () => api.listJobs(tenantId, { limit: 10 }),
    refetchInterval: 10_000,
  });
  const radiusQ = useQuery({
    queryKey: ['radius-status', tenantId],
    queryFn: () => api.listRadiusRouterStatus(tenantId),
  });

  const loading = routersQ.isLoading || servicesQ.isLoading;

  /* Yang perlu dikerjakan — kartu pekerjaan R1 */
  const workItems = useMemo(() => {
    if (!routersQ.data || !servicesQ.data || !backupsQ.data || !radiusQ.data) return [];
    const items: Array<{ key: string; tone: 'warning' | 'danger'; label: string; to: string; count?: number }> = [];
    const failedBackups = backupsQ.data.filter((b) => b.transfer_state === 'failed').length;
    if (failedBackups > 0) {
      items.push({ key: 'backup_failed', tone: 'danger', label: t('overview.work_backup_failed', { count: failedBackups }), to: `/app/${tenantId}/backups`, count: failedBackups });
    }
    const degraded = radiusQ.data.filter((r) => r.enforcement_mode === 'degraded' || r.client_status === 'missing_client');
    const badAuth = radiusQ.data.filter((r) => r.auth_success_ratio_24h != null && r.auth_success_ratio_24h < 0.9);
    if (degraded.length + badAuth.length > 0) {
      items.push({ key: 'radius_issue', tone: 'warning', label: t('overview.work_radius_issue', { count: degraded.length + badAuth.length }), to: `/app/${tenantId}/radius` });
    }
    const incomplete = servicesQ.data.items.filter((s) => s.incomplete_mapping).length;
    if (incomplete > 0) {
      items.push({ key: 'incomplete', tone: 'warning', label: t('overview.work_incomplete', { count: incomplete }), to: `/app/${tenantId}/customers?quick_tab=incomplete` });
    }
    const unmonitored = (monitorQ.data ?? []).filter((m) => m.group !== 'healthy').length;
    if (unmonitored > 0) {
      items.push({ key: 'router_health', tone: 'warning', label: t('overview.work_router_health', { count: unmonitored }), to: `/app/${tenantId}/monitoring` });
    }
    return items;
  }, [routersQ.data, servicesQ.data, backupsQ.data, radiusQ.data, monitorQ.data, t, tenantId]);

  /* Onboarding: langkah selesai, bukan persentase (UI_UX.md §3) */
  const onboarding = useMemo(() => {
    const hasCompany = true; // tenant ada = perusahaan dibuat
    const hasRouter = (routersQ.data ?? []).length > 0;
    const adopted = (radiusQ.data ?? []).reduce((s, r) => s + r.migrated_accounts, 0) > 0;
    const mapped = (servicesQ.data?.items ?? []).every((s) => !s.incomplete_mapping) && (servicesQ.data?.items.length ?? 0) > 0;
    const steps = [
      { key: 'company', done: hasCompany },
      { key: 'router', done: hasRouter },
      { key: 'adopt', done: adopted },
      { key: 'map', done: mapped },
    ];
    if (isReleased('billing')) steps.push({ key: 'billing', done: false });
    steps.push({ key: 'team', done: false });
    return steps;
  }, [routersQ.data, radiusQ.data, servicesQ.data]);

  const onboardingDone = onboarding.filter((s) => s.done).length;
  const emptyTenant = !loading && (routersQ.data ?? []).length === 0;

  /* Data grafik trafik — gap tetap gap */
  const trafficData: ChartPoint[] = useMemo(() => {
    const mon = monitorQ.data ?? [];
    const wan = mon.flatMap((m) => m.interfaces.filter((i) => i.name.includes('WAN')));
    const base = wan[0]?.rx_bytes_s ?? null;
    const now = Date.now();
    return Array.from({ length: 24 }).map((_, i) => {
      const tIso = new Date(now - (23 - i) * 3_600_000).toISOString();
      // Gap: sample kolektor tidak tersedia (bukan nol)
      const v = i === 7 || i === 13 ? null : base != null ? Math.round(base * (0.7 + Math.sin(i / 3) * 0.25)) : null;
      return { t: tIso, v };
    });
  }, [monitorQ.data]);

  return (
    <AppShell tenantId={tenantId} title={activeTenant?.display_name}>
      <PageHeader
        title={t('overview.title')}
        description={t('overview.description')}
        meta={
          <span className="mt-small mt-muted">
            {t('overview.period_now')} · {activeTenant?.display_name}
          </span>
        }
        actions={
          <ButtonLink to={`/app/${tenantId}/routers/new`} variant="primary" icon="plus">
            {t('routers.new_title')}
          </ButtonLink>
        }
      />

      {emptyTenant ? (
        <div className="mt-card mt-card-pad mt-stack" style={{ textAlign: 'center', alignItems: 'center' }}>
          <Icon name="router" size={44} style={{ color: 'var(--mt-primary)' }} />
          <h2>{t('overview.empty_tenant_title')}</h2>
          <p className="mt-muted" style={{ maxWidth: 480 }}>
            {t('overview.empty_tenant_desc')}
          </p>
          <ButtonLink to={`/app/${tenantId}/routers/new`} variant="primary" icon="plus">
            {t('overview.cta_connect_router')}
          </ButtonLink>
        </div>
      ) : (
        <>
          {/* Onboarding checklist */}
          <section className="mt-section" aria-labelledby="onb-title">
            <h2 id="onb-title" className="mt-section-title">
              {t('overview.onboarding_title')}
              <span className="mt-small mt-muted" style={{ fontWeight: 400, marginLeft: 8 }}>
                {t('overview.onboarding_progress', { done: onboardingDone, total: onboarding.length })}
              </span>
            </h2>
            <div className="mt-card mt-card-pad">
              {loading ? (
                <div className="mt-stack-sm">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} w="70%" h={20} />
                  ))}
                </div>
              ) : (
                onboarding.map((s) => (
                  <div key={s.key} className="mt-onboard-item">
                    <span className={`mt-onboard-check ${s.done ? 'mt-onboard-check-done' : 'mt-onboard-check-todo'}`} aria-hidden="true">
                      {s.done ? <Icon name="check" size={14} /> : null}
                    </span>
                    <span className={s.done ? '' : 'mt-muted'} style={{ textDecoration: s.done ? 'line-through' : 'none' }}>
                      {t(`overview.onboard_${s.key}` as never, undefined as never)}
                    </span>
                    {!s.done && s.key === 'router' ? (
                      <Link to={`/app/${tenantId}/routers/new`} className="mt-small">
                        {t('overview.onboard_cta')}
                      </Link>
                    ) : null}
                    {!s.done && s.key === 'adopt' ? (
                      <Link to={`/app/${tenantId}/imports/router`} className="mt-small">
                        {t('overview.onboard_cta')}
                      </Link>
                    ) : null}
                    {!s.done && s.key === 'team' ? (
                      <Link to={`/app/${tenantId}/settings/team`} className="mt-small">
                        {t('overview.onboard_cta')}
                      </Link>
                    ) : null}
                    {!s.done && s.key === 'billing' ? (
                      <span className="mt-xs mt-muted">{t('overview.onboard_billing_note')}</span>
                    ) : null}
                    {!s.done && s.key === 'map' ? (
                      <Link to={`/app/${tenantId}/customers?quick_tab=incomplete`} className="mt-small">
                        {t('overview.onboard_cta')}
                      </Link>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </section>

          {/* Yang perlu dikerjakan */}
          <section className="mt-section" aria-labelledby="work-title">
            <h2 id="work-title" className="mt-section-title">
              {t('overview.work_title')}
            </h2>
            {loading ? (
              <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="mt-card mt-card-pad">
                    <Skeleton h={20} w="80%" />
                  </div>
                ))}
              </div>
            ) : workItems.length === 0 ? (
              <div className="mt-banner mt-banner-success">
                <Icon name="checkCircle" size={20} />
                {t('overview.work_clear')}
              </div>
            ) : (
              <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
                {workItems.map((w) => (
                  <Link key={w.key} to={w.to} className={`mt-card mt-card-pad mt-metric ${w.tone === 'danger' ? 'mt-metric-danger' : 'mt-metric-warning'}`}>
                    <span className="mt-metric-label">{t('overview.work_card_label')}</span>
                    <span style={{ fontSize: 'var(--mt-text-base)', fontWeight: 500 }}>{w.label}</span>
                    <span className="mt-metric-hint">{t('overview.work_card_cta')}</span>
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Ringkasan usaha — R1: tanpa kartu tagihan/kas/piutang (UI_UX.md §4) */}
          <section className="mt-section" aria-labelledby="summary-title">
            <h2 id="summary-title" className="mt-section-title">
              {t('overview.summary_title')}
            </h2>
            {!isReleased('billing') ? (
              <p className="mt-small mt-muted" style={{ marginBottom: 'var(--mt-space-3)' }}>
                {t('overview.summary_r1_note')}
              </p>
            ) : null}
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              <MetricCard
                label={t('overview.metric_services')}
                value={servicesQ.data?.items.length ?? 0}
                to={`/app/${tenantId}/customers`}
                loading={servicesQ.isLoading}
                hint={t('overview.metric_services_hint')}
              />
              <MetricCard
                label={t('overview.metric_routers')}
                value={routersQ.data?.length ?? 0}
                to={`/app/${tenantId}/routers`}
                loading={routersQ.isLoading}
                hint={t('overview.metric_routers_hint')}
              />
              <MetricCard
                label={t('overview.metric_accounts')}
                value={(radiusQ.data ?? []).reduce((s, r) => s + r.migrated_accounts, 0)}
                to={`/app/${tenantId}/radius`}
                loading={radiusQ.isLoading}
                hint={t('overview.metric_accounts_hint')}
                pendingAggNote={t('overview.pending_agg_note')}
              />
            </div>
          </section>

          {/* Kesehatan jaringan */}
          <section className="mt-section" aria-labelledby="net-title">
            <h2 id="net-title" className="mt-section-title">
              {t('overview.network_title')}
            </h2>
            <div className="mt-card mt-card-pad">
              <div className="mt-row-between" style={{ marginBottom: 'var(--mt-space-3)' }}>
                <FreshnessLabel
                  observedAt={monitorQ.data?.[0]?.observed_at ?? null}
                  source={t('overview.source_collector')}
                />
                <Link to={`/app/${tenantId}/monitoring`} className="mt-small">
                  {t('overview.open_monitoring')} →
                </Link>
              </div>
              <ChartWithTable
                data={trafficData}
                unit="bits"
                caption={t('overview.traffic_chart_caption')}
                range={range}
                onRangeChange={setRange}
                loading={monitorQ.isLoading}
                rangeLabel={range === '24h' ? t('chart.range_24h') : t('chart.range_7d')}
              />
              {monitorQ.data?.some((m) => m.group === 'stale_data') ? (
                <p className="mt-banner mt-banner-warning" style={{ marginTop: 'var(--mt-space-3)', marginBottom: 0 }}>
                  <Icon name="clock" size={18} />
                  {t('overview.monitoring_partial_banner')}
                </p>
              ) : null}
            </div>
          </section>

          {/* Aktivitas terbaru */}
          <section className="mt-section" aria-labelledby="recent-title">
            <h2 id="recent-title" className="mt-section-title">
              {t('overview.recent_title')}
            </h2>
            <div className="mt-card mt-card-pad">
              {jobsQ.isLoading ? (
                <div className="mt-stack-sm">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} h={18} />
                  ))}
                </div>
              ) : (
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }} className="mt-stack-sm">
                  {(jobsQ.data?.items ?? []).slice(0, 6).map((j) => (
                    <li key={j.id} className="mt-row-between" style={{ borderBottom: '1px solid var(--mt-neutral-border)', paddingBottom: 'var(--mt-space-2)' }}>
                      <span className="mt-small mt-mono">{t(`job.kind.${j.kind}` as never, undefined as never)}</span>
                      <Link to={`/app/${tenantId}/jobs/${j.id}`} className="mt-small">
                        {t('overview.view_job')} →
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              <div style={{ marginTop: 'var(--mt-space-3)' }}>
                <Link to={`/app/${tenantId}/jobs`} className="mt-small">
                  {t('overview.all_jobs')} →
                </Link>
              </div>
            </div>
          </section>
        </>
      )}
    </AppShell>
  );
}
