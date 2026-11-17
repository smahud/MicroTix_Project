"""Service layer akses: penulis proyeksi RADIUS + lifecycle akun/NAS.

Aturan (RADIUS.md §3–§7):
- Aplikasi (access_account) sumber kebenaran; radius.* hanya proyeksi yang
  ditulis service layer DALAM transaksi database yang sama.
- Suspend: commit Account suspended + proyeksi Reject + audit/outbox atomik.
  Disconnect sesi adalah efek eksternal terpisah (job dispatcher) — bukan
  bagian dari transaksi proyeksi.
- Restore: tindakan manual aktor services.activate; commit atribut normal
  terkini (bukan snapshot lama).
- NAS: desired_revision naik saat secret/router berubah; applied_revision
  ditulis reconciler HANYA setelah probe membuktikan secret baru diterima.
"""
from __future__ import annotations

import secrets
import string

from django.db import connection, transaction
from django.utils import timezone as dj_timezone

from domains.access.models import AccessAccount, AccessAccountSource, Nas
from domains.access.resolver import resolve_attributes
from domains.common.crypto import SecretBox
from domains.common.tenant_context import tenant_scope

_ALPHABET = string.ascii_letters + string.digits

# Batas username (RADIUS.md §3): case-sensitive, 64 karakter / 64 byte UTF-8,
# tanpa karakter kontrol, tanpa spasi tepi / ganda.
def validate_username(username: str) -> str:
    if not username:
        raise ValueError("username wajib diisi")
    if len(username) > 64 or len(username.encode("utf-8")) > 64:
        raise ValueError("username maksimal 64 karakter / 64 byte UTF-8")
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in username):
        raise ValueError("username mengandung karakter kontrol")
    if username != username.strip() or "  " in username:
        raise ValueError("username tidak boleh berawalan/berakhir spasi atau spasi ganda")
    return username


