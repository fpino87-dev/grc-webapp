"""Formazione a evidenze, fase 2: evidenze → controlli, promemoria, scadenzario."""
import base64
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()

URL_SESS = "/api/v1/training/sessions/"

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="TA", name="Plant A", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def plant_b(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="TB", name="Plant B", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def co(db):
    u = User.objects.create_user(username="co", email="co@t.it", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def controls(db):
    from apps.controls.models import Control, Framework
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=date(2024, 1, 1))
    return [
        Control.objects.create(framework=fw, external_id=code, translations={"title": {"it": code}})
        for code in ("A.6.3", "A.5.1", "A.8.7")
    ]


@pytest.fixture
def course(db, co, controls):
    from apps.training.models import TrainingCourse
    c = TrainingCourse.objects.create(
        title="Awareness base", kind="corso", mandatory=True, validity_months=12, created_by=co,
    )
    c.controls.set(controls)
    return c


@pytest.fixture
def instances(plant, controls):
    """A.6.3 applicabile, A.5.1 escluso dallo SOA, A.8.7 non istanziato."""
    from apps.controls.models import ControlInstance
    return [
        ControlInstance.objects.create(plant=plant, control=controls[0], status="gap"),
        ControlInstance.objects.create(plant=plant, control=controls[1], status="non_valutato",
                                       applicability="escluso", exclusion_justification="n/a"),
    ]


def _plan_item(course, plant, due, audiences=()):
    from apps.training.models import TrainingPlan, TrainingPlanItem
    plan, _ = TrainingPlan.objects.get_or_create(plant=plant, year=due.year)
    item = TrainingPlanItem.objects.create(plan=plan, course=course, due_date=due)
    item.audiences.set(audiences)
    return item


def _register(user, course, plant, **extra):
    data = {
        "course": str(course.pk),
        "plant": str(plant.pk),
        "held_on": (timezone.localdate() - timedelta(days=1)).isoformat(),
        "target_count": 10,
        "trained_count": 8,
        "file": SimpleUploadedFile("registro.png", _PNG, content_type="image/png"),
    }
    data.update(extra)
    return _client(user).post(URL_SESS, data, format="multipart")


def _reminders(item):
    from apps.tasks.models import Task
    return Task.objects.filter(source_module="M15", source_id=item.pk)


# ── Evidenze → controlli ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_session_evidence_linked_to_site_controls(co, course, plant, instances):
    r = _register(co, course, plant)
    assert r.status_code == 201, r.data
    assert r.data["control_links"] == {"linked": 1, "not_applicable": ["A.5.1", "A.8.7"]}

    applicable, excluded = instances
    assert list(applicable.evidences.values_list("pk", flat=True)) == [r.data["evidence"]]
    assert not excluded.evidences.exists()


@pytest.mark.django_db
def test_session_does_not_touch_other_site_controls(co, course, plant, plant_b, instances):
    from apps.controls.models import ControlInstance
    other = ControlInstance.objects.create(plant=plant_b, control=instances[0].control)
    assert _register(co, course, plant).status_code == 201
    assert not other.evidences.exists()


@pytest.mark.django_db
def test_course_without_controls_links_nothing(co, course, plant, instances):
    course.controls.clear()
    r = _register(co, course, plant)
    assert r.status_code == 201
    assert r.data["control_links"] == {"linked": 0, "not_applicable": []}


@pytest.mark.django_db
def test_delete_session_unlinks_evidence_from_unevaluated_controls(co, course, plant, instances):
    from apps.training.models import TrainingSession
    instances[0].status = "non_valutato"
    instances[0].save()
    r = _register(co, course, plant)
    assert _client(co).delete(f"{URL_SESS}{r.data['id']}/").status_code == 204
    assert not instances[0].evidences.exists()
    assert not TrainingSession.objects.filter(pk=r.data["id"]).exists()


# ── Promemoria ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_reminder_task_for_due_and_late_items(co, course, plant):
    from apps.training.models import TrainingAudience
    from apps.training.services import remind_plan_items

    today = date(2026, 9, 21)
    aud = TrainingAudience.objects.create(plant=plant, name="Produzione", headcount=120,
                                          headcount_updated_at=today)
    soon = _plan_item(course, plant, today + timedelta(days=20), [aud])
    late = _plan_item(course, plant, today - timedelta(days=5))
    far = _plan_item(course, plant, today + timedelta(days=90))

    assert remind_plan_items(today=today) == {"in_scadenza": 1, "in_ritardo": 1}

    t_soon = _reminders(soon).get()
    assert t_soon.assigned_role == GrcRole.COMPLIANCE_OFFICER
    assert t_soon.assigned_to is None and t_soon.plant == plant
    assert t_soon.priority == "media" and t_soon.due_date == soon.due_date
    assert "120 persone" in t_soon.description
    t_late = _reminders(late).get()
    assert t_late.priority == "alta" and t_late.due_date == today + timedelta(days=7)
    assert not _reminders(far).exists()


@pytest.mark.django_db
def test_reminder_is_not_duplicated(co, course, plant):
    from apps.training.services import remind_plan_items

    today = date(2026, 9, 21)
    item = _plan_item(course, plant, today + timedelta(days=10))
    remind_plan_items(today=today)
    # Il giorno dopo il promemoria è ancora aperto; e se chi lo riceve lo
    # annulla, non ricompare.
    assert remind_plan_items(today=today + timedelta(days=1)) == {"in_scadenza": 0, "in_ritardo": 0}
    _reminders(item).update(status="annullato")
    remind_plan_items(today=today + timedelta(days=2))
    assert _reminders(item).count() == 1


@pytest.mark.django_db
def test_no_reminder_for_done_or_archived_items(co, course, plant):
    from apps.training.models import TrainingCourse, TrainingSession
    from apps.training.services import remind_plan_items

    today = date(2026, 9, 21)
    done = _plan_item(course, plant, today + timedelta(days=10))
    TrainingSession.objects.create(course=course, plan_item=done, plant=plant,
                                   held_on=today, trained_count=1, target_count=1)
    archived = TrainingCourse.objects.create(title="Vecchio", status="archiviato")
    _plan_item(archived, plant, today - timedelta(days=3))

    assert remind_plan_items(today=today) == {"in_scadenza": 0, "in_ritardo": 0}


@pytest.mark.django_db
def test_registering_session_closes_reminder(co, course, plant, instances):
    from apps.training.services import remind_plan_items

    today = timezone.localdate()
    item = _plan_item(course, plant, today + timedelta(days=10))
    remind_plan_items()
    assert _reminders(item).get().status == "aperto"

    r = _register(co, course, plant)
    assert r.status_code == 201, r.data
    assert str(r.data["plan_item"]) == str(item.pk)
    assert _reminders(item).get().status == "completato"


@pytest.mark.django_db
def test_reminder_notifies_training_managers(co, course, plant, mailoutbox):
    from apps.notifications.models import NotificationRoleProfile
    from apps.training.services import remind_plan_items

    NotificationRoleProfile.get_or_create_defaults()
    pm = User.objects.create_user(username="pm", email="pm@t.it", password="x")
    UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER, scope_type="org")
    auditor = User.objects.create_user(username="ext", email="ext@t.it", password="x")
    UserPlantAccess.objects.create(user=auditor, role="external_auditor", scope_type="org")

    today = date(2026, 9, 21)
    _plan_item(course, plant, today - timedelta(days=2))
    remind_plan_items(today=today)

    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    assert "Formazione in ritardo" in mail.subject
    assert set(mail.to) == {"co@t.it", "pm@t.it"}


