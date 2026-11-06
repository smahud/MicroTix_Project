import type {
  BackupArtifact,
  BackupSchedule,
  DiscoveredAccount,
  IdentityConflictCandidate,
  InternetInvoice,
  InternetPayment,
  IssuedDocumentInfo,
  JobRecord,
  MonitorStatus,
  RadiusAccountRow,
  RadiusRouterStatus,
  RouterSummary,
  ServiceDetail,
  ServiceRow,
  SubscriptionInfo,
  TenantSummary,
} from '../contracts';

/**
 * FIXTURES PENGEMBANGAN — bukan data produksi (IMPLEMENTATION_PLAN M0: seed dua tenant sintetis).
 * Deterministik: tanggal tetap relatif ke 2026-11-05 (zona Asia/Jakarta).
 * Backend nyata belum tersedia; seluruh angka di bawah hanya untuk pengembangan UI.
 */

export const MOCK_NOW = new Date('2026-11-05T09:30:00+07:00');

function minutesAgo(min: number): string {
  return new Date(MOCK_NOW.getTime() - min * 60_000).toISOString();
}
function daysAgo(d: number, h = 0): string {
  return new Date(MOCK_NOW.getTime() - (d * 86_400_000 + h * 3_600_000)).toISOString();
}

export const TENANTS: TenantSummary[] = [
  { id: 'b3f0a2de-1111-4000-8000-tenant01', display_name: 'RT Net Nusantara', role: 'owner' },
  { id: 'c7d1e3ab-2222-4000-8000-tenant02', display_name: 'RW Net Cemara', role: 'technician' },
];

export const ROUTERS: Record<string, RouterSummary[]> = {
  'b3f0a2de-1111-4000-8000-tenant01': [
    {
      id: 'rtr-101',
      display_name: 'Router Utama Kantor',
      router_code: 'RTR-UTAMA',
      location: 'Kantor — Jl. Melati 12',
      model: 'RB4011iGS+',
      routeros_version: '7.15.3',
      mode: 'managed',
      health: { vpn: 'up', api: 'up', observed_at: minutesAgo(2) },
      enforcement_mode: 'radius_authoritative',
      services_count: 3,
    },
    {
      id: 'rtr-102',
      display_name: 'Router Tower Selatan',
      router_code: 'RTR-TOWER',
      location: 'Tower Selatan',
      model: 'hAP ax3',
      routeros_version: '7.14.2',
      mode: 'read_only',
      health: { vpn: 'up', api: 'down', observed_at: minutesAgo(11) },
      enforcement_mode: 'radius_shadow',
      services_count: 1,
    },
    {
      id: 'rtr-103',
      display_name: 'Router Lama Gudang',
      router_code: 'RTR-GDG',
      location: 'Gudang Belakang',
      model: 'RB2011UiAS',
      routeros_version: '6.49.13',
      mode: 'read_only',
      health: { vpn: 'down', api: 'unknown', observed_at: minutesAgo(74) },
      enforcement_mode: 'local',
      services_count: 0,
    },
  ],
  'c7d1e3ab-2222-4000-8000-tenant02': [
    {
      id: 'rtr-201',
      display_name: 'Router Utama Cemara',
      router_code: 'RTR-CMR',
      location: 'Pos 1',
      model: 'hEX S',
      routeros_version: '7.16',
      mode: 'managed',
      health: { vpn: 'up', api: 'up', observed_at: minutesAgo(3) },
      enforcement_mode: 'local',
      services_count: 2,
    },
  ],
};

