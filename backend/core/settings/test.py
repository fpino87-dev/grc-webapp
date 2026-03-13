from .base import *  # noqa

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AI_ENGINE_CONFIG = {**AI_ENGINE_CONFIG, "enabled": False}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

