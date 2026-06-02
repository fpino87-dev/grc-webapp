# BUD — Backlog Unico di Debito & Sviluppo (GRC webapp)

> File di lavoro persistente. Si riprende **a ogni sessione**: si parte dai **P0 (critico, alto costo/beneficio)**, poi P1, poi P2.
> Aggiornare lo **Stato** delle voci man mano. Ultimo aggiornamento: **2026-06-02**.
>
> Legenda stato: ⬜ da fare · 🔄 in corso · ✅ fatto · 🧊 rimandato
> Legenda C/B: costo (S/M/L) · beneficio (Basso/Medio/Alto)

---

## 0. Già fatto (sessione 2026-06-02)
- ✅ OSINT: subdomain takeover (`enrichers/takeover.py`), lookalike weaponization, de-dup scan per dominio. (commit 939266b, ff594a3)
- ✅ Celery: OSINT weekly scan mai schedulato → PeriodicTask creata + consolidamento `beat_schedule` in `settings` (era codice morto in `celery.py`). (a7b8c4e, e600052)
- ✅ Backup notturno doppione (`auto-backup-daily` + command) → rimosso. (fdbdb41)
- ✅ Collisioni cron mattutine + finestra backup 02:00 liberata. (7ff649a, d284d4d)
- ✅ Scadenzario: bug `plant` vs `plants` (M2M Supplier) — scadenze fornitori per plant non calcolate. (76fc858)
- ✅ M06 Risk: `needs_revaluation` over-flagging (chiavi payload → diff valori) + "Completa" chiude il flag; pulizia 27 rischi Chivasso. (a0d7271)

---

## 1. P0 — Critico / alto costo-beneficio (si parte da qui)

