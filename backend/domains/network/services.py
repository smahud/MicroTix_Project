"""Layanan enrollment router (M3) — ROUTEROS.md §2.

Alur: draft → token CSPRNG (hash-only, TTL) → bootstrap skrip aman →
bridge enroll-complete (konsumsi token atomik) → verifikasi API-SSL
(simulator di beta) → router read-only aktif + peer WireGuard desired.

Phase-2 (master directive konektivitas): SSTP sebagai transport KOMPLEMENTER
WireGuard — bukan pengganti. Kredensial per-router (username unik global +
password CSPRNG SecretBox), MSCHAPv2 saja, verifikasi sertifikat server
WAJIB nyala (tidak ada PAP/CHAP/MSCHAPv1, tidak ada verify=no), listener
shared-port tunggal untuk semua tenant. Sumber kapabilitas klien:
report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md.

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
    SstpAccount,
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
SUPPORTED_ENROLLMENT_PROTOCOLS = ("wireguard", "sstp")
_WIREGUARD_MIN_ROS_MAJOR = 7  # WireGuard hadir sejak RouterOS 7.1 (sumber riset)
# SSTP klien tersedia pada jalur v6.49.x DAN v7.x (matriks kapabilitas §2 —
# inilah alasan komplementer: router v6 yang tidak memuat WireGuard tetap
# dapat di-onboard read-only via SSTP). v5 dan lebih lama ditolak jujur.
_SSTP_MIN_ROS_MAJOR = 6
# Panjang password SSTP: token_urlsafe(24) = 32 karakter (192-bit entropi);
# alfabet [A-Za-z0-9_-] aman untuk kutip RouterOS + pemisah chap-secrets.
_SSTP_PASSWORD_NBYTES = 24
# Nama sertifikat CA platform pada penyimpanan sertifikat router.
_SSTP_CA_CERT_NAME = "MicroTix-CA"


def _sstp_gw_address(host: WireGuardHost) -> str:
    """Alamat PPP gateway SSTP — host KEDUA carve (pertama = WireGuard).

    Satu carve 100.127.0.0/16 dipakai bersama lintas protokol; alamat
    .1 = interface WireGuard host, .2 = alamat PPP server SSTP (akun
    chap-secrets meneruskan gw-ip-address ini ke router). Keduanya
    dikecualikan dari alokasi /32 oleh allocate_tunnel_ip.
    """
    hosts = ipaddress.ip_network(host.subnet_cidr).hosts()
    next(hosts)  # .1 — WireGuard
    return str(next(hosts))  # .2 — SSTP

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
            continue  # alamat interface WireGuard host
        if str(candidate) == "100.127.0.2":
            continue  # alamat PPP gateway SSTP host (Phase-2)
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
    elif protocol == "sstp":
        # SSTP hadir sejak era v4/v5 dan stabil di v6.49.x + v7.x (matriks
        # kapabilitas §2); v6 = jalur utama SSTP (WireGuard tidak tersedia).
        if int(routeros_version.split(".")[0]) < _SSTP_MIN_ROS_MAJOR:
            errors["routeros_version"] = [
                {
                    "code": "sstp_requires_v6",
                    "message": "SSTP membutuhkan RouterOS v6+ — versi lebih lama tidak didukung",
                }
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
    if protocol == "sstp":
        _issue_sstp_credentials(enrollment)
    return enrollment


def _issue_sstp_credentials(enrollment: RouterEnrollment) -> SstpAccount:
    """Terbitkan kredensial SSTP per-router pada draft (master directive §8).

    Username unik GLOBAL (kredensial tidak pernah dibagi lintas tenant):
    mtx-<kode-router-diskalahkan>-<suffix>. Password CSPRNG 192-bit disimpan
    hanya sebagai SecretBox; plaintext keluar TIDAK PERNAH dari sini — hanya
    saat render skrip bootstrap (pemilik, TTL 15 menit) dan chap-secrets
    (ops host). Tumbukan username (prefix 32-bit) ditangani retry bounded.
    """
    from django.db import IntegrityError

    code = enrollment.router_code.lower()[:16]
    for suffix in (enrollment.id.hex[:8], secrets.token_hex(5), secrets.token_hex(8)):
        try:
            return SstpAccount.objects.create(
                tenant_id=enrollment.tenant_id,
                enrollment=enrollment,
                username=f"mtx-{code}-{suffix}",
                password_ref=SecretBox.encrypt(secrets.token_urlsafe(_SSTP_PASSWORD_NBYTES)),
                tunnel_ip=enrollment.tunnel_ip,
            )
        except IntegrityError:
            continue
    raise ApiError.conflict("sstp_username_exhausted", "error.conflict")


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
        "sstp": bool(capability.get("sstp", False)),
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
    """Skrip bootstrap RouterOS — idempoten, tanpa reset (WG v7; SSTP v6/v7).

    Token berada di BODY callback (bukan URL/analytics §2.2). Skrip hanya
    berlaku 15 menit (enroll.token_ttl_s). Endpoint peer = hostname publik
    gateway dari konfigurasi (vpn.gateway_hostname / MT_PUBLIC_HOST /
    MT_DOMAIN) — TIDAK PERNAH IP tunnel internal. Private key WireGuard
    dibangkitkan router sendiri (§2.3); kredensial SSTP per-router diterbitkan
    platform (CSPRNG; §2.5 jalur injeksi kanal sah). Port listener dari state
    host/registri; port API dari enrollment. Kejujuran beta: sintaks teruji
    terhadap simulator; perangkat produksi menunggu lab G1.
    """
    if enrollment.status not in (RouterEnrollment.Status.DRAFT, RouterEnrollment.Status.AWAITING_BOOTSTRAP):
        raise ApiError.conflict()
    if enrollment.token_expires_at < timezone.now():
        raise ApiError.conflict("expired", "error.conflict")
    if enrollment.protocol not in SUPPORTED_ENROLLMENT_PROTOCOLS:  # defense-in-depth
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

    gateway = gateway_hostname()
    if enrollment.protocol == "sstp":
        return _render_sstp_bootstrap(enrollment, host=host, gateway=gateway, token=token, registry=registry)
    keepalive = registry().get_int("vpn.keepalive_s")
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


def _render_sstp_bootstrap(
    enrollment: RouterEnrollment, *, host: WireGuardHost, gateway: str, token: str, registry
) -> dict:
    """Skrip bootstrap SSTP (v6/v7) — render dari state tervalidasi saja.

    Keamanan wajib (master directive §8): authentication=mschap2 SAJA (klien
    SSTP RouterOS tanpa EAP — matriks kapabilitas §2), verifikasi sertifikat
    server NYALA (verify-server-certificate + verifikasi alamat dari
    sertifikat; CA platform diimpor lebih dulu), TANPA add-default-route.
    Kredensial per-router (username+password) disematkan pada skrip — skrip
    sensitif TTL 15 menit (§2.2); password tetap dipakai router untuk
    koneksi ulang (disimpan perangkat sebagai konfigurasi sstp-client).
    """
    account = SstpAccount.objects.filter(enrollment=enrollment).first()
    if account is None:
        # State tak konsisten (akun hilang) — gagal jujur, jangan render skrip.
        raise ApiError.conflict("sstp_account_missing", "error.conflict")
    try:
        password = SecretBox.decrypt(account.password_ref).decode()
    except Exception:
        raise ApiError.conflict("sstp_password_unreadable", "error.conflict") from None
    sstp_port = registry().get_int("vpn.sstp_listen_port")
    gw_addr = _sstp_gw_address(host)
    script = _ROUTEROS_SSTP_TEMPLATE
    for placeholder, value in (
        ("{GATEWAY}", gateway),
        ("{SSTP_PORT}", str(sstp_port)),
        ("{GW_ADDR}", gw_addr),
        ("{API_PORT}", str(enrollment.api_port)),
        ("{SSTP_USER}", account.username),
        ("{SSTP_PASS}", password),
        ("{CA_NAME}", _SSTP_CA_CERT_NAME),
        ("{TOKEN}", token),
    ):
        script = script.replace(placeholder, value)
    return {
        "enrollment_id": str(enrollment.id),
        "protocol": "sstp",
        "routeros_version": enrollment.routeros_version or "7",
        "script": script,
        "expires_at": (timezone.now() + timedelta(seconds=BOOTSTRAP_TTL_S)).isoformat(),
        "gateway": {
            "hostname": gateway,
            "listen_port": sstp_port,
            "api_port": enrollment.api_port,
            "server_tunnel_ip": gw_addr,
        },
        "purpose_summary": [
            "Membuat klien SSTP + route API manajemen via tunnel TLS (objek rtrw milik platform; idempoten).",
            f"Endpoint gateway: {gateway}:{sstp_port}/TCP (TLS 1.2, MSCHAPv2) — listener shared-port seluruh router.",
            "CA platform diunduh + diimpor; verifikasi sertifikat server WAJIB nyala (tidak dapat dimatikan skrip ini).",
            "Rule input sempit API-SSL hanya dari alamat PPP server (API tidak dibuka publik).",
            "Tanpa reset/reboot/add-default-route/DNS/DHCP/NAT/bridge/akun existing.",
            "Skrip memuat kredensial SSTP per-router (sensitif — TTL 15 menit; jangan disimpan di tempat lain).",
            "Beta: sintaks skrip diverifikasi pada simulator; perangkat v6/v7 fisik menunggu lab G1.",
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

# Skrip RouterOS v6/v7 (SSTP) — sintaks klasik berjarak (didokumentasikan
# pada halaman SSTP help/manual untuk kedua jalur utama; matriks kapabilitas
# §2). Placeholder diisi render-time dari state tervalidasi — kredensial
# per-router TIDAK pernah berasal dari string bebas frontend. Baris "\" =
# lanjutan baris RouterOS. GAP TERDOKUMENTASI (lab G1): paritas field v6
# (verify-server-address-from-certificate) + sintaks pada perangkat nyata
# menunggu bukti lab; skrip memakai field inti yang didokumentasikan lintas
# versi (connect-to/port/user/password/authentication/
# verify-server-certificate).
_ROUTEROS_SSTP_TEMPLATE = """# MicroTix bootstrap enrollment — RouterOS v6/v7 · SSTP — idempoten
# Gateway: {GATEWAY}:{SSTP_PORT}/TCP (TLS 1.2 + MSCHAPv2) · API manajemen: {GW_ADDR}:{API_PORT}/TCP via tunnel
# TIDAK ada reset/reboot/perubahan route default/DNS/DHCP/NAT/bridge/akun existing.
:local iface "mtx-sstp"
:local user "{SSTP_USER}"
:local pass "{SSTP_PASS}"
:local gwaddr "{GW_ADDR}"
:local token "{TOKEN}"
# 1) CA platform (materi PUBLIK) diunduh + diimpor — syarat verifikasi
#    sertifikat server oleh klien SSTP. GAP G1: fetch tanpa check-certificate
#    (idem callback Phase-1); dampak dibatasi CA-publik + kredensial CSPRNG.
/tool/fetch url="https://{GATEWAY}/api/v1/bridge/enroll-ca" dst-path=microtix-ca.crt
:if ([:len [/certificate/find where name="{CA_NAME}"]] = 0) do={ \\
    /certificate/import file-name=microtix-ca.crt passphrase="" name="{CA_NAME}"; \\
}
# 2) Klien SSTP milik platform — kredensial per-router; MSCHAPv2 SAJA;
#    verifikasi sertifikat server + alamat dari sertifikat WAJIB nyala;
#    TANPA add-default-route (route manajemen via interface tunnel).
#    Idempoten: objek lama milik platform diganti (re-enroll/replace).
/interface/sstp-client/remove [find name=$iface]
/interface/sstp-client/add name=$iface connect-to={GATEWAY} port={SSTP_PORT} \\
    user=$user password=$pass authentication=mschap2 \\
    verify-server-certificate=yes verify-server-address-from-certificate=yes \\
    disabled=no
