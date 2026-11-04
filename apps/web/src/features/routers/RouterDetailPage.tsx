import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { Tabs, Skeleton } from '../../design-system/primitives/Misc';
import { EnumBadge, FreshnessLabel } from '../../design-system/components/StatusBadge';
import { AuditTimeline } from '../../design-system/components/DataParts';
import { Button, ButtonLink } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { ConfirmAction } from '../../design-system/components/Notices';
import { enforcementTone } from '../../lib/statuses';
import { formatDateTime, formatDuration, formatPercent } from '../../lib/format';
import type { JobRecord } from '../../api/contracts';
import { JobProgress } from '../../design-system/components/JobProgress';

/**
 * U06 — Detail router (UI_UX.md §7): tab Ringkasan, Akun ditemukan, Profile,
 * Interface, Backup, Pekerjaan, Audit. Panel RADIUS dengan enforcement_mode.
 */
export default function RouterDetailPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { routerId } = useParams<{ routerId: string }>();
  const navigate = useNavigate();
  const { can } = useSession();
  const { toast } = useToast();
  const [tab, setTab] = useState('summary');
  const [releaseOpen, setReleaseOpen] = useState(false);
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const routerQ = useQuery({
    queryKey: ['router', tenantId, routerId],
    queryFn: () => api.getRouter(tenantId, routerId!),
    enabled: !!routerId,
  });
  const radiusQ = useQuery({
    queryKey: ['radius-status-router', tenantId, routerId],
    queryFn: () => api.getRadiusRouterStatus(tenantId, routerId!),
    enabled: !!routerId && tab === 'summary',
    refetchInterval: 30_000,
  });
  const jobsQ = useQuery({
    queryKey: ['jobs', tenantId],
    queryFn: () => api.listJobs(tenantId, { limit: 30 }),
    enabled: tab === 'jobs',
    refetchInterval: 5_000,
  });
  const backupsQ = useQuery({
    queryKey: ['backups', tenantId],
    queryFn: () => api.listBackupArtifacts(tenantId, routerId ?? null),
    enabled: tab === 'backup',
  });
  const auditQ = useQuery({
    queryKey: ['audit', tenantId, routerId],
    queryFn: () => api.listAuditTimeline(tenantId, routerId ?? null, { limit: 20 }),
    enabled: tab === 'audit',
  });

  const r = routerQ.data;
  const radius = radiusQ.data;

  const routerJobs = useMemo(
    () => (jobsQ.data?.items ?? []).filter((j) => j.router_id === routerId),
    [jobsQ.data, routerId],
  );

  const doRelease = async () => {
    if (!routerId) return;
    setActionLoading(true);
    try {
      const res = await api.releaseRouter(tenantId, routerId);
      setReleaseOpen(false);
      toast(t('routers.release_submitted'), 'success');
      navigate(`/app/${tenantId}/jobs/${res.job_id}`);
    } finally {
      setActionLoading(false);
    }
  };

  const doReplace = async () => {
    if (!routerId) return;
    setActionLoading(true);
    try {
      const res = await api.replaceRouter(tenantId, routerId, '');
      setReplaceOpen(false);
      toast(t('routers.replace_submitted'), 'success');
      navigate(`/app/${tenantId}/jobs/${res.job_id}`);
    } finally {
      setActionLoading(false);
    }
  };

  const tabs = [
    { id: 'summary', label: t('routers.tab_summary') },
    { id: 'discovered', label: t('routers.tab_discovered') },
    { id: 'profiles', label: t('routers.tab_profiles') },
    { id: 'interfaces', label: t('routers.tab_interfaces') },
    { id: 'backup', label: t('routers.tab_backup') },
    { id: 'jobs', label: t('routers.tab_jobs'), count: routerJobs.length },
    { id: 'audit', label: t('routers.tab_audit') },
  ];

  return (
    <AppShell tenantId={tenantId} title={t('nav.routers')}>
      <PageHeader
        breadcrumbs={[
          { label: t('routers.list_title'), to: `/app/${tenantId}/routers` },
          { label: r?.display_name ?? '…' },
        ]}
        title={r ? r.display_name : <Skeleton w={200} h={28} />}
        description={
          r ? `${r.model ?? t('common.unknown')} · RouterOS ${r.routeros_version ?? t('common.unknown')}${r.location ? ` · ${r.location}` : ''}` : undefined
        }
        meta={
          r ? (
            <span className="mt-row" style={{ gap: 'var(--mt-space-2)' }}>
              <EnumBadge group="vpn" value={r.health.vpn} tone={r.health.vpn === 'up' ? 'success' : r.health.vpn === 'down' ? 'warning' : 'neutral'} />
              <EnumBadge group="api" value={r.health.api} tone={r.health.api === 'up' ? 'success' : r.health.api === 'down' ? 'danger' : 'neutral'} />
              <FreshnessLabel observedAt={r.health.observed_at} />
            </span>
          ) : undefined
        }
        actions={
          can('routers.release') && r ? (
            <>
              <Button variant="secondary" onClick={() => setReplaceOpen(true)}>
                {t('routers.replace_router')}
              </Button>
              <Button variant="danger" onClick={() => setReleaseOpen(true)}>
                {t('routers.release_router')}
              </Button>
            </>
          ) : undefined
        }
      />

      {routerQ.isLoading ? (
        <Skeleton h={220} />
      ) : !r ? (
        <div className="mt-banner mt-banner-danger">
          <Icon name="alertCircle" size={20} /> {t('common.not_found')}{' '}
          <Link to={`/app/${tenantId}/routers`}>{t('common.back_to_list')}</Link>
        </div>
      ) : (
        <>
          {/* Pesan kondisi berbeda: tunnel/API/izin (UI_UX.md §7) */}
          {r.health.vpn === 'down' ? (
            <p className="mt-banner mt-banner-warning" style={{ marginBottom: 'var(--mt-space-3)' }}>
              <Icon name="shield" size={18} /> {t('routers.cond_tunnel_down')}
            </p>
          ) : r.health.api === 'down' ? (
            <p className="mt-banner mt-banner-warning" style={{ marginBottom: 'var(--mt-space-3)' }}>
              <Icon name="terminal" size={18} /> {t('routers.cond_api_down')}
            </p>
          ) : null}

          <Tabs items={tabs} active={tab} onChange={setTab} ariaLabel={t('routers.detail_tabs')} />

          <div style={{ marginTop: 'var(--mt-space-4)' }} className="mt-stack">
            {tab === 'summary' ? (
              <>
                <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                  <div className="mt-card mt-card-pad">
                    <h2 style={{ fontSize: 'var(--mt-text-base)', marginBottom: 'var(--mt-space-3)' }}>{t('routers.info_title')}</h2>
                    <dl className="mt-deflist">
                      <dt>{t('routers.f_router_code')}</dt>
                      <dd className="mt-mono">{r.router_code}</dd>
                      <dt>{t('routers.identity_label')}</dt>
                      <dd className="mt-mono">{r.identity ?? t('common.unknown')}</dd>
                      <dt>{t('routers.f_mode')}</dt>
                      <dd>{r.mode === 'managed' ? t('routers.mode_managed') : t('routers.mode_read_only')}</dd>
                      <dt>{t('routers.serial_label')}</dt>
                      <dd className="mt-mono">{r.serial ?? t('common.unknown')}</dd>
                      <dt>{t('routers.uptime_label')}</dt>
                      <dd>{r.uptime_s != null ? formatDuration(r.uptime_s, locale) : t('common.unknown')}</dd>
                    </dl>
                  </div>

                  {/* Panel RADIUS (UI_UX.md §7) */}
                  <div className="mt-card mt-card-pad">
                    <h2 style={{ fontSize: 'var(--mt-text-base)', marginBottom: 'var(--mt-space-3)' }}>{t('routers.radius_panel_title')}</h2>
                    {radiusQ.isLoading || !radius ? (
                      <Skeleton h={140} />
                    ) : (
                      <div className="mt-stack-sm">
                        <div className="mt-row-between">
                          <span className="mt-small mt-muted">{t('routers.col_enforcement')}</span>
                          <EnumBadge group="enforcement_mode" value={radius.enforcement_mode} tone={enforcementTone(radius.enforcement_mode)} />
                        </div>
                        <div className="mt-row-between">
                          <span className="mt-small mt-muted">{t('routers.radius_auth_ratio')}</span>
                          <span className="mt-small">{formatPercent(radius.auth_success_ratio_24h, locale)}</span>
                        </div>
                        <div className="mt-row-between">
                          <span className="mt-small mt-muted">{t('routers.radius_sessions')}</span>
                          <span className="mt-small">{radius.inbound_sessions_24h ?? t('common.unknown')}</span>
                        </div>
                        <div className="mt-row-between">
                          <span className="mt-small mt-muted">{t('routers.radius_last_accounting')}</span>
                          <span className="mt-small">
                            {radius.last_accounting_at ? formatDateTime(radius.last_accounting_at, locale) : t('common.unknown')}
                          </span>
                        </div>
                        <div className="mt-row-between">
                          <span className="mt-small mt-muted">{t('routers.radius_servers')}</span>
                          <span className="mt-small mt-mono">
                            {radius.radius_primary}
                            {radius.radius_secondary ? ` / ${radius.radius_secondary}` : ''}
                          </span>
                        </div>
                        {radius.client_status !== 'ok' ? (
                          <p className="mt-banner mt-banner-warning mt-small" style={{ marginBottom: 0 }}>
                            <Icon name="alertTriangle" size={16} /> {t(`routers.radius_client_${radius.client_status}` as never, undefined as never)}
                          </p>
                        ) : null}
                        <div style={{ marginTop: 'var(--mt-space-2)' }}>
                          <ButtonLink to={`/app/${tenantId}/radius`} variant="secondary" size="sm">
                            {t('routers.open_cutover')} →
                          </ButtonLink>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-card mt-card-pad">
                    <h2 style={{ fontSize: 'var(--mt-text-base)', marginBottom: 'var(--mt-space-3)' }}>{t('routers.capability_title')}</h2>
                    <ul className="mt-small mt-muted" style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {Object.entries(r.capability).map(([k, v]) => (
                        <li key={k} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {v ? (
                            <Icon name="checkCircle" size={15} style={{ color: 'var(--mt-success-fg)' }} />
                          ) : (
                            <Icon name="x" size={15} style={{ color: 'var(--mt-text-secondary)' }} />
                          )}
                          {t(`routers.cap_${k}` as never, undefined as never)}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
            ) : null}

            {tab === 'discovered' ? (
              <div className="mt-card mt-card-pad mt-stack">
                <p className="mt-small mt-muted">{t('routers.discovered_desc')}</p>
                <div className="mt-row">
                  <ButtonLink to={`/app/${tenantId}/imports/router`} variant="primary" icon="search">
                    {t('routers.cta_scan_accounts')}
                  </ButtonLink>
                </div>
              </div>
            ) : null}

            {tab === 'profiles' ? (
              <div className="mt-card mt-card-pad mt-stack">
                <p className="mt-small mt-muted">{t('routers.profiles_desc')}</p>
                <ButtonLink to={`/app/${tenantId}/packages`} variant="secondary" size="sm">
                  {t('nav.packages')} →
                </ButtonLink>
              </div>
            ) : null}

            {tab === 'interfaces' ? (
              <div className="mt-card mt-card-pad">
                <p className="mt-small mt-muted">{t('routers.interfaces_hint')}</p>
                <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
                  {t('routers.interfaces_monitoring_note')}
                </p>
                <div style={{ marginTop: 'var(--mt-space-3)' }}>
                  <ButtonLink to={`/app/${tenantId}/monitoring`} variant="secondary" size="sm">
                    {t('overview.open_monitoring')} →
                  </ButtonLink>
                </div>
              </div>
            ) : null}

            {tab === 'backup' ? (
              <div className="mt-card mt-card-pad mt-stack">
                <div className="mt-row-between">
                  <span className="mt-small mt-muted">{t('routers.backup_count', { count: backupsQ.data?.filter((b) => b.router_id === routerId).length ?? 0 })}</span>
                  <ButtonLink to={`/app/${tenantId}/backups`} variant="secondary" size="sm">
                    {t('nav.backups')} →
                  </ButtonLink>
                </div>
              </div>
            ) : null}

            {tab === 'jobs' ? (
              <div className="mt-card mt-card-pad mt-stack-sm">
                {jobsQ.isLoading ? (
                  <Skeleton h={120} />
                ) : routerJobs.length === 0 ? (
                  <p className="mt-muted mt-small">{t('jobs.empty_router')}</p>
                ) : (
                  routerJobs.map((j: JobRecord) => (
                    <Link key={j.id} to={`/app/${tenantId}/jobs/${j.id}`} className="mt-row-between" style={{ borderBottom: '1px solid var(--mt-neutral-border)', paddingBottom: 'var(--mt-space-2)', color: 'inherit', textDecoration: 'none' }}>
                      <span className="mt-small">{t(`job.kind.${j.kind}` as never, undefined as never)}</span>
                      <JobProgress job={j} compact />
                    </Link>
                  ))
                )}
              </div>
            ) : null}

            {tab === 'audit' ? (
              <div className="mt-card mt-card-pad">
                {auditQ.isLoading ? (
                  <Skeleton h={120} />
                ) : (
                  <AuditTimeline
                    entries={(auditQ.data?.items ?? []).map((a) => ({
                      id: a.id,
                      at: a.at,
                      actor: a.actor_display,
                      action: a.action_code,
                      target: a.target_display,
                    }))}
                  />
                )}
              </div>
            ) : null}
          </div>
        </>
      )}

      {/* Lepas router: aksi destruktif terpisah, menyebut dampak (UI_UX.md §7) */}
      <ConfirmAction
        open={releaseOpen}
        onClose={() => setReleaseOpen(false)}
        onConfirm={doRelease}
        loading={actionLoading}
        title={t('routers.release_confirm_title', { name: r?.display_name ?? '' })}
        intent={t('routers.release_intent')}
        scopeLines={[
          t('routers.release_scope_slot'),
          t('routers.release_scope_accounts'),
          t('routers.release_scope_history'),
        ]}
        confirmLabel={t('routers.release_router')}
        confirmTone="danger"
        requiresReauth
      />

      <ConfirmAction
        open={replaceOpen}
        onClose={() => setReplaceOpen(false)}
        onConfirm={doReplace}
        loading={actionLoading}
        title={t('routers.replace_confirm_title', { name: r?.display_name ?? '' })}
        intent={t('routers.replace_intent')}
        scopeLines={[
          t('routers.replace_scope_slot'),
          t('routers.replace_scope_accounts'),
          t('routers.replace_scope_overlap'),
        ]}
        confirmLabel={t('routers.replace_router')}
      />
    </AppShell>
  );
}
