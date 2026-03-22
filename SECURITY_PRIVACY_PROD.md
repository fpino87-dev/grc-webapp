# ANALISI CRITICA — Security, Privacy, Scalabilità, Robustezza
# GRC Webapp — Pre-produzione

════════════════════════════════════════════════════════
1. COERENZA CLAUDE.md E .CURSORRULES
════════════════════════════════════════════════════════

CLAUDE.md — 3 incongruenze trovate:

  ❌ Stato "Celery worker/beat: non ancora avviati" — obsoleto,
     Celery è configurato e funzionante
  ❌ "Migrazioni GRC: create ma NON ancora applicate" — obsoleto,
     sono applicate da mesi
  ❌ JWT dichiarato "ACCESS=30min" in .cursorrules ma nel codice
     è 8 ore (timedelta(hours=8)) — disallineamento documentazione

.cursorrules — 2 incongruenze:
  ❌ "Rate limiting: anon=20/h, user=500/h" ma nel codice è
     anon=100/minute, user=1000/minute — completamente diverso
  ❌ M19 descritto come "NotificationSubscription (3 non
     disattivabili), WebhookEndpoint" ma ora ha anche
     EmailConfiguration, NotificationRoleProfile, NotificationRule
     — mancano i nuovi modelli

════════════════════════════════════════════════════════
2. SECURITY — PROBLEMI CRITICI
════════════════════════════════════════════════════════

CRITICO 1 — Nessun Dockerfile di produzione
  docker-compose.yml usa Dockerfile.dev per TUTTI i servizi:
    backend, celery, celery-beat, frontend
  Dockerfile.dev tipicamente ha:
    - hot-reload (volume mount ./backend:/app)
    - DEBUG tools
    - nessun utente non-root
    - python manage.py runserver (single-thread, no WSGI)
  In produzione serve gunicorn/uvicorn, utente non-root,
  nessun volume di codice sorgente.

CRITICO 2 — python manage.py runserver in produzione
  docker-compose.yml riga 35:
    command: python manage.py runserver 0.0.0.0:8000
  Il dev server Django non è sicuro per produzione:
    - single-threaded
    - non gestisce connessioni concorrenti
    - espone traceback agli utenti
    - non rispetta ALLOWED_HOSTS correttamente
  Serve: gunicorn con workers + timeout configurati

CRITICO 3 — File upload: solo estensione, no MIME type reale
  validate_uploaded_file() controlla solo l'estensione del nome file.
  Un attaccante può caricare malware.php rinominato in malware.pdf
  Il sistema accetterà il file perché .pdf è nella whitelist.
  Serve: python-magic per verificare il MIME type reale del contenuto.

CRITICO 4 — Throttle troppo permissivo sull'endpoint login
  Throttle globale: anon=100/minute = 6000 tentativi/ora di login.
  GrcTokenObtainPairView non ha throttle specifico più restrittivo.
  Un attacco brute force password può girare senza blocchi reali.
  Serve: throttle dedicato su login: 5/minute per IP.

CRITICO 5 — Nessun AUTH_PASSWORD_VALIDATORS configurato
  settings/base.py non ha AUTH_PASSWORD_VALIDATORS.
  Django usa i default (solo MinimumLength 8 caratteri).
  Per un sistema GRC con dati aziendali sensibili servono:
    - MinimumLengthValidator (12+)
    - CommonPasswordValidator
    - NumericPasswordValidator
    - UserAttributeSimilarityValidator

CRITICO 6 — Fernet key non configurata in .env.example
  EmailConfiguration usa EncryptedCharField (Fernet AES-256)
  ma non c'è FERNET_KEYS in .env.example.
  Se la variabile manca l'app crasha al primo salvataggio email config.
  Se la chiave viene persa i dati cifrati sono irrecuperabili.

MEDIO 7 — JWT: ACCESS_TOKEN_LIFETIME = 8 ore
  8 ore è troppo lungo per un sistema GRC con dati sensibili.
  Standard de facto per sistemi aziendali: 15-30 minuti.
  Con token di 8 ore un token rubato (XSS, log, ecc.) è valido
  per tutta la giornata lavorativa senza possibilità di revoca.

