"""Test 'Consiglia KPI': catalogo statico, endpoint suggest e import."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

SUGGEST_URL = "/api/v1/kpi-suggest/"
IMPORT_URL = "/api/v1/kpi-suggest/import/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="sug_user", email="sug@test.com", password="test", is_staff=True)
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="SUG-P", name="Plant Suggest", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


def _activate_framework(plant, code):
    """Attiva un framework sul plant via PlantFramework."""
    import datetime
    from apps.controls.models import Framework
    from apps.plants.models import PlantFramework
    fw, _ = Framework.objects.get_or_create(
        code=code,
        defaults={"name": code, "version": "1", "published_at": datetime.date(2024, 1, 1)},
    )
    PlantFramework.objects.get_or_create(
        plant=plant, framework=fw,
        defaults={"active": True, "active_from": datetime.date(2024, 1, 1)},
    )
    return fw


# ── Catalogo ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_catalog_complete_translations():
    from apps.tasks.kpi_catalog import KPI_CATALOG, LANGS
    assert len(KPI_CATALOG) >= 20
    for code, e in KPI_CATALOG.items():
        for field in ("name", "description", "rationale", "checklist_hint"):
            for lang in LANGS:
                assert e[field].get(lang), f"{code}.{field}.{lang} mancante"


# ── Suggest ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_suggest_without_frameworks_returns_all(client, plant):
    """Plant senza framework attivi → tutti i KPI del catalogo."""
    from apps.tasks.kpi_catalog import KPI_CATALOG
    resp = client.get(SUGGEST_URL, {"plant": str(plant.id)})
    assert resp.status_code == 200
    assert resp.data["plant_frameworks"] == []
    assert len(resp.data["suggestions"]) == len(KPI_CATALOG)


@pytest.mark.django_db
def test_suggest_filters_by_active_frameworks(client, plant):
    """Con solo NIS2 attivo, esclude i KPI che non citano NIS2."""
    _activate_framework(plant, "NIS2")
    resp = client.get(SUGGEST_URL, {"plant": str(plant.id), "lang": "en"})
    assert resp.status_code == 200
    assert "NIS2" in resp.data["plant_frameworks"]
    for s in resp.data["suggestions"]:
        assert "NIS2" in s["frameworks"]
    # incident_rca_completion_rate non ha NIS2 → escluso
    codes = {s["kpi_code"] for s in resp.data["suggestions"]}
    assert "incident_rca_completion_rate" not in codes
    assert "backup_success_rate" in codes


@pytest.mark.django_db
def test_suggest_marks_already_configured(client, plant):
    from apps.tasks.models import KPIDefinition
    KPIDefinition.objects.create(
        kpi_code="backup_success_rate", name="x", source="checklist", plant=plant
    )
    resp = client.get(SUGGEST_URL, {"plant": str(plant.id)})
    by_code = {s["kpi_code"]: s for s in resp.data["suggestions"]}
    assert by_code["backup_success_rate"]["already_configured"] is True
    assert by_code["incident_mttd_hours"]["already_configured"] is False


@pytest.mark.django_db
def test_suggest_links_checklist_template(client, plant):
    from apps.tasks.models import ChecklistTemplate
    tpl = ChecklistTemplate.objects.create(
        name="Verifica backup notturno", frequency="daily", plant=plant
    )
    resp = client.get(SUGGEST_URL, {"plant": str(plant.id)})
    by_code = {s["kpi_code"]: s for s in resp.data["suggestions"]}
    sug = by_code["backup_success_rate"]["suggested_checklist_template"]
    assert sug is not None
    assert sug["id"] == str(tpl.id)


# ── Import ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_import_creates_definitions(client, plant):
    from apps.tasks.models import KPIDefinition
    resp = client.post(IMPORT_URL, {
        "plant": str(plant.id),
        "kpi_codes": ["backup_success_rate", "incident_mttd_hours"],
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert set(resp.data["created"]) == {"backup_success_rate", "incident_mttd_hours"}
    assert resp.data["skipped"] == []
    kpi = KPIDefinition.objects.get(kpi_code="backup_success_rate")
    assert kpi.plant_id == plant.id
    assert kpi.threshold_warning == 99.0  # default catalogo
    assert kpi.aggregation == "success_rate"


@pytest.mark.django_db
def test_import_is_idempotent(client, plant):
    payload = {"plant": str(plant.id), "kpi_codes": ["backup_success_rate"]}
    r1 = client.post(IMPORT_URL, payload, format="json")
    assert r1.data["created"] == ["backup_success_rate"]
    r2 = client.post(IMPORT_URL, payload, format="json")
    assert r2.data["created"] == []
    assert r2.data["skipped"] == ["backup_success_rate"]
    from apps.tasks.models import KPIDefinition
    assert KPIDefinition.objects.filter(kpi_code="backup_success_rate").count() == 1


@pytest.mark.django_db
def test_import_restores_soft_deleted_definition(client, plant):
    """Una definizione cancellata logicamente occupa ancora il kpi_code (il
    vincolo UNIQUE del DB ignora deleted_at): il re-import deve ripristinarla,
    non tentare una INSERT che finirebbe in 'duplicate key'."""
    from apps.tasks.models import KPIDefinition
    payload = {"plant": str(plant.id), "kpi_codes": ["backup_success_rate"]}
    client.post(IMPORT_URL, payload, format="json")
    kpi = KPIDefinition.objects.get(kpi_code="backup_success_rate")
    original_pk = kpi.pk
    kpi.soft_delete()
    assert not KPIDefinition.objects.filter(kpi_code="backup_success_rate").exists()

    resp = client.post(IMPORT_URL, payload, format="json")

    assert resp.status_code == 201, resp.data
    assert resp.data["errors"] == []
    assert resp.data["created"] == []
    assert resp.data["restored"] == ["backup_success_rate"]
    revived = KPIDefinition.objects.get(kpi_code="backup_success_rate")
    assert revived.pk == original_pk  # stessa riga → snapshot storici salvi
    assert revived.deleted_at is None
    assert revived.is_active is True
    assert KPIDefinition.objects.all_with_deleted().filter(
        kpi_code="backup_success_rate"
    ).count() == 1


@pytest.mark.django_db
def test_import_restore_writes_dedicated_audit_log(client, plant):
    from apps.tasks.models import KPIDefinition
    from core.audit import AuditLog
    payload = {"plant": str(plant.id), "kpi_codes": ["backup_success_rate"]}
    client.post(IMPORT_URL, payload, format="json")
    KPIDefinition.objects.get(kpi_code="backup_success_rate").soft_delete()
    client.post(IMPORT_URL, payload, format="json")
    assert AuditLog.objects.filter(action_code="kpi_definition.restored").exists()


DEF_URL = "/api/v1/tasks/kpi-definitions/"


@pytest.fixture
def plant2(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="SUG-P2", name="Plant Suggest 2", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.mark.django_db
def test_create_definition_reuses_soft_deleted_code(client, plant):
    """Il vincolo di unicita' ignora le righe cancellate: un codice liberato
    dalla UI deve tornare disponibile."""
    from apps.tasks.models import KPIDefinition
    KPIDefinition.objects.create(
        kpi_code="backup_success_rate", name="Backup", plant=plant,
    ).soft_delete()

    resp = client.post(DEF_URL, {
        "kpi_code": "backup_success_rate",
        "name": "Backup bis",
        "plant": str(plant.id),
        "source": "manual",
        "aggregation": "success_rate",
    }, format="json")

    assert resp.status_code == 201, resp.data
    assert KPIDefinition.objects.filter(kpi_code="backup_success_rate").count() == 1


@pytest.mark.django_db
def test_same_kpi_code_on_two_plants(client, plant, plant2):
    """Ogni sito ha i propri KPI: lo stesso codice deve poter convivere su
    stabilimenti diversi, con soglie indipendenti."""
    from apps.tasks.models import KPIDefinition
    for p, warn in ((plant, 99.0), (plant2, 95.0)):
        resp = client.post(IMPORT_URL, {
            "plant": str(p.id),
            "kpi_codes": ["backup_success_rate"],
            "overrides": {"backup_success_rate": {"threshold_warning": warn}},
        }, format="json")
        assert resp.status_code == 201, resp.data
        assert resp.data["created"] == ["backup_success_rate"], resp.data

    defs = KPIDefinition.objects.filter(kpi_code="backup_success_rate")
    assert defs.count() == 2
    assert defs.get(plant=plant).threshold_warning == 99.0
    assert defs.get(plant=plant2).threshold_warning == 95.0


@pytest.mark.django_db
def test_duplicate_kpi_code_same_plant_is_400(client, plant):
    payload = {
        "kpi_code": "backup_success_rate", "name": "Backup",
        "plant": str(plant.id), "source": "manual", "aggregation": "success_rate",
    }
    assert client.post(DEF_URL, payload, format="json").status_code == 201
    resp = client.post(DEF_URL, payload, format="json")
    assert resp.status_code == 400, resp.data
    assert "kpi_code" in resp.data


@pytest.mark.django_db
def test_duplicate_global_kpi_code_is_400(client):
    payload = {
        "kpi_code": "backup_success_rate", "name": "Backup",
        "plant": None, "source": "manual", "aggregation": "success_rate",
    }
    assert client.post(DEF_URL, payload, format="json").status_code == 201
    resp = client.post(DEF_URL, payload, format="json")
    assert resp.status_code == 400, resp.data
    assert "globale" in str(resp.data["kpi_code"][0])


@pytest.mark.django_db
def test_suggest_already_configured_is_per_plant(client, plant, plant2):
    """Configurare un KPI sul sito A non deve marcarlo configurato sul B."""
    client.post(IMPORT_URL, {
        "plant": str(plant.id), "kpi_codes": ["backup_success_rate"],
    }, format="json")

    def _flag(plant_obj, key):
        data = client.get(SUGGEST_URL, {"plant": str(plant_obj.id)}).data
        item = next(
            s for s in data["suggestions"] if s["kpi_code"] == "backup_success_rate"
        )
        return item[key]

    assert _flag(plant, "already_configured") is True
    assert _flag(plant2, "already_configured") is False


@pytest.mark.django_db
def test_suggest_flags_coverage_by_global_definition(client, plant):
    """Un KPI globale non blocca il sito, ma viene segnalato come gia' coperto."""
    client.post(IMPORT_URL, {
        "plant": None, "kpi_codes": ["backup_success_rate"],
    }, format="json")
    data = client.get(SUGGEST_URL, {"plant": str(plant.id)}).data
    item = next(
        s for s in data["suggestions"] if s["kpi_code"] == "backup_success_rate"
    )
    assert item["already_configured"] is False
    assert item["covered_by_global"] is True


