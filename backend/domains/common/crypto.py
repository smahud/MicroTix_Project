"""Kripto rahasia tingkat aplikasi — ARCHITECTURE.md §7.

- SecretBox: AEAD AES-256-GCM (cryptography) untuk rahasia yang harus dapat
  dibaca kembali (seed TOTP). Kunci berasal dari env (di luar DB).
- Token: CSPRNG + penyimpanan hash (SHA-256) — token enroll/verifikasi email
  tidak pernah disimpan plaintext.
- Kode pemulihan: HMAC-SHA256 dengan pepper server (kode 128-bit CSPRNG,
  brute force 2^128 tidak praktis; perbandingan konstan-waktu).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LEN = 12
_TAG_HINT = b"mtx1"


def _key() -> bytes:
    from django.conf import settings

    raw = getattr(settings, "MT_SECRET_BOX_KEY", "")
    if not raw:
        raise RuntimeError("MT_SECRET_BOX_KEY belum dikonfigurasi")
    return hashlib.sha256(raw.encode()).digest()


class SecretBox:
    """Enkripsi-dekripsi AEAD untuk rahasia yang perlu dibaca ulang."""

    @staticmethod
    def encrypt(plaintext: str | bytes) -> str:
        data = plaintext.encode() if isinstance(plaintext, str) else plaintext
        nonce = os.urandom(_NONCE_LEN)
        box = AESGCM(_key())
        ct = box.encrypt(nonce, data, _TAG_HINT)
        return base64.urlsafe_b64encode(nonce + ct).decode()

    @staticmethod
    def decrypt(token: str) -> bytes:
        raw = base64.urlsafe_b64decode(token.encode())
        nonce, ct = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
        box = AESGCM(_key())
        return box.decrypt(nonce, ct, _TAG_HINT)

    @staticmethod
    def decrypt_str(token: str) -> str:
        return SecretBox.decrypt(token).decode()


def generate_token(nbytes: int = 32) -> str:
    """Token CSPRNG urlsafe (default 256-bit)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Hash satu arah untuk penyimpanan token (verifikasi/enroll)."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_recovery_code() -> str:
    """Kode pemulihan 128-bit dalam format grup 4x4."""
    raw = secrets.token_bytes(16)
    hexed = base64.b32encode(raw).decode().rstrip("=")
    return "-".join(hexed[i : i + 4] for i in range(0, 16, 4)).lower()


def hmac_code(value: str) -> str:
    """HMAC pepper server untuk kode pemulihan sekali pakai."""
    from django.conf import settings

    pepper = getattr(settings, "MT_SECRET_BOX_KEY", "") or settings.SECRET_KEY
    return hmac.new(pepper.encode(), value.encode(), hashlib.sha256).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
