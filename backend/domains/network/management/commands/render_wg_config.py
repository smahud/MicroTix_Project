"""Render konfigurasi host WireGuard (wg0.conf) dari state host+peers.

Idempoten; berkas 0600; TIDAK menyentuh interface aktif. PrivateKey hanya
disematkan bila --private-key-file diberikan (ops root); tanpa itu baris
komentar jujur — wg-quick membutuhkan PrivateKey untuk aktifasi.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from domains.network.services import render_host_config


class Command(BaseCommand):
    help = "Render wg0.conf dari state host+peers (ops mengaplikasikan; JSON)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--target", required=True, help="direktori keluaran")
        parser.add_argument("--private-key-file", default=None, help="berkas kunci privat host (root; opsional)")

    def handle(self, *args, **options) -> None:
        try:
            result = render_host_config(
                options["target"],
                private_key_file=options["private_key_file"],
            )
        except Exception as exc:  # noqa: BLE001 — diagnosis jujur tanpa traceback
            raise CommandError(str(exc).split("\n")[0][:200], returncode=1) from exc
        self.stdout.write(json.dumps(result))
