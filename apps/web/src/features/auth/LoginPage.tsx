import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import { useSession } from '../../state/session';
import { useBranding } from '../../branding';
import { TextInput } from '../../design-system/primitives/Input';
import { Button } from '../../design-system/primitives/Button';
import { LanguageSwitcher } from '../../design-system/components/AppShell';
import { Icon } from '../../design-system/primitives/Icon';
import '../landing/landing.css';

interface FieldErrs {
  [k: string]: string | undefined;
}

/** Login: email+password → kode TOTP bila MFA aktif (UI_UX.md §3). */
export default function LoginPage() {
  const t = useT();
  const { login, loginTotp } = useSession();
  const branding = useBranding();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totp, setTotp] = useState('');
  const [stage, setStage] = useState<'credentials' | 'totp'>('credentials');
  const [errors, setErrors] = useState<FieldErrs>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submitCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setFormError(null);
    const errs: FieldErrs = {};
    if (!email.trim()) errs.email = t('validation.required');
    if (!password) errs.password = t('validation.required');
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setLoading(true);
    try {
      const res = await login(email, password);
      if (res.requires_totp) {
        setStage('totp');
      } else {
        // Login non-MFA selesai — sesi aktif; lanjut ke aplikasi (paritas
        // jalur TOTP yang menavigasi setelah verifikasi).
        navigate('/app');
      }
    } catch (err) {
      // Pesan gagal login selalu sama — tidak mengungkap akun (UI_UX.md §3)
      setFormError(t('auth.login_mismatch'));
    } finally {
      setLoading(false);
    }
  };

  const submitTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setFormError(null);
    if (!/^\d{6}$/.test(totp)) {
      setErrors({ totp: t('validation.totp_digits') });
      return;
    }
    setLoading(true);
    try {
      await loginTotp(totp);
      navigate('/app');
    } catch {
      setFormError(t('auth.totp_invalid'));
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
          {stage === 'credentials' ? (
            <form onSubmit={submitCredentials} noValidate>
              <h1>{t('auth.login_title')}</h1>
              <p className="mt-auth-sub">{t('auth.login_sub')}</p>
              {formError ? (
                <p className="mt-banner mt-banner-danger" role="alert" style={{ marginBottom: 'var(--mt-space-4)' }}>
                  <Icon name="alertCircle" size={18} />
                  {formError}
                </p>
              ) : null}
              <div className="mt-stack">
                <TextInput
                  label={t('auth.field_email')}
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  error={errors.email}
                  icon="mail"
                  required
                />
                <TextInput
                  label={t('auth.field_password')}
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  error={errors.password}
                  icon="lock"
                  required
                />
                <Button variant="primary" type="submit" loading={loading} style={{ width: '100%' }}>
                  {t('auth.login_submit')}
                </Button>
              </div>
              <p className="mt-auth-alt">
                <Link to="/recover">{t('auth.forgot_password')}</Link>
              </p>
              <p className="mt-auth-alt">
                {t('auth.no_account')} <Link to="/register">{t('auth.register_link')}</Link>
              </p>
            </form>
          ) : (
            <form onSubmit={submitTotp} noValidate>
              <h1>{t('auth.totp_title')}</h1>
              <p className="mt-auth-sub">{t('auth.totp_sub')}</p>
              {formError ? (
                <p className="mt-banner mt-banner-danger" role="alert" style={{ marginBottom: 'var(--mt-space-4)' }}>
                  <Icon name="alertCircle" size={18} />
                  {formError}
                </p>
              ) : null}
              <div className="mt-stack">
                <TextInput
                  label={t('auth.field_totp')}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={totp}
                  onChange={(e) => setTotp(e.target.value.replace(/\D/g, ''))}
                  error={errors.totp}
                  placeholder="••••••"
                  required
                />
                <Button variant="primary" type="submit" loading={loading} style={{ width: '100%' }}>
                  {t('auth.totp_submit')}
                </Button>
                <Button variant="ghost" type="button" onClick={() => setStage('credentials')}>
                  {t('common.back')}
                </Button>
              </div>
              <p className="mt-auth-alt mt-small mt-muted">{t('auth.totp_recovery_hint')}</p>
            </form>
          )}
        </div>
      </div>
      <div className="mt-auth-footer">{t('auth.footer_note')}</div>
    </div>
  );
}