MEDIO 8 — BLACKLIST_AFTER_ROTATION richiede app blacklist
  settings.py ha BLACKLIST_AFTER_ROTATION = True
  ma "rest_framework_simplejwt.token_blacklist" non è in
  INSTALLED_APPS — la blacklist non funziona.
  I refresh token ruotati non vengono invalidati.

MEDIO 9 — Nessun Content Security Policy
  Nessun header CSP configurato.
  CSP è la principale difesa contro XSS.
  Per una SPA React serve almeno:
    default-src 'self'
    script-src 'self'
    connect-src 'self' api-endpoint

MEDIO 10 — logo endpoint con AllowAny
  GET /api/v1/plants/{id}/logo/ è pubblico (AllowAny).
  Chiunque con l'UUID del plant può scaricare il logo.
  Gli UUID sono non-indovinabili ma:
    - espone informazioni aziendali senza autenticazione
    - permette enumeration se gli UUID trapelano

BASSO 11 — Nessun restart policy in docker-compose
  Nessun container ha restart: unless-stopped.
  Se backend crasha non si riavvia automaticamente.

BASSO 12 — Nessun healthcheck sul backend
  Il DB ha healthcheck (pg_isready) ma backend e celery no.
  Se Django si avvia ma poi crasha il container resta "running".

════════════════════════════════════════════════════════
3. PRIVACY BY DEFAULT — PROBLEMI
════════════════════════════════════════════════════════

PRIVACY 1 — Email nei log di sistema
  notifications/services.py:
    logger.info("Email inviata a %s: %s", recipients, subject)
    logger.error("Errore invio email a %s: %s", recipients, exc)
  I log di sistema contengono indirizzi email (dato personale GDPR).
  I log di Docker sono visibili con docker logs e non hanno TTL.
  Fix: hashare o omettere le email dai log, loggare solo il count.

PRIVACY 2 — GDPR: nessun meccanismo di anonimizzazione utenti
  Non esiste nessuna funzione anonymize_user() o forget_user().
  Il GDPR Art. 17 (diritto alla cancellazione) richiede che
  quando un utente viene rimosso i suoi dati personali vengano
  anonimizzati nei log e nei record storici.
  Il soft delete non è sufficiente — l'email rimane in AuditLog.

PRIVACY 3 — AI Sanitizer incompleto
  Sanitizer rimuove IP, P.IVA, email ma NON:
    - numeri di telefono
    - codici fiscali italiani (16 caratteri alfanumerici)
    - nomi propri di persona (dipendenti, manager)
    - indirizzi fisici
  Questi dati possono essere presenti nei description/notes
  dei moduli GRC e potrebbero raggiungere il cloud LLM.

PRIVACY 4 — Nessuna data retention automatica per log
  AuditLog ha livelli L1/L2/L3 con retention 5/3/1 anni
  ma non c'è nessun Celery task che elimina i record scaduti.
  I dati personali negli AuditLog rimangono indefinitamente.

PRIVACY 5 — Celery result backend su DB
  CELERY_RESULT_BACKEND = "django-db"
  I risultati dei task Celery (inclusi eventuali payload)
  vengono salvati nella tabella django_celery_results.
  Questi dati non hanno TTL e si accumulano indefinitamente.

════════════════════════════════════════════════════════
4. SCALABILITÀ
════════════════════════════════════════════════════════

SCALABILITÀ 1 — Celery result backend su DB (già citato)
  django-db come result backend è un collo di bottiglia.
  Con molti task paralleli crea contention sulla tabella.
  Fix: usare Redis come result backend in produzione.

SCALABILITÀ 2 — Celery concurrency = 2
  Solo 2 worker thread Celery per tutti i task.
  Con 10+ plant e task notturni pesanti (KPI snapshot,
  evidenze scadute, notifiche) 2 worker possono essere
  insufficienti. Fix: almeno 4 worker, configurabile da env.

SCALABILITÀ 3 — Nessun connection pooling applicativo
  CONN_MAX_AGE=60 aiuta ma con gunicorn workers multipli
  ogni worker ha il suo pool di connessioni.
  Per produzione seria valutare PgBouncer.

════════════════════════════════════════════════════════
5. ROBUSTEZZA
════════════════════════════════════════════════════════

ROBUSTEZZA 1 — Nessun monitoring/alerting
  Nessuna integrazione con Sentry, Prometheus, o simili.
  Gli errori vanno solo nei log Docker — nessuno li vede
  a meno di non controllare manualmente.

