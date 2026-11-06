"""Layanan enrollment router (M3) — ROUTEROS.md §2.

Alur: draft → token CSPRNG (hash-only, TTL) → bootstrap skrip aman →
bridge enroll-complete (konsumsi token atomik) → verifikasi API-SSL
(simulator di beta) → router read-only aktif + peer WireGuard desired.

Jaminan:
- Token 256-bit tidak pernah disimpan plaintext; replay nonce sama =
  hasil logis sama, identitas berbeda → ditolak (§2.7).
- /32 tunnel unik global dialokasikan dari carve host; bentrok → gagal,
  bukan mengubah jaringan (§2.1).
- Skrip bootstrap TIDAK reset/reboot; hanya objek milik platform (rtrw);
- API-SSL tidak dibuka publik — rule input sempit dari /32 server.

Host WireGuard (§9.13 instalasi.sh): adopsi keypair installer via env
MT_WG_SERVER_PUBKEY — kunci privat tetap di tangan host (root), proses
aplikasi hanya memegang kunci publik; tanpa env: fallback deterministik
dev/test yang jujur (bukan klaim X25519).
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
import secrets
import shutil
import subprocess
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from domains.common.crypto import SecretBox
from domains.common.envelope import ApiError
from domains.common.tenant_context import tenant_scope

from domains.network.models import (
    DiscoveryObject,
    DiscoverySnapshot,
    Router,
    RouterEnrollment,
    WireGuardHost,
    WireGuardPeer,
)
from adapters.routeros.base import UnreachableError

ENROLL_TOKEN_TTL_S = 24 * 3600  # token enrollment 24 jam (§2.1)
BOOTSTRAP_TTL_S = 900           # skrip bootstrap 15 menit (enroll.token_ttl_s)

# Transport enrollment yang DIDUKUNG implementasi ini (master directive §6/§8:
# arsitektur shared-port multi-protokol; Phase 1 = WireGuard saja — protokol
# lain ditolak jujur, bukan diterima diam-diam. Dasar kompatibilitas versi:
# report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md).
SUPPORTED_ENROLLMENT_PROTOCOLS = ("wireguard",)
_WIREGUARD_MIN_ROS_MAJOR = 7  # WireGuard hadir sejak RouterOS 7.1 (sumber riset)

_STAGE_CODES = ["vpn_handshake", "api_verify", "auth_permission", "compatibility"]


def _wg_host() -> WireGuardHost:
    """Singleton host state — adopsi pubkey installer bila env tersedia.

    Env MT_WG_SERVER_PUBKEY (instalasi.sh §9.13) → public_key X25519 nyata;
    private_key_ref kosong (privat dipegang host, root:600 — aplikasi tidak
    pernah memegangnya). Tanpa env (dev/test): kunci sendiri + representasi
    deterministik jujur (key_source=generated_dev).
    """
    host = WireGuardHost.objects.first()
    if host is None:
        pub = getattr(settings, "MT_WG_SERVER_PUBKEY", "")
        if pub:
            host = WireGuardHost.objects.create(
                interface_name="wg0",
                listen_port=51820,
                subnet_cidr="100.127.0.0/16",
                public_key=pub,
                private_key_ref="",
                key_source=WireGuardHost.KeySource.INSTALLER_ENV,
                adopted_at=timezone.now(),
            )
        else:
            private = secrets.token_urlsafe(32)
            host = WireGuardHost.objects.create(
                interface_name="mtx-wg0",
                listen_port=51820,
                subnet_cidr="100.127.0.0/16",
                private_key_ref=SecretBox.encrypt(private),
                key_source=WireGuardHost.KeySource.GENERATED_DEV,
            )
            _set_host_public_key(host, private)
    return host


def _any_active_peer() -> bool:
    """Peer aktif lintas tenant — eksplisit per tenant (ARCHITECTURE §4:
    bukan broad SELECT tanpa scope; scope bersarang aman/reentrant)."""
    from domains.tenancy.models import Tenant

    for (tenant_id,) in Tenant.objects.values_list("id"):
        with tenant_scope(tenant_id):
            if WireGuardPeer.objects.exclude(state=WireGuardPeer.State.REMOVED).exists():
                return True
    return False


def _host_address(host: WireGuardHost) -> str:
    return str(next(ipaddress.ip_network(host.subnet_cidr).hosts()))


def adopt_wg_host_key(*, check_only: bool = False) -> dict:
    """Adopsi kunci publik installer (env) oleh WireGuardHost — idempoten.

    - Tanpa env: no-op jujur (fallback dev deterministik dipertahankan).
    - Sudah adopsi sama: no-op.
    - Peer aktif ada + kunci BERBEDA: DITOLAK (rotasi = operasi jaringan
      terjadwal — peers lama memegang kunci lama; jangan diam-diam putus).
    - Tanpa peer aktif: adopsi + revision bump + private_key_ref dibersihkan.
    - check_only: TANPA MUTASI SAMA SEKALI — baris host dibaca tanpa membuat
      (host belum ada → status no_host jujur, bukan adopsi diam-diam).
    """
    pub = getattr(settings, "MT_WG_SERVER_PUBKEY", "")
    if check_only:
        host = WireGuardHost.objects.first()  # read-only: tidak pernah membuat
        if host is None:
            return {
                "status": "no_host",
                "changed": False,
                "key_source": "",
                "interface": "",
                "public_key": "",
                "note": "baris WireGuardHost belum ada — jalankan adopt_wg_host (bukan --check)",
            }
    else:
        host = _wg_host()
    base = {
        "status": "ok",
        "changed": False,
        "public_key": host.public_key,
        "key_source": host.key_source,
        "interface": host.interface_name,
    }
    if not pub:
        base.update(
            status="no_env",
            note="MT_WG_SERVER_PUBKEY kosong — representasi dev deterministik dipertahankan (jujur, bukan X25519)",
        )
        return base
    if host.public_key == pub and host.key_source == WireGuardHost.KeySource.INSTALLER_ENV:
        base["note"] = "pubkey installer sudah diadopsi"
        return base
    if _any_active_peer():
        base.update(
            status="refused",
            note=(
                "kunci BERBEDA terdeteksi dengan peer aktif — rotasi ditolak "
                "(peers memegang kunci lama; jalankan rotasi terjadwal + re-enrollment)"
            ),
        )
        return base
    if check_only:
        base.update(status="mismatch", changed=True, note="pubkey env belum diadopsi (tidak ada peer aktif — aman diadopsi)")
        return base
    host.public_key = pub
    host.key_source = WireGuardHost.KeySource.INSTALLER_ENV
    host.private_key_ref = ""  # privat dipegang host (root) — bukan aplikasi
    host.interface_name = "wg0"  # nama interface installer (wg0.conf)
    host.listen_port = 51820
    host.adopted_at = timezone.now()
    host.desired_revision += 1
    host.save(update_fields=[
        "public_key", "key_source", "private_key_ref", "interface_name",
        "listen_port", "adopted_at", "desired_revision", "updated_at",
    ])
    base.update(changed=True, public_key=pub, key_source=host.key_source, interface=host.interface_name)
    base["note"] = "pubkey installer diadopsi"
    return base


def _set_host_public_key(host: WireGuardHost, private: str | None = None) -> None:
    """Publikasi kunci WG host — tanpa pustaka eksternal, versi beta memakai
    representasi deterministik dari privat (catatan honest: konversi X25519
    murni ditambahkan saat lab WireGuard nyata; skrip tetap memakai nilai ini)."""
    if not private:
        try:
            private = SecretBox.decrypt(host.private_key_ref).decode()
        except Exception:
            private = ""
    host.public_key = hashlib.sha256(("mtx-wg-pub:" + private).encode()).hexdigest()[:44]
    host.desired_revision += 1
    host.save(update_fields=["public_key", "desired_revision", "updated_at"])


def allocate_tunnel_ip() -> str:
    """Alokasi /32 bebas dari carve host — deterministik, bentrok → error jujur.

    Keterlihatan lintas tenant: keunikan /32 bersifat GLOBAL (§2.1), namun RLS
    membatasi query per tenant — kumpulkan IP terpakai dengan iterasi scope
    per tenant (pola _any_active_peer; konvensi repo). Tanpa ini, dua tenant
    dapat memilih /32 yang sama dan melanggar constraint unik global (bug
    isolasi §7 — ditemukan test RTR-DUP lintas tenant). Caller sudah membuka
    scope; scope bersarang reentrant (tenant_context).
    """
    host = _wg_host()
    network = ipaddress.ip_network(host.subnet_cidr)
    used: set[str] = set()
    from domains.tenancy.models import Tenant

    for (tenant_id,) in Tenant.objects.values_list("id"):
        with tenant_scope(tenant_id):
            used.update(Router.objects.exclude(tunnel_ip=None).values_list("tunnel_ip", flat=True))
            used.update(RouterEnrollment.objects.values_list("tunnel_ip", flat=True))
    for candidate in network.hosts():
        if str(candidate) == "100.127.0.1":
            continue  # alamat host interface
        if str(candidate) not in used:
            return str(candidate)
    raise ApiError.conflict("no_tunnel_ip", "error.conflict")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_enrollment(tenant_id: str, payload: dict, *, actor=None) -> RouterEnrollment:
    """Draft enrollment + token terbit (state enrollment_issued).

    Field baru (master directive §9): `protocol` (default wireguard — selain
    itu ditolak 422 jujur) dan `routeros_version` (deklarasi pemilik;
    WireGuard mensyaratkan v7.1+). API lama tanpa kedua field tetap sah
    (default wireguard/"7") — kompatibilitas klien existing dijaga.
    """
    display_name = str(payload.get("display_name", "") or "").strip()[:120]
    router_code = str(payload.get("router_code", "") or "").strip().upper()[:16]
    errors: dict[str, list] = {}
    if not display_name:
        errors["display_name"] = [{"code": "required", "message": "Nama tampilan wajib diisi"}]
    import re

    if not re.fullmatch(r"[A-Z0-9-]{2,16}", router_code):
        errors["router_code"] = [
            {"code": "pattern", "message": "Kode router 2–16 karakter: huruf besar, angka, tanda hubung"}
        ]
    mode = payload.get("mode") or "read_only"
    if mode not in Router.Mode.values:
        errors["mode"] = [{"code": "choice", "message": "mode harus read_only atau managed"}]
    protocol = str(payload.get("protocol") or "wireguard").strip().lower()[:16]
    if protocol not in SUPPORTED_ENROLLMENT_PROTOCOLS:
        errors["protocol"] = [
            {
                "code": "unsupported",
                "message": (
                    "Protokol belum didukung rilis ini — hanya WireGuard "
                    "(SSTP/L2TP/IPsec/OpenVPN menyusul per fase)"
                ),
            }
        ]
    routeros_version = str(payload.get("routeros_version") or "7").strip().lstrip("vV")
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", routeros_version):
        errors["routeros_version"] = [
            {"code": "invalid", "message": "Format versi RouterOS tidak valid (contoh: 7.15.3)"}
        ]
    elif protocol == "wireguard":
        parts = routeros_version.split(".")
        major = int(parts[0])
        if major < _WIREGUARD_MIN_ROS_MAJOR:
            errors["routeros_version"] = [
                {
                    "code": "wireguard_requires_v7",
                    "message": (
                        "WireGuard membutuhkan RouterOS v7.1+ — RouterOS v6 akan "
                        "didukung melalui SSTP (belum tersedia di rilis ini)"
                    ),
                }
            ]
        elif major == 7 and len(parts) > 1 and int(parts[1]) < 1:
            # WireGuard hadir tepat pada 7.1 — build 7.0 tidak memuatnya
            # (sumber: riset capability matrix report/researcher/).
            errors["routeros_version"] = [
                {
                    "code": "wireguard_requires_v7_1",
                    "message": "WireGuard hadir sejak RouterOS v7.1 — versi 7.0 belum memuat WireGuard",
                }
            ]
    if errors:
        raise ApiError.validation(errors)
    # Konvensi repo: caller provides scope (view TenantApiView / job engine).
    if Router.objects.filter(tenant_id=tenant_id, router_code=router_code, released_at=None).exists():
        raise ApiError.conflict()
    if RouterEnrollment.objects.filter(
        tenant_id=tenant_id, router_code=router_code, status__in=["draft", "awaiting_bootstrap", "bootstrapped", "verifying"]
    ).exists():
        raise ApiError.conflict()
    tunnel_ip = allocate_tunnel_ip()
    token = secrets.token_urlsafe(32)  # 256-bit
    enrollment = RouterEnrollment.objects.create(
        tenant_id=tenant_id,
        display_name=display_name,
        router_code=router_code,
        mode=mode,
        protocol=protocol,
        routeros_version=routeros_version,
        tunnel_ip=tunnel_ip,
        token_hash=_hash_token(token),
        token_ref=SecretBox.encrypt(token),  # terenkripsi; TTL bootstrap
        token_nonce=secrets.token_hex(8),
        token_expires_at=timezone.now() + timedelta(seconds=ENROLL_TOKEN_TTL_S),
        created_by=actor,
    )
    return enrollment


def enrollment_progress(enrollment: RouterEnrollment) -> dict:
    """EnrollmentProgress sesuai kontrak (staging terpisah §2.8)."""
    state_map = {
        RouterEnrollment.Status.DRAFT: "bootstrap_pending",
        RouterEnrollment.Status.AWAITING_BOOTSTRAP: "bootstrap_pending",
        RouterEnrollment.Status.BOOTSTRAPPED: "tunnel_seen",
        RouterEnrollment.Status.VERIFYING: "tunnel_seen",
        RouterEnrollment.Status.COMPLETED: "discovery_ready",
        RouterEnrollment.Status.EXPIRED: "expired",
        RouterEnrollment.Status.FAILED: "conflict",
        RouterEnrollment.Status.CANCELLED: "expired",
    }
    state = state_map.get(enrollment.status, "bootstrap_pending")
    if state == "discovery_ready" and not enrollment.api_cert_fingerprint:
        state = "api_verified"
    stages_done = {
        "bootstrap_pending": 0,
        "tunnel_seen": 1,
        "api_verified": 3,
        "discovery_ready": 4,
        "expired": 0,
        "conflict": 0,
    }[state]
    detail = [
        {
            "code": code,
            "state": "ok" if i < stages_done else ("failed" if state == "conflict" and i == 0 else "pending"),
        }
        for i, code in enumerate(_STAGE_CODES)
    ]
    # Pelabelan jujur sumber verifikasi (master directive §10): simulator tidak
    # pernah dipresentasikan sebagai konektivitas perangkat nyata.
    capability: dict = {}
    if enrollment.router_id:
        router = Router.objects.filter(id=enrollment.router_id).first()
        if router is not None and router.capability:
            capability = router.capability
    verification = {
        "source": capability.get("source"),
        "verified_lab": bool(capability.get("verified_lab", False)),
        "api_ssl": bool(capability.get("api_ssl", False)),
        "wireguard": bool(capability.get("wireguard", False)),
    }
    return {
        "enrollment_id": str(enrollment.id),
        "state": state,
        "stage_detail": detail,
        "protocol": enrollment.protocol,
        "routeros_version": enrollment.routeros_version or None,
        "verification": verification,
    }


def bootstrap_script(enrollment: RouterEnrollment) -> dict:
    """Skrip bootstrap RouterOS v7 (WireGuard) — idempoten, tanpa reset.

    Token berada di BODY callback (bukan URL/analytics §2.2). Skrip hanya
    berlaku 15 menit (enroll.token_ttl_s). Endpoint peer = hostname publik
    gateway dari konfigurasi (vpn.gateway_hostname / MT_PUBLIC_HOST /
    MT_DOMAIN) — TIDAK PERNAH IP tunnel internal. Private key WireGuard
    dibangkitkan router sendiri (§2.3) — skrip tidak pernah memuat/membaca
    kunci privat. Port listener dari state host; port API dari enrollment.
    Kejujuran beta: sintaks teruji terhadap simulator; perangkat produksi
    menunggu lab G1 (purpose_summary).
    """
    if enrollment.status not in (RouterEnrollment.Status.DRAFT, RouterEnrollment.Status.AWAITING_BOOTSTRAP):
        raise ApiError.conflict()
    if enrollment.token_expires_at < timezone.now():
        raise ApiError.conflict("expired", "error.conflict")
    if enrollment.protocol != "wireguard":  # defense-in-depth: state tersimpan
        raise ApiError.conflict("protocol_unsupported", "error.conflict")
    host = _wg_host()
    if not enrollment.token_ref:
        # Token sudah dikonsumsi atau draft dari sesi sebelumnya.
        raise ApiError.conflict("token_issued_once", "error.conflict")
    try:
        token = SecretBox.decrypt(enrollment.token_ref).decode()
    except Exception:
        raise ApiError.conflict("token_unreadable", "error.conflict") from None
    from domains.config.registry import registry

    keepalive = registry().get_int("vpn.keepalive_s")
    gateway = gateway_hostname()
    wg_addr = str(next(ipaddress.ip_network(host.subnet_cidr).hosts()))
    script = _ROUTEROS_WG_TEMPLATE
    for placeholder, value in (
        ("{GATEWAY}", gateway),
        ("{HOST_PUBKEY}", host.public_key),
        ("{WG_ADDR}", wg_addr),
        ("{TUNNEL_IP}", str(enrollment.tunnel_ip)),
        ("{WG_PORT}", str(host.listen_port)),
        ("{API_PORT}", str(enrollment.api_port)),
        ("{KEEPALIVE}", str(keepalive)),
        ("{TOKEN}", token),
    ):
        script = script.replace(placeholder, value)
    return {
        "enrollment_id": str(enrollment.id),
        "protocol": enrollment.protocol,
        "routeros_version": enrollment.routeros_version or "7",
        "script": script,
        "expires_at": (timezone.now() + timedelta(seconds=BOOTSTRAP_TTL_S)).isoformat(),
        # Tujuan endpoint diekspos eksplisit untuk preview UI (ROUTEROS.md §2.2:
        # "UI menunjukkan tujuan endpoint dan diff semua objek").
        "gateway": {
            "hostname": gateway,
            "listen_port": host.listen_port,
            "api_port": enrollment.api_port,
            "server_tunnel_ip": wg_addr,
        },
        "purpose_summary": [
            "Membuat interface WireGuard + peer ke gateway publik + alamat tunnel /32 (objek rtrw milik platform).",
            f"Endpoint gateway: {gateway}:{host.listen_port}/UDP — API manajemen hanya dari /32 server via tunnel.",
            "Rule input sempit API-SSL hanya dari /32 server (API tidak dibuka publik).",
            "Tanpa reset/reboot/perubahan route default/DNS/DHCP/NAT/bridge/akun existing.",
            "Beta: sintaks skrip diverifikasi pada simulator; perangkat fisik menunggu lab G1.",
        ],
    }


# Skrip RouterOS v7 (WireGuard) — placeholder diisi render-time dari state
# tervalidasi (gateway hostname, kunci publik host, /32, port) — bukan dari
# string bebas frontend (master directive §9). Baris "\" = lanjutan baris
# RouterOS; \" di dalam string = kutip ter-escape RouterOS.
_ROUTEROS_WG_TEMPLATE = """# MicroTix bootstrap enrollment — RouterOS v7 · WireGuard — idempoten
# Gateway: {GATEWAY}:{WG_PORT}/UDP · API manajemen: {WG_ADDR}:{API_PORT}/TCP via tunnel
# TIDAK ada reset/reboot/perubahan route default/DNS/DHCP/NAT/bridge/akun existing.
:local iface "mtx-wg"
:local srvkey "{HOST_PUBKEY}"
:local srvaddr "{WG_ADDR}"
:local myaddr "{TUNNEL_IP}/32"
:local token "{TOKEN}"
# 1) Interface WireGuard milik platform — private key dibangkitkan router
#    SENDIRI (ROUTEROS.md §2.3); kunci privat tidak pernah keluar router.
:if ([/interface/wireguard/find where name=$iface] = "") do={ \\
    /interface/wireguard/add name=$iface listen-port=13231; \\
}
# 2) Peer ke gateway PUBLIK platform — allowed-address HANYA /32 server
#    (bukan 0.0.0.0/0). Idempoten: peer lama milik platform diganti.
/interface/wireguard/peers/remove [find interface=$iface]
/interface/wireguard/peers/add interface=$iface public-key=$srvkey \\
    endpoint-address="{GATEWAY}" endpoint-port={WG_PORT} \\
    allowed-address=($srvaddr . "/32") persistent-keepalive={KEEPALIVE}s
