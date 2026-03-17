# GRC Compliance Webapp

> Piattaforma GRC (Governance, Risk & Compliance) per aziende manifatturiere con certificazioni TISAX L2/L3, NIS2 e ISO 27001:2022.

---

## Indice

- [Panoramica](#panoramica)
- [Moduli](#moduli)
- [Quick start](#quick-start)
- [Struttura repository](#struttura-repository)
- [Framework normativi](#framework-normativi)
- [Integrazioni](#integrazioni)
- [Multilingua](#multilingua)
- [AI Engine M20](#ai-engine-m20)
- [Documentazione](#documentazione)
- [Contribuire](#contribuire)

---

## Panoramica

La webapp GRC consolida in un'unica piattaforma la gestione di tutti i framework di sicurezza applicabili a un'organizzazione manifatturiera multi-plant, eliminando fogli Excel distribuiti, evidenze disperse e processi manuali non tracciati.

**Caratteristiche principali:**

- 21 moduli funzionali dall'onboarding all'audit preparation (M00–M20)
- Struttura multi-plant con Business Unit, sub-plant e profilo NIS2 per plant
- Risk assessment IT/OT con heat map 5×5 e traduzione automatica in ALE (€)
- Workflow documentale ISO 27001 cl.7.5 con approvazione a 3 livelli e versioning SHA-256
- Gestione incidenti NIS2 con timer countdown 24h/72h/30gg e template ACN precompilato
- PDCA controller con trigger automatici e storico maturità per auditor
- Integrazione KnowBe4 bidirezionale per cybersecurity awareness
- AI Engine opzionale (M20) con human-in-the-loop e sanitization layer GDPR-safe
- Interfaccia multilingua IT · EN · FR · PL · TR

---

## Moduli

| # | Modulo | Fase | Framework principali |
|---|--------|------|----------------------|
| M00 | Governance & Organigramma | Fase 0 | TISAX L3 · ISO 27001 cl.5 · NIS2 |
| M01 | Plant Registry | Fase 0 | Tutti |
| M02 | Ruoli & RBAC | Fase 0 | Tutti |
| M03 | Libreria Controlli | Fase 0 | VDA ISA 6.0 · NIS2 · ISO 27001 |
| M04 | Asset Inventory IT/OT | Fase 1 | TISAX · IEC 62443 |
| M05 | BIA & ROI | Fase 1 | ISO 27001 · NIS2 |
| M06 | Risk Assessment IT/OT | Fase 1 | IEC 62443 · NIST 800-82 |
| M07 | Documenti & Evidenze | Fase 2 | ISO 27001 cl.7.5 |
| M08 | Scadenzario & Task | Fase 2 | Tutti |
| M09 | Gestione Incidenti | Fase 2 | NIS2 Art.23 · ISO 27001 A.16 |
| M10 | Audit Trail | Fase 2 | TISAX L3 · ISO 27001 |
| M11 | PDCA Controller | Fase 3 | ISO 27001 cl.10 |
| M12 | Lesson Learning & KB | Fase 3 | ISO 27001 A.5.27 |
| M13 | Revisione di Direzione | Fase 3 | ISO 27001 cl.9.3 |
| M14 | Supplier Management | Fase 4 | VDA ISA 5.x · NIS2 supply chain |
| M15 | Formazione & Awareness | Fase 4 | TISAX A.7 · KnowBe4 |
| M16 | Business Continuity | Fase 4 | ISO 27001 A.17 |
| M17 | Audit Preparation | Fase 4 | TISAX · ISO 27001 · NIS2 |
| M18 | Reporting & Dashboard | Cross-cutting | Tutti |
| M19 | Notifiche & Integrazioni | Cross-cutting | Tutti |
| M20 | AI Engine *(opzionale)* | Cross-cutting | ISO 27001 · TISAX · NIS2 |

---

## Quick start

### Prerequisiti

- Docker Desktop >= 4.x
- Node.js >= 20 LTS
- Python >= 3.11

```bash
# 1. Clona il repository
git clone https://github.com/org/grc-webapp.git
cd grc-webapp

# 2. Variabili d'ambiente
cp .env.example .env
# Modifica .env con le tue credenziali

# 3. Avvia lo stack
docker compose up -d

# 4. Migrazioni e dati iniziali
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py load_frameworks
docker compose exec backend python manage.py createsuperuser

# 5. Apri l'app
open http://localhost:3001
```

Per la configurazione completa in produzione vedere [INFRASTRUCTURE.md](./INFRASTRUCTURE.md).

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
│   │   └── ai_engine/          # M20 — opzionale
│   ├── core/                   # Settings, middleware, modelli base
│   ├── frameworks/             # JSON framework normativi
│   └── requirements/
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── modules/            # Un folder per modulo
│   │   ├── i18n/               # Traduzioni IT EN FR PL TR
│   │   └── components/         # Componenti condivisi
├── infra/                      # IaC — Terraform / Ansible / Docker
├── CLAUDE.md
├── MANUAL_UTENTE.md
├── MANUAL_TECNICO.md
├── INFRASTRUCTURE.md
├── .cursorrules
├── scripts/
│   ├── load_frameworks.py
│   ├── seed_demo.py
│   └── backup.sh
├── tests/                      # unit / integration / e2e
├── .env.example
├── docker-compose.yml
├── docker-compose.prod.yml
└── Makefile
```

---

## Framework normativi

| Framework | Versione | Controlli | Stato |
|-----------|----------|-----------|-------|
| VDA ISA (TISAX) | 6.0 | 83 | Incluso |
| NIS2 Art. 21 | 2022/2555 | ~20 misure | Incluso |
| ISO 27001 Annex A | 2022 | 93 | Incluso |
| IEC 62443 (semplificato) | 3-3 | Score OT in M06 | Incluso |
| DORA / NIST CSF 2.0 | — | — | Aggiungibile via JSON |

I framework sono dati, non codice: aggiungere un nuovo standard non richiede deploy. Vedere `backend/frameworks/` e la sezione [Aggiungere un framework](./MANUAL_TECNICO.md#aggiungere-un-framework) nel manuale tecnico.

---

## Integrazioni

| Sistema | Modulo | Tipo | Note |
|---------|--------|------|------|
| KnowBe4 | M15 | API REST bidirezionale | Provisioning utenti + import completamenti + phishing |
| Azure OpenAI / Anthropic | M20 | API REST — opt-in | Solo prompt sanitizzati, nessun PII |
| Ollama / vLLM | M20 | HTTP locale | Modello on-prem per classificazioni |
| SMTP aziendale | M19 | SMTP | Notifiche e digest email |
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

## Documentazione

| File | Contenuto |
|------|-----------|
| [README.md](./README.md) | Questo file — panoramica e quick start |
| [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) | Stack tecnologico, deployment, DB, backup, sicurezza, monitoraggio |
| [MANUAL_UTENTE.md](./MANUAL_UTENTE.md) | Guida per Compliance Officer, Risk Manager, Plant Manager, Auditor |
| [MANUAL_TECNICO.md](./MANUAL_TECNICO.md) | API, modelli dati, framework, AI Engine, test, convenzioni |

### Stato implementazione ultime feature

- **Hardening backend**: JWT SimpleJWT configurato (**ACCESS_TOKEN_LIFETIME=30min**, **REFRESH_TOKEN_LIFETIME=7gg** con rotazione e blacklist), rate limiting DRF di base (**AnonRateThrottle 20/h**, **UserRateThrottle 500/h**), header di sicurezza e `CONN_MAX_AGE` per pooling DB in `core.settings.base/prod`.
- **UX moduli operativi**: help contestuale via componente `ModuleHelp` sulle principali pagine React (asset, BIA, risk, incidenti, controlli, audit prep, management review, scadenzario).
- **Audit trail & job async**: catena hash dell’audit trail serializzata (`select_for_update`) e task Celery critici con `autoretry` e backoff.
- **Performance DB**: indici aggiuntivi su campi di filtro frequenti per incidenti, task, controlli, rischi, documenti ed evidenze.

---

## Contribuire

- Branch da `develop`: `git checkout -b feature/M{nn}-descrizione-breve`
- Coverage minimo 80% per ogni nuovo modulo
- Pull Request verso `develop` con 2 reviewer obbligatori
- Merge su `main` solo via PR approvata + CI verde

Convenzioni di codice, struttura modelli e API in [MANUAL_TECNICO.md](./MANUAL_TECNICO.md#convenzioni-di-sviluppo).
