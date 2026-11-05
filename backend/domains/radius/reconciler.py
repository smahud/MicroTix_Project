"""Reconciler FreeRADIUS — render + validasi konfigurasi (RADIUS.md §2).

- clients.conf dari baris radius.nas; satu client per NAS dengan secret
  unik per router (§6.4) dan require_message_authenticator (BlastRADIUS §12).
- Modul sql HANYA memanggil facade tenant-aware (§4) — resolusi tenant dari
  ALAMAT SUMBUNGA paket (%{Packet-Src-IP-Address}), bukan atribut payload.
- Bentuk baris authorize mengikuti posisi kolom rlm_sql 3.x:
  (id, username, attribute, value, op) — diverifikasi freeradius -X 3.2.7.
- simul_verify_query memanggil radius.session_list (kolom persis mod_checksimul).
- Validasi via freeradius -C pada binary terpinn (MT_FREERADIUS_BIN).
- Penerapan restart/reload produksi = tanggung jawab installer (root host);
  reconciler tidak mengklaim applied sebelum probe (§2).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FREERADIUS_BIN = os.environ.get(
    "MT_FREERADIUS_BIN", "/home/z/my-project/frdeb/extracted/usr/sbin/freeradius"
)
FREERADIUS_ROOT = os.environ.get(
    "MT_FREERADIUS_ROOT", "/home/z/my-project/frdeb/extracted"
)


def freeradius_available() -> bool:
    return os.path.exists(FREERADIUS_BIN)


# ---------------------------------------------------------------------------
# Render per berkas (murni — mudah diuji)


def render_clients_conf(nas_rows: list[dict]) -> str:
    """clients.conf dari baris NAS; kosong → berkas kosong (bukan placeholder)."""
    parts: list[str] = []
    for row in nas_rows:
        shortname = str(row.get("shortname") or row.get("nasname"))[:32]
        parts.append(
            f'client nas-{row["nasname"]} {{\n'
            f"    ipaddr = {row['nasname']}\n"
            f'    secret = "{row["secret"]}"\n'
            f"    require_message_authenticator = yes\n"
            f'    shortname = "{shortname}"\n'
            f"    nas_type = other\n"
            f"}}\n"
        )
    if not parts:
        return "\n"  # tanpa NAS → berkas kosong sah (bukan placeholder palsu)
    return "".join(parts)


def render_sql_module(*, host: str, port: int, db: str, login: str, password: str) -> str:
    # Semua kueri data memanggil facade dengan alamat sumber paket (§4).
    # Struktur seksi mengikuti queries.conf 3.2: accounting bersarang di
    # type { <Acct-Status-Type> { query } } via reference dispatcher;
    # post-auth { query } juga bersarang (kunci datar 3.0 diabaikan senyap).
    return f"""# Dibuat reconciler MicroTix — JANGAN edit manual.
