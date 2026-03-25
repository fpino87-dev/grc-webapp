# Teknik Kılavuz — GRC Platform

> Geliştiriciler için kılavuz: mimari, veri modelleri, API, normatif çerçeveler, AI Engine, testler ve kurallar.

---

## İçindekiler

- [Stack ve versiyonlar](#stack-ve-versiyonlar)
- [Mimari](#mimari)
- [Depo yapısı](#depo-yapısı)
- [Ana modeller](#ana-modeller)
- [API](#api)
- [Güvenlik](#güvenlik)
- [Gizlilik ve GDPR](#gizlilik-ve-gdpr)
- [Denetim izi — yalnızca-ekleme ve hash zinciri](#denetim-izi--yalnızca-ekleme-ve-hash-zinciri)
- [Denetim Hazırlığı — teknik mantık](#denetim-hazırlığı--teknik-mantık)
- [Uyumluluk Takvimi (M08)](#uyumluluk-takvimi-m08)
- [Normatif çerçeve ekleme](#normatif-çerçeve-ekleme)
- [Modül ekleme](#modül-ekleme)
- [AI Engine M20 — teknik entegrasyon](#ai-engine-m20--teknik-entegrasyon)
- [Harici entegrasyonlar](#harici-entegrasyonlar)
- [i18n — uluslararasılaştırma](#i18n--uluslararasılaştırma)
- [Frontend](#frontend)
- [Testler](#testler)
- [Yönetim komutları](#yönetim-komutları)
- [Ortam değişkenleri](#ortam-değişkenleri)
- [Geliştirme kuralları](#geliştirme-kuralları)
- [Sorun giderme](#sorun-giderme)

---

## Stack ve versiyonlar

| Bileşen | Teknoloji | Versiyon |
|---------|-----------|---------|
| Backend çalışma zamanı | Python | 3.11 |
| Web çerçevesi | Django | 5.1 |
| REST API | Django REST Framework | 3.15 |
| Görev kuyruğu | Celery | 5.x |
| Önbellek/Broker | Redis | 7 |
| Veritabanı | PostgreSQL | 16 (Docker dev) |
| Üretim sunucusu | Gunicorn | — |
| Frontend çerçevesi | React | 18.3 |
| Derleme aracı | Vite | 5.4 |
| CSS | Tailwind CSS | 3.4 |
| Durum yönetimi | Zustand | 5.0 |
| Veri alımı | TanStack Query | 5.56 |
| Router | React Router | 7 |
| Frontend i18n | i18next | 23.10 |
| Markdown | react-markdown | 9.0 |
| Konteyner | Docker Compose | v2 |

---

## Mimari

### Mimari akış

```
frontend (React SPA)
    │  REST JSON / JWT
    ▼
backend (Django + DRF)
    │
    ├── apps/          her modül için bir Django uygulaması (M00–M20)
    ├── core/          ayarlar, middleware, temel modeller, auth
    └── frameworks/    normatif çerçeve JSON dosyaları (VDA ISA, NIS2, ISO 27001)
    │
    ├── PostgreSQL     ana veritabanı + yalnızca-ekleme denetim izi
    ├── Redis          oturum önbelleği + Celery broker
    └── S3 / MinIO     belgeler ve kanıtlar için nesne depolama
    │
    └── Celery Worker  asenkron görevler: bildirimler, KB4 senkronizasyonu, denetim izi işleri
        Celery Beat    tekrarlayan zamanlayıcılar: son tarihler, e-posta özeti, senkronizasyon
```

### Mimari ilkeler (CLAUDE.md'den)

Aşağıdaki ilkeler projenin tüm kodu için bağlayıcıdır. Bunlardan hiçbir zaman sapılması izin verilmez.

**1. BaseModel** — tüm modeller `core.models.BaseModel`'den miras alır

```python
class MyModel(BaseModel):
    name = models.CharField(max_length=100)
    # Miras alır: id (UUID pk), created_at, updated_at, deleted_at, created_by, soft_delete()
```

**2. İş mantığı services.py içinde** — view'lerde veya serializer'larda asla

```python
# ✅ Doğru
# apps/mymodule/services.py
def create_something(plant, user, data):
    obj = MyModel.objects.create(plant=plant, created_by=user, **data)
    log_action(user=user, action_code="mymodule.created", level="L2", entity=obj, payload={...})
    return obj

# ❌ Yanlış — view içinde mantık
def perform_create(self, serializer):
    obj = MyModel.objects.create(...)  # burada mantık = ihlal
```

**3. Zorunlu denetim günlüğü** — her ilgili eylem `log_action` çağırır

```python
from core.audit import log_action
log_action(
    user=request.user,
    action_code="mymodule.entity.action",  # format: app.entity.action
    level="L2",  # L1=güvenlik (5yıl), L2=uyumluluk (3yıl), L3=operasyonel (1yıl)
    entity=instance,
    payload={"key": "value"},  # KİŞİSEL VERİ YOK, yalnızca sayılar/ID'ler
)
```

**4. Soft delete** — doğrudan `queryset.delete()` asla

```python
# ✅ Doğru
instance.soft_delete()

# ❌ Yanlış
instance.delete()
MyModel.objects.filter(...).delete()
```

**5. N+1 yok** — `select_related` ve `prefetch_related` zorunlu

```python
# ✅ Doğru
queryset = MyModel.objects.select_related("plant", "created_by").prefetch_related("items")

# ❌ Yanlış
for obj in MyModel.objects.all():
    print(obj.plant.name)  # N+1!
```

**6. Göreve rol atanır** (`UserPlantAccess` üzerinden dinamik çözümleme), doğrudan kullanıcıya asla.

**7. Normatif çerçeveler = JSON** `backend/frameworks/` içinde — kontrolleri kodda doğrudan yazmayın.

**8. M20 AI Engine**: bulut LLM'ye göndermeden önce her zaman `Sanitizer.sanitize()`; herhangi bir AI çıktısını uygulamadan önce insan-döngüde-onay.

**9. Soft delete yöneticisi** varsayılandır — `.all_with_deleted()` yalnızca açıkça gerekli olduğunda.

**10. PII asla günlüğe yazılmaz** — sistem günlüklerinde yalnızca sayılar veya anonim tanımlayıcılar.

**11. Dosya yükleme**: her zaman MIME kontrolüyle `validate_uploaded_file()` (python-magic).

**12. Üretim**: `docker-compose.prod.yml` ve `Dockerfile.prod`.

**13. Zorunlu çeviriler**: `it/common.json` veya `en/common.json`'a eklenen her i18n anahtarı aynı anda tüm 5 dilde çevrilmelidir (IT, EN, FR, PL, TR).

Ek bağlayıcı ilkeler:

- Veri olarak çerçeve: kontroller JSON'dur, kod değil. DORA eklemek dağıtım gerektirmez.
- BT/OT tablo kalıtımı: `Asset` temel + `AssetIT` ve `AssetOT` — gereksiz nullable sütun yok.
- RBAC (M02) normatif yönetişimden (M00) ayrı: uygulama izinleri vs. resmi atamalar.
- SHA-256 hash zinciri ile yalnızca-ekleme denetim izi: yalnızca prosedürel değil teknik değişmezlik.
- Dinamik çözümlemeyle göreve rol atanır: personel değişikliği manuel yeniden tahsis gerektirmez.
- Çerçeve sürümleri değiştirilemez: arşivlenir, asla silinmez.

### Örneklerle zorunlu kalıplar

**Tam service kalıbı:**

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

**Otomatik yeniden deneme ile Celery görevi:**

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def my_scheduled_task(self):
    # görev mantığı
    return "done"
```

**Destroy kalıbı (soft delete):**

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

### Ana veri akışı

```
BIA.downtime_cost → RiskAssessment.ale_eur (hesaplanan)
RiskAssessment(score > 14) → Acil Task + otomatik PDCA
Incident.close() → otomatik PDCA + LessonLearned
AuditFinding.close() → otomatik PDCA + LessonLearned
BcpTest(başarısız) → otomatik PDCA
PDCA.close() → kaynak modülü günceller + LessonLearned
```

### Geliştirme ortamı kurulumu

#### Önkoşullar

```bash
python --version     # >= 3.11
node --version       # >= 20
docker --version     # >= 4.x
```

#### İlk başlatma

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
python manage.py load_frameworks       # VDA ISA, NIS2, ISO 27001 içe aktarır
python manage.py seed_demo             # isteğe bağlı demo verileri
python manage.py createsuperuser

# Backend'i başlat
python manage.py runserver 0.0.0.0:8000

# Frontend (başka bir terminalde)
cd frontend
npm install
npm run dev
```

#### Makefile komutları

```bash
make dev          # docker compose up + runserver + npm run dev
make migrate      # python manage.py migrate
make test         # pytest (backend) + npm test / vitest (frontend)
make lint         # ruff (backend)
make load-fw      # python manage.py load_frameworks
make seed         # python manage.py seed_demo
make shell        # python manage.py shell_plus
make celery       # Celery worker'ı ön planda başlatır
```

---

## Depo yapısı

### Backend

```
backend/
├── core/
│   ├── settings/
│   │   ├── base.py          # paylaşılan ayarlar (JWT, DRF, INSTALLED_APPS, CELERY)
│   │   ├── dev.py           # geliştirme geçersiz kılmaları (DEBUG=True, isteğe bağlı SQLite)
│   │   └── prod.py          # üretim geçersiz kılmaları (ALLOWED_HOSTS, SECURE_*, günlükleme)
│   ├── models.py            # BaseModel, SoftDeleteManager
│   ├── audit.py             # log_action(), compute_hash()
│   ├── validators.py        # MIME kontrolüyle validate_uploaded_file()
│   ├── permissions.py       # ModulePermission, PlantScopedPermission
│   ├── middleware.py        # PlantContextMiddleware, RequestLoggingMiddleware
│   └── urls.py              # her uygulama için include içeren kök URL
├── apps/
│   ├── governance/          # M00 — Yönetişim & Roller
│   ├── plants/              # M01 — Tesis Kayıt Defteri
│   ├── auth_grc/            # M02 — RBAC + JWT
│   ├── controls/            # M03 — Kontrol Kütüphanesi + load_frameworks komutu
│   ├── assets/              # M04 — BT/OT Varlıkları
│   ├── bia/                 # M05 — BIA
│   ├── risk/                # M06 — Risk Değerlendirmesi
│   ├── documents/           # M07 — Belgeler
│   ├── tasks/               # M08 — Görev Yönetimi + Uyumluluk Takvimi
│   ├── incidents/           # M09 — NIS2 Olayları
│   ├── audit_trail/         # M10 — Denetim İzi (salt okunur view'lar)
│   ├── pdca/                # M11 — PDCA
│   ├── lessons/             # M12 — Alınan Dersler
│   ├── management_review/   # M13 — Yönetim Gözden Geçirme
│   ├── suppliers/           # M14 — Tedarikçiler
│   ├── training/            # M15 — Eğitim/KnowBe4
│   ├── bcp/                 # M16 — BCP
│   ├── audit_prep/          # M17 — Denetim Hazırlığı
│   ├── reporting/           # M18 — Raporlama (model yok, yalnızca toplama view'ları)
│   ├── notifications/       # M19 — Bildirimler
│   └── ai_engine/           # M20 — AI Engine + Sanitizer
└── frameworks/
    ├── iso27001.json
    ├── nis2.json
    ├── tisax_l2.json
    └── tisax_l3.json
```

### Modül uygulaması yapısı

```
apps/incidents/          # M09 — Olay Yönetimi
├── __init__.py
├── admin.py
├── apps.py
├── models.py            # Incident, IncidentNotification, RCA, ...
├── serializers.py       # DRF serializer'ları
├── views.py             # API ViewSet
├── urls.py              # router.register(...)
├── permissions.py       # modüle özgü izinler
├── services.py          # iş mantığı — view'da değil
├── tasks.py             # modülün Celery görevleri
├── signals.py           # denetim izi için post_save, post_delete
└── tests/
    ├── test_models.py
    ├── test_api.py
    └── test_services.py
```

### Frontend

```
frontend/src/
├── App.tsx                    # Router — modüller, takvim, ayarlar
├── main.tsx                   # QueryClientProvider + i18n ile giriş noktası
├── store/
│   └── auth.ts                # Zustand: user, token, selectedPlant
├── api/
│   ├── client.ts              # JWT interceptor + otomatik yenileme ile axios
│   └── endpoints/             # TypeScript API istemcisi (~24 dosya)
├── components/
│   ├── layout/
│   │   ├── Shell.tsx          # Kenar çubuğu ile ana düzen
│   │   ├── Sidebar.tsx        # M00–M20 için öğelerle yan gezinme
│   │   ├── Topbar.tsx         # Tesis seçimi ve dil ile üst çubuk
│   │   └── BottomBar.tsx      # Mobil alt çubuk
│   └── ui/
│       ├── AiSuggestion.tsx   # Kabul Et/Düzenle/Yoksay ile AI başlığı
│       ├── CountdownTimer.tsx # Gerçek zamanlı NIS2 geri sayımı
│       ├── StatusBadge.tsx    # Uyumluluk durumları için renkli rozet
│       └── ManualDrawer.tsx   # Bağlamsal kılavuz çekmecesi (? düğmesi)
├── modules/                   # Her modül için bir klasör (M00–M20)
│   ├── dashboard/Dashboard.tsx
│   ├── controls/ControlsList.tsx
│   ├── incidents/IncidentsList.tsx
│   └── ...
├── pages/
│   └── LoginPage.tsx
└── i18n/
    ├── index.ts               # i18next yapılandırması
    ├── it/common.json
    ├── en/common.json
    ├── fr/common.json
    ├── pl/common.json
    └── tr/common.json
```

---

## Ana modeller

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

    objects = SoftDeleteManager()  # varsayılan olarak deleted_at null olanları filtreler

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    class Meta:
        abstract = True
```

Uygulamanın tüm modelleri `BaseModel`'den miras alır. Hiçbir zaman doğrudan `delete()` kullanmayın — `soft_delete()` kullanın.

### AuditLog

```python
class AuditLog(models.Model):
    # BaseModel'den miras almaz — soft delete yok, updated_at yok
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)

    # Kim
    user_id = models.UUIDField()
    user_email_at_time = models.CharField(max_length=255)
    user_role_at_time = models.CharField(max_length=50)   # o anki rol anlık görüntüsü

    # Ne
    action_code = models.CharField(max_length=100)        # ör. incident.created
    level = models.CharField(max_length=2)                # L1 | L2 | L3
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField()                          # eylemin ilgili verileri

    # SHA-256 hash zinciri
    prev_hash = models.CharField(max_length=64)
    record_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'audit_log'
        # RANGE (timestamp_utc) ile bölümlenmiş — migrasyonda tanımlı
```

AuditLog'un temel özellikleri:

- SHA-256 hash zinciri: her kayıt `prev_hash` + `record_hash` içerir
- PostgreSQL tetikleyicisi UPDATE/DELETE'i engeller
- Race condition'ı önlemek için `_get_prev_hash()` içinde `select_for_update()`
- L1/L2/L3 seviyeleri 5/3/1 yıl saklama ile
- Doğrulama: `python manage.py verify_audit_trail_integrity`

### ControlInstance

- SOA ISO 27001 için `applicability` alanı
- VDA ISA için `calc_maturity_level()` (0-5 ölçeği)
- Değişiklik yönetimi için `needs_revaluation` (M04)

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
    na_review_by = models.DateField(null=True)            # TISAX L3 için en fazla 12 ay
    notes = models.TextField(blank=True)
    last_evaluated_at = models.DateTimeField(null=True)
```

### RiskAssessment

- İçsel vs. kalıntı risk (BT için 6 boyut + OT için 4)
- BIA çarpanıyla (`downtime_cost`) `weighted_score`
- `risk_level`: yeşil ≤7, sarı ≤14, kırmızı >14
- Puan > 14 ise otomatik PDCA tetiklenir

### M00 — Yönetişim

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

### M01 — Tesis Kayıt Defteri

```python
class Plant(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=2)  # ISO 3166-1 alfa-2
    bu = models.ForeignKey('BusinessUnit', null=True, on_delete=models.SET_NULL)
    parent_plant = models.ForeignKey('self', null=True, on_delete=models.SET_NULL)
    has_ot = models.BooleanField(default=False)
    purdue_level_max = models.IntegerField(null=True)
    nis2_scope = models.CharField(
        max_length=20,
        choices=[('essenziale','Essenziale'),('importante','Importante'),('non_soggetto','Non soggetto')]
    )
    status = models.CharField(max_length=20)  # aktif | kullanım_dışı | kapalı

class PlantFramework(BaseModel):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    framework = models.ForeignKey('controls.Framework', on_delete=models.CASCADE)
    active_from = models.DateField()
    level = models.CharField(max_length=10, null=True)  # ör. TISAX için L2 veya L3

    class Meta:
        unique_together = ['plant', 'framework']
```

### M04 — Varlık

```python
class Asset(BaseModel):
    """Temel tablo — tablo kalıtımı"""
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10)          # BT | OT
    criticality = models.IntegerField(default=1)          # 1–5, süreçten miras alınır
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
    category = models.CharField(max_length=20)            # PLC | SCADA | HMI | RTU | sensör
    patchable = models.BooleanField(default=False)
    patch_block_reason = models.TextField(blank=True)
    maintenance_window = models.CharField(max_length=100, blank=True)
    network_zone = models.ForeignKey('NetworkZone', null=True, on_delete=models.SET_NULL)
```

### M09 — Olaylar

```python
class Incident(BaseModel):
    plant = models.ForeignKey('plants.Plant', on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField()
    detected_at = models.DateTimeField()
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assets = models.ManyToManyField('assets.Asset', blank=True)
    severity = models.CharField(max_length=10)            # düşük|orta|yüksek|kritik
    nis2_notifiable = models.CharField(max_length=15)     # evet|hayır|değerlendirilecek
    nis2_confirmed_at = models.DateTimeField(null=True)
    nis2_confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    status = models.CharField(max_length=20)              # açık|analiz_aşamasında|kapalı
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

### Kimlik doğrulama

```
Authorization: Bearer <JWT-token>
```

JWT token'larının ACCESS süresi 30 dakikadır. Kullanıcı aktifse (REFRESH=7 gün) yenileme axios interceptor aracılığıyla otomatik gerçekleşir. Harici denetçiler kapsam ve süresi sınırlı özel token'lar kullanır (M02 tarafından oluşturulur).

### URL kuralları

```
GET    /api/v1/{modül}/                  # filtreleme ve sayfalandırma ile liste
POST   /api/v1/{modül}/                  # oluştur
GET    /api/v1/{modül}/{id}/             # detay
PATCH  /api/v1/{modül}/{id}/             # kısmi güncelleme
DELETE /api/v1/{modül}/{id}/             # soft delete (deleted_at)

# Özel eylemler
POST   /api/v1/incidents/{id}/confirm_nis2/
POST   /api/v1/incidents/{id}/send_notification/
POST   /api/v1/documents/{id}/approve/
POST   /api/v1/controls/{id}/evaluate/
```

### Ana endpoint'ler

Temel URL: `/api/v1/`

| Endpoint | Metotlar | Açıklama |
|----------|---------|----------|
| `governance/roles/` | GET, POST, PUT, DELETE | M00 normatif roller |
| `plants/` | GET, POST | M01 tesis kayıt defteri |
| `auth/users/` | GET, POST | M02 kullanıcılar |
| `controls/instances/` | GET, PUT | M03 kontroller |
| `controls/export/` | GET | SOA/VDA/NIS2 dışa aktarma |
| `assets/` | GET, POST | M04 BT/OT varlıkları |
| `bia/processes/` | GET, POST | M05 BIA |
| `risk/assessments/` | GET, POST | M06 risk |
| `documents/` | GET, POST | M07 belgeler |
| `tasks/` | GET, POST | M08 görevler |
| `incidents/` | GET, POST | M09 olaylar |
| `audit-trail/` | GET | M10 denetim izi (salt okunur) |
| `pdca/` | GET, POST | M11 PDCA |
| `lessons/` | GET, POST | M12 alınan dersler |
| `management-review/` | GET, POST | M13 yönetim gözden geçirme |
| `suppliers/` | GET, POST | M14 tedarikçiler |
| `training/` | GET, POST | M15 eğitim |
| `bcp/` | GET, POST | M16 BCP |
| `audit-prep/preps/` | GET, POST | M17 denetim hazırlığı |
| `audit-prep/programs/` | GET, POST | M17 denetim programları |
| `reporting/dashboard-summary/` | GET | M18 toplama panosu |
| `reporting/kpi-trend/` | GET | M18 KPI trendi |
| `notifications/` | GET | M19 bildirimler |
| `manual/<type>/` | GET | Kılavuzlar (kullanıcı/teknik) |

### Filtreler ve sayfalandırma

```
GET /api/v1/controls/?framework=VDA_ISA_6_0&plant=PLT-001&status=gap&page=2&page_size=25
```

Tüm liste endpoint'leri şunları destekler:

- `page` ve `page_size` (varsayılan 25, maksimum 100)
- `ordering` (ör. `ordering=-created_at`)
- `/api/v1/schema/` (OpenAPI 3.0) içinde belgelenen modüle özgü filtreler

### Standart yanıt

```json
{
  "count": 83,
  "next": "/api/v1/controls/?page=2",
  "previous": null,
  "results": [...]
}
```

### Hatalar

```json
{
  "error": "validation_error",
  "detail": {
    "status": ["'invalid' değeri geçerli bir seçim değil."],
    "owner": ["Bu alan zorunludur."]
  }
}
```

Kullanılan HTTP kodları: 200, 201, 204, 400, 401, 403, 404, 409 (durum çakışması), 422 (iş mantığı hatası), 500.

### Uyumluluk dışa aktarma

Dosya indirme işlemi başlıkta JWT gerektirir. Token'ı taşımayan `window.open()` kullanmayın.

```typescript
// ✅ Doğru — Authorization başlığıyla fetch() kullan
const response = await fetch(
  `/api/v1/controls/export/?framework=ISO27001&format=soa&plant=${plantId}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const blob = await response.blob();

// ❌ Yanlış — window.open() JWT'yi geçirmez
window.open(`/api/v1/controls/export/?framework=ISO27001`);
```

### Giden genel API (M19)

```
GET /api/external/v1/plants/           # nis2_scope ile tesis listesi
GET /api/external/v1/controls/         # tesise göre durumlu kontroller
GET /api/external/v1/risks/            # açık risk değerlendirmeleri

Kimlik doğrulama: başlıkta API anahtarı  X-API-Key: <anahtar>
Hız sınırı: anahtar başına 100 istek/dk
```

---

## Güvenlik

### JWT yapılandırması

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

### Hız sınırlama

Temel hız sınırlama `AnonRateThrottle` ve `UserRateThrottle` kullanır:

- `AnonRateThrottle`: 20/sa
- `UserRateThrottle`: 500/sa
- `LoginRateThrottle`: 5/dk (`GrcTokenObtainPairView` üzerinde)

ViewSet'te `throttle_classes` geçersiz kılınarak hassas endpoint'ler için özelleştirilebilir.

### Güvenli dosya yükleme

```python
from core.validators import validate_uploaded_file

# Doğrular: boyut + uzantı beyaz listesi + gerçek MIME türü (python-magic)
validate_uploaded_file(request.FILES["file"])
```

### SMTP kimlik bilgisi şifreleme

```python
# EncryptedCharField Fernet AES-256 kullanır
# FERNET_KEY .env içinde zorunlu — güvenli varsayılan yok
class EmailConfiguration(BaseModel):
    smtp_password = EncryptedCharField(max_length=500)
```

### Parola politikası

- Minimum 12 karakter
- `CommonPasswordValidator`
- `NumericPasswordValidator`
- `UserAttributeSimilarityValidator`

### Servis endpoint'leri

Bazı yönetim endpoint'leri (ör. `auth_grc.ResetTestDbView` içindeki test DB sıfırlama), test ortamları dışında yanlış kullanımı önlemek için `settings.DEBUG` kontrolü aracılığıyla üretimde açıkça engellenir.

---

## Gizlilik ve GDPR

### Kullanıcı anonimleştirme (GDPR Madde 17)

```python
from apps.auth_grc.services import anonymize_user

anonymize_user(user_id)
# Ad, e-posta, telefon kaldırır — denetim izi bütünlüğünü korur
# Endpoint: POST /api/v1/auth/users/{id}/anonymize/
```

### AI Sanitizer

```python
from apps.ai_engine.sanitizer import Sanitizer

safe_text = Sanitizer.sanitize(raw_text)
# Kaldırır: e-posta, IP, VAT no, vergi no, telefon, tesis adları
# Bulut LLM'ye göndermeden önce DAIMA kullanın
```

### Denetim günlüğü otomatik saklama

- L1 (güvenlik): 5 yıl
- L2 (uyumluluk): 3 yıl
- L3 (operasyonel): 1 yıl
- Zamanlama: her ayın 1'inde saat 03:00 (`cleanup_expired_audit_logs` görevi)

---

## Denetim izi — yalnızca-ekleme ve hash zinciri

### İlke

Her ilgili eylem bir `AuditLog` kaydı yazar. Kayıt değiştirilemez: PostgreSQL tetikleyicisi UPDATE ve DELETE'i reddeder. Her kayıt `prev_hash` ve `record_hash = SHA256(json_payload + prev_hash)` içererek doğrulanabilir bir zincir oluşturur.

### Bir eylemi günlüğe kaydetme

```python
from core.audit import log_action

# Bir service veya post_save sinyalinde
log_action(
    request=request,            # kullanıcı ve geçerli rolü çıkarmak için
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

`core.audit` modülü otomatik olarak yönetir:

- Çağrı anındaki `user_role_at_time` anlık görüntüsü
- `prev_hash` hesaplama (entity_type için son kaydı okur) ve `record_hash`
- Race condition'ı önlemek için `select_for_update()` ile işlemsel yazma
- Günlük başarısız olursa istisna oluşturulur (işlem geri alınır)

### Bütünlük doğrulama

```bash
# Tüm zinciri kontrol eder: her hash'i yeniden hesaplar ve karşılaştırır
python manage.py verify_audit_trail_integrity

# İlk bozuk kaydı bulur
python manage.py verify_audit_trail_integrity --verbose

# Gece görevi (Celery Beat — zaten yapılandırıldı)
# Zincir kırıksa uyarı gönderir
```

---

## Denetim Hazırlığı — teknik mantık

### suggest_audit_plan()

- Açık boşluklarla alanları önceliklendirir (en yüksek `gap_pct`)
- Çalıştırmalar arasında tekrarlanabilir örnek için belirleyici tohum (MD5 hash `program_id` + `quarter`)
- `seen_domains` sözlüğü aracılığıyla çerçeveler arası alan tekilleştirme
- Örnek dağılımı: `campione`=%25, `esteso`=%50, `full`=%100

### launch_audit_from_program()

- `transaction.atomic()` — tamamen atomik operasyon
- EvidenceItem için `bulk_create` (N yerine tek INSERT)
- `perform_update()` içinde otomatik olarak çağrılan `sync_program_completion()`

### Hatırlatma görevi (check_upcoming_audits)

- Haftalık görev vs. haftanın ortasındaki tarihleri yönetmek için ±4 günlük aralık
- 28-32 gün önce: hazırlık görevi
- 5-9 gün önce: AuditPrep henüz başlatılmamışsa acil görev
- Tarihten 0-3 gün sonra: AuditPrep başlatılmamışsa kritik uyarı

---

## Uyumluluk Takvimi (M08)

### Son tarih hesaplama

```python
from apps.compliance_schedule.services import get_due_date

due = get_due_date("finding_major", plant=plant, from_date=date.today())
# Yönetici kullanıcı arayüzünden yapılandırılabilir 23 kural türü
```

---

## Normatif çerçeve ekleme

Çerçeveler `backend/frameworks/` içindeki JSON dosyalarıdır. Python koduna dokunmaya gerek yoktur.

### JSON yapısı

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

### İçe aktarma

```bash
# Yeni çerçeveyi içe aktarır
python manage.py load_frameworks --file frameworks/nist_csf_2_0.json

# Komut:
# 1. Çerçeveyi ve tüm Kontrolleri oluşturur
# 2. Diğer çerçevelerle ControlMapping oluşturur
# 3. ControlInstance oluşturmaz (bir tesiste çerçeve etkinleştirildiğinde oluşturulur)

# Bir tesiste çerçeveyi etkinleştirme (yönetici veya API aracılığıyla)
POST /api/v1/plant-frameworks/
{ "plant": "PLT-001", "framework": "NIST_CSF_2_0", "active_from": "2026-03-13" }
# → her kontrol için otomatik olarak non_valutato durumunda ControlInstance oluşturur
```

### Çerçeve sürümleme

Mevcut bir çerçevenin yeni sürümü çıktığında:

1. Aynı `code` ancak güncellenmiş `version` içeren yeni bir JSON dosyası oluşturun (ör. `VDA_ISA_6_1`)
2. `load_frameworks --version-update` komutu kontrolleri karşılaştırır:
   - Değişmeyenler: otomatik olarak aynı durumla taşınır
   - Değişenler: inceleme görevi ile `non_valutato` durumunda yeni `ControlInstance` oluşturulur
   - Silinenler: notla arşivlenir (`archived_at`)
   - Yeniler: `non_valutato` durumunda oluşturulur

Önceki sürüm hiçbir zaman silinmez — geçmiş denetimlere arşivlenir.

---

## Modül ekleme

Yeni bir işlevsel modül eklemek için (ör. M21):

```bash
# 1. Django uygulamasını oluştur
cd backend
python manage.py startapp new_module apps/new_module

# 2. core/settings/base.py içindeki INSTALLED_APPS'e ekle
INSTALLED_APPS = [
    ...
    'apps.new_module',
]

# 3. URL'leri backend/core/urls.py içine kaydet
path('api/v1/new-module/', include('apps.new_module.urls')),
```

Zorunlu minimum yapı:

```
apps/new_module/
  models.py        — BaseModel'den miras al
  serializers.py
  views.py         — izinli ViewSet
  urls.py          — router.register
  services.py      — iş mantığı
  tasks.py         — gerekirse Celery görevleri
  signals.py       — denetim izi için
  tests/
```

**Her yeni modül için kontrol listesi:**

- [ ] Tüm modeller `BaseModel`'den miras alır (UUID, soft delete, zaman damgası)
- [ ] Her ilgili eylem service'lerde `log_action()` çağırır
- [ ] View'lar erişim kontrolü için `ModulePermission` kullanır
- [ ] Modeller, API ve service için testler mevcut (coverage >= %70)
- [ ] Eylem kodları `core/audit/action_codes.py` kataloğuna kayıtlı
- [ ] UI etiket çevirileri `frontend/src/i18n/` içindeki i18n dosyalarına tüm 5 dilde eklendi

---

## AI Engine M20 — teknik entegrasyon

### Modül mimarisi

```
apps/ai_engine/
├── sanitizer.py        # buluta göndermeden önce PII anonimleştirme
├── router.py           # fonksiyona göre yerel vs. bulut seçimi
├── functions/
│   ├── classification.py
│   ├── text_analysis.py
│   ├── draft_generation.py
│   └── anomaly_detection.py
├── models.py           # AiInteractionLog
├── tasks.py            # anomali tespiti için asenkron işler
└── tests/
```

### AiInteractionLog

```python
class AiInteractionLog(BaseModel):
    function = models.CharField(max_length=50)
    # classification | text_analysis | draft_generation | anomaly_detection
    module_source = models.CharField(max_length=5)       # M04, M07, M09...
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)        # ör. gpt-4o | llama3.1:8b
    input_hash = models.CharField(max_length=64)         # istemcinin SHA256'sı — metin asla
    output_ai = models.TextField()                       # modelin ham çıktısı
    output_human_final = models.TextField(null=True)     # insanın onayı/düzenlemesinden sonra
    delta = models.JSONField(null=True)                  # output_ai ile output_human_final arasındaki fark
    confirmed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(null=True)
    ignored = models.BooleanField(default=False)         # kullanıcı tarafından yoksayılan öneri
```

`AiInteractionLog`, M10'da `action_code='ai.suggestion.confirmed'` veya `'ai.suggestion.ignored'` ile `log_action()` aracılığıyla kayıt altına alınır.

### Sanitizer

```python
# apps/ai_engine/sanitizer.py
class Sanitizer:
    """
    Bulut LLM'ye göndermeden önce bağlamı anonimleştirir.
    Sonucu anonim kaldırma için token'ları gerçek değerlerle eşleştirir.
    """

    def sanitize(self, context: dict) -> tuple[dict, dict]:
        """
        Döndürür: (sanitized_context, token_map)
        token_map: { "[PLANT_A]": "Milano Tesisi", ... }
        """
        ...

    def desanitize(self, text: str, token_map: dict) -> str:
        """Oluşturulan metindeki token'ları gerçek değerlerle değiştirir."""
        ...
```

### Bir service'den AI fonksiyonu çağırma

```python
from apps.ai_engine.functions.classification import classify_incident_severity

# M09 service'inde — incidents/services.py
async def suggest_severity(incident: Incident, request) -> dict | None:
    if not settings.AI_ENGINE_CONFIG['functions']['classification']['enabled']:
        return None

    result = await classify_incident_severity(
        description=incident.description,
        assets=[a.name for a in incident.assets.all()],
        plant_type=incident.plant.nis2_scope,
    )
    # result = { "suggested_severity": "alta", "confidence": 0.87, "reasoning": "..." }

    # Kullanıcıya öneri olarak gösterilir — otomatik uygulanmaz
    return result
```

### İnsan-döngüde-onay — API akışı

```
POST /api/v1/ai/suggest/
{ "function": "classification", "entity_type": "incident", "entity_id": "..." }

→ 200 { "suggestion_id": "...", "output": { "suggested_severity": "alta" } }

# Kullanıcı kabul eder, düzenler veya yoksayar
POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": true, "final_value": "alta" }
# → AiInteractionLog.confirmed_by ve .output_human_final günceller
# → değeri varlığa uygular

POST /api/v1/ai/confirm/
{ "suggestion_id": "...", "accepted": false }
# → AiInteractionLog.ignored = True
# → varlık üzerinde hiçbir etki yok
```

---

## Harici entegrasyonlar

### KnowBe4 (M15)

```python
# apps/training/kb4_client.py
class KnowBe4Client:
    BASE_URL = settings.KNOWBE4_API_URL

    def get_enrollments_delta(self, since: datetime) -> list[dict]:
        """Belirtilen zaman damgasından bu yana tamamlamaları indirir."""
        ...

    def get_phishing_results(self, campaign_id: str) -> list[dict]:
        ...

    def provision_user(self, user: User, groups: list[str]) -> bool:
        """KB4'te doğru gruplarla kullanıcı oluşturur veya günceller (rol+tesis+dil)."""
        ...

    def deprovision_user(self, email: str) -> bool:
        """KB4'te kullanıcı erişimini iptal eder (User.is_active=False için post_save sinyali tarafından çağrılır)."""
        ...
```

Senkronizasyon, her gece saat 02:00'de zamanlanmış `training.tasks.sync_knowbe4` Celery görevi tarafından yürütülür.

### Giden webhook (M19)

```python
# Webhook yük yapısı
{
  "event": "risk.red_threshold_exceeded",
  "timestamp": "2026-03-13T10:00:00Z",
  "plant_id": "PLT-001",
  "plant_name": "...",              # yalnızca alıcının erişimi varsa dahil edilir
  "data": {
    "risk_id": "...",
    "score": 18,
    "asset_ids": ["..."]
  },
  "signature": "sha256=..."         # yapılandırılmış anahtarla HMAC-SHA256
}
```

---

## i18n — uluslararasılaştırma

### Backend — Django i18n

```python
# Bir model veya service'de — hardcoded string kullanmayın
from django.utils.translation import gettext_lazy as _

class ControlInstance(BaseModel):
    status = models.CharField(
        choices=[
            ('compliant', _('Compliant')),
            ('gap', _('Gap')),
        ]
    )
```

Backend çevirileri `backend/locale/{dil}/LC_MESSAGES/django.po` içindedir:

```bash
python manage.py makemessages -l pl
# locale/pl/LC_MESSAGES/django.po dosyasını düzenle
python manage.py compilemessages
```

### Frontend — i18next

Çeviri dosyaları:

```
frontend/src/i18n/
├── it/common.json
├── en/common.json
├── fr/common.json
├── pl/common.json
└── tr/common.json
```

Namespace dosya yapısı:

```json
{
  "status": {
    "compliant": "Uyumlu",
    "gap": "Boşluk",
    "parziale": "Kısmi",
    "na": "N/A",
    "non_valutato": "Değerlendirilmedi"
  },
  "actions": {
    "save": "Kaydet",
    "approve": "Onayla"
  }
}
```

React bileşeninde kullanım:

```typescript
import { useTranslation } from "react-i18next"

function ControlStatus({ status }: { status: string }) {
  const { t } = useTranslation()
  return <span>{t(`status.${status}`)}</span>
}
```

**Kural**: `it/common.json` veya `en/common.json`'a eklenen her anahtar aynı anda tüm 5 dosyaya eklenmeli. Hiçbir zaman bir dilde eksik anahtar bırakmayın.

### Kontroller — çerçeve JSON'unda çeviriler

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

Serializer, istekte bulunanın diline çeviriyi otomatik döndürür:

```python
# controls/serializers.py
def get_title(self, obj):
    lang = self.context['request'].user.profile.language  # it | en | fr | pl | tr
    return obj.translations.get(lang, {}).get('title') or obj.translations['en']['title']
```

---

## Frontend

### Durum yönetimi

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

Otomatik önbellek, mutasyonda geçersiz kılma, ağ hatalarında üstel yeniden deneme.

### Otomatik yenileme ile API istemcisi

```typescript
// api/client.ts — JWT interceptor
apiClient.interceptors.response.use(
  r => r,
  async error => {
    if (error.response?.status === 401) {
      // /api/auth/token/refresh/ aracılığıyla otomatik token yenileme
      // yenileme başarısız olursa çıkış yap ve /login'e yönlendir
    }
  }
)
```

### Uluslararasılaştırma

```typescript
import { useTranslation } from "react-i18next"

const { t } = useTranslation()
// Dosya: frontend/src/i18n/{it,en,fr,pl,tr}/common.json
// Kural: aynı anda TÜM 5 dile ekle
```

---

## Testler

### Yürütme

```bash
# Tam backend paketi
docker compose exec backend pytest
docker compose exec backend pytest --cov=apps --cov-report=html

# Tek modül testi
docker compose exec backend pytest apps/audit_prep/

# Yalnızca hızlı testler (DB olmadan)
pytest -m "not slow" tests/unit/

# Frontend
cd frontend && npm test
```

### Yapı

```
apps/{modül}/tests/
  test_models.py     — model ve service birim testleri
  test_api.py        — APIClient ile API endpoint testleri
  test_services.py   — izole iş mantığı testleri
```

### Standart fixture'lar

```python
# conftest.py — tüm testlerde kullanılabilir
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

### Denetim izi testi

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
    # Hash zincirini doğrula
    assert log.record_hash == compute_hash(log.payload, log.prev_hash)
```

### Coverage hedefi: >= 70%

pytest paketi (`backend/pytest.ini`, `--cov=apps --cov=core --cov-fail-under=70`) çoğu uygulamayı kapsar; genel coverage CI’da izlenir (güncel rakamlar için `CLAUDE.md`).

---

## Yönetim komutları

| Komut | Açıklama | Ne zaman çalıştırılacak |
|-------|----------|------------------------|
| `migrate` | DB migrasyonlarını uygular | Her dağıtımdan sonra |
| `load_frameworks` | Normatif çerçeve JSON'larını içe aktarır | İlk kurulum + çerçeve güncellemesi |
| `load_notification_profiles` | Varsayılan bildirim profilleri | İlk kurulum |
| `load_competency_requirements` | M15 yeterlilik gereksinimleri | İlk kurulum |
| `load_required_documents` | Zorunlu belgeler | İlk kurulum |
| `verify_audit_trail_integrity` | Denetim izi hash zincirini doğrular | Aylık + geri yüklemeden sonra |
| `check --deploy` | Üretim yapılandırmasını doğrular | Her dağıtımdan önce |
| `createsuperuser` | İlk yönetici oluşturur | İlk kurulum |
| `seed_demo` | Demo verileri yükler | Yalnızca geliştirme ortamı |
| `makemessages -l <dil>` | Backend i18n dizilerini çıkarır | Yeni diziler eklendikten sonra |
| `compilemessages` | .po dosyalarını .mo'ya derler | Çeviri sonrasında |
| `sync_knowbe4 --full` | Manuel KnowBe4 senkronizasyonu | Hata sonrası kurtarma |

---

## Ortam değişkenleri

| Ad | Tür | Geliştirme varsayılanı | Açıklama | Zorunlu |
|----|-----|----------------------|----------|---------|
| `SECRET_KEY` | string | — | Django kriptografik anahtarı | Evet |
| `FERNET_KEY` | string | — | SMTP kimlik bilgileri için AES-256 | Evet |
| `DEBUG` | bool | True | Üretimde False | Hayır |
| `ALLOWED_HOSTS` | string | localhost | İzin verilen host'lar (virgülle ayrılmış) | Üretimde Evet |
| `DATABASE_URL` | string | postgresql://grc:grc@db:5432/grc_dev | PostgreSQL URL | Evet |
| `REDIS_URL` | string | redis://redis:6379/0 | Redis URL | Evet |
| `FRONTEND_URL` | string | http://localhost:3001 | Frontend URL | Evet |
| `CORS_ALLOWED_ORIGINS` | string | http://localhost:3001 | CORS origin'leri | Hayır |
| `AI_ENGINE_ENABLED` | bool | False | M20 AI Engine'i etkinleştirir | Hayır |
| `KNOWBE4_API_KEY` | string | — | KnowBe4 API anahtarı | Yalnızca M15 aktifse |

---

## Geliştirme kuralları

### Git

- Branch: `feature/M{nn}-açıklama`, `fix/M{nn}-hata-açıklaması`, `chore/açıklama`
- Commit: `feat(M09): NIS2 zamanlayıcısını görünür geri sayımla ekle`
- Bir branch = bir modül veya tutarlı bir özellik
- `main` veya `develop`'a doğrudan commit yok

### Python / Django

- Formatlayıcı: `ruff format` (siyah uyumlu)
- Linter: `ruff check`
- Tüm service'lerde ve harici istemcilerde tür ipuçları
- Sınıflarda ve genel metotlarda zorunlu docstring
- View'larda iş mantığı yok — her şey `services.py` içinde
- N+1 sorgu yok — `select_related` ve `prefetch_related` kullan

### React / TypeScript

- Tüm bileşenlerde TypeScript
- Açık `any` yok
- Sunum bileşenleri konteyner bileşenlerinden ayrı
- API çağrıları özel hook'larda (`useIncident`, `useControls`)
- Formatlayıcı: Prettier
- Linter: ESLint

### Güvenlik

- Kaynak kodda kimlik bilgisi yok
- Günlüklerde hassas veri yok (hash veya maskeleme kullan)
- Tüm mutasyonlarda CSRF token'ı
- Genel endpoint'lerde ve M20 AI'da hız sınırlaması
- Serializer'da girdi doğrulaması — istemciye asla güvenme

---

## Sorun giderme

### Celery Beat zamanlanan görevleri çalıştırmıyor

```bash
# Beat'in çalışıp çalışmadığını doğrula
docker compose ps celery-beat
# Çalışmıyorsa: docker compose restart celery-beat

# Planlanan görevlerin durumunu doğrula
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(PeriodicTask.objects.filter(enabled=True).values('name','last_run_at'))"
```

### Denetim izi bütünlük kontrolü başarısız oluyor

Başarısızlık, bir kaydın değiştirildiğini veya zincirin kesildiğini gösterir. Onarmaya çalışmayın — güvenlik ekibiyle iletişime geçin. Sistem otomatik olarak P1 uyarısı oluşturur.

```bash
# İlk bozuk kaydı bul
python manage.py verify_audit_trail_integrity --verbose
```

### Çerçeve içe aktarma başarısız oluyor

```bash
python manage.py load_frameworks --file frameworks/yeni.json --dry-run
# Uygulamadan farklılıkları gösterir

python manage.py load_frameworks --file frameworks/yeni.json --validate-only
# İçe aktarmadan JSON'ı doğrular
```

### KnowBe4 senkronizasyonu başarısız oluyor

```bash
# Kimlik bilgilerini doğrula
python manage.py shell -c "from apps.training.kb4_client import KnowBe4Client; print(KnowBe4Client().health_check())"

# Senkronizasyonu manuel olarak yeniden çalıştır
python manage.py sync_knowbe4 --full
```

### AI bulut token'ı yetkisiz (M20)

1. `AI_ENGINE_ENABLED=true` olduğunu ve `AI_ENGINE_CONFIG` içinde belirli fonksiyonun etkinleştirildiğini doğrula
2. API anahtarının yapılandırıldığını ve süresi dolmadığını kontrol et
3. Sanitizer'ın hata üretmediğini doğrula: `grep "sanitizer" logs/app.log | tail -20`
4. Kalıcı hata durumunda, sistem mevcut ise yerel modele döner

### Üretimde migrasyon başarısız oluyor

```bash
# Uygulamadan önce migrasyon durumunu doğrula
docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations

# Ayrıntılı çıktıyla uygula
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate --verbosity=2

# Migrasyon takılırsa DB kilidini kontrol et
# PostgreSQL'e bağlanın ve pg_stat_activity'yi kontrol edin
```

### Frontend yenilenen token'ı almıyor

`refresh_token` çerezinin süresi dolmadığını ve domain'in eşleştiğini doğrulayın. Geliştirmede, `CORS_ALLOW_CREDENTIALS = True` olduğundan ve `FRONTEND_URL`'nin doğru ayarlandığından emin olun.

### Health check başarısız oluyor

```bash
# Servis durumunu doğrula
curl http://localhost:8001/api/health/
# Beklenen yanıt: {"status": "ok", "db": "ok"}

# db=error ise PostgreSQL bağlantısını doğrula
docker compose ps db
docker compose logs db --tail=20
```
