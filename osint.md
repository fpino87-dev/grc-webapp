# OSINT Module — Guida di Sviluppo per Claude Code

> Documento di riferimento completo. Seguire i passi in ordine.
> Non procedere al passo successivo senza aver completato e testato il precedente.

---

## STATO AVANZAMENTO (aggiornato ad ogni step)

**Decisioni operative già prese (24-04-2026):**
- Single-tenant: rimosso `tenant_id` da tutte le tabelle OSINT (la webapp è single-tenant; `osint_settings` è singleton come `SupplierEvaluationConfig`)
- Feature flag: env `OSINT_ENABLED` + permission `osint.access_module` per gate modulo "a pagamento"
- AI settings: **riusato il menu AI Engine M20** (`AiProviderConfig`). Aggiunti 3 nuovi `TASK_TYPES`: `osint_attack_surface`, `osint_suppliers_nis2`, `osint_board_report`. Nessuna config AI duplicata in osint_settings
- API keys enricher (VT/AbuseIPDB/HIBP) in `osint_settings` cifrate con `EncryptedCharField` (già disponibile)
- Campi prerequisito mancanti aggiunti a moduli esistenti come campi opzionali (non breaking): `Plant.domain`, `Plant.additional_domains`, `Supplier.website`, `AssetSW.vendor_url`
- Anonymizer: dedicato in `apps/osint/anonymizer.py` (mapping diverso da sanitizer M20)
- i18n: 5 lingue IT/EN/FR/PL/TR per ogni nuova chiave

**Avanzamento step:**
- [x] Step 0 — Prerequisiti campi dominio (Plant/Supplier/AssetSW) — COMPLETATO 2026-04-24
- [x] Step 1 — App `osint`: modelli + migrazioni + admin — COMPLETATO 2026-04-24
- [x] Step 2 — Aggregator service — COMPLETATO 2026-04-24
- [ ] Step 3 — Enrichment engine
- [ ] Step 4 — Score engine
- [ ] Step 5 — Alert engine
- [ ] Step 6 — Scheduler Celery
- [ ] Step 7 — AnonymizationService
- [ ] Step 8 — API REST + integrazione AI Engine
- [ ] Step 9 — Dashboard frontend
- [ ] Step 10 — Test integrazione finale

**Per riprendere:** leggere questo file, vedere ultima checkbox non spuntata, seguire le note di ripresa qui sotto.

**Note di ripresa (ultimo stato — Milestone 1 / Step 0+1+2 completi):**
- Migrazioni applicate: `plants.0007`, `suppliers.0011`, `assets.0006`, `osint.0001_initial`.
- App `apps.osint` registrata in `backend/core/settings/base.py`. Modelli: `OsintEntity`, `OsintSubdomain`, `OsintScan` (con SSL/DNS/WHOIS/reputation/breach/score), `OsintAlert` (link soft via UUIDField a Incidents/Tasks), `OsintSettings` singleton con API keys cifrate (`EncryptedCharField`).
- Aggregator: `apps.osint.services.aggregate_entities()` idempotente — ricostruisce da Plants/Suppliers/AssetIT/AssetSW. `AssetOT` non ha campi rete → placeholder pronto per estensione futura.
- Test: 15 casi in `apps/osint/tests/test_services.py` — tutti PASS. 108 test plants/suppliers/assets invariati PASS.
- Supplier.website e AssetSW.vendor_url sono esposti via API/serializer ma il form frontend relativo NON è stato esteso con UI dedicata — gestione rimandata alla dashboard OSINT stessa.

**Prossimo step (per riprendere):** Step 3 — Enrichment engine. Costruire sotto `apps/osint/enrichers/` un modulo per ciascuna sorgente (`ssl.py` via crt.sh + TLS diretto, `dns.py` via dnspython, `whois_enr.py`, `virustotal.py`, `abuseipdb.py`, `otx.py`, `gsb.py`, `hibp.py`). Un orchestratore `enrichers/run.py` chiama tutti gli enricher, gestisce rate limit e salva in `OsintScan`. Dipendenze da aggiungere a `backend/requirements.txt`: `dnspython`, `python-whois`, `cryptography` (già presente per FERNET), `requests` (già presente). Rate limit: 15s tra richieste crt.sh/VT; 5s tra AbuseIPDB/OTX.

---

## CONTESTO GENERALE

Stiamo aggiungendo un modulo OSINT a una webapp GRC esistente.
Il modulo è **standalone** — ha la propria dashboard, non appare nella dashboard principale.
È un modulo **a pagamento** — trattarlo come feature premium.

Il modulo:
- Legge dati dagli altri moduli esistenti (read-only)
- Fa enrichment passivo via API esterne gratuite
- Calcola un OSINT Risk Score per ogni entità monitorata
- Genera alert che si collegano ai moduli Incidenti e Task esistenti
- Offre analisi AI tramite Claude API con anonimizzazione dei dati sensibili

