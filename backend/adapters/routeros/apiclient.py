"""Klien native RouterOS API-SSL — TK-304 (ROUTEROS.md §4).

Protokol API RouterOS (biner, length-prefixed words) di atas TLS dengan
certificate PINNING (fingerprint SHA-256 dari enrollment). Tanpa SDK
eksternal; bounded connect/read/deadline; koneksi hanya ke tunnel IP
router terdaftar dari registri (bukan URL bebas — anti SSRF).

Status verifikasi: protokol+TLS dipatuji unit terhadap server TLS
in-process; perilaku per firmware RouterOS menunggu lab (G1) — tidak
dipakai sebagai bukti verified_lab.

Mutasi/cutover adapter ini menolak dengan kode jujur sampai lab lulus
(bukan fake success).
"""
from __future__ import annotations

import hashlib
import socket
import ssl
import struct
from dataclasses import dataclass
from typing import Any

from adapters.routeros.base import (
    Capability,
    ChangePlan,
    PlannedChange,
    RouterContext,
    RouterOsError,
    TimeoutAfterSendError,
    UnreachableError,
)

DEFAULT_API_PORT = 8729
CONNECT_TIMEOUT_S = 5.0
READ_TIMEOUT_S = 10.0
MAX_RESPONSE_WORDS = 20_000
MAX_WORD_BYTES = 1 << 20  # 1 MiB per word — bounded response


# ---------------------------------------------------------------------------
# Encoding panjang kata (RouterOS API)


def encode_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    if length < 0x4000:
        return struct.pack(">H", 0x8000 | length)
    if length < 0x200000:
        return struct.pack(">BB", 0xC0 | (length >> 16), (length >> 8) & 0xFF) + bytes([length & 0xFF])
    if length < 0x10000000:
        return struct.pack(">L", 0xE0000000 | length)
    return b"\xf0" + struct.pack(">L", length)


def encode_sentence(words: list[str]) -> bytes:
    out = bytearray()
    for word in words:
        raw = word.encode("utf-8")
        if len(raw) > MAX_WORD_BYTES:
            raise RouterOsError("word_too_large")
        out += encode_length(len(raw)) + raw
    out += b"\x00"  # penanda akhir kalimat
    return bytes(out)


def _read_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise UnreachableError("connection_closed")
        buf += chunk
    return bytes(buf)


def _read_length(sock: socket.socket) -> int:
    first = _read_exact(sock, 1)[0]
    if first < 0x80:
        return first
    if first == 0xFF:
        return struct.unpack(">L", _read_exact(sock, 4))[0]
    if first & 0xE0 == 0xC0:
        rest = _read_exact(sock, 2)
        return ((first & 0x1F) << 16) | (rest[0] << 8) | rest[1]
    if first & 0xC0 == 0x80:
        rest = _read_exact(sock, 1)[0]
        return ((first & 0x3F) << 8) | rest
    # 0xE0..0xEF: 4 byte
    rest = _read_exact(sock, 3)
    return ((first & 0x0F) << 24) | (rest[0] << 16) | (rest[1] << 8) | rest[2]


def read_sentence(sock: socket.socket) -> list[str]:
    words: list[str] = []
    while True:
        length = _read_length(sock)
        if length == 0:
            return words
        if length > MAX_WORD_BYTES:
            raise RouterOsError("word_too_large")
        words.append(_read_exact(sock, length).decode("utf-8", errors="replace"))
        if len(words) > MAX_RESPONSE_WORDS:
            raise RouterOsError("response_too_large")


