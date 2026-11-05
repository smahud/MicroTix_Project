"""Integrasi adopsi keypair WG installer + render konfigurasi host + probe.

Bukti jujur:
- Adopsi env MT_WG_SERVER_PUBKEY (X25519 nyata dari installer) → model
  WireGuardHost; bootstrap script memuat kunci NYATA, bukan placeholder.
- Rotasi dengan peer aktif DITOLAK; tanpa peer → adopsi idempoten.
- Render wg0.conf dari state (peers per-tenant via scope eksplisit), 0600,
  PrivateKey tidak pernah disematkan tanpa --private-key-file.
- Probe: binary wg hilang → BLOCKED (exit 2 path); jalur pembaruan peer
  diuji dengan stub berlabel jujur (source=stub, bukan klaim host nyata).
"""
from __future__ import annotations

import base64
import json
import stat
import time
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command

from domains.common.crypto import SecretBox
from domains.common.tenant_context import tenant_scope
from domains.network import services as net
from domains.network.models import WireGuardHost, WireGuardPeer

pytestmark = pytest.mark.integration

# Kunci X25519 valid 32-byte base64 (keluaran `wg pubkey` — kunci tes, bukan produksi).
_REAL_PUB = base64.b64encode(b"\x01" * 32).decode()
_OTHER_PUB = base64.b64encode(b"\x02" * 32).decode()


def _set_env_pub(monkeypatch, value: str) -> None:
    monkeypatch.setattr(settings, "MT_WG_SERVER_PUBKEY", value)


def _make_peer(tenant, *, public_key="peer-key", ip="100.127.40.5",
               state=WireGuardPeer.State.APPLIED) -> WireGuardPeer:
    with tenant_scope(tenant.id):
        return WireGuardPeer.objects.create(
            tenant=tenant, router=None, allowed_ip=ip,
            public_key=public_key, state=state,
        )


def _call_json(*args, **kw) -> dict:
    buf = StringIO()
    call_command(*args, stdout=buf, **kw)
    return json.loads(buf.getvalue())


