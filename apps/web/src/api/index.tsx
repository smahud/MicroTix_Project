import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { API_MODE, PRODUCTION_MODE_MISCONFIGURED } from './client';
import type { ApiClient } from './client';
import { MockApiClient } from './mock/adapter';
import { LiveApiClient } from './live/adapter';

/**
 * Mode integrasi:
 * - 'mock' (default dev): adapter pengembangan in-browser, data simulasi berlabel.
 * - 'live': klien HTTP ke backend same-origin /api/v1 (TK-104). Jalankan backend
 *   dan set VITE_API_MODE=live (+ MICROTIX_API untuk proxy dev server Vite).
 */
if (PRODUCTION_MODE_MISCONFIGURED) {
  // Jangan pernah menjalankan adapter mock pada build produksi.
  throw new Error('Konfigurasi produksi tidak sah: VITE_API_MODE harus "live".');
}
const client: ApiClient = API_MODE === 'live' ? new LiveApiClient() : new MockApiClient();

const ApiContext = createContext<ApiClient>(client);

export function ApiProvider({ children }: { children: ReactNode }) {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // TanStack Query: polling job memakai refetchInterval per-query.
            staleTime: 15_000,
            retry: false,
            refetchOnWindowFocus: false,
          },
        },
      }),
    [],
  );
  return (
    <QueryClientProvider client={queryClient}>
      <ApiContext.Provider value={client}>{children}</ApiContext.Provider>
    </QueryClientProvider>
  );
}

export function useApi(): ApiClient {
  return useContext(ApiContext);
}

export function useApiMode(): 'mock' | 'live' {
  return API_MODE;
}
