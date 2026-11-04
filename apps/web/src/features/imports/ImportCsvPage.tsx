import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { PermissionNotice } from '../../design-system/components/Notices';
import { SelectInput } from '../../design-system/primitives/Input';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { ConfirmAction } from '../../design-system/components/Notices';
import { EmptyState } from '../../design-system/primitives/Misc';
import type { CsvImportMode, CsvValidationResult } from '../../api/contracts';

const MODES: CsvImportMode[] = ['create', 'link', 'update', 'device_mapping', 'password_migration'];
const MAX_BYTES = 10 * 1024 * 1024; // csv.max_bytes default
const MAX_ROWS = 10_000; // csv.max_rows default

/** Contoh dua baris template (UI_UX.md §6) — header kolom baku bahasa Inggris (I18N.md §5). */
const TEMPLATE_HEADER = 'username,full_name,package,service_kind,phone,address';
const TEMPLATE_EXAMPLE = 'budi.santoso,Budi Santoso,Paket Rumah 20 Mbps,pppoe,081234567801,"Jl. Melati 12"\nsiti.aminah,Siti Aminah,Paket Rumah 20 Mbps,pppoe,081234567802,"Jl. Kenanga 4"';

/**
 * U08 — Impor CSV: unduh template, pilih mode sebelum mapping, validasi,
 * error per baris (baris, field, alasan, tindakan), hasil (UI_UX.md §6).
 */
