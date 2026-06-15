"""Test Quick Checklist (M08): modelli, servizi, API e soglia PDCA."""
import datetime

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

TEMPLATES_URL = "/api/v1/tasks/checklist-templates/"
RUNS_URL = "/api/v1/tasks/checklist-runs/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="chk_user", email="chk@test.com", password="test")
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
        code="CHK-P", name="Plant Checklist", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def template(db, plant, user):
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem
    tpl = ChecklistTemplate.objects.create(
        name="Controllo giornaliero shopfloor",
        frequency="daily",
        plant=plant,
        created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Item A", is_mandatory=True)
    ChecklistTemplateItem.objects.create(template=tpl, order=1, text="Item B", is_mandatory=True)
    ChecklistTemplateItem.objects.create(template=tpl, order=2, text="Item C opzionale", is_mandatory=False)
    return tpl


# ── Modelli / servizi ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_run_for_template_builds_items(template, plant):
    from apps.tasks.services import create_run_for_template
    today = timezone.localdate()
    run = create_run_for_template(template, plant, today)
    assert run.status == "pending"
    assert run.items.count() == 3


@pytest.mark.django_db
def test_create_run_for_template_is_idempotent(template, plant):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import create_run_for_template
    today = timezone.localdate()
    create_run_for_template(template, plant, today)
    create_run_for_template(template, plant, today)
    assert ChecklistRun.objects.filter(template=template, plant=plant, due_date=today).count() == 1


@pytest.mark.django_db
def test_complete_run_item_sets_checked_and_progresses(template, plant, user):
    from apps.tasks.services import complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    first = run.items.first()
    complete_run_item(run, item_id=first.id, checked=True, note="ok", user=user)
    first.refresh_from_db()
    run.refresh_from_db()
    assert first.checked is True
    assert first.checked_by == user
    assert run.status == "in_progress"


@pytest.mark.django_db
def test_complete_run_requires_all_mandatory(template, plant, user):
    from django.core.exceptions import ValidationError
    from apps.tasks.services import complete_run, create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    with pytest.raises(ValidationError):
        complete_run(run, user)


@pytest.mark.django_db
def test_complete_run_succeeds_when_mandatory_checked(template, plant, user):
    from apps.tasks.services import complete_run, complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    complete_run(run, user)
    run.refresh_from_db()
    assert run.status == "completed"
    assert run.completed_by == user
    assert run.completed_at is not None


@pytest.mark.django_db
def test_complete_run_atomic_rollback_on_audit_failure(template, plant, user):
    """P1-2: se l'audit fallisce, lo stato del run NON deve restare 'completed'."""
    from unittest.mock import patch
    from apps.tasks.services import complete_run, complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    with patch("apps.tasks.services.log_action", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            complete_run(run, user)
    run.refresh_from_db()
    assert run.status != "completed"  # rollback: nessuno stato parziale persistito


@pytest.mark.django_db
def test_complete_run_writes_audit_log(template, plant, user):
    from core.audit import AuditLog
    from apps.tasks.services import complete_run, complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    complete_run(run, user)
    assert AuditLog.objects.filter(action_code="checklist_run.completed", entity_id=run.id).exists()


# ── Soglia PDCA ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_pdca_threshold_opens_cycle_after_three_incomplete(template, plant, user):
    from apps.pdca.models import PdcaCycle
    from apps.tasks.services import create_run_for_template, evaluate_checklist_pdca_threshold

    today = timezone.localdate()
    for i in range(3):
        run = create_run_for_template(template, plant, today - datetime.timedelta(days=i + 1))
        run.status = "overdue"  # concluso ma con obbligatori non spuntati
        run.save(update_fields=["status"])

    cycle = evaluate_checklist_pdca_threshold(template)
    assert cycle is not None
    assert PdcaCycle.objects.filter(
        trigger_type="checklist_incompleta", trigger_source_id=template.id
    ).count() == 1


@pytest.mark.django_db
def test_pdca_threshold_not_triggered_with_fewer_runs(template, plant):
    from apps.tasks.services import create_run_for_template, evaluate_checklist_pdca_threshold
    today = timezone.localdate()
    for i in range(2):
        run = create_run_for_template(template, plant, today - datetime.timedelta(days=i + 1))
        run.status = "overdue"
        run.save(update_fields=["status"])
    assert evaluate_checklist_pdca_threshold(template) is None


@pytest.mark.django_db
def test_pdca_threshold_idempotent(template, plant):
    from apps.pdca.models import PdcaCycle
    from apps.tasks.services import create_run_for_template, evaluate_checklist_pdca_threshold
    today = timezone.localdate()
    for i in range(3):
        run = create_run_for_template(template, plant, today - datetime.timedelta(days=i + 1))
        run.status = "overdue"
        run.save(update_fields=["status"])
    evaluate_checklist_pdca_threshold(template)
    evaluate_checklist_pdca_threshold(template)
    assert PdcaCycle.objects.filter(
        trigger_type="checklist_incompleta", trigger_source_id=template.id
    ).count() == 1


# ── API ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_template_with_items_via_api(client, plant):
    payload = {
        "name": "Apertura turno",
        "frequency": "daily",
        "plant": str(plant.id),
        "items": [
            {"order": 0, "text": "Verifica DPI", "is_mandatory": True},
            {"order": 1, "text": "Controllo accessi", "is_mandatory": False},
        ],
    }
    resp = client.post(TEMPLATES_URL, payload, format="json")
    assert resp.status_code == 201, resp.data
    assert len(resp.data["items"]) == 2


@pytest.mark.django_db
def test_update_template_syncs_items(client, template):
    resp = client.patch(
        f"{TEMPLATES_URL}{template.id}/",
        {"items": [{"order": 0, "text": "Nuovo unico item", "is_mandatory": True}]},
        format="json",
    )
    assert resp.status_code == 200
    assert len(resp.data["items"]) == 1


@pytest.mark.django_db
def test_list_templates_filter_by_active(client, template):
    resp = client.get(TEMPLATES_URL, {"is_active": "true"})
    assert resp.status_code == 200


@pytest.mark.django_db
def test_run_complete_item_action(client, template, plant, user):
    from apps.tasks.services import create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    item = run.items.first()
    resp = client.post(
        f"{RUNS_URL}{run.id}/complete-item/",
        {"item_id": str(item.id), "checked": True, "note": "fatto"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["progress_done"] == 1


@pytest.mark.django_db
def test_run_complete_action_blocked_when_mandatory_open(client, template, plant):
    from apps.tasks.services import create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    resp = client.post(f"{RUNS_URL}{run.id}/complete/", {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_run_complete_action_ok(client, template, plant, user):
    from apps.tasks.services import complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    resp = client.post(f"{RUNS_URL}{run.id}/complete/", {}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "completed"


# ── days_of_week: generazione solo nei giorni indicati ───────────────────────

@pytest.mark.django_db
def test_generate_respects_days_of_week(plant, user):
    """Un template giornaliero con days_of_week=[0..4] (Lun–Ven) non genera run
    nel weekend (così i KPI su checklist non restano "rossi" per i run di
    sab/dom destinati a scadere); un template senza giorni genera tutti i 7."""
    from unittest.mock import patch
    from apps.tasks.models import (
        ChecklistRun, ChecklistTemplate, ChecklistTemplateItem,
    )
    from apps.tasks.tasks import generate_scheduled_checklists

    weekdays_tpl = ChecklistTemplate.objects.create(
        name="Backup feriale", frequency="daily",
        days_of_week=[0, 1, 2, 3, 4], plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=weekdays_tpl, order=0, text="Backup OK")
    everyday_tpl = ChecklistTemplate.objects.create(
        name="Ronda 7/7", frequency="daily",
        days_of_week=[], plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=everyday_tpl, order=0, text="Ronda OK")

    # Date derivate da un lunedì reale → robuste a qualsiasi giorno di esecuzione.
    base = datetime.date(2026, 6, 15)
    monday = base - datetime.timedelta(days=base.weekday())
    wednesday = monday + datetime.timedelta(days=2)
    saturday = monday + datetime.timedelta(days=5)

    # Sabato: il template feriale NON genera, quello 7/7 sì.
    with patch("apps.tasks.tasks.timezone.localdate", return_value=saturday):
        generate_scheduled_checklists()
    assert not ChecklistRun.objects.filter(
        template=weekdays_tpl, due_date=saturday
    ).exists()
    assert ChecklistRun.objects.filter(
        template=everyday_tpl, due_date=saturday
    ).exists()

    # Mercoledì: entrambi generano.
    with patch("apps.tasks.tasks.timezone.localdate", return_value=wednesday):
        generate_scheduled_checklists()
    assert ChecklistRun.objects.filter(
        template=weekdays_tpl, due_date=wednesday
    ).exists()
    assert ChecklistRun.objects.filter(
        template=everyday_tpl, due_date=wednesday
    ).exists()


@pytest.mark.django_db
def test_template_serializer_rejects_invalid_days(plant):
    from apps.tasks.serializers import ChecklistTemplateSerializer
    s = ChecklistTemplateSerializer(data={
        "name": "X", "frequency": "daily", "plant": str(plant.id),
        "days_of_week": [0, 7],  # 7 fuori range (0-6)
        "items": [{"order": 0, "text": "a", "is_mandatory": True}],
    })
    assert not s.is_valid()
    assert "days_of_week" in s.errors


@pytest.mark.django_db
def test_template_serializer_dedups_and_sorts_days(plant):
    from apps.tasks.serializers import ChecklistTemplateSerializer
    s = ChecklistTemplateSerializer(data={
        "name": "X", "frequency": "daily", "plant": str(plant.id),
        "days_of_week": [4, 0, 0, 2],
        "items": [{"order": 0, "text": "a", "is_mandatory": True}],
    })
    assert s.is_valid(), s.errors
    assert s.validated_data["days_of_week"] == [0, 2, 4]