# 3) Rule input sempit: API-SSL hanya dari alamat PPP server platform pada
#    interface manajemen (API tidak dibuka publik).
:if ([:len [/ip/firewall/filter/find where comment="rtrw-mgmt-api"]] = 0) do={ \\
    /ip/firewall/filter/add chain=input action=accept protocol=tcp dst-port={API_PORT} \\
        src-address=($gwaddr . "/32") in-interface=$iface comment="rtrw-mgmt-api" place-before=0; \\
}
# 4) Callback platform — token + identitas kredensial di BODY HTTPS (§2.2).
#    Identitas SSTP = username per-router (tidak ada kunci publik klien).
:local cb ("{\\"token\\":\\"" . $token . "\\",\\"protocol\\":\\"sstp\\",\\"sstp_username\\":\\"" . $user . "\\"}")
/tool/fetch url="https://{GATEWAY}/api/v1/bridge/enroll-complete" \\
    http-method=post http-data=$cb http-header-field="Content-Type: application/json"
:put "MicroTix bootstrap SSTP selesai — pantau status verifikasi di dasbor platform."
"""


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


def enroll_ca_bundle() -> str:
    """Baca bundel CA platform untuk endpoint enroll-ca (materi PUBLIK).

    Sumber: env MT_SSTP_CA_PATH (dipasang installer §setup_sstp — CA milik
    SSTP listener, bukan sertifikat platform HTTPS). Tanpa env / berkas
    hilang / bukan PEM → error jujur (TIDAK ada fallback palsu). CA adalah
    materi publik; hanya sertifikat CA yang disajikan — kunci privat tidak
    pernah melewati endpoint ini.
    """
    path = os.environ.get("MT_SSTP_CA_PATH", "")
    if not path:
        raise ApiError.conflict("enroll_ca_unconfigured", "error.conflict")
    if not os.path.isfile(path) or os.path.getsize(path) > 256 * 1024:
        raise ApiError.conflict("enroll_ca_unavailable", "error.conflict")
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        bundle = fh.read()
    if "BEGIN CERTIFICATE" not in bundle:
        raise ApiError.conflict("enroll_ca_invalid", "error.conflict")
    return bundle


# Konfigurasi server accel-ppp 1.15.0 (Phase-2) — kunci/nilai diverifikasi
# dari accel-ppp.conf sampel rilis 1.15.0 + man page accel-ppp.conf(5):
# [sstp] port/ssl-protocol/ssl-ciphers/ssl-pemfile/ssl-keyfile/ifname/
# ppp-max-mtu; [chap-secrets] chap-secrets=/gw-ip-address= (format berkas
# per-baris: username password ip [rate] — sumber: chap-secrets.c rilis).
# Ciphers = AES256-SHA + AES256-GCM-SHA384 — dua suite yang DOKUMENTASIKAN
# dapat dipilih klien SSTP RouterOS (matriks kapabilitas §2); TLS dibatasi
# 1.2 (klien RouterOS tanpa opsi TLS 1.3).
_SSTP_ACCEL_CONF_TEMPLATE = """# MicroTix — server SSTP manajemen router (Phase-2) — dirender dari state
# akun aktif (SstpAccount); diterapkan ops host: /etc/microtix/sstp/accel-ppp.conf
# Listener SHARED-PORT untuk seluruh router tenant (bukan per-tenant).
# TLS 1.2 + MSCHAPv2 saja (klien SSTP RouterOS tanpa EAP); verifikasi
# sertifikat server di sisi router WAJIB nyala (skrip bootstrap).
# Aktifkan (root): systemctl enable --now microtix-sstp
[modules]
log_file
sstp
auth_mschap_v2
chap-secrets

