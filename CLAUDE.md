# GRC Compliance Webapp — Contesto per Claude Agent

## Progetto
Webapp GRC per azienda manifatturiera automotive.
Compliance: TISAX L2/L3, NIS2, ISO 27001.
21 moduli M00-M20. Multilingua: IT (default) / EN / FR / PL / TR.

## Stack
- **Backend**: Python 3.11, Django 5.1, DRF, Celery 5, PostgreSQL 15, Redis 7
- **Frontend**: React 18, TypeScript, Vite 5, Tailwind CSS, i18next, Zustand, TanStack Query, React Router v6
- **Infra**: Docker Compose, Nginx Proxy Manager
- **Test**: pytest, factory-boy, coverage ≥ 70%

## Stato attuale (aggiornato)
- Backend Django: **UP** porta 8001
- Frontend React/Vite: **UP** porta 3001
- PostgreSQL: **UP** porta 5433
- Redis: **UP**
- Migrazioni GRC apps: **applicate** (inclusa token_blacklist)
- Superuser: `admin@azienda.it`
- Celery worker/beat: **configurati e avviati**
- Framework normativi JSON: **presenti** in `backend/frameworks/` (ISO27001, NIS2, TISAX_L2, TISAX_L3)
- Docker produzione: **Dockerfile.prod** + **docker-compose.prod.yml** pronti
- ⚠️ Traduzione UI: solo IT/EN — FR/PL/TR in sviluppo

## Regole architetturali — NON derogare mai

1. Tutti i model ereditano da `core.models.BaseModel` (UUID pk, soft delete, timestamps, created_by)
2. Business logic SOLO in `services.py` — mai nelle view o nei serializer
3. Ogni azione rilevante chiama `core.audit.log_action(action_code, level, entity, payload)`
4. `AuditLog` è append-only — trigger PostgreSQL impedisce UPDATE/DELETE
5. Soft delete sempre (`soft_delete()`) — mai `queryset.delete()` diretto
6. Nessuna query N+1 — `select_related` / `prefetch_related` obbligatori
7. Task assegnati a ruolo (risoluzione dinamica via `UserPlantAccess`), mai a utente diretto
8. Framework normativi = JSON in `backend/frameworks/` — non hardcodare controlli nel codice
9. M20 AI Engine: nessun PII inviato al cloud senza `Sanitizer.sanitize()`, human-in-the-loop sempre prima di applicare output AI
10. Soft delete manager è il default — usare `.all_with_deleted()` solo dove esplicitamente necessario
11. Mai loggare dati personali (email, CF, telefono) nei log di sistema — loggare solo conteggi o identificatori anonimi
12. File upload: sempre `validate_uploaded_file()` con MIME check (python-magic)
13. Produzione: usare `docker-compose.prod.yml` e `Dockerfile.prod`
14. **Traduzioni obbligatorie**: ogni nuova chiave i18n aggiunta in `it/common.json` o `en/common.json` DEVE essere tradotta contestualmente in **tutte e 5 le lingue** — IT, EN, FR, PL, TR — nei rispettivi file `frontend/src/i18n/<lang>/common.json`. Non lasciare mai chiavi parzialmente tradotte.

## Sicurezza (configurazione attuale)
- **JWT**: ACCESS=30min, REFRESH=7gg, ROTATE=True, BLACKLIST=True (token_blacklist app attiva)
- **Rate limiting**: anon=20/h, user=500/h, login=5/min (LoginRateThrottle su GrcTokenObtainPairView)
- **File upload**: whitelist estensioni + MIME type reale (python-magic)
- **Password**: min 12 caratteri + CommonPassword + NumericPassword + UserAttributeSimilarity
- **FERNET**: cifratura AES-256 per credenziali SMTP (FERNET_KEY in env)
- **GDPR**: `anonymize_user()` disponibile in `auth_grc/services.py`, retention automatica audit log mensile
- **Health check**: `GET /api/health/` — status DB incluso

## Struttura backend/apps/ — moduli implementati

| App | Modulo | Stato |
|-----|--------|-------|
| `governance` | M00 Governance & Ruoli | models + services + serializers + views + urls + tests |
| `plants` | M01 Plant Registry | models + services + serializers + views + urls |
| `auth_grc` | M02 RBAC | models + services + views + urls + tests |
| `controls` | M03 Libreria Controlli | models + services + load_frameworks cmd + tests |
| `assets` | M04 Asset IT/OT | models + serializers + views + urls |
| `bia` | M05 BIA | models + services + serializers + views |
| `risk` | M06 Risk Assessment | models + services + serializers + views |
| `documents` | M07 Documenti | models + services + serializers + views |
| `tasks` | M08 Task Management | models + serializers + views |
| `incidents` | M09 Incidenti NIS2 | models + serializers + views |
| `audit_trail` | M10 Audit Trail | views + verify_audit_trail_integrity cmd |
| `pdca` | M11 PDCA | models + services + serializers + views |
| `lessons` | M12 Lesson Learned | models + serializers + views |
| `management_review` | M13 Revisione Direzione | models + serializers + views |
| `suppliers` | M14 Fornitori | models + serializers + views |
| `training` | M15 Training/KnowBe4 | models + serializers + views |
| `bcp` | M16 BCP | models + services + serializers + views |
| `audit_prep` | M17 Audit Readiness | models + services + serializers + views |
| `reporting` | M18 Reporting | views (no model) |
| `notifications` | M19 Notifiche | models + serializers + views |
| `ai_engine` | M20 AI Engine | models + sanitizer |

