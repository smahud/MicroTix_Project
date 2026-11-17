"""Resolver atribut RADIUS — RADIUS.md §5 (RAD-04).

Fungsi murni (dapat diuji unit tanpa DB): menentukan atribut check/reply
efektif dari satu AccessAccount. Precedence: override router > paket >
tenant; tepat satu nilai untuk atribut single-value.

Kecepatan: rx = upload dari pelanggan, tx = download ke pelanggan (bit/s).
Mikrotik-Rate-Limit format "rx/tx" (RouterOS menerima "up/down" tanpa burst).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from domains.access.models import AccessAccount


@dataclass(frozen=True)
class ResolvedAttributes:
    """Hasil resolver: kontrol internal vs reply NAS dipisah (RAD-04 §5)."""

    check: dict[str, str] = field(default_factory=dict)
    reply: dict[str, str] = field(default_factory=dict)
    reject: bool = False
    reject_reason_code: str = ""


def _rate_limit_string(account: AccessAccount) -> str | None:
    rx = account.rate_limit_rx_kbps
    tx = account.rate_limit_tx_kbps
    if not rx and not tx:
        return None
    # rx (upload pelanggan) / tx (download pelanggan) dalam bit/s.
    return f"{(rx or 0) * 1000}/{(tx or 0) * 1000}"


def _today() -> object:
    from django.utils import timezone as dj_timezone

    return dj_timezone.localdate()


def resolve_attributes(account: AccessAccount, *, router_id: str | None = None) -> ResolvedAttributes:
    """Atribut efektif untuk satu akun pada konteks NAS/router tertentu.

    Eligibility (state/credential/validitas/kind/MAC/allowed routers) dievaluasi
    sebagai kontrol internal — bukan reply universal. Akun tanpa kredensial
    siap TIDAK menghasilkan Accept (password_unknown tidak diproyeksikan).
    """
    today = _today()
    reject_code = ""
    if account.state == AccessAccount.State.SUSPENDED:
        reject_code = "policy_suspended"
    elif account.state == AccessAccount.State.DISABLED:
        reject_code = "policy_disabled"
    elif account.state == AccessAccount.State.EXPIRED:
        reject_code = "policy_expired"
    elif account.credential_state != AccessAccount.CredentialState.READY:
        reject_code = "credential_not_ready"
    elif account.valid_from and today < account.valid_from:
        reject_code = "not_yet_valid"
    elif account.valid_until and today >= account.valid_until:
        reject_code = "expired_valid_until"

    allowed = account.allowed_router_ids or None
    if router_id is not None and allowed and str(router_id) not in [str(a) for a in allowed]:
        reject_code = reject_code or "router_not_allowed"

    if reject_code:
        # Auth-Type Reject sebagai kontrol internal; tanpa Cleartext-Password
        # agar kredensial tidak pernah bocor pada akun tertolak.
        return ResolvedAttributes(
            check={"Auth-Type": "Reject"},
            reject=True,
            reject_reason_code=reject_code,
        )

    check: dict[str, str] = {}
    if account.simultaneous_use and account.simultaneous_use != 1:
        check["Simultaneous-Use"] = str(account.simultaneous_use)

    reply: dict[str, str] = {}
    rate = _rate_limit_string(account)
    if rate:
        reply["Mikrotik-Rate-Limit"] = rate
    # Pool: override router > static_ip > pool; nilai invalid ditolak di
    # validator input (bukan fallback diam-diam di resolver).
    static_ip = None
    if router_id and account.static_ip_by_router:
        static_ip = account.static_ip_by_router.get(str(router_id)) or account.static_ip_by_router.get(router_id)
    if not static_ip and account.static_ip:
        static_ip = str(account.static_ip)
    if static_ip:
        reply["Framed-IP-Address"] = static_ip
    elif account.framed_pool:
        reply["Framed-Pool"] = account.framed_pool
    if account.valid_until:
        # Expiration eksklusif pada midnight timezone bisnis (WIB default).
        from datetime import datetime, time

        expiry = datetime.combine(account.valid_until, time.min)
        reply["Expiration"] = expiry.strftime("%d %b %Y %H:%M:%S")

    return ResolvedAttributes(check=check, reply=reply)


def project_rows(account: AccessAccount, *, router_id: str | None = None) -> ResolvedAttributes:
    """Alias resolve_attributes — dipakai projection writer."""
    return resolve_attributes(account, router_id=router_id)