@pytest.mark.django_db
def test_global_kpi_skips_plants_with_own_definition(client, plant, plant2):
    """La definizione globale copre solo i siti senza una propria: altrimenti
    lo stesso KPI verrebbe misurato due volte sullo stesso sito."""
    from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot
    from apps.tasks.tasks import compute_operational_kpis

    KPIDefinition.objects.create(
        kpi_code="ctrl_compliance_rate", name="Globale", plant=None,
        source="internal", is_active=True,
    )
    own = KPIDefinition.objects.create(
        kpi_code="ctrl_compliance_rate", name="Solo sito 2", plant=plant2,
        source="internal", is_active=True,
    )

    compute_operational_kpis()

    snaps = OperationalKpiSnapshot.objects.filter(plant=plant2)
    assert snaps.count() == 1
    assert snaps.first().kpi_definition_id == own.id


@pytest.mark.django_db
def test_ingest_prefers_plant_definition_over_global(db, plant):
    """L'ingest per sito riusa la definizione del sito se c'e', altrimenti la
    globale: non deve creare una terza definizione a ogni push."""
    from apps.tasks.models import KPIDefinition
    from apps.tasks.services import ingest_kpi_from_api

    glob = KPIDefinition.objects.create(
        kpi_code="osint_critical_open", name="Globale", plant=None, source="api",
    )
    snap = ingest_kpi_from_api("osint_critical_open", str(plant.id), 3, "osint")
    assert snap.kpi_definition_id == glob.id
    assert KPIDefinition.objects.filter(kpi_code="osint_critical_open").count() == 1

    own = KPIDefinition.objects.create(
        kpi_code="osint_critical_open", name="Sito", plant=plant, source="api",
    )
    snap2 = ingest_kpi_from_api("osint_critical_open", str(plant.id), 4, "osint")
    assert snap2.kpi_definition_id == own.id


