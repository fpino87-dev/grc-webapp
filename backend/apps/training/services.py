from django.utils import timezone

from .models import TrainingCourse, TrainingEnrollment


def get_completion_rate(course_id) -> float:
    """Return completion rate (0-100) for a given course."""
    total = TrainingEnrollment.objects.filter(course_id=course_id).count()
    if total == 0:
        return 0.0
    completed = TrainingEnrollment.objects.filter(course_id=course_id, status="completato").count()
    return round((completed / total) * 100, 2)


def get_overdue_enrollments():
    """Return enrollments where the course deadline has passed and status is not completed."""
    today = timezone.now().date()
    return TrainingEnrollment.objects.filter(
        course__deadline__lt=today,
    ).exclude(
        status__in=["completato", "scaduto"],
    ).select_related("course", "user")
