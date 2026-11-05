"""Paginasi kursor — ARCHITECTURE.md §5.

Kursor opaque urutan stabil (sort_key,id); limit default 50 maks 200;
> maks, ≤ 0, atau kursor rusak ditolak 422 validation_error.
"""
from __future__ import annotations

import base64
import binascii
import struct
from typing import Any, TypeVar

from domains.common.envelope import ApiError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

T = TypeVar("T")


def encode_cursor(sort_key: Any, last_id: str) -> str:
    """Kursor opaque: base64(payload 'sq|<sort_key>|<id>') — '|' tak muncul di sort_key/uuid."""
    raw = f"sq|{sort_key}|{last_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, str]:
    """Balikkan kursor; kursor rusak → 422."""
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + pad).decode()
        prefix, sort_key, last_id = raw.split("|", 2)
        if prefix != "sq" or not last_id:
            raise ValueError
        return sort_key, last_id
    except (ValueError, binascii.Error, UnicodeDecodeError, struct.error):
        raise ApiError.validation(
            field_errors={"cursor": [{"code": "invalid", "message": "Kursor tidak valid"}]}
        ) from None


def parse_limit(raw: Any) -> int:
    if raw is None:
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        raise ApiError.validation(
            field_errors={"limit": [{"code": "integer", "message": "limit harus bilangan bulat"}]}
        ) from None
    if limit <= 0 or limit > MAX_LIMIT:
        raise ApiError.validation(
            field_errors={
                "limit": [
                    {
                        "code": "out_of_range",
                        "message": f"limit harus 1..{MAX_LIMIT}",
                    }
                ]
            }
        )
    return limit


def page_response(items: list[T], next_cursor: str | None) -> dict:
    return {"items": items, "next_cursor": next_cursor}
