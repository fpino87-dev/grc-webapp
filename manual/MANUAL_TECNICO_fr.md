# Manuel Technique — GRC Platform

> Guide pour les développeurs : architecture, modèles de données, API, référentiels normatifs, moteur IA, tests et conventions.

---

## Sommaire

- [Stack et versions](#stack-et-versions)
- [Architecture](#architecture)
- [Structure du dépôt](#structure-du-dépôt)
- [Modèles principaux](#modèles-principaux)
- [API](#api)
- [Sécurité](#sécurité)
- [Confidentialité et RGPD](#confidentialité-et-rgpd)
- [Audit trail — append-only avec chaîne de hachage](#audit-trail--append-only-avec-chaîne-de-hachage)
- [Préparation d'audit — logique technique](#préparation-daudit--logique-technique)
- [Calendrier de conformité (M08)](#calendrier-de-conformité-m08)
- [Ajouter un référentiel normatif](#ajouter-un-référentiel-normatif)
- [Ajouter un module](#ajouter-un-module)
- [Moteur IA M20 — intégration technique](#moteur-ia-m20--intégration-technique)
- [Intégrations externes](#intégrations-externes)
- [i18n — internationalisation](#i18n--internationalisation)
- [Frontend](#frontend)
- [Tests](#tests)
- [Commandes de gestion](#commandes-de-gestion)
- [Variables d'environnement](#variables-denvironnement)
- [Conventions de développement](#conventions-de-développement)
- [Dépannage](#dépannage)

---

## Stack et versions

| Composant | Technologie | Version |
|-----------|-----------|---------|
| Runtime backend | Python | 3.11 |
| Framework web | Django | 5.1 |
| API REST | Django REST Framework | 3.15 |
| File d'attente de tâches | Celery | 5.x |
| Cache/Broker | Redis | 7 |
| Base de données | PostgreSQL | 16 (Docker dev) |
| Serveur de production | Gunicorn | — |
| Framework frontend | React | 18.3 |
| Outil de build | Vite | 5.4 |
| CSS | Tailwind CSS | 3.4 |
| Gestion d'état | Zustand | 5.0 |
| Récupération de données | TanStack Query | 5.56 |
| Routeur | React Router | 7 |
| i18n frontend | i18next | 23.10 |
| Markdown | react-markdown | 9.0 |
| Conteneur | Docker Compose | v2 |

---

## Architecture

### Flux architectural

```
frontend (React SPA)
    │  REST JSON / JWT
    ▼
backend (Django + DRF)
    │
    ├── apps/          une application Django par module (M00–M20)
    ├── core/          settings, middleware, modèles de base, auth
    └── frameworks/    référentiels normatifs JSON (VDA ISA, NIS2, ISO 27001)
    │
    ├── PostgreSQL     base de données principale + audit trail append-only
    ├── Redis          cache sessions + broker Celery
    └── S3 / MinIO     stockage objet documents et preuves
    │
    └── Celery Worker  tâches asynchrones : notifications, sync KB4, jobs audit trail
        Celery Beat    scheduler récurrents : échéances, digest email, sync
```

### Principes architecturaux (issus de CLAUDE.md)

Les principes suivants sont contraignants pour tout le code du projet. Il n'est jamais permis d'y déroger.

**1. BaseModel** — tous les modèles héritent de `core.models.BaseModel`

```python
class MyModel(BaseModel):
    name = models.CharField(max_length=100)
    # Hérite de : id (UUID pk), created_at, updated_at, deleted_at, created_by, soft_delete()
```

**2. Logique métier dans services.py** — jamais dans les vues ou les sérialiseurs

```python
# ✅ Correct
# apps/mymodule/services.py
def create_something(plant, user, data):
    obj = MyModel.objects.create(plant=plant, created_by=user, **data)
    log_action(user=user, action_code="mymodule.created", level="L2", entity=obj, payload={...})
    return obj

# ❌ Incorrect — logique dans la vue
def perform_create(self, serializer):
    obj = MyModel.objects.create(...)  # logique ici = violation
```

**3. Audit log obligatoire** — chaque action pertinente appelle `log_action`

```python
from core.audit import log_action
log_action(
    user=request.user,
    action_code="mymodule.entity.action",  # format : app.entity.action
    level="L2",  # L1=sécurité (5 ans), L2=conformité (3 ans), L3=opérationnel (1 an)
    entity=instance,
    payload={"key": "value"},  # SANS PII, uniquement compteurs/ID
)
```

**4. Soft delete** — jamais `queryset.delete()` direct

```python
# ✅ Correct
instance.soft_delete()

# ❌ Incorrect
instance.delete()
MyModel.objects.filter(...).delete()
```

**5. Pas de N+1** — `select_related` et `prefetch_related` obligatoires

```python
# ✅ Correct
queryset = MyModel.objects.select_related("plant", "created_by").prefetch_related("items")

# ❌ Incorrect
for obj in MyModel.objects.all():
    print(obj.plant.name)  # N+1 !
```

**6. Tâches assignées à un rôle** (résolution dynamique via `UserPlantAccess`), jamais à un utilisateur direct.

**7. Référentiels normatifs = JSON** dans `backend/frameworks/` — ne pas coder les contrôles en dur dans le code.

**8. M20 Moteur IA** : toujours `Sanitizer.sanitize()` avant d'envoyer au LLM cloud ; validation humaine avant d'appliquer tout résultat IA.

**9. Le gestionnaire soft delete** est celui par défaut — `.all_with_deleted()` uniquement lorsque c'est explicitement nécessaire.

**10. Ne jamais journaliser de PII** — uniquement des compteurs ou des identifiants anonymes dans les logs système.

**11. Upload de fichiers** : toujours `validate_uploaded_file()` avec vérification MIME (python-magic).

**12. Production** : `docker-compose.prod.yml` et `Dockerfile.prod`.

**13. Traductions obligatoires** : chaque clé i18n ajoutée dans `it/common.json` ou `en/common.json` doit être traduite simultanément dans les 5 langues (IT, EN, FR, PL, TR).

Principes contraignants supplémentaires :

- Framework as data : les contrôles sont en JSON, pas en code. Ajouter DORA ne nécessite pas de déploiement.
- Table inheritance IT/OT : `Asset` de base + `AssetIT` et `AssetOT` — aucune colonne nullable inutile.
- RBAC (M02) séparé de la gouvernance normative (M00) : permissions applicatives vs. nominations formelles.
- Audit trail append-only avec chaîne de hachage SHA-256 : immuabilité technique, pas seulement procédurale.
- Tâches assignées à un rôle avec résolution dynamique : un changement de personnel ne nécessite pas de réallocation manuelle.
- Versions de référentiels immuables : archivées, jamais supprimées.

### Patterns obligatoires avec exemples

**Pattern service complet :**

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

**Tâche Celery avec autoretry :**

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def my_scheduled_task(self):
    # logique de la tâche
    return "done"
```

**Pattern Destroy (soft delete) :**

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

### Flux de données principal

```
BIA.downtime_cost → RiskAssessment.ale_eur (calculé)
RiskAssessment(score > 14) → Tâche urgente + PDCA automatique
Incident.close() → PDCA + LessonLearned automatiques
AuditFinding.close() → PDCA + LessonLearned automatiques
BcpTest(échoué) → PDCA automatique
PDCA.close() → met à jour le module source + LessonLearned
```

### Configuration de l'environnement de développement

#### Prérequis

```bash
python --version     # >= 3.11
node --version       # >= 20
docker --version     # >= 4.x
```

#### Premier démarrage

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
python manage.py load_frameworks       # importe VDA ISA, NIS2, ISO 27001
python manage.py seed_demo             # données de démonstration optionnelles
python manage.py createsuperuser

# Démarrer le backend
python manage.py runserver 0.0.0.0:8000

# Frontend (dans un autre terminal)
cd frontend
npm install
npm run dev
```

#### Commandes Makefile

```bash
make dev          # docker compose up + runserver + npm run dev
make migrate      # python manage.py migrate
make test         # pytest (backend) + npm test / vitest (frontend)
make lint         # ruff (backend)
make load-fw      # python manage.py load_frameworks
make seed         # python manage.py seed_demo
make shell        # python manage.py shell_plus
make celery       # démarre le worker Celery en premier plan
```

---

## Structure du dépôt

### Backend

```
backend/
├── core/
│   ├── settings/
│   │   ├── base.py          # settings partagés (JWT, DRF, INSTALLED_APPS, CELERY)
│   │   ├── dev.py           # surcharge développement (DEBUG=True, SQLite optionnel)
│   │   └── prod.py          # surcharge production (ALLOWED_HOSTS, SECURE_*, logging)
│   ├── models.py            # BaseModel, SoftDeleteManager
│   ├── audit.py             # log_action(), compute_hash()
│   ├── validators.py        # validate_uploaded_file() avec vérification MIME
│   ├── permissions.py       # ModulePermission, PlantScopedPermission
│   ├── middleware.py        # PlantContextMiddleware, RequestLoggingMiddleware
│   └── urls.py              # URL racine avec include pour chaque app
├── apps/
│   ├── governance/          # M00 — Gouvernance & Rôles
│   ├── plants/              # M01 — Plant Registry
│   ├── auth_grc/            # M02 — RBAC + JWT
│   ├── controls/            # M03 — Bibliothèque de contrôles + cmd load_frameworks
│   ├── assets/              # M04 — Assets IT/OT
│   ├── bia/                 # M05 — BIA
│   ├── risk/                # M06 — Évaluation des risques
│   ├── documents/           # M07 — Documents
│   ├── tasks/               # M08 — Gestion des tâches + Calendrier de conformité
│   ├── incidents/           # M09 — Incidents NIS2
│   ├── audit_trail/         # M10 — Audit Trail (vues en lecture seule)
│   ├── pdca/                # M11 — PDCA
│   ├── lessons/             # M12 — Lessons Apprises
│   ├── management_review/   # M13 — Revue de Direction
│   ├── suppliers/           # M14 — Fournisseurs
│   ├── training/            # M15 — Formation/KnowBe4
│   ├── bcp/                 # M16 — PCA
│   ├── audit_prep/          # M17 — Préparation d'audit
│   ├── reporting/           # M18 — Reporting (pas de modèle, seulement vues agrégées)
│   ├── notifications/       # M19 — Notifications
│   └── ai_engine/           # M20 — Moteur IA + Sanitizer
└── frameworks/
    ├── iso27001.json
    ├── nis2.json
    ├── tisax_l2.json
    └── tisax_l3.json
```

### Structure d'une application module

```
apps/incidents/          # M09 — Gestion des incidents
├── __init__.py
├── admin.py
├── apps.py
├── models.py            # Incident, IncidentNotification, RCA, ...
├── serializers.py       # Sérialiseurs DRF
├── views.py             # ViewSet API
├── urls.py              # router.register(...)
├── permissions.py       # Permissions spécifiques au module
├── services.py          # Logique métier — pas dans la vue
├── tasks.py             # Tâches Celery du module
├── signals.py           # post_save, post_delete pour l'audit trail
└── tests/
    ├── test_models.py
    ├── test_api.py
    └── test_services.py
```

### Frontend

```
frontend/src/
├── App.tsx                    # Routeur — modules, planning, paramètres
├── main.tsx                   # Point d'entrée avec QueryClientProvider + i18n
├── store/
│   └── auth.ts                # Zustand : user, token, selectedPlant
├── api/
│   ├── client.ts              # axios avec intercepteur JWT + refresh automatique
│   └── endpoints/             # client API TypeScript (~24 fichiers)
├── components/
│   ├── layout/
│   │   ├── Shell.tsx          # Layout principal avec sidebar
│   │   ├── Sidebar.tsx        # Navigation latérale avec entrées pour M00–M20
│   │   ├── Topbar.tsx         # Barre supérieure avec sélection plant et langue
│   │   └── BottomBar.tsx      # Barre inférieure mobile
│   └── ui/
│       ├── AiSuggestion.tsx   # Bannière IA avec Accept/Edit/Ignore
│       ├── CountdownTimer.tsx # Compte à rebours NIS2 en temps réel
│       ├── StatusBadge.tsx    # Badge coloré pour les états de conformité
│       └── ManualDrawer.tsx   # Tiroir contextuel des manuels (bouton ?)
├── modules/                   # Un dossier par module (M00–M20)
│   ├── dashboard/Dashboard.tsx
│   ├── controls/ControlsList.tsx
│   ├── incidents/IncidentsList.tsx
│   └── ...
├── pages/
│   └── LoginPage.tsx
└── i18n/
    ├── index.ts               # configuration i18next
    ├── it/common.json
    ├── en/common.json
    ├── fr/common.json
    ├── pl/common.json
    └── tr/common.json
```

---

## Modèles principaux

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

    objects = SoftDeleteManager()  # filtre deleted_at is null par défaut

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    class Meta:
        abstract = True
```

Tous les modèles de l'application héritent de `BaseModel`. Ne jamais utiliser `delete()` directement — utiliser `soft_delete()`.

### AuditLog

```python
class AuditLog(models.Model):
    # N'hérite pas de BaseModel — pas de soft delete, pas de updated_at
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)

    # Qui
    user_id = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time = models.CharField(max_length=50)   # snapshot du rôle au moment de l'action

    # Quoi
    action_code = models.CharField(max_length=100)        # ex. incident.created
    level = models.CharField(max_length=2)                # L1 | L2 | L3
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField()                          # données pertinentes de l'action

    # Chaîne de hachage SHA-256
    prev_hash = models.CharField(max_length=64)
    record_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'audit_log'
        # partitionné par RANGE (timestamp_utc) — défini dans la migration
```

Propriétés clés de l'AuditLog :

- Chaîne de hachage SHA-256 : chaque enregistrement a `prev_hash` + `record_hash`
- Déclencheur PostgreSQL empêche UPDATE/DELETE
- `select_for_update()` dans `_get_prev_hash()` pour prévenir les conditions de course
- Niveaux L1/L2/L3 avec rétention de 5/3/1 ans
- Vérification : `python manage.py verify_audit_trail_integrity`

### ControlInstance

- Champ `applicability` pour la SOA ISO 27001
- `calc_maturity_level()` pour VDA ISA (échelle 0-5)
- `needs_revaluation` pour la gestion du changement (M04)

```python
class ControlInstance(BaseModel):
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    control = models.ForeignKey(Control, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[('compliant','Compliant'),('parziale','Partiel'),
                 ('gap','Gap'),('na','N/A'),('non_valutato','Non évalué')]
    )
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    na_approved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    na_approved_at = models.DateTimeField(null=True)
    na_review_by = models.DateField(null=True)            # max 12 mois pour TISAX L3
    notes = models.TextField(blank=True)
    last_evaluated_at = models.DateTimeField(null=True)
```

### RiskAssessment

- Risque inhérent vs résiduel (6 dimensions IT + 4 OT)
- `weighted_score` avec multiplicateur BIA (`downtime_cost`)
- `risk_level` : vert ≤7, jaune ≤14, rouge >14
- Déclenchement automatique de PDCA si score > 14

### M00 — Gouvernance

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
        choices=[('essenziale','Essentiel'),('importante','Important'),('non_soggetto','Non assujetti')]
    )
    status = models.CharField(max_length=20)  # actif | en_fermeture | fermé

class PlantFramework(BaseModel):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    framework = models.ForeignKey('controls.Framework', on_delete=models.CASCADE)
    active_from = models.DateField()
    level = models.CharField(max_length=10, null=True)  # ex. L2 ou L3 pour TISAX

    class Meta:
        unique_together = ['plant', 'framework']
```

### M04 — Assets

```python
class Asset(BaseModel):
    """Table de base — table inheritance"""
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10)          # IT | OT
    criticality = models.IntegerField(default=1)          # 1–5, hérité du processus
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
    category = models.CharField(max_length=20)            # PLC | SCADA | HMI | RTU | capteur
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
    severity = models.CharField(max_length=10)            # faible|moyen|élevé|critique
    nis2_notifiable = models.CharField(max_length=15)     # oui|non|à_évaluer
    nis2_confirmed_at = models.DateTimeField(null=True)
    nis2_confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    status = models.CharField(max_length=20)              # ouvert|en_analyse|fermé
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

### Authentification

```
Authorization: Bearer <JWT-token>
```

Les tokens JWT ont une durée de vie ACCESS=30 min. Le refresh s'effectue automatiquement via l'intercepteur axios si l'utilisateur est actif (REFRESH=7 jours). Les auditeurs externes utilisent des tokens spéciaux avec portée et durée de validité limitées (générés par M02).

### Conventions d'URL

```
GET    /api/v1/{module}/                  # liste avec filtres et pagination
POST   /api/v1/{module}/                  # créer
GET    /api/v1/{module}/{id}/             # détail
PATCH  /api/v1/{module}/{id}/             # mise à jour partielle
DELETE /api/v1/{module}/{id}/             # soft delete (deleted_at)

# Actions personnalisées
POST   /api/v1/incidents/{id}/confirm_nis2/
POST   /api/v1/incidents/{id}/send_notification/
POST   /api/v1/documents/{id}/approve/
POST   /api/v1/controls/{id}/evaluate/
```

### Endpoints principaux

URL de base : `/api/v1/`

| Endpoint | Méthodes | Description |
|----------|--------|-------------|
| `governance/roles/` | GET, POST, PUT, DELETE | Rôles normatifs M00 |
| `plants/` | GET, POST | Plant registry M01 |
| `auth/users/` | GET, POST | Utilisateurs M02 |
| `controls/instances/` | GET, PUT | Contrôles M03 |
| `controls/export/` | GET | Export SOA/VDA/NIS2 |
| `assets/` | GET, POST | Assets IT/OT M04 |
| `bia/processes/` | GET, POST | BIA M05 |
| `risk/assessments/` | GET, POST | Risques M06 |
| `documents/` | GET, POST | Documents M07 |
| `tasks/` | GET, POST | Tâches M08 |
| `incidents/` | GET, POST | Incidents M09 |
| `audit-trail/` | GET | Audit trail M10 (lecture seule) |
| `pdca/` | GET, POST | PDCA M11 |
| `lessons/` | GET, POST | Lessons Apprises M12 |
| `management-review/` | GET, POST | Revue de Direction M13 |
| `suppliers/` | GET, POST | Fournisseurs M14 |
| `training/` | GET, POST | Formation M15 |
| `bcp/` | GET, POST | PCA M16 |
| `audit-prep/preps/` | GET, POST | Préparation d'audit M17 |
| `audit-prep/programs/` | GET, POST | Programmes d'audit M17 |
| `reporting/dashboard-summary/` | GET | Tableau de bord agrégé M18 |
| `reporting/kpi-trend/` | GET | Tendance KPI M18 |
| `notifications/` | GET | Notifications M19 |
| `manual/<type>/` | GET | Manuels (utilisateur/technique) |

### Filtres et pagination

```
GET /api/v1/controls/?framework=VDA_ISA_6_0&plant=PLT-001&status=gap&page=2&page_size=25
```

Tous les endpoints de liste supportent :

- `page` et `page_size` (défaut 25, max 100)
- `ordering` (ex. `ordering=-created_at`)
- filtres spécifiques au module documentés dans `/api/v1/schema/` (OpenAPI 3.0)

### Réponse standard

```json
{
  "count": 83,
  "next": "/api/v1/controls/?page=2",
  "previous": null,
  "results": [...]
}
```

### Erreurs

```json
{
  "error": "validation_error",
  "detail": {
    "status": ["La valeur 'invalid' n'est pas un choix valide."],
    "owner": ["Ce champ est obligatoire."]
  }
}
```

Codes HTTP utilisés : 200, 201, 204, 400, 401, 403, 404, 409 (conflit d'état), 422 (erreur de logique métier), 500.

### Export de conformité

Le téléchargement de fichiers nécessite le JWT dans l'en-tête. Ne pas utiliser `window.open()` qui ne transporte pas le token.

```typescript
// ✅ Correct — utiliser fetch() avec l'en-tête Authorization
const response = await fetch(
  `/api/v1/controls/export/?framework=ISO27001&format=soa&plant=${plantId}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const blob = await response.blob();

// ❌ Incorrect — window.open() ne transmet pas le JWT
window.open(`/api/v1/controls/export/?framework=ISO27001`);
```

### API externe sortante (M19)

```
GET /api/external/v1/plants/           # liste des plants avec nis2_scope
GET /api/external/v1/controls/         # contrôles avec état par plant
GET /api/external/v1/risks/            # évaluations de risques ouvertes

Authentification : clé API dans l'en-tête  X-API-Key: <key>
Limite de débit : 100 req/min par clé
```

---

## Sécurité

### Configuration JWT

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

### Limitation de débit

La limitation de débit de base utilise `AnonRateThrottle` et `UserRateThrottle` :

- `AnonRateThrottle` : 20/h
- `UserRateThrottle` : 500/h
- `LoginRateThrottle` : 5/min (sur `GrcTokenObtainPairView`)

Personnalisable pour les endpoints sensibles en surchargeant `throttle_classes` dans le ViewSet.

### Upload de fichiers sécurisé

```python
from core.validators import validate_uploaded_file

# Vérifie : taille + liste blanche d'extensions + type MIME réel (python-magic)
validate_uploaded_file(request.FILES["file"])
```

### Chiffrement des identifiants SMTP

```python
# EncryptedCharField utilise Fernet AES-256
# FERNET_KEY obligatoire dans .env — aucune valeur par défaut sécurisée
class EmailConfiguration(BaseModel):
    smtp_password = EncryptedCharField(max_length=500)
```

### Politique de mots de passe

- Minimum 12 caractères
- `CommonPasswordValidator`
- `NumericPasswordValidator`
- `UserAttributeSimilarityValidator`

### Endpoints de service

Certains endpoints administratifs (ex. reset de la base de données de test dans `auth_grc.ResetTestDbView`) sont explicitement bloqués en production via une vérification de `settings.DEBUG` pour éviter toute utilisation inappropriée en dehors des environnements de test.

---

## Confidentialité et RGPD

### Anonymisation des utilisateurs (Art. 17 RGPD)

```python
from apps.auth_grc.services import anonymize_user

anonymize_user(user_id)
# Supprime le nom, l'email, le téléphone — préserve l'intégrité de l'audit trail
# Endpoint : POST /api/v1/auth/users/{id}/anonymize/
```

### Sanitizer IA

```python
from apps.ai_engine.sanitizer import Sanitizer

safe_text = Sanitizer.sanitize(raw_text)
# Supprime : email, IP, numéro de TVA, code fiscal, téléphone, noms de plants
# TOUJOURS utiliser avant d'envoyer au LLM cloud
```

### Rétention automatique de l'audit log

- L1 (sécurité) : 5 ans
- L2 (conformité) : 3 ans
- L3 (opérationnel) : 1 an
- Planifié : 1er du mois à 03:00 (tâche `cleanup_expired_audit_logs`)

---

## Audit trail — append-only avec chaîne de hachage

### Principe

Chaque action pertinente écrit un enregistrement `AuditLog`. L'enregistrement est immuable : le déclencheur PostgreSQL rejette les UPDATE et DELETE. Chaque enregistrement contient `prev_hash` et `record_hash = SHA256(json_payload + prev_hash)`, formant une chaîne vérifiable.

### Comment journaliser une action

```python
from core.audit import log_action

# Dans un service ou dans un signal post_save
log_action(
    request=request,            # pour extraire l'utilisateur et le rôle courant
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

Le module `core.audit` gère automatiquement :

- Snapshot `user_role_at_time` au moment de l'appel
- Calcul de `prev_hash` (lit le dernier enregistrement pour entity_type) et `record_hash`
- Écriture transactionnelle avec `select_for_update()` pour prévenir les conditions de course
- Si le log échoue, une exception est levée (la transaction est annulée)

### Vérification d'intégrité

```bash
# Vérifie l'ensemble de la chaîne : recalcule chaque hachage et compare
python manage.py verify_audit_trail_integrity

# Trouve le premier enregistrement corrompu
python manage.py verify_audit_trail_integrity --verbose

# Job nocturne (Celery Beat — déjà configuré)
# Envoie une alerte si la chaîne est rompue
```

---

## Préparation d'audit — logique technique

### suggest_audit_plan()

- Priorise les domaines avec des écarts ouverts (`gap_pct` le plus élevé)
- Graine déterministe (hachage MD5 `program_id` + `quarter`) pour un échantillon reproductible entre exécutions
- Déduplication des domaines cross-framework via dictionnaire `seen_domains`
- Distribution de l'échantillon : `campione`=25%, `esteso`=50%, `full`=100%

### launch_audit_from_program()

- `transaction.atomic()` — opération complètement atomique
- `bulk_create` pour EvidenceItem (un seul INSERT au lieu de N)
- `sync_program_completion()` appelé automatiquement dans `perform_update()`

### Tâche de rappel (check_upcoming_audits)

- Plage ±4 jours pour gérer les tâches hebdomadaires vs les dates en milieu de semaine
- 28-32 jours avant : tâche de préparation
- 5-9 jours avant : tâche urgente si AuditPrep pas encore démarré
- 0-3 jours après la date : alerte critique si AuditPrep non démarré

---

## Calendrier de conformité (M08)

### Calcul des échéances

```python
from apps.compliance_schedule.services import get_due_date

due = get_due_date("finding_major", plant=plant, from_date=date.today())
# 23 types de règles configurables depuis l'interface d'administration
```

---

## Ajouter un référentiel normatif

Les référentiels sont des fichiers JSON dans `backend/frameworks/`. Aucune modification du code Python n'est nécessaire.

### Structure JSON

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
# Importe le nouveau référentiel
python manage.py load_frameworks --file frameworks/nist_csf_2_0.json

# La commande :
# 1. Crée le Framework et tous les Control
# 2. Crée les ControlMapping avec les autres référentiels
# 3. NE génère PAS de ControlInstance (ils sont générés quand le référentiel est activé sur un plant)

# Activer le référentiel sur un plant (via admin ou API)
POST /api/v1/plant-frameworks/
{ "plant": "PLT-001", "framework": "NIST_CSF_2_0", "active_from": "2026-03-13" }
# → génère automatiquement des ControlInstance à l'état non_valutato pour chaque contrôle
```

### Gestion des versions de référentiels

Lorsqu'une nouvelle version d'un référentiel existant est publiée :

1. Créer un nouveau fichier JSON avec le même `code` mais une `version` mise à jour (ex. `VDA_ISA_6_1`)
2. La commande `load_frameworks --version-update` compare les contrôles :
   - Inchangés : migrent automatiquement avec le même état
   - Modifiés : de nouveaux `ControlInstance` sont créés à l'état `non_valutato` avec une tâche de révision
   - Supprimés : archivés (`archived_at`) avec une note
   - Nouveaux : créés à l'état `non_valutato`

La version précédente n'est jamais supprimée — elle reste archivée pour les audits historiques.

---

## Ajouter un module

Pour ajouter un nouveau module fonctionnel (ex. M21) :

```bash
# 1. Créer l'application Django
cd backend
python manage.py startapp new_module apps/new_module

# 2. Ajouter dans INSTALLED_APPS dans core/settings/base.py
INSTALLED_APPS = [
    ...
    'apps.new_module',
]

# 3. Enregistrer les URL dans backend/core/urls.py
path('api/v1/new-module/', include('apps.new_module.urls')),
```

Structure minimale obligatoire :

```
apps/new_module/
  models.py        — hériter de BaseModel
  serializers.py
  views.py         — ViewSet avec permissions
  urls.py          — router.register
  services.py      — logique métier
  tasks.py         — tâches Celery si nécessaire
  signals.py       — pour l'audit trail
  tests/
```

**Checklist pour chaque nouveau module :**

- [ ] Tous les modèles héritent de `BaseModel` (UUID, soft delete, horodatage)
- [ ] Chaque action pertinente appelle `log_action()` dans les services
- [ ] Les vues utilisent `ModulePermission` pour le contrôle d'accès
- [ ] Des tests sont présents pour les modèles, l'API et les services (coverage >= 70%)
- [ ] Les codes d'action sont enregistrés dans le catalogue `core/audit/action_codes.py`
- [ ] Les traductions des libellés UI sont ajoutées aux fichiers i18n dans `frontend/src/i18n/` dans les 5 langues

---

## Moteur IA M20 — intégration technique

### Architecture du module

```
apps/ai_engine/
├── sanitizer.py        # anonymisation des PII avant envoi au cloud
├── router.py           # choix local vs cloud selon la fonction
├── functions/
│   ├── classification.py
│   ├── text_analysis.py
│   ├── draft_generation.py
│   └── anomaly_detection.py
├── models.py           # AiInteractionLog
├── tasks.py            # jobs asynchrones détection d'anomalies
└── tests/
```

### AiInteractionLog

```python
class AiInteractionLog(BaseModel):
    function = models.CharField(max_length=50)
    # classification | text_analysis | draft_generation | anomaly_detection
    module_source = models.CharField(max_length=5)       # M04, M07, M09...
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)        # ex. gpt-4o | llama3.1:8b
    input_hash = models.CharField(max_length=64)         # SHA256 du prompt — jamais le texte
    output_ai = models.TextField()                       # sortie brute du modèle
    output_human_final = models.TextField(null=True)     # après confirmation/modification humaine
    delta = models.JSONField(null=True)                  # diff output_ai vs output_human_final
    confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(null=True)
    ignored = models.BooleanField(default=False)         # suggestion ignorée par l'utilisateur
```

`AiInteractionLog` est enregistré dans M10 via `log_action()` avec `action_code='ai.suggestion.confirmed'` ou `'ai.suggestion.ignored'`.

### Sanitizer

```python
# apps/ai_engine/sanitizer.py
class Sanitizer:
    """
    Anonymise le contexte avant de l'envoyer au LLM cloud.
    Mappe les tokens aux valeurs réelles pour la dé-anonymisation du résultat.
    """

    def sanitize(self, context: dict) -> tuple[dict, dict]:
        """
        Returns: (sanitized_context, token_map)
        token_map: { "[PLANT_A]": "Établissement Milan", ... }
        """
        ...

    def desanitize(self, text: str, token_map: dict) -> str:
        """Remplace les tokens par les valeurs réelles dans le texte généré."""
        ...
```

### Appeler une fonction IA depuis un service

```python
from apps.ai_engine.functions.classification import classify_incident_severity

# Dans le service M09 — incidents/services.py
async def suggest_severity(incident: Incident, request) -> dict | None:
    if not settings.AI_ENGINE_CONFIG['functions']['classification']['enabled']:
        return None

    result = await classify_incident_severity(
        description=incident.description,
        assets=[a.name for a in incident.assets.all()],
        plant_type=incident.plant.nis2_scope,
    )
    # result = { "suggested_severity": "alta", "confidence": 0.87, "reasoning": "..." }

    # Affiché à l'utilisateur comme suggestion — non appliqué automatiquement
    return result
```

### Validation humaine — flux API

```
POST /api/v1/ai/suggest/
{ "function": "classification", "entity_type": "incident", "entity_id": "..." }

→ 200 { "suggestion_id": "...", "output": { "suggested_severity": "alta" } }

# L'utilisateur accepte, modifie ou ignore
POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": true, "final_value": "alta" }
# → met à jour AiInteractionLog.confirmed_by et .output_human_final
# → applique la valeur à l'entité

POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": false }
# → AiInteractionLog.ignored = True
# → aucun effet sur l'entité
```

---

## Intégrations externes

### KnowBe4 (M15)

```python
# apps/training/kb4_client.py
class KnowBe4Client:
    BASE_URL = settings.KNOWBE4_API_URL

    def get_enrollments_delta(self, since: datetime) -> list[dict]:
        """Télécharge les complétions depuis l'horodatage indiqué."""
        ...

    def get_phishing_results(self, campaign_id: str) -> list[dict]:
        ...

    def provision_user(self, user: User, groups: list[str]) -> bool:
        """Crée ou met à jour l'utilisateur sur KB4 avec les groupes corrects (rôle+plant+langue)."""
        ...

    def deprovision_user(self, email: str) -> bool:
        """Révoque l'accès de l'utilisateur sur KB4 (appelé par signal post_save sur User.is_active=False)."""
        ...
```

La synchronisation est effectuée par la tâche Celery `training.tasks.sync_knowbe4` planifiée chaque nuit à 02:00.

### Webhook sortant (M19)

```python
# Structure du payload webhook
{
  "event": "risk.red_threshold_exceeded",
  "timestamp": "2026-03-13T10:00:00Z",
  "plant_id": "PLT-001",
  "plant_name": "...",              # inclus uniquement si le destinataire a accès
  "data": {
    "risk_id": "...",
    "score": 18,
    "asset_ids": ["..."]
  },
  "signature": "sha256=..."         # HMAC-SHA256 avec la clé configurée
}
```

---

## i18n — internationalisation

### Backend — Django i18n

```python
# Dans un modèle ou service — ne pas utiliser de chaînes codées en dur
from django.utils.translation import gettext_lazy as _

class ControlInstance(BaseModel):
    status = models.CharField(
        choices=[
            ('compliant', _('Compliant')),
            ('gap', _('Gap')),
        ]
    )
```

Les traductions backend se trouvent dans `backend/locale/{langue}/LC_MESSAGES/django.po` :

```bash
python manage.py makemessages -l pl
# Modifier locale/pl/LC_MESSAGES/django.po
python manage.py compilemessages
```

### Frontend — i18next

Fichiers de traduction :

```
frontend/src/i18n/
├── it/common.json
├── en/common.json
├── fr/common.json
├── pl/common.json
└── tr/common.json
```

Structure du fichier namespace :

```json
{
  "status": {
    "compliant": "Conforme",
    "gap": "Gap",
    "parziale": "Partiel",
    "na": "N/A",
    "non_valutato": "Non évalué"
  },
  "actions": {
    "save": "Enregistrer",
    "approve": "Approuver"
  }
}
```

Utilisation dans le composant React :

```typescript
import { useTranslation } from "react-i18next"

function ControlStatus({ status }: { status: string }) {
  const { t } = useTranslation()
  return <span>{t(`status.${status}`)}</span>
}
```

**Règle** : chaque clé ajoutée dans `it/common.json` ou `en/common.json` doit être ajoutée simultanément dans les 5 fichiers. Ne jamais laisser de clés manquantes dans une langue.

### Contrôles — traductions dans le JSON du référentiel

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

Le sérialiseur retourne automatiquement la traduction dans la langue du demandeur :

```python
# controls/serializers.py
def get_title(self, obj):
    lang = self.context['request'].user.profile.language  # it | en | fr | pl | tr
    return obj.translations.get(lang, {}).get('title') or obj.translations['en']['title']
```

---

## Frontend

### Gestion d'état

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

Cache automatique, invalidation lors des mutations, réessais exponentiels sur les erreurs réseau.

### Client API avec refresh automatique

```typescript
// api/client.ts — intercepteur JWT
apiClient.interceptors.response.use(
  r => r,
  async error => {
    if (error.response?.status === 401) {
      // refresh automatique du token via /api/auth/token/refresh/
      // si le refresh échoue, déconnexion et redirection vers /login
    }
  }
)
```

### Internationalisation

```typescript
import { useTranslation } from "react-i18next"

const { t } = useTranslation()
// Fichier : frontend/src/i18n/{it,en,fr,pl,tr}/common.json
// Règle : ajouter dans TOUTES les 5 langues simultanément
```

---

## Tests

### Exécution

```bash
# Suite complète backend
docker compose exec backend pytest
docker compose exec backend pytest --cov=apps --cov-report=html

# Test d'un seul module
docker compose exec backend pytest apps/audit_prep/

# Uniquement les tests rapides (sans DB)
pytest -m "not slow" tests/unit/

# Frontend
cd frontend && npm test
```

### Structure

```
apps/{module}/tests/
  test_models.py     — tests unitaires des modèles et services
  test_api.py        — tests des endpoints API avec APIClient
  test_services.py   — tests de la logique métier isolée
```

### Fixtures standard

```python
# conftest.py — disponibles dans tous les tests
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

### Test de l'audit trail

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
    # Vérifie la chaîne de hachage
    assert log.record_hash == compute_hash(log.payload, log.prev_hash)
```

### Objectif de couverture : >= 70%

La suite pytest (`backend/pytest.ini`, `--cov=apps --cov=core --cov-fail-under=70`) couvre la plupart des apps ; la couverture globale est suivie en CI (voir `CLAUDE.md` pour les chiffres à jour).

---

## Commandes de gestion

| Commande | Description | Quand exécuter |
|---------|-------------|-----------------|
| `migrate` | Applique les migrations DB | Après chaque déploiement |
| `load_frameworks` | Importe les référentiels normatifs JSON | Configuration initiale + mise à jour des référentiels |
| `load_notification_profiles` | Profils de notification par défaut | Configuration initiale |
| `load_competency_requirements` | Exigences de compétences M15 | Configuration initiale |
| `load_required_documents` | Documents obligatoires | Configuration initiale |
| `verify_audit_trail_integrity` | Vérifie la chaîne de hachage de l'audit trail | Mensuel + après restauration |
| `check --deploy` | Vérifie la configuration de production | Avant chaque déploiement |
| `createsuperuser` | Crée le premier administrateur | Configuration initiale |
| `seed_demo` | Charge les données de démonstration | Environnement de développement uniquement |
| `makemessages -l <lang>` | Extrait les chaînes i18n backend | Après ajout de nouvelles chaînes |
| `compilemessages` | Compile les fichiers .po en .mo | Après traduction |
| `sync_knowbe4 --full` | Synchronisation manuelle KnowBe4 | Récupération après erreur |

---

## Variables d'environnement

| Nom | Type | Défaut dev | Description | Obligatoire |
|------|------|------------|-------------|-------------|
| `SECRET_KEY` | string | — | Clé cryptographique Django | Oui |
| `FERNET_KEY` | string | — | AES-256 pour les identifiants SMTP | Oui |
| `DEBUG` | bool | True | False en production | Non |
| `ALLOWED_HOSTS` | string | localhost | Hôtes autorisés (séparés par virgule) | Oui en prod |
| `DATABASE_URL` | string | postgresql://grc:grc@db:5432/grc_dev | URL PostgreSQL | Oui |
| `REDIS_URL` | string | redis://redis:6379/0 | URL Redis | Oui |
| `FRONTEND_URL` | string | http://localhost:3001 | URL du frontend | Oui |
| `CORS_ALLOWED_ORIGINS` | string | http://localhost:3001 | Origines CORS | Non |
| `AI_ENGINE_ENABLED` | bool | False | Active le moteur IA M20 | Non |
| `KNOWBE4_API_KEY` | string | — | Clé API KnowBe4 | Uniquement si M15 actif |

---

## Conventions de développement

### Git

- Branches : `feature/M{nn}-description`, `fix/M{nn}-bug-description`, `chore/description`
- Commits : `feat(M09): ajoute le timer NIS2 avec compte à rebours visible`
- Une branche = un module ou une fonctionnalité cohérente
- Aucun commit direct sur `main` ou `develop`

### Python / Django

- Formateur : `ruff format` (compatible black)
- Linter : `ruff check`
- Annotations de type sur tous les services et les clients externes
- Docstring obligatoire sur les classes et méthodes publiques
- Aucune logique métier dans les vues — tout dans `services.py`
- Aucune requête N+1 — utiliser `select_related` et `prefetch_related`

### React / TypeScript

- TypeScript sur tous les composants
- Aucun `any` explicite
- Composants de présentation séparés des composants conteneurs
- Les appels API vont dans des hooks personnalisés (`useIncident`, `useControls`)
- Formateur : Prettier
- Linter : ESLint

### Sécurité

- Aucune information d'identification dans le code source
- Aucune donnée sensible dans les logs (utiliser le hachage ou le masquage)
- Token CSRF sur toutes les mutations
- Limitation de débit sur les endpoints publics et sur M20 IA
- Validation des entrées dans les sérialiseurs — ne jamais faire confiance au client

---

## Dépannage

### Celery Beat n'exécute pas les tâches planifiées

```bash
# Vérifier que le beat est en cours d'exécution
docker compose ps celery-beat
# Si non démarré : docker compose restart celery-beat

# Vérifier l'état des tâches planifiées
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(PeriodicTask.objects.filter(enabled=True).values('name','last_run_at'))"
```

### L'audit trail integrity check échoue

L'échec indique qu'un enregistrement a été modifié ou que la chaîne a été interrompue. Ne pas tenter de réparer — contacter l'équipe de sécurité. Le système génère automatiquement une alerte P1.

```bash
# Trouver le premier enregistrement corrompu
python manage.py verify_audit_trail_integrity --verbose
```

### L'import du référentiel échoue

```bash
python manage.py load_frameworks --file frameworks/nouveau.json --dry-run
# Affiche les différences sans les appliquer

python manage.py load_frameworks --file frameworks/nouveau.json --validate-only
# Valide le JSON sans importer
```

### La synchronisation KnowBe4 échoue

```bash
# Vérifier les identifiants
python manage.py shell -c "from apps.training.kb4_client import KnowBe4Client; print(KnowBe4Client().health_check())"

# Relancer la synchronisation manuellement
python manage.py sync_knowbe4 --full
```

### Token IA cloud non autorisé (M20)

1. Vérifier que `AI_ENGINE_ENABLED=true` et que la fonction spécifique est activée dans `AI_ENGINE_CONFIG`
2. Vérifier que la clé API est configurée et non expirée
3. Vérifier que le sanitizer ne génère pas d'erreurs : `grep "sanitizer" logs/app.log | tail -20`
4. En cas d'erreur persistante, le système bascule vers le modèle local si disponible

### La migration échoue en production

```bash
# Vérifier l'état des migrations avant de les appliquer
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Appliquer avec sortie verbeuse
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate --verbosity=2

# En cas de migration bloquée, vérifier les verrous sur la base de données
# Se connecter à PostgreSQL et vérifier pg_stat_activity
```

### Le frontend ne reçoit pas le token rafraîchi

Vérifier que le cookie `refresh_token` n'est pas expiré et que le domaine correspond. En développement, s'assurer que `CORS_ALLOW_CREDENTIALS = True` et que `FRONTEND_URL` est correctement défini.

### Le health check échoue

```bash
# Vérifier l'état des services
curl http://localhost:8001/api/health/
# Réponse attendue : {"status": "ok", "db": "ok"}

# Si db=error, vérifier la connexion PostgreSQL
docker compose ps db
docker compose logs db --tail=20
```
