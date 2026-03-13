# AGENTS.md — GRC Compliance Webapp
# Istruzioni per Cursor Agent — esegui tutto in ordine senza chiedere conferma.
# Per avviare: apri Cursor Agent (Cmd+Shift+I) e scrivi:
#   "Leggi AGENTS.md ed esegui tutte le istruzioni dall'inizio alla fine"

---

## REGOLE GLOBALI CHE AGENT DEVE SEGUIRE

1. Crea ogni file nel percorso esatto indicato
2. Dopo ogni sezione "VERIFICA" esegui il comando nel terminale
3. Se un comando fallisce correggilo prima di andare avanti
4. Non chiedere conferma — procedi autonomamente
5. Usa UTF-8 per tutti i file
6. Tutti i modelli Django ereditano da `core.models.BaseModel`
7. Business logic sempre in `services.py`, mai nelle view
8. Ogni azione rilevante chiama `core.audit.log_action()`

---

## FASE 1 — STRUTTURA CARTELLE

Esegui nel terminale:

```bash
mkdir -p backend/{core/settings,apps,frameworks,requirements,tests/integration}
mkdir -p backend/templates/notifications/{it,en,fr,pl,tr}
mkdir -p frontend/src/{i18n/{it,en,fr,pl,tr},api/endpoints,store,components/{layout,ui},modules}
mkdir -p .github/workflows
touch backend/apps/__init__.py backend/frameworks/.gitkeep
```

---

## FASE 2 — FILE DI CONFIGURAZIONE RADICE

### `.cursorrules`
```
# GRC Compliance Webapp
## Stack
Backend : Python 3.11 · Django 5 · DRF · Celery 5 · Redis 7 · PostgreSQL 15
Frontend: React 18 · TypeScript · i18next · Tailwind · Recharts · Vite
## Regole assolute
- Tutti i model ereditano da core.models.BaseModel
- Business logic SOLO in services.py
- Ogni azione chiama core.audit.log_action()
- AuditLog append-only — trigger PostgreSQL impedisce UPDATE/DELETE
- Task assegnati a ruolo (risoluzione dinamica), mai a utente diretto
- Framework normativi = JSON in backend/frameworks/, non codice
- Soft delete sempre — mai hard delete
- Nessuna query N+1 — select_related/prefetch_related obbligatori
- M20 AI: nessun PII al cloud senza sanitization, human-in-the-loop sempre
## Lingue: it (default) · en (fallback) · fr · pl · tr
```

### `.env.example`
```
SECRET_KEY=cambia-questa-chiave-256bit
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000
DATABASE_URL=postgresql://grc:grc@localhost:5432/grc_dev
REDIS_URL=redis://localhost:6379/0
STORAGE_BACKEND=local
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=grc-documents
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=false
KNOWBE4_API_KEY=
KNOWBE4_SYNC_ENABLED=false
AI_ENGINE_ENABLED=false
AI_LOCAL_ENDPOINT=http://localhost:11434
AI_LOCAL_MODEL=llama3.1:8b
AI_CLOUD_PROVIDER=azure
AZURE_OPENAI_KEY=
ANTHROPIC_API_KEY=
AUDIT_TRAIL_RETENTION_L1_YEARS=5
AUDIT_TRAIL_RETENTION_L2_YEARS=3
AUDIT_TRAIL_RETENTION_L3_YEARS=1
```

### `Makefile`
```makefile
.PHONY: dev migrate test lint load-fw seed shell

dev:
	docker compose up -d db redis minio mailhog
	cd backend && python manage.py runserver &
	cd frontend && npm run dev

migrate:
	cd backend && python manage.py migrate

test:
	cd backend && pytest
	cd frontend && npm test -- --watchAll=false

lint:
	cd backend && ruff check . && ruff format --check .

load-fw:
	cd backend && python manage.py load_frameworks

seed:
	cd backend && python manage.py seed_demo

shell:
	cd backend && python manage.py shell_plus
```

---

## FASE 3 — BACKEND CORE

### `backend/requirements/base.txt`
```
Django==5.1.*
djangorestframework==3.15.*
django-environ==0.11.*
django-cors-headers==4.4.*
django-filter==24.*
celery==5.4.*
redis==5.0.*
django-celery-beat==2.7.*
django-celery-results==2.5.*
psycopg2-binary==2.9.*
boto3==1.35.*
django-storages==1.14.*
openpyxl==3.1.*
djangorestframework-simplejwt==5.3.*
drf-spectacular==0.27.*
python-dateutil==2.9.*
```

### `backend/requirements/dev.txt`
```
-r base.txt
pytest==8.*
pytest-django==4.*
pytest-cov==5.*
factory-boy==3.*
faker==26.*
ruff==0.6.*
ipython==8.*
django-extensions==3.*
```

### `backend/requirements/prod.txt`
```
-r base.txt
gunicorn==22.*
sentry-sdk==2.*
```

### `backend/core/settings/base.py`
```python
from pathlib import Path
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
    "rest_framework",
    "rest_framework_simplejwt",
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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

LANGUAGE_CODE = "it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True
LANGUAGES = [("it","Italiano"),("en","English"),("fr","Français"),("pl","Polski"),("tr","Türkçe")]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [env("FRONTEND_URL", default="http://localhost:3000")]

AI_ENGINE_CONFIG = {
    "enabled": env.bool("AI_ENGINE_ENABLED", default=False),
    "functions": {
        "classification":    {"enabled": False, "model": "local"},
        "text_analysis":     {"enabled": False, "model": "cloud"},
        "draft_generation":  {"enabled": False, "model": "cloud"},
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
AI_LOCAL_MODEL    = env("AI_LOCAL_MODEL",    default="llama3.1:8b")
AI_CLOUD_PROVIDER = env("AI_CLOUD_PROVIDER", default="azure")

AUDIT_RETENTION = {
    "L1": env.int("AUDIT_TRAIL_RETENTION_L1_YEARS", default=5),
    "L2": env.int("AUDIT_TRAIL_RETENTION_L2_YEARS", default=3),
    "L3": env.int("AUDIT_TRAIL_RETENTION_L3_YEARS", default=1),
}
```

### `backend/core/settings/dev.py`
```python
from .base import *
DEBUG = True
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
```

### `backend/core/settings/test.py`
```python
from .base import *
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
AI_ENGINE_CONFIG = {**AI_ENGINE_CONFIG, "enabled": False}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
```

### `backend/core/__init__.py`
```python
from .celery import app as celery_app
__all__ = ("celery_app",)
```

