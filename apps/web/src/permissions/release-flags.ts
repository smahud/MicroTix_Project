/**
 * Release flag per modul (TK-107). Modul belum `release_enabled`
 * disembunyikan dari menu, bukan ditampilkan sebagai fitur aktif.
 */
export const RELEASE_FLAGS = {
  // R1
  landing: true,
  auth: true,
  overview: true,
  customers: true,
  routers: true,
  imports: true,
  backups: true,
  monitoring: true,
  jobs: true,
  settings: true,
  radius: true,
  admin: true,
  // R2 — belum release
  billing: false,
  activation: false,
  finance: false,
  collectors: false,
  // R3 — belum release
  devices: false,
  vouchers: false,
  agents: false,
  fieldops: false,
  // R4 — belum release
  configuration: false,
} as const;

export type ReleaseFlag = keyof typeof RELEASE_FLAGS;

export function isReleased(flag: ReleaseFlag): boolean {
  return RELEASE_FLAGS[flag];
}
