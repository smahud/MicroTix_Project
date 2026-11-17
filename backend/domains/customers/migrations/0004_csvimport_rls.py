"""RLS untuk tabel impor CSV (tenant data)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0003_csvimport"),
    ]

    operations = [
        sqlx.enable_rls("customer_csv_import"),
        sqlx.unique_tenant("customer_csv_import", "id"),
    ]