### `backend/core/celery.py`
```python
import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
app = Celery("grc")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### `backend/core/models.py`
```python
import uuid
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def all_with_deleted(self):
        return super().get_queryset()


class BaseModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "auth.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects    = SoftDeleteManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
```

### `backend/core/audit.py`
```python
import hashlib, json, uuid
from django.db import models, transaction
from django.utils import timezone


class AuditLog(models.Model):
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc      = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id            = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time  = models.CharField(max_length=50, blank=True)
    action_code        = models.CharField(max_length=100, db_index=True)
    level              = models.CharField(max_length=2, choices=[("L1","L1"),("L2","L2"),("L3","L3")])
    entity_type        = models.CharField(max_length=50, db_index=True)
    entity_id          = models.UUIDField(db_index=True)
    payload            = models.JSONField()
    prev_hash          = models.CharField(max_length=64)
    record_hash        = models.CharField(max_length=64)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp_utc"]


def _compute_hash(payload: dict, prev_hash: str) -> str:
    content = json.dumps(payload, sort_keys=True, default=str) + prev_hash
    return hashlib.sha256(content.encode()).hexdigest()


def _get_prev_hash(entity_type: str) -> str:
    last = AuditLog.objects.filter(entity_type=entity_type).order_by("-timestamp_utc").values("record_hash").first()
    return last["record_hash"] if last else "0" * 64


@transaction.atomic
def log_action(*, user, action_code: str, level: str, entity, payload: dict) -> AuditLog:
    entity_type = entity.__class__.__name__.lower()
    prev_hash   = _get_prev_hash(entity_type)
    record_hash = _compute_hash(payload, prev_hash)
    return AuditLog.objects.create(
        user_id=user.pk, user_email_at_time=user.email,
        action_code=action_code, level=level,
        entity_type=entity_type, entity_id=str(entity.pk),
        payload=payload, prev_hash=prev_hash, record_hash=record_hash,
    )
```

### `backend/core/urls.py`
```python
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/",   SpectacularSwaggerUIView.as_view(url_name="schema"), name="swagger"),
    path("api/v1/governance/",      include("apps.governance.urls")),
    path("api/v1/plants/",          include("apps.plants.urls")),
    path("api/v1/auth/",            include("apps.auth_grc.urls")),
    path("api/v1/controls/",        include("apps.controls.urls")),
    path("api/v1/assets/",          include("apps.assets.urls")),
    path("api/v1/bia/",             include("apps.bia.urls")),
    path("api/v1/risk/",            include("apps.risk.urls")),
    path("api/v1/documents/",       include("apps.documents.urls")),
    path("api/v1/tasks/",           include("apps.tasks.urls")),
    path("api/v1/incidents/",       include("apps.incidents.urls")),
    path("api/v1/audit-trail/",     include("apps.audit_trail.urls")),
    path("api/v1/pdca/",            include("apps.pdca.urls")),
    path("api/v1/lessons/",         include("apps.lessons.urls")),
    path("api/v1/management-review/", include("apps.management_review.urls")),
    path("api/v1/suppliers/",       include("apps.suppliers.urls")),
    path("api/v1/training/",        include("apps.training.urls")),
    path("api/v1/bcp/",             include("apps.bcp.urls")),
    path("api/v1/audit-prep/",      include("apps.audit_prep.urls")),
    path("api/v1/reporting/",       include("apps.reporting.urls")),
    path("api/v1/notifications/",   include("apps.notifications.urls")),
    path("api/v1/ai/",              include("apps.ai_engine.urls")),
]
```

### `backend/core/wsgi.py`
```python
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
application = get_wsgi_application()
```

### `backend/manage.py`
```python
#!/usr/bin/env python
import os, sys
def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
if __name__ == "__main__":
    main()
