from django.apps import AppConfig


class NetworkConfig(AppConfig):
    name = "domains.network"
    label = "network"

    def ready(self) -> None:
        # Registrasi handler job network (§6; kind tanpa handler ditolak).
        from domains.network import handlers  # noqa: F401 — register saat import
