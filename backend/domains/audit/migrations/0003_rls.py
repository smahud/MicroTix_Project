"""RLS untuk tabel audit tenant (TK-102)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_initial"),
    ]

    operations = [
        sqlx.enable_rls("audit_event"),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS ix_audit_tenant_id ON audit_event (tenant_id, id)",
            reverse_sql="DROP INDEX IF EXISTS ix_audit_tenant_id",
        ),
    ]
