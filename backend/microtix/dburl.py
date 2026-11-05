"""Parser DATABASE_URL minimal (tanpa dependensi tambahan).

Mendukung postgresql://user:password@host:port/dbname?sslmode=...
Kredensial tidak pernah di-log.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class DbConfig:
    engine: str
    name: str
    user: str
    password: str
    host: str
    port: int
    options: dict[str, str]

    def as_django(self) -> dict:
        cfg = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": str(self.port),
            "CONN_MAX_AGE": int(os.environ.get("MT_CONN_MAX_AGE", "60")),
            # application_name memudahkan audit pg_stat_activity tanpa membocorkan data.
            "OPTIONS": {"application_name": os.environ.get("MT_APP_NAME_DB", "microtix")},
        }
        if self.options.get("sslmode"):
            cfg["OPTIONS"]["sslmode"] = self.options["sslmode"]
        return cfg


def parse_db_url(url: str) -> DbConfig:
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL harus postgresql://")
    options: dict[str, str] = {}
    if parsed.query:
        for part in parsed.query.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                options[unquote(k)] = unquote(v)
    return DbConfig(
        engine="django.db.backends.postgresql",
        name=unquote(parsed.path.lstrip("/")),
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 5432,
        options=options,
    )
