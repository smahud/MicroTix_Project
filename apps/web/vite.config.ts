import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

/**
 * Gate mode produksi (master prompt §5): build produksi TIDAK BOLEH diam-diam
 * memakai adapter mock. VITE_API_MODE wajib 'live' eksplisit saat build
 * produksi; tanpa itu build GAGAL dengan pesan jelas (bukan fallback mock).
 */
function enforceLiveModeInProduction() {
  return {
    name: 'microtix-enforce-live-mode',
    enforce: 'pre' as const,
    apply: 'build' as const,
    configResolved(resolved: { mode: string; env?: { VITE_API_MODE?: string } }) {
      const mode = resolved.env?.VITE_API_MODE ?? process.env.VITE_API_MODE;
      if (mode !== 'live') {
        throw new Error(
          [
            '',
            '=========================================================',
            ' MICROtIX BUILD DITOLAK: VITE_API_MODE bukan "live".',
            ' Build produksi wajib menghubungkan backend nyata.',
            ' Jalankan: VITE_API_MODE=live pnpm exec vite build',
            ' (Mode mock hanya untuk development terisolasi/unit test.)',
            '=========================================================',
            '',
          ].join('\n'),
        );
      }
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), enforceLiveModeInProduction()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@locales': path.resolve(__dirname, '../../locales'),
    },
  },
  server: {
    port: 5173,
    fs: {
      // Katalog pesan berada di <repo>/locales (I18N.md: locales/{id,en})
      allow: [path.resolve(__dirname, '../..')],
    },
    // Dev only: backend same-origin in production (Caddy); mock mode runs fully in-browser.
    proxy: process.env.MICROTIX_API
      ? {
          '/api': {
            target: process.env.MICROTIX_API,
            changeOrigin: true,
          },
        }
      : undefined,
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          intl: ['react-intl'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