# rlm_sql postgresql; akses data HANYA lewat facade tenant-aware.
sql {{
    dialect = "postgresql"
    driver = "rlm_sql_postgresql"
    server = "{host}"
    port = {port}
    login = "{login}"
    password = "{password}"
    radius_db = "{db}"
    read_clients = no

    pool {{
        start = 2
        min = 1
        max = 8
        spare = 2
        lifetime = 3600
        idle_timeout = 600
    }}

    authorize_check_query = "SELECT id, username, attribute, value, op FROM radius.authorize_check('%{{Packet-Src-IP-Address}}', '%{{User-Name}}')"
    authorize_reply_query = "SELECT id, username, attribute, value, op FROM radius.authorize_reply('%{{Packet-Src-IP-Address}}', '%{{User-Name}}')"
    group_membership_query = "SELECT NULL AS groupname, NULL AS reply_attr WHERE 1 = 0"

    simul_count_query = "SELECT COUNT(*) FROM radius.session_count('%{{Packet-Src-IP-Address}}', '%{{User-Name}}')"
    simul_verify_query = "SELECT radacctid, acctsessionid, username, nasipaddress, nasportid, framedipaddress, callingstationid, framedprotocol FROM radius.session_list('%{{Packet-Src-IP-Address}}', '%{{User-Name}}')"

    accounting {{
        reference = "%{{tolower:type.%{{%{{Acct-Status-Type}}:-%{{Request-Processing-Stage}}}}.query}}"
        type {{
            accounting-on {{
                query = "SELECT radius.accounting_onoff('%{{Packet-Src-IP-Address}}', 'Accounting-On')"
            }}
            accounting-off {{
                query = "SELECT radius.accounting_onoff('%{{Packet-Src-IP-Address}}', 'Accounting-Off')"
            }}
            start {{
                query = "SELECT radius.accounting('%{{Packet-Src-IP-Address}}', '%{{Acct-Unique-Session-Id}}', '%{{Acct-Session-Id}}', '%{{User-Name}}', 'Start', %{{Acct-Delay-Time}}, %{{Acct-Input-Octets}}, %{{Acct-Output-Octets}}, %{{Acct-Session-Time}}, '%{{Acct-Terminate-Cause}}', NULLIF('%{{Framed-IP-Address}}', '')::inet)"
            }}
            interim-update {{
                query = "SELECT radius.accounting('%{{Packet-Src-IP-Address}}', '%{{Acct-Unique-Session-Id}}', '%{{Acct-Session-Id}}', '%{{User-Name}}', 'Interim-Update', %{{Acct-Delay-Time}}, %{{Acct-Input-Octets}}, %{{Acct-Output-Octets}}, %{{Acct-Session-Time}}, '%{{Acct-Terminate-Cause}}', NULLIF('%{{Framed-IP-Address}}', '')::inet)"
            }}
            stop {{
                query = "SELECT radius.accounting('%{{Packet-Src-IP-Address}}', '%{{Acct-Unique-Session-Id}}', '%{{Acct-Session-Id}}', '%{{User-Name}}', 'Stop', %{{Acct-Delay-Time}}, %{{Acct-Input-Octets}}, %{{Acct-Output-Octets}}, %{{Acct-Session-Time}}, '%{{Acct-Terminate-Cause}}', NULLIF('%{{Framed-IP-Address}}', '')::inet)"
            }}
        }}
    }}

    post-auth {{
        query = "SELECT radius.post_auth('%{{Packet-Src-IP-Address}}', '%{{User-Name}}', '%{{reply:Packet-Type}}')"
    }}
}}
"""


def render_radiusd_conf(*, prefix: str, listen_ip: str, auth_port: int, acct_port: int, user: str | None = None, group: str | None = None) -> str:
    # 3.2.7: user/group/allow_core_dumps deprecated — identitas proses
    # ditentukan pemanggil (systemd User= / harness non-root).
    return f"""# Dibuat reconciler MicroTix — JANGAN edit manual.
prefix = "{prefix}"
sysconfdir = "{prefix}"
localstatedir = "{prefix}"
logdir = "{prefix}/log"
rundir = "{prefix}/run"
pidfile = "{prefix}/run/radiusd.pid"
name = "microtix-radius"
libdir = "{FREERADIUS_ROOT}/usr/lib/freeradius"

log {{
    destination = files
    auth = no
    auth_goodpass = no
    auth_badpass = no
}}
security {{
    max_attributes = 256
    reject_delay = 0.2s
    status_server = yes
}}
proxy_requests = no
$INCLUDE clients.conf
thread pool {{
    start_servers = 2
    max_servers = 8
    min_spare_servers = 1
    max_spare_servers = 3
    max_requests_per_server = 0
}}
modules {{
    $INCLUDE mods-enabled/expr
    $INCLUDE mods-enabled/pap
    $INCLUDE mods-enabled/sql
}}

# Server virtual dimuat dari berkas terpisah (pola upstream).
$INCLUDE sites-enabled/default
"""


def render_site(*, listen_ip: str, auth_port: int, acct_port: int) -> str:
    return f"""# Dibuat reconciler MicroTix — JANGAN edit manual.
