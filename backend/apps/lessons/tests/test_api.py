"""Test API lezioni apprese."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/lessons/lessons/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="ls_user", email="ls@test.com", password="test")
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
        code="LS-P", name="Plant Lessons", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def lesson(db, plant, user):
    from apps.lessons.models import LessonLearned
    return LessonLearned.objects.create(
        title="Lezione da incidente ransomware",
        description="Migliorare backup offsite",
        category="incident",
        status="bozza",
        plant=plant,
        identified_by=user,
        created_by=user,
    )


@pytest.mark.django_db
def test_list_lessons_authenticated(client):
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_list_lessons_unauthenticated():
    resp = APIClient().get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_create_lesson(client, plant):
    payload = {
        "title": "Patch management migliorato",
        "description": "Ridurre la finestra di patching",
        "category": "operativo",
        "status": "bozza",
        "plant": str(plant.id),
    }
    resp = client.post(URL, payload, format="json")
    assert resp.status_code == 201
    assert resp.data["title"] == "Patch management migliorato"


@pytest.mark.django_db
def test_retrieve_lesson(client, lesson):
    resp = client.get(f"{URL}{lesson.id}/")
    assert resp.status_code == 200
    assert resp.data["title"] == "Lezione da incidente ransomware"


@pytest.mark.django_db
def test_update_lesson_status_is_governed(client, lesson):
    """status è read-only: una PATCH diretta non valida la lezione
    (la validazione passa solo dall'azione dedicata)."""
    resp = client.patch(f"{URL}{lesson.id}/", {"status": "validato"}, format="json")
    assert resp.status_code == 200
    lesson.refresh_from_db()
    assert lesson.status == "bozza"
    assert lesson.validated_by is None


@pytest.mark.django_db
def test_validate_action(client, lesson):
    resp = client.post(f"{URL}{lesson.id}/validate/")
    assert resp.status_code == 200
    lesson.refresh_from_db()
    assert lesson.status == "validato"
    assert lesson.validated_by is not None
    assert lesson.validated_at is not None


@pytest.mark.django_db
def test_delete_lesson_soft(client, lesson):
    resp = client.delete(f"{URL}{lesson.id}/")
    assert resp.status_code == 204
    from apps.lessons.models import LessonLearned
    lesson.refresh_from_db()
    assert lesson.deleted_at is not None
    assert LessonLearned.objects.filter(pk=lesson.pk).count() == 0
    assert LessonLearned.objects.all_with_deleted().filter(pk=lesson.pk).count() == 1


@pytest.mark.django_db
def test_filter_lessons_by_plant(client, plant, lesson):
    resp = client.get(f"{URL}?plant={plant.id}")
    assert resp.status_code == 200
