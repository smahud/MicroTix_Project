"""Registri konfigurasi — defaults.json sebagai satu-sumber nilai teknis (TK-107).

- Tipe/bounds/scope divalidasi; kunci tak dikenal ditolak.
- Nilai dapat dioverride environment (MT_OVERRIDE_<key>=<json>) hanya bila
  bounds mengizinkan; snapshot per job/dokumen memakai nilai resolved.
- Release flag fase fitur; parameter fase lanjut tidak aktif sebelum fiturnya.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from domains.common.envelope import ApiError


@dataclass(frozen=True)
class Parameter:
    key: str
    type: str
    default: object
    scope: str
    bounds: dict | None
    nullable: bool = False


class ConfigRegistry:
    def __init__(self, doc: dict) -> None:
        self.parameters: dict[str, Parameter] = {}
        self.rules: list[str] = list(doc.get("rules", []))
        self.formulas: dict[str, str] = dict(doc.get("formulas", {}))
        self.revision: str = str(doc.get("revision", ""))
        seen: set[str] = set()
        for entry in doc.get("parameters", []):
            key = entry["key"]
            if key in seen:
                raise ValueError(f"Kunci duplikat: {key}")
            seen.add(key)
            self.parameters[key] = Parameter(
                key=key,
                type=entry["type"],
                default=entry["default"],
                scope=entry.get("scope", "deployment"),
                bounds=entry.get("bounds"),
                nullable=bool(entry.get("nullable", False)),
            )
        self._values: dict[str, object] = {k: p.default for k, p in self.parameters.items()}

    # --- akses ---

    def get(self, key: str) -> object:
        if key not in self.parameters:
            raise KeyError(f"Kunci konfigurasi tak dikenal: {key}")
        # Override environment valid-bounds (MT_OVERRIDE_<key>).
        env_name = "MT_OVERRIDE_" + key.upper().replace(".", "__")
        if env_name in os.environ and env_name not in getattr(self, "_loaded_env", set()):
            value = json.loads(os.environ[env_name])
            self._validate(key, value)
            self._values[key] = value
            getattr(self, "_loaded_env").add(env_name)
        return self._values[key]

    def get_int(self, key: str) -> int:
        return int(self.get(key))  # type: ignore[arg-type]

    def snapshot(self, keys: list[str] | None = None) -> dict:
        """Snapshot immutable untuk job/dokumen (default→override sah)."""
        wanted = keys or list(self.parameters.keys())
        return {k: self.get(k) for k in wanted if k in self.parameters}

    def _validate(self, key: str, value: object) -> None:
        param = self.parameters[key]
        bounds = param.bounds or {}
        mode = bounds.get("mode")
        if mode == "range":
            lo, hi = bounds.get("minimum"), bounds.get("maximum")
            if isinstance(value, (int, float)) and (lo is not None and value < lo or hi is not None and value > hi):
                raise ValueError(f"{key} di luar bounds {lo}..{hi}")
        elif mode == "approved_default_only":
            allowed = bounds.get("allowed")
            if allowed is not None and value not in allowed:
                raise ValueError(f"{key} hanya boleh {allowed}")
        if param.type == "integer" and not isinstance(value, int):
            raise ValueError(f"{key} harus integer")
        if param.type == "string" and not isinstance(value, str):
            raise ValueError(f"{key} harus string")

    def validate_all_overrides(self) -> None:
        for key in self.parameters:
            self.get(key)


_REGISTRY: ConfigRegistry | None = None


def registry() -> ConfigRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        from django.conf import settings

        path = Path(settings.MT_DOCS_DIR) / "defaults.json"
        doc = json.loads(path.read_text())
        _REGISTRY = ConfigRegistry(doc)
        _REGISTRY._loaded_env = set()  # type: ignore[attr-defined]
        _REGISTRY.validate_all_overrides()
    return _REGISTRY


# --- Release flags fase (R1 aktif; R2-R4 sesuai roadmap PRODUCT.md §2) ---
RELEASE_FLAGS: dict[str, bool] = {
    "R1": True,
    "R2": False,
    "R3": False,
    "R4": False,
}