### P0-1 · `controls.needs_revaluation` non chiudibile + cascata `assets.register_change` ridondante — ✅ FATTO (2026-06-02)
- **Trovato**: in `controls` il flag `needs_revaluation` veniva **solo settato** (dalla cascata asset) e **mai azzerato** → `evaluate_control` non lo chiudeva, restava a vita. La cascata `register_change` ri-flaggava TUTTI i controlli del plant **per ogni processo** BIA (filtro `plant=asset.plant` che ignorava il processo) → ri-scritture e conteggio ×N. Non atomica.
- **Fatto**: `evaluate_control` ora azzera il flag (rivalutare = chiudere); cascata controlli fatta **una sola volta** + `@transaction.atomic` su `register_change`; test di regressione (assets+controls 83 verdi). 0 flag stuck a DB → nessuna pulizia necessaria. (commit: vedi git)
- **NB**: il narrowing reale (flaggare solo i controlli dell'asset, non tutto il plant) richiede un legame `ControlInstance↔asset/processo` che **non esiste nel modello** → spostato in P1-5.

### P0-2 · Verifica schedulazione (no più "automazione fantasma") — ✅ FATTO (2026-06-02)
- **Fatto**: command `apps/audit_trail/.../verify_schedule.py` (confronta settings vs PeriodicTask: MISSING/DISABLED/MISMATCH; exit≠0 per CI; `--report-only`). Riepilogo esposto in `GET /api/health/` (`schedule.expected/problems`, non altera lo status). 6 test. Verificato live: 22/22 allineate.
- **TODO opzionale**: aggiungere `verify_schedule` come step in CI (`security-audit.yml`/test workflow) per fallire la build sul drift.

### P0-3 · Bonifica `except: pass` nei calcoli di compliance
- **Problema**: eccezioni inghiottite nascondono bug per settimane (provato col bug `plant`/`plants`). Occorrenze: controls 6, osint 6, suppliers 3, governance/incidents/audit_prep 2, ecc.
- **Azione**: policy "nessun except silenzioso": almeno `logger.exception` + contatore errori esposto; rivedere caso per caso i calcoli di compliance.
- **C/B**: M · Alto · Stato: ⬜

---

## 2. P1 — Importante (difendibilità del dato, integrità, sicurezza)

### P1-1 · `reporting`: estrarre `services.py` + test (oggi 1026 righe in view, **0 test**)
- **Problema**: la parte che vede direzione/auditor è la meno testata; logica cross-modulo dentro `APIView.get` (viola regola #2).
- **Azione**: `reporting/services.py` con funzioni pure; ≥20 test sui numeri della dashboard.
- **C/B**: L · Alto · Stato: ⬜

### P1-2 · `@transaction.atomic` sulle azioni multi-write + audit
- **Problema**: `risk, tasks, assets, bia, incidents, documents, notifications` con atomic=0. Es. `risk.complete` (score+ALE+escalate+save), `assets.register_change` (cascata). Stato parziale → audit append-only incoerente.
- **Azione**: avvolgere le azioni che scrivono >1 entità (priorità risk/incidents/assets).
- **C/B**: M · Alto · Stato: ⬜

### P1-3 · Write-authorization granulare (SoD) dove `permission_classes=0`
- **Problema**: default globale `IsAuthenticated` + RBAC solo in `get_queryset` (visibilità). In `risk, assets, plants, bia, pdca, governance, tasks, training` chi vede può anche modificare/cancellare → SoD debole.
- **Azione**: permission object-level riusabile per **write** con check di ruolo nello scope.
- **C/B**: M · Alto · Stato: ⬜

### P1-5 · Legame `ControlInstance ↔ asset/processo` per restringere la cascata change
- **Problema**: oggi `register_change` flagga i controlli a livello di **plant** (manca un legame diretto controllo↔asset/processo). Troppo largo: un change su un asset rimette "da rivalutare" l'intera postura di conformità del plant.
- **Azione**: aggiungere il legame (M2M `ControlInstance.assets`/`processes` o tramite SoA/BIA) e flaggare solo i controlli realmente impattati.
- **C/B**: M · Medio · Stato: ⬜

### P1-4 · `ai_engine`: test sanitizer "no-PII-leak" + circuit breaker LLM
- **Problema**: 8 test su orchestratore che spende su LLM; manca test che garantisca nessun PII esca senza sanitize e fallback se LLM giù.
- **C/B**: M · Medio · Stato: ⬜

---

## 3. P2 — Copertura test & evoluzioni prodotto

### P2-1 · Colmare gap di test
- reporting 0 → ≥20; plants 5 (registry core!) → ≥20; ai_engine 8; lessons 7; training 11; mgmt_review 12; notifications 12; documents 14. **C/B**: M · Medio · Stato: ⬜

### P2-2 · Asset OT network fields → sblocca automazioni
- Aggiungere campi rete a `AssetOT` → abilita `osint._sync_assets_ot` e l'escalation OT (`osint.alerts._has_ot_asset_linked` oggi ritorna sempre False). **C/B**: M · Medio · Stato: ⬜

### P2-3 · OSINT evoluzioni (da [[project_osint_backlog]])
- CT monitoring proattivo, DKIM/MTA-STS, Shodan/Censys, MISP/abuse.ch, pesi scoring in OsintSettings, RDAP vs WHOIS, notifiche M19 per alert critici, KPI `osint_critical_open_count` via `/api/v1/kpi-ingest/`. **C/B**: vario · Stato: ⬜

### P2-4 · Catene di valore GRC più strette
- BIA→BCP→Risk; PDCA↔finding automatico; KPI engine→management_review auto-popolato; concentrazione fornitura→risk. **C/B**: L · Medio · Stato: ⬜

---

## 4. Note di metodo
- Ogni fix: regola #2 (logica in services), #3 (audit), #5 (soft-delete), test di regressione, voci CHANGELOG sotto `[Unreleased]` per feat/fix/security.
- Pattern ricorrente da sorvegliare: **flag di stato** (needs_revaluation) basati su presenza-nel-payload invece che diff reale; **cascate broadcast** troppo larghe; **except silenziosi**; **job schedulati non a DB**.
