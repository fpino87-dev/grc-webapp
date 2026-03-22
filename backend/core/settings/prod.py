from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["grc.azienda.com"])

SECURE_HSTS_SECONDS = 63072000  # 2 anni
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True

# Celery: usa Redis come result backend in produzione (evita contention su DB)
CELERY_RESULT_BACKEND = env("REDIS_URL") + "/1"
CELERY_RESULT_EXPIRES = 86400  # 24h in secondi

