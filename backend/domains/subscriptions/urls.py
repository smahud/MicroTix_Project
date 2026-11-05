from django.urls import path

from domains.subscriptions import views

urlpatterns = [
    path("tenants/<str:tenant_id>/subscription", views.SubscriptionView.as_view(), name="subscription"),
    path("plans", views.PlansView.as_view(), name="plans"),
    path("tenants/<str:tenant_id>/quotations", views.QuotationView.as_view(), name="quotation"),
    path(
        "tenants/<str:tenant_id>/saas-invoices/<str:invoice_id>/payment-submissions",
        views.PaymentSubmissionView.as_view(),
        name="payment-submission",
    ),
    # --- Platform admin (M2): izin platform, di luar konteks tenant (§5). ---
    path(
        "platform/payment-submissions",
        views.PlatformSubmissionListView.as_view(),
        name="platform-payment-submissions",
    ),
    path(
        "platform/payment-submissions/<str:submission_id>/approve",
        views.PlatformSubmissionApproveView.as_view(),
        name="platform-submission-approve",
    ),
    path(
        "platform/payment-submissions/<str:submission_id>/reject",
        views.PlatformSubmissionRejectView.as_view(),
        name="platform-submission-reject",
    ),
    path(
        "platform/payment-submissions/<str:submission_id>/request-revision",
        views.PlatformSubmissionRevisionView.as_view(),
        name="platform-submission-revision",
    ),
]