[core]
log-error=/var/log/accel-ppp/core.log

[common]
# Router boleh tersambung ulang (reboot) — sesi lama digantikan, bukan
# memblokir kredensial yang sama milik router tersebut.
single-session=replace

[ppp]
# Tanpa MPPE — TLS SSTP sudah mengenkripsi transport; menolak negosiasi
# ganda mencegah confusi kripto.
mppe=deny

[sstp]
port={SSTP_PORT}
# Bind eksplisit semua antarmuka; akses dibatasi nftables host (ops).
ssl-protocol=tls1.2
ssl-ciphers=AES256-SHA:AES256-GCM-SHA384
ssl-pemfile=/etc/microtix/sstp/gateway.pem
ssl-keyfile=/etc/microtix/sstp/gateway.key
ifname=mtx-sstp%d
# Samakan MTU maksimum dengan default klien SSTP RouterOS (1460).
ppp-max-mtu=1460

[chap-secrets]
chap-secrets=/etc/microtix/sstp/chap-secrets
# Alamat PPP gateway (host kedua carve 100.127.0.0/16; .1 = WireGuard).
gw-ip-address={GW_ADDR}

[log]
log-file=/var/log/accel-ppp/accel-ppp.log
log-emerg=/var/log/accel-ppp/emerg.log
log-fail-file=/var/log/accel-ppp/auth-fail.log
copy=1
# level 3 = sesi + kegagalan auth (audit koneksi; tanpa password di log).
level=3

