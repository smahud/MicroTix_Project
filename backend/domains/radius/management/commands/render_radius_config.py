"""Render bundle konfigurasi FreeRADIUS (reconciler) untuk satu instance.

Instance per-NAS: --nas-ip membatasi clients.conf hanya pada NAS tersebut
(harness menjalankan dua instance terpisah untuk uji isolasi tenant).
"""
from __future__ import annotations

import json
import os

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from domains.radius import reconciler


class Command(BaseCommand):
    help = "Render konfigurasi daemon FreeRADIUS (clients.conf + sql facade + site)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--target", required=True)
        parser.add_argument("--db-name", default="microtix")
        parser.add_argument("--db-user", default="mtx_radius")
        parser.add_argument("--db-password", default=os.environ.get("MT_RADIUS_DB_PASSWORD", ""))
        parser.add_argument("--db-host", default="")
        parser.add_argument("--db-port", type=int, default=0)
        parser.add_argument("--bind-ip", default="127.0.0.1")
        parser.add_argument("--auth-port", type=int, default=18120)
        parser.add_argument("--acct-port", type=int, default=18121)
        parser.add_argument("--nas-ip", default="", help="Hanya NAS dengan nasname ini (instance per-tenant)")
        parser.add_argument("--validate", action="store_true")

    def handle(self, *args, **options) -> None:
        if not options["db_password"]:
            raise CommandError("Password DB daemon wajib: --db-password atau MT_RADIUS_DB_PASSWORD")
        host = options["db_host"]
        port = options["db_port"]
        if not host or not port:
            from django.db import connection

            cfg = connection.get_connection_params()
            host = host or (cfg.get("host") or "127.0.0.1")
            port = port or int(cfg.get("port") or 5432)
        nas_rows = reconciler.nas_rows_for(options["nas_ip"] or None)
        written = reconciler.write_config(
            options["target"],
            nas_rows=nas_rows,
            db={
                "host": host,
                "port": port,
                "name": options["db_name"],
                "login": options["db_user"],
                "password": options["db_password"],
            },
            auth_port=options["auth_port"],
            acct_port=options["acct_port"],
            listen_ip=options["bind_ip"],
        )
        result = {"status": "ok", "target": options["target"], "files": written, "nas_count": len(nas_rows)}
        if options["validate"]:
            code, output = reconciler.validate_config(options["target"])
            result["validate_exit"] = code
            if code != 0:
                self.stdout.write(json.dumps(result))
                raise CommandError(f"freeradius -C gagal: {output[-500:]}")
        self.stdout.write(json.dumps(result))
