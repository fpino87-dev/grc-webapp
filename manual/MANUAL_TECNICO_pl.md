# Podręcznik Techniczny — GRC Platform

> Przewodnik dla programistów: architektura, modele danych, API, frameworki normatywne, AI Engine, testy i konwencje.

---

## Spis treści

- [Stos technologiczny i wersje](#stos-technologiczny-i-wersje)
- [Architektura](#architektura)
- [Struktura repozytorium](#struktura-repozytorium)
- [Główne modele](#główne-modele)
- [API](#api)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Prywatność i RODO](#prywatność-i-rodo)
- [Audit trail — append-only z łańcuchem hashy](#audit-trail--append-only-z-łańcuchem-hashy)
- [Audit Preparation — logika techniczna](#audit-preparation--logika-techniczna)
- [Compliance Schedule (M08)](#compliance-schedule-m08)
- [Dodawanie frameworku normatywnego](#dodawanie-frameworku-normatywnego)
- [Dodawanie modułu](#dodawanie-modułu)
- [AI Engine M20 — integracja techniczna](#ai-engine-m20--integracja-techniczna)
- [Integracje zewnętrzne](#integracje-zewnętrzne)
- [i18n — internacjonalizacja](#i18n--internacjonalizacja)
- [Frontend](#frontend)
- [Testy](#testy)
- [Komendy zarządzania](#komendy-zarządzania)
- [Zmienne środowiskowe](#zmienne-środowiskowe)
- [Konwencje programistyczne](#konwencje-programistyczne)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Stos technologiczny i wersje

| Komponent | Technologia | Wersja |
|-----------|-----------|---------|
| Runtime backend | Python | 3.11 |
| Framework webowy | Django | 5.1 |
| API REST | Django REST Framework | 3.15 |
| Kolejka zadań | Celery | 5.x |
| Cache/Broker | Redis | 7 |
| Baza danych | PostgreSQL | 16 (Docker dev) |
| Serwer produkcyjny | Gunicorn | — |
| Framework frontend | React | 18.3 |
| Narzędzie budowania | Vite | 5.4 |
| CSS | Tailwind CSS | 3.4 |
| Zarządzanie stanem | Zustand | 5.0 |
| Pobieranie danych | TanStack Query | 5.56 |
| Router | React Router | 7 |
| i18n frontend | i18next | 23.10 |
| Markdown | react-markdown | 9.0 |
| Konteneryzacja | Docker Compose | v2 |

---

## Architektura

### Przepływ architektoniczny

```
frontend (React SPA)
    │  REST JSON / JWT
    ▼
backend (Django + DRF)
    │
    ├── apps/          jedna aplikacja Django na moduł (M00–M20)
    ├── core/          settings, middleware, modele bazowe, auth
    └── frameworks/    JSON frameworki normatywne (VDA ISA, NIS2, ISO 27001)
    │
    ├── PostgreSQL     główna baza danych + audit trail append-only
    ├── Redis          cache sesji + broker Celery
    └── S3 / MinIO     object storage dokumentów i dowodów
    │
    └── Celery Worker  zadania asynchroniczne: powiadomienia, sync KB4, zadania audit trail
        Celery Beat    harmonogram cykliczny: terminy, digest email, sync
```

### Zasady architektoniczne (z CLAUDE.md)

Poniższe zasady są wiążące dla całego kodu projektu. Nigdy nie wolno od nich odstępować.

**1. BaseModel** — wszystkie modele dziedziczą po `core.models.BaseModel`

```python
class MyModel(BaseModel):
    name = models.CharField(max_length=100)
    # Dziedziczy: id (UUID pk), created_at, updated_at, deleted_at, created_by, soft_delete()
```

**2. Logika biznesowa w services.py** — nigdy w widokach ani serializerach

```python
# ✅ Poprawnie
# apps/mymodule/services.py
def create_something(plant, user, data):
    obj = MyModel.objects.create(plant=plant, created_by=user, **data)
    log_action(user=user, action_code="mymodule.created", level="L2", entity=obj, payload={...})
    return obj

# ❌ Błędnie — logika w widoku
def perform_create(self, serializer):
    obj = MyModel.objects.create(...)  # logika tutaj = naruszenie zasady
```

**3. Obowiązkowy audit log** — każda istotna akcja wywołuje `log_action`

```python
from core.audit import log_action
log_action(
    user=request.user,
    action_code="mymodule.entity.action",  # format: app.entity.action
    level="L2",  # L1=bezpieczeństwo (5 lat), L2=compliance (3 lata), L3=operacyjne (1 rok)
    entity=instance,
    payload={"key": "value"},  # BEZ PII, tylko liczby/ID
)
```

**4. Soft delete** — nigdy bezpośrednio `queryset.delete()`

```python
# ✅ Poprawnie
instance.soft_delete()

# ❌ Błędnie
instance.delete()
MyModel.objects.filter(...).delete()
```

**5. Brak N+1** — `select_related` i `prefetch_related` są obowiązkowe

```python
# ✅ Poprawnie
queryset = MyModel.objects.select_related("plant", "created_by").prefetch_related("items")

# ❌ Błędnie
for obj in MyModel.objects.all():
    print(obj.plant.name)  # N+1!
```

**6. Zadania przypisane do roli** (dynamiczne rozwiązywanie przez `UserPlantAccess`), nigdy bezpośrednio do użytkownika.

**7. Frameworki normatywne = JSON** w `backend/frameworks/` — nie kodować kontroli na stałe w kodzie.

**8. M20 AI Engine**: zawsze `Sanitizer.sanitize()` przed wysłaniem do chmurowego LLM; human-in-the-loop przed zastosowaniem jakiegokolwiek wyjścia AI.

**9. Menedżer soft delete** jest domyślny — `.all_with_deleted()` tylko tam, gdzie jest to wyraźnie konieczne.

**10. Nigdy nie logować PII** — w logach systemowych tylko liczby lub anonimowe identyfikatory.

**11. Upload plików**: zawsze `validate_uploaded_file()` z kontrolą MIME (python-magic).

**12. Produkcja**: `docker-compose.prod.yml` i `Dockerfile.prod`.

**13. Obowiązkowe tłumaczenia**: każdy klucz i18n dodany w `it/common.json` lub `en/common.json` musi być jednocześnie przetłumaczony na wszystkie 5 języków (IT, EN, FR, PL, TR).

Dodatkowe wiążące zasady:

- Framework as data: kontrole są w JSON, nie w kodzie. Dodanie DORA nie wymaga deployu.
- Dziedziczenie tabel IT/OT: `Asset` bazowy + `AssetIT` i `AssetOT` — żadnych zbędnych kolumn nullable.
- RBAC (M02) oddzielony od zarządzania normatywnego (M00): uprawnienia aplikacyjne vs. formalne mianowania.
- Audit trail append-only z łańcuchem hashy SHA-256: niezmienność techniczna, nie tylko proceduralna.
- Zadania przypisane do roli z dynamicznym rozwiązywaniem: zmiana personelu nie wymaga ręcznej realokacji.
- Wersje frameworków są niezmienne: archiwizowane, nigdy nie usuwane.

### Obowiązkowe wzorce z przykładami

**Kompletny wzorzec service:**

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

**Zadanie Celery z autoretry:**

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def my_scheduled_task(self):
    # logika zadania
    return "done"
```

**Wzorzec Destroy (soft delete):**

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

### Główny przepływ danych

```
BIA.downtime_cost → RiskAssessment.ale_eur (obliczony)
RiskAssessment(score > 14) → Zadanie pilne + automatyczny PDCA
Incident.close() → automatyczne PDCA + LessonLearned
AuditFinding.close() → automatyczne PDCA + LessonLearned
BcpTest(nieudany) → automatyczny PDCA
PDCA.close() → aktualizuje moduł źródłowy + LessonLearned
```

### Konfiguracja środowiska deweloperskiego

#### Wymagania wstępne

```bash
python --version     # >= 3.11
node --version       # >= 20
docker --version     # >= 4.x
```

#### Pierwsze uruchomienie

```bash
git clone https://github.com/fpino87-dev/grc-webapp.git
cd grc-webapp

# Backend
cp .env.example .env
docker compose up -d db redis

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py load_frameworks       # importuje VDA ISA, NIS2, ISO 27001
python manage.py seed_demo             # opcjonalne dane demo
python manage.py createsuperuser

# Uruchom backend
python manage.py runserver 0.0.0.0:8000

# Frontend (w innym terminalu)
cd frontend
npm install
npm run dev
```

#### Komendy Makefile

```bash
make dev          # docker compose up + runserver + npm run dev
make migrate      # python manage.py migrate
make test         # pytest + jest
make lint         # ruff + eslint
make load-fw      # python manage.py load_frameworks
make seed         # python manage.py seed_demo
make shell        # python manage.py shell_plus
make celery       # uruchamia worker Celery na pierwszym planie
```

---

## Struktura repozytorium

### Backend

```
backend/
├── core/
│   ├── settings/
│   │   ├── base.py          # współdzielone ustawienia (JWT, DRF, INSTALLED_APPS, CELERY)
│   │   ├── dev.py           # nadpisania dla dev (DEBUG=True, opcjonalny SQLite)
│   │   └── prod.py          # nadpisania dla prod (ALLOWED_HOSTS, SECURE_*, logging)
│   ├── models.py            # BaseModel, SoftDeleteManager
│   ├── audit.py             # log_action(), compute_hash()
│   ├── validators.py        # validate_uploaded_file() z kontrolą MIME
│   ├── permissions.py       # ModulePermission, PlantScopedPermission
│   ├── middleware.py        # PlantContextMiddleware, RequestLoggingMiddleware
│   └── urls.py              # główny URL z include dla każdej aplikacji
├── apps/
│   ├── governance/          # M00 — Governance i Role
│   ├── plants/              # M01 — Rejestr Plant
│   ├── auth_grc/            # M02 — RBAC + JWT
│   ├── controls/            # M03 — Biblioteka Kontroli + komenda load_frameworks
│   ├── assets/              # M04 — Zasoby IT/OT
│   ├── bia/                 # M05 — BIA
│   ├── risk/                # M06 — Ocena Ryzyka
│   ├── documents/           # M07 — Dokumenty
│   ├── tasks/               # M08 — Zarządzanie Zadaniami + Compliance Schedule
│   ├── incidents/           # M09 — Incydenty NIS2
│   ├── audit_trail/         # M10 — Audit Trail (widoki tylko do odczytu)
│   ├── pdca/                # M11 — PDCA
│   ├── lessons/             # M12 — Lesson Learned
│   ├── management_review/   # M13 — Przegląd Zarządzania
│   ├── suppliers/           # M14 — Dostawcy
│   ├── training/            # M15 — Szkolenia/KnowBe4
│   ├── bcp/                 # M16 — BCP
│   ├── audit_prep/          # M17 — Gotowość Audytowa
│   ├── reporting/           # M18 — Raportowanie (brak modelu, tylko zagregowane widoki)
│   ├── notifications/       # M19 — Powiadomienia
│   └── ai_engine/           # M20 — AI Engine + Sanitizer
└── frameworks/
    ├── iso27001.json
    ├── nis2.json
    ├── tisax_l2.json
    └── tisax_l3.json
```

### Struktura aplikacji modułowej

```
apps/incidents/          # M09 — Zarządzanie Incydentami
├── __init__.py
├── admin.py
├── apps.py
├── models.py            # Incident, IncidentNotification, RCA, ...
├── serializers.py       # serializery DRF
├── views.py             # ViewSet API
├── urls.py              # router.register(...)
├── permissions.py       # uprawnienia specyficzne dla modułu
├── services.py          # logika biznesowa — nie w widoku
├── tasks.py             # zadania Celery modułu
├── signals.py           # post_save, post_delete dla audit trail
└── tests/
    ├── test_models.py
    ├── test_api.py
    └── test_services.py
```

### Frontend

```
frontend/src/
├── App.tsx                    # Router — moduły, harmonogram, ustawienia
├── main.tsx                   # Punkt wejścia z QueryClientProvider + i18n
├── store/
│   └── auth.ts                # Zustand: user, token, selectedPlant
├── api/
│   ├── client.ts              # axios z interceptorem JWT + automatycznym odświeżaniem
│   └── endpoints/             # klient API TypeScript (~24 pliki)
├── components/
│   ├── layout/
│   │   ├── Shell.tsx          # Główny layout z paskiem bocznym
│   │   ├── Sidebar.tsx        # Boczna nawigacja z pozycjami dla M00–M20
│   │   ├── Topbar.tsx         # Górny pasek z wyborem plant i języka
│   │   └── BottomBar.tsx      # Dolny pasek mobilny
│   └── ui/
│       ├── AiSuggestion.tsx   # Baner AI z przyciskami Accept/Edit/Ignore
│       ├── CountdownTimer.tsx # Odliczanie NIS2 w czasie rzeczywistym
│       ├── StatusBadge.tsx    # Kolorowa odznaka dla stanów compliance
│       └── ManualDrawer.tsx   # Kontekstowa szuflada instrukcji (przycisk ?)
├── modules/                   # Jeden folder na moduł (M00–M20)
│   ├── dashboard/Dashboard.tsx
│   ├── controls/ControlsList.tsx
│   ├── incidents/IncidentsList.tsx
│   └── ...
├── pages/
│   └── LoginPage.tsx
└── i18n/
    ├── index.ts               # konfiguracja i18next
    ├── it/common.json
    ├── en/common.json
    ├── fr/common.json
    ├── pl/common.json
    └── tr/common.json
```

---

## Główne modele

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

    objects = SoftDeleteManager()  # domyślnie filtruje deleted_at is null

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    class Meta:
        abstract = True
```

Wszystkie modele aplikacji dziedziczą po `BaseModel`. Nigdy nie używać bezpośrednio `delete()` — używać `soft_delete()`.

### AuditLog

```python
class AuditLog(models.Model):
    # Nie dziedziczy po BaseModel — nie ma soft delete, nie ma updated_at
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)

    # Kto
    user_id = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time = models.CharField(max_length=50)   # snapshot roli w chwili zapisu

    # Co
    action_code = models.CharField(max_length=100)        # np. incident.created
    level = models.CharField(max_length=2)                # L1 | L2 | L3
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField()                          # istotne dane akcji

    # Łańcuch hashy SHA-256
    prev_hash = models.CharField(max_length=64)
    record_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'audit_log'
        # partitioned by RANGE (timestamp_utc) — zdefiniowane w migracji
```

Kluczowe właściwości AuditLog:

- Łańcuch hashy SHA-256: każdy rekord ma `prev_hash` + `record_hash`
- Trigger PostgreSQL uniemożliwia UPDATE/DELETE
- `select_for_update()` w `_get_prev_hash()` zapobiega wyścigowi warunków (race condition)
- Poziomy L1/L2/L3 z retencją 5/3/1 lat
- Weryfikacja: `python manage.py verify_audit_trail_integrity`

### ControlInstance

- Pole `applicability` dla SOA ISO 27001
- `calc_maturity_level()` dla VDA ISA (skala 0-5)
- `needs_revaluation` dla zarządzania zmianami (M04)

```python
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
    na_review_by = models.DateField(null=True)            # max 12 miesięcy dla TISAX L3
    notes = models.TextField(blank=True)
    last_evaluated_at = models.DateTimeField(null=True)
```

### RiskAssessment

- Ryzyko wrodzone vs. resztkowe (6 wymiarów IT + 4 OT)
- `weighted_score` z mnożnikiem BIA (`downtime_cost`)
- `risk_level`: zielony ≤7, żółty ≤14, czerwony >14
- Automatyczne uruchomienie PDCA jeśli score > 14

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

### M01 — Rejestr Plant

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
    level = models.CharField(max_length=10, null=True)  # np. L2 lub L3 dla TISAX

    class Meta:
        unique_together = ['plant', 'framework']
```

### M04 — Zasoby (Assets)

```python
class Asset(BaseModel):
    """Tabela bazowa — dziedziczenie tabel"""
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10)          # IT | OT
    criticality = models.IntegerField(default=1)          # 1–5, dziedziczona z procesu
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
    category = models.CharField(max_length=20)            # PLC | SCADA | HMI | RTU | czujnik
    patchable = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone = models.ForeignKey('NetworkZone', null=True, on_delete=models.SET_NULL)
```

### M09 — Incydenty

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

## API

### Uwierzytelnianie

```
Authorization: Bearer <JWT-token>
```

Tokeny JWT mają ważność ACCESS=30min. Odświeżanie odbywa się automatycznie przez interceptor axios, gdy użytkownik jest aktywny (REFRESH=7 dni). Audytorzy zewnętrzni używają specjalnych tokenów z ograniczonym zakresem i terminem ważności (generowane przez M02).

### Konwencje URL

```
GET    /api/v1/{modul}/                  # lista z filtrami i paginacją
POST   /api/v1/{modul}/                  # tworzenie
GET    /api/v1/{modul}/{id}/             # szczegóły
PATCH  /api/v1/{modul}/{id}/             # częściowa aktualizacja
DELETE /api/v1/{modul}/{id}/             # soft delete (deleted_at)

# Akcje niestandardowe
POST   /api/v1/incidents/{id}/confirm_nis2/
POST   /api/v1/incidents/{id}/send_notification/
POST   /api/v1/documents/{id}/approve/
POST   /api/v1/controls/{id}/evaluate/
```

### Główne endpointy

Bazowy URL: `/api/v1/`

| Endpoint | Metody | Opis |
|----------|--------|------|
| `governance/roles/` | GET, POST, PUT, DELETE | Role normatywne M00 |
| `plants/` | GET, POST | Rejestr plant M01 |
| `auth/users/` | GET, POST | Użytkownicy M02 |
| `controls/instances/` | GET, PUT | Kontrole M03 |
| `controls/export/` | GET | Eksport SOA/VDA/NIS2 |
| `assets/` | GET, POST | Zasoby IT/OT M04 |
| `bia/processes/` | GET, POST | BIA M05 |
| `risk/assessments/` | GET, POST | Ryzyko M06 |
| `documents/` | GET, POST | Dokumenty M07 |
| `tasks/` | GET, POST | Zadania M08 |
| `incidents/` | GET, POST | Incydenty M09 |
| `audit-trail/` | GET | Audit trail M10 (tylko odczyt) |
| `pdca/` | GET, POST | PDCA M11 |
| `lessons/` | GET, POST | Lesson Learned M12 |
| `management-review/` | GET, POST | Przegląd Zarządzania M13 |
| `suppliers/` | GET, POST | Dostawcy M14 |
| `training/` | GET, POST | Szkolenia M15 |
| `bcp/` | GET, POST | BCP M16 |
| `audit-prep/preps/` | GET, POST | Audit Prep M17 |
| `audit-prep/programs/` | GET, POST | Programy audytu M17 |
| `reporting/dashboard-summary/` | GET | Zagregowany dashboard M18 |
| `reporting/kpi-trend/` | GET | Trend KPI M18 |
| `notifications/` | GET | Powiadomienia M19 |
| `manual/<type>/` | GET | Instrukcje (użytkownika/techniczna) |

### Filtry i paginacja

```
GET /api/v1/controls/?framework=VDA_ISA_6_0&plant=PLT-001&status=gap&page=2&page_size=25
```

Wszystkie endpointy listowe obsługują:

- `page` i `page_size` (domyślnie 25, maksymalnie 100)
- `ordering` (np. `ordering=-created_at`)
- filtry specyficzne dla modułu udokumentowane w `/api/v1/schema/` (OpenAPI 3.0)

### Standardowa odpowiedź

```json
{
  "count": 83,
  "next": "/api/v1/controls/?page=2",
  "previous": null,
  "results": [...]
}
```

### Błędy

```json
{
  "error": "validation_error",
  "detail": {
    "status": ["Wartość 'invalid' nie jest prawidłowym wyborem."],
    "owner": ["To pole jest wymagane."]
  }
}
```

Używane kody HTTP: 200, 201, 204, 400, 401, 403, 404, 409 (konflikt stanu), 422 (błąd logiki biznesowej), 500.

### Eksport compliance

Pobieranie plików wymaga JWT w nagłówku. Nie używać `window.open()`, które nie przekazuje tokenu.

```typescript
// ✅ Poprawnie — używa fetch() z nagłówkiem Authorization
const response = await fetch(
  `/api/v1/controls/export/?framework=ISO27001&format=soa&plant=${plantId}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const blob = await response.blob();

// ❌ Błędnie — window.open() nie przekazuje JWT
window.open(`/api/v1/controls/export/?framework=ISO27001`);
```

### Publiczne API wychodzące (M19)

```
GET /api/external/v1/plants/           # lista plant z nis2_scope
GET /api/external/v1/controls/         # kontrole ze stanem dla plant
GET /api/external/v1/risks/            # otwarte oceny ryzyka

Uwierzytelnianie: klucz API w nagłówku  X-API-Key: <key>
Limit zapytań: 100 req/min na klucz
```

---

## Bezpieczeństwo

### Konfiguracja JWT

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

### Throttling

Podstawowy throttling używa `AnonRateThrottle` i `UserRateThrottle`:

- `AnonRateThrottle`: 20/h
- `UserRateThrottle`: 500/h
- `LoginRateThrottle`: 5/min (na `GrcTokenObtainPairView`)

Możliwość dostosowania dla wrażliwych endpointów przez nadpisanie `throttle_classes` w ViewSet.

### Bezpieczny upload plików

```python
from core.validators import validate_uploaded_file

# Weryfikuje: rozmiar + whitelist rozszerzeń + rzeczywisty typ MIME (python-magic)
validate_uploaded_file(request.FILES["file"])
```

### Szyfrowanie poświadczeń SMTP

```python
# EncryptedCharField używa Fernet AES-256
# FERNET_KEY wymagana w .env — brak bezpiecznej wartości domyślnej
class EmailConfiguration(BaseModel):
    smtp_password = EncryptedCharField(max_length=500)
```

### Polityka haseł

- Minimum 12 znaków
- `CommonPasswordValidator`
- `NumericPasswordValidator`
- `UserAttributeSimilarityValidator`

### Endpointy serwisowe

Niektóre endpointy administracyjne (np. reset testowej bazy danych w `auth_grc.ResetTestDbView`) są jawnie blokowane w środowisku produkcyjnym przez sprawdzenie `settings.DEBUG`, aby uniemożliwić niewłaściwe użycie poza środowiskami testowymi.

---

## Prywatność i RODO

### Anonimizacja użytkowników (Art. 17 RODO)

```python
from apps.auth_grc.services import anonymize_user

anonymize_user(user_id)
# Usuwa imię, email, telefon — zachowuje integralność audit trail
# Endpoint: POST /api/v1/auth/users/{id}/anonymize/
```

### AI Sanitizer

```python
from apps.ai_engine.sanitizer import Sanitizer

safe_text = Sanitizer.sanitize(raw_text)
# Usuwa: email, IP, NIP, PESEL, telefon, nazwy plant
# ZAWSZE używać przed wysłaniem do chmurowego LLM
```

### Automatyczna retencja audit log

- L1 (bezpieczeństwo): 5 lat
- L2 (compliance): 3 lata
- L3 (operacyjne): 1 rok
- Harmonogram: 1. dnia miesiąca o 03:00 (zadanie `cleanup_expired_audit_logs`)

---

## Audit trail — append-only z łańcuchem hashy

### Zasada działania

Każda istotna akcja zapisuje rekord `AuditLog`. Rekord jest niezmienny: trigger PostgreSQL odrzuca UPDATE i DELETE. Każdy rekord zawiera `prev_hash` i `record_hash = SHA256(json_payload + prev_hash)`, tworząc weryfikowalny łańcuch.

### Jak zalogować akcję

```python
from core.audit import log_action

# W service lub w sygnale post_save
log_action(
    request=request,            # do wyodrębnienia użytkownika i aktualnej roli
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

Moduł `core.audit` automatycznie obsługuje:

- Snapshot `user_role_at_time` w chwili wywołania
- Obliczanie `prev_hash` (odczytuje ostatni rekord dla entity_type) i `record_hash`
- Transakcyjny zapis z `select_for_update()` zapobiegający wyścigowi warunków
- Jeśli log się nie powiedzie, zgłaszany jest wyjątek (transakcja zostaje wycofana)

### Weryfikacja integralności

```bash
# Sprawdza cały łańcuch: przelicza każdy hash i porównuje
python manage.py verify_audit_trail_integrity

# Znajduje pierwszy uszkodzony rekord
python manage.py verify_audit_trail_integrity --verbose

# Zadanie nocne (Celery Beat — już skonfigurowane)
# Wysyła alert jeśli łańcuch jest uszkodzony
```

---

## Audit Preparation — logika techniczna

### suggest_audit_plan()

- Priorytetyzuje domeny z otwartymi lukami (wyższy `gap_pct`)
- Deterministyczne ziarno (hash MD5 `program_id` + `quarter`) dla reprodukowalnej próbki między wykonaniami
- Deduplikacja domen cross-framework przez słownik `seen_domains`
- Rozkład próbki: `campione`=25%, `esteso`=50%, `full`=100%

### launch_audit_from_program()

- `transaction.atomic()` — operacja całkowicie atomowa
- `bulk_create` dla EvidenceItem (tylko jeden INSERT zamiast N)
- `sync_program_completion()` wywoływane automatycznie w `perform_update()`

### Zadanie przypominające (check_upcoming_audits)

- Zakres ±4 dni dla obsługi tygodniowego zadania vs dat w środku tygodnia
- 28-32 dni wcześniej: zadanie przygotowawcze
- 5-9 dni wcześniej: pilne zadanie jeśli AuditPrep nie został jeszcze uruchomiony
- 0-3 dni po dacie: krytyczny alert jeśli AuditPrep nie uruchomiony

---

## Compliance Schedule (M08)

### Obliczanie terminów

```python
from apps.compliance_schedule.services import get_due_date

due = get_due_date("finding_major", plant=plant, from_date=date.today())
# 23 typy reguł konfigurowalnych z poziomu UI administratora
```

---

## Dodawanie frameworku normatywnego

Frameworki są plikami JSON w `backend/frameworks/`. Nie ma potrzeby modyfikowania kodu Python.

### Struktura JSON

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
# Importuje nowy framework
python manage.py load_frameworks --file frameworks/nist_csf_2_0.json

# Komenda:
# 1. Tworzy Framework i wszystkie kontrole Control
# 2. Tworzy mapowania ControlMapping z innymi frameworkami
# 3. NIE generuje ControlInstance (są generowane gdy framework jest aktywowany dla plant)

# Aktywowanie frameworku dla plant (przez admin lub API)
POST /api/v1/plant-frameworks/
{ "plant": "PLT-001", "framework": "NIST_CSF_2_0", "active_from": "2026-03-13" }
# → automatycznie generuje ControlInstance w stanie non_valutato dla każdej kontroli
```

### Wersjonowanie frameworków

Gdy wychodzi nowa wersja istniejącego frameworku:

1. Utwórz nowy plik JSON z tym samym `code`, ale zaktualizowaną `version` (np. `VDA_ISA_6_1`)
2. Komenda `load_frameworks --version-update` porównuje kontrole:
   - Niezmienione: migrowane automatycznie z tym samym stanem
   - Zmienione: tworzone są nowe `ControlInstance` w stanie `non_valutato` z zadaniem przeglądu
   - Usunięte: archiwizowane (`archived_at`) z notatką
   - Nowe: tworzone w stanie `non_valutato`

Poprzednia wersja nigdy nie jest usuwana — pozostaje zarchiwizowana do celów audytów historycznych.

---

## Dodawanie modułu

Aby dodać nowy moduł funkcjonalny (np. M21):

```bash
# 1. Utwórz aplikację Django
cd backend
python manage.py startapp new_module apps/new_module

# 2. Dodaj do INSTALLED_APPS w core/settings/base.py
INSTALLED_APPS = [
    ...
    'apps.new_module',
]

# 3. Zarejestruj URL w backend/core/urls.py
path('api/v1/new-module/', include('apps.new_module.urls')),
```

Obowiązkowa minimalna struktura:

```
apps/new_module/
  models.py        — dziedziczyć po BaseModel
  serializers.py
  views.py         — ViewSet z uprawnieniami
  urls.py          — router.register
  services.py      — logika biznesowa
  tasks.py         — zadania Celery jeśli konieczne
  signals.py       — dla audit trail
  tests/
```

**Lista kontrolna dla każdego nowego modułu:**

- [ ] Wszystkie modele dziedziczą po `BaseModel` (UUID, soft delete, znacznik czasu)
- [ ] Każda istotna akcja wywołuje `log_action()` w service
- [ ] Widoki używają `ModulePermission` do kontroli dostępu
- [ ] Istnieją testy dla modeli, API i service (pokrycie >= 70%)
- [ ] Kody akcji są zarejestrowane w katalogu `core/audit/action_codes.py`
- [ ] Etykiety UI są dodane do plików i18n w `frontend/src/i18n/` we wszystkich 5 językach

---

## AI Engine M20 — integracja techniczna

### Architektura modułu

```
apps/ai_engine/
├── sanitizer.py        # anonimizacja PII przed wysłaniem do chmury
├── router.py           # wybór lokalny vs. chmura w zależności od funkcji
├── functions/
│   ├── classification.py
│   ├── text_analysis.py
│   ├── draft_generation.py
│   └── anomaly_detection.py
├── models.py           # AiInteractionLog
├── tasks.py            # asynchroniczne zadania detekcji anomalii
└── tests/
```

### AiInteractionLog

```python
class AiInteractionLog(BaseModel):
    function = models.CharField(max_length=50)
    # classification | text_analysis | draft_generation | anomaly_detection
    module_source = models.CharField(max_length=5)       # M04, M07, M09...
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)        # np. gpt-4o | llama3.1:8b
    input_hash = models.CharField(max_length=64)         # SHA256 promptu — nigdy tekst
    output_ai = models.TextField()                       # surowy wynik modelu
    output_human_final = models.TextField(null=True)     # po potwierdzeniu/modyfikacji przez człowieka
    delta = models.JSONField(null=True)                  # różnica output_ai vs output_human_final
    confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(null=True)
    ignored = models.BooleanField(default=False)         # sugestia zignorowana przez użytkownika
```

`AiInteractionLog` jest rejestrowany w M10 przez `log_action()` z `action_code='ai.suggestion.confirmed'` lub `'ai.suggestion.ignored'`.

### Sanitizer

```python
# apps/ai_engine/sanitizer.py
class Sanitizer:
    """
    Anonimizuje kontekst przed wysłaniem do chmurowego LLM.
    Mapuje tokeny na rzeczywiste wartości do de-anonimizacji wyniku.
    """

    def sanitize(self, context: dict) -> tuple[dict, dict]:
        """
        Returns: (sanitized_context, token_map)
        token_map: { "[PLANT_A]": "Stabilimento Milano", ... }
        """
        ...

    def desanitize(self, text: str, token_map: dict) -> str:
        """Zastępuje tokeny rzeczywistymi wartościami w wygenerowanym tekście."""
        ...
```

### Wywołanie funkcji AI z service

```python
from apps.ai_engine.functions.classification import classify_incident_severity

# W service M09 — incidents/services.py
async def suggest_severity(incident: Incident, request) -> dict | None:
    if not settings.AI_ENGINE_CONFIG['functions']['classification']['enabled']:
        return None

    result = await classify_incident_severity(
        description=incident.description,
        assets=[a.name for a in incident.assets.all()],
        plant_type=incident.plant.nis2_scope,
    )
    # result = { "suggested_severity": "alta", "confidence": 0.87, "reasoning": "..." }

    # Wyświetlane użytkownikowi jako sugestia — nie stosowane automatycznie
    return result
```

### Human-in-the-loop — przepływ API

```
POST /api/v1/ai/suggest/
{ "function": "classification", "entity_type": "incident", "entity_id": "..." }

→ 200 { "suggestion_id": "...", "output": { "suggested_severity": "alta" } }

# Użytkownik akceptuje, modyfikuje lub ignoruje
POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": true, "final_value": "alta" }
# → aktualizuje AiInteractionLog.confirmed_by i .output_human_final
# → stosuje wartość do encji

POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": false }
# → AiInteractionLog.ignored = True
# → brak efektu na encję
```

---

## Integracje zewnętrzne

### KnowBe4 (M15)

```python
# apps/training/kb4_client.py
class KnowBe4Client:
    BASE_URL = settings.KNOWBE4_API_URL

    def get_enrollments_delta(self, since: datetime) -> list[dict]:
        """Pobiera ukończenia od podanego znacznika czasu."""
        ...

    def get_phishing_results(self, campaign_id: str) -> list[dict]:
        ...

    def provision_user(self, user: User, groups: list[str]) -> bool:
        """Tworzy lub aktualizuje użytkownika w KB4 z poprawnymi grupami (rola+plant+język)."""
        ...

    def deprovision_user(self, email: str) -> bool:
        """Odwołuje dostęp użytkownika w KB4 (wywoływane przez sygnał post_save na User.is_active=False)."""
        ...
```

Synchronizacja jest wykonywana przez zadanie Celery `training.tasks.sync_knowbe4` planowane co noc o 02:00.

### Webhook wychodzący (M19)

```python
# Struktura payload webhooka
{
  "event": "risk.red_threshold_exceeded",
  "timestamp": "2026-03-13T10:00:00Z",
  "plant_id": "PLT-001",
  "plant_name": "...",              # dołączany tylko jeśli odbiorca ma dostęp
  "data": {
    "risk_id": "...",
    "score": 18,
    "asset_ids": ["..."]
  },
  "signature": "sha256=..."         # HMAC-SHA256 ze skonfigurowanym kluczem
}
```

---

## i18n — internacjonalizacja

### Backend — Django i18n

```python
# W modelu lub service — nie używać hardkodowanych ciągów
from django.utils.translation import gettext_lazy as _

class ControlInstance(BaseModel):
    status = models.CharField(
        choices=[
            ('compliant', _('Compliant')),
            ('gap', _('Gap')),
        ]
    )
```

Tłumaczenia backendowe znajdują się w `backend/locale/{język}/LC_MESSAGES/django.po`:

```bash
python manage.py makemessages -l pl
# Zmodyfikuj locale/pl/LC_MESSAGES/django.po
python manage.py compilemessages
```

### Frontend — i18next

Pliki tłumaczeń:

```
frontend/src/i18n/
├── it/common.json
├── en/common.json
├── fr/common.json
├── pl/common.json
└── tr/common.json
```

Struktura pliku namespace:

```json
{
  "status": {
    "compliant": "Zgodny",
    "gap": "Luka",
    "parziale": "Częściowy",
    "na": "N/A",
    "non_valutato": "Nieoceniony"
  },
  "actions": {
    "save": "Zapisz",
    "approve": "Zatwierdź"
  }
}
```

Użycie w komponencie React:

```typescript
import { useTranslation } from "react-i18next"

function ControlStatus({ status }: { status: string }) {
  const { t } = useTranslation()
  return <span>{t(`status.${status}`)}</span>
}
```

**Zasada**: każdy klucz dodany w `it/common.json` lub `en/common.json` musi być jednocześnie dodany do wszystkich 5 plików. Nigdy nie pozostawiać brakujących kluczy w żadnym języku.

### Kontrole — tłumaczenia w JSON frameworku

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

Serializator automatycznie zwraca tłumaczenie w języku żądającego:

```python
# controls/serializers.py
def get_title(self, obj):
    lang = self.context['request'].user.profile.language  # it | en | fr | pl | tr
    return obj.translations.get(lang, {}).get('title') or obj.translations['en']['title']
```

---

## Frontend

### Zarządzanie stanem

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

Automatyczne buforowanie, unieważnianie przy mutacji, wykładnicze ponowne próby przy błędach sieci.

### Klient API z automatycznym odświeżaniem

```typescript
// api/client.ts — interceptor JWT
apiClient.interceptors.response.use(
  r => r,
  async error => {
    if (error.response?.status === 401) {
      // automatyczne odświeżanie tokenu przez /api/auth/token/refresh/
      // jeśli odświeżanie się nie powiedzie, wylogowanie i przekierowanie do /login
    }
  }
)
```

### Internacjonalizacja

```typescript
import { useTranslation } from "react-i18next"

const { t } = useTranslation()
// Pliki: frontend/src/i18n/{it,en,fr,pl,tr}/common.json
// Zasada: dodawać JEDNOCZEŚNIE do wszystkich 5 języków
```

---

## Testy

### Wykonanie

```bash
# Kompletna suita backend
docker compose exec backend pytest
docker compose exec backend pytest --cov=apps --cov-report=html

# Test pojedynczego modułu
docker compose exec backend pytest apps/audit_prep/

# Tylko szybkie testy (bez DB)
pytest -m "not slow" tests/unit/

# Frontend
cd frontend && npm test
```

### Struktura

```
apps/{modul}/tests/
  test_models.py     — testy jednostkowe modeli i serwisów
  test_api.py        — testy endpointów API z APIClient
  test_services.py   — testy izolowanej logiki biznesowej
```

### Standardowe fixtures

```python
# conftest.py — dostępne we wszystkich testach
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
    # Weryfikacja łańcucha hashy
    assert log.record_hash == compute_hash(log.payload, log.prev_hash)
```

### Cel pokrycia: >= 70%

Suite pytest (`backend/pytest.ini`, `--cov=apps --cov=core --cov-fail-under=70`) obejmuje większość aplikacji; globalne pokrycie jest monitorowane w CI (aktualne liczby w `CLAUDE.md`).

---

## Komendy zarządzania

| Komenda | Opis | Kiedy wykonywać |
|---------|------|-----------------|
| `migrate` | Stosuje migracje DB | Po każdym deployu |
| `load_frameworks` | Importuje frameworki normatywne z JSON | Początkowa konfiguracja + aktualizacja frameworku |
| `load_notification_profiles` | Domyślne profile powiadomień | Początkowa konfiguracja |
| `load_competency_requirements` | Wymagania kompetencyjne M15 | Początkowa konfiguracja |
| `load_required_documents` | Obowiązkowe dokumenty | Początkowa konfiguracja |
| `verify_audit_trail_integrity` | Weryfikuje łańcuch hashy audit trail | Miesięcznie + po przywróceniu |
| `check --deploy` | Weryfikuje konfigurację produkcyjną | Przed każdym deployem |
| `createsuperuser` | Tworzy pierwszego administratora | Początkowa konfiguracja |
| `seed_demo` | Ładuje dane demo | Tylko środowisko deweloperskie |
| `makemessages -l <lang>` | Wyodrębnia ciągi i18n z backendu | Po dodaniu nowych ciągów |
| `compilemessages` | Kompiluje pliki .po do .mo | Po tłumaczeniu |
| `sync_knowbe4 --full` | Ręczna synchronizacja KnowBe4 | Odtwarzanie po błędzie |

---

## Zmienne środowiskowe

| Nazwa | Typ | Domyślna dev | Opis | Wymagana |
|------|------|------------|-----|---------|
| `SECRET_KEY` | string | — | Klucz kryptograficzny Django | Tak |
| `FERNET_KEY` | string | — | AES-256 dla poświadczeń SMTP | Tak |
| `DEBUG` | bool | True | False w środowisku produkcyjnym | Nie |
| `ALLOWED_HOSTS` | string | localhost | Dozwolone hosty (oddzielone przecinkami) | Tak na prod |
| `DATABASE_URL` | string | postgresql://grc:grc@db:5432/grc_dev | URL PostgreSQL | Tak |
| `REDIS_URL` | string | redis://redis:6379/0 | URL Redis | Tak |
| `FRONTEND_URL` | string | http://localhost:3001 | URL frontendu | Tak |
| `CORS_ALLOWED_ORIGINS` | string | http://localhost:3001 | Originy CORS | Nie |
| `AI_ENGINE_ENABLED` | bool | False | Włącza M20 AI Engine | Nie |
| `KNOWBE4_API_KEY` | string | — | Klucz API KnowBe4 | Tylko gdy M15 aktywny |

---

## Konwencje programistyczne

### Git

- Branch: `feature/M{nn}-opis`, `fix/M{nn}-opis-błędu`, `chore/opis`
- Commit: `feat(M09): aggiungi timer NIS2 con countdown visibile`
- Jeden branch = jeden moduł lub spójna funkcjonalność
- Brak bezpośrednich commitów na `main` lub `develop`

### Python / Django

- Formatter: `ruff format` (kompatybilny z black)
- Linter: `ruff check`
- Type hints na wszystkich service i klientach zewnętrznych
- Docstring obowiązkowy dla klas i metod publicznych
- Żadnej logiki biznesowej w widokach — wszystko w `services.py`
- Brak zapytań N+1 — używać `select_related` i `prefetch_related`

### React / TypeScript

- TypeScript na wszystkich komponentach
- Brak jawnego użycia `any`
- Komponenty prezentacyjne oddzielone od komponentów kontenerów
- Wywołania API umieszczone w custom hookach (`useIncident`, `useControls`)
- Formatter: Prettier
- Linter: ESLint

### Bezpieczeństwo

- Żadnych poświadczeń w kodzie źródłowym
- Żadnych wrażliwych danych w logach (używać hashy lub maskowania)
- Token CSRF na wszystkich mutacjach
- Rate limiting na publicznych endpointach i na M20 AI
- Walidacja danych wejściowych w serializerach — nigdy nie ufać klientowi

---

## Rozwiązywanie problemów

### Celery Beat nie wykonuje zaplanowanych zadań

```bash
# Sprawdź czy beat jest uruchomiony
docker compose ps celery-beat
# Jeśli nie jest up: docker compose restart celery-beat

# Sprawdź stan zaplanowanych zadań
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(PeriodicTask.objects.filter(enabled=True).values('name','last_run_at'))"
```

### Sprawdzenie integralności audit trail nie powiodło się

Niepowodzenie wskazuje, że rekord został zmodyfikowany lub łańcuch został przerwany. Nie próbować naprawiać — skontaktować się z zespołem bezpieczeństwa. System automatycznie generuje alert P1.

```bash
# Znajdź pierwszy uszkodzony rekord
python manage.py verify_audit_trail_integrity --verbose
```

### Import frameworku nie powiódł się

```bash
python manage.py load_frameworks --file frameworks/nowy.json --dry-run
# Pokazuje różnice bez ich stosowania

python manage.py load_frameworks --file frameworks/nowy.json --validate-only
# Waliduje JSON bez importowania
```

### Synchronizacja KnowBe4 nie powiodła się

```bash
# Sprawdź poświadczenia
python manage.py shell -c "from apps.training.kb4_client import KnowBe4Client; print(KnowBe4Client().health_check())"

# Ponownie wykonaj synchronizację ręcznie
python manage.py sync_knowbe4 --full
```

### Token AI w chmurze nieautoryzowany (M20)

1. Sprawdź, czy `AI_ENGINE_ENABLED=true` i czy konkretna funkcja jest włączona w `AI_ENGINE_CONFIG`
2. Sprawdź, czy klucz API jest skonfigurowany i nie wygasł
3. Sprawdź, czy sanitizer nie generuje błędów: `grep "sanitizer" logs/app.log | tail -20`
4. W przypadku trwałego błędu, system przechodzi do trybu awaryjnego z modelem lokalnym jeśli jest dostępny

### Migracja nie powiodła się w środowisku produkcyjnym

```bash
# Sprawdź stan migracji przed zastosowaniem
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Zastosuj z pełnym opisem
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate --verbosity=2

# W przypadku zablokowanej migracji sprawdź blokady na DB
# Połącz się z PostgreSQL i sprawdź pg_stat_activity
```

### Frontend nie otrzymuje odświeżonego tokenu

Sprawdź, czy cookie `refresh_token` nie wygasło i czy domena jest zgodna. W środowisku deweloperskim upewnij się, że `CORS_ALLOW_CREDENTIALS = True` i że `FRONTEND_URL` jest ustawiony poprawnie.

### Health check nie powiódł się

```bash
# Sprawdź stan serwisów
curl http://localhost:8001/api/health/
# Oczekiwana odpowiedź: {"status": "ok", "db": "ok"}

# Jeśli db=error, sprawdź połączenie PostgreSQL
docker compose ps db
docker compose logs db --tail=20
```
