# GRC Webapp — Roadmap di hardening (newfix)

> Tracker di lavoro post-OSINT. Stato: `[ ]` aperto / `[x]` chiuso / `[~]` in corso / `[!]` bloccato.
> Prima sessione: 2026-04-26.
> Branch: main.
> Origine: revisione critica end-to-end del progetto a OSINT chiuso.

---

## PROMPT DI RIPRESA SESSIONE

> **Quando la sessione si interrompe, l'utente scriverà "leggi newfix e continua".**
>
> **Cosa fare al riavvio:**
> 1. Leggi questo file integralmente con `Read /home/claw/grc-webapp/newfix.md`.
> 2. Identifica la prima voce con stato `[~]` (in corso): finiscila per prima cosa.
> 3. Se non c'è nessun `[~]`, prendi la prima voce `[ ]` in ordine di priorità (P0 sicurezza → P0 affidabilità → P1 sicurezza → P1 funzionali → P1 UX → P2 hardening → P2 GRC → P2 UX extra).
> 4. Marca la voce come `[~]` (Edit), poi implementa il fix, poi marca `[x]` e aggiungi una riga al **REGISTRO LAVORO** in fondo con data + cosa è stato fatto.
> 5. Esegui i test rilevanti (`docker compose exec -T backend pytest apps/<app>/ -q` e/o `docker compose exec -T frontend npx tsc --noEmit`) prima di chiudere la voce.
> 6. **Convenzioni commit**: `security(scope):` per S*, `fix(scope):` per R*/F*/G*, `feat(scope):` per U*/X*, `chore(ops):` per H*. Aggiungere riga in `CHANGELOG.md` sotto `[Unreleased]` per ogni S/R/F/G chiuso.
> 7. **Non fare release autonome** (no bump VERSION, no tag). Solo commit + CHANGELOG `[Unreleased]`.
> 8. Se serve un cambio architetturale invasivo (es. migrazioni distruttive, breaking change API), **fermati e chiedi conferma** all'utente prima di applicare.
> 9. Vincoli operativi del progetto sono in `CLAUDE.md` (non derogare alle 14 regole architetturali).
> 10. Quando tutte le voci sono `[x]`, comunica "newfix completato" e proponi un giro di micro-issue (vedi nota in fondo al registro 2026-04-26).
>
> **File complementari**: `fix.md` (storico OSINT, chiuso), `CLAUDE.md` (regole), `CHANGELOG.md` (sotto `[Unreleased]`).

---

---

## Premessa

`fix.md` è il tracker storico OSINT (chiuso). Questo documento gestisce le **issue cross-cutting** trovate nella revisione del progetto. Nessuna delle voci sotto è stata affrontata da `fix.md`. Le priorità sono state assegnate con criterio **"breaks-the-product-or-the-audit"**, non solo "comodità".

---

## P0 — SICUREZZA / COMPLIANCE BLOCCANTI

### S1 — Multi-tenancy / RBAC scoping completamente assente sul data layer
**Stato**: `[x]` (2026-04-27)
**Severity**: critica.
**Files**: 14 ViewSet senza `get_queryset` di filtro per ruolo/plant: `apps/auth_grc/views.py`, `apps/audit_trail/views.py`, `apps/ai_engine/views.py`, `apps/bcp/views.py`, `apps/backups/views.py`, `apps/incidents/views.py`, `apps/governance/views.py`, `apps/lessons/views.py`, `apps/training/views.py`, `apps/audit_prep/views.py`, `apps/pdca/views.py`, `apps/management_review/views.py`, `apps/reporting/views.py`, `apps/suppliers/views.py`.
**Problema**: gli unici due moduli che filtrano per `UserPlantAccess` sono `tasks/views.py` e `bcp/views.py` (parzialmente). Tutti gli altri restituiscono `Model.objects.all()` filtrato solo dal `?plant=<id>` opzionale che il client può **omettere**. Conseguenza: un Plant Manager dello stabilimento A può listare incidenti, rischi, controlli, fornitori e revisioni di tutti gli stabilimenti.
**Fix**: introdurre `core/scoping.py::PlantScopedQuerysetMixin` che, dato `request.user`, calcola gli ID plant accessibili (org → tutti; bu → plants della BU; plant_list/single_plant → quelli espliciti) e lo applica a tutti i ViewSet. Test obbligatorio: utente plant_manager su Plant A non vede dati di Plant B.

### S2 — Hash chain dell'audit trail forgiabile
**Stato**: `[x]` (2026-04-26)
**Severity**: critica per uso compliance.
**File**: `backend/core/audit.py:46-48` (`_compute_hash`).
**Problema**: l'hash viene calcolato su `payload + prev_hash`. Mancano `user_id`, `action_code`, `entity_type`, `entity_id`, `level`, `timestamp_utc`. Un attaccante con write sul DB (o un DBA infedele) può swappare `user_id` o `action_code` mantenendo la catena valida. Per TISAX L3 / NIS2 questo NON è un audit trail tamper-evident.
**Fix**: rendere l'hash su `json.dumps({user_id, action_code, level, entity_type, entity_id, timestamp_utc, payload}, sort_keys=True) + prev_hash`. Migrazione di re-hash dei record esistenti con marker "rebased_at_v2". Aggiornare `verify_audit_trail_integrity` di conseguenza.

### S3 — `resolve_current_risk_manager` ignora il plant
**Stato**: `[x]` (2026-04-26)
**Severity**: alta (privacy + correttezza).
**File**: `backend/apps/auth_grc/services.py:10-21`.
**Problema**: l'argomento `plant` non viene mai usato. Restituisce il **primo** `risk_manager` trovato globalmente. I task vengono assegnati a un risk manager che potrebbe non avere visibilità del plant in oggetto, esponendo dati incidente di plant non di sua competenza.
**Fix**: filtrare `UserPlantAccess` per `(scope_type="org") OR (scope_type="single_plant" AND scope_plants=plant) OR (scope_type="plant_list" AND scope_plants=plant) OR (scope_type="bu" AND scope_bu=plant.bu)`. Restituire `None` se nessuno e attivare un alert di governance.

