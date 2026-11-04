import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';

/**
 * branding.json: frontend memperoleh *resolved public config* dari backend.
 * Placeholder dev berlabel jelas; publikasi landing memerlukan nilai nyata.
 * Nama display tidak dipakai sebagai identitas internal apa pun.
 */
export interface PublicBranding {
  /** Sudah di-resolve backend: environment override nonempty → file default. */
  readonly display_name: string;
  readonly public_domain: string | null;
  readonly public_logo: string | null;
  readonly public_contact: string | null;
  /** true bila brand publik belum terisi (landing tidak dipublikasikan). */
  readonly publication_blocked: boolean;
  readonly source: 'backend' | 'dev_placeholder';
}

const DEV_PLACEHOLDER: PublicBranding = {
  display_name: 'MicroTix',
  public_domain: null,
  public_logo: null,
  public_contact: null,
  publication_blocked: true,
  source: 'dev_placeholder',
};

const BrandingContext = createContext<PublicBranding>(DEV_PLACEHOLDER);

export function BrandingProvider({ value, children }: { value?: PublicBranding; children: ReactNode }) {
  const resolved = useMemo(() => value ?? DEV_PLACEHOLDER, [value]);
  return <BrandingContext.Provider value={resolved}>{children}</BrandingContext.Provider>;
}

export function useBranding(): PublicBranding {
  return useContext(BrandingContext);
}
