"""RLS + FK komposit untuk tabel backup tenant (M5).

Mengikuti pola subscriptions/network 0002_rls_composite (ARCHITECTURE.md §4):
ENABLE+FORCE RLS, UNIQUE(tenant_id,id), FK komposit (tenant_id,router_id)
→ network_router(tenant_id,id).
"""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("backups", "0001_initial"),
        # FK komposit menunjuk network_router(tenant_id, id) yang unik sejak
        # network 0002_rls_composite.
        ("network", "0004_rls_m3"),
    ]

    operations = [
        # --- RLS: kedua tabel tenant, konteks kosong gagal tertutup (§4) ---
        sqlx.enable_rls("backups_artifact"),
        sqlx.enable_rls("backups_schedule"),
        # --- UNIQUE(tenant_id, id) §4 ---
        sqlx.unique_tenant("backups_artifact", "id"),
        sqlx.unique_tenant("backups_schedule", "id"),
        # --- FK komposit anak→induk (tenant konsisten) ---
        sqlx.composite_fk(
            table="backups_artifact",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_backup_artifact_tenant_router",
        ),
        sqlx.composite_fk(
            table="backups_schedule",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_backup_sched_tenant_router",
        ),
    ]