ROBUSTEZZA 2 — Nessun backup strategy documentato
  INFRASTRUCTURE.md non documenta backup PostgreSQL.
  Per produzione serve: backup giornaliero automatico,
  test di restore, retention minima 30 giorni.

════════════════════════════════════════════════════════
PROMPT PER CURSOR — tutte le fix
════════════════════════════════════════════════════════

Leggi CLAUDE.md e .cursorrules per il contesto completo.

Implementa in ordine. Checkpoint dopo ogni gruppo.

────────────────────────────────────────────────────────
GRUPPO 1 — Docker produzione (CRITICO)
────────────────────────────────────────────────────────

## Crea backend/Dockerfile.prod

FROM python:3.11-slim

# Utente non-root per sicurezza
RUN groupadd -r grc && useradd -r -g grc grc

WORKDIR /app

# Dipendenze sistema per python-magic e Pillow
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Dipendenze Python
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

# Codice sorgente
COPY . .

# Colleziona static files
RUN python manage.py collectstatic --noinput

# Utente non-root
RUN chown -R grc:grc /app
USER grc

EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

## Crea frontend/Dockerfile.prod

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

## Crea frontend/nginx.conf

server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json
               application/javascript text/xml;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy
      "default-src 'self'; script-src 'self' 'unsafe-inline';
       style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:;
       connect-src 'self';" always;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|svg|ico|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

## Crea docker-compose.prod.yml

services:
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB:       ${POSTGRES_DB}
      POSTGRES_USER:     ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # Non esporre la porta DB in produzione

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning",
             "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    env_file: .env.prod
    environment:
      DJANGO_SETTINGS_MODULE: core.settings.prod
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL",
             "curl -f http://localhost:8000/api/health/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    # Non esporre porte — solo via nginx

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    command: celery -A core worker -l warning
             --concurrency ${CELERY_CONCURRENCY:-4}
             --max-tasks-per-child 500
    env_file: .env.prod
    environment:
      DJANGO_SETTINGS_MODULE: core.settings.prod
    depends_on:
      - backend
      - redis

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    command: celery -A core beat -l warning
             --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env.prod
    environment:
      DJANGO_SETTINGS_MODULE: core.settings.prod
    depends_on:
      - backend
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    ports:
      - "3001:80"
    depends_on:
      - backend

volumes:
  pgdata:
  redisdata:

## backend/requirements/prod.txt (crea se non esiste)
-r base.txt
gunicorn==21.*
psycopg2-binary==2.9.*

────────────────────────────────────────────────────────
GRUPPO 2 — Security (CRITICO)
────────────────────────────────────────────────────────

## backend/core/settings/base.py

### 2A. Aggiungi AUTH_PASSWORD_VALIDATORS
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation"
                ".UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation"
                ".MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation"
                ".CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation"
                ".NumericPasswordValidator",
    },
]

### 2B. Aggiungi token_blacklist a INSTALLED_APPS
"rest_framework_simplejwt.token_blacklist",

### 2C. Correggi JWT — ACCESS_TOKEN da 8h a 30min
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":    timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME":   timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":    True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN":        True,
    "AUTH_HEADER_TYPES":        ("Bearer",),
}

### 2D. Correggi throttle — valori reali
"DEFAULT_THROTTLE_RATES": {
    "anon":  "20/hour",
    "user":  "500/hour",
    "login": "5/minute",    # anti brute-force
},

### 2E. Aggiungi FERNET_KEYS in settings
FERNET_KEYS = [env("FERNET_KEY")]

## backend/core/urls.py
Aggiungi throttle specifico sul login:

from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    rate = "5/minute"
    scope = "login"

class GrcTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]

## .env.example
Aggiungi:
  FERNET_KEY=<genera con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
  REDIS_PASSWORD=cambia-questa-password-redis
  CELERY_CONCURRENCY=4
  POSTGRES_DB=grc_prod
  POSTGRES_USER=grc
  POSTGRES_PASSWORD=cambia-questa-password-db

