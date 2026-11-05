"""TOTP RFC 6238 — vektor uji resmi Appendix B (SHA1, 8 digit dikecualikan;
kita uji 6 digit dengan rumus sama) + perilaku jendela/anti-replay."""
from __future__ import annotations

import base64

from domains.identity import totp

# Seed RFC 6238 Appendix B: "12345678901234567890" (SHA1)
RFC_SEED = base64.b32encode(b"12345678901234567890").decode().rstrip("=")


def test_rfc6238_vectors_sha1():
    # Tabel RFC 6238 Appendix B (SHA1, 8 digit); 6 digit = nilai % 10^6.
    assert totp.totp_at(RFC_SEED, 59) == "287082"        # 94287082
    assert totp.totp_at(RFC_SEED, 1111111109) == "081804"  # 07081804
    assert totp.totp_at(RFC_SEED, 1111111111) == "050471"  # 14050471
    assert totp.totp_at(RFC_SEED, 1234567890) == "005924"  # 89005924
    assert totp.totp_at(RFC_SEED, 2000000000) == "279037"  # 69279037


def test_verify_accepts_current_step():
    now = 1111111109
    code = totp.totp_at(RFC_SEED, now)
    assert totp.verify(RFC_SEED, code, at_s=now) is not None


def test_verify_rejects_wrong_code():
    assert totp.verify(RFC_SEED, "000000", at_s=59) is None
    assert totp.verify(RFC_SEED, "12345", at_s=59) is None  # panjang salah
    assert totp.verify(RFC_SEED, "abcdef", at_s=59) is None


def test_verify_window_plus_minus_one_step():
    code = totp.totp_at(RFC_SEED, 59)  # step 1
    # Waktu step 2 (89s): kode step 1 masih dalam jendela -1
    assert totp.verify(RFC_SEED, code, at_s=89) is not None
    # Waktu step 0 (29s): juga dalam jendela
    assert totp.verify(RFC_SEED, code, at_s=29) is not None
    # Waktu step 3 (149s): di luar jendela
    assert totp.verify(RFC_SEED, code, at_s=149) is None


def test_verify_anti_replay_same_step():
    code = totp.totp_at(RFC_SEED, 1111111109)
    step = totp.verify(RFC_SEED, code, at_s=1111111109)
    assert step is not None
    # Kode yang sama pada langkah ≤ langkah terpakai ditolak (replay).
    assert totp.verify(RFC_SEED, code, at_s=1111111109, last_used_step=step) is None


def test_generated_seed_roundtrip():
    seed = totp.generate_seed()
    code = totp.totp_at(seed, 1700000000)
    assert totp.verify(seed, code, at_s=1700000000) is not None
    assert len(seed) == 32  # 160-bit base32
