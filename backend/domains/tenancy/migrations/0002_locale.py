"""Tenant.locale — bahasa default tenant (I18N-06; M6 TK-601).

Rantai bahasa dokumen pelanggan (I18N-01 §2): preferensi pelanggan →
bahasa default tenant → id. Field ini tautan kedua rantai tersebut;
BIL-01 "Dokumen memuat bahasa terbit".
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="locale",
            field=models.CharField(default="id", max_length=5),
        ),
    ]