@pytest.mark.django_db
def test_import_applies_overrides(client, plant):
    from apps.tasks.models import ChecklistTemplate, KPIDefinition
    tpl = ChecklistTemplate.objects.create(name="Backup check", frequency="daily", plant=plant)
    resp = client.post(IMPORT_URL, {
        "plant": str(plant.id),
        "kpi_codes": ["backup_success_rate"],
        "overrides": {
            "backup_success_rate": {"threshold_warning": 98.0, "checklist_template": str(tpl.id)},
        },
    }, format="json")
    assert resp.status_code == 201
    kpi = KPIDefinition.objects.get(kpi_code="backup_success_rate")
    assert kpi.threshold_warning == 98.0
    assert kpi.checklist_template_id == tpl.id


@pytest.mark.django_db
def test_import_unknown_code_reports_error(client, plant):
    resp = client.post(IMPORT_URL, {
        "plant": str(plant.id), "kpi_codes": ["does_not_exist"],
    }, format="json")
    assert resp.status_code == 201
    assert resp.data["created"] == []
    assert resp.data["errors"] and resp.data["errors"][0]["kpi_code"] == "does_not_exist"


@pytest.mark.django_db
def test_import_writes_audit_log(client, plant):
    from core.audit import AuditLog
    client.post(IMPORT_URL, {
        "plant": str(plant.id), "kpi_codes": ["backup_success_rate"],
    }, format="json")
    assert AuditLog.objects.filter(action_code="kpi_definition.imported").exists()


