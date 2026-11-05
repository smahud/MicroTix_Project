"""Unit protokol API-SSL RouterOS (TK-304): encoding, parsing, pinning TLS."""
from __future__ import annotations

import socket
import ssl
import threading

import pytest

from adapters.routeros.apiclient import (
    ApiSslAdapter,
    cert_fingerprint,
    encode_length,
    encode_sentence,
    parse_response,
    read_sentence,
    _parse_uptime,
)
from adapters.routeros.base import RouterContext, RouterOsError, UnreachableError

pytestmark = pytest.mark.unit


class TestEncoding:
    def test_short_length(self):
        assert encode_length(0) == b"\x00"
        assert encode_length(5) == b"\x05"
        assert encode_length(0x7F) == b"\x7f"

    def test_two_byte_length(self):
        assert encode_length(0x80) == b"\x80\x80"
        assert encode_length(0x3FFF) == b"\xbf\xff"

    def test_three_byte_length(self):
        assert encode_length(0x4000) == b"\xc0\x40\x00"

    def test_sentence_roundtrip(self):
        payload = encode_sentence(["/login", "=name=user", "=password=secret"])
        assert payload.endswith(b"\x00")

    def test_word_too_large_rejected(self):
        with pytest.raises(RouterOsError):
            encode_sentence(["x" * (1 << 21)])


class TestParsing:
    def test_parse_re_rows(self):
        sentences = [
            ["!re", "=name=cust-1", "=profile=10M", "=disabled=false"],
            ["!re", "=name=cust-2", "=profile=20M"],
            ["!done"],
        ]
        rows = parse_response(sentences)
        assert rows == [
            {"name": "cust-1", "profile": "10M", "disabled": "false"},
            {"name": "cust-2", "profile": "20M"},
        ]

    def test_trap_raises(self):
        with pytest.raises(RouterOsError) as exc:
            parse_response([["!trap", "=message=invalid user or password"]])
        assert "invalid user" in str(exc.value)

    def test_parse_uptime(self):
        assert _parse_uptime("1w2d3h4m5s") == 7 * 86400 + 2 * 86400 + 3 * 3600 + 4 * 60 + 5
        assert _parse_uptime("45s") == 45
        assert _parse_uptime("") is None
        assert _parse_uptime("weird") is None


class TestSocketRoundtrip:
    def test_read_sentence_over_socketpair(self):
        payload = encode_sentence(["!re", "=name=a", "=value=b"]) + encode_sentence(["!done"])
        a, b = socket.socketpair()
        try:
            a.sendall(payload)
            assert read_sentence(b) == ["!re", "=name=a", "=value=b"]
            assert read_sentence(b) == ["!done"]
        finally:
            a.close()
            b.close()


def _make_self_signed_cert(tmp_path):
    """Buat sertifikat self-signed untuk server TLS uji (via openssl CLI)."""
    import subprocess

    crt = tmp_path / "test.crt"
    key = tmp_path / "test.key"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key), "-out", str(crt),
         "-days", "2", "-nodes", "-subj", "/CN=rtrw-test"],
        check=True, capture_output=True,
    )
    return crt, key


class _FakeRouterOsServer(threading.Thread):
    """Server TLS yang membalas login + /system/resource/print."""

    def __init__(self, crt, key, port_holder):
        super().__init__(daemon=True)
        self.crt, self.key = crt, key
        self.port_holder = port_holder
        self.stop_flag = False

    def run(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.crt), str(self.key))
        raw = socket.socket()
        raw.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw.bind(("127.0.0.1", 0))
        raw.listen(1)
        self.port_holder.append(raw.getsockname()[1])
        conn, _ = raw.accept()
        tls = context.wrap_socket(conn, server_side=True)
        try:
            while not self.stop_flag:
                sentence = read_sentence(tls)
                if not sentence:
                    continue
                if sentence[0] == "/login":
                    tls.sendall(encode_sentence(["!done"]))
                elif sentence[0] == "/system/resource/print":
                    tls.sendall(
                        encode_sentence(["!re", "=version=7.15.3", "=cpu-load=13", "=uptime=1w2d"])
                        + encode_sentence(["!done"])
                    )
                elif sentence[0] == "/ppp/secret/print":
                    tls.sendall(
                        encode_sentence(["!re", "=name=cust-1", "=service=pppoe", "=profile=10M"])
                        + encode_sentence(["!done"])
                    )
                else:
                    tls.sendall(encode_sentence(["!done"]))
        except OSError:
            pass
        finally:
            tls.close()
            raw.close()


@pytest.fixture
def fake_router(tmp_path):
    crt, key = _make_self_signed_cert(tmp_path)
    port_holder: list[int] = []
    server = _FakeRouterOsServer(crt, key, port_holder)
    server.start()
    for _ in range(100):
        if port_holder:
            break
        import time

        time.sleep(0.05)
    der = ssl.PEM_cert_to_DER_cert(crt.read_text())
    yield {"port": port_holder[0], "pin": cert_fingerprint(der)}
    server.stop_flag = True
    # Bangunkan server agar keluar.
    try:
        s = socket.create_connection(("127.0.0.1", port_holder[0]), timeout=1)
        s.close()
    except OSError:
        pass


def _ctx(fake, pin: str = "", credential: str = "") -> RouterContext:
    return RouterContext(
        router_id="00000000-0000-0000-0000-00000000000f",
        tenant_id="00000000-0000-0000-0000-0000000000aa",
        tunnel_ip="127.0.0.1",
        api_port=fake["port"],
        mode="read_only",
        credential_ref=credential,
        cert_pin=pin,
    )


class TestApiSslAdapter:
    def test_login_and_read_health(self, fake_router):
        adapter = ApiSslAdapter()
        ctx = _ctx(fake_router, pin=fake_router["pin"], credential=_packed_credential())
        health = adapter.read_health(ctx)
        assert health["api_up"] is True
        assert health["cpu_percent"] == 13
        assert health["uptime_s"] == 7 * 86400 + 2 * 86400

    def test_list_accounts(self, fake_router):
        adapter = ApiSslAdapter()
        ctx = _ctx(fake_router, pin=fake_router["pin"], credential=_packed_credential())
        rows = adapter.list_accounts(ctx, kind="pppoe")
        assert rows and rows[0]["name"] == "cust-1"

    def test_certificate_pin_mismatch_rejected(self, fake_router):
        adapter = ApiSslAdapter()
        ctx = _ctx(fake_router, pin="deadbeef" * 8, credential=_packed_credential())
        with pytest.raises(RouterOsError) as exc:
            adapter.read_health(ctx)
        assert "cert_pin_mismatch" in str(exc.value)

    def test_unreachable(self):
        adapter = ApiSslAdapter(connect_timeout=0.3)
        ctx = RouterContext(router_id="r", tenant_id="t", tunnel_ip="127.0.0.1", api_port=1)
        with pytest.raises(UnreachableError):
            adapter.read_health(ctx)

    def test_mutation_pending_lab_honest(self, fake_router):
        adapter = ApiSslAdapter()
        ctx = _ctx(fake_router)
        with pytest.raises(RouterOsError) as exc:
            adapter.plan_action(ctx, {})
        assert "pending_lab" in str(exc.value)


def _packed_credential() -> str:
    from domains.common.crypto import SecretBox

    return SecretBox.encrypt("rt-001\x00api-password-123")
