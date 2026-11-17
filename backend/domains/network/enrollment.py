"""Enrollment router — ROUTEROS.md §2 (TK-301/TK-302).

Alur: create draft (reserve /32 + token hashed TTL) → issue (token
ditampilkan SEKALI) → bootstrap script bernamespace idempoten (private key
WG dibuat router; platform menyuntik password API CSPRNG lewat kanal
rahasia sah) → probe/complete (konsumsi token, verifikasi identitas +
sumber tunnel, buat Router read_only + NAS desired revision + audit dalam
SATU transaksi; replay nonce sama = idempoten).

Jaminan:
- Token tidak pernah masuk log/audit (redacted) dan tidak dikirim via URL.
- Draft enrollment berakhir EXPIRED otomatis (TTL) — /32 dikembalikan.
- Complete dari identitas berbeda dengan token sama → 409 conflict.
- Enrollment tidak mengubah default route/bridge/DNS/DHCP/akun existing.
"""
from __future__ import annotations

import ipaddress
import secrets
import string

from django.db import transaction
from django.utils import timezone as dj_timezone

from domains.audit.models import record as audit_record
from domains.common.crypto import generate_token, hash_token
from domains.common.tenant_context import tenant_scope
from domains.network.models import (
    ENROLL_DRAFT_TTL_S,
    ENROLL_TOKEN_TTL_S,
    WG_FIRST_CLIENT_IP,
    WG_NETWORK,
    WG_SERVER_IP,
    Router,
    RouterEnrollment,
)

_ACTIVE_ENROLL_STATES = [
    RouterEnrollment.State.DRAFT,
    RouterEnrollment.State.ENROLLMENT_ISSUED,
    RouterEnrollment.State.BOOTSTRAP_PENDING,
    RouterEnrollment.State.TUNNEL_SEEN,
    RouterEnrollment.State.API_VERIFIED,
]


class EnrollmentError(Exception):
    def __init__(self, code: str, message: str = "", status: int = 400) -> None:
        self.code = code
        self.message = message or code
        self.status = status
        super().__init__(self.message)


def _wg_public_key() -> str:
    """Pubkey host WG dari env (dibangkitkan installer; private di host)."""
    from django.conf import settings

    return getattr(settings, "MT_WG_SERVER_PUBKEY", "")


