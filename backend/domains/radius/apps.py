from django.apps import AppConfig


class RadiusConfig(AppConfig):
    name = "domains.radius"
    label = "radius"

    def ready(self) -> None:
        """Proyeksi AccessAccount → radius.* dalam transaksi sama (§3).

        Receiver didefinisikan lokal di ready() → wajib weak=False:
        weakref default akan menstabilkan setelah ready() kembali (GC closure)
        dan proyeksi diam-diam berhenti bekerja.
        """
        from django.db.models.signals import post_delete, post_save

        from domains.customers.models import AccessAccount
        from domains.radius.projection import deproject_account, project_account

        def _reproject(sender, instance: AccessAccount, **kwargs) -> None:
            project_account(instance)

        def _deproject(sender, instance: AccessAccount, **kwargs) -> None:
            deproject_account(instance)

        post_save.connect(_reproject, sender=AccessAccount, dispatch_uid="radius_project_account", weak=False)
        post_delete.connect(_deproject, sender=AccessAccount, dispatch_uid="radius_deproject_account", weak=False)

        # Registrasi handler job cutover (idempoten per proses).
        from domains.radius.handlers import RadiusCutoverStepHandler

        from domains.jobs import engine

        if engine.handler_for(RadiusCutoverStepHandler.kind) is None:
            engine.register(RadiusCutoverStepHandler())