const SERVICES_BASE: ServiceRow[] = [
  {
    id: 'svc-001',
    service_code: 'SVC-001',
    customer_code: 'CUS-1001',
    customer_name: 'Budi Santoso',
    username: 'budi.santoso',
    kind: 'pppoe',
    package_name: 'Paket Rumah 20 Mbps',
    router_id: 'rtr-101',
    router_display_name: 'Router Utama Kantor',
    lifecycle: 'provisioned',
    payment: 'paid',
    isolation: 'normal',
    connection: 'online',
    job: 'none',
    incomplete_mapping: false,
  },
  {
    id: 'svc-002',
    service_code: 'SVC-002',
    customer_code: 'CUS-1002',
    customer_name: 'Siti Aminah',
    username: 'siti.aminah',
    kind: 'pppoe',
    package_name: 'Paket Rumah 20 Mbps',
    router_id: 'rtr-101',
    router_display_name: 'Router Utama Kantor',
    lifecycle: 'provisioned',
    payment: 'unbilled',
    isolation: 'isolated',
    connection: 'offline',
    job: 'none',
    incomplete_mapping: false,
  },
  {
    id: 'svc-003',
    service_code: 'SVC-003',
    customer_code: 'CUS-1003',
    customer_name: 'Warung Kopi Melati (Rina)',
    username: 'warung.melati',
    kind: 'pppoe',
    package_name: 'Paket Bisnis 50 Mbps',
    router_id: 'rtr-102',
    router_display_name: 'Router Tower Selatan',
    lifecycle: 'provisioned',
    payment: 'partial',
    isolation: 'awaiting_verification',
    connection: 'online',
    job: 'queued',
    incomplete_mapping: false,
  },
  {
    id: 'svc-004',
    service_code: 'SVC-004',
    customer_code: 'CUS-1004',
    customer_name: 'Agus Wijaya',
    username: 'agus.wijaya',
    kind: 'pppoe',
    package_name: null,
    router_id: 'rtr-101',
    router_display_name: 'Router Utama Kantor',
    lifecycle: 'provisioned',
    payment: 'not_billed',
    isolation: 'normal',
    connection: 'unknown',
    job: 'none',
    incomplete_mapping: true,
  },
  {
    id: 'svc-005',
    service_code: 'SVC-005',
    customer_code: 'CUS-1005',
    customer_name: 'Dewi Lestari',
    username: 'dewi.lestari',
    kind: 'pppoe',
    package_name: 'Paket Rumah 10 Mbps',
    router_id: 'rtr-101',
    router_display_name: 'Router Utama Kantor',
    lifecycle: 'provisioned',
    payment: 'paid',
    isolation: 'normal',
    connection: 'offline',
    job: 'none',
    incomplete_mapping: false,
  },
  {
    id: 'svc-018',
    service_code: 'SVC-018',
    customer_code: 'CUS-1018',
    customer_name: 'Kos Putri Mawar (Ibu Yanti)',
    username: 'kos.mawar',
    kind: 'pppoe',
    package_name: 'Paket Kos 30 Mbps',
    router_id: 'rtr-102',
    router_display_name: 'Router Tower Selatan',
    lifecycle: 'provisioned',
    payment: 'paid',
    isolation: 'hold',
    connection: 'online',
    job: 'needs_review',
    incomplete_mapping: false,
  },
];

export const SERVICES: Record<string, ServiceRow[]> = {
  'b3f0a2de-1111-4000-8000-tenant01': SERVICES_BASE,
  'c7d1e3ab-2222-4000-8000-tenant02': SERVICES_BASE.filter((s) =>
    ['svc-001', 'svc-005'].includes(s.id),
  ).map((s) => ({
    ...s,
    router_id: 'rtr-201',
    router_display_name: 'Router Utama Cemara',
  })),
};

export const SERVICE_DETAILS: Record<string, Partial<ServiceDetail>> = {
  'svc-002': {
    start_date: '2026-05-01',
    contact: '0812-3456-7802',
    address: 'Jl. Kenanga 4, RT 03/RW 05',
    access: {
      username: 'siti.aminah',
      state: 'suspended',
      credential_state: 'ready',
      session_limit: 1,
      mac_locked: true,
      last_active_session_at: daysAgo(3, 2),
      restricting_router_id: 'rtr-101',
    },
  },
  'svc-004': {
    start_date: '2026-09-12',
    contact: '0857-1122-3344',
    address: null,
    access: {
      username: 'agus.wijaya',
      state: 'active',
      credential_state: 'unknown',
      session_limit: null,
      mac_locked: null,
      last_active_session_at: null,
      restricting_router_id: 'rtr-101',
    },
  },
  'svc-018': {
    start_date: '2024-08-01',
    contact: '0821-9988-7766',
    address: 'Jl. Mawar 21',
    access: {
      username: 'kos.mawar',
      state: 'active',
      credential_state: 'ready',
      session_limit: 2,
      mac_locked: false,
      last_active_session_at: minutesAgo(26),
      restricting_router_id: 'rtr-102',
    },
  },
};