def generate_api_password() -> str:
    """Password akun baca API-SSL — CSPRNG 24 karakter platform (§2.5)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(24))


def allocate_tunnel_ip() -> str:
    """Reserve /32 berikutnya dari WG_NETWORK yang benar-benar bebas.

    Cek Router.tunnel_ip + enrollment aktif LINTAS TENANT (UNIQUE global).
    Jalur baca memakai GUC layanan platform (kebijakan platform_service_read,
    fail-closed bila kosong) — hanya dipakai kode server, bukan sesi tenant.
    Bentrok berarti jaringan host harus diperiksa — bukan dipaksa cocok.
    """
    from django.db import connection, transaction

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.platform_service', '1', true)")
            network = ipaddress.ip_network(WG_NETWORK)
            used: set[str] = set(
                r[0] for r in cur.execute(
                    "SELECT tunnel_ip FROM network_router WHERE tunnel_ip IS NOT NULL"
                ).fetchall()
            )
            used |= set(
                r[0] for r in cur.execute(
                    "SELECT tunnel_ip FROM network_router_enrollment WHERE state IN "
                    "('draft','enrollment_issued','bootstrap_pending','tunnel_seen','api_verified')"
                ).fetchall()
            )
    start = int(ipaddress.ip_address(WG_FIRST_CLIENT_IP))
    for candidate in range(start, int(network.broadcast_address) + 1):
        ip = str(ipaddress.ip_address(candidate))
        if ip not in used:
            return ip
    raise EnrollmentError(
        "tunnel_pool_exhausted", "Kapasitas alamat tunnel habis — hubungi operator platform", status=507
    )


def create_enrollment(
    *,
    tenant_id,
    actor,
    display_name: str,
    router_code: str,
    location: str = "",
    model: str = "",
) -> tuple[RouterEnrollment, str]:
    """Draft + issue dalam satu langkah; token dikembalikan SEKALI (plaintext)."""
    if not display_name or len(display_name) > 120:
        raise EnrollmentError("invalid_display_name", "Nama tampilan wajib 1-120 karakter")
    if not router_code or len(router_code) > 48:
        raise EnrollmentError("invalid_router_code", "Kode router wajib 1-48 karakter")
    with tenant_scope(tenant_id):
        with transaction.atomic():
            active = RouterEnrollment.objects.filter(
                tenant_id=tenant_id, router_code=router_code, state__in=_ACTIVE_ENROLL_STATES
            ).first()
            if active is not None:
                raise EnrollmentError("router_code_active", "Kode router masih memiliki enrollment aktif", status=409)
            if Router.objects.filter(tenant_id=tenant_id, router_code=router_code, released_at=None).exists():
                raise EnrollmentError("router_code_taken", "Kode router sudah dipakai router aktif", status=409)
            token = generate_token(32)  # 256-bit
            now = dj_timezone.now()
            enrollment = RouterEnrollment.objects.create(
                tenant_id=tenant_id,
                created_by=actor,
                display_name=display_name,
                router_code=router_code,
                location=location or "",
                model=model or "",
                tunnel_ip=allocate_tunnel_ip(),
                state=RouterEnrollment.State.ENROLLMENT_ISSUED,
                token_hash=hash_token(token),
                token_expires_at=now + dj_timezone.timedelta(seconds=ENROLL_TOKEN_TTL_S),
                expires_at=now + dj_timezone.timedelta(seconds=ENROLL_DRAFT_TTL_S),
            )
            audit_record(
                tenant_id=tenant_id,
                action_code="network.enrollment.created",
                actor_display=getattr(actor, "full_name", "") or getattr(actor, "email", ""),
                actor_id=getattr(actor, "id", None),
                target_type="router_enrollment",
                target_id=str(enrollment.id),
                target_display=f"{display_name} ({router_code})",
                payload={"tunnel_ip": enrollment.tunnel_ip, "ttl_s": ENROLL_TOKEN_TTL_S},
            )
            return enrollment, token


def expire_stale_enrollments() -> int:
    """Tandai draft kedaluwarsa + token basi (dipanggil worker/scheduler)."""
    now = dj_timezone.now()
    stale = RouterEnrollment.objects.filter(
        state__in=[
            RouterEnrollment.State.DRAFT,
            RouterEnrollment.State.ENROLLMENT_ISSUED,
            RouterEnrollment.State.BOOTSTRAP_PENDING,
        ],
        expires_at__lt=now,
    )
    count = 0
    for e in stale:
        e.state = RouterEnrollment.State.EXPIRED
        e.updated_at = now
        e.save(update_fields=["state", "updated_at"])
        count += 1
    return count


def mark_bootstrap_downloaded(enrollment: RouterEnrollment) -> None:
    """Script bootstrap diunduh → bootstrap_pending (tetap satu jalur sah)."""
    if enrollment.state == RouterEnrollment.State.ENROLLMENT_ISSUED:
        enrollment.state = RouterEnrollment.State.BOOTSTRAP_PENDING
        enrollment.updated_at = dj_timezone.now()
        enrollment.save(update_fields=["state", "updated_at"])


def generate_bootstrap_script(
    enrollment: RouterEnrollment,
    *,
    token: str | None = None,
    api_password: str | None = None,
) -> str:
    """Skrip RouterOS idempoten bernamespace rtrw- (ROUTEROS.md §2 langkah 3–6).

    - Hanya objek milik enrollment: interface WG peer, grup+akun baca API-SSL,
      aturan input sempit dari /32 server.
    - Private key WG dibangkitkan router; platform menerima pubkey lewat
      panggilan probe (fetch melalui tunnel).
    - Password akun baca API-SSL: dibangkitkan platform (CSPRNG) dan disuntik
      lewat kanal rahasia sah (UI + HTTPS) — ROUTEROS.md §2.5; generator
      router tidak dipakai karena belum terbukti aman per build.
    - Token hanya di dalam skrip (kanal rahasia UI) — tidak di URL/log.
    - TIDAK menyentuh default route/bridge/DNS/DHCP/akun pelanggan.
    """
    if not _wg_public_key():
        raise EnrollmentError(
            "wg_host_not_configured",
            "Kunci publik WireGuard host belum dikonfigurasi (MT_WG_SERVER_PUBKEY) — jalankan konfigurasi host terlebih dahulu",
            status=503,
        )
    from django.conf import settings

    platform_base = (getattr(settings, "MT_PUBLIC_BASE_URL", "") or "https://platform.invalid").rstrip("/")
    wg_endpoint = getattr(settings, "MT_WG_ENDPOINT", "platform.example:51820")
    wg_host, _, wg_port = wg_endpoint.partition(":")
    code = enrollment.router_code
    tunnel_ip = enrollment.tunnel_ip
    script_token = token or ""
    script_password = api_password or ""
    peer_name = f"rtrw-wg-{code}"
    group_name = "rtrw-read"
    user_name = f"rtrw-ro-{code}"
    wg_pub = _wg_public_key()
    # Baris body JSON dibangun di luar f-string (kutip/brace RouterOS rapat).
    body_line = (
        ':local body ("{\\"token\\":\\"' + script_token + '\\",\\"nonce\\":\\"' + code
        + '-enroll\\",\\"router_identity\\":\\"[sysid]\\",\\"routeros_version\\":\\"[ver]\\",'
        + '\\"architecture\\":\\"[arch]\\",\\"wireguard_pubkey\\":\\"[wgpub]\\"}")'
    )
    return f"""# MicroTix enrollment bootstrap — {code}
