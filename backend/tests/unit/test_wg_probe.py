"""Unit parser probe handshake WG — murni tanpa DB (parser adalah logika inti)."""
from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest

from domains.network.services import parse_handshake_output
from microtix.wg import validate_public_key

pytestmark = pytest.mark.unit


class TestParseHandshakeOutput:
    def test_valid_rows_with_epoch(self):
        text = "iB7vO5G6r3Xq9Wk2mZpA1cD4eF6gH8iJ0kL2mN4oP5Q=\t1780000000\n"
        out = parse_handshake_output(text)
        assert list(out) == ["iB7vO5G6r3Xq9Wk2mZpA1cD4eF6gH8iJ0kL2mN4oP5Q="]
        assert out["iB7vO5G6r3Xq9Wk2mZpA1cD4eF6gH8iJ0kL2mN4oP5Q="] == datetime(
            2026, 5, 28, 20, 26, 40, tzinfo=timezone.utc
        )

    def test_epoch_zero_means_never(self):
        out = parse_handshake_output("AAAA\t0\n")
        assert out == {"AAAA": None}

    def test_blank_and_unknown_lines_ignored(self):
        text = "\nnoise-line\nAAAA\t100\nBBBB\tgarbage\nCCCC\t-5\n"
        out = parse_handshake_output(text)
        assert out == {"AAAA": datetime.fromtimestamp(100, tz=timezone.utc), "CCCC": None}

    def test_negative_epoch_means_never(self):
        out = parse_handshake_output("AAAA\t-1\n")
        assert out == {"AAAA": None}

    def test_empty_text(self):
        assert parse_handshake_output("") == {}
        assert parse_handshake_output("\n\n") == {}

    def test_multi_peer_order_preserved(self):
        text = "B\t300\nA\t200\nC\t0\n"
        out = parse_handshake_output(text)
        assert list(out) == ["B", "A", "C"]
        assert out["A"] == datetime.fromtimestamp(200, tz=timezone.utc)

    def test_absurd_epoch_overflow_ignored_not_fatal(self):
        text = "KEY\t99999999999999999999\nOK\t100\n"
        out = parse_handshake_output(text)
        assert out == {"OK": datetime.fromtimestamp(100, tz=timezone.utc)}


class TestValidatePublicKey:
    """Validasi env MT_WG_SERVER_PUBKEY (helper murni; settings memetakan
    ValueError → ImproperlyConfigured saat boot)."""

    def test_valid_x25519_32byte(self):
        key = base64.b64encode(b"\x07" * 32).decode()
        assert validate_public_key(f"  {key} \n") == key  # strip spasi/baris

    def test_empty_returns_empty(self):
        assert validate_public_key("") == ""
        assert validate_public_key("   ") == ""

    def test_rejects_non_base64(self):
        with pytest.raises(ValueError):
            validate_public_key("bukan-base64!")

    def test_rejects_wrong_length(self):
        with pytest.raises(ValueError):
            validate_public_key(base64.b64encode(b"\x01" * 16).decode())

    def test_rejects_padding_ignored(self):
        # 32-byte yang diencode TANPA pad '=' → panjang 43, decode gagal/beda.
        with pytest.raises(ValueError):
            validate_public_key(base64.b64encode(b"\x01" * 32).decode().rstrip("="))
