"""URL root MicroTix — prefix /api/v1 (ARCHITECTURE.md §5)."""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

handler404 = "domains.common.envelope.handler404"
handler500 = "domains.common.envelope.handler500"


urlpatterns = [
    path("api/v1/", include("domains.config.urls")),      # meta/health/branding/enums
    path("api/v1/", include("domains.identity.urls")),    # auth/sesi/tenant
    path("api/v1/", include("domains.jobs.urls")),        # pekerjaan
    path("api/v1/", include("domains.audit.urls")),       # audit timeline
    path("api/v1/", include("domains.subscriptions.urls")),  # paket/subscription
    path("api/v1/", include("domains.network.urls")),     # router/enrollment/discovery (M3)
    path("api/v1/", include("domains.customers.urls")),   # pelanggan/layanan/akun akses/CSV (M4)
    path("api/v1/", include("domains.billing.urls")),     # paket/invoice/pembayaran internet (M6)
    path("api/v1/", include("domains.documents.urls")),   # dokumen terbit PDF (TK-109)
    path("api/v1/", include("domains.radius.urls")),      # RADIUS status/cutover (M3)
    path("api/v1/", include("domains.backups.urls")),     # backup router (M5)
    path("api/v1/", include("domains.monitoring.urls")),  # monitoring (M5)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]
