import { describe, expect, it } from 'vitest';
import {
  connectionTone,
  isolationTone,
  jobStateTone,
  paymentTone,
  enforcementTone,
  freshness,
  monitorGroupTone,
} from './statuses';

/** UI_UX.md §2: "Offline" memakai netral/kuning, bukan merah. */
describe('connectionTone', () => {
  it('offline bukan danger', () => {
    expect(connectionTone('offline')).not.toBe('danger');
    expect(['neutral', 'warning']).toContain(connectionTone('offline'));
  });
  it('online success; unknown netral', () => {
    expect(connectionTone('online')).toBe('success');
    expect(connectionTone('unknown')).toBe('neutral');
  });
});

/** Empat dimensi terpisah — bukan digabung (UI_UX.md §5). */
describe('dimensi status terpisah', () => {
  it('bayar/isolir/koneksi/job punya tone sendiri', () => {
    // layanan lunas namun terisolir
    expect(paymentTone('paid')).toBe('success');
    expect(isolationTone('isolated')).toBe('warning');
    // bayar tetap lunas walau RADIUS gagal — dimensi terpisah
    expect(paymentTone('paid')).toBe('success');
    expect(jobStateTone('failed')).toBe('danger');
  });
});

describe('jobStateTone', () => {
  it('uncertain/recovery_required warning; succeeded success; failed danger', () => {
    expect(jobStateTone('uncertain')).toBe('warning');
    expect(jobStateTone('recovery_required')).toBe('warning');
    expect(jobStateTone('succeeded')).toBe('success');
    expect(jobStateTone('failed')).toBe('danger');
    expect(jobStateTone('cancelled')).toBe('neutral');
  });
});

describe('enforcementTone', () => {
  it('mode sesuai RADIUS.md', () => {
    expect(enforcementTone('local')).toBe('neutral');
    expect(enforcementTone('radius_shadow')).toBe('warning');
    expect(enforcementTone('radius_authoritative')).toBe('success');
    expect(enforcementTone('degraded')).toBe('danger');
  });
});

describe('monitorGroupTone', () => {
  it('tidak terpantau/netral bukan merah', () => {
    expect(monitorGroupTone('unmonitored')).toBe('neutral');
    expect(monitorGroupTone('management_unreachable')).not.toBe('danger');
  });
});

/** Freshness: data usang/unknown ≠ nol (UI_UX.md §12). */
describe('freshness', () => {
  it('null → unknown', () => {
    expect(freshness(null)).toBe('unknown');
  });
  it('baru → fresh; lama → stale', () => {
    expect(freshness(new Date().toISOString())).toBe('fresh');
    expect(freshness(new Date(Date.now() - 20 * 60_000).toISOString(), 15)).toBe('stale');
  });
});
