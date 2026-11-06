# Migrasi awal documents — IssuedDocument (TK-109; BIL-01/BIL-08, I18N-01).

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenancy', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IssuedDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[('internet_invoice', 'Internet Invoice'), ('receipt', 'Receipt'), ('saas_invoice', 'Saas Invoice'), ('report', 'Report')], max_length=48)),
                ('doc_number', models.CharField(max_length=64)),
                ('ref_type', models.CharField(blank=True, default='', max_length=48)),
                ('ref_id', models.CharField(blank=True, default='', max_length=64)),
                ('locale', models.CharField(default='id', max_length=5)),
                ('timezone', models.CharField(default='Asia/Jakarta', max_length=64)),
                ('template_version', models.CharField(default='1', max_length=16)),
                ('values', models.JSONField(default=dict)),
                ('storage_path', models.CharField(blank=True, default='', max_length=512)),
                ('sha256', models.CharField(blank=True, default='', max_length=64)),
                ('size_bytes', models.IntegerField(blank=True, null=True)),
                ('issued_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('tenant', models.ForeignKey(db_column='tenant_id', on_delete=django.db.models.deletion.CASCADE, related_name='issued_documents', to='tenancy.tenant')),
            ],
            options={
                'db_table': 'documents_issued_document',
            },
        ),
        migrations.AddConstraint(
            model_name='issueddocument',
            constraint=models.UniqueConstraint(fields=('tenant', 'kind', 'doc_number'), name='uq_document_tenant_kind_number'),
        ),
        migrations.AddIndex(
            model_name='issueddocument',
            index=models.Index(fields=('tenant', 'kind', 'issued_at'), name='ix_document_tenant_kind_time'),
        ),
        migrations.AddIndex(
            model_name='issueddocument',
            index=models.Index(fields=('tenant', 'ref_type', 'ref_id'), name='ix_document_tenant_ref'),
        ),
    ]
