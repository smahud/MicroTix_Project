import type { ReactNode } from 'react';
import { Icon } from '../primitives/Icon';
import { Button } from '../primitives/Button';
import { useT } from '../../i18n/useT';
import type { ServiceRow } from '../../api/contracts';
import { isReleased } from '../../permissions/release-flags';
import { EnumBadge } from './StatusBadge';
import { connectionTone, isolationTone, jobDimensionTone, paymentTone } from '../../lib/statuses';
import { formatDateTime } from '../../lib/format';
import { useActiveLocale } from '../../i18n/useT';
import { Link } from 'react-router-dom';

/**
 * MobileServiceCard — tabel pelanggan pada mobile menjadi kartu
 * dengan EMPAT status terpisah (UI_UX.md §13: bayar/isolir/koneksi/job).
 */
export function MobileServiceCard({ service, tenantId }: { service: ServiceRow; tenantId: string }) {
  const t = useT();
  return (
    <article className="mt-svc-card">
      <div className="mt-svc-card-head">
        <div style={{ minWidth: 0 }}>
          <Link to={`/app/${tenantId}/customers/${service.id}`} className="mt-svc-card-name">
            {service.customer_name}
          </Link>
          <div className="mt-xs mt-muted mt-mono">{service.service_code}</div>
        </div>
        <span className="mt-xs mt-muted">{service.kind === 'hotspot' ? 'Hotspot' : 'PPPoE'}</span>
      </div>
      <dl className="mt-svc-card-grid">
        <div>
          <dt className="mt-xs mt-muted">{t('customers.col.username')}</dt>
          <dd className="mt-small mt-mono">{service.username ?? t('common.unknown')}</dd>
        </div>
        <div>
          <dt className="mt-xs mt-muted">{t('customers.col.router')}</dt>
          <dd className="mt-small">{service.router_display_name ?? t('common.not_set')}</dd>
        </div>
        <div>
          <dt className="mt-xs mt-muted">{t('customers.col.package')}</dt>
          <dd className="mt-small">{service.package_name ?? t('common.not_set')}</dd>
        </div>
      </dl>
      <div className="mt-svc-statuses">
        <StatusQuad service={service} />
      </div>
    </article>
  );
}

/** Empat dimensi status terpisah — jangan digabung (UI_UX.md §5).
 *  Kolom bayar/isolir (R2) tersembunyi pada R1 sesuai fase. */
export function StatusQuad({ service }: { service: ServiceRow }) {
  const t = useT();
  const showBilling = isReleased('billing');
  return (
    <>
      {showBilling ? (
        <div className="mt-status-cell">
          <span className="mt-xs mt-muted">{t('customers.status.payment')}</span>
          <EnumBadge group="payment" value={service.payment} tone={paymentTone(service.payment)} />
        </div>
      ) : null}
      {showBilling ? (
        <div className="mt-status-cell">
          <span className="mt-xs mt-muted">{t('customers.status.isolation')}</span>
          <EnumBadge group="isolation" value={service.isolation} tone={isolationTone(service.isolation)} />
        </div>
      ) : null}
      <div className="mt-status-cell">
        <span className="mt-xs mt-muted">{t('customers.status.connection')}</span>
        <EnumBadge group="connection" value={service.connection} tone={connectionTone(service.connection)} />
      </div>
      <div className="mt-status-cell">
        <span className="mt-xs mt-muted">{t('customers.status.job')}</span>
        <EnumBadge group="job_dimension" value={service.job} tone={jobDimensionTone(service.job)} />
      </div>
    </>
  );
}

/**
 * BulkActionBar — "2 layanan dipilih di halaman ini";
 * "pilih seluruh hasil" aksi kedua menyebut jumlah dan filter (UI_UX.md §5).
 */
export function BulkActionBar({
  selectedCount,
  totalCount,
  filterDescription,
  onSelectAllResults,
  onClear,
  children,
}: {
  selectedCount: number;
  totalCount: number;
  filterDescription?: ReactNode;
  onSelectAllResults?: () => void;
  onClear: () => void;
  children?: ReactNode;
}) {
  const t = useT();
  if (selectedCount === 0) return null;
  return (
    <div className="mt-bulkbar" role="toolbar" aria-label={t('bulk.toolbar_label')}>
      <Icon name="checkCircle" size={18} style={{ color: 'var(--mt-primary)', flexShrink: 0 }} />
      <span className="mt-small" style={{ fontWeight: 500 }}>
        {t('bulk.selected_on_page', { count: selectedCount })}
      </span>
      {onSelectAllResults ? (
        <Button variant="ghost" size="sm" onClick={onSelectAllResults}>
          {t('bulk.select_all_results', { count: totalCount })}
          {filterDescription ? <span className="mt-xs mt-muted"> · {filterDescription}</span> : null}
        </Button>
      ) : null}
      <span style={{ flex: 1 }} />
      {children}
      <Button variant="ghost" size="sm" onClick={onClear}>
        {t('bulk.clear_selection')}
      </Button>
    </div>
  );
}

/**
 * AuditTimeline — riwayat audit redacted (entri aktor, waktu, aksi, target).
 */
export interface TimelineEntry {
  id: string;
  at: string;
  actor: string;
  action: string;
  target?: string | null;
}

export function AuditTimeline({ entries }: { entries: TimelineEntry[] }) {
  const t = useT();
  const locale = useActiveLocale();
  if (entries.length === 0) {
    return <p className="mt-muted mt-small">{t('audit.empty')}</p>;
  }
  return (
    <ol className="mt-timeline">
      {entries.map((e) => (
        <li key={e.id} className="mt-timeline-item">
          <span className="mt-timeline-dot" aria-hidden="true" />
          <div className="mt-timeline-body">
            <div className="mt-timeline-head">
              <strong className="mt-small">{e.actor}</strong>
              <time className="mt-xs mt-muted" dateTime={e.at}>
                {formatDateTime(e.at, locale)}
              </time>
            </div>
            <div className="mt-small">
              <span className="mt-mono mt-xs">{e.action}</span>
              {e.target ? <span className="mt-muted"> · {e.target}</span> : null}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