# Skrip ini SENSITIF selama token berlaku. Jalankan di router target.
# Idempoten: menjalankan ulang tidak menggandakan objek (namespace rtrw-).
# Router menambahkan: peer WG ke platform, grup+akun baca API-SSL,
# aturan input sempit dari /32 server platform. Tidak mengubah konfigurasi
# pelanggan/default route/bridge/DNS/DHCP yang sudah ada.

# 1) Grup baca minimal + akun API-SSL baca (password CSPRNG platform,
#    disuntik lewat kanal rahasia; tidak pernah dikirim balik ke platform).
:if ([:len [/user group find name="{group_name}"]] = 0) do={{ \\
  /user group add name="{group_name}" policy=read,api \\
    comment="MicroTix read-only (enrollment)" }}
:if ([:len [/user find name="{user_name}"]] = 0) do={{ \\
  /user add name="{user_name}" group="{group_name}" password="{script_password}" \\
    comment="MicroTix API-SSL read" }}

# 2) Interface WireGuard milik enrollment (buat hanya bila belum ada).
:if ([:len [/interface wireguard find name="{peer_name}"]] = 0) do={{ \\
  /interface wireguard add name="{peer_name}" listen-port=13231 comment="MicroTix management" }}

# 3) Peer platform: endpoint publik host; allowed-address HANYA /32 server
#    (bukan 0.0.0.0/0) — ROUTEROS.md §2 langkah 3.
:if ([:len [/interface wireguard peers find interface="{peer_name}" public-key="{wg_pub}"]] = 0) do={{ \\
  /interface wireguard peers add interface="{peer_name}" \\
    public-key="{wg_pub}" \\
    endpoint-address="{wg_host}" \\
    endpoint-port={wg_port or 51820} \\
    allowed-address="{WG_SERVER_IP}/32" \\
    comment="MicroTix platform" }}

