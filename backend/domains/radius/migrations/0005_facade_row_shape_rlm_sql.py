"""Ubah bentuk baris facade authorize → kolom posisi rlm_sql 3.x.

rlm_sql FreeRADIUS 3.x membaca hasil authorize_check_query/authorize_reply_query
berdasarkan POSISI kolom: id, username, attribute, value, op (lima kolom —
diverifikasi dengan ``freeradius -X`` pada binary 3.2.7 nyata: bentuk 4 kolom
diinterpretasi salah sebagai username/attribute bergeser). Facade diubah
mengembalikan lima kolom itu; tipe kembalian berubah → DROP + CREATE (PostgreSQL
menolak mengubah tipe kembalian lewat CREATE OR REPLACE).

Isi tetap sesuai RADIUS.md §4: satu pemanggilan mengikat NAS terverifikasi →
tenant → GUC transaction-local → query scope tenant pada transaksi sama.
"""
import os

from django.db import migrations

FUNCTIONS_SQL = r"""
DROP FUNCTION IF EXISTS radius.authorize_reply(inet, text);
DROP FUNCTION IF EXISTS radius.authorize_check(inet, text);

CREATE OR REPLACE FUNCTION radius.authorize_check(p_nas_ip inet, p_username text)
RETURNS TABLE(id bigint, username text, attribute text, value text, op text)
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
        SELECT c.id, c.username, c.attribute, c.value, c.op
          FROM radius.radcheck c
         WHERE c.tenant_id = v_tenant AND c.username = p_username
         ORDER BY c.id;
END
$fn$;

CREATE OR REPLACE FUNCTION radius.authorize_reply(p_nas_ip inet, p_username text)
RETURNS TABLE(id bigint, username text, attribute text, value text, op text)
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
        SELECT r.id, r.username, r.attribute, r.value, r.op
          FROM radius.radreply r
         WHERE r.tenant_id = v_tenant AND r.username = p_username
         ORDER BY r.id;
END
$fn$;
"""

REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS radius.authorize_reply(inet, text);
DROP FUNCTION IF EXISTS radius.authorize_check(inet, text);
CREATE OR REPLACE FUNCTION radius.authorize_check(p_nas_ip inet, p_username text)
RETURNS TABLE(id bigint, attribute text, value text, op text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = radius, public SET row_security = on
AS $fn$
DECLARE v_tenant uuid; v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    RETURN QUERY SELECT c.id, c.attribute, c.value, c.op
      FROM radius.radcheck c WHERE c.tenant_id = v_tenant AND c.username = p_username ORDER BY c.id;
END
$fn$;
CREATE OR REPLACE FUNCTION radius.authorize_reply(p_nas_ip inet, p_username text)
RETURNS TABLE(id bigint, attribute text, value text, op text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = radius, public SET row_security = on
AS $fn$
DECLARE v_tenant uuid; v_router uuid;
BEGIN
    SELECT t.tenant, t.router INTO v_tenant, v_router FROM radius._nas_tenant(p_nas_ip) t;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    RETURN QUERY SELECT r.id, r.attribute, r.value, r.op
      FROM radius.radreply r WHERE r.tenant_id = v_tenant AND r.username = p_username ORDER BY r.id;
END
$fn$;
"""

_RECREATED = [
    "radius.authorize_check(inet, text)",
    "radius.authorize_reply(inet, text)",
]


def _grants_sql() -> str:
    """EXECUTE ulang untuk peran tepercaya (pola migrasi 0002)."""
    stmts = [f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC;" for fn in _RECREATED]
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
        ("radius", "0004_cutover_run_rls"),
    ]

    operations = [
        migrations.RunSQL(FUNCTIONS_SQL, reverse_sql=REVERSE_SQL),
        migrations.RunSQL(_grants_sql(), reverse_sql=migrations.RunSQL.noop),
    ]
