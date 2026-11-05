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
    path("api/v1/", include("domains.network.urls")),     # router + enrollment + discovery
    path("api/v1/", include("domains.customers.urls")),    # pelanggan/layanan (M4)
    path("api/v1/", include("domains.access.urls")),       # akun AAA + status RADIUS (M3)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]
