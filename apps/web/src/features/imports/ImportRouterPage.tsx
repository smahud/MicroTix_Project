import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useSession } from '../../state/session';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { PermissionNotice } from '../../design-system/components/Notices';
import { DataTable } from '../../design-system/components/DataTable';
import type { Column } from '../../design-system/components/DataTable';
import { SelectInput, Checkbox } from '../../design-system/primitives/Input';
import { Button } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { EnumBadge } from '../../design-system/components/StatusBadge';
import { ConfirmAction } from '../../design-system/components/Notices';
import { ProgressBar } from '../../design-system/primitives/Misc';
import type { DiscoveredAccount, IdentityConflictCandidate, PasswordSource } from '../../api/contracts';

const STEPS = [
  'source', 'select', 'identity', 'map_customers', 'map_profiles', 'password', 'review', 'save',
] as const;

const PASSWORD_SOURCES: PasswordSource[] = ['harvest_temporary', 'csv', 'new_password', 'radius_import'];

/**
 * U07 — Adopsi & migrasi akun existing: stepper 8 langkah (UI_UX.md §6).
 * Adopsi database-only; router TIDAK diubah; cutover RADIUS terpisah.
 */
export default function ImportRouterPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const { can } = useSession();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const routerId = params.get('router') ?? '';
  const [step, setStep] = useState(0);
  const [migrationId, setMigrationId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [conflicts, setConflicts] = useState<IdentityConflictCandidate[]>([]);
  const [resolutions, setResolutions] = useState<Record<string, 'merge' | 'keep_one' | 'rename'>>({});
  const [profileMap, setProfileMap] = useState<Record<string, string>>({});
  const [passwordSource, setPasswordSource] = useState<PasswordSource | null>(null);
  const [commitOpen, setCommitOpen] = useState(false);
  const [committing, setCommitting] = useState(false);

  const routersQ = useQuery({ queryKey: ['routers', tenantId], queryFn: () => api.listRouters(tenantId) });
  const subscriptionQ = useQuery({ queryKey: ['subscription', tenantId], queryFn: () => api.getSubscription(tenantId) });

  const accountsQ = useQuery({
    queryKey: ['discovered', tenantId, migrationId],
    queryFn: () => api.listDiscoveredAccounts(tenantId, migrationId!, { limit: 200 }),
    enabled: step >= 1 && !!migrationId,
  });

  const start = async () => {
    if (!routerId) return;
    const res = await api.startMigration(tenantId, routerId);
    setMigrationId(res.migration_id);
    setStep(1);
  };

  const accounts = accountsQ.data?.items ?? [];
  const selectedAccounts = useMemo(
    () => (accountsQ.data?.items ?? []).filter((a) => selected.has(a.id)),
    [accountsQ.data, selected],
  );
  const uniqueProfiles = useMemo(() => [...new Set(selectedAccounts.map((a) => a.profile).filter((p): p is string => !!p))], [selectedAccounts]);
  const quotaLimit = subscriptionQ.data?.plan.services_limit ?? 0;
  const quotaUsed = subscriptionQ.data?.usage.services_used ?? 0;

  const counts = {
    to_create: selectedAccounts.filter((a) => !a.disabled_on_router).length,
    to_merge: Object.values(resolutions).filter((r) => r === 'merge').length,
    conflicts: conflicts.filter((c) => c.resolution == null).length,
    quota_after: quotaUsed + selectedAccounts.length,
  };

  if (!can('migration.run')) {
    return (
      <AppShell tenantId={tenantId} title={t('nav.customers')}>
        <PermissionNotice what={t('permission.migration_run')} />
      </AppShell>
    );
  }

  const commit = async () => {
    if (!migrationId) return;
    setCommitting(true);
    try {
      await api.saveMigrationDraft(tenantId, {
        id: migrationId,
        step,
        selected_account_ids: [...selected],
        identity_resolutions: resolutions,
        profile_package_map: profileMap,
        password_source: passwordSource,
        counts: { to_create: counts.to_create, to_merge: counts.to_merge, unchanged: 0, conflicts: counts.conflicts, quota_used: counts.quota_after, quota_limit: quotaLimit },
      });
      const res = await api.commitMigration(tenantId, migrationId);
      setCommitOpen(false);
      toast(t('imports.commit_accepted'), 'success');
      await queryClient.invalidateQueries();
      navigate(`/app/${tenantId}/jobs/${res.job_id}`);
    } catch (err) {
      const e = err as { envelope?: { message?: string } };
      toast(e.envelope?.message ?? t('common.error_generic'), 'danger');
    } finally {
      setCommitting(false);
    }
  };

  const stepTitles = STEPS.map((s) => t(`imports.step_${s}` as never, undefined as never));

  const columns: Column<DiscoveredAccount>[] = [
    {
      key: 'username',
      header: t('imports.col_username'),
      render: (a) => (
        <span className="mt-mono mt-small" style={{ fontWeight: a.state === 'conflict' ? 600 : 400 }}>
          {a.username}
          {a.state === 'conflict' ? <span className="mt-xs" style={{ color: 'var(--mt-warning-fg)' }}> ({t('imports.case_sensitive_note')})</span> : null}
        </span>
      ),
    },
    { key: 'kind', header: t('imports.col_kind'), render: (a) => (a.kind === 'hotspot' ? 'Hotspot' : 'PPPoE'), hideOnMobile: true },
    { key: 'profile', header: t('imports.col_profile'), render: (a) => <span className="mt-mono mt-small">{a.profile ?? t('common.not_set')}</span>, hideOnMobile: true },
    { key: 'service', header: t('imports.col_service'), render: (a) => (a.service === 'any' ? <EnumBadge group="service" value={a.service} tone="warning" /> : a.service === 'pppoe' ? 'PPPoE' : 'Hotspot'), hideOnMobile: true },
    {
      key: 'state',
      header: t('imports.col_state'),
      render: (a) => <EnumBadge group="discovery_state" value={a.state} tone={a.state === 'conflict' ? 'warning' : 'neutral'} />,
    },
  ];

  return (
    <AppShell tenantId={tenantId} title={t('nav.customers')}>
      <PageHeader
        breadcrumbs={[{ label: t('routers.list_title'), to: `/app/${tenantId}/routers` }, { label: t('imports.title') }]}
        title={t('imports.title')}
        description={t('imports.desc')}
      />

      <div className="mt-card mt-card-pad mt-stack">
        {/* Stepper 8 langkah */}
        <ol className="mt-stepper" aria-label={t('imports.wizard_steps')}>
          {stepTitles.map((s, i) => (
            <li key={s}>
              <button
                type="button"
                className={`mt-step${i < step ? ' mt-step-done' : ''}`}
                aria-current={i === step ? 'step' : undefined}
                disabled={i > step}
                onClick={() => i < step && setStep(i)}
              >
                <span className="mt-step-index">{i < step ? <Icon name="check" size={13} /> : i + 1}</span>
                {s}
              </button>
            </li>
          ))}
        </ol>

        {/* Peringatan FastTrack (UI_UX.md §6) */}
        {step >= 1 ? (
          <p className="mt-banner mt-banner-warning">
            <Icon name="alertTriangle" size={18} />
            {t('imports.fasttrack_warning')}
          </p>
        ) : null}

        {/* Langkah 0: Sumber */}
        {step === 0 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_source')}</h2>
            <div style={{ maxWidth: 420 }}>
              <SelectInput
                label={t('imports.f_source_router')}
                options={(routersQ.data ?? []).map((r) => ({ value: r.id, label: `${r.display_name} (${r.router_code})` }))}
                value={routerId}
                placeholderOption={t('imports.f_source_router_placeholder')}
                onChange={(e) => {
                  const next = new URLSearchParams();
                  if (e.target.value) next.set('router', e.target.value);
                  setParams(next, { replace: true });
                  setMigrationId(null);
                }}
                helper={t('imports.f_source_helper')}
              />
            </div>
            <Button variant="primary" onClick={start} disabled={!routerId} loading={accountsQ.isFetching && step === 0}>
              {t('common.continue')}
            </Button>
          </div>
        ) : null}

        {/* Langkah 1: Pilih akun */}
        {step === 1 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_select')}</h2>
            <p className="mt-small mt-muted">{t('imports.select_desc')}</p>
            <DataTable
              rows={accounts}
              columns={columns}
              rowKey={(a) => a.id}
              loading={accountsQ.isLoading}
              selectable
              selectedIds={selected}
              onToggleSelect={(id, checked) =>
                setSelected((prev) => {
                  const next = new Set(prev);
                  if (checked) next.add(id);
                  else next.delete(id);
                  return next;
                })
              }
              onToggleSelectAll={(checked) => setSelected(checked ? new Set(accounts.map((a) => a.id)) : new Set())}
              allSelected={accounts.length > 0 && accounts.every((a) => selected.has(a.id))}
              someSelected={selected.size > 0 && !accounts.every((a) => selected.has(a.id))}
              emptyTitle={t('imports.no_accounts_title')}
              emptyDescription={t('imports.no_accounts_desc')}
            />
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(0)}>
                {t('common.back')}
              </Button>
              <Button
                variant="primary"
                disabled={selected.size === 0}
                onClick={async () => {
                  setConflicts(await api.getIdentityConflicts(tenantId, migrationId!));
                  setStep(2);
                }}
              >
                {t('common.continue')} ({selected.size})
              </Button>
            </div>
          </div>
        ) : null}

        {/* Langkah 2: Gabungkan identitas */}
        {step === 2 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_identity')}</h2>
            <p className="mt-small mt-muted">{t('imports.identity_desc')}</p>
            {conflicts.length === 0 ? (
              <p className="mt-banner mt-banner-success">
                <Icon name="checkCircle" size={18} /> {t('imports.identity_no_conflicts')}
              </p>
            ) : (
              <div className="mt-stack-sm">
                {conflicts.map((c) => (
                  <div key={c.candidate_group_id} className="mt-card mt-card-pad mt-stack-sm">
                    <div className="mt-small">
                      <strong className="mt-mono">{c.usernames[0]}</strong> <span className="mt-muted">vs</span>{' '}
                      <strong className="mt-mono">{c.usernames[1]}</strong>
                      <span className="mt-xs mt-muted"> · {c.routers.length} router · {t(`imports.conflict_kind_${c.kind}` as never, undefined as never)}</span>
                    </div>
                    <fieldset style={{ border: 0, padding: 0, margin: 0 }} className="mt-stack-sm">
                      <div className="mt-row" style={{ gap: 'var(--mt-space-2)' }}>
                        {(['merge', 'keep_one', 'rename'] as const).map((res) => (
                          <Checkbox
                            key={res}
                            type="radio"
                            name={`res-${c.candidate_group_id}`}
                            checked={(resolutions[c.candidate_group_id] ?? null) === res}
                            onChange={() =>
                              setResolutions((prev) => ({ ...prev, [c.candidate_group_id]: res }))
                            }
                            label={t(`imports.resolution_${res}` as never, undefined as never)}
                          />
                        ))}
                      </div>
                    </fieldset>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(1)}>
                {t('common.back')}
              </Button>
              <Button variant="primary" disabled={conflicts.some((c) => !resolutions[c.candidate_group_id])} onClick={() => setStep(3)}>
                {t('common.continue')}
              </Button>
            </div>
          </div>
        ) : null}

        {/* Langkah 3: Petakan pelanggan */}
        {step === 3 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_map_customers')}</h2>
            <p className="mt-small mt-muted">{t('imports.map_customers_desc')}</p>
            <p className="mt-banner mt-banner-info">
              <Icon name="info" size={18} /> {t('imports.map_customers_note')}
            </p>
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(2)}>
                {t('common.back')}
              </Button>
              <Button variant="primary" onClick={() => setStep(4)}>
                {t('common.continue')}
              </Button>
            </div>
          </div>
        ) : null}

        {/* Langkah 4: Petakan profile/paket */}
        {step === 4 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_map_profiles')}</h2>
            <p className="mt-small mt-muted">{t('imports.map_profiles_desc')}</p>
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
              {uniqueProfiles.map((p) => (
                <div key={p} className="mt-card mt-card-pad mt-stack-sm">
                  <span className="mt-mono mt-small" style={{ fontWeight: 600 }}>
                    {p}
                  </span>
                  <SelectInput
                    label={t('imports.f_package_for_profile')}
                    options={[
                      { value: 'pkg-20m', label: t('imports.pkg_20m') },
                      { value: 'pkg-50m', label: t('imports.pkg_50m') },
                      { value: 'pkg-10m', label: t('imports.pkg_10m') },
                      { value: 'unmapped', label: t('imports.pkg_unmapped') },
                    ]}
                    value={profileMap[p] ?? ''}
                    placeholderOption={t('imports.pkg_unmapped')}
                    onChange={(e) => setProfileMap((prev) => ({ ...prev, [p]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
            <p className="mt-xs mt-muted">{t('imports.map_profiles_note')}</p>
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(3)}>
                {t('common.back')}
              </Button>
              <Button variant="primary" onClick={() => setStep(5)}>
                {t('common.continue')}
              </Button>
            </div>
          </div>
        ) : null}

        {/* Langkah 5: Sumber password */}
        {step === 5 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_password')}</h2>
            <p className="mt-small mt-muted">{t('imports.password_desc')}</p>
            <div className="mt-stack-sm">
              {PASSWORD_SOURCES.map((src) => (
                <label key={src} className="mt-card mt-card-pad" style={{ display: 'flex', gap: 'var(--mt-space-3)', alignItems: 'flex-start', cursor: 'pointer', borderColor: passwordSource === src ? 'var(--mt-primary)' : undefined }}>
                  <input
                    type="radio"
                    name="pw-source"
                    checked={passwordSource === src}
                    onChange={() => setPasswordSource(src)}
                    style={{ marginTop: 4, accentColor: 'var(--mt-primary)' }}
                  />
                  <span>
                    <span className="mt-small" style={{ fontWeight: 600 }}>
                      {t(`imports.pw_${src}` as never, undefined as never)}
                    </span>
                    <span className="mt-xs mt-muted" style={{ display: 'block' }}>
                      {t(`imports.pw_${src}_impact` as never, undefined as never)}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            {passwordSource === 'harvest_temporary' ? (
              <p className="mt-banner mt-banner-warning">
                <Icon name="clock" size={18} /> {t('imports.pw_harvest_ttl_note')}
              </p>
            ) : null}
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(4)}>
                {t('common.back')}
              </Button>
              <Button
                variant="primary"
                disabled={!passwordSource}
                onClick={async () => {
                  if (passwordSource === 'harvest_temporary' && migrationId) {
                    const res = await api.requestPasswordHarvest(tenantId, routerId);
                    toast(t('imports.harvest_started'), 'info');
                    void res;
                  }
                  setStep(6);
                }}
              >
                {t('common.continue')}
              </Button>
            </div>
          </div>
        ) : null}

        {/* Langkah 6: Validasi dan tinjau */}
        {step === 6 ? (
          <div className="mt-stack">
            <h2>{t('imports.step_review')}</h2>
            <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <span className="mt-xs mt-muted">{t('imports.count_create')}</span>
                <strong style={{ fontSize: 'var(--mt-text-lg)' }}>{counts.to_create}</strong>
              </div>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <span className="mt-xs mt-muted">{t('imports.count_merge')}</span>
                <strong style={{ fontSize: 'var(--mt-text-lg)' }}>{counts.to_merge}</strong>
              </div>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <span className="mt-xs mt-muted">{t('imports.count_conflicts')}</span>
                <strong style={{ fontSize: 'var(--mt-text-lg)' }}>{counts.conflicts}</strong>
              </div>
              <div className="mt-card mt-card-pad mt-stack-sm">
                <span className="mt-xs mt-muted">{t('imports.count_quota')}</span>
                <strong style={{ fontSize: 'var(--mt-text-lg)' }}>
                  {counts.quota_after} / {quotaLimit == null ? '∞' : quotaLimit}
                </strong>
                <ProgressBar value={counts.quota_after} max={quotaLimit || counts.quota_after || 1} />
              </div>
            </div>
            {passwordSource == null ? (
              <p className="mt-banner mt-banner-warning">
                <Icon name="lock" size={18} /> {t('imports.pw_unknown_note')}
              </p>
            ) : null}
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(5)}>
                {t('common.back')}
              </Button>
              <Button variant="primary" onClick={() => setStep(7)}>
                {t('common.continue')}
              </Button>
            </div>
          </div>
        ) : null}

        {/* Langkah 7: Simpan */}
        {step === 7 ? (
          <div className="mt-stack" style={{ alignItems: 'flex-start' }}>
            <h2>{t('imports.step_save')}</h2>
            <ul className="mt-small mt-muted" style={{ paddingLeft: 20 }}>
              <li>
                {t('imports.save_scope_accounts', { count: selected.size })} — {t('imports.save_scope_router_unchanged')}
              </li>
              <li>{t('imports.save_scope_password', { source: t(`imports.pw_${passwordSource ?? 'unknown'}` as never, undefined as never) })}</li>
            </ul>
            <div className="mt-row">
              <Button variant="secondary" onClick={() => setStep(6)}>
                {t('common.back')}
              </Button>
              <Button variant="primary" onClick={() => setCommitOpen(true)}>
                {t('imports.save_cta')}
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <ConfirmAction
        open={commitOpen}
        onClose={() => setCommitOpen(false)}
        onConfirm={commit}
        loading={committing}
        title={t('imports.commit_title')}
        intent={t('imports.commit_intent')}
        scopeLines={[
          t('imports.commit_scope_tenant'),
          t('imports.commit_scope_count', { count: selected.size }),
          t('imports.commit_scope_router_unchanged'),
          t('imports.commit_scope_billing'),
        ]}
        confirmLabel={t('imports.save_cta')}
      />
    </AppShell>
  );
}