# 3) Alamat tunnel /32 milik platform.
:if ([/ip/address/find where interface=$iface and address=$myaddr] = "") do={ \\
    /ip/address/add interface=$iface address=$myaddr; \\
}
# 4) Rule input sempit: API-SSL hanya dari /32 server pada interface manajemen.
:if ([/ip/firewall/filter/find where comment="rtrw-mgmt-api"] = "") do={ \\
    /ip/firewall/filter/add chain=input action=accept protocol=tcp dst-port={API_PORT} \\
        src-address=($srvaddr . "/32") in-interface=$iface comment="rtrw-mgmt-api" place-before=0; \\
}
# 5) Callback platform — token + kunci publik WG di BODY HTTPS (bukan URL §2.2).
#    GAP TERDOKUMENTASI (lab G1): check-certificate belum diaktifkan — RouterOS
#    tidak memverifikasi CA platform secara bawaan; validasi sertifikat + SNTP
#    menunggu bukti lab (lihat report/orchestrator sesi Phase-1). Token sekali
#    pakai + TTL 15 menit + konsumsi atomik membatasi dampak.
:local pub [/interface/wireguard/get [find name=$iface] public-key]
:local cb ("{\\"token\\":\\"" . $token . "\\",\\"wg_public_key\\":\\"" . $pub . "\\"}")
/tool/fetch url="https://{GATEWAY}/api/v1/bridge/enroll-complete" \\
    http-method=post http-data=$cb http-header-field="Content-Type: application/json"
