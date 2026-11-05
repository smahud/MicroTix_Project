from django.urls import path

from domains.config import views

urlpatterns = [
    path("meta/enums", views.EnumsView.as_view(), name="meta-enums"),
    path("meta/branding", views.BrandingView.as_view(), name="meta-branding"),
    path("meta/config", views.ConfigView.as_view(), name="meta-config"),
    path("health/live", views.HealthLiveView.as_view(), name="health-live"),
    path("health/ready", views.HealthReadyView.as_view(), name="health-ready"),
]
