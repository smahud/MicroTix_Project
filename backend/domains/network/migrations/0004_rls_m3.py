"""RLS + FK komposit untuk tabel M3 (enrollment, WireGuard, discovery, ops)."""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("network", "0003_wireguardhost_router_api_cert_fingerprint_and_more"),
    ]

    operations = [
        # --- RLS: tabel tenant ---
        sqlx.enable_rls("network_router_enrollment"),
        sqlx.enable_rls("network_wireguard_peer"),
        sqlx.enable_rls("network_discovery_snapshot"),
        sqlx.enable_rls("network_discovery_object"),
        sqlx.enable_rls("network_device_operation"),
        # network_wireguard_host: state host platform (tanpa baris tenant) —
        # tidak diekspos API; hanya service layer terpercaya.
        # --- UNIQUE(tenant_id, id) induk untuk FK komposit ---
        # network_router sudah dibuat unik pada 0002_rls_composite.
        sqlx.unique_tenant("network_router_enrollment", "id"),
        sqlx.unique_tenant("network_discovery_snapshot", "id"),
        # --- FK komposit anak→induk (tenant konsisten) ---
        sqlx.composite_fk(
            table="network_router_enrollment",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_enroll_tenant_router",
        ),
        sqlx.composite_fk(
            table="network_wireguard_peer",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_wgpeer_tenant_router",
        ),
        sqlx.composite_fk(
            table="network_discovery_snapshot",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_discsnap_tenant_router",
        ),
        sqlx.composite_fk(
            table="network_discovery_object",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_discobj_tenant_router",
        ),
        sqlx.composite_fk(
            table="network_discovery_object",
            parent_table="network_discovery_snapshot",
            local_parent_col="snapshot_id",
            constraint_name="ck_discobj_tenant_snapshot",
        ),
        sqlx.composite_fk(
            table="network_device_operation",
            parent_table="network_router",
            local_parent_col="router_id",
            constraint_name="ck_devop_tenant_router",
        ),
    ]
