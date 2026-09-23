# <img src="./docs/govrico-logo.svg" width="34" align="middle" alt="govrico logo" /> govrico — Governance, Risk and Compliance Platform

> govrico (Governance, Risk & Compliance) per aziende manifatturiere con certificazioni TISAX L2/L3, NIS2 e ISO 27001:2022.

![Version](https://img.shields.io/badge/version-0.9.0-informational) ![License](https://img.shields.io/badge/license-AGPL--3.0-blue) ![Python](https://img.shields.io/badge/Python-3.11-blue) ![Django](https://img.shields.io/badge/Django-5.2-green) ![React](https://img.shields.io/badge/React-18-blue) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-blue)

---

## Governance del progetto

Le modifiche al codice seguono un processo tracciato: branch dedicati, Pull Request con revisione obbligatoria, release taggate e documentate in [CHANGELOG.md](./CHANGELOG.md). Vedere [CONTRIBUTING.md](./CONTRIBUTING.md) per il processo completo e [SECURITY.md](./SECURITY.md) per la politica di divulgazione delle vulnerabilità.

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

- 22 moduli funzionali dall'onboarding all'audit preparation (M00-M21) più il modulo trasversale OSINT Monitor, multilingua IT/EN/FR/PL/TR
- Struttura multi-plant con Business Unit, sub-plant e profilo NIS2 per plant
- Risk assessment IT/OT con heat map 5x5 e traduzione automatica in ALE (€)
- Workflow documentale ISO 27001 cl.7.5: policy di approvazione per tipo di documento (anche per delibera dell'organo di governo), separazione dei compiti, versione in vigore tracciata, versioning SHA-256
- Riesame di direzione ISO 27001 cl.9.3 con dati congelati, ordine del giorno, approvazione dell'organo e verbale PDF/HTML multilingua
- Gestione incidenti NIS2 con timer countdown 24h/72h/30gg e template ACN precompilato
- PDCA controller con trigger automatici e storico maturità per auditor
- Formazione e awareness basate sulle evidenze: piano, erogazioni con file di prova collegate ai controlli, copertura del personale per conteggi (nessuna integrazione e-learning)
- AI Engine opzionale (M20) con human-in-the-loop e sanitization layer GDPR-safe
- Interfaccia multilingua IT · EN · FR · PL · TR

---

## Moduli implementati

| Codice | Modulo | Funzionalità principali | Stato |
|--------|--------|-------------------------|-------|
| M00 | Governance & Organigramma | Ruoli normativi (CISO/DPO/Plant Manager…) con scadenze, organi di governo con componenti, obiettivi di sicurezza ISO 27001 §6.2, policy di workflow documentale | Implementato |
| M01 | Plant Registry | Anagrafica plant, Business Unit, profilo NIS2, sub-plant | Implementato |
| M02 | Ruoli & RBAC | Accessi per ruolo e perimetro (organizzazione, BU, uno o più siti), pannello unico accessi e responsabilità, MFA, token auditor esterno, competenze | Implementato |
| M03 | Libreria Controlli | Catalogo controlli da JSON normativi, gap analysis, stato per plant | Implementato |
| M04 | Asset Inventory IT/OT | Inventario asset con criticità 1-5, badge tooltip, change management | Implementato |
| M05 | BIA & ROI | Business Impact Analysis, calcolo RTO/RPO, traduzione ALE | Implementato |
| M06 | Risk Assessment IT/OT | Heat map 5x5, score IEC 62443, scenari OT, trattamento rischi | Implementato |
| M07 | Documenti & Evidenze | Versioning SHA-256 con revisione da frontespizio, workflow di approvazione per tipo (anche per delibera), separazione dei compiti, scadenza evidenze, MIME check | Implementato |
| M08 | Scadenzario & Task | Assegnazione per ruolo, notifiche scadenza, compliance_schedule cross-modulo | Implementato |
| M09 | Gestione Incidenti | Timer NIS2 24h/72h/30gg, template ACN, escalation automatica, countdown real-time | Implementato |
| M10 | Audit Trail | Hash chain SHA-256 append-only e immutabile (trigger PostgreSQL), email pseudonimizzata, verify_audit_trail_integrity | Implementato |
| M11 | PDCA Controller | Ciclo Plan-Do-Check-Act, trigger automatici, storico maturità, notifica PDCA bloccati | Implementato |
| M12 | Lesson Learning & KB | Knowledge base con ricerca, validazione, propagazione ai siti, collegamento a PDCA | Implementato |
| M13 | Revisione di Direzione | Snapshot dati ISO 9.3, ordine del giorno, convocati e presenze, documenti da approvare, bozze IA con accettazione umana, approvazione dell'organo, verbale PDF/HTML | Implementato |
| M14 | Supplier Management | Anagrafica fornitori, valutazione VDA ISA 5.x, supply chain NIS2 | Implementato |
| M15 | Formazione & Awareness | Piano formativo, erogazioni con prova (evidenze sui controlli), gruppi destinatari, copertura, phishing aggregato | Implementato |
| M16 | Business Continuity | Piani BCP, test DR, scadenza piani, collegamento a BIA M05 | Implementato |
| M17 | Audit Preparation | Preparazione audit TISAX/ISO/NIS2, finding, evidence pack, annulla con soft delete | Implementato |
| M18 | Reporting & Dashboard | KPI snapshot settimanale con connettori interni, matrice accessi & responsabilità (ISO A.5.18), export report, dashboard cross-modulo | Implementato |
| M19 | Notifiche | Notifiche email per evento con regole e profili per ruolo, iscrizioni personali, configurazione SMTP cifrata | Implementato |
| M20 | AI Engine *(opzionale)* | Classificazione incidenti, bozze RCA, azioni per i gap, spiegazioni dei controlli, bozze del riesame, assistente — sanitizzazione GDPR e human-in-the-loop | Implementato |
| M21 | Centro Operativo | Posture score, advisor automatici, problemi/configurazioni mancanti e azioni consigliate in vista prioritizzata, widget dashboard | Implementato |
| — | OSINT Monitor *(trasversale)* | Monitoraggio superficie di attacco e reputazione domini, enricher CTI, scoring esposizione, alert e semaforo salute chiavi | Implementato |

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
# Solo alla prima installazione: policy di workflow documentale predefinite
# (aggiorna quelle di organizzazione già presenti — usare --dry-run per vedere cosa cambia)
docker compose -f docker-compose.prod.yml exec backend python manage.py load_document_workflow_policies

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
SMTP aziendale · Sentry (opzionale) · enricher CTI dell'OSINT Monitor
AI Engine M20: Ollama (locale) + Anthropic/OpenAI/Google/Mistral/Groq (cloud, testo sanitizzato)
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
│   │   ├── ai_engine/          # M20 — opzionale
│   │   ├── cockpit/            # M21 — Centro Operativo
│   │   ├── osint/              # OSINT Monitor — trasversale
│   │   ├── backups/            # Backup DB (API + task)
│   │   └── compliance_schedule/  # M08 — scadenze cross-modulo
│   ├── core/                   # Settings, middleware, modelli base, audit
│   ├── frameworks/             # JSON framework normativi (ISO27001, NIS2, TISAX L2/L3)
│   ├── tests/                  # pytest — integrazione audit trail, ecc.
│   └── requirements/
├── frontend/                   # React SPA
│   └── src/
│       ├── modules/            # Pagine per modulo (M00–M21, OSINT) e impostazioni
│       ├── api/endpoints/      # Client API (~24 file TS)
│       ├── i18n/               # Traduzioni IT / EN / FR / PL / TR
│       └── components/         # Shell, Sidebar, UI condivise
├── manual/                     # Manuali utente e tecnici (multi-lingua)
│   ├── MANUAL_UTENTE_{it,en,fr,pl,tr}.md
│   └── MANUAL_TECNICO_{it,en,fr,pl,tr}.md
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
- NIS2 (UE 2022/2555) — 25 misure Art. 21
- ACN NIS2 (D.Lgs. 138/2024, attuazione italiana secondo NIST CSF 2.0) — 43 misure
- TISAX VDA ISA 6.0 — L2 High Protection (45 controlli), L3 Very High (12 estensioni "-VH" sopra L2), Prototype Protection (22)
- IEC 62443 (semplificato) — score OT in M06

I framework sono dati, non codice: aggiungere un nuovo standard (DORA, NIST CSF 2.0, ecc.) non richiede deploy. Vedere `backend/frameworks/` e la sezione [Aggiungere un framework normativo](./manual/MANUAL_TECNICO_it.md#aggiungere-un-framework-normativo) nel manuale tecnico (IT; altre lingue in `manual/`).

| Framework | Versione | Controlli | Stato |
|-----------|----------|-----------|-------|
| ISO 27001 Annex A | 2022 | 93 | Incluso |
| NIS2 Art. 21 | 2022/2555 | 25 | Incluso |
| ACN NIS2 | D.Lgs. 138/2024 | 43 | Incluso |
| VDA ISA (TISAX) L2 / L3 / Prototype | 6.0 | 45 / +12 VH / 22 | Incluso |
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
- MFA (TOTP) con dispositivi fidati
- Rate limiting: login 5/min, utenti autenticati 2000/h, anonimi 20/h, chiamate IA ed export limitate a parte
- MIME check upload file con python-magic (whitelist estensioni + tipo reale)
- Fernet AES-256 per credenziali SMTP in database (FERNET_KEY)
- Password minimo 12 caratteri + validatori Django (CommonPassword, NumericPassword, UserAttributeSimilarity)
- Audit trail append-only con hash chain SHA-256 — trigger PostgreSQL impedisce UPDATE/DELETE
- Docker produzione con utente non-root + Gunicorn
- Header HTTP sicurezza: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- GDPR: `anonymize_user()` in `auth_grc/services.py`; audit log immutabile e pseudonimizzato (nessuna cancellazione per retention); log interazioni IA conservati 365 giorni; export dei dati (`export_portable_data`)
- Output HTML degli export con escape dei testi utente; errori imprevisti senza dettagli interni verso il client
- Supply chain: `pip-audit` e `npm audit` ogni notte, GitHub CodeQL, Dependabot, secret scanning con push protection, SBOM CycloneDX a ogni release

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

Per l'elenco completo di tutte le variabili (storage, email, SSO, AI Engine) vedere [INFRASTRUCTURE.md](./INFRASTRUCTURE.md#variabili-dambiente-obbligatorie).

---

## Comandi Makefile

| Target | Descrizione |
|--------|-------------|
| `make dev` | Avvia stack sviluppo (db, redis, minio, mailhog + backend + frontend) |
| `make migrate` | Esegui migrazioni Django |
| `make test` | Esegui test suite (pytest backend + npm test frontend) |
| `make lint` | Linting backend con ruff (check + format) |
| `make load-fw` | Importa framework normativi JSON (ISO27001, NIS2, TISAX) |
| `make load-competencies` | Importa requisiti di competenza (M02) |
| `make seed` | Carica dati demo con seed_demo |
| `make shell` | Shell Django interattiva (shell_plus) |
| `make prod-build` | Build immagini Docker produzione |
| `make prod-up` | Avvia stack produzione in background |
| `make prod-down` | Ferma e rimuove stack produzione |
| `make prod-migrate` | Esegui migrazioni Django in produzione |
| `make prod-seed` | Carica dati iniziali in produzione (framework, profili notifica, competenze, requisiti di ruolo, documenti richiesti, controlli provati dalla formazione) — idempotente, non sovrascrive le personalizzazioni |
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
| Anthropic / OpenAI / Google / Mistral / Groq | M20 | API REST — opt-in | Prompt sanitizzati (Sanitizer), routing per funzione |
| Ollama | M20 | HTTP locale | Modello on-prem, nessun trasferimento extra-UE |
| SMTP aziendale | M19 | SMTP | Notifiche email, credenziali cifrate Fernet |
| VirusTotal, HIBP, AbuseIPDB, OTX, Google Safe Browsing, abuse.ch, crt.sh, RDAP | OSINT | API REST — opt-in per chiave | Enricher CTI con difesa SSRF |
| Sentry | trasversale | SDK — opzionale | Error monitoring GDPR-safe, attivo se `SENTRY_DSN` impostato |
| ACN (NIS2) | M09 | Documento generato | Notifica precompilata da inviare tramite il portale ACN |

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

| Funzione | Esecuzione predefinita | Moduli coinvolti |
|----------|-----------|-----------------|
| Classificazione degli incidenti | Locale (Ollama) | M09 |
| Bozza RCA, azioni per i gap | Cloud (sanitizzato) | M09, M03 |
| Spiegazione dei controlli, procedura .docx per un controllo | Cloud (solo testo normativo) | M03 |
| Sintesi del riesame e bozze dei punti all'ordine del giorno | Cloud (sanitizzato + nomi pseudonimizzati) | M13 |
| Suggerimento codici CPV dei fornitori | Cloud (sanitizzato) | M14 |
| Assistente govrico, spiegazione insight, copilota del Centro Operativo | Cloud (sanitizzato) | M20, M21 |
| Analisi della superficie d'attacco | Cloud (anonimizzato) | OSINT |

Il routing locale/cloud si configura per funzione. Garanzie: sanitizzazione prima di ogni invio al cloud, human-in-the-loop su ogni output (nessun output applicato in automatico), contenuti generati dichiarati come tali (AI Act art. 50), `AiInteractionLog` con hash dell'input (mai il testo) e conservazione 365 giorni.

---

## Backup

Il modulo **Backup** (Impostazioni → Backup) crea archivi completi **database + file caricati** (`.tar`), con backup automatico ogni notte alle 02:00 (`python manage.py schedule_backup_task`), conservazione di 30 giorni, download, import e ripristino guidato dall'interfaccia.

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

### Novità dell'ultima release

Le modifiche di ogni versione, con le note di aggiornamento per chi fa il deploy, sono nel [CHANGELOG](./CHANGELOG.md). La 0.9.0 introduce la formazione basata sulle evidenze (M15), l'approvazione controllata dei documenti con versione in vigore e delibera dell'organo (M07/M13) e un giro di correzioni di sicurezza.

---

## Contribuire

- Branch da `main`: `feature/M{nn}-descrizione-breve`, `fix/…`, `security/…`
- Conventional Commits (`feat`, `fix`, `security`, `docs`, …) e voce nel CHANGELOG per ogni `feat`/`fix`/`security`
- Coverage globale ≥ 70% (≥ 80% sui nuovi moduli); ogni chiave i18n tradotta in tutte e 5 le lingue
- Pull Request verso `main` con 1 reviewer e CI verde — dettagli in [CONTRIBUTING.md](./CONTRIBUTING.md)
- Seguire le regole architetturali e le convenzioni di codice documentate nel [manuale tecnico](./manual/MANUAL_TECNICO_it.md#convenzioni-di-sviluppo) — mai derogare

Convenzioni di codice, struttura modelli e API in [MANUAL_TECNICO_it.md](./manual/MANUAL_TECNICO_it.md#convenzioni-di-sviluppo).

---

## Riconoscimenti

Il modello decisionale NIS2 per la classificazione degli incidenti (M09 — motore PTA/PTNR e fattispecie ACN) è stato sviluppato con riferimento al progetto open source:

> **NIS2 Incident Management and Reporting** — [CISOs4AI](https://github.com/CISOs4AI/NIS2-Incident-Management-and-Reporting)

---

## Licensing

govrico is released under the [GNU Affero General Public License v3.0](./LICENSE) (AGPL-3.0).

This means:
- ✅ Free to use, modify and self-host
- ✅ Contributions welcome under the same license
- ⚠️ If you run a modified version as a network service, you must release your source code under AGPL-3.0
- ❌ If you want to use govrico in a commercial product or service without open-sourcing your code, you need a commercial license

### Commercial License

For businesses that need to integrate govrico without the AGPL obligations — white-label deployments, commercial SaaS, or enterprise on-premise without source disclosure — a commercial license is available.

Contact: [linkedin.com/in/fpino87](https://www.linkedin.com/in/fpino87/) or write me: info@govrico.com
