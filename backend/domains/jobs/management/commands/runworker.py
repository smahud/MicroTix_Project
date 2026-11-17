"""Command worker: loop claim → authority → preflight → execute → verify.

Worker adalah proses terpisah dari API (boundary privilege berbeda); kode
worker tidak memegang kredensial HTTP pengguna. Jalankan:
    python manage.py runworker --loop --interval 2

Drain (PA-002 / A08): SIGTERM/SIGINT menghentikan klaim baru segera; job
aktif diselesaikan atau ditahan jujur dalam batas --drain-timeout. Status
keluar membedakan drained (0) vs deadline drain terlampaui/incomplete (3):
job yang ditahan berada di state durable (retry_wait/uncertain) dan pulih
lewat klaim/rekonsiliasi berikutnya — runbook: stop claims → drain/stop old
writers → reconcile/readback → resume. Ini bukan rehearsal systemd/installer.
"""
from __future__ import annotations

import signal
import threading
import time

from django.core.management.base import BaseCommand

from domains.jobs import engine

EXIT_DRAINED = 0
EXIT_DRAIN_DEADLINE = 3


class Command(BaseCommand):
    help = "Worker pekerjaan MicroTix (PostgreSQL job + outbox)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--once", action="store_true", help="Klaim & jalankan satu job lalu keluar")
        parser.add_argument("--loop", action="store_true", help="Jalan terus (default)")
        parser.add_argument("--interval", type=float, default=2.0, help="Jeda polling detik (default 2)")
        parser.add_argument("--reconcile-only", action="store_true", help="Hanya rekonsiliasi lease/uncertain")
        parser.add_argument(
            "--drain-timeout",
            type=float,
            default=60.0,
            help="Batas detik menyelesaikan job aktif setelah sinyal stop (default 60)",
        )

    def handle(self, *args, **options) -> None:
        once = options["once"]
        interval = options["interval"]
        drain_timeout = options["drain_timeout"]
        if options["reconcile_only"]:
            expired = engine.reconcile_expired_leases()
            self.stdout.write(f"reconcile: {expired} lease kedaluwarsa")
            return

        state = {"stopping": False, "job_active": False}
        stop_event = threading.Event()

        def _arm_drain_timer() -> None:
            # Timer drain hanya relevan saat job AKTIF (REV-2011-06): alarm
            # saat idle akan mengklaim exit-3 palsu padahal tidak ada job.
            if state["stopping"] and state["job_active"]:
                try:
                    signal.setitimer(signal.ITIMER_REAL, drain_timeout)
                except (ValueError, OSError):  # pragma: no cover
                    pass

        def _request_stop(signum, frame) -> None:  # noqa: ARG001
            if not state["stopping"]:
                state["stopping"] = True
                self.stdout.write(f"signal {signum}: stop klaim baru; drain {drain_timeout:g}s")
                _arm_drain_timer()
                stop_event.set()  # bangunkan sleep segera (tidak menunggu interval)

        def _drain_deadline(signum, frame) -> None:  # noqa: ARG001
            raise engine.DrainRequested("batas waktu drain terlampaui")

        try:
            signal.signal(signal.SIGTERM, _request_stop)
            signal.signal(signal.SIGINT, _request_stop)
            signal.signal(signal.SIGALRM, _drain_deadline)
        except ValueError:  # pragma: no cover - bukan thread utama (uji proses selalu utama)
            pass
        # Marker kesiapan (flush): drain handler sudah terpasang — sinyal
        # yang tiba setelah baris ini ditangani sebagai drain, bukan kill
        # default. Uji proses memakai ini untuk deterministis (A08).
        self.stdout.write("worker siap: klaim dibuka, drain handler terpasang")
        self.stdout.flush()

        exit_code = EXIT_DRAINED
        try:
            while True:
                if state["stopping"]:
                    self.stdout.write("drain selesai: tidak ada klaim baru")
                    break
                expired = engine.reconcile_expired_leases()
                if state["stopping"]:
                    break
                job = engine.claim_next()
                if job is not None:
                    self.stdout.write(f"job {job.id} kind={job.kind} attempt={job.attempt}")
                    state["job_active"] = True
                    _arm_drain_timer()  # sinyal bisa tiba tepat sebelum klaim
                    try:
                        result = engine.run_claimed(job, stop_check=lambda: state["stopping"])
                    except engine.DrainRequested as exc:
                        # Job ditahan jujur di state durable (retry_wait/
                        # uncertain); proses keluar incomplete — bukan
                        # dibiarkan menggantung.
                        self.stdout.write(f"job {job.id} ditahan saat drain: {exc}")
                        exit_code = EXIT_DRAIN_DEADLINE
                        break
                    finally:
                        state["job_active"] = False
                        try:
                            signal.setitimer(signal.ITIMER_REAL, 0)
                        except (ValueError, OSError):  # pragma: no cover
                            pass
                    self.stdout.write(
                        f"job {job.id} → {result.state}" + (f" ({result.error_code})" if result.error_code else "")
                    )
                    if once:
                        break
                    continue
                dispatched = engine.dispatch_outbox()
                if expired or dispatched:
                    self.stdout.write(f"reconcile={expired} outbox={dispatched}")
                if once:
                    break
                if state["stopping"]:
                    break
                # Sleep yang dapat dibangunkan sinyal (REV-2011-06): SIGTERM
                # saat idle segera dievaluasi tanpa menunggu interval.
                stop_event.wait(interval)
        except engine.DrainRequested as exc:  # alarm liar di luar job aktif
            self.stdout.write(f"drain: batas waktu terlampaui: {exc}")
            exit_code = EXIT_DRAIN_DEADLINE
        finally:
            # Stop pasti: alarm tidak boleh menyala setelah loop bersih.
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except (ValueError, OSError):  # pragma: no cover
                pass
        if exit_code:
            raise SystemExit(exit_code)
