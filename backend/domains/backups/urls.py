from django.urls import path

from domains.backups import views

urlpatterns = [
    path("tenants/<str:tenant_id>/backups", views.BackupArtifactListView.as_view(), name="backups-list"),
    path("tenants/<str:tenant_id>/backup-schedules", views.BackupScheduleListView.as_view(), name="backup-schedules"),
    path(
        "tenants/<str:tenant_id>/routers/<str:router_id>/backups",
        views.RunBackupView.as_view(),
        name="backup-run",
    ),
]
