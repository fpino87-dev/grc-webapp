# ROPA — Registro dei trattamenti (GDPR Art. 30)

> ⚠️ Bozza/template, non parere legale. Il ROPA è **del titolare** (Art. 30.1); in scenario
> SaaS l'operatore tiene anche un ROPA del responsabile (Art. 30.2). I campi `[DA COMPILARE]`
> dipendono dal contesto del titolare. Periodi di conservazione: vedi
> [`retention-and-erasure.md`](retention-and-erasure.md). Trasferimenti: vedi
> [`international-transfers.md`](international-transfers.md). Misure di sicurezza: vedi `../README.md` §"Punti di forza".

## Intestazione

| Campo | Valore |
|-------|--------|
| Titolare del trattamento | `[DA COMPILARE]` |
| Rappresentante / DPO | `[DA COMPILARE]` |
| Responsabili esterni (sub-processor) | vedi [`../data-flows.md`](../data-flows.md) |
| Data / versione | 2026-06-14 — v0 draft |

## Registro (Art. 30.1)

Misura di sicurezza comune a tutti (Art. 32, sintesi): RBAC con scoping per sito, MFA,
password policy, JWT con rotazione/blacklist, rate-limiting, **FERNET AES-256** sui segreti,
MIME-check upload, **audit trail append-only con hash-chain**, TLS in transito, backup cifrabili.

| # | Trattamento | Finalità | Categorie interessati | Categorie dati | Destinatari | Trasferimenti extra-UE | Conservazione |
|---|-------------|----------|------------------------|----------------|-------------|------------------------|----------------|
| 1 | **Gestione account / RBAC** | autenticazione, autorizzazione | utenti interni | nome, email, username, ruolo, accessi per sito | personale IT/sicurezza interno | No | finché attivo + `[DA COMPILARE]` post-cessazione; poi `anonymize_user()` |
| 2 | **Audit trail** | accountability, sicurezza, conformità | utenti interni | user_id, **email pseudonimizzata**, azioni, timestamp | super_admin / compliance / auditor | No | **Permanente** (immutabile, pseudonimizzato) |
| 3 | **Gestione incidenti (M09)** | gestione incidenti, obblighi NIS2 | interni / terzi citati nelle descrizioni | descrizioni incidenti (PII incidentale), asset coinvolti | governance, eventuale CSIRT | No (salvo notifica autorità) | `[DA COMPILARE]` (pluriennale per compliance) |
| 4 | **Simulazioni phishing (M15)** | awareness sicurezza | **dipendenti** | esito per dipendente (click/report), data | governance formazione + auditor interno | No | `[DA COMPILARE]`; valutare aggregazione/anonimizzazione |
| 5 | **Formazione (M15)** | obbligo formazione sicurezza | **dipendenti** | corso, completamento, punteggio | governance formazione + auditor interno | (KnowBe4 se integrato → `[DA VERIFICARE]`) | `[DA COMPILARE]` |
| 6 | **Governance ruoli (M00)** | conformità (chi è responsabile) | interni | persona ↔ ruolo normativo, scadenze | governance, auditor | No | durata incarico + storico |
| 7 | **OSINT (esposizione esterna)** | monitoraggio superficie d'attacco | dipendenti (email aziendali in breach) | domini, certificati, **breach/email esposte** | governance + auditor **interno** (no external) | enricher esterni (VT, HIBP, ecc.) → `[DA VERIFICARE]` | scan tiered (`cleanup_old_scans`) |
| 8 | **AI Engine (M20)** | assistenza decisionale (HIL) | interni / terzi citati | prompt sanitizzato (PII incidentale), output | utente richiedente; **provider AI** (se cloud) | **Sì se provider cloud** → vedi TIA; leva: Ollama locale | log interazioni **365 giorni** |
| 9 | **Fornitori (M14)** | gestione TPRM | persone di contatto fornitori | nome referente, email, NDA, questionari | governance acquisti/sicurezza | No (salvo invio email questionari) | durata rapporto + `[DA COMPILARE]` |

## Basi giuridiche (sintesi — dettaglio in DPIA)
- Esecuzione contratto / obbligo legale: 1, 3, 5, 6, 9.
- Legittimo interesse (sicurezza), con bilanciamento: 2, 4, 7, 8.
- **Monitoraggio lavoratori (4, 5)**: richiede bilanciamento documentato + trasparenza +
  eventuale consultazione RSU/comitato — vedi [`dpia.md`](dpia.md).

## Note
- Le categorie particolari (Art. 9) non sono trattate intenzionalmente.
- Nessuna decisione automatizzata con effetti giuridici (Art. 22): l'AI è solo di supporto (HIL).
- Aggiornare il ROPA a ogni nuovo trattamento, integrazione (es. nuovo enricher/provider) o cambio finalità.
