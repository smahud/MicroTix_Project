from django.urls import path

from domains.network import views

urlpatterns = [
    path("tenants/<str:tenant_id>/routers", views.RouterListView.as_view(), name="routers-list"),
    path("tenants/<str:tenant_id>/routers/<str:router_id>", views.RouterDetailView.as_view(), name="router-detail"),
    # --- Enrollment (M3) ---
    path("tenants/<str:tenant_id>/router-enrollments", views.RouterEnrollmentCreateView.as_view(), name="enrollments-create"),
    path(
        "tenants/<str:tenant_id>/router-enrollments/<str:enrollment_id>",
        views.RouterEnrollmentDetailView.as_view(),
        name="enrollments-detail",
    ),
    path(
        "tenants/<str:tenant_id>/router-enrollments/<str:enrollment_id>/bootstrap",
        views.RouterEnrollmentBootstrapView.as_view(),
        name="enrollments-bootstrap",
    ),
    # Probe dipanggil router melalui tunnel (token di body; bukan sesi user).
    path("router-enrollments/<str:enrollment_id>/probe", views.RouterEnrollmentProbeView.as_view(), name="enrollments-probe"),
    # --- Discovery & health (job read-only) ---
    path("tenants/<str:tenant_id>/routers/<str:router_id>/discoveries", views.RouterDiscoveryView.as_view(), name="router-discovery"),
    path("tenants/<str:tenant_id>/routers/<str:router_id>/health-probe", views.RouterHealthProbeView.as_view(), name="router-health-probe"),
]
