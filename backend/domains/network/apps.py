from django.apps import AppConfig


class NetworkConfig(AppConfig):
    name = "domains.network"
    label = "network"

    def ready(self) -> None:
        # Registrasi handler job (idempoten; worker + test mengimpor ulang aman).
        try:
            from domains.network.handlers import register_handlers as _rh
        except Exception:  # pragma: no cover
            return
        _rh()
