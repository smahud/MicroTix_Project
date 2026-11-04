import { useNavigate } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import { useSession } from '../../state/session';
import { PageHeader } from '../../design-system/components/PageHeader';
import { Icon } from '../../design-system/primitives/Icon';
import { Button } from '../../design-system/primitives/Button';
import { useI18n } from '../../i18n';
import { LANGUAGE_NAMES, LOCALES } from '../../i18n';

/** U18 Tim — daftar anggota + peran + undang (R1: tampilan kontrak tim). */
export default function TeamPanel({ tenantId }: { tenantId: string }) {
  const t = useT();
  const { ctx, activeTenant } = useSession();
  const { locale, setLocale } = useI18n();
  const navigate = useNavigate();
  void navigate;

  const members = [
    { name: ctx?.user?.full_name ?? '', email: ctx?.user?.email ?? '', role: activeTenant?.role ?? 'owner', mfa: ctx?.user?.mfa_enabled ?? false },
  ];

  return (
    <>
      <PageHeader
        title={t('settings.team_title')}
        description={t('settings.team_desc', { tenant: activeTenant?.display_name ?? '' })}
      />
      <div className="mt-stack">
        <div className="mt-table-wrap">
          <table className="mt-table">
            <thead>
              <tr>
                <th scope="col">{t('settings.team_col_name')}</th>
                <th scope="col">{t('settings.team_col_role')}</th>
                <th scope="col">{t('settings.team_col_mfa')}</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.email}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{m.name}</div>
                    <div className="mt-xs mt-muted">{m.email}</div>
                  </td>
                  <td>{t(`role.${m.role}` as never, undefined as never)}</td>
                  <td>
                    {m.mfa ? (
                      <span className="mt-badge mt-badge-success">
                        <Icon name="checkCircle" size={12} /> {t('settings.mfa_on')}
                      </span>
                    ) : (
                      <span className="mt-badge mt-badge-warning">
                        <Icon name="alertTriangle" size={12} /> {t('settings.mfa_off')}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Bahasa default tenant (UI_UX.md §15) */}
        <div className="mt-card mt-card-pad mt-stack-sm">
          <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('settings.tenant_language_title')}</h2>
          <p className="mt-small mt-muted">{t('settings.tenant_language_desc')}</p>
          <div className="mt-row">
            {LOCALES.map((l) => (
              <Button
                key={l}
                variant={locale === l ? 'primary' : 'secondary'}
                size="sm"
                aria-pressed={locale === l}
                onClick={() => setLocale(l)}
              >
                {LANGUAGE_NAMES[l]}
              </Button>
            ))}
          </div>
        </div>

        {/* Undang tim via undangan email (workflow API belum tersedia) */}
        <div className="mt-card mt-card-pad mt-stack-sm">
          <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('settings.invite_title')}</h2>
          <p className="mt-small mt-muted">{t('settings.invite_desc')}</p>
          <Button variant="primary" icon="plus" disabled disabledReason={t('settings.invite_blocked_note')}>
            {t('settings.invite_cta')}
          </Button>
        </div>
      </div>
      <span className="mt-visually-hidden">{tenantId}</span>
    </>
  );
}
