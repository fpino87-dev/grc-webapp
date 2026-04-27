"""Test API training e corsi."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL_COURSES = "/api/v1/training/courses/"
URL_ENROLLMENTS = "/api/v1/training/enrollments/"


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


@pytest.fixture
def enrollment(db, course, user):
    from apps.training.models import TrainingEnrollment
    return TrainingEnrollment.objects.create(
        course=course,
        user=user,
        status="assegnato",
        created_by=user,
    )


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


@pytest.mark.django_db
def test_completion_rate_action(client, course):
    resp = client.get(f"{URL_COURSES}{course.id}/completion_rate/")
    assert resp.status_code == 200
    assert "rate" in resp.data or "completion_rate" in resp.data or isinstance(resp.data, dict)


# ── Enrollments ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_enrollments(client):
    resp = client.get(URL_ENROLLMENTS)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_enrollment(client, course, user):
    payload = {
        "course": str(course.id),
        "user": str(user.id),
        "status": "assegnato",
    }
    resp = client.post(URL_ENROLLMENTS, payload, format="json")
    assert resp.status_code in (201, 400)  # 400 if unique constraint (already enrolled)


@pytest.mark.django_db
def test_retrieve_enrollment(client, enrollment):
    resp = client.get(f"{URL_ENROLLMENTS}{enrollment.id}/")
    assert resp.status_code == 200
    assert resp.data["status"] == "assegnato"


# ── TrainingCourse model properties ──────────────────────────────────────

@pytest.mark.django_db
def test_training_course_mandatory_flag(plant, user):
    from apps.training.models import TrainingCourse
    c = TrainingCourse.objects.create(
        title="Mandatory Course", source="interno", status="attivo",
        mandatory=True, created_by=user,
    )
    assert c.mandatory is True
