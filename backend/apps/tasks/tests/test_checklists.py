"""Test Quick Checklist (M08): modelli, servizi, API e soglia PDCA."""
import datetime

import pytest
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
    today = datetime.date.today()
    run = create_run_for_template(template, plant, today)
    assert run.status == "pending"
    assert run.items.count() == 3


@pytest.mark.django_db
def test_create_run_for_template_is_idempotent(template, plant):
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import create_run_for_template
    today = datetime.date.today()
    create_run_for_template(template, plant, today)
    create_run_for_template(template, plant, today)
    assert ChecklistRun.objects.filter(template=template, plant=plant, due_date=today).count() == 1


@pytest.mark.django_db
def test_complete_run_item_sets_checked_and_progresses(template, plant, user):
    from apps.tasks.services import complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, datetime.date.today())
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
    run = create_run_for_template(template, plant, datetime.date.today())
    with pytest.raises(ValidationError):
        complete_run(run, user)


@pytest.mark.django_db
def test_complete_run_succeeds_when_mandatory_checked(template, plant, user):
    from apps.tasks.services import complete_run, complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, datetime.date.today())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    complete_run(run, user)
    run.refresh_from_db()
    assert run.status == "completed"
    assert run.completed_by == user
    assert run.completed_at is not None


@pytest.mark.django_db
def test_complete_run_writes_audit_log(template, plant, user):
    from core.audit import AuditLog
    from apps.tasks.services import complete_run, complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, datetime.date.today())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    complete_run(run, user)
    assert AuditLog.objects.filter(action_code="checklist_run.completed", entity_id=run.id).exists()


# ── Soglia PDCA ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_pdca_threshold_opens_cycle_after_three_incomplete(template, plant, user):
    from apps.pdca.models import PdcaCycle
    from apps.tasks.models import ChecklistRun
    from apps.tasks.services import create_run_for_template, evaluate_checklist_pdca_threshold

    today = datetime.date.today()
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
    today = datetime.date.today()
    for i in range(2):
        run = create_run_for_template(template, plant, today - datetime.timedelta(days=i + 1))
        run.status = "overdue"
        run.save(update_fields=["status"])
    assert evaluate_checklist_pdca_threshold(template) is None


@pytest.mark.django_db
def test_pdca_threshold_idempotent(template, plant):
    from apps.pdca.models import PdcaCycle
    from apps.tasks.services import create_run_for_template, evaluate_checklist_pdca_threshold
    today = datetime.date.today()
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
    run = create_run_for_template(template, plant, datetime.date.today())
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
    run = create_run_for_template(template, plant, datetime.date.today())
    resp = client.post(f"{RUNS_URL}{run.id}/complete/", {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_run_complete_action_ok(client, template, plant, user):
    from apps.tasks.services import complete_run_item, create_run_for_template
    run = create_run_for_template(template, plant, datetime.date.today())
    for item in run.items.filter(template_item__is_mandatory=True):
        complete_run_item(run, item_id=item.id, checked=True, user=user)
    resp = client.post(f"{RUNS_URL}{run.id}/complete/", {}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "completed"
