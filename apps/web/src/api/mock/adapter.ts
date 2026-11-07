import type {
  ApiClient,
  AuthContextShape,
  CsvImportDraft,
  EnrollmentProgress,
  InvoiceListFilters,
  JobAccepted,
  MigrationDraftState,
  PaymentListFilters,
  RecordPaymentInput,
  RouterEnrollmentDraft,
  ServiceListFilters,
} from '../client';
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
  InternetInvoice,
  InternetInvoiceDetail,
  InternetPayment,
  InternetPaymentDetail,
  InvoiceAgingReport,
  IssuedDocumentInfo,
  JobRecord,
  MonitorStatus,
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
  EnrollmentProtocol,
} from '../contracts';
import type { MutationOptions, PageParams } from '../http';
import type { Permission } from '../../permissions/permissions';
import type { Locale } from '../../i18n';
import { ROLE_PERMISSIONS } from '../../permissions/permissions';
import {
  AUDIT,
  BACKUP_ARTIFACTS,
  BACKUP_SCHEDULES,
  BILLING_AGING,
  BILLING_DOCUMENTS,
  BILLING_INVOICES,
  BILLING_PAYMENT_ALLOCATIONS,
  BILLING_PAYMENTS,
  DISCOVERED,
  IDENTITY_CONFLICTS,
  JOBS_SEED,
  MOCK_NOW,
  MONITOR,
  RADIUS_ACCOUNTS,
  RADIUS_STATUS,
  ROUTERS,
  SERVICE_DETAILS,
  SERVICES,
  SUBSCRIPTIONS,
  TENANTS,
} from './fixtures';

/**
 * ADAPTER PENGEMBANGAN (mock) — terisolasi di belakang batas integrasi typed.
 * Semua hasilnya adalah data simulasi; bukan integrasi backend.
 * Latensi & progres job disimulasikan deterministik agar state UI dapat diuji.
 */

const LATENCY_MS = 160;

