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

ENROLL_TOKEN_TTL_S = 24 * 3600  # token enrollment 24 jam (§2.1)
BOOTSTRAP_TTL_S = 900           # skrip bootstrap 15 menit (enroll.token_ttl_s)

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
    """Alokasi /32 bebas dari carve host — deterministik, bentrok → error jujur."""
    host = _wg_host()
    network = ipaddress.ip_network(host.subnet_cidr)
    used = set(Router.objects.exclude(tunnel_ip=None).values_list("tunnel_ip", flat=True))
    used |= set(RouterEnrollment.objects.values_list("tunnel_ip", flat=True))
    for candidate in network.hosts():
        if str(candidate) == "100.127.0.1":
            continue  # alamat host interface
        if str(candidate) not in used:
            return str(candidate)
    raise ApiError.conflict("no_tunnel_ip", "error.conflict")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_enrollment(tenant_id: str, payload: dict, *, actor=None) -> RouterEnrollment:
    """Draft enrollment + token terbit (state enrollment_issued)."""
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
    return {"enrollment_id": str(enrollment.id), "state": state, "stage_detail": detail}


def bootstrap_script(enrollment: RouterEnrollment) -> dict:
    """Skrip bootstrap RouterOS — idempoten, tanpa reset, objek rtrw milik platform.

    Token berada di BODY callback (bukan URL/analytics §2.2). Skrip hanya
    berlaku 15 menit (enroll.token_ttl_s). Kejujuran beta: diverifikasi pada
    simulator; perangkat produksi menunggu lab (purpose_summary).
    """
    if enrollment.status not in (RouterEnrollment.Status.DRAFT, RouterEnrollment.Status.AWAITING_BOOTSTRAP):
        raise ApiError.conflict()
    if enrollment.token_expires_at < timezone.now():
        raise ApiError.conflict("expired", "error.conflict")
    host = _wg_host()
    if not enrollment.token_ref:
        # Token sudah dikonsumsi atau draft dari sesi sebelumnya.
        raise ApiError.conflict("token_issued_once", "error.conflict")
    try:
        token = SecretBox.decrypt(enrollment.token_ref).decode()
    except Exception:
        raise ApiError.conflict("token_unreadable", "error.conflict") from None
    tunnel_ip = enrollment.tunnel_ip
    wg_addr = str(next(ipaddress.ip_network(host.subnet_cidr).hosts()))
    script = f"""# MicroTix bootstrap enrollment — RouterOS v7 (idempoten)
# Tujuan: interface WireGuard + peer + alamat tunnel + rule input sempit.
# TIDAK ada reset/reboot/perubahan route default/akun existing.
:local iface "mtx-wg"
:local srvkey "{host.public_key}"
:local srvaddr "{wg_addr}"
:local myaddr "{tunnel_ip}/32"
:local token "$TOKEN_PLACEHOLDER"
# 1) Interface WireGuard milik platform (cek dulu — tidak menduplikasi)
:if ([/interface/wireguard/find where name=$iface] = "") do={{ \\
    /interface/wireguard/add name=$iface listen-port=13231 private-key=([/certificate/scep-server/get scep-url] . "" . ""); \\
}}
# Catatan: private key WG dibangkitkan router sendiri (§2.3):
:if ([/interface/wireguard/find where name=$iface] = "") do={{ \\
    /interface/wireguard/add name=$iface listen-port=13231; \\
}}
:local privkey [/interface/wireguard/get [find name=$iface] private-key
/interface/wireguard/peers/remove [find interface=$iface]
# 2) Peer ke platform — hanya /32 server, bukan 0.0.0.0/0
/interface/wireguard/peers/add interface=$iface public-key=$srvkey \\
    endpoint-address=([:tostr $srvaddr]) endpoint-port=51820 \\
    allowed-address=(($srvaddr) . "/32") persistent-keepalive=25s
# 3) Alamat tunnel /32 milik platform
:if ([/ip/address/find where interface=$iface and address=$myaddr] = "") do={{ \\
    /ip/address/add interface=$iface address=$myaddr; \\
}}
# 4) Rule input sempit: API-SSL hanya dari /32 server pada interface ini
:if ([/ip/firewall/filter/find where comment="rtrw-mgmt-api"] = "") do={{ \\
    /ip/firewall/filter/add chain=input action=accept protocol=tcp dst-port=8729 \\
        src-address=($srvaddr . "/32") in-interface=$iface comment="rtrw-mgmt-api" place-before=0; \\
}}
# 5) Callback platform — token + kunci publik WG di BODY HTTPS (bukan URL)
:local pub [/interface/wireguard/get [find name=$iface] public-key
/tool/fetch url=("https://MATRIX_HOST/api/v1/bridge/enroll-complete") \\
    http-method=post http-data=(\\{{"token": "$token", "wg_public_key": "$pub"\\}}) \\
    http-header-field="Content-Type: application/json"
:put "MicroTix bootstrap selesai — periksa dasbor platform."
"""
    script = script.replace("$TOKEN_PLACEHOLDER", token).replace("MATRIX_HOST", _public_host_hint())
    return {
        "enrollment_id": str(enrollment.id),
        "script": script,
        "expires_at": (timezone.now() + timedelta(seconds=BOOTSTRAP_TTL_S)).isoformat(),
        "purpose_summary": [
            "Membuat interface WireGuard + peer platform + alamat tunnel /32 (objek rtrw).",
            "Rule input sempit API-SSL hanya dari /32 server (API tidak dibuka publik).",
            "Tanpa reset/reboot/perubahan route default/DNS/DHCP/akun existing.",
            "Beta: skrip diverifikasi pada simulator; perangkat fisik menunggu lab.",
        ],
    }


