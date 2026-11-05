"""Skema radius: tabel proyeksi FreeRADIUS 3.2 (RADIUS.md §3) + RLS tenant.

Tabel dibuat dengan SQL mentah pada skema non-default ``radius`` (pembantu
migration_sql.py hanya public-schema). Semua tabel memakai RLS
tenant_isolation GUC app.tenant_id + FORCE — akses aplikasi selalu
ter-scope; role daemon (mtx_radius) hanya memanggil facade (migrasi 0002).

Catatan kejujuran desain: radius.nas juga memasang policy tambahan
``facade_bootstrap`` (SELECT, GUC-gate app.radius_facade='on') — diperlukan
oleh SECURITY DEFINER facade untuk resolusi nas→tenant SEBELUM konteks
tenant diketahui (RADIUS.md §4 "bootstrap lookup metadata minimum").
Sekuat apa pun gatenya, peran yang bisa SET GUC bisa membukanya; kepercayaan
setara dengan daemon RADIUS sendiri (trusted computing base §4) dan daemon
memang sudah memegang seluruh secret klien via clients.conf. Tabel data
(radcheck/radacct/…) TIDAK memasang policy bootstrap apa pun.
"""
from django.db import migrations

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS radius;
"""

TABLES_SQL = """
CREATE TABLE radius.nas (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    router_id uuid NOT NULL REFERENCES network_router (id) ON DELETE CASCADE,
    nasname inet NOT NULL,
    shortname text NOT NULL DEFAULT '',
    secret text NOT NULL,
    type text NOT NULL DEFAULT 'other',
    applied_revision int NOT NULL DEFAULT 0,
    desired_revision int NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_radius_nas_tenant_nasname UNIQUE (tenant_id, nasname)
);

CREATE TABLE radius.radcheck (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES customers_access_account (id) ON DELETE CASCADE,
    username text NOT NULL,
    attribute text NOT NULL,
    scope text NOT NULL DEFAULT '',
    ordinal int NOT NULL DEFAULT 0,
    op text NOT NULL DEFAULT ':=',
    value text NOT NULL DEFAULT '',
    CONSTRAINT uq_radius_radcheck UNIQUE (tenant_id, account_id, attribute, scope, ordinal)
);
CREATE INDEX ix_radius_radcheck_tenant_user ON radius.radcheck (tenant_id, username);

CREATE TABLE radius.radreply (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES customers_access_account (id) ON DELETE CASCADE,
    username text NOT NULL,
    attribute text NOT NULL,
    scope text NOT NULL DEFAULT '',
    ordinal int NOT NULL DEFAULT 0,
    op text NOT NULL DEFAULT '=',
    value text NOT NULL DEFAULT '',
    CONSTRAINT uq_radius_radreply UNIQUE (tenant_id, account_id, attribute, scope, ordinal)
);
CREATE INDEX ix_radius_radreply_tenant_user ON radius.radreply (tenant_id, username);

CREATE TABLE radius.radgroupreply (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    groupname text NOT NULL,
    attribute text NOT NULL,
    op text NOT NULL DEFAULT '=',
    value text NOT NULL DEFAULT '',
    router_id uuid REFERENCES network_router (id) ON DELETE CASCADE
);
CREATE INDEX ix_radius_radgroupreply_tenant_group ON radius.radgroupreply (tenant_id, groupname);

CREATE TABLE radius.radusergroup (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    username text NOT NULL,
    groupname text NOT NULL,
    priority int NOT NULL DEFAULT 1,
    CONSTRAINT uq_radius_radusergroup UNIQUE (tenant_id, username, groupname)
);

CREATE TABLE radius.radacct (
    radacctid bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    router_id uuid REFERENCES network_router (id) ON DELETE SET NULL,
    service_id uuid REFERENCES customers_service (id) ON DELETE SET NULL,
    acctsessionid text NOT NULL DEFAULT '',
    acctuniqueid text NOT NULL,
    username text NOT NULL DEFAULT '',
    nasipaddress inet,
    nasportid text NOT NULL DEFAULT '',
    acctstarttime timestamptz,
    acctupdatetime timestamptz,
    acctstoptime timestamptz,
    acctsessiontime int,
    acctinputoctets bigint,
    acctoutputoctets bigint,
    calledstationid text NOT NULL DEFAULT '',
    callingstationid text NOT NULL DEFAULT '',
    framedipaddress inet,
    acctterminatecause text NOT NULL DEFAULT '',
    servicetype text NOT NULL DEFAULT '',
    framedprotocol text NOT NULL DEFAULT '',
    acctdelaytime int,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_radius_radacct_tenant_acctuniqueid UNIQUE (tenant_id, acctuniqueid)
);
CREATE INDEX ix_radius_radacct_tenant_user_start ON radius.radacct (tenant_id, username, acctstarttime);
CREATE INDEX ix_radius_radacct_tenant_open ON radius.radacct (tenant_id, username, acctstoptime);

CREATE TABLE radius.radpostauth (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenancy_tenant (id) ON DELETE CASCADE,
    username text NOT NULL DEFAULT '',
    reply text NOT NULL DEFAULT '',
    authdate timestamptz NOT NULL DEFAULT now(),
    nas_ip inet
);
CREATE INDEX ix_radius_radpostauth_tenant_time ON radius.radpostauth (tenant_id, authdate);
"""

RLS_SQL = """
ALTER TABLE radius.nas ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.nas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.nas;
CREATE POLICY tenant_isolation ON radius.nas
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
-- Bootstrap lookup facade (lihat docstring modul): SELECT ter-GUC-gate.
DROP POLICY IF EXISTS facade_bootstrap ON radius.nas;
CREATE POLICY facade_bootstrap ON radius.nas FOR SELECT
    USING (current_setting('app.radius_facade', true) = 'on');

ALTER TABLE radius.radcheck ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.radcheck FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.radcheck;
CREATE POLICY tenant_isolation ON radius.radcheck
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE radius.radreply ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.radreply FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.radreply;
CREATE POLICY tenant_isolation ON radius.radreply
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE radius.radgroupreply ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.radgroupreply FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.radgroupreply;
CREATE POLICY tenant_isolation ON radius.radgroupreply
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE radius.radusergroup ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.radusergroup FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.radusergroup;
CREATE POLICY tenant_isolation ON radius.radusergroup
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE radius.radacct ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.radacct FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.radacct;
CREATE POLICY tenant_isolation ON radius.radacct
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

ALTER TABLE radius.radpostauth ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius.radpostauth FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius.radpostauth;
CREATE POLICY tenant_isolation ON radius.radpostauth
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
"""

REVERSE_SQL = """
DROP TABLE IF EXISTS radius.radpostauth, radius.radacct, radius.radusergroup,
    radius.radgroupreply, radius.radreply, radius.radcheck, radius.nas CASCADE;
DROP SCHEMA IF EXISTS radius;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0001_initial"),
        ("network", "0001_initial"),
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(SCHEMA_SQL, reverse_sql="DROP SCHEMA IF EXISTS radius CASCADE;"),
        migrations.RunSQL(TABLES_SQL, reverse_sql=REVERSE_SQL),
        migrations.RunSQL(RLS_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
