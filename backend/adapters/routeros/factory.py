"""Selektor adapter RouterOS aktif — konsolidasi beta-0.1 (port dari be2).

Default: simulator deterministik (dev/test). Klien API-SSL native aktif
melalui MT_ROUTEROS_ADAPTER=api_ssl — untuk jalur produksi setelah bukti
lab G1 (adapter menolak mutasi dengan kode pending_lab sampai lulus lab,
jadi aktifasi dini tidak bisa mengklaim integrasi palsu).
"""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from adapters.routeros.base import RouterOsAdapter
from adapters.routeros.simulator import RouterOsSimulator

_ALLOWED = ("simulator", "api_ssl")


def active_routeros_adapter() -> RouterOsAdapter:
    """Adapter aktif sesuai settings.MT_ROUTEROS_ADAPTER (default simulator)."""
    from django.conf import settings

    choice = getattr(settings, "MT_ROUTEROS_ADAPTER", "simulator")
    if choice == "simulator":
        return RouterOsSimulator()
    if choice == "api_ssl":
        from adapters.routeros.apiclient import ApiSslAdapter

        return ApiSslAdapter()
    raise ImproperlyConfigured(
        f"MT_ROUTEROS_ADAPTER tidak sah: {choice!r} (pilihan: {'|'.join(_ALLOWED)})"
    )


def active_adapter_name() -> str:
    """Nama adapter aktif — untuk catatan evidence jujur (bukan klaim lab)."""
    from django.conf import settings

    return getattr(settings, "MT_ROUTEROS_ADAPTER", "simulator")
