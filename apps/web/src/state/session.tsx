import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useApi } from '../api';
import type { AuthContextShape } from '../api/client';
import type { Permission } from '../permissions/permissions';
import type { TenantSummary } from '../api/contracts';

interface SessionState {
  ctx: AuthContextShape | null;
  loading: boolean;
  error: string | null;
  can: (permission: Permission) => boolean;
  activeTenant: TenantSummary | null;
  switchTenant: (tenantId: string) => Promise<void>;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<{ requires_totp: boolean }>;
  loginTotp: (code: string) => Promise<AuthContextShape>;
  logout: () => Promise<void>;
  reauthUntil: string | null;
  setReauthUntil: (iso: string | null) => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [reauthUntil, setReauthUntil] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ['session'],
    queryFn: () => api.getSession(),
    retry: false,
    staleTime: 30_000,
  });

  const ctx = query.data ?? null;

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries();
  }, [queryClient]);

  const switchTenant = useCallback(
    async (tenantId: string) => {
      // Tenant switch membersihkan seleksi & namespace query cache (ARCHITECTURE.md §3),
      // tanpa memutus observer query sesi yang sedang dipasang.
      const next = await api.switchTenant(tenantId);
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' });
      queryClient.setQueryData(['session'], next);
    },
    [api, queryClient],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      if (!res.requires_totp) {
        // Login non-MFA: sesi aktif — segarkan konteks (paritas loginTotp),
        // lalu halaman login yang menavigasi ke /app.
        queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' });
        await queryClient.refetchQueries({ queryKey: ['session'] });
      }
      return res;
    },
    [api, queryClient],
  );

  const loginTotp = useCallback(
    async (code: string) => {
      const next = await api.loginTotp(code);
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' });
      queryClient.setQueryData(['session'], next);
      return next;
    },
    [api, queryClient],
  );

  const logout = useCallback(async () => {
    await api.logout();
    queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'session' });
    queryClient.setQueryData(['session'], null);
  }, [api, queryClient]);

  const can = useCallback(
    (permission: Permission) => ctx?.permissions.includes(permission) ?? false,
    [ctx],
  );

  const activeTenant = useMemo(
    () => ctx?.tenants.find((t) => t.id === ctx.active_tenant_id) ?? null,
    [ctx],
  );

  const value: SessionState = {
    ctx,
    loading: query.isLoading,
    error: (query.error as Error | null)?.message ?? null,
    can,
    activeTenant,
    switchTenant,
    refresh,
    login,
    loginTotp,
    logout,
    reauthUntil: reauthUntil ?? ctx?.sensitive_reauth_until ?? null,
    setReauthUntil,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const s = useContext(SessionContext);
  if (!s) throw new Error('useSession harus dipakai di dalam SessionProvider');
  return s;
}
