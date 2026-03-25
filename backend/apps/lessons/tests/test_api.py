"""Test API lezioni apprese."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/lessons/lessons/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ls_user", email="ls@test.com", password="test")


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
def test_update_lesson(client, lesson):
    resp = client.patch(f"{URL}{lesson.id}/", {"status": "validato"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "validato"


@pytest.mark.django_db
def test_delete_lesson(client, lesson):
    resp = client.delete(f"{URL}{lesson.id}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_filter_lessons_by_plant(client, plant, lesson):
    resp = client.get(f"{URL}?plant={plant.id}")
    assert resp.status_code == 200
