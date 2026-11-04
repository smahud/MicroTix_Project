import { useCallback } from 'react';
import { useIntl } from 'react-intl';
import type idWeb from '@locales/id/web.json';

/**
 * Sumber kebenaran pesan adalah katalog `id` (I18N.md §6).
 * Key yang dipakai kode tetapi tidak ada di katalog `id` → error kompilasi.
 */
export type MessageId = Extract<keyof typeof idWeb, string>;

export type TValues = Record<string, string | number>;

/**
 * `t('customers.title')` → string terlokalkan.
 * Argumen tidak dirangkai dengan penggabungan string (I18N.md §3);
 * gunakan placeholder ICU: t('x', {count: 3}).
 */
export function useT(): (id: MessageId, values?: TValues) => string {
  const intl = useIntl();
  return useCallback(
    (id: MessageId, values?: TValues) =>
      intl.formatMessage({ id }, values) as string,
    [intl],
  );
}

export function useFormatDate(): (iso: string, opts?: Intl.DateTimeFormatOptions) => string {
  const intl = useIntl();
  return useCallback(
    (iso: string, opts?: Intl.DateTimeFormatOptions) =>
      intl.formatDate(new Date(iso), opts),
    [intl],
  );
}

/**
 * Label enum terlokalkan dengan fallback aman:
 * kunci `enums.<group>.<value>` bila ada; kalau tidak, tampilkan nilai mentah.
 * Kode status/enum tidak diterjemahkan (I18N.md §3) — hanya labelnya.
 */
export function useEnumLabel(): (group: string, value: string | null | undefined) => string {
  const intl = useIntl();
  return useCallback(
    (group: string, value: string | null | undefined) => {
      if (value == null) return intl.formatMessage({ id: 'common.unknown' });
      const id = `enums.${group}.${value}`;
      try {
        const msg = intl.formatMessage({ id }, undefined);
        return msg === id ? value : msg;
      } catch {
        return value;
      }
    },
    [intl],
  );
}

/** Locale aktif untuk pemformatan berbasis Intl non-katalog. */
export function useActiveLocale(): 'id' | 'en' {
  const intl = useIntl();
  return intl.locale.toLowerCase().startsWith('en') ? 'en' : 'id';
}