## Crea .env.prod.example (separato da .env.example che è per dev)
DEBUG=false
SECRET_KEY=<genera con: python -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=grc.tuaazienda.com
FRONTEND_URL=https://grc.tuaazienda.com
DATABASE_URL=postgresql://grc:PASSWORD@db:5432/grc_prod
REDIS_URL=redis://:PASSWORD@redis:6379/0
FERNET_KEY=<chiave Fernet>
DJANGO_SETTINGS_MODULE=core.settings.prod
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=noreply@tuaazienda.com
EMAIL_HOST_PASSWORD=password-app
DEFAULT_FROM_EMAIL=GRC Platform <noreply@tuaazienda.com>
CELERY_CONCURRENCY=4

## backend/apps/documents/services.py
Fix validate_uploaded_file() con MIME type reale:

Aggiungi in backend/requirements/base.txt:
  python-magic==0.4.*

Modifica validate_uploaded_file():

import magic

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument"
    ".spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument"
    ".presentationml.presentation",
    "image/png",
    "image/jpeg",
}

def validate_uploaded_file(uploaded_file):
    # 1. Dimensione
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(_("File troppo grande. Max 50MB."))

    # 2. Estensione (whitelist)
    _, ext = os.path.splitext(getattr(uploaded_file, "name", "") or "")
    ext = ext.lstrip(".").lower()
    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(_(
            "Estensione non consentita. "
            "Formati ammessi: doc, docx, xls, xlsx, ppt, pptx, pdf, png, jpg."
        ))

    # 3. MIME type reale (contrasto extension spoofing)
    uploaded_file.seek(0)
    header = uploaded_file.read(2048)
    uploaded_file.seek(0)
    mime_type = magic.from_buffer(header, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(_(
            "Tipo di file non consentito. "
            "Il contenuto del file non corrisponde all'estensione."
        ))

## backend/apps/plants/views.py
Fix logo endpoint — rimuovi AllowAny, usa IsAuthenticated:

    @action(detail=True, methods=["get"], url_path="logo")
    def logo(self, request, pk=None):
        # IsAuthenticated è già il default del ViewSet
        plant = self.get_object()
        # ... resto invariato

## Aggiungi healthcheck endpoint backend:

### backend/core/urls.py
from django.http import JsonResponse

def health_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "error",
                         "db": db_ok}, status=status)

path("api/health/", health_check, name="health-check"),

────────────────────────────────────────────────────────
GRUPPO 3 — Privacy by default
────────────────────────────────────────────────────────

## backend/apps/notifications/services.py
Fix log con email personali:

# ERA:
# logger.info("Email inviata a %s: %s", recipients, subject)
# logger.error("Errore invio email a %s: %s", recipients, exc)

# DIVENTA:
logger.info(
    "Email inviata a %d destinatari: %s",
    len(recipients), subject
)
logger.error(
    "Errore invio email a %d destinatari [%s]: %s",
    len(recipients), subject, exc
)

## backend/apps/ai_engine/sanitizer.py
Estendi il sanitizer con i pattern mancanti:

# Aggiungi dopo EMAIL_RE:
PHONE_RE = re.compile(
    r"\b(\+39|0039)?[\s\-]?(\d{2,4})[\s\-]?(\d{6,8})\b"
)
CF_RE = re.compile(
    r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b",
    re.IGNORECASE
)
PHONE_MOBILE_RE = re.compile(
    r"\b3\d{2}[\s\-]?\d{6,7}\b"
)

# Nel metodo sanitize() aggiungi:
text = self.PHONE_RE.sub("[PHONE_REMOVED]", text)
text = self.PHONE_MOBILE_RE.sub("[PHONE_REMOVED]", text)
text = self.CF_RE.sub("[CF_REMOVED]", text)

## backend/apps/auth_grc/services.py
Crea funzione anonymize_user() per GDPR Art. 17:

