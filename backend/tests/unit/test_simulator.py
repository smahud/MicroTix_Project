"""Simulator RouterOS — deterministik + failure injection (TK-004)."""
from __future__ import annotations

import pytest

from adapters.routeros.base import (
    PermissionDeniedError,
    RevisionConflictError,
    RouterContext,
    TimeoutAfterSendError,
    UnreachableError,
)
from adapters.routeros.simulator import FaultInjection, RouterOsSimulator

CTX = RouterContext(router_id="r-1", tenant_id="t-1", tunnel_ip="10.99.0.2", mode="managed")


def test_capabilities_v7_managed():
    sim = RouterOsSimulator()
    caps = {c.name: c.supported for c in sim.discover_capabilities(CTX)}
    assert caps["radius_client_manage"] is True
    assert caps["api_ssl"] is True
    assert caps["backup"] is True


def test_capabilities_read_only_blocks_radius_manage():
    sim = RouterOsSimulator()
    ctx = RouterContext(router_id="r-2", tenant_id="t-1", tunnel_ip=None, mode="read_only")
    caps = {c.name: c.supported for c in sim.discover_capabilities(ctx)}
    assert caps["radius_client_manage"] is False
    assert caps["read_accounts"] is True


def test_list_accounts_never_returns_password():
    sim = RouterOsSimulator()
    router = sim.register(CTX, seed_accounts=6)
    router.accounts[0]["password"] = "super-secret"
    accounts = sim.list_accounts(CTX, kind="any")
    assert all("password" not in a for a in accounts)
    assert len(accounts) == 6


def test_plan_apply_verify_roundtrip():
    sim = RouterOsSimulator()
    plan = sim.plan_action(CTX, {"objects": [{"object_type": "radius_client", "natural_key": "mtx", "desired": {"service": "ppp", "address": "10.99.0.1"}}]})
    assert plan.changes[0].action == "add"
    sim.apply_action(CTX, plan)
    result = sim.verify_action(CTX, plan)
    assert result["verified"] is True
    # Plan lama (baseline revision berubah) → revision_conflict
    with pytest.raises(RevisionConflictError):
        sim.apply_action(CTX, plan)


def test_fault_unreachable():
    sim = RouterOsSimulator()
    sim.register(CTX, faults=FaultInjection(unreachable=True))
    with pytest.raises(UnreachableError):
        sim.read_health(CTX)


def test_fault_permission_denied():
    sim = RouterOsSimulator()
    sim.register(CTX, faults=FaultInjection(permission_denied=True))
    plan = sim.plan_action(CTX, {"objects": [{"object_type": "ppp_secret", "natural_key": "u1", "desired": {"disabled": True}}]})
    with pytest.raises(PermissionDeniedError):
        sim.apply_action(CTX, plan)


def test_fault_timeout_after_send_yields_uncertain_semantics():
    """Kunci: perintah sudah tercatat terkirim saat timeout → hasil tak pasti."""
    sim = RouterOsSimulator()
    sim.register(CTX, faults=FaultInjection(timeout_after_send=True))
    plan = sim.plan_action(CTX, {"objects": [{"object_type": "ppp_secret", "natural_key": "u1", "desired": {"disabled": True}}]})
    with pytest.raises(TimeoutAfterSendError):
        sim.apply_action(CTX, plan)
    router = sim.router(CTX)
    assert router.sent_commands, "perintah harus tercatat terkirim sebelum timeout"
    # Objek TIDAK diterapkan pada simulator ini — readback diperlukan sebelum retry.
    assert ("ppp_secret", "u1") not in router.objects


def test_drift_after_apply_fails_verification():
    sim = RouterOsSimulator()
    sim.register(CTX, faults=FaultInjection(drift_after_apply=True))
    plan = sim.plan_action(CTX, {"objects": [{"object_type": "ppp_secret", "natural_key": "u1", "desired": {"disabled": True}}]})
    sim.apply_action(CTX, plan)
    result = sim.verify_action(CTX, plan)
    assert result["verified"] is False
