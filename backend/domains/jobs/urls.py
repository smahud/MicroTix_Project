from django.urls import path

from domains.jobs import views

urlpatterns = [
    path("tenants/<str:tenant_id>/jobs", views.JobListView.as_view(), name="jobs-list"),
    path("jobs/<str:job_id>", views.JobDetailView.as_view(), name="job-detail"),
    path("jobs/<str:job_id>/retry", views.JobRetryView.as_view(), name="job-retry"),
    path("jobs/<str:job_id>/cancel", views.JobCancelView.as_view(), name="job-cancel"),
]
