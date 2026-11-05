"""RLS + FK komposit untuk tabel subscription tenant; event sumber immutable."""
from django.db import migrations

from domains.common import migration_sql as sqlx

IMMUTABLE_TRIGGER = """
CREATE OR REPLACE FUNCTION subs_source_event_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'subs_platform_payment_source_event bersifat immutable';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_source_event_immutable ON subs_platform_payment_source_event;
CREATE TRIGGER trg_source_event_immutable
    BEFORE UPDATE OR DELETE ON subs_platform_payment_source_event
    FOR EACH ROW EXECUTE FUNCTION subs_source_event_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        sqlx.enable_rls("subs_subscription"),
        sqlx.enable_rls("subs_quota_reservation"),
        sqlx.enable_rls("subs_saas_invoice"),
        sqlx.enable_rls("subs_payment_submission"),
        sqlx.unique_tenant("subs_saas_invoice", "id"),
        # FK komposit: PaymentSubmission(tenant_id, saas_invoice_id) → SaaSInvoice(tenant_id, id)
        sqlx.composite_fk(
            table="subs_payment_submission",
            parent_table="subs_saas_invoice",
            local_parent_col="saas_invoice_id",
            constraint_name="ck_paysub_tenant_invoice",
        ),
        # Event sumber pembayaran platform: immutable (TK-003) — tidak ada UPDATE/DELETE.
        migrations.RunSQL(
            IMMUTABLE_TRIGGER,
            reverse_sql="DROP TRIGGER IF EXISTS trg_source_event_immutable ON subs_platform_payment_source_event; DROP FUNCTION IF EXISTS subs_source_event_immutable();",
        ),
    ]
