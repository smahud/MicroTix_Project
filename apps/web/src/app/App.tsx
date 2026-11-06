import { lazy, Suspense } from 'react';
import type { ReactNode } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import { useSession } from '../state/session';
import { Skeleton } from '../design-system/primitives/Misc';
import { useT } from '../i18n/useT';

const Landing = lazy(() => import('../features/landing/Landing'));
const LoginPage = lazy(() => import('../features/auth/LoginPage'));
const RegisterPage = lazy(() => import('../features/auth/RegisterPage'));
const VerifyPage = lazy(() => import('../features/auth/VerifyPage'));
const RecoverPage = lazy(() => import('../features/auth/RecoverPage'));
const OverviewPage = lazy(() => import('../features/overview/OverviewPage'));
const CustomersPage = lazy(() => import('../features/customers/CustomersPage'));
const CustomerDetailPage = lazy(() => import('../features/customers/CustomerDetailPage'));
const RouterNewPage = lazy(() => import('../features/routers/RouterNewPage'));
const RouterDetailPage = lazy(() => import('../features/routers/RouterDetailPage'));
const RoutersListPage = lazy(() => import('../features/routers/RoutersListPage'));
const ImportRouterPage = lazy(() => import('../features/imports/ImportRouterPage'));
const ImportCsvPage = lazy(() => import('../features/imports/ImportCsvPage'));
const BackupsPage = lazy(() => import('../features/backups/BackupsPage'));
const MonitoringPage = lazy(() => import('../features/monitoring/MonitoringPage'));
const JobsPage = lazy(() => import('../features/jobs/JobsPage'));
const JobDetailPage = lazy(() => import('../features/jobs/JobDetailPage'));
const SettingsPage = lazy(() => import('../features/settings/SettingsPage'));
const RadiusPage = lazy(() => import('../features/radius/RadiusPage'));
const AdminSubscriptionsPage = lazy(() => import('../features/admin/AdminSubscriptionsPage'));
const PackagesPage = lazy(() => import('../features/settings/PackagesPage'));
const BillingPage = lazy(() => import('../features/billing/BillingPage'));
const ActivationPage = lazy(() => import('../features/activation/ActivationPage'));

function PageFallback(): ReactNode {
  return (
    <div className="mt-stack" style={{ padding: 'var(--mt-space-4)' }}>
      <Skeleton w={240} h={28} />
      <Skeleton w="60%" h={16} />
      <Skeleton w="100%" h={120} />
      <Skeleton w="100%" h={220} />
    </div>
  );
}

/** Guard sesi untuk ruang /app. */
function RequireAuth({ children }: { children: ReactNode }): ReactNode {
  const { ctx, loading } = useSession();
  if (loading) return <PageFallback />;
  if (!ctx?.user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function TenantRoute({ children }: { children: (tenantId: string) => ReactNode }): ReactNode {
  const { tenantId } = useParams<{ tenantId: string }>();
  const { ctx, loading } = useSession();
  if (loading) return <PageFallback />;
  if (!ctx?.user || !tenantId) return <Navigate to="/login" replace />;
  const member = ctx.tenants.find((t) => t.id === tenantId);
  if (!member) {
    // Tenant asing → 404 generik, tanpa membocorkan isi (AC-TEN)
    return <Navigate to="/not-found" replace />;
  }
  return <>{children(tenantId)}</>;
}

/** `/app` → beranda tenant aktif (setelah login). */
function AppIndexRedirect(): ReactNode {
  const { ctx, loading } = useSession();
  if (loading) return <PageFallback />;
  if (!ctx?.user || !ctx.active_tenant_id) return <Navigate to="/login" replace />;
  return <Navigate to={`/app/${ctx.active_tenant_id}/overview`} replace />;
}

function NotFoundPage(): ReactNode {
  const t = useT();
  return (
    <main className="mt-content" style={{ maxWidth: 640, paddingTop: 'var(--mt-space-8)' }}>
      <div className="mt-card mt-card-pad">
        <h1>404</h1>
        <p className="mt-muted">{t('common.not_found')}</p>
      </div>
    </main>
  );
}

export function App(): ReactNode {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify" element={<VerifyPage />} />
        <Route path="/recover" element={<RecoverPage />} />
        <Route path="/app" element={<AppIndexRedirect />} />

        <Route
          path="/app/:tenantId/*"
          element={
            <RequireAuth>
              <Routes>
                <Route
                  path="overview"
                  element={
                    <TenantRoute>{(tid) => <OverviewPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="customers"
                  element={
                    <TenantRoute>{(tid) => <CustomersPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="customers/:serviceId"
                  element={
                    <TenantRoute>{(tid) => <CustomerDetailPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="routers"
                  element={
                    <TenantRoute>{(tid) => <RoutersListPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="routers/new"
                  element={
                    <TenantRoute>{(tid) => <RouterNewPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="routers/:routerId"
                  element={
                    <TenantRoute>{(tid) => <RouterDetailPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="imports/router"
                  element={
                    <TenantRoute>{(tid) => <ImportRouterPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="imports/csv"
                  element={
                    <TenantRoute>{(tid) => <ImportCsvPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="backups"
                  element={
                    <TenantRoute>{(tid) => <BackupsPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="monitoring"
                  element={
                    <TenantRoute>{(tid) => <MonitoringPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="jobs"
                  element={
                    <TenantRoute>{(tid) => <JobsPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="jobs/:jobId"
                  element={
                    <TenantRoute>{(tid) => <JobDetailPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="settings/*"
                  element={
                    <RequireAuth>
                      <SettingsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="radius"
                  element={
                    <TenantRoute>{(tid) => <RadiusPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="packages"
                  element={
                    <TenantRoute>{(tid) => <PackagesPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="billing"
                  element={
                    <TenantRoute>{(tid) => <BillingPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route
                  path="activation"
                  element={
                    <TenantRoute>{(tid) => <ActivationPage tenantId={tid} />}</TenantRoute>
                  }
                />
                <Route path="*" element={<Navigate to="overview" replace />} />
              </Routes>
            </RequireAuth>
          }
        />

        <Route
          path="/admin/subscriptions"
          element={
            <RequireAuth>
              <AdminSubscriptionsPage />
            </RequireAuth>
          }
        />

        <Route
          path="*"
          element={<NotFoundPage />}
        />
      </Routes>
    </Suspense>
  );
}