---

## PASSO 0 — MODIFICA MODULO SITI (prerequisito)

**Obiettivo:** aggiungere il campo "Domini aggiuntivi / Plant" al modulo Siti esistente.

**Cosa fare:**
- Aggiungere al modello dati del modulo Siti un campo `additional_domains`
- Tipo: array di stringhe (domini multipli)
- Label UI: "Domini aggiuntivi / Plant"
- Placeholder: "es. plant-milano.azienda.it, sede-roma.azienda.it"
- Campo opzionale, non obbligatorio
- Questi domini vengono letti dal modulo OSINT esattamente come il dominio principale

**Test:** verificare che il campo si salvi e sia leggibile via API/query dal modulo OSINT.

---

## PASSO 1 — STRUTTURA DATI E MODELLO

**Obiettivo:** creare il modello dati del modulo OSINT nel database esistente.

### Tabelle da creare:

```
osint_entities
──────────────────────────────────────────────────
id                  UUID primary key
tenant_id           FK → tenant
entity_type         ENUM('my_domain', 'supplier', 'asset')
source_module       ENUM('sites', 'suppliers', 'assets_it',
                         'assets_ot', 'assets_software')
source_id           UUID → FK all'entità di origine
domain              VARCHAR(255)  — dominio principale
display_name        VARCHAR(255)  — nome leggibile (es. nome fornitore)
is_nis2_critical    BOOLEAN default false
is_active           BOOLEAN default true  — monitoraggio attivo/sospeso
scan_frequency      ENUM('weekly', 'monthly') default 'weekly'
created_at          TIMESTAMP
updated_at          TIMESTAMP

osint_subdomains
──────────────────────────────────────────────────
id                  UUID primary key
entity_id           FK → osint_entities
subdomain           VARCHAR(255)
status              ENUM('pending', 'included', 'ignored')
first_seen          TIMESTAMP
last_seen           TIMESTAMP

osint_scans
──────────────────────────────────────────────────
id                  UUID primary key
entity_id           FK → osint_entities
scan_date           TIMESTAMP
status              ENUM('running', 'completed', 'failed')

  — Risultati SSL
  ssl_valid           BOOLEAN
  ssl_expiry_date     DATE
  ssl_days_remaining  INTEGER
  ssl_issuer          VARCHAR(255)
  ssl_wildcard        BOOLEAN

  — Risultati DNS
  spf_present         BOOLEAN
  spf_policy          VARCHAR(50)   — 'pass','softfail','fail','+all'
  dmarc_present       BOOLEAN
  dmarc_policy        VARCHAR(20)   — 'none','quarantine','reject'
  mx_present          BOOLEAN
  dnssec_enabled      BOOLEAN

  — WHOIS
  domain_expiry_date  DATE
  domain_registrar    VARCHAR(255)
  whois_privacy       BOOLEAN
  registrar_country   VARCHAR(10)

  — Reputazione
  vt_malicious        INTEGER      — n. engine che segnalano malicious
  vt_suspicious       INTEGER
  abuseipdb_score     INTEGER      — 0-100
  abuseipdb_reports   INTEGER
  otx_pulses          INTEGER      — n. pulse AlienVault OTX
  gsb_status          VARCHAR(20)  — 'safe','phishing','malware','unwanted'
  in_blacklist        BOOLEAN
  blacklist_sources   TEXT[]

  — Breach (opzionale HIBP)
  hibp_breaches       INTEGER
  hibp_latest_breach  DATE
  hibp_data_types     TEXT[]

  — Score calcolato
  score_ssl           INTEGER      — 0-100
  score_dns           INTEGER
  score_reputation    INTEGER
  score_grc_context   INTEGER      — solo miei domini
  score_total         INTEGER      — aggregato pesato

osint_alerts
──────────────────────────────────────────────────
id                  UUID primary key
entity_id           FK → osint_entities
scan_id             FK → osint_scans
alert_type          VARCHAR(50)   — 'ssl_expiry','blacklist',
                                    'dmarc_missing','score_critical',
                                    'new_subdomain','breach_found'
severity            ENUM('critical','warning','info')
description         TEXT
status              ENUM('new','acknowledged','resolved')
linked_incident_id  UUID nullable  — FK modulo incidenti
linked_task_id      UUID nullable  — FK modulo task
created_at          TIMESTAMP
resolved_at         TIMESTAMP nullable

osint_settings
──────────────────────────────────────────────────
id                  UUID primary key
tenant_id           FK → tenant (unique)
score_threshold_critical    INTEGER default 70
score_threshold_warning     INTEGER default 50
freq_my_domains             ENUM('weekly','monthly') default 'weekly'
freq_suppliers_critical     ENUM('weekly','monthly') default 'weekly'
freq_suppliers_other        ENUM('weekly','monthly') default 'monthly'
subdomain_auto_include      ENUM('yes','no','ask') default 'ask'
anonymization_enabled       BOOLEAN default true
hibp_api_key                VARCHAR(255) nullable  — cifrato
virustotal_api_key          VARCHAR(255) nullable  — cifrato
abuseipdb_api_key           VARCHAR(255) nullable  — cifrato
```