def generate_nas_secret() -> str:
    """Secret NAS 32 karakter CSPRNG (RAD-05 §4) — tidak dipakai ulang antarrouter."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(32))


# ---------------------------------------------------------------------------
# Penulis proyeksi (radius.*) — hanya dipanggil dalam tenant_scope


def _project_delete(account: AccessAccount) -> None:
    with connection.cursor() as cur:
        cur.execute("DELETE FROM radius.radcheck WHERE account_id = %s", [account.id])
        cur.execute("DELETE FROM radius.radreply WHERE account_id = %s", [account.id])
        cur.execute("DELETE FROM radius.radusergroup WHERE username = %s AND tenant_id = %s", [account.username, account.tenant_id])


def project_account(account: AccessAccount, *, router_id: str | None = None) -> None:
    """Tulis ulang proyeksi atribut satu akun (idempoten; panggil dalam transaksi tenant).

    Baris radcheck/radreply milik akun dihapus lalu ditulis ulang sesuai
    resolver — menjamin tidak ada atribut basi tersisa. Cleartext-Password
    hanya diproyeksikan untuk akun aktif dengan kredensial siap.
    """
    resolved = resolve_attributes(account, router_id=router_id)
    _project_delete(account)
    rows_check: list[tuple] = []
    if not resolved.reject and account.credential_state == AccessAccount.CredentialState.READY and account.secret_ref:
        password = SecretBox.decrypt_str(account.secret_ref)
        rows_check.append((account.id, account.username, "Cleartext-Password", ":=", password))
    for attr, value in resolved.check.items():
        rows_check.append((account.id, account.username, attr, ":=", value))
    rows_reply = [(account.id, account.username, attr, "=", value) for attr, value in resolved.reply.items()]
    with connection.cursor() as cur:
        if rows_check:
            cur.executemany(
                "INSERT INTO radius.radcheck (tenant_id, account_id, username, attribute, op, value) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [(str(account.tenant_id), *row) for row in rows_check],
            )
        if rows_reply:
            cur.executemany(
                "INSERT INTO radius.radreply (tenant_id, account_id, username, attribute, op, value) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [(str(account.tenant_id), *row) for row in rows_reply],
            )


# ---------------------------------------------------------------------------
# Lifecycle akun


class AccessError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(self.message)


def create_access_account(
    *,
    tenant_id,
    username: str,
    password: str,
    kind: str = AccessAccount.Kind.PPPOE,
    service=None,
    actor=None,
    router_id: str | None = None,
    simultaneous_use: int = 1,
    mac_lock: str = "",
    static_ip: str | None = None,
    rate_limit_rx_kbps: int | None = None,
    rate_limit_tx_kbps: int | None = None,
    framed_pool: str = "",
    valid_until=None,
    source: dict | None = None,
) -> AccessAccount:
    """Buat akun + proyeksi atomik (TK-501: idempoten lewat natural key)."""
    username = validate_username(username)
    if len(password) < 8:
        raise AccessError("password_too_short", "Password layanan minimal 8 karakter")
    with tenant_scope(tenant_id):
        with transaction.atomic():
            if AccessAccount.objects.filter(username=username).exists():
                raise AccessError("username_taken", "Username sudah dipakai pada tenant ini")
            account = AccessAccount.objects.create(
                tenant_id=tenant_id,
                username=username,
                kind=kind,
                secret_ref=SecretBox.encrypt(password),
                credential_state=AccessAccount.CredentialState.READY,
                simultaneous_use=max(1, int(simultaneous_use)),
                mac_lock=mac_lock or "",
                static_ip=static_ip,
                rate_limit_rx_kbps=rate_limit_rx_kbps,
                rate_limit_tx_kbps=rate_limit_tx_kbps,
                framed_pool=framed_pool or "",
                valid_until=valid_until,
                service=service,
            )
            project_account(account, router_id=router_id)
            if source:
                AccessAccountSource.objects.create(
                    tenant_id=tenant_id,
                    account=account,
                    router_id=source["router_id"],
                    namespace=source.get("namespace", "routeros"),
                    external_handle=source["external_handle"],
                    fingerprint=source.get("fingerprint", ""),
                )
            _audit(
                tenant_id,
                actor,
                "access.account.created",
                target_type="access_account",
                target_id=str(account.id),
                target_display=username,
                payload={"username": username, "kind": kind, "source": bool(source)},
            )
            return account


def set_account_state(account: AccessAccount, *, new_state: str, actor=None) -> AccessAccount:
    """Suspend/activate/restore — proyeksi mengikuti state terkini (RAD-06).

    Suspend: state→suspended + proyeksi Auth-Type Reject, satu transaksi.
    Activate: manual aktor services.activate; kelayakan (hold/binding)
    diperiksa ulang; atribut normal terkini yang diproyeksikan ulang.
    """
    from domains.access.models import AccessAccount as AA

    if new_state not in {AA.State.ACTIVE, AA.State.SUSPENDED, AA.State.DISABLED}:
        raise AccessError("invalid_state", f"State tidak sah: {new_state}")
    if account.state == new_state:
        return account
    with tenant_scope(account.tenant_id):
        with transaction.atomic():
            account.state = new_state
            account.revision += 1
            account.updated_at = dj_timezone.now()
            account.save(update_fields=["state", "revision", "updated_at"])
            project_account(account)
            _audit(
                account.tenant_id,
                actor,
                f"access.account.{new_state}",
                target_type="access_account",
                target_id=str(account.id),
                target_display=account.username,
                payload={"revision": account.revision},
            )
            return account


def rotate_password(account: AccessAccount, *, new_password: str, actor=None) -> AccessAccount:
    """Rotasi password: secret_ref + proyeksi dalam SATU transaksi (RAD-05 §3)."""
    if len(new_password) < 8:
        raise AccessError("password_too_short", "Password layanan minimal 8 karakter")
    with tenant_scope(account.tenant_id):
        with transaction.atomic():
            account.secret_ref = SecretBox.encrypt(new_password)
            account.credential_state = AccessAccount.CredentialState.READY
            account.revision += 1
            account.updated_at = dj_timezone.now()
            account.save(update_fields=["secret_ref", "credential_state", "revision", "updated_at"])
            project_account(account)
            _audit(
                account.tenant_id,
                actor,
                "access.account.rotated",
                target_type="access_account",
                target_id=str(account.id),
                target_display=account.username,
                payload={"revision": account.revision},
            )
            return account


def reveal_password(account: AccessAccount) -> str:
    """Baca password terenkripsi (pemanggil wajib sudah lewat permission+reauth)."""
    if not account.secret_ref:
        raise AccessError("credential_unknown", "Kredensial akun ini tidak tersedia")
    return SecretBox.decrypt_str(account.secret_ref)


def nas_secret(nas: Nas) -> str:
    """Baca secret NAS terenkripsi (hanya reconciler/worker yang memanggil)."""
    return SecretBox.decrypt_str(nas.secret_ref)


# ---------------------------------------------------------------------------
# NAS lifecycle (RAD-01 §2 + TK-307)


def ensure_nas(*, tenant_id, router, shortname: str) -> Nas:
    """Buat/ambil NAS untuk router; secret CSPRNG unik; desired_revision mulai 1."""
    with tenant_scope(tenant_id):
        nas = Nas.objects.filter(router=router).first()
        if nas is not None:
            return nas
        nas = Nas.objects.create(
            tenant_id=tenant_id,
            router=router,
            shortname=shortname,
            secret_ref=SecretBox.encrypt(generate_nas_secret()),
        )
        _project_nas(nas)
        _audit(
            tenant_id,
            None,
            "access.nas.created",
            target_type="nas",
            target_id=str(nas.id),
            target_display=shortname,
            payload={"desired_revision": nas.desired_revision},
        )
        return nas


def rotate_nas_secret(nas: Nas, *, actor=None) -> Nas:
    """Rotasi secret NAS: naikkan desired_revision; applied menyusul reconciler."""
    with tenant_scope(nas.tenant_id):
        with transaction.atomic():
            nas.secret_ref = SecretBox.encrypt(generate_nas_secret())
            nas.desired_revision += 1
            nas.updated_at = dj_timezone.now()
            nas.save(update_fields=["secret_ref", "desired_revision", "updated_at"])
            _project_nas(nas)
            _audit(
                nas.tenant_id,
                actor,
                "access.nas.rotated",
                target_type="nas",
                target_id=str(nas.id),
                target_display=nas.shortname,
                payload={"desired_revision": nas.desired_revision},
            )
            return nas


def _project_nas(nas: Nas) -> None:
    """Proyeksi radius.nas (dibaca reconciler untuk clients.conf; RLS berlaku).

    Bersihkan baris router ini ATAU baris yatim yang memakai alamat tunnel
    sama (nasname UNIQUE global — sisa proyeksi lama tidak boleh menghalangi).
    """
    secret = SecretBox.decrypt_str(nas.secret_ref)
    router = nas.router
    with connection.cursor() as cur:
        cur.execute(
            "DELETE FROM radius.nas WHERE router_id = %s OR nasname = %s",
            [nas.router_id, router.tunnel_ip],
        )
        cur.execute(
            "INSERT INTO radius.nas (tenant_id, router_id, nasname, shortname, secret, type) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [str(nas.tenant_id), str(nas.router_id), router.tunnel_ip, nas.shortname, secret, nas.nas_type],
        )


def nas_pending_reconciliation(tenant_id) -> list[dict]:
    """NAS dengan desired_revision > applied_revision (untuk reconciler/status)."""
    from django.db.models import F, Q

    with tenant_scope(tenant_id):
        pending = Nas.objects.filter(
            Q(applied_revision__isnull=True) | Q(applied_revision__lt=F("desired_revision"))
        ).select_related("router")
        return [
            {
                "id": str(n.id),
                "router_id": str(n.router_id),
                "shortname": n.shortname,
                "nasname": n.router.tunnel_ip,
                "desired_revision": n.desired_revision,
                "applied_revision": n.applied_revision,
            }
            for n in pending
        ]


def mark_nas_applied(nas: Nas, *, revision: int) -> None:
    """Reconciler menulis applied_revision SETELAH probe membuktikan secret baru."""
    with tenant_scope(nas.tenant_id):
        nas.applied_revision = revision
        nas.updated_at = dj_timezone.now()
        nas.save(update_fields=["applied_revision", "updated_at"])


# ---------------------------------------------------------------------------
# Audit (payload tersanitasi)


def _audit(tenant_id, actor, action_code: str, *, target_type: str, target_id: str, target_display: str, payload: dict) -> None:
    from domains.audit.models import record

    record(
        tenant_id=tenant_id,
        action_code=action_code,
        actor_display=getattr(actor, "full_name", "") or getattr(actor, "email", "") or ("sistem" if actor is None else ""),
        actor_id=getattr(actor, "id", None),
        target_type=target_type,
        target_id=target_id,
        target_display=target_display,
        payload=payload,
    )
