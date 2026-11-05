from django.urls import path

from domains.radius import views

urlpatterns = [
    path("tenants/<str:tenant_id>/radius-status", views.RadiusStatusListView.as_view(), name="radius-status-list"),
    path("tenants/<str:tenant_id>/radius-status/<str:router_id>", views.RadiusStatusDetailView.as_view(), name="radius-status-detail"),
    path(
        "tenants/<str:tenant_id>/routers/<str:router_id>/radius-cutover",
        views.RadiusCutoverView.as_view(),
        name="radius-cutover",
    ),
]