**Test:** migrazioni applicate, relazioni verificate, nessun conflitto con tabelle esistenti.

---

## PASSO 2 — AGGREGATORE ENTITÀ

**Obiettivo:** costruire il servizio che legge dagli altri moduli e popola `osint_entities`.

### Sorgenti da leggere:

```
Modulo Siti
  → domain (campo esistente)
  → additional_domains[] (nuovo campo aggiunto al Passo 0)
  → entity_type = 'my_domain'
  → source_module = 'sites'

Modulo Fornitori
  → domain del fornitore
  → is_nis2_critical dal campo criticità NIS2 esistente
  → entity_type = 'supplier'
  → source_module = 'suppliers'

Modulo Asset IT/OT
  → IP pubblici e hostname
  → entity_type = 'asset'
  → source_module = 'assets_it' | 'assets_ot'

Modulo Asset Software
  → vendor_url (estrarre il dominio dalla URL)
  → entity_type = 'supplier'
  → source_module = 'assets_software'
```

### Logica di sincronizzazione:

- Gira ad ogni scan e ogni volta che si apre la dashboard OSINT
- Se entità esiste già (stesso source_id + source_module) → aggiorna, non duplicare
- Se entità viene cancellata dal modulo di origine → `is_active = false` (non cancellare, preserva storico)
- Deduplicazione per dominio: se stesso dominio arriva da due sorgenti, crea un'entità per sorgente ma segnala il duplicato in UI

**Test:** aggiungere un sito, un fornitore, un asset e verificare che compaiano in `osint_entities`.

---

## PASSO 3 — ENRICHMENT ENGINE

**Obiettivo:** costruire il motore che chiama le API esterne e salva i risultati in `osint_scans`.

### Architettura consigliata:

```
OsintScanJob (job schedulato)
  → legge tutte le osint_entities attive
  → rispetta frequenza configurata (weekly/monthly)
  → per ogni entità: chiama OsintEnricher
  → salva risultati in osint_scans
  → calcola score (Passo 4)
  → triggera AlertEngine (Passo 5)
```

### Moduli enricher da implementare (uno per API):

**[3.1] SSL Enricher → crt.sh**
```
Endpoint: https://crt.sh/?q=%.{domain}&output=json
Rate limit: 5 req/min → implementare throttling con delay 15s tra richieste
Raccoglie:
  - Lista certificati emessi per il dominio e sottodomini
  - Data not_before e not_after del cert più recente
  - Issuer
  - Wildcard (name_value inizia con "*.")
  - Sottodomini unici trovati nei name_value

Nota: usare anche endpoint diretto SSL:
  https://crt.sh/?q={domain}&output=json
  Per il cert attivo: fare anche una connessione TLS diretta
  al dominio per leggere il cert in uso (non solo i log CT)
```

**[3.2] DNS Enricher → lookup nativo**
```
Nessuna API esterna — usare il resolver DNS del sistema o
libreria DNS del tuo stack (es. dns package in Node, dnspython in Python)

Raccogliere:
  SPF:    TXT record → cercare "v=spf1"
          Classificare: present/absent, policy (+all = misconfigured)
  DMARC:  TXT record su _dmarc.{domain}
          Classificare: absent / p=none / p=quarantine / p=reject
  MX:     MX records presenti/assenti
  DNSSEC: verificare presenza RRSIG records
```

**[3.3] WHOIS Enricher**
```
Usare libreria WHOIS del tuo stack
Raccogliere:
  - expiration_date → domain_expiry_date
  - registrar name
  - privacy shield: se registrant è un servizio privacy
    (es. "Domains By Proxy", "WhoisGuard", "Privacy service")
  - registrar country (dal campo registrar IANA)

Gestire gracefully i domini che bloccano WHOIS
```

**[3.4] VirusTotal Enricher**
```
API key: da osint_settings.virustotal_api_key
Endpoint: GET https://www.virustotal.com/api/v3/domains/{domain}
Headers: x-apikey: {key}
Free tier: 4 req/min, 500 req/day → rispettare con throttling

Raccogliere da response.data.attributes.last_analysis_stats:
  malicious  → vt_malicious
  suspicious → vt_suspicious

Se no API key configurata: saltare silenziosamente,
  score reputazione calcolato senza questo dato
```

**[3.5] AbuseIPDB Enricher**
```
API key: da osint_settings.abuseipdb_api_key (gratuita)
Endpoint: GET https://api.abuseipdb.com/api/v2/check
          ?ipAddress={ip}&maxAgeInDays=90
Headers: Key: {api_key}, Accept: application/json

Usare solo se l'entità ha un IP associato (asset IT/OT)
Per domini: risolvere prima il dominio in IP, poi controllare

Raccogliere:
  data.abuseConfidenceScore → abuseipdb_score
  data.totalReports         → abuseipdb_reports
```

