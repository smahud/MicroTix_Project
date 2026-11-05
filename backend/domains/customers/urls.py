from django.urls import path

from domains.customers import views

urlpatterns = [
    path("tenants/<str:tenant_id>/services", views.ServiceListView.as_view(), name="services-list"),
    path("tenants/<str:tenant_id>/services/<str:service_id>", views.ServiceDetailView.as_view(), name="service-detail"),
    path(
        "tenants/<str:tenant_id>/services/<str:service_id>/reveal-credentials",
        views.ServiceRevealCredentialsView.as_view(),
        name="service-reveal-credentials",
    ),
]
urlpatterns += [
    path("tenants/<str:tenant_id>/imports", views.CsvImportCreateView.as_view(), name="csv-import-create"),
    path("tenants/<str:tenant_id>/imports/<str:import_id>/validate", views.CsvImportValidateView.as_view(), name="csv-import-validate"),
    path("tenants/<str:tenant_id>/imports/<str:import_id>/commit", views.CsvImportCommitView.as_view(), name="csv-import-commit"),
]
