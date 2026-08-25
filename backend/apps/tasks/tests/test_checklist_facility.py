"""
Checklist legate agli impianti: espansione per categoria, misura per apparato,
registrazione della manutenzione, e KPI agganciato alla voce invece che al testo.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="fac@test.com", email="fac@test.com", password="x")
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
        code="FAC-P", name="Plant Facility", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def ups_pair(db, plant):
    from apps.assets.models import AssetFacility
    return [
        AssetFacility.objects.create(
            plant=plant, name=f"UPS {n}", asset_type="FAC", category="ups",
            maintenance_frequency_months=3, rated_autonomy_minutes=30,
        )
        for n in ("sala server", "quadro produzione")
    ]


@pytest.fixture
def ups_template(db, plant, user):
    """Prova UPS trimestrale con una voce numerica: l'autonomia misurata."""
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem
    tpl = ChecklistTemplate.objects.create(
        name="Prova autonomia UPS", frequency="quarterly", start_month=1,
        day_of_month=1, plant=plant, facility_category="ups",
        records_maintenance=True, created_by=user,
    )
    ChecklistTemplateItem.objects.create(
        template=tpl, order=0, text="Autonomia misurata", item_type="numeric",
        unit="min", is_mandatory=True,
    )
    return tpl


# ── Espansione sugli impianti ────────────────────────────────────────────────

@pytest.mark.django_db
def test_one_run_per_facility(ups_pair, ups_template, plant):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.tasks import generate_scheduled_checklists

    generate_scheduled_checklists()
    runs = ChecklistRun.objects.filter(template=ups_template)
    assert runs.count() == 2
    assert sorted(r.asset.name for r in runs) == ["UPS quadro produzione", "UPS sala server"]


@pytest.mark.django_db
def test_expansion_is_idempotent(ups_pair, ups_template):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.tasks import generate_scheduled_checklists

    generate_scheduled_checklists()
    generate_scheduled_checklists()
    assert ChecklistRun.objects.filter(template=ups_template).count() == 2


@pytest.mark.django_db
def test_a_new_facility_gets_its_run_on_the_next_pass(ups_pair, ups_template, plant):
    from apps.assets.models import AssetFacility
    from apps.tasks.models import ChecklistRun
    from apps.tasks.tasks import generate_scheduled_checklists

    generate_scheduled_checklists()
    AssetFacility.objects.create(
        plant=plant, name="UPS uffici", asset_type="FAC", category="ups",
    )
    generate_scheduled_checklists()
    assert ChecklistRun.objects.filter(template=ups_template).count() == 3


@pytest.mark.django_db
def test_no_facilities_means_no_runs(ups_template, plant):
    """Una prova UPS in un sito senza UPS non deve generare una checklist
    vuota: non è una verifica, è rumore."""
    from apps.tasks.models import ChecklistRun
    from apps.tasks.tasks import generate_scheduled_checklists

    generate_scheduled_checklists()
    assert not ChecklistRun.objects.filter(template=ups_template).exists()


@pytest.mark.django_db
def test_template_without_category_still_generates_one_run_per_plant(plant, user):
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Ronda giornaliera", frequency="daily", plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Giro fatto")
    generate_scheduled_checklists()
    run = ChecklistRun.objects.get(template=tpl)
    assert run.asset is None


# ── Manutenzione registrata dalla checklist ──────────────────────────────────

@pytest.mark.django_db
def test_completing_the_run_records_the_maintenance(ups_pair, ups_template, user):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import complete_run, complete_run_item
    from apps.tasks.tasks import generate_scheduled_checklists

    generate_scheduled_checklists()
    run = ChecklistRun.objects.filter(template=ups_template).first()
    for item in run.items.all():
        complete_run_item(run, item_id=item.id, checked=True, user=user, value=28)
    complete_run(run, user)

    run.asset.refresh_from_db()
    assert run.asset.last_maintenance_date == run.due_date
    assert run.asset.last_maintenance_result == "superata"
    # La prossima scadenza è ripartita dalla data della verifica.
    assert run.asset.next_maintenance_date > run.due_date


@pytest.mark.django_db
def test_maintenance_recording_is_opt_in(ups_pair, ups_template, user):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import complete_run, complete_run_item
    from apps.tasks.tasks import generate_scheduled_checklists

    ups_template.records_maintenance = False
    ups_template.save()

    generate_scheduled_checklists()
    run = ChecklistRun.objects.filter(template=ups_template).first()
    for item in run.items.all():
        complete_run_item(run, item_id=item.id, checked=True, user=user, value=28)
    complete_run(run, user)

    run.asset.refresh_from_db()
    assert run.asset.last_maintenance_date is None


