"""Kebijakan RLS khusus jalur layanan enrollment.

Dua kebijakan GUC terpisah (bukan peran superuser; fail-closed bila kosong):
- app.enrollment_probe='1': SELECT (+FOR UPDATE) pada enrollment oleh
  endpoint probe yang diautentikasi token — pemanggil adalah router, bukan
  sesi tenant. Mutasi tetap hanya terjadi dalam tenant_scope.
- app.platform_service='1': SELECT global router/enrollment untuk alokasi
  /32 tunnel yang memang harus lintas tenant (UNIQUE global).
"""
from django.db import migrations

PROBE_SQL = """
DROP POLICY IF EXISTS enrollment_probe ON network_router_enrollment;
CREATE POLICY enrollment_probe ON network_router_enrollment FOR SELECT
  USING (current_setting('app.enrollment_probe', true) = '1');
DROP POLICY IF EXISTS enrollment_probe_update ON network_router_enrollment;
CREATE POLICY enrollment_probe_update ON network_router_enrollment FOR UPDATE
  USING (current_setting('app.enrollment_probe', true) = '1')
  WITH CHECK (current_setting('app.enrollment_probe', true) = '1');
"""

SERVICE_READ_SQL = """
DROP POLICY IF EXISTS platform_service_read ON network_router;
CREATE POLICY platform_service_read ON network_router FOR SELECT
  USING (current_setting('app.platform_service', true) = '1');
DROP POLICY IF EXISTS platform_service_read ON network_router_enrollment;
CREATE POLICY platform_service_read ON network_router_enrollment FOR SELECT
  USING (current_setting('app.platform_service', true) = '1');
"""


class Migration(migrations.Migration):
    dependencies = [
        ("network", "0004_enrollment_rls"),
    ]

    operations = [
        migrations.RunSQL(
            PROBE_SQL,
            reverse_sql=(
                "DROP POLICY IF EXISTS enrollment_probe ON network_router_enrollment; "
                "DROP POLICY IF EXISTS enrollment_probe_update ON network_router_enrollment;"
            ),
        ),
        migrations.RunSQL(
            SERVICE_READ_SQL,
            reverse_sql=(
                "DROP POLICY IF EXISTS platform_service_read ON network_router; "
                "DROP POLICY IF EXISTS platform_service_read ON network_router_enrollment;"
            ),
        ),
    ]
