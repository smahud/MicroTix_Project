import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useI18n, LANGUAGE_NAMES, LOCALES } from '../../i18n';
import { useBranding } from '../../branding';
import { useApi } from '../../api';
import { formatMoney } from '../../lib/format';
import { ButtonLink } from '../../design-system/primitives/Button';
import { LanguageSwitcher } from '../../design-system/components/AppShell';
import { Icon } from '../../design-system/primitives/Icon';
import { Segmented } from '../../design-system/primitives/Misc';
import { useState } from 'react';
import type { PlanInfo } from '../../api/contracts';
import './landing.css';

/**
 * U01 — Landing: manfaat, fitur yang benar-benar tersedia (R1), harga
 * bulanan/tahunan dengan dua batas terpisah, masuk/daftar.
 * Rekening bank TIDAK ditampilkan di landing (UI_UX.md §9).
 */
export default function Landing() {
  const t = useT();
  const branding = useBranding();
  const api = useApi();
  const locale = useActiveLocale();
  const { locale: activeLocale, setLocale } = useI18n();
  const [term, setTerm] = useState<'monthly' | 'yearly'>('monthly');
  const { data: plans } = useQuery({ queryKey: ['plans'], queryFn: () => api.getPlans() });

  return (
    <div className="mt-landing">
      <header className="mt-landing-header">
        <span className="mt-brand-mark" aria-hidden="true">
          M
        </span>
        <span className="mt-brand-name">{branding.display_name}</span>
        <span style={{ flex: 1 }} />
        <LanguageSwitcher />
        <ButtonLink to="/login" variant="secondary" size="sm">
          {t('landing.login')}
        </ButtonLink>
        <ButtonLink to="/register" variant="primary" size="sm">
          {t('landing.register')}
        </ButtonLink>
      </header>

      <section className="mt-landing-hero">
        <h1>{t('landing.hero_title', { brand: branding.display_name })}</h1>
        <p className="mt-landing-sub">{t('landing.hero_sub')}</p>
        <div className="mt-row" style={{ justifyContent: 'center' }}>
          <ButtonLink to="/register" variant="primary" icon="zap">
            {t('landing.cta_start_free')}
          </ButtonLink>
          <ButtonLink to="/login" variant="secondary">
            {t('landing.cta_login')}
          </ButtonLink>
        </div>
        {branding.publication_blocked ? (
          <p className="mt-xs mt-muted mt-landing-note">{t('landing.publication_note')}</p>
        ) : null}
      </section>

      <section className="mt-landing-section">
        <h2>{t('landing.benefits_title', { brand: branding.display_name })}</h2>
        <div className="mt-landing-grid">
          {(
            [
              { icon: 'router', key: 'adopt' },
              { icon: 'users', key: 'customers' },
              { icon: 'shield', key: 'radius' },
              { icon: 'database', key: 'backup' },
            ] as const
          ).map((b) => (
            <article key={b.key} className="mt-card mt-card-pad">
              <span className="mt-landing-benefit-icon">
                <Icon name={b.icon} size={22} />
              </span>
              <h3>{t(`landing.benefit_${b.key}_title` as never, undefined as never)}</h3>
              <p className="mt-small mt-muted">{t(`landing.benefit_${b.key}_desc` as never, undefined as never)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-landing-section">
        <h2>{t('landing.pricing_title')}</h2>
        <p className="mt-muted mt-small" style={{ marginBottom: 'var(--mt-space-4)' }}>
          {t('landing.pricing_sub')}
        </p>
        <div className="mt-row" style={{ justifyContent: 'center', marginBottom: 'var(--mt-space-6)' }}>
          <Segmented
            ariaLabel={t('landing.term_toggle')}
            value={term}
            onChange={setTerm}
            options={[
              { value: 'monthly', label: t('landing.term_monthly') },
              { value: 'yearly', label: t('landing.term_yearly') },
            ]}
          />
        </div>
        {term === 'yearly' ? (
          <p className="mt-small mt-muted" style={{ textAlign: 'center', marginBottom: 'var(--mt-space-4)' }}>
            {t('landing.yearly_note')}
          </p>
        ) : null}
        <div className="mt-landing-grid">
          {(plans ?? []).map((p) => (
            <PlanCard key={p.code} plan={p} term={term} locale={locale} />
          ))}
        </div>
        <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-4)', textAlign: 'center' }}>
          {t('landing.platinum_fair_use_note')}
        </p>
      </section>

      <footer className="mt-landing-footer">
        <div className="mt-row-between">
          <span className="mt-small mt-muted">
            © 2026 {branding.display_name}
          </span>
          <span className="mt-row mt-small mt-muted">
            {LOCALES.map((l) => (
              <button
                key={l}
                type="button"
                className="mt-btn mt-btn-ghost mt-btn-sm"
                aria-pressed={activeLocale === l}
                onClick={() => setLocale(l)}
              >
                {LANGUAGE_NAMES[l]}
              </button>
            ))}
          </span>
        </div>
      </footer>
    </div>
  );
}

function PlanCard({ plan, term, locale }: { plan: PlanInfo; term: 'monthly' | 'yearly'; locale: 'id' | 'en' }) {
  const t = useT();
  const free = plan.code === 'free';
  const amount = free ? t('landing.price_free') : formatMoney(term === 'monthly' ? plan.monthly_price : plan.yearly_price, locale);
  const isCurrent = false;
  void isCurrent;
  return (
    <article className={`mt-card mt-card-pad mt-plan${plan.code === 'silver' ? ' mt-plan-highlight' : ''}`}>
      {plan.code === 'silver' ? <span className="mt-plan-tag">{t('landing.plan_popular')}</span> : null}
      <h3>{t(`landing.plan_${plan.code}` as never, undefined as never)}</h3>
      <div className="mt-plan-price">{amount}</div>
      <div className="mt-xs mt-muted">
        {term === 'monthly' ? t('landing.per_month') : t('landing.per_year')}
      </div>
      <ul className="mt-plan-limits">
        <li>
          <Icon name="router" size={16} />
          {plan.routers_limit == null
            ? t('landing.routers_unlimited')
            : t('landing.routers_limit', { count: plan.routers_limit })}
        </li>
        <li>
          <Icon name="users" size={16} />
          {plan.services_limit == null
            ? t('landing.services_unlimited')
            : t('landing.services_limit', { count: plan.services_limit })}
        </li>
      </ul>
      <Link to="/register" className="mt-btn mt-btn-secondary" style={{ marginTop: 'auto' }}>
        {free ? t('landing.cta_start_free') : t('landing.plan_choose')}
      </Link>
    </article>
  );
}
