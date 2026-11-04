import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { NavLink, Link, useLocation, useNavigate } from 'react-router-dom';
import { Icon } from '../primitives/Icon';
import { useT } from '../../i18n/useT';
import { useBranding } from '../../branding';
import { useSession } from '../../state/session';
import { useI18n, LANGUAGE_NAMES, LOCALES } from '../../i18n';
import type { Locale } from '../../i18n';
import { isReleased } from '../../permissions/release-flags';
import type { Permission } from '../../permissions/permissions';
import { useApiMode } from '../../api';
import { useToast } from '../primitives/Toast';

/* ================= TenantSwitcher ================= */

export function TenantSwitcher({ dark = false }: { dark?: boolean }) {
  const { ctx, switchTenant } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const t = useT();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const [dirty, setDirty] = useState(false);

  // Deteksi form belum tersimpan (unsaved state global via event custom sederhana)
  useEffect(() => {
    const onDirty = (e: Event) => setDirty((e as CustomEvent<boolean>).detail);
    window.addEventListener('mt:form-dirty', onDirty);
    return () => window.removeEventListener('mt:form-dirty', onDirty);
  }, []);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  if (!ctx) return null;
  const active = ctx.tenants.find((x) => x.id === ctx.active_tenant_id);
  if (!active) return null;

  const pick = async (tenantId: string, tenantName: string) => {
    console.log('[debug] pick called', tenantId, 'dirty=', dirty);
    if (dirty) {
      // Tenant switch dengan form belum tersimpan (UI_UX.md §1)
      const keep = window.confirm(t('tenant.switch_dirty_confirm'));
      if (!keep) {
        setDirty(false);
        return;
      }
    }
    setOpen(false);
    await switchTenant(tenantId);
    toast(t('tenant.switched_to', { name: tenantName }), 'success');
    // Pilihan checkbox tidak terbawa; kembali ke beranda tenant.
    navigate(`/app/${tenantId}/overview`);
    void location;
  };

  return (
    <div className="mt-tenant-switch" ref={ref}>
      <button
        type="button"
        className="mt-tenant-btn"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        style={dark ? { background: 'rgba(255,255,255,0.1)', borderColor: 'rgba(255,255,255,0.3)', color: '#fff' } : undefined}
      >
        <span className="mt-tenant-avatar" style={dark ? { background: 'rgba(255,255,255,0.18)', color: '#fff' } : undefined}>
          {active.display_name.slice(0, 2).toUpperCase()}
        </span>
        <span style={{ minWidth: 0, textAlign: 'left' }}>
          <span className="mt-tenant-btn-name" style={{ display: 'block', color: 'inherit' }}>
            {active.display_name}
          </span>
          <span className="mt-tenant-btn-role" style={{ display: 'block', color: dark ? 'rgba(255,255,255,0.75)' : undefined }}>
            {t(`role.${active.role}` as never, undefined as never)}
          </span>
        </span>
        <Icon name="chevronDown" size={16} style={{ flexShrink: 0 }} />
      </button>
      {open ? (
        <div className="mt-menu-panel" role="listbox" aria-label={t('tenant.switch_label')} style={{ left: 0, right: 'auto' }}>
          {ctx.tenants.map((x) => (
            <button
              key={x.id}
              type="button"
              role="option"
              aria-selected={x.id === active.id}
              className="mt-menu-item"
              onClick={() => pick(x.id, x.display_name)}
              style={x.id === active.id ? { background: 'var(--mt-primary-subtle)', color: 'var(--mt-primary)' } : undefined}
            >
              <Icon name="building" size={18} />
              <span style={{ minWidth: 0 }}>
                <span style={{ display: 'block' }}>{x.display_name}</span>
                <span className="mt-xs mt-muted">{t(`role.${x.role}` as never, undefined as never)}</span>
              </span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/* ================= Language switcher ================= */

export function LanguageSwitcher({ dark = false }: { dark?: boolean }) {
  const { locale, setLocale } = useI18n();
  return (
    <label className={`mt-lang-switch${dark ? ' mt-lang-switch--admin' : ''}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span className="mt-visually-hidden">Bahasa / Language</span>
      <Icon name="globe" size={16} style={{ color: dark ? 'rgba(255,255,255,0.8)' : 'var(--mt-text-secondary)' }} />
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        // Mengganti bahasa tidak menghapus isian formulir (hanya katalog)
      >
        {LOCALES.map((l) => (
          <option key={l} value={l}>
            {LANGUAGE_NAMES[l]}
          </option>
        ))}
      </select>
    </label>
  );
}

/* ================= Navigasi ================= */

interface NavEntry {
  to: string;
  labelKey: string;
  icon: string;
  permission?: Permission;
  release?: boolean;
}

const NAV_GROUPS: Array<{ labelKey: string; entries: NavEntry[] }> = [
  {
    labelKey: 'nav.group.operational',
    entries: [
      { to: 'overview', labelKey: 'nav.overview', icon: 'home' },
      { to: 'customers', labelKey: 'nav.customers', icon: 'users', permission: 'customers.read' },
      { to: 'packages', labelKey: 'nav.packages', icon: 'layers', permission: 'customers.read' },
      { to: 'billing', labelKey: 'nav.billing', icon: 'wallet', permission: 'payments.verify', release: isReleased('billing') },
      { to: 'incidents', labelKey: 'nav.incidents', icon: 'alertTriangle', release: isReleased('fieldops') },
      { to: 'jobs', labelKey: 'nav.jobs', icon: 'list' },
    ],
  },
  {
    labelKey: 'nav.group.network',
    entries: [
      { to: 'routers', labelKey: 'nav.routers', icon: 'router', permission: 'routers.read' },
      { to: 'radius', labelKey: 'nav.radius', icon: 'shield', permission: 'routers.read' },
      { to: 'backups', labelKey: 'nav.backups', icon: 'database', permission: 'backups.run' },
      { to: 'devices', labelKey: 'nav.devices', icon: 'device', permission: 'devices.manage', release: isReleased('devices') },
      { to: 'inventory', labelKey: 'nav.inventory', icon: 'mapPin', release: isReleased('fieldops') },
      { to: 'configuration', labelKey: 'nav.configuration', icon: 'settings', permission: 'routers.configure', release: isReleased('configuration') },
    ],
  },
  {
    labelKey: 'nav.group.finance',
    entries: [
      { to: 'finance', labelKey: 'nav.finance', icon: 'trendingUp', permission: 'ledger.post', release: isReleased('finance') },
    ],
  },
  {
    labelKey: 'nav.group.company',
    entries: [
      { to: 'settings/team', labelKey: 'nav.team', icon: 'building', permission: 'team.manage' },
      { to: 'settings/subscription', labelKey: 'nav.subscription', icon: 'zap', permission: 'subscription.manage' },
    ],
  },
];

function SidebarNav({ tenantId }: { tenantId: string }) {
  const t = useT();
  const { can } = useSession();
  return (
    <nav className="mt-nav" aria-label={t('nav.main_nav')}>
      {NAV_GROUPS.map((g) => {
        const visible = g.entries.filter((e) => e.release !== false && (!e.permission || can(e.permission)));
        if (visible.length === 0) return null;
        return (
          <div key={g.labelKey}>
            <div className="mt-nav-group-label">{t(g.labelKey as never, undefined as never)}</div>
            {visible.map((e) => (
              <NavLink
                key={e.to}
                to={`/app/${tenantId}/${e.to}`}
                className="mt-nav-item"
              >
                <span className="mt-nav-item-icon">
                  <Icon name={e.icon} size={19} />
                </span>
                <span>{t(e.labelKey as never, undefined as never)}</span>
              </NavLink>
            ))}
          </div>
        );
      })}
      <div className="mt-nav-group-label" style={{ marginTop: 'var(--mt-space-3)' }}>
        {t('nav.group.help')}
      </div>
      <a className="mt-nav-item" href="#help">
        <span className="mt-nav-item-icon">
          <Icon name="helpCircle" size={19} />
        </span>
        <span>{t('nav.help')}</span>
      </a>
    </nav>
  );
}

/* ================= User menu ================= */

function UserMenu({ dark = false }: { dark?: boolean }) {
  const { ctx, logout } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const t = useT();
  const navigate = useNavigate();
  const darkStyle = dark ? { color: '#fff' } : undefined;
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);
  if (!ctx?.user) return null;
  return (
    <div className="mt-menu" ref={ref}>
      <button
        type="button"
        className="mt-btn mt-btn-ghost mt-btn-icon"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        aria-label={t('app.user_menu')}
        style={darkStyle}
      >
        <Icon name="user" size={20} />
      </button>
      {open ? (
        <div className="mt-menu-panel" role="menu">
          <div className="mt-menu-label">{ctx.user.email}</div>
          <Link to="/" className="mt-menu-item" role="menuitem" onClick={() => setOpen(false)}>
            <Icon name="globe" size={18} /> {t('app.back_to_landing')}
          </Link>
          <button
            type="button"
            role="menuitem"
            className="mt-menu-item mt-menu-item-danger"
            onClick={async () => {
              setOpen(false);
              await logout();
              navigate('/login');
            }}
          >
            <Icon name="logout" size={18} /> {t('app.logout')}
          </button>
        </div>
      ) : null}
    </div>
  );
}

/* ================= AppShell ================= */

export function AppShell({
  tenantId,
  children,
  title,
}: {
  tenantId: string;
  children: ReactNode;
  title?: ReactNode;
}) {
  const t = useT();
  const branding = useBranding();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const apiMode = useApiMode();

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  return (
    <div className="mt-shell">
      <a href="#mt-main-content" className="mt-skip-link">
        {t('app.skip_to_content')}
      </a>
      <aside className="mt-sidebar">
        <div className="mt-sidebar-brand">
          <span className="mt-brand-mark" aria-hidden="true">
            M
          </span>
          <span>
            <span className="mt-brand-name">{branding.display_name}</span>
            <span className="mt-brand-sub" style={{ display: 'block' }}>
              {t('app.brand_sub')}
            </span>
          </span>
        </div>
        <SidebarNav tenantId={tenantId} />
      </aside>

      <div className="mt-main">
        {apiMode === 'mock' ? <DevMockBanner /> : null}
        <header className="mt-header">
          <button
            type="button"
            className="mt-btn mt-btn-ghost mt-btn-icon mt-mobiletop"
            aria-label={t('app.open_menu')}
            onClick={() => setDrawerOpen(true)}
          >
            <Icon name="menu" size={20} />
          </button>
          <span className="mt-header-title">{title}</span>
          <span style={{ flex: 1 }} />
          <LanguageSwitcher />
          <TenantSwitcher />
          <UserMenu />
        </header>
        <main className="mt-content" id="mt-main-content" tabIndex={-1}>
          {children}
        </main>
      </div>

      {drawerOpen ? (
        <div className="mt-mobile-drawer" role="dialog" aria-modal="true" aria-label={t('nav.main_nav')}>
          <div className="mt-mobile-drawer-backdrop" onClick={() => setDrawerOpen(false)} />
          <div className="mt-mobile-drawer-panel">
            <div className="mt-sidebar-brand">
              <span className="mt-brand-mark" aria-hidden="true">
                M
              </span>
              <span className="mt-brand-name">{branding.display_name}</span>
              <span style={{ flex: 1 }} />
              <button type="button" className="mt-btn mt-btn-ghost mt-btn-icon" onClick={() => setDrawerOpen(false)}>
                <Icon name="x" size={18} />
                <span className="mt-visually-hidden">{t('common.close_panel')}</span>
              </button>
            </div>
            <SidebarNav tenantId={tenantId} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Banner mode data pengembangan — pembeda jelas demo data dari data produksi
 * (master prompt §10). Hanya tampil saat adapter mock aktif.
 */
function DevMockBanner() {
  const t = useT();
  return (
    <div className="mt-devbanner" role="note">
      <Icon name="info" size={14} />
      {t('app.dev_mock_banner')}
    </div>
  );
}

/* ================= AdminShell (ruang /admin — header navy) ================= */

export function AdminShell({ children, title }: { children: ReactNode; title?: ReactNode }) {
  const t = useT();
  const branding = useBranding();
  const { ctx } = useSession();
  const navigate = useNavigate();
  const apiMode = useApiMode();

  if (ctx && ctx.user && !ctx.user.platform_admin) {
    return (
      <div className="mt-shell">
        <main className="mt-content" style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--mt-space-8) var(--mt-space-4)' }}>
          <div className="mt-banner mt-banner-warning">
            <Icon name="lock" size={20} />
            <span>{t('permission.admin_only')}</span>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="mt-shell" style={{ flexDirection: 'column' }}>
      <a href="#mt-main-content" className="mt-skip-link">
        {t('app.skip_to_content')}
      </a>
      {apiMode === 'mock' ? <DevMockBanner /> : null}
      <header className="mt-header mt-header-admin">
        <span className="mt-brand-mark" aria-hidden="true" style={{ background: 'rgba(255,255,255,0.16)' }}>
          M
        </span>
        <span className="mt-header-title">{branding.display_name}</span>
        <span className="mt-admin-tag">
          <Icon name="shield" size={12} /> {t('admin.workspace_label')}
        </span>
        <span style={{ flex: 1 }} />
        <LanguageSwitcher dark />
        <button type="button" className="mt-btn mt-btn-ghost mt-btn-sm mt-admin-back" onClick={() => navigate('/')}>
          <Icon name="arrowLeft" size={16} /> <span>{t('admin.back_to_tenant')}</span>
        </button>
        <UserMenu dark />
      </header>
      {title ? (
        <div style={{ padding: 'var(--mt-space-4) var(--mt-space-4) 0', maxWidth: 'var(--mt-content-max)', width: '100%', margin: '0 auto' }}>
          {title}
        </div>
      ) : null}
      <main className="mt-content" id="mt-main-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
