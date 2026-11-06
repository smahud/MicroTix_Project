"""Simulator RouterOS deterministik + failure injection — TK-004.

Tujuan: menguji engine job, plan/verify, dan path galat TANPA klaim
perangkat terverifikasi (hasil simulator tidak pernah menjadi verified_lab).
Fault setelah kirim menghasilkan TimeoutAfterSendError → engine menandai
job uncertain, bukan failed (invariant ARCHITECTURE §6).

State disimpan per router_id dalam proses (deterministik dari seed);
pengujian ulang memakai instance baru.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from adapters.routeros.base import (
    Capability,
    ChangePlan,
    PlannedChange,
    PermissionDeniedError,
    RevisionConflictError,
    RouterContext,
    RouterOsError,
    TimeoutAfterSendError,
    UnreachableError,
)

CAPABILITIES_V7 = [
    "read_accounts",
    "read_profiles",
    "read_health",
    "read_interfaces",
    "api_ssl",
    "radius_client_manage",
    "disconnect_session",
    "backup",
]
CAPABILITIES_V6 = ["read_accounts", "read_profiles", "read_health", "read_interfaces", "backup"]


@dataclass
class FaultInjection:
    """Skenario galat untuk pengujian (default: tanpa galat)."""

    unreachable: bool = False
    permission_denied: bool = False
    timeout_after_send: bool = False  # → uncertain
    revision_bump_before_apply: bool = False  # → revision_conflict
    drift_after_apply: bool = False  # verify gagal setelah apply


@dataclass
class SimulatedRouter:
    ctx: RouterContext
    revision: str = "r0"
    objects: dict[tuple[str, str], dict] = field(default_factory=dict)
    accounts: list[dict] = field(default_factory=list)
    faults: FaultInjection = field(default_factory=FaultInjection)
    sent_commands: list[str] = field(default_factory=list)

    def fingerprint(self, obj: dict) -> str:
        canonical = "|".join(f"{k}={obj.get(k)}" for k in sorted(obj))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class RouterOsSimulator:
    """Adapter simulator — deterministik dari konteks + state eksplisit."""

    def __init__(self) -> None:
        self._routers: dict[str, SimulatedRouter] = {}

    # --- pengaturan pengujian ---

    def register(self, ctx: RouterContext, *, faults: FaultInjection | None = None, seed_accounts: int = 0) -> SimulatedRouter:
        rng = random.Random(f"seed:{ctx.router_id}")
        router = SimulatedRouter(ctx=ctx, faults=faults or FaultInjection())
        for i in range(seed_accounts):
            kind = "pppoe" if i % 2 == 0 else "hotspot"
            router.accounts.append(
                {
                    "name": f"cust-{i:03d}",
                    "kind": kind,
                    "profile": "PROFILE-10M" if kind == "pppoe" else "hc-1d",
                    "disabled": rng.random() < 0.1,
                    "comment": f"legacy {i}",
                    ".id": f"*{i + 10:X}",
                }
            )
        self._routers[ctx.router_id] = router
        return router

    def router(self, ctx: RouterContext) -> SimulatedRouter:
        router = self._routers.get(ctx.router_id)
        if router is None:
            router = self.register(ctx)
            self._routers[ctx.router_id] = router
        return router

    def _guard(self, ctx: RouterContext) -> SimulatedRouter:
        router = self.router(ctx)
        if router.faults.unreachable:
            raise UnreachableError()
        return router

    # --- kontrak adapter ---

    def probe_connectivity(self, ctx: RouterContext) -> dict:
        """Simulator TIDAK melakukan koneksi nyata — hasil jujur (§2.8).

        Dipanggil hanya pada jalur adapter aktif non-simulator; jika dipanggil
        pada simulator, kembalikan performed=False — jangan pernah mengklaim
        probe nyata berhasil (hasil simulator tidak menjadi verified_lab).
        """
        return {"ok": False, "performed": False, "error": "simulator_no_real_connection"}

    def discover_capabilities(self, ctx: RouterContext) -> list[Capability]:
        router = self._guard(ctx)
        base = CAPABILITIES_V7 if ctx.routeros_version.startswith("7") else CAPABILITIES_V6
        caps = []
        for name in base:
            supported = name in base and not (name == "radius_client_manage" and ctx.mode == "read_only")
            caps.append(
                Capability(
                    name=name,
                    supported=supported,
                    evidence=f"simulator:{ctx.routeros_version}:{ctx.architecture}",
                )
            )
        return caps

    def list_accounts(self, ctx: RouterContext, *, kind: str = "pppoe") -> list[dict]:
        router = self._guard(ctx)
        # Discovery tidak membaca password (ROUTEROS.md §3).
        return [
            {k: v for k, v in acc.items() if k != "password"}
            for acc in router.accounts
            if kind == "any" or acc["kind"] == kind
        ]

    def read_object(self, ctx: RouterContext, object_type: str, natural_key: str) -> dict | None:
        router = self._guard(ctx)
        return router.objects.get((object_type, natural_key))

    def plan_action(self, ctx: RouterContext, desired: dict) -> ChangePlan:
        router = self._guard(ctx)
        changes: list[PlannedChange] = []
        for obj in desired.get("objects", []):
            key = obj["natural_key"]
            current = router.objects.get((obj["object_type"], key))
            changes.append(
                PlannedChange(
                    object_type=obj["object_type"],
                    natural_key=key,
                    action="set" if current else "add",
                    desired=obj["desired"],
                    current=current,
                    fingerprint=router.fingerprint(obj["desired"]),
                )
            )
        return ChangePlan(
            router=ctx,
            baseline_revision=router.revision,
            changes=changes,
            recovery="Hapus objek yang ditambahkan; kembalikan field yang diubah",
            verification=[f"readback:{c.object_type}:{c.natural_key}" for c in changes],
        )

    def apply_action(self, ctx: RouterContext, plan: ChangePlan) -> list[dict]:
        router = self._guard(ctx)
        if router.faults.permission_denied:
            raise PermissionDeniedError()
        if plan.baseline_revision != router.revision:
            raise RevisionConflictError()
        if router.faults.revision_bump_before_apply:
            router.revision = "r" + str(int(router.revision[1:]) + 1)
            raise RevisionConflictError()
        applied: list[dict] = []
        for change in plan.changes:
            # Perintah tercatat 'terkirim' sebelum fault timeout — hasil tak pasti.
            router.sent_commands.append(f"{change.action} {change.object_type} {change.natural_key}")
            if router.faults.timeout_after_send:
                raise TimeoutAfterSendError()
            router.objects[(change.object_type, change.natural_key)] = dict(change.desired)
            applied.append(
                {
                    "object_type": change.object_type,
                    "natural_key": change.natural_key,
                    "action": change.action,
                    "fingerprint": router.fingerprint(change.desired),
                }
            )
        router.revision = "r" + str(int(router.revision[1:]) + 1)
        if router.faults.drift_after_apply and applied:
            # Objek terakhir diubah pihak lain setelah apply (drift).
            key = (applied[-1]["object_type"], applied[-1]["natural_key"])
            if key in router.objects:
                router.objects[key]["__drifted"] = True
        return applied

    def verify_action(self, ctx: RouterContext, plan: ChangePlan) -> dict:
        router = self._guard(ctx)
        results = []
        all_ok = True
        for change in plan.changes:
            obj = router.objects.get((change.object_type, change.natural_key))
            expected = {k: v for k, v in change.desired.items()}
            ok = obj is not None and all(obj.get(k) == v for k, v in expected.items()) and "__drifted" not in obj
            all_ok = all_ok and ok
            results.append({"natural_key": change.natural_key, "verified": ok})
        return {"verified": all_ok, "objects": results, "revision": router.revision}

    def create_backup(self, ctx: RouterContext, *, category: str) -> dict:
        router = self._guard(ctx)
        token = hashlib.sha256(f"{ctx.router_id}:{category}:{router.revision}".encode()).hexdigest()
        return {
            "category": category,
            "simulated": True,
            "size_bytes": 1024 * 1024,
            "hash": token,
            "revision": router.revision,
        }

    def read_health(self, ctx: RouterContext) -> dict:
        self._guard(ctx)
        rng = random.Random(f"health:{ctx.router_id}")
        return {
            "cpu_percent": rng.randint(3, 40),
            "memory_percent": rng.randint(20, 70),
            "uptime_s": rng.randint(3600, 999999),
            "interfaces": [
                {"name": "wg-mtx", "enabled": True, "running": True},
                {"name": "ether1", "enabled": True, "running": True},
            ],
            "observed_at": None,  # diisi pemanggil (waktu nyata)
        }

    # --- domain cutover (implementasi minim untuk pengujian engine M3) ---

    def install_radius_client(self, ctx: RouterContext, config: dict) -> ChangePlan:
        desired = {
            "objects": [
                {"object_type": "radius_client", "natural_key": config.get("name", "mtx-radius"), "desired": config}
            ]
        }
        return self.plan_action(ctx, desired)

    def set_aaa(self, ctx: RouterContext, config: dict) -> ChangePlan:
        desired = {"objects": [{"object_type": "aaa", "natural_key": "default", "desired": config}]}
        return self.plan_action(ctx, desired)

    def resolve_local_shadow(self, ctx: RouterContext, plan: dict) -> ChangePlan:
        desired = {"objects": [{"object_type": "ppp_secret", "natural_key": plan["username"], "desired": {"disabled": True}}]}
        return self.plan_action(ctx, desired)

    def rollback_radius(self, ctx: RouterContext, baseline: dict) -> ChangePlan:
        return self.plan_action(ctx, {"objects": baseline.get("objects", [])})

    def disconnect_session(self, ctx: RouterContext, session_id: str) -> dict:
        router = self._guard(ctx)
        router.sent_commands.append(f"remove session {session_id}")
        if router.faults.timeout_after_send:
            raise TimeoutAfterSendError()
        return {"session_id": session_id, "disconnected": True}
