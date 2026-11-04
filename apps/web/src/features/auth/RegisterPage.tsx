import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useBranding } from '../../branding';
import { TextInput } from '../../design-system/primitives/Input';
import { Button } from '../../design-system/primitives/Button';
import { LanguageSwitcher } from '../../design-system/components/AppShell';
import { Icon } from '../../design-system/primitives/Icon';
import { passwordStrength } from '../../lib/format';
import '../landing/landing.css';

interface FieldErrs {
  [k: string]: string | undefined;
}

/** Daftar: nama, email, password (min 12, indikator kekuatan), nama perusahaan (UI_UX.md §3). */
export default function RegisterPage() {
  const t = useT();
  const api = useApi();
  const branding = useBranding();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', company_name: '' });
  const [errors, setErrors] = useState<FieldErrs>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const strength = useMemo(() => passwordStrength(form.password), [form.password]);
  const strengthLabel =
    strength >= 80 ? t('auth.strength_strong') : strength >= 55 ? t('auth.strength_good') : strength > 0 ? t('auth.strength_weak') : '';

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setFormError(null);
    const errs: FieldErrs = {};
    if (!form.full_name.trim()) errs.full_name = t('validation.required');
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) errs.email = t('validation.email_invalid');
    if (form.password.length < 12) errs.password = t('validation.password_min', { count: 12 });
    if (!form.company_name.trim()) errs.company_name = t('validation.required');
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setLoading(true);
    try {
      await api.register(form);
      setDone(true);
    } catch (err) {
      const fe = (err as { envelope?: { field_errors?: Record<string, Array<{ message: string }>> } }).envelope?.field_errors;
      if (fe) {
        const mapped: FieldErrs = {};
        for (const [k, v] of Object.entries(fe)) mapped[k] = v[0]?.message;
        setErrors(mapped);
      } else {
        setFormError(t('common.error_generic'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-auth">
      <div className="mt-auth-header">
        <Link to="/" className="mt-row" style={{ textDecoration: 'none', color: 'inherit', gap: 'var(--mt-space-2)' }}>
          <span className="mt-brand-mark" aria-hidden="true">M</span>
          <span className="mt-brand-name">{branding.display_name}</span>
        </Link>
        <LanguageSwitcher />
      </div>
      <div className="mt-auth-body">
        <div className="mt-card mt-auth-card">
          {done ? (
            <div className="mt-stack" style={{ textAlign: 'center' }}>
              <Icon name="mail" size={44} style={{ color: 'var(--mt-primary)', margin: '0 auto' }} />
              <h1>{t('auth.register_done_title')}</h1>
              <p className="mt-muted">{t('auth.register_done_sub')}</p>
              <Button variant="primary" onClick={() => navigate('/login')}>
                {t('auth.login_submit')}
              </Button>
            </div>
          ) : (
            <form onSubmit={submit} noValidate>
              <h1>{t('auth.register_title')}</h1>
              <p className="mt-auth-sub">{t('auth.register_sub')}</p>
              {formError ? (
                <p className="mt-banner mt-banner-danger" role="alert" style={{ marginBottom: 'var(--mt-space-4)' }}>
                  <Icon name="alertCircle" size={18} />
                  {formError}
                </p>
              ) : null}
              <div className="mt-stack">
                <TextInput
                  label={t('auth.field_full_name')}
                  autoComplete="name"
                  value={form.full_name}
                  onChange={set('full_name')}
                  error={errors.full_name}
                  icon="user"
                  required
                />
                <TextInput
                  label={t('auth.field_email')}
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={set('email')}
                  error={errors.email}
                  icon="mail"
                  required
                />
                <div>
                  <TextInput
                    label={t('auth.field_password')}
                    type="password"
                    autoComplete="new-password"
                    value={form.password}
                    onChange={set('password')}
                    error={errors.password}
                    helper={t('auth.password_helper', { count: 12 })}
                    icon="lock"
                    required
                  />
                  {form.password ? (
                    <div className="mt-stack-sm" style={{ marginTop: 'var(--mt-space-2)' }}>
                      <div
                        className="mt-strength"
                        role="progressbar"
                        aria-valuenow={strength}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={t('auth.strength_label')}
                      >
                        <div
                          className="mt-strength-fill"
                          style={{
                            width: `${strength}%`,
                            background: strength >= 55 ? 'var(--mt-success-fg)' : 'var(--mt-warning-fg)',
                          }}
                        />
                      </div>
                      <span className="mt-xs mt-muted">{strengthLabel}</span>
                    </div>
                  ) : null}
                </div>
                <TextInput
                  label={t('auth.field_company')}
                  autoComplete="organization"
                  value={form.company_name}
                  onChange={set('company_name')}
                  error={errors.company_name}
                  icon="building"
                  helper={t('auth.company_helper')}
                  required
                />
                <Button variant="primary" type="submit" loading={loading} style={{ width: '100%' }}>
                  {t('auth.register_submit')}
                </Button>
              </div>
              <p className="mt-auth-alt">
                {t('auth.has_account')} <Link to="/login">{t('auth.login_submit')}</Link>
              </p>
            </form>
          )}
        </div>
      </div>
      <div className="mt-auth-footer">{t('auth.footer_note')}</div>
    </div>
  );
}