server default {{
    listen {{
        type = auth
        ipaddr = {listen_ip}
        port = {auth_port}
    }}
    listen {{
        type = acct
        ipaddr = {listen_ip}
        port = {acct_port}
    }}
    authorize {{
        # Urutan PENTING: sql mengisi control:Cleartext-Password dari facade,
        # pap SETELAHNYA menyetel Auth-Type := PAP (pap lebih dulu = tanpa
        # known-password → Auth-Type kosong → reject).
        sql
        pap
    }}
    authenticate {{
        Auth-Type PAP {{
            pap
        }}
    }}
    preacct {{
    }}
    accounting {{
        sql
    }}
    session {{
        sql
    }}
    post-auth {{
        sql
        Post-Auth-Type REJECT {{
            sql
        }}
    }}
}}
"""


MODS_PAP = """# PAP — perbandingan password di dalam proses (cleartext dari facade).
pap {
    normalise = yes
}
"""

MODS_EXPR = """# expr — xlat string (tolower) untuk reference dispatcher accounting.
expr {
}
"""

# filter_username adalah policy bawaan dictionary daemon (-D); tidak perlu
# berkas modul terpisah.


# ---------------------------------------------------------------------------
# Bundle + validasi


def write_config(
    target: str,
    *,
    nas_rows: list[dict],
    db: dict,
    auth_port: int = 18120,
    acct_port: int = 18121,
    listen_ip: str = "127.0.0.1",
) -> list[str]:
    """Tulis bundle lengkap; berkas rahasia 0600; kembalikan nama relatif."""
    root = Path(target)
    (root / "mods-enabled").mkdir(parents=True, exist_ok=True)
    (root / "sites-enabled").mkdir(parents=True, exist_ok=True)
    (root / "log").mkdir(exist_ok=True)
    (root / "run").mkdir(exist_ok=True)

    files = {
        "radiusd.conf": render_radiusd_conf(
            prefix=str(root), listen_ip=listen_ip, auth_port=auth_port, acct_port=acct_port
        ),
        "clients.conf": render_clients_conf(nas_rows),
        "mods-enabled/expr": MODS_EXPR,
        "mods-enabled/pap": MODS_PAP,
        "mods-enabled/sql": render_sql_module(
            host=db["host"], port=db["port"], db=db["name"], login=db["login"], password=db["password"]
        ),
        "sites-enabled/default": render_site(listen_ip=listen_ip, auth_port=auth_port, acct_port=acct_port),
    }
    written: list[str] = []
    for rel, content in files.items():
        p = root / rel
        p.write_text(content)
        # Berkas pembawa rahasia wajib 0600 (clients.conf: secret NAS;
        # sql: kredensial daemon). Lainnya minimal tidak world-writable.
        if rel in ("clients.conf", "mods-enabled/sql"):
            p.chmod(0o600)
        else:
            p.chmod(0o640)
        written.append(rel)
    return written


def validate_config(config_dir: str) -> tuple[int, str]:
    """freeradius -C → (exit_code, output). 127 bila binary tidak ada."""
    if not os.path.exists(FREERADIUS_BIN):
        return 127, f"binary freeradius tidak ditemukan: {FREERADIUS_BIN}"
    env = dict(os.environ)
    ld = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = (
        f"{FREERADIUS_ROOT}/usr/lib/x86_64-linux-gnu:{FREERADIUS_ROOT}/usr/lib/freeradius:{ld}"
    )
    try:
        proc = subprocess.run(
            [FREERADIUS_BIN, "-C", "-d", config_dir, "-D", f"{FREERADIUS_ROOT}/usr/share/freeradius", "-l", "stdout"],
            capture_output=True, text=True, env=env, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return 124, "freeradius -C timeout 60s"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def nas_rows_for(nas_ip: str | None = None) -> list[dict]:
    """Baris NAS dari DB (seluruh, atau satu nasname tertentu).

    radius.nas berlaku RLS lintas tenant; reconciler adalah kode platform
    terpercaya dan memakai GUC bootstrap facade (policy facade_bootstrap,
    RADIUS.md §4) — bukan melemahkan RLS untuk peran lain.
    """
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.radius_facade', 'on', false)")  # session-level: autocommit
        if nas_ip:
            cur.execute(
                "SELECT host(nasname), shortname, secret FROM radius.nas WHERE nasname = %s::inet",
                [nas_ip],
            )
        else:
            cur.execute("SELECT host(nasname), shortname, secret FROM radius.nas ORDER BY nasname")
        rows = [
            {"nasname": r[0], "shortname": r[1], "secret": r[2]} for r in cur.fetchall()
        ]
        cur.execute("SELECT set_config('app.radius_facade', 'off', false)")
        return rows


def mark_applied(router) -> None:
    """Set applied_revision = desired (dipanggil SETELAH probe secret baru)."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            "UPDATE radius.nas SET applied_revision = desired_revision "
            "WHERE tenant_id = %s AND router_id = %s",
            [str(router.tenant_id), str(router.id)],
        )
