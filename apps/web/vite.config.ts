import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
