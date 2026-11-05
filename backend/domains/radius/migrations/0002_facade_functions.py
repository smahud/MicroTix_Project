"""Facade SQL RADIUS (RADIUS.md §4) — satu panggilan mengikat NAS→tenant→GUC.

Desain (lihat docstring 0001 untuk policy bootstrap radius.nas):
- Fungsi SECURITY DEFINER (owner = peran migrasi; bukan BYPASSRLS) dengan
  ``SET search_path = radius, public`` + ``SET row_security = on``. Semua
  tabel radius memakai FORCE RLS sehingga owner fungsi tetap tunduk policy;
  fungsi memanggil set_config('app.tenant_id', …, true) SEBELUM query
  tenant-scoped pada transaksi yang sama (§4: konteks transaction-local,
  bukan SET terpisah pada pool).
- Resolusi nas: radius._nas_tenant mencari baris nas berdasarkan alamat
  sumber paket (%{Packet-Src-IP-Address}) — atribut payload (NAS-IP-Address
  dsb.) tidak berwenang memilih tenant. NAS tak dikenal → SQLSTATE P0001
  'unknown_nas' (FreeRADIUS memperlakukan galat SQL sebagai kegagalan query
  → tidak ada Accept).
- Role daemon mtx_radius hanya memerlukan EXECUTE (grant di bawah, plus
  command setup_radius). Aplikasi biasa (mtx_app) TIDAK diberi EXECUTE pada
  production; dev/test diberi agar suite pytest (koneksi sebagai mtx_app)
  dapat menguji facade secara langsung — keputusan eksplisit ini mengikuti
  spesifikasi slice (§4 dijalankan di jalur tepercaya platform).
"""
import os

from django.db import migrations

