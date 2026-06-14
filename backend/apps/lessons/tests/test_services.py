"""P2-1 — copertura lessons/services.py (validate, propagate)."""
import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="les", email="les@x.it", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


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
    from apps.lessons.services import propagate_to_plants, validate_lesson
    from apps.plants.models import Plant
    p2 = Plant.objects.create(code="LES-P2", name="P2", country="IT",
                              nis2_scope="non_soggetto", status="attivo")
    validate_lesson(lesson, user)  # workflow: bozza → validato prima di propagare
    out = propagate_to_plants(lesson, [p2.id], user)
    out.refresh_from_db()
    assert out.status == "propagato"
    assert p2 in out.propagated_to_plants.all()


def test_propagate_requires_validated(lesson, user):
    """Una lezione in bozza non è propagabile."""
    from apps.lessons.services import propagate_to_plants
    from apps.plants.models import Plant
    from rest_framework.exceptions import ValidationError
    p2 = Plant.objects.create(code="LES-P3", name="P3", country="IT",
                              nis2_scope="non_soggetto", status="attivo")
    with pytest.raises(ValidationError):
        propagate_to_plants(lesson, [p2.id], user)


def test_propagate_blocked_for_inaccessible_plant(lesson, plant):
    """Un utente fuori perimetro non può propagare verso un sito non suo."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.lessons.services import propagate_to_plants
    from apps.plants.models import Plant
    from rest_framework.exceptions import PermissionDenied

    pm = User.objects.create_user(username="pm_les", email="pm_les@x.it", password="x")
    acc = UserPlantAccess.objects.create(user=pm, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.set([plant])
    other = Plant.objects.create(code="LES-OTH", name="Other", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    lesson.status = "validato"
    lesson.save(update_fields=["status"])
    with pytest.raises(PermissionDenied):
        propagate_to_plants(lesson, [other.id], pm)
