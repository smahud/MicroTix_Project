"""Antarmuka adapter RouterOS — ROUTEROS.md §4.

Interface kecil: discover_capabilities, list_accounts, read_object,
plan_action, apply_action, verify_action, create_backup, read_health;
domain cutover install_radius_client/set_aaa/resolve_local_shadow/
rollback_radius; dispatcher Disconnect. Semua menerima konteks router
terdaftar — tidak ada command/URL bebas dari tenant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class RouterContext:
    """Konteks router terdaftar dari registry — bukan input bebas tenant."""

    router_id: str
    tenant_id: str
    tunnel_ip: str | None
    api_port: int = 8729
    mode: str = "read_only"
    routeros_version: str = "7.15"
    architecture: str = "arm64"
    credential_ref: str = ""
    # Pin sertifikat API-SSL (SHA-256 hex) dari enrollment (TK-304).
    cert_pin: str = ""


@dataclass
class Capability:
    """Capability per fungsi — bukan asumsi per merek (ROUTEROS.md §1)."""

    name: str
    supported: bool
    evidence: str = ""


@dataclass
class PlannedChange:
    """Satu perubahan terencana pada objek RouterOS."""

    object_type: str  # ppp_secret, hotspot_user, radius_client, wireguard_peer...
    natural_key: str
    action: str  # add | set | remove
    desired: dict[str, Any]
    current: dict[str, Any] | None = None
    fingerprint: str = ""


@dataclass
class ChangePlan:
    """Plan immutable setelah disetujui (ARCHITECTURE §6)."""

    router: RouterContext
    baseline_revision: str
    changes: list[PlannedChange] = field(default_factory=list)
    recovery: str = ""
    verification: list[str] = field(default_factory=list)


class RouterOsError(Exception):
    code = "router_error"

    def __init__(self, message: str = "") -> None:
        self.message = message or self.code
        super().__init__(self.message)


class PermissionDeniedError(RouterOsError):
    code = "permission_denied"


class UnreachableError(RouterOsError):
    code = "router_unreachable"


class TimeoutAfterSendError(RouterOsError):
    """Timeout SETELAH perintah terkirim → hasil tak pasti (uncertain)."""

    code = "timeout_after_send"


class RevisionConflictError(RouterOsError):
    code = "revision_conflict"


class RouterOsAdapter(Protocol):
    """Kontrak adapter — implementasi: simulator (dev) & klien API-SSL (M3)."""

    def discover_capabilities(self, ctx: RouterContext) -> list[Capability]: ...

    def list_accounts(self, ctx: RouterContext, *, kind: str = "pppoe") -> list[dict]: ...

    def read_object(self, ctx: RouterContext, object_type: str, natural_key: str) -> dict | None: ...

    def plan_action(self, ctx: RouterContext, desired: dict) -> ChangePlan: ...

    def apply_action(self, ctx: RouterContext, plan: ChangePlan) -> list[dict]: ...

    def verify_action(self, ctx: RouterContext, plan: ChangePlan) -> dict: ...

    def create_backup(self, ctx: RouterContext, *, category: str) -> dict: ...

    def read_health(self, ctx: RouterContext) -> dict: ...

    # Domain cutover RADIUS (RADIUS.md B0–B6) — diaktifkan pada fase M3.
    def install_radius_client(self, ctx: RouterContext, config: dict) -> ChangePlan: ...

    def set_aaa(self, ctx: RouterContext, config: dict) -> ChangePlan: ...

    def resolve_local_shadow(self, ctx: RouterContext, plan: dict) -> ChangePlan: ...

    def rollback_radius(self, ctx: RouterContext, baseline: dict) -> ChangePlan: ...

    def disconnect_session(self, ctx: RouterContext, session_id: str) -> dict: ...