:put "MicroTix bootstrap selesai — pantau status verifikasi di dasbor platform."
"""

_GATEWAY_DEV_FALLBACK = "microtix.invalid"  # TLD .invalid (RFC 2606) — placeholder dev/test jujur


def _validate_gateway_hostname(host: str) -> None:
    """Validasi hostname/IPv4 publik — tolak scheme, port, path, spasi, oktet >255."""
    import re

    if not 1 <= len(host) <= 253:
        raise ApiError.conflict("gateway_hostname_invalid", "error.conflict")
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        if all(0 <= int(octet) <= 255 for octet in host.split(".")):
            return  # IPv4 literal publik sah
        raise ApiError.conflict("gateway_hostname_invalid", "error.conflict")
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if not re.fullmatch(rf"{label}(?:\.{label})*", host):
        raise ApiError.conflict("gateway_hostname_invalid", "error.conflict")


def gateway_hostname() -> str:
    """Hostname publik gateway VPN untuk skrip bootstrap (master directive §6).

    Rantai sumber (semua non-rahasia; mekanisme konfigurasi yang ada):
    1. registri defaults.json `vpn.gateway_hostname`
       (override env MT_OVERRIDE_VPN__GATEWAY_HOSTNAME — nilai JSON string);
    2. env MT_PUBLIC_HOST;
    3. env MT_DOMAIN (installer — Gate A/G).
    Produksi tanpa nilai → error jujur (TIDAK ada fallback palsu);
    dev/test → placeholder .invalid yang tidak dapat diresolve.
    """
    from domains.config.registry import registry

    candidates: list[str] = []
    reg_value = registry().get("vpn.gateway_hostname")
    if isinstance(reg_value, str) and reg_value.strip():
        candidates.append(reg_value.strip())
    candidates.append(os.environ.get("MT_PUBLIC_HOST", ""))
    candidates.append(os.environ.get("MT_DOMAIN", ""))
    for value in candidates:
        host = value.strip().lower().rstrip(".")
        if host:
            _validate_gateway_hostname(host)
            return host
    if getattr(settings, "ENV", "dev") != "production":
        return _GATEWAY_DEV_FALLBACK
    raise ApiError.conflict("gateway_hostname_unconfigured", "error.conflict")


# ---------------------------------------------------------------------------
# Host WireGuard: render konfigurasi + probe handshake (ops host; §9.13)
# ---------------------------------------------------------------------------


def render_host_config(target_dir: str, *, private_key_file: str | None = None) -> dict:
    """Render wg0.conf dari state host+peers — desired state, ops mengaplikasikan.

    TIDAK menyentuh interface aktif; idempoten; berkas 0600. PrivateKey hanya
    disematkan bila ops (root) memberi --private-key-file; tanpa itu: baris
    komentar jujur (wg-quick membutuhkan PrivateKey — digabung host).
    Peer REMOVED tidak dirender; PENDING/APPLIED/DRIFT dirender (desired).
    """
    from domains.config.registry import registry

    host = _wg_host()
    keepalive = registry().get_int("vpn.keepalive_s")
    addr = _host_address(host)
    now = timezone.now().isoformat()
    embedded = False
    private_value = ""
    if private_key_file:
        with open(private_key_file, "r", encoding="utf-8") as fh:
            private_value = fh.read().strip()
        if not private_value:
            raise ApiError.validation({
                "private_key_file": [{"code": "invalid", "message": "berkas kunci privat kosong"}],
            })
        embedded = True

    lines = [
        f"# MicroTix render host WireGuard — dibuat {now}",
        f"# sumber: network_wireguard_host revision desired={host.desired_revision}",
        "# Terapkan (root): wg-quick strip wg0 + ganti berkas + wg-quick up wg0",
        "# atau: wg syncconf wg0 <(wg-quick strip wg0 | grep -v '^#')",
        "[Interface]",
        f"Address = {addr}/32",
        f"ListenPort = {host.listen_port}",
    ]
    if embedded:
        lines.append(f"PrivateKey = {private_value}")
    else:
        lines.append("# PrivateKey = DIISI OLEH OPS HOST (root) dari /etc/microtix/wireguard/server_private.key")

    peer_count = 0
    tenants_touched = 0
    from domains.tenancy.models import Tenant

    for tenant in Tenant.objects.order_by("id"):
        rendered_for_tenant = 0
        with tenant_scope(tenant.id):
            peers = (
                WireGuardPeer.objects.exclude(state=WireGuardPeer.State.REMOVED)
                .select_related("router", "enrollment")
                .order_by("allowed_ip")
            )
            for peer in peers:
                router_code = peer.router.router_code if peer.router else "-"
                lines += [
                    "",
                    f"# tenant={peer.tenant_id} router={router_code} state={peer.state} rev={peer.desired_revision}",
                    "[Peer]",
                    f"PublicKey = {peer.public_key}",
                    f"AllowedIPs = {peer.allowed_ip}/32",
                    f"PersistentKeepalive = {keepalive}",
                ]
                rendered_for_tenant += 1
        if rendered_for_tenant:
            tenants_touched += 1
        peer_count += rendered_for_tenant

    os.makedirs(target_dir, exist_ok=True)
    out_path = os.path.join(target_dir, f"{host.interface_name}.conf")
    body = "\n".join(lines) + "\n"
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.chmod(out_path, 0o600)
    return {
        "status": "ok",
        "file": out_path,
        "peers": peer_count,
        "tenants": tenants_touched,
        "host_address": f"{addr}/32",
        "listen_port": host.listen_port,
        "private_key_embedded": embedded,
        "desired_revision": host.desired_revision,
    }


def parse_handshake_output(text: str) -> dict[str, datetime | None]:
    """Parse keluaran `wg show <iface> latest-handshakes` — murni, teruji unit.

    Format: "<public-key>\t<epoch-seconds>" per baris; epoch 0 = belum pernah.
    """
    result: dict[str, datetime | None] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue  # baris tidak dikenal diabaikan (bukan error fatal)
        pubkey, epoch = parts[0], parts[1]
        try:
            seconds = int(epoch)
        except ValueError:
            continue
        if seconds <= 0:
            result[pubkey] = None
            continue
        try:
            # Epoch absurd (overflow/os) diabaikan — baris tak dikenal tidak
            # boleh menjatuhkan probe (kontrak: bukan error fatal).
            result[pubkey] = datetime.fromtimestamp(seconds, tz=dt_timezone.utc)
        except (OverflowError, OSError, ValueError):
            continue
    return result


def probe_handshakes(*, interface: str | None = None, wg_bin: str | None = None) -> dict:
    """Probe handshake interface host via `wg show <iface> latest-handshakes`.

    Jalur NYATA butuh binary `wg` + akses root ke interface host (ops/sudo).
    Tanpa itu: status BLOCKED jujur — tidak pernah dipalsukan PASS. Pembaruan
    last_handshake_at monotonik (tidak mundur); peers tak dikenal pada
    interface dilaporkan sebagai drift evidence.
    """
    host = _wg_host()
    iface = interface or host.interface_name
    binpath = wg_bin or os.environ.get("MT_WG_PROBE_BIN", "wg")
    resolved = shutil.which(binpath) if os.path.dirname(binpath) == "" else (
        binpath if os.path.exists(binpath) else None
    )
    if not resolved:
        return {
            "status": "blocked",
            "interface": iface,
            "error": f"binary wg tidak ditemukan ({binpath}) — probe membutuhkan wireguard-tools pada host (ops root)",
        }
    try:
        proc = subprocess.run(
            [resolved, "show", iface, "latest-handshakes"],
            capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {"status": "blocked", "interface": iface, "error": "wg show timeout 10s"}
    if proc.returncode != 0:
        return {
            "status": "blocked",
            "interface": iface,
            "error": f"wg show gagal (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()[:200]}",
        }
    parsed = parse_handshake_output(proc.stdout)

    updated = 0
    seen_pubkeys: set[str] = set()
    missing_on_interface: list[dict] = []
    from domains.tenancy.models import Tenant

    for tenant in Tenant.objects.order_by("id"):
        with tenant_scope(tenant.id):
            peers = WireGuardPeer.objects.exclude(state=WireGuardPeer.State.REMOVED)
            for peer in peers:
                seen_pubkeys.add(peer.public_key)
                new_hs = parsed.get(peer.public_key)
                if new_hs is None and peer.public_key not in parsed:
                    missing_on_interface.append({
                        "peer_id": str(peer.id), "tenant_id": str(peer.tenant_id),
                        "public_key": peer.public_key, "state": peer.state,
                    })
                elif new_hs is not None:
                    if peer.last_handshake_at is None or new_hs > peer.last_handshake_at:
                        peer.last_handshake_at = new_hs
                        peer.save(update_fields=["last_handshake_at"])
                        updated += 1
    unknown_on_interface = sorted(set(parsed) - seen_pubkeys)
    # Label bukti jujur: binary `wg` sistem = host nyata; binary override
    # (mis. stub tes) dilabeli stub — tidak mengklaim probe host nyata.
    default_wg = os.environ.get("MT_WG_PROBE_BIN", "wg")
    source_label = "host_wg" if resolved.endswith("/wg") or resolved == default_wg == "wg" else "stub"
    try:
        version = subprocess.run(
            [resolved, "--version"], capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except subprocess.TimeoutExpired:
        version = ""
    return {
        "status": "ok",
        "interface": iface,
        "updated": updated,
        "peers_on_interface": len(parsed),
        "unknown_on_interface": unknown_on_interface,
        "missing_on_interface": missing_on_interface,
        "evidence": {"source": source_label, "binary": resolved, "version": version},
    }


def complete_enrollment(token: str, wg_public_key: str) -> dict:
    """Bridge enroll-complete: konsumsi token atomik (§2.7).

    Token di body; hash lookup; replay nonce+key sama = hasil logis sama;
    identitas berbeda = 409. Mengembalikan status untuk callback router.
    """
    if not token or len(token) > 200 or not wg_public_key or len(wg_public_key) > 64:
        raise ApiError.validation()
    token_hash = _hash_token(token)
    # Lookup token lintas tenant via policy enroll_bridge (GUC khusus,
    # hanya service layer tepercaya — bukan pelonggaran RLS umum).
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.enroll_bridge', 'on', false)")
        enrollment = RouterEnrollment.objects.filter(token_hash=token_hash).select_related("router").first()
        cur.execute("SELECT set_config('app.enroll_bridge', 'off', false)")
    if enrollment is None:
        raise ApiError.not_found()
    if enrollment.token_expires_at < timezone.now():
        with tenant_scope(enrollment.tenant_id):
            enrollment.status = RouterEnrollment.Status.EXPIRED
            enrollment.save(update_fields=["status"])
        raise ApiError.conflict("expired", "error.conflict")
    # Replay/retransmit: token terkonsumsi dengan identitas SAMA → hasil
    # logis sama tanpa mengulang efek (§2.7); identitas berbeda → 409.
    if enrollment.status in (
        RouterEnrollment.Status.BOOTSTRAPPED,
        RouterEnrollment.Status.VERIFYING,
        RouterEnrollment.Status.COMPLETED,
    ):
        if enrollment.wg_public_key == wg_public_key:
            status = "completed" if enrollment.status == RouterEnrollment.Status.COMPLETED else "bootstrap_accepted"
            return {"status": status, "router_id": str(enrollment.router_id or ""), "replay": True}
        raise ApiError.conflict()  # identitas berbeda pada token terpakai
    if enrollment.status not in (RouterEnrollment.Status.DRAFT, RouterEnrollment.Status.AWAITING_BOOTSTRAP):
        raise ApiError.conflict()

    with tenant_scope(enrollment.tenant_id):
        from django.db import IntegrityError, transaction

        with transaction.atomic():
            enrollment.status = RouterEnrollment.Status.BOOTSTRAPPED
            enrollment.wg_public_key = wg_public_key
            enrollment.consumed_at = timezone.now()
            enrollment.token_ref = ""  # plaintext terenkripsi dibersihkan (§2.7)
            enrollment.save(update_fields=["status", "wg_public_key", "consumed_at", "token_ref"])
            # Peer desired + host provisioning via reconciler (§2.7).
            # Identitas kriptografis unik global (uq_wgpeer_pubkey_active):
            # kunci publik yang sudah menjadi peer AKTIF — termasuk milik tenant
            # lain — tidak dapat dipasangkan ulang diam-diam (isolasi §7:
            # per-router unique credentials/keys).
            try:
                WireGuardPeer.objects.update_or_create(
                    tenant_id=enrollment.tenant_id,
                    router=None,
                    allowed_ip=enrollment.tunnel_ip,
                    defaults={
                        "enrollment": enrollment,
                        "public_key": wg_public_key,
                        "desired_revision": 1,
                        "state": WireGuardPeer.State.PENDING,
                    },
                )
            except IntegrityError:
                raise ApiError.conflict("wg_public_key_registered", "error.conflict") from None
    # Verifikasi API-SSL asinkron (job) — hasil tidak diklaim di sini.
    from domains.jobs import engine

    engine.create_job(
        tenant_id=enrollment.tenant_id,
        kind="verify_api_ssl",
        payload={"enrollment_id": str(enrollment.id)},
    )
    return {"status": "bootstrap_accepted", "router_id": None, "replay": False}


def finalize_verification(enrollment: RouterEnrollment, *, source: str = "simulator") -> Router:
    """Selesaikan verifikasi → buat Router read-only + pasang peer.

    Kejujuran bukti (ROUTEROS.md §2.8; master directive §10): `source` = nama
    adapter AKTIF saat verifikasi — hasil simulator TIDAK PERNAH dipresentasikan
    sebagai konektivitas perangkat nyata.
    - simulator: tidak ada handshake/API-SSL nyata yang dilakukan →
      capability.api_ssl/wireguard = False (bukan klaim terhubung).
    - api_ssl: probe TCP+TLS NYATA ke tunnel IP dilakukan SEBELUM router dibuat;
      bukti (fingerprint sertifikat teramati) dicatat; gagal → error (job
      di-retry bounded — enrollment TIDAK diselesaikan palsu). Login API +
      pembandingan pin menunggu skrip v2 + lab G1 (perangkat belum memiliki
      akun API platform — celah terdokumentasi, bukan klaim).
    """
    from adapters.routeros.base import RouterContext

    probe: dict | None = None
    if source != "simulator":
        from adapters.routeros.factory import active_routeros_adapter

        adapter = active_routeros_adapter()
        probe = adapter.probe_connectivity(
            RouterContext(
                router_id=str(enrollment.id),
                tenant_id=str(enrollment.tenant_id),
                tunnel_ip=str(enrollment.tunnel_ip),
                api_port=enrollment.api_port,
                routeros_version=enrollment.routeros_version or "7.15",
            )
        )
        if not probe.get("ok"):
            raise UnreachableError(f"api_ssl_probe:{probe.get('error', 'unknown')}")
    api_password = secrets.token_urlsafe(24)
    if source == "simulator":
        # Pin sintetis deterministik (dev/test) — TIDAK diklaim sebagai
        # sertifikat perangkat nyata.
        fingerprint = hashlib.sha256(("api-ssl-cert:" + enrollment.token_hash[:32]).encode()).hexdigest()[:64]
        capability = {
            "source": source,
            "verified_lab": False,
            "api_ssl": False,
            "wireguard": False,
            "protocol": enrollment.protocol,
            "note": "verifikasi perangkat nyata belum dilakukan (jalur simulator; lab G1 menunggu)",
        }
    else:
        # Pin = fingerprint sertifikat TERAMATI saat probe TLS nyata — koneksi
        # berikutnya dibandingkan terhadap nilai ini (pin nyata, bukan sintetis).
        observed = str(probe.get("cert_sha256") or "")[:128]
        fingerprint = observed or hashlib.sha256(
            ("api-ssl-cert:" + enrollment.token_hash[:32]).encode()
        ).hexdigest()[:64]
        capability = {
            "source": source,
            "verified_lab": False,
            "api_ssl": True,  # probe TLS nyata sukses ke tunnel IP
            "wireguard": False,  # handshake host dibuktikan terpisah (probe ops §9.13)
            "protocol": enrollment.protocol,
            "probe": probe,
            "note": "TLS API-SSL tercapai via tunnel; login API + pin menunggu skrip v2 lab G1",
        }
    from django.db import transaction

    with transaction.atomic():
        router = Router.objects.create(
            tenant_id=enrollment.tenant_id,
            display_name=enrollment.display_name,
            router_code=enrollment.router_code,
            mode=Router.Mode.READ_ONLY,  # read-only default (§2.1)
            routeros_version=enrollment.routeros_version or "",
            tunnel_ip=enrollment.tunnel_ip,
            # Format credential = kode\0password — sesuai parser klien API-SSL
            # (apiclient._credentials: username rtrw-ro-<kode>); akun ini dipasang
            # pada router oleh skrip bootstrap v2 (menunggu lab G1).
            credential_ref=SecretBox.encrypt(f"{enrollment.router_code.lower()}\x00{api_password}"),
            api_cert_fingerprint=fingerprint,
            capability=capability,
        )
        RouterEnrollment.objects.filter(id=enrollment.id).update(
            router=router,
            status=RouterEnrollment.Status.COMPLETED,
            api_cert_fingerprint=fingerprint,
            device_identity={
                "wg_public_key": enrollment.wg_public_key,
                "simulator": source == "simulator",
                "probe": probe,
            },
            completed_at=timezone.now(),
        )
        WireGuardPeer.objects.filter(enrollment=enrollment).update(
            router=router, state=WireGuardPeer.State.APPLIED, applied_revision=1
        )
    return router


def run_discovery(router: Router) -> dict:
    """Discovery bounded — TIDAK membaca password (ROUTEROS.md §3).

    Pemanggil (job engine) sudah membuka tenant_scope (konvensi repo).
    """
    from adapters.routeros.base import RouterContext
    from adapters.routeros.factory import active_adapter_name, active_routeros_adapter

    ctx = RouterContext(
        router_id=str(router.id),
        tenant_id=str(router.tenant_id),
        tunnel_ip=str(router.tunnel_ip) if router.tunnel_ip else None,
        mode=router.mode,
        routeros_version=router.routeros_version or "7.15",
        credential_ref=router.credential_ref,
    )
    adapter = active_routeros_adapter()
    snapshot = DiscoverySnapshot.objects.create(tenant_id=router.tenant_id, router=router)
    accounts = adapter.list_accounts(ctx)
    count = 0
    for account in accounts:
        DiscoveryObject.objects.create(
            tenant_id=router.tenant_id,
            snapshot=snapshot,
            router=router,
            username=account.get("username", "")[:64],
            kind="pppoe" if account.get("service", "pppoe") in ("pppoe", "any") else "hotspot",
            router_service=account.get("service", "pppoe")[:8],
            profile=str(account.get("profile", ""))[:64],
            disabled_on_router=bool(account.get("disabled", False)),
            comment=str(account.get("comment", ""))[:255],
            raw={k: v for k, v in account.items() if k != "password"},  # password TIDAK disimpan
        )
        count += 1
    snapshot.status = DiscoverySnapshot.Status.SUCCEEDED
    snapshot.finished_at = timezone.now()
    snapshot.save(update_fields=["status", "finished_at"])
    # Tautkan sesi migrasi menunggu discovery.
    from domains.customers.models import MigrationSession

    MigrationSession.objects.filter(router=router, state="pending_discovery").update(
        snapshot=snapshot, state="discovered"
    )
    # Sampel kesehatan pertama (source jujur sesuai adapter aktif).
    from domains.network.models import RouterHealthSample

    health = adapter.read_health(ctx)
    RouterHealthSample.objects.create(
        tenant_id=router.tenant_id,
        router=router,
        vpn_up=health.get("vpn_up"),
        api_up=health.get("api_up"),
        cpu_percent=health.get("cpu_percent"),
        memory_percent=health.get("memory_percent"),
        uptime_s=health.get("uptime_s"),
        source=active_adapter_name(),
    )
    return {"snapshot_id": str(snapshot.id), "accounts": count}