class TestAdoption:
    def test_no_env_keeps_deterministic_dev_fallback(self, db, monkeypatch):
        _set_env_pub(monkeypatch, "")
        WireGuardHost.objects.all().delete()
        host = net._wg_host()
        assert host.key_source == WireGuardHost.KeySource.GENERATED_DEV
        assert len(host.public_key) == 44  # representasi deterministik jujur
        assert host.private_key_ref  # dev menyimpan privat terenkripsi sendiri

    def test_env_adopts_real_key_on_first_create(self, db, monkeypatch):
        _set_env_pub(monkeypatch, _REAL_PUB)
        WireGuardHost.objects.all().delete()
        host = net._wg_host()
        assert host.public_key == _REAL_PUB
        assert host.key_source == WireGuardHost.KeySource.INSTALLER_ENV
        assert host.private_key_ref == ""  # privat dipegang host (root), bukan aplikasi
        assert host.interface_name == "wg0"
        assert host.adopted_at is not None

    def test_adopt_command_idempotent(self, db, monkeypatch):
        _set_env_pub(monkeypatch, _REAL_PUB)
        host = net._wg_host()  # adopsi via first-use
        rev = host.desired_revision
        out = _call_json("adopt_wg_host")
        assert out["status"] == "ok" and out["changed"] is False
        host.refresh_from_db()
        assert host.desired_revision == rev  # idempoten: tanpa revision bump

    def test_adopt_command_rotates_without_peers(self, db, monkeypatch):
        _set_env_pub(monkeypatch, _REAL_PUB)
        net._wg_host()
        _set_env_pub(monkeypatch, _OTHER_PUB)  # keypair installer baru (mis. host reinstall)
        out = _call_json("adopt_wg_host")
        assert out["status"] == "ok" and out["changed"] is True
        assert out["public_key"] == _OTHER_PUB

    def test_adopt_check_mode_reports_mismatch_without_mutation(self, db, monkeypatch):
        _set_env_pub(monkeypatch, _REAL_PUB)
        host = net._wg_host()
        _set_env_pub(monkeypatch, _OTHER_PUB)
        buf = StringIO()
        with pytest.raises(CommandError) as excinfo:  # mismatch → exit 1
            call_command("adopt_wg_host", "--check", stdout=buf)
        assert excinfo.value.returncode == 1
        out = json.loads(buf.getvalue())
        assert out["status"] == "mismatch"
        host.refresh_from_db()
        assert host.public_key == _REAL_PUB  # check tidak bermutasi

    def test_adopt_check_mode_without_host_row_is_read_only(self, db, monkeypatch):
        """--check TIDAK boleh membuat baris host (reviewer F2): tanpa baris →
        status no_host jujur, tabel tetap kosong."""
        _set_env_pub(monkeypatch, _REAL_PUB)
        WireGuardHost.objects.all().delete()
        buf = StringIO()
        call_command("adopt_wg_host", "--check", stdout=buf)
        out = json.loads(buf.getvalue())
        assert out["status"] == "no_host"
        assert WireGuardHost.objects.count() == 0  # tidak dibuat oleh --check

    def test_adopt_command_refuses_rotation_with_active_peer(self, db, monkeypatch, tenant_a):
        _set_env_pub(monkeypatch, _REAL_PUB)
        net._wg_host()
        _make_peer(tenant_a, public_key="peer-key-1", ip="100.127.40.2")
        _set_env_pub(monkeypatch, _OTHER_PUB)
        buf = StringIO()
        with pytest.raises(CommandError) as excinfo:  # refused → exit 1
            call_command("adopt_wg_host", stdout=buf)
        assert excinfo.value.returncode == 1
        out = json.loads(buf.getvalue())
        assert out["status"] == "refused"
        # Host TIDAK berubah — peers lama tetap memegang kunci lama.
        host = WireGuardHost.objects.first()
        assert host.public_key == _REAL_PUB

    def test_bootstrap_script_contains_real_key(self, db, monkeypatch, tenant_a):
        _set_env_pub(monkeypatch, _REAL_PUB)
        with tenant_scope(tenant_a.id):
            enr = net.create_enrollment(str(tenant_a.id), {
                "display_name": "Router Kunci Nyata", "router_code": "RTR-WG-02", "mode": "read_only",
            })
            out = net.bootstrap_script(enr)
        assert f':local srvkey "{_REAL_PUB}"' in out["script"]

    def test_bootstrap_script_dev_fallback_labeled(self, db, monkeypatch, tenant_a):
        """Tanpa env: representasi deterministik tetap dipakai (dev/test jujur)."""
        _set_env_pub(monkeypatch, "")
        WireGuardHost.objects.all().delete()
        with tenant_scope(tenant_a.id):
            enr = net.create_enrollment(str(tenant_a.id), {
                "display_name": "Router Dev", "router_code": "RTR-WG-03", "mode": "read_only",
            })
            out = net.bootstrap_script(enr)
        host = net._wg_host()
        assert f':local srvkey "{host.public_key}"' in out["script"]
        assert host.key_source == WireGuardHost.KeySource.GENERATED_DEV


class TestRenderHostConfig:
    def test_render_without_private_key_is_honest(self, db, monkeypatch, tmp_path, tenant_a):
        _set_env_pub(monkeypatch, _REAL_PUB)
        _make_peer(tenant_a, public_key="peer-key-render", ip="100.127.40.5")
        out = _call_json("render_wg_config", "--target", str(tmp_path))
        assert out["status"] == "ok" and out["peers"] == 1
        assert out["private_key_embedded"] is False
        conf = (tmp_path / "wg0.conf").read_text()
        assert "[Interface]" in conf and "Address = 100.127.0.1/32" in conf
        assert "ListenPort = 51820" in conf
        # privat aktif TIDAK pernah ditulis tanpa file root (baris berawalan # boleh)
        active_private = [ln for ln in conf.splitlines() if ln.startswith("PrivateKey")]
        assert active_private == []
        assert "DIISI OLEH OPS HOST" in conf
        assert "[Peer]" in conf and "PublicKey = peer-key-render" in conf
        assert "AllowedIPs = 100.127.40.5/32" in conf
        assert "PersistentKeepalive = 25" in conf  # registry vpn.keepalive_s
        mode = stat.S_IMODE((tmp_path / "wg0.conf").stat().st_mode)
        assert mode == 0o600

    def test_render_with_private_key_file_embeds(self, db, monkeypatch, tmp_path, tenant_a):
        _set_env_pub(monkeypatch, _REAL_PUB)
        _make_peer(tenant_a, public_key="peer-key-render2", ip="100.127.40.6")
        keyfile = tmp_path / "server_private.key"
        keyfile.write_text("AAAAPRIVATETESTKEYNOTREAL\n")
        out = _call_json("render_wg_config", "--target", str(tmp_path),
                         "--private-key-file", str(keyfile))
        assert out["private_key_embedded"] is True
        conf = (tmp_path / "wg0.conf").read_text()
        assert "PrivateKey = AAAAPRIVATETESTKEYNOTREAL" in conf

    def test_render_excludes_removed_peers(self, db, monkeypatch, tmp_path, tenant_a):
        _set_env_pub(monkeypatch, _REAL_PUB)
        _make_peer(tenant_a, public_key="peer-gone", ip="100.127.40.8",
                   state=WireGuardPeer.State.REMOVED)
        out = _call_json("render_wg_config", "--target", str(tmp_path))
        assert out["peers"] == 0
        assert "[Peer]" not in (tmp_path / "wg0.conf").read_text()

    def test_render_includes_pending_peer(self, db, monkeypatch, tmp_path, tenant_a):
        """PENDING = desired state — dirender agar ops dapat menerapkan lebih awal."""
        _set_env_pub(monkeypatch, _REAL_PUB)
        _make_peer(tenant_a, public_key="peer-pending", ip="100.127.40.9",
                   state=WireGuardPeer.State.PENDING)
        out = _call_json("render_wg_config", "--target", str(tmp_path))
        assert out["peers"] == 1
        conf = (tmp_path / "wg0.conf").read_text()
        assert "state=pending" in conf and "PublicKey = peer-pending" in conf


