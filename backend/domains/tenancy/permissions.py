"""Bundel izin per peran — persis kontrak frontend (ARCHITECTURE.md §3).

Satu sumber kebenaran untuk backend; frontend menyimpan salinan untuk UX.
"""
from __future__ import annotations

PERMISSIONS: tuple[str, ...] = (
    "customers.read",
    "customers.write",
    "imports.run",
    "migration.run",
    "services.provision",
    "services.activate",
    "services.reveal_credentials",
    "routers.read",
    "routers.enroll",
    "routers.release",
    "routers.configure",
    "radius.cutover",
    "profiles.write",
    "backups.run",
    "backups.download",
    "payments.verify",
    "isolation.policy.manage",
    "collections.receive",
    "collections.settle",
    "vouchers.manage",
    "agents.manage",
    "devices.manage",
    "prospects.manage",
    "workorders.manage",
    "ledger.post",
    "period.close",
    "period.reopen",
    "subscription.manage",
    "team.manage",
    "platform.payments.approve",
    "platform.destinations.manage",
)

# Aksi sensitif: wajib TOTP + reauth 600 detik (ARCHITECTURE.md §3).
SENSITIVE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "radius.cutover",
        "services.reveal_credentials",
        "backups.download",
        "period.reopen",
        "team.manage",
        "subscription.manage",
        "platform.destinations.manage",
    }
)

_VIEWER = ("customers.read", "routers.read")
_OWNER = tuple(p for p in PERMISSIONS if not p.startswith("platform."))
_TECHNICIAN = (
    "customers.read",
    "customers.write",
    "routers.read",
    "routers.enroll",
    "services.provision",
    "services.reveal_credentials",
    "backups.run",
    "backups.download",
    "imports.run",
    "migration.run",
    "devices.manage",
    "workorders.manage",
    "prospects.manage",
)
_PAYMENTS_ADMIN = (
    "customers.read",
    "customers.write",
    "payments.verify",
    "services.activate",
    "services.reveal_credentials",
    "collections.receive",
    "collections.settle",
)
_ACCOUNTANT = (
    "customers.read",
    "ledger.post",
    "period.close",
    "period.reopen",
    "payments.verify",
)
_COLLECTOR = ("collections.receive",)
_AGENT: tuple[str, ...] = ()

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset(_OWNER),
    "technician": frozenset(_TECHNICIAN),
    "payments_admin": frozenset(_PAYMENTS_ADMIN),
    "accountant": frozenset(_ACCOUNTANT),
    "viewer": frozenset(_VIEWER),
    "collector": frozenset(_COLLECTOR),
    "agent": frozenset(_AGENT),
}


def permissions_for_role(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def is_sensitive(permission: str) -> bool:
    return permission in SENSITIVE_PERMISSIONS
