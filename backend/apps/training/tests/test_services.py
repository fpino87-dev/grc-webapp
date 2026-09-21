"""P2-1 — copertura training/services.py (completion rate dei corsi, UI legacy)."""
import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def users(db):
    return [
        User.objects.create_user(username=f"tr{i}", email=f"tr{i}@x.it", password="x")
        for i in range(3)
    ]


def _course(deadline=None):
    from apps.training.models import TrainingCourse
    return TrainingCourse.objects.create(title="Corso", deadline=deadline)


def test_completion_rate_no_enrollments_is_zero():
    from apps.training.services import get_completion_rate
    c = _course()
    assert get_completion_rate(c.id) == 0.0


def test_completion_rate_partial(users):
    from apps.training.models import TrainingEnrollment
    from apps.training.services import get_completion_rate
    c = _course()
    TrainingEnrollment.objects.create(course=c, user=users[0], status="completato")
    TrainingEnrollment.objects.create(course=c, user=users[1], status="completato")
    TrainingEnrollment.objects.create(course=c, user=users[2], status="assegnato")
    assert get_completion_rate(c.id) == round(2 / 3 * 100, 2)
