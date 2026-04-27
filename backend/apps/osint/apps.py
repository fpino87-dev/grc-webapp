from django.apps import AppConfig


class OsintConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.osint"
    verbose_name = "OSINT Monitoring"

    def ready(self) -> None:  # pragma: no cover - solo setup
        # Importa i signal handlers (aggiornamento cache denormalizzata + sync).
        from . import signals  # noqa: F401
