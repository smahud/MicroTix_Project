import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useBranding } from '../../branding';
import { Button } from '../../design-system/primitives/Button';
import { LanguageSwitcher } from '../../design-system/components/AppShell';
import { Icon } from '../../design-system/primitives/Icon';
import '../landing/landing.css';

/** Verifikasi email lewat tautan (email transaksional). */
export default function VerifyPage() {
  const t = useT();
  const api = useApi();
  const branding = useBranding();
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [state, setState] = useState<'idle' | 'ok' | 'error'>('idle');
  const [loading, setLoading] = useState(false);

  const verify = async () => {
    if (!token) return;
    setLoading(true);
    try {
      await api.verifyEmail(token);
      setState('ok');
    } catch {
      setState('error');
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
          <h1>{t('auth.verify_title')}</h1>
          <p className="mt-auth-sub">{t('auth.verify_sub')}</p>
          {state === 'ok' ? (
            <div className="mt-stack">
              <p className="mt-banner mt-banner-success">
                <Icon name="checkCircle" size={18} /> {t('auth.verify_ok')}
              </p>
              <Link to="/login" className="mt-btn mt-btn-primary">
                {t('auth.login_submit')}
              </Link>
            </div>
          ) : state === 'error' ? (
            <p className="mt-banner mt-banner-danger">
              <Icon name="alertCircle" size={18} /> {t('auth.verify_error')}
            </p>
          ) : (
            <div className="mt-stack">
              <Button variant="primary" onClick={verify} loading={loading} disabled={!token}>
                {t('auth.verify_submit')}
              </Button>
              {!token ? <p className="mt-small mt-muted">{t('auth.verify_missing_token')}</p> : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
