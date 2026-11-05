"""Kunci sesi derivat + facade session_list untuk verifikasi Simultaneous-Use.

Dua perbaikan dari temuan harness nyata (freeradius 3.2.7 + radclient):

1. ``Acct-Unique-Session-Id`` pada FreeRADIUS 3.2 adalah atribut INTERNAL
   (1051) — TIDAK pernah hadir di kawat (atribut 51 RFC 2866 adalah
   ``Acct-Link-Count``), dan binary ini tidak menghitungnya otomatis, jadi
   parameter p_acctuniqueid praktis selalu kosong dari daemon. Identitas sesi
   kini diderivasi DI DALAM facade: ``host(nas_ip) || ':' || acctsessionid``
   — tenant + router (NAS sumber) + session identity sesuai RADIUS.md §8,
   bukan Acct-Session-Id global (dua router tenant sama tak bisa saling
   menimpa sesi lewat ON CONFLICT).

2. rlm_sql 3.x ``mod_checksimul``: bila count >= Simultaneous-Use, ia RESET
   ``request->simul_count = 0`` lalu hanya menghitung ulang sesi yang
   dikembalikan ``simul_verify_query`` dan dikonfirmasi hidup oleh
   ``rad_check_ts`` (klien bertipe "other" → percaya data accounting).
   Tanpa baris sesi nyata dari verify query, jumlah selalu 0 → Simultaneous-
   Use tidak pernah ditegakkan. Facade baru ``radius.session_list`` mengembalikan
   sesi terbuka tenant (8 kolom persis ekspektasi rlm_sql: radacctid,
   acctsessionid, username, nasipaddress, nasportid, framedipaddress,
   callingstationid, framedprotocol).
"""
import os

from django.db import migrations

FUNCTIONS_SQL = r"""
-- Identitas sesi: unik-id eksplisit (mis. proxy unlang) atau derivasi
-- NAS+session-id (§8). Signature tidak berubah; hanya body.
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
    v_key text;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    v_key := COALESCE(NULLIF(p_acctuniqueid, ''), host(p_nas_ip) || ':' || p_acctsessionid);

    IF p_acctstatustype = 'Start' THEN
        INSERT INTO radius.radacct (
            tenant_id, router_id, acctsessionid, acctuniqueid, username,
            nasipaddress, acctstarttime, acctupdatetime,
            acctinputoctets, acctoutputoctets, acctsessiontime,
            acctterminatecause, framedipaddress, acctdelaytime
        ) VALUES (
            v_tenant, v_router, p_acctsessionid, v_key, p_username,
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
        WHERE tenant_id = v_tenant AND acctuniqueid = v_key AND acctstoptime IS NULL;
        IF NOT FOUND THEN
            IF EXISTS (SELECT 1 FROM radius.radacct
                        WHERE tenant_id = v_tenant AND acctuniqueid = v_key) THEN
                -- Interim terlambat setelah Stop: perbarui counter baris
                -- tertutup (monotonik) TANPA membuka kembali sesi (§8).
                UPDATE radius.radacct SET
                    acctupdatetime   = now(),
                    acctinputoctets  = GREATEST(COALESCE(acctinputoctets, 0), p_inputoctets),
                    acctoutputoctets = GREATEST(COALESCE(acctoutputoctets, 0), p_outputoctets),
                    acctsessiontime  = GREATEST(COALESCE(acctsessiontime, 0), p_acctsessiontime)
                WHERE tenant_id = v_tenant AND acctuniqueid = v_key;
            ELSE
                -- Interim tanpa Start (out-of-order hulu) → catat sesi terbuka.
                INSERT INTO radius.radacct (
                    tenant_id, router_id, acctsessionid, acctuniqueid, username,
                    nasipaddress, acctstarttime, acctupdatetime,
                    acctinputoctets, acctoutputoctets, acctsessiontime,
                    framedipaddress, acctdelaytime
                ) VALUES (
                    v_tenant, v_router, p_acctsessionid, v_key, p_username,
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
        WHERE tenant_id = v_tenant AND acctuniqueid = v_key AND acctstoptime IS NULL;
        IF NOT FOUND THEN
            IF EXISTS (SELECT 1 FROM radius.radacct
                        WHERE tenant_id = v_tenant AND acctuniqueid = v_key) THEN
                RETURN;  -- retransmit Stop untuk sesi sudah tertutup → idempoten
            END IF;
            -- Stop tanpa Start tercatat → sesi singkat yang sudah tertutup.
            INSERT INTO radius.radacct (
                tenant_id, router_id, acctsessionid, acctuniqueid, username,
                nasipaddress, acctstarttime, acctupdatetime, acctstoptime,
                acctsessiontime, acctinputoctets, acctoutputoctets,
                acctterminatecause, framedipaddress, acctdelaytime
            ) VALUES (
                v_tenant, v_router, p_acctsessionid, v_key, p_username,
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

-- Sesi terbuka untuk simul_verify_query rlm_sql (kolom persis ekspektasi
-- mod_checksimul: 8 kolom; nasipaddress dipakai rad_check_ts mencari klien).
CREATE OR REPLACE FUNCTION radius.session_list(p_nas_ip inet, p_username text)
RETURNS TABLE(
    radacctid bigint, acctsessionid text, username text, nasipaddress text,
    nasportid text, framedipaddress text, callingstationid text, framedprotocol text
)
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
        SELECT a.radacctid, a.acctsessionid, a.username, host(a.nasipaddress),
               a.nasportid, host(a.framedipaddress), a.callingstationid, a.framedprotocol
          FROM radius.radacct a
         WHERE a.tenant_id = v_tenant AND a.username = p_username AND a.acctstoptime IS NULL
         ORDER BY a.radacctid;
END
$fn$;
"""

REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS radius.session_list(inet, text);
-- Kembalikan accounting versi 0002 (kunci = parameter apa adanya).
CREATE OR REPLACE FUNCTION radius.accounting(
    p_nas_ip inet, p_acctuniqueid text, p_acctsessionid text, p_username text,
    p_acctstatustype text, p_acctdelaytime int, p_inputoctets bigint,
    p_outputoctets bigint, p_acctsessiontime int, p_acctterminatecause text, p_framedip inet
)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = radius, public SET row_security = on
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
            p_nas_ip, now(), now(), p_inputoctets, p_outputoctets, p_acctsessiontime,
            '', p_framedip, p_acctdelaytime
        )
        ON CONFLICT (tenant_id, acctuniqueid) DO UPDATE
            SET acctupdatetime = now();
    ELSIF p_acctstatustype IN ('Interim-Update', 'Alive') THEN
        UPDATE radius.radacct SET acctupdatetime = now()
         WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid;
    ELSIF p_acctstatustype = 'Stop' THEN
        UPDATE radius.radacct SET acctstoptime = now(), acctupdatetime = now()
         WHERE tenant_id = v_tenant AND acctuniqueid = p_acctuniqueid AND acctstoptime IS NULL;
    END IF;
END
$fn$;
"""

_FUNCTIONS = [
    "radius.accounting(inet, text, text, text, text, int, bigint, bigint, int, text, inet)",
    "radius.session_list(inet, text)",
]


def _grants_sql() -> str:
    """EXECUTE ulang untuk peran tepercaya (pola migrasi 0002/0005)."""
    stmts = [f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC;" for fn in _FUNCTIONS]
    do_block = [
        "DO $grant$",
        "BEGIN",
        "  EXECUTE format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO %I', current_user);",
        "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mtx_radius') THEN",
        "    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA radius TO mtx_radius;",
        "  END IF;",
    ]
    if os.environ.get("MT_ENV", "production") in ("dev", "test"):
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
        ("radius", "0005_facade_row_shape_rlm_sql"),
    ]

    operations = [
        migrations.RunSQL(FUNCTIONS_SQL, reverse_sql=REVERSE_SQL),
        migrations.RunSQL(_grants_sql(), reverse_sql=migrations.RunSQL.noop),
    ]
