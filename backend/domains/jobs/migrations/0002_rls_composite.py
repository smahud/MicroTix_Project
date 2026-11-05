"""RLS + FK komposit untuk tabel tenant jobs (TK-102, ARCHITECTURE §4).

Job envelope global (worker terpercaya); JobDetail tenant-RLS.
"""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        # JobDetail: RLS + FK komposit (tenant_id, job_id) → jobs_job(tenant_id, id)
        sqlx.unique_tenant("jobs_job", "id"),
        sqlx.enable_rls("jobs_jobdetail"),
        sqlx.unique_tenant("jobs_jobdetail", "job_id"),
        sqlx.composite_fk(
            table="jobs_jobdetail",
            parent_table="jobs_job",
            local_parent_col="job_id",
            constraint_name="ck_jobdetail_tenant_job",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS ix_jobdetail_tenant_job ON jobs_jobdetail (tenant_id, job_id)",
            reverse_sql="DROP INDEX IF EXISTS ix_jobdetail_tenant_job",
        ),
    ]
