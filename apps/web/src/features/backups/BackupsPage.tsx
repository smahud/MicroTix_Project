import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useT, useActiveLocale } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { PermissionNotice } from '../../design-system/components/Notices';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { ConfirmAction } from '../../design-system/components/Notices';
import { formatBytes, formatDateTime } from '../../lib/format';
import type { BackupArtifact } from '../../api/contracts';

/**
 * U12 — Backup (UI_UX.md §10): jadwal, histori, retensi 100 rutin +
 * 10 manual + 10 pre-change terpisah, unduhan berizin, kunci pemulihan.
 */
export default function BackupsPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const locale = useActiveLocale();
  const { can } = useSession();
  const { toast } = useToast();
  const [runOpen, setRunOpen] = useState(false);
  const [running, setRunning] = useState(false);

  const schedulesQ = useQuery({ queryKey: ['backup-schedules', tenantId], queryFn: () => api.listBackupSchedules(tenantId) });
  const backupsQ = useQuery({
    queryKey: ['backups', tenantId],
    queryFn: () => api.listBackupArtifacts(tenantId, null),
    refetchInterval: 30_000,
  });

  const byCategory = useMemo(
    () => {
      const artifacts = backupsQ.data ?? [];
      return {
        routine: artifacts.filter((a) => a.category === 'routine'),
        manual: artifacts.filter((a) => a.category === 'manual'),
        pre_change: artifacts.filter((a) => a.category === 'pre_change'),
      };
    },
    [backupsQ.data],
  );

  const columns = useMemo<Column<BackupArtifact>[]>(
    () => [
      {
        key: 'gen',
        header: t('backups.col_generation'),
        render: (a) => <span className="mt-mono">#{a.generation}</span>,
      },
      {
        key: 'router',
        header: t('backups.col_router'),
        render: (a) => a.router_id,
        hideOnMobile: true,
      },
      {
        key: 'created',
        header: t('backups.col_created'),
        render: (a) => formatDateTime(a.created_at, locale),
      },
      {
        key: 'category',
        header: t('backups.col_category'),
        render: (a) => <EnumBadge group="backup_category" value={a.category} tone={a.category === 'routine' ? 'neutral' : 'info'} />,
      },
      {
        key: 'size',
        header: t('backups.col_size'),
        align: 'right',
        render: (a) => formatBytes(a.size_bytes, locale),
      },
      {
        key: 'transfer',
        header: t('backups.col_transfer'),
        render: (a) => (
          <EnumBadge
            group="backup_state"
            value={a.transfer_state}
            tone={a.transfer_state === 'committed' ? 'success' : a.transfer_state === 'failed' ? 'danger' : 'info'}
          />
        ),
      },
      {
        key: 'encrypted',
        header: t('backups.col_encrypted'),
        render: (a) => (a.encrypted ? <Icon name="lock" size={16} style={{ color: 'var(--mt-success-fg)' }} /> : <span className="mt-xs mt-muted">{t('common.no')}</span>),
        hideOnMobile: true,
      },
      {
        key: 'actions',
        header: '',
        render: (a) =>
          a.transfer_state === 'committed' && can('backups.download') ? (
            <Button
              variant="ghost"
              size="sm"
              icon="download"
              onClick={() => toast(t('backups.download_reauth_note'), 'info')}
            >
              {t('backups.download_cta')}
            </Button>
          ) : null,
      },
    ],
    [t, locale, can, toast],
  );

  if (!can('backups.run')) {
    return (
      <AppShell tenantId={tenantId} title={t('nav.backups')}>
        <PermissionNotice what={t('permission.backups_run')} />
      </AppShell>
    );
  }

  const runBackup = async () => {
    const routerId = schedulesQ.data?.[0]?.router_id;
    if (!routerId) return;
    setRunning(true);
    try {
      const res = await api.runBackupNow(tenantId, routerId);
      setRunOpen(false);
      toast(t('backups.run_submitted'), 'success');
      void res;
      await backupsQ.refetch();
    } finally {
      setRunning(false);
    }
  };

  return (
    <AppShell tenantId={tenantId} title={t('nav.backups')}>
      <PageHeader
        title={t('backups.title')}
        description={t('backups.desc')}
        actions={
          <Button variant="primary" icon="plus" onClick={() => setRunOpen(true)}>
            {t('backups.run_now')}
          </Button>
        }
      />

      <div className="mt-stack">
        {/* Jadwal */}
        <section className="mt-section">
          <h2 className="mt-section-title">{t('backups.schedule_title')}</h2>
          <div className="mt-card mt-card-pad mt-stack-sm">
            {schedulesQ.isLoading ? (
              <p className="mt-muted">{t('common.loading')}</p>
            ) : (schedulesQ.data ?? []).length === 0 ? (
              <p className="mt-muted mt-small">{t('backups.schedule_empty')}</p>
            ) : (
              (schedulesQ.data ?? []).map((s) => (
                <div key={s.router_id} className="mt-row-between" style={{ borderBottom: '1px solid var(--mt-neutral-border)', paddingBottom: 'var(--mt-space-2)' }}>
                  <span className="mt-small">
                    <Icon name="calendar" size={16} style={{ verticalAlign: -3, marginRight: 6 }} />
                    {s.router_id} · {s.frequency === 'daily' ? t('backups.freq_daily') : t('backups.freq_weekly')} {s.time_local} {s.timezone}
                  </span>
                  <span className="mt-xs mt-muted">
                    {s.artifact_type === 'binary' ? t('backups.type_binary') : t('backups.type_export')}
                    {s.notification_enabled ? ` · ${t('backups.notif_on')}` : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Retensi */}
        <section className="mt-section">
          <h2 className="mt-section-title">{t('backups.retention_title')}</h2>
          <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <div className="mt-card mt-card-pad mt-stack-sm">
              <span className="mt-xs mt-muted">{t('backups.retention_routine')}</span>
              <strong style={{ fontSize: 'var(--mt-text-lg)' }}>
                {byCategory.routine.length} / 100
              </strong>
            </div>
            <div className="mt-card mt-card-pad mt-stack-sm">
              <span className="mt-xs mt-muted">{t('backups.retention_manual')}</span>
              <strong style={{ fontSize: 'var(--mt-text-lg)' }}>
                {byCategory.manual.length} / 10
              </strong>
            </div>
            <div className="mt-card mt-card-pad mt-stack-sm">
              <span className="mt-xs mt-muted">{t('backups.retention_prechange')}</span>
              <strong style={{ fontSize: 'var(--mt-text-lg)' }}>
                {byCategory.pre_change.length} / 10
              </strong>
            </div>
          </div>
          <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
            {t('backups.retention_note')}
          </p>
        </section>

        {/* Kunci pemulihan */}
        <section className="mt-section">
          <div className="mt-card mt-card-pad mt-stack-sm">
            <h2 style={{ fontSize: 'var(--mt-text-base)' }}>{t('backups.recovery_key_title')}</h2>
            <p className="mt-small mt-muted">{t('backups.recovery_key_desc')}</p>
            {/* Tampilkan kunci memerlukan reauth+MFA; di dev adapter ditolak sopan */}
            <Button variant="secondary" icon="eye" onClick={() => toast(t('backups.recovery_key_reauth'), 'info')}>
              {t('backups.show_key')}
            </Button>
          </div>
        </section>

        {/* Histori */}
        <section className="mt-section">
          <h2 className="mt-section-title">{t('backups.history_title')}</h2>
          <DataTable
            rows={backupsQ.data ?? []}
            columns={columns}
            rowKey={(a) => a.id}
            loading={backupsQ.isLoading}
            error={backupsQ.error ? t('common.error_generic') : undefined}
            emptyTitle={t('backups.empty_title')}
            emptyDescription={t('backups.empty_desc')}
          />
          <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
            {t('backups.staging_note')}
          </p>
        </section>

        {/* Restore terpisah — menu berisiko (UI_UX.md §10) */}
        <section className="mt-section">
          <div className="mt-banner mt-banner-warning">
            <Icon name="alertTriangle" size={20} />
            <div>
              <strong>{t('backups.restore_title')}</strong>
              <p className="mt-small">{t('backups.restore_desc')}</p>
            </div>
          </div>
        </section>
      </div>

      <ConfirmAction
        open={runOpen}
        onClose={() => setRunOpen(false)}
        onConfirm={runBackup}
        loading={running}
        title={t('backups.run_confirm_title')}
        intent={t('backups.run_confirm_intent')}
        scopeLines={[t('backups.run_scope_router'), t('backups.run_scope_note')]}
        confirmLabel={t('backups.run_now')}
      />
    </AppShell>
  );
}
