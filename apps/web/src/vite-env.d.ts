/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "mock" (default): dev fixtures in-browser. "live": real backend at /api/v1 (same-origin). */
  readonly VITE_API_MODE?: 'mock' | 'live';
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
