"""RLS + FK komposit untuk tabel pelanggan/layanan (tenant data)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0001_initial"),
        ("network", "0002_rls_composite"),
    ]

    operations = [
        sqlx.enable_rls("customer"),
        sqlx.enable_rls("service"),
        sqlx.unique_tenant("customer", "id"),
        sqlx.unique_tenant("service", "id"),
        sqlx.composite_fk(
            table="service",
            parent_table="customer",
            local_parent_col="customer_id",
            constraint_name="ck_service_tenant_customer",
        ),
    ]
