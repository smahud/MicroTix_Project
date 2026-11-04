import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { API_MODE } from './client';
import type { ApiClient } from './client';
import { MockApiClient } from './mock/adapter';

/**
 * Mode integrasi:
 * - 'mock' (default dev): adapter pengembangan in-browser, data simulasi berlabel.
 * - 'live': klien HTTP ke backend same-origin /api/v1 (belum tersedia di repo ini).
 */
const client: ApiClient = new MockApiClient();

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
