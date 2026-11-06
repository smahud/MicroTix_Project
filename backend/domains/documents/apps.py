"""Konfigurasi app documents — render dokumen PDF immutable (TK-109)."""
from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    name = "domains.documents"
    label = "documents"
