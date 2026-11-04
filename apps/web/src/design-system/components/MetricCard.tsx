import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../primitives/Icon';
import { Skeleton } from '../primitives/Misc';
import { useT } from '../../i18n/useT';

/**
 * MetricCard — kartu navigable keyboard, berlabel periode + satuan;
 * skeleton tanpa nol palsu; agregat tertunda → waktu pembaruan + tautan (UI_UX.md §4).
 */
export function MetricCard({
  label,
  value,
  unit,
  hint,
  to,
  loading,
  pendingAggNote,
  tone = 'default',
}: {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  hint?: ReactNode;
  to?: string;
  loading?: boolean;
  /** Catatan agregat tertunda (bukan angka palsu). */
  pendingAggNote?: ReactNode;
  tone?: 'default' | 'warning' | 'danger' | 'success';
}) {
  const t = useT();
  const inner = (
    <>
      <span className="mt-metric-label">{label}</span>
      <span className="mt-metric-value">
        {loading ? <Skeleton w={96} h={30} /> : value}
        {unit && !loading ? <span className="mt-metric-unit">{unit}</span> : null}
      </span>
      {pendingAggNote ? (
        <span className="mt-xs mt-muted" style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
          <Icon name="clock" size={12} />
          {pendingAggNote}
        </span>
      ) : hint ? (
        <span className="mt-metric-hint">{hint}</span>
      ) : null}
    </>
  );
  const cls = `mt-card mt-metric${tone === 'warning' ? ' mt-metric-warning' : tone === 'danger' ? ' mt-metric-danger' : tone === 'success' ? ' mt-metric-success' : ''}`;
  if (to && !loading) {
    return (
      <Link to={to} className={cls}>
        {inner}
      </Link>
    );
  }
  return (
    <div className={cls} aria-label={typeof label === 'string' ? label : undefined}>
      {inner}
      {loading ? <span className="mt-visually-hidden">{t('common.loading')}</span> : null}
    </div>
  );
}
