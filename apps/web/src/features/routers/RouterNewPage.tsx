import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import type { EnrollmentProtocol } from '../../api/contracts';
import { useToast } from '../../design-system/primitives/Toast';
import { AppShell } from '../../design-system/components/AppShell';
import { PageHeader } from '../../design-system/components/PageHeader';
import { TextInput, Checkbox } from '../../design-system/primitives/Input';
import { Button, ButtonLink } from '../../design-system/primitives/Button';
import { Icon } from '../../design-system/primitives/Icon';
import { useSession } from '../../state/session';
import { PermissionNotice } from '../../design-system/components/Notices';

/**
 * U05 — Enrollment router: Identitas (protokol+versi) → Prasyarat → Skrip →
 * Menunggu → Siap (UI_UX.md §7). Jangan menulis "Router terhubung" sebelum
 * handshake DAN API terverifikasi — dan sumber verifikasi (simulator vs
 * perangkat nyata) selalu diperlihatkan jujur (master directive §10).
 */
export default function RouterNewPage({ tenantId }: { tenantId: string }) {
  const t = useT();
  const api = useApi();
  const { toast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { can } = useSession();
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [creating, setCreating] = useState(false);
  const [enrollmentId, setEnrollmentId] = useState<string | null>(null);
  const [form, setForm] = useState({
    display_name: '',
    router_code: '',
    location: '',
    mode: 'read_only' as 'read_only' | 'managed',
    protocol: 'wireguard' as EnrollmentProtocol,
    routeros_version: '7' as '7' | '6',
  });

  // WireGuard hadir sejak RouterOS 7.1 (riset capability matrix) — pada v6
  // tidak ada protokol yang didukung rilis ini (SSTP menyusul, fase berikutnya).
  const wireguardAvailable = form.routeros_version === '7';
  const protocolAvailable = wireguardAvailable && form.protocol === 'wireguard';

  const scriptQ = useQuery({
    queryKey: ['bootstrap-script', tenantId, enrollmentId],
    queryFn: () => api.getBootstrapScript(tenantId, enrollmentId!),
    enabled: step >= 2 && !!enrollmentId,
    retry: false,
  });

  const progressQ = useQuery({
    queryKey: ['enrollment-progress', tenantId, enrollmentId],
    queryFn: () => api.getEnrollment(tenantId, enrollmentId!),
    enabled: step === 3 && !!enrollmentId,
    refetchInterval: (q) => ((q.state.data?.state ?? '') === 'discovery_ready' ? false : 2000),
  });

  const enrollmentState = progressQ.data?.state;
  useEffect(() => {
    if (enrollmentState === 'discovery_ready') setStep(4);
  }, [enrollmentState]);

  if (!can('routers.enroll')) {
    return (
      <AppShell tenantId={tenantId} title={t('nav.routers')}>
        <PermissionNotice what={t('permission.routers_enroll')} />
      </AppShell>
    );
  }

  const steps = [
    t('routers.step_identity'),
    t('routers.step_prereq'),
    t('routers.step_script'),
    t('routers.step_waiting'),
    t('routers.step_ready'),
  ];

  const submitIdentity = async () => {
    setErrors({});
    const errs: Record<string, string | undefined> = {};
    if (!form.display_name.trim()) errs.display_name = t('validation.required');
    if (!/^[A-Z0-9-]{2,16}$/.test(form.router_code)) errs.router_code = t('validation.router_code');
    if (!wireguardAvailable) errs.routeros_version = t('routers.protocol_v6_unsupported');
    else if (form.protocol !== 'wireguard') errs.protocol = t('routers.protocol_planned');
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setCreating(true);
    try {
      const res = await api.createEnrollment(tenantId, {
        display_name: form.display_name,
        router_code: form.router_code,
        location: form.location || null,
        mode: form.mode,
        protocol: form.protocol,
        routeros_version: form.routeros_version,
      });
      setEnrollmentId(res.id);
      await queryClient.invalidateQueries({ queryKey: ['routers', tenantId] });
      setStep(1);
    } catch (err) {
      const e = err as { envelope?: { field_errors?: Record<string, Array<{ message: string }>> } };
      const fe = e.envelope?.field_errors;
      if (fe) {
        const mapped: Record<string, string | undefined> = {};
        for (const [k, v] of Object.entries(fe)) mapped[k] = v[0]?.message;
        setErrors(mapped);
      }
    } finally {
      setCreating(false);
    }
  };

  const copyScript = () => {
    if (scriptQ.data) {
      void navigator.clipboard?.writeText(scriptQ.data.script);
      toast(t('routers.script_copied'), 'success');
    }
  };

  const expired = scriptQ.error != null;

  return (
    <AppShell tenantId={tenantId} title={t('nav.routers')}>
      <PageHeader
        breadcrumbs={[{ label: t('routers.list_title'), to: `/app/${tenantId}/routers` }, { label: t('routers.new_title') }]}
        title={t('routers.new_title')}
        description={t('routers.new_desc')}
      />

      <div className="mt-card mt-card-pad">
        {/* Stepper */}
        <ol className="mt-stepper" aria-label={t('routers.wizard_steps')}>
          {steps.map((s, i) => (
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

        <div style={{ marginTop: 'var(--mt-space-4)' }}>
          {step === 0 ? (
            <div className="mt-stack">
              <div className="mt-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                <TextInput
                  label={t('routers.f_display_name')}
                  value={form.display_name}
                  onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                  error={errors.display_name}
                  required
                />
                <TextInput
                  label={t('routers.f_router_code')}
                  value={form.router_code}
                  onChange={(e) => setForm((f) => ({ ...f, router_code: e.target.value.toUpperCase() }))}
                  error={errors.router_code}
                  placeholder="RTR-UTAMA"
                  helper={t('routers.f_router_code_helper')}
                  required
                />
                <TextInput
                  label={t('routers.f_location')}
                  value={form.location}
                  onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                />
              </div>
              <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                <legend className="mt-label" style={{ marginBottom: 'var(--mt-space-2)' }}>
                  {t('routers.f_mode')}
                </legend>
                <div className="mt-stack-sm">
                  <Checkbox
                    type="radio"
                    name="mode"
                    checked={form.mode === 'read_only'}
                    onChange={() => setForm((f) => ({ ...f, mode: 'read_only' }))}
                    label={t('routers.mode_read_only')}
                    hint={t('routers.mode_read_only_hint')}
                  />
                  <Checkbox
                    type="radio"
                    name="mode"
                    checked={form.mode === 'managed'}
                    onChange={() => setForm((f) => ({ ...f, mode: 'managed' }))}
                    label={t('routers.mode_managed')}
                    hint={t('routers.mode_managed_hint')}
                  />
                </div>
              </fieldset>
              <fieldset style={{ border: 0, padding: 0, margin: 0 }} data-testid="fieldset-routeros-version">
                <legend className="mt-label" style={{ marginBottom: 'var(--mt-space-2)' }}>
                  {t('routers.f_routeros_version')}
                </legend>
                <div className="mt-stack-sm">
                  <Checkbox
                    type="radio"
                    name="routeros_version"
                    checked={form.routeros_version === '7'}
                    onChange={() => setForm((f) => ({ ...f, routeros_version: '7' }))}
                    label={t('routers.version_v7')}
                    hint={t('routers.version_v7_hint')}
                  />
                  <Checkbox
                    type="radio"
                    name="routeros_version"
                    checked={form.routeros_version === '6'}
                    onChange={() => setForm((f) => ({ ...f, routeros_version: '6' }))}
                    label={t('routers.version_v6')}
                    hint={t('routers.version_v6_hint')}
                  />
                </div>
                {errors.routeros_version ? (
                  <p className="mt-banner mt-banner-warning mt-small" role="alert" style={{ marginBottom: 0 }}>
                    <Icon name="alertTriangle" size={16} /> {errors.routeros_version}
                  </p>
                ) : null}
              </fieldset>
              <fieldset style={{ border: 0, padding: 0, margin: 0 }} data-testid="fieldset-protocol">
                <legend className="mt-label" style={{ marginBottom: 'var(--mt-space-2)' }}>
                  {t('routers.f_protocol')}
                </legend>
                <div className="mt-stack-sm">
                  <Checkbox
                    type="radio"
                    name="protocol"
                    checked={form.protocol === 'wireguard'}
                    disabled={!wireguardAvailable}
                    onChange={() => setForm((f) => ({ ...f, protocol: 'wireguard' }))}
                    label={t('routers.protocol_wireguard')}
                    hint={wireguardAvailable ? t('routers.protocol_wireguard_hint') : t('routers.protocol_v6_unsupported')}
                  />
                  <Checkbox
                    type="radio"
                    name="protocol"
                    checked={form.protocol === 'sstp'}
                    disabled
                    onChange={() => setForm((f) => ({ ...f, protocol: 'sstp' }))}
                    label={t('routers.protocol_sstp')}
                    hint={t('routers.protocol_planned')}
                  />
                  <Checkbox
                    type="radio"
                    name="protocol"
                    checked={form.protocol === 'l2tp_ipsec'}
                    disabled
                    onChange={() => setForm((f) => ({ ...f, protocol: 'l2tp_ipsec' }))}
                    label={t('routers.protocol_l2tp')}
                    hint={t('routers.protocol_planned')}
                  />
                  <Checkbox
                    type="radio"
                    name="protocol"
                    checked={form.protocol === 'openvpn'}
                    disabled
                    onChange={() => setForm((f) => ({ ...f, protocol: 'openvpn' }))}
                    label={t('routers.protocol_ovpn')}
                    hint={t('routers.protocol_planned')}
                  />
                </div>
                {errors.protocol ? (
                  <p className="mt-banner mt-banner-warning mt-small" role="alert" style={{ marginBottom: 0 }}>
                    <Icon name="alertTriangle" size={16} /> {errors.protocol}
                  </p>
                ) : null}
              </fieldset>
              <div className="mt-row">
                <Button
                  variant="primary"
                  onClick={submitIdentity}
                  loading={creating}
                  disabled={!protocolAvailable}
                  disabledReason={protocolAvailable ? undefined : t('routers.protocol_v6_unsupported')}
                >
                  {t('common.continue')}
                </Button>
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="mt-stack">
              <h2>{t('routers.prereq_title')}</h2>
              <ul className="mt-stack-sm mt-small mt-muted" style={{ paddingLeft: 20 }}>
                <li>{t('routers.prereq_chosen', { protocol: t('routers.protocol_wireguard'), version: form.routeros_version === '7' ? t('routers.version_v7') : t('routers.version_v6') })}</li>
                <li>{t('routers.prereq_v7')}</li>
                <li>{t('routers.prereq_internet')}</li>
                <li>{t('routers.prereq_terminal')}</li>
                <li>{t('routers.prereq_no_port')}</li>
              </ul>
              <div className="mt-row">
                <Button variant="secondary" onClick={() => setStep(0)}>
                  {t('common.back')}
                </Button>
                <Button variant="primary" onClick={() => setStep(2)}>
                  {t('common.continue')}
                </Button>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="mt-stack">
              <h2>{t('routers.script_title')}</h2>
              {scriptQ.isLoading ? (
                <p className="mt-muted">{t('common.loading')}</p>
              ) : expired ? (
                <div className="mt-stack-sm">
                  <p className="mt-banner mt-banner-warning">
                    <Icon name="clock" size={18} /> {t('routers.script_expired')}
                  </p>
                  <Button
                    variant="secondary"
                    icon="refresh"
                    onClick={() => {
                      void queryClient.invalidateQueries({ queryKey: ['bootstrap-script', tenantId, enrollmentId] });
                    }}
                  >
                    {t('routers.script_regenerate')}
                  </Button>
                </div>
              ) : scriptQ.data ? (
                <>
                  <p className="mt-small mt-muted">{t('routers.script_purpose')}</p>
                  {scriptQ.data.gateway ? (
                    <p className="mt-small mt-mono" data-testid="gateway-line" style={{ margin: 0 }}>
                      <Icon name="router" size={15} />{' '}
                      {t('routers.script_gateway', {
                        hostname: scriptQ.data.gateway.hostname,
                        port: String(scriptQ.data.gateway.listen_port),
                        server_ip: scriptQ.data.gateway.server_tunnel_ip,
                        api_port: String(scriptQ.data.gateway.api_port),
                      })}
                    </p>
                  ) : null}
                  <ul className="mt-small mt-muted" style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {scriptQ.data.purpose_summary.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                  <pre className="mt-code" data-testid="bootstrap-script">{scriptQ.data.script}</pre>
                  <p className="mt-xs mt-muted">
                    {t('routers.script_expires_note')} · {t('routers.script_confidential')}
                  </p>
                  <div className="mt-row">
                    <Button variant="secondary" onClick={() => setStep(1)}>
                      {t('common.back')}
                    </Button>
                    <Button variant="primary" icon="copy" onClick={copyScript}>
                      {t('routers.copy_script')}
                    </Button>
                    <Button variant="primary" onClick={() => setStep(3)} disabled={!scriptQ.data}>
                      {t('routers.script_waiting_cta')}
                    </Button>
                  </div>
                </>
              ) : null}
            </div>
          ) : null}

          {step === 3 ? (
            <div className="mt-stack">
              <h2>{t('routers.waiting_title')}</h2>
              <p className="mt-small mt-muted">{t('routers.waiting_desc')}</p>
              <div className="mt-stack-sm">
                {(progressQ.data?.stage_detail ?? []).map((st) => (
                  <div key={st.code} className="mt-row-between" style={{ borderBottom: '1px solid var(--mt-neutral-border)', paddingBottom: 'var(--mt-space-2)' }}>
                    <span className="mt-small">{t(`routers.stage_${st.code}` as never, undefined as never)}</span>
                    {st.state === 'ok' ? (
                      <Icon name="checkCircle" size={18} style={{ color: 'var(--mt-success-fg)' }} />
                    ) : st.state === 'failed' ? (
                      <Icon name="alertCircle" size={18} style={{ color: 'var(--mt-danger-fg)' }} />
                    ) : (
                      <Icon name="spinner" size={18} className="mt-spinner" style={{ color: 'var(--mt-text-secondary)' }} />
                    )}
                  </div>
                ))}
              </div>
              <p className="mt-xs mt-muted">{t('routers.waiting_note')}</p>
              <Button variant="secondary" onClick={() => setStep(2)}>
                {t('common.back')}
              </Button>
            </div>
          ) : null}

          {step === 4 ? (
            <div className="mt-stack" style={{ textAlign: 'center', alignItems: 'center' }}>
              <Icon name="checkCircle" size={44} style={{ color: 'var(--mt-success-fg)' }} />
              <h2>{t('routers.ready_title')}</h2>
              <p className="mt-muted" style={{ maxWidth: 480 }}>
                {t('routers.ready_desc')}
              </p>
              {progressQ.data?.verification?.source === 'simulator' ? (
                <p className="mt-banner mt-banner-warning mt-small" data-testid="simulated-verification-banner" style={{ maxWidth: 560 }}>
                  <Icon name="alertTriangle" size={18} /> {t('routers.verification_simulated_note')}
                </p>
              ) : progressQ.data?.verification?.source === 'api_ssl' ? (
                <p className="mt-banner mt-banner-info mt-small" style={{ maxWidth: 560 }}>
                  <Icon name="shield" size={18} /> {t('routers.verification_api_ssl_note')}
                </p>
              ) : null}
              <div className="mt-row">
                <Button variant="primary" icon="search" onClick={() => navigate(`/app/${tenantId}/imports/router`)}>
                  {t('routers.cta_scan_accounts')}
                </Button>
                <ButtonLink to={`/app/${tenantId}/monitoring`} variant="secondary">
                  {t('routers.cta_monitoring')}
                </ButtonLink>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
