from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = "domains.customers"
    label = "customers"
    verbose_name = "Pelanggan dan layanan"

    def ready(self) -> None:
        try:
            from domains.customers.handlers import register_handlers
        except Exception:  # pragma: no cover
            return
        register_handlers()