def anonymize_user(user, requesting_user) -> None:
    """
    Anonimizza i dati personali di un utente rimosso.
    GDPR Art. 17 — Diritto alla cancellazione.
    Preserva i record di audit trail (obbligo legale)
    ma rimuove i dati identificativi.
    """
    from django.utils import timezone
    from core.audit import log_action
    import uuid

    anon_id  = str(uuid.uuid4())[:8]
    anon_email = f"deleted_{anon_id}@anonymized.invalid"

    # Anonimizza utente Django
    user.first_name = "Utente"
    user.last_name  = "Rimosso"
    user.email      = anon_email
    user.username   = anon_email
    user.is_active  = False
    user.set_unusable_password()
    user.save()

    # Soft delete accessi GRC
    from apps.auth_grc.models import UserPlantAccess
    UserPlantAccess.objects.filter(user=user).update(
        deleted_at=timezone.now()
    )

    # Anonimizza nei log (preserva action_code e payload
    # ma rimuove l'email identificativa)
    from core.models import AuditLog
    AuditLog.objects.filter(
        user_email_at_time=user.email
    ).update(
        user_email_at_time=anon_email
    )

    log_action(
        user=requesting_user,
        action_code="auth.user.anonymized",
        level="L1",
        entity=user,
        payload={"anon_id": anon_id, "gdpr_request": True},
    )

## backend/apps/auth_grc/views.py
Aggiungi endpoint anonimizzazione (solo superadmin):

    @action(detail=True, methods=["post"], url_path="anonymize",
            permission_classes=[IsAuthenticated, IsAdminUser])
    def anonymize(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import anonymize_user
        user = self.get_object()
        reason = request.data.get("reason", "")
        if not reason or len(reason.strip()) < 10:
            return Response({
                "error": "Motivazione obbligatoria (min 10 caratteri) "
                         "per richiesta GDPR Art. 17"
            }, status=400)
        anonymize_user(user, request.user)
        return Response({
            "ok": True,
            "message": "Utente anonimizzato (GDPR Art. 17)"
        })

## Crea Celery task per data retention:

### backend/apps/audit_trail/tasks.py
from celery import shared_task
from django.utils import timezone

@shared_task(bind=True, autoretry_for=(Exception,),
             max_retries=3, default_retry_delay=300)
def cleanup_expired_audit_logs(self):
    """
    Elimina i log AuditTrail scaduti secondo la retention policy.
    L1: 5 anni, L2: 3 anni, L3: 1 anno.
    Eseguito il primo giorno di ogni mese.
    """
    from core.models import AuditLog
    import logging
    logger = logging.getLogger(__name__)

    now = timezone.now()
    retention = {
        "L1": now - timezone.timedelta(days=365 * 5),
        "L2": now - timezone.timedelta(days=365 * 3),
        "L3": now - timezone.timedelta(days=365 * 1),
    }

    total_deleted = 0
    for level, cutoff in retention.items():
        deleted, _ = AuditLog.objects.filter(
            level=level,
            timestamp_utc__lt=cutoff,
        ).delete()
        total_deleted += deleted
        if deleted:
            logger.info(
                "Audit log cleanup: eliminati %d record L%s "
                "precedenti a %s",
                deleted, level, cutoff.date()
            )

    return f"Cleanup completato: {total_deleted} record eliminati"

### Aggiungi al cleanup Celery result backend:

@shared_task
def cleanup_celery_results():
    """Elimina risultati task Celery più vecchi di 7 giorni."""
    from django_celery_results.models import TaskResult
    from django.utils import timezone
    cutoff  = timezone.now() - timezone.timedelta(days=7)
    deleted, _ = TaskResult.objects.filter(
        date_done__lt=cutoff
    ).delete()
    return f"Celery results cleanup: {deleted} record eliminati"

### backend/core/celery.py
Aggiungi al beat_schedule:

    "cleanup-audit-logs": {
        "task":     "apps.audit_trail.tasks.cleanup_expired_audit_logs",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),
    },
    "cleanup-celery-results": {
        "task":     "apps.audit_trail.tasks.cleanup_celery_results",
        "schedule": crontab(hour=3, minute=30),
    },

────────────────────────────────────────────────────────
GRUPPO 4 — Scalabilità: Celery result backend su Redis
────────────────────────────────────────────────────────

## backend/core/settings/base.py
Mantieni django-db come default per dev (semplice).

## backend/core/settings/prod.py
Aggiungi:
  CELERY_RESULT_BACKEND = env("REDIS_URL") + "/1"
  CELERY_RESULT_EXPIRES = 86400  # 24h in secondi

────────────────────────────────────────────────────────
GRUPPO 5 — Robustezza: restart e monitoring
────────────────────────────────────────────────────────

## docker-compose.yml (versione dev — aggiungi restart)
Aggiungi a ogni servizio:
  restart: unless-stopped

