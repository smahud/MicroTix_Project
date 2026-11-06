import { describe, expect, it } from 'vitest';
import idWeb from '@locales/id/web.json';
import enWeb from '@locales/en/web.json';
import { RELEASE_FLAGS, isReleased } from './release-flags';

/** I18N.md §6: sumber kebenaran katalog id; paritas id/en. */
describe('katalog pesan', () => {
  it('id dan en memiliki kunci yang sama', () => {
    expect(Object.keys(enWeb).sort()).toEqual(Object.keys(idWeb).sort());
  });

  it('placeholder argumen konsisten id/en', () => {
    const ph = (s: unknown) => {
      // buang klausa ICU plural/select sebelum mencocokkan placeholder
      const cleaned = String(s).replace(/\{\s*[a-zA-Z0-9_]+\s*,\s*(?:plural|select|selectordinal)\s*,[\s\S]*?\}\s*\}/g, '');
      return Array.from(cleaned.matchAll(/\{([a-zA-Z0-9_]+)[,}]/g)).map((m) => m[1]);
    };
    const mismatches: string[] = [];
    for (const [k, v] of Object.entries(idWeb)) {
      const a = new Set(ph(v));
      const b = new Set(ph(enWeb[k as keyof typeof enWeb]));
      if (a.size !== b.size || [...a].some((x) => !b.has(x))) {
        mismatches.push(k);
      }
    }
    expect(mismatches).toEqual([]);
  });

  it('tidak ada teks komponen kosong', () => {
    for (const [k, v] of Object.entries(idWeb)) {
      expect(String(v).trim().length, `kunci ${k}`).toBeGreaterThan(0);
    }
  });
});

/** Modul belum release_enabled disembunyikan (UI_UX.md §1). */
describe('release flags', () => {
  it('R1 aktif', () => {
    expect(isReleased('overview')).toBe(true);
    expect(isReleased('customers')).toBe(true);
    expect(isReleased('routers')).toBe(true);
    expect(isReleased('radius')).toBe(true);
  });
  it('R2 billing/aktivasi aktif (TK-604; engine TK-601+TK-109 terverifikasi)', () => {
    expect(RELEASE_FLAGS.billing).toBe(true);
    expect(RELEASE_FLAGS.activation).toBe(true);
  });
  it('R2+ lain dan R3–R4 disembunyikan', () => {
    expect(RELEASE_FLAGS.finance).toBe(false);
    expect(RELEASE_FLAGS.collectors).toBe(false);
    expect(RELEASE_FLAGS.devices).toBe(false);
    expect(RELEASE_FLAGS.vouchers).toBe(false);
    expect(RELEASE_FLAGS.configuration).toBe(false);
  });
});
