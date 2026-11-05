from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = "domains.customers"
    label = "customers"

    def ready(self) -> None:
        """Daftarkan handler job domain customers ke engine (§6).

        ValueError duplikat diabaikan — ready() dipanggil ulang saat autoreload.
        """
        from domains.customers import handlers
        from domains.jobs import engine

        for handler in handlers.HANDLERS:
            try:
                engine.register(handler)
            except ValueError:
                pass