# 4) Alamat tunnel /32 milik router ini (idempoten).
:if ([:len [/ip address find address="{tunnel_ip}/32 interface={peer_name}"]] = 0) do={{ \\
  /ip address add address="{tunnel_ip}/32" interface="{peer_name}" comment="MicroTix mgmt" }}

# 5) Aturan input sempit: hanya /32 server pada interface manajemen,
#    ditempatkan paling atas (place-before=0) agar tidak berada di bawah
#    drop umum; operator memverifikasi urutan pada lab (gate T01/T19).
:if ([:len [/ip firewall filter find comment="rtrw-allow-mgmt-api"]] = 0) do={{ \\
  /ip firewall filter add chain=input action=accept \\
    src-address="{WG_SERVER_IP}/32" in-interface="{peer_name}" \\
    protocol=tcp dst-port=8729 comment="rtrw-allow-mgmt-api" \\
    place-before=0 }}

# 6) Kunci publik WG router + identitas + konsumsi token → platform
#    MELALUI TUNNEL (token di body, bukan URL; tidak dicatat log).
:delay 3s
:local wgpub [/interface wireguard get [find name="{peer_name}"] public-key]
{body_line}
:local body ($body | replace "[sysid]" [/system identity get name])
:local body ($body | replace "[ver]" [/system resource get version])
:local body ($body | replace "[arch]" [/system resource get architecture-name])
:local body ($body | replace "[wgpub]" $wgpub)
/tool fetch mode=https url="{platform_base}/api/v1/router-enrollments/{enrollment.id}/probe" \\
  http-method=post http-data=$body output=none