function delay<T>(value: T, ms = LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function fail(code: string, message: string, field_errors?: Record<string, { code: string; message: string }[]>): never {
  const err = new Error(`[${code}] ${message}`) as Error & {
    code: string;
    envelope: { code: string; message: string; request_id: string; locale: string; field_errors?: Record<string, { code: string; message: string }[]> };
  };
  err.code = code;
  err.envelope = {
    code,
    message,
    request_id: `mock-${Math.random().toString(36).slice(2, 8)}`,
    locale: 'id',
    field_errors,
  };
  throw err;
}

function paginate<T>(items: T[], page: PageParams): CursorPage<T> {
  const limit = Math.min(page.limit ?? 50, 200);
  const start = page.cursor ? Number(atob(page.cursor)) || 0 : 0;
  const slice = items.slice(start, start + limit);
  const next = start + limit < items.length ? btoa(String(start + limit)) : null;
  return { items: slice, next_cursor: next };
}

interface MockJobState {
  job: JobRecord;
  started_at: number;
  /** Rencana tahap: [kode fase, durasi ms]. */
  plan: Array<[string, number]>;
  end: 'succeeded' | 'failed' | 'uncertain';
  errorCode?: string;
}

export class MockApiClient implements ApiClient {
  static instanceCount = 0;
  readonly instanceId = ++MockApiClient.instanceCount;
  private session: SessionUser | null = null;
  private activeTenantId: string | null = null;
  private jobs: JobRecord[] = [...JOBS_SEED];
  private jobPlans = new Map<string, MockJobState>();
  /* Billing M6 (TK-604): salinan muat state per-instance — mutasi verify/reject
     mengubah salinan, bukan fixture modul (isolasi antar sesi dev). */
  private billingInvoices: Record<string, InternetInvoice[]> = Object.fromEntries(
    Object.entries(BILLING_INVOICES).map(([k, v]) => [k, v.map((i) => ({ ...i }))]),
  );
  private billingPayments: Record<string, InternetPayment[]> = Object.fromEntries(
    Object.entries(BILLING_PAYMENTS).map(([k, v]) => [k, v.map((p) => ({ ...p }))]),
  );
  private billingDocuments: Record<string, IssuedDocumentInfo[]> = Object.fromEntries(
    Object.entries(BILLING_DOCUMENTS).map(([k, v]) => [k, v.map((d) => ({ ...d }))]),
  );
  private billingSeq = 100;
  private enrollments = new Map<string, RouterEnrollmentDraft>();
  private enrollmentStage = new Map<string, number>();
  private enrollmentIssuedAt = new Map<string, number>();
  private migrations = new Map<string, { routerId: string; draft: MigrationDraftState }>();
  private csvImports = new Map<string, CsvImportDraft>();
  private submissions: PlatformPaymentSubmission[] = [
    {
      id: 'sub-01',
      tenant_display_name: 'RT Net Nusantara',
      saas_invoice_id: 'sinv-2031',
      plan_code: 'silver',
      period_months: 12,
      amount: '10000000.00',
      submitted_at: '2026-11-04T16:20:00+07:00',
      state: 'submitted',
      assignee: null,
    },
    {
      id: 'sub-02',
      tenant_display_name: 'RT Sungai Pinang',
      saas_invoice_id: 'sinv-2029',
      plan_code: 'gold',
      period_months: 1,
      amount: '1500000.00',
      submitted_at: '2026-11-03T11:05:00+07:00',
      state: 'submitted',
      assignee: null,
    },
    {
      id: 'sub-03',
      tenant_display_name: 'RW Net Cemara',
      saas_invoice_id: 'sinv-2018',
      plan_code: 'bronze',
      period_months: 12,
      amount: '5000000.00',
      submitted_at: '2026-10-28T09:44:00+07:00',
      state: 'approved',
      assignee: 'Admin Platform 1',
    },
  ];
  private reauthUntil: string | null = null;
  private authenticatingEmail: string | null = null;

  constructor() {
    // Auto-login dev: memudahkan pemeriksaan UI; tetap bisa logout.
    this.session = {
      id: 'usr-owner-01',
      email: 'huda@example.dev',
      full_name: 'Huda Choirul Anam',
      mfa_enabled: true,
      platform_admin: true,
    };
    this.activeTenantId = TENANTS[0]!.id;
  }

  /* ---------- helper ---------- */

  private authCtx(): AuthContextShape {
    if (!this.session || !this.activeTenantId) fail('unauthorized', 'Sesi berakhir. Masuk kembali');
    const tenant = TENANTS.find((t) => t.id === this.activeTenantId);
    if (!tenant) fail('not_found', 'Data tidak ditemukan');
    return {
      user: this.session,
      tenants: TENANTS,
      active_tenant_id: this.activeTenantId,
      permissions: [...ROLE_PERMISSIONS[tenant.role]],
      sensitive_reauth_until: this.reauthUntil,
    };
  }

  private tenantOr404(tenantId: string): TenantSummary {
    const t = TENANTS.find((x) => x.id === tenantId);
    if (!t) fail('not_found', 'Data tidak ditemukan');
    return t;
  }

  private permissionOr403(tenantId: string, permission: Permission): void {
    const tenant = this.tenantOr404(tenantId);
    if (!ROLE_PERMISSIONS[tenant.role].includes(permission)) {
      fail('forbidden', 'Anda tidak memiliki izin untuk tindakan ini');
    }
  }

  private newJob(
    kind: JobRecord['kind'],
    routerId: string | null,
    actor: string,
    plan: Array<[string, number]>,
    end: MockJobState['end'],
    items: { total: number | null; done: number | null },
    errorCode?: string,
  ): JobRecord {
    const id = `job-${Math.random().toString(36).slice(2, 7)}`;
    const job: JobRecord = {
      id,
      kind,
      state: 'queued',
      actor_display: actor,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      router_id: routerId,
      phase_label_code: null,
      items_total: items.total,
      items_done: items.done,
      error_code: null,
      request_id: `req-${Math.random().toString(36).slice(2, 8)}`,
      retryable: end === 'failed',
    };
    this.jobs.unshift(job);
    this.jobPlans.set(id, { job, started_at: Date.now(), plan, end, errorCode });
    return job;
  }

  /** Majukan job sesuai waktu berjalan; dipanggil saat job dibaca. */
  private advanceJob(job: JobRecord): JobRecord {
    const st = this.jobPlans.get(job.id);
    if (!st || ['succeeded', 'failed', 'cancelled'].includes(job.state)) return job;
    const elapsed = Date.now() - st.started_at;
    let acc = 0;
    let phase = 'queued';
    let state: JobRecord['state'] = 'queued';
    for (const [code, dur] of st.plan) {
      acc += dur;
      if (elapsed < acc) {
        state = 'executing';
        phase = code;
        break;
      }
      phase = code;
    }
    if (elapsed >= st.plan.reduce((s, [, d]) => s + d, 0) + 700) {
      job.state = st.end;
      job.phase_label_code = null;
      if (st.end === 'failed') {
        job.error_code = st.errorCode ?? 'router_unreachable';
      }
      job.updated_at = new Date().toISOString();
      if (job.items_total && job.items_done !== null) job.items_done = job.items_total;
      return job;
    }
    if (elapsed > 900 && state === 'executing') {
      // fase terakhir → verifying sebelum terminal
      const lastDur = st.plan[st.plan.length - 1]?.[1] ?? 0;
      if (elapsed > acc - lastDur + 400) state = 'verifying';
    }
    job.state = state;
    job.phase_label_code = phase;
    job.updated_at = new Date().toISOString();
    if (job.items_total) {
      const frac = Math.min(1, elapsed / (acc || 1));
      job.items_done = Math.round((job.items_total ?? 0) * frac);
    }
    return job;
  }

  /* ---------- Meta ---------- */

  getEnums(locale: Locale): Promise<Record<string, Record<string, string>>> {
    const enums = {
      job_state: {
        queued: 'Permintaan diterima dan menunggu giliran',
        claimed: 'Sedang diproses',
        preflight: 'Sedang diproses',
        executing: 'Sedang diproses',
        verifying: 'Memeriksa hasil sesuai jenis tindakan',
        waiting_dependency: 'Menunggu dependency yang disebutkan pada pekerjaan',
        retry_wait: 'Akan dicoba lagi otomatis',
        uncertain: 'Hasil perubahan belum dapat dipastikan',
        recovery_required: 'Perlu pemulihan manual sebelum melanjutkan',
        succeeded: 'Pekerjaan selesai; hasil telah diverifikasi',
        failed: 'Gagal',
        cancelled: 'Dibatalkan',
      },
      enforcement_mode: {
        local: 'Lokal',
        radius_shadow: 'Bayangan',
        radius_authoritative: 'Otoritatif',
        degraded: 'Terganggu',
      },
      connection: { online: 'Online', offline: 'Offline', unknown: 'Tidak diketahui' },
      isolation: {
        normal: 'Normal',
        isolated: 'Terisolir',
        awaiting_verification: 'Menunggu verifikasi',
        hold: 'Hold',
      },
      payment: {
        unbilled: 'Belum dibayar',
        partial: 'Sebagian',
        paid: 'Lunas',
        not_billed: 'Tidak ditagih',
      },
      lifecycle: {
        draft: 'Draft',
        pending: 'Menunggu',
        provisioning: 'Menyiapkan',
        provisioned: 'Aktif',
        conflict: 'Konflik',
        failed: 'Gagal',
        terminated: 'Dihentikan',
        archived: 'Diarsipkan',
      },
    };
    const out: Record<string, Record<string, string>> = {};
    for (const [group, values] of Object.entries(enums)) {
      out[group] = {};
      for (const [key, idLabel] of Object.entries(values)) {
        out[group]![key] = locale === 'en' ? `${idLabel} (en)` : idLabel;
      }
    }
    return delay(out);
  }

  /* ---------- Sesi ---------- */

  async login(email: string, password: string): Promise<{ requires_totp: boolean }> {
    if (!email || !password) {
      fail('validation_error', 'Email dan password wajib diisi', {
        email: email ? undefined : [{ code: 'required', message: 'Email wajib diisi' }],
        password: password ? undefined : [{ code: 'required', message: 'Password wajib diisi' }],
      } as Record<string, { code: string; message: string }[]>);
    }
    this.authenticatingEmail = email;
    // Pesan gagal login selalu sama agar tidak mengungkap akun (UI_UX.md §3).
    if (password.length < 12) fail('unauthorized', 'Email atau password tidak cocok');
    return delay({ requires_totp: true });
  }

  async loginTotp(code: string): Promise<AuthContextShape> {
    if (!/^\d{6}$/.test(code)) {
      fail('validation_error', 'Kode TOTP tidak valid', {
        code: [{ code: 'pattern', message: 'Kode TOTP harus 6 digit' }],
      });
    }
    this.session = {
      id: 'usr-owner-01',
      email: this.authenticatingEmail ?? 'huda@example.dev',
      full_name: 'Huda Choirul Anam',
      mfa_enabled: true,
      platform_admin: true,
    };
    this.activeTenantId = TENANTS[0]!.id;
    return delay(this.authCtx());
  }

  async register(input: { full_name: string; email: string; password: string; company_name: string }): Promise<{ verification_sent: true }> {
    const fe: Record<string, { code: string; message: string }[]> = {};
    if (!input.full_name.trim()) fe.full_name = [{ code: 'required', message: 'Nama wajib diisi' }];
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.email)) fe.email = [{ code: 'email', message: 'Format email tidak valid' }];
    if (input.password.length < 12) fe.password = [{ code: 'min_length', message: 'Password minimal 12 karakter' }];
    if (!input.company_name.trim()) fe.company_name = [{ code: 'required', message: 'Nama perusahaan wajib diisi' }];
    if (Object.keys(fe).length) fail('validation_error', 'Periksa kembali isian Anda', fe);
    return delay({ verification_sent: true });
  }

  async verifyEmail(_token: string): Promise<AuthContextShape> {
    this.session = {
      id: 'usr-new-01',
      email: 'baru@example.dev',
      full_name: 'Pengguna Baru',
      mfa_enabled: false,
      platform_admin: false,
    };
    this.activeTenantId = TENANTS[0]!.id;
    return delay(this.authCtx());
  }

  async requestPasswordReset(_email: string): Promise<void> {
    return delay(undefined);
  }

  async getSession(): Promise<AuthContextShape> {
    if (!this.session) fail('unauthorized', 'Sesi berakhir. Masuk kembali');
    return delay(this.authCtx());
  }

  async logout(): Promise<void> {
    this.session = null;
    this.activeTenantId = null;
    this.reauthUntil = null;
    return delay(undefined);
  }

  async reauthenticate(password: string, totp_code: string): Promise<{ valid_until: string }> {
    if (password.length < 1 || !/^\d{6}$/.test(totp_code)) {
      fail('validation_error', 'Konfirmasi identitas gagal', {
        totp_code: [{ code: 'pattern', message: 'Kode TOTP harus 6 digit' }],
      });
    }
    const until = new Date(Date.now() + 600_000).toISOString();
    this.reauthUntil = until;
    return delay({ valid_until: until });
  }

  /* ---------- Tenant ---------- */

  async getTenants(): Promise<TenantSummary[]> {
    return delay([...TENANTS]);
  }

  async switchTenant(tenantId: string): Promise<AuthContextShape> {
    this.tenantOr404(tenantId);
    this.activeTenantId = tenantId;
    return delay(this.authCtx());
  }

  /* ---------- Services ---------- */

  listServices(tenantId: string, filters: ServiceListFilters, page: PageParams): Promise<CursorPage<ServiceRow>> {
    this.permissionOr403(tenantId, 'customers.read');
    let items = [...(SERVICES[tenantId] ?? [])];
    if (filters.router_id) items = items.filter((s) => s.router_id === filters.router_id);
    if (filters.query) {
      const q = filters.query.toLowerCase();
      items = items.filter(
        (s) =>
          s.customer_name.toLowerCase().includes(q) ||
          s.service_code.toLowerCase().includes(q) ||
          s.username?.toLowerCase().includes(q),
      );
    }
    if (filters.connection) items = items.filter((s) => s.connection === filters.connection);
    if (filters.payment) items = items.filter((s) => s.payment === filters.payment);
    if (filters.isolation) items = items.filter((s) => s.isolation === filters.isolation);
    if (filters.job) items = items.filter((s) => s.job === filters.job);
    if (filters.incomplete_mapping) items = items.filter((s) => s.incomplete_mapping);
    if (filters.quick_tab) {
      switch (filters.quick_tab) {
        case 'unpaid':
          items = items.filter((s) => s.payment === 'unbilled' || s.payment === 'partial');
          break;
        case 'paid_awaiting_activation':
          items = items.filter((s) => s.payment === 'paid' && s.isolation === 'awaiting_verification');
          break;
        case 'isolated':
          items = items.filter((s) => s.isolation === 'isolated');
          break;
        case 'incomplete':
          items = items.filter((s) => s.incomplete_mapping);
          break;
        default:
          break;
      }
    }
    return delay(paginate(items, page));
  }

  async getService(tenantId: string, serviceId: string): Promise<ServiceDetail> {
    this.permissionOr403(tenantId, 'customers.read');
    const row = (SERVICES[tenantId] ?? []).find((s) => s.id === serviceId);
    if (!row) fail('not_found', 'Data tidak ditemukan');
    const extra = SERVICE_DETAILS[serviceId] ?? {};
    return delay({
      ...row,
      start_date: '2026-01-05',
      contact: null,
      address: null,
      access: {
        username: row.username,
        state: 'active',
        credential_state: 'ready',
        session_limit: 1,
        mac_locked: false,
        last_active_session_at: '2026-11-04T22:10:00Z',
        restricting_router_id: row.router_id,
      },
      ...extra,
    });
  }

  async createServiceDraft(
    tenantId: string,
    input: Record<string, unknown>,
    _opts?: MutationOptions,
  ): Promise<{ id: string; state: string }> {
    this.permissionOr403(tenantId, 'customers.write');
    const fe: Record<string, { code: string; message: string }[]> = {};
    const name = String(input.customer_name ?? '').trim();
    if (!name) fe.customer_name = [{ code: 'required', message: 'Nama pelanggan wajib diisi' }];
    const routerId = input.router_id ? String(input.router_id) : null;
    if (routerId) this.tenantOr404(tenantId) && ROUTERS[tenantId]?.find((r) => r.id === routerId) === undefined && (fe.router_id = [{ code: 'invalid', message: 'Router tidak ditemukan' }]);
    if (Object.keys(fe).length) fail('validation_error', 'Periksa kembali isian Anda', fe);
    const choice = String(input.final_choice ?? 'draft');
    const id = `svc-${Math.random().toString(36).slice(2, 7)}`;
    if (choice === 'draft') {
      (SERVICES[tenantId] ??= []).push({
        id,
        service_code: `SVC-9${Math.floor(Math.random() * 90 + 10)}`,
        customer_code: `CUS-9${Math.floor(Math.random() * 90 + 10)}`,
        customer_name: name,
        username: null,
        kind: (input.kind as 'pppoe' | 'hotspot') ?? 'pppoe',
        package_name: (input.package_name as string) ?? null,
        router_id: routerId,
        router_display_name: null,
        lifecycle: 'draft',
        payment: 'not_billed',
        isolation: 'normal',
        connection: 'unknown',
        job: 'none',
        incomplete_mapping: true,
      });
      return delay({ id, state: 'draft' }, 400);
    }
    // Buat akun: 202 + job (arsitektur §5 — tidak menulis ke router di R1).
    const job = this.newJob(
      'import_commit',
      routerId,
      'Pengguna Dev',
      [['reserve', 500], ['create_account', 900], ['verify', 600]],
      'succeeded',
      { total: 1, done: 0 },
    );
    return delay({ id, state: `job:${job.id}` }, 400);
  }

  async revealCredential(tenantId: string, serviceId: string, _opts?: MutationOptions): Promise<RevealCredentialResult> {
    this.permissionOr403(tenantId, 'services.reveal_credentials');
    if (!this.reauthUntil || new Date(this.reauthUntil) < new Date()) {
      fail('forbidden', 'Konfirmasi identitas Anda diperlukan sebelum menampilkan password');
    }
    const svc = (SERVICES[tenantId] ?? []).find((s) => s.id === serviceId);
    if (!svc) fail('not_found', 'Data tidak ditemukan');
    if (svc.username === null) {
      // draft tanpa akun → tidak ada yang bisa direveal
      fail('validation_error', 'Layanan ini belum memiliki akun akses');
    }
    const chars = 'abcdefghjkmnpqrstuvwxyz23456789';
    let pw = '';
    for (let i = 0; i < 10; i++) pw += chars[Math.floor(Math.random() * chars.length)];
    return delay({ username: svc.username ?? '', password: pw, display_for_s: 30 });
  }

  /* ---------- Enrollment ---------- */

  async createEnrollment(
    tenantId: string,
    input: RouterEnrollmentRequest,
    _opts?: MutationOptions,
  ): Promise<RouterEnrollmentDraft> {
    this.permissionOr403(tenantId, 'routers.enroll');
    const fe: Record<string, { code: string; message: string }[]> = {};
    if (!input.display_name.trim()) fe.display_name = [{ code: 'required', message: 'Nama tampilan wajib diisi' }];
    if (!/^[A-Z0-9-]{2,16}$/.test(input.router_code)) fe.router_code = [{ code: 'pattern', message: 'Kode router 2–16 karakter: huruf besar, angka, tanda hubung' }];
    // Paritas backend Phase-2: wireguard (v7.1+) DAN sstp (v6.49.x + v7.x)
    // aktif; l2tp/openvpn ditolak jujur (menyusul per fase).
    const protocol = (input.protocol ?? 'wireguard') as EnrollmentProtocol;
    if (protocol !== 'wireguard' && protocol !== 'sstp') {
      fe.protocol = [{ code: 'unsupported', message: 'Protokol belum didukung rilis ini — WireGuard dan SSTP aktif (L2TP/IPsec/OpenVPN menyusul per fase)' }];
    }
    const rosVersion = (input.routeros_version ?? '7').replace(/^[vV]+/, '');
    if (!/^\d+(?:\.\d+){0,3}$/.test(rosVersion)) {
      fe.routeros_version = [{ code: 'invalid', message: 'Format versi RouterOS tidak valid (contoh: 7.15.3)' }];
    } else if (protocol === 'wireguard') {
      const parts = rosVersion.split('.').map(Number);
      if (parts[0]! < 7) {
        fe.routeros_version = [{ code: 'wireguard_requires_v7', message: 'WireGuard membutuhkan RouterOS v7.1+ — untuk RouterOS v6 pilih SSTP' }];
      } else if (parts[0]! === 7 && parts.length > 1 && parts[1]! < 1) {
        fe.routeros_version = [{ code: 'wireguard_requires_v7_1', message: 'WireGuard hadir sejak RouterOS v7.1 — versi 7.0 belum memuat WireGuard' }];
      }
    } else if (protocol === 'sstp') {
      const parts = rosVersion.split('.').map(Number);
      if (parts[0]! < 6) {
        fe.routeros_version = [{ code: 'sstp_requires_v6', message: 'SSTP membutuhkan RouterOS v6+ — versi lebih lama tidak didukung' }];
      }
    }
    if (Object.keys(fe).length) fail('validation_error', 'Periksa kembali isian Anda', fe);
    const id = `enr-${Math.random().toString(36).slice(2, 7)}`;
    const draft: RouterEnrollmentDraft = {
      id,
      request: { ...input, protocol, routeros_version: rosVersion },
      state: 'enrollment_issued',
    };
    this.enrollments.set(id, draft);
    this.enrollmentIssuedAt.set(id, Date.now());
    this.enrollmentStage.set(id, 0);
    return delay(draft, 300);
  }

  async getEnrollment(_tenantId: string, enrollmentId: string): Promise<EnrollmentProgress> {
    const draft = this.enrollments.get(enrollmentId);
    if (!draft) fail('not_found', 'Data tidak ditemukan');
    const elapsed = Date.now() - (this.enrollmentIssuedAt.get(enrollmentId) ?? Date.now());
    // Handshake VPN → API → autentikasi/izin → kompatibilitas; tiap tahap hasil sendiri (UI_UX.md §7).
    const stageCodes = ['vpn_handshake', 'api_verify', 'auth_permission', 'compatibility'];
    let stageIdx = Math.min(3, Math.floor(elapsed / 3000));
    if (elapsed > 13_000) stageIdx = 4; // discovery_ready
    this.enrollmentStage.set(enrollmentId, stageIdx);
    const states: Array<'pending' | 'ok' | 'failed'> = stageCodes.map((_, i) =>
      i < stageIdx ? 'ok' : 'pending',
    );
    const enrState: EnrollmentProgress['state'] =
      stageIdx >= 4 ? 'discovery_ready' : stageIdx >= 2 ? 'api_verified' : stageIdx >= 1 ? 'tunnel_seen' : 'bootstrap_pending';
    // Pelabelan jujur paritas backend: mock = simulator — TIDAK pernah diklaim
    // sebagai konektivitas perangkat nyata (verification.source='simulator').
    const verification =
      enrState === 'discovery_ready'
        ? { source: 'simulator', verified_lab: false, api_ssl: false, wireguard: false }
        : { source: null, verified_lab: false, api_ssl: false, wireguard: false };
    return delay(
      {
        enrollment_id: enrollmentId,
        state: enrState,
        stage_detail: stageCodes.map((code, i) => ({ code, state: states[i]! })),
        protocol: draft.request.protocol ?? 'wireguard',
        routeros_version: draft.request.routeros_version ?? '7',
        verification,
      },
      200,
    );
  }

  async getBootstrapScript(_tenantId: string, enrollmentId: string): Promise<BootstrapScript> {
    const draft = this.enrollments.get(enrollmentId);
    if (!draft) fail('not_found', 'Data tidak ditemukan');
    const issuedAt = this.enrollmentIssuedAt.get(enrollmentId) ?? Date.now();
    // Kedaluwarsa 15 menit (enroll.token_ttl_s = 900).
    if (Date.now() - issuedAt > 900_000) fail('expired', 'Skrip kedaluwarsa. Buat ulang; token lama dicabut');
    const mode = draft.request.mode === 'managed' ? 'read+write' : 'read-only';
    // Paritas backend Phase-2: skrip SSTP (v6/v7) — MSCHAPv2 saja + verifikasi
    // sertifikat server wajib nyala; port 4443; CA via endpoint enroll-ca.
    if (draft.request.protocol === 'sstp') {
      return delay({
        enrollment_id: enrollmentId,
        protocol: 'sstp',
        routeros_version: draft.request.routeros_version ?? '6',
        script: [
          '# MicroTix bootstrap — DEV FIXTURE (mock), jangan dijalankan pada perangkat nyata',
          `# Protokol: sstp · mode=${mode} · RouterOS: ${draft.request.routeros_version ?? '6'}`,
          ':local iface "mtx-sstp"',
          '/tool/fetch url="https://microtix.invalid/api/v1/bridge/enroll-ca" dst-path=microtix-ca.crt',
          '/interface/sstp-client/add name=$iface connect-to=microtix.invalid port=4443 \\',
          '    user=$user password=$pass authentication=mschap2 \\',
          '    verify-server-certificate=yes verify-server-address-from-certificate=yes disabled=no',
          '/tool/fetch url="https://microtix.invalid/api/v1/bridge/enroll-complete" http-method=post \\',
          '    http-data="{\\"token\\":\\"<dev-fixture-token>\\",\\"protocol\\":\\"sstp\\",\\"sstp_username\\":\\"<dev-fixture-user>\\"}" http-header-field="Content-Type: application/json"',
        ].join('\n'),
        expires_at: new Date(issuedAt + 900_000).toISOString(),
        gateway: {
          hostname: 'microtix.invalid',
          listen_port: 4443,
          api_port: 8729,
          server_tunnel_ip: '100.127.0.2',
        },
        purpose_summary: [
          'Membuat klien SSTP ke gateway publik via TLS (DEV FIXTURE — mock).',
          'Endpoint gateway: microtix.invalid:4443/TCP — kredensial per-router, MSCHAPv2, verifikasi sertifikat server wajib.',
          'Tanpa reset/reboot/add-default-route/perubahan DNS/DHCP/NAT/bridge/akun existing.',
          'Mock: skrip ini simulasi tampilan; verifikasi perangkat nyata menunggu lab G1.',
        ],
      });
    }
    return delay({
      enrollment_id: enrollmentId,
      protocol: 'wireguard',
      routeros_version: draft.request.routeros_version ?? '7',
      script: [
        '# MicroTix bootstrap — DEV FIXTURE (mock), jangan dijalankan pada perangkat nyata',
        `# Protokol: wireguard · mode=${mode} · RouterOS: ${draft.request.routeros_version ?? '7'}`,
        ':local iface "mtx-wg"',
        ':if ([/interface/wireguard/find where name=$iface] = "") do={ /interface/wireguard/add name=$iface listen-port=13231; }',
        '/interface/wireguard/peers/add interface=$iface public-key="<dev-fixture-server-pubkey>" \\',
        '    endpoint-address="microtix.invalid" endpoint-port=51820 \\',
        '    allowed-address=("100.127.0.1" . "/32") persistent-keepalive=25s',
        '/tool/fetch url="https://microtix.invalid/api/v1/bridge/enroll-complete" http-method=post \\',
        '    http-data="{\\"token\\":\\"<dev-fixture-token>\\"}" http-header-field="Content-Type: application/json"',
      ].join('\n'),
      expires_at: new Date(issuedAt + 900_000).toISOString(),
      gateway: {
        hostname: 'microtix.invalid',
        listen_port: 51820,
        api_port: 8729,
        server_tunnel_ip: '100.127.0.1',
      },
      purpose_summary: [
        'Membuat interface WireGuard + peer ke gateway publik + alamat tunnel /32 (DEV FIXTURE — mock).',
        'Endpoint gateway: microtix.invalid:51820/UDP — API manajemen hanya dari /32 server via tunnel.',
        'Tanpa reset/reboot/perubahan route default/DNS/DHCP/NAT/bridge/akun existing.',
        'Mock: skrip ini simulasi tampilan; verifikasi perangkat nyata menunggu lab G1.',
      ],
    });
  }

  /* ---------- Routers ---------- */

  async listRouters(tenantId: string): Promise<RouterSummary[]> {
    this.permissionOr403(tenantId, 'routers.read');
    return delay([...(ROUTERS[tenantId] ?? [])]);
  }

  async getRouter(tenantId: string, routerId: string): Promise<RouterDetail> {
    this.permissionOr403(tenantId, 'routers.read');
    const r = (ROUTERS[tenantId] ?? []).find((x) => x.id === routerId);
    if (!r) fail('not_found', 'Data tidak ditemukan');
    return delay({
      ...r,
      identity: `rtrw-${routerId}-node`,
      capability: { pppoe: true, hotspot: true, radius_client: true, fasttrack_detect: true },
      verification: { source: 'simulator', verified_lab: false, api_ssl: false, wireguard: false, sstp: false },
      uptime_s: 86400 * 12,
      serial: 'ABCD1234567',
    });
  }

  async releaseRouter(tenantId: string, routerId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'routers.release');
    this.getRouter(tenantId, routerId);
    const job = this.newJob('router_release', routerId, 'Pengguna Dev', [['fence', 800], ['detach', 700]], 'succeeded', { total: 1, done: 0 });
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` });
  }

  async replaceRouter(tenantId: string, routerId: string, _newRouterName: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'routers.release');
    this.getRouter(tenantId, routerId);
    const job = this.newJob('router_replace', routerId, 'Pengguna Dev', [['slot', 600], ['cutover_hint', 900]], 'succeeded', { total: 1, done: 0 });
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` });
  }

  async startDiscovery(tenantId: string, routerId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'routers.read');
    const r = (ROUTERS[tenantId] ?? []).find((x) => x.id === routerId);
    if (!r) fail('not_found', 'Data tidak ditemukan');
    const unreachable = r.health.vpn === 'down';
    const job = this.newJob(
      'discover_router',
      routerId,
      'Pengguna Dev',
      [['connect', 700], ['read_sources', 1100], ['build_snapshot', 800]],
      unreachable ? 'failed' : 'succeeded',
      { total: 4, done: 0 },
      'router_unreachable',
    );
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` }, 250);
  }

  /* ---------- Migration wizard ---------- */

  async startMigration(tenantId: string, routerId: string, _opts?: MutationOptions): Promise<{ migration_id: string }> {
    this.permissionOr403(tenantId, 'migration.run');
    const r = (ROUTERS[tenantId] ?? []).find((x) => x.id === routerId);
    if (!r) fail('not_found', 'Data tidak ditemukan');
    const id = `mig-${Math.random().toString(36).slice(2, 6)}`;
    this.migrations.set(id, {
      routerId,
      draft: {
        id,
        step: 0,
        selected_account_ids: [],
        identity_resolutions: {},
        profile_package_map: {},
        password_source: null,
        counts: null,
      },
    });
    return delay({ migration_id: id });
  }

  listDiscoveredAccounts(_tenantId: string, _migrationId: string, page: PageParams): Promise<CursorPage<DiscoveredAccount>> {
    return delay(paginate([...DISCOVERED], page));
  }

  async getIdentityConflicts(_tenantId: string, _migrationId: string): Promise<IdentityConflictCandidate[]> {
    return delay([...IDENTITY_CONFLICTS]);
  }

  async resolveIdentityConflict(_tenantId: string, _migrationId: string, _groupId: string, _resolution: 'merge' | 'keep_one' | 'rename', _opts?: MutationOptions): Promise<void> {
    return delay(undefined, 120);
  }

  async saveMigrationDraft(_tenantId: string, state: MigrationDraftState): Promise<void> {
    const m = this.migrations.get(state.id);
    if (m) m.draft = state;
    return delay(undefined, 100);
  }

  async getMigrationDraft(tenantId: string, routerId: string): Promise<MigrationDraftState | null> {
    for (const m of this.migrations.values()) {
      if (m.routerId === routerId) return delay(m.draft, 120);
    }
    void tenantId;
    return delay(null, 120);
  }

  async requestPasswordHarvest(tenantId: string, routerId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'migration.run');
    const r = (ROUTERS[tenantId] ?? []).find((x) => x.id === routerId);
    if (!r) fail('not_found', 'Data tidak ditemukan');
    const job = this.newJob(
      'harvest_passwords',
      routerId,
      'Pengguna Dev',
      [['temp_account', 800], ['read_creds', 1200], ['cleanup', 700], ['verify_cleanup', 500]],
      'succeeded',
      { total: 6, done: 0 },
    );
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` });
  }

  async commitMigration(tenantId: string, migrationId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'migration.run');
    const m = this.migrations.get(migrationId);
    if (!m) fail('not_found', 'Data tidak ditemukan');
    if (m.draft.password_source === null) {
      fail('validation_error', 'Pilih sumber password sebelum menyimpan', {
        password_source: [{ code: 'required', message: 'Sumber password wajib dipilih' }],
      });
    }
    const job = this.newJob(
      'commit_migration',
      m.routerId,
      'Pengguna Dev',
      [['reserve', 500], ['write_db', 1000], ['verify', 700]],
      'succeeded',
      { total: m.draft.selected_account_ids.length || 6, done: 0 },
    );
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` }, 250);
  }

  /* ---------- CSV ---------- */

  async createCsvImport(
    tenantId: string,
    input: { mode: CsvImportMode; file_name: string; rows: Record<string, string>[] },
    _opts?: MutationOptions,
  ): Promise<CsvImportDraft> {
    this.permissionOr403(tenantId, 'imports.run');
    if (input.rows.length > 10_000) {
      fail('validation_error', 'Berkas melebihi batas baris (10.000)', {
        file: [{ code: 'max_rows', message: 'Maksimum 10.000 baris' }],
      });
    }
    const id = `imp-${Math.random().toString(36).slice(2, 6)}`;
    const draft: CsvImportDraft = {
      id,
      mode: input.mode,
      file_name: input.file_name,
      total_rows: input.rows.length,
      validation: null,
      rows: input.rows,
    };
    this.csvImports.set(id, draft);
    return delay(draft, 200);
  }

  async validateCsvImport(_tenantId: string, importId: string, _opts?: MutationOptions): Promise<CsvValidationResult> {
    const draft = this.csvImports.get(importId);
    if (!draft) fail('not_found', 'Data tidak ditemukan');
    // Validasi contoh: kolom wajib username; baris tanpa username → error per baris.
    const rowErrors: { row: number; field: string | null; reason_code: string; action_hint: string }[] = [];
    let valid = 0;
    (draft.rows ?? []).forEach((row, i) => {
      if (!row.username) {
        rowErrors.push({ row: i + 2, field: 'username', reason_code: 'required', action_hint: 'Isi username atau hapus baris' });
      } else {
        valid++;
      }
    });
    const result: CsvValidationResult = {
      total_rows: draft.total_rows,
      valid_rows: valid,
      error_rows: rowErrors.length,
      row_errors: rowErrors,
      preview: (draft.rows ?? []).slice(0, 5),
    };
    draft.validation = result;
    return delay(result, 600);
  }

  async commitCsvImport(tenantId: string, importId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'imports.run');
    const draft = this.csvImports.get(importId);
    if (!draft) fail('not_found', 'Data tidak ditemukan');
    if (!draft.validation) fail('validation_error', 'Validasi belum dijalankan');
    const job = this.newJob(
      'import_commit',
      null,
      'Pengguna Dev',
      [['reserve', 600], ['commit', 1400], ['verify', 800]],
      'succeeded',
      { total: draft.validation.valid_rows, done: 0 },
    );
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` }, 250);
  }

  /* ---------- Jobs ---------- */

  listJobs(_tenantId: string, page: PageParams): Promise<CursorPage<JobRecord>> {
    return delay(paginate(this.jobs.map((j) => ({ ...j })), page));
  }

  async getJob(_tenantId: string, jobId: string): Promise<JobRecord> {
    const job = this.jobs.find((j) => j.id === jobId);
    if (!job) fail('not_found', 'Data tidak ditemukan');
    const advanced = { ...this.advanceJob(job) };
    return delay(advanced, 120);
  }

  async retryJob(_tenantId: string, jobId: string, _opts?: MutationOptions): Promise<JobAccepted | null> {
    const job = this.jobs.find((j) => j.id === jobId);
    if (!job) fail('not_found', 'Data tidak ditemukan');
    if (!job.retryable) fail('validation_error', 'Pekerjaan ini tidak dapat dicoba ulang');
    const newJob = this.newJob(
      job.kind,
      job.router_id,
      'Pengguna Dev',
      [['connect', 700], ['execute', 1300], ['verify', 700]],
      'succeeded',
      { total: job.items_total, done: 0 },
    );
    return delay({ job_id: newJob.id, status_url: `/api/v1/jobs/${newJob.id}` }, 200);
  }

  async cancelJob(_tenantId: string, jobId: string, _reason: string, _opts?: MutationOptions): Promise<void> {
    const job = this.jobs.find((j) => j.id === jobId);
    if (!job) fail('not_found', 'Data tidak ditemukan');
    if (!['queued', 'claimed', 'preflight', 'waiting_dependency', 'retry_wait'].includes(job.state)) {
      fail('validation_error', 'Tahap ini tidak lagi dapat dibatalkan');
    }
    job.state = 'cancelled';
    job.updated_at = new Date().toISOString();
    return delay(undefined, 150);
  }

  /* ---------- Backups ---------- */

  async listBackupArtifacts(tenantId: string, routerId: string | null): Promise<BackupArtifact[]> {
    this.permissionOr403(tenantId, 'backups.run');
    const all = BACKUP_ARTIFACTS[tenantId] ?? [];
    return delay(routerId ? all.filter((b) => b.router_id === routerId) : all);
  }

  async listBackupSchedules(tenantId: string): Promise<BackupSchedule[]> {
    this.permissionOr403(tenantId, 'backups.run');
    return delay([...(BACKUP_SCHEDULES ?? [])].filter(() => tenantId === TENANTS[0]!.id));
  }

  async runBackupNow(tenantId: string, routerId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'backups.run');
    const r = (ROUTERS[tenantId] ?? []).find((x) => x.id === routerId);
    if (!r) fail('not_found', 'Data tidak ditemukan');
    const unreachable = r.health.vpn === 'down';
    const job = this.newJob(
      'backup_router',
      routerId,
      'Pengguna Dev',
      [['connect', 600], ['export', 1100], ['transfer', 1200], ['verify', 800]],
      unreachable ? 'failed' : 'succeeded',
      { total: 1, done: 0 },
      'router_unreachable',
    );
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` }, 250);
  }

  /* ---------- Monitoring ---------- */

  async listMonitorStatus(tenantId: string): Promise<MonitorStatus[]> {
    this.permissionOr403(tenantId, 'routers.read');
    return delay([...(MONITOR[tenantId] ?? [])]);
  }

  /* ---------- RADIUS ---------- */

  listRadiusAccounts(
    tenantId: string,
    filters: { query?: string; state?: string },
    page: PageParams,
  ): Promise<CursorPage<RadiusAccountRow>> {
    this.permissionOr403(tenantId, 'routers.read');
    let items = [...(RADIUS_ACCOUNTS[tenantId] ?? [])];
    if (filters.query) {
      const q = filters.query.toLowerCase();
      items = items.filter((a) => a.username.toLowerCase().includes(q));
    }
    if (filters.state) items = items.filter((a) => a.state === filters.state);
    return delay(paginate(items, page));
  }

  async listRadiusRouterStatus(tenantId: string): Promise<RadiusRouterStatus[]> {
    this.permissionOr403(tenantId, 'routers.read');
    return delay([...(RADIUS_STATUS[tenantId] ?? [])]);
  }

  async getRadiusRouterStatus(tenantId: string, routerId: string): Promise<RadiusRouterStatus> {
    const s = (RADIUS_STATUS[tenantId] ?? []).find((x) => x.router_id === routerId);
    if (!s) fail('not_found', 'Data tidak ditemukan');
    return delay(s);
  }

  async startRadiusCutover(tenantId: string, routerId: string, _opts?: MutationOptions): Promise<JobAccepted> {
    this.permissionOr403(tenantId, 'radius.cutover');
    if (!this.reauthUntil || new Date(this.reauthUntil) < new Date()) {
      fail('forbidden', 'Cutover memerlukan konfirmasi identitas (MFA + reautentikasi)');
    }
    const s = (RADIUS_STATUS[tenantId] ?? []).find((x) => x.router_id === routerId);
    if (!s) fail('not_found', 'Data tidak ditemukan');
    const job = this.newJob(
      'radius_cutover_step',
      routerId,
      'Pengguna Dev',
      [['preflight', 900], ['install_client', 1400], ['shadow', 1300], ['authoritative', 1100], ['verify', 800]],
      'succeeded',
      { total: 5, done: 0 },
    );
    return delay({ job_id: job.id, status_url: `/api/v1/jobs/${job.id}` }, 250);
  }

  async suspendRadiusAccount(tenantId: string, accountId: string, _opts?: MutationOptions): Promise<void> {
    this.permissionOr403(tenantId, 'services.activate');
    const acc = (RADIUS_ACCOUNTS[tenantId] ?? []).find((a) => a.id === accountId);
    if (!acc) fail('not_found', 'Data tidak ditemukan');
    if (acc.state !== 'active') fail('conflict', 'Transisi state tidak diizinkan');
    acc.state = 'suspended';
    this.newJob('suspend_service', acc.restricting_router_id, 'Pengguna Dev', [['disconnect', 700], ['verify', 600]], 'succeeded', { total: 1, done: 0 });
    return delay(undefined, 200);
  }

  async activateRadiusAccount(tenantId: string, accountId: string, _opts?: MutationOptions): Promise<void> {
    this.permissionOr403(tenantId, 'services.activate');
    const acc = (RADIUS_ACCOUNTS[tenantId] ?? []).find((a) => a.id === accountId);
    if (!acc) fail('not_found', 'Data tidak ditemukan');
    // Paritas backend: state sama → idempoten (204 tanpa perubahan).
    if (acc.state === 'suspended') {
      acc.state = 'active';
      this.newJob('apply_account_attributes', acc.restricting_router_id, 'Pengguna Dev', [['apply', 800], ['verify', 600]], 'succeeded', { total: 1, done: 0 });
    }
    this.newJob('apply_account_attributes', acc.restricting_router_id, 'Pengguna Dev', [['apply', 800], ['verify', 600]], 'succeeded', { total: 1, done: 0 });
    return delay(undefined, 200);
  }

  /* ---------- Subscription ---------- */

  async getSubscription(tenantId: string): Promise<SubscriptionInfo> {
    const s = SUBSCRIPTIONS[tenantId];
    if (!s) fail('not_found', 'Data tidak ditemukan');
    return delay({ ...s });
  }

  async getPlans(): Promise<PlanInfo[]> {
    // Harga dari PRODUCT.md §3 — sumber kebenaran; ditampilkan via mock untuk dev.
    return delay([
      { code: 'free', routers_limit: 1, services_limit: 50, monthly_price: '0.00', yearly_price: '0.00' },
      { code: 'bronze', routers_limit: 2, services_limit: 150, monthly_price: '500000.00', yearly_price: '5000000.00' },
      { code: 'silver', routers_limit: 3, services_limit: 300, monthly_price: '1000000.00', yearly_price: '10000000.00' },
      { code: 'gold', routers_limit: 4, services_limit: 500, monthly_price: '1500000.00', yearly_price: '15000000.00' },
      { code: 'diamond', routers_limit: 5, services_limit: 750, monthly_price: '2000000.00', yearly_price: '20000000.00' },
      { code: 'platinum', routers_limit: null, services_limit: null, monthly_price: '4000000.00', yearly_price: '40000000.00' },
    ]);
  }

  async requestQuotation(tenantId: string, planCode: string, term: 'monthly' | 'yearly', _opts?: MutationOptions): Promise<{ quotation_id: string; invoice_id: string; amount: string }> {
    this.permissionOr403(tenantId, 'subscription.manage');
    const plan = [
      { code: 'bronze', m: '500000.00', y: '5000000.00' },
      { code: 'silver', m: '1000000.00', y: '10000000.00' },
      { code: 'gold', m: '1500000.00', y: '15000000.00' },
      { code: 'diamond', m: '2000000.00', y: '20000000.00' },
      { code: 'platinum', m: '4000000.00', y: '40000000.00' },
    ].find((p) => p.code === planCode);
    if (!plan) fail('validation_error', 'Paket tidak ditemukan');
    const qid = `q-${Math.random().toString(36).slice(2, 6)}`;
    const iid = `sinv-${Math.floor(Math.random() * 9000 + 1000)}`;
    void tenantId;
    return delay({ quotation_id: qid, invoice_id: iid, amount: term === 'monthly' ? plan.m : plan.y }, 350);
  }

  async submitPaymentProof(_tenantId: string, invoiceId: string, input: { file_name: string; file_size: number; mime: string }, _opts?: MutationOptions): Promise<{ submission_id: string; state: string }> {
    const allowed = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!allowed.includes(input.mime)) {
      fail('validation_error', 'Format bukti tidak didukung', {
        file: [{ code: 'mime', message: 'JPEG, PNG, atau PDF maksimum 5 MiB' }],
      });
    }
    if (input.file_size > 5 * 1024 * 1024) {
      fail('validation_error', 'Bukti melebihi 5 MiB', {
        file: [{ code: 'max_size', message: 'Maksimum 5 MiB' }],
      });
    }
    const id = `sub-${Math.random().toString(36).slice(2, 6)}`;
    this.submissions.unshift({
      id,
      tenant_display_name: 'RT Net Nusantara',
      saas_invoice_id: invoiceId,
      plan_code: 'silver',
      period_months: 1,
      amount: '1000000.00',
      submitted_at: new Date().toISOString(),
      state: 'submitted',
      assignee: null,
    });
    return delay({ submission_id: id, state: 'submitted' }, 400);
  }

  /* ---------- Platform admin ---------- */

  async listPlatformSubmissions(queue: PlatformPaymentSubmission['state']): Promise<PlatformPaymentSubmission[]> {
    return delay(this.submissions.filter((s) => s.state === queue));
  }

  async approvePlatformSubmission(submissionId: string, _opts?: MutationOptions): Promise<void> {
    const s = this.submissions.find((x) => x.id === submissionId);
    if (!s) fail('not_found', 'Data tidak ditemukan');
    if (s.state !== 'submitted' && s.state !== 'reviewing') fail('conflict', 'Keputusan untuk berkas ini sudah ada');
    s.state = 'approved';
    s.assignee = 'Admin Platform 1';
    return delay(undefined, 250);
  }

  async rejectPlatformSubmission(submissionId: string, reason: string, _opts?: MutationOptions): Promise<void> {
    const s = this.submissions.find((x) => x.id === submissionId);
    if (!s) fail('not_found', 'Data tidak ditemukan');
    if (!reason.trim()) fail('validation_error', 'Alasan wajib diisi', { reason: [{ code: 'required', message: 'Alasan penolakan wajib diisi' }] });
    s.state = 'rejected';
    s.assignee = 'Admin Platform 1';
    return delay(undefined, 250);
  }

  async requestRevisionPlatformSubmission(submissionId: string, reason: string, _opts?: MutationOptions): Promise<void> {
    const s = this.submissions.find((x) => x.id === submissionId);
    if (!s) fail('not_found', 'Data tidak ditemukan');
    if (!reason.trim()) fail('validation_error', 'Alasan wajib diisi', { reason: [{ code: 'required', message: 'Alasan permintaan perbaikan wajib diisi' }] });
    s.state = 'revision_requested';
    s.assignee = 'Admin Platform 1';
    return delay(undefined, 250);
  }

  /* ---------- Audit ---------- */

  listAuditTimeline(tenantId: string, targetId: string | null, page: PageParams): Promise<CursorPage<AuditEntry>> {
    let items = AUDIT[tenantId] ?? [];
    if (targetId) items = items.filter((a) => a.target_display === targetId);
    return delay(paginate(items, page));
  }

  /* ---------- Billing internet M6 — U09/U10 (TK-604) ---------- */

  async listInvoices(tenantId: string, filters: InvoiceListFilters, page: PageParams): Promise<CursorPage<InternetInvoice>> {
    this.permissionOr403(tenantId, 'customers.read');
    let items = [...(this.billingInvoices[tenantId] ?? [])].sort((a, b) => b.issued_at.localeCompare(a.issued_at));
    if (filters.state) items = items.filter((i) => i.state === filters.state);
    if (filters.kind) items = items.filter((i) => i.kind === filters.kind);
    if (filters.service_id) items = items.filter((i) => i.service_id === filters.service_id);
    if (filters.period_from) items = items.filter((i) => i.period_start >= filters.period_from!);
    if (filters.period_to) items = items.filter((i) => i.period_end <= filters.period_to!);
    return delay(paginate(items, page));
  }

  async getInvoice(tenantId: string, invoiceId: string): Promise<InternetInvoiceDetail> {
    this.permissionOr403(tenantId, 'customers.read');
    const inv = (this.billingInvoices[tenantId] ?? []).find((i) => i.id === invoiceId);
    if (!inv) fail('not_found', 'Data tidak ditemukan');
    return delay({
      ...inv,
      lines: [{ line_kind: 'subscription', name: 'Langganan internet', amount: inv.total_amount, ordinal: 0 }],
    });
  }

  async getInvoiceAging(tenantId: string): Promise<InvoiceAgingReport> {
    this.permissionOr403(tenantId, 'customers.read');
    const report = BILLING_AGING[tenantId];
    if (!report) {
      return delay({ as_of: MOCK_NOW.toISOString().slice(0, 10), totals: { not_due: { count: 0, outstanding: '0.00' }, current: { count: 0, outstanding: '0.00' }, d31_60: { count: 0, outstanding: '0.00' }, d61_90: { count: 0, outstanding: '0.00' }, d90_plus: { count: 0, outstanding: '0.00' } }, items: [] });
    }
    return delay(report as InvoiceAgingReport);
  }

  async listPayments(tenantId: string, filters: PaymentListFilters, page: PageParams): Promise<CursorPage<InternetPayment>> {
    this.permissionOr403(tenantId, 'customers.read');
    let items = [...(this.billingPayments[tenantId] ?? [])].sort((a, b) => b.submitted_at.localeCompare(a.submitted_at));
    if (filters.state) items = items.filter((p) => p.state === filters.state);
    if (filters.method) items = items.filter((p) => p.method === filters.method);
    return delay(paginate(items, page));
  }

  async getPayment(tenantId: string, paymentId: string): Promise<InternetPaymentDetail> {
    this.permissionOr403(tenantId, 'customers.read');
    const pay = (this.billingPayments[tenantId] ?? []).find((p) => p.id === paymentId);
    if (!pay) fail('not_found', 'Data tidak ditemukan');
    return delay({ ...pay, allocations: BILLING_PAYMENT_ALLOCATIONS[paymentId] ?? [] });
  }

  async recordInternetPayment(tenantId: string, input: RecordPaymentInput): Promise<InternetPayment> {
    this.permissionOr403(tenantId, 'payments.verify');
    const amount = Number(input.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      fail('validation_error', 'Nominal tidak valid', { amount: [{ code: 'invalid', message: 'Nominal harus > 0' }] });
    }
    if ((input.method === 'bank_transfer' || input.method === 'ewallet') && !input.file_b64) {
      fail('validation_error', 'Bukti wajib diunggah', { file_b64: [{ code: 'required', message: 'Bukti transfer/e-wallet wajib diunggah' }] });
    }
    const payment: InternetPayment = {
      id: `pay-mock-${++this.billingSeq}`,
      method: input.method,
      state: 'submitted',
      amount: amount.toFixed(2),
      allocated_amount: '0.00',
      credit: '0.00',
      external_ref: input.external_ref ?? null,
      has_proof: Boolean(input.file_b64),
      collector_display: input.collector_display ?? null,
      submitted_at: MOCK_NOW.toISOString(),
      verified_at: null,
      rejected_reason: null,
    };
    (this.billingPayments[tenantId] ??= []).unshift(payment);
    return delay(payment);
  }

  async verifyInternetPayment(
    tenantId: string,
    paymentId: string,
    input: { allocations: Array<{ invoice_id: string; amount: string }> },
  ): Promise<InternetPaymentDetail> {
    this.permissionOr403(tenantId, 'payments.verify');
    const pay = (this.billingPayments[tenantId] ?? []).find((p) => p.id === paymentId);
    if (!pay) fail('not_found', 'Data tidak ditemukan');
    if (pay.state !== 'submitted') fail('conflict', 'Keputusan sudah diambil untuk pembayaran ini');
    const merged = new Map<string, number>();
    let total = 0;
    for (const a of input.allocations) {
      const amt = Number(a.amount);
      if (!Number.isFinite(amt) || amt <= 0) fail('validation_error', 'Alokasi tidak sah', { allocations: [{ code: 'invalid', message: 'Nominal alokasi harus > 0' }] });
      merged.set(a.invoice_id, (merged.get(a.invoice_id) ?? 0) + amt);
      total += amt;
    }
    if (total > Number(pay.amount)) fail('conflict', 'Alokasi melebihi nilai pembayaran');
    const applied: Array<{ invoice_id: string; invoice_number: string; amount: string; allocated_at: string }> = [];
    for (const [invoiceId, amt] of merged) {
      const inv = (this.billingInvoices[tenantId] ?? []).find((i) => i.id === invoiceId);
      if (!inv) fail('not_found', 'Data tidak ditemukan');
      if (inv.state !== 'open' && inv.state !== 'partial') fail('conflict', 'Invoice tidak dapat dibayar');
      if (amt > Number(inv.outstanding)) fail('conflict', 'Alokasi melebihi sisa tagihan');
      const paid = Number(inv.paid_amount) + amt;
      inv.paid_amount = paid.toFixed(2);
      inv.outstanding = (Number(inv.total_amount) - paid).toFixed(2);
      inv.state = inv.outstanding === '0.00' ? 'paid' : 'partial';
      applied.push({ invoice_id: invoiceId, invoice_number: inv.doc_number, amount: amt.toFixed(2), allocated_at: MOCK_NOW.toISOString() });
    }
    pay.state = 'verified';
    pay.allocated_amount = total.toFixed(2);
    pay.credit = (Number(pay.amount) - total).toFixed(2);
    pay.verified_at = MOCK_NOW.toISOString();
    BILLING_PAYMENT_ALLOCATIONS[paymentId] = applied;
    // Kwitansi terbit saat verify (BIL-08 paritas).
    (this.billingDocuments[tenantId] ??= []).unshift({
      id: `doc-rcp-mock-${++this.billingSeq}`,
      kind: 'receipt',
      doc_number: `RCP-ns01-202611-${String(this.billingSeq).padStart(4, '0')}`,
      ref_type: 'billing_payment',
      ref_id: paymentId,
      locale: 'id',
      timezone: 'Asia/Jakarta',
      template_version: '1',
      sha256: 'f'.repeat(64),
      size_bytes: 38220,
      issued_at: MOCK_NOW.toISOString(),
    });
    return delay({ ...pay, allocations: applied });
  }

  async rejectInternetPayment(tenantId: string, paymentId: string, reason: string): Promise<InternetPayment> {
    this.permissionOr403(tenantId, 'payments.verify');
    const pay = (this.billingPayments[tenantId] ?? []).find((p) => p.id === paymentId);
    if (!pay) fail('not_found', 'Data tidak ditemukan');
    if (pay.state !== 'submitted') fail('conflict', 'Keputusan sudah diambil untuk pembayaran ini');
    if (!reason.trim()) fail('validation_error', 'Alasan wajib diisi', { reason: [{ code: 'required', message: 'Alasan penolakan wajib diisi' }] });
    pay.state = 'rejected';
    pay.rejected_reason = reason.trim();
    return delay(pay);
  }

  async listDocuments(
    tenantId: string,
    filters: { kind?: string; ref_type?: string; ref_id?: string },
    page: PageParams,
  ): Promise<CursorPage<IssuedDocumentInfo>> {
    this.permissionOr403(tenantId, 'customers.read');
    let items = [...(this.billingDocuments[tenantId] ?? [])].sort((a, b) => b.issued_at.localeCompare(a.issued_at));
    if (filters.kind) items = items.filter((d) => d.kind === filters.kind);
    if (filters.ref_type) items = items.filter((d) => d.ref_type === filters.ref_type);
    if (filters.ref_id) items = items.filter((d) => d.ref_id === filters.ref_id);
    return delay(paginate(items, page));
  }
}

export const MOCK_NOW_ISO = MOCK_NOW.toISOString();
