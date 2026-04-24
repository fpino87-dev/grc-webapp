# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — versioning: [SemVer](https://semver.org/).

---

## [Unreleased]

### Added
- Modulo OSINT (Fase 1/6) — **prerequisiti dati**: nuovi campi opzionali `Plant.domain` (dominio internet principale del sito) e `Plant.additional_domains` (JSON list di domini aggiuntivi/plant), `Supplier.website` (URL fornitore), `AssetSW.vendor_url` (URL vendor software). Utilizzati dal modulo OSINT per monitoraggio passivo. UI Plant aggiornata (form Edit + Create) con i due nuovi campi ("Dominio principale" e "Domini aggiuntivi / Plant") — i18n completa in IT/EN/FR/PL/TR. Migrazioni: `plants.0007`, `suppliers.0011`, `assets.0006`. Non breaking: tutti i campi sono opzionali.
- Modulo OSINT (Fase 2/6) — **app `osint` + modelli base**: nuova Django app `apps.osint` con 5 modelli (`OsintEntity`, `OsintSubdomain`, `OsintScan`, `OsintAlert`, `OsintSettings`), tutti ereditano da `BaseModel` (UUID pk, soft delete, audit). `OsintSettings` è singleton con soglie score (default critico=70, warning=50), frequenza scan (weekly/monthly) per miei domini / fornitori NIS2 / fornitori non critici, policy sottodomini (default "chiedi conferma"), toggle anonimizzazione AI (default on). API key threat intel (VirusTotal, AbuseIPDB, HIBP, Google Safe Browsing, OTX) cifrate a riposo con `EncryptedCharField` (AES-256 via `FERNET_KEY`). Admin Django registrato per tutti i modelli. Migrazione `osint.0001_initial`. Decisione architetturale: single-tenant (nessun `tenant_id`), link soft a Incidents/Tasks via `UUIDField` (il modulo OSINT **non modifica** i moduli esistenti).
- Modulo OSINT (Fase 3/6) — **aggregator service**: nuovo `apps.osint.services.aggregate_entities()` idempotente che sincronizza `osint_entities` leggendo da Plants (`domain` + `additional_domains`), Suppliers (`website`), Asset IT (`fqdn` + `ip_address`) e Asset SW (`vendor_url`). Helper `extract_domain()` per normalizzazione hostname da URL. Gestione soft-delete: se la sorgente viene eliminata dal modulo origine, l'entità OSINT viene marcata `is_active=False` (preservazione storico). Helper `find_duplicates()` per banner UI quando stesso dominio proviene da più sorgenti. Frequenza scan per entità risolta tramite `OsintSettings` (fornitori NIS2 → freq_suppliers_critical, altri → freq_suppliers_other). Test: 15 casi in `apps/osint/tests/test_services.py`.
- Modulo OSINT (Fase 4/6) — **enrichment engine + score engine**: 7 enricher passivi (`ssl`, `dns`, `whois_enr`, `virustotal`, `abuseipdb`, `otx`, `gsb`, `hibp`) orchestrati da `enrichers/run.py` con throttling per-enricher (15s tra crt.sh/VT, 5s tra AbuseIPDB/OTX) per rispettare i rate limit delle API. Enricher `ssl`: verifica TLS diretta + crt.sh CT-log per rilevamento sottodomini. Enricher `dns`: dnspython — SPF/DMARC/MX/DNSSEC. Enricher `hibp`: limitato a `entity_type=my_domain`, non inviato per fornitori terzi. Score engine (`scoring.py`): formula weighted differenziata per tipo entità — `my_domain` SSL 25% / DNS 25% / Reputazione 30% / GRC 20%, `supplier` SSL 30% / DNS 30% / Reputazione 40% (no GRC). Score 0–100 (più alto = peggio), classificazione: `critical` ≥70, `warning` ≥50, `attention` ≥30, `ok` <30. Dipendenze aggiunte: `dnspython==2.7.*`, `python-whois==0.9.*`.
- Modulo OSINT (Fase 5/6) — **alert engine, Celery scheduler, AnonymizationService, API REST, integrazione AI (M20)**: alert engine (`alerts.py`) con 7 trigger (score critico, score degradato ≥20pt, SSL scaduto/in scadenza, blacklist, DMARC mancante, nuovo sottodominio, breach HIBP) — routing automatico: `my_domain + critico` → incidente, `supplier + critico/warning` → task, OT supplier → `pending_escalation`, `new_subdomain` → solo dashboard. Anti-duplicate: nessun nuovo alert se esiste già un alert attivo dello stesso tipo. Task Celery `osint.weekly_scan` (lun ore 02:00 UTC) rispetta la frequenza `weekly/monthly` per entità; task on-demand `osint.scan_entity` con `autoretry`. `AnonymizationService` (`anonymizer.py`): sostituisce domini/IP/URL con placeholder `[DOM_001]`, `[IP_001]` ecc. prima dell'invio all'AI; deanonymize ricostruisce il testo originale; mapping solo in RAM (nessuna persistenza). API REST completa su router DRF: `OsintEntityViewSet` (read-only + `history`, `scan_detail`, `scan` force), `OsintAlertViewSet` (acknowledge/resolve + `escalate`), `OsintSubdomainViewSet` (`pending` + classify), `OsintDashboardView` (summary), `OsintSettingsViewSet`, `OsintAiView` (analyze con anonimizzazione + M20 AI router). 3 nuovi task type in `AiProviderConfig`: `osint_attack_surface`, `osint_suppliers_nis2`, `osint_board_report`.
- Modulo OSINT (Fase 6/6) — **frontend dashboard**: nuova sezione "🔍 OSINT Monitor" in sidebar (gruppo "Sicurezza", visibile a `super_admin`, `ciso`, `compliance_officer`). Tre route: `/osint` (dashboard), `/osint/settings` (impostazioni OSINT), `/osint/subdomains` (gestione sottodomini). Dashboard con 5 KPI card, banner sottodomini pending, filtri tab (tutti/miei domini/fornitori) + ricerca + sort, tabella entità con score badge colorato, delta arrow (▲▼), icon sub-score (SSL/DNS/Reputazione) e contatore alert. Drawer dettaglio entità: score totale + delta, 4 pill (SSL/DNS/Rep/GRC), checklist rilevamenti (SSL/DMARC/SPF/blacklist/VT/HIBP), grafico storico recharts con zone colorate (rosso=critico, arancio=warning, giallo=attenzione, verde=ok, asse Y invertito), alert attivi con link a incidente/task, pulsante "Forza scansione". Pannello AI modale: selezione analisi (superficie attacco / briefing NIS2 / report board), spinner durante analisi, copia/download/rigenera. Pagina Impostazioni OSINT: soglie score, frequenza scan, policy sottodomini, toggle anonimizzazione, campi API key (write-only, con indicatore "chiave salvata"). Pagina Sottodomini: tabella pending con azioni includi/ignora/ripristina. i18n completa IT/EN/FR/PL/TR per tutte le chiavi `osint.*`.

