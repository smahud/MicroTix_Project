import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import type { Plugin } from 'vite';
import path from 'node:path';

// https://vite.dev/config/
// Guard integrasi produksi (§5): build produksi TANPA VITE_API_MODE=live gagal
// dengan pesan jelas — mencegah bundle mock beredar sebagai rilis (anti
// fallback senyap). Dev/test tetap bebas memilih mode.
function enforceLiveApiMode(): Plugin {
  return {
    name: "microtix-enforce-live-api",
    apply: "build",
    configResolved(config) {
      if (config.env.VITE_API_MODE !== "live") {
        throw new Error(
          "VITE_API_MODE=live wajib untuk build produksi MicroTix (build mock dilarang; " +
            "set variabel env VITE_API_MODE=live sebelum vite build).",
        );
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), enforceLiveApiMode()],
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
