"""Registri konfigurasi defaults.json — kunci tak dikenal, bounds, snapshot."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from domains.common.envelope import ApiError
from domains.common.pagination import MAX_LIMIT, decode_cursor, encode_cursor, parse_limit
from domains.config.registry import ConfigRegistry, RELEASE_FLAGS

DOC = json.loads((Path(__file__).resolve().parents[3] / "docs" / "defaults.json").read_text())


def test_registry_loads_all_parameters():
    reg = ConfigRegistry(DOC)
    assert len(reg.parameters) == 115  # 2.3: +vpn.gateway_hostname (skrip bootstrap)
    assert reg.revision == "2.3"


def test_unknown_key_rejected():
    reg = ConfigRegistry(DOC)
    with pytest.raises(KeyError):
        reg.get("tidak.ada")


def test_approved_default_only_bounds():
    reg = ConfigRegistry(DOC)
    assert reg.get_int("job.lease_s") == 30
    os.environ["MT_OVERRIDE_JOB__LEASE_S"] = "31"
    try:
        reg2 = ConfigRegistry(DOC)
        reg2._loaded_env = set()
        with pytest.raises(ValueError):
            reg2.get("job.lease_s")
    finally:
        del os.environ["MT_OVERRIDE_JOB__LEASE_S"]


def test_snapshot_is_dict_of_known_keys():
    reg = ConfigRegistry(DOC)
    snap = reg.snapshot(["job.lease_s", "auth.password_min_chars"])
    assert snap == {"job.lease_s": 30, "auth.password_min_chars": 12}


def test_release_flags_r1_only():
    assert RELEASE_FLAGS["R1"] is True
    assert all(not RELEASE_FLAGS[k] for k in ("R2", "R3", "R4"))


# --- paginasi kursor (§5) ---


def test_parse_limit_bounds():
    assert parse_limit(None) == 50
    assert parse_limit("1") == 1
    assert parse_limit(str(MAX_LIMIT)) == MAX_LIMIT
    for bad in ("0", "-1", "201", "abc"):
        with pytest.raises(ApiError):
            parse_limit(bad)


def test_cursor_roundtrip_and_garbage():
    cur = encode_cursor("2026-01-01T00:00:00+00:00", "abc-123")
    sort_key, last_id = decode_cursor(cur)
    assert sort_key == "2026-01-01T00:00:00+00:00"
    assert last_id == "abc-123"
    for garbage in ("x", "!!!", "c3FfYWJj"):
        with pytest.raises(ApiError):
            decode_cursor(garbage)
