import type {
  AuditEntry,
  BackupArtifact,
  BackupSchedule,
  BootstrapScript,
  CsvImportMode,
  CsvValidationResult,
  CursorPage,
  DiscoveredAccount,
  IdentityConflictCandidate,
  JobRecord,
  MigrationSummaryCounts,
  MonitorStatus,
  PasswordSource,
  PlanInfo,
  PlatformPaymentSubmission,
  RadiusAccountRow,
  RadiusRouterStatus,
  RevealCredentialResult,
  RouterDetail,
  RouterEnrollmentRequest,
  RouterSummary,
  ServiceDetail,
  ServiceRow,
  SessionUser,
  SubscriptionInfo,
  TenantSummary,
} from './contracts';
import type { PageParams, MutationOptions } from './http';
import type { Permission } from '../permissions/permissions';
import type { Locale } from '../i18n';

/**
 * Batas integrasi typed. Endpoint yang tercantum pada ARCHITECTURE.md §5
 * mengikuti kontrak persis; endpoint PENDING_BACKEND menunggu konfirmasi
 * OpenAPI backend (mock adapter mengimplementasikannya untuk development).
 */
export interface ServiceListFilters {
  router_id?: string;
  query?: string;
  connection?: 'online' | 'offline' | 'unknown';
  payment?: 'unbilled' | 'partial' | 'paid' | 'not_billed';
  isolation?: 'normal' | 'isolated' | 'awaiting_verification' | 'hold';
  job?: 'none' | 'queued' | 'running' | 'needs_review';
  incomplete_mapping?: boolean;
  quick_tab?: 'all' | 'unpaid' | 'paid_awaiting_activation' | 'isolated' | 'incomplete';
}

export interface RouterEnrollmentDraft {
  id: string;
  request: RouterEnrollmentRequest;
  state: 'draft' | 'enrollment_issued' | 'bootstrap_pending' | 'tunnel_seen' | 'api_verified' | 'discovery_ready';
}

export interface JobAccepted {
  job_id: string;
  status_url: string;
}

export interface MigrationDraftState {
  id: string;
  step: number; // 0..7 dari 8 langkah (UI_UX.md §6)
  selected_account_ids: string[];
  identity_resolutions: Record<string, 'merge' | 'keep_one' | 'rename'>;
  profile_package_map: Record<string, string>;
  password_source: PasswordSource | null;
  counts: MigrationSummaryCounts | null;
}

export interface CsvImportDraft {
  id: string;
  mode: CsvImportMode;
  file_name: string;
  total_rows: number;
  validation: CsvValidationResult | null;
  /** Baris tersimpan adapter dev; backend menyimpan berkas terunggah. */
  rows?: Record<string, string>[];
}

export interface AuthContextShape {
  user: SessionUser | null;
  tenants: TenantSummary[];
  active_tenant_id: string | null;
  permissions: Permission[];
  sensitive_reauth_until: string | null;
}

export interface EnrollmentProgress {
  enrollment_id: string;
  state: 'bootstrap_pending' | 'tunnel_seen' | 'api_verified' | 'discovery_ready' | 'conflict' | 'expired';
  stage_detail: Array<{ code: string; state: 'pending' | 'ok' | 'failed' }>;
}

export interface ApiClient {
  /* ---- Meta & enums (dokumentasi: GET /meta/enums?locale=id) ---- */
  getEnums(locale: Locale): Promise<Record<string, Record<string, string>>>;

  /* ---- Sesi (PENDING_BACKEND: endpoint auth belum didokumentasikan §5) ---- */
  login(email: string, password: string): Promise<{ requires_totp: boolean }>;
  loginTotp(code: string): Promise<AuthContextShape>;
  register(input: {
    full_name: string;
    email: string;
    password: string;
    company_name: string;
  }): Promise<{ verification_sent: true }>;
  verifyEmail(token: string): Promise<AuthContextShape>;
  requestPasswordReset(email: string): Promise<void>;
  getSession(): Promise<AuthContextShape>;
  logout(): Promise<void>;
  /** Reauth "Konfirmasi identitas Anda" (password+TOTP), berlaku 600 detik. */
  reauthenticate(password: string, totp_code: string): Promise<{ valid_until: string }>;

  /* ---- Tenant ---- */
  getTenants(): Promise<TenantSummary[]>;
  switchTenant(tenantId: string): Promise<AuthContextShape>;

  /* ---- Services (dok: GET /tenants/{t}/services) ---- */
  listServices(
    tenantId: string,
    filters: ServiceListFilters,
    page: PageParams,
  ): Promise<CursorPage<ServiceRow>>;
  getService(tenantId: string, serviceId: string): Promise<ServiceDetail>;
  createServiceDraft(
    tenantId: string,
    input: Record<string, unknown>,
    opts?: MutationOptions,
  ): Promise<{ id: string; state: string }>;
  revealCredential(
    tenantId: string,
    serviceId: string,
    opts?: MutationOptions,
  ): Promise<RevealCredentialResult>;

  /* ---- Router enrollment (dok: POST /tenants/{t}/router-enrollments) ---- */
  createEnrollment(
    tenantId: string,
    input: RouterEnrollmentRequest,
    opts?: MutationOptions,
  ): Promise<RouterEnrollmentDraft>;
  getEnrollment(tenantId: string, enrollmentId: string): Promise<EnrollmentProgress>;
  getBootstrapScript(tenantId: string, enrollmentId: string): Promise<BootstrapScript>;