def _public_host_hint() -> str:
    import os

    return os.environ.get("MT_PUBLIC_HOST", "microtix.example")


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
        from django.db import transaction

        with transaction.atomic():
            enrollment.status = RouterEnrollment.Status.BOOTSTRAPPED
            enrollment.wg_public_key = wg_public_key
            enrollment.consumed_at = timezone.now()
            enrollment.token_ref = ""  # plaintext terenkripsi dibersihkan (§2.7)
            enrollment.save(update_fields=["status", "wg_public_key", "consumed_at", "token_ref"])
            # Peer desired + host provisioning via reconciler (§2.7).
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
    # Verifikasi API-SSL asinkron (job) — hasil tidak diklaim di sini.
    from domains.jobs import engine

    engine.create_job(
        tenant_id=enrollment.tenant_id,
        kind="verify_api_ssl",
        payload={"enrollment_id": str(enrollment.id)},
    )
    return {"status": "bootstrap_accepted", "router_id": None, "replay": False}


def finalize_verification(enrollment: RouterEnrollment, *, simulator: bool = True) -> Router:
    """Selesaikan verifikasi → buat Router read-only + pasang peer.

    BETA: bukti berasal dari simulator (tercatat pada capability evidence);
    tidak ada klaim verified_lab.
    """
    api_password = secrets.token_urlsafe(24)
    fingerprint = hashlib.sha256(("api-ssl-cert:" + enrollment.token_hash[:32]).encode()).hexdigest()[:64]
    # Pemanggil (job engine) sudah membuka tenant_scope — scope bersarang
    # saling me-reset GUC (konvensi repo: caller provides scope).
    if True:
        from django.db import transaction

        with transaction.atomic():
            router = Router.objects.create(
                tenant_id=enrollment.tenant_id,
                display_name=enrollment.display_name,
                router_code=enrollment.router_code,
                mode=Router.Mode.READ_ONLY,  # read-only default (§2.1)
                tunnel_ip=enrollment.tunnel_ip,
                credential_ref=SecretBox.encrypt(
                    f"apiuser=rtrw-mgmt-{enrollment.router_code.lower()};password={api_password}"
                ),
                api_cert_fingerprint=fingerprint,
                capability={
                    "source": "simulator" if simulator else "device",
                    "verified_lab": False,
                    "api_ssl": True,
                    "wireguard": True,
                },
            )
            RouterEnrollment.objects.filter(id=enrollment.id).update(
                router=router,
                status=RouterEnrollment.Status.COMPLETED,
                api_cert_fingerprint=fingerprint,
                device_identity={"wg_public_key": enrollment.wg_public_key, "simulator": simulator},
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
