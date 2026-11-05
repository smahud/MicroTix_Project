from django.urls import path

from domains.network import views

urlpatterns = [
    path("tenants/<str:tenant_id>/routers", views.RouterListView.as_view(), name="routers-list"),
    path("tenants/<str:tenant_id>/routers/<str:router_id>", views.RouterDetailView.as_view(), name="router-detail"),
    path("tenants/<str:tenant_id>/router-enrollments", views.EnrollmentCreateView.as_view(), name="enrollment-create"),
    path(
        "tenants/<str:tenant_id>/router-enrollments/<str:enrollment_id>",
        views.EnrollmentProgressView.as_view(),
        name="enrollment-progress",
    ),
    path(
        "tenants/<str:tenant_id>/router-enrollments/<str:enrollment_id>/bootstrap",
        views.EnrollmentBootstrapView.as_view(),
        name="enrollment-bootstrap",
    ),
    path(
        "tenants/<str:tenant_id>/routers/<str:router_id>/discoveries",
        views.DiscoveryStartView.as_view(),
        name="router-discovery",
    ),
    path("tenants/<str:tenant_id>/routers/<str:router_id>/release", views.RouterReleaseView.as_view(), name="router-release"),
    path("tenants/<str:tenant_id>/routers/<str:router_id>/replace", views.RouterReplaceView.as_view(), name="router-replace"),
    # Bridge dari perangkat router (token di body; tanpa sesi pengguna).
    path("bridge/enroll-complete", views.BridgeEnrollCompleteView.as_view(), name="bridge-enroll-complete"),
]
