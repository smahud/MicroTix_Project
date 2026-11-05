"""TOTP RFC 6238 — implementasi tanpa dependensi eksternal.

- HMAC-SHA1, 6 digit, langkah 30 detik, jendela ±1.
- Seed base32; verifikasi mencatat langkah terpakai untuk mencegah replay
  kode sama dalam jendela (kode tidak boleh dipakai dua kali).
- Uji vektor resmi RFC 6238 Appendix B ada di tests/unit/test_totp.py.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

STEP_S = 30
DIGITS = 6
WINDOW = 1  # ±1 langkah (30s)


def generate_seed() -> str:
    """Seed 160-bit base32 (CSPRNG)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _hotp(seed: bytes, step: int) -> str:
    msg = struct.pack(">Q", step)
    digest = hmac.new(seed, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**DIGITS)
    return str(code).zfill(DIGITS)


def decode_seed(seed_b32: str) -> bytes:
    padded = seed_b32 + "=" * (-len(seed_b32) % 8)
    return base64.b32decode(padded, casefold=True)


def totp_at(seed_b32: str, timestamp_s: int | float) -> str:
    return _hotp(decode_seed(seed_b32), int(timestamp_s) // STEP_S)


def verify(
    seed_b32: str,
    code: str,
    *,
    at_s: int | None = None,
    last_used_step: int | None = None,
) -> int | None:
    """Verifikasi kode 6 digit dalam jendela ±1.

    Mengembalikan langkah yang cocok (untuk dicatat anti-replay),
    atau None bila tidak valid. Kode pada langkah ≤ last_used_step ditolak.
    """
    if not code or not code.isdigit() or len(code) != DIGITS:
        return None
    now = int(at_s if at_s is not None else time.time())
    current = now // STEP_S
    seed = decode_seed(seed_b32)
    for step in (current - WINDOW, current, current + WINDOW):
        if step < 0:
            continue
        if last_used_step is not None and step <= last_used_step:
            continue
        expected = _hotp(seed, step)
        if hmac.compare_digest(expected, code):
            return step
    return None


def provisioning_uri(seed_b32: str, email: str, issuer: str = "MicroTix") -> str:
    from urllib.parse import quote

    return (
        f"otpauth://totp/{quote(issuer)}:{quote(email)}"
        f"?secret={seed_b32}&issuer={quote(issuer)}&algorithm=SHA1&digits={DIGITS}&period={STEP_S}"
    )
