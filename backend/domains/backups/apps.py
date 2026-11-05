from django.apps import AppConfig


class BackupsConfig(AppConfig):
    name = "domains.backups"
    label = "backups"

    def ready(self) -> None:
        # Daftarkan handler job backup_run (ARCHITECTURE.md §6: handler ter-tipe
        # per kind; create_job menolak kind tanpa handler).
        from domains.backups.service import BackupRunHandler
        from domains.jobs import engine

        if engine.handler_for(BackupRunHandler.kind) is None:
            engine.register(BackupRunHandler())
