# BUD — Backlog Unico di Debito & Sviluppo (GRC webapp)

> File di lavoro persistente. Si riprende **a ogni sessione**: si parte dai **P0 (critico, alto costo/beneficio)**, poi P1, poi P2.
> Aggiornare lo **Stato** delle voci man mano. Ultimo aggiornamento: **2026-06-03**.
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

### P0-3 · Bonifica `except: pass` (audit AST: 31 `pass` + 119 "soft") — TARGET PRECISI
- **Trovato (AST)**: la stragrande maggioranza è LEGITTIMA (`except ValidationError→400`, `DoesNotExist→404`, `ValueError→fallback`, `ImportError→dep opzionale`). Da bonificare solo il sottoinsieme `except Exception: pass` che inghiotte logica o audit/notifiche.
- ✅ Già fixato: `osint/views.py:339` (nome PeriodicTask vecchio → next_scan sempre null). (commit 1efdb79)
- ✅ 🔴 **Logica reale inghiottita** — investigati: tutti e 5 sono "best-effort" legittimi (nessun bug di comportamento), ma ora **loggano** (`logger.warning`) invece di `pass` silenzioso: `incidents/nis2_services.py:652` (PDCA NIS2), `audit_prep/views.py:70` (sync_program_completion), `controls/views.py:850+859` (verbali + risk register nello ZIP), `bcp/services.py:142` (evidenza test), `documents/services.py:166` (file orfano). (commit: vedi git)
- ✅ 🟠 **Audit/notifiche best-effort** — ora loggano (`logger.warning`): audit (`auth_grc/signals.py`, `osint/views.py` ×2), notifiche (`audit_prep/services`, `bcp/services`, `controls/tasks`, `incidents/services`, `suppliers/services`), documenti (`documents/services` ×3).
- ✅ 🟡 **broad→narrow**: `governance/views.py` ×2 e `risk/views.py` ora `except (ValueError, TypeError, OverflowError)` + log; `bcp/views.py` logga.
- **C/B**: M · Alto · **Stato: ✅ FATTO (2026-06-02)** — 448 test verdi sui moduli toccati, system check pulito.

---

## 2. P1 — Importante (difendibilità del dato, integrità, sicurezza)

