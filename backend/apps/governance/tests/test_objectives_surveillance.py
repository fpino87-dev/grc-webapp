"""Sorveglianza automatica degli obiettivi (§6.2): traiettoria, notifiche, scadenzario."""
import pytest
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="OBS-P1", name="Plant Sorveglianza", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def user(db, plant):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="obs_u", email="obs@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


def _objective(plant, code="OBJ-S1", **kw):
    from apps.governance.models import SecurityObjective
    today = timezone.localdate()
    data = dict(
        code=code, title="Copertura patch", measure_source="manual", unit="%",
        start_date=today - timedelta(days=60), baseline_value=40.0, target_value=90.0,
        target_direction="above", target_date=today + timedelta(days=60),
        owner_role="plant_manager", evaluation_method="Misura mensile.", status="attivo",
    )
    data.update(kw)
    return SecurityObjective.objects.create(plant=plant, **data)


@pytest.mark.django_db
def test_task_notifies_once_when_trajectory_worsens(plant, user):
    """Si notifica quando la traiettoria peggiora, non a ogni giro: un'email
    ogni settimana fino alla scadenza la si impara a ignorare."""
    from apps.governance.services import record_objective_measurement
    from apps.governance.tasks_objectives import evaluate_objectives_task

    obj = _objective(plant)
    record_objective_measurement(obj, user, value=41.0)  # fermo a metà periodo

    # Il task importa fire_notification al momento della chiamata: si
    # sostituisce nel modulo che la definisce.
    with patch("apps.notifications.resolver.fire_notification") as fire:
        first = evaluate_objectives_task()
        events = [c.args[0] for c in fire.call_args_list]
    assert first["a_rischio"] == 1
    assert "objective_off_track" in events

    obj.refresh_from_db()
    assert obj.last_track == "a_rischio"

    with patch("apps.notifications.resolver.fire_notification") as fire:
        evaluate_objectives_task()
        assert "objective_off_track" not in [c.args[0] for c in fire.call_args_list]


@pytest.mark.django_db
def test_task_notifies_again_when_it_gets_worse(plant, user):
    from apps.governance.services import record_objective_measurement
    from apps.governance.tasks_objectives import evaluate_objectives_task

    obj = _objective(plant, target_date=timezone.localdate() + timedelta(days=5))
    record_objective_measurement(obj, user, value=41.0)
    with patch("apps.notifications.resolver.fire_notification"):
        evaluate_objectives_task()

    obj.target_date = timezone.localdate() - timedelta(days=1)  # scadenza passata
    obj.save(update_fields=["target_date"])
    with patch("apps.notifications.resolver.fire_notification") as fire:
        result = evaluate_objectives_task()
        assert "objective_off_track" in [c.args[0] for c in fire.call_args_list]
    assert result["mancati"] == 1


@pytest.mark.django_db
def test_deadline_reminder_is_sent_once(plant, user):
    from apps.governance.tasks_objectives import evaluate_objectives_task

    obj = _objective(plant, target_date=timezone.localdate() + timedelta(days=20))
    with patch("apps.notifications.resolver.fire_notification") as fire:
        evaluate_objectives_task()
        assert "objective_deadline" in [c.args[0] for c in fire.call_args_list]
    obj.refresh_from_db()
    assert obj.deadline_notice_at is not None

    with patch("apps.notifications.resolver.fire_notification") as fire:
        evaluate_objectives_task()
        assert "objective_deadline" not in [c.args[0] for c in fire.call_args_list]


@pytest.mark.django_db
def test_no_deadline_reminder_when_already_reached(plant, user):
    """Un obiettivo raggiunto in anticipo non ha bisogno di solleciti."""
    from apps.governance.services import record_objective_measurement
    from apps.governance.tasks_objectives import evaluate_objectives_task

    obj = _objective(plant, target_date=timezone.localdate() + timedelta(days=10))
    record_objective_measurement(obj, user, value=95.0)
    with patch("apps.notifications.resolver.fire_notification") as fire:
        evaluate_objectives_task()
        assert fire.call_args_list == []
    obj.refresh_from_db()
    assert obj.deadline_notice_at is None and obj.last_track == "in_linea"


@pytest.mark.django_db
def test_draft_and_closed_objectives_are_not_watched(plant, user):
    from apps.governance.tasks_objectives import evaluate_objectives_task

    _objective(plant, code="OBJ-DRAFT", status="bozza")
    _objective(plant, code="OBJ-DONE", status="raggiunto")
    assert evaluate_objectives_task()["valutati"] == 0


@pytest.mark.django_db
def test_objective_deadline_appears_in_activity_schedule(plant, user):
    from apps.compliance_schedule.services import get_activity_schedule

    _objective(plant, code="OBJ-SCHED")
    _objective(None, code="OBJ-ORG-SCHED")
    items = get_activity_schedule(plant=plant, months_ahead=6)
    labels = [i["label"] for i in items if i["category"] == "security_objective"]
    assert len(labels) == 2
    assert any("OBJ-SCHED" in l for l in labels)
    assert any("OBJ-ORG-SCHED" in l for l in labels)


@pytest.mark.django_db
def test_closed_objectives_leave_the_schedule(plant, user):
    from apps.compliance_schedule.services import get_activity_schedule
    from apps.governance.services import close_objective

    obj = _objective(plant, code="OBJ-CLOSED")
    close_objective(obj, user, outcome="raggiunto")
    items = get_activity_schedule(plant=plant, months_ahead=6)
    assert [i for i in items if i["category"] == "security_objective"] == []


@pytest.mark.django_db
def test_notification_reaches_the_configured_roles(plant, user):
    """Percorso completo fino alla mail, con i profili di notifica reali."""
    from apps.notifications.models import NotificationRoleProfile
    from apps.notifications.resolver import fire_notification
    from apps.governance.services import evaluate_objective

    NotificationRoleProfile.objects.update_or_create(
        grc_role="compliance_officer", defaults={"profile": "completo", "enabled": True})
    obj = _objective(plant)
    with patch("apps.notifications.services.send_grc_email") as send:
        fire_notification("objective_off_track", plant=plant,
                          context={"objective": obj, "evaluation": evaluate_objective(obj)})
    assert send.called
    assert "obs@test.com" in send.call_args.kwargs["recipients"]
    assert obj.code in send.call_args.kwargs["subject"]
