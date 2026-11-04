import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useT } from '../../i18n/useT';

/* ---------- Tabs ---------- */
export interface TabItem {
  id: string;
  label: ReactNode;
  count?: number | null;
}

export function Tabs({
  items,
  active,
  onChange,
  ariaLabel,
}: {
  items: TabItem[];
  active: string;
  onChange: (id: string) => void;
  ariaLabel: string;
}) {
  return (
    <div className="mt-tabs" role="tablist" aria-label={ariaLabel}>
      {items.map((t) => (
        <button
          key={t.id}
          role="tab"
          type="button"
          aria-selected={active === t.id}
          className="mt-tab"
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.count != null ? <span className="mt-tab-count">{t.count}</span> : null}
        </button>
      ))}
    </div>
  );
}

/* ---------- Segmented control ---------- */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: Array<{ value: T; label: ReactNode }>;
  value: T;
  onChange: (v: T) => void;
  ariaLabel: string;
}) {
  return (
    <div className="mt-segmented" role="group" aria-label={ariaLabel}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          className="mt-segmented-item"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ---------- Tooltip (keyboard accessible) ---------- */
export function Tooltip({ label, children }: { label: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span
      className="mt-tooltip-wrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined} tabIndex={0} style={{ display: 'inline-flex' }}>
        {children}
      </span>
      {open ? (
        <span className="mt-tooltip" role="tooltip" id={id}>
          {label}
        </span>
      ) : null}
    </span>
  );
}

/* ---------- Breadcrumb ---------- */
export interface Crumb {
  label: ReactNode;
  to?: string;
}

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mt-small mt-muted">
      <ol style={{ display: 'flex', gap: 6, flexWrap: 'wrap', listStyle: 'none', margin: 0, padding: 0 }}>
        {items.map((c, i) => (
          <li key={i} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {i > 0 ? <span aria-hidden="true">/</span> : null}
            {c.to ? <Link to={c.to}>{c.label}</Link> : <span aria-current="page">{c.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/* ---------- Pagination (server, kursor) ---------- */
export function CursorPagination({
  hasNext,
  hasPrev,
  onNext,
  onPrev,
  loading,
  rangeLabel,
}: {
  hasNext: boolean;
  hasPrev: boolean;
  onNext: () => void;
  onPrev: () => void;
  loading?: boolean;
  rangeLabel?: ReactNode;
}) {
  const t = useT();
  return (
    <div className="mt-pagination">
      <span className="mt-small mt-muted">{rangeLabel}</span>
      <span style={{ display: 'flex', gap: 'var(--mt-space-2)' }}>
        <button type="button" className="mt-btn mt-btn-secondary mt-btn-sm" onClick={onPrev} disabled={!hasPrev || loading}>
          ‹ {t('common.prev_page')}
        </button>
        <button type="button" className="mt-btn mt-btn-secondary mt-btn-sm" onClick={onNext} disabled={!hasNext || loading}>
          {t('common.next_page')} ›
        </button>
      </span>
    </div>
  );
}

/* ---------- Skeleton ---------- */
export function Skeleton({ w, h, style }: { w?: number | string; h?: number; style?: React.CSSProperties }) {
  return <span className="mt-skeleton" style={{ display: 'block', width: w ?? '100%', height: h ?? 14, ...style }} />;
}

/* ---------- EmptyState — komponen wajib ---------- */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div style={{ textAlign: 'center', padding: 'var(--mt-space-8) var(--mt-space-4)' }}>
      {icon ? <div style={{ color: 'var(--mt-text-secondary)', marginBottom: 'var(--mt-space-3)' }}>{icon}</div> : null}
      <h3 style={{ marginBottom: 'var(--mt-space-2)' }}>{title}</h3>
      {description ? <p className="mt-muted" style={{ maxWidth: 420, margin: '0 auto var(--mt-space-4)' }}>{description}</p> : null}
      {action}
    </div>
  );
}

/* ---------- Progress bar ---------- */
export function ProgressBar({
  value,
  max = 100,
  tone = 'info',
  label,
}: {
  value: number;
  max?: number;
  tone?: 'info' | 'success' | 'warning';
  label?: ReactNode;
}) {
  const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100));
  return (
    <div
      className="mt-progress-track"
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={typeof label === 'string' ? label : undefined}
    >
      <div className={`mt-progress-fill${tone === 'success' ? ' mt-progress-fill-success' : tone === 'warning' ? ' mt-progress-fill-warning' : ''}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
