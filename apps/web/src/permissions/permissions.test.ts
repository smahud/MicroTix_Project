import { describe, expect, it } from 'vitest';
import { can, SENSITIVE_PERMISSIONS, ROLE_PERMISSIONS } from './permissions';
import type { Role } from './permissions';

/** ARCHITECTURE.md §3 — bundel peran. */
describe('role permissions', () => {
  it('owner melihat seluruh izin tenant (tanpa platform)', () => {
    expect(can('owner', 'routers.enroll')).toBe(true);
    expect(can('owner', 'radius.cutover')).toBe(true);
    expect(can('owner', 'ledger.post')).toBe(true);
    expect(can('owner', 'platform.payments.approve')).toBe(false);
  });

  it('teknisi membaca operasional, tidak memverifikasi uang', () => {
    expect(can('technician', 'customers.read')).toBe(true);
    expect(can('technician', 'routers.enroll')).toBe(true);
    expect(can('technician', 'payments.verify')).toBe(false);
    expect(can('technician', 'routers.configure')).toBe(false);
  });

  it('admin pembayaran memverifikasi uang/aktivasi, tidak membuka konfigurasi WAN', () => {
    expect(can('payments_admin', 'payments.verify')).toBe(true);
    expect(can('payments_admin', 'services.activate')).toBe(true);
    expect(can('payments_admin', 'routers.configure')).toBe(false);
    expect(can('payments_admin', 'routers.enroll')).toBe(false);
  });

  it('akuntan mengelola buku; viewer hanya baca', () => {
    expect(can('accountant', 'ledger.post')).toBe(true);
    expect(can('accountant', 'customers.write')).toBe(false);
    expect(can('viewer', 'customers.read')).toBe(true);
    expect(can('viewer', 'customers.write')).toBe(false);
  });

  it('setiap peran punya definisi', () => {
    for (const role of ['owner', 'technician', 'payments_admin', 'accountant', 'viewer', 'collector', 'agent'] as Role[]) {
      expect(Array.isArray(ROLE_PERMISSIONS[role])).toBe(true);
    }
  });

  it('aksi sensitif terdaftar untuk reauth (ARCHITECTURE.md §3)', () => {
    expect(SENSITIVE_PERMISSIONS.has('radius.cutover')).toBe(true);
    expect(SENSITIVE_PERMISSIONS.has('services.reveal_credentials')).toBe(true);
    expect(SENSITIVE_PERMISSIONS.has('backups.download')).toBe(true);
  });
});
