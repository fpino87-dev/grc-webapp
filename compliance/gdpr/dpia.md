# DPIA — Valutazione d'impatto sulla protezione dei dati (GDPR Art. 35)

> ⚠️ **DRAFT / template pre-compilato.** Non è un parere legale. La DPIA è di competenza
> del **titolare** (in self-hosted: il cliente; in SaaS: l'operatore). Questo documento la
> pre-compila con i trattamenti noti della piattaforma e le misure tecniche già in essere;
> i campi `[DA COMPILARE]` dipendono dal contesto del titolare e vanno completati con il DPO.

| Campo | Valore |
|-------|--------|
| Titolare del trattamento | `[DA COMPILARE]` |
| DPO / referente | `[DA COMPILARE]` |
| Data / versione | 2026-06-14 — v0 draft |
| Sistema | GRC Webapp (TISAX/NIS2/ISO 27001) |
| Esito sintetico | Rischio **medio**, **mitigabile** con le misure elencate; consultazione preventiva Garante non necessaria se le misure sono implementate |

## 1. È necessaria la DPIA? (Art. 35.3 + linee guida WP248)
Sì. Ricorrono almeno due criteri che, combinati, la rendono obbligatoria:
- **Monitoraggio sistematico di lavoratori**: simulazioni di phishing e completamento
  formazione tracciati per singolo dipendente (M15).
- **Trattamento su larga scala** di dati relativi al personale e ad attività di sicurezza.
- **Trasferimento verso paese terzo** (USA) se è attivo un provider AI cloud.
- **Uso di tecnologia innovativa** (AI generativa).

## 2. Descrizione sistematica dei trattamenti

| # | Trattamento | Categorie di dati | Interessati | Finalità | Base giuridica (proposta) |
|---|-------------|-------------------|-------------|----------|----------------------------|
| 1 | Gestione account/RBAC (`auth_grc`) | nome, email, ruolo, accessi | utenti interni | autenticazione, autorizzazione | esecuzione contratto / obbligo legale sicurezza |
| 2 | Audit trail (`core.audit`) | user_id, email **pseudonimizzata**, azioni | utenti interni | accountability, sicurezza | obbligo legale / legittimo interesse |
| 3 | Incidenti (M09) | descrizioni libere (possibili nomi) | interni/terzi citati | gestione incidenti NIS2 | obbligo legale (NIS2) |
| 4 | **Simulazioni phishing (M15)** | esito per dipendente (click/report), data | **dipendenti** | awareness sicurezza | legittimo interesse `[bilanciamento DA COMPILARE]` |
| 5 | **Formazione (M15)** | completamento, punteggio per dipendente | **dipendenti** | obbligo formazione sicurezza | obbligo legale / legittimo interesse |
| 6 | Governance ruoli (M00) | persona ↔ ruolo normativo, scadenze | interni | conformità (chi è responsabile) | obbligo legale |
| 7 | OSINT (trasversale) | domini, **breach/email aziendali** esposte | dipendenti (email aziendali) | monitoraggio esposizione esterna | legittimo interesse (sicurezza) |
| 8 | AI Engine (M20) | testo libero inviato al modello (possibili nomi) | interni/terzi citati | assistenza decisionale | legittimo interesse + HIL |
| 9 | Fornitori (M14) | referente, email, NDA | persone di contatto fornitori | gestione TPRM | esecuzione contratto / legittimo interesse |

Flussi e sub-responsabili dettagliati in `../data-flows.md` (da redigere).

## 3. Necessità e proporzionalità
- **Minimizzazione**: identificatori diretti non loggati nell'audit (vedi
  [`audit-log-pii-assessment.md`](audit-log-pii-assessment.md)); email pseudonimizzata; prosa
  libera troncata; AI con sanitizzazione + opzione locale.
- **Limitazione finalità**: dati di sicurezza usati per sicurezza/conformità, non per fini
  ulteriori. **Il monitoraggio phishing NON deve essere usato per provvedimenti disciplinari
  individuali** salvo policy esplicita e informata `[DA COMPILARE: policy + accordo sindacale]`.
- **Limitazione conservazione**: `[DA COMPILARE periodi]`; audit log permanente per obbligo
  legale (vedi `retention-and-erasure.md`).
- **Esattezza / diritti**: rettifica via UI; cancellazione via `anonymize_user()` (Art. 17,
  con bilanciamento per l'audit).

## 4. Rischi per i diritti e le libertà + misure

| Rischio | Probabilità | Gravità | Misure (in essere salvo nota) |
|---------|-------------|---------|--------------------------------|
| **Profilazione/sorveglianza dipendenti** (phishing/training) | Media | **Alta** | Finalità limitata ad awareness; **valutare aggregazione/anonimizzazione dei report**; accesso ristretto; trasparenza + `[consultazione RSU/comitato — DE/IT]`; divieto uso disciplinare automatico |
| **Trasferimento extra-UE** dati a provider AI USA | Media | Alta | **Opzione/forzatura LLM locale (Ollama)** → dato resta in UE; sanitizzazione; `[SCC/DPF + TIA DA COMPILARE]`; provider non addestrano su dati API |
| PII incidentale in testo libero al cloud (nomi) | Media | Media | Sanitizer (IP/email/CF/tel/P.IVA) + token siti; **avviso UI "usa nomi di fantasia"**; HIL; opzione locale |
| Accesso non autorizzato ai dati | Bassa | Alta | RBAC least-privilege + scoping per sito; MFA; JWT blacklist; FERNET AES-256 sui segreti; rate-limiting; **auditor esterni esclusi da OSINT/esposizione** |
| Alterazione/cancellazione evidenze | Bassa | Alta | Audit **append-only** (trigger DB) + verifica hash-chain |
| Data breach | Bassa | Alta | Misure Art. 32 + processo incidenti (M09) + notifica `[DA COMPILARE tempistiche GDPR 72h]` |
| Decisione automatizzata su persone (Art. 22) | Bassa | Alta | **Nessuna**: l'AI è solo di supporto, output sempre soggetto a human-in-the-loop |

## 5. Misure tecniche di sicurezza già implementate (Art. 32) — evidenza
Audit append-only + hash-chain · pseudonimizzazione email · `anonymize_user()` · RBAC +
scoping per sito · MFA · password policy 12+ · JWT 30m/blacklist · rate-limiting · FERNET
AES-256 (segreti) · MIME-check upload · Sanitizer/Anonymizer AI + opzione locale · HIL +
`AiInteractionLog` · CI `pip-audit`/`npm audit`.

## 6. Esito e azioni residue
**Esito**: rischio residuo **accettabile** una volta completate le azioni `[DA COMPILARE]`:
1. Bilanciamento del legittimo interesse per phishing/training + (dove richiesto) consultazione RSU.
2. Meccanismo di trasferimento per l'uso AI cloud (o policy "solo locale").
3. Definizione periodi di conservazione.
4. Informativa al personale (trasparenza sul monitoraggio).
5. Valutare aggregazione/pseudonimizzazione dei report phishing per ridurre l'impatto.

## 7. Pareri
- Parere DPO: `[DA COMPILARE]`
- Eventuale consultazione preventiva Garante (Art. 36): **non necessaria** se le misure sono attuate; rivalutare se il rischio resta alto.
- Approvazione titolare: `[DA COMPILARE — data/firma]`
