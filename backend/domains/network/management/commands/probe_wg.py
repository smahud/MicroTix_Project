"""Probe handshake interface WireGuard host (ops root; JSON; jujur).

Jalur nyata: `wg show <iface> latest-handshakes` — membutuhkan binary wg +
akses root pada host. Tanpa itu: status BLOCKED + exit 2 (bukan PASS palsu).
Hasil: pembaruan last_handshake_at peer (monotonik), drift evidence
(unknown_on_interface / missing_on_interface).
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from domains.network.services import probe_handshakes


class Command(BaseCommand):
    help = "Probe handshake WG host (wg show; update last_handshake_at; JSON)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--interface", default=None, help="interface host (default: WireGuardHost.interface_name)")
        parser.add_argument("--wg-bin", default=None, help="binary wg (default: MT_WG_PROBE_BIN / wg)")

    def handle(self, *args, **options) -> None:
        result = probe_handshakes(
            interface=options["interface"],
            wg_bin=options["wg_bin"],
        )
        self.stdout.write(json.dumps(result))
        if result.get("status") == "blocked":
            raise CommandError(result.get("error", "blocked"), returncode=2)
        if result.get("status") != "ok":
            raise CommandError(result.get("error", "probe gagal"), returncode=1)
