# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — versioning: [SemVer](https://semver.org/).

---

## [Unreleased]

### Fixed
- M14 Fornitori: codici CPV ora gestiti nel formato standard `XXXXXXXX-Y` (8 cifre + cifra di controllo ufficiale UE, es. `79211100-0`) sia in input manuale, sia nei suggerimenti AI; precedentemente la cifra di controllo veniva troncata. La cifra di controllo proviene dal catalogo ufficiale CPV (Reg. CE 213/2008) e non viene mai inferita o defaultata: i suggerimenti AI privi di check digit valido vengono scartati.
- M14 Fornitori: export CSV — codice CPV e descrizione ora in due colonne distinte (`Codici CPV` e `Descrizione CPV`) per agevolare filtri e analisi su Excel.

---

## [0.2.0] - 2026-04-16

### Added
- M14 Fornitori: nuovi campi ACN per conformità alla Delibera ACN n. 127434 del 13/04/2026 — `description` (descrizione fornitura), `cpv_codes` (Codici CPV, JSON list), `nis2_relevant` (flag NIS2), `nis2_relevance_criterion` (criterio ICT strutturale / non fungibilità / entrambi), `supply_concentration_pct` (% concentrazione fornitura) con property derivata `concentration_threshold` (bassa/media/critica secondo soglie TPRM <20%/20-50%/>50%); `vat_number` (CF/P.IVA) ora obbligatorio; migrazione `0006_supplier_acn_nis2_fields`
- M14 Fornitori: suggerimento codici CPV tramite AI (M20 AI Engine) — la descrizione della fornitura viene sanitizzata con `Sanitizer` prima dell'invio, il nome del fornitore non è mai inviato al cloud; human-in-the-loop obbligatorio (revisione prima dell'accettazione)
- M14 Fornitori: export CSV fornitori con tutti i campi ACN — endpoint `GET /suppliers/export-csv/` con parametro `?nis2_only=true` per filtrare ai soli fornitori NIS2 rilevanti; BOM UTF-8 per compatibilità Excel
- M14 Fornitori: filtro "Solo NIS2 rilevanti" in lista fornitori; colonne NIS2 e Concentrazione fornitura nella tabella; badge visivi per criterio e soglia TPRM
- M14 Fornitori: tab "NDA / Contratti" nell'espansione riga fornitore — lista documenti con stato e scadenza, upload NDA (multipart) con versioning SHA-256
- M14 Fornitori: tab "Stato NDA" a livello pagina — visione trasversale di tutti i fornitori attivi con semaforo stato NDA
- API endpoint `GET /suppliers/suppliers/<id>/nda/` e `POST /suppliers/suppliers/<id>/nda/upload/`
- `Document.supplier` FK (nullable) per collegare documenti NDA al fornitore (migrazione `0005_document_supplier_fk`)
- M15 Formazione: le righe della tabella corsi sono ora modificabili ed eliminabili dagli utenti con ruolo `super_admin` — pulsanti matita e cestino per riga, modale di modifica pre-compilata con tutti i campi (titolo, descrizione, fonte, stato, durata, scadenza, obbligatorio)
- Compliance Schedule: task Celery notturno `check_schedule_deadlines` (02:30) che crea automaticamente task in M08 per ogni attività in scadenza (urgency red/yellow) su tutti i plant attivi, con dedup su `source_id` e assegnazione per ruolo in base alla categoria
- M18 Reporting: nuovo tab KPI con quattro sezioni — copertura documenti obbligatori per framework, MTTR (finding audit / incidenti / task), completamento formazione obbligatoria (perimetro utenti GRC), stato NDA fornitori (ok/in scadenza/scaduto/mancante)
- Endpoint `GET /reporting/kpi-overview/?plant=<uuid>` — include sezione `supplier_nda` con contatori e dettaglio per fornitore
- AI Engine: `cpv_suggestion` aggiunto ai task routing con default `cloud`; voce visibile in Impostazioni → AI Engine → Routing per Task

### Fixed
- M03 Controlli: `check_evidence_requirements` degradava un controllo a "parziale" anche quando aveva evidenze valide — la logica iterava su tutte le evidenze di un tipo e marcava il requisito come non soddisfatto se qualsiasi di esse era scaduta, ignorando le altre valide. Ora il requisito è soddisfatto se esiste almeno un'evidenza non scaduta.
- M08 Task: i titoli dei task generati automaticamente da M03 (evidenze scadute) ora sono cliccabili e portano direttamente al drawer del controllo corrispondente in M03 Controls.
- Documenti obbligatori (M08/M18): tutti i documenti di tipo `procedure` e `record` risultavano sempre "Mancanti" anche se caricati — causato da disallineamento tra le chiavi inglesi di `RequiredDocument` (`procedure`/`record`) e le chiavi italiane di `Document.document_type` (`procedura`/`registro`). Aggiunta mappatura `_TYPE_MAP` in `get_required_documents_status`.
- Documenti obbligatori (M08/M18): documenti condivisi via `shared_plants` non venivano considerati — il filtro cercava solo `plant=plant`, ignorando il campo M2M. Corretto con `Q(plant=plant) | Q(shared_plants=plant)`.

