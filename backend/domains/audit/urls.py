from django.urls import path

from domains.audit import views

urlpatterns = [
    path("tenants/<str:tenant_id>/audit-timeline", views.AuditTimelineView.as_view(), name="audit-timeline"),
]