## [0.3.0] - 2026-04-24

### Added

- M03 Controlli — Genera documento procedura (AI): nuovo pulsante "Genera Procedura (.docx)" nel tab "Cos'è" del drawer di dettaglio controllo. Chiama `POST /controls/controls/{id}/generate-document/` con la lingua UI corrente; il backend usa l'AI Engine (M20) con `max_tokens=4096` per produrre un documento Markdown strutturato (Scopo, Ambito, Riferimenti normativi, Ruoli, Procedura, KPI, Frequenza revisione), lo converte in `.docx` via `python-docx` e lo serve come attachment con nome `{external_id}_procedura.docx`. Il frontend triggera il download diretto senza modale né upload. Audit trail L1 su ogni generazione. Nessun PII inviato all'AI (dati normativi puri). Dipendenza aggiunta: `python-docx==1.1.*`.
- M03 Controlli — Framework ACN NIS2: nuovo file `backend/frameworks/ACN_NIS2.json` con 43 misure di sicurezza ai sensi del D.Lgs. 138/2024 (trasposizione italiana NIS2), strutturate secondo NIST CSF 2.0 (domini GV/ID/PR/DE/RS/RC). 37 misure si applicano sia ai soggetti essenziali sia agli importanti (`level=""`); 6 si applicano solo ai soggetti essenziali (`level="essential"`: ID.AM-03, PR.AT-02, PR.PS-01, PR.PS-03, PR.IR-03, RC.CO-03). Al momento dell'attivazione del framework su un impianto con `nis2_scope="importante"`, il service `_create_control_instances` crea istanze solo per le 37 misure comuni, escludendo automaticamente quelle riservate ai soggetti essenziali. Tutte le 43 misure includono `evidence_requirement` strutturato e traduzioni in IT/EN/FR/PL/TR. Il codice framework `ACN_NIS2` è completamente separato dall'esistente `NIS2`: zero impatto su controlli ed evidenze in produzione.
- M14 Fornitori — Valutazione interna del rischio (Fase 1/7): nuovo model singleton `SupplierEvaluationConfig` per gestire pesi, label dei 6 parametri (Impatto, Accesso, Dati, Dipendenza, Integrazione, Compliance), soglie di classificazione (basso/medio/alto/critico), validità assessment esterno (default 12 mesi) e flag bump NIS2 — tutto editabile via UI Impostazioni, nessun valore hardcoded. Endpoint `GET /suppliers/evaluation-config/` (auth) e `PUT` (super_admin GRC) con audit trail. Management command `load_supplier_evaluation_config` per seeding/reset. Migrazione `0007_supplierevaluationconfig`. Pesi default: Impatto 0.30, Accesso 0.20, Dati 0.20, Compliance 0.15, Dipendenza 0.10, Integrazione 0.05 (somma 1.00). Categorie Compliance riscritte per riflettere certificazioni cyber rilevanti per NIS2/TISAX/ISO27001 (rimossi IATF e "Base" generici).
- M14 Fornitori — Valutazione interna del rischio (Fase 2/7): nuovo model `SupplierInternalEvaluation` storicizzato (6 score 1–5, weighted_score, risk_class, snapshot dei pesi/soglie usati al momento della valutazione, flag `is_current` per la valutazione attiva). Service `create_internal_evaluation()` con validazione score (1–5), calcolo weighted_score = Σ score × peso, classificazione automatica con le soglie correnti, gestione storico (precedente marcata `is_current=False`), audit log L2. Migrazione `0008_supplierinternalevaluation`.
- M14 Fornitori — Rischio aggiustato (Fase 3/7): nuovi campi calcolati su `Supplier` — `internal_risk_level` (classe interna corrente), `risk_adj` (rischio aggiustato), `risk_adj_updated_at`. Service `risk_adj.recompute_risk_adj()` implementa formula B (worst-case): `base = max(classe_interna, classe_esterna_se_valida)`, con classe esterna dedotta dall'ultimo `SupplierAssessment` approvato entro validità (default 12 mesi). Bump NIS2: +1 classe se `nis2_relevant=True` AND `concentration_threshold='critica'` AND `config.nis2_concentration_bump=True` (saturazione a `critico`). Hook automatici: `approve_assessment` ricalcola, signal `post_save` su `Supplier` ricalcola al cambio di NIS2/concentrazione, `create_internal_evaluation` ricalcola. Task Celery `recompute_expired_risk_adj_task` (02:45 ogni notte) intercetta assessment scaduti che non devono più partecipare al worst-case. Rationale: NIS2 Art.21.2(d), TISAX 5.2.x, ISO27001 A.5.19–A.5.21. Migrazione `0009_supplier_internal_risk_level_supplier_risk_adj_and_more`.
- M14 Fornitori — API REST valutazione interna (Fase 4/7): nuovi endpoint `GET/POST /suppliers/<id>/internal-evaluation/` (recupero valutazione corrente / creazione nuova, storicizza la precedente) e `GET /suppliers/<id>/internal-evaluation/history/` (storico completo). `SupplierSerializer` espone ora `internal_risk_level`, `risk_adj`, `risk_adj_updated_at` come read-only. Test API 11 casi: validazione score, storicizzazione, trigger risk_adj, permessi super_admin su config, validazione somma pesi.
- M14 Fornitori — Frontend valutazione interna + Impostazioni (Fase 5/7): nuovo tab "Valutazione interna" nell'espansione riga fornitore (form 6 parametri con anteprima weighted_score e classe, storico con marker "corrente", card valutazione attiva con pesi snapshot). Colonna "Rischio Adj" sostituisce "Rischio" nella tabella fornitori (mostra classe interna come sotto-testo quando differisce). Nuova pagina `/settings/supplier-evaluation` (solo super_admin): edit pesi (con controllo somma live), soglie classificazione, validità assessment (mesi), toggle bump NIS2, label dei 5 livelli per ciascun parametro. Voce sidebar "Valutazione Fornitori" tradotta IT/EN/FR/PL/TR. Filtro API esteso anche a `risk_adj`.

### Changed
- M14 Fornitori — Rischio aggiustato: formula estesa a **tre sorgenti opzionali** (worst-case): (1) valutazione interna corrente, (2) questionario valutato non scaduto, (3) audit terze parti (`SupplierAssessment` approvato entro validità configurata). Ogni sorgente contribuisce solo se presente; il `risk_adj` finale è il massimo tra quelle disponibili + bump NIS2. Gli assessment esterni possono ora essere eliminati via `DELETE /assessments/<id>/` (soft delete) con ricalcolo automatico del `risk_adj` del fornitore e audit trail L2.

### Fixed
- M03 Controlli — task notturno `check_expired_evidences`: non genera più task "Nessuna evidenza valida" per ControlInstance il cui plant non ha più il framework attivo (es. dopo rimozione del PlantFramework). Aggiunto filtro `Exists(PlantFramework)` sulla query. Contestualmente, `perform_destroy` in `PlantFrameworkViewSet` ora effettua soft-delete di *tutte* le ControlInstance del plant+framework al momento della rimozione (non solo quelle `non_valutato`), eliminando alla radice la causa delle istanze orfane.
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
