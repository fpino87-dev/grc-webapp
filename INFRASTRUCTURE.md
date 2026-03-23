# INFRASTRUCTURE.md — GRC Compliance Platform

> Architettura infrastrutturale, stack tecnologico, deployment, database, sicurezza, backup e monitoraggio.

---

## Indice

- [Panoramica architetturale](#panoramica-architetturale)
- [Stack tecnologico](#stack-tecnologico)
- [Porte in uso](#porte-in-uso)
- [Variabili d'ambiente obbligatorie](#variabili-dambiente-obbligatorie)
- [Deployment produzione — step by step](#deployment-produzione--step-by-step)
- [Nginx Proxy Manager](#nginx-proxy-manager)
- [Database](#database)
- [Storage file](#storage-file)
- [Celery — task schedulati](#celery--task-schedulati)
- [Sicurezza infrastrutturale](#sicurezza-infrastrutturale)
- [Backup e disaster recovery](#backup-e-disaster-recovery)
- [Monitoraggio e alerting](#monitoraggio-e-alerting)
- [Scalabilità](#scalabilità)
- [AI Engine — infrastruttura M20](#ai-engine--infrastruttura-m20)
- [Checklist pre-produzione](#checklist-pre-produzione)

---

## Panoramica architetturale

```
  Browser --> Nginx Proxy Manager (80/443)
                  |               |
             Frontend          Backend API
             React SPA         Django + DRF
             porta 3001        porta 8001
                                    |
                      +-------------+-----------+
                      |             |           |
                 PostgreSQL       Redis      S3 / MinIO
                 Primary +        Cache +    Documenti
                 Replica          Broker     Evidenze
                 porta 5433

                      |
              Celery Worker + Beat
              (task async, sync KB4,
               notifiche, audit job)

                      |
              +-------+--------+
              |  AI Engine M20 |  <- opzionale
              |  Ollama/vLLM   |
              |  + Sanitizer   |--> Cloud LLM
              +----------------+   (solo dati anonimi)

  Integrazioni esterne:
  KnowBe4 API . SMTP aziendale . SSO/SAML . SIEM webhook . ACN email
```

---

## Stack tecnologico

### Backend

| Componente | Tecnologia | Versione |
|-----------|-----------|---------|
| Runtime | Python | 3.11+ |
| Framework | Django + Django REST Framework | 5.1 |
| Task queue | Celery | 5.x |
| Broker / cache | Redis | 7.x |
| Auth JWT | SimpleJWT | latest |
| Auth SSO | django-allauth | latest |
| i18n | Django i18n built-in | — |
| Cifratura | cryptography (Fernet) | latest |
| MIME check | python-magic | latest |

### Frontend

| Componente | Tecnologia | Versione |
|-----------|-----------|---------|
| Framework | React | 18+ |
| Language | TypeScript | 5.x |
| Build | Vite | 5.x |
| State management | Zustand | — |
| Data fetching | TanStack Query | — |
| Router | React Router | v6 |
| i18n | i18next + react-i18next | — |
| UI components | Tailwind CSS + shadcn/ui | — |
| Charts | Recharts | — |

### Database e storage

| Componente | Tecnologia | Versione |
|-----------|-----------|---------|
| Database principale | PostgreSQL | 15+ |
| Full-text search | PostgreSQL FTS nativo | — |
| Cache / broker | Redis | 7+ |
| Object storage | MinIO (on-prem) o AWS S3 | — |

### Infrastruttura

| Componente | Tecnologia |
|-----------|-----------|
| Container | Docker + Compose |
| Reverse proxy | Nginx Proxy Manager |
| Orchestrazione avanzata | Kubernetes o Docker Swarm |
| IaC | Terraform |
| Config management | Ansible |
| CI/CD | GitLab CI o GitHub Actions |
| Secrets | HashiCorp Vault o env cifrati |

---

## Porte in uso

| Servizio | Porta host dev | Porta host prod | Porta container |
|----------|---------------|----------------|----------------|
| Backend Django | 8001 | 8001 | 8000 |
| Frontend Vite/Nginx | 3001 | 3001 | 3000 |
| PostgreSQL GRC | 5433 | 5433 | 5432 |
| Redis GRC | — | — | 6379 |
| MinIO console | 9001 | — | 9001 |
| Mailhog SMTP | 1026 | — (non in prod) | 1025 |
| Mailhog UI | 8026 | — (non in prod) | 8025 |

**Altri container sul server (non toccare):**
- `ai-docintel-*` — progetto separato
- `npm` — Nginx Proxy Manager su 80/443
- `budget-db`, `sitebudget`, `siteciso`, `sitebb`

---

## Variabili d'ambiente obbligatorie

Il repository include `.env.example` (sviluppo) e `.env.prod.example` (produzione) con tutti i placeholder. Non committare mai i file `.env` o `.env.prod` — sono in `.gitignore`.

### Tabella variabili principali

| Variabile | Obbligatoria | Default dev | Descrizione |
|-----------|-------------|-------------|-------------|
| `SECRET_KEY` | Si | — | Chiave Django (min 50 char, generare con `secrets.token_urlsafe(50)`) |
| `FERNET_KEY` | Si | — | Cifratura AES-256 credenziali SMTP (generare con `Fernet.generate_key()`) |
| `DEBUG` | No | `True` | Impostare `False` in produzione |
| `ALLOWED_HOSTS` | Si in prod | `localhost` | Host ammessi separati da virgola |
| `DATABASE_URL` | Si | `postgresql://grc:grc@db:5432/grc_dev` | URL connessione PostgreSQL |
| `REDIS_URL` | Si | `redis://redis:6379/0` | URL connessione Redis |
| `FRONTEND_URL` | Si | `http://localhost:3001` | URL frontend (per CORS e link nelle email) |
| `STORAGE_BACKEND` | No | `local` | `local` o `s3` |
| `S3_ENDPOINT_URL` | Se S3 | — | Endpoint MinIO o AWS S3 |
| `S3_BUCKET_NAME` | Se S3 | — | Nome bucket documenti |
| `S3_ACCESS_KEY` | Se S3 | — | Access key S3/MinIO |
| `S3_SECRET_KEY` | Se S3 | — | Secret key S3/MinIO |
| `EMAIL_HOST` | No | — | Server SMTP |
| `EMAIL_PORT` | No | 587 | Porta SMTP |
| `EMAIL_USE_TLS` | No | `True` | TLS per SMTP |
| `EMAIL_HOST_USER` | No | — | Utente SMTP |
| `EMAIL_HOST_PASSWORD` | No | — | Password SMTP (cifrata con FERNET_KEY in DB) |
| `SSO_ENABLED` | No | `False` | Abilita autenticazione SSO |
| `SAML_METADATA_URL` | Se SSO | — | URL metadata IdP SAML |
| `KNOWBE4_API_KEY` | Se M15 | — | API key KnowBe4 |
| `AI_ENGINE_ENABLED` | No | `False` | Master switch AI Engine M20 |
| `AZURE_OPENAI_KEY` | Se AI cloud | — | API key Azure OpenAI |
| `ANTHROPIC_API_KEY` | Se AI cloud | — | API key Anthropic |
| `AUDIT_TRAIL_RETENTION_L1_YEARS` | No | `5` | Retention log sicurezza (anni) |
| `AUDIT_TRAIL_RETENTION_L2_YEARS` | No | `3` | Retention log compliance (anni) |
| `AUDIT_TRAIL_RETENTION_L3_YEARS` | No | `1` | Retention log operativo (anni) |
| `SESSION_COOKIE_SECURE` | No | `False` | Impostare `True` in produzione (HTTPS) |
| `CSRF_COOKIE_SECURE` | No | `False` | Impostare `True` in produzione (HTTPS) |

### Riferimento completo `.env`

```bash
# ── Core ──────────────────────────────────────────────────────────────
SECRET_KEY=<stringa-generata-min-50-char>
FERNET_KEY=<chiave-fernet-generata>
DEBUG=false
ALLOWED_HOSTS=grc.azienda.com
FRONTEND_URL=https://grc.azienda.com

# ── Database ──────────────────────────────────────────────────────────
DATABASE_URL=postgresql://grc:password@db:5432/grc_prod

# ── Redis ─────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Storage ───────────────────────────────────────────────────────────
STORAGE_BACKEND=s3                    # local | s3
S3_ENDPOINT_URL=https://minio.internal
S3_BUCKET_NAME=grc-documents
S3_ACCESS_KEY=...
S3_SECRET_KEY=...

# ── Email ─────────────────────────────────────────────────────────────
EMAIL_HOST=smtp.azienda.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=grc-noreply@azienda.com
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=GRC Compliance <grc-noreply@azienda.com>

# ── SSO ───────────────────────────────────────────────────────────────
SSO_ENABLED=true
SAML_METADATA_URL=https://idp.azienda.com/metadata
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_ENDPOINT=https://idp.azienda.com

# ── KnowBe4 (M15) ─────────────────────────────────────────────────────
KNOWBE4_API_KEY=...
KNOWBE4_API_URL=https://us.api.knowbe4.com
KNOWBE4_SYNC_ENABLED=true
KNOWBE4_SYNC_CRON=0 2 * * *           # ogni notte alle 02:00

# ── AI Engine (M20) — disabilitato di default ─────────────────────────
AI_ENGINE_ENABLED=false
AI_LOCAL_ENDPOINT=http://ollama:11434
AI_LOCAL_MODEL=llama3.1:8b
AI_CLOUD_PROVIDER=azure               # azure | anthropic
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
ANTHROPIC_API_KEY=...

# ── Retention audit trail ─────────────────────────────────────────────
AUDIT_TRAIL_RETENTION_L1_YEARS=5      # Log sicurezza
AUDIT_TRAIL_RETENTION_L2_YEARS=3      # Log compliance
AUDIT_TRAIL_RETENTION_L3_YEARS=1      # Log operativo

# ── Sicurezza cookie ──────────────────────────────────────────────────
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

---

## Deployment produzione — step by step

### Requisiti server minimi

- 4 CPU, 8 GB RAM, 100 GB SSD
- Docker Engine >= 24.x + Docker Compose v2
- Sistema operativo: Ubuntu 22.04 LTS o Debian 12 (consigliati)
- Accesso SSH con utente non-root sudoer

### Procedura completa

**1. Installazione Docker Engine + Docker Compose v2**

```bash
# Ubuntu 22.04
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Logout e login per applicare il gruppo
docker --version && docker compose version
```

**2. Clone repository**

```bash
git clone https://github.com/org/grc-webapp.git
cd grc-webapp
```

**3. Configurazione variabili produzione**

```bash
cp .env.prod.example .env.prod
# Compilare TUTTI i valori — non lasciare placeholder
nano .env.prod
```

**4. Generazione chiavi sicure**

```bash
# SECRET_KEY Django (min 50 caratteri)
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# FERNET_KEY per cifratura AES-256 credenziali SMTP
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Inserire i valori generati in `.env.prod`.

**5. Build immagini produzione**

```bash
make prod-build
```

**6. Avvio stack**

```bash
make prod-up
```

**7. Migrazioni database**

```bash
make prod-migrate
```

**8. Dati iniziali (frameworks, profili notifica, competenze, documenti richiesti)**

```bash
make prod-seed
```

**9. Creazione superuser iniziale**

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

**10. Configurazione Nginx Proxy Manager** (vedi sezione dedicata sotto)

**11. Verifica deploy**

```bash
make prod-check
# Verifica anche l'endpoint di health
curl http://localhost:8001/api/health/
```

### Docker Compose sviluppo — estratto

```yaml
# docker-compose.yml — estratto reale del progetto
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: grc_dev
      POSTGRES_USER: grc
      POSTGRES_PASSWORD: grc
    ports: ["5433:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    volumes: [redisdata:/data]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9001:9001"]
    volumes: [miniodata:/data]

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes: [./backend:/app]
    ports: ["8001:8000"]
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A core worker -l info --concurrency 2
    volumes: [./backend:/app]
    env_file: .env
    depends_on: [backend, redis]

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes: [./backend:/app]
    env_file: .env
    depends_on: [backend, redis]

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes: [./frontend:/app, /app/node_modules]
    ports: ["3001:3000"]
    environment:
      - VITE_API_URL=http://localhost:8001

  mailhog:
    image: mailhog/mailhog
    ports: ["1026:1025", "8026:8025"]

volumes:
  pgdata:
  redisdata:
  miniodata:
```

---

## Nginx Proxy Manager

Nginx Proxy Manager (NPM) gestisce il routing HTTPS e il proxy verso i servizi interni. E' già in esecuzione sul server come container `npm` sulla porta 80/443.

### Configurazione proxy host

**Frontend (React SPA):**
- Forward hostname/IP: `localhost`
- Forward port: `3001`
- Dominio pubblico: `grc.azienda.com`
- SSL: Let's Encrypt — attivare "Force SSL" e "HTTP/2 Support"

**Backend API:**
- Forward hostname/IP: `localhost`
- Forward port: `8001`
- Dominio pubblico: `grc.azienda.com`
- Location: `/api/` (proxy solo percorsi `/api/*`)
- SSL: stesso certificato del frontend

**Custom location header consigliato per l'API:**

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
client_max_body_size 50m;
```

SSL Let's Encrypt con auto-renewal automatico gestito da NPM.

---

## Database

### Principi di design

- **Table inheritance IT/OT**: tabella `Asset` base + `AssetIT` e `AssetOT` con attributi specifici — nessuna colonna nullable inutile
- **Audit trail append-only**: tabella `AuditLog` protetta da trigger PostgreSQL che rifiuta UPDATE e DELETE
- **Hash chain**: ogni record contiene `prev_hash` e `record_hash = SHA256(payload + prev_hash)` — integrità verificabile
- **Partitioning per anno**: `AuditLog` partizionata su `timestamp_utc` — gestione retention differenziata L1/L2/L3 via `DROP PARTITION`
- **Full-text search**: colonna `tsvector` su `LessonLearned` per knowledge base M12 (lingua italiana e inglese)
- **Soft delete globale**: nessuna tabella usa hard delete — `deleted_at TIMESTAMPTZ NULL` con filtro nel manager

### Indici critici

```sql
-- Audit trail — query per entità e per utente
CREATE INDEX idx_auditlog_entity   ON audit_log(entity_type, entity_id, timestamp_utc DESC);
CREATE INDEX idx_auditlog_user     ON audit_log(user_id, timestamp_utc DESC);

-- Task — scadenze imminenti (query più frequente nella dashboard)
CREATE INDEX idx_task_due          ON tasks(due_date, stato)
  WHERE stato IN ('aperto','in_corso');

-- ControlInstance — vista compliance per plant e framework
CREATE INDEX idx_ctrl_inst_plant   ON control_instances(plant_id, framework_id, stato);

-- Lesson learned — full-text search knowledge base
CREATE INDEX idx_lesson_fts        ON lesson_learned
  USING GIN(to_tsvector('italian', coalesce(descrizione,'') || ' ' || coalesce(causa_radice,'')));

-- Risk score — heat map (aggiornato frequentemente)
CREATE INDEX idx_risk_score        ON risk_assessments(plant_id, score DESC)
  WHERE archived_at IS NULL;
```

### Trigger append-only per audit trail

```sql
CREATE OR REPLACE FUNCTION prevent_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Audit trail is append-only -- UPDATE and DELETE are not allowed';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_no_mutation
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
```

Oltre agli indici SQL espliciti, il codice applicativo definisce `db_index=True` sui principali campi di filtro (`status`, `due_date`, `score`, `valid_until`, campi di tipo e stato) per `Task`, `Incident`, `ControlInstance`, `RiskAssessment`, `Document` ed `Evidence`, per ottimizzare le query operative usate da dashboard e scadenzario.

---

## Storage file

### Struttura bucket

```
grc-documents/
├── documents/{plant_id}/{doc_id}/v{major}.{minor}_{hash}.pdf
├── evidences/{plant_id}/{control_instance_id}/{evidence_id}_{filename}
├── audit-exports/{year}/{month}/export_{timestamp}_{hash}.zip
└── ai-temp/{request_id}/                     <- eliminati dopo 24h (lifecycle rule)
```

### Policy di retention

| Tipo | Retention | Note |
|------|-----------|------|
| Documenti vigenti | Illimitata | Versioni archiviate mantenute |
| Evidenze valide | Illimitata | Scadute: archiviate dopo 1 anno |
| Export audit | 5 anni | Allineato a audit trail L1 |
| Temp AI (M20) | 24 ore | Auto-delete via bucket lifecycle |

---

## Celery — task schedulati

Tutti i task sono gestiti da Celery Beat con scheduler basato su database (`django_celery_beat`). I task critici usano `autoretry` con backoff esponenziale per gestire errori transitori.

| Task | Schedule | Descrizione | Modulo |
|------|----------|-------------|--------|
| `check_expired_evidences` | Ogni notte 02:00 | Marca evidenze scadute e notifica i responsabili | M07 |
| `generate_weekly_kpi_snapshots` | Lunedi 06:00 | Snapshot KPI settimanale per dashboard M18 | M18 |
| `check_unrevalued_changes` | Lunedi 07:00 | Asset con change non rivalutati in risk assessment | M04 |
| `check_upcoming_audits` | Lunedi 07:30 | Reminder audit pianificati (range ±4 giorni) | M17 |
| `notify_expiring_roles` | Ogni giorno 08:00 | Ruoli in scadenza nei prossimi 30/7/1 giorni | M00 |
| `notify_pdca_blocked` | Ogni giorno 08:30 | PDCA bloccati senza aggiornamenti | M11 |
| `check_overdue_findings` | Ogni giorno 08:00 | Finding scaduti da 1/7/14 giorni | M17 |
| `check_stale_audit_preps` | Lunedi 08:15 | AuditPrep bloccati senza aggiornamenti da >30gg | M17 |
| `check_expired_bcp_plans` | Ogni notte 02:10 | Piani BCP scaduti o in scadenza | M16 |
| `cleanup_expired_audit_logs` | 1° del mese 03:00 | Retention differenziata: L1=5anni, L2=3anni, L3=1anno | M10 |
| `cleanup_celery_results` | Ogni notte 03:30 | Pulizia risultati task Celery scaduti dal DB | — |

### Verifica stato Celery

```bash
# Verifica worker attivi
docker compose exec backend celery -A core inspect active

# Verifica task schedulati
docker compose exec backend celery -A core inspect scheduled

# Monitor in tempo reale
docker compose logs celery --tail=50 -f
docker compose logs celery-beat --tail=50 -f
```

---

## Sicurezza infrastrutturale

### TLS e header HTTP

```nginx
# nginx.conf — sezione TLS e sicurezza
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;

add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'";
add_header Referrer-Policy strict-origin-when-cross-origin;
```

### Regole firewall

| Porta | Sorgente | Destinazione | Motivo |
|-------|---------|-------------|--------|
| 443 | Internet | Load balancer | UI utenti |
| 80 | Internet | Load balancer | Redirect a 443 |
| 8000 | Load balancer | Backend | API interna |
| 5432 | Backend, Celery | PostgreSQL | Database |
| 6379 | Backend, Celery | Redis | Cache / broker |
| 11434 | Backend | Ollama | AI locale M20 |
| 443 | Sanitizer | Azure / Anthropic | AI cloud M20 (solo anonimi) |
| 443 | Celery | KnowBe4 API | Sync M15 |

### Sicurezza API e sessioni

- I token JWT usano SimpleJWT con durata **30 minuti** per gli access token e **7 giorni** per i refresh token, con rotazione e blacklist abilitate.
- Rate limiting DRF: **AnonRateThrottle 20/h**, **UserRateThrottle 500/h**, **LoginRateThrottle 5/min** su `GrcTokenObtainPairView`.
- In `core.settings.prod` sono abilitati `SECURE_HSTS_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` e `SECURE_SSL_REDIRECT`.
- File upload: whitelist estensioni + MIME type reale verificato con python-magic.
- Password: minimo 12 caratteri + validatori CommonPassword, NumericPassword, UserAttributeSimilarity.

### Secrets management

In produzione non usare variabili d'ambiente Docker in chiaro. Usare HashiCorp Vault con agent sidecar oppure secret cifrati in Kubernetes (`kind: Secret` con cifratura etcd at-rest abilitata).

---

## Backup e disaster recovery

### Obiettivi RTO / RPO

| Scenario | RPO | RTO |
|----------|-----|-----|
| Failure singolo nodo | 0 (replica sincrona) | < 2 min |
| Corruzione dati | Ultimo backup (max 24h) | < 4 ore |
| Disaster completo datacenter | Ultimo backup (max 24h) | < 8 ore |
| Ripristino DB < 10 GB (Docker) | 24h (backup giornaliero) | 15-30 min |

### Backup automatico — crontab host

Configurare sul server host (non nei container):

```bash
# Aprire crontab dell'utente che esegue Docker
crontab -e

# Backup giornaliero PostgreSQL — ogni notte alle 01:00
0 1 * * * docker exec grc-webapp-db-1 pg_dump -U grc grc_prod | gzip > /backup/grc_$(date +\%Y\%m\%d).sql.gz

# Pulizia backup più vecchi di 30 giorni — ogni notte alle 02:00
0 2 * * * find /backup -name "grc_*.sql.gz" -mtime +30 -delete

# Backup file media — ogni notte alle 03:00
0 3 * * * docker cp grc-webapp-backend-1:/app/media /backup/media_$(date +\%Y\%m\%d)/
```

Assicurarsi che `/backup` esista e abbia spazio sufficiente:

```bash
mkdir -p /backup
df -h /backup
```

### Script di backup completo

```bash
#!/usr/bin/env bash
# scripts/backup.sh
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/${TIMESTAMP}"
RETENTION_DAYS=${RETENTION_DAYS:-30}

mkdir -p "${BACKUP_DIR}"

# 1. Backup PostgreSQL
pg_dump -Fc "${DATABASE_URL}" > "${BACKUP_DIR}/db.dump"
echo "DB dump OK"

# 2. Sync documenti su bucket di backup
aws s3 sync s3://grc-documents "s3://grc-backups/${TIMESTAMP}/documents" --quiet
echo "Storage sync OK"

# 3. Verifica integrità dump
pg_restore --list "${BACKUP_DIR}/db.dump" > /dev/null
echo "Verifica integrita OK"

# 4. Cleanup backup scaduti
find /backups -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} +

echo "Backup completato: ${BACKUP_DIR}"
```

### Procedura test restore mensile

Eseguire ogni primo lunedi del mese. Documentare il risultato come evidenza in M16 BCP.

```bash
# 1. Verifica restore in ambiente isolato
gunzip -c /backup/grc_YYYYMMDD.sql.gz | psql -U grc grc_test

# Oppure con formato custom pg_dump:
# pg_restore -d grc_test_restore "${LATEST_BACKUP}/db.dump"

# 2. Verifica hash chain audit trail
python manage.py verify_audit_trail_integrity --db grc_test_restore

# 3. Smoke test applicativo
python manage.py test tests.smoke --keepdb --settings=core.settings.test_restore

# 4. Documentare risultato come evidenza in M16 BCP
```

---

## Monitoraggio e alerting

### Health check endpoint

```
GET /api/health/
-> { "status": "ok", "db": "ok", "redis": "ok", "storage": "ok", "version": "1.2.0" }

GET /api/health/detailed/    # solo IP interni -- include metriche Celery e sync KB4
```

### Metriche chiave (Prometheus)

| Metrica | Warning | Critico |
|---------|---------|---------|
| `grc_api_latency_p99_ms` | > 500 | > 2000 |
| `grc_db_pool_used_pct` | > 80% | > 95% |
| `grc_celery_queue_length` | > 100 | > 500 |
| `grc_audit_chain_integrity` | — | `false` |
| `grc_nis2_timer_remaining_min` | < 120 | < 30 |
| `grc_ai_sanitizer_errors_5m` | > 0 | > 5 |

### Alert P1 — risposta immediata

- Audit trail chain rotta (integrità SHA-256 fallita)
- NIS2 timer < 30 minuti senza notifica inviata
- Database non raggiungibile
- Sanitizer M20 che espone dati non anonimizzati

### Log strutturati (JSON)

```json
{
  "timestamp": "2026-03-13T10:00:00Z",
  "level": "INFO",
  "module": "M09",
  "action": "incident.created",
  "plant_id": "PLT-001",
  "user_id": "USR-042",
  "incident_id": "INC-2026-0042",
  "nis2_notifiable": "da_valutare",
  "request_id": "req-abc123"
}
```

---

## Scalabilità

### Horizontal scaling backend

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: grc-backend-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: grc-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### PostgreSQL read replicas

I job pesanti (M18 export report, M17 evidence pack) vengono indirizzati alla replica di lettura — nessun impatto sulle operazioni transazionali OLTP.

```
Primary (write)  -->  Replica 1  (read -- dashboard M18, export M17)
                 -->  Replica 2  (read -- audit trail queries M10)
```

---

## AI Engine — infrastruttura M20

### Installazione Ollama (modello locale)

```bash
# Installazione
curl -fsSL https://ollama.ai/install.sh | sh
systemctl enable ollama && systemctl start ollama

# Download modello in base alla RAM disponibile
ollama pull llama3.1:8b      # 8 GB -- classificazioni rapide
ollama pull llama3.1:70b     # 40 GB -- analisi testo complessa

# Test
curl http://localhost:11434/api/generate \
  -d '{"model":"llama3.1:8b","prompt":"Classifica questa severita: accesso non autorizzato a PLC","stream":false}'
```

### Regole sanitization (dati verso cloud)

| Tipo dato | Trasformazione | Esempio |
|-----------|---------------|---------|
| Nome plant | Token fisso | "Stabilimento Milano" -> `[PLANT_A]` |
| Nome persona | Token numerato | "Mario Rossi" -> `[PERSON_1]` |
| Valore ALE | Range ordinale | "450.000 euro" -> `[VALORE_ALTO]` |
| IP / hostname | Offuscato | "192.168.1.50" -> `[IP_INTERNAL]` |
| P.IVA / C.F. | Rimosso | -> `[REMOVED]` |
| Nome fornitore | Token fisso | "Fornitore X S.r.l." -> `[SUPPLIER_A]` |

### Configurazione per funzione (settings/ai_engine.py)

```python
AI_ENGINE_CONFIG = {
    "enabled": False,                    # master switch -- off di default
    "functions": {
        "classification":    {"enabled": False, "model": "local"},
        "text_analysis":     {"enabled": False, "model": "cloud"},
        "draft_generation":  {"enabled": False, "model": "cloud"},
        "anomaly_detection": {"enabled": False, "model": "local"},
    },
    "sanitization": {
        "strip_plant_names":    True,
        "strip_person_names":   True,
        "strip_financial_values": True,
        "strip_ip_addresses":   True,
    },
    "logging": {
        "log_input_hash": True,          # mai il testo originale
        "log_output":     True,
        "log_delta":      True,
    }
}
```

---

## Checklist pre-produzione

### Sicurezza

- [ ] TLS 1.2+ configurato, certificato valido e non scaduto
- [ ] Header di sicurezza HTTP presenti (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
- [ ] `DEBUG=false` e `SECRET_KEY` generato (non il valore di default)
- [ ] `FERNET_KEY` generato e configurato
- [ ] Database non esposto all'esterno della rete interna
- [ ] Secrets non in chiaro nelle variabili d'ambiente Docker
- [ ] Firewall configurato (solo porte necessarie aperte)
- [ ] SSO configurato, testato e con fallback locale disabilitato
- [ ] Scadenza token auditor esterno configurata in M02
- [ ] Rate limiting verificato: login 5/min, utenti 500/h

### Operatività

- [ ] Backup automatico configurato (crontab host) e testato con restore verificato
- [ ] Monitoraggio e alerting attivi (P1 su audit trail e NIS2 timer)
- [ ] Log centralizzati (ELK / Loki / CloudWatch)
- [ ] Health check risponde correttamente su tutti i componenti: `curl /api/health/`
- [ ] Celery beat attivo: `celery -A core inspect scheduled`
- [ ] Tutti i task schedulati presenti nella tabella Celery Beat
- [ ] Job verifica integrità audit trail: `python manage.py verify_audit_trail_integrity`

### Framework normativi e dati

- [ ] VDA ISA 6.0, NIS2 Art.21, ISO 27001:2022 importati via `load_frameworks`
- [ ] `load_notification_profiles` eseguito
- [ ] `load_competency_requirements` eseguito
- [ ] `load_required_documents` eseguito
- [ ] `ControlInstance` generate per tutti i plant attivi
- [ ] `nis2_scope` configurato correttamente per ogni plant
- [ ] Almeno un CISO con `RoleAssignment` attiva in M00

### AI Engine (solo se abilitato)

- [ ] Sanitization layer testato: nessun PII passa nel log cloud
- [ ] Modello locale Ollama risponde correttamente
- [ ] Cloud API key configurata e testata
- [ ] `AiInteractionLog` popola correttamente M10
- [ ] Human-in-the-loop verificato end-to-end per ogni funzione abilitata
