/**
 * Kontrak tipe frontend — sumber: docs/ARCHITECTURE.md §5 (API), §7 (state domain),
 * docs/UI_UX.md (alur). Endpoint yang didokumentasikan mengikuti bentuk persis;
 * endpoint READ pendukung UI yang belum tercantum ditandai PENDING_BACKEND.
 * Uang: numeric(20,2) sebagai string JSON — tidak float (ARCHITECTURE.md §4).
 * Waktu kejadian: UTC ISO 8601 string; tanggal bisnis: 'YYYY-MM-DD'.
 */

/* ---------- Umum ---------- */

export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}

export interface FieldError {
  code: string;
  message: string;
}

export interface ApiErrorEnvelope {
  code: string;
  message: string;
  request_id: string;
  locale: string;
  field_errors?: Record<string, FieldError[]>;
  retryable?: boolean;
}

/* ---------- Identitas & tenant ---------- */

export type Role =
  | 'owner'
  | 'technician'
  | 'payments_admin'
  | 'accountant'
  | 'viewer'
  | 'collector'
  | 'agent';

export interface TenantSummary {
  id: string;
  display_name: string;
  role: Role;
}

export interface SessionUser {
  id: string;
  email: string;
  full_name: string;
  mfa_enabled: boolean;
  /** true bila platform admin permission aktif (ruang /admin). */
  platform_admin: boolean;
}

/* ---------- Router & enrollment (U05/U06) ---------- */

export type EnrollmentMode = 'read_only' | 'managed';

export type EnrollmentState =
  | 'draft'
  | 'enrollment_issued'
  | 'bootstrap_pending'
  | 'tunnel_seen'
  | 'api_verified'
  | 'discovery_ready'
  | 'conflict'
  | 'expired'
  | 'revoked';

export interface RouterEnrollmentRequest {
  display_name: string;
  router_code: string;
  location?: string | null;
  mode: EnrollmentMode;
}

export interface BootstrapScript {
  enrollment_id: string;
  /** Skrip hanya untuk role berwenang; kedaluwarsa 15 menit (enroll.token_ttl_s=900). */
  script: string;
  expires_at: string;
  purpose_summary: string[];
}

export interface RouterHealth {
  vpn: 'up' | 'down' | 'unknown';
  api: 'up' | 'down' | 'unknown';
  observed_at: string | null;
}

export type EnforcementMode =
  | 'local'
  | 'radius_shadow'
  | 'radius_authoritative'
  | 'degraded';

export interface RouterSummary {
  id: string;
  display_name: string;
  router_code: string;
  location: string | null;
  model: string | null;
  routeros_version: string | null;
  mode: 'read_only' | 'managed';
  health: RouterHealth;
  enforcement_mode: EnforcementMode;
  services_count: number;
}

export interface RouterDetail extends RouterSummary {
  identity: string | null;
  capability: Record<string, boolean>;
  uptime_s: number | null;
  serial: string | null;
}

/* ---------- Discovery/adopsi (U07) ---------- */

export type DiscoveryObjectState =
  | 'discovered'
  | 'selected'
  | 'adopted'
  | 'ignored'
  | 'conflict'
  | 'stale';

export type DriftCode =
  | 'missing_source'
  | 'needs_review'
  | 'hold_unknown'
  | 'local_account_shadow'
  | 'binding_invalid';

export interface DiscoveredAccount {
  id: string;
  username: string;
  kind: 'pppoe' | 'hotspot';
  profile: string | null;
  service: 'pppoe' | 'hotspot' | 'any';
  disabled_on_router: boolean;
  comment: string | null;
  state: DiscoveryObjectState;
}

export interface IdentityConflictCandidate {
  candidate_group_id: string;
  usernames: string[];
  routers: string[];
  kind: 'structural_match' | 'password_conflict';
  /** Keputusan Owner: gabung / pilih satu / rename (UI_UX.md §6). */
  resolution: 'merge' | 'keep_one' | 'rename' | null;
}

export type PasswordSource =
  | 'harvest_temporary'
  | 'csv'
  | 'new_password'
  | 'radius_import'
  | 'unknown';

export interface MigrationSummaryCounts {
  to_create: number;
  to_merge: number;
  unchanged: number;
  conflicts: number;
  quota_used: number;
  quota_limit: number;
}

/* ---------- CSV import (U08) ---------- */

export type CsvImportMode =
  | 'create'
  | 'link'
  | 'update'
  | 'device_mapping'
  | 'password_migration';

export interface CsvRowError {
  row: number;
  field: string | null;
  reason_code: string;
  action_hint: string;
}

export interface CsvValidationResult {
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  row_errors: CsvRowError[];
  preview: Record<string, string>[];
}

/* ---------- Pelanggan & layanan (U04) ---------- */

export type BillingStatus = 'not_billed' | 'current' | 'overdue' | 'exempt';
export type PaymentDimension = 'unbilled' | 'partial' | 'paid' | 'not_billed';
export type IsolationStatus =
  | 'normal'
  | 'isolated'
  | 'awaiting_verification'
  | 'hold';
export type ConnectionStatus = 'online' | 'offline' | 'unknown';
export type JobDimension = 'none' | 'queued' | 'running' | 'needs_review';
export type ServiceLifecycle =
  | 'draft'
  | 'pending'
  | 'provisioning'
  | 'provisioned'
  | 'conflict'
  | 'failed'
  | 'terminated'
  | 'archived';