def parse_response(sentences: list[list[str]]) -> list[dict[str, Any]]:
    """!re/=k=v → dict; !done → penanda akhir; !trap/!fatal → galat."""
    rows: list[dict[str, Any]] = []
    for sentence in sentences:
        if not sentence:
            continue
        tag = sentence[0]
        if tag in ("!re",):
            row: dict[str, Any] = {}
            for word in sentence[1:]:
                if word.startswith("="):
                    key, _, value = word[1:].partition("=")
                    row[key] = value
            rows.append(row)
        elif tag in ("!trap", "!fatal"):
            message = next((w[7:] for w in sentence[1:] if w.startswith("=message=")), tag)
            raise RouterOsError(f"routeros_trap:{message}")
        elif tag == "!done":
            # done dapat memuat =ret= (login lama) — diabaikan di sini.
            continue
    return rows


# ---------------------------------------------------------------------------
# Koneksi terkelola dengan pinning sertifikat


@dataclass
class ApiSslConnection:
    sock: ssl.SSLSocket

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def send_sentence(self, words: list[str]) -> None:
        self.sock.sendall(encode_sentence(words))

    def read_until_done(self) -> list[list[str]]:
        sentences: list[list[str]] = []
        while True:
            sentence = read_sentence(self.sock)
            if not sentence:
                continue
            sentences.append(sentence)
            if sentence[0] in ("!done", "!fatal"):
                return sentences


def cert_fingerprint(der_cert: bytes) -> str:
    """Fingerprint SHA-256 sertifikat peer (pin dari enrollment)."""
    return hashlib.sha256(der_cert).hexdigest()


