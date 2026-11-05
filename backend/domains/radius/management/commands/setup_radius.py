"""Grant privilege daemon FreeRADIUS (RADIUS.md §4) — dijalankan migrator.

Membuat peran + password TIDAK dilakukan di sini (butuh superuser — lihat
instalasi.sh / harness); command ini hanya memberi USAGE skema + EXECUTE
facade kepada peran mtx_radius yang sudah ada, dan mencabut PUBLIC.
Idempoten; keluaran JSON. Tanpa privilege/peran → status jujur, exit 1.
"""
from __future__ import annotations

import json
import sys

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "GRANT EXECUTE facade RADIUS kepada peran daemon (migrator; idempoten)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--role", default="mtx_radius")

    def handle(self, *args, **options) -> None:
        role = options["role"]
        out = {"status": "error", "role": role, "grant_daemon": {"status": "error"}}
        with connection.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role])
            if cur.fetchone() is None:
                out["error"] = f"peran {role} belum ada — buat lewat superuser (instalasi.sh/harness)"
                self.stdout.write(json.dumps(out))
                sys.exit(1)
            try:
                cur.execute(f"GRANT USAGE ON SCHEMA radius TO {role}")
                cur.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO {role}")
                cur.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA radius FROM PUBLIC")
            except Exception as exc:  # noqa: BLE001 — diagnosis jujur tanpa traceback
                out["error"] = str(exc).split("\n")[0][:200]
                self.stdout.write(json.dumps(out))
                sys.exit(1)
        out.update({"status": "ok", "grant_daemon": {"status": "ok"}})
        self.stdout.write(json.dumps(out))
