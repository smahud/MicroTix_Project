import type {
  ApiErrorEnvelope,
  CursorPage,
  FieldError,
} from './contracts';

/**
 * Klien HTTP live — hanya dipakai bila backend tersedia (same-origin /api/v1).
 * Cookie HttpOnly/Secure/SameSite=Lax + CSRF (ARCHITECTURE.md §2).
 * 202 mengembalikan job_id/status_url; browser ditutup tidak membatalkan pekerjaan.
 */
export class ApiError extends Error {
  readonly envelope: ApiErrorEnvelope;
  readonly status: number;
  constructor(envelope: ApiErrorEnvelope, status: number) {
    super(`[${envelope.code}] ${envelope.message}`);
    this.name = 'ApiError';
    this.envelope = envelope;
    this.status = status;
  }
  get code(): string {
    return this.envelope.code;
  }
  get fieldErrors(): Record<string, FieldError[]> | undefined {
    return this.envelope.field_errors;
  }
}

function normalizeEnvelope(raw: unknown, _status: number): ApiErrorEnvelope {
  const e = (raw ?? {}) as Partial<ApiErrorEnvelope>;
  return {
    code: typeof e.code === 'string' ? e.code : 'dependency_unavailable',
    message: typeof e.message === 'string' ? e.message : '',
    request_id: typeof e.request_id === 'string' ? e.request_id : 'unknown',
    locale: typeof e.locale === 'string' ? e.locale : 'id',
    field_errors: e.field_errors,
    retryable: e.retryable,
  };
}

export interface PageParams {
  cursor?: string | null;
  limit?: number;
}

export interface MutationOptions {
  /** Idempotency-Key wajib untuk mutasi uang/provisioning/commit/cutover/backup (ARCHITECTURE.md §5). */
  idempotencyKey?: string;
  /** CSRF token dari meta (cookie-based session). */
  csrfToken?: string;
}

const JSON_HEADERS = { 'content-type': 'application/json' };

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'PUT',
  path: string,
  opts: MutationOptions = {},
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { ...JSON_HEADERS };
  if (opts.idempotencyKey) headers['idempotency-key'] = opts.idempotencyKey;
  if (opts.csrfToken) headers['x-csrf-token'] = opts.csrfToken;

  const res = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!res.ok) {
    let raw: unknown = null;
    try {
      raw = await res.json();
    } catch {
      raw = null;
    }
    throw new ApiError(normalizeEnvelope(raw, res.status), res.status);
  }
  // 204 atau kosong
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const http = {
  get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params ?? {})) {
      if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
    }
    const q = qs.toString();
    return request<T>('GET', q ? `${path}?${q}` : path);
  },
  post<T>(path: string, body?: unknown, opts?: MutationOptions): Promise<T> {
    return request<T>('POST', path, opts ?? {}, body);
  },
  patch<T>(path: string, body?: unknown, opts?: MutationOptions): Promise<T> {
    return request<T>('PATCH', path, opts ?? {}, body);
  },
  put<T>(path: string, body?: unknown, opts?: MutationOptions): Promise<T> {
    return request<T>('PUT', path, opts ?? {}, body);
  },
};

/** Halaman kursor: limit default 50, maks 200 (ARCHITECTURE.md §5). */
export const PAGE_SIZE_DEFAULT = 50;
export const PAGE_SIZE_MAX = 200;

export function pageQuery(p: PageParams): Record<string, string | number | undefined> {
  return {
    cursor: p.cursor ?? undefined,
    limit: p.limit ?? PAGE_SIZE_DEFAULT,
  };
}

/**
 * URL artefak dokumen terbit (PDF — TK-109). Sesi same-origin dikirim
 * otomatis oleh <a href>; dipakai untuk tautan invoice/kwitansi (U09).
 */
export function documentArtifactUrl(tenantId: string, documentId: string): string {
  return `/api/v1/tenants/${tenantId}/documents/${documentId}`;
}

export type { CursorPage };
