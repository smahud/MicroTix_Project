"""Utilitas migrasi SQL — FK komposit (tenant_id, parent) dan RLS.

ARCHITECTURE.md §4: Django ForeignKey biasa dipakai ORM, tetapi migration SQL
menambah constraint komposit (tenant_id,parent_id)→(tenant_id,id) dengan
reverse SQL. ENABLE+FORCE RLS berlaku pada data tenant.
"""
from __future__ import annotations

from django.db import migrations


def composite_fk(
    *,
    table: str,
    parent_table: str,
    local_parent_col: str,
    constraint_name: str | None = None,
) -> migrations.RunSQL:
    """Tambah FK komposit (tenant_id, parent) → parent(tenant_id, id)."""
    name = constraint_name or f"ck_{table}_{local_parent_col}_tenant"
    sql = (
        f"ALTER TABLE {table} "
        f"ADD CONSTRAINT {name} FOREIGN KEY (tenant_id, {local_parent_col}) "
        f"REFERENCES {parent_table} (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE"
    )
    reverse = f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"
    return migrations.RunSQL(sql, reverse_sql=reverse)


def enable_rls(table: str, policy: str = "tenant_isolation") -> migrations.RunSQL:
    """Aktifkan + paksa RLS dan pasang policy tenant; konteks kosong gagal tertutup."""
    sql = (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; "
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY; "
        f"DROP POLICY IF EXISTS {policy} ON {table}; "
        f"CREATE POLICY {policy} ON {table} USING "
        f"(tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )
    reverse = f"DROP POLICY IF EXISTS {policy} ON {table}; ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"
    return migrations.RunSQL(sql, reverse_sql=reverse)


def unique_tenant(table: str, cols: str) -> migrations.RunSQL:
    """UNIQUE(tenant_id, ...) sesuai invariant §4."""
    name = f"uq_{table}_tenant_{'_'.join(c.strip() for c in cols.split(','))}"
    sql = f"ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE (tenant_id, {cols})"
    reverse = f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"
    return migrations.RunSQL(sql, reverse_sql=reverse)
