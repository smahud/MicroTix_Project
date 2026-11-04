import { useT, useEnumLabel, useActiveLocale } from '../../i18n/useT';
import { jobStateTone } from '../../lib/statuses';
import { StatusBadge } from './StatusBadge';
import { ProgressBar } from '../primitives/Misc';
import { Icon } from '../primitives/Icon';
import { formatDateTime, formatDuration } from '../../lib/format';
import type { JobRecord } from '../../api/contracts';

/**
 * JobProgress — status pekerjaan dengan tahap dan item selesai,
 * tanpa ETA bila tak terukur (UI_UX.md §10/U16).
 * `uncertain` dan `recovery_required` tetap terlihat setelah refresh.
 */
export function JobProgress({ job, compact = false }: { job: JobRecord; compact?: boolean }) {
  const t = useT();
  const enumLabel = useEnumLabel();
  const locale = useActiveLocale();
  const tone = jobStateTone(job.state);
  const stateLabel = enumLabel('job_state', job.state);
  const isTerminal = ['succeeded', 'failed', 'cancelled'].includes(job.state);
  const showBar = !compact && job.items_total != null && !isTerminal;

  return (
    <div className="mt-stack-sm" style={{ minWidth: compact ? 120 : 240 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <StatusBadge
          tone={tone}
          label={stateLabel}
          icon={
            job.state === 'succeeded'
              ? 'checkCircle'
              : job.state === 'failed'
                ? 'alertCircle'
                : job.state === 'uncertain' || job.state === 'recovery_required'
                  ? 'alertTriangle'
                  : 'clock'
          }
        />
        {job.phase_label_code && !isTerminal ? (
          <span className="mt-xs mt-muted">· {enumLabel('job_phase', job.phase_label_code)}</span>
        ) : null}
      </div>
      {showBar && job.items_total ? (
        <div className="mt-stack-sm">
          <ProgressBar
            value={job.items_done ?? 0}
            max={job.items_total}
            label={t('job.items_progress', { done: job.items_done ?? 0, total: job.items_total })}
          />
          <span className="mt-xs mt-muted">
            {t('job.items_progress', { done: job.items_done ?? 0, total: job.items_total })}
          </span>
        </div>
      ) : null}
      {!compact ? (
        <div className="mt-xs mt-muted" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
            <Icon name="clock" size={14} />
            {formatDateTime(job.updated_at, locale)}
            <span aria-hidden="true">·</span>
            {formatDuration((Date.now() - new Date(job.created_at).getTime()) / 1000, locale)}
          </span>
          {job.error_code ? (
            <span style={{ color: 'var(--mt-danger-fg)' }}>
              {t('job.error_with_code', { code: job.error_code, requestId: job.request_id ?? '—' })}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