FUNCTIONS_SQL = r"""
-- Bantu resolusi nas→(tenant,router); gate GUC app.radius_facade untuk
-- policy facade_bootstrap pada radius.nas (lihat 0001).
CREATE OR REPLACE FUNCTION radius._nas_tenant(p_nas_ip inet)
RETURNS TABLE(tenant uuid, router uuid)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
BEGIN
    PERFORM set_config('app.radius_facade', 'on', true);
    SELECT n.tenant_id, n.router_id INTO v_tenant, v_router
      FROM radius.nas n
     WHERE n.nasname = p_nas_ip
     ORDER BY n.id
     LIMIT 1;
    PERFORM set_config('app.radius_facade', 'off', true);
    IF v_tenant IS NULL THEN
        RAISE EXCEPTION 'unknown_nas' USING ERRCODE = 'P0001';
    END IF;
    RETURN QUERY SELECT v_tenant, v_router;
END
$fn$;

-- Atribut kontrol (kolom id,attribute,value,op — urutan default rlm_sql).
CREATE OR REPLACE FUNCTION radius.authorize_check(p_nas_ip inet, p_username text)
RETURNS TABLE(id bigint, attribute text, value text, op text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    RETURN QUERY
        SELECT c.id, c.attribute, c.value, c.op
          FROM radius.radcheck c
         WHERE c.tenant_id = v_tenant AND c.username = p_username
         ORDER BY c.id;
END
$fn$;

-- Atribut reply NAS (rate-limit, interim, session-timeout, dst.).
CREATE OR REPLACE FUNCTION radius.authorize_reply(p_nas_ip inet, p_username text)
RETURNS TABLE(id bigint, attribute text, value text, op text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    RETURN QUERY
        SELECT r.id, r.attribute, r.value, r.op
          FROM radius.radreply r
         WHERE r.tenant_id = v_tenant AND r.username = p_username
         ORDER BY r.id;
END
$fn$;

-- Log hasil autentikasi (tanpa password — RADIUS.md §12).
CREATE OR REPLACE FUNCTION radius.post_auth(p_nas_ip inet, p_username text, p_reply text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    INSERT INTO radius.radpostauth (tenant_id, username, reply, authdate, nas_ip)
    VALUES (v_tenant, p_username, COALESCE(p_reply, ''), now(), p_nas_ip);
END
$fn$;

-- Accounting Start/Interim/Stop — dedup retransmit (tenant, acctuniqueid),
-- counter monotonik (GREATEST), Stop tidak dibuka kembali oleh Start lama.
CREATE OR REPLACE FUNCTION radius.accounting(
    p_nas_ip inet,
    p_acctuniqueid text,
    p_acctsessionid text,
    p_username text,
    p_acctstatustype text,
    p_acctdelaytime int,
    p_inputoctets bigint,
    p_outputoctets bigint,
    p_acctsessiontime int,
    p_acctterminatecause text,
    p_framedip inet
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);

    IF p_acctstatustype = 'Start' THEN
        INSERT INTO radius.radacct (
            tenant_id, router_id, acctsessionid, acctuniqueid, username,
            nasipaddress, acctstarttime, acctupdatetime,
            acctinputoctets, acctoutputoctets, acctsessiontime,
            acctterminatecause, framedipaddress, acctdelaytime
        ) VALUES (
            v_tenant, v_router, p_acctsessionid, p_acctuniqueid, p_username,
            p_nas_ip, now(), now(),
            p_inputoctets, p_outputoctets, p_acctsessiontime,
            '', p_framedip, p_acctdelaytime
        )
        ON CONFLICT (tenant_id, acctuniqueid) DO UPDATE
            SET acctupdatetime = now(),
                acctinputoctets  = GREATEST(COALESCE(radius.radacct.acctinputoctets, 0), EXCLUDED.acctinputoctets),
                acctoutputoctets = GREATEST(COALESCE(radius.radacct.acctoutputoctets, 0), EXCLUDED.acctoutputoctets),
                acctsessiontime  = GREATEST(COALESCE(radius.radacct.acctsessiontime, 0), EXCLUDED.acctsessiontime)
            WHERE radius.radacct.acctstoptime IS NULL;

    ELSIF p_acctstatustype IN ('Interim-Update', 'Alive') THEN
        UPDATE radius.radacct SET
            acctupdatetime    = now(),
            acctinputoctets   = GREATEST(COALESCE(acctinputoctets, 0), p_inputoctets),
            acctoutputoctets  = GREATEST(COALESCE(acctoutputoctets, 0), p_outputoctets),
            acctsessiontime   = GREATEST(COALESCE(acctsessiontime, 0), p_acctsessiontime),
            framedipaddress   = COALESCE(p_framedip, framedipaddress),
            acctdelaytime     = p_acctdelaytime
        WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid AND acctstoptime IS NULL;
        IF NOT FOUND THEN
            IF EXISTS (SELECT 1 FROM radius.radacct
                        WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid) THEN
                -- Interim terlambat setelah Stop: perbarui counter baris
                -- tertutup (monotonik) TANPA membuka kembali sesi (§8).
                UPDATE radius.radacct SET
                    acctupdatetime   = now(),
                    acctinputoctets  = GREATEST(COALESCE(acctinputoctets, 0), p_inputoctets),
                    acctoutputoctets = GREATEST(COALESCE(acctoutputoctets, 0), p_outputoctets),
                    acctsessiontime  = GREATEST(COALESCE(acctsessiontime, 0), p_acctsessiontime)
                WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid;
            ELSE
                -- Interim tanpa Start (out-of-order hulu) → catat sesi terbuka.
                INSERT INTO radius.radacct (
                    tenant_id, router_id, acctsessionid, acctuniqueid, username,
                    nasipaddress, acctstarttime, acctupdatetime,
                    acctinputoctets, acctoutputoctets, acctsessiontime,
                    framedipaddress, acctdelaytime
                ) VALUES (
                    v_tenant, v_router, p_acctsessionid, p_acctuniqueid, p_username,
                    p_nas_ip, now(), now(),
                    p_inputoctets, p_outputoctets, p_acctsessiontime,
                    p_framedip, p_acctdelaytime
                );
            END IF;
        END IF;

    ELSIF p_acctstatustype = 'Stop' THEN
        UPDATE radius.radacct SET
            acctstoptime      = now(),
            acctupdatetime    = now(),
            acctterminatecause = COALESCE(NULLIF(p_acctterminatecause, ''), NULLIF(acctterminatecause, ''), 'User-Request'),
            acctinputoctets   = GREATEST(COALESCE(acctinputoctets, 0), p_inputoctets),
            acctoutputoctets  = GREATEST(COALESCE(acctoutputoctets, 0), p_outputoctets),
            acctsessiontime   = GREATEST(COALESCE(acctsessiontime, 0), p_acctsessiontime),
            framedipaddress   = COALESCE(p_framedip, framedipaddress)
        WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid AND acctstoptime IS NULL;
        IF NOT FOUND THEN
            IF EXISTS (SELECT 1 FROM radius.radacct
                        WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid) THEN
                RETURN;  -- retransmit Stop untuk sesi sudah tertutup → idempoten
            END IF;
            -- Stop tanpa Start tercatat → sesi singkat yang sudah tertutup.
            INSERT INTO radius.radacct (
                tenant_id, router_id, acctsessionid, acctuniqueid, username,
                nasipaddress, acctstarttime, acctupdatetime, acctstoptime,
                acctsessiontime, acctinputoctets, acctoutputoctets,
                acctterminatecause, framedipaddress, acctdelaytime
            ) VALUES (
                v_tenant, v_router, p_acctsessionid, p_acctuniqueid, p_username,
                p_nas_ip,
                now() - make_interval(secs => COALESCE(p_acctsessiontime, 0)),
                now(), now(),
                p_acctsessiontime, p_inputoctets, p_outputoctets,
                COALESCE(NULLIF(p_acctterminatecause, ''), 'User-Request'),
                p_framedip, p_acctdelaytime
            );
        END IF;
    ELSE
        RAISE EXCEPTION 'unknown_acct_status_type' USING ERRCODE = 'P0001';
    END IF;
END
$fn$;

-- Accounting On/Off (NAS reboot): tutup sesi terbuka milik NAS tersebut.
CREATE OR REPLACE FUNCTION radius.accounting_onoff(p_nas_ip inet, p_status text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    UPDATE radius.radacct SET
        acctstoptime = now(),
        acctupdatetime = now(),
        acctterminatecause = 'NAS-Reboot'
    WHERE tenant_id = v_tenant
      AND router_id = v_router
      AND acctstoptime IS NULL;
END
$fn$;

-- Hitung sesi terbuka (Simultaneous-Use) — scope tenant dari NAS sumber.
CREATE OR REPLACE FUNCTION radius.session_count(p_nas_ip inet, p_username text)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = radius, public
SET row_security = on
AS $fn$
DECLARE
    v_tenant uuid;
    v_router uuid;
    v_count bigint;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    SELECT COUNT(*) INTO v_count
      FROM radius.radacct
     WHERE tenant_id = v_tenant AND username = p_username AND acctstoptime IS NULL;
    RETURN v_count;
END
$fn$;
"""

REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS radius.session_count(inet, text);
DROP FUNCTION IF EXISTS radius.accounting_onoff(inet, text);
DROP FUNCTION IF EXISTS radius.accounting(inet, text, text, text, text, int, bigint, bigint, int, text, inet);
DROP FUNCTION IF EXISTS radius.post_auth(inet, text, text);
DROP FUNCTION IF EXISTS radius.authorize_reply(inet, text);
DROP FUNCTION IF EXISTS radius.authorize_check(inet, text);
DROP FUNCTION IF EXISTS radius._nas_tenant(inet);
"""

_FUNCTIONS = [
    "radius._nas_tenant(inet)",
    "radius.authorize_check(inet, text)",
    "radius.authorize_reply(inet, text)",
    "radius.post_auth(inet, text, text)",
    "radius.accounting(inet, text, text, text, text, int, bigint, bigint, int, text, inet)",
    "radius.accounting_onoff(inet, text)",
    "radius.session_count(inet, text)",
]


def _grants_sql() -> str:
    """EXECUTE hanya untuk peran tepercaya (§4): executor migrasi + daemon.

    Dev/test juga memberi mtx_app/mtx_migrator agar suite pytest dapat
    memanggil facade langsung; production (MT_ENV=production) tidak.
    """
    stmts = []
    for fn in _FUNCTIONS:
        stmts.append(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC;")
    roles = ["current_user", "mtx_radius"]
    env = os.environ.get("MT_ENV", "production")
    if env in ("dev", "test"):
        roles += ["mtx_app", "mtx_migrator"]
    do_block = ["DO $grant$", "BEGIN"]
    for role in roles:
        if role == "current_user":
            do_block.append("  EXECUTE format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO %I', current_user);")
            break
    do_block += [
        "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mtx_radius') THEN",
        "    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO mtx_radius;",
        "  END IF;",
    ]
    if env in ("dev", "test"):
        do_block += [
            "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mtx_app') THEN",
            "    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO mtx_app;",
            "  END IF;",
            "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mtx_migrator') THEN",
            "    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO mtx_migrator;",
            "  END IF;",
        ]
    do_block += ["END", "$grant$;"]
    return "\n".join(stmts + do_block)


class Migration(migrations.Migration):
    dependencies = [
        ("radius", "0001_radius_schema"),
    ]

    operations = [
        migrations.RunSQL(FUNCTIONS_SQL, reverse_sql=REVERSE_SQL),
        migrations.RunSQL(_grants_sql(), reverse_sql=migrations.RunSQL.noop),
    ]
