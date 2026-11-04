import { Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { AppShell, LanguageSwitcher } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { AuditTimeline } from '../../design-system/components/DataParts';
import { Skeleton } from '../../design-system/primitives/Misc';
import SubscriptionPanel from './SubscriptionPanel';
import TeamPanel from './TeamPanel';
import { useI18n } from '../../i18n';
import { formatDateTime } from '../../lib/format';
import { Icon } from '../../design-system/primitives/Icon';

/** U18 — Tim, paket aplikasi, bahasa, audit, support grant (UI_UX.md §9). */
export default function SettingsPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();
  const t = useT();
  const api = useApi();
  const { activeTenant } = useSession();
  const { locale } = useI18n();
  const activeLocale = useActiveLocale();
  void locale;

  const auditQ = useQuery({
    queryKey: ['audit', tenantId],
    queryFn: () => api.listAuditTimeline(tenantId ?? '', null, { limit: 30 }),
    enabled: !!tenantId,
  });

  if (!tenantId) {
    void navigate;
    return null;
  }

  return (
    <AppShell tenantId={tenantId} title={t('nav.team')}>
      <Routes>
        <Route path="team" element={<TeamPanel tenantId={tenantId} />} />
        <Route path="subscription" element={<SubscriptionPanel tenantId={tenantId} />} />
        <Route path="audit" element={
          <>
            <PageHeader title={t('settings.audit_title')} description={t('settings.audit_desc')} />
            <div className="mt-card mt-card-pad">
              {auditQ.isLoading ? (
                <Skeleton h={200} />
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
          </>
        } />
        <Route path="*" element={
          <>
            <PageHeader title={t('settings.title')} description={t('settings.desc', { tenant: activeTenant?.display_name ?? '' })} />
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('settings.language_title')}</h2>
                <p className="mt-small mt-muted">{t('settings.language_desc')}</p>
                <LanguageSwitcher />
              </div>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('settings.audit_title')}</h2>
                <p className="mt-small mt-muted">{t('settings.audit_desc')}</p>
                <a className="mt-small" href={`/app/${tenantId}/settings/audit`}>
                  {t('settings.open_audit')} →
                </a>
              </div>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('settings.support_title')}</h2>
                <p className="mt-small mt-muted">{t('settings.support_desc')}</p>
                <p className="mt-xs mt-muted">
                  <Icon name="lock" size={14} style={{ verticalAlign: -2 }} /> {t('settings.support_note')}
                </p>
              </div>
            </div>
            {auditQ.data?.items[0] ? (
              <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-3)' }}>
                {t('settings.last_activity', { time: formatDateTime(auditQ.data.items[0].at, activeLocale) })}
              </p>
            ) : null}
          </>
        } />
      </Routes>
    </AppShell>
  );
}