:log info "MicroTix enrollment selesai — periksa status di platform."
"""


def complete_enrollment(
    *,
    enrollment_id,
    token: str,
    nonce: str,
    router_identity: str,
    routeros_version: str,
    architecture: str,
    wireguard_pubkey: str,
    api_cert_fingerprint: str = "",
    source_ip: str | None = None,
) -> tuple[RouterEnrollment, bool]:
    """Konsumsi token + buat Router read_only + NAS desired — atomik.

    Return (enrollment, created). Replay dengan nonce sama → logical
    enrollment (idempoten, created=False). Identitas berbeda → 409.
    Sumber: di production, permintaan HARUS datang dari tunnel_ip reserved
    (bukti jalur WG); dev/test dapat melewati lewat MT_ENROLL_VERIFY_SOURCE=0.
    """
    from django.conf import settings

    now = dj_timezone.now()
    verify_source = bool(getattr(settings, "MT_ENROLL_VERIFY_SOURCE", False))
    # Fase 1 — baca enrollment lewat jalur probe (endpoint token-gated;
    # pemanggil adalah router, bukan sesi tenant). GUC fail-closed.
    from django.db import connection, transaction

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.enrollment_probe', '1', true)")
        enrollment = (
            RouterEnrollment.objects.select_for_update()
            .filter(
                id=enrollment_id,
                state__in=[
                    RouterEnrollment.State.ENROLLMENT_ISSUED,
                    RouterEnrollment.State.BOOTSTRAP_PENDING,
                    RouterEnrollment.State.TUNNEL_SEEN,
                    RouterEnrollment.State.API_VERIFIED,
                ],
            )
            .first()
        )
        if enrollment is None:
            done = RouterEnrollment.objects.select_for_update().filter(
                id=enrollment_id, state=RouterEnrollment.State.CONSUMED
            ).first()
            if done is not None:
                # Replay pasca-konsumsi: nonce/router-key sama → logical
                # enrollment; identitas BERBEDA → 409 (ROUTEROS.md §2.7).
                if done.router_identity == router_identity:
                    return done, False
                raise EnrollmentError(
                    "identity_conflict", "Token telah dikonsumsi identitas lain", status=409
                )
            raise EnrollmentError("enrollment_not_found", "Enrollment tidak ditemukan atau tidak aktif", status=404)
        tenant_id = enrollment.tenant_id

    # Fase 2 — seluruh validasi + mutasi dalam tenant_scope(tenant):
    # kebijakan RLS tenant yang berlaku; audit + NAS pada transaksi sama.
    with tenant_scope(tenant_id):
        with transaction.atomic():
            enrollment = (
                RouterEnrollment.objects.select_for_update().filter(id=enrollment_id).first()
            )
            assert enrollment is not None
            if enrollment.token_expires_at and enrollment.token_expires_at < now:
                enrollment.state = RouterEnrollment.State.EXPIRED
                enrollment.save(update_fields=["state", "updated_at"])
                raise EnrollmentError("token_expired", "Token enrollment kedaluwarsa — minta token baru", status=410)
            if not secrets.compare_digest(enrollment.token_hash, hash_token(token)):
                raise EnrollmentError("token_invalid", "Token enrollment tidak valid", status=401)
            if not nonce or len(nonce) > 64:
                raise EnrollmentError("nonce_required", "Nonce wajib 1-64 karakter")
            # Replay: nonce sama + identitas sama → logical enrollment.
            if enrollment.complete_nonce == nonce and enrollment.router_identity == router_identity:
                return enrollment, False
            if enrollment.complete_nonce and enrollment.complete_nonce != nonce:
                raise EnrollmentError("nonce_conflict", "Token telah dikonsumsi identitas lain", status=409)
            if enrollment.router_identity and enrollment.router_identity != router_identity:
                raise EnrollmentError("identity_conflict", "Identitas router berbeda dengan yang terdaftar", status=409)
            source_verified = bool(source_ip) and str(source_ip) == str(enrollment.tunnel_ip)
            if verify_source and not source_verified:
                raise EnrollmentError(
                    "source_not_verified",
                    "Permintaan harus berasal dari alamat tunnel yang direservasi",
                    status=403,
                )
            if enrollment.router is not None:
                raise EnrollmentError("already_completed", "Enrollment telah membuat router", status=409)

            # Buat router read_only + identitas terverifikasi + NAS desired.
            router = Router.objects.create(
                tenant_id=enrollment.tenant_id,
                display_name=enrollment.display_name,
                router_code=enrollment.router_code,
                location=enrollment.location,
                model=enrollment.model or "",
                identity=router_identity,
                routeros_version=routeros_version,
                mode=Router.Mode.READ_ONLY,
                tunnel_ip=enrollment.tunnel_ip,
                wireguard_pubkey=wireguard_pubkey,
                api_cert_fingerprint=api_cert_fingerprint,
                # Password API baca (dari bootstrap) pindah ke credential_ref.
                credential_ref=enrollment.api_password_ref or "",
                capability={"verified_at": now.isoformat(), "source_verified": source_verified},
            )
            enrollment.router = router
            enrollment.router_identity = router_identity
            enrollment.routeros_version = routeros_version
            enrollment.architecture = architecture
            enrollment.wireguard_pubkey = wireguard_pubkey
            enrollment.api_cert_fingerprint = api_cert_fingerprint
            enrollment.source_verified = source_verified
            enrollment.complete_nonce = nonce
            enrollment.token_used_at = now
            enrollment.state = RouterEnrollment.State.CONSUMED
            enrollment.updated_at = now
            enrollment.save()

            # NAS desired revision — proyeksi radius.nas + secret CSPRNG unik.
            from domains.access import services as access_services

            access_services.ensure_nas(
                tenant_id=enrollment.tenant_id,
                router=router,
                shortname=f"{enrollment.router_code}-{router_identity[:16]}",
            )
            audit_record(
                tenant_id=enrollment.tenant_id,
                action_code="network.enrollment.completed",
                actor_display=f"router:{router_identity}",
                target_type="router",
                target_id=str(router.id),
                target_display=f"{router.display_name} ({router.router_code})",
                payload={
                    "tunnel_ip": enrollment.tunnel_ip,
                    "routeros_version": routeros_version,
                    "source_verified": source_verified,
                    "mode": router.mode,
                },
            )
            return enrollment, True
