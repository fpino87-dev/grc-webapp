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
def test_update_template_with_existing_runs_does_not_crash(client, template, plant):
    """Regressione: il salvataggio di un template che ha già generato dei run
    falliva con 500 (ProtectedError) perché gli item venivano ricreati."""
    from apps.tasks.services import create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    items = list(template.items.all())

    resp = client.patch(
        f"{TEMPLATES_URL}{template.id}/",
        {
            "days_of_week": [0, 2, 4],
            "items": [
                {"id": str(it.id), "order": i, "text": it.text,
                 "is_mandatory": it.is_mandatory}
                for i, it in enumerate(items)
            ],
        },
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["days_of_week"] == [0, 2, 4]
    # Gli item mantengono i loro id: i run già generati restano validi.
    assert [it["id"] for it in resp.data["items"]] == [str(it.id) for it in items]
    assert run.items.count() == 3


@pytest.mark.django_db
def test_update_template_soft_deletes_removed_items(client, template, plant):
    from apps.tasks.models import ChecklistTemplateItem
    from apps.tasks.services import create_run_for_template
    run = create_run_for_template(template, plant, timezone.localdate())
    keep, drop = list(template.items.all())[:2]

    resp = client.patch(
        f"{TEMPLATES_URL}{template.id}/",
        {"items": [{"id": str(keep.id), "order": 0, "text": keep.text,
                    "is_mandatory": True}]},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert template.items.count() == 1
    # L'item rimosso è soft-deletato, non cancellato: il run storico lo mostra.
    drop.refresh_from_db()
    assert drop.deleted_at is not None
    assert ChecklistTemplateItem.objects.all_with_deleted().filter(pk=drop.pk).exists()
    assert run.items.filter(template_item=drop).exists()


@pytest.mark.django_db
def test_update_template_preserves_numeric_item_metadata(client, template):
    """Un client che invia solo testo/ordine non deve azzerare tipo e unità."""
    item = template.items.first()
    item.item_type = "numeric"
    item.unit = "%"
    item.save()

    resp = client.patch(
        f"{TEMPLATES_URL}{template.id}/",
        {"items": [{"id": str(item.id), "order": 0, "text": "Uptime backup"}]},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    item.refresh_from_db()
    assert item.text == "Uptime backup"
    assert item.item_type == "numeric"
    assert item.unit == "%"


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


# ── Settimanale / mensile: giorno configurabile, scadenza a fine periodo ─────

@pytest.mark.django_db
def test_weekly_generates_on_configured_day_with_due_date_end_of_week(plant, user):
    from unittest.mock import patch
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Offboarding", frequency="weekly", days_of_week=[2],  # mercoledì
        plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Revoca accessi")

    base = datetime.date(2026, 6, 15)
    monday = base - datetime.timedelta(days=base.weekday())
    tuesday = monday + datetime.timedelta(days=1)
    wednesday = monday + datetime.timedelta(days=2)
    sunday = monday + datetime.timedelta(days=6)

    # Martedì: il giorno di generazione non è ancora arrivato.
    with patch("apps.tasks.tasks.timezone.localdate", return_value=tuesday):
        generate_scheduled_checklists()
    assert not ChecklistRun.objects.filter(template=tpl).exists()

    # Mercoledì: generata, con scadenza a fine settimana (domenica).
    with patch("apps.tasks.tasks.timezone.localdate", return_value=wednesday):
        generate_scheduled_checklists()
    run = ChecklistRun.objects.get(template=tpl)
    assert run.due_date == sunday
    assert run.status == "pending"


@pytest.mark.django_db
def test_weekly_defaults_to_monday_and_is_not_duplicated(plant, user):
    from unittest.mock import patch
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Settimanale storica", frequency="weekly", days_of_week=[],
        plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Check")

    base = datetime.date(2026, 6, 15)
    monday = base - datetime.timedelta(days=base.weekday())
    for day_offset in range(7):
        with patch(
            "apps.tasks.tasks.timezone.localdate",
            return_value=monday + datetime.timedelta(days=day_offset),
        ):
            generate_scheduled_checklists()
    # Un solo run per la settimana, nonostante 7 esecuzioni dello scheduler.
    assert ChecklistRun.objects.filter(template=tpl).count() == 1


@pytest.mark.django_db
def test_weekly_recovers_period_when_scheduler_was_down(plant, user):
    """Il giorno di generazione è passato ma la settimana è ancora scoperta:
    il run va creato lo stesso, altrimenti un fermo di Celery (o un template
    attivato a metà settimana) lascia un buco nell'evidenza."""
    from unittest.mock import patch
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Recupero", frequency="weekly", days_of_week=[0],
        plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Check")

    base = datetime.date(2026, 6, 15)
    monday = base - datetime.timedelta(days=base.weekday())
    thursday = monday + datetime.timedelta(days=3)
    with patch("apps.tasks.tasks.timezone.localdate", return_value=thursday):
        generate_scheduled_checklists()
    run = ChecklistRun.objects.get(template=tpl)
    assert run.due_date == monday + datetime.timedelta(days=6)


@pytest.mark.django_db
def test_monthly_generates_on_configured_day_with_due_date_end_of_month(plant, user):
    from unittest.mock import patch
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Test ripristino backup", frequency="monthly", day_of_month=10,
        plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Ripristino OK")

    with patch(
        "apps.tasks.tasks.timezone.localdate", return_value=datetime.date(2026, 6, 9)
    ):
        generate_scheduled_checklists()
    assert not ChecklistRun.objects.filter(template=tpl).exists()

    with patch(
        "apps.tasks.tasks.timezone.localdate", return_value=datetime.date(2026, 6, 10)
    ):
        generate_scheduled_checklists()
    run = ChecklistRun.objects.get(template=tpl)
    assert run.due_date == datetime.date(2026, 6, 30)


@pytest.mark.django_db
def test_monthly_last_day_option_handles_short_months(plant, user):
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import checklist_due_date_for, checklist_period_bounds

    tpl = ChecklistTemplate.objects.create(
        name="Fine mese", frequency="monthly",
        day_of_month=ChecklistTemplate.LAST_DAY_OF_MONTH, plant=plant, created_by=user,
    )
    _start, end, gen = checklist_period_bounds(tpl, datetime.date(2028, 2, 5))
    assert gen == datetime.date(2028, 2, 29)  # bisestile
    assert end == datetime.date(2028, 2, 29)
    assert checklist_due_date_for(tpl, datetime.date(2028, 2, 5)) is None
    assert checklist_due_date_for(tpl, datetime.date(2028, 2, 29)) == datetime.date(2028, 2, 29)


@pytest.mark.django_db
def test_monthly_day_is_clamped_to_short_month(plant, user):
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import checklist_period_bounds

    tpl = ChecklistTemplate.objects.create(
        name="Giorno 28", frequency="monthly", day_of_month=28,
        plant=plant, created_by=user,
    )
    _start, _end, gen = checklist_period_bounds(tpl, datetime.date(2027, 2, 1))
    assert gen == datetime.date(2027, 2, 28)


@pytest.mark.django_db
def test_ad_hoc_is_never_generated_automatically(plant, user):
    from unittest.mock import patch
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Post incidente", frequency="ad_hoc", plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Verifica")
    for day in range(1, 32):
        with patch(
            "apps.tasks.tasks.timezone.localdate",
            return_value=datetime.date(2026, 7, day),
        ):
            generate_scheduled_checklists()
    assert not ChecklistRun.objects.filter(template=tpl).exists()


@pytest.mark.django_db
def test_serializer_rejects_multiple_days_for_weekly(plant):
    from apps.tasks.serializers import ChecklistTemplateSerializer
    s = ChecklistTemplateSerializer(data={
        "name": "X", "frequency": "weekly", "plant": str(plant.id),
        "days_of_week": [0, 3],
        "items": [{"order": 0, "text": "a", "is_mandatory": True}],
    })
    assert not s.is_valid()
    assert "days_of_week" in s.errors


@pytest.mark.django_db
def test_serializer_rejects_invalid_day_of_month(plant):
    from apps.tasks.serializers import ChecklistTemplateSerializer
    s = ChecklistTemplateSerializer(data={
        "name": "X", "frequency": "monthly", "plant": str(plant.id),
        "day_of_month": 31,  # oltre il massimo consentito (28 o 0=fine mese)
        "items": [{"order": 0, "text": "a", "is_mandatory": True}],
    })
    assert not s.is_valid()
    assert "day_of_month" in s.errors


# ── Avvio manuale (ad hoc e fuori ciclo) ─────────────────────────────────────

@pytest.mark.django_db
def test_start_run_action_creates_run_for_ad_hoc_template(client, plant, user):
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem

    tpl = ChecklistTemplate.objects.create(
        name="Verifica post incidente", frequency="ad_hoc", plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Log raccolti")

    resp = client.post(f"{TEMPLATES_URL}{tpl.id}/start-run/", {}, format="json")
    assert resp.status_code == 201, resp.data
    assert str(resp.data["template"]) == str(tpl.id)
    assert resp.data["due_date"] == str(timezone.localdate())
    assert len(resp.data["items"]) == 1


@pytest.mark.django_db
def test_start_run_action_accepts_due_date_and_is_idempotent(client, template, plant):
    due = timezone.localdate() + datetime.timedelta(days=5)
    first = client.post(
        f"{TEMPLATES_URL}{template.id}/start-run/", {"due_date": str(due)}, format="json"
    )
    assert first.status_code == 201, first.data
    assert first.data["due_date"] == str(due)
    second = client.post(
        f"{TEMPLATES_URL}{template.id}/start-run/", {"due_date": str(due)}, format="json"
    )
    assert second.data["id"] == first.data["id"]


@pytest.mark.django_db
def test_start_run_action_requires_plant_for_global_template(client, user):
    from apps.tasks.models import ChecklistTemplate, ChecklistTemplateItem

    tpl = ChecklistTemplate.objects.create(
        name="Globale", frequency="ad_hoc", plant=None, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Check")
    resp = client.post(f"{TEMPLATES_URL}{tpl.id}/start-run/", {}, format="json")
    assert resp.status_code == 400
    assert "plant" in resp.data


@pytest.mark.django_db
def test_start_run_action_writes_audit_log(client, template):
    from core.audit import AuditLog

    resp = client.post(f"{TEMPLATES_URL}{template.id}/start-run/", {}, format="json")
    assert resp.status_code == 201, resp.data
    assert AuditLog.objects.filter(
        action_code="checklist_run.started_manually"
    ).exists()


# ── Frequenze lunghe: trimestrale, semestrale, annuale ───────────────────────

@pytest.mark.django_db
def test_quarterly_period_is_anchored_to_start_month(plant, user):
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import checklist_due_date_for, checklist_period_bounds

    # Ancorato a febbraio → periodi feb-apr, mag-lug, ago-ott, nov-gen.
    tpl = ChecklistTemplate.objects.create(
        name="Trimestrale", frequency="quarterly", start_month=2, day_of_month=1,
        plant=plant, created_by=user,
    )
    start, end, gen = checklist_period_bounds(tpl, datetime.date(2026, 6, 10))
    assert (start, end, gen) == (
        datetime.date(2026, 5, 1), datetime.date(2026, 7, 31), datetime.date(2026, 5, 1)
    )
    assert checklist_due_date_for(tpl, datetime.date(2026, 6, 10)) == datetime.date(2026, 7, 31)


@pytest.mark.django_db
def test_quarterly_period_wraps_across_the_year(plant, user):
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import checklist_period_bounds

    tpl = ChecklistTemplate.objects.create(
        name="A cavallo d'anno", frequency="quarterly", start_month=11,
        plant=plant, created_by=user,
    )
    start, end, _gen = checklist_period_bounds(tpl, datetime.date(2027, 1, 15))
    assert start == datetime.date(2026, 11, 1)
    assert end == datetime.date(2027, 1, 31)


@pytest.mark.django_db
def test_semiannual_generates_once_per_semester(plant, user):
    from unittest.mock import patch
    from apps.tasks.models import ChecklistRun, ChecklistTemplate, ChecklistTemplateItem
    from apps.tasks.tasks import generate_scheduled_checklists

    tpl = ChecklistTemplate.objects.create(
        name="Test ripristino semestrale", frequency="semiannual",
        start_month=1, day_of_month=15, plant=plant, created_by=user,
    )
    ChecklistTemplateItem.objects.create(template=tpl, order=0, text="Ripristino OK")

    # 14 gennaio: il giorno di generazione non è ancora arrivato.
    with patch("apps.tasks.tasks.timezone.localdate", return_value=datetime.date(2026, 1, 14)):
        generate_scheduled_checklists()
    assert not ChecklistRun.objects.filter(template=tpl).exists()

    # Dal 15 gennaio a fine giugno resta lo stesso, unico run: scade il 30/06.
    for day in [datetime.date(2026, 1, 15), datetime.date(2026, 3, 2), datetime.date(2026, 6, 30)]:
        with patch("apps.tasks.tasks.timezone.localdate", return_value=day):
            generate_scheduled_checklists()
    run = ChecklistRun.objects.get(template=tpl)
    assert run.due_date == datetime.date(2026, 6, 30)

    # Luglio apre il secondo semestre: nuovo run con scadenza 31/12.
    with patch("apps.tasks.tasks.timezone.localdate", return_value=datetime.date(2026, 7, 20)):
        generate_scheduled_checklists()
    assert ChecklistRun.objects.filter(template=tpl).count() == 2
    assert ChecklistRun.objects.filter(
        template=tpl, due_date=datetime.date(2026, 12, 31)
    ).exists()


@pytest.mark.django_db
def test_annual_covers_the_whole_year(plant, user):
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import checklist_due_date_for, checklist_period_bounds

    tpl = ChecklistTemplate.objects.create(
        name="Riesame ISMS", frequency="annual", start_month=1, day_of_month=10,
        plant=plant, created_by=user,
    )
    start, end, gen = checklist_period_bounds(tpl, datetime.date(2026, 9, 3))
    assert (start, end, gen) == (
        datetime.date(2026, 1, 1), datetime.date(2026, 12, 31), datetime.date(2026, 1, 10)
    )
    assert checklist_due_date_for(tpl, datetime.date(2026, 1, 9)) is None
    assert checklist_due_date_for(tpl, datetime.date(2026, 9, 3)) == datetime.date(2026, 12, 31)


@pytest.mark.django_db
def test_monthly_behaviour_is_unchanged_by_start_month(plant, user):
    """La frequenza mensile ignora l'ancoraggio: un periodo al mese, sempre."""
    from apps.tasks.models import ChecklistTemplate
    from apps.tasks.services import checklist_period_bounds

    tpl = ChecklistTemplate.objects.create(
        name="Mensile", frequency="monthly", start_month=7, day_of_month=1,
        plant=plant, created_by=user,
    )
    start, end, gen = checklist_period_bounds(tpl, datetime.date(2026, 3, 18))
    assert (start, end, gen) == (
        datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), datetime.date(2026, 3, 1)
    )


@pytest.mark.django_db
def test_serializer_rejects_invalid_start_month(plant):
    from apps.tasks.serializers import ChecklistTemplateSerializer
    s = ChecklistTemplateSerializer(data={
        "name": "X", "frequency": "semiannual", "plant": str(plant.id),
        "start_month": 13,
        "items": [{"order": 0, "text": "a", "is_mandatory": True}],
    })
    assert not s.is_valid()
    assert "start_month" in s.errors
