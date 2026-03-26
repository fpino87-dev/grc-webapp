# GRC Compliance Platform

> Piattaforma GRC (Governance, Risk & Compliance) per aziende manifatturiere con certificazioni TISAX L2/L3, NIS2 e ISO 27001:2022.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Django](https://img.shields.io/badge/Django-5.1-green) ![React](https://img.shields.io/badge/React-18-blue) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-blue)

---

## Indice

- [Panoramica](#panoramica)
- [Moduli implementati](#moduli-implementati)
- [Quick start (sviluppo)](#quick-start-sviluppo)
- [Quick start (produzione)](#quick-start-produzione)
- [Architettura](#architettura)
- [Struttura repository](#struttura-repository)
- [Framework normativi supportati](#framework-normativi-supportati)
- [Flusso logico principale](#flusso-logico-principale)
- [Sicurezza](#sicurezza)
- [Variabili d'ambiente](#variabili-dambiente)
- [Comandi Makefile](#comandi-makefile)
- [Porte in uso](#porte-in-uso)
- [Integrazioni](#integrazioni)
- [Multilingua](#multilingua)
- [AI Engine M20](#ai-engine-m20)
- [Backup](#backup)
- [Documentazione](#documentazione)
- [Contribuire](#contribuire)

---

## Panoramica

La piattaforma GRC consolida in un'unica soluzione la gestione di tutti i framework di sicurezza applicabili a un'organizzazione manifatturiera multi-plant, eliminando fogli Excel distribuiti, evidenze disperse e processi manuali non tracciati.

**Caratteristiche principali:**

- 21 moduli funzionali dall'onboarding all'audit preparation (M00-M20), multilingua IT/EN/FR/PL/TR
- Struttura multi-plant con Business Unit, sub-plant e profilo NIS2 per plant
- Risk assessment IT/OT con heat map 5x5 e traduzione automatica in ALE (€)
- Workflow documentale ISO 27001 cl.7.5 con approvazione a 3 livelli e versioning SHA-256
- Gestione incidenti NIS2 con timer countdown 24h/72h/30gg e template ACN precompilato
- PDCA controller con trigger automatici e storico maturità per auditor
- Integrazione KnowBe4 bidirezionale per cybersecurity awareness
- AI Engine opzionale (M20) con human-in-the-loop e sanitization layer GDPR-safe
- Interfaccia multilingua IT · EN · FR · PL · TR

---

## Moduli implementati

| Codice | Modulo | Funzionalità principali | Stato |
|--------|--------|-------------------------|-------|
| M00 | Governance & Organigramma | Struttura organizzativa, ruoli CISO/DPO/Plant Manager, organigramma multi-plant | Implementato |
| M01 | Plant Registry | Anagrafica plant, Business Unit, profilo NIS2, sub-plant | Implementato |
| M02 | Ruoli & RBAC | Assegnazione ruoli dinamica per plant, scadenza accessi, token auditor esterno | Implementato |
| M03 | Libreria Controlli | Catalogo controlli da JSON normativi, gap analysis, stato per plant | Implementato |
| M04 | Asset Inventory IT/OT | Inventario asset con criticità 1-5, badge tooltip, change management | Implementato |
| M05 | BIA & ROI | Business Impact Analysis, calcolo RTO/RPO, traduzione ALE | Implementato |
| M06 | Risk Assessment IT/OT | Heat map 5x5, score IEC 62443, scenari OT, trattamento rischi | Implementato |
| M07 | Documenti & Evidenze | Versioning SHA-256, approvazione 3 livelli, scadenza evidenze, MIME check | Implementato |
| M08 | Scadenzario & Task | Assegnazione per ruolo, notifiche scadenza, compliance_schedule cross-modulo | Implementato |
| M09 | Gestione Incidenti | Timer NIS2 24h/72h/30gg, template ACN, escalation automatica, countdown real-time | Implementato |
| M10 | Audit Trail | Hash chain SHA-256 append-only, verify_audit_trail_integrity, partitioning per anno | Implementato |
| M11 | PDCA Controller | Ciclo Plan-Do-Check-Act, trigger automatici, storico maturità, notifica PDCA bloccati | Implementato |
| M12 | Lesson Learning & KB | Knowledge base full-text search, categorizzazione, collegamento a PDCA | Implementato |
| M13 | Revisione di Direzione | Verbali, presenze, action items, collegamento a KPI M18 | Implementato |
| M14 | Supplier Management | Anagrafica fornitori, valutazione VDA ISA 5.x, supply chain NIS2 | Implementato |
| M15 | Formazione & Awareness | Piani formativi, integrazione KnowBe4, tracking completamenti, phishing | Implementato |
| M16 | Business Continuity | Piani BCP, test DR, scadenza piani, collegamento a BIA M05 | Implementato |
| M17 | Audit Preparation | Preparazione audit TISAX/ISO/NIS2, finding, evidence pack, annulla con soft delete | Implementato |
| M18 | Reporting & Dashboard | KPI snapshot settimanale, export report, dashboard cross-modulo | Implementato |
| M19 | Notifiche & Integrazioni | Notifiche in-app, email digest, webhook SIEM, profili notifica per ruolo | Implementato |
| M20 | AI Engine *(opzionale)* | Classificazione severità, analisi RCA, bozze documenti, anomaly detection — sanitization GDPR | Implementato |

---

## Quick start (sviluppo)

### Prerequisiti

- Docker Desktop >= 4.x (o Docker Engine + Compose v2)
- Node.js >= 20 LTS (per sviluppo frontend locale)
- Python >= 3.11 (per sviluppo backend locale)

```bash
# 1. Clona e configura ambiente
git clone https://github.com/fpino87-dev/grc-webapp.git
cd grc-webapp
cp .env.example .env

# Genera SECRET_KEY (min 50 caratteri)
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Genera FERNET_KEY (cifratura AES-256 credenziali SMTP)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Inserisci i valori generati in .env

# 2. Avvia stack
docker compose up -d

# 3. Setup iniziale
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py load_frameworks
docker compose exec backend python manage.py load_notification_profiles
docker compose exec backend python manage.py load_competency_requirements
docker compose exec backend python manage.py createsuperuser

# 4. Apri http://localhost:3001
```

Per la configurazione completa in produzione vedere [INFRASTRUCTURE.md](./INFRASTRUCTURE.md).

---

## Quick start (produzione)

```bash
# 1. Configura variabili produzione
cp .env.prod.example .env.prod
# Compilare TUTTI i valori in .env.prod prima di procedere

# 2. Build e avvio
make prod-build
make prod-up

# 3. Migrazioni e dati iniziali
make prod-migrate
make prod-seed

# 4. Crea superuser iniziale
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 5. Verifica deploy
make prod-check

# 6. Configurare Nginx Proxy Manager
#    - Frontend (React): http://localhost:3001 → dominio grc.azienda.com
#    - Backend API:      http://localhost:8001 → dominio grc.azienda.com/api/*
#    - SSL Let's Encrypt con auto-renewal
```

Vedere [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) per la guida completa step-by-step al deployment produzione.

**English — full Ubuntu install (firewall, reverse proxy, TLS, env):** [manual/HowtoDeploy.md](./manual/HowtoDeploy.md)

---

## Architettura

```
Browser → Nginx Proxy Manager → Frontend React/Vite (porta 3001)
                              → Backend Django/Gunicorn (porta 8001)
                                       → PostgreSQL 16 (porta 5433)
                                       → Redis 7
                                              → Celery Worker
                                              → Celery Beat

                                       → MinIO / S3 (documenti ed evidenze)

Integrazioni esterne:
KnowBe4 API · SMTP aziendale · SSO/SAML · SIEM webhook · ACN email
AI Engine M20: Ollama/vLLM (locale) + Azure OpenAI/Anthropic (cloud, solo dati anonimi)
```

---

## Struttura repository

```
grc-webapp/
├── backend/                    # API REST — Django + DRF
│   ├── apps/
│   │   ├── governance/         # M00
│   │   ├── plants/             # M01
│   │   ├── auth_grc/           # M02
│   │   ├── controls/           # M03
│   │   ├── assets/             # M04
│   │   ├── bia/                # M05
│   │   ├── risk/               # M06
│   │   ├── documents/          # M07
│   │   ├── tasks/              # M08
│   │   ├── incidents/          # M09
│   │   ├── audit_trail/        # M10
│   │   ├── pdca/               # M11
│   │   ├── lessons/            # M12
│   │   ├── management_review/  # M13
│   │   ├── suppliers/          # M14
│   │   ├── training/           # M15
│   │   ├── bcp/                # M16
│   │   ├── audit_prep/         # M17
│   │   ├── reporting/          # M18
│   │   ├── notifications/      # M19
│   │   ├── backups/            # Backup DB (API + task)
│   │   ├── compliance_schedule/  # M08 — scadenze cross-modulo
│   │   └── ai_engine/          # M20 — opzionale
│   ├── core/                   # Settings, middleware, modelli base, audit
│   ├── frameworks/             # JSON framework normativi (ISO27001, NIS2, TISAX L2/L3)
│   ├── tests/                  # pytest — integrazione audit trail, ecc.
│   └── requirements/
├── frontend/                   # React SPA
│   └── src/
│       ├── modules/            # Pagine per modulo (M00–M20) e impostazioni
│       ├── api/endpoints/      # Client API (~24 file TS)
│       ├── i18n/               # Traduzioni IT / EN / FR / PL / TR
│       └── components/         # Shell, Sidebar, UI condivise
├── manual/                     # Manuali utente e tecnici (multi-lingua)
│   ├── MANUAL_UTENTE_{it,en,fr,pl,tr}.md
│   └── MANUAL_TECNICO_{it,en,fr,pl,tr}.md
├── CLAUDE.md                   # Istruzioni architetturali per agenti AI
├── INFRASTRUCTURE.md
├── .cursorrules
├── scripts/                    # Utility i18n (apply_translations, check hardcoded, ecc.)
├── .env.example
├── .env.prod.example
├── docker-compose.yml
├── docker-compose.prod.yml
└── Makefile
```

---

## Framework normativi supportati

- ISO/IEC 27001:2022 — 93 controlli Annex A
- TISAX L2 VDA ISA 6.0 — 40 controlli
- TISAX L3 VDA ISA 6.0 — 68 controlli (superset L2)
- NIS2 (UE 2022/2555) — misure Art.21
- IEC 62443 (semplificato) — score OT in M06

I framework sono dati, non codice: aggiungere un nuovo standard (DORA, NIST CSF 2.0, ecc.) non richiede deploy. Vedere `backend/frameworks/` e la sezione [Aggiungere un framework normativo](./manual/MANUAL_TECNICO_it.md#aggiungere-un-framework-normativo) nel manuale tecnico (IT; altre lingue in `manual/`).

| Framework | Versione | Controlli | Stato |
|-----------|----------|-----------|-------|
| VDA ISA (TISAX) | 6.0 | 83 | Incluso |
| NIS2 Art. 21 | 2022/2555 | ~20 misure | Incluso |
| ISO 27001 Annex A | 2022 | 93 | Incluso |
| IEC 62443 (semplificato) | 3-3 | Score OT in M06 | Incluso |
| DORA / NIST CSF 2.0 | — | — | Aggiungibile via JSON |

---

## Flusso logico principale

```
BIA → Risk Assessment → Controlli → Gap Analysis
  |
  v
PDCA → Lesson Learned → Management Review
  |
  v
Audit Prep → Finding → PDCA → Lesson Learned
```

---

## Sicurezza

- JWT 30min + refresh 7gg con rotazione e blacklist (SimpleJWT)
- Rate limiting: login 5/min, utenti autenticati 500/h, anonimi 20/h
- MIME check upload file con python-magic (whitelist estensioni + tipo reale)
- Fernet AES-256 per credenziali SMTP in database (FERNET_KEY)
- Password minimo 12 caratteri + validatori Django (CommonPassword, NumericPassword, UserAttributeSimilarity)
- Audit trail append-only con hash chain SHA-256 — trigger PostgreSQL impedisce UPDATE/DELETE
- Docker produzione con utente non-root + Gunicorn
- Header HTTP sicurezza: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- GDPR: `anonymize_user()` disponibile in `auth_grc/services.py`, retention automatica audit log mensile

---

## Variabili d'ambiente

Il repository include `.env.example` (sviluppo) e `.env.prod.example` (produzione) con tutti i placeholder documentati. Non committare mai i file `.env` o `.env.prod` — sono in `.gitignore`.

**Variabili obbligatorie:**

| Variabile | Obbligatoria | Default dev | Descrizione |
|-----------|-------------|-------------|-------------|
| `SECRET_KEY` | Si | — | Chiave Django (min 50 char, generare con `secrets.token_urlsafe(50)`) |
| `FERNET_KEY` | Si | — | Cifratura AES-256 credenziali SMTP (generare con `Fernet.generate_key()`) |
| `DEBUG` | No | `True` | Impostare `False` in produzione |
| `ALLOWED_HOSTS` | Si in prod | `localhost` | Host ammessi separati da virgola |
| `DATABASE_URL` | Si | `postgresql://grc:REPLACE_DB_PASSWORD@db:5432/grc_dev` | URL connessione PostgreSQL |
| `REDIS_URL` | Si | `redis://redis:6379/0` | URL connessione Redis |
| `FRONTEND_URL` | Si | `http://localhost:3001` | URL frontend (usato per CORS e link nelle email) |

Per l'elenco completo di tutte le variabili (storage, email, SSO, KnowBe4, AI Engine) vedere [INFRASTRUCTURE.md](./INFRASTRUCTURE.md#variabili-dambiente-obbligatorie).

---

## Comandi Makefile

| Target | Descrizione |
|--------|-------------|
| `make dev` | Avvia stack sviluppo (db, redis, minio, mailhog + backend + frontend) |
| `make migrate` | Esegui migrazioni Django |
| `make test` | Esegui test suite (pytest backend + npm test frontend) |
| `make lint` | Linting backend con ruff (check + format) |
| `make load-fw` | Importa framework normativi JSON (ISO27001, NIS2, TISAX) |
| `make load-competencies` | Importa requisiti competenze M15 |
| `make seed` | Carica dati demo con seed_demo |
| `make shell` | Shell Django interattiva (shell_plus) |
| `make prod-build` | Build immagini Docker produzione |
| `make prod-up` | Avvia stack produzione in background |
| `make prod-down` | Ferma e rimuove stack produzione |
| `make prod-migrate` | Esegui migrazioni Django in produzione |
| `make prod-seed` | Carica dati iniziali in produzione (frameworks, profili notifica, competenze, documenti richiesti) |
| `make prod-logs` | Log in tempo reale di tutti i servizi produzione (tail 50) |
| `make prod-shell` | Shell Django interattiva in produzione |
| `make prod-check` | Verifica configurazione deploy produzione (`manage.py check --deploy`) |

---

## Porte in uso

| Servizio | Porta host | Porta container |
|----------|-----------|----------------|
| Backend Django | 8001 | 8000 |
| Frontend Vite/Nginx | 3001 | 3000 |
| PostgreSQL GRC | 5433 | 5432 |
| Redis GRC | interno | 6379 |
| MinIO console | 9001 | 9001 |
| Mailhog SMTP | 1026 | 1025 |
| Mailhog UI | 8026 | 8025 |

---

## Integrazioni

| Sistema | Modulo | Tipo | Note |
|---------|--------|------|------|
| KnowBe4 | M15 | API REST bidirezionale | Provisioning utenti + import completamenti + phishing |
| Azure OpenAI / Anthropic | M20 | API REST — opt-in | Solo prompt sanitizzati, nessun PII |
| Ollama / vLLM | M20 | HTTP locale | Modello on-prem per classificazioni |
| SMTP aziendale | M19 | SMTP | Notifiche e digest email, credenziali cifrate Fernet |
| SSO / LDAP | M02 | OAuth2 / SAML | Autenticazione aziendale |
| SIEM / SOC | M19 | Webhook uscente | Feed eventi sicurezza real-time |
| ACN (NIS2) | M09 | Email uscente | Template notifica precompilato |

---

## Multilingua

La piattaforma supporta 5 lingue a tutti i livelli: UI, libreria controlli, email, export PDF/Excel, audit trail.

| Lingua | Codice | Note |
|--------|--------|------|
| Italiano | `it` | Lingua principale |
| Inglese | `en` | Fallback globale |
| Francese | `fr` | |
| Polacco | `pl` | |
| Turco | `tr` | |

Ogni nuova chiave i18n deve essere tradotta contestualmente in tutte e 5 le lingue nei file `frontend/src/i18n/<lang>/common.json`. Non lasciare mai chiavi parzialmente tradotte.

---

## AI Engine M20

Opzionale, disabilitato di default, opt-in per funzione:

| Funzione | Esecuzione | Moduli coinvolti |
|----------|-----------|-----------------|
| Classificazione severità / criticità | Modello locale | M04, M07, M09 |
| Analisi testo RCA / gap analysis | Cloud (sanitizzato) | M06, M09, M12 |
| Generazione bozze documenti / notifiche | Cloud (sanitizzato) | M07, M09 |
| Anomaly detection scadenze / incidenti | Locale + cloud | M08, M09 |

Garanzie di sicurezza: nessun PII o valore ALE raggiunge il cloud LLM, sanitization layer obbligatorio on-prem, human-in-the-loop su ogni output, `AiInteractionLog` in M10 con hash input e delta umano.

---

## Backup

Backup rapido del database:

```bash
docker exec grc-webapp-db-1 pg_dump -U grc grc_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

Per la strategia completa di backup, crontab host, pulizia automatica, backup file media, procedura di restore verificato e obiettivi RTO/RPO vedere [INFRASTRUCTURE.md](./INFRASTRUCTURE.md#backup-e-disaster-recovery).

---

## Documentazione

| File | Contenuto |
|------|-----------|
| [README.md](./README.md) | Questo file — panoramica, quick start, moduli, architettura |
| [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) | Stack tecnologico, deployment step-by-step, DB, backup, sicurezza, monitoraggio, Celery tasks |
| [manual/MANUAL_UTENTE_it.md](./manual/MANUAL_UTENTE_it.md) | Manuale utente (IT; versioni EN/FR/PL/TR in `manual/`) |
| [manual/MANUAL_TECNICO_it.md](./manual/MANUAL_TECNICO_it.md) | Manuale tecnico — API, modelli, framework, AI Engine, test (IT; altre lingue in `manual/`) |
| [manual/HowtoDeploy.md](./manual/HowtoDeploy.md) | **Deploy (English)** — Ubuntu server, Docker, firewall, reverse proxy, TLS, environment variables |
| [CLAUDE.md](./CLAUDE.md) | Istruzioni architetturali per agenti AI e sviluppatori |

### Stato implementazione ultime feature

- **Soft delete e rimozione accesso**: eliminazione logica (soft delete) con regole di business in `services.py` per istanze controlli, documenti ed evidenze, asset IT/OT, plant, archiviazione framework; rimozione accesso GRC utente (super_admin) con audit dove previsto.
- **M17 Audit Preparation**: eliminazione sicura con soft delete e azione di annullamento (`annulla`) che archivia il prep solo se tutti i finding sono chiusi, con audit trail dedicato.
- **Hardening backend**: JWT SimpleJWT (**ACCESS_TOKEN_LIFETIME=30min**, **REFRESH_TOKEN_LIFETIME=7gg** con rotazione e blacklist), rate limiting DRF (**AnonRateThrottle 20/h**, **UserRateThrottle 500/h**), header sicurezza e `CONN_MAX_AGE` per pooling DB.
- **UX moduli operativi**: help contestuale via componente `ModuleHelp` sulle principali pagine React (asset, BIA, risk, incidenti, controlli, audit prep, management review, scadenzario).
- **Audit trail & job async**: catena hash serializzata (`select_for_update`) e task Celery critici con `autoretry` e backoff esponenziale.
- **Performance DB**: indici aggiuntivi su campi di filtro frequenti per incidenti, task, controlli, rischi, documenti ed evidenze.

---

## Contribuire

- Branch da `develop`: `git checkout -b feature/M{nn}-descrizione-breve`
- Coverage minimo 80% per ogni nuovo modulo (target globale >= 70%)
- Pull Request verso `develop` con 2 reviewer obbligatori
- Merge su `main` solo via PR approvata + CI verde
- Seguire le regole architetturali in [CLAUDE.md](./CLAUDE.md) — mai derogare

Convenzioni di codice, struttura modelli e API in [MANUAL_TECNICO_it.md](./manual/MANUAL_TECNICO_it.md#convenzioni-di-sviluppo).