export const MONITOR: Record<string, MonitorStatus[]> = {
  'b3f0a2de-1111-4000-8000-tenant01': [
    {
      router_id: 'rtr-101',
      group: 'healthy',
      observed_at: minutesAgo(2),
      source: 'collector',
      interfaces: [
        { name: 'ether1 (WAN)', enabled: true, rx_bytes_s: 41_200_000, tx_bytes_s: 8_900_000, last_sample_at: minutesAgo(2) },
        { name: 'ether2 (LAN Pelanggan)', enabled: true, rx_bytes_s: 9_100_000, tx_bytes_s: 39_800_000, last_sample_at: minutesAgo(2) },
      ],
      radius: { auth_success_ratio_24h: 0.986, inbound_sessions_24h: 128, last_accounting_at: minutesAgo(1) },
    },
    {
      router_id: 'rtr-102',
      group: 'management_unreachable',
      observed_at: minutesAgo(11),
      source: 'collector',
      interfaces: [
        { name: 'ether1 (WAN)', enabled: true, rx_bytes_s: null, tx_bytes_s: null, last_sample_at: minutesAgo(11) },
      ],
      radius: { auth_success_ratio_24h: 0.71, inbound_sessions_24h: 12, last_accounting_at: minutesAgo(14) },
    },
    {
      router_id: 'rtr-103',
      group: 'stale_data',
      observed_at: minutesAgo(74),
      source: 'cache',
      interfaces: [
        { name: 'ether1', enabled: true, rx_bytes_s: 2_400_000, tx_bytes_s: 1_100_000, last_sample_at: minutesAgo(74) },
      ],
      radius: null,
    },
  ],
  'c7d1e3ab-2222-4000-8000-tenant02': [
    {
      router_id: 'rtr-201',
      group: 'healthy',
      observed_at: minutesAgo(3),
      source: 'collector',
      interfaces: [
        { name: 'ether1 (WAN)', enabled: true, rx_bytes_s: 18_400_000, tx_bytes_s: 4_200_000, last_sample_at: minutesAgo(3) },
      ],
      radius: { auth_success_ratio_24h: 0.99, inbound_sessions_24h: 42, last_accounting_at: minutesAgo(2) },
    },
  ],
};

export const BACKUP_SCHEDULES: BackupSchedule[] = [
  { router_id: 'rtr-101', timezone: 'Asia/Jakarta', frequency: 'daily', time_local: '03:00', artifact_type: 'binary', notification_enabled: true },
];

export const BACKUP_ARTIFACTS: Record<string, BackupArtifact[]> = {
  'b3f0a2de-1111-4000-8000-tenant01': [
    { id: 'bk-0100', router_id: 'rtr-101', generation: 100, created_at: daysAgo(1), category: 'routine', size_bytes: 3_650_000, transfer_state: 'committed', encrypted: true },
    { id: 'bk-0099', router_id: 'rtr-101', generation: 99, created_at: daysAgo(2), category: 'routine', size_bytes: 3_610_000, transfer_state: 'committed', encrypted: true },
    { id: 'bk-0098', router_id: 'rtr-101', generation: 98, created_at: daysAgo(3), category: 'routine', size_bytes: 3_598_000, transfer_state: 'failed', encrypted: true },
    { id: 'bk-0042', router_id: 'rtr-102', generation: 42, created_at: daysAgo(1, 2), category: 'pre_change', size_bytes: 2_940_000, transfer_state: 'committed', encrypted: true },
  ],
};