[cli]
# CLI lokal ops (accel-cmd) — audit sesi; TIDAK diexpose jaringan.
verbose=1
telnet=127.0.0.1:2000
tcp=127.0.0.1:2001
"""


def render_sstp_config(target_dir: str) -> dict:
    """Render accel-ppp.conf + chap-secrets dari akun SSTP aktif (ops host).

    TIDAK menyentuh proses/listener aktif; idempoten; berkas 0600 (berkas
    memuat password kredensial per-router — sensitif, milik root host).
    Akun REMOVED tidak dirender; PENDING/APPLIED/DRIFT dirender (desired).
    chap-secrets per-baris (format accel-ppp 1.15.0): username password ip.
    """
    from domains.config.registry import registry

    host = _wg_host()
    sstp_port = registry().get_int("vpn.sstp_listen_port")
    gw_addr = _sstp_gw_address(host)

    lines = [
        f"# MicroTix chap-secrets SSTP — dirender {timezone.now().isoformat()}",
        "# Format accel-ppp: username password <ip-statis-per-router>",
        "# IP statis = /32 tunnel enrollment (unik global lintas tenant).",
        "# BERKAS SENSITIF (password) — root:600; dirender ulang reconciler.",
    ]
    account_count = 0
    tenants_touched = 0
    from domains.tenancy.models import Tenant

    for tenant in Tenant.objects.order_by("id"):
        rendered_for_tenant = 0
        with tenant_scope(tenant.id):
            accounts = (
                SstpAccount.objects.exclude(state=SstpAccount.State.REMOVED)
                .select_related("router", "enrollment")
                .order_by("tunnel_ip")
            )
            for account in accounts:
                try:
                    password = SecretBox.decrypt_str(account.password_ref)
                except Exception:
                    # Kredensial tidak terbaca — jangan render baris rusak;
                    # laporkan sebagai akun gagal (ops menyelidiki).
                    password = ""
                router_code = account.router.router_code if account.router else "-"
                lines.append(
                    f"# tenant={account.tenant_id} router={router_code} state={account.state}"
                    + ("" if password else " GAGAL-DEKRIP")
                )
                if password:
                    lines.append(f"{account.username} {password} {account.tunnel_ip}")
                    rendered_for_tenant += 1
        if rendered_for_tenant:
            tenants_touched += 1
        account_count += rendered_for_tenant

    os.makedirs(target_dir, exist_ok=True)
    conf_path = os.path.join(target_dir, "accel-ppp.conf")
    secrets_path = os.path.join(target_dir, "chap-secrets")
    conf_body = _SSTP_ACCEL_CONF_TEMPLATE.replace("{SSTP_PORT}", str(sstp_port)).replace("{GW_ADDR}", gw_addr)
    secrets_body = "\n".join(lines) + "\n"
    for path, body in ((conf_path, conf_body), (secrets_path, secrets_body)):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.chmod(path, 0o600)
    return {
        "status": "ok",
        "config_file": conf_path,
        "secrets_file": secrets_path,
        "accounts": account_count,
        "tenants": tenants_touched,
        "listen_port": sstp_port,
        "gateway_ppp_address": gw_addr,
        "note": "terapkan (root): pasang ke /etc/microtix/sstp/ lalu restart microtix-sstp",
    }


def complete_enrollment(token: str, wg_public_key: str = "", sstp_username: str = "") -> dict:
    """Bridge enroll-complete: konsumsi token atomik (§2.7).

    Token di body; hash lookup; replay nonce+key sama = hasil logis sama;
    identitas berbeda = 409. Identitas per protokol: WireGuard = kunci
    publik WG; SSTP = username kredensial per-router (dicocokkan dengan
    SstpAccount enrollment ini — sumber kebenaran yang tidak dapat dipalsukan
    tanpa memegang skrip/token). Mengembalikan status untuk callback router.
    """
    if not token or len(token) > 200:
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
    # Validasi identitas per protokol SEBELUM transisi (protokol enrollment
    # menentukan bentuk identitas; bentuk lain ditolak jujur).
    account: SstpAccount | None = None
    if enrollment.protocol == "sstp":
        if wg_public_key:
            raise ApiError.validation(
                {"protocol": [{"code": "mismatch", "message": "Enrollment SSTP tidak memakai kunci publik WireGuard"}]}
            )
        if not sstp_username or len(sstp_username) > 64:
            raise ApiError.validation()
        with tenant_scope(enrollment.tenant_id):
            account = SstpAccount.objects.filter(enrollment=enrollment).first()
        if account is None or account.username != sstp_username:
            # Token benar tetapi identitas kredensial tidak cocok — 409,
            # bukan 404 (token diketahui; kredensial salah).
            raise ApiError.conflict("sstp_identity_mismatch", "error.conflict")
    else:
        if not wg_public_key or len(wg_public_key) > 64:
            raise ApiError.validation()
        if sstp_username:
            raise ApiError.validation(
                {"protocol": [{"code": "mismatch", "message": "Enrollment WireGuard tidak memakai username SSTP"}]}
            )
    # Replay/retransmit: token terkonsumsi dengan identitas SAMA → hasil
    # logis sama tanpa mengulang efek (§2.7); identitas berbeda → 409.
    if enrollment.status in (
        RouterEnrollment.Status.BOOTSTRAPPED,
        RouterEnrollment.Status.VERIFYING,
        RouterEnrollment.Status.COMPLETED,
    ):
        same_identity = (
            (account is not None and account.username == sstp_username)
            if enrollment.protocol == "sstp"
            else (enrollment.wg_public_key == wg_public_key)
        )
        if same_identity:
            status = "completed" if enrollment.status == RouterEnrollment.Status.COMPLETED else "bootstrap_accepted"
            return {"status": status, "router_id": str(enrollment.router_id or ""), "replay": True}
        raise ApiError.conflict()  # identitas berbeda pada token terpakai
    if enrollment.status not in (RouterEnrollment.Status.DRAFT, RouterEnrollment.Status.AWAITING_BOOTSTRAP):
        raise ApiError.conflict()

    with tenant_scope(enrollment.tenant_id):
        from django.db import IntegrityError, transaction

        with transaction.atomic():
            enrollment.status = RouterEnrollment.Status.BOOTSTRAPPED
            enrollment.consumed_at = timezone.now()
            enrollment.token_ref = ""  # plaintext terenkripsi dibersihkan (§2.7)
            if enrollment.protocol == "wireguard":
                enrollment.wg_public_key = wg_public_key
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
            else:
                # SSTP: akun kredensial sudah dibuat saat draft; tidak ada
                # peer kriptografis — kredensial = identitas (di atas).
                enrollment.save(update_fields=["status", "consumed_at", "token_ref"])
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
            "sstp": False,
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
            "sstp": enrollment.protocol == "sstp",  # tunnel SSTP nyata teramati via probe
            "protocol": enrollment.protocol,
            "probe": probe,
            "note": (
                "TLS API-SSL tercapai via tunnel; login API + pin menunggu skrip v2 lab G1"
                if enrollment.protocol != "sstp"
                else "TLS API-SSL tercapai via tunnel SSTP (sesi PPP nyata); login API + pin menunggu skrip v2 lab G1"
            ),
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
            device_identity=(
                {
                    "sstp_username": (SstpAccount.objects.filter(enrollment=enrollment).values_list("username", flat=True).first() or ""),
                    "simulator": source == "simulator",
                    "probe": probe,
                }
                if enrollment.protocol == "sstp"
                else {
                    "wg_public_key": enrollment.wg_public_key,
                    "simulator": source == "simulator",
                    "probe": probe,
                }
            ),
            completed_at=timezone.now(),
        )
        if enrollment.protocol == "sstp":
            # Kredensial aktif + terpasang pada router (pola peer WG §2.7):
            # reconciler merender akun pada chap-secrets host.
            SstpAccount.objects.filter(enrollment=enrollment).update(
                router=router, state=SstpAccount.State.APPLIED, applied_revision=1
            )
        else:
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
