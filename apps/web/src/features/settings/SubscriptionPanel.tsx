import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { PageHeader } from '../../design-system/components/PageHeader';
import { MetricCard } from '../../design-system/components/MetricCard';
import { ProgressBar } from '../../design-system/primitives/Misc';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { ConfirmAction } from '../../design-system/components/Notices';
import { formatMoney, formatDateFull } from '../../lib/format';
import { subscriptionStateTone } from '../../lib/statuses';

/**
 * U18 Paket aplikasi (UI_UX.md §9): paket aktif, periode, pemakaian
 * router/layanan, invoice tertunda, upgrade/downgrade dengan penjelasan.
 */
export default function SubscriptionPanel({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { can } = useSession();
  const { toast } = useToast();
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [upgradePlan, setUpgradePlan] = useState<string | null>(null);
  const [quoting, setQuoting] = useState(false);

  const subQ = useQuery({ queryKey: ['subscription', tenantId], queryFn: () => api.getSubscription(tenantId) });
  const plansQ = useQuery({ queryKey: ['plans'], queryFn: () => api.getPlans() });

  const sub = subQ.data;

  const requestQuotation = async () => {
    if (!upgradePlan) return;
    setQuoting(true);
    try {
      const res = await api.requestQuotation(tenantId, upgradePlan, 'monthly');
      setUpgradeOpen(false);
      toast(t('settings.quotation_created', { amount: formatMoney(res.amount, locale) }), 'success');
      await subQ.refetch();
    } catch (err) {
      const e = err as { envelope?: { message?: string } };
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
    } finally {
      setQuoting(false);
    }
  };

  if (subQ.isLoading) {
    return (
      <>
        <PageHeader title={t('settings.subscription_title')} />
        <div className="mt-stack">
          <ProgressBar value={0} max={100} />
        </div>
      </>
    );
  }
  if (!sub) return null;

  const stateCopy: Record<string, string> = {
    active: t('settings.sub_state_active'),
    free: t('settings.sub_state_free'),
    grace: t('settings.sub_state_grace'),
    restricted: t('settings.sub_state_restricted'),
    ended: t('settings.sub_state_ended'),
    pending: t('settings.sub_state_pending'),
  };

  return (
    <>
      <PageHeader
        title={t('settings.subscription_title')}
        description={
          can('subscription.manage')
            ? t('settings.subscription_desc')
            : t('settings.subscription_view_only')
        }
        meta={
          <EnumBadge group="subscription_state" value={sub.state} tone={subscriptionStateTone(sub.state)} />
        }
      />

      <div className="mt-stack">
        {sub.state === 'grace' || sub.state === 'restricted' ? (
          <p className={`mt-banner ${sub.state === 'grace' ? 'mt-banner-warning' : 'mt-banner-warning'}`}>
            <Icon name="alertTriangle" size={18} />
            {stateCopy[sub.state]}
          </p>
        ) : null}

        <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          <div className="mt-card mt-card-pad mt-stack-sm">
            <span className="mt-xs mt-muted">{t('settings.sub_plan')}</span>
            <strong style={{ fontSize: 'var(--mt-text-lg)' }}>{t(`landing.plan_${sub.plan.code}` as never, undefined as never)}</strong>
            <span className="mt-small mt-muted">
              {sub.period_start && sub.period_end
                ? `${formatDateFull(sub.period_start, locale)} — ${formatDateFull(sub.period_end, locale)}`
                : t('settings.sub_no_period')}
            </span>
          </div>
          <MetricCard
            label={t('settings.sub_routers_used')}
            value={`${sub.usage.routers_used} / ${sub.plan.routers_limit ?? '∞'}`}
            to={`/app/${tenantId}/routers`}
          />
          <MetricCard
            label={t('settings.sub_services_used')}
            value={`${sub.usage.services_used} / ${sub.plan.services_limit ?? '∞'}`}
            to={`/app/${tenantId}/customers`}
          />
          <MetricCard
            label={t('settings.sub_drafts_used')}
            value={`${sub.usage.draft_used} / ${sub.usage.draft_cap}`}
            hint={t('settings.sub_drafts_hint')}
          />
        </div>

        {/* Penggunaan kuota layanan */}
        <div className="mt-card mt-card-pad mt-stack-sm">
          <span className="mt-small mt-muted">{t('settings.sub_quota_label')}</span>
          <ProgressBar value={sub.usage.services_used} max={sub.plan.services_limit ?? sub.usage.services_used} />
          <span className="mt-xs mt-muted">
            {t('settings.sub_quota_note', { used: sub.usage.services_used, limit: sub.plan.services_limit ?? '∞' })}
          </span>
        </div>

        {sub.pending_invoice ? (
          <div className="mt-banner mt-banner-info">
            <Icon name="fileText" size={18} />
            <div>
              <strong>{t('settings.sub_pending_invoice')}</strong>
              <p className="mt-small">
                {formatMoney(sub.pending_invoice.amount, locale)} · {t('settings.sub_due', { date: formatDateFull(sub.pending_invoice.due_at, locale) })}
              </p>
              <Button variant="secondary" size="sm" icon="upload" onClick={() => toast(t('settings.upload_blocked_note'), 'info')}>
                {t('settings.upload_proof_cta')}
              </Button>
            </div>
          </div>
        ) : null}

        {/* Naik/turun paket */}
        {can('subscription.manage') ? (
          <div className="mt-card mt-card-pad mt-stack">
            <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('settings.change_plan_title')}</h2>
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
              {(plansQ.data ?? [])
                .filter((p) => p.code !== sub.plan.code && p.code !== 'free')
                .map((p) => (
                  <div key={p.code} className="mt-card mt-card-pad mt-stack-sm">
                    <strong>{t(`landing.plan_${p.code}` as never, undefined as never)}</strong>
                    <span>{formatMoney(p.monthly_price, locale)}</span>
                    <span className="mt-xs mt-muted">
                      {t('landing.routers_limit', { count: p.routers_limit ?? 0 })} ·{' '}
                      {t('landing.services_limit', { count: p.services_limit ?? 0 })}
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setUpgradePlan(p.code);
                        setUpgradeOpen(true);
                      }}
                    >
                      {t('settings.request_upgrade')}
                    </Button>
                  </div>
                ))}
            </div>
            <p className="mt-xs mt-muted">{t('settings.upgrade_note')}</p>
            <p className="mt-xs mt-muted">{t('settings.downgrade_note')}</p>
          </div>
        ) : null}
      </div>

      <ConfirmAction
        open={upgradeOpen}
        onClose={() => setUpgradeOpen(false)}
        onConfirm={requestQuotation}
        loading={quoting}
        title={t('settings.quotation_title')}
        intent={t('settings.quotation_intent', { plan: upgradePlan ? t(`landing.plan_${upgradePlan}` as never, undefined as never) : '' })}
        scopeLines={[
          t('settings.quotation_scope_period'),
          t('settings.quotation_scope_bonus'),
          t('settings.quotation_scope_invoice'),
        ]}
        confirmLabel={t('settings.quotation_confirm')}
      />
    </>
  );
}