export const RADIUS_ACCOUNTS: Record<string, RadiusAccountRow[]> = {
  'b3f0a2de-1111-4000-8000-tenant01': [
    { id: 'acc-001', username: 'budi.santoso', kind: 'pppoe', state: 'active', credential_state: 'ready', service_id: 'svc-001', service_code: 'SVC-001', customer_name: 'Budi Santoso', package_name: 'Paket Rumah 20 Mbps', restricting_router_id: null, last_active_session_at: minutesAgo(5) },
    { id: 'acc-002', username: 'siti.aminah', kind: 'pppoe', state: 'suspended', credential_state: 'ready', service_id: 'svc-002', service_code: 'SVC-002', customer_name: 'Siti Aminah', package_name: 'Paket Rumah 20 Mbps', restricting_router_id: 'rtr-101', last_active_session_at: daysAgo(3, 2) },
    { id: 'acc-003', username: 'warung.melati', kind: 'pppoe', state: 'active', credential_state: 'rotation_pending', service_id: 'svc-003', service_code: 'SVC-003', customer_name: 'Warung Kopi Melati (Rina)', package_name: 'Paket Bisnis 50 Mbps', restricting_router_id: 'rtr-102', last_active_session_at: minutesAgo(38) },
    { id: 'acc-004', username: 'agus.wijaya', kind: 'pppoe', state: 'active', credential_state: 'unknown', service_id: 'svc-004', service_code: 'SVC-004', customer_name: 'Agus Wijaya', package_name: null, restricting_router_id: 'rtr-101', last_active_session_at: null },
    { id: 'acc-005', username: 'dewi.lestari', kind: 'pppoe', state: 'active', credential_state: 'ready', service_id: 'svc-005', service_code: 'SVC-005', customer_name: 'Dewi Lestari', package_name: 'Paket Rumah 10 Mbps', restricting_router_id: null, last_active_session_at: daysAgo(1) },
    { id: 'acc-018', username: 'kos.mawar', kind: 'pppoe', state: 'active', credential_state: 'ready', service_id: 'svc-018', service_code: 'SVC-018', customer_name: 'Kos Putri Mawar (Ibu Yanti)', package_name: 'Paket Kos 30 Mbps', restricting_router_id: 'rtr-102', last_active_session_at: minutesAgo(26) },
    { id: 'acc-201', username: 'hotspot-tamua1', kind: 'hotspot', state: 'active', credential_state: 'ready', service_id: 'svc-004', service_code: 'SVC-004', customer_name: 'Agus Wijaya', package_name: 'Voucher Harian', restricting_router_id: 'rtr-101', last_active_session_at: minutesAgo(12) },
  ],
};

export const RADIUS_STATUS: Record<string, RadiusRouterStatus[]> = {
  'b3f0a2de-1111-4000-8000-tenant01': [
    { router_id: 'rtr-101', enforcement_mode: 'radius_authoritative', migrated_accounts: 6, auth_success_ratio_24h: 0.986, inbound_sessions_24h: 128, last_accounting_at: minutesAgo(1), radius_primary: '10.10.0.5', radius_secondary: '10.10.0.6', client_status: 'ok' },
    { router_id: 'rtr-102', enforcement_mode: 'radius_shadow', migrated_accounts: 2, auth_success_ratio_24h: 0.71, inbound_sessions_24h: 12, last_accounting_at: minutesAgo(14), radius_primary: '10.10.0.5', radius_secondary: '10.10.0.6', client_status: 'degraded' },
    { router_id: 'rtr-103', enforcement_mode: 'local', migrated_accounts: 0, auth_success_ratio_24h: null, inbound_sessions_24h: null, last_accounting_at: null, radius_primary: '10.10.0.5', radius_secondary: '10.10.0.6', client_status: 'missing_client' },
  ],
};

export const DISCOVERED: DiscoveredAccount[] = [
  { id: 'dsc-01', username: 'budi.santoso', kind: 'pppoe', profile: 'PPPF-20M', service: 'pppoe', disabled_on_router: false, comment: 'rumah budi', state: 'discovered' },
  { id: 'dsc-02', username: 'siti.aminah', kind: 'pppoe', profile: 'PPPF-20M', service: 'pppoe', disabled_on_router: true, comment: null, state: 'discovered' },
  { id: 'dsc-03', username: 'warung.melati', kind: 'pppoe', profile: 'PPPF-50M', service: 'pppoe', disabled_on_router: false, comment: 'bisnis', state: 'discovered' },
  { id: 'dsc-04', username: 'agus.wijaya', kind: 'pppoe', profile: 'PPPF-DFT', service: 'pppoe', disabled_on_router: false, comment: null, state: 'discovered' },
  { id: 'dsc-05', username: 'dewi.lestari', kind: 'pppoe', profile: 'PPPF-10M', service: 'pppoe', disabled_on_router: false, comment: null, state: 'discovered' },
  { id: 'dsc-06', username: 'kos.mawar', kind: 'pppoe', profile: 'PPPF-30M', service: 'pppoe', disabled_on_router: false, comment: 'kos 2 lantai', state: 'discovered' },
  { id: 'dsc-07', username: 'Budi.Santoso', kind: 'pppoe', profile: 'PPPF-20M', service: 'pppoe', disabled_on_router: false, comment: 'duplikat tower', state: 'conflict' },
  { id: 'dsc-08', username: 'guest-hotspot-07', kind: 'hotspot', profile: 'HS-DAILY', service: 'hotspot', disabled_on_router: false, comment: null, state: 'discovered' },
  { id: 'dsc-09', username: 'ip-static-3', kind: 'pppoe', profile: 'PPPF-DFT', service: 'any', disabled_on_router: false, comment: 'tampaknya lease', state: 'discovered' },
];

