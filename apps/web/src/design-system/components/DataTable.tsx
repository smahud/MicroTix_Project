import type { ReactNode } from 'react';
import { useT } from '../../i18n/useT';
import { Icon } from '../primitives/Icon';
import { EmptyState, Skeleton } from '../primitives/Misc';

/**
 * DataTable — sticky header, selection via checkbox (hanya memilih),
 * state loading (skeleton tanpa nol palsu), empty, error, dan aksi baris.
 * Detail luas pada halaman, bukan modal bertumpuk (UI_UX.md §2).
 */
export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  width?: number | string;
  align?: 'left' | 'right';
  hideOnMobile?: boolean;
  /** Kolom muncul hanya bila true (mis. kolom R2 disembunyikan pada R1). */
  visible?: boolean;
}

interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: ReactNode;
  emptyTitle?: string;
  emptyDescription?: ReactNode;
  emptyAction?: ReactNode;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (id: string, checked: boolean) => void;
  onToggleSelectAll?: (checked: boolean) => void;
  allSelected?: boolean;
  someSelected?: boolean;
  /** Konten mobile menggantikan tabel (MobileServiceCard). */
  mobileRender?: (row: T) => ReactNode;
  caption?: string;
}

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  loading,
  error,
  emptyTitle,
  emptyDescription,
  emptyAction,
  onRowClick,
  selectable,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  allSelected,
  someSelected,
  mobileRender,
  caption,
}: DataTableProps<T>) {
  const t = useT();
  const visibleColumns = columns.filter((c) => c.visible !== false);

  if (loading) {
    return (
      <div className="mt-card" style={{ padding: 'var(--mt-space-4)' }}>
        <div className="mt-stack">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ display: 'flex', gap: 'var(--mt-space-3)', alignItems: 'center' }}>
              <Skeleton w={20} h={20} />
              <Skeleton w={`${25 + ((i * 13) % 50)}%`} h={16} />
              <Skeleton w={90} h={16} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-card">
        <EmptyState
          icon={<Icon name="alertCircle" size={40} />}
          title={t('table.error_title')}
          description={error}
        />
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="mt-card">
        <EmptyState
          icon={<Icon name="search" size={40} />}
          title={emptyTitle ?? t('table.empty_title')}
          description={emptyDescription}
          action={emptyAction}
        />
      </div>
    );
  }

  const table = (
    <div className="mt-table-wrap">
      <table className="mt-table">
        {caption ? <caption className="mt-visually-hidden">{caption}</caption> : null}
        <thead>
          <tr>
            {selectable ? (
              <th scope="col" style={{ width: 44 }}>
                <input
                  type="checkbox"
                  checked={allSelected ?? false}
                  ref={(el) => {
                    if (el) el.indeterminate = (someSelected ?? false) && !allSelected;
                  }}
                  onChange={(e) => onToggleSelectAll?.(e.target.checked)}
                  aria-label={t('table.select_all')}
                />
              </th>
            ) : null}
            {visibleColumns.map((c) => (
              <th
                key={c.key}
                scope="col"
                style={{ width: c.width, textAlign: c.align === 'right' ? 'right' : 'left' }}
                className={c.hideOnMobile ? 'mt-col-desktop' : undefined}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const id = rowKey(row);
            const selected = selectedIds?.has(id) ?? false;
            return (
              <tr
                key={id}
                className={selected ? 'mt-row-selected' : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                style={onRowClick ? { cursor: 'pointer' } : undefined}
              >
                {selectable ? (
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={(e) => onToggleSelect?.(id, e.target.checked)}
                      aria-label={t('table.select_row')}
                    />
                  </td>
                ) : null}
                {visibleColumns.map((c) => (
                  <td
                    key={c.key}
                    className={`${c.align === 'right' ? 'mt-table-num' : ''} ${c.hideOnMobile ? 'mt-col-desktop' : ''}`}
                  >
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  if (mobileRender) {
    return (
      <>
        <div className="mt-only-desktop">{table}</div>
        <div className="mt-only-mobile mt-stack">
          {rows.map((row) => (
            <div key={rowKey(row)} className="mt-card mt-card-pad">
              {mobileRender(row)}
            </div>
          ))}
        </div>
      </>
    );
  }
  return table;
}