**[3.6] AlienVault OTX Enricher**
```
Nessuna API key necessaria per query base
Endpoint: GET https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general
Headers: X-OTX-API-KEY opzionale (aumenta quota se presente)

Raccogliere:
  pulse_info.count → otx_pulses
  (> 0 pulse = dominio presente in threat intelligence)
```

**[3.7] Google Safe Browsing Enricher**
```
API key: Google Cloud Console (gratuita)
Endpoint: POST https://safebrowsing.googleapis.com/v4/threatMatches:find
          ?key={GOOGLE_API_KEY}
Body:
{
  "client": {"clientId": "your-grc-app", "clientVersion": "1.0"},
  "threatInfo": {
    "threatTypes": ["MALWARE","SOCIAL_ENGINEERING","UNWANTED_SOFTWARE"],
    "platformTypes": ["ANY_PLATFORM"],
    "threatEntryTypes": ["URL"],
    "threatEntries": [{"url": "https://{domain}"}]
  }
}

Se matches vuoto → gsb_status = 'safe'
Se matches presente → gsb_status = tipo minaccia trovata
```

**[3.8] HIBP Enricher (opzionale — solo miei domini)**
```
API key: da osint_settings.hibp_api_key (a pagamento, opzionale)
Endpoint: GET https://haveibeenpwned.com/api/v3/breacheddomain/{domain}
Headers: hibp-api-key: {key}

Prerequisito: dominio deve essere verificato su HIBP
Usare SOLO per entity_type = 'my_domain'
MAI usare per domini fornitori (non abbiamo autorizzazione)

Raccogliere:
  keys().length → hibp_breaches (n. account coinvolti)
  trovare la breach più recente → hibp_latest_breach
  aggregare i DataClasses → hibp_data_types
```

### Gestione errori enricher:

- Ogni enricher è indipendente — se uno fallisce, gli altri continuano
- Salvare comunque il scan con i dati disponibili
- Loggare l'errore per debug
- Scan status = 'completed' anche con errori parziali (non 'failed')
- 'failed' solo se TUTTI gli enricher falliscono

**Test:** eseguire manualmente un scan su un dominio di test, verificare che tutti i campi di `osint_scans` si popolino correttamente.

---

## PASSO 4 — SCORE ENGINE

**Obiettivo:** calcolare i 4 score dimensionali e lo score aggregato.

### Algoritmo di calcolo:

```
SCORE SSL (peso 25%)
────────────────────────────────────
if !ssl_valid OR ssl_days_remaining == null  → 100
if ssl_days_remaining <= 0                   → 100
if ssl_days_remaining <= 14                  →  90
if ssl_days_remaining <= 30                  →  70
if ssl_days_remaining <= 60                  →  40
if ssl_days_remaining <= 90                  →  20
else                                         →   0

SCORE DNS (peso 25%)
────────────────────────────────────
base = 0
if !spf_present                              → base += 40
if spf_policy == '+all'                      → base += 20  (misconfigured)
if !dmarc_present                            → base += 30
if dmarc_present AND dmarc_policy == 'none'  → base += 15  (solo monitoring)
if !mx_present                               → base += 10
score_dns = MIN(base, 100)

SCORE REPUTATION (peso 30%)
────────────────────────────────────
base = 0
if gsb_status != 'safe'                      → base += 100  (esce subito)
if in_blacklist                              → base += 60
if vt_malicious > 5                          → base += 40
if vt_malicious > 0                          → base += 20
if abuseipdb_score > 50                      → base += 30
if abuseipdb_score > 20                      → base += 15
if otx_pulses > 5                            → base += 20
if otx_pulses > 0                            → base += 10
score_reputation = MIN(base, 100)

SCORE GRC CONTEXT (peso 20%) — solo entity_type = 'my_domain'
────────────────────────────────────
(Per fornitori questo score = 0, il peso va redistribuito)

base = 0
if is_nis2_critical                          → base += 20
count open_risks collegati all'entità:
  if open_risks >= 3                         → base += 40
  if open_risks >= 1                         → base += 20
count gap_controls (controlli non compliant):
  if gap_controls >= 5                       → base += 40
  if gap_controls >= 1                       → base += 20
score_grc = MIN(base, 100)

SCORE TOTALE
────────────────────────────────────
Per entity_type = 'my_domain':
  total = (ssl * 0.25) + (dns * 0.25) + (rep * 0.30) + (grc * 0.20)

Per entity_type = 'supplier' | 'asset':
  (GRC context non applicabile → redistribuire peso)
  total = (ssl * 0.30) + (dns * 0.30) + (rep * 0.40)

Arrotondare a intero. Range 0-100.
```

### Classificazione colore:

```
70-100  → CRITICO   🔴
50-69   → WARNING   🟠
30-49   → ATTENZIONE 🟡
0-29    → OK        🟢
```

### Delta calcolo:

```
delta = score_totale_scan_corrente - score_totale_scan_precedente
Se delta > 0  → peggiorato (▲ +N)
Se delta < 0  → migliorato (▼ -N)
Se delta == 0 → stabile    (→)
```

**Test:** simulare scan con valori noti e verificare che gli score calcolati corrispondano ai valori attesi.

---

## PASSO 5 — ALERT ENGINE

**Obiettivo:** dopo ogni scan, generare alert e collegarli ai moduli Incidenti/Task.

### Trigger alert:

```
TRIGGER 1 — Score critico
  if score_total >= threshold_critical (default 70)
  AND (scan precedente < threshold_critical OR primo scan)
  → genera alert severity='critical', type='score_critical'

TRIGGER 2 — Score peggiorato drasticamente
  if delta >= 20 (peggiorato di 20+ punti in una settimana)
  → genera alert severity='warning', type='score_degraded'

TRIGGER 3 — SSL in scadenza
  if ssl_days_remaining <= 30 AND ssl_days_remaining > 0
  → severity='warning', type='ssl_expiry'
  if ssl_days_remaining <= 0 OR !ssl_valid
  → severity='critical', type='ssl_expired'

TRIGGER 4 — Blacklist attiva
  if in_blacklist = true AND (scan precedente: in_blacklist = false)
  → severity='critical', type='blacklist_new'

TRIGGER 5 — DMARC assente (solo primo rilevamento)
  if !dmarc_present AND nessun alert dmarc_missing attivo
  → severity='warning', type='dmarc_missing'

TRIGGER 6 — Nuovo sottodominio
  if sottodominio trovato in crt.sh non presente in osint_subdomains
  → severity='info', type='new_subdomain'
  → status sottodominio = 'pending' (aspetta classificazione utente)

TRIGGER 7 — Breach trovato (solo miei domini, HIBP)
  if hibp_breaches > 0 AND (scan precedente: hibp_breaches = 0)
  → severity='critical', type='breach_found'
```

### Routing alert → Incidenti/Task:

```
CASO 1 — entity_type = 'my_domain'
  severity = 'critical'
  → Crea INCIDENTE nel modulo incidenti esistente
  → Pre-compila:
      title:       "OSINT Alert: {alert_type} su {display_name}"
      description: testo descrittivo del finding
      source:      "OSINT Module"
      severity:    mappare da alert severity
      domain:      entity.domain
      date:        now()
  → Salva linked_incident_id nell'alert

CASO 2 — entity_type = 'supplier'
  severity IN ('critical', 'warning')
  → Crea TASK nel modulo task esistente
  → Pre-compila:
      title:       "OSINT: {alert_type} - {display_name}"
      description: testo descrittivo del finding
      priority:    'high' se critical, 'medium' se warning
      due_date:    now() + 14 giorni
      source:      "OSINT Module"
  → Salva linked_task_id nell'alert

CASO 3 — entity_type = 'supplier' con asset OT/IT collegato
  → NON creare automaticamente
  → Salvare alert con status = 'pending_escalation'
  → Mostrare in dashboard banner di conferma:
      "Il fornitore [X] gestisce asset OT/IT.
       Vuoi aprire un Incidente invece di un Task?"
      [Crea Incidente] [Crea Task] [Ignora]

CASO 4 — type = 'new_subdomain'
  → NON creare incidente/task
  → Notifica in dashboard sezione "Sottodomini in attesa"
  → Utente sceglie: Includi / Ignora

Nota: non creare duplicati.
Controllare se esiste già un alert attivo dello stesso tipo
per la stessa entità prima di crearne uno nuovo.
```

**Test:** forzare uno scan con valori che triggerino ogni tipo di alert. Verificare che incidenti e task vengano creati correttamente nei moduli esistenti.

---

## PASSO 6 — SCHEDULER

**Obiettivo:** eseguire i scan automaticamente in base alla frequenza configurata.

```
Job: OsintWeeklyScanner
  Frequenza: ogni lunedì alle 02:00 (fuori orario lavorativo)
  Logica:
    1. Legge osint_settings per ogni tenant
    2. Legge tutte le osint_entities attive
    3. Per ogni entità:
       - Se freq = 'weekly' → esegui sempre
       - Se freq = 'monthly' → esegui solo se
         ultimo scan > 28 giorni fa
    4. Esegui enrichment in coda con throttling
       (non in parallelo massivo — rispettare rate limit API)
    5. Calcola score
    6. Triggera alert engine

Throttling consigliato:
  - max 1 richiesta ogni 15s verso crt.sh
  - max 1 richiesta ogni 15s verso VirusTotal (free: 4/min)
  - AbuseIPDB e OTX: 1 ogni 5s
  - DNS e WHOIS: nessun limite, sono lookup locali

Logging: salvare ogni run con timestamp, n. entità scansionate,
         n. alert generati, eventuali errori per entità.
```

