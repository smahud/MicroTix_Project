"""RLS + FK komposit untuk tabel network tenant (registri router)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("network", "0001_initial"),
    ]

    operations = [
        sqlx.enable_rls("network_router"),
        sqlx.enable_rls("network_router_health"),
        sqlx.unique_tenant("network_router", "id"),
        # FK komposit: health(tenant_id, router_id) → router(tenant_id, id)
        sqlx.composite_fk(
            table="network_router_health",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_routerhealth_tenant_router",
        ),
    ]
