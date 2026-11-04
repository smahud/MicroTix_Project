import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { Tabs, Skeleton } from '../../design-system/primitives/Misc';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { EnumBadge, FreshnessLabel } from '../../design-system/components/StatusBadge';
import { ConfirmAction, PermissionNotice } from '../../design-system/components/Notices';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { TextInput } from '../../design-system/primitives/Input';
import { accountStateTone, enforcementTone } from '../../lib/statuses';
import { formatDateTime, formatPercent } from '../../lib/format';
import type { RadiusAccountRow } from '../../api/contracts';

/**
 * U19 — Basis akun akses RADIUS (UI_UX.md §16): tiga area Akun, Router, Cutover.
 * Tombol cutover memerlukan radius.cutover + MFA + reauth.
 */
export default function RadiusPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { can } = useSession();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('accounts');
  const [search, setSearch] = useState('');
  const [cutoverOpen, setCutoverOpen] = useState(false);
  const [cutoverRouter, setCutoverRouter] = useState<string | null>(null);
  const [cutting, setCutting] = useState(false);
  const [reauthPassword, setReauthPassword] = useState('');
  const [reauthTotp, setReauthTotp] = useState('');
  const [reauthError, setReauthError] = useState<string | null>(null);

  const accountsQ = useQuery({
    queryKey: ['radius-accounts', tenantId, search],
    queryFn: () => api.listRadiusAccounts(tenantId, { query: search || undefined }, { limit: 50 }),
  });
  const statusQ = useQuery({
    queryKey: ['radius-status', tenantId],
    queryFn: () => api.listRadiusRouterStatus(tenantId),
    refetchInterval: 30_000,
  });
  const routersQ = useQuery({ queryKey: ['routers', tenantId], queryFn: () => api.listRouters(tenantId) });

  const routerName = useCallback(
    (id: string) => routersQ.data?.find((r) => r.id === id)?.display_name ?? id,
    [routersQ.data],
  );

  const doReauth = async (): Promise<boolean> => {
    try {
      await api.reauthenticate(reauthPassword, reauthTotp);
      return true;
    } catch {
      setReauthError(t('auth.reauth_failed'));
      return false;
    }
  };

  const startCutover = async () => {
    if (!cutoverRouter) return;
    setCutting(true);
    const ok = await doReauth();
    if (!ok) {
      setCutting(false);
      return;
    }
    try {
      const res = await api.startRadiusCutover(tenantId, cutoverRouter);
      setCutoverOpen(false);
      setReauthPassword('');
      setReauthTotp('');
      setReauthError(null);
      toast(t('radius.cutover_started'), 'success');
      await queryClient.invalidateQueries({ queryKey: ['radius-status', tenantId] });
      window.location.assign(`/app/${tenantId}/jobs/${res.job_id}`);
    } catch (err) {
      const e = err as { envelope?: { message?: string } };
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
    } finally {
      setCutting(false);
    }
  };

  const columns: Column<RadiusAccountRow>[] = useMemo(
    () => [
      {
        key: 'username',
        header: t('radius.col_username'),
        render: (a) => <span className="mt-mono mt-small" style={{ fontWeight: 500 }}>{a.username}</span>,
      },
      {
        key: 'kind',
        header: t('radius.col_kind'),
        render: (a) => (a.kind === 'hotspot' ? 'Hotspot' : 'PPPoE'),
        hideOnMobile: true,
      },
      {
        key: 'state',
        header: t('radius.col_state'),
        render: (a) => <EnumBadge group="account_state" value={a.state} tone={accountStateTone(a.state)} />,
      },
      {
        key: 'credential',
        header: t('radius.col_credential'),
        render: (a) => <EnumBadge group="credential_state" value={a.credential_state} tone={a.credential_state === 'ready' ? 'success' : a.credential_state === 'unknown' ? 'warning' : 'info'} />,
      },
      {
        key: 'package',
        header: t('customers.col.package'),
        render: (a) => a.package_name ?? <span className="mt-xs mt-muted">{t('common.not_set')}</span>,
        hideOnMobile: true,
      },
      {
        key: 'router',
        header: t('radius.col_restriction'),
        render: (a) =>
          a.restricting_router_id ? (
            <Link to={`/app/${tenantId}/routers/${a.restricting_router_id}`} className="mt-small">
              {routerName(a.restricting_router_id)}
            </Link>
          ) : (
            <span className="mt-xs mt-muted">{t('customers.access_all_routers')}</span>
          ),
        hideOnMobile: true,
      },
      {
        key: 'last',
        header: t('radius.col_last_session'),
        render: (a) => <FreshnessLabel observedAt={a.last_active_session_at} />,
        hideOnMobile: true,
      },
    ],
    [t, tenantId, routerName],
  );

  const tabs = [
    { id: 'accounts', label: t('radius.tab_accounts'), count: accountsQ.data?.items.length },
    { id: 'routers', label: t('radius.tab_routers'), count: statusQ.data?.length },
    { id: 'cutover', label: t('radius.tab_cutover') },
  ];

  return (
    <AppShell tenantId={tenantId} title={t('nav.radius')}>
      <PageHeader
        title={t('radius.title')}
        description={t('radius.desc')}
      />

      <Tabs items={tabs} active={tab} onChange={setTab} ariaLabel={t('radius.tabs_label')} />

      <div style={{ marginTop: 'var(--mt-space-4)' }} className="mt-stack">
        {tab === 'accounts' ? (
          <>
            {/* Password tidak pernah tampil di tabel (UI_UX.md §16) */}
            <div className="mt-filterbar">
              <div className="mt-input-wrap" style={{ flex: '1 1 220px', maxWidth: 320 }}>
                <span className="mt-input-icon">
                  <Icon name="search" size={18} />
                </span>
                <input
                  className="mt-input"
                  placeholder={t('radius.search_placeholder')}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  aria-label={t('radius.search_label')}
                  type="search"
                />
              </div>
              <span className="mt-filterbar-spacer" />
              <span className="mt-xs mt-muted">{t('radius.password_never_shown')}</span>
            </div>
            <DataTable
              rows={accountsQ.data?.items ?? []}
              columns={columns}
              rowKey={(a) => a.id}
              loading={accountsQ.isLoading}
              emptyTitle={t('radius.empty_accounts_title')}
              emptyDescription={t('radius.empty_accounts_desc')}
              caption={t('radius.table_caption')}
            />
          </>
        ) : null}

        {tab === 'routers' ? (
          statusQ.isLoading ? (
            <Skeleton h={200} />
          ) : (
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
              {(statusQ.data ?? []).map((s) => (
                <div key={s.router_id} className="mt-card mt-card-pad mt-stack-sm">
                  <div className="mt-row-between">
                    <Link to={`/app/${tenantId}/routers/${s.router_id}`} style={{ fontWeight: 600, color: 'var(--mt-text)', textDecoration: 'none' }}>
                      {routerName(s.router_id)}
                    </Link>
                    <EnumBadge group="enforcement_mode" value={s.enforcement_mode} tone={enforcementTone(s.enforcement_mode)} />
                  </div>
                  <dl className="mt-deflist" style={{ gridTemplateColumns: 'minmax(120px, 160px) 1fr' }}>
                    <dt>{t('radius.migrated_accounts')}</dt>
                    <dd>{s.migrated_accounts}</dd>
                    <dt>{t('radius.auth_ratio_24h')}</dt>
                    <dd>{formatPercent(s.auth_success_ratio_24h, locale)}</dd>
                    <dt>{t('radius.sessions_24h')}</dt>
                    <dd>{s.inbound_sessions_24h ?? t('common.unknown')}</dd>
                    <dt>{t('radius.last_accounting')}</dt>
                    <dd>{s.last_accounting_at ? formatDateTime(s.last_accounting_at, locale) : t('common.unknown')}</dd>
                    <dt>{t('radius.servers')}</dt>
                    <dd className="mt-mono mt-small">
                      {s.radius_primary}
                      {s.radius_secondary ? ` / ${s.radius_secondary}` : ''}
                    </dd>
                    <dt>{t('radius.client_status')}</dt>
                    <dd>
                      <EnumBadge group="radius_client" value={s.client_status} tone={s.client_status === 'ok' ? 'success' : s.client_status === 'degraded' ? 'danger' : 'warning'} />
                    </dd>
                  </dl>
                  {s.enforcement_mode !== 'radius_authoritative' ? (
                    <Button variant="secondary" size="sm" onClick={() => { setCutoverRouter(s.router_id); setCutoverOpen(true); }} disabled={!can('radius.cutover')}>
                      {t('radius.open_cutover_cta')}
                    </Button>
                  ) : null}
                  {!can('radius.cutover') && s.enforcement_mode !== 'radius_authoritative' ? (
                    <p className="mt-xs mt-muted">{t('radius.cutover_permission_note')}</p>
                  ) : null}
                </div>
              ))}
            </div>
          )
        ) : null}

        {tab === 'cutover' ? (
          <div className="mt-stack">
            {!can('radius.cutover') ? (
              <PermissionNotice what={t('permission.radius_cutover')} />
            ) : null}
            <p className="mt-banner mt-banner-info">
              <Icon name="info" size={18} />
              {t('radius.cutover_intro')}
            </p>
            {/* Stepper B0–B6 ringkas sesuai RADIUS.md §10.2 */}
            <ol className="mt-stack-sm" style={{ paddingLeft: 0, listStyle: 'none' }}>
              {['b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6'].map((b) => (
                <li key={b} className="mt-card mt-card-pad mt-stack-sm">
                  <strong>{t(`radius.cutover_${b}_title` as never, undefined as never)}</strong>
                  <span className="mt-small mt-muted" style={{ display: 'block' }}>
                    {t(`radius.cutover_${b}_desc` as never, undefined as never)}
                  </span>
                </li>
              ))}
            </ol>
            <p className="mt-xs mt-muted">{t('radius.cutover_exit_note')}</p>
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
              {(statusQ.data ?? [])
                .filter((s) => s.enforcement_mode !== 'radius_authoritative')
                .map((s) => (
                  <div key={s.router_id} className="mt-card mt-card-pad mt-stack-sm">
                    <strong>{routerName(s.router_id)}</strong>
                    <EnumBadge group="enforcement_mode" value={s.enforcement_mode} tone={enforcementTone(s.enforcement_mode)} />
                    <Button variant="primary" size="sm" onClick={() => { setCutoverRouter(s.router_id); setCutoverOpen(true); }} disabled={!can('radius.cutover')}>
                      {t('radius.start_cutover')}
                    </Button>
                  </div>
                ))}
            </div>
            <p className="mt-xs mt-muted">{t('radius.rollback_note')}</p>
          </div>
        ) : null}
      </div>

      <ConfirmAction
        open={cutoverOpen}
        onClose={() => {
          setCutoverOpen(false);
          setReauthError(null);
        }}
        onConfirm={startCutover}
        loading={cutting}
        title={t('radius.cutover_confirm_title', { name: cutoverRouter ? routerName(cutoverRouter) : '' })}
        intent={t('radius.cutover_confirm_intent')}
        scopeLines={[
          t('radius.cutover_scope_settings'),
          t('radius.cutover_scope_accounts', { count: statusQ.data?.find((s) => s.router_id === cutoverRouter)?.migrated_accounts ?? 0 }),
          t('radius.cutover_scope_batches'),
          t('radius.cutover_scope_rollback'),
        ]}
        confirmLabel={t('radius.start_cutover')}
        requiresReauth
      >
        <div className="mt-stack-sm">
          <TextInput
            label={t('auth.reauth_password')}
            type="password"
            value={reauthPassword}
            onChange={(e) => setReauthPassword(e.target.value)}
            autoComplete="current-password"
          />
          <TextInput
            label={t('auth.field_totp')}
            inputMode="numeric"
            maxLength={6}
            value={reauthTotp}
            onChange={(e) => setReauthTotp(e.target.value.replace(/\D/g, ''))}
            placeholder="••••••"
          />
          {reauthError ? (
            <p className="mt-field-error" role="alert">
              <Icon name="alertCircle" size={16} /> {reauthError}
            </p>
          ) : null}
          <p className="mt-xs mt-muted">{t('auth.reauth_window_note')}</p>
        </div>
      </ConfirmAction>
    </AppShell>
  );
}
