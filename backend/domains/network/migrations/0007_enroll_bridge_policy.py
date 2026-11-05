"""Policy bridge bootstrap untuk network_router_enrollment (RLS §4).

Callback perangkat (bridge/enroll-complete) datang TANPA konteks tenant —
token hash adalah anchor-nya (256-bit CSPRNG). Lookup butuh SELECT lintas
tenant; policy GUC khusus (pola sama dengan facade_bootstrap radius.nas)
daripada melemahkan RLS secara umum. GUC hanya diset oleh service layer
tepercaya selama lookup token, lalu dimatikan.
"""
from django.db import migrations

SQL = """
DROP POLICY IF EXISTS enroll_bridge ON network_router_enrollment;
CREATE POLICY enroll_bridge ON network_router_enrollment
    FOR SELECT
    USING (current_setting('app.enroll_bridge', true) = 'on');
"""


class Migration(migrations.Migration):
    dependencies = [
        ("network", "0006_routerenrollment_token_ref"),
    ]

    operations = [migrations.RunSQL(SQL, reverse_sql="DROP POLICY IF EXISTS enroll_bridge ON network_router_enrollment;")]