export default function ImportCsvPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const { can } = useSession();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<CsvImportMode>('create');
  const [importId, setImportId] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');
  const [validation, setValidation] = useState<CsvValidationResult | null>(null);
  const [validating, setValidating] = useState(false);
  const [commitOpen, setCommitOpen] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const downloadTemplate = () => {
    const content = `${TEMPLATE_HEADER}\n${TEMPLATE_EXAMPLE}\n`;
    const blob = new Blob([content], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'microtix-template-pelanggan.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setFileError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setFileError(t('imports.csv_too_large', { mb: 10 }));
      return;
    }
    const text = await file.text();
    const lines = text.split(/\r?\n/).filter((l) => l.trim() !== '');
    if (lines.length - 1 > MAX_ROWS) {
      setFileError(t('imports.csv_too_many_rows', { count: MAX_ROWS }));
      return;
    }
    const header = lines[0]?.split(',').map((h) => h.trim()) ?? [];
    const rows = lines.slice(1).map((line) => {
      const cells = line.split(',').map((c) => c.replace(/^"|"$/g, ''));
      const row: Record<string, string> = {};
      header.forEach((h, i) => {
        row[h] = cells[i] ?? '';
      });
      return row;
    });
    const res = await api.createCsvImport(tenantId, { mode, file_name: file.name, rows });
    setImportId(res.id);
    setFileName(file.name);
    setValidation(null);
  };

  const validate = async () => {
    if (!importId) return;
    setValidating(true);
    try {
      const res = await api.validateCsvImport(tenantId, importId);
      setValidation(res);
    } finally {
      setValidating(false);
    }
  };

  const commit = async () => {
    if (!importId) return;
    setCommitting(true);
    try {
      const res = await api.commitCsvImport(tenantId, importId);
      setCommitOpen(false);
      toast(t('imports.csv_committed', { count: validation?.valid_rows ?? 0 }), 'success');
      await queryClient.invalidateQueries();
      navigate(`/app/${tenantId}/jobs/${res.job_id}`);
    } finally {
      setCommitting(false);
    }
  };

  if (!can('imports.run')) {
    return (
      <AppShell tenantId={tenantId} title={t('nav.customers')}>
        <PermissionNotice what={t('permission.imports_run')} />
      </AppShell>
    );
  }

  return (
    <AppShell tenantId={tenantId} title={t('nav.customers')}>
      <PageHeader
        title={t('imports.csv_title')}
        description={t('imports.csv_desc')}
      />

      <div className="mt-stack">
        {/* Template */}
        <div className="mt-card mt-card-pad mt-stack">
          <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
            {t('imports.csv_template_title')}
          </h2>
          <p className="mt-small mt-muted">{t('imports.csv_template_desc', { mb: 10, rows: '10.000' })}</p>
          <pre className="mt-code" style={{ maxHeight: 140 }}>
            {TEMPLATE_HEADER}
            {TEMPLATE_EXAMPLE.split('\n').map((l) => `\n${l}`)}
          </pre>
          <Button variant="secondary" icon="download" onClick={downloadTemplate}>
            {t('imports.csv_download_template')}
          </Button>
        </div>

        {/* Mode dipilih sebelum mapping (UI_UX.md §6) */}
        <div className="mt-card mt-card-pad mt-stack">
          <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
            {t('imports.csv_mode_title')}
          </h2>
          <div style={{ maxWidth: 420 }}>
            <SelectInput
              label={t('imports.csv_f_mode')}
              options={MODES.map((m) => ({ value: m, label: t(`imports.csv_mode_${m}` as never, undefined as never) }))}
              value={mode}
              onChange={(e) => {
                setMode(e.target.value as CsvImportMode);
                setImportId(null);
                setValidation(null);
                if (fileRef.current) fileRef.current.value = '';
              }}
              helper={t(`imports.csv_mode_${mode}_impact` as never, undefined as never)}
            />
          </div>
        </div>

        {/* Unggah */}
        <div className="mt-card mt-card-pad mt-stack">
          <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
            {t('imports.csv_upload_title')}
          </h2>
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={onFile} aria-label={t('imports.csv_f_file')} />
          {fileError ? (
            <p className="mt-banner mt-banner-danger" role="alert">
              <Icon name="alertCircle" size={18} /> {fileError}
            </p>
          ) : null}
          {fileName ? (
            <p className="mt-small mt-muted">
              <Icon name="fileText" size={16} /> {fileName}
            </p>
          ) : null}
          <div className="mt-row">
            <Button variant="secondary" onClick={() => fileRef.current?.click()} icon="upload">
              {t('imports.csv_pick_file')}
            </Button>
            <Button variant="primary" onClick={validate} disabled={!importId} loading={validating}>
              {t('imports.csv_validate_cta')}
            </Button>
          </div>
        </div>

        {/* Hasil validasi */}
        {validation ? (
          <div className="mt-card mt-card-pad mt-stack">
            <h2 className="mt-section-title" style={{ fontSize: 'var(--mt-text-base)' }}>
              {t('imports.csv_result_title')}
            </h2>
            <div className="mt-row" style={{ gap: 'var(--mt-space-4)' }}>
              <span className="mt-small">
                {t('imports.csv_total_rows')}: <strong>{validation.total_rows}</strong>
              </span>
              <span className="mt-small" style={{ color: 'var(--mt-success-fg)' }}>
                {t('imports.csv_valid_rows')}: <strong>{validation.valid_rows}</strong>
              </span>
              <span className="mt-small" style={{ color: validation.error_rows ? 'var(--mt-danger-fg)' : undefined }}>
                {t('imports.csv_error_rows')}: <strong>{validation.error_rows}</strong>
              </span>
            </div>

            {validation.error_rows > 0 ? (
              <div className="mt-stack-sm">
                <p className="mt-small mt-muted">{t('imports.csv_errors_desc')}</p>
                <div className="mt-table-wrap">
                  <table className="mt-table">
                    <thead>
                      <tr>
                        <th scope="col">{t('imports.csv_err_row')}</th>
                        <th scope="col">{t('imports.csv_err_field')}</th>
                        <th scope="col">{t('imports.csv_err_reason')}</th>
                        <th scope="col">{t('imports.csv_err_action')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {validation.row_errors.map((e, i) => (
                        <tr key={i}>
                          <td className="mt-table-num">{e.row}</td>
                          <td className="mt-mono">{e.field ?? '—'}</td>
                          <td>
                            {t(`validation.csv_${e.reason_code}` as never, undefined as never)}
                          </td>
                          <td className="mt-muted">{e.action_hint}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-xs mt-muted">{t('imports.csv_retry_note')}</p>
              </div>
            ) : null}

            {validation.valid_rows > 0 ? (
              <div className="mt-row">
                <Button variant="primary" icon="check" onClick={() => setCommitOpen(true)}>
                  {t('imports.csv_commit_cta', { count: validation.valid_rows })}
                </Button>
              </div>
            ) : (
              <EmptyState
                icon={<Icon name="alertTriangle" size={36} />}
                title={t('imports.csv_all_invalid_title')}
                description={t('imports.csv_all_invalid_desc')}
              />
            )}
          </div>
        ) : null}
      </div>

      <ConfirmAction
        open={commitOpen}
        onClose={() => setCommitOpen(false)}
        onConfirm={commit}
        loading={committing}
        title={t('imports.csv_commit_title')}
        intent={t('imports.csv_commit_intent', { count: validation?.valid_rows ?? 0 })}
        scopeLines={[
          t('imports.commit_scope_tenant'),
          t('imports.csv_commit_scope_mode', { mode: t(`imports.csv_mode_${mode}` as never, undefined as never) }),
          t('imports.csv_commit_scope_empty_note'),
        ]}
        confirmLabel={t('imports.csv_commit_cta', { count: validation?.valid_rows ?? 0 })}
      />
    </AppShell>
  );
}
