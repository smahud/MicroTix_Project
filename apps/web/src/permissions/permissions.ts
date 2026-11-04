/**
 * ARCHITECTURE.md §3 — permission granular, bundel peran.
 * Nama izin mengikuti dokumentasi; jangan menambah izin bisnis baru.
 */
export const PERMISSIONS = [
  'customers.read',
  'customers.write',
  'imports.run',
  'migration.run',
  'services.provision',
  'services.activate',
  'services.reveal_credentials',
  'routers.read',
  'routers.enroll',
  'routers.release',
  'routers.configure',
  'radius.cutover',
  'profiles.write',
  'backups.run',
  'backups.download',
  'payments.verify',
  'isolation.policy.manage',
  'collections.receive',
  'collections.settle',
  'vouchers.manage',
  'agents.manage',
  'devices.manage',
  'prospects.manage',
  'workorders.manage',
  'ledger.post',
  'period.close',
  'period.reopen',
  'subscription.manage',
  'team.manage',
  'platform.payments.approve',
  'platform.destinations.manage',
] as const;

export type Permission = (typeof PERMISSIONS)[number];

export const ROLES = [
  'owner',
  'technician',
  'payments_admin',
  'accountant',
  'viewer',
  'collector',
  'agent',
] as const;

export type Role = (typeof ROLES)[number];

const VIEWER: readonly Permission[] = [
  'customers.read',
  'routers.read',
];

/** Owner melihat seluruh menu tenant. */
const OWNER: readonly Permission[] = [...PERMISSIONS].filter(
  (p) => !p.startsWith('platform.'),
);

/**
 * Teknisi: pelanggan operasional, router, perangkat, backup berizin, tiket;
 * nominal tagihan disembunyikan bila tak dibutuhkan (tidak payments.verify).
 */
const TECHNICIAN: readonly Permission[] = [
  'customers.read',
  'customers.write',
  'routers.read',
  'routers.enroll',
  'services.provision',
  'services.reveal_credentials',
  'backups.run',
  'backups.download',
  'imports.run',
  'migration.run',
  'devices.manage',
  'workorders.manage',
  'prospects.manage',
];

/**
 * Admin Pembayaran: pelanggan, invoice, payment, aktivasi;
 * tidak membuka konfigurasi WAN (tanpa routers.configure).
 */
const PAYMENTS_ADMIN: readonly Permission[] = [
  'customers.read',
  'customers.write',
  'payments.verify',
  'services.activate',
  'services.reveal_credentials',
  'collections.receive',
  'collections.settle',
];

/** Akuntan mengelola buku. */
const ACCOUNTANT: readonly Permission[] = [
  'customers.read',
  'ledger.post',
  'period.close',
  'period.reopen',
  'payments.verify',
];

/** Kolektor hanya assignment dan penerimaan/setorannya. */
const COLLECTOR: readonly Permission[] = ['collections.receive'];

/** Agen hanya stok/penjualannya. */
const AGENT: readonly Permission[] = [];

export const ROLE_PERMISSIONS: Record<Role, readonly Permission[]> = {
  owner: OWNER,
  technician: TECHNICIAN,
  payments_admin: PAYMENTS_ADMIN,
  accountant: ACCOUNTANT,
  viewer: VIEWER,
  collector: COLLECTOR,
  agent: AGENT,
};

export function can(role: Role, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role].includes(permission);
}

/**
 * Aksi sensitif wajib MFA + reauth (10 menit) — ARCHITECTURE.md §3:
 * izin/rekening, cutover/rollback/restore, reveal secret/kunci,
 * ekspor sensitif, override hold, reopen periode.
 */
export const SENSITIVE_PERMISSIONS: ReadonlySet<Permission> = new Set([
  'radius.cutover',
  'services.reveal_credentials',
  'backups.download',
  'period.reopen',
  'team.manage',
  'subscription.manage',
  'platform.destinations.manage',
]);
