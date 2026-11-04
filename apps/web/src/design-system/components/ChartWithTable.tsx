import { useMemo } from 'react';
import { useT, useActiveLocale } from '../../i18n/useT';
import { formatBitsPerSecond, formatDateTime } from '../../lib/format';
import { Segmented } from '../primitives/Misc';

/**
 * ChartWithTable — grafik dengan unit dan rentang jelas; gap tetap gap;
 * tabel alternatif selalu tersedia (UI_UX.md §4: chart punya alternatif tabel).
 */
export interface ChartPoint {
  t: string; // ISO
  v: number | null; // null = gap data (bukan nol)
}

export function ChartWithTable({
  data,
  unit,
  rangeLabel,
  range,
  onRangeChange,
  caption,
  loading,
}: {
  data: ChartPoint[];
  unit: 'bits' | 'bytes' | 'count';
  rangeLabel?: string;
  range?: string;
  onRangeChange?: (r: string) => void;
  caption: string;
  loading?: boolean;
}) {
  const t = useT();
  const locale = useActiveLocale();

  const { path, area, max, gaps } = useMemo(() => {
    const vals = data.filter((d) => d.v != null).map((d) => d.v as number);
    const maxV = vals.length ? Math.max(...vals) : 0;
    const W = 640;
    const H = 180;
    const P = 8;
    const n = data.length;
    let d = '';
    let a = '';
    let gapStart = true;
    data.forEach((p, i) => {
      const x = P + (i * (W - 2 * P)) / Math.max(1, n - 1);
      const y = p.v == null ? H - P : H - P - ((p.v / (maxV || 1)) * (H - 2 * P));
      if (p.v == null) {
        gapStart = true;
        return;
      }
      if (gapStart) {
        d += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
        a += `M ${x.toFixed(1)} ${H - P} L ${x.toFixed(1)} ${y.toFixed(1)}`;
        gapStart = false;
      } else {
        d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
        a += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
    });
    a += ` L ${(P + ((n - 1) * (W - 2 * P)) / Math.max(1, n - 1)).toFixed(1)} ${H - P} Z`;
    return { path: d, area: a, max: maxV, gaps: data.some((p) => p.v == null) };
  }, [data]);

  const fmt = (v: number | null) => {
    if (v == null) return t('common.unknown');
    if (unit === 'bits') return formatBitsPerSecond(v, locale);
    return String(v);
  };

  return (
    <figure className="mt-chart" style={{ margin: 0 }}>
      <div className="mt-row-between" style={{ marginBottom: 'var(--mt-space-2)' }}>
        <span className="mt-small mt-muted">
          {caption}
          {rangeLabel ? ` · ${rangeLabel}` : ''}
          {unit === 'bits' ? ` · ${t('chart.unit_bits')}` : ''}
        </span>
        {onRangeChange ? (
          <Segmented
            ariaLabel={t('chart.range')}
            value={range ?? '24h'}
            onChange={onRangeChange}
            options={[
              { value: '24h', label: t('chart.range_24h') },
              { value: '7d', label: t('chart.range_7d') },
            ]}
          />
        ) : null}
      </div>
      <div className="mt-chart-plot" style={{ position: 'relative' }}>
        {loading ? (
          <div className="mt-skeleton" style={{ height: 180, borderRadius: 'var(--mt-radius)' }} />
        ) : (
          <svg
            viewBox="0 0 640 180"
            style={{ width: '100%', height: 'auto', display: 'block' }}
            role="img"
            aria-label={`${caption}. ${t('chart.max_value', { value: fmt(max) })}${gaps ? ` ${t('chart.has_gaps')}` : ''}`}
          >
            <path d={area} fill="rgba(29,78,216,0.08)" />
            <path d={path} fill="none" stroke="var(--mt-primary)" strokeWidth={2} strokeLinecap="round" />
          </svg>
        )}
      </div>
      {gaps ? (
        <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
          {t('chart.gap_note')}
        </p>
      ) : null}
      <details className="mt-chart-table">
        <summary className="mt-small" style={{ cursor: 'pointer', marginTop: 'var(--mt-space-2)' }}>
          {t('chart.show_table')}
        </summary>
        <div className="mt-table-wrap" style={{ marginTop: 'var(--mt-space-2)' }}>
          <table className="mt-table">
            <caption className="mt-visually-hidden">{caption}</caption>
            <thead>
              <tr>
                <th scope="col">{t('chart.col_time')}</th>
                <th scope="col" className="mt-table-num">
                  {t('chart.col_value')}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.t}>
                  <td className="mt-small">{formatDateTime(p.t, locale)}</td>
                  <td className="mt-table-num mt-small">{fmt(p.v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
