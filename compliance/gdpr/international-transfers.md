# Trasferimenti internazionali — TIA (GDPR Cap. V, Art. 44-49)

> ⚠️ Bozza tecnica / Transfer Impact Assessment (Schrems II), **non parere legale**. Le
> scelte di provider/meccanismo e la verifica delle certificazioni spettano al **titolare**
> (self-hosted: cliente; SaaS: operatore). Campi `[DA COMPILARE/VERIFICARE]` da completare col DPO.

## 1. Quando avviene un trasferimento
La piattaforma effettua un trasferimento extra-UE **solo** quando un task AI è instradato a
un **provider cloud non UE** (es. Anthropic, OpenAI, Groq, Google, Mistral). Il routing è
configurabile per-task (`AiProviderConfig.task_routing`).

**Se tutti i task sono instradati su Ollama locale → nessun trasferimento** (il dato non
lascia l'infrastruttura del titolare). Questa è la mitigazione più forte ed è già disponibile.

| Funzione AI | Routing default | Trasferimento di default? |
|-------------|-----------------|----------------------------|
| `incident_classify` | locale (Ollama) | **No** |
| `rca_draft`, `gap_actions`, `cockpit_*`, `osint_*`, `assistant_*` | cloud | Sì (verso il provider configurato) |

## 2. Cosa viene trasferito
Prompt costruito dal task, **dopo** sanitizzazione:
- **Rimossi**: IP, email, codici fiscali, telefoni, P.IVA (Sanitizer); per OSINT
  `AnonymizationService`.
- **Tokenizzati**: nomi/codici dei siti.
- **Residuo**: testo libero che può contenere nomi di persona (mitigato da avviso UI "usa
  nomi di fantasia" + human-in-the-loop). Vedi [`audit-log-pii-assessment.md`](audit-log-pii-assessment.md)
  e l'inventario AI.

Categorie: dati di sicurezza/operativi; PII solo incidentale. **Nessuna categoria particolare
(Art. 9) inviata intenzionalmente.**

## 3. Meccanismo di trasferimento (da scegliere per provider)
Opzioni, in ordine di preferenza:

1. **Nessun trasferimento** — usare Ollama locale (o endpoint LLM self-hosted in UE). ✅ supportato.
2. **Endpoint EU-region** del provider dove disponibile (la piattaforma accetta `base_url`
   OpenAI-compatibile → puntabile a region UE). `[DA VERIFICARE per provider]`
3. **Adeguatezza — EU-US Data Privacy Framework (DPF)**: valido se il provider USA è
   **certificato DPF**. `[DA VERIFICARE: certificazione DPF del provider scelto]`
4. **Garanzie adeguate — SCC (2021)** + **questo TIA** (misure supplementari) se il provider
   non è coperto da adeguatezza. `[DA COMPILARE: SCC firmate nel DPA]`
5. Deroghe Art. 49 (consenso esplicito, ecc.): **sconsigliate** per uso sistematico.

## 4. Valutazione del rischio (Schrems II) + misure supplementari
Rischio principale: accesso da parte di autorità del paese terzo ai dati trasferiti.

**Misure supplementari già in essere (tecniche/organizzative):**
- **Minimizzazione drastica**: identificatori diretti rimossi prima dell'invio; siti tokenizzati.
- **Niente PII strutturata**: non si inviano anagrafiche, solo testo operativo sanitizzato.
- **Trasporto cifrato** (TLS) verso le API.
- **Opzione "zero trasferimento"** (locale) sempre disponibile come fallback.
- **Human-in-the-loop**: nessun output applicato automaticamente.

**Misure contrattuali da assicurare nel DPA col provider** `[DA COMPILARE]`:
- **No training** sui dati API (default per Anthropic/OpenAI API — confermare per iscritto).
- **Zero/limited data retention** lato provider dove offerto.
- SCC allegate; impegno a notificare richieste delle autorità; cifratura.

## 5. Provider — scheda (da completare per quello/i effettivamente usati)

| Provider | Paese | DPF certificato? | DPA firmato? | No-training? | Region EU? |
|----------|-------|------------------|--------------|--------------|------------|
| Anthropic | USA | `[VERIFICARE]` | `[ ]` | `[VERIFICARE]` | `[VERIFICARE]` |
| OpenAI | USA | `[VERIFICARE]` | `[ ]` | `[VERIFICARE]` | `[VERIFICARE]` |
| Groq / Google / Mistral | `[ ]` | `[VERIFICARE]` | `[ ]` | `[VERIFICARE]` | `[VERIFICARE]` |
| **Ollama (locale)** | UE/on-prem | n/a — **nessun trasferimento** | n/a | n/a | ✅ |

Questi provider sono **sub-responsabili** del trattamento → vanno in lista sub-processor
(`../data-flows.md`) e nel DPA verso il cliente (scenario SaaS).

## 6. Raccomandazioni operative
1. **Default consigliato per dati sensibili**: instradare i task con testo libero su **Ollama
   locale** (privacy-by-default, nessun trasferimento). Configurabile in `AiProviderConfig.task_routing`.
2. Se si usa il cloud: scegliere un provider **DPF-certificato** o firmare **SCC + DPA** con
   no-training e (se possibile) **endpoint EU**.
3. Documentare la scelta nel ROPA e nell'informativa; allegare il presente TIA.
4. Rivalutare il TIA a ogni cambio di provider o di quadro normativo (es. evoluzioni DPF).

## 7. Esito
Con (a) sanitizzazione + (b) opzione locale + (c) provider DPF/SCC + no-training, il rischio
residuo del trasferimento è **basso e gestito**. La via a rischio minimo (`Ollama locale`) è
sempre disponibile e raccomandata per i trattamenti più sensibili.
