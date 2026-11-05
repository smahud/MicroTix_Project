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
]