# ── Scadenzario ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_schedule_lists_open_plan_items(co, course, plant, plant_b):
    from apps.compliance_schedule.services import get_activity_schedule
    from apps.training.models import TrainingCourse, TrainingPlan, TrainingPlanItem, TrainingSession

    today = timezone.localdate()
    course.deadline = today + timedelta(days=10)
    course.save()
    course.plants.add(plant)
    open_item = _plan_item(course, plant, today + timedelta(days=15))
    done = _plan_item(course, plant, today + timedelta(days=20))
    TrainingSession.objects.create(course=course, plan_item=done, plant=plant,
                                   held_on=today, trained_count=1, target_count=1)
    org_plan = TrainingPlan.objects.create(plant=None, year=(today + timedelta(days=25)).year)
    org_item = TrainingPlanItem.objects.create(plan=org_plan, course=course,
                                               due_date=today + timedelta(days=25))
    other_site = _plan_item(course, plant_b, today + timedelta(days=30))
    # Corso con la vecchia scadenza e senza piano: resta nello scadenzario.
    old = TrainingCourse.objects.create(title="Storico", mandatory=True,
                                        deadline=today + timedelta(days=40))
    old.plants.add(plant)

    rows = [a for a in get_activity_schedule(plant=plant) if a["category"] == "training_mandatory"]
    refs = {a["ref_id"] for a in rows}
    assert refs == {str(open_item.pk), str(org_item.pk), str(old.pk)}
    assert str(done.pk) not in refs and str(other_site.pk) not in refs
    # La scadenza del corso non compare più una volta che il corso è nel piano.
    assert str(course.pk) not in refs
