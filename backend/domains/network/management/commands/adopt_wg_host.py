"""Adopsi kunci publik WireGuard host dari installer (idempoten; JSON).

Env MT_WG_SERVER_PUBKEY (instalasi.sh §9.13) diadopsi model WireGuardHost.
Tanpa env: no-op jujur (fallback dev deterministik). Rotasi dengan peer
aktif DITOLAK (exit 1) — rotasi adalah operasi jaringan terjadwal.

--check: hanya melaporkan, tanpa mutasi (mode doctor; mismatch → exit 1).
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from domains.network.services import adopt_wg_host_key


class Command(BaseCommand):
    help = "Adopsi pubkey WG host dari env installer (idempoten; keluaran JSON)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--check", action="store_true", help="tanpa mutasi (doctor)")

    def handle(self, *args, **options) -> None:
        result = adopt_wg_host_key(check_only=bool(options["check"]))
        self.stdout.write(json.dumps(result))
        if result.get("status") in ("refused", "mismatch"):
            raise CommandError(result.get("note", result["status"]), returncode=1)
