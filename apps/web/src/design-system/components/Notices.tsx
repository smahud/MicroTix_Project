import type { ReactNode } from 'react';
import { Dialog } from '../primitives/Dialog';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';
import { useT } from '../../i18n/useT';

/**
 * PermissionNotice — aksi tanpa izin bukan tabel kosong (UI_UX.md §12: 403 ≠ kosong).
 */
export function PermissionNotice({
  what,
  who,
}: {
  what: ReactNode;
  who?: string;
}) {
  const t = useT();
  return (
    <div className="mt-banner mt-banner-warning" role="alert">
      <Icon name="lock" size={20} style={{ flexShrink: 0, marginTop: 2 }} />
      <div>
        <strong>{t('permission.title')}</strong>
        <p>{what}</p>
        <p className="mt-small">
          {who ? t('permission.contact_owner_with', { who }) : t('permission.contact_owner')}
        </p>
      </div>
    </div>
  );
}

/**
 * ConfirmAction — konfirmasi menyebut objek, jumlah, jenis perubahan, dampak;
 * CTA bervera; aksi destruktif terpisah (UI_UX.md §2–§3).
 * Konfirmasi destruktif spesifik: "Putuskan sesi layanan SVC-018?".
 */
export function ConfirmAction({
  open,
  onClose,
  onConfirm,
  title,
  intent,
  scopeLines,
  confirmLabel,
  confirmTone = 'primary',
  loading,
  requiresReauth,
  children,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: ReactNode;
  intent: ReactNode;
  scopeLines?: ReactNode[];
  confirmLabel: ReactNode;
  confirmTone?: 'primary' | 'danger';
  loading?: boolean;
  requiresReauth?: boolean;
  children?: ReactNode;
}) {
  const t = useT();
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            {t('common.cancel')}
          </Button>
          <Button variant={confirmTone} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="mt-stack-sm">
        <p>{intent}</p>
        {scopeLines?.length ? (
          <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {scopeLines.map((l, i) => (
              <li key={i} className="mt-small mt-muted">
                {l}
              </li>
            ))}
          </ul>
        ) : null}
        {requiresReauth ? (
          <p className="mt-banner mt-banner-info" style={{ marginBottom: 0 }}>
            <Icon name="shield" size={18} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>{t('auth.reauth_required_note')}</span>
          </p>
        ) : null}
        {children}
      </div>
    </Dialog>
  );
}
