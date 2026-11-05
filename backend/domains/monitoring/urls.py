from django.urls import path

from domains.monitoring import views

urlpatterns = [
    path("tenants/<str:tenant_id>/monitor", views.MonitorListView.as_view(), name="monitor"),
]