### S4 — Audit log world-readable a qualunque utente autenticato
**Stato**: `[x]` (2026-04-27)
**Severity**: alta.
**Files**: `backend/apps/audit_trail/views.py` (`AuditLogViewSet`, `AuditIntegrityView`).
**Problema**: solo `IsAuthenticated`. Un Auditor Esterno (o un Plant Manager) può leggere chi ha fatto cosa su tutti i moduli, payload incluso (anche se l'email è pseudonimizzata, payload e timing sono in chiaro). Per ISO 27001 A.12.4.2 i log devono essere visibili solo a admin di sicurezza.
**Fix**: limitare a CISO / IT Security / Internal Auditor. `verify_integrity` solo a CISO/IT.

### S5 — `validate_uploaded_file()` mancante su 5/6 entry point
**Stato**: `[x]` (2026-04-26 — re-valutato: solo `plants.upload_logo` aveva un validator separato; bcp/suppliers/audit_prep passano per `documents.services.add_version_with_file/create_evidence_with_file` che valida. Estratto in `core/uploads.py` + plants refactorato. SVG rimosso dai logo per defense-in-depth XSS.)
**Severity**: alta (CLAUDE.md rule #12 violata).
**Files** che bypassano la validazione MIME/python-magic:
- `apps/bcp/views.py:181, 277` (test BCP evidence)
- `apps/plants/views.py:111` (plant upload)
- `apps/suppliers/views.py:79` (NDA upload)
- `apps/audit_prep/views.py` evidence (verificare)
- `apps/ai_engine` documenti analisi (verificare)
**Problema**: solo `documents/services.py` chiama `validate_uploaded_file`. Negli altri moduli un utente può caricare `.exe` rinominato `.pdf`.
**Fix**: spostare `validate_uploaded_file` in `core/uploads.py` e applicarlo a tutti i `request.FILES.get(...)` con whitelist MIME contestuale (PDF/DOCX per documenti, PDF/PNG/JPG per evidenze, ecc.).

### S6 — `anonymize_user()` GDPR Art.17 non funzionante
**Stato**: `[x]` (2026-04-26)
**Severity**: alta (compliance GDPR).
**File**: `backend/apps/auth_grc/services.py:129-168`.
**Problemi**:
1. `user.email` viene **prima** sovrascritto con `anon_email`, poi il filtro `AuditLog.objects.filter(user_email_at_time=user.email)` cerca l'email anonimizzata, non quella originale. La query non trova mai nulla.
2. Anche con la query corretta, `AuditLog.user_email_at_time` contiene l'email **già pseudonimizzata** dal momento dell'evento (es. `mar***@***.com`), quindi il match fallisce by design.
3. Non vengono propagati: `notifications`, `tasks.created_by` (FK al user, già OK), riferimenti testuali in `payload` JSONB.
**Fix**: catturare `original_email = user.email` PRIMA della sovrascrittura, calcolare `_pseudonymize_email(original_email)`, fare `AuditLog.objects.filter(user_id=user.pk).update(user_email_at_time=anon_email)` (filtro per `user_id` che è stabile). Aggiungere management command `gdpr_purge_user` per pulizia ricorsiva di payload contenenti l'email originale.

### S7 — Content-Security-Policy assente
**Stato**: `[x]` (2026-04-26)
**Severity**: alta.
**File**: `backend/core/middleware.py`.
**Problema**: nessun header `Content-Security-Policy`. SECURE_BROWSER_XSS_FILTER non impostato (deprecato ma ok). In caso di XSS (es. via campo libero non sanitizzato) l'attaccante può esfiltrare dati a qualunque dominio.
**Fix**: aggiungere CSP a `SecurityHeadersMiddleware` con default-src 'self' + connect-src whitelist API + Sentry + img-src per loghi. Test pagina admin (deve continuare a funzionare).

---

## P0 — RELIABILITY / FUNZIONALITÀ BLOCCANTI

### R1 — Frontend perde lo stato auth a ogni refresh + nessun token refresh
**Stato**: `[x]` (2026-04-27 — `localStorage` scelto su `sessionStorage` per allinearsi alla durata REFRESH JWT 7gg già definita in `SIMPLE_JWT.REFRESH_TOKEN_LIFETIME`. Trade-off documentato.)
**Severity**: alta UX + supporto.
**File**: `frontend/src/store/auth.ts`, `frontend/src/api/client.ts`.
**Problema**: lo store Zustand non usa `persist`. Ad ogni F5 l'utente è loggato fuori. Non esiste interceptor per `/api/token/refresh/`: alla scadenza del JWT (30 min) c'è hard redirect a `/login` anche se l'utente sta digitando. UX inaccettabile per webapp aziendale.
**Fix**:
1. `persist({ name: "grc-auth", partialize: state => ({ token: state.token, user: state.user, refresh: state.refresh }) })` su Zustand.
2. Salvare anche `refresh` token in store; interceptor risposta 401 → tenta `POST /api/token/refresh/`, se OK aggiorna token e rifà la request, se KO logout.
3. Token in `sessionStorage` invece di `localStorage` se possibile (limita persistenza a tab/finestra) — trade-off UX vs sicurezza da decidere col CISO.

### R2 — JWT `role` claim preso dal primo `UserPlantAccess` casuale
**Stato**: `[x]` (2026-04-27)
**Severity**: media (privilege confusion).
**File**: `backend/core/jwt.py:24-27`.
**Problema**: `UserPlantAccess.objects.filter(user=user).first()` — se l'utente ha più accessi (es. Risk Manager su Plant A + Internal Auditor su Plant B), uno è arbitrariamente perso. Il frontend prende decisioni UI sul `role` del token.
**Fix**: il claim `role` deve essere una **lista** `roles_by_plant: {plant_id: role}` o `roles: ["risk_manager", "internal_auditor"]`. Frontend leggerà la combinazione e selezionerà il ruolo "più alto" per la nav, mostrando lo switcher per plant.

### R3 — Postgres dev (16) ≠ prod (15)
**Stato**: `[x]` (2026-04-27 — `docker-compose.prod.yml` allineato a `postgres:16-alpine`. Aggiunte istruzioni inline per migrazione volume pgdata 15 → 16 (pg_dumpall + recreate volume + restore). **NON deploy automatico**: serve passaggio manuale una tantum prima del primo deploy del nuovo image.)
**Severity**: media.
**File**: `docker-compose.yml`, `docker-compose.prod.yml`.
**Problema**: sviluppi su 16, deploi su 15. JSONB ops, generated columns, planner cost differenze. Migrazioni testate possono regredire.
**Fix**: allineare entrambi a `postgres:16-alpine` (oppure entrambi a 15). 16 è raccomandato (LTS, performance JSONB migliorate).

### R4 — Backup non cifrati at rest documentati
**Stato**: `[x]` (2026-04-27)
**Severity**: alta per TISAX L3.
**File**: `backend/apps/backups/`, `BACKUP_DIR=/app/backups`.
**Problema**: il volume `backupdata` contiene dump SQL in chiaro montato sul container. Se il volume viene snapshottato dal cloud provider o esposto, i dati sono leggibili. Per TISAX L3 / ISO27001 A.8.24 i backup di dati personali devono essere cifrati.
**Fix**: cifrare il dump con `gpg --cipher-algo AES256 --symmetric` usando key in env (separata dalla `FERNET_KEY`). Alternativa: rclone con cifratura su S3-compatible.

---

## P1 — SICUREZZA (alta priorità)

### S8 — TrustedDevice token in localStorage = bypass MFA persistente via XSS
**Stato**: `[x]` (2026-04-28)
**File**: `frontend/src/pages/LoginPage.tsx:67`, `backend/apps/auth_grc/models.py::TrustedDevice`.
**Problema**: token 30 giorni in `localStorage` (`DEVICE_TOKEN_KEY`). XSS → attaccante esfiltra il token → re-login + skip MFA per 30 giorni anche dopo cambio password.
**Fix**: legare il token al fingerprint del browser (User-Agent + Accept-Language + secrets server-side); su rotazione password invalidare tutti i `TrustedDevice` dell'utente; valutare HttpOnly cookie con SameSite=Strict.

### S9 — MFA brute-force: nessun rate-limit per-utente
**Stato**: `[x]` (2026-04-28)
**File**: `backend/core/jwt.py::MfaVerifyView`.
**Problema**: throttle solo per IP (`LoginRateThrottle`, scope `login`, 5/min). Botnet distribuita → attacchi paralleli. Codice OTP a 6 cifre = 1M combinazioni: con 1000 IP a 5/min servono ~3.5h per coprire tutto lo spazio.
**Fix**: aggiungere lock per-utente (Redis: `mfa_lock:{user_pk}` con max 10 tentativi/ora, lock 1h al raggiungimento).

### S10 — Hard delete che violano soft delete
**Stato**: `[x]` (2026-04-28 — `apps/plants/views.py::PlantFrameworkViewSet.perform_destroy` ora `soft_delete()`. Il rollback upload in `apps/suppliers/views.py:111` resta `delete()` come da indicazione originale: e' garbage di un Document mai validato, non c'e' valore audit nel preservarlo.)
**Files**: `apps/plants/views.py:237`, `apps/suppliers/views.py:111`.
**Problema**: `instance.delete()` su `PlantFramework` e `Document` (rollback fallito upload).
**Fix**: il rollback upload in suppliers è accettabile (garbage); il delete in plants no — fare `soft_delete()` sull'associazione e archive.

### S11 — Throttle `user` 2000/h troppo alto
**Stato**: `[x]` (2026-04-28)
**File**: `backend/core/settings/base.py:142`.
**Problema**: 2000 req/h per user post-login. Un account compromesso può scrapare l'intero database in mezza giornata senza alert.
**Fix**: ridurre a 500/h come documentato in CLAUDE.md; aggiungere throttle scoped per endpoint sensibili (export CSV: 10/h).

### S12 — Body size / file upload limits non configurati
**Stato**: `[x]` (2026-04-28)
**File**: `backend/core/settings/base.py`.
**Problema**: `DATA_UPLOAD_MAX_MEMORY_SIZE` e `FILE_UPLOAD_MAX_MEMORY_SIZE` ai default Django (2.5MB). Né limit massimo assoluto. JSON body unbounded (denial of memory).
**Fix**: `DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024`, `FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024`, `DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000`. Per upload grandi (evidenze video?) usare endpoint dedicato con streaming.

### S13 — Swagger UI accessibile senza auth in DEBUG
**Stato**: `[x]` (2026-04-28)
**File**: `backend/core/urls.py:126-130`.
**Problema**: `if settings.DEBUG or SHOW_API_DOCS` espone `/api/docs/` senza autenticazione. In dev OK, ma `SHOW_API_DOCS=true` in staging espone tutta l'API surface.
**Fix**: gating con `IsAdminUser` anche in DEBUG; redirect a `/admin/login/` se non autenticato.

### S14 — `pip-audit` / `npm audit` non eseguiti automaticamente
**Stato**: `[x]` (2026-04-28)
**Files**: `backend/requirements/base.txt`, `frontend/package.json`.
**Problema**: `pip-audit>=2.7.0` è in requirements ma non c'è CI che lo invochi. Stesso per `npm audit`.
**Fix**: workflow GitHub Actions `security-audit.yml` che gira `pip-audit --strict` e `npm audit --omit=dev` ogni notte + a ogni PR.

---

## P1 — FUNZIONALI / ARCHITETTURA

### F1 — 12 ViewSet usano ancora `IsAuthenticated` (no RBAC)
**Stato**: `[x]` (2026-04-28)
**Files**: vedi lista S1, sezione permessi (audit_trail, ai_engine, lessons, incidents, reporting, compliance_schedule, audit_prep, bcp, documents, management_review, controls, suppliers).
**Problema**: replica del pattern OSINT che ha già `OsintReadPermission`/`OsintWritePermission`. Mappare a ruoli `governance`.
**Fix**: introdurre `core/permissions.py` con `RoleScopedPermission(read_roles=[...], write_roles=[...])` riutilizzabile.

### F2 — Apps senza audit logging su azioni sensibili
**Stato**: `[x]` (2026-04-29 — login success/failure gia' coperti in `core/jwt.py`, SMTP config in `notifications/views.py`, `schedule.requirement.changed` in `compliance_schedule/views.py`, export CSV/Excel in suppliers/risk/osint/controls; gap residui chiusi qui: `UserPlantAccessViewSet` audita create/update/destroy con `auth.access.granted/modified/revoked`, `anonymize_user` propaga la motivazione GDPR nel payload, `BACKUP_FAILED` / `BACKUP_RESTORE_FAILED` ora emessi su pg_dump/encryption/decryption/pg_restore/timeout/unexpected.)
**Files**: `apps/auth_grc/views.py` (login non logga successo/fallimento), `apps/notifications/views.py` (modifica configurazione SMTP non logga), `apps/backups/views.py` (creazione/restore backup non logga), `apps/reporting/views.py` (export non logga), `apps/compliance_schedule/views.py`.
**Problema**: per ISO 27001 A.12.4 e A.9.4.4 modifiche di configurazione e accessi privilegiati DEVONO essere loggati.
**Fix**: aggiungere `log_action` con codici `auth.login.success`, `auth.login.failure`, `notif.smtp.config.changed`, `backup.created`, `backup.restored`, `reporting.export.<scope>`, `schedule.requirement.changed`.

### F3 — Frontend TypeScript senza CI gate
**Stato**: `[ ]`
**File**: `frontend/package.json`, no `.github/workflows/`.
**Problema**: abbiamo appena fixato 17 errori TS. Senza gate CI rientreranno.
**Fix**: workflow `frontend-ci.yml` con `npm ci && npm run typecheck && npm run test` che blocca i PR.

### F4 — `pytest --cov-fail-under=70` rompe i subset
**Stato**: `[ ]`
**File**: `backend/pytest.ini`.
**Problema**: anche `pytest apps/osint/` fa fail per coverage globale (calcola su tutto il codebase). Falsi negativi continui.
**Fix**: rimuovere `--cov-fail-under` da `pytest.ini`; metterlo solo nel comando CI con scope `apps/ core/`. Locale `pytest apps/X/` non deve mai fallire per coverage.

### F5 — `BiaService.update_critical_process` (verifica) e altri service non transazionali
**Stato**: `[ ]`
**Files**: da auditare con grep `def.*services.py` senza `@transaction.atomic`.
**Problema**: operazioni multi-step (es. salva risk + crea task + log audit) non sono atomiche → stato inconsistente al primo errore.
**Fix**: revisione globale; tutti i service che toccano >1 modello devono avere `@transaction.atomic`.

### F6 — Postgres trigger `audit_no_mutation` esiste solo se le migrazioni sono applicate
**Stato**: `[ ]` (probabilmente già OK in dev e prod)
**File**: `backend/core/migrations/0002_audit_trigger.py`.
**Verifica**: aggiungere check al management command `verify_audit_trail_integrity` che il trigger esista (`SELECT 1 FROM pg_trigger WHERE tgname='audit_no_mutation'`); fail se mancante.

### F7 — `apps/ai_engine` AiSuggestView non scopa per plant
**Stato**: `[x]` (2026-04-27 — coperto da S1: `AiSuggestView` ora chiama `scope_queryset_by_plant(Incident.objects.all(), request.user).get(pk=entity_id)` per `incident_classify` / `rca_draft` e `scope_queryset_by_plant(ControlInstance.objects.all(), …)` per `gap_actions`. Un utente senza accesso al plant dell'entità ottiene 404 prima che il payload entri nel prompt AI.)
**File**: `backend/apps/ai_engine/views.py:69`.
**Problema**: `Incident.objects.get(pk=entity_id)` senza check di accesso del richiedente. Un utente con accesso a Plant A può chiedere all'AI di analizzare un incidente di Plant B.
**Fix**: dopo il `get`, validare che `request.user` abbia accesso a `entity.plant` via `UserPlantAccess`.

---

## P1 — UX / PRODOTTO

### U1 — Nessun warning di sessione in scadenza
**Stato**: `[ ]`
**Problema**: l'utente perde tutto a 30min senza preavviso.
**Fix**: timer client-side che mostra toast a -2min "Sessione in scadenza, vuoi rinnovare?" + bottone refresh manuale.

### U2 — Nessun gate i18n in CI
**Stato**: `[ ]`
**Problema**: la regola CLAUDE.md #14 richiede 5 lingue allineate. Manca check automatico.
**Fix**: script `scripts/check_i18n_completeness.py` (esiste `check_i18n_hardcoded.py` simile) che fail se IT/EN/FR/PL/TR non hanno le stesse chiavi. Eseguito in CI.

### U3 — Nessun ErrorBoundary React globale
**Stato**: `[ ]`
**Problema**: un crash in un modulo schianta tutta la SPA con white screen.
**Fix**: `<ErrorBoundary>` in `App.tsx` che mostra fallback UI + invia errore a Sentry.

### U4 — Skeleton/loading state poveri
**Stato**: `[ ]`
**Problema**: ovunque "Caricamento..." testuale. Nessuna percezione di progresso.
**Fix**: componente `<TableSkeleton rows={5}>` riutilizzabile, sostituire i testi.

### U5 — Nessun audit di accessibility (a11y)
**Stato**: `[ ]`
**Problema**: per applicazioni B2B aziendali Direttiva UE 2019/882 (Accessibility Act) obbligatoria da giugno 2025 per nuovi prodotti.
**Fix**: integrare `@axe-core/react` in dev mode, fix issues iniziali (label form, contrasto, tab order).

### U6 — Onboarding zero
**Stato**: `[ ]`
**Problema**: nuovo tenant entra e trova pagine vuote senza guida.
**Fix**: management command `seed_demo_data` (1 plant, 5 controlli, 1 incidente, 1 risk, 1 BCP) opzionale.

---

## P2 — HARDENING / OPS

### H1 — Health endpoint non rate-limited
**Stato**: `[ ]`
**File**: `backend/core/urls.py:43-51`.
**Problema**: `/api/health/` fa query DB ad ogni hit. DOS vector.
**Fix**: cache 30s o rate-limit anonimo dedicato (1 req/s).

### H2 — `/api/manual/` legge dal disco ad ogni richiesta
**Stato**: `[ ]`
**File**: `backend/core/urls.py:70-107`.
**Fix**: `lru_cache` su `_load_manual(manual_type, lang)`; invalidare al deploy.

### H3 — Nessun X-Request-ID per tracing
**Stato**: `[ ]`
**Problema**: tracciare un errore tra nginx → backend → celery → Sentry richiede correlation ID.
**Fix**: middleware che genera/propaga `X-Request-ID` (UUID4); aggiungerlo a `LOGGING` formatter.

### H4 — Logging non strutturato (no JSON)
**Stato**: `[ ]`
**File**: `backend/core/settings/base.py:287-308`.
**Problema**: log testuali → SIEM (Splunk/ELK) deve fare parsing fragile.
**Fix**: `python-json-logger` o `structlog` in prod; mantenere verbose in dev.

### H5 — Nessuna metrica Prometheus / OpenTelemetry
**Stato**: `[ ]`
**Problema**: Sentry traccia errori ma non KPI di business (n° task aperti, latency p95 endpoint critici, queue depth Celery).
**Fix**: `django-prometheus` + dashboard Grafana minima; metriche custom per moduli M03 (compliance %), M09 (incidenti aperti), M19 (notifiche fallite).

### H6 — Nessun runbook on-call
**Stato**: `[ ]`
**File**: nessuno.
**Fix**: `docs/RUNBOOK.md` con: come riavviare backend, come rieseguire un task Celery fallito, come restorare un backup, come ruotare la `FERNET_KEY` senza perdere dati cifrati.

### H7 — `docker-compose.prod.yml` espone frontend su 3001
**Stato**: `[ ]`
**File**: `docker-compose.prod.yml:98-99`.
**Problema**: bypassa nginx/NPM. In produzione il frontend deve essere SOLO dietro reverse proxy con TLS.
**Fix**: rimuovere `ports`, esporre solo via NPM. INFRASTRUCTURE.md probabilmente già lo spiega — verificare.

### H8 — Nessun resource limit nei container prod
**Stato**: `[ ]`
**File**: `docker-compose.prod.yml`.
**Problema**: un memory leak in Celery può saturare l'host.
**Fix**: `deploy.resources.limits` (memory: 1G per backend, 512M per worker, 256M per beat).

---

## P2 — DATA QUALITY / GRC SPECIFICO

### G1 — `BIA → BCP` link non enforced
**Stato**: `[ ]`
**Problema**: `CriticalProcess` ha `rto_target_hours`, ma nessun trigger DB/service forza che esista almeno un BcpPlan attivo che lo soddisfa.
**Fix**: management command settimanale che alerta su `CriticalProcess` con `rto_bcp_status=critical`.

### G2 — `Risk → Mitigation → Task` non coerente in tutti i casi
**Stato**: `[ ]`
**Problema**: un `RiskMitigationPlan` può esistere senza task creato in M08. Workflow incompleto.
**Fix**: creazione task automatica al `save()` di un mitigation plan se status=approvato.

### G3 — `Incident NIS2` deadline 24h non hard-enforced
**Stato**: `[ ]` (verifica)
**Problema**: il countdown frontend esiste ma se il backend non blocca mancato invio, è solo UI.
**Fix**: task Celery che ogni 15min verifica incidenti `nis2_notifiable=si` con deadline_24h<now() AND notifications_sent_24h is null → escalation a CISO.

### G4 — `Documents` retention policy non applicata
**Stato**: `[ ]`
**Problema**: TISAX richiede retention diversificata per categoria documento. CLAUDE.md cita retention solo per audit log.
**Fix**: aggiungere `retention_years` su `DocumentCategory` + management command che soft-delete documenti scaduti con notifica al document owner.

### G5 — `Suppliers` non hanno scoring di rischio cross-incidente
**Stato**: `[ ]`
**Problema**: M14 traccia fornitori, M09 incidenti, ma incident.supplier_id non aggiorna risk score automatico.
**Fix**: signal post_save su Incident con supplier → ricalcolo `Supplier.risk_score`.

---

## P2 — UX EXTRA

### X1 — Nessun "what's new" / changelog UI
**Stato**: `[ ]`
**Fix**: drawer in topbar che mostra `CHANGELOG.md` formatted, badge "novità" se l'utente non ha visto la release corrente.

### X2 — Mobile responsive parziale
**Stato**: `[ ]`
**Verifica**: alcuni moduli (es. RiskPage) hanno tabelle dense non responsive.
**Fix**: audit con DevTools mobile, breakpoint principali.

### X3 — Dark mode non disponibile
**Stato**: `[ ]`
**Fix**: Tailwind `dark:` variant + toggle in topbar (basso impatto, alta percezione).

---

## STATO BUILD / RUN (riferimento)

```bash
# Backend
docker compose exec -T backend pytest apps/ core/ -q
docker compose exec -T backend python manage.py verify_audit_trail_integrity
docker compose exec -T backend pip-audit --strict

# Frontend
docker compose exec -T frontend npx tsc --noEmit
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm audit --omit=dev
```

---

## NOTE OPERATIVE

- Conventional commits: `security(scope):` per S*, `fix(scope):` per R*/F*/G*, `feat(scope):` per U*/X*, `chore(ops):` per H*.
- Aggiornare `CHANGELOG.md` sotto `[Unreleased]` ad ogni voce chiusa.
- Nessuna release autonoma — confermare con utente prima di bump versione.
- I fix S1-S2-S6 sono propedeutici a una prima certificazione TISAX/ISO27001 della webapp stessa.

---

## REGISTRO LAVORO (append-only)

- 2026-04-26: documento creato. Revisione end-to-end del progetto post-OSINT. **47 voci aperte** (7 P0 sicurezza, 4 P0 affidabilità, 7 P1 sicurezza, 7 P1 funzionali, 6 P1 UX, 8 P2 hardening, 5 P2 GRC, 3 P2 UX extra). Nessun fix ancora applicato — solo identificato e prioritizzato.
- 2026-04-26: nota — non sono incluse micro-issue (frontend `as any`, service atomicity puntuale, OpenAPI completeness, dead code, naming inconsistencies, hardening docker-compose dev). Da aggiungere se priorità di prodotto le richiede.
- 2026-04-27: S4 chiuso — applicati `AuditLogReadPermission` (SUPER_ADMIN/COMPLIANCE_OFFICER/INTERNAL_AUDITOR/EXTERNAL_AUDITOR) a `AuditLogViewSet` e `AuditLogIntegrityPermission` (solo SUPER_ADMIN/COMPLIANCE_OFFICER) all'action `verify_integrity` + `AuditIntegrityView`. Aggiunti 3 test (Plant Manager → 403, Internal Auditor read OK, Internal Auditor su verify_integrity → 403). 527 test pass.
- 2026-04-27: R2 chiuso — `core/jwt.py::GrcTokenObtainPairSerializer.get_token` ora espone `roles` (lista deduplicata di tutti i ruoli dell'utente) e `roles_by_plant` (mappa `plant_id → [role,...]`, con chiavi speciali `__org__` per scope=org e `bu:<id>` per scope=bu). Il claim `role` legacy resta come "ruolo dominante" calcolato via `_ROLE_HIERARCHY` (super_admin > compliance_officer > internal_auditor > external_auditor > risk_manager > plant_manager > control_owner) per non rompere il frontend. UserPlantAccess soft-deleted esclusi. 6 test su `apps/auth_grc/tests/test_jwt_claims.py`. 556 test pass. Frontend: nessuna modifica richiesta a R2 (ne' regressione) — il frontend continua a leggere `role` per nav/sidebar; switch UI multi-plant restano backlog (R2 backend è la base, lo switcher UI sarà tracciato separato come issue UX).
- 2026-04-27: R1 chiuso — `frontend/src/store/auth.ts` ora usa `persist` middleware Zustand con `localStorage` (key `grc-auth`, partialize su user/token/refresh/selectedPlant). `frontend/src/api/client.ts` interceptor risposta 401: chiama `POST /api/token/refresh/` con il refresh token in store, su successo aggiorna `token` e ritenta la richiesta originale (single-flight via `refreshInFlight` Promise condivisa per evitare race su 401 multipli paralleli); su fallimento o assenza refresh esegue `logout()` e redirect `/login`. Aggiunti `setToken` allo store + 4 test su `auth.ts` (persistenza, setToken non tocca refresh, logout pulisce storage, setUser senza refresh OK). Sistemati anche 2 test pre-esistenti di LoginPage (mock JWT non decodificabile da `atob` — pre-rotto, non regressione di R1). 13 test frontend pass, typecheck pulito. Scelta: `localStorage` su `sessionStorage` per allinearsi a REFRESH=7gg backend; rivalutare con CISO se la policy aziendale richiede session-only.
- 2026-04-27: commit S1 → `8fcbc65 security(rbac): enforce plant scoping on data layer (newfix S1)` — solo file puri S1 (30 file). `audit_trail/*` (S4) e `tests/integration/test_audit_trail.py` (allineamento S2) lasciati intenzionalmente non staged perche' intrecciati con pre-existing changes S2/S3/S5/S6/S7 non ancora committate. CHANGELOG.md non staged (modifiche pre-esistenti accumulate da altre sessioni).
- 2026-04-28: S14 chiuso — nuovo workflow `.github/workflows/security-audit.yml` con due job: `pip-audit` (strict su `backend/requirements/base.txt`, warning-only su `dev.txt`), `npm audit` (`--omit=dev --audit-level=high` su `frontend`, full report come artifact con retention 30g). Trigger: nightly cron `30 3 * * *` UTC, PR su main che toccano `backend/requirements/**` o `frontend/package*.json`, manuale (`workflow_dispatch`). pip-audit: 1 vulnerabilita' critica blocca la build (pacchetti backend pochi e curati). npm audit: blocco solo su high/critical in produzione, low/moderate tracciate via report (registry npm rumoroso). Setup esplicito di pip-audit>=2.7.0 e Node 20. Cache su pip + npm per build < 2 min. **Nota operativa**: il workflow e' attivo solo dopo push su main del file (non testabile in locale); la prima nightly successiva al merge produrra' il primo report.
- 2026-04-28: S13 chiuso — `core/urls.py` ora monta `SpectacularAPIView` e `SpectacularSwaggerView` con `permission_classes=[IsAdminUser]` anche quando `DEBUG=True` o `SHOW_API_DOCS=True`. Anonimi e utenti non staff ricevono 401/403; solo `is_staff=True` accede. Prima `/api/docs/` era pubblico in dev/staging ed esponeva l'intera API surface (endpoint, parametri, esempi) a osservatori non autorizzati. 4 nuovi test in `backend/tests/test_swagger_gating.py` (anon, schema anon, user normale, admin). Test settings aggiornato (`SHOW_API_DOCS=True` in test per esercitare le rotte) — non incide su throttle/CI.
- 2026-04-28: S12 chiuso — `core/settings/base.py` ora fissa esplicitamente `DATA_UPLOAD_MAX_MEMORY_SIZE = 5 MB` (cap JSON/form, era unbounded oltre il default 2.5 MB), `FILE_UPLOAD_MAX_MEMORY_SIZE = 50 MB` (soglia in-memory per file multipart, oltre questa Django streama su /tmp), `DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000` (esplicito per code review). Allinea il prodotto a OWASP API4:2023 (Unrestricted Resource Consumption). 3 nuovi test in `backend/tests/test_upload_limits.py`. 140 test bundle (documents/plants/suppliers/bcp/audit_prep) restano verdi: nessun upload reale supera la soglia.
- 2026-04-28: S11 chiuso — `DEFAULT_THROTTLE_RATES["user"]` ridotto da 2000/h a 500/h come documentato in CLAUDE.md. Aggiunto scope `export` 10/h. Nuova classe `core.jwt.ExportRateThrottle` (sottoclasse `UserRateThrottle` con `scope="export"`) applicata via `@action(throttle_classes=[ExportRateThrottle])` ai 4 endpoint export bulk individuati: `apps/risk/views.py::RiskAssessmentViewSet.export` (Excel registro rischi), `apps/osint/views.py::OsintEntityViewSet.export_csv`, `apps/osint/views.py::OsintFindingViewSet.export_csv`, `apps/suppliers/views.py::SupplierViewSet.export_csv` (NIS2). Un account compromesso non puo' piu' scrapare l'intero database in mezza giornata (500/h * 12h = 6000 record vs 2000/h * 12h = 24000); per gli export bulk il limite e' ulteriormente abbassato a 10/h per utente. 193 test bundle (risk + osint + suppliers) pass. Trade-off: 500/h puo' impattare client batch o dashboard pesanti che fanno polling fitto — riducibile in caso a 1000/h con motivazione.
- 2026-04-28: S10 chiuso — `PlantFrameworkViewSet.perform_destroy` non chiama piu' `instance.delete()` (hard delete che violava CLAUDE.md regola #5) ma `instance.soft_delete()`. Aggiunta logica di "reattivazione" in `perform_create`: se esiste un PlantFramework soft-deleted con stesso `(plant, framework)` lo si riattiva (deleted_at=None, active=True, active_from aggiornato, level rideposito) invece di tentare l'INSERT (il vincolo `unique_together` sul DB ignora il soft-delete e farebbe `IntegrityError`). Riusa `_create_control_instances()` sul record riattivato (idempotente: salta i ControlInstance gia' esistenti). Il rollback `doc.delete()` in `apps/suppliers/views.py:116` resta hard-delete (Document mai validato, garbage senza valore audit). 2 nuovi test in `apps/plants/tests/test_api.py` (delete soft, recreate riattiva). 5 test plants pass.
- 2026-04-28: S9 chiuso — `MfaVerifyView` ora applica un lock per-utente in cache Redis sopra il throttle DRF per-IP. Costanti `_MFA_LOCK_THRESHOLD=10`, `_MFA_LOCK_WINDOW=3600`, `_MFA_LOCK_DURATION=3600`. Flusso: la chiave `mfa:lock:{user_pk}` viene controllata prima di chiamare `device.verify_token`; se presente -> 429 immediato. Su OTP errato il counter `mfa:attempts:{user_pk}` viene incrementato (con TTL 1h al primo incr); al raggiungimento di 10 tentativi viene impostato il lock 1h, eliminato il counter e loggato `AUTH_MFA_LOCKED`. Su OTP corretto il counter viene azzerato. Una botnet distribuita non puo' piu' aggirare il rate-limit IP scalando orizzontalmente: il lock e' legato all'identita' dell'utente (1M combinazioni a 10 tentativi/h = ~11 anni per esaurire lo spazio TOTP). 3 nuovi test in `apps/auth_grc/tests/test_mfa_flow.py` (lock dopo soglia, reset su success, rifiuto immediato se gia' bloccato). 37 test auth_grc pass. Trade-off: lock 1h su 10 tentativi puo' creare DoS su utente legittimo se l'attaccante ne conosce l'email — accettabile per il valore del bypass MFA, mitigato dal flow "contatta IT" e dal fatto che il lock e' rinnovabile manualmente via admin Django.
- 2026-04-28: S8 chiuso — `TrustedDevice` ora vincolato al fingerprint del browser (User-Agent + Accept-Language + `SECRET_KEY` come pepper) tramite il nuovo helper `compute_device_fingerprint(source)` in `apps/auth_grc/models.py`. `create_for_user(user, device_name="", fingerprint_source="")` salva l'hash; `verify(user, raw_token, fingerprint_source="")` lo confronta. `core/jwt.py` espone `_fingerprint_source(request)` (UA `\x01` Accept-Language, max 500+200 char) e lo passa sia in trust-device emission (`MfaVerifyView`) sia in `device_token` verification (`GrcTokenObtainPairView`). Token rubato via XSS e replayato da browser/lingua diversi → 202 MFA. Token legacy senza `fingerprint_hash` non sono piu' accettati (degradazione voluta). Nuovo signal `apps/auth_grc/signals.py`: `pre_save` rileva cambio password (confronto `old.password != new.password`), `post_save` revoca tutti i `TrustedDevice` dell'utente con `revoke_all_for_user()` + audit `AUTH_PASSWORD_CHANGED_DEVICES_REVOKED`. Caricato in `AuthGrcConfig.ready()`. **HttpOnly cookie SameSite=Strict valutato e non adottato in questo round**: cambio breaking che richiede revisione completa del flusso CSRF e dei consumer (frontend + eventuali integrazioni esterne) — annotare in backlog UX se richiesto dal CISO. Migrazione `auth_grc/0005_trusteddevice_fingerprint_hash`. 7 nuovi test su `test_trusted_device.py` (fingerprint OK, browser diverso, request senza UA, legacy record, password change cascade, password unchanged no-op, helper compute) + 1 nuovo test su `test_mfa_flow.py` (login da UA diverso → 202). Test esistenti aggiornati al nuovo contratto. **34 test auth_grc + 82 test bundle pass.**
- 2026-04-28: R4 chiuso — cifratura at-rest dei backup pg_dump. Nuovo `apps/backups/encryption.py` (AES-256-GCM via `cryptography`, key derivata PBKDF2-HMAC-SHA256 200k iter da `BACKUP_ENCRYPTION_KEY`); formato file `GRC1 || salt 16B || nonce 12B || ciphertext+GCM tag`. `services.create_backup` cifra il dump dopo `pg_dump`, applica suffisso `.enc`, marca `BackupRecord.encrypted=True`. `services.restore_backup` decifra in temp file e lo elimina sempre dopo `pg_restore`. Aggiunti `BACKUP_ENCRYPTION_KEY` a `.env.example` / `.env.prod.example` / `core/settings/base.py`; nuovo flag `BackupRecord.encrypted` (migrazione `backups/0002`). 5 test in `apps/backups/tests/test_encryption.py` (enable/disable, roundtrip, wrong-passphrase fail, magic-header fail, empty-key fail) — 20 test backups pass totali. **Operazione manuale post-deploy**: settare `BACKUP_ENCRYPTION_KEY` in `.env.prod` con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. I backup pre-esistenti restano in chiaro (`encrypted=False`) e devono essere ruotati o re-cifrati separatamente. Trade-off: scelta single-shot (no streaming) accettabile perche' i dump GRC sono ordine MB/centinaia di MB su single-tenant.
- 2026-04-27: S1 chiuso (modulo per modulo) — nuovo `core/scoping.py` con `PlantScopedQuerysetMixin` + funzione `scope_queryset_by_plant` (supporta FK, M2M e percorsi indiretti tipo `assessment__plant`, `audit_prep__plant`, `process__plant`, `document__plant`, `supplier__plants`, `cycle__plant`, `review__plant`, `plan__plant`). Mixin applicato a: `IncidentViewSet`, `NIS2ConfigurationViewSet`, `SupplierViewSet` (M2M `plants`), `SupplierAssessmentViewSet`, `SupplierQuestionnaireViewSet`, `RiskAssessmentViewSet`, `RiskDimensionViewSet`, `RiskMitigationPlanViewSet`, `RiskAppetitePolicyViewSet` (allow_null per policy org-wide), `CriticalProcessViewSet`, `TreatmentOptionViewSet`, `RiskDecisionViewSet`, `DocumentVersionViewSet`, `EvidenceViewSet`, `ControlInstanceViewSet`, `AuditPrepViewSet`, `EvidenceItemViewSet`, `AuditFindingViewSet`, `AuditProgramViewSet`, `PdcaCycleViewSet`, `PdcaPhaseViewSet`, `ManagementReviewViewSet`, `ReviewActionViewSet`, `LessonLearnedViewSet`, `PhishingSimulationViewSet`, `BcpPlanViewSet`, `BcpTestViewSet`. `DocumentViewSet` ha override custom (proprietario OR `shared_plants` OR org-wide). `AiSuggestView` valida l'accesso all'incidente / control instance prima di passarli all'AI (anche F7). 11 test mixin in `tests/test_scoping.py` + 7 test API cross-plant nei moduli (incidents, suppliers, risk, bia, documents, controls, pdca). Test allineati: `co_user`/`compliance_officer org` come fixture default. **550 test pass, 0 regressioni.** Reporting/ai_engine/governance/auth_grc: APIView aggregate o cross-plant by design — non scopate (ad eccezione di AiSuggestView). Vedi anche F7 e F1 che restano aperti per la mappatura puntuale dei permessi RBAC sugli endpoint.
- 2026-04-29: F2 chiuso — recap dello stato attuale: login success/failure gia' coperti in `core/jwt.py` da S8/S9 (`auth.login.success` / `auth.login.failure` con path `no_mfa` / `mfa_otp` / `trusted_device`); modifica SMTP gia' coperta in `apps/notifications/views.py::EmailConfigurationViewSet` con `notif.smtp.config.changed`; calendario compliance gia' coperto in `apps/compliance_schedule/views.py::ComplianceSchedulePolicyViewSet` con `schedule.requirement.changed` (incl. `update-rule` action); export CSV/Excel/PDF gia' coperti in `risk.assessment.export`, `suppliers.export.csv`, `reporting.export.osint_entities/findings`, `export.<format>` (controls). **Gap residui chiusi qui**: (1) `UserPlantAccessViewSet` (assegnazione/modifica/revoca ruoli privileged, ISO 27001 A.9.2.2 + A.9.4.4) — `perform_create` / `perform_update` / `perform_destroy` ora chiamano `log_action("auth.access.granted/modified/revoked", level="L2")` con payload sintetico (`user_id`, `role`, `scope_type`, `scope_bu_id`, `scope_plant_ids`); destroy fa `soft_delete()` se disponibile (era hard delete); (2) `anonymize_user(user, requesting_user, *, reason="")` ora accetta motivazione GDPR Art. 17 dal caller e la include nel payload (`reason`, troncato a 500 char); (3) backup fallimenti — `apps/backups/services.py::create_backup` audita `BACKUP_FAILED` su 4 percorsi (pg_dump returncode!=0 / cifratura / TimeoutExpired / Exception) con `stage` distinto; `restore_backup` audita `BACKUP_RESTORE_FAILED` su decryption fail e pg_restore fail prima di sollevare l'exception. 2 nuovi test in `apps/auth_grc/tests/test_api.py` (grant + revoke audit), 2 test esistenti in `apps/backups/tests/test_services.py` estesi per asserire l'audit BACKUP_FAILED. **599 test pass, 0 regressioni** (564 in apps/+core/, 35 in tests/).
- 2026-04-28: F1 chiuso — nuovo `core/permissions.py::RoleScopedPermission` (con helper `user_has_any_role`): permission base configurabile via `read_roles` / `write_roles` (set di `GrcRole`), bypass superuser, esclusione `UserPlantAccess` soft-deleted, fallback `write_roles` -> `read_roles` se vuoto. Mappatura per modulo in `apps/<module>/permissions.py` (11 file): `incidents` (operativi rw + auditor read), `audit_prep` (auditor + governance, write esclude external_auditor), `bcp` (owner rw + auditor read), `compliance_schedule` (read allargato a tutti i ruoli, write super_admin/compliance_officer), `controls` (FrameworkPermission + ControlInstancePermission con write a chi gestisce controlli + ControlsReportPermission per gap analysis/export), `documents` (lettura per tutti i ruoli operativi + scrittura a chi gestisce documenti, le query restano scopate da `DocumentViewSet.get_queryset` per owner/shared/org-wide), `lessons` (operativi + auditor read, write operativi), `management_review` (governance + auditor + plant_manager read, write super_admin/compliance_officer), `reporting` (read = governance + auditor, no control_owner), `suppliers` (governance rw + auditor read), `ai_engine` (`AiSuggestView`/`AiConfirmView` ai 4 ruoli operativi). 33 ViewSet/APIView migrati a `permission_classes=[<XxxPermission>]` (incl. `FrameworkViewSet`, `ControlDomainViewSet`, `ControlViewSet`, `GapAnalysisView`, `ComplianceExportView`, `DocumentViewSet`, `DocumentVersionViewSet`, `EvidenceViewSet`, `IncidentViewSet`, `NIS2ConfigurationViewSet`, `LessonLearnedViewSet`, `ManagementReviewViewSet`, `ReviewActionViewSet`, `BcpPlanViewSet`, `BcpTestViewSet`, `AuditPrepViewSet`, `EvidenceItemViewSet`, `AuditFindingViewSet`, `AuditProgramViewSet`, `ComplianceSchedulePolicyViewSet`, `RequiredDocumentViewSet`, `ActivityScheduleView`, `RequiredDocumentsStatusView`, `RuleTypeCatalogueView`, `SupplierViewSet`, `SupplierAssessmentViewSet`, `QuestionnaireTemplateViewSet`, `SupplierQuestionnaireViewSet`, `SupplierEvaluationConfigView`, `AiProviderConfigViewSet` (era IsAuthenticated+IsGrcSuperAdmin, ora solo IsGrcSuperAdmin), `AiSuggestView`, `AiConfirmView`, 8 viste reporting). 15 nuovi test in `tests/test_role_permissions.py` (matrice anonimo / no-role / read-only role / write role / superuser / soft-delete UserPlantAccess) su 3 endpoint disjoint (incidents, audit_prep, suppliers) per validare il wiring orizzontale. Aggiornati 5 fixture pre-esistenti per dotare `user` di un `UserPlantAccess` compliance_officer/risk_manager (compliance_schedule x2, documents, suppliers x2) e 1 test `test_user_without_access_sees_no_incidents` ora atteso a 403 (era 200 lista vuota: lo scoping S1 non e' piu' raggiungibile, la permission F1 blocca prima). Trade-off: F1 e' una restrizione "permission only" — non sostituisce lo scoping S1 (che decide *quali* record vedi all'interno del set di endpoint a cui hai accesso). Le APIView audit_trail/governance/auth_grc sono gia' coperte da permessi specifici (S4 + IsGrcSuperAdmin) e non sono state toccate. **597 test pass, 0 regressioni.**
