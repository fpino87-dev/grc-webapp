"""Corsi di organizzazione o di sito e controlli provati per tipo di destinatari."""
import base64
import importlib
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()

URL_COURSES = "/api/v1/training/courses/"
URL_ITEMS = "/api/v1/training/plan-items/"
URL_SESS = "/api/v1/training/sessions/"
URL_RULES = "/api/v1/training/evidence-controls/"

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


def _user(name, role, plants=()):
    u = User.objects.create_user(username=name, email=f"{name}@t.it", password="x")
    access = UserPlantAccess.objects.create(
        user=u, role=role, scope_type="single_plant" if plants else "org",
    )
    if plants:
        access.scope_plants.set(plants)
    return u


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
    return _user("co", GrcRole.COMPLIANCE_OFFICER)


@pytest.fixture
def pm(plant):
    return _user("pm", GrcRole.PLANT_MANAGER, plants=[plant])


def _course(title="Igiene standard", plants=()):
    from apps.training.models import TrainingCourse
    c = TrainingCourse.objects.create(title=title, validity_months=12)
    c.plants.set(plants)
    return c


# ── Ambito del corso ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_org_courses_need_org_scope_site_courses_the_site(co, pm, plant, plant_b):
    r = _client(co).post(URL_COURSES, {"title": "Igiene standard"}, format="json")
    assert r.status_code == 201 and r.data["plants"] == [] and r.data["plant_codes"] == []

    pm_client = _client(pm)
    assert pm_client.post(URL_COURSES, {"title": "Comune"}, format="json").status_code == 403
    r = pm_client.post(URL_COURSES, {"title": "Carrelli TA", "plants": [str(plant.pk)]},
                       format="json")
    assert r.status_code == 201 and r.data["plant_codes"] == ["TA"]
    r = pm_client.post(URL_COURSES, {"title": "A e B", "plants": [str(plant.pk), str(plant_b.pk)]},
                       format="json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_site_manager_cannot_change_org_course(co, pm, plant):
    org = _course()
    own = _course("Carrelli TA", plants=[plant])
    c = _client(pm)
    assert c.patch(f"{URL_COURSES}{org.pk}/", {"title": "x"}, format="json").status_code == 403
    assert c.delete(f"{URL_COURSES}{org.pk}/").status_code == 403
    # Un corso di sito non si trasforma in corso di organizzazione.
    assert c.patch(f"{URL_COURSES}{own.pk}/", {"plants": []}, format="json").status_code == 403
    assert c.patch(f"{URL_COURSES}{own.pk}/", {"title": "Carrelli"}, format="json").status_code == 200
    assert _client(co).patch(f"{URL_COURSES}{own.pk}/", {"plants": []},
                             format="json").status_code == 200


@pytest.mark.django_db
def test_site_sees_org_courses_and_its_own(pm, plant, plant_b):
    _course()
    _course("Carrelli TA", plants=[plant])
    _course("Solo TB", plants=[plant_b])
    titles = {c["title"] for c in _client(pm).get(URL_COURSES).data["results"]}
    assert titles == {"Igiene standard", "Carrelli TA"}


@pytest.mark.django_db
def test_plans_and_sessions_accept_only_courses_valid_for_the_site(co, plant, plant_b):
    from apps.training.models import TrainingPlan

    org_course = _course()
    course_b = _course("Solo TB", plants=[plant_b])
    org_plan = TrainingPlan.objects.create(plant=None, year=2026)
    site_plan = TrainingPlan.objects.create(plant=plant, year=2026)
    c = _client(co)
    item = lambda plan, course: c.post(URL_ITEMS, {  # noqa: E731
        "plan": str(plan.pk), "course": str(course.pk), "due_date": "2026-11-30",
    }, format="json")

    assert item(org_plan, org_course).status_code == 201
    assert "course" in item(org_plan, course_b).data
    assert item(site_plan, org_course).status_code == 201
    assert "course" in item(site_plan, course_b).data

    r = c.post(URL_SESS, {
        "course": str(course_b.pk), "plant": str(plant.pk),
        "held_on": (timezone.localdate() - timedelta(days=1)).isoformat(),
        "target_count": 5, "trained_count": 5,
        "file": SimpleUploadedFile("r.png", _PNG, content_type="image/png"),
    }, format="multipart")
    assert r.status_code == 400 and "course" in r.data


# ── Controlli provati per tipo di destinatari ──────────────────────────────

@pytest.fixture
def acn(db):
    from apps.controls.models import Control, Framework
    fw = Framework.objects.create(code="ACN_NIS2", name="ACN", version="1",
                                  published_at=date(2024, 1, 1))
    return {code: Control.objects.create(framework=fw, external_id=code, translations={})
            for code in ("ACN-NIS2-PR.AT-01", "ACN-NIS2-PR.AT-02", "ACN-NIS2-GV.RR-02")}


@pytest.mark.django_db
def test_evidence_controls_are_managed_at_org_level(co, pm, acn):
    auditor = _user("aud", GrcRole.EXTERNAL_AUDITOR)
    payload = {"audience_kind": "generale", "control": str(acn["ACN-NIS2-PR.AT-01"].pk)}
    assert _client(pm).post(URL_RULES, payload, format="json").status_code == 403
    assert _client(auditor).post(URL_RULES, payload, format="json").status_code == 403
    r = _client(co).post(URL_RULES, payload, format="json")
    assert r.status_code == 201
    assert _client(auditor).get(URL_RULES).status_code == 200
    assert _client(pm).delete(f"{URL_RULES}{r.data['id']}/").status_code == 403


@pytest.mark.django_db
def test_load_defaults_adds_only_loaded_controls_and_is_idempotent(acn):
    from apps.training.models import TrainingEvidenceControl

    call_command("load_training_evidence_controls")
    call_command("load_training_evidence_controls")
    rows = sorted(TrainingEvidenceControl.objects.values_list("audience_kind", "control__external_id"))
    assert rows == [("generale", "ACN-NIS2-PR.AT-01"), ("ruoli_critici", "ACN-NIS2-PR.AT-02")]


@pytest.mark.django_db
def test_migration_turns_course_controls_into_audience_rules(acn):
    from django.apps import apps

    from apps.training.models import TrainingCourse, TrainingEvidenceControl

    migration = importlib.import_module("apps.training.migrations.0006_training_evidence_controls")
    general = TrainingCourse.objects.create(title="Awareness")
    general.controls.set([acn["ACN-NIS2-PR.AT-01"]])
    critical = TrainingCourse.objects.create(title="Admin", audience_kind="ruoli_critici")
    critical.controls.set([acn["ACN-NIS2-PR.AT-02"], acn["ACN-NIS2-GV.RR-02"]])
    archived = TrainingCourse.objects.create(title="Vecchio", status="archiviato")
    archived.controls.set([acn["ACN-NIS2-GV.RR-02"]])

    migration.copy_course_controls(apps, None)
    rows = sorted(TrainingEvidenceControl.objects.values_list("audience_kind", "control__external_id"))
    assert rows == [
        ("generale", "ACN-NIS2-PR.AT-01"),
        ("ruoli_critici", "ACN-NIS2-GV.RR-02"),
        ("ruoli_critici", "ACN-NIS2-PR.AT-02"),
    ]
