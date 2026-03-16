# MANUAL_TECNICO.md — GRC Compliance Webapp

> Guida per sviluppatori: architettura, modelli dati, API, framework normativi, AI Engine, test e convenzioni.

---

## Indice

- [Architettura applicativa](#architettura-applicativa)
- [Setup ambiente di sviluppo](#setup-ambiente-di-sviluppo)
- [Struttura backend](#struttura-backend)
- [Modelli dati principali](#modelli-dati-principali)
- [API REST](#api-rest)
- [Audit trail — append-only con hash chain](#audit-trail--append-only-con-hash-chain)
- [Aggiungere un framework normativo](#aggiungere-un-framework-normativo)
- [Aggiungere un modulo](#aggiungere-un-modulo)
- [AI Engine M20 — integrazione tecnica](#ai-engine-m20--integrazione-tecnica)
- [Integrazioni esterne](#integrazioni-esterne)
- [i18n — internazionalizzazione](#i18n--internazionalizzazione)
- [Test](#test)
- [Convenzioni di sviluppo](#convenzioni-di-sviluppo)
- [Troubleshooting](#troubleshooting)

---

## Architettura applicativa

```
frontend (React SPA)
    │  REST JSON / JWT
    ▼
backend (Django + DRF)
    │
    ├── apps/          un'app Django per modulo (M00–M20)
    ├── core/          settings, middleware, base models, auth
    └── frameworks/    JSON framework normativi (VDA ISA, NIS2, ISO 27001)
    │
    ├── PostgreSQL     database principale + audit trail append-only
    ├── Redis          cache sessioni + broker Celery
    └── S3 / MinIO     object storage documenti ed evidenze
    │
    └── Celery Worker  task asincroni: notifiche, sync KB4, job audit trail
        Celery Beat    scheduler ricorrenti: scadenze, digest email, sync
```

**Principi architetturali vincolanti:**

- Framework as data: i controlli sono JSON, non codice. Aggiungere DORA non richiede deploy.
- Table inheritance IT/OT: `Asset` base + `AssetIT` e `AssetOT` — nessuna colonna nullable inutile.
- RBAC (M02) separato dalla governance normativa (M00): permessi applicativi vs. nomine formali.
- Audit trail append-only con hash chain SHA-256: immutabilità tecnica, non solo procedurale.
- Task assegnati a ruolo con risoluzione dinamica: cambio di personale non richiede riallocazione manuale.
- Versioni framework immutabili: archiviate, mai eliminate.

---

## Setup ambiente di sviluppo

### Prerequisiti

```bash
# Verifica versioni
python --version     # >= 3.11
node --version       # >= 20
docker --version     # >= 4.x
```

### Primo avvio

```bash
git clone https://github.com/org/grc-webapp.git
cd grc-webapp

# Backend
cp .env.example .env
docker compose up -d db redis

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py load_frameworks       # importa VDA ISA, NIS2, ISO 27001
python manage.py seed_demo             # dati demo opzionali
python manage.py createsuperuser

# Avvia backend
python manage.py runserver 0.0.0.0:8000

# Frontend (in un altro terminale)
cd frontend
npm install
npm run dev
```

### Comandi Makefile

```bash
make dev          # docker compose up + runserver + npm run dev
make migrate      # python manage.py migrate
make test         # pytest + jest
make lint         # ruff + eslint
make load-fw      # python manage.py load_frameworks
make seed         # python manage.py seed_demo
make shell        # python manage.py shell_plus
make celery       # avvia worker Celery in foreground
```

---

## Struttura backend

### Struttura di un'app modulo

```
apps/incidents/          # M09 — Gestione Incidenti
├── __init__.py
├── admin.py
├── apps.py
├── models.py            # Incident, IncidentNotification, RCA, ...
├── serializers.py       # DRF serializers
├── views.py             # ViewSet API
├── urls.py              # router.register(...)
├── permissions.py       # permessi specifici del modulo
├── services.py          # business logic — non nella view
├── tasks.py             # task Celery del modulo
├── signals.py           # post_save, post_delete per audit trail
└── tests/
    ├── test_models.py
    ├── test_api.py
    └── test_services.py
```

La business logic non va mai nelle view — sta in `services.py`. Le view chiamano solo serializer e service.

### Modello base

```python
# core/models.py
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='+')
    deleted_at = models.DateTimeField(null=True, blank=True)  # soft delete

    objects = SoftDeleteManager()  # filtra deleted_at is null di default

    class Meta:
        abstract = True
```

Tutti i modelli dell'applicazione ereditano da `BaseModel`. Non usare mai `delete()` diretto — usare il manager `soft_delete()`.

---

## Modelli dati principali

### M00 — Governance

```python
class RoleAssignment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=NormativeRole.choices)
    # ciso, plant_security_officer, nis2_contact, dpo, isms_manager,
    # internal_auditor, comitato_membro, bu_referente, raci_*
    scope_type = models.CharField(max_length=20)  # org | bu | plant
    scope_id = models.UUIDField(null=True)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True)
    signed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    document = models.ForeignKey('documents.Document', null=True, on_delete=models.SET_NULL)
    framework_refs = ArrayField(models.CharField(max_length=50), default=list)
```

### M01 — Plant Registry

```python
class Plant(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=2)  # ISO 3166-1 alpha-2
    bu = models.ForeignKey('BusinessUnit', null=True, on_delete=models.SET_NULL)
    parent_plant = models.ForeignKey('self', null=True, on_delete=models.SET_NULL)
    has_ot = models.BooleanField(default=False)
    purdue_level_max = models.IntegerField(null=True)
    nis2_scope = models.CharField(
        max_length=20,
        choices=[('essenziale','Essenziale'),('importante','Importante'),('non_soggetto','Non soggetto')]
    )
    status = models.CharField(max_length=20)  # attivo | in_dismissione | chiuso

class PlantFramework(BaseModel):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    framework = models.ForeignKey('controls.Framework', on_delete=models.CASCADE)
    active_from = models.DateField()
    level = models.CharField(max_length=10, null=True)  # es. L2 o L3 per TISAX

    class Meta:
        unique_together = ['plant', 'framework']
```

### M03 — Controlli

```python
class Framework(BaseModel):
    code = models.CharField(max_length=50, unique=True)   # VDA_ISA_6_0, NIS2, ISO_27001_2022
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    published_at = models.DateField()
    archived_at = models.DateField(null=True)             # mai cancellato, solo archiviato

class Control(BaseModel):
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=50)         # es. "VDA-5.1.1"
    domain = models.CharField(max_length=100)
    translations = models.JSONField()
    # { "it": {"title": "...", "guidance": "..."}, "en": {...}, "fr": {...}, "pl": {...}, "tr": {...} }

class ControlInstance(BaseModel):
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    control = models.ForeignKey(Control, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[('compliant','Compliant'),('parziale','Parziale'),
                 ('gap','Gap'),('na','N/A'),('non_valutato','Non valutato')]
    )
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    na_approved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    na_approved_at = models.DateTimeField(null=True)
    na_review_by = models.DateField(null=True)            # max 12 mesi per TISAX L3
    notes = models.TextField(blank=True)
    last_evaluated_at = models.DateTimeField(null=True)
```

### M04 — Asset

```python
class Asset(BaseModel):
    """Tabella base — table inheritance"""
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10)          # IT | OT
    criticality = models.IntegerField(default=1)          # 1–5, ereditata dal processo
    processes = models.ManyToManyField('bia.CriticalProcess', blank=True)

class AssetIT(Asset):
    fqdn = models.CharField(max_length=255, blank=True)
    ip_address = GenericIPAddressField(null=True)
    os = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    eol_date = models.DateField(null=True)
    cve_score_max = models.FloatField(null=True)
    internet_exposed = models.BooleanField(default=False)

class AssetOT(Asset):
    purdue_level = models.IntegerField()                  # 0–5
    category = models.CharField(max_length=20)            # PLC | SCADA | HMI | RTU | sensore
    patchable = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone = models.ForeignKey('NetworkZone', null=True, on_delete=models.SET_NULL)
```

### M09 — Incidenti

```python
class Incident(BaseModel):
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField()
    detected_at = models.DateTimeField()
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assets = models.ManyToManyField('assets.Asset', blank=True)
    severity = models.CharField(max_length=10)            # bassa|media|alta|critica
    nis2_notifiable = models.CharField(max_length=15)     # si|no|da_valutare
    nis2_confirmed_at = models.DateTimeField(null=True)
    nis2_confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    status = models.CharField(max_length=20)              # aperto|in_analisi|chiuso
    rca = models.OneToOneField('RCA', null=True, on_delete=models.SET_NULL)

    @property
    def nis2_early_warning_deadline(self):
        return self.created_at + timedelta(hours=24)

    @property
    def nis2_full_notification_deadline(self):
        return self.created_at + timedelta(hours=72)
```

---

## API REST

### Autenticazione

```
Authorization: Bearer <JWT-token>
```

I token JWT scadono dopo 8 ore. Il refresh avviene automaticamente se l'utente è attivo. Gli auditor esterni usano token speciali con scope e scadenza limitati (generati da M02).

### Convenzioni URL

```
GET    /api/v1/{modulo}/                  # lista con filtri e paginazione
POST   /api/v1/{modulo}/                  # crea
GET    /api/v1/{modulo}/{id}/             # dettaglio
PATCH  /api/v1/{modulo}/{id}/             # aggiornamento parziale
DELETE /api/v1/{modulo}/{id}/             # soft delete (deleted_at)

# Azioni custom
POST   /api/v1/incidents/{id}/confirm_nis2/
POST   /api/v1/incidents/{id}/send_notification/
POST   /api/v1/documents/{id}/approve/
POST   /api/v1/controls/{id}/evaluate/
```

### Filtri e paginazione

```
GET /api/v1/controls/?framework=VDA_ISA_6_0&plant=PLT-001&status=gap&page=2&page_size=25
```

Tutti gli endpoint lista supportano:
- `page` e `page_size` (default 25, max 100)
- `ordering` (es. `ordering=-created_at`)
- filtri specifici del modulo documentati in `/api/v1/schema/` (OpenAPI 3.0)

### Risposta standard

```json
{
  "count": 83,
  "next": "/api/v1/controls/?page=2",
  "previous": null,
  "results": [...]
}
```

### Errori

```json
{
  "error": "validation_error",
  "detail": {
    "status": ["Il valore 'invalid' non è una scelta valida."],
    "owner": ["Questo campo è obbligatorio."]
  }
}
```

Codici HTTP usati: 200, 201, 204, 400, 401, 403, 404, 409 (conflitto di stato), 422 (errore business logic), 500.

### API pubblica uscente (M19)

```
GET /api/external/v1/plants/           # lista plant con nis2_scope
GET /api/external/v1/controls/         # controlli con stato per plant
GET /api/external/v1/risks/            # risk assessment aperti

Autenticazione: API key nell'header  X-API-Key: <key>
Rate limit: 100 req/min per chiave
```

---

## Audit trail — append-only con hash chain

### Principio

Ogni azione rilevante scrive un record `AuditLog`. Il record è immutabile: il trigger PostgreSQL rifiuta UPDATE e DELETE. Ogni record contiene `prev_hash` e `record_hash = SHA256(json_payload + prev_hash)`, formando una catena verificabile.

### Struttura record

```python
class AuditLog(models.Model):
    # Non eredita da BaseModel — non ha soft delete, non ha updated_at
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)

    # Chi
    user_id = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time = models.CharField(max_length=50)   # snapshot ruolo al momento

    # Cosa
    action_code = models.CharField(max_length=100)        # codice neutro — es. incident.created
    level = models.CharField(max_length=2)                # L1 | L2 | L3
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField()                          # dati rilevanti dell'azione

    # Hash chain
    prev_hash = models.CharField(max_length=64)
    record_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'audit_log'
        # partitioned by RANGE (timestamp_utc) — definito nella migrazione
```

### Come loggare un'azione

```python
from core.audit import log_action

# In un service o in un signal post_save
log_action(
    request=request,            # per estrarre user e ruolo corrente
    action_code='document.approved',
    level='L2',
    entity=document,
    payload={
        'version': document.current_version,
        'approver_id': str(request.user.id),
        'framework_ids': document.framework_ids,
    }
)
```

Il modulo `core.audit` gestisce automaticamente:
- Snapshot `user_role_at_time` al momento della chiamata
- Calcolo `prev_hash` (legge l'ultimo record per entity_type) e `record_hash`
- Scrittura transazionale (se il log fallisce, viene sollevata eccezione)

### Verifica integrità

```bash
python manage.py verify_audit_trail_integrity
# Controlla l'intera catena: ricalcola ogni hash e confronta
# Output: OK se la catena è integra, FAIL con primo record corrotto se no

# Job notturno (Celery Beat — già configurato)
# Invia alert se catena rotta
```

---

## Aggiungere un framework normativo

I framework sono JSON in `backend/frameworks/`. Non serve toccare il codice Python.

### Struttura JSON

```json
{
  "code": "NIST_CSF_2_0",
  "name": "NIST Cybersecurity Framework",
  "version": "2.0",
  "published_at": "2024-02-26",
  "domains": [
    {
      "code": "GV",
      "translations": {
        "it": {"name": "Govern"},
        "en": {"name": "Govern"},
        "fr": {"name": "Gouverner"},
        "pl": {"name": "Zarządzanie"},
        "tr": {"name": "Yönetim"}
      }
    }
  ],
  "controls": [
    {
      "external_id": "GV.OC-01",
      "domain": "GV",
      "translations": {
        "it": {
          "title": "Missione organizzativa documentata",
          "guidance": "La missione dell'organizzazione è compresa e informa la gestione della cybersecurity..."
        },
        "en": {
          "title": "Organizational mission documented",
          "guidance": "The organizational mission is understood..."
        },
        "fr": { "title": "...", "guidance": "..." },
        "pl": { "title": "...", "guidance": "..." },
        "tr": { "title": "...", "guidance": "..." }
      }
    }
  ],
  "mappings": [
    {
      "source_control": "GV.OC-01",
      "target_framework": "ISO_27001_2022",
      "target_control": "5.2",
      "relationship": "equivalente"
    }
  ]
}
```

### Import

```bash
# Importa il nuovo framework
python manage.py load_frameworks --file frameworks/nist_csf_2_0.json

# Il comando:
# 1. Crea il Framework e tutti i Control
# 2. Crea le ControlMapping con gli altri framework
# 3. NON genera ControlInstance (si generano quando si attiva il framework su un plant)

# Attivare il framework su un plant
# Via admin o API:
POST /api/v1/plant-frameworks/
{ "plant": "PLT-001", "framework": "NIST_CSF_2_0", "active_from": "2026-03-13" }
# → genera automaticamente ControlInstance in stato non_valutato per ogni controllo
```

### Versionamento framework

Quando esce una nuova versione di un framework esistente:

1. Crea un nuovo file JSON con `code` identico ma `version` aggiornato (es. `VDA_ISA_6_1`)
2. Il comando `load_frameworks --version-update` confronta i controlli:
   - Invariati: migrano automaticamente con lo stesso stato
   - Modificati: vengono creati nuovi `ControlInstance` in stato `non_valutato` con task di review
   - Eliminati: vengono archiviati (`archived_at`) con nota
   - Nuovi: creati in stato `non_valutato`

La versione precedente non viene mai cancellata — rimane archiviata per gli audit storici.

---

## Aggiungere un modulo

Per aggiungere un nuovo modulo funzionale (es. M21):

```bash
# 1. Crea l'app Django
cd backend
python manage.py startapp new_module apps/new_module

# 2. Aggiungi a INSTALLED_APPS in core/settings/base.py
INSTALLED_APPS = [
    ...
    'apps.new_module',
]

# 3. Registra le URL
# backend/core/urls.py
path('api/v1/new-module/', include('apps.new_module.urls')),

# 4. Struttura minima obbligatoria
# apps/new_module/
#   models.py        — ereditare da BaseModel
#   serializers.py
#   views.py         — ViewSet con permessi
#   urls.py          — router.register
#   services.py      — business logic
#   tasks.py         — Celery tasks se necessario
#   signals.py       — per audit trail
#   tests/
```

**Checklist per ogni nuovo modulo:**

- [ ] Tutti i modelli ereditano da `BaseModel` (UUID, soft delete, timestamp)
- [ ] Ogni azione rilevante chiama `log_action()` nei signal o nei service
- [ ] Le view usano `ModulePermission` per il controllo accessi
- [ ] Sono presenti test per modelli, API e service (coverage >= 80%)
- [ ] Gli action code sono registrati nel catalogo `core/audit/action_codes.py`
- [ ] Le traduzioni delle label UI sono aggiunte ai file i18n in `frontend/src/i18n/`

---

## AI Engine M20 — integrazione tecnica

### Architettura del modulo

```
apps/ai_engine/
├── sanitizer.py        # anonimizzazione PII prima del cloud
├── router.py           # scelta locale vs cloud in base alla funzione
├── functions/
│   ├── classification.py
│   ├── text_analysis.py
│   ├── draft_generation.py
│   └── anomaly_detection.py
├── models.py           # AiInteractionLog
├── tasks.py            # job asincroni anomaly detection
└── tests/
```

### AiInteractionLog

```python
class AiInteractionLog(BaseModel):
    function = models.CharField(max_length=50)
    # classification | text_analysis | draft_generation | anomaly_detection
    module_source = models.CharField(max_length=5)       # M04, M07, M09...
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)        # es. gpt-4o | llama3.1:8b
    input_hash = models.CharField(max_length=64)         # SHA256 del prompt — mai il testo
    output_ai = models.TextField()                       # output grezzo del modello
    output_human_final = models.TextField(null=True)     # dopo conferma/modifica umana
    delta = models.JSONField(null=True)                  # diff output_ai vs output_human_final
    confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(null=True)
    ignored = models.BooleanField(default=False)         # suggerimento ignorato dall'utente
```

`AiInteractionLog` è registrato in M10 tramite `log_action()` con `action_code='ai.suggestion.confirmed'` o `'ai.suggestion.ignored'`.

### Sanitizer

```python
# apps/ai_engine/sanitizer.py

class Sanitizer:
    """
    Anonimizza il contesto prima di inviarlo al cloud LLM.
    Mappa i token ai valori reali per la de-anonimizzazione del risultato.
    """

    def sanitize(self, context: dict) -> tuple[dict, dict]:
        """
        Returns: (sanitized_context, token_map)
        token_map: { "[PLANT_A]": "Stabilimento Milano", ... }
        """
        ...

    def desanitize(self, text: str, token_map: dict) -> str:
        """Sostituisce i token con i valori reali nel testo generato."""
        ...
```

### Chiamare una funzione AI da un service

```python
from apps.ai_engine.functions.classification import classify_incident_severity

# Nel service M09 — incidents/services.py
async def suggest_severity(incident: Incident, request) -> dict | None:
    if not settings.AI_ENGINE_CONFIG['functions']['classification']['enabled']:
        return None

    result = await classify_incident_severity(
        description=incident.description,
        assets=[a.name for a in incident.assets.all()],
        plant_type=incident.plant.nis2_scope,
    )
    # result = { "suggested_severity": "alta", "confidence": 0.87, "reasoning": "..." }

    # Viene mostrato all'utente come suggerimento — non applicato automaticamente
    return result
```

### Human-in-the-loop — flusso API

```
POST /api/v1/ai/suggest/
{ "function": "classification", "entity_type": "incident", "entity_id": "..." }

→ 200 { "suggestion_id": "...", "output": { "suggested_severity": "alta" } }

# L'utente accetta, modifica o ignora
POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": true, "final_value": "alta" }
# → aggiorna AiInteractionLog.confirmed_by e .output_human_final
# → applica il valore all'entità

POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": false }
# → AiInteractionLog.ignored = True
# → nessun effetto sull'entità
```

---

## Integrazioni esterne

### KnowBe4 (M15)

```python
# apps/training/kb4_client.py

class KnowBe4Client:
    BASE_URL = settings.KNOWBE4_API_URL

    def get_enrollments_delta(self, since: datetime) -> list[dict]:
        """Scarica i completamenti dal timestamp indicato."""
        ...

    def get_phishing_results(self, campaign_id: str) -> list[dict]:
        ...

    def provision_user(self, user: User, groups: list[str]) -> bool:
        """Crea o aggiorna utente su KB4 con i gruppi corretti (ruolo+plant+lingua)."""
        ...

    def deprovision_user(self, email: str) -> bool:
        """Revoca accesso utente su KB4 (chiamato da signal post_save su User.is_active=False)."""
        ...
```

Il sync viene eseguito dal task Celery `training.tasks.sync_knowbe4` schedulato ogni notte alle 02:00.

### Webhook uscente (M19)

```python
# Struttura payload webhook
{
  "event": "risk.red_threshold_exceeded",
  "timestamp": "2026-03-13T10:00:00Z",
  "plant_id": "PLT-001",
  "plant_name": "...",              # incluso solo se il destinatario ha accesso
  "data": {
    "risk_id": "...",
    "score": 18,
    "asset_ids": ["..."]
  },
  "signature": "sha256=..."         # HMAC-SHA256 con la chiave configurata
}
```

---

## i18n — internazionalizzazione

### Backend — Django i18n

```python
# In un model o service — non usare stringhe hardcoded
from django.utils.translation import gettext_lazy as _

class ControlInstance(BaseModel):
    status = models.CharField(
        choices=[
            ('compliant', _('Compliant')),
            ('gap', _('Gap')),
        ]
    )
```

Le traduzioni backend stanno in `backend/locale/{lingua}/LC_MESSAGES/django.po`. Per aggiungere stringhe:

```bash
python manage.py makemessages -l pl
# Modifica locale/pl/LC_MESSAGES/django.po
python manage.py compilemessages
```

### Frontend — i18next

```
frontend/src/i18n/
├── it/
│   ├── common.json          # stringhe UI generali
│   ├── incidents.json        # M09
│   └── controls.json         # M03
├── en/
├── fr/
├── pl/
└── tr/
```

Struttura file namespace:

```json
{
  "status": {
    "compliant": "Conforme",
    "gap": "Gap",
    "parziale": "Parziale",
    "na": "N/A",
    "non_valutato": "Non valutato"
  },
  "actions": {
    "save": "Salva",
    "approve": "Approva"
  }
}
```

Uso nel componente React:

```jsx
import { useTranslation } from 'react-i18next';

function ControlStatus({ status }) {
  const { t } = useTranslation('controls');
  return <span>{t(`status.${status}`)}</span>;
}
```

### Controlli — traduzioni nel JSON framework

```json
// frameworks/vda_isa_6_0.json — controllo con 5 lingue
{
  "external_id": "VDA-5.1.1",
  "translations": {
    "it": { "title": "Classificazione delle informazioni", "guidance": "..." },
    "en": { "title": "Information classification", "guidance": "..." },
    "fr": { "title": "Classification des informations", "guidance": "..." },
    "pl": { "title": "Klasyfikacja informacji", "guidance": "..." },
    "tr": { "title": "Bilgi sınıflandırması", "guidance": "..." }
  }
}
```

Il serializer restituisce automaticamente la traduzione nella lingua del richiedente:

```python
# In controls/serializers.py
def get_title(self, obj):
    lang = self.context['request'].user.profile.language  # it | en | fr | pl | tr
    return obj.translations.get(lang, {}).get('title') or obj.translations['en']['title']
```

---

## Test

### Struttura

```
tests/
├── unit/           # test modelli e service, no DB
├── integration/    # test API con DB, usa pytest-django
└── e2e/            # Playwright — flussi utente end-to-end
```

### Eseguire i test

```bash
# Test suite completa
pytest

# Solo un modulo
pytest tests/integration/test_incidents.py -v

# Con coverage
pytest --cov=apps --cov-report=html
open htmlcov/index.html

# Solo i test veloci (no DB)
pytest -m "not slow" tests/unit/

# Frontend
cd frontend && npm test
```

### Fixtures standard

```python
# conftest.py — disponibili in tutti i test
@pytest.fixture
def plant(db):
    return PlantFactory(nis2_scope='essenziale')

@pytest.fixture
def compliance_officer(db, plant):
    user = UserFactory()
    UserPlantAccess.objects.create(user=user, plant=plant, role='compliance_officer')
    return user

@pytest.fixture
def api_client(compliance_officer):
    client = APIClient()
    client.force_authenticate(user=compliance_officer)
    return client
```

### Test audit trail

```python
def test_incident_creation_logs_audit(api_client, plant, db):
    response = api_client.post('/api/v1/incidents/', {...})
    assert response.status_code == 201

    log = AuditLog.objects.filter(
        action_code='incident.created',
        entity_id=response.data['id']
    ).first()

    assert log is not None
    assert log.level == 'L2'
    assert log.user_role_at_time == 'compliance_officer'
    # Verifica hash chain
    assert log.record_hash == compute_hash(log.payload, log.prev_hash)
```

---

## Convenzioni di sviluppo

### Git

- Branch: `feature/M{nn}-descrizione`, `fix/M{nn}-bug-description`, `chore/descrizione`
- Commit: `feat(M09): aggiungi timer NIS2 con countdown visibile`
- Un branch = un modulo o una funzionalità coerente
- Nessun commit diretto su `main` o `develop`

### Python / Django

- Formatter: `ruff format` (black-compatible)
- Linter: `ruff check`
- Type hints su tutti i service e i client esterni
- Docstring obbligatoria su classi e metodi pubblici
- Nessuna logica business nelle view — tutto in `services.py`
- Nessuna query N+1 — usare `select_related` e `prefetch_related`

### React / TypeScript

- TypeScript su tutti i componenti
- Nessun `any` esplicito
- Componenti di presentazione separati dai componenti contenitore
- Le chiamate API vanno in custom hook (`useIncident`, `useControls`)
- Formatter: Prettier
- Linter: ESLint

### Sicurezza

- Nessuna credenziale nel codice sorgente
- Nessun dato sensibile nei log (usare hash o mascheramento)
- CSRF token su tutte le mutation
- Rate limiting su endpoint pubblici e su M20 AI
- Input validation su serializer — mai fidarsi del client

#### JWT, throttling e endpoint di servizio

- I token JWT sono gestiti da `rest_framework_simplejwt` con **ACCESS_TOKEN_LIFETIME=8h** e **REFRESH_TOKEN_LIFETIME=7gg**, rotazione e blacklist attive (vedi `core/settings/base.py` – `SIMPLE_JWT`).
- Il throttling di base usa `AnonRateThrottle` e `UserRateThrottle` con rate predefinite (`anon=100/min`, `user=1000/min`) — personalizzabili per endpoint sensibili.
- Alcuni endpoint amministrativi (es. reset DB di test in `auth_grc.ResetTestDbView`) sono esplicitamente bloccati in produzione tramite controllo su `settings.DEBUG` per evitare uso improprio fuori da ambienti di test.

---

## Troubleshooting

### Celery Beat non esegue i task schedulati

```bash
# Verifica che il beat sia in esecuzione
docker compose ps celery-beat
# Se non è up: docker compose restart celery-beat

# Verifica lo stato dei task pianificati
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(PeriodicTask.objects.filter(enabled=True).values('name','last_run_at'))"
```

### Audit trail integrity check fallisce

Il fallimento indica che un record è stato modificato o che la catena è stata interrotta. Non tentare di riparare — contattare il team di sicurezza. Il sistema genera un alert P1 automatico.

```bash
# Trova il primo record corrotto
python manage.py verify_audit_trail_integrity --verbose
```

### Import framework fallisce

```bash
python manage.py load_frameworks --file frameworks/nuovo.json --dry-run
# Mostra le differenze senza applicarle

python manage.py load_frameworks --file frameworks/nuovo.json --validate-only
# Valida il JSON senza importare
```

### Sync KnowBe4 fallisce

```bash
# Verifica credenziali
python manage.py shell -c "from apps.training.kb4_client import KnowBe4Client; print(KnowBe4Client().health_check())"

# Riesegui il sync manualmente
python manage.py sync_knowbe4 --full
```

### Token AI cloud non autorizzato (M20)

1. Verifica che `AI_ENGINE_ENABLED=true` e che la funzione specifica sia abilitata in `AI_ENGINE_CONFIG`
2. Controlla che l'API key sia configurata e non scaduta
3. Verifica che il sanitizer non stia generando errori: `grep "sanitizer" logs/app.log | tail -20`
4. In caso di errore persistente, il sistema fa fallback al modello locale se disponibile