**Aggiungere anche:** pulsante "Forza rescan ora" nella dashboard
per singola entità (esegue scan immediato, ignora scheduler).

**Test:** configurare un job di test con frequenza più alta,
verificare che giri correttamente e non crei duplicati.

---

## PASSO 7 — ANONIMIZZAZIONE AI

**Obiettivo:** implementare il layer di anonimizzazione Opzione B
prima di ogni chiamata Claude API.

### Servizio AnonymizationService:

```
Campi DA ANONIMIZZARE (dati identificativi):
  domain          → [DOM_001], [DOM_002], ...
  display_name    → [SUP_001], [SUP_002], ... (fornitori)
                    [SITE_001], ...           (miei siti)
                    [ASSET_001], ...          (asset)
  ip_address      → [IP_001], [IP_002], ...
  email           → [EMAIL_001], ...
  plant_name      → [PLANT_001], ...
  sede_name       → [SEDE_001], ...

Campi CHE RESTANO INTATTI (dati tecnici):
  score_*         tutti gli score numerici
  ssl_*           tutti i dati SSL tecnici
  spf_*           configurazione DNS
  dmarc_*
  vt_malicious, vt_suspicious
  abuseipdb_score, abuseipdb_reports
  otx_pulses
  gsb_status
  in_blacklist, blacklist_sources (nome fonte, non il dominio)
  hibp_breaches, hibp_latest_breach, hibp_data_types
  is_nis2_critical
  asset_type      (IT/OT — generico, non il nome)
  open_risks      (conteggio, non i nomi)
  open_tasks      (conteggio)
  scan_date
  delta

Implementazione:
  1. anonymize(payload) → { anonymizedPayload, mappingTable }
     - Genera placeholder sequenziali per tipo
     - Sostituisce tutte le occorrenze nel payload JSON
     - Ritorna sia il payload anonimizzato che la mappatura
     - La mappatura NON viene mai salvata su disco

  2. deanonymize(text, mappingTable) → text
     - Sostituisce i placeholder con i valori reali nella risposta AI
     - Usare replace con regex per trovare tutti i placeholder

  3. La mappingTable vive solo in RAM durante la singola richiesta
     - Creata subito prima della chiamata API
     - Passata alla funzione di de-anonimizzazione
     - Poi garbage collected — mai persistita
```

### System prompt da inviare a Claude con ogni richiesta OSINT:

```
Sei un esperto di cybersecurity e GRC (Governance, Risk & Compliance).
Stai analizzando dati di monitoraggio OSINT per un'organizzazione.

IMPORTANTE: I dati contengono placeholder anonimizzati nel formato
[DOM_001], [SUP_001], [IP_001], [ASSET_001] ecc.
Usa SEMPRE questi placeholder nelle tue risposte — non tentare
di inferire, indovinare o sostituire i nomi reali.
Analizza esclusivamente i dati tecnici forniti.

Il tuo obiettivo è produrre analisi chiare, prioritizzate e
actionable — non elenchi di dati tecnici grezzi.
Scrivi per un pubblico misto: CISO, responsabili IT e board.
Lingua: italiano, salvo diversa indicazione nei dati.
```

**Test:** chiamare l'API con dati reali, verificare che nessun dato
identificativo reale appaia nel payload inviato. Verificare che
la de-anonimizzazione restituisca i nomi reali nella risposta finale.

---

## PASSO 8 — API BACKEND

**Obiettivo:** esporre le API REST necessarie alla dashboard.

```
GET    /api/osint/entities
       → lista tutte le entità con ultimo score e delta
       Params: ?type=my_domain|supplier|asset
               ?severity=critical|warning|ok
               ?nis2_critical=true

GET    /api/osint/entities/:id
       → dettaglio entità con ultimo scan completo

GET    /api/osint/entities/:id/history
       → storico scan (max 52 settimane = 1 anno)
       Response: array di { scan_date, score_total,
                 score_ssl, score_dns, score_reputation,
                 score_grc_context }

GET    /api/osint/entities/:id/scans/:scanId
       → dettaglio di un singolo scan

POST   /api/osint/entities/:id/scan
       → forza rescan immediato (job asincrono)
       Response: { job_id, status: 'queued' }

GET    /api/osint/alerts
       → lista alert attivi
       Params: ?status=new|acknowledged
               ?severity=critical|warning

PATCH  /api/osint/alerts/:id
       → aggiorna status alert (acknowledge, resolve)
       Body: { status: 'acknowledged' | 'resolved' }

POST   /api/osint/alerts/:id/escalate
       → per alert pending_escalation: scegli routing
       Body: { action: 'incident' | 'task' | 'ignore' }

GET    /api/osint/subdomains/pending
       → lista sottodomini in attesa di classificazione

PATCH  /api/osint/subdomains/:id
       → classifica sottodominio
       Body: { status: 'included' | 'ignored' }

GET    /api/osint/dashboard/summary
       → KPI per header dashboard:
         { total_entities, critical_count, warning_count,
           last_scan_date, next_scan_date, pending_subdomains }

POST   /api/osint/ai/analyze
       → chiama Claude API con dati anonimizzati
       Body: { type: 'attack_surface' | 'suppliers_nis2' | 'board_report' }
       Response: { analysis: string }  — già de-anonimizzato

GET    /api/osint/settings
PATCH  /api/osint/settings
       → lettura e aggiornamento impostazioni modulo
```

