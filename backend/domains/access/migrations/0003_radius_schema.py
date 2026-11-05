"""Skema radius.* — proyeksi FreeRADIUS + facade terpercaya (RADIUS.md §3–§4).

Tabel proyeksi (nas/radcheck/radreply/radusergroup/radacct/radpostauth)
memakai RLS tenant yang sama seperti tabel aplikasi; hanya service layer
(dalam tenant_scope) yang menulis. Facade SQL dipakai role daemon RADIUS
(EXECUTE-only): satu pemanggilan mengikat NAS terverifikasi → menetapkan
konteks transaction-local → query scoped; User-Name/NAS-IP dari paket tidak
pernah memilih tenant (RAD-03).
"""
from django.db import migrations

RADIUS_TABLES = ("nas", "radcheck", "radreply", "radusergroup", "radgroupreply", "radacct", "radpostauth")

CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS radius"

CREATE_TABLES = """
-- Klien NAS per router (proyeksi dari access_nas; secret per router unik).
CREATE TABLE IF NOT EXISTS radius.nas (
    id BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    router_id uuid NOT NULL,
    nasname text NOT NULL UNIQUE,
    shortname text NOT NULL,
    secret text NOT NULL,
    type text NOT NULL DEFAULT 'other',
    servers text,
    community text,
    description text
);
-- Check/reply per akun (username case-sensitive; satu akun banyak baris).
CREATE TABLE IF NOT EXISTS radius.radcheck (
    id BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    account_id uuid NOT NULL,
    username text NOT NULL,
    attribute text NOT NULL,
    scope text NOT NULL DEFAULT 'check',
    ordinal int NOT NULL DEFAULT 0,
    op text NOT NULL DEFAULT ':=',
    value text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS radius.radreply (
    id BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    account_id uuid NOT NULL,
    username text NOT NULL,
    attribute text NOT NULL,
    scope text NOT NULL DEFAULT 'reply',
    ordinal int NOT NULL DEFAULT 0,
    op text NOT NULL DEFAULT '=',
    value text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS radius.radusergroup (
    id BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    username text NOT NULL,
    groupname text NOT NULL,
    priority int NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS radius.radgroupreply (
    id BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    groupname text NOT NULL,
    attribute text NOT NULL,
    op text NOT NULL DEFAULT '=',
    value text NOT NULL DEFAULT '',
    router_id uuid
);
-- Accounting (skema standar FreeRADIUS + kolom tenant/router/service; RAD-02).
CREATE TABLE IF NOT EXISTS radius.radacct (
    radacctid BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    router_id uuid,
    service_id uuid,
    acctsessionid text NOT NULL,
    acctuniqueid text NOT NULL UNIQUE,
    username text NOT NULL DEFAULT '',
    realm text,
    nasipaddress inet NOT NULL,
    nasportid text,
    nasporttype text,
    acctstarttime timestamptz,
    acctupdatetime timestamptz,
    acctstoptime timestamptz,
    acctinterval bigint,
    acctsessiontime bigint,
    acctauthentic text,
    connectinfo_start text,
    connectinfo_stop text,
    acctinputoctets bigint,
    acctoutputoctets bigint,
    calledstationid text,
    callingstationid text,
    acctterminatecause text,
    servicetype text,
    framedprotocol text,
    framedipaddress inet,
    acctdelaytime bigint DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_radacct_tenant_user ON radius.radacct (tenant_id, username, acctstarttime);
CREATE INDEX IF NOT EXISTS ix_radacct_session ON radius.radacct (acctuniqueid);
-- Post-auth (log hasil autentikasi tanpa password; RAD-13: retensi 30 hari).
CREATE TABLE IF NOT EXISTS radius.radpostauth (
    id BIGSERIAL PRIMARY KEY,
    tenant_id uuid NOT NULL,
    username text NOT NULL,
    pass text NOT NULL DEFAULT '',
    reply text NOT NULL DEFAULT '',
    authdate timestamptz NOT NULL DEFAULT now(),
    nas_ip inet
);
CREATE INDEX IF NOT EXISTS ix_radpostauth_tenant_date ON radius.radpostauth (tenant_id, authdate);
"""

