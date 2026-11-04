import { describe, expect, it } from 'vitest';
import {
  formatMoney,
  formatBytes,
  formatDuration,
  formatBitsPerSecond,
  formatPercent,
  zoneLabel,
  passwordStrength,
} from './format';

/** I18N.md §4: tampilan `Rp1.500.000` (id) / `IDR 1,500,000` (en). */
describe('formatMoney', () => {
  it('memformat Rupiah gaya id', () => {
    expect(formatMoney('1500000.00', 'id')).toBe('Rp1.500.000');
    expect(formatMoney(500000, 'id')).toBe('Rp500.000');
  });
  it('memformat gaya en', () => {
    expect(formatMoney('1500000.00', 'en')).toBe('IDR 1,500,000');
  });
  it('nilai tidak valid tidak menjadi NaN', () => {
    expect(formatMoney('abc', 'id')).toContain('Rp');
  });
});

describe('formatBytes', () => {
  it('KiB/MiB', () => {
    expect(formatBytes(512, 'id')).toBe('512 B');
    expect(formatBytes(3_650_000, 'id')).toContain('MiB');
  });
});

describe('formatDuration', () => {
  it('menit dan jam', () => {
    expect(formatDuration(90, 'id')).toBe('1 menit');
    expect(formatDuration(5400, 'id')).toBe('1 jam 30 menit');
    expect(formatDuration(3600 * 26, 'id')).toContain('1 hari');
  });
});

describe('formatBitsPerSecond', () => {
  it('null → tidak diketahui (bukan 0)', () => {
    expect(formatBitsPerSecond(null, 'id')).toBe('tidak diketahui');
  });
  it('skala bit/s', () => {
    expect(formatBitsPerSecond(41_200_000, 'id')).toContain('Mbit/s');
  });
});

describe('formatPercent', () => {
  it('null → tidak diketahui', () => {
    expect(formatPercent(null, 'en')).toBe('unknown');
  });
});

/** I18N.md §4: zona WIB/WITA/WIT dengan label. */
describe('zoneLabel', () => {
  it('memetakan zona Indonesia', () => {
    expect(zoneLabel('Asia/Jakarta')).toBe('WIB');
    expect(zoneLabel('Asia/Makassar')).toBe('WITA');
    expect(zoneLabel('Asia/Jayapura')).toBe('WIT');
    expect(zoneLabel('UTC')).toBe('UTC');
  });
});

describe('passwordStrength', () => {
  it('password pendek lemah', () => {
    expect(passwordStrength('abc')).toBeLessThan(50);
  });
  it('password panjang dan beragam kuat', () => {
    expect(passwordStrength('Zx9#kLm2$Qr7!vB3')).toBeGreaterThanOrEqual(80);
  });
});