export const IDENTITY_CONFLICTS: IdentityConflictCandidate[] = [
  {
    candidate_group_id: 'grp-budi',
    usernames: ['budi.santoso', 'Budi.Santoso'],
    routers: ['rtr-101', 'rtr-102'],
    kind: 'structural_match',
    resolution: null,
  },
];

export const SUBSCRIPTIONS: Record<string, SubscriptionInfo> = {
  'b3f0a2de-1111-4000-8000-tenant01': {
    plan: {
      code: 'silver',
      routers_limit: 3,
      services_limit: 300,
      monthly_price: '1000000.00',
      yearly_price: '10000000.00',
    },
    state: 'active',
    period_start: '2026-10-12',
    period_end: '2026-11-12',
    usage: { routers_used: 3, services_used: 6, draft_used: 4, draft_cap: 75 },
    pending_invoice: null,
  },
  'c7d1e3ab-2222-4000-8000-tenant02': {
    plan: {
      code: 'free',
      routers_limit: 1,
      services_limit: 50,
      monthly_price: '0.00',
      yearly_price: '0.00',
    },
    state: 'free',
    period_start: null,
    period_end: null,
    usage: { routers_used: 1, services_used: 2, draft_used: 1, draft_cap: 13 },
    pending_invoice: null,
  },
};

export const AUDIT: Record<string, Array<{ id: string; at: string; actor_display: string; action_code: string; target_display: string | null }>> = {
  'b3f0a2de-1111-4000-8000-tenant01': [
    { id: 'aud-01', at: minutesAgo(6), actor_display: 'Huda (Owner)', action_code: 'service.isolation.requested', target_display: 'SVC-002' },
    { id: 'aud-02', at: minutesAgo(41), actor_display: 'Huda (Owner)', action_code: 'radius.account.reveal', target_display: 'acc-003' },
    { id: 'aud-03', at: daysAgo(1), actor_display: 'Wawan (Teknisi)', action_code: 'backup.manual_run', target_display: 'rtr-101' },
    { id: 'aud-04', at: daysAgo(2), actor_display: 'Huda (Owner)', action_code: 'migration.commit', target_display: 'mig-9001' },
  ],
};

/** Pekerjaan awal (job center U16). */
export const JOBS_SEED: JobRecord[] = [
  {
    id: 'job-5010',
    kind: 'backup_router',
    state: 'succeeded',
    actor_display: 'Wawan (Teknisi)',
    created_at: daysAgo(1),
    updated_at: daysAgo(1),
    router_id: 'rtr-101',
    phase_label_code: null,
    items_total: 1,
    items_done: 1,
    error_code: null,
    request_id: 'req-8b41',
    retryable: false,
  },
  {
    id: 'job-5011',
    kind: 'backup_router',
    state: 'failed',
    actor_display: 'Wawan (Teknisi)',
    created_at: daysAgo(3),
    updated_at: daysAgo(3),
    router_id: 'rtr-101',
    phase_label_code: 'transfer',
    items_total: 1,
    items_done: 0,
    error_code: 'router_unreachable',
    request_id: 'req-8b42',
    retryable: true,
  },
  {
    id: 'job-5012',
    kind: 'radius_cutover_step',
    state: 'uncertain',
    actor_display: 'Huda (Owner)',
    created_at: daysAgo(0, 5),
    updated_at: daysAgo(0, 4),
    router_id: 'rtr-102',
    phase_label_code: 'install_client',
    items_total: 3,
    items_done: 2,
    error_code: null,
    request_id: 'req-8b43',
    retryable: false,
  },
  {
    id: 'job-5013',
    kind: 'import_commit',
    state: 'recovery_required',
    actor_display: 'Huda (Owner)',
    created_at: daysAgo(0, 8),
    updated_at: daysAgo(0, 6),
    router_id: null,
    phase_label_code: 'commit',
    items_total: 120,
    items_done: 87,
    error_code: 'dependency_unavailable',
    request_id: 'req-8b44',
    retryable: false,
  },
  {
    id: 'job-5014',
    kind: 'suspend_service',
    state: 'succeeded',
    actor_display: 'Sistem (kebijakan isolir)',
    created_at: daysAgo(3, 2),
    updated_at: daysAgo(3, 2),
    router_id: 'rtr-101',
    phase_label_code: null,
    items_total: 1,
    items_done: 1,
    error_code: null,
    request_id: 'req-8b45',
    retryable: false,
  },
];

