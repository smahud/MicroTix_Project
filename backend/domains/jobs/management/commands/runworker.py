"""Command worker: loop claim → preflight → execute → verify + rekonsiliasi.

Worker adalah proses terpisah dari API (boundary privilege berbeda); kode
worker tidak memegang kredensial HTTP pengguna. Jalankan:
    python manage.py runworker --loop --interval 2
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from domains.jobs import engine


class Command(BaseCommand):
    help = "Worker pekerjaan MicroTix (PostgreSQL job + outbox)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--once", action="store_true", help="Klaim & jalankan satu job lalu keluar")
        parser.add_argument("--loop", action="store_true", help="Jalan terus (default)")
        parser.add_argument("--interval", type=float, default=2.0, help="Jeda polling detik (default 2)")
        parser.add_argument("--reconcile-only", action="store_true", help="Hanya rekonsiliasi lease/uncertain")

    def handle(self, *args, **options) -> None:
        once = options["once"]
        interval = options["interval"]
        if options["reconcile_only"]:
            expired = engine.reconcile_expired_leases()
            self.stdout.write(f"reconcile: {expired} lease kedaluwarsa")
            return
        while True:
            expired = engine.reconcile_expired_leases()
            job = engine.claim_next()
            if job is not None:
                self.stdout.write(f"job {job.id} kind={job.kind} attempt={job.attempt}")
                result = engine.run_claimed(job)
                self.stdout.write(
                    f"job {job.id} → {result.state}" + (f" ({result.error_code})" if result.error_code else "")
                )
                if once:
                    return
                continue
            dispatched = engine.dispatch_outbox()
            if expired or dispatched:
                self.stdout.write(f"reconcile={expired} outbox={dispatched}")
            if once:
                return
            time.sleep(interval)
