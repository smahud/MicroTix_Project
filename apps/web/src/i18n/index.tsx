import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { IntlProvider } from 'react-intl';
import idWeb from '@locales/id/web.json';
import enWeb from '@locales/en/web.json';

/**
 * I18N.md: default `id`; `en` wajib. Sebelum login: pilihan pengunjung
 * (cookie fungsional) → Accept-Language yang didukung → `id`.
 * Mengganti bahasa tidak boleh menghapus isian formulir (hanya ganti katalog).
 */
export const LOCALES = ['id', 'en'] as const;
export type Locale = (typeof LOCALES)[number];

const CATALOGS: Record<Locale, Record<string, string>> = {
  id: idWeb as Record<string, string>,
  en: enWeb as Record<string, string>,
};

export const LANGUAGE_NAMES: Record<Locale, string> = {
  // Nama bahasa ditulis dalam bahasanya sendiri (I18N.md §7)
  id: 'Bahasa Indonesia',
  en: 'English',
};

const COOKIE_NAME = 'mt_locale';

function readVisitorLocale(): Locale {
  try {
    const m = document.cookie.match(new RegExp(`(?:^|;\\s*)${COOKIE_NAME}=([^;]*)`));
    const v = m?.[1];
    if (v === 'id' || v === 'en') return v;
  } catch {
    /* SSR/privacy mode — abaikan */
  }
  const nav = typeof navigator !== 'undefined' ? navigator.language : 'id';
  if (nav?.toLowerCase().startsWith('en')) return 'en';
  return 'id';
}

function persistVisitorLocale(locale: Locale): void {
  try {
    // Cookie fungsional 1 tahun, bukan pelacakan
    document.cookie = `${COOKIE_NAME}=${locale};path=/;max-age=31536000;samesite=lax`;
  } catch {
    /* abaikan */
  }
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'id',
  setLocale: () => undefined,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => readVisitorLocale());

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    persistVisitorLocale(next);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  return (
    <I18nContext.Provider value={value}>
      <IntlProvider
        locale={locale}
        defaultLocale="id"
        messages={CATALOGS[locale]}
        // Kunci belum diterjemahkan jatuh ke teks `id` (I18N.md §1 rantai cadangan)
        onError={(err) => {
          if (process.env.NODE_ENV !== 'production') {
            console.warn('[i18n]', err.message);
          }
        }}
      >
        {children}
      </IntlProvider>
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
