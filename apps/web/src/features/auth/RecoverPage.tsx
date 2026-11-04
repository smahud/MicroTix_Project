import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useBranding } from '../../branding';
import { TextInput } from '../../design-system/primitives/Input';
import { Button } from '../../design-system/primitives/Button';
import { LanguageSwitcher } from '../../design-system/components/AppShell';
import { Icon } from '../../design-system/primitives/Icon';
import '../landing/landing.css';

/** Pemulihan password: pesan selalu sama agar tidak mengungkap akun (UI_UX.md §3). */
export default function RecoverPage() {
  const t = useT();
  const api = useApi();
  const branding = useBranding();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.requestPasswordReset(email);
    } finally {
      setSent(true);
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
          <h1>{t('auth.recover_title')}</h1>
          <p className="mt-auth-sub">{t('auth.recover_sub')}</p>
          {sent ? (
            <p className="mt-banner mt-banner-info">
              <Icon name="mail" size={18} /> {t('auth.recover_sent')}
            </p>
          ) : (
            <form onSubmit={submit} noValidate>
              <div className="mt-stack">
                <TextInput
                  label={t('auth.field_email')}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  icon="mail"
                  required
                />
                <Button variant="primary" type="submit" loading={loading} style={{ width: '100%' }}>
                  {t('auth.recover_submit')}
                </Button>
              </div>
            </form>
          )}
          <p className="mt-auth-alt">
            <Link to="/login">{t('common.back')}</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