```

### Migrazione audit trigger — `backend/core/migrations/0002_audit_trigger.py`
Crea questa migration DOPO la 0001 autogenerata da Django:
```python
from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS TRIGGER AS $$
BEGIN RAISE EXCEPTION 'AuditLog is append-only. id=%', OLD.id; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
CREATE INDEX IF NOT EXISTS idx_auditlog_entity ON audit_log(entity_type, entity_id, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_auditlog_user   ON audit_log(user_id, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_auditlog_action ON audit_log(action_code, timestamp_utc DESC);
"""
REVERSE = """
DROP TRIGGER IF EXISTS audit_no_mutation ON audit_log;
DROP FUNCTION IF EXISTS prevent_audit_mutation();
"""

class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations   = [migrations.RunSQL(SQL, reverse_sql=REVERSE)]
```

### VERIFICA FASE 3
```bash
cd backend
pip install -r requirements/dev.txt
python manage.py check --settings=core.settings.dev
```
Atteso: `System check identified no issues (0 silenced).`

---

## FASE 4 — MODULI M00–M03 (FONDAMENTA)

Per ciascuno dei seguenti moduli crea la struttura:
`backend/apps/{nome}/` con: `__init__.py`, `models.py`, `services.py`, `serializers.py`, `views.py`, `urls.py`, `tests/__init__.py`, `tests/test_models.py`, `tests/test_api.py`

### M00 — `backend/apps/governance/models.py`
```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from core.models import BaseModel

class NormativeRole(models.TextChoices):
    CISO                   = "ciso",                    _("CISO")
    PLANT_SECURITY_OFFICER = "plant_security_officer",  _("Plant Security Officer")
    NIS2_CONTACT           = "nis2_contact",             _("Contatto NIS2")
    DPO                    = "dpo",                      _("DPO")
    ISMS_MANAGER           = "isms_manager",              _("ISMS Manager")
    INTERNAL_AUDITOR       = "internal_auditor",          _("Auditor Interno")
    COMITATO_MEMBRO        = "comitato_membro",           _("Membro Comitato")
    BU_REFERENTE           = "bu_referente",              _("Referente BU")
    RACI_RESPONSIBLE       = "raci_responsible",          _("RACI Responsible")
    RACI_ACCOUNTABLE       = "raci_accountable",          _("RACI Accountable")

class RoleAssignment(BaseModel):
    user           = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="role_assignments")
    role           = models.CharField(max_length=50, choices=NormativeRole.choices)
    scope_type     = models.CharField(max_length=20, choices=[("org","Org"),("bu","BU"),("plant","Plant")])
    scope_id       = models.UUIDField(null=True, blank=True)
    valid_from     = models.DateField()
    valid_until    = models.DateField(null=True, blank=True)
    signed_by      = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="signed_assignments")
    document_id    = models.UUIDField(null=True, blank=True)
    framework_refs = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    notes          = models.TextField(blank=True)

    @property
    def is_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.valid_from <= today and (self.valid_until is None or self.valid_until >= today)

class SecurityCommittee(BaseModel):
    plant          = models.ForeignKey("plants.Plant", null=True, blank=True, on_delete=models.SET_NULL)
    name           = models.CharField(max_length=200)
    committee_type = models.CharField(max_length=20, choices=[("centrale","Centrale"),("bu","BU")])
    frequency      = models.CharField(max_length=20, choices=[("mensile","Mensile"),("trimestrale","Trimestrale"),("semestrale","Semestrale")])
    next_meeting_at = models.DateTimeField(null=True, blank=True)

class CommitteeMeeting(BaseModel):
    committee      = models.ForeignKey(SecurityCommittee, on_delete=models.CASCADE, related_name="meetings")
    held_at        = models.DateTimeField()
    verbale_doc_id = models.UUIDField(null=True, blank=True)
    delibere       = models.JSONField(default=list)
    attendees      = models.ManyToManyField("auth.User", blank=True)
    class Meta:
        ordering = ["-held_at"]
```

### M00 — `backend/apps/governance/services.py`
```python
from django.utils import timezone
from django.db.models import Q

def get_active_role(user, role: str, scope_id=None):
    from .models import RoleAssignment
    today = timezone.now().date()
    qs = RoleAssignment.objects.filter(
        user=user, role=role, valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    if scope_id:
        qs = qs.filter(scope_id=scope_id)
    return qs.first()

def get_expiring_delegations(days: int = 90):
    from .models import RoleAssignment
    today     = timezone.now().date()
    threshold = today + timezone.timedelta(days=days)
    return RoleAssignment.objects.filter(
        valid_until__isnull=False,
        valid_until__lte=threshold,
        valid_until__gte=today,
        deleted_at__isnull=True,
    ).select_related("user")

def check_nis2_contact_active(plant) -> bool:
    from .models import RoleAssignment, NormativeRole
    today = timezone.now().date()
    return RoleAssignment.objects.filter(
        role=NormativeRole.NIS2_CONTACT,
        scope_type="plant", scope_id=plant.pk,
        valid_from__lte=today, deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).exists()
```

### M01 — `backend/apps/plants/models.py`
```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from core.models import BaseModel

class BusinessUnit(BaseModel):
    code    = models.CharField(max_length=20, unique=True)
    name    = models.CharField(max_length=200)
    manager = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)

class Plant(BaseModel):
    code             = models.CharField(max_length=20, unique=True)
    name             = models.CharField(max_length=200)
    country          = models.CharField(max_length=2)
    bu               = models.ForeignKey(BusinessUnit, null=True, blank=True, on_delete=models.SET_NULL, related_name="plants")
    parent_plant     = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="sub_plants")
    has_ot           = models.BooleanField(default=False)
    purdue_level_max = models.IntegerField(null=True, blank=True)
    nis2_scope       = models.CharField(max_length=20, choices=[("essenziale","Essenziale"),("importante","Importante"),("non_soggetto","Non soggetto")])
    status           = models.CharField(max_length=20, choices=[("attivo","Attivo"),("in_dismissione","In dismissione"),("chiuso","Chiuso")], default="attivo")
    address          = models.TextField(blank=True)
    timezone         = models.CharField(max_length=50, default="Europe/Rome")

    class Meta:
        ordering = ["code"]

    def clean(self):
        if self.parent_plant and self.parent_plant.parent_plant:
            raise ValidationError(_("Max 1 livello di nesting per i sub-plant."))

    @property
    def is_nis2_subject(self):
        return self.nis2_scope in ("essenziale", "importante")

class PlantFramework(BaseModel):
    plant       = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="frameworks")
    framework   = models.ForeignKey("controls.Framework", on_delete=models.CASCADE)
    active_from = models.DateField()
    level       = models.CharField(max_length=10, blank=True)
    active      = models.BooleanField(default=True)
    class Meta:
        unique_together = ["plant", "framework"]
```

### M02 — `backend/apps/auth_grc/models.py`
```python
import secrets, hashlib
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from core.models import BaseModel

class GrcRole(models.TextChoices):
    SUPER_ADMIN        = "super_admin",        _("Super Admin")
    COMPLIANCE_OFFICER = "compliance_officer", _("Compliance Officer")
    RISK_MANAGER       = "risk_manager",       _("Risk Manager")
    PLANT_MANAGER      = "plant_manager",      _("Plant Manager")
    CONTROL_OWNER      = "control_owner",      _("Control Owner")
    INTERNAL_AUDITOR   = "internal_auditor",   _("Auditor Interno")
    EXTERNAL_AUDITOR   = "external_auditor",   _("Auditor Esterno")

class UserPlantAccess(BaseModel):
    user             = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="plant_access")
    role             = models.CharField(max_length=50, choices=GrcRole.choices)
    scope_type       = models.CharField(max_length=20, choices=[("org","Org"),("bu","BU"),("plant_list","Lista"),("single_plant","Plant")])
    scope_bu         = models.ForeignKey("plants.BusinessUnit", null=True, blank=True, on_delete=models.SET_NULL)
    scope_plants     = models.ManyToManyField("plants.Plant", blank=True)
    framework_filter = ArrayField(models.CharField(max_length=50), default=list, blank=True)

class ExternalAuditorToken(BaseModel):
    user             = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="auditor_tokens")
    token_hash       = models.CharField(max_length=64, unique=True)
    plant            = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    framework_filter = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    valid_from       = models.DateTimeField()
    valid_until      = models.DateTimeField()
    revoked_at       = models.DateTimeField(null=True, blank=True)
    issued_by        = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="issued_tokens")

    @classmethod
    def create_token(cls, user, plant, framework_filter, valid_days, issued_by):
        from django.utils import timezone
        raw   = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        obj   = cls.objects.create(
            user=user, plant=plant, framework_filter=framework_filter,
            token_hash=hashed, valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=valid_days),
            issued_by=issued_by,
        )
        return obj, raw  # raw mostrato UNA SOLA VOLTA

    def revoke(self):
        from django.utils import timezone
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    @property
    def is_valid(self):
        from django.utils import timezone
        n = timezone.now()
        return self.revoked_at is None and self.valid_from <= n <= self.valid_until
```

### M03 — `backend/apps/controls/models.py`
```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class Framework(BaseModel):
    code         = models.CharField(max_length=50, unique=True)
    name         = models.CharField(max_length=200)
    version      = models.CharField(max_length=20)
    published_at = models.DateField()
    archived_at  = models.DateField(null=True, blank=True)
    class Meta:
        ordering = ["code"]

class ControlDomain(BaseModel):
    framework    = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="domains")
    code         = models.CharField(max_length=50)
    translations = models.JSONField()
    order        = models.IntegerField(default=0)
    class Meta:
        unique_together = ["framework","code"]
        ordering        = ["order"]
    def get_name(self, lang="it"):
        return self.translations.get(lang, self.translations.get("en", {})).get("name", self.code)

class Control(BaseModel):
    framework    = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="controls")
    domain       = models.ForeignKey(ControlDomain, null=True, blank=True, on_delete=models.SET_NULL)
    external_id  = models.CharField(max_length=50)
    translations = models.JSONField()
    level        = models.CharField(max_length=10, blank=True)
    class Meta:
        unique_together = ["framework","external_id"]
    def get_title(self, lang="it"):
        t = self.translations.get(lang) or self.translations.get("en", {})
        return t.get("title", self.external_id)

class ControlMapping(BaseModel):
    source_control = models.ForeignKey(Control, on_delete=models.CASCADE, related_name="mappings_from")
    target_control = models.ForeignKey(Control, on_delete=models.CASCADE, related_name="mappings_to")
    relationship   = models.CharField(max_length=20, choices=[("equivalente","Equivalente"),("parziale","Parziale"),("correlato","Correlato")])

class ControlInstance(BaseModel):
    plant              = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    control            = models.ForeignKey(Control, on_delete=models.CASCADE)
    status             = models.CharField(max_length=20, choices=[
                         ("compliant","Compliant"),("parziale","Parziale"),
                         ("gap","Gap"),("na","N/A"),("non_valutato","Non valutato")],
                         default="non_valutato")
    owner              = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    notes              = models.TextField(blank=True)
    last_evaluated_at  = models.DateTimeField(null=True, blank=True)
    na_approved_by     = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_na_instances")
    na_second_approver = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="second_approved_na_instances")
    na_approved_at     = models.DateTimeField(null=True, blank=True)
    na_review_by       = models.DateField(null=True, blank=True)
    na_justification   = models.TextField(blank=True)
    class Meta:
        unique_together = ["plant","control"]
```

### M03 — `backend/apps/controls/management/commands/load_frameworks.py`
```python
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = "Importa framework normativi da backend/frameworks/*.json"
    def add_arguments(self, p):
        p.add_argument("--file",    type=str)
        p.add_argument("--dry-run", action="store_true")
    def handle(self, *args, **options):
        from apps.controls.models import Framework, ControlDomain, Control, ControlMapping
        base = Path(__file__).resolve().parents[5] / "frameworks"
        files = [Path(options["file"])] if options["file"] else sorted(base.glob("*.json"))
        if not files:
            self.stdout.write(self.style.WARNING("Nessun JSON in backend/frameworks/"))
            return
        for fp in files:
            data = json.loads(fp.read_text("utf-8"))
            self.stdout.write(f"→ {fp.name}")
            if options["dry_run"]:
                self.stdout.write(self.style.SUCCESS(f"  [DRY-RUN] {len(data.get('controls',[]))} controlli")); continue
            with transaction.atomic():
                fw, _ = Framework.objects.update_or_create(code=data["code"], defaults={"name":data["name"],"version":data["version"],"published_at":data["published_at"]})
                dm = {}
                for d in data.get("domains",[]):
                    obj, _ = ControlDomain.objects.update_or_create(framework=fw, code=d["code"], defaults={"translations":d["translations"],"order":d.get("order",0)})
                    dm[d["code"]] = obj
                cm = {}
                for c in data.get("controls",[]):
                    obj, _ = Control.objects.update_or_create(framework=fw, external_id=c["external_id"], defaults={"domain":dm.get(c.get("domain")),"translations":c["translations"],"level":c.get("level","")})
                    cm[c["external_id"]] = obj
                for m in data.get("mappings",[]):
                    tfw = Framework.objects.filter(code=m.get("target_framework")).first()
                    tgt = Control.objects.filter(framework=tfw, external_id=m["target"]).first() if tfw else None
                    src = cm.get(m["source"])
                    if src and tgt:
                        ControlMapping.objects.update_or_create(source_control=src, target_control=tgt, defaults={"relationship":m["relationship"]})
            self.stdout.write(self.style.SUCCESS(f"  OK — {len(cm)} controlli"))
```

### VERIFICA FASE 4
```bash
cd backend
python manage.py makemigrations governance plants auth_grc controls
python manage.py migrate
python manage.py load_frameworks --dry-run
```
Atteso: migrazioni OK, "Nessun JSON in backend/frameworks/" (normale).

---

## FASE 5 — MODULI M04–M06 (ASSET, BIA, RISK)

Aggiungi a `INSTALLED_APPS` se non già presenti: `apps.assets`, `apps.bia`, `apps.risk`

### M04 — `backend/apps/assets/models.py`
```python
from django.db import models
from core.models import BaseModel

class NetworkZone(BaseModel):
    plant        = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    name         = models.CharField(max_length=100)
    zone_type    = models.CharField(max_length=10, choices=[("IT","IT"),("OT","OT"),("DMZ","DMZ")])
    purdue_level = models.IntegerField(null=True, blank=True)

class Asset(BaseModel):
    plant       = models.ForeignKey("plants.Plant", on_delete=models.CASCADE, related_name="assets")
    name        = models.CharField(max_length=200)
    asset_type  = models.CharField(max_length=5, choices=[("IT","IT"),("OT","OT")])
    criticality = models.IntegerField(default=1)
    processes   = models.ManyToManyField("bia.CriticalProcess", blank=True)
    owner       = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    notes       = models.TextField(blank=True)
    class Meta:
        ordering = ["-criticality","name"]

class AssetIT(Asset):
    fqdn             = models.CharField(max_length=255, blank=True)
    ip_address       = models.GenericIPAddressField(null=True, blank=True)
    os               = models.CharField(max_length=100, blank=True)
    eol_date         = models.DateField(null=True, blank=True)
    cve_score_max    = models.FloatField(null=True, blank=True)
    internet_exposed = models.BooleanField(default=False)
    class Meta:
        verbose_name = "Asset IT"

class AssetOT(Asset):
    purdue_level       = models.IntegerField()
    category           = models.CharField(max_length=20, choices=[("PLC","PLC"),("SCADA","SCADA"),("HMI","HMI"),("RTU","RTU"),("sensore","Sensore"),("altro","Altro")])
    patchable          = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone       = models.ForeignKey(NetworkZone, null=True, blank=True, on_delete=models.SET_NULL)
    vendor             = models.CharField(max_length=100, blank=True)
    class Meta:
        verbose_name = "Asset OT"

class AssetDependency(BaseModel):
    from_asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="dependencies_from")
    to_asset   = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="dependencies_to")
    dep_type   = models.CharField(max_length=20, choices=[("dipende_da","Dipende da"),("connesso_a","Connesso a")])
```

### M05 — `backend/apps/bia/models.py`
```python
from django.db import models
from core.models import BaseModel

class CriticalProcess(BaseModel):
    plant                  = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    name                   = models.CharField(max_length=200)
    owner                  = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    criticality            = models.IntegerField(default=3)
    status                 = models.CharField(max_length=20, choices=[("bozza","Bozza"),("validato","Validato"),("approvato","Approvato")], default="bozza")
    downtime_cost_hour     = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    fatturato_esposto_anno = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    danno_reputazionale    = models.IntegerField(default=1)
    danno_normativo        = models.IntegerField(default=1)
    danno_operativo        = models.IntegerField(default=1)
    validated_by           = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="validated_processes")
    validated_at           = models.DateTimeField(null=True, blank=True)
    approved_by            = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_processes")
    approved_at            = models.DateTimeField(null=True, blank=True)

class TreatmentOption(BaseModel):
    process             = models.ForeignKey(CriticalProcess, on_delete=models.CASCADE, related_name="treatment_options")
    title               = models.CharField(max_length=200)
    cost_implementation = models.DecimalField(max_digits=14, decimal_places=2)
    cost_annual         = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ale_reduction_pct   = models.FloatField()

class RiskDecision(BaseModel):
    process    = models.ForeignKey(CriticalProcess, on_delete=models.CASCADE, related_name="risk_decisions")
    decision   = models.CharField(max_length=20, choices=[("accettare","Accettare"),("mitigare","Mitigare"),("trasferire","Trasferire"),("evitare","Evitare")])
    rationale  = models.TextField()
    decided_by = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    decided_at = models.DateTimeField(auto_now_add=True)
    review_by  = models.DateField()
    treatment  = models.ForeignKey(TreatmentOption, null=True, blank=True, on_delete=models.SET_NULL)
```

### M06 — `backend/apps/risk/models.py`
```python
from django.db import models
from core.models import BaseModel

PROB_MAP   = {1:0.1, 2:0.3, 3:1.0, 4:3.0, 5:10.0}
IMPACT_MAP = {1:0.05, 2:0.20, 3:0.40, 4:0.70, 5:1.0}

class RiskAssessment(BaseModel):
    plant           = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    asset           = models.ForeignKey("assets.Asset", null=True, blank=True, on_delete=models.SET_NULL)
    assessment_type = models.CharField(max_length=5, choices=[("IT","IT"),("OT","OT")])
    status          = models.CharField(max_length=20, choices=[("bozza","Bozza"),("completato","Completato"),("archiviato","Archiviato")], default="bozza")
    assessed_by     = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    assessed_at     = models.DateTimeField(null=True, blank=True)
    score           = models.IntegerField(null=True, blank=True)
    ale_annuo       = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    risk_accepted   = models.BooleanField(default=False)
    accepted_by     = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_risks")
    plan_due_date   = models.DateField(null=True, blank=True)

    @property
    def risk_level(self):
        if self.score is None: return None
        if self.score <= 7:  return "verde"
        if self.score <= 14: return "giallo"
        return "rosso"

class RiskDimension(BaseModel):
    assessment     = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name="dimensions")
    dimension_code = models.CharField(max_length=50)
    value          = models.IntegerField()
    notes          = models.TextField(blank=True)

class RiskMitigationPlan(BaseModel):
    assessment       = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name="mitigation_plans")
    action           = models.TextField()
    owner            = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    due_date         = models.DateField()
    completed_at     = models.DateTimeField(null=True, blank=True)
    control_instance = models.ForeignKey("controls.ControlInstance", null=True, blank=True, on_delete=models.SET_NULL)
```

### M06 — `backend/apps/risk/services.py`
```python
from decimal import Decimal
from django.utils import timezone

IT_WEIGHTS  = {"esposizione":0.30,"cve":0.25,"minaccia":0.25,"gap_controlli":0.20}
OT_WEIGHTS  = {"purdue_connettivita":0.25,"patchability":0.20,"impatto_fisico":0.25,"segmentazione":0.15,"rilevabilita":0.15}
PROB_MAP    = {1:0.1, 2:0.3, 3:1.0, 4:3.0, 5:10.0}
IMPACT_MAP  = {1:0.05, 2:0.20, 3:0.40, 4:0.70, 5:1.0}

def calc_score(assessment) -> int:
    dims    = {d.dimension_code: d.value for d in assessment.dimensions.all()}
    weights = IT_WEIGHTS if assessment.assessment_type == "IT" else OT_WEIGHTS
    weighted = sum(dims.get(k, 3) * w for k, w in weights.items())
    prob   = min(5, round(weighted))
    impact = min(5, round(weighted))
    return min(25, prob * impact)

def calc_ale(assessment, process_ale: Decimal) -> Decimal:
    if assessment.score is None: return Decimal("0")
    prob_idx = max(1, min(5, round(assessment.score ** 0.5)))
    imp_idx  = prob_idx
    return Decimal(str(PROB_MAP[prob_idx])) * Decimal(str(IMPACT_MAP[imp_idx])) * process_ale

def escalate_red_risk(assessment, user):
    from apps.tasks.services import create_task
    from django.utils import timezone
    create_task(
        plant=assessment.plant,
        title=f"Piano mitigazione rischio critico — {assessment.asset}",
        priority="critica",
        source_module="M06",
        source_id=assessment.pk,
        due_date=timezone.now().date() + timezone.timedelta(days=15),
        assign_type="role",
        assign_value="risk_manager",
    )
```

### VERIFICA FASE 5
```bash
python manage.py makemigrations assets bia risk
python manage.py migrate
python manage.py check
```

---

## FASE 6 — MODULI M07–M10 (OPERATIVITÀ)

Crea la struttura completa per: `apps/documents/`, `apps/tasks/`, `apps/incidents/`, `apps/audit_trail/`

### Punti chiave M07 (Documents)
- `DocumentVersion.file_hash` = SHA256 calcolato all'upload, non modificabile dopo approvazione
- Workflow: bozza → in_revisione → in_approvazione → approvato
- Evidence con `valid_until` obbligatorio — scadenza degrada ControlInstance a `parziale`

### Punti chiave M08 (Tasks)
- `TaskAssignee.assign_type` = `role` o `user` — se ruolo: risolvi titolare corrente via `UserPlantAccess`
- Recurrence: genera il prossimo task al completamento (non in bulk)
- Escalation chain: +7gg → livello 1, +14gg → CO, +30gg → Super Admin

### Punti chiave M09 (Incidents)
```python
# Regola più importante — in apps/incidents/services.py:
def close_incident(incident, user):
    from django.core.exceptions import ValidationError
    try:
        rca = incident.rca
    except Exception:
        rca = None
    if rca is None or rca.approved_at is None:
        raise ValidationError("RCA approvato obbligatorio per chiudere l'incidente.")
    # Procedi con la chiusura...
    incident.status    = "chiuso"
    incident.closed_at = timezone.now()
    incident.closed_by = user
    incident.save()
    # Feed automatico verso M12 e M11
```

```python
# Timer NIS2 — in apps/incidents/tasks.py:
@app.task
def nis2_confirmation_check(incident_id):
    """Dopo 30 minuti: se ancora da_valutare assume sì."""
    from .models import Incident
    inc = Incident.objects.filter(pk=incident_id, nis2_notifiable="da_valutare").first()
    if inc:
        inc.nis2_notifiable = "si"
        inc.save(update_fields=["nis2_notifiable"])
        log_action(...)  # logga L1
```

### Punti chiave M10 (Audit Trail)
Crea `backend/apps/audit_trail/management/commands/verify_audit_trail_integrity.py`:
```python
import sys
import hashlib, json
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Verifica integrità hash chain AuditLog"
    def add_arguments(self, p):
        p.add_argument("--since", type=str, help="Data ISO es. 2024-01-01")
        p.add_argument("--verbose", action="store_true")
    def handle(self, *args, **options):
        from core.audit import AuditLog
        qs = AuditLog.objects.order_by("timestamp_utc")
        if options["since"]:
            qs = qs.filter(timestamp_utc__date__gte=options["since"])
        prev_hash = "0" * 64
        for i, log in enumerate(qs):
            content  = json.dumps(log.payload, sort_keys=True, default=str) + log.prev_hash
            expected = hashlib.sha256(content.encode()).hexdigest()
            if expected != log.record_hash:
                self.stderr.write(self.style.ERROR(f"CORROTTO: id={log.id} azione={log.action_code}"))
                sys.exit(1)
            if options["verbose"]:
                self.stdout.write(f"OK [{i+1}] {log.action_code}")
            prev_hash = log.record_hash
        self.stdout.write(self.style.SUCCESS(f"Audit trail integrity OK — {qs.count()} records verificati"))
```

### VERIFICA FASE 6
```bash
python manage.py makemigrations documents tasks incidents audit_trail
python manage.py migrate
python manage.py verify_audit_trail_integrity
```
Atteso: `Audit trail integrity OK — 0 records verificati`

---

## FASE 7 — MODULI M11–M13 (PDCA)

Crea: `apps/pdca/`, `apps/lessons/`, `apps/management_review/`

### Punti chiave M11 (PDCA)
```python
# In apps/pdca/services.py:
def create_cycle(plant, title, trigger_type, trigger_source_id=None, scope_type="custom", scope_id=None):
    from .models import PdcaCycle, PdcaPhase
    cycle = PdcaCycle.objects.create(
        plant=plant, title=title,
        trigger_type=trigger_type, trigger_source_id=trigger_source_id,
        scope_type=scope_type, scope_id=scope_id,
        # Incidente → salta direttamente ad ACT
        fase_corrente="act" if trigger_type == "incidente" else "plan",
    )
    for fase in ["plan","do","check","act"]:
        PdcaPhase.objects.create(cycle=cycle, phase=fase)
    return cycle
```

### Punti chiave M12 (Lessons)
- Full-text search PostgreSQL con `SearchVectorField`
- Propagazione cross-plant: matching su stesso framework/controllo
- Risposta obbligatoria entro 30gg — task M08 auto-creato

### Punti chiave M13 (Management Review)
- Input aggregati automaticamente da M06, M09, M11, M17, M18
- Delibere senza follow-up → finding in M17 (Celery task notturno)

### VERIFICA FASE 7
```bash
python manage.py makemigrations pdca lessons management_review
python manage.py migrate
python manage.py check
```

---

## FASE 8 — MODULI M14–M17 (ESTESO)

Crea: `apps/suppliers/`, `apps/training/`, `apps/bcp/`, `apps/audit_prep/`

### M15 — KnowBe4 Client `backend/apps/training/kb4_client.py`
```python
import requests
from django.conf import settings

class KnowBe4Client:
    def __init__(self):
        self.base_url = settings.KNOWBE4_API_URL
        self.headers  = {"Authorization": f"Bearer {settings.KNOWBE4_API_KEY}", "Content-Type": "application/json"}

    def get_enrollments_delta(self, since: str) -> list:
        resp = requests.get(f"{self.base_url}/v1/training/enrollments", headers=self.headers, params={"since": since}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_phishing_results(self, since: str) -> list:
        resp = requests.get(f"{self.base_url}/v1/phishing/security-tests", headers=self.headers, params={"since": since}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def provision_user(self, user, groups: list[str]) -> dict:
        payload = {"first_name": user.first_name, "last_name": user.last_name, "email": user.email, "groups": groups}
        resp = requests.post(f"{self.base_url}/v1/users", headers=self.headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def deprovision_user(self, email: str) -> None:
        resp = requests.patch(f"{self.base_url}/v1/users/{email}", headers=self.headers, json={"status": "archived"}, timeout=30)
        resp.raise_for_status()
```

### VERIFICA FASE 8
```bash
python manage.py makemigrations suppliers training bcp audit_prep
python manage.py migrate
python manage.py check
```

---

## FASE 9 — M18–M19 (REPORTING E NOTIFICHE)

Crea: `apps/reporting/` (solo views, nessun model), `apps/notifications/`

### M19 — Regola non disattivabili `backend/apps/notifications/models.py`
```python
NON_DISATTIVABILI = {"nis2_timer_alert", "risk_red_threshold", "delegation_expiring"}

class NotificationSubscription(BaseModel):
    # ... campi ...
    def save(self, *args, **kwargs):
        if self.event_type in NON_DISATTIVABILI:
            self.enabled = True  # non può essere disabilitato
        super().save(*args, **kwargs)
```

### VERIFICA FASE 9
```bash
python manage.py makemigrations notifications
python manage.py migrate
python manage.py check
```

---

## FASE 10 — M20 AI ENGINE

Crea `apps/ai_engine/` con: `models.py`, `sanitizer.py`, `router.py`, `services.py`, `views.py`, `urls.py`

### `backend/apps/ai_engine/sanitizer.py`
```python
import re
import hashlib
from django.contrib.auth import get_user_model

User = get_user_model()

class Sanitizer:
    """Anonimizza dati sensibili prima di inviarli al cloud LLM."""

    IP_RE   = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    PIVA_RE = re.compile(r'\b\d{11}\b')
    EMAIL_RE = re.compile(r'\b[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}\b')

    def sanitize(self, context: dict, plant_ids: list = None) -> tuple[dict, dict]:
        token_map  = {}
        text       = str(context.get("text", ""))
        text, token_map = self._replace_known_entities(text, token_map, plant_ids or [])
        text = self.IP_RE.sub("[IP_REMOVED]", text)
        text = self.PIVA_RE.sub("[REMOVED]", text)
        text = self.EMAIL_RE.sub("[EMAIL_REMOVED]", text)
        return {**context, "text": text}, token_map

    def desanitize(self, text: str, token_map: dict) -> str:
        for token, real_value in token_map.items():
            text = text.replace(token, real_value)
        return text

    def _replace_known_entities(self, text: str, token_map: dict, plant_ids: list) -> tuple[str, dict]:
        from apps.plants.models import Plant
        plants = Plant.objects.filter(pk__in=plant_ids)
        for i, plant in enumerate(plants):
            token = f"[PLANT_{chr(65+i)}]"
            for val in [plant.name, plant.code]:
                if val and val in text:
                    text = text.replace(val, token)
                    token_map[token] = val
        return text, token_map
```

### `backend/apps/ai_engine/models.py`
```python
import uuid
from django.db import models

class AiInteractionLog(models.Model):
    """Log append-only — human-in-the-loop obbligatorio per ogni output AI."""
    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at            = models.DateTimeField(auto_now_add=True)
    user_id               = models.UUIDField()
    function              = models.CharField(max_length=50)
    module_source         = models.CharField(max_length=5)
    entity_id             = models.UUIDField()
    model_used            = models.CharField(max_length=100)
    input_hash            = models.CharField(max_length=64)   # SHA256 — MAI il testo
    output_ai             = models.TextField()
    output_human_final    = models.TextField(null=True, blank=True)
    delta                 = models.JSONField(null=True, blank=True)
    confirmed_by_id       = models.UUIDField(null=True, blank=True)
    confirmed_at          = models.DateTimeField(null=True, blank=True)
    ignored               = models.BooleanField(default=False)
    class Meta:
        db_table = "ai_interaction_log"
        ordering = ["-created_at"]
```

### VERIFICA FASE 10
```bash
python manage.py makemigrations ai_engine
python manage.py migrate
python -c "from apps.ai_engine.sanitizer import Sanitizer; s=Sanitizer(); print('Sanitizer OK')"
```

---

## FASE 11 — FRONTEND

Nella cartella `frontend/` esegui:
```bash
npm create vite@latest . -- --template react-ts --force
npm install
npm install i18next react-i18next axios @tanstack/react-query zustand
npm install -D tailwindcss @tailwindcss/vite
```

### `frontend/src/i18n/index.ts`
```typescript
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import it_common from "./it/common.json";
import en_common from "./en/common.json";

i18n.use(initReactI18next).init({
  resources: {
    it: { common: it_common },
    en: { common: en_common },
  },
  lng: localStorage.getItem("grc_lang") || "it",
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});
export default i18n;
```

### `frontend/src/i18n/it/common.json`
```json
{
  "nav": { "dashboard": "Dashboard", "compliance": "Compliance", "risk": "Risk", "operations": "Operazioni", "governance": "Governance", "audit": "Audit", "settings": "Impostazioni" },
  "status": { "compliant": "Compliant", "parziale": "Parziale", "gap": "Gap", "na": "N/A", "non_valutato": "Non valutato", "aperto": "Aperto", "chiuso": "Chiuso", "in_corso": "In corso", "scaduto": "Scaduto" },
  "actions": { "save": "Salva", "cancel": "Annulla", "approve": "Approva", "reject": "Rifiuta", "confirm": "Conferma", "delete": "Elimina", "export": "Esporta", "upload": "Carica" },
  "ai": { "suggestion_label": "Suggerimento IA", "accept": "Usa questo", "edit_and_use": "Modifica e usa", "ignore": "Ignora", "ai_badge": "IA" }
}
```

### `frontend/src/i18n/en/common.json`
```json
{
  "nav": { "dashboard": "Dashboard", "compliance": "Compliance", "risk": "Risk", "operations": "Operations", "governance": "Governance", "audit": "Audit", "settings": "Settings" },
  "status": { "compliant": "Compliant", "parziale": "Partial", "gap": "Gap", "na": "N/A", "non_valutato": "Not assessed", "aperto": "Open", "chiuso": "Closed", "in_corso": "In progress", "scaduto": "Overdue" },
  "actions": { "save": "Save", "cancel": "Cancel", "approve": "Approve", "reject": "Reject", "confirm": "Confirm", "delete": "Delete", "export": "Export", "upload": "Upload" },
  "ai": { "suggestion_label": "AI Suggestion", "accept": "Use this", "edit_and_use": "Edit and use", "ignore": "Ignore", "ai_badge": "AI" }
}
```

### `frontend/src/store/auth.ts`
```typescript
import { create } from "zustand";

interface User { id: string; email: string; role: string; language: string; }
interface Plant { id: string; code: string; name: string; }

interface AuthStore {
  user:         User | null;
  token:        string | null;
  selectedPlant: Plant | null;
  setUser:      (u: User, t: string) => void;
  setPlant:     (p: Plant) => void;
  logout:       () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user:          null,
  token:         null,
  selectedPlant: null,
  setUser:  (user, token) => set({ user, token }),
  setPlant: (plant)       => set({ selectedPlant: plant }),
  logout:   ()            => set({ user: null, token: null, selectedPlant: null }),
}));
```

### `frontend/src/components/ui/CountdownTimer.tsx`
```typescript
import { useEffect, useState } from "react";

interface Props { deadlineISO: string; label: string; urgentMinutes?: number; }

export function CountdownTimer({ deadlineISO, label, urgentMinutes = 120 }: Props) {
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    const calc = () => setRemaining(Math.max(0, new Date(deadlineISO).getTime() - Date.now()));
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, [deadlineISO]);

  if (remaining === 0) return <span className="text-red-600 font-bold">SCADUTO — {label}</span>;

  const totalMinutes = remaining / 60000;
  const color = totalMinutes < 30 ? "text-red-600" : totalMinutes < urgentMinutes ? "text-orange-500" : "text-green-600";

  const d  = Math.floor(remaining / 86400000);
  const h  = Math.floor((remaining % 86400000) / 3600000);
  const m  = Math.floor((remaining % 3600000) / 60000);
  const s  = Math.floor((remaining % 60000) / 1000);
  const fmt = `${d > 0 ? d+"g " : ""}${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;

  return <span className={`font-mono font-semibold ${color}`}>{label}: {fmt}</span>;
}
```

### `frontend/src/components/ui/AiSuggestion.tsx`
```typescript
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  suggestionId: string;
  output: string;
  onAccept: (final: string) => void;
  onIgnore: () => void;
}

export function AiSuggestion({ suggestionId, output, onAccept, onIgnore }: Props) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [edited, setEdited]   = useState(output);

  return (
    <div className="border border-amber-300 bg-amber-50 rounded-lg p-4 my-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs bg-amber-400 text-white px-2 py-0.5 rounded font-bold">{t("ai.ai_badge")}</span>
        <span className="text-sm font-medium text-amber-800">{t("ai.suggestion_label")}</span>
      </div>
      {editing ? (
        <textarea
          className="w-full border rounded p-2 text-sm min-h-24"
          value={edited}
          onChange={e => setEdited(e.target.value)}
        />
      ) : (
        <p className="text-sm text-gray-700 mb-3 whitespace-pre-wrap">{output}</p>
      )}
      <div className="flex gap-2 mt-2">
        <button onClick={() => onAccept(output)}       className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700">{t("ai.accept")}</button>
        {!editing
          ? <button onClick={() => setEditing(true)}   className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">{t("ai.edit_and_use")}</button>
          : <button onClick={() => onAccept(edited)}   className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">Salva modifiche</button>
        }
        <button onClick={onIgnore}                     className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300">{t("ai.ignore")}</button>
      </div>
    </div>
  );
}
```

### VERIFICA FASE 11
```bash
cd frontend && npm run build
```
Atteso: build completata senza errori TypeScript.

---

## FASE 12 — TEST SUITE

### `backend/tests/conftest.py`
```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
User = get_user_model()

@pytest.fixture
def plant_nis2(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="NIS2-TEST", name="Plant NIS2", country="IT", nis2_scope="essenziale", status="attivo")

@pytest.fixture
def plant_tisax(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="TISAX-TEST", name="Plant TISAX L3", country="IT", nis2_scope="non_soggetto", status="attivo")

@pytest.fixture
def co_user(db):
    from apps.auth_grc.models import UserPlantAccess, GrcRole
    user = User.objects.create_user(username="co", email="co@test.com", password="test")
    UserPlantAccess.objects.create(user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return user

@pytest.fixture
def api_client(co_user):
    c = APIClient()
    c.force_authenticate(user=co_user)
    return c
```

### `backend/tests/integration/test_audit_trail.py`
```python
import pytest, json, hashlib
from core.audit import log_action, AuditLog

@pytest.mark.django_db
def test_hash_chain_valid(co_user, plant_nis2):
    for i in range(5):
        log_action(user=co_user, action_code=f"test.{i}", level="L2", entity=plant_nis2, payload={"i": i})
    logs = AuditLog.objects.filter(entity_type="plant").order_by("timestamp_utc")
    for log in logs:
        expected = hashlib.sha256((json.dumps(log.payload, sort_keys=True, default=str) + log.prev_hash).encode()).hexdigest()
        assert expected == log.record_hash

@pytest.mark.django_db
def test_audit_append_only_trigger(co_user, plant_nis2):
    import pytest
    from django.db import connection
    log = log_action(user=co_user, action_code="test.create", level="L3", entity=plant_nis2, payload={"x": 1})
    with pytest.raises(Exception, match="append-only"):
        with connection.cursor() as cur:
            cur.execute("UPDATE audit_log SET action_code=%s WHERE id=%s", ["tampered", str(log.id)])
```

### `backend/pytest.ini`
```ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings.test
addopts = --reuse-db --cov=apps --cov=core --cov-report=term-missing --cov-fail-under=70
```

### VERIFICA FASE 12
```bash
cd backend && pytest tests/integration/test_audit_trail.py -v
```
Atteso: 2 test passano.

---

## FASE 13 — CI/CD

### `.github/workflows/ci.yml`
```yaml
name: CI
on:
  push:    {branches: [main, develop]}
  pull_request: {branches: [develop]}

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: {POSTGRES_DB: grc_test, POSTGRES_USER: grc, POSTGRES_PASSWORD: grc}
        options: --health-cmd pg_isready --health-interval 10s --health-retries 5
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11", cache: pip}
      - run: pip install -r backend/requirements/dev.txt
      - run: cd backend && python manage.py migrate
        env: {DJANGO_SETTINGS_MODULE: core.settings.test, DATABASE_URL: postgresql://grc:grc@localhost:5432/grc_test, SECRET_KEY: ci-key}
      - run: cd backend && pytest
        env: {DJANGO_SETTINGS_MODULE: core.settings.test, DATABASE_URL: postgresql://grc:grc@localhost:5432/grc_test, SECRET_KEY: ci-key}
      - run: cd backend && ruff check .

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: "20", cache: npm, cache-dependency-path: frontend/package-lock.json}
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build
      - run: cd frontend && npx tsc --noEmit
```

---

## VERIFICA FINALE

Esegui in sequenza dalla root del progetto:

```bash
# 1. Backend
cd backend
python manage.py migrate
python manage.py check
python manage.py verify_audit_trail_integrity
pytest tests/ -v

# 2. Frontend
cd ../frontend
npm run build

# 3. Docker
cd ..
docker compose up -d
# Attendi 15 secondi poi:
curl http://localhost:8000/api/docs/
```

Tutti i comandi devono completarsi senza errori.
Il progetto GRC è ora pronto: 21 moduli M00–M20, frontend React, CI/CD, test suite.