---

## [0.1.0] - 2026-04-10

First public release. All 21 modules (M00–M20) implemented and operational.

### Added
- M00 Governance & Organigramma — organizational structure, roles (CISO/DPO/Plant Manager), multi-plant org chart
- M01 Plant Registry — plant registry, Business Unit, NIS2 entity profile, sub-plant
- M02 RBAC — dynamic role assignment per plant, access expiry, external auditor token
- M03 Controls Library — normative controls catalog from JSON (ISO 27001, NIS2, TISAX L2/L3), gap analysis, per-plant status
- M04 Asset Inventory IT/OT — asset inventory with criticality 1–5, badge tooltips, Approved Software List (NIS2/TISAX), change management
- M05 BIA & ROI — Business Impact Analysis, RTO/RPO calculation, ALE translation
- M06 Risk Assessment IT/OT — 5×5 heat map, IEC 62443 OT score, risk treatment, formal acceptance tracking with expiry and renewal
- M07 Documents & Evidence — SHA-256 versioning, 3-level approval workflow, evidence expiry, MIME check, multi-plant sharing without re-upload
- M08 Task & Schedule — role-based assignment, expiry notifications, cross-module compliance_schedule
- M09 Incident Management — NIS2 timers (24h/72h/30d), ACN template, real-time countdown, NIS2 Art.21 classification, Excel export
- M10 Audit Trail — append-only SHA-256 hash chain, PostgreSQL trigger (no UPDATE/DELETE), `verify_audit_trail_integrity` command, annual partitioning
- M11 PDCA Controller — Plan-Do-Check-Act cycle, automatic triggers, maturity history, blocked PDCA notification
- M12 Lesson Learned & KB — knowledge base with full-text search, categorization, PDCA linkage
- M13 Management Review — minutes, attendance, action items, KPI linkage (M18)
- M14 Supplier Management — supplier registry, VDA ISA 5.x assessment, NIS2 supply chain questionnaires
- M15 Training & Awareness — training plans, KnowBe4 bidirectional integration, completion tracking, phishing campaigns
- M16 Business Continuity — BCP plans, DR tests, plan expiry, BIA linkage (M05)
- M17 Audit Preparation — TISAX/ISO/NIS2 audit readiness, findings, evidence pack, soft-delete with annul (requires all findings closed)
- M18 Reporting & Dashboard — weekly KPI snapshot, report export, cross-module dashboard, Risk/BIA/BCP tabs with heatmap and NIS2 breakdown
- M19 Notifications & Integrations — in-app notifications, email digest, SIEM webhook, per-role notification profiles
- M20 AI Engine (optional) — severity classification, RCA analysis, document drafts, anomaly detection — GDPR sanitization layer, human-in-the-loop
- Multi-language UI: IT / EN / FR / PL / TR across all modules, emails, and exports
- Multi-plant architecture with Business Unit hierarchy and per-plant NIS2 profile
- Automatic nightly backup task (02:00, 30-day retention) via Celery Beat
- Sentry integration for error monitoring — backend (Django + Celery) and frontend (React + BrowserTracing + SessionReplay), GDPR-safe
- `ModuleHelp` contextual help drawer on all main operational modules
- Bottom bar with user manual, technical manual, and donation link
- Production Docker setup: `Dockerfile.prod` + `docker-compose.prod.yml` with non-root user and Gunicorn

### Security
- JWT 30min access / 7-day refresh with rotation and blacklist (SimpleJWT + token_blacklist)
- Login rate limiting: 5/min (LoginRateThrottle); authenticated users 500/h; anonymous 20/h
- File upload: extension whitelist + real MIME check (python-magic)
- SMTP credentials encrypted at rest with Fernet AES-256 (`FERNET_KEY`)
- Password policy: minimum 12 characters, CommonPassword, NumericPassword, UserAttributeSimilarity validators
- GDPR: `anonymize_user()` in `auth_grc/services.py`, automatic monthly audit log retention
- Security HTTP headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options

### Fixed
- Resolved N+1 query patterns across controls, risk, documents, and evidence endpoints
- Fixed off-by-one date display on mitigation plans and appetite policy
- Fixed false "expired" status on formal risk acceptance created on the same day
- Fixed 500 error on risk export with missing context
- Fixed UUID serialization in management review snapshot
- Fixed Polish quotation marks in `pl/common.json` i18n files
- Fixed rate-limit 429 errors caused by mass refetch on window focus

### Changed
- Controls nightly task now uses `check_evidence_requirements`; fixed null handling on expired status
- Risk acceptance: unified simple and formal acceptance flows
- Documents: alphabetical sorting by title
- Frontend: adopted React Query with stale-time tuning to reduce redundant API calls

[0.1.0]: https://github.com/fpino87-dev/grc-webapp/releases/tag/v0.1.0
