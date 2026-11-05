"""Konteks tenant PostgreSQL (RLS) — ARCHITECTURE.md §4.

Konteks tenant bersifat transaction-local: SET melalui set_config(..., true)
pada transaksi yang sama dengan query. Konteks kosong gagal tertutup
(policy membandingkan NULL → baris tidak terlihat).
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager

from django.db import transaction
from django.db.backends.base.base import BaseDatabaseWrapper


def _validate_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("tenant_id bukan UUID valid") from None


def set_tenant_context(db_wrapper_or_conn, tenant_id: str | uuid.UUID) -> None:
    """Atur GUC app.tenant_id pada transaksi berjalan (transaction-local)."""
    tenant = _validate_uuid(tenant_id)
    cursor = db_wrapper_or_conn.cursor()
    try:
        cursor.execute("SELECT set_config('app.tenant_id', %s, true)", [tenant])
    finally:
        cursor.close()


@contextmanager
def tenant_scope(tenant_id: str | uuid.UUID):
    """Buka transaksi dengan konteks tenant; semua query di dalam tunduk RLS.

    Reentrant (konsolidasi beta-0.1, port dari agent paralel): scope dalam
    (mis. service dipanggil dari view/handler yang sudah berjalan dalam
    scope) MENYIMPAN nilai sebelumnya dan memulihkannya saat keluar — bukan
    mereset ke kosong, yang akan memutus konteks scope luar.

    Tanpa scope luar: keluar dengan reset fail-closed (string kosong →
    policy NULL → tanpa baris) sehingga koneksi pooled/non-transaction
    tidak membawa konteks lama.
    """
    from django.db import connection

    tenant = _validate_uuid(tenant_id)
    previous = current_tenant_id()
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", [tenant])
            yield
    finally:
        try:
            with connection.cursor() as cur:
                if previous:
                    # Pulihkan nilai scope luar (transaction-local pada
                    # transaksi yang sama — keduanya is_local=true).
                    cur.execute(
                        "SELECT set_config('app.tenant_id', %s, true)", [previous]
                    )
                else:
                    # Fail-closed: reset sesi agar tidak ada konteks bocor.
                    cur.execute("SELECT set_config('app.tenant_id', '', false)")
        except Exception:  # pragma: no cover - koneksi bermasalah: biarkan fail-closed
            pass


def current_tenant_id() -> str | None:
    """Baca GUC pada koneksi aktif (untuk diagnostik/tes)."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT current_setting('app.tenant_id', true)")
        row = cur.fetchone()
    value = row[0] if row else None
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None
