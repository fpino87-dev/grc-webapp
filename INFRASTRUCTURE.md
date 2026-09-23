# INFRASTRUCTURE.md — govrico

> Architettura infrastrutturale, stack tecnologico, deployment, database, sicurezza, backup e monitoraggio.
> Descrive ciò che il repository fornisce; dove una scelta spetta a chi gestisce l'installazione (es. monitoraggio centralizzato) è indicato come raccomandazione.

---

## Indice

- [Panoramica architetturale](#panoramica-architetturale)
- [Stack tecnologico](#stack-tecnologico)
- [Porte in uso](#porte-in-uso)
- [Variabili d'ambiente obbligatorie](#variabili-dambiente-obbligatorie)
- [Deployment produzione — step by step](#deployment-produzione--step-by-step)
- [Reverse proxy](#reverse-proxy)
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
  Browser --> Reverse proxy HTTPS (nginx sull'host o Nginx Proxy Manager, 80/443)
                  |                         |
             Frontend                  Backend API
             React SPA (nginx)         Django + DRF (gunicorn)
             127.0.0.1:3001            127.0.0.1:8000
                                            |
                        +-------------------+------------------+
                        |                   |                  |
                   PostgreSQL 17          Redis 7         File caricati
                   (volume pgdata)        broker +        /srv/grc/media
                                          cache           (bind mount)
                        |
                Celery worker + Celery Beat
                (scadenze, promemoria, backup notturno,
                 KPI, OSINT, pulizie)

                        |
                +-------+--------+
                |  AI Engine M20 |  <- opzionale
                |  Ollama locale |
                |  + Sanitizer   |--> Provider cloud (testo sanitizzato)
                +----------------+

  Integrazioni esterne:
  SMTP aziendale · Sentry (opzionale) · enricher CTI dell'OSINT Monitor
```

---

## Stack tecnologico

### Backend

| Componente | Tecnologia | Versione |
|-----------|-----------|---------|
| Runtime | Python | 3.11 |
| Framework | Django + Django REST Framework | 5.2 LTS + DRF 3.17 |
| Application server | Gunicorn (gthread) | — |
| Task queue | Celery + django-celery-beat | 5.4 |
| Broker / cache | Redis | 7 |
| Auth | SimpleJWT (JWT + blacklist) + MFA TOTP | 5.5 |
| i18n | Django i18n (`.po` IT/EN/FR/PL/TR) | — |
| Cifratura | cryptography (Fernet, AES-256-GCM per i backup) | — |
| MIME check | python-magic | — |
| Error monitoring | sentry-sdk (opzionale) | 2.x |

### Frontend

| Componente | Tecnologia | Versione |
|-----------|-----------|---------|
| Framework | React | 18 |
| Language | TypeScript | 5 |
| Build | Vite | 8 |
| State management | Zustand | 5 |
| Data fetching | TanStack Query | 5 |
| Router | React Router | 7 |
| i18n | i18next + react-i18next | 23 |
| UI | Tailwind CSS | 3 |
| Charts | Recharts | 2 |

### Database e storage

| Componente | Tecnologia | Note |
|-----------|-----------|------|
| Database principale | PostgreSQL | 17 in produzione (`postgres:17-alpine`), 16 nello stack di sviluppo |
| Cache / broker | Redis | 7, con password in produzione |
| File caricati | Filesystem (`MEDIA_ROOT`) | in produzione bind mount `/srv/grc/media`, condiviso da backend e worker Celery |

### Infrastruttura

| Componente | Tecnologia |
|-----------|-----------|
| Container | Docker + Docker Compose v2 (`docker-compose.prod.yml`, `Dockerfile.prod`) |
| Reverse proxy | nginx sull'host (installato da `manual/install_grc.sh`) oppure Nginx Proxy Manager |
| Installazione guidata | `manual/install_grc.sh` (Ubuntu 24.04 / 26.04 LTS) |
| CI | GitHub Actions: `tests` (pytest, ruff, migrazioni, vitest, eslint, tsc), `security-audit` (pip-audit, npm audit), `sbom` (CycloneDX a ogni release), CodeQL |
| Secrets | file `.env.prod` (permessi 600) — vedi [Secrets management](#secrets-management) |

---

## Porte in uso

| Servizio | Porta host dev | Porta host prod | Porta container |
|----------|---------------|----------------|----------------|
| Backend Django | 8001 | 127.0.0.1:8000 (+ 127.0.0.1:8001 con `install_grc.sh`) | 8000 |
| Frontend | 3001 (Vite) | 3001 (nginx; 127.0.0.1 con `install_grc.sh`) | 3000 dev / 80 prod |
| PostgreSQL | 5433 | non esposta | 5432 |
| Redis | non esposta | non esposta | 6379 |
| MinIO console | 9001 | — | 9001 (solo sviluppo, l'applicazione salva i file su filesystem) |
| Mailhog SMTP | 1026 | — | 1025 |
| Mailhog UI | 8026 | — | 8025 |
| Ollama (opzionale) | — | 127.0.0.1:11434 | 11434 |

**Altri container sul server (non toccare):**
- `ai-docintel-*` — progetto separato
- `npm` — Nginx Proxy Manager su 80/443
- `budget-db`, `sitebudget`, `siteciso`, `sitebb`

---

## Variabili d'ambiente obbligatorie

Il repository include `.env.example` (sviluppo) e `.env.prod.example` (produzione) con tutti i placeholder. Non committare mai i file `.env` o `.env.prod` — sono in `.gitignore`.

### Tabella variabili principali

| Variabile | Obbligatoria | Default | Descrizione |
|-----------|-------------|---------|-------------|
| `SECRET_KEY` | Sì | — | Chiave Django (min 50 caratteri: `secrets.token_urlsafe(50)`) |
| `FERNET_KEY` | Sì | — | Cifratura delle credenziali SMTP salvate nel DB (`Fernet.generate_key()`) |
| `DEBUG` | No | `False` in prod | `false` in produzione |
| `ALLOWED_HOSTS` | Sì in prod | — | Host ammessi, separati da virgola |
| `FRONTEND_URL` | Sì | — | URL pubblico del frontend (CORS, link nelle email); validato all'avvio in prod |
| `CSRF_TRUSTED_ORIGINS` | Sì in prod | — | Origini HTTPS da cui arrivano i POST |
| `DRF_NUM_PROXIES` | No | `1` | Proxy fidati davanti a Django (IP reale del client per rate limit e audit) |
| `ADMIN_URL` | Consigliata | `admin/` | Percorso non prevedibile dell'admin Django |
| `DATABASE_URL` | Sì | — | Connessione PostgreSQL |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Sì in prod | — | Credenziali del container PostgreSQL |
| `REDIS_URL` / `REDIS_PASSWORD` | Sì | — | Connessione e password Redis |
| `BACKUP_ENCRYPTION_KEY` | Consigliata | vuota | Cifra gli archivi di backup; **distinta** da `FERNET_KEY`; senza di essa i backup cifrati non si ripristinano |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | No | — | SMTP di fallback; la configurazione operativa si fa dall'app (Impostazioni → Email) |
| `CELERY_CONCURRENCY` | No | `4` | Processi del worker Celery |
| `KPI_INGEST_API_KEY` | No | vuota | Chiave per l'invio di KPI da sistemi esterni (M18) |
| `SENTRY_DSN` / `VITE_SENTRY_DSN` | No | vuota | Error monitoring backend / frontend (disattivo se vuoto) |
| `APP_VERSION` / `VITE_APP_VERSION` | No | — | Versione riportata a Sentry |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | No | `True` in prod | Cookie solo su HTTPS |

Note:
- **AI Engine**: provider (Anthropic, OpenAI, Google, Mistral, Groq, Ollama locale), chiavi, modelli, routing per funzione e budget si configurano **dall'app** (Impostazioni → AI Engine) e sono salvati nel DB. Le variabili `AI_ENGINE_ENABLED`, `AI_LOCAL_*`, `AI_CLOUD_PROVIDER`, `AZURE_OPENAI_KEY` e `ANTHROPIC_API_KEY` presenti negli esempi non sono lette dal codice.
- **Audit trail**: non esiste una retention per cancellazione (il log è immutabile); le variabili `AUDIT_TRAIL_RETENTION_*` non hanno effetto.
- **`STORAGE_BACKEND`**: i file sono salvati su filesystem; la variabile non ha effetto.

### Riferimento `.env.prod`

Il modello completo e commentato è `.env.prod.example`. Estratto delle voci essenziali:

```bash
# ── Django ────────────────────────────────────────────────────────────
SECRET_KEY=<stringa-generata-min-50-char>
DEBUG=false
ALLOWED_HOSTS=grc.azienda.com
FRONTEND_URL=https://grc.azienda.com
CSRF_TRUSTED_ORIGINS=https://grc.azienda.com
DRF_NUM_PROXIES=1
ADMIN_URL=<uuid>/

# ── PostgreSQL / Redis ────────────────────────────────────────────────
DATABASE_URL=postgresql://grc:<password>@db:5432/grc_prod
POSTGRES_DB=grc_prod
POSTGRES_USER=grc
POSTGRES_PASSWORD=<password>
REDIS_URL=redis://:<password>@redis:6379/0
REDIS_PASSWORD=<password>

# ── Cifratura ─────────────────────────────────────────────────────────
FERNET_KEY=<chiave-fernet>
BACKUP_ENCRYPTION_KEY=<secrets.token_urlsafe(48)>

# ── Email (fallback: la configurazione operativa si fa dall'app) ─────
EMAIL_HOST=smtp.azienda.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=govrico <grc-noreply@azienda.com>

# ── Sentry (opzionale) ────────────────────────────────────────────────
SENTRY_DSN=
VITE_SENTRY_DSN=
```

---

## Deployment produzione — step by step

### Requisiti server minimi

- 4 CPU, 8 GB RAM (16 GB se si abilita l'IA locale), 100 GB SSD
- Docker Engine recente + Docker Compose v2 (≥ 2.24.4 per l'override del frontend di `install_grc.sh`)
- Ubuntu 24.04 o 26.04 LTS (consigliati)
- Accesso SSH con utente sudoer

### Installazione guidata

`manual/install_grc.sh` (eseguito come root) installa Docker, nginx con certificato self-signed, UFW, genera `.env.prod` con tutte le chiavi, avvia lo stack, carica i dati di riferimento, programma il backup notturno e crea il superuser. Dal suo menu si fanno anche aggiornamento (backup completo, anteprima delle migrazioni dei dati e conferma), restart, log e stato.

### Procedura manuale

**1. Docker Engine + Compose v2**

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # logout/login per applicare il gruppo
docker --version && docker compose version
```

**2. Clone repository**

```bash
git clone https://github.com/fpino87-dev/grc-webapp.git
cd grc-webapp
```

**3. Variabili di produzione**

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod
nano .env.prod        # compilare tutti i valori, nessun placeholder

# chiavi
python3 -c "import secrets; print(secrets.token_urlsafe(50))"                               # SECRET_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # FERNET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"                               # BACKUP_ENCRYPTION_KEY
```

**4. Cartella dei file caricati**

```bash
sudo mkdir -p /srv/grc/media
```

**5. Build, avvio e permessi**

```bash
make prod-build
make prod-up
# il backend gira come utente non-root `grc`: rende scrivibili media e backup
docker compose -f docker-compose.prod.yml exec --user root backend chown -R grc:grc /app/media /app/backups
```

**6. Migrazioni e dati di riferimento**

```bash
make prod-migrate
make prod-seed            # framework, profili notifica, competenze, requisiti di ruolo,
                          # documenti richiesti, controlli provati dalla formazione (idempotente)
# solo alla prima installazione: aggiorna anche le policy di organizzazione esistenti
docker compose -f docker-compose.prod.yml exec backend python manage.py load_document_workflow_policies
# backup automatico notturno (02:00)
docker compose -f docker-compose.prod.yml exec backend python manage.py schedule_backup_task
```

**7. Superuser iniziale**

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

**8. Reverse proxy** — vedi [Reverse proxy](#reverse-proxy)

**9. Verifica**

```bash
make prod-check                               # manage.py check --deploy
curl -s http://127.0.0.1:8000/api/health/     # {"status": "ok", "db": true, ...}
docker compose -f docker-compose.prod.yml exec backend python manage.py verify_schedule
```

**Aggiornamenti di versione**: leggere prima la sezione della release nel `CHANGELOG.md`, che riporta la sequenza di deploy quando servono passi particolari (es. anteprime prima di `migrate`). Dopo ogni aggiornamento del codice dei task o della schedule: `docker compose -f docker-compose.prod.yml restart celery celery-beat`.

### Docker Compose sviluppo — estratto

```yaml
services:
  db:
    image: postgres:16-alpine
    ports: ["5433:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  backend:
    command: python manage.py runserver 0.0.0.0:8000
    volumes: [./backend:/app]           # codice montato: autoreload
    ports: ["8001:8000"]

  celery:
    command: celery -A core worker -l info --concurrency 2
    volumes: [./backend:/app]           # NB: dopo modifiche al codice → restart celery

  celery-beat:
    command: celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

  frontend:
    volumes: [./frontend:/app, /app/node_modules]
    ports: ["3001:3000"]

  mailhog:
    image: mailhog/mailhog
    ports: ["1026:1025", "8026:8025"]
```

---

## Reverse proxy

Il reverse proxy termina TLS e inoltra:
- `/api/`, `/<ADMIN_URL>`, `/static/`, `/media/` → backend `127.0.0.1:8000`
- tutto il resto → frontend `127.0.0.1:3001`

Header da inoltrare al backend: `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` (Django usa `SECURE_PROXY_SSL_HEADER` per riconoscere HTTPS). Dimensione massima upload consigliata: `client_max_body_size 50m`.

**nginx sull'host** — configurato da `install_grc.sh` (redirect 80→443, TLS 1.2/1.3, HSTS).

**Nginx Proxy Manager** — il backend è pubblicato solo su `127.0.0.1:8000`: se NPM gira in un container, deve usare la rete dell'host oppure raggiungere l'host tramite il bridge Docker con un binding del backend adeguato; il frontend è su `3001`. Attivare "Force SSL" e il certificato Let's Encrypt. Dettagli in [manual/HowtoDeploy.md](./manual/HowtoDeploy.md).

---

## Database

### Principi di design

- **Ereditarietà degli asset**: modello `Asset` base e tabelle figlie `AssetIT`, `AssetOT`, `AssetSW`, `AssetFacility` (multi-table inheritance) con gli attributi specifici
- **Audit trail append-only**: tabella `audit_log` protetta da trigger PostgreSQL che rifiuta UPDATE e DELETE; nessuna cancellazione per retention
- **Hash chain**: ogni record contiene `prev_hash` e `record_hash` (SHA-256), serializzati con `select_for_update`; verifica con `verify_audit_trail_integrity`
- **Soft delete globale**: `deleted_at` con filtro nel manager di default; purge definitivo solo manuale (`purge_soft_deleted`, dry-run salvo `--apply`)
- **Chiavi UUID** su tutti i modelli di dominio (`core.models.BaseModel`)

### Indici

Gli indici sono definiti nei modelli (`db_index=True` e `Meta.indexes`) sui campi di filtro frequenti — stato, scadenze, score, validità, perimetro — per `Task`, `Incident`, `ControlInstance`, `RiskAssessment`, `Document`, `Evidence`, `ManagementReview` e altri, e creati dalle migrazioni. I vincoli di unicità "solo fra i record non eliminati" sono `UniqueConstraint` condizionali.

### Trigger append-only per audit trail

Definito nella migrazione `core/migrations/0002_audit_trigger.py`:

```sql
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Audit trail is append-only -- UPDATE and DELETE are not allowed';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
```

---

## Storage file

I file caricati (documenti, evidenze, loghi, NDA) sono salvati su filesystem in `MEDIA_ROOT` (`/app/media` nel container, bind mount `/srv/grc/media` in produzione). Il volume **deve** essere montato sia sul backend (upload) sia sul worker Celery (ripristino dei backup).

```
media/
├── documents/{document_id}/v{n}/{nome_file}     # versioni dei documenti (M07), con SHA-256 in DB
├── evidences/{evidence_id}/{nome_file}          # evidenze dei controlli
└── ...                                         # loghi dei siti, allegati di altri moduli
```

### Conservazione

| Tipo | Conservazione | Note |
|------|---------------|------|
| Documenti ed evidenze | Illimitata | Eliminazione logica (soft delete); purge manuale con `purge_soft_deleted` |
| Audit trail | Permanente | Immutabile, email pseudonimizzata |
| Log interazioni IA | 365 giorni | `cleanup_ai_interaction_logs` mensile (`AI_LOG_RETENTION_DAYS`) |
| Risultati task Celery | 7 giorni | `cleanup_celery_results` |
| Backup | 30 giorni | pulizia automatica nel task di backup |

---

## Celery — task schedulati

La schedule è definita in `CELERY_BEAT_SCHEDULE` (`core/settings/base.py`) e sincronizzata nel DB (`django_celery_beat`); il backup notturno è registrato a parte da `schedule_backup_task`. `python manage.py verify_schedule` confronta le due cose. Orari nel fuso `Europe/Rome`.

| Task | Schedule | Modulo |
|------|----------|--------|
| Backup automatico (DB + file) e pulizia backup scaduti | ogni notte 02:00 | Backup |
| `check_expired_evidences` | ogni notte 02:05 | M03/M07 |
| `check_expired_bcp_plans` | ogni notte 02:10 | M16 |
| `check_control_reviews_due` | ogni notte 02:15 | M03 |
| `roll_recurring_tasks` | ogni notte 02:20 | M08 |
| `check_maintenance_due` | ogni notte 02:25 | M04 |
| `check_schedule_deadlines` | ogni notte 02:30 | M08 |
| `recompute_expired_risk_adj_task` | ogni notte 02:45 | M14 |
| `cleanup_celery_results` | ogni notte 03:30 | — |
| `check_enricher_health` | ogni notte 03:30 | OSINT |
| `cleanup_ai_interaction_logs` | il 1° del mese 03:45 | M20 |
| `generate_scheduled_checklists` | ogni giorno 07:00 | M08 |
| `check_expiring_risk_acceptances` | ogni giorno 07:20 | M06 |
| `notify_expiring_documents` | ogni giorno 07:45 | M07 |
| `remind_unapproved_mandatory_documents` | ogni giorno 07:50 | M07 |
| `notify_expiring_roles_task` | ogni giorno 08:00 | M00 |
| `remind_training_plan_items_task` | ogni giorno 08:10 | M15 |
| `notify_blocked_pdca_task` | ogni giorno 08:30 | M11 |
| `check_overdue_findings` | ogni giorno 08:45 | M17 |
| `check_final_report_deadlines` | ogni giorno 09:00 | M09 |
| `check_nis2_deadlines` | ogni 30 minuti | M09 |
| `weekly_scan` | lunedì 04:00 | OSINT |
| `push_kpis` | lunedì 05:30 | OSINT |
| `generate_weekly_kpi_snapshots` | lunedì 06:00 | M18 |
| `compute_operational_kpis` | lunedì 06:30 | M08/M18 |
| `check_unrevalued_changes` | lunedì 07:00 | M04 |
| `sync` (Centro Operativo) | lunedì 07:15 | M21 |
| `check_software_eos` | lunedì 07:15 | M04 |
| `check_upcoming_audits` | lunedì 07:30 | M17 |
| `evaluate_objectives_task` | lunedì 07:45 | M00 |
| `check_stale_audit_preps` | lunedì 08:15 | M17 |
| `check_questionnaire_followups_task` | lunedì 09:30 | M14 |

I task critici usano `autoretry` con backoff esponenziale.

### Verifica stato Celery

```bash
docker compose exec celery celery -A core inspect ping
docker compose exec celery celery -A core inspect active
docker compose exec backend python manage.py verify_schedule
docker compose logs celery --tail=50 -f
docker compose logs celery-beat --tail=50 -f
```

I processi Celery non ricaricano il codice a caldo: dopo ogni modifica ai task o a `CELERY_BEAT_SCHEDULE` va eseguito `docker compose restart celery celery-beat`.

---

## Sicurezza infrastrutturale

### TLS e header HTTP

- **Reverse proxy**: TLS 1.2/1.3, redirect 80→443, HSTS.
- **Frontend** (`frontend/nginx.conf`): `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` restrittiva, `Content-Security-Policy` con `default-src 'self'` e `frame-ancestors 'none'`.
- **Django** (`core.settings.prod`): `SECURE_HSTS_SECONDS` (2 anni, subdomain, preload), `SECURE_SSL_REDIRECT`, cookie `Secure`, `SECURE_PROXY_SSL_HEADER`.

### Regole firewall

| Porta | Sorgente | Destinazione | Motivo |
|-------|---------|-------------|--------|
| 22 | Amministratori | Server | SSH |
| 80 | Internet | Reverse proxy | Redirect a 443 |
| 443 | Internet | Reverse proxy | UI e API |
| 443 (uscita) | Backend / Celery | Provider IA cloud, enricher OSINT, Sentry | Solo se configurati |
| 587 (uscita) | Backend / Celery | SMTP | Notifiche |

Backend, frontend, PostgreSQL, Redis e Ollama non sono esposti all'esterno: Docker pubblica le porte scavalcando UFW, per questo i servizi sono legati a `127.0.0.1`.

### Sicurezza API e sessioni

- JWT SimpleJWT: access token **30 minuti**, refresh **7 giorni**, rotazione e blacklist; MFA TOTP con dispositivi fidati.
- Rate limiting DRF: **anonimi 20/h**, **utenti 2000/h**, **login 5/min**; limiti separati per chiamate IA ed export.
- File upload: whitelist estensioni + MIME type reale (python-magic).
- Password: minimo 12 caratteri + CommonPassword, NumericPassword, UserAttributeSimilarity.
- Errori imprevisti: dettaglio solo nei log del server, messaggio generico al client.

### Secrets management

- `.env.prod` con permessi `600`, fuori dal repository.
- `FERNET_KEY` cifra le credenziali SMTP salvate nel DB; `BACKUP_ENCRYPTION_KEY` (distinta) cifra i backup.
- Copiare `BACKUP_ENCRYPTION_KEY` fuori dal server: senza, i backup cifrati non si ripristinano.
- Per esigenze più strette (Vault, secret manager del cloud) le variabili si possono iniettare nell'ambiente dei container al posto del file; il repository non include un'integrazione dedicata.

---

## Backup e disaster recovery

### Backup applicativo

Il modulo **Backup** (Impostazioni → Backup) produce archivi completi `.tar` con il dump del database (`database.dump`) e l'albero dei file caricati, cifrati se `BACKUP_ENCRYPTION_KEY` è impostata. Gli archivi sono nel volume `backupdata` (`/app/backups`).

- **Automatico**: ogni notte alle 02:00 (`schedule_backup_task`), con eliminazione dei backup più vecchi di 30 giorni
- **Manuale**: pulsante «Crea backup»
- **Download e import** di un archivio dall'interfaccia (import compatibile anche con i vecchi `.dump` solo database)
- **Ripristino**: asincrono dal worker Celery; sostituisce database e cartella dei file

### Copia fuori dal server

Il volume dei backup è sullo stesso host: copiare periodicamente gli archivi altrove (NAS, storage di rete, bucket). Esempio con cron sull'host:

```bash
# copia notturna degli archivi del volume backupdata
30 4 * * * rsync -a /var/lib/docker/volumes/grc-webapp_backupdata/_data/ backup-host:/backup/govrico/
```

### Obiettivi RTO / RPO indicativi

| Scenario | RPO | RTO |
|----------|-----|-----|
| Corruzione dati / errore umano | Ultimo backup (max 24h) | 15-60 min (ripristino da interfaccia) |
| Perdita del server | Ultima copia fuori server | Reinstallazione + ripristino (ore) |

### Test di ripristino periodico

Eseguire almeno ogni trimestre, in un ambiente separato, e registrare l'esito come evidenza in M16 BCP:

1. Installare un'istanza pulita (es. con `install_grc.sh`) con la stessa `BACKUP_ENCRYPTION_KEY`
2. Importare l'archivio da Impostazioni → Backup e avviare il ripristino
3. Verificare la catena dell'audit: `python manage.py verify_audit_trail_integrity`
4. Controllare a campione documenti, evidenze e loghi

---

## Monitoraggio e alerting

### Health check endpoint

```
GET /api/health/
-> 200 {"status": "ok", "db": true, "schedule": {"expected": N, "problems": [...]}}
-> 503 {"status": "error", "db": false, ...}          # database non raggiungibile
```

`schedule` segnala task periodici mancanti o disallineati rispetto a `CELERY_BEAT_SCHEDULE` (informativo, non cambia lo stato HTTP).

### Cosa monitorare

Il repository non include uno stack di metriche: si consiglia un monitor esterno su
- `GET /api/health/` (stato e `schedule.problems`)
- container `backend`, `celery`, `celery-beat` in esecuzione (`docker compose ps`)
- spazio disco di `/srv/grc/media` e del volume dei backup
- esito del backup notturno (Impostazioni → Backup)
- integrità dell'audit trail: `verify_audit_trail_integrity` pianificato periodicamente

### Error monitoring

Sentry (opzionale) su backend (Django, Celery, Redis) e frontend (React), attivo se `SENTRY_DSN` / `VITE_SENTRY_DSN` sono valorizzati. Configurazione GDPR-safe: `send_default_pii=False`, header Authorization rimosso, Session Replay disattivo di default e con testo mascherato.

### Log

I container scrivono su stdout/stderr in formato testo (`livello data modulo processo thread messaggio`); si leggono con `docker compose logs`. Nei log non finiscono dati personali (email, CF, telefono): solo conteggi o identificatori. Per la raccolta centralizzata usare il logging driver di Docker verso il sistema aziendale.

---

## Scalabilità

L'installazione di riferimento è un singolo host con Docker Compose. Leve disponibili:
- **Backend**: worker e thread di gunicorn in `backend/Dockerfile.prod` (default 4 worker × 2 thread)
- **Celery**: `CELERY_CONCURRENCY` (default 4) e `--max-tasks-per-child`
- **Database**: risorse del container PostgreSQL; indici già definiti sui filtri frequenti

Orchestratori (Kubernetes, Swarm) e repliche di lettura non sono inclusi nel repository.

---

## AI Engine — infrastruttura M20

### Modello locale (Ollama)

`install_grc.sh` può aggiungere Ollama come container (`127.0.0.1:11434`) e scaricare un modello adatto alla RAM (es. `llama3.2:3b` solo CPU, `llama3.1:8b` con GPU e ≥ 32 GB). In alternativa installarlo sull'host:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
curl http://localhost:11434/api/generate -d '{"model":"llama3.2:3b","prompt":"ok","stream":false}'
```

L'endpoint locale (es. `http://ollama:11434` o `http://host.docker.internal:11434`) si imposta nell'app.

### Configurazione

Tutto si configura da **Impostazioni → AI Engine** (modello `AiProviderConfig` nel DB): provider cloud e chiave, modello cloud e locale (con catalogo aggiornato dal provider), routing locale/cloud **per funzione**, fallback, budget mensile di token. Senza una configurazione attiva le funzioni IA rispondono «IA non configurata».

### Sanitizzazione (dati verso il cloud)

| Tipo dato | Trasformazione |
|-----------|---------------|
| Nomi e codici dei siti | Token (`[PLANT_A]`, `[PLANT_B]`, …), ripristinati nella risposta |
| Indirizzi IP | `[IP_REMOVED]` |
| Email | `[EMAIL_REMOVED]` |
| Telefoni | `[PHONE_REMOVED]` |
| Codice fiscale | `[CF_REMOVED]` |
| Partita IVA | `[PIVA_REMOVED]` |
| Nomi delle persone (riesame M13) | pseudonimizzati prima dell'invio |
| Dati OSINT | anonimizzati dall'`AnonymizationService` |

Ogni interazione è registrata in `AiInteractionLog` con l'hash dell'input (mai il testo), l'output e l'esito della revisione umana (conservazione 365 giorni). Nessun output IA è applicato senza conferma di una persona.

---

## Checklist pre-produzione

### Sicurezza

- [ ] TLS 1.2+ con certificato valido
- [ ] Header di sicurezza presenti (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
- [ ] `DEBUG=false`, `SECRET_KEY`, `FERNET_KEY` e `BACKUP_ENCRYPTION_KEY` generate
- [ ] `ADMIN_URL` non prevedibile
- [ ] `.env.prod` con permessi 600; `BACKUP_ENCRYPTION_KEY` copiata fuori dal server
- [ ] Backend, frontend, database e Redis non raggiungibili dall'esterno (solo 80/443)
- [ ] Firewall configurato (22, 80, 443)
- [ ] MFA attiva per gli amministratori
- [ ] Scadenza dei token auditor esterno configurata in M02
- [ ] Rate limiting verificato: login 5/min, utenti 2000/h

### Operatività

- [ ] `/srv/grc/media` e `/app/backups` scrivibili dall'utente `grc`
- [ ] Backup notturno programmato (`schedule_backup_task`), un backup manuale riuscito e un ripristino di prova documentato
- [ ] Copia degli archivi di backup fuori dal server
- [ ] `GET /api/health/` risponde 200 senza `schedule.problems`
- [ ] Celery worker e beat attivi: `celery -A core inspect ping`, `verify_schedule`
- [ ] `verify_audit_trail_integrity` senza errori
- [ ] Monitor esterno su health, container e spazio disco

### Framework normativi e dati

- [ ] `make prod-seed` eseguito (framework, profili notifica, competenze, requisiti di ruolo, documenti richiesti, controlli provati dalla formazione)
- [ ] `load_document_workflow_policies` eseguito alla prima installazione e policy verificate in Governance
- [ ] Framework assegnati ai siti e `ControlInstance` generate
- [ ] `nis2_scope` configurato per ogni sito
- [ ] Almeno un CISO con `RoleAssignment` attiva in M00

### AI Engine (solo se abilitato)

- [ ] Configurazione attiva in Impostazioni → AI Engine, con test di connessione riuscito
- [ ] Routing per funzione deciso (locale per i dati più sensibili)
- [ ] Sanitizzazione verificata: nessun dato personale nei prompt inviati al cloud
- [ ] Human-in-the-loop verificato per le funzioni abilitate
