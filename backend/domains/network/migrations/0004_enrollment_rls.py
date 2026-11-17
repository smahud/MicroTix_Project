"""RLS + FK komposit untuk tabel enrollment/discovery (tenant data)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("network", "0003_router_enrollment_models"),
        ("access", "0003_radius_schema"),
        ("customers", "0001_initial"),
    ]

    operations = [
        sqlx.enable_rls("network_router_enrollment"),
        sqlx.enable_rls("network_discovery_snapshot"),
        sqlx.unique_tenant("network_router_enrollment", "id"),
        sqlx.unique_tenant("network_discovery_snapshot", "id"),
        # FK komposit: enrollment(tenant,router)→router(tenant,id);
        #              snapshot(tenant,router)→router(tenant,id)
        sqlx.composite_fk(
            table="network_router_enrollment",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_enrollment_tenant_router",
        ),
        sqlx.composite_fk(
            table="network_discovery_snapshot",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_discovery_tenant_router",
        ),
    ]
