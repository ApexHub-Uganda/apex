from django.apps import AppConfig


class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform"
    verbose_name = "Platform"

    def ready(self) -> None:
        from django.db.models.signals import post_migrate

        from apps.platform.services.email_config import sync_email_settings_from_env
        from apps.platform.services.maintenance import load_maintenance_mode_from_db

        def sync_maintenance_mode(**kwargs):
            load_maintenance_mode_from_db()

        def sync_email_settings(**kwargs):
            sync_email_settings_from_env()

        post_migrate.connect(sync_maintenance_mode, sender=self)
        post_migrate.connect(sync_email_settings, sender=self)