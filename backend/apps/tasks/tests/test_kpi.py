"""Test KPI engine operativo (M08 ↔ M18): modelli, servizi, soglie, ingest."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

KPI_DEF_URL = "/api/v1/tasks/kpi-definitions/"
INGEST_URL = "/api/v1/kpi-ingest/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(
        username="kpi_user", email="kpi@test.com", password="test", is_staff=True
    )
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
        code="KPI-P", name="Plant KPI", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def plant_manager(db, plant):
    """Destinatario degli alert KPI (Plant Manager con accesso al plant)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="pm_kpi", email="pm@test.com", password="test")
    access = UserPlantAccess.objects.create(
        user=u, role=GrcRole.PLANT_MANAGER, scope_type="single_plant"
    )
    access.scope_plants.add(plant)
    return u


@pytest.fixture
def checklist_template(db, plant, user):
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem
    tpl = ChecklistTemplate.objects.create(
        name="Backup giornaliero", frequency="daily", plant=plant, created_by=user
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Backup OK", is_mandatory=True)
    return tpl


@pytest.fixture
def kpi_def(db, plant, checklist_template):
    from apps.tasks.models import KPIDefinition
    return KPIDefinition.objects.create(
        kpi_code="backup_success_rate",
        name="Tasso successo backup",
        unit="%",
        source="checklist",
        checklist_template=checklist_template,
        aggregation="success_rate",
        plant=plant,
        threshold_warning=90.0,
        threshold_critical=75.0,
        threshold_direction="above",
    )


def _monday(offset_weeks=0):
    from apps.tasks.services import _monday_of
    return _monday_of(datetime.date.today()) - datetime.timedelta(weeks=offset_weeks)


# ── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_kpi_definition_crud(client, plant):
    # create
    resp = client.post(KPI_DEF_URL, {
        "kpi_code": "vuln_critical_open",
        "name": "Vulnerabilità critiche aperte",
        "unit": "n°",
        "source": "api",
        "aggregation": "last_value",
        "plant": str(plant.id),
        "threshold_warning": 3,
        "threshold_critical": 5,
        "threshold_direction": "below",
    }, format="json")
    assert resp.status_code == 201, resp.data
    kpi_id = resp.data["id"]

    # list (reduced serializer)
    resp = client.get(KPI_DEF_URL)
    assert resp.status_code == 200
    assert any(r["kpi_code"] == "vuln_critical_open" for r in resp.data["results"])

    # update
    resp = client.patch(f"{KPI_DEF_URL}{kpi_id}/", {"threshold_warning": 2}, format="json")
    assert resp.status_code == 200
    assert resp.data["threshold_warning"] == 2

    # delete (soft)
    resp = client.delete(f"{KPI_DEF_URL}{kpi_id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_kpi_code_validation_rejects_non_slug(client, plant):
    resp = client.post(KPI_DEF_URL, {
        "kpi_code": "Backup Success",  # spazi + maiuscole → invalido
        "name": "X",
        "source": "api",
    }, format="json")
    assert resp.status_code == 400
    assert "kpi_code" in resp.data


# ── calculate_kpi_value ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_calculate_kpi_success_rate(kpi_def, plant, checklist_template):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import calculate_kpi_value

    week = _monday()
    # 3 completed + 1 overdue nello stesso giorno della settimana
    for _ in range(3):
        ChecklistRun.objects.create(
            template=checklist_template, plant=plant, due_date=week, status="completed"
        )
    ChecklistRun.objects.create(
        template=checklist_template, plant=plant, due_date=week, status="overdue"
    )
    result = calculate_kpi_value(kpi_def, plant, week)
    assert result["run_count"] == 4
    assert result["value"] == 75.0  # 3/4 * 100


@pytest.mark.django_db
def test_calculate_kpi_no_runs_returns_none(kpi_def, plant):
    from apps.tasks.services import calculate_kpi_value
    result = calculate_kpi_value(kpi_def, plant, _monday())
    assert result["value"] is None
    assert result["run_count"] == 0


# ── evaluate_kpi_status ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_evaluate_kpi_status_above_threshold(kpi_def):
    from apps.tasks.services import evaluate_kpi_status
    # direction=above: warning=90, critical=75
    assert evaluate_kpi_status(kpi_def, 95) == "ok"
    assert evaluate_kpi_status(kpi_def, 80) == "warning"
    assert evaluate_kpi_status(kpi_def, 50) == "critical"
    assert evaluate_kpi_status(kpi_def, None) == "no_data"


@pytest.mark.django_db
def test_evaluate_kpi_status_below_threshold(db, plant):
    from apps.tasks.models import KPIDefinition
    from apps.tasks.services import evaluate_kpi_status
    kpi = KPIDefinition.objects.create(
        kpi_code="vuln_open", name="Vuln", source="api", plant=plant,
        threshold_warning=3.0, threshold_critical=5.0, threshold_direction="below",
    )
    # direction=below: valori bassi buoni
    assert evaluate_kpi_status(kpi, 1) == "ok"
    assert evaluate_kpi_status(kpi, 4) == "warning"
    assert evaluate_kpi_status(kpi, 9) == "critical"


# ── compute_and_store_kpi_snapshot + alert ───────────────────────────────────

@pytest.mark.django_db
def test_compute_and_store_snapshot_creates_alert_on_critical(
    kpi_def, plant, checklist_template, plant_manager
):
    from django.core import mail
    from apps.tasks.models import ChecklistRun, OperationalKpiSnapshot
    from apps.tasks.services import compute_and_store_kpi_snapshot

    week = _monday()
    # tutti overdue → success_rate 0% → critical (sotto 75)
    for _ in range(2):
        ChecklistRun.objects.create(
            template=checklist_template, plant=plant, due_date=week, status="overdue"
        )

    snapshot = compute_and_store_kpi_snapshot(kpi_def, plant, week)
    assert snapshot.status == "critical"
    assert snapshot.value == 0.0
    assert getattr(snapshot, "_alert_sent", False) is True
    assert OperationalKpiSnapshot.objects.filter(
        kpi_definition=kpi_def, plant=plant, week_start=week
    ).count() == 1
    # alert email inviata al plant manager
    assert len(mail.outbox) == 1
    assert "pm@test.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_compute_snapshot_no_repeat_alert_when_status_unchanged(
    kpi_def, plant, checklist_template, plant_manager
):
    from django.core import mail
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import compute_and_store_kpi_snapshot

    # settimana scorsa già critical
    prev_week = _monday(offset_weeks=1)
    ChecklistRun.objects.create(
        template=checklist_template, plant=plant, due_date=prev_week, status="overdue"
    )
    compute_and_store_kpi_snapshot(kpi_def, plant, prev_week)
    mail.outbox.clear()

    # questa settimana ancora critical → nessun nuovo alert (non peggiorato)
    week = _monday()
    ChecklistRun.objects.create(
        template=checklist_template, plant=plant, due_date=week, status="overdue"
    )
    snapshot = compute_and_store_kpi_snapshot(kpi_def, plant, week)
    assert snapshot.status == "critical"
    assert getattr(snapshot, "_alert_sent", False) is False
    assert len(mail.outbox) == 0


# ── ingest API ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_ingest_kpi_from_api_endpoint(client, plant):
    from apps.tasks.models import KPIDefinition, OperationalKpiSnapshot
    from core.audit import AuditLog

    resp = client.post(INGEST_URL, {
        "kpi_code": "backup_success_rate",
        "plant": str(plant.id),
        "value": 98.5,
        "source": "veeam",
        "note": "Backup notturno completato",
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["kpi_code"] == "backup_success_rate"
    assert resp.data["status"] in ("ok", "warning", "critical", "no_data")

    # KPIDefinition auto-creata con source=api
    kpi = KPIDefinition.objects.get(kpi_code="backup_success_rate")
    assert kpi.source == "api"
    # snapshot creato + audit log
    assert OperationalKpiSnapshot.objects.filter(kpi_definition=kpi, plant=plant).exists()
    assert AuditLog.objects.filter(action_code="kpi.ingested").exists()


@pytest.mark.django_db
def test_ingest_rejects_invalid_kpi_code(client, plant):
    resp = client.post(INGEST_URL, {
        "kpi_code": "INVALID CODE",
        "plant": str(plant.id),
        "value": 1.0,
        "source": "x",
    }, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_ingest_requires_auth(plant, settings):
    """Senza JWT staff né X-API-Key → 401. Con X-API-Key valido → 201."""
    settings.KPI_INGEST_API_KEY = "secret-key-123"
    anon = APIClient()
    payload = {
        "kpi_code": "disk_usage", "plant": str(plant.id),
        "value": 42.0, "source": "zabbix",
    }
    # nessuna credenziale
    resp = anon.post(INGEST_URL, payload, format="json")
    assert resp.status_code == 401
    # con API key valida
    resp = anon.post(INGEST_URL, payload, format="json", HTTP_X_API_KEY="secret-key-123")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_kpi_trend_endpoint(client, kpi_def, plant):
    from apps.tasks.models import OperationalKpiSnapshot
    for i in range(3):
        OperationalKpiSnapshot.objects.create(
            kpi_definition=kpi_def, plant=plant,
            week_start=_monday(offset_weeks=i), value=80 + i, status="ok",
        )
    resp = client.get(
        f"/api/v1/tasks/kpi-snapshots/trend/?kpi_code=backup_success_rate&plant={plant.id}&weeks=12"
    )
    assert resp.status_code == 200
    assert resp.data["kpi_code"] == "backup_success_rate"
    assert len(resp.data["results"]) == 3
    # ordinati ASC per week_start
    weeks = [r["week_start"] for r in resp.data["results"]]
    assert weeks == sorted(weeks)