**Test:** testare ogni endpoint con Postman o equivalente.
Verificare autenticazione, autorizzazioni per tenant, response format.

---

## PASSO 9 — DASHBOARD FRONTEND

**Obiettivo:** costruire la UI del modulo OSINT.

### Layout pagina:

```
┌─────────────────────────────────────────────────────────────────┐
│  OSINT Monitor                           [⚙ Impostazioni]       │
├──────────┬──────────┬──────────┬──────────┬────────────────────-┤
│ Entità   │ Critiche │ Warning  │ Ultimo   │ Prossimo scan       │
│ 47       │ 🔴 3     │ 🟠 8     │ 21/04    │ 28/04              │
├─────────────────────────────────────────────────────────────────┤
│ ⚠ 2 sottodomini in attesa di classificazione    [Vedi →]       │
├─────────────────────────────────────────────────────────────────┤
│ [Tutti] [Miei domini] [Fornitori NIS2] [Con alert]              │
│ Cerca...                          Ordina: Score ▼               │
├──────────────────────────────────────────────────────────────────┤
│ Entità     | Tipo    | Score      | Δ    | SSL | DNS | Rep | ⚡ │
│ ──────────────────────────────────────────────────────────────  │
│ [SITE_01]  | Sito    | 🔴 82      | ▲+12 | ❌  | ⚠   | ✅  | 1 │
│ [SUP_03]   | Forn.   | 🔴 75      | →    | ⚠   | ❌  | ❌  | 2 │
│ [DOM_07]   | Sito    | 🟠 61      | ▲+5  | ✅  | ⚠   | ⚠   | 0 │
│ ...                                                             │
├─────────────────────────────────────────────────────────────────┤
│  🤖 Analisi AI                                                  │
│  [Analizza superficie di attacco]                               │
│  [Briefing fornitori critici NIS2]                              │
│  [Genera report Board/Audit]                                    │
└─────────────────────────────────────────────────────────────────┘

Note UI tabella:
  - Score: numero + colore background
  - Delta: freccia colorata (rosso se peggiorato, verde se migliorato)
  - SSL/DNS/Rep: icone ✅ ⚠ ❌
  - ⚡ = n. alert attivi per quella entità
  - Click su riga → apre dettaglio entità (slide-over o pagina)
```

### Pannello dettaglio entità (click su riga):

```
┌─────────────────────────────────────────────────────┐
│ [Nome entità]              [🔄 Forza rescan]        │
│ Tipo: Fornitore NIS2-critico | Ultimo scan: 21/04   │
├─────────────────────────────────────────────────────┤
│ SCORE TOTALE: 🔴 82  ▲+12 rispetto alla scorsa sett.│
├──────────┬──────────┬───────────┬───────────────────┤
│ SSL  🔴  │ DNS  🟠  │ Rep  🟢   │ GRC  🟠           │
│   100    │   65     │    10     │    55              │
├─────────────────────────────────────────────────────┤
│ DETTAGLIO FINDING                                   │
│ ❌ SSL scaduto il 14/12/2025                        │
│ ⚠  DMARC presente ma p=none (solo monitoring)      │
│ ✅ SPF configurato correttamente                    │
│ ✅ Nessuna blacklist attiva                         │
│ ℹ  2 rischi aperti collegati                       │
├─────────────────────────────────────────────────────┤
│ STORICO SCORE — 12 mesi                             │
│ [grafico lineare — vedi spec sotto]                 │
├─────────────────────────────────────────────────────┤
│ ALERT ATTIVI                                        │
│ 🔴 SSL scaduto → Task #234 [Vedi task →]           │
│ 🟠 DMARC p=none → Task #235 [Vedi task →]         │
├─────────────────────────────────────────────────────┤
│ [+ Crea task manualmente]  [+ Crea incidente]       │
└─────────────────────────────────────────────────────┘
```

### Grafico storico score:

```
Libreria: recharts (già disponibile nel progetto) o Chart.js
Tipo: LineChart
Asse X: date settimanali, ultimi 52 scan (o disponibili)
Asse Y: 0-100 (invertito: 0 in alto = OK, 100 in basso = CRITICO)
Serie 1: score anno corrente — linea continua colorata per zona
Serie 2: score anno precedente — linea tratteggiata grigia
Zone colorate di sfondo:
  0-29   verde tenue
  30-49  giallo tenue
  50-69  arancione tenue
  70-100 rosso tenue
Marker: pallino su punti dove è stato creato un incidente/task

Tooltip al hover: data, score, delta, n. alert attivi quel giorno
```