# ── Creazione template dallo seed ────────────────────────────────────────────

@pytest.mark.django_db
def test_suggest_marks_can_create_template(client, plant):
    """Senza template corrispondente, un KPI checklist con seed → can_create_template."""
    resp = client.get(SUGGEST_URL, {"plant": str(plant.id)})
    by_code = {s["kpi_code"]: s for s in resp.data["suggestions"]}
    bs = by_code["backup_success_rate"]
    assert bs["suggested_checklist_template"] is None
    assert bs["can_create_template"] is True
    assert bs["template_seed_name"]  # nome localizzato presente
    # un KPI api non può creare template
    assert by_code["vuln_critical_open_count"]["can_create_template"] is False


@pytest.mark.django_db
def test_suggest_no_create_when_template_exists(client, plant):
    """Se esiste un template collegabile, can_create_template è False."""
    from apps.tasks.models import ChecklistTemplate
    ChecklistTemplate.objects.create(name="Backup notturno sito", frequency="daily", plant=plant)
    resp = client.get(SUGGEST_URL, {"plant": str(plant.id)})
    bs = {s["kpi_code"]: s for s in resp.data["suggestions"]}["backup_success_rate"]
    assert bs["suggested_checklist_template"] is not None
    assert bs["can_create_template"] is False


@pytest.mark.django_db
def test_import_with_create_template(client, plant):
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem, KPIDefinition
    resp = client.post(IMPORT_URL, {
        "plant": str(plant.id),
        "kpi_codes": ["backup_success_rate"],
        "overrides": {"backup_success_rate": {"create_template": True}},
    }, format="json")
    assert resp.status_code == 201
    assert resp.data["created"] == ["backup_success_rate"]
    # template creato dallo seed e collegato
    tpl = ChecklistTemplate.objects.get(name="Verifica backup notturno", plant=plant)
    assert tpl.frequency == "daily"
    assert ChecklistTemplateItem.objects.filter(template=tpl).count() == 1
    kpi = KPIDefinition.objects.get(kpi_code="backup_success_rate")
    assert kpi.checklist_template_id == tpl.id


@pytest.mark.django_db
def test_create_template_from_seed_idempotent(db, plant):
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import create_template_from_seed
    t1 = create_template_from_seed("backup_success_rate", plant)
    t2 = create_template_from_seed("backup_success_rate", plant)
    assert t1.id == t2.id
    assert ChecklistTemplate.objects.filter(name="Verifica backup notturno", plant=plant).count() == 1


@pytest.mark.django_db
def test_create_template_from_seed_numeric_item(db, plant):
    from apps.tasks.services import create_template_from_seed
    tpl = create_template_from_seed("backup_restore_test_age_days", plant)
    item = tpl.items.first()
    assert item.item_type == "numeric"
    assert item.unit == "giorni"


@pytest.mark.django_db
def test_create_template_from_seed_none_for_api_kpi(db, plant):
    from apps.tasks.services import create_template_from_seed
    assert create_template_from_seed("vuln_critical_open_count", plant) is None
