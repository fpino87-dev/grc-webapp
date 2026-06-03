"""P2-1 — copertura lessons/services.py (validate, propagate)."""
import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="les", email="les@x.it", password="x")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="LES-P", name="Plant Lessons", country="IT",
                                nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def lesson(db, plant, user):
    from apps.lessons.models import LessonLearned
    return LessonLearned.objects.create(
        title="Lezione", description="desc", plant=plant, status="bozza", created_by=user,
    )


def test_validate_lesson(lesson, user):
    from apps.lessons.services import validate_lesson
    out = validate_lesson(lesson, user)
    out.refresh_from_db()
    assert out.status == "validato"
    assert out.validated_by == user
    assert out.validated_at is not None


def test_propagate_to_plants(lesson, user):
    from apps.lessons.services import propagate_to_plants
    from apps.plants.models import Plant
    p2 = Plant.objects.create(code="LES-P2", name="P2", country="IT",
                              nis2_scope="non_soggetto", status="attivo")
    out = propagate_to_plants(lesson, [p2.id], user)
    out.refresh_from_db()
    assert out.status == "propagato"
    assert p2 in out.propagated_to_plants.all()
