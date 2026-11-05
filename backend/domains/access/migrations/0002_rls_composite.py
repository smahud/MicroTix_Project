"""RLS + FK komposit untuk tabel akses (akun AAA + NAS)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0001_initial"),
        ("network", "0002_rls_composite"),
        ("customers", "0002_rls"),
    ]

    operations = [
        sqlx.enable_rls("access_account"),
        sqlx.enable_rls("access_account_source"),
        sqlx.enable_rls("access_nas"),
        sqlx.unique_tenant("access_account", "id"),
        sqlx.unique_tenant("access_account_source", "id"),
        sqlx.unique_tenant("access_nas", "id"),
        # FK komposit: source(tenant,account)→account(tenant,id);
        #              source(tenant,router)→router(tenant,id);
        #              nas(tenant,router)→router(tenant,id)
        sqlx.composite_fk(
            table="access_account_source",
            parent_table="access_account",
            local_parent_col="account_id",
            constraint_name="ck_accesssource_tenant_account",
        ),
        sqlx.composite_fk(
            table="access_account_source",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_accesssource_tenant_router",
        ),
        sqlx.composite_fk(
            table="access_nas",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_accessnas_tenant_router",
        ),
    ]
