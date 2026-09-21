"""Test API training e corsi."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_COURSES = "/api/v1/training/courses/"


def _client_with_role(role):
    from apps.auth_grc.models import UserPlantAccess
    u = User.objects.create_user(username=f"u_{role}", email=f"{role}@t.it", password="x")
    UserPlantAccess.objects.create(user=u, role=role, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="trn_user", email="trn@test.com", password="test")
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
    return Plant.objects.create(code="TRN-P", name="Plant Training", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def course(db, plant, user):
    from apps.training.models import TrainingCourse
    c = TrainingCourse.objects.create(
        title="Cybersecurity Awareness",
        source="interno",
        status="attivo",
        mandatory=True,
        created_by=user,
    )
    c.plants.add(plant)
    return c


# ── Courses CRUD ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_courses_authenticated(client):
    resp = client.get(URL_COURSES)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_courses_unauthenticated():
    resp = APIClient().get(URL_COURSES)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_course(client, plant):
    payload = {
        "title": "GDPR Training",
        "source": "interno",
        "status": "attivo",
        "mandatory": False,
        "plants": [str(plant.id)],
    }
    resp = client.post(URL_COURSES, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "GDPR Training"


@pytest.mark.django_db
def test_retrieve_course(client, course):
    resp = client.get(f"{URL_COURSES}{course.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Cybersecurity Awareness"


@pytest.mark.django_db
def test_update_course_status(client, course):
    resp = client.patch(f"{URL_COURSES}{course.id}/", {"status": "archiviato"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "archiviato"


@pytest.mark.django_db
def test_delete_course(client, course):
    resp = client.delete(f"{URL_COURSES}{course.id}/")
    assert resp.status_code == 204
    resp2 = client.get(f"{URL_COURSES}{course.id}/")
    assert resp2.status_code == 404


# ── Dati per persona: niente più endpoint (formazione a evidenze) ─────────

@pytest.mark.django_db
@pytest.mark.parametrize("url", [
    "/api/v1/training/enrollments/",
    "/api/v1/training/phishing/",
])
def test_per_person_endpoints_removed(client, url):
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_completion_rate_action_removed(client, course):
    assert client.get(f"{URL_COURSES}{course.id}/completion_rate/").status_code == 404


# ── Capacità e controlli collegabili ──────────────────────────────────────

@pytest.mark.django_db
def test_capabilities_readable_by_every_role(plant):
    from apps.auth_grc.models import GrcRole
    c = _client_with_role(GrcRole.RISK_MANAGER)
    r = c.get(f"{URL_COURSES}capabilities/")
    assert r.status_code == 200
    assert r.data == {"can_read_records": False, "can_manage_courses": False,
                      "can_manage_org": False, "manage_plant_ids": []}


@pytest.mark.django_db
def test_capabilities_of_site_plant_manager_and_nominated_ciso(plant):
    import datetime

    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.governance.models import NormativeRole, RoleAssignment
    from apps.plants.models import Plant

    other = Plant.objects.create(code="TRN-O", name="Altro", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    pm = User.objects.create_user(username="pm", email="pm@t.it", password="x")
    acc = UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER,
                                         scope_type="plant_list")
    acc.scope_plants.set([plant, other])
    RoleAssignment.objects.create(
        user=pm, role=NormativeRole.CISO, scope_type="plant", scope_id=other.pk,
        valid_from=datetime.date(2026, 1, 1),
    )
    c = APIClient()
    c.force_authenticate(user=pm)
    r = c.get(f"{URL_COURSES}capabilities/").data
    assert r["can_read_records"] and r["can_manage_courses"] and not r["can_manage_org"]
    assert set(r["manage_plant_ids"]) == {str(plant.pk), str(other.pk)}


@pytest.mark.django_db
def test_control_options_and_course_controls(client):
    import datetime

    from apps.controls.models import Control, Framework
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="A.6.3",
                                  translations={"it": {"title": "Consapevolezza"}})
    Control.objects.create(framework=fw, external_id="A.8.1", translations={})

    opts = client.get(f"{URL_COURSES}control-options/", {"search": "6.3"}).data
    assert [o["external_id"] for o in opts] == ["A.6.3"]
    assert opts[0]["framework_code"] == "ISO27001"

    r = client.post(URL_COURSES, {"title": "Awareness", "controls": [str(ctrl.pk)]},
                    format="json")
    assert r.status_code == 201, r.data
    assert "framework_refs" not in r.data
    assert [c["external_id"] for c in r.data["controls_detail"]] == ["A.6.3"]


@pytest.mark.django_db
def test_delete_course_is_soft(client, course):
    from apps.training.models import TrainingCourse
    resp = client.delete(f"{URL_COURSES}{course.id}/")
    assert resp.status_code == 204
    course.refresh_from_db()
    assert course.deleted_at is not None
    assert TrainingCourse.objects.filter(pk=course.pk).count() == 0
    assert TrainingCourse.objects.all_with_deleted().filter(pk=course.pk).count() == 1


# ── TrainingCourse model properties ──────────────────────────────────────

@pytest.mark.django_db
def test_training_course_mandatory_flag(plant, user):
    from apps.training.models import TrainingCourse
    c = TrainingCourse.objects.create(
        title="Mandatory Course", source="interno", status="attivo",
        mandatory=True, created_by=user,
    )
    assert c.mandatory is True


@pytest.mark.django_db
def test_course_in_plan_cannot_be_deleted(client, course):
    import datetime

    from apps.training.models import TrainingPlan, TrainingPlanItem
    plan = TrainingPlan.objects.create(plant=None, year=2026)
    TrainingPlanItem.objects.create(plan=plan, course=course, due_date=datetime.date(2026, 12, 31))
    resp = client.delete(f"{URL_COURSES}{course.id}/")
    assert resp.status_code == 400
    course.refresh_from_db()
    assert course.deleted_at is None
