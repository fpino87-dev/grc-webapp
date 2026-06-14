# Inventario sistemi AI + classificazione AI Act

> ⚠️ Bozza tecnica, non parere legale. La classificazione finale va confermata da un legale.

## 1. Ruolo nella catena AI Act

La piattaforma **non addestra** modelli e **non è provider di GPAI**: integra modelli
di terzi (Anthropic Claude, OpenAI GPT, ecc., oppure Ollama locale) come **deployer /
integratore a valle**. Gli obblighi da *provider GPAI* ricadono sui fornitori dei modelli.
Obblighi del deployer rilevanti: **trasparenza (Art. 50)**, **supervisione umana (Art. 14)**,
**record-keeping (Art. 12)**, AI literacy (Art. 4).

## 2. Inventario delle funzioni AI

| Funzione | Modulo | Scopo | Routing default | Dati inviati al modello | Anonimizzazione | Supervisione umana |
|----------|--------|-------|-----------------|--------------------------|-----------------|--------------------|
| `incident_classify` | M09 | Suggerisce categoria ENISA/severità | **locale (Ollama)** | titolo+descrizione incidente | Sanitizer + token sito | HIL (confirm/ignore) |
| `rca_draft` | M09 | Bozza analisi causa radice | cloud | descrizione incidente, asset | Sanitizer + token sito | HIL |
| `gap_actions` | M03 | Azioni correttive per controllo gap | cloud | note controllo, sito (tokenizzato) | Sanitizer + token sito | HIL |
| `control_explain` | M03 | Spiega un controllo normativo | cloud | testo normativo **pubblico** | n/d (no PII) | HIL |
| `cpv_suggestion` | M14 | Suggerisce codici CPV fornitura | cloud | descrizione fornitura | sanitizzazione manuale | HIL |
| `osint_*` | OSINT | Analisi attack surface / report | cloud | dati esposizione (domini, score) | **AnonymizationService** + anti-prompt-injection | HIL |
| `assistant_explain` | M20 | Spiega un gap | cloud | dati del gap | Sanitizer + token sito | HIL |
| `cockpit_explain` / `cockpit_assistant` | M21 | Spiega insight / Copilot | cloud | params insight / domanda utente | Sanitizer + token sito; grounded sugli insight reali | HIL |

Routing configurabile per-task (`AiProviderConfig.task_routing`): un deployer può
spostare **qualsiasi** task su Ollama locale → nessun dato lascia l'infrastruttura.

## 3. Classificazione del rischio (Art. 6 / Annex III)

**Esito preliminare: rischio limitato (non high-risk).** Motivazione:

- Tutte le funzioni sono **supporto decisionale con human-in-the-loop**: l'output è
  *proposto*, mai applicato automaticamente; un umano conferma/modifica/ignora.
- **Nessuna decisione automatizzata su persone** ai sensi dell'Art. 22 GDPR.
- **Annex III.4 (occupazione / gestione lavoratori)**: le funzioni AI **non valutano né
  monitorano i lavoratori**. Il monitoraggio phishing/training è registrato dal sistema
  *senza* intervento dell'AI (nessuna classificazione AI del dipendente). → fuori da Annex III.4.
- Nessun'altra voce Annex III applicabile (no biometria, no credit scoring, no infrastrutture
  critiche gestite dall'AI, ecc.).

⚠️ **Da confermare** se in futuro una funzione AI dovesse *valutare automaticamente*
persone (es. scoring fornitori/dipendenti via AI): in quel caso rivalutare verso high-risk.

## 4. Obblighi di trasparenza (Art. 50) — stato

| Misura | Stato | Note |
|--------|-------|------|
| L'utente sa che interagisce con AI | ✅ | Banner "Raccomandazione AI" + badge provider/modello |
| Avviso sui dati liberi verso cloud | ✅ | `ai.cloud_pii_notice` (banner + Copilot cockpit), i18n ×5 |
| **Output marcato come "generato da AI"** | ✅ | Label `ai.generated_label` su banner raccomandazioni + OSINT AI (anche nel testo esportato/copiato); cockpit già con `cockpit.ai.disclaimer` |
| Tracciabilità interazioni | ✅ | `AiInteractionLog`: input_hash SHA-256 (mai il testo), output, confermatore |

## 5. Misure di minimizzazione (privacy + transfer)

- **Sanitizer** (regex): rimuove IP, email, CF, telefono, P.IVA dal prompt.
- **Tokenizzazione** nomi/codici sito (`plant_ids`).
- **AnonymizationService** per OSINT + neutralizzazione prompt-injection.
- **Limite noto**: la sanitizzazione regex **non cattura i nomi di persona** nel testo
  libero → mitigato da (a) avviso UI "usa nomi di fantasia con il cloud", (b) human-in-the-loop,
  (c) possibilità di routing locale. *Opzione futura: NER (es. Presidio) se serve copertura piena.*

## 6. Trasferimenti internazionali (collega a `gdpr/international-transfers.md`)

I provider cloud di default (Anthropic/OpenAI) sono **fuori UE** → ogni chiamata cloud è un
trasferimento (GDPR Cap. V). Mitigazioni/leve:
1. **Default/forzatura Ollama locale** per i task con testo libero → dato resta in UE.
2. Endpoint EU-region del provider dove disponibile.
3. SCC / EU-US Data Privacy Framework + TIA per l'uso cloud residuo.
4. I provider API (Anthropic/OpenAI) **non addestrano** sui dati API per default → da confermare nel DPA.
