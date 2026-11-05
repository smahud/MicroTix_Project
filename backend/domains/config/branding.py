"""Resolusi branding — branding.json + override environment (ARCHITECTURE §9).

PROJECT_NAME mengalir ke APP_NAME/BRAND_NAME bila override khusus tidak ada.
Nama display tidak pernah menjadi nama DB/cookie/UUID/prefix API.
Landing publik menolak rilis bila BRAND_* kosong (publication_blocked).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def resolve_branding() -> dict:
    from django.conf import settings

    path = Path(settings.MT_DOCS_DIR) / "branding.json"
    doc = json.loads(path.read_text()) if path.exists() else {}
    env_project = (os_env("PROJECT_NAME") or "").strip()
    env_app = (os_env("APP_NAME") or "").strip()
    env_brand = (os_env("BRAND_NAME") or "").strip()
    project = env_project or doc.get("project_name", "MicroTix")
    resolved = {
        "project_name": project,
        "app_name": env_app or doc.get("app_name") or project,
        "brand_name": env_brand or doc.get("brand_name") or project,
        "tagline": doc.get("tagline", ""),
        "contact": doc.get("contact", {}),
        "privacy_url": doc.get("privacy_url", ""),
        "terms_url": doc.get("terms_url", ""),
    }
    # Gate publikasi: landing menolak rilis bila identitas publik kosong.
    resolved["publication_blocked"] = not (
        resolved["brand_name"] and resolved["contact"].get("email") and resolved["privacy_url"]
    )
    return resolved


def os_env(name: str) -> str | None:
    import os

    return os.environ.get(name)
