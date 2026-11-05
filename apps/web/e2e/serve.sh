#!/usr/bin/env bash
# Dibesarkan playwright webServer — cwd deterministik: SELALU apps/web
# (config berada di e2e/ sehingga command default dijalankan dari sana;
# pnpm exec butuh cwd proyek untuk menemukan binary vite).
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec pnpm exec vite --port 5173 --strictPort --host 127.0.0.1