### Pannello AI (click su uno dei 3 pulsanti):

```
1. Chiama /api/osint/ai/analyze con type corrispondente
2. Mostra spinner con messaggio "Analisi in corso..."
3. Mostra risposta in pannello slide-over o modal
4. Pulsante [📋 Copia] e [⬇ Scarica .txt]
5. Non salvare la risposta nel DB — è sempre on-demand
```

### Pannello impostazioni (/osint/settings):

```
Sezione: Frequenza scan
  Miei domini:              [Settimanale ▼]
  Fornitori NIS2-critici:   [Settimanale ▼]
  Fornitori non critici:    [Mensile ▼]

Sezione: Soglie alert
  Score critico (default 70): [____]
  Score warning (default 50): [____]

Sezione: Sottodomini
  Nuovi sottodomini rilevati: [Chiedi conferma ▼]

Sezione: Privacy AI
  Anonimizzazione dati verso AI: [✅ Attivo]

Sezione: API Keys opzionali
  HIBP API Key:        [______________] [Testa]
  Nota: solo per i tuoi domini verificati su haveibeenpwned.com

[Salva impostazioni]
```

**Test:** navigare tutta la UI, verificare responsività,
testare filtri, tooltip, grafico, pannello AI end-to-end.

---

## PASSO 10 — TEST INTEGRAZIONE FINALE

**Checklist completa prima del rilascio:**

```
DATI
☐ Modulo Siti: campo additional_domains si salva e si legge
☐ Aggregatore: entità create correttamente da tutti i moduli
☐ Deduplicazione: stesso dominio da due sorgenti gestito correttamente
☐ Entità disattivata se sorgente viene eliminata

ENRICHMENT
☐ crt.sh: SSL e sottodomini recuperati correttamente
☐ DNS: SPF, DMARC, MX, DNSSEC rilevati correttamente
☐ WHOIS: scadenza dominio e registrar recuperati
☐ VirusTotal: risponde correttamente (con e senza API key)
☐ AbuseIPDB: risponde correttamente
☐ OTX: risponde correttamente
☐ Google Safe Browsing: risponde correttamente
☐ HIBP: risponde correttamente (solo miei domini)
☐ Rate limiting: nessun ban da API esterne dopo scan completo

SCORE
☐ Score SSL: valori calcolati correttamente su casi noti
☐ Score DNS: valori calcolati correttamente su casi noti
☐ Score reputation: valori calcolati correttamente
☐ Score GRC: applicato solo a miei domini
☐ Pesi corretti per tipo entità (fornitore vs mio dominio)
☐ Delta calcolato correttamente

ALERT
☐ Alert score_critical generato correttamente
☐ Alert ssl_expiry generato ai giorni giusti
☐ Alert blacklist_new generato solo al primo rilevamento
☐ Nessun alert duplicato creato
☐ Incidente creato per miei domini con severity critical
☐ Task creato per fornitori con severity critical/warning
☐ Banner escalation mostrato per fornitori con asset OT collegato
☐ Notifica sottodomini pending mostrata in dashboard

SCHEDULER
☐ Job gira alla frequenza configurata
☐ Rispetta frequenza per entità (weekly vs monthly)
☐ Non crea scan duplicati se job gira due volte
☐ "Forza rescan" funziona correttamente

ANONIMIZZAZIONE
☐ Nessun dato identificativo reale nel payload verso Claude API
☐ De-anonimizzazione corretta nella risposta mostrata all'utente
☐ Mappatura non persiste dopo la richiesta

UI
☐ Dashboard si carica con tutti i KPI corretti
☐ Filtri funzionanti
☐ Dettaglio entità mostra tutti i dati
☐ Grafico storico renderizza correttamente
☐ Analisi AI restituisce risposta sensata
☐ Impostazioni si salvano e vengono rispettate dallo scheduler
☐ Responsive su mobile e tablet
```

---

## NOTE FINALI PER CLAUDE CODE

- **Non modificare** i moduli esistenti (Incidenti, Task, Risk Assessment, Fornitori, Asset) — solo aggiungere il campo al modulo Siti (Passo 0) e creare i link in entrata da OSINT
- **Usare il sistema di autenticazione esistente** — il modulo OSINT rispetta le stesse logiche di accesso
- **Le API key esterne** vanno sempre cifrate a riposo nel DB
- **Non bloccare la UI** durante i scan — tutto asincrono, mostrare stati di loading
- Seguire i pattern di codice, naming convention e struttura cartelle già esistenti nel progetto
- ** Aggiorna sempre questo file quando vai avanti per non perderti **
- ** se possiamor isparmiare token cambiando modello a seconda della fase facciamolo **
