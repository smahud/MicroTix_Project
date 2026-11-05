"""RLS + FK komposit untuk tabel customers (M4) — pola subscriptions/network.

- ENABLE+FORCE RLS pada seluruh tabel tenant; konteks kosong gagal tertutup.
- UNIQUE(tenant_id, id) pada induk yang dirujuk FK komposit.
- FK komposit (tenant_id, parent_id)→(tenant_id, id) — ARCHITECTURE.md §4.

Catatan deviasi (terdokumentasi):
- network_discovery_object belum memiliki UNIQUE(tenant_id, id) (migrasi network
  milik domain lain), sehingga FK komposit decision(tenant_id,
  discovery_object_id)→network_discovery_object(tenant_id, id) belum dapat
  dipasang; konsistensi tenant dijaga RLS kedua tabel + service layer yang
  memuat objek melalui snapshot sesi (tenant-scoped). Constraint tersebut
  menyusul bersama skema network.
- customers_csv_import tidak memiliki kolom router (model §A.4), sehingga FK
  komposit csv_import(tenant_id, router_id) tidak berlaku untuk tabel ini.
"""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0001_initial"),
        ("network", "0004_rls_m3"),
    ]

    operations = [
        # --- RLS: seluruh tabel tenant ---
        sqlx.enable_rls("customers_customer"),
        sqlx.enable_rls("customers_service"),
        sqlx.enable_rls("customers_access_account"),
        sqlx.enable_rls("customers_csv_import"),
        sqlx.enable_rls("customers_migration_session"),
        sqlx.enable_rls("customers_migration_decision"),
        # --- UNIQUE(tenant_id, id) induk untuk FK komposit ---
        sqlx.unique_tenant("customers_customer", "id"),
        sqlx.unique_tenant("customers_service", "id"),
        # Induk untuk decision(tenant_id, session_id).
        sqlx.unique_tenant("customers_migration_session", "id"),
        # --- FK komposit anak→induk (tenant konsisten, §4) ---
        sqlx.composite_fk(
            table="customers_service",
            parent_table="customers_customer",
            local_parent_col="customer_id",
            constraint_name="ck_service_tenant_customer",
        ),
        sqlx.composite_fk(
            table="customers_access_account",
            parent_table="customers_service",
            local_parent_col="service_id",
            constraint_name="ck_access_tenant_service",
        ),
        sqlx.composite_fk(
            table="customers_migration_session",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_migsession_tenant_router",
        ),
        sqlx.composite_fk(
            table="customers_migration_session",
            parent_table="network_discovery_snapshot",
            local_parent_col="snapshot_id",
            constraint_name="ck_migsession_tenant_snapshot",
        ),
        sqlx.composite_fk(
            table="customers_migration_decision",
            parent_table="customers_migration_session",
            local_parent_col="session_id",
            constraint_name="ck_decision_tenant_session",
        ),
    ]
