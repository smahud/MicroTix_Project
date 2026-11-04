import type { ReactNode } from 'react';
import { Breadcrumb } from '../primitives/Misc';
import type { Crumb } from '../primitives/Misc';

/**
 * PageHeader — judul, konteks, dan aksi utama.
 * Tombol primer maksimum satu per langkah (UI_UX.md §2).
 */
export function PageHeader({
  title,
  description,
  actions,
  breadcrumbs,
  meta,
}: {
  title: ReactNode;
  description?: ReactNode;
  /** Slot aksi: satu tombol primer + sekunder. */
  actions?: ReactNode;
  breadcrumbs?: Crumb[];
  meta?: ReactNode;
}) {
  return (
    <header className="mt-pageheader">
      {breadcrumbs?.length ? <Breadcrumb items={breadcrumbs} /> : null}
      <div className="mt-pageheader-main">
        <div className="mt-pageheader-text">
          <h1>{title}</h1>
          {description ? <p className="mt-muted mt-pageheader-desc">{description}</p> : null}
          {meta ? <div className="mt-pageheader-meta">{meta}</div> : null}
        </div>
        {actions ? <div className="mt-pageheader-actions">{actions}</div> : null}
      </div>
    </header>
  );
}

/**
 * FilterBar — pencarian dan filter dekat judul (UI_UX.md §13).
 * Filter dipertahankan saat kembali dari detail.
 */
export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="mt-filterbar">{children}</div>;
}
