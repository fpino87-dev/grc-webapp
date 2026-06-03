"""P2-1 — copertura training/services.py (completion rate, overdue)."""
import datetime
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

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


def test_overdue_enrollments(users):
    from apps.training.models import TrainingEnrollment
    from apps.training.services import get_overdue_enrollments
    past = _course(deadline=timezone.localdate() - datetime.timedelta(days=1))
    future = _course(deadline=timezone.localdate() + datetime.timedelta(days=30))
    over = TrainingEnrollment.objects.create(course=past, user=users[0], status="assegnato")
    TrainingEnrollment.objects.create(course=past, user=users[1], status="completato")  # escluso
    TrainingEnrollment.objects.create(course=future, user=users[2], status="assegnato")  # non scaduto
    ids = {e.id for e in get_overdue_enrollments()}
    assert over.id in ids
    assert len(ids) == 1
