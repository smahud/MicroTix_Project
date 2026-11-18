"""Writer attempt receipt (REV-1711-04 R4) — additive.

Identitas proses penulis attempt (pid/host/starttime /proc) + receipt
penyelesaian attempt, untuk membedakan "penulis lama terverifikasi
selesai/berhenti" dari "status lintas proses tidak diketahui" pada
resolve_uncertain(applied=False). Kolom baru nullable — baris lama
tetap NULL (unknown → ditahan, fail-closed; A09 compatibility).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0005_idempotency_scrub_secret_preview"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="writer_pid",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="writer_host",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="writer_start_ticks",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="writer_ended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
