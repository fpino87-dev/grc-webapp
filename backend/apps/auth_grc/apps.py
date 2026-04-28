from django.apps import AppConfig


class AuthGrcConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_grc"

    def ready(self):
        # Carica i signal handler (newfix S8 — revoca TrustedDevice su
        # cambio password).
        from . import signals  # noqa: F401

