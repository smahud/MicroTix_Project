"""Penulis proyeksi AccessAccount → radius.* (RADIUS.md §3/§5/§6).

Aturan:
- Ditulis HANYA di sini, dalam transaksi database yang sama dengan
  perubahan AccessAccount (sinyal post_save/post_delete → proyeksi ulang).
- Cleartext-Password di radcheck adalah kebutuhan CHAP/MS-CHAPv2 (§6.1);
  risiko dikendalikan: role daemon hanya EXECUTE facade, koneksi loopback.
- Kecepatan diproyeksikan hanya bila package_name cocok pola RouterOS rate
  (mis. "20M/10M") — tidak mengarang angka (anti fake-success §5).
- suspend/disabled/expired → Auth-Type := Reject (§7).
"""
from __future__ import annotations

import re
import secrets
import string

from django.db import connection

from domains.common.crypto import SecretBox

_ALPHABET = string.ascii_letters + string.digits
# Pola rate RouterOS: "20M", "20M/10M", "30M/10M/40M/20M" (rx/tx/burst).
_RATE_RE = re.compile(r"^(\d+[KM]\d?)(/(\d+[KM]\d?)){0,3}$", re.IGNORECASE)

ATTR_PASSWORD = "Cleartext-Password"
ATTR_REJECT = "Auth-Type"
ATTR_SIMUSE = "Simultaneous-Use"
ATTR_EXPIRATION = "Expiration"
ATTR_RATE = "Mikrotik-Rate-Limit"
ATTR_INTERIM = "Acct-Interim-Interval"
ATTR_SESSION_TIMEOUT = "Session-Timeout"


def generate_nas_secret(length: int = 32) -> str:
    """Secret NAS per-router CSPRNG (§6.4) — 32 karakter."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _rate_from_package(package_name: str | None) -> str | None:
    if not package_name:
        return None
    candidate = package_name.strip()
    return candidate if _RATE_RE.match(candidate) else None


def _seconds_until(valid_until) -> int | None:
    """Session-Timeout tidak boleh melewati valid_until (§5 Expiry)."""
    if valid_until is None:
        return None
    from django.utils import timezone

    remaining = int((valid_until - timezone.now()).total_seconds())
    return remaining if remaining > 0 else None


def project_account(account) -> None:
    """Proyeksikan satu AccessAccount ke radcheck/radreply (idempoten penuh)."""
    tenant_id = str(account.tenant_id)
    username = account.username
    rate = _rate_from_package(getattr(account.service, "package_name", None))
    session_timeout = _seconds_until(account.valid_until)

    checks: list[tuple[str, str, str]] = []
    replies: list[tuple[str, str, str]] = []

    if account.state == "active":
        if account.secret_ref:
            # Dekripsi sekali untuk proyeksi; plaintext TIDAK pernah di-log.
            try:
                password = SecretBox.decrypt(account.secret_ref).decode()
            except Exception:
                # secret_ref rusak/tidak terbaca → jangan proyeksikan password
                # palsu; akun tetap tanpa password (auth CHAP gagal jujur).
                password = None
            if password is not None:
                checks.append((ATTR_PASSWORD, ":=", password))
        checks.append((ATTR_SIMUSE, ":=", str(account.simultaneous_use or 1)))
        if account.valid_until is not None:
            checks.append((ATTR_EXPIRATION, ":=", account.valid_until.strftime("%d %b %Y")))
        if rate:
            replies.append((ATTR_RATE, "=", rate))
        replies.append((ATTR_INTERIM, "=", "300"))
        if session_timeout is not None:
            replies.append((ATTR_SESSION_TIMEOUT, "=", str(min(session_timeout, 86400))))
    else:
        # suspended/disabled/expired → tolak di level kontrol (§7).
        checks.append((ATTR_REJECT, ":=", "Reject"))

    with connection.cursor() as cur:
        # Hapus baris lama akun ini (kedua tabel) lalu tulis ulang — idempoten.
        cur.execute("DELETE FROM radius.radcheck WHERE tenant_id = %s AND account_id = %s", [tenant_id, str(account.id)])
        cur.execute("DELETE FROM radius.radreply WHERE tenant_id = %s AND account_id = %s", [tenant_id, str(account.id)])
        for attribute, op, value in checks:
            cur.execute(
                "INSERT INTO radius.radcheck (tenant_id, account_id, username, attribute, op, value) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [tenant_id, str(account.id), username, attribute, op, value],
            )
        for attribute, op, value in replies:
            cur.execute(
                "INSERT INTO radius.radreply (tenant_id, account_id, username, attribute, op, value) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [tenant_id, str(account.id), username, attribute, op, value],
            )


def deproject_account(account) -> None:
    """Hapus proyeksi akun (akun dihapus)."""
    with connection.cursor() as cur:
        cur.execute("DELETE FROM radius.radcheck WHERE tenant_id = %s AND account_id = %s", [str(account.tenant_id), str(account.id)])
        cur.execute("DELETE FROM radius.radreply WHERE tenant_id = %s AND account_id = %s", [str(account.tenant_id), str(account.id)])


def project_nas(router, secret: str | None = None) -> str:
    """Daftarkan/perbarui NAS untuk router; bump desired_revision.

    Secret baru (rotasi) hanya diterapkan reconciler setelah probe membuktikan
    secret diterima (§2) — desired vs applied revision.
    """
    nasname = str(router.tunnel_ip) if router.tunnel_ip else None
    if not nasname:
        raise ValueError("Router belum memiliki tunnel_ip — enrollment belum selesai")
    with connection.cursor() as cur:
        cur.execute("SELECT id, secret FROM radius.nas WHERE tenant_id = %s AND router_id = %s", [str(router.tenant_id), str(router.id)])
        row = cur.fetchone()
        if row is None:
            secret = secret or generate_nas_secret()
            cur.execute(
                "INSERT INTO radius.nas (tenant_id, router_id, nasname, shortname, secret, desired_revision, applied_revision) "
                "VALUES (%s, %s, %s, %s, %s, 1, 0)",
                [str(router.tenant_id), str(router.id), nasname, router.router_code[:32], secret],
            )
        else:
            cur.execute(
                "UPDATE radius.nas SET nasname = %s, shortname = %s, "
                "secret = COALESCE(%s, secret), desired_revision = desired_revision + 1 "
                "WHERE tenant_id = %s AND router_id = %s",
                [nasname, router.router_code[:32], secret, str(router.tenant_id), str(router.id)],
            )
        cur.execute("SELECT secret FROM radius.nas WHERE tenant_id = %s AND router_id = %s", [str(router.tenant_id), str(router.id)])
        return cur.fetchone()[0]


def deproject_nas(router) -> None:
    with connection.cursor() as cur:
        cur.execute("DELETE FROM radius.nas WHERE tenant_id = %s AND router_id = %s", [str(router.tenant_id), str(router.id)])


def nas_state(router):
    """(nasname, secret, desired_revision, applied_revision) | None."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT nasname, secret, desired_revision, applied_revision FROM radius.nas "
            "WHERE tenant_id = %s AND router_id = %s",
            [str(router.tenant_id), str(router.id)],
        )
        row = cur.fetchone()
    return row if row else None
