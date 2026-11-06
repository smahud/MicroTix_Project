"""RLS + FK komposit untuk tabel billing M6 (TK-601).

Pola sesuai ARCHITECTURE.md §4 dan migration_sql.py:
- ENABLE+FORCE RLS + policy tenant_isolation GUC app.tenant_id pada seluruh
  tabel billing (data tenant).
- UNIQUE(tenant_id, id) pada induk yang dirujuk FK komposit
  (billing_internet_invoice, billing_internet_payment).
- FK komposit menjaga baris milik tenant yang sama:
  * billing_service_charge (tenant, service) → customers_service(tenant, id)
  * billing_internet_invoice (tenant, service) → customers_service(tenant, id)
  * billing_internet_invoice_line (tenant, invoice) → billing_internet_invoice
  * billing_payment_allocation (tenant, payment)/(tenant, invoice) → masing-masing
"""
from django.db import migrations

from domains.common import migration_sql as sqlx


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
        ("customers", "0002_rls_composite"),
    ]

    operations = [
        # --- RLS: seluruh tabel billing adalah data tenant ---
        sqlx.enable_rls("billing_package"),
        sqlx.enable_rls("billing_service_charge"),
        sqlx.enable_rls("billing_internet_invoice"),
        sqlx.enable_rls("billing_internet_invoice_line"),
        sqlx.enable_rls("billing_internet_payment"),
        sqlx.enable_rls("billing_payment_allocation"),
        # --- UNIQUE(tenant_id, id) induk untuk FK komposit ---
        sqlx.unique_tenant("billing_internet_invoice", "id"),
        sqlx.unique_tenant("billing_internet_payment", "id"),
        # --- FK komposit: tenant selalu milik yang sama ---
        sqlx.composite_fk(
            table="billing_service_charge",
            parent_table="customers_service",
            local_parent_col="service_id",
            constraint_name="ck_charge_tenant_service",
        ),
        sqlx.composite_fk(
            table="billing_internet_invoice",
            parent_table="customers_service",
            local_parent_col="service_id",
            constraint_name="ck_bilinv_tenant_service",
        ),
        sqlx.composite_fk(
            table="billing_internet_invoice_line",
            parent_table="billing_internet_invoice",
            local_parent_col="invoice_id",
            constraint_name="ck_billine_tenant_invoice",
        ),
        sqlx.composite_fk(
            table="billing_payment_allocation",
            parent_table="billing_internet_payment",
            local_parent_col="payment_id",
            constraint_name="ck_bilalloc_tenant_payment",
        ),
        sqlx.composite_fk(
            table="billing_payment_allocation",
            parent_table="billing_internet_invoice",
            local_parent_col="invoice_id",
            constraint_name="ck_bilalloc_tenant_invoice",
        ),
    ]
