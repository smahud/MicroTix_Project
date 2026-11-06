"""RLS + kekekalan row dokumen terbit (TK-109).

Row IssuedDocument bersifat immutable (I18N-01: snapshot saat issued; reprint
tidak memakai template terbaru) — UPDATE dan DELETE ditolak trigger, mengikuti
pola subs_platform_payment_source_event (subscriptions/0002_rls_composite).
"""
from django.db import migrations

from domains.common import migration_sql as sqlx

IMMUTABLE_TRIGGER = """
CREATE OR REPLACE FUNCTION documents_issued_document_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'documents_issued_document bersifat immutable';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_documents_issued_document_immutable ON documents_issued_document;
CREATE TRIGGER trg_documents_issued_document_immutable
    BEFORE UPDATE OR DELETE ON documents_issued_document
    FOR EACH ROW EXECUTE FUNCTION documents_issued_document_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        sqlx.enable_rls("documents_issued_document"),
        # Dokumen terbit tidak pernah diubah/dihapus: reprint membaca artifact
        # tersimpan (snapshot), bukan merender ulang dari template terbaru.
        migrations.RunSQL(
            IMMUTABLE_TRIGGER,
            reverse_sql=(
                "DROP TRIGGER IF EXISTS trg_documents_issued_document_immutable "
                "ON documents_issued_document; "
                "DROP FUNCTION IF EXISTS documents_issued_document_immutable();"
            ),
        ),
    ]
