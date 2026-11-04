import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale, useEnumLabel } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { Tabs } from '../../design-system/primitives/Misc';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { StatusQuad } from '../../design-system/components/DataParts';
import { AuditTimeline } from '../../design-system/components/DataParts';
import { Button, ButtonLink } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { Dialog } from '../../design-system/primitives/Dialog';
import { Skeleton } from '../../design-system/primitives/Misc';
import { connectionTone, jobDimensionTone, lifecycleTone, accountStateTone } from '../../lib/statuses';
import { formatDateTime } from '../../lib/format';
import { isReleased } from '../../permissions/release-flags';
import { useToast } from '../../design-system/primitives/Toast';

/**
 * U04 detail layanan: tab Ringkasan, Tagihan (R2), Akses, Jaringan, Perangkat, Riwayat
 * (UI_UX.md §5). Ringkasan memisahkan bayar/isolir/koneksi/job.
 */
export default function CustomerDetailPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const enumLabel = useEnumLabel();
  const { serviceId } = useParams<{ serviceId: string }>();
  const [params] = useSearchParams();
  const { can } = useSession();
  const { toast } = useToast();
  const [tab, setTab] = useState('summary');
  const [revealOpen, setRevealOpen] = useState(false);
  const [revealLoading, setRevealLoading] = useState(false);
  const [revealed, setRevealed] = useState<{ username: string; password: string } | null>(null);
  const [reauthNeeded, setReauthNeeded] = useState(false);

  const serviceQ = useQuery({
    queryKey: ['service', tenantId, serviceId],
    queryFn: () => api.getService(tenantId, serviceId!),
    enabled: !!serviceId,
  });
  const auditQ = useQuery({
    queryKey: ['audit', tenantId, serviceId],
    queryFn: () => api.listAuditTimeline(tenantId, serviceId ?? null, { limit: 20 }),
    enabled: tab === 'history',
  });

  const s = serviceQ.data;
  const backParams = params.get('back');

  const tabs = [
    { id: 'summary', label: t('customers.tab_summary') },
    ...(isReleased('billing') ? [{ id: 'billing', label: t('customers.tab_billing') }] : []),
    { id: 'access', label: t('customers.tab_access') },
    { id: 'network', label: t('customers.tab_network') },
    { id: 'devices', label: t('customers.tab_devices') },
    { id: 'history', label: t('customers.tab_history') },
  ];

  const doReveal = async () => {
    if (!serviceId) return;
    setRevealLoading(true);
    try {
      const res = await api.revealCredential(tenantId, serviceId);
      setRevealed({ username: res.username, password: res.password });
      setReauthNeeded(false);
      // Auto-sembunyi 30 detik (UI_UX.md §3)
      window.setTimeout(() => setRevealed(null), 30_000);
    } catch (err) {
      const e = err as { code?: string };
      if (e.code === 'forbidden') setReauthNeeded(true);
      else toast(t('common.error_generic'), 'danger');
    } finally {
      setRevealLoading(false);
    }
  };

  return (
    <AppShell tenantId={tenantId} title={t('nav.customers')}>
      <PageHeader
        breadcrumbs={[
          { label: t('customers.title'), to: `/app/${tenantId}/customers${backParams ? `?${backParams}` : ''}` },
          { label: s ? s.service_code : '…' },
        ]}
        title={s ? s.customer_name : <Skeleton w={180} h={28} />}
        description={s ? `${s.service_code} · ${s.customer_code}` : undefined}
        meta={
          s ? (
            <span className="mt-row" style={{ gap: 'var(--mt-space-2)' }}>
              <EnumBadge group="lifecycle" value={s.lifecycle} tone={lifecycleTone(s.lifecycle)} />
            </span>
          ) : undefined
        }
        actions={
          <ButtonLink to={`/app/${tenantId}/jobs`} variant="secondary" icon="list">
            {t('customers.open_jobs')}
          </ButtonLink>
        }
      />

      {serviceQ.isLoading ? (
        <div className="mt-stack">
          <Skeleton h={120} />
          <Skeleton h={200} />
        </div>
      ) : serviceQ.error ? (
        <div className="mt-banner mt-banner-danger">
          <Icon name="alertCircle" size={20} />
          {t('common.not_found')}{' '}
          <Link to={`/app/${tenantId}/customers`}>{t('common.back_to_list')}</Link>
        </div>
      ) : s ? (
        <>
          {/* Empat dimensi terpisah pada ringkasan (UI_UX.md §5) */}
          <div className="mt-card mt-card-pad" style={{ marginBottom: 'var(--mt-space-4)' }}>
            <div className="mt-svc-statuses">
              <StatusQuad service={s} />
            </div>
          </div>

          <Tabs items={tabs} active={tab} onChange={setTab} ariaLabel={t('customers.detail_tabs')} />

          <div style={{ marginTop: 'var(--mt-space-4)' }}>
            {tab === 'summary' ? (
              <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                <div className="mt-card mt-card-pad">
                  <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
                    {t('customers.info_title')}
                  </h2>
                  <dl className="mt-deflist">
                    <dt>{t('customers.col.service_kind')}</dt>
                    <dd>{s.kind === 'hotspot' ? 'Hotspot' : 'PPPoE'}</dd>
                    <dt>{t('customers.f_start_date')}</dt>
                    <dd>{s.start_date ?? t('common.not_set')}</dd>
                    <dt>{t('customers.f_contact')}</dt>
                    <dd>{s.contact ?? t('common.not_set')}</dd>
                    <dt>{t('customers.f_address')}</dt>
                    <dd>{s.address ?? t('common.not_set')}</dd>
                    <dt>{t('customers.f_package')}</dt>
                    <dd>{s.package_name ?? t('common.not_set')}</dd>
                  </dl>
                </div>
                <div className="mt-card mt-card-pad">
                  <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
                    {t('customers.job_title')}
                  </h2>
                  {s.job === 'none' ? (
                    <p className="mt-muted mt-small">{t('customers.job_none')}</p>
                  ) : (
                    <p className="mt-small">
                      <EnumBadge group="job_dimension" value={s.job} tone={jobDimensionTone(s.job)} />
                    </p>
                  )}
                  <div style={{ marginTop: 'var(--mt-space-3)' }}>
                    <ButtonLink to={`/app/${tenantId}/jobs`} variant="secondary" size="sm" iconRight="arrowRight">
                      {t('customers.open_jobs')}
                    </ButtonLink>
                  </div>
                </div>
              </div>
            ) : null}

            {tab === 'access' ? (
              <div className="mt-card mt-card-pad mt-stack">
                {!s.access?.username ? (
                  <p className="mt-muted">{t('customers.access_none')}</p>
                ) : (
                  <>
                    <dl className="mt-deflist">
                      <dt>{t('radius.col_username')}</dt>
                      <dd className="mt-mono">{s.access.username}</dd>
                      <dt>{t('customers.access_state')}</dt>
                      <dd>
                        <EnumBadge group="account_state" value={s.access.state} tone={accountStateTone(s.access.state ?? '')} />
                      </dd>
                      <dt>{t('customers.access_credential')}</dt>
                      <dd>{enumLabel('credential_state', s.access.credential_state)}</dd>
                      <dt>{t('customers.access_session_limit')}</dt>
                      <dd>{s.access.session_limit ?? t('common.not_set')}</dd>
                      <dt>{t('customers.access_mac_lock')}</dt>
                      <dd>{s.access.mac_locked == null ? t('common.unknown') : s.access.mac_locked ? t('common.yes') : t('common.no')}</dd>
                      <dt>{t('customers.access_last_session')}</dt>
                      <dd>
                        {s.access.last_active_session_at ? (
                          formatDateTime(s.access.last_active_session_at, locale)
                        ) : (
                          t('common.unknown')
                        )}
                      </dd>
                      <dt>{t('customers.access_restricting_router')}</dt>
                      <dd>
                        {s.access.restricting_router_id ? (
                          <Link to={`/app/${tenantId}/routers/${s.access.restricting_router_id}`}>
                            {s.router_display_name ?? s.access.restricting_router_id}
                          </Link>
                        ) : (
                          t('customers.access_all_routers')
                        )}
                      </dd>
                    </dl>
                    {can('services.reveal_credentials') ? (
                      <div>
                        <Button variant="secondary" icon="eye" onClick={() => setRevealOpen(true)}>
                          {t('customers.reveal_password')}
                        </Button>
                        <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
                          {t('customers.reveal_note')}
                        </p>
                      </div>
                    ) : (
                      <p className="mt-banner mt-banner-warning">
                        <Icon name="lock" size={18} /> {t('customers.reveal_no_permission')}
                      </p>
                    )}
                  </>
                )}
              </div>
            ) : null}

            {tab === 'network' ? (
              <div className="mt-card mt-card-pad">
                <dl className="mt-deflist">
                  <dt>{t('customers.col.router')}</dt>
                  <dd>
                    {s.router_id ? (
                      <Link to={`/app/${tenantId}/routers/${s.router_id}`}>{s.router_display_name}</Link>
                    ) : (
                      t('customers.access_all_routers')
                    )}
                  </dd>
                  <dt>{t('customers.col.connection')}</dt>
                  <dd>
                    <EnumBadge group="connection" value={s.connection} tone={connectionTone(s.connection)} />
                  </dd>
                </dl>
                <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-3)' }}>
                  {t('customers.network_note')}
                </p>
                <div style={{ marginTop: 'var(--mt-space-3)' }}>
                  <ButtonLink to={`/app/${tenantId}/monitoring`} variant="secondary" size="sm">
                    {t('overview.open_monitoring')} →
                  </ButtonLink>
                </div>
              </div>
            ) : null}

            {tab === 'devices' ? (
              <div className="mt-card mt-card-pad">
                <p className="mt-muted">{t('customers.devices_none')}</p>
                <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
                  {t('customers.devices_r3_note')}
                </p>
              </div>
            ) : null}

            {tab === 'history' ? (
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
      ) : null}

      <Dialog
        open={revealOpen}
        onClose={() => {
          setRevealOpen(false);
          setRevealed(null);
          setReauthNeeded(false);
        }}
        title={t('customers.reveal_title')}
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setRevealOpen(false);
                setRevealed(null);
              }}
            >
              {t('common.close')}
            </Button>
            {!revealed ? (
              <Button variant="primary" onClick={doReveal} loading={revealLoading}>
                {t('customers.reveal_confirm')}
              </Button>
            ) : null}
          </>
        }
      >
        {reauthNeeded ? (
          <p className="mt-banner mt-banner-warning">
            <Icon name="shield" size={18} /> {t('auth.reauth_required_note')}{' '}
            <Link to={`/app/${tenantId}/settings`} onClick={() => setRevealOpen(false)}>
              {t('auth.reauth_cta')}
            </Link>
          </p>
        ) : revealed ? (
          <div className="mt-stack">
            <p className="mt-small mt-muted">{t('customers.reveal_shown_once')}</p>
            <div className="mt-reveal-box">
              <span className="mt-mono">{revealed.password}</span>
              <span style={{ flex: 1 }} />
              <Button
                variant="secondary"
                size="sm"
                icon="copy"
                onClick={() => {
                  void navigator.clipboard?.writeText(revealed.password);
                  toast(t('common.copied'), 'success');
                }}
              >
                {t('common.copy')}
              </Button>
            </div>
            <p className="mt-xs" style={{ color: 'var(--mt-warning-fg)' }}>
              {t('customers.reveal_auto_hide', { seconds: 30 })}
            </p>
          </div>
        ) : (
          <p>{t('customers.reveal_intent')}</p>
        )}
      </Dialog>
    </AppShell>
  );
}