### P1-1 · `reporting`: estrarre `services.py` + test (oggi 1026 righe in view, **0 test**) — ✅ FATTO (2026-06-03)
- **Problema**: la parte che vede direzione/auditor era la meno testata; logica cross-modulo dentro `APIView.get` (viola regola #2).
- **Fatto**: tutta la logica spostata in `reporting/services.py` (funzioni pure: `compliance_summary`, `risk_summary`, `incident_summary`, `owner_report`, `kpi_trend`, `risk_bia_bcp`, `dashboard_summary`, `kpi_overview`+`_mttr`/`_required_docs`/`_training`/`_supplier_nda`, `kpi_suggest`); view ridotte a wrapper sottili. **32 test** (22 sui numeri + 10 smoke API/permessi); reporting/services 90%, views 91%; coverage globale 71.59%.
- **Bug trovato e corretto**: `_mttr` filtrava `finding_type` su `"major"`/`"minor"` ma i codici reali sono `major_nc`/`minor_nc` → MTTR Major/Minor degli audit finding **sempre a 0**. Corretto con mappa output→codici (contratto API invariato).
- **C/B**: L · Alto · **Stato: ✅ FATTO (2026-06-03)**

### P1-2 · `@transaction.atomic` sulle azioni multi-write + audit — ✅ FATTO (2026-06-03)
- **Problema**: `risk, tasks, assets, bia, incidents, documents, notifications` con atomic=0. Es. `risk.complete` (score+ALE+escalate+save), `assets.register_change` (cascata). Stato parziale → audit append-only incoerente.
- **Fatto** (priorità risk/incidents/assets, come da backlog): atomiche `risk.complete` (view), `risk.accept_risk`, `risk.escalate_red_risk`, `risk.delete_risk_assessment`, `incidents.close_incident`, `incidents.mark_notification_sent`, `assets.delete_asset`. Le notifiche email best-effort (rischio rosso) spostate su `transaction.on_commit` (partono solo a commit avvenuto, mai bloccano). `update_pdca_with_nis2_evidence` lasciata **volutamente non atomica** (l'evidenza deve persistere anche se l'avanzamento PDCA fallisce — best-effort documentato). 10 test di regressione nuovi (rollback verificato per ogni azione). Suite intera verde, coverage 70.01% (vedi NB).
- **NB coverage**: a HEAD pre-sessione la suite era a **69.49%**, già sotto il gate `--cov-fail-under=70` (debito preesistente = P2-1). Questo lavoro l'ha riportata a **70.01%**. Il grosso del gap resta da colmare in P2-1.
- **Resta fuori (follow-up)**: `bia.delete_process` (cascata ampia), `documents.approve/reject/add_version*`, `tasks.complete_run`/`compute_and_store_kpi_snapshot` — stesso pattern multi-write, non prioritari.
- **C/B**: M · Alto · **Stato: ✅ FATTO (2026-06-03)**

### P1-3 · Write-authorization granulare (SoD) dove `permission_classes=0` — ✅ FATTO (2026-06-03)
- **Problema**: default globale `IsAuthenticated` + RBAC solo in `get_queryset` (visibilità). In `risk, assets, plants, bia, pdca, governance, tasks, training` chi vede può anche modificare/cancellare → SoD debole.
- **Fatto**: creata una `RoleScopedPermission` per ciascuno degli 8 moduli (`<modulo>/permissions.py`), collegata a tutti i viewset, completando il pattern dei ~11 moduli già coperti dal lavoro "newfix F1". Auditor sempre read-only; config org-level (BU/framework/role-assignment/comitato/KPIDefinition) write solo super_admin/compliance_officer; dato operativo write ai ruoli competenti (control_owner incluso su asset/pdca/task). Lo scoping per-plant resta su `PlantScopedQuerysetMixin` (vale anche per update/delete via get_object). 11 test di autorizzazione + fixture dei test assets/governance aggiornate (usavano un utente senza ruolo → ora serve un `UserPlantAccess`). Suite 781 verde, coverage 71.98%.
- **NB**: object-level scope-aware non necessario: lo scope è già imposto dal queryset (un utente non può update/delete record fuori dal suo scope perché get_object non li trova). Il gap reale era solo il ruolo di scrittura.
- **C/B**: M · Alto · **Stato: ✅ FATTO (2026-06-03)**

### P1-5 · Legame `ControlInstance ↔ asset/processo` per restringere la cascata change
- **Problema**: oggi `register_change` flagga i controlli a livello di **plant** (manca un legame diretto controllo↔asset/processo). Troppo largo: un change su un asset rimette "da rivalutare" l'intera postura di conformità del plant.
- **Azione**: aggiungere il legame (M2M `ControlInstance.assets`/`processes` o tramite SoA/BIA) e flaggare solo i controlli realmente impattati.
- **C/B**: M · Medio · Stato: ⬜

### P1-4 · `ai_engine`: test sanitizer "no-PII-leak" + circuit breaker LLM — ✅ FATTO (2026-06-03)
- **Problema**: 8 test su orchestratore che spende su LLM; mancava test che garantisse nessun PII esca senza sanitize e un fallback robusto se LLM giù.
- **Fatto**: (1) test no-PII-leak che mockano il provider e verificano che il prompt inviato non contenga PII in chiaro (email/IP/CF/telefono/P.IVA/plant) + desanitize della risposta + `sanitize=True` di default; (2) `circuit_breaker.py` (cache Redis): dopo 3 fallimenti consecutivi apre il circuito 120s → `route()` salta il provider giù (fail-fast); (3) eccezione `LlmUnavailable` quando anche il fallback locale è giù → endpoint AI rispondono **503** invece di 500. 8 test nuovi (16 totali ai_engine). Suite 789 verde, coverage 72.56%.
- **Finding minore (rimandato)**: `Sanitizer` collide il token quando `name` e `code` dello stesso plant sono entrambi nel testo (desanitize ripristina solo l'ultimo). Non è un leak.
- **C/B**: M · Medio · **Stato: ✅ FATTO (2026-06-03)**

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