/* ---------- Billing internet M6 (U09/U10 — TK-604) ---------- */

const TENANT01 = 'b3f0a2de-1111-4000-8000-tenant01';

export const BILLING_INVOICES: Record<string, InternetInvoice[]> = {
  [TENANT01]: [
    {
      id: 'inv-001',
      doc_number: 'INV-ns01-202611-0001',
      service_id: 'svc-001',
      service_code: 'SVC-001',
      customer_name: 'Budi Santoso',
      kind: 'prepaid',
      state: 'paid',
      period_index: 0,
      period_start: '2026-11-01',
      period_end: '2026-12-01',
      due_date: '2026-11-01',
      issued_at: daysAgo(4),
      total_amount: '300000.00',
      paid_amount: '300000.00',
      outstanding: '0.00',
      first_period_policy: 'full',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      document_id: 'doc-inv-001',
    },
    {
      id: 'inv-002',
      doc_number: 'INV-ns01-202611-0002',
      service_id: 'svc-002',
      service_code: 'SVC-002',
      customer_name: 'Siti Aminah',
      kind: 'prepaid',
      state: 'paid',
      period_index: 0,
      period_start: '2026-11-01',
      period_end: '2026-12-01',
      due_date: '2026-11-01',
      issued_at: daysAgo(4),
      total_amount: '300000.00',
      paid_amount: '300000.00',
      outstanding: '0.00',
      first_period_policy: 'full',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      document_id: 'doc-inv-002',
    },
    {
      id: 'inv-003',
      doc_number: 'INV-ns01-202611-0003',
      service_id: 'svc-004',
      service_code: 'SVC-004',
      customer_name: 'Agus Wijaya',
      kind: 'prepaid',
      state: 'open',
      period_index: 0,
      period_start: '2026-11-01',
      period_end: '2026-12-01',
      due_date: '2026-11-01',
      issued_at: daysAgo(3),
      total_amount: '250000.00',
      paid_amount: '0.00',
      outstanding: '250000.00',
      first_period_policy: 'full',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      document_id: 'doc-inv-003',
    },
    {
      id: 'inv-004',
      doc_number: 'INV-ns01-202610-0009',
      service_id: 'svc-003',
      service_code: 'SVC-003',
      customer_name: 'Warung Kopi Melati (Rina)',
      kind: 'prepaid',
      state: 'partial',
      period_index: 0,
      period_start: '2026-10-01',
      period_end: '2026-11-01',
      due_date: '2026-10-01',
      issued_at: daysAgo(38),
      total_amount: '350000.00',
      paid_amount: '100000.00',
      outstanding: '250000.00',
      first_period_policy: 'full',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      document_id: 'doc-inv-004',
    },
  ],
};

