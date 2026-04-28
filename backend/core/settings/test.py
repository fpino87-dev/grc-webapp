from .base import *  # noqa

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AI_ENGINE_CONFIG = {**AI_ENGINE_CONFIG, "enabled": False}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Esponi swagger nei test per esercitare il gating (newfix S13). In dev/prod
# il toggle viene da .env (SHOW_API_DOCS) o DEBUG=True.
SHOW_API_DOCS = True

# Disabilita throttling nei test con rate altissimi
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "9999/min",
        "user": "9999/min",
        "login": "9999/min",
    },
}

