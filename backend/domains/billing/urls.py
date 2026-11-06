"""URL billing internet M6 (TK-601) — BIL-01/02/03/07."""
from django.urls import path

from domains.billing import views

urlpatterns = [
    # Paket penagihan (BIL-02)
    path("tenants/<str:tenant_id>/billing/packages", views.BillingPackageListView.as_view(), name="billing-packages"),
    path(
        "tenants/<str:tenant_id>/billing/packages/<str:package_id>",
        views.BillingPackageDetailView.as_view(),
        name="billing-package-detail",
    ),
    # Pasang paket ke layanan + add-on/diskon (BIL-07)
    path(
        "tenants/<str:tenant_id>/services/<str:service_id>/billing-package",
        views.ServiceBillingPackageView.as_view(),
        name="service-billing-package",
    ),
    path(
        "tenants/<str:tenant_id>/services/<str:service_id>/charges",
        views.ServiceChargeListView.as_view(),
        name="service-charges",
    ),
    path(
        "tenants/<str:tenant_id>/charges/<str:charge_id>",
        views.ServiceChargeDetailView.as_view(),
        name="service-charge-detail",
    ),
    # Invoice internet (BIL-01)
    path("tenants/<str:tenant_id>/invoices", views.InternetInvoiceListView.as_view(), name="internet-invoices"),
    path(
        "tenants/<str:tenant_id>/invoices/aging",
        views.InternetInvoiceAgingView.as_view(),
        name="internet-invoices-aging",
    ),
    path(
        "tenants/<str:tenant_id>/invoices/<str:invoice_id>",
        views.InternetInvoiceDetailView.as_view(),
        name="internet-invoice-detail",
    ),
    # Penerimaan pembayaran (BIL-03): GET daftar / POST catat pada path sama
    path("tenants/<str:tenant_id>/payments", views.InternetPaymentCollectionView.as_view(), name="internet-payments"),
    path(
        "tenants/<str:tenant_id>/payments/<str:payment_id>/verify",
        views.InternetPaymentVerifyView.as_view(),
        name="internet-payment-verify",
    ),
    path(
        "tenants/<str:tenant_id>/payments/<str:payment_id>/reject",
        views.InternetPaymentRejectView.as_view(),
        name="internet-payment-reject",
    ),
    path(
        "tenants/<str:tenant_id>/payments/<str:payment_id>",
        views.InternetPaymentDetailView.as_view(),
        name="internet-payment-detail",
    ),
]