  /* ---- Routers (PENDING_BACKEND: list/detail routers) ---- */
  listRouters(tenantId: string): Promise<RouterSummary[]>;
  getRouter(tenantId: string, routerId: string): Promise<RouterDetail>;
  releaseRouter(tenantId: string, routerId: string, opts?: MutationOptions): Promise<JobAccepted>;
  replaceRouter(
    tenantId: string,
    routerId: string,
    newRouterName: string,
    opts?: MutationOptions,
  ): Promise<JobAccepted>;

  /* ---- Discovery (dok: POST /routers/{id}/discoveries → 202) ---- */
  startDiscovery(tenantId: string, routerId: string, opts?: MutationOptions): Promise<JobAccepted>;

  /* ---- Migration wizard U07 ---- */
  startMigration(tenantId: string, routerId: string, opts?: MutationOptions): Promise<{ migration_id: string }>;
  listDiscoveredAccounts(
    tenantId: string,
    migrationId: string,
    page: PageParams,
  ): Promise<CursorPage<DiscoveredAccount>>;
  getIdentityConflicts(tenantId: string, migrationId: string): Promise<IdentityConflictCandidate[]>;
  resolveIdentityConflict(
    tenantId: string,
    migrationId: string,
    groupId: string,
    resolution: 'merge' | 'keep_one' | 'rename',
    opts?: MutationOptions,
  ): Promise<void>;
  saveMigrationDraft(tenantId: string, state: MigrationDraftState): Promise<void>;
  getMigrationDraft(tenantId: string, routerId: string): Promise<MigrationDraftState | null>;
  requestPasswordHarvest(tenantId: string, routerId: string, opts?: MutationOptions): Promise<JobAccepted>;
  commitMigration(
    tenantId: string,
    migrationId: string,
    opts?: MutationOptions,
  ): Promise<JobAccepted>;

  /* ---- CSV import U08 ---- */
  createCsvImport(
    tenantId: string,
    input: { mode: CsvImportMode; file_name: string; rows: Record<string, string>[] },
    opts?: MutationOptions,
  ): Promise<CsvImportDraft>;
  validateCsvImport(tenantId: string, importId: string, opts?: MutationOptions): Promise<CsvValidationResult>;
  commitCsvImport(tenantId: string, importId: string, opts?: MutationOptions): Promise<JobAccepted>;

  /* ---- Jobs (dok: GET /jobs/{id}) ---- */
  listJobs(tenantId: string, page: PageParams): Promise<CursorPage<JobRecord>>;
  getJob(tenantId: string, jobId: string): Promise<JobRecord>;
  retryJob(tenantId: string, jobId: string, opts?: MutationOptions): Promise<JobAccepted | null>;
  cancelJob(tenantId: string, jobId: string, reason: string, opts?: MutationOptions): Promise<void>;

  /* ---- Backups U12 ---- */
  listBackupArtifacts(tenantId: string, routerId: string | null): Promise<BackupArtifact[]>;
  listBackupSchedules(tenantId: string): Promise<BackupSchedule[]>;
  runBackupNow(tenantId: string, routerId: string, opts?: MutationOptions): Promise<JobAccepted>;

  /* ---- Monitoring U13 (PENDING_BACKEND) ---- */
  listMonitorStatus(tenantId: string): Promise<MonitorStatus[]>;

  /* ---- RADIUS U19 (dok: GET /routers/{id}/radius-status) ---- */
  listRadiusAccounts(
    tenantId: string,
    filters: { query?: string; state?: string },
    page: PageParams,
  ): Promise<CursorPage<RadiusAccountRow>>;
  listRadiusRouterStatus(tenantId: string): Promise<RadiusRouterStatus[]>;
  getRadiusRouterStatus(tenantId: string, routerId: string): Promise<RadiusRouterStatus>;
  startRadiusCutover(
    tenantId: string,
    routerId: string,
    opts?: MutationOptions,
  ): Promise<JobAccepted>;
  suspendRadiusAccount(tenantId: string, accountId: string, opts?: MutationOptions): Promise<void>;
  activateRadiusAccount(tenantId: string, accountId: string, opts?: MutationOptions): Promise<void>;

  /* ---- Subscription (dok: GET /tenants/{t}/subscription; POST quotations; payment-submissions) ---- */
  getSubscription(tenantId: string): Promise<SubscriptionInfo>;
  getPlans(): Promise<PlanInfo[]>;
  requestQuotation(
    tenantId: string,
    planCode: string,
    term: 'monthly' | 'yearly',
    opts?: MutationOptions,
  ): Promise<{ quotation_id: string; invoice_id: string; amount: string }>;
  submitPaymentProof(
    tenantId: string,
    invoiceId: string,
    input: { file_name: string; file_size: number; mime: string },
    opts?: MutationOptions,
  ): Promise<{ submission_id: string; state: string }>;

  /* ---- Platform admin U14 (dok: GET/POST platform/payment-submissions) ---- */
  listPlatformSubmissions(
    queue: 'submitted' | 'reviewing' | 'approved' | 'revision_requested' | 'rejected',
  ): Promise<PlatformPaymentSubmission[]>;
  approvePlatformSubmission(
    submissionId: string,
    opts?: MutationOptions,
  ): Promise<void>;
  rejectPlatformSubmission(submissionId: string, reason: string, opts?: MutationOptions): Promise<void>;
  requestRevisionPlatformSubmission(submissionId: string, reason: string, opts?: MutationOptions): Promise<void>;

  /* ---- Audit timeline ---- */
  listAuditTimeline(tenantId: string, targetId: string | null, page: PageParams): Promise<CursorPage<AuditEntry>>;
}

export type ApiMode = 'mock' | 'live';
export const API_MODE: ApiMode = (import.meta.env.VITE_API_MODE ?? 'mock') as ApiMode;
