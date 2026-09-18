"""Reporting — tab Obiettivi di sicurezza (§6.2): aggregati per sito, scadenze,
confronto con il KPI agganciato, perimetro per sito."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/reporting/objectives/"
TODAY = date(2026, 6, 1)


@pytest.fixture
def plants(db):
    from apps.plants.models import Plant
    return [
        Plant.objects.create(code=c, name=f"Sito {c}", country="IT",
                             nis2_scope="non_soggetto", status="attivo")
        for c in ("OR-A", "OR-B")
    ]


@pytest.fixture
def kpi(db, plants):
    from apps.tasks.models import KPIDefinition
    return KPIDefinition.objects.create(
        kpi_code="patch_coverage", name="Copertura patch", unit="%",
        source="internal", plant=plants[0], aggregation="last_value",
        threshold_direction="above", threshold_warning=60.0, threshold_critical=50.0,
    )


def _objective(plant=None, **kw):
    """Attivo, manuale, 40 → 90 fra TODAY-50 e TODAY+50 (metà periodo)."""
    from apps.governance.models import SecurityObjective
    data = dict(
        code="OBJ-1", title="Obiettivo", measure_source="manual", unit="%",
        start_date=TODAY - timedelta(days=50), baseline_value=40.0, target_value=90.0,
        target_direction="above", target_date=TODAY + timedelta(days=50),
        owner_role="plant_manager", evaluation_method="x", status="attivo",
    )
    data.update(kw)
    return SecurityObjective.objects.create(plant=plant, **data)


def _measure(obj, value):
    from apps.governance.models import SecurityObjectiveMeasurement
    SecurityObjectiveMeasurement.objects.create(objective=obj, measured_on=TODAY, value=value)


@pytest.mark.django_db
def test_counts_by_plant_and_track(plants):
    from apps.reporting.services import objectives_report

    _measure(_objective(plants[0], code="A-1"), 66.0)          # 52% su 50% di tempo → in linea
    _measure(_objective(plants[0], code="A-2"), 45.0)          # 10% su 50% → a rischio
    _objective(plants[0], code="A-3")                          # nessuna misura
    _objective(plants[0], code="A-4", status="bozza")
    _objective(plants[1], code="B-1", status="raggiunto", closed_at=timezone.now())
    _measure(_objective(None, code="ORG-1", target_date=TODAY - timedelta(days=1)), 50.0)  # scaduto

    data = objectives_report(None, today=TODAY)

    assert data["totals"] == {
        "attivi": 4, "in_linea": 1, "a_rischio": 1, "mancato": 1, "senza_misure": 1,
        "in_preparazione": 1, "raggiunti": 1, "non_raggiunti": 0,
    }
    # Organizzazione in testa, poi i siti.
    assert [r["plant_code"] for r in data["by_plant"]] == [None, "OR-A", "OR-B"]
    a = data["by_plant"][1]
    assert (a["attivi"], a["in_linea"], a["a_rischio"], a["senza_misure"], a["in_preparazione"]) == (3, 1, 1, 1, 1)
    assert data["by_plant"][2]["raggiunti"] == 1


@pytest.mark.django_db
def test_old_closed_and_cancelled_excluded(plants):
    from apps.reporting.services import objectives_report

    _objective(plants[0], code="OLD", status="non_raggiunto",
               closed_at=timezone.now() - timedelta(days=400))
    _objective(plants[0], code="CANC", status="annullato", closed_at=timezone.now())

    data = objectives_report(None, today=TODAY)
    assert data["by_plant"] == []
    assert data["totals"]["non_raggiunti"] == 0


@pytest.mark.django_db
def test_deadlines_within_horizon_sorted(plants):
    from apps.reporting.services import objectives_report

    _objective(plants[0], code="FAR", target_date=TODAY + timedelta(days=200))
    _objective(plants[0], code="NEAR", target_date=TODAY + timedelta(days=10))
    _objective(plants[0], code="LATE", target_date=TODAY - timedelta(days=3))
    _objective(plants[0], code="DRAFT", status="bozza", target_date=TODAY + timedelta(days=5))

    codes = [d["code"] for d in objectives_report(None, today=TODAY)["deadlines"]]
    assert codes == ["LATE", "NEAR"]


@pytest.mark.django_db
def test_kpi_linked_shows_threshold_status_next_to_track(plants, kpi):
    """Stesso valore, due letture: sopra la soglia (ok) ma in ritardo sul target."""
    from apps.reporting.services import objectives_report
    from apps.tasks.models import OperationalKpiSnapshot

    # 90% del tempo consumato, 44% del cammino percorso.
    _objective(plants[0], code="K-1", measure_source="kpi", kpi_definition=kpi, unit="",
               start_date=TODAY - timedelta(days=90), target_date=TODAY + timedelta(days=10))
    OperationalKpiSnapshot.objects.create(
        kpi_definition=kpi, plant=plants[0], week_start=TODAY - timedelta(days=7),
        value=62.0, status="ok",
    )
    _objective(plants[0], code="M-1")  # manuale: non compare nel confronto

    rows = objectives_report(None, today=TODAY)["kpi_linked"]
    assert len(rows) == 1
    r = rows[0]
    assert (r["kpi_code"], r["current_value"], r["kpi_status"], r["track"]) == (
        "patch_coverage", 62.0, "ok", "a_rischio",
    )
    assert r["threshold_warning"] == 60.0


@pytest.mark.django_db
def test_plant_filter_includes_org_objectives(plants):
    from apps.reporting.services import objectives_report

    _objective(plants[0], code="A-1")
    _objective(plants[1], code="B-1")
    _objective(None, code="ORG-1")

    data = objectives_report(str(plants[0].id), today=TODAY)
    assert [r["plant_code"] for r in data["by_plant"]] == [None, "OR-A"]
    assert data["totals"]["attivi"] == 2


@pytest.mark.django_db
def test_api_scoping(plants):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    _objective(plants[0], code="A-1")
    u = User.objects.create_user(username="or_pm", email="orpm@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=u, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.add(plants[0])
    c = APIClient()
    c.force_authenticate(user=u)

    assert c.get(URL, {"plant": str(plants[0].id)}).status_code == 200
    assert c.get(URL, {"plant": str(plants[1].id)}).status_code == 403
    # Vista aggregata su tutti i siti: solo scope org.
    assert c.get(URL).status_code == 403


@pytest.mark.django_db
def test_api_denied_to_operational_role(plants):
    from apps.auth_grc.models import GrcRole, UserPlantAccess

    u = User.objects.create_user(username="or_co", email="orco@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.CONTROL_OWNER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    assert c.get(URL).status_code == 403