export const BILLING_PAYMENTS: Record<string, InternetPayment[]> = {
  [TENANT01]: [
    {
      id: 'pay-001',
      method: 'cash',
      state: 'submitted',
      amount: '300000.00',
      allocated_amount: '0.00',
      credit: '0.00',
      external_ref: null,
      has_proof: false,
      collector_display: null,
      submitted_at: daysAgo(0, 2),
      verified_at: null,
      rejected_reason: null,
    },
    {
      id: 'pay-002',
      method: 'bank_transfer',
      state: 'verified',
      amount: '300000.00',
      allocated_amount: '300000.00',
      credit: '0.00',
      external_ref: 'TRF-889124',
      has_proof: true,
      collector_display: null,
      submitted_at: daysAgo(1, 3),
      verified_at: daysAgo(1, 1),
      rejected_reason: null,
    },
    {
      id: 'pay-003',
      method: 'ewallet',
      state: 'rejected',
      amount: '150000.00',
      allocated_amount: '0.00',
      credit: '0.00',
      external_ref: 'EWA-77120',
      has_proof: true,
      collector_display: null,
      submitted_at: daysAgo(2),
      verified_at: null,
      rejected_reason: 'Nominal tidak cocok dengan mutasi rekening',
    },
  ],
};

export const BILLING_PAYMENT_ALLOCATIONS: Record<string, Array<{ invoice_id: string; invoice_number: string; amount: string; allocated_at: string }>> = {
  'pay-002': [
    { invoice_id: 'inv-002', invoice_number: 'INV-ns01-202611-0002', amount: '300000.00', allocated_at: daysAgo(1, 1) },
  ],
};

export const BILLING_AGING: Record<string, { as_of: string; totals: Record<string, { count: number; outstanding: string }>; items: Array<Record<string, unknown>> }> = {
  [TENANT01]: {
    as_of: '2026-11-05',
    totals: {
      not_due: { count: 0, outstanding: '0.00' },
      current: { count: 1, outstanding: '250000.00' },
      d31_60: { count: 1, outstanding: '250000.00' },
      d61_90: { count: 0, outstanding: '0.00' },
      d90_plus: { count: 0, outstanding: '0.00' },
    },
    items: [
      {
        invoice_id: 'inv-003',
        doc_number: 'INV-ns01-202611-0003',
        service_code: 'SVC-004',
        customer_name: 'Agus Wijaya',
        due_date: '2026-11-01',
        days_overdue: 4,
        overdue: true,
        bucket: 'current',
        outstanding: '250000.00',
      },
      {
        invoice_id: 'inv-004',
        doc_number: 'INV-ns01-202610-0009',
        service_code: 'SVC-003',
        customer_name: 'Warung Kopi Melati (Rina)',
        due_date: '2026-10-01',
        days_overdue: 35,
        overdue: true,
        bucket: 'd31_60',
        outstanding: '250000.00',
      },
    ],
  },
};

export const BILLING_DOCUMENTS: Record<string, IssuedDocumentInfo[]> = {
  [TENANT01]: [
    {
      id: 'doc-inv-001',
      kind: 'internet_invoice',
      doc_number: 'INV-ns01-202611-0001',
      ref_type: 'billing_invoice',
      ref_id: 'inv-001',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      template_version: '1',
      sha256: 'a'.repeat(64),
      size_bytes: 48210,
      issued_at: daysAgo(4),
    },
    {
      id: 'doc-inv-002',
      kind: 'internet_invoice',
      doc_number: 'INV-ns01-202611-0002',
      ref_type: 'billing_invoice',
      ref_id: 'inv-002',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      template_version: '1',
      sha256: 'b'.repeat(64),
      size_bytes: 48301,
      issued_at: daysAgo(4),
    },
    {
      id: 'doc-inv-003',
      kind: 'internet_invoice',
      doc_number: 'INV-ns01-202611-0003',
      ref_type: 'billing_invoice',
      ref_id: 'inv-003',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      template_version: '1',
      sha256: 'c'.repeat(64),
      size_bytes: 48155,
      issued_at: daysAgo(3),
    },
    {
      id: 'doc-inv-004',
      kind: 'internet_invoice',
      doc_number: 'INV-ns01-202610-0009',
      ref_type: 'billing_invoice',
      ref_id: 'inv-004',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      template_version: '1',
      sha256: 'd'.repeat(64),
      size_bytes: 47990,
      issued_at: daysAgo(38),
    },
    {
      id: 'doc-rcp-002',
      kind: 'receipt',
      doc_number: 'RCP-ns01-202611-0001',
      ref_type: 'billing_payment',
      ref_id: 'pay-002',
      locale: 'id',
      timezone: 'Asia/Jakarta',
      template_version: '1',
      sha256: 'e'.repeat(64),
      size_bytes: 39112,
      issued_at: daysAgo(1, 1),
    },
  ],
};
