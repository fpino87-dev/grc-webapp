from pathlib import Path
from datetime import timedelta

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # 2FA — ordine vincolato: otp_core prima dei plugin, two_factor dopo
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",  # backup codes monouso
    "two_factor",
    "formtools",                       # wizard multi-step (dipendenza two_factor)
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "django_celery_results",
    "drf_spectacular",
    "core",
    # GRC apps — aggiunte progressivamente:
    "apps.governance",
    "apps.plants",
    "apps.auth_grc",
    "apps.controls",
    "apps.assets",
    "apps.bia",
    "apps.risk",
    "apps.documents",
    "apps.tasks",
    "apps.incidents",
    "apps.audit_trail",
    "apps.pdca",
    "apps.lessons",
    "apps.management_review",
    "apps.suppliers",
    "apps.training",
    "apps.bcp",
    "apps.audit_prep",
    "apps.reporting",
    "apps.notifications",
    "apps.ai_engine",
    "apps.compliance_schedule",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",   # dopo AuthenticationMiddleware: aggiunge is_verified()
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": env.db("DATABASE_URL")}

CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
}}

CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Rome"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon":  "20/hour",
        "user":  "500/hour",
        "login": "5/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":    timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME":   timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":    True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN":        True,
    "AUTH_HEADER_TYPES":        ("Bearer",),
}

LANGUAGE_CODE = "it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True
LANGUAGES = [("it", "Italiano"), ("en", "English"), ("fr", "Français"), ("pl", "Polski"), ("tr", "Türkçe")]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [env("FRONTEND_URL", default="http://localhost:3000")]

# Punta il login al wizard 2FA di django-two-factor-auth (non al default /accounts/login/)
LOGIN_URL = "two_factor:login"
LOGOUT_REDIRECT_URL = "/"

CONN_MAX_AGE = 60

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

SESSION_COOKIE_SECURE   = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE      = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_HTTPONLY    = False   # Deve essere False: axios/fetch leggono il token via JS
CSRF_COOKIE_SAMESITE    = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

AI_ENGINE_CONFIG = {
    "enabled": env.bool("AI_ENGINE_ENABLED", default=False),
    "functions": {
        "classification": {"enabled": False, "model": "local"},
        "text_analysis": {"enabled": False, "model": "cloud"},
        "draft_generation": {"enabled": False, "model": "cloud"},
        "anomaly_detection": {"enabled": False, "model": "local"},
    },
    "sanitization": {
        "strip_plant_names": True,
        "strip_person_names": True,
        "strip_financial_values": True,
        "strip_ip_addresses": True,
    },
}
AI_LOCAL_ENDPOINT = env("AI_LOCAL_ENDPOINT", default="http://localhost:11434")
AI_LOCAL_MODEL = env("AI_LOCAL_MODEL", default="llama3.1:8b")
AI_CLOUD_PROVIDER = env("AI_CLOUD_PROVIDER", default="azure")

AUDIT_RETENTION = {
    "L1": env.int("AUDIT_TRAIL_RETENTION_L1_YEARS", default=5),
    "L2": env.int("AUDIT_TRAIL_RETENTION_L2_YEARS", default=3),
    "L3": env.int("AUDIT_TRAIL_RETENTION_L3_YEARS", default=1),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

FERNET_KEYS = [env("FERNET_KEY")]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process} {thread} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django":  {"handlers": ["console"], "level": "WARNING"},
        "apps":    {"handlers": ["console"], "level": "INFO"},
        "core":    {"handlers": ["console"], "level": "INFO"},
        "celery":  {"handlers": ["console"], "level": "WARNING"},
    },
}