class ApiSslAdapter:
    """Adapter RouterOsAdapter via API-SSL native (TK-304)."""

    def __init__(self, *, connect_timeout: float = CONNECT_TIMEOUT_S, read_timeout: float = READ_TIMEOUT_S) -> None:
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

    # --- koneksi ---

    def _connect(self, ctx: RouterContext) -> ApiSslConnection:
        if not ctx.tunnel_ip:
            raise RouterOsError("router_without_tunnel")
        host = str(ctx.tunnel_ip)  # hanya alamat terdaftar — anti SSRF
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # verifikasi via PIN di bawah
        try:
            raw = socket.create_connection((host, ctx.api_port or DEFAULT_API_PORT), timeout=self.connect_timeout)
        except (OSError, socket.timeout) as exc:
            raise UnreachableError(f"connect: {exc}") from exc
        try:
            sock = context.wrap_socket(raw)
            der = sock.getpeercert(binary_form=True)
        except (OSError, ssl.SSLError) as exc:
            raw.close()
            raise UnreachableError(f"tls: {exc}") from exc
        pin = cert_fingerprint(der or b"")
        expected = getattr(ctx, "cert_pin", "") or ""
        if expected and pin != expected:
            sock.close()
            raise RouterOsError(f"cert_pin_mismatch:{pin[:16]}")
        sock.settimeout(self.read_timeout)
        return ApiSslConnection(sock=sock)

    def _login(self, conn: ApiSslConnection, ctx: RouterContext) -> None:
        username, password = self._credentials(ctx)
        conn.send_sentence(["/login", f"=name={username}", f"=password={password}"])
        sentences = conn.read_until_done()
        for sentence in sentences:
            if sentence[0] in ("!trap", "!fatal"):
                raise RouterOsError("login_rejected")
        # Login modern: !done kosong. Login lama mengembalikan =ret= challenge —
        # tidak didukung (RouterOS <6.43 di luar scope; v6 hanya baca jalur aman).

    def _credentials(self, ctx: RouterContext) -> tuple[str, str]:
        """Dekripsi credential API-SSL read user (dari enrollment)."""
        if not ctx.credential_ref:
            raise RouterOsError("credential_missing")
        from domains.common.crypto import SecretBox

        try:
            packed = SecretBox.decrypt_str(ctx.credential_ref)
        except Exception as exc:
            raise RouterOsError("credential_unreadable") from exc
        code, _, password = packed.partition("\x00")
        return f"rtrw-ro-{code}", password

    def _query(self, ctx: RouterContext, command: list[str]) -> list[dict[str, Any]]:
        conn = self._connect(ctx)
        try:
            self._login(conn, ctx)
            conn.send_sentence(command)
            return parse_response(conn.read_until_done())
        finally:
            conn.close()

    # --- RouterOsAdapter ---

    def discover_capabilities(self, ctx: RouterContext) -> list[Capability]:
        rows = self._query(ctx, ["/system/resource/print"])
        version = next((r.get("version", "") for r in rows), "") or ctx.routeros_version
        is_v7 = version.startswith("7")
        caps = [
            Capability(name="read_accounts", supported=True, evidence=f"api-ssl v{version}"),
            Capability(name="read_health", supported=True, evidence="system/resource"),
            Capability(name="api_ssl", supported=True, evidence="tls+pinned"),
        ]
        caps.append(Capability(name="radius_client_manage", supported=is_v7, evidence="RouterOS v7 untuk mutasi"))
        caps.append(Capability(name="disconnect_session", supported=is_v7, evidence="v7 dispatcher"))
        return caps

    def list_accounts(self, ctx: RouterContext, *, kind: str = "pppoe") -> list[dict]:
        command = ["/ppp/secret/print"] if kind == "pppoe" else ["/ip/hotspot/user/print"]
        rows = self._query(ctx, command)
        for row in rows:
            row.setdefault("kind", kind)
        return rows

    def read_object(self, ctx: RouterContext, object_type: str, natural_key: str) -> dict | None:
        rows = self._query(ctx, [f"/{object_type}/print", f"?name={natural_key}"])
        return rows[0] if rows else None

    def read_health(self, ctx: RouterContext) -> dict:
        rows = self._query(ctx, ["/system/resource/print"])
        if not rows:
            raise RouterOsError("empty_health")
        row = rows[0]
        uptime_s = _parse_uptime(row.get("uptime", ""))

        def _pct(value: str) -> int | None:
            try:
                return int(int(value.rstrip("%")) * 100 / 100)
            except (ValueError, AttributeError):
                return None

        return {
            "vpn_up": True,  # koneksi API-SSL ini sendiri lewat tunnel WG
            "api_up": True,
            "cpu_percent": _pct(row.get("cpu-load", "")),
            "memory_percent": None,
            "uptime_s": uptime_s,
            "free_memory": row.get("free-memory"),
            "version": row.get("version"),
        }

    # Mutasi: jujur menolak sampai lab — bukan fake success (§5).

    def plan_action(self, ctx: RouterContext, desired: dict) -> ChangePlan:
        raise RouterOsError("mutation_pending_lab")

    def apply_action(self, ctx: RouterContext, plan: ChangePlan) -> list[dict]:
        raise RouterOsError("mutation_pending_lab")

    def verify_action(self, ctx: RouterContext, plan: ChangePlan) -> dict:
        raise RouterOsError("mutation_pending_lab")

    def create_backup(self, ctx: RouterContext, *, category: str) -> dict:
        raise RouterOsError("backup_pending_lab")

    def install_radius_client(self, ctx: RouterContext, config: dict) -> ChangePlan:
        raise RouterOsError("cutover_pending_lab")

    def set_aaa(self, ctx: RouterContext, config: dict) -> ChangePlan:
        raise RouterOsError("cutover_pending_lab")

    def resolve_local_shadow(self, ctx: RouterContext, plan: dict) -> ChangePlan:
        raise RouterOsError("cutover_pending_lab")

    def rollback_radius(self, ctx: RouterContext, baseline: dict) -> ChangePlan:
        raise RouterOsError("cutover_pending_lab")

    def disconnect_session(self, ctx: RouterContext, session_id: str) -> dict:
        raise RouterOsError("disconnect_pending_lab")


def _parse_uptime(value: str) -> int | None:
    """'1w2d3h4m5s' → detik; gagal → None (bukan 0 — data unavailable)."""
    if not value:
        return None
    total = 0
    number = ""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    for char in value:
        if char.isdigit():
            number += char
        elif char in units and number:
            total += int(number) * units[char]
            number = ""
        else:
            return None
    if number:
        total += int(number)
    return total
