import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useT } from '../../i18n/useT';
import { useApi } from '../../api';
import { useToast } from '../../design-system/primitives/Toast';
import { TextInput, SelectInput, Checkbox } from '../../design-system/primitives/Input';
import { Button } from '../../design-system/primitives/Button';
import { Dialog } from '../../design-system/primitives/Dialog';
import { Icon } from '../../design-system/primitives/Icon';

/**
 * Tambah pelanggan (UI_UX.md §3): enam field awal + bagian Lanjutan +
 * pilihan akhir dengan keterangan dampak persis dari spesifikasi.
 */
const FINAL_CHOICES = [
  { value: 'draft', icon: 'fileText' },
  { value: 'link_existing', icon: 'link' },
  { value: 'create_account', icon: 'key' },
  { value: 'create_and_activate', icon: 'zap' },
] as const;

type FinalChoice = (typeof FINAL_CHOICES)[number]['value'];

export function AddCustomerDialog({
  open,
  onClose,
  tenantId,
  routers,
}: {
  open: boolean;
  onClose: () => void;
  tenantId: string;
  routers: Array<{ value: string; label: string }>;
}) {
  const t = useT();
  const api = useApi();
  const { toast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [advanced, setAdvanced] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({
    customer_name: '',
    label: '',
    router_id: '',
    kind: 'pppoe',
    package_name: '',
    start_date: '',
    contact: '',
    address: '',
    ip: '',
    mac: '',
    odp: '',
  });
  const [choice, setChoice] = useState<FinalChoice>('draft');

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setErrors({});
    setFormError(null);
    const errs: Record<string, string | undefined> = {};
    if (!form.customer_name.trim()) errs.customer_name = t('validation.required');
    if (form.ip && !/^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/.test(form.ip)) {
      errs.ip = t('validation.ip_prefix');
    }
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setSaving(true);
    try {
      const res = await api.createServiceDraft(tenantId, {
        customer_name: form.customer_name,
        label: form.label || null,
        router_id: form.router_id || null,
        kind: form.kind,
        package_name: form.package_name || null,
        start_date: form.start_date || null,
        contact: form.contact || null,
        final_choice: choice,
      });
      await queryClient.invalidateQueries({ queryKey: ['services', tenantId] });
      await queryClient.invalidateQueries({ queryKey: ['services-overview', tenantId] });
      onClose();
      setForm({
        customer_name: '', label: '', router_id: '', kind: 'pppoe', package_name: '',
        start_date: '', contact: '', address: '', ip: '', mac: '', odp: '',
      });
      if (res.state.startsWith('job:')) {
        toast(t('customers.created_with_job'), 'success');
        navigate(`/app/${tenantId}/jobs/${res.state.slice(4)}`);
      } else {
        toast(t('customers.created_draft'), 'success');
      }
    } catch (err) {
      const e = err as { envelope?: { field_errors?: Record<string, Array<{ message: string }>>; message?: string } };
      const fe = e.envelope?.field_errors;
      if (fe) {
        const mapped: Record<string, string | undefined> = {};
        for (const [k, v] of Object.entries(fe)) mapped[k] = v[0]?.message;
        setErrors(mapped);
        setFormError(t('validation.summary'));
      } else {
        setFormError(e.envelope?.message ?? t('common.error_generic'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t('customers.add_title')}
      width={640}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" onClick={submit} loading={saving}>
            {t(`customers.choice_${choice}_cta` as never, undefined as never)}
          </Button>
        </>
      }
    >
      <div className="mt-stack">
        {formError ? (
          <p className="mt-banner mt-banner-danger" role="alert">
            <Icon name="alertCircle" size={18} /> {formError}
          </p>
        ) : null}
        <div className="mt-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <TextInput
            label={t('customers.f_name')}
            value={form.customer_name}
            onChange={set('customer_name')}
            error={errors.customer_name}
            required
          />
          <TextInput
            label={t('customers.f_label')}
            value={form.label}
            onChange={set('label')}
            helper={t('customers.f_label_helper')}
          />
        </div>
        <div className="mt-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <SelectInput
            label={t('customers.f_router')}
            options={routers}
            value={form.router_id}
            placeholderOption={t('common.not_set')}
            onChange={set('router_id')}
            helper={t('customers.f_router_helper')}
          />
          <SelectInput
            label={t('customers.f_kind')}
            options={[
              { value: 'pppoe', label: 'PPPoE' },
              { value: 'hotspot', label: 'Hotspot' },
            ]}
            value={form.kind}
            onChange={set('kind')}
          />
        </div>
        <div className="mt-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <TextInput
            label={t('customers.f_package')}
            value={form.package_name}
            onChange={set('package_name')}
            helper={t('customers.f_package_helper')}
          />
          <TextInput
            label={t('customers.f_start_date')}
            type="date"
            value={form.start_date}
            onChange={set('start_date')}
          />
        </div>
        <TextInput
          label={t('customers.f_contact')}
          value={form.contact}
          onChange={set('contact')}
          helper={t('customers.f_contact_helper')}
        />

        <button
          type="button"
          className="mt-btn mt-btn-ghost mt-btn-sm"
          onClick={() => setAdvanced((v) => !v)}
          aria-expanded={advanced}
        >
          <Icon name="chevronDown" size={16} style={{ transform: advanced ? 'rotate(180deg)' : 'none', transition: 'transform var(--mt-motion-fast) var(--mt-ease)' }} />
          {t('customers.advanced_toggle')}
        </button>

        {advanced ? (
          <div className="mt-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <TextInput label={t('customers.f_address')} value={form.address} onChange={set('address')} />
            <TextInput
              label={t('customers.f_ip')}
              value={form.ip}
              onChange={set('ip')}
              placeholder="192.0.2.2/24"
              error={errors.ip}
              helper={t('customers.f_ip_helper')}
            />
            <TextInput label={t('customers.f_mac')} value={form.mac} onChange={set('mac')} />
            <TextInput label={t('customers.f_odp')} value={form.odp} onChange={set('odp')} />
          </div>
        ) : null}

        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="mt-label" style={{ marginBottom: 'var(--mt-space-2)' }}>
            {t('customers.final_choice_label')}
          </legend>
          <div className="mt-stack-sm">
            {FINAL_CHOICES.map((c) => (
              <Checkbox
                key={c.value}
                type="radio"
                name="final-choice"
                checked={choice === c.value}
                onChange={() => setChoice(c.value)}
                label={
                  <span className="mt-small" style={{ fontWeight: 500 }}>
                    {t(`customers.choice_${c.value}` as never, undefined as never)}
                  </span>
                }
                hint={<span className="mt-xs mt-muted">{t(`customers.choice_${c.value}_impact` as never, undefined as never)}</span>}
              />
            ))}
          </div>
          <p className="mt-xs mt-muted" style={{ marginTop: 'var(--mt-space-2)' }}>
            {t('customers.final_choice_note')}
          </p>
        </fieldset>
      </div>
    </Dialog>
  );
}
