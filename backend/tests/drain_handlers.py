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


class DrainActiveHandler(JobHandler):
    """Job DB kooperatif dengan BARRIER (REV-1711-09 / A08).

    Fase pertama melaporkan progress (commit DB), lalu menunggu file sentinel
    (barrier) sebelum unit DB kedua + progress akhir. Sinyal drain yang tiba
    SELAMA fase aktif membuktikan: job kooperatif diselesaikan (exit 0),
    bukan ditahan — sementara klaim baru sudah dihentikan.
    """

    kind = "_test_drain_active"

    def execute(self, ctx: JobContext) -> dict:
        # Efek durable fase aktif ini adalah tulisan envelope/progress job
        # (CAS lease: items_done/phase_label + perpanjangan lease), BUKAN
        # unit domain — mapping evidence A08 (REV-1711-09 R2) menyatakan
        # ini secara eksplisit, tanpa mengklaim transaksi domain.
        ctx.progress(phase="active-1", done=1, total=2)
        sentinel = str(ctx.payload.get("sentinel") or "")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if sentinel and os.path.exists(sentinel):
                break
            time.sleep(0.05)
        with ctx.scope():
            # Unit DB kedua pendek (efek DB kooperatif di balik barrier) —
            # guard entry+commit terkunci; payload dibaca sebagai bagian
            # unit, bukan efek domain tersendiri.
            _ = ctx.payload
        ctx.progress(phase="active-2", done=2, total=2)
        return {"ok": True, "kind": "active", "sentinel_seen": bool(sentinel)}

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
    for handler in (DrainDbHandler(), DrainActiveHandler(), DrainIoHandler()):
        try:
            register(handler)
        except ValueError:  # pragma: no cover - sudah terdaftar di sesi sama
            pass
