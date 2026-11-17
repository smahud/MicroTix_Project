"""Handler drain untuk uji proses nyata (J20-A08 / task0020).

Dipakai tests.drain_worker (subprocess worker terpisah) — bukan handler
produksi. Sentinel berbasis FILE agar terlihat lintas proses.
"""
from __future__ import annotations

import os
import time

from domains.jobs.engine import JobContext, JobHandler, register


class DrainDbHandler(JobHandler):
    """Job DB kooperatif cepat: selesai tanpa blokir (drain menyelesaikannya)."""

    kind = "_test_drain_db"

    def execute(self, ctx: JobContext) -> dict:
        return {"ok": True, "kind": "db"}

    def verify(self, ctx: JobContext) -> dict:
        return {"ok": True}


class DrainIoHandler(JobHandler):
    """Job I/O terblokir: menunggu file sentinel muncul (payload.sentinel).

    Mensimulasikan send/readback jaringan yang terblokir — tidak menyentuh
    DB selama menunggu; drain deadline akan memotongnya (DrainRequested).
    """

    kind = "_test_drain_io"

    def execute(self, ctx: JobContext) -> dict:
        sentinel = str(ctx.payload.get("sentinel") or "")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if sentinel and os.path.exists(sentinel):
                return {"ok": True, "kind": "io", "sentinel_seen": True}
            time.sleep(0.05)
        return {"ok": True, "kind": "io", "sentinel_seen": False}

    def verify(self, ctx: JobContext) -> dict:
        return {"ok": True}


def register_all() -> None:
    for handler in (DrainDbHandler(), DrainIoHandler()):
        try:
            register(handler)
        except ValueError:  # pragma: no cover - sudah terdaftar di sesi sama
            pass
