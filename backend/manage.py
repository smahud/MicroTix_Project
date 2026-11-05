#!/usr/bin/env python3
"""Utilitas manajemen Django MicroTix.

Migrasi skema dijalankan dengan peran migrator terpisah:
    DATABASE_URL="$MIGRATE_DATABASE_URL" python manage.py migrate
(ARCHITECTURE.md §4 — migrator terpisah dari runtime).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "microtix.settings")
    sys.path.insert(0, str(BACKEND_DIR))
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
