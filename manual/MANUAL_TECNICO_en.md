# Technical Manual — GRC Platform

> Developer guide: architecture, data models, API, regulatory frameworks, AI Engine, tests and conventions.

---

## Table of Contents

- [Stack and versions](#stack-and-versions)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Main models](#main-models)
- [API](#api)
- [Security](#security)
- [Privacy and GDPR](#privacy-and-gdpr)
- [Audit trail — append-only with hash chain](#audit-trail--append-only-with-hash-chain)
- [Audit Preparation — technical logic](#audit-preparation--technical-logic)
- [Compliance Schedule (M08)](#compliance-schedule-m08)
- [Adding a regulatory framework](#adding-a-regulatory-framework)
- [Adding a module](#adding-a-module)
- [AI Engine M20 — technical integration](#ai-engine-m20--technical-integration)
- [External integrations](#external-integrations)
- [i18n — internationalisation](#i18n--internationalisation)
- [Frontend](#frontend)
- [Tests](#tests)
- [Management commands](#management-commands)
- [Environment variables](#environment-variables)
- [Development conventions](#development-conventions)
- [Troubleshooting](#troubleshooting)

---

## Stack and versions

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend runtime | Python | 3.11 |
| Web framework | Django | 5.1 |
| REST API | Django REST Framework | 3.15 |
| Task queue | Celery | 5.x |
| Cache/Broker | Redis | 7 |
| Database | PostgreSQL | 15 |
| Production server | Gunicorn | — |
| Frontend framework | React | 18.3 |
| Build tool | Vite | 5.4 |
| CSS | Tailwind CSS | 3.4 |
| State management | Zustand | 5.0 |
| Data fetching | TanStack Query | 5.56 |
| Router | React Router | 7 |
| Frontend i18n | i18next | 23.10 |
| Markdown | react-markdown | 9.0 |
| Container | Docker Compose | v2 |

---

## Architecture

### Architectural flow

```
frontend (React SPA)
    │  REST JSON / JWT
    ▼
backend (Django + DRF)
    │
    ├── apps/          one Django app per module (M00–M20)
    ├── core/          settings, middleware, base models, auth
    └── frameworks/    regulatory framework JSON files (VDA ISA, NIS2, ISO 27001)
    │
    ├── PostgreSQL     main database + append-only audit trail
    ├── Redis          session cache + Celery broker
    └── S3 / MinIO     object storage for documents and evidence
    │
    └── Celery Worker  async tasks: notifications, KB4 sync, audit trail jobs
        Celery Beat    recurring scheduler: deadlines, email digest, sync
```

### Architectural principles (from CLAUDE.md)

The following principles are binding for all project code. Deviating from them is never permitted.

**1. BaseModel** — all models inherit from `core.models.BaseModel`

```python
class MyModel(BaseModel):
    name = models.CharField(max_length=100)
    # Inherits: id (UUID pk), created_at, updated_at, deleted_at, created_by, soft_delete()
```

**2. Business logic in services.py** — never in views or serializers

```python
# ✅ Correct
# apps/mymodule/services.py
def create_something(plant, user, data):
    obj = MyModel.objects.create(plant=plant, created_by=user, **data)
    log_action(user=user, action_code="mymodule.created", level="L2", entity=obj, payload={...})
    return obj

# ❌ Wrong — logic in the view
def perform_create(self, serializer):
    obj = MyModel.objects.create(...)  # logic here = violation
```

**3. Mandatory audit log** — every relevant action calls `log_action`

```python
from core.audit import log_action
log_action(
    user=request.user,
    action_code="mymodule.entity.action",  # format: app.entity.action
    level="L2",  # L1=security (5 years), L2=compliance (3 years), L3=operational (1 year)
    entity=instance,
    payload={"key": "value"},  # NO PII, only counts/IDs
)
```

**4. Soft delete** — never use `queryset.delete()` directly

```python
# ✅ Correct
instance.soft_delete()

# ❌ Wrong
instance.delete()
MyModel.objects.filter(...).delete()
```

**5. No N+1** — `select_related` and `prefetch_related` are mandatory

```python
# ✅ Correct
queryset = MyModel.objects.select_related("plant", "created_by").prefetch_related("items")

# ❌ Wrong
for obj in MyModel.objects.all():
    print(obj.plant.name)  # N+1!
```

**6. Tasks assigned to a role** (dynamic resolution via `UserPlantAccess`), never to a direct user.

**7. Regulatory frameworks = JSON** in `backend/frameworks/` — do not hardcode controls in source code.

**8. M20 AI Engine**: always call `Sanitizer.sanitize()` before sending to a cloud LLM; human-in-the-loop is required before applying any AI output.

**9. Soft delete manager** is the default — use `.all_with_deleted()` only where explicitly necessary.

**10. Never log PII** — only counts or anonymous identifiers in system logs.

**11. File upload**: always use `validate_uploaded_file()` with MIME check (python-magic).

**12. Production**: use `docker-compose.prod.yml` and `Dockerfile.prod`.

**13. Mandatory translations**: every i18n key added in `it/common.json` or `en/common.json` must be translated at the same time in all 5 languages (IT, EN, FR, PL, TR).

Additional binding principles:

- Framework as data: controls are JSON, not code. Adding DORA does not require a deploy.
- IT/OT table inheritance: `Asset` base + `AssetIT` and `AssetOT` — no unnecessary nullable columns.
- RBAC (M02) separated from regulatory governance (M00): application permissions vs. formal appointments.
- Append-only audit trail with SHA-256 hash chain: technical immutability, not merely procedural.
- Tasks assigned to a role with dynamic resolution: personnel changes do not require manual reallocation.
- Immutable framework versions: archived, never deleted.

### Mandatory patterns with examples

**Complete service pattern:**

```python
# apps/mymodule/services.py
from django.db import transaction
from core.audit import log_action

def create_entity(plant, user, title: str, **kwargs):
    with transaction.atomic():
        entity = MyEntity.objects.create(
            plant=plant,
            title=title,
            created_by=user,
            **kwargs,
        )
        log_action(
            user=user,
            action_code="mymodule.entity.created",
            level="L2",
            entity=entity,
            payload={"title": title[:100]},
        )
    return entity
```

**Celery task with autoretry:**

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def my_scheduled_task(self):
    # task logic
    return "done"
```

**Destroy pattern (soft delete):**

```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()
    instance.soft_delete()
    log_action(
        user=request.user,
        action_code="mymodule.entity.deleted",
        level="L2",
        entity=instance,
        payload={},
    )
    return Response(status=204)
```

### Main data flow

```
BIA.downtime_cost → RiskAssessment.ale_eur (calculated)
RiskAssessment(score > 14) → urgent Task + automatic PDCA
Incident.close() → automatic PDCA + LessonLearned
AuditFinding.close() → automatic PDCA + LessonLearned
BcpTest(failed) → automatic PDCA
PDCA.close() → updates source module + LessonLearned
```

### Development environment setup

#### Prerequisites

```bash
python --version     # >= 3.11
node --version       # >= 20
docker --version     # >= 4.x
```

#### First start

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
python manage.py load_frameworks       # imports VDA ISA, NIS2, ISO 27001
python manage.py seed_demo             # optional demo data
python manage.py createsuperuser

# Start backend
python manage.py runserver 0.0.0.0:8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

#### Makefile commands

```bash
make dev          # docker compose up + runserver + npm run dev
make migrate      # python manage.py migrate
make test         # pytest + jest
make lint         # ruff + eslint
make load-fw      # python manage.py load_frameworks
make seed         # python manage.py seed_demo
make shell        # python manage.py shell_plus
make celery       # start Celery worker in foreground
```

---

## Repository structure

### Backend

```
backend/
├── core/
│   ├── settings/
│   │   ├── base.py          # shared settings (JWT, DRF, INSTALLED_APPS, CELERY)
│   │   ├── dev.py           # development overrides (DEBUG=True, optional SQLite)
│   │   └── prod.py          # production overrides (ALLOWED_HOSTS, SECURE_*, logging)
│   ├── models.py            # BaseModel, SoftDeleteManager
│   ├── audit.py             # log_action(), compute_hash()
│   ├── validators.py        # validate_uploaded_file() with MIME check
│   ├── permissions.py       # ModulePermission, PlantScopedPermission
│   ├── middleware.py        # PlantContextMiddleware, RequestLoggingMiddleware
│   └── urls.py              # root URL conf with include for each app
├── apps/
│   ├── governance/          # M00 — Governance & Roles
│   ├── plants/              # M01 — Plant Registry
│   ├── auth_grc/            # M02 — RBAC + JWT
│   ├── controls/            # M03 — Controls Library + load_frameworks cmd
│   ├── assets/              # M04 — IT/OT Assets
│   ├── bia/                 # M05 — BIA
│   ├── risk/                # M06 — Risk Assessment
│   ├── documents/           # M07 — Documents
│   ├── tasks/               # M08 — Task Management + Compliance Schedule
│   ├── incidents/           # M09 — NIS2 Incidents
│   ├── audit_trail/         # M10 — Audit Trail (read-only views)
│   ├── pdca/                # M11 — PDCA
│   ├── lessons/             # M12 — Lesson Learned
│   ├── management_review/   # M13 — Management Review
│   ├── suppliers/           # M14 — Suppliers
│   ├── training/            # M15 — Training/KnowBe4
│   ├── bcp/                 # M16 — BCP
│   ├── audit_prep/          # M17 — Audit Readiness
│   ├── reporting/           # M18 — Reporting (no model, aggregate views only)
│   ├── notifications/       # M19 — Notifications
│   └── ai_engine/           # M20 — AI Engine + Sanitizer
└── frameworks/
    ├── iso27001.json
    ├── nis2.json
    ├── tisax_l2.json
    └── tisax_l3.json
```

### Module app structure

```
apps/incidents/          # M09 — Incident Management
├── __init__.py
├── admin.py
├── apps.py
├── models.py            # Incident, IncidentNotification, RCA, ...
├── serializers.py       # DRF serializers
├── views.py             # API ViewSet
├── urls.py              # router.register(...)
├── permissions.py       # module-specific permissions
├── services.py          # business logic — not in the view
├── tasks.py             # module Celery tasks
├── signals.py           # post_save, post_delete for audit trail
└── tests/
    ├── test_models.py
    ├── test_api.py
    └── test_services.py
```

### Frontend

```
frontend/src/
├── App.tsx                    # Full router — all routes defined
├── main.tsx                   # Entry point with QueryClientProvider + i18n
├── store/
│   └── auth.ts                # Zustand: user, token, selectedPlant
├── api/
│   ├── client.ts              # axios with JWT interceptor + automatic refresh
│   └── endpoints/             # one file per module (20 files)
├── components/
│   ├── layout/
│   │   ├── Shell.tsx          # Main layout with sidebar
│   │   ├── Sidebar.tsx        # Side navigation with entries for M00–M20
│   │   ├── Topbar.tsx         # Top bar with plant and language selector
│   │   └── BottomBar.tsx      # Mobile bottom bar
│   └── ui/
│       ├── AiSuggestion.tsx   # AI banner with Accept/Edit/Ignore
│       ├── CountdownTimer.tsx # Real-time NIS2 countdown
│       ├── StatusBadge.tsx    # Coloured badge for compliance statuses
│       └── ManualDrawer.tsx   # Contextual manual drawer (? button)
├── modules/                   # One folder per module (M00–M20)
│   ├── dashboard/Dashboard.tsx
│   ├── controls/ControlsList.tsx
│   ├── incidents/IncidentsList.tsx
│   └── ...
├── pages/
│   └── LoginPage.tsx
└── i18n/
    ├── index.ts               # i18next configuration
    ├── it/common.json
    ├── en/common.json
    ├── fr/common.json
    ├── pl/common.json
    └── tr/common.json
```

---

## Main models

### BaseModel

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

    objects = SoftDeleteManager()  # filters deleted_at is null by default

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    class Meta:
        abstract = True
```

All application models inherit from `BaseModel`. Never use `delete()` directly — use `soft_delete()`.

### AuditLog

```python
class AuditLog(models.Model):
    # Does not inherit from BaseModel — no soft delete, no updated_at
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)

    # Who
    user_id = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time = models.CharField(max_length=50)   # role snapshot at the time of the action

    # What
    action_code = models.CharField(max_length=100)        # e.g. incident.created
    level = models.CharField(max_length=2)                # L1 | L2 | L3
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField()                          # relevant data for the action

    # SHA-256 hash chain
    prev_hash = models.CharField(max_length=64)
    record_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'audit_log'
        # partitioned by RANGE (timestamp_utc) — defined in the migration
```

Key properties of AuditLog:

- SHA-256 hash chain: every record has `prev_hash` + `record_hash`
- PostgreSQL trigger prevents UPDATE/DELETE
- `select_for_update()` in `_get_prev_hash()` to prevent race conditions
- Levels L1/L2/L3 with 5/3/1 year retention
- Verification: `python manage.py verify_audit_trail_integrity`

### ControlInstance

- `applicability` field for ISO 27001 SOA
- `calc_maturity_level()` for VDA ISA (scale 0–5)
- `needs_revaluation` for change management (M04)

```python
class ControlInstance(BaseModel):
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    control = models.ForeignKey(Control, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[('compliant','Compliant'),('parziale','Partial'),
                 ('gap','Gap'),('na','N/A'),('non_valutato','Not evaluated')]
    )
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    na_approved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    na_approved_at = models.DateTimeField(null=True)
    na_review_by = models.DateField(null=True)            # max 12 months for TISAX L3
    notes = models.TextField(blank=True)
    last_evaluated_at = models.DateTimeField(null=True)
```

### RiskAssessment

- Inherent vs residual risk (6 IT dimensions + 4 OT dimensions)
- `weighted_score` with BIA multiplier (`downtime_cost`)
- `risk_level`: green ≤7, yellow ≤14, red >14
- Automatic PDCA trigger if score > 14

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
        choices=[('essenziale','Essential'),('importante','Important'),('non_soggetto','Not subject')]
    )
    status = models.CharField(max_length=20)  # active | being_decommissioned | closed

class PlantFramework(BaseModel):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    framework = models.ForeignKey('controls.Framework', on_delete=models.CASCADE)
    active_from = models.DateField()
    level = models.CharField(max_length=10, null=True)  # e.g. L2 or L3 for TISAX

    class Meta:
        unique_together = ['plant', 'framework']
```

### M04 — Asset

```python
class Asset(BaseModel):
    """Base table — table inheritance"""
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10)          # IT | OT
    criticality = models.IntegerField(default=1)          # 1–5, inherited from the process
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
    category = models.CharField(max_length=20)            # PLC | SCADA | HMI | RTU | sensor
    patchable = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone = models.ForeignKey('NetworkZone', null=True, on_delete=models.SET_NULL)
```

### M09 — Incidents

```python
class Incident(BaseModel):
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField()
    detected_at = models.DateTimeField()
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assets = models.ManyToManyField('assets.Asset', blank=True)
    severity = models.CharField(max_length=10)            # low|medium|high|critical
    nis2_notifiable = models.CharField(max_length=15)     # yes|no|to_be_evaluated
    nis2_confirmed_at = models.DateTimeField(null=True)
    nis2_confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    status = models.CharField(max_length=20)              # open|under_analysis|closed
    rca = models.OneToOneField('RCA', null=True, on_delete=models.SET_NULL)

    @property
    def nis2_early_warning_deadline(self):
        return self.created_at + timedelta(hours=24)

    @property
    def nis2_full_notification_deadline(self):
        return self.created_at + timedelta(hours=72)
```

---

## API

### Authentication

```
Authorization: Bearer <JWT-token>
```

JWT tokens have an ACCESS lifetime of 30 minutes. Refresh is performed automatically by the axios interceptor if the user is active (REFRESH=7 days). External auditors use special tokens with a limited scope and expiry (generated by M02).

### URL conventions

```
GET    /api/v1/{module}/                  # list with filters and pagination
POST   /api/v1/{module}/                  # create
GET    /api/v1/{module}/{id}/             # detail
PATCH  /api/v1/{module}/{id}/             # partial update
DELETE /api/v1/{module}/{id}/             # soft delete (deleted_at)

# Custom actions
POST   /api/v1/incidents/{id}/confirm_nis2/
POST   /api/v1/incidents/{id}/send_notification/
POST   /api/v1/documents/{id}/approve/
POST   /api/v1/controls/{id}/evaluate/
```

### Main endpoints

Base URL: `/api/v1/`

| Endpoint | Methods | Description |
|----------|--------|-------------|
| `governance/roles/` | GET, POST, PUT, DELETE | M00 normative roles |
| `plants/` | GET, POST | M01 plant registry |
| `auth/users/` | GET, POST | M02 users |
| `controls/instances/` | GET, PUT | M03 controls |
| `controls/export/` | GET | SOA/VDA/NIS2 export |
| `assets/` | GET, POST | M04 IT/OT assets |
| `bia/processes/` | GET, POST | M05 BIA |
| `risk/assessments/` | GET, POST | M06 risk |
| `documents/` | GET, POST | M07 documents |
| `tasks/` | GET, POST | M08 tasks |
| `incidents/` | GET, POST | M09 incidents |
| `audit-trail/` | GET | M10 audit trail (read-only) |
| `pdca/` | GET, POST | M11 PDCA |
| `lessons/` | GET, POST | M12 lesson learned |
| `management-review/` | GET, POST | M13 management review |
| `suppliers/` | GET, POST | M14 suppliers |
| `training/` | GET, POST | M15 training |
| `bcp/` | GET, POST | M16 BCP |
| `audit-prep/preps/` | GET, POST | M17 audit prep |
| `audit-prep/programs/` | GET, POST | M17 audit programs |
| `reporting/dashboard-summary/` | GET | M18 aggregated dashboard |
| `reporting/kpi-trend/` | GET | M18 KPI trend |
| `notifications/` | GET | M19 notifications |
| `manual/<type>/` | GET | Manuals (user/technical) |

### Filters and pagination

```
GET /api/v1/controls/?framework=VDA_ISA_6_0&plant=PLT-001&status=gap&page=2&page_size=25
```

All list endpoints support:

- `page` and `page_size` (default 25, max 100)
- `ordering` (e.g. `ordering=-created_at`)
- module-specific filters documented in `/api/v1/schema/` (OpenAPI 3.0)

### Standard response

```json
{
  "count": 83,
  "next": "/api/v1/controls/?page=2",
  "previous": null,
  "results": [...]
}
```

### Errors

```json
{
  "error": "validation_error",
  "detail": {
    "status": ["The value 'invalid' is not a valid choice."],
    "owner": ["This field is required."]
  }
}
```

HTTP codes used: 200, 201, 204, 400, 401, 403, 404, 409 (state conflict), 422 (business logic error), 500.

### Compliance export

File downloads require the JWT in the header. Do not use `window.open()` as it does not pass the token.

```typescript
// ✅ Correct — use fetch() with Authorization header
const response = await fetch(
  `/api/v1/controls/export/?framework=ISO27001&format=soa&plant=${plantId}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const blob = await response.blob();

// ❌ Wrong — window.open() does not pass the JWT
window.open(`/api/v1/controls/export/?framework=ISO27001`);
```

### Outbound public API (M19)

```
GET /api/external/v1/plants/           # plant list with nis2_scope
GET /api/external/v1/controls/         # controls with status per plant
GET /api/external/v1/risks/            # open risk assessments

Authentication: API key in header  X-API-Key: <key>
Rate limit: 100 req/min per key
```

---

## Security

### JWT configuration

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

### Throttling

Basic throttling uses `AnonRateThrottle` and `UserRateThrottle`:

- `AnonRateThrottle`: 20/h
- `UserRateThrottle`: 500/h
- `LoginRateThrottle`: 5/min (on `GrcTokenObtainPairView`)

Customisable for sensitive endpoints by overriding `throttle_classes` in the ViewSet.

### Secure file upload

```python
from core.validators import validate_uploaded_file

# Verifies: size + extension whitelist + actual MIME type (python-magic)
validate_uploaded_file(request.FILES["file"])
```

### SMTP credential encryption

```python
# EncryptedCharField uses Fernet AES-256
# FERNET_KEY is mandatory in .env — no secure default
class EmailConfiguration(BaseModel):
    smtp_password = EncryptedCharField(max_length=500)
```

### Password policy

- Minimum 12 characters
- `CommonPasswordValidator`
- `NumericPasswordValidator`
- `UserAttributeSimilarityValidator`

### Service endpoints

Some administrative endpoints (e.g. test DB reset in `auth_grc.ResetTestDbView`) are explicitly blocked in production via a check on `settings.DEBUG` to prevent misuse outside test environments.

---

## Privacy and GDPR

### User anonymisation (Art. 17 GDPR)

```python
from apps.auth_grc.services import anonymize_user

anonymize_user(user_id)
# Removes name, email, phone — preserves audit trail integrity
# Endpoint: POST /api/v1/auth/users/{id}/anonymize/
```

### AI Sanitizer

```python
from apps.ai_engine.sanitizer import Sanitizer

safe_text = Sanitizer.sanitize(raw_text)
# Removes: email, IP, VAT number, tax code, phone, plant names
# ALWAYS use before sending to a cloud LLM
```

### Automatic audit log retention

- L1 (security): 5 years
- L2 (compliance): 3 years
- L3 (operational): 1 year
- Scheduled: 1st of each month at 03:00 (task `cleanup_expired_audit_logs`)

---

## Audit trail — append-only with hash chain

### Principle

Every relevant action writes an `AuditLog` record. The record is immutable: the PostgreSQL trigger rejects UPDATE and DELETE. Each record contains `prev_hash` and `record_hash = SHA256(json_payload + prev_hash)`, forming a verifiable chain.

### How to log an action

```python
from core.audit import log_action

# In a service or a post_save signal
log_action(
    request=request,            # to extract the current user and role
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

The `core.audit` module automatically handles:

- `user_role_at_time` snapshot at the time of the call
- `prev_hash` calculation (reads the last record for entity_type) and `record_hash`
- Transactional write with `select_for_update()` to prevent race conditions
- If the log fails, an exception is raised (the transaction is rolled back)

### Integrity verification

```bash
# Checks the entire chain: recalculates every hash and compares
python manage.py verify_audit_trail_integrity

# Finds the first corrupted record
python manage.py verify_audit_trail_integrity --verbose

# Nightly job (Celery Beat — already configured)
# Sends an alert if the chain is broken
```

---

## Audit Preparation — technical logic

### suggest_audit_plan()

- Prioritises domains with open gaps (highest `gap_pct`)
- Deterministic seed (MD5 hash of `program_id` + `quarter`) for a reproducible sample across executions
- Cross-framework domain deduplication via the `seen_domains` dictionary
- Sample distribution: `campione`=25%, `esteso`=50%, `full`=100%

### launch_audit_from_program()

- `transaction.atomic()` — fully atomic operation
- `bulk_create` for EvidenceItem (a single INSERT instead of N)
- `sync_program_completion()` called automatically in `perform_update()`

### Reminder task (check_upcoming_audits)

- ±4-day range to handle weekly task vs mid-week dates
- 28–32 days before: preparation task
- 5–9 days before: urgent task if AuditPrep not yet started
- 0–3 days after the date: critical alert if AuditPrep not started

---

## Compliance Schedule (M08)

### Deadline calculation

```python
from apps.compliance_schedule.services import get_due_date

due = get_due_date("finding_major", plant=plant, from_date=date.today())
# 23 configurable rule types from the admin UI
```

---

## Adding a regulatory framework

Frameworks are JSON files in `backend/frameworks/`. No Python code changes are needed.

### JSON structure

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
      "relationship": "equivalent"
    }
  ]
}
```

### Import

```bash
# Import the new framework
python manage.py load_frameworks --file frameworks/nist_csf_2_0.json

# The command:
# 1. Creates the Framework and all Controls
# 2. Creates ControlMappings with the other frameworks
# 3. Does NOT generate ControlInstances (these are generated when the framework is activated on a plant)

# Activate the framework on a plant (via admin or API)
POST /api/v1/plant-frameworks/
{ "plant": "PLT-001", "framework": "NIST_CSF_2_0", "active_from": "2026-03-13" }
# → automatically generates ControlInstances in non_valutato state for every control
```

### Framework versioning

When a new version of an existing framework is released:

1. Create a new JSON file with the same `code` but an updated `version` (e.g. `VDA_ISA_6_1`)
2. The `load_frameworks --version-update` command compares the controls:
   - Unchanged: migrated automatically with the same status
   - Modified: new `ControlInstance` records are created in `non_valutato` state with a review task
   - Deleted: archived (`archived_at`) with a note
   - New: created in `non_valutato` state

The previous version is never deleted — it remains archived for historical audits.

---

## Adding a module

To add a new functional module (e.g. M21):

```bash
# 1. Create the Django app
cd backend
python manage.py startapp new_module apps/new_module

# 2. Add to INSTALLED_APPS in core/settings/base.py
INSTALLED_APPS = [
    ...
    'apps.new_module',
]

# 3. Register the URLs in backend/core/urls.py
path('api/v1/new-module/', include('apps.new_module.urls')),
```

Mandatory minimum structure:

```
apps/new_module/
  models.py        — inherit from BaseModel
  serializers.py
  views.py         — ViewSet with permissions
  urls.py          — router.register
  services.py      — business logic
  tasks.py         — Celery tasks if needed
  signals.py       — for audit trail
  tests/
```

**Checklist for every new module:**

- [ ] All models inherit from `BaseModel` (UUID, soft delete, timestamps)
- [ ] Every relevant action calls `log_action()` in the service
- [ ] Views use `ModulePermission` for access control
- [ ] Tests are present for models, API and service (coverage >= 70%)
- [ ] Action codes are registered in the catalogue `core/audit/action_codes.py`
- [ ] UI label translations are added to the i18n files in `frontend/src/i18n/` in all 5 languages

---

## AI Engine M20 — technical integration

### Module architecture

```
apps/ai_engine/
├── sanitizer.py        # PII anonymisation before cloud
├── router.py           # local vs cloud selection based on the function
├── functions/
│   ├── classification.py
│   ├── text_analysis.py
│   ├── draft_generation.py
│   └── anomaly_detection.py
├── models.py           # AiInteractionLog
├── tasks.py            # async anomaly detection jobs
└── tests/
```

### AiInteractionLog

```python
class AiInteractionLog(BaseModel):
    function = models.CharField(max_length=50)
    # classification | text_analysis | draft_generation | anomaly_detection
    module_source = models.CharField(max_length=5)       # M04, M07, M09...
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)        # e.g. gpt-4o | llama3.1:8b
    input_hash = models.CharField(max_length=64)         # SHA256 of the prompt — never the text itself
    output_ai = models.TextField()                       # raw model output
    output_human_final = models.TextField(null=True)     # after human confirmation/edit
    delta = models.JSONField(null=True)                  # diff between output_ai and output_human_final
    confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(null=True)
    ignored = models.BooleanField(default=False)         # suggestion ignored by the user
```

`AiInteractionLog` is registered in M10 via `log_action()` with `action_code='ai.suggestion.confirmed'` or `'ai.suggestion.ignored'`.

### Sanitizer

```python
# apps/ai_engine/sanitizer.py
class Sanitizer:
    """
    Anonymises the context before sending it to the cloud LLM.
    Maps tokens to real values for de-anonymising the result.
    """

    def sanitize(self, context: dict) -> tuple[dict, dict]:
        """
        Returns: (sanitized_context, token_map)
        token_map: { "[PLANT_A]": "Milan Plant", ... }
        """
        ...

    def desanitize(self, text: str, token_map: dict) -> str:
        """Replaces tokens with real values in the generated text."""
        ...
```

### Calling an AI function from a service

```python
from apps.ai_engine.functions.classification import classify_incident_severity

# In the M09 service — incidents/services.py
async def suggest_severity(incident: Incident, request) -> dict | None:
    if not settings.AI_ENGINE_CONFIG['functions']['classification']['enabled']:
        return None

    result = await classify_incident_severity(
        description=incident.description,
        assets=[a.name for a in incident.assets.all()],
        plant_type=incident.plant.nis2_scope,
    )
    # result = { "suggested_severity": "high", "confidence": 0.87, "reasoning": "..." }

    # Shown to the user as a suggestion — not applied automatically
    return result
```

### Human-in-the-loop — API flow

```
POST /api/v1/ai/suggest/
{ "function": "classification", "entity_type": "incident", "entity_id": "..." }

→ 200 { "suggestion_id": "...", "output": { "suggested_severity": "high" } }

# User accepts, edits or ignores
POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": true, "final_value": "high" }
# → updates AiInteractionLog.confirmed_by and .output_human_final
# → applies the value to the entity

POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": false }
# → AiInteractionLog.ignored = True
# → no effect on the entity
```

---

## External integrations

### KnowBe4 (M15)

```python
# apps/training/kb4_client.py
class KnowBe4Client:
    BASE_URL = settings.KNOWBE4_API_URL

    def get_enrollments_delta(self, since: datetime) -> list[dict]:
        """Downloads completions since the given timestamp."""
        ...

    def get_phishing_results(self, campaign_id: str) -> list[dict]:
        ...

    def provision_user(self, user: User, groups: list[str]) -> bool:
        """Creates or updates the user on KB4 with the correct groups (role+plant+language)."""
        ...

    def deprovision_user(self, email: str) -> bool:
        """Revokes user access on KB4 (called by the post_save signal on User.is_active=False)."""
        ...
```

The sync is executed by the Celery task `training.tasks.sync_knowbe4` scheduled every night at 02:00.

### Outbound webhook (M19)

```python
# Webhook payload structure
{
  "event": "risk.red_threshold_exceeded",
  "timestamp": "2026-03-13T10:00:00Z",
  "plant_id": "PLT-001",
  "plant_name": "...",              # included only if the recipient has access
  "data": {
    "risk_id": "...",
    "score": 18,
    "asset_ids": ["..."]
  },
  "signature": "sha256=..."         # HMAC-SHA256 with the configured key
}
```

---

## i18n — internationalisation

### Backend — Django i18n

```python
# In a model or service — do not use hardcoded strings
from django.utils.translation import gettext_lazy as _

class ControlInstance(BaseModel):
    status = models.CharField(
        choices=[
            ('compliant', _('Compliant')),
            ('gap', _('Gap')),
        ]
    )
```

Backend translations are in `backend/locale/{language}/LC_MESSAGES/django.po`:

```bash
python manage.py makemessages -l pl
# Edit locale/pl/LC_MESSAGES/django.po
python manage.py compilemessages
```

### Frontend — i18next

Translation files:

```
frontend/src/i18n/
├── it/common.json
├── en/common.json
├── fr/common.json
├── pl/common.json
└── tr/common.json
```

Namespace file structure:

```json
{
  "status": {
    "compliant": "Compliant",
    "gap": "Gap",
    "parziale": "Partial",
    "na": "N/A",
    "non_valutato": "Not evaluated"
  },
  "actions": {
    "save": "Save",
    "approve": "Approve"
  }
}
```

Usage in a React component:

```typescript
import { useTranslation } from "react-i18next"

function ControlStatus({ status }: { status: string }) {
  const { t } = useTranslation()
  return <span>{t(`status.${status}`)}</span>
}
```

**Rule**: every key added in `it/common.json` or `en/common.json` must be added at the same time in all 5 files. Never leave keys missing in any language.

### Controls — translations in the framework JSON

```json
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

The serializer automatically returns the translation in the requester's language:

```python
# controls/serializers.py
def get_title(self, obj):
    lang = self.context['request'].user.profile.language  # it | en | fr | pl | tr
    return obj.translations.get(lang, {}).get('title') or obj.translations['en']['title']
```

---

## Frontend

### State management

```typescript
import { useAuthStore } from "../store/auth"

const { user, token, selectedPlant } = useAuthStore()
```

### TanStack Query

```typescript
const { data, isLoading } = useQuery({
  queryKey: ["audit-preps", plantId],
  queryFn: () => apiClient.get("/audit-prep/preps/").then(r => r.data),
})
```

Automatic cache, invalidation on mutation, exponential retry on network errors.

### API client with automatic refresh

```typescript
// api/client.ts — JWT interceptor
apiClient.interceptors.response.use(
  r => r,
  async error => {
    if (error.response?.status === 401) {
      // automatic token refresh via /api/auth/token/refresh/
      // if refresh fails, logout and redirect to /login
    }
  }
)
```

### Internationalisation

```typescript
import { useTranslation } from "react-i18next"

const { t } = useTranslation()
// File: frontend/src/i18n/{it,en,fr,pl,tr}/common.json
// Rule: add in ALL 5 languages at the same time
```

---

## Tests

### Running tests

```bash
# Full backend suite
docker compose exec backend pytest
docker compose exec backend pytest --cov=apps --cov-report=html

# Single module test
docker compose exec backend pytest apps/audit_prep/

# Fast tests only (no DB)
pytest -m "not slow" tests/unit/

# Frontend
cd frontend && npm test
```

### Structure

```
apps/{module}/tests/
  test_models.py     — unit tests for models and services
  test_api.py        — API endpoint tests with APIClient
  test_services.py   — isolated business logic tests
```

### Standard fixtures

```python
# conftest.py — available in all tests
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

### Audit trail test

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
    # Verify hash chain
    assert log.record_hash == compute_hash(log.payload, log.prev_hash)
```

### Coverage target: >= 70%

Modules with existing tests: `auth_grc`, `governance`, `controls`, `audit_trail`

Modules to cover: `risk`, `incidents`, `pdca`, `audit_prep`, `notifications`

---

## Management commands

| Command | Description | When to run |
|---------|-------------|-----------------|
| `migrate` | Apply DB migrations | After every deploy |
| `load_frameworks` | Import regulatory framework JSON | Initial setup + framework update |
| `load_notification_profiles` | Default notification profiles | Initial setup |
| `load_competency_requirements` | M15 competency requirements | Initial setup |
| `load_required_documents` | Mandatory documents | Initial setup |
| `verify_audit_trail_integrity` | Verify audit trail hash chain | Monthly + after restore |
| `check --deploy` | Verify production configuration | Before every deploy |
| `createsuperuser` | Create the first admin | Initial setup |
| `seed_demo` | Load demo data | Development environment only |
| `makemessages -l <lang>` | Extract backend i18n strings | After adding new strings |
| `compilemessages` | Compile .po files to .mo | After translation |
| `sync_knowbe4 --full` | Manual KnowBe4 sync | Recovery after error |

---

## Environment variables

| Name | Type | Dev default | Description | Required |
|------|------|------------|-------------|-------------|
| `SECRET_KEY` | string | — | Django cryptographic key | Yes |
| `FERNET_KEY` | string | — | AES-256 for SMTP credentials | Yes |
| `DEBUG` | bool | True | False in production | No |
| `ALLOWED_HOSTS` | string | localhost | Allowed hosts (comma-separated) | Yes in prod |
| `DATABASE_URL` | string | postgresql://grc:grc@db:5432/grc_dev | PostgreSQL URL | Yes |
| `REDIS_URL` | string | redis://redis:6379/0 | Redis URL | Yes |
| `FRONTEND_URL` | string | http://localhost:3001 | Frontend URL | Yes |
| `CORS_ALLOWED_ORIGINS` | string | http://localhost:3001 | CORS origins | No |
| `AI_ENGINE_ENABLED` | bool | False | Enable M20 AI Engine | No |
| `KNOWBE4_API_KEY` | string | — | KnowBe4 API key | Only if M15 is active |

---

## Development conventions

### Git

- Branch: `feature/M{nn}-description`, `fix/M{nn}-bug-description`, `chore/description`
- Commit: `feat(M09): add NIS2 timer with visible countdown`
- One branch = one module or one coherent feature
- No direct commits to `main` or `develop`

### Python / Django

- Formatter: `ruff format` (black-compatible)
- Linter: `ruff check`
- Type hints on all services and external clients
- Docstring mandatory on classes and public methods
- No business logic in views — everything in `services.py`
- No N+1 queries — use `select_related` and `prefetch_related`

### React / TypeScript

- TypeScript on all components
- No explicit `any`
- Presentation components separated from container components
- API calls go in custom hooks (`useIncident`, `useControls`)
- Formatter: Prettier
- Linter: ESLint

### Security

- No credentials in source code
- No sensitive data in logs (use hashing or masking)
- CSRF token on all mutations
- Rate limiting on public endpoints and on M20 AI
- Input validation in serializers — never trust the client

---

## Troubleshooting

### Celery Beat not executing scheduled tasks

```bash
# Verify that the beat is running
docker compose ps celery-beat
# If not up: docker compose restart celery-beat

# Check the status of planned tasks
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(PeriodicTask.objects.filter(enabled=True).values('name','last_run_at'))"
```

### Audit trail integrity check fails

A failure indicates that a record has been modified or that the chain has been broken. Do not attempt to repair it — contact the security team. The system automatically generates a P1 alert.

```bash
# Find the first corrupted record
python manage.py verify_audit_trail_integrity --verbose
```

### Framework import fails

```bash
python manage.py load_frameworks --file frameworks/nuovo.json --dry-run
# Shows the differences without applying them

python manage.py load_frameworks --file frameworks/nuovo.json --validate-only
# Validates the JSON without importing
```

### KnowBe4 sync fails

```bash
# Verify credentials
python manage.py shell -c "from apps.training.kb4_client import KnowBe4Client; print(KnowBe4Client().health_check())"

# Re-run the sync manually
python manage.py sync_knowbe4 --full
```

### AI cloud token unauthorised (M20)

1. Verify that `AI_ENGINE_ENABLED=true` and that the specific function is enabled in `AI_ENGINE_CONFIG`
2. Check that the API key is configured and has not expired
3. Verify that the sanitizer is not generating errors: `grep "sanitizer" logs/app.log | tail -20`
4. In the event of a persistent error, the system falls back to the local model if available

### Migration fails in production

```bash
# Verify migration status before applying
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Apply with verbose output
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate --verbosity=2

# In the event of a stuck migration, check for DB locks
# Connect to PostgreSQL and check pg_stat_activity
```

### Frontend does not receive the refreshed token

Verify that the `refresh_token` cookie has not expired and that the domain matches. In development, ensure that `CORS_ALLOW_CREDENTIALS = True` and that `FRONTEND_URL` is set correctly.

### Health check fails

```bash
# Check service status
curl http://localhost:8001/api/health/
# Expected response: {"status": "ok", "db": "ok"}

# If db=error, check the PostgreSQL connection
docker compose ps db
docker compose logs db --tail=20
```