# ── KPI agganciato alla voce ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_kpi_follows_the_item_even_after_a_rename(ups_pair, ups_template, plant, user):
    """Il difetto storico: il KPI filtrava per testo, e rinominare la voce lo
    faceva smettere di misurare senza alcun segnale."""
    from apps.tasks.models import ChecklistRun, KPIDefinition
    from apps.tasks.services import (
        _monday_of, calculate_kpi_value, complete_run, complete_run_item,
    )
    from apps.tasks.tasks import generate_scheduled_checklists

    item = ups_template.items.first()
    kpi = KPIDefinition.objects.create(
        kpi_code="ups_autonomy_minutes", name="Autonomia UPS", unit="min",
        source="checklist", checklist_template=ups_template, checklist_item=item,
        aggregation="avg_value", plant=plant,
        threshold_warning=20.0, threshold_critical=10.0, threshold_direction="above",
    )

    generate_scheduled_checklists()
    for n, run in enumerate(ChecklistRun.objects.filter(template=ups_template)):
        for run_item in run.items.all():
            complete_run_item(run, item_id=run_item.id, checked=True, user=user, value=20 + n * 10)
        complete_run(run, user)

    # La voce viene rinominata: il vecchio filtro testuale non la troverebbe più.
    item.text = "Autonomia rilevata in prova"
    item.save()

    week = _monday_of(ChecklistRun.objects.filter(template=ups_template).first().due_date)
    res = calculate_kpi_value(kpi, plant, week)
    assert res["value"] == 25.0


@pytest.mark.django_db
def test_kpi_item_must_belong_to_its_template(ups_template, plant, user):
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.serializers import KPIDefinitionSerializer

    other = ChecklistTemplate.objects.create(name="Altro", frequency="daily", plant=plant)
    foreign_item = ChecklistTemplateItem.objects.create(template=other, order=0, text="X")

    s = KPIDefinitionSerializer(data={
        "kpi_code": "test_kpi", "name": "Test", "unit": "min", "source": "checklist",
        "checklist_template": str(ups_template.id), "checklist_item": str(foreign_item.id),
        "aggregation": "avg_value", "plant": str(plant.id),
        "threshold_warning": 1, "threshold_critical": 0, "threshold_direction": "above",
    })
    assert not s.is_valid()
    assert "checklist_item" in s.errors


# ── Inserimento manuale del valore ───────────────────────────────────────────

@pytest.mark.django_db
def test_manual_value_for_a_kpi_without_integration(client, plant):
    from apps.tasks.models import KPIDefinition

    kpi = KPIDefinition.objects.create(
        kpi_code="vuln_critical_open_count", name="Vulnerabilità critiche aperte",
        unit="n°", source="api", aggregation="last_value", plant=plant,
        threshold_warning=1.0, threshold_critical=5.0, threshold_direction="below",
    )
    resp = client.post(f"/api/v1/tasks/kpi-definitions/{kpi.id}/record-value/",
                       {"value": 7, "note": "Letto dalla console dello scanner"},
                       format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["value"] == 7.0
    assert resp.data["status"] == "critical"
    assert resp.data["source"] == "manual"


@pytest.mark.django_db
def test_manual_value_is_refused_on_self_computing_kpis(client, plant):
    from apps.tasks.models import KPIDefinition

    kpi = KPIDefinition.objects.create(
        kpi_code="controls_compliance_rate", name="Conformità controlli", unit="%",
        source="internal", aggregation="last_value", plant=plant,
        threshold_warning=85.0, threshold_critical=70.0, threshold_direction="above",
    )
    resp = client.post(f"/api/v1/tasks/kpi-definitions/{kpi.id}/record-value/",
                       {"value": 90}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_manual_value_writes_audit_log(client, plant):
    from apps.tasks.models import KPIDefinition
    from core.audit import AuditLog

    kpi = KPIDefinition.objects.create(
        kpi_code="phishing_click_rate", name="Click rate phishing", unit="%",
        source="api", aggregation="avg_value", plant=plant,
        threshold_warning=5.0, threshold_critical=15.0, threshold_direction="below",
    )
    client.post(f"/api/v1/tasks/kpi-definitions/{kpi.id}/record-value/",
                {"value": 3.2}, format="json")
    assert AuditLog.objects.filter(action_code="kpi_snapshot.recorded_manually").exists()


@pytest.mark.django_db
def test_manual_value_rejects_non_numeric(client, plant):
    from apps.tasks.models import KPIDefinition

    kpi = KPIDefinition.objects.create(
        kpi_code="vapt_age_days", name="Anzianità VAPT", unit="giorni",
        source="api", aggregation="last_value", plant=plant,
        threshold_warning=180.0, threshold_critical=365.0, threshold_direction="below",
    )
    resp = client.post(f"/api/v1/tasks/kpi-definitions/{kpi.id}/record-value/",
                       {"value": "molte"}, format="json")
    assert resp.status_code == 400
