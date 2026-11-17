from django.urls import path

from domains.access import views

urlpatterns = [
    path("tenants/<str:tenant_id>/access-accounts", views.AccessAccountListView.as_view(), name="access-accounts-list"),
    path(
        "tenants/<str:tenant_id>/access-accounts/<str:account_id>",
        views.AccessAccountPatchView.as_view(),
        name="access-accounts-patch",
    ),
    path(
        "tenants/<str:tenant_id>/access-accounts/<str:account_id>/rotate",
        views.AccessAccountRotateView.as_view(),
        name="access-accounts-rotate",
    ),
    path("tenants/<str:tenant_id>/radius-status", views.RadiusStatusListView.as_view(), name="radius-status-list"),
    path(
        "tenants/<str:tenant_id>/radius-status/<str:router_id>",
        views.RadiusStatusDetailView.as_view(),
        name="radius-status-detail",
    ),
    path("tenants/<str:tenant_id>/nas/pending", views.NasPendingView.as_view(), name="nas-pending"),
]
