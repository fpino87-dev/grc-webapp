from .base import *
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["grc.azienda.com"])

# HSTS — 2 anni, includi sottodomini e preload
SECURE_HSTS_SECONDS            = 63072000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE    = True
SECURE_SSL_REDIRECT   = True

# Celery: usa Redis come result backend in produzione (evita contention su DB)
CELERY_RESULT_BACKEND = env("REDIS_URL") + "/1"
CELERY_RESULT_EXPIRES = 86400  # 24h in secondi

# --- Swagger/OpenAPI: disabilitato di default in produzione ---
# Impostare SHOW_API_DOCS=true in .env solo per ambienti staging/partner
SHOW_API_DOCS = env.bool("SHOW_API_DOCS", default=False)

# --- Admin URL personalizzato (sicurezza per obscurity, non sostituto di auth) ---
# Impostare ADMIN_URL in .env con path non predicibile, es. "grc-admin-<uuid>/"
ADMIN_URL = env("ADMIN_URL", default="admin/")

# --- Validazione FRONTEND_URL in produzione ---
_frontend_url = env("FRONTEND_URL", default=None)
if not _frontend_url:
    raise ImproperlyConfigured("FRONTEND_URL deve essere impostato in produzione.")
_parsed = urlparse(_frontend_url)
if not _parsed.scheme or not _parsed.netloc:
    raise ImproperlyConfigured("FRONTEND_URL deve essere un URL valido (es. https://grc.azienda.com).")
if _parsed.scheme not in ("http", "https"):
    raise ImproperlyConfigured("FRONTEND_URL deve usare schema http o https.")
CORS_ALLOWED_ORIGINS = [_frontend_url.rstrip("/")]

# Sentry: in produzione forziamo environment=production e sample rate più alto
# Il DSN e gli altri parametri sono già letti da env in base.py.
# Nessuna ulteriore configurazione necessaria — SENTRY_ENVIRONMENT=production in .env.

