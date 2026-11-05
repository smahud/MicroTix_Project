from django.urls import path

from domains.identity import views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view(), name="auth-register"),
    path("auth/verify-email", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/login-totp", views.LoginTotpView.as_view(), name="auth-login-totp"),
    path("auth/recover", views.RecoverView.as_view(), name="auth-recover"),
    path("auth/session", views.SessionView.as_view(), name="auth-session"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/reauthenticate", views.ReauthenticateView.as_view(), name="auth-reauthenticate"),
    path("auth/tenants", views.TenantsView.as_view(), name="auth-tenants"),
    path("auth/tenants/<str:tenant_id>/switch", views.TenantSwitchView.as_view(), name="auth-tenant-switch"),
    path("auth/mfa/setup", views.MfaSetupView.as_view(), name="auth-mfa-setup"),
    path("auth/mfa/confirm", views.MfaConfirmView.as_view(), name="auth-mfa-confirm"),
]