class TestProbeHandshake:
    def test_probe_blocked_without_wg_binary(self, db, monkeypatch):
        _set_env_pub(monkeypatch, "")
        result = net.probe_handshakes(wg_bin="/tidak/ada/wg")
        assert result["status"] == "blocked"
        assert "binary wg tidak ditemukan" in result["error"]

    def test_probe_command_blocked_exit_2(self, db, monkeypatch):
        with pytest.raises(CommandError) as excinfo:
            _call_json("probe_wg", "--wg-bin", "/tidak-ada/wg")
        assert excinfo.value.returncode == 2

    def test_probe_updates_peer_handshake_via_stub(self, db, monkeypatch, tmp_path, tenant_a):
        """Jalur pembaruan diuji dengan stub berlabel jujur — bukan klaim host nyata."""
        _set_env_pub(monkeypatch, "")
        _make_peer(tenant_a, public_key="peer-stub-key", ip="100.127.40.7")
        epoch = int(time.time()) - 60
        stub = tmp_path / "wg-stub"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = "--version" ]; then echo "wg stub (tes, bukan host) v0"; exit 0; fi\n'
            f'printf "peer-stub-key\\t{epoch}\\n"\n'
        )
        stub.chmod(0o755)
        result = net.probe_handshakes(interface="wg0", wg_bin=str(stub))
        assert result["status"] == "ok"
        assert result["updated"] == 1
        assert result["evidence"]["binary"] == str(stub)
        with tenant_scope(tenant_a.id):
            peer = WireGuardPeer.objects.get(public_key="peer-stub-key")
            assert peer.last_handshake_at is not None
            stored = int(peer.last_handshake_at.timestamp())
        # Monotonik: probe ulang dengan epoch lebih lama tidak memundurkan.
        older = epoch - 3600
        stub.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "peer-stub-key\\t{older}\\n"\n'
        )
        stub.chmod(0o755)
        net.probe_handshakes(interface="wg0", wg_bin=str(stub))
        with tenant_scope(tenant_a.id):
            peer.refresh_from_db()
            assert int(peer.last_handshake_at.timestamp()) == stored

    def test_probe_reports_unknown_peer_on_interface(self, db, monkeypatch, tmp_path, tenant_a):
        _set_env_pub(monkeypatch, "")
        stub = tmp_path / "wg-stub"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = "--version" ]; then echo "wg stub v0"; exit 0; fi\n'
            'printf "orphan-key-on-interface\\t1780000000\\n"\n'
        )
        stub.chmod(0o755)
        result = net.probe_handshakes(interface="wg0", wg_bin=str(stub))
        assert result["status"] == "ok"
        assert result["unknown_on_interface"] == ["orphan-key-on-interface"]
        assert result["missing_on_interface"] == []  # tidak ada peer DB aktif

    def test_probe_reports_db_peer_missing_on_interface(self, db, monkeypatch, tmp_path, tenant_a):
        _set_env_pub(monkeypatch, "")
        _make_peer(tenant_a, public_key="peer-missing", ip="100.127.40.11")
        stub = tmp_path / "wg-stub"
        stub.write_text("#!/usr/bin/env bash\nexit 0\n")  # interface tanpa peer sama sekali
        stub.chmod(0o755)
        result = net.probe_handshakes(interface="wg0", wg_bin=str(stub))
        assert result["status"] == "ok"
        assert result["updated"] == 0
        assert result["missing_on_interface"][0]["public_key"] == "peer-missing"
