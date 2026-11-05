"""RLS + FK komposit untuk radius_cutover_run (tabel cutover B0–B6 §10.2).

Pola sama dengan network 0004_rls_m3: policy tenant_isolation GUC
app.tenant_id + FORCE; FK komposit (tenant_id, router_id) →
network_router(tenant_id, id) menjaga router milik tenant yang sama.
network_router sudah UNIQUE(tenant_id, id) sejak network 0002.
"""
from django.db import migrations

RLS_SQL = """
ALTER TABLE radius_cutover_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE radius_cutover_run FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON radius_cutover_run;
CREATE POLICY tenant_isolation ON radius_cutover_run
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
"""

RLS_REVERSE = (
    "DROP POLICY IF EXISTS tenant_isolation ON radius_cutover_run; "
    "ALTER TABLE radius_cutover_run DISABLE ROW LEVEL SECURITY;"
)

FK_SQL = (
    "ALTER TABLE radius_cutover_run "
    "ADD CONSTRAINT ck_covrun_tenant_router FOREIGN KEY (tenant_id, router_id) "
    "REFERENCES network_router (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE"
)
FK_REVERSE = "ALTER TABLE radius_cutover_run DROP CONSTRAINT IF EXISTS ck_covrun_tenant_router"


class Migration(migrations.Migration):
    dependencies = [
        ("radius", "0003_initial"),
        ("network", "0004_rls_m3"),
    ]

    operations = [
        migrations.RunSQL(RLS_SQL, reverse_sql=RLS_REVERSE),
        migrations.RunSQL(FK_SQL, reverse_sql=FK_REVERSE),
    ]
