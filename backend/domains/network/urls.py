from django.urls import path

from domains.network import views

urlpatterns = [
    path("tenants/<str:tenant_id>/routers", views.RouterListView.as_view(), name="routers-list"),
    path("tenants/<str:tenant_id>/routers/<str:router_id>", views.RouterDetailView.as_view(), name="router-detail"),
]
