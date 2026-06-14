# Flussi dei dati e sub-responsabili

> ⚠️ Bozza tecnica, non parere legale. La lista sub-responsabili dipende dalla
> **configurazione del deployment** (provider AI, SMTP, enricher OSINT, monitoring abilitati).
> Completare i campi `[DA COMPILARE/VERIFICARE]` in base allo scenario.

## 1. Architettura e flussi

```
                            ┌─────────────────────────────────────────┐
                            │              PERIMETRO UE                │
                            │        (infrastruttura del titolare)     │
  Browser utente            │                                          │
  (HTTPS + JWT)  ──────────►│  Frontend React ──► Backend Django/DRF   │
                            │                         │                │
                            │        ┌────────────────┼───────────┐    │
                            │        ▼                ▼           ▼    │
                            │   PostgreSQL          Redis      Celery  │
                            │   (dati persistenti) (cache/broker)      │
                            │        │                                 │
                            │        ▼                                 │
                            │   Backup (BACKUP_DIR, cifrabili)         │
                            │                                          │
                            │   LLM locale (Ollama)  ◄── opzione       │
                            └───────────────┬──────────────────────────┘
                                            │  chiamate esterne (TLS)
              ┌─────────────────────────────┼───────────────────────────────┐
              ▼                ▼             ▼              ▼                ▼
        Provider AI cloud   SMTP/email   Enricher OSINT   Sentry        (Hosting/cloud
        (se non locale)     (notifiche)  (VT/HIBP/...)    (se attivo)    in scenario SaaS)
        ⚠️ TRASFERIMENTO    email dest.  domini/IP org    telemetria     infrastruttura
        se non-UE                        (HIBP→email)     mascherata
```

## 2. Flussi che coinvolgono dati personali

| Flusso | Dati | Direzione | Note privacy |
|--------|------|-----------|--------------|
| Browser ↔ Backend | credenziali, dati operativi | bidirezionale | HTTPS, JWT 30m + blacklist |
| Backend ↔ PostgreSQL | tutti i dati persistenti | interno UE | RBAC a livello applicativo |
| Backend ↔ Redis | cache, throttle, broker Celery | interno UE | nessun dato persistente sensibile |
| Backend → Backup | dump DB | interno UE | retention 30gg, cifratura disponibile |
| Backend → **Provider AI cloud** | prompt **sanitizzato** | uscita | ⚠️ **trasferimento** se non-UE → [TIA](gdpr/international-transfers.md); evitabile con Ollama locale |
| Backend → SMTP | email destinatari + contenuto notifica | uscita | dipende dal provider SMTP configurato |
| Backend → Enricher OSINT | domini/IP/hash dell'organizzazione | uscita | HIBP restituisce email aziendali esposte (breach) |
| Backend → Sentry (se attivo) | telemetria errori | uscita | `sendDefaultPii=false`, `maskAllText=true`, header Authorization rimosso |

## 3. Lista sub-responsabili (Art. 28)

> Compilare in base al deployment effettivo. In **self-hosted con Ollama locale, SMTP interno,
> OSINT/Sentry disabilitati** la lista può essere **vuota** (nessun terzo tratta dati personali).

| Sub-responsabile | Servizio | Dati trattati | Quando | DPA / garanzie |
|------------------|----------|---------------|--------|----------------|
| `[Provider AI]` (Anthropic/OpenAI/…) | inferenza LLM | prompt sanitizzato (PII incidentale) | solo task AI su **cloud** | `[DPA + SCC/DPF — DA VERIFICARE]` — vedi TIA |
| `[Provider SMTP/email]` | invio email | email destinatari, contenuto notifiche | invio notifiche/questionari | `[DPA — DA COMPILARE]` |
| Enricher OSINT (VirusTotal, **HIBP**, AbuseIPDB, OTX, Google Safe Browsing, abuse.ch) | threat intelligence | domini/IP org; HIBP → email esposte | se OSINT attivo + chiavi configurate | `[DA VERIFICARE per ciascun servizio]` |
| `[Sentry o equivalente]` | error monitoring | telemetria mascherata | se `SENTRY_DSN` valorizzato | `[DPA — DA COMPILARE]`; PII già minimizzata |
| `[Hosting/cloud provider]` | infrastruttura | tutti (a riposo) | **scenario SaaS** | `[DPA + ubicazione UE — DA COMPILARE]` |
| KnowBe4 | phishing/training | dati dipendenti | se integrazione M15 attiva | `[DA VERIFICARE]` |

## 4. Note
- I servizi esterni passivi che **non ricevono dati personali** (es. crt.sh / RDAP / DNSBL su
  domini pubblici dell'org) non sono sub-responsabili di dati personali.
- Ogni nuovo provider/integrazione va aggiunto qui, nel [ROPA](gdpr/ropa.md) e (in SaaS) nel DPA col cliente.
- La leva **"tutto locale"** (Ollama + SMTP interno + niente Sentry/OSINT esterni) minimizza la
  catena di sub-responsabili — utile per i clienti più sensibili.
