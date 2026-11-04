import type { ReactNode } from 'react';
import { useIntl } from 'react-intl';
import { useT, useEnumLabel } from '../../i18n/useT';
import { formatRelative } from '../../lib/format';
import { freshness as calcFreshness, freshnessTone } from '../../lib/statuses';
import { Icon } from '../primitives/Icon';

/**
 * StatusBadge — teks + warna + ikon (UI_UX.md §2);
 * warna bukan satu-satunya penanda status.
 */
export function StatusBadge({
  tone,
  label,
  icon,
  title,
}: {
  tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info';
  label: ReactNode;
  icon?: string;
  title?: string;
}) {
  return (
    <span className={`mt-badge mt-badge-${tone}`} title={title}>
      <Icon name={icon ?? toneIcon(tone)} size={12} />
      {label}
    </span>
  );
}

function toneIcon(tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info'): string {
  switch (tone) {
    case 'success':
      return 'checkCircle';
    case 'warning':
      return 'alertTriangle';
    case 'danger':
      return 'alertCircle';
    case 'info':
      return 'clock';
    default:
      return 'hash';
  }
}

/** Label enum terlokalkan: kunci `enums.<group>.<value>` — kode tidak diterjemahkan. */
export function EnumBadge({
  group,
  value,
  tone,
}: {
  group: string;
  value: string | null | undefined;
  tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info';
}) {
  const enumLabel = useEnumLabel();
  return <StatusBadge tone={value == null ? 'neutral' : tone} label={enumLabel(group, value)} />;
}

/**
 * FreshnessLabel — "Data terakhir diperbarui 12 menit lalu" (UI_UX.md §12).
 * Data tidak tersedia ≠ offline; sumber pengamatan ditampilkan.
 */
export function FreshnessLabel({
  observedAt,
  source,
  staleMinutes = 15,
}: {
  observedAt: string | null;
  source?: string;
  staleMinutes?: number;
}) {
  const t = useT();
  const intl = useIntl();
  const f = calcFreshness(observedAt, staleMinutes);
  const tone = freshnessTone(f);
  const text =
    f === 'unknown'
      ? t('freshness.unknown')
      : t('freshness.updated', {
          rel: formatRelative(observedAt!, intl.locale.toLowerCase().startsWith('en') ? 'en' : 'id'),
        });
  return (
    <span className="mt-small" style={{ color: 'var(--mt-text-secondary)', display: 'inline-flex', gap: 6, alignItems: 'center' }}>
      <StatusBadge tone={tone} label={text} icon={f === 'stale' ? 'clock' : undefined} />
      {source ? <span className="mt-xs mt-muted">· {source}</span> : null}
    </span>
  );
}