RLS_POLICIES = """
-- RLS tenant identik dengan tabel aplikasi (konteks app.tenant_id).
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['nas','radcheck','radreply','radusergroup','radgroupreply','radacct','radpostauth'] LOOP
    EXECUTE format('ALTER TABLE radius.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE radius.%I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON radius.%I', t);
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON radius.%I USING (tenant_id = NULLIF(current_setting(''app.tenant_id'', true), '''')::uuid)',
      t);
  END LOOP;
END $$;
-- Bootstrap lookup NAS untuk facade terpercaya: metadata klien minimum
-- (RAD-03 §4). GUC app.radius_facade hanya disetel oleh facade_lookup_nas.
DROP POLICY IF EXISTS nas_facade ON radius.nas;
CREATE POLICY nas_facade ON radius.nas FOR SELECT
  USING (current_setting('app.radius_facade', true) = '1');
-- read_clients daemon terpercaya (rlm_sql) membaca metadata NAS langsung.
DROP POLICY IF EXISTS nas_bootstrap ON radius.nas;
CREATE POLICY nas_bootstrap ON radius.nas FOR SELECT
  USING (current_user = 'radius_svc');
"""

FACADE = """
-- Facade EXECUTE-only untuk daemon RADIUS (RAD-03 §4):
-- 1) NAS ditemukan dari alamat sumber terverifikasi (bukan payload).
-- 2) Konteks tenant transaction-local ditetapkan pada pemanggilan sama.
-- 3) Query berjalan scoped; role pemanggil tidak memegang DML tabel.
-- Semua tabel lintas skema memakai nama terkualifikasi penuh (search_path
-- minimal radius,pg_catalog — tidak ada objek yang bisa dibayangi).
-- facade_lookup_nas: menetapkan GUC sempit (app.radius_facade untuk
-- radius.nas; app.platform_service untuk network_router — kebijakan yang
-- sama dengan jalur layanan) LALU melakukan bootstrap lookup; kedua GUC
-- transaction-local dan hanya disetel kode server/facade.
CREATE OR REPLACE FUNCTION radius.facade_lookup_nas(p_nas text)
RETURNS TABLE(tenant_id uuid, router_id uuid, nasname text, secret text)
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = radius, pg_catalog
AS $$
BEGIN
    PERFORM set_config('app.radius_facade', '1', true);
    PERFORM set_config('app.platform_service', '1', true);
    RETURN QUERY
    SELECT n.tenant_id, n.router_id, n.nasname, n.secret
    FROM radius.nas n
    WHERE n.nasname = p_nas
      AND EXISTS (SELECT 1 FROM public.network_router r
                  WHERE r.id = n.router_id AND r.released_at IS NULL);
END $$;

CREATE OR REPLACE FUNCTION radius.facade_check(p_nas text, p_username text)
RETURNS TABLE(attribute text, op text, value text)
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = radius, pg_catalog
AS $$
DECLARE
    v_tenant uuid;
BEGIN
    -- Nasname (IP sumber tunnel) adalah satu-satunya input yang mengikat tenant.
    SELECT f.tenant_id INTO v_tenant FROM radius.facade_lookup_nas(p_nas) f;
    IF v_tenant IS NULL THEN
        RETURN;  -- NAS tak dikenal: tanpa baris (secure discard; tanpa Accept).
    END IF;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    RETURN QUERY
    SELECT c.attribute, c.op, c.value
    FROM radius.radcheck c
    WHERE c.username = p_username
    ORDER BY c.ordinal, c.id;
END $$;

CREATE OR REPLACE FUNCTION radius.facade_reply(p_nas text, p_username text)
RETURNS TABLE(attribute text, op text, value text)
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = radius, pg_catalog
AS $$
DECLARE
    v_tenant uuid;
BEGIN
    SELECT f.tenant_id INTO v_tenant FROM radius.facade_lookup_nas(p_nas) f;
    IF v_tenant IS NULL THEN
        RETURN;
    END IF;
    PERFORM set_config('app.tenant_id', v_tenant::text, true);
    RETURN QUERY
    SELECT r.attribute, r.op, r.value
    FROM radius.radreply r
    WHERE r.username = p_username
    ORDER BY r.ordinal, r.id;
END $$;
"""

DROP_FACADE = """
DROP FUNCTION IF EXISTS radius.facade_reply(text, text);
DROP FUNCTION IF EXISTS radius.facade_check(text, text);
DROP FUNCTION IF EXISTS radius.facade_lookup_nas(text);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0002_rls_composite"),
    ]

    operations = [
        migrations.RunSQL(CREATE_SCHEMA, reverse_sql="DROP SCHEMA IF EXISTS radius CASCADE"),
        migrations.RunSQL(CREATE_TABLES, reverse_sql="; ".join(f"DROP TABLE IF EXISTS radius.{t}" for t in RADIUS_TABLES)),
        migrations.RunSQL(RLS_POLICIES, reverse_sql="; ".join(f"DROP POLICY IF EXISTS tenant_isolation ON radius.{t}" for t in RADIUS_TABLES)),
        migrations.RunSQL(FACADE, reverse_sql=DROP_FACADE),
    ]