## backend/core/settings/base.py
Aggiungi configurazione logging strutturato:

LOGGING = {
    "version":            1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process} "
                      "{thread} {message}",
            "style":  "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django":           {"handlers": ["console"], "level": "WARNING"},
        "apps":             {"handlers": ["console"], "level": "INFO"},
        "core":             {"handlers": ["console"], "level": "INFO"},
        "celery":           {"handlers": ["console"], "level": "WARNING"},
    },
}

────────────────────────────────────────────────────────
GRUPPO 6 — Aggiorna CLAUDE.md e .cursorrules
────────────────────────────────────────────────────────

## CLAUDE.md — aggiorna:

Sezione "Stato attuale":
  ✅ Celery worker/beat: configurati e avviati
  ✅ Migrazioni GRC: applicate
  ✅ Framework normativi: caricati
  ✅ Docker produzione: Dockerfile.prod + docker-compose.prod.yml
  ⚠️ Traduzione UI: solo IT/EN — FR/PL/TR in sviluppo

Sezione "Sicurezza":
  JWT: ACCESS=30min, REFRESH=7gg, ROTATE=True, BLACKLIST=True
  Rate limiting: anon=20/h, user=500/h, login=5/min
  File upload: whitelist estensioni + MIME type reale (python-magic)
  Password: min 12 caratteri + CommonPassword + NumericPassword
  FERNET: cifratura AES-256 per credenziali SMTP
  GDPR: anonymize_user() disponibile, retention automatica audit log

Sezione "M19 Notifications":
  EmailConfiguration — SMTP config cifrata Fernet da UI
  NotificationRoleProfile — profili silenzioso/essenziale/standard/completo/custom
  NotificationRule — regole granulari (avanzato)
  resolver.py — risoluzione destinatari per evento/plant/ruolo

Sezione "Prossime attività":
  Rimuovi tutto il vecchio
  Sostituisci con:
    DA FARE: Traduzioni FR/PL/TR
    DA FARE: Test suite (coverage target ≥ 70%)
    DA FARE: Sentry integration per error monitoring
    DA FARE: Backup automatico PostgreSQL

## .cursorrules — aggiorna:

Sezione "Sicurezza":
  JWT: ACCESS=30min, REFRESH=7gg, ROTATE=True, BLACKLIST=True
  Rate limiting: anon=20/h, user=500/h, login=5/min (LoginRateThrottle)
  File upload: whitelist estensioni + python-magic MIME type reale
  Password: AUTH_PASSWORD_VALIDATORS con min 12 char
  Fernet: FERNET_KEY in env per EncryptedCharField
  GDPR: anonymize_user() per Art.17, cleanup_expired_audit_logs() mensile

Sezione "M19 Notifications":
  Aggiorna con nuovi modelli e resolver

Aggiungi regola 11 nelle "Regole architetturali ASSOLUTE":
  11. Mai loggare dati personali (email, CF, telefono) nei log
      di sistema — loggare solo conteggi o identificatori anonimi
  12. File upload: sempre validate_uploaded_file() con MIME check
  13. Produzione: usare docker-compose.prod.yml e Dockerfile.prod

════════════════════════════════════════════════════════
CHECKPOINT FINALE
════════════════════════════════════════════════════════

# Verifica settings
docker compose exec backend python manage.py check
docker compose exec backend python -c "
from django.conf import settings
print('JWT access:', settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])
print('Throttle login:', settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES',{}).get('login'))
print('Password validators:', len(settings.AUTH_PASSWORD_VALIDATORS))
print('Token blacklist:', 'rest_framework_simplejwt.token_blacklist' in settings.INSTALLED_APPS)
print('Fernet configured:', bool(getattr(settings, 'FERNET_KEYS', None)))
"

# Verifica MIME check
docker compose exec backend python -c "
import magic
print('python-magic OK:', magic.from_buffer(b'%PDF', mime=True))
"

# Verifica migrazioni
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

docker compose exec frontend npm run build 2>&1 | tail -10

git add .
git commit -m "feat: security hardening (gunicorn, MIME check, throttle login, JWT 30min, blacklist, password validators, Fernet key), privacy by default (anonimizzazione GDPR, sanitizer esteso, log senza PII, retention audit log), docker prod, scalabilità Celery Redis backend"
git push
