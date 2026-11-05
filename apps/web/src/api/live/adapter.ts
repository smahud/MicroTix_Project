/**
 * ADAPTER LIVE — klien HTTP ke backend same-origin /api/v1 (TK-104).
 *
 * Mengimplementasikan ApiClient typed memakai http.ts:
 * - Cookie sesi HttpOnly dikirim otomatis (credentials same-origin).
 * - CSRF: token dibaca dari cookie mtx_csrf (di-set oleh GET /auth/session)
 *   dan dikirim sebagai header x-csrf-token pada setiap mutasi.
 * - Idempotency-Key dibuat sekali per aksi mutasi (crypto.randomUUID).
 * - Endpoint domain fase M2+ (belum dibangun backend-nya) menghasilkan
 *   ApiError code 'not_found' dari backend — diteruskan apa adanya agar UI
 *   menampilkan status "belum tersedia", bukan data palsu.
 */
import type {
  ApiClient,
  AuthContextShape,
  CsvImportDraft,
  EnrollmentProgress,
  JobAccepted,
  MigrationDraftState,
  RouterEnrollmentDraft,
  ServiceListFilters,
} from '../client';
import type {
  AuditEntry,
  BackupArtifact,
  BackupSchedule,
  BootstrapScript,
  CsvValidationResult,
  CursorPage,
  DiscoveredAccount,
  IdentityConflictCandidate,
  JobRecord,
  MonitorStatus,
  PlanInfo,
  PlatformPaymentSubmission,
  RadiusAccountRow,
  RadiusRouterStatus,
  RevealCredentialResult,
  RouterDetail,
  RouterSummary,
  ServiceDetail,
  ServiceRow,
  SubscriptionInfo,
  TenantSummary,
} from '../contracts';
import type { MutationOptions, PageParams } from '../http';
import type { Locale } from '../../i18n';
import { http, pageQuery } from '../http';

function csrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const match = document.cookie.match(/(?:^|;\s*)mtx_csrf=([^;]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : undefined;
}

function opts(): MutationOptions {
  return { csrfToken: csrfToken() };
}

function withIdem(existing?: MutationOptions): MutationOptions {
  return {
    ...existing,
    csrfToken: existing?.csrfToken ?? csrfToken(),
    idempotencyKey: existing?.idempotencyKey ?? crypto.randomUUID(),
  };
}

export class LiveApiClient implements ApiClient {
  /* ---- Meta & enums ---- */
  async getEnums(locale: Locale): Promise<Record<string, Record<string, string>>> {
    return http.get<Record<string, Record<string, string>>>('/meta/enums', { locale });
  }

  /* ---- Sesi ---- */
  async login(email: string, password: string): Promise<{ requires_totp: boolean }> {
    return http.post<{ requires_totp: boolean }>('/auth/login', { email, password }, opts());
  }
  async loginTotp(code: string): Promise<AuthContextShape> {
    return http.post<AuthContextShape>('/auth/login-totp', { code }, opts());
  }
  async register(input: {
    full_name: string;
    email: string;
    password: string;
    company_name: string;
  }): Promise<{ verification_sent: true }> {
    return http.post<{ verification_sent: true }>('/auth/register', input, opts());
  }
  async verifyEmail(token: string): Promise<AuthContextShape> {
    return http.post<AuthContextShape>('/auth/verify-email', { token }, opts());
  }
  async requestPasswordReset(email: string): Promise<void> {
    return http.post<void>('/auth/recover', { email }, opts());
  }
  async getSession(): Promise<AuthContextShape> {
    return http.get<AuthContextShape>('/auth/session');
  }
  async logout(): Promise<void> {
    return http.post<void>('/auth/logout', undefined, opts());
  }
  async reauthenticate(password: string, totp_code: string): Promise<{ valid_until: string }> {
    return http.post<{ valid_until: string }>('/auth/reauthenticate', { password, totp_code }, opts());
  }

  /* ---- Tenant ---- */
  async getTenants() {
    return http.get<TenantSummary[]>('/auth/tenants');
  }
  async switchTenant(tenantId: string): Promise<AuthContextShape> {
    return http.post<AuthContextShape>(`/auth/tenants/${tenantId}/switch`, undefined, opts());
  }

  /* ---- Services (M4 — backend belum aktif) ---- */
  async listServices(tenantId: string, _filters: ServiceListFilters, page: PageParams) {
    return http.get<CursorPage<ServiceRow>>(`/tenants/${tenantId}/services`, pageQuery(page));
  }
  async getService(tenantId: string, serviceId: string) {
    return http.get<ServiceDetail>(`/tenants/${tenantId}/services/${serviceId}`);
  }
  async createServiceDraft(tenantId: string, input: Record<string, unknown>, o?: MutationOptions) {
    return http.post<{ id: string; state: string }>(`/tenants/${tenantId}/services`, input, withIdem(o));
  }
  async revealCredential(tenantId: string, serviceId: string, o?: MutationOptions) {
    return http.post<RevealCredentialResult>(`/tenants/${tenantId}/services/${serviceId}/reveal-credentials`, undefined, withIdem(o));
  }

  /* ---- Router enrollment (M3 — backend belum aktif) ---- */
  async createEnrollment(tenantId: string, input: object, o?: MutationOptions): Promise<RouterEnrollmentDraft> {
    return http.post<RouterEnrollmentDraft>(`/tenants/${tenantId}/router-enrollments`, input, withIdem(o));
  }
  async getEnrollment(tenantId: string, enrollmentId: string): Promise<EnrollmentProgress> {
    return http.get<EnrollmentProgress>(`/tenants/${tenantId}/router-enrollments/${enrollmentId}`);
  }
  async getBootstrapScript(tenantId: string, enrollmentId: string) {
    return http.get<BootstrapScript>(`/tenants/${tenantId}/router-enrollments/${enrollmentId}/bootstrap`);
  }

  /* ---- Routers (registri R1 tersedia; mutasi M3) ---- */
  async listRouters(tenantId: string) {
    return http.get<RouterSummary[]>(`/tenants/${tenantId}/routers`);
  }
  async getRouter(tenantId: string, routerId: string) {
    return http.get<RouterDetail>(`/tenants/${tenantId}/routers/${routerId}`);
  }
  async releaseRouter(tenantId: string, routerId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/routers/${routerId}/release`, undefined, withIdem(o));
  }
  async replaceRouter(tenantId: string, routerId: string, newRouterName: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/routers/${routerId}/replace`, { display_name: newRouterName }, withIdem(o));
  }

  async startDiscovery(tenantId: string, routerId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/routers/${routerId}/discoveries`, undefined, withIdem(o));
  }

  /* ---- Migration wizard U07 (M4) ---- */
  async startMigration(tenantId: string, routerId: string, o?: MutationOptions): Promise<{ migration_id: string }> {
    return http.post<{ migration_id: string }>(`/tenants/${tenantId}/routers/${routerId}/migrations`, undefined, withIdem(o));
  }
  async listDiscoveredAccounts(tenantId: string, migrationId: string, page: PageParams) {
    return http.get<CursorPage<DiscoveredAccount>>(`/tenants/${tenantId}/migrations/${migrationId}/accounts`, pageQuery(page));
  }
  async getIdentityConflicts(tenantId: string, migrationId: string) {
    return http.get<IdentityConflictCandidate[]>(`/tenants/${tenantId}/migrations/${migrationId}/identity-conflicts`);
  }
  async resolveIdentityConflict(
    tenantId: string,
    migrationId: string,
    groupId: string,
    resolution: 'merge' | 'keep_one' | 'rename',
    o?: MutationOptions,
  ): Promise<void> {
    return http.post<void>(`/tenants/${tenantId}/migrations/${migrationId}/identity-conflicts/${groupId}`, { resolution }, withIdem(o));
  }
  async saveMigrationDraft(_tenantId: string, state: MigrationDraftState): Promise<void> {
    // Draft U07 dipertahankan lokal sampai backend M4 aktif (terdokumentasi di progress.md).
    localStorage.setItem(`mt-migration-draft-${state.id}`, JSON.stringify(state));
  }
  async getMigrationDraft(_tenantId: string, _routerId: string): Promise<MigrationDraftState | null> {
    const keys = Object.keys(localStorage).filter((k) => k.startsWith('mt-migration-draft-'));
    const first = keys[0];
    if (!first) return null;
    const raw = localStorage.getItem(first);
    return raw ? (JSON.parse(raw) as MigrationDraftState) : null;
  }
  async requestPasswordHarvest(tenantId: string, routerId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/routers/${routerId}/password-harvest`, undefined, withIdem(o));
  }
  async commitMigration(tenantId: string, migrationId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/migrations/${migrationId}/commit`, undefined, withIdem(o));
  }

  /* ---- CSV import U08 (M4) ---- */
  async createCsvImport(tenantId: string, input: object, o?: MutationOptions): Promise<CsvImportDraft> {
    return http.post<CsvImportDraft>(`/tenants/${tenantId}/imports`, input, withIdem(o));
  }
  async validateCsvImport(tenantId: string, importId: string, o?: MutationOptions) {
    return http.post<CsvValidationResult>(`/tenants/${tenantId}/imports/${importId}/validate`, undefined, withIdem(o));
  }
  async commitCsvImport(tenantId: string, importId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/imports/${importId}/commit`, undefined, withIdem(o));
  }

  /* ---- Jobs U16 (backend aktif M1) ---- */
  async listJobs(tenantId: string, page: PageParams) {
    return http.get<CursorPage<JobRecord>>(`/tenants/${tenantId}/jobs`, pageQuery(page));
  }
  async getJob(_tenantId: string, jobId: string) {
    return http.get<JobRecord>(`/jobs/${jobId}`);
  }
  async retryJob(_tenantId: string, jobId: string, o?: MutationOptions): Promise<JobAccepted | null> {
    return http.post<JobAccepted | null>(`/jobs/${jobId}/retry`, undefined, withIdem(o));
  }
  async cancelJob(_tenantId: string, jobId: string, reason: string, o?: MutationOptions): Promise<void> {
    return http.post<void>(`/jobs/${jobId}/cancel`, { reason }, withIdem(o));
  }

  /* ---- Backups U12 (M5) ---- */
  async listBackupArtifacts(tenantId: string, routerId: string | null) {
    return http.get<BackupArtifact[]>(`/tenants/${tenantId}/backups`, routerId ? { router_id: routerId } : undefined);
  }
  async listBackupSchedules(tenantId: string) {
    return http.get<BackupSchedule[]>(`/tenants/${tenantId}/backup-schedules`);
  }
  async runBackupNow(tenantId: string, routerId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/routers/${routerId}/backups`, undefined, withIdem(o));
  }

  /* ---- Monitoring U13 (M5) ---- */
  async listMonitorStatus(tenantId: string) {
    return http.get<MonitorStatus[]>(`/tenants/${tenantId}/monitor`);
  }

  /* ---- RADIUS U19 (M3/M5) ---- */
  async listRadiusAccounts(tenantId: string, filters: { query?: string; state?: string }, page: PageParams) {
    return http.get<CursorPage<RadiusAccountRow>>(`/tenants/${tenantId}/access-accounts`, { ...filters, ...pageQuery(page) });
  }
  async listRadiusRouterStatus(tenantId: string) {
    return http.get<RadiusRouterStatus[]>(`/tenants/${tenantId}/radius-status`);
  }
  async getRadiusRouterStatus(tenantId: string, routerId: string) {
    return http.get<RadiusRouterStatus>(`/tenants/${tenantId}/radius-status/${routerId}`);
  }
  async startRadiusCutover(tenantId: string, routerId: string, o?: MutationOptions): Promise<JobAccepted> {
    return http.post<JobAccepted>(`/tenants/${tenantId}/routers/${routerId}/radius-cutover`, undefined, withIdem(o));
  }
  async suspendRadiusAccount(tenantId: string, accountId: string, o?: MutationOptions): Promise<void> {
    return http.patch<void>(`/tenants/${tenantId}/access-accounts/${accountId}`, { state: 'suspended' }, withIdem(o));
  }
  async activateRadiusAccount(tenantId: string, accountId: string, o?: MutationOptions): Promise<void> {
    return http.patch<void>(`/tenants/${tenantId}/access-accounts/${accountId}`, { state: 'active' }, withIdem(o));
  }

  /* ---- Subscription (backend aktif M1) ---- */
  async getSubscription(tenantId: string) {
    return http.get<SubscriptionInfo>(`/tenants/${tenantId}/subscription`);
  }
  async getPlans() {
    return http.get<PlanInfo[]>('/plans');
  }
  async requestQuotation(tenantId: string, planCode: string, term: 'monthly' | 'yearly', o?: MutationOptions) {
    return http.post<{ quotation_id: string; invoice_id: string; amount: string }>(`/tenants/${tenantId}/quotations`, { plan_code: planCode, term }, withIdem(o));
  }
  async submitPaymentProof(tenantId: string, invoiceId: string, input: object, o?: MutationOptions) {
    return http.post<{ submission_id: string; state: string }>(`/tenants/${tenantId}/saas-invoices/${invoiceId}/payment-submissions`, input, withIdem(o));
  }

  /* ---- Platform admin U14 (M2) ---- */
  async listPlatformSubmissions(queue: string) {
    return http.get<PlatformPaymentSubmission[]>('/platform/payment-submissions', { queue });
  }
  async approvePlatformSubmission(submissionId: string, o?: MutationOptions): Promise<void> {
    return http.post<void>(`/platform/payment-submissions/${submissionId}/approve`, undefined, withIdem(o));
  }
  async rejectPlatformSubmission(submissionId: string, reason: string, o?: MutationOptions): Promise<void> {
    return http.post<void>(`/platform/payment-submissions/${submissionId}/reject`, { reason }, withIdem(o));
  }
  async requestRevisionPlatformSubmission(submissionId: string, reason: string, o?: MutationOptions): Promise<void> {
    return http.post<void>(`/platform/payment-submissions/${submissionId}/request-revision`, { reason }, withIdem(o));
  }

  /* ---- Audit timeline (backend aktif M1) ---- */
  async listAuditTimeline(tenantId: string, targetId: string | null, page: PageParams) {
    return http.get<CursorPage<AuditEntry>>(`/tenants/${tenantId}/audit-timeline`, { target_id: targetId ?? undefined, ...pageQuery(page) });
  }
}
