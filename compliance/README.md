# Compliance Pack — GRC Webapp

> ⚠️ **DRAFT / work-in-progress.** Questi documenti sono un *fascicolo di conformità*
> tecnico-organizzativo, **non un parere legale**. I testi destinati a clienti,
> autorità o audit devono essere validati da un legale / DPO prima dell'uso.

Questo pacchetto rende verificabile la conformità della piattaforma ai principali
regolamenti UE applicabili e abilita la conformità di chi la distribuisce/ospita.
È versionato nel repo perché **evolve insieme al codice**: ogni misura tecnica
dichiarata qui ha (o deve avere) un riscontro nel sorgente.

## Modello "Common + Overlay" (multi-scenario)

La piattaforma può essere distribuita in tre modi; gli obblighi cambiano di
conseguenza. Invece di triplicare i documenti, usiamo **un nucleo comune + overlay**.

| Pacchetto | Scenario | Chi è titolare/operatore | Regolamenti che pesano di più |
|-----------|----------|--------------------------|-------------------------------|
| **Common** | sempre | Fornitore del software (tu) | privacy/security-by-design (GDPR 25/32), trasparenza AI (AI Act 50) |
| **Overlay A** | Self-hosted OSS (cliente ospita) | Cliente = **titolare** | GDPR (cliente), NIS2 (cliente). CRA: OSS non commerciale **esente** |
| **Overlay B** | SaaS gestito da te | Tu = **responsabile/operatore** (a volte titolare) | GDPR (DPA, ROPA, sub-processor), CRA, possibile NIS2 su di te |
| **Overlay C** | Self-hosted ma gestito da te | **Ibrido**: cliente titolare, tu operatore | GDPR (DPA per la gestione), parti di CRA |

Legenda owner usata nel register: **P** = Prodotto (dentro il software, sempre tuo) ·
**D** = Deployer/Titolare (cliente self-hosted) · **O** = Operatore (tu, in SaaS/managed).

## Regolamenti in scope

- **GDPR** (2016/679) + **DPIA** (Art. 35) — la piattaforma tratta dati personali
  (utenti, audit log pseudonimizzato, risultati phishing/training per dipendente,
  descrizioni incidenti, OSINT).
- **AI Act** (2024/1689) — feature AI di supporto decisionale con human-in-the-loop.
- **Data Act** (2023/2854) — portabilità/export dati, clausole eque (rilevante soprattutto in SaaS).
- **Cyber Resilience Act** (2024/2847) — prodotto con elementi digitali (rilevante se commerciale).
- **NIS2** (2022/2555) — i clienti sono in scope per natura del prodotto; tu se offri SaaS.

## Indice del pacchetto

| Doc | Contenuto | Stato |
|-----|-----------|-------|
| [`compliance-register.md`](compliance-register.md) | Mappa master: regolamento → obbligo → scenario → owner → stato → evidenza | 🟡 bozza |
| [`ai/ai-system-inventory.md`](ai/ai-system-inventory.md) | Inventario sistemi AI + classificazione AI Act + trasparenza | 🟡 bozza |
| [`gdpr/dpia.md`](gdpr/dpia.md) | DPIA (phishing/training, OSINT, AI cloud) | 🟡 bozza pre-compilata |
| [`gdpr/audit-log-pii-assessment.md`](gdpr/audit-log-pii-assessment.md) | Verifica PII nei payload audit | ✅ fatto |
| [`gdpr/retention-and-erasure.md`](gdpr/retention-and-erasure.md) | Retention + Art. 17 vs audit immutabile | 🟡 bozza |
| [`gdpr/ropa.md`](gdpr/ropa.md) | Registro dei trattamenti (Art. 30) | 🟡 bozza |
| [`gdpr/international-transfers.md`](gdpr/international-transfers.md) | TIA provider AI + leve (Ollama/EU region) | 🟡 bozza |
| [`../SECURITY.md`](../SECURITY.md) | Vulnerability disclosure coordinata (CRA Art. 13) — a root del repo | ✅ fatto |
| [`data-flows.md`](data-flows.md) | Diagramma flussi dati + sub-processor | 🟡 bozza |

## Punti di forza già nel prodotto (evidenze "Common")

Misure tecniche già implementate che fanno da evidenza di privacy/security-by-design:

- Audit trail **append-only/immutabile** (trigger DB) con verifica hash-chain — accountability (GDPR 5.2 / 30, ISO 27001 A.12.4).
- Email **pseudonimizzata** nell'audit, mai PII nei log di sistema (regola #11) — minimizzazione (Art. 25).
- `anonymize_user()` — supporto all'Art. 17.
- **RBAC least-privilege** + scoping per sito + esclusione auditor esterni dai dati di esposizione.
- **Sanitizer** + AnonymizationService + avviso "campi liberi → cloud" + opzione **LLM locale (Ollama)** — minimizzazione e *leva sui trasferimenti extra-UE* (AI Act/GDPR Cap. V).
- **Human-in-the-loop** su ogni output AI + `AiInteractionLog` (record-keeping AI Act).
- **FERNET (AES-256)** per i segreti (chiavi AI/SMTP/enricher), MIME-check upload, password policy.
- **CI**: `pip-audit` + `npm audit` (base SBOM/vulnerability management — CRA).

## Gap residui (sintesi)

**Documentali** — bozze redatte (DPIA, ROPA, retention, TIA, data-flows) + SECURITY.md e
audit-PII assessment completi. Restano i campi `[DA COMPILARE]` di competenza del **titolare**
(intestazione, basi giuridiche di dettaglio, periodi di conservazione, verifica certificazioni provider).

**Tecnici** ancora aperti:
1. Export/portabilità completi del dato cliente (Data Act).
2. Purge definitivo dei record soft-deleted dopo il periodo di retention.
3. Pubblicazione **SBOM** per release (CRA Annex I.2).

*(Chiusi nel corso del lavoro: verifica PII payload audit, label "AI-generated", avviso cloud-PII,
retention `AiInteractionLog`, esclusione external_auditor da OSINT.)*
