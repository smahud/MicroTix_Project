"""URL documents (TK-109) — BIL-08.

GET /tenants/{t}/documents          → daftar (kursor + filter eksak)
GET /tenants/{t}/documents/{id}     → artifact PDF (application/pdf inline)
"""
from django.urls import path

from domains.documents import views

urlpatterns = [
    path("tenants/<str:tenant_id>/documents", views.DocumentListView.as_view(), name="documents-list"),
    path(
        "tenants/<str:tenant_id>/documents/<str:document_id>",
        views.DocumentArtifactView.as_view(),
        name="document-artifact",
    ),
]
