from django.urls import path

from domains.customers import views

urlpatterns = [
    # --- Services (U04): GET daftar + POST provisioning (izin per metode) ---
    path("tenants/<str:tenant_id>/services", views.ServiceListView.as_view(), name="services-list"),
    path("tenants/<str:tenant_id>/services/<str:service_id>", views.ServiceDetailView.as_view(), name="service-detail"),
    path(
        "tenants/<str:tenant_id>/services/<str:service_id>/reveal-credentials",
        views.RevealCredentialsView.as_view(),
        name="service-reveal-credentials",
    ),
    # --- Access accounts (U19) ---
    path("tenants/<str:tenant_id>/access-accounts", views.AccessAccountListView.as_view(), name="access-accounts-list"),
    path(
        "tenants/<str:tenant_id>/access-accounts/<str:account_id>",
        views.AccessAccountStateView.as_view(),
        name="access-account-state",
    ),
    # --- CSV import (U08) ---
    path("tenants/<str:tenant_id>/imports", views.CsvImportCreateView.as_view(), name="csv-import-create"),
    path(
        "tenants/<str:tenant_id>/imports/<str:import_id>/validate",
        views.CsvImportValidateView.as_view(),
        name="csv-import-validate",
    ),
    path(
        "tenants/<str:tenant_id>/imports/<str:import_id>/commit",
        views.CsvImportCommitView.as_view(),
        name="csv-import-commit",
    ),
    # --- Migration wizard (U07) ---
    path(
        "tenants/<str:tenant_id>/routers/<str:router_id>/migrations",
        views.MigrationStartView.as_view(),
        name="migration-start",
    ),
    path(
        "tenants/<str:tenant_id>/migrations/<str:migration_id>/accounts",
        views.MigrationAccountsView.as_view(),
        name="migration-accounts",
    ),
    path(
        "tenants/<str:tenant_id>/migrations/<str:migration_id>/identity-conflicts",
        views.IdentityConflictsView.as_view(),
        name="migration-identity-conflicts",
    ),
    path(
        "tenants/<str:tenant_id>/migrations/<str:migration_id>/identity-conflicts/<str:group_id>",
        views.IdentityConflictResolveView.as_view(),
        name="migration-identity-conflict-resolve",
    ),
    path(
        "tenants/<str:tenant_id>/migrations/<str:migration_id>/commit",
        views.MigrationCommitView.as_view(),
        name="migration-commit",
    ),
    path(
        "tenants/<str:tenant_id>/routers/<str:router_id>/password-harvest",
        views.PasswordHarvestView.as_view(),
        name="password-harvest",
    ),
]
