"""Validasi kunci publik WireGuard host (murni, teruji unit).

Kunci berasal dari installer (`wg pubkey`): X25519 base64 tepat 32 byte
(44 karakter berpad NUL/=). Kunci privat TIDAK pernah masuk proses aplikasi.
"""
from __future__ import annotations

import base64
import binascii


def validate_public_key(value: str) -> str:
    """Normalisasi + validasi kunci publik X25519.

    - Kosong (setelah strip) → "" (fallback dev deterministik, jujur).
    - Valid → nilai ternormalisasi.
    - Salah format/panjang → ValueError (settings memetakannya ke
      ImproperlyConfigured saat boot — gagal cepat, bukan senyap).
    """
    value = (value or "").strip()
    if not value:
        return ""
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"bukan base64 valid: {exc}") from None
    if len(raw) != 32:
        raise ValueError(f"bukan kunci 32-byte X25519 (dapat {len(raw)} byte)")
    return value
