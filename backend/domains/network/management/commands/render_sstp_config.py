"""Render konfigurasi server SSTP host (accel-ppp 1.15.0) dari state akun.

Menghasilkan accel-ppp.conf + chap-secrets di direktori target (idempoten;
berkas 0600 — chap-secrets memuat password kredensial per-router). Ops host
menerapkan: pasang ke /etc/microtix/sstp/ lalu restart accel-ppp@microtix.
TIDAK menyentuh proses/listener aktif.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from domains.network.services import render_sstp_config


class Command(BaseCommand):
    help = "Render accel-ppp.conf + chap-secrets dari akun SSTP aktif (ops host; JSON)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--target", required=True, help="direktori keluaran (mis. /etc/microtix/sstp)")

    def handle(self, *args, **options) -> None:
        try:
            result = render_sstp_config(options["target"])
        except Exception as exc:  # noqa: BLE001 — diagnosis jujur tanpa traceback
            raise CommandError(str(exc).split("\n")[0][:200], returncode=1) from exc
        self.stdout.write(json.dumps(result))
