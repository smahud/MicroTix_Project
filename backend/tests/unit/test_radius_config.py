"""Tes unit reconciler konfigurasi FreeRADIUS — RADIUS.md §2/§12.

Tanpa DB: render clients.conf/modul sql/radiusd.conf + izin berkas rahasia.
Bila binary nyata tersedia (ekstraksi deb), bundle juga divalidasi dengan
``freeradius -C`` — bukti sintaks 3.2, bukan asumsi.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from domains.radius import reconciler

pytestmark = pytest.mark.unit

NAS_ROWS = [
    {"nasname": "100.127.10.1", "secret": "s" * 32, "shortname": "RTR-A1", "tenant_id": "t-a"},
    {"nasname": "100.127.10.2", "secret": "q" * 32, "shortname": "RTR-A2", "tenant_id": "t-b"},
]

DB = {"host": "127.0.0.1", "port": 55432, "db": "microtix", "login": "mtx_radius", "password": "daemon-pass"}


def _sql_module() -> str:
    return reconciler.render_sql_module(**DB)


class TestClientsConf:
    def test_require_message_authenticator_per_client(self):
        conf = reconciler.render_clients_conf(NAS_ROWS)
        # Mitigasi BlastRADIUS (§12): setiap klien mewajibkan MA.
        assert conf.count("require_message_authenticator = yes") == len(NAS_ROWS)

    def test_one_client_per_nas_with_secret_and_ip(self):
        conf = reconciler.render_clients_conf(NAS_ROWS)
        assert "client nas-100.127.10.1 {" in conf
        assert "client nas-100.127.10.2 {" in conf
        assert 'ipaddr = 100.127.10.1' in conf
        assert f'secret = "{"s" * 32}"' in conf
        # shortname dari kode router (identitas metadata daemon, bukan payload).
        assert 'shortname = "RTR-A1"' in conf

    def test_empty_nas_renders_empty(self):
        assert reconciler.render_clients_conf([]) == "\n"


class TestSqlModule:
    """Modul sql hanya memanggil facade tenant-aware — bukan tabel mentah."""

    def test_authorize_queries_call_facades(self):
        sql = _sql_module()
        assert "radius.authorize_check('%{Packet-Src-IP-Address}'" in sql
        assert "radius.authorize_reply('%{Packet-Src-IP-Address}'" in sql
        # Tenant diikat dari ALAMAT SUMBUNGA paket (§4), bukan atribut payload.
        assert "NAS-IP-Address" not in sql

    def test_session_queries_call_facades(self):
        sql = _sql_module()
        assert "radius.session_count('%{Packet-Src-IP-Address}'" in sql
        # simul_verify_query mengembalikan sesi terbuka NYATA (mod_checksimul
        # rlm_sql me-reset hitungan lalu hanya menghitung baris verify).
        assert "FROM radius.session_list('%{Packet-Src-IP-Address}'" in sql
        for col in ("radacctid", "acctsessionid", "username", "nasipaddress", "nasportid",
                    "framedipaddress", "callingstationid", "framedprotocol"):
            assert col in sql

    def test_accounting_queries_call_facade_for_all_types(self):
        sql = _sql_module()
        assert sql.count("SELECT radius.accounting(") == 3  # start/interim/stop
        for status in ("'Start'", "'Interim-Update'", "'Stop'"):
            assert status in sql
        assert "radius.accounting_onoff(" in sql

    def test_postauth_query_logs_reply(self):
        sql = _sql_module()
        assert "radius.post_auth('%{Packet-Src-IP-Address}'" in sql

    def test_daemon_credentials_embedded(self):
        sql = _sql_module()
        assert 'login = "mtx_radius"' in sql
        assert 'password = "daemon-pass"' in sql
        assert 'driver = "rlm_sql_postgresql"' in sql


class TestRadiusdConf:
    def test_bind_loopback_and_ports(self):
        conf = reconciler.render_radiusd_conf(prefix="/tmp/mtx-r", listen_ip="127.0.0.1", auth_port=18120, acct_port=18121)
        site = reconciler.render_site(listen_ip="127.0.0.1", auth_port=18120, acct_port=18121)
        # Tidak ada listener publik (§12) — hanya 127.0.0.1 (tunnel produksi
        # memakai alamat WG; harness loopback).
        assert "ipaddr = 127.0.0.1" in site
        assert "port = 18120" in site and "port = 18121" in site
        assert "type = auth" in site and "type = acct" in site
        # Password tidak pernah dicatat (§12).
        assert "auth_goodpass = no" in conf and "auth_badpass = no" in conf


class TestWriteConfig:
    def test_bundle_files_and_secret_permissions(self, tmp_path):
        written = reconciler.write_config(
            tmp_path,
            nas_rows=NAS_ROWS,
            db={"host": DB["host"], "port": DB["port"], "name": DB["db"], "login": DB["login"], "password": DB["password"]},
            auth_port=18120,
            acct_port=18121,
        )
        assert "radiusd.conf" in written and "clients.conf" in written
        assert "mods-enabled/sql" in written and "sites-enabled/default" in written
        # Berkas pembawa rahasia wajib 0600 (kredensial daemon + secret NAS).
        for rel in ("mods-enabled/sql", "clients.conf"):
            mode = stat.S_IMODE((tmp_path / rel).stat().st_mode)
            assert mode == 0o600, f"{rel} harus 0600, dapat {oct(mode)}"
        # Berkas non-rahasia: tidak boleh dapat-ditulis dunia (umask apa pun).
        mode = stat.S_IMODE((tmp_path / "radiusd.conf").stat().st_mode)
        assert mode & 0o002 == 0, oct(mode)

    def test_validate_config_missing_binary(self, tmp_path, monkeypatch):
        reconciler.write_config(
            tmp_path,
            nas_rows=NAS_ROWS,
            db={"host": DB["host"], "port": DB["port"], "name": DB["db"], "login": DB["login"], "password": DB["password"]},
            auth_port=18120,
            acct_port=18121,
        )
        monkeypatch.setattr(reconciler, "FREERADIUS_BIN", "/nonexistent/freeradius")
        code, out = reconciler.validate_config(tmp_path)
        assert code == 127
        assert "tidak ditemukan" in out

    @pytest.mark.skipif(not reconciler.freeradius_available(), reason="binary freeradius tidak tersedia")
    def test_validate_config_real_binary(self, tmp_path):
        """Bukti nyata: bundle lolos `freeradius -C` pada binary 3.2.7."""
        reconciler.write_config(
            tmp_path,
            nas_rows=NAS_ROWS,
            db={"host": DB["host"], "port": DB["port"], "name": DB["db"], "login": DB["login"], "password": DB["password"]},
            auth_port=18120,
            acct_port=18121,
        )
        code, out = reconciler.validate_config(tmp_path)
        assert code == 0, out[-2000:]
