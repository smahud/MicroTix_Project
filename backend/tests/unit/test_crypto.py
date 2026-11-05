"""Kripto rahasia: AEAD round-trip, token hash, kode pemulihan (TK-102)."""
from __future__ import annotations

import pytest

from domains.common import crypto


def test_secretbox_roundtrip():
    plaintext = "JBSWY3DPEHPK3PXP"
    token = crypto.SecretBox.encrypt(plaintext)
    assert token != plaintext
    assert crypto.SecretBox.decrypt_str(token) == plaintext


def test_secretbox_tamper_fails():
    token = crypto.SecretBox.encrypt("rahasia")
    tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
    with pytest.raises(Exception):
        crypto.SecretBox.decrypt(tampered)


def test_token_hash_stable_and_not_reversible():
    token = crypto.generate_token(32)
    hashed = crypto.hash_token(token)
    assert hashed == crypto.hash_token(token)
    assert token not in hashed
    assert len(hashed) == 64


def test_recovery_code_format_and_hmac():
    code = crypto.generate_recovery_code()
    parts = code.split("-")
    assert len(parts) == 4 and all(len(p) == 4 for p in parts)
    digest = crypto.hmac_code(code)
    assert len(digest) == 64 and crypto.constant_time_eq(digest, crypto.hmac_code(code))


def test_recovery_codes_unique():
    codes = {crypto.generate_recovery_code() for _ in range(50)}
    assert len(codes) == 50