## Struttura frontend/src/

```
src/
├── App.tsx                    # Router completo — tutte le 20 route definite
├── main.tsx                   # Entry point con QueryClientProvider + i18n
├── store/auth.ts              # Zustand: user, token, selectedPlant
├── api/
│   ├── client.ts              # axios con JWT interceptor + refresh
│   └── endpoints/             # un file per ogni modulo (20 file)
├── components/
│   ├── layout/Shell.tsx       # Layout principale con sidebar
│   ├── layout/Sidebar.tsx
│   ├── layout/Topbar.tsx
│   └── ui/
│       ├── AiSuggestion.tsx   # Banner IA con Accept/Edit/Ignore
│       ├── CountdownTimer.tsx # Countdown NIS2 real-time
│       └── StatusBadge.tsx    # Badge colorato per stati compliance
├── modules/                   # Una cartella per modulo
│   ├── dashboard/Dashboard.tsx
│   ├── controls/ControlsList.tsx
│   ├── incidents/IncidentsList.tsx
│   └── ... (20 moduli totali)
├── pages/LoginPage.tsx
└── i18n/
    ├── index.ts
    ├── it/common.json
    └── en/common.json
```

## Comandi Docker utili

```bash
# Stato container
docker compose ps

# Logs
docker compose logs backend --tail=30
docker compose logs frontend --tail=30

# Esegui comandi Django
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py load_frameworks
docker compose exec backend python manage.py verify_audit_trail_integrity
docker compose exec backend python manage.py createsuperuser

# Rebuild dopo modifiche
docker compose up -d --build backend
docker compose up -d --build frontend

# Celery (già configurato e avviato)
docker compose up -d celery celery-beat

# Produzione — usa docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py load_frameworks
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py load_notification_profiles
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py load_competency_requirements
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

## Porte in uso su questo server

| Servizio | Porta host | Porta container |
|----------|-----------|----------------|
| Backend Django | 8001 | 8000 |
| Frontend Vite | 3001 | 3000 |
| PostgreSQL GRC | 5433 | 5432 |
| Redis GRC | interno | 6379 |
| MinIO console | 9001 | 9001 |
| Mailhog SMTP | 1026 | 1025 |
| Mailhog UI | 8026 | 8025 |

**Altri container sul server (non toccare):**
- `ai-docintel-*` — progetto separato
- `npm` — Nginx Proxy Manager su 80/443
- `budget-db`, `sitebudget`, `siteciso`, `sitebb`

## Prossime attività prioritarie

- **DA FARE**: Traduzioni FR/PL/TR
- **DA FARE**: Test suite (coverage target ≥ 70%) — `docker compose exec backend pytest`
- **DA FARE**: Sentry integration per error monitoring
- **DA FARE**: Backup automatico PostgreSQL (cron + pg_dump, retention 30gg)

---

## Aggiornamenti recenti (hardening & UX)

- **M17 Audit Preparation**: eliminazione sicura con soft delete e azione di annullamento (`annulla`) che archivia il prep solo se tutti i finding sono chiusi, con audit trail dedicato.
- **Frontend moduli**: introdotto `ModuleHelp` (pulsante `?` con drawer contestuale) sui principali moduli operativi (asset, BIA, risk, incidenti, controlli, audit prep, management review, scadenzario).
- **M04 Asset**: badge di criticità con tooltip esplicativi e tabella guida all’interno del form, per scelta coerente dei livelli 1–5.
- **Security hardening**: JWT 30min/7gg con blacklist, throttle login 5/min, MIME check upload (python-magic), password validators 12+ char, FERNET_KEY per credenziali SMTP, GDPR anonymize_user(), retention audit log automatica.
- **Robustezza async**: task Celery critici (controlli ed asset) ora con `autoretry` esponenziale; catena hash dell’audit trail serializzata con `select_for_update` per prevenire race condition.
- **Performance DB**: indici aggiuntivi su campi `status`, `due_date`, `score`, `valid_until` e campi di filtro più usati per `ControlInstance`, `RiskAssessment`, `Task`, `Incident`, `Document` ed `Evidence`.

## File di riferimento

- `AGENTS.md` — build plan completo con tutto il codice
- `GRC_Specifica_Funzionale_v1.0.docx` — specifiche funzionali M00-M20
- `MANUAL_TECNICO.md` — pattern architetturali dettagliati
- `INFRASTRUCTURE.md` — infrastruttura e deployment
- `backend/frameworks/*.json` — controlli normativi (ISO27001, NIS2, TISAX L2/L3)