export interface ServiceRow {
  id: string;
  service_code: string;
  customer_code: string;
  customer_name: string;
  username: string | null;
  kind: 'pppoe' | 'hotspot';
  package_name: string | null;
  router_id: string | null;
  router_display_name: string | null;
  lifecycle: ServiceLifecycle;
  /** Empat dimensi terpisah — jangan digabung (UI_UX.md §5). */
  payment: PaymentDimension;
  isolation: IsolationStatus;
  connection: ConnectionStatus;
  job: JobDimension;
  incomplete_mapping: boolean;
}

export interface ServiceDetail extends ServiceRow {
  start_date: string | null;
  contact: string | null;
  address: string | null;
  access: {
    username: string | null;
    state: 'active' | 'suspended' | 'disabled' | 'expired' | null;
    credential_state: 'unknown' | 'ready' | 'rotation_pending' | null;
    session_limit: number | null;
    mac_locked: boolean | null;
    last_active_session_at: string | null;
    restricting_router_id: string | null;
  } | null;
}

/* ---------- Pekerjaan (U16) ---------- */

export type JobState =
  | 'queued'
  | 'claimed'
  | 'preflight'
  | 'executing'
  | 'verifying'
  | 'waiting_dependency'
  | 'retry_wait'
  | 'uncertain'
  | 'recovery_required'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type JobKind =
  | 'discover_router'
  | 'harvest_passwords'
  | 'commit_migration'
  | 'radius_cutover_step'
  | 'disconnect_session'
  | 'apply_account_attributes'
  | 'suspend_service'
  | 'activate_service'
  | 'backup_router'
  | 'import_commit'
  | 'router_release'
  | 'router_replace'
  | 'change_plan';

export interface JobRecord {
  id: string;
  kind: JobKind;
  state: JobState;
  actor_display: string;
  created_at: string;
  updated_at: string;
  router_id: string | null;
  /** Tahap dan item selesai — tanpa ETA bila tak terukur. */
  phase_label_code: string | null;
  items_total: number | null;
  items_done: number | null;
  error_code: string | null;
  request_id: string | null;
  retryable: boolean;
}

/* ---------- Backup (U12) ---------- */

export interface BackupArtifact {
  id: string;
  router_id: string;
  generation: number;
  created_at: string;
  category: 'routine' | 'manual' | 'pre_change';
  size_bytes: number;
  transfer_state: 'committed' | 'staging' | 'verifying' | 'failed';
  encrypted: boolean;
}

export interface BackupSchedule {
  router_id: string;
  timezone: string;
  frequency: 'daily' | 'weekly';
  time_local: string;
  artifact_type: 'binary' | 'export';
  notification_enabled: boolean;
}

/* ---------- Monitoring (U13) ---------- */

export type RouterMonitorGroup =
  | 'healthy'
  | 'disturbed'
  | 'unmonitored'
  | 'stale_data'
  | 'management_unreachable';

export interface InterfaceStat {
  name: string;
  enabled: boolean;
  rx_bytes_s: number | null;
  tx_bytes_s: number | null;
  last_sample_at: string | null;
}

export interface MonitorStatus {
  router_id: string;
  group: RouterMonitorGroup;
  observed_at: string | null;
  source: string;
  interfaces: InterfaceStat[];
  radius: {
    auth_success_ratio_24h: number | null;
    inbound_sessions_24h: number | null;
    last_accounting_at: string | null;
  } | null;
}

/* ---------- RADIUS (U19) ---------- */

export interface RadiusAccountRow {
  id: string;
  username: string;
  kind: 'pppoe' | 'hotspot';
  state: 'active' | 'suspended' | 'disabled' | 'expired';
  credential_state: 'unknown' | 'ready' | 'rotation_pending';
  package_name: string | null;
  restricting_router_id: string | null;
  last_active_session_at: string | null;
}

export interface RadiusRouterStatus {
  router_id: string;
  enforcement_mode: EnforcementMode;
  migrated_accounts: number;
  auth_success_ratio_24h: number | null;
  inbound_sessions_24h: number | null;
  last_accounting_at: string | null;
  radius_primary: string;
  radius_secondary: string | null;
  client_status: 'ok' | 'missing_client' | 'degraded';
}

/* ---------- Subscription (U18) ---------- */

export type SubscriptionState =
  | 'free'
  | 'pending'
  | 'active'
  | 'grace'
  | 'restricted'
  | 'ended';

export interface PlanInfo {
  code: 'free' | 'bronze' | 'silver' | 'gold' | 'diamond' | 'platinum';
  routers_limit: number | null;
  services_limit: number | null;
  monthly_price: string;
  yearly_price: string;
}

export interface SubscriptionInfo {
  plan: PlanInfo;
  state: SubscriptionState;
  period_start: string | null;
  period_end: string | null;
  usage: {
    routers_used: number;
    services_used: number;
    draft_used: number;
    draft_cap: number;
  };
  pending_invoice: { id: string; amount: string; due_at: string } | null;
}

/* ---------- Platform admin (U14) ---------- */

export type PaymentSubmissionState =
  | 'submitted'
  | 'reviewing'
  | 'approved'
  | 'revision_requested'
  | 'rejected';

export interface PlatformPaymentSubmission {
  id: string;
  tenant_display_name: string;
  saas_invoice_id: string;
  plan_code: string;
  period_months: number;
  amount: string;
  submitted_at: string;
  state: PaymentSubmissionState;
  assignee: string | null;
}

/* ---------- Audit timeline ---------- */

export interface AuditEntry {
  id: string;
  at: string;
  actor_display: string;
  action_code: string;
  target_display: string | null;
}

/* ---------- Reveal ---------- */

export interface RevealCredentialResult {
  username: string;
  password: string;
  /** Auto-sembunyi 30 detik (UI_UX.md §3). */
  display_for_s: 30;
}
