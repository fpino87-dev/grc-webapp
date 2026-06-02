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
