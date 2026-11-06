"""Konfigurasi app billing — penagihan internet M6 (TK-601)."""
from django.apps import AppConfig


class BillingConfig(AppConfig):
    name = "domains.billing"
    label = "billing"
